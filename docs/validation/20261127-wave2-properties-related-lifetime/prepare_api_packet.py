"""Prepare the reviewed four-file packet; no remote or host mutation."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
API = ROOT / "api"
PACKET = ROOT / "publication-packet"
BASE = "d8a2c67b6dae09a7b769e803a319de3d3080019c"
BASE_TREE = "d6ef8cf91bc81732a1a506eabac5950d14ed56f2"
BRANCH = "codex/chatgpt-wave15-wave2-properties-related-lifetime-20261127"
DOC = "docs/validation/20261127-wave2-properties-related-lifetime"
MODULE = "Modules/PinkhaAnyUI"
SOURCES = {
    MODULE + "/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift": "f3b6b6bb5425d69d7eff09aecac9c82a5dfd125ed004c644126cb518e137c4a5",
    MODULE + "/Sources/PinkhaAnyUI/AnyNativePropertiesView.swift": "47e04a0dedaebe5a0d6dc35e4b8d30b58a5f0c8eda0cb44fea6283ecf801465d",
    MODULE + "/Sources/PinkhaAnyUI/AnyNativeSourceDocumentsPresentation.swift": "1cf8d0790e949b7592d4298dff0e788982ad3b0959c838350fe587d2c80e48c1",
    MODULE + "/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift": "f334ce278537413df7ef7b508db8bd250135f002f3b6dfa65a306459e4b807c6",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main():
    assert not PACKET.exists(), "Retain every packet attempt"
    base = json.loads((API / "base-commit.primary.json").read_bytes())
    assert base["sha"] == BASE and base["tree"]["sha"] == BASE_TREE
    trees = {n: json.loads((API / f"base-{n}.primary.json").read_bytes())
             for n in ["root", "modules", "ui-module", "docs", "validation", "engine-docs"]}
    assert all(v["truncated"] is False for v in trees.values())
    assert len(trees["validation"]["tree"]) == 630
    assert not any(v["path"] == Path(DOC).name for v in trees["validation"]["tree"])
    files = {}
    for name, expected in SOURCES.items():
        value = (ROOT / "candidate" / name).read_bytes()
        assert sha(value) == expected
        files[name] = value
    inverse = json.loads((ROOT / "source-inverse.json").read_bytes())
    assert sha((ROOT / "source-inverse.json").read_bytes()) == "43b7c54c50412cb85f6626d189d5c86779b20e9a5e6d74c93b9356e40239a67b"
    assert inverse["fullInverseRestoredAllOriginalBytes"] is True
    assert {v["path"]: v["candidateSHA256"] for v in inverse["files"]} == SOURCES
    original_leaves = {v["path"]: v for v in trees["ui-module"]["tree"] if v["type"] != "tree"}
    assert len(original_leaves) == 68
    for row in inverse["files"]:
        short = row["path"].removeprefix(MODULE + "/")
        if row["originalGitBlob"] is None:
            assert short not in original_leaves
        else:
            assert original_leaves[short]["sha"] == row["originalGitBlob"]
            assert original_leaves[short]["mode"] == "100644"
    for name, expected in {
        "root-independent-review-v3.json": "5a000a11e62e3818d06b8042957316214bdd10a277f460084d98c0594897a94f",
        "editor-independent-review-v3.json": "2eab027ef19c26d5af5e76a0dbcd6d276a52bfa9f1647546621a799210789d7e",
    }.items():
        assert sha((ROOT / name).read_bytes()) == expected
        review = json.loads((ROOT / name).read_bytes())
        assert review["status"] == "PASS_SOURCE_REVIEW_ONLY" and review["findings"] == []
        assert {v["path"]: v["sha256"] for v in review["inputs"]} == SOURCES
    origin = json.loads((ROOT / "source-origin.json").read_bytes())
    assert origin["classification"] == "DOWNSTREAM_OWNED" and origin["sourceGateExecuted"] is False
    workflows = json.loads((API / "workflow-preflight.json").read_bytes())
    assert workflows["newOwnedBranch"] == BRANCH
    assert workflows["createEventPresent"] is False and workflows["automaticWorkflowSelected"] is False
    assert workflows["workflowDispatch"] is False
    preflight = {
        "status": "REVIEWED_SOURCE_PACKET_NOT_COMPILER_OR_RUNTIME_ADMISSION",
        "baseCommit": BASE, "baseTree": BASE_TREE, "ownedNewBranch": BRANCH,
        "modifiedExistingSourceFiles": 3, "addedProductSourceFiles": 1,
        "allowedSourceFiles": SOURCES, "allowedNewEvidenceSubtree": DOC,
        "rootChangedSubtreesOnly": ["Modules", "docs"],
        "moduleChangedChildOnly": "PinkhaAnyUI", "originalModuleLeaves": 68,
        "newModuleLeaves": 69, "unchangedOriginalValidationChildren": 630,
        "protectedInventories": {v["path"]: v["sha"] for v in trees["engine-docs"]["tree"]
            if v["path"] in ["SOURCE_REFACTOR_MAP.json", "SOURCE_INVENTORY.json", "CAPABILITY_INVENTORY.json"]},
        "sourceGate": {"executedHere": False, "inheritedMapRows": 130,
                       "note": "Downstream module is absent from baseline/upstream; all untouched subtree identities must remain exact."},
        "workflowPreflightSHA256": sha((API / "workflow-preflight.json").read_bytes()),
        "tests": {"oldMethods": 5, "oldDeclaredCases": 7, "newMethods": 5,
                  "newDeclaredCases": 11, "execution": "NOT_RUN", "typecheck": "NOT_RUN"},
        "privateFixtureOrCredentialsIncluded": False,
        "operations": {"oracle": 0, "mac": 0, "compiler": 0, "native": 0, "simulator": 0},
        "runtimeAdmission": False,
    }
    (API / "publication-preflight.json").write_bytes(encode(preflight))
    scoped = {}
    for name in ["README.md", "source-origin.json", "source-inverse.json", "source.patch", "verify_source.py",
                 "test-suffix.swift", "review-successor.json", "review-successor.patch",
                 "foreground-cleanup-successor.json", "foreground-cleanup-successor.patch",
                 "editor-independent-review-v3.json", "root-independent-review-v3.json",
                 "editor-lifecycle-primary.json", "editor-document-view-primary.json",
                 "prepare_api_packet.py", "verify_api_trees.py"]:
        scoped[name] = ROOT / name
    for directory in ["review-v1", "review-v2"]:
        for path in (ROOT / directory).rglob("*"):
            if path.is_file(): scoped[str(path.relative_to(ROOT))] = path
    for name in ["base-commit", "base-root", "base-modules", "base-ui-module", "base-docs",
                 "base-validation", "base-engine-docs", "branch-before", "default-ref"]:
        scoped[f"api/{name}.primary.json"] = API / f"{name}.primary.json"
    for name in ["workflow-preflight.json", "publication-preflight.json", "local-api-metadata-save-failure.json"]:
        scoped["api/" + name] = API / name
    for name in ["README.md", "source-manifest.json"]:
        scoped["audit/" + name] = ROOT.parent / "t5-publication-lifetime" / name
    for name, path in scoped.items(): files[DOC + "/" + name] = path.read_bytes()
    manifest = {"schema": "wave2-properties-related-source-packet/v1", "baseCommit": BASE,
                "branch": BRANCH, "productRuntimeAdmission": False,
                "files": {p: {"bytes": len(b), "sha256": sha(b), "gitBlob": blob(b),
                              "mode": "100644", "type": "blob"} for p, b in files.items()}}
    files[DOC + "/packet-manifest.json"] = encode(manifest)
    assert sum(map(len, files.values())) <= 1024 * 1024, "Keep this publication bounded to one MiB"
    for name, value in files.items():
        path = PACKET / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    elements = [{"path": p, "mode": "100644", "type": "blob", "content": b.decode("utf-8")}
                for p, b in files.items()]
    (API / "tree-elements.json").write_bytes(encode(elements))
    (API / "expected-files.json").write_bytes(encode({p: {"mode": "100644", "type": "blob", "sha": blob(b)} for p, b in files.items()}))
    print(json.dumps({"status": preflight["status"], "files": len(files), "bytes": sum(map(len, files.values())),
                      "manifestSHA256": sha(encode(manifest)), "base": BASE, "branch": BRANCH}))


if __name__ == "__main__": main()
