#!/usr/bin/env python3
"""Build and install the separately identified full-file native candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import zipfile

import contract
import execution

BUILD_SCRIPT_BLOB = "4ebea60454865884284a6c34a903de00e2f0e53f"
GO_ARCHIVE_SHA = "91a44a2b8a716600ad94a4f143e156116620db8828086a6e3602291be9bd0bb4"


def archive_helper(control):
    return contract.load_module(control / contract.ARCHIVE_HELPER, "full_file_archive_format")


def source_inventory(root):
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
    result = {}
    for relative in sorted(filter(None, paths)):
        path = root / relative
        contract.require(not path.is_symlink(), "Native source symlink requires separate admission")
        result[relative] = contract.digest(path)
    contract.require(result, "Native source inventory is empty")
    return result


def committed_sources(manifest, any_root):
    result = {}
    for name, root in (("any", any_root), ("sdk", any_root / ".runtime-artifacts/sdk-source")):
        expected = manifest[name]
        contract.require(contract.git(root, "rev-parse", "HEAD") == expected["testedLocalCommit"]
                         and contract.git(root, "rev-parse", "HEAD^{tree}") == expected["testedEffectiveTree"]
                         and not contract.git(root, "diff", "HEAD", "--"),
                         "Native committed source changed: " + name)
        changed = set(contract.git(root, "diff", "--name-only", "--no-renames",
                                   expected["upstreamCommit"], "HEAD").splitlines())
        contract.require(changed == {entry["path"] for entry in expected["files"]},
                         "Native upstream overlay path set changed")
        for entry in expected["files"]:
            path = root / entry["path"]
            contract.require(path.stat().st_size == entry["bytes"] and contract.digest(path) == entry["sha256"]
                             and contract.git(root, "hash-object", "--path=" + entry["path"], entry["path"]) == entry["gitBlob"],
                             "Native source differs from tested input: " + entry["path"])
        untracked = contract.git(root, "ls-files", "--others", "--exclude-standard").splitlines()
        allowed = (".runtime-artifacts/", "build/", "dist/", "any.xcframework/") if name == "any" else ()
        contract.require(all(path.startswith(allowed) for path in untracked), "Unexpected native untracked source")
        # Go also sees ignored source files in imported directories. Admit no
        # untracked Go/C/header input outside the separate SDK/build trees.
        tracked = set(contract.git(root, "ls-files").splitlines())
        for path in root.rglob("*"):
            relative = path.relative_to(root).as_posix()
            if relative.startswith((".git/", *allowed)):
                continue
            if path.is_file() and path.suffix in (".go", ".c", ".h", ".s", ".syso"):
                contract.require(relative in tracked, "Untracked native compilation input")
        result[name] = dict(commit=expected["testedLocalCommit"], tree=expected["testedEffectiveTree"],
                            upstream_commit=expected["upstreamCommit"], files=source_inventory(root))
    return result


def validate_artifact(control, artifact, producer):
    _, manifest = contract.candidate(control)
    receipt_path = artifact / "native-artifact.json"
    receipt = json.loads(receipt_path.read_bytes())
    contract.require(receipt["status"] == contract.BUILD_PASS and receipt["execution_kind"] == "local-mac"
                     and receipt["version"] == contract.VERSION and receipt["producer_commit"] == producer
                     and receipt["source_manifest_sha256"] == contract.MANIFEST_SHA,
                     "Native artifact has the wrong source or local execution identity")
    # A Swift-only repair can consume this artifact, but cannot relabel native
    # source, its original producer, or the original build receipts.
    consumer = contract.git(control, "rev-parse", "HEAD")
    ancestry = subprocess.run(["git", "-C", str(control), "merge-base", "--is-ancestor", producer, consumer], capture_output=True)
    contract.require(ancestry.returncode == 0, "Native producer is not an ancestor of this consumer")
    for relative in (contract.MANIFEST, *(str(Path(contract.MANIFEST).parent / manifest[n]["patch"]) for n in ("any", "sdk"))):
        original = subprocess.check_output(["git", "-C", str(control), "show", producer + ":" + relative])
        contract.require(original == (control / relative).read_bytes(), "Native source input changed after build")
    for name in ("any", "sdk"):
        contract.require(receipt["sources"][name]["commit"] == manifest[name]["testedLocalCommit"]
                         and receipt["sources"][name]["tree"] == manifest[name]["testedEffectiveTree"],
                         "Native artifact source tree differs")
    archive = artifact / "any.xcframework.zip"
    native = archive_helper(control)
    contract.require(contract.digest(archive) == receipt["archive_sha256"]
                     and native.archive_files(archive) == receipt["files_sha256"],
                     "Native archive or its two actual slices changed")
    return receipt


def install(control, artifact, producer):
    receipt = validate_artifact(control, artifact, producer)
    vendor = control / "Modules/PinkhaAnyRuntime/Vendor"
    contract.require(not vendor.exists(), "Fresh isolated runtime Vendor directory required")
    vendor.mkdir(parents=True)
    native = archive_helper(control)
    with zipfile.ZipFile(artifact / "any.xcframework.zip") as archive:
        for member in archive.infolist():
            path = vendor / str(native.safe_relative(member.filename.rstrip("/")))
            if member.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, path.open("xb") as destination:
                    shutil.copyfileobj(source, destination, 1024 * 1024)
    shutil.copyfile(artifact / "native-artifact.json", vendor / "native-artifact.json")
    contract.save(vendor / "consumer-binding.json", dict(
        schema=1, status="SOURCE_IDENTICAL_FULL_FILE_NATIVE_ARTIFACT", producer_commit=producer,
        consumer_commit=contract.git(control, "rev-parse", "HEAD"),
        artifact_receipt_sha256=contract.digest(artifact / "native-artifact.json"),
        archive_sha256=receipt["archive_sha256"], source_manifest_sha256=contract.MANIFEST_SHA,
        test_results_relabeled=False))
    return receipt


def build(args, receipt, run):
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple ARM64 host required")
    contract.clean_source(args.control, args.expected_app_sha)
    _, manifest = contract.candidate(args.control)
    before = contract.snapshot(args.control)
    sources = committed_sources(manifest, args.any_root)
    contract.save(args.evidence / "control-source-before.json", before)
    contract.save(args.evidence / "native-source-before.json", sources)
    primary = None
    try:
        contract.require(not args.artifacts.exists(), "Preserve every previous native artifact")
        contract.require(not any((args.any_root / name).exists() for name in ("build", "dist", "any.xcframework")),
                         "Original native build script requires a fresh owned output tree")
        contract.require(contract.git(args.any_root, "hash-object", "scripts/build-xcframework.sh") == BUILD_SCRIPT_BLOB,
                         "Original native build script changed")
        installation = json.loads((args.go_root.parent / "installation.json").read_bytes())
        contract.require(installation["archive_sha256"] == GO_ARCHIVE_SHA
                         and installation["version"] == "go version go1.27.4 darwin/arm64",
                         "Pinned verified Apple Go toolchain required")
        environment = os.environ.copy()
        environment.update(PATH=str(args.go_root / "bin") + os.pathsep + environment["PATH"],
                           GOROOT=str(args.go_root), GOTOOLCHAIN="local", GOWORK="off",
                           GOMAXPROCS="2", GOMEMLIMIT="6GiB", GOFLAGS="-p=2 -mod=readonly",
                           GOCACHE=str(args.go_cache), GOMODCACHE=str(args.module_cache),
                           ANY_BUILD_VERSION=contract.VERSION, ANYSERVER_IOS_MIN_VERSION="18.4")
        args.go_cache.mkdir(parents=True, exist_ok=True)
        args.module_cache.mkdir(parents=True, exist_ok=True)
        version = run([str(args.go_root / "bin/go"), "version"], "go-version", env=environment, timeout=30)
        contract.require("go version go1.27.4 darwin/arm64" in version.read_text(), "Actual compiler version differs")
        run(["xcodebuild", "-version"], "xcode-version", timeout=30)
        run(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], "device-sdk-version", timeout=30)
        run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "simulator-sdk-version", timeout=30)
        run(["/bin/bash", "scripts/build-xcframework.sh", "dist"], "native-build-both-slices",
            cwd=args.any_root, env=environment, timeout=3600)
        archive = args.any_root / "dist/any.xcframework.zip"
        native = archive_helper(args.control)
        members = native.archive_files(archive)
        contract.require(committed_sources(manifest, args.any_root) == sources, "Native build source changed")
        args.artifacts.mkdir(parents=True)
        shutil.copyfile(archive, args.artifacts / archive.name)
        artifact = dict(status=contract.BUILD_PASS, execution_kind="local-mac", execution_uuid=args.execution_uuid,
                        producer_commit=args.expected_app_sha, version=contract.VERSION,
                        source_manifest_sha256=contract.MANIFEST_SHA, sources=sources,
                        archive_sha256=contract.digest(archive), files_sha256=members,
                        compiler_archive_sha256=GO_ARCHIVE_SHA,
                        compiler_binary_sha256=contract.digest(args.go_root / "bin/go"),
                        original_build_script_blob=BUILD_SCRIPT_BLOB, native_tests_executed=0,
                        apple_tests_executed=0, original_control_sources=before)
        contract.save(args.artifacts / "native-artifact.json", artifact)
        receipt.update(status=contract.BUILD_PASS, archive_sha256=artifact["archive_sha256"],
                       native_artifact_receipt_sha256=contract.digest(args.artifacts / "native-artifact.json"),
                       native_tests_executed=0, apple_tests_executed=0, source_trees={n:sources[n]["tree"] for n in sources})
    except BaseException as error:
        primary = error
        raise
    finally:
        contract.source_after(args.control, before, args.evidence, receipt, primary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "any-root", "artifacts", "evidence", "go-root", "go-cache", "module-cache"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--execution-uuid", required=True)
    args = parser.parse_args()
    for name in ("control", "any_root", "artifacts", "evidence", "go_root", "go_cache", "module_cache"):
        setattr(args, name, getattr(args, name).resolve())
    return execution.run_stage(args, build)


if __name__ == "__main__":
    raise SystemExit(main())
