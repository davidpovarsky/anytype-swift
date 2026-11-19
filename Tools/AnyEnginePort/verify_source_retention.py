#!/usr/bin/env python3
"""Verify pinned source provenance and explicitly reviewed extraction mappings.

This is a preservation/review-map gate. It cannot prove semantic equivalence,
native runtime parity, UI acceptance, or physical-device behavior.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])

def tree_blobs(root: Path, ref: str, paths: list[str] | None = None) -> dict[str, str]:
    command = ["ls-tree", "-rz", "--full-tree", ref]
    if paths: command += ["--", *paths]
    result = {}
    for entry in git(root, *command).split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            result[path.decode("utf-8")] = metadata.decode().split()[2]
    return result

def read(root: Path, ref: str, path: str) -> bytes:
    return git(root, "show", f"{ref}:{path}")

def without_imports(data: bytes) -> list[str]:
    return [line for line in data.decode("utf-8").splitlines()
            if not re.match(r"^\s*(?:@testable\s+)?import\s+\w+\s*$", line)]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--ref", default="HEAD", help="Commit/tree to check; use git write-tree for a staged precommit gate.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    base = git(root, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
    head = git(root, "rev-parse", "HEAD").decode().strip()
    selected_tree = git(root, "rev-parse", "--verify", args.ref + "^{tree}").decode().strip()
    ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head],
                              capture_output=True, check=False).returncode == 0
    paths = ["Anytype/Sources", "AnyTypeTests", "Modules",
             "Tools/TorahNativeOperations", "Tools/PinkhaNativeDerived", "Tools/Hanlin/source.json"]
    baseline = tree_blobs(root, base)
    current = tree_blobs(root, selected_tree)
    baseline_protected = tree_blobs(root, base, paths)
    current_protected = tree_blobs(root, selected_tree, paths)
    inventory_root = "docs/any-engine-port/"
    sources = json.loads(read(root, selected_tree, inventory_root + "SOURCE_INVENTORY.json"))
    capabilities = json.loads(read(root, selected_tree, inventory_root + "CAPABILITY_INVENTORY.json"))
    errors = []
    if sources["baseline_commit"] != base or capabilities["baseline"]["commit"] != base:
        errors.append("Inventory source does not match pinned base")
    if sources["baseline_tree"] != git(root, "rev-parse", base + "^{tree}").decode().strip():
        errors.append("Inventory tree differs from pinned base")
    ids = [c["id"] for c in capabilities["capabilities"]]
    if len(ids) != len(set(ids)): errors.append("Duplicate capability IDs")
    listed = sources["entries"]
    for entry in listed + [s for c in capabilities["capabilities"] for s in c["sources"]]:
        if baseline.get(entry["path"]) != entry["git_blob"]:
            errors.append("Invalid source provenance: " + entry["path"])
    for capability in capabilities["capabilities"]:
        if not capability["acceptance"] or not capability["sources"]:
            errors.append("Missing contract/source: " + capability["id"])
        for test in capability["baseline_tests"]:
            if test not in baseline: errors.append("Missing baseline test: " + test)

    map_path = inventory_root + "SOURCE_REFACTOR_MAP.json"
    mapping = json.loads(read(root, selected_tree, map_path)) if map_path in current else {"changes": []}
    if mapping.get("changes") and (mapping.get("schemaVersion") != 1 or mapping.get("baselineCommit") != base):
        errors.append("Refactor mapping has incompatible schema/base")
    reviewed = {}
    verified = []
    for change in mapping.get("changes", []):
        old = change.get("from")
        if not old or old in reviewed or not change.get("reason") or not change.get("validation"):
            errors.append("Incomplete or duplicate reviewed mapping: " + str(old)); continue
        reviewed[old] = change
        if baseline_protected.get(old) != change.get("baselineBlob"):
            errors.append("Refactor baseline blob mismatch: " + old)
        kind = change.get("kind")
        destination = change.get("to")
        if kind == "move":
            if old in current: errors.append("Moved source still compiled at original path: " + old)
            if not destination or destination == old:
                errors.append("Invalid move destination: " + old)
        elif kind in ("refactor", "import_only"):
            if destination != old: errors.append("Refactor must retain original source path: " + old)
        else:
            errors.append("Unknown refactor kind: " + str(kind))
        if not destination or current.get(destination) != change.get("replacementBlob"):
            errors.append("Replacement blob mismatch: " + str(destination))
        if kind == "import_only" and destination in current:
            if without_imports(read(root, base, old)) != without_imports(read(root, selected_tree, destination)):
                errors.append("Import-only consumer changed implementation/test body: " + old)
        for shared in change.get("sharedSources", []):
            if current.get(shared["path"]) != shared["gitBlob"]:
                errors.append("Shared extracted source blob mismatch: " + shared["path"])
        verified.append({"kind": kind, "from": old, "to": destination,
                         "baselineBlob": change.get("baselineBlob"), "replacementBlob": change.get("replacementBlob")})

    changed = [path for path, blob in baseline_protected.items() if current.get(path) != blob]
    unreviewed = [path for path in changed if path not in reviewed]
    unused = [path for path in reviewed if path not in changed]
    if unused: errors.append("Stale mappings without a changed baseline source: " + ", ".join(unused))
    result = {
        "schemaVersion": 2, "base": base, "head": head, "checkedTree": selected_tree,
        "baseIsAncestor": ancestor, "protectedPaths": paths,
        "baselineFileCount": len(baseline_protected), "currentFileCount": len(current_protected),
        "unchangedBaselineFileCount": len(baseline_protected) - len(changed),
        "reviewedRefactors": verified, "unreviewedChangedExistingFiles": unreviewed,
        "inventoryCapabilityCount": len(ids), "inventorySourceCount": len(listed),
        "inventoryErrors": errors,
        "sourceRetentionPassed": ancestor and not errors and not unreviewed,
        "semanticEquivalence": "REQUIRES_INDEPENDENT_TEST_AND_REVIEW_EVIDENCE",
        "productParity": "NOT_PROVEN_BY_SOURCE_RETENTION",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["sourceRetentionPassed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
