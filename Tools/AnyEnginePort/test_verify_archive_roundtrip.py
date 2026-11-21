#!/usr/bin/env python3
"""Synthetic verifier controls only; these tests are not mounted UI acceptance."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

import verify_archive_roundtrip as gate


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


class ArchiveRoundtripEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.scope = "00000000-0000-0000-0000-000000000001"
        self.snapshot = "Synthetic quote שלום"
        self.source_block, self.destination_block = "source-block", "destination-block"
        self.item = {"id": "stable-item", "kind": "ref", "role": "sourceQuote",
                     "providerID": "sefaria", "externalID": "Genesis 1:1", "canonicalKey": "Genesis 1:1",
                     "labelHe": "בראשית א א", "labelEn": "Genesis 1:1",
                     "createdAt": "2026-11-21T00:00:00.000Z",
                     "providerPayload": "{\"source\":\"retained public raw payload\"}",
                     "customMetadata": {"snapshotText": self.snapshot, "direction": "rtl"},
                     "futureItem": {"enabled": True, "nested": ["future", 3]}}
        self.source_payload = {"version": 2, "futureEnvelope": {"keep": "yes"},
                               "records": [{"spaceId": "space", "objectId": "source-document",
                                            "blockId": self.source_block, "item": self.item,
                                            "futureRecord": {"preserve": [1, 2, 3]}}]}
        self.destination_payload = copy.deepcopy(self.source_payload)
        self.destination_payload["records"][0].update(objectId="destination-document",
                                                     blockId=self.destination_block)
        self.source = self.envelope("source-document", self.source_block, "a", "source-change", self.source_payload)
        self.destination = self.envelope("destination-document", self.destination_block, "b",
                                         "destination-change", self.destination_payload)
        source_hash = gate.digest(self.snapshot.encode("utf-8"))
        destination_hash = gate.digest(b"Existing destination body")
        self.receipt = {
            "schemaVersion": 1, "method": gate.METHOD, "coldReopenObserved": True, "scopeUUID": self.scope,
            "sourceFileName": "canonical-source-" + self.scope + ".json",
            "destinationFileName": "canonical-destination-" + self.scope + ".json",
            "sourceColdFileName": "canonical-source-cold-" + self.scope + ".json",
            "sourceBlockID": self.source_block, "destinationBlockID": self.destination_block,
            "canonicalReference": "Genesis 1:1", "sourceBodySHA256": source_hash,
            "sourceColdBodySHA256": source_hash, "sourceBodyUTF8Count": len(self.snapshot.encode("utf-8")),
            "destinationBeforeBodySHA256": destination_hash, "destinationAfterBodySHA256": destination_hash,
            "destinationColdBodySHA256": destination_hash, "destinationBodyUTF8Count": 25,
            "mappingRequiredBeforePrepare": True, "sourceAssociationCount": 1, "destinationColdAssociationCount": 1,
        }

    def envelope(self, object_id, block, operation, change, payload):
        return {"format": "pinkha-canonical-archive-v1", "sourceSpaceID": "space",
                "sourceObjectID": object_id, "sourceRootObjectID": object_id + "-root",
                "sourceGeneration": "c" * 64, "reachableClaimBlockIDs": [block],
                "claims": [{"creator": "creator", "nativeChangeID": change, "nativeACLHeadID": "acl-head",
                            "operation": {"version": 1, "operationID": operation * 32, "spaceID": "space",
                                          "authorID": "creator", "kind": "add", "targetObjectID": object_id,
                                          "targetBlockID": block, "providerID": "sefaria",
                                          "canonicalRef": "Genesis 1:1",
                                          "payload": base64.b64encode(encode(payload)).decode(), "observed": []}}]}

    def validate(self):
        return gate.validate_roundtrip(encode(self.source), encode(self.destination), self.receipt,
                                       source_cold_bytes=encode(self.source))

    def set_destination_payload(self, payload):
        self.destination["claims"][0]["operation"]["payload"] = base64.b64encode(encode(payload)).decode()

    def test_exact_mapping_preserves_full_item_and_all_unknown_fields(self):
        result = self.validate()
        self.assertTrue(result["canonicalItemAndUnknownFieldsPreserved"])
        self.assertTrue(result["explicitLocationRemapVerified"])
        self.assertTrue(result["freshNativeOperationProvenance"])

    def test_unknown_field_loss_or_boolean_type_change_is_rejected(self):
        for location in ("envelope", "record", "item"):
            with self.subTest(location=location):
                changed = copy.deepcopy(self.destination_payload)
                if location == "envelope":
                    del changed["futureEnvelope"]
                elif location == "record":
                    del changed["records"][0]["futureRecord"]
                else:
                    changed["records"][0]["item"]["futureItem"]["enabled"] = 1
                self.set_destination_payload(changed)
                with self.assertRaisesRegex(ValueError, "changed_beyond_explicit_location_map"):
                    self.validate()

    def test_payload_scope_must_match_explicit_native_block(self):
        changed = copy.deepcopy(self.destination_payload)
        changed["records"][0]["blockId"] = self.source_block
        self.set_destination_payload(changed)
        with self.assertRaisesRegex(ValueError, "canonical_record_scope"):
            self.validate()

    def test_reused_native_operation_or_change_is_rejected(self):
        for key in ("operationID", "nativeChangeID"):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.destination)
                if key == "operationID":
                    changed["claims"][0]["operation"][key] = "a" * 32
                else:
                    changed["claims"][0][key] = "source-change"
                with self.assertRaisesRegex(ValueError, "fresh_native_operation_provenance"):
                    gate.validate_roundtrip(encode(self.source), encode(changed), self.receipt,
                                            source_cold_bytes=encode(self.source))

    def test_cold_source_body_must_match_canonical_quote_snapshot(self):
        self.receipt["sourceColdBodySHA256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "source_body_or_canonical_anchor_changed"):
            self.validate()

    def test_destination_body_must_remain_exactly_its_original_bytes(self):
        self.receipt["destinationColdBodySHA256"] = self.receipt["sourceBodySHA256"]
        with self.assertRaisesRegex(ValueError, "destination_body_was_not_preserved"):
            self.validate()

    def test_observation_or_implicit_mapping_cannot_satisfy_roundtrip(self):
        for key in ("coldReopenObserved", "mappingRequiredBeforePrepare"):
            with self.subTest(key=key):
                changed = {**self.receipt, key: False}
                with self.assertRaises(ValueError):
                    gate.validate_roundtrip(encode(self.source), encode(self.destination), changed,
                                            source_cold_bytes=encode(self.source))

    def test_cold_source_provenance_must_remain_unchanged(self):
        changed = copy.deepcopy(self.source)
        changed["claims"][0]["nativeChangeID"] = "unexpected-source-change"
        with self.assertRaisesRegex(ValueError, "source_canonical_claims_or_provenance_changed"):
            gate.validate_roundtrip(encode(self.source), encode(self.destination), self.receipt,
                                    source_cold_bytes=encode(changed))

    def test_only_readiness_generation_may_change_in_cold_source_export(self):
        changed = {**self.source, "sourceGeneration": "d" * 64}
        result = gate.validate_roundtrip(encode(self.source), encode(self.destination), self.receipt,
                                         source_cold_bytes=encode(changed))
        self.assertTrue(result["sourceCanonicalClaimsUnchanged"])

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_json_key"):
            gate.strict_json(b'{"claim":"first","claim":"other"}')

    def test_original_read_is_bounded_and_does_not_modify_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = directory / "archive.json"
            raw = encode(self.source)
            path.write_bytes(raw)
            before = path.stat()
            self.assertEqual(gate.regular_bytes(path, directory, gate.MAXIMUM_BYTES), raw)
            after = path.stat()
            self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
            with self.assertRaisesRegex(ValueError, "regular_bounded_file_required"):
                gate.regular_bytes(path, directory, 10)

    def test_export_identity_cannot_point_to_another_account_file(self):
        self.receipt["sourceFileName"] = "../other-account.json"
        with self.assertRaisesRegex(ValueError, "ui_export_file_identity"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
