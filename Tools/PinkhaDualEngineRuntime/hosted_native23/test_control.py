"""Portable controls for new boundaries only; no Apple/native/Swift execution."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import control
import native23_inputs

spec = importlib.util.spec_from_file_location("native23_tested_entry", Path(__file__).with_name("run.py"))
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class NewNative23Boundaries(unittest.TestCase):
    def test_complete_literal_inverse_preserves_original_run_bind_and_selectors(self):
        source = Path(os.environ["PINKHA_NATIVE23_ORIGINAL_CONTROL_SOURCE"])
        before = (source / control.RUNTIME).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            module, metadata = control.materialize(source, Path(directory) / "owned")
            candidate = Path(module.__file__).read_bytes()
            inverse = control.load_json(Path(control.__file__).with_name("runtime_inverse.json"))
            restored = candidate.decode()
            for row in reversed(inverse["patches"]):
                self.assertEqual(restored.count(row["after"]), 1)
                restored = restored.replace(row["after"], row["before"])
            self.assertEqual(restored.encode(), before)
            def functions(raw):
                text = raw.decode()
                return {node.name: ast.get_source_segment(text, node).encode() for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef)}
            old, new = functions(before), functions(candidate)
            self.assertEqual({name for name in old if old[name] != new[name]}, {"main", "native8ac_module"})
            self.assertEqual(hashlib.sha256(new["run"]).hexdigest(), control.RUN_SHA)
            self.assertEqual(old["bind"], new["bind"])
            tree = ast.parse(before)
            old_stages = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "STAGES" for t in n.targets))
            self.assertEqual(module.STAGES, old_stages)
            self.assertEqual(len(control.PLANS), 10)
            self.assertIn('timeout=360', new["main"].decode())
            self.assertIn('allowance + 300', new["main"].decode())
            profile, proof = control.selected_profile(source)
            self.assertFalse(profile.READY_FOR_EXECUTION)
            self.assertIsNone(profile.FUTURE_SOURCE_COMMIT)
            self.assertNotIn("configure", proof["reusedDeclarations"])
            self.assertTrue(proof["historicalReadyFlagUnchanged"])
            self.assertEqual(metadata["status"], "SOURCE_DERIVATIVE_NOT_RUNTIME_ACCEPTANCE")

    def test_unresolved_registry_forbids_direct_requalification_and_later_commands(self):
        calls, diagnostics = [], []
        bridge = types.SimpleNamespace(
            file_only_postflight=lambda: calls.append("file-only"),
            styled_process_closed=lambda: False,
            qualify_runtime_inputs=lambda *args: calls.append("FORBIDDEN-GIT-OR-SPAWN"))
        control.final_input_boundary(bridge, None, None, None, None, diagnostics)
        self.assertEqual(calls, ["file-only"])
        self.assertEqual(diagnostics[0]["phase"], "shared-command-requalification-withheld")
        real_bridge = object.__new__(entry.SameJobBridge)
        real_bridge.commands = types.SimpleNamespace(closed=False)
        with patch("subprocess.Popen", side_effect=AssertionError("No new command may spawn")), \
             patch("subprocess.check_output", side_effect=AssertionError("No direct Git may run")):
            with self.assertRaisesRegex(ValueError, "Unresolved original c249"):
                real_bridge.qualify_runtime_inputs(None, None, None)
        # The old registry owns its group; the new barrier never observes,
        # signals, relatches or clears an already recorded group.
        self.assertFalse(real_bridge.commands.closed)

    def test_receipt_failure_preserves_first_error_and_existing_evidence(self):
        primary = RuntimeError("original execution failed")
        writer_error = OSError("disk full")
        def broken(*args):
            raise writer_error
        diagnostics = []
        control.retain_native23_failure(broken, Path("unused"), {}, primary, diagnostics)
        receipt = {"status": "FAIL", "firstFailure": {"type": "RuntimeError", "reason": str(primary)}}
        observed = control.retain_native23_receipt(broken, Path("unused"), receipt, primary, diagnostics)
        self.assertIs(observed, primary)
        self.assertEqual(receipt["firstFailure"]["reason"], "original execution failed")
        self.assertEqual(receipt["status"], "FAIL")
        self.assertGreaterEqual(len(primary.__notes__), 2)
        cleanup = [{"phase": "owned-device-custody", "reason": "original unresolved group"}]
        observed = control.retain_native23_receipt(broken, Path("unused"), {"status": "FAIL"}, None, cleanup)
        self.assertIsNot(observed, writer_error)
        self.assertIn("original unresolved group", str(observed))
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "receipt.json"
            existing.write_bytes(b"retained-original\n")
            observed = control.retain_native23_receipt(control.exclusive, existing, receipt, primary, [])
            self.assertIs(observed, primary)
            self.assertEqual(existing.read_bytes(), b"retained-original\n")

    def test_closed_entry_precedes_external_input_or_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "no-output"
            argv = [str(Path(entry.__file__)), "--control", "/no-control", "--source", "/no-source",
                    "--plan", "/no-plan", "--plan-sha256", "0" * 64, "--build-root", "/no-build", "--output", str(out)]
            with patch.object(sys, "argv", argv), \
                 patch("subprocess.Popen", side_effect=AssertionError("closed entry spawned")), \
                 patch("subprocess.check_output", side_effect=AssertionError("closed entry ran Git")):
                with self.assertRaisesRegex(ValueError, "CLOSED_NATIVE23_SAME_JOB"):
                    entry.main()
            self.assertFalse(out.exists())

    def test_observed_runtime_and_family_are_not_legacy_aliases(self):
        runtime = {"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0", "version": "27.0",
                   "buildversion": "fixture-build-not-runtime-evidence", "isAvailable": True, "name": "iOS 27.0"}
        device = {"identifier": entry.DEFAULT_DEVICE, "name": "iPad Pro (13-inch)"}
        raw = json.dumps({"runtimes": [runtime]}).encode()
        types_raw = json.dumps({"devicetypes": [device]}).encode()
        self.assertEqual(entry.actual_runtime(raw, types_raw, "archive", None), (runtime, device, "ipad"))
        with self.assertRaisesRegex(ValueError, "One actual original"):
            entry.actual_runtime(json.dumps({"runtimes": [runtime, runtime]}).encode(), types_raw, "archive", None)
        with self.assertRaisesRegex(ValueError, "family differs"):
            entry.actual_runtime(raw, types_raw, "rtl", {"deviceType": entry.DEFAULT_DEVICE, "deviceFamily": "iphone"})
        # A non-directory projection never purports to replace full mode/link
        # admission: the separate actual compiler validator still checks it.
        full = {"folder": {"kind": "directory", "mode": 448},
                "folder/data": {"kind": "file", "mode": 384, "bytes": 3, "sha256": "fixture"}}
        self.assertEqual(native23_inputs.product_entries(full), [
            {"path": "folder/data", "kind": "file", "bytes": 3, "sha256": "fixture"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
