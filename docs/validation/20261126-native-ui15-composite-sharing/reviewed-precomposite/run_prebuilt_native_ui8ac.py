#!/usr/bin/env python3
"""Run one unchanged native UI journey in the source-qualified unified app.

No application/native/UI compilation is performed. The original complete main
and UI build receipts are mandatory. All mutable test descriptors, simulator
data and any finite Hanlin HTTPS fixture belong to this explicit invocation.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import ssl
import subprocess
import sys
import time
import traceback
import uuid

TARGET = "PinkhaAnyNativeUITests"
STAGES = {
    "drag": ("NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen", 600),
    "archive": ("NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies", 1800),
    "history": ("NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen", 600),
    "hanlin": ("NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen", 600),
    "custom-type": ("NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen", 600),
    "bin": ("NativeLaunchTests/testNativeBinRestoreKeepsIdentityAndBodyAcrossColdReopen", 600),
    "miniapps": ("NativeLaunchTests/testAnyMiniAppsTextStudioWarmAndColdReturnPersistInNativeDocument", 900),
    "archive-picker-observe": ("NativeLaunchTests/testObserveCanonicalArchiveSystemPickers", 600),
}
FLOOR = 2 * 1024**3
LIFECYCLE = None


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def inventory(base):
    rows = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            rows.append({"path": str(path.relative_to(base)), "kind": "symlink",
                         "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": str(path.relative_to(base)), "kind": "file",
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    return rows


def original_module(path, name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, directory, label, *, timeout=120, environment=None, allow_failure=False, cleanup=False):
    require(not (directory / (label + ".command.json")).exists(), "unique_command_label_required")
    started = time.time()
    log = directory / (label + ".log")
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
               PYTHONDONTWRITEBYTECODE="1")
    if environment:
        env.update(environment)
    minimum = shutil.disk_usage(directory).free
    require(cleanup or minimum >= FLOOR, "owned_process_emergency_floor")
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=directory, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record = {"argv": argv, "pid": process.pid, "pgid": process.pid,
                  "started": started, "freeBytesBefore": minimum}
        if LIFECYCLE is not None:
            record.update(cleanupErrors=[], termination=[],
                          lifecycleSHA256="73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a")
        write(directory / (label + ".command.json"), record)
        stopped = None
        while process.poll() is None:
            free = shutil.disk_usage(directory).free
            minimum = min(minimum, free)
            if free < FLOOR and not cleanup:
                stopped = "RESOURCE_DISK_FLOOR"
            elif time.time() - started > timeout:
                stopped = "TIMEOUT"
            if stopped:
                if LIFECYCLE is not None:
                    LIFECYCLE._terminate_owned_process(process, record)
                else:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        process.wait()
                break
            time.sleep(1)
        if LIFECYCLE is not None:
            try:
                code = process.wait(timeout=1)
            except BaseException as exc:
                code = None
                record["cleanupErrors"].append({"phase": "final-owned-wait",
                    "type": type(exc).__name__, "reason": str(exc)})
        else:
            code = process.wait()
    if LIFECYCLE is not None:
        record.update(exitCode=code, elapsedSeconds=time.time() - started,
                      minimumFreeBytes=minimum, stopped=stopped, logSHA256=digest(log),
                      status="EXIT_RECORDED_PENDING_GROUP_OBSERVATION")
        write(directory / (label + ".process-exit.json"), record)
        observation = LIFECYCLE._observe_exited_group(process.pid)
        group = observation["status"]
        record["ownedGroupObservations"] = observation["observations"]
        record["processExitReceiptSHA256"] = digest(directory / (label + ".process-exit.json"))
    else:
        try:
            os.killpg(process.pid, 0)
            group = "STILL_PRESENT"
        except ProcessLookupError:
            group = "ABSENT_ESRCH"
        except PermissionError as exc:
            # A denied group probe must not discard the completed command ledger.
            # It remains a failure; no broader signal or ownership inference follows.
            group = "PRESENT_OR_UNRESOLVED_PERMISSION_DENIED"
            record["groupProbeError"] = {"type": type(exc).__name__, "reason": str(exc)}
    record.update(exitCode=code, elapsedSeconds=time.time() - started,
                  minimumFreeBytes=minimum, stopped=stopped, ownedProcessGroup=group,
                  logSHA256=digest(log), status="PASS" if code == 0 and not stopped and
                  group == "ABSENT_ESRCH" and not record.get("cleanupErrors") else "FAIL")
    write(directory / (label + ".result.json"), record)
    if not allow_failure:
        require(record["status"] == "PASS", "owned_command_failed:" + label)
    return record, log.read_bytes()


def bind(original, products, app, selector, runtime_root):
    require(set(original) == {TARGET, "__xctestrun_metadata__"}
            and original["__xctestrun_metadata__"]["FormatVersion"] == 1,
            "one_original_ui_target_required")
    target = original[TARGET]
    require(target["IsUITestBundle"] is True
            and target.get("UseUITargetAppProvidedByTests") is True
            and not target.get("SkipTestIdentifiers")
            and not target.get("OnlyTestIdentifiers")
            and not target.get("UITargetAppPath"), "unmodified_ui_only_descriptor_required")
    info = plistlib.loads((app / "Info.plist").read_bytes())
    require(info["CFBundleIdentifier"] == "io.anytype.app",
            "source_qualified_debug_application_identifier_required")
    value = copy.deepcopy(original)
    changed = value[TARGET]
    changed.pop("UseUITargetAppProvidedByTests")
    changed["UITargetAppPath"] = str(app)
    changed["UITargetAppBundleIdentifier"] = info["CFBundleIdentifier"]
    changed["OnlyTestIdentifiers"] = [selector]
    changed["DependentProductPaths"] = [str(app), *target["DependentProductPaths"]]
    changed["EnvironmentVariables"]["PINKHA_NATIVE_UI_UNIFIED_HOST"] = "1"
    changed["EnvironmentVariables"]["PINKHA_SIMULATOR_UI_DISPOSABLE"] = "1"
    changed["SystemAttachmentLifetime"] = "keepAlways"
    changed["UserAttachmentLifetime"] = "keepAlways"
    injections = {}
    for key in ("EnvironmentVariables", "TestingEnvironmentVariables",
                "UITargetAppEnvironmentVariables"):
        env = changed.get(key, {})
        if "DYLD_INSERT_LIBRARIES" in env:
            old = env["DYLD_INSERT_LIBRARIES"]
            parts = old.split(":")
            rewritten = []
            for part in parts:
                if part.endswith("/libMainThreadChecker.dylib"):
                    actual = runtime_root / "usr/lib/libMainThreadChecker.dylib"
                    require(actual.is_file(), "actual_runtime_main_thread_checker_required")
                    rewritten.append(str(actual))
                else:
                    rewritten.append(part)
            env["DYLD_INSERT_LIBRARIES"] = ":".join(rewritten)
            if old != env["DYLD_INSERT_LIBRARIES"]:
                injections[key] = {"before": old, "after": env["DYLD_INSERT_LIBRARIES"]}
    # The only descriptor changes are explicit app/selection/environment binding.
    inverse = copy.deepcopy(value)
    for key in ("UseUITargetAppProvidedByTests", "UITargetAppPath", "UITargetAppBundleIdentifier",
                "OnlyTestIdentifiers", "DependentProductPaths", "EnvironmentVariables",
                "TestingEnvironmentVariables", "UITargetAppEnvironmentVariables",
                "SystemAttachmentLifetime", "UserAttachmentLifetime"):
        if key in target:
            inverse[TARGET][key] = copy.deepcopy(target[key])
        else:
            inverse[TARGET].pop(key, None)
    require(inverse == original, "unexpected_test_descriptor_delta")

    def absolute_paths(item):
        if isinstance(item, str):
            return item.replace("__TESTROOT__", str(products))
        if isinstance(item, list):
            return [absolute_paths(x) for x in item]
        if isinstance(item, dict):
            return {k: absolute_paths(v) for k, v in item.items()}
        return item
    value = absolute_paths(value)
    return value, {"exactOriginalInverse": True, "runtimeInjection": injections,
                   "application": str(app), "bundleIdentifier": info["CFBundleIdentifier"],
                   "selector": TARGET + "/" + selector, "realVisibleEngineSelection": True}



def admit_miniapps_runner(source, main_record, ui_build, ui_record):
    require(main_record["sourceCommit"] == "5c05a612e4054a4adfa7f812343be6a15871cc89"
            and ui_record["runnerSourceCommit"] == "53eec4a2289f969979bc301760ce152088ebc2f7",
            "exact_additive_real_miniapps_runner_required")
    expected = {
        "sourceCommit": "53eec4a2289f969979bc301760ce152088ebc2f7",
        "originalSHA256": "2727945d9a6745c8f11d64841649c7a5117d79b85818f9406e7ed0e35ec346be",
        "compiledSHA256": "cc3f0e17c1c228b01a36c9e3307bcbae7a2f444f5c850614e7d843fd1e29dfc7",
        "allOriginalMethodsByteIdentical": True,
        "newMethods": [STAGES["miniapps"][0]],
        "testStorageOverrides": False,
        "actualCompanionRequired": True,
        "ordinaryAccountSelectionAfterColdCallback": True,
    }
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("miniAppsCrossAppFixture") == projection.get("miniAppsCrossAppFixture") == expected
            and projection["mainSourceCommit"] == main_record["sourceCommit"]
            and projection["runnerSourceCommit"] == expected["sourceCommit"]
            and projection["changedOriginalMethodAssertions"] == 0
            and projection["applicationBuildTargets"] == 0
            and projection["nativeLibraryBuilds"] == 0,
            "original_methods_and_exact_source_overlay_must_remain_bound")
    for name, row in projection["sourceFiles"].items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink() and ui_build in path.resolve().parents
                and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "compiled_UI_source_changed:" + name)
    original = source / "NativeApp/UITests/NativeLaunchTests.swift"
    compiled = ui_build / "source/UITests/NativeLaunchTests.swift"
    marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
    require(digest(original) == expected["originalSHA256"]
            and digest(compiled) == expected["compiledSHA256"]
            and compiled.read_bytes().count(marker) == 1
            and compiled.read_bytes().split(marker)[0].rstrip() == original.read_bytes().rstrip(),
            "additive_method_must_preserve_every_original_UI_method")
    return expected


def admit_current_runner(source, main_record, ui_build, ui_record):
    require(main_record["sourceCommit"] == "5ffff121e696044b0d1955524b7a69baf453b4b1",
            "exact_current_normal_storage_App_required")
    expected = {
        "sourceCommit": "5ffff121e696044b0d1955524b7a69baf453b4b1",
        "originalSHA256": "61a981863f52c18f5b2f73125209b39df8e6b7b5e9aabf6bb4cc09cfb703e687",
        "methodSectionSHA256": "3a4b0995b8a37f10521a4c6355c3830a2c152ea44f56d77a787c27b534b98465",
        "sourceAlreadyIntegrated": True,
        "allMiniAppsMethodBytesUnchanged": True,
        "testStorageOverrides": False,
        "disposableSimulatorObserverOptIn": True,
        "actualCompanionRequired": True,
        "ordinaryAccountSelectionAfterColdCallback": True,
    }
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("integratedMiniAppsFixture") == projection.get("integratedMiniAppsFixture") == expected
            and projection["mainSourceCommit"] == main_record["sourceCommit"]
            and projection["runnerSourceCommit"] == ui_record["runnerSourceCommit"]
            and projection["changedOriginalMethodAssertions"] == 0
            and projection["applicationBuildTargets"] == 0 and projection["nativeLibraryBuilds"] == 0,
            "current_fixture_original_build_and_assertions_required")
    for name, row in projection["sourceFiles"].items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink() and ui_build in path.resolve().parents
                and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "compiled_current_UI_source_changed:" + name)
    original = (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
    compiled = (ui_build / "source/UITests/NativeLaunchTests.swift").read_bytes()
    marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
    require(hashlib.sha256(original).hexdigest() == expected["originalSHA256"]
            and original.count(marker) == compiled.count(marker) == 1
            and hashlib.sha256(original.split(marker)[1]).hexdigest() == expected["methodSectionSHA256"]
            and original.split(marker)[1] == compiled.split(marker)[1],
            "original_actual_MiniApps_method_and_cold_storage_must_remain_identical")
    binding = ui_record.get("binContextPreparation")
    require(binding == projection.get("binContextPreparation"), "Bin_binding_changed")
    if binding is None:
        require(compiled == original and ui_record["runnerSourceCommit"] == main_record["sourceCommit"],
                "same_source_current_runner_required")
    else:
        require(binding.get("sourceCommit") in {"36401a8e49189465ad89e395d962695e3a76e67a",
                                                "06a3d5b83caf656f2b9a28618cd186c6794ab27e"},
                "explicit_Bin_preparation_revision_required")
        observed_creation = binding["sourceCommit"] == "06a3d5b83caf656f2b9a28618cd186c6794ab27e"
        wanted = {"sourceCommit": binding["sourceCommit"],
            "originalSHA256": expected["originalSHA256"],
            "compiledSHA256": "0b01a8f35eea248f2bbd7727e60c6a2bf95fdcd9af74674b58437d75d0b62eae",
            "reviewSHA256": "31b047c1fa07be8a86fbb078d1b6ae73dbcb8c7b48bb7d9457fdeee05a1606dc",
            "inverseDeltaRestoresCompleteOriginalFile": True,
            "allOriginalIdentityBodyBinRestoreColdReopenAssertionsUnchanged": True,
            "timeoutSeconds": 60, "gestureDurationSeconds": 1.1}
        if observed_creation:
            wanted.update(compiledSHA256="989af328bd04926cbef2f7e3fc529e13012b784d1c72fd90ac47a37c444254b3",
                          reviewSHA256="7619c15a8557736acdeb712b957d8405dd14fd4c0abb03f2297f3d6bdfd8babe",
                          creationPreparation="existing-createNamedItemWithObservedTransition")
        require(binding == wanted and ui_record["runnerSourceCommit"] == wanted["sourceCommit"]
                and hashlib.sha256(compiled).hexdigest() == wanted["compiledSHA256"]
                and digest(ui_build / "bin-preparation-source-review.json") == wanted["reviewSHA256"],
                "exact_reviewed_Bin_preparation_required")
        method = b"    func testNativeBinRestoreKeepsIdentityAndBodyAcrossColdReopen()"
        start = b"        let row = app.buttons[title].firstMatch\n"
        end = b"        let rowID = row.identifier\n"
        a = original.index(start, original.index(method)); b = original.index(end, a)
        c = compiled.index(start, compiled.index(method)); d = compiled.index(end, c)
        restored = compiled[:c] + original[a:b] + compiled[d:]
        if observed_creation:
            m = restored.index(method); n = restored.index(b"    private func makeApplication(", m)
            section = restored[m:n]
            section = section.replace(method + b" throws {", method + b" {", 1)
            section = section.replace(b'        try createNamedItemWithObservedTransition(app, action: "any-native-new-document", title: title)',
                                      b'        createNamedItem(app, action: "any-native-new-document", title: title)', 1)
            restored = restored[:m] + section + restored[n:]
        require(restored == original, "Bin_inverse_must_restore_complete_original_file")
    return {"integratedMiniAppsFixture": expected, "binContextPreparation": binding}


def admit_current_menu_runner(source, main_record, ui_build, ui_record):
    expected = {'mainSourceCommit': '0c5ffc51cdeb480194fdd4d5e396a602d04d5d78', 'sourceCommit': '9b7f0df07ad4b9f81829ee834ac30c5c4c8588fd', 'originalSHA256': '989af328bd04926cbef2f7e3fc529e13012b784d1c72fd90ac47a37c444254b3', 'compiledSHA256': 'de36d8508963db5e31554e88078a60cbf2273ba8ae67a8d53c597647f97a4b97', 'originalMethodSectionSHA256': '3a4b0995b8a37f10521a4c6355c3830a2c152ea44f56d77a787c27b534b98465', 'compiledMethodSectionSHA256': 'cef7734232b8f12ff432a97b435a5c6e0801d2cd77a30ce097e83f5e1cf40a63', 'reviewSHA256': 'f5811451e908f601be5ea6005912b13b759e9e288afdd4231e478c8d51ed062f', 'inverseDeltaRestoresCompleteOriginalFile': True, 'allOriginalCrossAppNativeColdAssertionsUnchanged': True, 'testStorageOverrides': False, 'actualCompanionRequired': True, 'ordinaryAccountSelectionAfterColdCallback': True, 'nativeCallsAdded': 0, 'timeoutsChanged': 0, 'productChanges': 0}
    require(main_record["sourceCommit"] == expected["mainSourceCommit"],
            "exact_build12_menu_preparation_App_required")
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("currentMiniAppsMenuFixture") ==
                projection.get("currentMiniAppsMenuFixture") == expected
            and projection["mainSourceCommit"] == main_record["sourceCommit"]
            and projection["runnerSourceCommit"] == ui_record["runnerSourceCommit"] == expected["sourceCommit"]
            and projection["changedOriginalMethodAssertions"] == 0
            and projection["applicationBuildTargets"] == 0 and projection["nativeLibraryBuilds"] == 0
            and projection.get("binContextPreparation") is None
            and projection.get("integratedMiniAppsFixture") is None,
            "exact_menu_UI_projection_and_original_assertions_required")
    for name, row in projection["sourceFiles"].items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink() and ui_build in path.resolve().parents
                and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "compiled_menu_UI_source_changed:" + name)
    original = (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
    compiled = (ui_build / "source/UITests/NativeLaunchTests.swift").read_bytes()
    previous = b'        func roundTrip(_ text: String, cold: Bool) {\n            tapReady(app.buttons["any-native-miniapps"])'
    replacement = b'        func roundTrip(_ text: String, cold: Bool) {\n            tapReady(app.buttons["any-native-document-options"])\n            tapReady(app.buttons["any-native-miniapps"])'
    require(hashlib.sha256(original).hexdigest() == expected["originalSHA256"]
            and hashlib.sha256(compiled).hexdigest() == expected["compiledSHA256"]
            and digest(ui_build / "miniapps-menu-source-review.json") == expected["reviewSHA256"]
            and original.count(previous) == compiled.count(replacement) == 1
            and compiled.replace(replacement, previous) == original,
            "one_actual_menu_tap_must_restore_complete_original_UI_file")
    marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
    require(hashlib.sha256(original.split(marker)[1]).hexdigest() == expected["originalMethodSectionSHA256"]
            and hashlib.sha256(compiled.split(marker)[1]).hexdigest() == expected["compiledMethodSectionSHA256"],
            "every_original_cross_app_native_cold_assertion_required")
    return expected


def native8ac_module():
    path = Path(__file__).resolve().with_name("native8ac_profile.py")
    require(digest(path) == "6cfb95a83fb6b7156d9af9ddde1cdd953a191a91e6946dd4869b951659595ec2",
            "exact_App15_NativeUI_profile_required")
    sys.dont_write_bytecode = True
    original = path.read_bytes()
    require(hashlib.sha256(original).hexdigest() ==
            "6cfb95a83fb6b7156d9af9ddde1cdd953a191a91e6946dd4869b951659595ec2",
            "App15_profile_changed_during_admission")
    module = type(sys)("qualified_native8ac")
    module.__file__ = str(path)
    exec(compile(original, str(path), "exec"), module.__dict__)
    return module


def native11619_module():
    path = Path(__file__).resolve().with_name("native11619_profile.py")
    require(digest(path) == "58643d32057cf6f692b39e15eb53d50925170d26ccbe12304c55a62f73fa5e41", "exact_App14_NativeUI_profile_required")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_native11619", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bin_confirmation_module():
    path = Path(__file__).resolve().with_name("bin_confirmation_preparation.py")
    require(digest(path) == "6f30156103912fdebe67bedc530e57f159ece79d640cde38b1c05b51e67341a4", "exact_Bin_confirmation_source_validator_required")
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_bin_confirmation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admit_410b_runner(source, main_record, ui_build, ui_record):
    expected = {'sourceCommit': 'e540cd7e01b497f1b3173ae2e68b43ade0b00b6f', 'originalSHA256': '6fbcd0173351597af99dd6d79e7869ac72077c0b9ad2ff464d9c02e60d096d02', 'compiledSHA256': '6fbcd0173351597af99dd6d79e7869ac72077c0b9ad2ff464d9c02e60d096d02', 'miniAppsMethodSectionSHA256': 'cef7734232b8f12ff432a97b435a5c6e0801d2cd77a30ce097e83f5e1cf40a63', 'sourceAlreadyIntegrated': True, 'allOriginalMethodAssertionsUnchanged': True, 'testStorageOverrides': False, 'actualCompanionRequired': True, 'ordinaryAccountSelectionAfterColdCallback': True, 'binPreparation': 'real-accessible-native-row-menu', 'nativeSourceManifestSHA256': '410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9'}
    require(main_record["sourceCommit"] == expected["sourceCommit"]
            and ui_record["runnerSourceCommit"] == expected["sourceCommit"]
            and main_record["inputs"]["nativeSourceManifestSHA256"] == expected["nativeSourceManifestSHA256"]
            and main_record.get("assemblyReceiptSHA256") ==
                "8556b47a6a7e523bd5ad4c58ae292501acda1038b0d1f827e268cef15a542797",
            "exact_current410b_source_and_assembly_required")
    pins = {
        "nativeSHA256": "48905b7312d7228fe88a60517ec90c1c23d73f2ada762877c05ace9752103342",
        "sdkReceiptSHA256": "bad0afa285da6bd023235b15f82329f9d7b32ec50bf9194d63b9ee96730324a5",
        "lockSHA256": "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd",
    }
    for key, value in pins.items():
        require(main_record["inputs"].get(key) == value
                and ui_record.get("reviewedInputProfile", {}).get(key) == value,
                "exact_current410b_dependency_required:" + key)
    projection = json.loads((ui_build / "projection.json").read_bytes())
    require(ui_record.get("current410bFixture") == projection.get("current410bFixture") == expected
            and projection["mainSourceCommit"] == projection["runnerSourceCommit"] == expected["sourceCommit"]
            and projection["changedOriginalMethodAssertions"] == 0
            and projection["applicationBuildTargets"] == projection["nativeLibraryBuilds"] == 0,
            "complete_original_current410b_UI_required")
    for name, row in projection["sourceFiles"].items():
        path = ui_build / name
        require(path.is_file() and not path.is_symlink() and ui_build in path.resolve().parents
                and path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
                "compiled_current410b_UI_source_changed:" + name)
    original = (source / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
    compiled = (ui_build / "source/UITests/NativeLaunchTests.swift").read_bytes()
    marker = b"// BEGIN_NATIVE_MINIAPPS_CROSS_APP_UI_V1\n"
    require(original == compiled and hashlib.sha256(original).hexdigest() == expected["originalSHA256"]
            and original.count(marker) == 1
            and hashlib.sha256(original.split(marker)[1]).hexdigest() == expected["miniAppsMethodSectionSHA256"],
            "every_original_current410b_native_UI_byte_required")
    return expected


def companion86_module():
    path = Path(__file__).with_name("companion86_profile.py")
    require(digest(path) == "75f441f073f8e85ac18c0eb110dac0c8847c1d955f0f025bd305cfc11e045f78",
            "exact_App14_original_companion86_profile_required")
    return original_module(path, "qualified_App14_companion86")


def admit_real_companion(source, manifest_path, out, app):
    require(manifest_path is not None and manifest_path.is_absolute()
            and manifest_path.resolve() == manifest_path and not manifest_path.is_symlink()
            and digest(manifest_path) == "350af7b55f5e981d2029778b75d61a17ea4db1b6df670ed623f630d283afb370",
            "actual_original_companion_manifest_required")
    helpers = {
        "local_producer.py": "4fca2ddd4e07af1f6b7f3856d0ee5838eb9e97cf9bd2feea9324052e4d41e518",
        "simulator_entitlements.py": "aa1cfcd4f371dd25a637bc56ab281ef94f8bcdcc2bb415b9125dd0b0aa0b27a8",
    }
    helper_root = source / "Tools/MiniApps"
    for name, pin in helpers.items():
        require(digest(helper_root / name) == pin, "original_companion_validator_changed:" + name)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(helper_root))
    entitlements = __import__("simulator_entitlements")
    require(Path(entitlements.__file__).resolve() == helper_root / "simulator_entitlements.py",
            "foreign_simulator_entitlement_validator")
    producer_module = original_module(helper_root / "local_producer.py", "original_real_native_companion")
    original_root = manifest_path.parent
    original_inventory = producer_module.inventory(original_root)
    copied = out / "original-companion"
    run(["cp", "-cRp", str(original_root), str(copied)], out, "clone-original-companion", timeout=180)
    require(producer_module.inventory(original_root) == original_inventory == producer_module.inventory(copied),
            "original_companion_changed_during_copy")
    copied_manifest = copied / manifest_path.name
    pin = {"execution_origin": "local-mac", "run_id": None,
           "revision": "70eb9c2d2cdfd920a65da59643dff7d4e7b775ff",
           "repository": "davidpovarsky/hanlin-ai", "bundle_id": "com.itorah.hanlinminiapps",
           "local_manifest_path": str(copied_manifest), "local_manifest_sha256": digest(manifest_path)}
    evidence = out / "companion-evidence"
    producer = producer_module.admit(source, out / "companion", evidence, pin)
    info = plistlib.loads((app / "Info.plist").read_bytes())
    actual = entitlements.read_simulator_entitlements(app / info["CFBundleExecutable"])
    require(info["CFBundleIdentifier"] == "io.anytype.app"
            and "group.com.itorah.shared" in actual["entitlements"].get("com.apple.security.application-groups", [])
            and any("anytype" in value.get("CFBundleURLSchemes", []) for value in info.get("CFBundleURLTypes", [])),
            "actual_source_shared_group_and_return_scheme_required")
    write(out / "companion-binding.json", {
        "originalManifestSHA256": digest(manifest_path), "originalProducerSource": pin["revision"],
        "actualOriginalBuildVerified": True, "completeProducerInventory": original_inventory,
        "actualSourceEntitlements": actual, "physicalSharing": "NOT_PROVEN_BY_SIMULATOR",
        "companionBuilds": 0, "originalProducerAcceptanceClaimed": False})
    return producer, producer_module, original_root, original_inventory


def qualify_miniapps_report(out):
    attachments = out / "private-original-attachments"
    run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(out / "Original.xcresult"),
         "--output-path", str(attachments)], out, "miniapps-original-attachments", timeout=180, cleanup=True)
    attachments.chmod(0o700)
    reports = []
    for path in attachments.glob("*.json"):
        require(path.is_file() and not path.is_symlink(), "regular_original_attachment_required")
        if path.stat().st_size > 2 * 1024**2:
            continue
        try:
            value = json.loads(path.read_bytes())
        except (ValueError, UnicodeError):
            continue
        if isinstance(value, dict) and value.get("schema") == "any-miniapps-real-cross-app-ui/v1":
            reports.append((path, value))
    require(len(reports) == 1, "one_original_real_cross_app_result_required")
    path, value = reports[0]
    expected = {"fixtureUsesNormalAppStorage": True, "testStorageOverrides": False,
        "actualCompanionReturns": 2, "sourceTerminatedBeforeSecondReturn": True,
        "manualSourceLaunchForCallback": False, "ordinaryAccountSelectionAfterColdCallback": True,
        "manualDocumentSelectionForCallback": False,
        "nativeReadOrigin": "original-runtime-readback-and-mounted-editor",
        "nativeReadExtraCallsByObserver": 0, "originalBlockPreserved": True, "nativeParagraphCount": 3}
    require(all(value.get(key) == expected_value for key, expected_value in expected.items())
            and all(re.fullmatch(r"[0-9a-f]{64}", value.get(key, ""))
                    for key in ("sameSpaceSHA256", "sameObjectSHA256"))
            and type(value.get("initialProcessID")) is int and type(value.get("finalProcessID")) is int
            and value["initialProcessID"] > 0 and value["finalProcessID"] > 0
            and value["initialProcessID"] != value["finalProcessID"],
            "actual_cross_app_and_cold_native_assertions_required")
    result = {"status": "QUALIFIED_ORIGINAL_XCTEST_ATTACHMENT_NOT_INDEPENDENT_NATIVE_CALL",
              "originalAttachmentSHA256": digest(path), "originalAttachment": path.name,
              "assertedScope": value, "extraNativeCalls": 0}
    write(out / "original-miniapps-result-qualified.json", result)
    return result


def main():
    global LIFECYCLE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path, required=True)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--ui-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--frozen-inputs", type=Path)
    parser.add_argument("--companion-manifest", type=Path)
    parser.add_argument("--retain-owned-simulator", action="store_true",
                        help="Keep the exact owned device Shutdown for diagnostic continuity.")
    args = parser.parse_args()
    for path in (args.main_root, args.main_evidence, args.ui_build, args.output):
        require(path.is_absolute() and path.resolve() == path, "canonical_absolute_path_required")
    require(all(args.main_root in p.parents for p in
                (args.main_evidence, args.ui_build, args.output)), "owned_workspace_required")
    require(not args.output.exists(), "refuse_existing_execution_output")
    args.output.mkdir(mode=0o700)
    os.umask(0o077)
    out = args.output
    if args.frozen_inputs is not None:
        require(args.frozen_inputs.is_absolute()
                and args.frozen_inputs.resolve() == args.frozen_inputs
                and args.main_root in args.frozen_inputs.parents,
                "owned_canonical_frozen_inputs_required")
    require(args.source_root is None or args.frozen_inputs is None,
            "explicit_current_source_cannot_mix_with_historical_frozen_inputs")
    source = args.source_root or (args.frozen_inputs or args.main_root) / "source"
    receipt = {"status": "FAIL", "stage": args.stage, "applicationBuilds": 0,
               "nativeLibraryBuilds": 0, "uiRunnerBuilds": 0, "testsExecuted": 0,
               "controllerSHA256": digest(Path(__file__).resolve())}
    udid = None
    fixture_config = None
    products = None
    app = None
    app_original = None
    original_app_inventory = None
    copied_ui_inventory = None
    companion_contract = None
    first_error = None
    cleanup_errors = []
    try:
        main_record = json.loads((args.main_evidence / "receipt.json").read_bytes())
        ui_record = json.loads((args.ui_build / "receipt.json").read_bytes())
        require(main_record["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                and main_record["sourceUnchanged"] is True and main_record["testsExecuted"] == 0,
                "complete_original_main_build_required")
        require(ui_record["status"] == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
                and ui_record["sourceCommit"] == main_record["sourceCommit"]
                and ui_record["testsExecuted"] == 0
                and ui_record.get("mainReceiptSHA256") == digest(args.main_evidence / "receipt.json"),
                "same_source_exact_main_receipt_ui_runner_build_required")
        if ui_record.get("miniAppsCrossAppFixture") is not None:
            receipt["miniAppsCrossAppFixture"] = admit_miniapps_runner(source, main_record, args.ui_build, ui_record)
        if ui_record.get("integratedMiniAppsFixture") is not None:
            receipt.update(admit_current_runner(source, main_record, args.ui_build, ui_record))
        if ui_record.get("currentMiniAppsMenuFixture") is not None:
            receipt["currentMiniAppsMenuFixture"] = admit_current_menu_runner(source, main_record, args.ui_build, ui_record)
        if (main_record["sourceCommit"] == "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
                or main_record.get("inputs", {}).get("nativeSourceManifestSHA256") ==
                    "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
                or ui_record.get("current11619Fixture") is not None):
            receipt["current11619Fixture"] = native11619_module().admit(
                source, main_record, args.ui_build, ui_record)
        if (main_record["sourceCommit"] == "379ca3568f247d2fc218ed63df24796d461713c0"
                or main_record.get("inputs", {}).get("nativeSourceManifestSHA256") ==
                    "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
                or ui_record.get("current8acFixture") is not None):
            current8ac = native8ac_module()
            runtime_binding = current8ac.qualify_runtime_inputs(source, args.main_evidence, main_record)
            projection = json.loads((args.ui_build / "projection.json").read_bytes())
            require(ui_record.get("current8acRuntimeIdentity") ==
                    projection.get("current8acRuntimeIdentity") == runtime_binding,
                    "exact_App15_original_runtime_proofs_required")
            receipt["current8acFixture"] = current8ac.admit(
                source, main_record, args.ui_build, ui_record)
            receipt["current8acRuntimeIdentity"] = runtime_binding
            LIFECYCLE = current8ac.owned_lifecycle(source, out, out / "owned-command-lifecycle")
        require(args.source_root is None or receipt.get("current8acFixture") is not None,
                "explicit_source_root_is_only_for_closed_App15_warm_layout")
        if ui_record.get("current410bFixture") is not None:
            receipt["current410bFixture"] = admit_410b_runner(source, main_record, args.ui_build, ui_record)
        if ui_record.get("current410bBinConfirmationFixture") is not None:
            require(args.stage == "bin" and ui_record.get("current410bFixture") is None,
                    "Bin_confirmation_derivative_has_one_explicit_original_stage")
            receipt["current410bBinConfirmationFixture"] = bin_confirmation_module().admit(
                source, main_record, args.ui_build, ui_record)
        require(main_record["sourceCommit"] != "e540cd7e01b497f1b3173ae2e68b43ade0b00b6f"
                or receipt.get("current410bFixture") is not None
                or receipt.get("current410bBinConfirmationFixture") is not None,
                "current410b_fixture_binding_cannot_be_omitted")
        if args.stage == "archive-picker-observe":
            require(main_record["sourceCommit"] == "5ffff121e696044b0d1955524b7a69baf453b4b1",
                    "exact_observation_app_source_required")
            method_start = "    func testObserveCanonicalArchiveSystemPickers() throws {"
            method_end = "    private func openCanonicalArchiveObservationEntry"
            method_hashes = []
            for path in (source / "NativeApp/UITests/NativeLaunchTests.swift",
                         args.ui_build / "source/UITests/NativeLaunchTests.swift"):
                text = path.read_text()
                require(text.count(method_start) == 1 and text.count(method_end) == 1,
                        "one_original_picker_observation_method_required")
                body = method_start + text.split(method_start, 1)[1].split(method_end, 1)[0]
                method_hashes.append(hashlib.sha256(body.encode()).hexdigest())
            require(method_hashes == ["49e9472a160dcb7f4cb6824e6e11369120a6d5cb6ee6f592ade19c3f66d00ded", "49e9472a160dcb7f4cb6824e6e11369120a6d5cb6ee6f592ade19c3f66d00ded"],
                    "original_picker_observation_method_changed")
            receipt["observationScope"] = {
                "methodSHA256": method_hashes[0],
                "purpose": "observe_original_system_picker_presentation_after_actual_blank_exporter",
                "acceptance": False, "exportSaveInvoked": False,
                "importFileSelected": False, "archiveRoundtripAccepted": False,
                "originalArchiveFailureReceiptSHA256":
                    "733b210f79f5b31cb07772e104f6dfd43285d0e11dd818346fa28eb537131d94"}
        if args.stage == "miniapps":
            require((receipt.get("miniAppsCrossAppFixture") is not None
                     or receipt.get("integratedMiniAppsFixture") is not None
                     or receipt.get("currentMiniAppsMenuFixture") is not None
                      or receipt.get("current410bFixture") is not None
                      or receipt.get("current11619Fixture") is not None
                      or receipt.get("current8acFixture") is not None)
                    and args.companion_manifest is not None,
                    "real_companion_and_new_compiled_method_required")
        else:
            require(args.companion_manifest is None, "companion_is_only_needed_for_its_scoped_stage")
        if args.frozen_inputs is not None:
            frozen = json.loads((args.frozen_inputs / "receipt.json").read_bytes())
            require(frozen.get("status") == "PASS_EXACT_FROZEN_NATIVE_UI_INPUTS"
                    and frozen.get("sourceCommit") == main_record["sourceCommit"]
                    and frozen.get("mainReceiptSHA256") == digest(args.main_evidence / "receipt.json")
                    and frozen.get("uiReceiptSHA256") == digest(args.ui_build / "receipt.json"),
                    "exact_frozen_source_and_product_provenance_required")
            receipt["frozenInputReceiptSHA256"] = digest(args.frozen_inputs / "receipt.json")
        before = json.loads((args.main_evidence / "source-before.json").read_bytes())
        require(before == json.loads((args.main_evidence / "source-after.json").read_bytes()),
                "unchanged_built_source_required")
        source_head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                                     capture_output=True, text=True, check=True).stdout.strip()
        require(source_head == before["commit"], "frozen_checkout_required")
        for name, row in before["files"].items():
            require(digest(source / name) == row["sha256"], "source_changed:" + name)
        all_products = args.main_evidence / "products-all.json"
        require(digest(all_products) == main_record["completeProductsInventory"]["sha256"],
                "original_product_inventory_changed")
        original_products = json.loads(all_products.read_bytes())["app-derived"]
        app_original = (args.frozen_inputs / "Anytype.app" if args.frozen_inputs is not None else
                        Path(original_products["base"]) / "Debug-Anytype-iphonesimulator/Anytype.app")
        prefix = "Debug-Anytype-iphonesimulator/Anytype.app/"
        original_app_inventory = []
        for row in original_products["entries"]:
            if row["path"].startswith(prefix):
                original_app_inventory.append(dict(row, path=row["path"][len(prefix):]))
        require(original_app_inventory and inventory(app_original) == original_app_inventory,
                "built_main_application_changed")
        ui_products = args.ui_build / "derived/Build/Products"
        templates = list(ui_products.glob("*.xctestrun"))
        require(len(templates) == 1, "one_original_native_ui_descriptor_required")
        product_record = args.ui_build / "products-all.json"
        require(digest(product_record) == ui_record["completeProductsInventory"]["sha256"],
                "native_ui_build_product_record_changed")
        ui_inventory = json.loads(product_record.read_bytes())
        require(ui_inventory and inventory(ui_products) == ui_inventory,
                "original_native_ui_products_changed")
        products = out / "ui-products"
        run(["cp", "-cR", str(ui_products), str(products)], out, "clone-ui-products")
        require(inventory(products) == ui_inventory, "ui_product_clone_mismatch")
        copied_ui_inventory = ui_inventory
        app = out / "Anytype.app"
        run(["cp", "-cR", str(app_original), str(app)], out, "clone-unified-app")
        require(inventory(app) == original_app_inventory, "app_clone_mismatch")
        receipt.update(sourceCommit=source_head,
                       mainReceiptSHA256=digest(args.main_evidence / "receipt.json"),
                       runnerReceiptSHA256=digest(args.ui_build / "receipt.json"),
                       historyKeyboardPreparation=ui_record.get("historyKeyboardPreparation"),
                       runnerSourceCommit=ui_record.get("runnerSourceCommit"),
                       archiveGrabberPreparation=ui_record.get("archiveGrabberPreparation"),
                       originalAppFileCount=len(original_app_inventory))
        if args.stage == "miniapps":
            if (receipt.get("current11619Fixture") is not None
                    or receipt.get("current8acFixture") is not None):
                companion_contract = companion86_module().admit(
                    source, args.companion_manifest, out, app,
                    lambda argv, label, timeout: run(argv, out, label, timeout=timeout))
            else:
                companion_contract = admit_real_companion(source, args.companion_manifest, out, app)
            receipt["companionManifestSHA256"] = digest(args.companion_manifest)
            receipt["companionBuilds"] = 0
        _, raw = run(["xcrun", "simctl", "list", "runtimes", "--json"], out, "runtimes")
        runtimes = [x for x in json.loads(raw)["runtimes"] if
                    x.get("isAvailable") is True and x.get("version") == "27.0"
                    and "iOS" in x.get("name", "")]
        require(len(runtimes) == 1, "one_available_original_ios27_runtime_required")
        _, raw = run(["xcrun", "simctl", "list", "devicetypes", "--json"], out, "device-types")
        types = [x for x in json.loads(raw)["devicetypes"] if
                 x.get("identifier") == "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"]
        require(len(types) == 1, "one_available_ipad_pro_m5_device_type_required")
        runtime = runtimes[0]
        name = "PinkhaUnifiedD-" + args.stage + "-" + str(uuid.uuid4())
        _, raw = run(["xcrun", "simctl", "create", name, types[0]["identifier"],
                      runtime["identifier"]], out, "create-simulator")
        udid = str(uuid.UUID(raw.decode().strip())).upper()
        write(out / "simulator.json", {"ownedUDID": udid, "name": name,
              "runtime": runtime["identifier"], "deviceType": types[0]["identifier"]})
        run(["xcrun", "simctl", "boot", udid], out, "boot-simulator")
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], out, "bootstatus", timeout=180)
        _, raw = run(["xcrun", "simctl", "getenv", udid, "SIMULATOR_ROOT"],
                     out, "simulator-runtime-root")
        runtime_root = Path(raw.decode().strip())
        require(runtime_root.is_dir(), "observed_runtime_root_required")
        run(["xcrun", "simctl", "install", udid, str(app)], out, "install-unified-app", timeout=120)
        if companion_contract is not None:
            run(["xcrun", "simctl", "install", udid, companion_contract[0]["app"]],
                out, "install-real-companion", timeout=120)
        selector, allowance = STAGES[args.stage]
        original_template = plistlib.loads(templates[0].read_bytes())
        configured, binding = bind(original_template, products, app, selector, runtime_root)
        fixture_environment = {}
        if args.stage == "hanlin":
            private = out / "private-provider"
            private.mkdir(mode=0o700)
            fixture = source / "Tools/AnyEngineValidation/HanlinProviderFixture/fixture.py"
            fixture_config = private / "private-config.json"
            run([sys.executable, "-B", str(fixture), "start", "--private-dir", str(private),
                 "--safe-result", str(out / "provider-start.json")], out, "start-provider", timeout=90)
            fixture_config = private / "private-config.json"
            conf = json.loads(fixture_config.read_bytes())
            ca = private / "root-ca.pem"
            require(hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca.read_text())).hexdigest()
                    == conf["rootCAFingerprintSHA256"], "original_fixture_ca_mismatch")
            fixture_environment = conf["testRunnerEnvironment"]
            expected_keys = {"TEST_RUNNER_PINKHA_HANLIN_FIXTURE_" + suffix for suffix in
                             ("URL", "MODEL", "KEY", "CONTROL_URL", "CONTROL_TOKEN")}
            require(set(fixture_environment) == expected_keys, "exact_fixture_environment_required")
            run(["xcrun", "simctl", "keychain", udid, "add-root-cert", str(ca)],
                out, "owned-simulator-fixture-trust")
        descriptor = out / "Selected.xctestrun"
        descriptor.write_bytes(plistlib.dumps(configured, sort_keys=False))
        descriptor.chmod(0o600)
        binding.update(originalSHA256=digest(templates[0]), copiedSHA256=digest(descriptor),
                       originalMainReceiptSHA256=receipt["mainReceiptSHA256"])
        write(out / "descriptor-binding.json", binding)
        plan = ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
                "-destination", "platform=iOS Simulator,id=" + udid,
                "-parallel-testing-enabled", "NO", "-test-timeouts-enabled", "YES",
                "-default-test-execution-time-allowance", str(allowance),
                "-maximum-test-execution-time-allowance", str(allowance),
                "-only-testing:" + TARGET + "/" + selector,
                "-collect-test-diagnostics", "never",
                "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGN_IDENTITY=-",
                "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES"]
        enumeration = out / "enumeration.json"
        run(plan + ["-enumerate-tests", "-test-enumeration-style", "flat",
                    "-test-enumeration-format", "json", "-test-enumeration-output-path",
                    str(enumeration)], out, "enumerate", timeout=360,
                    environment=fixture_environment)
        contract = original_module(source / "Tools/AnyEnginePort/native_ui_transition_contract.py",
                                   "original_native_ui_selection")
        label, enabled, disabled = contract.enumerated_identifiers(
            json.loads(enumeration.read_bytes()))
        require(enabled == {TARGET + "/" + selector + "()"}, "exact_compiled_method_not_selected")
        require(digest(descriptor) == binding["copiedSHA256"], "descriptor_changed_after_enumeration")
        record, _ = run(plan + ["-resultBundlePath", str(out / "Original.xcresult")],
                        out, "execute", timeout=allowance + 300,
                        environment=fixture_environment, allow_failure=True)
        receipt["testCommand"] = record
        require(record["status"] == "PASS", "actual_original_ui_execution_failed")
        if args.stage == "hanlin":
            run([sys.executable, "-B", str(fixture), "verify", "--private-config",
                 str(fixture_config), "--safe-result", str(out / "provider-contract.json")],
                out, "verify-provider", timeout=60)
    except BaseException as exc:
        first_error = {"type": type(exc).__name__, "reason": str(exc)}
        write(out / "first-failure.json", {**first_error, "traceback": traceback.format_exc()})
    finally:
        # Only the original xcresult may establish completed test counts.
        # A terminated xcodebuild can leave an incomplete result bundle.
        issued = (out / "execute.command.json").is_file()
        receipt["testCommandIssued"] = issued
        receipt["testsExecuted"] = None if issued else 0
        receipt["testResultAvailability"] = "UNAVAILABLE" if issued else "NOT_STARTED"
        result_path = out / "Original.xcresult"
        if result_path.is_dir():
            try:
                values = {}
                for kind in ("summary", "tests"):
                    _, raw = run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                  "--path", str(result_path), "--format", "json"],
                                 out, "original-" + kind, timeout=120, cleanup=True)
                    values[kind] = json.loads(raw)
                    write(out / (kind + ".json"), values[kind])
                parser_module = original_module(
                    source / "Tools/AnyEnginePort/verify_native_test_execution.py",
                    "original_native_ui_results")
                cases = parser_module.test_cases(values["tests"])
                counts = {k: values["summary"].get(k) for k in
                          ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                receipt.update(counts=counts, actualCases=cases,
                               testsExecuted=counts.get("totalTestCount"),
                               testResultAvailability="ORIGINAL_XCRESULT")
                selector = STAGES[args.stage][0]
                require(counts == {"totalTestCount": 1, "passedTests": 1,
                                   "failedTests": 0, "skippedTests": 0}
                        and len(cases) == 1 and all(x == "Passed" for x in cases.values())
                        and any(re.search(r"(?:^|/)" + re.escape(selector) + r"(?:\(|/|$)", x)
                                for x in cases), "exact_original_method_did_not_pass")
                devices = values["summary"]["devicesAndConfigurations"]
                require(len(devices) == 1
                        and devices[0]["device"]["deviceId"].upper() == udid
                        and devices[0]["device"]["architecture"] == "arm64",
                        "original_result_destination_mismatch")
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-results", "reason": str(exc)})
        if args.stage == "miniapps" and not first_error and not cleanup_errors:
            try:
                receipt["originalCrossAppReport"] = qualify_miniapps_report(out)
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-cross-app-result", "reason": str(exc)})
        if fixture_config is not None and fixture_config.is_file():
            try:
                run([sys.executable, "-B", str(source / "Tools/AnyEngineValidation/"
                     "HanlinProviderFixture/fixture.py"), "stop", "--private-config",
                     str(fixture_config)], out, "stop-provider", timeout=60, cleanup=True)
            except BaseException as exc:
                cleanup_errors.append({"phase": "provider-stop", "reason": str(exc)})
        if udid is not None:
            sandbox = None
            try:
                _, raw = run(["xcrun", "simctl", "get_app_container", udid,
                              "io.anytype.app", "data"], out, "native-sandbox-path",
                             cleanup=True)
                sandbox = Path(raw.decode().strip())
                require(sandbox.is_absolute() and sandbox.resolve() == sandbox
                        and udid in sandbox.parts and sandbox.is_dir(),
                        "owned_native_sandbox_path_required")
            except BaseException as exc:
                cleanup_errors.append({"phase": "private-native-sandbox", "reason": str(exc)})
            try:
                run(["xcrun", "simctl", "shutdown", udid], out, "shutdown-simulator",
                    timeout=60, cleanup=True)
                if sandbox is not None:
                    retained = out / "private-native-sandbox"
                    run(["cp", "-cR", str(sandbox), str(retained)], out,
                        "retain-native-sandbox", timeout=120, cleanup=True)
                    retained.chmod(0o700)
                    write(out / "private-native-sandbox-retention.json",
                          {"original": str(sandbox), "retained": str(retained),
                           "sourceSimulator": udid, "containsPrivateNativeAccountData": True})
            except BaseException as exc:
                cleanup_errors.append({"phase": "native-sandbox-retention", "reason": str(exc)})
            deletion_commands = () if args.retain_owned_simulator else (
                ("delete-simulator", ["xcrun", "simctl", "delete", udid]),)
            for label, command in deletion_commands:
                try:
                    run(command, out, label, timeout=60, cleanup=True)
                except BaseException as exc:
                    cleanup_errors.append({"phase": label, "reason": str(exc)})
            try:
                _, raw = run(["xcrun", "simctl", "list", "devices", "--json"],
                             out, "final-devices", cleanup=True)
                owned = [d for group in json.loads(raw)["devices"].values()
                         for d in group if d["udid"].upper() == udid]
                if args.retain_owned_simulator:
                    require(len(owned) == 1 and owned[0]["state"] == "Shutdown",
                            "retained_owned_simulator_must_be_shutdown")
                else:
                    require(not owned, "owned_simulator_still_exists")
            except BaseException as exc:
                cleanup_errors.append({"phase": "device-absence", "reason": str(exc)})
        try:
            if receipt.get("current8acFixture") is not None:
                require(native8ac_module().qualify_runtime_inputs(
                    source, args.main_evidence, main_record) == receipt["current8acRuntimeIdentity"],
                    "original_App15_runtime_inputs_changed_during_UI_execution")
            if companion_contract is not None:
                producer, producer_module, original_root, original_inventory = companion_contract
                require(producer_module.inventory(original_root) == original_inventory
                        and producer_module.inventory(Path(producer["app"])) == producer["manifest"]["app_files"],
                        "actual_companion_original_or_extracted_products_changed")
            if app_original is not None and original_app_inventory is not None:
                require(inventory(app_original) == original_app_inventory,
                        "original_main_products_changed")
            if app is not None and original_app_inventory is not None:
                require(inventory(app) == original_app_inventory, "copied_main_products_changed")
            if products is not None and copied_ui_inventory is not None:
                require(inventory(products) == copied_ui_inventory, "copied_ui_products_changed")
            write(out / "products-after.json", {
                "originalAppUnchanged": app_original is not None,
                "copiedAppUnchanged": app is not None,
                "copiedUIUnchanged": products is not None,
                "privateNativeSandboxRetained": (out / "private-native-sandbox").is_dir()})
        except BaseException as exc:
            cleanup_errors.append({"phase": "product-integrity", "reason": str(exc)})
        receipt.update(firstFailure=first_error, diagnosticFailures=cleanup_errors,
                       ownedSimulator=udid,
                       ownedSimulatorRetention=("Shutdown" if args.retain_owned_simulator
                                                else "Deleted"),
                       finished=time.time())
        receipt["status"] = "PASS" if first_error is None and not cleanup_errors and \
            receipt.get("counts", {}).get("passedTests") == 1 else "FAIL"
        if args.stage == "archive-picker-observe" and receipt["status"] == "PASS":
            receipt["status"] = "PASS_DIAGNOSTIC_ONLY_NOT_ARCHIVE_ACCEPTANCE"
        write(out / "receipt.json", receipt)
    expected_status = ("PASS_DIAGNOSTIC_ONLY_NOT_ARCHIVE_ACCEPTANCE"
                       if args.stage == "archive-picker-observe" else "PASS")
    require(receipt["status"] == expected_status, "scoped_unified_native_ui_execution_failed")


if __name__ == "__main__":
    main()
