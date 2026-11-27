"""Finite complete-tree retention proof from actual primary Git tree receipts."""
from pathlib import Path
import hashlib
import json

API = Path(__file__).resolve().parent / "api"
DOC = "docs/validation/20261127-wave2-properties-related-lifetime"
MODULE = "Modules/PinkhaAnyUI"
BASE_TREE = "d6ef8cf91bc81732a1a506eabac5950d14ed56f2"


def read(name):
    value = json.loads((API / name).read_bytes())
    assert value["truncated"] is False
    return value


def entries(value, leaves=False):
    rows = [r for r in value["tree"] if not leaves or r["type"] != "tree"]
    result = {r["path"]: {k: r[k] for k in ["mode", "type", "sha"]} for r in rows}
    assert len(result) == len(rows)
    return result


def exact_except(before, after, allowed):
    assert before.keys() == after.keys()
    assert {p for p in before if before[p] != after[p]} == set(allowed)
    for p in allowed:
        assert before[p]["type"] == after[p]["type"] == "tree"
        assert before[p]["mode"] == after[p]["mode"] == "040000"


def main():
    names = ["root", "modules", "ui-module", "docs", "validation"]
    before = {n: read(f"base-{n}.primary.json") for n in names}
    after = {n: read(f"new-{n}.primary.json") for n in names + ["evidence"]}
    created = json.loads((API / "created-tree.primary.json").read_bytes())
    assert before["root"]["sha"] == BASE_TREE
    assert after["root"]["sha"] == created["sha"]
    expected = json.loads((API / "expected-files.json").read_bytes())
    exact_except(entries(before["root"]), entries(after["root"]), ["Modules", "docs"])
    exact_except(entries(before["modules"]), entries(after["modules"]), ["PinkhaAnyUI"])
    original_leaves = entries(before["ui-module"], leaves=True)
    expected_module = dict(original_leaves)
    for path, identity in expected.items():
        if path.startswith(MODULE + "/"):
            expected_module[path.removeprefix(MODULE + "/")] = identity
    assert len(original_leaves) == 68 and len(expected_module) == 69
    assert entries(after["ui-module"], leaves=True) == expected_module
    all_before, all_after = entries(before["ui-module"]), entries(after["ui-module"])
    assert set(all_after) - set(all_before) == {"Sources/PinkhaAnyUI/AnyNativeSourceDocumentsPresentation.swift"}
    changed_parents = {"Sources", "Sources/PinkhaAnyUI", "Tests", "Tests/PinkhaAnyUITests"}
    for path, identity in all_before.items():
        assert all_after[path]["mode"] == identity["mode"] and all_after[path]["type"] == identity["type"]
        if identity["type"] == "tree" and path not in changed_parents: assert all_after[path] == identity
    exact_except(entries(before["docs"]), entries(after["docs"]), ["validation"])
    old_validation, new_validation = entries(before["validation"]), entries(after["validation"])
    assert len(old_validation) == 630
    assert set(new_validation) - set(old_validation) == {Path(DOC).name}
    assert all(new_validation.get(p) == identity for p, identity in old_validation.items())
    assert new_validation[Path(DOC).name] == {"mode": "040000", "type": "tree", "sha": after["evidence"]["sha"]}
    expected_docs = {p.removeprefix(DOC + "/"): row for p, row in expected.items() if p.startswith(DOC + "/")}
    assert entries(after["evidence"], leaves=True) == expected_docs
    dirs = {str(parent) for path in expected_docs for parent in Path(path).parents if str(parent) != "."}
    assert set(entries(after["evidence"])) == set(expected_docs) | dirs
    assert all(entries(after["evidence"])[d]["mode"] == "040000" and entries(after["evidence"])[d]["type"] == "tree" for d in dirs)
    links = [("root", "modules", "Modules"), ("modules", "ui-module", "PinkhaAnyUI"),
             ("root", "docs", "docs"), ("docs", "validation", "validation")]
    for parent, child, path in links:
        assert entries(before[parent])[path]["sha"] == before[child]["sha"]
        assert entries(after[parent])[path]["sha"] == after[child]["sha"]
    protected = [".github", "Anytype", "AnyTypeTests", "Anytype.xcodeproj", "PinkhaStage1Acceptance", "Tools"]
    assert all(entries(before["root"])[p] == entries(after["root"])[p] for p in protected)
    assert entries(before["docs"])["any-engine-port"] == entries(after["docs"])["any-engine-port"]
    proof = {
        "status": "PASS_ACTUAL_PRIMARY_FINITE_MERKLE_SOURCE_CUSTODY_NOT_GATE_OR_RUNTIME",
        "baseTree": BASE_TREE, "newTree": after["root"]["sha"],
        "rootEntries": len(entries(before["root"])), "changedRootTreesOnly": ["Modules", "docs"],
        "unchangedOtherModuleChildren": len(entries(before["modules"])) - 1,
        "originalModuleLeaves": 68, "newModuleLeaves": 69,
        "modifiedExistingSourceLeaves": 3, "addedProductSourceLeaves": 1,
        "unchangedExistingValidationChildren": len(old_validation), "newEvidenceLeaves": len(expected_docs),
        "protectedRootIdentities": {p: entries(after["root"])[p] for p in protected},
        "inventoryAndMapSubtree": entries(after["docs"])["any-engine-port"],
        "allOtherTrackedDescendantsRetainedByExactSubtreeIdentity": True,
        "sourceRetentionGateExecutedHere": False, "compilerOrRuntimeExecuted": False,
        "inputs": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                   for p in API.glob("*-*.primary.json") if p.name.startswith(("base-", "new-", "created-"))},
    }
    out = API / "actual-tree-verification.json"
    assert not out.exists(), "Retain prior verification attempts"
    out.write_text(json.dumps(proof, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": proof["status"], "tree": proof["newTree"], "proofSHA256": hashlib.sha256(out.read_bytes()).hexdigest(),
                      "newEvidenceLeaves": len(expected_docs)}))


if __name__ == "__main__": main()
