"""Retain only this completed Native D run before a later checkout can clean it."""
from __future__ import annotations
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "native-ui-failed"
REPOSITORY = "davidpovarsky/anytype-swift"

def require(value, message):
    if not value:
        raise ValueError(message)

def original(path):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 32 * 1024**2,
            "nonregular_or_unbounded_journal")
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def absent_groups(commands, context):
    observations = []
    if not commands.exists():
        return observations
    require(commands.resolve() == commands and commands.is_dir(), "linked_command_directory")
    started = sorted(commands.glob("*.started.json"))
    require(len(started) <= 4096, "unbounded_command_journals")
    for path in started:
        record, checksum = original(path)
        require(record.get("context") == context, "foreign_command_context")
        pgid = record.get("pgid")
        require(type(pgid) is int and pgid > 1 and pgid != os.getpgrp(), "invalid_owned_group")
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError as failure:
            require(failure.errno == errno.ESRCH, "unproven_group_absence")
        else:
            raise RuntimeError("owned_command_group_still_exists")
        observations.append({"journal": path.name, "sha256": checksum, "pgid": pgid,
                             "kernelObservation": "ABSENT_ESRCH"})
    return observations

def retain():
    require(platform.system() == "Darwin" and platform.machine() == "arm64"
            and os.environ.get("GITHUB_ACTIONS") == "true"
            and os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "owned_apple_ci_required")
    run, attempt, source = (os.environ.get(k, "") for k in
                            ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA"))
    require(re.fullmatch("[1-9][0-9]*", run) and re.fullmatch("[1-9][0-9]*", attempt)
            and re.fullmatch("[0-9a-f]{40}", source), "fixed_run_identity_required")
    context = {"profile": PROFILE, "sourceCommit": source, "runID": run,
               "runAttempt": attempt, "repository": REPOSITORY}
    root = ROOT / "build" / ("current-apple-" + PROFILE + "-" + run + "-" + attempt)
    require(root.is_dir() and root.resolve() == root, "real_original_run_directory_required")
    before = root.lstat()
    require(stat.S_ISDIR(before.st_mode) and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) & 0o077 == 0, "private_owned_run_directory_required")
    evidence = root / "evidence"
    require(evidence.is_dir() and evidence.resolve() == evidence, "real_evidence_directory_required")
    journal_checksums = {}
    for name in ("execution-intent.json", "execution.json", "cleanup-final.json"):
        path = evidence / name
        if path.exists():
            record, checksum = original(path)
            if record.get("context") is not None:
                require(record["context"] == context, "foreign_run_context")
            journal_checksums[name] = checksum
    groups = absent_groups(evidence / "commands", context)
    # The D workflow has no actions/cache save step for this path. SwiftPM and
    # DerivedData below it belong to these now-absent journaled build processes.
    # No shared cache, source checkout, or other run directory is moved.
    base = Path("/Users/m1/builds/_retained-anytype")
    require(base.is_dir() and base.resolve() == base, "real_retention_base_required")
    parent = base / (run + "-" + attempt)
    if not parent.exists():
        parent.mkdir(mode=0o700)
    require(parent.is_dir() and parent.resolve() == parent and parent.stat().st_uid == os.getuid(),
            "owned_retention_parent_required")
    build = parent / "build"
    if not build.exists():
        build.mkdir(mode=0o700)
    require(build.is_dir() and build.resolve() == build and build.stat().st_uid == os.getuid(),
            "owned_retention_build_parent_required")
    destination = build / root.name
    receipt = parent / "native-ui-retention.json"
    require(not destination.exists() and not destination.is_symlink()
            and not receipt.exists() and not receipt.is_symlink(), "retention_destination_already_exists")
    # Repeat kernel absence immediately before atomic same-volume rename.
    require(absent_groups(evidence / "commands", context) == groups, "owned_groups_changed")
    root.rename(destination)
    after = destination.lstat()
    require(not root.exists() and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
            "original_root_identity_not_preserved")
    value = {"status": "OWNED_COMPLETED_ROOT_RETAINED", "context": context,
             "originalPath": str(root), "retainedPath": str(destination),
             "originalDevice": before.st_dev, "originalInode": before.st_ino,
             "atomicSameVolumeRename": True, "originalJournalSHA256": journal_checksums,
             "ownedCommandGroups": groups, "privateDirectoryModePreserved": True,
             "otherRunsOrSharedCachesMoved": False, "testResultsRelabeled": False}
    with receipt.open("x") as stream:
        os.chmod(receipt, 0o600)
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": value["status"], "retainedPath": str(destination),
                      "receipt": str(receipt), "ownedAbsentGroups": len(groups),
                      "testResultsRelabeled": False}))

if __name__ == "__main__":
    retain()
