"""Exact coherent Release cleanup recovery; never product acceptance or retry."""
from functools import partial
import json
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace

import wave15_batch as batch

PROFILE = batch.COHERENT_HEART_PROFILE


def readiness_commands(pair):
    """Opt in only the coherent readiness adapter; ordinary T5 calls stay at 2s."""
    return SimpleNamespace(require=pair.require, digest=pair.digest, write=pair.write,
                           run_logged=partial(pair.run_logged, cleanup_profile=PROFILE))


def _original(path, root):
    batch.require(path.is_file() and not path.is_symlink()
                  and path.resolve().is_relative_to(root.resolve())
                  and path.stat().st_size <= 1024 * 1024,
                  "Nested original owned receipt is missing, escaped or unbounded")
    value = json.loads(path.read_bytes())
    batch.require(isinstance(value, dict), "Nested command receipt is not an object")
    return value


def audit_nested_receipts(roots, app, private_work, report):
    """Audit pinned originals once; retain failed projections without relabelling."""
    from run_owned_single_lane import verify_owned_group_stopped
    originals = {}
    for root in roots:
        if not root.exists():
            continue
        batch.require(root.is_dir() and not root.is_symlink() and root.resolve().is_relative_to(app),
                      "Nested receipt root escaped the owned App work")
        for path in sorted(root.rglob("*.command.json")):
            if root != private_work and {"actual", "actual-native"}.intersection(path.relative_to(root).parts):
                continue
            value = _original(path, root)
            projection = None
            if "original_owned_command" in value:
                name = value["original_owned_command"]
                batch.require(isinstance(name, str) and len(name) <= 200
                              and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.owned\.command\.json", name),
                              "Nested projected receipt has no exact owned basename")
                original = path.parent / name
                data = _original(original, root)
                batch.require(batch.digest(original) == value.get("original_owned_command_sha256")
                              and type(data.get("worker_pid")) is int
                              and value.get("controller_process_id") == data["worker_pid"]
                              and value.get("argv") == data.get("argv")
                              and value.get("cwd") == data.get("cwd")
                              and value.get("return_code") == data.get("return_code")
                              and value.get("owned_group_termination") == data.get("owned_group_cleanup")
                              == "TERM_THEN_KILL",
                              "Nested projection differs from its exact original owned command")
                projection = dict(path=path.relative_to(app).as_posix(), sha256=batch.digest(path),
                                  status=value.get("status"),
                                  original_owned_command_sha256=value["original_owned_command_sha256"],
                                  prior_quiescence=value.get("owned_group_quiescence"),
                                  cleanup_error_type=value.get("cleanup_error_type"),
                                  cleanup_error=value.get("cleanup_error"),
                                  cleanup_probe_timeouts=value.get("cleanup_probe_timeouts", []))
            elif "worker_pid" in value:
                original, data = path, value
            else:
                continue
            key = original.resolve()
            sha = batch.digest(original)
            row = originals.setdefault(key, dict(path=original.relative_to(app).as_posix(),
                sha256=sha, original_command_status=data.get("status"),
                original_return_code=data.get("return_code"), projections=[]))
            batch.require(row["sha256"] == sha, "Nested original command changed during receipt admission")
            if projection is not None:
                row["projections"].append(projection)
    report["original_owned_commands"] = []
    for original, row in sorted(originals.items(), key=lambda item: str(item[0])):
        report["original_owned_commands"].append(row)
        batch.require(batch.digest(original) == row["sha256"], "Nested original changed before its cleanup observation")
        try:
            state = verify_owned_group_stopped(original, cleanup_profile=PROFILE)
            batch.require(batch.digest(original) == row["sha256"], "Nested original changed during cleanup observation")
            row.update(state, evidence_scope="CLEANUP_ONLY_ORIGINAL_COMMAND_AND_PRODUCT_STATUS_UNCHANGED")
            report["groups_checked"] = report.get("groups_checked", 0) + 1
        except BaseException as error:
            row.update(status="FAIL", error_type=type(error).__name__, error=str(error),
                       timeout_observations=getattr(error, "timeout_observations", []))
            raise


def reconcile_delete_timeout(device, error, *, entry, report, baseline_udids, deadline):
    """Observe only the same verified owned UUID within the caller's original 180s."""
    argv = ["xcrun", "simctl", "delete", device["udid"]]
    batch.require(isinstance(error, subprocess.TimeoutExpired) and error.cmd == argv
                  and batch.valid_udid(device["udid"])
                  and device["udid"].lower() not in {value.lower() for value in baseline_udids},
                  "Delete reconciliation requires the original nonbaseline owned UUID")
    detail = dict(status="DELETE_OUTCOME_UNCERTAIN", original_error_type=type(error).__name__,
                  original_error=str(error), original_timeout_seconds=error.timeout,
                  same_owned_udid=device["udid"], deadline_reset=False, retry_commands=0)
    entry["delete_timeout_reconciliation"] = detail
    remaining = deadline - time.monotonic()
    batch.require(remaining > 0, "Owned cleanup budget exhausted before delete reconciliation")
    observation = dict(phase="AFTER_OWNED_DELETE_TIMEOUT")
    report["inventory_queries"].append(observation)
    try:
        inventory = batch.scoped_device_inventory(device,
            timeout=min(batch.SCOPED_DEVICE_QUERY_SECONDS, remaining), observation=observation)
        batch.require(time.monotonic() <= deadline, "Owned cleanup budget exhausted during delete requery")
        observed = batch.resolve_cleanup_device(inventory, device, baseline_udids, device)
        if observed is None:
            detail.update(status="DELETION_PROVED_BY_ACTUAL_SCOPED_ABSENCE", retry_commands=0)
            return
        actual = batch.validate_owned_device(inventory, device)
        batch.require(actual.get("state") in {"Shutdown", "Booted"},
                      "Owned delete retry has no observed stable device state")
        detail["revalidated_identity"] = dict(actual, runtime_identifier=device["runtime"]["identifier"])
        remaining = deadline - time.monotonic()
        batch.require(remaining > 0, "Owned cleanup budget exhausted before the single delete retry")
        timeout = min(20, remaining)
        detail.update(retry_commands=1, retry_timeout_seconds=timeout)
        result = subprocess.run(argv, capture_output=True, timeout=timeout)
        detail["retry_return_code"] = result.returncode
        entry["delete_retry_exit_code"] = result.returncode
        batch.require(time.monotonic() <= deadline, "Owned cleanup budget exhausted during delete retry")
        batch.require(result.returncode == 0, "Single same-owned-UUID delete retry failed")
        detail["status"] = "DELETION_PROVED_BY_SUCCESSFUL_SAME_OWNED_UUID_RETRY"
    except BaseException as failure:
        detail.update(status="FAIL", error_type=type(failure).__name__, error=str(failure))
        raise
