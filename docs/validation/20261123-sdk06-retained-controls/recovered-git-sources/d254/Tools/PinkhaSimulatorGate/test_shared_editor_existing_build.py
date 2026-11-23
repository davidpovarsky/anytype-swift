"""Focused controls for exact editor/table/authority execution in the SDK06 build.

Synthetic enumerations/results below test the controller, never stand in for
actual Apple evidence or qualify product acceptance.
"""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
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
AUTHORITY_SUITE = "TorahRelatedReadAuthorityMappingTests"
AUTHORITY_PARAMETERIZED = "nativeDenialRequiresExactTypedCodeAndDescription"
AUTHORITY_PLAIN = "providerAndTransportDescriptionsCannotForgeNativeAuthority"
AUTHORITY_EXPECTED = {AUTHORITY_SUITE + "/" + name
                      for name in (AUTHORITY_PARAMETERIZED, AUTHORITY_PLAIN)}
EXPECTED = fixtures.EXPECTED | TABLE_EXPECTED | AUTHORITY_EXPECTED
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

def authority_tree():
    return dict(children=[
        dict(nodeType="Test Case",
             nodeIdentifier="AnytypeTests/" + AUTHORITY_SUITE + "/" + AUTHORITY_PARAMETERIZED + "(objectShow:)",
             result="Passed", children=[
                 dict(nodeType="Arguments", name=json.dumps(value), result="Passed")
                 for value in (False, True)]),
        dict(nodeType="Test Case", result="Passed",
             nodeIdentifier="AnytypeTests/" + AUTHORITY_SUITE + "/" + AUTHORITY_PLAIN + "()"),
    ])


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
        for path in (self.app_executable, self.test_executable):
            path.write_bytes(path.name.encode())
        self.original_configuration = {"__xctestrun_metadata__": {"FormatVersion": 2}, "TestConfigurations": [
            {"Name": "Anytype", "IsEnabled": True, "TestTargets": [
                {"BlueprintName": "AnytypeTests", "TestHostPath": "__TESTROOT__/Anytype.app",
                 "TestBundlePath": "__TESTHOST__/AnytypeTests.xctest", "EnvironmentVariables": {"OWNED": "1"},
                 "OnlyTestIdentifiers": [fixtures.SUITE, TABLE_SUITE, AUTHORITY_SUITE, text_native_ack.SUITE],
                 "SkipTestIdentifiers": []},
                {"BlueprintName": "OtherTests", "TestBundlePath": "__TESTROOT__/OtherTests.xctest"}]}]}
        self.configuration.write_bytes(plistlib.dumps(self.original_configuration))
        self.original_product_bytes = {path: path.read_bytes()
                                       for path in (self.app_executable, self.test_executable, self.configuration)}
        self.tree = dict(children=fixtures.tree()["children"] + table_tree()["children"] + authority_tree()["children"])
        declarations = {node["nodeIdentifier"].removeprefix("AnytypeTests/").split("(", 1)[0]:
                        node["nodeIdentifier"] for node in self.tree["children"]}
        declarations.update({fixtures.SUITE + "/" + name:
                             "AnytypeTests/" + fixtures.SUITE + "/" + name + "(" + parameters + ")"
                             for name, parameters in UNSELECTED.items()})
        self.source = dict(methods=sorted(EXPECTED), source_hashes={"editor.swift": "a" * 64,
                           "table.swift": "b" * 64, "authority.swift": "d" * 64}, expected_methods=23, declared_invocations=32,
                           profile=runner.PROFILE, compiled_declarations=declarations,
                           unselected_existing_methods=sorted(set(declarations) - EXPECTED))
        self.report = fixtures.summary(23)
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
        configuration_path = Path(command[command.index("-xctestrun") + 1])
        self.assertNotEqual(configuration_path, self.configuration)
        self.assertEqual(configuration_path.parent, self.configuration.parent)
        value = plistlib.loads(configuration_path.read_bytes())
        targets = value["TestConfigurations"][0]["TestTargets"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["BlueprintName"], "AnytypeTests")
        self.assertEqual(targets[0]["EnvironmentVariables"], {"OWNED": "1"})
        # Deliberately ignore CLI filters here: the native configuration must
        # constrain discovery even on an SDK that enumerates past CLI filters.
        enabled, disabled = [], []
        for identifier in sorted(self.source["compiled_declarations"].values()):
            relative = identifier.removeprefix("AnytypeTests/")
            # Original run45047827580 enabled zero-argument full signatures,
            # but rejected all parameterized full-signature selectors. Model
            # that observed failure and the separate method-name grammar here;
            # actual Apple enumeration still has to verify the latter.
            matches = lambda candidate: (relative.startswith(candidate + "/")
                                         or relative.split("(", 1)[0] == candidate
                                         or (relative.endswith("()") and relative == candidate))
            if any(matches(candidate) for candidate in targets[0]["OnlyTestIdentifiers"]):
                (disabled if any(matches(candidate) for candidate in targets[0]["SkipTestIdentifiers"])
                 else enabled).append({"identifier": identifier})
            else:
                disabled.append({"identifier": identifier})
        payload = {"errors": [], "values": [{"testPlan": "Anytype",
                    "enabledTests": enabled, "disabledTests": disabled}]}
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

    def test_one_build_enumerates_exact23_then_proves_all32_actual_cases(self):
        for count in (23, 32):
            self.report = fixtures.summary(count)
            result = self.execute("evidence-" + str(count))
            self.assertEqual(result["status"], runner.PASS_STATUS)
            self.assertEqual(result["actual"]["actual_method_count"], 23)
            self.assertEqual(result["actual"]["declared_case_count"], 32)
            self.assertEqual(result["actual"]["components"]["shared-editor"]["declared_case_count"], 15)
            self.assertEqual(result["actual"]["components"]["shared-table"]["declared_case_count"], 14)
            self.assertEqual(result["actual"]["components"]["related-read-authority"]["declared_case_count"], 3)
            self.assertEqual(set(result["component_receipts"]),
                             {"shared-editor", "shared-table", "related-read-authority"})
            for label, expected_methods in (("shared-editor", fixtures.EXPECTED),
                                             ("shared-table", TABLE_EXPECTED),
                                             ("related-read-authority", AUTHORITY_EXPECTED)):
                receipt_info = result["component_receipts"][label]
                path = Path(receipt_info["path"])
                self.assertEqual(self.digest(path), receipt_info["sha256"])
                component = json.loads(path.read_text())
                self.assertEqual(component["status"], "SOURCE_BOUND_COMPONENT_PASS")
                self.assertEqual(set(component["methods"]), expected_methods)
                self.assertFalse(component["real_native_persistence_accepted"])

            self.assertEqual(result["additional_app_builds"], 0)
            self.assertFalse(result["real_native_persistence_accepted"])
            self.assertEqual(result["enumeration"]["enumerated_source_method_count"], 30)
            self.assertEqual(len(result["enumeration"]["unselected_identifiers"]), 7)
            self.assertEqual(plistlib.loads(self.configuration.read_bytes()), self.original_configuration)
            binding = result["enumeration"]["selected_configuration"]
            self.assertEqual(binding["other_targets_removed_from_copy"], ["OtherTests"])
            selectors = {identifier if identifier.endswith("()") else identifier.split("(", 1)[0]
                         for identifier in (self.source["compiled_declarations"][name] for name in EXPECTED)}
            self.assertEqual(set(binding["only_test_identifiers"]),
                             {identifier.removeprefix("AnytypeTests/") for identifier in selectors})
            selected = {"-only-testing:" + identifier for identifier in selectors}
            for command in (self.enumerations[-1], self.commands[-1]):
                self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
                self.assertEqual({item for item in command if item.startswith("-only-testing:")}, selected)
                self.assertNotIn("build-for-testing", command)
            self.assertNotIn("-enumerate-tests", self.commands[-1])
            self.assertEqual(self.commands[-1][self.commands[-1].index("-xctestrun") + 1],
                             self.enumerations[-1][self.enumerations[-1].index("-xctestrun") + 1])
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


    def test_old_editor_table_only_result_cannot_qualify_the_authority_extension(self):
        self.tree["children"] = [node for node in self.tree["children"]
                                 if ("/" + AUTHORITY_SUITE + "/") not in node["nodeIdentifier"]]
        for old_count in (21, 29):
            self.report = fixtures.summary(old_count)
            with self.subTest(old_count=old_count), self.assertRaises(ValueError):
                self.execute("old-scope-" + str(old_count))

    def test_authority_compiled_signature_drift_prevents_any_component_execution(self):
        def mutate(payload, discovery):
            if discovery:
                for row in payload["values"][0]["enabledTests"]:
                    if AUTHORITY_PARAMETERIZED in row["identifier"]:
                        row["identifier"] = row["identifier"].replace("(objectShow:)", "(unreviewed:)")
        self.mutate_enumeration = mutate
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.commands, [])

    def test_wrong_app_product_is_rejected_before_xcode(self):
        self.product_mock.return_value = (self.root / "different.app", *self.products[1:])
        with self.assertRaisesRegex(ValueError, "SDK06 app build"):
            self.execute()
        self.assertEqual(self.commands + self.enumerations, [])

    def test_missing_duplicate_or_nonpassing_arguments_in_any_group_cannot_hide_in_summary(self):
        original = copy.deepcopy(self.tree)
        for suite in (fixtures.SUITE, TABLE_SUITE, AUTHORITY_SUITE):
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
                for product, raw in self.original_product_bytes.items():
                    product.write_bytes(raw)
                action = lambda path=path: path.write_bytes(path.read_bytes() + b"changed")
                if phase == "enumeration":
                    self.after_enumeration = action
                else:
                    self.after_run = action
                executed_before = len(self.commands)
                with self.subTest(phase=phase, path=path.name), self.assertRaisesRegex(ValueError, "(built products|xctestrun) changed"):
                    self.execute(phase + str(index))
                self.assertEqual(len(self.commands) - executed_before, int(phase == "execution"))

    def test_stale_evidence_is_rejected_before_xcode(self):
        self.write(self.root / "evidence/execution.json", {"status": "old"})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.execute()
        self.assertEqual(self.commands + self.enumerations, [])

    def test_ambiguous_disabled_or_unknown_original_configuration_never_executes(self):
        for change in ("version", "configuration", "duplicate-target", "disabled-target"):
            value = copy.deepcopy(self.original_configuration)
            if change == "version":
                value["__xctestrun_metadata__"]["FormatVersion"] = 1
            elif change == "configuration":
                value["TestConfigurations"].append(copy.deepcopy(value["TestConfigurations"][0]))
            elif change == "duplicate-target":
                targets = value["TestConfigurations"][0]["TestTargets"]
                targets.append(copy.deepcopy(targets[0]))
            else:
                value["TestConfigurations"][0]["TestTargets"][0]["IsEnabled"] = False
            self.configuration.write_bytes(plistlib.dumps(value))
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.execute(change)
            self.assertEqual(self.commands + self.enumerations, [])

    def test_existing_skip_cannot_be_silently_reenabled_by_a_scoped_copy(self):
        value = copy.deepcopy(self.original_configuration)
        value["TestConfigurations"][0]["TestTargets"][0]["SkipTestIdentifiers"] = [
            TABLE_SUITE + "/acceptedSnapshotSurvivesViewReuse()"]
        self.configuration.write_bytes(plistlib.dumps(value))
        with self.assertRaisesRegex(ValueError, "exact30"):
            self.execute()
        self.assertEqual(self.commands, [])
        self.assertEqual(plistlib.loads(self.configuration.read_bytes()), value)

    def test_selected_configuration_mutation_before_or_after_execution_is_rejected(self):
        for phase in ("enumeration", "execution"):
            self.after_enumeration, self.after_run = None, None
            directory = "selected-mutation-" + phase
            def action():
                command = self.enumerations[-1]
                path = Path(command[command.index("-xctestrun") + 1])
                path.write_bytes(path.read_bytes() + b"changed")
            if phase == "enumeration":
                self.after_enumeration = action
            else:
                self.after_run = action
            executed_before = len(self.commands)
            with self.subTest(phase=phase), self.assertRaisesRegex(ValueError, "xctestrun changed"):
                self.execute(directory)
            self.assertEqual(len(self.commands) - executed_before, int(phase == "execution"))

    def test_fresh_owned_nonce_preserves_cached_other_run_configuration_files(self):
        stale = [self.configuration.with_name("UI27-evidence-" + suffix + ".xctestrun")
                 for suffix in ("discovery", "selected")]
        for path in stale:
            path.write_bytes(b"preserved-other-run-copy")
        result = self.execute()
        enumeration = result["enumeration"]
        nonce = enumeration["selection_nonce"]
        self.assertRegex(nonce, r"^[0-9a-f]{32}$")
        for key, suffix in (("discovery_configuration", "discovery"), ("selected_configuration", "selected")):
            path = Path(enumeration[key]["path"])
            self.assertEqual(path.name, "UI27-evidence-" + nonce + "-" + suffix + ".xctestrun")
            self.assertEqual(self.digest(path), enumeration[key]["sha256"])
        for path in stale:
            self.assertEqual(path.read_bytes(), b"preserved-other-run-copy")
        self.assertEqual(result["status"], runner.PASS_STATUS)


