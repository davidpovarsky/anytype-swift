#!/usr/bin/env python3
"""One genuine local owned-process probe; no Swift, project, cache or host work."""
import ctypes
import datetime
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import traceback

HERE = Path(__file__).resolve().parent
RUNNER_SHA = "99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2"
OUTPUT = HERE / "owned-cleanup-probe1"
LEADER = r'''
import json, os, signal, time
read_fd, write_fd = os.pipe()
child = os.fork()
if child == 0:
    os.close(read_fd)
    signal.alarm(20)
    os.write(write_fd, b"R")
    os.close(write_fd)
    while True:
        time.sleep(0.1)
os.close(write_fd)
assert os.read(read_fd, 1) == b"R"
os.close(read_fd)
os.write(1, (json.dumps({"leaderPID": os.getpid(), "childPID": child, "group": os.getpgrp()}) + "\n").encode())
os._exit(0)
'''


def main():
    started = time.monotonic()
    assert not OUTPUT.exists(), "Retain every original probe attempt"
    OUTPUT.mkdir(mode=0o700)
    raw = (HERE / "run_component.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RUNNER_SHA
    spec = importlib.util.spec_from_file_location("owned_cleanup_probe_runner", HERE / "run_component.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    result = {"schema": "pinkha-properties-owned-cleanup-probe-v1", "status": "FAIL",
        "runnerSHA256": RUNNER_SHA, "probeSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "startedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Actual cleanup/finalization helper with a newly owned local Python process group",
        "SwiftInvocations": 0, "AppleInvocations": 0, "OracleActions": 0,
        "MacActions": 0, "projectCacheMutations": 0, "productAdmission": False}
    libc = ctypes.CDLL(None, use_errno=True)
    original_subreaper = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(original_subreaper), 0, 0, 0) == 0
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    # This setting belongs only to this short-lived probe process. It lets us
    # genuinely reap our adopted child instead of mistaking a zombie for absence.
    process = None
    reaper = None
    group_state = {}
    phase = {"status": "FAIL"}
    real_killpg, real_members = runner.os.killpg, runner.group_members
    calls = []
    terminal_observed = False
    reaped = {}

    def reaping(child):
        try:
            waited, status = os.waitpid(child, 0)
            reaped.update(pid=waited, waitStatus=status,
                terminatingSignal=os.WTERMSIG(status) if os.WIFSIGNALED(status) else None)
        except BaseException:
            reaped["failure"] = traceback.format_exc()

    def tracked_killpg(pgid, sig):
        nonlocal terminal_observed
        assert process is not None and pgid == process.pid, "Only this newly owned group may be addressed"
        assert not terminal_observed, "No group syscall is allowed after actual terminal absence"
        row = {"group": pgid, "signal": int(sig)}
        calls.append(row)
        try:
            real_killpg(pgid, sig)
            row["result"] = "PRESENT" if sig == 0 else "SIGNAL_DELIVERED"
        except OSError as error:
            row.update(result="OS_ERROR", errno=error.errno)
            if error.errno == errno.ESRCH:
                terminal_observed = True
            raise

    def tracked_members(pgid):
        assert not terminal_observed, "No diagnostic re-probe after recorded absence"
        return real_members(pgid)

    try:
        with (OUTPUT / "leader.stdout").open("wb") as stdout, (OUTPUT / "leader.stderr").open("wb") as stderr:
            process = subprocess.Popen([sys.executable, "-c", LEADER], stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            assert process.wait(timeout=5) == 0
        identity = json.loads((OUTPUT / "leader.stdout").read_text())
        assert identity["leaderPID"] == identity["group"] == process.pid
        child = identity["childPID"]
        stat = Path("/proc", str(child), "stat").read_text()
        fields = stat[stat.rindex(")") + 2:].split()
        assert int(fields[1]) == os.getpid() and int(fields[2]) == process.pid
        result["actualOwnedIdentity"] = identity
        result["leaderReapedBeforeFailure"] = True
        result["childAdoptedByProbe"] = True
        reaper = threading.Thread(target=reaping, args=(child,), daemon=False)
        reaper.start()
        runner.os.killpg, runner.group_members = tracked_killpg, tracked_members
        try:
            raise RuntimeError("CONTROLLED_POST_POPEN_EXCEPTION_WITH_SURVIVING_CHILD")
        except BaseException:
            phase["failure"] = traceback.format_exc()
            original_failure = phase["failure"]
        finally:
            runner.finish_owned_process(process, group_state, phase)
        reaper.join(timeout=3)
        assert not reaper.is_alive() and "failure" not in reaped
        assert reaped["pid"] == child and reaped["terminatingSignal"] == signal.SIGTERM
        assert phase["status"] == "FAIL" and phase["failure"] == original_failure
        assert phase["ownedCleanup"]["status"] == "PASS_OWNED_GROUP_ABSENT"
        assert phase["ownedCleanup"]["terminationRequired"] is True
        assert phase["ownedCleanup"]["absenceEvidence"]["signal"] == 0
        assert terminal_observed and calls[-1]["errno"] == errno.ESRCH and calls[-1]["signal"] == 0
        before = list(calls)
        assert runner.observe_owned_group(process, group_state) == group_state["absence"]
        cached = runner.drain_owned_process(process, group_state)
        assert cached["status"] == "PASS_OWNED_GROUP_ABSENT" and calls == before
        result.update(status="PASS_REAL_OWNED_CLEANUP_AND_ORIGINAL_FAILURE_RETAINED",
            phaseReceipt=phase, reapedChild=reaped, actualGroupCalls=calls,
            noSyscallOrDiagnosticAfterAbsence=True, originalFailureRetained=True,
            cachedObservation=group_state["absence"], cachedCleanup=cached)
    except BaseException:
        result["failure"] = traceback.format_exc()
    finally:
        # Fallback cleanup still uses only our stateful owned-group helper. The
        # child also has a 20-second self-expiry if the intentional probe fails.
        if process is not None and group_state.get("absence") is None:
            result["fallbackCleanup"] = runner.drain_owned_process(process, group_state)
        if reaper is not None:
            reaper.join(timeout=25)
            if reaper.is_alive():
                result["status"] = "FAIL"
                result["reapingFailure"] = "Owned adopted-child reaper did not finish"
        runner.os.killpg, runner.group_members = real_killpg, real_members
        assert libc.prctl(36, original_subreaper.value, 0, 0, 0) == 0
        result["subreaperSettingRestored"] = True
        result["elapsedSeconds"] = time.monotonic() - started
        result["actualGroupCalls"] = calls
        result["reapedChild"] = reaped
        result["phaseReceipt"] = phase
        (OUTPUT / "receipt.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True, indent=2), flush=True)
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
