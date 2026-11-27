"""Package only the frozen Bin read correction and its source evidence."""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "2207b131f45d305ba828c93deb0633e275e59cba"
BRANCH = "codex/chatgpt-wave15-wave2-bin-read-failure-20261127"
DOCS = "docs/validation/20261127-wave2-bin-read-failure/"
SOURCES = {
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyLibraryPresentation.swift": (
        "f0675b0d2a0842ad87670640d5242da82c354aab96056c1b6d23ca8540b3dc17",
        "3dd7517d2ecba44fe7568b16ed005a97489929f4a248c1899ad3d1c1864e66d4"),
    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift": (
        "e46dc67553d9e050c7955958cff56aac559c4d51eaa3b75e379029dd83f8d839",
        "b242b8bdbe9f2c9c10c742d26ffe88b237b797b28dfd600e07b85f4e3c2a5494"),
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryView.swift": (
        "af2b406c5cf80f126e9684a0cc4bb673658329925188e264aa9746eeba4926c0",
        "3791fe7ccadbf5caf4d1a82b1f6cc8d497b5562db1c58ba346803a9ebf43fec1"),
}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def pin(raw): return {"bytes": len(raw), "sha256": sha(raw)}
def encode(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
def require(value, message):
    if not value: raise RuntimeError(message)


parser = argparse.ArgumentParser(description=__doc__)
for role in ("root", "torah"):
    parser.add_argument("--" + role + "-review", type=Path, required=True)
    parser.add_argument("--" + role + "-review-sha256", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
require(not args.output.exists(), "Preserve original source-publication preparations")
files = {}
for path, (old, new) in SOURCES.items():
    before = (HERE / "source" / path).read_bytes()
    candidate = (HERE / "candidate" / path).read_bytes()
    require(sha(before) == old and sha(candidate) == new, "Frozen product or test changed")
    files[path] = candidate
    files[DOCS + "original/" + Path(path).name] = before
reviews = {}
for role in ("root", "torah"):
    raw = getattr(args, role + "_review").read_bytes()
    expected = getattr(args, role + "_review_sha256")
    require(sha(raw) == expected, "Exact independent review changed")
    expected_status = {"root": "SOURCE_REVIEWED_NO_REMAINING_SCOPED_BLOCKER",
                       "torah": "PASS_SOURCE_REVIEW_NOT_COMPILED"}[role]
    require(json.loads(raw).get("status") == expected_status, "Exact scoped source review is incomplete")
    require(all(new in raw.decode() for _, new in SOURCES.values()), "Review must bind all three candidate files")
    files[DOCS + ("root-source-review.json" if role == "root" else "torah-independent-review.json")] = raw
    reviews[role] = expected
for name in ("README.md", "source-inverse.json", "source-inputs.json", "github-source-verification.json",
             "source-retention-prerequisites.json", "view-source-prerequisites.json", "bin_publication_suite.swift",
             "actor-annotation-delta.json", "public-epoch-capture-delta.json",
             "failure-ui-state-delta.json", "root-independent-review.initial03bd.json",
             "root-independent-review.superseded-pending-ui.json",
             "prepare_publication_packet.py", "publish_bin_read_failure.py"):
    files[DOCS + name] = (HERE / name).read_bytes()
for directory in ("prior-review-input", "actor-annotation-input"):
    for name in ("AnyLibraryPresentation.swift", "source-inverse.json"):
        files[DOCS + directory + "/" + name] = (HERE / directory / name).read_bytes()
for name in ("AnyLibraryPresentation.swift", "AnyLibrarySearchPublicationTests.swift", "source-inverse.json"):
    files[DOCS + "epoch-preservation-input/" + name] = (HERE / "epoch-preservation-input" / name).read_bytes()
for name in ("AnyLibraryPresentation.diff", "AnyLibrarySearchPublicationTests.diff", "AnyNativeLibraryView.diff"):
    raw = (HERE / name).read_bytes()
    files[DOCS + name + ".json"] = encode({
        "format": "base64-exact-original-diff", **pin(raw),
        "base64": base64.b64encode(raw).decode(),
        "reason": "Retain exact context whitespace while keeping the original Git whitespace gate",
    })
handoff = {
    "schema": "wave2-native-bin-read-failure-source-handoff/v1",
    "createdAtUTC": datetime.now(timezone.utc).isoformat(),
    "status": "SOURCE_REVIEWED_APP_RUNTIME_NOT_RUN", "base": BASE, "branch": BRANCH,
    "sources": {path: {"originalSHA256": old, "candidateSHA256": new} for path, (old, new) in SOURCES.items()},
    "sourceReviews": reviews,
    "downstreamOwned": True, "retentionMapChanged": False,
    "originalAuthorizedNativeReadStatementSHA256": "63fcd33e2dddc2b6ad6743f8a4567fed18551a4f1bcfbf9c309c9daa66e4e9cd",
    "modelChanges": "refreshBin, read-only failure field and clearing that field at revoke; all other source exact",
    "viewChanges": "Only native Bin List failure/Retry/empty presentation; all other source exact",
    "publicEpochCapturedWithStoreBeforeAwait": True,
    "privateEntryValidatesCapturedEpochBeforeRead": True,
    "readCallbackExplicitlyMainActorAndNonescaping": True,
    "originalSearchMethodsAndHelpersUnchanged": True,
    "focusedModelRegressions": {
        "suite": "AnyLibraryBinPublicationTests", "methodCount": 2, "caseCount": 3,
        "methods": ["failedCurrentBinReadRetiresRowsAndAnExplicitRetryCanRecover",
                    "olderBinCompletionCannotReplaceOrClearANewerRead"],
        "status": "NOT_RUN", "requiresActualMatchingSharedApp": True,
    },
    "existingBinRestoreProofRetained": "5454534733ae7b9a76fe03a9b0f171d5470069067dc09eb4eb16d200e167c5b0",
    "acceptedHierarchyDragOrArchiveRestoreReplay": False,
    "compilerInvocations": 0, "nativeCalls": 0, "cacheWrites": 0, "simulatorOperations": 0,
    "actualUIVisualPhysical": "NOT_RUN",
    "scope": "Current failed Bin read retires prior rows and shows failure/Retry instead of successful-empty; native read and guarded restore remain unchanged",
    "consumerPinsChanged": False,
    "rollback": "Ordinary revert of this isolated correction",
    "files": {name: pin(raw) for name, raw in files.items()},
}
files[DOCS + "handoff.json"] = encode(handoff)
payload = sum(map(len, files.values()))
require(payload <= 1024 * 1024, "Source-only payload exceeds its bounded envelope")
packet = {"schema": "native-bin-read-failure-source-packet/v1", "base": BASE, "branch": BRANCH,
          "files": {name: {**pin(raw), "base64": base64.b64encode(raw).decode()} for name, raw in files.items()}}
raw_packet = gzip.compress(encode(packet), mtime=0)
assembly = {"status": "PACKAGED_NOT_COMMITTED", "base": BASE, "branch": BRANCH,
            "fileCount": len(files), "payloadBytes": payload, "packet": pin(raw_packet),
            "handoffSHA256": sha(files[DOCS + "handoff.json"])}
args.output.mkdir(mode=0o700)
(args.output / "packet.json.gz").write_bytes(raw_packet)
(args.output / "handoff.json").write_bytes(files[DOCS + "handoff.json"])
(args.output / "assembly.json").write_bytes(encode(assembly))
print(json.dumps(assembly, sort_keys=True))
