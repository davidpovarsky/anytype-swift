#!/usr/bin/env python3
"""Focused portable controls of aggregate owned custody; all children are fake."""
from __future__ import annotations
import ast
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


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load(ROOT / "native_styled_runtime.py", "registry_runtime_under_test")
old = load(ROOT / "validate_styled_lifecycle.py", "retained_registry_utilities")
Core, Child, Lifecycle = old.Core, old.Child, old.Lifecycle


class Controls(unittest.TestCase):
    def registry(self, root):
        path = ROOT.parent / "library-search-ui/materialized3/run_prebuilt_native_ui16.py"
        module = load(path, "actual_original_registry_run")
        declaration = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "run")
        self.assertEqual(Core.sha(ast.get_source_segment(path.read_text(), declaration).encode()), R.ORIGINAL_RUN_SHA256)
        lifecycle = Lifecycle()
        binding = {"syntheticControlOnly": True, "originalRunController": R.pin(Core, path, 128 * 1024),
                   "originalRunDeclarationSHA256": R.ORIGINAL_RUN_SHA256,
                   "originalLifecycleSHA256": R.ORIGINAL_LIFECYCLE_SHA256,
                   "runtimeAdapterSHA256": Core.digest(ROOT / "native_styled_runtime.py")}
        with mock.patch.object(R, "original_execution_binding", return_value=(lifecycle, binding)):
            registry = R.OwnedCommands(Core, module.run, root)
        return registry, module, lifecycle

    def session(self, root, registry, stage="styled-live-type"):
        ctx = old.prior.invocation()
        ctx["method"] = R.STAGES[stage][0].split("/")[1]
        R.exclusive(Core, root / "styled-invocation.json", R.encoded(ctx))
        return R.LiveSession(Core, {"actual_setting": lambda raw, expected, label: raw.strip()},
            registry.run, root, ctx["simulatorUDID"], ctx,
            {"bundleIdentifier": "synthetic.tests.runner", "builtApplication": str(root / "Synthetic.app"),
             "builtExecutable": "Synthetic", "builtCodeCarriersSHA256": "9" * 64})

    def test_setter_post_spawn_error_preserves_first_exception_and_exact_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            registry, module, lifecycle = self.registry(root)
            child, first = Child(), OSError("synthetic setter ledger failed after spawn")
            def save_failure(c, path, raw):
                raise OSError("secondary synthetic closure write failed")
            with mock.patch.object(module.subprocess, "Popen", return_value=child), \
                 mock.patch.object(module, "write", side_effect=first), \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)), \
                 mock.patch.object(R, "exclusive", side_effect=save_failure):
                with self.assertRaises(OSError) as caught:
                    registry.run(["xcrun", "simctl", "ui", "synthetic-owned", "content_size", "large"],
                                 root, "styled-expanded-set", timeout=15)
            self.assertIs(caught.exception, first)
            self.assertEqual(lifecycle.terminations, [child])
            self.assertEqual(lifecycle.observations, [child.pid])
            self.assertTrue(registry.closed)
            self.assertEqual(registry.entries[0]["boundary"].record["originalException"]["reason"], str(first))
            self.assertIn("secondary synthetic closure write failed", [row["reason"] for row in registry.errors])
            with self.assertRaisesRegex(RuntimeError, "custody or retention failed"):
                registry.final_receipt()
            self.assertEqual(Core.decode((root / "styled-owned-commands.json").read_bytes())["status"], "FAIL")

    def test_readback_positive_absence_is_not_probed_again_after_result_io_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            registry, module, lifecycle = self.registry(root)
            child, first, original_write = Child(exited=True), OSError("synthetic readback result write failed"), module.write
            def fail_result(path, value):
                if path.name.endswith(".result.json"):
                    raise first
                return original_write(path, value)
            with mock.patch.object(module.subprocess, "Popen", return_value=child), \
                 mock.patch.object(module, "write", side_effect=fail_result), \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)):
                with self.assertRaises(OSError) as caught:
                    registry.run(["xcrun", "simctl", "ui", "synthetic-owned", "content_size"], root, "styled-expanded-read", timeout=15)
            self.assertIs(caught.exception, first)
            self.assertEqual(lifecycle.terminations, [])
            self.assertEqual(lifecycle.observations, [child.pid])
            self.assertTrue(registry.closed)
            self.assertEqual(registry.entries[0]["boundary"].record["ownedProcessGroup"], "ABSENT_ESRCH")

    def test_unresolved_setter_is_not_hidden_by_closed_xcode_and_blocks_both_device_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            registry, module, lifecycle = self.registry(root)
            first, second = Child(exited=True), Child(exited=True)
            second.pid = 24002
            with mock.patch.object(module.subprocess, "Popen", side_effect=[first, second]) as popen, \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)):
                passed, _ = registry.run(["synthetic-original-xcode"], root, "execute", allow_failure=True)
                self.assertEqual(passed["status"], "PASS")
                lifecycle.group_absent = False
                failed, _ = registry.run(["xcrun", "simctl", "ui", "synthetic-owned", "content_size", "large"],
                                         root, "styled-expanded-set", allow_failure=True)
                self.assertEqual(failed["status"], "FAIL")
                self.assertTrue(registry.entries[0]["boundary"].closed)
                self.assertFalse(registry.closed)
                session = self.session(root, registry)
                session.worker_returned.set()
                session.may_have_changed = True
                with self.assertRaisesRegex(RuntimeError, "coordination or final restoration failed"):
                    session.finish()
                with self.assertRaisesRegex(RuntimeError, "Further commands withheld"):
                    registry.run(["xcrun", "simctl", "shutdown", "synthetic-owned"], root, "must-not-shutdown", cleanup=True)
                self.assertEqual(popen.call_count, 2)
            self.assertEqual(len(registry.entries), 2)
            value = Core.decode((root / "styled-live-control.json").read_bytes())
            self.assertEqual(value["finalRestore"]["withheldReason"], "UNRESOLVED_OWNED_EXECUTION_CUSTODY")
            candidate = ROOT / "materialized-closed3/run_prebuilt_native_ui16.py"
            main = next(n for n in ast.parse(candidate.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "main")
            final = next(n for n in main.body if isinstance(n, ast.Try)).finalbody
            guard = [n for n in final if isinstance(n, ast.If) and ast.unparse(n.test).startswith("udid is not None and")]
            self.assertEqual(len(guard), 1)
            for stage in R.STAGES:
                namespace = {"udid": "synthetic-owned", "args": types.SimpleNamespace(stage=stage),
                             "native8ac_module": lambda: types.SimpleNamespace(styled_process_closed=lambda: registry.closed)}
                exec(compile(ast.Module(body=guard, type_ignores=[]), str(candidate), "exec"), namespace)
                self.assertNotIn("sandbox", namespace)

    def test_catalog_uses_same_owned_execution_without_live_request_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            registry, module, lifecycle = self.registry(root)
            session = self.session(root, registry, "styled-blocks")
            session.runner_directory = lambda: root / "synthetic-unused-rendezvous"
            child = Child(exited=True)
            with mock.patch.object(module.subprocess, "Popen", return_value=child), \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)):
                result, _ = session.execute(["synthetic-original-xcode"], 1, {})
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(registry.closed)
            self.assertEqual([entry["label"] for entry in registry.entries], ["execute"])
            report = session.finish()
            self.assertEqual(report["schema"], "native-styled-catalog-execution/v1")
            self.assertEqual(session.requests, [])
            self.assertFalse((root / "styled-live-control.json").exists())


if __name__ == "__main__":
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    record = {"schema": "native-styled-owned-registry-control/v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
              "scope": "SYNTHETIC_POPEN_ORIGINAL_RUN_AND_REAL_GENERATED_GUARDS_NO_BACKEND_OR_UI",
              "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "elapsedSeconds": time.monotonic() - started,
              "files": {name: Core.digest(ROOT / name) for name in ("native_styled_runtime.py", "validate_styled_registry.py",
                  "materialized-closed3/run_prebuilt_native_ui16.py")},
              "backendProcessesSpawned": 0, "AppleBuilds": 0, "UIRuns": 0, "settingsChanged": 0, "nativeCalls": 0}
    with (ROOT / "registry-controls4.json").open("xb") as stream:
        stream.write((json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
    sys.exit(0 if result.wasSuccessful() else 1)
