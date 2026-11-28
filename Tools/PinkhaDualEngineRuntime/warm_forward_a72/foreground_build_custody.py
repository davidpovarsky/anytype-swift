"""Finite ownership for the exact original warm App/UI producer.

Only this producer's subprocess namespace uses this adapter. The original
73bb termination and positive-absence declarations are called unchanged.
No observer, compiler command, resource allowance, or shared module is patched.
"""
from __future__ import annotations

import hashlib
import io
import json
import locale
import os
from pathlib import Path
import shutil
import signal
import subprocess as original_subprocess
import time

FLOOR = 2 * 1024 ** 3
ACTIVE_SECONDS = 3000
PHASES = ("app", "ui")


def error(exc):
    return {"type": type(exc).__name__, "message": str(exc)}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class ForegroundCommands:
    """One caller, one actual child generation at a time; no historical probes."""

    STDOUT = original_subprocess.STDOUT
    TimeoutExpired = original_subprocess.TimeoutExpired
    CalledProcessError = original_subprocess.CalledProcessError

    def __init__(self, output, source, lifecycle, started, record):
        self.output, self.source = Path(output), Path(source)
        self.lifecycle, self.started, self.record = lifecycle, started, record
        self.entries = []
        self.first_exception = None
        self.spawning = False
        self.cleaning = False
        self.phase_names = []
        self.namespace = None
        self.read_root = self.output / "owned-read-commands"
        self.read_root.mkdir(mode=0o700)

    def fail(self, exc, phase):
        if self.record["firstFailure"] is None:
            self.first_exception = exc
            self.record["firstFailure"] = error(exc)
            self.record["firstFailurePhase"] = phase
        elif self.record["firstFailure"] != error(exc):
            self.record["secondaryErrors"].append({"phase": phase, **error(exc)})
        self.record["workAdmissionClosed"] = True
        # Cancel, never restart, the sole active-work alarm before cleanup.
        signal.setitimer(signal.ITIMER_REAL, 0)

    def absorb_observer(self):
        if self.namespace is None:
            return
        state = self.namespace.get("WR_PHASE_OBSERVATION_STATE", {})
        first = state.get("firstFailure")
        if first is not None and self.record["firstFailure"] is None:
            self.record["firstFailure"] = first
            self.record["firstFailurePhase"] = "original-phase-observation"
            self.record["workAdmissionClosed"] = True
            signal.setitimer(signal.ITIMER_REAL, 0)
        if state.get("commandCustodyBlocked") or state.get("processObservationCustodyBlocked"):
            self.record["commandCustodyBlocked"] = True
            self.record["workAdmissionClosed"] = True

    def check(self):
        self.absorb_observer()
        if time.monotonic() - self.started >= ACTIVE_SECONDS and self.record["firstFailure"] is None:
            self.fail(TimeoutError("WHOLE_BUILD_ACTIVE_BUDGET_3000_SECONDS_EXPIRED"), "whole-budget")
        if self.record["firstFailure"] is not None or self.record["workAdmissionClosed"] or self.record["commandCustodyBlocked"]:
            raise RuntimeError("Foreground build work is closed after its original failure or unresolved custody") from self.first_exception
        if any(not item["finished"] for item in self.entries):
            raise RuntimeError("An earlier actual child generation is not yet closed")

    def on_signal(self, signum):
        already_closed = self.record["workAdmissionClosed"] or self.record["firstFailure"] is not None
        if signum == signal.SIGALRM:
            self.record["alarmFired"] = True
            exc = TimeoutError("WHOLE_BUILD_ACTIVE_BUDGET_3000_SECONDS_EXPIRED")
        else:
            exc = InterruptedError("FOREGROUND_BUILD_SIGNAL_" + str(signum))
        self.record.setdefault("signals", []).append({"signal": signum, "at": time.time()})
        self.fail(exc, "signal")
        # A signal cannot interrupt the Popen-return/registration boundary or
        # an already-entered original cleanup. Admission remains closed.
        if already_closed or self.spawning or self.cleaning:
            return
        raise exc

    def _write(self, path, value, phase):
        try:
            raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
            with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if Path(path).read_bytes() != raw:
                raise RuntimeError("Owned command receipt readback differs")
            return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        except BaseException as exc:
            self.fail(exc, phase)
            return None

    def _spawn(self, argv, directory, outcome, *, cwd, env, stdout, stderr):
        self.check()
        item = {"process": None, "directory": Path(directory), "outcome": outcome,
                "finished": False, "absence": None, "exitReceipt": None, "resultReceipt": None}
        self.entries.append(item)
        self.spawning = True
        try:
            process = original_subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout,
                                                stderr=stderr, start_new_session=True)
            # Retain the actual Popen object before time, serialization, log,
            # receipt, polling, or any other fallible post-spawn work.
            item["process"] = process
            self.lifecycle.groups.append(process.pid)
            self.lifecycle.absent_groups.discard(process.pid)
            outcome.update(pid=process.pid, pgid=process.pid)
        except BaseException as exc:
            self.fail(exc, "owned-spawn")
            raise
        finally:
            self.spawning = False
        if self.record["firstFailure"] is not None:
            raise self.first_exception or RuntimeError("Signal closed work while retaining actual Popen")
        return item

    def _finish(self, item, *, log=None):
        if item["finished"]:
            return
        was_cleaning = self.cleaning
        self.cleaning = True
        process, row, directory = item["process"], item["outcome"], item["directory"]
        try:
            if process is not None:
                try:
                    if process.poll() is None:
                        self.lifecycle._terminate_owned_process(process, row)
                except BaseException as exc:
                    row["cleanupErrors"].append({"phase": "original-owned-termination", **error(exc)})
                    self.fail(exc, "original-owned-termination")
                try:
                    row["exitCode"] = process.wait(timeout=1)
                except BaseException as exc:
                    row["exitCode"] = None
                    row["cleanupErrors"].append({"phase": "final-owned-wait", **error(exc)})
                    self.fail(exc, "final-owned-wait")
            else:
                row["exitCode"] = None
            row["finished"] = time.time()
            row["firstFailure"] = self.record["firstFailure"]
            row["commandStatus"] = ("PASS_COMMAND" if row["exitCode"] == 0 and not row["cleanupErrors"]
                                    and self.record["firstFailure"] is None else "FAIL_COMMAND")
            if log is not None:
                try:
                    row.update(logSHA256=digest(log), logBytes=Path(log).stat().st_size)
                except BaseException as exc:
                    row["cleanupErrors"].append({"phase": "original-log-identity", **error(exc)})
                    self.fail(exc, "original-log-identity")
            # Attempt exit persistence before the original read-only group
            # observation. A failed write cannot skip actual closure.
            row["status"] = "EXIT_RECORDED_PENDING_GROUP_OBSERVATION"
            item["exitReceipt"] = self._write(directory / "process-exit.json", row, "process-exit-receipt")
            if process is None:
                observed = {"status": "NOT_CREATED", "present": None, "observations": []}
            elif process.pid in self.lifecycle.absent_groups:
                # Only this exact retained generation can have been latched.
                observed = {"status": "ABSENT_ESRCH", "present": False, "observations": []}
            else:
                try:
                    observed = self.lifecycle._observe_exited_group(process.pid)
                except BaseException as exc:
                    observed = {"status": "UNRESOLVED_OBSERVATION_ERROR", "present": None,
                                "observations": [{"status": "UNRESOLVED_OBSERVATION_ERROR", "error": error(exc)}]}
                    self.fail(exc, "original-group-observation")
            item["absence"] = observed["status"]
            if process is not None and observed["status"] == "ABSENT_ESRCH":
                self.lifecycle.absent_groups.add(process.pid)
            elif process is not None:
                self.record["commandCustodyBlocked"] = True
                self.fail(RuntimeError("Actual owned group absence remains unresolved"), "owned-group-closure")
            row.update(ownedProcessGroup=observed["status"],
                       ownedGroupObservationStatus=observed["status"],
                       ownedGroupPresentAfterExit=observed["present"],
                       ownedGroupObservations=observed["observations"],
                       firstFailure=self.record["firstFailure"])
            if item["exitReceipt"] is not None:
                row["processExitReceiptSHA256"] = item["exitReceipt"]["sha256"]
            good = (row["exitCode"] == 0 and not row["cleanupErrors"]
                    and observed["status"] == "ABSENT_ESRCH" and self.record["firstFailure"] is None)
            row["status"] = ("PASS_BUILD_EXIT_0" if good else "FAIL_BUILD") if row.get("phase") in PHASES else ("PASS_COMMAND" if good else "FAIL_COMMAND")
            item["resultReceipt"] = self._write(directory / "result.json", row, "command-result-receipt")
        finally:
            # A completed unresolved observation is final evidence, not a
            # license for later repeated probes or historical signaling.
            item["finished"] = True
            self.cleaning = was_cleaning

    def run(self, argv, **kwargs):
        """Preserve the original fixed run() call semantics and separate streams."""
        allowed = {"cwd", "env", "capture_output", "text", "check", "timeout"}
        if set(kwargs) - allowed or kwargs.get("capture_output") is not True or kwargs.get("text") is not True:
            raise ValueError("Only the original captured-text producer calls are admitted")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("Exact original argv list required")
        self.check()
        original_timeout = kwargs.get("timeout")
        if original_timeout is not None and (type(original_timeout) not in (int, float) or not 0 < original_timeout < float("inf")):
            raise ValueError("Original command timeout must be positive and finite")
        remaining = ACTIVE_SECONDS - (time.monotonic() - self.started)
        timeout = min(remaining, original_timeout) if original_timeout is not None else remaining
        directory = self.read_root / ("%04d" % (len(self.entries) + 1))
        directory.mkdir(mode=0o700)
        started = time.monotonic()
        minimum = shutil.disk_usage(self.output).free
        if minimum < FLOOR:
            raise RuntimeError("Free space below original owned 2 GiB guard")
        row = {"argv": list(argv), "cwd": str(kwargs.get("cwd") or Path.cwd()),
               "started": time.time(), "originalTimeoutSeconds": original_timeout,
               "timeoutSeconds": timeout, "minimumFreeBytes": minimum, "cleanupErrors": [], "termination": []}
        item, raised = None, None
        stdout, stderr = directory / "stdout.log", directory / "stderr.log"
        try:
            with stdout.open("xb") as out, stderr.open("xb") as err:
                item = self._spawn(argv, directory, row, cwd=kwargs.get("cwd"), env=kwargs.get("env"),
                                   stdout=out, stderr=err)
                if self._write(directory / "started.json", row, "read-command-started-receipt") is None:
                    raise self.first_exception or RuntimeError("Owned started receipt failed")
                while item["process"].poll() is None:
                    minimum = min(minimum, shutil.disk_usage(self.output).free)
                    if minimum < FLOOR:
                        raise RuntimeError("OWNED_RESOURCE_FLOOR")
                    if time.monotonic() - started > timeout:
                        raise original_subprocess.TimeoutExpired(argv, timeout)
                    time.sleep(min(0.1, max(0.001, timeout - (time.monotonic() - started))))
                row["exitCode"] = item["process"].wait(timeout=1)
                if kwargs.get("check", False) and row["exitCode"]:
                    raise original_subprocess.CalledProcessError(row["exitCode"], argv)
        except BaseException as exc:
            raised = exc
            self.fail(exc, "original-read-command")
        finally:
            row["minimumFreeBytes"] = minimum
            if item is not None:
                self._finish(item)
        if raised is not None:
            raise raised
        if self.record["firstFailure"] is not None:
            raise self.first_exception or RuntimeError("Owned read command closure failed")
        def decoded(path):
            with io.TextIOWrapper(io.BytesIO(path.read_bytes()), encoding=locale.getencoding(), errors="strict", newline=None) as stream:
                return stream.read()
        return original_subprocess.CompletedProcess(argv, row["exitCode"], decoded(stdout), decoded(stderr))

    def run_phase(self, namespace, name, argv, timeout=7200):
        self.check()
        if name not in PHASES or self.phase_names != list(PHASES[:len(self.phase_names)]) or name != PHASES[len(self.phase_names)]:
            raise ValueError("Exactly original App then original Stage1 UI is required")
        if timeout != 7200 or argv.count("-jobs") != 1 or argv[argv.index("-jobs") + 1] != "4":
            raise ValueError("Original phase ceiling and four jobs must remain exact")
        self.phase_names.append(name)
        root, evidence = namespace["ROOT"], namespace["EVIDENCE"]
        directory = evidence / name
        directory.mkdir()
        log = directory / "original.log"
        start = time.time()
        phase_start = time.monotonic()
        minimum = shutil.disk_usage(root).free
        if minimum < namespace["FLOOR"] + namespace["PHASE_GROWTH"][name] + namespace["CONCURRENT_GROWTH"]:
            raise RuntimeError("Warm phase allowance, concurrent growth and 2 GiB emergency floor are unavailable")
        env = namespace["ENV"]
        row = {"phase": name, "sourceCommit": namespace["EXPECTED"], "argv": argv,
               "cwd": str(namespace["SOURCE"]), "started": start, "status": "RUNNING",
               "freeBytesBefore": minimum, "minimumFreeBytes": minimum,
               "timeoutSeconds": timeout, "wholeActiveBudgetSeconds": ACTIVE_SECONDS,
               "jobs": 4, "cleanupErrors": [], "termination": [],
               "environment": {"DEVELOPER_DIR": env["DEVELOPER_DIR"],
                               "PINKHA_ANY_NATIVE_ARTIFACT": env["PINKHA_ANY_NATIVE_ARTIFACT"],
                               "PINKHA_NATIVE_T2_AUTHORIZED_READ_V1": "1"}}
        item, raised = None, None
        try:
            with log.open("wb") as stream:
                item = self._spawn(argv, directory, row, cwd=namespace["SOURCE"], env=env,
                                   stdout=stream, stderr=original_subprocess.STDOUT)
                namespace["write"](directory / "command.json", row)
                namespace["write"](evidence / "active.json", row)
                while item["process"].poll() is None:
                    free = shutil.disk_usage(root).free
                    minimum = min(minimum, free)
                    if free < namespace["FLOOR"]:
                        raise RuntimeError("RESOURCE_DISK_FLOOR")
                    if time.monotonic() - phase_start > timeout:
                        raise TimeoutError("TIMEOUT")
                    if time.monotonic() - self.started >= ACTIVE_SECONDS:
                        raise TimeoutError("WHOLE_BUILD_ACTIVE_BUDGET_3000_SECONDS_EXPIRED")
                    namespace["write"](directory / "monitor.json",
                        {"time": time.time(), "elapsedSeconds": time.time() - start, "freeBytes": free,
                         "minimumFreeBytes": minimum, "pid": item["process"].pid})
                    time.sleep(2)
                code = item["process"].wait(timeout=1)
                if code != 0:
                    raise RuntimeError(name + " FAIL_BUILD_EXIT_" + str(code))
        except BaseException as exc:
            raised = exc
            self.fail(exc, "original-" + name + "-phase")
        finally:
            row.update(elapsedSeconds=time.time() - start, minimumFreeBytes=minimum)
            try:
                row["freeBytesAfter"] = shutil.disk_usage(root).free
            except BaseException as exc:
                self.fail(exc, "phase-final-free-space")
            if item is not None:
                self._finish(item, log=log)
                try:
                    namespace["write"](evidence / "active.json", row)
                except BaseException as exc:
                    self.fail(exc, "phase-active-receipt")
        if raised is not None:
            raise raised
        if self.record["firstFailure"] is not None:
            raise self.first_exception or RuntimeError(name + " owned closure failed")
        if row["status"] != "PASS_BUILD_EXIT_0" or row["ownedProcessGroup"] != "ABSENT_ESRCH":
            raise RuntimeError(name + " process group is not positively absent")
        return row

    def close_all(self):
        self.cleaning = True
        self.record["workAdmissionClosed"] = True
        signal.setitimer(signal.ITIMER_REAL, 0)
        for item in self.entries:
            if not item["finished"]:
                self._finish(item, log=(item["directory"] / "original.log") if item["outcome"].get("phase") in PHASES else None)
        self.absorb_observer()
        closed = all(item["process"] is None or item["absence"] == "ABSENT_ESRCH" for item in self.entries)
        self.record["allDirectProducerGroupsClosed"] = closed
        if not closed:
            self.record["commandCustodyBlocked"] = True
        rows = []
        for item in self.entries:
            row = item["outcome"]
            rows.append({"pid": row.get("pid"), "phase": row.get("phase"), "status": row.get("status"),
                         "exitCode": row.get("exitCode"), "ownedGroup": item["absence"],
                         "processExit": item["exitReceipt"], "result": item["resultReceipt"]})
        return self._write(self.output / "owned-producer-command-index.json",
                           {"schema": "pinkha-warm-build-owned-command-index-v1", "commands": rows,
                            "allDirectProducerGroupsClosed": closed, "historicalProcessProbes": 0,
                            "firstFailure": self.record["firstFailure"]}, "owned-command-index")
