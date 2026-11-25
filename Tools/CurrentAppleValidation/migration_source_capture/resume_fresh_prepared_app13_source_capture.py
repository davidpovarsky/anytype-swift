#!/usr/bin/env python3
"""Continue only C capture on the exact original prepared account.

The first controller actually prepared the account, then looked up the wrong
raw timestamp field before invoking C. Its failure and original two-hour
deadline remain preserved. No preparation, installation or fixture replay.
"""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import sys
import time
import traceback
import uuid

sys.dont_write_bytecode = True
CONTROL = Path("/Users/m1/development/anytype-e-active-20261125/main13/control-643c7d8")
CORE_SHA = "73ee947386ac6115ec7b1d75d74b1590a68a033000b311329fb8824c15691239"
BASE_ADMISSION = CONTROL / "admission-app13.json"
BASE_ADMISSION_SHA = "67bd30ff19e2fc3e1890369dcf60cef0936111ee7ebe635113026c0cadef515f"
CAPTURE_SHA = "5330c499dcac6a57d7242256a9daaf8702dc5e2d826327a14bfd10fbb1f572ec"
SOURCE = "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f"
UI_DONOR = "19307349e0ef469e7d4637132ada529072e1a0c0"
UI_SOURCE_SHA = "c9f5a63f49c2f1a73232d05c0a6238109b4f5f1fcf0ddf699f0d68d24e1faff0"
OLD_CUI_SHA = "272dd5ce3620eafc4a1411f51f38d799041a0f535a46cafc97f6972c26407727"
UI_PATH = "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift"
NAME_PREFIX = "C-Source-Capture-"
RETAINER_SHA = "24b3d4739fb4a3404263832f0a710365bb314c3249c3c392a2db53a731eb3ee9"

PRIOR = Path("/Users/m1/development/anytype-c-active-20261125/app13-fresh-source-capture/fresh-account-attempt1")
PRIOR_EXECUTION_SHA = "e2608d4d3f9cc90fd23a0c02fa3d76fad94233de4c42a7f8e6b616caef801c9e"
PRIOR_FINAL_SHA = "31374dcdda28c4bdb293ddf8b394e2ad5275baccc6fb17140a21c468e743dc84"
PRIOR_BACKUP_SHA = "878c4006cbb0d627bd57b1d4723ede5ab31d736a97fc4092a380e8afe20c9551"
PRIOR_PLIST_SHA = "76a5ad2069663015d9caa455b4b60ae58d4aa11ca9f20bc61a458ecb2915a535"
PRIOR_FIXTURE_SHA = "1fcf19934d5ab77669339a71cee62f771f5610099117ca418a866d14876229e2"
PRIOR_PREPARATION_SHA = "99a919b7c6a7356e281c320f0ef740ea2636a158d4df75c8d108a4541527ec05"
PRIOR_CONTROLLER_SHA = "df5207bbf1599e460dbe40586ab68645775133c53f0b89af79a8e9bf23864f94"
PRIOR_DEVICE = "95F3188C-EFDE-40A4-A248-40E04236BF11"
PRIOR_BINDING = {"sourceSHA": SOURCE, "runID": "1795648348430776", "runAttempt": "1", "nonce": "1055b7b9bd53479ba48390deb505f1b6"}
PRIOR_DEADLINE = 1795655679.149899

