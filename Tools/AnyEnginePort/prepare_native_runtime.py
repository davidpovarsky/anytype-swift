#!/usr/bin/env python3
"""Build provenance and strict installation for the patched Any iOS runtime."""
from __future__ import annotations
import argparse, hashlib, json, os, plistlib, shutil, stat, subprocess, tempfile, zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-source.json"
VERSION = "v0.5.0-pinkha.1"
# The SDK v0.8.0 annotated tag object and its checkout commit are pinned
# separately; compare actual HEAD to the peeled commit.
PINNED_COMMITS = {"any": "88fae2e5ae7d0f46d6707567a3123081faa8de9a",
                  "sdk": "854df54cdadd76006ae823cbd1b1d923138356d0"}

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def read_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data["any"]["upstreamCommit"] == "88fae2e5ae7d0f46d6707567a3123081faa8de9a", "Unexpected Any base")
    require(data["sdk"]["upstreamCommit"] == "854df54cdadd76006ae823cbd1b1d923138356d0", "Unexpected SDK base")
    require(data["sdk"]["upstreamTagObject"] == "b161a0475479bbe7d9d693bc496c6fdd90c3969b", "Unexpected SDK tag object")
    return data

def safe_relative(value):
    path = PurePosixPath(value)
    require(value and "\\" not in value and not path.is_absolute() and ".." not in path.parts, "Unsafe relative path")
    return path

def verify_source(manifest, manifest_path, any_root):
    result = {}
    for name, root in (("any", any_root), ("sdk", any_root / ".runtime-artifacts/sdk-source")):
        spec = manifest[name]
        require(git(root, "rev-parse", "HEAD") == PINNED_COMMITS[name], name + " upstream changed")
        expected = {entry["path"] for entry in spec["files"]}
        changed = set(git(root, "diff", "--name-only", "--no-renames", "HEAD").splitlines())
        require(changed == expected, name + " changed path set differs from manifest")
        for entry in spec["files"]:
            path = str(safe_relative(entry["path"]))
            require(git(root, "hash-object", "--path=" + path, path) == entry["gitBlob"], name + " file differs: " + path)
        patch = manifest_path.parent / safe_relative(spec["patch"])
        require(digest(patch) == spec["patchSHA256"], name + " patch digest mismatch")
        if "testedEffectiveTree" in spec:
            require(git(root, "write-tree") == spec["testedEffectiveTree"], name + " effective source tree differs")
        result[name] = {"upstreamCommit": spec["upstreamCommit"], "resolvedUpstreamCommit": PINNED_COMMITS[name], "patchSHA256": spec["patchSHA256"],
                        "upstreamTagObject": spec.get("upstreamTagObject"), "testedLocalCommit": spec["testedLocalCommit"], "files": spec["files"]}
        for key in ("testedEffectiveTree", "testedWorkingTreeIncludesUncommittedV8Changes"):
            if key in spec:
                result[name][key] = spec[key]
    return result

