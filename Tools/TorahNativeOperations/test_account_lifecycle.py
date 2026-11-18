"""Controller rejection/ownership controls; these do not count as native acceptance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import run_account_lifecycle as runner

REGISTRATION = "c" * 64
FIXTURE = "d" * 64


def state():
    return {"AccountID": "disposable-account", "SpaceID": "disposable-space", "DocumentID": "document",
            "BlockID": "block", "RootID": "private-root", "OperationID": "0" * 31 + "1",
            "OperationSHA256": "e" * 64, "ClaimID": "a" * 64 + "/" + "b" * 64, "ChangeID": "signed-change",
            "RawChanges": {"private-root": "a" * 64, "signed-change": "b" * 64}, "Heads": ["signed-change"]}


def identity(role):
    return {"role": role, "heart_sha": runner.HEART, "legacy_patch_sha256": runner.LEGACY_PATCH,
            "registration_patch_sha256": REGISTRATION if role == "new" else "none", "fixture_sha256": FIXTURE,
            "runtime_version": runner.runtime_version(role, REGISTRATION)}


def phase_report(phase, role):
    original = state()
    calls = {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1, "AccountStop": 1,
             "AppShutdown": 1, "ObjectExport": 4, "ObjectShow": 2, "ObjectSearch": 4}
    if phase == "new-create":
        calls.update({name: 1 for name in ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"]})
    else:
        calls.update(WalletRecover=1, AccountSelect=1)
    if phase == "legacy-edit":
        calls["ObjectSetDetails"] = 1
    if phase == "new-recover":
        calls.update(BlockListDelete=1, SpaceDelete=1)
    observation = {"private_registry": "UNKNOWN_CHANGE_TYPE_REJECTED", "private_read": "NOT_AVAILABLE_ON_LEGACY",
                   "handler_boundary": {"scope": "UNSUPPORTED_LEGACY"}}
    if role == "new":
        observation = {"private_registry": "ACTUAL_NATIVE_FACTORY", "private_read": "EXACT_PERSISTED_CLAIM",
                       "idempotent_retry": "already_exists_same_payload", "operation_sha256": original["OperationSHA256"],
                       "claim_id": original["ClaimID"], "signed_change_id": original["ChangeID"], "private_type": 0x504B0001,
                       "handler_boundary": {"scope": "ACCOUNT_SCOPED_TYPED_BOUNDARY_NOT_REGISTERED_RPC",
                                              "creation": ("INVALID_CALLS_NO_ROOT_THEN_VALID_APPEND_CREATED_ROOT"
                                                           if phase == "new-create" else "EXISTING_HISTORY_REOPENED"),
                                              "read": "EXACT_PERSISTED_CLAIM_NATIVE_AUTHOR",
                                              "read_guards": "VERSION_AND_LIMIT_REJECTED",
                                              "retry": "already_exists_same_payload", "collision": "collision_different_payload",
                                              "after_stop": "NATIVE_READ_AND_APPEND_NOT_LOGGED_IN"}}
    return {**identity(role), "protocol": runner.PROTOCOL, "phase": phase, "pid": 42, "nonce": "fresh-nonce",
            "account_root": str(Path("/disposable/account-root")), "state_sha256": "f" * 64,
            "account_id": original["AccountID"], "space_id": original["SpaceID"], "document_id": original["DocumentID"],
            "block_id": original["BlockID"], "private_root_id": original["RootID"], "raw_changes_sha256": original["RawChanges"],
            "heads": original["Heads"], "account_stop_verified": True, "closed": True, "test_passed": True,
            "app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN",
            "runtime_observation": observation, "rpc_calls": calls,
            "cleanup": "TARGET_ORPHAN_PRESERVED_THEN_SPACE_AND_PROJECTION_REMOVED" if phase == "new-recover" else "NOT_REQUESTED_IN_THIS_PHASE",
            "visibility": {"ordinary_name": runner.VISIBLE + (" edited by legacy" if phase in {"legacy-edit", "new-recover"} else ""),
                           "block_sha256": hashlib.sha256((original["BlockID"] + "\0" + runner.VISIBLE).encode()).hexdigest(),
                           "ordinary_fulltext_control": "PASS", "private_search": "ABSENT", "private_show": "REJECTED",
                           "private_export": "REJECTED_JSON_AND_PROTOBUF", "exports": {"document.json": "a" * 64, "document.pbc": "b" * 64}}}


def validate(report, phase="new-reopen", role="new"):
    runner.validate_phase(report, phase, role, identity(role), "fresh-nonce", Path("/disposable/account-root"), 42, state(), "f" * 64)


class AccountControllerControls(unittest.TestCase):
    def test_each_explicit_phase_and_narrow_native_scope(self):
        for phase, role in runner.PHASES:
            with self.subTest(phase=phase):
                validate(phase_report(phase, role), phase, role)

    def test_source_role_nonce_process_and_original_identity_cannot_drift(self):
        for key, wrong in {"heart_sha": "0" * 40, "legacy_patch_sha256": "0" * 64,
                           "registration_patch_sha256": "none", "fixture_sha256": "0" * 64,
                           "runtime_version": "old", "role": "legacy", "nonce": "stale", "pid": 43,
                           "account_id": "other-account", "document_id": "other-document",
                           "private_root_id": "another-private-root", "state_sha256": "0" * 64}.items():
            with self.subTest(field=key):
                report = phase_report("new-reopen", "new")
                report[key] = wrong
                with self.assertRaises(ValueError):
                    validate(report)

    def test_private_bytes_or_heads_cannot_be_rewritten_or_dropped(self):
        for key, value in [("raw_changes_sha256", {"private-root": "a" * 64}),
                           ("raw_changes_sha256", {"private-root": "a" * 64, "signed-change": "0" * 64}),
                           ("heads", ["new-change"])]:
            report = phase_report("new-reopen", "new")
            report[key] = value
            with self.assertRaises(ValueError):
                validate(report)

    def test_later_account_creation_and_unexpected_rpc_are_rejected(self):
        for name in ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate", "ObjectListDelete"]:
            report = phase_report("new-reopen", "new")
            report["rpc_calls"][name] = 1
            with self.subTest(rpc=name), self.assertRaises(ValueError):
                validate(report)

    def test_only_explicit_migration_fallback_is_accepted(self):
        report = phase_report("new-reopen", "new")
        report["rpc_calls"].update(AccountSelect=2, AccountMigrate=1)
        validate(report)
        report["rpc_calls"]["AccountSelect"] = 1
        with self.assertRaises(ValueError):
            validate(report)

    def test_close_and_acceptance_claims_are_not_inferred_from_exit_zero(self):
        for key, value in [("account_stop_verified", False), ("closed", False), ("test_passed", False),
                           ("app_capability", "ON"), ("two_app_clients", "PASS"), ("ios_acceptance", "PASS")]:
            report = phase_report("new-reopen", "new")
            report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(report)

    def test_legacy_cannot_claim_new_host_read(self):
        report = phase_report("legacy-edit", "legacy")
        report["runtime_observation"] = phase_report("new-reopen", "new")["runtime_observation"]
        with self.assertRaises(ValueError):
            validate(report, "legacy-edit", "legacy")

    def test_handler_receipt_cannot_be_missing_or_upgraded_to_registered_rpc(self):
        for phase in ["new-create", "new-reopen", "new-recover"]:
            complete = phase_report(phase, "new")["runtime_observation"]["handler_boundary"]
            for key in complete:
                with self.subTest(phase=phase, missing=key):
                    report = phase_report(phase, "new")
                    del report["runtime_observation"]["handler_boundary"][key]
                    with self.assertRaises(ValueError):
                        validate(report, phase, "new")
            for key, value in [("scope", "REGISTERED_RPC"), ("after_stop", "NOT_RUN"),
                               ("collision", "created"), ("read", "EMPTY_SNAPSHOT")]:
                with self.subTest(phase=phase, invalid=key):
                    report = phase_report(phase, "new")
                    report["runtime_observation"]["handler_boundary"][key] = value
                    with self.assertRaises(ValueError):
                        validate(report, phase, "new")
        report = phase_report("legacy-edit", "legacy")
        report["runtime_observation"]["handler_boundary"] = {"scope": "ACCOUNT_SCOPED_TYPED_BOUNDARY_NOT_REGISTERED_RPC"}
        with self.assertRaises(ValueError):
            validate(report, "legacy-edit", "legacy")

    def test_missing_export_positive_search_and_cleanup_fail_closed(self):
        for key, value in [("exports", {"document.json": "a" * 64}), ("ordinary_fulltext_control", "NOT_RUN"),
                           ("private_export", "NOT_RUN"), ("private_search", "UNKNOWN"), ("ordinary_name", runner.VISIBLE)]:
            report = phase_report("new-recover", "new")
            report["visibility"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(report, "new-recover", "new")
        report = phase_report("new-recover", "new")
        report["cleanup"] = "NOT_RUN"
        with self.assertRaises(ValueError):
            validate(report, "new-recover", "new")

    def test_complete_composition_includes_new_overlay_path_collisions(self):
        legacy = {"heart_sha": runner.HEART, "files": [{"path": "core/shared.go", "before_sha256": None, "after_sha256": "a" * 64}]}
        private = {"heart_sha": runner.HEART, "tracked": {}, "overlay": {"core/shared.go": "b" * 64}}
        with self.assertRaises(ValueError):
            runner.composition(legacy, private)
        private["overlay"] = {"core/private.go": "b" * 64}
        old, new = runner.composition(legacy, private)
        self.assertEqual(set(old), {"core/shared.go"})
        self.assertEqual(set(new), {"core/shared.go", "core/private.go"})
        private["overlay"] = {"../escape.go": "b" * 64}
        with self.assertRaises(ValueError):
            runner.composition(legacy, private)

    def test_linked_role_uses_full_patch_marker_not_shared_literal_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "fixture-elf-header-only"
            old = identity("legacy")
            data = b"\x7fELF\x02\x01" + b"\0".join(value.encode() for value in
                    [runner.HEART, old["runtime_version"], FIXTURE, runner.PROTOCOL, runner.METHOD, "-pinkha-t2-registry-v1-"])
            file.write_bytes(data)
            old.update(binary=str(file), binary_sha256=runner.digest(file))
            runner.verify_binary("legacy", old, REGISTRATION)
            file.write_bytes(data + ("-pinkha-t2-registry-v1-" + REGISTRATION).encode())
            old["binary_sha256"] = runner.digest(file)
            with self.assertRaises(ValueError):
                runner.verify_binary("legacy", old, REGISTRATION)

    def test_native_log_requires_one_exact_named_pass_and_no_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "phase.log"
            good = "=== RUN   " + runner.METHOD + "\n--- PASS: " + runner.METHOD + " (1.00s)\nPASS\n"
            file.write_text(good)
            runner.validate_test_log(file)
            for content in ["PASS", good + "--- SKIP: helper (0.00s)\n", good + "--- FAIL: other (0.00s)\n", good + good]:
                file.write_text(content)
                with self.assertRaises(ValueError):
                    runner.validate_test_log(file)

    def test_evidence_allowlist_excludes_account_and_private_key(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            work.mkdir()
            (work / "ownership.json").write_text('{}')
            (work / "result.json").write_text('{"status":"FAIL"}')
            (work / "sensitive-needles.private").write_text(json.dumps(["synthetic-key-123", "synthetic mnemonic"]), encoding="utf-8")
            (work / "account-key.private").write_text("synthetic-key-123")
            (work / "new-create.log").write_text("ordinary diagnostic")
            (work / "state.json").write_text(json.dumps(state()))
            (work / "account-root").mkdir()
            (work / "account-root/credential").write_text("synthetic-key-123")
            target = Path(directory) / "safe"
            result = runner.preserve_account_evidence(work, target)
            self.assertEqual(result["secret_scan"], "PASS")
            self.assertFalse((target / "account-key.private").exists())
            self.assertFalse((target / "account-root").exists())
            self.assertTrue((target / "new-create.log").is_file())

    def test_secret_in_one_candidate_withholds_all_account_files(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            work.mkdir()
            (work / "ownership.json").write_text('{}')
            (work / "result.json").write_text('{}')
            (work / "sensitive-needles.private").write_text(json.dumps(["synthetic-key-123", "synthetic mnemonic"]))
            (work / "new-create.log").write_text("unexpected synthetic-key-123 in log")
            target = Path(directory) / "withheld"
            with self.assertRaises(ValueError):
                runner.preserve_account_evidence(work, target)
            self.assertFalse(target.exists())

    def test_no_secret_inventory_withholds_native_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / "work"
            work.mkdir()
            (work / "ownership.json").write_text('{}')
            (work / "result.json").write_text('{}')
            (work / "new-create.log").write_text("unverified native output")
            target = Path(directory) / "safe"
            result = runner.preserve_account_evidence(work, target)
            self.assertEqual(result["secret_scan"], "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY")
            self.assertFalse((target / "new-create.log").exists())

    @unittest.skipUnless(os.name == "posix", "Actual process-group control requires POSIX")
    def test_actual_child_pid_exit_and_log_flush(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "success.log"
            pid = runner.run_process([sys.executable, "-c", "import os; print(os.getpid(), flush=True)"], root, os.environ.copy(), log, 5)
            self.assertEqual(int(log.read_text().strip()), pid)

    @unittest.skipUnless(sys.platform == "linux", "Owned descendant proof uses Linux proc state")
    def test_timeout_kills_owned_term_ignoring_descendant_and_preserves_other_group(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
            child_code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('ready',flush=True); time.sleep(30)"
            parent_code = ("import subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c'," + repr(child_code)
                           + "],stdout=subprocess.PIPE,text=True); assert p.stdout.readline().strip()=='ready'; print(p.pid,flush=True); time.sleep(30)")
            log = root / "timeout.log"
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    runner.run_process([sys.executable, "-c", parent_code], root, os.environ.copy(), log, 0.5)
                child_pid = int(log.read_text().strip())
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    stat = Path("/proc") / str(child_pid) / "stat"
                    if not stat.exists() or stat.read_text().split()[2] == "Z":
                        break
                    time.sleep(0.02)
                else:
                    self.fail("Owned descendant remained running after bounded timeout")
                self.assertIsNone(unrelated.poll(), "Unrelated owned-control group must remain alive")
            finally:
                runner.terminate_owned(unrelated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
