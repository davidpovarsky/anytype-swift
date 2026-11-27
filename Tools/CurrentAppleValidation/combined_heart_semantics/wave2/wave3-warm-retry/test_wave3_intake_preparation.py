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
        with self.assertRaisesRegex(ValueError, "literal exact8f2/385"):
            self.module(changed)
        changed = copy.deepcopy(self.profile)
        changed["readyForRuntimeAdmission"] = True
        with self.assertRaisesRegex(ValueError, "Actual exact warm-retry receipt pins are pending"):
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
            with self.assertRaisesRegex(ValueError, "Actual exact warm-retry receipt pins are pending"):
                module.admit_and_clone_products(admission, root, None, None)
            admission["producerReceipt"] = dict(pin, sha256="0" * 64)
            with self.assertRaisesRegex(ValueError, "Actual exact warm-retry receipt pins are pending"):
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

    def test_exact_reviewed_warm_expansion_restores_both_original_producers(self):
        module, _, _ = self.module()
        def original(name):
            result = types.ModuleType("synthetic_original_" + name)
            result.__file__ = str(INPUTS_ROOT / (name + ".py"))
            exec(compile(self.embedded[name], result.__file__, "exec"), result.__dict__)
            return result
        adapter, warm = original("wave3_shared_build"), original("wave3_warm_retry")
        value = json.loads((INPUTS_ROOT / "wave3_build_admission.template.json").read_text())
        value.update(readyForBuild=True, appSourceSHA=materializer.SOURCE,
                     buildRoot=warm.FAILED_ROOT + "-synthetic-control")
        value["sourceStaging"]["sha256"] = "2" * 64
        value["cacheQualification"]["sha256"] = "3" * 64
        value["pins"]["sdkMaterializationReceiptSHA256"] = warm.SDK_MARKER_SHA
        selected = json.loads((INPUTS_ROOT / "warm-retry-compiler-inputs.json").read_text())
        for key in ("selectedNativeTestSources", "selectedUITestSources"):
            value[key] = selected[key]
        value["warmRetry"] = {"schema": "pinkha-terminal-failure-warm-retry-v1",
            "priorFailedSourceCommit": warm.FAILED_SOURCE, "priorBuildRoot": warm.FAILED_ROOT,
            "failedPreservation": {"path": warm.FAILED_ROOT + "/failed-preservation1/receipt.json",
                                   "sha256": warm.PRESERVATION_SHA},
            "concurrentGrowthAllowanceBytes": 2 * 1024 ** 3}
        with tempfile.TemporaryDirectory(prefix="synthetic-warm-inverse-control-") as directory:
            root = Path(directory).resolve()
            def retained(name, content):
                path = root / name
                path.write_bytes(content)
                return {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
            approval = retained("synthetic-admission.json", (json.dumps(value, sort_keys=True) + "\n").encode())
            candidate, delta = warm.expand(self.embedded["base_producer"], value,
                Path(approval["path"]), approval["sha256"], adapter, module.W3_ADAPTER_SHA)
            builder = retained("synthetic-expanded-producer.py", candidate.encode())
            difference = retained("synthetic-byte-inverse.json", (json.dumps(delta, sort_keys=True) + "\n").encode())
            # These isolated values exercise only the pure inverse validator.
            # The public common entry remains closed and no producer is run.
            module.W3_EXECUTED_PRODUCER_SHA, module.W3_EXECUTED_DELTA_SHA = builder["sha256"], difference["sha256"]
            contract = {"builder": builder, "builderDelta": difference, "buildAdmission": approval}
            receipt = {"controllerSHA256": builder["sha256"]}
            proof = module.w3_three_stage_inverse(contract, receipt, value, adapter, warm)
            self.assertTrue(proof["fullOriginalProducerInverse"])
            self.assertEqual(proof["originalProducerSHA256"], module.W3_ORIGINAL_SHA)
            self.assertEqual(proof["originalPositionalSpans"], 90)
            self.assertGreater(proof["warmRetryInverseChanges"], 0)
            self.assertEqual(proof["unchangedFunctions"], ["run_phase", "source_state"])
            with self.assertRaisesRegex(ValueError, "runtime intake is closed"):
                module.admit_and_clone_products({}, None, None, None)
            changed = candidate.replace('wr_validate_cache(cache,staging)', 'None # cache gate removed', 1)
            contract["builder"] = retained("synthetic-changed-producer.py", changed.encode())
            with self.assertRaisesRegex(ValueError, "exact reviewed root-bound expansion"):
                module.w3_three_stage_inverse(contract, receipt, value, adapter, warm)

    def test_stale_cache_and_foreign_external_control_are_rejected(self):
        module, _, _ = self.module()
        with tempfile.TemporaryDirectory(prefix="synthetic-warm-custody-control-") as directory:
            root = Path(directory).resolve()
            path = root / "wave3_warm_retry.py"
            path.write_text(self.embedded["wave3_warm_retry"])
            pin = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
            warm = module.w3_external_module("wave3_warm_retry", pin)
            warm.WAVE3_ADMISSION = {"warmRetry": {}}
            warm.EXPECTED = materializer.SOURCE
            with self.assertRaisesRegex(ValueError, "Fresh post-failure warm-cache qualification"):
                warm.wr_validate_cache({"protocol": "app16-observed-cache-requalification-v1",
                                       "sourceCommit": materializer.SOURCE}, {})
            path.write_text(self.embedded["wave3_warm_retry"] + "\n")
            pin.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
            with self.assertRaisesRegex(ValueError, "Exact reviewed external warm control changed"):
                module.w3_external_module("wave3_warm_retry", pin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
