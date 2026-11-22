#!/usr/bin/env python3
"""Verify an observed Apple dependency closure without updating any package.

This is a resolver-only maintenance lane. It cannot qualify a framework or
Native acceptance. The original build continues to require the committed lock.
"""
from pathlib import Path
import datetime
import hashlib
import io
import zipfile
import json
import os
import subprocess
import sys
import time

BASE = "3a33d083af7a4f087b37bf910904bb817e990ee0"
LOCK_PATH = "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
LOCK_BLOB = "b011914658931c21b97dcf14355d961ab6248b8f"
BRANCH = "refs/heads/codex/otzaria-original-editor-lock-origin-20261122"
LANE_FILES = {
    ".github/workflows/pinkha-original-editor-lock-origin.yml",
    "Tools/OriginalEditor/refresh_package_origin.py",
    "Tools/PinkhaNativeDerived/install_verified_heart.py",
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
    subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=root, check=True)
    changed = set(git("diff", "--name-only", BASE, "HEAD").splitlines())
    if changed != LANE_FILES or git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("resolver source has unreviewed changes")
    if git("rev-parse", "HEAD:" + LOCK_PATH) != LOCK_BLOB:
        raise ValueError("frozen lock changed before observation")
    installer_path = "Tools/PinkhaNativeDerived/install_verified_heart.py"
    original_installer = subprocess.check_output(["git", "show", BASE + ":" + installer_path], cwd=root).decode()
    prior_choice = "'codex/otzaria-original-editor-framework-v11-host-reviewed-20261122']"
    if original_installer.count(prior_choice) != 1:
        raise ValueError("unexpected original Heart branch allowlist")
    expected_installer = original_installer.replace(prior_choice,
        "'codex/otzaria-original-editor-framework-v11-host-reviewed-20261122',\n                             'codex/otzaria-original-editor-lock-origin-20261122']")
    if (root / installer_path).read_text() != expected_installer:
        raise ValueError("unreviewed Heart installer change")
    receipt["heart_installer_scope"] = "Original verifier unchanged; only this resolver branch admitted."
    xcode = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    machine = subprocess.check_output(["uname", "-m"], text=True).strip()
    if xcode != "Xcode 27.0\nBuild version 27A266a" or machine != "arm64":
        raise ValueError("unqualified resolver toolchain")
    receipt.update(xcode=xcode, machine=machine)
    lock = root / LOCK_PATH
    before_bytes = lock.read_bytes()
    before = json.loads(before_bytes)
    if set(before) != {"originHash", "pins", "version"} or before["version"] != 3 or len(before["pins"]) != 51:
        raise ValueError("unexpected original lock schema")
    review_dir = root / "docs/pinkha/torah-integration/evidence/original-editor-package-closure-20261122"
    original = json.loads((review_dir / "Original-44-Package.resolved").read_bytes())
    review = json.loads((review_dir / "SOURCE_CLOSURE_REVIEW.json").read_bytes())
    old_pins = {pin["identity"]: pin for pin in original["pins"]}
    candidate_pins = {pin["identity"]: pin for pin in before["pins"]}
    additions = {pin["identity"]: pin for pin in review["additional_pins"]}
    if len(old_pins) != 44 or len(additions) != 7 or set(old_pins) & set(additions):
        raise ValueError("invalid reviewed additive dependency closure")
    if candidate_pins != old_pins | additions:
        raise ValueError("candidate changed an original pin or invented an unreviewed addition")
    receipt["original_pin_count"] = 44
    receipt["original_pins_unchanged"] = True
    receipt["reviewed_additions"] = sorted(additions)
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
    # Reuse the already successful resolver, including its immutable archive.
    # Do not repeat it just because its observer incorrectly expected a changed
    # originHash. The still-missing check is strict resolution on a fresh runner.
    observed_run = 44973540287
    artifact_id = 14734653215
    artifact_sha = "40e34bd2e5549c9bc0dde527c024cbe3d37a6281189c28e0a0e14238c0ff41ff"
    prior_head = "19babeaafd9c24d2cdd1e514531084a05d83a996"
    endpoint = "/repos/davidpovarsky/anytype-swift/actions/"
    def api(path):
        return subprocess.check_output(["gh", "api", endpoint + path], cwd=root)
    run = json.loads(api("runs/" + str(observed_run)))
    artifact = json.loads(api("artifacts/" + str(artifact_id)))
    if run["head_sha"] != prior_head or run["status"] != "completed" or run["conclusion"] != "failure":
        raise ValueError("unexpected prior resolver run")
    if artifact["id"] != artifact_id or artifact["workflow_run"]["id"] != observed_run or artifact["expired"] or artifact["digest"] != "sha256:" + artifact_sha:
        raise ValueError("unexpected prior resolver artifact")
    archive_bytes = api("artifacts/" + str(artifact_id) + "/zip")
    if len(archive_bytes) != 19780 or sha(archive_bytes) != artifact_sha:
        raise ValueError("prior resolver artifact changed")
    (evidence / "original-observation-44973540287.zip").write_bytes(archive_bytes)
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    if archive.testzip() is not None:
        raise ValueError("prior resolver artifact failed CRC")
    prefix = "original-editor-lock-origin-evidence/"
    prior = json.loads(archive.read(prefix + "observation.json"))
    prior_command = json.loads(archive.read(prefix + "observe-resolver.command.json"))
    if prior["base_source"] != BASE or prior["source_sha"] != prior_head or prior["run_id"] != str(observed_run) or prior["error"] != "expected an observed new originHash":
        raise ValueError("prior observation does not describe this exact source")
    if prior_command["returncode"] != 0 or prior_command.get("timed_out", False):
        raise ValueError("prior Apple resolution did not succeed")
    if prior_command["command"] != [
        "xcodebuild", "-resolvePackageDependencies",
        "-project", "/Users/runner/work/anytype-swift/anytype-swift/Anytype.xcodeproj",
        "-scheme", "AnytypeOriginalEditor", "-configuration", "Debug-Anytype",
        "-clonedSourcePackagesDirPath", "/Users/runner/work/anytype-swift/anytype-swift/build/original-editor-lock-packages-44973540287",
        "-skipPackageUpdates",
    ]:
        raise ValueError("prior resolution used a foreign command")
    for kind in ("stdout", "stderr"):
        if sha(archive.read(prefix + "observe-resolver." + kind + ".log")) != prior_command[kind + "_sha256"]:
            raise ValueError("prior resolver log hash mismatch")
    if archive.read(prefix + "Package.before.resolved") != before_bytes or archive.read(prefix + "Package.after.resolved") != before_bytes:
        raise ValueError("candidate differs from the exact observed 51-pin lock")
    origin = before["originHash"]
    if not isinstance(origin, str) or len(origin) != 64 or any(c not in "0123456789abcdef" for c in origin):
        raise ValueError("invalid observed originHash")
    receipt["reused_successful_resolver"] = {
        "run_id": observed_run, "artifact_id": artifact_id,
        "archive_sha256": artifact_sha, "command_returncode": 0,
        "command_duration_seconds": prior_command["duration_seconds"],
        "resolution_rerun": False,
        "correction": "Xcode accepted the complete 51-pin closure without changing originHash; no changed hash is invented or required.",
    }
    command("strict-frozen-resolver", base_command + ["-onlyUsePackageVersionsFromResolvedFile"])
    after_bytes = lock.read_bytes()
    (evidence / "Package.after.resolved").write_bytes(after_bytes)
    receipt["after_sha256"] = sha(after_bytes)
    receipt["before_originHash"] = origin
    receipt["after_originHash"] = json.loads(after_bytes).get("originHash")
    receipt["origin_hash_changed"] = after_bytes != before_bytes
    if after_bytes != before_bytes:
        raise ValueError("strict resolver changed the exact observed lock")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("strict resolver mutated source")
    receipt["status"] = "PASS_OBSERVED_51_PIN_CLOSURE_44_ORIGINAL_UNCHANGED_STRICT_RESOLVER_ACCEPTED"
except Exception as exc:
    receipt["error_type"] = type(exc).__name__
    receipt["error"] = str(exc)
finally:
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json("observation.json", receipt)
    print(json.dumps(receipt, indent=2))
sys.exit(0 if receipt["status"].startswith("PASS_") else 1)
