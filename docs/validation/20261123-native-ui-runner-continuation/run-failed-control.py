#!/usr/bin/env python3
"""Only the previously failed retained-runner control; first PASS is retained."""
from __future__ import annotations
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

PROTOCOL = "pinkha-native-ui-retained-runner-failed-control-v1"
NAMESPACE = "docs/validation/20261123-native-ui-runner-continuation"
MANIFEST_REL = NAMESPACE + "/failed-control-inputs.json"
WRAPPER_REL = NAMESPACE + "/run-failed-control.py"
TEST_REL = "Tools/AnyEnginePort/test_native_ui_runner_reuse.py"
TEST_MODULE = "test_native_ui_runner_reuse"
DECLARED_METHODS = (
    "test_actual_descriptor_mode_app_dependency_and_exact_field_refusals",
    "test_original_runner_restore_origin_ledger_and_zero_build_separation",
)
METHODS = ("test_original_runner_restore_origin_ledger_and_zero_build_separation",)
MIN_FREE = 2_500_000_000
START_FREE = 2_520_000_000
OUTPUT_LIMIT = 16 * 1024**2
MAX_INPUT = 4 * 1024**2

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stamp():
    return datetime.now(timezone.utc).isoformat()

def raw_file(path, maximum=MAX_INPUT):
    observed = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(observed.st_mode)
            and observed.st_nlink == 1 and 0 <= observed.st_size <= maximum,
            "regular_bounded_single_link_input_required:" + str(path))
    raw = path.read_bytes()
    require(len(raw) == observed.st_size, "input_changed_while_reading:" + str(path))
    return raw, observed

def write(path, raw):
    require(not path.exists(), "exclusive_original_output_required:" + str(path))
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)

def write_json(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())

def capacity(root, output=None, *, start=False):
    free = shutil.disk_usage(root).free
    require(free >= (START_FREE if start else MIN_FREE), "capacity_reserve_not_available")
    if output is not None:
        allocated = sum(p.lstat().st_size for p in output.rglob("*") if p.is_file())
        require(allocated <= OUTPUT_LIMIT, "control_output_budget_exceeded")
    return {"observedAt": stamp(), "freeBytes": free, "reserveBytes": MIN_FREE}

def git(root, argv, payload=None):
    return subprocess.check_output(["git", "-C", str(root), *argv], input=payload, timeout=30)

def source_rows(root, source, manifest):
    rows = manifest["inputs"]
    require(len({x["path"] for x in rows}) == len(rows), "duplicate_control_input")
    paths = [x["path"] for x in rows]
    require(all(isinstance(x, str) and x and not x.startswith("/") and
                all(y not in {".", ".."} for y in x.split("/")) and
                not any(y in x for y in ("\n", "\r", "\0", ":")) for x in paths),
            "unsafe_control_input")
    require(git(root, ["rev-parse", "HEAD"]).decode().strip() == source, "frozen_head_changed")
    require(not git(root, ["status", "--porcelain", "--untracked-files=no"]).strip(),
            "tracked_source_not_clean")
    tree = git(root, ["ls-tree", "-r", "--full-tree", "-z", source, "--", *paths])
    metadata = {}
    for item in tree.split(b"\0"):
        if not item:
            continue
        header, relative = item.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        require(kind == "blob" and mode in {"100644", "100755"}, "source_git_mode_not_regular")
        metadata[relative.decode()] = {"gitMode": mode, "gitBlob": oid}
    require(set(metadata) == set(paths), "frozen_git_input_set_mismatch")
    request = b"".join((source + ":" + path + "\n").encode() for path in paths)
    raw = git(root, ["cat-file", "--batch"], request)
    position = 0
    observed = {}
    for expected in rows:
        relative = expected["path"]
        line_end = raw.index(b"\n", position)
        oid, kind, size_raw = raw[position:line_end].decode().split()
        size = int(size_raw)
        require(kind == "blob" and 0 <= size <= MAX_INPUT, "bounded_git_blob_required")
        position = line_end + 1
        blob = raw[position:position + size]
        position += size
        require(raw[position:position + 1] == b"\n", "git_blob_frame_changed")
        position += 1
        physical, info = raw_file(root / relative)
        require(physical == blob and len(physical) == expected["bytes"]
                and sha(physical) == expected["sha256"]
                and stat.S_IMODE(info.st_mode) == expected["physicalMode"]
                and metadata[relative]["gitMode"] == expected["gitMode"]
                and oid == metadata[relative]["gitBlob"],
                "fixed_physical_git_input_mismatch:" + relative)
        observed[relative] = {
            "bytes": len(physical), "sha256": sha(physical),
            "physicalMode": stat.S_IMODE(info.st_mode),
            **metadata[relative], "inode": str(info.st_ino), "uid": info.st_uid,
        }
    require(position == len(raw), "extra_git_blob_output")
    return observed

