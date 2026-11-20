#!/usr/bin/env python3
"""Synthetic negative controls for the actual-xcresult acceptance gate."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
from verify_native_test_execution import PROFILES, expected_methods, validate

UDID = "01234567-89AB-CDEF-0123-456789ABCDEF"

def fixture(profile="runtime"):
    methods = sorted(expected_methods(profile))
    summary = {
        "totalTestCount": len(methods), "passedTests": len(methods),
        "failedTests": 0, "skippedTests": 0,
        "devicesAndConfigurations": [{"device": {
            "deviceId": UDID, "osVersion": "27.1", "osBuildNumber": "fixture-build",
            "architecture": "arm64", "modelName": "iPad synthetic fixture"}}],
    }
    tree = {"testNodes": [{"nodeType": "Test Case",
             "nodeIdentifier": "FixtureModule/" + name + "()", "result": "Passed"}
             for name in methods]}
    return summary, tree

class NativeExecutionGateTests(unittest.TestCase):
    def testEveryRequiredProfileAcceptsItsActualNamedShape(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                summary, tree = fixture(profile)
                self.assertEqual(set(validate(summary, tree, profile, UDID)["observedRequiredMethods"]),
                                 expected_methods(profile))

    def testZeroExecutionCannotPass(self):
        summary, tree = fixture()
        summary.update(totalTestCount=0, passedTests=0)
        with self.assertRaises(RuntimeError):
            validate(summary, tree, "runtime", UDID)

    def testSkippedOrFailedCountCannotPass(self):
        for field in ("failedTests", "skippedTests"):
            summary, tree = fixture()
            summary[field] = 1
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate(summary, tree, "runtime", UDID)

    def testUnrelatedPassingCaseCannotSubstituteForMissingMethod(self):
        summary, tree = fixture()
        tree["testNodes"][0]["nodeIdentifier"] = "FixtureModule/Other/testOther()"
        with self.assertRaises(RuntimeError):
            validate(summary, tree, "runtime", UDID)

    def testSimilarMethodSuffixCannotMasqueradeAsRequiredExecution(self):
        summary, tree = fixture()
        original = tree["testNodes"][0]["nodeIdentifier"]
        tree["testNodes"][0]["nodeIdentifier"] = original.removesuffix("()") + "NotActuallyRun()"
        with self.assertRaises(RuntimeError):
            validate(summary, tree, "runtime", UDID)

    def testDuplicateOrNonpassingNodeCannotPass(self):
        for mutation in ("duplicate", "failure"):
            summary, tree = fixture()
            if mutation == "duplicate":
                tree["testNodes"].append(copy.deepcopy(tree["testNodes"][0]))
            else:
                tree["testNodes"][0]["result"] = "Failed"
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                validate(summary, tree, "runtime", UDID)

    def testWrongDeviceOrOlderOSCannotPass(self):
        for field, value in (("deviceId", "other-run"), ("osVersion", "26.9"),
                             ("architecture", "x86_64")):
            summary, tree = fixture()
            summary["devicesAndConfigurations"][0]["device"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                validate(summary, tree, "runtime", UDID)

    def testMalformedCountsAndMultipleDestinationsCannotPass(self):
        summary, tree = fixture()
        summary["failedTests"] = False
        with self.assertRaises(RuntimeError):
            validate(summary, tree, "runtime", UDID)
        summary, tree = fixture()
        summary["devicesAndConfigurations"] *= 2
        with self.assertRaises(RuntimeError):
            validate(summary, tree, "runtime", UDID)

    def testAdditionalGenuinePassingPackageTestsRemainAllowed(self):
        summary, tree = fixture()
        summary["totalTestCount"] += 1
        summary["passedTests"] += 1
        tree["testNodes"].append({"nodeType": "Test Case",
             "nodeIdentifier": "FixtureModule/Other/testAnother()", "result": "Passed"})
        self.assertEqual(len(validate(summary, tree, "runtime", UDID)["actualCases"]), 4)

    def testEachMissingPropertyMethodFailsEvenWhenAnUnrelatedCaseKeepsCountsComplete(self):
        for name in PROFILES["ui-ios"]["AnyNativePropertyPresentationTests"]:
            summary, tree = fixture("ui-ios")
            missing = "AnyNativePropertyPresentationTests/" + name
            for node in tree["testNodes"]:
                if node["nodeIdentifier"] == "FixtureModule/" + missing + "()":
                    node["nodeIdentifier"] = "FixtureModule/UnrelatedPropertyTests/notTheRequiredMethod()"
                    break
            else:
                self.fail("Required property method was not in the synthetic fixture")
            with self.subTest(missing=missing), self.assertRaisesRegex(RuntimeError, missing):
                validate(summary, tree, "ui-ios", UDID)

    def testSwiftTestingUsesTypeIdentifierIndependentlyOfHumanSuiteDisplayName(self):
        summary, tree = fixture("ui-ios")
        ordinary, properties = [], []
        for node in tree["testNodes"]:
            if "/AnyNativePropertyPresentationTests/" in node["nodeIdentifier"]:
                # Actual archived d58 Swift Testing nodes have Type/method(),
                # even when their enclosing suite uses a human display name.
                node["nodeIdentifier"] = node["nodeIdentifier"].removeprefix("FixtureModule/")
                properties.append(node)
            else:
                ordinary.append(node)
        tree["testNodes"] = ordinary + [{
            "nodeType": "Test Suite", "name": "Native property presentation ordering",
            "result": "Passed", "children": properties}]
        self.assertEqual(set(validate(summary, tree, "ui-ios", UDID)["observedRequiredMethods"]),
                         expected_methods("ui-ios"))
        for node in properties:
            node["nodeIdentifier"] = node["nodeIdentifier"].replace(
                "AnyNativePropertyPresentationTests/", "Native property presentation ordering/")
        with self.assertRaisesRegex(RuntimeError, "Missing required named execution"):
            validate(summary, tree, "ui-ios", UDID)


    def testEachNewHostedMethodMustExecuteEvenIfOtherPassingCasesFillItsCount(self):
        for suite in ("NativeDocumentPublicationTests", "NativePropertyWorkflowTests"):
            for name in PROFILES["application"][suite]:
                summary, tree = fixture("application")
                missing = suite + "/" + name
                for node in tree["testNodes"]:
                    if node["nodeIdentifier"] == "FixtureModule/" + missing + "()":
                        node["nodeIdentifier"] = "FixtureModule/OtherHostedTests/notTheRequiredMethod()"
                        break
                else:
                    self.fail("Required hosted method was not in the synthetic fixture")
                with self.subTest(missing=missing), self.assertRaisesRegex(RuntimeError, missing):
                    validate(summary, tree, "application", UDID)


    def testRequiredHanlinCannotBeReplacedByPassingPickerObservation(self):
        summary, tree = fixture("native-ui")
        missing = "NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen"
        replacement = "NativeLaunchTests/testObserveCanonicalArchiveSystemPickers"
        for node in tree["testNodes"]:
            if node["nodeIdentifier"] == "FixtureModule/" + missing + "()":
                node["nodeIdentifier"] = "FixtureModule/" + replacement + "()"
                break
        else:
            self.fail("Required Hanlin method is missing from the synthetic fixture")
        with self.assertRaisesRegex(RuntimeError, missing):
            validate(summary, tree, "native-ui", UDID)

    def testPickerObservationCannotBeSatisfiedByBusinessMethods(self):
        observation = expected_methods("archive-picker-observation")
        self.assertEqual(observation, {"NativeLaunchTests/testObserveCanonicalArchiveSystemPickers"})
        self.assertTrue(observation.isdisjoint(expected_methods("native-ui")))
        summary, tree = fixture("native-ui")
        with self.assertRaisesRegex(RuntimeError, "Missing required named execution"):
            validate(summary, tree, "archive-picker-observation", UDID)
        summary["totalTestCount"] += 1
        summary["passedTests"] += 1
        tree["testNodes"].append({"nodeType": "Test Case",
            "nodeIdentifier": "FixtureModule/" + next(iter(observation)) + "()", "result": "Passed"})
        self.assertEqual(set(validate(summary, tree, "native-ui", UDID)["observedRequiredMethods"]),
                         expected_methods("native-ui"))
        self.assertEqual(set(validate(summary, tree, "archive-picker-observation", UDID)["observedRequiredMethods"]),
                         observation)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(NativeExecutionGateTests))
    gate = Path(__file__).with_name("verify_native_test_execution.py")
    record = {"schemaVersion": 1, "status": "PASS" if result.wasSuccessful() else "FAIL",
        "scope": "synthetic_xcresult_gate_controls", "actualAppleExecution": False,
        "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "requiredProfileMethods": {name: len(expected_methods(name)) for name in PROFILES},
        "gateSHA256": hashlib.sha256(gate.read_bytes()).hexdigest(),
        "runnerSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "output": stream.getvalue()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
