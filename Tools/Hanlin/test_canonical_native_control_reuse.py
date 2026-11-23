"""New admission controls only; never execute the original 69 controller methods."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import retain_canonical_native_controls as gate

ROOT = Path(__file__).resolve().parents[2]


def copy_inputs(destination):
    policy = json.loads((ROOT / gate.POLICY_PATH).read_text())
    original = json.loads((ROOT / policy["owner_manifest_path"]).read_text())
    names = {gate.POLICY_PATH, policy["owner_helper_path"], policy["owner_manifest_path"],
             policy["import_receipt"]["path"], *policy["source_inputs"],
             *[item["path"] for item in original["proof_files"]]}
    extension = policy["observer_budget_extension"]
    budget = json.loads((ROOT / extension["path"]).read_text())
    names.update({extension["path"], budget["control"]["path"],
                  *[item["path"] for item in budget["proof_files"]]})
    for key in ("observer_diagnostics_extension", "source_scan_extension"):
        item = policy[key]
        extension_proof = json.loads((ROOT / item["path"]).read_text())
        names.update({item["path"], extension_proof["control"]["path"],
                      *[entry["path"] for entry in extension_proof["proof_files"]]})
    for name in names:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return policy


class CanonicalNativeControlReuseTests(unittest.TestCase):
    def test_current_69_bind_retained62_and_seven_fresh_mapping_controls_without_execution(self):
        result = gate.verify(ROOT)
        self.assertEqual(result["current_control_methods"], 69)
        self.assertEqual(result["retained_original_methods"], 54)
        self.assertEqual(result["requalified_changed_original_methods"], 8)
        self.assertEqual(result["unchanged_methods_retained"], 61)
        self.assertEqual(result["qualified_observer_methods"], 7)
        self.assertEqual(result["controller_methods_requalified_this_update"], 7)
        self.assertEqual(result["controller_methods_reused_this_update"], 62)
        self.assertEqual(sum(item["proof_batch"] == "canonical-source-scans-affected-seven"
                             for item in result["catalog"]), 7)
        self.assertEqual(result["controller_methods_executed_now"], 0)
        self.assertEqual(result["product_tests_executed_now"], 0)
        self.assertEqual(len(result["source_inputs"]), 29)
        self.assertTrue(result["original_failure_preserved"])
        self.assertEqual(result["supplemental_observer_budget"]["control_methods"], 2)
        self.assertEqual(result["supplemental_observer_budget"]["control_cases"], 5)
        self.assertEqual(result["supplemental_observer_budget"]["methods_executed_now"], 0)
        self.assertFalse({"test_hanlin_ui_runtime", "test_hanlin_acceptance_evidence"} & set(sys.modules))

    def test_changed_parallel_source_or_named_result_cannot_inherit_source_scan_proof(self):
        policy = json.loads((ROOT / gate.POLICY_PATH).read_text())
        proof = json.loads((ROOT / policy["source_scan_extension"]["path"]).read_text())
        for name in (proof["source_path"], proof["affected_log"], proof["trace"]):
            with self.subTest(path=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                copy_inputs(root)
                path = root / name
                path.write_bytes(path.read_bytes() + b"\nUNREVIEWED_SOURCE_OR_EVIDENCE_CHANGE\n")
                with self.assertRaises((ValueError, RuntimeError)):
                    gate.verify(root)

    def test_changed_supplemental_control_or_trace_cannot_admit_current_budget(self):
        policy = json.loads((ROOT / gate.POLICY_PATH).read_text())
        budget = json.loads((ROOT / policy["observer_budget_extension"]["path"]).read_text())
        for name in (budget["control"]["path"], budget["after_log"],
                     budget["case_traces"]["late-process-replacement"]):
            with self.subTest(path=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                copy_inputs(root)
                path = root / name
                path.write_bytes(path.read_bytes() + b"\nUNREVIEWED_PROOF_CHANGE\n")
                with self.assertRaises((ValueError, RuntimeError)):
                    gate.verify(root)

    def test_changed_observer_and_candidate_guard_do_not_inherit_proof(self):
        for name in ("Tools/PinkhaSimulatorGate/hanlin_ui_runtime.py", "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py"):
            with self.subTest(path=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                copy_inputs(root)
                path = root / name
                path.write_bytes(path.read_bytes() + b"\nCHANGED_UNREVIEWED_INPUT = True\n")
                with self.assertRaises((ValueError, RuntimeError)):
                    gate.verify(root)

    def test_forged_replacement_hash_cannot_expand_the_fixed_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = copy_inputs(root)
            name = "Tools/Hanlin/run_host_tests.py"
            path = root / name
            path.write_bytes(path.read_bytes() + b"\nUNREVIEWED_EXECUTION_CHANGE = True\n")
            policy["source_deltas"][name]["current_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            (root / gate.POLICY_PATH).write_text(json.dumps(policy))
            with self.assertRaisesRegex(ValueError, "Changed native-control admission"):
                gate.verify(root)

    def test_original_log_mutation_and_linked_proof_are_rejected(self):
        for linked in (False, True):
            with self.subTest(linked=linked), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                policy = copy_inputs(root)
                original = json.loads((root / policy["owner_manifest_path"]).read_text())
                log = root / original["batches"][0]["log"]
                if linked:
                    kept = root / "unchanged-log"
                    log.rename(kept)
                    log.symlink_to(kept)
                else:
                    log.write_bytes(log.read_bytes().replace(b"... ok", b"... FAIL", 1))
                with self.assertRaises((ValueError, RuntimeError)):
                    gate.verify(root)


if __name__ == "__main__":
    unittest.main()
