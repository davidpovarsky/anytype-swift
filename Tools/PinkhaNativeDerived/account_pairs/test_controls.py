"""Controller rejection tests only; these do not execute or simulate native acceptance."""
import json
from pathlib import Path
import tempfile
import unittest

import run_account_pairs as controller


def sample_state():
    docs = []
    for index, name in enumerate(["document", "block", "quote"]):
        block_id = "" if index == 0 else name + "-real-block"
        record = dict(spaceId="original-space", objectId=name,
                      unknownRecord={"preserve": "unchanged"},
                      item=dict(role="sourceQuote" if index == 2 else "context",
                                canonicalKey="Genesis 3:3", unknownItem="preserve"))
        if block_id:
            record["blockId"] = block_id
        docs.append(dict(ID=name, BlockID=block_id, Name="original title",
                         Canonical=json.dumps(dict(version=2, unknownRoot="preserve", records=[record]))))
    return dict(AccountID="original-account", SpaceID="original-space", ManifestID="manifest",
                ManifestRaw="opaque manifest", CanonicalKey="canonical-property", Documents=docs)


def identity(role):
    return dict(heart_sha=controller.shared.PIN, patch_sha256=controller.shared.PATCHES[role],
                fixture_sha256="f" * 64, runtime_version=controller.runtime_version(role))


def report_for(phase, role):
    initial = phase == "old-create"
    calls = dict(InitialSetParameters=1, AppGetVersion=1, AccountStop=1, AppShutdown=1, WorkspaceOpen=1,
                 AccountPreloadRemainingSpaces=1, ObjectExport=6, ObjectShow=7, ObjectSearch=2 if role == "new" else 1)
    if initial:
        calls.update(WalletCreate=1, AccountCreate=1, WorkspaceCreate=1,
                     WorkspaceObjectListAdd=1, BlockCreate=2, ObjectCreate=4)
    else:
        calls.update(WalletRecover=1, AccountSelect=1)
        if phase == "old-edit":
            calls["ObjectSetDetails"] = 1
    names = {name: "original title" for name in ["document", "block", "quote"]}
    if phase in ["old-edit", "new-recover"]:
        names["document"] = "T5 ordinary title edited by r14"
    return dict(protocol=controller.PROTOCOL, phase=phase, nonce="current-nonce", pid=123,
                **identity(role), account_root=str(Path("/fresh/account-root")), account_id="original-account",
                space_id="original-space", state_sha256="e" * 64, closed=True, test_passed=True,
                account_stop_completed=True, application_cleared=True,
                export_status="ACTUAL_JSON_AND_PROTOBUF", swift_pairing_status="NOT_RUN",
                client_enablement=controller.DISABLED, rpc_calls=calls, ordinary_names=names,
                canonical_sha256={key: "a" * 64 for key in ["manifest", "document", "block", "quote"]},
                public_sha256={key: "b" * 64 for key in ["document", "block", "quote"]},
                block_sha256={key: "c" * 64 for key in ["block", "quote"]},
                exports={key: "d" * 64 for key in controller.EXPORT_NAMES},
                public_members=["document"],
                private_members=["block", "document", "quote"] if role == "new" else [],
                private_query_status="EXECUTED" if role == "new" else "NOT_ATTEMPTED_RUNTIME_UNAVAILABLE",
                private_versions={key: 1 if role == "new" else 0 for key in ["document", "block", "quote"]})


