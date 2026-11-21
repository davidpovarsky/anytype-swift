"""Ordinary simulator artifact controls; synthetic XCTest is not Apple evidence."""
import copy
import plistlib
import unittest
from unittest.mock import patch

import destination_artifacts as destination
import run_ui27 as shared
import test_type_preservation as fixtures
import type_preservation as preservation
import wave15_batch as batch


class DestinationArtifactControls(unittest.TestCase):
    def fixture(self):
        control = fixtures.PreservationControls(methodName="runTest")
        control.setUp()
        self.addCleanup(control.doCleanups)
        return control


    def supported(self):
        control = self.fixture()
        frozen = control.freeze()
        installation = control.install(frozen)
        environment = preservation.environment(frozen, installation)
        return control, frozen, installation, environment


    def test_missing_or_changed_host_test_bundle_identity_blocks_before_install(self):
        for mode in ("host-missing", "host-wrong", "test-missing", "test-wrong", "executable-wrong"):
            with self.subTest(mode=mode):
                control = self.fixture()
                frozen = control.freeze()
                metadata = (control.installed / "Info.plist" if mode.startswith("host")
                            else control.installed / destination.BUNDLE / "Info.plist")
                value = plistlib.loads(metadata.read_bytes())
                if mode in ("host-missing", "test-missing"):
                    value.pop("CFBundleIdentifier")
                elif mode == "executable-wrong":
                    value["CFBundleExecutable"] = "ForeignTests"
                else:
                    value["CFBundleIdentifier"] = "io.foreign.tests"
                metadata.write_bytes(plistlib.dumps(value))
                with self.assertRaises(ValueError):
                    control.install(frozen)
                self.assertEqual(control.capability_calls, [])
                self.assertEqual(control.install_calls, [])


    def test_missing_or_escaped_bundle_and_uninventoried_executable_are_rejected(self):
        for mode in ("missing", "external", "uninventoried", "wrong-size"):
            with self.subTest(mode=mode):
                control = self.fixture()
                carriers = control.carriers(control.built)
                bundle = control.built / destination.BUNDLE
                if mode in ("missing", "external"):
                    moved = control.root / "saved-test-bundle.xctest"
                    bundle.rename(moved)
                    if mode == "external":
                        bundle.symlink_to(moved, target_is_directory=True)
                elif mode == "uninventoried":
                    carriers["manifest"]["carriers"].clear()
                else:
                    carriers["manifest"]["carriers"][destination.EXECUTABLE]["bytes"] += 1
                with self.assertRaises(ValueError):
                    destination.test_bundle(control.built, carriers)


    def test_wrong_or_missing_native_target_identifiers_paths_and_flags_are_rejected(self):
        _, _, _, environment = self.supported()
        changes = [lambda value: value.pop("TestHostBundleIdentifier"),
                   lambda value: value.update(TestHostBundleIdentifier="io.foreign.app"),
                   lambda value: value.update(UITargetAppBundleIdentifier="io.foreign.app"),
                   lambda value: value.pop("TestBundlePath"),
                   lambda value: value.update(TestBundlePath="__TESTHOST__/PlugIns/ForeignTests.xctest"),
                   lambda value: value.update(TestBundleDestinationRelativePath="__TESTHOST__/../AnytypeTests.xctest"),
                   lambda value: value.pop("TestHostPath"),
                   lambda value: value.update(TestHostPath="__TESTROOT__/../Anytype.app"),
                   lambda value: value.update(TestHostPath="/foreign/Anytype.app"),
                   lambda value: value.update(BlueprintName="PinkhaStage1AcceptanceUITests"),
                   lambda value: value.update(IsAppHostedTestBundle=False),
                   lambda value: value.update(IsUITestBundle=True),
                   lambda value: value.pop("TestingEnvironmentVariables"),
                   lambda value: value.update(UseDestinationArtifacts=True)]
        for change in changes:
            target = fixtures.native_target(); change(target); original = copy.deepcopy(target)
            with self.subTest(change=change), self.assertRaises(ValueError):
                preservation.configure_target(target, environment)
            self.assertEqual(target, original)


    def test_batch_and_standalone_share_normal_simulator_native_configuration(self):
        control, _, _, environment = self.supported()
        original = control.root / "native.xctestrun"
        unrelated = {"BlueprintName": "OtherTests", "TestBundlePath": "__TESTROOT__/OtherTests.xctest",
                     "EnvironmentVariables": {"PINKHA_UNRELATED": "kept"}}
        target = fixtures.native_target()
        raw = plistlib.dumps({"TestConfigurations": [{"TestTargets": [target, unrelated]}]})
        original.write_bytes(raw)
        first = preservation.selected_configuration(original, environment)
        second = batch.explicit_selection(original, "AnytypeTests", [preservation.METHOD], environment, shared)
        one, two = (plistlib.loads(path.read_bytes())["TestConfigurations"][0]["TestTargets"] for path in (first, second))
        self.assertEqual(one, two)
        self.assertEqual(one[1], unrelated)
        self.assertEqual(one[0]["OnlyTestIdentifiers"], [preservation.METHOD])
        self.assertEqual(one[0]["SkipTestIdentifiers"], [])
        self.assertFalse(one[0].get("UseDestinationArtifacts", False))
        self.assertEqual(one[0]["TestHostPath"], target["TestHostPath"])
        self.assertEqual(one[0]["TestBundlePath"], target["TestBundlePath"])
        self.assertEqual(one[0]["TestingEnvironmentVariables"], target["TestingEnvironmentVariables"])
        self.assertEqual(original.read_bytes(), raw)
        self.assertEqual(first.parent, original.parent)
        self.assertEqual(second.parent, original.parent)


    def test_other_native_ui_and_sdk_selections_keep_original_install_behavior(self):
        control = self.fixture()
        cases = [("AnytypeTests", [batch.PREPARATIONS[3]], fixtures.native_target()),
                 ("AnytypeTests", ["HanlinNativeIntegrationTests/realNativeControl"], fixtures.native_target()),
                 ("PinkhaStage1AcceptanceUITests", ["PinkhaStage1AcceptanceUITests/testHanlinStreaming"],
                  {"BlueprintName": "PinkhaStage1AcceptanceUITests", "IsUITestBundle": True,
                   "TestBundlePath": "__TESTROOT__/UITests-Runner.app/PlugIns/UITests.xctest",
                   "TestHostPath": "__TESTROOT__/UITests-Runner.app",
                   "UITargetAppPath": "__TESTROOT__/Anytype.app",
                   "TestingEnvironmentVariables": {"XCODE_REQUIRED": "kept"}})]
        for index, (blueprint, methods, target) in enumerate(cases):
            with self.subTest(blueprint=blueprint, methods=methods):
                original = control.root / (str(index) + ".xctestrun")
                raw = plistlib.dumps({"TestConfigurations": [{"TestTargets": [target]}]})
                original.write_bytes(raw)
                with patch.object(preservation, "configure_target", side_effect=AssertionError("Wrong lane")):
                    selected = batch.explicit_selection(original, blueprint, methods, {}, shared)
                observed = plistlib.loads(selected.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
                expected = copy.deepcopy(target)
                expected.update(EnvironmentVariables={}, OnlyTestIdentifiers=(sorted({name.split("/")[0] for name in methods})
                    if blueprint == "AnytypeTests" else methods), SkipTestIdentifiers=[])
                self.assertEqual(observed, expected)
                self.assertNotIn("UseDestinationArtifacts", observed)
                self.assertNotIn("TestBundleDestinationRelativePath", observed)
                self.assertEqual(original.read_bytes(), raw)



if __name__ == "__main__":
    unittest.main()
