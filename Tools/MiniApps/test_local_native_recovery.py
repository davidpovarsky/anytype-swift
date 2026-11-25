"""Refusal controls for original-byte native evidence recovery; no native credit."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("recovery", HERE / "local_native_recovery.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)
POLICY = json.loads((HERE / "local_native_policy.json").read_bytes())
REVIEW = json.loads((HERE / "native70f_recovery.json").read_bytes())


class NativeRecoveryIntegrity(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.app = self.base / "source"
        self.app.mkdir()
        self.value = deepcopy(REVIEW)
        self.value["recovery_root"] = str(self.base / "materialization/native70f-recovery")

    def test_exact_review_keeps_missing_transport_and_original_source(self):
        self.assertEqual(recovery.validate_review(self.value, POLICY, self.app),
                         Path(self.value["recovery_root"]))

    def test_transport_cannot_be_reported_verified(self):
        self.value["original_simulator_zip_status"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "relabel"):
            recovery.validate_review(self.value, POLICY, self.app)

    def test_recovery_cannot_grant_native_tests_or_new_build(self):
        for field, value in (("new_native_tests_executed", 66), ("new_build_claimed", True)):
            altered = deepcopy(self.value)
            altered[field] = value
            with self.assertRaisesRegex(ValueError, "relabel"):
                recovery.validate_review(altered, POLICY, self.app)

    def test_foreign_original_source_is_rejected(self):
        self.value["original_evidence_source"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "relabel"):
            recovery.validate_review(self.value, POLICY, self.app)

    def test_unowned_destination_is_rejected(self):
        self.value["recovery_root"] = str(self.base / "other-owner")
        with self.assertRaisesRegex(ValueError, "Unowned"):
            recovery.validate_review(self.value, POLICY, self.app)

    def test_original_root_cannot_be_relabelled(self):
        self.value["original_roots"]["device"] += "-new"
        with self.assertRaisesRegex(ValueError, "identity"):
            recovery.validate_review(self.value, POLICY, self.app)

    def test_payload_changes_and_aliases_are_rejected(self):
        path = self.base / "payload"
        path.write_bytes(b"actual immutable input")
        row = {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        self.assertEqual(recovery.regular(self.base, "payload", row), path)
        path.write_bytes(b"changed immutable input")
        with self.assertRaisesRegex(ValueError, "differs"):
            recovery.regular(self.base, "payload", row)
        link = self.base / "alias"
        link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, "differs"):
            recovery.regular(self.base, "alias", row)
        with self.assertRaisesRegex(ValueError, "Noncanonical"):
            recovery.regular(self.base, "../payload", row)

    def test_receipt_cannot_escape_exact_original_roots(self):
        record = {"original_roots": self.value["original_roots"],
                  "recovered_roots": {role: str(self.base / role) for role in ("device", "simulator")}}
        with self.assertRaisesRegex(ValueError, "outside"):
            recovery.recovered_receipt("/unrelated-owner/evidence/receipt.json", record)


if __name__ == "__main__":
    unittest.main(verbosity=2)
