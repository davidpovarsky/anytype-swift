#!/usr/bin/env python3
"""One owned-simulator diagnostic. No application build, test, or downloaded product."""
from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
RELATIVE = "Tools/SimulatorBootInventoryDiagnostic"
MANIFEST_PATH = RELATIVE + "/source-inputs.json"
PROFILE_PATH = RELATIVE + "/profile.json"
WORKFLOW_PATH = ".github/workflows/pinkha-owned-simulator-inventory-diagnostic.yml"
RUNTIME_PATHS = (RELATIVE + "/run.py", PROFILE_PATH, WORKFLOW_PATH)
BRANCH = "codex/chatgpt-wave15-shared-20261121"
DEVELOPER = "/Applications/Xcode_27.app/Contents/Developer"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
DEVICE = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"
RUNTIME_BUILD = "24A434"
GLOBAL_SECONDS = 1200.0
CLEANUP_RESERVE_SECONDS = 240.0
MIN_FREE = 1024 ** 3
MAX_BYTES = 8 * 1024 ** 2
FINAL_RESERVE = 128 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_COMMANDS = 56
PS_ARGV = ["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,comm="]
SERVICE_NAMES = ("CoreSimulator", "Simulator", "launchd_sim", "simdiskimaged", "simulatord")
PS_SECONDS = 5.0
TOTAL_SECONDS = 60.0
ORIGINAL_POLICY_SHA256 = "14fa818cdf6c2cf8b7b1f78c075bad8e98240bf1f40d2d50acf6fb3c5fd74cc6"


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def error(value):
    result = {"type": type(value).__name__, "message": str(value)}
    if isinstance(value, subprocess.TimeoutExpired):
        result.update(argv=value.cmd, timeout_seconds=value.timeout)
    elif isinstance(value, subprocess.CalledProcessError):
        result.update(argv=value.cmd, return_code=value.returncode)
    if isinstance(value, OSError):
        result["errno"] = value.errno
    return result


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def read(path, limit=MAX_FILE_BYTES):
    path = Path(path)
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not path.is_symlink() and st.st_nlink == 1
            and 0 <= st.st_size <= limit, "invalid_bounded_regular_file:" + str(path))
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) == st.st_size and len(raw) <= limit, "bounded_file_changed")
    return json.loads(raw, object_pairs_hook=unique_object)


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(UUID(value)).upper() == value
    except (ValueError, TypeError, AttributeError):
        return False


def observe_usage(directory):
    logical = allocated = entries = 0
    for parent, dirs, files in os.walk(directory, followlinks=False):
        for name in ["."] if parent == str(directory) else []:
            st = Path(parent).lstat()
            allocated += st.st_blocks * 512
        for name in dirs + files:
            path = Path(parent) / name
            st = path.lstat()
            entries += 1
            require(entries <= 512 and not stat.S_ISLNK(st.st_mode)
                    and (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)),
                    "unexpected_evidence_entry")
            allocated += st.st_blocks * 512
            if stat.S_ISREG(st.st_mode):
                require(st.st_nlink == 1, "linked_evidence_file")
                logical += st.st_size
    space = os.statvfs(directory)
    return {"logical_bytes": logical, "allocated_bytes": allocated, "entries": entries,
            "free_bytes": space.f_bavail * space.f_frsize, "monotonic": time.monotonic()}


class Evidence:
    def __init__(self, root):
        self.root = root
        self.peak_logical = 0
        self.peak_allocated = 0

    def capacity(self, reserve=FINAL_RESERVE):
        current = observe_usage(self.root)
        self.peak_logical = max(self.peak_logical, current["logical_bytes"])
        self.peak_allocated = max(self.peak_allocated, current["allocated_bytes"])
        require(current["free_bytes"] >= MIN_FREE, "diagnostic_disk_floor")
        require(max(current["logical_bytes"], current["allocated_bytes"]) + reserve <= MAX_BYTES,
                "diagnostic_evidence_limit")
        return current

    def write(self, relative, value, *, final=False):
        path = self.root / relative
        require(path.parent.is_dir() and path.parent.resolve() == path.parent
                and not path.exists() and not path.is_symlink(), "evidence_replacement_forbidden")
        raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
        require(len(raw) <= MAX_FILE_BYTES, "evidence_record_too_large")
        self.capacity(reserve=0 if final else FINAL_RESERVE)
        require(max(observe_usage(self.root)[key] for key in ("logical_bytes", "allocated_bytes"))
                + len(raw) + 4096 <= MAX_BYTES, "evidence_write_would_exceed_limit")
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def record_signal(pgid, sig, records):
    entry = {"pgid": pgid, "signal": int(sig), "before_monotonic": time.monotonic()}
    records.append(entry)
    try:
        os.killpg(pgid, sig)
    except BaseException as failure:
        entry.update(after_monotonic=time.monotonic(), outcome="ERROR", error=error(failure))
        raise
    else:
        entry.update(after_monotonic=time.monotonic(), outcome="RETURNED_ZERO")


def terminate_owned(process, signals):
    require(process.pid != os.getpgrp(), "Refuse the controller's own process group")
    try:
        record_signal(process.pid, signal.SIGTERM, signals)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # An exited parent can leave TERM-ignoring owned descendants.
    try:
        record_signal(process.pid, signal.SIGKILL, signals)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)

