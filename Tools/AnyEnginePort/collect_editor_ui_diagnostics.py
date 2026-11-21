#!/usr/bin/env python3
"""Read only bounded noncontent Debug editor diagnostics from the owned app."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import subprocess
import uuid

PHASES = frozenset({
    "documentAppeared", "documentReadinessChanged", "documentSceneChanged",
    "emptyButtonTapped", "menuButtonTapped", "addParagraphEntered",
    "flushCompleted", "mutationReserved", "prewriteReadCompleted",
    "nativeCreationVerified", "mutationReadbackVerified", "readbackPublished",
    "addParagraphCompleted", "addParagraphFailed",
})
FLAGS = frozenset({
    "ownerMatches", "mounted", "active", "saving", "canMutate", "canWrite",
    "navigating", "draftReview", "composing", "foreground",
})
MAX_BYTES = 131_072
FILE_PATTERN = re.compile(r"pinkha-editor-ui-diagnostics-([0-9A-F-]{36})\.json")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def validate_events(value):
    require(type(value) is list and 0 < len(value) <= 256, "invalid_event_count")
    allowed = FLAGS | {"phase", "timestamp", "request", "errorType"}
    for event in value:
        require(type(event) is dict and set(event) <= allowed, "unexpected_diagnostic_field")
        require(event.get("phase") in PHASES, "invalid_diagnostic_phase")
        timestamp = event.get("timestamp")
        require(type(timestamp) in {int, float} and math.isfinite(timestamp), "invalid_timestamp")
        for key in FLAGS & set(event):
            require(type(event[key]) is bool, "invalid_boolean_field")
        if "request" in event:
            require(type(event["request"]) is str and
                    str(uuid.UUID(event["request"])).upper() == event["request"], "invalid_local_request")
        if "errorType" in event:
            require(type(event["errorType"]) is str and len(event["errorType"]) <= 128 and
                    re.fullmatch(r"[A-Za-z0-9_.<>: ()]+", event["errorType"]) is not None,
                    "invalid_error_type")
    return value


def bounded_file(path):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
            0 < before.st_size <= MAX_BYTES and not path.is_symlink(), "invalid_diagnostic_file")
    with path.open("rb") as source:
        data = source.read(MAX_BYTES + 1)
        after = source.fileno()
        import os
        current = os.fstat(after)
    require(len(data) == before.st_size and
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns),
            "diagnostic_file_changed_during_read")
    validate_events(json.loads(data))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "NOT_AVAILABLE",
              "scope": "noncontent_debug_diagnosis_only", "acceptance": False,
              "collectorNativeWrites": 0, "files": []}
    try:
        simulator = json.loads(args.simulator.read_text())
        owned = simulator["ownedUDID"]
        require(type(owned) is str and str(uuid.UUID(owned)).upper() == owned.upper(),
                "invalid_owned_simulator")
        record["ownedUDID"] = owned
        container = Path(subprocess.check_output([
            "xcrun", "simctl", "get_app_container", owned, "io.pinkha.anynative.dev", "data"
        ], text=True, stderr=subprocess.PIPE, timeout=30).strip()).resolve(strict=True)
        temporary = container / "tmp"
        require(temporary.is_dir() and not temporary.is_symlink(), "invalid_app_temporary_directory")
        candidates = sorted(temporary.glob("pinkha-editor-ui-diagnostics-*.json"))
        require(len(candidates) <= 64, "too_many_diagnostic_files")
        destination = args.output.parent / "editor-debug-events"
        for path in candidates:
            match = FILE_PATTERN.fullmatch(path.name)
            require(match is not None and str(uuid.UUID(match[1])).upper() == match[1],
                    "invalid_diagnostic_filename")
            require(path.parent.resolve() == temporary.resolve(), "diagnostic_outside_owned_container")
            data = bounded_file(path)
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / path.name
            target.write_bytes(data)
            record["files"].append({"name": path.name, "bytes": len(data),
                                    "sha256": hashlib.sha256(data).hexdigest(),
                                    "eventCount": len(json.loads(data))})
        if record["files"]:
            record["status"] = "COLLECTED"
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        # Neither arbitrary exception text nor a full native container is copied.
        record["status"] = "UNAVAILABLE_OR_INVALID"
        record["errorType"] = type(error).__name__
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record))
    return 0  # A diagnostic collector never supplies an acceptance pass.


if __name__ == "__main__":
    raise SystemExit(main())
