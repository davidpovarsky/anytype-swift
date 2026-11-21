#!/usr/bin/env python3
"""Acceptance receipt regression checks: missing or failed execution cannot pass."""
import unittest
import run_native_operations as runner


class ReceiptAcceptanceTests(unittest.TestCase):
    def component_events(self):
        package = runner.MODULE + "/core/block/editor/torahops"
        return [{"Action": "pass", "Package": package, "Test": name}
                for name in runner.REQUIRED["component"]] + [{"Action": "pass", "Package": package}]

    def test_no_test_events_cannot_pass(self):
        self.assertFalse(runner.passes_suite([], "component", 0))
        self.assertFalse(runner.passes_suite([], "registration", 0))

    def test_required_native_execution_is_mandatory(self):
        events = self.component_events()
        self.assertTrue(runner.passes_suite(events, "component", 0))
        self.assertFalse(runner.passes_suite([event for event in events
                                            if event.get("Test") != "TestNativeCurrentWriteAuthority"], "component", 0))

    def test_remote_fetch_and_binding_controls_must_each_execute(self):
        names = {
            "TestNativeRemoteFetchKeepsSingleCommitGuard",
            "TestNativeRebuiltStorageRejectsForeignBinding",
            "TestNativeRebuiltStorageRejectsForeignBinding/different_ACL_instance",
            "TestNativeRebuiltStorageRejectsForeignBinding/different_root_header",
            "TestNativeRebuiltStorageRejectsForeignBinding/nested_guard",
        }
        self.assertTrue(names <= runner.REQUIRED["component"])
        events = self.component_events()
        for name in names:
            for outcome in ("missing", "fail", "skip"):
                with self.subTest(name=name, outcome=outcome):
                    changed = [event for event in events if event.get("Test") != name]
                    if outcome != "missing":
                        changed.append({"Action": outcome, "Test": name, "Package": runner.MODULE + "/core/block/editor/torahops"})
                    self.assertFalse(runner.passes_suite(changed, "component", 0))

    def test_failure_or_nonzero_exit_cannot_be_hidden_by_passes(self):
        events = self.component_events()
        self.assertFalse(runner.passes_suite(events, "component", 1))
        self.assertFalse(runner.passes_suite(events + [{"Action": "fail", "Package": "other"}], "component", 0))

    def test_lifecycle_controls_must_each_execute(self):
        markers = ("Lease", "RootCreationGuard", "RootCannotBypass")
        for suite in ("component", "registration"):
            packages = [runner.MODULE + package[1:] for package in runner.PACKAGES[suite]]
            events = [{"Action": "pass", "Package": packages[0], "Test": name}
                      for name in runner.REQUIRED[suite]]
            events += [{"Action": "pass", "Package": package} for package in packages]
            self.assertTrue(runner.passes_suite(events, suite, 0))
            required = {name for name in runner.REQUIRED[suite] if any(marker in name for marker in markers)}
            self.assertGreaterEqual(len(required), 2 if suite == "component" else 24)
            for name in required:
                for outcome in ("missing", "fail", "skip"):
                    with self.subTest(suite=suite, name=name, outcome=outcome):
                        changed = [event for event in events if event.get("Test") != name]
                        if outcome != "missing":
                            changed.append({"Action": outcome, "Test": name, "Package": packages[0]})
                        self.assertFalse(runner.passes_suite(changed, suite, 0))

    def test_each_registration_package_must_execute(self):
        packages = [runner.MODULE + package[1:] for package in runner.PACKAGES["registration"]]
        events = [{"Action": "pass", "Package": packages[0], "Test": name}
                  for name in runner.REQUIRED["registration"]]
        self.assertFalse(runner.passes_suite(events, "registration", 0))
        events += [{"Action": "pass", "Package": package} for package in packages]
        self.assertTrue(runner.passes_suite(events, "registration", 0))
        self.assertFalse(runner.passes_suite(events + [{"Action": "skip", "Package": packages[0], "Test": "TestPrivateBoundary"}], "registration", 0))

    def test_inventory_paths_cannot_escape_owned_source(self):
        for path in ["../file.go", "/file.go", "core/../../file.go", "core\\file.go"]:
            with self.assertRaises(ValueError):
                runner.safe_relative(path)


if __name__ == "__main__":
    unittest.main()
