#!/usr/bin/env python3
"""Materialize immutable canonical Hanlin packages without touching a producer checkout.

Usage: python3 Tools/Hanlin/prepare_sdk.py --source /path/to/hanlin-ai
The source must already contain the pinned commit. This script never fetches,
checks out, resets, stages, commits or changes that repository's working files.
Run before Xcode resolves Anytype.xcodeproj's nested local package references.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PIN = json.loads((Path(__file__).with_name("source.json")).read_text())
DESTINATION = ROOT / "Dependencies" / "Hanlin"
MARKER = ".pinkha-source.json"


def git(source, *arguments):
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(source), *arguments], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("A dependency snapshot cannot contain symbolic links")
        if path.is_file() and path != directory / MARKER:
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify(directory):
    record = json.loads((directory / MARKER).read_text())
    if record.get("revision") != PIN["revision"] or record.get("files") != hashes(directory):
        raise ValueError("Existing Hanlin snapshot differs from its pin; preserve it and inspect manually")
    for package in PIN["packages"]:
        if not (directory / package / "Package.swift").is_file():
            raise ValueError("Canonical nested package is absent: " + package)
    return record


def materialize(source):
    resolved = git(source, "rev-parse", PIN["revision"] + "^{commit}").decode().strip()
    if resolved != PIN["revision"]:
        raise ValueError("Unexpected Hanlin source revision")
    if DESTINATION.exists():
        verify(DESTINATION)
        return
    archive = git(source, "archive", "--format=tar", PIN["revision"], *PIN["packages"])
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hanlin-prepare-", dir=DESTINATION.parent) as temporary:
        stage = Path(temporary) / "snapshot"
        stage.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            for member in bundle:
                relative = PurePosixPath(member.name)
                if relative.is_absolute() or ".." in relative.parts or not (member.isfile() or member.isdir()):
                    raise ValueError("Unsafe entry in canonical dependency archive")
                target = stage.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                stream = bundle.extractfile(member)
                if stream is None:
                    raise ValueError("Missing archived dependency file")
                data = stream.read()
                if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                    raise ValueError("Pinned Hanlin archive needs a producer-provided LFS materialization")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        record = {"revision": PIN["revision"], "files": hashes(stage)}
        (stage / MARKER).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        verify(stage)
        stage.rename(DESTINATION)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    if options.check:
        verify(DESTINATION)
    elif options.source:
        materialize(options.source)
    else:
        parser.error("--source is required when preparing the snapshot")
    print("Verified Hanlin " + PIN["revision"] + " at " + str(DESTINATION))


if __name__ == "__main__":
    main()
