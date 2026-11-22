#!/usr/bin/env python3
"""Install this isolated source overlay only after exact original/r14 preimages."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
parser.add_argument("--check-only", action="store_true")
args = parser.parse_args()
root = args.source_root.resolve(strict=True)
packet = Path(__file__).resolve().parent
composition = packet / "composition/r14"
bindings = json.loads((composition / "SOURCE_BINDINGS.json").read_bytes())
expected_head = "d98420b1113536afd08cde6de9a5816f6d27ffff"
head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
assert head == expected_head, "unexpected original Heart commit"
assert len(bindings) == 6, "unexpected overlay file inventory"
prepared = []
for item in bindings:
    relative = PurePosixPath(item["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    target = root.joinpath(*relative.parts)
    assert target.resolve().is_relative_to(root) and not target.is_symlink()
    source = composition / "native" / relative
    data = source.read_bytes()
    assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], "candidate source hash mismatch"
    before = None
    if item["must_be_absent"]:
        assert not target.exists(), "new observation file already exists"
    else:
        previous = target.read_bytes()
        before = hashlib.sha256(previous).hexdigest()
        assert any(before == allowed["sha256"] and len(previous) == allowed["bytes"] for allowed in item["expected_preimages"]), "original/r14 source preimage mismatch: " + item["path"]
    prepared.append((target, data, {"path": item["path"], "before_sha256": before, "after_sha256": item["sha256"]}))

# Every source and target is validated before the first reversible source write.
if not args.check_only:
    for target, data, _ in prepared:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for target, data, _ in prepared:
        assert target.read_bytes() == data, "source write readback mismatch"
receipt = {
    "status": "CHECKED_SOURCE_PREIMAGES_ONLY" if args.check_only else "INSTALLED_REVIEWED_SOURCE_OVERLAY",
    "original_commit": head,
    "r14_patch_sha256": "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
    "files": [record for _, _, record in prepared],
    "native_imports_executed": 0,
    "tests_executed": 0,
    "qualification": "source overlay only; full original module compilation and native import remain open",
}
args.receipt.parent.mkdir(parents=True, exist_ok=True)
args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
