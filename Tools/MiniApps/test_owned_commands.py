"""Actual process-boundary controls; no compiler or application acceptance credit."""
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from owned_commands import run_logged


class OwnedCommands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="miniapps-owned-command-control-")
        self.root = Path(self.temp.name)
        self.log = self.root / "command.log"

    def tearDown(self):
        self.temp.cleanup()

    def receipt(self):
        return json.loads(self.log.with_suffix(".command.json").read_bytes())

    def test_actual_success_has_own_drained_process_group(self):
        result = run_logged([sys.executable, "-B", "-c", "print('actual control')"],
                            self.root, self.log, 5)
        self.assertEqual(result.returncode, 0)
        proof = self.receipt()
        self.assertTrue(proof["owned_group_drained"])
        self.assertNotEqual(proof["process_group_id"], os.getpgrp())
        self.assertEqual(self.log.read_text(), "actual control\n")

    def test_actual_failure_retains_exit_code(self):
        result = run_logged([sys.executable, "-B", "-c", "raise SystemExit(7)"],
                            self.root, self.log, 5)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.receipt()["returncode"], 7)
        self.assertTrue(self.receipt()["owned_group_drained"])

    def test_actual_timeout_drains_only_its_owned_process(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_logged([sys.executable, "-B", "-c", "import time; time.sleep(20)"],
                       self.root, self.log, 0.2)
        self.assertTrue(self.receipt()["timed_out"])
        self.assertTrue(self.receipt()["owned_group_drained"])
        self.assertNotEqual(self.receipt()["process_group_id"], os.getpgrp())

    def test_permission_denied_after_actual_success_retains_failed_receipt(self):
        with patch("owned_commands.group_exists", side_effect=PermissionError(errno.EPERM, "Operation not permitted")), \
             patch("owned_commands.os.killpg") as signal_group:
            with self.assertRaisesRegex(RuntimeError, "did not drain"):
                run_logged([sys.executable, "-B", "-c", "print('original complete')"],
                           self.root, self.log, 5)
        proof = self.receipt()
        self.assertEqual(proof["returncode"], 0)
        self.assertFalse(proof["owned_group_drained"])
        self.assertEqual(proof["drain_error"]["errno"], errno.EPERM)
        self.assertEqual(proof["drain_error"]["type"], "PermissionError")
        self.assertEqual(self.log.read_text(), "original complete\n")
        self.assertIn("log_sha256", proof)
        signal_group.assert_not_called()

    def test_permission_denied_preserves_actual_primary_nonzero_exit(self):
        with patch("owned_commands.group_exists", side_effect=PermissionError(errno.EPERM, "Operation not permitted")):
            with self.assertRaisesRegex(RuntimeError, "did not drain"):
                run_logged([sys.executable, "-B", "-c", "raise SystemExit(7)"],
                           self.root, self.log, 5)
        proof = self.receipt()
        self.assertEqual(proof["returncode"], 7)
        self.assertFalse(proof["owned_group_drained"])
        self.assertFalse(proof["timed_out"])
        self.assertEqual(proof["drain_error"]["errno"], errno.EPERM)

    def test_existing_raw_log_is_never_overwritten(self):
        self.log.write_text("preserved")
        with self.assertRaises(ValueError):
            run_logged([sys.executable, "-B", "-c", "print('replacement')"],
                       self.root, self.log, 5)
        self.assertEqual(self.log.read_text(), "preserved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
