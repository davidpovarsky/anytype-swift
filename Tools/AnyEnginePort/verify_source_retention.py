#!/usr/bin/env python3
"""Verify this additive migration has not silently discarded the pinned old app.

This is an inventory/preservation gate, not a claim that retained source executes
against Any. Product parity requires independent runtime and UI acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    base = git(root, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
    head = git(root, "rev-parse", "HEAD").decode().strip()
    ancestor = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", base, head],
        check=False, capture_output=True,
    )
    # These paths contain the existing user capabilities, including the original
    # UI and Heart patches. New Any implementations live alongside them until
    # their replacement gates are proven. Compare Git blobs, not platform line
    # endings or a fragile count of filenames.
    paths = [
        "Anytype/Sources", "Modules",
        "Tools/TorahNativeOperations", "Tools/PinkhaNativeDerived",
        "Tools/Hanlin/source.json",
    ]
    changes = git(root, "diff", "--name-status", "--no-renames", base, "HEAD", "--", *paths).decode().splitlines()
    deleted = [line.split("\t", 1)[1] for line in changes if line.startswith("D\t")]
    changed = [line for line in changes if not line.startswith("A\t")]
    baseline_tree = git(root, "ls-tree", "-r", "--full-tree", base, "--", *paths)
    current_tree = git(root, "ls-tree", "-r", "--full-tree", "HEAD", "--", *paths)
    all_blobs = {}
    for entry in git(root, "ls-tree", "-rz", "--full-tree", base).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        all_blobs[path.decode("utf-8")] = metadata.decode().split()[2]
    inventory_root = root / "docs" / "any-engine-port"
    sources = json.loads((inventory_root / "SOURCE_INVENTORY.json").read_text(encoding="utf-8"))
    capabilities = json.loads((inventory_root / "CAPABILITY_INVENTORY.json").read_text(encoding="utf-8"))
    inventory_errors = []
    if sources["baseline_commit"] != base or capabilities["baseline"]["commit"] != base:
        inventory_errors.append("Inventory source does not match the pinned base")
    if sources["baseline_tree"] != git(root, "rev-parse", base + "^{tree}").decode().strip():
        inventory_errors.append("Inventory tree differs from the pinned base")
    listed = sources["entries"]
    ids = [capability["id"] for capability in capabilities["capabilities"]]
    if len(ids) != len(set(ids)):
        inventory_errors.append("Duplicate capability IDs")
    for entry in listed + [
        source for capability in capabilities["capabilities"] for source in capability["sources"]
    ]:
        if all_blobs.get(entry["path"]) != entry["git_blob"]:
            inventory_errors.append("Invalid source provenance: " + entry["path"])
    for capability in capabilities["capabilities"]:
        if not capability["acceptance"] or not capability["sources"]:
            inventory_errors.append("Missing contract/source: " + capability["id"])
        for test in capability["baseline_tests"]:
            if test not in all_blobs:
                inventory_errors.append("Missing baseline test: " + test)
    result = {
        "schemaVersion": 1,
        "base": base,
        "head": head,
        "baseIsAncestor": ancestor.returncode == 0,
        "baselineInventorySHA256": hashlib.sha256(baseline_tree).hexdigest(),
        "currentInventorySHA256": hashlib.sha256(current_tree).hexdigest(),
        "baselineFileCount": len(baseline_tree.splitlines()),
        "currentFileCount": len(current_tree.splitlines()),
        "protectedPaths": paths,
        "removedFiles": deleted,
        "changedExistingFiles": changed,
        "inventoryCapabilityCount": len(ids),
        "inventorySourceCount": len(listed),
        "inventoryErrors": inventory_errors,
        "sourceRetentionPassed": ancestor.returncode == 0 and not changed and not inventory_errors,
        "productParity": "NOT_PROVEN_BY_SOURCE_RETENTION",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["sourceRetentionPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
