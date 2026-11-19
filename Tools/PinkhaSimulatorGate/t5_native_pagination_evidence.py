"""Validate source-bound native pagination receipts; fixture controls are not Apple acceptance."""
import hashlib
import json
import math
import re

from run_t5_apple_pair import require, runtime_version

PROTOCOL = "pinkha-t5-native-pagination-v1"
METHOD = "TorahT5NativePaginationTests/nativePaginationCurrentSpaceAndMutationAcceptance"
SOURCE = ("sefaria", "Genesis 5:5")
INDEX = "torah1|3:ref|7:sefaria|11:Genesis 5:5"
ROLES = ["page_a", "page_b", "note", "writing", "block", "quote", "multi",
         "different_verse", "different_provider", "foreign"]
STAGES = ["baseline", "candidate_cap", "target_cap", "other_space", "return_to_original",
          "note_archive", "note_unarchive", "page_unlink", "page_restore", "block_removed"]
KEYS = {"id", "spaceId", "_pinkhaTorahReady", "_pinkhaTorahState",
        "_pinkhaTorahProjectionVersion", "_pinkhaTorahRelatedVersion"}


def sha(value):
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value) and len(value) <= 4096


def target_id(space, object_id, block_id):
    return "|".join(str(len(value.encode("utf8"))) + ":" + value for value in [space, object_id, block_id or ""])


def graph_nodes(readback):
    nodes = readback.get("nodes")
    require(isinstance(nodes, list) and 0 < len(nodes) <= 10000, "Bounded original native graph required")
    graph = {}
    for node in nodes:
        require(isinstance(node, dict) and set(node) == {"id", "childIDs"}
                and nonempty(node["id"]) and node["id"] not in graph
                and isinstance(node["childIDs"], list)
                and all(nonempty(child) for child in node["childIDs"]), "Invalid or duplicate native graph node")
        graph[node["id"]] = node["childIDs"]
    pending, reachable = [readback["objectID"]], set()
    while pending:
        value = pending.pop()
        if value in reachable:
            continue
        require(value in graph, "Unresolved child in native ObjectShow graph")
        reachable.add(value)
        pending.extend(graph[value])
    return graph, reachable


def validate_readback(value, obj):
    require(isinstance(value, dict) and value.get("objectID") == obj["objectID"]
            and value.get("rootID") == obj["objectID"] and value.get("spaceID") == obj["spaceID"],
            "ObjectShow source/Space/root identity differs")
    require(nonempty(value.get("title")) and nonempty(value.get("typeID")), "Actual title and native type required")
    for field in ["isArchived", "isDeleted", "isReadonly", "detailsRestricted", "projectionReady"]:
        require(type(value.get(field)) is bool, "Native readback boolean missing")
    require(value["isDeleted"] is False and value["isReadonly"] is False and value["detailsRestricted"] is False,
            "Fixture authority or deletion state differs")
    require(value["projectionReady"] is True and value.get("projectionState") == "READY"
            and type(value.get("projectionVersion")) is int and value["projectionVersion"] == 1
            and type(value.get("relatedVersion")) is int and value["relatedVersion"] == 1,
            "Actual live projection is not ready")
    date = value.get("updatedAt")
    require(type(date) in [int, float] and math.isfinite(date) and date > 0, "Actual native modification time missing")
    raw = value.get("canonicalRaw")
    require(isinstance(raw, str) and len(raw.encode("utf8")) <= 256 * 1024
            and sha(raw) == value.get("canonicalSHA256"), "Canonical readback bytes or digest differ")
    root = json.loads(raw)
    require(isinstance(root, dict) and root.get("version") == 2 and isinstance(root.get("records"), list),
            "Original canonical v2 records required")
    graph, reachable = graph_nodes(value)
    return root, graph, reachable


