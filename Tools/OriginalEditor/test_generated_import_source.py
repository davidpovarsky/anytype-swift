"""New generated-source boundary controls; no compiler or native qualification."""
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import generated_import_source as boundary
from framework_profile import read_manifest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Tools/OriginalEditor/GeneratedImport"
ADOPTION = json.loads((BASE / "SOURCE_ADOPTION.json").read_bytes())
INDEX = json.loads((BASE / "GENERATED_OUTPUT_INDEX.json").read_bytes())
HANDOFF = json.loads((BASE / "ACTUAL_GENERATED_UNION_HANDOFF.json").read_bytes())


class GeneratedSourceControls(unittest.TestCase):
    def documents(self, adoption=None, index=None, handoff=None):
        return boundary.validate_documents(
            copy.deepcopy(ADOPTION) if adoption is None else adoption,
            copy.deepcopy(INDEX) if index is None else index,
            copy.deepcopy(HANDOFF) if handoff is None else handoff)

    def test_actual_committed_733_postimages_have_no_execution_credit(self):
        result = boundary.verify_generated_source(ROOT, read_manifest())
        self.assertEqual(result["working_generated_files"], 733)
        self.assertEqual(result["committed_generated_blobs"], 733)
        self.assertEqual(result["changed_source_paths"], 41)
        self.assertEqual(result["postimage_source"], boundary.POSTIMAGE)
        self.assertFalse(result["native_or_swift_qualification_granted"])
        self.assertEqual(result["lib_abi_qualification"], "NOT_ASSESSED_BY_SOURCE_OBSERVATION")

    def test_complete_original_baseline_is_kept_separate_from_generated_modules(self):
        profile = read_manifest()
        self.assertEqual(profile["original_trees"]["Modules"], "4467772e9ac8bea7fc37080b4502978fb0a93322")
        self.assertEqual(profile["generated_import_source"]["composed_product_trees"]["Modules"],
                         "94f2871225cf6da9e724e600262c21a05b3b6550")
        before, after, changes = self.documents()
        self.assertEqual((len(before), len(after), len(changes)), (695, 733, 41))

    def test_missing_middleware_member_is_rejected(self):
        index = copy.deepcopy(INDEX)
        index["middleware"].pop()
        with self.assertRaisesRegex(ValueError, "family inventory differs"):
            self.documents(index=index)

    def test_extra_generated_family_cannot_enter_the_sdk(self):
        index = copy.deepcopy(INDEX)
        index["unreviewed"] = []
        with self.assertRaisesRegex(ValueError, "family inventory differs"):
            self.documents(index=index)

    def test_expanded_scope_cannot_alias_original_application_source(self):
        adoption = copy.deepcopy(ADOPTION)
        adoption["scopes"].append("Anytype/Sources")
        with self.assertRaisesRegex(ValueError, "source lineage differs"):
            self.documents(adoption=adoption)

    def test_foreign_original_preimage_revision_is_rejected(self):
        adoption = copy.deepcopy(ADOPTION)
        adoption["original_generated_preimage_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "source lineage differs"):
            self.documents(adoption=adoption)

    def test_generation_source_cannot_grant_native_acceptance(self):
        adoption = copy.deepcopy(ADOPTION)
        adoption["complete_sdk_native_acceptance"] = True
        with self.assertRaisesRegex(ValueError, "provenance or acceptance"):
            self.documents(adoption=adoption)

    def test_changed_working_body_cannot_hide_behind_committed_blob(self):
        rows = copy.deepcopy(ADOPTION["after"])
        rows[0]["sha256"] = "0" * 64
        with mock.patch.object(boundary, "working_entries", return_value=rows):
            with self.assertRaisesRegex(ValueError, "Working generated postimages differ"):
                boundary.verify_generated_source(ROOT, read_manifest())

    def test_changed_head_blob_cannot_hide_behind_matching_working_body(self):
        original = boundary.git_entries
        def drift(root, revision):
            rows = original(root, revision)
            if revision == "HEAD":
                rows[next(iter(rows))] = "0" * 40
            return rows
        with mock.patch.object(boundary, "git_entries", side_effect=drift):
            with self.assertRaisesRegex(ValueError, "Committed generated postimages differ"):
                boundary.verify_generated_source(ROOT, read_manifest())

    def test_wrong_composed_tree_cannot_reuse_source_rows(self):
        profile = read_manifest()
        profile["generated_import_source"]["composed_product_trees"]["Modules"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "Composed SDK product tree differs"):
            boundary.verify_generated_source(ROOT, profile)


if __name__ == "__main__":
    unittest.main()
