#!/usr/bin/env python3
"""Read the preserved UI control evidence only; do not import or execute any tested module."""
import ast
from collections import Counter
from datetime import datetime, timezone
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ORIGINAL = Path("/mnt/development/projects/evidence/native-ui-owned-readiness-20261123/attempt1")
OUTPUT = ORIGINAL.parent / "audit-only-attempt1"
SOURCE = "c30e20e42ae6c52b7c4d251fc59630c2ff2f677c"
APP = Path("/mnt/development/projects/worktrees/anytype-wave15-ui-qualified-continuation-20261123")
APP_SOURCE = "4b09cc5478c60c1c6728a54f2a27a115637a835b"
RESULT_SHA = "42969ef092224e45ad7b29e113ffd15712b2bde9d094f4028f60214154b1da97"
CONTROLLER_SHA = "2c29e7c8fe17e2f5fd3eb839c0fa3b18e0de0256aece77962584b5843d173e60"
FUTURE_SHA = "3c2dbb686c6fc606b9b869ca28888c477d2b80068a604edc1090c75f054b1200"
INPUTS_SHA = "1193dcef9d33e36d0b8eebd84149891cabd5948072dfdc88122a74a30cd8bf1f"
PROFILE = "pinkha-native-ui-original-products-readiness-v1"
TEST_MODULE = "test_native_ui_original_products_readiness.UIOriginalProductsReadinessTests."
METHODS = (
 "test_owned_command_binds_actual_child_and_preserves_first_failure",
 "test_driver_binds_real_both_origin_imports_before_exact_readiness",
)


def require(value, code):
    if not value:
        raise RuntimeError(code)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1048576), b""):
            h.update(part)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=30)


def artifact_bindings(result):
    expected = result["originals"]
    require(len(expected) == 70, "exact_original_artifact_count")
    found = {}
    for name, row in expected.items():
        path = ORIGINAL / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and path.resolve() == path and path.is_file() and not path.is_symlink(),
                "original_artifact_path_changed")
        info = path.stat()
        require(info.st_size == row["bytes"] and stat.S_IMODE(info.st_mode) == row["mode"]
                and digest(path) == row["sha256"], "original_artifact_bytes_or_mode_changed")
        found[name] = dict(row)
    require(digest(ORIGINAL / "result.json") == RESULT_SHA, "original_failed_result_changed")
    return found


def source_bindings():
    before = read(ORIGINAL / "source-before.json")
    after = read(ORIGINAL / "source-after.json")
    require(before == after and before["source_sha"] == SOURCE and
            before["original_app_sha"] == APP_SOURCE and before["input_manifest_sha256"] == INPUTS_SHA
            and before["controller_sha256"] == CONTROLLER_SHA and len(before["inputs"]) == 70,
            "original_source_or_mode_snapshots_changed")
    path = ROOT / "docs/validation/20261123-native-ui-owned-readiness/control-inputs.json"
    require(digest(path) == INPUTS_SHA and not git(ROOT, "status", "--porcelain").strip()
            and git(APP, "rev-parse", "HEAD").decode().strip() == APP_SOURCE
            and not git(APP, "status", "--porcelain").strip(), "current_source_or_original_app_changed")
    declaration = read(path)
    for item in declaration["inputs"]:
        root = ROOT if item["origin"] == "current" else APP
        revision = SOURCE if item["origin"] == "current" else APP_SOURCE
        value = root / item["path"]
        require(value.resolve() == value and value.is_file() and not value.is_symlink(),
                "original_declared_source_path_changed")
        info = value.stat()
        observed = {"sha256": digest(value), "bytes": info.st_size, "mode": stat.S_IMODE(info.st_mode),
                    "inode": info.st_ino, "device": info.st_dev, "mtime_ns": info.st_mtime_ns}
        key = item["origin"] + ":" + item["path"]
        require(observed == before["inputs"][key] and observed["sha256"] == item["sha256"]
                and observed["bytes"] == item["bytes"], "original_declared_source_identity_changed")
        original = git(ROOT, "show", revision + ":" + item["path"])
        require(hashlib.sha256(original).hexdigest() == item["sha256"], "frozen_git_source_binding_changed")
    return before


