"""New integration controls for the package wrapper's existing POSIX owner."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import run_packages as subject


class RelatedReadCommandOwnershipControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="pinkha-related-process-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                          start_new_session=True)
        self.addCleanup(self.stop_unrelated)

    def stop_unrelated(self):
        self.unrelated.terminate()
        self.unrelated.wait(timeout=5)

    def worker(self, *, finish=True, code=0):
        path = self.root / "worker.py"
        path.write_text("import json, os, subprocess, sys, time\nfrom pathlib import Path\n"
            "child = subprocess.Popen([sys.executable, '-c', "
            "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
            "Path('owned-pids.json').write_text(json.dumps([os.getpid(),child.pid]))\n"
            "Path('original-events.jsonl').write_bytes(b'original event evidence\\n')\n"
            "print('original command output', flush=True)\n"
            + ("time.sleep(0.15)\nraise SystemExit(" + str(code) + ")\n" if finish else "time.sleep(60)\n"))
        return [sys.executable, str(path)]

    def assert_finished(self, status):
        receipt = json.loads((self.root / "command.ownership.json").read_bytes())
        command = json.loads((self.root / "command.command.json").read_bytes())
        self.assertEqual(receipt["status"], status)
        self.assertIs(receipt["testAcceptanceInferred"], False)
        self.assertEqual(receipt["originalCommandSHA256"], subject.digest(self.root / "command.command.json"))
        self.assertEqual(receipt["logSHA256"], subject.digest(self.root / "command.log"))
        self.assertEqual(command["owned_group_cleanup"], "TERM_THEN_KILL")
        self.assertEqual(receipt["ownedGroupQuiescence"]["status"], "PASS")
        self.assertEqual(receipt["ownedGroupQuiescence"]["pgid"], command["worker_pid"])
        self.assertEqual(receipt["ownedGroupQuiescence"]["live_members"], 0)
        self.assertEqual((self.root / "original-events.jsonl").read_bytes(), b"original event evidence\n")
        self.assertIn(b"original command output", (self.root / "command.log").read_bytes())
        for pid in json.loads((self.root / "owned-pids.json").read_bytes()):
            actual = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                                    capture_output=True, text=True, timeout=2)
            self.assertTrue(actual.returncode != 0 or not actual.stdout.strip()
                            or actual.stdout.strip().startswith("Z"), "Owned worker or child remains live")
        self.assertIsNone(self.unrelated.poll(), "Unrelated process was signalled")
        return receipt

    def test_success_waits_for_owned_children_and_preserves_original_events(self):
        receipt = subject.run_command(self.root, self.worker(), self.root / "command.log", 5)
        self.assertEqual(receipt["returncode"], 0)
        self.assert_finished("PROCESS_COMPLETE_TEST_ACCEPTANCE_PENDING")

    def test_timeout_retires_owned_group_and_cannot_return_a_result(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            subject.run_command(self.root, self.worker(finish=False), self.root / "command.log", 0.8)
        self.assert_finished("TIMED_OUT")

    def test_nonzero_exit_is_preserved_after_owned_cleanup(self):
        receipt = subject.run_command(self.root, self.worker(code=7), self.root / "command.log", 5)
        self.assertEqual(receipt["returncode"], 7)
        self.assert_finished("PROCESS_FAILED")

    def test_sigterm_cancels_before_next_profile_and_preserves_receipts(self):
        argv = self.worker(finish=False)
        launcher = self.root / "launcher.py"
        launcher.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0, "
                            + repr(str(Path(subject.__file__).resolve().parent)) + ")\nimport run_packages as s\n"
                            + "s.run_command(Path('.'), " + repr(argv) + ", Path('command.log'), 10)\n"
                            + "Path('next-profile-started').write_text('wrong')\n")
        with (self.root / "launcher.log").open("wb") as stream:
            process = subprocess.Popen([sys.executable, str(launcher)], cwd=self.root,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 5
                while not (self.root / "owned-pids.json").exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((self.root / "owned-pids.json").exists())
                os.kill(process.pid, signal.SIGTERM)
                self.assertNotEqual(process.wait(timeout=12), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
        self.assertFalse((self.root / "next-profile-started").exists())
        self.assert_finished("CANCELLED")

    def test_cleanup_verification_failure_cannot_return_zero_exit(self):
        gate = Path(subject.__file__).resolve().parents[1] / "PinkhaSimulatorGate"
        sys.path.insert(0, str(gate))
        import run_owned_single_lane as owner
        with patch.object(owner, "verify_owned_group_stopped", side_effect=ValueError("unproved quiescence")):
            with self.assertRaisesRegex(ValueError, "unproved quiescence"):
                subject.run_command(self.root, self.worker(), self.root / "command.log", 5)
        receipt = json.loads((self.root / "command.ownership.json").read_bytes())
        self.assertEqual(receipt["status"], "FAILED_PROCESS_CLEANUP")
        self.assertIs(receipt["testAcceptanceInferred"], False)
        self.assertEqual(owner.verify_owned_group_stopped(self.root / "command.command.json")["status"], "PASS")
        self.assertIsNone(self.unrelated.poll())


if __name__ == "__main__":
    unittest.main()
