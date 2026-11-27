#!/usr/bin/env python3
"""Bounded portable resource-successor controls; never Apple/product admission."""
import base64
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
EVIDENCE = Path(os.environ.get("PINKHA_RESOURCE512_EVIDENCE_ROOT", HERE))
ORIGINALS = Path(os.environ.get("PINKHA_WARM_ORIGINAL_INPUTS",
    HERE.parent / "wave3-warm-retry/original-inputs"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


materializer = load("resource512_materializer", HERE / "materialize_wave3_intake.py")


class Resource512IntakeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((HERE / "frozen-profile.resource512.closed.json").read_text())
        cls.embedded = {key: (ORIGINALS / filename).read_text()
                        for key, (filename, _) in materializer.INPUTS.items()}
        cls.candidate, cls.materialization = materializer.compose(HISTORICAL.read_bytes(),
            (HERE / "wave3_intake.py").read_bytes(), cls.embedded, cls.profile)
        cls.original_bytes = {}
        for folder, name_key in (("actual-inputs", "name"), ("retained-originals", "localName")):
            for reference in json.loads((EVIDENCE / folder / "custody.json").read_text()):
                value = (EVIDENCE / folder / reference.get("storedName", reference[name_key])).read_bytes()
                if reference.get("storageEncoding") == "base64-json":
                    archive = json.loads(value)
                    value = base64.b64decode(archive["data"], validate=True)
                    assert archive["sha256"] == reference["sha256"]
                    assert archive["bytes"] == reference["bytes"]
                assert len(value) == reference["bytes"]
                assert hashlib.sha256(value).hexdigest() == reference["sha256"]
                cls.original_bytes[reference["path"]] = value
        cls.proposal = json.loads((EVIDENCE / "actual-inputs/proposed-admission.preview.txt").read_text())
        cls.old_draft = json.loads((EVIDENCE / "retained-originals/main16-wave3-8f2c11713fb8--build-admission.draft.json").read_text())
        cls.adapter = load("resource512_original47c", ORIGINALS / "wave3_shared_build.py")
        cls.warm = load("resource512_originalc4b", ORIGINALS / "wave3_warm_retry.py")

    def module(self):
        module = types.ModuleType("resource512_portable_control_only")
        module.__file__ = str(HERE / "NEVER_EXECUTED_COMMON_MAIN.py")
        exec(compile(self.candidate, module.__file__, "exec"), module.__dict__)
        buffers = dict(self.original_bytes)
        reads = []

        def pinned(reference):
            module.require(set(reference) == {"path", "sha256", "bytes"}, "pin schema changed")
            module.require(reference["path"] in buffers, "Original retained input missing")
            raw = buffers[reference["path"]]
            module.require(len(raw) == reference["bytes"]
                           and hashlib.sha256(raw).hexdigest() == reference["sha256"],
                           "Original retained input bytes changed")
            reads.append(reference)
            return raw

        module.pinned = pinned
        return module, buffers, reads

    def restore(self, module, proposal=None, contract=None):
        return module.w3_resource512_restore_admission(
            copy.deepcopy(self.proposal if proposal is None else proposal),
            copy.deepcopy(self.profile["evidence"]["app16Producer"] if contract is None else contract),
            self.adapter, self.warm)

    def test_actual_resource_preview_restores_exact_old_reference_and_expansion(self):
        module, _, reads = self.module()
        restored, proof = self.restore(module)
        self.assertEqual(restored, dict(self.old_draft, readyForBuild=True))
        self.assertIs(self.old_draft["readyForBuild"], False)
        self.assertIs(proof["exactResourceInverse"], True)
        self.assertIs(proof["previewProvidesBuildApproval"], False)
        self.assertIs(proof["previewExecutesBuildsOrTests"], False)
        self.assertIs(proof["freshAllHostCensusAndFiniteWindowRemainRootDispatchPrerequisites"], True)
        self.assertEqual((proof["appEstimateBytes"], proof["emergencyFloorBytes"], proof["concurrentAllowanceBytes"]),
                         (6442450944, 2147483648, 536870912))
        self.assertEqual(len({row["path"] for row in reads}), 19)
        report = json.loads((EVIDENCE / "actual-inputs/receipt.json").read_text())
        self.assertIs(report["prospectiveResourceObservation"]["heavyOrQueuedProcessesAbsent"], False)
        self.assertEqual(self.materialization["originalDefinitionsUnchanged"], 33)
        self.assertIs(self.materialization["actualProductAdmitted"], False)

    def test_unreviewed_admission_or_cache_contract_cannot_use_resource_preview(self):
        for change in ("source", "sdk", "native", "concurrency", "cache-contract"):
            with self.subTest(change=change):
                module, _, _ = self.module()
                proposal = copy.deepcopy(self.proposal)
                contract = copy.deepcopy(self.profile["evidence"]["app16Producer"])
                if change == "source": proposal["appSourceSHA"] = "0" * 40
                elif change == "sdk": proposal["pins"]["sdkMaterializationReceiptSHA256"] = "0" * 64
                elif change == "native": proposal["pins"]["nativeSourceManifestSHA256"] = "0" * 64
                elif change == "concurrency": proposal["warmRetry"]["concurrentGrowthAllowanceBytes"] -= 1
                else: contract["cacheQualification"]["path"] += ".detached"
                with self.assertRaisesRegex(ValueError, "not the exact reviewed"):
                    self.restore(module, proposal, contract)

    def test_changed_cache_or_missing_original_draft_fails_custody(self):
        for change in ("changed-cache", "missing-original-draft"):
            with self.subTest(change=change):
                module, buffers, _ = self.module()
                if change == "changed-cache":
                    path = module.W3_RESOURCE512_EVIDENCE["cache-requalification.json"]["path"]
                    buffers[path] += b" "
                else:
                    path = next(path for path in buffers if path.endswith("/build-admission.draft.json"))
                    del buffers[path]
                with self.assertRaisesRegex(ValueError, "Original retained input"):
                    self.restore(module)

    def test_ready_flag_cannot_turn_previews_into_approval_or_successful_products(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                module, _, _ = self.module()
                module.W3_FROZEN["readyForRuntimeAdmission"] = ready

                def forbidden(*args, **kwargs):
                    self.fail("A resource preview reached product I/O or commands")

                module.pinned = module.raw = module._W3_ORIGINAL_CLONER = forbidden
                expected = "Actual exact warm-retry receipt pins are pending" if ready else "Wave3 runtime intake is closed:"
                with self.assertRaisesRegex(ValueError, expected):
                    module.admit_and_clone_products({}, None, None, None)

    def test_exact_delta_detects_missing_null_and_bool_numeric_changes(self):
        module, _, _ = self.module()
        self.assertEqual(module.w3_resource512_delta({}, {"extra": None}),
                         [{"path": "/extra", "before": None, "after": None}])
        self.assertEqual(module.w3_resource512_delta({"extra": None}, {}),
                         [{"path": "/extra", "before": None, "after": None}])
        self.assertEqual(module.w3_resource512_delta({"flag": False}, {"flag": 0}),
                         [{"path": "/flag", "before": False, "after": 0}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
