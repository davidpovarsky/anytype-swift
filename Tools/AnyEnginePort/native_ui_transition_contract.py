#!/usr/bin/env python3
"""Strict composition of a newly built UI runner with the retained original App.

Pure admission/selection helpers: no build, simulator, process or network action.
The old 22 passes and old failed outcomes remain separate from this candidate.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat

PROFILE = "pinkha-native-ui-failed-transition-candidate-v1"
APP_COMMIT = "4b09cc5478c60c1c6728a54f2a27a115637a835b"
TARGET = "PinkhaAnyNativeUITests"
APP_BUNDLE = "io.pinkha.anynative.dev"
SWIFT_SHA = "1d0b0f4a66d4ebfe1af522ef38372525c3ec8c452cc82963fe346e77d0608d72"
HISTORY_SHA = "f104bcd9722dfac94c90c947e4879447f081f2898149809966f0fb4ccea6230b"
PROJECT_HELPER_SHA = "3c666726a42f9e42b481f82e45d90362079c0c0ff062192e4b5c3461ea1f02ec"
ORIGINAL_EXECUTION_HELPER_SHA = "bd8f295934757612e2d5d71bf943f5ef93b3d883936d9bba572c6cfad9370b73"
STAGES = {
    "native-ui-continuation": ("native-ui-continuation-four", 360, (
        "NativeLaunchTests/testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
        "NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen",
        "NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
        "NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen")),
    "archive-roundtrip": ("archive-roundtrip", 1800, (
        "NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies",)),
}
ALL_METHODS = tuple(method for _, _, methods in STAGES.values() for method in methods)
COPY_NAMES = {stage: "Candidate-" + stage + ".xctestrun" for stage in STAGES}


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path, maximum=8 * 1024**2):
    path = Path(path)
    value = path.lstat()
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and value.st_size <= maximum,
            "bounded_single_link_regular_input_required")
    return path.read_bytes()


class host:
    # Scope adapter for the exact already-qualified enumeration function below.
    require = staticmethod(require)


def enumerated_identifiers(payload):
    """Read Xcode's flat JSON; preserve the returned full identifiers verbatim.

    Empty/error/ambiguous/unreviewed output never permits test execution. The
    original JSON is retained for review if a future Xcode changes this schema.
    """
    host.require(isinstance(payload, dict) and payload.get("errors") == [],
                 "Compiled test enumeration reported errors or an unknown schema")
    values = payload.get("values")
    host.require(isinstance(values, list) and len(values) == 1,
                 "Expected one compiled test enumeration configuration")
    value = values[0]
    host.require(isinstance(value, dict) and isinstance(value.get("testPlan"), str),
                 "Compiled test enumeration has no explicit test plan")
    inventories = {}
    for field in ("enabledTests", "disabledTests"):
        entries = value.get(field)
        host.require(isinstance(entries, list), "Unknown compiled " + field + " schema")
        identifiers = []
        for entry in entries:
            identifier = entry.get("identifier") if isinstance(entry, dict) else None
            host.require(isinstance(identifier, str) and identifier and not any(c.isspace() for c in identifier),
                         "Compiled enumeration has a malformed test identifier")
            identifiers.append(identifier)
        host.require(len(identifiers) == len(set(identifiers)), "Compiled enumeration repeats an identifier")
        inventories[field] = set(identifiers)
    host.require(inventories["enabledTests"], "Compiled enumeration selected zero tests")
    host.require(not inventories["enabledTests"].intersection(inventories["disabledTests"]),
                 "Compiled test is both enabled and disabled")
    return value["testPlan"], inventories["enabledTests"], inventories["disabledTests"]


def exact_enumeration(payload, stage):
    require(stage in STAGES, "fixed_failed_stage_required")
    plan, enabled, disabled = enumerated_identifiers(payload)
    def normalized(raw):
        require(raw.startswith(TARGET + "/") and raw.endswith("()")
                and raw.count("/") == 2, "exact_target_plain_xctest_identifier_required")
        return raw[:-2]
    selected = {TARGET + "/" + name for name in STAGES[stage][2]}
    actual = {normalized(raw) for raw in enabled}
    excluded = {normalized(raw) for raw in disabled}
    require(len(actual) == len(enabled) and len(excluded) == len(disabled)
            and actual == selected and not actual.intersection(excluded),
            "exact_enabled_method_inventory_required")
    return {"observedPlanLabel": plan, "planIdentityPolicy": "unnamed_v1_single_ui_target_observed_label",
            "enabledOriginalIdentifiers": sorted(enabled), "disabledOriginalIdentifiers": sorted(disabled),
            "expectedMethods": sorted(selected), "errors": [], "testsExecuted": 0}


def product_path(raw, products, *, host_path=None):
    require(isinstance(raw, str) and raw and "\0" not in raw and "\\" not in raw,
            "explicit_product_path_required")
    if raw.startswith("__TESTROOT__/"):
        tail = raw[len("__TESTROOT__/"):]
        base = products
    elif raw.startswith("__TESTHOST__/") and host_path is not None:
        tail = raw[len("__TESTHOST__/"):]
        base = host_path
    else:
        raise ValueError("unadmitted_product_path_macro_or_absolute_path")
    pieces = PurePosixPath(tail).parts
    require(pieces and all(part not in ("", ".", "..") for part in pieces)
            and "__" not in tail, "product_path_escape_or_unknown_macro")
    path = base.joinpath(*pieces)
    require(path.absolute() == path.resolve() and path.is_relative_to(products),
            "product_path_outside_new_runner_products")
    return path


def descriptor_bytes(original, *, products, original_app, stage):
    require(stage in STAGES and products.is_absolute() and original_app.is_absolute(),
            "fixed_composition_paths_required")
    require(products.resolve() == products and original_app.resolve() == original_app
            and not original_app.is_relative_to(products) and not products.is_relative_to(original_app),
            "original_app_and_new_runner_products_must_be_disjoint")
    value = plistlib.loads(original)
    require(isinstance(value, dict) and set(value) == {"__xctestrun_metadata__", TARGET}
            and isinstance(value["__xctestrun_metadata__"], dict)
            and type(value["__xctestrun_metadata__"].get("FormatVersion")) is int
            and value["__xctestrun_metadata__"]["FormatVersion"] == 1,
            "single_ui_target_v1_descriptor_required")
    target = value[TARGET]
    require(isinstance(target, dict) and target.get("IsUITestBundle") is True
            and not any(key in owner for owner in (target, value["__xctestrun_metadata__"])
                        for key in ("TestPlans", "TestConfigurations", "TestPlanName")),
            "unnamed_ui_target_descriptor_required")
    host_path = product_path(target.get("TestHostPath"), products)
    test_path = product_path(target.get("TestBundlePath"), products, host_path=host_path)
    require(host_path.name == TARGET + "-Runner.app"
            and test_path == host_path / "PlugIns" / (TARGET + ".xctest"),
            "exact_generated_ui_runner_and_test_bundle_required")
    require(isinstance(target.get("DependentProductPaths", []), list), "typed_dependent_products_required")
    for raw in target.get("DependentProductPaths", []):
        dependency = product_path(raw, products, host_path=host_path)
        require(dependency == host_path or dependency == test_path
                or dependency.is_relative_to(host_path), "foreign_dependent_product_forbidden")
    require(isinstance(target.get("DependentProductPaths", []), list)
            and target.get("SkipTestIdentifiers", []) == [], "unadmitted_descriptor_filter")
    existing = target.get("OnlyTestIdentifiers", [])
    require(isinstance(existing, list) and (existing == [] or
            (len(existing) == len(ALL_METHODS) and set(existing) == set(ALL_METHODS))),
            "unadmitted_original_only_test_filter")
    require(target.get("UITargetAppPath", "") == ""
            and target.get("UITargetAppBundleIdentifier", "") == "",
            "generated_descriptor_must_not_bind_an_application")
    result = copy.deepcopy(value)
    result[TARGET]["UITargetAppPath"] = str(original_app)
    result[TARGET]["UITargetAppBundleIdentifier"] = APP_BUNDLE
    result[TARGET]["OnlyTestIdentifiers"] = list(STAGES[stage][2])
    inverse = copy.deepcopy(result)
    for key in ("UITargetAppPath", "UITargetAppBundleIdentifier", "OnlyTestIdentifiers"):
        if key in target:
            inverse[TARGET][key] = target[key]
        else:
            inverse[TARGET].pop(key)
    require(inverse == value, "descriptor_contains_noncomposition_delta")
    return plistlib.dumps(result, sort_keys=False), {
        "originalSHA256": sha(original), "originalFormatVersion": 1, "blueprint": TARGET,
        "testHostPath": str(host_path), "testBundlePath": str(test_path),
        "originalApplicationPath": str(original_app), "originalApplicationCommit": APP_COMMIT,
        "changedFields": ["UITargetAppPath", "UITargetAppBundleIdentifier", "OnlyTestIdentifiers"],
        "exactInverse": True, "methods": list(STAGES[stage][2]),
    }


def command(stage, descriptor, udid, result):
    require(stage in STAGES and re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", udid),
            "fixed_stage_and_owned_uuid_required")
    profile, allowance, methods = STAGES[stage]
    argv = ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
            "-destination", "platform=iOS Simulator,id=" + udid,
            "-parallel-testing-enabled", "NO", "-test-timeouts-enabled", "YES",
            "-default-test-execution-time-allowance", str(allowance),
            "-maximum-test-execution-time-allowance", str(allowance)]
    for method in methods:
        argv += ["-only-testing:" + TARGET + "/" + method]
    argv += ["-resultBundlePath", str(result), "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-"]
    return {"stage": stage, "profile": profile, "methods": list(methods), "command": argv,
            "applicationBuilds": 0, "nativeLibraryBuilds": 0, "runnerOrigin": "CURRENT_UI_ONLY_BUILD"}


def enumeration_command(plan, output):
    argv = list(plan["command"])
    i = argv.index("-resultBundlePath")
    del argv[i:i+2]
    argv += ["-enumerate-tests", "-test-enumeration-style", "flat",
             "-test-enumeration-format", "json", "-test-enumeration-output-path", str(output)]
    require([value for value in argv if value.startswith("-only-testing:")]
            == ["-only-testing:" + TARGET + "/" + method for method in plan["methods"]],
            "enumeration_execution_selector_divergence")
    return argv


def partial_named(tree, parser):
    cases = parser(tree)
    return {"actualNamedCases": cases,
            "actualNamedPasses": sorted(name for name, outcome in cases.items() if outcome == "Passed"),
            "actualNamedNonpasses": {name: outcome for name, outcome in cases.items() if outcome != "Passed"},
            "completeStageAcceptance": False, "namedOutcomesAreObservedOnly": True}


def finish_outcome(primary_error, evidence_errors, result, *, validate):
    """Preserve the first actual failure; successful later diagnostics cannot replace it."""
    if primary_error is not None:
        result["status"] = "FAIL"
        result.setdefault("firstFailure", {"type": type(primary_error).__name__, "message": str(primary_error)})
        result["diagnosticFailures"] = evidence_errors
        return result, primary_error
    if evidence_errors:
        result["status"] = "FAIL"
        result["diagnosticFailures"] = evidence_errors
        return result, RuntimeError("required_original_result_evidence_incomplete")
    try:
        result["validation"] = validate()
        result["status"] = "PASS"
        result["completeStageAcceptance"] = True
        return result, None
    except BaseException as error:
        result["status"] = "FAIL"
        result["validationFailure"] = {"type": type(error).__name__, "message": str(error)}
        return result, error
