"""Actual filesystem controls for the generated dependency-lock lifecycle."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import native_continuation_sources as sources
import preserve_native_resolution as resolution

ROOT = Path(__file__).resolve().parents[2]


class NativeResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.canonical = self.root / resolution.CANONICAL
        self.canonical.parent.mkdir(parents=True)
        self.expected = (ROOT / resolution.CANONICAL).read_bytes()
        self.canonical.write_bytes(self.expected)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Lock Test",
                        "-c", "user.email=lock@invalid", "commit", "-qm", "Published pins"], check=True)
        self.generated = self.root / resolution.GENERATED
        self.generated.parent.mkdir(parents=True)
        value = json.loads(self.expected)
        value["originHash"] = "1" * 64
        value["pins"].reverse()
        self.raw = json.dumps(value, indent=4).encode() + b"\n"
        self.generated.write_bytes(self.raw)
        self.derived = self.root / "build/derived"
        products = self.derived / "Build/Products"
        products.mkdir(parents=True)
        (products / "PinkhaAnyNativeApp_fixture.xctestrun").write_bytes(b"original configuration")
        self.evidence = self.root / "build/lock-evidence"

    def run_preserve(self):
        return resolution.preserve(self.root, self.evidence, self.derived)

    def test_exact_pins_preserve_original_bytes_and_restore_original_clean_fence(self):
        with self.assertRaisesRegex(ValueError, "consumer_source_worktree_not_clean"):
            sources.verify_worktree(self.root)
        result = self.run_preserve()
        self.assertFalse(self.generated.exists())
        self.assertEqual((self.evidence / "generated-Package.resolved").read_bytes(), self.raw)
        self.assertEqual((self.evidence / "canonical-Package.resolved").read_bytes(), self.expected)
        self.assertEqual(result["generatedSHA256"], resolution.digest(self.raw))
        self.assertFalse(result["buildProductsAccepted"])
        self.assertEqual(result["testsExecuted"], 0)
        sources.verify_worktree(self.root)

    def test_changed_pin_revision_origin_url_extra_and_missing_are_refused_without_removal(self):
        original = json.loads(self.raw)
        variants = []
        value = copy.deepcopy(original)
        value["pins"][0]["state"]["revision"] = "a" * 40
        variants.append(value)
        value = copy.deepcopy(original)
        value["pins"][0]["location"] += "-other"
        variants.append(value)
        value = copy.deepcopy(original)
        extra = copy.deepcopy(value["pins"][0])
        extra["identity"] = "unexpected-dependency"
        value["pins"].append(extra)
        variants.append(value)
        value = copy.deepcopy(original)
        value["pins"].pop()
        variants.append(value)
        for value in variants:
            with self.subTest(value=value["pins"][0]["identity"]):
                raw = json.dumps(value).encode()
                self.generated.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "generated_dependency_pins_changed"):
                    self.run_preserve()
                self.assertEqual(self.generated.read_bytes(), raw)
                self.assertFalse(self.evidence.exists())

    def test_duplicate_identity_and_duplicate_json_key_are_refused(self):
        value = json.loads(self.raw)
        value["pins"].append(value["pins"][0])
        for raw in (json.dumps(value).encode(), self.raw.replace(b'"version": 3', b'"version": 3, "version": 3')):
            self.generated.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                self.run_preserve()
            self.assertEqual(self.generated.read_bytes(), raw)

    def test_other_dirty_source_or_changed_canonical_lock_remains_rejected(self):
        extra = self.root / "Modules/Unexpected.swift"
        extra.write_text("unreviewed source\n")
        with self.assertRaisesRegex(ValueError, "only_owned_generated"):
            self.run_preserve()
        self.assertTrue(self.generated.exists())
        self.assertTrue(extra.exists())
        extra.unlink()
        self.canonical.write_bytes(self.expected + b"\n")
        with self.assertRaisesRegex(ValueError, "only_owned_generated"):
            self.run_preserve()
        self.assertTrue(self.generated.exists())

    def test_symlink_generated_output_is_refused_without_changing_target(self):
        self.generated.unlink()
        target = self.root / "build/external-lock"
        target.write_bytes(self.raw)
        self.generated.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "package_path_symlink"):
            self.run_preserve()
        self.assertTrue(self.generated.is_symlink())
        self.assertEqual(target.read_bytes(), self.raw)

    def test_preexisting_preserved_evidence_is_never_overwritten(self):
        self.evidence.mkdir()
        original = self.evidence / "receipt.json"
        original.write_bytes(b"original evidence")
        with self.assertRaisesRegex(ValueError, "new_owned_evidence"):
            self.run_preserve()
        self.assertEqual(original.read_bytes(), b"original evidence")
        self.assertEqual(self.generated.read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