def admit_prepared(c, commands, retainer, evidence):
    """Requalify actual setup and all private custody before any owned boot."""
    for name, expected in [("evidence/execution.json", PRIOR_EXECUTION_SHA),
        ("evidence/final-outcome.json", PRIOR_FINAL_SHA),
        ("private/owned-account-originals/retention.json", PRIOR_BACKUP_SHA),
        ("private/" + c.FIXTURE, PRIOR_FIXTURE_SHA),
        ("evidence/preparation/result.json", PRIOR_PREPARATION_SHA)]:
        c.require(c.digest(PRIOR / name) == expected, "Original prepared account receipt changed")
    execution = c.decode(c.raw(PRIOR / "evidence/execution.json"))
    backup = c.decode(c.raw(PRIOR / "private/owned-account-originals/retention.json"))
    fixture_raw = c.raw(PRIOR / "private" / c.FIXTURE, 65536)
    fixture = c.decode(fixture_raw)
    c.require(execution["protocol"] == "pinkha-fresh-heart-source-capture-v1"
        and execution["controllerSHA256"] == PRIOR_CONTROLLER_SHA
        and execution["sourceCommit"] == SOURCE and execution["uiSourceCommit"] == UI_DONOR
        and execution["binding"] == PRIOR_BINDING and execution["ownedSimulator"] == PRIOR_DEVICE
        and execution["status"] == "FAIL" and set(execution["stages"]) == {"preparation"}
        and execution["firstFailure"] == {"type":"ValueError", "message":"Original new fixture creation time required"}
        and execution["factoryMethodsExecuted"] == 1
        and execution["cleanup"]["status"] == "PASS"
        and execution["cleanup"]["ownedSimulatorDeleted"] is False
        and execution["cleanup"]["ownedSimulatorRetainedForRecovery"] == PRIOR_DEVICE,
        "Only the exact zero-capture timestamp-field failure may continue")
    c.require(not (PRIOR / "commands/source-review-enumerate/started.json").exists()
        and not (PRIOR / "commands/source-review-test/started.json").exists(),
        "A prior C source method must not be replayed by this continuation")
    original = execution["stages"]["preparation"]
    log = PRIOR / "commands/preparation-test/original.log"
    c.require(original["status"] == "PASS" and original["testInvoked"] is True
        and original["command"]["exitCode"] == 0 and c.digest(log) == original["command"]["logSHA256"],
        "Actual original setup exit/log required")
    proof = c.qualify_execution(c.decode(c.raw(PRIOR / "evidence/preparation/summary.json")),
        c.decode(c.raw(PRIOR / "evidence/preparation/tests.json")), c.STAGES["preparation"], PRIOR_DEVICE, log)
    c.require(c.decode(json.dumps(proof).encode()) == original["actual"], "Original setup result differs")
    c.mounted.fixture(fixture, PRIOR_BINDING)
    # The existing Swift fixture uses Date's reference epoch (2001), exactly
    # as the unchanged mounted contract validates. Keep its fractional value.
    c.require(fixture["createdAt"] + 978307200 + 7200 == PRIOR_DEADLINE
        and time.time() + 300 < PRIOR_DEADLINE, "Original account deadline changed or exhausted")
    c.require(backup["protocol"] == "pinkha-fresh-c-source-account-retention-v1"
        and backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
        and backup["executionSHA256"] == PRIOR_EXECUTION_SHA and backup["device"] == PRIOR_DEVICE
        and backup["restoredFixtures"] == 0 and backup["fixtureDeadlineChanged"] is False,
        "Exact original full account backup required")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "prepared-owned-shutdown", "Shutdown")
    old_command = PRIOR / "commands/final-private-sandbox-container"
    command = c.decode(c.raw(old_command / "result.json"))
    c.require(command["argv"] == ["xcrun","simctl","get_app_container",PRIOR_DEVICE,"io.anytype.app","data"]
        and command["exitCode"] == 0 and command["status"] == "PASS_COMMAND"
        and c.digest(old_command / "original.log") == command["logSHA256"], "Original native data container resolution required")
    app = Path(c.raw(old_command / "original.log", 4096).decode().strip())
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / PRIOR_DEVICE
    plist = device_root / "device.plist"
    c.require(app.parent == device_root / "data/Containers/Data/Application" and app.is_dir()
        and re.fullmatch(r"[0-9A-F-]{36}", app.name), "Exact original account container required")
    def identity(path):
        value = path.lstat()
        c.require(path.resolve() == path and not stat.S_ISLNK(value.st_mode), "Account root was replaced by an alias")
        return (value.st_dev, value.st_ino, value.st_mode)
    original = (identity(device_root), identity(plist), identity(app))
    c.require(c.digest(plist) == PRIOR_PLIST_SHA
        == c.digest(PRIOR / "private/owned-account-originals/device.plist"), "Original shutdown device metadata changed")
    scopes = {"application-data":app, "shared-app-groups":device_root / "data/Containers/Shared/AppGroup",
        "keychains":device_root / "data/Library/Keychains", "device-preferences":device_root / "data/Library/Preferences"}
    identities = {key:identity(path) if path.exists() else None for key,path in scopes.items()}
    for key,path in scopes.items():
        row = backup["scopes"][key]
        if row["status"] == "NOT_PRESENT":
            c.require(not path.exists() and not path.is_symlink(), "An absent scope appeared")
        else:
            manifest = PRIOR / "private/owned-account-originals" / (key + "-before.json")
            c.require(row["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES"
                and c.digest(manifest) == row["manifestSHA256"]
                and retainer.inventory(path) == c.decode(c.raw(manifest)), "Live account differs from original full backup")
        c.require(c.digest(plist) == PRIOR_PLIST_SHA
            and original == (identity(device_root),identity(plist),identity(app)), "Device identity changed during account admission")
        for label,scope in scopes.items():
            c.require((identity(scope) if scope.exists() else None) == identities[label]
                and not scope.is_symlink(), "Account scope root changed during admission")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "prepared-after-inventory", "Shutdown")
    c.require(c.digest(app / "Library/Application Support" / c.FIXTURE) == PRIOR_FIXTURE_SHA,
        "Live original fixture changed")
    c.write(evidence / "original-preparation-requalification.json", {
        "priorExecutionSHA256":PRIOR_EXECUTION_SHA, "priorStatus":"FAIL_ZERO_CAPTURE_METHODS",
        "actualOriginalPreparation":proof, "originalBackupSHA256":PRIOR_BACKUP_SHA,
        "fixtureSHA256":PRIOR_FIXTURE_SHA, "originalDeadlineEpoch":PRIOR_DEADLINE,
        "originalPreparationReplayed":False, "allFourPrivateScopesMatch":True})
    return app, fixture_raw, execution["finalPrivateSandbox"]

