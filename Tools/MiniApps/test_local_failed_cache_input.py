"""Refusal controls for one observed failed-cache continuation; no native credit."""
import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import local_failed_cache_input as failed


class SourceContractControls(unittest.TestCase):
    def setUp(self):
        self.before = {name: old for name, (old, new) in failed.REVIEWED_CHANGES.items()}
        self.before.update({
            "Anytype/Anytype.entitlements": "100644 blob original-capabilities",
            "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved": "100644 blob original-pins",
            "PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift": "100644 blob all-original-methods",
        })
        self.reviewed = dict(self.before)
        self.reviewed.update({name: new for name, (old, new) in failed.REVIEWED_CHANGES.items()})

    def test_exact_three_source_fixes_are_admitted(self):
        self.assertEqual(failed.check_source_contract(self.before, self.reviewed, self.reviewed), self.reviewed)

    def test_extra_reviewed_source_delta_is_refused(self):
        changed = {**self.reviewed, "Anytype/Unexpected.swift": "100644 blob unexpected"}
        with self.assertRaisesRegex(RuntimeError, "exactly the three"):
            failed.check_source_contract(self.before, changed, changed)

    def test_wrong_reviewed_blob_is_refused(self):
        changed = dict(self.reviewed)
        changed[next(iter(failed.REVIEWED_CHANGES))] = "100644 blob other-project"
        with self.assertRaisesRegex(RuntimeError, "exactly the three"):
            failed.check_source_contract(self.before, changed, changed)

    def test_missing_original_edit_menu_fix_is_refused(self):
        changed = dict(self.reviewed)
        name = list(failed.REVIEWED_CHANGES)[1]
        changed[name] = self.before[name]
        with self.assertRaisesRegex(RuntimeError, "exactly the three"):
            failed.check_source_contract(self.before, changed, changed)

    def test_current_ui_capability_dependency_or_unreviewed_source_drift_is_refused(self):
        for name in set(self.before) | {"Anytype/New.swift"}:
            with self.subTest(path=name):
                changed = {**self.reviewed, name: "100644 blob unreviewed"}
                with self.assertRaisesRegex(RuntimeError, "differs from the reviewed repair"):
                    failed.check_source_contract(self.before, self.reviewed, changed)


class FailedIntervalControls(unittest.TestCase):
    def setUp(self):
        self.descriptor = dict(source_sha=failed.FAILED_SOURCE, source_root=str(failed.APP),
            derived=str(failed.DERIVED), configuration="Debug-MiniAppsOwner",
            execution_origin="local-mac", github_run_id=None, run_id="local-actual-shape-fixture")
        self.terminal = dict(status="FAIL", actual_test_methods=0,
            error="build-native returned 65; see the original log",
            source_sha=failed.FAILED_SOURCE, run_id=self.descriptor["run_id"],
            local_execution_sha256=failed.FAILED_RECEIPTS["local-execution.json"])
        self.command = dict(returncode=65, timed_out=False, owned_group_drained=True,
            cwd=str(failed.APP), arguments=["actual-command-shape-only"], log_sha256="complete-log-shape")
        self.build = dict(status="BUILDING", phase="build-native-finished",
            source_sha=failed.FAILED_SOURCE, run_id=self.descriptor["run_id"],
            completed_build_commands={"build-native": {
                "arguments": self.command["arguments"], "log_sha256": self.command["log_sha256"]}})

    def check(self):
        failed.validate_failure(self.descriptor, self.terminal, self.build, self.command)

    def test_original_failed_identity_is_zero_credit(self):
        self.check()
        self.assertEqual(self.terminal["actual_test_methods"], 0)

    def test_relabelled_pass_or_ui_credit_is_refused(self):
        for field, value in (("status", "PASS"), ("actual_test_methods", 5)):
            with self.subTest(field=field):
                old = self.terminal[field]; self.terminal[field] = value
                with self.assertRaises(RuntimeError): self.check()
                self.terminal[field] = old

    def test_foreign_source_configuration_run_or_github_identity_is_refused(self):
        for field, value in (("source_sha", "other"), ("configuration", "Debug-Anytype"),
                             ("source_root", "/foreign"), ("github_run_id", "invented")):
            with self.subTest(field=field):
                old = self.descriptor[field]; self.descriptor[field] = value
                with self.assertRaises(RuntimeError): self.check()
                self.descriptor[field] = old
        self.terminal["run_id"] = "other"
        with self.assertRaises(RuntimeError): self.check()

    def test_success_timeout_or_undrained_command_is_refused(self):
        for field, value in (("returncode", 0), ("timed_out", True), ("owned_group_drained", False)):
            with self.subTest(field=field):
                old = self.command[field]; self.command[field] = value
                with self.assertRaises(RuntimeError): self.check()
                self.command[field] = old

    def test_changed_command_or_complete_log_is_refused(self):
        for field, value in (("arguments", ["different"]), ("log_sha256", "different")):
            with self.subTest(field=field):
                old = self.command[field]; self.command[field] = value
                with self.assertRaises(RuntimeError): self.check()
                self.command[field] = old

    def test_live_owned_group_is_refused_without_signalling(self):
        with patch.object(failed.os, "killpg", return_value=None) as observe:
            with self.assertRaisesRegex(RuntimeError, "still present"):
                failed.require_group_absent(12345)
            observe.assert_called_once_with(12345, 0)

    def test_absent_owned_group_is_admitted(self):
        with patch.object(failed.os, "killpg", side_effect=ProcessLookupError):
            failed.require_group_absent(12345)

    def test_altered_receipt_bytes_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "original.json"
            path.write_text('{"status":"FAIL"}\n')
            actual = failed.digest(path)
            path.write_text('{"status":"PASS"}\n')
            with self.assertRaises(RuntimeError):
                failed.completed.exact_json(path, actual)

    def test_foreign_failed_cache_root_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeError):
                failed.admit(failed.APP, Path(temporary), Path(temporary), None, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