def original_methods(result):
    require(result["status"] == "FAIL" and result["source_sha"] == SOURCE
            and result["tests_run"] == 2 and result["failures"] == result["errors"] == result["skipped"] == 0,
            "original_wrapper_or_control_counts_changed")
    require(result["error"] == {"type": "AttributeError",
             "message": "'RecordedResult' object has no attribute 'isSuccessful'"},
            "original_post_test_error_changed")
    require(result["declared_inputs_unchanged"] is True
            and result["new_builds"] == result["apple_commands_executed"] ==
                result["product_methods_executed"] == result["old_test_methods_reexecuted"] == 0,
            "original_control_scope_changed")
    events = read(ORIGINAL / "events.json")
    expected = [(kind, TEST_MODULE + name) for name in METHODS for kind in ("START", "PASS")]
    require([(e["event"], e["test"]) for e in events] == expected, "actual_named_outcomes_changed")
    log = (ORIGINAL / "controls.log").read_text()
    require(digest(ORIGINAL / "controls.log") == "b591c63eff4fbb5ae60103936d6a8521c36852bbcebf1ea058c9017e4ad22597"
            and log.endswith("\nOK\n") and "Ran 2 tests in 1.462s" in log,
            "original_unittest_output_changed")
    original = (ORIGINAL / "controller.py").read_bytes()
    future = (HERE / "future-controller-static-correction.py").read_bytes()
    require(digest(ORIGINAL / "controller.py") == CONTROLLER_SHA
            and digest(HERE / "future-controller-static-correction.py") == FUTURE_SHA,
            "controller_original_or_static_correction_changed")
    require(original.count(b"result.isSuccessful()") == 1 and
            future.replace(b"result.wasSuccessful()", b"result.isSuccessful()", 1) == original,
            "only_exact_future_wrapper_typo_correction_allowed")
    ast.parse(future)
    return {"actual_named_passes": [TEST_MODULE + n for n in METHODS], "original_wrapper_status": "FAIL",
            "post_test_failure": result["error"], "future_wrapper_executed": False}


def final_test_closure(source):
    original = ORIGINAL / "originals/driver-composition"
    initial = read(original / "actual-import-origin-closures.json")["sourceBindings"]
    final = read(original / "final-physical-source-bindings.json")
    outer = read(ORIGINAL / "loaded-sources-before.json")
    flat = {origin + ":" + name: value for origin, row in final.items() for name, value in row["files"].items()}
    require(final == initial and len(flat) == 21 and
            {name: row["sha256"] for name, row in outer.items()} == flat,
            "actual_final_test_file_closure_changed")
    require(set(final) == {"current", "originalApp"} and final["current"]["commit"] == SOURCE
            and final["originalApp"]["commit"] == APP_SOURCE, "final_test_origins_changed")
    for name, expected in flat.items():
        require(name in source["inputs"] and source["inputs"][name]["sha256"] == expected,
                "final_test_file_not_declared_or_changed")
    require(not (ORIGINAL / "loaded-sources-after.json").exists(), "do_not_manufacture_outer_loaded_after")
    raw = git(ROOT, "show", SOURCE + ":Tools/AnyEnginePort/test_native_ui_original_products_readiness.py")
    require(hashlib.sha256(raw).hexdigest() == "91d1572131d61b7757f52f074c31909a996ad6aa0f6c7b0f0a2b33ee5700715e",
            "original_control_source_changed")
    cls = next(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == "UIOriginalProductsReadinessTests")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == METHODS[-1])
    final_statement = ast.get_source_segment(raw.decode(), method.body[-1])
    require(final_statement == 'r.write_new(directory / "final-physical-source-bindings.json",\n                    r.recheck_physical_sources(app, sources))', "final_test_map_position_changed")
    return {"actual_final_test_file_count": len(flat),
            "current_files": sum(name.startswith("current:") for name in flat),
            "immutable_app_files": sum(name.startswith("originalApp:") for name in flat),
            "capture_position": "LAST_STATEMENT_OF_LAST_EXECUTED_TEST_BODY_THEN_ORIGINAL_PASS_EVENT",
            "outer_loaded_after": "ABSENT_AFTER_ORIGINAL_RUNNER_ATTRIBUTE_ERROR",
            "post_runner_module_alias_map_claimed": False, "file_sha256": flat}


def check_absence(value, pid):
    require(value.get("scope") == PROFILE and value.get("status") == "PASS"
            and value.get("pgid") == pid and type(value.get("pgid")) is int
            and value.get("liveMembers") == 0 and value.get("budgetSeconds") == 10,
            "original_ui_group_absence_record_changed")
    obs = value["kernelObservation"]
    require(obs.get("pgid") == pid and obs.get("operation") == "os.killpg" and obs.get("signal") == 0
            and obs.get("outcome") == "ABSENT_ESRCH" and obs.get("errno") == errno.ESRCH,
            "original_kernel_absence_not_proven")
    times = [obs.get(k) for k in ("before_monotonic", "after_monotonic", "deadline_monotonic")]
    require(all(type(v) in (int, float) and math.isfinite(v) for v in times)
            and times[0] <= times[1] <= times[2] and 0 <= times[2] - times[0] <= 10,
            "original_kernel_observation_not_timely")


