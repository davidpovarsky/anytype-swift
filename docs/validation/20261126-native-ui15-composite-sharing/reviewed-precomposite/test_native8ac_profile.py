"""Pure admission boundary controls; no build, simulator, engine, or account."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("profile_under_control", HERE / "native8ac_profile.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
OUTPUT = Path(os.environ["PINKHA_D_PROFILE_CONTROL_OUTPUT"])
assert OUTPUT.is_absolute() and not OUTPUT.exists()
OUTPUT.mkdir(mode=0o700, parents=True)


def main_fixture():
    return {
        "fixturePurpose": "SYNTHETIC_PURE_ADMISSION_CONTROL_NOT_BUILD_EVIDENCE",
        "status": "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE",
        "sourceCommit": p.SOURCE, "sourceUnchanged": True, "testsExecuted": 0,
        "assemblyReceiptSHA256": p.ASSEMBLY, "controllerSHA256": p.PRODUCER_SHA,
        "inputs": dict(nativeSourceManifestSHA256=p.NATIVE, stagingReceiptSHA256=p.STAGING_SHA,
                       **{k: v for k, v in p.PROFILE.items() if k != "name"}),
        "app": {"exitCode": 0, "status": "PASS_BUILD_EXIT_0"},
        "ui": {"exitCode": 0, "status": "PASS_BUILD_EXIT_0"},
    }


class Native8acAdmissionControls(unittest.TestCase):
    def setUp(self):
        self.directory = OUTPUT / self._testMethodName
        self.directory.mkdir()
        helper_path = ROOT / "Tools/AnyEnginePort/native_ui_transition_project.py"
        hspec = importlib.util.spec_from_file_location("original_project_fixture", helper_path)
        helper = importlib.util.module_from_spec(hspec)
        hspec.loader.exec_module(helper)
        project, transformation = helper.project_bytes(
            (ROOT / "NativeApp/AnyNative.xcodeproj/project.pbxproj").read_bytes())
        scheme = helper.scheme_bytes((ROOT /
            "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme").read_bytes())
        files = {
            "source/" + helper.PROJECT_NAME + "/project.pbxproj": project,
            "source/" + helper.PROJECT_NAME + "/xcshareddata/xcschemes/" +
                helper.SCHEME_NAME + ".xcscheme": scheme,
            "source/UITests/NativeLaunchTests.swift":
                (ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes(),
            "source/UITests/NativeHistoryTests.swift":
                (ROOT / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes(),
        }
        for name, raw in files.items():
            dest = self.directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        self.projection = {
            "mainSourceCommit": p.SOURCE, "runnerSourceCommit": p.SOURCE,
            "current8acFixture": dict(p.FIXTURE),
            "historyKeyboardPreparation": dict(p.INTEGRATED_HISTORY),
            "reviewedInputProfile": dict(p.PROFILE),
            "changedOriginalMethodAssertions": 0, "applicationBuildTargets": 0,
            "nativeLibraryBuilds": 0, "allOriginalNativeUITestMethodsCompiled": True,
            "sourceFiles": {name: {"bytes": len(raw), "sha256": p.sha(raw)}
                            for name, raw in files.items()},
            "exactOriginalProjectAndScheme": transformation,
        }
        self.ui = {
            "sourceCommit": p.SOURCE, "runnerSourceCommit": p.SOURCE,
            "status": "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE", "testsExecuted": 0,
            "reviewedInputProfile": dict(p.PROFILE),
            "current8acFixture": dict(p.FIXTURE),
            "historyKeyboardPreparation": dict(p.INTEGRATED_HISTORY),
        }
        self.main = main_fixture()
        self.write_projection()

    def write_projection(self):
        (self.directory / "projection.json").write_text(json.dumps(self.projection))

    def test_exact_original_source_and_project_are_admitted(self):
        launch = (ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
        history = (ROOT / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes()
        self.assertEqual(p.bind_source(ROOT, self.main, p.SOURCE, launch, history, {}), p.FIXTURE)
        self.assertEqual(p.admit(ROOT, self.main, self.directory, self.ui), p.FIXTURE)

    def test_prior_native_manifest_is_refused(self):
        self.main["inputs"]["nativeSourceManifestSHA256"] = "410b" + "0" * 60
        with self.assertRaisesRegex(RuntimeError, "exact_App15_source_and_native_assembly_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_prior_sdk_marker_is_refused(self):
        self.main["inputs"]["sdkReceiptSHA256"] = "bad0" + "0" * 60
        with self.assertRaisesRegex(RuntimeError, "App15_dependency_changed:sdkReceiptSHA256"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_any_optional_source_overlay_is_refused(self):
        launch = (ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
        history = (ROOT / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes()
        for argument in p.OVERLAY_ARGUMENTS:
            with self.subTest(argument=argument):
                with self.assertRaisesRegex(RuntimeError, "without_overlays"):
                    p.bind_source(ROOT, self.main, p.SOURCE, launch, history,
                                  {argument: p.SOURCE})

    def test_changed_launch_bytes_are_refused(self):
        launch = (ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()
        history = (ROOT / "NativeApp/UITests/NativeHistoryTests.swift").read_bytes()
        with self.assertRaisesRegex(RuntimeError, "App15_all_original_NativeUI_bytes_required"):
            p.bind_source(ROOT, self.main, p.SOURCE, launch + b"\n", history, {})

    def test_missing_exact_profile_binding_is_refused(self):
        del self.projection["current8acFixture"]
        self.write_projection()
        with self.assertRaisesRegex(RuntimeError, "complete_same_source_App15_NativeUI_projection_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_compiled_history_change_is_refused(self):
        dest = self.directory / "source/UITests/NativeHistoryTests.swift"
        dest.write_bytes(dest.read_bytes() + b"\n")
        with self.assertRaisesRegex(RuntimeError, "compiled_App15_NativeUI_source_changed"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_changed_project_manifest_is_refused(self):
        key = next(k for k in self.projection["sourceFiles"] if k.endswith("project.pbxproj"))
        self.projection["sourceFiles"][key]["sha256"] = "0" * 64
        self.write_projection()
        with self.assertRaisesRegex(RuntimeError, "exact_original_App15_complete_project_and_sources_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_mixed_old_derivative_binding_is_refused(self):
        self.ui["current410bFixture"] = {"sourceCommit": "e540"}
        with self.assertRaisesRegex(RuntimeError, "App15_disallows_other_source_derivatives"):
            p.admit(ROOT, self.main, self.directory, self.ui)


    def test_missing_integrated_history_receipt_is_refused(self):
        self.ui.pop("historyKeyboardPreparation")
        with self.assertRaisesRegex(RuntimeError, "App15_exact_already_integrated_History_binding_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_unintegrated_history_derivative_is_refused(self):
        self.ui["historyKeyboardPreparation"]["sourceAlreadyIntegrated"] = False
        with self.assertRaisesRegex(RuntimeError, "App15_exact_already_integrated_History_binding_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_history_source_and_compiled_receipt_mismatch_is_refused(self):
        self.projection["historyKeyboardPreparation"]["sourceCommit"] = "e540"
        self.write_projection()
        with self.assertRaisesRegex(RuntimeError, "App15_exact_already_integrated_History_binding_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)


    def test_other_original_producer_is_refused(self):
        self.main["controllerSHA256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact_App15_original_producer_and_staging_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_other_source_staging_is_refused(self):
        self.main["inputs"]["stagingReceiptSHA256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact_App15_original_producer_and_staging_required"):
            p.admit(ROOT, self.main, self.directory, self.ui)

    def test_previous_complete_profile_cannot_be_mixed_with_current(self):
        self.projection["current11619Fixture"] = {"sourceCommit": "76f59"}
        self.write_projection()
        with self.assertRaisesRegex(RuntimeError, "App15_disallows_other_source_derivatives"):
            p.admit(ROOT, self.main, self.directory, self.ui)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(Native8acAdmissionControls))
    record = {
        "scope": "PURE_ADMISSION_BOUNDARY_CONTROLS_ONLY",
        "methods": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skips": len(result.skipped),
        "AppBuilds": 0, "UIBuilds": 0, "nativeCalls": 0, "XCTestMethods": 0,
        "status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
    }
    (OUTPUT / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    raise SystemExit(0 if record["status"] == "PASS" else 1)
