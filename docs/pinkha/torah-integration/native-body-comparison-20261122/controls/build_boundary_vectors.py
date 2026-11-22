#!/usr/bin/env python3
"""New synthetic boundary inputs; never native-export acceptance evidence."""
import base64
import binascii
import io
import json
from pathlib import Path
import struct
import zlib


def zip_bytes(items, *, descriptor=False, extra=b"", flags=0):
    local, central = bytearray(), bytearray()
    for path, body in items:
        name = path.encode("utf-8") if isinstance(path, str) else path
        bit = flags | (8 if descriptor else 0) | (2048 if any(x >= 128 for x in name) else 0)
        codec = zlib.compressobj(wbits=-15)
        compressed = codec.compress(body) + codec.flush()
        crc = binascii.crc32(body)
        offset = len(local)
        local.extend(struct.pack("<I5H3I2H", 0x04034B50, 20, bit, 8, 0, 0,
                                 0 if descriptor else crc, 0 if descriptor else len(compressed),
                                 0 if descriptor else len(body), len(name), len(extra)))
        local.extend(name + extra + compressed)
        if descriptor:
            local.extend(struct.pack("<4I", 0x08074B50, crc, len(compressed), len(body)))
        central.extend(struct.pack("<I6H3I5H2I", 0x02014B50, 20, 20, bit, 8, 0, 0, crc,
                                   len(compressed), len(body), len(name), len(extra), 0, 0, 0, 0, offset))
        central.extend(name + extra)
    return bytes(local + central + struct.pack("<I4H2IH", 0x06054B50, 0, 0, len(items), len(items), len(central), len(local), 0))


def changed(data, offset, value, fmt="<I"):
    data = bytearray(data)
    struct.pack_into(fmt, data, offset, value)
    return bytes(data)


def varint(n):
    result = bytearray()
    while n >= 128:
        result.append((n & 127) | 128)
        n >>= 7
    return bytes(result + bytes([n]))


def field(number, body):
    return varint(number << 3 | 2) + varint(len(body)) + body


def entry(key, value=b""):
    key = key.encode() if isinstance(key, str) else key
    return field(1, key) + field(2, field(3, value))


def structure(*keys):
    return b"".join(field(1, entry(k)) for k in keys)


def wrap(body):
    return field(2, field(2, body))


vectors = []


def vector(name, kind, data, failure=None):
    vectors.append(dict(name=name, kind=kind, bytes=base64.b64encode(data).decode(), failure=failure))


ordinary = zip_bytes([("objects/root.pb", b"original protobuf fixture")])
descriptor = zip_bytes([("objects/root.pb", b"fixture"), ("files/שלום.txt", "שלום English".encode())], descriptor=True)
central = struct.unpack_from("<I", ordinary, len(ordinary) - 6)[0]
vector("ordinary ZIP inventory is accepted", "zip", ordinary)
vector("Go-style data descriptors and UTF-8 member names are accepted", "zip", descriptor)
vector("r14 writer timestamp extra is accepted", "zip", zip_bytes([("objects/root.pb", b"fixture")], extra=struct.pack("<HHBI", 0x5455, 5, 1, 1)))
vector("duplicate ZIP member paths are refused", "zip", zip_bytes([("objects/root.pb", b"one"), ("objects/root.pb", b"two")]), "duplicatePath")
for name, path in [("parent path", "../objects/root.pb"), ("absolute path", "/objects/root.pb"), ("drive path", "C:/objects/root.pb"), ("backslash path", "objects\\root.pb"), ("empty component", "objects//root.pb"), ("NUL path", b"objects/roo\0.pb")]:
    vector(name + " is refused", "zip", zip_bytes([(path, b"fixture")]), "unsafePath")
