"""Source-bound lane routing controls, not native UI acceptance."""
import unittest
from run_wave15_acceptance import LANES, HANLIN_LANES, plan, preparation_environment
import hanlin_acceptance_evidence as document
import hanlin_selection_evidence as selection


class HanlinLaneRoutingTests(unittest.TestCase):
    def test_selection_uses_its_own_one_native_preparation_and_one_named_ui(self):
        actual = plan("hanlin-selection", "ipad", "en")
        self.assertEqual(actual["methods"], ["HanlinSelectionAcceptanceUITests/testRealSelectedBlockReadAndReturn"])
        self.assertEqual(actual["preparation"], "HanlinSelectionAcceptancePreparationTests/prepareSelectedBlockFixture")
        self.assertEqual((actual["expected_preparation_executions"], actual["expected_ui_executions"]), (1, 1))
        self.assertEqual(actual["build_configuration"], "Debug-Anytype")
        self.assertFalse(actual["release_accepted"])
        self.assertFalse(actual["full_matrix_accepted"])
        with self.assertRaisesRegex(ValueError, "English labels"):
            plan("hanlin-selection", "iphone", "he")

    def test_reused_native_preparation_receives_identical_source_run_and_attempt(self):
        actual = preparation_environment("hanlin-selection", "a" * 40, "42", "3")
        for suffix, value in [("SOURCE_SHA", "a" * 40), ("RUN_ID", "42"), ("RUN_ATTEMPT", "3")]:
            self.assertEqual(actual["PINKHA_HANLIN_SELECTION_" + suffix], value)
            self.assertEqual(actual["PINKHA_HANLIN_NATIVE_" + suffix], value)
        for name in ["PINKHA_PREPARE_HANLIN_SELECTION_UI", "PINKHA_HANLIN_NATIVE_PREPARATION",
                     "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION", "PINKHA_SIMULATOR_UI_DISPOSABLE"]:
            self.assertEqual(actual[name], "1")
        self.assertNotIn("PINKHA_HANLIN_NATIVE_UI", actual)
        self.assertNotIn("PINKHA_HANLIN_SELECTION_UI", actual)
        actual["PINKHA_PREPARE_HANLIN_SELECTION_UI"] = "changed"
        self.assertEqual(LANES["hanlin-selection"]["preparation_environment"]["PINKHA_PREPARE_HANLIN_SELECTION_UI"], "1")

    def test_selection_cannot_validate_the_document_receipt_or_reuse_its_fixture(self):
        self.assertIs(HANLIN_LANES["hanlin-native"][0], document)
        self.assertIs(HANLIN_LANES["hanlin-selection"][0], selection)
        self.assertEqual(HANLIN_LANES["hanlin-native"][1:],
                         ("pinkha-hanlin-native-result.json", "hanlin-native-result.json", "hanlin_native_receipt"))
        self.assertEqual(HANLIN_LANES["hanlin-selection"][1:],
                         ("pinkha-hanlin-selection-result.json", "hanlin-selection-result.json", "hanlin_selection_receipt"))
        self.assertNotEqual(LANES["hanlin-native"]["fixture"], LANES["hanlin-selection"]["fixture"])
        self.assertEqual(len(document.REQUIRED_CHECKS), 22)
        self.assertEqual(len(selection.REQUIRED_CHECKS), 9)

    def test_existing_document_and_inspector_preparation_do_not_enable_selection(self):
        old = preparation_environment("hanlin-native", "b" * 40, "51", "2")
        self.assertEqual(old["PINKHA_HANLIN_NATIVE_SOURCE_SHA"], "b" * 40)
        self.assertFalse(any("SELECTION" in key for key in old))
        inspector = preparation_environment("inspector", "b" * 40, "51", "2")
        self.assertEqual(inspector, {"PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"})
        self.assertEqual(plan("hanlin-native", "ipad", "en")["build_configuration"], "Debug-Anytype")


if __name__ == "__main__":
    unittest.main()
