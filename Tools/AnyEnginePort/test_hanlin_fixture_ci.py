#!/usr/bin/env python3
"""Focused regression for the public simctl capability preflight."""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("hanlin_fixture_ci", Path(__file__).with_name("hanlin_fixture_ci.py"))
CI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CI)


class ReadyToCreateOwnedFixture(RuntimeError):
    pass


class SimulatorKeychainCapabilityTests(unittest.TestCase):
    def prepare_until_capability_boundary(self, stdout, stderr, returncode=0):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = argparse.Namespace(safe_dir=directory, simulator_receipt=directory / "simulator.json")
            with patch.object(CI, "github_context", return_value=("123", "a" * 40, directory)), \
                 patch.object(CI, "verify_simulator", return_value=("owned", {}, "Booted")), \
                 patch.object(CI, "ensure_owned_simulator_booted"), \
                 patch.object(CI.subprocess, "run", return_value=subprocess.CompletedProcess(
                     ["xcrun", "simctl", "help", "keychain"], returncode, stdout, stderr)) as command, \
                 patch.object(CI.tempfile, "mkdtemp", side_effect=ReadyToCreateOwnedFixture) as create:
                error = None
                try:
                    CI.prepare(args, {})
                except (CI.BoundaryError, ReadyToCreateOwnedFixture) as caught:
                    error = caught
                help_file = directory / "simctl-keychain-help.txt"
                help_text = help_file.read_text(encoding="utf-8") if help_file.exists() else None
                self.assertEqual(command.call_args.args[0], ["xcrun", "simctl", "help", "keychain"])
                return error, help_text, create.called

    def test_supported_command_in_stderr_reaches_owned_fixture_setup(self):
        help_text = "Usage: simctl keychain <device> add-root-cert <path>\n"
        error, recorded, created = self.prepare_until_capability_boundary("", help_text)
        self.assertIsInstance(error, ReadyToCreateOwnedFixture)
        self.assertEqual(recorded, help_text)
        self.assertTrue(created)

    def test_supported_command_in_stdout_reaches_owned_fixture_setup(self):
        help_text = "Usage: simctl keychain <device> add-root-cert <path>\n"
        error, recorded, created = self.prepare_until_capability_boundary(help_text, "")
        self.assertIsInstance(error, ReadyToCreateOwnedFixture)
        self.assertEqual(recorded, help_text)
        self.assertTrue(created)

    def test_missing_command_fails_before_any_fixture_or_trust_mutation(self):
        help_text = "Usage: simctl keychain <device> reset\n"
        error, recorded, created = self.prepare_until_capability_boundary("", help_text)
        self.assertIsInstance(error, CI.BoundaryError)
        self.assertEqual(str(error), "simulator_root_command_unavailable")
        self.assertEqual(recorded, help_text)
        self.assertFalse(created)

    def test_failed_help_command_is_not_accepted_from_its_output(self):
        error, _, created = self.prepare_until_capability_boundary("", "add-root-cert", returncode=1)
        self.assertIsInstance(error, CI.BoundaryError)
        self.assertEqual(str(error), "owned_command_failed")
        self.assertFalse(created)

    def test_other_commands_keep_stderr_separate(self):
        with patch.object(CI.subprocess, "run", return_value=subprocess.CompletedProcess(
                ["private-command"], 0, "public-stdout", "private-diagnostics")):
            self.assertEqual(CI.run(["private-command"]), "public-stdout")



