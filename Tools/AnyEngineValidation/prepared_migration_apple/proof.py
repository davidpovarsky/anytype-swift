"""Independently admit one actual XCTest and its bounded native observations."""
from __future__ import annotations

import hashlib
import re
from uuid import UUID

import contract

NAME = "הגירה מקומית — e\u0301"
BODY = "שָׁלוֹם — עברית\nsecond e\u0301 👩🏽‍💻\n"
NAME_SHA = hashlib.sha256(NAME.encode()).hexdigest()
BODY_SHA = hashlib.sha256(BODY.encode()).hexdigest()
PLAN_SHA = hashlib.sha256((NAME + "\n" + BODY).encode()).hexdigest()
LIMITS = {
    "restartKind": "orderly native SDK/store reopen within one XCTest OS process",
    "osProcessCrash": "NOT_RUN", "lostHTTPAcknowledgement": "NOT_INJECTED",
    "networkSynchronization": "NOT_RUN", "nativeACLMutation": "NOT_RUN",
    "inlineFiles": "NOT_RUN_NO_HTTP_ROUTE", "fullSpaceMigration": "NOT_PROVEN",
}
PHASES = ("root-prepared", "root-committed", "bootstrap-prepared", "object-complete", "block-prepared",
          "block-complete", "object-reconciled-after-reopen", "block-reconciled-after-reopen", "revoked-owner-refused")
ROW_KEYS = {"phase", "runtimeVersion", "engineGeneration", "ownerGeneration", "contract", "intentId", "fingerprint",
            "specSHA256", "stage", "outcome", "objectId", "changeId", "recordIds", "accountId", "spaceId", "storeId",
            "planId", "planSHA256", "readback"}


def text(value, maximum=1024):
    return isinstance(value, str) and 0 < len(value.encode()) <= maximum and "\0" not in value


def uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)).lower() == value.lower()
    except (ValueError, AttributeError):
        return False


def exact_execution(summary, tree, udid, test_cases):
    counts = {name: summary.get(name) for name in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    contract.require(all(type(v) is int for v in counts.values())
                     and counts == dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0),
                     "Exactly one actual passed XCTest and zero failures/skips required")
    destinations = summary.get("devicesAndConfigurations")
    contract.require(isinstance(destinations, list) and len(destinations) == 1, "One actual simulator result required")
    device = destinations[0].get("device", {})
    contract.require(uuid(udid) and str(device.get("deviceId", "")).lower() == udid.lower()
                     and str(device.get("osVersion", "")).split(".")[0] == "27"
                     and device.get("architecture") == "arm64" and text(device.get("osBuildNumber")),
                     "Actual test destination is not the owned iOS27 ARM64 device")
    cases = test_cases(tree)
    contract.require(len(cases) == 1 and list(cases.values()) == ["Passed"]
                     and re.search(r"(?:^|/)" + re.escape(contract.METHOD) + r"(?:\(\))?$", next(iter(cases))),
                     "Wrong, duplicated or nonpassing actual XCTest terminal")
    return dict(counts=counts, actual_cases=cases, selected_method=contract.SELECTOR, device=device)


def history_readback(row, expected_hash, block):
    readback = row["readback"]
    keys = {"dataset", "recordId", "nativeHistoryEntry"}
    keys |= ({"currentBodyUTF8SHA256", "historicalBodyUTF8SHA256", "currentRecordCount"} if block
             else {"currentNameUTF8SHA256", "historicalNameUTF8SHA256"})
    contract.require(isinstance(readback, dict) and set(readback) == keys, "Missing or unexpected native readback fields")
    dataset = "editor_blocks" if block else "objects"
    record = row["recordIds"][0]
    hash_keys = ("currentBodyUTF8SHA256", "historicalBodyUTF8SHA256") if block else ("currentNameUTF8SHA256", "historicalNameUTF8SHA256")
    contract.require(readback["dataset"] == dataset and readback["recordId"] == record
                     and all(readback[k] == expected_hash for k in hash_keys), "Native current/history byte hashes differ")
    if block:
        contract.require(type(readback["currentRecordCount"]) is int and readback["currentRecordCount"] == 1,
                         "Native retry must retain exactly one block")
    history = readback["nativeHistoryEntry"]
    required = {"version", "author", "timestamp", "dataset", "groupSize", "touched"}
    contract.require(isinstance(history, dict) and required <= set(history)
                     and set(history) <= required | {"traceIds", "truncated"}, "Unexpected native history envelope")
    contract.require(history["version"] == row["changeId"] and history["author"] == row["accountId"]
                     and history["dataset"] == dataset and type(history["timestamp"]) is int
                     and type(history["groupSize"]) is int and history["groupSize"] in (0, 1)
                     and history.get("truncated", False) is False, "Native signed provenance differs")
    if "traceIds" in history:
        contract.require(isinstance(history["traceIds"], list) and len(history["traceIds"]) <= 16
                         and all(text(item) for item in history["traceIds"]), "Invalid native trace metadata")
    touched = history["touched"]
    contract.require(isinstance(touched, list) and 0 < len(touched) <= 16, "Missing native touched-record proof")
    for item in touched:
        contract.require(isinstance(item, dict) and {"dataset", "recordId"} <= set(item)
                         and set(item) <= {"dataset", "recordId", "ops"}, "Unexpected touched-record fields")
        contract.require(text(item["dataset"]) and text(item["recordId"]), "Invalid touched-record identity")
        if "ops" in item:
            contract.require(isinstance(item["ops"], list) and len(item["ops"]) <= 16
                             and all(text(op, 128) for op in item["ops"]), "Invalid native operation kinds")
    contract.require(any(item["dataset"] == dataset and item["recordId"] == record for item in touched),
                     "Original native change did not touch the expected record")


