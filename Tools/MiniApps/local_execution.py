"""Genuine local execution and immutable dual-engine native input.

The current producer retains its original failed graph preparation and its
actual successful native build plus current production-wrapper qualification.
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
PRIVATE_ROOT = Path("/Users/m1/builds/anytype-miniapps-original-recovery-20261125")


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
    from local_native_input import admit
    return admit(Path(app), Path(evidence), json.loads(POLICY.read_text()), digest(POLICY))


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


def select_runtime_pairs(inventory, runtime_identifier, select_pairs):
    selection_inventory = inventory
    if runtime_identifier is not None:
        require(re.fullmatch(r"com\.apple\.CoreSimulator\.SimRuntime\.iOS-27(?:-[0-9]+)+",
                             runtime_identifier), "An explicit original OS27 runtime identifier is required")
        selected_runtimes = [row for row in inventory["runtimes"]
                             if row.get("identifier") == runtime_identifier]
        require(len(selected_runtimes) == 1 and selected_runtimes[0].get("isAvailable") is True,
                "Requested actual runtime is unavailable or ambiguous")
        selection_inventory = {**inventory, "runtimes": selected_runtimes}
    runtime, devices = select_pairs(selection_inventory)
    require(runtime_identifier is None or runtime["identifier"] == runtime_identifier,
            "Actual compatible-device selection changed the requested runtime")
    return runtime, devices


def prepare(app, evidence, derived, *, runtime_identifier=None):
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
    runtime, devices = select_runtime_pairs(inventory, runtime_identifier, select_pairs)
    receipt = dict(status="PREFLIGHT_RUNNING_UI_NOT_RUN", source_sha=descriptor["source_sha"],
                   run_id=descriptor["run_id"], run_attempt="1", execution_origin="local-mac",
                   local_execution_sha256=digest(evidence / "local-execution.json"),
                   selected={}, ui_tests_executed=0, xcode=xcode, host_architecture=platform.machine(),
                   requested_runtime_identifier=runtime_identifier)
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
