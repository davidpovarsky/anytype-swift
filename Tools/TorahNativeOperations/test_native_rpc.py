import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import run_native_rpc as runner


def _signal_harness(directory, phase):
    """Exercise real owned processes; only native preflight/generation is fake."""
    root = Path(directory)
    control, heart, evidence = [root / name for name in ["control", "heart", "evidence"]]
    for path in [control, heart, evidence]:
        path.mkdir()
    previous = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}
    original_write = runner.process_control.write_json
    final_signal_sent = False
    def write(path, value):
        nonlocal final_signal_sent
        original_write(path, value)
        if phase == "finalization" and value.get("finished_at") and not final_signal_sent:
            final_signal_sent = True
            os.kill(os.getpid(), signal.SIGTERM)
    def generate(args, receipt, run):
        run([sys.executable, "-c", "print('completed-command', flush=True)"], "completed", root, os.environ.copy())
        if phase == "command":
            leaf = "import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('leaf-ready', flush=True); time.sleep(60)"
            child = ("import json,os,subprocess,sys,time; child=subprocess.Popen([sys.executable,'-c'," + repr(leaf) + "]); "
                     "print(json.dumps({'parent':os.getpid(),'leaf':child.pid}), flush=True); time.sleep(60)")
            run([sys.executable, "-c", child], "blocked", root, os.environ.copy(), 30)
        receipt["status"] = "PASS_CONTROL_STAGE_ONLY"
    def git(root_path, *args):
        return ("1" * 40 if root_path == control else runner.HEART) if args == ("rev-parse", "HEAD") else ""
    with mock.patch.object(runner, "generate", generate), mock.patch.object(runner, "git", git), \
         mock.patch.object(runner.subprocess, "check_output", return_value=runner.VERSION), \
         mock.patch.object(runner.shutil, "disk_usage", return_value=type("Disk", (), {"free": 16 * 1024**3})()), \
         mock.patch.object(runner.process_control, "write_json", write):
        code = runner.main(["generate", "--control", str(control), "--heart-source", str(heart),
                            "--work", str(root / "work"), "--evidence", str(evidence), "--expected-app-sha", "1" * 40])
    print(json.dumps({"code": code, "handlers_restored": all(signal.getsignal(number) == value for number, value in previous.items())}), flush=True)
    return code


class NativeRPCControllerTests(unittest.TestCase):
    def successful_events(self):
        return ([{"Action": "pass", "Test": name, "Package": package} for name, package in runner.REQUIRED_PAIRS]
                + [{"Action": "pass", "Package": name} for name in runner.PACKAGES])

    def test_missing_required_generated_boundary_cannot_pass(self):
        events = self.successful_events()
        result = runner.validate_test_events(events, True)
        self.assertEqual(result["top_level_pass"], len(runner.REQUIRED))
        for name in runner.REQUIRED:
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.validate_test_events([event for event in events if event.get("Test") != name], True)

    def test_exit_failure_skip_and_package_failure_remain_failure(self):
        events = self.successful_events()
        for extra in [{"Action": "fail", "Package": "pkg"}, {"Action": "skip", "Test": "unexpected"}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                runner.validate_test_events(events + [extra], True)
        with self.assertRaises(ValueError):
            runner.validate_test_events(events, False)
        with self.assertRaises(ValueError):
            runner.validate_test_events([event for event in events if "Test" in event], True)
        with self.assertRaises(ValueError):
            runner.validate_test_events([{**event, "Package": "unrelated"} if "Test" in event else event for event in events], True)

    def test_schema_import_closure_hashes_exact_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            heart, include = root / "heart", root / "include"
            for parent in [heart / "pb/protos/service", include / "google/protobuf"]:
                parent.mkdir(parents=True)
            (heart / "pb/protos/commands.proto").write_text('import "google/protobuf/struct.proto";\n')
            (heart / "pb/protos/service/service.proto").write_text('import "pb/protos/commands.proto";\n')
            (include / "google/protobuf/struct.proto").write_text('syntax = "proto3";\n')
            before = runner.proto_closure(heart, include)
            self.assertEqual(set(before), {"pb/protos/commands.proto", "pb/protos/service/service.proto", "google/protobuf/struct.proto"})
            (include / "google/protobuf/struct.proto").write_text('syntax = "proto3";\n// changed\n')
            after = runner.proto_closure(heart, include)
            self.assertNotEqual(before["google/protobuf/struct.proto"], after["google/protobuf/struct.proto"])
            self.assertEqual(before["pb/protos/commands.proto"], after["pb/protos/commands.proto"])

    def test_inventory_and_proto_import_paths_cannot_escape(self):
        for value in ["../secret", "/absolute", "a/../secret", "C:/secret", "a\\secret", ""]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                runner.relative(value)

    @unittest.skipUnless(sys.platform == "linux", "Real Linux process-group control")
    def test_sigterm_cleans_owned_group_and_preserves_completed_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
            process = subprocess.Popen([sys.executable, "-c", "import sys,test_native_rpc as t; sys.exit(t._signal_harness(sys.argv[1],'command'))", str(root)],
                                       cwd=Path(__file__).parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            owned = None
            try:
                log = root / "evidence/blocked.log"
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    content = log.read_text() if log.exists() else ""
                    if "leaf-ready" in content:
                        owned = json.loads(next(line for line in content.splitlines() if line.startswith("{")))
                        break
                    self.assertIsNone(process.poll(), "Controller exited before real child readiness")
                    time.sleep(0.02)
                self.assertIsNotNone(owned, "Owned process group did not become ready")
                process.send_signal(signal.SIGTERM)
                output, error = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 1, error)
                self.assertTrue(json.loads(output)["handlers_restored"])
                receipt = json.loads((root / "evidence/generation-receipt.json").read_text())
                self.assertEqual(receipt["status"], "CANCELLED")
                self.assertTrue(receipt["finished_at"])
                self.assertEqual([entry["status"] for entry in receipt["commands"]], ["PASS_EXIT_0", "CANCELLED"])
                self.assertEqual((root / "evidence/completed.log").read_text().strip(), "completed-command")
                for pid in owned.values():
                    state = Path(f"/proc/{pid}/stat")
                    deadline = time.monotonic() + 3
                    while True:
                        try:
                            terminated = state.read_text().split(") ", 1)[1].startswith("Z")
                        except FileNotFoundError:
                            break
                        if terminated:
                            break
                        self.assertLess(time.monotonic(), deadline, "Owned descendant is still running")
                        time.sleep(0.01)
                self.assertIsNone(unrelated.poll(), "Cancellation touched an unrelated process")
            finally:
                if owned is not None:
                    try:
                        os.killpg(owned["parent"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5)
                unrelated.terminate()
                unrelated.wait(timeout=5)

    @unittest.skipUnless(sys.platform == "linux", "Real Linux signal during final receipt write")
    def test_sigterm_during_finalization_rewrites_cancelled_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-c", "import sys,test_native_rpc as t; sys.exit(t._signal_harness(sys.argv[1],'finalization'))", directory],
                                    cwd=Path(__file__).parent, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(json.loads(result.stdout)["handlers_restored"])
            receipt = json.loads((Path(directory) / "evidence/generation-receipt.json").read_text())
            self.assertEqual(receipt["status"], "CANCELLED")
            self.assertTrue(receipt["finished_at"])
            self.assertEqual([entry["status"] for entry in receipt["commands"]], ["PASS_EXIT_0"])


if __name__ == "__main__":
    unittest.main()
