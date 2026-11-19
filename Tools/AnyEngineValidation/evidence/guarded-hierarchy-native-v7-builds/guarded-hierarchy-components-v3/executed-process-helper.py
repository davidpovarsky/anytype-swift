#!/usr/bin/env python3
"""Run the real Swift public-provider probe with source and process evidence.

This runner supplies no provider transport, response, URL, or account. The Swift
executable receives only --live-public-provider. Each invocation creates a new
evidence directory and preserves stdout/stderr even after failure or timeout.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from typing import Any


CASE_IDS = [
    "hebrew_reference_genesis_1_1",
    "hebrew_text_version_preserved_payload",
    "commentary_and_links",
    "source_hierarchy",
    "topic_search_shabbat",
    "resolve_returned_topic",
    "hebrew_word_with_reference_context",
]
SCOPE = "real_public_sefaria_production_facade"
PACKAGES = ("PinkhaKit", "PinkhaAnyEngine", "PinkhaAnyIntegration")
MAX_PROCESS_SECONDS = 720


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8", timeout=30
    ).rstrip("\r\n")


def is_source_artifact(path: Path) -> bool:
    """Exclude known editor/cache artifacts that SwiftPM does not compile."""
    name = path.name
    return not (
        ".bak." in name or name.endswith((".bak", "~", ".swp", ".swo", ".tmp", ".pyc"))
        or name.startswith(".#") or name == ".DS_Store"
        or any(part in ("__pycache__", ".cache") for part in path.parts)
    )


def source_snapshot(repo: Path, runner: Path) -> dict[str, Any]:
    paths: set[Path] = {runner.resolve()}
    for package in PACKAGES:
        root = repo / "Modules" / package
        paths.update(p for p in (root / "Sources").rglob("*") if p.is_file() and is_source_artifact(p))
        for name in ("Package.swift", "Package.resolved"):
            if (root / name).is_file():
                paths.add(root / name)
    files = {
        p.relative_to(repo).as_posix(): {"sha256": sha256(p), "bytes": p.stat().st_size}
        for p in sorted(paths)
    }
    dependencies: dict[str, Any] = {}
    checkout_root = repo / "Modules/PinkhaAnyIntegration/.build/checkouts"
    if not checkout_root.is_dir():
        raise RuntimeError("integration_dependency_checkouts_missing")
    for checkout in sorted(checkout_root.iterdir()):
        if not checkout.is_dir():
            continue
        # The commit pins ordinary dependency source. Any local tracked or
        # untracked changes are listed and hashed, so a clean pin is not invented.
        status = git(checkout, "status", "--porcelain", "--untracked-files=all")
        changes: dict[str, Any] = {}
        source_status: list[str] = []
        for line in status.splitlines():
            relative = line[3:]
            if " -> " in relative or relative.startswith('"'):
                raise RuntimeError("unsupported_dependency_change_path")
            path = checkout / relative
            if not is_source_artifact(path):
                continue
            source_status.append(line)
            if path.is_file():
                changes[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
            else:
                changes[relative] = {"missing": True}
        dependencies[checkout.name] = {
            "gitHEAD": git(checkout, "rev-parse", "HEAD"),
            "sourceRelevantChanges": "\n".join(source_status),
            "changedFiles": changes,
        }
    return {
        "gitHEAD": git(repo, "rev-parse", "HEAD"), "files": files, "dependencies": dependencies,
        "manifestPolicy": "Package declarations/resolutions and source/resources; known editor backups and caches excluded",
    }


class WindowsProcessJob:
    """An owned kill-on-close job; descendants inherit the same job boundary."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IOCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount"
            )]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimits), ("IoInfo", IOCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.TerminateJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "create_owned_job_failed")
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "set_owned_job_limits_failed")
        if not self.api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "assign_owned_process_job_failed")

    def terminate(self) -> None:
        if self.handle and not self.api.TerminateJobObject(self.handle, 124):
            raise OSError(ctypes.get_last_error(), "terminate_owned_job_failed")

    def close(self) -> None:
        if self.handle:
            handle, self.handle = self.handle, None
            if not self.api.CloseHandle(handle):
                raise OSError(ctypes.get_last_error(), "close_owned_job_failed")


