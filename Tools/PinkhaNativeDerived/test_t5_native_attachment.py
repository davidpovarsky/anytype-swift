"""Reject incomplete native runs and unrelated failures in the counterexample."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_t5_native_attachment as gate


class NativeEvidenceControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.log = Path(self.directory.name) / "go-test.log"

    def events(self, negative=False):
        events = []
        for test in sorted(gate.NEGATIVE_CASES | {gate.BASIC_TEST}):
            events.append({"Action": "run", "Package": gate.BASIC_PACKAGE, "Test": test})
            if negative and test in gate.NEGATIVE_CASES:
                reason = ("an ordinary edit must preserve the existing attachment decision" if test.endswith("/unattached")
                          else "projected topics must not create an attachment")
                events.append({"Action": "output", "Package": gate.BASIC_PACKAGE, "Test": test, "Output": reason})
            events.append({"Action": "fail" if negative else "pass", "Package": gate.BASIC_PACKAGE, "Test": test})
        events.append({"Action": "fail" if negative else "pass", "Package": gate.BASIC_PACKAGE})
        if not negative:
            for test in (gate.EXPLICIT_TEST, "TestExistingNativeRegression"):
                events.extend([{"Action": action, "Package": gate.EXPLICIT_PACKAGE, "Test": test} for action in ("run", "pass")])
            events.append({"Action": "pass", "Package": gate.EXPLICIT_PACKAGE})
        return events

    def qualify(self, events, *, negative=False, exit_code=None):
        self.log.write_text("\n".join(json.dumps(e) for e in events) + "\n")
        return gate.qualify_log(self.log, int(negative) if exit_code is None else exit_code, negative=negative)

    def test_two_real_packages_and_all_new_cases_are_required(self):
        result = self.qualify(self.events())
        self.assertEqual(result["status"], "PASS_ACTUAL_NATIVE_PACKAGES")
        self.assertEqual(len(result["tests"]), 7)
        self.assertEqual(result["log_sha256"], gate.digest(self.log))

    def test_original_source_control_requires_all_four_exact_failures(self):
        result = self.qualify(self.events(True), negative=True)
        self.assertEqual(result["status"], "PASS_EXPECTED_ORIGINAL_SOURCE_FAILURE")
        self.assertEqual(len(result["tests"]), 5)

    def test_compile_error_is_not_a_native_counterexample(self):
        self.log.write_text("# compilation failed\nundefined: bad fixture\n")
        with self.assertRaisesRegex(RuntimeError, "inventory"):
            gate.qualify_log(self.log, 1, negative=True)

    def test_zero_selected_tests_cannot_pass(self):
        with self.assertRaises(RuntimeError):
            self.qualify([{"Action": "pass", "Package": gate.BASIC_PACKAGE}])

    def test_missing_or_duplicate_terminal_is_rejected(self):
        events = self.events()
        terminal = next(e for e in events if e.get("Action") == "pass" and e.get("Test"))
        for candidate in ([e for e in events if e is not terminal], events + [terminal]):
            with self.subTest(candidate=candidate[-1]):
                with self.assertRaises(RuntimeError):
                    self.qualify(candidate)

    def test_duplicate_run_is_rejected(self):
        events = self.events()
        with self.assertRaises(RuntimeError):
            self.qualify(events + [events[0]])

    def test_a_skipped_original_or_new_test_is_not_a_pass(self):
        for selected in (gate.EXPLICIT_TEST, "TestExistingNativeRegression"):
            events = self.events()
            for event in events:
                if event.get("Test") == selected and event["Action"] == "pass":
                    event["Action"] = "skip"
            with self.subTest(selected=selected), self.assertRaises(RuntimeError):
                self.qualify(events)

    def test_unexpected_package_failure_is_not_hidden_by_fixture_success(self):
        events = self.events()
        events.append({"Action": "fail", "Package": "unexpected/package"})
        with self.assertRaises(RuntimeError):
            self.qualify(events)

    def test_wrong_process_exit_code_is_rejected(self):
        for negative, code in ((False, 1), (True, 0), (True, 2)):
            with self.subTest(negative=negative, code=code), self.assertRaises(RuntimeError):
                self.qualify(self.events(negative), negative=negative, exit_code=code)

    def test_only_some_counterexample_cases_failing_is_rejected(self):
        events = self.events(True)
        for event in events:
            if event.get("Test") == sorted(gate.NEGATIVE_CASES)[0] and event["Action"] == "fail":
                event["Action"] = "pass"
        with self.assertRaises(RuntimeError):
            self.qualify(events, negative=True)

    def test_unrelated_runtime_failure_is_not_the_expected_bug(self):
        events = self.events(True)
        for event in events:
            if event["Action"] == "output":
                event["Output"] = "panic: unrelated fixture failure"
                break
        with self.assertRaisesRegex(RuntimeError, "unrelated reason"):
            self.qualify(events, negative=True)

    def test_counterexample_case_names_cannot_be_substituted(self):
        events = self.events(True)
        selected = sorted(gate.NEGATIVE_CASES)[0]
        for event in events:
            if event.get("Test") == selected:
                event["Test"] = selected + "-substitute"
        with self.assertRaises(RuntimeError):
            self.qualify(events, negative=True)

    def test_scoped_original_patch_requires_one_exact_file(self):
        target = b"diff --git a/" + gate.DETAILS.encode() + b" b/" + gate.DETAILS.encode() + b"\n--- first\n"
        other = b"diff --git a/another.go b/another.go\n--- second\n"
        self.assertEqual(gate.scoped_patch(other + target + other, gate.DETAILS), target)
        for content in (other, target + target):
            with self.assertRaises(RuntimeError):
                gate.scoped_patch(content, gate.DETAILS)

    def test_failed_executed_native_stage_retains_actual_exit_and_is_not_not_run(self):
        self.log.write_text("native compile error\n")
        receipt = {"native_packages": "NOT_RUN"}
        actual = {"pid": 123, "exit_code": 1, "log_sha256": gate.digest(self.log)}
        with patch.object(gate, "run", return_value=actual), self.assertRaises(RuntimeError):
            gate.native_stage(receipt, "native_packages", ["go", "test"], self.log.parent,
                              self.log, {}, 30, negative=False)
        self.assertEqual(receipt["native_packages"]["status"], "FAIL")
        self.assertEqual(receipt["native_packages"]["exit_code"], 1)
        self.assertEqual(receipt["native_packages"]["pid"], 123)
        self.assertEqual(receipt["native_packages"]["log_sha256"], actual["log_sha256"])

    def test_timeout_remains_failure_and_cannot_leave_not_run_label(self):
        receipt = {"native_packages": "NOT_RUN"}
        with patch.object(gate, "run", side_effect=RuntimeError("finite deadline")), self.assertRaisesRegex(RuntimeError, "finite deadline"):
            gate.native_stage(receipt, "native_packages", ["go", "test"], self.log.parent,
                              self.log, {}, 30, negative=False)
        self.assertEqual(receipt["native_packages"]["status"], "FAIL")
        self.assertEqual(receipt["native_packages"]["error"], "finite deadline")


if __name__ == "__main__":
    unittest.main(verbosity=2)
