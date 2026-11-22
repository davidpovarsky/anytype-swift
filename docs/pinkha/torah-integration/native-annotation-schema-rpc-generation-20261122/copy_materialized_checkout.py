#!/usr/bin/env python3
"""Copy a materialized original Git checkout without serving or fetching objects.

The parent owns this finite child process and its fresh target directory. This
does not hydrate a partial repository, change its sparse scope or generate code.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess


def git(root, *args):
    env = os.environ.copy()
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"})
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("local checkout inspection failed: " + args[0])
    return result.stdout.decode("utf-8").rstrip("\r\n")


def inspect_checkout(root, expected_head):
    metadata = root / ".git"
    if not metadata.is_dir() or metadata.is_symlink():
        raise RuntimeError("a private ordinary Git directory is required")
    for relative in ("commondir", "worktrees", "objects/info/alternates", "objects/info/http-alternates"):
        if os.path.lexists(metadata / relative):
            raise RuntimeError("shared or alternate Git storage is refused")
    for name in ("config", "config.worktree"):
        config = metadata / name
        if not config.exists():
            continue
        fields = git(root, "config", "--file", str(config), "--no-includes", "--null", "--list").split("\0")
        for field in fields:
            key = field.partition("\n")[0].lower()
            if key.startswith(("include.", "includeif.")) or key in ("core.worktree", "core.hookspath"):
                raise RuntimeError("external Git configuration is refused")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise RuntimeError("Git worktree resolves outside its owned root")
    if Path(git(root, "rev-parse", "--absolute-git-dir")).resolve() != metadata:
        raise RuntimeError("Git metadata resolves outside its owned root")
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if Path(common).resolve() != metadata:
        raise RuntimeError("Git common directory is shared")
    if git(root, "rev-parse", "HEAD") != expected_head:
        raise RuntimeError("original commit differs")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("original materialized checkout is not clean")


def inventory(root):
    rows = []
    for path in sorted(root.rglob("*")):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise RuntimeError("non-regular materialized source is refused")
        relative = path.relative_to(root).as_posix()
        row = {"path": relative, "mode": stat.S_IMODE(mode), "kind": "directory"}
        if stat.S_ISREG(mode):
            raw = path.read_bytes()
            row.update({"kind": "file", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    source, target = args.source.resolve(strict=True), args.target.resolve()
    receipt = args.receipt.resolve()
    if os.path.lexists(args.target) or source == target or source in target.parents or target in source.parents:
        raise RuntimeError("fresh disjoint target is required")
    if receipt == source or source in receipt.parents or receipt == target or target in receipt.parents:
        raise RuntimeError("copy receipt must remain outside both source trees")
    # Refuse environment overrides that could redirect even a local Git read.
    if any(os.environ.get(key) for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES")):
        raise RuntimeError("external Git storage override is refused")
    before = inventory(source)
    inspect_checkout(source, args.expected_head)
    if inventory(source) != before:
        raise RuntimeError("source changed during initial readback")
    shutil.copytree(source, target, copy_function=shutil.copy2, symlinks=False)
    if inventory(target) != before:
        raise RuntimeError("copied bytes, membership or modes differ")
    for row in before:
        if row["kind"] == "file" and os.path.samefile(source / row["path"], target / row["path"]):
            raise RuntimeError("copy shares a file identity with its source")
    inspect_checkout(target, args.expected_head)
    if inventory(source) != before or inventory(target) != before:
        raise RuntimeError("source or copy changed during readback")
    encoded = json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
    result = {
        "schema": "otzaria.materialized-original-checkout-copy/1", "status": "EXACT_PRIVATE_COPY",
        "source": str(source), "target": str(target), "head": args.expected_head,
        "files": sum(row["kind"] == "file" for row in before),
        "directories": sum(row["kind"] == "directory" for row in before),
        "bytes": sum(row.get("bytes", 0) for row in before),
        "inventory_sha256": hashlib.sha256(encoded).hexdigest(),
        "source_and_copy_unchanged_after_readback": True, "file_identities_disjoint": True,
        "lazy_fetch_disabled_for_git_reads": True, "remote_clone_or_hydration": False,
        "scope": "Already materialized source and private Git metadata only; no generator or product execution.",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
