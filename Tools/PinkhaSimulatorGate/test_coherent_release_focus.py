"""Bounded admission controls for the coherent union's original F4 selection."""
import copy
import plistlib
from pathlib import Path
import tempfile
import unittest

import coherent_release_focus as focus
import coherent_test_diagnostics as diagnostics


class CoherentFocusControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.products = Path(self.temporary.name).resolve()
        self.app = self.products / "Release-Anytype-iphonesimulator/Anytype.app"
        (self.app / "PlugIns/AnytypeTests.xctest").mkdir(parents=True)
        self.value = {
            "__xctestrun_metadata__": {"FormatVersion": 2},
            "TestConfigurations": [{
                "Name": "AnytypeTests", "IsEnabled": True, "TestTargets": [{
                    "BlueprintName": "AnytypeTests",
                    "TestHostPath": "__TESTROOT__/Release-Anytype-iphonesimulator/Anytype.app",
                    "TestBundlePath": "__TESTHOST__/PlugIns/AnytypeTests.xctest",
                    "OnlyTestIdentifiers": sorted(focus.UNION),
                    "SkipTestIdentifiers": [],
                    "EnvironmentVariables": {"RETAINED_FIXTURE": "unchanged"},
                    "CommandLineArguments": ["-AppleLanguages", "(he)"],
                    "TestLanguage": "he", "TestRegion": "IL",
                    "MainThreadCheckerEnabled": True
                }]
            }]
        }

    def tearDown(self):
        self.temporary.cleanup()

    def scoped(self, stage="return-controls"):
        return focus.scope_descriptor(plistlib.dumps(self.value), stage, self.products)

    def test_exact_union_scopes_only_original_three_and_one(self):
        raw_original = plistlib.dumps(self.value)
        for stage in focus.STAGES:
            with self.subTest(stage=stage):
                raw, proof = self.scoped(stage)
                scoped = plistlib.loads(raw)
                self.assertEqual(focus.target(scoped)["OnlyTestIdentifiers"],
                                 focus.c.selected_identifiers(focus.PROFILE, stage))
                focus.target(scoped)["OnlyTestIdentifiers"] = sorted(focus.UNION)
                self.assertEqual(scoped, self.value)
                self.assertEqual(proof["originalSHA256"], focus.c.sha(raw_original))
                self.assertTrue(proof["exactInverse"])

    def test_missing_extra_empty_and_duplicate_unions_are_rejected(self):
        original = sorted(focus.UNION)
        for changed in (original[:-1], original + ["ForeignSuite"], [], original[:-1] + [original[0]]):
            with self.subTest(selection=changed):
                focus.target(self.value)["OnlyTestIdentifiers"] = changed
                with self.assertRaises(ValueError):
                    self.scoped()

    def test_extra_native_target_and_disabled_target_are_rejected(self):
        value = copy.deepcopy(self.value)
        self.value["TestConfigurations"][0]["TestTargets"].append(copy.deepcopy(focus.target(self.value)))
        with self.assertRaises(ValueError):
            self.scoped()
        self.value = value
        focus.target(self.value)["IsEnabled"] = False
        with self.assertRaises(ValueError):
            self.scoped()

    def test_skip_filters_and_outside_host_cannot_hide_a_missing_case(self):
        focus.target(self.value)["SkipTestIdentifiers"] = [focus.c.RETURN[0]]
        with self.assertRaises(ValueError):
            self.scoped()
        focus.target(self.value)["SkipTestIdentifiers"] = []
        focus.target(self.value)["TestHostPath"] = "__TESTROOT__/../Foreign.app"
        with self.assertRaises(ValueError):
            self.scoped()

    def original_build_receipt(self):
        return dict(status="SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS",
                    profile=focus.batch.COHERENT_HEART_PROFILE,
                    native_preparation_suites_built=sorted(focus.UNION)[:-1],
                    native_postflight_suites_built=sorted(focus.UNION)[-1:],
                    build_flags=focus.batch.profile_flags(focus.batch.COHERENT_HEART_PROFILE),
                    app_builds=1, ui_runner_builds=1)

    def test_xcode27_three_targets_with_omitted_filter_use_original_build_receipt(self):
        original_target = focus.target(self.value)
        del original_target["OnlyTestIdentifiers"]
        self.value["TestConfigurations"][0]["TestTargets"] = [
            dict(BlueprintName="DeepLinksTests", EnvironmentVariables={"unchanged": "one"}),
            dict(BlueprintName="AnytypeCoreTests", CommandLineArguments=["unchanged"]),
            original_target]
        original = copy.deepcopy(self.value)
        for stage in focus.STAGES:
            with self.subTest(stage=stage):
                raw, proof = focus.scope_descriptor(plistlib.dumps(original), stage, self.products,
                                                     build_receipt=self.original_build_receipt())
                result = plistlib.loads(raw)
                self.assertEqual(len(result["TestConfigurations"][0]["TestTargets"]), 1)
                selected = focus.target(result)
                self.assertEqual(selected.pop("OnlyTestIdentifiers"),
                                 focus.c.selected_identifiers(focus.PROFILE, stage))
                self.assertEqual(selected, original_target)
                self.assertEqual(self.value, original)
                self.assertEqual(proof["originalTargetCount"], 3)
                self.assertFalse(proof["originalSelectionPresent"])
                self.assertEqual(proof["unionAuthority"], "frozen_build_receipt")
                self.assertTrue(proof["exactInverse"])

    def test_omitted_filter_requires_successful_exact_build_without_skip(self):
        del focus.target(self.value)["OnlyTestIdentifiers"]
        receipt = self.original_build_receipt()
        for changed in (None, {}, dict(receipt, status="FAILED"),
                        dict(receipt, native_preparation_suites_built=[]),
                        dict(receipt, ui_runner_builds=2),
                        dict(receipt, build_flags=["foreign"])):
            with self.subTest(receipt=changed):
                with self.assertRaises(ValueError):
                    focus.scope_descriptor(plistlib.dumps(self.value), "return-controls",
                                           self.products, build_receipt=changed)
        focus.target(self.value)["SkipTestIdentifiers"] = [focus.c.RETURN[0]]
        with self.assertRaises(ValueError):
            focus.scope_descriptor(plistlib.dumps(self.value), "return-controls",
                                   self.products, build_receipt=receipt)

    def test_original_f_selectors_remain_suffixed_and_exact(self):
        raw, _ = self.scoped()
        self.assertEqual(len(focus.target(plistlib.loads(raw))["OnlyTestIdentifiers"]), 3)
        command = focus.c.test_command(focus.PROFILE, "return-controls", self.products / "copy.xctestrun",
            "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", self.products / "result.xcresult")
        expected = ["-only-testing:AnytypeTests/" + method + "()" for method in focus.c.RETURN]
        self.assertEqual([x for x in command if x.startswith("-only-testing:")], expected)

    def test_planned_pair_uses_exact_f_runtime_and_new_run_names(self):
        spec = focus.c.PROFILES[focus.PROFILE]
        inventory = {"runtimes": [{"identifier": spec["runtime"], "version": spec["version"],
                     "buildversion": spec["build"], "isAvailable": True,
                     "supportedDeviceTypes": [spec["device"]]}],
                     "devicetypes": [{"identifier": spec["device"], "name": "original F device"}]}
        devices = focus.planned_devices(inventory, "a" * 32, "123")
        self.assertEqual([d["lane"] for d in devices], list(focus.KEYS))
        self.assertEqual(len({d["name"] for d in devices}), 2)
        inventory["runtimes"][0]["buildversion"] = "foreign"
        with self.assertRaises(RuntimeError):
            focus.planned_devices(inventory, "a" * 32, "123")

    def test_builds_and_enumeration_are_not_modified_by_diagnostic_policy(self):
        for command in (["xcodebuild", "build-for-testing"],
                        ["xcodebuild", "test-without-building", "-enumerate-tests"],
                        ["xcrun", "xcresulttool", "get", "test-results", "summary"]):
            self.assertEqual(diagnostics.never(command), command)

    def test_policy_is_idempotent_and_rejects_conflicting_collection(self):
        command = ["xcodebuild", "test-without-building", "-only-testing:AnytypeTests/Original()"]
        selected = diagnostics.never(command)
        self.assertEqual(selected[:-2], command)
        self.assertEqual(selected[-2:], ["-collect-test-diagnostics", "never"])
        self.assertEqual(diagnostics.never(selected), selected)
        with self.assertRaises(ValueError):
            diagnostics.never(command + ["-collect-test-diagnostics", "on-failure"])
        with self.assertRaises(ValueError):
            diagnostics.never(selected + ["-collect-test-diagnostics", "never"])

    def test_pair_adapter_preserves_real_return_and_all_other_arguments(self):
        class Original:
            FLAGS = ["exact retained compile flags"]
            def run_logged(self, *args, **kwargs):
                self.observed = (args, kwargs)
                return "original result", "original log"
        original = Original()
        pair = diagnostics.Pair(original)
        argv = ["xcodebuild", "test-without-building", "-resultBundlePath", "owned.xcresult"]
        result = pair.run_logged(argv, "cwd", "evidence", "test", 300, check=False)
        self.assertEqual(result, ("original result", "original log"))
        self.assertEqual(pair.FLAGS, original.FLAGS)
        self.assertEqual(original.observed,
                         ((diagnostics.never(argv), "cwd", "evidence", "test", 300), {"check": False}))
        self.assertEqual(argv[-1], "owned.xcresult")


if __name__ == "__main__":
    unittest.main()
