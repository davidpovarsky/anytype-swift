"""Observe the exact native reply rejected by the original Page154 validator.

Explicit local diagnostic: original 96fadb App/UI Products, fresh owned fixture,
zero builds and zero acceptance credit. One LLDB observation reads the native
JSON reply at a byte-qualified existing Foundation.Data function boundary.
Original test actions, assertions, limits and all product bytes are preserved.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

ORIGINAL = Path("/Users/m1/builds/_retained-anytype/45498082340-1/build/current-page154-45498082340-1")
ORIGINAL_SOURCE = "96fadb1945a33e8c7bfa6153cae1cd6124604fdd"
APP_RECEIPT_SHA = "94a8f41db17cf1f9cb0a40ff3abcda5bad30de4eaeb581157a6bbc6885984ecc"
UI_RECEIPT_SHA = "567b1fbce20df8e2c3bda998176609b817981d7698a811ef35240694f2e01f73"
PREP_SHA = "345f94dbb49d773a9a5767a0c2038c23a69f488a6d9b8f4935f6ca80ced6270a"
UI_SHA = "2b05faf3daa9e36d0e7f1169ac8bd4291730cae26f2fbcd2e7b44143796a1141"
PREP = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
UI = "PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
FIXTURE = "pinkha-semantic-page154-mounted-fixture.json"
BUNDLE = "io.anytype.app"
HERE = Path(__file__).resolve().parent
STAGE = HERE
DEVELOPER = "/Applications/Xcode.app/Contents/Developer"
GROUPS = set()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def inventory(root):
    require(root.is_absolute() and root.resolve() == root and root.is_dir(), "real_original_products_required")
    values, total, deadline = {}, 0, time.monotonic() + 180
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            p = Path(parent) / name
            info = p.lstat()
            require(time.monotonic() < deadline and len(values) < 100000, "inventory_limit")
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISDIR(info.st_mode):
                row = {"kind": "directory", "mode": mode}
            elif stat.S_ISLNK(info.st_mode):
                target = os.readlink(p)
                require(not Path(target).is_absolute() and p.resolve().is_relative_to(root), "external_product_link")
                row = {"kind": "symlink", "mode": mode, "target": target}
            elif stat.S_ISREG(info.st_mode):
                total += info.st_size
                require(total <= 16 * 1024**3, "inventory_size")
                row = {"kind": "file", "mode": mode, "bytes": info.st_size, "sha256": digest(p)}
            else:
                raise RuntimeError("special_product")
            values[p.relative_to(root).as_posix()] = row
    require(time.monotonic() < deadline, "inventory_timeout")
    return values


def stop(process):
    if process is None:
        return
    if process.poll() is None:
        require(os.getpgid(process.pid) == process.pid and process.pid in GROUPS, "unowned_process_group")
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=8)
    GROUPS.discard(process.pid)


def run(argv, timeout=30, check=True):
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    GROUPS.add(process.pid)
    try:
        out, err = process.communicate(timeout=timeout)
    finally:
        stop(process)
    result = subprocess.CompletedProcess(argv, process.returncode, out, err)
    if check:
        require(result.returncode == 0, "command_failed:" + Path(argv[0]).name + ":" + str(result.returncode))
    return result


def original_products():
    roots = {"app": ORIGINAL / "work/app-derived/Build/Products",
             "ui": ORIGINAL / "work/ui-derived/Build/Products"}
    receipts = {}
    expected = {}
    hashes = {"app": APP_RECEIPT_SHA, "ui": UI_RECEIPT_SHA}
    extra = {
        "app": ("Current-Page154-preparation.xctestrun", {"kind": "file", "mode": 384, "bytes": 6575,
                "sha256": "5846f4253317679cdbdb039ba534c389e8bc5d84ba396583dfb6029c0ffd1993"}),
        "ui": ("Current-Page154-ui.xctestrun", {"kind": "file", "mode": 384, "bytes": 6934,
               "sha256": "f5906d6e2e402abef66a78809f97798088cf70ac6669a28e46e8e1b6e40dc75b"})
    }
    for key, root in roots.items():
        receipt = ORIGINAL / ("evidence/" + key + "-build/original-products.json")
        require(digest(receipt) == hashes[key], "original_product_receipt_changed:" + key)
        value = json.loads(receipt.read_bytes())
        require(value["context"] == {"profile": "current-page154-mounted",
                "repository": "davidpovarsky/anytype-swift", "runAttempt": "1",
                "runID": "45498082340", "sourceCommit": ORIGINAL_SOURCE},
                "exact_original_product_producer_required")
        expected[key] = dict(value["files"])
        require(len(expected[key]) == (5006 if key == "app" else 29), "original_inventory_scope_changed")
        name, row = extra[key]
        require(name not in expected[key], "original_frozen_inventory_already_contains_scoped_descriptor")
        # These are the two exact descriptors created by the original failed run.
        # They remain unchanged and are never used as the new diagnostic inputs.
        expected[key][name] = row
        require(inventory(root) == expected[key], "original_products_changed:" + key)
    app_path = roots["app"] / "Debug-Anytype-iphonesimulator/Anytype.app"
    runner = roots["ui"] / "Debug-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
    for bundle in (app_path, runner):
        run(["codesign", "--verify", "--deep", "--strict", str(bundle)], timeout=60)
    descriptors = {
        "app": roots["app"] / "Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun",
        "ui": roots["ui"] / "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"
    }
    require(digest(descriptors["app"]) == PREP_SHA and digest(descriptors["ui"]) == UI_SHA,
            "original_descriptor_changed")
    require(plistlib.loads((app_path / "Info.plist").read_bytes())["CFBundleIdentifier"] == BUNDLE,
            "original_app_bundle_changed")
    return roots, expected, descriptors, app_path


def relocated(value, root):
    if isinstance(value, dict):
        return {key: relocated(child, root) for key, child in value.items()}
    if isinstance(value, list):
        return [relocated(child, root) for child in value]
    if isinstance(value, str):
        return value.replace("__TESTROOT__", str(root))
    return value


def descriptor(original, destination, root, selector, environment, app_path=None):
    baseline = plistlib.loads(original.read_bytes())
    copied = relocated(copy.deepcopy(baseline), root)
    target_name, suite, method = selector.split("/")
    if selector == PREP:
        configurations = copied["TestConfigurations"]
        require(len(configurations) == 1, "one_preparation_configuration_required")
        targets = [t for t in configurations[0]["TestTargets"] if t.get("BlueprintName") == target_name]
        require(len(targets) == 1, "one_preparation_target_required")
        configurations[0]["TestTargets"] = targets
        target = targets[0]
    else:
        require(set(copied) == {"__xctestrun_metadata__", target_name}, "one_original_ui_target_required")
        target = copied[target_name]
        require(target.get("IsUITestBundle") is True, "original_ui_target_required")
    before = copy.deepcopy(target)
    previous = target.get("EnvironmentVariables", {})
    require(all(not key.startswith(("PINKHA_", "TEST_RUNNER_PINKHA_")) for key in previous),
            "stale_original_binding")
    target["EnvironmentVariables"] = previous | environment
    target["OnlyTestIdentifiers"] = [suite + "/" + method]
    if selector == UI:
        require(app_path is not None and app_path.is_dir(), "actual_app_required")
        target["UITargetAppPath"] = str(app_path)
    restored = copy.deepcopy(target)
    for key in ("EnvironmentVariables", "OnlyTestIdentifiers", "UITargetAppPath", "UITargetAppEnvironmentVariables"):
        if key in before:
            restored[key] = before[key]
        else:
            restored.pop(key, None)
    require(restored == before, "unreviewed_descriptor_change")
    with destination.open("xb") as stream:
        plistlib.dump(copied, stream, sort_keys=False)
    return {"originalSHA256": digest(original), "copySHA256": digest(destination),
            "selector": selector, "testRootRelocatedTo": str(root),
            "changedTargetKeys": sorted(k for k in target if target.get(k) != before.get(k)),
            "originalTestActionsUnchanged": True}


def methods(value):
    result = {}
    if isinstance(value, dict):
        if value.get("nodeType") == "Test Case":
            require(value.get("nodeIdentifier") not in result, "duplicate_method")
            result[value["nodeIdentifier"]] = value.get("result")
        children = value.values()
    elif isinstance(value, list):
        children = value
    else:
        children = []
    for child in children:
        found = methods(child)
        require(not result.keys() & found.keys(), "duplicate_method")
        result.update(found)
    return result


def summarize(work, stage, bundle, selector, udid):
    summary = json.loads(run(["xcrun", "xcresulttool", "get", "test-results", "summary",
                              "--path", str(bundle)], timeout=45).stdout)
    tests = json.loads(run(["xcrun", "xcresulttool", "get", "test-results", "tests",
                            "--path", str(bundle)], timeout=45).stdout)
    write(work / (stage + "-summary.json"), summary)
    write(work / (stage + "-tests.json"), tests)
    actual = {key.removesuffix("()"): value for key, value in methods(tests).items()}
    wanted = selector.split("/", 1)[1]
    counts = {k: summary.get(k) for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(counts["totalTestCount"] == 1 and counts["skippedTests"] == 0 and set(actual) == {wanted},
            "exact_one_actual_method_required")
    devices = [row["device"] for row in summary.get("devicesAndConfigurations", [])]
    require(devices and all(row.get("deviceId", "").lower() == udid.lower()
                           and row.get("architecture") == "arm64" and row.get("osVersion") == "27.0"
                           and row.get("osBuildNumber") == "24A434" for row in devices),
            "actual_result_runtime_changed")
    return {"counts": counts, "methods": actual, "devices": devices}


def owned_application(udid):
    output = run(["xcrun", "simctl", "spawn", udid, "launchctl", "list"], timeout=15, check=False)
    entries = [line.split() for line in output.stdout.splitlines() if "UIKitApplication:io.anytype.app[" in line]
    entries = [row for row in entries if row and row[0].isdigit()]
    if len(entries) != 1:
        return None
    pid = entries[0][0]
    argv = run(["ps", "-p", pid, "-o", "command="], check=False).stdout.strip()
    if udid.lower() not in argv.lower() or "/Anytype.app/Anytype" not in argv:
        return None
    return {"pid": int(pid), "ownedAppPathVerified": True}


def start_observer(work, app, udid, app_path):
    config = {"pid": app["pid"], "udid": udid, "work": str(work), "appPath": app_path}
    config_path = work / "reply-observer-config.json"
    write(config_path, config)
    helper = STAGE / "page96_validation_lldb.py"
    argv = ["xcrun", "lldb", "-b", "-o", "script import sys; sys.dont_write_bytecode = True",
            "-o", "command script import " + str(helper),
            "-o", "script page96_validation_lldb.main(lldb.debugger, " + repr(str(config_path)) + ")",
            "-o", "quit"]
    write(work / "reply-observer-command.json", argv)
    output = (work / "reply-observer-private.log").open("wb")
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output,
                               stderr=subprocess.STDOUT, start_new_session=True)
    GROUPS.add(process.pid)
    write(work / "reply-observer-started.json", {"pid": process.pid, "group": process.pid, "startedAt": time.time(), "ownedAppPID": app["pid"], "ownedSimulator": udid})
    return process, output


def stop_owned_diagnose(udid, work):
    def observed():
        rows = []
        for line in run(["ps", "-axo", "pid,pgid,command"]).stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) != 3 or not fields[0].isdigit():
                continue
            command = fields[2]
            if (command.split()[0].endswith("/simctl") and " diagnose " in command
                    and udid.lower() in command.lower() and str(work) in command):
                rows.append({"pid": int(fields[0]), "pgid": int(fields[1]), "command": command})
        return rows
    before = observed()
    for row in before:
        require(row in observed(), "owned_diagnose_identity_changed")
        if row["pid"] == row["pgid"]:
            os.killpg(row["pgid"], signal.SIGTERM)
        else:
            os.kill(row["pid"], signal.SIGTERM)
    deadline = time.monotonic() + 8
    remaining = observed()
    while remaining and time.monotonic() < deadline:
        time.sleep(0.2)
        remaining = observed()
    return {"identified": before, "signal": "SIGTERM" if before else None, "remaining": remaining}


def selected_test(work, stage, desc, selector, udid, seconds, receipt):
    bundle = work / (stage + ".xcresult")
    argv = ["xcodebuild", "test-without-building", "-xctestrun", str(desc),
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
            "-maximum-concurrent-test-simulator-destinations", "1", "-collect-test-diagnostics", "never",
            "-only-testing:" + selector,
            "-resultBundlePath", str(bundle)]
    write(work / (stage + "-command.json"), argv)
    failure_seen = None
    observer = observer_output = None
    observer_started = None
    with (work / (stage + ".log")).open("wb") as output:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        GROUPS.add(process.pid)
        receipt["activeGroup"] = process.pid
        deadline = time.monotonic() + seconds
        try:
            while process.poll() is None:
                require(time.monotonic() < deadline, "bounded_diagnostic_command_timeout:" + stage)
                if stage == "ui" and observer is None:
                    observed = owned_application(udid)
                    if observed is not None and observed["pid"] != receipt.get("preparationProcessID"):
                        receipt["observedApplication"] = observed
                        observer, observer_output = start_observer(work, observed, udid, receipt["originalAppPath"])
                        receipt["observerGroup"] = observer.pid
                        observer_started = time.monotonic()
                if observer is not None and observer.poll() is None:
                    require(time.monotonic() - observer_started < 100, "bounded_reply_observer_timeout")
                text = (work / (stage + ".log")).read_text(errors="replace")
                if "Test Suite 'Selected tests' failed" in text:
                    failure_seen = failure_seen or time.monotonic()
                    if time.monotonic() - failure_seen >= 90:
                        require(process.pid in GROUPS and os.getpgid(process.pid) == process.pid, "unowned_failure_cleanup")
                        os.killpg(process.pid, signal.SIGINT)
                        receipt["operatorInterruptionAfterCompletedFailure"] = {
                            "stage": stage, "group": process.pid, "graceSeconds": 90, "signal": "SIGINT"}
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            stop(process)
                        break
                time.sleep(1)
        finally:
            stop(observer)
            if observer_output:
                observer_output.close()
            stop(process)
            receipt.pop("activeGroup", None)
    if stage == "ui":
        observed = work / "reply-observation.json"
        receipt["replyObservation"] = json.loads(observed.read_bytes()) if observed.exists() else {"status": "NOT_CAPTURED"}
    result = summarize(work, stage, bundle, selector, udid)
    result["commandExit"] = process.returncode
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(sys.platform == "darwin" and os.uname().machine == "arm64" and sys.version_info[:2] == (3, 12),
            "qualified_mac_python_required")
    require(not any(key.startswith("GITHUB_") for key in os.environ), "explicit_local_context_required")
    require(os.environ.get("DEVELOPER_DIR") == DEVELOPER, "qualified_xcode_path_required")
    os.umask(0o077)
    manifest = json.loads((STAGE / "source-manifest.json").read_bytes())
    require(re.fullmatch("[0-9a-f]{40}", manifest["controllerCommit"]), "controller_commit_required")
    require(all(digest(STAGE / name) == row["sha256"] for name, row in manifest["inputs"].items()),
            "staged_controller_changed")
    require(run(["xcodebuild", "-version"]).stdout.strip() == "Xcode 27.0\nBuild version 27A266a",
            "qualified_xcode_changed")
    roots, originals, descriptors, app_path = original_products()
    work = Path(tempfile.mkdtemp(prefix="page96-validation-", dir="/Users/m1/builds/_diagnostics"))
    binding = {"sourceSHA": manifest["controllerCommit"], "runID": str(time.time_ns()),
               "runAttempt": "1", "nonce": uuid.uuid4().hex}
    receipt = {"mode": "LOCAL_DIAGNOSTIC", "controllerCommit": manifest["controllerCommit"],
               "controllerInputs": manifest["inputs"], "binding": binding, "originalAppUIBuildRun": "45498082340",
               "originalBuildControllerSource": ORIGINAL_SOURCE, "originalCurrentUIFailureRun": "45498082340",
               "originalFailuresPreserved": True, "appBuilds": 0, "uiRunnerBuilds": 0, "nativeBuilds": 0,
               "acceptanceCredit": 0, "verboseDiagnosticsPolicy": "never",
               "keepAlwaysAttachmentsUnchanged": True,
               "work": str(work), "originalAppPath": str(app_path), "stages": {}, "status": "QUALIFIED_NOT_EXECUTED"}
    write(work / "original-inventories.json", originals)
    udid = None
    if not args.execute:
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        write(work / "result.json", receipt)
        print(json.dumps({"status": receipt["status"], "work": str(work), "controllerCommit": manifest["controllerCommit"], "appBuilds": 0, "uiRunnerBuilds": 0}))
        return 0
    with (STAGE / "run-once.json").open("x") as lock:
        json.dump({"controllerCommit": manifest["controllerCommit"], "binding": binding, "work": str(work), "mode": "LOCAL_DIAGNOSTIC"}, lock, indent=2)
    try:
        devices = json.loads(run(["xcrun", "simctl", "list", "--json"]).stdout)
        runtimes = [x for x in devices["runtimes"] if x.get("version") == "27.0"
                    and x.get("buildversion") == "24A434" and x.get("isAvailable") is True]
        types = [x for x in devices["devicetypes"] if x["name"] == "iPad Pro 13-inch (M5) (16GB)"]
        require(len(runtimes) == len(types) == 1, "fixed_original_device_runtime_required")
        name = "Page event observation " + binding["nonce"]
        udid = run(["xcrun", "simctl", "create", name, types[0]["identifier"], runtimes[0]["identifier"]]).stdout.strip()
        require(re.fullmatch("[A-Fa-f0-9-]{36}", udid), "owned_device_identity_required")
        receipt["ownedSimulator"] = {"name": name, "udid": udid, "runtime": runtimes[0]["identifier"],
                                     "build": "24A434", "deviceType": types[0]["identifier"]}
        write(work / "ownership.json", receipt)
        run(["xcrun", "simctl", "boot", udid], timeout=45)
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], timeout=150)
        environment = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            environment["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        prep = work / "prepare.xctestrun"
        receipt["preparationDescriptor"] = descriptor(descriptors["app"], prep, roots["app"], PREP,
                                                      environment | {"PINKHA_SEMANTIC_MOUNTED_PREPARE": "1"})
        receipt["stages"]["preparation"] = selected_test(work, "preparation", prep, PREP, udid, 240, receipt)
        require(receipt["stages"]["preparation"]["counts"]["passedTests"] == 1
                and receipt["stages"]["preparation"]["commandExit"] == 0, "actual_preparation_required")
        container = Path(run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"]).stdout.strip())
        require(container.resolve() == container and udid.lower() in str(container).lower(), "owned_container_required")
        raw = (container / "Library/Application Support" / FIXTURE).read_bytes()
        require(len(raw) <= 65536, "fixture_bound")
        fixture = json.loads(raw)
        require(all(fixture[key] == value for key, value in binding.items()), "fresh_fixture_binding_changed")
        (work / "private-fixture.json").write_bytes(raw)
        receipt["preparationProcessID"] = fixture["preparationProcessID"]
        ui = work / "ui.xctestrun"
        receipt["uiDescriptor"] = descriptor(descriptors["ui"], ui, roots["ui"], UI,
            environment | {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": raw.decode()},
            app_path=app_path)
        receipt["stages"]["ui"] = selected_test(work, "ui", ui, UI, udid, 330, receipt)
        observation = receipt.get("replyObservation", {})
        require(observation.get("status") == "CAPTURED_ORIGINAL_REPLY"
                and observation.get("hits") == 1 and observation.get("detachSucceeded") is True
                and observation.get("validationThrow"),
                "actual_original_reply_observation_required")
        captured = json.loads((work / "private-original-capture-reply.json").read_bytes())
        require(all(captured["receipt"][key] == fixture[key] for key in ("spaceID", "objectID", "blockID")),
                "captured_reply_fixture_owner_changed")
        capture_file = container / "Library/Application Support/pinkha-semantic-page154-mounted-capture.json"
        require(capture_file.is_file(), "actual_app_capture_receipt_required")
        capture_raw = capture_file.read_bytes()
        captured_receipt = json.loads(capture_raw)
        require(all(captured_receipt[key] == value for key, value in binding.items()),
                "actual_capture_receipt_binding_changed")
        (work / "private-app-capture-receipt.json").write_bytes(capture_raw)
        receipt["appCaptureReceiptSHA256"] = hashlib.sha256(capture_raw).hexdigest()
        receipt["actualAppCapturePhase"] = captured_receipt.get("phase")
        receipt["status"] = "DIAGNOSTIC_COMPLETED"
    except BaseException as error:
        receipt["status"] = "DIAGNOSTIC_FAILED"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)[:1000]}
    finally:
        if udid:
            try:
                receipt["ownedDetachedDiagnostics"] = stop_owned_diagnose(udid, work)
                require(not receipt["ownedDetachedDiagnostics"]["remaining"], "owned_diagnose_cleanup_incomplete")
            except BaseException as error:
                receipt["status"] = "DIAGNOSTIC_FAILED"
                receipt["ownedDiagnoseCleanupError"] = type(error).__name__
            try:
                shot = run(["xcrun", "simctl", "io", udid, "screenshot",
                            str(work / "post-outcome-private.png")], check=False)
                receipt["postOutcomeScreenshotExit"] = shot.returncode
            except BaseException as error:
                receipt["postOutcomeScreenshotError"] = type(error).__name__
            for action in ("shutdown", "delete"):
                try:
                    receipt[action + "Exit"] = run(["xcrun", "simctl", action, udid], timeout=60, check=False).returncode
                except BaseException as error:
                    receipt[action + "Error"] = type(error).__name__
        try:
            receipt["originalInputsUnchanged"] = (all(inventory(root) == originals[key] for key, root in roots.items())
                and digest(descriptors["app"]) == PREP_SHA and digest(descriptors["ui"]) == UI_SHA)
            receipt["controllerInputsUnchanged"] = all(digest(STAGE / name) == row["sha256"]
                                                       for name, row in manifest["inputs"].items())
            if not receipt["originalInputsUnchanged"] or not receipt["controllerInputsUnchanged"]:
                receipt["status"] = "DIAGNOSTIC_FAILED"
        except BaseException as error:
            receipt["status"], receipt["integrityError"] = "DIAGNOSTIC_FAILED", type(error).__name__
        if udid:
            try:
                devices = json.loads(run(["xcrun", "simctl", "list", "devices", "--json"]).stdout)["devices"]
                receipt["ownedDeviceAbsent"] = all(row.get("udid", "").lower() != udid.lower()
                    for rows in devices.values() for row in rows)
            except BaseException as error:
                receipt["ownedDeviceAbsent"] = False
        receipt["remainingOwnedGroups"] = sorted(GROUPS)
        if GROUPS or (udid and (receipt.get("deleteExit") != 0 or receipt.get("ownedDeviceAbsent") is not True)):
            receipt["status"] = "DIAGNOSTIC_FAILED"
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        write(work / "result.json", receipt)
        print(json.dumps({"status": receipt["status"], "work": str(work), "failure": receipt.get("failure"), "originalInputsUnchanged": receipt.get("originalInputsUnchanged"), "ownedDeviceAbsent": receipt.get("ownedDeviceAbsent"), "remainingOwnedGroups": receipt.get("remainingOwnedGroups")}))
    return 0 if receipt["status"] == "DIAGNOSTIC_COMPLETED" else 1


if __name__ == "__main__":
    def interrupted(signum, _):
        raise RuntimeError("owned_diagnostic_interrupted:" + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    raise SystemExit(main())
