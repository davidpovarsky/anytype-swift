from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "publication/packet"
DOCS = Path("docs/validation/20261127-wave2-attachment-tier")
BRANCH = "codex/chatgpt-wave15-wave2-attachment-tier-20261127"
ROOT_REVIEW = "b6f996cc2113af5d4c6bfe6401dd1293a020c0bc4c7140efb8fe2d804b590feb"
TORAH_REVIEW = "36165f05e27fcb065c451d48a25350fc2b81a4759df13a06b9d60f30e7d2d3ba"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def js(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def put(path: Path, raw: bytes) -> None:
    target = PACKET / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw, str(path)
    else:
        target.write_bytes(raw)


def copy(source: Path, destination: Path) -> None:
    put(destination, source.read_bytes())


manifest = json.loads((ROOT / "candidate-manifest.json").read_text())
assert sha((ROOT / "candidate-manifest.json").read_bytes()) == "a20e2b8b377a008c709a03d1c76e61eee5e642033b60f05d270bfdb6e95f40e4"
assert sha((ROOT / "root-independent-review.json").read_bytes()) == ROOT_REVIEW
assert sha((ROOT / "torah-independent-review.json").read_bytes()) == TORAH_REVIEW
assert manifest["baseCommit"] == "bd684a8ad5b12cc2eef3b14d4fb64a34bd98f304"
assert manifest["baseTree"] == "42049d3ea1d63f80d29f1b894407ab4cf2fe97fc"
assert manifest["metadataSuite"]["resultingMethods"] == 5
assert manifest["metadataSuite"]["resultingDeclaredCases"] == 24
assert manifest["metadataSuite"]["actualResults"] is None
for item in manifest["files"]:
    raw = (ROOT / "candidate" / item["path"]).read_bytes()
    assert len(raw) == item["candidate"]["bytes"]
    assert sha(raw) == item["candidate"]["sha256"]
    assert blob(raw) == item["candidate"]["gitBlob"]
    put(Path(item["path"]), raw)

inverse = json.loads((ROOT / "source-inverse.json").read_text())
for item in inverse["files"]:
    restored = (ROOT / "candidate" / item["path"]).read_bytes()
    for edit in reversed(item["inverse"]):
        offset = edit["candidateOffset"]
        original = base64.b64decode(edit["originalBase64"])
        candidate = base64.b64decode(edit["candidateBase64"])
        assert restored[offset:offset + len(candidate)] == candidate
        restored = restored[:offset] + original + restored[offset + len(candidate):]
    assert restored == (ROOT / "source" / item["path"]).read_bytes()
    assert sha(restored) == item["original"]["sha256"]
    put(DOCS / "originals" / Path(item["path"]).name, restored)

for name in (
    "README.md", "proposal.md", "proposal-handoff.json", "candidate-manifest.json",
    "source-inverse.json", "source.patch", "prepare_candidate.py", "new-test-methods.swift",
    "root-independent-review.json", "torah-independent-review.json", "caller-search-proof.json",
    "base-ui-tree.primary.json", "wire-source-binding.json", "w1-wire-and-transport-comments.json",
    "primary-input-0.json", "primary-input-1.json",
):
    copy(ROOT / name, DOCS / name)
for name, expected in (
    ("files.go", "c9aa3e006f8fcc24bd129fbe9e41eabe7bd6b3d3c3675125370d83d75ddf65ea"),
    ("handlers_files.go", "a7e299282612adcdb76f2b8f3c64553a92770edcf6ba2bab4ab91e3bb9786658"),
):
    raw = (ROOT / "wire-source" / name).read_bytes()
    assert sha(raw) == expected
    put(DOCS / "wire-source" / name, raw)

# The exact authoritative sources and bounded per-blob caller proof are retained.
# No needless duplicate of all 71 unchanged package source bodies is published.
prior = ROOT.parent / "attachment-upload-ui/publication/packet/docs/validation/20261127-wave2-attachment-upload-ui/publication/integration-workflow-original-audit.json"
audit = json.loads(prior.read_text())
assert sha(prior.read_bytes()) == "51921c475999cc4032e1c5ee0248bb12f9d75264115fbde91fea1aa90ab4df87"
assert audit["workflowCount"] == 83
triggered = [item for item in audit["workflows"] if re.search(r"(?m)^\s*(push|create)\s*:", item["triggerSource"])]
assert len(triggered) == 5
filters = ["codex/any-engine-port-20261119", "pinkha/torah-associations-native-ux-persistence-localization-2026-10-20", "pinkha/*", "pinkha/torah-functional-ui-single-device-2026-10-18", "pinkha/upstream-u10-validation-2026-10-18"]
assert all(not fnmatch.fnmatchcase(BRANCH, pattern) for pattern in filters)
assert all(any(pattern in item["triggerSource"] for pattern in filters) for item in triggered)
preflight = json.loads((ROOT / "publication/preflight.json").read_text())
preflight["awaitsFinalRootSourceReview"] = False
preflight["rootReviewSHA256"] = ROOT_REVIEW
preflight["torahReviewSHA256"] = TORAH_REVIEW
preflight["workflowAuditReuse"]["exactFivePushFilters"] = filters
preflight["workflowAuditReuse"]["createTriggerCount"] = 0
put(DOCS / "publication/preflight.json", js(preflight))
copy(prior, DOCS / "publication/integration-workflow-original-audit.json")
copy(ROOT / "publication/workflow-preflight-reused.json", DOCS / "publication/workflow-preflight-reused.json")
for name in ("owned-ref-absent.primary.json", "default-ref.primary.json"):
    copy(ROOT / "publication/api" / name, DOCS / "publication" / name)
copy(ROOT.parent / "attachment-test-bridge/publication/publication-result.json", DOCS / "prior-bridge-publication.json")
copy(ROOT.parent / "attachment-metadata-projection/publication/publication-result.json", DOCS / "prior-metadata-publication.json")
copy(Path(__file__), DOCS / "publication/prepare_packet.py")

entries = []
for path in sorted(PACKET.rglob("*")):
    if not path.is_file(): continue
    raw = path.read_bytes()
    raw.decode("utf-8")
    entries.append({"path": str(path.relative_to(PACKET)), "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw), "mode": "100644", "type": "blob"})
packet = {"status": "SOURCE_REVIEWED_NOT_COMPILED_NOT_RUN", "parentCommit": manifest["baseCommit"], "parentTree": manifest["baseTree"], "ownedBranch": BRANCH, "sourceFiles": 2, "metadataMethods": 5, "metadataDeclaredCases": 24, "storeMethodsUnchanged": 3, "storeDeclaredCasesUnchanged": 4, "actualExecutions": 0, "files": entries, "bytesExcludingManifest": sum(item["bytes"] for item in entries)}
put(DOCS / "packet-manifest.json", js(packet))
all_entries = []
for path in sorted(PACKET.rglob("*")):
    if path.is_file():
        raw = path.read_bytes()
        all_entries.append({"path": str(path.relative_to(PACKET)), "mode": "100644", "type": "blob", "content": raw.decode()})
out = ROOT / "publication/api"
out.mkdir(parents=True, exist_ok=True)
expected = [{"path": item["path"], "mode": item["mode"], "type": item["type"], "gitBlob": blob(item["content"].encode()), "sha256": sha(item["content"].encode()), "bytes": len(item["content"].encode())} for item in all_entries]
(out / "expected-files.json").write_bytes(js(expected))
chunks = []; current = []; total = 0
for item in all_entries:
    cost = len(js(item))
    if current and total + cost > 90000:
        chunks.append(current); current = []; total = 0
    current.append(item); total += cost
if current: chunks.append(current)
for index, chunk in enumerate(chunks):
    target = out / "tree-input-chunks" / f"{index:02}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(js(chunk))
print(json.dumps({"files": len(all_entries), "sourceFiles": 2, "newDocs": len(all_entries) - 2, "bytesExcludingManifest": packet["bytesExcludingManifest"], "packetManifestSHA256": sha((PACKET / DOCS / "packet-manifest.json").read_bytes()), "chunks": len(chunks)}))
