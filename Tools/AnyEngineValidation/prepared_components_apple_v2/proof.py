"""Check native file observations separately from the original passed XCTest."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from uuid import UUID

import contract

SCHEMA = "pinkha-prepared-components-apple-v2"
OBSERVATION_STATUS = "OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"
BINDING_KEYS = {"sourceSHA", "executionUUID", "nonce"}
LIMITS = {
    "restartKind": "orderly-native-sdk-store-same-xctest-process",
    "osProcessCrash": "NOT_RUN",
    "lostHTTPAcknowledgement": "NOT_INJECTED",
    "networkSynchronization": "NOT_RUN",
    "SSEDelivery": "NOT_EVALUATED_TRANSIENT",
    "fullSpaceMigration": "NOT_PROVEN",
}
RECEIPT_PHASES = (
    ("prepared", 0, "file-prepared", "prepared"),
    ("afterPreparedReopen", 1, "file-prepared", "prepared"),
    ("committed", 1, "complete", "committed"),
    ("currentStatus", 1, "complete", "committed"),
    ("retry", 1, "complete", "committed"),
    ("afterCommittedReopenStatus", 2, "complete", "committed"),
    ("afterCommittedReopenRetry", 2, "complete", "committed"),
)
RECEIPT_IDENTITY = {"fingerprint", "payloadObjectId", "changeId", "fileId", "recordIds", "rootCid"}
RECEIPT_KEYS = RECEIPT_IDENTITY | {"runtimeGeneration", "ownerGeneration", "stage", "outcome", "localFileComplete", "networkVerified"}
FILE_KEYS = {
    "label", "sourceKey", "intentId", "ownerObjectId", "specBase64", "specSHA256",
    "expectedSize", "expectedContentSHA256", "nameUTF8Base64", "mime",
    "currentRead", "reopenedRead",
} | {row[0] for row in RECEIPT_PHASES}
TOP_KEYS = BINDING_KEYS | {
    "schema", "status", "method", "expectedNativeManifestSHA256", "expectedRuntimeVersion", "executionKind",
    "processId", "runtimeVersions", "runtimeGenerations", "ownerGenerations",
    "identity", "capabilities", "files", "orderlyReopenCount", "journeyComplete",
    "completedCleanup", "limits", "definitions", "documents", "schemaReads",
}
MAXIMUM_NAME = "\u05e7\u05d5\u05d1\u05e5 e\u0301 \U0001f9ea.bin"
FIXTURES = (
    ("minimum", bytes(index % 256 for index in range(4096)), "minimum.bin", "application/octet-stream"),
    ("two-mib", bytes(index % 251 for index in range(2 << 20)), MAXIMUM_NAME, "application/octet-stream"),
)


def text(value, maximum=1024):
    try:
        return isinstance(value, str) and 0 < len(value.encode("utf-8")) <= maximum and "\0" not in value
    except UnicodeError:
        return False


def uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)).lower() == value.lower()
    except (ValueError, AttributeError):
        return False


def exact_execution(summary, tree, udid, test_cases):
    contract.require(isinstance(summary, dict), "Actual XCTest summary must be an object")
    counts = {name: summary.get(name) for name in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    contract.require(all(type(v) is int for v in counts.values())
                     and counts == dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0),
                     "Exactly one actual passed XCTest and zero failures/skips required")
    destinations = summary.get("devicesAndConfigurations")
    contract.require(isinstance(destinations, list) and len(destinations) == 1
                     and isinstance(destinations[0], dict), "One actual simulator result required")
    device = destinations[0].get("device")
    contract.require(isinstance(device, dict) and uuid(udid)
                     and str(device.get("deviceId", "")).lower() == udid.lower()
                     and str(device.get("osVersion", "")).split(".")[0] == "27"
                     and device.get("architecture") == "arm64" and text(device.get("osBuildNumber")),
                     "Actual test destination is not the owned iOS27 ARM64 device")
    cases = test_cases(tree)
    contract.require(isinstance(cases, dict) and len(cases) == 1 and list(cases.values()) == ["Passed"]
                     and re.search(r"(?:^|/)" + re.escape(contract.METHOD) + r"(?:\(\))?$", next(iter(cases))),
                     "Wrong, duplicated or nonpassing actual XCTest terminal")
    return dict(counts=counts, actual_cases=cases, selected_method=contract.SELECTOR, device=device)


def _keys(value, required, optional=()):
    contract.require(isinstance(value, dict) and set(required) <= set(value)
                     and set(value) <= set(required) | set(optional),
                     "Missing or unexpected observation fields")


def _integer(value, expected):
    contract.require(type(value) is int and value == expected, "Wrong exact integer observation")


def _hex(value, count=64):
    contract.require(isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(count) + "}", value),
                     "Expected exact lowercase hexadecimal identity")


def _identifier(value, maximum=1024):
    contract.require(text(value, maximum) and all(0x21 <= ord(c) <= 0x7e for c in value),
                     "Invalid actual native record identity")


def _opaque(value, maximum=4096):
    contract.require(text(value, maximum) and all(ord(c) >= 32 and not 127 <= ord(c) <= 159 for c in value),
                     "Invalid native scope identity")


def _base64(value, maximum):
    contract.require(isinstance(value, str) and len(value) <= maximum, "Unbounded base64 observation")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError, UnicodeError) as error:
        raise ValueError("Invalid base64 observation") from error
    contract.require(base64.b64encode(decoded).decode("ascii") == value, "Noncanonical base64 observation")
    return decoded


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        contract.require(key not in result, "Duplicated JSON specification member")
        result[key] = value
    return result


def _json_constant(value):
    raise ValueError("Non-JSON number in original specification")


def _specification(raw):
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_pairs, parse_constant=_json_constant)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Invalid original full-file specification JSON") from error
    _keys(value, {"ownerObjectId", "name", "mime", "size", "contentSHA256"})
    return value


def _material(parts):
    # This is the public client's length-prefixed UTF-8 material, not a join
    # whose separators could conflate distinct source/workspace fields.
    return b"|".join(str(len(part.encode("utf-8"))).encode("ascii") + b":" + part.encode("utf-8")
                     for part in parts)


def _generation(value, index, runtimes, owners):
    contract.require(value["runtimeGeneration"] == runtimes[index]
                     and value["ownerGeneration"] == owners[index],
                     "Observation belongs to the wrong runtime or application owner generation")


def _receipt(value, index, stage, outcome, runtimes, owners, native_owner):
    _keys(value, RECEIPT_KEYS)
    _generation(value, index, runtimes, owners)
    contract.require(value["stage"] == stage and value["outcome"] == outcome,
                     "Unexpected native stage/outcome; obsolete is never successful")
    _hex(value["fingerprint"])
    for name in ("payloadObjectId", "changeId", "fileId", "rootCid"):
        _identifier(value[name])
    contract.require(value["payloadObjectId"] != native_owner and value["recordIds"] == [value["fileId"]],
                     "Native carrier/owner/file identities were conflated")
    contract.require(value["localFileComplete"] is (stage == "complete") and value["networkVerified"] is False,
                     "Local file and network completion claims differ")
    return {name: value[name] for name in RECEIPT_IDENTITY}


def _readback(value, index, runtimes, owners, native_owner, file_id, root_cid, content, name, mime):
    _keys(value, {"runtimeGeneration", "ownerGeneration", "metadata", "status", "content"})
    _generation(value, index, runtimes, owners)
    metadata = value["metadata"]
    _keys(metadata, {"fileId", "objectId", "size", "cached", "rootCid"},
          {"inline", "durable", "name", "mime", "variant", "variantOf"})
    contract.require(metadata["fileId"] == file_id and metadata["objectId"] == native_owner
                     and metadata["rootCid"] == root_cid and metadata.get("inline", False) is False
                     and metadata["cached"] is True, "Exact locally complete full-tier native file required")
    _integer(metadata["size"], len(content))
    contract.require(metadata.get("name", "").encode("utf-8") == name.encode("utf-8")
                     and metadata.get("mime", "") == mime, "Filename or MIME bytes changed")
    if "durable" in metadata:
        contract.require(type(metadata["durable"]) is bool, "Malformed remote durability state")
    status = value["status"]
    _keys(status, {"fileId", "objectId", "state", "cached"}, {"attempts", "lastErr"})
    contract.require(status["fileId"] == file_id and status["objectId"] == native_owner
                     and status["cached"] is True and text(status["state"], 64),
                     "Ordinary native status does not identify the local file")
    if "attempts" in status:
        contract.require(type(status["attempts"]) is int and status["attempts"] >= 0, "Invalid retry count")
    if "lastErr" in status:
        contract.require(isinstance(status["lastErr"], str) and len(status["lastErr"].encode("utf-8")) <= 4096,
                         "Unbounded file status detail")
    observed = value["content"]
    _keys(observed, {"httpStatus", "mediaType", "byteCount", "sha256"})
    _integer(observed["httpStatus"], 200)
    _integer(observed["byteCount"], len(content))
    contract.require(observed["mediaType"] == "application/octet-stream"
                     and observed["sha256"] == _digest(content), "Native HTTP bytes changed")
    # Queue state may legitimately progress between reopens. Only immutable
    # content and identifiers are compared; network durability is not accepted.
    return observed


def observation(value, expected_binding):
    """Return qualified observations; original passing XCTest is still required."""
    _keys(expected_binding, BINDING_KEYS)
    _hex(expected_binding["sourceSHA"], 40)
    _hex(expected_binding["nonce"], 32)
    contract.require(uuid(expected_binding["executionUUID"]), "Actual local UUID required")
    _keys(value, TOP_KEYS)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("Observation is not bounded valid JSON") from error
    contract.require(len(encoded) <= 131072, "Observation exceeds the 131072-byte bound")
    contract.require({key: value[key] for key in BINDING_KEYS} == expected_binding,
                     "Observation source/local-execution/nonce does not match this actual execution")
    contract.require(value["schema"] == SCHEMA and value["status"] == OBSERVATION_STATUS
                     and value["method"] == contract.METHOD and value["executionKind"] == "local-mac"
                     and value["expectedNativeManifestSHA256"] == contract.MANIFEST_SHA
                     and value["expectedRuntimeVersion"] == contract.VERSION, "Wrong exact observation/native contract")
    contract.require(type(value["processId"]) is int and value["processId"] > 0, "Actual process identity required")
    versions = value["runtimeVersions"]
    contract.require(isinstance(versions, list) and len(versions) == 3
                     and all(text(version) and version.startswith("any " + contract.VERSION + " ") for version in versions)
                     and len(set(versions)) == 1, "Three matching exact native version observations required")
    generations = []
    for key in ("runtimeGenerations", "ownerGenerations"):
        entries = value[key]
        contract.require(isinstance(entries, list) and len(entries) == 3 and all(uuid(entry) for entry in entries)
                         and len({entry.lower() for entry in entries}) == 3,
                         "Exactly three distinct runtime and application owner generations required")
        generations.append(entries)
    runtimes, owners = generations
    _integer(value["orderlyReopenCount"], 2)
    contract.require(value["journeyComplete"] is True and value["completedCleanup"] is True,
                     "Journey and owned cleanup must actually complete")
    _keys(value["limits"], LIMITS)
    contract.require(value["limits"] == LIMITS, "Unsupported acceptance scope claim")
    capabilities = value["capabilities"]
    _keys(capabilities, {"contract", "maximumBytes", "networkVerified", "definitionsContract", "supportsParts", "maximumDefinitionRecordIDs", "propertyUpdatesContract", "maximumPropertyPatchKeys"})
    contract.require(capabilities["contract"] == "pinkha-native-prepared-migration-v1"
                     and capabilities["networkVerified"] is False, "Unsupported native capability")
    _integer(capabilities["maximumBytes"], 512 << 20)
    contract.require(capabilities["definitionsContract"] == "pinkha-native-prepared-definitions-v1" and capabilities["supportsParts"] is True, "Actual native definition/part capability required")
    _integer(capabilities["maximumDefinitionRecordIDs"], 2048)
    contract.require(capabilities["propertyUpdatesContract"] == "pinkha-native-prepared-property-update-v1",
                     "Actual durable property-update contract required")
    _integer(capabilities["maximumPropertyPatchKeys"], 128)

    identity = value["identity"]
    _keys(identity, {"accountId", "spaceId", "storeId", "ownerObjectIds", "planId", "planSHA256"})
    for key in ("accountId", "spaceId"):
        _opaque(identity[key])
    _opaque(identity["storeId"], 256)
    native_owners = identity["ownerObjectIds"]
    contract.require(isinstance(native_owners, list) and len(native_owners) == 2, "Two native owners required")
    for owner in native_owners:
        _identifier(owner, 256)
    contract.require(len(set(native_owners)) == 2, "Pending plans must have distinct native owners")
    _hex(identity["planId"])
    _hex(identity["planSHA256"])
    nonce = expected_binding["nonce"]
    contract.require(identity["planId"] == _digest(("apple-native-components-plan|" + nonce).encode("utf-8"))
                     and identity["planSHA256"] == _digest(b"definitions+parts+deferred-properties+objects+blocks+files:4096+2097152/v2"),
                     "Plan identity differs from the deterministic actual XCTest")

    files = value["files"]
    contract.require(isinstance(files, list) and len(files) == 2, "Exactly the two ordered full-tier files required")
    qualified = []
    for index, (row, fixture) in enumerate(zip(files, FIXTURES)):
        _keys(row, FILE_KEYS)
        label, content, name, mime = fixture
        source_key = "apple-full-file-" + label + "-" + nonce
        native_owner = native_owners[index]
        contract.require(row["label"] == label and row["sourceKey"] == source_key
                         and row["ownerObjectId"] == native_owner, "Ordered case/source/native-owner binding differs")
        _integer(row["expectedSize"], len(content))
        contract.require(row["expectedContentSHA256"] == _digest(content)
                         and _base64(row["nameUTF8Base64"], 1368) == name.encode("utf-8")
                         and row["mime"] == mime, "Deterministic content or Unicode metadata differs")
        material = _material(["pinkha-native-prepared-migration-intent/v1", identity["accountId"],
                              identity["spaceId"], identity["storeId"], identity["planId"], source_key, "file"])
        contract.require(row["intentId"] == _digest(material), "Length-prefixed source intent identity differs")
        raw_spec = _base64(row["specBase64"], 16384)
        contract.require(row["specSHA256"] == _digest(raw_spec), "Original specification bytes/hash differ")
        spec = _specification(raw_spec)
        contract.require(spec["ownerObjectId"] == native_owner and isinstance(spec["name"], str)
                         and spec["name"].encode("utf-8") == name.encode("utf-8") and spec["mime"] == mime
                         and spec["contentSHA256"] == _digest(content)
                         and type(spec["size"]) is int and spec["size"] == len(content),
                         "Original specification differs from the exact input bytes/owner")
        reference = None
        for phase, generation, stage, outcome in RECEIPT_PHASES:
            observed = _receipt(row[phase], generation, stage, outcome, runtimes, owners, native_owner)
            if reference is None:
                reference = observed
            contract.require(observed == reference, "Native signed carrier/change/file identity changed across phases")
        current = _readback(row["currentRead"], 1, runtimes, owners, native_owner, reference["fileId"], reference["rootCid"], content, name, mime)
        reopened = _readback(row["reopenedRead"], 2, runtimes, owners, native_owner, reference["fileId"], reference["rootCid"], content, name, mime)
        contract.require(current == reopened, "Ordinary native bytes/metadata/status changed after committed reopen")
        qualified.append(dict(label=label, ownerObjectId=native_owner, sourceKey=source_key,
                              intentId=row["intentId"], specSHA256=row["specSHA256"], **reference,
                              byteCount=len(content), contentSHA256=_digest(content)))
    contract.require(len({row["fileId"] for row in qualified}) == 2
                     and len({row["intentId"] for row in qualified}) == 2,
                     "Two actual file and intent identities must remain distinct")
    components = _validate_components(value, identity, nonce, runtimes, owners)
    # Payload roots are owner-scoped native carriers, not globally unique per-file IDs.
    return dict(status="VALIDATED_OBSERVATIONS_ORIGINAL_XCTEST_REQUIRED", schema=SCHEMA,
                execution_binding=dict(expected_binding), runtime_versions=versions,
                runtime_generations=runtimes, owner_generations=owners, identity=identity,
                files=qualified, components=components, receipt_observations=14, ordinary_content_readbacks=4,
                orderly_reopens=2, completed_cleanup=True, limits=dict(LIMITS))



COMPONENT_RECEIPT_KEYS = {"runtimeGeneration", "ownerGeneration", "stage", "outcome",
                          "fingerprint", "objectId", "changeId", "recordIds"}
DEFINITION_PHASES = (("committed", 0), ("afterFirstReopenStatus", 1),
                     ("afterFirstReopenRetry", 1), ("afterSecondReopenStatus", 2),
                     ("afterSecondReopenRetry", 2))
DEFINITION_LABELS = ("type", "collection", "part", "type-property", "collection-property")
DEFINITION_KINDS = ("typeDefinition", "collectionDefinition", "partDefinition",
                    "propertyDefinition", "propertyDefinition")


def _component_receipt(value, generation, runtimes, owners, stage="complete", outcome="committed"):
    _keys(value, COMPONENT_RECEIPT_KEYS)
    _generation(value, generation, runtimes, owners)
    contract.require(value["stage"] == stage and value["outcome"] == outcome,
                     "Component native receipt has the wrong stage/outcome")
    _hex(value["fingerprint"])
    _identifier(value["objectId"])
    _identifier(value["changeId"])
    ids = value["recordIds"]
    contract.require(isinstance(ids, list) and len(ids) <= 2048 and len(ids) == len(set(ids)),
                     "Component native ordered record IDs are invalid")
    for identifier in ids:
        _identifier(identifier)
    return {name: value[name] for name in ("fingerprint", "objectId", "changeId", "recordIds")}


def _component_intent(value, identity, source_key, kind):
    contract.require(value["kind"] == kind and value["sourceKey"] == source_key,
                     "Component source/kind differs from the actual fixture")
    material = _material(["pinkha-native-prepared-migration-intent/v1", identity["accountId"],
        identity["spaceId"], identity["storeId"], identity["planId"], source_key, kind])
    contract.require(value["intentId"] == _digest(material), "Component intent is not bound to its source/scope")
    raw = _base64(value["specBase64"], 32768)
    contract.require(value["specSHA256"] == _digest(raw), "Component original specification hash differs")
    spec = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_pairs, parse_constant=_json_constant)
    contract.require(isinstance(spec, dict), "Component specification is not an object")
    return spec


def _validate_components(value, identity, nonce, runtimes, owners):
    definitions = value["definitions"]
    contract.require(isinstance(definitions, list) and len(definitions) == 5,
                     "Exactly five actual native definition plans required")
    completed = []
    specs = []
    definition_keys = {"label", "kind", "sourceKey", "intentId", "specBase64", "specSHA256", "prepared"} | {
        name for name, _ in DEFINITION_PHASES}
    for index, (row, label, kind) in enumerate(zip(definitions, DEFINITION_LABELS, DEFINITION_KINDS)):
        _keys(row, definition_keys)
        contract.require(row["label"] == label, "Definition order differs from the source fixture")
        spec = _component_intent(row, identity, "apple-native-definition-" + label + "-" + nonce, kind)
        specs.append(spec)
        initial_stage = "definition-root-prepared" if index < 2 else (
            "definition-part-prepared" if index == 2 else "definition-property-prepared")
        prepared = _component_receipt(row["prepared"], 0, runtimes, owners, initial_stage, "prepared")
        reference = None
        for phase, generation in DEFINITION_PHASES:
            actual = _component_receipt(row[phase], generation, runtimes, owners)
            if reference is None:
                reference = actual
            contract.require(actual == reference, "Definition native IDs changed across actual reopen/status/retry")
        contract.require(prepared["fingerprint"] == reference["fingerprint"] and
                         prepared["objectId"] == reference["objectId"], "Definition lost its original native owner")
        if index < 2:
            contract.require(prepared["recordIds"] == [] and prepared["changeId"] == prepared["objectId"]
                             and reference["recordIds"] == [reference["objectId"]]
                             and reference["changeId"] != prepared["changeId"],
                             "Native root and original bootstrap identities were conflated")
        else:
            contract.require(prepared == reference and len(reference["recordIds"]) == (6 if index == 2 else 1),
                             "Native atomic part/property signed identity changed")
        completed.append(reference)
    type_id, collection_id = completed[0]["objectId"], completed[1]["objectId"]
    part = completed[2]["recordIds"]
    type_property, collection_property = completed[3]["recordIds"][0], completed[4]["recordIds"][0]
    contract.require(type_id != collection_id and completed[2]["objectId"] == type_id
                     and completed[3]["objectId"] == type_id and completed[4]["objectId"] == collection_id
                     and len(set(part + [type_id, collection_id, type_property, collection_property])) == 10,
                     "Distinct native definition identities or owner mapping were lost")
    type_seed = {"xKey": "apple-type-" + nonce, "name": "סוג מסמך מועבר", "description": "", "iconCid": "",
                 "hidden": False, "meta": {"migrationFixture": True}, "layout": {"type": "page"}}
    collection_seed = {"xKey": "apple-collection-" + nonce, "name": "אוסף מועבר", "description": "", "iconCid": "",
                       "hidden": False, "meta": {}}
    part_seed = {"key": "content", "name": "תוכן", "pos": "m", "ui": {"type": "document"}, "datasets": [
        {"module": "editor", "key": "editor_blocks"},
        {"module": "records", "key": "notes", "displayName": "הערות", "fields": [
            {"key": "title", "name": "Title", "kind": "string", "required": True, "mutableBy": "any"},
            {"key": "score", "kind": "number", "mutableBy": "any"}],
         "indexes": [{"key": "title_index", "fields": ["title"]}]}]}
    expected_specs = [
        {"kind": "typeDefinition", "type": type_seed},
        {"kind": "collectionDefinition", "collection": collection_seed},
        {"kind": "partDefinition", "ownerObjectId": type_id, "part": part_seed},
        {"kind": "propertyDefinition", "ownerObjectId": type_id, "property": {
            "kind": "string", "name": "מקור", "xKey": "source_ref", "description": "", "scope": "synced"}},
        {"kind": "propertyDefinition", "ownerObjectId": collection_id, "property": {
            "kind": "string", "name": "קבוצה", "xKey": "source_group", "description": "", "scope": "synced"}}]
    contract.require(specs == expected_specs, "Actual definition specification differs from its complete fixture")

    schema_reads = value["schemaReads"]
    contract.require(isinstance(schema_reads, list) and len(schema_reads) == 3,
                     "Ordinary compiled native schema must be read in all three runtime generations")
    expected_schema = dict(typeId=type_id, typeXKey="apple-type-" + nonce, typeName="סוג מסמך מועבר",
        collectionId=collection_id, collectionXKey="apple-collection-" + nonce, collectionName="אוסף מועבר",
        typePropertyId=type_property, typePropertyKind="string", typePropertyXKey="source_ref",
        collectionPropertyId=collection_property, collectionPropertyKind="string", collectionPropertyXKey="source_group",
        partId=part[0], partKey="content", partName="תוכן", editorDatasetId=part[1], notesDatasetId=part[2],
        titleFieldId=part[3], scoreFieldId=part[4], titleIndexId=part[5])
    notes_collection = None
    for generation, read in enumerate(schema_reads):
        _keys(read, set(expected_schema) | {"runtimeGeneration", "ownerGeneration", "notesCollection"})
        _generation(read, generation, runtimes, owners)
        contract.require({key: read[key] for key in expected_schema} == expected_schema,
                         "Ordinary compiled native schema differs from its mapped original identities")
        _identifier(read["notesCollection"])
        if notes_collection is None:
            notes_collection = read["notesCollection"]
        contract.require(read["notesCollection"] == notes_collection and notes_collection != "editor_blocks",
                         "Native records collection changed across reopen or collided with editor data")

    documents = value["documents"]
    contract.require(isinstance(documents, list) and len(documents) == 2, "Two actual custom-type native documents required")
    for index, (row, fixture) in enumerate(zip(documents, FIXTURES)):
        label = fixture[0]
        document_keys = {"label", "ownerObjectId", "objectIntent", "blockIntent", "objectCommitted",
            "blockPrepared", "blockCommitted", "expectedTypeValueUTF8Base64", "expectedCollectionValueUTF8Base64",
            "expectedBlockTextUTF8Base64", "currentRead", "propertyIntent", "propertyPrepared", "propertyCommitted"}
        for phase in ("afterFirstReopen", "afterSecondReopen"):
            document_keys.add(phase + "Read")
            for kind in ("Object", "Block", "Property"):
                document_keys.update({phase + kind + "Status", phase + kind + "Retry"})
        _keys(row, document_keys)
        owner_id = identity["ownerObjectIds"][index]
        contract.require(row["label"] == label and row["ownerObjectId"] == owner_id,
                         "Document and full-file native owner identities differ")
        type_value = ("מקור e\u0301 " + label).encode("utf-8")
        collection_value = ("קבוצה " + label).encode("utf-8")
        block_text = ("שלום e\u0301 🧪 — migrated custom type " + label).encode("utf-8")
        for key, expected in (("expectedTypeValueUTF8Base64", type_value),
                              ("expectedCollectionValueUTF8Base64", collection_value),
                              ("expectedBlockTextUTF8Base64", block_text)):
            contract.require(_base64(row[key], 4096) == expected, "Expected document Unicode bytes differ")
        for name, kind, prefix in (("objectIntent", "object", "apple-native-document-"),
                                   ("blockIntent", "editorBlock", "apple-native-block-")):
            _keys(row[name], {"kind", "sourceKey", "intentId", "specBase64", "specSHA256"})
            spec = _component_intent(row[name], identity, prefix + label + "-" + nonce, kind)
            if kind == "object":
                expected = {"type": type_id, "collections": [collection_id], "initialProperties": {
                    "any": {"name": "Migrated document " + label}, type_id: {type_property: type_value.decode()}}}
            else:
                expected = {"objectId": owner_id, "dataset": "editor_blocks", "type": "paragraph",
                    "text": block_text.decode(), "style": {}, "nav": {"parentId": "", "pos": "m"}}
            contract.require(spec == expected, "Native document/block original specification differs")
        original_object = _component_receipt(row["objectCommitted"], 0, runtimes, owners)
        original_block = _component_receipt(row["blockCommitted"], 0, runtimes, owners)
        prepared_block = _component_receipt(row["blockPrepared"], 0, runtimes, owners, "block-prepared", "prepared")
        contract.require(original_object["objectId"] == owner_id and original_object["recordIds"] == [owner_id]
                         and original_block == prepared_block and original_block["objectId"] == owner_id
                         and len(original_block["recordIds"]) == 1,
                         "Actual document/block native identity was not preserved")
        _keys(row["propertyIntent"], {"kind", "sourceKey", "intentId", "specBase64", "specSHA256"})
        property_spec = _component_intent(row["propertyIntent"], identity,
            "apple-native-property-update-" + label + "-" + nonce, "propertyUpdate")
        _keys(property_spec, {"objectId", "ownerId", "patch", "expectedApplySeq"})
        contract.require(property_spec["objectId"] == owner_id and property_spec["ownerId"] == collection_id
                         and property_spec["patch"] == {collection_property: collection_value.decode()}
                         and type(property_spec["expectedApplySeq"]) is int
                         and 0 < property_spec["expectedApplySeq"] <= 9007199254740991,
                         "Deferred collection property specification or original native sequence differs")
        prepared_property = _component_receipt(row["propertyPrepared"], 0, runtimes, owners, "properties-prepared", "prepared")
        original_property = _component_receipt(row["propertyCommitted"], 0, runtimes, owners)
        contract.require(prepared_property == original_property
                         and original_property["objectId"] == owner_id
                         and original_property["recordIds"] == [owner_id]
                         and original_property["changeId"] not in {original_object["changeId"], original_block["changeId"]},
                         "Deferred SET lost its distinct original signed native change")
        for generation, phase in ((1, "afterFirstReopen"), (2, "afterSecondReopen")):
            for kind, original in (("Object", original_object), ("Block", original_block), ("Property", original_property)):
                for action in ("Status", "Retry"):
                    actual = _component_receipt(row[phase + kind + action], generation, runtimes, owners)
                    contract.require(actual == original, "Actual document/block changed across native reopen/retry")
        read_keys = {"runtimeGeneration", "ownerGeneration", "objectId", "typeValueUTF8Base64",
            "collectionValueUTF8Base64", "blockId", "blockType", "blockTextUTF8Base64", "parentId", "position", "blockCount"}
        for generation, phase in ((0, "currentRead"), (1, "afterFirstReopenRead"), (2, "afterSecondReopenRead")):
            read = row[phase]
            _keys(read, read_keys)
            _generation(read, generation, runtimes, owners)
            contract.require(read["objectId"] == owner_id and read["blockId"] == original_block["recordIds"][0]
                             and read["blockType"] == "paragraph" and read["parentId"] == "" and read["position"] == "m",
                             "Ordinary native document/block hierarchy differs")
            _integer(read["blockCount"], 1)
            for key, expected in (("typeValueUTF8Base64", type_value), ("collectionValueUTF8Base64", collection_value),
                                  ("blockTextUTF8Base64", block_text)):
                contract.require(_base64(read[key], 4096) == expected, "Ordinary native document/block lost exact Unicode bytes")
    return dict(definition_plans=5, atomic_part_record_ids=part, compiled_schema_readbacks=3,
                custom_type_documents=2, native_editor_blocks=2, document_readbacks=6, durable_property_updates=2,
                type_id=type_id, collection_id=collection_id, type_property_id=type_property,
                collection_property_id=collection_property, whole_space_admission=False)
