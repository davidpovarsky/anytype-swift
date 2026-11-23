"""New SDK-enumeration kernel absence controls; no Apple/product tests."""
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import run_owned_single_lane as groups

PGID = 92001
PROFILE = "sdk06-enumeration"


class SDKKernelQuiescenceControls(unittest.TestCase):
    def record(self, root, **changes):
        value = dict(worker_pid=PGID, owned_group_cleanup="TERM_THEN_KILL")
        value.update(changes)
        path = root / "original.command.json"; path.write_text(json.dumps(value))
        return path

    def test_timely_esrch_proves_actual_absence_without_ps(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            original = ProcessLookupError(errno.ESRCH, "synthetic exact group absent")
            with mock.patch.object(groups.time, "monotonic", side_effect=[0, 1, 2]), \
                 mock.patch.object(groups.os, "killpg", side_effect=original) as kernel, \
                 mock.patch.object(groups.subprocess, "check_output") as ps:
                result = groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            kernel.assert_called_once_with(PGID, 0); ps.assert_not_called()
            self.assertEqual((result["status"], result["live_members"], result["observations"]), ("PASS", 0, 0))
            self.assertEqual(result["absence_source"], "KERNEL_ESRCH")
            observation = result["kernel_group_observation"]
            self.assertEqual((observation["before_monotonic"], observation["after_monotonic"],
                              observation["deadline_monotonic"], observation["errno"]), (1, 2, 10, errno.ESRCH))

    def test_existing_group_falls_through_to_ps_with_original_remaining_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            with mock.patch.object(groups.time, "monotonic", side_effect=[0, 1, 2, 3, 4]), \
                 mock.patch.object(groups.os, "killpg", return_value=None) as kernel, \
                 mock.patch.object(groups.subprocess, "check_output", return_value="93001 93001 S\n") as ps:
                result = groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            kernel.assert_called_once_with(PGID, 0)
            self.assertEqual(ps.call_args.kwargs["timeout"], 7)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["observations"], 1)
            self.assertEqual(result["kernel_group_observation"]["outcome"], "GROUP_EXISTS")
            self.assertNotIn("absence_source", result)

    def test_permission_and_other_kernel_errors_preserve_original_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            for code in (errno.EPERM, errno.EINVAL, errno.EIO):
                original = OSError(code, "synthetic kernel error")
                with self.subTest(errno=code), mock.patch.object(groups.time, "monotonic", side_effect=[0, 1, 2]), \
                     mock.patch.object(groups.os, "killpg", side_effect=original), \
                     mock.patch.object(groups.subprocess, "check_output") as ps:
                    with self.assertRaises(OSError) as caught:
                        groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
                self.assertIs(caught.exception, original); ps.assert_not_called()
                observed = caught.exception.quiescence_observation
                self.assertEqual(observed["status"], "FAIL_KERNEL_QUERY")
                self.assertIsNone(observed["live_members"])
                self.assertEqual(observed["kernel_group_observation"]["errno"], code)

    def test_late_esrch_is_retained_but_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            with mock.patch.object(groups.time, "monotonic", side_effect=[0, 1, 11]), \
                 mock.patch.object(groups.os, "killpg", side_effect=ProcessLookupError(errno.ESRCH, "late absence")), \
                 mock.patch.object(groups.subprocess, "check_output") as ps:
                with self.assertRaises(RuntimeError) as caught:
                    groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            observed = caught.exception.quiescence_observation
            self.assertEqual(observed["status"], "FAIL_DEADLINE")
            self.assertEqual(observed["kernel_group_observation"]["outcome"], "ABSENT_ESRCH")
            self.assertEqual(observed["kernel_group_observation"]["errno"], errno.ESRCH)
            self.assertEqual(observed["kernel_group_observation"]["after_monotonic"], 11)
            ps.assert_not_called()

    def test_expired_before_query_and_late_existing_group_cannot_reset_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            for times, expected_calls in [([0, 11], 0), ([0, 1, 11], 1)]:
                with self.subTest(times=times), mock.patch.object(groups.time, "monotonic", side_effect=times), \
                     mock.patch.object(groups.os, "killpg", return_value=None) as kernel, \
                     mock.patch.object(groups.subprocess, "check_output") as ps:
                    with self.assertRaises(RuntimeError) as caught:
                        groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
                self.assertEqual(caught.exception.quiescence_observation["status"], "FAIL_DEADLINE")
                self.assertEqual(kernel.call_count, expected_calls); ps.assert_not_called()

    def test_original_owned_receipt_must_pass_before_any_kernel_query(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for changes in [dict(worker_pid=os.getpgrp()), dict(worker_pid=1),
                            dict(owned_group_cleanup="NOT_DONE"), dict(cleanup_error_type="OriginalFailure")]:
                path = self.record(root, **changes)
                with self.subTest(changes=changes), mock.patch.object(groups.os, "killpg") as kernel, \
                     mock.patch.object(groups.subprocess, "check_output") as ps:
                    with self.assertRaises(RuntimeError):
                        groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
                kernel.assert_not_called(); ps.assert_not_called()

    def test_other_existing_profiles_never_call_the_kernel_fast_path(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp))
            for profile, expected in [(None, 2), (groups.owned.COHERENT_HEART_PROFILE, 10), ("semantic-page154", 10)]:
                with self.subTest(profile=profile), mock.patch.object(groups.time, "monotonic", side_effect=[0, 0, 1]), \
                     mock.patch.object(groups.os, "killpg") as kernel, \
                     mock.patch.object(groups.subprocess, "check_output", return_value="") as ps:
                    result = groups.verify_owned_group_stopped(path, cleanup_profile=profile)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(ps.call_args.kwargs["timeout"], expected)
                self.assertNotIn("kernel_group_observation", result); kernel.assert_not_called()

    def test_existing_group_then_ps_timeout_preserves_both_original_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.record(Path(temp)); original = subprocess.TimeoutExpired(["ps"], 7)
            with mock.patch.object(groups.time, "monotonic", side_effect=[0, 1, 2, 3, 10]), \
                 mock.patch.object(groups.os, "killpg", return_value=None), \
                 mock.patch.object(groups.subprocess, "check_output", side_effect=original):
                with self.assertRaises(subprocess.TimeoutExpired) as caught:
                    groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
            self.assertIs(caught.exception, original)
            self.assertEqual(original.timeout_observations, [{"observation": 1, "timeout_seconds": 7}])
            self.assertEqual(original.quiescence_observation["status"], "FAIL_PS_AFTER_KERNEL_GROUP_EXISTS")
            self.assertEqual(original.quiescence_observation["kernel_group_observation"]["outcome"], "GROUP_EXISTS")

    def test_real_owned_process_exit_has_kernel_absence_and_original_receipt(self):
        directory = Path(os.environ["PINKHA_SDK_KERNEL_CONTROL_EVIDENCE"])
        directory.mkdir(parents=True, exist_ok=False)
        command = [sys.executable, "-B", "-c", "print('SDK06_OWNED_PROCESS_CONTROL', flush=True)"]
        outcome = groups.owned.run_worker_command(command, directory, directory / "owned-process.log", 10)
        self.assertEqual(outcome["return_code"], 0)
        path = directory / "owned-process.command.json"
        self.assertEqual(json.loads(path.read_text())["worker_pid"], outcome["worker_pid"])
        result = groups.verify_owned_group_stopped(path, cleanup_profile=PROFILE)
        groups.owned.write(directory / "actual-kernel-quiescence.json", result)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["absence_source"], "KERNEL_ESRCH")
        self.assertEqual(result["kernel_group_observation"]["pgid"], outcome["worker_pid"])
        self.assertEqual(result["kernel_group_observation"]["signal"], 0)
        self.assertEqual(result["kernel_group_observation"]["errno"], errno.ESRCH)
        self.assertLessEqual(result["kernel_group_observation"]["after_monotonic"],
                             result["kernel_group_observation"]["deadline_monotonic"])


if __name__ == "__main__":
    unittest.main()