def validate_fixture(receipt):
    objects = receipt.get("objects", [])
    require(isinstance(objects, list) and [obj.get("role") for obj in objects] == ROLES,
            "Exactly ten independent native fixture objects required")
    ids, associations, block_ids = set(), set(), set()
    for obj in objects:
        role = obj["role"]
        expected_space = receipt["foreignSpaceID"] if role == "foreign" else receipt["spaceID"]
        require(nonempty(obj.get("objectID")) and obj["objectID"] not in ids and obj.get("spaceID") == expected_space
                and nonempty(obj.get("canonicalKey")), "Fixture identity, Space or canonical property differs")
        ids.add(obj["objectID"])
        root, _, reachable = validate_readback(obj.get("original"), obj)
        require(obj["original"]["isArchived"] is False, "Fixture is already archived")
        targets = obj.get("targets", [])
        expected_roles = ["document", "block", "quote"] if role == "multi" else [role if role in ["block", "quote"] else "document"]
        require([target.get("role") for target in targets] == expected_roles and len(root["records"]) == len(targets),
                "Independent fixture target/record inventory differs")
        provider = "fixture-other-provider" if role == "different_provider" else SOURCE[0]
        reference = "Genesis 5:6" if role == "different_verse" else SOURCE[1]
        for target in targets:
            identifier, block = target.get("associationID"), target.get("blockID")
            require(target.get("objectID") == obj["objectID"] and nonempty(identifier) and identifier not in associations,
                    "Fixture association identity reused")
            associations.add(identifier)
            if target["role"] == "document":
                require(block is None, "Document target contains a block identity")
            else:
                require(nonempty(block) and block != obj["objectID"] and block not in block_ids and block in reachable,
                        "Original exact block target is not independently reachable")
                block_ids.add(block)
            matches = [record for record in root["records"] if record.get("item", {}).get("id") == identifier]
            require(len(matches) == 1, "Canonical association absent or duplicated")
            record, item = matches[0], matches[0]["item"]
            require(record.get("spaceId") == expected_space and record.get("objectId") == obj["objectID"]
                    and record.get("blockId") == block and item.get("kind") == "ref"
                    and item.get("role") == ("sourceQuote" if target["role"] == "quote" else "context")
                    and item.get("providerID") == provider and item.get("canonicalKey") == reference
                    and item.get("externalID") == reference, "Canonical role/source/Space/target binding differs")
    require(len(ids) == 10 and len(associations) == 12 and len(block_ids) == 4, "Native fixture cardinality differs")
    by_role = {obj["role"]: obj for obj in objects}
    require(len({by_role[role]["original"]["typeID"] for role in ["page_a", "note", "writing"]}) == 3,
            "Page, Note and Writing native types must be distinct")
    return by_role


def validate_calls(calls, space, native_ids, candidate_limit):
    require(isinstance(calls, list) and 0 < len(calls) <= 30, "Actual native search calls missing")
    seen, consumed, position = [], [], 0
    while len(seen) < candidate_limit:
        require(position < len(calls), "A native pagination call is missing")
        call = calls[position]
        position += 1
        limit = min(2, candidate_limit - len(seen))
        expected = native_ids[len(seen):len(seen) + limit]
        require(call.get("spaceID") == space and type(call.get("limit")) is int and call["limit"] == limit
                and type(call.get("offset")) is int and call["offset"] == 0 and call.get("fullText") == "",
                "Actual request Space/page size/offset/full text differs")
        require(isinstance(call.get("keys"), list) and len(call["keys"]) == len(KEYS) and set(call["keys"]) == KEYS,
                "Native candidate projection keys differ")
        require(call.get("sorts") == [dict(key="id", direction="asc", noCollate=True)]
                and type(call["sorts"][0]["noCollate"]) is bool, "Stable native ID pagination sort required")
        filters = call.get("filters")
        require(isinstance(filters, list) and len(filters) == (9 if seen else 8), "Exact native filter inventory required")
        decoded = []
        for item in filters:
            require(isinstance(item, dict) and set(item) == {"key", "condition", "valueJSON"}, "Original filter shape differs")
            decoded.append((item["key"], item["condition"], json.loads(item["valueJSON"])))
        expected_filters = [(key, "notEqual", True) for key in ["isHidden", "isHiddenDiscovery", "isDeleted", "isArchived"]]
        expected_filters.extend([("uniqueKey", "notEqual", "ot-objectType"), ("type.uniqueKey", "notEqual", "ot-template"),
                                 ("spaceId", "equal", space), ("_pinkhaTorahRelatedSources", "in", [INDEX])])
        if seen:
            expected_filters.append(("id", "notIn", sorted(seen)))
        require(decoded == expected_filters, "Exact source/Space/visibility/type/exclusion predicates differ")
        require(call.get("objectIDs") == expected and call.get("resultSpaceIDs") == [space] * len(expected),
                "Native page skipped, duplicated, reordered or leaked an object")
        consumed.extend(expected)
        seen.extend(expected)
        if len(expected) < limit:
            break
    require(position == len(calls), "Unexpected extra search call in the accepted query")
    return consumed


