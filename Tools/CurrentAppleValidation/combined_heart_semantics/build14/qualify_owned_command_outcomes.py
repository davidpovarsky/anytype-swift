#!/usr/bin/env python3
"""Actual tiny-process and injected-observation controls; no Apple/app/native test claim."""
from __future__ import annotations
import argparse
import ast
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from unittest import mock

sys.dont_write_bytecode = True
EXPECTED = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"
ORIGINAL = "59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de"

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controller", type=Path, required=True)
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert digest(a.controller) == EXPECTED and digest(a.original) == ORIGINAL
    a.output.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location("owned_outcomes_candidate", a.controller)
    c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
    checks = []
    start = time.time()

    def check(name, body):
        case = a.output / name
        case.mkdir(mode=0o700)
        row = {"name": name, "startedAt": time.time(), "status": "FAIL"}
        try:
            row["evidence"] = body(case)
            row["status"] = "PASS"
        except BaseException as exc:
            row["error"] = {"type": type(exc).__name__, "message": str(exc)}
        row["finishedAt"] = time.time()
        checks.append(row)
        c.write(case / "control.json", row)

    def receipts(cmd, label):
        d = cmd.root / label
        e, r = c.decode((d / "process-exit.json").read_bytes()), c.decode((d / "result.json").read_bytes())
        assert r["processExitReceipt"]["sha256"] == digest(d / "process-exit.json")
        assert r["logSHA256"] == digest(d / "original.log")
        return e, r

    def proof(cmd, label, **extra):
        d = cmd.root / label
        return {"exitReceiptSHA256": digest(d / "process-exit.json"),
                "resultSHA256": digest(d / "result.json"), **extra}

    def actual_absent(pid):
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        raise AssertionError("actual owned group not positively absent")

    def normal(case):
        class Observe(c.Commands):
            def _observe_exited_group(self, group):
                e = c.decode((self.root / "actual" / "process-exit.json").read_bytes())
                assert e["exitCode"] == 0 and e["status"] == "EXIT_RECORDED_PENDING_GROUP_OBSERVATION"
                assert not (self.root / "actual" / "result.json").exists()
                return super()._observe_exited_group(group)
        cmd = Observe(case / "commands", case)
        _, row = cmd.run([sys.executable, "-c", "print('actual-child-output')"], "actual", capacity=False)
        e, r = receipts(cmd, "actual")
        assert row == r and r["status"] == "PASS_COMMAND" and r["ownedGroupObservationStatus"] == "ABSENT_ESRCH"
        assert r["ownedGroupObservations"] == [r["ownedGroupObservations"][0]]
        assert r["pid"] in cmd.absent_groups
        actual_absent(r["pid"])
        assert (cmd.root / "actual" / "original.log").read_text() == "actual-child-output\n"
        return proof(cmd, "actual", actualExitCode=0, exitPersistedBeforeProbe=True)

    def nonzero(case, checked):
        cmd = c.Commands(case / "commands", case)
        caught = None
        try:
            cmd.run([sys.executable, "-c", "raise SystemExit(7)"], "nonzero", checked=checked, capacity=False)
        except ValueError as exc:
            caught = str(exc)
        e, r = receipts(cmd, "nonzero")
        assert r["exitCode"] == 7 and e["exitCode"] == 7 and r["status"] == "FAIL_COMMAND"
        assert bool(caught) == checked and r["ownedGroupObservationStatus"] == "ABSENT_ESRCH"
        actual_absent(r["pid"])
        return proof(cmd, "nonzero", checked=checked, actualExitCode=7)

    def spawn_failure(case):
        cmd = c.Commands(case / "commands", case)
        try:
            cmd.run([str(case / "does-not-exist")], "spawn", capacity=False)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("spawn must fail")
        e, r = receipts(cmd, "spawn")
        assert e["exitCode"] is None and r["ownedGroupObservationStatus"] == "NOT_CREATED"
        assert r["status"] == "FAIL_COMMAND" and not cmd.groups
        assert not (cmd.root / "spawn" / "started.json").exists()
        return proof(cmd, "spawn", actualProcessStarted=False)

    def permission_then_absence(case):
        class Observe(c.Commands):
            calls = 0
            def present(self, group):
                self.calls += 1
                assert (self.root / "actual" / "process-exit.json").is_file()
                if self.calls == 1:
                    raise PermissionError(errno.EPERM, "injected post-exit observation")
                assert self.calls == 2, "absence must end all historical probes"
                return c.Commands.present(group)
        cmd = Observe(case / "commands", case)
        _, r = cmd.run([sys.executable, "-c", "pass"], "actual", capacity=False)
        assert [x["status"] for x in r["ownedGroupObservations"]] == [
            "UNRESOLVED_PERMISSION_DENIED", "ABSENT_ESRCH"]
        assert r["status"] == "PASS_COMMAND" and cmd.calls == 2
        actual_absent(r["pid"])
        return proof(cmd, "actual", injectedEPERM=1, actualESRCH=1, signals=0)

    def unresolved_permission(case):
        class Observe(c.Commands):
            def present(self, group):
                raise PermissionError(errno.EPERM, "injected persistent observation denial")
        cmd = Observe(case / "commands", case)
        started = time.monotonic()
        try:
            cmd.run([sys.executable, "-c", "pass"], "actual", checked=False, capacity=False)
        except ValueError as exc:
            assert "absence unresolved" in str(exc)
        else:
            raise AssertionError("checked=False must not waive unresolved ownership")
        elapsed = time.monotonic() - started
        e, r = receipts(cmd, "actual")
        assert e["exitCode"] == r["exitCode"] == 0
        assert r["status"] == "FAIL_COMMAND" and r["pid"] not in cmd.absent_groups
        assert len(r["ownedGroupObservations"]) == len(cmd._group_observation_delays)
        assert all(x["status"] == "UNRESOLVED_PERMISSION_DENIED" for x in r["ownedGroupObservations"])
        assert elapsed < 10
        actual_absent(r["pid"])  # independent real check; does not rewrite candidate FAIL
        return proof(cmd, "actual", actualExitCode=0, elapsedSeconds=elapsed,
                     originalStatusRetained="FAIL_COMMAND", injectedEPERM=True)

    def present_then_absence(case):
        class Observe(c.Commands):
            calls = 0
            def present(self, group):
                self.calls += 1
                if self.calls == 1:
                    return True
                assert self.calls == 2
                return c.Commands.present(group)
        cmd = Observe(case / "commands", case)
        _, r = cmd.run([sys.executable, "-c", "pass"], "actual", capacity=False)
        assert [x["status"] for x in r["ownedGroupObservations"]] == ["PRESENT", "ABSENT_ESRCH"]
        assert r["status"] == "PASS_COMMAND"
        actual_absent(r["pid"])
        return proof(cmd, "actual", injectedPresent=1, actualESRCH=1)

    def unresolved_present(case):
        class Observe(c.Commands):
            def present(self, group):
                return True
        cmd = Observe(case / "commands", case)
        try:
            cmd.run([sys.executable, "-c", "pass"], "actual", checked=False, capacity=False)
        except ValueError:
            pass
        else:
            raise AssertionError("persistent presence cannot pass")
        e, r = receipts(cmd, "actual")
        assert r["status"] == "FAIL_COMMAND" and r["ownedGroupPresentAfterExit"] is True
        assert r["pid"] not in cmd.absent_groups and e["exitCode"] == 0
        actual_absent(r["pid"])
        return proof(cmd, "actual", injectedPresent=True, originalStatusRetained="FAIL_COMMAND")

    def other_probe_error(case):
        class Observe(c.Commands):
            def present(self, group):
                raise OSError(errno.EIO, "injected observation error")
        cmd = Observe(case / "commands", case)
        try:
            cmd.run([sys.executable, "-c", "pass"], "actual", capacity=False)
        except ValueError:
            pass
        else:
            raise AssertionError("observation error must fail")
        e, r = receipts(cmd, "actual")
        assert r["ownedGroupObservationStatus"] == "UNRESOLVED_OBSERVATION_ERROR"
        assert r["status"] == "FAIL_COMMAND" and len(r["ownedGroupObservations"]) == 1
        actual_absent(r["pid"])
        return proof(cmd, "actual", originalExitRetained=e["exitCode"])

    def timeout_reaps(case):
        cmd = c.Commands(case / "commands", case)
        try:
            cmd.run([sys.executable, "-c", "import time; time.sleep(30)"], "timeout", timeout=0.05, capacity=False)
        except ValueError:
            pass
        else:
            raise AssertionError("timeout must fail")
        e, r = receipts(cmd, "timeout")
        assert r["interruption"]["type"] == "TimeoutError" and "OWNED_TIMEOUT" in r["interruption"]["message"]
        assert r["exitCode"] == -signal.SIGTERM and r["status"] == "FAIL_COMMAND"
        assert r["termination"][0]["waitStatus"] == "CHILD_REAPED"
        assert (cmd.root / "timeout" / "interruption.json").is_file()
        actual_absent(r["pid"])
        try:
            os.waitpid(r["pid"], os.WNOHANG)
        except ChildProcessError:
            pass
        else:
            raise AssertionError("owned child must already be reaped")
        return proof(cmd, "timeout", actualExitCode=r["exitCode"], actualChildReaped=True)

    def timeout_denied_signal(case):
        cmd = c.Commands(case / "commands", case)
        original = os.killpg
        attempted = []
        def scoped(group, sig):
            if sig:
                assert group in cmd.groups and group > 1
                attempted.append({"group": group, "signal": int(sig)})
                raise PermissionError(errno.EPERM, "injected owned signal denial")
            return original(group, sig)
        with mock.patch.object(c.os, "killpg", side_effect=scoped):
            try:
                cmd.run([sys.executable, "-c", "import time; time.sleep(1.4)"],
                        "timeout", timeout=0.05, capacity=False)
            except ValueError:
                pass
            else:
                raise AssertionError("original timeout must remain failure")
        e, r = receipts(cmd, "timeout")
        assert r["exitCode"] == 0 and r["interruption"]["type"] == "TimeoutError"
        assert r["status"] == "FAIL_COMMAND" and r["cleanupErrors"][0]["type"] == "PermissionError"
        assert len(attempted) == 1 and r["termination"][0]["waitStatus"] == "CHILD_REAPED"
        assert r["ownedGroupObservationStatus"] == "ABSENT_ESRCH"
        actual_absent(r["pid"])
        return proof(cmd, "timeout", actualExitCode=0, originalTimeoutRetained=True,
                     injectedSignalEPERM=1, actualSignalsSent=0)

    def source_inverse(case):
        before, after = a.original.read_text(), a.controller.read_text()
        def class_span(s):
            tree = ast.parse(s)
            n = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "Commands")
            lines = s.splitlines(keepends=True)
            return "".join(lines[n.lineno-1:n.end_lineno])
        old_class, new_class = class_span(before), class_span(after)
        recovered = after.replace(new_class, old_class, 1)
        old_cleanup = '            present = Commands.present(group)\n            cleanup["groups"].append({"pgid": group, "present": present})\n            if present:\n                cleanup["status"] = "FAIL"\n                cleanup["errors"].append({"ownedGroupStillPresent": group})'
        new_cleanup = '            try:\n                present = Commands.present(group)\n                cleanup["groups"].append({"pgid": group, "present": present})\n                if present:\n                    cleanup["status"] = "FAIL"\n                    cleanup["errors"].append({"ownedGroupStillPresent": group})\n                else:\n                    commands.absent_groups.add(group)\n            except BaseException as exc:\n                cleanup["status"] = "FAIL"\n                cleanup["errors"].append({"phase": "owned-group-observation",\n                                          "pgid": group, **error(exc)})'
        assert recovered.count(new_cleanup) == 1
        recovered = recovered.replace(new_cleanup, old_cleanup, 1)
        assert recovered == before
        return {"inverseSHA256": hashlib.sha256(recovered.encode()).hexdigest(),
                "allAdmissionAndStageBytesUnchanged": True, "noAppleBuildOrTests": True}

    check("actual-zero-exit-recorded-before-probe", normal)
    check("actual-nonzero-checked", lambda q: nonzero(q, True))
    check("actual-nonzero-unchecked", lambda q: nonzero(q, False))
    check("actual-spawn-failure-retained", spawn_failure)
    check("injected-eperm-then-real-esrch", permission_then_absence)
    check("injected-unresolved-eperm-stays-fail", unresolved_permission)
    check("injected-present-then-real-esrch", present_then_absence)
    check("injected-unresolved-present-stays-fail", unresolved_present)
    check("injected-other-probe-error-retains-exit", other_probe_error)
    check("actual-timeout-terminates-and-reaps-owned-child", timeout_reaps)
    check("injected-signal-eperm-still-reaps-and-keeps-timeout", timeout_denied_signal)
    check("exact-source-inverse", source_inverse)
    same = digest(a.controller) == EXPECTED and digest(a.original) == ORIGINAL
    result = {"protocol": "pinkha-owned-command-outcome-controls-v1",
              "status": "PASS" if same and all(x["status"] == "PASS" for x in checks) else "FAIL",
              "passed": sum(x["status"] == "PASS" for x in checks),
              "failed": sum(x["status"] != "PASS" for x in checks), "skipped": 0,
              "startedAt": start, "finishedAt": time.time(), "platform": platform.platform(),
              "python": sys.version, "candidateSHA256": EXPECTED, "originalSHA256": ORIGINAL,
              "sourcesUnchanged": same, "checks": checks,
              "appleBuilds": 0, "nativeBuilds": 0, "appOrSimulatorCalls": 0}
    c.write(a.output / "result.json", result)
    print(json.dumps({"status": result["status"], "passed": result["passed"], "failed": result["failed"],
                      "result": str(a.output / "result.json"), "sha256": digest(a.output / "result.json")}))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
