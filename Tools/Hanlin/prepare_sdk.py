#!/usr/bin/env python3
"""Prepare one pinned canonical Hanlin product profile without editing its producer.

The existing --source / --check and verify(directory) interfaces are preserved.
Only generated dependency metadata is managed locally; original SDK files are
verified against immutable Git objects before importing the shared installer.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SOURCE = json.loads(Path(__file__).with_name("source.json").read_text())
LOCK = ROOT / SOURCE["lock"]
PIN = {**SOURCE, **json.loads(LOCK.read_text())}
DESTINATION = ROOT / "Dependencies/Hanlin"
MARKER = ".pinkha-source.json"
GENERATED = ("Package.swift", "docs/agent-sdk/unified-package-manifest.json")
URL = "https://github.com/davidpovarsky/hanlin-ai.git"


def command(arguments, cwd=ROOT):
    return subprocess.check_output(arguments, cwd=cwd, text=True, encoding="utf-8",
        stderr=subprocess.PIPE, timeout=180,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1"}).rstrip("\n")


def git(directory, *arguments):
    return command(["git", "--no-replace-objects", "-C", str(directory), *arguments])


def lock():
    value = json.loads(LOCK.read_text())
    if (SOURCE["repository"] != URL or not re.fullmatch(r"[a-f0-9]{40}", value.get("revision", ""))
            or not isinstance(value.get("products"), list) or not value["products"]
            or len(value["products"]) != len(set(value["products"]))
            or value != {name: PIN[name] for name in ("revision", "products")}):
        raise ValueError("Canonical Hanlin lock/source contract differs")
    return value


def original_inventory(directory, revision):
    rows = subprocess.check_output(["git", "--no-replace-objects", "-C", str(directory),
                                    "ls-tree", "-r", "-z", revision])
    result = {}
    for row in rows.split(b"\0"):
        if row:
            metadata, name = row.split(b"\t", 1)
            mode, kind, blob = metadata.split()
            result[name.decode()] = (mode, kind, blob.decode())
    return result


def source_record(directory):
    directory = Path(directory)
    selected = lock()
    revision = selected["revision"]
    if (directory.resolve() != DESTINATION.resolve() or git(directory, "rev-parse", "HEAD") != revision
            or git(directory, "remote", "get-url", "origin").rstrip("/").removesuffix(".git") != URL.removesuffix(".git")):
        raise ValueError("Installed Hanlin checkout differs from its canonical source pin")
    tree = original_inventory(directory, revision)
    state = json.loads((directory / ".hanlin-sdk/installation.json").read_text())
    source_paths = state.get("sourcePaths", [])
    if not source_paths:
        raise ValueError("Canonical selected source membership is missing")
    required = {name for name in tree if any(name == p or name.startswith(p + "/") for p in source_paths)}
    actual = set()
    for name in source_paths:
        location = directory / name
        candidates = [location] if location.is_file() else location.rglob("*")
        for path in candidates:
            if path.is_symlink():
                raise ValueError("A selected dependency source cannot contain symbolic links")
            if path.is_file():
                actual.add(path.relative_to(directory).as_posix())
    if actual != required:
        raise ValueError("Actual selected SDK directory membership differs from the original pin")
    rows = subprocess.check_output(["git", "-C", str(directory), "ls-files", "-t", "-z"]).decode()
    materialized = {row[2:] for row in rows.split("\0") if row and not row.startswith("S ")}
    names = sorted((required | materialized) - set(GENERATED))
    expected = {}
    for name in names:
        mode, kind, blob = tree.get(name, (None, None, None))
        if kind != b"blob" or mode not in (b"100644", b"100755") or not (directory / name).is_file():
            raise ValueError("Original selected SDK source is missing or unsupported: " + name)
        expected[name] = blob
    actual_blobs = subprocess.check_output(["git", "-C", str(directory), "hash-object", "--no-filters", "--stdin-paths"],
        input=("\n".join(names) + "\n").encode()).decode().splitlines()
    if len(actual_blobs) != len(names) or any(expected[name] != blob for name, blob in zip(names, actual_blobs)):
        raise ValueError("Installed SDK source bytes differ from the immutable canonical pin")
    if "Scripts/SDK/install.py" not in expected:
        raise ValueError("The shared installer was not verified")
    spec = importlib.util.spec_from_file_location("canonical_hanlin_installer", directory / "Scripts/SDK/install.py")
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    checked = installer.check(ROOT, LOCK, "Dependencies/Hanlin")
    command([sys.executable, "Scripts/SDK/generate_manifest.py", "--check", "--products", *selected["products"]], directory)
    package = json.loads(command(["swift", "package", "--package-path", str(directory), "dump-package"], directory))
    if ({p["name"] for p in package["products"]} != set(selected["products"])
            or installer.selected_source_paths(directory, package) != source_paths):
        raise ValueError("Installed SDK graph differs from the canonical product closure")
    if checked["binaryTargets"] or checked["managedNativeTargets"]:
        raise ValueError("This Anytype host profile must not prepare unrelated native runtimes")
    hashes = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
              for name in sorted(set(names) | set(GENERATED))}
    return {"revision": revision, "files": hashes, "repository": URL, "git_blobs": expected,
            "source_profile": {"products": selected["products"], "source_paths": source_paths,
                "generated_sha256": checked["generatedSHA256"], "binary_targets": checked["binaryTargets"]}}


def verify(directory):
    record = json.loads((Path(directory) / MARKER).read_text())
    actual = source_record(directory)
    if record != actual:
        raise ValueError("Existing Hanlin source receipt differs; preserve it and inspect manually")
    return record


def manage_marker(directory):
    # This one generated proof file is not SDK source. No tracked source or
    # generated Package.swift is ignored; both remain under the strict checks.
    exclude = Path(git(directory, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = directory / exclude
    text = exclude.read_text() if exclude.exists() else ""
    line = "/" + MARKER
    if line not in text.splitlines():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text + ("" if not text or text.endswith("\n") else "\n") + line + "\n")


def materialize(source):
    selected = lock()
    source = Path(source).resolve(strict=True)
    if git(source, "remote", "get-url", "origin").rstrip("/").removesuffix(".git") != URL.removesuffix(".git"):
        raise ValueError("The source cache is not the canonical Hanlin repository")
    if git(source, "rev-parse", selected["revision"] + "^{commit}") != selected["revision"]:
        raise ValueError("Unexpected Hanlin source revision")
    if DESTINATION.exists() and not (DESTINATION / ".git").exists():
        raise ValueError("Preserve the existing archived dependency; use a fresh managed SDK destination")
    if DESTINATION.exists() and (DESTINATION / MARKER).exists():
        # Existing generated proof is verified before any upgrade resets files.
        existing = json.loads((DESTINATION / MARKER).read_text())
        if existing.get("revision") == selected["revision"]:
            verify(DESTINATION)
        elif existing.get("revision") != git(DESTINATION, "rev-parse", "HEAD"):
            raise ValueError("Existing dependency marker/source identity differs")
    original = subprocess.check_output(["git", "--no-replace-objects", "-C", str(source),
                                       "show", selected["revision"] + ":Scripts/SDK/install.py"])
    with tempfile.TemporaryDirectory(prefix="hanlin-shared-installer-") as temporary:
        script = Path(temporary) / "install.py"
        script.write_bytes(original)
        command([sys.executable, str(script), "--host-root", str(ROOT),
                 "--destination", "Dependencies/Hanlin", "--source-cache", str(source)])
    manage_marker(DESTINATION)
    record = source_record(DESTINATION)
    (DESTINATION / MARKER).write_text(json.dumps(record, indent=2) + "\n")
    verify(DESTINATION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--github-output", type=Path, help="Write the validated immutable revision for checkout")
    args = parser.parse_args()
    if args.github_output:
        value = lock()
        with args.github_output.open("a") as output:
            output.write("revision=" + value["revision"] + "\n")
        return
    if args.check:
        verify(DESTINATION)
    elif args.source:
        materialize(args.source)
    else:
        parser.error("--source is required when preparing the SDK")
    print("Verified Hanlin " + PIN["revision"] + " at " + str(DESTINATION))


if __name__ == "__main__":
    main()
