"""Genuine local execution and immutable dual-engine native input.

The retained producer failed its original Swift probe. Its unchanged binary was
subsequently qualified against the actual generated and production wrappers.
Both original receipts are retained; neither grants original app acceptance.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
POLICY = HERE / "local_native_policy.json"
BRANCHES = {"codex/anytype-miniapps-final-20261125",
            "codex/anytype-miniapps-bridge-20261123"}
PRIVATE_ROOT = Path("/Users/m1/builds/anytype-miniapps-original-final-20261125")


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def git(root, *args):
    return subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(root), *args],
                                   text=True).strip()


def read_exact(root, row):
    path = Path(root) / row["path"]
    require(path.resolve() == path and path.is_file() and not path.is_symlink(),
            "Local native proof is missing or aliased")
    require(digest(path) == row["sha256"], "Local native proof bytes changed")
    return json.loads(path.read_text())


def identity(app, descriptor_path, expected_sha256):
    app, path = Path(app), Path(descriptor_path)
    require(app.is_absolute() and app.resolve() == app and not app.is_symlink()
            and path.is_absolute() and path.resolve() == path and not path.is_symlink(),
            "Local source or execution descriptor is aliased")
    require(app == PRIVATE_ROOT / "source" and path.is_relative_to(PRIVATE_ROOT / "evidence"),
            "Local execution must remain in its independently owned workspace")
    require(not any(os.environ.get(key) for key in
                    ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")),
            "Local execution must not impersonate a GitHub run")
    require(digest(path) == expected_sha256, "Local execution descriptor changed")
    value = json.loads(path.read_text())
    require(value["schema"] == "miniapps.original-local-execution/1"
            and value["execution_origin"] == "local-mac"
            and value["github_run_id"] is None and value["run_attempt"] == "1",
            "Unknown or relabelled local execution")
    require(value["run_id"] == "local-" + str(uuid.UUID(value["execution_uuid"])),
            "Local execution UUID differs")
    require(value["source_sha"] == git(app, "rev-parse", "HEAD")
            and value["source_branch"] == git(app, "branch", "--show-current")
            and value["source_branch"] in BRANCHES,
            "Local original source identity differs")
    require(value["source_root"] == str(app) and value["private_root"] == str(PRIVATE_ROOT),
            "Local source root differs")
    require(value["configuration"] == "Debug-MiniAppsOwner",
            "A generic upstream build cannot qualify the owner application")
    require(value["native_policy_sha256"] == digest(POLICY),
            "Local native source policy changed")
    return value


def native_input(app, evidence):
    app, evidence = Path(app).resolve(), Path(evidence).resolve()
    policy = json.loads(POLICY.read_text())
    require(policy["schema"] == "miniapps.original-local-native/1", "Unknown local native policy")
    root = Path(policy["root"])
    require(root.resolve() == root, "Local native producer root aliases another path")
    abi = read_exact(root, policy["abi_receipt"])
    original = read_exact(root, policy["original_build_receipt"])
    files = read_exact(root, policy["framework_inventory"])
    require(abi["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
            and abi["frameworkUnchanged"] is True and abi["sourceUnchanged"] is True
            and abi["originalProducerFailurePreserved"] is True
            and abi["originalProducerReceiptSHA256"] == policy["original_build_receipt"]["sha256"],
            "The actual corrected ABI evidence lost its original producer")
    require(original["status"] == "FAIL"
            and original["failure"]["message"] == "actual_command_failed:generated-actual-swift-entry-typecheck",
            "The original failed probe must retain its true outcome")
    require(abi["sourceManifestSHA256"] == original["sourceManifestSHA256"]
            == policy["source_manifest_sha256"]
            and abi["sourcePins"] == original["sourcePins"] == policy["source_pins"]
            and abi["independentGoRuntimeCount"] == original["independentGoRuntimeCount"] == 1
            and original["sourceFilesVerified"] == 4852,
            "Original combined native source or Go ownership differs")
    require(digest(root / "source/source-manifest.json") == policy["source_manifest_sha256"]
            and digest(root / "native-source.tar.gz") == policy["source_archive_sha256"]
            and original["sourceArchiveSHA256"] == policy["source_archive_sha256"],
            "Native source archive/manifest bytes changed")
    require(digest(root / "Lib.xcframework.zip") == policy["archive_sha256"]
            and abi["archiveSHA256"] == policy["archive_sha256"]
            and abi["binarySHA256"] == policy["binary_sha256"]
            and abi["frameworkInventorySHA256"] == policy["framework_inventory"]["sha256"],
            "Native binary/archive provenance differs")
    bind = [row for row in abi["originalNativeCommands"] if row["name"] == "combined-gomobile-bind"]
    require(len(bind) == 1 and bind[0]["exitCode"] == 0
            and bind[0]["status"] == "PASS_EXIT_0"
            and "-target=iossimulator/arm64" in bind[0]["argv"],
            "No successful original arm64 simulator native build")
    probes = {row["name"]: row for row in abi["commands"]}
    require(set(probes) == {"sdk", "generated-actual-swift-entry-typecheck",
                            "actual-production-protobuf-wrapper-typecheck"}
            and all(row["exitCode"] == 0 for row in probes.values()),
            "The actual generated and production Swift ABI probes did not pass")
    for name, row in probes.items():
        log = root / "swift-abi-qualification" / (name + ".log")
        require(log.is_file() and digest(log) == row["logSHA256"],
                "Original ABI compiler log changed: " + name)
    framework = app / "Dependencies/Middleware/Lib.xcframework"
    require(framework.is_dir() and framework.resolve().is_relative_to(app),
            "The original application must own its exact native artifact copy")
    actual = {}
    for path in sorted(framework.rglob("*")):
        require(not path.is_symlink(), "Native framework contains an unreviewed alias")
        if path.is_file():
            actual[str(path.relative_to(framework))] = {
                "bytes": path.stat().st_size, "sha256": digest(path)}
    require(actual == files, "The installed native framework differs from all original qualified members")
    for name, row in abi["productionWrapperInputs"]["files"].items():
        path = app / "Modules/ProtobufMessages/Sources" / name
        require(path.is_file() and path.stat().st_size == row["bytes"]
                and digest(path) == row["sha256"], "Actual original native wrapper changed: " + name)
    require(not os.environ.get("PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE"),
            "The production combined runtime cannot use a fixture library")
    heart_marker = "pinkha-dual-runtime-v1-" + policy["source_manifest_sha256"]
    require(abi["heartRuntimeVersion"] == heart_marker
            and abi["anyRuntimeVersion"] == "v0.5.0-pinkha.dual.1-" + policy["source_manifest_sha256"],
            "Combined engine runtime identities differ")
    installation = {
        "status": "VERIFIED_EXACT_NATIVE_INPUT_APP_ACCEPTANCE_PENDING",
        "execution_origin": "local-mac", "github_run_id": None,
        "source_sha": git(app, "rev-parse", "HEAD"),
        "policy_sha256": digest(POLICY), "native_source_manifest_sha256": policy["source_manifest_sha256"],
        "abi_receipt_sha256": policy["abi_receipt"]["sha256"],
        "original_failed_receipt_sha256": policy["original_build_receipt"]["sha256"],
        "native_framework_files": actual, "original_native_acceptance_tests": 0,
        "current_native_tests_executed": 0, "original_editor_sdk_abi_reused": False}
    binding = {"runtime_profile": policy["runtime_profile"], "native_marker": heart_marker,
               "native_source_manifest_sha256": policy["source_manifest_sha256"],
               "native_binary_sha256": policy["binary_sha256"],
               "native_abi_receipt_sha256": policy["abi_receipt"]["sha256"],
               "independent_go_runtime_count": 1, "execution_origin": "local-mac"}
    write(evidence / "local-native-input.json", installation)
    return installation, binding


def test_environment(receipt):
    values = {"PINKHA_MINIAPPS_EXECUTION_KIND": receipt["execution_origin"],
              "PINKHA_MINIAPPS_SOURCE_SHA": receipt["source_sha"],
              "PINKHA_MINIAPPS_EXECUTION_ID": receipt["run_id"]}
    if receipt["execution_origin"] == "github-actions":
        values.update(GITHUB_SHA=receipt["source_sha"], GITHUB_RUN_ID=receipt["run_id"],
                      GITHUB_RUN_ATTEMPT=receipt["run_attempt"])
    else:
        require(receipt["execution_origin"] == "local-mac"
                and receipt["run_id"].startswith("local-"), "Unknown local test execution")
    return values


def prepare(app, evidence, derived):
    app, evidence, derived = map(lambda x: Path(x).resolve(), (app, evidence, derived))
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "Genuine local Apple silicon preflight is required")
    require(app == PRIVATE_ROOT / "source" and evidence.is_relative_to(PRIVATE_ROOT / "evidence")
            and derived.is_relative_to(PRIVATE_ROOT) and not derived.is_relative_to(app)
            and not evidence.exists(), "Unowned or stale local execution paths")
    require(git(app, "branch", "--show-current") in BRANCHES
            and not git(app, "diff", "--name-only", "HEAD"), "Unreviewed or dirty local source")
    require(not any(os.environ.get(k) for k in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")),
            "Local preflight cannot reuse GitHub identity variables")
    from owner_signing import verify as verify_owner
    from acceptance_profile import resolve_profile
    from prepare_sdk import verify as verify_sdk
    owner = verify_owner(app, require_profile_grants=False)
    profile = resolve_profile(app, "miniapps-native", git(app, "branch", "--show-current"),
                              local_execution=True)
    require(profile is not None, "Local original five-method profile is not selected")
    pin = json.loads((app / "Tools/MiniApps/producer.json").read_text())
    require(verify_sdk(app / "Dependencies/Hanlin")["revision"] == pin["revision"],
            "Prepared shared source differs from actual companion pin")
    evidence.mkdir(parents=True)
    native_input(app, evidence)
    local_uuid = str(uuid.uuid4())
    descriptor = dict(schema="miniapps.original-local-execution/1", execution_origin="local-mac",
                      github_run_id=None, execution_uuid=local_uuid, run_id="local-" + local_uuid,
                      run_attempt="1", source_sha=git(app, "rev-parse", "HEAD"),
                      source_branch=git(app, "branch", "--show-current"), source_root=str(app),
                      private_root=str(PRIVATE_ROOT), derived=str(derived), evidence=str(evidence),
                      configuration=owner["configuration"], native_policy_sha256=digest(POLICY),
                      created_at=datetime.now(timezone.utc).isoformat())
    write(evidence / "local-execution.json", descriptor)
    sys.path.insert(0, str(app / "Tools/PinkhaSimulatorGate"))
    from preflight import select_pairs
    xcode = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    require(re.match(r"Xcode 27(?:\.|\s)", xcode), "Actual Xcode27 is required")
    inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "--json"]))
    runtime, devices = select_pairs(inventory)
    receipt = dict(status="PREFLIGHT_RUNNING_UI_NOT_RUN", source_sha=descriptor["source_sha"],
                   run_id=descriptor["run_id"], run_attempt="1", execution_origin="local-mac",
                   local_execution_sha256=digest(evidence / "local-execution.json"),
                   selected={}, ui_tests_executed=0, xcode=xcode, host_architecture=platform.machine())
    write(evidence / "preflight/simulator-inventory.json", inventory)
    for kind, device in devices.items():
        name = "Pinkha-UI27-" + descriptor["run_id"] + "-" + kind
        udid = subprocess.check_output(["xcrun", "simctl", "create", name,
                                       device["identifier"], runtime["identifier"]], text=True).strip()
        require(re.fullmatch(r"[A-Fa-f0-9-]{36}", udid), "Invalid owned simulator identity")
        receipt["selected"][kind] = dict(udid=udid, name=name, device=device, runtime=runtime)
        write(evidence / "preflight/preflight.json", receipt)
    receipt.update(status="PREFLIGHT_PASS_UI_NOT_RUN", finished_at=datetime.now(timezone.utc).isoformat())
    write(evidence / "preflight/preflight.json", receipt)
    return descriptor
