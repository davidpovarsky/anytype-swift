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
                 patch.object(CI, "verify_simulator", return_value=("owned", {})), \
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


if __name__ == "__main__":
    unittest.main()
