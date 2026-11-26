"""Verify the pinned original Tantivy closures and staged machine-code-only archives."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

MANIFEST_SHA = "8c63151616ed8fdd4f5c2bb7b4418d9f134fe4574e52a23d8ac049d68aef385b"
ARCHIVE_SHA = "a20d84bcffa31bab35909ad0555142ec5b1f54f07c1482fb023675ad81309159"
PLATFORMS = {
    "ios-arm64": ("c949c72ac58601ef02f5b5e11569fbf21970a6afcd05d1ac645e78174398ccde",
                  "598f4d40afa384f5364a234bffd07133a31f80c2bb4228491382fd95ff6e3e0e"),
    "ios-arm64-sim": ("8902d1608a2263597f8f9fa9d7d4155e8ec5efe4701cc0db03905c170c25899a",
                      "aafce3613a1ec63a0cca3fa2acf08cf56cb5ebefe6dc03a88f5702cdc4981652")
}

def require(ok, reason):
    if not ok: raise ValueError(reason)

def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""): result.update(chunk)
    return result.hexdigest()

def prepare(root, source, run, environment):
    archive = root / "native-dependencies.tar.gz"
    require(digest(archive) == ARCHIVE_SHA, "native_dependency_archive_mismatch")
    target = root / "native-dependencies"
    require(not target.exists(), "fresh_native_dependency_directory_required")
    target.mkdir(mode=0o700)
    with tarfile.open(archive, "r:gz") as tar:
        member = tar.getmember("dependency-manifest.json")
        require(member.isfile() and member.size < 64 * 1024, "dependency_manifest_size")
        data = tar.extractfile(member).read()
        require(hashlib.sha256(data).hexdigest() == MANIFEST_SHA, "dependency_manifest_mismatch")
        manifest = json.loads(data)
        require(manifest["contract"] == "pinkha-dual-native-dependencies-v1"
                and manifest["version"] == "v1.0.6", "dependency_contract")
        expected = manifest["files"]
        seen = set()
        for item in tar:
            name = item.name
            require(name not in seen and item.isfile() and not name.startswith("/")
                    and all(x not in ("", ".", "..") for x in name.split("/"))
                    and "\\" not in name and (name in expected or name == "dependency-manifest.json"),
                    "unexpected_dependency_member")
            seen.add(name)
            path = target / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tar.extractfile(item) as incoming, path.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            if name in expected:
                require(path.stat().st_size == expected[name]["bytes"] and digest(path) == expected[name]["sha256"],
                        "native_dependency_member_changed:" + name)
        require(seen == set(expected) | {"dependency-manifest.json"}, "native_dependency_inventory")
    extra, receipts = {}, []
    for platform, (archive_pin, native_pin) in PLATFORMS.items():
        directory = target / platform
        original_archive = directory / "original-release.tar.gz"
        native = directory / "libtantivy_go.a"
        require(digest(original_archive) == archive_pin and digest(native) == native_pin,
                "pinned_tantivy_dependency_changed")
        proof = json.loads((directory / "transform.json").read_text())
        require(proof["contract"] == "pinkha-native-embedded-llvm-removal-v2"
                and proof["verified"] is True and proof["nativeSHA256"] == native_pin
                and proof["nativeCodeDataSymbolsRelocationTargetsUnchanged"] is True
                and proof["goLTOGuardDisabled"] is False and proof["removedLegacyLLVMSections"] > 0,
                "native_transform_proof_missing")
        original = directory / "original-expanded/libtantivy_go.a"
        original.parent.mkdir(mode=0o700)
        with tarfile.open(original_archive, "r:gz") as tar:
            members = [m for m in tar if not m.isdir()]
            require(len(members) == 1 and members[0].isfile()
                    and members[0].name.removeprefix("./") == "libtantivy_go.a", "original_tantivy_inventory")
            with tar.extractfile(members[0]) as incoming, original.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
        require(digest(original) == proof["sourceSHA256"], "original_library_changed")
        # Native symbols, not LLVM IR symbols. Preserve both exact tool outputs.
        original_symbols = run(["xcrun", "nm", "--no-llvm-bc", "-g", "-j", original],
                               "tantivy-" + platform + "-original-symbols", environment=environment, timeout=120)
        native_symbols = run(["xcrun", "nm", "--no-llvm-bc", "-g", "-j", native],
                             "tantivy-" + platform + "-native-symbols", environment=environment, timeout=120)
        require(sorted(original_symbols.read_text().splitlines()) == sorted(native_symbols.read_text().splitlines()),
                "actual_native_symbols_changed:" + platform)
        relative = "heart/deps/libs/" + platform + "/libtantivy_go.a"
        destination = source / relative
        require(not destination.exists(), "unexpected_native_dependency_destination")
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(native, destination)
        extra[relative] = {"sha256": native_pin, "bytes": destination.stat().st_size}
        receipts.append({"platform": platform, "releaseArchiveSHA256": archive_pin,
            "originalLibrarySHA256": proof["sourceSHA256"], "nativeLibrarySHA256": native_pin,
            "transformReceiptSHA256": digest(directory / "transform.json"),
            "nativeSemanticInventorySHA256": proof["nativeSemanticInventorySHA256"],
            "macNativeSymbolsSHA256": digest(native_symbols),
            "originalReleaseRetained": True, "nativeRuntimeAcceptance": "NOT_RUN"})
    return extra, {"dependencyManifestSHA256": MANIFEST_SHA, "archiveSHA256": ARCHIVE_SHA, "libraries": receipts}
