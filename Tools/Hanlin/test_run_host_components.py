"""Reject borrowed success across the three real host component scopes.

These are controller controls with deliberately synthetic xcresult fixtures.
They do not execute or claim Apple/SDK/editor acceptance.
"""
from copy import deepcopy
import unittest

import run_host_tests as host
import test_run_host_tests as existing
import test_run_host_core_profile as existing_core


class CombinedComponentGateTests(unittest.TestCase):
    def setUp(self):
        self.sdk = existing.SDKResultGateTests()
        self.sdk.setUp()
        self.sdk.expected.add(host.SDK_BUDGET_METHOD)
        self.sdk.tree["children"].append(dict(nodeType="Test Case",
            nodeIdentifier=host.SDK_BUDGET_METHOD + "(budget:)", result="Passed",
            children=[dict(nodeType="Arguments", name=value, result="Passed") for value in ("1048576", "8388608")]))
        self.editor = existing.EditorResultGateTests()
        self.editor.setUp()
        self.core = existing_core.CoreScopeGateTests()
        self.core.setUp()
        self.expected = self.sdk.expected | self.editor.expected | self.core.expected
        self.summary = deepcopy(self.sdk.summary)
        self.summary.update(totalTestCount=len(self.expected), passedTests=len(self.expected))
        self.tree = [self.sdk.tree, self.editor.tree, self.core.tree]

    def validate(self):
        return host.validate_results(self.summary, self.tree, self.expected,
                                     "disposable-id", host.HostTestProfile.COMPONENTS)

    def nodes(self, value=None):
        value = self.tree if value is None else value
        if isinstance(value, dict):
            result = [value] if value.get("nodeType") == "Test Case" else []
            for child in value.values():
                result.extend(self.nodes(child))
            return result
        if isinstance(value, list):
            return [node for child in value for node in self.nodes(child)]
        return []

    def test_original_nodes_and_summary_are_preserved_with_separate_argument_evidence(self):
        original_tree, original_summary = deepcopy(self.tree), deepcopy(self.summary)
        actual = self.validate()
        self.assertEqual(self.tree, original_tree)
        self.assertEqual(self.summary, original_summary)
        self.assertEqual(actual["counts"]["totalTestCount"], len(self.expected))
        self.assertEqual(set(actual["components"]), {"sdk06", "editor", "wave15-core"})
        self.assertEqual(actual["components"]["sdk06"]["actual_method_count"], 5)
        self.assertEqual(actual["components"]["editor"]["actual_method_count"], 10)
        self.assertEqual(actual["components"]["editor"]["declared_case_count"], 12)
        self.assertEqual(actual["components"]["wave15-core"]["actual_method_count"], 52)
        self.assertEqual(actual["components"]["wave15-core"]["declared_case_count"], 73)
        self.assertEqual(host.HostTestProfile.COMPONENTS.pass_status, "WAVE15_ALL_COMPONENTS_PASS")
        self.assertEqual(len(host.HostTestProfile.COMPONENTS.suites), 11)

    def test_other_components_cannot_replace_a_missing_entire_component(self):
        original = deepcopy(self.tree)
        for index in range(3):
            with self.subTest(component=index):
                self.tree = deepcopy(original)
                self.tree.pop(index)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_successful_aggregate_cannot_hide_a_failed_or_skipped_method(self):
        original = deepcopy(self.tree)
        prefixes = ("HanlinHost", "TorahQuoteInsertionTests/", "PinkhaTextDirection")
        for prefix in prefixes:
            for status in ("Failed", "Skipped", None):
                with self.subTest(prefix=prefix, result=status):
                    self.tree = deepcopy(original)
                    node = next(node for node in self.nodes() if node["nodeIdentifier"].startswith(prefix))
                    node["result"] = status
                    with self.assertRaises(ValueError):
                        self.validate()

    def test_editor_and_core_argument_contracts_still_reject_all_corruptions(self):
        original = deepcopy(self.tree)
        for is_editor in (True, False):
            for mutation in ("missing", "duplicate", "failed", "skipped", "failed-run"):
                with self.subTest(editor=is_editor, mutation=mutation):
                    self.tree = deepcopy(original)
                    node = next(node for node in self.nodes()
                                if node.get("children") and not node["nodeIdentifier"].startswith("Hanlin") and
                                node["nodeIdentifier"].startswith("TorahQuoteInsertionTests/") == is_editor)
                    args = node["children"]
                    if mutation == "missing":
                        args.pop()
                    elif mutation == "duplicate":
                        args[1]["name"] = args[0]["name"]
                    elif mutation == "failed-run":
                        args[0]["children"] = [dict(nodeType="Test Case Run", result="Failed")]
                    else:
                        args[0]["result"] = "Failed" if mutation == "failed" else "Skipped"
                    with self.assertRaises(ValueError):
                        self.validate()

    def test_alias_duplicate_cannot_inflate_a_component_without_raw_duplicate_identifier(self):
        duplicate = deepcopy(self.sdk.tree["children"][0])
        duplicate["nodeIdentifier"] = "AnytypeTests/" + duplicate["nodeIdentifier"]
        self.tree.append(duplicate)
        self.summary["totalTestCount"] += 1
        self.summary["passedTests"] += 1
        with self.assertRaisesRegex(ValueError, "duplicate actual terminals"):
            self.validate()

    def test_foreign_method_and_wrong_editor_signature_are_rejected(self):
        original = deepcopy(self.tree)
        for identity in ("UnrelatedTests/claimedSuccess()", "TorahQuoteInsertionTests/staleInspectorInsertionIsRejected(other:)"):
            with self.subTest(identity=identity):
                self.tree = deepcopy(original)
                node = next(node for node in self.nodes()
                            if node["nodeIdentifier"] == "TorahQuoteInsertionTests/staleInspectorInsertionIsRejected(dismiss:)")
                node["nodeIdentifier"] = identity
                with self.assertRaises(ValueError):
                    self.validate()

    def test_unknown_argument_schema_remains_review_pending(self):
        original = deepcopy(self.tree)
        for is_editor in (True, False):
            with self.subTest(editor=is_editor):
                self.tree = deepcopy(original)
                node = next(node for node in self.nodes()
                            if node.get("children") and not node["nodeIdentifier"].startswith("Hanlin") and
                            node["nodeIdentifier"].startswith("TorahQuoteInsertionTests/") == is_editor)
                node["children"][0]["nodeType"] = "UnrecognizedResult"
                expected = host.EditorEvidenceReviewPending if is_editor else host.core_profile.CoreEvidenceReviewPending
                with self.assertRaises(expected):
                    self.validate()


    def test_aggregate_can_only_describe_actual_methods_or_all_source_bound_cases(self):
        for total in (len(self.expected), len(self.expected) + 24):
            self.summary.update(totalTestCount=total, passedTests=total)
            actual = self.validate()
            self.assertEqual(actual["declared_case_count"], len(self.expected) + 24)
        for total in (len(self.expected) + 1, len(self.expected) + 23, 999):
            with self.subTest(total=total):
                self.summary.update(totalTestCount=total, passedTests=total)
                with self.assertRaisesRegex(ValueError, "Combined summary differs"):
                    self.validate()

    def test_sdk_budget_source_and_actual_arguments_cannot_change_under_passing_total(self):
        source = "@Test(arguments: [1_048_576, 8 * 1_048_576])\nfunc canonicalDispatcherBudgetsReachReadAndReplayOnlyReceipt(budget: Int) throws {}\n"
        host.validate_sdk_declarations(source, "HanlinSDKConsumerTests")
        for bad in (source.replace("8 *", "9 *"), source.replace("budget: Int", "size: Int"),
                    source + "@Test(arguments: [false, true])\nfunc unexpected(flag: Bool) {}\n"):
            with self.subTest(source=bad), self.assertRaises(ValueError):
                host.validate_sdk_declarations(bad, "HanlinSDKConsumerTests")
        original = deepcopy(self.tree)
        for mutation in ("missing", "duplicate", "wrong-value", "skipped", "unknown", "wrong-signature", "extra-other-method"):
            with self.subTest(mutation=mutation):
                self.tree = deepcopy(original)
                node = next(node for node in self.nodes() if node["nodeIdentifier"].startswith(host.SDK_BUDGET_METHOD))
                args = node["children"]
                if mutation == "missing":
                    args.pop()
                elif mutation == "duplicate":
                    args[1]["name"] = args[0]["name"]
                elif mutation == "wrong-value":
                    args[1]["name"] = "9437184"
                elif mutation == "skipped":
                    args[0]["result"] = "Skipped"
                elif mutation == "unknown":
                    args[0]["nodeType"] = "UnrecognizedResult"
                elif mutation == "wrong-signature":
                    node["nodeIdentifier"] = host.SDK_BUDGET_METHOD + "(other:)"
                else:
                    other = next(node for node in self.nodes() if node["nodeIdentifier"].startswith("HanlinHostAdapterTests/"))
                    other["children"] = deepcopy(args)
                with self.assertRaises(ValueError):
                    self.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
