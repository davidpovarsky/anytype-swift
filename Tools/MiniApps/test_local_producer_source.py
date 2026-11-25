"""Git integrity controls only; these fixtures grant no native/app acceptance."""
import hashlib
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from local_producer_source import validate_source_identity


class PreparedSourceIntegrity(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="anytype-prepared-source-control-")
        self.root = Path(self.temporary.name)
        self.sdk = self.root / "sdk"
        self.sdk.mkdir()
        self.run_git("init", "-q")
        (self.sdk / "engine.js").write_text("export const originalSource = true;\n")
        (self.sdk / "other.js").write_text("export const other = true;\n")
        self.run_git("add", "engine.js", "other.js")
        self.run_git("-c", "user.name=Integrity Control", "-c", "user.email=control@example.invalid",
                     "commit", "-q", "-m", "Original control source")
        self.sha = self.run_git("rev-parse", "HEAD")
        self.export = self.root / "export"
        self.export.mkdir()
        self.manifest = {"source_identity": {
            "commit": self.sha, "tree": self.run_git("rev-parse", "HEAD^{tree}"),
            "tracked_file_sha256": {name: self.digest(self.sdk / name)
                                   for name in ["engine.js", "other.js"]}}}
        self.config = {}

    def tearDown(self):
        self.temporary.cleanup()

    def run_git(self, *arguments):
        return subprocess.check_output(["git", "-C", str(self.sdk), *arguments], text=True).strip()

    @staticmethod
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def save_manifest(self):
        pass  # These controls exercise source objects directly, not an app manifest.

    def validate(self):
        return validate_source_identity(self.manifest["source_identity"], self.sdk, self.sha,
            review_spec=self.config.get("local_producer_preparation"), export_directory=self.export,
            consumer_root=getattr(self, "consumer", None))

    def test_clean_original_source_is_verified(self):
        self.assertEqual(self.validate()["verified_source_files"], 2)

    def test_incorrect_source_blob_is_rejected(self):
        self.manifest["source_identity"]["tracked_file_sha256"]["engine.js"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source bytes differ"):
            self.validate()

    def make_preparation(self, extra_path=False):
        original_tree = self.run_git("rev-parse", self.sha + "^{tree}")
        (self.sdk / "engine.js").write_text("export const originalSource = 'prepared control';\n")
        if extra_path:
            (self.sdk / "other.js").write_text("export const other = 'unreviewed preparation';\n")
        self.patch = self.export / "source-preparation.diff"
        self.patch.write_bytes(subprocess.check_output(["git", "-C", str(self.sdk), "diff", "--binary", self.sha]))
        with tempfile.TemporaryDirectory() as temporary:
            objects = Path(temporary) / "objects"
            objects.mkdir()
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary) / "index"),
                       GIT_OBJECT_DIRECTORY=str(objects),
                       GIT_ALTERNATE_OBJECT_DIRECTORIES=str(self.sdk / ".git/objects"))
            for arguments in (["read-tree", self.sha], ["apply", "--cached", "--binary", str(self.patch)]):
                subprocess.run(["git", "-C", str(self.sdk), *arguments], check=True, env=env, capture_output=True)
            prepared = subprocess.check_output(["git", "-C", str(self.sdk), "write-tree"], env=env, text=True).strip()
            def proof(tree):
                row = subprocess.check_output(["git", "-C", str(self.sdk), "ls-tree", tree,
                                               "--", "engine.js"], env=env, text=True).split("\t")[0].split()
                blob = subprocess.check_output(["git", "-C", str(self.sdk), "cat-file", "blob", row[2]], env=env)
                return {"mode": row[0], "blob": row[2], "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
            before, after = proof(original_tree), proof(prepared)
        self.review = {
            "schema": "miniapps.producer-preparation-review/1",
            "producer_sha": self.sha, "source_tree": original_tree, "prepared_tree": prepared,
            "git_status_porcelain": " M engine.js\n",
            "patch": {"name": self.patch.name, "bytes": self.patch.stat().st_size, "sha256": self.digest(self.patch)},
            "changes": [{"path": "engine.js", "status": "M", "before": before,
                         "after": after, "reason": "Synthetic prepared-source admission control only."}],
        }
        identity = self.manifest["source_identity"]
        identity.update({"git_status_porcelain": self.review["git_status_porcelain"],
                         "preparation_diff_name": self.patch.name, "preparation_diff_sha256": self.digest(self.patch),
                         "prepared_tree": prepared})
        identity["tracked_file_sha256"]["engine.js"] = self.digest(self.sdk / "engine.js")
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        subprocess.run(["git", "-C", str(self.consumer), "init", "-q"], check=True)
        self.review_path = self.consumer / "Tools/MiniApps/preparation.json"
        self.review_path.parent.mkdir(parents=True)
        self.config["local_producer_preparation"] = {"path": "Tools/MiniApps/preparation.json"}
        self.save_review()
        self.save_manifest()

    def save_review(self, commit=True):
        self.review_path.write_text(json.dumps(self.review, sort_keys=True))
        self.config["local_producer_preparation"]["sha256"] = self.digest(self.review_path)
        if commit:
            subprocess.run(["git", "-C", str(self.consumer), "add", "Tools/MiniApps/preparation.json"], check=True)
            subprocess.run(["git", "-C", str(self.consumer), "-c", "user.name=Admission Control",
                            "-c", "user.email=control@example.invalid", "commit", "-q", "--allow-empty",
                            "-m", "Explicit synthetic preparation review"], check=True)

    def test_exact_reviewed_preparation_is_independently_reconstructed_without_index_mutation(self):
        self.make_preparation()
        index = self.digest(self.sdk / ".git/index")
        status = self.run_git("status", "--porcelain")
        result = self.validate()
        self.assertEqual(result["prepared_tree"], self.review["prepared_tree"])
        self.assertEqual(self.digest(self.sdk / ".git/index"), index)
        self.assertEqual(self.run_git("status", "--porcelain"), status)

    def test_dirty_preparation_without_committed_review_is_rejected(self):
        self.make_preparation()
        del self.config["local_producer_preparation"]
        with self.assertRaisesRegex(ValueError, "Dirty producer preparation requires"):
            self.validate()

    def test_claimed_clean_status_cannot_hide_prepared_patch(self):
        self.make_preparation()
        del self.config["local_producer_preparation"]
        self.manifest["source_identity"]["git_status_porcelain"] = ""
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Prepared producer source requires"):
            self.validate()

    def test_uncommitted_review_cannot_admit_preparation(self):
        self.make_preparation()
        self.review["changes"][0]["reason"] = "Uncommitted change"
        self.save_review(commit=False)
        with self.assertRaisesRegex(ValueError, "not the exact committed file"):
            self.validate()

    def test_changed_preparation_patch_is_rejected(self):
        self.make_preparation()
        self.patch.write_bytes(self.patch.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "patch bytes differ"):
            self.validate()

    def test_reviewed_but_wrong_prepared_tree_is_rejected(self):
        self.make_preparation()
        self.review["prepared_tree"] = self.review["source_tree"]
        self.manifest["source_identity"]["prepared_tree"] = self.review["source_tree"]
        self.save_review()
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Reconstructed producer preparation tree differs"):
            self.validate()

    def test_extra_prepared_path_is_rejected_even_when_tree_and_patch_hashes_match(self):
        self.make_preparation(extra_path=True)
        with self.assertRaisesRegex(ValueError, "tree contains unreviewed changes"):
            self.validate()

    def test_preparation_index_status_cannot_be_relabelled_as_worktree_preparation(self):
        self.make_preparation()
        self.review["git_status_porcelain"] = "M  engine.js\n"
        self.manifest["source_identity"]["git_status_porcelain"] = "M  engine.js\n"
        self.save_review()
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "unreviewed index or working-tree"):
            self.validate()

    def test_preparation_before_blob_must_match_actual_git_source(self):
        self.make_preparation()
        self.review["changes"][0]["before"]["blob"] = "0" * 40
        self.save_review()
        with self.assertRaisesRegex(ValueError, "before object differs"):
            self.validate()

    def test_preparation_after_bytes_must_match_actual_reconstructed_blob(self):
        self.make_preparation()
        self.review["changes"][0]["after"]["sha256"] = "0" * 64
        self.save_review()
        with self.assertRaisesRegex(ValueError, "after object differs"):
            self.validate()

    def test_prepared_inventory_cannot_fall_back_to_unprepared_bytes(self):
        self.make_preparation()
        self.manifest["source_identity"]["tracked_file_sha256"]["engine.js"] = self.review["changes"][0]["before"]["sha256"]
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "source bytes differ"):
            self.validate()

    def test_preparation_review_cannot_be_a_symlink(self):
        self.make_preparation()
        saved = self.consumer / "unreviewed.json"
        saved.write_bytes(self.review_path.read_bytes())
        self.review_path.unlink()
        self.review_path.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, "review bytes differ"):
            self.validate()

    def test_clean_generated_metadata_still_requires_empty_patch_and_original_tree(self):
        self.patch = self.export / "source-preparation.diff"
        self.patch.write_bytes(b"")
        self.manifest["source_identity"].update({
            "git_status_porcelain": "", "preparation_diff_name": self.patch.name,
            "preparation_diff_sha256": self.digest(self.patch),
            "prepared_tree": self.manifest["source_identity"]["tree"],
        })
        self.save_manifest()
        self.validate()

    def test_reconstruction_never_writes_producer_object_store(self):
        self.make_preparation()
        before = {str(p.relative_to(self.sdk)): self.digest(p)
                  for p in (self.sdk / ".git/objects").rglob("*") if p.is_file()}
        missing = subprocess.run(["git", "-C", str(self.sdk), "cat-file", "-e",
                                  self.review["prepared_tree"]], capture_output=True)
        self.assertNotEqual(missing.returncode, 0)
        self.validate()
        after = {str(p.relative_to(self.sdk)): self.digest(p)
                 for p in (self.sdk / ".git/objects").rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertNotEqual(subprocess.run(["git", "-C", str(self.sdk), "cat-file", "-e",
            self.review["prepared_tree"]], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
