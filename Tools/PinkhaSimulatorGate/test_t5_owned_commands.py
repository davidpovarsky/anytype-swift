"""Actual local process controls only; never App/native/simulator acceptance."""
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

import run_t5_apple_pair as pair


CHILD = "import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('READY '+str(os.getpid()),flush=True); time.sleep(120)"
PARENT = ("import subprocess,sys; child=subprocess.Popen([sys.executable,'-c'," + repr(CHILD)
          + "],stdout=subprocess.PIPE,text=True); print(child.stdout.readline().strip(),flush=True)")


@unittest.skipUnless(os.name == "posix", "Actual owned Unix process groups required")
class OwnedT5CommandControls(unittest.TestCase):
    def assert_owned_quiet(self, directory, name, status):
        record = json.loads((directory / (name + ".command.json")).read_bytes())
        self.assertEqual(record["status"], status)
        self.assertEqual(record["owned_group_termination"], "TERM_THEN_KILL")
        self.assertEqual(record["owned_group_quiescence"]["status"], "PASS")
        self.assertEqual(record["owned_group_quiescence"]["live_members"], 0)
        original = directory / record["original_owned_command"]
        self.assertEqual(pair.digest(original), record["original_owned_command_sha256"])
        self.assertEqual(json.loads(original.read_bytes())["worker_pid"], record["controller_process_id"])
        return record

    def test_normal_parent_exit_drains_actual_term_ignoring_descendant(self):
        handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
        previous_env = {name: os.environ.get(name) for name in ("GH_DEBUG", "GH_PROMPT_DISABLED")}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result, log = pair.run_logged([sys.executable, "-c", PARENT], directory, directory, "normal", 10)
            self.assertEqual(result["return_code"], 0)
            self.assertRegex(log.read_text(), r"^READY \d+\n$")
            self.assert_owned_quiet(directory, "normal", "SUCCESS")
        self.assertEqual({number: signal.getsignal(number) for number in handlers}, handlers)
        self.assertEqual({name: os.environ.get(name) for name in previous_env}, previous_env)

    def test_timeout_retains_original_exception_and_drains_its_actual_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                pair.run_logged([sys.executable, "-c", CHILD], directory, directory, "timeout", 0.2)
            self.assertEqual(caught.exception.timeout, 0.2)
            record = self.assert_owned_quiet(directory, "timeout", "TIMED_OUT")
            self.assertTrue(record["timed_out"])
            self.assertEqual(record["error_type"], "TimeoutExpired")

    def test_cancelled_controller_drains_nested_group_and_unrelated_process_survives(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            controller = ("import sys; from pathlib import Path; import run_t5_apple_pair as pair\n"
                "try:\n pair.run_logged([sys.executable,'-c'," + repr(CHILD) + "],Path(" + repr(temporary)
                + "),Path(" + repr(temporary) + "),'cancelled',30)\n"
                "except KeyboardInterrupt:\n sys.exit(77)\n")
            unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)
            process = None
            try:
                env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
                process = subprocess.Popen([sys.executable, "-c", controller], env=env, start_new_session=True,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                deadline = time.monotonic() + 10
                log = directory / "cancelled.log"
                while not log.exists() or "READY " not in log.read_text():
                    self.assertIsNone(process.poll(), "Owned controller exited before its child started")
                    self.assertLess(time.monotonic(), deadline, "Owned child did not become ready")
                    time.sleep(0.02)
                os.kill(process.pid, signal.SIGTERM)
                self.assertEqual(process.wait(timeout=15), 77)
                self.assert_owned_quiet(directory, "cancelled", "CANCELLED")
                self.assertIsNone(unrelated.poll(), "Cancellation signalled an unrelated process")
            finally:
                if process is not None:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                    process.stderr.close()
                unrelated.terminate()
                unrelated.wait(timeout=5)

    def test_outer_timeout_preserves_completed_inner_owned_cleanup(self):
        import wave15_batch as owned
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            controller = ("import sys; from pathlib import Path; import run_t5_apple_pair as pair\n"
                "try:\n pair.run_logged([sys.executable,'-c'," + repr(CHILD) + "],Path(" + repr(temporary)
                + "),Path(" + repr(temporary) + "),'inner',30)\n"
                "except KeyboardInterrupt:\n sys.exit(77)\n")
            old_path = os.environ.get("PYTHONPATH")
            os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    owned.run_nested_worker_command([sys.executable, "-c", controller], directory,
                        directory / "outer.log", 0.5, profile="coherent-heart-release")
                self.assert_owned_quiet(directory, "inner", "CANCELLED")
                outer = json.loads((directory / "outer.command.json").read_bytes())
                self.assertEqual(outer["timeout_seconds"], 0.5)
                self.assertEqual(outer["outer_term_grace_seconds"], 25)
                self.assertEqual(outer["owned_group_quiescence"]["status"], "PASS")
            finally:
                if old_path is None:
                    os.environ.pop("PYTHONPATH", None)
                else:
                    os.environ["PYTHONPATH"] = old_path
                # This is only the exact PID emitted by this test's created
                # native command, never a discovered/unrelated process.
                log = directory / "inner.log"
                if log.is_file() and log.read_text().startswith("READY "):
                    pid = int(log.read_text().split()[1])
                    try:
                        os.killpg(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_success_without_original_owned_receipt_is_rejected(self):
        import wave15_batch as owned
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(owned, "run_worker_command", return_value={"return_code": 0}), \
                 self.assertRaisesRegex(RuntimeError, "original owned-group receipt"):
                pair.run_logged(["controller-only-no-process"], directory, directory, "missing", 10)
            result = json.loads((directory / "missing.command.json").read_bytes())
            self.assertEqual(result["status"], "FAILED_PROCESS_CLEANUP")
            self.assertNotIn("owned_group_quiescence", result)


if __name__ == "__main__":
    unittest.main()
