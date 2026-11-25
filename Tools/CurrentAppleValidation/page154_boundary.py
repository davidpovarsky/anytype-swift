"""Verify privately retained actual Page154 call results; never invoke an engine."""
from __future__ import annotations
import base64
import hashlib
import re
import struct

import contracts as c

FILES = {"preflight": "pinkha-semantic-page154-preflight.pb",
         "nativeReply": "pinkha-semantic-page154-native-reply.json",
         "readback": "pinkha-semantic-page154-readback.pb"}
KEYS = {"_pinkhaTorahState", "_pinkhaTorahCanonicalHash", "_pinkhaTorahProjectionVersion",
        "_pinkhaTorahCacheIntegrity", "_pinkhaTorahCanonicalPropertyKey", "_pinkhaTorahRelatedVersion",
        "_pinkhaTorahReady", "_pinkhaTorahAttachedProperties", "_pinkhaTorahLabels"}
MAXIMUM = 4 * 1024**2


def fields(raw):
    c.require(isinstance(raw, bytes) and len(raw) <= MAXIMUM, "bounded_original_boundary_protobuf")
    rows, offset = [], 0
    def varint():
        nonlocal offset
        value = 0
        for index in range(10):
            c.require(offset < len(raw), "truncated_boundary_varint")
            byte = raw[offset]; offset += 1
            c.require(index < 9 or byte <= 1, "overflow_boundary_varint")
            value |= (byte & 127) << (7 * index)
            if byte < 128: return value
        raise ValueError("oversized_boundary_varint")
    while offset < len(raw):
        tag = varint(); number, wire = tag >> 3, tag & 7
        c.require(0 < number < 2**29 and wire in {0, 1, 2, 5}, "unsupported_boundary_wire_field")
        if wire == 0:
            value = varint()
        else:
            length = varint() if wire == 2 else (8 if wire == 1 else 4)
            c.require(offset + length <= len(raw), "truncated_boundary_field")
            value = raw[offset:offset + length]; offset += length
        rows.append((number, wire, value))
        c.require(len(rows) <= 50000, "boundary_field_limit")
    return rows


def one(rows, number, wire, default=None):
    found = [row for row in rows if row[0] == number]
    c.require(len(found) <= 1 and (not found or found[0][1] == wire), "ambiguous_boundary_field")
    return found[0][2] if found else default


def only(rows, allowed):
    c.require(all((number, wire) in allowed for number, wire, _ in rows), "unknown_boundary_field")


def text_value(raw):
    rows = fields(raw)
    c.require(len(rows) == 1 and rows[0][:2] == (3, 2), "boundary_string_value_required")
    return rows[0][2].decode("utf8")


def projection_value(key, raw):
    rows = fields(raw)
    c.require(len(rows) == 1, "one_projection_value_kind_required")
    number, wire, value = rows[0]
    if key in {"_pinkhaTorahProjectionVersion", "_pinkhaTorahRelatedVersion"}:
        c.require((number, wire) == (2, 1) and struct.unpack("<d", value)[0] == 1,
                  "projection_version_mismatch")
    elif key == "_pinkhaTorahReady":
        c.require((number, wire, value) == (4, 0, 1), "projection_not_ready")
    elif key == "_pinkhaTorahAttachedProperties":
        c.require((number, wire) == (6, 2), "projection_list_required")
        items = fields(value); only(items, {(1, 2)})
        names = [text_value(item[2]) for item in items]
        c.require(len(names) == len(set(names)) and set(names) <= {
            "pinkhaTorahSources", "pinkhaTorahTopics", "pinkhaTorahWords"}, "projection_properties_invalid")
    else:
        value = text_value(raw)
        if key == "_pinkhaTorahState":
            c.require(value == "READY", "projection_state_invalid")
        elif key in {"_pinkhaTorahCanonicalHash", "_pinkhaTorahCacheIntegrity"}:
            c.require(re.fullmatch("[0-9a-f]{64}", value), "projection_hash_invalid")
        elif key == "_pinkhaTorahCanonicalPropertyKey":
            c.require(bool(value), "projection_canonical_key_missing")
        elif key == "_pinkhaTorahLabels":
            c.require(len(value.encode()) <= 2 * 1024**2, "projection_labels_limit")
            labels = c.strict_json(value.encode())
            c.require(isinstance(labels, dict), "projection_labels_object_required")
            for identity, label in labels.items():
                c.require(identity and isinstance(label, dict) and set(label) <= {"he", "en"}
                          and isinstance(label.get("he"), str)
                          and ("en" not in label or isinstance(label["en"], str)), "projection_label_invalid")
        else:
            raise ValueError("unreviewed_projection_key")


