#!/usr/bin/env python3
"""Audit only the preserved synthetic protobufs; do not open account stores."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "synthetic-page-artifacts"

def varint(raw, index):
    value = shift = 0
    while True:
        byte = raw[index]
        index += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, index
        shift += 7
        if shift >= 70:
            raise ValueError("Invalid protobuf varint")

def fields(raw):
    result, index = {}, 0
    while index < len(raw):
        tag, index = varint(raw, index)
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            value, index = varint(raw, index)
        elif wire == 2:
            size, index = varint(raw, index)
            value = raw[index:index + size]
            if len(value) != size:
                raise ValueError("Truncated protobuf field")
            index += size
        elif wire in (1, 5):
            size = 8 if wire == 1 else 4
            value = raw[index:index + size]
            if len(value) != size:
                raise ValueError("Truncated protobuf number")
            index += size
        else:
            raise ValueError("Unexpected protobuf wire type")
        result.setdefault(number, []).append((wire, value))
    return result

def block(path, block_id):
    response = fields(path.read_bytes())
    view = fields(response[2][0][1])
    matches = [entry[1] for entry in view[2]
               if fields(entry[1])[1][0][1] == block_id.encode("utf-8")]
    if len(matches) != 1:
        raise ValueError("Expected one exact synthetic block")
    return fields(matches[0])

request = json.loads((ARTIFACTS / "capture-applied-request.json").read_text())
before = block(ARTIFACTS / "capture-before-object-show.pb", request["blockID"])
after = block(ARTIFACTS / "capture-after-object-show.pb", request["blockID"])
assert 3 not in before and after[3] == [(2, b"")]
assert {k: v for k, v in before.items() if k not in (3, 14)} == {
    k: v for k, v in after.items() if k not in (3, 14)}
before_text, after_text = fields(before[14][0][1]), fields(after[14][0][1])
assert {k: v for k, v in before_text.items() if k != 3} == {
    k: v for k, v in after_text.items() if k != 3}
assert len(fields(before_text[3][0][1])[1]) == 4
assert len(fields(after_text[3][0][1])[1]) == 5
print(json.dumps({
    "status": "CONFIRMED_ONLY_NON_MARK_DIFFERENCE_IS_EMPTY_RESTRICTIONS_PRESENCE",
    "before_restrictions": "absent",
    "after_restrictions": "present-empty",
    "other_block_fields_byte_identical": True,
    "other_text_fields_byte_identical": True,
    "before_mark_count": 4,
    "after_mark_count": 5,
    "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(ARTIFACTS.iterdir())},
}, sort_keys=True, indent=2))
