"""Real filesystem controls for app-update storage continuity; not Apple acceptance."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import run_t5_apple_pair as pair
from test_t5_apple_pair import TOKEN, SOURCE, LEDGER_SHA, ledger_for, report_for


class ApplePairStorageControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.container = self.directory / "original-uuid"
        self.native = self.container / pair.ROOT_RELATIVE_PATH
        (self.native / "account/object-store").mkdir(parents=True)
        (self.native / "account/object-store/data.bin").write_bytes(b"original native bytes\x00\xff")
        (self.native / "account/wallet.bin").write_bytes(b"original wallet bytes")
        private = self.container / pair.PAIR_RELATIVE_PATH
        private.mkdir(parents=True)
        (private / "ledger.json").write_text('{"original":"ledger"}')
        (private / "secrets.json").write_text(json.dumps(dict(
            token=TOKEN, mnemonic="original synthetic private mnemonic", accountKey="original-private-account-key")))
        self.prior = dict(nextLedgerSHA256=pair.digest(private / "ledger.json"))
        self.work = self.directory / "work"
        self.work.mkdir()

    def relocate(self):
        relocated = self.directory / "updated-uuid"
        self.container.rename(relocated)
        return relocated

    def test_relocation_preserves_every_native_byte_and_the_private_ledger(self):
        before = pair.account_storage_inventory(self.container)
        relocated = self.relocate()
        receipt = {"status": "FAIL"}
        pair.verify_install_continuity(before, relocated, self.prior, receipt)
        self.assertEqual(receipt["status"], "PASS_ALL_NATIVE_FILES_AND_PRIVATE_IDENTITY_UNCHANGED")
        self.assertEqual(receipt["before"], receipt["after"])
        self.assertEqual(receipt["before"]["files"], 2)
        self.assertNotIn("wallet", json.dumps(receipt))
        self.assertNotIn("mnemonic", json.dumps(receipt))

    def test_changed_deleted_and_extra_native_files_fail_with_intact_ledger(self):
        for mode in ["change", "delete", "extra"]:
            with self.subTest(mode=mode):
                destination = self.directory / mode
                shutil.copytree(self.container, destination)
                before = pair.account_storage_inventory(self.container)
                native = destination / pair.ROOT_RELATIVE_PATH
                target = native / "account/wallet.bin"
                if mode == "change":
                    target.write_bytes(b"replacement wallet bytes")
                elif mode == "delete":
                    target.unlink()
                else:
                    (native / "new-file.bin").write_bytes(b"unexpected store")
                receipt = {"status": "FAIL"}
                with self.assertRaisesRegex(RuntimeError, "original native account data"):
                    pair.verify_install_continuity(before, destination, self.prior, receipt)
                self.assertEqual(receipt["status"], "FAIL")
                self.assertNotEqual(receipt["before"]["sha256"], receipt["after"]["sha256"])

    def test_missing_root_cannot_be_replaced_by_the_retained_private_ledger(self):
        before = pair.account_storage_inventory(self.container)
        relocated = self.relocate()
        shutil.rmtree(relocated / pair.ROOT_RELATIVE_PATH)
        self.assertTrue((relocated / pair.PAIR_RELATIVE_PATH / "ledger.json").is_file())
        with self.assertRaisesRegex(RuntimeError, "root missing"):
            pair.verify_install_continuity(before, relocated, self.prior, {})

    def test_changed_private_ledger_or_credentials_fails_even_when_native_files_match(self):
        for name in ["ledger.json", "secrets.json"]:
            with self.subTest(name=name):
                destination = self.directory / name
                shutil.copytree(self.container, destination)
                before = pair.account_storage_inventory(self.container)
                (destination / pair.PAIR_RELATIVE_PATH / name).write_text('{"replacement":true}')
                with self.assertRaisesRegex(RuntimeError, "original native account data"):
                    pair.verify_install_continuity(before, destination, self.prior, {})

    def test_identical_recreated_store_cannot_replace_the_preceding_ledger_chain(self):
        before = pair.account_storage_inventory(self.container)
        with self.assertRaisesRegex(RuntimeError, "preceding account ledger"):
            pair.verify_install_continuity(before, self.container, dict(nextLedgerSHA256="0" * 64), {})

    def test_symlinked_native_file_is_rejected_even_when_target_bytes_are_identical(self):
        target = self.native / "account/wallet.bin"
        original = self.directory / "outside-wallet.bin"
        target.rename(original)
        try:
            target.symlink_to(original)
        except (OSError, NotImplementedError):
            self.skipTest("Host does not support creating a test symlink")
        with self.assertRaisesRegex(RuntimeError, "file entry"):
            pair.account_storage_inventory(self.container)

    def test_current_root_location_is_checked_against_the_live_container(self):
        old_hash = pair.sha_bytes(str(self.native.resolve()).encode())
        relocated = self.relocate()
        current_hash = pair.sha_bytes(str((relocated / pair.ROOT_RELATIVE_PATH).resolve()).encode())
        pair.verify_current_root(dict(currentRootPathSHA256=current_hash), relocated)
        with self.assertRaisesRegex(RuntimeError, "actual current account root"):
            pair.verify_current_root(dict(currentRootPathSHA256=old_hash), relocated)

    def test_phase_keeps_original_root_identity_while_recording_current_location(self):
        prior = report_for("old-create", "old")
        report = report_for("new-upgrade", "new")
        report["currentRootPathSHA256"] = "e" * 64
        pair.validate_phase(report, "new-upgrade", "new", TOKEN, "2" * 32, SOURCE,
                            ledger_for("new-upgrade"), LEDGER_SHA, prior)
        for key, value in [("rootRelativePath", "another/store"), ("currentRootPathSHA256", None),
                           ("rootPathSHA256", "e" * 64), ("protocolVersion", "pinkha-t5-apple-runtime-pair-v1")]:
            invalid = copy.deepcopy(report)
            invalid[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                pair.validate_phase(invalid, "new-upgrade", "new", TOKEN, "2" * 32, SOURCE,
                                    ledger_for("new-upgrade"), LEDGER_SHA, prior)

    def test_original_credential_scan_survives_a_missing_or_relocated_container(self):
        inventory = pair.preserve_private_credential_inventory(self.container, self.work, TOKEN)
        phase = self.work / "phases/old-create"
        phase.mkdir(parents=True)
        (phase / "test.log").write_text("original clean native output")
        self.relocate()
        proof = self.directory / "proof"
        self.assertTrue(pair.preserve_native_evidence(self.work, proof, self.container, TOKEN,
                                                      credential_inventory=inventory))
        self.assertEqual((proof / "actual-phases/old-create/test.log").read_text(), "original clean native output")
        self.assertFalse(list(proof.rglob("credential-inventory.json")))
        self.assertFalse(list(proof.rglob("secrets.json")))

    def test_original_credentials_in_failed_logs_still_withhold_all_evidence(self):
        inventory = pair.preserve_private_credential_inventory(self.container, self.work, TOKEN)
        phase = self.work / "phases/new-upgrade"
        phase.mkdir(parents=True)
        (phase / "test.log").write_text("leak original-private-account-key")
        self.relocate()
        proof = self.directory / "proof"
        with self.assertRaisesRegex(RuntimeError, "credential found"):
            pair.preserve_native_evidence(self.work, proof, None, TOKEN, credential_inventory=inventory)
        self.assertFalse((proof / "actual-phases").exists())

    def test_later_credentials_cannot_replace_original_inventory(self):
        original = pair.preserve_private_credential_inventory(self.container, self.work, TOKEN).read_bytes()
        source = self.container / pair.PAIR_RELATIVE_PATH / "secrets.json"
        value = json.loads(source.read_text())
        value["accountKey"] = "different-private-key"
        source.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "inventory changed"):
            pair.preserve_private_credential_inventory(self.container, self.work, TOKEN)
        self.assertEqual((self.work / "credential-inventory.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
