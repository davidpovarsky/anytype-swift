#!/usr/bin/env python3
"""One fresh original account setup followed directly by real source UI capture.

This is a new disposable account after a previous simulator disappeared. It
does not restore that account, extend an old deadline or rerun E acceptance.
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
    result = {"protocol": "pinkha-fresh-heart-source-capture-v1", "status": "FAIL",
        "sourceCommit": SOURCE, "uiSourceCommit": UI_DONOR, "originalCUIFileSHA256": UI_SOURCE_SHA,
        "controllerSHA256": c.digest(Path(__file__)), "captureHelperSHA256": CAPTURE_SHA,
        "coreSHA256": CORE_SHA, "uiProfileSHA256": args.ui_profile_sha256,
        "uiAdmissionSHA256": args.ui_admission_sha256, "qualificationOnly": args.qualify_only,
        "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "stages": {},
        "factoryMethodsExecuted": 0, "originalSimulatorStateReused": False,
        "wholeSpaceMigration": False, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
        "priorExternallyLostAccountRestored": False, "priorFixtureDeadlineExtended": False}
    binding = {"sourceSHA": SOURCE, "runID": str(time.time_ns() // 1000),
               "runAttempt": "1", "nonce": uuid.uuid4().hex}
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
        if args.qualify_only:
            result["status"] = "QUALIFIED_SOURCE_PRODUCTS_ONLY_NO_ACCOUNT_OR_TEST"
        else:
            c.require(c.shutil.disk_usage(args.root).free >= 5 * 1024**3,
                      "Measured fresh simulator/account growth plus emergency floor unavailable")
            result["resourcePolicy"] = {"estimatedNewBytes": 3 * 1024**3,
                "emergencyFreeBytes": 2 * 1024**3,
                "reason": "APFS-cloned qualified products; one fresh disposable iPad simulator, source bundles and private logs; no compiler or dependency download."}
            log, _ = commands.run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtime-inventory", 30)
            rows = [r for r in c.decode(c.raw(log))["runtimes"] if r.get("identifier") == c.RUNTIME]
            c.require(len(rows) == 1 and rows[0].get("version") == c.OS_VERSION
                      and rows[0].get("buildversion") == c.OS_BUILD and rows[0].get("isAvailable") is True,
                      "Exact installed runtime required")
            c.write(evidence / "execution-intent.json", {"binding": binding,
                "selectors": [c.STAGES["preparation"], src.SELECTOR],
                "purpose": "fresh native account setup followed by actual source review/close/recapture",
                "noEMountedOrSourceAcceptanceReplay": True})
            log, _ = commands.run(["xcrun", "simctl", "create", NAME_PREFIX + binding["nonce"], c.DEVICE, c.RUNTIME],
                                  "create-owned-simulator", 60)
            device = c.raw(log, 4096).decode().strip()
            c.require(re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", device),
                      "Actual fresh owned simulator UUID required")
            result["ownedSimulator"] = device
            c.write(evidence / "owned-simulator.json", {"udid": device, "runtime": rows[0], "deviceType": c.DEVICE})
            device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device
            root_stat = device_root.lstat()
            c.require(device_root.resolve() == device_root and stat.S_ISDIR(root_stat.st_mode), "Fresh owned device root required")
            created_root_identity = (root_stat.st_dev, root_stat.st_ino, root_stat.st_mode)
            state(c, commands, device, binding, "fresh-created-state", "Shutdown")
            claimed_boot = True
            commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator", 60)
            commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-owned-boot", 180)
            state(c, commands, device, binding, "fresh-booted-state", "Booted")
            _, result["originalAppInstallation"] = commands.run(
                ["xcrun", "simctl", "install", device, str(app)], "install-original-before-preparation", 120)
            base_env = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
            for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
                base_env["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
            prep = c.stage(commands, evidence, "preparation", built["app"], app, binding, device,
                           dict(base_env, PINKHA_SEMANTIC_MOUNTED_PREPARE="1"))
            result["stages"]["preparation"] = prep
            c.require(prep["status"] == "PASS", "Original real account preparation failed")
            result["factoryMethodsExecuted"] = 1
            fixture_raw = c.app_file(commands, device, private, c.FIXTURE, "preserve-original-fixture", 65536)
            fixture = c.decode(fixture_raw)
            c.mounted.fixture(fixture, binding)
            created = fixture.get("createdAtEpoch")
            c.require(type(created) in (int, float) and math.isfinite(created)
                      and 0 <= time.time() - created < 7200, "Original new fixture creation time required")
            deadline = created + 7200
            result["originalFixtureDeadlineEpoch"] = deadline
            result["fixtureSHA256"] = c.sha(fixture_raw)
            src.DEVICE, src.BINDING, src.DEADLINE, src.FIXTURE_SHA = device, binding, deadline, c.sha(fixture_raw)
            app_data = src.app_container(c, commands, "prepared-original-container")
            prepared_sandbox = c.preserve_final_sandbox(LabelledCommands(commands, "prepared-"), device,
                private / "prepared-sandbox-originals", application_invoked=True)
            c.write(evidence / "prepared-sandbox.json", prepared_sandbox)
            c.require(prepared_sandbox["files"][c.FIXTURE]["sha256"] == c.sha(fixture_raw),
                      "Actual fixture was not preserved from its original account")
            parent, before = src.captures_inventory(c, app_data)
            c.require(before == {}, "A fresh setup must not contain previous source captures")
            c.write(private / "captures-before.json", before)
            handoff = {"protocol": "pinkha-fresh-c-preparation-handoff-v1", "binding": binding,
                "ownedSimulator": device, "preparationResultSHA256": c.digest(evidence / "preparation/result.json"),
                "fixtureSHA256": c.sha(fixture_raw), "preparedSandboxSHA256": c.digest(evidence / "prepared-sandbox.json"),
                "deadlineEpoch": deadline, "scope": "new-disposable-account-setup-only-not-E-acceptance"}
            c.write(evidence / "fresh-preparation-handoff.json", handoff)
            handoff_sha = c.digest(evidence / "fresh-preparation-handoff.json")
            result["handoffSHA256"] = handoff_sha
            c.write(evidence / "after-preparation-checkpoint.json", result)
            c.require(time.time() + 300 < deadline, "Original fresh fixture has insufficient bounded UI time")
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
                              for name in ("preparation", "source-review"))
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
