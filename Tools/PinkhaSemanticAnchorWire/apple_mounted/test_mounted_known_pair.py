"""One new mounted caller/import composition control; no old pair suite or simulator runs."""
from __future__ import annotations
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REVIEW = ROOT / "docs/validation/20261123-semantic-page-mounted-known-pair/source-review.json"
ORIGINAL = ROOT / "docs/validation/20261123-page154-known-simulator"
HELPER_SHA256 = "3282bc162cef0486cd334fbdeb2ed2dcdf79980acf1e8d675badd26f273f56e1"
SELECTOR_SHA256 = "2309bb55b3752774bffc588a7c489392daa7ceb3b7279f6a9ec870899a1f1d5f"


class MountedKnownPairAdapterControl(unittest.TestCase):
    def test_mounted_import_and_owned_region_use_qualified_pair_without_fallback(self):
        # Import the real controller, through its actual repository-relative loader.
        # Any attempted external command during this control is a failure.
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected external command")):
            spec = importlib.util.spec_from_file_location("page154_mounted_pair_composed_control", HERE / "run.py")
            mounted = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mounted
            spec.loader.exec_module(mounted)
            self.assertEqual(mounted.ROOT, ROOT)
            self.assertEqual(mounted.consumer.ROOT, ROOT)
            self.assertEqual(Path(mounted.consumer.__file__).resolve(),
                             ROOT / "Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py")
            policy = mounted.consumer.consumer_simulator
            self.assertEqual(Path(policy.__file__).resolve(),
                             ROOT / "Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_simulator.py")
            self.assertEqual(hashlib.sha256(Path(policy.__file__).read_bytes()).hexdigest(), HELPER_SHA256)
            self.assertEqual(Path(policy.simulator_selection.__file__).resolve(),
                             ROOT / "Tools/PinkhaSimulatorGate/simulator_selection.py")
            self.assertEqual(hashlib.sha256(Path(policy.simulator_selection.__file__).read_bytes()).hexdigest(),
                             SELECTOR_SHA256)

            # Exercise the real loaded-helper source guard with the frozen inputs.
            # The full checkout walk belongs to the real Mac controller; this
            # sparse Oracle control does not pretend to have a complete checkout.
            source = Path(mounted.consumer.__file__).read_text()
            checkout = next(n for n in ast.parse(source).body
                            if isinstance(n, ast.FunctionDef) and n.name == "checkout_inputs")
            guard = next(n for n in checkout.body
                         if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
                         and n.target.id == "module")
            checked = compile(ast.Module(body=[guard], type_ignores=[]),
                              str(mounted.consumer.__file__), "exec")
            inputs = json.loads(REVIEW.read_text())["source_sha256"]
            guard_context = dict(mounted.consumer.__dict__, root=ROOT, actual=copy.deepcopy(inputs))
            exec(checked, guard_context)
            guard_context["actual"][Path(policy.__file__).relative_to(ROOT).as_posix()] = "0" * 64
            with self.assertRaisesRegex(ValueError, "Loaded helper is not exact tracked source"):
                exec(checked, guard_context)

            # Execute the unchanged inventory/create/boot region from the real
            # mounted method with only its external runner replaced.
            source = (HERE / "run.py").read_text()
            function = next(n for n in ast.parse(source).body
                            if isinstance(n, ast.FunctionDef) and n.name == "execute")
            owner = next(n for n in function.body if isinstance(n, ast.Try)
                         and any(isinstance(c, ast.Assign)
                                 and any(isinstance(t, ast.Name) and t.id == "runtimes" for t in c.targets)
                                 for c in n.body))
            start = next(i for i, n in enumerate(owner.body) if isinstance(n, ast.Assign)
                         and any(isinstance(t, ast.Name) and t.id == "runtimes" for t in n.targets))
            end = next(i for i in range(start, len(owner.body))
                       if isinstance(owner.body[i], ast.Expr)
                       and any(isinstance(n, ast.Constant) and n.value == "wait-owned-simulator"
                               for n in ast.walk(owner.body[i])))
            region = compile(ast.Module(body=owner.body[start:end + 1], type_ignores=[]),
                             str(HERE / "run.py"), "exec")
            runtimes = json.loads((ORIGINAL / "original-page-available-runtimes.log").read_text())
            devices = json.loads((ORIGINAL / "original-page-available-device-types.log").read_text())
            self.assertTrue(any(v["version"] == "27.2" and v["isAvailable"] for v in runtimes["runtimes"]))
            fresh = "11111111-2222-4333-8444-555555555555"
            nonce = "a" * 32

            def exercise(runtime_input):
                queries, commands, receipt = [], [], {}
                with tempfile.TemporaryDirectory() as tmp:
                    created = Path(tmp) / "controlled-created-uuid.log"
                    created.write_text(fresh + "\n")
                    def query(argv, label, timeout=60):
                        queries.append((argv, label, timeout))
                        return copy.deepcopy(runtime_input if label == "available-runtimes" else devices)
                    def command(argv, label, timeout=60):
                        commands.append((argv, label, timeout))
                        return created, {"return_code": 0}
                    context = dict(mounted.__dict__, runner=SimpleNamespace(json=query, run=command),
                                   binding={"nonce": nonce}, receipt=receipt,
                                   owned_udid=None, creation_command=None)
                    failure = None
                    try:
                        exec(region, context)
                    except ValueError as error:
                        failure = error
                    return context, queries, commands, receipt, failure

            context, queries, commands, receipt, failure = exercise(runtimes)
            self.assertIsNone(failure)
            self.assertEqual([q[2] for q in queries], [60, 60])
            self.assertEqual(commands, [
                (["xcrun", "simctl", "create", "Page154Mounted-" + nonce,
                  policy.DEVICE_ID, policy.RUNTIME_ID], "create-owned-simulator", 60),
                (["xcrun", "simctl", "boot", fresh], "boot-owned-simulator", 90),
                (["xcrun", "simctl", "bootstatus", fresh, "-b"], "wait-owned-simulator", 180),
            ])
            self.assertEqual(context["creation_command"], commands[0][0])
            self.assertEqual(context["owned_udid"], fresh)
            self.assertEqual(receipt["owned_simulator"]["udid"], fresh)
            self.assertNotEqual(fresh, policy.ORIGIN["originalSimulatorUDID"])
            self.assertEqual(receipt["owned_simulator"]["selection"]["selectionPolicy"], policy.POLICY)
            self.assertEqual(receipt["owned_simulator"]["selection"]["runtimeBuild"], "24A434")

            missing = copy.deepcopy(runtimes)
            missing["runtimes"] = [v for v in missing["runtimes"] if v["identifier"] != policy.RUNTIME_ID]
            context, queries, commands, receipt, failure = exercise(missing)
            self.assertIsInstance(failure, ValueError)
            self.assertIn("not installed", str(failure))
            self.assertEqual(len(queries), 2)
            self.assertEqual(commands, [])
            self.assertEqual(receipt, {})
            self.assertIsNone(context["creation_command"])
            self.assertIsNone(context["owned_udid"])


if __name__ == "__main__":
    unittest.main()
