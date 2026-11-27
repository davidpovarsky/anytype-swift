#!/usr/bin/env python3
"""Materialize immutable canonical Hanlin packages without touching a producer checkout.

Usage: python3 Tools/Hanlin/prepare_sdk.py --source /path/to/hanlin-ai
The source must already contain the pinned commit. This script never fetches,
checks out, resets, stages, commits or changes that repository's working files.
Run before Xcode resolves Anytype.xcodeproj's nested local package references.
"""

import argparse
import hashlib
import io
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import sys


ROOT = Path(__file__).resolve().parents[2]
PIN = json.loads((Path(__file__).with_name("source.json")).read_text())
DESTINATION = ROOT / "Dependencies" / "Hanlin"
MARKER = ".pinkha-source.json"


def git(source, *arguments):
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(source), *arguments], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("A dependency snapshot cannot contain symbolic links")
        if path.is_file() and path != directory / MARKER:
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def component_definition(source):
    component = PIN.get("assistantCapabilities")
    if component is None:
        return None
    if component.get("product") != "HanlinAssistantCapabilities" or component.get("layout") != "nested":
        raise ValueError("Unreviewed original assistant component")
    def original(name):
        return git(source, "show", PIN["revision"] + ":" + name)
    for name, digest in component["generatedFiles"].items():
        if hashlib.sha256(original(name)).hexdigest() != digest:
            raise ValueError("Generated assistant input differs from its reviewed pin: " + name)
    receipt = json.loads(original(component["receiptPath"]))
    if receipt.get("packageLayout") != "nested" or receipt.get("selectedProducts") != ["HanlinAssistantCapabilities"]:
        raise ValueError("Assistant component does not preserve original nested ownership")
    if set(receipt.get("nestedPackages", [])) != set(PIN["packages"]):
        raise ValueError("Original nested package closure differs")
    for name, digest in receipt["inputs"].items():
        if hashlib.sha256(original(name)).hexdigest() != digest:
            raise ValueError("Assistant manifest generator input differs: " + name)
    sources = receipt.get("applicationSourceSHA256")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Original assistant source closure is missing")
    for name, digest in sources.items():
        if hashlib.sha256(original(name)).hexdigest() != digest:
            raise ValueError("Original assistant source differs: " + name)
    profile = json.loads(original(component["profilePath"]))
    paths = list(PIN["packages"]) + list(component["generatedFiles"]) + [
        "Scripts/SDK/native_artifacts.py", "Scripts/Runtime/runtime_host_archive.py"]
    paths += ["AI_HLY/" + name for name in profile["sourceDirectories"]]
    paths += ["AI_HLY/" + name for name in profile["additionalSources"]]
    paths += [name for name in receipt["applicationResourcePaths"] if name != "AI_HLY/RuntimeHostResources.zip"]
    return component, sorted(set(paths))


def prepare_native_inputs(source, stage, component, cache):
    """Reuse the original publisher, archive validator and owned product copier."""
    catalog_path = Path(__file__).with_name("assistant_native_artifacts.json")
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != component["nativeCatalogSHA256"]:
        raise ValueError("Original published native catalog differs from its reviewed pin")
    spec = importlib.util.spec_from_file_location("hanlin_original_native_artifacts", stage / "Scripts/SDK/native_artifacts.py")
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    catalog = native.load_catalog(catalog_path)
    if catalog["state"] != "published":
        raise ValueError("Original native dependencies require published readback evidence")
    if native.verify_source_inputs(catalog, source) != PIN["revision"]:
        raise ValueError("Original prepared native source revision differs")
    # The existing exporter validates aliases inside each owned product and
    # materializes them as independent files. No snapshot alias escapes to a
    # producer checkout or another app's prepared dependency.
    sys.path.insert(0, str(ROOT / "Tools/OriginalEditor"))
    from framework_products import copy_product
    records = native.selected_records(catalog, ["NodeMobile", "Python"], True)
    receipts = []
    for item in records:
        archive = native.download(item, cache)
        with tempfile.TemporaryDirectory(prefix="hanlin-native-", dir=stage.parent) as temporary:
            extracted = Path(temporary)
            native.extract_verified(archive, item["checksum"], extracted, item["root"])
            payload = extracted / item["root"]
            if item["kind"] == "xcframework":
                observed = native.framework_libraries(payload, item["target"])
                if observed != item["libraries"]:
                    raise ValueError("Original native slice closure differs: " + item["target"])
                names = [item["installPath"]]
            else:
                names = item["installPaths"]
            if item["target"] == "HanlinNodeHostSupport":
                native.validate_node_support(source, payload / "AI_HLY/RuntimeHostResources.zip", PIN["revision"])
            for name in names:
                origin = payload if item["kind"] == "xcframework" else payload / name
                copy_product(origin, stage / name, extracted)
            receipts.append({"target": item["target"], "checksum": item["checksum"], "paths": names})
    if git(source, "rev-parse", "HEAD").decode().strip() != PIN["revision"]:
        raise ValueError("Native preparation source changed during materialization")
    return {"releaseTag": catalog["releaseTag"], "catalogSHA256": component["nativeCatalogSHA256"],
            "artifacts": receipts}


