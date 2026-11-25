"""Integrity controls over a copy of the actual fresh original Swift evidence.

These are metadata admission controls, not compiler, native or application tests.
Usage: python3 -B test_fresh_swift_input.py --proof /absolute/actual/proof
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from fresh_swift_input import qualify, copy_evidence
from import_abi_input import exact_file
from reused_abi_history import history_proofs


def reference(path, base):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": path.relative_to(base).as_posix(), "bytes": path.stat().st_size,
            "sha256": digest}


class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="actual-fresh-swift-controls-")
        cls.root = Path(cls.temp.name) / "proof"
        shutil.copytree(PROOF, cls.root)
        cls.refs = json.loads((cls.root / "INPUT_REFS.json").read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def admit(self, refs=None):
        refs = refs or self.refs
        return qualify(self.root, refs["historical_receipts"],
                       refs["fresh_changed_swift"], exact_file)

    def mutate(self, relative, change):
        path = self.root / relative
        original = path.read_bytes()
        try:
            path.write_bytes(change(original))
            with self.assertRaises((RuntimeError, ValueError, KeyError)):
                self.admit()
        finally:
            path.write_bytes(original)

    def test_actual_evidence_qualifies_only_its_scope(self):
        values = self.admit()
        self.assertEqual(values["changed_swift_qualification"]["execution_origin"], "local-mac")
        self.assertIsNone(values["changed_swift_qualification"]["github_run_id"])
        self.assertFalse(values["changed_swift_qualification"]["full_sdk_typechecked"])
        self.assertEqual(values["generation_qualification"]["aggregate_producer_outcome"], "FAIL")

    def test_source_pin_substitution_rejected(self):
        self.mutate("fresh-swift/changed-swift-sdk-pin.json", lambda b: b + b" ")

    def test_source_driver_substitution_rejected(self):
        self.mutate("fresh-swift/typecheck_repaired_swift.py", lambda b: b + b"\n")

    def test_execution_identity_substitution_rejected(self):
        self.mutate("fresh-swift/local-execution.json", lambda b: b.replace(b'"github_run_id": null', b'"github_run_id": 45269355714'))

    def test_controller_substitution_rejected(self):
        self.mutate("fresh-swift/controller-result.json", lambda b: b.replace(b'"returncode": 0', b'"returncode": 1'))

    def test_compiler_result_substitution_rejected(self):
        self.mutate("fresh-swift/raw/RESULT.json", lambda b: b.replace(b'"actual_input_files": 689', b'"actual_input_files": 0'))

    def test_command_log_substitution_rejected(self):
        self.mutate("fresh-swift/raw/10-typecheck-changed-original-swift-with-sdk.stderr", lambda b: b + b"error\n")

    def test_command_receipt_substitution_rejected(self):
        self.mutate("fresh-swift/raw/COMMANDS.json", lambda b: b.replace(b'"timed_out": false', b'"timed_out": true', 1))

    def test_evidence_index_substitution_rejected(self):
        self.mutate("fresh-swift/raw/EVIDENCE_INDEX.json", lambda b: b + b" ")

    def test_additional_unrecorded_raw_member_rejected(self):
        path = self.root / "fresh-swift/raw/unrecorded.log"
        try:
            path.write_text("unrecorded")
            with self.assertRaises(ValueError):
                self.admit()
        finally:
            path.unlink()

    def test_missing_original_generation_rejected(self):
        refs = deepcopy(self.refs)
        del refs["historical_receipts"]["generated_index"]
        with self.assertRaises(ValueError):
            self.admit(refs)

    def test_legacy_route_still_requires_lost_original_swift(self):
        with self.assertRaises(ValueError):
            history_proofs(self.root, self.refs["historical_receipts"], exact_file)

    def test_traversal_reference_rejected(self):
        refs = deepcopy(self.refs)
        refs["fresh_changed_swift"]["path"] = "../" + refs["fresh_changed_swift"]["path"]
        with self.assertRaises(ValueError):
            self.admit(refs)

    def test_complete_copy_is_independently_qualifiable(self):
        target = Path(self.temp.name) / "portable"
        target.mkdir()
        rows = {}
        for name, row in self.refs["historical_receipts"].items():
            path = target / (name + ".json")
            shutil.copyfile(exact_file(self.root, row), path)
            rows[name] = reference(path, target)
        fresh = copy_evidence(self.root, self.refs["fresh_changed_swift"],
                              target / "fresh-swift", exact_file, reference)
        self.assertEqual(qualify(target, rows, fresh, exact_file), self.admit())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof", type=Path, required=True)
    args, rest = parser.parse_known_args()
    PROOF = args.proof.resolve()
    unittest.main(argv=["test_fresh_swift_input.py", *rest])