def _sdk06_kernel_group_observation(pgid, deadline):
    """Read only exact owned PGID existence; only timely ESRCH proves absence."""
    before = time.monotonic()
    observation = dict(operation="os.killpg", signal=0, pgid=pgid, errno=None,
                       before_monotonic=before, deadline_monotonic=deadline,
                       after_monotonic=before, outcome="NOT_QUERIED")

    def fail(error, status):
        error.timeout_observations = []
        error.quiescence_observation = dict(status=status, pgid=pgid,
            live_members=0 if observation["outcome"] == "ABSENT_ESRCH" else None,
            observations=0, kernel_group_observation=dict(observation))
        return error

    if before >= deadline:
        raise fail(RuntimeError("SDK kernel observation has no remaining original cleanup budget"),
                   "FAIL_DEADLINE")
    original_error = None
    try:
        os.killpg(pgid, 0)
    except OSError as error:
        original_error = error
        observation.update(errno=error.errno, error_type=type(error).__name__)
    observation["after_monotonic"] = time.monotonic()
    if original_error is not None:
        if original_error.errno != errno.ESRCH:
            observation["outcome"] = "KERNEL_QUERY_ERROR"
            raise fail(original_error, "FAIL_KERNEL_QUERY")
        observation["outcome"] = "ABSENT_ESRCH"
    else:
        observation["outcome"] = "GROUP_EXISTS"
    if observation["after_monotonic"] > deadline:
        raise fail(RuntimeError("SDK kernel observation returned after the original cleanup deadline"),
                   "FAIL_DEADLINE") from original_error
    return observation


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _version(text):
    _require(isinstance(text, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,2}", text),
             "Malformed simulator runtime version")
    parts = tuple(map(int, text.split(".")))
    parts += (0,) * (3 - len(parts))
    _require(0 < parts[0] <= 65535 and all(0 <= value <= 255 for value in parts[1:]),
             "Simulator version cannot be represented by the native runtime bounds")
    return parts, (parts[0] << 16) | (parts[1] << 8) | parts[2]


def _unique(items, label):
    _require(isinstance(items, list), "Missing simulator " + label)
    result = {}
    for value in items:
        _require(isinstance(value, dict), "Malformed simulator " + label)
        identifier = value.get("identifier")
        _require(isinstance(identifier, str) and identifier and identifier not in result,
                 "Missing or repeated simulator identifier in " + label)
        result[identifier] = value
    return result


def choose_pair(runtime_inventory, device_inventory, *, product_family="iPad", major=27,
                architecture="arm64"):
    """Require both the runtime support matrix and the installed type's bounds.

    A model-specific iPhone runtime may share the general iOS version number.
    Neither version sorting nor a type's minimum version proves compatibility.
    Missing support matrices are refused instead of inferred from device names.
    """
    _require(product_family in {"iPad", "iPhone"} and type(major) is int and major > 0,
             "Unsupported simulator family or major version")
    _require(architecture in {"arm64", "x86_64"}, "Unsupported simulator architecture")
    _require(isinstance(runtime_inventory, dict) and isinstance(device_inventory, dict),
             "Simulator inventories must be objects")
    runtimes = _unique(runtime_inventory.get("runtimes"), "runtimes")
    device_types = _unique(device_inventory.get("devicetypes"), "device types")
    candidates = []
    for identifier, runtime in runtimes.items():
        if not identifier.startswith("com.apple.CoreSimulator.SimRuntime.iOS-") or runtime.get("isAvailable") is not True:
            continue
        version, encoded = _version(runtime.get("version"))
        if version[0] != major:
            continue
        architectures = runtime.get("supportedArchitectures")
        _require(isinstance(architectures, list) and all(isinstance(value, str) for value in architectures),
                 "Runtime lacks explicit supported architectures")
        if architecture not in architectures:
            continue
        supported = _unique(runtime.get("supportedDeviceTypes"), "runtime-supported device types")
        for device_id, description in supported.items():
            installed = device_types.get(device_id)
            if installed is None or description.get("productFamily") != product_family or installed.get("productFamily") != product_family:
                continue
            minimum, maximum = installed.get("minRuntimeVersion"), installed.get("maxRuntimeVersion")
            _require(type(minimum) is int and type(maximum) is int and 0 <= minimum <= maximum <= 0xFFFFFFFF,
                     "Malformed installed simulator runtime bounds")
            if minimum <= encoded <= maximum:
                _require(isinstance(installed.get("name"), str) and installed["name"], "Missing installed device name")
                candidates.append((version, minimum, installed["name"], identifier, device_id, runtime, installed))
    _require(candidates, "No explicitly compatible installed " + product_family + " / iOS " + str(major) + " pair")
    chosen = max(candidates, key=lambda value: value[:5])
    return {
        "runtime": chosen[5], "device": chosen[6],
        "selection": {
            "runtimeIdentifier": chosen[3], "deviceTypeIdentifier": chosen[4],
            "runtimeVersion": chosen[5]["version"], "runtimeBuild": chosen[5].get("buildversion"),
            "productFamily": product_family, "architecture": architecture,
            "compatibilityEvidence": "runtime.supportedDeviceTypes AND installed type version bounds"
        }
    }

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

FIXED_PROFILE = {
    "schema": "owned-simulator-postboot-diagnostic-profile-v1",
    "scope": "ONE_FRESH_OWNED_SIMULATOR_ONLY",
    "runtime": {
        "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
        "version": "27.0",
        "build": "24A434"
    },
    "device": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB",
    "global_seconds": 1200,
    "cleanup_reserve_seconds": 240,
    "original_inventory_seconds": 30,
    "additional_inventory_seconds": 120,
    "additional_inventory_max_calls": 1,
    "additional_condition": "EXACT_ORIGINAL_TIMEOUT_AND_OWNED_GROUP_ESRCH",
    "per_command_session": "NEW_SESSION_TERM_KILL_ON_SUCCESS_OR_FAILURE",
    "sampled_output_limits": {
        "total_logical_and_allocated_bytes": 8388608,
        "per_file_bytes": 262144,
        "max_entries": 512,
        "max_commands": 56,
        "poll_seconds": 0.1,
        "hard_output_quota": False
    },
    "minimum_free_bytes": 1073741824,
    "product_methods": 0,
    "app_builds": 0,
    "native_builds": 0,
    "ui_runner_builds": 0,
    "artifact_downloads": 0
}

