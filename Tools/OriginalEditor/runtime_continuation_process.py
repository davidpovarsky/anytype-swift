"""Owned finite command lifecycle reused without changes from the reviewed native lane."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Commands:
    def __init__(self, evidence, env, deadline):
        self.evidence, self.env, self.deadline = evidence, env, deadline
        self.monotonic_deadline = time.monotonic() + max(0.0, deadline - time.time())
        self.items = []
        self.owned_groups_drained = True

    def persist(self):
        write_json(self.evidence / "COMMANDS.json", self.items)

    def cleanup_event(self, item, event, **values):
        item.setdefault("cleanup", []).append({"event": event, "unix": time.time(), **values})
        # Cleanup must still happen if receipt storage itself fails.
        try:
            self.persist()
        except Exception as error:
            item["receipt_error_type"] = type(error).__name__

    @staticmethod
    def group_exists(pgid):
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False

    def signal_group(self, item, sig):
        self.cleanup_event(item, "SIGNAL_REQUESTED", signal=int(sig))
        try:
            os.killpg(item["process_group_id"], sig)
            self.cleanup_event(item, "SIGNAL_SENT", signal=int(sig))
        except ProcessLookupError:
            self.cleanup_event(item, "GROUP_ALREADY_ABSENT", signal=int(sig))

    def drain(self, item, process, terminate):
        pgid = item["process_group_id"]
        if terminate:
            self.signal_group(item, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        # A parent that exits after TERM may leave an ignoring descendant.
        # Check the originally owned group even when that parent has exited.
        if self.group_exists(pgid):
            self.signal_group(item, signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.cleanup_event(item, "PARENT_REAP_TIMEOUT")
        deadline = time.monotonic() + 5
        while self.group_exists(pgid) and time.monotonic() < deadline:
            time.sleep(0.1)
        drained = not self.group_exists(pgid)
        self.cleanup_event(item, "OWNED_GROUP_DRAIN_RESULT", drained=drained)
        if not drained:
            self.owned_groups_drained = False
        return drained

    def run(self, label, argv, cwd, seconds):
        index = len(self.items) + 1
        stdout = self.evidence / f"{index:02d}-{label}.stdout"
        stderr = self.evidence / f"{index:02d}-{label}.stderr"
        started = time.time()
        effective_seconds = min(float(seconds), max(0.0, self.monotonic_deadline - time.monotonic()))
        item = {
            "label": label, "argv": [str(x) for x in argv], "cwd": str(cwd),
            "status": "STARTING", "started_unix": started, "pid": None,
            "process_group_id": None, "start_new_session": True,
            "requested_timeout_seconds": seconds, "effective_timeout_seconds": effective_seconds,
            "absolute_command_deadline_unix": self.deadline,
            "returncode": None, "effective_returncode": None, "timed_out": False,
            "stdout": stdout.name, "stderr": stderr.name, "cleanup": [],
        }
        self.items.append(item)
        self.persist()  # Actionable start intent exists before Popen.
        process = None
        try:
            with stdout.open("wb") as out, stderr.open("wb") as err:
                if effective_seconds <= 0:
                    item.update({"status": "REFUSED_GLOBAL_DEADLINE", "effective_returncode": 124, "budget_exhausted": True})
                else:
                    process = subprocess.Popen(argv, cwd=cwd, env=self.env, stdout=out, stderr=err, start_new_session=True)
                    # POSIX start_new_session creates this owned process group.
                    item.update({"status": "RUNNING", "pid": process.pid, "process_group_id": process.pid,
                                 "child_started_unix": time.time()})
                    self.persist()  # Persist ownership BEFORE awaiting the child.
                    try:
                        remaining = min(effective_seconds, max(0.0, self.monotonic_deadline - time.monotonic()))
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(argv, remaining)
                        code = process.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        item.update({"status": "TIMED_OUT", "timed_out": True})
                        self.persist()
                        self.drain(item, process, terminate=True)
                        code = process.returncode
                    else:
                        if self.group_exists(process.pid):
                            item["unexpected_owned_descendants"] = True
                            self.drain(item, process, terminate=False)
                        else:
                            self.cleanup_event(item, "OWNED_GROUP_ABSENT_AFTER_WAIT", drained=True)
                    effective_code = 124 if item["timed_out"] else (code if code is not None else 125)
                    if item.get("unexpected_owned_descendants") or not self.owned_groups_drained:
                        effective_code = effective_code or 125
                    item.update({"status": "TERMINAL", "returncode": code, "effective_returncode": effective_code})
        except BaseException as error:
            item.update({"status": "INTERRUPTED_OR_FAILED", "error_type": type(error).__name__,
                         "effective_returncode": 125})
            if process is not None:
                try:
                    self.drain(item, process, terminate=True)
                except Exception as cleanup_error:
                    self.owned_groups_drained = False
                    self.cleanup_event(item, "DRAIN_ERROR", error_type=type(cleanup_error).__name__)
                item["returncode"] = process.returncode
            raise
        finally:
            item["duration_seconds"] = round(time.time() - started, 3)
            for name, path in (("stdout", stdout), ("stderr", stderr)):
                if path.exists():
                    item[name + "_sha256"] = digest(path)
            self.persist()
        print(json.dumps({"stage": label, "returncode": item["returncode"],
                          "effective_returncode": item["effective_returncode"], "timed_out": item["timed_out"]}), flush=True)
        return item["effective_returncode"], stdout, stderr

    def require(self, label, argv, cwd, seconds):
        code, stdout, stderr = self.run(label, argv, cwd, seconds)
        if code or self.items[-1]["timed_out"]:
            raise RuntimeError("owned command failed: " + label)
        return stdout
