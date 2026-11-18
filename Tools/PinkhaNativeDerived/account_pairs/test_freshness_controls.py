"""Reject forged freshness receipts; only the compiled Go/RPC lane proves native behavior."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import run_account_pairs as controller
from test_controls import identity, report_for, sample_state

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_t5_account_pairs_ci as ci


def sha(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def freshness_fixture():
    state = sample_state()
    docs = state["Documents"]
    for doc in docs:
        value = json.loads(doc["Canonical"])
        value["records"][0]["item"].update(kind="ref", providerID="sefaria", externalID="Genesis 3:3")
        doc["Canonical"] = json.dumps(value)
    baseline = dict(private_primary=["block", "document", "quote"], public_primary=["document"],
                    private_verse=[], public_verse=[], private_provider=[], public_provider=[])
    checks = []
    for name, index, mode in controller.FRESHNESS_CASES:
        doc = docs[index]
        value = json.loads(doc["Canonical"])
        item = value["records"][0]["item"]
        members = copy.deepcopy(baseline)
        if mode != "label-alias":
            members["private_primary"].remove(doc["ID"])
            if index == 0:
                members["public_primary"] = []
        if mode == "other-verse":
            item.update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
            members["private_verse"] = [doc["ID"]]
            if index == 0:
                members["public_verse"] = [doc["ID"]]
        elif mode == "unlink":
            value["records"] = []
        elif mode == "label-alias":
            item.update(labelHe="\u05db\u05d5\u05ea\u05e8\u05ea \u05d0\u05d7\u05e8\u05ea",
                        labelEn="A different English display label")
        elif mode == "other-provider":
            item["providerID"] = "fixture-other-provider"
            members["private_provider"] = members["public_provider"] = [doc["ID"]]
        elif mode == "foreign-space":
            value["records"][0]["spaceId"] = "not-the-current-fixture-space"
        elif mode == "foreign-object":
            value["records"][0]["objectId"] = docs[0]["ID"]
        raw = "{" if mode == "malformed" else json.dumps(value)
        checks.append(dict(name=name, object_id=doc["ID"], canonical_raw=raw, canonical_sha256=sha(raw),
                           members=members, restored_members=copy.deepcopy(baseline), object_retained=True,
                           canonical_restored_sha256=sha(doc["Canonical"])))
    archived = copy.deepcopy(baseline)
    archived["private_primary"] = ["document", "quote"]
    checks += [
        dict(name="archive_cycle", object_id="block", members=archived, restored_members=copy.deepcopy(baseline),
             archive_observed=True, unarchive_observed=True),
        dict(name="type_cycle", object_id="document", members=copy.deepcopy(baseline),
             restored_members=copy.deepcopy(baseline), note_type_id="native-note-type", page_type_id="native-page-type"),
    ]
    for name, doc in zip(["block_target_removed", "source_quote_target_removed"], docs[1:]):
        checks.append(dict(name=name, object_id=doc["ID"], block_id=doc["BlockID"],
                           members=copy.deepcopy(baseline), canonical_sha256=sha(doc["Canonical"]),
                           live_root_id=doc["ID"], live_graph_nodes=[dict(id=doc["ID"], child_ids=[])],
                           target_reachable=False, host_target_exclusion_status="NOT_RUN_SWIFT_HOST"))
    deleted = copy.deepcopy(baseline)
    deleted.update(private_primary=["block", "quote"], public_primary=[])
    checks.append(dict(name="object_deleted", object_id="document", members=deleted, object_show_error=4))
    report = dict(protocol=controller.PROTOCOL, phase="new-freshness", nonce="current-nonce", pid=123,
                  **identity("new"), account_root=str(Path("/fresh/account-root")), account_id=state["AccountID"],
                  space_id=state["SpaceID"], state_sha256="e" * 64, closed=True, test_passed=True,
                  account_stop_completed=True, application_cleared=True,
                  freshness_status=controller.FRESHNESS_STATUS, checks=checks, coverage="indexedTargetsOnly",
                  space_wide_freshness="NOT_PROVEN", host_target_exclusion_status="NOT_RUN_SWIFT_HOST",
                  write_origin=controller.FRESHNESS_ORIGIN, client_enablement=controller.DISABLED,
                  swift_pairing_status="NOT_RUN",
                  rpc_calls=dict(InitialSetParameters=1, AppGetVersion=1, WalletRecover=1, AccountSelect=1,
                                 WorkspaceOpen=1, AccountStop=1, AccountPreloadRemainingSpaces=1, AppShutdown=1,
                                 ObjectSetDetails=22, ObjectListSetIsArchived=2, ObjectSetObjectType=2,
                                 BlockListDelete=2, ObjectListDelete=1, ObjectShow=32, ObjectSearch=182))
    return state, report


def result_fixture(include_freshness=True):
    reports = [report_for(phase, role) for phase, role in controller.PHASES]
    for index, report in enumerate(reports):
        report.update(pid=100 + index, nonce="nonce-" + str(index))
    _, fresh = freshness_fixture()
    fresh.update(pid=104, nonce="nonce-4")
    return dict(status=controller.STATUS, include_freshness=include_freshness,
                actual_counts=dict(binaries=2, native_processes=5 if include_freshness else 4,
                                   passing_test_invocations=5 if include_freshness else 4, actual_export_files=24),
                export_status="ACTUAL_JSON_AND_PROTOBUF", swift_pairing_status="NOT_RUN",
                full_F10="NOT_PROVEN", client_enablement=controller.DISABLED, phase_reports=reports,
                freshness_report=fresh if include_freshness else None,
                freshness_status=controller.FRESHNESS_STATUS if include_freshness else "NOT_REQUESTED")


class FreshnessControls(unittest.TestCase):
    def validate(self, report, state=None):
        controller.validate_freshness_phase(report, identity("new"), "current-nonce",
                                             Path("/fresh/account-root"), 123,
                                             state or freshness_fixture()[0], "e" * 64)

    def test_explicit_native_only_sixteen_check_receipt_is_accepted(self):
        state, report = freshness_fixture()
        self.validate(report, state)
        self.assertEqual(len(report["checks"]), 16)

    def test_wrong_source_process_account_and_stop_are_rejected(self):
        for key, value in [("nonce", "old"), ("pid", 124), ("runtime_version", controller.runtime_version("old")),
                           ("fixture_sha256", "0" * 64), ("patch_sha256", "0" * 64), ("state_sha256", "0" * 64),
                           ("account_root", "/different"), ("space_id", "other"), ("account_id", "other"),
                           ("closed", False), ("account_stop_completed", False), ("application_cleared", False)]:
            with self.subTest(field=key):
                _, report = freshness_fixture()
                report[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_missing_or_reordered_mutation_and_every_wrong_index_observation_are_rejected(self):
        for index in range(16):
            with self.subTest(case=index):
                _, report = freshness_fixture()
                report["checks"][index]["members"]["private_primary"] = ["foreign-object"]
                with self.assertRaises(RuntimeError):
                    self.validate(report)
        for operation in ["missing", "reordered"]:
            with self.subTest(operation=operation):
                _, report = freshness_fixture()
                if operation == "missing":
                    report["checks"].pop()
                else:
                    report["checks"][0], report["checks"][1] = report["checks"][1], report["checks"][0]
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_unlink_cannot_delete_note_or_lose_unknown_fields_on_restore(self):
        for change in ["deleted-note", "lost-unknown-root", "bad-digest", "restored-different-bytes"]:
            with self.subTest(change=change):
                _, report = freshness_fixture()
                target = report["checks"][5]
                if change == "deleted-note":
                    target["object_retained"] = False
                elif change == "lost-unknown-root":
                    value = json.loads(target["canonical_raw"])
                    del value["unknownRoot"]
                    target["canonical_raw"] = json.dumps(value)
                    target["canonical_sha256"] = sha(target["canonical_raw"])
                elif change == "bad-digest":
                    target["canonical_sha256"] = "0" * 64
                else:
                    target["canonical_restored_sha256"] = "0" * 64
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_removed_target_bool_cannot_hide_a_reachable_or_invalid_live_graph(self):
        for change in ["reachable", "missing-root", "dangling-child", "duplicate", "wrong-target"]:
            with self.subTest(change=change):
                _, report = freshness_fixture()
                target = report["checks"][14]
                if change == "reachable":
                    target["live_graph_nodes"][0]["child_ids"] = [target["block_id"]]
                    target["live_graph_nodes"].append(dict(id=target["block_id"], child_ids=[]))
                elif change == "missing-root":
                    target["live_graph_nodes"][0]["id"] = "foreign-root"
                elif change == "dangling-child":
                    target["live_graph_nodes"][0]["child_ids"] = ["missing-node"]
                elif change == "duplicate":
                    target["live_graph_nodes"].append(copy.deepcopy(target["live_graph_nodes"][0]))
                else:
                    target["block_id"] = "different-target"
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_failed_archive_type_or_delete_observation_cannot_pass(self):
        for index, field, value in [(11, "archive_observed", False), (11, "unarchive_observed", False),
                                    (12, "note_type_id", "native-page-type"), (15, "object_show_error", 0),
                                    (15, "object_show_error", True)]:
            with self.subTest(case=index, field=field):
                _, report = freshness_fixture()
                report["checks"][index][field] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_fixture_recreation_reindex_or_missing_native_mutations_cannot_pass(self):
        for rpc, count in [("WalletCreate", 1), ("ObjectCreate", 1), ("BlockCreate", 1), ("ObjectExport", 1),
                           ("Reindex", 1), ("ObjectSetDetails", 21), ("BlockListDelete", 1),
                           ("AccountStop", 0), ("ObjectSearch", 1), ("AccountSelect", 2)]:
            with self.subTest(rpc=rpc):
                _, report = freshness_fixture()
                report["rpc_calls"][rpc] = count
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_native_receipt_cannot_claim_swift_target_exclusion_or_complete_space_coverage(self):
        for key, value in [("coverage", "spaceWide"), ("space_wide_freshness", "PASS"),
                           ("host_target_exclusion_status", "PASS"), ("swift_pairing_status", "PASS"),
                           ("client_enablement", "ENABLED"), ("write_origin", "MOCK_OR_MANUAL_REINDEX")]:
            with self.subTest(field=key):
                _, report = freshness_fixture()
                report[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_ci_retains_four_compatibility_phases_and_explicit_fifth_process(self):
        for enabled in [False, True]:
            with self.subTest(enabled=enabled):
                counts = ci.validate_account_result(result_fixture(enabled), enabled)
                self.assertEqual(counts["native_processes"], 5 if enabled else 4)
                self.assertEqual(counts["actual_export_files"], 24)

    def test_ci_rejects_missing_duplicate_or_unrequested_freshness_process(self):
        for change in ["missing", "pid", "nonce", "state", "count", "unrequested"]:
            with self.subTest(change=change):
                result = result_fixture()
                if change == "missing":
                    result["freshness_report"] = None
                elif change in ["pid", "nonce"]:
                    result["freshness_report"][change] = result["phase_reports"][0][change]
                elif change == "state":
                    result["freshness_report"]["state_sha256"] = "0" * 64
                elif change == "count":
                    result["actual_counts"]["native_processes"] = 4
                with self.assertRaises(RuntimeError):
                    ci.validate_account_result(result, change != "unrequested")

    def test_freshness_evidence_is_opt_in_and_secret_scan_finishes_before_any_copy(self):
        for enabled, leaked in [(False, False), (True, False), (True, True)]:
            with self.subTest(enabled=enabled, leaked=leaked), tempfile.TemporaryDirectory() as temp:
                work, target = Path(temp) / "work", Path(temp) / "evidence"
                work.mkdir()
                (work / "ownership.json").write_text("{}")
                (work / "result.json").write_text("{}")
                (work / "sensitive-needles.private").write_text(json.dumps(["private-key-value", "private mnemonic"]))
                (work / "new-freshness.log").write_text("private-key-value" if leaked else "actual native log")
                (work / "new-freshness.json").write_text("{}")
                (work / "account-key.private").write_text("private-key-value")
                if leaked:
                    with self.assertRaises(RuntimeError):
                        controller.preserve_evidence(work, target, enabled)
                    self.assertFalse(target.exists())
                else:
                    receipt = controller.preserve_evidence(work, target, enabled)
                    self.assertEqual((target / "new-freshness.log").exists(), enabled)
                    self.assertEqual(receipt["secret_scan_status"], "PASS")
                    self.assertFalse((target / "account-key.private").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