# These namespaces satisfy the unchanged qualified cleanup policy's dependencies.
contract = SimpleNamespace(require=require, digest=digest)
execution = SimpleNamespace(command_json=read)
proof = SimpleNamespace(uuid=valid_uuid)


class Commands:
    def __init__(self, evidence, context, deadline, mode):
        self.evidence, self.context = evidence, context
        self.directory = evidence.root / "commands"
        if not self.directory.exists():
            self.directory.mkdir(mode=0o700)
        require(self.directory.is_dir() and self.directory.resolve() == self.directory,
                "invalid_commands_directory")
        self.deadline, self.mode = deadline, mode
        self.cleanup_mode = False
        self.records = {}
        self.finalized_commands = {}
        self.first_passive_failure = None
        self.passive_observation_failures = []
        self.count = len(list(self.directory.glob("*.log")))
        require(self.count <= MAX_COMMANDS, "existing_command_count_exceeded")

    def _budget(self, timeout):
        require(0 < timeout <= 180, "invalid_diagnostic_command_budget")
        reserve = 0 if self.cleanup_mode else CLEANUP_RESERVE_SECONDS
        require(time.monotonic() + timeout + 35 < self.deadline - reserve,
                "diagnostic_global_budget_exhausted")
        self.evidence.capacity()

    def process_snapshot(self, label, owned_pgid):
        path = self.run(PS_ARGV, label, PS_SECONDS)
        raw = path.read_text(encoding="utf-8", errors="strict")
        rows = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            fields = line.split(None, 4)
            require(len(fields) == 5 and all(re.fullmatch("[0-9]+", x) for x in fields[:3]),
                    "unexpected_ps_metadata")
            rows.append({"pid": int(fields[0]), "ppid": int(fields[1]), "pgid": int(fields[2]),
                         "state": fields[3], "comm": fields[4]})
        require(len(rows) <= 4096, "process_metadata_row_limit")
        return {"argv": PS_ARGV, "log": path.name, "sha256": digest(path), "row_count": len(rows),
                "owned_pgid": owned_pgid,
                "owned_group_members": [row for row in rows if row["pgid"] == owned_pgid],
                "simulator_service_rows": [
                    row for row in rows if any(token in Path(row["comm"]).name for token in SERVICE_NAMES)],
                "scope": "SAMPLED_PROCESS_METADATA_NOT_A_LIVENESS_OR_CAUSATION_PROOF"}

    def _unavailable_passive_snapshot(self, label, owned_pgid, failure):
        """Only a durably recorded, safely reaped PS outcome may be deferred."""
        name = self.mode + "-" + label
        record = self.records.get(name, {})
        receipt = self.finalized_commands.get(name)
        outcome = (
            type(failure) is subprocess.TimeoutExpired
            and failure.cmd == PS_ARGV and failure.timeout == PS_SECONDS
        ) or (
            type(failure) is subprocess.CalledProcessError
            and failure.cmd == PS_ARGV and failure.returncode != 0
            and failure.returncode == record.get("return_code")
        )
        if not (
            self.mode == "execute" and not self.cleanup_mode and outcome
            and failure.__cause__ is None
            and record.get("argv") == PS_ARGV
            and record.get("timeout_seconds") == PS_SECONDS
            and record.get("status") == "FAIL"
            and record.get("first_error") == error(failure)
            and record.get("secondary_errors") == []
            and record.get("sampling_changes_cleanup_timing") is False
            and type(record.get("pid")) is int and record["pid"] > 1
            and record.get("pgid") == record["pid"]
            and record.get("kernel_observation", {}).get("pgid") == record["pid"]
            and record.get("kernel_observation", {}).get("outcome") == "ABSENT_ESRCH"
            and type(record.get("log_bytes")) is int
            and 0 <= record["log_bytes"] <= MAX_FILE_BYTES
            and isinstance(record.get("log_sha256"), str)
            and re.fullmatch("[0-9a-f]{64}", record["log_sha256"]) is not None
            and isinstance(receipt, dict)
            and receipt.get("path") == "commands/" + name + ".command.json"
        ):
            return None
        return {
            "status": "UNAVAILABLE",
            "reason": "PASSIVE_PS_COMMAND_FAILED",
            "argv": list(PS_ARGV),
            "owned_pgid": owned_pgid,
            "error": error(failure),
            "command_receipt": dict(receipt),
            "log": name + ".log",
            "log_sha256": record["log_sha256"],
            "log_bytes": record["log_bytes"],
            "scope": "NO_PROCESS_ROWS_OR_SERVICE_ABSENCE_INFERRED",
        }

    def _defer_passive_failures(self, failures, parent_command):
        for failure, observation in failures:
            if self.first_passive_failure is None:
                self.first_passive_failure = failure
            self.passive_observation_failures.append({
                "parent_command": parent_command, **observation})

    def initial_process_snapshot(self):
        try:
            return self.process_snapshot("initial-processes", -1)
        except BaseException as failure:
            unavailable = self._unavailable_passive_snapshot("initial-processes", -1, failure)
            if unavailable is None:
                raise
            self._defer_passive_failures([(failure, unavailable)], None)
            return unavailable

    def run(self, argv, name, timeout, *, observe=None, sample_cleanup=False):
        require(isinstance(argv, list) and argv and all(isinstance(x, str) and "\x00" not in x for x in argv),
                "invalid_command_argv")
        require(re.fullmatch("[a-z0-9][a-z0-9-]*", name) is not None, "invalid_command_name")
        self.count += 1
        require(self.count <= MAX_COMMANDS, "diagnostic_command_count_limit")
        self._budget(timeout)
        name = self.mode + "-" + name
        log = self.directory / (name + ".log")
        start = "commands/" + name + ".started.json"
        final = "commands/" + name + ".command.json"
        require(not any((self.evidence.root / p).exists() for p in (start, final))
                and not log.exists(), "command_replay_forbidden")
        record = {"context": self.context, "argv": argv, "cwd": str(ROOT),
                  "timeout_seconds": timeout, "status": "FAIL", "started_wall": time.time(),
                  "started_monotonic": time.monotonic(), "environment_values_recorded": False,
                  "stdout_kind": "REGULAR_FILE_MERGED_STDOUT_STDERR",
                  "session_policy": "START_NEW_SESSION_WITH_TERM_KILL_EVEN_AFTER_SUCCESS",
                  "sampling_changes_cleanup_timing": bool(sample_cleanup),
                  "signals": [], "secondary_errors": []}
        primary = None
        passive_snapshot_failures = []
        process = None
        stream = None
        try:
            stream = log.open("xb")
            os.chmod(log, 0o600)
            process = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            require(process.pid > 1 and process.pid != os.getpgrp(), "invalid_owned_process_group")
            record.update(pid=process.pid, pgid=process.pid)
            self.evidence.write(start, record)
            command_deadline = time.monotonic() + timeout
            try:
                while True:
                    remaining = command_deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(argv, timeout)
                    try:
                        record["return_code"] = process.wait(timeout=min(0.1, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        require(os.fstat(stream.fileno()).st_size <= MAX_FILE_BYTES,
                                "command_sampled_output_limit")
                        self.evidence.capacity()
                require(os.fstat(stream.fileno()).st_size <= MAX_FILE_BYTES,
                        "command_final_output_limit")
                if time.monotonic() > command_deadline:
                    raise subprocess.TimeoutExpired(argv, timeout)
                if process.returncode:
                    primary = subprocess.CalledProcessError(process.returncode, argv)
            except BaseException as failure:
                primary = failure
            record["wait_finished_monotonic"] = time.monotonic()
            try:
                stream.flush()
                os.fsync(stream.fileno())
                if observe is not None:
                    observe(log, record)
            except BaseException as failure:
                record["secondary_errors"].append({"stage": "log_flush_or_create_capture", **error(failure)})
                primary = primary or failure
        except BaseException as failure:
            primary = primary or failure
        finally:
            if process is not None:
                if sample_cleanup:
                    try:
                        record["before_group_cleanup"] = self.process_snapshot(name + "-before-group-cleanup",
                                                                                process.pid)
                    except BaseException as failure:
                        record["secondary_errors"].append({"stage": "before_group_snapshot", **error(failure)})
                        primary = primary or failure
                        unavailable = self._unavailable_passive_snapshot(
                            name + "-before-group-cleanup", process.pid, failure)
                        if unavailable is not None:
                            record["before_group_cleanup"] = unavailable
                            passive_snapshot_failures.append((failure, unavailable))
                try:
                    terminate_owned(process, record["signals"])
                    record["kernel_observation"] = _sdk06_kernel_group_observation(
                        process.pid, time.monotonic() + 10)
                    require(record["kernel_observation"]["outcome"] == "ABSENT_ESRCH",
                            "owned_process_group_not_absent")
                except BaseException as failure:
                    record["secondary_errors"].append({"stage": "owned_group_cleanup", **error(failure)})
                    primary = primary or failure
                record["return_code"] = process.returncode
                if sample_cleanup:
                    try:
                        record["after_group_cleanup"] = self.process_snapshot(name + "-after-group-cleanup",
                                                                               process.pid)
                    except BaseException as failure:
                        record["secondary_errors"].append({"stage": "after_group_snapshot", **error(failure)})
                        primary = primary or failure
                        unavailable = self._unavailable_passive_snapshot(
                            name + "-after-group-cleanup", process.pid, failure)
                        if unavailable is not None:
                            record["after_group_cleanup"] = unavailable
                            passive_snapshot_failures.append((failure, unavailable))
            if stream is not None:
                try:
                    stream.flush()
                    os.fsync(stream.fileno())
                except BaseException as failure:
                    record["secondary_errors"].append({"stage": "final_stream_flush", **error(failure)})
                    primary = primary or failure
                try:
                    stream.close()
                except BaseException as failure:
                    record["secondary_errors"].append({"stage": "stream_close", **error(failure)})
                    primary = primary or failure
        record.update(finished_wall=time.time(), finished_monotonic=time.monotonic(),
                      log_sha256=None, log_bytes=None)
        try:
            record.update(log_sha256=digest(log), log_bytes=log.stat().st_size)
            self.evidence.capacity()
        except BaseException as failure:
            record["secondary_errors"].append({"stage": "final_log_or_capacity", **error(failure)})
            primary = primary or failure
        continuation_eligible = bool(
            sample_cleanup and primary
            and any(primary is failure for failure, _ in passive_snapshot_failures)
            and record.get("return_code") == 0
            and record.get("kernel_observation", {}).get("outcome") == "ABSENT_ESRCH"
            and len(record["secondary_errors"]) == len(passive_snapshot_failures)
            and all(row["stage"] in {"before_group_snapshot", "after_group_snapshot"}
                    for row in record["secondary_errors"])
        )
        record["first_error"] = error(primary) if primary else None
        record["status"] = "FAIL" if primary else "PASS"
        record["passive_continuation_eligible"] = continuation_eligible
        self.records[name] = record
        try:
            self.finalized_commands[name] = self.evidence.write(final, record, final=self.cleanup_mode)
        except BaseException as preservation:
            if primary:
                raise primary from preservation
            raise
        if primary:
            if continuation_eligible:
                self._defer_passive_failures(passive_snapshot_failures, name)
            else:
                raise primary
        return log

    def json(self, argv, name, timeout=30, **kwargs):
        return read(self.run(argv, name, timeout, **kwargs))


def source_snapshot(commands, expected, label):
    def git(args, name):
        return commands.run(["git", "-c", "core.packedGitLimit=64m",
                             "-c", "core.packedGitWindowSize=16m", *args],
                            label + "-" + name, 15).read_bytes()
    actual_root = git(["rev-parse", "--show-toplevel"], "git-root").decode().strip()
    actual_head = git(["rev-parse", "HEAD"], "git-head").decode().strip()
    actual_branch = git(["symbolic-ref", "--quiet", "--short", "HEAD"], "git-branch").decode().strip()
    require(actual_root == str(ROOT) and actual_head == expected and actual_branch == BRANCH,
            "controller_git_identity_changed")
    paths = sorted((*RUNTIME_PATHS, MANIFEST_PATH))
    require(git(["status", "--porcelain=v1", "--untracked-files=all", "--", *paths], "git-status") == b"",
            "controller_inputs_dirty")
    listing = git(["ls-tree", "-z", "HEAD", "--", *paths], "git-tree")
    tree = {}
    for row in listing.split(b"\x00"):
        if not row:
            continue
        left, path = row.split(b"\t", 1)
        mode, kind, blob = left.decode("ascii").split()
        rel = path.decode("utf-8")
        require(kind == "blob" and mode == "100644" and rel in paths and rel not in tree,
                "controller_git_tree_shape")
        tree[rel] = {"git_blob": blob, "git_mode": mode}
    require(set(tree) == set(paths), "controller_git_input_missing")
    manifest = read(ROOT / MANIFEST_PATH)
    require(set(manifest) == {"schema", "inputs"} and manifest["schema"] == "owned-simulator-diagnostic-inputs-v1"
            and isinstance(manifest["inputs"], list), "controller_manifest_schema")
    rows = {row["path"]: row for row in manifest["inputs"]}
    require(len(rows) == len(manifest["inputs"]) and set(rows) == set(RUNTIME_PATHS),
            "controller_fixed_input_set")
    observed = {}
    for relative in paths:
        path = ROOT / relative
        require(path.resolve() == path and path.is_file() and not path.is_symlink(),
                "controller_input_not_canonical")
        st = path.lstat()
        require(stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o644
                and st.st_nlink == 1 and st.st_size <= MAX_FILE_BYTES, "controller_input_metadata")
        raw = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()
        require(blob == tree[relative]["git_blob"], "controller_physical_git_bytes_changed")
        row = {**tree[relative], "sha256": hashlib.sha256(raw).hexdigest(),
               "bytes": len(raw), "physical_mode": stat.S_IMODE(st.st_mode)}
        if relative in rows:
            require(rows[relative] == {"path": relative, "sha256": row["sha256"],
                                      "bytes": row["bytes"], "git_mode": "100644"},
                    "controller_fixed_input_changed")
        observed[relative] = row
    profile = read(ROOT / PROFILE_PATH)
    require(profile == FIXED_PROFILE, "diagnostic_profile_changed")
    loaded = {}
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename or not isinstance(filename, str):
            continue
        path = Path(filename).absolute()
        resolved = path.resolve()
        if resolved.is_relative_to(ROOT):
            require(path == resolved and name == "__main__"
                    and resolved == ROOT / (RELATIVE + "/run.py"), "unexpected_repository_module")
            loaded[name] = {"path": resolved.relative_to(ROOT).as_posix(), "sha256": digest(resolved)}
    require(set(loaded) == {"__main__"}, "diagnostic_main_origin_missing")
    result = {"source": actual_head, "branch": actual_branch, "files": observed,
              "loaded_repository_modules": loaded}
    commands.evidence.write(label + ".json", result, final=commands.cleanup_mode)
    return result


def device_map(value):
    require(isinstance(value, dict) and set(value) == {"devices"} and isinstance(value["devices"], dict),
            "device_inventory_shape")
    result = {}
    for runtime, rows in value["devices"].items():
        require(isinstance(runtime, str) and isinstance(rows, list), "device_runtime_shape")
        for row in rows:
            require(isinstance(row, dict) and valid_uuid(row.get("udid")), "device_identity_shape")
            identity = row["udid"]
            require(identity not in result, "duplicate_device_uuid")
            result[identity] = (runtime, row)
    return result


def fixed_pair(commands):
    runtimes = _unique(commands.json(["xcrun", "simctl", "list", "runtimes", "--json"],
                                     "runtimes").get("runtimes"), "runtimes")
    devices = _unique(commands.json(["xcrun", "simctl", "list", "devicetypes", "--json"],
                                    "device-types").get("devicetypes"), "device types")
    require(RUNTIME in runtimes and DEVICE in devices, "exact_release_pair_unavailable")
    runtime, device = runtimes[RUNTIME], devices[DEVICE]
    require(runtime.get("version") == "27.0" and runtime.get("buildversion") == RUNTIME_BUILD,
            "exact_runtime_build_changed")
    return choose_pair({"runtimes": [runtime]}, {"devicetypes": [device]},
                       product_family="iPad", major=27, architecture="arm64")


def verify_inventory(value, item, states):
    found = device_map(value)
    require(set(found) == {item["udid"]}, "owned_uuid_query_not_exact")
    runtime, row = found[item["udid"]]
    require(runtime == item["runtime"]["identifier"] and row.get("name") == item["name"]
            and row.get("deviceTypeIdentifier") == item["device"]["identifier"]
            and row.get("isAvailable") is True, "owned_device_identity_changed")
    require(row.get("state") in states, "owned_device_state_changed")
    return {"udid": item["udid"], "runtime": runtime, "device_type": row["deviceTypeIdentifier"],
            "name": row["name"], "state": row["state"], "is_available": True}


def create_one(commands, name, state):
    pair = fixed_pair(commands)
    baseline = device_map(commands.json(["xcrun", "simctl", "list", "devices", "--json"], "before-create"))
    require(not any(row.get("name") == name for _, row in baseline.values()), "planned_name_exists")
    argv = ["xcrun", "simctl", "create", name, DEVICE, RUNTIME]
    intent = {"context": commands.context, "argv": argv, "name": name, "baseline_uuids": sorted(baseline),
              "runtime": pair["runtime"], "device": pair["device"]}
    commands.evidence.write("creation-intent.json", intent)
    def capture(log, record):
        require(log.stat().st_size <= 128, "create_output_bound")
        raw = log.read_text(encoding="ascii").strip()
        if not valid_uuid(raw.upper()):
            return
        identity = raw.upper()
        require(identity not in baseline and state["owned"] is None, "created_uuid_not_fresh")
        item = {"udid": identity, "name": name, "runtime": pair["runtime"], "device": pair["device"],
                "context": commands.context, "create_argv": argv, "create_log_sha256": digest(log),
                "create_return_code": record.get("return_code")}
        # Retain memory ownership even if a subsequent durable write fails.
        state["owned"] = item
        commands.evidence.write("created-simulator.json", item)
        state["creation_journal_durable"] = True
    commands.run(argv, "create-device", 60, observe=capture)
    require(state["owned"] is not None and state["creation_journal_durable"], "created_uuid_missing")
    item = state["owned"]
    inventory = commands.json(["xcrun", "simctl", "list", "devices", item["udid"], "--json"],
                              "created-exact-uuid", 30)
    state["preboot_identity"] = verify_inventory(inventory, item, {"Shutdown"})
    commands.evidence.write("preboot-identity.json", state["preboot_identity"])
    return item


def cleanup_once(commands, item, state):
    evidence = commands.evidence
    final_path = evidence.root / "simulator-cleanup.json"
    claim_path = evidence.root / "simulator-cleanup-started.json"
    if final_path.exists():
        receipt = read(final_path)
        require(receipt.get("context") == commands.context, "prior_cleanup_context_changed")
        if item is not None:
            require(receipt.get("owned_simulator", {}).get("udid") == item["udid"],
                    "prior_cleanup_uuid_changed")
        state["simulator_cleanup"] = receipt
        state["simulator_cleanup_reused"] = True
        return
    if claim_path.exists():
        state["simulator_cleanup"] = {"owned_simulator_cleanup_status": "INCOMPLETE",
                                     "reason": "PRIOR_CLEANUP_STARTED_WITHOUT_TERMINAL_RECEIPT"}
        return
    if item is None:
        attempted = (evidence.root / "creation-intent.json").exists()
        receipt = {"owned_simulator_cleanup_status": "INCOMPLETE" if attempted else "NOT_CREATED",
                   "owned_simulator": None, "context": commands.context,
                   "reason": "CREATION_ATTEMPT_WITHOUT_VERIFIED_UUID" if attempted else "NO_CREATION_INTENT"}
        evidence.write("simulator-cleanup.json", receipt, final=True)
        state["simulator_cleanup"] = receipt
        return
    require(valid_uuid(item["udid"]) and item["context"] == commands.context
            and item["name"] == "PinkhaInventory-" + commands.context["run_id"] + "-"
            + commands.context["run_attempt"] and item["runtime"]["identifier"] == RUNTIME
            and item["device"]["identifier"] == DEVICE, "cleanup_ownership_changed")
    receipt = {"owned_simulator": item, "context": commands.context,
               "scope": "EXACT_CREATED_UUID_ONLY", "policy_total_seconds": TOTAL_SECONDS}
    evidence.write("simulator-cleanup-started.json",
                   {"udid": item["udid"], "context": commands.context, "started_monotonic": time.monotonic()},
                   final=True)
    commands.cleanup_mode = True
    primary = None
    try:
        cleanup_owned_simulator(commands.run, receipt, item["udid"])
    except BaseException as failure:
        primary = failure
        receipt.update(owned_simulator_cleanup_status="INCOMPLETE", adapter_error=error(failure))
    state["simulator_cleanup"] = receipt
    try:
        evidence.write("simulator-cleanup.json", receipt, final=True)
    except BaseException as preservation:
        if primary:
            raise primary from preservation
        raise
    if primary:
        raise primary


def diagnostic(commands, state):
    state["phase"] = "EXACT_SOURCE_ADMITTED"
    for argv, label in ((["xcodebuild", "-version"], "xcode-version"),
                        (["xcode-select", "-p"], "selected-developer-directory"),
                        (["uname", "-m"], "host-architecture")):
        path = commands.run(argv, label, 15)
        if label == "selected-developer-directory":
            require(path.read_text().strip() == DEVELOPER, "selected_developer_directory_changed")
        if label == "host-architecture":
            require(path.read_text().strip() == "arm64", "non_native_host")
    state["initial_process_snapshot"] = commands.initial_process_snapshot()
    item = create_one(commands, "PinkhaInventory-" + commands.context["run_id"] + "-"
                      + commands.context["run_attempt"], state)
    state["phase"] = "CREATED_PREBOOT_IDENTITY_VERIFIED"
    commands.run(["xcrun", "simctl", "boot", item["udid"]], "boot", 120, sample_cleanup=True)
    commands.run(["xcrun", "simctl", "bootstatus", item["udid"], "-b"], "bootstatus", 180,
                 sample_cleanup=True)
    state["bootstatus_completed_monotonic"] = time.monotonic()
    state["phase"] = "POSTBOOT_ORIGINAL_30_SECOND_OBSERVATION"
    argv = ["xcrun", "simctl", "list", "devices", item["udid"], "--json"]
    try:
        value = commands.json(argv, "postboot-original-30", 30, sample_cleanup=True)
        identity = verify_inventory(value, item, {"Booted"})
        state["original_30_seconds"] = {"status": "PASS", "identity": identity}
    except BaseException as original:
        state["original_30_seconds"] = {"status": "FAIL", "error": error(original)}
        state["primary_failure"] = error(original)
        record = commands.records.get(commands.mode + "-postboot-original-30", {})
        try:
            state["after_original_failure_process_snapshot"] = commands.process_snapshot(
                "after-original-failure-processes", item.get("pid", -1))
            path = commands.run(["/bin/launchctl", "list"], "after-original-failure-service-status", 10)
            state["service_status"] = {"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size}
        except BaseException as observation_failure:
            state["secondary_errors"].append({"stage": "service_observation", **error(observation_failure)})
        permitted = (isinstance(original, subprocess.TimeoutExpired) and original.cmd == argv
                     and original.timeout == 30
                     and record.get("kernel_observation", {}).get("outcome") == "ABSENT_ESRCH")
        if permitted:
            state["phase"] = "ONE_ADDITIONAL_120_SECOND_DIAGNOSTIC_OBSERVATION"
            state["additional_120_seconds"] = {
                "status": "STARTED", "read_only": True, "is_retry_of_product_gate": False,
                "original_30_second_failure_preserved": True,
                "seconds_since_bootstatus": time.monotonic() - state["bootstatus_completed_monotonic"]}
            try:
                value = commands.json(argv, "additional-diagnostic-120", 120, sample_cleanup=True)
                identity = verify_inventory(value, item, {"Booted"})
                state["additional_120_seconds"].update(status="PASS_OBSERVATION_ONLY", identity=identity)
            except BaseException as observation_failure:
                state["additional_120_seconds"].update(status="FAIL", error=error(observation_failure))
                state["secondary_errors"].append({"stage": "additional_120_observation", **error(observation_failure)})
        else:
            state["additional_120_seconds"] = {"status": "NOT_RUN", "reason": "EXACT_TIMEOUT_OR_QUIESCENCE_NOT_PROVED"}
        raise original
    else:
        state["additional_120_seconds"] = {"status": "NOT_RUN", "reason": "ORIGINAL_30_SECOND_OBSERVATION_PASSED"}
    state["phase"] = "OBSERVATIONS_COMPLETE"


def context(expected):
    require(re.fullmatch("[0-9a-f]{40}", expected) is not None and os.environ.get("GITHUB_SHA") == expected,
            "expected_ci_source_required")
    require(os.environ.get("GITHUB_REPOSITORY") == "davidpovarsky/anytype-swift"
            and os.environ.get("GIT_OPTIONAL_LOCKS") == "0", "repository_or_git_environment_changed")
    require(os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_REF_NAME") == BRANCH, "unapproved_ci_branch")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch("[1-9][0-9]*", run_id) is not None
            and re.fullmatch("[1-9][0-9]*", attempt) is not None, "invalid_ci_run_identity")
    require(os.environ.get("DEVELOPER_DIR") == DEVELOPER and sys.flags.isolated == 1
            and sys.dont_write_bytecode and sys.version_info[:2] == (3, 12)
            and platform.system() == "Darwin" and platform.machine() == "arm64",
            "native_isolated_diagnostic_environment_required")
    require(ROOT.resolve() == ROOT, "repository_root_not_canonical")
    return {"source": expected, "run_id": run_id, "run_attempt": attempt,
            "job": os.environ.get("GITHUB_JOB", ""), "runner_name": os.environ.get("RUNNER_NAME", ""),
            "developer_dir": DEVELOPER, "python_executable": sys.executable,
            "python_version": sys.version}


def recover_owned(evidence, binding):
    if not (evidence.root / "created-simulator.json").exists():
        require(not (evidence.root / "creation-intent.json").exists(),
                "creation_was_attempted_but_owned_uuid_is_unavailable")
        return None
    item = read(evidence.root / "created-simulator.json")
    intent = read(evidence.root / "creation-intent.json")
    require(item["context"] == intent["context"] == binding
            and valid_uuid(item["udid"]) and item["udid"] not in intent["baseline_uuids"]
            and item["create_argv"] == intent["argv"]
            == ["xcrun", "simctl", "create", item["name"], DEVICE, RUNTIME],
            "recovered_creation_binding_changed")
    require(item["runtime"] == intent["runtime"] and item["device"] == intent["device"]
            and item["name"] == intent["name"] and isinstance(intent["baseline_uuids"], list)
            and intent["baseline_uuids"] == sorted(set(intent["baseline_uuids"]))
            and all(valid_uuid(value) for value in intent["baseline_uuids"]),
            "recovered_creation_intent_changed")
    started = read(evidence.root / "commands/execute-create-device.started.json")
    log = evidence.root / "commands/execute-create-device.log"
    require(started["context"] == binding and started["argv"] == item["create_argv"]
            and started["cwd"] == str(ROOT) and type(started["pid"]) is int and started["pid"] > 1
            and started["pgid"] == started["pid"] and log.is_file() and not log.is_symlink()
            and log.stat().st_size <= 128 and digest(log) == item["create_log_sha256"]
            and log.read_text(encoding="ascii").strip().upper() == item["udid"],
            "recovered_create_command_or_log_changed")
    return item


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("execute", "cleanup"))
    parser.add_argument("--expected-source", required=True)
    args = parser.parse_args()
    binding = context(args.expected_source)
    output = ROOT / "build" / ("owned-simulator-inventory-" + binding["run_id"] + "-" + binding["run_attempt"])
    require(output.parent.resolve() == output.parent, "evidence_parent_not_canonical")
    if not output.parent.exists():
        output.parent.mkdir(mode=0o700)
    if args.mode == "execute":
        require(not output.exists() and not output.is_symlink(), "diagnostic_attempt_replay_forbidden")
        output.mkdir(mode=0o700)
        os.chmod(output, 0o700)
    else:
        require(output.is_dir() and output.resolve() == output, "cleanup_evidence_missing")
    evidence = Evidence(output)
    evidence.capacity()
    lock_path = output / "controller.lock"
    flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT | os.O_EXCL if args.mode == "execute" else 0)
    lock_fd = os.open(lock_path, flags, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    started = time.monotonic()
    state = {"protocol": "owned-simulator-postboot-diagnostic-v1", "status": "FAIL",
             "mode": args.mode, "context": binding, "phase": "STARTING", "started_monotonic": started,
             "owned": None, "creation_journal_durable": False, "primary_failure": None,
             "secondary_errors": [], "app_builds": 0, "ui_runner_builds": 0, "native_builds": 0,
             "product_methods": 0, "artifact_downloads": 0, "planned_simulator_count": 1}
    primary = None
    before = None
    old_handlers = {}
    commands = None
    finalizing = False
    deferred_signals = []
    def interrupted(signum, frame):
        if finalizing:
            if len(deferred_signals) < 2:
                deferred_signals.append({"signal": signum, "monotonic": time.monotonic()})
            return
        raise RuntimeError("diagnostic_signal_" + str(signum))
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, interrupted)
        if args.mode == "execute":
            deadline = started + GLOBAL_SECONDS
            evidence.write("context.json", {"context": binding, "started_monotonic": started,
                                            "deadline_monotonic": deadline})
        else:
            original_context = read(output / "context.json")
            require(original_context["context"] == binding, "cleanup_context_changed")
            deadline = original_context["deadline_monotonic"]
            require(started < deadline, "original_diagnostic_deadline_expired")
        commands = Commands(evidence, binding, deadline, args.mode)
        commands.cleanup_mode = args.mode == "cleanup"
        before = source_snapshot(commands, args.expected_source, args.mode + "-source-before")
        state["source_before"] = before
        if args.mode == "execute":
            diagnostic(commands, state)
        else:
            state["owned"] = recover_owned(evidence, binding)
            state["creation_journal_durable"] = state["owned"] is not None
    except BaseException as failure:
        primary = failure
        state["primary_failure"] = state["primary_failure"] or error(failure)
    finally:
        finalizing = True
        if commands is not None:
            state["passive_observation_failures"] = list(commands.passive_observation_failures)
            if commands.first_passive_failure is not None:
                if primary is not None and primary is not commands.first_passive_failure:
                    state["secondary_errors"].append({"stage": "later_diagnostic_failure", **error(primary)})
                primary = commands.first_passive_failure
                state["primary_failure"] = error(primary)
        if commands is not None and before is not None:
            commands.cleanup_mode = True
            try:
                cleanup_once(commands, state["owned"], state)
                status = state["simulator_cleanup"]["owned_simulator_cleanup_status"]
                require(status in {"COMPLETE", "NOT_CREATED"}, "owned_simulator_cleanup_unproved")
            except BaseException as failure:
                state["secondary_errors"].append({"stage": "simulator_cleanup", **error(failure)})
                primary = primary or failure
            try:
                after = source_snapshot(commands, args.expected_source, args.mode + "-source-after")
                state["source_after"] = after
                require(after == before, "final_source_or_loaded_closure_changed")
            except BaseException as failure:
                state["secondary_errors"].append({"stage": "final_source_admission", **error(failure)})
                primary = primary or failure
            state["commands"] = {name: {"status": row["status"], "return_code": row.get("return_code"),
                                       "kernel_observation": row.get("kernel_observation"),
                                       "first_error": row.get("first_error")}
                                 for name, row in sorted(commands.records.items())}
        try:
            state["final_capacity"] = evidence.capacity(reserve=0)
            require(time.monotonic() <= (commands.deadline if commands else started + GLOBAL_SECONDS),
                    "diagnostic_finished_after_deadline")
        except BaseException as failure:
            state["secondary_errors"].append({"stage": "final_resource_admission", **error(failure)})
            primary = primary or failure
        state.update(finished_monotonic=time.monotonic(), status="FAIL" if primary else "PASS",
                     deferred_finalization_signals=deferred_signals,
                     created_simulator_count=int(state["owned"] is not None),
                     primary_failure=state["primary_failure"] or (error(primary) if primary else None),
                     peak_sampled_logical_bytes=evidence.peak_logical,
                     peak_sampled_allocated_bytes=evidence.peak_allocated,
                     byte_limits_are_sampled_not_hard_output_quotas=True)
        try:
            evidence.write(args.mode + "-result.json", state, final=True)
        except BaseException as failure:
            state["secondary_errors"].append({"stage": "final_result_persistence", **error(failure)})
            primary = primary or failure
        finally:
            for sig, handler in old_handlers.items():
                try:
                    signal.signal(sig, handler)
                except BaseException as failure:
                    state["secondary_errors"].append({"stage": "signal_handler_restore", **error(failure)})
                    primary = primary or failure
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except BaseException as failure:
                state["secondary_errors"].append({"stage": "controller_lock_release", **error(failure)})
                primary = primary or failure
    print(json.dumps({"status": "FAIL" if primary else "PASS", "mode": args.mode,
                      "first_error": state["primary_failure"] or (error(primary) if primary else None),
                      "later_errors": state["secondary_errors"], "evidence": str(output),
                      "product_methods": 0, "builds": 0}, sort_keys=True), flush=True)
    if primary:
        raise primary


if __name__ == "__main__":
    main()
