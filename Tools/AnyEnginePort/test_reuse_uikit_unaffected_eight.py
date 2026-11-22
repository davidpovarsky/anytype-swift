#!/usr/bin/env python3
"""Narrow negative controls for eight-method retention and fresh focus admission."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

import reuse_uikit_execution as original
import reuse_uikit_unaffected_eight as retained
import verify_focus_handoff_execution as fresh
import verify_native_test_execution as execution


class UIKitSplitAdmissionTests(unittest.TestCase):
    def test_embedded_executed_text_view_is_byte_exact_and_boundaries_are_unique(self):
        current = (retained.ROOT / retained.EDITOR).read_bytes()
        outside = current.replace(b"public struct AnyNativeEditor:", b"public struct ChangedController:", 1)
        value = retained.verify_embedded_text_view(current, outside)
        self.assertEqual(value["sha256"], retained.TEXT_VIEW_SHA256)
        self.assertEqual(value["bytes"], 4607)
        changed = current.replace(b"var blockID: String?", b"var blockID: String? = nil", 1)
        with self.assertRaisesRegex(RuntimeError, "executed_text_view_declaration_changed"):
            retained.verify_embedded_text_view(current, changed)
        for malformed in (current + retained.TEXT_VIEW_START,
                          current.replace(retained.TEXT_VIEW_END, b"missing declaration", 1)):
            with self.assertRaisesRegex(RuntimeError, "ambiguous_embedded"):
                retained.verify_embedded_text_view(current, malformed)

    def test_fixed_handoff_review_does_not_excuse_other_changed_dependencies(self):
        producer, run_id = "a" * 40, "44942212731"
        before = {path: "b" * 40 for path in execution.SOURCE_PATHS[original.PROFILE]}
        before.update({path: entry["beforeGitBlob"] for path, entry in retained.HANDOFF_SOURCE_REVIEW.items()})
        reviewed = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift"
        renderer = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeTextRenderer.swift"
        before[reviewed], before[renderer] = "c" * 40, "d" * 40
        after = dict(before)
        after.update({path: entry["afterGitBlob"] for path, entry in retained.HANDOFF_SOURCE_REVIEW.items()})
        after[reviewed] = "e" * 40
        review = {"schemaVersion": 1, "profile": original.PROFILE, "producerCommit": producer,
                  "producerRunID": run_id, "claim": original.REVIEW_CLAIM,
                  "requiredMethods": sorted(execution.expected_methods(original.PROFILE)),
                  "testSourceGitBlobs": {path: before[path] for path in execution.SOURCE_PATHS[original.PROFILE]},
                  "reviewedChanges": [{"path": reviewed, "beforeGitBlob": before[reviewed],
                      "afterGitBlob": after[reviewed], "claim": original.REVIEW_CLAIM,
                      "reason": "The prior review binds this exact unexecuted presentation path; component fixtures do not construct it."}]}
        unchanged, entries = retained.verify_reviewed_maps(before, after, review, producer, run_id)
        self.assertEqual(unchanged[renderer], before[renderer])
        self.assertFalse(set(retained.HANDOFF_SOURCE_REVIEW) & set(unchanged))
        self.assertEqual(len(entries), 1)
        for path in (retained.EDITOR, retained.FOCUS, renderer,
                     execution.SOURCE_PATHS[original.PROFILE][0],
                     "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/UnexpectedSource.swift"):
            changed = dict(after); changed[path] = "f" * 40
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                retained.verify_reviewed_maps(before, changed, review, producer, run_id)
        relabelled = copy.deepcopy(review); relabelled["claim"] = "PASS"
        with self.assertRaises(RuntimeError):
            retained.verify_reviewed_maps(before, after, relabelled, producer, run_id)

    def test_original_fourteen_cases_yield_only_eight_reusable_cases(self):
        receipt = {"actualCases": {name + "()": "Passed"
                   for name in execution.expected_methods(original.PROFILE)}}
        selected = retained.selected_original_cases(receipt)
        self.assertEqual(len(selected), 8)
        self.assertEqual(len(retained.affected_methods()), 6)
        self.assertFalse(any("Focus" in name for name in selected))
        first = sorted(selected)[0]
        for alteration in ("missing", "failed", "duplicate"):
            changed = copy.deepcopy(receipt)
            if alteration == "missing": changed["actualCases"].pop(first)
            elif alteration == "failed": changed["actualCases"][first] = "Failed"
            else: changed["actualCases"]["OtherTarget/" + first] = "Passed"
            with self.subTest(alteration=alteration), self.assertRaises(RuntimeError):
                retained.selected_original_cases(changed)

    def test_fresh_profile_rejects_old_fourteen_wrong_counts_skips_names_and_device(self):
        fresh.register_profile()
        methods = sorted(execution.expected_methods(fresh.PROFILE))
        udid = "owned-simulator"
        summary = {"totalTestCount": 10, "passedTests": 10, "failedTests": 0, "skippedTests": 0,
                   "devicesAndConfigurations": [{"device": {"deviceId": udid, "osVersion": "27.2",
                       "osBuildNumber": "24B8117", "architecture": "arm64"}}]}
        tree = {"children": [{"nodeType": "Test Case", "nodeIdentifier": method + "()", "result": "Passed"}
                              for method in methods]}
        self.assertEqual(fresh.validate(summary, tree, udid)["counts"]["totalTestCount"], 10)
        for alteration in ("old14", "bool", "skip", "missing", "duplicate", "wrong_name", "device", "x86"):
            changed_summary, changed_tree = copy.deepcopy(summary), copy.deepcopy(tree)
            if alteration == "old14":
                changed_summary.update(totalTestCount=14, passedTests=14)
                changed_tree["children"] = [{"nodeType": "Test Case", "nodeIdentifier": method + "()", "result": "Passed"}
                    for method in execution.expected_methods(original.PROFILE)]
            elif alteration == "bool": changed_summary["failedTests"] = False
            elif alteration == "skip": changed_summary.update(passedTests=9, skippedTests=1)
            elif alteration == "missing": changed_tree["children"].pop()
            elif alteration == "duplicate": changed_tree["children"][-1] = changed_tree["children"][0]
            elif alteration == "wrong_name": changed_tree["children"][-1]["nodeIdentifier"] = "Unknown/testUnrelated()"
            elif alteration == "device": changed_summary["devicesAndConfigurations"][0]["device"]["deviceId"] = "foreign"
            elif alteration == "x86": changed_summary["devicesAndConfigurations"][0]["device"]["architecture"] = "x86_64"
            with self.subTest(alteration=alteration), self.assertRaises(RuntimeError):
                fresh.validate(changed_summary, changed_tree, udid)

    def test_fresh_receipt_requires_the_exact_consumer_subset_and_source_review(self):
        consumer = "a" * 40
        record = {"status": "VERIFIED_REUSE", "profile": retained.PROFILE,
                  "scope": "verified_prior_uikit_subset_reuse", "consumerCommit": consumer,
                  "originalExecutedCount": 14, "reusedCount": 8, "testsExecutedThisRun": 0,
                  "fullAcceptance": False, "reusedMethods": sorted(retained.retained_methods()),
                  "notReusedAffectedMethods": sorted(retained.affected_methods()),
                  "requiredFreshProfile": fresh.PROFILE, "requiredFreshCount": 10,
                  "runnerSHA256": original.digest((retained.ROOT / retained.SELF).read_bytes()),
                  "sourceProof": {"handoffSourceReview": retained.HANDOFF_SOURCE_REVIEW,
                      "unchangedEmbeddedAnyNativeTextView": {"sha256": retained.TEXT_VIEW_SHA256},
                      "freshHandoffTestGitBlob": retained.NEW_TEST_GIT_BLOB}}
        fresh.verify_retained_record(record, consumer)
        for key, value in (("consumerCommit", "b" * 40), ("reusedCount", 14),
                           ("testsExecutedThisRun", False), ("fullAcceptance", True),
                           ("runnerSHA256", "f" * 64), ("sourceProof", {})):
            changed = copy.deepcopy(record); changed[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                fresh.verify_retained_record(changed, consumer)


if __name__ == "__main__":
    unittest.main()
