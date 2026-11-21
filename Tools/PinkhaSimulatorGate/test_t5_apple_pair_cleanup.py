"""Controller cleanup controls; mocked Apple commands are not native acceptance."""
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import run_t5_apple_pair as controller


SOURCE = "a" * 40
UDID = "11111111-2222-3333-4444-555555555555"
RUN = "123456"


class ApplePairCleanupControls(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.args = SimpleNamespace(**{key: self.root / key for key in
                                      ["app", "native_source", "work", "evidence", "derived"]},
                                    heart_r14_run_id="14", heart_r15_run_id="15",
                                    include_freshness=False, include_native_ui=False)
        self.args.app.mkdir()
        self.args.native_source.mkdir()
        self.preflight = dict(status="PREFLIGHT_PASS_UI_NOT_RUN", source_sha=SOURCE,
                              selected={"ipad": dict(udid=UDID, name="Pinkha-UI27-" + RUN + "-ipad")})
        self.save_preflight()
        self.result = dict(status="RUNNING", phase="PREFLIGHT", completed_builds=[],
                           completed_phases=[], actual_counts=None)
        self.events = []
        self.command_errors = {}
        self.shutdown_code = 0
        self.container_calls = 0
        self.container_errors = {}
        self.patch(controller.platform, "system", return_value="Darwin")
        self.patch(controller.platform, "machine", return_value="arm64")
        self.patch(sys, "version_info", (3, 12, 0))
        self.patch(sys, "path", list(sys.path))
        self.stack.enter_context(patch.dict(controller.os.environ,
                                           GITHUB_RUN_ID=RUN, GITHUB_REPOSITORY="owner/repo"))
        modules = {name: ModuleType(name) for name in
                   ["build_custom_heart", "build_native_ipa", "run_ui27", "validate_release", "run_t5_native_ui"]}
        modules["validate_release"].method_results = lambda value: value
        modules["run_t5_native_ui"].continue_with_native_ui = lambda **kwargs: self.events.append("optional-ui")
        self.stack.enter_context(patch.dict(sys.modules, modules))
        self.source = self.patch(controller, "verify_published_source", return_value=SOURCE)
        self.patch(controller, "git", side_effect=self.git)
        self.patch(controller.shutil, "disk_usage", return_value=SimpleNamespace(free=10 * 1024**3))
        self.patch(controller, "digest", return_value=controller.BUILDER_SHA)
        self.run_logged = self.patch(controller, "run_logged", side_effect=self.command)
        self.container = self.patch(controller, "app_container", side_effect=self.get_container)
        self.download = self.patch(controller, "download_runtime", return_value=(self.root / "archive", {}))
        self.install = self.patch(controller, "install_runtime", return_value=self.root / "framework")
        self.build = self.patch(controller, "build_app", side_effect=self.build_app)
        self.patch(controller.shutil, "move")
        self.phase = self.patch(controller, "run_phase", side_effect=self.run_phase)
        self.credentials = self.patch(controller, "preserve_private_credential_inventory", return_value=None)
        self.preserve = self.patch(controller, "preserve_native_evidence", side_effect=self.preserve_evidence)
        self.patch(controller, "validate_sequence", return_value={"named_swift_tests_passed": 4})

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(patch.object(obj, name, *args, **kwargs))

    def save_preflight(self):
        controller.write(self.args.evidence / "preflight/preflight.json", self.preflight)

    def git(self, root, *args):
        if args == ("rev-parse", "HEAD"):
            return controller.NATIVE_SOURCE if root == self.args.native_source else SOURCE
        if args == ("status", "--porcelain"):
            return ""
        self.fail("Unexpected git call")

    def command(self, argv, cwd, directory, name, timeout, check=True, output=None):
        self.events.append(name)
        if name in self.command_errors:
            raise self.command_errors[name]
        return {"return_code": self.shutdown_code if name == "shutdown" else 0}, directory / (name + ".log")

    def get_container(self, *args, **kwargs):
        self.container_calls += 1
        self.events.append("container-" + str(self.container_calls))
        if self.container_calls in self.container_errors:
            raise self.container_errors[self.container_calls]
        return None if self.container_calls == 1 else self.root / "container"

    def build_app(self, role, *args, **kwargs):
        self.events.append("build-" + role)
        return {"role": role}

    def run_phase(self, phase, *args, **kwargs):
        self.events.append(phase)
        return {"phase": phase}, self.root / "container"

    def preserve_evidence(self, *args, **kwargs):
        self.events.append("preserve-evidence")
        return True

    def execute(self):
        controller.execute(self.args, self.result)

    def assert_shutdown(self, status="PASS", primary=None):
        calls = [call for call in self.run_logged.call_args_list if call.args[3] == "shutdown"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args,
                         (["xcrun", "simctl", "shutdown", UDID], self.args.app,
                          self.args.evidence / "simulator", "shutdown", 120))
        self.assertEqual(calls[0].kwargs, {"check": False})
        receipt = self.result["simulator_cleanup"]
        self.assertEqual(receipt["status"], status)
        self.assertEqual(receipt["action"], "shutdown")
        self.assertEqual(receipt["device_udid"], UDID)
        self.assertEqual(receipt["primary_error_type"], type(primary).__name__ if primary else None)
        self.assertEqual(json.loads((self.args.evidence / "simulator/cleanup.json").read_text()), receipt)

    def test_boot_timeout_shuts_down_once_without_container_or_account_reads(self):
        error = subprocess.TimeoutExpired(["xcrun", "simctl", "boot"], 120)
        self.command_errors["boot"] = error
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.events, ["boot", "shutdown"])
        self.container.assert_not_called()
        self.credentials.assert_not_called()
        self.preserve.assert_not_called()
        self.assertEqual(self.result["completed_builds"], [])
        self.assertEqual(self.result["completed_phases"], [])
        self.assertIsNone(self.result["actual_counts"])
        self.assert_shutdown(primary=error)

    def test_bootstatus_cancellation_keeps_original_error_and_shuts_down_once(self):
        error = KeyboardInterrupt()
        self.command_errors["boot-status"] = error
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.events, ["boot", "boot-status", "shutdown"])
        self.container.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_bootstatus_timeout_preserves_timeout_and_zero_native_execution(self):
        error = subprocess.TimeoutExpired(["xcrun", "simctl", "bootstatus"], 180)
        self.command_errors["boot-status"] = error
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.build.assert_not_called()
        self.phase.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_boot_cancellation_shuts_down_once(self):
        error = KeyboardInterrupt()
        self.command_errors["boot"] = error
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assert_shutdown(primary=error)

    def test_fresh_container_lookup_failure_shuts_down_before_any_build(self):
        error = OSError("container lookup failed")
        self.container_errors[1] = error
        with self.assertRaises(OSError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.build.assert_not_called()
        self.preserve.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_build_failure_shuts_down_without_native_account_finalization(self):
        error = RuntimeError("build failed")
        self.build.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.container_calls, 1)
        self.credentials.assert_not_called()
        self.preserve.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_runtime_download_failure_shuts_down(self):
        error = RuntimeError("runtime unavailable")
        self.download.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.build.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_native_phase_failure_preserves_evidence_before_shutdown(self):
        error = RuntimeError("native phase failed")
        self.phase.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assertEqual(self.events[-2:], ["preserve-evidence", "shutdown"])
        self.assert_shutdown(primary=error)

    def test_final_container_lookup_failure_cannot_bypass_shutdown(self):
        error = OSError("final container unavailable")
        self.container_errors[2] = error
        with self.assertRaises(OSError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.preserve.assert_not_called()
        self.assert_shutdown(primary=error)

    def test_native_evidence_failure_cannot_bypass_shutdown(self):
        error = RuntimeError("evidence failed")
        self.preserve.side_effect = error
        with self.assertRaises(RuntimeError) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assert_shutdown(primary=error)

    def test_shutdown_exception_cannot_replace_primary_timeout(self):
        primary = subprocess.TimeoutExpired(["boot"], 120)
        self.command_errors.update(boot=primary, shutdown=OSError("cleanup failed"))
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.execute()
        self.assertIs(caught.exception, primary)
        self.assert_shutdown(status="FAIL", primary=primary)
        self.assertEqual(self.result["simulator_cleanup"]["error_type"], "OSError")

    def test_nonzero_shutdown_is_failure_and_keeps_primary_cancellation(self):
        primary = KeyboardInterrupt()
        self.command_errors["boot"] = primary
        self.shutdown_code = 1
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.execute()
        self.assertIs(caught.exception, primary)
        self.assert_shutdown(status="FAIL", primary=primary)
        self.assertEqual(self.result["simulator_cleanup"]["return_code"], 1)

    def test_shutdown_failure_after_successful_phases_prevents_pass_and_optional_ui(self):
        self.args.include_native_ui = True
        self.shutdown_code = 1
        with self.assertRaisesRegex(RuntimeError, "shutdown failed"):
            self.execute()
        self.assertNotEqual(self.result["status"], "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS")
        self.assertNotIn("optional-ui", self.events)
        self.assert_shutdown(status="FAIL")

    def test_shutdown_exception_without_primary_remains_failure(self):
        error = subprocess.TimeoutExpired(["shutdown"], 120)
        self.command_errors["shutdown"] = error
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.execute()
        self.assertIs(caught.exception, error)
        self.assert_shutdown(status="FAIL")

    def test_cleanup_receipt_write_failure_cannot_mask_primary_error(self):
        primary = KeyboardInterrupt()
        self.command_errors["boot"] = primary
        original = controller.write
        def write(path, value):
            if path.name == "cleanup.json":
                raise OSError("disk full")
            return original(path, value)
        self.patch(controller, "write", side_effect=write)
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.execute()
        self.assertIs(caught.exception, primary)
        self.assertEqual(self.result["simulator_cleanup"]["receipt_error_type"], "OSError")
        self.assertEqual(self.result["simulator_cleanup"]["status"], "FAIL")
        self.assertEqual(self.events, ["boot", "shutdown"])

    def test_success_preserves_phase_order_then_shuts_down_before_optional_ui(self):
        self.args.include_native_ui = True
        self.execute()
        self.assertEqual([event for event in self.events if event in dict(controller.PHASES)],
                         [phase for phase, _ in controller.PHASES])
        self.assertEqual(self.events[-3:], ["preserve-evidence", "shutdown", "optional-ui"])
        self.assertEqual(self.result["status"], "APPLE_SAME_ACCOUNT_RUNTIME_PAIR_PASS")
        self.assert_shutdown()

    def test_untrusted_source_prevents_any_simulator_command(self):
        self.source.side_effect = RuntimeError("source mismatch")
        with self.assertRaisesRegex(RuntimeError, "source mismatch"):
            self.execute()
        self.run_logged.assert_not_called()
        self.assertNotIn("simulator_cleanup", self.result)

    def test_mismatched_preflight_prevents_any_simulator_command(self):
        self.preflight["source_sha"] = "0" * 40
        self.save_preflight()
        with self.assertRaisesRegex(RuntimeError, "source-bound"):
            self.execute()
        self.run_logged.assert_not_called()
        self.assertNotIn("simulator_cleanup", self.result)

    def test_unowned_simulator_name_prevents_any_simulator_command(self):
        self.preflight["selected"]["ipad"]["name"] = "Another-job-ipad"
        self.save_preflight()
        with self.assertRaisesRegex(RuntimeError, "job-owned"):
            self.execute()
        self.run_logged.assert_not_called()
        self.assertNotIn("simulator_cleanup", self.result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
