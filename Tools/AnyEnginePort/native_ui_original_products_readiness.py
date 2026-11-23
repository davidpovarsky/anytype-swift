#!/usr/bin/env python3
"""Admit both original Products origins before bounded, explicitly owned UI readiness."""
from __future__ import annotations
import ast
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import native_ui_original_products as ui
import native_ui_original_products_contract as c

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "Tools/PinkhaSimulatorGate"
if str(GATE) not in sys.path:
    sys.path.insert(0, str(GATE))
import coherent_controller_sources as source_reader
import owned_simulator_readiness as readiness
import run_owned_single_lane as kernel
import wave15_batch as owned

PROFILE = "pinkha-native-ui-original-products-readiness-v1"
MANIFEST = ROOT / "Tools/AnyEnginePort/native-ui-readiness-helpers.json"
MANIFEST_SHA = "17858c0aedc52e4a8e6547fc64c1bb6dbbc08e377b3e255f8843d15cda30eb14"
READY_ROOT = c.EVIDENCE / "native-ui-owned-readiness"
RESULT = c.EVIDENCE / "native-ui-readiness-result.json"
CURRENT_MODULES = {
    "ui": "Tools/AnyEnginePort/native_ui_original_products.py",
    "c": "Tools/AnyEnginePort/native_ui_original_products_contract.py",
    "source_reader": "Tools/PinkhaSimulatorGate/coherent_controller_sources.py",
    "readiness": "Tools/PinkhaSimulatorGate/owned_simulator_readiness.py",
    "kernel": "Tools/PinkhaSimulatorGate/run_owned_single_lane.py",
    "owned": "Tools/PinkhaSimulatorGate/wave15_batch.py",
}
LEGACY_MODULES = ("verify_archive_roundtrip", "verify_native_test_execution", "verify_custom_type",
                  "native_continuation_sources", "continue_native_acceptance", "native_ui_followup_retention")


def require(value, code):
    if not value:
        raise RuntimeError(code)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(part)
    return value.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def error_record(error):
    result = {"type": type(error).__name__, "message": str(error)}
    for name in ("timeout_observations", "quiescence_observation"):
        if hasattr(error, name):
            result[name] = getattr(error, name)
    return result


def verify_helpers():
    require(c.ROOT.resolve() == ROOT and digest(MANIFEST) == MANIFEST_SHA,
            "fixed_ui_readiness_manifest_changed")
    fixed = c.data(MANIFEST)
    require(fixed["profile"] == PROFILE, "ui_readiness_helper_profile_changed")
    observed = {}
    for relative, expected in fixed["wholeFiles"].items():
        path = ROOT / relative
        require(path.resolve() == path and not path.is_symlink() and digest(path) == expected,
                "qualified_ui_readiness_helper_file_changed:" + relative)
        observed[relative] = expected
    for relative, functions in fixed["functionSourceSlices"].items():
        path = ROOT / relative
        raw = c.regular(path, 4 * 1024**2)
        tree = ast.parse(raw)
        lines = raw.splitlines(keepends=True)
        definitions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        slices = {}
        for name, expected in functions.items():
            require(name in definitions, "required_helper_function_missing")
            node = definitions[name]
            value = b"".join(lines[node.lineno - 1:node.end_lineno])
            slices[name] = hashlib.sha256(value).hexdigest()
            require(slices[name] == expected, "qualified_ui_readiness_helper_slice_changed:" + name)
        observed[relative] = {"wholeCurrentFileSHA256": digest(path), "qualifiedFunctionSlices": slices}
    return {"manifestSHA256": MANIFEST_SHA, "helpers": observed,
            "claim": "Exact used helper scopes; not every function in their modules"}


