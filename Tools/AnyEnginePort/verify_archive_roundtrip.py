#!/usr/bin/env python3
"""Read-only postflight for a real Files picker canonical-association roundtrip."""
from __future__ import annotations

import argparse
import base64
import copy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import uuid

import verify_native_test_execution as execution

ROOT = Path(__file__).resolve().parents[2]
METHOD = "NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies"
ATTACHMENT = "native-canonical-archive-roundtrip-receipt"
MAXIMUM_BYTES = 24 * 1024 * 1024
ENVELOPE_KEYS = {"format", "sourceSpaceID", "sourceObjectID", "sourceRootObjectID",
                 "sourceGeneration", "reachableClaimBlockIDs", "claims"}
OPERATION_KEYS = {"version", "operationID", "spaceID", "authorID", "kind",
                  "targetObjectID", "targetBlockID", "providerID", "canonicalRef", "payload", "observed"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json(raw: bytes):
    def pairs(entries):
        result = {}
        for key, value in entries:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("nonfinite_json_number")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_float=Decimal, parse_constant=invalid_constant)


def same_value(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same_value(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same_value(a, b) for a, b in zip(left, right))
    return left == right


def bounded_identity(value):
    return isinstance(value, str) and 0 < len(value.encode("utf-8")) <= 1024 and "\0" not in value


def archive(raw: bytes, expected_block: str, reference: str):
    require(0 < len(raw) <= MAXIMUM_BYTES, "archive_byte_limit")
    envelope = strict_json(raw)
    require(isinstance(envelope, dict) and set(envelope) == ENVELOPE_KEYS and
            envelope["format"] == "pinkha-canonical-archive-v1", "archive_envelope")
    require(all(bounded_identity(envelope[key]) for key in
                ("sourceSpaceID", "sourceObjectID", "sourceRootObjectID")), "archive_native_identity")
    require(re.fullmatch(r"[0-9a-f]{64}", envelope["sourceGeneration"]) is not None, "archive_generation")
    require(envelope["reachableClaimBlockIDs"] == [expected_block], "archive_reachability")
    require(isinstance(envelope["claims"], list) and len(envelope["claims"]) == 1, "exactly_one_live_claim")
    entry = envelope["claims"][0]
    require(isinstance(entry, dict) and set(entry) ==
            {"operation", "creator", "nativeChangeID", "nativeACLHeadID"}, "archive_claim_shape")
    require(all(bounded_identity(entry[key]) for key in
                ("creator", "nativeChangeID", "nativeACLHeadID")), "archive_native_provenance")
    operation = entry["operation"]
    require(isinstance(operation, dict) and set(operation) == OPERATION_KEYS, "operation_shape")
    require(type(operation["version"]) is int and operation["version"] == 1 and
            operation["kind"] == "add" and operation["observed"] == [], "one_unconflicted_add")
    require(re.fullmatch(r"[0-9a-f]{32}", operation["operationID"]) is not None, "operation_identity")
    require(operation["spaceID"] == envelope["sourceSpaceID"] and
            operation["targetObjectID"] == envelope["sourceObjectID"] and
            operation["targetBlockID"] == expected_block and
            operation["authorID"] == entry["creator"], "operation_native_scope")
    require(operation["providerID"] == "sefaria" and operation["canonicalRef"] == reference,
            "operation_canonical_source")
    payload_bytes = base64.b64decode(operation["payload"], validate=True)
    payload = strict_json(payload_bytes)
    require(isinstance(payload, dict) and type(payload.get("version")) is int and
            payload["version"] == 2 and isinstance(payload.get("records"), list) and
            len(payload["records"]) == 1, "canonical_payload_shape")
    record = payload["records"][0]
    require(isinstance(record, dict) and record.get("spaceId") == operation["spaceID"] and
            record.get("objectId") == operation["targetObjectID"] and
            record.get("blockId") == expected_block, "canonical_record_scope")
    item = record.get("item")
    require(isinstance(item, dict) and bounded_identity(item.get("id")) and item.get("kind") == "ref" and
            item.get("role") == "sourceQuote" and item.get("providerID") == "sefaria" and
            item.get("externalID") == reference and item.get("canonicalKey") == reference,
            "canonical_source_quote")
    snapshot = item.get("customMetadata", {}).get("snapshotText")
    require(isinstance(snapshot, str) and snapshot, "canonical_quote_snapshot_missing")
    return envelope, entry, operation, payload, snapshot


def validate_roundtrip(source_bytes: bytes, destination_bytes: bytes, receipt: dict, *,
                       source_cold_bytes: bytes) -> dict:
    require(type(receipt.get("schemaVersion")) is int and receipt["schemaVersion"] == 1 and
            receipt.get("method") == METHOD and receipt.get("coldReopenObserved") is True,
            "ui_receipt_contract")
    scope = receipt.get("scopeUUID")
    require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope, "ui_scope_identity")
    require(receipt.get("sourceFileName") == "canonical-source-" + scope + ".json" and
            receipt.get("destinationFileName") == "canonical-destination-" + scope + ".json" and
            receipt.get("sourceColdFileName") == "canonical-source-cold-" + scope + ".json",
            "ui_export_file_identity")
    source_block, destination_block = receipt.get("sourceBlockID"), receipt.get("destinationBlockID")
    require(bounded_identity(source_block) and bounded_identity(destination_block) and
            source_block != destination_block, "explicit_distinct_block_mapping")
    reference = receipt.get("canonicalReference")
    require(reference == "Genesis 1:1", "unexpected_public_source")
    source, source_entry, source_op, source_payload, source_snapshot = archive(source_bytes, source_block, reference)
    destination, destination_entry, destination_op, destination_payload, destination_snapshot = archive(
        destination_bytes, destination_block, reference)
    source_cold, _, _, _, _ = archive(source_cold_bytes, source_block, reference)
    # Space readiness may be recomputed after importing into another object.
    # Every source claim, payload byte, identity and native provenance must remain exact.
    source_with_current_generation = {**source, "sourceGeneration": source_cold["sourceGeneration"]}
    require(same_value(source_with_current_generation, source_cold),
            "source_canonical_claims_or_provenance_changed_after_import")
    require(source["sourceSpaceID"] == destination["sourceSpaceID"] and
            source["sourceObjectID"] != destination["sourceObjectID"], "distinct_native_documents_same_space")
    require(source_entry["creator"] == destination_entry["creator"] and
            source_op["operationID"] != destination_op["operationID"] and
            source_entry["nativeChangeID"] != destination_entry["nativeChangeID"],
            "import_requires_fresh_native_operation_provenance")
    remapped = copy.deepcopy(source_payload)
    record = remapped["records"][0]
    record["spaceId"] = destination["sourceSpaceID"]
    record["objectId"] = destination["sourceObjectID"]
    record["blockId"] = destination_block
    require(same_value(remapped, destination_payload), "canonical_payload_changed_beyond_explicit_location_map")
    require(source_snapshot.encode("utf-8") == destination_snapshot.encode("utf-8"), "source_snapshot_changed")
    source_hash = digest(source_snapshot.encode("utf-8"))
    require(receipt.get("sourceBodySHA256") == source_hash and
            receipt.get("sourceColdBodySHA256") == source_hash, "source_body_or_canonical_anchor_changed")
    require(type(receipt.get("sourceBodyUTF8Count")) is int and
            receipt["sourceBodyUTF8Count"] == len(source_snapshot.encode("utf-8")), "source_body_size")
    destination_hash = receipt.get("destinationBeforeBodySHA256")
    require(isinstance(destination_hash, str) and re.fullmatch(r"[0-9a-f]{64}", destination_hash) and
            destination_hash == receipt.get("destinationAfterBodySHA256") ==
            receipt.get("destinationColdBodySHA256") and destination_hash != source_hash,
            "destination_body_was_not_preserved")
    require(type(receipt.get("destinationBodyUTF8Count")) is int and receipt["destinationBodyUTF8Count"] > 0,
            "destination_body_size")
    require(receipt.get("mappingRequiredBeforePrepare") is True and
            receipt.get("sourceAssociationCount") == receipt.get("destinationColdAssociationCount") == 1 and
            type(receipt.get("sourceAssociationCount")) is int and
            type(receipt.get("destinationColdAssociationCount")) is int, "explicit_mapping_or_count_missing")
    return {"canonicalReference": reference, "canonicalClaims": 1,
            "sourceFileSHA256": digest(source_bytes), "destinationFileSHA256": digest(destination_bytes),
            "sourceColdFileSHA256": digest(source_cold_bytes), "sourceCanonicalClaimsUnchanged": True,
            "sourcePayloadSHA256": digest(base64.b64decode(source_op["payload"], validate=True)),
            "destinationPayloadSHA256": digest(base64.b64decode(destination_op["payload"], validate=True)),
            "canonicalItemAndUnknownFieldsPreserved": True, "explicitLocationRemapVerified": True,
            "freshNativeOperationProvenance": True,
            "sourceBodySHA256": source_hash, "destinationBodySHA256": destination_hash}

