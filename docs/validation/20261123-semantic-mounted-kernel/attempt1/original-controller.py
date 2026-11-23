#!/usr/bin/env python3
"""Run exactly one new mounted-caller control on the main thread, preserving originals."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import threading
import time
import traceback
import unittest
from datetime import datetime, timezone

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTPUT = Path("/mnt/development/projects/evidence/semantic-mounted-kernel-20261123/attempt1")
MANIFEST = HERE / "control-inputs.json"
TEST_RELATIVE = "Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_kernel_quiescence.py"
METHOD = "test_actual_mounted_consumer_keeps_owned_kernel_deadline_and_first_error"
BB = "bb046d988d57bf5f530f71b8b86588b21ab7ded2"
QUALIFIED = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
SUPERVISOR = "Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
BEFORE = 'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE):'
AFTER = 'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE, "semantic-page154"):'
COMPOSED_INPUTS = {
    "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py": [
        "main9cafd",
        "9cafd32811e50f4e883efb034888d7ce1e349c02",
        "17b3b349025ede11e4e4081fdd664cd0eb3cf6a1f9e7fe1ed41a0b888f42d189"
    ],
    "Tools/PinkhaSimulatorGate/wave15_batch.py": [
        "release6acab",
        "6acab36f450ce411a8614f23e55cb14a5602ed58",
        "75e923d8c9718553d80c6aa3fd5338f06e2622e275ba10bc5537d03c4ba03193"
    ],
    "Tools/PinkhaNativeDerived/package_evidence.py": [
        "main9cafd",
        "9cafd32811e50f4e883efb034888d7ce1e349c02",
        "8400bd4ac7bbc61871b51f1021c3dbbb1de5800094e07129417a784d24337309"
    ]
}
NON_IMPORTED_POLICY = "Tools/PinkhaNativeDerived/package_evidence.py"
events = []


def require(value, code):
    if not value:
        raise RuntimeError(code)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30)


def snapshot():
    head = git("rev-parse", "HEAD").decode().strip()
    require(not git("status", "--porcelain").strip(), "dirty_control_source")
    require(git("show", head + ":" + MANIFEST.relative_to(ROOT).as_posix()) == MANIFEST.read_bytes(),
            "manifest_not_exact_frozen_git_source")
    declaration = read(MANIFEST)
    require(declaration["original_controller"] == BB and declaration["qualified_supervisor_origin"] == QUALIFIED
            and declaration["selected_methods"] == [METHOD]
            and declaration["protocol"] == "pinkha-page154-mounted-kernel-control-inputs-v2"
            and declaration["composed_inputs"] == COMPOSED_INPUTS
            and declaration["non_imported_policy_paths"] == [NON_IMPORTED_POLICY]
            and len(declaration["files"]) == 35, "wrong_fixed_control_scope")
    changed = git("diff", "--name-only", BB, head).decode().splitlines()
    allowed_changes = {SUPERVISOR, TEST_RELATIVE, *COMPOSED_INPUTS}
    require(changed and all(path in allowed_changes
                           or path.startswith("docs/validation/20261123-semantic-mounted-kernel/")
                           for path in changed), "unexpected_app_or_controller_change")
    raw = (ROOT / SUPERVISOR).read_bytes()
    require(raw.count(AFTER.encode()) == 1 and BEFORE.encode() not in raw,
            "exact_new_page_profile_hunk_missing")
    baseline = raw.replace(AFTER.encode(), BEFORE.encode(), 1)
    require(hashlib.sha256(baseline).hexdigest() ==
            "627c5b3dde88e11aaf89d157cf4a05152e42a7fc6ba9545fac13607cf7923d51"
            and baseline == git("show", QUALIFIED + ":" + SUPERVISOR),
            "whole_file_inverse_does_not_recover_qualified_75bd")
    require(hashlib.sha256(git("show", BB + ":" + SUPERVISOR)).hexdigest() ==
            "72d3ea9028133a11a1d148fcb04d2f59e0757a804cbc5e9480ebdb07e6ccd361",
            "original_bb_supervisor_changed")
    inputs = {}
    for name, expected in declaration["files"].items():
        path = ROOT / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and path.resolve() == path and path.is_file() and not path.is_symlink(), "invalid_source_path")
        info = path.stat()
        row = {"sha256": sha(path), "bytes": info.st_size, "mode": stat.S_IMODE(info.st_mode),
               "inode": info.st_ino, "device": info.st_dev, "mtime_ns": info.st_mtime_ns}
        require(row["sha256"] == expected["sha256"] and row["bytes"] == expected["bytes"],
                "physical_input_changed:" + name)
        require(hashlib.sha256(git("show", head + ":" + name)).hexdigest() == row["sha256"],
                "current_git_input_changed:" + name)
        if name in COMPOSED_INPUTS:
            origin, revision, pinned_hash = COMPOSED_INPUTS[name]
            require(expected["origin"] == origin and row["sha256"] == pinned_hash
                    and git("show", revision + ":" + name) == path.read_bytes(),
                    "fixed_integrated_dependency_changed:" + name)
        elif expected["origin"] == "bb046":
            require(git("show", BB + ":" + name) == path.read_bytes(), "original_caller_or_dependency_changed:" + name)
        else:
            require(expected["origin"] in ("new_control", "new_semantic_profile_over_75bd"),
                    "unknown_source_origin")
        inputs[name] = row
    return {"source_sha": head, "input_manifest_sha256": sha(MANIFEST),
            "original_controller": BB, "qualified_supervisor_origin": QUALIFIED,
            "composed_inputs": COMPOSED_INPUTS, "non_imported_policy_paths": [NON_IMPORTED_POLICY],
            "whole_supervisor_inverse_to_75bd": True,
            "product_source_changes": 0, "inputs": inputs}


def loaded_sources():
    expected = read(MANIFEST)["files"]
    rows = {}
    for alias, module in list(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        path = Path(raw).resolve()
        if path.is_relative_to(ROOT):
            name = path.relative_to(ROOT).as_posix()
            require(name in expected and sha(path) == expected[name]["sha256"],
                    "unbound_actual_repository_module:" + name)
            row = rows.setdefault(name, {"sha256": sha(path), "aliases": []})
            row["aliases"].append(alias)
        elif str(path).startswith("/mnt/development/projects/worktrees/"):
            raise RuntimeError("foreign_actual_repository_module:" + str(path))
    require(NON_IMPORTED_POLICY not in rows, "packaging_policy_must_not_execute_in_control")
    for row in rows.values():
        row["aliases"].sort()
    return rows


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        events.append({"event": "START", "test": test.id(), "time": now()})
        super().startTest(test)

    def addSuccess(self, test):
        events.append({"event": "PASS", "test": test.id(), "time": now()})
        super().addSuccess(test)

    def addFailure(self, test, error):
        events.append({"event": "FAIL", "test": test.id(), "time": now()})
        super().addFailure(test, error)

    def addError(self, test, error):
        events.append({"event": "ERROR", "test": test.id(), "time": now()})
        super().addError(test, error)

    def addSkip(self, test, reason):
        events.append({"event": "SKIP", "test": test.id(), "time": now(), "reason": reason})
        super().addSkip(test, reason)


def main():
    require(threading.current_thread() is threading.main_thread(), "actual_control_requires_main_thread")
    require(shutil.disk_usage("/mnt/development").free >= 2500000000 and not OUTPUT.exists(),
            "fresh_owned_attempt_and_capacity_required")
    OUTPUT.mkdir(parents=True)
    original_directory = OUTPUT / "originals"
    original_directory.mkdir(mode=0o700)
    os.environ["PINKHA_PAGE_KERNEL_CONTROL_ORIGINALS"] = str(original_directory)
    (OUTPUT / "original-controller.py").write_bytes(Path(__file__).read_bytes())
    record = {"status": "FAIL", "started_at": now(), "selected_methods": [METHOD],
              "new_app_or_ui_builds": 0, "product_methods": 0, "apple_commands": 0,
              "old_control_methods_reexecuted": 0, "actual_apple_acceptance": "NOT_RUN",
              "python": sys.version, "python_executable": sys.executable,
              "python_executable_sha256": sha(sys.executable)}
    before = None
    loaded_before = None
    result = None
    failure = None
    try:
        before = snapshot()
        record["source_sha"] = before["source_sha"]
        save(OUTPUT / "source-before.json", before)
        spec = importlib.util.spec_from_file_location("test_mounted_kernel_quiescence", ROOT / TEST_RELATIVE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        loaded_before = loaded_sources()
        save(OUTPUT / "loaded-sources-before.json", loaded_before)
        case = module.MountedPageKernelCompositionTests(METHOD)
        started = time.monotonic()
        with (OUTPUT / "controls.log").open("x") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(
                unittest.TestSuite([case]))
        record.update(elapsed_seconds=time.monotonic()-started, tests_run=result.testsRun,
                      failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
        require(result.wasSuccessful() and result.testsRun == 1 and not result.skipped,
                "original_new_control_failed")
        expected_id = "test_mounted_kernel_quiescence.MountedPageKernelCompositionTests." + METHOD
        require([(r["event"], r["test"]) for r in events] == [("START", expected_id), ("PASS", expected_id)],
                "unexpected_actual_named_outcomes")
        record["status"] = "PASS_ONE_NEW_MOUNTED_CALLER_CONTROL"
    except BaseException as error:
        failure = error
        record["error"] = {"type": type(error).__name__, "message": str(error)}
        (OUTPUT / "runner-error.log").write_text(traceback.format_exc())
    finally:
        try:
            after = snapshot()
            save(OUTPUT / "source-after.json", after)
            record["source_inputs_unchanged"] = before == after
            require(before == after, "control_changed_source_or_mode_inputs")
            loaded_after = loaded_sources()
            save(OUTPUT / "loaded-sources-after.json", loaded_after)
            record["loaded_sources_unchanged"] = loaded_before == loaded_after
            require(loaded_before == loaded_after, "actual_module_alias_or_source_changed")
        except BaseException as error:
            record["postflight_failure"] = {"type": type(error).__name__, "message": str(error)}
            record["status"] = "FAIL"
            (OUTPUT / "postflight-error.log").write_text(traceback.format_exc())
            if failure is None:
                failure = error
        if failure is not None:
            record["status"] = "FAIL"
        save(OUTPUT / "events.json", events)
        record["finished_at"] = now()
        record["free_bytes_final"] = shutil.disk_usage("/mnt/development").free
        record["originals"] = {path.relative_to(OUTPUT).as_posix():
            {"sha256": sha(path), "bytes": path.stat().st_size, "mode": stat.S_IMODE(path.stat().st_mode)}
            for path in sorted(OUTPUT.rglob("*")) if path.is_file() and not path.is_symlink()}
        save(OUTPUT / "result.json", record)
        print(json.dumps({"status": record["status"], "tests_run": record.get("tests_run", 0),
                          "result_sha256": sha(OUTPUT / "result.json"), "product_methods": 0}))
    return 0 if record["status"] == "PASS_ONE_NEW_MOUNTED_CALLER_CONTROL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
