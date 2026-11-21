"""Focused controls for exact pending editor/table execution in the SDK06 build.

Synthetic enumerations/results below test the controller, never stand in for
actual Apple evidence or qualify product acceptance.
"""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import shared_editor_existing_build as runner
import test_shared_editor_profile as fixtures
import text_native_ack

TABLE_PLAIN = {
    "acceptedSnapshotSurvivesViewReuse", "laterDraftKeepsTheLatestAcceptedSnapshot",
    "nativeRejectionKeepsTheTableDirty", "defocusCommitsTheDeferredSearchBuffer",
    "rowRebindCannotWriteIntoTheNewOwner", "structuralKeyWaitsForAcceptedText",
    "markdownStyleWaitsForEarlierNativeWrite", "queuedMarkdownCommandIsRetiredWhenRowChanges",
}
TABLE_PARAMETERS = {
    "replacementClaimsPendingOwnershipBeforePublication": "asyncEntry",
    "markdownCommandsKeepCapturedTextBeforeLaterTyping": "addBlock",
    "markdownAddBlockDoesNotContinueAfterOwnerRebind": "returnToOriginalID",
}
TABLE_SUITE = "SimpleTableTextPersistenceTests"
TABLE_EXPECTED = {TABLE_SUITE + "/" + name for name in TABLE_PLAIN | set(TABLE_PARAMETERS)}
EXPECTED = fixtures.EXPECTED | TABLE_EXPECTED
UNSELECTED = {
    "nativeFocusObservationDistinguishesOutcomes": "outcome:",
    "pendingFocusWaitsForKeyWindow": "", "refusedFocusWaitsForWindowReadiness": "",
    "laterFocusSupersedesDetachedRequest": "useNativeEditing:",
    "editingDenialCancelsPendingFocus": "locked:",
    "focusedTextViewDoesNotReplayResponderAcquisition": "",
    "consumedAndNewerFocusSurviveOldCallbacks": "",
}


def table_tree():
    children = []
    for name in sorted(TABLE_PLAIN | set(TABLE_PARAMETERS)):
        parameter = TABLE_PARAMETERS.get(name)
        signature = parameter + ":" if parameter else ""
        node = dict(nodeType="Test Case", nodeIdentifier="AnytypeTests/" + TABLE_SUITE + "/" + name
                    + "(" + signature + ")", result="Passed")
        if parameter:
            node["children"] = [dict(nodeType="Arguments", name=json.dumps(value), result="Passed")
                                for value in (False, True)]
        children.append(node)
    return dict(children=children)


class ExistingBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "Anytype.app"
        self.app.mkdir()
        self.app_executable = self.app / "Anytype"
        self.test_bundle = self.app / "AnytypeTests.xctest"
        self.test_bundle.mkdir()
        self.test_executable = self.test_bundle / "AnytypeTests"
        self.configuration = self.root / "Anytype.xctestrun"
        for path in (self.app_executable, self.test_executable, self.configuration):
            path.write_bytes(path.name.encode())
        self.tree = dict(children=fixtures.tree()["children"] + table_tree()["children"])
        declarations = {node["nodeIdentifier"].removeprefix("AnytypeTests/").split("(", 1)[0]:
                        node["nodeIdentifier"] for node in self.tree["children"]}
        declarations.update({fixtures.SUITE + "/" + name:
                             "AnytypeTests/" + fixtures.SUITE + "/" + name + "(" + parameters + ")"
                             for name, parameters in UNSELECTED.items()})
        self.source = dict(methods=sorted(EXPECTED), source_hashes={"editor.swift": "a" * 64,
                           "table.swift": "b" * 64}, expected_methods=21, declared_invocations=29,
                           profile=runner.PROFILE, compiled_declarations=declarations,
                           unselected_existing_methods=sorted(set(declarations) - EXPECTED))
        self.report = fixtures.summary(21)
        self.commands, self.enumerations = [], []
        self.after_run, self.after_enumeration, self.mutate_enumeration = None, None, None
        self.shared = SimpleNamespace(write=self.write, digest=self.digest, run_xctest=self.run_xctest)
        self.products = (self.app, self.app_executable, self.test_bundle, self.test_executable)
        source_patch = patch.object(runner, "source_contract", return_value=self.source)
        self.source_mock = source_patch.start()
        self.addCleanup(source_patch.stop)
        product_patch = patch.object(runner.host, "xctest_products", return_value=self.products)
        self.product_mock = product_patch.start()
        self.addCleanup(product_patch.stop)
        enumeration_patch = patch.object(runner.host, "command", side_effect=self.enumerate_tests)
        enumeration_patch.start()
        self.addCleanup(enumeration_patch.stop)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def enumerate_tests(self, command, app, evidence):
        self.enumerations.append(command)
        self.assertIn("-enumerate-tests", command)
        self.assertEqual(command[command.index("-test-enumeration-style") + 1], "flat")
        self.assertEqual(command[command.index("-test-enumeration-format") + 1], "json")
        path = Path(command[command.index("-test-enumeration-output-path") + 1])
        discovery = path.name == "compiled-suite-enumeration.json"
        identifiers = sorted(self.source["compiled_declarations"].values()) if discovery else [
            argument.removeprefix("-only-testing:") for argument in command if argument.startswith("-only-testing:")]
        payload = {"errors": [], "values": [{"testPlan": "Anytype", "disabledTests": [],
                    "enabledTests": [{"identifier": identifier} for identifier in identifiers]}]}
        if self.mutate_enumeration:
            self.mutate_enumeration(payload, discovery)
        self.write(path, payload)
        if not discovery and self.after_enumeration:
            self.after_enumeration()

    def run_xctest(self, command, app, evidence, bundle, prefix, *, command_runner):
        self.commands.append(command)
        self.assertIs(command_runner, runner.host.command)
        self.write(evidence / (prefix + "-summary.json"), self.report)
        self.write(evidence / (prefix + "-tests.json"), self.tree)
        if self.after_run:
            self.after_run()

    def execute(self, directory="evidence"):
        return runner.execute(self.root, self.configuration, fixtures.UDID, self.app,
                              self.root / directory, self.shared)

    def test_one_build_enumerates_exact21_then_proves_all29_actual_cases(self):
        for count in (21, 29):
            self.report = fixtures.summary(count)
            result = self.execute("evidence-" + str(count))
            self.assertEqual(result["status"], runner.PASS_STATUS)
            self.assertEqual(result["actual"]["actual_method_count"], 21)
            self.assertEqual(result["actual"]["declared_case_count"], 29)
            self.assertEqual(result["actual"]["components"]["shared-editor"]["declared_case_count"], 15)
            self.assertEqual(result["actual"]["components"]["shared-table"]["declared_case_count"], 14)
            self.assertEqual(result["additional_app_builds"], 0)
            self.assertFalse(result["real_native_persistence_accepted"])
            self.assertEqual(result["enumeration"]["enumerated_source_method_count"], 28)
            self.assertEqual(len(result["enumeration"]["unselected_identifiers"]), 7)
            selected = {"-only-testing:" + self.source["compiled_declarations"][name] for name in EXPECTED}
            for command in (self.enumerations[-1], self.commands[-1]):
                self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
                self.assertEqual({item for item in command if item.startswith("-only-testing:")}, selected)
                self.assertNotIn("build-for-testing", command)
            self.assertNotIn("-enumerate-tests", self.commands[-1])
        self.assertEqual(len(self.commands), 2)
        self.assertEqual(len(self.enumerations), 4)

    def test_discovery_errors_missing_duplicate_disabled_and_signature_drift_never_execute(self):
        for change in ("error", "empty", "missing", "duplicate", "disabled", "signature"):
            def mutate(payload, discovery, change=change):
                if not discovery:
                    return
                rows = payload["values"][0]["enabledTests"]
                if change == "error":
                    payload["errors"] = ["Enumeration failed"]
                elif change == "empty":
                    rows.clear()
                elif change == "missing":
                    rows.pop()
                elif change == "duplicate":
                    rows.append(copy.deepcopy(rows[0]))
                elif change == "disabled":
                    payload["values"][0]["disabledTests"].append(rows.pop())
                else:
                    rows[0]["identifier"] = rows[0]["identifier"].replace("()", "(unreviewed:)")
            self.mutate_enumeration = mutate
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.execute(change)
            self.assertEqual(self.commands, [])

    def test_exact_selection_enumeration_rejects_zero_extra_or_disabled_before_execution(self):
        for change in ("empty", "extra", "disabled"):
            def mutate(payload, discovery, change=change):
                if discovery:
                    return
                rows = payload["values"][0]["enabledTests"]
                if change == "empty":
                    rows.clear()
                elif change == "extra":
                    rows.append({"identifier": self.source["compiled_declarations"][
                        fixtures.SUITE + "/pendingFocusWaitsForKeyWindow"]})
                else:
                    payload["values"][0]["disabledTests"].append(rows.pop())
            self.mutate_enumeration = mutate
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.execute(change)
            self.assertEqual(self.commands, [])

    def test_wrong_app_product_is_rejected_before_xcode(self):
        self.product_mock.return_value = (self.root / "different.app", *self.products[1:])
        with self.assertRaisesRegex(ValueError, "SDK06 app build"):
            self.execute()
        self.assertEqual(self.commands + self.enumerations, [])

    def test_missing_duplicate_or_nonpassing_arguments_in_either_group_cannot_hide_in_summary(self):
        original = copy.deepcopy(self.tree)
        for suite in (fixtures.SUITE, TABLE_SUITE):
            for change in ("missing", "duplicate", "skipped"):
                self.tree = copy.deepcopy(original)
                node = next(item for item in self.tree["children"]
                            if ("/" + suite + "/") in item["nodeIdentifier"] and item.get("children"))
                if change == "missing":
                    node["children"].pop()
                elif change == "duplicate":
                    node["children"][-1]["name"] = node["children"][0]["name"]
                else:
                    node["children"][-1]["result"] = "Skipped"
                with self.subTest(suite=suite, change=change), self.assertRaises(ValueError):
                    self.execute(suite + change)
                result = json.loads((self.root / (suite + change) / "execution.json").read_text())
                self.assertEqual(result["status"], "FAIL")

    def test_unrequested_actual_method_is_rejected_even_after_correct_enumeration(self):
        self.tree["children"].append(dict(nodeType="Test Case", result="Passed", nodeIdentifier=
            self.source["compiled_declarations"][fixtures.SUITE + "/pendingFocusWaitsForKeyWindow"]))
        with self.assertRaisesRegex(ValueError, "Unexpected xcresult"):
            self.execute()

    def test_source_mutation_during_enumeration_prevents_execution(self):
        changed = copy.deepcopy(self.source)
        changed["source_hashes"]["table.swift"] = "c" * 64
        self.source_mock.side_effect = [self.source, changed]
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.execute()
        self.assertEqual(self.commands, [])

    def test_source_mutation_during_execution_is_rejected(self):
        changed = copy.deepcopy(self.source)
        changed["source_hashes"]["editor.swift"] = "c" * 64
        self.source_mock.side_effect = [self.source, self.source, changed]
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.execute()
        self.assertEqual(len(self.commands), 1)

    def test_mutated_app_test_or_configuration_is_rejected_before_or_after_execution(self):
        for phase in ("enumeration", "execution"):
            for index, path in enumerate((self.app_executable, self.test_executable, self.configuration)):
                self.after_enumeration, self.after_run = None, None
                action = lambda path=path: path.write_bytes(path.read_bytes() + b"changed")
                if phase == "enumeration":
                    self.after_enumeration = action
                else:
                    self.after_run = action
                executed_before = len(self.commands)
                with self.subTest(phase=phase, path=path.name), self.assertRaisesRegex(ValueError, "built products changed"):
                    self.execute(phase + str(index))
                self.assertEqual(len(self.commands) - executed_before, int(phase == "execution"))

    def test_stale_evidence_is_rejected_before_xcode(self):
        self.write(self.root / "evidence/execution.json", {"status": "old"})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.execute()
        self.assertEqual(self.commands + self.enumerations, [])


class TrackedContractTests(unittest.TestCase):
    def test_actual_tracked_profiles_keep_exact_pending_selection_and_original_ack7(self):
        root = Path(__file__).resolve().parents[2]
        source = runner.source_contract(root)
        self.assertEqual(source["methods"], sorted(EXPECTED))
        self.assertEqual(source["declared_invocations"], 29)
        self.assertEqual(len(source["source_hashes"]), 2)
        self.assertEqual(len(source["compiled_declarations"]), 28)
        self.assertEqual(source["unselected_existing_methods"],
                         sorted(fixtures.SUITE + "/" + name for name in UNSELECTED))
        acknowledgement = text_native_ack.source_contract(root)
        self.assertEqual(acknowledgement["expected_methods"], 7)
        self.assertEqual(acknowledgement["methods"], text_native_ack.METHODS)


if __name__ == "__main__":
    unittest.main()
