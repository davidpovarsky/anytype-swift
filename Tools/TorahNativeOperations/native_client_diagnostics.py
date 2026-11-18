"""Fixed-schema diagnostics produced inside the current owned native-client run.

Only the controller's already secret-scanned, hash-bound publication is read.
No archive, URL, historical run, private error string, path or ID is exported.
These observations neither decide acceptance nor request another native call.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

STAGES = frozenset({"PREFLIGHT", "VERIFY_BUILD", "CREATE_NETWORK", "START_CREATOR", "WAIT_CREATOR",
                    "SEED_RECOVERED", "START_RECOVERED", "WAIT_RECOVERED", "VERIFY_PAIR",
                    "REQUEST_NATIVE_STOP", "WAIT_NATIVE_STOP", "VERIFY_FINAL", "COMPLETE",
                    "OFFLINE_SEQUENCE", "OFFLINE_REOPEN", "CRASH_ARM", "CRASH_KILL", "CRASH_RECOVER",
                    "OBSERVED_REMOVE_AFTER_REOPEN"})
ERRORS = {"ValueError": "CHECK_FAILED", "TimeoutError": "DEADLINE", "KeyboardInterrupt": "CANCELLED",
          "FileNotFoundError": "MISSING_FILE", "CalledProcessError": "PROCESS_FAILED",
          "PermissionError": "PERMISSION_FAILURE", "OSError": "FILESYSTEM_ERROR"}
READ_CODES = frozenset({"NULL", "UNKNOWN_ERROR", "BAD_INPUT", "UNSUPPORTED_VERSION", "PERMISSION_DENIED",
                        "NOT_LOGGED_IN", "ACCOUNT_CHANGED", "TARGET_UNAVAILABLE", "HISTORY_UNAVAILABLE",
                        "PROJECTION_BEHIND", "READ_LIMIT", "CANCELLED", "DEADLINE_EXCEEDED", "COLLISION",
                        "INVALID_ENVELOPE", "UNRECOGNIZED_CODE"})
PREFIX = r"(?:native_client_phase_test\.go:[0-9]+: )?"
READ = re.compile(PREFIX + r"T2_READ_OBSERVATION code=([A-Z_]+) snapshot_present=(true|false) readiness=(WAIT|READY|REJECTED)")
NATIVE_FIELDS = ("unknown_tree", "no_responsible_peers", "tree_closed", "tree_deleted", "space_closed",
                 "cancelled", "deadline", "context_nil", "context_peer_missing")
NATIVE = re.compile(r"T2_NATIVE_READ_BOUNDARY error_type=\S{1,160} unwrap_type=\S{1,160} "
                    + " ".join(name + r"=(true|false)" for name in NATIVE_FIELDS))
MAX_LOG_BYTES = 64 * 1024**2


def parse_fixed_records(data: bytes) -> dict:
    result = {"records": "NO_FIXED_RECORD", "last_read": "NOT_OBSERVED", "last_native_error": "NOT_OBSERVED"}
    for raw in data.splitlines():
        if b"T2_READ_OBSERVATION" not in raw and b"T2_NATIVE_READ_BOUNDARY" not in raw:
            continue
        line = raw.decode("ascii", errors="replace").strip()
        read, native = READ.fullmatch(line), NATIVE.fullmatch(line)
        if read and read[1] in READ_CODES:
            result["last_read"] = {"wire_code": read[1], "snapshot_present": read[2] == "true", "readiness": read[3]}
        elif native:
            fields = dict(zip(NATIVE_FIELDS, (value == "true" for value in native.groups())))
            # These are the original RPC context, not the target-lookup child.
            fields["outer_context_nil"] = fields.pop("context_nil")
            fields["outer_context_peer_missing"] = fields.pop("context_peer_missing")
            result["last_native_error"] = fields
        else:
            return {"records": "MALFORMED_FIXED_RECORD", "last_read": "WITHHELD", "last_native_error": "WITHHELD"}
        result["records"] = "FIXED_RECORDS_OBSERVED"
    return result


def read_current_published_log(evidence: Path, role: str, expected: str) -> bytes:
    if role not in {"creator", "recovered"} or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Unverified diagnostic input")
    root = evidence.resolve(strict=True)
    path = root / "native-clients" / role / "native.log"
    if path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError("Unverified diagnostic input")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_LOG_BYTES:
            raise ValueError("Unverified diagnostic input")
        data = stream.read(MAX_LOG_BYTES + 1)
    if len(data) > MAX_LOG_BYTES or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Unverified diagnostic input")
    return data


def summarize(receipt: dict, evidence: Path) -> dict:
    stage = receipt.get("diagnostic_stage")
    cleanup = receipt.get("owned_cleanup", {}).get("status")
    publication = receipt.get("native_publication", {})
    result = {"schema": "pinkha-t2-live-diagnostic-v1", "scope": "DIAGNOSTIC_ONLY_NO_ACCEPTANCE",
              "controller_stage": stage if stage in STAGES else "UNRECOGNIZED_STAGE",
              "controller_error": ERRORS.get(receipt.get("error_type"), "OTHER_ERROR" if receipt.get("error_type") else "NONE_OBSERVED"),
              "cleanup_error": ERRORS.get(receipt.get("cleanup_or_publication_error_type"),
                                           "OTHER_ERROR" if receipt.get("cleanup_or_publication_error_type") else "NONE_OBSERVED"),
              "finalization": {name: ERRORS.get(receipt.get(key), "OTHER_ERROR" if receipt.get(key) else "NONE_OBSERVED")
                               for name, key in [("permissions_error", "evidence_permissions_error_type"),
                                                 ("receipt_error", "receipt_write_error_type")]},
              "cleanup": {"PASS": "COMPLETE", "FAIL": "FAILED"}.get(cleanup, "NOT_OBSERVED"),
              "log_publication": "WITHHELD", "roles": {role: {"source": "WITHHELD"} for role in ["creator", "recovered"]}}
    if cleanup != "PASS" or publication.get("status") != "PASS_SECRET_SCANNED_EXACT_ALLOWLIST":
        return result
    result["log_publication"] = "CURRENT_RUN_SECRET_SCANNED"
    for role in result["roles"]:
        expected = publication.get("files_sha256", {}).get(role + "/native.log")
        try:
            data = read_current_published_log(evidence, role, expected)
            result["roles"][role] = {"source": "CURRENT_RUN_HASH_VERIFIED", **parse_fixed_records(data)}
        except Exception:
            # Cancellation remains a BaseException and reaches the controller's
            # existing finalization guard. Never format a caught exception.
            result["roles"][role] = {"source": "UNAVAILABLE_OR_HASH_MISMATCH"}
    return result


def emit_current_run_notice(receipt: dict, evidence: Path) -> None:
    try:
        result = summarize(receipt, evidence)
    except Exception:
        result = {"schema": "pinkha-t2-live-diagnostic-v1", "scope": "DIAGNOSTIC_ONLY_NO_ACCEPTANCE",
                  "diagnostic": "UNAVAILABLE"}
    # summarize constructs every exported key/value from fixed enums or bools.
    # Do not accept caller-supplied JSON as an annotation, or forward raw data.
    try:
        text = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        print("::notice title=Pinkha T2 diagnostic::" + text, flush=True)
    except Exception:
        # A closed stream or serialization failure is diagnostic-only. Keep
        # KeyboardInterrupt/SystemExit outside this ordinary-exception guard.
        pass
