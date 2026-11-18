#!/usr/bin/env python3
"""Run the T2 native component and isolated two-process AnySync transport proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HEART_SHA = "d98420b1113536afd08cde6de9a5816f6d27ffff"
GO_VERSION = "go1.26.5"
PACKAGE = "./core/block/editor/torahops"


def output(command: list[str], cwd: Path, env: dict | None = None) -> str:
    return subprocess.check_output(command, cwd=cwd, env=env, text=True, encoding="utf-8").strip()


def run_bounded(command: list[str], cwd: Path, env: dict, log, seconds: int) -> int:
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=os.name != "nt")
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=log, stderr=subprocess.STDOUT, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heart-source", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    app = Path(__file__).resolve().parents[2]
    heart, evidence = args.heart_source.resolve(), args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 2,
        "status": "NOT_RUN",
        "heart_sha_expected": HEART_SHA,
        "app_sha_expected": args.expected_app_sha,
        "platform": platform.platform(),
        "evidence_scope": "native StoreState / any-store component and two-process signed AnySync loopback transport",
        "middleware_acceptance": "NOT_RUN",
        "two_client_transport_acceptance": "NOT_RUN",
        "full_t2_acceptance": "NOT_RUN",
        "ios_acceptance": "NOT_RUN",
        "native_host_rpc_acl_hidden_lifecycle": "NOT_BOUND_TO_APP",
        "native_signed_tree_contract": "NOT_RUN",
        "current_local_read_authority": "NOT_RUN",
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
        "repository": os.environ.get("GITHUB_REPOSITORY"),
    }
    started = time.time()
    code = 1
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha):
            raise ValueError("expected app SHA must be a full immutable commit")
        receipt["app_sha_actual"] = output(["git", "rev-parse", "HEAD"], app)
        receipt["heart_sha_actual"] = output(["git", "rev-parse", "HEAD"], heart)
        if receipt["app_sha_actual"] != args.expected_app_sha or receipt["heart_sha_actual"] != HEART_SHA:
            raise ValueError("source SHA mismatch")
        for source in (app, heart):
            if output(["git", "diff", "HEAD", "--name-only"], source):
                raise ValueError(f"tracked source modifications in {source}")
        overlay = Path(__file__).resolve().parent / "overlay/core/block/editor/torahops"
        files = sorted(overlay.glob("*.go"))
        expected = {"operation.go", "operation_test.go", "projection.go", "store.go", "store_test.go",
                    "native_host.go", "native_transport_test.go", "native_read_authority_test.go"}
        if {p.name for p in files} != expected:
            raise ValueError("unexpected or missing overlay source")
        receipt["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        aggregate = hashlib.sha256()
        for file in files:
            aggregate.update(file.name.encode() + b"\0" + file.read_bytes())
        receipt["overlay_sha256"] = aggregate.hexdigest()
        receipt["go_mod_sha256"] = hashlib.sha256((heart / "go.mod").read_bytes()).hexdigest()
        receipt["go_sum_sha256"] = hashlib.sha256((heart / "go.sum").read_bytes()).hexdigest()
        target = heart / "core/block/editor/torahops"
        if target.exists():
            if {p.name for p in target.iterdir()} != expected or any(
                (target / file.name).read_bytes() != file.read_bytes() for file in files
            ):
                raise ValueError("refusing to overwrite a different native overlay")
        else:
            target.mkdir(parents=True)
            for file in files:
                shutil.copyfile(file, target / file.name)
        go = shutil.which("go")
        if not go:
            raise ValueError("Go executable unavailable")
        env = os.environ.copy()
        env.update(GOMAXPROCS="2", GOMEMLIMIT="1024MiB", GOTOOLCHAIN="local")
        receipt["go_version"] = output([go, "version"], heart, env)
        if receipt["go_version"].split()[2] != GO_VERSION:
            raise ValueError("unexpected Go toolchain")
        command = [go, "test", "-p", "1", "-count=1", "-timeout=240s", "-json", PACKAGE]
        receipt["command"] = command
        receipt["status"] = "RUNNING"
        with (evidence / "go-test.jsonl").open("w", encoding="utf-8", newline="") as log:
            code = run_bounded(command, heart, env, log, seconds=900)
        events = []
        for line in (evidence / "go-test.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # compiler/download messages remain verbatim in the log
        receipt["passed_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "pass" and e.get("Test"))
        receipt["failed_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "fail" and e.get("Test"))
        receipt["skipped_tests"] = sorted(e["Test"] for e in events if e.get("Action") == "skip" and e.get("Test"))
        package_pass = any(e.get("Action") == "pass" and not e.get("Test") for e in events)
        required = {"TestNativeTwoProcessTreeSync", "TestNativeHostRejectsUnboundAuthorityAndInvalidHistory",
                    "TestNativeCurrentReadAuthority"}
        if code == 0 and package_pass and required.issubset(receipt["passed_tests"]) and not receipt["failed_tests"]:
            receipt["status"] = "PASS_NATIVE_COMPONENT_AND_LOOPBACK_TRANSPORT"
            receipt["two_client_transport_acceptance"] = "PASS_ISOLATED_LOOPBACK_PROTOCOL_ONLY"
            receipt["native_signed_tree_contract"] = "PASS_ISOLATED_NATIVE_HOST"
            receipt["current_local_read_authority"] = "PASS_CURRENT_LOCALLY_VERIFIED_ACL"
        else:
            receipt["status"] = "FAIL"
            code = code or 1
        receipt["returncode"] = code
    except Exception as exc:
        code = 1
        receipt["status"] = "FAIL" if receipt["status"] == "RUNNING" else "NOT_RUN_PREFLIGHT_FAILED"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["returncode"] = 1
        print(receipt["error"], file=sys.stderr)
    finally:
        receipt["elapsed_seconds"] = round(time.time() - started, 3)
        receipt["evidence_sha256"] = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(evidence.glob("*.jsonl"))
        }
        (evidence / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
