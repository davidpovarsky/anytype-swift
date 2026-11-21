"""Focused controls for the standalone corrected-runtime UI route."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_native_ui as runner
import run_ui27 as ui
import test_t5_native_ui as original

class CorrectedUIControls(unittest.TestCase):
    def build(self):
        profile=ui.heart_profiles.select("r15-attachment-v1")
        value=original.build()
        value.update(role="corrected-r15", runtime_version=profile.version)
        value["runtime_binding"]=dict(runtime_profile=profile.name,native_marker=profile.version,
            heart_patch_sha256=profile.patch_sha256,heart_inventory_sha256=profile.inventory_sha256,
            heart_source_run_id="44943967103",heart_source_attempt="1",heart_source_sha="1"*40,
            heart_build_receipt_sha256="2"*64,heart_artifact_id=14722543676,heart_artifact_sha256="3"*64,
            heart_proof_artifact_id=14722434042,heart_proof_artifact_sha256="4"*64)
        return value

    def invoke(self,build):
        return runner.run_after_corrected_build(app=Path("app"),work=Path("work"),proof=Path("proof"),
            build=build,selection={},pair=SimpleNamespace(FLAGS=original.FLAGS),ui=ui,
            method_results=None,source=original.SOURCE,run_id=original.RUN)

    def test_corrected_route_uses_shared_journey_without_a_fabricated_pair(self):
        with patch.object(runner,"_run_on_fresh_simulator",return_value={"status":"PENDING_ACTUAL_UI"}) as shared:
            self.assertEqual(self.invoke(self.build()),{"status":"PENDING_ACTUAL_UI"})
            args=shared.call_args.kwargs
            self.assertIsNone(args["pair_boundary"])
            self.assertEqual(args["runtime_profile"],"r15-attachment-v1")
            self.assertEqual(args["runtime"],ui.heart_profiles.select("r15-attachment-v1").version)

    def test_corrected_route_refuses_old_runtime_flags_source_and_missing_proof(self):
        mutations=[
            lambda v:v.update(role="new"),
            lambda v:v.update(runtime_version=original.RUNTIME),
            lambda v:v.update(flags=[]),
            lambda v:v.update(app_source_sha="0"*40),
            lambda v:v.update(code_sha256="bad"),
            lambda v:v["runtime_binding"].update(native_marker="prefix-only"),
            lambda v:v["runtime_binding"].pop("heart_build_receipt_sha256"),
        ]
        with patch.object(runner,"_run_on_fresh_simulator") as shared:
            for change in mutations:
                value=self.build(); change(value)
                with self.subTest(value=value),self.assertRaises((ValueError,RuntimeError)):
                    self.invoke(value)
            shared.assert_not_called()

    def test_standalone_fixture_preserves_exact_schema_bounds_and_real_identities(self):
        fixture=original.fixture()
        result=runner.evidence.validate_standalone_fixture(fixture,source=original.SOURCE,
            run_id=original.RUN,token=original.TOKEN,runtime=original.RUNTIME)
        self.assertEqual(set(result),set(runner.evidence.TARGET_ROLES))
        mutations=[
            lambda v:v.update(accountID=""),
            lambda v:v.update(runtimeVersion="foreign"),
            lambda v:v.update(spaceID=v["foreignSpaceID"]),
            lambda v:v["targets"][0].update(resultID="foreign"),
            lambda v:v["excluded"].pop(),
        ]
        for change in mutations:
            value=copy.deepcopy(fixture);change(value)
            with self.subTest(value=value),self.assertRaises(ValueError):
                runner.evidence.validate_standalone_fixture(value,source=original.SOURCE,
                    run_id=original.RUN,token=original.TOKEN,runtime=original.RUNTIME)

if __name__=="__main__":
    unittest.main()
