"""One new ordering composition control; no simulator or product execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import coherent_fresh_construction as construction
import owned_simulator_readiness  # Preload the unchanged real guard's lazy dependency.
import run_ui27 as ui
import test_coherent_owned_continuation as fixture
import wave15_batch as batch

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/validation/20261123-release-selection-order"
CALLER = ROOT / "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py"
ACTUAL_PLAN = DOC / "actual-attempt2/private-originals/lanes/editor/selection-plan.json"
INITIAL_SHA = "c09670cd6fb4c55a8130506dda2bdaaf607a4d7698c386de4a18d0e68b392cc1"
FINAL_SHA = "0d202e0880ccd347684201a4947e151b74a7cbcc81d291f644eab2668cc8ce4f"


def live_region():
    """Execute only the actual caller's language/construction statements."""
    source = CALLER.read_bytes()
    tree = ast.parse(source, filename=str(CALLER))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
    def calls(node, attribute):
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == attribute for n in ast.walk(node))
    starts = [i for i, node in enumerate(function.body) if calls(node, "confirm_empty_container")]
    stop = next(i for i, node in enumerate(function.body) if calls(node, "prepare_source_cache"))
    if len(starts) != 2 or not starts[0] < starts[1] < stop:
        raise AssertionError("The frozen original-only caller region changed")
    nodes = function.body[starts[0]:stop]
    return compile(ast.Module(body=nodes, type_ignores=[]), str(CALLER), "exec"), {
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "first_line": nodes[0].lineno, "last_line": nodes[-1].end_lineno,
        "scope": "EXACT_CALLER_LANGUAGE_AND_CONSTRUCTION_REGION_ONLY",
    }


class NativeBoundaryReached(Exception):
    """Injected boundary after the real one-shot preparation guard, before native work."""


