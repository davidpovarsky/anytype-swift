"""SDK enumeration uses the existing bounded owned-process cleanup policy."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sdk06_enumeration_probe as sdk
import run_owned_single_lane as supervisor


class SDKEnumerationQuiescenceControls(unittest.TestCase):
    def worker(self, *, error=None):
        def run(argv, cwd, path, timeout):
            path.write_text("synthetic owned command output\n")
            record = dict(worker_pid=987654, return_code=-15 if error else 0,
                          timeout_seconds=timeout, owned_group_cleanup="TERM_THEN_KILL")
            if error:
                record["error_type"] = type(error).__name__
            sdk.save(path.with_suffix(".command.json"), record)
            if error:
                raise error
            return record
        return run

    def test_sdk_adapter_uses_remaining_ten_seconds_and_requires_observed_zero_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            clock, observations = [0.0], []
            def inventory(argv, *, text, timeout):
                observations.append(dict(argv=argv, timeout=timeout))
                if len(observations) == 1:
                    clock[0] = 2.0
                    return "987655 987654 S\n"
                clock[0] = 7.0
                return "1 1 Ss\n987655 987654 Z\n"
            with patch.object(sdk.owned, "run_worker_command", side_effect=self.worker()) as worker, \
                 patch.object(supervisor.time, "monotonic", side_effect=lambda: clock[0]), \
                 patch.object(supervisor.time, "sleep"), \
                 patch.object(supervisor.subprocess, "check_output", side_effect=inventory):
                _, record = sdk.Commands(root, root, {}).run(["synthetic"], "bootstatus", 180)
            self.assertEqual(worker.call_args.args[-1], 180)
            self.assertEqual([value["timeout"] for value in observations], [10.0, 8.0])
            self.assertTrue(all(value["argv"] == ["ps", "-axo", "pid=,pgid=,stat="]
                                for value in observations))
            proof = record["owned_group_quiescence"]
            self.assertEqual(proof["status"], "PASS")
            self.assertEqual(proof["live_members"], 0)
            self.assertEqual(proof["observations"], 2)
            self.assertEqual(proof["budget_seconds"], 10)
            self.assertEqual(proof["pgid"], record["worker_pid"])
            self.assertEqual(json.loads((root / "receipt.json").read_bytes())["commands"][0], record)

    def test_sdk_profile_preserves_deadline_and_refuses_live_timed_out_or_late_zero_probes(self):
        for scenario in ["live-at-deadline", "timeout-at-deadline", "zero-after-deadline"]:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                clock = [0.0]
                def inventory(argv, *, text, timeout):
                    clock[0] = 10.1 if scenario == "zero-after-deadline" else 10.0
                    if scenario == "timeout-at-deadline":
                        raise subprocess.TimeoutExpired(argv, timeout)
                    return "1 1 Ss\n" if scenario == "zero-after-deadline" else "987655 987654 S\n"
                with patch.object(sdk.owned, "run_worker_command", side_effect=self.worker()), \
                     patch.object(supervisor.time, "monotonic", side_effect=lambda: clock[0]), \
                     patch.object(supervisor.time, "sleep"), \
                     patch.object(supervisor.subprocess, "check_output", side_effect=inventory) as probe, \
                     self.assertRaises((RuntimeError, subprocess.TimeoutExpired)):
                    sdk.Commands(root, root, {}).run(["synthetic"], "bootstatus", 180)
                self.assertEqual(probe.call_count, 1)
                self.assertEqual(probe.call_args.kwargs["timeout"], 10.0)
                record = json.loads((root / "receipt.json").read_bytes())["commands"][0]
                self.assertNotIn("owned_group_quiescence", record)
                failure = record["quiescence_failure"]
                if scenario == "timeout-at-deadline":
                    self.assertEqual(failure["timeout_observations"],
                                     [dict(observation=1, timeout_seconds=10.0)])
                if scenario == "zero-after-deadline":
                    self.assertEqual(failure["quiescence_observation"]["status"], "FAIL_DEADLINE")
                    self.assertEqual(failure["quiescence_observation"]["live_members"], 0)
                    self.assertEqual(failure["quiescence_observation"]["budget_seconds"], 10)
                command = root / "bootstatus.command.json"
                with self.assertRaisesRegex(RuntimeError, "unchanged 10-second cleanup budget"):
                    supervisor.verify_owned_group_stopped(
                        command, cleanup_profile="sdk06-enumeration", seconds=11)

    def test_sdk_adapter_keeps_first_command_timeout_and_all_cleanup_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            primary = subprocess.TimeoutExpired(["xcrun", "simctl", "shutdown", "owned-id"], 30)
            cleanup = RuntimeError("late actual zero-member observation")
            cleanup.timeout_observations = [dict(observation=1, timeout_seconds=10)]
            cleanup.quiescence_observation = dict(
                status="FAIL_DEADLINE", live_members=0, observations=2, budget_seconds=10)
            with patch.object(sdk.owned, "run_worker_command", side_effect=self.worker(error=primary)) as worker, \
                 patch.object(supervisor, "verify_owned_group_stopped", side_effect=cleanup) as verify, \
                 self.assertRaises(subprocess.TimeoutExpired) as failed:
                sdk.Commands(root, root, {}).run(primary.cmd, "cleanup-owned-shutdown", 30)
            self.assertIs(failed.exception, primary)
            self.assertEqual(worker.call_args.args[-1], 30)
            self.assertEqual(verify.call_args.kwargs, {"cleanup_profile": "sdk06-enumeration"})
            record = json.loads((root / "receipt.json").read_bytes())["commands"][0]
            self.assertEqual(record["error_type"], "TimeoutExpired")
            self.assertEqual(record["return_code"], -15)
            self.assertNotIn("owned_group_quiescence", record)
            self.assertEqual(record["quiescence_failure"]["timeout_observations"],
                             cleanup.timeout_observations)
            self.assertEqual(record["quiescence_failure"]["quiescence_observation"],
                             cleanup.quiescence_observation)


if __name__ == "__main__":
    unittest.main()
