#!/usr/bin/env python3
"""Restore the exact qualified Hanlin source and run its original dependency preparation.

This owns a fresh isolated checkout and logs only. It does not build the app,
run XCTest, modify another checkout, recover a missing binary, or claim a pass
from the prior producer. The next original build is a separate actual phase.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from owned_commands import run_logged

SOURCE = "86a6dde354947be9329fe1e8f4d45a433fe488c4"
CONFIG_SHA = "03d96d520f785e34d85b643e31bcb4a424e46e76a81c6b4c245f91eaac3e110f"
HOST_SHA = "540507770659f00b8424b394c0c3857f52001cd13a0dc2bc3b38f313b385303a"
DIFF_SHA = "863bf97e4b83fe9824be5345a7fcb2453f403a50d16ce3fdbc0c1c978b5482ab"
ORIGINAL_DRIVER_SHA = "0070ab53ebc486c4df2a722cdd74b036bb5cf002aa72e772813ffaa434dbf23a"

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def require(value, message):
    if not value:
        raise ValueError(message)

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.chmod(path, 0o600)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--original-git", type=Path, required=True)
    parser.add_argument("--restored-source", type=Path, required=True)
    parser.add_argument("--original-identity", type=Path, required=True)
    parser.add_argument("--identity-sha256", required=True)
    parser.add_argument("--prepared-diff", type=Path, required=True)
    args = parser.parse_args()
    require(platform.system() == "Darwin" and platform.machine() == "arm64" and os.getuid() == 501,
            "Actual authorized Apple Silicon m1 session required")
    parent = Path("/Users/m1/development/anytype-root-active-20261125")
    require(args.root.parent == parent and parent.resolve() == parent and not args.root.exists(),
            "A new protected root owned by this recovery is required")
    require(args.original_git.is_dir() and args.restored_source.is_dir(), "Existing original source/git unavailable")
    require(digest(args.original_identity) == args.identity_sha256 and digest(args.prepared_diff) == DIFF_SHA,
            "Original retained source evidence differs")
    expected = json.loads(args.original_identity.read_bytes())
    require(expected["commit"] == SOURCE and len(expected["tracked_file_sha256"]) == 7693,
            "Complete original source identity is required")
    config = args.restored_source / "Config.xcconfig"
    host = args.restored_source / "build/runtime-host/RuntimeHostResources.zip"
    require(digest(config) == CONFIG_SHA and digest(host) == HOST_SHA, "Actual canonical configuration/host differs")
    source_head = subprocess.check_output(["git", "-C", str(args.restored_source), "rev-parse", "HEAD"], text=True).strip()
    require(source_head == SOURCE, "Restored original source HEAD changed")
    original_status = subprocess.check_output(["git", "-C", str(args.restored_source), "status", "--porcelain=v1", "-z"])
    node = Path("/Users/m1/builds/_preflight/native-owned-node245-20261125/node-v24.5.0-darwin-arm64/bin")
    require((node / "node").is_file(), "Original qualified Node toolchain unavailable")
    os.environ.update(PATH=str(node) + ":/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                      PYTHONDONTWRITEBYTECODE="1",
                      DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    require(subprocess.check_output(["node", "--version"], text=True).strip() == "v24.5.0", "Node version differs")
    args.root.mkdir(mode=0o700)
    evidence = args.root / "preparation"; evidence.mkdir(mode=0o700)
    source = args.root / "source"
    state = {"schema": "pinkha.original-companion-recovery-preparation/1", "status": "RUNNING",
             "source": SOURCE, "startedAt": datetime.now(timezone.utc).isoformat(),
             "originalIdentitySHA256": args.identity_sha256, "originalDiffSHA256": DIFF_SHA,
             "originalSource": str(args.restored_source), "isolatedSource": str(source),
             "appBuilds": 0, "nativeTests": 0, "originalBinaryRecovered": False, "steps": []}

    def command(label, argv, cwd, timeout):
        result = run_logged(list(map(str, argv)), cwd, evidence / (label + ".log"), timeout)
        record = json.loads((evidence / (label + ".command.json")).read_bytes())
        state["steps"].append({"label": label, "returncode": result.returncode,
                               "receiptSHA256": digest(evidence / (label + ".command.json")),
                               "logSHA256": record["log_sha256"]})
        save(evidence / "STATE.json", state)
        require(result.returncode == 0, "Original dependency command failed: " + label)

    def verify_source():
        mismatches = []
        for name, wanted in expected["tracked_file_sha256"].items():
            path = source / name
            require(path.resolve().is_relative_to(source), "Original source escaped isolated checkout")
            if not path.is_file() or digest(path) != wanted:
                mismatches.append(name)
        require(not mismatches, "Original prepared source differs: " + repr(mismatches[:12]))
        require(subprocess.check_output(["git", "-C", str(source), "diff", "--binary", "HEAD"]) == args.prepared_diff.read_bytes(),
                "Prepared tracked diff changed")
        require(digest(source / "Scripts/ProductSplit/run_native_acceptance.py") == ORIGINAL_DRIVER_SHA,
                "Original producer acceptance driver changed")
        require(digest(source / "Config.xcconfig") == CONFIG_SHA
                and digest(source / "AI_HLY/RuntimeHostResources.zip") == HOST_SHA
                and digest(source / "build/runtime-host/RuntimeHostResources.zip") == HOST_SHA,
                "Canonical configuration/runtime resource changed")

    try:
        free = shutil.disk_usage(args.root).free
        state["capacity"] = {"freeBytes": free, "preparationGrowthBytes": 8_000_000_000,
                             "concurrentGrowthAllowanceBytes": 10_000_000_000, "marginBytes": 5_000_000_000}
        require(free >= 23_000_000_000, "Actual phase growth/concurrency capacity unavailable")
        command("clone-isolated-git", ["git", "clone", "--no-hardlinks", "--no-checkout", str(args.original_git), str(source)], args.root, 180)
        command("checkout-original", ["git", "-c", "advice.detachedHead=false", "checkout", "--detach", SOURCE], source, 60)
        command("apply-exact-original-preparation", ["git", "apply", "--binary", str(args.prepared_diff)], source, 60)
        shutil.copy2(config, source / "Config.xcconfig")
        for target in (source / "AI_HLY/RuntimeHostResources.zip", source / "build/runtime-host/RuntimeHostResources.zip"):
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(host, target)
        verify_source()
        state["sourceBefore"] = {"files": 7693, "status": "EXACT_ORIGINAL_PREPARED_SOURCE"}
        for label, argv in (
            ("install-nativescript", ["node", "Scripts/MiniApps/install-tooling.mjs", "--engine=nativescript", "--ignore-scripts"]),
            ("prepare-nativescript", ["npm", "run", "prepare:ios-dependencies", "--prefix", "Scripts/NativeScript"]),
            ("install-expo", ["node", "Scripts/MiniApps/install-tooling.mjs", "--engine=expo", "--ignore-scripts"]),
            ("prepare-expo", ["node", "Scripts/Expo/prepare-ios-dependencies.mjs"]),
            ("prepare-expo-types", ["node", "Scripts/Expo/prepare-types.mjs"]),
        ):
            state["activeStep"] = label; save(evidence / "STATE.json", state)
            command(label, argv, source, 1200)
        verify_source()
        state["status"] = "EXACT_SOURCE_AND_ORIGINAL_DEPENDENCIES_PREPARED_BUILD_NOT_RUN"
    except BaseException as error:
        state["status"] = "FAILED"
        state["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        same = source_head == subprocess.check_output(["git", "-C", str(args.restored_source), "rev-parse", "HEAD"], text=True).strip()
        same = same and original_status == subprocess.check_output(["git", "-C", str(args.restored_source), "status", "--porcelain=v1", "-z"])
        state["existingCheckoutUnchanged"] = same
        if not same: state["status"] = "FAILED_EXISTING_CHECKOUT_CHANGED"
        state["finishedAt"] = datetime.now(timezone.utc).isoformat()
        save(evidence / "RESULT.json", state)
        print(json.dumps({key: state[key] for key in ("status", "source", "appBuilds", "nativeTests", "existingCheckoutUnchanged")}), flush=True)
    require(state["status"] == "EXACT_SOURCE_AND_ORIGINAL_DEPENDENCIES_PREPARED_BUILD_NOT_RUN", "Preparation was not accepted")

if __name__ == "__main__":
    main()
