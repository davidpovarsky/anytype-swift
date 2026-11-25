#!/usr/bin/env python3
"""Focused checks for materializing a newer exact SDK pin from an older read-only checkout."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("miniapps_prepare_sdk", Path(__file__).parents[1] / "Hanlin/prepare_sdk.py")
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)

def git(path, *arguments):
    return subprocess.check_output(["git", "-C", str(path), *arguments], stderr=subprocess.PIPE, text=True).strip()

class SDKPinMaterializationTests(unittest.TestCase):
    def testMissingPinUsesOwnedFetchWithoutChangingSuppliedSource(self):
        previous_pin, previous_destination = prepare.PIN, prepare.DESTINATION
        with tempfile.TemporaryDirectory(prefix="miniapps-pin-test-") as temporary:
            root = Path(temporary)
            remote = root / "remote"
            remote.mkdir()
            git(remote, "init")
            git(remote, "config", "user.name", "Fixture")
            git(remote, "config", "user.email", "fixture@example.test")
            package = remote / "Packages/Bridge"
            package.mkdir(parents=True)
            (package / "Package.swift").write_text("// first fixture\n")
            git(remote, "add", ".")
            git(remote, "commit", "-m", "First fixture")
            old = git(remote, "rev-parse", "HEAD")
            supplied = root / "supplied"
            subprocess.run(["git", "clone", "--depth=1", remote.as_uri(), str(supplied)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (package / "Package.swift").write_text("// exact second fixture\n")
            git(remote, "add", ".")
            git(remote, "commit", "-m", "Second fixture")
            new = git(remote, "rev-parse", "HEAD")
            objects_before = git(supplied, "count-objects", "-v")
            try:
                prepare.PIN = dict(repository=remote.as_uri(), revision=new, packages=["Packages/Bridge"])
                prepare.DESTINATION = root / "snapshot"
                prepare.materialize(supplied)
                self.assertEqual(prepare.verify(prepare.DESTINATION)["revision"], new)
                self.assertEqual((prepare.DESTINATION / "Packages/Bridge/Package.swift").read_text(),
                                 "// exact second fixture\n")
                self.assertEqual(git(supplied, "rev-parse", "HEAD"), old)
                self.assertEqual(git(supplied, "status", "--porcelain"), "")
                self.assertEqual(git(supplied, "count-objects", "-v"), objects_before)
            finally:
                prepare.PIN, prepare.DESTINATION = previous_pin, previous_destination

    def testMismatchedExistingSnapshotRemainsUnchanged(self):
        previous_pin = prepare.PIN
        with tempfile.TemporaryDirectory(prefix="miniapps-snapshot-test-") as temporary:
            root = Path(temporary)
            marker = root / prepare.MARKER
            original = json.dumps({"revision": "old", "files": {}})
            marker.write_text(original)
            try:
                prepare.PIN = {"revision": "new", "packages": []}
                with self.assertRaises(ValueError):
                    prepare.verify(root)
                self.assertEqual(marker.read_text(), original)
            finally:
                prepare.PIN = previous_pin

if __name__ == "__main__":
    unittest.main()
