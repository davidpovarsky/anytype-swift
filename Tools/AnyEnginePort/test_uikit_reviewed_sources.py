"""Behavior controls for a fixed, per-blob unexecuted UIKit source review."""
from copy import deepcopy
import unittest

import reuse_uikit_execution as reuse
import verify_native_test_execution as execution


class ReviewedUIKitSourcesTests(unittest.TestCase):
    def setUp(self):
        self.producer = "1" * 40
        self.run_id = "44942212731"
        self.path = "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSerialTextEditQueue.swift"
        self.renderer = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeTextRenderer.swift"
        self.original = {path: "2" * 40 for path in execution.SOURCE_PATHS[reuse.PROFILE]}
        self.original.update({self.path: "3" * 40, self.renderer: "4" * 40})
        self.current = {**self.original, self.path: "5" * 40}
        self.review = {
            "schemaVersion": 1, "profile": reuse.PROFILE,
            "producerCommit": self.producer, "producerRunID": self.run_id,
            "claim": reuse.REVIEW_CLAIM,
            "requiredMethods": sorted(execution.expected_methods(reuse.PROFILE)),
            "testSourceGitBlobs": {path: self.original[path]
                                   for path in execution.SOURCE_PATHS[reuse.PROFILE]},
            "reviewedChanges": [{
                "path": self.path, "beforeGitBlob": "3" * 40, "afterGitBlob": "5" * 40,
                "claim": reuse.REVIEW_CLAIM,
                "reason": "These component methods construct UIKit text and focus fixtures; none constructs or calls the serial persistence queue."
            }]
        }

    def verify(self, review=None, current=None):
        return reuse.verify_reviewed_source_maps(
            self.original, self.current if current is None else current,
            self.review if review is None else review, self.producer, self.run_id)

    def test_reviewed_difference_is_separate_from_unchanged_sources(self):
        unchanged, reviewed = self.verify()
        self.assertNotIn(self.path, unchanged)
        self.assertEqual(unchanged[self.renderer], self.original[self.renderer])
        self.assertEqual(reviewed, self.review["reviewedChanges"])
        self.assertEqual(set(unchanged) | {entry["path"] for entry in reviewed}, set(self.current))

    def test_wrong_before_or_after_blob_is_refused(self):
        for key in ("beforeGitBlob", "afterGitBlob"):
            review = deepcopy(self.review)
            review["reviewedChanges"][0][key] = "6" * 40
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, "reviewed_source_blob_mismatch"):
                self.verify(review=review)

    def test_new_unreviewed_difference_is_refused(self):
        current = {**self.current,
                   "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyHostAuthorizedTorahOperationReader.swift": "7" * 40}
        with self.assertRaisesRegex(RuntimeError, "new_or_missing_source_difference_requires_review"):
            self.verify(current=current)

    def test_changed_renderer_cannot_be_added_to_review(self):
        review = deepcopy(self.review)
        review["reviewedChanges"].append({
            **review["reviewedChanges"][0], "path": self.renderer,
            "beforeGitBlob": "4" * 40, "afterGitBlob": "8" * 40
        })
        with self.assertRaisesRegex(RuntimeError, "unreviewable_or_duplicate_source_change"):
            self.verify(review=review, current={**self.current, self.renderer: "8" * 40})

    def test_pass_relabelling_is_refused_at_both_levels(self):
        for location in ("root", "entry"):
            review = deepcopy(self.review)
            target = review if location == "root" else review["reviewedChanges"][0]
            target["claim"] = "changed_source_passed_in_original_run"
            with self.subTest(location=location), self.assertRaises(RuntimeError):
                self.verify(review=review)

    def test_wrong_producer_or_method_inventory_is_refused(self):
        for key, value in (("producerCommit", "9" * 40),
                           ("producerRunID", "44948053285"),
                           ("requiredMethods", self.review["requiredMethods"][:-1])):
            review = deepcopy(self.review)
            review[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                self.verify(review=review)

    def test_duplicate_or_unchanged_entry_is_refused(self):
        duplicate = deepcopy(self.review)
        duplicate["reviewedChanges"].append(deepcopy(duplicate["reviewedChanges"][0]))
        with self.assertRaisesRegex(RuntimeError, "unreviewable_or_duplicate_source_change"):
            self.verify(review=duplicate)
        with self.assertRaisesRegex(RuntimeError, "new_or_missing_source_difference_requires_review"):
            self.verify(current=self.original)


if __name__ == "__main__":
    unittest.main()
