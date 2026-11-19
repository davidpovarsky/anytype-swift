"""Controls for real-fixture selection; these are not application acceptance."""
import json
import hashlib
import plistlib
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from run_wave15_acceptance import (plan, fixture_environment, property_environment,
                                   validate_device_language, configure_editor_device_language,
                                   require_source_identity)


class AcceptanceSelectionTests(unittest.TestCase):
    def test_only_reviewed_native_branches_with_exact_source_and_ref_are_admitted(self):
        branches = ["codex/chatgpt-wave15-integration-20261118",
                    "codex/chatgpt-wave15-hanlin-consumer-20261119",
                    "codex/chatgpt-wave15-ui-resume-20261119"]
        for branch in branches:
            require_source_identity("a" * 40, "a" * 40, branch, "refs/heads/" + branch)
        rejected = [
            ("a" * 40, "a" * 40, "unreviewed-consumer", "refs/heads/unreviewed-consumer"),
            ("a" * 40, "a" * 40, branches[0], "refs/heads/" + branches[1]),
            ("a" * 40, "a" * 40, branches[0], "refs/tags/" + branches[0]),
            ("a" * 40, "a" * 40, branches[2], "refs/heads/" + branches[0]),
            ("a" * 40, "b" * 40, branches[0], "refs/heads/" + branches[0]),
            ("", "", branches[0], "refs/heads/" + branches[0]),
        ]
        for arguments in rejected:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                require_source_identity(*arguments)

    def test_english_label_methods_cannot_claim_hebrew_coverage(self):
        for lane in ["inspector", "quote-drop", "properties", "properties-set", "canonical-properties", "hanlin-native"]:
            with self.subTest(lane=lane), self.assertRaisesRegex(ValueError, "English labels"):
                plan(lane, "ipad", "he")
        self.assertEqual(plan("editor", "ipad", "he")["expected_ui_executions"], 3)

    def test_named_selections_remain_partial_acceptance(self):
        for lane, count in [("inspector", 5), ("quote-drop", 1), ("properties", 3), ("properties-set", 2), ("editor", 3), ("canonical-properties", 1), ("hanlin-native", 1)]:
            with self.subTest(lane=lane):
                value = plan(lane, "iphone", "en")
                self.assertEqual(len(set(value["methods"])), count)
                self.assertFalse(value["full_matrix_accepted"])
                self.assertFalse(value["release_accepted"])
                self.assertEqual(value["build_configuration"],
                                 "Debug-Anytype" if lane == "hanlin-native" else "Release-Anytype")

    def test_missing_or_reused_real_object_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            fixture_environment("inspector", {"spaceId": "s", "universalDocuments": {"page": "p"}, "manySourcesDocument": "p"}, "en")
        with self.assertRaisesRegex(ValueError, "three distinct"):
            fixture_environment("editor", {"spaceId": "s", "pinkhaObjectId": "p", "noteObjectId": "n", "pageObjectId": "p"}, "he")
        with self.assertRaisesRegex(ValueError, "Space"):
            fixture_environment("inspector", {"spaceId": "", "universalDocuments": {"page": "p"}, "manySourcesDocument": "d"}, "en")

    def test_editor_environment_uses_actual_persisted_fixture_ids(self):
        value = fixture_environment("editor", {"spaceId": "s", "pinkhaObjectId": "a", "noteObjectId": "b", "pageObjectId": "c"}, "he", observed_device_language="en")
        self.assertEqual(value["PINKHA_ACCEPTANCE_DIRECTION"], "rtl")
        self.assertEqual(value["PINKHA_ACCEPTANCE_PINKHA_ID"], "a")
        self.assertEqual(value["PINKHA_ACCEPTANCE_NOTE_ID"], "b")
        self.assertEqual(value["PINKHA_ACCEPTANCE_PAGE_ID"], "c")

    def test_editor_cannot_use_an_unobserved_or_matching_device_language(self):
        fixture = {"spaceId": "s", "pinkhaObjectId": "a", "noteObjectId": "b", "pageObjectId": "c"}
        for actual in [None, "", "he", "fr", True]:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, "verified"):
                fixture_environment("editor", fixture, "he", observed_device_language=actual)
        value = fixture_environment("editor", fixture, "he", observed_device_language="en")
        self.assertEqual(value["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"], "en")

    def test_actual_language_globals_support_both_mismatch_directions(self):
        for app_language, device_language, locale in [("en", "he-IL", "he_IL"), ("he", "en-US", "en_US")]:
            with self.subTest(app_language=app_language):
                raw = plistlib.dumps({"AppleLanguages": [device_language], "AppleLocale": locale})
                value = validate_device_language(raw, app_language)
                self.assertNotEqual(value["device_language"], app_language)
                self.assertEqual(value["verification_scope"], "SIMULATOR_GLOBAL_PREFERENCES_AFTER_REBOOT")
                self.assertFalse(value["app_override_verified_by_this_observation"])
                self.assertEqual(value["preferences_sha256"], hashlib.sha256(raw).hexdigest())

    def test_wrong_missing_or_unreadable_device_preferences_fail_closed(self):
        cases = [
            b"", b"not a property list", plistlib.dumps(["en"]),
            plistlib.dumps({"AppleLocale": "en_US"}),
            plistlib.dumps({"AppleLanguages": "en", "AppleLocale": "en_US"}),
            plistlib.dumps({"AppleLanguages": [], "AppleLocale": "en_US"}),
            plistlib.dumps({"AppleLanguages": [True], "AppleLocale": "en_US"}),
            plistlib.dumps({"AppleLanguages": ["he"], "AppleLocale": "he_IL"}),
            plistlib.dumps({"AppleLanguages": ["en"], "AppleLocale": "he_IL"}),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                validate_device_language(raw, "he")

    def test_device_readback_happens_after_reboot_and_does_not_publish_other_globals(self):
        raw = plistlib.dumps({"AppleLanguages": ["en"], "AppleLocale": "en_US",
                              "UnrelatedPrivateFixture": "do-not-publish"})
        events = []
        def command(argv, *_):
            events.append(argv)
        def observe(argv, **_):
            events.append(argv)
            return subprocess.CompletedProcess(argv, 0, raw, b"")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("run_wave15_acceptance.shared.command", side_effect=command), \
                    patch("run_wave15_acceptance.subprocess.run", side_effect=observe) as readback:
                value = configure_editor_device_language(root, root, "fixture-udid", "he")
            output = (root / "device-language-observation.json").read_text()
        self.assertEqual([event[2] for event in events], ["spawn", "spawn", "shutdown", "boot", "bootstatus", "spawn"])
        self.assertEqual(events[-1][-3:], ["export", "NSGlobalDomain", "-"])
        self.assertEqual(value["status"], "DEVICE_LANGUAGE_PREFERENCES_VERIFIED")
        self.assertNotIn("do-not-publish", output)
        self.assertNotIn("UnrelatedPrivateFixture", output)
        readback.assert_called_once_with(events[-1], capture_output=True, timeout=120)
        self.assertEqual(value["readback_timeout_seconds"], 120)
        self.assertGreaterEqual(value["readback_elapsed_seconds"], 0)

    def test_device_readback_failure_keeps_failure_receipt_and_cannot_claim_language(self):
        for code, raw in [(1, b""), (0, plistlib.dumps({"AppleLanguages": ["he"], "AppleLocale": "he_IL"}))]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = subprocess.CompletedProcess([], code, raw, b"read failed" if code else b"")
                with patch("run_wave15_acceptance.shared.command"), \
                        patch("run_wave15_acceptance.subprocess.run", return_value=result), \
                        self.assertRaises(ValueError):
                    configure_editor_device_language(root, root, "fixture-udid", "he")
                value = json.loads((root / "device-language-observation.json").read_text())
                self.assertEqual(value["status"], "FAIL")
                self.assertNotIn("device_language", value)

    def test_device_readback_timeout_and_cancellation_fail_once_with_bounded_evidence(self):
        timeout = subprocess.TimeoutExpired(["xcrun", "simctl", "spawn", "fixture-udid"], 120,
                                             output=b"private-partial-preferences")
        for error in [timeout, KeyboardInterrupt()]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with patch("run_wave15_acceptance.shared.command"), \
                        patch("run_wave15_acceptance.time.monotonic", side_effect=[10.0, 130.5]), \
                        patch("run_wave15_acceptance.subprocess.run", side_effect=error) as readback, \
                        self.assertRaises(type(error)):
                    configure_editor_device_language(root, root, "fixture-udid", "he")
                output = (root / "device-language-observation.json").read_text()
                value = json.loads(output)
                self.assertEqual(readback.call_count, 1)
                self.assertEqual(readback.call_args.kwargs["timeout"], 120)
                self.assertEqual(value["status"], "FAIL")
                self.assertEqual(value["readback_timeout_seconds"], 120)
                self.assertEqual(value["readback_elapsed_seconds"], 120.5)
                self.assertNotIn("device_language", value)
                self.assertNotIn("verification_scope", value)
                self.assertNotIn("private-partial-preferences", output)

    def test_quote_drop_requires_the_native_disposable_source_document(self):
        fixture = {"spaceId": "s", "universalDocuments": {"page": "blank"}, "manySourcesDocument": "source"}
        environment = fixture_environment("quote-drop", fixture, "en")
        self.assertEqual(environment["PINKHA_NATIVE_UI_DISPOSABLE"], "1")
        self.assertEqual(json.loads(environment["PINKHA_NATIVE_UI_FIXTURE_JSON"]), fixture)
        self.assertEqual(plan("quote-drop", "ipad", "en")["methods"],
                         ["PinkhaTorahQuoteAcceptanceUITests/testNativeQuoteUndoRedoDragAndRelaunch"])
        with self.assertRaisesRegex(ValueError, "distinct"):
            fixture_environment("quote-drop", {**fixture, "manySourcesDocument": "blank"}, "en")

    def test_property_fixture_from_another_space_cannot_be_used(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "command-00.log").write_text("PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON " + json.dumps(
                {"PINKHA_PROPERTIES_SPACE_ID": "another"}))
            with self.assertRaisesRegex(ValueError, "another Space"):
                property_environment(root, "expected")

    def test_exact_native_header_cases_reach_only_the_existing_property_lanes(self):
        fixture = self.source_header_fixture()
        for lane in ["properties", "properties-set"]:
            with self.subTest(lane=lane):
                environment = fixture_environment(lane, fixture, "en")
                self.assertEqual(json.loads(environment["PINKHA_NATIVE_UI_FIXTURE_JSON"]), fixture)
        self.assertEqual(plan("properties", "ipad", "en")["expected_ui_executions"], 3)
        # Other lanes retain their own real preparation contract.
        simple = {"spaceId": "s", "universalDocuments": {"page": "page"}, "manySourcesDocument": "source"}
        self.assertEqual(json.loads(fixture_environment("inspector", simple, "en")["PINKHA_NATIVE_UI_FIXTURE_JSON"]), simple)

    def test_missing_foreign_or_ambiguous_header_cases_fail_before_ui(self):
        def changed(case_index, key, value):
            def apply(fixture):
                fixture["sourceHeaderCases"][case_index][key] = value
            return apply
        changes = {
            "missing": lambda f: f.pop("sourceHeaderCases"),
            "not_list": lambda f: f.update(sourceHeaderCases={}),
            "missing_case": lambda f: f["sourceHeaderCases"].pop(),
            "extra_case": lambda f: f["sourceHeaderCases"].append(f["sourceHeaderCases"][0]),
            "reordered": lambda f: f["sourceHeaderCases"].reverse(),
            "unknown_field": changed(0, "unobserved", True),
            "boolean_count": changed(1, "count", True),
            "float_count": changed(2, "count", 2.0),
            "string_count": changed(2, "count", "2"),
            "missing_label": changed(2, "labels", ["Genesis 2:1"]),
            "duplicate_label": changed(2, "labels", ["Genesis 2:1", "Genesis 2:1"]),
            "different_reference": changed(1, "labels", ["Genesis 1:1"]),
            "empty_object": changed(0, "objectId", ""),
            "same_object": changed(0, "objectId", "header-1"),
            "other_many_object": changed(3, "objectId", "not-the-native-twelve-object"),
            "writing_object": changed(0, "objectId", "writing-chiddush"),
            "page_object": changed(0, "objectId", "universal-page"),
            "type_object": changed(0, "objectId", "type-article"),
            "set_object": changed(0, "objectId", "writing-set"),
        }
        for name, change in changes.items():
            for lane in ["properties", "properties-set"]:
                with self.subTest(change=name, lane=lane):
                    fixture = self.source_header_fixture()
                    change(fixture)
                    with self.assertRaisesRegex(ValueError, "[Ss]ource header"):
                        fixture_environment(lane, fixture, "en")

    @staticmethod
    def source_header_fixture():
        roles = ["chiddush", "article", "research"]
        universal = ["page", "note", "custom"]
        fixture = {"spaceId": "s",
                "documents": {role: "writing-" + role for role in roles},
                "types": {role: "type-" + role for role in roles},
                "universalDocuments": {role: "universal-" + role for role in universal},
                "universalTypes": {role: "universal-type-" + role for role in universal},
                "setId": "writing-set", "universalSetId": "universal-set",
                "manySourcesDocument": "header-12",
                "sourceHeaderCases": [
                    {"count": count, "objectId": "header-" + str(count),
                     "labels": ["Genesis 2:" + str(index) for index in range(1, count + 1)]}
                    for count in [0, 1, 2, 12]]}
        values = [
            {"kind": kind, "canonicalKey": canonical, "propertyKey": "native-" + kind,
             "propertyName": name, "identity": "canonical-" + kind, "label": label}
            for kind, canonical, label, name in [
                ("ref", "Genesis 3:1", "Genesis 3:1", "מקור/ות"),
                ("topic", "creation", "Creation", "נושא"),
                ("word", "בראשית", "בראשית", "מילה / ערך")]
        ]
        fixture["typeSwitch"] = {
            "schemaVersion": 1, "objectId": "type-switch-document", "spaceId": "s",
            "name": "Native Type-switch preserved properties", "initialTypeId": "type-chiddush",
            "types": {role: {"id": "type-" + role, "label": role.title(), "propertyName": "Type",
                              "sectionId": "featured", "sectionTitle": "", "sectionExpandable": False}
                      for role in roles},
            "values": values,
            "nativeReadback": {"method": "ObjectShow", "objectId": "type-switch-document", "spaceId": "s",
                               "typeId": "type-chiddush", "canonicalNonempty": True,
                               "projections": {record["propertyKey"]: [record["identity"]] for record in values}},
        }
        return fixture

    def test_type_switch_preserves_native_identity_and_real_expandable_section_metadata(self):
        fixture = self.source_header_fixture()
        fixture["typeSwitch"]["types"]["article"].update(
            sectionId="hidden", sectionTitle="Hidden", sectionExpandable=True)
        for lane in ["properties", "properties-set"]:
            with self.subTest(lane=lane):
                result = fixture_environment(lane, fixture, "en")
                self.assertEqual(json.loads(result["PINKHA_NATIVE_UI_FIXTURE_JSON"]), fixture)
        self.assertEqual(plan("properties-set", "ipad", "en")["methods"], [
            "PinkhaNativeDerivedAcceptanceUITests/testRemainingNativeSourceFilterEditing",
            "PinkhaNativeDerivedAcceptanceUITests/testRemainingUniversalTypePickersAndMixedSet",
        ])

    def test_type_switch_rejects_reused_targets_and_unproven_native_readback_before_ui(self):
        def field(key, value):
            return lambda fixture: fixture["typeSwitch"].update({key: value})
        def choice(key, value):
            return lambda fixture: fixture["typeSwitch"]["types"]["article"].update({key: value})
        def association(index, key, value):
            return lambda fixture: fixture["typeSwitch"]["values"][index].update({key: value})
        def readback(key, value):
            return lambda fixture: fixture["typeSwitch"]["nativeReadback"].update({key: value})
        changes = {
            "missing": lambda f: f.pop("typeSwitch"),
            "unknown_field": field("unobserved", True),
            "boolean_version": field("schemaVersion", True),
            "future_version": field("schemaVersion", 2),
            "foreign_space": field("spaceId", "other-space"),
            "empty_object": field("objectId", ""),
            "wrong_name": field("name", "source header"),
            "writing_object": field("objectId", "writing-chiddush"),
            "header_object": field("objectId", "header-1"),
            "universal_object": field("objectId", "universal-page"),
            "type_object": field("objectId", "type-article"),
            "set_object": field("objectId", "universal-set"),
            "wrong_initial_type": field("initialTypeId", "type-article"),
            "missing_type": lambda f: f["typeSwitch"]["types"].pop("research"),
            "extra_type": lambda f: f["typeSwitch"]["types"].update(page={}),
            "foreign_type": choice("id", "another-type"),
            "duplicate_label": choice("label", "Chiddush"),
            "empty_type_label": choice("label", ""),
            "missing_section": choice("sectionId", ""),
            "numeric_expansion": choice("sectionExpandable", 1),
            "empty_expandable_title": choice("sectionExpandable", True),
            "unknown_choice_field": choice("selectedByFixture", True),
            "missing_value": lambda f: f["typeSwitch"]["values"].pop(),
            "extra_value": lambda f: f["typeSwitch"]["values"].append({}),
            "reordered_values": lambda f: f["typeSwitch"]["values"].reverse(),
            "wrong_kind": association(0, "kind", "topic"),
            "source_from_set": association(0, "canonicalKey", "Genesis 1:1"),
            "word_placeholder": association(2, "label", "Select options"),
            "wrong_property": association(1, "propertyName", "מקור/ות"),
            "reused_property_key": association(1, "propertyKey", "native-ref"),
            "reused_canonical_identity": association(1, "identity", "canonical-ref"),
            "empty_identity": association(2, "identity", ""),
            "unknown_value_field": association(0, "passed", True),
            "missing_readback": field("nativeReadback", None),
            "foreign_readback_object": readback("objectId", "writing-chiddush"),
            "foreign_readback_space": readback("spaceId", "other-space"),
            "wrong_readback_type": readback("typeId", "type-research"),
            "no_native_call": readback("method", "Fixture"),
            "empty_canonical": readback("canonicalNonempty", False),
            "numeric_canonical": readback("canonicalNonempty", 1),
            "missing_projections": readback("projections", {}),
            "wrong_projection": lambda f: f["typeSwitch"]["nativeReadback"]["projections"].update({"native-word": ["other"]}),
            "extra_projection": lambda f: f["typeSwitch"]["nativeReadback"]["projections"].update({"extra": ["other"]}),
            "unknown_readback_field": readback("accepted", True),
        }
        for name, change in changes.items():
            for lane in ["properties", "properties-set"]:
                with self.subTest(change=name, lane=lane):
                    fixture = self.source_header_fixture()
                    change(fixture)
                    with self.assertRaisesRegex(ValueError, "Type-switch"):
                        fixture_environment(lane, fixture, "en")

    def test_missing_native_preparation_output_is_not_a_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "one actual"):
                property_environment(Path(directory), "expected")


if __name__ == "__main__":
    unittest.main()
