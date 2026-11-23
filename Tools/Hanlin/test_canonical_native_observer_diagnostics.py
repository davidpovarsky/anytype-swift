"""One new diagnostic regression against the original runtime observer.

Original fixture helpers are reused without executing their test methods.
Injected OS command failures are deterministic controller controls, not Apple
or UI acceptance and not a replacement for the missing native runtime proof.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import test_hanlin_ui_runtime as original

gate = original.gate


class CanonicalObserverDiagnosticTests(unittest.TestCase):
    def run_case(self, name, command):
        fixture = original.ObserverControls()
        fixture.setUp()
        try:
            observer = fixture.observer
            error = subprocess.TimeoutExpired(command, 8.5,
                output=b"private mapping stdout", stderr=b"private mapping stderr")

            def fail_mapping():
                raise error

            fixture.map_hook = fail_mapping
            calls, deadlines = fixture.poll_timeout_case()
            rejected = False
            try:
                fixture.qualify(fixture.final())
            except RuntimeError:
                rejected = True
            summary = observer.summary()
            result = {
                "schema": "pinkha-observer-stage-failure-control-v1",
                "scope": "DETERMINISTIC_OBSERVER_CONTROL_NOT_APPLE_ACCEPTANCE",
                "case": name,
                "observerSHA256": hashlib.sha256((ROOT / "Tools/PinkhaSimulatorGate/hanlin_ui_runtime.py").read_bytes()).hexdigest(),
                "fixtureSHA256": hashlib.sha256((ROOT / "Tools/PinkhaSimulatorGate/test_hanlin_ui_runtime.py").read_bytes()).hexdigest(),
                "controlSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "errorType": type(observer.error).__name__,
                "sameTerminalError": observer.error is error,
                "mappedPIDs": fixture.mapped_pids,
                "sourceVerifications": fixture.source_calls,
                "commands": calls,
                "deadlines": deadlines,
                "finalDeadline": observer.deadline,
                "continuityCalls": fixture.continuity_calls,
                "qualificationRejected": rejected,
                "qualificationFileExists": (observer.directory / "qualification.json").exists(),
                "observation": summary,
                "oldControllerMethodsExecuted": 0,
                "nativeTestsExecuted": 0,
            }
            directory = os.environ.get("HANLIN_OBSERVER_DIAGNOSTIC_EVIDENCE")
            if directory:
                destination = Path(directory); destination.mkdir(parents=True, exist_ok=True)
                (destination / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")
            return result
        finally:
            fixture.doCleanups()

    def test_recovered_poll_preserves_the_later_terminal_mapping_failure(self):
        cases = [
            ("vmmap", ["/usr/bin/vmmap", "-w", "51457"]),
            ("process-identity", ["ps", "-ww", "-p", "51457", "-o", "lstart=", "-o", "comm="]),
        ]
        for name, command in cases:
            with self.subTest(case=name):
                result = self.run_case(name, command)
                diagnostics = result["observation"]["diagnostics"]
                stages = {item["stage"]: item for item in diagnostics["stages"]}
                first = diagnostics["first_failure"]
                self.assertEqual(first["stage"], "poll_data_container")
                self.assertEqual(first["command"], result["commands"][1])
                self.assertEqual(first["command_timeout_seconds"], 10)
                self.assertEqual(diagnostics["poll_timeout_retries"], 1)
                self.assertEqual(stages["poll_data_container"]["status"], "RETURNED")
                self.assertEqual(stages["poll_data_container"]["attempts"], 2)
                self.assertEqual(stages["map_running_process"]["status"], "FAILED")
                self.assertEqual(stages["map_running_process"]["attempts"], 1)
                self.assertTrue(result["sameTerminalError"])
                self.assertEqual(result["errorType"], "TimeoutExpired")
                self.assertEqual(result["mappedPIDs"], [51457])
                self.assertEqual(result["sourceVerifications"], 2)
                self.assertEqual(len(result["commands"]), 3)
                self.assertEqual(len(set(result["deadlines"])), 1)
                self.assertLessEqual(result["finalDeadline"], result["deadlines"][0])
                self.assertEqual(result["continuityCalls"], [])
                self.assertTrue(result["qualificationRejected"])
                self.assertFalse(result["qualificationFileExists"])
                self.assertEqual(result["observation"]["extra_app_launches"], 0)
                self.assertEqual(result["observation"]["status"], "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND")
                self.assertTrue(all("launch" not in argv and "terminate" not in argv
                                    for argv in result["commands"]))
                serialized = json.dumps(diagnostics)
                self.assertNotIn("private mapping", serialized)
                self.assertNotIn("private stdout", serialized)
                self.assertNotIn("private stderr", serialized)
                last = stages["map_running_process"].get("last_failure")
                self.assertIsNotNone(last, "Recovered polling must not hide the later fatal command")
                self.assertEqual(last["stage"], "map_running_process")
                self.assertEqual(last["command"], command)
                self.assertEqual(last["command_timeout_seconds"], 8.5)
                self.assertEqual(last["attempt"], 1)
                self.assertEqual(last["stage_elapsed_seconds"],
                                 stages["map_running_process"]["stage_elapsed_seconds"])
                recovered = stages["poll_data_container"]["last_failure"]
                self.assertEqual(recovered["attempt"], 1)
                self.assertEqual(recovered["stage"], first["stage"])
                self.assertEqual(recovered["command"], first["command"])
                self.assertEqual(recovered["stage_elapsed_seconds"], first["stage_elapsed_seconds"])


if __name__ == "__main__":
    unittest.main()
