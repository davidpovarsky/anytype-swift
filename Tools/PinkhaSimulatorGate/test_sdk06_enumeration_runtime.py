"""New controls for original descriptor portability and bounded host startup."""
import copy
from pathlib import Path
import plistlib
import tempfile
import unittest

import sdk06_enumeration_probe as probe


def runtime(root):
    mounted = root / "runtime/Contents/Resources/RuntimeRoot"
    library = mounted / "usr/lib/libMainThreadChecker.dylib"
    library.parent.mkdir(parents=True)
    library.write_bytes(b"\xcf\xfa\xed\xfe" + b"actual-current-runtime-control")
    return {"isAvailable": True, "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-2",
            "supportedArchitectures": ["arm64"], "runtimeRoot": str(mounted),
            "version": "27.2", "buildversion": "24B8117"}, library


def descriptor(root):
    original = root / "original.xctestrun"
    target = {
        "BlueprintName": "AnytypeTests", "IsEnabled": True,
        "TestHostPath": "__TESTROOT__/Anytype.app",
        "TestBundlePath": "__TESTHOST__/PlugIns/AnytypeTests.xctest",
        "EnvironmentVariables": {"DYLD_INSERT_LIBRARIES": "/usr/lib/libRPAC.dylib", "PRESERVE": "value"},
        "TestingEnvironmentVariables": {
            "DYLD_INSERT_LIBRARIES": "__TESTHOST__/Frameworks/libXCTestBundleInject.dylib:"
                + probe.ORIGINAL_MAIN_THREAD_CHECKER + ":/usr/lib/libRPAC.dylib",
            "DYLD_FRAMEWORK_PATH": "__TESTROOT__:__PLATFORMS__",
            "OTHER_INJECTION": "original-value"},
        "OnlyTestIdentifiers": [], "SkipTestIdentifiers": ["Existing/disabled()"],
        "CommandLineArguments": ["--unchanged"],
    }
    value = {"__xctestrun_metadata__": {"FormatVersion": 2},
             "TestConfigurations": [{"Name": "Original", "IsEnabled": True,
                                     "TestTargets": [target, {"BlueprintName": "OtherTests"}]}]}
    original.write_bytes(plistlib.dumps(value, sort_keys=False))
    return original, target


class RuntimeInjectionControls(unittest.TestCase):
    def test_copy_relocates_only_one_exact_library_and_keeps_original_and_other_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual, library = runtime(root)
            original, target = descriptor(root)
            before = original.read_bytes()
            candidate = root / "probe.xctestrun"
            variant = dict(include=["AnytypeTests/Suite/method(value:)"], exclude=[], cli=[])
            receipt = probe.copied_configuration(original, candidate, variant, runtime=actual)
            copied = plistlib.loads(candidate.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
            self.assertEqual(original.read_bytes(), before)
            self.assertEqual(copied["EnvironmentVariables"], target["EnvironmentVariables"])
            old_testing = copy.deepcopy(target["TestingEnvironmentVariables"])
            old_testing["DYLD_INSERT_LIBRARIES"] = old_testing["DYLD_INSERT_LIBRARIES"].replace(
                probe.ORIGINAL_MAIN_THREAD_CHECKER, str(library.resolve()))
            self.assertEqual(copied["TestingEnvironmentVariables"], old_testing)
            self.assertEqual(copied["CommandLineArguments"], target["CommandLineArguments"])
            self.assertEqual(copied["SkipTestIdentifiers"], target["SkipTestIdentifiers"])
            self.assertEqual(receipt["runtime_injection"]["library_sha256"], probe.sha(library))
            self.assertEqual(receipt["original_sha256"], probe.sha(original))
            self.assertEqual(receipt["copied_sha256"], probe.sha(candidate))

    def test_changed_or_duplicate_original_token_is_rejected_without_rewriting_other_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); actual, _ = runtime(root); _, base = descriptor(root)
            original = base["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"]
            for changed in (original.replace("DPYuL8", "another-mount"),
                            original + ":" + probe.ORIGINAL_MAIN_THREAD_CHECKER,
                            original + ":/elsewhere/libMainThreadChecker.dylib"):
                target = copy.deepcopy(base)
                target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = changed
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    probe.normalize_runtime_injection(target, actual)
                self.assertEqual(target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"], changed)

    def test_unavailable_wrong_architecture_and_non_macho_runtime_library_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); actual, library = runtime(root); _, target = descriptor(root)
            for patch in ({"isAvailable": False}, {"supportedArchitectures": ["x86_64"]},
                          {"identifier": "com.apple.CoreSimulator.SimRuntime.tvOS-27-2"}):
                with self.subTest(patch=patch), self.assertRaises(ValueError):
                    probe.normalize_runtime_injection(copy.deepcopy(target), actual | patch)
            library.write_bytes(b"not-a-native-library")
            with self.assertRaises(ValueError):
                probe.normalize_runtime_injection(copy.deepcopy(target), actual)

    def test_library_symlink_outside_selected_runtime_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); actual, library = runtime(root); _, target = descriptor(root)
            outside = root / "other-runtime.dylib"
            outside.write_bytes(library.read_bytes())
            library.unlink(); library.symlink_to(outside)
            with self.assertRaises(ValueError):
                probe.normalize_runtime_injection(target, actual)

    def test_each_setup_inclusive_budget_and_whole_variant_sequence_remain_bounded(self):
        self.assertEqual(probe.enumeration_budget(2400, 0), 600)
        self.assertEqual(probe.enumeration_budget(2400, 600), 600)
        self.assertEqual(probe.enumeration_budget(2400, 2390), 10)
        for now in (2400, 2401):
            with self.subTest(now=now), self.assertRaises(ValueError):
                probe.enumeration_budget(2400, now)

    def test_relocated_descriptor_command_still_only_enumerates_original_products(self):
        command = probe.enumeration_command(Path("/owned/copy.xctestrun"),
            "67621AE7-2788-4A27-B350-21D9C1D4C4E5", Path("/owned/enumeration.json"),
            Path("/owned/result.xcresult"), {"cli": []})
        self.assertEqual(command.count("-enumerate-tests"), 1)
        self.assertIn("test-without-building", command)
        self.assertNotIn("build-for-testing", command)
        self.assertNotIn("test", command)


if __name__ == "__main__":
    unittest.main()
