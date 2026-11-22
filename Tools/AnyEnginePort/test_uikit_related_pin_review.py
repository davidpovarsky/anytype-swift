"""Focused admission controls for the exact six related-authority/pin differences."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

import reuse_uikit_execution as reuse

REVIEW_PATH = Path(__file__).parent / "reviews/uikit14-unexecuted-source-changes-20261122.json"
NEW_PATHS = frozenset({
    "Modules/PinkhaAnyUI/Package.resolved",
    "Modules/PinkhaAnyUI/Package.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyTorahPresentationBridge.swift",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyTorahRelatedReadFailure.swift",
    "Modules/PinkhaKit/Package.swift",
    "Modules/PinkhaTorahPresentation/Package.swift",
})
RENDERER = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeTextRenderer.swift"
RENDERER_BLOB = "6516f0744f06854ac02141d94ed88106c564c99f"


class RelatedPinUIKitReviewTests(unittest.TestCase):
    def setUp(self):
        self.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        self.original = dict(self.review["testSourceGitBlobs"])
        self.original[RENDERER] = RENDERER_BLOB
        for entry in self.review["reviewedChanges"]:
            if entry["beforeGitBlob"] is not None:
                self.original[entry["path"]] = entry["beforeGitBlob"]
        self.current = dict(self.original)
        for entry in self.review["reviewedChanges"]:
            self.current[entry["path"]] = entry["afterGitBlob"]

    def verify(self, review=None, current=None):
        return reuse.verify_reviewed_source_maps(
            self.original, self.current if current is None else current,
            self.review if review is None else review,
            self.review["producerCommit"], self.review["producerRunID"])

    def test_six_new_paths_remain_reviewed_differences(self):
        unchanged, reviewed = self.verify()
        self.assertEqual(len(reviewed), 14)
        self.assertTrue(NEW_PATHS <= {entry["path"] for entry in reviewed})
        self.assertTrue(NEW_PATHS.isdisjoint(unchanged))
        self.assertEqual(unchanged[RENDERER], RENDERER_BLOB)
        self.assertEqual(set(unchanged) | {entry["path"] for entry in reviewed}, set(self.current))

    def test_each_new_path_requires_its_exact_before_and_after_blob(self):
        for path in sorted(NEW_PATHS):
            for key in ("beforeGitBlob", "afterGitBlob"):
                review = deepcopy(self.review)
                entry = next(item for item in review["reviewedChanges"] if item["path"] == path)
                entry[key] = "f" * 40
                with self.subTest(path=path, key=key), self.assertRaisesRegex(
                        RuntimeError, "reviewed_source_blob_mismatch"):
                    self.verify(review=review)

    def test_unknown_dependency_or_future_source_cannot_be_excused(self):
        for path in ("Modules/PinkhaAnyEngine/Package.swift",
                     "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/FutureSharedBehavior.swift"):
            review = deepcopy(self.review)
            review["reviewedChanges"].append({
                "path": path, "beforeGitBlob": None, "afterGitBlob": "e" * 40,
                "claim": reuse.REVIEW_CLAIM,
                "reason": "This fabricated future change has no approved execution-dependency review and must never qualify."
            })
            with self.subTest(path=path), self.assertRaisesRegex(
                    RuntimeError, "unreviewable_or_duplicate_source_change"):
                self.verify(review=review, current={**self.current, path: "e" * 40})

    def test_related_pin_review_cannot_relabel_changed_behavior_as_executed(self):
        for path in (None, *sorted(NEW_PATHS)):
            review = deepcopy(self.review)
            target = review if path is None else next(
                item for item in review["reviewedChanges"] if item["path"] == path)
            target["claim"] = "changed_dependency_passed_in_original_run"
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                self.verify(review=review)


if __name__ == "__main__":
    unittest.main()
