#!/usr/bin/env python3
"""New setting/finalization/descriptor boundary controls with synthetic commands.

These exercise only the new choreography. Baseline setup, OS readback and the
owned-command backend are deliberately synthetic. The reviewed collector and
c249 process-registry controls are not rerun, and no product is admitted.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def load(name):
    path = ROOT / (name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_control", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load("native_styled_runtime")
A = load("native_accessibility_runtime")
O = load("native_accessibility_observations")
M = load("native_rtl_matrix")


class Core:
    @staticmethod
    def require(value, message):
        if not value:
            raise RuntimeError(message)

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def digest(path):
        return Core.sha(path.read_bytes())

    @staticmethod
    def raw(path, limit=128 * 1024):
        value = path.read_bytes()
        Core.require(len(value) <= limit, "Bounded synthetic-control data")
        return value

    decode = staticmethod(json.loads)


class SyntheticCommands(R.OwnedCommands):
    """No parent process-manager initialization or real Popen is called."""
    def __init__(self, out):
        self.out, self.calls, self.current_size = out, [], "large"
        self.absent, self.fail_label, self.failure, self.leave_unresolved = True, None, None, False

    @property
    def closed(self):
        return self.absent

    def run(self, argv, directory, label, **options):
        Core.require(directory == self.out and self.absent, "Unresolved synthetic custody")
        self.calls.append({"argv": argv, "label": label, "options": options})
        if argv[:3] == ["xcrun", "simctl", "ui"] and len(argv) == 6 and argv[4] == "content_size":
            self.current_size = argv[5]
        if label == self.fail_label:
            self.absent = not self.leave_unresolved
            raise self.failure
        return {"status": "PASS", "exitCode": 0, "syntheticControlOnly": True}, b""


def observed(configuration, udid, size):
    return {"language": {"app_language": configuration["appLanguage"],
                          "device_language": "en" if configuration["appLanguage"] == "he" else "he"},
            "presentation": {"appearance": configuration["appearance"], "content_size": size},
            "ownedUDID": udid, "visualReview": "PENDING", "physicalDevice": "NOT_RUN"}


class Controls(unittest.TestCase):
    def session(self, root, stage="accessibility-audit-expanded"):
        cell = {"schema": "pinkha-native-rtl-cell-v1", "appLanguage": "he", "deviceFamily": "ipad",
                "deviceType": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB",
                "appearance": "light", "contentSize": "large"}
        path = root / "cell.json"
        path.write_bytes(R.encoded(cell))
        udid = "11111111-2222-4333-8444-555555555555"
        commands = SyntheticCommands(root)
        def baseline(c, helpers, configuration, run, out, device):
            value = observed(configuration, device, commands.current_size)
            R.exclusive(c, out / "rtl-before-environment.json", R.encoded(value))
            return value
        def readback(c, out, configuration, device, selected_stage, phase, *, settings_helpers):
            expected = "large" if phase == "restored" else O.PLANS[selected_stage]["contentSize"]
            c.require(commands.current_size == expected, "Synthetic actual selected content size differs")
            return observed(configuration, device, commands.current_size)
        matrix = types.SimpleNamespace(HELPERS=M.HELPERS, cell=M.cell, prepare=baseline,
                                       installed=lambda *args: {"syntheticInstalledReadbackOnly": True})
        observations = types.SimpleNamespace(EXPANDED=O.EXPANDED, plan=O.plan, environment=O.environment,
                                             readback_record=readback)
        helpers = {key: (lambda *args: None) for key in M.HELPERS}
        value = A.AccessibilitySession(Core, observations, matrix, R, helpers, cell, path, Core.digest(path),
                                       commands, root, udid, "a" * 40, stage)
        return value, commands

    def descriptor(self, session):
        return {A.TARGET: {"OnlyTestIdentifiers": ["NativeLaunchTests/" + session.specification["method"]],
                          "EnvironmentVariables": {"PINKHA_NATIVE_UI_UNIFIED_HOST": "1", "PINKHA_SIMULATOR_UI_DISPOSABLE": "1"},
                          "UnchangedSyntheticCarrier": {"value": [1, "exact"]}},
                "__xctestrun_metadata__": {"FormatVersion": 2}}

    def execute(self, session):
        session.bind(self.descriptor(session))
        argv = ["xcodebuild", "test-without-building", "-xctestrun", str(session.out / "Selected.xctestrun"),
                "-destination", "platform=iOS Simulator,id=" + session.udid,
                "-default-test-execution-time-allowance", "900", "-maximum-test-execution-time-allowance", "900",
                "-only-testing:" + session.specification["selector"], "-resultBundlePath", str(session.out / "Original.xcresult")]
        return session.execute(argv, 1200, session.environment())

    def test_failed_expanded_setter_still_restores_original_large(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session, commands = self.session(root)
            first = OSError("synthetic setter ledger failed after possible size write")
            commands.fail_label, commands.failure = "accessibility-set-content-size", first
            with self.assertRaises(OSError) as caught:
                session.prepare()
            self.assertIs(caught.exception, first)
            self.assertTrue(session.may_have_changed)
            self.assertEqual(commands.current_size, O.EXPANDED)
            final = session.finish(None)
            self.assertEqual(commands.current_size, "large")
            self.assertEqual([row["label"] for row in commands.calls], [
                "accessibility-set-content-size", "accessibility-restore-content-size",
                "accessibility-restored-language-readback", "accessibility-restored-appearance-readback",
                "accessibility-restored-content-size-readback"])
            self.assertFalse(final["originalExecutionAttempted"])
            self.assertIsNone(final["after"])
            self.assertEqual(final["restoration"]["value"]["presentation"]["content_size"], "large")
            self.assertEqual(final["status"], "PASS_SETTINGS_FINALIZATION_NOT_UI_ACCEPTANCE")

    def test_after_failure_restores_and_secondary_retention_preserves_first_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session, commands = self.session(root)
            session.prepare()
            self.execute(session)
            first = OSError("synthetic post-test selected-size readback failure")
            commands.fail_label, commands.failure = "accessibility-after-language-readback", first
            original = R.exclusive
            def retained(c, path, value):
                if path.name == "accessibility-finalization.json":
                    raise OSError("synthetic secondary final receipt failure")
                return original(c, path, value)
            with mock.patch.object(R, "exclusive", side_effect=retained):
                with self.assertRaises(OSError) as caught:
                    session.finish(None)
            self.assertIs(caught.exception, first)
            self.assertEqual(commands.current_size, "large")
            self.assertTrue((root / "accessibility-restored-environment.json").is_file())
            self.assertTrue(any("secondary final receipt failure" in note for note in first.__notes__))
            labels = [row["label"] for row in commands.calls]
            self.assertLess(labels.index("execute"), labels.index("accessibility-after-language-readback"))
            self.assertLess(labels.index("accessibility-after-language-readback"), labels.index("accessibility-restore-content-size"))

    def test_unresolved_setter_withholds_every_further_device_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session, commands = self.session(root)
            commands.fail_label = "accessibility-set-content-size"
            commands.failure, commands.leave_unresolved = OSError("synthetic unresolved group"), True
            with self.assertRaises(OSError):
                session.prepare()
            calls = copy.deepcopy(commands.calls)
            with self.assertRaisesRegex(RuntimeError, "Unresolved owned command custody"):
                session.finish(None)
            self.assertEqual(commands.calls, calls)
            final = Core.decode((root / "accessibility-finalization.json").read_bytes())
            self.assertEqual(final["status"], "FAIL")
            self.assertFalse(final["ownedCommandsClosed"])
            self.assertEqual(final["restoration"], {"withheldReason": "UNRESOLVED_OWNED_COMMAND_CUSTODY"})

    def test_descriptor_context_is_exact_and_ambient_or_prebound_overrides_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session, commands = self.session(root, "accessibility-voiceover-large")
            session.prepare()
            original = self.descriptor(session)
            with mock.patch.dict(os.environ, {A.ENVIRONMENT[0]: "synthetic-forbidden-context"}):
                with self.assertRaisesRegex(RuntimeError, "Ambient or prebound"):
                    session.bind(original)
            prebound = copy.deepcopy(original)
            prebound[A.TARGET]["TestingEnvironmentVariables"] = {"TEST_RUNNER_" + A.ENVIRONMENT[1]: "f" * 64}
            with self.assertRaisesRegex(RuntimeError, "Ambient or prebound"):
                session.bind(prebound)
            selected, proof = session.bind(original)
            raw = (root / "accessibility-invocation.json").read_bytes()
            self.assertEqual(selected[A.TARGET]["EnvironmentVariables"][A.ENVIRONMENT[0]].encode(), raw)
            self.assertEqual(selected[A.TARGET]["EnvironmentVariables"][A.ENVIRONMENT[1]], Core.sha(raw))
            restored = copy.deepcopy(selected)
            for key in A.ENVIRONMENT:
                del restored[A.TARGET]["EnvironmentVariables"][key]
            self.assertEqual(restored, original)
            self.assertEqual(set(session.environment()), {"TEST_RUNNER_" + key for key in A.ENVIRONMENT})
            self.assertTrue(proof["inverseRestoresOriginalBoundDescriptor"])
            self.assertEqual(len(session.context), 13)
            self.assertFalse(session.may_have_changed)
            self.assertEqual(commands.calls, [])


if __name__ == "__main__":
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    record = {"schema": "native23-accessibility-choreography-controls/v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
              "scope": "SYNTHETIC_COMMANDS_BASELINE_AND_READBACK_NEW_CHOREOGRAPHY_ONLY_NO_PRODUCT_ADMISSION",
              "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "elapsedSeconds": time.monotonic() - started,
              "files": {name: Core.digest(ROOT / name) for name in ("native_accessibility_runtime.py",
                       "native_accessibility_observations.py", "native_styled_runtime.py", "validate_accessibility_choreography.py")},
              "oldCollectorAndRegistryControlsRerun": 0, "backendProcessesSpawned": 0, "AppleCommands": 0,
              "XCTestRuns": 0, "nativeCalls": 0, "settingsChanged": 0}
    with (ROOT / "choreography-controls1.json").open("xb") as stream:
        stream.write((json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    sys.exit(0 if result.wasSuccessful() else 1)
