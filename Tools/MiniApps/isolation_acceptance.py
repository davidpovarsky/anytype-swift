"""Independently bind the real UI isolation observations to original native receipts."""
import hashlib
import json
from pathlib import Path
import uuid


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, limit=8 * 1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.stat().st_size <= limit, "Original bounded evidence file required")
    return path.read_bytes()


def identifier(value):
    result = str(uuid.UUID(value))
    require(result == value, "Canonical original request UUID required")
    return result


def verify(source_data, shared, fixture, source_bundle, evidence, report_name):
    source_data, shared, evidence = map(Path, (source_data, shared, evidence))
    require(Path(report_name).name == report_name, "Unsafe owned report name")
    raw = read(shared / report_name, 64 * 1024)
    report = json.loads(raw)
    require(report["status"] == "REAL_ENGINE_ACCOUNT_MINIAPPS_UI_PASS"
            and report["sourceSHA"] == fixture["sourceSHA"] and report["runID"] == fixture["runID"],
            "UI isolation source/execution differs")
    for name in ("foreignAccountRejectedBeforeAndAfterColdReopen", "foreignNativeBlocksAndVersionUnchanged"):
        require(report[name] is True, "Actual isolation UI assertion is missing: " + name)
    require(report["replayedCallbacks"] == report["sourceColdReopens"] == 2
            and report["syntheticRequests"] == report["syntheticResults"] == report["directNativeTestMutations"] == 0,
            "Actual isolation journey scope differs")
    heart_id, any_id = map(identifier, (report["heartRequestID"], report["anyRequestID"]))
    probes = [identifier(value) for value in report["foreignReadRequestIDs"]]
    require(len(probes) == 2 and len(set([heart_id, any_id, *probes])) == 4,
            "Four distinct genuine requests are required")
    records = {}
    for request_id in (heart_id, any_id, *probes):
        value = json.loads(read(shared / "requests" / (request_id + ".json")))
        require(identifier(value["request"]["id"].lower()) == request_id
                and value["request"]["source"]["appID"] == source_bundle
                and value["acknowledged"] is True
                and identifier(value["result"]["requestID"].lower()) == request_id,
                "Original request/result/final ACK ownership differs")
        records[request_id] = value
    heart, original, before, after = (records[key] for key in (heart_id, any_id, *probes))
    for row, engine, account, document, text in (
        (heart, "heart", fixture["accountID"], fixture["objectID"], report["heartReturnedText"]),
        (original, "any", report["originalAnyAccountID"], report["anyDocumentID"], report["anyReturnedText"]),
    ):
        request, result = row["request"], row["result"]
        require(request["appID"] == "nativeapp.textstudio" and request["operation"] == "insert"
                and request["source"]["metadata"]["pinkha.engine"] == engine
                and request["source"]["metadata"]["anytype.accountID"] == account
                and request["source"]["documentID"] == document
                and result["status"] == "success" and result["operation"] == "insert"
                and len(result["items"]) == 1 and result["items"][0]["kind"] == "text"
                and result["items"][0]["text"] == text, "Actual native insertion result differs")
    require(heart["request"]["source"]["metadata"]["anytype.spaceID"] == fixture["spaceID"],
            "Heart return selected a foreign Space")
    require(report["originalAnyAccountID"] != report["foreignAnyAccountID"]
            and report["foreignAnyAccountID"] != fixture["accountID"], "Independent native accounts required")
    require(original["request"]["source"]["documentText"] == report["originalAnyText"],
            "Original account capture differs")
    for row in (before, after):
        request, result = row["request"], row["result"]
        require(request["appID"] == "org.itorah.miniapps.fileworkshop"
                and request["source"]["metadata"]["pinkha.engine"] == "any"
                and request["source"]["metadata"]["anytype.accountID"] == report["foreignAnyAccountID"]
                and request["source"]["documentID"] == report["foreignDocumentID"]
                and request["source"]["documentText"] == report["foreignAnyText"]
                and result["status"] == "cancelled" and result["items"] == [],
                "Foreign-account probe is not an actual original read/cancel")
    for key in ("anytype.accountID", "anytype.spaceID", "anytype.blocks", "anytype.nativeVersion"):
        require(before["request"]["source"]["metadata"][key] == after["request"]["source"]["metadata"][key],
                "The foreign native document was changed: " + key)
    b_blocks = json.loads(before["request"]["source"]["metadata"]["anytype.blocks"])
    a_blocks = json.loads(original["request"]["source"]["metadata"]["anytype.blocks"])
    require(len(b_blocks) == len(a_blocks) == 1
            and report["foreignAnyBlock"] == "any-native-block-" + b_blocks[0]["id"]
            and report["originalAnyBlock"] == "any-native-block-" + a_blocks[0]["id"],
            "Actual native original block identities differ")

    observations = report["foreignPendingObservations"]
    require(len(observations) == 2 and observations[1]["observedAt"] > observations[0]["observedAt"],
            "Warm/cold original pending observations required")
    for observation in observations:
        observed_bytes = observation["recordJSON"].encode("utf-8")
        require(digest(observed_bytes) == observation["recordSHA256"]
                and observation["selectedAccountID"] == report["foreignAnyAccountID"],
                "Foreign-account original observation bytes differ")
        pending = json.loads(observed_bytes)
        require(pending["request"] == original["request"] and pending["result"] == original["result"]
                and pending["acknowledged"] is False,
                "A foreign account acknowledged or replaced the actual pending result")

    support = source_data / "Library/Application Support"
    heart_paths = list((support / "MiniAppsReceipts").glob("*/" + heart_id + ".json"))
    any_paths = list((support / "MiniAppsReceipts/any").glob("*/" + any_id + ".json"))
    require(len(heart_paths) == len(any_paths) == 1, "One actual native receipt for each successful return required")
    heart_journal = json.loads(read(heart_paths[0]))
    any_journal = json.loads(read(any_paths[0]))
    plan = any_journal["plan"]
    for journal, request_id, text in ((heart_journal, heart_id, report["heartReturnedText"]),
                                     (plan, any_id, report["anyReturnedText"])):
        require(journal["completed"] is True and identifier(journal["requestID"].lower()) == request_id
                and len(journal["insertedBlocks"]) == 1
                and [value.get("text") for value in journal["additions"]] == [text],
                "Native result did not complete exactly one original insertion")
    scope = ["any", report["originalAnyAccountID"],
             original["request"]["source"]["metadata"]["anytype.spaceID"], report["anyDocumentID"]]
    expected_scope = digest(json.dumps(scope, ensure_ascii=False, separators=(",", ":")).replace("/", "\\/").encode())
    require(any_paths[0].parent.name == expected_scope and any_journal["nativeStoreID"],
            "Any native receipt belongs to a different account/Space/document/store")
    inserted = list(plan["insertedBlocks"].values())[0]
    require(set(report["savedAnyBlocks"]) == {report["originalAnyBlock"], "any-native-block-" + inserted},
            "The committed Any native ID differs from warm/replay/cold UI observations")
    for request_id in probes:
        require(not list((support / "MiniAppsReceipts/any").glob("*/" + request_id + ".json")),
                "A cancelled read probe unexpectedly created a native mutation journal")

    native_raw = read(support / "miniapps-engine-account-native-readback.json")
    native = json.loads(native_raw)
    require(native["status"] == "REAL_ENGINE_ACCOUNT_MINIAPPS_HEART_NATIVE_PASS"
            and native["sourceSHA"] == fixture["sourceSHA"] and native["runID"] == fixture["runID"]
            and native["uiReportSHA256"] == digest(raw)
            and native["heartRequestID"] == heart_id and native["anyRequestID"] == any_id
            and native["accountID"] == fixture["accountID"] and native["spaceID"] == fixture["spaceID"]
            and native["objectID"] == fixture["objectID"]
            and native["returnedCount"] == native["originalCount"] == 1
            and native["foreignContentAbsent"] is True and native["nativeReadOnly"] is True
            and set(heart_journal["insertedBlocks"].values()) == {native["returnedBlockID"]},
            "Actual Heart native readback differs from the UI and original mutation journal")
    proof = {"status": "REAL_ENGINE_ACCOUNT_MINIAPPS_ISOLATION_PASS", "ui": report, "native": native,
             "originalBridgeRecords": records, "heartJournal": heart_journal, "anyJournal": any_journal,
             "originalUIReportSHA256": digest(raw), "originalNativeReportSHA256": digest(native_raw),
             "physicalDevice": "NOT_RUN", "nativeMutationAndACKAtomic": False}
    path = evidence / "engine-account-isolation.json"
    with path.open("x") as stream:
        json.dump(proof, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return proof