def observation(value):
    keys = {"status", "completedCleanup", "processId", "runtimeGenerations", "observations", "nameUTF8SHA256", "bodyUTF8SHA256"} | set(LIMITS)
    contract.require(isinstance(value, dict) and set(value) == keys
                     and value["status"] == "OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"
                     and value["completedCleanup"] is True and type(value["processId"]) is int and value["processId"] > 0
                     and all(value[k] == v for k, v in LIMITS.items()), "Wrong observation scope or incomplete cleanup")
    contract.require(value["nameUTF8SHA256"] == NAME_SHA and value["bodyUTF8SHA256"] == BODY_SHA,
                     "Frozen exact UTF-8 inputs differ")
    generations = value["runtimeGenerations"]
    contract.require(isinstance(generations, list) and len(generations) == 6 and all(uuid(v) for v in generations)
                     and len({v.lower() for v in generations}) == 6, "Six actual distinct runtime generations required")
    rows = value["observations"]
    contract.require(isinstance(rows, list) and len(rows) == len(PHASES)
                     and all(isinstance(row, dict) for row in rows)
                     and [row.get("phase") for row in rows] == list(PHASES), "Missing, repeated or reordered native stage observations")
    expected_generations = [generations[i] for i in (0, 1, 2, 3, 3, 4, 5, 5)]
    expected_stages = ["root-prepared", "root-committed", "bootstrap-prepared", "complete", "block-prepared", "complete", "complete", "complete"]
    owners = {}
    for i, row in enumerate(rows[:-1]):
        contract.require(set(row) == ROW_KEYS and row["contract"] == "pinkha-native-prepared-migration-v1"
                         and row["stage"] == expected_stages[i]
                         and row["outcome"] == ("committed" if row["stage"] == "complete" else "prepared")
                         and row["engineGeneration"] == expected_generations[i] and uuid(row["ownerGeneration"]),
                         "Unexpected native stage, owner or outcome")
        contract.require(text(row["runtimeVersion"]) and row["runtimeVersion"].startswith("any " + contract.VERSION + " "),
                         "Wrong actual linked native runtime version")
        for key in ("intentId", "fingerprint", "specSHA256", "planId", "planSHA256"):
            contract.require(isinstance(row[key], str) and re.fullmatch(r"[0-9a-f]{64}", row[key]), "Missing native immutable digest")
        for key in ("objectId", "changeId", "accountId", "spaceId", "storeId"):
            contract.require(text(row[key]), "Missing native identity")
        contract.require(isinstance(row["recordIds"], list) and len(row["recordIds"]) <= 1
                         and all(text(v) for v in row["recordIds"]), "Unexpected native record identities")
        owners.setdefault(row["engineGeneration"], row["ownerGeneration"])
        contract.require(owners[row["engineGeneration"]] == row["ownerGeneration"], "Application owner changed inside one observed lifetime")
        for key in ("runtimeVersion", "accountId", "spaceId", "storeId", "planId", "planSHA256", "objectId"):
            contract.require(row[key] == rows[0][key], "Native scope changed during reopen/retry")
        contract.require(row["planSHA256"] == PLAN_SHA, "Reviewed logical plan digest differs")
    contract.require(len({v.lower() for v in owners.values()}) == 6, "Reopen did not create six distinct application owners")
    object_rows = [rows[i] for i in (0, 1, 2, 3, 6)]
    block_rows = [rows[i] for i in (4, 5, 7)]
    for group in (object_rows, block_rows):
        for key in ("intentId", "fingerprint", "specSHA256"):
            contract.require(len({row[key] for row in group}) == 1, "Native intent/spec binding changed across stages")
    contract.require(object_rows[0]["intentId"] != block_rows[0]["intentId"]
                     and object_rows[0]["fingerprint"] != block_rows[0]["fingerprint"], "Object/block intent classes collapsed")
    contract.require(rows[0]["changeId"] == rows[1]["changeId"]
                     and rows[2]["changeId"] == rows[3]["changeId"] == rows[6]["changeId"]
                     and rows[0]["changeId"] != rows[2]["changeId"], "Prepared signed root/bootstrap identity changed")
    contract.require(rows[0]["recordIds"] == rows[1]["recordIds"] == []
                     and all(row["recordIds"] == [row["objectId"]] for row in object_rows[2:]),
                     "Unexpected root/bootstrap record mapping")
    contract.require(len(rows[4]["recordIds"]) == 1 and all(row["recordIds"] == rows[4]["recordIds"]
                     and row["changeId"] == rows[4]["changeId"] for row in block_rows), "Known native block was replaced")
    for i in (0, 1, 2, 4):
        contract.require(rows[i]["readback"] is None, "Preparation observation contains unexpected committed readback")
    for i in (3, 6):
        history_readback(rows[i], NAME_SHA, False)
    for i in (5, 7):
        history_readback(rows[i], BODY_SHA, True)
    contract.require(rows[3]["readback"] == rows[6]["readback"] and rows[5]["readback"] == rows[7]["readback"],
                     "Cold native history/readback differs from committed state")
    contract.require(rows[-1] == {"phase": "revoked-owner-refused", "error": "AnyHostError.sessionClosed",
                     "authorityScope": "application-owner-lifetime; native ACL mutation not exercised"},
                     "Retired application owner refusal missing or broadened")
    return dict(process_id=value["processId"], runtime_generations=generations,
                native_runtime_version=rows[0]["runtimeVersion"], phases=list(PHASES),
                account_id_sha256=hashlib.sha256(rows[0]["accountId"].encode()).hexdigest(),
                space_id_sha256=hashlib.sha256(rows[0]["spaceId"].encode()).hexdigest(),
                source_utf8=dict(name=NAME_SHA, body=BODY_SHA), limits=LIMITS, full_migration_accepted=False)
