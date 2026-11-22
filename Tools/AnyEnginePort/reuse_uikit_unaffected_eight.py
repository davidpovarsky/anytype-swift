#!/usr/bin/env python3
"""Retain only the eight unaffected methods from the original UIKit14 proof."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

import reuse_uikit_execution as original
import verify_native_test_execution as execution

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "ui-ios-unaffected-eight"
FRESH_PROFILE = "ui-ios-focus-handoff"
EDITOR = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift"
FOCUS = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeFocusCoordinator.swift"
NEW_TEST = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeFocusHandoffTests.swift"
SELF = "Tools/AnyEnginePort/reuse_uikit_unaffected_eight.py"
HELPERS = (SELF, "Tools/AnyEnginePort/reuse_uikit_execution.py",
           "Tools/AnyEnginePort/verify_native_test_execution.py")

# This is an exact source review for the responder handoff repair. It is not a
# general exception for changed focus/editor sources. A later edit requires a
# fresh review, even if these eight methods remain candidates for retention.
HANDOFF_SOURCE_REVIEW = {
    EDITOR: {
        "beforeGitBlob": "59c0a9061081f9bc2776357f09d58d726d6a0bc8",
        "afterGitBlob": "87e143a99640689ea1e520d3459819f153b48740",
        "reason": "Only AnyNativeEditorController readiness delivery and reveal scheduling change. The eight retained methods never instantiate that controller; their actual AnyNativeTextView declaration is verified byte for byte below.",
    },
    FOCUS: {
        "beforeGitBlob": "0ea0e0bcb2aa6518d3210517bdac599b90fc9a6d",
        "afterGitBlob": "bef053d891d3a9cc10f042d62ef331d730d85681",
        "reason": "The six original focus methods are excluded from reuse and must execute again with the four new handoff methods. None of the eight marked-text/renderer methods constructs this coordinator or registers its notification observer.",
    },
}
NEW_TEST_GIT_BLOB = "7aef0601107efe1f51174bee9ff3f3fbfa8c20ee"
TEXT_VIEW_SHA256 = "8739ef7a27019f8d286473227ca784a8e149643d28d4749b277a58ee4bad3951"
TEXT_VIEW_START = b"@MainActor\nfinal class AnyNativeTextView:"
TEXT_VIEW_END = b"@MainActor\nprivate final class AnyNativeBlockCell:"


def require(condition, reason):
    original.require(condition, reason)


def retained_methods() -> set[str]:
    suites = execution.PROFILES[original.PROFILE]
    values = {suite + "/" + name
              for suite in ("AnyNativeMarkedTextTests", "AnyNativeTextRendererTests")
              for name in suites[suite]}
    require(len(values) == 8, "unaffected_method_inventory_changed")
    return values


def affected_methods() -> set[str]:
    values = execution.expected_methods(original.PROFILE) - retained_methods()
    require(len(values) == 6 and all(value.startswith("AnyNativeFocusLifecycleTests/")
                                   for value in values), "affected_focus_inventory_changed")
    return values


def text_view_declaration(source: bytes) -> bytes:
    require(source.count(TEXT_VIEW_START) == source.count(TEXT_VIEW_END) == 1,
            "ambiguous_embedded_text_view_declaration")
    start, end = source.index(TEXT_VIEW_START), source.index(TEXT_VIEW_END)
    require(start < end, "invalid_embedded_text_view_boundaries")
    return source[start:end]


def verify_embedded_text_view(before: bytes, after: bytes) -> dict:
    left, right = text_view_declaration(before), text_view_declaration(after)
    require(left == right, "executed_text_view_declaration_changed_requires_new_execution")
    return {"sha256": original.digest(left), "bytes": len(left),
            "claim": "identical_executed_declaration_in_original_and_consumer"}


def verify_reviewed_maps(before: dict[str, str], after: dict[str, str], review: dict,
                         producer: str, run_id: str) -> tuple[dict, list]:
    previous_scope = dict(after)
    for path, entry in HANDOFF_SOURCE_REVIEW.items():
        require(before.get(path) == entry["beforeGitBlob"] and
                after.get(path) == entry["afterGitBlob"], "unreviewed_handoff_source_" + path)
        previous_scope[path] = before[path]
    # The original verifier still requires every other source difference to
    # match its exact existing per-file review. No wildcard or directory is
    # removed from that closure. The two changed files are reported separately,
    # never included in the map described as unchanged.
    unchanged, entries = original.verify_reviewed_source_maps(
        before, previous_scope, review, producer, run_id)
    return {path: blob for path, blob in unchanged.items()
            if path not in HANDOFF_SOURCE_REVIEW}, entries


def verify_sources(producer: str, consumer: str, run_id: str, review_path: Path,
                   root: Path = ROOT) -> dict:
    before, after = original.source_tree(producer, root), original.source_tree(consumer, root)
    review_bytes = review_path.read_bytes()
    unchanged, entries = verify_reviewed_maps(before, after, json.loads(review_bytes), producer, run_id)
    declaration = verify_embedded_text_view(
        original.producer_file(producer, EDITOR, root), original.producer_file(consumer, EDITOR, root))
    require(declaration["sha256"] == TEXT_VIEW_SHA256, "reviewed_text_view_declaration_identity_changed")
    new_test = original.git("rev-parse", consumer + ":" + NEW_TEST, root=root).decode().strip()
    require(new_test == NEW_TEST_GIT_BLOB, "fresh_handoff_test_source_requires_review")
    protected = [*original.PROTECTED_PATHS, NEW_TEST, *HELPERS]
    dirty = original.git("diff", "--name-only", "-z", "HEAD", "--", *protected, root=root)
    untracked = original.git("ls-files", "--others", "--exclude-standard", "-z",
                             "--", *protected, root=root)
    require(all(not path or path.decode("utf-8") == original.EXCLUDED_SOURCE
                for path in (dirty + untracked).split(b"\0")), "tested_worktree_source_is_dirty")
    return {
        "unchangedSourceGitBlobs": unchanged,
        "previousSourceReviewSHA256": original.digest(review_bytes),
        "previousReviewedUnexecutedChanges": entries,
        "handoffSourceReview": HANDOFF_SOURCE_REVIEW,
        "unchangedEmbeddedAnyNativeTextView": declaration,
        "freshHandoffTestGitBlob": new_test,
        "verificationSources": {path: original.digest((root / path).read_bytes()) for path in HELPERS},
    }


def selected_original_cases(receipt: dict) -> dict[str, str]:
    expected, selected, observed = retained_methods(), {}, set()
    for identifier, result in receipt["actualCases"].items():
        matches = [method for method in expected
                   if re.search(r"(?:^|/)" + re.escape(method) + r"(?:\(|/|$)", identifier)]
        if not matches:
            continue
        require(len(matches) == 1 and matches[0] not in observed and result == "Passed",
                "ambiguous_or_failed_retained_case")
        observed.add(matches[0]); selected[identifier] = result
    require(observed == expected and len(selected) == 8, "missing_retained_named_case")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--producer-commit", required=True)
    parser.add_argument("--producer-run", required=True)
    parser.add_argument("--consumer-simulator", required=True, type=Path)
    parser.add_argument("--consumer-xcode-version", required=True, type=Path)
    parser.add_argument("--reviewed-source-changes", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "profile": PROFILE,
              "scope": "verified_prior_uikit_subset_reuse", "testsExecutedThisRun": 0,
              "fullAcceptance": False, "producerCommit": args.producer_commit,
              "producerRunID": args.producer_run, "runnerSHA256": original.digest(Path(__file__).read_bytes()),
              "claimBoundary": "Only eight unchanged marked-text/renderer methods are retained from the original fourteen-method execution. The six changed focus methods require new execution; the repaired native UI journey remains independently required."}
    try:
        consumer = original.git("rev-parse", "HEAD", root=ROOT).decode().strip()
        record["consumerCommit"] = consumer
        receipt = original.verify_evidence(args.evidence, args.producer_commit, args.producer_run)
        selected = selected_original_cases(receipt)
        source_proof = verify_sources(args.producer_commit, consumer, args.producer_run,
                                      args.reviewed_source_changes)
        before_simulator, after_simulator = original.read_json(args.evidence / "simulator.json"), original.read_json(args.consumer_simulator)
        require(all(before_simulator.get(key) and before_simulator[key] == after_simulator.get(key)
                    for key in ("runtime", "deviceType")), "simulator_platform_changed_requires_new_execution")
        require((args.evidence / "xcode-version.txt").read_text().strip() ==
                args.consumer_xcode_version.read_text().strip(), "apple_toolchain_changed_requires_new_execution")
        destination = args.output.parent / "reused-ui-ios-unaffected-eight"
        require(destination.resolve() != args.evidence.resolve(), "original_evidence_must_be_preserved")
        destination.mkdir(parents=True, exist_ok=True)
        original_files = {}
        for name in original.FILES:
            shutil.copyfile(args.evidence / name, destination / name)
            original_files[name] = original.digest((destination / name).read_bytes())
        record.update(status="VERIFIED_REUSE", originalExecutedCount=14, reusedCount=8,
                      reusedMethods=sorted(retained_methods()), reusedOriginalCases=selected,
                      notReusedAffectedMethods=sorted(affected_methods()),
                      requiredFreshProfile=FRESH_PROFILE, requiredFreshCount=10,
                      originalReceiptPath="reused-ui-ios-unaffected-eight/" + original.RECEIPT,
                      originalFiles=original_files, originalDevice=receipt["device"], sourceProof=source_proof)
    except Exception as error:
        record["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record.items() if key != "sourceProof"}, indent=2))
    return 0 if record["status"] == "VERIFIED_REUSE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
