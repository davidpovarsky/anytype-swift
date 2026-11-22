#!/usr/bin/env python3
"""Observe an Apple-generated originHash without authorizing any package update.

This is a resolver-only maintenance lane. It cannot qualify a framework or
Native acceptance. The original build continues to require the committed lock.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

BASE = "8d80a2754c1a21597ef6ac65c5ad01a3204909b1"
LOCK_PATH = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
LOCK_BLOB = "93172ce5fe62007a1620f7e64866e3b59338dc58"
BRANCH = "refs/heads/codex/otzaria-original-editor-lock-origin-20261122"
LANE_FILES = {
    ".github/workflows/pinkha-original-editor-lock-origin.yml",
    "Tools/OriginalEditor/refresh_package_origin.py",
}
root = Path(__file__).resolve().parents[2]
evidence = root / os.environ["LOCK_EVIDENCE"]
evidence.mkdir(parents=True, exist_ok=False)
receipt = {
    "schema": 1, "status": "FAIL", "base_source": BASE,
    "source_sha": os.environ.get("GITHUB_SHA"),
    "run_id": os.environ.get("GITHUB_RUN_ID"),
    "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
    "scope": "APPLE_RESOLVER_METADATA_ONLY_NO_FRAMEWORK_OR_NATIVE_ACCEPTANCE",
    "framework_builds": 0, "native_tests_executed": 0,
}
def git(*args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
def sha(data):
    return hashlib.sha256(data).hexdigest()
def write_json(name, value):
    (evidence / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
def command(name, argv):
    result = {
        "command": argv, "cwd": str(root), "timeout_seconds": 900,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    start = time.monotonic()
    try:
        with (evidence / (name + ".stdout.log")).open("wb") as stdout, (evidence / (name + ".stderr.log")).open("wb") as stderr:
            proc = subprocess.run(argv, cwd=root, stdout=stdout, stderr=stderr, timeout=900)
            result["returncode"] = proc.returncode
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
        raise
    finally:
        result["duration_seconds"] = time.monotonic() - start
        for kind in ("stdout", "stderr"):
            data = (evidence / (name + "." + kind + ".log")).read_bytes()
            result[kind + "_sha256"] = sha(data)
        write_json(name + ".command.json", result)
    if proc.returncode:
        raise ValueError(name + " failed: " + str(proc.returncode))
try:
    if os.environ.get("GITHUB_REF") != BRANCH or git("rev-parse", "HEAD") != receipt["source_sha"]:
        raise ValueError("foreign source or branch")
    if git("rev-parse", "HEAD^") != BASE:
        raise ValueError("resolver lane is not directly based on recorded failed producer")
    changed = set(git("diff", "--name-only", BASE, "HEAD").splitlines())
    if changed != LANE_FILES or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("resolver source has unreviewed changes")
    if git("rev-parse", "HEAD:" + LOCK_PATH) != LOCK_BLOB:
        raise ValueError("frozen lock changed before observation")
    xcode = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    machine = subprocess.check_output(["uname", "-m"], text=True).strip()
    if xcode != "Xcode 27.0\nBuild version 27A266a" or machine != "arm64":
        raise ValueError("unqualified resolver toolchain")
    receipt.update(xcode=xcode, machine=machine)
    lock = root / LOCK_PATH
    before_bytes = lock.read_bytes()
    before = json.loads(before_bytes)
    if set(before) != {"originHash", "pins", "version"} or before["version"] != 3 or len(before["pins"]) != 44:
        raise ValueError("unexpected original lock schema")
    (evidence / "Package.before.resolved").write_bytes(before_bytes)
    receipt["before_sha256"] = sha(before_bytes)
    receipt["pin_count"] = len(before["pins"])
    package_dir = root / "build" / ("original-editor-lock-packages-" + receipt["run_id"])
    base_command = [
        "xcodebuild", "-resolvePackageDependencies",
        "-project", str(root / "Anytype.xcodeproj"),
        "-scheme", "AnytypeOriginalEditor", "-configuration", "Debug-Anytype",
        "-clonedSourcePackagesDirPath", str(package_dir), "-skipPackageUpdates",
    ]
    command("observe-resolver", base_command)
    after_bytes = lock.read_bytes()
    after = json.loads(after_bytes)
    (evidence / "Package.after.resolved").write_bytes(after_bytes)
    receipt["after_sha256"] = sha(after_bytes)
    receipt["before_originHash"] = before["originHash"]
    receipt["after_originHash"] = after.get("originHash")
    if set(after) != set(before) or after["version"] != before["version"] or after["pins"] != before["pins"]:
        raise ValueError("resolver changed frozen pin identity, location, revision, version, or order")
    origin = after["originHash"]
    if not isinstance(origin, str) or len(origin) != 64 or any(c not in "0123456789abcdef" for c in origin) or origin == before["originHash"]:
        raise ValueError("expected an observed new originHash")
    if git("diff", "--name-only").splitlines() != [LOCK_PATH] or git("ls-files", "--others", "--exclude-standard"):
        raise ValueError("resolver mutated a source other than the lock")
    command("strict-frozen-resolver", base_command + ["-onlyUsePackageVersionsFromResolvedFile"])
    if lock.read_bytes() != after_bytes:
        raise ValueError("strict resolver changed observed lock")
    if git("diff", "--name-only").splitlines() != [LOCK_PATH] or git("ls-files", "--others", "--exclude-standard"):
        raise ValueError("strict resolver mutated another source")
    (evidence / "observed-origin-only.patch").write_text(git("diff", "--", LOCK_PATH) + "\n")
    receipt["status"] = "PASS_ORIGIN_ONLY_44_PINS_UNCHANGED_STRICT_RESOLVER_ACCEPTED"
except Exception as exc:
    receipt["error_type"] = type(exc).__name__
    receipt["error"] = str(exc)
finally:
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json("observation.json", receipt)
    print(json.dumps(receipt, indent=2))
sys.exit(0 if receipt["status"].startswith("PASS_") else 1)