class SelectorRepairTests(unittest.TestCase):
    """New controller controls; synthetic terminals are never product proof."""

    setUp = ExistingBuildTests.setUp
    write = staticmethod(ExistingBuildTests.write)
    digest = staticmethod(ExistingBuildTests.digest)
    enumerate_tests = ExistingBuildTests.enumerate_tests
    run_xctest = ExistingBuildTests.run_xctest
    execute = ExistingBuildTests.execute

    def test_parameterized_filter_mapping_preserves_exact_full_identity_and_32_cases(self):
        result = self.execute()
        enumeration = result["enumeration"]
        full_ids = {self.source["compiled_declarations"][name] for name in EXPECTED}
        parameterized = {identifier for identifier in full_ids if not identifier.endswith("()")}
        self.assertEqual(len(parameterized), 8)
        self.assertEqual(set(enumeration["selected_identifiers"]), full_ids)
        expected_filters = {identifier.split("(", 1)[0] for identifier in parameterized} | (full_ids - parameterized)
        self.assertEqual(set(enumeration["xcode_method_selectors"]), expected_filters)
        self.assertEqual(set(enumeration["selector_identity_binding"].values()), full_ids)
        self.assertEqual(len(enumeration["selector_identity_binding"]), 23)
        self.assertEqual(result["actual"]["declared_case_count"], 32)
        self.assertEqual({item for item in self.commands[0] if item.startswith("-only-testing:")},
                         {"-only-testing:" + name for name in expected_filters})
        self.assertEqual(plistlib.loads(self.configuration.read_bytes()), self.original_configuration)

    def test_original_full_parameter_signature_filters_reproduce_15_only_refusal(self):
        with patch.object(runner, "xcode_method_selectors", side_effect=lambda selected, declarations: selected):
            with self.assertRaisesRegex(ValueError, "exact23"):
                self.execute()
        payload = json.loads((self.root / "evidence/compiled-selected-enumeration.json").read_text())
        _, enabled, disabled = runner.enumerated_identifiers(payload)
        expected = {self.source["compiled_declarations"][name] for name in EXPECTED}
        self.assertEqual(len(enabled), 15)
        self.assertEqual(expected - enabled, {name for name in expected if not name.endswith("()")})
        self.assertTrue((expected - enabled).issubset(disabled))
        self.assertEqual(self.commands, [])

    def test_mapped_filter_still_rejects_changed_full_signature_before_execution(self):
        def mutate(payload, discovery):
            if not discovery:
                node = next(row for row in payload["values"][0]["enabledTests"]
                            if "(objectShow:)" in row["identifier"])
                node["identifier"] = node["identifier"].replace("(objectShow:)", "(unreviewed:)")
        self.mutate_enumeration = mutate
        with self.assertRaisesRegex(ValueError, "exact23"):
            self.execute()
        self.assertEqual(self.commands, [])

    def test_selector_mapping_refuses_overloads_unknown_or_unscoped_identities(self):
        identifier = "AnytypeTests/" + AUTHORITY_SUITE + "/" + AUTHORITY_PARAMETERIZED + "(objectShow:)"
        declarations = list(self.source["compiled_declarations"].values())
        cases = [
            ([identifier], declarations + [identifier.replace("(objectShow:)", "(other:)")]),
            ([identifier, identifier], declarations),
            ([], declarations),
            ([identifier.replace("(objectShow:)", "(unknown:)")], declarations),
            (["AnytypeTests/" + AUTHORITY_SUITE], declarations),
            ([identifier], declarations + ["OtherTarget/OtherSuite/method()"]),
        ]
        for selected, inventory in cases:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                runner.xcode_method_selectors(selected, inventory)
        self.assertEqual(self.commands + self.enumerations, [])


