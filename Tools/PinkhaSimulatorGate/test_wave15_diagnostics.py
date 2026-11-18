import contextlib
import copy
import io
import json
import unittest
from unittest import mock

import wave15_diagnostics as diagnostics


SECRET = "PRIVATE_PAYLOAD /private/account/notes\n::error::injected%0Asecret@example.invalid"


def selection():
    return {"status": "FAIL", "phase": "EXECUTION", "selected": ["Fixture/testOne", "Fixture/testTwo"],
            "command_exit_code": 65, "error_type": "CalledProcessError", "error": SECRET,
            "passed": 1, "failed": 1, "skipped": 0,
            "actual_methods": {"Fixture/testTwo()": "Passed", "Fixture/testOne()": "Failed"}}


def summary():
    return {"totalTestCount": 2, "passedTests": 1, "failedTests": 1, "skippedTests": 0,
            "environmentDescription": SECRET, "testFailures": [{
                "testIdentifierString": "Fixture/testOne()", "targetName": SECRET,
                "failureText": "Expectation failed: textView.text == line\n" + SECRET}]}


class Wave15DiagnosticsTests(unittest.TestCase):
    def assertSafe(self, value):
        encoded = json.dumps(value)
        for text in ("PRIVATE_PAYLOAD", "/private/", "secret@example", "::error", "Fixture/", "textView"):
            self.assertNotIn(text, encoded)

    def test_selection_preserves_numeric_facts_without_private_values(self):
        result, raw = selection(), summary()
        before = copy.deepcopy((result, raw))
        value = diagnostics.selection_observation(result, raw)
        self.assertEqual(value["reported_status"], "FAIL")
        self.assertEqual(value["command_exit_code"], 65)
        self.assertEqual(value["error_category"], "COMMAND_EXIT")
        self.assertEqual(value["reported_counts"], {"passed": 1, "failed": 1, "skipped": 0})
        self.assertEqual(value["summary_counts"], {"total": 2, "passed": 1, "failed": 1, "skipped": 0})
        self.assertEqual(value["selector_results"], [
            {"selector_index": 0, "result": "Failed"}, {"selector_index": 1, "result": "Passed"}])
        self.assertEqual(value["failures"], [{"selector_index": 0, "category": "TEXT_ECHO"}])
        self.assertEqual((result, raw), before)
        self.assertTrue(value["diagnostic_only"])
        self.assertSafe(value)

    def test_failure_categories_use_known_prefixes_not_embedded_document_text(self):
        examples = {
            "Expectation failed: textView.text == line\n" + SECRET: "TEXT_ECHO",
            "Expectation failed: textView.selectedRange == NSRange(location: 0, length: 0)": "CARET",
            "Expectation failed: emptyCaret.midX > textView.bounds.midX": "CARET",
            "Expectation failed: document.infoContainer.recursiveChildren(of: objectId).filter { value }.count == 1": "NATIVE_PERSISTENCE",
            "Expectation failed: !acceptedReturn": "RETURN",
            "Issue recorded: The real editor did not focus a distinct empty block; phase=return-after-line-1 " + SECRET: "RETURN",
            "Expectation failed: textView.window != nil && textView.window === controller.view.window": "WINDOW",
            "Expectation failed: responders.count == 1 && responders.first === textView": "FOCUS",
            "Expectation failed: controller.firstResponderView === textView": "FOCUS",
            "Expectation failed: !UITextView().isFirstResponder": "FOCUS",
            "Expectation failed: inputReady": "FOCUS",
            "Caught error: .missingFocusedBlock": "FOCUS",
            "Test exceeded execution time allowance of 5 minutes": "TIMEOUT",
            "Test exceeded maximum execution time allowance of 300 seconds": "TIMEOUT",
            "Test timed out after 300 seconds": "TIMEOUT",
            "Expectation failed: unrelated == value\n" + SECRET: "ASSERTION",
            "XCTAssertTrue failed - " + SECRET: "ASSERTION",
            SECRET + " Expectation failed: textView.text == line": "UNCLASSIFIED",
        }
        for text, category in examples.items():
            with self.subTest(category=category):
                raw = summary()
                raw["testFailures"][0]["failureText"] = text
                value = diagnostics.selection_observation(selection(), raw)
                self.assertEqual(value["failures"][0]["category"], category)
                self.assertSafe(value)

    def test_unknown_failed_selector_never_becomes_selected_index(self):
        result, raw = selection(), summary()
        result["actual_methods"][SECRET] = "Failed"
        raw["testFailures"][0]["testIdentifierString"] = SECRET
        value = diagnostics.selection_observation(result, raw)
        self.assertEqual(value["unexpected_method_count"], 1)
        self.assertEqual(value["failures"][0]["selector_index"], diagnostics.NOT_RECORDED)
        self.assertSafe(value)

    def test_duplicate_normalized_actual_method_is_not_reported_passed(self):
        result = selection()
        result["actual_methods"] = {"Fixture/testOne": "Passed", "Fixture/testOne()": "Passed"}
        value = diagnostics.selection_observation(result)
        self.assertEqual(value["selector_results"][0]["result"], diagnostics.NOT_RECORDED)
        self.assertEqual(value["unexpected_method_count"], 1)

    def test_invalid_or_missing_selection_does_not_invent_zero_executions(self):
        for selected in (None, [], ["Fixture/testOne", "Fixture/testOne()"], [SECRET], ["testOne"], [True]):
            with self.subTest(selected_type=type(selected).__name__):
                result = selection()
                result["selected"] = selected
                value = diagnostics.selection_observation(result)
                self.assertEqual(value["expected_count"], diagnostics.NOT_RECORDED)
                self.assertEqual(value["selector_results"], [])
                self.assertEqual(value["summary_counts"]["total"], diagnostics.NOT_RECORDED)
                self.assertSafe(value)

    def test_counts_exit_and_boolean_fields_are_exact_bounded_types(self):
        for invalid in (True, False, -1, 10001, 1.0, "1", None, [], {}):
            with self.subTest(value_type=type(invalid).__name__):
                result = selection()
                result["passed"] = invalid
                self.assertEqual(diagnostics.selection_observation(result)["reported_counts"]["passed"], diagnostics.NOT_RECORDED)
        for invalid in (True, 256, -256, 0.0, "65"):
            result = selection()
            result["command_exit_code"] = invalid
            self.assertEqual(diagnostics.selection_observation(result)["command_exit_code"], diagnostics.NOT_RECORDED)
        self.assertEqual(diagnostics.execution_observation({"native_build_succeeded": 1}, "editor")["native_build_succeeded"], diagnostics.NOT_RECORDED)

    def test_unknown_records_and_custom_objects_are_not_stringified(self):
        class Poison:
            def __str__(self):
                raise AssertionError("must never stringify input")
            __repr__ = __str__
        for value in (None, [], "unknown", 7, Poison()):
            self.assertSafe(diagnostics.selection_observation(value, value))
            self.assertSafe(diagnostics.execution_observation(value, value))
        result = selection()
        result.update(status=Poison(), phase=Poison(), error_type=Poison(), command_exit_code=Poison())
        self.assertSafe(diagnostics.selection_observation(result))

    def test_unknown_error_type_is_unclassified_without_message_inspection(self):
        result = selection()
        result.update(error_type=SECRET, error="TimeoutExpired " + SECRET)
        value = diagnostics.selection_observation(result)
        self.assertEqual(value["error_category"], "UNCLASSIFIED")
        self.assertSafe(value)
        for error_type, expected in (("TimeoutExpired", "TIMEOUT"), ("KeyboardInterrupt", "CANCELLATION"),
                                     ("TrackedSourceChanged", "SOURCE_IDENTITY"),
                                     ("SelectionFailure", "NAMED_XCTEST_FAILED")):
            result["error_type"] = error_type
            self.assertEqual(diagnostics.selection_observation(result)["error_category"], expected)
        read_failure = diagnostics.execution_observation({"status": "DIAGNOSTIC_READ_FAILED"}, "editor")
        self.assertEqual(read_failure["reported_status"], "DIAGNOSTIC_READ_FAILED")

    def test_batch_source_change_keeps_only_fixed_stage_and_count(self):
        receipt = {"status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "phase": "SHARED_INPUTS_BEFORE_LANE",
            "current_lane": "properties", "error_type": "TrackedSourceChanged", "error": SECRET,
            "tracked_source_change": {"stage": "AFTER_UI_RUNNER_BUILD", "changed_path_count": 3,
                "porcelain_observation": SECRET, "changes": [{"path": SECRET, "head_tree_entry": SECRET}]},
            "lane_statuses": {"inspector": "LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "properties": "NOT_COMPLETED_SETUP_OR_IDENTITY", SECRET: SECRET}}
        before = copy.deepcopy(receipt)
        value = diagnostics.execution_observation(receipt, "remaining-release")
        self.assertEqual(value["reported_status"], "BATCH_ABORTED_SETUP_OR_IDENTITY")
        self.assertEqual(value["source_change_stage"], "AFTER_UI_RUNNER_BUILD")
        self.assertEqual(value["changed_path_count"], 3)
        self.assertIs(value["tracked_source_changed"], True)
        self.assertEqual(value["lane_statuses"][2], {"lane_index": 2, "reported_status": "NOT_COMPLETED_SETUP_OR_IDENTITY"})
        self.assertEqual(receipt, before)
        self.assertSafe(value)
        receipt["tracked_source_change"]["stage"] = SECRET
        value = diagnostics.execution_observation(receipt, SECRET)
        self.assertEqual(value["lane"], diagnostics.NOT_RECORDED)
        self.assertEqual(value["source_change_stage"], diagnostics.NOT_RECORDED)
        self.assertSafe(value)

    def test_nested_public_diagnostics_are_reprojected_and_detached(self):
        public = diagnostics.selection_observation(selection(), summary())
        public["secret"] = SECRET
        public["failures"][0]["private_detail"] = SECRET
        public["selector_results"][0]["method"] = SECRET
        public["reported_counts"]["private"] = SECRET
        receipt = {"status": "FAIL", "phase": "PREPARATION", "preparation": {"public_diagnostics": public}}
        value = diagnostics.execution_observation(receipt, "editor")
        self.assertEqual(value["preparation"]["failures"], [{"selector_index": 0, "category": "TEXT_ECHO"}])
        public["failures"][0]["category"] = SECRET
        self.assertEqual(value["preparation"]["failures"][0]["category"], "TEXT_ECHO")
        changed = diagnostics.execution_observation(receipt, "editor")
        self.assertEqual(changed["preparation"]["failures"][0]["category"], "UNCLASSIFIED")
        self.assertSafe(value)
        self.assertSafe(changed)

    def test_nested_unknown_schema_and_out_of_selection_indexes_are_not_trusted(self):
        for malformed in (None, {"schema": True, "kind": "SELECTION", "diagnostic_only": True},
                          {"schema": 1, "kind": SECRET, "diagnostic_only": True}):
            value = diagnostics.execution_observation({"ui": {"public_diagnostics": malformed}}, "editor")
            self.assertEqual(value["ui"], diagnostics.NOT_RECORDED)
        public = diagnostics.selection_observation(selection(), summary())
        public["selector_results"][0]["selector_index"] = 2
        public["failures"][0]["selector_index"] = -1
        value = diagnostics.execution_observation({"ui": {"public_diagnostics": public}}, "editor")
        self.assertEqual(value["ui"]["selector_results"][0]["selector_index"], diagnostics.NOT_RECORDED)
        self.assertEqual(value["ui"]["failures"][0]["selector_index"], diagnostics.NOT_RECORDED)

    def test_large_input_has_bounded_output_and_explicit_omission(self):
        raw = summary()
        raw["testFailures"] *= 1000
        value = diagnostics.selection_observation(selection(), raw)
        self.assertEqual(len(value["failures"]), diagnostics.MAX_FAILURES)
        self.assertEqual(value["omitted_failure_count"], 1000 - diagnostics.MAX_FAILURES)
        self.assertLess(len(json.dumps(value)), diagnostics.MAX_ANNOTATION)
        self.assertSafe(value)
        value["failures"] *= 2
        nested = diagnostics.execution_observation({"ui": {"public_diagnostics": value}}, "editor")
        self.assertEqual(len(nested["ui"]["failures"]), diagnostics.MAX_FAILURES)
        self.assertEqual(nested["ui"]["omitted_failure_count"], 1000)

    def test_emit_returns_saved_observation_and_one_filtered_annotation(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            value = diagnostics.emit_selection(selection(), summary())
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        self.assertTrue(out.getvalue().startswith("::warning title=Pinkha UI diagnostic::"))
        decoded = json.loads(out.getvalue().split("::", 2)[2])
        self.assertEqual(decoded, value)
        self.assertSafe(decoded)
        result = selection()
        result["status"] = "PASS"
        with contextlib.redirect_stdout(io.StringIO()) as passed:
            diagnostics.emit_selection(result)
        self.assertTrue(passed.getvalue().startswith("::notice "))
        self.assertEqual(result["failed"], 1)  # diagnostics never edits an inconsistent original result

    def test_emit_revalidates_a_poisoned_producer_before_output(self):
        value = diagnostics.selection_observation(selection(), summary())
        value.update(reported_status=SECRET, phase=SECRET, secret=SECRET)
        value["failures"][0]["category"] = SECRET
        with mock.patch.object(diagnostics, "selection_observation", return_value=value), contextlib.redirect_stdout(io.StringIO()) as out:
            returned = diagnostics.emit_selection({})
        self.assertSafe(returned)
        self.assertNotIn("PRIVATE_PAYLOAD", out.getvalue())
        self.assertEqual(returned["reported_status"], diagnostics.NOT_RECORDED)

    def test_execution_emit_revalidates_nested_receipts(self):
        receipt = {"status": "CANCELLED", "phase": "UI", "error_type": "KeyboardInterrupt",
                   "ui": {"public_diagnostics": diagnostics.selection_observation(selection(), summary())}}
        receipt["ui"]["public_diagnostics"]["private"] = SECRET
        with contextlib.redirect_stdout(io.StringIO()) as out:
            value = diagnostics.emit_execution(receipt, "editor")
        self.assertEqual(value["reported_status"], "CANCELLED")
        self.assertEqual(value["error_category"], "CANCELLATION")
        self.assertSafe(value)
        self.assertNotIn("PRIVATE_PAYLOAD", out.getvalue())

    def test_execution_emitter_filters_a_poisoned_producer_without_calling_it_again(self):
        value = diagnostics.execution_observation({"status": "FAIL", "phase": "BUILD"}, "editor")
        value.update(lane=SECRET, reported_status=SECRET, phase=SECRET, private=SECRET)
        value["lane_statuses"][0]["reported_status"] = SECRET
        with mock.patch.object(diagnostics, "execution_observation", return_value=value) as producer, contextlib.redirect_stdout(io.StringIO()) as out:
            returned = diagnostics.emit_execution({}, "editor")
        self.assertEqual(producer.call_count, 1)
        self.assertSafe(returned)
        self.assertNotIn("PRIVATE_PAYLOAD", out.getvalue())

    def test_diagnostic_failure_never_masks_original_failure_or_changes_input(self):
        class BrokenOutput:
            def write(self, value):
                raise OSError("private output error")
            def flush(self):
                raise OSError("private flush error")
        result = selection()
        before = copy.deepcopy(result)
        original = RuntimeError("original acceptance error")
        with self.assertRaises(RuntimeError) as caught:
            try:
                raise original
            finally:
                with contextlib.redirect_stdout(BrokenOutput()):
                    self.assertIsNone(diagnostics.emit_selection(result, summary()))
        self.assertIs(caught.exception, original)
        self.assertEqual(result, before)
        with mock.patch.object(diagnostics, "execution_observation", side_effect=ValueError(SECRET)):
            self.assertIsNone(diagnostics.emit_execution({}, "editor"))

    def test_interruption_is_not_swallowed_or_converted_to_success(self):
        for error in (KeyboardInterrupt(), SystemExit(17)):
            with self.subTest(kind=type(error).__name__):
                with mock.patch.object(diagnostics, "selection_observation", side_effect=error):
                    with self.assertRaises(type(error)) as caught:
                        diagnostics.emit_selection(selection())
                self.assertIs(caught.exception, error)


if __name__ == "__main__":
    unittest.main()
