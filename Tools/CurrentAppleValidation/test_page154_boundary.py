"""Pure collector controls from the unchanged native fixture; no engine or Apple run."""
import base64
import copy
import json
from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Tools/PinkhaSemanticAnchorWire/apple_consumer"))
sys.path.insert(0, str(ROOT / "Tools/PinkhaSemanticAnchorWire/apple_mounted"))
import page154_boundary as boundary
import consumer_contract as native
import mounted_contract as mounted


def varint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128); value >>= 7
    result.append(value)
    return bytes(result)


def packed(rows):
    return b"".join(varint(number << 3 | wire) +
        (varint(value) if wire == 0 else (varint(len(value)) if wire == 2 else b"") + value)
        for number, wire, value in rows)


def string(value):
    return packed([(3, 2, value.encode())])


def replace(rows, field, data):
    return [(n, w, data if n == field else v) for n, w, v in rows]


class Page154BoundaryControls(unittest.TestCase):
    def setUp(self):
        directory = ROOT / "Modules/ProtobufMessages/Tests/ProtobufMessagesTests/Fixtures/NativePage"
        self.raw = {"preflight": (directory / "capture-before-object-show.pb").read_bytes(),
                    "nativeReply": (directory / "capture-applied-response.json").read_bytes(),
                    "readback": (directory / "capture-after-object-show.pb").read_bytes()}
        self.reply = json.loads(self.raw["nativeReply"])
        receipt = self.reply["receipt"]
        self.fixture = {key: receipt[key] for key in ("spaceID", "objectID", "blockID")}
        _, before = boundary.shown(self.raw["preflight"], self.fixture)
        _, after = boundary.shown(self.raw["readback"], self.fixture)
        body = boundary.fields(boundary.one(boundary.fields(before), 14, 2))
        self.fixture.update(text=boundary.one(body, 1, 2).decode(), beforeBlockBase64=base64.b64encode(before).decode())
        self.capture = {"native": {key: receipt[key] for key in (
            "anchorID", "marker", "changeID", "nativeChangeSHA256", "beforeTextMarksSHA256", "afterTextMarksSHA256")},
            "afterBlockBase64": base64.b64encode(after).decode(), "applyAttempts": 1, "documentPublications": 1}
        self.values = {"_pinkhaTorahState": string("READY"),
            "_pinkhaTorahReady": packed([(4, 0, 1)]),
            "_pinkhaTorahProjectionVersion": packed([(2, 1, struct.pack("<d", 1))]),
            "_pinkhaTorahRelatedVersion": packed([(2, 1, struct.pack("<d", 1))]),
            "_pinkhaTorahCanonicalHash": string("a" * 64),
            "_pinkhaTorahCacheIntegrity": string("b" * 64),
            "_pinkhaTorahCanonicalPropertyKey": string("original-canonical-key"),
            "_pinkhaTorahAttachedProperties": packed([(6, 2, b"")]),
            "_pinkhaTorahLabels": string("{}")}

    def with_projection(self, raw, values):
        response = boundary.fields(raw)
        view = boundary.fields(boundary.one(response, 2, 2))
        changed = []
        for n, w, v in view:
            if (n, w) == (3, 2) and boundary.one(boundary.fields(v), 1, 2) == self.fixture["objectID"].encode():
                row = boundary.fields(v)
                entries = [item for item in boundary.fields(boundary.one(row, 2, 2))
                           if boundary.one(boundary.fields(item[2]), 1, 2).decode() not in boundary.KEYS]
                entries += [(1, 2, packed([(1, 2, key.encode()), (2, 2, value)])) for key, value in sorted(values.items())]
                v = packed(replace(row, 2, packed(entries)))
            changed.append((n, w, v))
        return packed(replace(response, 2, packed(changed)))

    def materialized(self, values=None):
        values = self.values if values is None else values
        raw = dict(self.raw)
        raw["preflight"] = self.with_projection(raw["preflight"], {})
        raw["readback"] = self.with_projection(raw["readback"], values)
        event = boundary.fields(base64.b64decode(self.reply["responseEvent"]))
        entries = [(2, 2, packed([(1, 2, key.encode()), (2, 2, value)])) for key, value in sorted(values.items())]
        amendment = packed([(1, 2, self.fixture["objectID"].encode()), *entries])
        message = packed([(132, 2, self.fixture["spaceID"].encode()), (50, 2, amendment)])
        reply = copy.deepcopy(self.reply)
        reply["responseEvent"] = base64.b64encode(packed([(1, 2, message), *event])).decode()
        raw["nativeReply"] = json.dumps(reply).encode()
        return raw

    def verify(self, raw, capture=None):
        return boundary.verify(raw, self.fixture, self.capture if capture is None else capture, native, mounted)

    def test_original_single_event_and_new_projection_require_real_readback(self):
        self.assertEqual(self.verify(self.raw)["messageCount"], 1)
        result = self.verify(self.materialized())
        self.assertEqual(result["projectionFieldCount"], 9)
        self.assertEqual(result["materializedProjectionKeys"], sorted(boundary.KEYS))
        self.assertEqual(result["extraNativeCalls"], 0)

    def test_projection_missing_or_changed_in_authoritative_readback_is_rejected(self):
        for key in sorted(self.values):
            for missing in (False, True):
                with self.subTest(key=key, missing=missing):
                    raw = self.materialized(); values = dict(self.values)
                    if missing: del values[key]
                    else: values[key] = string("changed")
                    raw["readback"] = self.with_projection(self.raw["readback"], values)
                    with self.assertRaises(ValueError): self.verify(raw)

    def test_equal_but_invalid_projection_is_rejected(self):
        for key, value in [("_pinkhaTorahState", string("UNSUPPORTED")),
                           ("_pinkhaTorahReady", packed([(4, 0, 0)])),
                           ("_pinkhaTorahProjectionVersion", packed([(2, 1, struct.pack("<d", 2))])),
                           ("_pinkhaTorahCacheIntegrity", string("A" * 64)),
                           ("_pinkhaTorahCanonicalPropertyKey", string("")),
                           ("_pinkhaTorahLabels", string('{"id":{"en":"missing-he"}}')),
                           ("_pinkhaTorahAttachedProperties", packed([(6, 2, packed([(1, 2, string("foreign"))]))]))]:
            with self.subTest(key=key):
                values = dict(self.values); values[key] = value
                with self.assertRaises(ValueError): self.verify(self.materialized(values))

    def test_missing_original_foreign_object_and_extra_publication_are_rejected(self):
        for role in boundary.FILES:
            raw = self.materialized(); del raw[role]
            with self.assertRaises(ValueError): self.verify(raw)
        raw = self.materialized(); response = boundary.fields(raw["readback"])
        view = boundary.fields(boundary.one(response, 2, 2))
        raw["readback"] = packed(replace(response, 2, packed(replace(view, 1, b"foreign-root"))))
        with self.assertRaises(ValueError): self.verify(raw)
        for name in ("applyAttempts", "documentPublications"):
            capture = copy.deepcopy(self.capture); capture[name] = 2
            with self.assertRaises(ValueError): self.verify(self.materialized(), capture)
        raw = self.materialized(); reply = json.loads(raw["nativeReply"])
        reply["receipt"]["spaceID"] += "-foreign"; raw["nativeReply"] = json.dumps(reply).encode()
        with self.assertRaises(ValueError): self.verify(raw)


if __name__ == "__main__":
    unittest.main()
