"""Exact reviewed source inventory controls; no native typecheck or runtime credit."""
import copy
import json
import unittest
from framework_profile import HERE, read_manifest, verify_complete_source


class CompleteSourceContinuationControls(unittest.TestCase):
    def setUp(self):
        self.profile = read_manifest()
        self.continuation = json.loads((HERE / "complete_source_continuation.json").read_text())

    def test_complete_original_source_and_facades_are_bound_without_native_credit(self):
        value = verify_complete_source(self.profile, self.continuation)
        self.assertEqual(len(value["source_files"]), 2256)
        self.assertEqual(len(value["framework_facade_sources"]), 20)
        self.assertIs(value["native_qualified"], False)

    def test_different_product_source_cannot_reuse_complete_continuation(self):
        self.continuation["reviewed_source_sha"] = "0" * 40
        with self.assertRaises(ValueError):
            verify_complete_source(self.profile, self.continuation)

    def test_missing_original_source_cannot_hide_behind_count_metadata(self):
        self.continuation["source_files"].pop()
        self.profile["original_swift_sources"] -= 1
        with self.assertRaises(ValueError):
            verify_complete_source(self.profile, self.continuation)

    def test_missing_account_facade_cannot_hide_behind_matching_profile(self):
        path = "OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift"
        self.continuation["framework_facade_sources"].remove(path)
        self.profile["framework_facade_sources"].remove(path)
        with self.assertRaises(ValueError):
            verify_complete_source(self.profile, self.continuation)

    def test_original_resources_cannot_change_with_matching_candidate_hash(self):
        self.continuation["reviewed_product_trees"]["Anytype/Resources"] = "1" * 40
        self.profile["original_trees"]["Anytype/Resources"] = "1" * 40
        with self.assertRaises(ValueError):
            verify_complete_source(self.profile, self.continuation)
