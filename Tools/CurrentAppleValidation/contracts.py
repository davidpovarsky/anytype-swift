"""Fixed, opt-in current-App selections. No historical pass is a current result."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat

BASE = "7c506bb52c9e211e84de5feeaca549d315b2855d"
REPOSITORY = "davidpovarsky/anytype-swift"
SOURCE_DRAG = "NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens"
RETURN = (
    "BlockActionServiceReturnFocusTests/renderedSubscriberKeepsSplitRequest",
    "BlockActionServiceReturnFocusTests/laterRenderedRowConsumesSplitRequest",
    "BlockActionServiceReturnFocusTests/laterRequestStillSupersedesSplitFocus",
)
PREPARATION = ("PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",)
UI_THREE = (
    "NativeLaunchTests/testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
    "NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen",
    "NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen",
)
ARCHIVE = ("NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies",)
CUSTOM_TYPE = ("NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen",)
HISTORY = ("NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen",)
PROFILES = {
    "release-return-rtl": {
        "project": "Anytype.xcodeproj", "scheme": "Anytype", "configuration": "Release-Anytype",
        "target": "AnytypeTests", "app": "Anytype.app", "bundle": "io.anytype.app",
        "format": 2, "testPlan": "AnytypeTests",
        "runtime": "com.apple.CoreSimulator.SimRuntime.iOS-27-0", "version": "27.0", "build": "24A434",
        "device": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB",
        "stages": {"return-controls": (RETURN, 360), "preparation": (PREPARATION, 300)},
        "flags": ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1",
                  "ENABLE_TESTABILITY=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone"],
        "nativeBuilds": 0, "applicationBuilds": 1, "uiRunnerBuilds": 0,
    },
    "native-ui-failed": {
        "project": "NativeApp/AnyNative.xcodeproj", "scheme": "PinkhaAnyNativeApp", "configuration": "Debug",
        "target": "PinkhaAnyNativeUITests", "app": "PinkhaAnyNative.app", "bundle": "io.pinkha.anynative.dev",
        "format": 1, "testPlan": None,
        "runtime": "com.apple.CoreSimulator.SimRuntime.iOS-27-2", "version": "27.2", "build": "24B8117",
        "device": "com.apple.CoreSimulator.SimDeviceType.iPad-mini-A17-Pro",
        "stages": {"native-ui-three": (UI_THREE, 360), "archive-roundtrip": (ARCHIVE, 1800),
                   "custom-type": (CUSTOM_TYPE, 360), "native-history": (HISTORY, 1800)},
        "flags": [], "nativeBuilds": 0, "applicationBuilds": 1, "uiRunnerBuilds": 1,
    },
}
COMMON_FLAGS = ["ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
                "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-", "PROVISIONING_PROFILE_SPECIFIER="]
HEART = {
    "run": "45091223011", "source": "8b08033135f7cb508e813ab1d47d81c255037c07",
    "profile": "r15-attachment-authorized-current-read-v1",
    "patch": "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00",
    "inventory": "05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0",
    "originalBuildRun": "45035194823",
    "originalBuildReceipt": "f924c22b612bf456fafd754f66152905110e0e6556bf1b6f858dc09e2a6cc9a0",
    "sourceCount": 139,
}
ANY = {
    "run": "44695105165", "source": "31ae2e63890b6e10af8413625534f6234ed263bb",
    "artifactName": "any-pinkha-native-xcframework-31ae2e63890b6e10af8413625534f6234ed263bb",
    "receipt": "190cc5f18507f4e3ef5db57e0252f37d10184c0281752ad75b34388bf33e3ec2",
    "archive": "0c8933d9b8d6e290dff0577cac3450c1a32fad0a24ebdf7e353c00f333a6811e",
    "manifest": "15906eb27afea68cc7ec99242bffd6a8ea69517edb608a4421cce90c9a99a070",
    "version": "v0.5.0-pinkha.1",
}
HANLIN = "6bd6036dbca16c969689a5722550a54bebc1e851"

def require(value, reason):
    if not value:
        raise ValueError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_json")))

def read(path, limit=8 * 1024**2):
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "bounded_regular_input_required")
    raw = path.read_bytes()
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and len(raw) == before.st_size, "input_changed_while_reading")
    return raw

def methods(profile):
    value = tuple(method for names, _ in PROFILES[profile]["stages"].values() for method in names)
    count = {"release-return-rtl": 4, "native-ui-failed": 6}[profile]
    require(len(value) == len(set(value)) == count and SOURCE_DRAG not in value, "fixed_named_selection_changed")
    return value

def selected_identifiers(profile, stage=None):
    spec = PROFILES[profile]
    names = methods(profile) if stage is None else spec["stages"][stage][0]
    # Swift Testing's compiled identifiers include the empty argument list.
    # The retained F inventory proved that unsuffixed filters select zero tests.
    return [name + "()" if profile == "release-return-rtl" else name for name in names]

def selectors(profile, stage=None):
    return ["-only-testing:" + PROFILES[profile]["target"] + "/" + name
            for name in selected_identifiers(profile, stage)]

def product_path(raw, products, host=None):
    require(isinstance(raw, str) and raw and "\\" not in raw and "\0" not in raw, "product_path_required")
    if raw.startswith("__TESTROOT__/"):
        base, tail = products, raw[len("__TESTROOT__/"):]
    elif raw.startswith("__TESTHOST__/") and host is not None:
        base, tail = host, raw[len("__TESTHOST__/"):]
    else:
        raise ValueError("unreviewed_product_path_macro")
    require(all(part not in ("", ".", "..") for part in tail.split("/")) and "__" not in tail,
            "product_path_escape")
    result = base.joinpath(*PurePosixPath(tail).parts)
    require(result.resolve() == result and result.is_relative_to(products) and result.is_dir(),
            "actual_product_missing_or_outside_current_products")
    return result

def scope_descriptor(raw, profile, stage, products):
    spec = PROFILES[profile]
    require(stage in spec["stages"], "undeclared_stage")
    value = plistlib.loads(raw)
    require(isinstance(value, dict) and value.get("__xctestrun_metadata__", {}).get("FormatVersion")
            == spec["format"], "unexpected_original_descriptor_format")
    result = copy.deepcopy(value)
    if spec["format"] == 2:
        configurations = value.get("TestConfigurations")
        require(isinstance(configurations, list) and len(configurations) == 1
                and configurations[0].get("IsEnabled", True) is True, "single_enabled_configuration_required")
        targets = configurations[0].get("TestTargets")
        require(isinstance(targets, list) and all(isinstance(x, dict) for x in targets),
                "invalid_native_target_list")
        selected = [target for target in targets if target.get("BlueprintName") == spec["target"]]
        require(len(selected) == 1, "exact_native_test_blueprint_required")
        target = selected[0]
        copied = copy.deepcopy(target)
        result["TestConfigurations"][0]["TestTargets"] = [copied]
    else:
        require(set(value) == {"__xctestrun_metadata__", spec["target"]}, "single_ui_target_required")
        target, copied = value[spec["target"]], result[spec["target"]]
        require(target.get("IsUITestBundle") is True and
                not any(key in owner for owner in (target, value["__xctestrun_metadata__"])
                        for key in ("TestPlans", "TestConfigurations", "TestPlanName")),
                "unnamed_single_ui_descriptor_required")
    require(target.get("IsEnabled", True) is True, "selected_target_disabled")
    existing = target.get("OnlyTestIdentifiers", [])
    allowed_original_selections = [set(methods(profile)), set(selected_identifiers(profile))]
    require(isinstance(existing, list) and (not existing or
            len(existing) == len(methods(profile)) and set(existing) in allowed_original_selections),
            "original_descriptor_has_unreviewed_selection")
    host = product_path(target.get("TestHostPath"), products)
    bundle = product_path(target.get("TestBundlePath"), products, host)
    require(bundle.name == spec["target"] + ".xctest" and bundle == host / "PlugIns" / bundle.name,
            "actual_test_bundle_path_mismatch")
    application = products / (spec["configuration"] + "-iphonesimulator") / spec["app"]
    require(application.is_dir() and application.resolve() == application, "current_application_missing")
    if spec["format"] == 2:
        require(host == application, "native_host_is_not_current_application")
    else:
        require(host.name == spec["target"] + "-Runner.app"
                and target.get("UseUITargetAppProvidedByTests", False) is False,
                "generated_ui_runner_must_have_explicit_current_target")
        require(product_path(target.get("UITargetAppPath"), products) == application
                and target.get("UITargetAppBundleIdentifier", spec["bundle"]) == spec["bundle"],
                "ui_application_target_differs_from_current_build")
    copied["OnlyTestIdentifiers"] = selected_identifiers(profile, stage)
    # Only selection changes. App, runner, language, locale, environment, MTC and skip filters stay exact.
    inverse = copy.deepcopy(result)
    if spec["format"] == 2:
        inverse["TestConfigurations"][0]["TestTargets"] = copy.deepcopy(targets)
    elif "OnlyTestIdentifiers" in target:
        inverse[spec["target"]]["OnlyTestIdentifiers"] = target["OnlyTestIdentifiers"]
    else:
        inverse[spec["target"]].pop("OnlyTestIdentifiers")
    require(inverse == value, "nonselection_descriptor_mutation")
    return plistlib.dumps(result, sort_keys=False), {
        "originalSHA256": sha(raw), "format": spec["format"], "target": spec["target"],
        "applicationPath": str(application), "testHostPath": str(host), "testBundlePath": str(bundle),
        "selection": selected_identifiers(profile, stage), "exactInverse": True,
        "language": target.get("TestLanguage"), "region": target.get("TestRegion"),
        "skipTestIdentifiers": target.get("SkipTestIdentifiers", []),
    }

def test_command(profile, stage, descriptor, udid, result):
    spec = PROFILES[profile]
    require(re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", udid),
            "exact_owned_uuid_required")
    allowance = spec["stages"][stage][1]
    return ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
            "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", str(allowance),
            "-maximum-test-execution-time-allowance", str(allowance),
            *selectors(profile, stage), "-resultBundlePath", str(result), *COMMON_FLAGS]

def enumeration_command(argv, output):
    result = list(argv)
    i = result.index("-resultBundlePath")
    del result[i:i+2]
    result += ["-enumerate-tests", "-test-enumeration-style", "flat",
               "-test-enumeration-format", "json", "-test-enumeration-output-path", str(output)]
    require([x for x in result if x.startswith("-only-testing:")] ==
            [x for x in argv if x.startswith("-only-testing:")], "enumeration_selection_diverged")
    return result

def validate_enumeration(payload, profile, stage, parser):
    plan, enabled, disabled = parser(payload)
    spec = PROFILES[profile]
    expected = {spec["target"] + "/" + name + "()" for name in spec["stages"][stage][0]}
    require(enabled == expected, "compiled_selection_not_exact")
    require(not enabled.intersection(disabled), "enabled_disabled_overlap")
    if spec["testPlan"] is not None:
        require(plan == spec["testPlan"], "actual_test_plan_changed")
    return {"enabled": sorted(enabled), "disabledCount": len(disabled), "observedTestPlan": plan}

def validate_results(summary, tree, profile, stage, udid, parser):
    spec = PROFILES[profile]
    names = set(spec["stages"][stage][0])
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(v) is int for v in counts.values()) and counts["totalTestCount"] == len(names)
            and counts["passedTests"] == len(names) and counts["failedTests"] == counts["skippedTests"] == 0,
            "current_named_results_incomplete_or_failed")
    configurations = summary.get("devicesAndConfigurations")
    require(isinstance(configurations, list) and len(configurations) == 1, "one_actual_destination_required")
    device = configurations[0].get("device", {})
    require(device.get("deviceId", "").upper() == udid and device.get("osVersion") == spec["version"]
            and device.get("osBuildNumber") == spec["build"] and device.get("architecture") == "arm64",
            "actual_destination_does_not_match_owned_pair")
    cases = parser(tree)
    require(len(cases) == len(names) and all(v == "Passed" for v in cases.values()), "named_cases_not_exact")
    observed = set()
    for identifier in cases:
        matches = [name for name in names if identifier in (name, name + "()", spec["target"] + "/" + name,
                                                             spec["target"] + "/" + name + "()")]
        require(len(matches) == 1 and matches[0] not in observed, "foreign_or_duplicate_test_case")
        observed.add(matches[0])
    require(observed == names and SOURCE_DRAG not in observed, "retained_or_missing_method")
    return {"counts": counts, "actualCases": cases, "methods": sorted(observed), "device": device}
