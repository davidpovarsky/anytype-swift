#!/usr/bin/env python3
"""One owned public UIKit hit-test diagnostic; never a migration acceptance."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

sys.dont_write_bytecode = True
CONTROL = Path("/Users/m1/builds/e-combined-current-20261125/control-c5bcf1c")
CONTROL_SHA = "21998d3f410871cb5833e0de1a1b80ef06f17c2a688d43eead239b60ee373ddf"
RETAINER_SHA = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
LLDB_SHA = "1c1a1115f2b57fde93f7900fbd92c39d0feea3fa43ffad2aefe1c5e2cf7462af"
BASELINE = Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/attempt5")
BASELINE_EXECUTION_SHA = "c0bd2054cd57fae5ee0341b044125e871068a9118f364feffb94dfe51509256c"
BASELINE_BACKUP_SHA = "1e2a0cff07efad347e285df8aac8f20e9d566324d14b35265c84ebd6c2809978"
FIXTURE_SHA = "0a90efa3fb54b8313a633dbb1d1b4b95b4515c1d93c567b6078b84ac06e90887"
DEVICE = "5E77C761-78E5-4530-B44C-7561216652A6"
BINDING = {"sourceSHA": "ca7cb16f91c3d5fc4f7c8c178369abc9276e9a07",
           "runID": "1795610792364366", "runAttempt": "1",
           "nonce": "e8ef5f2272c14b848c43944a531a4606"}
DEADLINE = 1795618093.996194
INSTALLED = Path.home() / ("Library/Developer/CoreSimulator/Devices/" + DEVICE +
    "/data/Containers/Bundle/Application/DFD2F0F9-607A-412A-93BE-B3149126263E/Anytype.app")
BINARY_PINS = {"Anytype": "a0158826af42d9fb36d4faa2caca2bd01d1f01916aaeadce79e40d4581f5a2a2",
               "Anytype.debug.dylib": "dcb8ac76d496f524b6c0715b5b699242c5a877173e850ce4ab3a6cfec6d8014b"}

def load_core():
    path = CONTROL / "combined_heart_semantics_gateway_derivative.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != CONTROL_SHA:
        raise ValueError("Exact original lifecycle helper required")
    sys.path.insert(0, str(CONTROL))
    c = importlib.import_module("combined_heart_semantics_gateway_derivative")
    c.require(Path(c.__file__).resolve() == path, "Foreign original core")
    return c

def device(c, commands, label, expected):
    log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], label, 30, capacity=False)
    rows = [dict(row, runtime=runtime) for runtime, items in c.decode(c.raw(log))["devices"].items()
            for row in items if row.get("udid") == DEVICE]
    c.require(len(rows) == 1 and rows[0].get("state") == expected
              and rows[0].get("runtime") == c.RUNTIME
              and rows[0].get("deviceTypeIdentifier") == c.DEVICE
              and rows[0].get("name") == "E-Combined-Heart-" + BINDING["nonce"],
              "Delegated simulator identity or state differs")
    return rows[0]

def seal(c, commands):
    execution_path = BASELINE / "evidence/execution.json"
    backup_path = BASELINE / "private/owned-account-originals/retention.json"
    c.require(c.digest(execution_path) == BASELINE_EXECUTION_SHA
              and c.digest(backup_path) == BASELINE_BACKUP_SHA, "Exact C5 terminal and private seal required")
    execution = c.decode(c.raw(execution_path)); backup = c.decode(c.raw(backup_path))
    c.require(execution["status"] == "FAIL" and execution["binding"] == BINDING
              and execution["ownedSimulator"] == DEVICE and execution["deadlineExtended"] is False
              and execution["fixtureFactoryInvocations"] == 0
              and execution["stages"]["source-review"]["status"] == "FAIL"
              and execution["cleanup"]["status"] == "PASS"
              and execution["cleanup"]["ownedSimulatorRetainedForRecovery"] == DEVICE
              and execution["cleanup"]["ownedSimulatorDeleted"] is False,
              "Original actual C failure and lifecycle must remain unchanged")
    c.require(backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == BASELINE_EXECUTION_SHA and backup["device"] == DEVICE
              and backup["fixtureDeadlineChanged"] is False and backup["restoredFixtures"] == 0,
              "Current full private account backup required")
    retainer_path = CONTROL / "retain_owned_heart_account.py"
    c.require(c.digest(retainer_path) == RETAINER_SHA, "Exact safe retention helper required")
    retainer = importlib.import_module("retain_owned_heart_account")
    c.require(Path(retainer.__file__).resolve() == retainer_path, "Foreign retention helper")
    device(c, commands, "sealed-device", "Shutdown")
    command_dir = BASELINE / "commands/final-private-sandbox-container"
    command = c.decode(c.raw(command_dir / "result.json"))
    log = command_dir / "original.log"
    c.require(c.digest(log) == command["logSHA256"]
              == "cdf11e533f2d24827b6bd2b1360e6834a1027f707a9889fff13c35b09a183f03"
              and command["argv"] == ["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"]
              and command["status"] == "PASS_COMMAND" and command["exitCode"] == 0,
              "Original successful private container resolution required")
    app = Path(c.raw(log, 4096).decode().strip())
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    c.require(app.resolve() == app and app.is_dir()
              and app.parent == owner / "data/Containers/Data/Application"
              and re.fullmatch(r"[0-9A-F-]{36}", app.name), "Exact private app container required")
    roots = {"application-data": app, "shared-app-groups": owner / "data/Containers/Shared/AppGroup",
             "keychains": owner / "data/Library/Keychains", "device-preferences": owner / "data/Library/Preferences"}
    for label, path in roots.items():
        row = backup["scopes"][label]
        if row["status"] == "NOT_PRESENT":
            c.require(not path.exists() and not path.is_symlink(), "Absent scope appeared")
        else:
            manifest = BASELINE / "private/owned-account-originals" / (label + "-before.json")
            c.require(row["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES"
                      and c.digest(manifest) == row["manifestSHA256"]
                      and retainer.inventory(path) == c.decode(c.raw(manifest)),
                      "Private account changed since the C5 seal")
    fixture = app / "Library/Application Support" / c.FIXTURE
    c.require(c.digest(fixture) == FIXTURE_SHA, "Original native fixture changed")
    value = c.decode(c.raw(fixture, 65536))
    c.require(value["createdAt"] + 978307200 + 7200 == DEADLINE
              and time.time() + 300 < DEADLINE, "Unchanged fixture deadline required")
    device(c, commands, "sealed-device-after-inventory", "Shutdown")
    c.require(INSTALLED.resolve() == INSTALLED and INSTALLED.is_relative_to(owner), "Original installed app path required")
    for name, pin in BINARY_PINS.items():
        c.require(c.digest(INSTALLED / name) == pin, "Actual original ca7 installed binary differs")
    parent = app / "Library/Application Support/Pinkha/NativeSourceCaptures"
    captures = c.inventory(parent) if parent.exists() else None
    return app, retainer, execution, captures

def pid(c, commands):
    log, _ = commands.run(["xcrun", "simctl", "spawn", DEVICE, "launchctl", "list"],
                          "owned-process-resolution", 30, capacity=False)
    rows = []
    for line in c.raw(log, 2 * 1024**2).decode().splitlines():
        cells = line.split()
        if len(cells) == 3 and cells[0].isdigit() and cells[2].startswith("UIKitApplication:io.anytype.app["):
            rows.append(int(cells[0]))
    c.require(len(rows) == 1 and rows[0] > 1, "Exactly one original app process in the owned simulator required")
    log, _ = commands.run(["ps", "-p", str(rows[0]), "-o", "comm="], "owned-process-path", 15, capacity=False)
    c.require(c.raw(log, 4096).decode().strip() == str(INSTALLED / "Anytype"), "Resolved process is not the original installed app")
    return rows[0]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    c = load_core()
    c.require(sys.platform == "darwin" and sys.version_info >= (3, 12), "Actual Mac Python 3.12 required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent
              and not args.root.exists(), "Fresh canonical private diagnostic root required")
    args.root.mkdir(mode=0o700); os.umask(0o077)
    evidence = args.root / "evidence"; evidence.mkdir(mode=0o700)
    private = args.root / "private"; private.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    helper = Path(__file__).with_name("source_window_hit_test_lldb.py")
    result = {"protocol": "pinkha-owned-source-window-diagnostic-controller-v1",
              "status": "DIAGNOSTIC_FAILED_NOT_ACCEPTANCE", "binding": BINDING, "ownedSimulator": DEVICE,
              "controllerSHA256": c.digest(Path(__file__)), "helperSHA256": LLDB_SHA,
              "baselineExecutionSHA256": BASELINE_EXECUTION_SHA, "baselineBackupSHA256": BASELINE_BACKUP_SHA,
              "fixtureSHA256": FIXTURE_SHA, "originalDeadlineEpoch": DEADLINE,
              "diagnosticOnly": True, "builds": 0, "xctestInvocations": 0, "taps": 0,
              "fixtureFactoryInvocations": 0, "deadlineExtended": False, "sourceCaptureCalls": 0,
              "explicitNativeEngineCalls": 0, "targetExpressions": 0, "normalAppLaunches": 0,
              "startedAt": time.time()}
    claimed_boot = False; launched = False; retainer = None; prior = None; app = None
    try:
        c.require(c.digest(helper) == LLDB_SHA, "Frozen diagnostic helper required")
        app, retainer, prior, before_captures = seal(c, commands)
        result["sealedPrivateAccountUnchangedBeforeBoot"] = True
        claimed_boot = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-owned-device", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-owned-device", 180)
        device(c, commands, "booted-owned-device", "Booted")
        for kind, expected in (("data", app), ("app", INSTALLED)):
            log, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, kind],
                                  "recheck-installed-" + kind, 30, capacity=False)
            c.require(Path(c.raw(log, 4096).decode().strip()) == expected, "Booted original container differs")
        additions = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_SEMANTIC_MOUNTED_UI": "0",
                     "PINKHA_UI27_ROUTE_OBSERVATION": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            additions["PINKHA_SEMANTIC_MOUNTED_" + suffix] = BINDING[key]
        environment = ["SIMCTL_CHILD_" + key + "=" + value for key, value in sorted(additions.items())]
        launched = True; result["normalAppLaunches"] = 1
        commands.run(["env"] + environment + ["xcrun", "simctl", "launch", DEVICE, c.BUNDLE,
                     "-AppleLanguages", "(en)", "-AppleLocale", "en_US"], "normal-original-app-launch", 30)
        # A bounded startup interval precedes observation; it is not a readiness or acceptance gate.
        time.sleep(6)
        actual_pid = pid(c, commands)
        commands.run(["xcrun", "simctl", "io", DEVICE, "screenshot", str(private / "before-hit-test.png")],
                     "actual-window-screenshot", 30)
        output = evidence / "uikit-hit-test.json"
        config = private / "lldb-config.json"
        c.write(config, {"pid": actual_pid, "device": DEVICE, "executable": str(INSTALLED / "Anytype"),
                         "output": str(output)})
        result["targetExpressions"] = "SEE_ACTUAL_DIAGNOSTIC_RECEIPT"
        _, command = commands.run(["xcrun", "lldb", "--no-lldbinit", "--batch",
            "-o", "command script import " + str(helper),
            "-o", "script source_window_hit_test_lldb.run(lldb.debugger, " + repr(str(config)) + ")"],
            "owned-public-uikit-hit-test", 60, checked=False)
        result["diagnosticCommand"] = command
        c.require(output.is_file(), "Actual debugger diagnostic receipt missing")
        observation = c.decode(c.raw(output))
        result["targetExpressions"] = observation["targetExpressions"]
        result["diagnosticReceiptSHA256"] = c.digest(output)
        result["diagnosticStatus"] = observation["status"]
        result["detachedAndResumed"] = observation.get("detachedAndResumed") is True
        c.require(command["status"] == "PASS_COMMAND" and observation["status"] == "UIKIT_HIT_TEST_OBSERVED_NOT_ACCEPTANCE"
                  and result["detachedAndResumed"], "Owned UIKit diagnostic did not complete and detach successfully")
        result["status"] = "UIKIT_HIT_TEST_OBSERVED_NOT_ACCEPTANCE"
    except BaseException as exc:
        result["error"] = c.error(exc)
        c.write(private / "controller-error.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        cleanup = {"status": "PASS", "ownedSimulatorDeleted": False,
                   "ownedSimulatorRetainedForRecovery": DEVICE, "groups": [], "errors": []}
        if claimed_boot:
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(
                    commands, DEVICE, private / "final-sandbox-originals", application_invoked=launched)
                c.require(prior is not None and result["finalPrivateSandbox"]["files"]
                          == prior["finalPrivateSandbox"]["files"], "Original native E witnesses changed")
                parent = app / "Library/Application Support/Pinkha/NativeSourceCaptures"
                after = c.inventory(parent) if parent.exists() else None
                c.require(after == before_captures, "Diagnostic unexpectedly changed source captures")
                result["originalNativeWitnessesUnchanged"] = True
                result["sourceCaptureDirectoryUnchanged"] = True
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
            if launched:
                try:
                    _, terminated = commands.run(["xcrun", "simctl", "terminate", DEVICE, c.BUNDLE],
                                                  "terminate-only-owned-app", 30, checked=False, capacity=False)
                    result["ownedAppTerminateExit"] = terminated["exitCode"]
                except BaseException as exc:
                    cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
            try:
                _, stopped = commands.run(["xcrun", "simctl", "shutdown", DEVICE],
                                          "cleanup-shutdown", 60, checked=False, capacity=False)
                c.require(stopped["exitCode"] == 0, "Owned simulator shutdown failed")
                device(c, commands, "final-owned-shutdown", "Shutdown")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True})
            else:
                present = c.Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present:
                    cleanup["status"] = "FAIL"; cleanup["errors"].append({"ownedGroupStillPresent": group})
        try:
            c.require(c.digest(BASELINE / "evidence/execution.json") == BASELINE_EXECUTION_SHA
                      and c.digest(BASELINE / "private/owned-account-originals/retention.json") == BASELINE_BACKUP_SHA,
                      "Original actual failure or backup changed")
            for name, pin in BINARY_PINS.items():
                c.require(c.digest(INSTALLED / name) == pin, "Installed original app changed during observation")
        except BaseException as exc:
            cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        if cleanup["status"] != "PASS": result["status"] = "DIAGNOSTIC_CLEANUP_FAILED_NOT_ACCEPTANCE"
        result["cleanup"] = cleanup; result["finishedAt"] = time.time()
        c.write(evidence / "execution.json", result)
        final_status = result["status"]
        if claimed_boot and cleanup["status"] == "PASS" and retainer is not None:
            try:
                backup = retainer.retain(args.root, c.digest(evidence / "execution.json"))
                c.write(evidence / "account-retention.json", backup)
            except BaseException as exc:
                c.write(evidence / "account-retention-failure.json", c.error(exc))
                final_status = "DIAGNOSTIC_ACCOUNT_RETENTION_FAILED_NOT_ACCEPTANCE"
        c.write(evidence / "final-outcome.json", {"status": final_status, "executionSHA256": c.digest(evidence / "execution.json"),
                  "priorActualCFailuresPreserved": True, "fixtureDeadlineExtended": False})
    print(json.dumps({"status": final_status, "executionSHA256": c.digest(evidence / "execution.json"),
                      "root": str(args.root), "error": result.get("error")}, sort_keys=True))
    return 0 if final_status == "UIKIT_HIT_TEST_OBSERVED_NOT_ACCEPTANCE" else 1

if __name__ == "__main__":
    raise SystemExit(main())