class TrackedContractTests(unittest.TestCase):
    def test_actual_tracked_profiles_keep_exact_pending_selection_and_original_ack7(self):
        root = Path(__file__).resolve().parents[2]
        source = runner.source_contract(root)
        self.assertEqual(source["methods"], sorted(EXPECTED))
        self.assertEqual(source["declared_invocations"], 32)
        self.assertEqual(len(source["source_hashes"]), 3)
        self.assertEqual(len(source["compiled_declarations"]), 30)
        self.assertEqual(source["unselected_existing_methods"],
                         sorted(fixtures.SUITE + "/" + name for name in UNSELECTED))
        acknowledgement = text_native_ack.source_contract(root)
        self.assertEqual(acknowledgement["expected_methods"], 7)
        self.assertEqual(acknowledgement["methods"], text_native_ack.METHODS)


    def test_authority_source_requires_both_exact_native_types_and_literal_arguments(self):
        root = Path(__file__).resolve().parents[2]
        text = (root / runner.authority.SOURCE_PATH).read_text(encoding="utf-8")
        self.assertEqual(runner.authority.validate_source(text),
                         {AUTHORITY_PARAMETERIZED, AUTHORITY_PLAIN})
        changes = [
            text.replace("objectShow: Bool", "show: Bool"),
            text.replace("arguments: [false, true]", "arguments: [true]"),
            text.replace("arguments: [false, true]", "arguments: [true, true]"),
        ]
        for changed in changes:
            with self.subTest(source=changed), self.assertRaises(ValueError):
                runner.authority.validate_source(changed)


if __name__ == "__main__":
    unittest.main()
