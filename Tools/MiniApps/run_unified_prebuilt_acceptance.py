#!/usr/bin/env python3
"""Execute five original Heart MiniApps methods using admitted existing products.

This is an explicit local execution, not a fabricated CI run or native-runtime
profile. It reuses the immutable combined producer and actual companion receipt.
No application, UI runner, library, or companion compilation is performed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import sys
import time
import traceback
import uuid

CORE_SHA = "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
ADMISSION_SHA = "82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
SOURCE = "6f1194f9b8c9540dea1187826dda6a256777dbbf"
PRODUCER = "70eb9c2d2cdfd920a65da59643dff7d4e7b775ff"
PRODUCER_MANIFEST = "350af7b55f5e981d2029778b75d61a17ea4db1b6df670ed623f630d283afb370"
BUNDLE = "io.anytype.app"
NATIVE_GROUP = "group.io.anytype.app.dev"
SHARED_GROUP = "group.com.itorah.shared"
METHODS = [
    ("prepare", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"),
    ("return-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen"),
    ("replay-ui", "PinkhaStage1AcceptanceUITests", "MiniAppsNativeAcceptanceUITests/testDuplicateCallbackDoesNotInsertAgain"),
    ("native-readback", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/verifyReturnedNativeDocument"),
    ("native-adapter", "AnytypeTests", "PinkhaMiniAppsNativePreparationTests/applySelectedTextAndPreserveNewerNativeContent"),
]

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def raw(path, limit=16 * 1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.stat().st_size <= limit, "original bounded regular file required: " + str(path))
    return path.read_bytes()

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(data)
    os.chmod(path, 0o600)

def module(path, name, expected=None):
    data = raw(path)
    require(expected is None or sha(data) == expected, "exact helper changed: " + name)
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--companion-manifest", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.root, args.core, args.admission, args.companion_manifest):
        require(path.is_absolute() and path.resolve() == path, "canonical absolute input required")
    require(not args.root.exists(), "refuse existing execution")
    admission_raw = raw(args.admission)
    require(sha(admission_raw) == ADMISSION_SHA, "exact combined source/product admission required")
    admission = json.loads(admission_raw)
    require(admission["sourceCommit"] == SOURCE and not admission.get("menuPagingUIOverride"),
            "same-source complete original App/UI required")
    core = module(args.core, "qualified_unified_miniapps_products", CORE_SHA)
    root = args.root
    root.mkdir(mode=0o700)
    # Preserve cp-cR's original directory modes inside this private parent.
    os.umask(0o022)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    commands = core.Commands(root / "commands", root)
    outcome = {"protocol": "pinkha-unified-miniapps-original-five-v1",
               "status": "FAIL", "executionOrigin": "local-mac", "builds": 0,
               "controllerSHA256": sha(raw(Path(__file__).resolve())),
               "coreSHA256": CORE_SHA, "admissionSHA256": ADMISSION_SHA,
               "companionManifestSHA256": PRODUCER_MANIFEST, "companionSourceCommit": PRODUCER,
               "sourceCommit": SOURCE, "methods": [], "testsExecuted": 0, "testCommandsInvoked": 0,
               "physicalSharing": "NOT_PROVEN_BY_SIMULATOR", "errors": []}
    udid = None
    built = None
    app_container = None
    primary = None
    def interrupted(number, _frame):
        raise RuntimeError("owned controller interrupted by signal " + str(number))
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, interrupted)
    try:
        proof, built, app = core.admit_and_clone_products(admission, root, evidence, commands)
        write(evidence / "original-product-admission.json", proof)
        source = Path(admission["sourceRoot"])
        before = json.loads(core.pinned(admission["sourceBefore"]))
        sys.path[:0] = [str(root / "helpers/Tools/CurrentAppleValidation"),
                       str(source / "Tools/MiniApps"), str(source / "Tools/Hanlin"),
                       str(source / "Tools/PinkhaNativeDerived")]
        core.common = importlib.import_module("contracts")
        local_producer = importlib.import_module("local_producer")
        selection = importlib.import_module("selection")
        host = importlib.import_module("run_host_tests")
        simulator_entitlements = importlib.import_module("simulator_entitlements")
        for imported in (local_producer, selection, host, simulator_entitlements):
            path = Path(imported.__file__).resolve()
            require(source in path.parents and
                    core.digest(path) == before["files"][str(path.relative_to(source))]["sha256"],
                    "foreign or altered original MiniApps validator")

        original_manifest = raw(args.companion_manifest, 8 * 1024**2)
        require(sha(original_manifest) == PRODUCER_MANIFEST, "exact original companion manifest required")
        original = args.companion_manifest.parent
        original_inventory = local_producer.inventory(original)
        companion_root = root / "original-companion"
        commands.run(["cp", "-cRp", str(original), str(companion_root)], "clone-original-companion", 180)
        require(local_producer.inventory(original) == original_inventory ==
                local_producer.inventory(companion_root), "companion producer changed during copy")
        copied_manifest = companion_root / args.companion_manifest.name
        require(sha(raw(copied_manifest, 8 * 1024**2)) == PRODUCER_MANIFEST, "companion manifest copy changed")
        pin = {"execution_origin": "local-mac", "run_id": None, "revision": PRODUCER,
               "repository": "davidpovarsky/hanlin-ai", "bundle_id": "com.itorah.hanlinminiapps",
               "local_manifest_path": str(copied_manifest), "local_manifest_sha256": PRODUCER_MANIFEST}
        producer = local_producer.admit(source, root / "companion", evidence, pin)
        write(evidence / "companion-original-custody.json",
              {"originalPath": str(args.companion_manifest), "manifestSHA256": PRODUCER_MANIFEST,
               "completeInventory": original_inventory, "nativeAcceptanceClaimed": False})
        app_info = plistlib.loads(raw(app / "Info.plist"))
        executable = app / app_info["CFBundleExecutable"]
        entitlements = simulator_entitlements.read_simulator_entitlements(executable)
        groups = entitlements["entitlements"].get("com.apple.security.application-groups", [])
        require(BUNDLE == app_info["CFBundleIdentifier"] and NATIVE_GROUP in groups and SHARED_GROUP in groups,
                "actual source app's native/shared simulator groups required")
        require(any("anytype" in x.get("CFBundleURLSchemes", []) for x in app_info.get("CFBundleURLTypes", [])),
                "actual source return URL scheme required")
        require(app_info.get("PinkhaNativeAppGroup", NATIVE_GROUP) == NATIVE_GROUP,
                "compiled native group override differs")
        write(evidence / "source-embedded-entitlements.json", entitlements)

        log, _ = commands.run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtimes")
        available = [x for x in json.loads(raw(log))["runtimes"]
                     if x.get("isAvailable") is True and x.get("version") == "27.0"
                     and x.get("buildversion") == "24A434"]
        require(len(available) == 1, "exact available iOS27 original runtime required")
        runtime = available[0]["identifier"]
        name = "PinkhaUnifiedMiniApps-" + str(uuid.uuid4())
        device_type = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"
        log, _ = commands.run(["xcrun", "simctl", "create", name, device_type, runtime], "create-device")
        udid = str(uuid.UUID(raw(log).decode().strip())).upper()
        write(evidence / "owned-simulator.json", {"udid": udid, "name": name,
              "deviceType": device_type, "runtime": runtime})
        commands.run(["xcrun", "simctl", "boot", udid], "boot")
        commands.run(["xcrun", "simctl", "bootstatus", udid, "-b"], "bootstatus", 180)
        commands.run(["xcrun", "simctl", "install", udid, str(app)], "install-source", 120)
        commands.run(["xcrun", "simctl", "install", udid, producer["app"]], "install-companion", 120)
        run_id = "local-unified-miniapps-" + str(uuid.uuid4())
        environment = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_MINIAPPS_NATIVE_TESTING": "1",
                       "GITHUB_SHA": SOURCE, "GITHUB_RUN_ID": run_id, "GITHUB_RUN_ATTEMPT": "1",
                       "PINKHA_MINIAPPS_NATIVE_GROUP": NATIVE_GROUP, "PINKHA_MINIAPPS_SOURCE_BUNDLE": BUNDLE}
        outcome.update(localExecutionID=run_id, ownedSimulator=udid)

        def data_container(label):
            nonlocal app_container
            log, _ = commands.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"], label, 30)
            path = Path(raw(log, 4096).decode().strip())
            owned = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
            require(path.is_dir() and not path.is_symlink() and path.resolve() == path
                    and owned in path.parents, "exact owned app data container required")
            require(app_container is None or app_container == path, "installed source container changed")
            app_container = path
            return path

        def test(index, extra=None):
            label, target, method = METHODS[index]
            native = target == "AnytypeTests"
            item = built["app" if native else "ui"]
            directory = evidence / label
            directory.mkdir(mode=0o700)
            stage = {"status": "FAIL", "testInvoked": False, "target": target, "method": method, "errors": []}
            stage_error = None
            try:
                core.product_integrity(item)
                actual_selector = target + "/" + selection.selector(target, method)
                descriptor, binding = core.bind_descriptor(item, app, actual_selector,
                                                          dict(environment, **(extra or {})))
                path = item["products"] / ("MiniApps-" + label + ".xctestrun")
                with path.open("xb") as stream:
                    stream.write(descriptor)
                os.chmod(path, 0o600)
                item["copies"][path.name] = {"kind": "file", "bytes": len(descriptor),
                                              "mode": 0o600, "sha256": sha(descriptor)}
                write(directory / "descriptor-binding.json", binding)
                listing = directory / "enumeration.json"
                argv = ["xcodebuild", "test-without-building", "-xctestrun", str(path),
                        "-destination", "platform=iOS Simulator,id=" + udid,
                        "-parallel-testing-enabled", "NO", "-only-testing:" + actual_selector,
                        "-collect-test-diagnostics", "never"]
                commands.run(argv + ["-enumerate-tests", "-test-enumeration-style", "flat",
                                     "-test-enumeration-format", "json", "-test-enumeration-output-path", str(listing)],
                             label + "-enumerate", 180)
                stage["enumeration"] = selection.validate_enumeration(json.loads(raw(listing)), target, method)
                core.product_integrity(item)
                require(core.digest(path) == sha(descriptor), "enumerated descriptor changed")
                log, result = commands.run(argv + ["-resultBundlePath", str(directory / "original.xcresult")],
                                           label + "-test", 600, checked=False)
                stage["command"] = result
                require(result["status"] == "PASS_COMMAND", "actual original method command failed")
            except BaseException as exc:
                stage_error = exc
                stage["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
            original = directory / "original.xcresult"
            if original.is_dir():
                for kind in ("summary", "tests"):
                    try:
                        log, _ = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                               "--path", str(original), "--format", "json"],
                                              label + "-" + kind, 120, capacity=False)
                        data = raw(log)
                        value = json.loads(data)
                        if kind == "summary":
                            stage["originalCounts"] = {k: value.get(k) for k in
                                ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                        (directory / (kind + ".json")).write_bytes(data)
                        os.chmod(directory / (kind + ".json"), 0o600)
                    except BaseException as exc:
                        stage["errors"].append({"phase": kind, "reason": str(exc)})
                try:
                    commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(original),
                                  "--output-path", str(directory / "private-attachments")],
                                 label + "-attachments", 180, capacity=False)
                except BaseException as exc:
                    stage["errors"].append({"phase": "attachments", "reason": str(exc)})
            try:
                core.product_integrity(item)
                if stage_error is None and not stage["errors"]:
                    summary = json.loads(raw(directory / "summary.json"))
                    tree = json.loads(raw(directory / "tests.json"))
                    require({k: summary.get(k) for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                            == {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0},
                            "exact one original method with no skip/failure required")
                    stage["actual"] = host.validate_results(summary, tree, {method}, udid)
                    require(b"** TEST EXECUTE SUCCEEDED **" in raw(root / "commands" / (label + "-test") / "original.log", 64*1024**2),
                            "original successful test stdout required")
                    stage["status"] = "PASS"
            except BaseException as exc:
                stage["errors"].append({"phase": "original-result", "reason": str(exc)})
            stage["testInvoked"] = (root / "commands" / (label + "-test") / "started.json").is_file()
            write(directory / "result.json", stage)
            outcome["methods"].append(stage)
            outcome["testCommandsInvoked"] += int(stage["testInvoked"])
            actual_count = stage.get("originalCounts", {}).get("totalTestCount")
            if type(actual_count) is int and actual_count >= 0:
                outcome["testsExecuted"] += actual_count
            require(stage["status"] == "PASS", "original MiniApps stage failed: " + label)

        test(0)
        fixture = json.loads(raw(data_container("fixture-container") / "Library/Application Support/miniapps-native-fixture.json"))
        require(fixture["sourceSHA"] == SOURCE and fixture["runID"] == run_id, "original native fixture identity differs")
        write(evidence / "private-native-fixture.json", fixture)
        ui_env = {"PINKHA_MINIAPPS_FIXTURE_JSON": json.dumps(fixture, ensure_ascii=False),
                  "PINKHA_MINIAPPS_SOURCE_BUNDLE": BUNDLE, "PINKHA_MINIAPPS_SOURCE_SCHEME": "anytype"}
        test(1, ui_env)
        directory = data_container("returned-container") / "Library/Application Support/MiniAppsReceipts"
        journals = [json.loads(raw(p)) for p in directory.glob("*/*.json")]
        journals = [x for x in journals if x.get("completed")]
        require(len(journals) == 2, "two actual completed warm/cold receipts required")
        ordered = []
        for key in ("returnedText", "coldReturnedText"):
            matches = [x for x in journals if [i.get("text") for i in x.get("additions", [])] == [fixture[key]]]
            require(len(matches) == 1 and len(matches[0]["insertedBlocks"]) == 1, "complete actual insertion receipt required")
            ordered.append(matches[0])
        request_ids = [str(uuid.UUID(x["requestID"])) for x in ordered]
        require(len(set(request_ids)) == 2, "distinct real callback request IDs required")
        write(evidence / "private-completed-host-receipts.json", ordered)
        callbacks = dict(PINKHA_MINIAPPS_REQUEST_ID=request_ids[0], PINKHA_MINIAPPS_COLD_REQUEST_ID=request_ids[1])
        test(2, dict(ui_env, **callbacks))
        test(3, callbacks)
        readback = json.loads(raw(data_container("readback-container") / "Library/Application Support/miniapps-native-readback.json"))
        require(readback["status"] == "NATIVE_HEART_READBACK_PASS" and readback["sourceSHA"] == SOURCE
                and readback["requestIDs"] == request_ids, "actual native cold readback differs")
        write(evidence / "private-native-readback.json", readback)
        test(4)
        adapter = json.loads(raw(data_container("adapter-container") / "Library/Application Support/miniapps-native-adapter-readback.json"))
        require(adapter["status"] == "NATIVE_MINIAPPS_ADAPTER_PASS" and adapter["sourceSHA"] == SOURCE
                and adapter["runID"] == run_id and adapter["producerRoundTrips"] == 0
                and adapter["preservedOutputCount"] == 1 and adapter["nativeAttachmentCount"] == 1,
                "actual native selected/file adapter receipt differs")
        for key in ("replacementPreservedBlockID", "replacementPreservedTree", "nativeMarksPreserved",
                    "replayPreservedNewerText", "conflictPreservedNewerText", "nativeAttachmentUploaded",
                    "nativeAttachmentByteReadback", "nestedTableSelectionCaptured",
                    "nestedTableReplacementPersisted", "expiredSelectionDidNotFallback"):
            require(adapter[key] is True, "original native adapter assertion missing: " + key)
        write(evidence / "private-native-adapter-readback.json", adapter)
        require(all(core.digest(source / name) == row["sha256"] for name, row in before["files"].items()),
                "compiled source closure changed")
        outcome.update(status="PASS_FIVE_ORIGINAL_MINIAPPS_METHODS", actualCompanionInvocations=2,
                       nativePreparation=1, actualUIMethods=2, nativeReadback=1, nativeAdapter=1)
    except BaseException as exc:
        primary = exc
        outcome["firstFailure"] = {"type": type(exc).__name__, "reason": str(exc)}
        (evidence / "private-failure-traceback.txt").write_text(traceback.format_exc())
        os.chmod(evidence / "private-failure-traceback.txt", 0o600)
    finally:
        if udid is not None:
            if app_container is None:
                try:
                    log, _ = commands.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"],
                                          "final-app-container", 30, capacity=False)
                    app_container = Path(raw(log, 4096).decode().strip())
                except BaseException as exc:
                    outcome["errors"].append({"phase": "final-app-container", "reason": str(exc)})
            try:
                commands.run(["xcrun", "simctl", "shutdown", udid], "shutdown", 120, capacity=False)
            except BaseException as exc:
                outcome["errors"].append({"phase": "shutdown-command", "reason": str(exc)})
            try:
                log, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], "shutdown-state", 30, capacity=False)
                devices = [d for ds in json.loads(raw(log))["devices"].values() for d in ds if d.get("udid") == udid]
                require(len(devices) == 1 and devices[0]["state"] == "Shutdown"
                        and devices[0]["name"] == name, "exact owned simulator not Shutdown")
                outcome["ownedSimulatorRetention"] = "Shutdown"
                if app_container is not None:
                    owned = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
                    require(app_container.is_dir() and app_container.resolve() == app_container
                            and not app_container.is_symlink() and owned in app_container.parents,
                            "final app container identity differs")
                    outcome["privateAppContainer"] = str(app_container)
            except BaseException as exc:
                outcome["errors"].append({"phase": "shutdown-state", "reason": str(exc)})
        if built is not None:
            for item in built.values():
                try:
                    core.product_integrity(item)
                except BaseException as exc:
                    outcome["errors"].append({"phase": "product-integrity", "reason": str(exc)})
        unresolved = []
        for group in commands.groups:
            # Never re-probe a positively reaped original group: its numeric ID
            # can later belong to an unrelated project.
            if group in commands.absent_groups:
                continue
            try:
                if commands.present(group):
                    unresolved.append(group)
                else:
                    commands.absent_groups.add(group)
            except BaseException as exc:
                unresolved.append(group)
                outcome["errors"].append({"phase": "owned-group-observation", "group": group, "reason": str(exc)})
        # Commands.run already stops its own live Popen on timeout/cancellation.
        # An unresolved historical group is retained as a failure requiring a
        # fresh ownership check, rather than signalling a possibly recycled ID.
        outcome["ownedGroupsRemaining"] = unresolved
        if outcome["errors"] or outcome["ownedGroupsRemaining"]:
            outcome["status"] = "FAIL"
        outcome["accountBackup"] = "PENDING_EXPLICIT_FOUR_SCOPE_RETENTION"
        write(evidence / "execution.json", outcome)
        print(json.dumps({"status": outcome["status"], "receipt": str(evidence / "execution.json"),
                          "sha256": sha(raw(evidence / "execution.json")), "ownedSimulator": udid}), flush=True)
    if primary is not None or outcome["status"] != "PASS_FIVE_ORIGINAL_MINIAPPS_METHODS":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
