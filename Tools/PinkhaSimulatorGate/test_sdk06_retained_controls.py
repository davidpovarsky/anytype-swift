"""New admission-boundary controls only; no original controller is executed."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import sdk06_retained_controls as admission


ROOT = Path(__file__).resolve().parents[2]


class RetainedControllerAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sdk06-retained-controls-")
        self.addCleanup(temporary.cleanup)
        self.app = Path(temporary.name) / "app"
        self.app.mkdir()
        self.contract = json.loads((ROOT / admission.ADMISSION_PATH).read_text())
        paths = {admission.ADMISSION_PATH}
        paths.update(item["path"] for item in self.contract["source_inputs"])
        paths.update(item["path"] for item in self.contract["proof_files"])
        for relative in sorted(paths):
            destination = self.app / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

    def test_exact_named_original_proofs_qualify_only_current_98_controller_methods(self):
        receipt = admission.verify_retained_controls(self.app)
        self.assertEqual(receipt["status"], "PASS_RETAINED_CONTROLLER_CONTROLS_ONLY")
        self.assertEqual((receipt["current_control_methods"], receipt["retained_original_methods"],
                          receipt["qualified_observer_methods"], receipt["retired_historical_methods"]),
                         (98, 91, 7, 1))
        self.assertEqual(receipt["original_lane_conclusions"],
                         {"45096079315": "FAIL", "45087685319": "failure"})
        self.assertEqual(receipt["controller_methods_executed_now"], 0)
        self.assertEqual(receipt["product_tests_executed_now"], 0)
        self.assertEqual(len(receipt["source_inputs"]), 39)
        names = {item["method"] for item in receipt["current_catalog"]}
        retired = "ObserverControls.test_poll_timeout_records_command_stage_and_bound_without_retry_or_mapping"
        self.assertNotIn(retired, names)
        historical = next(item for item in receipt["original_proof_batches"]
                          if item["id"] == "runtime-original")
        self.assertIn(retired, historical["methods"])
        for module, count in (
            ("test_hanlin_ui_runtime.py", 49), ("test_hanlin_acceptance_evidence.py", 20),
            ("test_text_native_ack.py", 5), ("test_shared_editor_existing_build.py", 22),
            ("test_acceptance_continuation_branch.py", 2),
        ):
            self.assertEqual(sum(Path(item["module"]).name == module
                                 for item in receipt["current_catalog"]), count)
        json.dumps(receipt)

    def test_changed_production_swift_fixture_or_original_proof_is_unadmitted(self):
        paths = [
            "Tools/PinkhaSimulatorGate/run_ui27.py",
            "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py",
            "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py",
            "Tools/Hanlin/test_shared_editor_profile.py",
            "AnyTypeTests/Pinkha/TorahRelatedReadAuthorityMappingTests.swift",
            "docs/validation/20261123-sdk06-retained-controls/original-45087685319/original-job-137409920728.log",
        ]
        for relative in paths:
            with self.subTest(relative=relative):
                path = self.app / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n# unadmitted source or provenance change\n")
                    with self.assertRaisesRegex(admission.RetainedControlError, "Unadmitted"):
                        admission.verify_retained_controls(self.app)
                finally:
                    path.write_bytes(original)

    def test_named_parser_rejects_duplicate_failure_skip_count_drift_and_missing_terminal(self):
        names = [
            "test_first (__main__.BoundaryControls.test_first) ... ok",
            "test_second (__main__.BoundaryControls.test_second) ... ok",
        ]
        valid = "\n".join(names + ["Ran 2 tests in 0.001s", "", "OK"]) + "\n"
        parsed = admission.unittest_batches(valid.encode())
        self.assertEqual([entry["name"] for entry in parsed[0]["methods"]],
                         ["BoundaryControls.test_first", "BoundaryControls.test_second"])
        cases = {
            "duplicate": valid.replace(names[1], names[0]),
            "failed": valid.replace("test_second) ... ok", "test_second) ... FAIL"),
            "skipped": valid.replace("test_second) ... ok", "test_second) ... skipped 'unexecuted'"),
            "summary_only": "Ran 2 tests in 0.001s\n\nOK\n",
            "count": valid.replace("Ran 2", "Ran 3"),
            "truncated": valid.removesuffix("OK\n"),
            "relabelled": valid.replace("(__main__.BoundaryControls.test_first)",
                                       "(__main__.BoundaryControls.test_different)"),
        }
        for label, raw in cases.items():
            with self.subTest(case=label), self.assertRaises(admission.RetainedControlError):
                admission.unittest_batches(raw.encode())

    def test_fixed_admission_and_real_input_paths_cannot_be_replaced_by_overrides_or_symlinks(self):
        relative = "Tools/PinkhaSimulatorGate/hanlin_acceptance_evidence.py"
        path = self.app / relative
        data = path.read_bytes()
        outside = self.app.parent / "foreign-identical.py"
        outside.write_bytes(data)
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(admission.RetainedControlError, "Symlink"):
            admission.verify_retained_controls(self.app)
        path.unlink()
        path.write_bytes(data)
        contract_path = self.app / admission.ADMISSION_PATH
        exact = contract_path.read_bytes()
        contract = copy.deepcopy(self.contract)
        contract["pending_sdk_composition"]["admitted"] = True
        contract_path.write_text(json.dumps(contract))
        with self.assertRaisesRegex(admission.RetainedControlError, "Unadmitted"):
            admission.verify_retained_controls(self.app)
        contract_path.write_bytes(exact)
        with self.assertRaisesRegex(admission.RetainedControlError, "Unsafe"):
            admission.read_bound(self.app, "../foreign-identical.py")
        with self.assertRaises(TypeError):
            admission.verify_retained_controls(self.app, overrides={relative: admission.digest(data)})


    def test_fixed_composition_retains_98_only_with_exact_views_and_original_11_plus_7_plus_9(self):
        receipt = admission.verify_retained_controls(self.app)
        composed = receipt["fixed_composition"]
        self.assertEqual(receipt["current_control_methods"], 98)
        self.assertEqual(receipt["retained_original_methods"], 91)
        self.assertEqual(receipt["qualified_observer_methods"], 7)
        self.assertEqual(composed["composition_methods_qualified"], 18)
        self.assertEqual(composed["kernel_methods_qualified"], 9)
        self.assertEqual((composed["retained_original_passes"], composed["repaired_former_errors"]), (11, 7))
        self.assertTrue(composed["original_failed_attempt_preserved"])
        self.assertFalse(composed["selector_admission_claimed"])
        self.assertFalse(composed["product_acceptance_claimed"])
        self.assertEqual(composed["methods_executed_now"], 0)
        self.assertEqual(len(composed["qualified_methods"]), 27)
        extension = self.contract["composition_extension"]
        self.assertEqual(len(extension["inverses"]), 6)
        for relative in extension["inverses"]:
            with self.subTest(changed_hook=relative):
                path = self.app / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b"\n# unadmitted composition change\n")
                    with self.assertRaisesRegex(admission.RetainedControlError, "Unadmitted"):
                        admission.verify_retained_controls(self.app)
                finally:
                    path.write_bytes(original)
        supervisor = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
        layer = copy.deepcopy(extension["inverses"][supervisor]["layers"][0])
        layer["edits"][-1]["new"] += "\n# an unreviewed inverse must not apply"
        with self.assertRaisesRegex(admission.RetainedControlError, "composition hunk"):
            admission.reverse_scoped_edits((self.app / supervisor).read_bytes(),
                                          layer["edits"], layer["result_sha256"])
        original_attempt = next(item for item in extension["attempts"] if item["id"] == "qualified-attempt1")
        events = json.loads((self.app / original_attempt["events"]).read_text())
        failed = next(item for item in events if item.get("status") == "ERROR")
        failed["status"] = "PASS"
        with self.assertRaisesRegex(admission.RetainedControlError, "outcomes disagree"):
            admission.focused_outcomes(json.dumps(events).encode(),
                                       (self.app / original_attempt["log"]).read_bytes(),
                                       (self.app / original_attempt["result"]).read_bytes())



    def test_sdk_qualified_profile_addendum_preserves_history_and_rejects_scope_relabelling(self):
        receipt = admission.verify_retained_controls(self.app)
        profile = receipt["sdk_qualified_kernel_profile"]
        self.assertEqual(receipt["current_control_methods"], 98)
        self.assertEqual(receipt["fixed_composition"]["composition_methods_qualified"], 18)
        self.assertEqual(receipt["fixed_composition"]["source_scope"], "HISTORICAL_FROZEN_COMPOSITION")
        self.assertNotIn("current_source_inputs", receipt["fixed_composition"])
        self.assertEqual((profile["unchanged_original_composition_methods_retained"],
                          profile["directly_affected_composition_methods_requalified"],
                          profile["new_profile_methods_qualified"]), (17, 1, 1))
        self.assertEqual(profile["current_composition_methods_qualified"], 19)
        self.assertEqual(profile["original_kernel_methods_retained"], 9)
        self.assertFalse(profile["original_18_history_relabelled"])
        self.assertEqual(profile["methods_executed_now"], 0)
        self.assertFalse(profile["selector_admission_claimed"])
        self.assertFalse(profile["product_acceptance_claimed"])
        extension = self.contract["sdk_qualified_kernel_profile_addendum"]
        for relative in extension["inverses"]:
            path = self.app / relative
            original = path.read_bytes()
            try:
                path.write_bytes(original + b"\n# unadmitted profile or fixture bytes\n")
                with self.assertRaisesRegex(admission.RetainedControlError, "Unadmitted"):
                    admission.verify_retained_controls(self.app)
            finally:
                path.write_bytes(original)
        files = {row["path"]: (self.app / row["path"]).read_bytes()
                 for row in self.contract["proof_files"]}
        malformed = copy.deepcopy(self.contract)
        production = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
        malformed["sdk_qualified_kernel_profile_addendum"]["inverses"][production]["edits"][0]["new"] = (
            '    if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", "arbitrary"):\n')
        with self.assertRaisesRegex(admission.RetainedControlError, "predicate alias"):
            admission.qualified_kernel_profile_view(malformed, files)
        proof = extension["original_pair"]
        result = json.loads(files[proof["result"]])
        result["old_control_methods_executed"] = 0
        with self.assertRaisesRegex(admission.RetainedControlError, "affected/new execution scope"):
            admission.qualified_profile_pair_outcomes(files[proof["events"]], files[proof["log"]],
                json.dumps(result).encode(), proof["methods"], proof["source_sha"])
        events = json.loads(files[proof["events"]])
        events[-1]["status"] = "FAIL"
        with self.assertRaisesRegex(admission.RetainedControlError, "named terminal"):
            admission.qualified_profile_pair_outcomes(json.dumps(events).encode(), files[proof["log"]],
                files[proof["result"]], proof["methods"], proof["source_sha"])


if __name__ == "__main__":
    unittest.main()
