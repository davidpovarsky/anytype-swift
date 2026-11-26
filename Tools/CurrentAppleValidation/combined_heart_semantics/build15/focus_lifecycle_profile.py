"""Exact affected UIKit focus suite; original result/argument validators; no native acceptance by declaration."""
import hashlib
import subprocess
import run_host_tests as host
import wave15_core_profile as core
import shared_editor_existing_build as existing
SUITE="TextBlockFocusLifecycleTests"
SOURCE_PATH='AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift'
SOURCE_SHA256='74f09e8baa94bc8ab33668ceb72b9f59790d5a1b5e5a6d624b286844651190b3'
METHOD_COUNT=21
CASE_COUNT=32
METHODS={'reusedCellDoesNotPreserveDifferentPendingOwner': {'parameters': [{'name': 'composing', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'sameInputOwnerSurvivesForkAndExplicitReplacementEndsComposition': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'pendingLocalTextSurvivesNativeReconfiguration': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'completedLocalTextAcceptsRemoteReplacement': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'nativeFocusObservationDistinguishesOutcomes': {'parameters': [{'name': 'outcome', 'type': 'String'}], 'argument_collections': [['ineligible', 'refused', 'accepted']], 'case_count': 3}, 'insertedCellUsesCurrentEditingBeforeFocus': {'parameters': [{'name': 'editing', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'reusedCellUsesCurrentLockBeforeFocus': {'parameters': [{'name': 'newLocked', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'initialFocusWaitsForAttachment': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'pendingFocusWaitsForVisibleLayout': {'parameters': [{'name': 'superseded', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'visibleLayoutsDoNotRetryNativeRefusal': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'pendingFocusWaitsForKeyWindow': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'refusedFocusWaitsForWindowReadiness': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'explicitHandoffDoesNotReplayInitialCaret': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'staleFocusDoesNotSurviveRowLifetime': {'parameters': [{'name': 'change', 'type': 'String'}], 'argument_collections': [['rebind', 'detach', 'editorContext']], 'case_count': 3}, 'laterFocusSupersedesDetachedRequest': {'parameters': [{'name': 'useNativeEditing', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'editingDenialCancelsPendingFocus': {'parameters': [{'name': 'locked', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'focusedTextViewDoesNotReplayResponderAcquisition': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'consumedAndNewerFocusSurviveOldCallbacks': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'requestIdentityParticipatesInCellConfigurationEquality': {'parameters': [], 'argument_collections': [], 'case_count': 1}, 'collectionPresentationResumesOnlyCurrentUnattemptedFocus': {'parameters': [{'name': 'superseded', 'type': 'Bool'}], 'argument_collections': [[False, True]], 'case_count': 2}, 'collectionPresentationDoesNotReplayNativeRefusal': {'parameters': [], 'argument_collections': [], 'case_count': 1}}

def validate_source(text):
    core.require(hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA256, "Exact379ca additive focus source required")
    declarations = core.inspect_declarations(text)
    core.require(declarations == METHODS, "Affected UIKit focus named declarations or exact literal cases changed")
    core.require(len(METHODS) == METHOD_COUNT
                 and sum(value["case_count"] for value in METHODS.values()) == CASE_COUNT,
                 "Affected UIKit focus source method/case scope differs")
    return {SUITE + "/" + name for name in METHODS}


def source_contract(app):
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    candidates = [name for name in tracked if name.casefold() == SOURCE_PATH.casefold()]
    core.require(len(candidates) == 1, "Missing or case-colliding tracked Affected UIKit focus source")
    actual, synced = app / candidates[0], app / SOURCE_PATH
    core.require(synced.is_file() and actual.samefile(synced), "Affected UIKit focus source is outside the synchronized Xcode root")
    data = actual.read_bytes()
    methods = validate_source(data.decode("utf-8"))
    identifiers = ["AnytypeTests/" + SUITE + "/" + name + "("
                   + "".join(parameter["name"] + ":" for parameter in spec["parameters"]) + ")"
                   for name, spec in METHODS.items()]
    return dict(kind="focus-lifecycle", source_path=candidates[0], source_sha256=hashlib.sha256(data).hexdigest(),
                methods=sorted(methods), compiled_identifiers=sorted(identifiers),
                expected_methods=METHOD_COUNT, declared_cases=CASE_COUNT)


def validate_results(summary, tree, udid):
    expected = {SUITE + "/" + name for name in METHODS}
    actual = host.validate_results(summary, tree, expected, udid)
    cases = core.validate_arguments(tree, expected, {SUITE: {"methods": METHODS}})
    core.require(actual["counts"]["totalTestCount"] in {METHOD_COUNT, CASE_COUNT},
                 "Affected UIKit focus summary differs from exact source methods or literal cases")
    core.require(cases["actual_method_count"] == METHOD_COUNT and cases["declared_case_count"] == CASE_COUNT,
                 "Affected UIKit focus actual named/argument execution is incomplete")
    return dict(actual, **cases)


def validate_enumeration(payload, contract):
    plan, enabled, disabled = existing.enumerated_identifiers(payload)
    core.require(enabled == set(contract["compiled_identifiers"]) and not enabled.intersection(disabled),
                 "Compiled pending T5 suite differs from exact source declarations; no tests executed")
    return dict(test_plan=plan, identifiers=sorted(enabled), tests_executed=0)
