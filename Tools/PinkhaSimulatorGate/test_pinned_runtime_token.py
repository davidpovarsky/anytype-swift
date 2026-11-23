import copy
from pathlib import Path
import tempfile
import unittest

import sdk06_enumeration_probe as probe

ORIGINAL = probe.ORIGINAL_MAIN_THREAD_CHECKER.replace("DPYuL8", "1Q2C7p")


class PinnedOriginalRuntimeTokenControls(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name) / "RuntimeRoot"
        library = root / "usr/lib/libMainThreadChecker.dylib"
        library.parent.mkdir(parents=True)
        library.write_bytes(bytes.fromhex("cffaedfe") + b"owned synthetic Mach-O")
        self.library = library.resolve()
        self.runtime = dict(isAvailable=True, identifier="com.apple.CoreSimulator.SimRuntime.iOS-27-2",
                            supportedArchitectures=["arm64"], runtimeRoot=str(root),
                            version="27.2", buildversion="24B8117")

    def target(self, token=ORIGINAL):
        return {"TestingEnvironmentVariables": {
            "DYLD_INSERT_LIBRARIES": "__TESTBUNDLE_INJECT_PATH__:" + token + ":/usr/lib/libRPAC.dylib",
            "UNCHANGED": "original"},
            "TestHostPath": "__TESTROOT__/Original.app/Original"}

    def test_explicit_pinned_token_changes_only_one_original_chain_element(self):
        target = self.target()
        original = copy.deepcopy(target)
        receipt = probe.normalize_runtime_injection(target, self.runtime, expected_original_token=ORIGINAL)
        self.assertEqual(receipt["original_token"], ORIGINAL)
        self.assertEqual(receipt["replacement_token"], str(self.library))
        restored = copy.deepcopy(target)
        restored["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = restored[
            "TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"].replace(str(self.library), ORIGINAL)
        self.assertEqual(restored, original)
        self.assertEqual(receipt["library_bytes"], self.library.stat().st_size)

    def test_default_profile_does_not_accept_another_artifacts_token(self):
        target = self.target()
        before = copy.deepcopy(target)
        with self.assertRaises(ValueError):
            probe.normalize_runtime_injection(target, self.runtime)
        self.assertEqual(target, before)

    def test_caller_pin_mismatch_or_duplicate_checker_never_mutates_target(self):
        for token in (probe.ORIGINAL_MAIN_THREAD_CHECKER, ORIGINAL + ":" + ORIGINAL):
            target = self.target(token)
            before = copy.deepcopy(target)
            with self.assertRaises(ValueError):
                probe.normalize_runtime_injection(target, self.runtime, expected_original_token=ORIGINAL)
            self.assertEqual(target, before)

    def test_unbounded_nonchecker_or_multi_token_pin_is_rejected(self):
        for token in (None, "relative/libMainThreadChecker.dylib", "/x/libOther.dylib",
                      "/x/../libMainThreadChecker.dylib", ORIGINAL + ":/another",
                      "/x/" + chr(0) + "/libMainThreadChecker.dylib",
                      "/" + "x" * 4096 + "/libMainThreadChecker.dylib"):
            target = self.target()
            before = copy.deepcopy(target)
            with self.assertRaises(ValueError):
                probe.normalize_runtime_injection(target, self.runtime, expected_original_token=token)
            self.assertEqual(target, before)


if __name__ == "__main__":
    unittest.main()
