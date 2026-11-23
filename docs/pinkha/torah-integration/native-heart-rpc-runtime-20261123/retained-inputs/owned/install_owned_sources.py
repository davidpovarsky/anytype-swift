#!/usr/bin/env python3
"""Install the reviewed owned-import proposal after exact compiled preimages.

This only changes source in a disposable original Heart checkout. It does not
initialize an app, execute an import, change modules or publish authority.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

parser = argparse.ArgumentParser(__doc__)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
parser.add_argument("--check-only", action="store_true")
args = parser.parse_args()
root = args.source_root.resolve(strict=True)
packet = Path(__file__).resolve().parent
composition = packet / "composition"
bindings = json.loads((composition / "SOURCE_MANIFEST.json").read_bytes())
head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
    capture_output=True, text=True, check=True, timeout=15).stdout.strip()
assert head == "d98420b1113536afd08cde6de9a5816f6d27ffff", "unexpected original Heart commit"
assert len(bindings) == len({item["path"] for item in bindings}) == 15
assert sum(item["preimage"] is not None for item in bindings) == 7
prepared = []
for item in bindings:
    relative = PurePosixPath(item["path"])
    assert relative.parts and not relative.is_absolute() and ".." not in relative.parts
    assert "\\" not in item["path"] and ":" not in item["path"] and relative.as_posix() == item["path"]
    target = root.joinpath(*relative.parts)
    source = composition / "native" / relative
    assert target.resolve().is_relative_to(root) and not target.is_symlink()
    assert source.resolve().is_relative_to(composition) and not source.is_symlink()
    data = source.read_bytes()
    assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
    before = None
    if item["preimage"] is None:
        assert not target.exists(), "new owned-import source already exists: " + item["path"]
    else:
        previous = target.read_bytes()
        before = hashlib.sha256(previous).hexdigest()
        assert len(previous) == item["preimage"]["bytes"] and before == item["preimage"]["sha256"], "compiled original preimage differs: " + item["path"]
    prepared.append((target, data, {"path": item["path"], "before_sha256": before, "after_sha256": item["sha256"]}))

# Validate every target before the first reversible source write.
if not args.check_only:
    for target, data, _ in prepared:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for target, data, _ in prepared:
        assert target.read_bytes() == data
receipt = {
    "status": "CHECKED_OWNED_SOURCE_PREIMAGES_ONLY" if args.check_only else "INSTALLED_REVIEWED_OWNED_SOURCE_OVERLAY",
    "original_commit": head,
    "compatible_origin_commit": "13f63c2dff32ff8ca6b864748843822fcdd0d004",
    "preimage_actual_compile_run": 45047489968,
    "files": [record for _, _, record in prepared],
    "native_imports_executed": 0, "tests_executed": 0,
    "qualification": "Source overlay only; full original module compilation, lifetime admission and native import remain separate gates.",
}
args.receipt.parent.mkdir(parents=True, exist_ok=True)
args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
