"""Focused controller controls; no Apple acceptance is claimed."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import run_owned_single_lane as lane


class OwnedCleanupTimeoutControls(unittest.TestCase):
    def receipt(self, root):
        path = Path(root) / "worker.command.json"
        path.write_text(json.dumps({"worker_pid": 987654, "owned_group_cleanup": "TERM_THEN_KILL"}))
        return path

    def test_transient_timeout_requires_actual_empty_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = self.receipt(directory)
            failure = subprocess.TimeoutExpired(["ps", "-axo", "pid=,pgid=,stat="], 2)
            with patch.object(lane.time, "monotonic", side_effect=[0, 0, 2, 2]), \
                 patch.object(lane.subprocess, "check_output", side_effect=[failure, "1 1 Ss\n"]) as probe:
                result = lane.verify_owned_group_stopped(receipt)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["live_members"], 0)
            self.assertEqual(result["observations"], 2)
            self.assertEqual(result["budget_seconds"], 10)
            self.assertEqual(result["timeout_observations"], [{"observation": 1, "timeout_seconds": 2}])
            self.assertEqual([call.kwargs["timeout"] for call in probe.call_args_list], [2, 2])

    def test_deadline_exhaustion_is_failure_with_timeout_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = self.receipt(directory)
            first = subprocess.TimeoutExpired(["ps"], 2)
            last = subprocess.TimeoutExpired(["ps"], 2)
            with patch.object(lane.time, "monotonic", side_effect=[0, 0, 2, 2, 10]), \
                 patch.object(lane.subprocess, "check_output", side_effect=[first, last]) as probe:
                with self.assertRaises(subprocess.TimeoutExpired) as failed:
                    lane.verify_owned_group_stopped(receipt)
            self.assertIs(failed.exception, last)
            self.assertEqual(len(failed.exception.timeout_observations), 2)
            self.assertEqual(probe.call_count, 2)
            self.assertEqual([call.kwargs["timeout"] for call in probe.call_args_list], [2, 2])

    def test_actual_live_descendant_after_timeout_still_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = self.receipt(directory)
            failure = subprocess.TimeoutExpired(["ps"], 2)
            with patch.object(lane.time, "monotonic", side_effect=[0, 0, 2, 2, 3, 10]), \
                 patch.object(lane.time, "sleep"), \
                 patch.object(lane.subprocess, "check_output", side_effect=[failure, "555 987654 S\n"]):
                with self.assertRaisesRegex(RuntimeError, "cleanup budget"):
                    lane.verify_owned_group_stopped(receipt)


if __name__ == "__main__":
    unittest.main()
