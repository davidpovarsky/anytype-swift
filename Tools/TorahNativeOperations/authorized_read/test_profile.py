"""Reject missing or mismatched proof and candidate source declarations."""
import copy
import importlib.util
import re
import unittest
from pathlib import Path

from authorized_read import profile


class AuthorizedOperationReadProfileTests(unittest.TestCase):
    def events(self):
        return ([{"Action": "pass", "Test": name, "Package": package} for name, package in sorted(profile.REQUIRED)]
                + [{"Action": "pass", "Package": package} for package in sorted(profile.PACKAGES)])

    def test_source_declarations_match_exact_twenty_three_methods(self):
        root = Path(profile.__file__).resolve().parent
        found = set()
        for directory in [root / "overlay", root / "rpc/overlay"]:
            for path in directory.rglob("*_test.go"):
                package = profile.PACKAGE_ROOT + path.relative_to(directory).parent.as_posix()
                for name in re.findall(r"^func (Test\w+)\(t \*testing\.T\)", path.read_text(encoding="utf-8"), re.M):
                    if re.match(profile.TEST_PATTERN, name):
                        self.assertNotIn((name, package), found)
                        found.add((name, package))
        expected = {(name, profile.PACKAGE_ROOT + package) for package, names in profile.TOP_LEVEL.items() for name in names}
        self.assertEqual(found, expected)
        self.assertEqual(len(found), 23)
        self.assertEqual(len(profile.REQUIRED), 71)

    def test_complete_actual_records_and_packages_pass(self):
        value = profile.validate_test_events(self.events(), True)
        self.assertEqual((value["top_level_pass"], value["subcase_pass"], value["pass"]), (23, 48, 71))
        self.assertEqual(value["unchanged_prior_tests_executed"], 0)

    def test_missing_subcase_fails(self):
        events = self.events()
        events.pop(next(i for i, row in enumerate(events) if "/cancelled-after-discovery" in row.get("Test", "")))
        with self.assertRaisesRegex(ValueError, "Missing"):
            profile.validate_test_events(events, True)

    def test_duplicate_record_fails(self):
        events = self.events(); events.append(dict(events[0]))
        with self.assertRaisesRegex(ValueError, "repeated"):
            profile.validate_test_events(events, True)

    def test_failure_skip_or_exit_code_cannot_qualify(self):
        for action in ["fail", "skip"]:
            with self.subTest(action=action):
                events = self.events(); events.append({"Action": action, "Test": "unrelated", "Package": next(iter(profile.PACKAGES))})
                with self.assertRaisesRegex(ValueError, "failed/skipped"):
                    profile.validate_test_events(events, True)
        with self.assertRaisesRegex(ValueError, "failed/skipped"):
            profile.validate_test_events(self.events(), False)

    def test_wrong_native_package_fails(self):
        events = self.events(); events[0]["Package"] += "/other"
        with self.assertRaisesRegex(ValueError, "wrong-package"):
            profile.validate_test_events(events, True)

    def test_unchanged_prior_tests_are_not_part_of_candidate_selection(self):
        events = self.events(); events.append({"Action": "pass", "Test": "TestPinkhaTorahRPCSchemaAndOpaqueRequestRoundTrip", "Package": profile.PACKAGE_ROOT + "core"})
        with self.assertRaisesRegex(ValueError, "unexpected"):
            profile.validate_test_events(events, True)
        self.assertIsNone(re.match(profile.TEST_PATTERN, "TestPinkhaTorahRPCSchemaAndOpaqueRequestRoundTrip"))

    def test_package_without_terminal_success_fails(self):
        events = self.events(); events.pop()
        with self.assertRaisesRegex(ValueError, "Missing"):
            profile.validate_test_events(events, True)

    def test_source_inventory_matches_retained_baseline_and_candidate(self):
        root = Path(profile.__file__).resolve().parents[3]
        spec = importlib.util.spec_from_file_location("retained_rpc_for_profile_test", root / "Tools/TorahNativeOperations/run_native_rpc.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        rpc, registry = module.source_inputs(root, root / "Tools/TorahNativeOperations/rpc")
        source = profile.read_sources(root, rpc, registry)
        self.assertEqual(len(source["paths"]), 11)
        self.assertEqual(source["manifest"]["app_capability"], "OFF")
        forged = copy.deepcopy(rpc)
        forged["tracked"]["pb/protos/service/service.proto"]["after_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "exact retained service schema"):
            profile.read_sources(root, forged, registry)

    def test_path_traversal_absolute_and_platform_paths_are_rejected(self):
        for value in ["../secret", "/absolute", "C:/Windows", "core\\file.go"]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Unsafe"):
                profile.relative(value)


if __name__ == "__main__":
    unittest.main()