def owned_children(result):
    originals = ORIGINAL / "originals"
    paths = sorted(originals.rglob("*.command.json"))
    require(len(paths) == 8, "exact_eight_original_control_children_required")
    items = []
    for path in paths:
        record = read(path)
        pid = record.get("worker_pid")
        require(type(pid) is int and pid > 1 and record["argv"][:2] == [result["python_executable"], "-c"]
                and record["cwd"] == str(ROOT) and record["owned_group_cleanup"] == "TERM_THEN_KILL"
                and not record.get("cleanup_error_type"), "original_owned_command_identity_changed")
        query_path = path.with_name(path.name.replace(".command.json", ".ui-quiescence.json"))
        query = read(query_path)
        require(query["scope"] == PROFILE and query["originalCommandSHA256"] == digest(path),
                "original_ui_command_hash_changed")
        log = path.with_name(path.name.replace(".command.json", ".log"))
        require(query["originalLogSHA256"] == digest(log), "original_owned_log_changed")
        absence = query.get("quiescence")
        absence_path = query_path
        if absence is None:
            require(path == originals / "owned-command/nonzero.command.json" and record["return_code"] == 9
                    and query["commandFailure"]["type"] == "CalledProcessError"
                    and query["quiescenceFailure"]["type"] == "PermissionError",
                    "original_first_failure_or_injected_error_changed")
            absence_path = originals / "owned-command/nonzero-actual-owned-group-absence.json"
            absence = read(absence_path)
        check_absence(absence, pid)
        require(query["status"] == ("PASS" if record["return_code"] == 0 else "FAIL"),
                "nonzero_original_command_cannot_be_relabelled_pass")
        items.append({"path": path.relative_to(ORIGINAL).as_posix(), "pid": pid,
                      "return_code": record["return_code"], "command_sha256": digest(path),
                      "quiescence_sha256": digest(query_path), "actual_absence_sha256": digest(absence_path)})
    calibration = read(originals / "owned-command/complete.log")
    calibrated_command = read(originals / "owned-command/complete.command.json")
    require(calibration["pid"] == calibration["pgid"] == calibrated_command["worker_pid"],
            "actual_control_child_pid_pgid_calibration_changed")
    require(len({v["pid"] for v in items}) == 8 and
            Counter(v["return_code"] for v in items) == Counter({0: 6, 9: 1, 13: 1}),
            "original_child_count_or_exit_outcomes_changed")
    for case in ("success", "bootstatus-failure"):
        base = originals / "driver-composition" / case
        mapping = read(base / "control-call-map.json")
        require(mapping["actualCIAdmissionClaimed"] is False and
                mapping["actualAppleCommandsExecuted"] == mapping["productMethodsExecuted"] == 0,
                "control_fixture_must_not_claim_actual_apple_admission")
        observations = mapping["observations"]
        require([x["phase"] for x in observations] ==
                ["current_admission", "both_real_git_closures"] + ["controlled_simulator_command"] * 3,
                "actual_control_source_before_readiness_order_changed")
        for entry, name, seconds in zip(observations[2:], ("before", "boot", "boot-status"), (60, 120, 180)):
            command = read(base / "evidence/owned-readiness" / (name + ".command.json"))
            require(entry["actualOwnedControlArgv"] == command["argv"] and
                    entry["timeoutSeconds"] == command["timeout_seconds"] == seconds and
                    entry["appleCommandExecuted"] is False, "actual_control_argv_or_budget_mapping_changed")
    return items


def main():
    require(shutil.disk_usage("/mnt/development").free >= 2500000000 and not OUTPUT.exists(),
            "fresh_read_only_audit_and_capacity_required")
    OUTPUT.mkdir()
    result = {"status": "FAIL_ORIGINAL_EVIDENCE_AUDIT", "started_at": datetime.now(timezone.utc).isoformat(),
              "new_controls_executed": 0, "new_child_commands_executed": 0,
              "new_apple_commands_executed": 0, "original_aggregate_relabelled": False}
    try:
        audit_head = git(ROOT, "rev-parse", "HEAD").decode().strip()
        source = git(ROOT, "show", audit_head + ":" + Path(__file__).resolve().relative_to(ROOT).as_posix())
        require(hashlib.sha256(source).hexdigest() == digest(__file__), "frozen_auditor_source_changed")
        old = read(ORIGINAL / "result.json")
        before = artifact_bindings(old)
        source_before = source_bindings()
        methods = original_methods(old)
        closure = final_test_closure(source_before)
        children = owned_children(old)
        require(artifact_bindings(old) == before and source_bindings() == source_before,
                "audit_changed_originals_or_sources")
        result.update(status="PASS_ORIGINAL_TWO_CONTROL_RESULTS_AUDITED",
                      audit_source_sha=audit_head, audit_file_sha256=digest(__file__),
                      original_aggregate_status="FAIL", original_aggregate_sha256=RESULT_SHA,
                      original_controller_sha256=CONTROLLER_SHA, future_static_controller_sha256=FUTURE_SHA,
                      methods=methods, source_input_count=70, original_bound_artifact_count=70,
                      actual_last_test_file_closure=closure, actual_owned_children=children,
                      source_modes_and_original_bytes_unchanged=True)
    except BaseException as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        write(OUTPUT / "audit.json", result)
        print(json.dumps({"status": result["status"], "audit_sha256": digest(OUTPUT / "audit.json"),
                          "new_controls_executed": 0, "new_child_commands_executed": 0}))


if __name__ == "__main__":
    main()
