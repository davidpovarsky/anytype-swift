"""Opt-in, single-observation recovery of a fully preserved owned inventory timeout."""
from __future__ import annotations
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import uuid

POLICY = "owned-inventory-timeout-v1"
BUDGETS = {"postboot": 120, "pre-cleanup": 90}
MAX_LOG = 8 * 1024**2
_START_KEYS = {"context", "argv", "cwd", "timeoutSeconds", "status", "started",
               "environmentValuesRecorded", "pid", "pgid"}
_FINAL_KEYS = _START_KEYS | {"returnCode", "ownedGroupCleanup", "kernelObservation", "finished",
                            "logSHA256", "logBytes", "logMetadataStatus"}

def require(value, reason):
    if not value:
        raise ValueError(reason)

def error(failure):
    return {"type": type(failure).__name__, "message": str(failure)}

def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "inventory_proof_duplicate_json_key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("inventory_proof_nonfinite_json")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

def _number(value):
    return type(value) in (int, float) and math.isfinite(value)

def _raw(path, maximum):
    path = Path(path)
    require(path.is_absolute() and path.parent.resolve() == path.parent, "inventory_proof_parent_link")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == os.getuid()
            and 0 <= before.st_size <= maximum, "inventory_proof_regular_single_owned_file")
    identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_nlink,
                          s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    with path.open("rb") as stream:
        require(identity(os.fstat(stream.fileno())) == identity(before), "inventory_proof_open_changed")
        raw = stream.read(maximum + 1)
        require(identity(os.fstat(stream.fileno())) == identity(before), "inventory_proof_read_changed")
    require(identity(path.lstat()) == identity(before) and len(raw) == before.st_size,
            "inventory_proof_changed")
    return raw, {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                 "identity": [str(v) for v in identity(before)]}

def _unchanged(proofs):
    for proof in proofs:
        _, observed = _raw(Path(proof["path"]), max(proof["bytes"], 1))
        require(observed == proof, "original_inventory_evidence_changed")

def _command_proof(commands, name, argv, timeout, cwd, failure=None):
    records, proofs = {}, []
    for suffix, maximum in ((".started.json", 65536), (".command.json", 65536), (".log", MAX_LOG)):
        raw, proof = _raw(commands.root / (name + suffix), maximum)
        proofs.append(proof)
        records[suffix] = raw if suffix == ".log" else _json(raw)
    started, final, log = (records[k] for k in (".started.json", ".command.json", ".log"))
    require(isinstance(started, dict) and set(started) == _START_KEYS, "inventory_start_shape")
    expected_keys = _FINAL_KEYS | ({"firstFailure"} if failure is not None else set())
    require(isinstance(final, dict) and set(final) == expected_keys, "inventory_final_secondary_or_unknown_field")
    for record in (started, final):
        require(record["context"] == commands.context and record["argv"] == argv and record["cwd"] == cwd,
                "inventory_command_identity_changed")
        require(type(record["timeoutSeconds"]) is int and record["timeoutSeconds"] == timeout
                and record["environmentValuesRecorded"] is False, "inventory_command_budget_changed")
        require(type(record["pid"]) is int and record["pid"] > 1 and record["pgid"] == record["pid"]
                and record["pgid"] != os.getpgrp(), "inventory_group_not_owned")
        require(_number(record["started"]), "inventory_started_time")
    require(all(started[k] == final[k] for k in _START_KEYS - {"status"})
            and started["status"] == "FAIL", "inventory_start_final_binding")
    require(_number(final["finished"]) and final["finished"] >= final["started"]
            and type(final["returnCode"]) is int, "inventory_command_not_final")
    require(final["logMetadataStatus"] == "AVAILABLE" and type(final["logBytes"]) is int
            and final["logBytes"] == len(log) and final["logSHA256"] == hashlib.sha256(log).hexdigest(),
            "inventory_original_log_not_complete")
    kernel = final["kernelObservation"]
    require(final["ownedGroupCleanup"] == "TERM_THEN_KILL" and isinstance(kernel, dict)
            and set(kernel) == {"before_monotonic", "after_monotonic", "deadline_monotonic", "errno",
                                "error_type", "operation", "outcome", "pgid", "signal"}
            and kernel["pgid"] == final["pgid"] and kernel["operation"] == "os.killpg"
            and type(kernel["signal"]) is int and kernel["signal"] == 0
            and type(kernel["errno"]) is int and kernel["errno"] == errno.ESRCH
            and kernel["error_type"] == "ProcessLookupError" and kernel["outcome"] == "ABSENT_ESRCH",
            "inventory_original_group_absence_unproven")
    times = [kernel[k] for k in ("before_monotonic", "after_monotonic", "deadline_monotonic")]
    require(all(_number(v) for v in times) and times[0] <= times[1] <= times[2],
            "inventory_original_group_absence_late")
    if failure is None:
        require(final["status"] == "PASS" and final["returnCode"] == 0, "inventory_followup_not_pass")
    else:
        require(type(failure) is subprocess.TimeoutExpired and failure.cmd == argv
                and type(failure.timeout) is int and failure.timeout == 30
                and failure.__cause__ is None and failure.__context__ is None,
                "inventory_exact_unchained_timeout30_required")
        require(final["status"] == "FAIL" and final["firstFailure"] == error(failure),
                "inventory_timeout_first_failure_changed")
    return proofs

