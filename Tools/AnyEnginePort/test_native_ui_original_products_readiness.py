"""Two new UI readiness adapter controls; no Apple, product or retained test methods."""
from __future__ import annotations
import contextlib
import copy
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest import mock

import native_ui_original_products_readiness as r

ORIGINAL_APP_SHA = "4b09cc5478c60c1c6728a54f2a27a115637a835b"


class UIOriginalProductsReadinessTests(unittest.TestCase):
    def originals(self, name):
        path = Path(os.environ["PINKHA_UI_READINESS_CONTROL_ORIGINALS"]).resolve()
        self.assertTrue(path.is_dir())
        target = path / name
        target.mkdir()
        return target

    def test_owned_command_binds_actual_child_and_preserves_first_failure(self):
        directory = self.originals("owned-command")
        helpers = r.verify_helpers()
        r.write_new(directory / "helper-bindings.json", helpers)
        command = [sys.executable, "-c",
                   "import json,os;print(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp()}),flush=True)"]
        observed, log = r.run_owned(command, directory / "complete.log", 5)
        actual = json.loads(log.read_text())
        record = r.c.data(log.with_suffix(".command.json"))
        proof = r.c.data(log.with_suffix(".ui-quiescence.json"))
        self.assertEqual(record["argv"], command)
        self.assertEqual(record["cwd"], str(r.ROOT))
        self.assertEqual(record["timeout_seconds"], 5)
        self.assertEqual(actual["pid"], actual["pgid"])
        self.assertEqual(actual["pgid"], record["worker_pid"])
        self.assertEqual(proof["quiescence"]["pgid"], actual["pgid"])
        self.assertEqual(proof["quiescence"]["kernelObservation"]["outcome"], "ABSENT_ESRCH")
        self.assertEqual(proof["quiescence"]["liveMembers"], 0)
        self.assertEqual(proof["scope"], r.PROFILE)
        self.assertEqual(proof["status"], "PASS")
        self.assertEqual(observed["return_code"], 0)

        mutations = {
            "boolean_pid": {"worker_pid": True},
            "init_pid": {"worker_pid": 1},
            "self_pid": {"worker_pid": os.getpid()},
            "self_group": {"worker_pid": os.getpgrp()},
            "foreign_pid": {"worker_pid": actual["pid"] + 100000},
            "foreign_argv": {"argv": ["foreign"]},
            "foreign_cwd": {"cwd": "/"},
            "changed_timeout": {"timeout_seconds": 6},
            "boolean_timeout": {"timeout_seconds": True},
            "uncompleted_cleanup": {"owned_group_cleanup": None},
            "cleanup_error": {"cleanup_error_type": "RuntimeError"},
        }
        for name, values in mutations.items():
            with self.subTest(name=name), mock.patch.object(r.kernel, "_sdk06_kernel_group_observation") as query:
                malformed = {**record, **values}
                with self.assertRaises(RuntimeError):
                    r.kernel_absence(malformed, command, 5,
                                     returned_record=record if name == "foreign_pid" else malformed)
                query.assert_not_called()

        def kernel_observation(outcome, after_deadline=False):
            def query(pid, deadline):
                now = time.monotonic()
                return {"operation": "os.killpg", "signal": 0, "pgid": pid,
                        "errno": errno.ESRCH if outcome == "ABSENT_ESRCH" else None,
                        "before_monotonic": now,
                        "after_monotonic": deadline + 0.001 if after_deadline else time.monotonic(),
                        "deadline_monotonic": deadline, "outcome": outcome}
            return query

        for name, replacement in (("group_exists", kernel_observation("GROUP_EXISTS")),
                                  ("late_absence", kernel_observation("ABSENT_ESRCH", True))):
            with self.subTest(name=name), mock.patch.object(
                    r.kernel, "_sdk06_kernel_group_observation", side_effect=replacement):
                with self.assertRaises(RuntimeError) as caught:
                    r.kernel_absence(record, command, 5, returned_record=record)
                self.assertEqual(caught.exception.quiescence_observation["scope"], r.PROFILE)
                r.write_new(directory / (name + "-synthetic-observation.json"),
                            r.error_record(caught.exception))

        failing = [sys.executable, "-c", "import sys;print('owned-control-exit-9',flush=True);sys.exit(9)"]
        kernel_error = PermissionError(errno.EPERM, "synthetic kernel observation refusal")
        with mock.patch.object(r.kernel, "_sdk06_kernel_group_observation", side_effect=kernel_error):
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                r.run_owned(failing, directory / "nonzero.log", 5)
        self.assertEqual(caught.exception.returncode, 9)
        failed = r.c.data(directory / "nonzero.command.json")
        failure = r.c.data(directory / "nonzero.ui-quiescence.json")
        self.assertEqual(failed["return_code"], 9)
        self.assertEqual(failure["commandFailure"]["type"], "CalledProcessError")
        self.assertEqual(failure["quiescenceFailure"]["type"], "PermissionError")
        self.assertEqual(failure["status"], "FAIL")
        # The injected observation error is retained. Separately prove our real child is gone.
        actual_absence = r.kernel_absence(failed, failing, 5, returned_record=failed)
        r.write_new(directory / "nonzero-actual-owned-group-absence.json", actual_absence)

    def test_driver_binds_real_both_origin_imports_before_exact_readiness(self):
        directory = self.originals("driver-composition")
        app = Path(os.environ["PINKHA_UI_READINESS_ORIGINAL_APP"]).resolve()
        app_head = subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"],
                                           text=True, timeout=30).strip()
        self.assertEqual(app_head, ORIGINAL_APP_SHA)
        self.assertEqual(subprocess.check_output(["git", "-C", str(app), "status", "--porcelain"],
                                                 text=True, timeout=30).strip(), "")
        current_head = subprocess.check_output(["git", "-C", str(r.ROOT), "rev-parse", "HEAD"],
                                               text=True, timeout=30).strip()
        # Use the real current provider/Gate modules and the real six immutable App validators.
        r.ui.provider()
        legacy = r.c.legacy_modules(app)
        bindings = r.bind_modules(app, legacy)
        sources = r.verify_source_closures(app, current_head, app_head)
        helpers = r.verify_helpers()
        r.write_new(directory / "actual-import-origin-closures.json",
                    {"sourceBindings": sources, "requiredModuleBindings": bindings,
                     "helperBindings": helpers, "testOnly": True, "productMethodsExecuted": 0})
        self.assertIn("Tools/PinkhaSimulatorGate/run_owned_single_lane.py", sources["current"]["files"])
        self.assertIn("Tools/AnyEnginePort/verify_custom_type.py", sources["originalApp"]["files"])
        self.assertEqual(sources["originalApp"]["commit"], ORIGINAL_APP_SHA)

        fixed = r.c.contract()
        fixed_runtime = fixed["runtime"]
        udid = "A413A413-8117-4B09-A413-A413A413A413"
        run_id = "90000000001"
        ctx = {"controlCommit": current_head, "currentRunID": run_id, "currentRunAttempt": 1,
               "fixtureOnly": True}
        actual_owned = r.run_owned
        actual_closures = r.verify_source_closures

        @contextlib.contextmanager
        def pipeline(name, *, failed_bootstatus=False, foreign_module=False, source_failure=None,
                     admission_failure=False, wrong_uuid=False):
            case = directory / name
            case.mkdir()
            evidence = case / "evidence"
            evidence.mkdir()
            admitted = {"fixtureOnly": True, "ownedSimulatorUDID": udid}
            runtime = {"runtime": {"identifier": fixed_runtime["identifier"]},
                       "device": {"identifier": fixed_runtime["deviceType"]},
                       "ownedSimulatorUDID": "B413A413-8117-4B09-A413-A413A413A413" if wrong_uuid else udid}
            r.write_new(evidence / "native-ui-original-runtime.json", runtime)
            r.write_new(evidence / "admission.json", admitted)
            observations = []
            modules = dict(legacy)
            if foreign_module:
                modules["verify_custom_type"] = r.c

            def current():
                observations.append({"phase": "current_admission"})
                if admission_failure:
                    raise RuntimeError("synthetic current admission refused")
                return fixed, ctx, {"app": app, "evidence": evidence}, admitted, modules

            def closures(*args):
                observations.append({"phase": "both_real_git_closures"})
                value = actual_closures(*args)
                if source_failure is not None:
                    source_failure()
                return value

            def control_command(requested, log, timeout):
                self.assertTrue(any(x["phase"] == "both_real_git_closures" for x in observations))
                self.assertEqual(requested[:2], ["xcrun", "simctl"])
                action = requested[2]
                if action == "list":
                    self.assertEqual(requested, ["xcrun", "simctl", "list", "devices", udid, "--json"])
                    self.assertEqual(timeout, 60)
                    value = {"devices": {fixed_runtime["identifier"]: [{
                        "udid": udid, "name": "AnyNativePort-" + run_id,
                        "deviceTypeIdentifier": fixed_runtime["deviceType"],
                        "state": "Shutdown", "isAvailable": True}]}}
                    body = "print(" + repr(json.dumps(value)) + ",flush=True)"
                elif action == "boot":
                    self.assertEqual(requested, ["xcrun", "simctl", "boot", udid])
                    self.assertEqual(timeout, 120)
                    body = "print('CONTROL_BOOT_REQUEST_ONLY',flush=True)"
                elif action == "bootstatus":
                    self.assertEqual(requested, ["xcrun", "simctl", "bootstatus", udid, "-b"])
                    self.assertEqual(timeout, 180)
                    body = ("import sys;print('CONTROL_BOOTSTATUS',flush=True);sys.exit(" +
                            ("13" if failed_bootstatus else "0") + ")")
                else:
                    self.fail("unadmitted fixture command")
                actual = [sys.executable, "-c", body]
                observations.append({"phase": "controlled_simulator_command", "requested": requested,
                                     "actualOwnedControlArgv": actual, "timeoutSeconds": timeout,
                                     "appleCommandExecuted": False})
                return actual_owned(actual, log, timeout)

            with mock.patch.object(r.ui, "current", side_effect=current), \
                    mock.patch.object(r, "verify_source_closures", side_effect=closures), \
                    mock.patch.object(r, "run_owned", side_effect=control_command), \
                    mock.patch.object(r.c, "EVIDENCE", evidence), \
                    mock.patch.object(r.c, "ADMISSION", evidence / "admission.json"), \
                    mock.patch.object(r, "READY_ROOT", evidence / "owned-readiness"), \
                    mock.patch.object(r, "RESULT", evidence / "result.json"):
                try:
                    yield observations, evidence
                finally:
                    r.write_new(case / "control-call-map.json",
                                {"observations": observations, "actualCIAdmissionClaimed": False,
                                 "actualAppleCommandsExecuted": 0, "productMethodsExecuted": 0})

        with pipeline("success") as (observations, evidence):
            passed = r.run()
            self.assertEqual(passed["status"], "ADMITTED_ORIGINAL_PRODUCTS_OWNED_SIMULATOR_READY")
            self.assertEqual(passed["testsExecuted"], 0)
            self.assertTrue(passed["providerBootedVerificationStillRequired"])
            self.assertEqual([x["requested"][2] for x in observations if "requested" in x],
                             ["list", "boot", "bootstatus"])
            self.assertEqual(observations[0]["phase"], "current_admission")
            self.assertEqual(observations[1]["phase"], "both_real_git_closures")
            self.assertEqual(passed["readiness"]["bootstatus_return_code"], 0)

        with pipeline("bootstatus-failure", failed_bootstatus=True) as (observations, evidence):
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                r.run()
            self.assertEqual(caught.exception.returncode, 13)
            self.assertEqual(r.c.data(evidence / "result.json")["status"], "FAIL")
            self.assertEqual(r.c.data(evidence / "owned-readiness/readiness.json")["status"], "FAIL")

        # A real disposable Git source proves drift refusal without changing any actual input.
        git_root = directory / "source-drift-fixture"
        git_root.mkdir()
        (git_root / "module.py").write_text("VALUE = 1\n")
        subprocess.run(["git", "init", "-q", str(git_root)], check=True, timeout=30)
        subprocess.run(["git", "-C", str(git_root), "add", "module.py"], check=True, timeout=30)
        env = {**os.environ, "GIT_AUTHOR_NAME": "UI control fixture", "GIT_AUTHOR_EMAIL": "fixture@invalid",
               "GIT_COMMITTER_NAME": "UI control fixture", "GIT_COMMITTER_EMAIL": "fixture@invalid"}
        subprocess.run(["git", "-C", str(git_root), "-c", "gc.auto=0", "commit", "-qm", "fixture"],
                       env=env, check=True, timeout=30)
        git_head = subprocess.check_output(["git", "-C", str(git_root), "rev-parse", "HEAD"],
                                           text=True, timeout=30).strip()
        r.git_source_bytes(git_root, git_head, {"module.py": git_root / "module.py"})
        (git_root / "module.py").write_text("VALUE = 2\n")

        def changed_source():
            r.git_source_bytes(git_root, git_head, {"module.py": git_root / "module.py"})

        for name, settings in (
                ("foreign-module", {"foreign_module": True}),
                ("source-drift", {"source_failure": changed_source}),
                ("admission-refusal", {"admission_failure": True}),
                ("wrong-owned-uuid", {"wrong_uuid": True})):
            with self.subTest(name=name), pipeline(name, **settings) as (observations, evidence):
                with self.assertRaises(RuntimeError):
                    r.run()
                self.assertFalse(any(x["phase"] == "controlled_simulator_command" for x in observations))
                self.assertFalse((evidence / "owned-readiness").exists())
                self.assertEqual(r.c.data(evidence / "result.json")["status"], "FAIL")

        workflow = (r.ROOT / ".github/workflows/pinkha-any-native-ui-original-products.yml").read_text()
        create = workflow.index("id: simulator")
        admission = workflow.index("id: admission")
        readiness = workflow.index("id: readiness")
        provider = workflow.index("id: provider\n")
        self.assertLess(create, admission)
        self.assertLess(admission, readiness)
        self.assertLess(readiness, provider)
        self.assertNotIn("id: boot\n", workflow)
        self.assertIn("steps.simulator.outcome == 'success'", workflow[admission:readiness])
        self.assertIn("steps.admission.outcome == 'success'", workflow[readiness:provider])
        self.assertIn("steps.readiness.outcome == 'success'", workflow[provider:workflow.index("id: four")])
        self.assertIn("hanlin_fixture_ci.py prepare", workflow[provider:workflow.index("id: four")])
        self.assertEqual(subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"],
                                                 text=True, timeout=30).strip(), ORIGINAL_APP_SHA)
        self.assertEqual(subprocess.check_output(["git", "-C", str(app), "status", "--porcelain"],
                                                 text=True, timeout=30).strip(), "")
        r.write_new(directory / "final-physical-source-bindings.json",
                    r.recheck_physical_sources(app, sources))


if __name__ == "__main__":
    unittest.main()
