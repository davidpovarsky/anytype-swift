"""New bounded controls for exact macro approval and owned restoration.

Uses actual review files and helper functions with temporary files and explicit
archive/path/context probes. No Apple build, macro expansion, or Native credit.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import prepare_reviewed_macro as actual

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/pinkha/torah-integration/evidence/original-editor-equatable-macro-20261122/reviewed-source"
REVIEW = actual.read_review(ROOT)
PIN = actual.verify_pin(json.loads((ROOT / actual.LOCK).read_bytes()))
ENV = {"GITHUB_RUN_ID": "EXPLICIT_LOCAL_MACRO_CONTROL", "GITHUB_SHA": "f" * 40}


def archive_with(change=None, extra=None, special=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for row in REVIEW["reviewed_files"]:
            path = row["path"]
            body = (SOURCE / path).read_bytes()
            if path == change:
                body += b"\n// changed source\n"
            entry = tarfile.TarInfo("reviewed-root/" + path)
            entry.size = len(body)
            archive.addfile(entry, io.BytesIO(body))
        if extra:
            entry = tarfile.TarInfo(extra)
            entry.size = 1
            archive.addfile(entry, io.BytesIO(b"x"))
        if special:
            entry = tarfile.TarInfo("reviewed-root/linked.swift")
            entry.type = special
            entry.linkname = "../foreign.swift"
            archive.addfile(entry)
    return output.getvalue()


def owned_state(home, evidence, before):
    target = actual.checked_target(home)
    if before is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before)
    after, added = actual.merge_approval(before)
    evidence.mkdir()
    if before is not None:
        (evidence / "macros.before.json").write_bytes(before)
    (evidence / "macros.after.json").write_bytes(after)
    actual.write_json(evidence / "owned-trust-state.json", {
        "schema": 1, "run_id": ENV["GITHUB_RUN_ID"], "head_sha": ENV["GITHUB_SHA"],
        "target": str(target), "before_existed": before is not None, "added_by_this_run": added,
        "before_sha256": None if before is None else actual.digest(before),
        "after_sha256": actual.digest(after), "approval": actual.APPROVAL,
    })
    if added:
        actual.replace_owned(target, before, after)
    return target, after


class ReviewedMacroControls(unittest.TestCase):
    def test_01_exact_original_pin_accepted(self):
        self.assertEqual(actual.verify_pin({"pins": [PIN]}), PIN)

    def test_02_foreign_revision_rejected(self):
        pin = copy.deepcopy(PIN)
        pin["state"]["revision"] = "0" * 40
        with self.assertRaises(ValueError):
            actual.verify_pin({"pins": [pin]})

    def test_03_foreign_version_rejected(self):
        pin = copy.deepcopy(PIN)
        pin["state"]["version"] = "1.4.2"
        with self.assertRaises(ValueError):
            actual.verify_pin({"pins": [pin]})

    def test_04_foreign_url_rejected(self):
        pin = copy.deepcopy(PIN)
        pin["location"] = "https://github.com/unreviewed/equatable"
        with self.assertRaises(ValueError):
            actual.verify_pin({"pins": [pin]})

    def test_05_duplicate_pin_rejected(self):
        with self.assertRaises(ValueError):
            actual.verify_pin({"pins": [PIN, PIN]})

    def test_06_absent_store_adds_only_exact_tuple(self):
        after, added = actual.merge_approval(None)
        self.assertTrue(added)
        self.assertEqual(json.loads(after), [actual.APPROVAL])

    def test_07_other_entries_retained(self):
        other = {"packageIdentity": "existing", "targetName": "ExistingMacros",
                 "fingerprint": "a" * 40, "opaque": ["retain", 1]}
        after, added = actual.merge_approval(json.dumps([other]).encode())
        self.assertTrue(added)
        self.assertEqual(json.loads(after), [other, actual.APPROVAL])

    def test_08_preexisting_exact_approval_preserves_every_byte(self):
        before = b" [\n " + json.dumps(actual.APPROVAL).encode() + b" \n]\n"
        self.assertEqual(actual.merge_approval(before), (before, False))

    def test_09_malformed_store_refused(self):
        for before in [b"{}", b"null", b"[1]", b'[{"packageIdentity":"unknown"}]']:
            with self.assertRaises(ValueError):
                actual.merge_approval(before)

    def test_10_all_actual_reviewed_source_bytes_admitted(self):
        self.assertEqual(len(actual.verify_archive(archive_with(), REVIEW)), 18)

    def test_11_changed_macro_source_refused(self):
        with self.assertRaises(ValueError):
            actual.verify_archive(archive_with(change="Sources/EquatableMacros/EquatablePlugin.swift"), REVIEW)

    def test_12_additional_unreviewed_macro_refused(self):
        with self.assertRaises(ValueError):
            actual.verify_archive(archive_with(extra="reviewed-root/Sources/EquatableMacros/Injected.swift"), REVIEW)

    def test_13_archive_traversal_refused(self):
        with self.assertRaises(ValueError):
            actual.verify_archive(archive_with(extra="reviewed-root/../foreign.swift"), REVIEW)

    def test_14_archive_link_refused(self):
        with self.assertRaises(ValueError):
            actual.verify_archive(archive_with(special=tarfile.SYMTYPE), REVIEW)

    def test_15_restore_recovers_exact_prior_bytes(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            home, evidence = Path(directory) / "home", Path(directory) / "evidence"
            before = b"[\n]\n"
            target, after = owned_state(home, evidence, before)
            self.assertNotEqual(after, before)
            result = actual.restore(evidence, home)
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(result["wrote_trust_store"])

    def test_16_only_created_approval_file_is_removed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            home, evidence = Path(directory) / "home", Path(directory) / "evidence"
            target, _ = owned_state(home, evidence, None)
            actual.restore(evidence, home)
            self.assertFalse(target.exists())
            self.assertTrue(target.parent.is_dir())

    def test_17_preexisting_exact_approval_never_removed(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            home, evidence = Path(directory) / "home", Path(directory) / "evidence"
            before = json.dumps([actual.APPROVAL]).encode() + b"\n"
            target, _ = owned_state(home, evidence, before)
            result = actual.restore(evidence, home)
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse(result["wrote_trust_store"])

    def test_18_concurrent_change_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            home, evidence = Path(directory) / "home", Path(directory) / "evidence"
            target, after = owned_state(home, evidence, None)
            concurrent = after + b"\n"
            target.write_bytes(concurrent)
            with self.assertRaises(ValueError):
                actual.restore(evidence, home)
            self.assertEqual(target.read_bytes(), concurrent)

    def test_19_foreign_run_cannot_restore(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            home, evidence = Path(directory) / "home", Path(directory) / "evidence"
            target, after = owned_state(home, evidence, None)
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "FOREIGN"}), self.assertRaises(ValueError):
                actual.restore(evidence, home)
            self.assertEqual(target.read_bytes(), after)

    def test_20_aliased_target_signal_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ValueError):
                actual.checked_target(Path(directory))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewedMacroControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    successful = result.wasSuccessful() and result.testsRun == 20 and not result.skipped
    print(json.dumps({
        "status": "PASS_20_NEW_MACRO_TRUST_CONTROLS" if successful else "FAIL",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "helper_sha256": actual.digest(Path(actual.__file__).read_bytes()),
        "review_manifest_sha256": actual.digest((ROOT / "Tools/OriginalEditor/reviewed_equatable_macro.json").read_bytes()),
        "scope": "Actual helper functions and original reviewed source with temporary filesystem and explicit archive/path/context probes",
        "previous_221_controls_rerun": False, "apple_macro_validation": "NOT_RUN",
        "framework_builds": 0, "native_tests": 0,
    }, sort_keys=True))
    raise SystemExit(0 if successful else 1)