vector("non UTF-8 name is refused", "zip", zip_bytes([(b"files/\xff.bin", b"fixture")]), "unsafePath")
vector("empty archive cannot attest an object", "zip", zip_bytes([]), "invalidCount")
vector("multi-disk ZIP is unsupported", "zip", changed(ordinary, len(ordinary) - 18, 1, "<H"), "unsupportedZIP")
vector("ZIP64 offset is unsupported", "zip", changed(ordinary, len(ordinary) - 6, 0xFFFFFFFF), "unsupportedZIP")
vector("encrypted member is unsupported", "zip", zip_bytes([("objects/root.pb", b"fixture")], flags=1), "unsupportedZIP")
vector("unknown extra field is unsupported", "zip", zip_bytes([("objects/root.pb", b"fixture")], extra=struct.pack("<HH", 0x9999, 0)), "unsupportedZIP")
vector("appended data invalidates ZIP framing", "zip", ordinary + b"tail", "malformedZIP")
vector("advertised central count cannot hide an entry", "zip", changed(changed(ordinary, len(ordinary)-14, 2, "<H"), len(ordinary)-12, 2, "<H"), "malformedZIP")
wrong_name = bytearray(ordinary); wrong_name[30] = ord("X")
vector("local and central member identities must agree", "zip", bytes(wrong_name), "malformedZIP")
vector("expanded byte budget is enforced before decompression", "zip", changed(ordinary, central + 24, 8 * 1024 * 1024 + 1), "sizeLimit")
vector("archive byte budget is enforced", "zip", bytes(65537), "sizeLimit")
prefix = bytearray(b"X" + ordinary)
struct.pack_into("<I", prefix, len(prefix)-6, central+1)
struct.pack_into("<I", prefix, central+1+42, 1)
vector("unindexed prefix is refused", "zip", bytes(prefix), "unindexedData")
bad_descriptor = bytearray(descriptor)
at = descriptor.index(struct.pack("<I", 0x08074B50))
bad_descriptor[at+4] ^= 1
vector("descriptor CRC must match central identity", "zip", bytes(bad_descriptor), "malformedZIP")

vector("exact distinct Unicode map keys are retained", "map", wrap(field(2, structure("מקור", "English"))))
vector("Unicode-equivalent distinct keys cannot collapse in Swift", "map", wrap(field(2, structure("K", "K"))), "ambiguousMapKey")
vector("composed and decomposed map-key collision is refused", "map", wrap(field(2, structure("é", "e\u0301"))), "ambiguousMapKey")
vector("duplicate native map keys are refused", "map", wrap(field(2, structure("id", "id"))), "ambiguousMapKey")
vector("invalid UTF-8 map key is refused", "map", wrap(field(2, structure(b"\xff"))), "ambiguousMapKey")
vector("block fields cannot collapse Unicode keys", "map", wrap(field(1, field(2, structure("K", "K")))), "ambiguousMapKey")
vector("link fields cannot collapse Unicode keys", "map", wrap(field(1, field(20, field(3, structure("K", "K"))))), "ambiguousMapKey")
value = field(5, structure("K", "K"))
vector("nested dataview filter maps are checked", "map", wrap(field(1, field(21, field(2, field(5, field(4, value)))))), "ambiguousMapKey")
vector("nested custom sort maps are checked", "map", wrap(field(1, field(21, field(2, field(4, field(3, value)))))), "ambiguousMapKey")
vector("deprecated relation defaults preserve map identity", "map", wrap(field(4, field(4, value))), "ambiguousMapKey")
vector("snapshot head-map identities cannot collapse", "map", field(2, field(1, entry("K")) + field(1, entry("K"))), "ambiguousMapKey")
vector("native file-key identities cannot collapse", "map", field(2, field(3, field(2, entry("K")) + field(2, entry("K")))), "ambiguousMapKey")
vector("split singular message fragments are refused", "map", field(2, field(2, field(2, structure("one"))) + field(2, field(2, structure("two")))), "duplicateMessageFragment")
vector("truncated message length is refused", "map", b"\x12\x7f\x00", "malformedWire")
deep = field(3, b"text")
for _ in range(101):
    deep = field(6, field(1, deep))
vector("recursive native values have a depth bound", "map", wrap(field(2, field(1, field(1, b"key") + field(2, deep)))), "depthLimit")

Path(__file__).with_name("boundary-vectors.json").write_text(json.dumps(vectors, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"vectors": len(vectors), "scope": "new synthetic ZIP/map boundaries only; native executions=0"}))
