"""Portable source/closed-gate controls; never import or dispatch Apple runners."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

import g02_word_consumer as g
import g02_ui_receipts as ui
import materialize_g02_control as materializer


class ClosedControls(unittest.TestCase):
    def test_exact_inverse_and_existing_budget_delegation(self):
        original = Path(__file__).resolve().parent.parent / "materialized-control-attempt2/combined_host_acceptance_app15.py"
        prepared, proof = materializer.compose(original.read_bytes())
        self.assertTrue(proof["inverseRestoresEveryOriginalByte"])
        self.assertFalse(proof["runtimeReady"])
        def plans(raw):
            assignment = next(n for n in ast.parse(raw).body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == "PLANS" for t in n.targets))
            return ast.literal_eval(assignment.value)
        old_plans, new_plans = plans(original.read_text()), plans(prepared)
        self.assertEqual(new_plans, {**old_plans, g.PLAN: (g.LANE,)})
        calls = []
        sentinel = {"unchanged-original-budget": True}
        def old(target, methods):
            calls.append((target, methods)); return sentinel
        def require(value, reason):
            if not value: raise ValueError(reason)
        consumer = SimpleNamespace(admission={"plan": g.PLAN}, shared_module=SimpleNamespace(require=require),
                                   helpers={"run_ui27": SimpleNamespace(selection_time_budget=old)})
        old_method = "PinkhaNativeDerivedAcceptanceUITests/testSourceHeaderSelectionAndOverflow"
        self.assertIs(g.ui_budget(consumer, ui.TARGET, [old_method]), sentinel)
        self.assertEqual(calls, [(ui.TARGET, [old_method])])
        for phase in ("seed", "unlink"):
            self.assertEqual(g.ui_budget(consumer, ui.TARGET, [ui.METHODS[phase]])["maximum_seconds"], ui.ALLOWANCES[phase])
        self.assertEqual(len(calls), 1)
        consumer.admission["plan"] = "properties-only"
        with self.assertRaises(ValueError): g.ui_budget(consumer, ui.TARGET, [ui.METHODS["seed"]])

    def test_current_or_forged_future_admission_cannot_open_gate(self):
        for admission in ({"sourceCommit": "8f2c11713fb8a40ae13444104723666ffef68afe", "plan": g.PLAN},
                          {"sourceCommit": "f" * 40, "plan": g.PLAN, "runtimeReady": True, "nativeAdapter": {"sha256": "a" * 64}}):
            with self.assertRaisesRegex(ValueError, "G02_RUNTIME_CLOSED"):
                g.require_runtime_ready(admission, Path("/synthetic-no-product"))


if __name__ == "__main__": unittest.main(verbosity=2)
