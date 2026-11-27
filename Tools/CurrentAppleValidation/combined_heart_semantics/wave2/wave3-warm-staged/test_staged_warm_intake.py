#!/usr/bin/env python3
"""Local schema controls using actual staged metadata; no product admission."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import types
import unittest

HERE = Path(__file__).resolve().parent
HISTORICAL = Path(os.environ.get("PINKHA_WAVE3_HISTORICAL_COMMON",
    HERE.parent / "materialized-control/combined_heart_semantics_current.py"))
ORIGINALS = Path(os.environ.get("PINKHA_WARM_ORIGINAL_INPUTS",
    HERE.parent / "wave3-warm-retry/original-inputs"))
ACTUAL = Path(os.environ.get("PINKHA_WARM_STAGE_ACTUAL_INPUTS", HERE / "actual-inputs"))
spec = importlib.util.spec_from_file_location("staged_warm_materializer", HERE / "materialize_wave3_intake.py")
materializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materializer)


class StagedWarmSchemaControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((HERE / "frozen-profile.staged.closed.json").read_text())
        cls.embedded = {key: (ORIGINALS / filename).read_text()
                        for key, (filename, _) in materializer.INPUTS.items()}
        cls.candidate, cls.proof = materializer.compose(HISTORICAL.read_bytes(),
            (HERE / "wave3_intake.py").read_bytes(), cls.embedded, cls.profile)
        raw = (ACTUAL / "source-staging.proposed-ready.preview.txt").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == "d22db29bd444895e0152cc9234b3631cfb085684d23bd5ac9c074b64e51e5f3d"
        cls.plan = json.loads(raw)
        cls.physical = json.loads((ACTUAL / "plan-physical-references.json").read_text())

    def module(self):
        module = types.ModuleType("synthetic_staged_schema_only")
        module.__file__ = str(HERE / "NEVER_EXECUTED_COMMON_MAIN.py")
        exec(compile(self.candidate, module.__file__, "exec"), module.__dict__)
        return module

    def gate(self, plan):
        owner = self
        names = {"originalStager": "stage_wave3_source", "originalAdapter": "wave3_shared_build",
                 "originalProducer": "base_producer", "preservation": "preserve_failed_shared_build",
                 "warmAdapter": "wave3_warm_retry", "warmStager": "stage_wave3_warm_retry"}
        originals = {self.plan["controls"][key]["path"]: self.embedded[name].encode()
                     for key, name in names.items()}
        reads = []
        def read_ref(reference):
            owner.assertEqual(set(reference), {"path", "sha256"})
            reads.append(reference)
            if reference["path"] == owner.plan["gitBundle"]["path"]:
                observed = owner.physical["references"]["bundle"]
                owner.assertEqual(reference["sha256"], observed["sha256"])
                owner.assertEqual(observed["bytes"], 206516)
                # This local buffer exercises schema/length only. The actual
                # physical bundle digest was observed separately on the Mac.
                # No synthetic bundle is represented as admitted Git data.
                return bytes(observed["bytes"])
            value = originals[reference["path"]]
            owner.assertEqual(hashlib.sha256(value).hexdigest(), reference["sha256"])
            return value
        return types.SimpleNamespace(read_ref=read_ref, observedReads=reads)

    def test_actual_six_control_and_four_field_bundle_schema_is_consumed_precisely(self):
        module = self.module()
        contract = self.profile["evidence"]["app16Producer"]
        gate = self.gate(self.plan)
        module.w3_stage_control_references(self.plan, contract, gate)
        self.assertEqual(set(self.plan["controls"]), {"originalStager", "originalAdapter", "originalProducer",
                                                    "preservation", "warmAdapter", "warmStager"})
        self.assertEqual(set(self.plan["gitBundle"]), {"path", "sha256", "bytes", "prerequisite"})
        self.assertEqual(len(gate.observedReads), 8)
        self.assertEqual(gate.observedReads[-1], {key: self.plan["gitBundle"][key] for key in ("path", "sha256")})

    def test_missing_extra_changed_or_detached_control_and_bundle_fields_are_rejected(self):
        for mutation in ("missing-producer", "extra-control", "changed-producer", "detached-stager",
                         "wrong-bundle-size", "wrong-prerequisite", "extra-bundle-field"):
            with self.subTest(mutation=mutation):
                module = self.module()
                plan = copy.deepcopy(self.plan)
                contract = copy.deepcopy(self.profile["evidence"]["app16Producer"])
                if mutation == "missing-producer": del plan["controls"]["originalProducer"]
                elif mutation == "extra-control": plan["controls"]["other"] = plan["controls"]["originalAdapter"]
                elif mutation == "changed-producer": plan["controls"]["originalProducer"]["sha256"] = "0" * 64
                elif mutation == "detached-stager": contract["stagingScript"]["path"] += ".other"
                elif mutation == "wrong-bundle-size": plan["gitBundle"]["bytes"] += 1
                elif mutation == "wrong-prerequisite": plan["gitBundle"]["prerequisite"] = "a" * 40
                else: plan["gitBundle"]["other"] = True
                with self.assertRaises(ValueError):
                    module.w3_stage_control_references(plan, contract, self.gate(plan))

    def test_real_stage_and_draft_do_not_open_runtime_admission(self):
        module = self.module()
        module.W3_FROZEN = copy.deepcopy(self.profile)
        module.W3_FROZEN["readyForRuntimeAdmission"] = True
        def forbidden(*args, **kwargs):
            self.fail("Partial stage evidence reached product reads or commands")
        module.pinned = module.raw = module._W3_ORIGINAL_CLONER = forbidden
        with self.assertRaisesRegex(ValueError, "Actual exact warm-retry receipt pins are pending"):
            module.admit_and_clone_products({}, None, None, None)
        draft = json.loads((ACTUAL / "build-admission.draft.json").read_text())
        template = json.loads((ACTUAL / "build-admission.template.ready-false.json").read_text())
        self.assertIs(draft["readyForBuild"], False)
        self.assertIs(template["readyForBuild"], False)
        self.assertEqual({key for key in template if template[key] != draft.get(key)},
                         {"sourceStaging", "cacheQualification"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
