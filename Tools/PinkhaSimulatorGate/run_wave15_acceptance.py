"""Run existing Wave-15 UI suites on one fresh OS27 configuration.

A lane result is evidence for its named methods, not full-matrix or release
acceptance. The main controller runs a successful Home/document smoke first.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess
import sys
import time

import run_ui27 as shared
import hanlin_acceptance_evidence as hanlin
import hanlin_ui_runtime
import hanlin_selection_evidence as hanlin_selection
import wave15_diagnostics as diagnostics
import type_preservation as preservation
import text_native_ack
import shared_editor_existing_build

BRANCH = "codex/chatgpt-wave15-integration-20261118"
CONSUMER_BRANCH = "codex/chatgpt-wave15-hanlin-consumer-20261119"
UI_RESUME_BRANCH = "codex/chatgpt-wave15-ui-resume-20261119"
SHARED_BRANCH = "codex/chatgpt-wave15-shared-20261121"
APPROVED_BRANCHES = (BRANCH, CONSUMER_BRANCH, UI_RESUME_BRANCH, SHARED_BRANCH)
EDITOR_DEVICE_PREFERENCES_TIMEOUT_SECONDS = 120
LANES = {
    "hanlin-selection": {
        "suite": "HanlinSelectionAcceptanceUITests",
        "methods": ["testRealSelectedBlockReadAndReturn"],
        "preparation": "HanlinSelectionAcceptancePreparationTests/prepareSelectedBlockFixture",
        "preparation_environment": {"PINKHA_PREPARE_HANLIN_SELECTION_UI": "1",
            "PINKHA_HANLIN_NATIVE_PREPARATION": "1", "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1",
            "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-hanlin-selection-fixture.json",
    },
    "hanlin-native": {
        "suite": "HanlinNativeAcceptanceUITests",
        "methods": ["testRealNativeConsentCreatePageAndAuthorityRevocation"],
        "preparation": "HanlinNativeAcceptancePreparationTests/prepareRealHostFixture",
        "preparation_environment": {"PINKHA_HANLIN_NATIVE_PREPARATION": "1",
            "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-hanlin-native-fixture.json",
    },
    "quote-drop": {
        "suite": "PinkhaTorahQuoteAcceptanceUITests",
        "methods": ["testNativeQuoteUndoRedoDragAndRelaunch"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "preparation_environment": {"PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "inspector-search": {
        "suite": "AnytypeComprehensiveAcceptanceUITests",
        "methods": ["testInspectorEmbeddedSearchOpenReturnAndDocumentLink"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "preparation_environment": {"PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "inspector": {
        "suite": "AnytypeComprehensiveAcceptanceUITests",
        "methods": shared.SMOKE + ["testDocumentSourceSearchEmptyAndClear", "testInspectorShowsIndexedRelatedDocument"],
        "preparation": "SimulatorAcceptancePreparationTests/prepareRealUIFixture",
        "preparation_environment": {"PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
        "fixture": "pinkha-simulator-ui27-fixture.json",
    },
    "properties": {
        "suite": "PinkhaNativeDerivedAcceptanceUITests",
        "methods": ["testNativePropertiesPickerChipsSetMembershipAndRelaunch", "testSourceHeaderSelectionAndOverflow",
                    "testUniversalPageNoteCustomPropertiesAndMixedSet"],
        "preparation": "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
        "preparation_environment": {"PINKHA_NATIVE_DERIVED_ACCEPTANCE": "1"},
        "fixture": "pinkha-native-derived-ui-fixture.json",
    },
    # The historical Set-resume methods require untouched universal blank
    # fixtures. Their separate job creates a fresh native fixture; execution order
    # must never determine whether a method passes.
    "properties-set": {
        "suite": "PinkhaNativeDerivedAcceptanceUITests",
        "methods": ["testRemainingNativeSourceFilterEditing", "testRemainingUniversalTypePickersAndMixedSet"],
        "preparation": "TorahNativeDerivedProductIntegrationTests/originalProductPipeline",
        "preparation_environment": {"PINKHA_NATIVE_DERIVED_ACCEPTANCE": "1"},
        "fixture": "pinkha-native-derived-ui-fixture.json",
    },
    "editor": {
        "suite": "PinkhaStage1AcceptanceUITests",
        "methods": ["testAppWideDirectionPersistenceAndInteractiveBack", "testMultiBlockEnterCreationAndTypingLifecycle",
                    "testDocumentSourcesEntryOpensExistingSearch"],
        "preparation": "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
        "preparation_environment": {},
        "fixture": "pinkha-stage1-acceptance-state.json",
    },

    "canonical-properties": {
        "suite": "PinkhaTorahPropertiesAcceptanceUITests",
        "methods": ["testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes"],
        "preparation": "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState",
        "preparation_environment": {"PINKHA_PROPERTIES_PREPARE": "1"},
        "fixture": "pinkha-stage1-acceptance-state.json",
    },
}


HANLIN_LANES = {
    "hanlin-native": (hanlin, "pinkha-hanlin-native-result.json", "hanlin-native-result.json", "hanlin_native_receipt"),
    "hanlin-selection": (hanlin_selection, "pinkha-hanlin-selection-result.json",
                         "hanlin-selection-result.json", "hanlin_selection_receipt"),
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def require_source_identity(head, expected_sha, branch, ref):
    require(branch in APPROVED_BRANCHES and ref == "refs/heads/" + branch,
            "Actual integration source branch differs")
    require(re.fullmatch(r"[0-9a-f]{40}", expected_sha or "") and head == expected_sha,
            "Actual integration source SHA differs")


def plan(lane, device, language):
    require(lane in LANES, "Unknown acceptance lane")
    require(device in {"iphone", "ipad"} and language in {"en", "he"}, "Unknown actual configuration")
    require(lane == "editor" or language == "en",
            "Existing non-editor methods use English labels; do not report them as Hebrew acceptance")
    spec = LANES[lane]
    methods = [spec["suite"] + "/" + name for name in spec["methods"]]
    require(methods and len(methods) == len(set(methods)), "Empty or duplicate named UI selection")
    return dict(lane=lane, device_family=device, app_language=language,
                build_configuration="Debug-Anytype" if lane in HANLIN_LANES else "Release-Anytype",
                configuration_id=device + "-" + language + "-portrait-os27",
                methods=methods, expected_ui_executions=len(methods),
                preparation=spec["preparation"], expected_preparation_executions=1,
                postflight=preservation.METHOD if lane == "properties-set" else None,
                expected_postflight_executions=1 if lane == "properties-set" else 0,
                release_accepted=False, full_matrix_accepted=False,
                device_language_verified=False)


def preparation_environment(lane, source_sha, run_id, run_attempt):
    environment = dict(LANES[lane]["preparation_environment"])
    if lane in HANLIN_LANES:
        environment.update(PINKHA_HANLIN_NATIVE_SOURCE_SHA=source_sha,
            PINKHA_HANLIN_NATIVE_RUN_ID=run_id, PINKHA_HANLIN_NATIVE_RUN_ATTEMPT=run_attempt)
    if lane == "hanlin-selection":
        environment.update(PINKHA_HANLIN_SELECTION_SOURCE_SHA=source_sha,
            PINKHA_HANLIN_SELECTION_RUN_ID=run_id, PINKHA_HANLIN_SELECTION_RUN_ATTEMPT=run_attempt)
    return environment


def nonempty(value, name):
    require(isinstance(value, str) and bool(value.strip()), "Missing actual fixture " + name)
    return value


def fixture_environment(lane, value, language, observed_device_language=None):
    nonempty(value.get("spaceId"), "Space")
    if lane in {"inspector", "inspector-search", "quote-drop", "properties", "properties-set"}:
        docs = value.get("universalDocuments", {})
        page = nonempty(docs.get("page"), "Page")
        source = nonempty(value.get("manySourcesDocument"), "source document")
        require(page != source, "Page and source document must be distinct")
        if lane in {"properties", "properties-set"}:
            writing = value.get("documents", {})
            require(len(writing) == 3 and len(set(writing.values())) == 3
                    and all(isinstance(v, str) and v for v in writing.values()), "Missing distinct writing-type documents")
            nonempty(value.get("setId"), "native Set")
            nonempty(value.get("universalSetId"), "mixed Set")
            validate_source_header_cases(value)
            validate_type_switch_fixture(value)
        return {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_NATIVE_UI_FIXTURE_JSON": json.dumps(value)}
    ids = [nonempty(value.get(key), key) for key in ("pinkhaObjectId", "noteObjectId", "pageObjectId")]
    require(len(set(ids)) == 3, "Editor fixtures must be three distinct native objects")
    if lane == "editor":
        require(observed_device_language in {"en", "he"} and observed_device_language != language,
                "Actual opposite device language must be verified before creating the editor environment")
    return {
        "PINKHA_ACCEPTANCE_SPACE_ID": value["spaceId"],
        "PINKHA_ACCEPTANCE_PINKHA_ID": ids[0],
        "PINKHA_ACCEPTANCE_NOTE_ID": ids[1],
        "PINKHA_ACCEPTANCE_PAGE_ID": ids[2],
        "PINKHA_ACCEPTANCE_DIRECTION": "rtl" if language == "he" else "ltr",
        "PINKHA_ACCEPTANCE_DEVICE_LANGUAGE": observed_device_language or "",
    }


def validate_source_header_cases(value):
    """Only the four independently prepared native header fixtures are valid."""
    cases = value.get("sourceHeaderCases")
    require(isinstance(cases, list) and len(cases) == 4,
            "Source header fixture must contain exactly four cases")
    object_ids = []
    for case, count in zip(cases, [0, 1, 2, 12]):
        require(isinstance(case, dict) and set(case) == {"count", "objectId", "labels"},
                "Source header fixture has an unknown record schema")
        require(type(case["count"]) is int and case["count"] == count,
                "Source header fixture must declare the exact ordered 0/1/2/12 counts")
        require(case["labels"] == ["Genesis 2:" + str(index) for index in range(1, count + 1)],
                "Source header labels differ from the independently seeded native references")
        object_ids.append(nonempty(case["objectId"], "source header object"))
    require(len(set(object_ids)) == 4, "Source header cases reused an object")
    require(object_ids[-1] == value["manySourcesDocument"],
            "Source header twelve-source object differs from the native fixture")
    reserved = {value["setId"], value["universalSetId"]}
    for key in ["documents", "universalDocuments", "types", "universalTypes"]:
        mapping = value.get(key, {})
        require(isinstance(mapping, dict), "Source header isolation requires native fixture mappings")
        require(all(isinstance(item, str) and item for item in mapping.values()),
                "Source header isolation has an invalid native object identity")
        reserved.update(mapping.values())
    require(set(object_ids).isdisjoint(reserved),
            "Source header fixture reused a writing, universal, Type or Set object")


def validate_type_switch_fixture(value):
    """Bind the independent UI Type-switch target to its real native readback."""
    target = value.get("typeSwitch")
    require(isinstance(target, dict) and set(target) == {
        "schemaVersion", "objectId", "spaceId", "name", "initialTypeId", "types", "values", "nativeReadback"
    }, "Type-switch fixture has an unknown schema")
    require(type(target["schemaVersion"]) is int and target["schemaVersion"] == 1,
            "Type-switch fixture version differs")
    object_id = nonempty(target["objectId"], "Type-switch object")
    require(target["spaceId"] == value["spaceId"], "Type-switch fixture belongs to another Space")
    require(target["name"] == "Native Type-switch preserved properties", "Type-switch fixture name differs")
    reserved = {value["setId"], value["universalSetId"], value["manySourcesDocument"]}
    reserved.update(case["objectId"] for case in value["sourceHeaderCases"])
    for key in ["documents", "universalDocuments", "types", "universalTypes"]:
        reserved.update(value[key].values())
    require(object_id not in reserved, "Type-switch reused a writing, header, universal, Type or Set object")
    roles = {"chiddush", "article", "research"}
    types = target["types"]
    require(isinstance(types, dict) and set(types) == roles and set(value["types"]) == roles,
            "Type-switch must bind all three writing Types")
    type_ids, type_labels = [], []
    for role, choice in types.items():
        require(isinstance(choice, dict) and set(choice) == {
            "id", "label", "propertyName", "sectionId", "sectionTitle", "sectionExpandable"
        }, "Type-switch choice has an unknown schema")
        require(choice["id"] == value["types"][role], "Type-switch choice differs from the native registered Type")
        type_ids.append(nonempty(choice["id"], "Type-switch Type identity"))
        type_labels.append(nonempty(choice["label"], "Type-switch Type label"))
        nonempty(choice["propertyName"], "Type-switch native Type property name")
        nonempty(choice["sectionId"], "Type-switch native section identity")
        require(type(choice["sectionExpandable"]) is bool and isinstance(choice["sectionTitle"], str),
                "Type-switch section observation is invalid")
        if choice["sectionExpandable"]:
            nonempty(choice["sectionTitle"], "Type-switch expandable section title")
    require(len(set(type_ids)) == 3 and len(set(type_labels)) == 3,
            "Type-switch writing Type identities or labels are ambiguous")
    require(target["initialTypeId"] == types["chiddush"]["id"], "Type-switch did not start as Chiddush")
    expected = [
        ("ref", "Genesis 3:1", "Genesis 3:1", "מקור/ות"),
        ("topic", "creation", "Creation", "נושא"),
        ("word", "בראשית", "בראשית", "מילה / ערך"),
    ]
    values = target["values"]
    require(isinstance(values, list) and len(values) == 3, "Type-switch requires three native values")
    projection, identities = {}, []
    for record, (kind, canonical, label, name) in zip(values, expected):
        require(isinstance(record, dict) and set(record) == {
            "kind", "canonicalKey", "propertyKey", "propertyName", "identity", "label"
        }, "Type-switch value has an unknown schema")
        require((record["kind"], record["canonicalKey"], record["label"], record["propertyName"]) ==
                (kind, canonical, label, name), "Type-switch native value differs from its independently seeded association")
        key = nonempty(record["propertyKey"], "Type-switch native property key")
        identity = nonempty(record["identity"], "Type-switch canonical identity")
        require(key not in projection, "Type-switch reused a native property key")
        projection[key] = [identity]
        identities.append(identity)
    require(len(set(identities)) == 3, "Type-switch reused a canonical identity")
    readback = target["nativeReadback"]
    require(isinstance(readback, dict) and set(readback) == {
        "method", "objectId", "spaceId", "typeId", "canonicalNonempty", "projections"
    }, "Type-switch native readback has an unknown schema")
    require(readback["method"] == "ObjectShow" and readback["objectId"] == object_id and
            readback["spaceId"] == value["spaceId"] and readback["typeId"] == target["initialTypeId"] and
            readback["canonicalNonempty"] is True and readback["projections"] == projection,
            "Type-switch native readback is missing, foreign or differs from the seeded values")


def property_environment(preparation, expected_space):
    marker = "PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON "
    observed = {}
    for path in sorted(preparation.glob("command-*.log")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if marker in line:
                value = json.loads(line.split(marker, 1)[1].strip())
                observed[json.dumps(value, sort_keys=True)] = value
    require(len(observed) == 1, "Expected one actual native property fixture")
    value = next(iter(observed.values()))
    require(value.get("PINKHA_PROPERTIES_SPACE_ID") == expected_space, "Property fixture belongs to another Space")
    require(value.get("PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED") == "1", "Disposable property fixture confirmation missing")
    ids = [nonempty(value.get("PINKHA_PROPERTIES_" + role + "_ID"), role) for role in ("CHIDDUSH", "ARTICLE", "RESEARCH")]
    require(len(set(ids)) == 3, "Property documents must be distinct")
    labels = json.loads(nonempty(value.get("PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS"), "native property labels"))
    require(all(isinstance(labels.get(i), list) and labels[i] for i in ids), "Native original property labels missing")
    value.update(PINKHA_PROPERTIES_SOURCE_QUERY="Genesis 1:1", PINKHA_PROPERTIES_SOURCE_LABEL="Genesis 1:1",
                 PINKHA_PROPERTIES_TOPIC_QUERY="Creation", PINKHA_PROPERTIES_TOPIC_LABEL="Creation")
    return value


def validate_device_language(preferences, app_language):
    """Verify the actual disposable simulator globals independently of UI labels."""
    require(app_language in {"en", "he"}, "Unsupported editor app language")
    require(isinstance(preferences, bytes) and 0 < len(preferences) <= 1024 * 1024,
            "Missing or oversized simulator language preferences")
    try:
        value = plistlib.loads(preferences)
    except Exception as error:
        raise ValueError("Simulator globals are not a valid property list") from error
    require(isinstance(value, dict), "Simulator globals must be a dictionary")
    languages, locale = value.get("AppleLanguages"), value.get("AppleLocale")
    require(isinstance(languages, list) and languages
            and all(isinstance(item, str) and item for item in languages),
            "Actual simulator AppleLanguages are missing")
    actual = languages[0].replace("_", "-").split("-", 1)[0].lower()
    expected = "en" if app_language == "he" else "he"
    expected_locale = "en_US" if expected == "en" else "he_IL"
    require(actual == expected and actual != app_language,
            "Actual simulator language does not differ from the app language")
    require(locale == expected_locale, "Actual simulator locale differs from the configured locale")
    return dict(status="DEVICE_LANGUAGE_PREFERENCES_VERIFIED", device_language=actual,
                app_language=app_language, observed_languages=languages, observed_locale=locale,
                preferences_sha256=hashlib.sha256(preferences).hexdigest(),
                verification_scope="SIMULATOR_GLOBAL_PREFERENCES_AFTER_REBOOT",
                app_override_verified_by_this_observation=False)


def configure_editor_device_language(app, evidence, udid, app_language):
    """Only called after the exact fresh run-owned simulator identity is verified."""
    language = "en" if app_language == "he" else "he"
    locale = "en_US" if language == "en" else "he_IL"
    path = evidence / "device-language-observation.json"
    observation = dict(status="CONFIGURING_DISPOSABLE_SIMULATOR", simulator_udid=udid,
                       requested_device_language=language, requested_locale=locale,
                       app_language=app_language)
    shared.write(path, observation)
    try:
        for command in [
            ["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLanguages", "-array", language],
            ["xcrun", "simctl", "spawn", udid, "defaults", "write", "-g", "AppleLocale", "-string", locale],
            ["xcrun", "simctl", "shutdown", udid],
            ["xcrun", "simctl", "boot", udid],
            ["xcrun", "simctl", "bootstatus", udid, "-b"],
        ]:
            shared.command(command, app, evidence)
        command = ["xcrun", "simctl", "spawn", udid, "defaults", "export", "NSGlobalDomain", "-"]
        observation.update(command=command, readback_timeout_seconds=EDITOR_DEVICE_PREFERENCES_TIMEOUT_SECONDS)
        shared.write(path, observation)
        started = time.monotonic()
        try:
            observed = subprocess.run(command, capture_output=True, timeout=EDITOR_DEVICE_PREFERENCES_TIMEOUT_SECONDS)
        finally:
            observation["readback_elapsed_seconds"] = round(time.monotonic() - started, 3)
        observation.update(command_exit_code=observed.returncode,
                           error=observed.stderr.decode("utf-8", errors="replace"),
                           preferences_sha256=hashlib.sha256(observed.stdout).hexdigest())
        require(observed.returncode == 0, "Could not read actual simulator language after reboot")
        # Publish only the language/locale fields and digest, never the whole globals plist.
        observation.update(validate_device_language(observed.stdout, app_language))
        shared.write(path, observation)
        return observation
    except BaseException as error:
        observation.update(status="FAIL", failure_type=type(error).__name__, failure=str(error))
        shared.write(path, observation)
        raise


def source_methods(app, selection):
    text = "\n".join(p.read_text(encoding="utf-8") for p in (app / "PinkhaStage1Acceptance/Tests").glob("*.swift"))
    for method in selection:
        suite, name = method.split("/")
        require("class " + suite + ":" in text and re.search(r"\bfunc\s+" + re.escape(name) + r"\s*\(", text),
                "Selected real UI method absent from tracked source: " + method)


class SelectionFailure(ValueError):
    """The selected XCTest phase failed; the batch still verifies its raw result."""


def execute(args, receipt, *, build_context=None):
    require(platform.system() == "Darwin", "Actual Apple host required")
    app, evidence, derived = args.app.resolve(), args.evidence.resolve(), args.derived.resolve()
    selection = plan(args.lane, args.device, args.language)
    acknowledgement = None
    if getattr(args, "include_text_native_ack", False):
        require(args.lane == text_native_ack.BASE_LANE and build_context is None,
                "Native-ack components require the explicit single SDK06 Debug build")
        acknowledgement = text_native_ack.source_contract(app)
        selection["additional_components"] = acknowledgement
        selection["requested_lane"] = text_native_ack.LANE
        receipt["text_native_acknowledgement"] = {"status": "NOT_RUN", **acknowledgement}
    shared_editor = None
    if getattr(args, "include_shared_editor", False):
        require(acknowledgement is not None and args.device == "ipad",
                "The shared-editor profile requires the same SDK06 iPad Debug build")
        shared_editor = shared_editor_existing_build.source_contract(app)
        selection["shared_editor_components"] = shared_editor
        selection["requested_lane"] = shared_editor_existing_build.LANE
        receipt["shared_editor_components"] = {"status": "NOT_RUN", **shared_editor}
    hanlin_lane = HANLIN_LANES.get(args.lane)
    source_methods(app, selection["methods"])
    head = shared.git(app, "rev-parse", "HEAD")
    require_source_identity(head, os.environ.get("GITHUB_SHA"),
                            shared.git(app, "branch", "--show-current"), os.environ.get("GITHUB_REF"))
    require(os.environ.get("GITHUB_RUN_ID", "").isdigit(), "Missing actual CI run identity")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
            and preflight.get("source_sha") == head
            and preflight.get("run_id") == os.environ["GITHUB_RUN_ID"], "OS27 preflight is not from this source/run")
    selected = preflight["selected"][args.device]
    udid = selected["udid"]
    require(build_context is None or selected == build_context.device,
            "Same-job lane does not use its newly created simulator")
    expected_name = ("Pinkha-UI27-" + os.environ["GITHUB_RUN_ID"] + "-" + args.device
                     if build_context is None else build_context.device["name"])
    require(selected["name"] == expected_name, "Refuse a non-disposable simulator")
    installation = json.loads((evidence / "heart/heart-installation.json").read_text())
    binding = shared.runtime_binding(app, evidence, head, args, installation)
    matrix = json.loads((app / "Tools/PinkhaSimulatorGate/required-coverage.json").read_text())
    identity = shared.candidate_identity(app, matrix)
    receipt.update(source_sha=head, run_id=os.environ["GITHUB_RUN_ID"], run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                   kit_sha=shared.KIT, **binding, selection=selection,
                   candidate_input_hashes=identity["hashes"], runtime_installation=installation, phase="BUILD")
    shared.write(evidence / "selection-plan.json", selection)
    shared.write(evidence / "execution.json", receipt)
    shared.command(["xcrun", "simctl", "boot", udid], app, evidence)
    shared.command(["xcrun", "simctl", "bootstatus", udid, "-b"], app, evidence)
    if build_context is not None:
        build_context.confirm_empty_container(udid, evidence)
    observed_device_language = None
    if args.lane == "editor":
        receipt["phase"] = "DEVICE_LANGUAGE_CONFIGURATION"
        shared.write(evidence / "execution.json", receipt)
        language_observation = configure_editor_device_language(app, evidence, udid, args.language)
        observed_device_language = language_observation["device_language"]
        selection.update(device_language_verified=True, device_language=observed_device_language,
                         device_language_scope=language_observation["verification_scope"])
        receipt["phase"] = "BUILD"
        shared.write(evidence / "selection-plan.json", selection)
        shared.write(evidence / "execution.json", receipt)
    else:
        device_language = subprocess.run(["xcrun", "simctl", "spawn", udid, "defaults", "read", "-g", "AppleLanguages"],
                                        capture_output=True, text=True)
        shared.write(evidence / "device-language-observation.json",
                     dict(command_exit_code=device_language.returncode, observed=device_language.stdout,
                          error=device_language.stderr, acceptance=False))
    if build_context is None:
        shared.prepare_source_cache(app, derived)
    flags = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED", "ENABLE_TESTABILITY=YES",
             "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
    configuration_name = selection["build_configuration"]
    if hanlin_lane is not None:
        flags[0] += " -D DEBUG"
    if build_context is not None:
        flags = build_context.lane_build_flags(args.lane, flags, configuration_name)
    native_suite = LANES[args.lane]["preparation"].split("/")[0]
    base = ["xcodebuild", "build-for-testing", "-configuration", configuration_name,
            "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO"]
    if build_context is None:
        shared.command([*base, "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
                        "-derivedDataPath", str(derived), "-only-testing:AnytypeTests/" + native_suite,
                        *(["-only-testing:AnytypeTests/" + preservation.SUITE] if args.lane == "properties-set" else []),
                        *(["-only-testing:AnytypeTests/" + text_native_ack.SUITE] if acknowledgement else []),
                        *(["-only-testing:AnytypeTests/" + suite for suite in shared_editor_existing_build.SUITES] if shared_editor else []),
                        *flags], app, evidence)
    else:
        require(derived == build_context.derived, "Same-job native product directory differs")
        build_context.verify(app, head, identity, flags, configuration_name)
        receipt["build_mode"] = "SAME_JOB_FROZEN_BUILD"
    receipt.update(native_build_succeeded=True, native_build_flags=flags)
    built = derived / "Build/Products" / (configuration_name + "-iphonesimulator/Anytype.app")
    shared.verify_signed_simulator(built, evidence)
    shared.verify_runtime_copies(built, binding['native_marker'].encode(), evidence)
    checkouts = derived / "SourcePackages/checkouts"
    kit = next(p for p in checkouts.iterdir() if p.name.casefold() == "torahinspectorkit")
    require(shared.git(kit, "rev-parse", "HEAD") == shared.KIT, "Actual Kit checkout differs")
    lock = json.loads((app / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved").read_text())
    require(next(p["state"]["revision"] for p in lock["pins"] if p["identity"] == "torahinspectorkit") == shared.KIT,
            "Actual Kit lock differs")
    shared.write(evidence / "actual-package-pins.json", lock)
    before = shared.code_carriers(built)
    shared.write(evidence / "built-code-carriers.json", before)
    native_configuration = shared.test_configuration(derived / "Build/Products", "AnytypeTests")
    receipt["phase"] = "PREPARATION"
    native_environment = preparation_environment(args.lane, head, receipt["run_id"], receipt["run_attempt"])
    preservation_binding = None
    frozen_preservation = None
    if args.lane == "properties-set":
        preservation_binding = preservation.binding(head, receipt["run_id"], receipt["run_attempt"])
        receipt.update(postflight_binding=preservation_binding,
                       postflight={"status": "NOT_RUN", "reason": "REQUIRES_PREPARATION_AND_BOTH_UI_METHODS_PASS"})
        native_environment.update(preservation.binding_environment(preservation_binding))
        native_environment["PINKHA_PREPARE_TYPE_PRESERVATION"] = "1"
    run_selection = shared.run_selection if build_context is None else build_context.run_selection
    if shared_editor:
        receipt["phase"] = "SHARED_EDITOR_COMPONENTS"
        shared.write(evidence / "execution.json", receipt)
        component_evidence = evidence / "shared-editor-components"
        try:
            receipt["shared_editor_components"] = shared_editor_existing_build.execute(
                app, native_configuration, udid, built, component_evidence, shared)
        finally:
            component_receipt = component_evidence / "execution.json"
            if component_receipt.is_file():
                receipt["shared_editor_components"] = json.loads(component_receipt.read_text())
            shared.write(evidence / "execution.json", receipt)
    if acknowledgement:
        receipt["phase"] = "TEXT_NATIVE_ACK_COMPONENTS"
        shared.write(evidence / "execution.json", receipt)
        component = run_selection(app, native_configuration, "AnytypeTests", udid,
            text_native_ack.METHODS, {}, evidence / "text-native-ack", "text-native-ack")
        receipt["text_native_acknowledgement"] = {"source": acknowledgement, "execution": component}
        shared.write(evidence / "execution.json", receipt)
        qualified = text_native_ack.qualify_result(component)
        require(text_native_ack.source_contract(app) == acknowledgement,
                "Native-ack source changed during component execution")
        receipt["text_native_acknowledgement"].update(qualified)
        receipt["phase"] = "PREPARATION"
        shared.write(evidence / "execution.json", receipt)
    preparation = run_selection(app, native_configuration, "AnytypeTests", udid,
        [LANES[args.lane]["preparation"]], native_environment, evidence / "preparation", "prepare")
    receipt["preparation"] = preparation
    shared.write(evidence / "execution.json", receipt)
    if preparation["status"] != "PASS":
        raise SelectionFailure("The actual native fixture did not pass")
    container = Path(subprocess.check_output(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"], text=True).strip())
    raw_fixture = (container / "Library/Application Support" / LANES[args.lane]["fixture"]).read_text(encoding="utf-8")
    if hanlin_lane is not None:
        require(len(raw_fixture.encode("utf-8")) <= 16384, "Oversized native SDK fixture")
    fixture = json.loads(raw_fixture)
    if build_context is not None:
        build_context.observe_fixture(fixture, container, evidence)
    if hanlin_lane is not None:
        environment = hanlin_lane[0].fixture_environment(fixture, head, receipt["run_id"], receipt["run_attempt"],
                                               datetime.now(timezone.utc).timestamp(), raw_fixture)
    else:
        environment = fixture_environment(args.lane, fixture, args.language, observed_device_language)
    if args.lane == "canonical-properties":
        environment.update(property_environment(evidence / "preparation", fixture["spaceId"]))
    shared.write(evidence / "fixture-ids.json", fixture)
    if args.lane == "properties-set":
        frozen_preservation = preservation.freeze(container, evidence, preservation_binding, fixture, udid)
        receipt["preservation_baseline_sha256"] = frozen_preservation.sha256
        receipt["preservation_fixture_sha256"] = frozen_preservation.fixture_sha256
        shared.write(evidence / "type-preservation-inputs.json", {
            "binding": preservation_binding, "baseline_sha256": frozen_preservation.sha256,
            "fixture_sha256": frozen_preservation.fixture_sha256,
            "directories": frozen_preservation.directories, "container": str(frozen_preservation.container),
            "simulator_udid": udid, "source": "FROZEN_BEFORE_UI"})

    ui_derived = derived.with_name(derived.name + "-ui")
    receipt["phase"] = "UI_BUILD"
    shared.write(evidence / "execution.json", receipt)
    if build_context is None:
        project = shared.ui_only_project(app)
        shared.command([*base, "-project", str(project), "-scheme", "PinkhaPrebuiltUI", "-derivedDataPath", str(ui_derived),
                        *["-only-testing:PinkhaStage1AcceptanceUITests/" + method for method in selection["methods"]], *flags], app, evidence)
    else:
        require(ui_derived == build_context.ui_derived, "Same-job UI runner directory differs")
        build_context.verify(app, head, identity, flags, configuration_name)
        receipt["ui_build_mode"] = "SAME_JOB_FROZEN_BUILD"
    receipt["phase"] = "UI_RUNTIME_PREPARATION"
    shared.write(evidence / "execution.json", receipt)
    runtime_identity = {
        "source_sha": head, "run_id": receipt["run_id"], "run_attempt": receipt["run_attempt"],
        "kit_sha": shared.KIT, **binding,
        "candidate_inputs_sha256": hashlib.sha256(json.dumps(identity["hashes"], sort_keys=True).encode()).hexdigest()}
    ui_runtime_observer = None
    if args.lane == "hanlin-native":
        # This UI method cold-launches its own app. Observe that actual process
        # during its original native journey; a preflight probe cannot bind it.
        ui_runtime_observer = hanlin_ui_runtime.NativeUIRuntimeObserver(
            udid, evidence, built, fixture, raw_fixture, runtime_identity, shared)
        receipt["live_runtime_before_ui"] = {"status": "ACTUAL_UI_PROCESS_OBSERVATION_REQUIRED",
                                            "extra_app_launches": 0}
    else:
        live = shared.live_runtime(udid, evidence, built, args.language, source_identity=runtime_identity)
        receipt["live_runtime_before_ui"] = live
    shared.install_ui_runner(udid, ui_derived / "Build/Products", app, evidence, configuration=configuration_name)
    configuration = shared.test_configuration(ui_derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    environment.update(PINKHA_UI27_APP_LANGUAGE=args.language, PINKHA_UI27_SELECTION_SCOPE="WAVE15_ACCEPTANCE")
    if args.lane == "inspector":
        environment["PINKHA_UI27_EXPECTED_APP_PID"] = str(live["pid"])
    receipt["phase"] = "UI"
    shared.write(evidence / "execution.json", receipt)
    try:
        if ui_runtime_observer is not None:
            ui_runtime_observer.start()
        result = run_selection(app, configuration, "PinkhaStage1AcceptanceUITests", udid,
            selection["methods"], environment, evidence / "ui", "wave15-" + args.lane, built)
        receipt["ui"] = result
    finally:
        if ui_runtime_observer is not None:
            ui_runtime_observer.finalize(receipt, evidence / hanlin_lane[2],
                lambda: shared.export_ui_console(udid, evidence), sys.exception())
        else:
            shared.export_ui_console(udid, evidence)
            if hanlin_lane is not None:
                result_path = container / "Library/Application Support" / hanlin_lane[1]
                # Preserve failure receipts too; copying a label does not qualify it.
                if result_path.is_file():
                    (evidence / hanlin_lane[2]).write_bytes(result_path.read_bytes())
    if result["status"] != "PASS" or result["passed"] != selection["expected_ui_executions"]:
        raise SelectionFailure("Actual named UI selection did not pass")
    if hanlin_lane is not None:
        raw_result = (evidence / hanlin_lane[2]).read_bytes()
        native_result = hanlin_ui_runtime.decode(raw_result) if ui_runtime_observer is not None else json.loads(raw_result)
        receipt[hanlin_lane[3]] = hanlin_lane[0].validate_result(native_result, fixture, head,
            receipt["run_id"], receipt["run_attempt"], datetime.now(timezone.utc).timestamp())
        if ui_runtime_observer is not None:
            receipt["actual_ui_runtime"] = ui_runtime_observer.qualify(native_result, raw_result,
                evidence / "ui", "wave15-hanlin-native", selection["methods"])
    if args.lane == "inspector":
        receipt["ui_process_continuity"] = shared.verify_ui_process_continuity(
            evidence / "ui", "wave15-" + args.lane, live, selection["methods"])
    if args.lane == "properties-set":
        # Both original UI methods include bounded termination of their own
        # XCUIApplication. A failed exit fails UI and never reaches this phase.
        preservation.require_ui_passed(result, selection["methods"])
        receipt["phase"] = "POSTFLIGHT"
        shared.write(evidence / "execution.json", receipt)
        current_container = Path(subprocess.check_output(
            ["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"], text=True).strip())
        preservation.verify_frozen(frozen_preservation, current_container)
        installed_before = Path(subprocess.check_output(
            ["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "app"], text=True).strip())
        require(shared.code_carriers(installed_before)["sha256"] == before["sha256"],
                "Installed executable bytes changed before native postflight")
        if build_context is not None:
            build_context.verify_current()
        # Application_Home may move during installation (Apple TN2285). Prove
        # stopped native bytes and original fixture continuity across one
        # explicit same-build install. Normal simulator XCTest may then relocate
        # that same store; the native host proves its identity and all bytes
        # again before AccountSelect opens it.
        post_installation = preservation.install_for_postflight(
            frozen_preservation, built, before["sha256"], evidence, shared.code_carriers)
        receipt["preservation_installation_sha256"] = post_installation.sha256
        shared.write(evidence / "execution.json", receipt)
        post_environment = preservation.environment(frozen_preservation, post_installation)
        post_configuration = native_configuration if build_context is not None else preservation.selected_configuration(
            native_configuration, post_environment)
        postflight = run_selection(app, post_configuration, "AnytypeTests", udid,
            [preservation.METHOD], post_environment, evidence / "postflight", preservation.PREFIX)
        receipt["postflight"] = postflight
        shared.write(evidence / "execution.json", receipt)
        current_container = Path(subprocess.check_output(
            ["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "data"], text=True).strip())
        if postflight["status"] != "PASS":
            raise SelectionFailure("Actual existing-account preservation postflight did not pass")
        raw_receipt = preservation.read_bytes(current_container / "Library/Application Support" /
            ("pinkha-type-preservation-result-" + preservation_binding["nonce"] + ".json"))
        with (evidence / "postflight/native-result.json").open("xb") as stream:
            stream.write(raw_receipt)
        receipt["preservation_native_receipt_sha256"] = preservation.sha256(raw_receipt)
        receipt["type_preservation"] = preservation.validate_result(
            frozen_preservation, post_installation, preservation.decode(raw_receipt), postflight, current_container)
        if build_context is not None:
            build_context.verify_current()
    installed = Path(subprocess.check_output(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", "app"], text=True).strip())
    after = shared.code_carriers(installed)
    shared.write(evidence / "post-ui-installed-code-carriers.json", after)
    require(before["sha256"] == after["sha256"], "Installed executable bytes changed during UI execution")
    require(shared.git(app, "rev-parse", "HEAD") == head, "Source changed during acceptance")
    receipt.update(status="LANE_PASS_ACCEPTANCE_REVIEW_PENDING", phase="COMPLETE",
                   passed_ui_methods=result["passed"], failed_ui_methods=0, skipped_ui_methods=0,
                   full_matrix_accepted=False, release_accepted=False,
                   limitations=["This result covers only its named methods and actual configuration.",
                                "Screenshots require visual review; criteria outside the named methods remain open.",
                                "Device-language mismatch and every relaunch's live mapping are not established by a requested label."])


def main():
    import wave15_batch
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--lane", choices=[*LANES, *wave15_batch.PROFILES, text_native_ack.LANE, shared_editor_existing_build.LANE], required=True)
    parser.add_argument("--device", choices=["iphone", "ipad"], required=True)
    parser.add_argument("--language", choices=["en", "he"], required=True)
    parser.add_argument("--runtime-profile", choices=shared.heart_profiles.PROFILE_NAMES, default="r14")
    parser.add_argument("--heart-source-run-id", default="")
    args = parser.parse_args()
    args.include_shared_editor = args.lane == shared_editor_existing_build.LANE
    if args.include_shared_editor:
        args.lane = text_native_ack.LANE
    args.lane, args.include_text_native_ack = text_native_ack.resolve_lane(args.lane)
    if args.lane in wave15_batch.PROFILES:
        return wave15_batch.run(args, sys.modules[__name__])
    args.evidence.mkdir(parents=True, exist_ok=True)
    require(not (args.evidence / "execution.json").exists(), "Refuse stale execution evidence")
    receipt = dict(status="FAIL", phase="PREFLIGHT", full_matrix_accepted=False, release_accepted=False,
                   started_at=datetime.now(timezone.utc).isoformat())
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    if receipt.get("native_build_succeeded"):
        try:
            receipt["compiled_products"] = shared.capture_products(args.derived.resolve(), args.evidence,
                receipt["source_sha"], receipt["native_build_flags"])
        except Exception as error:
            receipt["compiled_products"] = dict(status="CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED", error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    shared.write(args.evidence / "execution.json", receipt)
    diagnostics.emit_execution(receipt, args.lane)
    print(json.dumps(receipt))
    return 0 if receipt["status"] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