def loaded_sources(root, fixed_rows):
    admitted = {x["path"]: x for x in fixed_rows if x["path"].endswith(".py")}
    names = {}
    for relative in admitted:
        names.setdefault(Path(relative).stem, set()).add(relative)
    observed = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not isinstance(filename, str) or not filename.endswith(".py"):
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            relative = path.relative_to(root).as_posix()
            require(relative in admitted, "unbound_loaded_repository_module:" + relative)
            require(not path.name.startswith("test_") or relative == TEST_REL,
                    "old_test_module_loaded:" + relative)
            data, info = raw_file(path)
            row = admitted[relative]
            require(sha(data) == row["sha256"] and len(data) == row["bytes"]
                    and stat.S_IMODE(info.st_mode) == row["physicalMode"],
                    "loaded_repository_source_changed:" + relative)
            observed[name] = {"path": relative, "sha256": sha(data), "bytes": len(data)}
        elif name != "__main__" and name.rsplit(".", 1)[-1] in names:
            raise RuntimeError("foreign_repository_module_origin:" + name + ":" + str(path))
    return observed

def method_guard(root):
    def guard(frame, event, arg):
        if event == "call":
            name = frame.f_code.co_name
            filename = Path(frame.f_code.co_filename)
            if name.startswith("test_") and filename.is_absolute() and filename.resolve().is_relative_to(root):
                relative = filename.resolve().relative_to(root).as_posix()
                require(relative == TEST_REL and name in METHODS, "unapproved_test_body:" + relative + ":" + name)
        return guard
    return guard

class OriginalResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, root, output, events):
        super().__init__(stream, descriptions, verbosity)
        self.root, self.output, self.events = root, output, events

    def event(self, outcome, test, **extra):
        value = {"at": stamp(), "outcome": outcome, "test": test.id(), **extra}
        self.events.append(value)
        with (self.output / "events.jsonl").open("ab") as stream:
            stream.write((json.dumps(value, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())

    def startTest(self, test):
        capacity(self.root, self.output)
        super().startTest(test)
        self.event("START", test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.event("PASS", test)

    def addError(self, test, err):
        super().addError(test, err)
        self.event("ERROR", test, exception=type(err[1]).__name__, message=str(err[1]))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.event("FAIL", test, exception=type(err[1]).__name__, message=str(err[1]))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.event("SKIP", test, reason=reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.event("SUBCASE_PASS" if err is None else "SUBCASE_FAIL", test,
                   subcase=str(subtest), exception=None if err is None else type(err[1]).__name__,
                   message=None if err is None else str(err[1]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output).absolute()
    require(len(args.source) == 40 and all(c in "0123456789abcdef" for c in args.source),
            "full_frozen_source_required")
    require(output.resolve() == output and not output.exists() and
            not output.is_relative_to(root) and output.parent.is_dir(),
            "fresh_outside_repository_output_required")
    initial_capacity = capacity(root, start=True)
    manifest_raw, _ = raw_file(root / MANIFEST_REL)
    require(manifest_raw == git(root, ["show", args.source + ":" + MANIFEST_REL]),
            "manifest_not_frozen_git_bytes")
    manifest = json.loads(manifest_raw)
    require(manifest["protocol"] == PROTOCOL and manifest["methods"] == list(METHODS)
            and manifest["testPath"] == TEST_REL and manifest["oldMethodsToExecute"] == 0
            and manifest["productTestsToExecute"] == 0 and manifest["buildsToExecute"] == 0,
            "exact_new_control_scope_required")
    wrapper_raw, _ = raw_file(Path(__file__).resolve())
    require(wrapper_raw == git(root, ["show", args.source + ":" + WRAPPER_REL]),
            "outside_wrapper_differs_from_frozen_original")
    before = source_rows(root, args.source, manifest)
    output.mkdir(mode=0o700)
    write_json(output / "invocation.json", {
        "protocol": PROTOCOL, "source": args.source, "root": str(root),
        "outsideWrapper": str(Path(__file__).resolve()), "wrapperSHA256": sha(wrapper_raw),
        "manifestSHA256": sha(manifest_raw), "methods": list(METHODS),
        "initialCapacity": initial_capacity, "productTests": 0, "oldMethods": 0, "builds": 0,
        "syntheticBoundaries": manifest["syntheticBoundaries"],
    })
    write_json(output / "source-before.json", before)
    temporary = output / "temporary-controls"
    temporary.mkdir(mode=0o700)
    tempfile.tempdir = str(temporary)
    os.environ["TMPDIR"] = str(temporary)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root / "Tools/AnyEnginePort"), str(root / "Tools/PinkhaSimulatorGate"),
                   str(root / "Tools/Hanlin")]
    result = None
    events, failure, before_loaded, after_loaded, after = [], None, None, None, None
    started = time.monotonic()
    original_profile = sys.getprofile()
    try:
        reuse = importlib.import_module("native_ui_runner_reuse")
        reuse.preload()
        importlib.import_module("native_ui_runner_continuation")
        importlib.import_module("hanlin_fixture_ci")
        before_loaded = loaded_sources(root, manifest["inputs"])
        require(TEST_MODULE not in before_loaded, "new_test_loaded_before_baseline")
        write_json(output / "loaded-before.json", before_loaded)
        sys.setprofile(method_guard(root))
        module = importlib.import_module(TEST_MODULE)
        actual = [name for name in vars(module.RetainedRunnerControls) if name.startswith("test_")]
        require(set(actual) == set(DECLARED_METHODS) and len(actual) == 2, "unchanged_two_declarations_required")
        suite = unittest.TestSuite(module.RetainedRunnerControls(name) for name in METHODS)
        with (output / "original-tests.log").open("x", encoding="utf-8") as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                result = unittest.TextTestRunner(
                    stream=stream, verbosity=2,
                    resultclass=lambda s, d, v: OriginalResult(s, d, v, root, output, events),
                ).run(suite)
            stream.flush()
            os.fsync(stream.fileno())
        require(result.testsRun == 1 and not result.skipped and result.wasSuccessful(),
                "new_controls_not_all_successful")
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error),
                   "traceback": traceback.format_exc()}
    finally:
        sys.setprofile(original_profile)
        for name, callable_ in (
            ("loaded-after", lambda: loaded_sources(root, manifest["inputs"])),
            ("source-after", lambda: source_rows(root, args.source, manifest)),
        ):
            try:
                value = callable_()
                write_json(output / (name + ".json"), value)
                if name == "loaded-after":
                    after_loaded = value
                else:
                    after = value
            except BaseException as error:
                record = {"phase": name, "type": type(error).__name__, "message": str(error),
                          "traceback": traceback.format_exc()}
                write_json(output / (name + "-failure.json"), record)
                if failure is None:
                    failure = record
        try:
            require(after == before, "physical_git_source_changed_during_controls")
            require(before_loaded is not None and after_loaded is not None and
                    all(after_loaded.get(k) == v for k, v in before_loaded.items()),
                    "preloaded_repository_module_changed")
            added = {k: v for k, v in after_loaded.items() if k not in before_loaded}
            require(set(added) == {TEST_MODULE} and added[TEST_MODULE]["path"] == TEST_REL,
                    "unexpected_late_repository_import")
            final_capacity = capacity(root, output)
        except BaseException as error:
            final_capacity = {"observedAt": stamp(), "freeBytes": shutil.disk_usage(root).free}
            if failure is None:
                failure = {"phase": "final_admission", "type": type(error).__name__,
                           "message": str(error), "traceback": traceback.format_exc()}
        evidence = {
            "protocol": PROTOCOL, "source": args.source, "status": "PASS" if failure is None else "FAIL",
            "failure": failure, "elapsedSeconds": time.monotonic() - started,
            "actualMethodsStarted": [x["test"] for x in events if x["outcome"] == "START"],
            "actualMethodsPassed": [x["test"] for x in events if x["outcome"] == "PASS"],
            "actualSubcasesPassed": sum(x["outcome"] == "SUBCASE_PASS" for x in events),
            "actualSubcasesFailed": sum(x["outcome"] == "SUBCASE_FAIL" for x in events),
            "testResult": None if result is None else {
                "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                "skips": len(result.skipped), "wasSuccessful": result.wasSuccessful()},
            "sourceInputs": len(before), "sourceUnchanged": after == before,
            "loadedBefore": None if before_loaded is None else len(before_loaded),
            "loadedAfter": None if after_loaded is None else len(after_loaded),
            "finalCapacity": final_capacity,
            "oldMethods": 0, "productTests": 0, "builds": 0,
            "claim": "Offline new controller controls only; no Mac execution, App acceptance, or original failure relabelling",
        }
        write_json(output / "receipt.json", evidence)
        originals = {}
        for path in sorted(output.iterdir()):
            if path.is_file():
                raw = path.read_bytes()
                originals[path.name] = {"bytes": len(raw), "sha256": sha(raw)}
        write_json(output / "original-files.json", originals)
        print(json.dumps(evidence, sort_keys=True))
    return 0 if failure is None else 1

if __name__ == "__main__":
    raise SystemExit(main())
