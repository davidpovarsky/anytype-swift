#!/usr/bin/env python3
"""Portable negative controls only; never admit a real product or execute Apple tests."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
HISTORICAL = Path(os.environ.get("PINKHA_WAVE3_HISTORICAL_COMMON",
                               HERE.parent / "materialized-control/combined_heart_semantics_current.py"))
INPUTS_ROOT = Path(os.environ.get("PINKHA_WAVE3_PREPARATION_INPUTS", HERE / "original-inputs"))
spec = importlib.util.spec_from_file_location("wave3_materializer_control", HERE / "materialize_wave3_intake.py")
materializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(materializer)


class ClosedWave3IntakeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = HISTORICAL.read_bytes()
        cls.fragment = (HERE / "wave3_intake.py").read_bytes()
        cls.embedded = {key: (INPUTS_ROOT / value[0]).read_text()
                        for key, value in materializer.INPUTS.items()}
        cls.profile = json.loads((HERE / "frozen-profile.closed.json").read_text())

    def module(self, profile=None):
        candidate, proof = materializer.compose(self.original, self.fragment, self.embedded, profile or self.profile)
        result = types.ModuleType("synthetic_closed_intake_control")
        result.__file__ = str(HERE / "NEVER_EXECUTED_COMMON_MAIN.py")
        exec(compile(candidate, result.__file__, "exec"), result.__dict__)
        return result, candidate, proof

    def test_closed_public_and_qualification_entries_cannot_read_or_clone(self):
        module, candidate, proof = self.module()
        def forbidden(*args, **kwargs):
            self.fail("Closed profile reached file/product or process activity")
        module.pinned = module.raw = module.inventory = forbidden
        module._W3_ORIGINAL_CLONER = module._W3_ORIGINAL_RUNTIME = module._W3_ORIGINAL_COMPILER = forbidden
        entries = ((module.admit_and_clone_products, ({}, None, None, None)),
                   (module.admit_app16_and_clone_products, ({}, None, None, None)),
                   (module.qualify_app16_producer, ({}, None, None)),
                   (module.qualify_app16_runtime, ({}, None)),
                   (module.qualify_app16_compiler_inputs, ({}, None, None)))
        for entry, arguments in entries:
            with self.subTest(entry=entry.__name__), self.assertRaisesRegex(ValueError, "Wave3 runtime intake is closed"):
                entry(*arguments)
        position, length = proof["insertionCharacterOffset"], proof["insertionCharacterLength"]
        text = candidate.decode()
        self.assertEqual((text[:position] + text[position + length:]).encode(), self.original)
        self.assertEqual(proof["runtimeGuard"], "CLOSED_BEFORE_ANY_PRODUCT_READ_OR_COMMAND")
        self.assertFalse(proof["actualProductAdmitted"])
        self.assertEqual(proof["additionalRuntimeSiblingPythonFiles"], [])

    def test_source_override_and_unsealed_ready_profile_are_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["sourceCommit"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "literal exact6aab/385"):
            self.module(changed)
        changed = copy.deepcopy(self.profile)
        changed["readyForRuntimeAdmission"] = True
        with self.assertRaisesRegex(ValueError, "Closed actual producer/evidence profile"):
            self.module(changed)

    def test_changed_historical_or_embedded_validator_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Historical4ec"):
            materializer.compose(self.original + b"\n", self.fragment, self.embedded, self.profile)
        changed = dict(self.embedded)
        changed["receipt_admission"] += "\n"
        with self.assertRaisesRegex(ValueError, "Exact original Wave3 gate"):
            materializer.compose(self.original, self.fragment, changed, self.profile)

    def test_failure_receipt_cannot_become_runtime_admission(self):
        module, _, _ = self.module()
        with tempfile.TemporaryDirectory(prefix="synthetic-wave3-failure-control-") as temporary:
            root = Path(temporary).resolve()
            receipt = root / "synthetic-failed-build.json"
            receipt.write_text(json.dumps({"status": "FAIL", "sourceCommit": materializer.SOURCE,
                                           "error": "synthetic app FAIL_BUILD"}) + "\n")
            pin = {"path": str(receipt), "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                   "bytes": receipt.stat().st_size}
            profile = copy.deepcopy(self.profile)
            profile["readyForRuntimeAdmission"] = True
            profile["evidence"]["producerReceipt"] = pin
            profile["evidence"]["app16Producer"] = {key: None for key in module.W3_PRODUCER_KEYS}
            module.W3_FROZEN = profile
            admission = dict(profile["evidence"], sourceCommit=materializer.SOURCE, nativeManifestSHA256=module.MANIFEST)
            def forbidden(*args, **kwargs):
                self.fail("Failed producer reached deeper qualification or cloning")
            module.qualify_app16_producer = forbidden
            with self.assertRaisesRegex(ValueError, "Successful source-bound App16 combined build required"):
                module.admit_and_clone_products(admission, root, None, None)
            admission["producerReceipt"] = dict(pin, sha256="0" * 64)
            with self.assertRaisesRegex(ValueError, "admission differs"):
                module.admit_and_clone_products(admission, root, None, None)

    def test_materialization_preserves_inputs_and_refuses_output_reuse(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-wave3-materialization-control-") as temporary:
            root = Path(temporary).resolve()
            output = root / "closed"
            frozen = HERE / "frozen-profile.closed.json"
            arguments = (HISTORICAL, INPUTS_ROOT, frozen, hashlib.sha256(frozen.read_bytes()).hexdigest(), output)
            proof = materializer.prepare(*arguments)
            self.assertEqual((output / "combined_heart_semantics_a089_preserved.py").read_bytes(), self.original)
            self.assertEqual((output / "frozen-profile.json").read_bytes(), frozen.read_bytes())
            self.assertEqual(hashlib.sha256((output / "combined_heart_semantics_current.py").read_bytes()).hexdigest(),
                             proof["candidateSHA256"])
            with self.assertRaisesRegex(ValueError, "Fresh owned preparation output"):
                materializer.prepare(*arguments)


if __name__ == "__main__":
    unittest.main(verbosity=2)
