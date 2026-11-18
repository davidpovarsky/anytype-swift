"""Real subprocess controls for the diagnostic controller; not Apple acceptance."""
import os
import subprocess
import sys
import time
import unittest

import run_journal_probe as probe


class CommandDeadlineTests(unittest.TestCase):
    def launch(self, seconds):
        return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(" + str(seconds) + ")"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def test_completed_command_retains_its_exit_status(self):
        process = self.launch(0)
        try:
            self.assertEqual(probe.wait_owned_command(process, 5, lambda elapsed: None), 0)
        finally:
            if process.poll() is None:
                probe.terminate_owned(process)

    def test_silent_command_emits_progress_before_completion(self):
        process = self.launch(0.15)
        observed = []
        try:
            result = probe.wait_owned_command(process, 5, observed.append, heartbeat_seconds=0.03)
            self.assertEqual(result, 0)
            self.assertGreaterEqual(len(observed), 1)
            self.assertEqual(observed, sorted(observed))
        finally:
            if process.poll() is None:
                probe.terminate_owned(process)

    @unittest.skipUnless(os.name == "posix", "Owned process-group cleanup requires POSIX")
    def test_progress_does_not_extend_deadline_and_own_process_is_reaped(self):
        process = self.launch(30)
        observed = []
        started = time.monotonic()
        try:
            with self.assertRaises(subprocess.TimeoutExpired) as raised:
                probe.wait_owned_command(process, 0.15, observed.append, heartbeat_seconds=0.03)
            self.assertEqual(raised.exception.timeout, 0.15)
            self.assertGreaterEqual(len(observed), 1)
            self.assertLess(time.monotonic() - started, 3)
        finally:
            probe.terminate_owned(process)
        self.assertIsNotNone(process.returncode)


if __name__ == "__main__":
    unittest.main()
