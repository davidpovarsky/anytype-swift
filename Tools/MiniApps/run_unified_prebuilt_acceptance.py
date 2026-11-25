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
# Original control helpers are Git inputs, separate from the compiled App closure.
ORIGINAL_HELPERS = {
    "Tools/AnyEnginePort/native_ui_transition_contract.py": {
        "bytes": 12615,
        "sha256": "42d56e2193643fde5ae6f329b63a123fee89a2ef22d858e3bea8aeb94cd0d3d5",
        "gitBlob": "242cfe6ecaa6302a106f0f908ca47124f47e393b"
    },
    "Tools/Hanlin/host_command.py": {
        "bytes": 4236,
        "sha256": "5f09813c5719f5ea3920c003e58ac6b2b5633f276686bf6c5ef8bc6f9f39a807",
        "gitBlob": "4fd63c36dbaf47ede3267ee40b76e1a19828c241"
    },
    "Tools/Hanlin/prepare_sdk.py": {
        "bytes": 4915,
        "sha256": "234f597c629da30045392f74e2b6d204f2bbc6349b70bdccd5562dc0db491fe2",
        "gitBlob": "a9984c45773809ec552e013a1c2d3bba87df877b"
    },
    "Tools/Hanlin/run_host_tests.py": {
        "bytes": 39409,
        "sha256": "106d40df8594c067fdcc389d0ac93e3055a01247d431b13563f9d6e0d1c3403d",
        "gitBlob": "85efec75356c8fadcd13a09a7cb0c5dd722d89b0"
    },
    "Tools/Hanlin/shared_editor_profile.py": {
        "bytes": 1745,
        "sha256": "77d27d083f8073ad027cd28e98f2e2986aaee1cb2e31d2931287e33a4f8497c8",
        "gitBlob": "c486549fb852eb9360fd8e07e75444fcbbf613b4"
    },
    "Tools/Hanlin/wave15_core_profile.py": {
        "bytes": 7868,
        "sha256": "f544619607be0d25e74cff541ac66418b76df11abcd9c15c0ca774d6cbd5d96a",
        "gitBlob": "ebf9f9a1c8fbaaf0463e44e8f4e8a0d0b5835631"
    },
    "Tools/MiniApps/acceptance_profile.py": {
        "bytes": 1930,
        "sha256": "be61a6ebbcacb906d26c3587aa9d1c9c369f2e1ca80975df7369d779b4ff8e91",
        "gitBlob": "39affb5cc015aaf74a50724a87ed95ea77d6fda7"
    },
    "Tools/MiniApps/local_producer.py": {
        "bytes": 9772,
        "sha256": "4fca2ddd4e07af1f6b7f3856d0ee5838eb9e97cf9bd2feea9324052e4d41e518",
        "gitBlob": "a23f4ec747dc88fe461e469bcf82c52cf444fe85"
    },
    "Tools/MiniApps/selection.py": {
        "bytes": 3706,
        "sha256": "ef45ca8ee08848bd8bbd912bf60421c41c735155ebee9443bb2fe519a668b173",
        "gitBlob": "72a823511b444901a1b3984c78cddcdf9b1eb6cc"
    },
    "Tools/MiniApps/simulator_entitlements.py": {
        "bytes": 3658,
        "sha256": "aa1cfcd4f371dd25a637bc56ab281ef94f8bcdcc2bb415b9125dd0b0aa0b27a8",
        "gitBlob": "252ad38403dbd7fe5bcf9c3d30c5e8ab63a3b9d0"
    },
    "Tools/PinkhaNativeDerived/attachment_runtime.py": {
        "bytes": 11989,
        "sha256": "0154ae5f6b0af197d62abc7eeb6233adbe3d469723a75e15e233e7ab5e37019a",
        "gitBlob": "7e25529bccec4b7e5ec5d598a6781238ad73e20f"
    },
    "Tools/PinkhaNativeDerived/build_custom_heart.py": {
        "bytes": 12945,
        "sha256": "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
        "gitBlob": "e32c935fedce5fc732240bf9b2ada21764b5add1"
    },
    "Tools/PinkhaNativeDerived/build_native_ipa.py": {
        "bytes": 20302,
        "sha256": "c9e35a228779ae761d36cef204a32148ffdd3a338c9ede11dde6df4ebee21055",
        "gitBlob": "cb509ecc637ffb669569bfafd7471ba924a5c851"
    },
    "Tools/PinkhaNativeDerived/heart_runtime_profile.py": {
        "bytes": 18158,
        "sha256": "d354e5ccf20bfbdbeaf9f61a0043bfcbb137400b835f8b34e910453c35995001",
        "gitBlob": "71e4efb0a5b953f5428e67252545cd274479b64e"
    },
    "Tools/PinkhaNativeDerived/relink_verified_simulator.py": {
        "bytes": 8760,
        "sha256": "d2877f33e9850ee76734218c4e5d1fd2e2e1ea4da11713c35f7aa312e142df8c",
        "gitBlob": "092d30401c824d239f05c19ae18ecc77fb1cf4ec"
    },
    "Tools/PinkhaNativeDerived/rerun_original_ui.py": {
        "bytes": 18707,
        "sha256": "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0",
        "gitBlob": "ce14bb27846eb06900f7827449516ea9ed1c924f"
    },
    "Tools/PinkhaNativeDerived/validate_wave1.py": {
        "bytes": 11158,
        "sha256": "743ddea3e4e42640070035fe7d149d148dfff1cbdc852ef464c8c19da07253a0",
        "gitBlob": "b77dd4f92d0e6b32c94ee67528bc198747ec45ee"
    }
}
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
        # Admit all transitive local helper bytes before importing any of them.
        # These tools were never asserted to be compiled App inputs.
        for relative, binding in ORIGINAL_HELPERS.items():
            value = raw(source / relative)
            require(len(value) == binding["bytes"] and sha(value) == binding["sha256"],
                    "original Git-bound MiniApps helper changed: " + relative)
        write(evidence / "original-helper-admission.json",
              {"sourceCommit": SOURCE, "files": ORIGINAL_HELPERS,
               "compiledApplicationSources": False})
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
                    core.digest(path) == ORIGINAL_HELPERS[str(path.relative_to(source))]["sha256"],
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
        # This exact Debug-Anytype product has an empty owner override.
        # Original TargetsConstants.appGroup consequently selects its existing
        # debug group; the unmodified native preparation checks that at runtime.
        require(app_info.get("PinkhaNativeAppGroup") == "",
                "exact compiled Debug-Anytype empty owner override required")
        write(evidence / "source-native-group-binding.json",
              {"infoSHA256": core.digest(app / "Info.plist"),
               "compiledOwnerOverride": "", "originalDebugFallback": NATIVE_GROUP,
               "actualEmbeddedGroup": NATIVE_GROUP,
               "runtimeAssertion": "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"})
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
        require(all(core.digest(source / name) == row["sha256"] for name, row in ORIGINAL_HELPERS.items()),
                "original Git-bound validator changed during execution")
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
