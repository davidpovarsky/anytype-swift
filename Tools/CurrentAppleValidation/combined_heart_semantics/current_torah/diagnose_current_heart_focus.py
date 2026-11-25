"""Diagnose real text focus on the exact partially linked owned account.

Original preparation/mounted results and account remain authoritative. This
controller neither prepares nor restores an account, installs an App, builds,
or extends the fixture deadline. Original UI/native predicates are reused.
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
import combined_heart_semantics_focus as c
import retain_owned_heart_account as account

CORE = "da322f6f9ce79e66c10589e7b8c818fafc00647ba326ce32a5a5337a25f0f4a0"
RETENTION = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
ADMISSION = "874d31f730e0b27c618cc61702f705089dec6d031f8821b7ea79460d84c95aab"
SOURCE = "5c05a612e4054a4adfa7f812343be6a15871cc89"
PRIOR = Path("/Users/m1/builds/e-combined-current-20261125/fresh-focus5c05-attempt1")
PRIOR_EXECUTION = "1ca2434c89f8628d97fb26ed88d587df8bcb72a129338f8a445e31149b472f25"
PRIOR_BACKUP = "a1709f2f5c7073456cd002eaba873c718d48cf455aa8e767c4675b7b9e7384ce"
EXPECTED_PLIST = "e2037cb23241369e59b1a2a7be013c7de5dc8545f1bac91a5a9465d39ba0c812"
DEVICE = "802B8243-627D-42CD-AE69-16A4E0605A99"
FIXTURE_SHA = "04c053413947c115b9db4d94bd72a243428ecfab46ac8124049f47a0303d8c68"
CAPTURE_SHA = "a3afbf5b66a5f68166aecd3387a58362e149c16c09d68eea81e9cd1ec9ccb614"
REOPEN_SHA = "97092589f811f725624f30ab80c8e9640a9d8c082be28333cb656f6e461e8e11"
EXPIRY = 1795635026.6347451


def admit_prior(admission):
    c.require(c.digest(PRIOR / "evidence/execution.json") == PRIOR_EXECUTION,
              "Exact original failure must remain unchanged")
    prior = c.decode(c.raw(PRIOR / "evidence/execution.json"))
    c.require(prior["status"] == "FAIL" and prior["sourceCommit"] == admission["sourceCommit"] == SOURCE
              and prior["controllerSHA256"] == "f5b9040dec5c940e52309f5d87dd6ce1bf2395344bdeaebfac0058c61fd16213" and prior["nativeManifestSHA256"] == c.MANIFEST
              and prior["heartOverlaySHA256"] == c.OVERLAY and prior["ownedSimulator"] == DEVICE
              and prior["appBuilds"] == prior["uiBuilds"] == prior["nativeBuilds"] == 0,
              "Exact prior source/native/owned device required")
    c.require(set(prior["stages"]) == {"preparation", "mounted", "linked-ui"}
              and [prior["stages"][x]["status"] for x in ("preparation", "mounted", "linked-ui")]
              == ["PASS", "PASS", "FAIL"]
              and all(x["testInvoked"] is True for x in prior["stages"].values()),
              "Exactly the two accepted originals and first-launch failure required")
    cleanup = prior["cleanup"]
    c.require(cleanup["status"] == "PASS" and cleanup["errors"] == []
              and cleanup["ownedSimulatorDeleted"] is False
              and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
              and all(x["absentAtOriginalExit"] is True for x in cleanup["groups"]),
              "Original ended owned processes and retained shutdown account required")
    for name in ("preparation", "mounted"):
        folder = PRIOR / "evidence" / name
        log = PRIOR / "commands" / (name + "-test") / "original.log"
        c.qualify_enumeration(c.decode(c.raw(folder / "enumeration.json")), c.STAGES[name])
        actual = c.qualify_execution(c.decode(c.raw(folder / "summary.json")),
            c.decode(c.raw(folder / "tests.json")), c.STAGES[name], DEVICE, log)
        c.require(c.decode(json.dumps(actual).encode()) == prior["stages"][name]["actual"]
                  and c.digest(log) == prior["stages"][name]["command"]["logSHA256"]
                  and prior["stages"][name]["command"]["status"] == "PASS_COMMAND",
                  "Original named setup outcomes/stdout changed")
    folder = PRIOR / "evidence/linked-ui"
    summary = c.decode(c.raw(folder / "summary.json"))
    c.require({k: summary[k] for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
              == {"totalTestCount": 1, "passedTests": 0, "failedTests": 1, "skippedTests": 0},
              "The original failed focus preparation must remain failed")
    c.require(len(summary["testFailures"]) == 1
              and summary["testFailures"][0]["testIdentifierString"] ==
              "SemanticAnchorPage154MountedUITests/testExistingSemanticAnchorSourceLinkEditAndColdReopen()"
              and summary["testFailures"][0]["failureText"].startswith(
              "Failed to synthesize event: Neither element nor any descendant has keyboard focus."),
              "Only the original observed keyboard focus failure is admitted")
    log = PRIOR / "commands/linked-ui-test/original.log"
    c.require(c.digest(log) == "5b3635caec68839e18a440cfc6a290ccf6946fbd5025b299fbdefd36f428e9ae",
              "Exact original partial-link/focus failure log required")
    text = c.raw(log).decode()
    c.require('Tap "torah-search-link-reference:Genesis 1:1" Button' in text
              and "Added attachment named 'heart-semantic-source-canonical-visible-link'" in text
              and "** TEST EXECUTE FAILED **" in text,
              "Preserve the actual partial link and failed preparation without claiming acceptance")
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
              and c.digest(device_root / "device.plist") == c.digest(directory / "device.plist") == EXPECTED_PLIST,
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
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    c.require(c.digest(Path(__file__)) == args.controller_sha256 and c.digest(Path(c.__file__)) == CORE
              and c.digest(Path(account.__file__)) == RETENTION
              and c.digest(Path(__file__).with_name("combined_heart_observations_gateway.py")) == c.OBSERVATION_HELPER,
              "Exact current original helpers/controller required")
    c.require(c.digest(args.admission) == ADMISSION, "Current source-bound admission required")
    admission = c.decode(c.raw(args.admission))
    prior = admit_prior(admission)
    c.require(args.root.is_absolute() and args.root.parent == PRIOR.parent
              and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh continuation output required")
    os.umask(0o022)
    args.root.mkdir(mode=0o700)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    private = args.root / "private"; private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", c.raw(args.admission))
    commands = c.Commands(args.root / "commands", args.root)
    result = {"status": "FAIL", "sourceCommit": SOURCE, "controllerSHA256": args.controller_sha256,
              "coreControllerSHA256": CORE, "priorExecutionSHA256": PRIOR_EXECUTION,
              "priorBackupSHA256": PRIOR_BACKUP, "nativeManifestSHA256": c.MANIFEST,
              "heartOverlaySHA256": c.OVERLAY, "binding": prior["binding"], "ownedSimulator": DEVICE,
              "originalSetupReused": {k: prior["stages"][k]["actual"] for k in ("preparation", "mounted")},
              "setupMethodsReexecuted": 0, "purpose": "readonly-real-UI-focus-diagnostic", "fixtureRestorations": 0, "fixtureDeadlineChanges": 0,
              "newSimulatorsCreated": 0, "appInstalls": 0, "appBuilds": 0, "uiBuilds": 0,
              "nativeBuilds": 0, "stages": {}, "fullEAcceptance": False, "physicalDevice": "NOT_RUN"}
    built = {}; owned_boot = False
    try:
        source_proof, built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        result["sourceAdmission"] = source_proof
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts")
        c.native = native = importlib.import_module("consumer_contract")
        c.mounted = mounted = importlib.import_module("mounted_contract")
        c.boundary = boundary = importlib.import_module("page154_boundary")
        policy = importlib.import_module("page154_contract")
        warning = importlib.import_module("warning_profile")
        specialized = importlib.import_module("combined_heart_observations_gateway")
        c.require(specialized.COMBINED_VERSION == c.VERSION and specialized.ORIGINAL_OVERLAY == c.OVERLAY,
                  "Exact original native observation profile required")
        binding = prior["binding"]
        payloads = {}
        for name, expected in ((c.FIXTURE, FIXTURE_SHA), (c.CAPTURE, CAPTURE_SHA), (c.REOPEN, REOPEN_SHA)):
            value = c.raw(PRIOR / "private" / name)
            c.require(c.sha(value) == expected, "Original private setup witness changed")
            c.write_bytes(private / name, value); payloads[name] = value
        fixture_raw, capture_raw, reopen_raw = (payloads[x] for x in (c.FIXTURE, c.CAPTURE, c.REOPEN))
        fixture, capture, reopen = map(c.decode, (fixture_raw, capture_raw, reopen_raw))
        mounted.fixture(fixture, binding)
        def deadline():
            c.require(fixture["createdAt"] + 978307200 + 7200 == EXPIRY
                      and 0 <= time.time() - (fixture["createdAt"] + 978307200) <= 7200,
                      "Original two-hour fixture deadline must remain unchanged")
        deadline()
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        boundaries = {}
        witness = capture["nativeBoundaryEvidence"]
        for role, name in boundary.FILES.items():
            value = c.raw(PRIOR / "private" / name, boundary.MAXIMUM)
            c.require(c.sha(value) == witness["files"][role]["sha256"]
                      and len(value) == witness["files"][role]["bytes"], "Original native boundary changed")
            c.write_bytes(private / name, value); boundaries[role] = value
        result["nativeBoundaryComparison"] = boundary.verify(boundaries, fixture, capture, native, mounted)
        c.require(result["nativeBoundaryComparison"] == prior["nativeBoundaryComparison"]
                  and result["nativeBoundaryComparison"]["projectionFieldCount"] == 9,
                  "Exact original mounted boundary acceptance required")
        result["originalAttachments"] = policy.mounted_attachments(PRIOR / "evidence/mounted/private-attachments",
            DEVICE, capture, reopen, binding, warning)
        result["accountAdmission"] = admit_shutdown_account(commands, prior)
        deadline()
        owned_boot = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-retained-owned-simulator", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-boot", 180)
        log, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"], "verify-live-account-container", 30)
        live = Path(c.raw(log).decode().strip())
        c.require(live == Path(c.raw(PRIOR / "commands/final-private-sandbox-container/original.log").decode().strip()),
                  "No account relocation or restore is admitted")
        for name in (c.FIXTURE, c.CAPTURE, c.REOPEN, *boundary.FILES.values()):
            c.require(c.raw(live / "Library/Application Support" / name) == c.raw(private / name),
                      "Original live native witness changed before continuation")
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        def run(name, additions):
            deadline()
            kind = "app" if c.STAGES[name].startswith("AnytypeTests/") else "ui"
            value = c.stage(commands, evidence, name, built[kind], app, binding, DEVICE, dict(base, **additions))
            result["stages"][name] = value
            c.require(value["status"] == "PASS", name + " actual method failed")
        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        sha, decode, require, write = c.sha, c.decode, c.require, c.write
        app_file, continuation_ui, continuation_native = c.app_file, c.continuation_ui, c.continuation_native
        STAGES, device = c.STAGES, DEVICE
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": c.sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = c.sha(payload)
        diagnostic = "focus-diagnostic"
        selector = c.UI_SUITE + "testDiagnoseExistingSemanticAnchorFocusAfterSourceDismissal"
        c.require(diagnostic not in c.STAGES, "No original selection may be overwritten")
        original_selectors = dict(c.STAGES)
        c.STAGES[diagnostic] = selector
        c.require({k: v for k, v in c.STAGES.items() if k != diagnostic} == original_selectors,
                  "Every original acceptance selector remains unchanged")
        run(diagnostic, dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE="linked"))
        ax, origin = policy.attachment(evidence / diagnostic / "private-attachments",
            "heart-semantic-focus-before-real-key-ax", selector, DEVICE, maximum=128 * 1024)
        app_pids = set(re.findall(r"Application, [^\n]*\bpid: (\d+)", ax.decode()))
        c.require(len(app_pids) == 1, "One actual App PID from the original before-key AX witness required")
        pid = int(next(iter(app_pids)))
        observed = c.app_file(commands, DEVICE, private, "pinkha-semantic-source-entry-" + str(pid) + ".json",
                              "preserve-focus-input-observer", maximum=65536)
        trace = c.decode(observed)
        c.require(trace["protocol"] == "pinkha-heart-semantic-source-entry-observation-v1"
                  and trace["processID"] == pid and trace["sourceSHA"] == SOURCE
                  and all(trace[key] == binding[key] for key in ("runID", "runAttempt", "nonce"))
                  and trace["capacityReached"] is False and trace["originalMountedObserverEnabled"] is False
                  and trace["extraEngineCalls"] == trace["automaticRetries"] == trace["selectionChanges"]
                  == trace["menuDismissals"] == 0, "Original read-only input observer identity/scope differs")
        events = trace["events"]
        c.require(1 <= len(events) <= 64 and all(events[i]["uptime"] <= events[i+1]["uptime"]
                  for i in range(len(events)-1)), "Original bounded chronological input observations required")
        handlers = [i for i, e in enumerate(events) if e["stage"] == "source-menu-handler"]
        returns = [i for i, e in enumerate(events) if e["stage"] == "shared-source-session-return"
                   and e["state"]["searchPresented"] is True]
        c.require(len(handlers) == len(returns) == 1 and handlers[0] < returns[0],
                  "The real preparation must not reopen the semantic link")
        selections = [(i, e["state"]) for i, e in enumerate(events) if e["stage"] == "source-menu-input"]
        c.require(len(selections) >= 3 and len({s["inputIdentity"] for _, s in selections}) == 1
                  and all(s["firstResponder"] is True and s["editable"] is True and s["windowPresent"] is True
                          and s["selectedLength"] == len("Anchor".encode("utf-16-le")) // 2 for _, s in selections)
                  and sum(i > returns[0] for i, _ in selections) >= 2,
                  "The same original input must really regain focus and full range before and after the real arrow")
        result["focusDiagnosticProof"] = {"scope": "REAL_UI_PREPARATION_ONLY_NOT_ACCEPTANCE",
            "observedPID": pid, "observerSHA256": c.sha(observed), "observerBytes": len(observed),
            "beforeKeyAXSHA256": c.sha(ax), "sameInputIdentities": 1, "focusedFullRangeObservations": len(selections),
            "realSourceMenuHandlers": 1, "explicitContentMutationsInDiagnosticMethod": 0,
            "originalAcceptanceMethodsExecuted": 0, "nativeSourceReadbackAcceptance": False}
        deadline()
        result["status"] = "PASS_REAL_DOUBLE_TAP_FOCUS_PREPARATION_NOT_ACCEPTANCE"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        cleanup = {"status": "PASS", "groups": [], "errors": [], "ownedSimulatorDeleted": False,
                   "ownedSimulatorRetainedForRecovery": DEVICE}
        if owned_boot:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE,
                    private / "final-sandbox-originals", application_invoked=True)
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
            else:
                try:
                    present = c.Commands.present(group)
                    cleanup["groups"].append({"pgid": group, "present": present})
                    c.require(not present, "Unresolved owned process group retained")
                except BaseException as exc:
                    cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        if owned_boot:
            try:
                commands.run(["xcrun", "simctl", "shutdown", DEVICE], "cleanup-shutdown", 60, capacity=False)
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        try:
            result["finalProducts"] = {k: c.product_integrity(v) for k, v in built.items()}
            for name, expected in c.HELPERS.items():
                c.require(c.digest(args.root / "helpers" / name) == expected, "Frozen original validator changed")
        except BaseException as exc:
            cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        result["cleanup"] = cleanup
        result["actualMethodInvocationWitnesses"] = [x for x in c.STAGES
            if (args.root / "commands" / (x + "-test") / "started.json").is_file()]
        result["finishedAt"] = time.time()
        if cleanup["status"] != "PASS": result["status"] = "FAIL"
        c.write(evidence / "execution.json", result)
    seal = {"status": "FAIL", "originalExecutionSHA256": c.digest(evidence / "execution.json")}
    try:
        seal["privateAccount"] = account.retain(args.root, seal["originalExecutionSHA256"])
        seal["retentionSHA256"] = c.digest(private / "owned-account-originals/retention.json")
        seal["devicePlistSHA256"] = c.digest(private / "owned-account-originals/device.plist")
        seal["status"] = "PASS_PRIVATE_RETENTION_WITH_ORIGINAL_OUTCOME_PRESERVED"
    except BaseException as exc:
        seal["firstFailure"] = c.error(exc)
    c.write(evidence / "retention-completion.json", seal)
    print(json.dumps({"status": result["status"], "retentionStatus": seal["status"],
                      "stages": {k: v["status"] for k, v in result["stages"].items()},
                      "originalSetupReexecuted": 0, "diagnosticOnly": True}, sort_keys=True))
    return 0 if result["status"] == "PASS_REAL_DOUBLE_TAP_FOCUS_PREPARATION_NOT_ACCEPTANCE" and seal["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
