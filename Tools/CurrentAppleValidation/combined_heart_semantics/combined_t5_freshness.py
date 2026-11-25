"""Original quote freshness predicates with the exact combined profile binding."""
import copy
import json
import re
from t5_remaining_freshness import pair, PROTOCOL, NATIVE_PASS, STAGES, COUNTS
from combined_t5_pending import VERSION, RUNTIME_PROFILE


def validate_receipt(value, *, source, run_id, run_attempt, token, root_sha, runtime):
    expected = dict(protocolVersion=PROTOCOL, status=NATIVE_PASS, appSourceSHA=source,
                    runID=run_id, runAttempt=run_attempt, token=token, rootPathSHA256=root_sha,
                    runtimeProfile=RUNTIME_PROFILE, runtimeVersion=runtime,
                    actualCapability="verified", serverConfiguration="localOnly",
                    wholeIndexCompleteness="NOT_PROVEN", forcedNetworkOutage="NOT_RUN", productLookupFlag="OFF")
    pair.require(re.fullmatch(r"[a-f0-9]{40}", source or "") and run_id.isdigit()
                 and run_attempt.isdigit() and int(run_attempt) > 0
                 and re.fullmatch(r"[a-f0-9]{32}", token or "") and pair.is_digest(root_sha)
                 and all(value.get(key) == item for key, item in expected.items()),
                 "Native quote freshness source/run/account/runtime identity differs")
    pair.require(type(value.get("processID")) is int and value["processID"] > 0
                 and all(value.get(key) is True for key in ("accountStopCompleted", "accountNotRunningConfirmed", "appShutdownCompleted"))
                 and value.get("mixedVersionAccepted") is False
                 and value.get("runtimePairPhasesExecuted") == []
                 and type(value.get("historicalPaginationInvocations")) is int
                 and value["historicalPaginationInvocations"] == 0,
                 "Native quote fixture lifecycle or retained acceptance scope differs")
    ledger = value.get("ledger", {})
    pair.require(ledger.get("completedPhases") == []
                 and all(ledger.get(key) == value.get(key) for key in
                         ("token", "appSourceSHA", "rootPathSHA256", "accountID", "spaceID"))
                 and ledger.get("rootRelativePath") == pair.ROOT_RELATIVE_PATH
                 and all(isinstance(ledger.get(key), str) and ledger[key] for key in
                         ("accountID", "spaceID", "manifestID", "canonicalKey"))
                 and pair.is_digest(ledger.get("manifestSHA256")),
                 "Fresh native ledger owner or original fixture identity differs")
    documents = ledger.get("documents", [])
    pair.require(len(documents) == 3 and len({item.get("objectID") for item in documents}) == 3
                 and documents[0].get("typeKey") == "ot-page" and documents[1].get("typeKey") == "ot-note"
                 and documents[2].get("typeKey") not in (None, "", "ot-page", "ot-note")
                 and documents[0].get("blockID") is None and documents[0].get("blockText") is None,
                 "Actual distinct Page/Note/custom-sourceQuote fixture is required")
    ids = [item["objectID"] for item in documents]
    blocks = [item.get("blockID") for item in documents[1:]]
    pair.require(all(isinstance(item, str) and item for item in ids + blocks) and len(set(blocks)) == 2
                 and all(isinstance(item.get("initialName"), str) and pair.is_digest(item.get("canonicalSHA256"))
                         and pair.is_digest(item.get("publicSHA256")) for item in documents)
                 and all(isinstance(item.get("blockText"), str) and item["blockText"] for item in documents[1:]),
                 "Native fixture details or original quote text missing")
    originals = value.get("originalCanonical", {})
    pair.require(set(originals) == set(ids), "All original canonical payloads are required")
    parsed = []
    for index, document in enumerate(documents):
        raw = originals[document["objectID"]]
        pair.require(isinstance(raw, str) and pair.sha_bytes(raw.encode()) == document["canonicalSHA256"],
                     "Original canonical bytes were substituted")
        canonical = json.loads(raw)
        records = canonical.get("records", [])
        pair.require(canonical.get("version") == 2 and len(records) == 1, "One canonical v2 record required")
        record = records[0]
        item = record.get("item", {})
        pair.require(record.get("spaceId") == ledger["spaceID"] and record.get("objectId") == document["objectID"]
                     and record.get("blockId") == document.get("blockID")
                     and item.get("kind") == "ref" and item.get("providerID") == "sefaria"
                     and item.get("canonicalKey") == item.get("externalID") == "Genesis 3:3"
                     and item.get("role") == ("sourceQuote" if index == 2 else "context"),
                     "Canonical quote/context source or native target binding differs")
        parsed.append(canonical)
    moved = copy.deepcopy(parsed[2])
    moved["records"][0]["item"].update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
    pair.require(isinstance(value.get("serviceID"), str) and value["serviceID"]
                 and type(value.get("serviceQueryCount")) is int and value["serviceQueryCount"] == 6
                 and value.get("nativeMutationCounts") == {"ObjectSetDetails": 2, "BlockListDelete": 1}
                 and all(type(count) is int for count in value["nativeMutationCounts"].values()),
                 "Exactly one retained host service, six queries and three native mutations required")
    rows = value.get("observations", [])
    pair.require([row.get("name") for row in rows] == [row[0] for row in STAGES],
                 "Six ordered original native observations required")
    for ordinal, (row, (_, reference, native, host, is_moved, reachable)) in enumerate(zip(rows, STAGES), 1):
        pair.require(row.get("spaceID") == ledger["spaceID"] and row.get("sourceReference") == reference
                     and row.get("serviceID") == value["serviceID"]
                     and type(row.get("serviceQueryOrdinal")) is int and row["serviceQueryOrdinal"] == ordinal
                     and row.get("coverage") == "indexedTargetsOnly"
                     and row.get("limitations") == (["indexFreshnessUnverified"] if reachable else
                                                     ["indexFreshnessUnverified", "staleCandidates"]),
                     "Same-service observation source, ordering or bounded coverage differs")
        expected_native = sorted(ids[index] for index in native)
        pair.require(row.get("nativeCandidatesBefore") == row.get("nativeCandidatesAfter") == expected_native,
                     "Actual native membership before and after host lookup differs")
        targets = row.get("targets", [])
        expected_targets = [dict(objectID=ids[index], blockID=documents[index].get("blockID"),
                                 canUnlink=documents[index].get("blockID") is None) for index in host]
        pair.require(all(type(item.get("canUnlink")) is bool for item in targets)
                     and sorted([dict(objectID=item.get("objectID"), blockID=item.get("blockID"),
                                      canUnlink=item.get("canUnlink")) for item in targets], key=pair.target_key)
                     == sorted(expected_targets, key=pair.target_key),
                     "Live host targets, quote exclusion or honest empty result differ")
        readbacks = row.get("readbacks", [])
        pair.require([item.get("objectID") for item in readbacks] == ids, "Complete original native readback order required")
        for index, readback in enumerate(readbacks):
            document = documents[index]
            raw = readback.get("canonicalRaw")
            pair.require(readback.get("spaceID") == ledger["spaceID"]
                         and readback.get("title") == document["initialName"]
                         and readback.get("typeKey") == document["typeKey"]
                         and isinstance(raw, str) and readback.get("canonicalSHA256") == pair.sha_bytes(raw.encode()),
                         "Quote mutation changed unrelated native document details")
            if index == 2 and is_moved:
                pair.require(json.loads(raw) == moved, "Quote move changed canonical metadata or unknown fields")
            else:
                pair.require(raw == originals[document["objectID"]], "Unrelated or restored canonical bytes differ")
        pair.validate_freshness_graph(row.get("quoteGraph"), documents[2], ledger["spaceID"], reachable)
        expected_text = pair.sha_bytes(documents[2]["blockText"].encode()) if reachable else None
        pair.require(row.get("quoteBlockTextSHA256") == expected_text, "Original live quote body was changed or invented")
    return dict(COUNTS)


def validate_combined_receipt(value, **binding):
    pair.require(binding.get("runtime") == VERSION,
                 "Exact actual combined quote-freshness runtime required")
    return validate_receipt(value, **binding)
