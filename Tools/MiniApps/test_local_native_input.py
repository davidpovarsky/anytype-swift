"""Negative admission controls; these never claim native or app execution."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import local_native_input as subject


class NativeInputIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The test invocation supplies a separate immutable copy of the observed
        # actual receipts. Missing evidence is a failure, never a skipped gate.
        cls.evidence = Path(os.environ["MINIAPPS_NATIVE70F_CONTROL_EVIDENCE"])
        cls.policy = json.loads((HERE / "local_native_policy.json").read_text())
        cls.actual = {name: json.loads((cls.evidence / (name + ".json")).read_text())
                      for name in ("native", "stopped", "union", "wrapper")}

    def altered(self, document, path, value):
        data = copy.deepcopy(self.actual)
        target = data[document]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with self.assertRaises((RuntimeError, KeyError)):
            subject.validate_receipts(self.policy, **data)

    def test_actual_observed_receipts_keep_original_failure(self):
        commands = subject.validate_receipts(self.policy, **self.actual)
        self.assertEqual(len(commands), 10)
        self.assertEqual(self.actual["stopped"]["status"], "FAIL")

    def test_cannot_relabel_original_preparation(self):
        self.altered("stopped", ("status",), "PASS")

    def test_cannot_lose_original_failure_binding(self):
        self.altered("native", ("originalPreparationStopReceiptSHA256",), "0" * 64)

    def test_cannot_admit_second_go_runtime(self):
        self.altered("native", ("independentGoRuntimeCount",), 2)

    def test_source_membership_is_exact(self):
        self.altered("native", ("sourceFilesVerified",), 4854)

    def test_no_unexecuted_app_credit(self):
        self.altered("native", ("applicationBuilds",), 1)

    def test_no_unexecuted_native_credit(self):
        self.altered("native", ("nativeAcceptanceTestsExecuted",), 1)

    def test_graph_correction_must_preserve_all_module_identities(self):
        self.altered("native", ("verifiedGatewayMetadataHydration",
                                "unchangedModuleIdentities"), 759)

    def test_graph_afterimage_is_bound(self):
        self.altered("native", ("actualModuleGraphSHA256",), "0" * 64)

    def test_failed_compiler_cannot_qualify(self):
        self.altered("native", ("commands", 0, "exitCode"), 1)

    def test_duplicate_command_name_is_rejected(self):
        data = copy.deepcopy(self.actual)
        data["native"]["commands"].append(copy.deepcopy(data["native"]["commands"][0]))
        with self.assertRaises(RuntimeError):
            subject.validate_receipts(self.policy, **data)

    def test_partial_union_is_rejected(self):
        self.altered("union", ("allPayloadBytesEqualOriginalSlices",), False)

    def test_wrapper_source_is_not_substitutable(self):
        self.altered("wrapper", ("source_sha",), "0" * 40)

    def test_wrapper_typecheck_cannot_claim_ui(self):
        self.altered("wrapper", ("application_tests_executed",), 1)


if __name__ == "__main__":
    unittest.main()
