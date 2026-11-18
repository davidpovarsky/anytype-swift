"""Receipt/control tests only; these do not execute a native binary."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import run_t5_pairs_ci as subject


class PairCIControlTests(unittest.TestCase):
    def receipt(self):
        return dict(status="COMPONENT_STORE_PAIR_PASS", full_F10="NOT_PROVEN",
                    export_status="NOT_RUN_COMPONENT_NO_RPC", swift_pairing_status="NOT_RUN",
                    client_enablement=subject.CLIENT_DISABLED,
                    phase_reports=[dict(phase=phase, pid=100 + index, test_passed=True, closed=True)
                                   for index, phase in enumerate(subject.PHASES)])

    def test_completed_four_process_receipt_retains_component_scope(self):
        self.assertEqual(subject.validate_pair_result(self.receipt()),
                         dict(binaries=2, native_processes=4, passing_test_invocations=4))

    def test_missing_or_duplicate_processes_cannot_pass(self):
        for mutation in ["missing-phase", "duplicate-pid", "boolean-pid", "unclosed-store", "wrong-order"]:
            with self.subTest(mutation=mutation):
                result = self.receipt()
                if mutation == "missing-phase":
                    result["phase_reports"].pop()
                elif mutation == "duplicate-pid":
                    result["phase_reports"][1]["pid"] = result["phase_reports"][0]["pid"]
                elif mutation == "boolean-pid":
                    result["phase_reports"][0]["pid"] = True
                elif mutation == "unclosed-store":
                    result["phase_reports"][0]["closed"] = False
                else:
                    result["phase_reports"].reverse()
                with self.assertRaises(RuntimeError):
                    subject.validate_pair_result(result)

    def test_component_receipt_cannot_claim_product_acceptance_or_enable_client(self):
        for key, value in [("full_F10", "PASS"), ("export_status", "PASS"),
                           ("swift_pairing_status", "PASS"), ("client_enablement", "ENABLED"),
                           ("status", "PASS")]:
            with self.subTest(field=key):
                result = deepcopy(self.receipt())
                result[key] = value
                with self.assertRaises(RuntimeError):
                    subject.validate_pair_result(result)

    def test_genproto_effective_content_matches_the_reviewed_dependency(self):
        effective = dict(Path=subject.GENPROTO_PATH, Version=subject.GENPROTO_VERSION,
                         Sum=subject.GENPROTO_SUM, GoModSum=subject.GENPROTO_MOD_SUM)
        for selection in [effective, dict(Path=subject.GENPROTO_PATH,
                                          Version="v0.0.0-20210917145530-b395a37504d4",
                                          Replace=effective)]:
            self.assertEqual(subject.validate_genproto_selection(selection), effective)

    def test_genproto_revision_fork_and_checksums_are_fail_closed(self):
        effective = dict(Path=subject.GENPROTO_PATH, Version=subject.GENPROTO_VERSION,
                         Sum=subject.GENPROTO_SUM, GoModSum=subject.GENPROTO_MOD_SUM)
        for field, value in [("Path", "unreviewed.invalid/genproto"),
                             ("Version", "v0.0.0-20210917145530-b395a37504d4"),
                             ("Sum", "h1:wrong"), ("GoModSum", "")]:
            with self.subTest(field=field):
                changed = dict(effective, **{field: value})
                with self.assertRaises(RuntimeError):
                    subject.validate_genproto_selection(dict(Path=subject.GENPROTO_PATH, Replace=changed))

    def test_preserved_fixture_modification_is_rejected_before_native_build(self):
        source = Path(__file__).resolve().parents[2]
        subject.verify_pair_inputs(source)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / subject.PAIR_DIRECTORY
            target.mkdir(parents=True)
            for name in subject.PAIR_HASHES:
                data = (source / subject.PAIR_DIRECTORY / name).read_bytes()
                (target / name).write_bytes(data)
            fixture = target / "pair_phase_test.go"
            fixture.write_bytes(fixture.read_bytes() + b"\n// changed fixture\n")
            with self.assertRaisesRegex(RuntimeError, "pair_phase_test.go"):
                subject.verify_pair_inputs(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
