"""Late successful observations never extend explicit Apple cleanup deadlines."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_owned_single_lane as supervisor
import wave15_batch as batch
import test_wave15_batch as fixtures


class LateCleanupDeadlineControls(unittest.TestCase):
    def test_late_zero_members_fail_only_explicit_profiles_and_preserve_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "owned.command.json"
            path.write_text(json.dumps(dict(worker_pid=987654, owned_group_cleanup="TERM_THEN_KILL")))
            for profile in ["coherent-heart-release", "semantic-page154"]:
                with self.subTest(profile=profile), \
                     patch.object(supervisor.time, "monotonic", side_effect=[0, 0, 11]), \
                     patch.object(supervisor.subprocess, "check_output", return_value="1 1 Ss\n"), \
                     self.assertRaisesRegex(RuntimeError, "after its original cleanup deadline") as failed:
                    supervisor.verify_owned_group_stopped(path, cleanup_profile=profile)
                observation = failed.exception.quiescence_observation
                self.assertEqual(observation["status"], "FAIL_DEADLINE")
                self.assertEqual(observation["live_members"], 0)
                self.assertEqual(observation["observations"], 1)
                self.assertEqual(observation["budget_seconds"], 10)
            with patch.object(supervisor.time, "monotonic", side_effect=[0, 0]), \
                 patch.object(supervisor.subprocess, "check_output", return_value="1 1 Ss\n") as probe:
                actual = supervisor.verify_owned_group_stopped(path)
                self.assertEqual(actual["status"], "PASS")
                self.assertEqual(probe.call_args.kwargs["timeout"], 2)

    def test_coherent_late_empty_inventory_or_final_delete_cannot_report_cleanup_pass(self):
        for phase in ["empty-inventory", "delete"]:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                clock = [0]
                def inventory(*args, **kwargs):
                    if phase == "empty-inventory":
                        clock[0] = 181
                        return fixtures.inventory([])
                    return fixtures.inventory([fixtures.DEVICE])
                def deletion(argv, **kwargs):
                    clock[0] = 181
                    return subprocess.CompletedProcess(argv, 0)
                intent = dict(profile=batch.COHERENT_HEART_PROFILE, preflight_devices=[fixtures.DEVICE],
                              lane_devices=[], baseline_udids=[])
                root = Path(temporary)
                with patch.object(batch.time, "monotonic", side_effect=lambda: clock[0]), \
                     patch.object(batch, "scoped_device_inventory", side_effect=inventory), \
                     patch.object(batch.subprocess, "run", side_effect=deletion), \
                     self.assertRaisesRegex(RuntimeError, "original 180-second deadline"):
                    batch.cleanup_owned(intent, root)
                report = json.loads((root / "batch-cleanup.json").read_bytes())
                self.assertEqual(report["status"], "FAIL")
                expected = "NOT_PRESENT" if phase == "empty-inventory" else "DELETED_OWNED_SIMULATOR"
                self.assertEqual(report["devices"][0]["status"], expected)
                if phase == "delete": self.assertEqual(report["devices"][0]["delete_exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
