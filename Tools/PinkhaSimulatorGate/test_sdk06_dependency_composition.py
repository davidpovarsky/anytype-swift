"""One new fixed dependency-composition admission control; no prior suites."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import sdk06_retained_controls as retained

ROOT = Path(__file__).resolve().parents[2]


class DependencyCompositionControls(unittest.TestCase):
    def test_exact_composed_dependencies_preserve_original_scopes_and_reject_unreviewed_source_or_events(self):
        contract = json.loads((ROOT / retained.ADMISSION_PATH).read_bytes())
        paths = {retained.ADMISSION_PATH}
        paths.update(row["path"] for row in contract["source_inputs"])
        paths.update(row["path"] for row in contract["proof_files"])
        with tempfile.TemporaryDirectory(prefix="sdk06-fixed-dependency-") as directory:
            app = Path(directory) / "app"; app.mkdir()
            for relative in sorted(paths):
                target = app / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            actual = retained.verify_retained_controls(app)
            dependency = actual["qualified_dependency_composition"]
            self.assertEqual(actual["current_control_methods"], 98)
            self.assertEqual(actual["fixed_composition"]["composition_methods_qualified"], 18)
            self.assertEqual(actual["sdk_qualified_kernel_profile"]["current_composition_methods_qualified"], 19)
            self.assertEqual(dependency["current_sdk_composition_methods"], 21)
            self.assertEqual(dependency["new_basename_consumer_methods"], 2)
            self.assertEqual(dependency["separate_coherent_dependency_methods"], 3)
            self.assertEqual(dependency["retained_kernel_methods"], 9)
            self.assertEqual(dependency["methods_executed_now"], 0)
            self.assertFalse(dependency["selector_admission_claimed"])
            self.assertFalse(dependency["product_acceptance_claimed"])
            self.assertEqual(actual["original_lane_conclusions"],
                             {"45096079315": "FAIL", "45087685319": "failure"})
            batches = dependency["batches"]
            self.assertEqual((batches["coherent-nested"]["original_source_inventory"],
                              batches["coherent-nested"]["actual_loaded_sources"]), (184, 19))
            self.assertEqual(len(batches["coherent-nested"]["bound_scope_sha256"]), 19)
            self.assertEqual((batches["basename-consumer"]["original_source_inventory"],
                              batches["basename-consumer"]["actual_loaded_sources"]), (29, 17))
            self.assertEqual((batches["coherent-lookup"]["original_source_inventory"],
                              batches["coherent-lookup"]["actual_loaded_sources"]), (4, 2))
            self.assertNotIn("current_tested_inputs", actual["sdk_qualified_kernel_profile"])
            self.assertIn("historical_tested_inputs", actual["sdk_qualified_kernel_profile"])
            extension = contract["post_profile_dependency_addendum"]
            for relative in (
                "Tools/PinkhaSimulatorGate/wave15_batch.py",
                "Tools/PinkhaSimulatorGate/coherent_container_observation.py",
                "Tools/PinkhaSimulatorGate/sdk06_qualified_selector.py",
            ):
                path = app / relative; original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n# unreviewed dependency bytes\n")
                    with self.subTest(changed=relative), self.assertRaisesRegex(retained.RetainedControlError, "Unadmitted"):
                        retained.verify_retained_controls(app)
                finally:
                    path.write_bytes(original)
            files = {row["path"]: (app / row["path"]).read_bytes() for row in contract["proof_files"]}
            bad = copy.deepcopy(contract)
            bad["post_profile_dependency_addendum"]["proof_additions"].append("Tools/unreviewed.json")
            with self.assertRaisesRegex(retained.RetainedControlError, "Unreviewed dependency proof"):
                retained.post_profile_dependency_view(bad, files)
            bad = copy.deepcopy(contract)
            selector = "Tools/PinkhaSimulatorGate/sdk06_qualified_selector.py"
            bad["post_profile_dependency_addendum"]["inverses"][selector]["edits"][0]["new"] += "# arbitrary\n"
            with self.assertRaisesRegex(retained.RetainedControlError, "exact inverse"):
                retained.post_profile_dependency_view(bad, files)
            proof = extension["batches"]["coherent-nested"]
            changed_files = dict(files)
            record = json.loads(files[proof["receipt"]])
            record["loaded_inputs"] = {}
            changed_files[proof["receipt"]] = json.dumps(record).encode()
            with self.assertRaisesRegex(retained.RetainedControlError, "actual19"):
                retained.post_profile_dependency_view(contract, changed_files)
            proof = extension["batches"]["coherent-lookup"]
            record, events = (json.loads(files[proof[key]]) for key in ("receipt", "events"))
            events[-1]["event"] = "FAIL"
            with self.assertRaisesRegex(retained.RetainedControlError, "five original"):
                retained.fixed_dependency_control_outcomes("coherent-lookup", record, events,
                    files[proof["log"]], proof["methods"])
            proof = extension["batches"]["basename-consumer"]
            record, events = (json.loads(files[proof[key]]) for key in ("receipt", "events"))
            record["new_control_methods_executed"] = 3
            with self.assertRaisesRegex(retained.RetainedControlError, "scope was relabelled"):
                retained.fixed_dependency_control_outcomes("basename-consumer", record, events,
                    files[proof["log"]], proof["methods"])


if __name__ == "__main__":
    unittest.main()