class OwnedSimulatorReadinessTests(unittest.TestCase):
    def test_shutdown_device_is_booted_and_reverified_before_fixture_setup(self):
        result = {}
        with patch.object(CI, "run", return_value="") as command, \
             patch.object(CI, "verify_simulator", return_value=("owned", {"runtime": "test"}, "Booted")) as verify:
            CI.ensure_owned_simulator_booted(Path("receipt"), "123", "owned",
                                            {"runtime": "test"}, "Shutdown", result)
        self.assertEqual([entry.args[0] for entry in command.call_args_list], [
            ["xcrun", "simctl", "boot", "owned"],
            ["xcrun", "simctl", "bootstatus", "owned", "-b"]])
        verify.assert_called_once_with(Path("receipt"), "123")
        self.assertEqual(result, {"simulatorInitialState": "Shutdown",
                                 "simulatorBootRequested": True, "simulatorReadyState": "Booted"})

    def test_already_booting_or_booted_device_is_waited_without_duplicate_boot(self):
        for state in ("Booting", "Booted"):
            with self.subTest(state=state), \
                 patch.object(CI, "run", return_value="") as command, \
                 patch.object(CI, "verify_simulator", return_value=("owned", {}, "Booted")):
                result = {}
                CI.ensure_owned_simulator_booted(Path("receipt"), "123", "owned", {}, state, result)
                self.assertEqual([entry.args[0] for entry in command.call_args_list],
                                 [["xcrun", "simctl", "bootstatus", "owned", "-b"]])
                self.assertFalse(result["simulatorBootRequested"])

    def test_unknown_state_fails_before_any_boot_or_trust_command(self):
        with patch.object(CI, "run") as command:
            with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_state_unavailable$"):
                CI.ensure_owned_simulator_booted(Path("receipt"), "123", "owned", {}, "Creating", {})
        command.assert_not_called()



    def test_boot_failure_does_not_continue_to_readiness_or_fixture_setup(self):
        with patch.object(CI, "run", side_effect=CI.BoundaryError("owned_simulator_boot_failed")) as command, \
             patch.object(CI, "verify_simulator") as verify:
            with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_boot_failed$"):
                CI.ensure_owned_simulator_booted(Path("receipt"), "123", "owned", {}, "Shutdown", {})
        self.assertEqual(command.call_count, 1)
        verify.assert_not_called()

    def test_changed_ownership_or_not_booted_after_readiness_is_rejected(self):
        for final in (("other", {}, "Booted"), ("owned", {"changed": True}, "Booted"),
                      ("owned", {}, "Shutdown")):
            with self.subTest(final=final), patch.object(CI, "run", return_value=""), \
                 patch.object(CI, "verify_simulator", return_value=final):
                with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_boot_verification_failed$"):
                    CI.ensure_owned_simulator_booted(Path("receipt"), "123", "owned", {}, "Booting", {})

    def test_command_failure_uses_fixed_stage_without_private_output(self):
        for failure in (subprocess.CompletedProcess(["private-command"], 1, "secret", "private"),
                        subprocess.TimeoutExpired(["private-command", "secret"], 1, output="private")):
            with self.subTest(kind=type(failure).__name__):
                kwargs = {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
                with patch.object(CI.subprocess, "run", **kwargs):
                    with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_root_install_failed$"):
                        CI.run(["private-command"], failure_reason="owned_simulator_root_install_failed")



class OwnedBootOverlapTests(unittest.TestCase):
    def test_boot_request_is_pending_without_a_fixture_or_full_boot_wait(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = argparse.Namespace(safe_dir=directory, simulator_receipt=directory / "simulator.json")
            result = {}
            with patch.object(CI, "github_context", return_value=("123", "a" * 40, directory)), \
                 patch.object(CI, "verify_simulator", return_value=("owned", {}, "Shutdown")), \
                 patch.object(CI, "run", return_value="") as command, \
                 patch.object(CI.tempfile, "mkdtemp") as fixture:
                CI.boot(args, result)
            self.assertEqual([entry.args[0] for entry in command.call_args_list],
                             [["xcrun", "simctl", "boot", "owned"]])
            self.assertEqual(result["status"], "OWNED_SIMULATOR_BOOT_REQUESTED_READINESS_PENDING")
            self.assertNotIn("simulatorReadyState", result)
            fixture.assert_not_called()

    def test_unverified_device_cannot_receive_an_early_boot_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = argparse.Namespace(safe_dir=directory, simulator_receipt=directory / "simulator.json")
            with patch.object(CI, "github_context", return_value=("123", "a" * 40, directory)), \
                 patch.object(CI, "verify_simulator", side_effect=CI.BoundaryError("owned_simulator_receipt_mismatch")), \
                 patch.object(CI, "run") as command:
                with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_receipt_mismatch$"):
                    CI.boot(args, {})
            command.assert_not_called()

    def test_public_readiness_timeout_keeps_original_progress_and_fixed_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "simulator-bootstatus.txt"
            with patch.object(CI.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                    ["xcrun", "simctl", "bootstatus", "owned", "-b"], 120,
                    output=b"Waiting for data migration\\n", stderr=b"Still booting\\n")):
                with self.assertRaisesRegex(CI.BoundaryError, "^owned_simulator_boot_readiness_failed$"):
                    CI.run(["xcrun", "simctl", "bootstatus", "owned", "-b"], timeout=120,
                           failure_reason="owned_simulator_boot_readiness_failed", public_log=log)
            self.assertIn("Waiting for data migration", log.read_text())
            self.assertIn("Still booting", log.read_text())


if __name__ == "__main__":
    unittest.main()
