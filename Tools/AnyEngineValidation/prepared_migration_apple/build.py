#!/usr/bin/env python3
"""Build the exact prepared candidate with the original two-slice native script."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys

import contract
import execution

BUILD_SCRIPT_BLOB = "4ebea60454865884284a6c34a903de00e2f0e53f"


def execute(args, receipt, run):
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Xcode ARM64 producer required")
    contract.clean_source(args.control, args.expected_app_sha)
    native, manifest = contract.candidate(args.control)
    before = contract.snapshot(args.control)
    contract.save(args.evidence / "control-source-before.json", before)
    primary = None
    try:
        contract.require(not args.artifacts.exists(), "Fresh native artifact output required")
        contract.require(contract.git(args.any_root, "hash-object", "scripts/build-xcframework.sh") == BUILD_SCRIPT_BLOB,
                         "Original pinned native build script changed")
        environment = os.environ.copy()
        environment.update(ANY_BUILD_VERSION=contract.VERSION, ANYSERVER_IOS_MIN_VERSION="18.4",
                           GOTOOLCHAIN="local", GOMAXPROCS="4", GOFLAGS="-p=4", GOWORK="off")
        run(["xcodebuild", "-version"], "xcode-version", timeout=30)
        run(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"], "device-sdk-version", timeout=30)
        run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "simulator-sdk-version", timeout=30)
        run(["go", "version"], "go-version", env=environment, timeout=30)
        helper = [sys.executable, "-B", str(args.control / contract.HELPER),
                  "--manifest", str(args.control / contract.MANIFEST)]
        run([*helper, "apply", "--any-root", str(args.any_root), "--output", str(args.evidence / "native-source.json")],
            "apply-exact-native-candidate", env=environment, timeout=180)
        applied = json.loads((args.evidence / "native-source.json").read_bytes())
        contract.require(applied["version"] == contract.VERSION
                         and applied["sourceManifestSHA256"] == contract.MANIFEST_SHA, "Native application receipt differs")
        run(["/bin/bash", "scripts/build-xcframework.sh", "dist"], "native-build-both-slices",
            cwd=args.any_root, env=environment, timeout=3600)
        run([*helper, "record", "--any-root", str(args.any_root), "--output", str(args.artifacts)],
            "record-exact-native-artifact", env=environment, timeout=300)
        artifact = json.loads((args.artifacts / "native-artifact.json").read_bytes())
        contract.require(artifact["sourceCommit"] == args.expected_app_sha
                         and artifact["version"] == contract.VERSION
                         and artifact["sourceManifestSHA256"] == contract.MANIFEST_SHA
                         and artifact["sources"] == applied["sources"], "Built runtime source identity differs")
        contract.require(native.verify_source(manifest, args.control / contract.MANIFEST, args.any_root) == applied["sources"],
                         "Native inputs changed while building")
        receipt.update(version=contract.VERSION, manifest_sha256=contract.MANIFEST_SHA,
                       native_artifact_receipt_sha256=contract.digest(args.artifacts / "native-artifact.json"),
                       archive_sha256=contract.digest(args.artifacts / "any.xcframework.zip"),
                       native_source_receipt_sha256=contract.digest(args.evidence / "native-source.json"),
                       original_native_build_script_git_blob=BUILD_SCRIPT_BLOB,
                       artifact_name=contract.artifact_name(receipt["run_id"], receipt["run_attempt"], args.expected_app_sha),
                       native_tests_executed=0, apple_tests_executed=0,
                       original_control_sources=before)
    except BaseException as error:
        primary = error
        raise
    finally:
        contract.source_after(args.control, before, args.evidence, receipt, primary)
    receipt["status"] = contract.BUILD_PASS
    contract.save(args.artifacts / "native-build.json", receipt)
    for name in ("control-source-before.json", "control-source-after.json", "native-source.json"):
        shutil.copyfile(args.evidence / name, args.artifacts / name)


def preflight(args):
    contract.clean_source(args.control, args.expected_app_sha)
    reuse = contract.reuse_inputs(args.native_artifact_run_id, args.native_artifact_run_attempt, args.native_producer_commit)
    run_id = args.native_artifact_run_id if reuse else os.environ.get("GITHUB_RUN_ID")
    attempt = args.native_artifact_run_attempt if reuse else os.environ.get("GITHUB_RUN_ATTEMPT")
    commit = args.native_producer_commit if reuse else args.expected_app_sha
    name = contract.artifact_name(run_id, attempt, commit)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write("reuse=" + str(reuse).lower() + "\nartifact_name=" + name + "\n")
    print(json.dumps(dict(reuse=reuse, artifact_name=name, manifest_sha256=contract.MANIFEST_SHA)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--preflight", action="store_true")
    for name in ("native-artifact-run-id", "native-artifact-run-attempt", "native-producer-commit"):
        parser.add_argument("--" + name, default="")
    for name in ("any-root", "artifacts", "evidence"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    args.control = args.control.resolve()
    if args.preflight:
        return preflight(args)
    for name in ("any_root", "artifacts", "evidence"):
        contract.require(getattr(args, name) is not None, "Build output/source path required")
        setattr(args, name, getattr(args, name).resolve())
    return execution.run_stage(args, execute)


if __name__ == "__main__":
    raise SystemExit(main())