def module(path, expected, name):
    if not (path.is_absolute() and path.resolve() == path and path.is_file()
            and re.fullmatch(r"[0-9a-f]{64}", expected)
            and hashlib.sha256(path.read_bytes()).hexdigest() == expected):
        raise ValueError("Exact canonical reviewed helper required")
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    if Path(value.__file__).resolve() != path or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Helper changed during import")
    return value

def admit_ui(c, args, base, built, app, commands, evidence):
    """Original App admission and a separately proven complete UI derivative."""
    raw = c.raw(args.ui_admission)
    c.require(c.sha(raw) == args.ui_admission_sha256, "Exact UI-only admission bytes required")
    admission = c.decode(raw)
    c.require("freshWarningUIOverride" in admission, "Explicit fresh-warning UI pairing required")
    original = copy.deepcopy(admission)
    original.pop("freshWarningUIOverride")
    original["products"]["ui"] = base["products"]["ui"]
    c.require(original == base, "The derivative may change only the declared UI pairing")
    profile = module(args.ui_profile, args.ui_profile_sha256, "c_fresh_warning_ui_override")
    proof = profile.qualify(c, admission, Path(base["sourceRoot"]), c.decode(c.pinned(base["producerReceipt"])))
    # The reviewed profile owns the complete twelve-file Git/blob inverse and
    # actual original build log/receipt. Retain its exact proof without reducing it.
    c.write(evidence / "fresh-warning-ui-admission.json", proof)
    row = admission["products"]["ui"]
    source = Path(row["root"])
    manifest = c.decode(c.pinned(row["manifest"]))
    c.require(c.inventory(source) == manifest, "Qualified UI products changed before cloning")
    destination = args.root / "ui-fresh-warning-products"
    previous = os.umask(0)
    try:
        commands.run(["cp", "-cR", str(source), str(destination)], "clone-fresh-warning-ui-products", 180)
    finally:
        os.umask(previous)
    c.require(c.inventory(destination) == manifest, "Complete derivative UI clone differs")
    descriptor = destination / row["descriptorRelativePath"]
    c.require(descriptor.parent == destination and descriptor.suffix == ".xctestrun"
              and c.digest(descriptor) == row["descriptorSHA256"], "Exact complete UI descriptor required")
    previous_ui = built["ui"]
    built["ui"] = {"products": destination, "inventory": manifest, "copies": {},
                   "descriptor": descriptor, "originalSelection": row["originalSelection"]}
    return proof, previous_ui

