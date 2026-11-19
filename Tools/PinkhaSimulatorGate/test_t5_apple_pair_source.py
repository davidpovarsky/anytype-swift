"""Real Git controls for the T5 job's exact-source admission boundary."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import run_t5_apple_pair as pair


class PublishedSourceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "app"
        self.repo.mkdir()
        self.proof = self.repo / "build/proof"
        self.source = self.repo / "source.swift"
        self.source.write_text("let value = 1\n")
        app = Path(__file__).resolve().parents[2]
        (self.repo / ".gitignore").write_bytes((app / ".gitignore").read_bytes())
        self.git("init", "-q")
        self.git("add", "--", "source.swift", ".gitignore")
        self.git("-c", "user.name=Source Control", "-c", "user.email=source-control@example.invalid",
                 "commit", "-q", "-m", "source fixture")
        self.sha = self.git("rev-parse", "HEAD")
        self.environment = patch.dict(os.environ, {"GITHUB_SHA": self.sha, "GITHUB_RUN_ID": "123456"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()

    def receipt(self):
        return json.loads((self.proof / "source-preflight.json").read_text())

    def test_existing_ci_checkout_location_is_rejected_and_observed(self):
        package = self.repo / ".ci/hanlin-source"
        package.mkdir(parents=True)
        (package / "Package.swift").write_text("// pinned dependency\n")
        subprocess.run(["git", "init", "-q", str(package)], check=True)
        with self.assertRaisesRegex(RuntimeError, "Exact clean published App"):
            pair.verify_published_source(self.repo, self.proof)
        observed = self.receipt()
        self.assertEqual(observed["status"], "FAIL")
        self.assertEqual(observed["actual_source_sha"], self.sha)
        self.assertFalse(observed["tracked_and_untracked_clean"])
        self.assertIn(".ci/", observed["git_porcelain"])

    def test_owned_build_inputs_preserve_clean_exact_source_and_workflow_contract(self):
        for name in ("build/t5-apple-hanlin-source/Package.swift", "build/t5-apple-native-source/source.json",
                     "build/t5-apple-pair-private/owned.json", "Dependencies/Hanlin/Package.swift"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("pinned fixture input\n")
        self.assertEqual(pair.verify_published_source(self.repo, self.proof), self.sha)
        self.assertEqual(pair.verify_published_source(self.repo, self.proof), self.sha)
        self.assertEqual(self.receipt()["status"], "PASS")
        self.assertEqual(self.receipt()["git_porcelain"], "")
        app = Path(__file__).resolve().parents[2]
        workflow = (app / ".github/workflows/pinkha-t5-apple-pair.yml").read_text()
        self.assertIn("      PYTHONDONTWRITEBYTECODE: '1'\n", workflow)
        self.assertIn("          path: build/t5-apple-hanlin-source\n", workflow)
        self.assertIn("prepare_sdk.py --source build/t5-apple-hanlin-source\n", workflow)
        self.assertNotIn(".ci/hanlin-source", workflow)

    def test_tracked_and_untracked_changes_are_still_rejected(self):
        self.source.write_text("let value = 2\n")
        with self.assertRaises(RuntimeError):
            pair.verify_published_source(self.repo, self.proof)
        self.assertIn("source.swift", self.receipt()["git_porcelain"])
        self.source.write_text("let value = 1\n")
        extra = self.repo / "Tools/__pycache__/unexpected.pyc"
        extra.parent.mkdir(parents=True)
        extra.write_bytes(b"unreviewed bytecode")
        with self.assertRaises(RuntimeError):
            pair.verify_published_source(self.repo, self.proof)
        self.assertIn("Tools/", self.receipt()["git_porcelain"])

    def test_wrong_source_and_missing_or_invalid_run_are_still_rejected(self):
        for changes in ({"GITHUB_SHA": "0" * 40}, {"GITHUB_SHA": ""},
                        {"GITHUB_RUN_ID": ""}, {"GITHUB_RUN_ID": "not-a-run"}):
            with self.subTest(changes=changes), patch.dict(os.environ, changes), self.assertRaises(RuntimeError):
                pair.verify_published_source(self.repo, self.proof)
            self.assertEqual(self.receipt()["status"], "FAIL")
            self.assertTrue(self.receipt()["tracked_and_untracked_clean"])


if __name__ == "__main__":
    unittest.main()
