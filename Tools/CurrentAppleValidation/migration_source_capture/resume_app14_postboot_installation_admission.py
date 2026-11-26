#!/usr/bin/env python3
"""Resume uninvoked App14 setup after the observed Shutdown lookup refusal.

Both original failures stay failed. Four private scopes are admitted while
Shutdown. Exact installed App content is checked after owned boot and before
any original method; there is no install, restore, new fixture or native bypass.
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
CONTROL = Path("/Users/m1/development/anytype-e-active-20261125/main14/control-59a9d56")
CORE_SHA = "59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de"
BASE_ADMISSION = CONTROL / "admission76f59.json"
BASE_ADMISSION_SHA = "e3871c16ccaa3147d90c1c3061690cca2551a54ff8b3c81583196720abaace9e"
CAPTURE_SHA = "5330c499dcac6a57d7242256a9daaf8702dc5e2d826327a14bfd10fbb1f572ec"
SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
UI_SOURCE_COMMIT = SOURCE
UI_SOURCE_SHA = "d8296d08ce03c4756c43e821116f244d4b26c26988134c8457f8dc4c55f6f03d"
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

PRIOR = Path("/Users/m1/development/anytype-c-active-20261125/app14-fresh-source-capture/fresh-account-attempt1")
PRIOR_EXECUTION_SHA = "955d9fd4fb398a2d09649bc8db28affc095ace4ff3c30a0cb096c6be0f6501c6"
PRIOR_OUTCOME_SHA = "a4837e5a97cc4e46177b3312d2c52a778961c8acf31cd2787b15348954db24c0"
PRIOR_CUSTODY_SHA = "9ce866794ef23e84148266f4f17bbae59a7829a548436577c46ff272741f4099"
PRIOR_BACKUP_SHA = "06fbd32b716ea87524fe01e64d1154dd5cc415c40a9523c2ea62808241e9d907"
PRIOR_PLIST_SHA = "b496f1855d29d34aaa9f09c592910023f8864c8e19399a03261820acdb585eab"
PRIOR_DEVICE = "CD378024-982E-41E5-A30B-B4D61996CA1A"
PRIOR_BINDING = {"sourceSHA": SOURCE, "runID": "1795660238909638",
                 "runAttempt": "1", "nonce": "5d2b09cf0d3144019fe3443ab72b4164"}

LOOKUP_PRIOR = PRIOR.parent / "preparation-enumeration-retry1"
LOOKUP_EXECUTION_SHA = "4e9b7a5db210f04c015d111b6793cd44136c1e076e1887ffec4bf91c6890a3d2"
LOOKUP_OUTCOME_SHA = "a92efcf46a533529318c3d305c49414f0b752e1176faeb0e3e7967652d2fd0fe"
LOOKUP_COMMAND_SHA = "4e7ea741d8b10168c68bcd6598975640ec1e7968b7abb4405ea13aeba9d47ead"
LOOKUP_LOG_SHA = "5a76947209a96086c83c0e238a53a5b1c3a4941c23ad3f3525ce11ebfaed5bd8"

def admit_prior(c, commands, retainer, app, evidence):
    def checked(path, expected):
        c.require(path.is_file() and not path.is_symlink() and path.resolve() == path
                  and path.stat().st_size <= 4 * 1024**2, "Closed original custody file required")
        raw = path.read_bytes()
        c.require(c.sha(raw) == expected, "Original custody bytes changed")
        return c.decode(raw)
    lookup = checked(LOOKUP_PRIOR / "evidence/execution.json", LOOKUP_EXECUTION_SHA)
    lookup_final = checked(LOOKUP_PRIOR / "evidence/final-outcome.json", LOOKUP_OUTCOME_SHA)
    lookup_command = checked(LOOKUP_PRIOR / "commands/prior-installed-app-container/result.json", LOOKUP_COMMAND_SHA)
    lookup_log = LOOKUP_PRIOR / "commands/prior-installed-app-container/original.log"
    c.require(c.digest(lookup_log) == LOOKUP_LOG_SHA
              and lookup_log.read_bytes() == b"An error was encountered processing the command (domain=com.apple.CoreSimulator.SimError, code=405):\nUnable to lookup in current state: Shutdown\n"
              and lookup_command["argv"] == ["xcrun", "simctl", "get_app_container", PRIOR_DEVICE, "io.anytype.app", "app"]
              and lookup_command["exitCode"] == 149
              and lookup_command["status"] == "FAIL_COMMAND"
              and lookup_command["logSHA256"] == LOOKUP_LOG_SHA
              and lookup_command["ownedGroupPresentAfterExit"] is False,
              "The exact preboot Shutdown lookup refusal must remain failed")
    c.require(lookup["protocol"] == "pinkha-app14-preparation-enumeration-retry-v1"
              and lookup["status"] == lookup_final["status"] == "FAIL"
              and lookup_final["executionSHA256"] == LOOKUP_EXECUTION_SHA
              and lookup["binding"] == PRIOR_BINDING and lookup["sourceCommit"] == SOURCE
              and lookup["factoryMethodsExecuted"] == 0 and lookup["stages"] == {}
              and "ownedSimulator" not in lookup and "originalFixtureDeadlineEpoch" not in lookup
              and lookup["firstFailure"] == {"message": "prior-installed-app-container failed: 149", "type": "ValueError"}
              and lookup["cleanup"]["status"] == "PASS"
              and lookup["cleanup"]["ownedSimulatorRetainedForRecovery"] is None
              and all(row.get("absentAtOriginalExit") is True and row.get("historicalGroupReprobed") is False
                      for row in lookup["cleanup"]["groups"]),
              "Only the exact zero-method preboot failure may be followed")
    for label in ("boot-owned-simulator", "preparation-enumerate", "preparation-test",
                  "source-review-enumerate", "source-review-test"):
        c.require(not (LOOKUP_PRIOR / "commands" / label / "started.json").exists(),
                  "The prior lookup failure must precede every boot and method")
    original = checked(PRIOR / "evidence/execution.json", PRIOR_EXECUTION_SHA)
    final = checked(PRIOR / "evidence/final-outcome.json", PRIOR_OUTCOME_SHA)
    custody = checked(PRIOR / "evidence/post-terminal-custody-outcome.json", PRIOR_CUSTODY_SHA)
    backup_root = PRIOR / "private/owned-account-originals"
    backup = checked(backup_root / "retention.json", PRIOR_BACKUP_SHA)
    c.require(original["protocol"] == "pinkha-fresh-app14-heart-source-capture-v1"
              and original["status"] == final["status"] == "FAIL"
              and final["executionSHA256"] == PRIOR_EXECUTION_SHA
              and original["binding"] == PRIOR_BINDING
              and original["ownedSimulator"] == PRIOR_DEVICE
              and original["sourceCommit"] == SOURCE
              and original["factoryMethodsExecuted"] == 0
              and set(original["stages"]) == {"preparation"}
              and original["stages"]["preparation"]["status"] == "FAIL"
              and original["stages"]["preparation"]["testInvoked"] is False
              and "originalFixtureDeadlineEpoch" not in original,
              "Only the exact original uninvoked preparation may continue")
    c.require(not (PRIOR / "commands/preparation-test/started.json").exists()
              and not (PRIOR / "commands/source-review-test/started.json").exists(),
              "An original method was already invoked")
    c.require(custody["status"] == "PASS_CUSTODY_ONLY"
              and custody["originalAcceptance"] == "FAIL"
              and custody["originalMethods"] == 0
              and custody["originalExecutionSHA256"] == PRIOR_EXECUTION_SHA
              and custody["retention"] == backup
              and backup["protocol"] == "pinkha-app14-zero-method-failure-custody-v1"
              and backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == PRIOR_EXECUTION_SHA
              and backup["device"] == PRIOR_DEVICE
              and backup["postTerminalGroupObservation"]["status"] == "POSITIVELY_ABSENT"
              and backup["postTerminalGroupObservation"]["errno"] == 3
              and backup["postTerminalGroupObservation"]["signalsSent"] == 0,
              "The separate original failed-group custody seal is required")
    # That group was already positively absent. It is never re-probed or signalled.
    command = checked(PRIOR / "commands/final-private-sandbox-container/result.json",
                      "be9c4d32c41bb9bd19c2304219e6a25e23b230f5688c0959bf98d1f4ba4011b3")
    container_log = PRIOR / "commands/final-private-sandbox-container/original.log"
    c.require(c.digest(container_log) == "2e7d53ebdc9e7255089f0aaa6a91eb7e709a298174abf379904832610d747946"
              and command["argv"] == ["xcrun", "simctl", "get_app_container", PRIOR_DEVICE, "io.anytype.app", "data"]
              and command["exitCode"] == 0 and command["status"] == "PASS_COMMAND"
              and command["logSHA256"] == c.digest(container_log),
              "Original data-container resolution required")
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / PRIOR_DEVICE
    app_data = Path(container_log.read_text().strip())
    c.require(app_data.resolve() == app_data and app_data.is_dir()
              and app_data.parent == device_root / "data/Containers/Data/Application",
              "Exact retained app-data container required")
    plist = device_root / "device.plist"
    c.require(c.digest(plist) == c.digest(backup_root / "device.plist") == PRIOR_PLIST_SHA,
              "Original device metadata changed")
    def identity(path):
        st = path.lstat()
        c.require(path.resolve() == path and not stat.S_ISLNK(st.st_mode), "Owned root must not be aliased")
        return (st.st_dev, st.st_ino, st.st_mode)
    scopes = {"application-data": app_data,
              "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
              "keychains": device_root / "data/Library/Keychains",
              "device-preferences": device_root / "data/Library/Preferences"}
    identities = {str(p): identity(p) if p.exists() else None for p in [device_root, plist, *scopes.values()]}
    def unchanged_identity():
        for name, expected in identities.items():
            path = Path(name)
            c.require((identity(path) if path.exists() else None) == expected
                      and (expected is not None or not path.is_symlink()),
                      "Original device or private scope root changed during admission")
        c.require(c.digest(plist) == PRIOR_PLIST_SHA, "Original device metadata changed during admission")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "prior-owned-shutdown", "Shutdown")
    original_rows = {}
    for label, path in scopes.items():
        row = backup["scopes"][label]
        unchanged_identity()
        if row["status"] == "NOT_PRESENT":
            c.require(not path.exists() and not path.is_symlink(), "An absent original scope appeared")
            original_rows[label] = None
        else:
            c.require(row["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES", "Unsealed original scope")
            before = checked(backup_root / (label + "-before.json"), row["manifestSHA256"])
            copied = c.decode(c.raw(backup_root / (label + "-copied.json")))
            after = c.decode(c.raw(backup_root / (label + "-after.json")))
            c.require(before == copied == after == retainer.inventory(backup_root / label)
                      == retainer.inventory(path) and len(before) == row["entries"],
                      "Every original private byte and mode must still match the sealed account")
            original_rows[label] = before
        unchanged_identity()
    for name, row in original["finalPrivateSandbox"]["files"].items():
        c.require(row["status"] == "NOT_PRESENT"
                  and not (app_data / "Library/Application Support" / name).exists()
                  and not (app_data / "Library/Application Support" / name).is_symlink(),
                  "Original absent setup witnesses changed")
    for label, path in scopes.items():
        unchanged_identity()
        c.require((retainer.inventory(path) if path.exists() else None) == original_rows[label],
                  "Original persistent account changed during shutdown admission")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "prior-final-shutdown", "Shutdown")
    unchanged_identity()
    proof = {"originalExecutionSHA256": PRIOR_EXECUTION_SHA, "originalAcceptance": "FAIL",
             "originalMethodCount": 0, "custodySHA256": PRIOR_CUSTODY_SHA,
             "backupSHA256": PRIOR_BACKUP_SHA, "devicePlistSHA256": PRIOR_PLIST_SHA,
             "ownedSimulator": PRIOR_DEVICE, "binding": PRIOR_BINDING,
             "allFourScopesUnchanged": True, "originalFixtureAbsent": True,
             "originalFixtureDeadlineExisted": False, "rootIdentity": list(identities[str(device_root)]),
             "priorLookupFailureSHA256": LOOKUP_EXECUTION_SHA,
             "installedAppAdmission": "PENDING_POSTBOOT_BEFORE_ORIGINAL_METHODS",
             "installedAppReinstalled": False, "stateRestored": False, "extraEngineCalls": 0}
    c.write(evidence / "prior-account-admission.json", proof)
    return proof


def admit_installed_app(c, commands, retainer, app, evidence, prior):
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / PRIOR_DEVICE
    def root_identity(path):
        st = path.lstat()
        c.require(path.resolve() == path and not stat.S_ISLNK(st.st_mode), "Canonical installed app/device root required")
        return (st.st_dev, st.st_ino, st.st_mode)
    c.require(root_identity(device_root) == tuple(prior["rootIdentity"]),
              "The exact shutdown-admitted device root must survive owned boot")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "installed-app-before-state", "Booted")
    log, _ = commands.run(["xcrun", "simctl", "get_app_container", PRIOR_DEVICE, "io.anytype.app", "app"],
                           "postboot-installed-app-container", 30, capacity=False)
    installed = Path(c.raw(log, 4096).decode().strip())
    c.require(installed.resolve() == installed and installed.is_dir()
              and installed.name == "Anytype.app"
              and installed.parent.parent == device_root / "data/Containers/Bundle/Application",
              "Exact original installed app path required")
    installed_identity = root_identity(installed)
    producer_identity = root_identity(app)
    producer_inventory = retainer.inventory(app)
    installed_inventory = retainer.inventory(installed)
    content = lambda table: {name: {k: v for k, v in row.items() if k != "mode"}
                             for name, row in table.items()}
    c.require(content(producer_inventory) == content(installed_inventory),
              "Every installed path, kind, content and link must match the exact App14 producer")
    mode_differences = [{"path": name, "producer": producer_inventory[name]["mode"],
                         "installed": row["mode"]} for name, row in installed_inventory.items()
                        if row["mode"] != producer_inventory[name]["mode"]]
    c.write(evidence / "installed-app-original-inventory.json", installed_inventory)
    c.write(evidence / "installed-app-mode-differences.json", mode_differences)
    c.require(root_identity(installed) == installed_identity and root_identity(app) == producer_identity
              and root_identity(device_root) == tuple(prior["rootIdentity"])
              and retainer.inventory(installed) == installed_inventory
              and retainer.inventory(app) == producer_inventory,
              "Exact producer and installed App bytes/modes/identities must remain stable through admission")
    state(c, commands, PRIOR_DEVICE, PRIOR_BINDING, "installed-app-final-state", "Booted")
    proof = {"reusedExactInstalledContent": True, "installedAppEntries": len(installed_inventory),
             "installedModeDifferences": len(mode_differences), "installsExecuted": 0,
             "admissionStage": "AFTER_OWNED_BOOT_BEFORE_ANY_ORIGINAL_METHOD",
             "priorSourceAdmissionSHA256": c.digest(evidence / "prior-account-admission.json"),
             "priorLookupFailureSHA256": LOOKUP_EXECUTION_SHA,
             "inventorySHA256": c.digest(evidence / "installed-app-original-inventory.json"),
             "modeDifferencesSHA256": c.digest(evidence / "installed-app-mode-differences.json")}
    c.write(evidence / "postboot-installed-app-admission.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--qualify-only", action="store_true")
    args = parser.parse_args()
    src = module(Path(__file__).with_name("run_app13_observed_heart_source_capture.py"),
                 CAPTURE_SHA, "c_original_source_capture")
    sys.path.insert(0, str(CONTROL))
    c = module(CONTROL / "combined_heart_semantics_current.py", CORE_SHA, "c_app14_shared_core")
    c.require(sys.platform == "darwin" and c.digest(CONTROL / "combined_heart_semantics_current.py") == CORE_SHA,
              "Original actual Apple runtime admission required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent
              and args.root.parent == Path("/Users/m1/development/anytype-c-active-20261125/app14-fresh-source-capture")
              and not args.root.exists(), "Fresh protected C execution root required")
    args.root.mkdir(mode=0o700)
    os.umask(0o077)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    private = args.root / "private"; private.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    result = {"protocol": "pinkha-app14-postboot-installation-admission-retry-v1", "status": "FAIL",
        "sourceCommit": SOURCE, "uiSourceCommit": UI_SOURCE_COMMIT, "originalCUIFileSHA256": UI_SOURCE_SHA,
        "controllerSHA256": c.digest(Path(__file__)), "captureHelperSHA256": CAPTURE_SHA,
        "coreSHA256": CORE_SHA, "sameSourceAppAndUI": True,
        "admissionSHA256": BASE_ADMISSION_SHA, "qualificationOnly": args.qualify_only,
        "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "stages": {},
        "factoryMethodsExecuted": 0, "originalSimulatorStateReused": True,
        "originalMethodsReplayed": 0, "priorFixtureDeadlineExisted": False,
        "wholeSpaceMigration": False, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
        "priorExternallyLostAccountRestored": False, "priorFixtureDeadlineExtended": False}
    binding = dict(PRIOR_BINDING)
    result["binding"] = binding
    result["bindingIdentityKind"] = "unique local microsecond receipt identity, not GitHub Actions"
    built = {}; device = None; claimed_boot = False
    app_data = None; prepared_sandbox = None; fixture = None; deadline = None
    retainer = None; created_root_identity = None
    try:
        retainer = module(Path(__file__).with_name("retain_fresh_c_source_account.py"),
                          RETAINER_SHA, "c_fresh_owned_account_retainer")
        c.require(c.digest(BASE_ADMISSION) == BASE_ADMISSION_SHA, "Exact same-source App14 base admission required")
        base = c.decode(c.raw(BASE_ADMISSION))
        c.require(base["controllerSHA256"] == CORE_SHA and base["sourceCommit"] == SOURCE
                  and c.digest(Path(base["sourceRoot"]) / UI_PATH) == UI_SOURCE_SHA,
                  "Original compiled C method source differs")
        mask = os.umask(0)
        try:
            result["sourceAdmission"], built, app = c.admit_and_clone_products(base, args.root, evidence, commands)
        finally:
            os.umask(mask)
        result["sameSourceUIAdmission"] = {"sourceCommit": SOURCE, "testFileSHA256": UI_SOURCE_SHA,
            "admissionSHA256": BASE_ADMISSION_SHA, "UIOverride": False}
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer",
                     "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        import importlib
        c.common = importlib.import_module("contracts")
        c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract")
        c.boundary = importlib.import_module("page154_boundary")
        c.native.binding(binding)
        prior = admit_prior(c, commands, retainer, app, evidence)
        result["priorAccountAdmission"] = prior
        if args.qualify_only:
            result["status"] = "QUALIFIED_SOURCE_PRODUCTS_ONLY_NO_ACCOUNT_OR_TEST"
        else:
            c.require(c.shutil.disk_usage(args.root).free >= 2 * 1024**3 + 768 * 1024**2,
                      "Measured fresh simulator/account growth plus emergency floor unavailable")
            result["resourcePolicy"] = {"estimatedNewBytes": 768 * 1024**2,
                "emergencyFreeBytes": 2 * 1024**3,
                "reason": "Existing exact shutdown simulator and installed App; APFS-cloned products, two bounded source bundles and original XCTest/private logs; no new simulator, install, compiler or dependency download."}
            log, _ = commands.run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtime-inventory", 30)
            rows = [r for r in c.decode(c.raw(log))["runtimes"] if r.get("identifier") == c.RUNTIME]
            c.require(len(rows) == 1 and rows[0].get("version") == c.OS_VERSION
                      and rows[0].get("buildversion") == c.OS_BUILD and rows[0].get("isAvailable") is True,
                      "Exact installed runtime required")
            c.write(evidence / "execution-intent.json", {"binding": binding,
                "selectors": [c.STAGES["preparation"], src.SELECTOR],
                "purpose": "retry only uninvoked original preparation, then actual source review/close/recapture",
                "noEMountedOrSourceAcceptanceReplay": True})
            device = PRIOR_DEVICE
            result["ownedSimulator"] = device
            c.write(evidence / "owned-simulator.json", {"udid": device, "runtime": rows[0], "deviceType": c.DEVICE,
                "originalCustodySHA256": PRIOR_CUSTODY_SHA, "newDeviceCreated": False})
            created_root_identity = tuple(prior["rootIdentity"])
            state(c, commands, device, binding, "retained-created-state", "Shutdown")
            claimed_boot = True
            commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator", 60)
            commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-owned-boot", 180)
            state(c, commands, device, binding, "fresh-booted-state", "Booted")
            result["originalAppInstallation"] = admit_installed_app(c, commands, retainer, app, evidence, prior)
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
            # Date uses the original Cocoa reference epoch; the unchanged
            # mounted contract above validates that exact fractional value.
            reference_date = fixture["createdAt"]
            c.require(type(reference_date) in (int, float) and math.isfinite(reference_date),
                      "Original native fixture creation time required")
            created = reference_date + 978307200
            c.require(0 <= time.time() - created < 7200, "Original new fixture creation time required")
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
            c.require(c.digest(CONTROL / "combined_heart_semantics_current.py") == CORE_SHA
                      and c.digest(BASE_ADMISSION) == BASE_ADMISSION_SHA, "Original App14 admission changed")
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