class ReleaseSelectionOrderTests(unittest.TestCase):
    def test_final_editor_plan_precedes_owned_seal_and_native_admission(self):
        code, region = live_region()
        actual = json.loads(ACTUAL_PLAN.read_bytes())
        self.assertEqual(hashlib.sha256(ACTUAL_PLAN.read_bytes()).hexdigest(), FINAL_SHA)
        initial = dict(actual)
        initial["device_language_verified"] = False
        initial.pop("device_language")
        initial.pop("device_language_scope")
        self.assertEqual(hashlib.sha256((json.dumps(initial, indent=2) + "\n").encode()).hexdigest(), INITIAL_SHA)
        method = actual["preparation"]
        self.assertEqual(method, "PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState")
        for scenario in ("successful_language_then_guard", "language_failure_before_seal", "post_seal_plan_drift"):
            with self.subTest(scenario=scenario), mock.patch.dict(os.environ, fixture.ENV), \
                    tempfile.TemporaryDirectory(prefix="release-selection-order-") as temporary:
                f = fixture.fixture(Path(temporary))
                commands = fixture.Commands(f)
                events = []
                first_error = RuntimeError("injected original language observation failure")
                boundary = NativeBoundaryReached("native work deliberately not executed")
                delegated = []
                try:
                    with commands.patch():
                        device = construction.create(f.origin, f.intent, f.planned, f.directory)
                        context = fixture.ready(f, device)
                        ui.write(f.directory / "selection-plan.json", dict(initial))
                        self.assertEqual(fixture.digest(f.directory / "selection-plan.json"), INITIAL_SHA)

                        def configure(app, evidence, udid, language):
                            self.assertEqual((app, evidence, udid, language),
                                             (f.app, f.directory, fixture.UDID, "en"))
                            self.assertFalse((f.directory / "fresh-container.json").exists())
                            events.append("EXISTING_LANGUAGE_CALLBACK")
                            if scenario == "language_failure_before_seal":
                                raise first_error
                            return {"device_language": "he",
                                    "verification_scope": "SIMULATOR_GLOBAL_PREFERENCES_AFTER_REBOOT"}

                        def write(path, value):
                            ui.write(path, value)
                            if path.name == "selection-plan.json":
                                events.append("FINAL_LANGUAGE_PLAN_WRITTEN")

                        def no_process(*args, **kwargs):
                            raise AssertionError("No simulator/host command may run in this control")

                        namespace = {
                            "build_context": context,
                            "original_products": isinstance(context, fixture.products.OriginalProductsContext),
                            "args": SimpleNamespace(lane="editor", language="en"),
                            "app": f.app, "evidence": f.directory, "udid": fixture.UDID,
                            "selection": dict(initial), "receipt": {},
                            "shared": SimpleNamespace(write=write),
                            "configure_editor_device_language": configure,
                            "subprocess": SimpleNamespace(run=no_process),
                        }

                        def delegate(instance, app, configuration, blueprint, udid, selections,
                                     environment, evidence, prefix, app_path=None):
                            self.assertIs(instance, context)
                            self.assertEqual((app, configuration, blueprint, udid, selections, evidence, prefix),
                                             (f.app, f.native, "AnytypeTests", fixture.UDID,
                                              [method], f.directory / "preparation", "prepare"))
                            attempt = fixture.raw(f.directory / "construction/first-selection-attempt.json")
                            self.assertEqual(attempt["selection_plan_sha256"], FINAL_SHA)
                            self.assertEqual(attempt["methods"], [method])
                            self.assertFalse(attempt["installation_success_proved"])
                            self.assertFalse(attempt["product_pass_proved"])
                            delegated.append(attempt)
                            events.append("REAL_GUARD_ACCEPTED_BEFORE_INJECTED_NATIVE_BOUNDARY")
                            raise boundary

                        with mock.patch.object(batch.FrozenBuild, "run_selection", new=delegate):
                            if scenario == "language_failure_before_seal":
                                with self.assertRaises(RuntimeError) as observed:
                                    exec(code, namespace)
                                self.assertIs(observed.exception, first_error)
                                self.assertFalse((f.directory / "fresh-container.json").exists())
                                self.assertFalse((f.directory / "construction/first-selection-attempt.json").exists())
                                self.assertEqual(fixture.digest(f.directory / "selection-plan.json"), INITIAL_SHA)
                                self.assertEqual(events, ["EXISTING_LANGUAGE_CALLBACK"])
                            else:
                                exec(code, namespace)
                                fresh = fixture.raw(f.directory / "fresh-container.json")
                                self.assertEqual(fresh["selection_plan_sha256"], FINAL_SHA)
                                self.assertEqual(fixture.digest(f.directory / "selection-plan.json"), FINAL_SHA)
                                self.assertFalse(fresh["container_absence_proved"])
                                self.assertEqual(fresh["prior_owned_install_or_selection_attempts"], 0)
                                self.assertEqual(events, ["EXISTING_LANGUAGE_CALLBACK", "FINAL_LANGUAGE_PLAN_WRITTEN"])
                                events.append("REAL_CONSTRUCTION_SEAL_CREATED")
                                if scenario == "post_seal_plan_drift":
                                    changed = fixture.raw(f.directory / "selection-plan.json")
                                    changed["configuration_id"] += "-unadmitted-drift"
                                    ui.write(f.directory / "selection-plan.json", changed)
                                    with self.assertRaisesRegex(ValueError, "First selection is not the exact original native preparation"):
                                        context.run_selection(f.app, f.native, "AnytypeTests", fixture.UDID,
                                            [method], {}, f.directory / "preparation", "prepare")
                                    self.assertFalse((f.directory / "construction/first-selection-attempt.json").exists())
                                else:
                                    with self.assertRaises(NativeBoundaryReached) as observed:
                                        context.run_selection(f.app, f.native, "AnytypeTests", fixture.UDID,
                                            [method], {}, f.directory / "preparation", "prepare")
                                    self.assertIs(observed.exception, boundary)
                                    self.assertEqual(len(delegated), 1)
                                    self.assertTrue(f.origin._constructions[fixture.UDID.lower()]["first_selection_consumed"])
                            self.assertFalse(f.origin._constructions[fixture.UDID.lower()]["native_preparation_passed"])
                            if scenario != "successful_language_then_guard":
                                self.assertEqual(delegated, [])
                                self.assertFalse(f.origin._constructions[fixture.UDID.lower()]["first_selection_consumed"])
                    self.assertEqual([argv[:3] for argv, timeout in commands.calls], [["xcrun", "simctl", "create"]])
                finally:
                    fixture.save(f.directory / "new-ordering-control.json", {
                        "scope": "INJECTED_COMMAND_AND_LANGUAGE_CONTROL_ONLY",
                        "scenario": scenario, "caller_region": region, "events": events,
                        "actual_simulator_commands_executed": 0, "actual_native_methods_executed": 0,
                        "actual_product_tests_executed": 0, "delegate_entries": len(delegated),
                        "original_failure_not_relabelled": True,
                    })
                    fixture.retain_control_outputs(f, "release-selection-order-" + scenario)


if __name__ == "__main__":
    unittest.main()
