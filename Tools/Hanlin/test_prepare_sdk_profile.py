#!/usr/bin/env python3
"""Focused real-file controls for an already installed isolated SDK profile.

These mutate only the owned dependency checkout temporarily and always restore
the original bytes. They do not resolve packages, build or execute Apple tests.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
import prepare_sdk as prepare


class PreparedProfileGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sdk = prepare.DESTINATION
        cls.marker = cls.sdk / prepare.MARKER
        cls.original = cls.marker.read_bytes()
        cls.record = prepare.verify(cls.sdk)
        cls.swift = cls.sdk / next(name for name in cls.record["git_blobs"]
                                  if name.startswith("Packages/HanlinAgentSDK/Sources/") and name.endswith(".swift"))

    def tearDown(self):
        self.assertEqual(self.marker.read_bytes(), self.original)

    def test_forged_compatibility_receipt_is_not_trusted(self):
        forged = json.loads(self.original)
        name = next(iter(forged["files"]))
        forged["files"][name] = "0" * 64
        try:
            self.marker.write_text(json.dumps(forged))
            with self.assertRaisesRegex(ValueError, "receipt differs"):
                prepare.verify(self.sdk)
        finally:
            self.marker.write_bytes(self.original)

    def test_source_and_compatibility_hash_forgery_is_rejected(self):
        original = self.swift.read_bytes()
        forged = json.loads(self.original)
        relative = self.swift.relative_to(self.sdk).as_posix()
        try:
            self.swift.write_bytes(original + b"\n// external source modification\n")
            forged["files"][relative] = hashlib.sha256(self.swift.read_bytes()).hexdigest()
            self.marker.write_text(json.dumps(forged))
            with self.assertRaisesRegex(ValueError, "source bytes differ"):
                prepare.verify(self.sdk)
        finally:
            self.swift.write_bytes(original)
            self.marker.write_bytes(self.original)

    def test_ignored_extra_compiler_input_is_rejected(self):
        extra = self.swift.parent / "UnexpectedSDKSource.swift"
        self.assertFalse(extra.exists())
        exclude = Path(prepare.git(self.sdk, "rev-parse", "--git-path", "info/exclude"))
        if not exclude.is_absolute():
            exclude = self.sdk / exclude
        original = exclude.read_bytes()
        try:
            exclude.write_bytes(original + b"\nUnexpectedSDKSource.swift\n")
            extra.write_text("public let unexpectedSDKSource = true\n")
            with self.assertRaisesRegex(ValueError, "directory membership differs"):
                prepare.verify(self.sdk)
        finally:
            if extra.exists():
                extra.unlink()
            exclude.write_bytes(original)

    def test_matching_forged_generated_hashes_do_not_admit_a_changed_graph(self):
        package = self.sdk / "Package.swift"
        state_path = self.sdk / ".hanlin-sdk/installation.json"
        original_package = package.read_bytes()
        original_state = state_path.read_bytes()
        state = json.loads(original_state)
        marker = json.loads(self.original)
        try:
            package.write_bytes(original_package + b"\n// changed generated profile\n")
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            state["generatedSHA256"]["Package.swift"] = digest
            marker["files"]["Package.swift"] = digest
            marker["source_profile"]["generated_sha256"]["Package.swift"] = digest
            state_path.write_text(json.dumps(state))
            self.marker.write_text(json.dumps(marker))
            with self.assertRaises(subprocess.CalledProcessError):
                prepare.verify(self.sdk)
        finally:
            package.write_bytes(original_package)
            state_path.write_bytes(original_state)
            self.marker.write_bytes(self.original)

    @classmethod
    def tearDownClass(cls):
        if cls.marker.read_bytes() != cls.original or prepare.verify(cls.sdk) != cls.record:
            raise AssertionError("The owned SDK profile was not restored exactly")


if __name__ == "__main__":
    unittest.main(verbosity=2)
