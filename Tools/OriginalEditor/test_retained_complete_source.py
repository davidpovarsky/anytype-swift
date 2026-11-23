"""Synthetic retained-admission mutation controls; no Apple execution claim."""
import copy
import json
import unittest
from framework_profile import HERE
from run_source_controls import EXPECTED_IDS
from admit_retained_source_controls import validate_retained, validate_shared_retained

ROOT = HERE.parents[1]
PACKET = ROOT / "docs/pinkha/torah-integration/evidence/original-editor-install-name-20261122/admission"

class RetainedCompleteSourceControls(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((PACKET / "INPUTS.json").read_text())
        self.original = json.loads((PACKET / "original-source-before.json").read_text())
        self.historical = json.loads((PACKET / "original-source-controls-result.json").read_text())
        self.current = copy.deepcopy(self.original)
        for key, change in self.plan["reviewed_product_source_changes"].items():
            self.current[key] = copy.deepcopy(change["after"])
        self.current["reviewed_complete_source_sha"] = self.plan["complete_product_source_sha"]
        for path, change in self.plan["reviewed_source_input_changes"].items():
            self.current["source_inputs"][path] = copy.deepcopy(change["after"])

    def verify(self):
        return validate_retained(self.plan, self.historical, self.original, self.current, EXPECTED_IDS)

    def test_explicit_complete_continuation_retains_only_historical_credit(self):
        value = self.verify()
        self.assertTrue(value["historical_only"])
        self.assertFalse(value["whole_suite_replayed"])
        self.assertEqual(value["original_source_sha"], "edce5b975b173059522f90adb71271fb95adf963")
        self.assertEqual(value["reviewed_complete_source_sha"], "4fd99f19b0ec361ba84ac4b2822cae10c6818f99")

    def test_changed_source_membership_requires_explicit_reviewed_delta(self):
        del self.plan["reviewed_product_source_changes"]["source_files"]
        with self.assertRaises(ValueError): self.verify()

    def test_foreign_complete_source_cannot_inherit_historical_credit(self):
        self.current["reviewed_complete_source_sha"] = "0" * 40
        with self.assertRaises(ValueError): self.verify()

    def test_changed_controller_afterimage_cannot_reuse_reviewed_delta(self):
        path = "Tools/OriginalEditor/run_framework_acceptance.py"
        self.current["source_inputs"][path]["sha256"] = "0" * 64
        with self.assertRaises(ValueError): self.verify()

    def test_seven_actual_unchanged_symbol_controls_retain_only_their_source_credit(self):
        result = json.loads((PACKET / "shared-source-controls-5e0b51f951.json").read_text())
        value = validate_shared_retained(self.plan, result, self.current)
        self.assertEqual(len(value["retained_ids"]), 7)
        self.assertFalse(value["native_qualified"])
        self.assertFalse(value["replayed"])

    def test_incomplete_recorded_shared_results_cannot_be_retained(self):
        result = json.loads((PACKET / "shared-source-controls-5e0b51f951.json").read_text())
        result["passed_ids"].pop()
        with self.assertRaises(ValueError):
            validate_shared_retained(self.plan, result, self.current)

    def test_changed_shared_symbol_implementation_requires_new_controls(self):
        result = json.loads((PACKET / "shared-source-controls-5e0b51f951.json").read_text())
        self.current["source_inputs"]["Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_shared_retained(self.plan, result, self.current)
