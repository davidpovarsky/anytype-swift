"""New real-process integration controls for the single-lane supervisor."""
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

import run_owned_single_lane as supervisor


CONTEXT = dict(source_sha="a" * 40, run_id="123", run_attempt="1")
ROOT = Path(__file__).resolve().parent


def live(pid):
    result = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, timeout=3)
    return result.returncode == 0 and bool(result.stdout.strip()) and not result.stdout.strip().startswith("Z")


class OwnedSingleLaneTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="pinkha-owned-single-")
        self.root = Path(self.directory.name)
        self.unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)

    def tearDown(self):
        self.unrelated.terminate()
        self.unrelated.wait(timeout=5)
        self.directory.cleanup()

    def write_execution(self, status="FAIL", phase="BUILD"):
        raw = (json.dumps(dict(status=status, phase=phase, **CONTEXT)) + "\n").encode()
        (self.root / "execution.json").write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def worker(self, *, finish=False):
        path = self.root / "worker.py"
        path.write_text("import json, os, signal, subprocess, sys, time\n"
                        "from pathlib import Path\n"
                        "child = subprocess.Popen([sys.executable, '-c', "
                        "'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
                        "Path('owned-pids.json').write_text(json.dumps([os.getpid(), child.pid]))\n"
                        + ("time.sleep(0.2)\n" if finish else "time.sleep(60)\n"))
        return [sys.executable, str(path)]

    def assert_finished(self, expected_status, original_hash):
        data = json.loads((self.root / "single-lane-supervisor.json").read_bytes())
        self.assertEqual(data["status"], expected_status)
        self.assertEqual(hashlib.sha256((self.root / "execution.json").read_bytes()).hexdigest(), original_hash)
        self.assertEqual(data["original_evidence"]["execution.json"], original_hash)
        record = json.loads((self.root / "single-lane-worker.command.json").read_bytes())
        self.assertEqual(record["owned_group_cleanup"], "TERM_THEN_KILL")
        for pid in json.loads((self.root / "owned-pids.json").read_text()):
            for _ in range(50):
                if not live(pid):
                    break
                time.sleep(0.02)
            self.assertFalse(live(pid), "Owned descendant is still executing")
        self.assertIsNone(self.unrelated.poll(), "Unrelated process was signalled")
        checked = subprocess.run([sys.executable, str(ROOT / "run_owned_single_lane.py"),
                                  "--check-cache-ready", str(self.root)], capture_output=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr.decode())

    def test_success_reaps_owned_descendant_and_preserves_original_pass(self):
        digest = self.write_execution("LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "COMPLETE")
        result = supervisor.supervise(self.worker(finish=True), self.root, self.root,
                                      context=CONTEXT, cleanup=lambda: {"status": "PASS"}, timeout=5)
        self.assertEqual(result, 0)
        self.assert_finished(supervisor.PASS, digest)

    def test_zero_worker_exit_cannot_promote_original_failure(self):
        digest = self.write_execution()
        result = supervisor.supervise(self.worker(finish=True), self.root, self.root,
                                      context=CONTEXT, cleanup=lambda: {"status": "PASS"}, timeout=5)
        self.assertEqual(result, 1)
        self.assert_finished("FAIL", digest)

    def test_timeout_reaps_group_and_keeps_incomplete_receipt(self):
        digest = self.write_execution()
        result = supervisor.supervise(self.worker(), self.root, self.root,
                                      context=CONTEXT, cleanup=lambda: {"status": "PASS"}, timeout=0.8)
        self.assertEqual(result, 1)
        self.assert_finished("TIMED_OUT", digest)

    def test_sigterm_latches_cancellation_then_reaps_group(self):
        digest = self.write_execution()
        command = self.worker()
        launcher = self.root / "launch.py"
        launcher.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0, " + repr(str(ROOT)) + ")\n"
                            "import run_owned_single_lane as s\n"
                            "raise SystemExit(s.supervise(" + repr(command) + ", Path('.'), Path('.'), context="
                            + repr(CONTEXT) + ", cleanup=lambda: {'status': 'PASS'}, timeout=10))\n")
        with (self.root / "launcher.log").open("wb") as stream:
            process = subprocess.Popen([sys.executable, str(launcher)], cwd=self.root,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 5
                while not (self.root / "owned-pids.json").exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((self.root / "owned-pids.json").exists())
                os.kill(process.pid, signal.SIGTERM)
                self.assertEqual(process.wait(timeout=12), 1)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
        self.assert_finished("CANCELLED", digest)

    def test_cache_publication_rejects_missing_cleanup_evidence(self):
        (self.root / "single-lane-supervisor.json").write_text(json.dumps({"protocol": supervisor.PROTOCOL}))
        (self.root / "single-lane-worker.command.json").write_text("{}")
        result = subprocess.run([sys.executable, str(ROOT / "run_owned_single_lane.py"),
                                 "--check-cache-ready", str(self.root)], capture_output=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(self.unrelated.poll())


if __name__ == "__main__":
    unittest.main()
