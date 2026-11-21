"""Rejection controls only. No test here represents Apple/native acceptance."""
import copy
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest

import run_t5_apple_pair as controller

TOKEN = "a" * 32
SOURCE = "b" * 40
LEDGER_SHA = "c" * 64
UDID = "11111111-2222-3333-4444-555555555555"


def ledger_for(phase):
    documents = []
    for index, name in enumerate(["document", "block", "quote"]):
        item = dict(objectID=name, typeKey=["ot-page", "ot-note", "ot-custom"][index],
                    initialName="" if index == 1 else "actual initial title",
                    canonicalSHA256=str(index + 1) * 64, publicSHA256=str(index + 4) * 64)
        if index:
            item.update(blockID=name + "-leaf", blockText=name + " preserved text")
        documents.append(item)
    index = [name for name, _ in controller.PHASES].index(phase)
    return dict(token=TOKEN, appSourceSHA=SOURCE, rootPathSHA256="d" * 64,
                rootRelativePath=controller.ROOT_RELATIVE_PATH,
                accountID="account", spaceID="space", manifestID="manifest", manifestSHA256="e" * 64,
                canonicalKey="canonical-key", documents=documents,
                completedPhases=[name for name, _ in controller.PHASES[:index + 1]])


def report_for(phase, role):
    ledger = ledger_for(phase)
    index = [name for name, _ in controller.PHASES].index(phase)
    expanded = role == "new"
    readbacks = []
    for offset, item in enumerate(ledger["documents"]):
        observed = {key: item[key] for key in ["objectID", "canonicalSHA256", "publicSHA256"]}
        if item.get("blockID"):
            observed.update(blockID=item["blockID"], blockTextSHA256=controller.sha_bytes(item["blockText"].encode()))
        observed["title"] = ("T5 ordinary edit by r14" if offset == 0 and phase in ["old-edit", "new-recover"]
                             else item["initialName"])
        observed["nativeRelatedVersion"] = 1 if expanded else 0
        readbacks.append(observed)
    report = dict(protocolVersion=controller.PROTOCOL, status="PASS", phase=phase, token=TOKEN,
                  nonce=str(index + 1) * 32, processID=100 + index, appSourceSHA=SOURCE,
                  rootRelativePath=controller.ROOT_RELATIVE_PATH, currentRootPathSHA256="d" * 64,
                  runtimeVersion=controller.runtime_version(role), actualCapability="verified" if expanded else "unavailable",
                  coverage="indexedTargetsOnly" if expanded else "indexedDocumentsOnly",
                  limitations=["indexFreshnessUnverified"] if expanded else [
                      "blockAssociationsNotIndexed", "sourceQuotesNotIndexed", "indexFreshnessUnverified"],
                  previousLedgerSHA256=LEDGER_SHA if index else None, nextLedgerSHA256=LEDGER_SHA,
                  migrationPerformed=False, walletCreated=index == 0, accountCreated=index == 0,
                  walletRecovered=index != 0, accountSelected=index != 0,
                  accountStopCompleted=True, accountNotRunningConfirmed=True, appShutdownCompleted=True,
                  documents=readbacks,
                  targets=[dict(objectID=item["objectID"], blockID=item.get("blockID") if expanded else None,
                                canUnlink=item.get("blockID") is None)
                           for item in ledger["documents"][:3 if expanded else 1]])
    report.update({key: ledger[key] for key in
                  ["rootPathSHA256", "accountID", "spaceID", "manifestID", "manifestSHA256", "canonicalKey"]})
    return report


def builds():
    result = {}
    for role in ["old", "new"]:
        result[role] = dict(app_source_sha=SOURCE, package_lock_hashes={"Package.resolved": "f" * 64},
                            hanlin_snapshot_sha256="1" * 64, kit_sha="2" * 40, flags=list(controller.FLAGS),
                            code_sha256=("3" if role == "old" else "4") * 64,
                            runtime_version=controller.runtime_version(role))
    return result


def xcode_summary():
    return dict(passedTests=1, failedTests=0, skippedTests=0, devicesAndConfigurations=[
        {"device": {"deviceId": UDID, "osVersion": "27.0", "architecture": "arm64"}}])