def apply(args):
    manifest = read_manifest(args.manifest)
    for name, root in (("any", args.any_root), ("sdk", args.any_root / ".runtime-artifacts/sdk-source")):
        spec = manifest[name]
        require(git(root, "rev-parse", "HEAD") == PINNED_COMMITS[name], name + " is not at exact base")
        require(not git(root, "diff", "HEAD", "--"), name + " source must start clean")
        patch = args.manifest.parent / safe_relative(spec["patch"])
        require(digest(patch) == spec["patchSHA256"], name + " patch digest mismatch")
        subprocess.run(["git", "-C", str(root), "apply", "--check", "--index", str(patch)], check=True)
        subprocess.run(["git", "-C", str(root), "apply", "--index", str(patch)], check=True)
    receipt = {"schemaVersion": 1, "version": VERSION, "sourceManifestSHA256": digest(args.manifest),
               "sources": verify_source(manifest, args.manifest, args.any_root)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Verified and applied both immutable native overlays.")

def archive_files(archive):
    files = {}
    total = 0
    with zipfile.ZipFile(archive) as z:
        require(len(z.infolist()) <= 5000, "Unexpected artifact entry count")
        for member in z.infolist():
            path = safe_relative(member.filename.rstrip("/"))
            require(path.parts[0] == "any.xcframework", "Unexpected archive root")
            require(not stat.S_ISLNK(member.external_attr >> 16), "Symbolic links are not allowed in this static library artifact")
            total += member.file_size
            require(total <= 1024 * 1024 * 1024, "Artifact exceeds bounded extraction size")
            if member.is_dir():
                continue
            require(str(path) not in files, "Duplicate archive member")
            files[str(path)] = hashlib.sha256(z.read(member)).hexdigest()
        info = plistlib.loads(z.read("any.xcframework/Info.plist"))
        libraries = info.get("AvailableLibraries", [])
        require(len(libraries) == 2, "Expected device and simulator slices")
        variants = set()
        for lib in libraries:
            require(lib["SupportedPlatform"] == "ios" and lib["SupportedArchitectures"] == ["arm64"], "Unexpected library platform")
            variant = lib.get("SupportedPlatformVariant", "device")
            variants.add(variant)
            prefix = "any.xcframework/" + str(safe_relative(lib["LibraryIdentifier"])) + "/"
            require(prefix + str(safe_relative(lib["LibraryPath"])) in files, "Missing archive slice")
            headers = prefix + str(safe_relative(lib["HeadersPath"])) + "/"
            header = z.read(headers + "anylib.h").decode("utf-8")
            for symbol in ("AnyLibVersion", "AnyLibStartWithMode", "AnyLibStop", "AnyLibStopNow"):
                require(symbol in header, "Missing exported C ABI " + symbol)
            module = z.read(headers + "module.modulemap").decode("utf-8")
            require("module AnyLib" in module, "Wrong Swift import module")
        require(variants == {"device", "simulator"}, "Both iOS variants are required")
    return files

def record(args):
    manifest = read_manifest(args.manifest)
    sources = verify_source(manifest, args.manifest, args.any_root)
    archive = args.any_root / "dist/any.xcframework.zip"
    files = archive_files(archive)
    require(os.environ.get("ANY_BUILD_VERSION") == VERSION, "Native build version was not explicitly selected")
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / archive.name
    shutil.copy2(archive, destination)
    receipt = {"schemaVersion": 1, "version": VERSION, "sourceCommit": git(ROOT, "rev-parse", "HEAD"),
               "sourceManifestSHA256": digest(args.manifest), "sources": sources,
               "archive": archive.name, "archiveSHA256": digest(destination), "filesSHA256": files,
               "toolchain": {"go": subprocess.check_output(["go", "version"], text=True).strip(),
                             "xcode": subprocess.check_output(["xcodebuild", "-version"], text=True).strip(),
                             "iphoneosSDK": subprocess.check_output(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], text=True).strip()}}
    (args.output / "native-artifact.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status":"BUILT_SOURCE_VERIFIED", "archiveSHA256":receipt["archiveSHA256"], "version":VERSION}))

def install(args):
    manifest = read_manifest(args.manifest)
    receipt = json.loads((args.artifact / "native-artifact.json").read_text(encoding="utf-8"))
    require(receipt["schemaVersion"] == 1 and receipt["version"] == VERSION, "Unrecognized native artifact")
    require(receipt["sourceCommit"] == git(ROOT, "rev-parse", "HEAD"), "Artifact belongs to another application commit")
    require(receipt["sourceManifestSHA256"] == digest(args.manifest), "Source manifest does not match artifact")
    for name in ("any", "sdk"):
        require(receipt["sources"][name]["upstreamCommit"] == manifest[name]["upstreamCommit"] and
                receipt["sources"][name]["patchSHA256"] == manifest[name]["patchSHA256"], "Native source pin mismatch")
    archive = args.artifact / safe_relative(receipt["archive"])
    require(digest(archive) == receipt["archiveSHA256"], "Archive SHA256 mismatch")
    require(archive_files(archive) == receipt["filesSHA256"], "Archive member digest mismatch")
    vendor = ROOT / "Modules/PinkhaAnyRuntime/Vendor"
    require(not vendor.exists(), "Refusing to replace an existing Vendor tree; use a clean checkout")
    vendor.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".native-install-", dir=vendor.parent))
    try:
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                relative = safe_relative(member.filename.rstrip("/"))
                target = stage / relative
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as f:
                        f.write(z.read(member))
        shutil.copy2(args.artifact / "native-artifact.json", stage / "native-artifact.json")
        stage.rename(vendor)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print("Installed exact source-bound native artifact; select PINKHA_ANY_NATIVE_ARTIFACT=verified-v1.")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    sub = p.add_subparsers(dest="command", required=True)
    for name, function in (("apply", apply), ("record", record)):
        s = sub.add_parser(name)
        s.add_argument("--any-root", type=Path, required=True)
        s.add_argument("--output", type=Path, required=True)
        s.set_defaults(function=function)
    s = sub.add_parser("install")
    s.add_argument("--artifact", type=Path, required=True)
    s.set_defaults(function=install)
    args = p.parse_args()
    args.manifest = args.manifest.resolve()
    if hasattr(args, "any_root"):
        args.any_root = args.any_root.resolve()
    args.function(args)

if __name__ == "__main__":
    main()
