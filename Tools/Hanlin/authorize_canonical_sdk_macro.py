#!/usr/bin/env python3
"""Authorize one canonical SDK macro after immutable source verification.

Uses the exact target/revision mechanism proven by Maktabah's original
hq-stage2-focused-apple.py. Xcode fingerprint validation stays enabled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import tempfile

REVISION = "597c2bb34af0c51331eb3b5e705f942d8ee20daa"
PACKAGE_IDENTITY = "equatable"
TARGET_NAME = "EquatableMacros"
ORIGIN = "https://github.com/ordo-one/equatable"
LOCK_PATH = Path("Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")
BRANCH = "codex/chatgpt-wave15-canonical-hanlin-20261123"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def verify_source(app, derived):
    """Check lock, actual commit, original bytes/modes and source membership."""
    lock_path = app / LOCK_PATH
    require(not lock_path.is_symlink(), "Linked package lock")
    lock_bytes = lock_path.read_bytes()
    lock = json.loads(lock_bytes)
    pins = [row for row in lock["pins"] if row["identity"] == PACKAGE_IDENTITY]
    require(len(pins) == 1, "Expected exactly one Equatable package pin")
    pin = pins[0]
    require(pin["kind"] == "remoteSourceControl"
            and pin["location"].removesuffix(".git") == ORIGIN
            and pin["state"] == {"revision": REVISION, "version": "1.4.1"},
            "Equatable reviewed package/version/revision differs")
    root = derived / "SourcePackages/checkouts/equatable"
    require(root.is_dir() and not root.is_symlink()
            and root.resolve().is_relative_to(derived.resolve()), "Missing or linked Equatable checkout")
    require(git(root, "rev-parse", "HEAD").decode().strip() == REVISION, "Equatable checkout revision differs")
    # SwiftPM makes non-editable working copies with git clone --shared from
    # its local repository cache. Bind provenance to the immutable lock and
    # actual content-addressed revision, not that local cache path.
    checkout_origin = git(root, "remote", "get-url", "origin").decode().strip()
    require(not git(root, "status", "--porcelain", "--untracked-files=all").strip(), "Equatable checkout is dirty")
    original = {}
    for record in git(root, "ls-tree", "-rz", "HEAD").split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = root / name.decode()
        require(kind == "blob" and mode in {"100644", "100755", "120000"}, "Unexpected macro source tree member")
        require(path.resolve().is_relative_to(root.resolve()), "Escaping macro source path")
        if mode == "120000":
            require(path.is_symlink(), "Macro source link kind changed")
            raw = os.readlink(path).encode()
        else:
            require(path.is_file() and not path.is_symlink(), "Macro source file kind changed")
            require(bool(path.stat().st_mode & 0o111) == (mode == "100755"), "Macro source executable mode changed")
            raw = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(blob == oid, "Macro source bytes changed: " + name.decode())
        original[name.decode()] = {"mode": mode, "blob": oid, "sha256": digest(raw)}
    require("Package.swift" in original, "Macro package manifest missing")
    require('name: "EquatableMacros"' in (root / "Package.swift").read_text(), "Reviewed macro target absent")
    for directory in ["Sources", "Plugins"]:
        base = root / directory
        if not base.exists():
            continue
        actual = {str(p.relative_to(root)) for p in base.rglob("*") if p.is_file() or p.is_symlink()}
        expected = {p for p in original if p.startswith(directory + "/")}
        require(actual == expected, "Untracked or omitted macro compilation input")
    return {"package": PACKAGE_IDENTITY, "target": TARGET_NAME, "revision": REVISION,
            "lock_sha256": digest(lock_bytes), "source_files": original,
            "checkout_origin": checkout_origin, "source_verified_clean": True}


def authorize(source, security_directory):
    """Add one exact fingerprint atomically; preserve unrelated authorizations."""
    require(source.get("source_verified_clean") is True
            and source.get("package") == PACKAGE_IDENTITY
            and source.get("target") == TARGET_NAME
            and source.get("revision") == REVISION, "Unverified macro source")
    directory = Path(security_directory)
    path = directory / "macros.json"
    require(not directory.is_symlink() and not path.is_symlink(), "Linked compiler authorization store")
    try:
        before = path.read_bytes()
    except FileNotFoundError:
        before = None
    entries = json.loads(before) if before is not None else []
    require(isinstance(entries, list) and all(
        isinstance(row, dict) and all(isinstance(row.get(key), str) and row[key]
        for key in ("fingerprint", "packageIdentity", "targetName")) for row in entries),
        "Existing macro authorization schema differs")
    entry = {"fingerprint": REVISION, "packageIdentity": PACKAGE_IDENTITY, "targetName": TARGET_NAME}
    added = entry not in entries
    if added:
        directory.mkdir(parents=True, exist_ok=True)
        mode = stat.S_IMODE(path.stat().st_mode) if before is not None else 0o600
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                    prefix=".canonical-hanlin-macro-", dir=directory, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump([*entries, entry], stream, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, mode)
            current = path.read_bytes() if path.exists() else None
            require(current == before and not path.is_symlink(), "Compiler authorization changed during update")
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    after = path.read_bytes()
    require(json.loads(after) == ([*entries, entry] if added else entries),
            "Compiler authorizations were not preserved exactly")
    return {"entry": entry, "entry_added": added, "existing_entries_preserved": True,
            "existing_entry_count": len(entries), "normal_xcode_fingerprint_validation": True,
            "global_validation_disabled": False, "before_sha256": digest(before) if before else None,
            "after_sha256": digest(after)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    app, derived, evidence = args.app.resolve(), args.derived.resolve(), args.evidence.resolve()
    require(platform.system() == "Darwin", "Actual Apple runner required")
    require(git(app, "rev-parse", "HEAD").decode().strip() == os.environ.get("GITHUB_SHA")
            and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("UI27_ACCEPTANCE_LANE") == "hanlin-native",
            "Only the exact canonical native consumer is admitted")
    evidence.mkdir(parents=True, exist_ok=True)
    lock_before = (app / LOCK_PATH).read_bytes()
    report = {"status": "FAIL", "source_sha": os.environ["GITHUB_SHA"],
              "run_id": os.environ["GITHUB_RUN_ID"], "tests_executed": 0}
    try:
        argv = ["xcodebuild", "-resolvePackageDependencies", "-project", "Anytype.xcodeproj",
                "-scheme", "Anytype", "-configuration", "Debug-Anytype",
                "-derivedDataPath", str(derived), "-onlyUsePackageVersionsFromResolvedFile"]
        report["resolve_command"] = argv
        with (evidence / "canonical-macro-resolve.log").open("wb") as stream:
            subprocess.run(argv, cwd=app, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1800)
        require((app / LOCK_PATH).read_bytes() == lock_before, "Package resolution modified the immutable lock")
        source = verify_source(app, derived)
        trust = authorize(source, Path.home() / "Library/org.swift.swiftpm/security")
        require(verify_source(app, derived) == source, "Macro source changed during authorization")
        report.update(status="PASS_EXACT_MACRO_SOURCE_AND_FINGERPRINT", source=source, authorization=trust)
    except BaseException as error:
        report.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (evidence / "canonical-macro-authorization.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "source"}))


if __name__ == "__main__":
    main()
