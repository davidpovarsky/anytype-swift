#!/usr/bin/env python3
"""One finite resource-admission window; at most one unchanged source graph."""
import hashlib
import json
import os
import pathlib
import selectors
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-resource-admission-20261123")
ATTEMPT = ROOT / "attempt1"
GRAPH = pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123/Tools/AnyEngineValidation/loaded_account_witness/graph.py")
CONTROL_SHA = "cd3f430633d9331ecad49230e0a20082f8f9e8b0"
GRAPH_SHA = "6aacb0c911aed49d88d9f0e7ef82b08a5ceab431139bb7b71f17c7d0aedfd23d"
REFUSAL_SHA = "b8f665bf6136a8dfd578ee50e02ee0d6220aebb1fc0c9a7f2d3ee2f0e155e0c5"
GRAPH_RESULT = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/graph-attempt1/result.json")
WAIT_SECONDS = 120
CHILD_SECONDS = 600
START_FREE = 2_650_000_000
METADATA_START = 1_073_741_824
RAW_LIMIT = 256 * 1024

def require(value, message):
    if not value:
        raise RuntimeError(message)

def now():
    return datetime.now(timezone.utc).isoformat()

def free():
    return shutil.disk_usage("/mnt/development").free

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def graph_source():
    before = GRAPH.lstat()
    require(GRAPH.is_file() and not GRAPH.is_symlink(), "pinned_graph_file_type")
    raw = GRAPH.read_bytes()
    after = GRAPH.lstat()
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
              "st_size", "st_mtime_ns", "st_ctime_ns")
    require(all(getattr(before, k) == getattr(after, k) for k in fields), "pinned_graph_changed_during_read")
    require(sha(raw) == GRAPH_SHA, "pinned_graph_hash")
    return {"path": str(GRAPH), "sha256": GRAPH_SHA,
            **{k: str(getattr(after, k)) for k in fields}}

def absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True

def stop_owned(child, record):
    require(record.get("pid") == child.pid == record.get("pgid"), "owned_supervisor_child_binding")
    child.poll()
    record["cleanup_initial_group_absent"] = absent(child.pid)
    if record["cleanup_initial_group_absent"]:
        return
    # The graph's own SIGTERM handler must have time to complete its three
    # bounded Docker observations/kill before this final transport backstop.
    for name, sig, seconds in (("term", signal.SIGTERM, 90), ("kill", signal.SIGKILL, 5)):
        try:
            os.killpg(child.pid, sig)
            record[name + "_sent"] = True
        except ProcessLookupError:
            record[name + "_sent"] = False
        deadline = time.monotonic() + seconds
        while True:
            child.poll()
            gone = absent(child.pid)
            if gone or time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        record["group_absent_after_" + name] = gone
        if gone:
            return
    require(gone, "owned_graph_group_survived")

def write_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    require(len(raw) <= 256 * 1024, "operational_json_bound")
    with path.open("xb") as target:
        os.chmod(path, 0o600)
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}

def interrupt(signum, _frame):
    raise InterruptedError("resource_supervisor_signal_" + str(signum))

