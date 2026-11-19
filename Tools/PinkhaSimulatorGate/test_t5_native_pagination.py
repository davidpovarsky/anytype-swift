"""Synthetic rejection controls only; no native or Apple acceptance is inferred."""
import copy
import json
import unittest

import t5_native_pagination_evidence as evidence
from run_t5_apple_pair import runtime_version

SOURCE = "a" * 40
TOKEN = "b" * 32
RUN = "44500000000"
ROOT = "c" * 64


def inputs():
    objects = []
    for index, role in enumerate(evidence.ROLES):
        space = "space-other" if role == "foreign" else "space-current"
        identifier = "object-" + str(index)
        kinds = ["document", "block", "quote"] if role == "multi" else [role if role in ["block", "quote"] else "document"]
        targets, records, children = [], [], []
        for target_index, kind in enumerate(kinds):
            block = identifier + "-block-" + str(target_index) if kind != "document" else None
            if block:
                children.append(block)
            association = identifier + "-association-" + str(target_index)
            targets.append(dict(objectID=identifier, blockID=block, associationID=association, role=kind))
            reference = "Genesis 5:6" if role == "different_verse" else "Genesis 5:5"
            item = dict(id=association, kind="ref", role="sourceQuote" if kind == "quote" else "context",
                        providerID="fixture-other-provider" if role == "different_provider" else "sefaria",
                        canonicalKey=reference, externalID=reference, unknownItem="retained")
            records.append(dict(spaceId=space, objectId=identifier, blockId=block, item=item, unknownRecord="retained"))
        raw = json.dumps(dict(version=2, records=records, unknownRoot="retained"), sort_keys=True)
        nodes = [dict(id=identifier, childIDs=children), *[dict(id=child, childIDs=[]) for child in children]]
        original = dict(objectID=identifier, spaceID=space, rootID=identifier, title="Native " + role,
                        typeID="native-" + (role if role in ["note", "writing"] else "page"),
                        isArchived=False, isDeleted=False, isReadonly=False, detailsRestricted=False,
                        projectionReady=True, projectionState="READY", projectionVersion=1, relatedVersion=1,
                        canonicalRaw=raw, canonicalSHA256=evidence.sha(raw), updatedAt=1000.0 + index, nodes=nodes)
        objects.append(dict(role=role, spaceID=space, objectID=identifier, canonicalKey="native-canonical",
                            targets=targets, original=original))
    observations = []
    for name in evidence.STAGES:
        foreign = name == "other_space"
        space = "space-other" if foreign else "space-current"
        selected = objects[9:] if foreign else objects[:7]
        excluded = "note" if name == "note_archive" else "page_a" if name == "page_unlink" else None
        native = sorted(obj["objectID"] for obj in selected if obj["role"] != excluded)
        candidate_limit, target_limit = (5, 50) if name == "candidate_cap" else (50, 3) if name == "target_cap" else (50, 50)
        visited = native[:candidate_limit]
        calls, seen = [], []
        for limit, chunk in ([(2, visited[:2]), (2, visited[2:4]), (1, visited[4:5])] if name == "candidate_cap"
                             else [(2, native[index:index + 2]) for index in range(0, len(native) + 1, 2)]):
            filters = [dict(key=key, condition="notEqual", valueJSON="true")
                       for key in ["isHidden", "isHiddenDiscovery", "isDeleted", "isArchived"]]
            filters += [dict(key="uniqueKey", condition="notEqual", valueJSON='"ot-objectType"'),
                        dict(key="type.uniqueKey", condition="notEqual", valueJSON='"ot-template"'),
                        dict(key="spaceId", condition="equal", valueJSON=json.dumps(space)),
                        dict(key="_pinkhaTorahRelatedSources", condition="in", valueJSON=json.dumps([evidence.INDEX]))]
            if seen:
                filters.append(dict(key="id", condition="notIn", valueJSON=json.dumps(seen)))
            calls.append(dict(spaceID=space, limit=limit, offset=0, fullText="", keys=sorted(evidence.KEYS),
                              filters=filters, sorts=[dict(key="id", direction="asc", noCollate=True)],
                              objectIDs=chunk, resultSpaceIDs=[space] * len(chunk)))
            seen.extend(chunk)
        readbacks, rows = [], []
        for obj in selected:
            current = copy.deepcopy(obj["original"])
            if name == "note_archive" and obj["role"] == "note":
                current["isArchived"] = True
            if name == "page_unlink" and obj["role"] == "page_a":
                canonical = json.loads(current["canonicalRaw"])
                canonical["records"] = []
                current["canonicalRaw"] = json.dumps(canonical, sort_keys=True)
                current["canonicalSHA256"] = evidence.sha(current["canonicalRaw"])
            removed = name == "block_removed" and obj["role"] == "block"
            if removed:
                current["nodes"] = [dict(id=obj["objectID"], childIDs=[])]
            readbacks.append(current)
            if obj["objectID"] not in visited or obj["role"] == excluded or removed:
                continue
            for target in obj["targets"]:
                rows.append(dict(id=evidence.target_id(space, obj["objectID"], target["blockID"]),
                                 spaceID=space, objectID=obj["objectID"], blockID=target["blockID"], title=current["title"],
                                 typeID=current["typeID"], sourceReference="Genesis 5:5", canUnlink=target["role"] == "document",
                                 kind="note" if obj["role"] == "note" else "document", updatedAt=current["updatedAt"]))
        rows.sort(key=lambda row: (-row["updatedAt"], row["id"]))
        limitations = ["indexFreshnessUnverified"]
        if name in ["candidate_cap", "target_cap"]:
            limitations.append("resultLimitReached")
        if name == "block_removed":
            limitations.append("staleCandidates")
        observations.append(dict(name=name, serviceID=name if name in ["candidate_cap", "target_cap"] else "base-service",
                                 activeSpaceID=space, requestedSpaceID=space, pageSize=2,
                                 candidateLimit=candidate_limit, targetLimit=target_limit,
                                 nativeCandidatesBefore=native, nativeCandidatesAfter=native,
                                 calls=calls, rows=rows[:target_limit], coverage="indexedTargetsOnly",
                                 limitations=sorted(limitations), readbacks=readbacks))
    return dict(protocolVersion=evidence.PROTOCOL, status="PASS_NATIVE_OBSERVATIONS", token=TOKEN,
                appSourceSHA=SOURCE, runID=RUN, processID=111, runtimeVersion=runtime_version("new"),
                accountID="disposable-account", spaceID="space-current", foreignSpaceID="space-other", rootPathSHA256=ROOT,
                providerID="sefaria", canonicalReference="Genesis 5:5", indexValue=evidence.INDEX, objects=objects,
                observations=observations, nativeMutationCounts=dict(SetActiveSpace=2, ObjectListSetIsArchived=2,
                ObjectSetDetails=2, BlockListDelete=1), accountStopCompleted=True, accountNotRunningConfirmed=True,
                appShutdownCompleted=True, productLookupFlag="OFF", wholeIndexCompleteness="NOT_PROVEN", aclRevocation="NOT_PROVEN")


