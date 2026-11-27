from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "publication/packet"
DOCS = Path("docs/validation/20261127-wave2-attachment-test-bridge")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def put(path: Path, raw: bytes) -> None:
    target = PACKET / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw, str(path)
    else:
        target.write_bytes(raw)


def js(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


manifest = json.loads((ROOT / "candidate-manifest.json").read_text())
assert sha((ROOT / "root-independent-review.json").read_bytes()) == "2b5e9a8a586f10985c3dd61a42508533342ff77d220b0a281e3bbf86c8bc719b"
assert sha((ROOT / "torah-independent-review.json").read_bytes()) == "1cef34d85359305443ac80eb9616dd7c03ae68619acd15cdc7b6ddf2c87eb802"
assert sha((ROOT / "candidate-manifest.json").read_bytes()) == "0550eb1491249c3b8879646e5ed873cb0c24ff55025d7253568fa3aac082fd61"
assert manifest["baseCommit"] == "2f9ac20a910d9922e13f8e5d410757604437fcc5"
assert manifest["validatorDefinitionCount"] == 17
assert manifest["qualifiedNextNativeCount"] is None
for item in manifest["files"]:
    raw = (ROOT / "candidate" / item["path"]).read_bytes()
    assert len(raw) == item["bytes"] and sha(raw) == item["sha256"] and blob(raw) == item["gitBlob"]
    put(Path(item["path"]), raw)

inverse = json.loads((ROOT / "source-inverse.json").read_text())
for item in inverse["files"]:
    restored = (ROOT / "candidate" / item["path"]).read_bytes()
    for edit in reversed(item["edits"]):
        offset = edit["candidateOffset"]
        old, new = base64.b64decode(edit["originalBase64"]), base64.b64decode(edit["candidateBase64"])
        assert restored[offset:offset + len(new)] == new
        restored = restored[:offset] + old + restored[offset + len(new):]
    assert sha(restored) == item["beforeSHA256"]
    assert restored == (ROOT / "source" / item["path"]).read_bytes()
    put(DOCS / "originals" / item["path"], restored)

for name in ("README.md", "candidate-manifest.json", "source-inverse.json", "source.patch", "source-binding.json", "root-independent-review.json", "root-review-attempt1.json", "torah-independent-review.json"):
    put(DOCS / name, (ROOT / name).read_bytes())
for p in sorted((ROOT / "reference-inputs").iterdir()):
    if p.is_file():
        put(DOCS / "reference-inputs" / p.name, p.read_bytes())
put(DOCS / "publication/preflight.json", (ROOT / "publication/preflight.json").read_bytes())
put(DOCS / "publication/prepare_packet.py", Path(__file__).read_bytes())

files = []
for p in sorted(PACKET.rglob("*")):
    if p.is_file():
        raw = p.read_bytes()
        raw.decode("utf-8")
        files.append({"path": str(p.relative_to(PACKET)), "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw), "mode": "100644", "type": "blob"})
packet = {"status": "SOURCE_REVIEWED_NOT_COMPILED_NOT_RUN", "parentCommit": manifest["baseCommit"], "parentTree": "6daed15b8e56d7d9b5e54254f2302d1ea9e3b2ac", "changedSources": 2, "newTests": 0, "sourceInputDelta": 2, "qualifiedNativeSourceTotal": None, "actualExecutions": 0, "files": files, "bytesExcludingManifest": sum(x["bytes"] for x in files)}
put(DOCS / "packet-manifest.json", js(packet))
print(json.dumps({"files": len(files) + 1, "changedSources": 2, "bytesExcludingManifest": packet["bytesExcludingManifest"], "packetManifestSHA256": sha((PACKET / DOCS / "packet-manifest.json").read_bytes())}))