def regular_bytes(path: Path, directory: Path, maximum: int) -> bytes:
    require(path.parent.resolve() == directory.resolve() and not path.is_symlink(), "file_escaped_owned_directory")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                0 < before.st_size <= maximum, "regular_bounded_file_required")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(descriptor)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
                len(raw) == before.st_size, "file_changed_during_read")
        return raw
    finally:
        os.close(descriptor)


def ui_receipt(directory: Path):
    manifest = strict_json((directory / "manifest.json").read_bytes())
    require(isinstance(manifest, list), "attachment_manifest_shape")
    cases = [case for case in manifest if case.get("testIdentifier", "").removesuffix("()") == METHOD]
    require(len(cases) == 1, "exactly_one_original_ui_attachment_case")
    exported_name = re.compile(re.escape(ATTACHMENT) + r"_\d+_[0-9A-Fa-f-]{36}\.json")
    matches = [entry for entry in cases[0].get("attachments", [])
               if entry.get("suggestedHumanReadableName") == ATTACHMENT or
               exported_name.fullmatch(entry.get("suggestedHumanReadableName", ""))]
    require(len(matches) == 1, "exactly_one_original_ui_receipt")
    name = matches[0].get("exportedFileName")
    require(isinstance(name, str) and Path(name).name == name and "/" not in name and "\\" not in name,
            "unsafe_attachment_basename")
    raw = regular_bytes(directory / name, directory, 64 * 1024)
    return strict_json(raw), raw


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attachments", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--simulator-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "scope": "real_files_canonical_archive_roundtrip",
              "fullAcceptance": False, "readOnlyPostflight": True,
              "bodyProofBoundary": "Actual source-bound UI assertions read both native bodies after cold reopen; archive files contain canonical associations, not document bodies.",
              "runnerSHA256": digest(Path(__file__).read_bytes())}
    try:
        from hanlin_fixture_ci import github_context, verify_simulator
        run_id, commit, _ = github_context()
        udid, _, _ = verify_simulator(args.simulator_receipt, run_id)
        record.update(githubRunID=run_id, commit=commit, ownedSimulatorUDID=udid)
        actual = execution.validate(json.loads(args.summary.read_text(encoding="utf-8")),
                                    json.loads(args.tests.read_text(encoding="utf-8")),
                                    "archive-roundtrip", udid)
        matching = [case for case in actual["actualCases"]
                    if re.search(r"(?:^|/)" + re.escape(METHOD) + r"(?:\(|/|$)", case)]
        require(len(matching) == 1, "exactly_one_archive_ui_execution")
        receipt, receipt_bytes = ui_receipt(args.attachments)
        # The app's private runtime and journals are outside Documents. Read only
        # the three unique exports chosen through Files in this disposable account.
        container = Path(subprocess.check_output(
            ["xcrun", "simctl", "get_app_container", udid, "io.pinkha.anynative.dev", "data"],
            text=True, timeout=30).strip()).resolve()
        exports = container / "Documents/Exports"
        require(exports.is_dir() and not exports.is_symlink() and
                exports.resolve().is_relative_to(container), "owned_exports_directory_missing")
        scope = receipt.get("scopeUUID")
        require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope, "ui_scope_identity")
        source_name = "canonical-source-" + scope + ".json"
        destination_name = "canonical-destination-" + scope + ".json"
        source_cold_name = "canonical-source-cold-" + scope + ".json"
        source_bytes = regular_bytes(exports / source_name, exports, MAXIMUM_BYTES)
        destination_bytes = regular_bytes(exports / destination_name, exports, MAXIMUM_BYTES)
        source_cold_bytes = regular_bytes(exports / source_cold_name, exports, MAXIMUM_BYTES)
        checked = validate_roundtrip(source_bytes, destination_bytes, receipt, source_cold_bytes=source_cold_bytes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        originals = args.output.parent / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        for name, raw in ((source_name, source_bytes), (destination_name, destination_bytes),
                          (source_cold_name, source_cold_bytes), ("ui-receipt.json", receipt_bytes)):
            (originals / name).write_bytes(raw)
        record.update(checked, status="PASS", uiMethodExecutions=1,
                      actualMethod=matching[0], uiReceiptSHA256=digest(receipt_bytes),
                      summarySHA256=digest(args.summary.read_bytes()),
                      testTreeSHA256=digest(args.tests.read_bytes()),
                      testSourceSHA256=digest((ROOT / "NativeApp/UITests/NativeLaunchTests.swift").read_bytes()),
                      archiveSourceSHA256=digest((ROOT / "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift").read_bytes()))
    except Exception as error:
        record["error"] = str(error)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
