"""Local source/evidence packaging only. Never calls Git, a compiler or a host."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
PACKET = ROOT / "publication-preparation" / "packet"
PREFIX = "docs/validation/20261127-wave2-native-bookmark-mounted"
AUTHORING_BASE = "5a45fe4af2c4601faad181f81d391057c1237654"
BASE = "a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd"
BASE_TREE = "2adebea229e42c5ff56e50aaf0adebbacfbc4c41"
BRANCH = "codex/chatgpt-wave15-wave2-native-bookmark-mounted-20261127"
REPO = "davidpovarsky/anytype-swift"
SOURCES = {
    "NativeApp/Sources/AnyNativeApp.swift": "081230a8b5b2c4c032f379a03e7a29076d4c7c3f044e1d6361d52e3cd48065e0",
    "NativeApp/Sources/NativeCustomTypeFixture.swift": "fdac35c51f6a2af10c75230360c3c2c5032e9a2c9c898625f78afc405778aab6",
    "NativeApp/UITests/NativeLaunchTests.swift": "e06c55a6ed9dd6153f8aabd528f0c225246ec08da96bb515431477c234bdc03c",
}
sha = lambda b: hashlib.sha256(b).hexdigest()
blob = lambda b: hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
encode = lambda v: (json.dumps(v, ensure_ascii=False, indent=2) + "\n").encode()

assert len(sys.argv) == 3, "prepare_publication_packet.py <peer-review-path> <peer-review-sha256>"
peer_path = Path(sys.argv[1]).resolve()
peer_bytes = peer_path.read_bytes()
assert len(sys.argv[2]) == 64 and sha(peer_bytes) == sys.argv[2]
json.loads(peer_bytes)
for expected in SOURCES.values():
    assert expected in peer_bytes.decode(), "Peer review must bind all three final sources"
root_review_path = ROOT / "root-source-review.json"
root_review_bytes = root_review_path.read_bytes()
assert sha(root_review_bytes) == "53bf537aa2bb2a9429afbc7e9e57d28775a2ec24e22734a913e155d1a2737a38"
root_review = json.loads(root_review_bytes)
assert root_review["sourceOnly"] and root_review["noFurtherConcreteBlockerFound"]
assert not root_review["compiledOrExecuted"]
manifest_bytes = (ROOT / "candidate-manifest.json").read_bytes()
assert sha(manifest_bytes) == "49f1c78ba4d09db091af9798b0655092316dcb1f8ad88e8cc6cb9ea14992f59d"
manifest = json.loads(manifest_bytes)
assert manifest["baseCommit"] == AUTHORING_BASE and not manifest["runtimeReady"]
continuity_path = ROOT / "current-base-continuity.json"
continuity_bytes = continuity_path.read_bytes()
continuity = json.loads(continuity_bytes)
assert continuity["publicationParent"] == BASE and continuity["publicationParentTree"] == BASE_TREE
assert continuity["sourceAuthoringAndReviewBase"] == AUTHORING_BASE
assert len(continuity["files"]) == 3 and all(x["exactUTF8ContentEqualToRetainedOriginal"] for x in continuity["files"])
assert not PACKET.exists(), "A frozen packet is not overwritten"

provenance = {}
def write(relative, raw, source=None, kind="derived-evidence"):
    path = Path(relative)
    assert not path.is_absolute() and ".." not in path.parts
    target = PACKET / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    assert target.read_bytes() == raw
    provenance[relative] = {"kind": kind, "localSource": str(source) if source else str(Path(__file__).resolve())}

for relative, expected in SOURCES.items():
    source = ROOT / "candidate" / relative
    raw = source.read_bytes()
    assert sha(raw) == expected
    write(relative, raw, source, "exact-reviewed-existing-source-successor")

retained = [
    "candidate-manifest.json", "current-base-continuity.json", "source-inverse.json", "source-bindings.json", "source.patch",
    "app-initialization-correction.json", "app-initialization-correction.patch",
    "external-evidence-order-correction.json", "external-evidence-order-correction.patch",
    "root-source-review.json", "prepare_source_artifacts.py",
    "review-v1-app-init/AnyNativeApp.swift",
]
for relative in retained:
    source = ROOT / relative
    assert source.is_file() and not source.is_symlink()
    write(PREFIX + "/" + relative, source.read_bytes(), source, "exact-retained-source-evidence")
write(PREFIX + "/README.md", (ROOT / "publication-README.md").read_bytes(), ROOT / "publication-README.md", "current-publication-readme")
write(PREFIX + "/source-preparation-README.md", (ROOT / "README.md").read_bytes(), ROOT / "README.md", "exact-retained-source-readme")
write(PREFIX + "/interfaces-independent-review.json", peer_bytes, peer_path, "exact-peer-source-review")
write(PREFIX + "/prepare_publication_packet.py", Path(__file__).read_bytes(), Path(__file__), "exact-packet-generator")

inverse = json.loads((ROOT / "source-inverse.json").read_text())
restoration = []
for change in inverse["changes"]:
    relative = change["repositoryPath"]
    current = (ROOT / "candidate" / relative).read_bytes()
    original = (ROOT / "originals" / relative).read_bytes()
    if change["operation"] == "append-exact-suffix":
        assert current[:len(original)] == original
        assert sha(current[len(original):]) == change["suffix"]["sha256"]
        mode = {"kind": "exact-prefix-and-suffix-slices", "prefixBytes": len(original),
                "suffixBytes": len(current) - len(original), "suffixSHA256": change["suffix"]["sha256"]}
    else:
        restored = current.decode()
        for edit in reversed(change["rules"]):
            assert restored.count(edit["new"]) == edit["count"] == 1
            restored = restored.replace(edit["new"], edit["old"], 1)
        assert restored.encode() == original
        mode = {"kind": "reverse-four-exact-text-replacements", "ruleFile": "source-inverse.json"}
    restoration.append({"repositoryPath": relative, "currentSHA256": sha(current),
        "originalBytes": len(original), "originalSHA256": sha(original), "originalGitBlob": blob(original),
        "originalImmutableURL": f"https://github.com/{REPO}/blob/{AUTHORING_BASE}/{relative}",
        "currentPublicationParentURL": f"https://github.com/{REPO}/blob/{BASE}/{relative}", "restoration": mode})

history = []
for correction_name, old_path, current_path, form in [
    ("app-initialization-correction.json", "review-v1-app-init/AnyNativeApp.swift", "candidate/NativeApp/Sources/AnyNativeApp.swift", "single"),
    ("external-evidence-order-correction.json", "review-v1-ui-evidence/NativeLaunchTests.swift", "candidate/NativeApp/UITests/NativeLaunchTests.swift", "multiple"),
]:
    correction = json.loads((ROOT / correction_name).read_text())
    raw = (ROOT / current_path).read_bytes()
    restored = raw.decode()
    edits = [correction["forward"]] if form == "single" else correction["edits"]
    for edit in reversed(edits):
        assert restored.count(edit["new"]) == edit["count"] == 1
        restored = restored.replace(edit["new"], edit["old"], 1)
    old = (ROOT / old_path).read_bytes()
    assert restored.encode() == old
    history.append({"localPredecessor": str(ROOT / old_path), "bytes": len(old), "sha256": sha(old),
        "gitBlob": blob(old), "restorationFromCurrentRepositoryPath": current_path.removeprefix("candidate/"),
        "fullInverseFile": correction_name, "exactWholePredecessorRestored": True,
        "bodyCopiedIntoDocs": form == "single"})
write(PREFIX + "/compact-restoration-index.json", encode({
    "schema": "native-bookmark-compact-source-restoration-v1", "sourceAuthoringBase": AUTHORING_BASE, "publicationParent": BASE,
    "wholeOriginalBodies": restoration, "sourceCorrectionPredecessors": history,
    "precision": "Full current source bodies are retained once at their original repository paths. Original prefixes and the prior full UI body are independently reconstructable by the verified slices/full text inverses; no duplicate 296–320KB UI source body is copied into docs. All local originals remain untouched."
}))

write(PREFIX + "/handoff.json", encode({
    "schema": "native-bookmark-mounted-source-handoff-v1", "status": "SOURCE_ONLY_NOT_RUN",
    "repository": REPO, "publicationParent": BASE, "publicationParentTree": BASE_TREE, "sourceAuthoringAndReviewBase": AUTHORING_BASE,
    "currentBaseContinuitySHA256": sha(continuity_bytes), "ownedBranch": BRANCH,
    "changedExistingSourceSHA256": SOURCES, "newSelector": "NativeLaunchTests/testNativeBookmarkCancelCreateEditOpenAndColdReopen",
    "newMethods": 1, "newUnparameterizedCases": 1, "originalMethodsPreserved": 26, "sourceMethodsAfterAppend": 27,
    "existingSourcePathsOnly": True, "newPBXPaths": [], "runtimeReady": False, "matchingProducerAdmission": None,
    "compiledEnumeration": None, "original26SelectionChanged": False,
    "syntheticInstalledDefinitions": True, "originalNineteenTypeMigrationQualified": False,
    "standaloneHookSourceOnly": True, "combinedHookQualified": False,
    "firstApplePriority": "original22methods34cases -> originalrealpreparation -> original4UIselectors",
    "sourceReviews": {"rootSHA256": sha(root_review_bytes), "peerSHA256": sha(peer_bytes)},
    "actualAcceptance": {"SwiftAppleCompilation": "NOT_RUN", "NativeMountedUI": "NOT_RUN", "externalBrowser": "NOT_RUN",
                         "coldReopen": "NOT_RUN", "visual": "NOT_RUN", "physicalDevice": "NOT_RUN"},
    "futureOwner": "W3 owns product/source/compiled selection and Apple execution; no current consumer is opened by this source packet.",
    "runtimeOrNativeCallsByPreparation": 0, "hostOrMacActions": 0
}))

def entries():
    result = []
    for path in sorted(PACKET.rglob("*")):
        if path.is_file():
            relative = str(path.relative_to(PACKET)); raw = path.read_bytes()
            result.append({"path": relative, "mode": "100644", "bytes": len(raw), "sha256": sha(raw), "gitBlob": blob(raw),
                           "provenance": provenance[relative]})
    return result

rows = entries()
write(PREFIX + "/packet-manifest.json", encode({
    "schema": "native-bookmark-mounted-publication-packet-v1", "status": "SOURCE_PACKET_PENDING_ROOT_COMPLETE_PACKET_REVIEW",
    "baseCommit": BASE, "baseTree": BASE_TREE, "sourceAuthoringBase": AUTHORING_BASE, "ownedBranch": BRANCH, "sourceAllowlist": list(SOURCES),
    "payloadCountExcludingThisManifest": len(rows), "payloadBytesExcludingThisManifest": sum(x["bytes"] for x in rows),
    "files": rows, "runtimeExecuted": False, "nativeActions": 0, "compiledAcceptance": False
}))
rows = entries()
target = {"schema": "native-bookmark-mounted-publication-target-v1", "baseCommit": BASE, "baseTree": BASE_TREE, "branch": BRANCH,
          "docsPrefix": PREFIX, "fileCount": len(rows), "totalBytes": sum(x["bytes"] for x in rows),
          "files": rows, "gitMutationAuthorizedByThisFile": False, "runtimeExecuted": False}
target_path = ROOT / "publication-preparation/target.json"
target_path.write_bytes(encode(target))
print(json.dumps({"targetPath": str(target_path), "targetSHA256": sha(target_path.read_bytes()),
                  "fileCount": len(rows), "totalBytes": target["totalBytes"], "packet": str(PACKET)}, indent=2))
