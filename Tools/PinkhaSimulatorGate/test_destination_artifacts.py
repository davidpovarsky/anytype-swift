"""Portable no-install selection controls; synthetic Xcode is not Apple acceptance."""
import base64
import copy
import gzip
import json
from pathlib import Path
import plistlib
import subprocess
import time
from types import SimpleNamespace
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

    def manual(self, control, name="xctestrun"):
        section, filename = destination.MANUALS[name]
        return control.developer / "usr/share/man" / section / filename

    def test_capture_uses_selected_xcode_once_and_saves_exact_both_manuals_before_install(self):
        control = self.fixture()
        frozen = control.freeze()
        def before_install(_):
            self.assertTrue((control.evidence / destination.PROOF).is_file())
            self.assertFalse((control.evidence / preservation.INSTALLATION).exists())
        installation = control.install(frozen, before_install)
        proof = destination.decode((control.evidence / destination.PROOF).read_bytes())
        self.assertEqual(control.capability_calls, [["xcrun", "--find", "xcodebuild"],
                                                  [str(control.xcodebuild), "-version"]])
        self.assertEqual(len(control.install_calls), 1)
        self.assertEqual(proof["xcodebuildPath"], str(control.xcodebuild))
        self.assertEqual(proof["binding"], frozen.value["binding"])
        self.assertEqual(proof["codeCarriersSHA256"], installation.value["codeCarriersSHA256"])
        self.assertEqual(proof["testBundle"]["relativeBundlePath"], "__TESTHOST__/PlugIns/AnytypeTests.xctest")
        for name, record in proof["manuals"].items():
            self.assertEqual((control.evidence / record["file"]).read_bytes(), self.manual(control, name).read_bytes())
            self.assertEqual(destination.sha256((control.evidence / record["file"]).read_bytes()), record["sha256"])

    def test_missing_ambiguous_unsupported_or_escaped_manual_never_installs(self):
        for mode in ("missing", "ambiguous", "unsupported", "opposite", "escaped"):
            with self.subTest(mode=mode):
                control = self.fixture()
                frozen = control.freeze()
                manual = self.manual(control)
                if mode == "missing":
                    manual.unlink()
                elif mode == "ambiguous":
                    manual.with_suffix(manual.suffix + ".gz").write_bytes(gzip.compress(manual.read_bytes()))
                elif mode == "unsupported":
                    manual.write_bytes(b"UseDestinationArtifacts is not documented by this synthetic version.\n")
                elif mode == "opposite":
                    manual.write_bytes(fixtures.XCTESTRUN_MANUAL.replace(b"will not install", b"will install"))
                else:
                    outside = control.root / "unselected-manual"
                    outside.write_bytes(manual.read_bytes())
                    manual.unlink(); manual.symlink_to(outside)
                with self.assertRaises(ValueError):
                    control.install(frozen)
                self.assertEqual(control.install_calls, [])
                self.assertFalse((control.evidence / preservation.INSTALLATION).exists())
                self.assertFalse((control.evidence / destination.PROOF).exists())

    def test_compressed_selected_manuals_are_captured_with_bounded_expansion(self):
        control = self.fixture()
        for name in destination.MANUALS:
            manual = self.manual(control, name)
            manual.with_suffix(manual.suffix + ".gz").write_bytes(gzip.compress(manual.read_bytes()))
            manual.unlink()
        frozen = control.freeze()
        installation = control.install(frozen)
        self.assertTrue(preservation.environment(frozen, installation)[destination.ENV + "BASE64"])
        proof = destination.decode((control.evidence / destination.PROOF).read_bytes())
        self.assertTrue(all(item["compressed"] for item in proof["manuals"].values()))
        with self.assertRaisesRegex(ValueError, "Expanded Xcode manual exceeds"):
            destination.manual_text(gzip.compress(b"x" * (destination.MANUAL_LIMIT + 1)), True)
        with self.assertRaisesRegex(ValueError, "Expanded Xcode manual exceeds"):
            destination.manual_text(b"x" * (destination.MANUAL_LIMIT + 1), False)

    def test_actual_mdoc_flag_and_font_macros_preserve_required_document_semantics(self):
        raw = b".Nm xcodebuild\n.Ar test-without-building\n.It Fl xctestrun\n.Op Fl destination\n.Fl version\n"
        text = destination.manual_text(raw, False)
        self.assertIn("-xctestrun", text)
        self.assertIn("-destination", text)
        self.assertIn("-version", text)
        rendered = destination.manual_text(fixtures.XCTESTRUN_MANUAL.replace(
            b"UseDestinationArtifacts", b"\\fBUseDestinationArtifacts\\fR"), False)
        destination.require_manual_support({"xcodebuild": text, "xctestrun": rendered})

    def test_saved_manual_corruption_or_foreign_toolchain_receipt_is_rejected(self):
        control, frozen, installation, _ = self.supported()
        path = control.evidence / destination.PROOF
        proof = destination.decode(path.read_bytes())
        for name, record in proof["manuals"].items():
            with self.subTest(manual=name):
                saved = control.evidence / record["file"]
                original = saved.read_bytes()
                saved.write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "Saved Xcode manual bytes changed"):
                    preservation.environment(frozen, installation)
                saved.write_bytes(original)
        changes = [lambda value: value.update(xcodebuildPath="/usr/bin/xcodebuild"),
                   lambda value: value.update(xcodebuildVersion="unknown"),
                   lambda value: value["manuals"]["xcodebuild"].update(sourcePath="/other/Xcode.app/manual"),
                   lambda value: value["manuals"]["xcodebuild"].update(file="../foreign"),
                   lambda value: value["manuals"].pop("xctestrun")]
        for change in changes:
            invalid = copy.deepcopy(proof); change(invalid)
            with self.subTest(change=change), self.assertRaises(ValueError):
                destination.validate(invalid, frozen.value["binding"], fixtures.CODE_SHA, control.evidence)

    def test_capability_timeout_or_cancellation_is_once_only_and_never_installs(self):
        for stage in (1, 2):
            for error_type in (subprocess.TimeoutExpired, KeyboardInterrupt):
                with self.subTest(stage=stage, error=error_type.__name__):
                    control = self.fixture()
                    frozen = control.freeze()
                    error = (subprocess.TimeoutExpired(["private-capability-argument"], 30,
                        output=b"private-capability-output", stderr=b"private-capability-stderr")
                        if error_type is subprocess.TimeoutExpired else KeyboardInterrupt("private-cancellation-text"))
                    with self.assertRaises(error_type):
                        control.install(frozen, capability_error=(stage, error))
                    self.assertEqual(len(control.capability_calls), stage)
                    self.assertEqual(control.install_calls, [])
                    self.assertFalse((control.evidence / destination.PROOF).exists())
                    self.assertFalse((control.evidence / preservation.INSTALLATION).exists())
                    observation = (control.evidence / "type-preservation-install-observation.json").read_text()
                    self.assertNotIn("private-", observation)
                    value = json.loads(observation)
                    self.assertEqual(value["phase"], "DESTINATION_ARTIFACTS_SUPPORT")
                    self.assertEqual(value["errorType"], error_type.__name__)

    def test_capability_commands_cannot_extend_existing_install_deadline(self):
        control = self.fixture()
        calls = []
        def command(argv, **kwargs):
            calls.append((argv, kwargs["timeout"]))
            return SimpleNamespace(returncode=0, stdout=(str(control.xcodebuild) + "\n").encode(), stderr=b"")
        bundle = destination.test_bundle(control.built, control.carriers(control.built))
        with patch.object(destination.time, "monotonic", side_effect=[10.0, 11.1]), \
             patch.object(destination.subprocess, "run", side_effect=command):
            with self.assertRaisesRegex(ValueError, "phase budget exhausted"):
                destination.capture(control.evidence, fixtures.BINDING, fixtures.CODE_SHA, bundle, 11.0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 1.0)
        self.assertEqual(preservation.INSTALLATION_SECONDS, 660)
        self.assertFalse((control.evidence / destination.PROOF).exists())

    def test_capability_nonzero_oversized_and_unselected_paths_fail_closed(self):
        for mode in ("nonzero", "oversized", "relative", "shim"):
            with self.subTest(mode=mode):
                control = self.fixture()
                bundle = destination.test_bundle(control.built, control.carriers(control.built))
                output = {"nonzero": str(control.xcodebuild).encode(), "oversized": b"x" * 4097,
                          "relative": b"xcodebuild", "shim": b"/usr/bin/xcodebuild"}[mode]
                response = SimpleNamespace(returncode=1 if mode == "nonzero" else 0,
                                           stdout=output, stderr=b"private-diagnostic")
                with patch.object(destination.subprocess, "run", return_value=response) as command:
                    with self.assertRaises(ValueError):
                        destination.capture(control.evidence, fixtures.BINDING, fixtures.CODE_SHA, bundle,
                                            time.monotonic() + 660)
                command.assert_called_once()
                self.assertFalse((control.evidence / destination.PROOF).exists())

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

    def test_foreign_or_missing_proof_cannot_enable_destination_mode(self):
        _, _, _, environment = self.supported()
        original = destination.decode(base64.b64decode(environment[destination.ENV + "BASE64"]))
        for mode in ("missing", "hash", "binding", "code", "bundle", "relative", "duplicate"):
            with self.subTest(mode=mode):
                env = environment.copy()
                value = copy.deepcopy(original)
                if mode == "missing":
                    env.pop(destination.ENV + "BASE64")
                elif mode == "hash":
                    env[destination.ENV + "SHA256"] = "f" * 64
                else:
                    if mode == "binding": value["binding"]["runID"] = "99999"
                    elif mode == "code": value["codeCarriersSHA256"] = "f" * 64
                    elif mode == "bundle": value["testBundle"]["hostBundleIdentifier"] = "io.foreign.app"
                    elif mode == "relative": value["testBundle"]["relativeBundlePath"] = "__TESTHOST__/Foreign.xctest"
                    raw = json.dumps(value).encode()
                    if mode == "duplicate": raw = raw[:-1] + b', "schemaVersion": 1}'
                    env[destination.ENV + "BASE64"] = base64.b64encode(raw).decode("ascii")
                    env[destination.ENV + "SHA256"] = destination.sha256(raw)
                target = fixtures.native_target()
                with self.assertRaises(ValueError):
                    preservation.configure_target(target, env)
                self.assertNotIn("UseDestinationArtifacts", target)

    def test_batch_and_standalone_share_exact_native_destination_configuration(self):
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
        self.assertTrue(one[0]["UseDestinationArtifacts"])
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
