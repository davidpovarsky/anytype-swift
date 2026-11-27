#!/usr/bin/env python3
"""Portable admission controls only. No app build, device or XCTest execution."""
from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
CONFIG = None


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class App16IntakeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.materializer = module("app16_materializer_control", PACKAGE / "materialize_app16_control.py")
        m = cls.materializer
        cls.originals = {name: (CONFIG.original_control / name).read_bytes() for name in m.ORIGINALS}
        cls.host = CONFIG.canonical_host.read_bytes()
        cls.fragment = (PACKAGE / "app16_intake.py").read_bytes()
        cls.focus = (PACKAGE / "focus_lifecycle_profile.py").read_bytes()
        cls.values, cls.proof = m.compose(cls.originals, cls.fragment, cls.host, cls.focus)
        cls.shared = module("app16_shared_control", CONFIG.materialized_control / "combined_heart_semantics_current.py")
        if cls.shared.sha((CONFIG.materialized_control / "combined_heart_semantics_current.py").read_bytes()) != cls.proof["files"]["combined_heart_semantics_current.py"]:
            raise AssertionError("Materialized common module differs from the exact composed control")

    def test_original_definitions_and_exact_method_scope_survive(self):
        m = self.materializer
        old = self.originals["combined_heart_semantics_current.py"]
        new = self.values["combined_heart_semantics_current.py"]
        span = self.proof["sharedInsertion"]
        offset, length = span["offset"], span["bytes"]
        self.assertEqual(new[:offset] + new[offset + length:], old)
        self.assertEqual(len(m.definitions(old)), 26)
        for original in m.definitions(old):
            self.assertEqual(m.definitions(new).count(original), 1)
        def plans(value):
            return next(ast.literal_eval(node.value) for node in ast.parse(value).body
                        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "PLANS" for target in node.targets))
        original_plans = plans(self.host)
        actual_plans = plans(self.values["combined_host_acceptance_app15.py"])
        self.assertEqual({key: actual_plans[key] for key in original_plans}, original_plans)
        self.assertEqual(set(actual_plans) - set(original_plans), {"t5-remaining-freshness-only"})
        self.assertEqual(actual_plans["t5-remaining-freshness-only"], ("t5-remaining-freshness",))
        # All control, result and enumeration functions retain their canonical
        # a089 bodies; execute_lane changes only the inaccurate scope sentence.
        def funcs(value):
            text = value.decode()
            return {node.name: ast.get_source_segment(text, node) for node in ast.walk(ast.parse(text))
                    if isinstance(node, ast.FunctionDef)}
        before, after = funcs(self.host), funcs(self.values["combined_host_acceptance_app15.py"])
        self.assertEqual(set(before), set(after))
        for name in before:
            if name != "execute_lane":
                self.assertEqual(before[name], after[name], name)
        self.assertEqual(self.proof["focusMethods"], 22)
        self.assertEqual(self.proof["focusCases"], 34)

    def test_changed_original_and_old_profiles_are_rejected(self):
        m = self.materializer
        damaged = dict(self.originals)
        damaged["combined_t5_pending_gateway.py"] += b"\n"
        with self.assertRaisesRegex(ValueError, "Original control changed"):
            m.compose(damaged, self.fragment, self.host, self.focus)
        with self.assertRaisesRegex(ValueError, "a089 host"):
            m.compose(self.originals, self.fragment, self.originals["combined_host_acceptance_app15.py"], self.focus)
        with self.assertRaisesRegex(ValueError, "22-method/34-case"):
            m.compose(self.originals, self.fragment, self.host, self.originals["focus_lifecycle_profile.py"])
        with self.assertRaisesRegex(ValueError, "additive App16 intake changed"):
            m.compose(self.originals, self.fragment + b"\n", self.host, self.focus)

    def test_cache_absence_cannot_be_reported_as_warm_reuse(self):
        s = self.shared
        cache = json.loads(CONFIG.cache_qualification.read_bytes())
        self.assertEqual(s.sha(CONFIG.cache_qualification.read_bytes()), s.APP16_CACHE_QUALIFICATION)
        derived = str(Path(cache["observedPaths"]["products"]["path"]).parent.parent)
        inputs = {"appDerived": derived, "originalIntermediatesAndPackagePathsReused": False,
                  "phaseGrowthAllowanceBytes": {"app": 6 * 1024**3, "ui": 1024**3},
                  "concurrentGrowthAllowanceBytes": 512 * 1024**2}
        s.qualify_app16_cache(cache, inputs)
        changes = (
            ("originalIntermediatesAndPackagePathsReused", True),
            ("stageSourceAndNativePreservationRetained", False),
            ("invalidatedStageMetadata", []),
            ("estimateNewAppPhaseBytes", 3 * 1024**3),
            ("emergencyFloorBytes", 1024**3),
        )
        for key, value in changes:
            candidate = copy.deepcopy(cache)
            candidate[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                s.qualify_app16_cache(candidate, inputs)
        for name in ("intermediates", "sourcePackages"):
            candidate = copy.deepcopy(cache)
            candidate["observedPaths"][name]["exists"] = True
            with self.subTest(path=name), self.assertRaises(ValueError):
                s.qualify_app16_cache(candidate, inputs)
        with self.assertRaises(ValueError):
            s.qualify_app16_cache(cache, dict(inputs, originalIntermediatesAndPackagePathsReused=True))

    def test_incomplete_and_old_producers_fail_before_source_or_execution(self):
        s = self.shared
        keys = {"builder", "builderDelta", "stagingScript", "stagingInput", "stagingReceipt",
                "preservationReceipt", "cacheQualification", "phaseReceipts", "compilerInputs", "compilerFileLists"}
        admission = {"sourceCommit": s.APP16_SOURCE, "app16Producer": {key: {} for key in keys}}
        receipt = {"sourceCommit": s.APP16_SOURCE,
                   "status": "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"}
        with patch.object(s.subprocess, "check_output", side_effect=AssertionError("No process may run in negative controls")):
            for candidate in ({"sourceCommit": s.APP16_SOURCE},
                              dict(admission, sourceCommit=s.APP16_PREVIOUS),
                              dict(admission, uiContinuation={})):
                with self.subTest(admission=candidate), self.assertRaises(ValueError):
                    s.qualify_app16_producer(candidate, Path("/not-an-actual-producer"), receipt)
            with self.assertRaises(ValueError):
                s.qualify_app16_producer(admission, Path("/not-an-actual-producer"),
                                         dict(receipt, status="PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"))
            old_builder = b"This is deliberately not the admitted builder."
            delta = json.dumps({"candidateSHA256": s.sha(old_builder)}).encode()
            with patch.object(s, "pinned", side_effect=[old_builder, delta]), self.assertRaises(ValueError):
                s.qualify_app16_producer(admission, Path("/not-an-actual-producer"),
                                         dict(receipt, controllerSHA256=s.sha(old_builder)))
        marker = object()
        with patch.object(s, "admit_app15_original_products", return_value=marker) as original:
            self.assertIs(s.admit_and_clone_products({"sourceCommit": s.APP16_PREVIOUS}, None, None, None), marker)
            original.assert_called_once()
            with self.assertRaises(ValueError):
                s.admit_and_clone_products(dict(admission, sourceCommit=s.APP16_PREVIOUS), None, None, None)


def main():
    global CONFIG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-control", type=Path, required=True)
    parser.add_argument("--canonical-host", type=Path, required=True)
    parser.add_argument("--materialized-control", type=Path, required=True)
    parser.add_argument("--cache-qualification", type=Path, required=True)
    CONFIG = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(App16IntakeControls))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