def shown(raw, fixture):
    response = fields(raw); only(response, {(1, 2), (2, 2)})
    error = fields(one(response, 1, 2, b""))
    c.require(one(error, 1, 0, 0) == 0, "authoritative_read_failed")
    view = fields(one(response, 2, 2, b""))
    c.require(one(view, 1, 2) == fixture["objectID"].encode(), "foreign_boundary_object")
    target_rows = [fields(value) for number, wire, value in view if (number, wire) == (3, 2)
                   and one(fields(value), 1, 2) == fixture["objectID"].encode()]
    c.require(len(target_rows) == 1, "one_boundary_details_row_required")
    row = target_rows[0]; only(row, {(1, 2), (2, 2)})
    entries = fields(one(row, 2, 2, b"")); only(entries, {(1, 2)})
    details = {}
    for _, _, value in entries:
        entry = fields(value); only(entry, {(1, 2), (2, 2)})
        key = one(entry, 1, 2, b"").decode("utf8"); item = one(entry, 2, 2)
        c.require(key not in details and isinstance(item, bytes), "ambiguous_boundary_map_entry")
        details[key] = item
    c.require(text_value(details.get("id", b"")) == fixture["objectID"]
              and text_value(details.get("spaceId", b"")) == fixture["spaceID"], "foreign_boundary_details")
    blocks = [value for number, wire, value in view if (number, wire) == (2, 2)
              and one(fields(value), 1, 2) == fixture["blockID"].encode()]
    c.require(len(blocks) == 1, "one_boundary_target_block_required")
    return details, blocks[0]


def verify(raw, fixture, capture, native, mounted):
    c.require(set(raw) == set(FILES), "three_actual_boundary_results_required")
    before, before_block = shown(raw["preflight"], fixture)
    after, after_block = shown(raw["readback"], fixture)
    reply = c.strict_json(raw["nativeReply"])
    c.require(isinstance(reply, dict) and set(reply) == {"protocolVersion", "outcome", "receipt", "responseEvent"}
              and reply["protocolVersion"] == 1 and reply["outcome"] == "applied", "original_applied_reply_required")
    c.require(capture.get("applyAttempts") == 1 and capture.get("documentPublications") == 1,
              "one_real_native_apply_and_document_publication_required")
    receipt = reply["receipt"]
    c.require(isinstance(receipt, dict)
              and all(receipt.get(key) == fixture[key] for key in ("spaceID", "objectID", "blockID"))
              and all(receipt.get(key) == value for key, value in capture["native"].items()),
              "native_reply_and_ui_receipt_binding_mismatch")
    encoded = reply["responseEvent"]
    c.require(isinstance(encoded, str), "native_event_base64_required")
    event_raw = base64.b64decode(encoded, validate=True)
    c.require(base64.b64encode(event_raw).decode() == encoded, "native_event_base64_not_canonical")
    event = fields(event_raw); only(event, {(1, 2), (2, 2), (4, 2)})
    c.require(one(event, 2, 2) == fixture["objectID"].encode(), "foreign_native_event_context")
    messages = [fields(value) for number, wire, value in event if (number, wire) == (1, 2)]
    c.require(1 <= len(messages) <= 2 and all(one(message, 132, 2) == fixture["spaceID"].encode()
              for message in messages), "native_event_scope_mismatch")
    projection = {}
    if len(messages) == 2:
        only(messages[0], {(132, 2), (50, 2)})
        amend = fields(one(messages[0], 50, 2, b"")); only(amend, {(1, 2), (2, 2)})
        c.require(one(amend, 1, 2) == fixture["objectID"].encode(), "foreign_native_amendment")
        for number, wire, value in amend:
            if (number, wire) != (2, 2): continue
            entry = fields(value); only(entry, {(1, 2), (2, 2)})
            key = one(entry, 1, 2, b"").decode("utf8"); item = one(entry, 2, 2)
            c.require(key in KEYS and key not in projection and isinstance(item, bytes), "invalid_native_projection_entry")
            projection_value(key, item)
            c.require(key in after, "projection_missing_from_authoritative_readback")
            projection_value(key, after[key])
            c.require(item == after[key], "event_and_authoritative_projection_differ")
            projection[key] = item
        c.require(set(projection) == KEYS, "incomplete_native_projection")
    only(messages[-1], {(132, 2), (10, 2)})
    update = fields(one(messages[-1], 10, 2, b"")); only(update, {(1, 2), (4, 2)})
    c.require(one(update, 1, 2) == fixture["blockID"].encode(), "foreign_native_mark_target")
    wrapper = fields(one(update, 4, 2, b"")); only(wrapper, {(1, 2)})
    mark_bytes = one(wrapper, 1, 2)
    c.require(isinstance(mark_bytes, bytes), "original_native_marks_required")
    before_value = mounted.native_block(before_block, fixture["blockID"], fixture["text"])
    after_value = mounted.native_block(after_block, fixture["blockID"], fixture["text"])
    fixture_before = mounted.native_block(native.decode64(fixture["beforeBlockBase64"]), fixture["blockID"], fixture["text"])
    fixture_after = mounted.native_block(native.decode64(capture["afterBlockBase64"]), fixture["blockID"], fixture["text"])
    c.require(before_value["marks"] == fixture_before["marks"]
              and after_value["marks"] == fixture_after["marks"] == native.marks(mark_bytes),
              "actual_preflight_event_and_post_apply_marks_differ")
    return {"status": "PASS_ORIGINAL_NATIVE_BOUNDARY_COMPARISON", "extraNativeCalls": 0,
            "messageCount": len(messages), "projectionFieldCount": len(projection),
            "preflightProjectionKeys": sorted(KEYS & before.keys()),
            "materializedProjectionKeys": sorted(projection.keys() - before.keys()),
            "readbackProjectionKeys": sorted(KEYS & after.keys()),
            "projectionFieldSHA256": {key: hashlib.sha256(value).hexdigest() for key, value in sorted(projection.items())},
            "eventSHA256": hashlib.sha256(event_raw).hexdigest(),
            "originalResultSHA256": {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()},
            "originalEventPublished": True, "fixtureAndUIReceiptBound": True}
