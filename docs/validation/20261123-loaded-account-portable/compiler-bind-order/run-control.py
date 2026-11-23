#!/usr/bin/env python3
"""One frozen, original-data-only compiler bind-order control."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import resource
import signal
import stat
import subprocess
import sys
import time
import traceback
import unittest

ROOT = pathlib.Path("/run/anytapy-wave15-source-overlay-20261123/native")
OUT = ROOT.parent / "compiler-bind-order-attempt1"
HERE = ROOT / "docs/validation/20261123-loaded-account-portable/compiler-bind-order"
INPUTS = HERE / "control-inputs.json"
METHOD = "test_original_docker_bind_order_accepts_only_exact_owned_multiset"
TEST = "Tools/AnyEngineValidation/loaded_account_witness/portable/test_compiler_bind_order.py"
PRODUCTION = "Tools/AnyEngineValidation/loaded_account_witness/portable/compiler_producer.py"
MIB = 1024 ** 2
GIB = 1024 ** 3
START = time.monotonic()
COMMANDS = []

def require(value, name):
    if not value:
        raise RuntimeError(name)

def save(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    require(len(data) <= MIB, "receipt_limit")
    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def resources():
    available = int(next(line.split()[1] for line in pathlib.Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))) * 1024
    require(available >= 2 * GIB, "ram_memory_floor")
    own = sum(p.lstat().st_blocks * 512 for p in ROOT.rglob("*") if p.is_file())
    require(own <= 8 * MIB, "writer_allocation_limit")
    usage = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) if OUT.exists() else 0
    require(usage <= 2 * MIB, "evidence_limit")
    require(time.monotonic() - START < 60, "total_deadline")
    return {"memory_available": available, "writer_allocated_bytes": own, "evidence_bytes": usage}

def absent(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return True
    return False

def stop(child):
    actions = []
    for sig, seconds in ((signal.SIGTERM, 2), (signal.SIGKILL, 2)):
        if absent(child.pid):
            child.wait(timeout=2)
            return {"absent": True, "actions": actions}
        os.killpg(child.pid, sig)
        actions.append(int(sig))
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            child.poll()
            if absent(child.pid):
                child.wait(timeout=2)
                return {"absent": True, "actions": actions}
            time.sleep(0.05)
    raise RuntimeError("owned_git_group_not_absent")

def git(name, args):
    row = {"name": name, "argv": ["/usr/bin/git", "-c", "core.packedGitWindowSize=16m",
                                 "-c", "core.packedGitLimit=64m", "-C", str(ROOT)] + args,
           "primary_error": None, "cleanup_error": None, "persistence_errors": []}
    COMMANDS.append(row)
    stdout = OUT / (name + ".stdout")
    stderr = OUT / (name + ".stderr")
    child = None
    error = None
    fo = fe = None
    started = time.monotonic()
    try:
        fo = stdout.open("xb")
        fe = stderr.open("xb")
        child = subprocess.Popen(row["argv"], stdout=fo, stderr=fe, stdin=subprocess.DEVNULL,
                                 env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
                                 start_new_session=True)
        row.update(pid=child.pid, pgid=os.getpgid(child.pid))
        require(row["pid"] == row["pgid"], "owned_git_group")
        while child.poll() is None:
            require(time.monotonic() - started < 12, "git_deadline")
            require(stdout.stat().st_size <= MIB and stderr.stat().st_size <= 65536, "git_output_limit")
            resources()
            time.sleep(0.05)
        row["returncode"] = child.returncode
        require(time.monotonic() - started < 12, "git_completed_late")
        resources()
        require(child.returncode == 0, "git_nonzero")
    except BaseException as exc:
        error = exc
        row["primary_error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if child is not None:
            try:
                row["cleanup"] = stop(child)
            except BaseException as exc:
                row["cleanup_error"] = {"type": type(exc).__name__, "message": str(exc)}
                if error is None:
                    error = exc
        for stream in (fo, fe):
            if stream is not None:
                for operation in (stream.flush, lambda s=stream: os.fsync(s.fileno()), stream.close):
                    try:
                        operation()
                    except BaseException as exc:
                        row["persistence_errors"].append({"type": type(exc).__name__, "message": str(exc)})
                        if error is None:
                            error = exc
        row["elapsed_seconds"] = time.monotonic() - started
    if error is not None:
        raise error
    require(stdout.stat().st_size <= MIB and stderr.stat().st_size <= 65536, "git_final_output_limit")
    return stdout.read_bytes()

def physical(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
        a = os.fstat(f.fileno())
        require(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= MIB, "source_file_shape")
        body = f.read(MIB + 1)
        b = os.fstat(f.fileno())
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    before = {k: str(getattr(a, k)) for k in fields}
    require(before == {k: str(getattr(b, k)) for k in fields}, "source_changed_during_read")
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest(),
            "physical": before}

def snapshot(phase, manifest, expected):
    require(git(phase + "-head", ["rev-parse", "HEAD"]).decode().strip() == expected, "frozen_head")
    require(git(phase + "-status", ["status", "--porcelain=v1", "--untracked-files=all"]) == b"", "clean_source")
    paths = sorted(set(manifest["inputs"]) | {INPUTS.relative_to(ROOT).as_posix()})
    listing = git(phase + "-index", ["ls-files", "--stage", "-z", "--"] + paths)
    entries = {}
    for item in listing.rstrip(b"\0").split(b"\0"):
        metadata, name = item.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        key = name.decode()
        require(key not in entries and stage == "0" and mode == "100644", "git_source_stage")
        entries[key] = oid
    require(set(entries) == set(paths), "complete_git_input_set")
    rows = {}
    for rel in paths:
        value = physical(ROOT / rel)
        require(value["git_blob"] == entries[rel], "physical_git_blob")
        if rel in manifest["inputs"]:
            pin = manifest["inputs"][rel]
            require(value["bytes"] == pin["bytes"] and value["sha256"] == pin["sha256"], "fixed_input_hash")
            require(value["physical"]["st_mode"] == pin["physical_mode"], "fixed_input_mode")
        rows[rel] = value
    return rows

def loaded():
    expected = {"__main__": pathlib.Path(__file__).resolve(),
                "compiler_bind_order_control": ROOT / TEST, "compiler_bind_order_subject": ROOT / PRODUCTION}
    rows = {}
    for name, module in list(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if value and pathlib.Path(value).resolve().is_relative_to(ROOT):
            path = pathlib.Path(value).resolve()
            require(name in expected and path == expected[name], "unexpected_loaded_repository_source")
            rows[name] = physical(path)
    require(set(rows) == set(expected), "loaded_source_incomplete")
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-manifest", required=True)
    args = parser.parse_args()
    require(os.getuid() == os.geteuid() == 1001, "ordinary_uid")
    require(pathlib.Path(__file__).resolve() == HERE / "run-control.py", "fixed_wrapper")
    resource.setrlimit(resource.RLIMIT_AS, (512 * MIB, 512 * MIB))
    os.umask(0o077)
    resources()
    OUT.mkdir(mode=0o700)
    body = INPUTS.read_bytes()
    require(hashlib.sha256(body).hexdigest() == args.expected_manifest, "manifest_admission")
    manifest = json.loads(body)
    require(manifest["method"] == METHOD and manifest["native_tests"] == 0, "literal_scope")
    result = {"schema": "compiler-bind-order-one-new-control-v1", "status": "FAILED", "source_head": args.expected_head,
              "method": METHOD, "primary_error": None, "final_errors": [], "native_builds": 0,
              "native_tests": 0, "docker_invocations": 0, "old_controls_replayed": 0,
              "historical_producer_status": "FAILED", "historical_cleanup_status": "FAILED",
              "python_version": sys.version, "python_executable": sys.executable, "controller_pid": os.getpid()}
    events = []
    before = None
    old = {}
    try:
        def interrupt(sig, frame):
            raise RuntimeError("control_signal_%s" % sig)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM):
            old[sig] = signal.signal(sig, interrupt)
        signal.alarm(60)
        before = snapshot("before", manifest, args.expected_head)
        save(OUT / "source-before.json", before)
        spec = importlib.util.spec_from_file_location("compiler_bind_order_control", ROOT / TEST)
        test = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = test
        spec.loader.exec_module(test)
        result["loaded_before"] = loaded()
        class Results(unittest.TextTestResult):
            def startTest(self, value):
                events.append({"method": value.id(), "event": "START"})
                super().startTest(value)
            def addSuccess(self, value):
                events.append({"method": value.id(), "event": "PASS"})
                super().addSuccess(value)
            def addFailure(self, value, err):
                events.append({"method": value.id(), "event": "FAIL"})
                super().addFailure(value, err)
            def addError(self, value, err):
                events.append({"method": value.id(), "event": "ERROR"})
                super().addError(value, err)
        stream = io.StringIO()
        suite = unittest.TestSuite([test.CompilerBindOrderOriginalControl(METHOD)])
        actual = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Results).run(suite)
        text = stream.getvalue()
        require(len(text.encode()) <= 65536, "test_log_limit")
        (OUT / "control.log").write_text(text)
        result["actual_counts"] = {"run": actual.testsRun, "failures": len(actual.failures),
                                  "errors": len(actual.errors), "skipped": len(actual.skipped)}
        result["observations"] = test.CompilerBindOrderOriginalControl.observations
        require(actual.wasSuccessful() and actual.testsRun == 1 and not actual.skipped, "new_method_failed")
    except BaseException as exc:
        result["primary_error"] = {"type": type(exc).__name__, "message": str(exc)}
        try:
            (OUT / "controller-error.txt").write_text(traceback.format_exc())
        except BaseException as later:
            result["final_errors"].append({"phase": "error_log_persistence", "message": str(later)})
    finally:
        for label, operation in (("source_after", lambda: snapshot("after", manifest, args.expected_head)),
                                 ("loaded_after", loaded), ("resources_final", resources)):
            try:
                value = operation()
                result[label] = value
                if label == "source_after":
                    save(OUT / "source-after.json", value)
                    require(before is not None and value == before, "source_before_after")
                if label == "loaded_after":
                    require(value == result.get("loaded_before"), "loaded_before_after")
            except BaseException as exc:
                result["final_errors"].append({"phase": label, "type": type(exc).__name__, "message": str(exc)})
        try:
            signal.alarm(0)
        except BaseException as exc:
            result["final_errors"].append({"phase": "alarm_restore", "message": str(exc)})
        for sig, handler in old.items():
            try:
                signal.signal(sig, handler)
            except BaseException as exc:
                result["final_errors"].append({"phase": "handler_restore", "message": str(exc)})
        result["events"] = events
        result["commands"] = COMMANDS
        result["elapsed_seconds"] = time.monotonic() - START
        if result["primary_error"] is None and not result["final_errors"]:
            result["status"] = "PASS_ONE_NEW_CONTROL"
        try:
            save(OUT / "events.json", events)
            save(OUT / "result.json", result)
        except BaseException as exc:
            result["final_errors"].append({"phase": "final_persistence", "message": str(exc)})
            result["status"] = "FAILED"
    print(json.dumps({"status": result["status"], "output": str(OUT), "primary_error": result["primary_error"],
                      "final_errors": result["final_errors"], "events": events}, sort_keys=True))
    return 0 if result["status"] == "PASS_ONE_NEW_CONTROL" else 1

if __name__ == "__main__":
    raise SystemExit(main())