def validate_observations(receipt, fixtures):
    observations = receipt.get("observations")
    require(isinstance(observations, list) and [row.get("name") for row in observations] == STAGES,
            "Exactly ten ordered native observations required")
    originals = [fixtures[role] for role in ROLES[:7]]
    ids = sorted(obj["objectID"] for obj in originals)
    service_ids = [row.get("serviceID") for row in observations]
    require(all(nonempty(value) for value in service_ids) and len(set(service_ids[:3])) == 3
            and all(value == service_ids[0] for value in service_ids[3:]),
            "One retained production service plus two independent limit variants required")
    total_calls = 0
    for observation in observations:
        name = observation["name"]
        foreign = name == "other_space"
        space = receipt["foreignSpaceID"] if foreign else receipt["spaceID"]
        selected = [fixtures["foreign"]] if foreign else originals
        excluded_role = "note" if name == "note_archive" else "page_a" if name == "page_unlink" else None
        native_ids = [fixtures["foreign"]["objectID"]] if foreign else [value for value in ids if not excluded_role or value != fixtures[excluded_role]["objectID"]]
        candidate_limit, target_limit = (5, 50) if name == "candidate_cap" else (50, 3) if name == "target_cap" else (50, 50)
        require(observation.get("activeSpaceID") == space and observation.get("requestedSpaceID") == space
                and observation.get("pageSize") == 2 and observation.get("candidateLimit") == candidate_limit
                and observation.get("targetLimit") == target_limit, "Observed current Space or independent query caps differ")
        require(observation.get("nativeCandidatesBefore") == native_ids and observation.get("nativeCandidatesAfter") == native_ids,
                "Independent raw native membership before and after query differs")
        consumed = validate_calls(observation.get("calls"), space, native_ids, candidate_limit)
        total_calls += len(observation["calls"])
        if name in ["baseline", "target_cap", "return_to_original"]:
            require(len(observation["calls"]) > 2, "Actual multi-page execution was not demonstrated")
        readbacks = observation.get("readbacks", [])
        require(isinstance(readbacks, list) and len(readbacks) == len(selected)
                and {row.get("objectID") for row in readbacks} == {obj["objectID"] for obj in selected},
                "Independent post-query native readbacks missing")
        live = {row["objectID"]: row for row in readbacks}
        expected_rows = []
        for obj in selected:
            current = live[obj["objectID"]]
            root, graph, reachable = validate_readback(current, obj)
            original = obj["original"]
            require(current["title"] == original["title"] and current["typeID"] == original["typeID"],
                    "Native mutation changed unrelated document metadata")
            require(current["isArchived"] is (name == "note_archive" and obj["role"] == "note"), "Native archive mutation/readback differs")
            if name == "page_unlink" and obj["role"] == "page_a":
                expected_canonical = json.loads(original["canonicalRaw"])
                expected_canonical["records"] = []
                require(root == expected_canonical, "Unlink changed unknown canonical fields or the wrong source")
            else:
                require(current["canonicalRaw"] == original["canonicalRaw"], "Native canonical bytes changed outside the exact mutation")
            original_graph, _ = graph_nodes(original)
            removed = name == "block_removed" and obj["role"] == "block"
            if removed:
                require(obj["targets"][0]["blockID"] not in reachable, "Deleted native target is still reachable")
            else:
                require(graph == original_graph, "Unrelated native block graph changed")
            if obj["objectID"] not in consumed or obj["role"] == excluded_role:
                continue
            for target in obj["targets"]:
                block = target.get("blockID")
                if removed:
                    continue
                require(block is None or block in reachable, "Expected target disappeared from native graph")
                expected_rows.append(dict(id=target_id(space, obj["objectID"], block), spaceID=space, objectID=obj["objectID"],
                    blockID=block, title=current["title"], typeID=current["typeID"], sourceReference=SOURCE[1],
                    canUnlink=target["role"] == "document", kind="note" if obj["role"] == "note" else "document",
                    updatedAt=current["updatedAt"]))
        expected_rows.sort(key=lambda row: (-row["updatedAt"], row["id"]))
        expected_rows = expected_rows[:target_limit]
        rows = observation.get("rows")
        require(isinstance(rows, list) and len(rows) == len(expected_rows), "Production result cardinality differs from independent native targets")
        for row, expected in zip(rows, expected_rows):
            require(isinstance(row, dict) and type(row.get("canUnlink")) is bool
                    and {key: row.get(key) for key in expected} == expected,
                    "Production row identity/order/metadata/authority differs from native evidence")
        limitations = ["indexFreshnessUnverified"]
        if name in ["candidate_cap", "target_cap"]:
            limitations.append("resultLimitReached")
        if name == "block_removed":
            limitations.append("staleCandidates")
        require(observation.get("coverage") == "indexedTargetsOnly" and observation.get("limitations") == sorted(limitations),
                "Exact incomplete/truncated/stale disclosure missing")
    return total_calls


