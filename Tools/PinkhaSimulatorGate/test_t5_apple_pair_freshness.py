"""Controller rejection cases for the opt-in Apple host freshness phase, not native acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import run_t5_apple_pair as controller
from test_t5_apple_pair import TOKEN, SOURCE, LEDGER_SHA, ledger_for, report_for, builds


def fresh_inputs():
    ledger = ledger_for("new-recover")
    ledger["completedPhases"].append("new-freshness")
    originals = {}
    for index, document in enumerate(ledger["documents"]):
        record = dict(spaceId=ledger["spaceID"], objectId=document["objectID"],
                      unknownRecord={"sentinel": "preserve"},
                      item=dict(id="item-" + str(index), kind="ref", providerID="sefaria",
                                canonicalKey="Genesis 3:3", externalID="Genesis 3:3",
                                role="sourceQuote" if index == 2 else "context", unknownItem="preserve"))
        if document.get("blockID"):
            record["blockId"] = document["blockID"]
        raw = json.dumps(dict(version=2, records=[record], unknownRoot="preserve"))
        originals[document["objectID"]] = raw
        document["canonicalSHA256"] = controller.sha_bytes(raw.encode())
    documents = ledger["documents"]
    specifications = [
        ("baseline", [0, 1, 2], [0, 1, 2], None, "original", True, False),
        ("note_unlink", [0, 2], [0, 2], 1, "unlink", True, False),
        ("note_restore", [0, 1, 2], [0, 1, 2], 1, "original", True, False),
        ("quote_update_original", [0, 1], [0, 1], 2, "verse", True, False),
        ("quote_update_other", [2], [2], 2, "verse", True, False),
        ("quote_restore", [0, 1, 2], [0, 1, 2], 2, "original", True, False),
        ("note_archive", [0, 2], [0, 2], 1, "original", True, True),
        ("note_unarchive", [0, 1, 2], [0, 1, 2], 1, "original", True, False),
        ("note_block_removed", [0, 1, 2], [0, 2], 1, "original", False, False),
        ("quote_block_removed", [0, 1, 2], [0], 2, "original", False, False),
        ("page_deleted", [1, 2], [], 0, "deleted", False, False),
    ]
    observations = []
    for name, native, host, index, mode, reachable, archived in specifications:
        row = dict(name=name, spaceID=ledger["spaceID"],
                   sourceReference="Genesis 3:4" if name == "quote_update_other" else "Genesis 3:3",
                   nativeCandidatesBefore=sorted(documents[i]["objectID"] for i in native),
                   nativeCandidatesAfter=sorted(documents[i]["objectID"] for i in native),
                   targets=[dict(objectID=documents[i]["objectID"], blockID=documents[i].get("blockID"),
                                 canUnlink=documents[i].get("blockID") is None) for i in host],
                   coverage="indexedTargetsOnly",
                   limitations=["indexFreshnessUnverified"] + (["staleCandidates"] if not reachable else []))
        if index is not None:
            document = documents[index]
            row["objectID"] = document["objectID"]
            if mode == "deleted":
                row["objectShowError"] = 4
            else:
                raw = originals[document["objectID"]]
                if mode != "original":
                    value = json.loads(raw)
                    if mode == "unlink":
                        value["records"] = []
                    else:
                        value["records"][0]["item"].update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
                    raw = json.dumps(value)
                nodes = [dict(id=document["objectID"], childIDs=[document["blockID"]] if reachable else [])]
                if reachable:
                    nodes.append(dict(id=document["blockID"], childIDs=[]))
                row.update(canonicalRaw=raw, canonicalSHA256=controller.sha_bytes(raw.encode()),
                           objectRetained=True, isArchived=archived,
                           graph=dict(spaceID=ledger["spaceID"], rootID=document["objectID"],
                                      targetID=document["blockID"], targetReachable=reachable, nodes=nodes))
        observations.append(row)
    freshness = dict(status=controller.FRESHNESS_STATUS,
                     writeOrigin="DIRECT_NATIVE_RPC_WITHOUT_EXPLICIT_HOST_INVALIDATION",
                     serviceScope="ONE_REUSED_PRODUCTION_SERVICE", coverage="indexedTargetsOnly",
                     spaceWideFreshness="NOT_PROVEN", navigationStatus="NOT_RUN",
                     originalCanonical=originals, observations=observations,
                     nativeMutationCounts=dict(ObjectSetDetails=4, ObjectListSetIsArchived=2,
                                               BlockListDelete=2, ObjectListDelete=1))
    report = report_for("new-recover", "new")
    for row, original in zip(report["documents"], documents):
        row["canonicalSHA256"] = original["canonicalSHA256"]
    prior = copy.deepcopy(report)
    report.update(phase="new-freshness", nonce="5" * 32, processID=104,
                  readbackBoundary="BEFORE_FRESHNESS_MUTATIONS", freshness=freshness)
    return ledger, report, prior


class AppleFreshnessControls(unittest.TestCase):
    def validate(self, report, ledger=None, prior=None):
        state, _, previous = fresh_inputs()
        controller.validate_phase(report, "new-freshness", "new", TOKEN, "5" * 32, SOURCE,
                                  ledger or state, LEDGER_SHA, prior or previous)

    def test_actual_fifth_phase_has_separate_mutation_and_compatibility_boundaries(self):
        ledger, report, prior = fresh_inputs()
        self.validate(report, ledger, prior)
        self.assertEqual(controller.validate_host_freshness(report["freshness"], ledger), 11)
        self.assertEqual(len(controller.phases()), 4)
        self.assertEqual(len(controller.phases(True)), 5)

    def test_missing_phase_identity_or_recreated_account_cannot_claim_host_freshness(self):
        for field, value in [("nonce", "stale"), ("runtimeVersion", controller.runtime_version("old")),
                             ("accountID", "recreated"), ("spaceID", "foreign"), ("appSourceSHA", "0" * 40),
                             ("readbackBoundary", "BEFORE_ACCOUNT_STOP"), ("accountCreated", True),
                             ("accountStopCompleted", False)]:
            with self.subTest(field=field):
                _, report, _ = fresh_inputs()
                report[field] = value
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_every_observation_requires_both_native_membership_reads(self):
        for index in range(11):
            for field in ["nativeCandidatesBefore", "nativeCandidatesAfter"]:
                with self.subTest(index=index, field=field):
                    _, report, _ = fresh_inputs()
                    report["freshness"]["observations"][index][field] = ["foreign"]
                    with self.assertRaises(RuntimeError):
                        self.validate(report)

    def test_deleted_target_cannot_leak_through_host_results_or_hide_stale_disclosure(self):
        for index in [8, 9, 10]:
            for change in ["returned-target", "missing-stale"]:
                with self.subTest(index=index, change=change):
                    _, report, _ = fresh_inputs()
                    row = report["freshness"]["observations"][index]
                    if change == "returned-target":
                        row["targets"].append(dict(objectID="block", blockID="block-leaf", canUnlink=False))
                    else:
                        row["limitations"] = ["indexFreshnessUnverified"]
                    with self.assertRaises(RuntimeError):
                        self.validate(report)

    def test_claimed_exclusion_cannot_hide_a_still_reachable_or_foreign_graph(self):
        for change in ["reachable", "foreign-space", "foreign-root", "missing-child", "duplicate-node"]:
            with self.subTest(change=change):
                _, report, _ = fresh_inputs()
                graph = report["freshness"]["observations"][9]["graph"]
                if change == "reachable":
                    graph["nodes"][0]["childIDs"] = [graph["targetID"]]
                    graph["nodes"].append(dict(id=graph["targetID"], childIDs=[]))
                elif change == "foreign-space":
                    graph["spaceID"] = "different"
                elif change == "foreign-root":
                    graph["rootID"] = "different"
                elif change == "missing-child":
                    graph["nodes"][0]["childIDs"] = ["absent"]
                else:
                    graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_unlink_and_restore_must_keep_note_unknown_fields_and_original_block(self):
        for change in ["delete-note", "lose-unknown", "different-restore", "lose-block"]:
            with self.subTest(change=change):
                _, report, _ = fresh_inputs()
                row = report["freshness"]["observations"][1 if change != "different-restore" else 2]
                if change == "delete-note":
                    row["objectRetained"] = False
                elif change == "lose-unknown":
                    value = json.loads(row["canonicalRaw"])
                    del value["unknownRoot"]
                    row["canonicalRaw"] = json.dumps(value)
                    row["canonicalSHA256"] = controller.sha_bytes(row["canonicalRaw"].encode())
                elif change == "different-restore":
                    row["canonicalRaw"] += " "
                    row["canonicalSHA256"] = controller.sha_bytes(row["canonicalRaw"].encode())
                else:
                    row["graph"]["nodes"][0]["childIDs"] = []
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_no_freshness_or_navigation_completion_can_be_inferred_from_partial_observations(self):
        for change in ["missing-observation", "missing-mutation", "fixture-create", "new-service", "space-wide", "navigation"]:
            with self.subTest(change=change):
                _, report, _ = fresh_inputs()
                proof = report["freshness"]
                if change == "missing-observation":
                    proof["observations"].pop()
                elif change == "missing-mutation":
                    proof["nativeMutationCounts"]["BlockListDelete"] = 1
                elif change == "fixture-create":
                    proof["nativeMutationCounts"]["ObjectCreate"] = 1
                elif change == "new-service":
                    proof["serviceScope"] = "RECREATED_AFTER_EVERY_WRITE"
                elif change == "space-wide":
                    proof["spaceWideFreshness"] = "PASS"
                else:
                    proof["navigationStatus"] = "PASS"
                with self.assertRaises(RuntimeError):
                    self.validate(report)

    def test_sequence_requires_fifth_process_and_keeps_four_phase_default(self):
        ledger, fresh, _ = fresh_inputs()
        reports = [report_for(phase, role) for phase, role in controller.PHASES]
        for report in reports:
            for row, original in zip(report["documents"], ledger["documents"]):
                row["canonicalSHA256"] = original["canonicalSHA256"]
        counts = controller.validate_sequence(reports, builds())
        self.assertEqual(counts["named_swift_tests_passed"], 4)
        counts = controller.validate_sequence(reports + [fresh], builds(), True)
        self.assertEqual(counts["named_swift_tests_passed"], 5)
        self.assertEqual(counts["host_freshness_observations"], 11)
        for change in ["missing", "pid", "nonce", "unrequested"]:
            with self.subTest(change=change):
                values = copy.deepcopy(reports + [fresh])
                if change == "missing":
                    values.pop()
                elif change in ["pid", "nonce"]:
                    field = "processID" if change == "pid" else "nonce"
                    values[-1][field] = values[0][field]
                with self.assertRaises(RuntimeError):
                    controller.validate_sequence(values, builds(), change != "unrequested")

    def test_fifth_phase_secret_scan_is_explicit_and_all_or_nothing(self):
        for enabled, leaked in [(False, False), (True, False), (True, True)]:
            with self.subTest(enabled=enabled, leaked=leaked), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                work, proof, container = root / "work", root / "proof", root / "container"
                phase = work / "phases/new-freshness"
                phase.mkdir(parents=True)
                proof.mkdir()
                secret = container / "Library/Application Support/pinkha-t5-runtime-pair/secrets.json"
                secret.parent.mkdir(parents=True)
                secret.write_text(json.dumps(dict(token=TOKEN, mnemonic="private mnemonic", accountKey="private-key")))
                (phase / "test.log").write_text("private-key" if leaked else "actual named Swift test")
                if leaked:
                    with self.assertRaises(RuntimeError):
                        controller.preserve_native_evidence(work, proof, container, TOKEN, enabled)
                    self.assertFalse((proof / "actual-phases").exists())
                else:
                    self.assertTrue(controller.preserve_native_evidence(work, proof, container, TOKEN, enabled))
                    self.assertEqual((proof / "actual-phases/new-freshness/test.log").exists(), enabled)
                    self.assertFalse((proof / "secrets.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
