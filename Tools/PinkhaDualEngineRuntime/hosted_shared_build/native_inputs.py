"""Transport the original, already compiled native8ac inputs without rebuilding.

The payload is an inventory of original files, not a new native qualification.
It contains no account, simulator, signing identity, key or credential input.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile


GIB = 1024 ** 3
MANIFEST_SHA = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
RUNTIME_SHA = "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0"
ASSEMBLY_SHA = "c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231"
FRAMEWORK_SHA = "fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf"
SLICE_PINS = {
    "simulator": ("946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b",
                  "efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903",
                  "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763",
                  "ios-arm64-simulator"),
    "device": ("c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208",
               "fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546",
               "8592fb526b8796b3e118f1a18bacc276e89894459207d5df294b17b0c3859c50",
               "ios-arm64"),
}
MAX_FILES = 20000
MAX_UNPACKED_BYTES = 4 * GIB
PAYLOAD_NAME = "native8ac-inputs.tar.gz"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 ** 2), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(name):
    p = PurePosixPath(name)
    require(isinstance(name, str) and name == p.as_posix() and not p.is_absolute()
            and name not in ("", ".") and ".." not in p.parts and "\\" not in name
            and not any(ord(c) < 32 for c in name), "Unsafe payload path")
    return p


def regular(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Expected a physical original regular file: " + str(path))
    s = path.stat()
    require(stat.S_IMODE(s.st_mode) & 0o7000 == 0, "Unexpected special file mode")
    return {"bytes": s.st_size, "sha256": sha(path), "mode": stat.S_IMODE(s.st_mode),
            "mtimeNS": s.st_mtime_ns}


def file_inventory(root):
    root = Path(root)
    require(root.is_dir() and root.resolve() == root, "Physical input directory required")
    result = {}
    for p in sorted(root.rglob("*")):
        require(not p.is_symlink(), "Native inputs cannot contain symlinks")
        if p.is_file():
            row = regular(p)
            result[p.relative_to(root).as_posix()] = {k: row[k] for k in ("bytes", "sha256")}
        else:
            require(p.is_dir(), "Unexpected input node")
    return result


def exact_file(path, expected):
    row = regular(path)
    require(row["sha256"] == expected, "Original input bytes differ: " + str(path))
    return Path(path).read_bytes()


def qualify(materialization, framework, source_manifest, runtime_helper, bridge):
    """Reuse the original runtime validator and complete framework inventory."""
    materialization, framework = Path(materialization), Path(framework)
    manifest_bytes = exact_file(source_manifest, MANIFEST_SHA)
    exact_file(runtime_helper, RUNTIME_SHA)
    manifest = json.loads(manifest_bytes)
    require(len(manifest["files"]) == 4868 and manifest["runtimeBuildDate"] == "2026-11-26",
            "Exact original native source closure is required")
    assembly = json.loads(exact_file(materialization / "receipt.json", ASSEMBLY_SHA))
    inventory = json.loads(exact_file(materialization / "framework-files.json", FRAMEWORK_SHA))
    require(file_inventory(framework) == inventory, "Complete original framework differs")
    spec = importlib.util.spec_from_file_location("hosted_original_runtime_identity", runtime_helper)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    inputs = {}
    for kind, (receipt_sha, command_sha, binary_sha, identifier) in SLICE_PINS.items():
        base = materialization / kind
        receipt = exact_file(base / "receipt.json", receipt_sha)
        command = exact_file(base / "combined-gomobile-bind.command.json", command_sha)
        log_path = base / "combined-gomobile-bind.log"
        require(regular(log_path)["bytes"] <= 256 * 1024 ** 2, "Original native log is unexpectedly large")
        require([r for r in json.loads(receipt)["commands"] if r["name"] == "combined-gomobile-bind"]
                == [json.loads(command)], "Original command and receipt differ")
        inputs[kind] = {"receipt": receipt, "command": command, "log": log_path.read_bytes(),
                        "expectedReceiptSHA256": receipt_sha, "expectedCommandSHA256": command_sha}
        binary = framework / identifier / "Lib.framework/Lib"
        require(sha(binary) == binary_sha == assembly["inputs"][kind]["binarySHA256"]
                and binary.stat().st_size == assembly["inputs"][kind]["binaryBytes"],
                "Original native binary identity differs")
    result = runtime.qualify_application(manifest_bytes, "2026-11-26", Path(bridge).read_bytes(), inputs)
    require(assembly["status"] == "PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE"
            and assembly["runtimeIdentity"] == result["identity"]
            and assembly["frameworkInventorySHA256"] == FRAMEWORK_SHA,
            "Original assembly qualification differs")
    return {"runtimeIdentity": result, "frameworkFiles": len(inventory), "nativeSourceFiles": 4868,
            "nativeSourceManifestSHA256": MANIFEST_SHA, "nativeBuildsNow": 0, "testsExecuted": 0}


def payload_sources(materialization, framework, native_source, source_manifest):
    materialization, framework, native_source = map(Path, (materialization, framework, native_source))
    manifest = json.loads(exact_file(source_manifest, MANIFEST_SHA))
    files = {"source-manifest.json": Path(source_manifest)}
    for name in ("receipt.json", "framework-files.json"):
        files["native/" + name] = materialization / name
    for kind in SLICE_PINS:
        for name in ("receipt.json", "combined-gomobile-bind.command.json", "combined-gomobile-bind.log"):
            files["native/" + kind + "/" + name] = materialization / kind / name
    for relative, expected in manifest["files"].items():
        safe_relative(relative)
        path = native_source / relative
        row = regular(path)
        require({k: row[k] for k in ("bytes", "sha256")} == expected,
                "Original native source differs: " + relative)
        files["native-source/" + relative] = path
    for relative in file_inventory(framework):
        files["Lib.xcframework/" + relative] = framework / relative
    require(len(files) <= MAX_FILES, "Native payload file bound exceeded")
    return files


def pack(files, output, qualification):
    """One new archive, no temporary full copy and no input deletion."""
    output = Path(output)
    require(not output.exists(), "Fresh native payload output required")
    before = {name: regular(path) for name, path in sorted(files.items())}
    require(sum(row["bytes"] for row in before.values()) <= MAX_UNPACKED_BYTES, "Native payload byte bound exceeded")
    for name in before:
        safe_relative(name)
    manifest = {"schema": "pinkha-original-native8ac-transport-v1", "files": before,
                "qualification": qualification, "nativeSourceManifestSHA256": MANIFEST_SHA,
                "nativeBuildsNow": 0, "testsExecuted": 0}
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    with output.open("xb") as raw, tarfile.open(fileobj=raw, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo("payload-manifest.json")
        info.size, info.mode = len(manifest_bytes), 0o600
        archive.addfile(info, io.BytesIO(manifest_bytes))
        for name, row in before.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = row["bytes"], row["mode"]
            info.mtime = row["mtimeNS"] // 1000000000
            info.pax_headers = {"mtime": str(row["mtimeNS"] // 1000000000) + "." + f'{row["mtimeNS"] % 1000000000:09d}'}
            with files[name].open("rb") as stream:
                archive.addfile(info, stream)
    after = {name: regular(path) for name, path in sorted(files.items())}
    require(before == after, "Original native inputs changed during transport packaging")
    # Independently stream every archived byte; a successful tar command alone
    # does not qualify a native input artifact.
    checked = read_payload(output, expected_manifest=hashlib.sha256(manifest_bytes).hexdigest())
    return {"status": "PASS_ORIGINAL_NATIVE8AC_TRANSPORT_NOT_APP_ACCEPTANCE", "payload": regular(output),
            "payloadManifestSHA256": hashlib.sha256(manifest_bytes).hexdigest(), "files": len(before),
            "sourceBeforeEqualsAfter": True, "archiveVerified": checked,
            "nativeSourceManifestSHA256": MANIFEST_SHA, "nativeBuildsNow": 0, "testsExecuted": 0}


def read_payload(path, *, expected_manifest, destination=None):
    """Hash the whole bounded tar before optionally materializing safe files."""
    destination = Path(destination) if destination is not None else None
    if destination is not None:
        require(not destination.exists(), "Native destination must be fresh")
    seen, total, folded = {}, 0, set()
    with tarfile.open(path, "r:gz") as archive:
        first = archive.next()
        require(first and first.name == "payload-manifest.json" and first.isfile()
                and first.size <= 8 * 1024 ** 2, "First bounded payload manifest required")
        manifest_bytes = archive.extractfile(first).read()
        require(hashlib.sha256(manifest_bytes).hexdigest() == expected_manifest, "Native payload manifest differs")
        manifest = json.loads(manifest_bytes)
        require(manifest["schema"] == "pinkha-original-native8ac-transport-v1"
                and manifest["nativeSourceManifestSHA256"] == MANIFEST_SHA
                and manifest["nativeBuildsNow"] == 0 and manifest["testsExecuted"] == 0,
                "Wrong native payload scope")
        expected = manifest["files"]
        require(0 < len(expected) <= MAX_FILES and sum(r["bytes"] for r in expected.values()) <= MAX_UNPACKED_BYTES,
                "Native payload bounds exceeded")
        for name, row in expected.items():
            safe_relative(name)
            require(isinstance(row["bytes"], int) and row["bytes"] >= 0
                    and isinstance(row["mode"], int) and row["mode"] & ~0o777 == 0,
                    "Invalid native file metadata")
        # Validate every member before creating any output tree.
        while True:
            member = archive.next()
            if member is None:
                break
            name = member.name
            safe_relative(name)
            require(member.isfile() and name in expected and name not in seen
                    and name.casefold() not in folded, "Unexpected, duplicate or nonregular native member")
            row = expected[name]
            require(member.size == row["bytes"] and member.mode == row["mode"], "Native member size or mode differs")
            h = hashlib.sha256()
            stream = archive.extractfile(member)
            for chunk in iter(lambda: stream.read(1024 ** 2), b""):
                h.update(chunk)
            require(h.hexdigest() == row["sha256"], "Archived native bytes differ: " + name)
            seen[name], total = True, total + member.size
            folded.add(name.casefold())
            require(total <= MAX_UNPACKED_BYTES, "Native payload expanded bound exceeded")
        require(set(seen) == set(expected), "Native payload closure is incomplete")
    if destination is not None:
        destination.mkdir(mode=0o700)
        with tarfile.open(path, "r:gz") as archive:
            for member in archive:
                if member.name == "payload-manifest.json":
                    continue
                target = destination.joinpath(*PurePosixPath(member.name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output, archive.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(1024 ** 2), b""):
                        output.write(chunk)
                row = expected[member.name]
                os.chmod(target, row["mode"])
                os.utime(target, ns=(row["mtimeNS"], row["mtimeNS"]))
                require(regular(target) == row, "Restored original input differs")
        (destination / "payload-manifest.json").write_bytes(manifest_bytes)
    return {"files": len(seen), "bytes": total, "payloadManifestSHA256": expected_manifest}
