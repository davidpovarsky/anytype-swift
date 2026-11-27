from __future__ import annotations

import base64
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
ACCESSOR = WORKSPACE / "torah-acceptance-prep/t5-attachment-accessor"
PACKET = ROOT / "publication/packet"
DOCS = Path("docs/validation/20261127-wave2-attachment-upload-ui")
MERGE = "1384176f817605d6d97e07c7a1366a3d5fd8501c"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def write(path: Path, raw: bytes) -> None:
    target = PACKET / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw, str(path)
    else:
        target.write_bytes(raw)


def copied(source: Path, path: Path) -> None:
    write(path, source.read_bytes())


def js(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


original_manifest = json.loads((ROOT / "candidate-manifest.json").read_text())
files = list(original_manifest["files"])
for item in files:
    raw = (ROOT / "candidate" / item["path"]).read_bytes()
    assert len(raw) == item["bytes"] and sha(raw) == item["sha256"]
    assert blob(raw) == item["gitBlob"]
    write(Path(item["path"]), raw)

accessor = json.loads((ACCESSOR / "source-inverse.json").read_text())
document_path = Path(accessor["path"])
before = (ACCESSOR / "source" / document_path).read_bytes()
after = (ACCESSOR / "candidate" / document_path).read_bytes()
insertion = accessor["insertion"].encode()
assert after.count(insertion) == 1 and after.replace(insertion, b"", 1) == before
assert len(after) - len(before) == 204
assert sha(after) == accessor["after"]["sha256"] and sha(before) == accessor["before"]["sha256"]
assert blob(after) == accessor["after"]["gitBlob"]
write(document_path, after)
files.append({"path": str(document_path), "bytes": len(after), "sha256": sha(after), "gitBlob": blob(after), "change": "modified", "originalSHA256": sha(before), "originalCommit": accessor["baseCommit"], "insertionBytes": 204})

inverse = json.loads((ROOT / "source-inverse.json").read_text())
for item in inverse["files"]:
    candidate = (ROOT / "candidate" / item["path"]).read_bytes()
    restored = candidate
    for edit in reversed(item["edits"]):
        off = edit["candidateOffset"]
        old = base64.b64decode(edit["originalBase64"])
        new = base64.b64decode(edit["candidateBase64"])
        assert restored[off:off + len(new)] == new
        restored = restored[:off] + old + restored[off + len(new):]
    assert sha(restored) == item["originalSHA256"]
    assert restored == (ROOT / "source" / Path(item["path"]).name).read_bytes()
    write(DOCS / "originals" / Path(item["path"]).name, restored)
write(DOCS / "originals" / "AnyDocumentPresentation.swift", before)
offset = after.index(insertion)
inverse["files"].append({"path": str(document_path), "originalSHA256": sha(before), "candidateSHA256": sha(after), "status": "EXACT_FULL_SOURCE_RESTORED", "edits": [{"originalOffset": offset, "originalLength": 0, "candidateOffset": offset, "candidateLength": len(insertion), "originalBase64": "", "candidateBase64": base64.b64encode(insertion).decode()}]})
inverse["status"] = "PASS_EXACT_THREE_ORIGINALS_RESTORED_SOURCE_ONLY"
write(DOCS / "source-inverse.json", js(inverse))

manifest = dict(original_manifest)
manifest.update({"status": "SOURCE_REVIEWED_NOT_COMPILED_NOT_RUN", "publicationParent": MERGE, "publicationParentTree": "c8d94e00158db1a25fa8f035fb48ce54b66d4a29", "parentDependencies": ["e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff", "21d63bef8950f8b927f0d8d3b4b052758bc98fcb"], "files": files, "documentAccessor": {"bytesAdded": 204, "sourceSHA256": sha(after), "lifetimePreimageSHA256": sha(before), "sourceReview": "root-source-review-v2.json"}, "rootReviewSHA256": "9ac7e4b7613ebe13c98b2b0ab96f82eac2345e05572cab42eb446b260039c53e", "runtimeAdmission": False, "hostACKRecoverySuccessorConsumed": False, "unknownJournalNoRecordedMeansNoPriorUpload": False})
write(DOCS / "candidate-manifest.json", js(manifest))
write(DOCS / "source.patch", (ROOT / "source.patch").read_bytes() + (ACCESSOR / "source.patch").read_bytes())

for name in ("root-ui-review-v1.json", "root-source-review-v2.json", "editor-storage-source-review.json", "source-binding-qualified.json", "source-boundary-additional-reads-qualified.json", "wave1-source-intake.json", "engine-namespace-correction.json", "store-comment-correction.json", "root-ui-corrections.patch", "caller-snapshot-proposal.md", "integration-map.md"):
    copied(ROOT / name, DOCS / name)
copied(ROOT / "candidate-manifest.json", DOCS / "reviewed-four-source-manifest.json")
for dirname in ("review-v1", "review-v2-ui-before-root-findings"):
    for p in sorted((ROOT / dirname).rglob("*")):
        if p.is_file():
            copied(p, DOCS / dirname / p.relative_to(ROOT / dirname))
for name in ("README.md", "source-inverse.json", "source.patch"):
    copied(ACCESSOR / name, DOCS / "document-accessor" / name)
for name in ("preflight.json", "dependency-merge-tree-proof.json"):
    copied(ROOT / "publication" / name, DOCS / "publication" / name)
for name in ("merge-create-tree-input.json", "merge-create-tree-result.json", "merge-create-commit-input.json", "merge-create-commit-result.json", "merge-commit.primary.json"):
    copied(ROOT / "publication/api" / name, DOCS / "publication/api" / name)
copied(ROOT / "wave1-source/docs/validation/20261127-ordinary-file-attachment-source/workflow-trigger-review.json", DOCS / "publication" / "integration-workflow-original-audit.json")
copied(ROOT / "publication/policy/AGENTS.md", DOCS / "publication/policy/AGENTS.original.md")
copied(ROOT / "publication/policy/UPSTREAM_INTEGRITY_POLICY.md", DOCS / "publication/policy/UPSTREAM_INTEGRITY_POLICY.original.md")
copied(ROOT / "publication/README.md", DOCS / "README.md")
copied(Path(__file__), DOCS / "publication/prepare_packet.py")

all_files = []
for p in sorted(PACKET.rglob("*")):
    if p.is_file():
        raw = p.read_bytes()
        raw.decode("utf-8")
        all_files.append({"path": str(p.relative_to(PACKET)), "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw), "mode": "100644", "type": "blob"})
packet_manifest = {"status": "FROZEN_SOURCE_PACKET_NOT_RUNTIME_ACCEPTANCE", "parentCommit": MERGE, "sourceFiles": 5, "sourceMethodsDeclared": 3, "sourceCasesDeclared": 4, "testsExecuted": 0, "files": all_files, "totalBytesExcludingThisManifest": sum(x["bytes"] for x in all_files)}
write(DOCS / "packet-manifest.json", js(packet_manifest))
print(json.dumps({"files": len(all_files) + 1, "sourceFiles": 5, "bytesExcludingManifest": packet_manifest["totalBytesExcludingThisManifest"], "packetManifestSHA256": sha((PACKET / DOCS / "packet-manifest.json").read_bytes()), "candidateManifestSHA256": sha((PACKET / DOCS / "candidate-manifest.json").read_bytes()), "threeSourceInverseSHA256": sha((PACKET / DOCS / "source-inverse.json").read_bytes())}))
