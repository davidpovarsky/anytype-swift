#!/usr/bin/env python3
"""Three new host controls for this candidate only; no Xcode/native/UI execution."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import plistlib
import tempfile
import unittest

import native_ui_transition_contract as contract
import native_ui_transition_project as project

ROOT = Path(__file__).resolve().parents[2]


class NativeUITransitionCandidateControls(unittest.TestCase):
    def test_project_projection_builds_only_ui_sources(self):
        pbx = (ROOT / "NativeApp/AnyNative.xcodeproj/project.pbxproj").read_bytes()
        scheme = (ROOT / "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme").read_bytes()
        launch = (ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
        history = (ROOT / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes()
        self.assertEqual(contract.sha(launch), contract.SWIFT_SHA)
        with tempfile.TemporaryDirectory(prefix="owned-native-ui-projection-") as raw:
            directory = Path(raw).resolve() / "source"
            result = project.generate(directory, original_project=pbx, original_scheme=scheme,
                                      launch_source=launch, expected_launch_sha256=contract.SWIFT_SHA,
                                      history_source=history)
            self.assertEqual(result["testsExecuted"], 0)
            self.assertEqual(result["applicationBuilds"], 0)
            self.assertEqual(result["nativeLibraryBuilds"], 0)
            self.assertEqual(len(result["generatedInputs"]), 4)
            generated = (directory / project.PROJECT_NAME / "project.pbxproj").read_text()
            self.assertEqual(generated.count("isa = PBXNativeTarget;"), 1)
            self.assertNotIn("PinkhaAnyNativeApp", generated)
            self.assertNotIn("PBXTargetDependency", generated)
            self.assertNotIn("XCSwiftPackageProductDependency", generated)
            self.assertIn("packageReferences = ();", generated)
            self.assertIn('TEST_TARGET_NAME = "";', generated)
            self.assertIn('buildImplicitDependencies="NO"', (
                directory / project.PROJECT_NAME / "xcshareddata/xcschemes" /
                (project.SCHEME_NAME + ".xcscheme")).read_text())
            self.assertEqual((directory / "UITests/NativeLaunchTests.swift").read_bytes(), launch)
            self.assertEqual((directory / "UITests/NativeHistoryTests.swift").read_bytes(), history)
            with self.assertRaises(ValueError):
                project.generate(directory, original_project=pbx, original_scheme=scheme,
                                 launch_source=launch, expected_launch_sha256=contract.SWIFT_SHA,
                                 history_source=history)
        for label, altered in (("project", pbx + b"\n"), ("scheme", scheme + b"\n")):
            with self.subTest(kind=label), self.assertRaises(ValueError):
                if label == "project":
                    project.project_bytes(altered)
                else:
                    project.scheme_bytes(altered)

    def test_descriptor_and_enumeration_bind_original_app_and_five_only(self):
        with tempfile.TemporaryDirectory(prefix="owned-native-ui-composition-") as raw:
            base = Path(raw).resolve()
            products = base / "new-runner/Build/Products"
            app = base / "original-products/PinkhaAnyNative.app"
            products.mkdir(parents=True)
            app.mkdir(parents=True)
            target = {
                "IsUITestBundle": True,
                "TestHostPath": "__TESTROOT__/Debug-iphonesimulator/" + contract.TARGET + "-Runner.app",
                "TestBundlePath": "__TESTHOST__/PlugIns/" + contract.TARGET + ".xctest",
                "TestingEnvironmentVariables": {"UNCHANGED_TEST_VALUE": "original-fresh-descriptor"},
            }
            value = {"__xctestrun_metadata__": {"FormatVersion": 1}, contract.TARGET: target}
            original = plistlib.dumps(value)
            for stage in contract.STAGES:
                with self.subTest(stage=stage):
                    copied, proof = contract.descriptor_bytes(original, products=products, original_app=app, stage=stage)
                    actual = plistlib.loads(copied)
                    self.assertEqual(actual[contract.TARGET]["UITargetAppPath"], str(app))
                    self.assertEqual(actual[contract.TARGET]["UITargetAppBundleIdentifier"], contract.APP_BUNDLE)
                    self.assertEqual(actual[contract.TARGET]["OnlyTestIdentifiers"], list(contract.STAGES[stage][2]))
                    self.assertEqual(actual[contract.TARGET]["TestingEnvironmentVariables"],
                                     target["TestingEnvironmentVariables"])
                    self.assertTrue(proof["exactInverse"])
                    selected = [contract.TARGET + "/" + name + "()" for name in contract.STAGES[stage][2]]
                    payload = {"errors": [], "values": [{"testPlan": "observed-v1-container",
                        "enabledTests": [{"identifier": name} for name in selected], "disabledTests": []}]}
                    enumeration = contract.exact_enumeration(payload, stage)
                    self.assertEqual(len(enumeration["enabledOriginalIdentifiers"]), len(selected))
                    plan = contract.command(stage, products / contract.COPY_NAMES[stage],
                        "4BF2948A-6EA4-472C-85D0-61F939A21E84", base / (stage + ".xcresult"))
                    enum_command = contract.enumeration_command(plan, base / "enumeration.json")
                    for argv in (plan["command"], enum_command):
                        self.assertEqual([token for token in argv if token.startswith("-only-testing:")],
                                         ["-only-testing:" + contract.TARGET + "/" + name for name in contract.STAGES[stage][2]])
                    for label, mutate in (
                        ("zero", lambda p: p["values"][0].update(enabledTests=[])),
                        ("extra", lambda p: p["values"][0]["enabledTests"].append({"identifier": contract.TARGET + "/NativeLaunchTests/testUnselected()"})),
                        ("disabled_overlap", lambda p: p["values"][0]["disabledTests"].append({"identifier": selected[0]})),
                        ("foreign_target", lambda p: p["values"][0]["enabledTests"][0].update(identifier=selected[0].replace(contract.TARGET, "ForeignTests"))),
                    ):
                        changed = copy.deepcopy(payload); mutate(changed)
                        with self.subTest(stage=stage, rejection=label), self.assertRaises(ValueError):
                            contract.exact_enumeration(changed, stage)
            for key, invalid in (
                ("UITargetAppPath", "/foreign/App.app"),
                ("DependentProductPaths", ["__TESTROOT__/ForeignApp.app"]),
                ("TestBundlePath", "__TESTROOT__/../Foreign.xctest"),
                ("OnlyTestIdentifiers", ["NativeLaunchTests/testRetainedMethod"]),
                ("SkipTestIdentifiers", [contract.ALL_METHODS[0]]),
                ("TestPlanName", "unadmitted"),
            ):
                changed = copy.deepcopy(value); changed[contract.TARGET][key] = invalid
                with self.subTest(descriptor_rejection=key), self.assertRaises(ValueError):
                    contract.descriptor_bytes(plistlib.dumps(changed), products=products, original_app=app,
                                              stage="native-ui-continuation")
            with self.assertRaises(ValueError):
                contract.descriptor_bytes(original, products=products, original_app=products / "Foreign.app",
                                          stage="archive-roundtrip")

    def test_first_failure_preserves_named_partial_results_and_never_validates(self):
        first = TimeoutError("original owned test command timeout")
        first.quiescence_observation = {"status": "FAIL", "original": True}
        cases = {contract.ALL_METHODS[0]: "Passed", contract.ALL_METHODS[1]: "Failed"}
        partial = contract.partial_named({"original": "xcresult-tree"}, lambda _: dict(cases))
        self.assertEqual(partial["actualNamedPasses"], [contract.ALL_METHODS[0]])
        self.assertEqual(partial["actualNamedNonpasses"], {contract.ALL_METHODS[1]: "Failed"})
        self.assertFalse(partial["completeStageAcceptance"])
        self.assertTrue(partial["namedOutcomesAreObservedOnly"])
        original_failure = {"type": "TimeoutError", "message": str(first),
                            "quiescence_observation": first.quiescence_observation}
        result = {"firstFailure": copy.deepcopy(original_failure), "partialNamed": partial}
        called = []
        def forbidden_validation():
            called.append(True)
            raise AssertionError("failed execution must never reach complete acceptance")
        observed, failure = contract.finish_outcome(first, [{"phase": "later-diagnostic", "type": "OSError"}],
                                                     result, validate=forbidden_validation)
        self.assertIs(failure, first)
        self.assertEqual(observed["status"], "FAIL")
        self.assertEqual(observed["firstFailure"], original_failure)
        self.assertEqual(observed["partialNamed"], partial)
        self.assertEqual(called, [])
        diagnostic_result, diagnostic_error = contract.finish_outcome(
            None, [{"phase": "missing-original-xcresult", "type": "MissingOriginalResult"}],
            {"partialNamed": partial}, validate=forbidden_validation)
        self.assertEqual(diagnostic_result["status"], "FAIL")
        self.assertIsInstance(diagnostic_error, RuntimeError)
        self.assertEqual(called, [])
        with self.assertRaises(ValueError):
            contract.exact_enumeration({"errors": [], "values": []}, "native-ui-continuation")


if __name__ == "__main__":
    raise SystemExit("Use only the separately frozen three-method controller after review.")
