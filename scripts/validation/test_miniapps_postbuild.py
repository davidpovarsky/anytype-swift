#!/usr/bin/env python3
"""New harness regressions only; filesystem/mocked-command fixtures, not Apple acceptance."""
import hashlib
import json
from pathlib import Path
import plistlib
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/MiniApps"))
from export_products import export_built_products, product_closure
import simulator_admission


class ProductExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.products = self.root / "Products"
        self.configuration = self.products / "Anytype.xctestrun"
        variant = self.products / "Debug-MiniAppsOwner-iphonesimulator"
        self.app = variant / "Anytype.app"
        (self.app / "PlugIns/AnytypeTests.xctest").mkdir(parents=True)
        (self.app / "PlugIns/AnytypeTests.xctest/AnytypeTests").write_bytes(b"native-test-fixture")
        (self.app / "Anytype").write_bytes(b"app-fixture")
        (self.app / "Frameworks").mkdir()
        self.framework = variant / "PackageFrameworks/Fixture.framework"
        self.framework.mkdir(parents=True)
        (self.framework / "Fixture").write_bytes(b"actual-original-fixture-leaf")
        (self.app / "Frameworks/Fixture.framework").symlink_to("../../PackageFrameworks/Fixture.framework")
        self.configuration.write_bytes(plistlib.dumps({"AnytypeTests": {
            "BlueprintName": "AnytypeTests", "TestHostPath": "__TESTROOT__/Debug-MiniAppsOwner-iphonesimulator/Anytype.app",
            "TestBundlePath": "__TESTHOST__/PlugIns/AnytypeTests.xctest"}}))
        self.receipt = {key: "fixture-" + key for key in (
            "source_sha", "run_id", "run_attempt", "configuration", "producer_pin", "native_binding",
            "dependency_resolution", "source_profile_sha256", "selected_methods")}
        self.receipt.update(native_build_succeeded=True, status="NATIVE_BUILD_PASS_UI_NOT_BUILT")

    def test_original_native_and_ui_configuration_closure_and_changed_link_target(self):
        ui = self.products / "UI.xctestrun"
        runner = self.products / "Debug-MiniAppsOwner-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
        (runner / "PlugIns/PinkhaStage1AcceptanceUITests.xctest").mkdir(parents=True)
        (runner / "Runner").write_bytes(b"ui-runner-fixture")
        (runner / "PlugIns/PinkhaStage1AcceptanceUITests.xctest/UITests").write_bytes(b"ui-tests-fixture")
        ui.write_bytes(plistlib.dumps({"UITests": {
            "BlueprintName": "PinkhaStage1AcceptanceUITests",
            "TestHostPath": "__TESTROOT__/Debug-MiniAppsOwner-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app",
            "TestBundlePath": "__TESTHOST__/PlugIns/PinkhaStage1AcceptanceUITests.xctest",
            "UITargetAppPath": "__TESTROOT__/Debug-MiniAppsOwner-iphonesimulator/Anytype.app",
            "DependentProductPaths": ["__PLATFORMS__/iPhoneSimulator.platform/Developer/Library/Frameworks/XCTest.framework"]}}))
        configurations = [self.configuration, ui]
        output = self.root / "complete-export"
        proof = export_built_products(self.products, configurations, output, self.receipt)
        manifest = json.loads((output / "native-products-manifest.json").read_text())
        self.assertEqual(manifest["run_attempt"], self.receipt["run_attempt"])
        self.assertEqual(manifest["source_sha"], self.receipt["source_sha"])
        self.assertEqual(manifest["original_xctestrun"], [self.configuration.name, ui.name])
        self.assertEqual(hashlib.sha256((output / "original-build-receipt.json").read_bytes()).hexdigest(),
                         proof["original_build_receipt_sha256"])
        leaf = "Debug-MiniAppsOwner-iphonesimulator/PackageFrameworks/Fixture.framework/Fixture"
        link = "Debug-MiniAppsOwner-iphonesimulator/Anytype.app/Frameworks/Fixture.framework"
        with tarfile.open(proof["archive"], "r:gz") as archive:
            self.assertEqual(archive.extractfile(leaf).read(), b"actual-original-fixture-leaf")
            self.assertTrue(archive.getmember(link).issym())
            self.assertIn(ui.name, archive.getnames())
        before = product_closure(self.products, configurations)[1]
        (self.framework / "Fixture").write_bytes(b"changed-behind-the-same-link")
        after = product_closure(self.products, configurations)[1]
        self.assertNotEqual(before[leaf], after[leaf])
        self.assertEqual(before[link], after[link])
        with self.assertRaisesRegex(RuntimeError, "must not be overwritten"):
            export_built_products(self.products, configurations, output, self.receipt)

    def test_direct_xctestrun_symlink_chain_preserves_every_alias_and_target(self):
        alias = self.products / "Debug-MiniAppsOwner-iphonesimulator/Alias.framework"
        intermediate = alias.with_name("Intermediate.framework")
        intermediate.symlink_to("PackageFrameworks/Fixture.framework")
        alias.symlink_to("Intermediate.framework")
        value = plistlib.loads(self.configuration.read_bytes())
        value["AnytypeTests"]["DependentProductPaths"] = [
            "__TESTROOT__/Debug-MiniAppsOwner-iphonesimulator/Alias.framework"]
        self.configuration.write_bytes(plistlib.dumps(value))
        proof = export_built_products(self.products, [self.configuration], self.root / "alias-export", self.receipt)
        alias_name = alias.relative_to(self.products).as_posix()
        target_name = (self.framework / "Fixture").relative_to(self.products).as_posix()
        with tarfile.open(proof["archive"], "r:gz") as archive:
            self.assertTrue(archive.getmember(alias_name).issym())
            self.assertEqual(archive.getmember(alias_name).linkname, "Intermediate.framework")
            hop = archive.getmember(intermediate.relative_to(self.products).as_posix())
            self.assertTrue(hop.issym())
            self.assertEqual(hop.linkname, "PackageFrameworks/Fixture.framework")
            self.assertEqual(archive.extractfile(target_name).read(), b"actual-original-fixture-leaf")
            self.assertNotIn(alias_name + "/Fixture", archive.getnames())
        before = product_closure(self.products, [self.configuration])[1]
        other = self.framework.with_name("Other.framework")
        other.mkdir()
        (other / "Fixture").write_bytes(b"other-original-fixture-leaf")
        alias.unlink()
        alias.symlink_to("PackageFrameworks/Other.framework")
        after = product_closure(self.products, [self.configuration])[1]
        self.assertNotEqual(before[alias_name], after[alias_name])

    def test_outside_reference_and_unbuilt_export_are_rejected(self):
        outside = self.root / "OtherBuild.app"
        outside.mkdir()
        value = plistlib.loads(self.configuration.read_bytes())
        value["AnytypeTests"]["DependentProductPaths"] = [str(outside)]
        self.configuration.write_bytes(plistlib.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "outside Products"):
            export_built_products(self.products, [self.configuration], self.root / "wrong-export", self.receipt)
        self.assertFalse((self.root / "wrong-export").exists())
        unbuilt = {**self.receipt, "native_build_succeeded": False}
        with self.assertRaisesRegex(RuntimeError, "genuinely successful"):
            export_built_products(self.products, [self.configuration], self.root / "unbuilt-export", unbuilt)


class SimulatorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.owner = json.loads((ROOT / "Tools/MiniApps/owner-signing.json").read_text())
        self.claims = plistlib.loads((ROOT / "Config/Signing/AnytypeOwner.entitlements").read_bytes())
        self.claims["com.apple.security.application-groups"] = [self.owner["native_app_group"], self.owner["shared_app_group"]]
        self.claims["application-identifier"] = self.owner["team_id"] + "." + self.owner["bundle_ids"]["Anytype"]

    def invoke(self, claims, verify_code=0):
        calls = []
        def command(arguments, **kwargs):
            calls.append(arguments)
            if "--verify" in arguments:
                return SimpleNamespace(returncode=verify_code, stdout="", stderr="fixture verification")
            return SimpleNamespace(stdout=plistlib.dumps({}), stderr=b"")
        embedded = {"source": "__TEXT,__entitlements", "entitlements": claims,
                    "executable_sha256": "fixture", "section_sha256": "fixture"}
        with patch.object(simulator_admission.subprocess, "run", side_effect=command), \
             patch.object(simulator_admission, "read_simulator_entitlements", return_value=embedded):
            result = simulator_admission.verify_built_entitlements(
                ROOT, self.root / "fixture.app", self.root / "fixture.app/fixture", self.owner, self.root, "fixture")
        return result, calls

    def test_empty_signature_plist_uses_embedded_claims_and_retains_pending_physical_status(self):
        proof, calls = self.invoke(self.claims)
        self.assertEqual(calls[0][0:3], ["codesign", "--verify", "--strict"])
        self.assertEqual(proof["signature_entitlements"], {})
        self.assertEqual(proof["embedded"]["entitlements"], self.claims)
        self.assertEqual(proof["apple_profile_grants"], "PENDING_APPLE_GRANT")
        self.assertEqual(proof["physical_sharing"], "NOT_PROVEN_BY_SIMULATOR")

    def test_original_signature_and_all_source_claims_are_still_required(self):
        with self.assertRaisesRegex(RuntimeError, "signature did not verify"):
            self.invoke(self.claims, verify_code=1)
        missing = dict(self.claims)
        missing.pop("com.apple.developer.usernotifications.communication")
        with self.assertRaisesRegex(RuntimeError, "usernotifications.communication"):
            self.invoke(missing)
        foreign = {**self.claims, "application-identifier": "OTHER.foreign"}
        with self.assertRaisesRegex(RuntimeError, "application identity differs"):
            self.invoke(foreign)


if __name__ == "__main__":
    unittest.main(verbosity=2)
