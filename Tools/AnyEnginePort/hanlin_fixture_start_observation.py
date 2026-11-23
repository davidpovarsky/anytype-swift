"""Observe one owned fixture starter without publishing private output.

This observer does not admit provider readiness, test acceptance, process absence,
or cleanup. The original caller retains its fixed failure gate and cleanup owner.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

TIMEOUT_SECONDS = 90
FIXED_FAILURE_CODES = frozenset(['allowed_creation_not_empty_success', 'assistant_tool_call_shape', 'assistant_tool_calls', 'call_reissued', 'cancel_creation_was_not_refused', 'canonical_builder_compile', 'canonical_builder_execute', 'canonical_chunk_count', 'canonical_materialized_source', 'canonical_response_contract', 'canonical_source_changed', 'canonical_source_pin', 'canonical_sse_framing', 'canonical_vector_count', 'certificate_command_failed', 'certificate_path', 'changed_historical_tool_result', 'changed_tool_identity_or_arguments', 'child_identity_unavailable', 'child_receipt_mismatch', 'concurrent_provider_request', 'control_origin', 'control_request_failed', 'control_response_framing', 'control_response_length', 'control_response_truncated', 'creation_tool_unavailable', 'duplicate_json_key', 'fixture_already_failed', 'fixture_child_exited', 'fixture_deadline', 'fixture_protocol_incomplete', 'fixture_start_deadline', 'get_with_body', 'http_headers_size', 'http_host', 'http_request_limit', 'http_version', 'invalid_json', 'json_complexity', 'json_key', 'json_size', 'lifecycle_actual_sse', 'lifecycle_assertion_failed', 'lifecycle_command_failed', 'lifecycle_delivery_capture_deadline', 'lifecycle_final_gate_failed', 'lifecycle_output_shape', 'lifecycle_ready_capture', 'lifecycle_registration', 'lifecycle_status_capture', 'listener_port', 'listener_table_changed_repeatedly', 'listener_table_query', 'listener_table_shape', 'listener_table_size', 'listener_table_size_query', 'listener_table_state', 'message_role', 'missing_tool_result', 'nonfinite_json', 'nonloopback_client', 'openssl_unavailable', 'orphan_or_duplicate_tool_result', 'output_symlink', 'owned_child_exit_deadline', 'owned_handler_shutdown_deadline', 'owned_listener_status_unknown', 'owned_listener_still_accepting', 'private_config_ca_changed', 'private_config_contract', 'private_config_directory', 'private_config_missing', 'private_config_permissions', 'private_config_run', 'private_config_size', 'private_config_tls_path', 'private_config_token', 'private_directory_not_empty', 'private_directory_permissions', 'private_directory_symlink', 'process_birth_unavailable', 'process_id', 'process_status_shape', 'process_status_unavailable', 'provider_delivery_deadline', 'provider_messages', 'provider_model_or_stream', 'provider_object', 'provider_round_overflow', 'read_catalog_consent', 'request_authentication', 'request_body_truncated', 'request_content_length', 'request_content_type', 'request_query', 'request_transfer_encoding', 'response_delivery_order', 'safe_report_inside_private_directory', 'scenario_already_registered', 'scenario_blank', 'scenario_canaries_overlap', 'scenario_canary_in_title', 'scenario_fields', 'scenario_required', 'scenario_titles_overlap', 'selected_snapshot_block_or_text', 'selected_snapshot_coverage_or_title', 'selected_snapshot_fields', 'selected_snapshot_wrong_object', 'selected_snapshot_wrong_space', 'shutdown_body', 'shutdown_child_identity', 'shutdown_deadline', 'shutdown_refused', 'shutdown_startup_unresolved', 'source_disclosed_before_read_result', 'startup_failure_unproven', 'status_contract', 'stop_receipt_mismatch', 'tool_alias', 'tool_catalog_size', 'tool_descriptor', 'tool_function_fields', 'tool_result_shape', 'tool_schema', 'unexpected_before_read_history', 'unexpected_denied_history', 'unexpected_fixture_failure', 'unexpected_provider_strict_mode', 'unissued_or_duplicate_call', 'unknown_route', 'unselected_source_disclosed', 'user_content', 'wrong_pending_continuation', 'wrong_send_prompt'])


def _write(path: Path, raw: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
    finally:
        os.close(fd)


def _fixed_error(raw: bytes) -> dict | None:
    if not raw or len(raw) > 4096:
        return None

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate key")
            value[key] = item
        return value

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, ValueError, TypeError):
        return None
    if not isinstance(value, dict) or set(value) != {"schema", "status", "code"}:
        return None
    if type(value["schema"]) is not int or value["schema"] != 1:
        return None
    if value["status"] != "FIXTURE_ERROR" or not isinstance(value["code"], str):
        return None
    if value["code"] not in FIXED_FAILURE_CODES:
        return None
    return value


def observe_start(command: list[str], *, cwd: Path, private_dir: Path, safe_dir: Path) -> dict:
    """Preserve exact starter bytes privately and publish only finite metadata."""
    private_dir, safe_dir = Path(private_dir), Path(safe_dir)
    private = private_dir.lstat()
    if (not stat.S_ISDIR(private.st_mode) or private_dir.is_symlink()
            or stat.S_IMODE(private.st_mode) != 0o700
            or (hasattr(os, "getuid") and private.st_uid != os.getuid())
            or not safe_dir.is_dir() or safe_dir.is_symlink()
            or safe_dir.resolve().is_relative_to(private_dir.resolve())):
        raise ValueError("invalid owned diagnostic directories")
    report = {
        "schemaVersion": 1,
        "scope": "OWNED_FIXTURE_STARTER_OBSERVATION_ONLY",
        "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "timeoutSeconds": TIMEOUT_SECONDS,
        "outcome": "INTERRUPTED",
        "returnCode": None,
        "errorClass": None,
        "privateRawOutputPublished": False,
        "providerReadinessAccepted": False,
        "ownedChildAbsenceProved": False,
    }
    started = time.monotonic()
    stdout = stderr = b""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=TIMEOUT_SECONDS)
        stdout, stderr = result.stdout, result.stderr
        if not isinstance(stdout, bytes) or not isinstance(stderr, bytes) or type(result.returncode) is not int:
            raise ValueError("invalid starter process result")
        report.update(outcome="COMPLETED" if result.returncode == 0 else "NONZERO_EXIT",
                      returnCode=result.returncode)
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b"", error.stderr or b""
        report.update(outcome="TIMED_OUT", errorClass="TimeoutExpired")
    except OSError as error:
        report.update(outcome="OS_ERROR", errorClass="OSError",
                      errno=error.errno if type(error.errno) is int else None)
    finally:
        if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
            stdout = stderr = b""
            report.update(outcome="INVALID_CAPTURE", errorClass="InvalidOutputType")
        for name, raw in [("stdout", stdout), ("stderr", stderr)]:
            _write(private_dir / ("starter." + name), raw, 0o600)
            report[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                            "retention": "PRIVATE_OWNED_ROOT_UNTIL_EXISTING_CLEANUP"}
        fixed = _fixed_error(stdout)
        if fixed is not None:
            # Only this exact bounded, duplicate-free, finite-code protocol record
            # is safe to copy byte-for-byte. Arbitrary child text stays private.
            public_name = "starter-fixed-error.original.json"
            _write(safe_dir / public_name, stdout, 0o644)
            report["fixedFixtureError"] = fixed
            report["fixedFixtureErrorOriginal"] = {
                "path": public_name, "bytes": len(stdout),
                "sha256": hashlib.sha256(stdout).hexdigest()}
        report.update(finishedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      elapsedSeconds=max(0.0, time.monotonic() - started))
        _write(safe_dir / "starter-observation.json",
               (json.dumps(report, sort_keys=True, indent=2) + "\n").encode(), 0o644)
    return report
