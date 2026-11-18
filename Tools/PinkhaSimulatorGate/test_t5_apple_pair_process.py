"""Real owned-process checks only; these do not represent Apple/native acceptance."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import run_t5_apple_pair as controller


@unittest.skipUnless(os.name == "posix", "Owned process groups require POSIX")
class ApplePairProcessControls(unittest.TestCase):
    def running(self, pid):
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                               capture_output=True, text=True, check=False).stdout.strip()
        return bool(state) and not state.startswith("Z")

    def exercise_interruption(self, mode):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # Both process groups belong to this test. The unrelated control
            # must survive cleanup of the separately launched command group.
            control = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                       start_new_session=True)
            parent_file, child_file = root / "parent.pid", root / "child.pid"
            child = (
                "import os,signal,sys,time; from pathlib import Path; "
                "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                "print('original child output',flush=True); "
                "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)"
            )
            script = root / "owned_tree.py"
            script.write_text(
                "import os,signal,subprocess,sys,time\nfrom pathlib import Path\n"
                "parent,child,mode=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]\n"
                "parent.write_text(str(os.getpid()))\n"
                "subprocess.Popen([sys.executable,'-u','-c'," + repr(child) + ",str(child)])\n"
                "deadline=time.monotonic()+5\n"
                "while not child.exists() and time.monotonic()<deadline: time.sleep(.01)\n"
                "assert child.exists(), 'child readiness missing'\n"
                "print('original parent output',flush=True)\n"
                "if mode=='interrupt': os.kill(os.getppid(),signal.SIGINT)\n"
                "time.sleep(30)\n", encoding="utf8")
            error = KeyboardInterrupt if mode == "interrupt" else subprocess.TimeoutExpired
            try:
                with self.assertRaises(error):
                    controller.run_logged(
                        [sys.executable, "-u", str(script), str(parent_file), str(child_file), mode],
                        root, root / "evidence", mode, 3)
                metadata = json.loads((root / "evidence" / (mode + ".command.json")).read_text())
                parent_pid, child_pid = int(parent_file.read_text()), int(child_file.read_text())
                self.assertEqual(metadata["controller_process_id"], parent_pid)
                self.assertNotEqual(os.getpgid(control.pid), parent_pid)
                self.assertEqual(metadata["status"], "CANCELLED" if mode == "interrupt" else "TIMED_OUT")
                self.assertEqual(metadata["error_type"], error.__name__)
                self.assertEqual(metadata["owned_group_termination"], "TERM_THEN_KILL")
                self.assertEqual(metadata["return_code"], -signal.SIGTERM)
                self.assertTrue(metadata["finished_at"])
                output = (root / "evidence" / (mode + ".log")).read_text()
                self.assertIn("original parent output", output)
                self.assertIn("original child output", output)
                deadline = time.monotonic() + 3
                while self.running(child_pid) and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertFalse(self.running(parent_pid))
                self.assertFalse(self.running(child_pid), "TERM-ignoring owned descendant survived")
                self.assertIsNone(control.poll(), "cleanup touched the unrelated process group")
            finally:
                if parent_file.exists():
                    try:
                        os.killpg(int(parent_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if control.poll() is None:
                    os.killpg(control.pid, signal.SIGKILL)
                control.wait(timeout=5)

    def test_keyboard_interrupt_preserves_log_and_stops_owned_descendants(self):
        self.exercise_interruption("interrupt")

    def test_timeout_kills_owned_descendants_after_parent_exits_on_term(self):
        self.exercise_interruption("timeout")

    def test_failed_process_start_preserves_failure_receipt_and_empty_log(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FileNotFoundError):
                controller.run_logged([str(root / "absent-command")], root, root, "start", 1)
            metadata = json.loads((root / "start.command.json").read_text())
            self.assertEqual(metadata["status"], "FAILED")
            self.assertEqual(metadata["error_type"], "FileNotFoundError")
            self.assertNotIn("controller_process_id", metadata)
            self.assertTrue(metadata["finished_at"])
            self.assertEqual((root / "start.log").read_bytes(), b"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
