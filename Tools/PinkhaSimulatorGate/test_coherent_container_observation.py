"""One new focused lookup observation control; no simulator/product methods."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import coherent_container_observation as observed


class CoherentLookupObservationTests(unittest.TestCase):
    def test_original_results_and_failures_remain_exact_with_unchanged_thirty_second_query(self):
        argv = ["xcrun", "simctl", "get_app_container",
            "11111111-1111-4111-8111-111111111111", "io.anytype.app", "data"]
        cases = [
            (subprocess.CompletedProcess(argv, 1, b"", b"unclassified native error"), "RETURNED", b"", b"unclassified native error"),
            (subprocess.CompletedProcess(argv, 0, b"/unexpected/container", b""), "RETURNED", b"/unexpected/container", b""),
            (subprocess.TimeoutExpired(argv, 30, output=b"partial-out", stderr=b"partial-err"), "TIMED_OUT", b"partial-out", b"partial-err"),
            (OSError(2, "missing executable"), "OS_ERROR", b"", b""),
            (KeyboardInterrupt("owned cancellation"), "INTERRUPTED", b"", b""),
        ]
        for outcome, status, stdout, stderr in cases:
            with self.subTest(status=status), tempfile.TemporaryDirectory(prefix="pinkha-container-observation-") as directory:
                root = Path(directory)
                with mock.patch.object(observed.subprocess, "run",
                    side_effect=outcome if isinstance(outcome, BaseException) else None,
                    return_value=outcome) as run:
                    if isinstance(outcome, BaseException):
                        try:
                            observed.run_lookup(argv, root)
                        except BaseException as error:
                            self.assertIs(error, outcome)
                        else:
                            self.fail("original lookup failure was swallowed")
                    else:
                        self.assertIs(observed.run_lookup(argv, root), outcome)
                    run.assert_called_once_with(argv, capture_output=True, timeout=30)
                record = json.loads((root / "fresh-container-lookup.observation.json").read_bytes())
                self.assertEqual(record["status"], status)
                self.assertEqual((root / "fresh-container-lookup.stdout").read_bytes(), stdout)
                self.assertEqual((root / "fresh-container-lookup.stderr").read_bytes(), stderr)
                self.assertFalse(record["container_absence_proved"])
                self.assertFalse(record["owned_group_absence_proved"])
                self.assertEqual(record["product_methods_executed"], 0)
