"""Prepare an exact source-only API packet; perform no Git or host mutation."""
from pathlib import Path
import ast
import fnmatch
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
API = ROOT / "api-publication"
PACKET = ROOT / "publication-packet"
BASE = "cee06ac951f735514059e616fbea48f07d4e7c09"
BRANCH = "codex/chatgpt-wave15-wave2-t5-r08-warning-20261127"
DOC = "docs/validation/20261127-wave2-t5-r08-warning"
UI = "PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def blob(value):
    return hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def main():
    assert not PACKET.exists(), "Preserve each packet attempt"
    base = json.loads((API / "base-commit.original.json").read_bytes())
    assert base["sha"] == BASE and base["tree"]["sha"] == "7a1793b6fb4f074653814642fdae56b5e8a21633"
    trees = {name: json.loads((API / ("base-" + name + "-tree.original.json")).read_bytes())
             for name in ["root", "ui", "docs", "validation", "engine-docs"]}
    assert all(value["truncated"] is False for value in trees.values())
    assert not any(row["path"] == Path(DOC).name for row in trees["validation"]["tree"])
    original = (ROOT / "source/PinkhaT5NativeAcceptanceUITests.swift").read_bytes()
    candidate = (ROOT / "candidate/PinkhaT5NativeAcceptanceUITests.swift").read_bytes()
    assert digest(original) == "698f4ed7f1f81fe567b94b531f43e14259d08e6acbf79d72e132a5b9b6b941a7"
    assert digest(candidate) == "b43f97b3c1283f05b728b15cc9871bfecc1692ca55563f1e2c1f1886ecd38d5e"
    assert next(row for row in trees["ui"]["tree"] if row["path"] == "Tests/PinkhaT5NativeAcceptanceUITests.swift")["sha"] == blob(original)
    inverse = json.loads((ROOT / "source-inverse.json").read_bytes())
    restored = candidate.decode("utf8")
    for row in reversed(inverse["changes"]):
        assert restored.count(row["new"]) == row["count"] == 1
        restored = restored.replace(row["new"], row["old"], 1)
    assert restored.encode() == original
    workflows = json.loads((API / "workflow-triggers.json").read_bytes())
    assert len(workflows) == 83 and len({r["path"] for r in workflows}) == 83
    pushes = []
    for row in workflows:
        t = row["on"]
        events = list(t) if isinstance(t, dict) else t if isinstance(t, list) else [t]
        assert "create" not in events and "delete" not in events
        if "push" in events:
            assert isinstance(t, dict) and isinstance(t["push"], dict)
            branches = t["push"].get("branches")
            assert isinstance(branches, list) and branches and not any(fnmatch.fnmatchcase(BRANCH, b) for b in branches)
            pushes.append({"path": row["path"], "branches": branches})
    assert len(pushes) == 5
    gate = (API / "source-retention-gate.original.py").read_bytes()
    assert blob(gate) == "5b579e9bbb5a82981b5aef7d649f2caf88e998b6"
    function = next(n for n in ast.parse(gate).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    protected = next(ast.literal_eval(n.value) for n in function.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "paths" for t in n.targets))
    assert not any(UI == p or UI.startswith(p + "/") for p in protected)
    preservation = {
        "status": "PROSPECTIVE_SOURCE_CUSTODY_REQUIREMENTS_NOT_GATE_EXECUTION",
        "baseCommit": BASE, "baseRootTree": base["tree"]["sha"], "ownedNewBranch": BRANCH,
        "allowedExistingSourceChange": {"path": UI, "oldGitBlob": blob(original), "newGitBlob": blob(candidate), "newSHA256": digest(candidate)},
        "allowedNewEvidenceSubtree": DOC,
        "comparison": "Every root entry; complete UI leaf map; every docs child; all621 existing validation children; every new evidence leaf. All untouched subtrees exact mode/type/SHA.",
        "uiTreeEntries": len(trees["ui"]["tree"]), "uiLeaves": sum(r["type"] != "tree" for r in trees["ui"]["tree"]),
        "originalValidationChildren": len(trees["validation"]["tree"]),
        "protectedPaths": protected,
        "gate": {"gitBlob": blob(gate), "sha256": digest(gate), "executedHere": False},
        "protectedInventories": {r["path"]: r["sha"] for r in trees["engine-docs"]["tree"] if r["path"] in ["SOURCE_REFACTOR_MAP.json", "SOURCE_INVENTORY.json", "CAPABILITY_INVENTORY.json"]},
        "inheritedParentRetention": {"reviewedRows": 130, "actualW3AsanaStory": "1220950559845512", "newExecutionClaimed": False},
        "workflowQualification": {"exactSources": 83, "createEventCount": 0, "matchingPushFilters": 0, "pushWorkflows": pushes, "workflowDispatchRequested": False},
        "sourceClassification": "DOWNSTREAM_OWNED_UI_TEST_ONLY",
        "ownerAuthorization": "Original task development/commit/publication authorization; root review8401 and finite-Merkle approval after retained transport failure",
        "OracleWrites": 0, "MacCalls": 0, "runtimeAdmissionOpened": False,
    }
    (API / "publication-preflight.json").write_bytes(encoded(preservation))
    files = {UI: candidate}
    scoped = {
        "README.md": ROOT / "README.md",
        "prepare_source.py": ROOT / "prepare_source.py",
        "prepare_api_packet.py": Path(__file__),
        "source-inverse.json": ROOT / "source-inverse.json",
        "changes.diff": ROOT / "changes.diff",
        "originals/PinkhaT5NativeAcceptanceUITests.swift": ROOT / "source/PinkhaT5NativeAcceptanceUITests.swift",
        "root-independent-review.json": ROOT / "root-independent-review.json",
        "production-auth-evidence.json": ROOT.parent / "t5-page154-readiness-refresh/auth-primary-evidence.json",
        "readiness/README.md": ROOT.parent / "t5-page154-readiness-refresh/README.md",
        "readiness/readiness.json": ROOT.parent / "t5-page154-readiness-refresh/readiness.json",
        "readiness/primary-source-readback.json": ROOT.parent / "t5-page154-readiness-refresh/primary-source-readback.json",
        "readiness/asana-material-handoffs.json": ROOT.parent / "t5-page154-readiness-refresh/asana-material-handoffs.json",
    }
    for name in ["base-commit.original.json", "base-root-tree.original.json", "base-ui-tree.original.json", "base-docs-tree.original.json", "base-validation-tree.original.json", "base-engine-docs-tree.original.json", "original-recursive-tree-transport-failure.json", "branch-absence-before.original.json", "source-retention-gate.original.py", "workflow-triggers.json", "publication-preflight.json"]:
        scoped["api-custody/" + name] = API / name
    for name, path in scoped.items():
        files[DOC + "/" + name] = path.read_bytes()
    manifest = {"schema": "pinkha-t5-r08-source-api-packet-v1", "base": BASE, "branch": BRANCH,
                "modifiedSourceFiles": 1, "newMethods": 0, "newCases": 0,
                "files": {name: {"bytes": len(value), "sha256": digest(value), "gitBlob": blob(value), "mode": "100644", "type": "blob"} for name, value in files.items()}}
    files[DOC + "/packet-manifest.json"] = encoded(manifest)
    PACKET.mkdir()
    for name, value in files.items():
        p = PACKET / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value)
    entries = [{"path": name, "mode": "100644", "type": "blob", "content": value.decode("utf8")} for name, value in files.items()]
    (API / "tree-elements.json").write_bytes(encoded(entries))
    (API / "expected-files.json").write_bytes(encoded({e["path"]: {"mode": e["mode"], "type": e["type"], "sha": blob(e["content"].encode("utf8"))} for e in entries}))
    print(json.dumps({"status": "PREPARED_SOURCE_ONLY_PACKET_NO_API_MUTATION", "files": len(files), "bytes": sum(map(len, files.values())), "candidateSHA256": digest(candidate), "preflightSHA256": digest(encoded(preservation))}))


if __name__ == "__main__":
    main()
