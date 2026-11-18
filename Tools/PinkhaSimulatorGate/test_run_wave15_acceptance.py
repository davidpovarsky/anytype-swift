"""Controls for real-fixture selection; these are not application acceptance."""
import unittest
from run_wave15_acceptance import plan, fixture_environment


class AcceptanceSelectionTests(unittest.TestCase):
    def test_english_label_methods_cannot_claim_hebrew_coverage(self):
        for lane in ["inspector", "properties"]:
            with self.subTest(lane=lane), self.assertRaisesRegex(ValueError, "English labels"):
                plan(lane, "ipad", "he")
        self.assertEqual(plan("editor", "ipad", "he")["expected_ui_executions"], 2)

    def test_named_selections_remain_partial_acceptance(self):
        for lane, count in [("inspector", 5), ("properties", 5), ("editor", 2)]:
            with self.subTest(lane=lane):
                value = plan(lane, "iphone", "en")
                self.assertEqual(len(set(value["methods"])), count)
                self.assertFalse(value["full_matrix_accepted"])
                self.assertFalse(value["release_accepted"])

    def test_missing_or_reused_real_object_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            fixture_environment("inspector", {"spaceId": "s", "universalDocuments": {"page": "p"}, "manySourcesDocument": "p"}, "en")
        with self.assertRaisesRegex(ValueError, "three distinct"):
            fixture_environment("editor", {"spaceId": "s", "pinkhaObjectId": "p", "noteObjectId": "n", "pageObjectId": "p"}, "he")
        with self.assertRaisesRegex(ValueError, "Space"):
            fixture_environment("inspector", {"spaceId": "", "universalDocuments": {"page": "p"}, "manySourcesDocument": "d"}, "en")

    def test_editor_environment_uses_actual_persisted_fixture_ids(self):
        value = fixture_environment("editor", {"spaceId": "s", "pinkhaObjectId": "a", "noteObjectId": "b", "pageObjectId": "c"}, "he")
        self.assertEqual(value["PINKHA_ACCEPTANCE_DIRECTION"], "rtl")
        self.assertEqual(value["PINKHA_ACCEPTANCE_PINKHA_ID"], "a")
        self.assertEqual(value["PINKHA_ACCEPTANCE_NOTE_ID"], "b")
        self.assertEqual(value["PINKHA_ACCEPTANCE_PAGE_ID"], "c")

    def test_obsolete_legacy_property_lane_is_not_selectable(self):
        with self.assertRaisesRegex(ValueError, "Unknown acceptance lane"):
            plan("canonical-properties", "ipad", "en")


if __name__ == "__main__":
    unittest.main()
