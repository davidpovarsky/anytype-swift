import copy
from pathlib import Path
import unittest
import text_native_ack as ack

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "AnyTypeTests/Pinkha/PinkhaNativeTextAcknowledgementTests.swift"

class TextNativeAcknowledgementControls(unittest.TestCase):
    def valid_result(self):
        return dict(status="PASS", passed=7, failed=0, skipped=0,
                    selected=ack.METHODS.copy(),
                    actual_methods={name + "()": "Passed" for name in ack.METHODS})

    def test_original_lane_does_not_repeat_components(self):
        self.assertEqual(ack.resolve_lane("hanlin-native"), ("hanlin-native", False))
        self.assertEqual(ack.resolve_lane(ack.LANE), ("hanlin-native", True))
        self.assertEqual(ack.resolve_lane("editor"), ("editor", False))
        self.assertEqual(ack.resolve_lane("retained-heart-release"), ("retained-heart-release", False))

    def test_exact_current_source_selects_only_seven_new_methods(self):
        self.assertEqual(ack.validate_source(SOURCE.read_text(encoding="utf-8")), ack.METHODS)
        contract = ack.source_contract(ROOT)
        self.assertEqual(contract["expected_methods"], 7)
        self.assertEqual(contract["scope"], "CONTROLLED_NATIVE_SERVICE_COMPONENTS")
        self.assertEqual(len(contract["sha256"]), 64)

    def test_missing_duplicate_extra_and_parameterized_declarations_fail(self):
        source = SOURCE.read_text(encoding="utf-8")
        first = ack.METHOD_NAMES[0]
        mutations = [
            source.replace("func " + first, "func renamedCase", 1),
            source + "\n@Test func " + first + "() {}\n",
            source + "\n@Test func unreviewedCase() {}\n",
            source.replace("func " + first + "()", "func " + first + "(unexpected: Bool)", 1),
        ]
        for mutation in mutations:
            with self.subTest(length=len(mutation)):
                with self.assertRaises(ValueError):
                    ack.validate_source(mutation)

    def test_complete_actual_result_keeps_component_limit(self):
        qualified = ack.qualify_result(self.valid_result())
        self.assertEqual(qualified["passed"], 7)
        self.assertFalse(qualified["real_native_persistence_accepted"])

    def test_incomplete_skipped_or_relabelled_execution_fails(self):
        variants = []
        for key, value in [("passed", 6), ("passed", True), ("failed", 1),
                           ("failed", False), ("skipped", 1), ("skipped", False),
                           ("status", "NOT_RUN")]:
            result = self.valid_result()
            result[key] = value
            variants.append(result)
        missing = self.valid_result()
        missing["actual_methods"].pop(next(iter(missing["actual_methods"])))
        variants.append(missing)
        wrong = self.valid_result()
        key = next(iter(wrong["actual_methods"]))
        wrong["actual_methods"]["OtherSuite/otherMethod()"] = wrong["actual_methods"].pop(key)
        variants.append(wrong)
        failed = self.valid_result()
        failed["actual_methods"][next(iter(failed["actual_methods"]))] = "Failed"
        variants.append(failed)
        unselected = self.valid_result()
        unselected["selected"] = list(reversed(unselected["selected"]))
        variants.append(unselected)
        for result in variants:
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    ack.qualify_result(result)

if __name__ == "__main__":
    unittest.main()
