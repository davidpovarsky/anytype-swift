#!/usr/bin/env python3
"""Pinned execution of only the two new mounted source-origin controls."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import threading
import time
import traceback
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "docs/validation/20261123-page-source-origins/control-inputs.json"
METHODS = (
    "test_real_current_controller_and_original_app_have_separate_complete_source_admission",
    "test_actual_origin_adapter_refuses_wrong_roots_heads_foreign_imports_and_postflight_drift",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30)


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with path.open("xb") as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())
    path.chmod(0o400)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def source_snapshot(head, manifest):
    require(git("rev-parse", "HEAD").decode().strip() == head, "Wrong frozen source HEAD")
    require(git("status", "--porcelain") == b"", "Frozen writer must be completely clean")
    result = {}
    for row in manifest["inputs"]:
        path = ROOT / row["path"]
        mode = path.lstat()
        require(stat.S_ISREG(mode.st_mode) and mode.st_nlink == 1, "Unexpected input file kind")
        raw = path.read_bytes()
        require(digest(raw) == row["sha256"] and len(raw) == row["bytes"]
                and format(stat.S_IMODE(mode.st_mode), "04o") == row["physical_mode"],
                "Frozen physical input differs: " + row["path"])
        expected = git("show", head + ":" + row["path"])
        require(expected == raw, "Exact frozen Git source differs: " + row["path"])
        result[row["path"]] = {
            "bytes": len(raw), "sha256": digest(raw), "physical_mode": row["physical_mode"],
            "device": str(mode.st_dev), "inode": str(mode.st_ino),
            "mtime_ns": str(mode.st_mtime_ns), "ctime_ns": str(mode.st_ctime_ns),
        }
    require(MANIFEST.read_bytes() == git("show", head + ":" + MANIFEST.relative_to(ROOT).as_posix()),
            "Input manifest is not exact frozen Git content")
    return result


def loaded_sources(snapshot):
    result = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.suffix == ".py" and path.is_relative_to(ROOT):
            relative = path.relative_to(ROOT).as_posix()
            require(relative in snapshot and digest(path.read_bytes()) == snapshot[relative]["sha256"],
                    "Undeclared loaded outer source: " + relative)
            result[name] = {"path": relative, "sha256": snapshot[relative]["sha256"]}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    require(threading.current_thread() is threading.main_thread(), "Main-thread test execution required")
    require(shutil.disk_usage(ROOT).free >= 2_500_000_000, "Capacity reserve is required")
    evidence = args.evidence.resolve()
    allowed = Path("/mnt/development/projects/evidence/page-source-origins-20261123").resolve()
    require(evidence.parent == allowed and evidence.name == "attempt1"
            and not evidence.exists() and not allowed.is_symlink(), "One fresh original attempt only")
    allowed.mkdir(mode=0o700, exist_ok=True)
    evidence.mkdir(mode=0o700)
    child_output = evidence / "owned-child-originals"
    child_output.mkdir(mode=0o700)
    manifest = json.loads(MANIFEST.read_bytes())
    events = []
    before = None
    started = time.monotonic()
    outer_failure = None
    result = None
    records = {}
    try:
        before = source_snapshot(args.expected_head, manifest)
        records["source_before"] = save(evidence / "source-before.json", before)
        records["manifest"] = save(evidence / "manifest-binding.json", {
            "path": str(MANIFEST), "bytes": MANIFEST.stat().st_size,
            "sha256": digest(MANIFEST.read_bytes()), "head": args.expected_head})
        path = ROOT / "Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_source_origins.py"
        spec = importlib.util.spec_from_file_location("page_source_origin_controls", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        records["loaded_outer_before"] = save(evidence / "loaded-outer-before.json", loaded_sources(before))
        os.environ["PINKHA_PAGE_ORIGIN_CONTROL_OUTPUT"] = str(child_output)

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                events.append({"event": "START", "method": test.id(), "monotonic": time.monotonic()})
                super().startTest(test)

            def addSuccess(self, test):
                events.append({"event": "PASS", "method": test.id(), "monotonic": time.monotonic()})
                super().addSuccess(test)

            def addFailure(self, test, error):
                events.append({"event": "FAIL", "method": test.id(), "monotonic": time.monotonic()})
                super().addFailure(test, error)

            def addError(self, test, error):
                events.append({"event": "ERROR", "method": test.id(), "monotonic": time.monotonic()})
                super().addError(test, error)

        suite = unittest.TestSuite(module.PageSourceOriginControls(name) for name in METHODS)
        with (evidence / "controls.log").open("x") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=Result).run(suite)
        after = source_snapshot(args.expected_head, manifest)
        records["source_after"] = save(evidence / "source-after.json", after)
        records["loaded_outer_after"] = save(evidence / "loaded-outer-after.json", loaded_sources(after))
        require(before == after, "Physical/Git source changed during the new controls")
        require(result.wasSuccessful() and result.testsRun == len(METHODS), "One or both new controls failed")
        require([row["event"] for row in events] == ["START", "PASS", "START", "PASS"],
                "Unexpected original named outcomes")
        for mode in ("success", "refusals"):
            value = json.loads((child_output / ("real-origin-" + mode + ".stdout.json")).read_bytes())
            command = json.loads((child_output / ("real-origin-" + mode + ".command.json")).read_bytes())
            require(value["status"] == "PASS_NEW_SOURCE_ORIGIN_CONTROL"
                    and command["return_code"] == 0 and command["owned_group_absent"] is True,
                    "Actual child origin/cleanup proof failed")
        require(shutil.disk_usage(ROOT).free >= 2_500_000_000, "Capacity reserve crossed")
    except BaseException as error:
        outer_failure = {"type": type(error).__name__, "message": str(error)}
        with (evidence / "runner-error.log").open("x") as log:
            traceback.print_exc(file=log)
    finally:
        records["events"] = save(evidence / "events.json", events)
        receipt = {
            "protocol": "page-source-origin-two-control-execution-v1",
            "status": "PASS" if outer_failure is None else "FAIL",
            "frozen_head": args.expected_head, "manifest_sha256": digest(MANIFEST.read_bytes()),
            "reader_sha256": digest(Path(__file__).read_bytes()),
            "methods": list(METHODS), "tests_run": None if result is None else result.testsRun,
            "actual_named_passes": sum(row["event"] == "PASS" for row in events),
            "outer_failure": outer_failure, "records": records,
            "original_child_directory": str(child_output),
            "seconds": time.monotonic() - started,
            "older_controller_methods": 0, "product_methods": 0, "new_builds": 0,
            "actual_apple_source_acceptance": False,
        }
        record = save(evidence / "receipt.json", receipt)
        for path in evidence.rglob("*"):
            if path.is_file():
                path.chmod(0o400)
        print(json.dumps({"receipt": record, "status": receipt["status"],
                          "tests_run": receipt["tests_run"], "actual_named_passes": receipt["actual_named_passes"],
                          "outer_failure": outer_failure}, sort_keys=True))
    return 0 if outer_failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
