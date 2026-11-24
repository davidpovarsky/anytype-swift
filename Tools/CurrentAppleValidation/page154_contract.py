"""One necessary Page154 fixture setup and one unresolved mounted UI journey.

This additive policy never selects tests from the separate current-App profiles.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import plistlib
import re

import contracts as common

PROFILE = "current-page154-mounted"
PREPARATION = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture"
JOURNEY = "PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"
EXCLUDED_FACTORY = "AnytypeTests/SemanticAnchorPage154NativeAcceptanceTests/testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument"
SELECTORS = (PREPARATION, JOURNEY)
STAGES = {"preparation": PREPARATION, "ui": JOURNEY}
FLAGS = [
    "OTHER_SWIFT_FLAGS=$(inherited) -D DEBUG -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 "
    "-D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1",
    "ENABLE_TESTABILITY=YES", "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone",
    "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
    "PROVISIONING_PROFILE_SPECIFIER=",
]
UI_PATH = "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
UI_SHA256 = "711cfe8660bdb315a2b40d85e67a41ba79d846303a93d2a7460c77d8e0cd99a1"
NATIVE_MANIFEST = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
BUNDLE = "io.anytype.app"
APP_NAME = "Anytype.app"
CONFIGURATION = "Debug-Anytype"
UI_TARGET = "PinkhaStage1AcceptanceUITests"
UI_SCHEME = "PinkhaPrebuiltUI"
GENERATED_PROJECT = "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
FIXTURE = "pinkha-semantic-page154-mounted-fixture.json"
CAPTURE = "pinkha-semantic-page154-mounted-capture.json"
REOPEN = "pinkha-semantic-page154-mounted-reopen.json"
require = common.require


def descriptor(raw, selector, products, application, binding, *, fixture=None):
    require(selector in SELECTORS and EXCLUDED_FACTORY not in SELECTORS, "exact_page154_two_stage_policy")
    require(set(binding) == {"sourceSHA", "runID", "runAttempt", "nonce"}
            and re.fullmatch("[0-9a-f]{40}", binding["sourceSHA"])
            and re.fullmatch("[0-9a-f]{32}", binding["nonce"])
            and all(isinstance(binding[k], str) and re.fullmatch("[1-9][0-9]{0,19}", binding[k])
                    and int(binding[k]) < 2**64 for k in ("runID", "runAttempt")),
            "current_page_binding_required")
    products, application = Path(products), Path(application)
    require(products.resolve() == products and application.resolve() == application
            and application.is_dir() and application.name == APP_NAME
            and plistlib.loads(common.read(application / "Info.plist")).get("CFBundleIdentifier") == BUNDLE,
            "current_page_application_required")
    original = plistlib.loads(raw)
    require(isinstance(original, dict), "original_page_descriptor_object")
    value = copy.deepcopy(original)
    blueprint, suite, method = selector.split("/")
    native = selector == PREPARATION
    expected_version = 2 if native else 1
    version = original.get("__xctestrun_metadata__", {}).get("FormatVersion")
    require(type(version) is int and version == expected_version, "page_descriptor_format_changed")
    if native:
        configs = value.get("TestConfigurations")
        require(isinstance(configs, list) and len(configs) == 1
                and configs[0].get("IsEnabled", True) is True, "one_native_page_configuration")
        targets = configs[0].get("TestTargets")
        require(isinstance(targets, list) and all(isinstance(t, dict) for t in targets),
                "native_page_targets_missing")
        matches = [t for t in targets if t.get("BlueprintName") == blueprint]
        require(len(matches) == 1, "one_native_preparation_blueprint")
        target = matches[0]
    else:
        require(set(value) == {"__xctestrun_metadata__", blueprint}, "one_page_ui_blueprint")
        target = value[blueprint]
        require(isinstance(target, dict) and target.get("BlueprintName", blueprint) == blueprint
                and target.get("IsUITestBundle") is True
                and target.get("UseUITargetAppProvidedByTests") is True,
                "previously_observed_explicit_bundle_launch_mode_required")
        def unnamed(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    key = k.replace("_", "").lower()
                    require("testplan" not in key and "testconfiguration" not in key
                            and key != "configurationname", "unexpected_named_ui_plan")
                    unnamed(v)
            elif isinstance(node, list):
                for v in node:
                    unnamed(v)
        unnamed(value)
    require(target.get("IsEnabled", True) is True, "page_target_disabled")
    before = copy.deepcopy(target)
    selected = target.get("OnlyTestIdentifiers", [])
    require(selected in ([], [suite + "/" + method]), "unreviewed_original_page_selection")
    host = common.product_path(target.get("TestHostPath"), products)
    bundle = common.product_path(target.get("TestBundlePath"), products, host)
    require(bundle == host / "PlugIns" / (blueprint + ".xctest"), "actual_page_test_bundle_changed")
    if native:
        require(host == application and fixture is None, "native_preparation_host_or_fixture_changed")
    else:
        require(host.name == UI_TARGET + "-Runner.app" and isinstance(fixture, dict)
                and all(fixture.get(k) == v for k, v in binding.items()), "fresh_page_fixture_or_runner_required")
        require(target.get("DependentProductPaths") == [
            target["TestHostPath"], target["TestHostPath"] + "/PlugIns/" + UI_TARGET + ".xctest"],
            "page_ui_original_dependencies_changed")
        require("UITargetAppPath" not in target and "UITargetAppBundleIdentifier" not in target,
                "page_ui_original_target_mode_changed")
    environment = target.get("EnvironmentVariables", {})
    require(isinstance(environment, dict) and all(isinstance(k, str) and isinstance(v, str)
            for k, v in environment.items()) and not any(k.startswith(("PINKHA_", "TEST_RUNNER_PINKHA_"))
            for k in environment), "stale_page_environment")
    additions = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1",
                 "PINKHA_SEMANTIC_MOUNTED_PREPARE" if native else "PINKHA_SEMANTIC_MOUNTED_TESTING": "1"}
    for k, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"),
                      ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
        additions["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[k]
    if not native:
        encoded = json.dumps(fixture, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        require(len(encoded.encode()) <= 65536, "bounded_page_fixture_required")
        additions["PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON"] = encoded
        target["UITargetAppPath"] = str(application)
    target["EnvironmentVariables"] = environment | additions
    target["OnlyTestIdentifiers"] = [suite + "/" + method]
    if native:
        value["TestConfigurations"][0]["TestTargets"] = [target]
    reverse = copy.deepcopy(target)
    for k in ("EnvironmentVariables", "OnlyTestIdentifiers", "UITargetAppPath"):
        if k in before:
            reverse[k] = before[k]
        else:
            reverse.pop(k, None)
    require(reverse == before, "nonbinding_page_target_mutation")
    inverse = copy.deepcopy(value)
    if native:
        inverse["TestConfigurations"][0]["TestTargets"] = original["TestConfigurations"][0]["TestTargets"]
    else:
        inverse[blueprint] = reverse
    require(inverse == original, "nonbinding_page_descriptor_mutation")
    require(target.get("TestingEnvironmentVariables") == before.get("TestingEnvironmentVariables"),
            "same_job_testing_environment_changed")
    return plistlib.dumps(value, sort_keys=False), {
        "selector": selector, "originalSHA256": common.sha(raw), "formatVersion": expected_version,
        "binding": binding, "environmentKeys": sorted(additions), "exactInverse": True,
        "sameJobTestingEnvironmentUnchanged": True, "runtimeInjectionRelocations": 0,
        "applicationPath": str(application), "testHostPath": str(host), "testBundlePath": str(bundle),
        "freshSetupAcceptanceCredit": 0, "factoryMethodsSelected": 0,
        "enumerationPlan": "AnytypeTests" if native else None,
    }


def attachment(directory, prefix, selector, udid, *, maximum):
    directory = Path(directory)
    manifest = common.strict_json(common.read(directory / "manifest.json", 8 * 1024**2))
    require(isinstance(manifest, list), "page_attachment_manifest_missing")
    matches = []
    for row in manifest:
        for item in row.get("attachments", []):
            name = str(item.get("suggestedHumanReadableName", ""))
            if not name.startswith(prefix + "_"):
                continue
            test = str(row.get("testIdentifier", "")).removeprefix(selector.split("/")[0] + "/").removesuffix("()")
            require(test == "/".join(selector.split("/")[1:])
                    and str(item.get("deviceId", "")).lower() == udid.lower()
                    and item.get("isAssociatedWithFailure") is False, "page_attachment_origin_changed")
            name = item.get("exportedFileName")
            require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
                    "page_attachment_path_escaped")
            path = directory / name
            require(path.resolve() == path, "page_attachment_link")
            raw = common.read(path, maximum)
            matches.append((raw, {"path": str(path), "sha256": common.sha(raw), "bytes": len(raw), "test": test}))
    require(len(matches) == 1, "missing_or_duplicate_page_attachment:" + prefix)
    return matches[0]


def mounted_attachments(directory, udid, capture, reopen, binding, warning):
    result = {}
    for name, expected in (("semantic-anchor-mounted-capture-receipt", capture),
                           ("semantic-anchor-mounted-cold-reopen-receipt", reopen)):
        raw, proof = attachment(directory, name, JOURNEY, udid, maximum=65536)
        value = common.strict_json(raw)
        require(isinstance(value, dict) and value and all(expected.get(k) == v for k, v in value.items()),
                "page_attachment_differs_from_actual_application_receipt")
        result[name] = proof
    for phase in ("capture", "reopen"):
        name = "semantic-anchor-native-startup-" + phase
        raw, proof = attachment(directory, name, JOURNEY, udid, maximum=65536)
        warning.startup_observation(common.strict_json(raw), binding, phase)
        result[name] = proof
    raw, proof = attachment(directory, "semantic-anchor-native-startup-warning-ax", JOURNEY, udid, maximum=2 * 1024**2)
    text = raw.decode("utf-8")
    require(all(s in text for s in ("Warning", "You launch app with a unstable middleware.",
                                  "Continue with current vault", "Logout from current vault")),
            "real_native_startup_warning_not_observed")
    result["warningAX"] = proof
    raw, proof = attachment(directory, "semantic-anchor-native-startup-warning", JOURNEY, udid, maximum=20 * 1024**2)
    require(bool(raw), "real_warning_screenshot_missing")
    result["warningScreenshot"] = proof
    return result