class NativePaginationEvidenceControls(unittest.TestCase):
    def validate(self, receipt):
        return evidence.validate_receipt(receipt, source=SOURCE, run_id=RUN, token=TOKEN, root_sha=ROOT)

    def reject(self, mutate):
        value = inputs()
        mutate(value)
        with self.assertRaises((RuntimeError, ValueError, KeyError, TypeError)):
            self.validate(value)

    def test_complete_synthetic_receipt_has_exact_bounded_scope(self):
        result = self.validate(inputs())
        self.assertEqual(result["actual_search_calls"], 36)
        self.assertEqual(result["current_space_targets"], 9)
        self.assertEqual(result["whole_index_completeness"], "NOT_PROVEN")

    def test_exact_source_runtime_account_stop_and_product_boundary_are_required(self):
        for field, value in [("appSourceSHA", "d" * 40), ("runtimeVersion", runtime_version("old")),
                             ("token", "e" * 32), ("runID", "other"), ("rootPathSHA256", "f" * 64),
                             ("accountID", ""), ("foreignSpaceID", "space-current"), ("processID", 0),
                             ("accountStopCompleted", False), ("accountNotRunningConfirmed", False),
                             ("appShutdownCompleted", False), ("productLookupFlag", "ON"),
                             ("wholeIndexCompleteness", "PASS"), ("aclRevocation", "PASS")]:
            with self.subTest(field=field):
                self.reject(lambda receipt: receipt.update({field: value}))

    def test_source_and_fixture_scope_cannot_be_substituted(self):
        for field in ["providerID", "canonicalReference", "indexValue"]:
            with self.subTest(field=field):
                self.reject(lambda receipt: receipt.update({field: "wrong"}))
        self.reject(lambda receipt: receipt["objects"].pop())
        self.reject(lambda receipt: receipt["objects"][0].update(spaceID="space-other"))
        self.reject(lambda receipt: receipt["objects"][1].update(objectID=receipt["objects"][0]["objectID"]))
        self.reject(lambda receipt: receipt["objects"][3]["original"].update(typeID="native-page"))

    def test_late_page_cannot_be_dropped_repeated_or_replaced(self):
        self.reject(lambda receipt: receipt["observations"][0]["calls"].pop())
        self.reject(lambda receipt: receipt["observations"][0]["calls"][2].update(objectIDs=["object-0", "object-1"]))
        self.reject(lambda receipt: receipt["observations"][0]["calls"].append(copy.deepcopy(receipt["observations"][0]["calls"][-1])))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][3].update(objectIDs=[]))

    def test_actual_request_page_size_keys_sort_and_exclusions_are_mandatory(self):
        for field, value in [("limit", 50), ("offset", 2), ("fullText", "Genesis"), ("keys", ["id"]),
                             ("sorts", [dict(key="id", direction="desc", noCollate=True)])]:
            with self.subTest(field=field):
                self.reject(lambda receipt: receipt["observations"][0]["calls"][0].update({field: value}))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][1]["filters"][-1].update(valueJSON='["wrong"]'))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][1]["filters"].pop())

    def test_request_and_result_space_filters_are_independent(self):
        self.reject(lambda receipt: receipt["observations"][0].update(activeSpaceID="space-other"))
        self.reject(lambda receipt: receipt["observations"][3].update(requestedSpaceID="space-current"))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][0].update(resultSpaceIDs=["space-other"] * 2))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"][6].update(valueJSON='"space-other"'))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"][7].update(valueJSON='["wrong-source"]'))

    def test_exact_type_and_template_predicates_reject_extra_or_missing_filters(self):
        for index in [4, 5]:
            with self.subTest(index=index):
                self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"].pop(index))
                self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"][index].update(valueJSON='"wrong-type"'))
                self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"][index].update(condition="equal"))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"].append(dict(key="name", condition="equal", valueJSON='"hidden subset"')))
        self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"].append(copy.deepcopy(receipt["observations"][0]["calls"][0]["filters"][7])))

    def test_each_visibility_predicate_and_both_raw_membership_reads_are_required(self):
        for index in range(4):
            with self.subTest(filter_index=index):
                self.reject(lambda receipt: receipt["observations"][0]["calls"][0]["filters"][index].update(condition="equal"))
        for index in range(10):
            for field in ["nativeCandidatesBefore", "nativeCandidatesAfter"]:
                with self.subTest(stage=index, field=field):
                    self.reject(lambda receipt: receipt["observations"][index].update({field: ["foreign"]}))

    def test_candidate_and_target_caps_cannot_be_conflated(self):
        self.reject(lambda receipt: receipt["observations"][1].update(targetLimit=5))
        self.reject(lambda receipt: receipt["observations"][2].update(candidateLimit=3))
        self.reject(lambda receipt: receipt["observations"][1]["rows"].pop())
        self.reject(lambda receipt: receipt["observations"][2]["calls"].pop())
        for index in [1, 2]:
            self.reject(lambda receipt: receipt["observations"][index].update(limitations=["indexFreshnessUnverified"]))

    def test_returned_exact_targets_titles_authority_order_and_type_are_verified(self):
        for field, value in [("id", "wrong"), ("objectID", "object-9"), ("blockID", "foreign-block"),
                             ("title", "different"), ("typeID", "wrong"), ("sourceReference", "Genesis 5:6"),
                             ("spaceID", "space-other"), ("canUnlink", False), ("kind", "note"), ("updatedAt", 1)]:
            with self.subTest(field=field):
                self.reject(lambda receipt: receipt["observations"][0]["rows"][-1].update({field: value}))
        self.reject(lambda receipt: receipt["observations"][0]["rows"].reverse())
        self.reject(lambda receipt: next(row for row in receipt["observations"][0]["rows"] if row.get("blockID")).update(canUnlink=True))

    def test_native_mutation_reuse_and_stale_disclosure_must_be_real(self):
        self.reject(lambda receipt: receipt["nativeMutationCounts"].update(ObjectSetDetails=0))
        self.reject(lambda receipt: receipt["observations"][4].update(serviceID="new-service"))
        self.reject(lambda receipt: receipt["observations"][9].update(limitations=["indexFreshnessUnverified"]))
        self.reject(lambda receipt: receipt["observations"][9]["readbacks"][4].update(nodes=receipt["objects"][4]["original"]["nodes"]))
        self.reject(lambda receipt: receipt["observations"][5]["readbacks"][2].update(isArchived=False))

    def test_native_readback_canonical_digest_graph_and_unknown_fields_are_checked(self):
        self.reject(lambda receipt: receipt["observations"][0]["readbacks"][0].update(canonicalSHA256="0" * 64))
        self.reject(lambda receipt: receipt["observations"][0]["readbacks"][0].update(relatedVersion=0))
        self.reject(lambda receipt: receipt["observations"][0]["readbacks"][0].update(projectionReady=False))
        self.reject(lambda receipt: receipt["objects"][4]["original"]["nodes"][0].update(childIDs=["missing"]))
        def drop_unknown(receipt):
            row = receipt["observations"][7]["readbacks"][0]
            root = json.loads(row["canonicalRaw"])
            del root["unknownRoot"]
            row.update(canonicalRaw=json.dumps(root), canonicalSHA256=evidence.sha(json.dumps(root)))
        self.reject(drop_unknown)

    def test_no_stage_or_readback_can_be_omitted(self):
        self.reject(lambda receipt: receipt["observations"].pop())
        self.reject(lambda receipt: receipt["observations"][3]["readbacks"].clear())
        self.reject(lambda receipt: receipt["observations"][4].update(coverage="spaceWide"))


if __name__ == "__main__":
    unittest.main()