def run_process(command: list[str], cwd: Path, output: Path, timeout: float) -> dict[str, Any]:
    """One isolated process, with actual descendants killed on deadline/cleanup."""
    started = time.monotonic()
    process: subprocess.Popen[bytes] | None = None
    job: WindowsProcessJob | None = None
    result: dict[str, Any] = {"command": command, "timedOut": False, "cleanupErrors": []}
    with (output / "stdout.json").open("wb") as stdout, (output / "stderr.log").open("wb") as stderr:
        try:
            process = subprocess.Popen(
                command, cwd=cwd, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                start_new_session=os.name != "nt",
            )
            result["pid"] = process.pid
            if os.name == "nt":
                job = WindowsProcessJob(process)
                result["processBoundary"] = "owned_windows_kill_on_close_job"
            else:
                result["processBoundary"] = "owned_posix_process_group"
            try:
                result["exitCode"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result["timedOut"] = True
                if job:
                    job.terminate()
                elif os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    raise RuntimeError("windows_process_job_not_available")
                result["exitCode"] = process.wait(timeout=15)
        except Exception as error:
            result["runnerErrorType"] = type(error).__name__
        finally:
            if job:
                try:
                    job.close()  # Also closes any descendants after a normal parent exit.
                except Exception as error:
                    result["cleanupErrors"].append("job_close:" + type(error).__name__)
            if process is not None:
                if os.name != "nt":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except Exception as error:
                        result["cleanupErrors"].append("process_group:" + type(error).__name__)
                elif process.poll() is None:
                    # Assigning the Windows job can fail under a restrictive
                    # outer job. Refuse the run and clean only our process tree.
                    try:
                        cleanup = subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=15,
                        )
                        result["fallbackTaskkillExitCode"] = cleanup.returncode
                    except Exception as error:
                        result["cleanupErrors"].append("taskkill:" + type(error).__name__)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    result["cleanupErrors"].append("owned_process_still_running")
                result["parentExited"] = process.poll() is not None
    result["elapsedSeconds"] = round(time.monotonic() - started, 3)
    return result


