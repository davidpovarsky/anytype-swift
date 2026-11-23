"""Focused controls for the actual package authorization failure."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import authorize_canonical_sdk_macro as macro


class ExactMacroAuthorizationTests(unittest.TestCase):
    def fixture(self, directory):
        app = Path(directory) / "app"
        derived = Path(directory) / "derived"
        checkout = derived / "SourcePackages/checkouts/equatable"
        checkout.mkdir(parents=True)
        (checkout / "Sources/EquatableMacros").mkdir(parents=True)
        (checkout / "Package.swift").write_text('let target = .macro(name: "EquatableMacros")\n')
        (checkout / "Sources/EquatableMacros/Original.swift").write_text("original source\n")
        def git(*args):
            return subprocess.check_output(["git", "-C", str(checkout), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init")
        git("remote", "add", "origin", macro.ORIGIN)
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "Original fixture")
        revision = git("rev-parse", "HEAD")
        lock = app / macro.LOCK_PATH
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"pins": [{"identity": "equatable", "kind": "remoteSourceControl",
            "location": macro.ORIGIN, "state": {"revision": revision, "version": "1.4.1"}}]}))
        return app, derived, checkout, revision, git

    def test_exact_checkout_adds_one_target_preserves_other_entries_mode_and_idempotence(self):
        with tempfile.TemporaryDirectory() as directory:
            app, derived, checkout, revision, git = self.fixture(directory)
            security = Path(directory) / "security";security.mkdir()
            path = security / "macros.json"
            prior = {"fingerprint": "a"*40, "packageIdentity": "original-package", "targetName": "OriginalMacro"}
            path.write_text(json.dumps([prior]));path.chmod(0o640)
            with patch.object(macro, "REVISION", revision):
                source = macro.verify_source(app, derived)
                first = macro.authorize(source, security)
                saved = path.read_bytes()
                second = macro.authorize(macro.verify_source(app, derived), security)
            self.assertEqual(len(source["source_files"]), 2)
            self.assertEqual(json.loads(saved)[0], prior)
            self.assertEqual(len(json.loads(saved)), 2)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertTrue(first["entry_added"])
            self.assertFalse(second["entry_added"])
            self.assertTrue(first["normal_xcode_fingerprint_validation"])
            self.assertEqual(path.read_bytes(), saved)

    def test_dirty_or_hidden_changed_macro_source_is_never_authorized(self):
        for index_flag in [None, "--assume-unchanged", "--skip-worktree"]:
            with self.subTest(index_flag=index_flag), tempfile.TemporaryDirectory() as directory:
                app, derived, checkout, revision, git = self.fixture(directory)
                path = "Sources/EquatableMacros/Original.swift"
                if index_flag:git("update-index", index_flag, path)
                (checkout / path).write_text("changed source\n")
                with patch.object(macro, "REVISION", revision), self.assertRaises(ValueError):
                    macro.verify_source(app, derived)

    def test_lock_revision_and_untracked_compilation_input_drift_are_rejected(self):
        for change in ["lock", "revision", "untracked"]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                app, derived, checkout, revision, git = self.fixture(directory)
                if change == "lock":
                    p = app / macro.LOCK_PATH;x=json.loads(p.read_text())
                    x["pins"][0]["state"]["revision"]="b"*40;p.write_text(json.dumps(x))
                elif change == "revision":
                    (checkout/"README").write_text("new revision")
                    git("add", ".");git("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","commit","-m","Other")
                else:
                    (checkout/"Sources/EquatableMacros/Unreviewed.swift").write_text("unreviewed")
                with patch.object(macro, "REVISION", revision), self.assertRaises(ValueError):
                    macro.verify_source(app, derived)

    def test_real_shared_working_copy_from_local_git_cache_retains_exact_source_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            app, derived, checkout, revision, git = self.fixture(directory)
            cached = derived / "SourcePackages/repositories/equatable-cache"
            cached.parent.mkdir(parents=True)
            checkout.rename(cached)
            subprocess.run(["git", "clone", "--shared", "--no-checkout", str(cached), str(checkout)],
                           check=True, capture_output=True)
            git("checkout", "--detach", revision)
            with patch.object(macro, "REVISION", revision):
                source = macro.verify_source(app, derived)
            self.assertEqual(source["checkout_origin"], str(cached))
            self.assertEqual(source["revision"], revision)
            self.assertEqual(len(source["source_files"]), 2)

    def test_malformed_and_linked_compiler_store_fail_without_changing_prior_bytes(self):
        for linked in [False, True]:
            with self.subTest(linked=linked), tempfile.TemporaryDirectory() as directory:
                app, derived, checkout, revision, git = self.fixture(directory)
                security=Path(directory)/"security";security.mkdir()
                original=Path(directory)/"untouched.json";original.write_text('{"invalid":"schema"}')
                path=security/"macros.json"
                if linked:path.symlink_to(original)
                else:path.write_bytes(original.read_bytes())
                before=original.read_bytes()
                with patch.object(macro,"REVISION",revision):
                    source=macro.verify_source(app,derived)
                    with self.assertRaises(ValueError):macro.authorize(source,security)
                self.assertEqual(original.read_bytes(),before)
                self.assertEqual(path.read_bytes(),before)


if __name__ == "__main__":
    unittest.main()