def verify(directory):
    record = json.loads((directory / MARKER).read_text())
    if record.get("revision") != PIN["revision"] or record.get("files") != hashes(directory):
        raise ValueError("Existing Hanlin snapshot differs from its pin; preserve it and inspect manually")
    for package in PIN["packages"]:
        if not (directory / package / "Package.swift").is_file():
            raise ValueError("Canonical nested package is absent: " + package)
    component = PIN.get("assistantCapabilities")
    if component is not None:
        if record.get("assistantCapabilities") != component:
            raise ValueError("Assistant component source binding differs")
        manifest = directory / "Package.swift"
        expected = component["generatedFiles"][component["manifestPath"]]
        if not manifest.is_file() or hashlib.sha256(manifest.read_bytes()).hexdigest() != expected:
            raise ValueError("Generated original assistant manifest differs")
        native = record.get("nativeInputs", {})
        if native.get("catalogSHA256") != component["nativeCatalogSHA256"] or not native.get("artifacts"):
            raise ValueError("Original native inputs have no bound receipt")
    return record


def materialize(source, native_cache=None):
    resolved = git(source, "rev-parse", PIN["revision"] + "^{commit}").decode().strip()
    if resolved != PIN["revision"]:
        raise ValueError("Unexpected Hanlin source revision")
    if DESTINATION.exists():
        verify(DESTINATION)
        return
    definition = component_definition(source)
    paths = definition[1] if definition else PIN["packages"]
    archive = git(source, "archive", "--format=tar", PIN["revision"], *paths)
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hanlin-prepare-", dir=DESTINATION.parent) as temporary:
        stage = Path(temporary) / "snapshot"
        stage.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            for member in bundle:
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or not (member.isfile() or member.isdir()):
                    raise ValueError("Unsafe entry in canonical dependency archive")
                target = stage.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                stream = bundle.extractfile(member)
                if stream is None:
                    raise ValueError("Missing archived dependency file")
                data = stream.read()
                if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                    raise ValueError("Pinned Hanlin archive needs a producer-provided LFS materialization")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        extra = {}
        if definition:
            component, _ = definition
            (stage / "Package.swift").write_bytes((stage / component["manifestPath"]).read_bytes())
            native_receipt = prepare_native_inputs(source, stage, component,
                native_cache or DESTINATION.parent / ".hanlin-native-cache")
            extra = {"assistantCapabilities": component, "nativeInputs": native_receipt}
        record = {"revision": PIN["revision"], "files": hashes(stage), **extra}
        (stage / MARKER).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        verify(stage)
        stage.rename(DESTINATION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--native-cache", type=Path,
                        help="Owned cache for the original published Node/Python artifacts")
    options = parser.parse_args()
    if options.check:
        verify(DESTINATION)
    elif options.source:
        materialize(options.source, options.native_cache)
    else:
        parser.error("--source is required when preparing the snapshot")
    print("Verified Hanlin " + PIN["revision"] + " at " + str(DESTINATION))


if __name__ == "__main__":
    main()
