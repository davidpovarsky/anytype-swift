"""Portable synthetic controller controls, not Apple/native/UI acceptance."""
import copy
import unittest

import torah_ui_profile as profile


class TorahUIProfileControls(unittest.TestCase):
    def fixture(self, lane="quote-drop", language="en"):
        udid = "01234567-89AB-CDEF-0123-456789ABCDEF"
        binding = {"sourceSHA": "1" * 40, "runID": "42", "runAttempt": "1", "nonce": "a" * 32}
        admission = {"schema": "pinkha-combined-host-acceptance-admission-v1", "executionEnvironment": "SentinelX-owned-Mac",
                     "sourceCommit": binding["sourceSHA"], "appLanguage": language, "deviceType": "synthetic-iphone",
                     "deviceFamily": "iphone"}
        native = {"spaceId": "synthetic-space", "universalDocuments": {"page": "synthetic-page"},
                  "manySourcesDocument": "synthetic-source"}
        ui = {"PINKHA_NATIVE_UI_DISPOSABLE": "1", "PINKHA_NATIVE_UI_FIXTURE_JSON": profile.encode(native).decode(),
              "PINKHA_UI27_APP_LANGUAGE": language, "PINKHA_UI27_SELECTION_SCOPE": "WAVE15_ACCEPTANCE"}
        console = None
        if lane in {"inspector", "inspector-search"}:
            ui["PINKHA_UI27_EXPECTED_APP_PID"] = "12345"
        if lane in {"canonical-properties", "editor"}:
            native = {"spaceId": "synthetic-space", "pinkhaObjectId": "synthetic-pinkha", "noteObjectId": "synthetic-note",
                      "pageObjectId": "synthetic-page"}
            ui.pop("PINKHA_NATIVE_UI_DISPOSABLE")
            ui.pop("PINKHA_NATIVE_UI_FIXTURE_JSON")
        if lane == "editor":
            ui.update(PINKHA_ACCEPTANCE_SPACE_ID=native["spaceId"], PINKHA_ACCEPTANCE_PINKHA_ID=native["pinkhaObjectId"],
                      PINKHA_ACCEPTANCE_NOTE_ID=native["noteObjectId"], PINKHA_ACCEPTANCE_PAGE_ID=native["pageObjectId"],
                      PINKHA_ACCEPTANCE_DIRECTION="rtl" if language == "he" else "ltr",
                      PINKHA_ACCEPTANCE_DEVICE_LANGUAGE="en" if language == "he" else "he")
        if lane == "canonical-properties":
            ui.update(PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED="1", PINKHA_PROPERTIES_SPACE_ID="synthetic-space",
                      PINKHA_PROPERTIES_CHIDDUSH_ID="synthetic-chiddush", PINKHA_PROPERTIES_ARTICLE_ID="synthetic-article",
                      PINKHA_PROPERTIES_RESEARCH_ID="synthetic-research")
            ui["PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS"] = '{"synthetic-chiddush":["Name"],"synthetic-article":["Name"],"synthetic-research":["Name"]}'
            properties = {key: value for key, value in ui.items() if key.startswith("PINKHA_PROPERTIES_")}
            console = b"Synthetic original console\nPINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON " + profile.encode(properties) + b"\n"
        method = profile.STARTUP_LANES[lane]["preparation"]
        prepared = {"status": "PASS", "testInvoked": True, "selected": [method], "command_exit_code": 0,
                    "passed": 1, "failed": 0, "skipped": 0,
                    "actual_devices": [{"deviceId": udid, "platform": "iOS Simulator"}],
                    "installedOriginalCode": {"codeCarriersSHA256": "d" * 64}}
        invocation = {"binding": binding, "argv": ["xcodebuild", "test-without-building", "-destination",
                      "platform=iOS Simulator,id=" + udid, "-only-testing:AnytypeTests/" + method + "()"]}
        owned = {"udid": udid, "name": "F-Combined-" + binding["nonce"] + "-" + lane,
                 "deviceType": admission["deviceType"], "deviceFamily": admission["deviceFamily"]}
        return dict(lane=lane, fixture_raw=profile.encode(native), ui_environment=ui, preparation_raw=profile.encode(prepared),
                    invocation_raw=profile.encode(invocation), admission_raw=profile.encode(admission),
                    owned_simulator_raw=profile.encode(owned), binding=binding, udid=udid, token="b" * 32,
                    code_carriers_sha256="d" * 64, canonical_console_raw=console)

    def test_six_lanes_bind_exact_original_bytes_without_native_echo(self):
        for lane in profile.LANES:
            with self.subTest(lane=lane):
                arguments = self.fixture(lane)
                before = copy.deepcopy(arguments)
                environment = profile.startup_environment(**arguments)
                actual = profile.validate_startup_environment(environment, lane=lane, expected_space="synthetic-space")
                self.assertEqual(arguments, before)
                self.assertEqual(actual["provenance"], profile.PROVENANCE)
                self.assertEqual(actual["fixtureSHA256"], profile.sha(arguments["fixture_raw"]))
                self.assertNotIn("sourceSHA", profile.decode(arguments["fixture_raw"]))

    def test_failed_skipped_foreign_or_uninvoked_preparation_is_rejected(self):
        changes = [{"status": "FAIL"}, {"testInvoked": False}, {"selected": ["Foreign/method"]},
                   {"command_exit_code": 65}, {"passed": 0, "failed": 1}, {"skipped": 1},
                   {"actual_devices": [{"deviceId": "foreign", "platform": "iOS Simulator"}]},
                   {"installedOriginalCode": {"codeCarriersSHA256": "e" * 64}}]
        for change in changes:
            with self.subTest(change=change):
                arguments = self.fixture()
                original = profile.decode(arguments["preparation_raw"])
                arguments["preparation_raw"] = profile.encode({**original, **change})
                with self.assertRaises(ValueError): profile.startup_environment(**arguments)

    def test_source_run_owned_device_and_original_invocation_must_match(self):
        for key, change in [
            ("admission_raw", {"sourceCommit": "2" * 40}),
            ("admission_raw", {"appLanguage": "he"}),
            ("owned_simulator_raw", {"name": "reused-unowned-device"}),
            ("owned_simulator_raw", {"udid": "11234567-89AB-CDEF-0123-456789ABCDEF"}),
            ("invocation_raw", {"binding": {}}),
            ("invocation_raw", {"argv": ["xcodebuild", "test-without-building"]}),
        ]:
            with self.subTest(key=key, change=change):
                arguments = self.fixture()
                arguments[key] = profile.encode({**profile.decode(arguments[key]), **change})
                with self.assertRaises(ValueError): profile.startup_environment(**arguments)

    def test_changed_envelope_or_original_fixture_environment_is_rejected(self):
        pristine = profile.startup_environment(**self.fixture())
        changes = [{profile.PREFIX + "SOURCE_SHA": "2" * 40}, {profile.PREFIX + "RUN_ID": "43"},
                   {profile.PREFIX + "TOKEN": "c" * 32}, {profile.PREFIX + "FIXTURE_SHA256": "e" * 64},
                   {profile.PREFIX + "BINDING_JSON": ""}, {"PINKHA_NATIVE_UI_DISPOSABLE": "0"},
                   {"PINKHA_NATIVE_UI_FIXTURE_JSON": '{"spaceId":"foreign-space"}'}]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    profile.validate_startup_environment({**pristine, **change}, lane="quote-drop", expected_space="synthetic-space")
        with self.assertRaises(ValueError):
            profile.validate_startup_environment(pristine, lane="inspector", expected_space="synthetic-space")
        with self.assertRaises(ValueError):
            profile.validate_startup_environment(pristine, lane="quote-drop", expected_space="foreign-space")
        envelope = profile.decode(pristine[profile.PREFIX + "BINDING_JSON"])
        envelope["fixtureBase64"] = "e30="
        with self.assertRaises(ValueError):
            profile.validate_startup_environment({**pristine, profile.PREFIX + "BINDING_JSON": profile.encode(envelope).decode()},
                                                 lane="quote-drop", expected_space="synthetic-space")

    def test_inspector_requires_mapped_process_and_canonical_requires_three_writing_types(self):
        for lane in ("inspector", "inspector-search"):
            arguments = self.fixture(lane)
            arguments["ui_environment"].pop("PINKHA_UI27_EXPECTED_APP_PID")
            with self.assertRaises(ValueError): profile.startup_environment(**arguments)
        for change in [{"PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED": "0"},
                       {"PINKHA_PROPERTIES_SPACE_ID": "foreign-space"},
                       {"PINKHA_PROPERTIES_ARTICLE_ID": "synthetic-chiddush"}]:
            arguments = self.fixture("canonical-properties")
            arguments["ui_environment"].update(change)
            with self.assertRaises(ValueError): profile.startup_environment(**arguments)

    def test_unknown_lane_prior_binding_duplicate_json_and_wrong_scope_fail(self):
        for change in [{"lane": "t5-native-ui"}, {"fixture_raw": b'{"spaceId":"a","spaceId":"b"}'}]:
            with self.assertRaises(ValueError): profile.startup_environment(**{**self.fixture(), **change})
        for change in [{profile.PREFIX + "TOKEN": "c" * 32}, {"PINKHA_NATIVE_UI_DISPOSABLE": "0"},
                       {"PINKHA_UI27_APP_LANGUAGE": "he"}]:
            arguments = self.fixture()
            arguments["ui_environment"].update(change)
            with self.assertRaises(ValueError): profile.startup_environment(**arguments)

    def test_canonical_ids_require_the_original_native_console_marker(self):
        arguments = self.fixture("canonical-properties")
        for console in (None, b"no native marker", b'PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON {"PINKHA_PROPERTIES_SPACE_ID":"foreign"}'):
            with self.subTest(console=console):
                with self.assertRaises(ValueError):
                    profile.startup_environment(**{**arguments, "canonical_console_raw": console})
        changed = copy.deepcopy(arguments)
        changed["ui_environment"]["PINKHA_PROPERTIES_ARTICLE_ID"] = "unobserved-writing-id"
        with self.assertRaises(ValueError): profile.startup_environment(**changed)
        result = profile.startup_environment(**arguments)
        self.assertEqual(result[profile.PREFIX + "CANONICAL_CONSOLE_SHA256"], profile.sha(arguments["canonical_console_raw"]))

    def test_editor_two_app_languages_bind_exact_native_ids_and_opposite_device_language(self):
        for language in ("en", "he"):
            with self.subTest(language=language):
                arguments = self.fixture("editor", language)
                original = arguments["fixture_raw"]
                environment = profile.startup_environment(**arguments)
                actual = profile.validate_startup_environment(environment, lane="editor", expected_space="synthetic-space")
                self.assertEqual(actual["fixtureSHA256"], profile.sha(original))
                self.assertEqual(actual["canonicalPreparationConsoleSHA256"], "")
                self.assertEqual(environment["PINKHA_ACCEPTANCE_DEVICE_LANGUAGE"], "en" if language == "he" else "he")

    def test_editor_rejects_foreign_ids_direction_same_language_or_non_disposable_scope(self):
        for language in ("en", "he"):
            for change in [{"PINKHA_ACCEPTANCE_SPACE_ID": "foreign-space"}, {"PINKHA_ACCEPTANCE_NOTE_ID": "foreign-note"},
                           {"PINKHA_ACCEPTANCE_DIRECTION": "ltr" if language == "he" else "rtl"},
                           {"PINKHA_ACCEPTANCE_DEVICE_LANGUAGE": language}, {"PINKHA_NATIVE_UI_DISPOSABLE": "0"}]:
                with self.subTest(language=language, change=change):
                    arguments = self.fixture("editor", language)
                    arguments["ui_environment"].update(change)
                    with self.assertRaises(ValueError): profile.startup_environment(**arguments)
        arguments = self.fixture("editor")
        with self.assertRaises(ValueError):
            profile.startup_environment(**{**arguments, "canonical_console_raw": b"foreign canonical console"})

    def test_editor_app_language_must_match_the_admitted_product_selection(self):
        arguments = self.fixture("editor", "he")
        admission = profile.decode(arguments["admission_raw"])
        admission["appLanguage"] = "en"
        arguments["admission_raw"] = profile.encode(admission)
        with self.assertRaises(ValueError): profile.startup_environment(**arguments)


if __name__ == "__main__":
    unittest.main()
