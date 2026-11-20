#!/usr/bin/env python3
"""Require actual named iOS execution on this run's simulator, without skips."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROFILES = {
    "runtime": {
        "AnyEmbeddedRuntimeTests": [
            "testRealManagedRuntimeLifecycleAndControlBoundary",
            "testWrongNativeBuildContractCannotStart",
            "testInvalidConfigurationCannotSelectProductionByAccident",
        ],
    },
    "hanlin-ios": {
        "KnownCreationRecoveryFilesystemTests": [
            "testKnownPartialRootSurvivesReopenWithoutChangingV1OutcomeBytes",
            "testDifferentRootAndNoEffectCannotReplaceDurableKnownRoot",
            "testRecordedNoDispatchCannotAcquireAKnownNativeRoot",
        ],
    },
    "ui-ios": {
        "AnyNativePropertyPresentationTests": [
            "delayedReviewCannotRestoreOldTypeOrEraseAcknowledgedUndo",
            "delayedReadFailureCannotReplaceAcknowledgedWriteFeedbackOrUndo",
            "delayedRefreshCannotRevealAnAcknowledgedHiddenProperty",
            "refreshDuringWriteDoesNotDispatchOrReportMissingWorkspace",
            "supersededReadFailureCannotClearNewerReadSpinnerOrFeedback",
            "oldReadCannotPublishOrClearLoadingAfterOwnerReactivation",
            "oldWriteCompletionCannotClearNewOwnerSavingStateOrPublishFailure",
        ],
        "AnyNativeMarkedTextTests": [
            "testFirstMarkedInputBeginsBeforeMutationAndRepeatedUpdatesKeepTheMarkedRange",
            "testActualMarkedBufferUsesImmutableRawProjectionUntilCommit",
            "testRecoveryCapturesLatestVisibleTextAndNeverRequestsASave",
            "testRejectedBeginOrProposalDoesNotReplaceVisibleSource",
            "testUnmarkAndResignEndOnceAndNormalTextInputStillWorks",
        ],
        "AnyNativeFocusLifecycleTests": [
            "testDetachedRequestWaitsForAttachmentAndIsConsumedOnce",
            "testKeyWindowReadinessRetriesNativeRefusalWithoutRenderPolling",
            "testNewUserFocusCancelsDetachedRequest",
            "testOwnerOrVersionChangeCancelsOldRequestBeforeRebind",
            "testLockedViewDenialDoesNotReviveAfterUnlock",
            "testCurrentResponderRequestDoesNotStealFocusAfterLaterInput",
        ],
    },
    "application": {
        "NativeDocumentPublicationTests": [
            "testAcknowledgedNativeEditsRetireOlderReadsAndKeepUndo",
            "testStaleReadFailureAndDeferCannotReplaceNewOwnerState",
            "testTypingAndCompositionBackToBaseDuringNativeSaveRetainNewRevision",
        ],
        "NativePropertyWorkflowTests": [
            "testOriginalFifteenPropertyAssertionsOnRealNativeLibrary",
        ],
        "NativeApplicationTests": [
            "testRealAccountWorkspaceJournalEditorAndColdReopen",
            "testPostAuthKeychainFailureRevokesNativeAuthorityAndRecoversSameAccount",
            "testRealKeychainNamespaceAndRecoveryMetadataIsolation",
        ],
        "NativeHanlinCreationTests": [
            "testRealProtectedHanlinCreationDenialCommitDuplicateAndRevocation",
        ],
        "NativeTorahWorkflowTests": [
            "testNativeQuotesNotesRelatedIndexUnlinkAndRuntimeReopen",
        ],
    },
    "native-ui": {
        "NativeLaunchTests": [
            "testFreshNativeExecutableShowsAccountAndRecoveryEntryPoints",
            "testBackgroundAndForegroundReopenTheOwnedRuntime",
            "testCreateEditHanlinConsentBackgroundAndColdReopen",
            "testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
            "testSourceInspectorQuoteAndNoteSurviveColdReopen",
            "testExplicitHebrewDirectionAndAlignmentSurviveColdReopen",
            "testHierarchyDragIntoFolderPersistsAfterColdReopen",
        ],
    },
}
SOURCE_PATHS = {
    "runtime": ["Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyEmbeddedRuntimeTests.swift"],
    "hanlin-ios": ["Modules/PinkhaAnyHanlin/Tests/PinkhaAnyHanlinTests/KnownCreationRecoveryTests.swift"],
    "ui-ios": [
        "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeMarkedTextTests.swift",
        "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeFocusLifecycleTests.swift",
        "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift",
    ],
    "application": [
        "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeApplicationTests.swift",
        "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeHanlinCreationTests.swift",
        "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeTorahWorkflowTests.swift",
        "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeDocumentPublicationTests.swift",
        "Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativePropertyWorkflowTests.swift",
    ],
    "native-ui": ["NativeApp/UITests/NativeLaunchTests.swift"],
}

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def expected_methods(profile):
    return {suite + "/" + name for suite, names in PROFILES[profile].items() for name in names}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def test_cases(tree):
    # Same xcresult node contract used by the retained Hanlin host gate.
    found = {}
    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                identifier = value.get("nodeIdentifier")
                require(isinstance(identifier, str) and identifier and identifier not in found,
                        "Unnamed or duplicate actual test case")
                found[identifier] = value.get("result")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(tree)
    return found

def validate(summary, tree, profile, udid):
    expected = expected_methods(profile)
    counts = {key: summary.get(key) for key in
              ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(value) is int for value in counts.values()), "Missing integer execution counts")
    require(counts["totalTestCount"] >= len(expected) > 0, "Zero or incomplete test execution")
    require(counts["passedTests"] == counts["totalTestCount"] and
            counts["failedTests"] == counts["skippedTests"] == 0, "Failed or skipped tests")
    configurations = summary.get("devicesAndConfigurations", [])
    require(len(configurations) == 1, "Expected one actual test destination")
    device = configurations[0].get("device", {})
    version = str(device.get("osVersion", "")).split(".")
    require(isinstance(device.get("deviceId"), str) and
            device["deviceId"].lower() == udid.lower() and
            version[0].isdigit() and int(version[0]) >= 27 and
            device.get("osBuildNumber") and device.get("architecture") == "arm64",
            "Actual destination differs from this run's owned iOS 27+ ARM64 simulator")
    cases = test_cases(tree)
    require(cases and all(result == "Passed" for result in cases.values()),
            "Missing, failed, or skipped actual test nodes")
    observed = set()
    for identifier in cases:
        for method in expected:
            if re.search(r"(?:^|/)" + re.escape(method) + r"(?:\(|/|$)", identifier):
                observed.add(method)
    require(observed == expected, "Missing required named execution: " +
            ", ".join(sorted(expected - observed)))
    return {"counts": counts, "requiredMethods": sorted(expected),
            "observedRequiredMethods": sorted(observed),
            "actualCases": cases, "device": device}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILES), required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--udid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "profile": args.profile,
              "scope": "actual_named_apple_test_execution", "runnerSHA256": sha(Path(__file__))}
    try:
        require(bool(args.udid), "Owned simulator was not created")
        record["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        record["testSources"] = {path: sha(ROOT / path) for path in SOURCE_PATHS[args.profile]}
        record["summarySHA256"] = sha(args.summary)
        record["testTreeSHA256"] = sha(args.tests)
        record.update(validate(json.loads(args.summary.read_text(encoding="utf-8")),
                               json.loads(args.tests.read_text(encoding="utf-8")),
                               args.profile, args.udid))
        record["status"] = "PASS"
    except Exception as error:
        record["failure"] = {"kind": type(error).__name__, "description": str(error)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