def bind_modules(app, legacy):
    require(ROOT.resolve() == ROOT and app.resolve() == app and app != ROOT
            and not app.is_relative_to(ROOT) and not ROOT.is_relative_to(app),
            "ui_readiness_origins_must_be_disjoint")
    bindings = {}
    for name, relative in CURRENT_MODULES.items():
        module = globals()[name]
        require(Path(module.__file__).resolve() == ROOT / relative and not (ROOT / relative).is_symlink(),
                "ui_readiness_current_module_origin_changed:" + name)
        bindings[name] = {"origin": "CURRENT_CONTROL_CHECKOUT", "path": relative}
    provider = ui.provider()
    require(Path(provider.__file__).resolve() == ROOT / "Tools/AnyEnginePort/hanlin_fixture_ci.py",
            "ui_readiness_provider_origin_changed")
    bindings["provider"] = {"origin": "CURRENT_CONTROL_CHECKOUT",
                            "path": "Tools/AnyEnginePort/hanlin_fixture_ci.py"}
    require(kernel.owned is owned, "ui_readiness_worker_module_collision")
    require(set(legacy) == set(LEGACY_MODULES), "original_validator_module_set_changed")
    for name in LEGACY_MODULES:
        expected = app / "Tools/AnyEnginePort" / (name + ".py")
        require(Path(legacy[name].__file__).resolve() == expected and not expected.is_symlink(),
                "ui_readiness_original_validator_origin_changed:" + name)
        bindings[name] = {"origin": "IMMUTABLE_ORIGINAL_APP", "path": expected.relative_to(app).as_posix()}
    return bindings


def loaded_paths(app):
    roots = {"current": ROOT, "originalApp": app}
    paths = {name: {} for name in roots}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        raw = Path(filename).absolute()
        path = raw.resolve()
        for origin, root in roots.items():
            if not path.is_relative_to(root):
                continue
            require(raw == path and path.suffix == ".py" and path.is_file() and not path.is_symlink(),
                    "only_regular_git_python_modules_admitted")
            relative = path.relative_to(root).as_posix()
            require(not any(x in relative for x in ("\n", "\r", "\0", ":")),
                    "ambiguous_ui_readiness_source_path")
            require(path.stat().st_size <= source_reader.MAX_SOURCE_BYTES,
                    "ui_readiness_source_exceeds_file_bound")
            paths[origin][relative] = path
    for values in paths.values():
        require(1 <= len(values) <= 256 and
                sum(path.stat().st_size for path in values.values()) <= source_reader.MAX_BATCH_BYTES,
                "complete_bounded_ui_readiness_origin_required")
    require("Tools/AnyEnginePort/native_ui_original_products_readiness.py" in paths["current"],
            "actual_ui_readiness_driver_missing_from_loaded_closure")
    return paths


def git_source_bytes(root, head, paths):
    require(re.fullmatch("[0-9a-f]{40}", head) and paths, "exact_ui_source_commit_required")
    require(not subprocess.check_output(["git", "-C", str(root), "status", "--porcelain",
                                         "--untracked-files=no"], text=True, timeout=30).strip(),
            "ui_readiness_loaded_source_dirty")
    names = sorted(paths)
    require(all((root / name).resolve() == paths[name] and paths[name].is_relative_to(root)
                and not any(x in name for x in ("\n", "\r", "\0", ":")) for name in names),
            "ui_readiness_git_path_origin_changed")
    request = b"".join((head + ":" + name + "\n").encode("utf-8") for name in names)
    raw = subprocess.check_output(["git", "-C", str(root), "cat-file", "--batch"],
                                  input=request, timeout=30)
    original = source_reader.decode_batch(raw, names)
    hashes = {}
    for name in names:
        physical = paths[name].read_bytes()
        require(physical == original[name], "ui_readiness_physical_source_differs_from_git:" + name)
        hashes[name] = hashlib.sha256(physical).hexdigest()
    return hashes


def verify_source_closures(app, current_head, app_head):
    paths = loaded_paths(app)
    return {
        "current": {"origin": "CURRENT_CONTROL_CHECKOUT", "root": str(ROOT), "commit": current_head,
                    "files": git_source_bytes(ROOT, current_head, paths["current"])},
        "originalApp": {"origin": "IMMUTABLE_ORIGINAL_APP", "root": str(app), "commit": app_head,
                        "files": git_source_bytes(app, app_head, paths["originalApp"])},
    }


def recheck_physical_sources(app, before):
    paths = loaded_paths(app)
    after = {}
    for origin, values in paths.items():
        observed = {name: digest(path) for name, path in sorted(values.items())}
        require(observed == before[origin]["files"], "ui_readiness_loaded_source_changed_after_boot")
        after[origin] = {**before[origin], "files": observed}
    return after


