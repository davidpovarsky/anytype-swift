"""One new SDK-qualified kernel-wiring control; no Apple/product execution."""
import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import run_owned_single_lane as groups


class QualifiedKernelProfileControls(unittest.TestCase):
    def test_sdk_qualified_kernel_wiring_preserves_identity_fallback_and_original_deadline(self):
        pgid = 92001
        cases = [
            dict(name="timely-absence", clock=[0, 1, 2],
                 kernel=ProcessLookupError(errno.ESRCH, "synthetic absent owned group"),
                 status="PASS", outcome="ABSENT_ESRCH", ps=False),
            dict(name="existing-group-fallback", clock=[0, 1, 2, 3, 4],
                 kernel=None, status="PASS", outcome="GROUP_EXISTS", ps=True),
            dict(name="permission-is-not-absence", clock=[0, 1, 2],
                 kernel=PermissionError(errno.EPERM, "synthetic permission denial"),
                 status="FAIL_KERNEL_QUERY", outcome="KERNEL_QUERY_ERROR", ps=False),
            dict(name="late-absence-is-not-success", clock=[0, 1, 11],
                 kernel=ProcessLookupError(errno.ESRCH, "synthetic late absent group"),
                 status="FAIL_DEADLINE", outcome="ABSENT_ESRCH", ps=False),
            dict(name="late-fallback-zero-is-not-success", clock=[0, 1, 2, 3, 11],
                 kernel=None, status="FAIL_DEADLINE", outcome="GROUP_EXISTS", ps=True),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "owned.command.json"
            path.write_text(json.dumps(dict(worker_pid=pgid, owned_group_cleanup="TERM_THEN_KILL")))
            for case in cases:
                with self.subTest(case=case["name"]), \
                     mock.patch.object(groups.time, "monotonic", side_effect=case["clock"]), \
                     mock.patch.object(groups.os, "killpg", side_effect=case["kernel"]) as kernel, \
                     mock.patch.object(groups.subprocess, "check_output", return_value="93001 93001 S\n") as query:
                    if case["status"] == "PASS":
                        result = groups.verify_owned_group_stopped(path, cleanup_profile="sdk06-qualified")
                        self.assertEqual(result["status"], "PASS")
                        self.assertEqual(result["budget_seconds"], 10)
                    else:
                        expected_type = PermissionError if case["status"] == "FAIL_KERNEL_QUERY" else RuntimeError
                        with self.assertRaises(expected_type) as caught:
                            groups.verify_owned_group_stopped(path, cleanup_profile="sdk06-qualified")
                        if case["status"] == "FAIL_KERNEL_QUERY":
                            self.assertIs(caught.exception, case["kernel"])
                        result = caught.exception.quiescence_observation
                        self.assertEqual(result["status"], case["status"])
                    observed = result["kernel_group_observation"]
                    self.assertEqual((observed["pgid"], observed["signal"], observed["deadline_monotonic"]),
                                     (pgid, 0, 10))
                    self.assertEqual(observed["before_monotonic"], 1)
                    self.assertEqual(observed["outcome"], case["outcome"])
                    self.assertEqual(observed["errno"], None if case["kernel"] is None else case["kernel"].errno)
                    kernel.assert_called_once_with(pgid, 0)
                    if case["ps"]:
                        query.assert_called_once_with(["ps", "-axo", "pid=,pgid=,stat="], text=True, timeout=7)
                        self.assertEqual(result["observations"], 1)
                        self.assertNotIn("absence_source", result)
                    else:
                        query.assert_not_called()
                    if case["name"] == "timely-absence":
                        self.assertEqual((result["absence_source"], result["live_members"], result["observations"]),
                                         ("KERNEL_ESRCH", 0, 0))
                    if case["status"] == "FAIL_DEADLINE":
                        self.assertGreater(case["clock"][-1], observed["deadline_monotonic"])


if __name__ == "__main__":
    unittest.main()
