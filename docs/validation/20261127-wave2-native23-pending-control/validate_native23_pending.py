#!/usr/bin/env python3
"""Narrow portable controls of the five-lane Native23 wiring; no backend commands.

Actual generated runner branch statements and the unchanged c249 registry execute
against a synthetic Popen/lifecycle. No product admission is replaced or opened.
The existing registry, source-inverse and collector control suites are not rerun.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
MATERIALIZED = ROOT / "materialized-closed1"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Core:
    @staticmethod
    def require(value, reason):
        if not value:
            raise RuntimeError(reason)

    @staticmethod
    def raw(path, limit=128 * 1024):
        value = path.read_bytes()
        Core.require(len(value) <= limit, "bounded synthetic-control input")
        return value

    @staticmethod
    def sha(value):
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def digest(path):
        return Core.sha(path.read_bytes())

    decode = staticmethod(json.loads)


P = load(ROOT / "native23_profile_closed.py", "pending23_profile_control")
R = load(ROOT / "native_styled_runtime.py", "pending23_registry_control")
M = load(ROOT / "native_rtl_matrix.py", "pending23_original_matrix_control")
S = load(MATERIALIZED / "run_prebuilt_native_ui16.py", "pending23_original_run_control")
SOURCE = (MATERIALIZED / "run_prebuilt_native_ui16.py").read_text()
MAIN = next(node for node in ast.parse(SOURCE).body if isinstance(node, ast.FunctionDef) and node.name == "main")


class Child:
    pid = 24021

    def __init__(self):
        self.exited = False

    def poll(self):
        return 0 if self.exited else None

    def wait(self, timeout=None):
        if not self.exited:
            raise R.subprocess.TimeoutExpired("synthetic-only", timeout)
        return 0


class Lifecycle:
    def __init__(self, absent):
        self.absent, self.terminations, self.observations = absent, [], []

    def _terminate_owned_process(self, process, outcome):
        self.terminations.append(process)
        process.exited = True

    def _observe_exited_group(self, group):
        self.observations.append(group)
        return {"status": "ABSENT_ESRCH" if self.absent else "PRESENT", "present": not self.absent,
                "syntheticControlOnly": True}


class Controls(unittest.TestCase):
    def test_original_lanes_cannot_receive_another_lanes_device_or_language_cell(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "cell.json"
            value = {"schema": "pinkha-native-rtl-cell-v1", "appLanguage": "he", "deviceFamily": "ipad",
                     "deviceType": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB",
                     "appearance": "light", "contentSize": "large"}
            path.write_text(json.dumps(value))
            for stage in P.PENDING_ORIGINAL_STAGES:
                with self.subTest(stage=stage):
                    args = types.SimpleNamespace(stage=stage)
                    if stage == "rtl":
                        with self.assertRaisesRegex(RuntimeError, "explicitly pinned RTL cell"):
                            P.execution_configuration(args, Core, M)
                        args.rtl_cell, args.rtl_cell_sha256 = path, Core.digest(path)
                        self.assertEqual(P.execution_configuration(args, Core, M), value)
                        args.styled_cell = path
                        with self.assertRaisesRegex(RuntimeError, "Styled cells cannot change"):
                            P.execution_configuration(args, Core, M)
                    else:
                        self.assertIsNone(P.execution_configuration(args, Core, M))
                        args.rtl_cell, args.rtl_cell_sha256 = path, Core.digest(path)
                        with self.assertRaisesRegex(RuntimeError, "Only the original RTL and styled"):
                            P.execution_configuration(args, Core, M)
                        args.rtl_cell = args.rtl_cell_sha256 = None
                        args.styled_cell, args.styled_cell_sha256 = path, Core.digest(path)
                        with self.assertRaisesRegex(RuntimeError, "Only the original RTL and styled"):
                            P.execution_configuration(args, Core, M)

    def test_every_new_pending_execute_branch_uses_owned_cleanup_and_unresolved_device_guard(self):
        binding_nodes = [node for node in ast.walk(MAIN) if isinstance(node, ast.If)
                         and any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                                 and child.func.attr == "styled_owned_commands" for child in ast.walk(node))
                         and len(node.body) == 1 and isinstance(node.body[0], ast.Assign)]
        execute_nodes = [node for node in ast.walk(MAIN) if isinstance(node, ast.If)
                         and node.body and isinstance(node.body[0], ast.Assign)
                         and isinstance(node.body[0].value, ast.Call)
                         and isinstance(node.body[0].value.func, ast.Attribute)
                         and node.body[0].value.func.attr == "styled_execute"]
        final = next(node for node in MAIN.body if isinstance(node, ast.Try)).finalbody
        guards = [node for node in final if isinstance(node, ast.If)
                  and ast.unparse(node.test).startswith("udid is not None and")]
        self.assertEqual((len(binding_nodes), len(execute_nodes), len(guards)), (1, 1, 1))
        self.assertEqual(Core.digest(ROOT / "native_styled_runtime.py"),
                         "c249ab9d04b4f8014475cf1eb8b81cf0371cab40a3f98a77b2938a2a0f2b6714")
        for stage in P.PENDING_ORIGINAL_STAGES:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                out, child = Path(temporary).resolve(), Child()
                lifecycle = Lifecycle(absent=stage != "source-drag")
                first = OSError("synthetic original execute ledger failed after spawn: " + stage)
                P._state = {"args": types.SimpleNamespace(stage=stage), "shared": Core,
                            "styledRuntime": R, "styledOwned": None}
                namespace = {"args": P._state["args"], "current8ac": P, "run": S.run, "out": out,
                             "plan": ["synthetic-original-xcode"], "allowance": S.STAGES[stage][1],
                             "fixture_environment": {}, "udid": "synthetic-owned"}
                binding = {"syntheticControlOnly": True, "originalRunController": R.pin(Core, MATERIALIZED / "run_prebuilt_native_ui16.py"),
                           "runtimeAdapterSHA256": Core.digest(ROOT / "native_styled_runtime.py")}
                with mock.patch.object(R, "original_execution_binding", return_value=(lifecycle, binding)):
                    exec(compile(ast.Module(body=binding_nodes, type_ignores=[]), str(MATERIALIZED / "run_prebuilt_native_ui16.py"), "exec"), namespace)
                registry = P._state["styledOwned"]
                self.assertIs(namespace["run"].__self__, registry)
                with mock.patch.object(S.subprocess, "Popen", return_value=child) as popen, \
                     mock.patch.object(S, "write", side_effect=first), \
                     mock.patch.object(S.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)):
                    with self.assertRaises(OSError) as caught:
                        exec(compile(ast.Module(body=execute_nodes, type_ignores=[]), str(MATERIALIZED / "run_prebuilt_native_ui16.py"), "exec"), namespace)
                self.assertIs(caught.exception, first)
                self.assertEqual(popen.call_count, 1)
                self.assertEqual(lifecycle.terminations, [child])
                self.assertEqual(lifecycle.observations, [child.pid])
                self.assertEqual([entry["label"] for entry in registry.entries], ["execute"])
                self.assertEqual(registry.closed, lifecycle.absent)
                if not lifecycle.absent:
                    namespace["native8ac_module"] = lambda: P
                    exec(compile(ast.Module(body=guards, type_ignores=[]), str(MATERIALIZED / "run_prebuilt_native_ui16.py"), "exec"), namespace)
                    self.assertNotIn("sandbox", namespace)
                    with self.assertRaisesRegex(RuntimeError, "Further commands withheld"):
                        namespace["run"](["synthetic-must-not-shutdown"], out, "shutdown-simulator", cleanup=True)
                self.assertEqual(Core.decode((out / "styled-execute-closure.json").read_bytes())["originalException"]["reason"], str(first))
        P._state = None


if __name__ == "__main__":
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    record = {"schema": "native23-pending-lane-portable-controls/v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
              "scope": "SYNTHETIC_POPEN_AND_REAL_GENERATED_FIVE_LANE_DISPATCH_NO_APP_OR_NATIVE_ACCEPTANCE",
              "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "elapsedSeconds": time.monotonic() - started,
              "files": {name: Core.digest(ROOT / name) for name in ("native23_profile_closed.py", "native_styled_runtime.py",
                       "native_rtl_matrix.py", "validate_native23_pending.py", "materialized-closed1/run_prebuilt_native_ui16.py")},
              "backendProcessesSpawned": 0, "AppleBuilds": 0, "UIRuns": 0, "nativeCalls": 0, "settingsChanged": 0}
    with (ROOT / "pending-controls1.json").open("xb") as stream:
        stream.write((json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    sys.exit(0 if result.wasSuccessful() else 1)