class _OneFollowup:
    def __init__(self, commands, argv, original_name, followup_name, timeout):
        self.commands, self.argv = commands, argv
        self.original_name, self.followup_name, self.timeout = original_name, followup_name, timeout
        self.calls = 0

    def json(self, argv, name, timeout=60):
        require(self.calls == 0 and argv == self.argv and name == self.original_name
                and type(timeout) is int and timeout == 30, "inventory_followup_scope_changed")
        self.calls += 1
        return self.commands.json(argv, self.followup_name, self.timeout)

class Policy:
    def __init__(self, commands, *, cwd, recheck_source, write_json):
        self.commands, self.cwd = commands, cwd
        self.recheck_source, self.write_json = recheck_source, write_json
        self.used, self.records = set(), []

    def verify(self, verify_device, item, name, states, phase):
        require(phase in BUDGETS, "inventory_recovery_phase_not_admitted")
        prefix = "booted" if phase == "postboot" else "pre-cleanup"
        match = re.fullmatch(prefix + r"-([0-9]+)", name)
        require(match is not None and (phase, name) not in self.used, "inventory_recovery_not_once")
        require((phase == "pre-cleanup") is self.commands.cleanup_mode, "inventory_recovery_wrong_phase")
        self.used.add((phase, name))
        self.recheck_source()
        try:
            return verify_device(self.commands, item, name, states)
        except subprocess.TimeoutExpired as original:
            # Only admission after complete original command finalization can authorize a follow-up.
            first = original
        state = {"policy": POLICY, "phase": phase, "name": name, "context": self.commands.context,
                 "ownedUUID": item.get("udid"), "status": "REFUSED", "originalStatus": "FAIL",
                 "firstFailure": error(first), "followupAttempts": 0, "secondaryFailures": [],
                 "followupTimeoutSeconds": BUDGETS[phase], "cleanupPolicyTotalSecondsUnchanged": 60}
        final_path = self.commands.root / (name + "-inventory-recovery.json")
        primary_secondary = None
        proofs = []
        try:
            require(str(uuid.UUID(item["udid"])).upper() == item["udid"]
                    and item["context"] == self.commands.context, "inventory_owned_item_identity")
            directory = Path(item["directory"])
            require(directory.parent == self.commands.root.parent and directory.name == "device-" + match[1],
                    "inventory_owned_item_directory")
            created_raw, created_proof = _raw(directory / "created.json", 65536)
            intent_raw, intent_proof = _raw(directory / "intent.json", 65536)
            created, intent = _json(created_raw), _json(intent_raw)
            require(created == item and intent["context"] == self.commands.context
                    and item["udid"] not in intent["baseline"] and item["createArgv"] == intent["argv"]
                    and item["name"] == intent["name"] and item["runtime"] == intent["runtime"]
                    and item["device"] == intent["device"], "inventory_creation_proof_changed")
            argv = ["xcrun", "simctl", "list", "devices", item["udid"], "--json"]
            proofs = [created_proof, intent_proof, *_command_proof(
                self.commands, name, argv, 30, self.cwd, first)]
            followup_name = name + "-inventory-recovery-v1"
            require(not final_path.exists() and not any((self.commands.root / (followup_name + suffix)).exists()
                    for suffix in (".log", ".started.json", ".command.json")), "inventory_followup_replay")
            self.recheck_source()
            _unchanged(proofs)
            state.update(status="ADMITTED", originalProofs=proofs, argv=argv, followupName=followup_name)
            intent_path = self.commands.root / (name + "-inventory-recovery-intent.json")
            self.write_json(intent_path, state)
            _, intent_binding = _raw(intent_path, 65536)
            state["recoveryIntent"] = intent_binding
            adapter = _OneFollowup(self.commands, argv, name, followup_name, BUDGETS[phase])
            state["followupAttempts"] = 1
            verify_device(adapter, item, name, states)
            require(adapter.calls == 1, "inventory_followup_not_observed")
            state["followupProofs"] = _command_proof(self.commands, followup_name, argv, BUDGETS[phase], self.cwd)
            self.recheck_source()
            _unchanged([*proofs, intent_binding])
            state["status"] = "RECOVERED_EXACT_IDENTITY"
        except BaseException as secondary:
            primary_secondary = secondary
            state["secondaryFailures"].append(error(secondary))
            state["status"] = "FOLLOWUP_FAILED" if state["followupAttempts"] else "REFUSED"
        try:
            self.write_json(final_path, state)
            _, final_binding = _raw(final_path, 65536)
            state["dispositionReceipt"] = final_binding
        except BaseException as preservation:
            state["secondaryFailures"].append({"stage": "disposition_preservation", **error(preservation)})
            state["status"] = "DISPOSITION_UNAVAILABLE"
            primary_secondary = primary_secondary or preservation
        self.records.append(state)
        if state["status"] != "RECOVERED_EXACT_IDENTITY":
            raise first from primary_secondary
        return state

    def summary(self):
        return {"policy": POLICY, "originalTimeoutFailures": len(self.records),
                "recovered": sum(r["status"] == "RECOVERED_EXACT_IDENTITY" for r in self.records),
                "observations": self.records}
