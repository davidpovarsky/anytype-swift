"""Focused xctestrun admission controls; synthetic products, no Xcode or UI execution."""
import copy
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

import verify_custom_type as gate


COMMIT = "a" * 40
PRODUCTS = "Debug-iphonesimulator/"
RUNNER = PRODUCTS + gate.UI_TARGET + "-Runner.app"
BUNDLE = RUNNER + "/PlugIns/" + gate.UI_TARGET + ".xctest"
APP = PRODUCTS + "PinkhaAnyNative.app"


def target():
    return {
        "IsUITestBundle": True,
        "ProductModuleName": gate.UI_TARGET,
        "TestHostPath": "__TESTROOT__/" + RUNNER,
        "TestBundlePath": "__TESTHOST__/PlugIns/" + gate.UI_TARGET + ".xctest",
        "UITargetAppPath": "__TESTROOT__/" + APP,
        "TestHostBundleIdentifier": gate.UI_BUNDLE_ID + ".xctrunner",
    }


def configuration(version=1):
    if version == 1:
        return {gate.UI_TARGET: target(), "__xctestrun_metadata__": {"FormatVersion": 1}}
    value = target()
    value["BlueprintName"] = gate.UI_TARGET
    return {"__xctestrun_metadata__": {"FormatVersion": 2},
            "TestConfigurations": [{"Name": "Test Scheme Action", "IsEnabled": True, "TestTargets": [value]}]}


class CompiledUIProductIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.derived = self.root / "derived"
        self.products = self.derived / "Build/Products"
        for relative, bundle_id, executable in (
            (APP, gate.APP_ID, "PinkhaAnyNative"),
            (RUNNER, gate.UI_BUNDLE_ID + ".xctrunner", gate.UI_TARGET + "-Runner"),
            (BUNDLE, gate.UI_BUNDLE_ID, gate.UI_TARGET),
        ):
            directory = self.products / relative
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "Info.plist").write_bytes(plistlib.dumps(
                {"CFBundleIdentifier": bundle_id, "CFBundleExecutable": executable}))
            # Deliberately not runnable: this tests controller binding, not Apple execution.
            (directory / executable).write_bytes(bytes.fromhex("cffaedfe") + b"synthetic-control-only")
        self.manifest = self.products / "PinkhaAnyNativeApp_iphonesimulator27.0-arm64.xctestrun"
        self.write(configuration())
        vendor = self.root / "Modules/PinkhaAnyRuntime/Vendor"
        vendor.mkdir(parents=True)
        self.artifact = vendor / "native-artifact.json"
        self.artifact.write_text('{"syntheticControllerInput":true}\n')
        self.binding = vendor / "consumer-binding.json"
        self.binding.write_text(json.dumps({"status": "SOURCE_IDENTICAL_NATIVE_ARTIFACT",
            "consumerCommit": COMMIT, "testResultsRelabeled": False, "reused": True,
            "artifactReceiptSHA256": gate.sha(self.artifact.read_bytes())}))
        self.git = patch.object(gate.subprocess, "check_output", return_value=COMMIT + "\n")
        self.git.start()
        self.addCleanup(self.git.stop)

    def write(self, value):
        self.manifest.write_bytes(plistlib.dumps(value))

    def capture(self):
        return gate.product_identity(self.derived, root=self.root)

    def test_both_documented_formats_bind_the_same_local_products(self):
        results = []
        for version in (1, 2, None):
            value = configuration(version or 1)
            if version is None:
                del value["__xctestrun_metadata__"]
                # The format 1 dictionary key supplies the target identity.
                self.assertNotIn("BlueprintName", value[gate.UI_TARGET])
            self.write(value)
            with self.subTest(version=version):
                result = self.capture()
                self.assertEqual(result["xctestrun"]["formatVersion"], version or 1)
                self.assertEqual(result["xctestrun"]["target"], gate.UI_TARGET)
                self.assertEqual(result["xctestrun"]["testBundle"], BUNDLE)
                self.assertEqual(result["xctestrun"]["sha256"], gate.sha(self.manifest.read_bytes()))
                results.append(result)
        self.assertEqual(results[0]["app"], results[1]["app"])
        self.assertEqual(results[0]["uiRunner"], results[1]["uiRunner"])
        self.assertEqual(results[0]["nativeBindingSHA256"], results[2]["nativeBindingSHA256"])

    def test_schema_rejects_unknown_mixed_disabled_and_ambiguous_targets(self):
        bad = []
        for version in (0, 3, True, "1"):
            value = configuration(); value["__xctestrun_metadata__"]["FormatVersion"] = version
            bad.append(value)
        for key in ("OtherUITests", "TestConfigurations"):
            value = configuration(); value[key] = copy.deepcopy(value[gate.UI_TARGET])
            bad.append(value)
        value = configuration(); value[gate.UI_TARGET]["BlueprintName"] = "OtherUITests"; bad.append(value)
        value = configuration(2); value[gate.UI_TARGET] = target(); bad.append(value)
        value = configuration(2); value["TestConfigurations"] *= 2; bad.append(value)
        value = configuration(2); value["TestConfigurations"][0]["IsEnabled"] = False; bad.append(value)
        value = configuration(2); value["TestConfigurations"][0]["TestTargets"] *= 2; bad.append(value)
        value = configuration(2); value["TestConfigurations"][0]["TestTargets"][0]["BlueprintName"] = "OtherUITests"; bad.append(value)
        for key, disabled in (("IsUITestBundle", False), ("IsEnabled", False),
                              ("BlueprintIsSkipped", True), ("UseDestinationArtifacts", True)):
            value = configuration(); value[gate.UI_TARGET][key] = disabled; bad.append(value)
        for index, value in enumerate(bad):
            with self.subTest(index=index), self.assertRaises(ValueError):
                gate.compiled_ui_target(value)

    def test_paths_and_actual_bundle_identifiers_cannot_be_substituted(self):
        for field, replacement in (
            ("TestHostPath", "__TESTROOT__/" + APP),
            ("TestHostPath", "__TESTHOST__"),
            ("TestBundlePath", "__TESTROOT__/" + APP),
            ("UITargetAppPath", "__TESTROOT__/" + RUNNER),
            ("TestBundlePath", "__UNKNOWN__/" + BUNDLE),
            ("TestBundlePath", "__TESTROOT__/../Products/" + BUNDLE),
            ("UITargetAppPath", APP),
            ("TestHostBundleIdentifier", "io.other.runner"),
            ("UITargetAppBundleIdentifier", "io.other.app"),
        ):
            value = configuration(); value[gate.UI_TARGET][field] = replacement; self.write(value)
            with self.subTest(field=field, replacement=replacement), self.assertRaises(ValueError):
                self.capture()
        self.write(configuration())
        for relative in (APP, RUNNER, BUNDLE):
            path = self.products / relative / "Info.plist"
            original = path.read_bytes()
            value = plistlib.loads(original); value["CFBundleIdentifier"] = "io.other.product"
            path.write_bytes(plistlib.dumps(value))
            with self.subTest(bundle=relative), self.assertRaises(ValueError):
                self.capture()
            path.write_bytes(original)

    def test_duplicate_keys_symlinks_and_multiple_matching_manifests_are_rejected(self):
        raw = self.manifest.read_bytes()
        key = b"<key>IsUITestBundle</key>"
        self.manifest.write_bytes(raw.replace(key, key + b"<false/>" + key, 1))
        with self.assertRaisesRegex(ValueError, "duplicate_compiled_plist_key"):
            self.capture()
        self.manifest.write_bytes(raw)
        duplicate = self.products / "PinkhaAnyNativeApp_other.xctestrun"
        duplicate.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "one_compiled_native_test_configuration"):
            self.capture()
        duplicate.unlink()
        outside = self.root / "outside.xctestrun"; outside.write_bytes(raw)
        self.manifest.unlink(); self.manifest.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "one_compiled_native_test_configuration"):
            self.capture()

    def test_original_native_artifact_binding_stays_required_after_schema_admission(self):
        for key, replacement in (("consumerCommit", "b" * 40), ("testResultsRelabeled", True),
                                 ("reused", False), ("artifactReceiptSHA256", "0" * 64)):
            original = self.binding.read_bytes()
            value = json.loads(original); value[key] = replacement
            self.binding.write_text(json.dumps(value))
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "source_identical_native_runtime_binding"):
                self.capture()
            self.binding.write_bytes(original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
