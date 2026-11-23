"""Two new controls for starter diagnostics, with no product tests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import hanlin_fixture_start_observation as observation


class StarterObservationTests(unittest.TestCase):
    def dirs(self):
        temp = tempfile.TemporaryDirectory(prefix="pinkha-starter-observation-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        private, safe = root / "private", root / "safe"
        private.mkdir(mode=0o700)
        safe.mkdir()
        return private, safe

    def test_real_owned_starter_failure_preserves_finite_original_and_private_bytes(self):
        private, safe = self.dirs()
        raw = b'{"schema":1,"status":"FIXTURE_ERROR","code":"certificate_command_failed"}\n'
        secret = b"PRIVATE_SENTINEL_DO_NOT_PUBLISH\x00\xff"
        script = "import os,sys;os.write(1," + repr(raw) + ");os.write(2," + repr(secret) + ");sys.exit(7)"
        result = observation.observe_start([sys.executable, "-B", "-c", script],
            cwd=private, private_dir=private, safe_dir=safe)
        self.assertEqual(result["outcome"], "NONZERO_EXIT")
        self.assertEqual(result["returnCode"], 7)
        self.assertEqual((private / "starter.stdout").read_bytes(), raw)
        self.assertEqual((private / "starter.stderr").read_bytes(), secret)
        self.assertEqual((private / "starter.stderr").stat().st_mode & 0o777, 0o600)
        self.assertEqual((safe / "starter-fixed-error.original.json").read_bytes(), raw)
        self.assertFalse(result["providerReadinessAccepted"])
        self.assertFalse(result["ownedChildAbsenceProved"])
        for p in safe.iterdir():
            self.assertNotIn(b"PRIVATE_SENTINEL", p.read_bytes())
        print("ACTUAL_STARTER_DIAGNOSTIC exit=7 finite_original=preserved private_bytes=exact product_methods=0")

    def test_bounded_timeout_os_error_and_untrusted_output_never_create_readiness(self):
        cases = [
            ("timeout", subprocess.TimeoutExpired(["private"], 90, output=b"PRIVATE_PARTIAL", stderr=b"PRIVATE_ERROR"), "TIMED_OUT"),
            ("oserror", OSError(2, "PRIVATE_PATH"), "OS_ERROR"),
            ("unknown", subprocess.CompletedProcess([], 1, b'{"schema":1,"status":"FIXTURE_ERROR","code":"PRIVATE_SECRET"}', b""), "NONZERO_EXIT"),
            ("duplicate", subprocess.CompletedProcess([], 1, b'{"schema":1,"status":"FIXTURE_ERROR","code":"PRIVATE_SECRET","code":"certificate_command_failed"}', b""), "NONZERO_EXIT"),
            ("extra", subprocess.CompletedProcess([], 1, b'{"schema":1,"status":"FIXTURE_ERROR","code":"certificate_command_failed","key":"PRIVATE_SECRET"}', b""), "NONZERO_EXIT"),
            ("zero", subprocess.CompletedProcess([], 0, b"PRIVATE_READY_PAYLOAD", b""), "COMPLETED"),
        ]
        for name, outcome, expected in cases:
            with self.subTest(name=name):
                private, safe = self.dirs()
                call = mock.patch.object(observation.subprocess, "run",
                    side_effect=outcome if isinstance(outcome, BaseException) else None,
                    return_value=outcome)
                with call as run:
                    result = observation.observe_start(["owned-fixture-start"],
                        cwd=private, private_dir=private, safe_dir=safe)
                self.assertEqual(run.call_args.kwargs["timeout"], 90)
                self.assertEqual(result["outcome"], expected)
                self.assertFalse(result["providerReadinessAccepted"])
                self.assertFalse((safe / "starter-fixed-error.original.json").exists())
                safe_bytes = (safe / "starter-observation.json").read_bytes()
                for private_marker in [b"PRIVATE_PARTIAL", b"PRIVATE_ERROR", b"PRIVATE_PATH",
                                       b"PRIVATE_SECRET", b"PRIVATE_READY_PAYLOAD"]:
                    self.assertNotIn(private_marker, safe_bytes)
        private, safe = self.dirs()
        nested = safe / "must-not-upload-private"
        nested.mkdir(mode=0o700)
        with mock.patch.object(observation.subprocess, "run") as launched:
            with self.assertRaisesRegex(ValueError, "invalid owned diagnostic directories"):
                observation.observe_start(["owned-fixture-start"], cwd=private,
                    private_dir=nested, safe_dir=safe)
            launched.assert_not_called()
        self.assertEqual(list(nested.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