def validate_worker_record(record, command, timeout, *, returned_record=None):
    require(returned_record is None or record == returned_record,
            "ui_owned_original_receipt_differs_from_returned_record")
    require(isinstance(record, dict) and record.get("argv") == command
            and record.get("cwd") == str(ROOT)
            and type(record.get("timeout_seconds")) is int and record["timeout_seconds"] == timeout,
            "ui_owned_command_origin_or_budget_changed")
    pid = record.get("worker_pid")
    require(type(pid) is int and pid > 1 and pid not in (os.getpid(), os.getpgrp())
            and record.get("owned_group_cleanup") == "TERM_THEN_KILL"
            and not record.get("cleanup_error_type") and type(record.get("return_code")) is int,
            "ui_owned_command_group_not_completed")
    require(record.get("status") in {"COMPLETE", "WORKER_FAILED", "TIMED_OUT", "CANCELLED", "FAIL"},
            "ui_owned_command_status_unknown")
    return pid


def kernel_absence(record, command, timeout, *, returned_record=None):
    pid = validate_worker_record(record, command, timeout, returned_record=returned_record)
    start = time.monotonic()
    deadline = start + 10
    observation = kernel._sdk06_kernel_group_observation(pid, deadline)
    try:
        require(observation.get("pgid") == pid and type(observation["pgid"]) is int
                and observation.get("operation") == "os.killpg" and observation.get("signal") == 0,
                "ui_owned_kernel_observation_identity_changed")
        times = [observation.get(name) for name in
                 ("before_monotonic", "after_monotonic", "deadline_monotonic")]
        require(all(type(value) in (int, float) and math.isfinite(value) for value in times)
                and start <= times[0] <= times[1] <= deadline and times[2] == deadline,
                "ui_owned_kernel_observation_outside_fixed_budget")
        require(observation.get("outcome") == "ABSENT_ESRCH" and observation.get("errno") == errno.ESRCH,
                "ui_owned_kernel_group_absence_not_proven")
    except BaseException as error:
        error.quiescence_observation = {"scope": PROFILE, "status": "FAIL", "pgid": pid,
            "liveMembers": None, "budgetSeconds": 10, "kernelObservation": observation}
        raise
    return {"scope": PROFILE, "status": "PASS", "pgid": pid, "liveMembers": 0,
            "budgetSeconds": 10, "absenceSource": "KERNEL_ESRCH", "kernelObservation": observation}


def run_owned(command, log, timeout):
    """Preserve the real worker record and the first failure; never relabel an SDK profile."""
    require(type(timeout) is int and timeout > 0 and isinstance(command, list)
            and command and all(isinstance(x, str) for x in command), "explicit_ui_owned_command_required")
    log = Path(log)
    require(log.resolve() == log and log.parent.is_dir() and not log.exists(),
            "fresh_ui_owned_log_required")
    command_path = log.with_suffix(".command.json")
    quiescence_path = log.with_suffix(".ui-quiescence.json")
    require(not command_path.exists() and not quiescence_path.exists(), "fresh_ui_owned_receipts_required")
    first_error = None
    returned_record = None
    quiescence_error = None
    result = {"scope": PROFILE, "status": "FAIL", "command": command, "cwd": str(ROOT),
              "timeoutSeconds": timeout, "kernelBudgetSeconds": 10}
    try:
        record = owned.run_worker_command(command, ROOT, log, timeout, record_cwd=True)
        returned_record = record
        if record.get("return_code") != 0 or record.get("status") != "COMPLETE":
            first_error = subprocess.CalledProcessError(record.get("return_code"), command)
    except BaseException as error:
        first_error = error
    try:
        record = c.data(command_path)
        result["originalCommandSHA256"] = digest(command_path)
        result["originalLogSHA256"] = digest(log)
        result["quiescence"] = kernel_absence(record, command, timeout, returned_record=returned_record)
    except BaseException as error:
        quiescence_error = error
        result["quiescenceFailure"] = error_record(error)
    if first_error is not None:
        result["commandFailure"] = error_record(first_error)
    if first_error is None and quiescence_error is None:
        result["status"] = "PASS"
    try:
        write_new(quiescence_path, result)
    except BaseException as observation_error:
        if first_error is not None:
            first_error.ui_observation_write_failure = error_record(observation_error)
            raise first_error from observation_error
        if quiescence_error is not None:
            quiescence_error.ui_observation_write_failure = error_record(observation_error)
            raise quiescence_error from observation_error
        raise
    if first_error is not None:
        raise first_error
    if quiescence_error is not None:
        raise quiescence_error
    return {"return_code": record["return_code"], "timed_out": False,
            "originalCommandSHA256": result["originalCommandSHA256"],
            "originalLogSHA256": result["originalLogSHA256"], "ownedQuiescence": result["quiescence"]}, log


