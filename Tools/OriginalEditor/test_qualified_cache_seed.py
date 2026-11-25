"""Integrity controls for cache admission; no native acceptance credit."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import qualified_cache_seed as subject

class CacheInputControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def test_exact_receipt_bytes_are_required(self):
        p = self.root / "proof.json"
        p.write_text('{"status":"PASS"}\n')
        row = {"path": p.name, "sha256": subject.sha(p)}
        self.assertEqual(subject.read_exact(self.root, row), {"status": "PASS"})
        p.write_text('{"status":"FAIL"}\n')
        with self.assertRaisesRegex(RuntimeError, "bytes changed"):
            subject.read_exact(self.root, row)

    def test_aliased_receipt_is_rejected(self):
        p = self.root / "original.json"
        p.write_text("{}")
        (self.root / "alias.json").symlink_to(p)
        with self.assertRaisesRegex(RuntimeError, "missing or aliased"):
            subject.read_exact(self.root, {"path": "alias.json", "sha256": subject.sha(p)})

    def fixture(self):
        seed = self.root / "donor/build/SDK-Work-7/producer-derived-preserved"
        target = self.root / "current/build/SDK-Work/producer-derived"
        evidence = self.root / "evidence"
        evidence.mkdir()
        objects = seed / "SourcePackages/repositories/example/objects"
        (objects / "pack").mkdir(parents=True)
        (objects / "pack/pack-a.pack").write_bytes(b"retained-object-bytes")
        metadata = seed / "SourcePackages/checkouts/example/.git/objects/info/alternates"
        metadata.parent.mkdir(parents=True)
        original_path = seed.with_name("producer-derived") / objects.relative_to(seed)
        metadata.write_text(str(original_path) + "\n")
        metadata.chmod(0o444)
        shutil.copytree(seed, target)
        return seed, target, evidence, metadata

    def test_private_relocation_retains_original_bytes_and_modes(self):
        seed, target, evidence, original = self.fixture()
        old = original.read_bytes()
        result = subject.relocate_git(seed, target, evidence)
        self.assertEqual(result["status"], "VERIFIED_PRIVATE_GIT_ALTERNATES_RELOCATED")
        self.assertEqual(original.read_bytes(), old)
        copied = target / original.relative_to(seed)
        self.assertEqual(copied.stat().st_mode & 0o777, 0o444)
        self.assertIn(str(target), copied.read_text())
        self.assertFalse(result["grants_product_acceptance"])

    def test_changed_copied_object_is_rejected(self):
        seed, target, evidence, _ = self.fixture()
        (target / "SourcePackages/repositories/example/objects/pack/pack-a.pack").write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "objects differ"):
            subject.relocate_git(seed, target, evidence)

    def test_external_git_store_is_rejected(self):
        seed, target, evidence, original = self.fixture()
        original.chmod(0o644)
        original.write_text("/unowned/objects\n")
        copy = target / original.relative_to(seed)
        copy.chmod(0o644)
        copy.write_bytes(original.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "outside released cache"):
            subject.relocate_git(seed, target, evidence)

    def test_changed_metadata_is_rejected(self):
        seed, target, evidence, original = self.fixture()
        copy = target / original.relative_to(seed)
        copy.chmod(0o644)
        copy.write_text("/new/objects\n")
        with self.assertRaisesRegex(RuntimeError, "changed before admission"):
            subject.relocate_git(seed, target, evidence)

    def test_aliased_object_cannot_be_silently_ignored(self):
        seed, target, evidence, _ = self.fixture()
        (target / "SourcePackages/repositories/example/objects/unreviewed").symlink_to("/unowned")
        with self.assertRaisesRegex(RuntimeError, "Aliased"):
            subject.relocate_git(seed, target, evidence)

if __name__ == "__main__":
    unittest.main()
