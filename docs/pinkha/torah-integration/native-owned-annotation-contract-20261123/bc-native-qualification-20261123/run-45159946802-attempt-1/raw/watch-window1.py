#!/usr/bin/env python3
"""One bounded read-only observer for one immutable original native archive run."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
BINDING_SHA256 = "f81fe88859ad80dda74ea2c739ad2d62914448fa05c652affae735b70f9c0566"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(name, value):
    target = ROOT / name
    temporary = target.with_name(target.name + ".tmp")
    with temporary.open("w") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def event(value):
    with (ROOT / "WATCH_EVENTS_1.jsonl").open("a") as stream:
        stream.write(json.dumps(dict(utc=now(), **value), sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def check(run, binding):
    expected = {
        "id": binding["run_id"], "head_sha": binding["head_sha"],
        "head_branch": binding["head_branch"], "run_attempt": 1,
        "event": "push", "path": binding["workflow_path"],
        "workflow_id": binding["workflow_id"],
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Run/source/attempt/event/workflow identity changed")
    if run.get("repository", {}).get("full_name") != binding["repository"]:
        raise RuntimeError("Run repository differs")


def main():
    raw = (ROOT / "WATCH_BINDING.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != BINDING_SHA256:
        raise RuntimeError("Observer binding changed")
    binding = json.loads(raw)
    lock = (ROOT / "observer.lock").open("a+")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    record = {
        "run_id": binding["run_id"], "head_sha": binding["head_sha"],
        "run_attempt": 1, "event": "push", "window": 1, "sole_watcher": True,
        "minimum_api_interval_seconds": 120, "bounded_window_seconds": 3300,
        "started_utc": now(), "pid": os.getpid(), "state": "WATCHING",
        "lock_acquired": True, "lock_released": False,
    }
    deadline = time.monotonic() + 3300
    last_query = binding["discovery_observed_unix"]
    result_code = 0
    write("WATCH_OWNER_1.json", record)
    event({"state": "STARTED", "run_id": binding["run_id"], "head_sha": binding["head_sha"]})
    try:
        while time.monotonic() < deadline:
            remaining_interval = max(0, last_query + 120 - time.time())
            remaining_window = max(0, deadline - time.monotonic())
            if remaining_interval:
                time.sleep(min(remaining_interval, remaining_window))
            if time.monotonic() >= deadline:
                break
            started = time.time()
            response = subprocess.run([
                "gh", "api", "repos/" + binding["repository"] + "/actions/runs/" + str(binding["run_id"]),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=35)
            last_query = started
            if response.returncode:
                write("OBSERVATION_ERROR_1.json", {
                    "utc": now(), "returncode": response.returncode,
                    "stderr": response.stderr.decode(errors="replace"),
                    "runtime_failure_inferred": False,
                })
                raise RuntimeError("GitHub metadata observation failed; no CI result inferred")
            run = json.loads(response.stdout)
            check(run, binding)
            write("RUN.json", run)
            observed = {key: run.get(key) for key in
                        ("id", "head_sha", "head_branch", "run_attempt", "event",
                         "status", "conclusion", "html_url", "updated_at")}
            record["observed_run"] = observed
            event({"state": "OBSERVED", "run": observed})
            if run["status"] == "completed":
                if not isinstance(run.get("conclusion"), str) or not run["conclusion"]:
                    raise RuntimeError("Completed run has no explicit observed conclusion")
                record["state"] = "TERMINAL_OBSERVED"
                break
        else:
            record["state"] = "WINDOW_ENDED"
        if record["state"] == "WATCHING":
            record["state"] = "WINDOW_ENDED"
    except BaseException as error:
        result_code = 1
        record.update(state="OBSERVATION_ERROR", error_type=type(error).__name__, error=str(error),
                      runtime_failure_inferred=False)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
        record.update(finished_utc=now(), watch_exit_code=result_code, lock_released=True)
        write("WATCH_RESULT_1.json", record)
    print(json.dumps(record, sort_keys=True), flush=True)
    return result_code


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Observer interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
