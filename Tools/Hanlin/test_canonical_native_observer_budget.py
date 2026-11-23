"""New deadline controls using the real observer and retained fixture helpers.

No original controller method or Apple/native test is executed. A controllable
monotonic clock injects durations captured in the authenticated original run.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import test_hanlin_ui_runtime as original

gate = original.gate
SOURCE_SECONDS = 28.080363166999632
MAPPING_SECONDS = 16.649736624999605
FINAL_CONTAINER_SECONDS = 0.5598687080000673


class Clock:
    def __init__(self):
        self.value = 1000.0

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class CanonicalObserverBudgetTests(unittest.TestCase):
    def run_case(self, name, *, source_seconds=SOURCE_SECONDS,
                 elapsed_before_receipt=0.0, cancel=False, replace_pid=False):
        # Reuse only the original fixture helpers, never its test_ methods.
        fixture = original.ObserverControls()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        observer = fixture.observer
        clock = Clock()
        commands = []
        original_observe = observer.observe

        def observe_after_elapsed_time():
            clock.advance(elapsed_before_receipt)
            original_observe()

        observer.observe = observe_after_elapsed_time
        fixture.source_hook = lambda: clock.advance(source_seconds)

        def mapping_elapsed():
            clock.advance(MAPPING_SECONDS)
            if cancel:
                observer.stop_event.set()

        fixture.map_hook = mapping_elapsed

        def query(argv, **kwargs):
            self.assertEqual(argv, ["xcrun", "simctl", "get_app_container", original.UDID, "io.anytype.app", "data"])
            limit = kwargs["timeout"]
            self.assertGreater(limit, 0)
            self.assertLessEqual(limit, gate.COMMAND_SECONDS)
            closing = observer.diagnostic_stages.get("after_mapping_data_container", {}).get("status") == "STARTED"
            commands.append({"closing": closing, "timeout": limit, "deadline": observer.deadline,
                             "uptime": clock.now(), "argv": argv})
            if closing:
                if FINAL_CONTAINER_SECONDS > limit:
                    clock.advance(limit)
                    raise subprocess.TimeoutExpired(argv, limit)
                clock.advance(FINAL_CONTAINER_SECONDS)
                if replace_pid:
                    changed = dict(fixture.value, processID=fixture.value["processID"] + 1)
                    original.atomic_write(fixture.support / gate.RESULT, changed)
            return str(fixture.container) + "\n"

        with patch.object(gate.time, "monotonic", side_effect=clock.now), \
                patch.object(gate.subprocess, "check_output", side_effect=query):
            fixture.observe()
            qualification = None
            rejected = False
            try:
                final = fixture.final()
                qualification = fixture.qualify(final)["status"]
            except RuntimeError:
                rejected = True
            summary = observer.summary()
            result = {
                "scope": "DETERMINISTIC_OBSERVER_CONTROL_NOT_APPLE_ACCEPTANCE",
                "case": name,
                "observerSHA256": hashlib.sha256((ROOT / "Tools/PinkhaSimulatorGate/hanlin_ui_runtime.py").read_bytes()).hexdigest(),
                "controlSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "capturedSourceSeconds": source_seconds,
                "capturedMappingSeconds": MAPPING_SECONDS,
                "capturedFinalContainerSeconds": FINAL_CONTAINER_SECONDS,
                "elapsedBeforeReceipt": elapsed_before_receipt,
                "actualDeadline": observer.deadline,
                "endingUptime": clock.now(),
                "error": None if observer.error is None else type(observer.error).__name__,
                "errorMessage": None if observer.error is None else str(observer.error),
                "sourceVerifications": fixture.source_calls,
                "mappedPIDs": fixture.mapped_pids,
                "commands": commands,
                "qualificationStatus": qualification,
                "qualificationRejected": rejected,
                "observation": summary,
                "oldControllerMethodsExecuted": 0,
                "nativeTestsExecuted": 0,
            }
        directory = os.environ.get("HANLIN_OBSERVER_BUDGET_EVIDENCE")
        if directory:
            destination = Path(directory); destination.mkdir(parents=True, exist_ok=True)
            (destination / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        return result

    def test_captured_operations_reach_final_binding_with_fresh_source_checks(self):
        result = self.run_case("captured-durations")
        self.assertIsNone(result["error"], result)
        self.assertEqual(result["sourceVerifications"], 2)
        self.assertEqual(result["mappedPIDs"], [51457])
        self.assertEqual(result["qualificationStatus"], "PASS_ACTUAL_UI_PROCESS_RUNTIME")
        self.assertEqual(len([command for command in result["commands"] if command["closing"]]), 1)
        self.assertTrue(all("launch" not in command["argv"] and "terminate" not in command["argv"]
                            for command in result["commands"]))

    def test_expiry_cancellation_and_late_process_change_still_reject_binding(self):
        cases = [
            ("mapping-window-exhausted", {"source_seconds": 43.0}),
            ("original-global-window-exhausted", {"elapsed_before_receipt": 375.2}),
            ("cancelled-during-mapping", {"cancel": True}),
            ("late-process-replacement", {"replace_pid": True}),
        ]
        for name, arguments in cases:
            with self.subTest(case=name):
                result = self.run_case(name, **arguments)
                self.assertIsNotNone(result["error"], result)
                self.assertTrue(result["qualificationRejected"], result)
                self.assertIsNone(result["qualificationStatus"])
                self.assertNotEqual(result["observation"]["status"], "PASS_ACTUAL_UI_PROCESS_RUNTIME")
                self.assertLessEqual(result["actualDeadline"], 1000.0 + gate.OBSERVATION_SECONDS)
                if name == "late-process-replacement":
                    self.assertIn("changed process/session", result["errorMessage"])
                if name == "cancelled-during-mapping":
                    self.assertIn("cancelled", result["errorMessage"])


if __name__ == "__main__":
    unittest.main()
