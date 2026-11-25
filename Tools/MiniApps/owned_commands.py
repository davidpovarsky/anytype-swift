"""Run one owned native build/test command and retain its complete exit/drain proof."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def drain(process):
    for signum in (signal.SIGTERM, signal.SIGKILL):
        if not group_exists(process.pid):
            return True
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            return True
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            process.poll()
            if not group_exists(process.pid):
                return True
            time.sleep(0.05)
    return not group_exists(process.pid)


def run_logged(arguments, cwd, log, timeout):
    log = Path(log)
    if timeout <= 0 or log.exists():
        raise ValueError("A fresh command log and positive deadline are required")
    record = {"schema": "miniapps.owned-native-command/1", "arguments": list(map(str, arguments)),
              "cwd": str(cwd), "timeout_seconds": timeout,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "timed_out": False, "returncode": None, "owned_group_drained": False}
    process = None
    try:
        with log.open("xb") as stream:
            process = subprocess.Popen(arguments, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record["pid"] = record["process_group_id"] = process.pid
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                raise
    finally:
        if process is not None:
            record["owned_group_drained"] = drain(process)
            record["returncode"] = process.poll()
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        if log.is_file():
            with log.open("rb") as stream:
                record["log_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        with log.with_suffix(".command.json").open("x") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    if not record["owned_group_drained"]:
        raise RuntimeError("Owned native command group did not drain")
    return subprocess.CompletedProcess(arguments, record["returncode"])