def state(c, commands, device, binding, label, expected=None):
    log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], label, 30, capacity=False)
    matches = [dict(row, runtime=runtime) for runtime, rows in c.decode(c.raw(log))["devices"].items()
               for row in rows if row.get("udid") == device]
    c.require(len(matches) == 1 and matches[0].get("name") == NAME_PREFIX + binding["nonce"]
              and matches[0].get("runtime") == c.RUNTIME and matches[0].get("deviceTypeIdentifier") == c.DEVICE
              and matches[0].get("isAvailable") is True
              and (expected is None or matches[0].get("state") == expected),
              "Exact fresh C-owned simulator identity/state required")
    return matches[0]

class LabelledCommands:
    def __init__(self, commands, prefix):
        self.commands = commands
        self.prefix = prefix
    def run(self, argv, label, *args, **kwargs):
        return self.commands.run(argv, self.prefix + label, *args, **kwargs)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ui-admission", type=Path, required=True)
    parser.add_argument("--ui-admission-sha256", required=True)
    parser.add_argument("--ui-profile", type=Path, required=True)
    parser.add_argument("--ui-profile-sha256", required=True)
    parser.add_argument("--qualify-only", action="store_true")
    args = parser.parse_args()
    src = module(Path(__file__).with_name("run_app13_observed_heart_source_capture.py"),
                 CAPTURE_SHA, "c_original_source_capture")
    c = src.load_core()
    c.require(sys.platform == "darwin" and c.digest(CONTROL / "combined_heart_semantics_current.py") == CORE_SHA,
              "Original actual Apple runtime admission required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent
              and not args.root.exists(), "Fresh protected C execution root required")
    args.root.mkdir(mode=0o700)
    os.umask(0o077)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    private = args.root / "private"; private.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    result = {"protocol": "pinkha-resumed-fresh-heart-source-capture-v1", "status": "FAIL",
        "sourceCommit": SOURCE, "uiSourceCommit": UI_DONOR, "originalCUIFileSHA256": UI_SOURCE_SHA,
        "controllerSHA256": c.digest(Path(__file__)), "captureHelperSHA256": CAPTURE_SHA,
        "coreSHA256": CORE_SHA, "uiProfileSHA256": args.ui_profile_sha256,
        "uiAdmissionSHA256": args.ui_admission_sha256, "qualificationOnly": args.qualify_only,
        "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "stages": {},
        "factoryMethodsExecuted": 0, "originalSimulatorStateReused": True,
        "wholeSpaceMigration": False, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
        "priorExternallyLostAccountRestored": False, "priorFixtureDeadlineExtended": False}
    binding = dict(PRIOR_BINDING)
    result["binding"] = binding
    result["bindingIdentityKind"] = "unique local microsecond receipt identity, not GitHub Actions"
    built = {}; original_ui = None; device = None; claimed_boot = False
    app_data = None; prepared_sandbox = None; fixture = None; deadline = None
    retainer = None; created_root_identity = None
    try:
        retainer = module(Path(__file__).with_name("retain_fresh_c_source_account.py"),
                          RETAINER_SHA, "c_fresh_owned_account_retainer")
        c.require(c.digest(BASE_ADMISSION) == BASE_ADMISSION_SHA, "Exact same-source App13 base admission required")
        base = c.decode(c.raw(BASE_ADMISSION))
        c.require(base["controllerSHA256"] == CORE_SHA and base["sourceCommit"] == SOURCE
                  and c.digest(Path(base["sourceRoot"]) / UI_PATH) == OLD_CUI_SHA,
                  "Original compiled C method source differs")
        mask = os.umask(0)
        try:
            result["sourceAdmission"], built, app = c.admit_and_clone_products(base, args.root, evidence, commands)
        finally:
            os.umask(mask)
        result["uiDerivativeAdmission"], original_ui = admit_ui(c, args, base, built, app, commands, evidence)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer",
                     "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        import importlib
        c.common = importlib.import_module("contracts")
        c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract")
        c.boundary = importlib.import_module("page154_boundary")
        c.native.binding(binding)
        admitted_app_data, admitted_fixture_raw, original_sandbox = admit_prepared(c, commands, retainer, evidence)
        result["priorPreparedAccount"] = {"executionSHA256":PRIOR_EXECUTION_SHA,
            "originalStatus":"FAIL_ZERO_CAPTURE_METHODS", "preparationReplayed":False}
        if args.qualify_only:
            result["status"] = "QUALIFIED_SOURCE_PRODUCTS_ONLY_NO_ACCOUNT_OR_TEST"
        else:
            c.require(c.shutil.disk_usage(args.root).free >= (2 * 1024**3 + 512 * 1024**2),
                      "Measured reused account/bundle growth plus emergency floor unavailable")
            result["resourcePolicy"] = {"estimatedNewBytes":512 * 1024**2,
                "emergencyFreeBytes":2 * 1024**3,
                "reason":"APFS-cloned products, existing sealed simulator; only two native bundles, logs and backup. No compiler or fixture creation."}
            device = PRIOR_DEVICE
            result["ownedSimulator"] = device
            c.write(evidence / "execution-intent.json", {"binding":binding,"selectors":[src.SELECTOR],
                "priorPreparationSHA256":PRIOR_PREPARATION_SHA,"noPreparationReplay":True})
            c.write(evidence / "owned-simulator.json", {"udid":device, "originalCreationRoot":str(PRIOR),
                "originalExecutionSHA256":PRIOR_EXECUTION_SHA})
            device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device
            root_stat = device_root.lstat()
            created_root_identity = (root_stat.st_dev, root_stat.st_ino, root_stat.st_mode)
            claimed_boot = True
            commands.run(["xcrun","simctl","boot",device], "boot-owned-simulator",60)
            commands.run(["xcrun","simctl","bootstatus",device,"-b"], "await-owned-boot",180)
            state(c,commands,device,binding,"prepared-booted-state","Booted")
            base_env = {"PINKHA_SIMULATOR_UI_DISPOSABLE":"1"}
            for key,suffix in (("sourceSHA","SOURCE_SHA"),("runID","RUN_ID"),("runAttempt","RUN_ATTEMPT"),("nonce","NONCE")):
                base_env["PINKHA_SEMANTIC_MOUNTED_"+suffix] = binding[key]
            fixture_raw = c.app_file(commands, device, private, c.FIXTURE, "preserve-original-fixture", 65536)
            fixture = c.decode(fixture_raw)
            c.mounted.fixture(fixture, binding)
            c.require(fixture_raw == admitted_fixture_raw, "Original fixture changed after owned boot")
            deadline = fixture["createdAt"] + 978307200 + 7200
            c.require(deadline == PRIOR_DEADLINE and time.time() < deadline, "Original fixture deadline changed")
            result["originalFixtureDeadlineEpoch"] = deadline
            result["fixtureSHA256"] = c.sha(fixture_raw)
            src.DEVICE, src.BINDING, src.DEADLINE, src.FIXTURE_SHA = device, binding, deadline, c.sha(fixture_raw)
            app_data = src.app_container(c, commands, "prepared-original-container")
            c.require(app_data == admitted_app_data, "Original account container changed after boot")
            prepared_sandbox = c.preserve_final_sandbox(LabelledCommands(commands, "prepared-"), device,
                private / "prepared-sandbox-originals", application_invoked=True)
            c.require(prepared_sandbox["files"] == original_sandbox["files"], "Original setup witnesses changed")
            c.write(evidence / "prepared-sandbox.json", prepared_sandbox)
            c.require(prepared_sandbox["files"][c.FIXTURE]["sha256"] == c.sha(fixture_raw),
                      "Actual fixture was not preserved from its original account")
            parent, before = src.captures_inventory(c, app_data)
            c.require(before == {}, "A fresh setup must not contain previous source captures")
            c.write(private / "captures-before.json", before)
            handoff = {"protocol": "pinkha-fresh-c-preparation-handoff-v1", "binding": binding,
                "ownedSimulator": device, "preparationResultSHA256": PRIOR_PREPARATION_SHA,
                "originalPreparationRoot":str(PRIOR),"originalFailureSHA256":PRIOR_EXECUTION_SHA,
                "fixtureSHA256": c.sha(fixture_raw), "preparedSandboxSHA256": c.digest(evidence / "prepared-sandbox.json"),
                "deadlineEpoch": deadline, "scope": "new-disposable-account-setup-only-not-E-acceptance"}
            c.write(evidence / "fresh-preparation-handoff.json", handoff)
            handoff_sha = c.digest(evidence / "fresh-preparation-handoff.json")
            result["handoffSHA256"] = handoff_sha
            c.write(evidence / "after-preparation-checkpoint.json", result)
            c.require(time.time() + 300 < deadline, "Original prepared fixture has insufficient bounded UI time")
            additions = dict(base_env, PINKHA_SEMANTIC_MOUNTED_TESTING="1",
                PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON=fixture_raw.decode(),
                PINKHA_HEART_SOURCE_CAPTURE_TESTING="1",
                PINKHA_HEART_SOURCE_CAPTURE_FRESH_STARTUP="1",
                PINKHA_HEART_SOURCE_CAPTURE_FIXTURE_SHA256=c.sha(fixture_raw),
                PINKHA_HEART_SOURCE_CAPTURE_HANDOFF_SHA256=handoff_sha,
                PINKHA_HEART_SOURCE_CAPTURE_DEADLINE_EPOCH=repr(deadline))
            stage = src.source_stage(c, commands, evidence, built["ui"], app, binding, device, additions)
            result["stages"]["source-review"] = stage
            c.require(stage["status"] == "PASS" and stage["command"]["finishedAt"] < deadline,
                      "Original C source UI did not pass within the new fixture's original deadline")
            ui, pin = src.observation(c, evidence / "source-review/private-attachments", fixture, handoff_sha)
            c.require(ui.get("freshStartupNavigationRequested") is True and ui.get("freshStartupNavigationCompleted") is True,
                      "Actual original startup warning navigation required for this fresh account")
            c.write(private / "actual-ui-observation.json", ui)
            result["uiObservationSHA256"] = pin["sha256"]
            _, after = src.captures_inventory(c, app_data)
            c.require(len(after) == 2, "Exactly two new actual native capture bundles required")
            proofs = [src.verify_bundle(c, parent / name, fixture) for name in sorted(after)]
            c.require(collections.Counter(p["manifestSHA256"] for p in proofs) ==
                      collections.Counter(p["manifestSHA256"] for p in ui["captures"]),
                      "UI fingerprints differ from actual native source bundles")
            for capture in ui["captures"]:
                matches = [p for p in proofs if p["manifestSHA256"] == capture["manifestSHA256"]]
                c.require(matches and all(all(capture["counts"][key] == value for key, value in proof["counts"].items())
                                         for proof in matches), "UI census differs from actual snapshots/witness")
            c.write(private / "captures-after.json", after)
            result["nativeBundles"] = proofs
            result["distinctCaptureRequests"] = 2; result["closedReviews"] = 2
            result["status"] = "PASS_FRESH_ACTUAL_SOURCE_UI_TWO_CAPTURES_CLOSE_AND_NATIVE_BUNDLES"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        if app_data is not None:
            try:
                result["sourceDiagnosticObservations"] = src.collect_diagnostic(c, app_data, private)
            except BaseException as exc:
                result["diagnosticCollectionFailure"] = c.error(exc); result["status"] = "FAIL_DIAGNOSTIC_COLLECTION"
        cleanup = {"status": "PASS", "groups": [], "errors": [], "ownedSimulatorDeleted": False,
                   "ownedSimulatorRetainedForRecovery": device}
        if device:
            try:
                invoked = any((args.root / "commands" / (name + "-enumerate") / "started.json").is_file()
                              or (args.root / "commands" / (name + "-test") / "started.json").is_file()
                              for name in ("source-review",))
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, device,
                    private / "final-sandbox-originals", application_invoked=invoked)
                if prepared_sandbox is not None:
                    c.require(result["finalPrivateSandbox"]["files"] == prepared_sandbox["files"],
                              "Actual original setup witnesses changed during source capture")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "private-witness-retention", **c.error(exc)})
            try:
                current = state(c, commands, device, binding, "before-owned-shutdown")
                if current["state"] != "Shutdown":
                    _, stopped = commands.run(["xcrun", "simctl", "shutdown", device], "cleanup-shutdown", 60,
                                               checked=False, capacity=False)
                    c.require(stopped["exitCode"] == 0, "Owned simulator shutdown failed")
                state(c, commands, device, binding, "final-owned-shutdown", "Shutdown")
                st = (Path.home() / "Library/Developer/CoreSimulator/Devices" / device).lstat()
                c.require(created_root_identity == (st.st_dev, st.st_ino, st.st_mode),
                          "Fresh original simulator root identity changed")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"phase": "owned-shutdown", **c.error(exc)})
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
                continue
            try:
                present = c.Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present:
                    cleanup["status"] = "FAIL"; cleanup["errors"].append({"ownedGroupStillPresent": group})
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append({"pgid": group, "phase": "group-observation", **c.error(exc)})
        try:
            result["finalProducts"] = {kind: c.product_integrity(value) for kind, value in built.items()}
            if original_ui is not None: result["originalBaseUIProducts"] = c.product_integrity(original_ui)
            c.require(c.digest(Path(__file__).with_name("run_app13_observed_heart_source_capture.py")) == CAPTURE_SHA,
                      "Original capture acceptance helper changed")
        except BaseException as exc:
            cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        if cleanup["status"] != "PASS": result["status"] = "FAIL"
        result["cleanup"] = cleanup
        c.write(evidence / "cleanup.json", cleanup)
        c.write(evidence / "execution.json", result)
        if device and cleanup["status"] == "PASS" and retainer is not None and (
                result.get("finalPrivateSandbox", {}).get("status") == "PRESERVED_ORIGINAL_PRIVATE_FILES"):
            try:
                retained = retainer.retain(args.root, c.digest(evidence / "execution.json"))
                c.write(evidence / "account-retention.json", retained)
                c.write(evidence / "account-retention-handoff.json", {
                    "backupSHA256": c.digest(private / "owned-account-originals/retention.json"),
                    "devicePlistSHA256": c.digest(private / "owned-account-originals/device.plist"),
                    "executionSHA256": c.digest(evidence / "execution.json"), "device": device,
                    "originalDeadlineEpoch": deadline, "fixtureDeadlineExtended": False})
            except BaseException as exc:
                c.write(evidence / "account-retention-failure.json", c.error(exc)); result["status"] = "FAIL_ACCOUNT_RETENTION"
        c.write(evidence / "final-outcome.json", {"status": result["status"],
            "executionSHA256": c.digest(evidence / "execution.json"), "fullEAcceptance": False,
            "wholeSpaceMigration": False, "priorFixtureDeadlineExtended": False})
    print(json.dumps({"status": result["status"], "receipt": str(evidence / "execution.json"),
        "finalOutcome": str(evidence / "final-outcome.json"),
        "finalOutcomeSHA256": c.digest(evidence / "final-outcome.json"),
        "firstFailure": result.get("firstFailure")}, sort_keys=True))
    return 0 if result["status"] in ("PASS_FRESH_ACTUAL_SOURCE_UI_TWO_CAPTURES_CLOSE_AND_NATIVE_BUNDLES",
                                     "QUALIFIED_SOURCE_PRODUCTS_ONLY_NO_ACCOUNT_OR_TEST") else 1

if __name__ == "__main__":
    raise SystemExit(main())

