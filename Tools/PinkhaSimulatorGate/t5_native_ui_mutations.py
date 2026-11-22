"""Qualify two additional real native mutations in the existing corrected T5 prep.

This parses original native evidence; synthetic controller fixtures do not prove
runtime behavior. The original five UI targets and historical pair are unchanged.
"""
import hashlib
import json
from pathlib import Path

import t5_native_ui_evidence as evidence

PROFILE = "r15-attachment-v1"
PROFILES = frozenset({PROFILE, "r15-attachment-authorized-current-read-v1"})
RELATIVE = "Library/Application Support/pinkha-t5-native-ui-mutations.json"
COPY_NAME = "native-mutations.json"
PASS = "PASS_ACTUAL_NATIVE_TYPE_CHANGE_AND_DELETE"
STAGES = ["page-before-type-change", "note-after-type-change", "whole-object-deleted"]
BOUND_KEYS = {"token", "appSourceSHA", "runID", "runtimeVersion", "preparationProcessID", "accountID",
              "spaceID", "accountRootPathSHA256", "providerID", "canonicalReference"}
ROW_KEYS = {"resultID", "objectID", "spaceID", "title", "typeID", "kind", "canUnlink"}
COMMON_OBSERVATION = {"stage", "nativeReadStatus", "relatedRows", "coverage", "limitations"}
PRESENT_OBSERVATION = {"nativeTypeID", "nativeTypeKey", "nativeLayout", "nativeTitle", "associationID",
                       "canonicalSHA256", "bodySHA256", "blockReachable"}


def _identity(space, object_id, block=None):
    return "|".join(str(len(value.encode("utf8"))) + ":" + value for value in [space, object_id, block or ""])


def _rows(values, fixture):
    evidence.require(isinstance(values, list) and len(values) in {5, 6}, "Exact five or six actual rows required")
    for row in values:
        evidence.require(isinstance(row, dict) and set(row) in [ROW_KEYS, ROW_KEYS | {"blockID"}],
                         "Unexpected mutation row schema")
        evidence.require(all(evidence.nonempty(row.get(key)) for key in ["resultID", "objectID", "spaceID", "typeID"])
                         and isinstance(row.get("title"), str) and row["spaceID"] == fixture["spaceID"]
                         and row["kind"] in {"note", "document"} and type(row["canUnlink"]) is bool,
                         "Native mutation row authority/type is absent")
        evidence.require("blockID" not in row or evidence.nonempty(row["blockID"]), "Empty mutation block identity")
        evidence.require(row["resultID"] == _identity(row["spaceID"], row["objectID"], row.get("blockID")),
                         "Mutation row identifies another native target")
    ids = [row["resultID"] for row in values]
    evidence.require(ids == sorted(set(ids)) and len({row["objectID"] for row in values}) == len(values),
                     "Mutation native rows are duplicated or unordered")
    return {row["objectID"]: row for row in values}


