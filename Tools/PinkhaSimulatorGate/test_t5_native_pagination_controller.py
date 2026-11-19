"""Filesystem publication controls; no simulated receipt is native acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

import run_t5_native_pagination as controller


class NativePaginationPublicationControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.work, self.proof, self.container = [self.base / name for name in ["work", "proof", "container"]]
        for path in [self.work / "phase", self.proof, self.container / controller.PRIVATE_RELATIVE_PATH]:
            path.mkdir(parents=True)
        self.secret = dict(token="token", mnemonic="disposable original mnemonic phrase", accountKey="private-native-account-key")
        (self.container / controller.PRIVATE_RELATIVE_PATH / "secrets.json").write_text(json.dumps(self.secret))
        (self.work / "phase/test.log").write_text("One actual selected method completed")
        (self.work / "phase/receipt.json").write_text('{"publicSyntheticData": true}')
        (self.work / "phase/original.xcresult").mkdir()
        (self.work / "phase/original.xcresult/private.log").write_text(self.secret["mnemonic"])
        (self.work / "phase/unapproved.log").write_text("not allowlisted")

    def publish(self):
        return controller.publish_native_evidence(self.work, self.proof, self.container, "token")

    def test_only_allowlisted_secret_scanned_files_are_published(self):
        self.assertTrue(self.publish())
        destination = self.proof / "actual-native"
        self.assertEqual({path.name for path in destination.iterdir()}, {"test.log", "receipt.json"})
        self.assertTrue((self.work / "credential-inventory.json").is_file())
        policy = json.loads((self.proof / "native-evidence-policy.json").read_text())
        self.assertEqual(policy["scanned_complete_credential_encodings"], 3)
        self.assertFalse(policy["account_data_uploaded"])
        self.assertFalse(policy["raw_xcresult_uploaded"])
        self.assertFalse(policy["secrets_uploaded"])
        self.assertEqual(len(policy["files"]), 2)

    def test_missing_original_credentials_withhold_all_native_files(self):
        (self.container / controller.PRIVATE_RELATIVE_PATH / "secrets.json").unlink()
        self.assertFalse(self.publish())
        self.assertFalse((self.proof / "actual-native").exists())
        self.assertEqual(json.loads((self.proof / "native-evidence-policy.json").read_text())["status"], "WITHHELD_NO_SECRET_INVENTORY")

    def test_foreign_or_incomplete_credentials_cannot_authorize_publication(self):
        for change in [dict(token="foreign"), dict(mnemonic=""), dict(accountKey="")]:
            with self.subTest(change=change):
                value = dict(self.secret, **change)
                (self.container / controller.PRIVATE_RELATIVE_PATH / "secrets.json").write_text(json.dumps(value))
                with self.assertRaises(RuntimeError):
                    self.publish()
                self.assertFalse((self.proof / "actual-native").exists())

    def test_both_credentials_in_every_complete_encoding_block_the_entire_publication(self):
        for key in ["mnemonic", "accountKey"]:
            for encoding in ["utf8", "utf-16-le", "utf-16-be"]:
                with self.subTest(key=key, encoding=encoding):
                    inventory = self.work / "credential-inventory.json"
                    if inventory.exists():
                        inventory.unlink()
                    (self.work / "phase/receipt.json").write_bytes(b"prefix" + self.secret[key].encode(encoding) + b"suffix")
                    with self.assertRaises(RuntimeError):
                        self.publish()
                    self.assertFalse((self.proof / "actual-native").exists())

    def test_existing_private_inventory_or_public_destination_is_never_overwritten(self):
        (self.work / "credential-inventory.json").write_text("retained original")
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertEqual((self.work / "credential-inventory.json").read_text(), "retained original")
        (self.work / "credential-inventory.json").unlink()
        (self.proof / "actual-native").mkdir()
        (self.proof / "actual-native/retained.json").write_text("retained")
        with self.assertRaises(RuntimeError):
            self.publish()
        self.assertEqual((self.proof / "actual-native/retained.json").read_text(), "retained")

    def test_oversized_native_file_and_missing_receipt_fail_closed(self):
        path = self.container / controller.PRIVATE_RELATIVE_PATH / "receipt.json"
        with self.assertRaises(RuntimeError):
            controller.private_file(self.container, "receipt.json")
        path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        with self.assertRaises(RuntimeError):
            controller.private_file(self.container, "receipt.json")


if __name__ == "__main__":
    unittest.main()
