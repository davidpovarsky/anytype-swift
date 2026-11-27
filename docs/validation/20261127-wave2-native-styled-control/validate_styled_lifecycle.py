#!/usr/bin/env python3
"""Three portable controls of STYLED-RUN-01; every Popen is synthetic.

The real, byte-preserved original run() body and new runtime adapter execute
against a mocked child/lifecycle. No OS process, Apple command or device is
created by the tested controller. This is not a product or runtime receipt.
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


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load(ROOT / "native_styled_runtime.py", "styled_runtime_synthetic_lifecycle")
prior = load(ROOT / "validate_styled_preparation.py", "styled_prior_synthetic_utilities")
Core = prior.Core


class Child:
    def __init__(self, exited=False):
        self.pid = 24001
        self.exited = exited
        self.waits = []
    def poll(self):
        return 0 if self.exited else None
    def wait(self, timeout=None):
        self.waits.append(timeout)
        if not self.exited:
            raise R.subprocess.TimeoutExpired("synthetic-only", timeout)
        return 0


class Lifecycle:
    def __init__(self, group_absent=True):
        self.group_absent = group_absent
        self.terminations = []
        self.observations = []
    def _terminate_owned_process(self, process, record):
        self.terminations.append(process)
        # Match the original policy: an already-exited parent is never signaled.
        if process.poll() is None:
            process.exited = True
            record["termination"].append({"syntheticControlOnly": True, "pid": process.pid})
    def _observe_exited_group(self, group):
        self.observations.append(group)
        status = "ABSENT_ESRCH" if self.group_absent else "PRESENT"
        return {"status": status, "present": not self.group_absent,
                "observations": [{"status": status, "at": time.time(), "syntheticControlOnly": True}]}


class Controls(unittest.TestCase):
    def session(self, root, command=None):
        # Construct the instance from this exact loaded module; the earlier
        # harness utilities load another module object with identical bytes.
        ctx = prior.invocation()
        R.exclusive(Core, root / "styled-invocation.json", R.encoded(ctx))
        session = R.LiveSession(Core, {"actual_setting": lambda raw, expected, label: raw.strip()},
            command or prior.SyntheticRun(), root, ctx["simulatorUDID"], ctx,
            {"bundleIdentifier": "synthetic.tests.runner", "builtApplication": str(root / "Synthetic.app"),
             "builtExecutable": "Synthetic", "builtCodeCarriersSHA256": "9" * 64})
        return session

    def original(self):
        path = ROOT.parent / "library-search-ui/materialized3/run_prebuilt_native_ui16.py"
        module = load(path, "synthetic_original_native_run")
        text = path.read_text()
        declaration = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "run")
        self.assertEqual(Core.sha(ast.get_source_segment(text, declaration).encode()), R.ORIGINAL_RUN_SHA256)
        return module

    def test_first_post_spawn_io_error_survives_secondary_retention_and_closes_exact_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            module, child, lifecycle = self.original(), Child(), Lifecycle()
            original_error = OSError("synthetic execute.command receipt failed after Popen")
            session = self.session(root, module.run)
            session.runner_directory = lambda: (_ for _ in ()).throw(ValueError("secondary lookup error"))
            original_exclusive = R.exclusive
            def failed_retention(c, path, raw):
                if path.name == "styled-execute-closure.json":
                    raise OSError("secondary closure receipt write failed")
                return original_exclusive(c, path, raw)
            def failed_write(path, value):
                raise original_error
            with mock.patch.object(R, "original_execution_binding", return_value=(lifecycle, {"syntheticControlOnly": True})), \
                 mock.patch.object(module.subprocess, "Popen", return_value=child) as popen, \
                 mock.patch.object(module, "write", side_effect=failed_write), \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)), \
                 mock.patch.object(R, "exclusive", side_effect=failed_retention):
                with self.assertRaises(OSError) as caught:
                    session.execute(["synthetic-original-command"], 1, {})
            self.assertIs(caught.exception, original_error)
            self.assertEqual(popen.call_count, 1)
            self.assertIs(session.execution_boundary.process, child)
            self.assertEqual(lifecycle.terminations, [child])
            self.assertEqual(lifecycle.observations, [child.pid])
            self.assertTrue(session.process_closed)
            self.assertTrue(session.worker_returned.is_set())
            self.assertIn("secondary closure receipt write failed", [row["reason"] for row in session.errors])
            self.assertIs(module.run.__globals__["subprocess"], R.subprocess)

    def test_positive_absence_latches_before_later_original_result_write_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            module, child, lifecycle = self.original(), Child(exited=True), Lifecycle()
            error = OSError("synthetic execute.result write failed after positive absence")
            original_write = module.write
            def fail_after_absence(path, value):
                if path.name == "execute.result.json":
                    raise error
                return original_write(path, value)
            boundary = R.OwnedExecutionBoundary(Core, lifecycle, ["synthetic-original-command"], {"syntheticControlOnly": True})
            adapted = boundary.adapted(module.run)
            with mock.patch.object(module.subprocess, "Popen", return_value=child), \
                 mock.patch.object(module, "write", side_effect=fail_after_absence), \
                 mock.patch.object(module.shutil, "disk_usage", return_value=types.SimpleNamespace(free=4 * 1024**3)):
                # The isolated globals captured write before the mock; install
                # that same failure hook only in this test's isolated namespace.
                adapted.__globals__["write"] = fail_after_absence
                with self.assertRaises(OSError) as caught:
                    adapted(["synthetic-original-command"], root, "execute", timeout=1, allow_failure=True)
                proof = boundary.finish(None, caught.exception)
            self.assertIs(caught.exception, error)
            self.assertEqual(lifecycle.observations, [child.pid])
            self.assertEqual(lifecycle.terminations, [])
            self.assertTrue(boundary.closed)
            self.assertEqual(proof["ownedProcessGroup"], "ABSENT_ESRCH")
            self.assertIs(adapted.__code__, module.run.__code__)
            self.assertIsNot(adapted.__globals__, module.run.__globals__)

    def test_exited_parent_with_unresolved_group_withholds_settings_and_device_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            module, child, lifecycle = self.original(), Child(exited=True), Lifecycle(group_absent=False)
            boundary = R.OwnedExecutionBoundary(Core, lifecycle, ["synthetic-original-command"], {"syntheticControlOnly": True})
            boundary.process = child
            proof = boundary.finish(({"status": "FAIL"}, b""), None)
            self.assertFalse(boundary.closed)
            self.assertEqual(proof["status"], "UNRESOLVED_OWNED_PROCESS_CUSTODY")
            session = self.session(root)
            session.execution_boundary = boundary
            session.worker_returned.set()
            session.may_have_changed = True
            with self.assertRaisesRegex(RuntimeError, "coordination or final restoration failed"):
                session.finish()
            self.assertEqual(session.run.calls, [])
            retained = Core.decode((root / "styled-live-control.json").read_bytes())
            self.assertEqual(retained["status"], "FAIL")
            self.assertEqual(retained["finalRestore"]["withheldReason"], "UNRESOLVED_OWNED_EXECUTION_CUSTODY")
            # Execute the real materialized main's device-cleanup conditional in
            # isolation: an unresolved live group must enter none of its body.
            candidate = ROOT / "materialized-closed2/run_prebuilt_native_ui16.py"
            tree = ast.parse(candidate.read_text())
            main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
            final = next(n for n in main.body if isinstance(n, ast.Try)).finalbody
            guarded = [n for n in final if isinstance(n, ast.If) and ast.unparse(n.test).startswith("udid is not None and")]
            self.assertEqual(len(guarded), 1)
            namespace = {"udid": "synthetic-owned-uuid", "args": types.SimpleNamespace(stage="styled-live-type"),
                         "native8ac_module": lambda: types.SimpleNamespace(styled_process_closed=lambda: session.process_closed)}
            exec(compile(ast.Module(body=guarded, type_ignores=[]), str(candidate), "exec"), namespace)
            self.assertNotIn("sandbox", namespace)


if __name__ == "__main__":
    selected = sys.argv[1:] or [name for name in unittest.defaultTestLoader.getTestCaseNames(Controls)]
    suite = unittest.TestSuite(Controls(name) for name in selected)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {"schema": "native-styled-lifecycle-regression-control/v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
              "scope": "SYNTHETIC_POPEN_ORIGINAL_RUN_BODY_NO_BACKEND_PROCESS_OR_UI", "finding": "STYLED-RUN-01",
              "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "selectedMethods": selected,
              "elapsedSeconds": time.monotonic() - started,
              "files": {name: Core.digest(ROOT / name) for name in ("native_styled_runtime.py", "validate_styled_lifecycle.py",
                  "materialized-closed2/run_prebuilt_native_ui16.py")},
              "backendProcessesSpawned": 0, "AppleBuilds": 0, "UIRuns": 0, "settingsChanged": 0, "nativeCalls": 0}
    with (ROOT / "lifecycle-controls3.json").open("xb") as stream:
        stream.write((json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
    sys.exit(0 if result.wasSuccessful() else 1)
