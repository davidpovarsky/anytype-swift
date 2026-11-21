import unittest
import verify_native_test_execution as execution


class ExactNativeUIProfilesTests(unittest.TestCase):
    def fixture(self, profile):
        methods = sorted(execution.expected_methods(profile))
        summary = {
            "totalTestCount": len(methods), "passedTests": len(methods),
            "failedTests": 0, "skippedTests": 0,
            "devicesAndConfigurations": [{"device": {
                "deviceId": "OWNED", "osVersion": "27.2", "osBuildNumber": "24B8117",
                "architecture": "arm64", "deviceName": "owned disposable iPad"
            }}]
        }
        tree = [{"nodeType": "Test Case", "nodeIdentifier": name + "()", "result": "Passed"}
                for name in methods]
        return summary, tree

    def test_each_exact_profile_accepts_only_its_named_methods(self):
        for profile, count in (("native-ui-entry", 1), ("native-ui-followup", 7),
                               ("archive-roundtrip", 1)):
            with self.subTest(profile=profile):
                summary, tree = self.fixture(profile)
                result = execution.validate(summary, tree, profile, "OWNED")
                self.assertEqual(len(result["actualCases"]), count)

    def test_old_observation_or_onboarding_cannot_pad_exact_execution(self):
        for extra in ("testObserveCanonicalArchiveSystemPickers",
                      "testFreshNativeExecutableShowsAccountAndRecoveryEntryPoints"):
            summary, tree = self.fixture("native-ui-entry")
            tree.append({"nodeType": "Test Case",
                         "nodeIdentifier": "NativeLaunchTests/" + extra + "()", "result": "Passed"})
            summary["totalTestCount"] += 1
            summary["passedTests"] += 1
            with self.subTest(extra=extra), self.assertRaisesRegex(RuntimeError, "Unexpected tests"):
                execution.validate(summary, tree, "native-ui-entry", "OWNED")

    def test_failed_or_skipped_entry_execution_is_refused(self):
        for result, key in (("Failed", "failedTests"), ("Skipped", "skippedTests")):
            summary, tree = self.fixture("native-ui-entry")
            summary["passedTests"] = 0
            summary[key] = 1
            tree[0]["result"] = result
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                execution.validate(summary, tree, "native-ui-entry", "OWNED")

    def test_summary_case_disagreement_cannot_hide_an_extra_case(self):
        summary, tree = self.fixture("archive-roundtrip")
        tree.append({"nodeType": "Test Case",
                     "nodeIdentifier": "NativeLaunchTests/testObserveCanonicalArchiveSystemPickers()",
                     "result": "Passed"})
        with self.assertRaisesRegex(RuntimeError, "Actual case inventory"):
            execution.validate(summary, tree, "archive-roundtrip", "OWNED")


if __name__ == "__main__":
    unittest.main()