class UICommands:
    require = staticmethod(require)
    digest = staticmethod(digest)
    write = staticmethod(write_new)

    def __init__(self, selection, evidence=None):
        self.selection = selection
        self.evidence = READY_ROOT if evidence is None else evidence
        udid = selection["udid"]
        self.commands = {
            "before": (["xcrun", "simctl", "list", "devices", udid, "--json"], 60),
            "boot": (["xcrun", "simctl", "boot", udid], 120),
            "boot-status": (["xcrun", "simctl", "bootstatus", udid, "-b"], 180),
        }

    def run_logged(self, command, app, evidence, name, timeout, *, output=None):
        require(Path(app) == ROOT and Path(evidence) == self.evidence and name in self.commands
                and self.commands[name] == (command, timeout), "unadmitted_ui_readiness_command")
        observed, log = run_owned(command, evidence / (name + ".log"), timeout)
        if output is not None:
            require(name == "before" and output == evidence / "before.json",
                    "ui_readiness_inventory_output_changed")
            with output.open("xb") as stream:
                stream.write(log.read_bytes())
        return observed, log


def admit_readiness():
    fixed, ctx, locations, admitted, legacy = ui.current()
    require(not RESULT.exists() and not READY_ROOT.exists(), "fresh_ui_readiness_execution_required")
    helpers = verify_helpers()
    bindings = bind_modules(locations["app"], legacy)
    sources = verify_source_closures(locations["app"], ctx["controlCommit"], fixed["origin"]["commit"])
    runtime = c.data(locations["evidence"] / "native-ui-original-runtime.json")
    require(runtime["ownedSimulatorUDID"] == admitted["ownedSimulatorUDID"], "ui_readiness_owned_uuid_changed")
    selection = {"udid": admitted["ownedSimulatorUDID"], "name": "AnyNativePort-" + ctx["currentRunID"],
                 "runtime": runtime["runtime"], "device": runtime["device"]}
    require(selection["runtime"]["identifier"] == fixed["runtime"]["identifier"]
            and selection["device"]["identifier"] == fixed["runtime"]["deviceType"],
            "ui_readiness_original_runtime_pair_changed")
    before = {"profile": PROFILE, "currentContext": ctx, "applicationCommit": fixed["origin"]["commit"],
              "admissionSHA256": digest(c.ADMISSION), "helpers": helpers,
              "moduleBindings": bindings, "sources": sources, "selection": selection}
    return before, locations, selection


def run():
    require(not RESULT.exists(), "fresh_ui_readiness_result_required")
    result = {"scope": PROFILE, "status": "FAIL", "newBuilds": 0, "testsExecuted": 0,
              "originalProductsRebuilt": False, "providerBootedVerificationStillRequired": True}
    try:
        before, locations, selection = admit_readiness()
        write_new(c.EVIDENCE / "native-ui-readiness-source-before.json", before)
        ready = readiness.ensure_ready(app=ROOT, evidence=READY_ROOT, selection=selection,
            expected_name=selection["name"], pair=UICommands(selection), require_initial_shutdown=True)
        after = recheck_physical_sources(locations["app"], before["sources"])
        require(digest(c.ADMISSION) == before["admissionSHA256"]
                and digest(MANIFEST) == before["helpers"]["manifestSHA256"],
                "ui_readiness_admission_or_manifest_changed")
        write_new(c.EVIDENCE / "native-ui-readiness-source-after.json",
                  {"sources": after, "admissionSHA256": digest(c.ADMISSION)})
        result.update(status="ADMITTED_ORIGINAL_PRODUCTS_OWNED_SIMULATOR_READY",
                      controlCommit=before["currentContext"]["controlCommit"],
                      applicationCommit=before["applicationCommit"],
                      currentRunID=before["currentContext"]["currentRunID"],
                      currentRunAttempt=before["currentContext"]["currentRunAttempt"],
                      ownedSimulatorUDID=selection["udid"], readiness=ready,
                      sourceBeforeSHA256=digest(c.EVIDENCE / "native-ui-readiness-source-before.json"),
                      sourceAfterSHA256=digest(c.EVIDENCE / "native-ui-readiness-source-after.json"))
        return result
    except BaseException as error:
        result["failure"] = error_record(error)
        raise
    finally:
        original_error = sys.exc_info()[1]
        try:
            write_new(RESULT, result)
        except BaseException as observation_error:
            if original_error is not None:
                original_error.ui_observation_write_failure = error_record(observation_error)
                raise original_error from observation_error
            raise


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
