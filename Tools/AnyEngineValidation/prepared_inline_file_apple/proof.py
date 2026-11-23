"""Admit bounded native observations separately from one original actual XCTest.

Schema contract: observation.schema.json SHA256
19b0a8a98a0ecc6495e6be6048860d7f6307ae23f39786a4c90ed2ef8e7b6d9e.
The validator is stdlib-only and deliberately does not trust self-reported PASS.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from uuid import UUID

import contract

SCHEMA_SHA256 = "19b0a8a98a0ecc6495e6be6048860d7f6307ae23f39786a4c90ed2ef8e7b6d9e"
SCHEMA = "pinkha-prepared-inline-file-apple-v1"
OBSERVATION_STATUS = "OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"
BINDING_KEYS = {"sourceSHA", "runID", "runAttempt", "nonce"}
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
RECEIPT_IDENTITY = {"fingerprint", "payloadObjectId", "changeId", "fileId", "recordIds"}
RECEIPT_KEYS = RECEIPT_IDENTITY | {"runtimeGeneration", "ownerGeneration", "stage", "outcome"}
FILE_KEYS = {
    "label", "sourceKey", "intentId", "ownerObjectId", "specBase64", "specSHA256",
    "expectedSize", "expectedContentSHA256", "nameUTF8Base64", "mime",
    "currentRead", "reopenedRead",
} | {row[0] for row in RECEIPT_PHASES}
TOP_KEYS = BINDING_KEYS | {
    "schema", "status", "method", "expectedNativeManifestSHA256", "expectedRuntimeVersion",
    "processId", "runtimeVersions", "runtimeGenerations", "ownerGenerations",
    "identity", "capabilities", "files", "orderlyReopenCount", "journeyComplete",
    "completedCleanup", "limits",
}
MAXIMUM_NAME = "\u05e7\u05d5\u05d1\u05e5 e\u0301 \U0001f9ea.bin"
FIXTURES = (
    ("empty", b"", "", ""),
    ("maximum", bytes(index % 256 for index in range(4095)), MAXIMUM_NAME, "application/octet-stream"),
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
        raise ValueError("Invalid original inline specification JSON") from error
    _keys(value, {"ownerObjectId", "name", "mime", "content", "contentSHA256"})
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
    for name in ("payloadObjectId", "changeId", "fileId"):
        _identifier(value[name])
    contract.require(value["payloadObjectId"] != native_owner and value["recordIds"] == [value["fileId"]],
                     "Native carrier/owner/file identities were conflated")
    return {name: value[name] for name in RECEIPT_IDENTITY}


def _readback(value, index, runtimes, owners, native_owner, file_id, content, name, mime):
    _keys(value, {"runtimeGeneration", "ownerGeneration", "metadata", "status", "content"})
    _generation(value, index, runtimes, owners)
    metadata = value["metadata"]
    _keys(metadata, {"fileId", "objectId", "size", "inline", "durable", "cached"},
          {"name", "mime", "variant", "variantOf"})
    contract.require(metadata["fileId"] == file_id and metadata["objectId"] == native_owner,
                     "Ordinary native metadata belongs to another file/owner")
    _integer(metadata["size"], len(content))
    contract.require(all(metadata[key] is True for key in ("inline", "durable", "cached")),
                     "Ordinary file metadata is not inline/durable/cached")
    for key, maximum in (("name", 1024), ("mime", 255), ("variant", 256), ("variantOf", 256)):
        if key in metadata:
            entry = metadata[key]
            contract.require(isinstance(entry, str) and len(entry.encode("utf-8")) <= maximum
                             and "\0" not in entry, "Invalid ordinary metadata string")
    contract.require(metadata.get("name", "").encode("utf-8") == name.encode("utf-8")
                     and metadata.get("mime", "") == mime, "Original filename or MIME bytes changed")
    status = value["status"]
    _keys(status, {"fileId", "objectId", "state", "cached"}, {"attempts", "lastErr"})
    contract.require(status["fileId"] == file_id and status["objectId"] == native_owner
                     and status["state"] == "durable" and status["cached"] is True,
                     "Ordinary native status does not identify the durable local file")
    if "attempts" in status:
        contract.require(type(status["attempts"]) is int and status["attempts"] >= 0, "Invalid file attempt count")
    if "lastErr" in status:
        contract.require(isinstance(status["lastErr"], str) and len(status["lastErr"].encode("utf-8")) <= 4096,
                         "Unbounded file status error")
    observed = value["content"]
    _keys(observed, {"httpStatus", "mediaType", "byteCount", "sha256", "base64"})
    _integer(observed["httpStatus"], 200)
    _integer(observed["byteCount"], len(content))
    contract.require(observed["mediaType"] == "application/octet-stream"
                     and observed["sha256"] == _digest(content)
                     and _base64(observed["base64"], 5460) == content,
                     "Actual ordinary native HTTP content bytes changed")
    return {key: value[key] for key in ("metadata", "status", "content")}


def observation(value, expected_binding):
    """Return qualified observations; original passing XCTest is still required."""
    _keys(expected_binding, BINDING_KEYS)
    _hex(expected_binding["sourceSHA"], 40)
    _hex(expected_binding["nonce"], 32)
    for key in ("runID", "runAttempt"):
        entry = expected_binding[key]
        contract.require(isinstance(entry, str) and re.fullmatch(r"[1-9][0-9]*", entry)
                         and len(entry) <= 20 and int(entry) < 2**64, "Invalid expected run binding")
    _keys(value, TOP_KEYS)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("Observation is not bounded valid JSON") from error
    contract.require(len(encoded) <= 65536, "Observation exceeds the 65536-byte bound")
    contract.require({key: value[key] for key in BINDING_KEYS} == expected_binding,
                     "Observation source/run/attempt/nonce does not match this actual execution")
    contract.require(value["schema"] == SCHEMA and value["status"] == OBSERVATION_STATUS
                     and value["method"] == contract.METHOD
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
    _keys(capabilities, {"contract", "maximumInlineBytes", "networkVerified"})
    contract.require(capabilities["contract"] == "pinkha-native-prepared-migration-v1"
                     and capabilities["networkVerified"] is False, "Unsupported native capability")
    _integer(capabilities["maximumInlineBytes"], 4095)

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
    contract.require(identity["planId"] == _digest(("apple-inline-plan|" + nonce).encode("utf-8"))
                     and identity["planSHA256"] == _digest(b"inline-file-cases:empty+4095/v1"),
                     "Plan identity differs from the deterministic actual XCTest")

    files = value["files"]
    contract.require(isinstance(files, list) and len(files) == 2, "Exactly the two ordered inline files required")
    qualified = []
    for index, (row, fixture) in enumerate(zip(files, FIXTURES)):
        _keys(row, FILE_KEYS)
        label, content, name, mime = fixture
        source_key = "apple-inline-" + label + "-" + nonce
        native_owner = native_owners[index]
        contract.require(row["label"] == label and row["sourceKey"] == source_key
                         and row["ownerObjectId"] == native_owner, "Ordered case/source/native-owner binding differs")
        _integer(row["expectedSize"], len(content))
        contract.require(row["expectedContentSHA256"] == _digest(content)
                         and _base64(row["nameUTF8Base64"], 1368) == name.encode("utf-8")
                         and row["mime"] == mime, "Deterministic content or Unicode metadata differs")
        material = _material(["pinkha-native-prepared-migration-intent/v1", identity["accountId"],
                              identity["spaceId"], identity["storeId"], identity["planId"], source_key, "inlineFile"])
        contract.require(row["intentId"] == _digest(material), "Length-prefixed source intent identity differs")
        raw_spec = _base64(row["specBase64"], 16384)
        contract.require(row["specSHA256"] == _digest(raw_spec), "Original specification bytes/hash differ")
        spec = _specification(raw_spec)
        contract.require(spec["ownerObjectId"] == native_owner and isinstance(spec["name"], str)
                         and spec["name"].encode("utf-8") == name.encode("utf-8") and spec["mime"] == mime
                         and spec["contentSHA256"] == _digest(content)
                         and _base64(spec["content"], 5460) == content,
                         "Original specification differs from the exact input bytes/owner")
        reference = None
        for phase, generation, stage, outcome in RECEIPT_PHASES:
            observed = _receipt(row[phase], generation, stage, outcome, runtimes, owners, native_owner)
            if reference is None:
                reference = observed
            contract.require(observed == reference, "Native signed carrier/change/file identity changed across phases")
        current = _readback(row["currentRead"], 1, runtimes, owners, native_owner, reference["fileId"], content, name, mime)
        reopened = _readback(row["reopenedRead"], 2, runtimes, owners, native_owner, reference["fileId"], content, name, mime)
        contract.require(current == reopened, "Ordinary native bytes/metadata/status changed after committed reopen")
        qualified.append(dict(label=label, ownerObjectId=native_owner, sourceKey=source_key,
                              intentId=row["intentId"], specSHA256=row["specSHA256"], **reference,
                              byteCount=len(content), contentSHA256=_digest(content)))
    contract.require(len({row["fileId"] for row in qualified}) == 2
                     and len({row["intentId"] for row in qualified}) == 2,
                     "Two actual file and intent identities must remain distinct")
    # Payload roots are owner-scoped native carriers, not globally unique per-file IDs.
    return dict(status="VALIDATED_OBSERVATIONS_ORIGINAL_XCTEST_REQUIRED", schema_sha256=SCHEMA_SHA256,
                execution_binding=dict(expected_binding), runtime_versions=versions,
                runtime_generations=runtimes, owner_generations=owners, identity=identity,
                files=qualified, receipt_observations=14, ordinary_content_readbacks=4,
                orderly_reopens=2, completed_cleanup=True, limits=dict(LIMITS))