class ApplePairControls(unittest.TestCase):
    def validate(self, report, phase="new-upgrade", role="new", ledger=None):
        index = [name for name, _ in controller.PHASES].index(phase)
        prior = report_for(*controller.PHASES[index - 1]) if index else None
        controller.validate_phase(report, phase, role, TOKEN, str(index + 1) * 32, SOURCE,
                                  ledger or ledger_for(phase), LEDGER_SHA, prior)

    def test_each_declared_phase_has_an_explicit_runtime_and_closed_account(self):
        for phase, role in controller.PHASES:
            with self.subTest(phase=phase):
                self.validate(report_for(phase, role), phase, role)

    def test_old_runtime_private_cache_does_not_enable_expanded_lookup(self):
        report = report_for("old-edit", "old")
        for row in report["documents"]:
            row["nativeRelatedVersion"] = 1
        self.validate(report, "old-edit", "old")
        for key, value in [("actualCapability", "verified"), ("coverage", "indexedTargetsOnly"),
                           ("runtimeVersion", controller.runtime_version("new"))]:
            with self.subTest(key=key):
                changed = copy.deepcopy(report)
                changed[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(changed, "old-edit", "old")

    def test_other_source_account_space_and_stale_nonce_are_rejected(self):
        for key, value in [("appSourceSHA", "0" * 40), ("accountID", "recreated"),
                           ("spaceID", "another"), ("rootPathSHA256", "0" * 64),
                           ("manifestID", "recreated"), ("nonce", "old-nonce")]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                report[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_later_ledger_cannot_redefine_canonical_public_or_block_baselines(self):
        for key in ["canonicalSHA256", "publicSHA256", "blockID", "blockText"]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                ledger = ledger_for("new-upgrade")
                if key == "blockText":
                    ledger["documents"][1][key] = "changed text"
                    report["documents"][1]["blockTextSHA256"] = controller.sha_bytes(b"changed text")
                else:
                    value = "9" * 64 if key.endswith("SHA256") else "replacement-leaf"
                    ledger["documents"][1][key] = value
                    report["documents"][1][key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report, ledger=ledger)

    def test_missing_target_or_freshness_disclosure_cannot_pass(self):
        for change in ["target", "freshness", "space-wide", "truncated"]:
            with self.subTest(change=change):
                report = report_for("new-upgrade", "new")
                if change == "target":
                    report["targets"].pop()
                elif change == "freshness":
                    report["limitations"] = []
                elif change == "space-wide":
                    report["coverage"] = "spaceWide"
                else:
                    report["limitations"].append("resultLimitReached")
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_stop_must_include_success_and_original_rpc_not_running_observation(self):
        for key in ["accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                report[key] = False
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_no_later_recreation_or_unobserved_migration(self):
        for key in ["walletCreated", "accountCreated", "walletRecovered", "accountSelected"]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                report[key] = not report[key]
                with self.assertRaises(RuntimeError):
                    self.validate(report)
        report = report_for("old-create", "old")
        report["migrationPerformed"] = True
        with self.assertRaises(RuntimeError):
            self.validate(report, "old-create", "old")

    def test_empty_native_note_name_and_old_client_page_edit_both_survive(self):
        report = report_for("new-recover", "new")
        self.validate(report, "new-recover", "new")
        for index, title in [(0, "actual initial title"), (1, "invented requested Note title")]:
            with self.subTest(index=index):
                changed = copy.deepcopy(report)
                changed["documents"][index]["title"] = title
                with self.assertRaises(RuntimeError):
                    self.validate(changed, "new-recover", "new")

    def test_actual_named_xctest_and_selected_os27_device_are_required(self):
        controller.validate_xcresult(xcode_summary(), {controller.METHOD + "()": "Passed"}, UDID)
        for change in ["zero", "skip", "bool-count", "different-method", "different-device", "different-os"]:
            with self.subTest(change=change):
                summary, methods = xcode_summary(), {controller.METHOD: "Passed"}
                if change == "zero":
                    summary["passedTests"] = 0
                elif change == "skip":
                    summary["skippedTests"] = 1
                elif change == "bool-count":
                    summary["passedTests"] = True
                elif change == "different-method":
                    methods = {"OtherSuite/OtherTest": "Passed"}
                elif change == "different-device":
                    summary["devicesAndConfigurations"][0]["device"]["deviceId"] = "another"
                else:
                    summary["devicesAndConfigurations"][0]["device"]["osVersion"] = "26.0"
                with self.assertRaises(RuntimeError):
                    controller.validate_xcresult(summary, methods, UDID)

    def test_same_app_source_and_flags_with_four_distinct_processes_are_required(self):
        reports = [report_for(phase, role) for phase, role in controller.PHASES]
        self.assertEqual(controller.validate_sequence(reports, builds())["named_swift_tests_passed"], 4)
        for change in ["pid", "nonce", "flags", "source", "dependency", "same-binary", "missing-phase"]:
            with self.subTest(change=change):
                current, products = copy.deepcopy(reports), builds()
                if change in ["pid", "nonce"]:
                    key = "processID" if change == "pid" else "nonce"
                    current[1][key] = current[0][key]
                elif change == "flags":
                    products["new"]["flags"] = ["-D A_DIFFERENT_BUILD"]
                elif change == "source":
                    products["new"]["app_source_sha"] = "0" * 40
                elif change == "dependency":
                    products["new"]["kit_sha"] = "0" * 40
                elif change == "same-binary":
                    products["new"]["code_sha256"] = products["old"]["code_sha256"]
                else:
                    current.pop()
                with self.assertRaises(RuntimeError):
                    controller.validate_sequence(current, products)

    def private_fixture(self, root):
        work, proof, container = root / "work", root / "proof", root / "container"
        directory = work / "phases/old-create"
        directory.mkdir(parents=True)
        secret_dir = container / "Library/Application Support/pinkha-t5-runtime-pair"
        secret_dir.mkdir(parents=True)
        (secret_dir / "secrets.json").write_text(json.dumps(dict(
            token=TOKEN, mnemonic="private synthetic mnemonic", accountKey="private-synthetic-account-key")))
        (secret_dir / "ledger.json").write_text("private account ledger")
        (directory / "test.log").write_text("original XCTest output")
        (directory / "receipt.json").write_text('{"status":"FAIL"}')
        (directory / "unexpected.txt").write_text("private-synthetic-account-key")
        return work, proof, container, directory

    def test_only_explicit_secret_scanned_native_evidence_is_published(self):
        with tempfile.TemporaryDirectory() as temp:
            work, proof, container, directory = self.private_fixture(Path(temp))
            self.assertTrue(controller.preserve_native_evidence(work, proof, container, TOKEN))
            self.assertEqual((proof / "actual-phases/old-create/test.log").read_text(), "original XCTest output")
            self.assertFalse(list(proof.rglob("secrets.json")))
            self.assertFalse(list(proof.rglob("ledger.json")))
            self.assertFalse(list(proof.rglob("unexpected.txt")))
            self.assertFalse(list(proof.rglob("*.xcresult")))

    def test_any_complete_credential_withholds_all_native_evidence(self):
        for encoding in ["utf8", "utf-16-le", "utf-16-be"]:
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as temp:
                work, proof, container, directory = self.private_fixture(Path(temp))
                (directory / "test.log").write_bytes(b"x" * (128 * 1024 - 7)
                                                     + "private-synthetic-account-key".encode(encoding))
                with self.assertRaises(RuntimeError):
                    controller.preserve_native_evidence(work, proof, container, TOKEN)
                self.assertFalse((proof / "actual-phases").exists())

    def test_no_secret_inventory_withholds_native_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(controller.preserve_native_evidence(root / "work", root / "proof", None, TOKEN))
            self.assertEqual(json.loads((root / "proof/native-evidence-policy.json").read_text())["status"],
                             "WITHHELD_NO_SECRET_INVENTORY")
            self.assertFalse((root / "proof/actual-phases").exists())

    def test_only_product_paths_are_rebound_when_preserving_build_outputs(self):
        source, target = PurePosixPath("/derived/Build/Products"), PurePosixPath("/owned/old/Products")
        value = dict(TestHostPath="/derived/Build/Products/Release/Anytype.app/Anytype",
                     EnvironmentVariables={"UNCHANGED": "yes"}, TestBundlePath="__TESTROOT__/Tests.xctest")
        changed = controller.rewrite_product_paths(value, source, target)
        self.assertEqual(changed["TestHostPath"], "/owned/old/Products/Release/Anytype.app/Anytype")
        self.assertEqual(changed["TestBundlePath"], value["TestBundlePath"])
        self.assertEqual(changed["EnvironmentVariables"], value["EnvironmentVariables"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
