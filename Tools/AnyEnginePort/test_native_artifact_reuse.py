"""Behavioral checks for reusing a prior native binary without relabeling evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import prepare_native_runtime as runtime


class NativeArtifactReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run_git("init", "-q")
        self.run_git("config", "user.name", "Test")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("config", "core.autocrlf", "false")
        self.manifest = {}
        for name in ("any", "sdk"):
            content = (name + " exact native patch\n").encode()
            (self.root / (name + ".patch")).write_bytes(content)
            self.manifest[name] = {
                "upstreamCommit": runtime.PINNED_COMMITS[name],
                "resolvedUpstreamCommit": runtime.PINNED_COMMITS[name],
                "patch": name + ".patch",
                "patchSHA256": hashlib.sha256(content).hexdigest(),
                "files": [{"path": "native.go", "gitBlob": "a" * 40}],
                "testedEffectiveTree": ("b" if name == "any" else "c") * 40,
            }
        self.path = self.root / "manifest.json"
        self.path.write_bytes(json.dumps(self.manifest, sort_keys=True).encode())
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "native producer")
        self.producer = self.run_git("rev-parse", "HEAD")
        (self.root / "application.swift").write_bytes(b"changed consumer\n")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "application consumer")
        self.consumer = self.run_git("rev-parse", "HEAD")
        self.receipt = {"sourceCommit": self.producer,
                        "sourceManifestSHA256": runtime.digest(self.path),
                        "sources": copy.deepcopy(self.manifest),
                        "archiveSHA256": "d" * 64}
        self.root_patch = patch.object(runtime, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def run_git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                       text=True, stderr=subprocess.STDOUT).strip()

    def validate(self, producer=None):
        return runtime.validate_artifact_source(self.receipt, self.manifest, self.path, producer)

    def test_unchanged_native_inputs_reuse_with_original_provenance(self):
        before = copy.deepcopy(self.receipt)
        result = self.validate(self.producer)
        self.assertTrue(result["reused"])
        self.assertEqual(result["producerCommit"], self.producer)
        self.assertEqual(result["consumerCommit"], self.consumer)
        self.assertFalse(result["testResultsRelabeled"])
        self.assertEqual(self.receipt, before)

    def test_prior_binary_requires_explicit_exact_producer(self):
        for producer in (None, self.consumer, "0" * 40):
            with self.subTest(producer=producer), self.assertRaises(ValueError):
                self.validate(producer)

    def test_changed_native_patch_rejects_reuse(self):
        (self.root / "any.patch").write_bytes(b"different native code\n")
        with self.assertRaisesRegex(ValueError, "build input changed"):
            self.validate(self.producer)

    def test_changed_manifest_rejects_reuse_even_if_receipt_hash_is_rewritten(self):
        self.manifest["any"]["testedEffectiveTree"] = "e" * 40
        self.path.write_bytes(json.dumps(self.manifest, sort_keys=True).encode())
        self.receipt["sourceManifestSHA256"] = runtime.digest(self.path)
        self.receipt["sources"] = copy.deepcopy(self.manifest)
        with self.assertRaisesRegex(ValueError, "build input changed"):
            self.validate(self.producer)

    def test_receipt_effective_tree_must_match_full_native_contract(self):
        self.receipt["sources"]["sdk"]["testedEffectiveTree"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "source contract mismatch"):
            self.validate(self.producer)

    def test_same_commit_still_validates_native_sources(self):
        self.receipt["sourceCommit"] = self.consumer
        self.assertFalse(self.validate()["reused"])
        self.receipt["sources"]["any"]["files"] = []
        with self.assertRaisesRegex(ValueError, "source contract mismatch"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