def validate_report(raw: bytes) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not raw or len(raw) > 1024 * 1024:
        return None, ["stdout_empty_or_over_bound"]
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None, ["stdout_not_one_utf8_json_document"]
    if not isinstance(report, dict):
        return None, ["report_not_object"]
    if set(report) != {"status", "scope", "count", "passed", "failed", "checks"}:
        errors.append("unexpected_report_fields")
    if report.get("scope") != SCOPE or report.get("status") not in ("PASS", "FAIL"):
        errors.append("report_scope_or_status_mismatch")
    for field in ("count", "passed", "failed"):
        if type(report.get(field)) is not int:
            errors.append("report_count_type_mismatch")
    checks = report.get("checks")
    if not isinstance(checks, list) or len(checks) != len(CASE_IDS):
        return None, errors + ["report_must_include_seven_checks"]
    if [c.get("id") if isinstance(c, dict) else None for c in checks] != CASE_IDS:
        return None, errors + ["check_ids_or_order_mismatch"]
    for check in checks:
        required = {"id", "status", "elapsedMilliseconds", "ids", "counts", "sha256"}
        if not required.issubset(check) or not set(check).issubset(required | {"errorCode"}):
            errors.append("unexpected_check_fields")
        if check.get("status") not in ("PASS", "FAIL"):
            errors.append("invalid_check_status")
        if type(check.get("elapsedMilliseconds")) is not int or check["elapsedMilliseconds"] < 0:
            errors.append("invalid_check_elapsed_time")
        ids, counts, hashes = (check.get(key) for key in ("ids", "counts", "sha256"))
        if not isinstance(ids, list) or len(ids) > 16 or any(
            not isinstance(value, str) or len(value.encode("utf-8")) > 4096 for value in ids
        ):
            errors.append("invalid_bounded_ids")
        if not isinstance(counts, dict) or len(counts) > 32 or not all(
            isinstance(key, str) and len(key) <= 128 and type(value) is int and value >= 0
            for key, value in counts.items()
        ):
            errors.append("invalid_metadata_counts")
        if not isinstance(hashes, dict) or len(hashes) > 32 or not all(
            isinstance(key, str) and len(key) <= 128 and isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value)
            for key, value in hashes.items()
        ):
            errors.append("invalid_metadata_hashes")
        if check.get("status") == "PASS" and (not ids or not counts or not hashes or check.get("errorCode")):
            errors.append("pass_check_missing_evidence_or_contains_error")
        if check.get("status") == "FAIL" and (
            not isinstance(check.get("errorCode"), str) or len(check["errorCode"]) > 256
        ):
            errors.append("failed_check_missing_error_code")
    actual_passed = sum(check.get("status") == "PASS" for check in checks)
    if report.get("count") != 7 or report.get("passed") != actual_passed or report.get("failed") != 7 - actual_passed:
        errors.append("report_totals_mismatch")
    if (report.get("status") == "PASS") != (actual_passed == 7):
        errors.append("overall_status_mismatch")
    return (report if not errors else None), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--build-log", type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=MAX_PROCESS_SECONDS)
    args = parser.parse_args()
    if not 0 < args.timeout_seconds <= MAX_PROCESS_SECONDS:
        parser.error("timeout must be greater than zero and at most 720 seconds")
    repo, executable, output = args.repo_root.resolve(), args.executable.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)  # Preserve every prior attempt.
    receipt: dict[str, Any] = {"status": "FAIL", "scope": SCOPE, "timeoutSeconds": args.timeout_seconds}
    before: dict[str, Any] | None = None
    try:
        before = source_snapshot(repo, Path(__file__))
        write_json(output / "source-before.json", before)
        receipt["binarySHA256Before"] = sha256(executable)
        receipt["binaryBytes"] = executable.stat().st_size
        receipt["sourceBeforeSHA256"] = sha256(output / "source-before.json")
        if args.build_log:
            receipt["buildLog"] = {"path": str(args.build_log.resolve()), "sha256": sha256(args.build_log.resolve())}
        receipt["process"] = run_process(
            [str(executable), "--live-public-provider"], repo, output, args.timeout_seconds
        )
        report, errors = validate_report((output / "stdout.json").read_bytes())
        receipt["reportValidationErrors"] = errors
        receipt["providerReport"] = report
        after = source_snapshot(repo, Path(__file__))
        write_json(output / "source-after.json", after)
        receipt["sourceAfterSHA256"] = sha256(output / "source-after.json")
        receipt["sourceStable"] = before["files"] == after["files"] and before["dependencies"] == after["dependencies"]
        receipt["gitHEADBefore"], receipt["gitHEADAfter"] = before["gitHEAD"], after["gitHEAD"]
        receipt["binarySHA256After"] = sha256(executable)
        process = receipt["process"]
        if (report and report["status"] == "PASS" and process.get("exitCode") == 0
                and process.get("parentExited") and not process.get("timedOut")
                and not process.get("runnerErrorType") and not process.get("cleanupErrors")
                and receipt["sourceStable"]
                and receipt["binarySHA256Before"] == receipt["binarySHA256After"]):
            receipt["status"] = "PASS"
    except Exception as error:
        receipt["fatalErrorType"] = type(error).__name__
    finally:
        for name in ("stdout.json", "stderr.log"):
            path = output / name
            if path.is_file():
                receipt[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        write_json(output / "result.json", receipt)
    report = receipt.get("providerReport") or {}
    print(json.dumps({
        "status": receipt["status"], "scope": SCOPE, "count": report.get("count", 0),
        "passed": report.get("passed", 0), "failed": report.get("failed", 0),
        "sourceStable": receipt.get("sourceStable", False),
        "evidence": str(output / "result.json"), "evidenceSHA256": sha256(output / "result.json"),
    }, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
