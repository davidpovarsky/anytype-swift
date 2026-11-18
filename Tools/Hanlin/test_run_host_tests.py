"""Synthetic adversarial controls for the SDK CI gate, never native acceptance."""
import copy
import unittest

from run_host_tests import BRANCH, SUITES, require_identity, validate_results


class SDKResultGateTests(unittest.TestCase):
    def setUp(self):
        self.expected = {suite + "/actualMethod" for suite in SUITES}
        self.summary = dict(totalTestCount=4, passedTests=4, failedTests=0, skippedTests=0,
                            devicesAndConfigurations=[dict(device=dict(deviceId="disposable-id", osVersion="27.0",
                            osBuildNumber="24A-test", architecture="arm64", modelName="iPad (A16)"))])
        self.tree = dict(children=[dict(nodeType="Test Case", nodeIdentifier=name + "()", result="Passed")
                                   for name in sorted(self.expected)])

    def validate(self):
        return validate_results(self.summary, self.tree, self.expected, "disposable-id")

    def test_all_four_suites_pass_with_actual_method_identity(self):
        self.assertEqual(set(self.validate()["methods"]), self.expected)

    def test_zero_counts_cannot_pass_even_with_named_tree(self):
        self.summary.update(totalTestCount=0, passedTests=0)
        with self.assertRaisesRegex(ValueError, "Zero or incomplete"):
            self.validate()

    def test_missing_suite_cannot_hide_in_successful_summary(self):
        self.tree["children"].pop()
        with self.assertRaisesRegex(ValueError, "Missing SDK test methods"):
            self.validate()

    def test_unrelated_success_does_not_substitute_for_sdk_test(self):
        self.tree["children"][0]["nodeIdentifier"] = "Unrelated/testPassed()"
        with self.assertRaisesRegex(ValueError, "outside the four"):
            self.validate()

    def test_false_or_missing_or_skipped_results_are_rejected(self):
        for status in ("Failed", "Skipped", None):
            with self.subTest(status=status):
                self.tree["children"][0]["result"] = status
                with self.assertRaisesRegex(ValueError, "nonpassing"):
                    self.validate()

    def test_summary_failure_or_skip_cannot_be_hidden_by_passing_methods(self):
        for field in ("failedTests", "skippedTests"):
            with self.subTest(field=field):
                self.summary[field] = 1
                with self.assertRaisesRegex(ValueError, "Failed or skipped"):
                    self.validate()
                self.summary[field] = 0

    def test_missing_raw_device_os_or_architecture_fails(self):
        original = copy.deepcopy(self.summary["devicesAndConfigurations"][0]["device"])
        for field, value in (("deviceId", "different"), ("osVersion", "26.2"), ("architecture", "x86_64"),
                             ("osBuildNumber", ""), ("modelName", "iPhone 17")):
            with self.subTest(field=field):
                device = copy.deepcopy(original)
                device[field] = value
                self.summary["devicesAndConfigurations"][0]["device"] = device
                with self.assertRaisesRegex(ValueError, "Raw xcresult device"):
                    self.validate()

    def test_boolean_counts_are_not_real_test_counts(self):
        self.summary["failedTests"] = False
        with self.assertRaisesRegex(ValueError, "integer xcresult"):
            self.validate()

    def test_duplicate_identifiers_are_not_counted_twice(self):
        self.tree["children"].append(copy.deepcopy(self.tree["children"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.validate()

    def test_parameter_cases_can_cover_one_declaration_with_actual_passes(self):
        node = self.tree["children"][0]
        second = copy.deepcopy(node)
        second["nodeIdentifier"] = "AnytypeTests/" + node["nodeIdentifier"] + "/argument-2"
        self.tree["children"].append(second)
        self.summary.update(totalTestCount=5, passedTests=5)
        self.assertEqual(set(self.validate()["methods"]), self.expected)

    def test_wrong_source_or_branch_or_missing_run_is_rejected(self):
        valid = ["a" * 40, "a" * 40, BRANCH, BRANCH, "123", "1"]
        require_identity(*valid)
        for index, replacement in ((0, "b" * 40), (1, ""), (2, "develop"),
                                   (3, "codex/chatgpt-wave15-sdk06-20261118"), (4, ""), (5, "0")):
            with self.subTest(index=index):
                values = valid.copy()
                values[index] = replacement
                with self.assertRaises(ValueError):
                    require_identity(*values)


if __name__ == "__main__":
    unittest.main()
