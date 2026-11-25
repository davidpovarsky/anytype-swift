"""Exact retained native-policy controls; these do not grant product acceptance."""
import copy
import json
from pathlib import Path
import unittest

from donor_abi_input import (
    CLOSURE, DONOR, FRESH_CLOSURE, FRESH_DONOR, FRESH_POLICY, POLICY, validate_policy,
)


class FreshDonorPolicyControls(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.current = json.loads((self.root / FRESH_POLICY).read_text())
        self.current_binding = {"path": FRESH_POLICY, "source_sha": FRESH_DONOR}

    def test_exact_current_and_historical_policies_remain_distinct(self):
        self.assertEqual(validate_policy(self.current, self.current_binding), self.current)
        old = json.loads((self.root / POLICY).read_text())
        self.assertEqual(validate_policy(old, {"path": POLICY, "source_sha": DONOR}), old)
        self.assertEqual(len(CLOSURE), 8)
        self.assertEqual(len(FRESH_CLOSURE), 14)

    def test_source_or_schema_cannot_be_relabelled(self):
        for key, value in (("source_sha", DONOR), ("source_sha", "0" * 40),
                           ("schema", "otzaria.native-abi-donor-policy/1")):
            altered = copy.deepcopy(self.current)
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_policy(altered, self.current_binding)

    def test_missing_native_generated_or_verifier_input_rejected(self):
        for name in FRESH_CLOSURE:
            altered = copy.deepcopy(self.current)
            del altered["unchanged_git_inputs"][name]
            with self.subTest(path=name), self.assertRaises(ValueError):
                validate_policy(altered, self.current_binding)

    def test_extra_or_substituted_input_is_not_equivalence(self):
        altered = copy.deepcopy(self.current)
        altered["unchanged_git_inputs"]["Anytype.xcodeproj"] = "0" * 40
        with self.assertRaises(ValueError):
            validate_policy(altered, self.current_binding)

    def test_all_four_original_owner_receipts_are_required(self):
        for name in self.current["receipts"]:
            altered = copy.deepcopy(self.current)
            del altered["receipts"][name]
            with self.subTest(role=name), self.assertRaises(ValueError):
                validate_policy(altered, self.current_binding)

    def test_reference_cannot_claim_new_runtime_acceptance(self):
        for name in ("native_tests_rerun", "new_sdk_acceptance_granted"):
            altered = copy.deepcopy(self.current)
            altered[name] = True
            with self.subTest(claim=name), self.assertRaises(ValueError):
                validate_policy(altered, self.current_binding)

    def test_arbitrary_or_crossed_donor_path_rejected(self):
        for binding in ({"path": "../abi.json", "source_sha": FRESH_DONOR},
                        {"path": POLICY, "source_sha": FRESH_DONOR},
                        {"path": FRESH_POLICY, "source_sha": DONOR}):
            with self.subTest(binding=binding), self.assertRaises(ValueError):
                validate_policy(self.current, binding)


if __name__ == "__main__":
    unittest.main()
