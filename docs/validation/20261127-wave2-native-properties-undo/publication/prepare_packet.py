from pathlib import Path
import fnmatch
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
PACKET = ROOT / "publication/packet"
DOCS = Path("docs/validation/20261127-wave2-native-properties-undo")
BRANCH = "codex/chatgpt-wave15-wave2-native-properties-undo-20261127"
PARENT = "13dc5b060c23527aeaedb1d1e250a86c9a2fc17c"
TREE = "79fd8ae0d576c3c854642acd1bde44b6fc08fd1a"

def sha(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
def js(value): return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
def put(path, raw):
    target = PACKET / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): assert target.read_bytes() == raw, str(path)
    else: target.write_bytes(raw)
def copy(path, name=None): put(DOCS / (name or str(path.relative_to(ROOT))), path.read_bytes())
def read(name): return json.loads((ROOT / "publication/api" / name).read_bytes())

assert sha((ROOT / "root-independent-review.json").read_bytes()) == "ef164a52e27ac34d1aab6b330dcd85d9c9943c247292dcf989f979c4068c1cdb"
assert sha((ROOT / "editor-independent-review.json").read_bytes()) == "8e3d8d2910dc06698842c575e070711b1f8aa7c4563a64eac92f0b978c10e0fb"
manifest = json.loads((ROOT / "candidate-manifest.json").read_bytes())
assert sha((ROOT / "candidate-manifest.json").read_bytes()) == "a8697e11a333cb14c5a033495a5cf9b4e84fa3a1ea24be3ec59b0e14d835d173"
assert manifest["native25DonorCommit"] == PARENT
source = ROOT / manifest["append"]["candidatePath"]
raw = source.read_bytes()
original = (ROOT / "source/NativeLaunch25.swift").read_bytes()
suffix = (ROOT / "properties_undo_suffix.swift").read_bytes()
assert raw == original + suffix
assert sha(raw) == "e2979e777dd61f7eb8be06bd38028b15cc6f7e2d944fe6adce9603a3f7817358"
assert len(original) == 281769 and sha(original) == "7d7d60d61cabaf7e8c968c4d30cd584100e9d90217f6b1b66441146cbf5d943b"
assert read("native26-base-commit.json")["tree"]["sha"] == TREE
assert read("native26-ref-absent.json")["error_code"] == "NOT_FOUND"
root = read("native26-base-root.json")
native = read("native26-base-nativeapp.json")
docs = read("native26-base-docs.json")
validation = read("native26-base-validation.json")
assert all(x["truncated"] is False for x in [root, native, docs, validation])
assert not any(x["path"] == DOCS.name for x in validation["tree"])
native_source = next(x for x in native["tree"] if x["path"] == "UITests/NativeLaunchTests.swift")
assert native_source["sha"] == blob(original) and native_source["mode"] == "100644"
assert not any(Path(x["path"]).name == "AGENTS.md" for x in native["tree"])
assert not any(x["path"] == "AGENTS.md" for x in docs["tree"] + validation["tree"])

audit_path = WORKSPACE / "interfaces_work/attachment-upload-ui/publication/packet/docs/validation/20261127-wave2-attachment-upload-ui/publication/integration-workflow-original-audit.json"
audit_raw = audit_path.read_bytes()
assert sha(audit_raw) == "51921c475999cc4032e1c5ee0248bb12f9d75264115fbde91fea1aa90ab4df87"
audit = json.loads(audit_raw)
github = read("native26-base-github.json")
actual = {".github/" + x["path"]: x["sha"] for x in github["tree"] if x["type"] == "blob" and x["path"].startswith("workflows/") and x["path"].endswith((".yml", ".yaml"))}
assert actual == {x["path"]: x["gitBlob"] for x in audit["workflows"]}
assert len(actual) == 83
filters = ["codex/any-engine-port-20261119", "pinkha/torah-associations-native-ux-persistence-localization-2026-10-20", "pinkha/*", "pinkha/torah-functional-ui-single-device-2026-10-18", "pinkha/upstream-u10-validation-2026-10-18"]
push = [x for x in audit["workflows"] if re.search(r"(?m)^\s*push\s*:", x["triggerSource"])]
assert len(push) == 5 and not any(re.search(r"(?m)^\s*create\s*:", x["triggerSource"]) for x in audit["workflows"])
assert all(any(f in x["triggerSource"] for f in filters) for x in push)
assert all(not fnmatch.fnmatchcase(BRANCH, f) for f in filters)
default = read("native26-default-ref.json")
assert default["object"]["sha"] == "1b1043b3a810f6f528ec5147aeb1b29e17b840e7"
preflight = {
    "status": "PASS_SOURCE_PUBLICATION_PREFLIGHT_ONLY",
    "parentCommit": PARENT, "parentTree": TREE, "newOwnedBranch": BRANCH,
    "ownedRefAbsent": True, "newEvidenceDirectoryAbsent": True,
    "changedSource": "NativeApp/UITests/NativeLaunchTests.swift",
    "classification": "DOWNSTREAM_OWNED native test extension only",
    "standingOwnerAuthorizationRead": "AGENTS908d94f9; user Wave2 development/publication instruction; root exact source approvalef164",
    "rootEntries": len(root["tree"]), "nativeRecursiveEntries": len(native["tree"]),
    "workflowTree": "f4fa7f14a0a5808683977491486ed37ced88433e",
    "all83WorkflowBlobsMatchRetainedPrimaryAudit": True,
    "originalWorkflowAuditSHA256": sha(audit_raw), "pushFilters": filters,
    "pushOrCreateMatchesNewBranch": False,
    "defaultRef": default,
    "freshUpstreamDevelop": read("native26-upstream-develop.json")["object"]["sha"],
    "sourceRetentionMeaning": "Complete finite primary Merkle comparison will bind every original root subtree and every NativeApp leaf except the one declared test source. No Oracle worktree or CLI retention command is claimed.",
    "OracleWrites": 0, "MacActions": 0, "workflowDispatches": 0, "compilerOrTests": 0,
    "productOrControllerPinChanges": 0,
}
(ROOT / "publication/preflight.json").write_bytes(js(preflight))
put(Path("NativeApp/UITests/NativeLaunchTests.swift"), raw)
for name in ["README.md", "candidate-manifest.json", "source-inverse.json", "source-structure-proof.json", "setup-correction-inverse.json", "properties_undo_suffix.swift", "root-independent-review.json", "editor-independent-review.json"]:
    copy(ROOT / name)