class AccountPairControls(unittest.TestCase):
    def validate(self, report, phase="new-upgrade", role="new", state=None):
        controller.validate_phase(report, phase, role, identity(role), "current-nonce",
                                  Path("/fresh/account-root"), 123, state or sample_state(), "e" * 64,
                                  None if phase == "old-create" else report_for("old-create", "old"))

    def test_each_legitimate_phase_preserves_an_explicit_native_only_scope(self):
        for phase, role in controller.PHASES:
            with self.subTest(phase=phase):
                self.validate(report_for(phase, role), phase, role)

    def test_stale_process_and_different_account_or_build_are_rejected(self):
        for key, value in [("nonce", "previous"), ("pid", 124), ("account_id", "recreated"),
                           ("space_id", "another-space"), ("account_root", "/different/account-root"),
                           ("state_sha256", "0" * 64), ("patch_sha256", "0" * 64),
                           ("runtime_version", controller.runtime_version("old"))]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                report[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_canonical_public_and_block_changes_cannot_be_hidden_by_success(self):
        for key in ["canonical_sha256", "public_sha256", "block_sha256"]:
            with self.subTest(key=key):
                report = report_for("new-upgrade", "new")
                report[key][next(iter(report[key]))] = "0" * 64
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_stale_private_rows_do_not_grant_the_old_runtime_capability(self):
        report = report_for("old-edit", "old")
        report["private_versions"] = {key: 1 for key in report["private_versions"]}
        self.validate(report, "old-edit", "old")
        report["private_query_status"] = "EXECUTED"
        report["private_members"] = ["block", "document", "quote"]
        with self.assertRaises(RuntimeError):
            self.validate(report, "old-edit", "old")

    def test_missing_target_and_bool_private_version_do_not_pass(self):
        for field, value in [("private_members", ["document"]), ("public_members", ["block", "document"]),
                             ("private_versions", {"document": True, "block": 1, "quote": 1})]:
            with self.subTest(field=field):
                report = report_for("new-upgrade", "new")
                report[field] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_later_account_object_or_block_recreation_is_rejected(self):
        for method in ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"]:
            with self.subTest(method=method):
                report = report_for("new-upgrade", "new")
                report["rpc_calls"][method] = 1
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_note_installation_is_required_once_and_forbidden_after_creation(self):
        for phase, role, count in [("old-create", "old", 0), ("new-upgrade", "new", 1)]:
            with self.subTest(phase=phase):
                report = report_for(phase, role)
                if count:
                    report["rpc_calls"]["WorkspaceObjectListAdd"] = count
                else:
                    report["rpc_calls"].pop("WorkspaceObjectListAdd")
                with self.assertRaises(RuntimeError):
                    self.validate(report, phase, role)

    def test_missing_shutdown_or_export_and_unproven_apple_claim_are_rejected(self):
        for change in ["shutdown", "export-count", "export-bytes", "swift", "enabled"]:
            with self.subTest(change=change):
                report = report_for("new-upgrade", "new")
                if change == "shutdown":
                    report["closed"] = False
                elif change == "export-count":
                    report["rpc_calls"]["ObjectExport"] = 0
                elif change == "export-bytes":
                    del report["exports"]["quote.pbc"]
                elif change == "swift":
                    report["swift_pairing_status"] = "PASS"
                else:
                    report["client_enablement"] = "ENABLED"
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_unconditional_app_shutdown_acknowledgement_does_not_prove_account_stop(self):
        for change in ["stop-missing", "stop-duplicated", "stop-failed", "app-retained"]:
            with self.subTest(change=change):
                report = report_for("new-upgrade", "new")
                if change == "stop-missing":
                    del report["rpc_calls"]["AccountStop"]
                elif change == "stop-duplicated":
                    report["rpc_calls"]["AccountStop"] = 2
                elif change == "stop-failed":
                    report["account_stop_completed"] = False
                else:
                    report["application_cleared"] = False
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_old_runtime_title_edit_must_survive_the_new_runtime(self):
        report = report_for("new-recover", "new")
        report["ordinary_names"]["document"] = "original title"
        with self.assertRaises(RuntimeError):
            self.validate(report, "new-recover", "new")

    def test_native_note_postcreation_name_is_preserved_even_when_empty(self):
        for phase, role in controller.PHASES[1:]:
            with self.subTest(phase=phase):
                state = sample_state()
                state["Documents"][1]["Name"] = ""
                report = report_for(phase, role)
                report["ordinary_names"]["block"] = ""
                self.validate(report, phase, role, state)
                report["ordinary_names"]["block"] = "invented requested name"
                with self.assertRaises(RuntimeError):
                    self.validate(report, phase, role, state)

    def test_initial_state_requires_real_distinct_targets_and_unknown_data(self):
        for change in ["target", "sourceQuote", "unknown", "duplicate-block"]:
            with self.subTest(change=change):
                state = sample_state()
                if change == "duplicate-block":
                    state["Documents"][2]["BlockID"] = state["Documents"][1]["BlockID"]
                else:
                    raw = json.loads(state["Documents"][2]["Canonical"])
                    if change == "target":
                        raw["records"][0]["objectId"] = "wrong-object"
                    elif change == "sourceQuote":
                        raw["records"][0]["item"]["role"] = "context"
                    else:
                        del raw["unknownRoot"]
                    state["Documents"][2]["Canonical"] = json.dumps(raw)
                with self.assertRaises(RuntimeError):
                    controller.validate_state(state)

    def test_evidence_allowlist_retains_original_export_bytes_and_excludes_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace, destination = Path(temp) / "private-work", Path(temp) / "evidence"
            workspace.mkdir()
            (workspace / "ownership.json").write_text("{}")
            (workspace / "result.json").write_text('{"status":"FAIL"}')
            (workspace / "sensitive-needles.private").write_text(json.dumps(["synthetic-account-secret", "synthetic mnemonic"]))
            (workspace / "account-key.private").write_text("synthetic-account-secret")
            (workspace / "unexpected.txt").write_text("synthetic-account-secret")
            (workspace / "old-create.log").write_text("original native log")
            raw = b"original native export bytes"
            export = workspace / "exports/old-create/document.pbc"
            export.parent.mkdir(parents=True)
            export.write_bytes(raw)
            receipt = controller.preserve_evidence(workspace, destination)
            self.assertEqual(receipt["secret_scan_status"], "PASS")
            self.assertEqual((destination / "exports/old-create/document.pbc").read_bytes(), raw)
            self.assertEqual((destination / "old-create.log").read_text(), "original native log")
            self.assertFalse((destination / "account-key.private").exists())
            self.assertFalse((destination / "sensitive-needles.private").exists())
            self.assertFalse((destination / "unexpected.txt").exists())

    def test_key_or_mnemonic_in_any_candidate_withholds_all_native_evidence(self):
        for needle in ["synthetic-account-secret", "synthetic mnemonic"]:
            with self.subTest(needle_type="key" if "-" in needle else "mnemonic"):
                with tempfile.TemporaryDirectory() as temp:
                    workspace, destination = Path(temp) / "work", Path(temp) / "evidence"
                    workspace.mkdir()
                    (workspace / "ownership.json").write_text("{}")
                    (workspace / "result.json").write_text("{}")
                    (workspace / "sensitive-needles.private").write_text(json.dumps(["synthetic-account-secret", "synthetic mnemonic"]))
                    (workspace / "old-create.log").write_text("unintended output: " + needle)
                    with self.assertRaises(RuntimeError):
                        controller.preserve_evidence(workspace, destination)
                    self.assertFalse(destination.exists())

    def test_early_wallet_failure_does_not_upload_unverified_native_output(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace, destination = Path(temp) / "work", Path(temp) / "evidence"
            workspace.mkdir()
            (workspace / "result.json").write_text('{"status":"FAIL"}')
            (workspace / "old-create.log").write_text("unverified early native output")
            receipt = controller.preserve_evidence(workspace, destination)
            self.assertEqual(receipt["secret_scan_status"], "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY")
            self.assertFalse((destination / "old-create.log").exists())
            self.assertTrue((destination / "result.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