def validate(value, fixture):
    expected = BOUND_KEYS | {"protocolVersion", "status", "scope", "transientObjectID", "transientAssociationID",
                            "transientBlockID", "canonicalPropertyKey", "observations", "productLookupFlag", "fullT5Accepted"}
    evidence.require(isinstance(value, dict) and set(value) == expected
                     and type(value["protocolVersion"]) is int and value["protocolVersion"] == 1
                     and value["status"] == "PASS" and value["scope"] == "type-change-and-whole-object-delete",
                     "Original complete native mutation receipt required")
    evidence.require(all(value[key] == fixture[key] for key in BOUND_KEYS)
                     and type(value["preparationProcessID"]) is int and value["preparationProcessID"] > 0,
                     "Native mutation source/runtime/account/attempt differs")
    evidence.require(value["productLookupFlag"] == "OFF" and value["fullT5Accepted"] is False,
                     "Mutation receipt expanded product or acceptance scope")
    for key in ["transientObjectID", "transientAssociationID", "transientBlockID", "canonicalPropertyKey"]:
        evidence.require(evidence.nonempty(value[key]), "Transient native identity is absent")
    transient = value["transientObjectID"]
    forbidden = {item["objectID"] for item in fixture["targets"] + fixture["excluded"]}
    evidence.require(transient not in forbidden and transient != value["transientBlockID"]
                     and value["transientAssociationID"] not in {item["associationID"] for item in fixture["targets"]},
                     "Transient mutation reused an original fixture identity")
    observations = value["observations"]
    evidence.require(isinstance(observations, list) and [item.get("stage") for item in observations] == STAGES,
                     "Exactly three ordered native mutation observations required")
    row_sets = []
    body_hash = hashlib.sha256(("T5 native type/delete preserved body " + fixture["token"]).encode("utf8")).hexdigest()
    original_by_role = {item["role"]: item for item in fixture["targets"]}
    for index, observation in enumerate(observations):
        required = COMMON_OBSERVATION | (PRESENT_OBSERVATION if index < 2 else set())
        evidence.require(set(observation) == required, "Unexpected mutation observation fields")
        evidence.require(observation["coverage"] == "indexedTargetsOnly"
                         and observation["limitations"] == ["indexFreshnessUnverified"],
                         "Mutation observation silently asserted index completeness")
        rows = _rows(observation["relatedRows"], fixture)
        row_sets.append(rows)
        evidence.require(set(rows) == ({item["objectID"] for item in fixture["targets"]} | ({transient} if index < 2 else set())),
                         "Actual native mutation result membership differs")
        if index < 2:
            role = "page" if index == 0 else "note"
            evidence.require(observation["nativeReadStatus"] == "present"
                             and observation["blockReachable"] is True
                             and observation["bodySHA256"] == body_hash
                             and evidence.is_hash(observation["canonicalSHA256"])
                             and observation["associationID"] == value["transientAssociationID"],
                             "Type mutation lost native body, canonical bytes or original link identity")
            evidence.require(observation["nativeTypeKey"] == original_by_role[role]["typeKey"]
                             and type(observation["nativeLayout"]) is int
                             and observation["nativeTypeID"] == rows[original_by_role[role]["objectID"]]["typeID"],
                             "Native type identity does not match the real Page/Note type")
            changed = rows[transient]
            evidence.require(changed["typeID"] == observation["nativeTypeID"]
                             and changed["title"] == observation["nativeTitle"]
                             and changed["kind"] == ("document" if index == 0 else "note")
                             and changed.get("blockID") is None and changed["canUnlink"] is True,
                             "Actual related service retained stale native type/title/authority")
        else:
            evidence.require(observation["nativeReadStatus"] in {"isDeleted", "objectDeleted", "notFound"},
                             "Whole-object deletion lacks an actual native deleted/not-found readback")
    evidence.require(observations[0]["nativeTypeID"] != observations[1]["nativeTypeID"]
                     and observations[0]["nativeLayout"] != observations[1]["nativeLayout"]
                     and observations[0]["canonicalSHA256"] == observations[1]["canonicalSHA256"],
                     "Actual type did not change or exact canonical bytes were altered")
    for target in fixture["targets"]:
        rows = [values[target["objectID"]] for values in row_sets]
        evidence.require(rows[0] == rows[1] == rows[2], "Mutation altered an original UI row")
        row = rows[0]
        evidence.require(row["resultID"] == target["resultID"] and row["title"] == target["title"]
                         and row.get("blockID") == target.get("blockID")
                         and row["kind"] == ("note" if target["role"] == "note" else "document")
                         and row["canUnlink"] == (target.get("blockID") is None),
                         "Final five native rows differ from the actual UI fixture")
    return {"status": PASS, "actual_mutations": 2, "actual_observations": 3,
            "stages": STAGES, "final_ui_targets": 5, "full_t5_accepted": False}


def capture(container, private, fixture, runtime_profile):
    if runtime_profile not in PROFILES:
        return {"status": "NOT_SELECTED", "actual_mutations": 0, "actual_observations": 0}
    source = Path(container) / RELATIVE
    evidence.require(source.is_file() and not source.is_symlink() and 0 < source.stat().st_size <= 64 * 1024
                     and source.resolve(strict=True).is_relative_to(Path(container).resolve(strict=True)),
                     "Bounded original native mutation receipt is missing or foreign")
    data = source.read_bytes()
    result = validate(json.loads(data.decode("utf8")), fixture)
    destination = Path(private) / COPY_NAME
    with destination.open("xb") as stream:
        stream.write(data)
    return {**result, "receipt": COPY_NAME, "receipt_sha256": hashlib.sha256(data).hexdigest()}
