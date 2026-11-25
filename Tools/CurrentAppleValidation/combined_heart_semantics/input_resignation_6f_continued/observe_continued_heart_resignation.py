"""Observe the exact original 6f source-menu failure without changing its UI.

Only one original failed method is repeated, on its sealed original account and
deadline. The debugger reads stack/register metadata only. No result from this
diagnostic establishes acceptance, and the owned account is retained on failure.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import combined_heart_semantics_gateway as c
import retain_owned_heart_account as account
import resume_installed_modes_heart_6f as accepted

CORE = "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
RETENTION = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
OBSERVER = "ac5d1cba3fe7d56f6c7e1e343073948e175d3efafe20a9a39e7cdc7526ac55b7"
WATCHER = "4ecf10121274850e67ca69fca63aa36ae61c630ddf4d57cb187b3781527fcb8b"
SOURCE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
ADMISSION = "82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
PRIOR = Path("/Users/m1/builds/e-combined-current-20261125/prepared-header6f-installedmodes-continuation1")
CONTINUATION = "26667f90da9dd486be5b0d50425997c4d3ccbda77dc80dc042beab222fcea394"
EXPECTED_EXECUTION = "8c86fe5eaf61d6ad02bd7d41b630a4e94b82ad8f6a66d5719ef5c3f3aebf1fd1"
EXPECTED_BACKUP = "f4854a2c8a01cc8ad2f1facee6cbf96e93bc9c6433e7acdfc2ad5da270f467a2"
EXPECTED_TRACE = "82ecc571643e8d41f7a655c4611273aac5decdf185bfc453be8f7e3526551e12"
EXPECTED_PLIST = "3f9d7d18a3bf71e7dd4f605512eba755873549be67026488e3c3620db7136c99"
DEVICE = "A4489891-C78A-4E78-8649-6E9525A7FDB5"
PRIOR_EXECUTION = None
PRIOR_BACKUP = None
PRIOR_TRACE = None


def admit_prior(admission):
    c.require(c.digest(Path(accepted.__file__)) == CONTINUATION, "Exact accepted preparation continuation required")
    _, preparation = accepted.admit_prior(admission)
    path = PRIOR / "evidence/execution.json"
    c.require(c.digest(path) == PRIOR_EXECUTION, "Exact original failed execution required")
    prior = c.decode(c.raw(path))
    c.require(prior["status"] == "FAIL" and prior["sourceCommit"] == admission["sourceCommit"] == SOURCE
              and prior["controllerSHA256"] == CONTINUATION and prior["coreControllerSHA256"] == CORE
              and prior["priorExecutionSHA256"] == accepted.PRIOR_EXECUTION
              and prior["nativeManifestSHA256"] == c.MANIFEST
              and prior["heartOverlaySHA256"] == c.OVERLAY and prior["ownedSimulator"] == DEVICE,
              "Original source/native/device owner changed")
    c.require(set(prior["stages"]) == {"mounted", "linked-ui"}
              and [prior["stages"][name]["status"] for name in ("mounted", "linked-ui")]
              == ["PASS", "FAIL"]
              and prior["binding"] == preparation["binding"]
              and prior["originalPreparationReused"]["actual"] == preparation["stages"]["preparation"]["actual"]
              and prior["originalPreparationReused"]["executedInThisContinuation"] is False
              and prior["preparationMethodsReexecuted"] == prior["fixtureRestorations"]
              == prior["fixtureDeadlineChanges"] == prior["newSimulatorsCreated"] == 0
              and all(row["testInvoked"] is True for row in prior["stages"].values()),
              "Two actual original passes and one actual source UI failure required")
    cleanup = prior["cleanup"]
    c.require(cleanup["status"] == "PASS" and cleanup["errors"] == []
              and cleanup["ownedSimulatorDeleted"] is False
              and cleanup["ownedSimulatorRetainedForRecovery"] == DEVICE
              and all(row["absentAtOriginalExit"] is True for row in cleanup["groups"]),
              "Original completed cleanup and retained simulator required")
    for name in ("mounted",):
        folder = PRIOR / "evidence" / name
        log = PRIOR / "commands" / (name + "-test") / "original.log"
        actual = c.qualify_execution(c.decode(c.raw(folder / "summary.json")),
            c.decode(c.raw(folder / "tests.json")), c.STAGES[name], DEVICE, log)
        c.require(c.decode(json.dumps(actual).encode()) == prior["stages"][name]["actual"]
                  and c.digest(log) == prior["stages"][name]["command"]["logSHA256"]
                  and prior["stages"][name]["command"]["exitCode"] == 0,
                  "Original actual setup exports/stdout differ")
    folder = PRIOR / "evidence/linked-ui"
    summary = c.decode(c.raw(folder / "summary.json"))
    c.require({key: summary[key] for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
              == {"totalTestCount": 1, "passedTests": 0, "failedTests": 1, "skippedTests": 0},
              "Original failed method may not be reclassified")
    c.qualify_enumeration(c.decode(c.raw(folder / "enumeration.json")), c.STAGES["linked-ui"])
    log = PRIOR / "commands/linked-ui-test/original.log"
    text = c.raw(log).decode("utf-8", "replace")
    c.require(c.digest(log) == prior["stages"]["linked-ui"]["command"]["logSHA256"]
              and 'Tap "Sources for anchored text"' in text and 'torah-sources-search-field' in text
              and '** TEST EXECUTE FAILED **' in text, "Original real source tap and absent search required")
    traces = list((PRIOR / "private/final-sandbox-originals").glob("pinkha-semantic-source-entry-*.json"))
    c.require(len(traces) == 1 and c.digest(traces[0]) == PRIOR_TRACE, "Exact original no-handler observation required")
    trace = c.decode(c.raw(traces[0]))
    c.require(trace["capacityReached"] is False and trace["extraEngineCalls"] == 0
              and trace["selectionChanges"] == 0 and trace["menuDismissals"] == 0
              and all(trace[key] == value for key, value in prior["binding"].items())
              and not any(row["stage"] == "source-menu-handler" for row in trace["events"]),
              "The original observer must show no source handler or injected action")
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
    global PRIOR_EXECUTION, PRIOR_BACKUP, PRIOR_TRACE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    parser.add_argument("--prior-execution-sha256", required=True)
    parser.add_argument("--prior-backup-sha256", required=True)
    parser.add_argument("--prior-trace-sha256", required=True)
    args = parser.parse_args()
    for value in (args.prior_execution_sha256, args.prior_backup_sha256, args.prior_trace_sha256):
        c.require(re.fullmatch(r"[0-9a-f]{64}", value) is not None, "Exact completed original receipt hashes required")
    PRIOR_EXECUTION, PRIOR_BACKUP, PRIOR_TRACE = (args.prior_execution_sha256,
                                               args.prior_backup_sha256, args.prior_trace_sha256)
    c.require((PRIOR_EXECUTION, PRIOR_BACKUP, PRIOR_TRACE)
              == (EXPECTED_EXECUTION, EXPECTED_BACKUP, EXPECTED_TRACE), "Exact observed terminal receipt pins required")
    own = Path(__file__).resolve().parent
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple Silicon required")
    c.require(c.digest(Path(__file__)) == args.controller_sha256 and c.digest(Path(c.__file__)) == CORE
              and c.digest(Path(account.__file__)) == RETENTION
              and c.digest(own / "source_entry_trace_lldb.py") == OBSERVER
              and c.digest(own / "source_entry_trace_watch.py") == WATCHER,
              "Exact reviewed controller, shared admission, retention and observer required")
    c.require(c.digest(args.admission) == ADMISSION, "Exact existing 6f same-source admission required")
    admission = c.decode(c.raw(args.admission))
    prior = admit_prior(admission)
    c.require(args.root.is_absolute() and args.root.parent == PRIOR.parent
              and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh diagnostic root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    c.write_bytes(evidence / "admission.json", c.raw(args.admission))
    commands = c.Commands(args.root / "commands", args.root)
    built = {}; boot_owned = False; future = None; pool = None
    stop = private / "stop-observer"
    result = {"status": "DIAGNOSTIC_INCOMPLETE_NOT_ACCEPTANCE", "sourceCommit": SOURCE,
              "controllerSHA256": args.controller_sha256, "nativeManifestSHA256": c.MANIFEST,
              "heartOverlaySHA256": c.OVERLAY, "ownedSimulator": DEVICE, "binding": prior["binding"],
              "priorExecutionSHA256": PRIOR_EXECUTION, "priorBackupSHA256": PRIOR_BACKUP,
              "appBuilds": 0, "nativeBuilds": 0, "uiBuilds": 0, "setupMethodsReexecuted": 0,
              "factoryMethodsExecuted": 0, "fixtureDeadlineChanges": 0, "extraEngineCallsByObserver": 0,
              "targetExpressions": 0, "fullEAcceptance": False, "physicalDevice": "NOT_RUN",
              "stages": {}, "startedAt": time.time()}
    try:
        result["accountAdmission"] = admit_shutdown_account(commands, prior)
        result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts"); c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract"); c.boundary = importlib.import_module("page154_boundary")
        specialized = importlib.import_module("combined_heart_observations_gateway")
        c.require(c.digest(Path(specialized.__file__)) == c.OBSERVATION_HELPER, "Original current observation helper required")
        binding = prior["binding"]
        fixture_raw = c.raw(PRIOR / "private/final-sandbox-originals" / c.FIXTURE)
        c.mounted.fixture(c.decode(fixture_raw), binding)
        boot_owned = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-boot", 180)
        baseline = private / "baseline"; baseline.mkdir(mode=0o700)
        actual = {}
        for index, filename in enumerate((c.FIXTURE, c.CAPTURE, c.REOPEN, *c.boundary.FILES.values())):
            original = c.raw(PRIOR / "private/final-sandbox-originals" / filename)
            row = prior["finalPrivateSandbox"]["files"][filename]
            c.require(row == {"status": "COPIED_ORIGINAL", "bytes": len(original), "sha256": c.sha(original)},
                      "Original retained native witness changed")
            actual[filename] = c.app_file(commands, DEVICE, baseline, filename, "baseline-" + str(index))
            c.require(actual[filename] == original, "Live original native witness changed")
        fixture_raw, capture_raw, reopen_raw = (actual[name] for name in (c.FIXTURE, c.CAPTURE, c.REOPEN))
        fixture, capture, reopen = map(c.decode, (fixture_raw, capture_raw, reopen_raw))
        c.mounted.fixture(fixture, binding)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        result["nativeBoundaryComparison"] = c.boundary.verify(
            {role: actual[name] for role, name in c.boundary.FILES.items()}, fixture, capture, c.native, c.mounted)
        c.require(result["mountedProof"] == prior["mountedProof"]
                  and result["nativeBoundaryComparison"] == prior["nativeBoundaryComparison"],
                  "Original native/canonical proof changed")
        watcher = importlib.import_module("source_entry_trace_watch")
        c.require(Path(watcher.__file__).resolve() == own / "source_entry_trace_watch.py", "Foreign process watcher")
        trace = private / "original-entry-observation.json"
        config = {"device": DEVICE, "binding": binding, "excludePIDs": watcher.owned_app_pids(DEVICE),
                  "output": str(trace), "stopFile": str(stop), "observer": str(own / "source_entry_trace_lldb.py"),
                  "observerSHA256": OBSERVER}
        config_path = private / "observer-config.json"; c.write(config_path, config)
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(commands.run, [sys.executable, str(own / "source_entry_trace_watch.py"), str(config_path)],
                             "entry-observer", 200, checked=False, capacity=False)
        env = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            env["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        env.update(PINKHA_SEMANTIC_MOUNTED_TESTING="1", PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON=fixture_raw.decode(),
                   PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256=c.sha(fixture_raw), PINKHA_SEMANTIC_SOURCE_UI_PHASE="linked")
        for key, value in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = value.decode()
            env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = c.sha(value)
        result["stages"]["linked-ui"] = c.stage(commands, evidence, "linked-ui", built["ui"], app, binding, DEVICE, env)
        result["status"] = "ORIGINAL_UI_DIAGNOSTIC_FINISHED_NOT_ACCEPTANCE"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        errors = []
        observation_errors = []
        stop.write_text("Detach the owned observer; preserve original application state.\n")
        if future:
            try:
                _, result["observerCommand"] = future.result(timeout=35)
                c.require(result["observerCommand"]["status"] == "PASS_COMMAND"
                          and result["observerCommand"]["exitCode"] == 0, "Owned observer command failed")
                observed = c.decode(c.raw(private / "original-entry-observation.json"))
                c.require(observed["status"] == "OBSERVATION_FINISHED_NOT_ACCEPTANCE"
                          and observed["observationErrors"] == [] and observed["capacityReached"] is False
                          and observed["device"] == DEVICE and observed["binding"] == prior["binding"]
                          and observed["extraEngineCalls"] == observed["targetExpressions"]
                          == observed["targetRegisterWrites"] == observed["menuDismissals"] == 0
                          and observed["fixtureDeadlineChanges"] == 0,
                          "Original bounded read-only observation did not finish successfully")
                c.require(any(row["stage"] == "source-action-attempt-entry" for row in observed["events"]),
                          "Original selected source action was not observed")
            except BaseException as exc: observation_errors.append({"phase": "observer-completion", **c.error(exc)})
        if pool: pool.shutdown(wait=True)
        if boot_owned:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE, private / "final-sandbox-originals",
                    application_invoked=(any(row.get("testInvoked") is True for row in result["stages"].values())
                                         or (args.root / "commands/linked-ui-test/started.json").is_file()
                                         or prior["stages"]["mounted"]["testInvoked"] is True))
            except BaseException as exc: errors.append({"phase": "private-retention", **c.error(exc)})
            try:
                _, shutdown = commands.run(["xcrun", "simctl", "shutdown", DEVICE], "shutdown-owned-device", 60,
                                           checked=False, capacity=False)
                c.require(shutdown["exitCode"] == 0, "Owned shutdown failed")
            except BaseException as exc: errors.append({"phase": "shutdown", **c.error(exc)})
        try: result["finalProducts"] = {name: c.product_integrity(row) for name, row in built.items()}
        except BaseException as exc: errors.append({"phase": "product-retention", **c.error(exc)})
        for group in commands.groups:
            if group not in commands.absent_groups:
                errors.append({"phase": "owned-group-exit-not-proven", "pgid": group})
        trace = private / "original-entry-observation.json"
        if trace.exists(): result["observerOriginal"] = {"bytes": trace.stat().st_size, "sha256": c.digest(trace)}
        result["cleanup"] = {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "ownedSimulatorDeleted": False, "ownedSimulatorRetainedForRecovery": DEVICE,
            "groups": [{"pgid": group, "absentAtOriginalExit": group in commands.absent_groups,
                        "historicalGroupReprobed": False} for group in commands.groups]}
        result["observationErrors"] = observation_errors
        if errors or observation_errors:
            result["status"] = "DIAGNOSTIC_FAILED_NOT_ACCEPTANCE"
        result["finishedAt"] = time.time()
        c.write(evidence / "execution.json", result)
    sealed = {"status": "NOT_SEALED", "originalExecutionSHA256": c.digest(evidence / "execution.json")}
    if boot_owned and result["cleanup"]["status"] == "PASS":
        try:
            sealed["privateAccount"] = account.retain(args.root, sealed["originalExecutionSHA256"])
            sealed["retentionSHA256"] = c.digest(private / "owned-account-originals/retention.json")
            sealed["devicePlistSHA256"] = c.digest(private / "owned-account-originals/device.plist")
            sealed["status"] = "SEALED_DIAGNOSTIC_ORIGINALS_NOT_ACCEPTANCE"
        except BaseException as exc: sealed["firstFailure"] = c.error(exc)
    c.write(evidence / "retention-completion.json", sealed)
    print(json.dumps({"status": result["status"], "actualUIStatus": result["stages"].get("linked-ui", {}).get("status"),
                      "firstFailure": result.get("firstFailure"), "retention": sealed["status"]}))
    return 0 if result["status"] == "ORIGINAL_UI_DIAGNOSTIC_FINISHED_NOT_ACCEPTANCE" and sealed["status"] == "SEALED_DIAGNOSTIC_ORIGINALS_NOT_ACCEPTANCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
