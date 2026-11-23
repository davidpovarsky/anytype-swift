#!/usr/bin/env python3
"""Export only original Go test metadata and hashes; native stdout remains private."""
import argparse
import hashlib
import json
from pathlib import Path

FIELDS = {"Time", "Action", "Package", "Test", "Elapsed"}
PACKAGE = "github.com/anyproto/anytype-heart/clientlibrary/service"
METHODS = {
    "capture": "TestSemanticAnchorNativePageCaptureAndWire",
    "cold-reopen": "TestSemanticAnchorNativePageColdReopen",
}

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def export(run):
    private = run / "private/account-sequence"
    evidence = run / "evidence/named-go-events"
    evidence.mkdir(exist_ok=False)
    result = {"metadata_fields": sorted(FIELDS), "raw_logs_exported": False, "phases": {}}
    for phase, method in METHODS.items():
        log = private / (phase + ".jsonl")
        if not log.is_file():
            result["phases"][phase] = {"status": "NOT_RUN_NO_RAW_LOG", "method": method}
            continue
        rows = []
        with log.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                original = json.loads(line)
                if original.get("Package") != PACKAGE:
                    raise ValueError("Unexpected package in private log")
                if "Test" in original and original["Test"] != method:
                    raise ValueError("An unselected method appeared in the private log")
                if original.get("Action") not in {"start", "run", "pause", "cont", "pass", "bench", "fail", "output", "skip"}:
                    raise ValueError("Unknown Go event action")
                rows.append({key: value for key, value in original.items() if key in FIELDS})
        target = evidence / (phase + ".jsonl")
        with target.open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        named = [row["Action"] for row in rows if row.get("Test") == method
            and row["Action"] in {"run", "pass", "fail", "skip"}]
        package = [row["Action"] for row in rows if "Test" not in row and row["Action"] in {"pass", "fail", "skip"}]
        status = "PASS" if named == ["run", "pass"] and package == ["pass"] else "FAIL_OR_INCOMPLETE"
        result["phases"][phase] = {"method": method, "status": status,
            "original_private_log_sha256": digest(log), "original_private_log_bytes": log.stat().st_size,
            "metadata_sha256": digest(target), "metadata_event_count": len(rows),
            "named_actions": named, "package_terminal_actions": package}
    target = evidence / "AUDIT.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "EXPORTED_ORIGINAL_GO_EVENT_METADATA",
        "phases": {name: row["status"] for name, row in result["phases"].items()},
        "raw_logs_exported": False}))
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    export(args.run.resolve())
