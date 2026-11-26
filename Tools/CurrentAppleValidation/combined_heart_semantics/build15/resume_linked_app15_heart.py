"""Continue the three unrun methods after original prep, mounted and linked UI PASS.

The original JSON/PNG collector failure remains unchanged. Original successful
methods are independently requalified without replay; account and expiry stay exact.
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
import types

sys.dont_write_bytecode = True
import combined_heart_semantics_replacement as c
import retain_owned_heart_account as account

CORE = "6c1dea1ef571059291dc9d21c86d1558913a0153a67d719723b601ddcd2ac63c"
RETENTION = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
SOURCE = "379ca3568f247d2fc218ed63df24796d461713c0"
ADMISSION = "15b2e1a57c71599623fd4417b54180d70d81a7c0d683ed7dec4c64c32521c615"
PRIOR = Path("/Users/m1/development/anytype-e-active-20261125/main15/fresh-app15-attempt2")
PRIOR_EXECUTION = "f69519144707d12d6577d7300ae05caeaca514204c295a3652a16b17bdb993f7"
PRIOR_BACKUP = "c11727897347e71a77ba560e21fed2961870a505c4f57f4b55c0303aacd2ee9c"
ORIGINAL_FIXTURE = "aa09c01d3b1a8640009f01d7a36ae2cb9fb18aec0c580271b3764afe354f955b"
ORIGINAL_PLIST = "25d83d2d6a94986fd0b261175d00c2cd5750fcb57598db138ee07640a61c987c"
DEVICE = "98652CBB-F000-4A0F-AFBF-B8054D5F3876"

# Original UI/native outcome functions remain owned by the unchanged core.
# This controller resumes only the three methods that never ran.
require, app_file, decode, sha, write = c.require, c.app_file, c.decode, c.sha, c.write
continuation_ui, continuation_native, STAGES = c.continuation_ui, c.continuation_native, c.STAGES
CAPTURE, REOPEN = c.CAPTURE, c.REOPEN


def admit_prior(admission):
    path = PRIOR / "evidence/execution.json"
    prior_raw = c.raw(path)
    require(sha(prior_raw) == PRIOR_EXECUTION, "Exact original collector-failed execution required")
    prior = decode(prior_raw)
    require(prior["status"] == "FAIL" and prior["sourceCommit"] == admission["sourceCommit"] == SOURCE
            and prior["controllerSHA256"] == CORE and prior["nativeManifestSHA256"] == c.MANIFEST
            and prior["heartOverlaySHA256"] == c.OVERLAY and prior["ownedSimulator"] == DEVICE,
            "Original source/native/owned device identity differs")
    expected_failure = {"type": "ValueError", "message": "bounded regular file required: " + str(
        PRIOR / "evidence/linked-ui/private-attachments/9D74710B-BCB8-4D59-B9E0-FEAC8000D7F7.png")}
    require(prior["firstFailure"] == expected_failure
            and set(prior["stages"]) == {"preparation", "mounted", "linked-ui"}
            and all(row["status"] == "PASS" and row["testInvoked"] is True
                    for row in prior["stages"].values())
            and prior["linkedUIProof"]["status"] == "PASS_UI_ONLY"
            and "linkedRealLinkRouteProof" not in prior
            and prior["fullEAcceptance"] is False,
            "Original three method outcomes and collector failure must remain separate")
    pins = {
        "preparation": "293964bd0dbbba0cec2174521ac3c24a4aa524789e4b0e4c9cd3b5db0a2ddfa7",
        "mounted": "e5e288762a4519fd70b6413d307dea4e794b55666153f66da8f7b54c8e1433fd",
        "linked-ui": "062cc88c2cb2a6bf558ee134fe5df8691f596144af4af0d3263ae61c11d9836b",
    }
    for name, pin in pins.items():
        folder = PRIOR / "evidence" / name
        original = c.raw(folder / "result.json")
        require(sha(original) == pin and decode(original) == prior["stages"][name],
                "Original actual method result changed: " + name)
        log = PRIOR / "commands" / (name + "-test") / "original.log"
        actual = c.qualify_execution(decode(c.raw(folder / "summary.json")),
            decode(c.raw(folder / "tests.json")), STAGES[name], DEVICE, log)
        row = prior["stages"][name]
        require(decode(json.dumps(actual).encode()) == row["actual"]
                and c.digest(log) == row["command"]["logSHA256"]
                and row["command"]["exitCode"] == 0 and row["command"]["cleanupErrors"] == []
                and row["command"]["ownedGroupPresentAfterExit"] is False
                and row["command"]["ownedGroupObservationStatus"] == "ABSENT_ESRCH",
                "Original actual method exports/stdout/exit changed: " + name)
        enumeration = c.qualify_enumeration(decode(c.raw(folder / "enumeration.json")), STAGES[name])
        require(decode(json.dumps(enumeration).encode()) == row["enumeration"],
                "Original compiled method enumeration changed: " + name)
    for name in ("linked-native", "unlinked-ui", "unlinked-native"):
        require(not (PRIOR / "evidence" / name).exists()
                and not (PRIOR / "commands" / (name + "-test")).exists()
                and not (PRIOR / "commands" / (name + "-enumerate")).exists(),
                "A remaining method was already invoked")
    cleanup = prior["cleanup"]
    require(cleanup["status"] == "PASS" and cleanup["errors"] == []
            and cleanup["ownedSimulatorDeleted"] is False
            and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
            and all(row.get("absentAtOriginalExit") is True or row.get("present") is False
                    for row in cleanup["groups"]), "Original owned cleanup is incomplete")
    require(c.digest(PRIOR / "private/final-sandbox-originals" / c.FIXTURE) == ORIGINAL_FIXTURE
            and c.digest(PRIOR / "private/owned-account-originals/device.plist") == ORIGINAL_PLIST
            and c.digest(PRIOR / "evidence/linked-ui/private-attachments/manifest.json")
                == "cdad51421bf0998fba284a6fd3c527b7c07ab81fd1b50edbc0689f4edf22afed",
            "Original fixture, device metadata, or linked attachments changed")
    return prior


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
            and c.digest(args.admission) == ADMISSION, "Exact same-source App15 original UI admission required")
    admission = decode(c.raw(args.admission))
    require(admission["controllerSHA256"] == CORE and admission["sourceCommit"] == SOURCE
            and admission["nativeManifestSHA256"] == c.MANIFEST and admission["heartOverlaySHA256"] == c.OVERLAY,
            "Actual combined source/runtime admission differs")
    route_helper = own / "semantic_link_route_typed_attachments.py"
    require(c.digest(route_helper) == "39cb1d84f78efb922b71dc55ccb371647c90296093e365452b1291ef854aacf6",
            "Exact JSON/PNG route collector required")
    selection_helper = own / "replacement_selection_observation.py"
    require(c.digest(selection_helper) == c.REPLACEMENT_SELECTION_OBSERVATION_HELPER,
            "Exact reviewed passive selection observation required")
    prior = admit_prior(admission)
    require(args.root.is_absolute() and args.root.parent == PRIOR.parent
            and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
            "Fresh separately owned continuation root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", c.raw(args.admission))
    c.write_bytes(evidence / "original-three-method-execution.json", c.raw(PRIOR / "evidence/execution.json"))
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; boot_owned = False
    binding = prior["binding"]
    device = DEVICE
    result = {"status": "FAIL", "protocol": "pinkha-app15-original-three-methods-continuation-v1",
              "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": SOURCE,
              "controllerSHA256": args.controller_sha256, "coreControllerSHA256": CORE,
              "observationHelperSHA256": c.OBSERVATION_HELPER,
              "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
              "ownedSimulator": DEVICE, "binding": binding, "stages": {},
              "priorExecutionSHA256": PRIOR_EXECUTION, "priorBackupSHA256": PRIOR_BACKUP,
              "originalMethodsReused": {name: {"path": str(PRIOR), "actual": prior["stages"][name]["actual"],
                                              "executedInThisContinuation": False}
                                        for name in ("preparation", "mounted", "linked-ui")},
              "appBuilds": 0, "nativeBuilds": 0, "uiBuilds": 0, "factoryMethodsExecuted": 0,
              "preparationMethodsReexecuted": 0, "fixtureRestorations": 0, "fixtureDeadlineChanges": 0,
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
        capture_raw = c.raw(PRIOR / "private/final-sandbox-originals" / CAPTURE, 65536)
        reopen_raw = c.raw(PRIOR / "private/final-sandbox-originals" / REOPEN, 65536)
        capture, reopen = decode(capture_raw), decode(reopen_raw)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        require(result["mountedProof"] == prior["mountedProof"], "Original mounted proof changed")
        witness = capture.get("nativeBoundaryEvidence")
        require(isinstance(witness, dict) and witness.get("protocolVersion") == 1 and witness.get("extraNativeCalls") == 0
                and witness.get("source") == "actual-client-call-results" and set(witness["files"]) == set(boundary.FILES),
                "Original three native boundaries required")
        boundaries = {}
        for role, filename in boundary.FILES.items():
            row = witness["files"][role]
            require(row["filename"] == filename, "Native boundary filename differs")
            payload = c.raw(PRIOR / "private/final-sandbox-originals" / filename, boundary.MAXIMUM)
            require(len(payload) == row["bytes"] and sha(payload) == row["sha256"], "Original native boundary changed")
            boundaries[role] = payload
        result["nativeBoundaryComparison"] = boundary.verify(boundaries, fixture, capture, native, mounted)
        require(result["nativeBoundaryComparison"] == prior["nativeBoundaryComparison"]
                and result["nativeBoundaryComparison"]["projectionFieldCount"] == 9,
                "Original full nine-field native comparison changed")
        result["originalAttachments"] = policy.mounted_attachments(
            PRIOR / "evidence/mounted/private-attachments", device, capture, reopen, binding, warning)
        require(result["originalAttachments"] == prior["originalAttachments"], "Original mounted attachment proof changed")
        linked_raw, linked_origin = policy.attachment(PRIOR / "evidence/linked-ui/private-attachments",
            "heart-semantic-source-ui-linked", STAGES["linked-ui"], device, maximum=65536)
        result["linkedUIProof"] = continuation_ui(decode(linked_raw), "linked", fixture, capture, capture_raw, reopen_raw)
        require(result["linkedUIProof"] == prior["linkedUIProof"], "Original linked UI proof changed")
        import semantic_link_route_typed_attachments as route_observation
        require(Path(route_observation.__file__).resolve() == route_helper.resolve(), "Foreign typed route collector")
        result["linkedRealLinkRouteProof"] = route_observation.qualify_routes(
            c, policy, PRIOR / "evidence/linked-ui/private-attachments", STAGES["linked-ui"], device, "linked", binding)
        import replacement_selection_observation as selection_observation
        require(Path(selection_observation.__file__).resolve() == selection_helper.resolve(),
                "Foreign passive selection observer")
        def original_selection_file(used_commands, used_device, target, filename, label, maximum):
            require(used_commands is commands and used_device == device and target == private
                    and label == "preserve-real-replacement-native-selection"
                    and Path(filename).name == filename, "Unscoped retained selection observation")
            row = prior["finalPrivateSandbox"]["sourceEntryObservers"][filename]
            raw = c.raw(PRIOR / "private/final-sandbox-originals" / filename, maximum)
            require(row["status"] == "COPIED_ORIGINAL" and row["bytes"] == len(raw)
                    and row["sha256"] == sha(raw)
                    and raw == c.raw(PRIOR / "private/owned-account-originals/application-data/Library/Application Support" / filename, maximum),
                    "Original UI process observation differs from full sealed account")
            c.write_bytes(target / filename, raw)
            return raw
        selection_context = types.SimpleNamespace(STAGES=STAGES, require=require, sha=sha,
                                                  decode=decode, app_file=original_selection_file)
        result["replacementSelectionProof"] = selection_observation.qualify_selection(
            selection_context, policy, commands, PRIOR / "evidence", private, device, fixture, binding)
        result["replacementSelectionOrigin"] = "EXACT_ORIGINAL_FINAL_WITNESS_AND_FULL_ACCOUNT_COPY"
        # Claim cleanup ownership before boot; a post-exit infrastructure failure
        # still requires shutdown and full retention of this admitted account.
        boot_owned = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-boot", 180)
        witness_copy = private / "admitted-original-witnesses"
        witness_copy.mkdir(mode=0o700)
        log, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"],
                              "admit-original-continuation-sandbox", 30)
        container = Path(c.raw(log, 4096).decode().strip())
        require(container.resolve() == container and container.is_relative_to(
                Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE), "Wrong live account container")
        retained = dict(prior["finalPrivateSandbox"]["files"])
        retained.update(prior["finalPrivateSandbox"]["sourceEntryObservers"])
        for index, (filename, row) in enumerate(sorted(retained.items())):
            require(Path(filename).name == filename, "Original witness filename escaped")
            if row["status"] == "NOT_PRESENT":
                require(not (container / "Library/Application Support" / filename).exists()
                        and not (container / "Library/Application Support" / filename).is_symlink(),
                        "A remaining native witness appeared before its first method")
            else:
                current = c.app_file(commands, device, witness_copy, filename, "admit-original-witness-" + str(index))
                require(row["status"] == "COPIED_ORIGINAL" and len(current) == row["bytes"]
                        and sha(current) == row["sha256"]
                        and current == c.raw(PRIOR / "private/final-sandbox-originals" / filename),
                        "Live original witness changed after boot")
        mounted.fixture(fixture, binding)
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        def run(name, additions):
            require(name in ("linked-native", "unlinked-ui", "unlinked-native"),
                    "Only the three original unrun stages are allowed")
            mounted.fixture(fixture, binding)
            kind = "app" if STAGES[name].startswith("AnytypeTests/") else "ui"
            value = c.stage(commands, evidence, name, built[kind], app, binding, device, dict(base, **additions))
            result["stages"][name] = value
            require(value["status"] == "PASS", name + " actual method failed")

        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = sha(payload)
        previous, previous_raw = None, None
        for phase in ("linked", "unlinked"):
            if previous_raw is not None:
                source_env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"] = sha(previous_raw)
            if phase == "linked":
                ui_raw = linked_raw
            else:
                run(phase + "-ui", dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE=phase))
                ui_raw, ui_origin = policy.attachment(evidence / (phase + "-ui") / "private-attachments", "heart-semantic-source-ui-" + phase,
                                                    STAGES[phase + "-ui"], device, maximum=65536)
                result[phase + "UIProof"] = continuation_ui(decode(ui_raw), phase, fixture, capture, capture_raw, reopen_raw)
                result[phase + "RealLinkRouteProof"] = route_observation.qualify_routes(
                    c, policy, evidence / (phase + "-ui") / "private-attachments",
                    STAGES[phase + "-ui"], device, phase, binding)
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

        require(set(result["stages"]) == {"linked-native", "unlinked-ui", "unlinked-native"}
                and all(row["status"] == "PASS" and row["testInvoked"] is True for row in result["stages"].values()),
                "All three actual remaining methods are required")
        result["status"] = "PASS_THREE_ACTUAL_METHODS_WITH_ORIGINAL_THREE"
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
        for name in ("linked-native", "unlinked-ui", "unlinked-native"):
            started = args.root / "commands" / (name + "-test") / "started.json"
            if started.is_file():
                invoked.add(name)
                started_evidence[name] = {"sha256": c.digest(started), "selector": STAGES[name]}
        result["actualMethodsInvokedInThisContinuation"] = len(invoked)
        result["actualInvocationStartedEvidence"] = started_evidence
        result["finishedAt"] = time.time()
        write(evidence / "execution.json", result)
    seal = {"status": "NOT_SEALED", "executionSHA256": c.digest(evidence / "execution.json"),
            "originalThreeMethodExecutionSHA256": PRIOR_EXECUTION, "fullEAcceptance": False}
    if boot_owned and result["cleanup"]["status"] == "PASS":
        try:
            seal["privateAccount"] = account.retain(args.root, seal["executionSHA256"])
            seal["retentionSHA256"] = c.digest(private / "owned-account-originals/retention.json")
            seal["devicePlistSHA256"] = c.digest(private / "owned-account-originals/device.plist")
            seal["status"] = "SEALED_THREE_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E"
        except BaseException as exc: seal["firstFailure"] = c.error(exc)
    write(evidence / "retention-completion.json", seal)
    print(json.dumps({"status": result["status"], "actualStages": {k:v["status"] for k,v in result["stages"].items()},
                      "firstFailure": result.get("firstFailure"), "retention": seal["status"]}, sort_keys=True))
    return 0 if result["status"] == "PASS_THREE_ACTUAL_METHODS_WITH_ORIGINAL_THREE" and seal["status"] == "SEALED_THREE_STAGE_CONTINUATION_ACCOUNT_NOT_FULL_E" else 1


if __name__ == "__main__":
    raise SystemExit(main())
