"""Adversarial controls for the focused shared-editor gate; not Apple execution."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_host_tests as host
import shared_editor_profile as shared

# Independent reviewed inventory: changing the production registry must not
# silently lower the expected method or argument scope.
PLAIN = {
    "sameInputOwnerSurvivesForkAndExplicitReplacementEndsComposition",
    "pendingLocalTextSurvivesNativeReconfiguration",
    "completedLocalTextAcceptsRemoteReplacement",
    "initialFocusWaitsForAttachment",
    "explicitHandoffDoesNotReplayInitialCaret",
    "requestIdentityParticipatesInCellConfigurationEquality",
}
PARAMETERS = {
    "reusedCellDoesNotPreserveDifferentPendingOwner": ("composing", "Bool", [False, True]),
    "staleFocusDoesNotSurviveRowLifetime": ("change", "String", ["rebind", "detach", "editorContext"]),
    "reusedCellUsesCurrentLockBeforeFocus": ("newLocked", "Bool", [False, True]),
    "insertedCellUsesCurrentEditingBeforeFocus": ("editing", "Bool", [False, True]),
}
SUITE = "TextBlockFocusLifecycleTests"
NAMES = PLAIN | set(PARAMETERS)
EXPECTED = {SUITE + "/" + name for name in NAMES}
PROFILE = host.HostTestProfile.SHARED_EDITOR
UDID = "owned-disposable-ipad"

def source():
    declarations = ["@Test func " + name + "() {}" for name in sorted(PLAIN)]
    for name, (parameter, kind, values) in PARAMETERS.items():
        declarations.append('@Test("reviewed", arguments: ' + json.dumps(values) + ")\n"
                            + "func " + name + "(" + parameter + ": " + kind + ") {}")
    # Existing suite methods are not implicitly selected by the focused profile.
    declarations.extend("@Test func unselectedExistingMethod" + str(i) + "() {}" for i in range(5))
    return "\n".join(declarations)

def tree():
    children = []
    for name in sorted(NAMES):
        parameters = PARAMETERS.get(name)
        signature = parameters[0] + ":" if parameters else ""
        node = dict(nodeType="Test Case", nodeIdentifier="AnytypeTests/" + SUITE + "/" + name + "(" + signature + ")",
                    result="Passed")
        if parameters:
            node["children"] = [
                dict(nodeType="Arguments", name=json.dumps(value), result="Passed")
                for value in parameters[2]
            ]
        children.append(node)
    return dict(children=children)

def summary(count=10):
    return dict(totalTestCount=count, passedTests=count, failedTests=0, skippedTests=0,
                devicesAndConfigurations=[dict(device=dict(deviceId=UDID, osVersion="27.0",
                    osBuildNumber="24A-test", architecture="arm64", modelName="iPad (A16)"))])

def validate(report=None, results=None):
    return host.validate_results(summary() if report is None else report,
                                 tree() if results is None else results,
                                 EXPECTED, UDID, PROFILE)

class SharedEditorProfileTests(unittest.TestCase):
    def test_reviewed_scope_is_exactly_ten_methods_and_fifteen_invocations(self):
        self.assertEqual(set(shared.METHODS), NAMES)
        self.assertEqual(PROFILE.suites, {SUITE: 10})
        self.assertEqual(shared.validate_source(source()), NAMES)
        self.assertEqual(sum(value["case_count"] for value in shared.METHODS.values()), 15)

    def test_source_substitution_cannot_preserve_count_and_hide_missing_selected_method(self):
        for name in sorted(NAMES):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "named declarations"):
                shared.validate_source(source().replace("func " + name + "(", "func substitutedMethod(", 1))

    def test_source_argument_substitution_or_type_change_is_rejected(self):
        substitutions = [
            ('"editorContext"', '"otherContext"'),
            ('[false, true]', '[false]'),
            ('newLocked: Bool', 'newLocked: Int'),
        ]
        for before, after in substitutions:
            with self.subTest(before=before), self.assertRaises(ValueError):
                shared.validate_source(source().replace(before, after, 1))

    def test_duplicate_selected_source_declaration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            shared.validate_source(source() + "\n@Test func initialFocusWaitsForAttachment() {}")

    def test_tracked_source_selection_excludes_existing_unselected_methods(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            relative = "AnytypeTests/Pinkha/" + SUITE + ".swift"
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(source(), encoding="utf-8")
            with patch.object(subprocess, "check_output", return_value=(relative + "\0").encode()):
                actual, hashes = host.expected_methods(root, PROFILE)
            self.assertEqual(actual, EXPECTED)
            self.assertEqual(set(hashes), {relative})

    def test_real_tracked_swift_declarations_match_selected_contract(self):
        root = Path(__file__).resolve().parents[2]
        actual, hashes = host.expected_methods(root, PROFILE)
        self.assertEqual(actual, EXPECTED)
        self.assertEqual(len(hashes), 1)

    def test_method_or_invocation_summary_counts_both_require_actual_fifteen_cases(self):
        for count in (10, 15):
            with self.subTest(count=count):
                result = validate(summary(count))
                self.assertEqual(result["actual_method_count"], 10)
                self.assertEqual(result["declared_case_count"], 15)
                self.assertEqual(sum(map(len, result["core_cases"].values())), 15)

    def test_missing_method_fails_even_with_all_passing_summary(self):
        results = tree()
        results["children"].pop()
        with self.assertRaisesRegex(ValueError, "Missing SDK test methods"):
            validate(results=results)

    def test_extra_unselected_method_cannot_expand_focused_execution(self):
        results = tree()
        results["children"].append(dict(nodeType="Test Case",
            nodeIdentifier=SUITE + "/unselectedExistingMethod0()", result="Passed"))
        with self.assertRaisesRegex(ValueError, "Unexpected xcresult"):
            validate(results=results)

    def test_missing_or_duplicate_argument_case_cannot_hide_behind_method_pass(self):
        for mutation in ("missing", "duplicate"):
            results = tree()
            node = next(item for item in results["children"] if item.get("children"))
            if mutation == "missing":
                node["children"].pop()
            else:
                node["children"][-1]["name"] = node["children"][0]["name"]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "Missing or duplicate"):
                validate(results=results)

    def test_nonpassing_argument_or_method_is_rejected(self):
        for status in ("Failed", "Skipped", None):
            for level in ("method", "argument"):
                results = tree()
                node = next(item for item in results["children"] if item.get("children"))
                if level == "argument":
                    node = node["children"][0]
                node["result"] = status
                with self.subTest(status=status, level=level), self.assertRaises(ValueError):
                    validate(results=results)

    def test_failed_skipped_boolean_or_unreviewed_summary_counts_are_rejected(self):
        reports = [
            dict(failedTests=1),
            dict(skippedTests=1),
            dict(failedTests=False),
            dict(totalTestCount=9, passedTests=9),
            dict(totalTestCount=0, passedTests=0),
        ]
        for changes in reports:
            report = summary()
            report.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate(report)

    def test_wrong_destination_or_multiple_destinations_are_rejected(self):
        for field, value in [
            ("deviceId", "other-run"), ("osVersion", "26.9"),
            ("architecture", "x86_64"), ("osBuildNumber", ""), ("modelName", "iPhone 17"),
        ]:
            report = summary()
            report["devicesAndConfigurations"][0]["device"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Raw xcresult device"):
                validate(report)
        report = summary()
        report["devicesAndConfigurations"].append(copy.deepcopy(report["devicesAndConfigurations"][0]))
        with self.assertRaisesRegex(ValueError, "one actual test destination"):
            validate(report)

    def test_unrecognized_argument_schema_is_review_pending_not_pass(self):
        results = tree()
        node = next(item for item in results["children"] if item.get("children"))
        node["children"][0]["nodeType"] = "Unknown Future Result"
        with self.assertRaisesRegex(ValueError, "Unknown core case schema"):
            validate(results=results)

if __name__ == "__main__":
    unittest.main()
