"""New two-origin admission controls, using explicitly synthetic process inputs.

The complete existing original-proof/admission controls are not rerun here.
Their fixture builders provide controller inputs; Mach-O and xcresult tools are
substituted as before. The new original-build verifier is separately exercised
against the authentic pinned 106-file artifact in test_build_reuse.py.
"""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

import coherent_runtime_admission as admission
import heart_runtime_profile as profiles
import test_coherent_runtime_admission as original_controls
from coherent_apple import reuse_build as reuse

ROOT = Path(__file__).resolve().parents[2]
PROOF_ZIP = ROOT / "docs/validation/20261122-coherent-heart-apple-build/proof-original.zip"


class CoherentReuseAdmissionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original_controls.CoherentAdmissionControls.setUpClass()
        assert admission.digest(PROOF_ZIP) == profiles.COHERENT_BUILT_PROOF_SHA
        with zipfile.ZipFile(PROOF_ZIP) as archive:
            cls.original_receipt_raw = archive.read("proof/production/custom-heart-build.json")
        assert profiles.digest_bytes(cls.original_receipt_raw) == profiles.COHERENT_BUILT_RECEIPT_SHA

    def setUp(self):
        self.helper = original_controls.CoherentAdmissionControls()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)

    def fixture(self):
        value = self.helper.fixture()
        profile = value["args"].runtime_profile
        receipt, build, host = value["receipt"], value["build"], value["host"]
        receipt.update(github_run_id=reuse.RUN, github_run_attempt="1", integration_sha=reuse.SOURCE)
        build.update(app_sha=reuse.SOURCE, run_id=reuse.RUN, run_attempt="1")
        raw = original_controls.encoded(receipt)
        tar = original_controls.packed_tar({**{"Lib.xcframework/" + name: body for name, body in value["files"].items()},
                                           "PinkhaNativeHeartBuild.json": raw})
        build["frameworks"]["production"]["artifact_sha256"] = profiles.digest_bytes(tar)
        build_raw = original_controls.encoded(build)
        # This synthetic record represents the result returned by the separately
        # tested immutable-lineage verifier. It cannot pass that verifier itself.
        lineage_raw = original_controls.encoded({"synthetic_controller_input": True})
        lineage = dict(build_producer=reuse.origin(), receipt_sha256=profiles.digest_bytes(lineage_raw),
                       current_source=value["source_map"], modules=host["copied_module_sha256"],
                       original_artifacts=deepcopy(reuse.ARTIFACTS))
        host.update(build_receipt_sha256=profiles.digest_bytes(build_raw), build_origin=reuse.origin(),
                    build_reuse_receipt_sha256=lineage["receipt_sha256"])
        with zipfile.ZipFile(io.BytesIO(value["proof_zip"])) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        artifact = json.loads(files["proof/production/runtime-artifact.json"])
        artifact.update(integration_sha=reuse.SOURCE, github_run_id=reuse.RUN, github_run_attempt="1",
                        sha256=profiles.digest_bytes(tar), receipt_sha256=profiles.digest_bytes(raw))
        files.update({"proof/production/custom-heart-build.json": raw,
                      "proof/production/runtime-artifact.json": original_controls.encoded(artifact),
                      "proof/build.json": build_raw, "proof/build-reuse.json": lineage_raw,
                      "proof/host/receipt.json": original_controls.encoded(host)})
        value["runtime_zip"] = original_controls.packed_zip({profiles.select(profile).archive_name: tar})
        value["proof_zip"] = original_controls.packed_zip(files)
        for item, body in zip(value["items"], (value["runtime_zip"], value["proof_zip"])):
            item.update(size_in_bytes=len(body), digest="sha256:" + profiles.digest_bytes(body))
        value.update(lineage=lineage, synthetic_receipt_raw=raw)
        return value

    def run_fixture(self, value):
        with patch.object(reuse, "validate_admission_lineage", return_value=value["lineage"]):
            return self.helper.run_fixture(value)

    def test_successful_execution_origin_does_not_rewrite_the_built_runtime_origin(self):
        value = self.fixture()
        result = self.run_fixture(value)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["producer"]["run_id"], "9991")
        self.assertEqual(result["producer"]["source_sha"], original_controls.PRODUCER)
        self.assertEqual(result["build_producer"], reuse.origin())
        self.assertEqual(result["original_build_app_sha"], reuse.SOURCE)
        self.assertEqual(result["original_build_artifact_id"], profiles.COHERENT_BUILT_ARTIFACT)
        self.assertEqual(result["heart_artifact_id"], 1001)
        self.assertEqual(result["production_binary_execution"], "NOT_RUN")
        self.assertEqual((self.helper.app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json").read_bytes(),
                         value["synthetic_receipt_raw"])
        self.assertFalse(any(argv[0] in ("xcodebuild", "go", "swift") for argv in self.helper.calls))

    def test_lineage_mismatch_and_unsuccessful_execution_fail_before_installation(self):
        for mutation in (lambda value: value["lineage"].update(receipt_sha256="f" * 64),
                         lambda value: value["lineage"].update(current_source={"changed": "f" * 64}),
                         lambda value: value["lineage"].update(modules={"changed": "f" * 64}),
                         lambda value: value["lineage"]["build_producer"].update(source_sha="f" * 40),
                         lambda value: value["run"].update(conclusion="failure")):
            self.setUp()
            value = self.fixture(); mutation(value)
            with self.assertRaises(RuntimeError):
                self.run_fixture(value)
            self.helper.assert_not_installed()

    def actual_receipt_installation(self):
        destination = self.helper.app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.original_receipt_raw)
        profile = profiles.select(profiles.COHERENT)
        return dict(status="PASS", app_source_sha=original_controls.CONSUMER, marker=profile.receipt_marker,
                    runtime_profile=profile.name, source_run_id="9991", producer=dict(run_id="9991", run_attempt="1",
                        source_sha=original_controls.PRODUCER), build_producer=reuse.origin(),
                    original_build_app_sha=reuse.SOURCE, heart_build_receipt_sha256=profiles.COHERENT_BUILT_RECEIPT_SHA,
                    heart_artifact_id=1001, heart_artifact_sha256="a" * 64,
                    heart_proof_artifact_id=1002, heart_proof_artifact_sha256="b" * 64,
                    build_reuse_receipt_sha256="c" * 64,
                    original_build_artifact_id=profiles.COHERENT_BUILT_ARTIFACT,
                    original_build_artifact_sha256=profiles.COHERENT_BUILT_ARTIFACT_SHA,
                    original_build_proof_artifact_id=profiles.COHERENT_BUILT_PROOF_ARTIFACT,
                    original_build_proof_artifact_sha256=profiles.COHERENT_BUILT_PROOF_SHA)

    def test_actual_packaged_receipt_preserves_both_origins_in_observer_binding(self):
        installation = self.actual_receipt_installation()
        binding = profiles.installed_binding(self.helper.app, installation, original_controls.CONSUMER,
                                             profiles.COHERENT, "9991")
        self.assertEqual(binding["heart_source_run_id"], "9991")
        self.assertEqual(binding["heart_build_source_run_id"], reuse.RUN)
        self.assertEqual(binding["heart_build_source_sha"], reuse.SOURCE)
        self.assertEqual(profiles.verify_binding(binding), profiles.select(profiles.COHERENT).version)
        for key in profiles.REUSE_BINDING_KEYS:
            changed = deepcopy(binding); del changed[key]
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                profiles.verify_binding(changed)
        changed = {name: value for name, value in binding.items() if name not in profiles.REUSE_BINDING_KEYS}
        with self.assertRaises(RuntimeError):
            profiles.verify_binding(changed)
        changed = dict(binding, heart_build_receipt_sha256="0" * 64)
        with self.assertRaises(RuntimeError):
            profiles.verify_binding(changed)

    def test_original_failed_builder_cannot_be_presented_as_successful_execution_or_partial_lineage(self):
        installation = self.actual_receipt_installation()
        for key in profiles.REUSE_INSTALLATION_KEYS:
            changed = deepcopy(installation); del changed[key]
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                profiles.installed_binding(self.helper.app, changed, original_controls.CONSUMER,
                                           profiles.COHERENT, "9991")
        changed = deepcopy(installation)
        changed["source_run_id"] = reuse.RUN; changed["producer"]["run_id"] = reuse.RUN
        with self.assertRaises(RuntimeError):
            profiles.installed_binding(self.helper.app, changed, original_controls.CONSUMER,
                                       profiles.COHERENT, reuse.RUN)
        changed = deepcopy(installation); changed["build_producer"]["workflow_conclusion"] = "success"
        with self.assertRaises(RuntimeError):
            profiles.installed_binding(self.helper.app, changed, original_controls.CONSUMER,
                                       profiles.COHERENT, "9991")


if __name__ == "__main__":
    unittest.main()
