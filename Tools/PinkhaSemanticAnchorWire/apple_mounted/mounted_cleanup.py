"""Scoped Page154 adapter for the unchanged, qualified owned-cleanup policy."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import mounted_contract as mounted

ORIGINAL_POLICY_PATH = "Tools/AnyEngineValidation/prepared_inline_file_apple/cleanup.py"
ORIGINAL_POLICY_SHA256 = "14fa818cdf6c2cf8b7b1f78c075bad8e98240bf1f40d2d50acf6fb3c5fd74cc6"
ORIGINAL_FUNCTION_SHA256 = "ee23ff8e58d67ba53d3aa4eed4552cdea0c5056eabae3ea9c04cdebb0a563e45"
TOTAL_SECONDS = 60.0


def _uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)).lower() == value.lower()
    except (ValueError, AttributeError):
        return False


# These aliases are local module values, not generic sys.modules registrations.
# The qualified policy body below is retained verbatim. Mounted command logs
# contain one raw JSON object; the scoped reader additionally rejects duplicate
# keys and nonfinite values under the policy's existing one-MiB bound.
contract = SimpleNamespace(require=mounted.require, digest=mounted.digest)
execution = SimpleNamespace(command_json=lambda path: mounted.read(path, 1024**2))
proof = SimpleNamespace(uuid=_uuid)


def cleanup_owned_simulator(run, receipt, udid, *, clock=time.monotonic):
    contract.require(proof.uuid(udid) and receipt.get("owned_simulator", {}).get("udid") == udid,
                     "Cleanup must address the originally created simulator")
    started = clock()
    deadline = started + TOTAL_SECONDS
    actions = receipt.setdefault("owned_simulator_cleanup", {})
    shutdown_timeout = False
    for action in ("shutdown", "delete"):
        argv = ["xcrun", "simctl", action, udid]
        budget = min(30.0, max(0.0, deadline - clock()))
        try:
            contract.require(budget > 0, "Original simulator cleanup budget exhausted")
            run(argv, "cleanup-owned-simulator-" + action, timeout=budget)
            actions[action] = dict(status="PASS_EXIT_0")
        except BaseException as error:
            actions[action] = dict(status="FAIL", error_type=type(error).__name__, error=str(error))
            if action == "shutdown":
                shutdown_timeout = (isinstance(error, subprocess.TimeoutExpired)
                    and error.cmd == argv and 0 < error.timeout <= budget)
    complete = all(actions.get(action, {}).get("status") == "PASS_EXIT_0"
                   for action in ("shutdown", "delete"))
    if not complete and shutdown_timeout and actions.get("delete", {}).get("status") == "PASS_EXIT_0":
        reconciliation = dict(status="NOT_PROVEN", original_shutdown_status="FAIL",
                              delete_status="PASS_EXIT_0", total_budget_seconds=TOTAL_SECONDS)
        receipt["owned_simulator_cleanup_reconciliation"] = reconciliation
        try:
            budget = min(10.0, max(0.0, deadline - clock()))
            contract.require(budget > 0, "No original cleanup budget remains for absence observation")
            argv = ["xcrun", "simctl", "list", "devices", udid, "-j"]
            path = run(argv, "cleanup-owned-simulator-confirm-absent", timeout=budget)
            contract.require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024**2,
                             "Owned absence inventory must be a bounded original regular log")
            inventory = execution.command_json(path)
            contract.require(set(inventory) == {"devices"} and isinstance(inventory["devices"], dict),
                             "Owned absence inventory has an unexpected shape")
            contract.require(all(isinstance(runtime, str) and isinstance(devices, list)
                                 for runtime, devices in inventory["devices"].items()),
                             "Owned absence inventory has malformed runtime entries")
            # A present owned device or any unrelated entry is not absence.
            # This query never grants permission to signal or delete another ID.
            contract.require(all(not devices for devices in inventory["devices"].values()),
                             "The exact owned-UDID query did not establish absence")
            reconciliation.update(status="VERIFIED_ABSENT_AFTER_DELETE", command=argv,
                                  inventory_sha256=contract.digest(path))
            complete = True
        except BaseException as error:
            reconciliation.update(error_type=type(error).__name__, error=str(error))
    finished = clock()
    within_budget = finished <= deadline
    receipt["owned_simulator_cleanup_budget"] = dict(
        total_seconds=TOTAL_SECONDS, elapsed_seconds=finished - started, within_budget=within_budget)
    # Successful subprocess exit may still arrive late after its owned-group
    # finalization. The original deadline also applies to that observed outcome.
    complete = complete and within_budget
    receipt["owned_simulator_cleanup_status"] = "COMPLETE" if complete else "INCOMPLETE"


def recover_original_created_simulator(path, receipt, expected_argv, nonce):
    """Recover only the exact original create-command output after its failure."""
    if not path.exists():
        return None
    mounted.require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 128
        and isinstance(expected_argv, list) and len(expected_argv) == 6
        and expected_argv[:4] == ["xcrun", "simctl", "create", "Page154Mounted-" + nonce],
        "Original owned create-command identity missing")
    udid = path.read_text().strip()
    mounted.require(_uuid(udid), "Original create-command output is not one exact simulator UUID")
    records = [row for row in receipt.get("commands", []) if row.get("name") == "create-owned-simulator"]
    mounted.require(len(records) == 1 and records[0].get("argv") == expected_argv
        and records[0].get("log_sha256") == mounted.digest(path)
        and "owned_simulator" not in receipt, "Original owned creation receipt is missing, changed or conflicting")
    receipt["owned_simulator"] = dict(udid=udid, nonce=nonce,
        recovered_from_original_create_command=True, original_create_argv=expected_argv,
        original_create_log_sha256=mounted.digest(path))
    return udid


def finalize_mounted_simulator(runner, receipt, udid, primary, *, clock=time.monotonic):
    """Keep original failures while adapting the qualified policy to Commands."""
    first = len(receipt.get("commands", []))
    called = []
    def run(argv, name, *, timeout):
        called.append((argv, name))
        path, record = runner.run(argv, name, timeout=timeout)
        mounted.require(isinstance(path, Path) and isinstance(record, dict)
            and type(record.get("return_code")) is int and record["return_code"] == 0,
            "Mounted cleanup command did not return its original successful path/record")
        return path

    failure = None
    try:
        cleanup_owned_simulator(run, receipt, udid, clock=clock)
        rows = receipt.get("commands", [])[first:]
        mounted.require(len(rows) == len(called) and all(
            row.get("argv") == argv and row.get("name") == name
            and type(row.get("worker_pid")) is int and row["worker_pid"] > 1
            and row.get("owned_group_cleanup") == "TERM_THEN_KILL"
            and not row.get("cleanup_error_type") and not row.get("quiescence_failure")
            and row.get("owned_group_quiescence", {}).get("status") == "PASS"
            and row.get("owned_group_quiescence", {}).get("live_members") == 0
            and row.get("owned_group_quiescence", {}).get("pgid") == row.get("worker_pid")
            for row, (argv, name) in zip(rows, called)),
            "Original mounted cleanup command group did not prove quiescence")
        mounted.require(receipt.get("owned_simulator_cleanup_status") == "COMPLETE",
                        "Owned simulator cleanup did not complete within its original budget")
    except BaseException as error:
        failure = error
        receipt["owned_simulator_cleanup_status"] = "INCOMPLETE"
    receipt["mounted_cleanup_adapter"] = dict(
        status="PASS" if failure is None else "FAIL",
        original_policy_sha256=ORIGINAL_POLICY_SHA256,
        original_function_sha256=ORIGINAL_FUNCTION_SHA256,
        command_records_checked=len(receipt.get("commands", [])[first:]),
        previous_primary_failure_preserved=primary is not None)
    if failure is not None:
        receipt["mounted_cleanup_adapter"].update(error_type=type(failure).__name__, error=str(failure))
    return primary if primary is not None else failure
