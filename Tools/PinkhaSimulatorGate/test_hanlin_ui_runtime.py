"""Deterministic controller controls; these are not Apple/native UI acceptance."""
import ast
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import hanlin_ui_runtime as gate
import run_ui27 as shared

UDID = "11111111-1111-1111-1111-111111111111"
METHOD = "HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation"
SOURCE = {"source_sha": "a" * 40, "run_id": "123", "run_attempt": "1", "kit_sha": shared.KIT,
          "native_marker": shared.MARKER, "candidate_inputs_sha256": "b" * 64}


def apple_now():
    return datetime.now(timezone.utc).timestamp() - gate.native.APPLE_DATE_EPOCH


def atomic_write(path, value):
    temporary = path.with_name(path.name + ".new")
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


class ObserverControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(strict=True)
        self.container = self.root / UDID / "data"
        self.support = self.container / gate.SUPPORT
        self.support.mkdir(parents=True)
        self.evidence = self.root / "evidence"; self.evidence.mkdir()
        self.fixture = {"fixtureID": "22222222-2222-2222-2222-222222222222", "sourceSHA": SOURCE["source_sha"],
            "runID": "123", "runAttempt": "1", "accountID": "original-account", "spaceID": "original-space",
            "sourceObjectID": "original-document"}
        self.raw_fixture = json.dumps(self.fixture)
        (self.support / gate.FIXTURE).write_text(self.raw_fixture)
        self.mapped_pids = []
        self.map_hook = lambda: None
        self.source_hook = lambda: None
        self.continuity_calls = []
        self.source_calls = 0
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        def installed(udid, evidence, built, source, **kwargs):
            self.assertEqual(udid, UDID); self.assertEqual(source, SOURCE)
            kwargs["command_timeout"](); self.source_calls += 1
            if self.source_calls > 1:
                self.source_hook()
            return {"installed_app": str(self.root / UDID / "bundle/Anytype.app"), **source,
                    "installed_app_executable_sha256": "a" * 64, "built_app_executable_sha256": "a" * 64,
                    "installed_code_carriers": {"sha256": "c" * 64},
                    "built_code_carriers": {"sha256": "c" * 64}}
        def mapped(pid, evidence, built, source, **kwargs):
            kwargs["command_timeout"](); self.mapped_pids.append(pid)
            self.map_hook()
            kwargs["command_timeout"]()
            return {"pid": pid, "process_start_identity": "actual-start-identity", **source,
                    "runtime_sha256": "c" * 64, "every_launch_verified": False}
        def continuity(evidence, prefix, live, methods, **kwargs):
            self.continuity_calls.append((live["pid"], methods, kwargs["scope"]))
            return {"status": "PASS", "pid": live["pid"]}
        self.shared = SimpleNamespace(write=write, installed_runtime_source=installed,
            observe_running_runtime=mapped, verify_ui_process_continuity=continuity)
        self.commands = []
        def query(argv, **kwargs):
            self.commands.append(argv)
            self.assertEqual(argv, ["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "data"])
            self.assertGreater(kwargs["timeout"], 0)
            self.assertLessEqual(kwargs["timeout"], gate.COMMAND_SECONDS)
            return str(self.container) + "\n"
        patcher = patch.object(gate.subprocess, "check_output", side_effect=query)
        patcher.start(); self.addCleanup(patcher.stop)
        self.observer = gate.NativeUIRuntimeObserver(UDID, self.evidence, self.root / "built", self.fixture,
            self.raw_fixture, SOURCE, self.shared)
        self.addCleanup(self.observer.stop)

    def phase(self):
        return {**{k: self.fixture[k] for k in ("fixtureID", "sourceSHA", "runID", "runAttempt")},
            "processID": 51457, "startedAt": apple_now(), "sessionID": "33333333-3333-3333-3333-333333333333",
            "navigationContext": {"app": "anytype", "account": self.fixture["accountID"],
                "workspace": self.fixture["spaceID"], "space": self.fixture["spaceID"],
                "sceneID": "44444444-4444-4444-4444-444444444444",
                "generation": "55555555-5555-5555-5555-555555555555",
                "objectReference": self.fixture["sourceObjectID"], "selectionReferences": [], "sourceRevision": "d" * 64},
            "phase": "AWAIT_READ_CONSENT", "providerConfigured": False}

    def observe(self):
        self.observer.start()
        self.value = self.phase()
        atomic_write(self.support / gate.RESULT, self.value)
        self.observer.thread.join(3)
        self.assertFalse(self.observer.thread.is_alive())
        self.observer.stop()

    def final(self):
        return {**self.value, "phase": "NATIVE_ACCEPTANCE_PASS", "finishedAt": apple_now()}

    def qualify(self, value):
        return self.observer.qualify(value, json.dumps(value).encode(), self.evidence / "ui",
                                     "wave15-hanlin-native", [METHOD])

    def test_only_actual_receipt_pid_is_mapped_and_final_native_bytes_remain_bound(self):
        self.observe()
        self.assertIsNone(self.observer.error)
        value = self.final(); atomic_write(self.support / gate.RESULT, value)
        raw = self.observer.final_bytes()
        result = self.observer.qualify(gate.decode(raw), raw, self.evidence / "ui", "wave15-hanlin-native", [METHOD])
        self.assertEqual(self.mapped_pids, [51457])
        self.assertEqual(result["status"], "PASS_ACTUAL_UI_PROCESS_RUNTIME")
        self.assertEqual(result["final_native_receipt_sha256"], gate.digest(raw))
        self.assertEqual(result["extra_app_launches"], 0)
        self.assertFalse(result["every_launch_verified"])
        self.assertEqual(self.continuity_calls, [(51457, [METHOD], "ACTUAL_COLD_LAUNCH_UI_METHOD_BOUNDARIES")])
        self.assertTrue(all("launch" not in argv and "terminate" not in argv for argv in self.commands))

    def test_mapping_uses_remaining_budget_without_extending_the_total_deadline(self):
        original = self.shared.observe_running_runtime
        observed = []
        def mapped(*args, **kwargs):
            limit = kwargs["command_timeout"]()
            observed.append(limit)
            self.assertGreater(limit, gate.COMMAND_SECONDS)
            self.assertLessEqual(limit, 20)
            return original(*args, **kwargs)
        self.shared.observe_running_runtime = mapped
        self.source_hook = lambda: setattr(self.observer, "deadline", time.monotonic() + 20)
        self.observe()
        self.assertIsNone(self.observer.error)
        self.assertEqual(len(observed), 1)
        self.assertEqual(self.mapped_pids, [51457])

    def test_preexisting_receipt_is_rejected_before_observer_or_mapping(self):
        atomic_write(self.support / gate.RESULT, self.phase())
        with self.assertRaisesRegex(RuntimeError, "pre-existing"):
            self.observer.start()
        self.assertIsNone(self.observer.thread)
        self.assertEqual(self.mapped_pids, [])

    def test_stale_wrong_source_and_already_finished_receipts_cannot_start_mapping(self):
        self.observer.started_at = datetime.now(timezone.utc).timestamp()
        for change in (lambda x: x.update(sourceSHA="f" * 40), lambda x: x.update(runID="999"),
                       lambda x: x.update(fixtureID="66666666-6666-6666-6666-666666666666"),
                       lambda x: x.update(startedAt=apple_now() - 10),
                       lambda x: x.update(phase="NATIVE_ACCEPTANCE_PASS", finishedAt=apple_now()),
                       lambda x: x.update(processID=True), lambda x: x.update(providerConfigured=True),
                       lambda x: x["navigationContext"].update(account="another-account")):
            value = self.phase(); change(value)
            with self.subTest(value=value), self.assertRaises((RuntimeError, ValueError)):
                gate.receipt_identity(value, self.fixture, self.observer.started_at,
                    datetime.now(timezone.utc).timestamp(), inflight=True)

    def test_changed_native_fixture_bytes_reject_before_any_mapping(self):
        (self.support / gate.FIXTURE).write_text(self.raw_fixture + " ")
        with self.assertRaisesRegex(RuntimeError, "fixture bytes"):
            self.observer.start()
        self.assertEqual(self.mapped_pids, [])

    def test_changed_pre_ui_executable_carriers_cannot_be_rebased_at_mapping(self):
        original = self.shared.installed_runtime_source
        def changed(*args, **kwargs):
            source = original(*args, **kwargs)
            if self.source_calls > 1:
                source["installed_code_carriers"]["sha256"] = "e" * 64
                source["built_code_carriers"]["sha256"] = "e" * 64
            return source
        self.shared.installed_runtime_source = changed
        self.observe()
        self.assertIsNone(self.observer.observation)
        self.assertIn("pre-UI validation", str(self.observer.error))
        self.assertEqual(self.mapped_pids, [])

    def test_another_simulators_application_path_cannot_qualify_the_ui_receipt(self):
        original = self.shared.installed_runtime_source
        def changed(*args, **kwargs):
            source = original(*args, **kwargs)
            if self.source_calls > 1:
                source["installed_app"] = "/owned-elsewhere/Anytype.app"
            return source
        self.shared.installed_runtime_source = changed
        self.observe()
        self.assertIsNone(self.observer.observation)
        self.assertIn("outside the owned simulator", str(self.observer.error))
        self.assertEqual(self.mapped_pids, [])

    def test_phase_update_is_allowed_but_native_identity_change_during_mapping_is_rejected(self):
        def change():
            value = gate.decode((self.support / gate.RESULT).read_bytes())
            value["processID"] += 1
            atomic_write(self.support / gate.RESULT, value)
        self.map_hook = change
        self.observe()
        self.assertIsNotNone(self.observer.error)
        self.assertIsNone(self.observer.observation)
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.qualify(self.final())

    def test_ordinary_atomic_phase_progress_preserves_one_process(self):
        def change():
            value = gate.decode((self.support / gate.RESULT).read_bytes())
            value["phase"] = "AWAIT_CANCEL_CREATE"
            atomic_write(self.support / gate.RESULT, value)
        self.map_hook = change
        self.observe()
        self.assertIsNone(self.observer.error)
        self.assertEqual(self.qualify(self.final())["live_runtime"]["pid"], 51457)

    def test_final_receipt_cannot_switch_pid_session_start_source_or_raw_bytes(self):
        self.observe()
        for change in (lambda x: x.update(processID=49959),
                       lambda x: x.update(sessionID="77777777-7777-7777-7777-777777777777"),
                       lambda x: x.update(startedAt=x["startedAt"] + 0.00001),
                       lambda x: x.update(sourceSHA="e" * 40)):
            value = self.final(); change(value)
            with self.subTest(value=value), self.assertRaises((RuntimeError, ValueError)):
                self.qualify(value)
        value = self.final()
        with self.assertRaisesRegex(RuntimeError, "bytes differ"):
            self.observer.qualify(value, json.dumps({**value, "processID": 49959}).encode(),
                                 self.evidence / "ui", "wave15-hanlin-native", [METHOD])

    def test_mapping_after_native_finish_is_not_retroactive_runtime_proof(self):
        self.observe(); value = self.final()
        value["finishedAt"] = self.observer.observation["mapping_completed_at"] - gate.native.APPLE_DATE_EPOCH - 1
        with self.assertRaisesRegex(RuntimeError, "during the actual"):
            self.qualify(value)

    def test_cancellation_joins_observer_without_launching_or_killing_any_app(self):
        self.observer.start(); self.observer.stop()
        self.assertFalse(self.observer.thread.is_alive())
        self.assertIsNone(self.observer.observation)
        self.assertEqual(self.mapped_pids, [])
        self.assertEqual(self.observer.summary()["status"], "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND")

    def ui_boundary_context(self, primary=None, console_error=None):
        # Execute the actual controller region, including any statements before
        # its finally. This reproduces interruption after a real worker starts.
        source = Path(__file__).with_name("run_wave15_acceptance.py")
        execute = next(node for node in ast.parse(source.read_text()).body
                       if isinstance(node, ast.FunctionDef) and node.name == "execute")
        first = next(index for index, node in enumerate(execute.body)
                     if isinstance(node, ast.Assign) and ast.unparse(node) == "receipt['phase'] = 'UI'")
        last = next(index for index in range(first, len(execute.body))
                    if isinstance(execute.body[index], ast.Try) and any(
                        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "export_ui_console" for node in ast.walk(execute.body[index])))
        region = ast.Module(body=execute.body[first:last + 1], type_ignores=[])
        console_exports, selections = [], []
        receipt = {}
        def selection(*args):
            selections.append(args)
            (self.support / gate.RESULT).write_bytes(b'{"failure":"controlled"}')
            if primary is not None:
                raise primary
            return {"status": "PASS", "passed": 1}
        def export_console(*args):
            console_exports.append(args)
            if console_error is not None:
                raise console_error
        context = {"ui_runtime_observer": self.observer, "receipt": receipt, "udid": UDID,
            "evidence": self.evidence, "hanlin_lane": (None, gate.RESULT, "native-result.json", "native"),
            "shared": SimpleNamespace(write=self.shared.write, export_ui_console=export_console), "sys": sys,
            "run_selection": selection, "app": self.root,
            "configuration": self.root / "tests.xctestrun", "selection": {"methods": [METHOD]},
            "environment": {}, "args": SimpleNamespace(lane="hanlin-native"), "built": self.root / "built"}
        return compile(region, str(source), "exec"), context, console_exports, selections

    def execute_ui_boundary(self, start):
        code, context, console_exports, selections = self.ui_boundary_context()
        with patch.object(threading.Thread, "start", start):
            try:
                exec(code, context)
            finally:
                self.assertTrue(self.observer.stop_event.is_set())
                self.assertEqual(selections, [])
                self.assertEqual(console_exports, [(UDID, self.evidence)])
                self.assertEqual(context["receipt"]["actual_ui_runtime_observation"]["status"],
                                 "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND")
                self.assertEqual((self.evidence / "native-result.json").read_bytes(), b'{"failure":"controlled"}')

    def test_partial_start_cancellation_joins_real_worker_and_exports_original_failure(self):
        started, exited = threading.Event(), threading.Event()
        original_start = threading.Thread.start
        def worker():
            started.set()
            self.observer.stop_event.wait(3)
            exited.set()
        self.observer.observe = worker
        def interrupted_start(thread):
            original_start(thread)
            self.assertTrue(started.wait(1))
            (self.support / gate.RESULT).write_bytes(b'{"failure":"controlled"}')
            raise KeyboardInterrupt("controlled partial start")
        with self.assertRaisesRegex(KeyboardInterrupt, "controlled partial start"):
            self.execute_ui_boundary(interrupted_start)
        self.assertTrue(exited.is_set())
        self.assertFalse(self.observer.thread.is_alive())
        self.assertEqual(self.mapped_pids, [])

    def test_failure_before_thread_start_preserves_error_and_failure_export(self):
        def failed_start(thread):
            (self.support / gate.RESULT).write_bytes(b'{"failure":"controlled"}')
            raise RuntimeError("controlled thread start failure")
        with self.assertRaisesRegex(RuntimeError, "controlled thread start failure"):
            self.execute_ui_boundary(failed_start)
        self.assertIsNone(self.observer.thread.ident)
        self.assertFalse(self.observer.thread.is_alive())
        self.assertEqual(self.mapped_pids, [])

    def exercise_finalizer_failure(self, stage, primary, secondary):
        self.observer.observe = lambda: self.observer.stop_event.wait(3)
        code, context, console_exports, selections = self.ui_boundary_context(primary)
        original_write = self.shared.write
        if stage == "observer_stop":
            def write(path, value):
                if path.name == "observation.json":
                    raise secondary
                return original_write(path, value)
            patcher = patch.object(self.shared, "write", side_effect=write)
        else:
            patcher = patch.object(self.observer, "final_bytes", side_effect=secondary)
        expected = primary if primary is not None else secondary
        with patcher as failed_action, self.assertRaises(type(expected)) as caught:
            exec(code, context)
        self.assertIs(caught.exception, expected)
        self.assertEqual(failed_action.call_count, 1)
        self.assertTrue(self.observer.stop_event.is_set())
        self.assertFalse(self.observer.thread.is_alive())
        self.assertEqual(len(selections), 1)
        self.assertEqual(console_exports, [(UDID, self.evidence)])
        self.assertEqual(context["receipt"]["actual_ui_runtime_finalizer"], {"status": "FAIL", "errors": [
            {"stage": stage, "error_type": type(secondary).__name__}]})
        self.assertIsNone(self.observer.observation)
        path = self.evidence / "native-result.json"
        if stage == "observer_stop":
            self.assertEqual(path.read_bytes(), b'{"failure":"controlled"}')
        else:
            self.assertFalse(path.exists())
        self.assertEqual(self.mapped_pids, [])

    def test_stop_write_error_preserves_primary_cancellation_and_exports_remaining_evidence(self):
        self.exercise_finalizer_failure("observer_stop", KeyboardInterrupt("original cancellation"),
                                        OSError("private secondary text must not be serialized"))

    def test_stop_write_error_without_primary_fails_closed_after_remaining_exports(self):
        self.exercise_finalizer_failure("observer_stop", None, OSError("controlled stop write"))

    def test_final_receipt_error_preserves_original_selection_failure(self):
        from run_wave15_acceptance import SelectionFailure
        self.exercise_finalizer_failure("native_receipt_export", SelectionFailure("original UI failure"),
                                        RuntimeError("private secondary text must not be serialized"))

    def test_atomic_receipt_replacement_preserves_primary_cancellation(self):
        self.exercise_finalizer_failure("native_receipt_export", KeyboardInterrupt("original cancellation"),
                                        gate.ReceiptReplaced())

    def test_final_receipt_error_without_primary_fails_closed(self):
        self.exercise_finalizer_failure("native_receipt_export", None, gate.ReceiptReplaced())

    def test_console_error_preserves_primary_and_still_exports_original_native_bytes(self):
        self.observer.observe = lambda: self.observer.stop_event.wait(3)
        primary = KeyboardInterrupt("original cancellation")
        code, context, exports, selections = self.ui_boundary_context(primary, OSError("private console error"))
        with self.assertRaises(KeyboardInterrupt) as caught:
            exec(code, context)
        self.assertIs(caught.exception, primary)
        self.assertEqual(exports, [(UDID, self.evidence)])
        self.assertEqual(len(selections), 1)
        self.assertEqual((self.evidence / "native-result.json").read_bytes(), b'{"failure":"controlled"}')
        self.assertEqual(context["receipt"]["actual_ui_runtime_finalizer"], {"status": "FAIL", "errors": [
            {"stage": "console_export", "error_type": "OSError"}]})

    def test_mapping_uses_the_same_deadline_and_cannot_qualify_after_timeout(self):
        self.source_hook = lambda: setattr(self.observer, "deadline", time.monotonic() - 1)
        self.observe()
        self.assertIsNotNone(self.observer.error)
        self.assertIsNone(self.observer.observation)
        self.assertEqual(self.mapped_pids, [])

    def test_poll_timeout_records_command_stage_and_bound_without_retry_or_mapping(self):
        command = ["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "data"]
        error = gate.subprocess.TimeoutExpired(command, 10, output=b"private stdout", stderr=b"private stderr")
        calls = []
        def query(argv, **kwargs):
            calls.append(argv)
            if len(calls) > 1:
                raise error
            return str(self.container) + "\n"
        with patch.object(gate.subprocess, "check_output", side_effect=query):
            self.observe()
        summary = self.observer.summary()
        failure = summary["diagnostics"]["first_failure"]
        self.assertIs(self.observer.error, error)
        self.assertEqual((failure["stage"], failure["command"], failure["command_timeout_seconds"]),
                         ("poll_data_container", command, 10))
        self.assertGreaterEqual(failure["stage_elapsed_seconds"], 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.mapped_pids, [])
        self.assertEqual(summary["diagnostics"]["partial_observations"], {})
        self.assertNotIn("private stdout", json.dumps(summary))
        self.assertNotIn("private stderr", json.dumps(summary))
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.qualify(self.final())

    def test_installed_source_timeout_retains_original_live_phase_without_qualifying_it(self):
        command = ["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "app"]
        error = gate.subprocess.TimeoutExpired(command, 10)
        def fail():
            raise error
        self.source_hook = fail
        self.observe()
        summary = self.observer.summary()
        diagnostics = summary["diagnostics"]
        partial = diagnostics["partial_observations"]["native_phase_before"]
        raw = (self.observer.directory / partial["file"]).read_bytes()
        self.assertEqual(gate.decode(raw), self.value)
        self.assertEqual(partial["sha256"], gate.digest(raw))
        self.assertEqual(partial["identity"]["processID"], self.value["processID"])
        self.assertEqual(diagnostics["first_failure"]["stage"], "map_installed_source")
        self.assertEqual(diagnostics["first_failure"]["command"], command)
        self.assertEqual(self.source_calls, 2)
        self.assertEqual(self.mapped_pids, [])
        self.assertIsNone(self.observer.observation)
        self.assertFalse((self.observer.directory / "native-phase-before.json").exists())
        self.assertFalse((self.observer.directory / "qualification.json").exists())
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.qualify(self.final())

    def test_vmmap_timeout_preserves_collected_source_and_does_not_rerun_mapping(self):
        command = ["/usr/bin/vmmap", "-w", "51457"]
        error = gate.subprocess.TimeoutExpired(command, 10)
        def fail():
            raise error
        self.map_hook = fail
        self.observe()
        diagnostics = self.observer.summary()["diagnostics"]
        self.assertEqual(diagnostics["first_failure"]["stage"], "map_running_process")
        self.assertEqual(diagnostics["first_failure"]["command"], command)
        self.assertEqual(set(diagnostics["partial_observations"]),
                         {"native_phase_before", "installed_source_returned"})
        self.assertEqual(self.mapped_pids, [51457])
        self.assertIs(self.observer.error, error)
        self.assertIsNone(self.observer.observation)

    def test_after_mapping_timeout_retains_mapping_metadata_but_cannot_be_a_pass(self):
        command = ["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "data"]
        error = gate.subprocess.TimeoutExpired(command, 10)
        def query(argv, **kwargs):
            if self.mapped_pids:
                raise error
            return str(self.container) + "\n"
        with patch.object(gate.subprocess, "check_output", side_effect=query):
            self.observe()
        diagnostics = self.observer.summary()["diagnostics"]
        self.assertEqual(diagnostics["first_failure"]["stage"], "after_mapping_data_container")
        self.assertEqual(diagnostics["partial_observations"]["runtime_mapping_returned"]["pid"], 51457)
        self.assertEqual(self.mapped_pids, [51457])
        self.assertIsNone(self.observer.observation)
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.qualify(self.final())

    def test_diagnostic_duration_is_stage_elapsed_and_first_failure_survives_later_reads(self):
        error = gate.subprocess.TimeoutExpired(["xcrun", "simctl", "get_app_container"], 10)
        def fail():
            raise error
        with patch.object(gate.time, "monotonic", side_effect=[100.0, 112.5]):
            with self.assertRaises(gate.subprocess.TimeoutExpired) as caught:
                self.observer.diagnostic_operation("poll_data_container", fail)
        self.assertIs(caught.exception, error)
        self.observer.diagnostic_operation("export_final_data_container", lambda: self.container)
        summary = self.observer.diagnostic_summary()
        self.assertEqual(summary["stage_duration_scope"], "ENTIRE_NAMED_OPERATION_NOT_INDIVIDUAL_SUBPROCESS")
        self.assertEqual(summary["first_failure"]["stage_elapsed_seconds"], 12.5)
        self.assertEqual(summary["first_failure"]["command_timeout_seconds"], 10)
        self.assertEqual(summary["first_failure"]["stage"], "poll_data_container")

    def test_repeated_polls_have_bounded_diagnostics_and_transient_reads_stay_distinct(self):
        for _ in range(2000):
            self.observer.diagnostic_operation("poll_data_container", lambda: self.container)
        error = gate.ReceiptReplaced()
        def replaced():
            raise error
        with self.assertRaises(gate.ReceiptReplaced) as caught:
            self.observer.diagnostic_operation("read_native_phase_before", replaced,
                                              transient=(FileNotFoundError, gate.ReceiptReplaced))
        self.assertIs(caught.exception, error)
        summary = self.observer.diagnostic_summary()
        self.assertIsNone(summary["first_failure"])
        self.assertEqual(len(summary["stages"]), 2)
        self.assertEqual(summary["stages"][0]["attempts"], 2000)
        self.assertEqual(summary["stages"][1]["status"], "TRANSIENT_READ")
        self.assertLess(len(json.dumps(summary)), 2048)
        with self.assertRaisesRegex(RuntimeError, "Unknown runtime diagnostic stage"):
            self.observer.diagnostic_operation("unbounded-dynamic-stage", lambda: self.fail("must not execute"))

    def test_diagnostic_command_overflow_and_private_error_text_are_not_published(self):
        error = gate.subprocess.CalledProcessError(9, ["oversized"] * 33,
            output=b"private command stdout", stderr=b"private command stderr")
        def fail():
            raise error
        with self.assertRaises(gate.subprocess.CalledProcessError):
            self.observer.diagnostic_operation("map_running_process", fail)
        summary = self.observer.diagnostic_summary()
        self.assertEqual(summary["first_failure"]["command"], "UNAVAILABLE_OR_OUTSIDE_DIAGNOSTIC_BOUND")
        self.assertEqual(summary["first_failure"]["command_exit_code"], 9)
        self.assertNotIn("private command", json.dumps(summary))

    def test_diagnostics_do_not_change_original_deadlines_or_add_a_launch(self):
        self.assertEqual((gate.COMMAND_SECONDS, gate.OBSERVATION_SECONDS, gate.MAPPING_SECONDS), (10, 420, 45))
        self.observe()
        self.assertIsNone(self.observer.error)
        self.assertIsNone(self.observer.summary()["diagnostics"]["first_failure"])
        self.assertEqual(self.mapped_pids, [51457])
        self.assertTrue(all("launch" not in command and "terminate" not in command for command in self.commands))
        self.assertEqual(self.qualify(self.final())["status"], "PASS_ACTUAL_UI_PROCESS_RUNTIME")

    def test_finalizer_export_timeout_is_persisted_after_exports_in_disk_and_execution_receipt(self):
        self.observe()
        receipt = {}
        command = ["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "data"]
        error = gate.subprocess.TimeoutExpired(command, 10)
        with patch.object(self.observer, "container", side_effect=error), self.assertRaises(gate.subprocess.TimeoutExpired) as caught:
            self.observer.finalize(receipt, self.evidence / "final.json", lambda: None, None)
        self.assertIs(caught.exception, error)
        on_disk = json.loads((self.observer.directory / "observation.json").read_text())
        self.assertEqual(on_disk, receipt["actual_ui_runtime_observation"])
        self.assertIsNotNone(on_disk["diagnostics"]["first_failure"])
        self.assertEqual(on_disk["diagnostics"]["first_failure"]["stage"], "export_final_data_container")
        self.assertEqual(on_disk["diagnostics"]["first_failure"]["command"], command)
        self.assertEqual(on_disk["status"], "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND")
        self.assertIn("runtime_mapping_returned", on_disk["diagnostics"]["partial_observations"])

    def test_boundary_timeout_is_persisted_in_disk_and_previously_finalized_execution_receipt(self):
        self.observe()
        receipt = {}
        self.observer.finalize(receipt, self.evidence / "final.json", lambda: None, None)
        error = gate.subprocess.TimeoutExpired(["xcrun", "simctl", "get_app_container", UDID, "io.anytype.app", "app"], 10)
        with patch.object(self.shared, "verify_ui_process_continuity", side_effect=error), self.assertRaises(gate.subprocess.TimeoutExpired) as caught:
            self.qualify(self.final())
        self.assertIs(caught.exception, error)
        on_disk = json.loads((self.observer.directory / "observation.json").read_text())
        self.assertEqual(on_disk, receipt["actual_ui_runtime_observation"])
        self.assertIsNotNone(on_disk["diagnostics"]["first_failure"])
        self.assertEqual(on_disk["diagnostics"]["first_failure"]["stage"], "verify_ui_process_boundaries")
        self.assertEqual(on_disk["diagnostics"]["first_failure"]["command"], error.cmd)
        self.assertFalse((self.observer.directory / "qualification.json").exists())

    def test_final_snapshot_write_failure_does_not_replace_the_original_export_timeout(self):
        self.observe()
        receipt = {}
        error = gate.subprocess.TimeoutExpired(["xcrun", "simctl", "get_app_container"], 10)
        original_write = self.shared.write
        writes = []
        def write(path, value):
            if path.name == "observation.json":
                writes.append(path)
                if len(writes) == 2:
                    raise OSError("private diagnostic write failure")
            return original_write(path, value)
        with patch.object(self.observer, "container", side_effect=error), patch.object(self.shared, "write", side_effect=write):
            with self.assertRaises(gate.subprocess.TimeoutExpired) as caught:
                self.observer.finalize(receipt, self.evidence / "final.json", lambda: None, None)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(writes), 2)
        self.assertEqual(receipt["actual_ui_runtime_observation"]["diagnostics"]["first_failure"]["stage"], "export_final_data_container")
        self.assertEqual(receipt["actual_ui_runtime_finalizer"]["errors"], [
            {"stage": "native_receipt_export", "error_type": "TimeoutExpired"},
            {"stage": "final_observer_snapshot", "error_type": "OSError"}])

    def test_boundary_diagnostic_write_failure_preserves_primary_and_success_cannot_write_qualification(self):
        self.observe()
        error = gate.subprocess.TimeoutExpired(["/bin/ps", "-p", "51457"], 10)
        with patch.object(self.shared, "verify_ui_process_continuity", side_effect=error), patch.object(self.shared, "write", side_effect=OSError("private diagnostic write failure")):
            with self.assertRaises(gate.subprocess.TimeoutExpired) as caught:
                self.qualify(self.final())
        self.assertIs(caught.exception, error)
        self.assertFalse((self.observer.directory / "qualification.json").exists())
        with patch.object(self.shared, "write", side_effect=OSError("private diagnostic write failure")):
            with self.assertRaises(OSError):
                self.qualify(self.final())
        self.assertFalse((self.observer.directory / "qualification.json").exists())

    def test_atomic_file_replacement_during_read_is_not_a_stable_snapshot(self):
        path = self.support / gate.RESULT; atomic_write(path, self.phase())
        original = os.fstat; calls = [0]
        def fstat(fd):
            calls[0] += 1
            if calls[0] == 2:
                value = self.phase(); value["processID"] = 49959; atomic_write(path, value)
            return original(fd)
        with patch.object(gate.os, "fstat", side_effect=fstat), self.assertRaises(gate.ReceiptReplaced):
            gate.stable_bytes(path)

    def test_duplicate_keys_and_symlinked_receipts_are_not_admitted(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate"):
            gate.decode(b'{"processID":1,"processID":51457}')
        target = self.root / "other.json"; target.write_text(json.dumps(self.phase()))
        path = self.support / gate.RESULT; path.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            gate.stable_bytes(path)


class TemporaryRootControls(unittest.TestCase):
    def test_real_temporary_parent_alias_is_resolved_without_relaxing_receipt_symlink_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve(strict=True)
            physical = parent / "physical"; physical.mkdir()
            alias = parent / "temporary-alias"; alias.symlink_to(physical, target_is_directory=True)
            original = tempfile.TemporaryDirectory
            created = []
            def aliased_temporary(*args, **kwargs):
                kwargs["dir"] = str(alias)
                value = original(*args, **kwargs)
                created.append(Path(value.name))
                return value
            subject = ObserverControls("test_atomic_file_replacement_during_read_is_not_a_stable_snapshot")
            result = unittest.TestResult()
            with patch.object(tempfile, "TemporaryDirectory", side_effect=aliased_temporary):
                subject.run(result)
            self.assertEqual(result.testsRun, 1)
            self.assertEqual(result.failures, [])
            self.assertEqual(result.errors, [])
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].parent, alias)
            self.assertEqual(subject.root.parent, physical)
            self.assertEqual(subject.root, subject.root.resolve())
            receipt = alias / "native-result.json"
            receipt.write_text('{"processID":51457}')
            with self.assertRaisesRegex(RuntimeError, "contains a symlink"):
                gate.stable_bytes(receipt)


class ExistingProcessMappingControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.built = self.root / "built/Anytype.app"
        self.installed = self.root / UDID / "bundle/Anytype.app"
        self.evidence = self.root / "evidence"; self.evidence.mkdir()
        relative = "Frameworks/ProtobufMessages.framework/ProtobufMessages"
        for app in (self.built, self.installed):
            (app / relative).parent.mkdir(parents=True)
            (app / relative).write_bytes(shared.MARKER.encode())
            (app / "Anytype").write_bytes(b"original executable bytes")
        self.carriers = {"sha256": "c" * 64, "manifest": {
            "carriers": {"Anytype": {}, relative: {}}, "aliases": {"Anytype": ["Anytype"], relative: [relative]}}}
        self.mapping = "Process [51457]\n" + str(self.installed / "Anytype") + "\n" + str(self.installed / relative) + "\n"
        self.identity = "Thu Nov 19 18:00:00 2026 " + str(self.installed / "Anytype")
        self.commands, self.starts = [], 0
        self.change_start = False
        self.wrong_executable = False
        def query(argv, **kwargs):
            self.commands.append((argv, kwargs.get("timeout")))
            if argv[:3] == ["xcrun", "simctl", "get_app_container"]:
                return str(self.installed) + "\n"
            if argv[:3] == ["xcrun", "simctl", "launch"]:
                return "io.anytype.app: 51457\n"
            self.assertEqual(argv[0], "ps")
            if "lstart=" in argv:
                self.starts += 1
                return self.identity + ("-changed" if self.change_start and self.starts > 1 else "")
            return "/another/Anytype" if self.wrong_executable else str(self.installed / "Anytype")
        def mapping(argv, **kwargs):
            self.commands.append((argv, kwargs.get("timeout")))
            self.assertEqual(argv, ["/usr/bin/vmmap", "-w", "51457"])
            return SimpleNamespace(returncode=0, stdout=self.mapping, stderr="")
        for patcher in (patch.object(shared.subprocess, "check_output", side_effect=query),
                        patch.object(shared.subprocess, "run", side_effect=mapping),
                        patch.object(shared, "code_carriers", side_effect=lambda _: copy.deepcopy(self.carriers))):
            patcher.start(); self.addCleanup(patcher.stop)

    def mapped(self):
        source = shared.installed_runtime_source(UDID, self.evidence, self.built, SOURCE,
                                                command_timeout=lambda: 7)
        return shared.observe_running_runtime(51457, self.evidence, self.built, source, command_timeout=lambda: 7)

    def hierarchies(self, entry=51457, final=51457):
        directory = self.evidence / "wave15-hanlin-native-attachments"; directory.mkdir(exist_ok=True)
        attachments = []
        for label, pid in (("entry-hierarchy", entry), ("final-hierarchy", final)):
            name = label + ".txt"
            (directory / name).write_text(f"Attributes: Application, 0x1234, pid: {pid}, label: 'Anytype'\n")
            attachments.append({"suggestedHumanReadableName": label, "exportedFileName": name})
        (directory / "manifest.json").write_text(json.dumps([{"testIdentifier": METHOD, "attachments": attachments}]))

    def continuity(self, live):
        return shared.verify_ui_process_continuity(self.evidence, "wave15-hanlin-native", live, [METHOD],
            scope="ACTUAL_COLD_LAUNCH_UI_METHOD_BOUNDARIES", command_timeout=lambda: 7)

    def test_existing_process_mapping_has_no_launch_and_each_command_is_bounded(self):
        live = self.mapped()
        self.assertEqual(live["pid"], 51457); self.assertTrue(live["runtime_loaded"])
        self.assertTrue(all("launch" not in argv for argv, _ in self.commands))
        self.assertTrue(all(timeout == 7 for _, timeout in self.commands))

    def test_legacy_probe_wrapper_retains_its_single_launch_and_mapping(self):
        live = shared.live_runtime(UDID, self.evidence, self.built, source_identity=SOURCE)
        self.assertEqual(live["pid"], 51457)
        self.assertEqual(sum("launch" in argv for argv, _ in self.commands), 1)
        self.assertEqual(live["requested_app_language"], "en")

    def test_wrong_mapped_pid_or_missing_entrypoint_is_rejected(self):
        original = self.mapping
        for value in (original.replace("[51457]", "[49959]"),
                      "\n".join(line for line in original.splitlines() if not line.endswith("/Anytype"))):
            self.mapping = value
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.mapped()

    def test_process_executable_or_start_identity_change_is_rejected(self):
        self.wrong_executable = True
        with self.assertRaisesRegex(RuntimeError, "executable identity"):
            self.mapped()
        self.wrong_executable = False; self.change_start = True; self.starts = 0
        with self.assertRaisesRegex(RuntimeError, "mapping is unverified"):
            self.mapped()

    def test_changed_main_or_missing_runtime_marker_is_rejected(self):
        (self.installed / "Anytype").write_bytes(b"changed executable")
        with self.assertRaisesRegex(RuntimeError, "differs from the fresh build"):
            self.mapped()
        (self.installed / "Anytype").write_bytes((self.built / "Anytype").read_bytes())
        for app in (self.built, self.installed):
            (app / "Frameworks/ProtobufMessages.framework/ProtobufMessages").write_bytes(b"not the approved runtime")
        with self.assertRaisesRegex(RuntimeError, "bytes/marker"):
            self.mapped()

    def test_actual_ui_boundaries_must_match_mapped_pid_not_original_probe(self):
        live = self.mapped(); self.hierarchies()
        self.assertEqual(self.continuity(live)["pid"], 51457)
        self.hierarchies(entry=49959)
        with self.assertRaisesRegex(RuntimeError, "differs from the mapped"):
            self.continuity(live)
        self.hierarchies(final=49959)
        with self.assertRaisesRegex(RuntimeError, "differs from the mapped"):
            self.continuity(live)

    def test_missing_hierarchy_or_changed_post_ui_code_carrier_cannot_qualify(self):
        live = self.mapped(); self.hierarchies()
        path = self.evidence / "wave15-hanlin-native-attachments/manifest.json"
        value = json.loads(path.read_text()); value[0]["attachments"].pop(); path.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "Exactly one"):
            self.continuity(live)
        self.hierarchies(); self.carriers["sha256"] = "e" * 64
        with self.assertRaisesRegex(RuntimeError, "code carriers changed"):
            self.continuity(live)


if __name__ == "__main__":
    unittest.main()
