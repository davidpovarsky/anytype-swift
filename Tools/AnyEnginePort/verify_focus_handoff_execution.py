#!/usr/bin/env python3
"""Require exactly six prior focus methods and four new UIKit handoff methods."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import reuse_uikit_execution as original
import reuse_uikit_unaffected_eight as retained
import verify_native_test_execution as execution

ROOT = Path(__file__).resolve().parents[2]
PROFILE = retained.FRESH_PROFILE
FOCUS_METHODS = [
    "testDetachedRequestWaitsForAttachmentAndIsConsumedOnce",
    "testKeyWindowReadinessRetriesNativeRefusalWithoutRenderPolling",
    "testNewUserFocusCancelsDetachedRequest",
    "testOwnerOrVersionChangeCancelsOldRequestBeforeRebind",
    "testLockedViewDenialDoesNotReviveAfterUnlock",
    "testCurrentResponderRequestDoesNotStealFocusAfterLaterInput",
]
HANDOFF_METHODS = [
    "testSnapshotCompletionUnwindsBeforeResponderAcquisition",
    "testReadinessBurstAndReentrantLayoutDeliverOnlyOneAttempt",
    "testQueuedDeliveryRevalidatesOwnerVersionAndHonorsCancellationAndReplacement",
    "testDeferredNativeRefusalWaitsForActualReadinessWithoutLayoutRetries",
]
TEST_SOURCES = ["Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeFocusLifecycleTests.swift",
                retained.NEW_TEST]
SELF = "Tools/AnyEnginePort/verify_focus_handoff_execution.py"


def register_profile() -> None:
    original.require(set(FOCUS_METHODS) == set(execution.PROFILES[original.PROFILE]["AnyNativeFocusLifecycleTests"]),
                     "original_focus_method_inventory_changed")
    execution.PROFILES[PROFILE] = {"AnyNativeFocusLifecycleTests": FOCUS_METHODS,
                                   "AnyNativeFocusHandoffTests": HANDOFF_METHODS}
    execution.SOURCE_PATHS[PROFILE] = TEST_SOURCES
    execution.EXACT_PROFILES = execution.EXACT_PROFILES | {PROFILE}


def validate(summary: dict, tree: dict, udid: str) -> dict:
    register_profile()
    value = execution.validate(summary, tree, PROFILE, udid)
    original.require(value["counts"]["totalTestCount"] == 10 and len(value["actualCases"]) == 10,
                     "focus_handoff_requires_exactly_ten_methods")
    return value


def verify_retained_record(record: dict, consumer: str) -> None:
    original.require(all(type(record.get(key)) is int for key in
                         ("originalExecutedCount", "reusedCount", "testsExecutedThisRun", "requiredFreshCount")),
                     "retained_execution_counts_must_be_integers")
    original.require(record.get("status") == "VERIFIED_REUSE" and record.get("profile") == retained.PROFILE and
                     record.get("scope") == "verified_prior_uikit_subset_reuse" and
                     record.get("consumerCommit") == consumer and record.get("originalExecutedCount") == 14 and
                     record.get("reusedCount") == 8 and record.get("testsExecutedThisRun") == 0 and
                     record.get("fullAcceptance") is False and
                     record.get("reusedMethods") == sorted(retained.retained_methods()) and
                     record.get("notReusedAffectedMethods") == sorted(retained.affected_methods()) and
                     record.get("requiredFreshProfile") == PROFILE and record.get("requiredFreshCount") == 10,
                     "unaffected_eight_not_qualified_for_this_consumer")
    original.require(record.get("runnerSHA256") == original.digest((ROOT / retained.SELF).read_bytes()),
                     "retained_verifier_source_mismatch")
    proof = record.get("sourceProof", {})
    original.require(proof.get("handoffSourceReview") == retained.HANDOFF_SOURCE_REVIEW and
                     proof.get("unchangedEmbeddedAnyNativeTextView", {}).get("sha256") == retained.TEXT_VIEW_SHA256 and
                     proof.get("freshHandoffTestGitBlob") == retained.NEW_TEST_GIT_BLOB,
                     "retained_handoff_source_proof_mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--udid", required=True)
    parser.add_argument("--retained-eight", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "profile": PROFILE,
              "scope": "actual_named_apple_test_execution", "observationOnly": False,
              "fullAcceptance": False, "runnerSHA256": original.digest(Path(__file__).read_bytes()),
              "claimBoundary": "Exactly ten focus component methods execute now. Eight unrelated component methods retain their original proof. Real native editor entry and follow-up acceptance remain separate."}
    try:
        consumer = original.git("rev-parse", "HEAD", root=ROOT).decode().strip()
        record["commit"] = consumer
        retained_path = args.retained_eight or args.output.parent / "ui-ios-reuse.json"
        retained_bytes = retained_path.read_bytes()
        verify_retained_record(json.loads(retained_bytes), consumer)
        protected = [*original.PROTECTED_PATHS, retained.NEW_TEST, *retained.HELPERS, SELF]
        dirty = original.git("diff", "--name-only", "-z", "HEAD", "--", *protected, root=ROOT)
        untracked = original.git("ls-files", "--others", "--exclude-standard", "-z",
                                 "--", *protected, root=ROOT)
        original.require(all(not path or path.decode("utf-8") == original.EXCLUDED_SOURCE
                             for path in (dirty + untracked).split(b"\0")), "focus_test_source_is_dirty")
        record["testSources"] = {path: original.digest((ROOT / path).read_bytes()) for path in TEST_SOURCES}
        record["productionSources"] = {path: original.digest((ROOT / path).read_bytes())
                                       for path in retained.HANDOFF_SOURCE_REVIEW}
        record["sourceClosureGitBlobs"] = original.source_tree(consumer, ROOT)
        record["verificationSources"] = {path: original.digest((ROOT / path).read_bytes())
                                         for path in (*retained.HELPERS, SELF)}
        record["retainedEightReceiptSHA256"] = original.digest(retained_bytes)
        record["summarySHA256"] = original.digest(args.summary.read_bytes())
        record["testTreeSHA256"] = original.digest(args.tests.read_bytes())
        record.update(validate(original.read_json(args.summary), original.read_json(args.tests), args.udid))
        record["status"] = "PASS"
    except Exception as error:
        record["failure"] = {"kind": type(error).__name__, "description": str(error)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record.items() if key != "sourceClosureGitBlobs"}, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