def main():
    require(os.getuid() == 1001, "expected_oracle_owner")
    available = free()
    require(available >= METADATA_START, "metadata_preservation_start_reserve")
    require(not ATTEMPT.exists() and not GRAPH_RESULT.parent.exists(), "preserve_all_prior_attempts")
    source_before = graph_source()
    original = ROOT / "original-prelaunch-refusal.json"
    require(original.is_file() and not original.is_symlink() and original.stat().st_size < 64 * 1024,
            "original_prelaunch_refusal_required")
    require(sha(original.read_bytes()) == REFUSAL_SHA, "original_prelaunch_refusal_hash")
    os.umask(0o077)
    ATTEMPT.mkdir(mode=0o700)
    record = {
        "protocol": "loaded-account-resource-admission-v1", "started": now(),
        "status": "NOT_RUN", "primary_error": None, "final_errors": [],
        "expected_controller_sha": CONTROL_SHA, "graph_source_before": source_before,
        "supervisor_source_sha256": sha(pathlib.Path(__file__).read_bytes()),
        "original_prelaunch_refusal_sha256": sha(original.read_bytes()),
        "wait_budget_seconds": WAIT_SECONDS, "sample_interval_seconds": 2,
        "graph_query_budget_seconds_unchanged": 120,
        "graph_stop_free_bytes_unchanged": 2_600_000_000,
        "graph_metadata_limit_bytes_unchanged": 16 * 1024 * 1024,
        "launch_count": 0, "observations": [], "native_builds": 0, "native_methods": 0,
    }
    child = None
    selector = selectors.DefaultSelector()
    streams, outputs = {}, {}
    sizes = {"stdout": 0, "stderr": 0}
    source_after = None
    try:
        began = time.monotonic()
        while True:
            elapsed, available = time.monotonic() - began, free()
            record["observations"].append({"elapsed_seconds": elapsed, "free_bytes": str(available), "at": now()})
            require(len(record["observations"]) <= 62, "bounded_resource_observations")
            if elapsed <= WAIT_SECONDS and available >= START_FREE:
                record["resource_admitted"] = True
                break
            if elapsed >= WAIT_SECONDS:
                record["resource_admitted"] = False
                record["reason"] = "resource_window_expired"
                break
            time.sleep(min(2, WAIT_SECONDS - elapsed))
        if record["resource_admitted"]:
            require(graph_source() == source_before, "graph_changed_during_resource_wait")
            argv = [sys.executable, "-B", str(GRAPH), "--expected-controller-sha", CONTROL_SHA, "--execute"]
            record["argv"] = argv
            for name in sizes:
                outputs[name] = (ATTEMPT / (name + ".log")).open("xb")
                os.chmod(ATTEMPT / (name + ".log"), 0o600)
            start = time.monotonic()
            child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            record.update(launch_count=1, pid=child.pid, pgid=os.getpgid(child.pid), launched_at=now())
            require(record["pgid"] == child.pid, "owned_graph_process_group")
            for name, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
                streams[name] = stream
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                require(time.monotonic() - start < CHILD_SECONDS, "graph_transport_timeout")
                for key, _event in selector.select(0.25):
                    name = key.data
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        record[name + "_complete"] = True
                        continue
                    remain = RAW_LIMIT - sizes[name]
                    outputs[name].write(chunk[:max(0, remain)])
                    sizes[name] += min(len(chunk), max(0, remain))
                    require(len(chunk) <= remain, "graph_transport_output_bound")
            record["returncode"] = child.wait(timeout=max(0.001, CHILD_SECONDS - (time.monotonic() - start)))
            record["child_elapsed_seconds"] = time.monotonic() - start
            require(record["child_elapsed_seconds"] < CHILD_SECONDS, "graph_transport_late_exit")
            if record["returncode"] != 0:
                record["primary_error"] = {"type": "ChildProcessError", "code": "original_graph_nonzero",
                                           "returncode": record["returncode"]}
            record["status"] = "GRAPH_RETURNED"
    except BaseException as error:
        if record["primary_error"] is None:
            record["primary_error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if child is not None:
            try:
                stop_owned(child, record)
                record["returncode"] = child.wait(timeout=5)
                record["owned_group_absent"] = absent(child.pid)
                require(record["owned_group_absent"], "owned_graph_group_remaining")
            except BaseException as error:
                record["final_errors"].append({"phase": "graph-group-cleanup", "type": type(error).__name__,
                                               "message": str(error)})
        selector.close()
        for stream in streams.values():
            stream.close()
        for name, output in outputs.items():
            output.flush()
            os.fsync(output.fileno())
            output.close()
            path = ATTEMPT / (name + ".log")
            raw = path.read_bytes()
            record[name + "_original"] = {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}
        try:
            source_after = graph_source()
            require(source_after == source_before, "pinned_graph_final_integrity")
            record["graph_source_after"] = source_after
        except BaseException as error:
            record["final_errors"].append({"phase": "source-integrity", "type": type(error).__name__,
                                           "message": str(error)})
        if GRAPH_RESULT.exists():
            try:
                require(GRAPH_RESULT.is_file() and not GRAPH_RESULT.is_symlink() and
                        GRAPH_RESULT.stat().st_size <= 512 * 1024, "original_graph_result_shape")
                raw = GRAPH_RESULT.read_bytes()
                value = json.loads(raw)
                require(value.get("expected_controller_sha") == CONTROL_SHA, "original_graph_controller_binding")
                record["original_graph_result"] = {"path": str(GRAPH_RESULT), "bytes": len(raw),
                                                  "sha256": sha(raw), "status": value.get("status")}
            except BaseException as error:
                record["final_errors"].append({"phase": "original-graph-result", "type": type(error).__name__,
                                               "message": str(error)})
        else:
            record["original_graph_result"] = {"state": "NOT_CREATED"}
        if record["launch_count"] == 1:
            success = (record.get("returncode") == 0 and record.get("owned_group_absent") is True and
                       record["original_graph_result"].get("status") == "PASS_SOURCE_ONLY_GRAPH" and
                       record["primary_error"] is None and not record["final_errors"])
            record["status"] = "PASS_SOURCE_ONLY_GRAPH" if success else "FAILED_ORIGINAL_GRAPH"
        elif record["primary_error"] is not None or record["final_errors"]:
            record["status"] = "NOT_RUN_SUPERVISOR_FAILED"
        record.update(finished=now(), free_final=str(free()))
        receipt = write_json(ATTEMPT / "result.json", record)
        print(json.dumps({"status": record["status"], "launch_count": record["launch_count"], "receipt": receipt,
                          "graph_result": record["original_graph_result"], "free_final": record["free_final"]}))
    return 0 if record["status"] in ("PASS_SOURCE_ONLY_GRAPH", "NOT_RUN") else 1

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    sys.exit(main())
