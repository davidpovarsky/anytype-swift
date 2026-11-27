"""Package the exact reviewed downstream attachment presentation correction."""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "6581508faffa748ca51d97e6ea51ecf6400fef35"
BRANCH = "codex/chatgpt-wave15-wave2-attachment-storage-20261127"
SOURCE = "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachments.swift"
DOCS = "docs/validation/20261127-wave2-attachment-storage/"
OLD = "b9d51cc5d71665f853e8601585013880a7dcfe1a600ddc7b84b5647f96fcda41"
NEW = "9e88bb9abd3536b76ccde71a102ba88ca82e3a9dd0c27e28850ae79359cfde73"
TORAH_REVIEW = "f58f179dfadc28e2a517d89506c9149a57fe236672164d74f6c3da42656501cd"


def sha(b): return hashlib.sha256(b).hexdigest()
def pin(b): return {"bytes": len(b), "sha256": sha(b)}
def require(value, reason):
    if not value: raise RuntimeError(reason)
def encode(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root-review", type=Path, required=True)
p.add_argument("--root-review-sha256", required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
require(not args.output.exists(), "Retain earlier publication attempts")
old = (HERE / "AnyNativeAttachments.original.swift").read_bytes()
new = (HERE / "AnyNativeAttachments.swift").read_bytes()
require(sha(old) == OLD and sha(new) == NEW, "Frozen product source changed")
root_review = args.root_review.read_bytes()
require(sha(root_review) == args.root_review_sha256 and NEW in root_review.decode(),
        "Exact root review must bind the frozen product")
review = json.loads(root_review)
require(str(review.get("status", "")).startswith("PASS"), "Root source review must be complete")
torah = (HERE / "torah-independent-review.json").read_bytes()
require(sha(torah) == TORAH_REVIEW, "Independent actor/authorization review changed")
files = {SOURCE: new, DOCS + "original/AnyNativeAttachments.swift": old,
         DOCS + "root-source-review.json": root_review,
         DOCS + "torah-independent-review.json": torah}
for name in ("README.md", "source-inverse.json", "source-inputs.json",
             "github-source-verification.json", "origin-read.json",
             "prepare_publication_packet.py", "publish_attachment_storage.py"):
    files[DOCS + name] = (HERE / name).read_bytes()
diff = (HERE / "changes.diff").read_bytes()
files[DOCS + "changes.diff.json"] = encode({
    "format": "base64-exact-original-diff", **pin(diff),
    "base64": base64.b64encode(diff).decode(),
    "reason": "Preserve original context whitespace without changing the Git diff-check gate",
})
for name in ("assembly.json", "prepare_publication_packet.py"):
    files[DOCS + "packaging/attempt1-" + name] = (HERE / "publication1" / name).read_bytes()
handoff = {
    "schema": "wave2-native-attachment-storage-source-handoff/v1",
    "createdAtUTC": datetime.now(timezone.utc).isoformat(),
    "status": "SOURCE_REVIEWED_APP_RUNTIME_NOT_RUN", "base": BASE, "branch": BRANCH,
    "applicationSource": {"path": SOURCE, "classification": "DOWNSTREAM_OWNED", **pin(new)},
    "preimage": pin(old), "introducedBy": "1705d25f415236610e70db210eacd4790115b583",
    "protectedBaseline": "586c98bcc17dee425664224e508fc0e8df277678",
    "presentInProtectedBaseline": False,
    "freshUpstreamDevelop": "d857b23ea540be33d6faab4f7a7a1a260ab578c1",
    "retentionMapChanged": False,
    "sourceReviews": {"root": args.root_review_sha256, "torah": TORAH_REVIEW},
    "existingTypedAPI": "AnyNativeFileDurability.status/retry at exact integrated source6581508f",
    "authority": "Existing mounted owner/current row, account/Space/engine lease, canonical native read/write target proof; one explicit retry approval",
    "acknowledgement": "HTTP204 records request acknowledgement only; separate actual native status supplies visible state",
    "scope": "One downstream presentation file; no Host/Native/editor/SDK/MiniApps/contract change",
    "originalOpenCloseAuthorizationBodiesUnchanged": True,
    "privateNativeDiagnosticDisplayed": False,
    "automaticRetriesOrRowPolling": False,
    "originalStaleStateRepairRetained": "426f17d2f1c491e8aec2535fd114ffa006af7730",
    "newProductRequired": True, "sameTupleOwnedFileFixtureRequired": True,
    "actualXCTestNativeUIVisualPhysical": "NOT_RUN",
    "compilerInvocations": 0, "nativeCalls": 0, "fileUploadsOrRetries": 0,
    "historicalT5OrAcceptedHierarchyDragRerun": False,
    "otherFilesAndBookmarksObligations": "Remain separately recorded in D; this source does not establish add-file/upload or Bookmark mounted acceptance",
    "rollback": "Ordinary revert of this isolated source commit",
    "files": {name: pin(raw) for name, raw in files.items()},
}
files[DOCS + "handoff.json"] = encode(handoff)
payload = sum(map(len, files.values()))
require(payload <= 1024 * 1024, "Source-only payload exceeds authorized envelope")
packet = {"schema": "native-attachment-storage-source-packet/v1", "base": BASE, "branch": BRANCH,
          "files": {name: {**pin(raw), "base64": base64.b64encode(raw).decode()} for name, raw in files.items()}}
data = gzip.compress(encode(packet), mtime=0)
assembly = {"status": "PACKAGED_NOT_COMMITTED", "fileCount": len(files), "payloadBytes": payload,
            "packet": pin(data), "handoffSHA256": sha(files[DOCS + "handoff.json"]),
            "base": BASE, "branch": BRANCH}
args.output.mkdir(mode=0o700)
(args.output / "packet.json.gz").write_bytes(data)
(args.output / "handoff.json").write_bytes(files[DOCS + "handoff.json"])
(args.output / "assembly.json").write_bytes(encode(assembly))
print(json.dumps(assembly, sort_keys=True))