for path in sorted((ROOT / "review-v1").glob("*")): copy(path)
for path in sorted((ROOT / "source").glob("*.swift")):
    if path.name != "NativeLaunch25.swift": copy(path)
copy(ROOT / "primary/AnyNativePropertyPresentation.json")
copy(ROOT / "publication/preflight.json")
for name in ["native26-agents.json", "native26-upstream.json", "native26-ref-absent.json", "native26-default-ref.json", "native26-upstream-develop.json"]:
    copy(ROOT / "publication/api" / name)
put(DOCS / "publication/integration-workflow-original-audit.json", audit_raw)
prior = WORKSPACE / "wave2-semantic-anchor-audit/api-publication/publication-result.json"
put(DOCS / "prior-native25-publication.json", prior.read_bytes())
binding = {
    "donorCommit": PARENT, "sourcePath": "NativeApp/UITests/NativeLaunchTests.swift",
    "gitBlob": blob(original), "sha256": sha(original), "bytes": len(original),
    "fullOriginalSourceRetainedInImmutableParent": True,
    "fullPrimaryReadbackExactlyMatchedLocalPrefix": True,
    "localRawPrimarySHA256": sha((ROOT / "primary/NativeLaunch25.json").read_bytes()),
    "rawLocalCustody": "interfaces_work/native-properties-undo-ui/primary/NativeLaunch25.json",
    "sourceCopies": "The exact parent blob is already durable in13dc; this packet retains its binding and exact additive inverse without another full source duplicate.",
}
put(DOCS / "primary/NativeLaunch25-binding.json", js(binding))
copy(Path(__file__))
entries = []
for path in sorted(PACKET.rglob("*")):
    if path.is_file():
        b = path.read_bytes(); b.decode("utf-8")
        entries.append({"path": str(path.relative_to(PACKET)), "bytes": len(b), "sha256": sha(b), "gitBlob": blob(b), "mode": "100644", "type": "blob"})
packet = {"status": "SOURCE_REVIEWED_RUNTIME_NOT_RUN", "parentCommit": PARENT, "parentTree": TREE, "branch": BRANCH,
          "sourceFilesChanged": 1, "newMethod": "testNativePropertyValueCancelAndUndoSurviveColdReopen", "newMethods": 1, "newDeclaredCases": 1,
          "allOriginal25MethodsExact": True, "resultingNativeMethods": 26, "actualCompiledEnumeration": None, "actualResults": None,
          "files": entries, "bytesExcludingManifest": sum(x["bytes"] for x in entries)}
put(DOCS / "packet-manifest.json", js(packet))
expected=[]; chunks=[]; current=[]; count=0
for path in sorted(PACKET.rglob("*")):
    if not path.is_file(): continue
    b=path.read_bytes(); rel=str(path.relative_to(PACKET))
    expected.append({"path":rel,"mode":"100644","type":"blob","sha":blob(b),"sha256":sha(b),"bytes":len(b)})
    item={"path":rel,"mode":"100644","type":"blob","content":b.decode("utf-8")}
    if current and count+len(b)>90000: chunks.append(current);current=[];count=0
    current.append(item);count+=len(b)
if current: chunks.append(current)
api=ROOT/"publication/api"; (api/"expected-files.json").write_bytes(js(expected))
for number,chunk in enumerate(chunks):
    path=api/"tree-input-chunks"/f"{number:02d}.json";path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(js(chunk))
print(json.dumps({"files":len(expected),"newDocs":len(expected)-1,"bytesExcludingManifest":packet["bytesExcludingManifest"],"packetManifestSHA256":sha((PACKET/DOCS/"packet-manifest.json").read_bytes()),"chunks":len(chunks)}))
