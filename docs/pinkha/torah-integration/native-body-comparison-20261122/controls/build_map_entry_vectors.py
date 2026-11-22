#!/usr/bin/env python3
"""Cases selected only for the peer-observed map-entry decoder loss."""
import base64
import json
from pathlib import Path


def varint(n):
    result = bytearray()
    while n >= 128:
        result.append((n & 127) | 128)
        n >>= 7
    return bytes(result + bytes([n]))


def field(n, value):
    return varint(n << 3 | 2) + varint(len(value)) + value


def string_map(entry):
    return field(2, field(1, entry))


def value_map(entry):
    return field(2, field(2, field(2, field(1, entry))))


vectors = []
for label, wrap, value in [("string", string_map, b"value"), ("Value", value_map, field(3, b"value"))]:
    key, val = field(1, b"key"), field(2, value)
    for name, entry in [
        ("unknown varint field", key + val + b"\x18\x01"),
        ("unknown message field", key + val + field(3, b"opaque")),
        ("wrong-wire key", b"\x08\x01" + val),
        ("wrong-wire value", key + b"\x10\x01"),
        ("repeated value", key + val + val),
    ]:
        vectors.append({"name": label + " map refuses " + name,
                        "bytes": base64.b64encode(wrap(entry)).decode(), "failure": "unsupportedMapEntry"})
    vectors.append({"name": label + " map retains its supported exact key/value shape",
                    "bytes": base64.b64encode(wrap(key + val)).decode(), "failure": None})
# An unknown field belonging to the actual Value message has UnknownStorage;
# it is not an unsupported field of the enclosing map-entry wrapper.
vectors.append({"name": "ordinary nested Value unknown field remains supported",
                "bytes": base64.b64encode(value_map(field(1, b"key") + field(2, field(3, b"text") + b"\xa0\x06\x01"))).decode(),
                "failure": None})
Path(__file__).with_name("map-entry-vectors.json").write_text(json.dumps(vectors, indent=2) + "\n")
print(json.dumps({"new_controls": len(vectors), "prior_controls_rerun": 0}))
