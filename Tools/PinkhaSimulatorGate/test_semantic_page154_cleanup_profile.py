"""One new consumer profile control; ordinary and Release evidence is retained."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import run_owned_single_lane as supervisor


class SemanticPage154CleanupProfileControl(unittest.TestCase):
    def test_exact_consumer_profile_keeps_ten_second_deadline_and_default_two_second_probes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "owned.command.json"
            path.write_text(json.dumps(dict(worker_pid=987654, owned_group_cleanup="TERM_THEN_KILL")))
            for profile, expected in [(None, 2), ("coherent-heart-release", 7), ("semantic-page154", 7)]:
                with self.subTest(profile=profile), \
                     patch.object(supervisor.time, "monotonic", side_effect=[0, 3]), \
                     patch.object(supervisor.subprocess, "check_output", return_value="1 1 Ss\n") as probe:
                    actual = supervisor.verify_owned_group_stopped(path, cleanup_profile=profile)
                    self.assertEqual(probe.call_args.kwargs["timeout"], expected)
                    self.assertEqual(actual["budget_seconds"], 10)
                    self.assertEqual(actual["live_members"], 0)
            failure = subprocess.TimeoutExpired(["ps"], 10)
            with patch.object(supervisor.time, "monotonic", side_effect=[0, 0, 10]), \
                 patch.object(supervisor.subprocess, "check_output", side_effect=failure) as probe, \
                 self.assertRaises(subprocess.TimeoutExpired):
                supervisor.verify_owned_group_stopped(path, cleanup_profile="semantic-page154")
            self.assertEqual(probe.call_count, 1)
            self.assertEqual(failure.timeout_observations, [{"observation": 1, "timeout_seconds": 10}])
            for kwargs in [dict(cleanup_profile="semantic-page154", seconds=11),
                           dict(cleanup_profile="another-apple-consumer")]:
                with self.subTest(kwargs=kwargs), patch.object(supervisor.subprocess, "check_output") as probe, \
                     self.assertRaises(RuntimeError):
                    supervisor.verify_owned_group_stopped(path, **kwargs)
                probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
