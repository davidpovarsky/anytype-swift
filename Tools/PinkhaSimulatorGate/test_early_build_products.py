"""Focused early-build evidence controls; no Apple/product execution is claimed."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import early_build_products as products


SHA = "c8839d7ef090c95197443227e4c51fac471a07e6"


class EarlyBuildProductsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.derived = self.root / "derived"
        self.evidence = self.root / "evidence"
        self.product_root = self.derived / "Build/Products"
        self.app = self.product_root / "Debug-Anytype-iphonesimulator/Anytype.app"
        self.app.mkdir(parents=True)
        self.executable = self.app / "Anytype"
        self.executable.write_bytes(b"controlled original executable\x00\x01")
        self.executable.chmod(0o755)
        self.configuration = self.product_root / "Anytype_iphonesimulator.xctestrun"
        self.configuration.write_bytes(b"controlled original Xcode configuration")
        (self.derived / "Build/PinkhaSourceInputs.json").write_text(json.dumps({"source_sha": SHA}))
        self.arguments = dict(source_sha=SHA, run_id="999", run_attempt="1", build_flags=["fixture-only"])

    def capture(self, **extra):
        return products.capture(self.derived, self.evidence, **self.arguments, **extra)

    def test_exact_archive_survives_later_admission_failure_or_product_mutation(self):
        original = self.executable.read_bytes()
        (self.app / "Anytype-link").symlink_to("Anytype")
        os.link(self.executable, self.app / "Anytype-hardlink")
        result = self.capture()
        archive = self.evidence / result["archive_path"]
        manifest = json.loads((self.evidence / result["manifest_path"]).read_bytes())
        self.executable.write_bytes(b"later mutation cannot replace archived evidence")
        self.configuration.unlink()
        with tarfile.open(archive, "r:gz") as packed:
            name = "Build/Products/Debug-Anytype-iphonesimulator/Anytype.app/Anytype"
            self.assertEqual(packed.extractfile(name).read(), original)
            self.assertEqual(packed.getmember(name).mode, 0o755)
            self.assertTrue(packed.getmember(name + "-link").issym())
            self.assertEqual(packed.extractfile(name + "-hardlink").read(), original)
            self.assertEqual(packed.extractfile("Build/Products/Anytype_iphonesimulator.xctestrun").read(),
                             b"controlled original Xcode configuration")
        self.assertEqual(result["status"], products.STATUS)
        self.assertEqual(manifest["capture_phase"], "AFTER_BUILD_BEFORE_ADMISSION")
        self.assertEqual(manifest["source_sha"], SHA)
        self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
        for field in ("build_reuse_enabled", "every_entry_build_origin_verified",
                      "native_acceptance_reused", "ui_acceptance_reused"):
            self.assertIs(manifest[field], False)

    def test_rejects_stale_unknown_scope_and_special_product_without_overwrite(self):
        result = self.capture()
        original = (self.evidence / result["archive_path"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "stale"):
            self.capture()
        self.assertEqual((self.evidence / result["archive_path"]).read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "scope"):
            self.capture(scope="../../outside")
        os.mkfifo(self.product_root / "Unexpected.pipe")
        with self.assertRaisesRegex(ValueError, "Special build product"):
            self.capture(scope="coherent-native")
        failed = json.loads((self.evidence / "coherent-native-early-products/manifest.json").read_text())
        self.assertEqual(failed["status"], "CAPTURE_FAILED_NO_BUILD_REUSE_ALLOWED")
        self.assertFalse((self.evidence / "coherent-native-early-products/BuildProducts.tar.gz").exists())

    def test_package_transport_preserves_only_the_three_exact_archives(self):
        for scope in ("sdk06", "coherent-native", "coherent-ui"):
            result = self.capture(scope=scope)
            self.assertTrue((self.evidence / result["archive_path"]).is_file())
        (self.evidence / "unreviewed.tar.gz").write_bytes(b"not an approved build archive")
        (self.evidence / "sdk06-early-products/BuildProducts.tar.gz.partial").write_bytes(b"incomplete")
        root = Path(__file__).resolve().parents[2]
        subprocess.run([sys.executable, "-B", str(root / "Tools/PinkhaNativeDerived/package_evidence.py"),
                        str(self.evidence)], check=True, capture_output=True)
        with zipfile.ZipFile(self.evidence / "Pinkha-Native-Derived-Evidence.zip") as packed:
            for scope in ("sdk06", "coherent-native", "coherent-ui"):
                name = scope + "-early-products/BuildProducts.tar.gz"
                self.assertEqual(packed.read(name), (self.evidence / name).read_bytes())
                self.assertIn(scope + "-early-products/manifest.json", packed.namelist())
            self.assertNotIn("unreviewed.tar.gz", packed.namelist())
            self.assertNotIn("sdk06-early-products/BuildProducts.tar.gz.partial", packed.namelist())

    def test_sdk_controller_captures_before_the_first_failing_admission_gate(self):
        import run_wave15_acceptance as wave

        app = self.root / "source"
        app.mkdir()
        self.evidence.mkdir()
        (self.evidence / "preflight").mkdir()
        (self.evidence / "heart").mkdir()
        (app / "Tools/PinkhaSimulatorGate").mkdir(parents=True)
        (app / "Tools/PinkhaSimulatorGate/required-coverage.json").write_text("{}")
        preflight = {"status": "PREFLIGHT_PASS_UI_NOT_RUN", "source_sha": SHA, "run_id": "999",
                     "selected": {"ipad": {"udid": "00000000-0000-0000-0000-000000000001",
                                           "name": "Pinkha-UI27-999-ipad"}}}
        (self.evidence / "preflight/preflight.json").write_text(json.dumps(preflight))
        (self.evidence / "heart/heart-installation.json").write_text("{}")
        args = argparse.Namespace(app=app, evidence=self.evidence, derived=self.derived,
                                  lane="hanlin-native", device="ipad", language="en",
                                  include_shared_editor=True, include_text_native_ack=True)
        receipt = {}
        environment = {"GITHUB_SHA": SHA, "GITHUB_RUN_ID": "999", "GITHUB_RUN_ATTEMPT": "1",
                       "GITHUB_REF": "refs/heads/" + wave.CONTINUATION_BRANCH}
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, environment))
            stack.enter_context(patch.object(wave.platform, "system", return_value="Darwin"))
            stack.enter_context(patch.object(wave, "source_methods"))
            stack.enter_context(patch.object(wave.shared, "git",
                side_effect=lambda app, *args: SHA if args[0] == "rev-parse" else wave.CONTINUATION_BRANCH))
            stack.enter_context(patch.object(wave.shared, "runtime_binding", return_value={}))
            stack.enter_context(patch.object(wave.shared, "candidate_identity", return_value={"hashes": {}}))
            stack.enter_context(patch.object(wave.shared, "prepare_source_cache"))
            command = stack.enter_context(patch.object(wave.shared, "command"))
            stack.enter_context(patch.object(wave.subprocess, "run",
                return_value=SimpleNamespace(returncode=0, stdout="en", stderr="")))
            stack.enter_context(patch.object(wave.text_native_ack, "source_contract", return_value={}))
            stack.enter_context(patch.object(wave.shared_editor_existing_build, "source_contract",
                return_value={"expected_methods": 23}))
            stack.enter_context(patch.object(wave.shared, "verify_signed_simulator",
                side_effect=ValueError("controlled post-build admission failure")))
            with self.assertRaisesRegex(ValueError, "controlled post-build admission failure"):
                wave.execute(args, receipt)
        self.assertTrue(receipt["native_build_succeeded"])
        archived = self.evidence / receipt["early_products"]["archive_path"]
        self.assertTrue(archived.is_file())
        actual_builds = [call.args[0] for call in command.call_args_list if call.args[0][:2] == ["xcodebuild", "build-for-testing"]]
        self.assertEqual(len(actual_builds), 1)
        with tarfile.open(archived, "r:gz") as packed:
            self.assertEqual(packed.extractfile("Build/Products/Anytype_iphonesimulator.xctestrun").read(),
                             self.configuration.read_bytes())


if __name__ == "__main__":
    unittest.main()
