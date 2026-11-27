#!/usr/bin/env python3
"""Run the original five MiniApps objectives, files and genuine account isolation.

This controller consumes a new original app/UI build receipt. It does not build,
replace native APIs, write engine stores, manufacture bridge requests/results or
claim physical-device/TestFlight acceptance. Failed runs retain their own device.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
import receipt_admission as gate


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")


def bundle_executable(bundle):
    info = plistlib.loads((bundle / "Info.plist").read_bytes())
    name = info.get("CFBundleExecutable")
    gate.require(isinstance(name, str) and Path(name).name == name and name not in {"", ".", ".."},
                 "Invalid actual bundle executable")
    path = gate.canonical(bundle / name)
    gate.require(path.is_relative_to(bundle), "Actual executable escaped its bundle")
    return info, path


def entries(descriptor, target):
    value = plistlib.loads(descriptor.read_bytes())
    version = value.get("__xctestrun_metadata__", {}).get("FormatVersion")
    if version == 2:
        configurations = value.get("TestConfigurations", [])
        gate.require(len(configurations) == 1 and configurations[0].get("IsEnabled", True),
                     "One enabled original Xcode configuration required")
        found = [entry for entry in configurations[0].get("TestTargets", [])
                 if entry.get("BlueprintName") == target]
    elif version == 1:
        found = [entry for name, entry in value.items() if isinstance(entry, dict)
                 and name != "__xctestrun_metadata__"
                 and (entry.get("BlueprintName") == target or name == target)]
    else:
        raise ValueError("Unsupported original Xcode descriptor")
    gate.require(len(found) == 1 and found[0].get("IsEnabled", True)
                 and found[0].get("TestBundlePath"), "Exact compiled target missing or disabled")
    return value, version, found[0]


def resolve_product(raw, root, host=None):
    gate.require(isinstance(raw, str) and raw, "Original Xcode path missing")
    allowed = {"__TESTROOT__"} | ({"__TESTHOST__"} if host else set())
    gate.require(set(re.findall(r"__[A-Za-z][A-Za-z0-9_]*?__", raw)).issubset(allowed),
                 "Unadmitted Xcode product placeholder")
    value = raw.replace("__TESTROOT__", str(root))
    if host:
        value = value.replace("__TESTHOST__", str(host))
    return gate.canonical(value, directory=True)


def bind_descriptor(original, destination, target, method, environment, products, clones, original_app, cloned_app):
    data, version, entry = entries(original, target)
    root = original.parent
    original_host = resolve_product(entry["TestHostPath"], root)
    test_bundle = resolve_product(entry["TestBundlePath"], root, original_host)
    slot = "app-derived" if target == "AnytypeTests" else "ui-derived"
    gate.require(original_host.is_relative_to(Path(products[slot]["base"]))
                 and test_bundle.is_relative_to(Path(products[slot]["base"])), "Test host escaped admitted products")
    if target == "AnytypeTests":
        gate.require(original_host == original_app, "Native test host differs from the admitted app")
    else:
        target_app = resolve_product(entry["UITargetAppPath"], root, original_host)
        gate.require(gate.inventory(target_app) == gate.inventory(original_app),
                     "UI descriptor points to another actual app product")
    if version == 2:
        data["TestConfigurations"][0]["TestTargets"] = [entry]
    else:
        data = {"__xctestrun_metadata__": data["__xctestrun_metadata__"], target: entry}
    selector = method + ("()" if target == "AnytypeTests" else "")
    entry.setdefault("EnvironmentVariables", {}).update(environment)
    entry["OnlyTestIdentifiers"] = [selector]
    # Existing skip filters and all other original test settings remain intact.
    def relocate(value):
        if isinstance(value, dict):
            return {key: relocate(child) for key, child in value.items()}
        if isinstance(value, list):
            return [relocate(child) for child in value]
        if isinstance(value, str):
            value = value.replace("__TESTROOT__", str(root))
            for key, record in products.items():
                value = value.replace(record["base"], str(clones[key]))
            return value
        return value
    data = relocate(data)
    # Preserve the actual app product tested by both original targets.
    if target != "AnytypeTests":
        actual = data["TestConfigurations"][0]["TestTargets"][0] if version == 2 else data[target]
        actual["UITargetAppPath"] = str(cloned_app)
    with destination.open("xb") as stream:
        plistlib.dump(data, stream)
    return selector, {"originalSHA256": gate.sha256(original), "configuredSHA256": gate.sha256(destination),
                      "target": target, "method": method, "nativeApp": str(cloned_app),
                      "originalTestBundle": str(test_bundle), "originalSkipFiltersPreserved": True}


def actual_cases(tree):
    result = {}
    def walk(value):
        if isinstance(value, dict):
            # Same original xcresult leaf identity used by the retained verifier.
            if value.get("nodeType") == "Test Case":
                identifier = value.get("nodeIdentifier")
                gate.require(isinstance(identifier, str) and identifier not in result, "Ambiguous actual test case")
                result[identifier] = value.get("result")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(tree)
    return result


def verify_test_result(summary, tree, target, method, udid, runtime):
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    gate.require(counts == {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0},
                 "Exactly one actual passed method and no skipped/failed methods required")
    configurations = summary.get("devicesAndConfigurations", [])
    gate.require(len(configurations) == 1, "Unexpected original test destinations")
    device = configurations[0]["device"]
    expected_model = "iPad" if runtime["family"] == "ipad" else "iPhone"
    gate.require(device.get("deviceId") == udid and device.get("osVersion") == runtime["version"]
                 and device.get("osBuildNumber") == runtime["build"]
                 and device.get("architecture") == runtime["architecture"]
                 and expected_model in device.get("modelName", ""), "Actual destination differs from admitted runtime")
    cases = actual_cases(tree)
    gate.require(len(cases) == 1 and all(result == "Passed" for result in cases.values())
                 and all(re.search(r"(?:^|/)" + re.escape(method) + r"(?:\(|/|$)", name) for name in cases),
                 "Original xcresult lacks the exact compiled method")
    return {"counts": counts, "cases": cases, "device": device, "target": target, "method": method}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--admit-only", action="store_true")
    args = parser.parse_args()
    gate.require(args.output.is_absolute() and not args.output.exists(), "Fresh absolute output directory required")
    args.output.mkdir(parents=True, mode=0o700)
    evidence = args.output / "evidence"
    evidence.mkdir(mode=0o700)
    receipt = {"schema": "pinkha.miniapps.new-source-execution/1", "status": "FAIL",
               "executionOrigin": "local-mac", "githubRunID": None, "builds": 0,
               "testMethodsExecuted": 0, "testCommandsInvoked": 0, "methods": [], "startedAt": time.time(),
               "physicalDevice": "NOT_RUN", "testFlight": "NOT_RUN", "ownedSimulator": None}
    primary = None
    try:
        contract, admission, products = gate.admit(args.contract, args.contract_sha256)
        gate.require(Path(__file__).resolve() == Path(contract["controls"]["root"]) / "Tools/MiniApps/run_receipt_acceptance.py",
                     "The executing controller differs from its committed closure")
        write(evidence / "input-contract.json", contract)
        write(evidence / "source-product-admission.json", admission)
        receipt.update(sourceCommit=contract["source"]["commit"],
                       controllerCommit=contract["controls"]["commit"],
                       contractSHA256=args.contract_sha256)
        if args.admit_only:
            receipt["status"] = "ADMITTED_ONLY_NO_TESTS"
            return 0
        gate.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                     "Real arm64 Apple execution is required")
        control = Path(contract["controls"]["root"])
        sys.path[:0] = [str(control / "Tools/MiniApps"), str(control / "Tools/AnyEnginePort")]
        owned = importlib.import_module("owned_commands")
        selection = importlib.import_module("native_ui_transition_contract")
        producer_module = importlib.import_module("local_producer")
        simulator_entitlements = importlib.import_module("simulator_entitlements")
        boundary = importlib.import_module("consumer_runtime_boundary")
        file_lane = importlib.import_module("file_acceptance")
        isolation = importlib.import_module("isolation_acceptance")
        for imported in (owned, selection, producer_module, simulator_entitlements, boundary, file_lane, isolation):
            gate.require(Path(imported.__file__).resolve().is_relative_to(control),
                         "A foreign helper was imported")
        def command(argv, label, timeout=120, checked=True):
            path = evidence / (label + ".log")
            result = owned.run_logged(argv, args.output, path, timeout)
            if checked:
                gate.require(result.returncode == 0, "Original command failed: " + label)
            return path, result
        runtime = contract["runtime"]
        for index, observation in enumerate(contract["toolchain"]):
            old = gate.read_ref(observation["original"])
            path, _ = command(observation["argv"], "toolchain-" + str(index), 60)
            gate.require(path.read_bytes() == old, "Actual Apple toolchain differs from original build")
        clones = {}
        for slot, record in products.items():
            clone = args.output / slot
            command(["cp", "-cRp", record["base"], str(clone)], "clone-" + slot, 180)
            gate.verify_inventory(clone, record["entries"])
            gate.verify_inventory(record["base"], record["entries"])
            clones[slot] = clone
        descriptor = {
            kind: Path(products[value["slot"]]["base"]) / value["path"]
            for kind, value in contract["descriptors"].items()
        }
        _, _, native_entry = entries(descriptor["app"], "AnytypeTests")
        original_app = resolve_product(native_entry["TestHostPath"], descriptor["app"].parent)
        gate.require(original_app.is_relative_to(Path(products["app-derived"]["base"])), "Original app escaped products")
        app = clones["app-derived"] / original_app.relative_to(Path(products["app-derived"]["base"]))
        info, executable = bundle_executable(app)
        bundle = contract["bundleID"]
        gate.require(info["CFBundleIdentifier"] == bundle
                     and "iPhoneSimulator" in info.get("CFBundleSupportedPlatforms", []),
                     "Actual product is not the declared simulator app")
        schemes = [x for item in info.get("CFBundleURLTypes", []) for x in item.get("CFBundleURLSchemes", [])]
        gate.require(contract["sourceScheme"] in schemes, "Original return URL scheme absent")
        entitlements = simulator_entitlements.read_simulator_entitlements(executable)
        groups = entitlements["entitlements"].get("com.apple.security.application-groups", [])
        gate.require(contract["nativeAppGroup"] in groups and "group.com.itorah.shared" in groups,
                     "Actual native/shared simulator groups absent")
        command(["codesign", "--verify", "--deep", "--strict", str(app)], "source-codesign", 120)
        write(evidence / "source-entitlements.json", entitlements)
        source = Path(contract["source"]["root"])
        boundary.inspect(source, app, evidence)
        pin = json.loads((source / "Tools/MiniApps/producer.json").read_bytes())
        producer = producer_module.admit(source, args.output / "companion", evidence, pin)

        listing, _ = command(["xcrun", "simctl", "list", "runtimes", "--json"], "runtimes")
        matches = [item for item in json.loads(listing.read_bytes())["runtimes"]
                   if item.get("isAvailable") is True and item["identifier"] == runtime["identifier"]
                   and item["version"] == runtime["version"] and item["buildversion"] == runtime["build"]]
        gate.require(len(matches) == 1, "Exact original simulator runtime is unavailable")
        run_id = "local-" + str(uuid.uuid4())
        device_name = "PinkhaMiniAppsReceipt-" + run_id
        path, _ = command(["xcrun", "simctl", "create", device_name, runtime["deviceType"], runtime["identifier"]], "create-device")
        udid = str(uuid.UUID(path.read_text().strip())).upper()
        receipt.update(runID=run_id, ownedSimulator={"udid": udid, "name": device_name, **runtime})
        write(evidence / "owned-simulator.json", receipt["ownedSimulator"])
        command(["xcrun", "simctl", "boot", udid], "boot", 60)
        command(["xcrun", "simctl", "bootstatus", udid, "-b"], "bootstatus", 180)
        command(["xcrun", "simctl", "install", udid, str(app)], "install-source", 120)
        command(["xcrun", "simctl", "install", udid, producer["app"]], "install-companion", 120)
        environment = {
            "PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_MINIAPPS_NATIVE_TESTING": "1",
            "PINKHA_MINIAPPS_NATIVE_GROUP": contract["nativeAppGroup"],
            "PINKHA_MINIAPPS_SOURCE_BUNDLE": bundle,
            "PINKHA_MINIAPPS_SOURCE_SHA": contract["source"]["commit"],
            "PINKHA_MINIAPPS_EXECUTION_ID": run_id,
        }
        app_container = None
        container_reads = 0
        def data_container():
            nonlocal app_container, container_reads
            container_reads += 1
            path, _ = command(["xcrun", "simctl", "get_app_container", udid, bundle, "data"],
                              "data-container-" + str(container_reads), 30)
            actual = gate.canonical(path.read_text().strip(), directory=True)
            owned_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
            gate.require(actual.is_relative_to(owned_root) and (app_container is None or app_container == actual),
                         "Actual owned application data container changed")
            app_container = actual
            return actual
        def test(index, extra=None):
            label, target, method, timeout = gate.METHODS[index]
            target_descriptor = descriptor["app" if target == "AnytypeTests" else "ui"]
            configured = evidence / (label + ".xctestrun")
            selector, binding = bind_descriptor(target_descriptor, configured, target, method,
                dict(environment, **(extra or {})), products, clones, original_app, app)
            write(evidence / (label + "-descriptor.json"), binding)
            result_path = evidence / (label + ".xcresult")
            enumeration = evidence / (label + "-enumeration.json")
            argv = ["xcodebuild", "test-without-building", "-xctestrun", str(configured),
                    "-destination", "platform=iOS Simulator,id=" + udid,
                    "-parallel-testing-enabled", "NO", "-only-testing:" + target + "/" + selector]
            command(argv + ["-enumerate-tests", "-test-enumeration-style", "flat",
                            "-test-enumeration-format", "json", "-test-enumeration-output-path", str(enumeration)],
                    label + "-enumerate", 360)
            plan, enabled, disabled = selection.enumerated_identifiers(json.loads(enumeration.read_bytes()))
            gate.require(enabled == {target + "/" + method + "()"}
                         and (target != "AnytypeTests" or plan == "AnytypeTests"),
                         "Compiled enumeration is not the exact original method")
            observed = {"label": label, "target": target, "method": method, "status": "FAIL",
                        "enabledIdentifiers": sorted(enabled), "disabledCount": len(disabled)}
            receipt["methods"].append(observed)
            receipt["testCommandsInvoked"] += 1
            try:
                _, result = command(argv + ["-resultBundlePath", str(result_path)], label + "-test", timeout, checked=False)
                observed["commandExitCode"] = result.returncode
            finally:
                if result_path.is_dir():
                    for mode in ("summary", "tests"):
                        command(["xcrun", "xcresulttool", "get", "test-results", mode, "--path",
                                 str(result_path), "--format", "json"], label + "-" + mode, 120)
                    command(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result_path),
                             "--output-path", str(evidence / (label + "-attachments"))],
                            label + "-attachments", 120, checked=False)
            summary = json.loads((evidence / (label + "-summary.log")).read_bytes())
            tree = json.loads((evidence / (label + "-tests.log")).read_bytes())
            observed["originalSummaryCounts"] = {key: summary.get(key) for key in
                ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
            count = summary.get("totalTestCount")
            if type(count) is int:
                receipt["testMethodsExecuted"] += count
            gate.require(observed.get("commandExitCode") == 0, "Actual original test command failed")
            observed.update(verify_test_result(summary, tree, target, method, udid, runtime))
            observed["status"] = "PASS_ACTUAL_ORIGINAL_METHOD"
            write(evidence / (label + "-verified.json"), observed)

        test(0)
        source_data = data_container()
        support = source_data / "Library/Application Support"
        fixture = json.loads((support / "miniapps-native-fixture.json").read_bytes())
        gate.require(fixture["sourceSHA"] == contract["source"]["commit"] and fixture["runID"] == run_id,
                     "Actual prepared native fixture differs")
        write(evidence / "fixture.json", fixture)
        ui_env = {"PINKHA_MINIAPPS_FIXTURE_JSON": json.dumps(fixture, ensure_ascii=False),
                  "PINKHA_MINIAPPS_SOURCE_BUNDLE": bundle,
                  "PINKHA_MINIAPPS_SOURCE_SCHEME": contract["sourceScheme"]}
        test(1, ui_env)
        data_container()
        journals = []
        for path in (support / "MiniAppsReceipts").glob("*/*.json"):
            value = json.loads(path.read_bytes())
            if value.get("completed"):
                journals.append(value)
        gate.require(len(journals) == 2, "Exactly two actual original warm/cold native receipts required")
        ordered = []
        for key in ("returnedText", "coldReturnedText"):
            found = [row for row in journals
                     if [item.get("text") for item in row.get("additions", [])] == [fixture[key]]]
            gate.require(len(found) == 1 and len(found[0]["insertedBlocks"]) == 1,
                         "Incomplete actual warm/cold native receipt")
            ordered.append(found[0])
        ids = [str(uuid.UUID(row["requestID"])) for row in ordered]
        gate.require(len(set(ids)) == 2, "Warm/cold original invocations must differ")
        write(evidence / "completed-host-receipts.json", ordered)
        callbacks = {"PINKHA_MINIAPPS_REQUEST_ID": ids[0], "PINKHA_MINIAPPS_COLD_REQUEST_ID": ids[1]}
        ui_env.update(callbacks)
        test(2, ui_env)
        test(3, callbacks)
        data_container()
        native = json.loads((support / "miniapps-native-readback.json").read_bytes())
        gate.require(native["status"] == "NATIVE_HEART_READBACK_PASS"
                     and native["sourceSHA"] == contract["source"]["commit"] and native["runID"] == run_id
                     and native["requestIDs"] == ids, "Original native readback receipt differs")
        write(evidence / "native-readback.json", native)
        test(4)
        data_container()
        adapter = json.loads((support / "miniapps-native-adapter-readback.json").read_bytes())
        gate.require(adapter["status"] == "NATIVE_MINIAPPS_ADAPTER_PASS"
                     and adapter["sourceSHA"] == contract["source"]["commit"] and adapter["runID"] == run_id
                     and adapter["producerRoundTrips"] == 0
                     and adapter["preservedOutputCount"] == 1 and adapter["nativeAttachmentCount"] == 1,
                     "Original native adapter receipt differs")
        for key in ("replacementPreservedBlockID", "replacementPreservedTree", "nativeMarksPreserved",
                    "replayPreservedNewerText", "conflictPreservedNewerText", "nativeAttachmentUploaded",
                    "nativeAttachmentByteReadback", "nestedTableSelectionCaptured",
                    "nestedTableReplacementPersisted", "expiredSelectionDidNotFallback"):
            gate.require(adapter[key] is True, "Original native adapter assertion missing: " + key)
        write(evidence / "native-adapter-readback.json", adapter)

        staged = file_lane.stage(source, udid, bundle, evidence, run_id)
        file_environment = dict(ui_env,
            PINKHA_MINIAPPS_SHARED_BRIDGE=staged["bridge"],
            PINKHA_MINIAPPS_FILE_ARCHIVE=staged["archive"],
            PINKHA_MINIAPPS_FILE_ARCHIVE_SHA256=staged["archive_sha256"],
            PINKHA_MINIAPPS_FILE_REPORT_NAME=staged["report_name"])
        test(5, file_environment)
        file_proof = file_lane.verify(staged, data_container(), fixture, bundle, evidence)
        isolation_name = "original-engine-account-ui-" + run_id.removeprefix("local-") + ".json"
        isolation_environment = dict(ui_env, PINKHA_MINIAPPS_SHARED_BRIDGE=staged["bridge"],
            PINKHA_MINIAPPS_ISOLATION_REPORT_NAME=isolation_name)
        test(6, isolation_environment)
        test(7, isolation_environment)
        isolation_proof = isolation.verify(data_container(), staged["bridge"], fixture, bundle, evidence, isolation_name)

        gate.verify_source(contract["source"])
        gate.verify_controls(contract["controls"])
        gate.verify_build(contract)
        for slot, record in products.items():
            gate.verify_inventory(record["base"], record["entries"])
            gate.verify_inventory(clones[slot], record["entries"])
        gate.require(receipt["testMethodsExecuted"] == len(gate.METHODS)
                     and all(item["status"] == "PASS_ACTUAL_ORIGINAL_METHOD" for item in receipt["methods"]),
                     "Incomplete actual original acceptance")
        receipt.update(status="PASS_EIGHT_ORIGINAL_MINIAPPS_METHODS",
                       sourceAndProductsUnchanged=True, originalFiveMethodsPassed=True,
                       fileRoundTripStatus=file_proof["status"],
                       engineAccountIsolationStatus=isolation_proof["status"],
                       actualCompanionUIInvocations=10, adapterProducerRoundTrips=0,
                       nativeMutationAndACKAtomic=False,
                       ownedSimulatorRetained=True)
        return 0
    except BaseException as error:
        primary = error
        receipt.update(status="FAIL", errorType=type(error).__name__, error=str(error),
                       ownedSimulatorRetained=receipt.get("ownedSimulator") is not None)
        return 1
    finally:
        # Count executed tests only from retained original xcresult summaries,
        # including failures that interrupted command/drain handling.
        actual_total = 0
        missing = []
        for item in receipt["methods"]:
            summary_path = evidence / (item["label"] + "-summary.log")
            try:
                original = json.loads(summary_path.read_bytes())
                count = original["totalTestCount"]
                gate.require(type(count) is int and count >= 0, "Invalid original test count")
                actual_total += count
                item["originalSummaryCounts"] = {key: original.get(key) for key in
                    ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
            except (OSError, ValueError, KeyError, TypeError):
                missing.append(item["label"])
        receipt["testMethodsExecuted"] = actual_total
        receipt["commandsWithoutReadableOriginalSummary"] = missing
        receipt["finishedAt"] = time.time()
        write(evidence / "execution.json", receipt)
        print(json.dumps({"status": receipt["status"], "receipt": str(evidence / "execution.json"),
                          "receiptSHA256": gate.sha256(evidence / "execution.json"),
                          "sourceCommit": receipt.get("sourceCommit"),
                          "testMethodsExecuted": receipt["testMethodsExecuted"],
                          "ownedSimulator": receipt.get("ownedSimulator"),
                          "error": str(primary) if primary else None}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
