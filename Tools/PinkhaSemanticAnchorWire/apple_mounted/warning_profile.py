"""Opt-in admission for the Page154 failed-startup UI continuation.

The native App and its preparation XCTest remain the immutable 681 Products.
Only the declared downstream UI source differs. No process or network calls.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import xml.etree.ElementTree as ET

PLAN_SHA256 = "69302465d2480e7dfc483f3d9f0789fb38b9628c91f1d33bedde2fcddb11aa1d"
APP_COMMIT = "68148339c275268795360d71d519a5baf003adf8"
UI_PATH = "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
UI_SHA256 = "a79807cb99f6998201f7c20ec5f9f9032cbcebc6ec8e517820408b4402bae017"
ORIGINAL_UI_SHA256 = "468139db53be7dac0570ea16c7fec918332f44107927d6043a9bcc4469773c8b"
TARGET = "PinkhaStage1AcceptanceUITests"
SELECTOR = TARGET + "/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
PREPARATION = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
PROJECT = "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj"
GENERATED = "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
SCHEME = "PinkhaPrebuiltUI"
SOURCE_NAMES = {
    "AnytypeComprehensiveAcceptanceUITests.swift", "HanlinNativeAcceptanceUITests.swift",
    "HanlinSelectionAcceptanceUITests.swift", "PinkhaStage1AcceptanceUITests.swift",
    "PinkhaT5NativeAcceptanceUITests.swift", "PinkhaTorahQuoteAcceptanceUITests.swift",
    "SemanticAnchorPage154MountedUITests.swift",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, maximum=512 * 1024):
    path = Path(path)
    value = path.lstat()
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and value.st_size <= maximum,
            "bounded_regular_warning_input_required")
    return path.read_bytes()


def read_plan():
    path = Path(__file__).with_name("warning-ui-inputs.json")
    raw = regular(path)
    require(sha(raw) == PLAN_SHA256, "exact_warning_ui_plan_required")
    value = json.loads(raw)
    require(value["schema"] == "pinkha-page154-startup-warning-ui-v1"
            and value["app_commit"] == APP_COMMIT and value["ui_path"] == UI_PATH
            and value["candidate_ui_sha256"] == UI_SHA256
            and value["original_ui_sha256"] == ORIGINAL_UI_SHA256
            and value["preparation_selector"] == PREPARATION and value["ui_selector"] == SELECTOR
            and value["fresh_setup_new_acceptance_credit"] == 0, "warning_plan_identity_differs")
    expected = {PROJECT + "/project.pbxproj",
                PROJECT + "/xcshareddata/xcschemes/PinkhaStage1Acceptance.xcscheme"}
    expected |= {"PinkhaStage1Acceptance/Tests/" + name for name in SOURCE_NAMES}
    require(set(value["files"]) == expected, "exact_nine_ui_inputs_required")
    return value


def source_admission(original_plan, current_inputs, app_inputs, plan):
    """One explicit changed UI input; every immutable App-plan row stays exact."""
    require(plan == read_plan(), "unreviewed_warning_plan")
    require(current_inputs.get("Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json")
            == plan["original_mounted_source_plan_sha256"], "original_mounted_source_plan_changed")
    for name, row in original_plan["files"].items():
        require(app_inputs.get(name) == row["sha256"], "immutable_mounted_app_input_changed:" + name)
        expected = UI_SHA256 if name == UI_PATH else row["sha256"]
        require(current_inputs.get(name) == expected, "unreviewed_current_mounted_input:" + name)
    require(original_plan["files"][UI_PATH]["sha256"] == ORIGINAL_UI_SHA256,
            "original_warning_ui_source_missing")
    for name, row in plan["files"].items():
        require(app_inputs.get(name) == row["original_sha256"]
                and current_inputs.get(name) == row["sha256"], "ui_source_origin_differs:" + name)
        require(row["origin"] == ("controller" if name == UI_PATH else "app"),
                "ui_source_owner_differs")
    require(current_inputs.get(plan["generator_path"]) == plan["generator_sha256"],
            "qualified_ui_generator_changed")
    return {"app_source": APP_COMMIT, "changed_ui_path": UI_PATH,
            "original_ui_sha256": ORIGINAL_UI_SHA256, "current_ui_sha256": UI_SHA256,
            "ui_inputs": len(plan["files"]), "plan_sha256": PLAN_SHA256}


def copy_sources(directory, controller, app, plan):
    directory, controller, app = map(Path, (directory, controller, app))
    require(directory.is_absolute() and directory.resolve() == directory and not directory.exists(),
            "fresh_warning_ui_source_root_required")
    require(plan == read_plan(), "exact_warning_plan_required_for_copy")
    payloads = {}
    for name, row in plan["files"].items():
        owner = controller if row["origin"] == "controller" else app
        path = owner / name
        require(path.resolve().is_relative_to(owner.resolve()), "ui_source_escaped_owner")
        raw = regular(path)
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "ui_source_bytes_changed:" + name)
        payloads[name] = raw
    directory.mkdir(mode=0o700)
    for name, raw in payloads.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush(); os.fsync(stream.fileno())
        path.chmod(0o600)  # The qualified generator edits only its separate copied project.
    return {name: {"bytes": len(raw), "sha256": sha(raw)} for name, raw in payloads.items()}


def generated_project(directory, generated, plan):
    """Check the actual output of the unchanged, qualified UI-only generator."""
    directory, generated = Path(directory), Path(generated)
    require(generated == directory / GENERATED, "unexpected_ui_only_project_location")
    project = regular(generated / "project.pbxproj").decode("utf8")
    require(project.count("isa = PBXNativeTarget;") == 1
            and project.count('productType = "com.apple.product-type.bundle.ui-testing";') == 1,
            "one_ui_test_target_required")
    for forbidden in ("Anytype.xcodeproj", "com.apple.product-type.application",
                      "PBXTargetDependency", "PBXContainerItemProxy",
                      "XCLocalSwiftPackageReference", "XCRemoteSwiftPackageReference",
                      "XCSwiftPackageProductDependency", "TestTargetID"):
        require(forbidden not in project, "app_or_package_reference_remains:" + forbidden)
    require(project.count('TEST_TARGET_NAME = "";') == 4, "implicit_app_target_remains")
    require(set(re.findall(r"path = ([A-Za-z0-9_]+\.swift);", project)) == SOURCE_NAMES,
            "ui_compile_source_roster_changed")
    scheme = generated / "xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"
    root = ET.fromstring(regular(scheme))
    build = root.find("BuildAction")
    require(build is not None and build.get("buildImplicitDependencies") == "NO",
            "implicit_builds_must_be_disabled")
    refs = list(root.iter("BuildableReference"))
    require(len(refs) == 2 and all(r.get("BlueprintName") == TARGET
            and r.get("ReferencedContainer") == "container:PinkhaPrebuiltUI.xcodeproj" for r in refs),
            "one_ui_build_and_test_reference_required")
    require(root.find(".//TestPlans") is None and root.find(".//MacroExpansion") is None
            and root.find(".//BuildableProductRunnable") is None, "app_or_named_plan_remains")
    extra = {GENERATED + "/project.pbxproj",
             GENERATED + "/xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme"}
    expected = set(plan["files"]) | extra
    paths = [path for path in directory.rglob("*") if path.is_file()]
    require(all(not path.is_symlink() for path in directory.rglob("*"))
            and {p.relative_to(directory).as_posix() for p in paths} == expected,
            "unexpected_generated_ui_input")
    result = {}
    for path in paths:
        name = path.relative_to(directory).as_posix()
        raw = regular(path)
        if name in plan["files"]:
            require(sha(raw) == plan["files"][name]["sha256"], "copied_ui_source_changed:" + name)
        result[name] = {"sha256": sha(raw), "bytes": len(raw)}
    return result


def build_command(project, derived, udid, flags):
    require(re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", udid or ""),
            "owned_ui_build_udid_required")
    return ["xcodebuild", "build-for-testing", "-project", str(project), "-scheme", SCHEME,
            "-configuration", "Debug-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
            "-parallel-testing-enabled", "NO", "-derivedDataPath", str(derived),
            "-only-testing:" + SELECTOR, *flags]


def same_job_descriptor(raw):
    value = plistlib.loads(raw)
    require(isinstance(value, dict) and set(value) == {"__xctestrun_metadata__", TARGET}
            and value["__xctestrun_metadata__"].get("FormatVersion") == 1,
            "one_new_ui_descriptor_v1_required")
    target = value[TARGET]
    require(isinstance(target, dict) and target.get("BlueprintName", TARGET) == TARGET
            and target.get("IsUITestBundle") is True and target.get("IsEnabled", True) is True,
            "new_ui_target_differs")
    host = target.get("TestHostPath")
    require(isinstance(host, str) and host.startswith("__TESTROOT__/Debug-Anytype-iphonesimulator/")
            and target.get("UseUITargetAppProvidedByTests") is True
            and "UITargetAppPath" not in target and "UITargetAppBundleIdentifier" not in target
            and target.get("DependentProductPaths") == [
                host, host + "/PlugIns/" + TARGET + ".xctest"],
            "previously_observed_page_ui_target_mode_changed")
    environment = target.get("TestingEnvironmentVariables", {})
    require(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in environment.items()), "testing_environment_shape_differs")
    tokens = environment.get("DYLD_INSERT_LIBRARIES", "").split(":")
    mtc = [token for token in tokens if token.endswith("/libMainThreadChecker.dylib")]
    require(len(mtc) <= 1, "ambiguous_new_main_thread_checker")
    return {"sha256": sha(raw), "main_thread_checker_token": mtc[0] if mtc else None}


def setup_accounting(verified, fixture, binding, plan):
    require(verified.get("selector") == PREPARATION
            and verified.get("counts") == {"totalTestCount": 1, "passedTests": 1,
                                           "failedTests": 0, "skippedTests": 0},
            "one_actual_fresh_fixture_setup_required")
    require(all(fixture.get(key) == value for key, value in binding.items()),
            "fresh_setup_binding_differs")
    require(plan == read_plan(), "fresh_setup_requires_exact_retained_preparation")
    return {"purpose": "FRESH_FIXTURE_FOR_PREVIOUSLY_FAILED_UI",
            "original_simulator_state_reused": False,
            "retained_preparation_acceptance": plan["retained_preparation"],
            "actual_setup_method_invocations": 1, "actual_setup_methods_passed": 1,
            "new_preparation_acceptance_credit": 0, "actual_setup_execution": verified}


def startup_observation(value, binding, phase):
    common = {"protocol", "phase", "sourceSHA", "runID", "runAttempt", "nonce",
              "budgetSeconds", "continueTaps", "status", "elapsedSeconds", "admittedElapsedSeconds"}
    expected = common | ({"exactWarningObserved"} if phase == "capture" else set())
    require(phase in {"capture", "reopen"} and isinstance(value, dict) and set(value) == expected,
            "startup_trace_shape_differs")
    require(value["protocol"] == "pinkha-page154-native-startup-warning-v1"
            and value["phase"] == phase and value["status"] == "HOME_READY"
            and value["budgetSeconds"] == 60 and all(value.get(k) == v for k, v in binding.items()),
            "startup_trace_identity_or_outcome_differs")
    admitted, elapsed = value["admittedElapsedSeconds"], value["elapsedSeconds"]
    require(type(admitted) in (int, float) and type(elapsed) in (int, float)
            and math.isfinite(admitted) and math.isfinite(elapsed)
            and 0 <= admitted < 60 and elapsed >= admitted, "late_or_invalid_startup_admission")
    require(type(value["continueTaps"]) is int
            and value["continueTaps"] == (1 if phase == "capture" else 0)
            and (phase != "capture" or value["exactWarningObserved"] is True),
            "real_warning_continue_or_cold_absence_not_proven")
    return value
