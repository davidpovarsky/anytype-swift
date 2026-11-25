"""Execute only the unresolved native Hanlin UI journey on the dedicated Mac.

This is an explicitly local Apple run. Original GitHub failures and component
results remain separate. No CI identity, App build, SDK component execution, or
test assertion is substituted by this continuation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
SOURCE = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
GUARD_SHA = "4b762ba9a32c01c2f4990a7cba0e4d92e21e768e0167e5145223414677d775e4"
VERIFIER_SHA = "8552b94f2034d4a1ddfcd363ca02526ff7c843030d65790ceb048efcde2056e4"
PREP_METHOD = "HanlinNativeAcceptancePreparationTests/prepareRealHostFixture"
UI_METHOD = "HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation"
RECEIPTS = {
    "original-native/sdk06-early-products/manifest.json": "331ad15a50b7c0d815fde3b2597b63d24f4de48b206f005aecbf0316f5fe5707",
    "sdk06-ui/sdk06-early-products/manifest.json": "fcdfadc7f6ff3d001dbafc98bd5b46ab2206bdf7872e299f37a6d21a75ff302d",
    "first-ui-only-build-result.json": "f8fade357429951a1321c7fedd233835e0e7f0f15714510548a6e677065ce7bf",
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def module(name, path, expected):
    require(path.is_file() and path.resolve() == path and digest(path) == expected,
            "qualified_helper_changed:" + name)
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


base = module("qualified_original_hanlin_products", HERE / "owned_hanlin_launch_guard.py", GUARD_SHA)
native = module("qualified_hanlin_native_receipt", HERE.parent / "hanlin_acceptance_evidence.py", VERIFIER_SHA)


def tree(root):
    require(root.is_dir() and root.resolve() == root, "real_original_bundle_required")
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        mode = stat.S_IMODE(info.st_mode)
        key = "" if path == root else path.relative_to(root).as_posix()
        if stat.S_ISREG(info.st_mode):
            value = {"kind": "file", "mode": mode, "bytes": info.st_size, "sha256": digest(path)}
        elif stat.S_ISDIR(info.st_mode):
            value = {"kind": "directory", "mode": mode}
        else:
            raise RuntimeError("unexpected_original_bundle_entry:" + key)
        result[key] = value
    return result


def original_products():
    evidence = base.RETAINED / "sdk06-original-native-evidence-45423982997-1"
    receipts = {}
    for name, expected in RECEIPTS.items():
        path = evidence / name
        require(digest(path) == expected, "original_receipt_changed:" + name)
        receipts[name] = json.loads(path.read_bytes())
    app = receipts["original-native/sdk06-early-products/manifest.json"]
    ui = receipts["sdk06-ui/sdk06-early-products/manifest.json"]
    built = receipts["first-ui-only-build-result.json"]
    require(app["run_id"] == "45139431216" and app["run_attempt"] == "1"
            and app["source_sha"] == SOURCE and len(app["products"]) == 5011,
            "original_application_producer_changed")
    require(ui["run_id"] == "45423982997" and ui["run_attempt"] == "1"
            and ui["source_sha"] == SOURCE and len(ui["products"]) == 30,
            "original_ui_producer_changed")
    require(built["status"] == "FIRST_UI_ONLY_BUILD_SUCCEEDED"
            and built["ui_source_sha"] == SOURCE and built["native_products_unchanged"] is True
            and built["native_builds_this_run"] == 0 and built["ui_builds_this_run"] == 1,
            "original_ui_build_not_qualified")
    expected, observed = {}, {}
    roots = {
        "application": (base.APP, app, "Build/Products/Debug-Anytype-iphonesimulator/Anytype.app"),
        "uiRunner": (base.UI.parent / "Debug-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app",
                     ui, "Build/Products/Debug-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"),
    }
    for name, (root, manifest, prefix) in roots.items():
        expected[name] = {key[len(prefix):].lstrip("/"): value for key, value in manifest["products"].items()
                          if key == prefix or key.startswith(prefix + "/")}
        require(expected[name], "original_bundle_inventory_missing:" + name)
        observed[name] = tree(root)
        require(observed[name] == expected[name], "original_bundle_changed:" + name)
        base.run(["codesign", "--verify", "--deep", "--strict", str(root)], timeout=60)
    descriptors = {str(base.PREP): "decef96cbccc57a42d9debbccb91da4e9ad8b3e9dbc89afbf439a3151fbc2515",
                   str(base.UI): "550a7279b31e0c9a50406b644b650516172e46c17e2bca95bf8b7a54cf9a94b1"}
    require(all(digest(path) == sha for path, sha in descriptors.items()), "original_descriptor_changed")
    return roots, observed, descriptors


def method_results(value):
    result = {}
    if isinstance(value, dict):
        if value.get("nodeType") == "Test Case":
            require(value.get("nodeIdentifier"), "unnamed_actual_method")
            result[value["nodeIdentifier"]] = value.get("result")
        children = value.values()
    elif isinstance(value, list):
        children = value
    else:
        children = []
    for child in children:
        found = method_results(child)
        require(not result.keys() & found.keys(), "duplicate_actual_method")
        result.update(found)
    return result


def qualify_result(bundle, method, udid):
    summary = json.loads(base.run(["xcrun", "xcresulttool", "get", "test-results", "summary",
                                   "--path", str(bundle)], timeout=45).stdout)
    tests = json.loads(base.run(["xcrun", "xcresulttool", "get", "test-results", "tests",
                                 "--path", str(bundle)], timeout=45).stdout)
    bundle.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    bundle.with_suffix(".tests.json").write_text(json.dumps(tests, indent=2) + "\n")
    actual = {name.removesuffix("()"): status for name, status in method_results(tests).items()}
    counts = {key: summary.get(key) for key in ("passedTests", "failedTests", "skippedTests", "totalTestCount")}
    devices = [row["device"] for row in summary.get("devicesAndConfigurations", [])]
    require(counts == {"passedTests": 1, "failedTests": 0, "skippedTests": 0, "totalTestCount": 1}
            and actual == {method: "Passed"}, "actual_named_method_failed_or_not_executed:" + method)
    require(devices and all(row.get("deviceId", "").lower() == udid.lower()
                           and row.get("architecture") == "arm64" and row.get("osVersion") == "27.0"
                           for row in devices), "actual_result_device_changed")
    return {"counts": counts, "methods": actual, "devices": devices}


def selected_test(work, descriptor, target, selector, method, udid, seconds):
    bundle = work / (target + ".xcresult")
    command = ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
               "-destination", "platform=iOS Simulator,id=" + udid,
               "-parallel-testing-enabled", "NO", "-maximum-concurrent-test-simulator-destinations", "1",
               "-only-testing:" + target + "/" + selector, "-resultBundlePath", str(bundle)]
    (work / (target + ".command.json")).write_text(json.dumps(command, indent=2) + "\n")
    with (work / (target + ".log")).open("wb") as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=seconds)
        finally:
            base.owned_process_stop(process)
    result = qualify_result(bundle, method, udid)
    require(code == 0, "xcodebuild_test_command_failed:" + target)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(sys.platform == "darwin" and os.uname().machine == "arm64", "dedicated_arm64_mac_required")
    require(os.environ.get("GITHUB_ACTIONS") != "true", "explicit_local_execution_only")
    os.umask(0o077)
    stage = HERE.parents[2]
    source = json.loads((stage / "source-manifest.json").read_bytes())
    require(re.fullmatch("[0-9a-f]{40}", source["controllerCommit"]), "controller_commit_required")
    for name, row in source["inputs"].items():
        path = stage / name
        require(path.resolve() == path and digest(path) == row["sha256"], "staged_controller_changed:" + name)
    xcode = base.run(["xcodebuild", "-version"]).stdout.strip()
    require(xcode == "Xcode 27.0\nBuild version 27A266a", "qualified_xcode_changed")
    roots, inventories, descriptors = original_products()
    run_id = str(time.time_ns())
    work = Path(tempfile.mkdtemp(prefix="sdk-ui-continuation-", dir="/Users/m1/builds/_diagnostics"))
    receipt = {"mode": "LOCAL_APPLE_TEST_RUN", "localRunID": run_id,
               "controllerCommit": source["controllerCommit"], "controllerInputs": source["inputs"],
               "originalAppSource": SOURCE, "originalUIRun": "45423982997", "originalWorkflowConclusion": "failure",
               "appBuilds": 0, "uiRunnerBuilds": 0, "nativeBuilds": 0,
               "sdk23Replayed": False, "ack7Replayed": False,
               "sdk06CompositeAccepted": False, "productReleaseAccepted": False,
               "originalProductEntries": {name: len(value) for name, value in inventories.items()},
               "originalReceipts": RECEIPTS, "work": str(work), "stages": {}, "status": "QUALIFIED_NOT_EXECUTED"}
    (work / "original-inventories.json").write_text(json.dumps(inventories, sort_keys=True) + "\n")
    if not args.execute:
        receipt["originalInputsUnchanged"] = True
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        (work / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
        return 0
    udid = None
    try:
        inventory = json.loads(base.run(["xcrun", "simctl", "list", "--json"]).stdout)
        types = [row for row in inventory["devicetypes"] if row["name"] == "iPad Pro 13-inch (M5) (16GB)"]
        runtimes = [row for row in inventory["runtimes"] if row.get("version") == "27.0"
                    and row.get("buildversion") == "24A434" and row.get("isAvailable") is True]
        require(len(types) == len(runtimes) == 1, "exact_qualified_simulator_runtime_required")
        name = "Anytype Hanlin retained UI " + str(uuid.uuid4())
        udid = base.run(["xcrun", "simctl", "create", name, types[0]["identifier"], runtimes[0]["identifier"]]).stdout.strip()
        require(re.fullmatch("[A-Fa-f0-9-]{36}", udid), "owned_simulator_identity_invalid")
        receipt["ownedSimulator"] = {"name": name, "udid": udid, "runtime": runtimes[0]["identifier"]}
        (work / "ownership.json").write_text(json.dumps(receipt, indent=2) + "\n")
        base.run(["xcrun", "simctl", "boot", udid], timeout=45)
        base.run(["xcrun", "simctl", "bootstatus", udid, "-b"], timeout=150)
        environment = {"PINKHA_HANLIN_NATIVE_SOURCE_SHA": SOURCE, "PINKHA_HANLIN_NATIVE_RUN_ID": run_id,
                       "PINKHA_HANLIN_NATIVE_RUN_ATTEMPT": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        prep = work / "prepare.xctestrun"
        base.write_descriptor(base.PREP, prep, environment={**environment,
            "PINKHA_HANLIN_NATIVE_PREPARATION": "1", "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1"}, preparation=True)
        receipt["stages"]["preparation"] = selected_test(work, prep, "AnytypeTests", PREP_METHOD.split("/")[0],
                                                        PREP_METHOD, udid, 240)
        container = Path(base.run(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"]).stdout.strip())
        raw = (container / "Library/Application Support/pinkha-hanlin-native-fixture.json").read_text()
        fixture = json.loads(raw)
        environment.update(native.fixture_environment(fixture, SOURCE, run_id, "1", time.time(), raw))
        (work / "native-fixture.json").write_text(raw)
        base.run(["xcrun", "simctl", "terminate", udid, "io.anytype.app"], check=False)
        ui = work / "ui.xctestrun"
        base.write_descriptor(base.UI, ui, environment=environment, preparation=False)
        try:
            receipt["stages"]["ui"] = selected_test(work, ui, "PinkhaStage1AcceptanceUITests", UI_METHOD,
                                                    UI_METHOD, udid, 600)
        finally:
            active = base.run(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"], check=False)
            if active.returncode == 0:
                result_path = Path(active.stdout.strip()) / "Library/Application Support/pinkha-hanlin-native-result.json"
                if result_path.is_file():
                    data = result_path.read_bytes()
                    require(len(data) <= 131072, "native_result_exceeds_bound")
                    (work / "native-result.json").write_bytes(data)
        result = json.loads((work / "native-result.json").read_bytes())
        accepted = native.validate_result(result, fixture, SOURCE, run_id, "1", time.time())
        receipt["nativeReceipt"] = {key: accepted[key] for key in
            ("status", "required_checks", "process_id", "presentation_count", "provider_configured", "source_sha", "run_id", "run_attempt")}
        receipt["nativeResultSHA256"] = digest(work / "native-result.json")
        receipt["status"] = "RETAINED_NATIVE_UI_AND_22_CHECKS_PASS"
    except BaseException as error:
        receipt["status"] = "FAIL"
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)[:1500]}
    finally:
        if udid:
            for action in ("shutdown", "delete"):
                try:
                    receipt[action + "Exit"] = base.run(["xcrun", "simctl", action, udid], timeout=60, check=False).returncode
                except BaseException as error:
                    receipt[action + "Error"] = type(error).__name__
            if receipt.get("deleteExit") != 0:
                receipt["status"] = "FAIL"
        try:
            unchanged = (all(tree(root) == inventories[name] for name, (root, _, _) in roots.items())
                         and all(digest(path) == sha for path, sha in descriptors.items()))
            receipt["originalInputsUnchanged"] = unchanged
            receipt["controllerInputsUnchanged"] = all(digest(stage / name) == row["sha256"]
                                                       for name, row in source["inputs"].items())
            if not unchanged or not receipt["controllerInputsUnchanged"]:
                receipt["status"] = "FAIL"
        except BaseException as error:
            receipt.update(status="FAIL", originalIntegrityError=type(error).__name__)
        receipt["finishedAt"] = datetime.now(timezone.utc).isoformat()
        (work / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))
    return 0 if receipt["status"] in {"QUALIFIED_NOT_EXECUTED", "RETAINED_NATIVE_UI_AND_22_CHECKS_PASS"} else 1


if __name__ == "__main__":
    def interrupted(signum, _):
        raise RuntimeError("owned_execution_interrupted:" + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    raise SystemExit(main())
