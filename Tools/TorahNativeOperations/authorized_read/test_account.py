from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools/TorahNativeOperations"))
from authorized_read import account, profile


class AuthorizedReadAccountControls(unittest.TestCase):
    def _retained(self, root: Path) -> dict:
        shutil.copytree(ROOT / account.PRIOR_PROOF, root / account.PRIOR_PROOF, dirs_exist_ok=True)
        repaired = Path("Tools/TorahNativeOperations/authorized_read/rpc/overlay") / account.REPAIRED_TEST
        (root / repaired).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / repaired, root / repaired)
        old = json.loads((root / account.PRIOR_PROOF / "generation-receipt.json").read_bytes())
        old["source_sha256"][account.REPAIRED_TEST] = profile.digest(root / repaired)
        return old

    def testRetainsOnlyExact67AndSelectsTheFourPendingCases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = self._retained(root)
            retained = account.retain_prior_cases(root, current)
            self.assertEqual((retained["terminal_pass"], retained["top_level_pass"]), (67, 19))
            self.assertEqual(profile.REQUIRED - account.PENDING_PAIRS,
                {(e["Test"], e["Package"]) for e in account.events(root / account.PRIOR_PROOF / "native-rpc-tests.log")
                 if e.get("Test") and e.get("Action") == "pass"})

    def testRetainedPassesRejectAnyProductionOrGeneratedChange(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = self._retained(root)
            for section, key in [("source_sha256", "core/block/editor/torahops/native_operation_read.go"),
                                 ("generated_sha256", "pb/pinkha_authorized_operation_read.pb.go")]:
                current = copy.deepcopy(original)
                current[section][key] = "0" * 64
                with self.assertRaises(ValueError): account.retain_prior_cases(root, current)

    def testFixtureRepairCannotHideAnotherCodeChange(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); current = self._retained(root)
            path = root / "Tools/TorahNativeOperations/authorized_read/rpc/overlay" / account.REPAIRED_TEST
            path.write_bytes(path.read_bytes() + b"\n// unrelated change\n")
            current["source_sha256"][account.REPAIRED_TEST] = profile.digest(path)
            with self.assertRaises(ValueError): account.retain_prior_cases(root, current)

    def testPriorMissingPassOrWrongPackageCannotQualify(self):
        for wrong_package in [False, True]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); current = self._retained(root)
                proof = root / account.PRIOR_PROOF
                log = proof / "native-rpc-tests.log"
                rows = account.events(log)
                index = next(i for i, e in enumerate(rows) if e.get("Test") and e.get("Action") == "pass")
                if wrong_package: rows[index]["Package"] = "foreign/package"
                else: rows.pop(index)
                log.write_text("".join(json.dumps(e) + "\n" for e in rows), encoding="utf-8")
                pins = json.loads((proof / "evidence.json").read_bytes())
                pins["files_sha256"]["native-rpc-tests.log"] = profile.digest(log)
                (proof / "evidence.json").write_text(json.dumps(pins), encoding="utf-8")
                with self.assertRaises(ValueError): account.retain_prior_cases(root, current)

    def testPendingExecutionRequiresExactFourPassesAndCorrectPackage(self):
        rows = [{"Test": name, "Package": package, "Action": "pass"} for name, package in sorted(account.PENDING_PAIRS)]
        rows.append({"Package": profile.PACKAGE_ROOT + "core", "Action": "pass"})
        self.assertEqual(account.validate_pending(rows)["terminal_pass"], 4)
        for invalid in [rows[1:], rows + [rows[0]], rows + [{"Action": "skip"}], rows + [{"Action": "fail"}]]:
            with self.assertRaises(ValueError): account.validate_pending(invalid)
        invalid = copy.deepcopy(rows); invalid[0]["Package"] = "foreign/package"
        with self.assertRaises(ValueError): account.validate_pending(invalid)

    def testAccountPhaseBindsPidNonceSameStateAndNoRecreation(self):
        state = {"AccountID": "account", "SpaceID": "space", "DocumentID": "document", "BlockID": "block", "RootID": "private-root",
                 "OperationID": "1" * 32, "ClaimID": "1" * 64 + "/" + "2" * 64, "ChangeID": "change",
                 "OperationSHA256": "3" * 64, "RawChanges": {"private-root": "4" * 64, "change": "5" * 64}, "Heads": ["change"]}
        identity = {"heart_sha": profile.HEART, "candidate_sha256": "6" * 64, "fixture_sha256": "7" * 64, "runtime_version": "candidate"}
        root = Path("/owned/account-root")
        report = {**identity, "protocol": account.PROTOCOL, "phase": "reopen", "pid": 27, "nonce": "nonce",
                  "account_root": str(root), "state_sha256": "8" * 64, "account_id": "account", "space_id": "space",
                  "document_id": "document", "block_id": "block", "private_root_id": "private-root",
                  "raw_changes_sha256": state["RawChanges"], "heads": ["change"], "canonical_sha256": "3" * 64,
                  "exact_signed_provenance": True, "read_before_replay": True, "verified_local_absence": True,
                  "account_stop_verified": True, "closed": True, "test_passed": True, "orphan_history_preserved": True,
                  "space_cleanup_verified": True, "app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN",
                  "golden_file": "reopen-live.pb", "golden_sha256": "9" * 64,
                  "rpc_calls": {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WorkspaceOpen", "AccountStop",
                     "AppShutdown", "WalletRecover", "AccountSelect", "BlockListDelete", "SpaceDelete"]}}
        account.validate_phase(report, "reopen", identity, "nonce", root, 27, state, "8" * 64)
        for key, value in [("pid", 26), ("nonce", "old"), ("account_id", "foreign"), ("orphan_history_preserved", False)]:
            invalid = copy.deepcopy(report); invalid[key] = value
            with self.assertRaises(ValueError): account.validate_phase(invalid, "reopen", identity, "nonce", root, 27, state, "8" * 64)
        invalid = copy.deepcopy(report); invalid["rpc_calls"]["PinkhaTorahOperationsAppend"] = 1
        with self.assertRaises(ValueError): account.validate_phase(invalid, "reopen", identity, "nonce", root, 27, state, "8" * 64)

    def testEvidenceNeverExportsWalletAndWithholdsLeakedSecret(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); work = base / "work"; work.mkdir()
            (work / "ownership.json").write_text("{}")
            (work / "result.json").write_text("{}")
            (work / "account-key.private").write_text("synthetic-key")
            (work / "sensitive-needles.private").write_text(json.dumps(["synthetic-key", "synthetic-mnemonic"]))
            (work / "create.log").write_text("safe fixture output")
            result = account.export_evidence(work, base / "export")
            self.assertEqual(result["secret_scan"], "PASS")
            self.assertNotIn("account-key.private", result["files_sha256"])
            self.assertNotIn("sensitive-needles.private", result["files_sha256"])
            (work / "create.log").write_text("leak synthetic-key")
            with self.assertRaises(ValueError): account.export_evidence(work, base / "denied")
            self.assertFalse((base / "denied").exists())

    def testFixedFixtureSourceClosureAndMethodDeclaration(self):
        identity, files = account.fixtures(ROOT)
        self.assertEqual(len(identity), 64)
        self.assertEqual(set(files), account.FIXTURE_PATHS)
        source = (ROOT / "Tools/TorahNativeOperations/authorized_read/account/authorized_operation_account_test.go").read_text(encoding="utf-8")
        self.assertEqual(source.count("func " + account.METHOD + "("), 1)
        self.assertIn("raw := PinkhaTorahAuthorizedOperationRead(encoded)", source)


if __name__ == "__main__":
    unittest.main()
