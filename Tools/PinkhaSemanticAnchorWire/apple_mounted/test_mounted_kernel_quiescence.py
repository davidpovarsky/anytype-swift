"""One new caller-composition control; no Apple, product or earlier control execution."""
from __future__ import annotations

import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
SPEC = importlib.util.spec_from_file_location("page154_mounted_kernel_control_subject", HERE / "run.py")
mounted = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mounted
SPEC.loader.exec_module(mounted)
consumer = mounted.consumer
supervisor = consumer.supervisor
owned = consumer.owned
KERNEL = supervisor._sdk06_kernel_group_observation
PROFILE = "semantic-page154"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def loaded_sources():
    declaration = read(ROOT / "docs/validation/20261123-semantic-mounted-kernel/control-inputs.json")
    expected = declaration["files"]
    found = {}
    for alias, module in list(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if path.is_relative_to(ROOT):
            name = path.relative_to(ROOT).as_posix()
            if name not in expected or sha(path) != expected[name]["sha256"]:
                raise RuntimeError("Unbound or changed actual repository import: " + name)
            item = found.setdefault(name, {"sha256": sha(path), "aliases": []})
            item["aliases"].append(alias)
        elif str(path).startswith("/mnt/development/projects/worktrees/"):
            raise RuntimeError("Foreign repository import: " + str(path))
    for row in found.values():
        row["aliases"].sort()
    return found


class MountedPageKernelCompositionTests(unittest.TestCase):
    def test_actual_mounted_consumer_keeps_owned_kernel_deadline_and_first_error(self):
        raw_directory = os.environ["PINKHA_PAGE_KERNEL_CONTROL_ORIGINALS"]
        directory = Path(raw_directory)
        self.assertEqual(directory, directory.resolve())
        self.assertTrue(directory.is_dir())
        self.assertFalse(any(directory.iterdir()))
        self.assertEqual(mounted.ROOT, ROOT)
        self.assertEqual(consumer.ROOT, ROOT)
        self.assertEqual(Path(mounted.__file__).resolve(), HERE / "run.py")
        self.assertEqual(Path(consumer.__file__).resolve(), HERE.parent / "apple_consumer/run.py")
        self.assertEqual(Path(supervisor.__file__).resolve(), ROOT / "Tools/PinkhaSimulatorGate/run_owned_single_lane.py")
        self.assertEqual(Path(owned.__file__).resolve(), ROOT / "Tools/PinkhaSimulatorGate/wave15_batch.py")
        imported = loaded_sources()
        save(directory / "actual-import-source-closure-before.json", imported)

        complete = directory / "actual-complete"
        complete.mkdir()
        receipt = {}
        command = [sys.executable, "-c",
                   "import json,os; print(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'kind':'page-kernel-control'}),flush=True)"]
        with mock.patch.object(supervisor.subprocess, "check_output",
                               side_effect=AssertionError("The actual timely ESRCH path must not call ps")):
            log, row = consumer.Commands(ROOT, complete, receipt).run(command, "actual-child", 5)
        raw_path = log.with_suffix(".command.json")
        original = read(raw_path)
        calibrated = read(log)
        self.assertEqual(calibrated["pid"], calibrated["pgid"])
        self.assertEqual(calibrated["pid"], original["worker_pid"])
        self.assertEqual(original["argv"], command)
        self.assertEqual(original["return_code"], 0)
        self.assertEqual(original["owned_group_cleanup"], "TERM_THEN_KILL")
        self.assertNotIn("cleanup_error_type", original)
        observation = row["owned_group_quiescence"]
        self.assertEqual(observation["status"], "PASS")
        self.assertEqual(observation["pgid"], original["worker_pid"])
        self.assertEqual(observation["live_members"], 0)
        self.assertEqual(observation["observations"], 0)
        self.assertEqual(observation["budget_seconds"], 10)
        self.assertEqual(observation["absence_source"], "KERNEL_ESRCH")
        kernel = observation["kernel_group_observation"]
        self.assertEqual(kernel["operation"], "os.killpg")
        self.assertEqual(kernel["signal"], 0)
        self.assertEqual(kernel["pgid"], original["worker_pid"])
        self.assertEqual(kernel["errno"], errno.ESRCH)
        self.assertEqual(kernel["outcome"], "ABSENT_ESRCH")
        self.assertLessEqual(kernel["before_monotonic"], kernel["after_monotonic"])
        self.assertLessEqual(kernel["after_monotonic"], kernel["deadline_monotonic"])
        self.assertGreater(kernel["deadline_monotonic"] - kernel["before_monotonic"], 0)
        self.assertLessEqual(kernel["deadline_monotonic"] - kernel["before_monotonic"], 10)
        self.assertEqual(read(complete / "execution.json")["commands"], [row])
        save(directory / "actual-complete-proof.json", {
            "kind": "ACTUAL_OWNED_CHILD_AND_UNMODIFIED_KERNEL_QUERY",
            "profile": PROFILE, "command_sha256": sha(raw_path), "log_sha256": sha(log),
            "actual_pid": original["worker_pid"], "actual_pgid": calibrated["pgid"],
            "quiescence": observation, "actual_apple_commands": 0})

        timeout_dir = directory / "actual-timeout"
        timeout_dir.mkdir()
        timeout_receipt = {}
        timeout_command = [sys.executable, "-c",
            "import json,os,time; print(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'kind':'page-timeout-control'}),flush=True); time.sleep(30)"]
        primary = {}
        injected = []
        real_worker = owned.run_worker_command

        def capture_real_timeout(*args, **kwargs):
            try:
                return real_worker(*args, **kwargs)
            except BaseException as error:
                primary["error"] = error
                raise

        def deny_only_after_real_worker_cleanup(pgid, deadline):
            # The complete raw worker receipt is already written. The real
            # TERM/KILL lifecycle has finished before this narrow query injection.
            raw = read(timeout_dir / "actual-timeout.command.json")
            self.assertEqual(raw["worker_pid"], pgid)
            self.assertEqual(raw["owned_group_cleanup"], "TERM_THEN_KILL")
            self.assertNotIn("cleanup_error_type", raw)
            self.assertEqual(raw["error_type"], "TimeoutExpired")
            injected.append({"kind": "SYNTHETIC_KERNEL_EPERM_AFTER_ACTUAL_CLEANUP",
                             "pgid": pgid, "original_command_sha256": sha(timeout_dir / "actual-timeout.command.json")})
            with mock.patch.object(supervisor.os, "killpg",
                                   side_effect=PermissionError(errno.EPERM, "synthetic page query refusal")) as query:
                try:
                    return KERNEL(pgid, deadline)
                finally:
                    query.assert_called_once_with(pgid, 0)

        with mock.patch.object(owned, "run_worker_command", side_effect=capture_real_timeout):
            with mock.patch.object(supervisor, "_sdk06_kernel_group_observation",
                                   side_effect=deny_only_after_real_worker_cleanup):
                with self.assertRaises(subprocess.TimeoutExpired) as captured:
                    consumer.Commands(ROOT, timeout_dir, timeout_receipt).run(
                        timeout_command, "actual-timeout", 0.2)
        self.assertIs(captured.exception, primary["error"])
        self.assertEqual(captured.exception.cmd, timeout_command)
        self.assertEqual(captured.exception.timeout, 0.2)
        timed = read(timeout_dir / "actual-timeout.command.json")
        self.assertEqual(timed["status"], "TIMED_OUT")
        self.assertEqual(timed["error_type"], "TimeoutExpired")
        self.assertEqual(timed["owned_group_cleanup"], "TERM_THEN_KILL")
        self.assertNotIn("cleanup_error_type", timed)
        self.assertEqual(len(injected), 1)
        projected = timeout_receipt["commands"][0]
        self.assertNotIn("owned_group_quiescence", projected)
        failure = projected["quiescence_failure"]
        self.assertEqual(failure["error_type"], "PermissionError")
        self.assertEqual(failure["timeout_observations"], [])
        self.assertEqual(failure["quiescence_observation"]["status"], "FAIL_KERNEL_QUERY")
        self.assertEqual(failure["quiescence_observation"]["pgid"], timed["worker_pid"])
        self.assertEqual(failure["quiescence_observation"]["kernel_group_observation"]["outcome"], "KERNEL_QUERY_ERROR")
        self.assertEqual(failure["quiescence_observation"]["kernel_group_observation"]["errno"], errno.EPERM)
        # This is a new unmodified read of the actual owned group after removing
        # the query injection. It does not change the original failed projection.
        actual_absence = KERNEL(timed["worker_pid"], time.monotonic() + 10)
        self.assertEqual(actual_absence["outcome"], "ABSENT_ESRCH")
        self.assertEqual(actual_absence["errno"], errno.ESRCH)
        self.assertLessEqual(actual_absence["after_monotonic"], actual_absence["deadline_monotonic"])
        save(directory / "actual-timeout-proof.json", {
            "kind": "ACTUAL_COMMAND_TIMEOUT_WITH_SEPARATELY_INJECTED_QUERY_ERROR",
            "profile": PROFILE, "actual_pid": timed["worker_pid"],
            "original_command_sha256": sha(timeout_dir / "actual-timeout.command.json"),
            "original_log_sha256": sha(timeout_dir / "actual-timeout.log"),
            "primary_type": type(captured.exception).__name__, "primary_object_preserved": True,
            "injection": injected, "original_projection_stays_failed": True,
            "quiescence_failure": failure, "independent_actual_group_absence": actual_absence,
            "actual_apple_commands": 0})
        self.assertEqual(read(timeout_dir / "execution.json")["commands"], [projected])
        self.assertNotEqual(timed["worker_pid"], original["worker_pid"])

        synthetic = []
        # These observations exercise only the new caller profile. No process is
        # spawned, and none of the synthetic times/outcomes is actual OS evidence.
        late_clock = iter((100.0, 100.1, 110.01))
        late_time = SimpleNamespace(monotonic=lambda: next(late_clock),
                                    sleep=lambda _: self.fail("Unexpected synthetic sleep"))
        with mock.patch.object(supervisor, "time", late_time):
            with mock.patch.object(supervisor.os, "killpg",
                                   side_effect=ProcessLookupError(errno.ESRCH, "synthetic absence")) as query:
                with mock.patch.object(supervisor.subprocess, "check_output",
                                       side_effect=AssertionError("Late ESRCH cannot fall through to ps")):
                    with self.assertRaises(RuntimeError) as late:
                        supervisor.verify_owned_group_stopped(raw_path, cleanup_profile=PROFILE)
                query.assert_called_once_with(original["worker_pid"], 0)
        self.assertEqual(late.exception.quiescence_observation["status"], "FAIL_DEADLINE")
        self.assertEqual(late.exception.quiescence_observation["kernel_group_observation"]["outcome"], "ABSENT_ESRCH")
        synthetic.append({"kind": "SYNTHETIC_LATE_ESRCH_CALLER_REFUSAL", "actual_os_observation": False,
                          "original_command_sha256": sha(raw_path), "profile": PROFILE,
                          "error_type": type(late.exception).__name__,
                          "observation": late.exception.quiescence_observation})

        exists_clock = iter((100.0, 100.1, 100.2, 100.3, 110.1))
        exists_time = SimpleNamespace(monotonic=lambda: next(exists_clock),
                                      sleep=lambda _: self.fail("Unexpected synthetic sleep"))
        probes = []

        def timed_ps(argv, *, text, timeout):
            self.assertEqual(argv, ["ps", "-axo", "pid=,pgid=,stat="])
            self.assertIs(text, True)
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 10)
            probes.append({"argv": argv, "timeout": timeout, "synthetic": True})
            raise subprocess.TimeoutExpired(argv, timeout)

        with mock.patch.object(supervisor, "time", exists_time):
            with mock.patch.object(supervisor.os, "killpg", return_value=None) as query:
                with mock.patch.object(supervisor.subprocess, "check_output", side_effect=timed_ps):
                    with self.assertRaises(subprocess.TimeoutExpired) as exists:
                        supervisor.verify_owned_group_stopped(raw_path, cleanup_profile=PROFILE)
                query.assert_called_once_with(original["worker_pid"], 0)
        self.assertEqual(len(probes), 1)
        self.assertEqual(exists.exception.quiescence_observation["status"], "FAIL_PS_AFTER_KERNEL_GROUP_EXISTS")
        self.assertIsNone(exists.exception.quiescence_observation["live_members"])
        self.assertEqual(exists.exception.quiescence_observation["kernel_group_observation"]["outcome"], "GROUP_EXISTS")
        self.assertEqual(exists.exception.timeout_observations,
                         [{"observation": 1, "timeout_seconds": probes[0]["timeout"]}])
        synthetic.append({"kind": "SYNTHETIC_GROUP_EXISTS_AND_PS_TIMEOUT_CALLER_REFUSAL",
                          "actual_os_observation": False, "original_command_sha256": sha(raw_path),
                          "profile": PROFILE, "probes": probes, "error_type": type(exists.exception).__name__,
                          "observation": exists.exception.quiescence_observation,
                          "timeout_observations": exists.exception.timeout_observations})
        save(directory / "synthetic-profile-observations.json", synthetic)
        self.assertEqual(loaded_sources(), imported)
        save(directory / "actual-import-source-closure-after.json", loaded_sources())
        save(directory / "scope.json", {
            "control_method": self.id(), "actual_mounted_consumer_imported": True,
            "actual_owned_children": 2, "actual_kernel_absence_observations": 2,
            "injected_kernel_query_errors": 1, "synthetic_refusal_observations": 2,
            "actual_apple_commands": 0, "product_methods": 0, "old_control_methods": 0,
            "actual_page_readiness_or_product_acceptance": "NOT_RUN",
            "first_actual_timeout_retained": True})