def validate_receipt(receipt, *, source, run_id, token, root_sha):
    require(isinstance(receipt, dict) and receipt.get("protocolVersion") == PROTOCOL
            and receipt.get("status") == "PASS_NATIVE_OBSERVATIONS", "Native pagination receipt is incomplete")
    require(re.fullmatch("[a-f0-9]{40}", source or "") and re.fullmatch("[a-f0-9]{32}", token or "")
            and run_id.isdigit() and re.fullmatch("[a-f0-9]{64}", root_sha or ""), "Controller source/run/token/root identity missing")
    require(receipt.get("appSourceSHA") == source and receipt.get("runID") == run_id and receipt.get("token") == token
            and receipt.get("rootPathSHA256") == root_sha and receipt.get("runtimeVersion") == runtime_version("new")
            and type(receipt.get("processID")) is int and receipt["processID"] > 0, "Native receipt provenance differs")
    require(all(nonempty(receipt.get(field)) for field in ["accountID", "spaceID", "foreignSpaceID"])
            and receipt["spaceID"] != receipt["foreignSpaceID"], "Distinct account/Space identities required")
    require((receipt.get("providerID"), receipt.get("canonicalReference")) == SOURCE and receipt.get("indexValue") == INDEX,
            "Exact canonical provider/reference/index identity differs")
    require(all(receipt.get(field) is True for field in ["accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"]),
            "Real native account stop/shutdown not confirmed")
    require(receipt.get("productLookupFlag") == "OFF" and receipt.get("wholeIndexCompleteness") == "NOT_PROVEN"
            and receipt.get("aclRevocation") == "NOT_PROVEN", "Acceptance scope widened beyond actual evidence")
    require(receipt.get("nativeMutationCounts") == {"SetActiveSpace": 2, "ObjectListSetIsArchived": 2,
            "ObjectSetDetails": 2, "BlockListDelete": 1}
            and all(type(value) is int for value in receipt["nativeMutationCounts"].values()), "Actual native mutation sequence differs")
    fixtures = validate_fixture(receipt)
    calls = validate_observations(receipt, fixtures)
    return dict(native_test_methods=1, observations=10, fixture_objects=10, current_space_objects=7,
                current_space_targets=9, actual_search_calls=calls, independent_limit_cases=2, space_switches=2,
                native_data_mutations=5, whole_index_completeness="NOT_PROVEN", acl_revocation="NOT_PROVEN",
                product_lookup_flag="OFF")
