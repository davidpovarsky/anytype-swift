from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPLOAD = ROOT.parent / "attachment-upload-ui"
PACKET = ROOT / "publication/packet"
DOCS = Path("docs/validation/20261127-wave2-attachment-metadata")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def put(path: Path, raw: bytes) -> None:
    p = PACKET / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        assert p.read_bytes() == raw, str(path)
    else:
        p.write_bytes(raw)


def copy(source: Path, destination: Path) -> None:
    put(destination, source.read_bytes())


def js(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


manifest = json.loads((ROOT / "candidate-manifest.json").read_text())
assert sha((ROOT / "root-independent-review.json").read_bytes()) == "3bde04e7706ab814ed00ee5f2e2dac2d6dde0c485def5358ab648fd17ebf603f"
assert sha((ROOT / "torah-independent-review.json").read_bytes()) == "eb060bc06e9ceee995c1ab6eeeca88c6e5171e10d7947299f0095a35bd545134"
assert manifest["baseCommit"] == "f731e30409b7b479d9ed5e87280624485c181da8"
assert manifest["tests"]["methods"] == 3 and manifest["tests"]["declaredCases"] == 13
assert manifest["tests"]["actualExecutions"] == 0
for item in manifest["files"]:
    raw = (ROOT / "candidate" / item["path"]).read_bytes()
    assert len(raw) == item["bytes"] and sha(raw) == item["sha256"] and blob(raw) == item["gitBlob"]
    put(Path(item["path"]), raw)

inverse = json.loads((ROOT / "source-inverse.json").read_text())
for item in inverse["files"]:
    raw = (ROOT / "candidate" / item["path"]).read_bytes()
    restored = raw
    for edit in reversed(item["edits"]):
        offset = edit["candidateOffset"]
        old, new = base64.b64decode(edit["originalBase64"]), base64.b64decode(edit["candidateBase64"])
        assert restored[offset:offset + len(new)] == new
        restored = restored[:offset] + old + restored[offset + len(new):]
    assert sha(restored) == item["originalSHA256"]
    assert restored == (ROOT / "source" / item["path"]).read_bytes()
    put(DOCS / "originals" / Path(item["path"]).name, restored)

for name in ("README.md", "candidate-manifest.json", "source-inverse.json", "source.patch", "source-binding.json", "torah-independent-review.json", "root-independent-review.json"):
    copy(ROOT / name, DOCS / name)

up = "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyNativeFileUploader.swift"
uploader = UPLOAD / "wave1-source" / up
raw = uploader.read_bytes()
assert sha(raw) == "83e4618ee93a04ce407a62926a0bffbb1752756a59b38e6e5e5d636bad9138a6"
copy(uploader, DOCS / "primary-contracts" / "AnyNativeFileUploader.swift")
bindings = [{"path": "primary-contracts/AnyNativeFileUploader.swift", "sourceURL": "https://github.com/davidpovarsky/anytype-swift/blob/e96ba072887e7581ed6de20fdd81e0897c83763d/" + up, "gitBlob": blob(raw), "sha256": sha(raw), "bytes": len(raw)}]
contract_path = "docs/architecture/ordinary-file-attachment-contract-20261127.md"
contract = (UPLOAD / "wave1-source" / contract_path).read_bytes()
assert sha(contract) == "877f25249eea3ec03ee96d6d956b817326a1f349c6b95201ff44362687ef8ff3"
put(DOCS / "primary-contracts/ordinary-file-attachment-contract-20261127.md", contract)
bindings.append({"path": "primary-contracts/ordinary-file-attachment-contract-20261127.md", "sourceURL": "https://github.com/davidpovarsky/anytype-swift/blob/e96ba072887e7581ed6de20fdd81e0897c83763d/" + contract_path, "gitBlob": blob(contract), "sha256": sha(contract), "bytes": len(contract)})
observed = json.loads((UPLOAD / "source-boundary-additional-reads-qualified.json").read_text())
for item in observed["files"]:
    if not item["path"].startswith("projection-source/"):
        continue
    raw = (UPLOAD / item["path"]).read_bytes()
    assert sha(raw) == item["sha256"] and blob(raw) == item["gitBlob"]
    destination = Path("primary-contracts") / Path(item["path"]).name
    put(DOCS / destination, raw)
    bindings.append({"path": str(destination), "sourceURL": item["url"], "gitBlob": blob(raw), "sha256": sha(raw), "bytes": len(raw)})
put(DOCS / "primary-contracts/source-bindings.json", js({"sourceOnly": True, "files": bindings, "nativeListInlineRequiredness": "UNCONFIRMED_NO_CHANGE", "SDKChanges": False, "transportChanges": False}))
copy(UPLOAD / "publication/d-files-source-addendum.json", DOCS / "prior-upload-d-addendum.json")
copy(UPLOAD / "publication/publication-result.json", DOCS / "prior-upload-publication.json")
copy(ROOT / "publication/preflight.json", DOCS / "publication/preflight.json")
copy(Path(__file__), DOCS / "publication/prepare_packet.py")

entries = []
for p in sorted(PACKET.rglob("*")):
    if p.is_file():
        raw = p.read_bytes()
        raw.decode("utf-8")
        entries.append({"path": str(p.relative_to(PACKET)), "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw), "mode": "100644", "type": "blob"})
packet = {"status": "SOURCE_REVIEWED_NOT_COMPILED_NOT_RUN", "parentCommit": manifest["baseCommit"], "parentTree": "180fe9995d8f594cfc7f10f1e7f02c3433da8e2e", "sourceFiles": 2, "actualExecutions": 0, "files": entries, "bytesExcludingManifest": sum(x["bytes"] for x in entries)}
put(DOCS / "packet-manifest.json", js(packet))
print(json.dumps({"files": len(entries) + 1, "sourceFiles": 2, "bytesExcludingManifest": packet["bytesExcludingManifest"], "packetManifestSHA256": sha((PACKET / DOCS / "packet-manifest.json").read_bytes())}))
