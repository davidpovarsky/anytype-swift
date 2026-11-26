"""Continue the original Heart fixture with exact observed installation metadata.

All original failures remain separate. Every installed path and content byte must
match the producer, with only the pinned189 original installer mode differences.
No install, resign, chmod, account restoration, or fixture extension is performed.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import time
import traceback

sys.dont_write_bytecode = True
import combined_heart_semantics_gateway as c
import retain_owned_heart_account as account
import resume_prepared_heart_6f as original
import retry_prepared_heart_6f_install as installed
import resume_relocated_heart_6f as relocated

CORE = "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
RETENTION = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
SOURCE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
ADMISSION = "82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
ORIGINAL = Path("/Users/m1/builds/e-combined-current-20261125/fresh-header6f-attempt1")
PRIOR = Path("/Users/m1/builds/e-combined-current-20261125/prepared-header6f-relocated-continuation1")
ORIGINAL_CONTROLLER = "376cd194fe168675b48b2e9158d87825fe46f4a96d1f02e2c56f9078b9e9e0f7"
PRIOR_EXECUTION = "e1b36d602ef86017f534b0d498f7f24b5948757bcc4327720351d2dbbef4ab29"
PRIOR_BACKUP = "fd92b60b1e9ec759065f8f4d458a286a51569ec7f29af91e6f6e9a5c22183e6c"
ORIGINAL_FIXTURE = "143d71e3127d44a2f7827571a5776f6e36556813cde62dba1e6b5038a4c03294"
ORIGINAL_PLIST = "8932347055911cd9b56a865ddfe61e9619071801f8ff23a21e6b8cb9997bdb26"
RELOCATION_CONTROLLER = "4dcec8861c176bbbe2d779b1e9e9c7f5c4d068b95ecf957f786367b590eed536"
ORIGINAL_APP_INVENTORY = "31d85d7d83bf7c36ad260400b449abe8825db07de123ffaae14b19ea24456212"
INSTALLED_APP_INVENTORY = "d21ddd6ebc6af61a115d6dffc1d1e642c24bee337f6b1c03881d53df33f63f7c"
INSTALL_MODE_DELTA = "2d7cd5a138e74f147df3c66c006699b3de88041c7f7fc201d337ef7f82b521c2"
INSTALL_CONTROLLER = "c79b64a500a9ee65969bcf9eb5bb3fe7be23ab7e3f452a969485c98110a2bd74"
BEFORE_INSTALL = "3faa2ed4bc921f2cd21bdb6b0b21a6e6dcefc080f7d899836cd4e86c2e143fc9"
AFTER_INSTALL = "c60fe83b092c99093634cc257809203c4ccdd1c4efe93847c521ca9c282cc7a9"
DEVICE = "A4489891-C78A-4E78-8649-6E9525A7FDB5"

# These aliases let the entire five-stage execution/verification sequence remain
# byte-exact to the reviewed original controller. No predicate is rewritten.
require, app_file, decode, sha, write = c.require, c.app_file, c.decode, c.sha, c.write
continuation_ui, continuation_native, STAGES = c.continuation_ui, c.continuation_native, c.STAGES
CAPTURE, REOPEN = c.CAPTURE, c.REOPEN


def admit_prior(admission):
    require(c.digest(Path(relocated.__file__)) == RELOCATION_CONTROLLER,
            "Exact original relocation continuation authority required")
    relocation_failure, preparation = relocated.admit_prior(admission)
    path = PRIOR / "evidence/execution.json"
    require(c.digest(path) == PRIOR_EXECUTION, "Exact original installed-mode gate failure required")
    prior = decode(c.raw(path))
    require(prior["status"] == "FAIL" and prior["sourceCommit"] == admission["sourceCommit"] == SOURCE
            and prior["controllerSHA256"] == RELOCATION_CONTROLLER and prior["coreControllerSHA256"] == CORE
            and prior["priorExecutionSHA256"] == relocated.PRIOR_EXECUTION
            and prior["nativeManifestSHA256"] == c.MANIFEST and prior["heartOverlaySHA256"] == c.OVERLAY
            and prior["ownedSimulator"] == DEVICE and prior["binding"] == preparation["binding"],
            "Original installed-mode/relocation/launch/preparation authority differs")
    require(prior["stages"] == {} and prior["actualMethodsInvokedInThisContinuation"] == 0
            and prior["actualInvocationStartedEvidence"] == {}
            and prior["firstFailure"] == {"message": "Every installed original App byte and mode must match the admitted producer",
                                          "type": "ValueError"}
            and prior["preparationMethodsReexecuted"] == prior["fixtureRestorations"]
            == prior["fixtureDeadlineChanges"] == prior["newSimulatorsCreated"] == prior["installationsInThisContinuation"] == 0,
            "Only the exact before-test installed-mode gate failure is admitted")
    require(not list((PRIOR / "commands").glob("*-test/started.json")),
            "No original test may have started in the installed-mode attempt")
    diagnostic = PRIOR / "private/installed-app-comparison-diagnostic"
    require(c.digest(diagnostic / "receipt.json")
            == "44c862fc7d6f7d22e06e2f46ac2aebcfe12e11c8f9b3be61724156dbb151a45f"
            and c.digest(diagnostic / "original.json") == ORIGINAL_APP_INVENTORY
            and c.digest(diagnostic / "installed.json") == INSTALLED_APP_INVENTORY
            and c.digest(diagnostic / "mode-delta.json") == INSTALL_MODE_DELTA,
            "The original read-only installed-App comparison changed")
    original_app = decode(c.raw(diagnostic / "original.json"))
    installed_app = decode(c.raw(diagnostic / "installed.json"))
    delta = decode(c.raw(diagnostic / "mode-delta.json"))
    require(len(original_app) == len(installed_app) == 3494 and set(original_app) == set(installed_app)
            and len(delta) == 189, "Exact original installed paths and mode map required")
    actual_delta = {}
    for name, expected in original_app.items():
        actual = installed_app[name]
        require({k:v for k,v in expected.items() if k != "mode"}
                == {k:v for k,v in actual.items() if k != "mode"},
                "Any installed content/type/target difference is forbidden")
        if expected != actual:
            actual_delta[name] = {"originalMode": expected["mode"], "installedMode": actual["mode"],
                                  "kind": expected["kind"]}
    require(actual_delta == delta, "Only the exact observed189 mode changes are admitted")
    counts = {(kind, before, after): sum(row == {"kind":kind,"originalMode":before,"installedMode":after}
                                       for row in delta.values())
              for kind, before, after in (("file",493,420),("file",384,420),("directory",448,493))}
    require(counts == {("file",493,420):136,("file",384,420):29,("directory",448,493):24},
            "Unexpected installed permission transition")
    cleanup = prior["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True or row.get("present") is False
                    for row in cleanup["groups"]), "Original mode-gate attempt cleanup incomplete")
    require(c.digest(PRIOR / "private/final-sandbox-originals" / c.FIXTURE) == ORIGINAL_FIXTURE
            and c.digest(PRIOR / "private/owned-account-originals/device.plist") == ORIGINAL_PLIST,
            "Current unchanged fixture and actual final device seal are required")
    require(prior["originalPreparationReused"]["actual"] == preparation["stages"]["preparation"]["actual"]
            and prior["originalPreparationReused"]["executedInThisContinuation"] is False,
            "Original preparation must remain separately attributed")
    return prior, preparation

def admit_shutdown_account(commands, prior):
    directory = PRIOR / "private/owned-account-originals"
    c.require(c.digest(directory / "retention.json") == PRIOR_BACKUP, "Exact original account seal required")
    backup = c.decode(c.raw(directory / "retention.json"))
    c.require(backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == PRIOR_EXECUTION and backup["device"] == DEVICE
              and backup["fixtureDeadlineChanged"] is False and backup["restoredFixtures"] == 0,
              "Original backup identity/scope differs")
    log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "admit-owned-shutdown", 30)
    matches = [row for row in c.decode(c.raw(log))["devices"].get(c.RUNTIME, []) if row.get("udid") == DEVICE]
    c.require(len(matches) == 1 and matches[0]["state"] == "Shutdown"
              and matches[0]["name"] == "E-Combined-Heart-" + prior["binding"]["nonce"]
              and matches[0]["deviceTypeIdentifier"] == c.DEVICE, "Exact original owned shutdown device required")
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    c.require(device_root.resolve() == device_root and device_root.is_dir()
              and c.digest(device_root / "device.plist") == c.digest(directory / "device.plist"),
              "Original device metadata changed since seal")
    def identity(path):
        entry = os.lstat(path)
        c.require(path.resolve() == path and not stat.S_ISLNK(entry.st_mode), "Owned root became an alias")
        return (entry.st_dev, entry.st_ino, entry.st_mode)
    root_identity = identity(device_root)
    plist_identity = identity(device_root / "device.plist")
    plist_sha256 = c.digest(directory / "device.plist")
    def require_same_shutdown(stage):
        c.require(device_root.resolve() == device_root and device_root.is_dir()
                  and identity(device_root) == root_identity
                  and identity(device_root / "device.plist") == plist_identity
                  and c.digest(device_root / "device.plist") == plist_sha256,
                  "Original sealed device was replaced or its metadata changed")
        log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], stage, 30)
        rows = [row for row in c.decode(c.raw(log))["devices"].get(c.RUNTIME, []) if row.get("udid") == DEVICE]
        c.require(len(rows) == 1 and rows[0]["state"] == "Shutdown"
                  and rows[0]["name"] == "E-Combined-Heart-" + prior["binding"]["nonce"]
                  and rows[0]["deviceTypeIdentifier"] == c.DEVICE,
                  "The sealed owned device changed state during admission")
        for label, live in roots.items():
            expected = root_identities[label]
            if expected is None:
                c.require(not live.exists() and not live.is_symlink(), "Absent account root appeared")
            else:
                c.require(identity(live) == expected, "Original private account root was replaced")
    command_root = PRIOR / "commands/final-private-sandbox-container"
    command = c.decode(c.raw(command_root / "result.json"))
    c.require(command["argv"] == ["xcrun", "simctl", "get_app_container", DEVICE, "io.anytype.app", "data"]
              and command["status"] == "PASS_COMMAND" and command["exitCode"] == 0
              and command["logSHA256"] == c.digest(command_root / "original.log"),
              "Original observed app container command differs")
    app = Path(c.raw(command_root / "original.log").decode().strip())
    c.require(app.resolve() == app and app.parent == device_root / "data/Containers/Data/Application",
              "Original account container is not canonical")
    roots = {"application-data": app, "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains", "device-preferences": device_root / "data/Library/Preferences"}
    root_identities = {name: identity(live) if live.exists() else None for name, live in roots.items()}
    for name, live in roots.items():
        require_same_shutdown("admit-before-" + name)
        row = backup["scopes"][name]
        if row["status"] == "NOT_PRESENT":
            c.require(not live.exists() and not live.is_symlink(), "An absent owned scope appeared")
            require_same_shutdown("admit-after-absent-" + name)
            continue
        manifest = directory / (name + "-before.json")
        c.require(c.digest(manifest) == row["manifestSHA256"], "Original account manifest changed")
        expected = c.decode(c.raw(manifest))
        c.require(account.inventory(live) == expected == account.inventory(directory / name),
                  "The live original account or sealed backup changed")
        require_same_shutdown("admit-after-" + name)
    require_same_shutdown("admit-final-original-shutdown")
    return {"status": "EXACT_SEALED_ORIGINAL_SHUTDOWN_ACCOUNT", "backupSHA256": PRIOR_BACKUP,
            "devicePlistSHA256": plist_sha256, "deviceRootIdentityUnchanged": True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    args = parser.parse_args()
    own = Path(__file__).resolve().parent
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    require(c.digest(Path(__file__)) == args.controller_sha256 and c.digest(Path(c.__file__)) == CORE
            and c.digest(Path(account.__file__)) == RETENTION,
            "Exact reviewed continuation, core and private retention required")
    require(args.admission.is_absolute() and args.admission.resolve() == args.admission
            and c.digest(args.admission) == ADMISSION, "Exact same-source 6f admission required")
    admission = decode(c.raw(args.admission))
    require(admission["controllerSHA256"] == CORE and admission["sourceCommit"] == SOURCE
            and admission["nativeManifestSHA256"] == c.MANIFEST and admission["heartOverlaySHA256"] == c.OVERLAY,
            "Actual combined source/runtime admission differs")
    prior, preparation = admit_prior(admission)
    require(args.root.is_absolute() and args.root.parent == PRIOR.parent
            and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
            "Fresh separately owned continuation root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", c.raw(args.admission))
    c.write_bytes(evidence / "original-preparation-execution.json", c.raw(ORIGINAL / "evidence/execution.json"))
    c.write_bytes(evidence / "original-launch-failure-execution.json", c.raw(installed.PRIOR / "evidence/execution.json"))
    c.write_bytes(evidence / "original-installation-relocation-failure.json", c.raw(relocated.PRIOR / "evidence/execution.json"))
    c.write_bytes(evidence / "original-installed-mode-failure.json", c.raw(PRIOR / "evidence/execution.json"))
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; boot_owned = False
    binding = prior["binding"]
    device = DEVICE
    result = {"status": "FAIL", "protocol": "pinkha-original-preparation-exact-installed-mode-continuation-v1",
              "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": SOURCE,
              "controllerSHA256": args.controller_sha256, "coreControllerSHA256": CORE,
              "observationHelperSHA256": c.OBSERVATION_HELPER,
              "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
              "ownedSimulator": DEVICE, "binding": binding, "stages": {},
              "priorExecutionSHA256": PRIOR_EXECUTION, "priorBackupSHA256": PRIOR_BACKUP,
              "originalPreparationReused": {"path": str(ORIGINAL), "actual": preparation["stages"]["preparation"]["actual"],
                                            "executedInThisContinuation": False},
              "appBuilds": 0, "nativeBuilds": 0, "uiBuilds": 0, "factoryMethodsExecuted": 0,
              "preparationMethodsReexecuted": 0, "fixtureRestorations": 0, "fixtureDeadlineChanges": 0,
              "originalMountedLaunchFailurePreserved": True, "originalActualMountedFailedTests": 1,
              "originalInstallationRelocationFailurePreserved": True, "installationsInThisContinuation": 0,
              "originalInstalledModeFailurePreserved": True, "chmodOperations": 0,
              "newSimulatorsCreated": 0, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
              "startedAt": time.time()}
    try:
        result["accountAdmission"] = admit_shutdown_account(commands, prior)
        result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts")
        native = c.native = importlib.import_module("consumer_contract")
        mounted = c.mounted = importlib.import_module("mounted_contract")
        boundary = c.boundary = importlib.import_module("page154_boundary")
        policy = importlib.import_module("page154_contract")
        warning = importlib.import_module("warning_profile")
        specialized = importlib.import_module("combined_heart_observations_gateway")
        require(c.digest(Path(specialized.__file__)) == c.OBSERVATION_HELPER
                and specialized.COMBINED_VERSION == c.VERSION and specialized.ORIGINAL_OVERLAY == c.OVERLAY,
                "Exact original combined observation authority required")
        native.binding(binding)
        fixture_raw = c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE)
        require(sha(fixture_raw) == ORIGINAL_FIXTURE, "Original prepared fixture changed")
        fixture = decode(fixture_raw)
        mounted.fixture(fixture, binding)
        result["originalFixtureSHA256"] = ORIGINAL_FIXTURE
        result["originalFixtureCreatedAt"] = fixture["createdAt"]
        result["originalFixtureExpiryUnix"] = fixture["createdAt"] + 978307200 + 7200
        # Claim cleanup ownership before boot: a post-exit infrastructure error
        # must still shut down this positively admitted original device.
        boot_owned = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-boot", 180)
        actual_fixture = c.app_file(commands, DEVICE, private, c.FIXTURE, "original-live-fixture", 65536)
        require(actual_fixture == fixture_raw, "Live original prepared fixture differs after boot")
        mounted.fixture(decode(actual_fixture), binding)
        # The actual failed launch did not reach selection or capture. Native
        # capture/reopen witnesses must remain absent before the affected retry.
        log, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"],
                              "admit-original-unrun-sandbox", 30)
        container = Path(c.raw(log, 4096).decode().strip())
        require(container.resolve() == container and container.is_relative_to(
                Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE), "Wrong live account container")
        for filename in (c.CAPTURE, c.REOPEN, *boundary.FILES.values()):
            require(prior["finalPrivateSandbox"]["files"][filename]["status"] == "NOT_PRESENT"
                    and not (container / "Library/Application Support" / filename).exists()
                    and not (container / "Library/Application Support" / filename).is_symlink(),
                    "A native mutation witness appeared after the launch failure")
        # The original explicit installation already succeeded. Admit the exact
        # observed new container and the installed original binary without any
        # second installation, restoration, signing, or fixture mutation.
        original_container = c.raw(relocated.PRIOR / "commands/verify-installed-original-account/original.log", 4096).decode().strip()
        require(str(container) == original_container,
                "The observed original relocated container changed again")
        installed_log, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "app"],
                                        "verify-already-installed-original-app", 30)
        installed_app = Path(c.raw(installed_log, 4096).decode().strip())
        expected_parent = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE / "data/Containers/Bundle/Application"
        require(installed_app.resolve() == installed_app and installed_app.name == "Anytype.app"
                and installed_app.parent.parent == expected_parent,
                "Installed App is not the actual owned simulator bundle")
        original_app_inventory, installed_app_inventory = c.inventory(app), c.inventory(installed_app)
        original_manifest = PRIOR / "private/installed-app-comparison-diagnostic/original.json"
        installed_manifest = PRIOR / "private/installed-app-comparison-diagnostic/installed.json"
        require(c.digest(original_manifest) == ORIGINAL_APP_INVENTORY
                and c.digest(installed_manifest) == INSTALLED_APP_INVENTORY
                and original_app_inventory == decode(c.raw(original_manifest))
                and installed_app_inventory == decode(c.raw(installed_manifest)),
                "Every original and installed byte/mode must match its exact observed manifest")
        write(private / "installed-original-app-inventory.json", installed_app_inventory)
        result["originalInstallationRelocationQualified"] = {
            "originalExecutionSHA256": relocated.PRIOR_EXECUTION,
            "originalInstallationCommandSHA256": c.digest(relocated.PRIOR / "commands/install-exact-original-app/result.json"),
            "beforeInventorySHA256": BEFORE_INSTALL, "afterInventorySHA256": AFTER_INSTALL,
            "byteAndModeIdenticalEntries": 125, "exactRemovedOSSnapshotFiles": 9,
            "accountDataChangedEntries": 0, "containerMetadataIdentical": True,
            "installedAppVerifiedEntries": len(installed_app_inventory),
            "byteIdenticalInstalledPaths": 3494, "exactObservedModeChanges": 189,
            "originalModeDeltaSHA256": INSTALL_MODE_DELTA, "chmodOperations": 0,
            "installedAppInventorySHA256": c.digest(private / "installed-original-app-inventory.json"),
            "installationsInThisContinuation": 0, "resigningOperations": 0,
            "productIntegrity": c.product_integrity(built["app"])}
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        def run(name, additions):
            require(name in ("mounted", "linked-ui", "linked-native", "unlinked-ui", "unlinked-native"),
                    "Only the five original unrun stages are allowed")
            mounted.fixture(fixture, binding)
            kind = "app" if STAGES[name].startswith("AnytypeTests/") else "ui"
            value = c.stage(commands, evidence, name, built[kind], app, binding, device, dict(base, **additions))
            result["stages"][name] = value
            require(value["status"] == "PASS", name + " actual method failed")

        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        run("mounted", ui_env)
        capture_raw = app_file(commands, device, private, CAPTURE, "preserve-capture", 65536)
        reopen_raw = app_file(commands, device, private, REOPEN, "preserve-reopen", 65536)
        capture, reopen = decode(capture_raw), decode(reopen_raw)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        witness = capture.get("nativeBoundaryEvidence")
        require(isinstance(witness, dict) and witness.get("protocolVersion") == 1 and witness.get("extraNativeCalls") == 0
                and witness.get("source") == "actual-client-call-results" and set(witness["files"]) == set(boundary.FILES), "original three native boundaries required")
        boundaries = {}
        for role, filename in boundary.FILES.items():
            row = witness["files"][role]
            require(row["filename"] == filename, "native boundary filename differs")
            payload = app_file(commands, device, private, filename, "preserve-boundary-" + role.lower(), boundary.MAXIMUM)
            require(len(payload) == row["bytes"] and sha(payload) == row["sha256"], "native boundary original hash differs")
            boundaries[role] = payload
        result["nativeBoundaryComparison"] = boundary.verify(boundaries, fixture, capture, native, mounted)
        require(result["nativeBoundaryComparison"]["projectionFieldCount"] == 9, "full original nine-field projection required")
        result["originalAttachments"] = policy.mounted_attachments(evidence / "mounted/private-attachments", device, capture, reopen, binding, warning)
        write(evidence / "actual-mounted-qualified.json", {"binding": binding, "mounted": result["mountedProof"], "boundary": result["nativeBoundaryComparison"]})
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = sha(payload)
        previous, previous_raw = None, None
        for phase in ("linked", "unlinked"):
            if previous_raw is not None:
                source_env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"] = sha(previous_raw)
            run(phase + "-ui", dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE=phase))
            ui_raw, ui_origin = policy.attachment(evidence / (phase + "-ui") / "private-attachments", "heart-semantic-source-ui-" + phase,
                                                STAGES[phase + "-ui"], device, maximum=65536)
            result[phase + "UIProof"] = continuation_ui(decode(ui_raw), phase, fixture, capture, capture_raw, reopen_raw)
            native_env = dict(source_env, PINKHA_SEMANTIC_SOURCE_READBACK_PHASE=phase,
                              PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_JSON=ui_raw.decode(), PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_SHA256=sha(ui_raw))
            run(phase + "-native", native_env)
            native_raw = app_file(commands, device, private, "pinkha-semantic-source-" + phase + "-native-readback.json", "preserve-" + phase + "-readback")
            attached, origin = policy.attachment(evidence / (phase + "-native") / "private-attachments", "heart-semantic-source-native-" + phase,
                                                 STAGES[phase + "-native"], device, maximum=65536)
            value = decode(native_raw)
            proof = continuation_native(value, decode(attached), native_raw, phase, fixture, capture, fixture_raw, capture_raw, reopen_raw, ui_raw, previous)
            result[phase + "NativeProof"] = proof
            write(evidence / (phase + "-independent-native-qualified.json"), proof)
            previous, previous_raw = value, native_raw

        require(set(result["stages"]) == {"mounted", "linked-ui", "linked-native", "unlinked-ui", "unlinked-native"}
                and all(row["status"] == "PASS" and row["testInvoked"] is True for row in result["stages"].values()),
                "All five actual continuation methods are required")
        result["status"] = "PASS_FIVE_ACTUAL_METHODS_WITH_ORIGINAL_PREPARATION"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        errors = []
        if boot_owned:
            try:
                # The original preparation already ran the actual application.
                # A later stage exception cannot make this account optional.
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE,
                    private / "final-sandbox-originals", application_invoked=True)
            except BaseException as exc: errors.append({"phase": "private-retention", **c.error(exc)})
            try:
                _, stopped = commands.run(["xcrun", "simctl", "shutdown", DEVICE], "shutdown-owned-device", 60,
                                           checked=False, capacity=False)
                require(stopped["exitCode"] == 0, "Owned shutdown failed")
            except BaseException as exc: errors.append({"phase": "shutdown", **c.error(exc)})
        try:
            result["finalProducts"] = {name: c.product_integrity(row) for name, row in built.items()}
            if built:
                for name, expected in c.HELPERS.items():
                    require(c.digest(args.root / "helpers" / name) == expected, "Original pure helper changed")
        except BaseException as exc: errors.append({"phase": "product-helper-integrity", **c.error(exc)})
        groups = []
        for group in commands.groups:
            if group in commands.absent_groups:
                groups.append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
                continue
            try:
                present = c.Commands.present(group)
                groups.append({"pgid": group, "present": present})
                if present: errors.append({"phase": "owned-group-still-present", "pgid": group})
            except BaseException as exc: errors.append({"phase": "owned-group-state-unavailable", "pgid": group, **c.error(exc)})
        result["cleanup"] = {"status": "PASS" if not errors else "FAIL", "errors": errors, "groups": groups,
            "ownedSimulatorDeleted": False, "ownedSimulatorRetainedForRecovery": DEVICE}
        if errors: result["status"] = "FAIL"
        invoked = {name for name, row in result["stages"].items() if row.get("testInvoked") is True}
        started_evidence = {}
        for name in ("mounted", "linked-ui", "linked-native", "unlinked-ui", "unlinked-native"):
            started = args.root / "commands" / (name + "-test") / "started.json"
            if started.is_file():
                invoked.add(name)
                started_evidence[name] = {"sha256": c.digest(started), "selector": STAGES[name]}
        result["actualMethodsInvokedInThisContinuation"] = len(invoked)
        result["actualInvocationStartedEvidence"] = started_evidence
        result["finishedAt"] = time.time()
        write(evidence / "execution.json", result)
    seal = {"status": "NOT_SEALED", "executionSHA256": c.digest(evidence / "execution.json"),
            "originalPreparationExecutionSHA256": original.PRIOR_EXECUTION,
            "originalLaunchFailureExecutionSHA256": installed.PRIOR_EXECUTION,
            "originalInstallationRelocationExecutionSHA256": relocated.PRIOR_EXECUTION,
            "originalInstalledModeFailureExecutionSHA256": PRIOR_EXECUTION, "fullEAcceptance": False}
    if boot_owned and result["cleanup"]["status"] == "PASS":
        try:
            seal["privateAccount"] = account.retain(args.root, seal["executionSHA256"])
            seal["retentionSHA256"] = c.digest(private / "owned-account-originals/retention.json")
            seal["devicePlistSHA256"] = c.digest(private / "owned-account-originals/device.plist")
            seal["status"] = "SEALED_FIVE_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E"
        except BaseException as exc: seal["firstFailure"] = c.error(exc)
    write(evidence / "retention-completion.json", seal)
    print(json.dumps({"status": result["status"], "actualStages": {k:v["status"] for k,v in result["stages"].items()},
                      "firstFailure": result.get("firstFailure"), "retention": seal["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS_FIVE_ACTUAL_METHODS_WITH_ORIGINAL_PREPARATION" and seal["status"] == "SEALED_FIVE_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E" else 1


if __name__ == "__main__":
    raise SystemExit(main())
