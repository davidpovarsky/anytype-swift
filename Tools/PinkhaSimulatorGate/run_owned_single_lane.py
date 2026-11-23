"""Bound the existing shared-editor SDK lane without changing its test selection.

The existing lane writes execution.json. This supervisor preserves that receipt,
owns one worker process group, and finishes cleanup before cache publication.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import wave15_batch as owned


LANE = "hanlin-native-shared-editor"
PROTOCOL = "pinkha-owned-single-lane-v1"
PASS = "SUPERVISED_LANE_PASS_ACCEPTANCE_REVIEW_PENDING"


def verify_owned_group_stopped(command_path, *, seconds=10):
    record = json.loads(command_path.read_bytes())
    pgid = record.get("worker_pid")
    owned.require(type(pgid) is int and pgid > 1 and pgid != os.getpgrp()
                  and record.get("owned_group_cleanup") == "TERM_THEN_KILL"
                  and not record.get("cleanup_error_type"),
                  "Owned worker cleanup was not completed")
    deadline = time.monotonic() + seconds
    observations = 0
    timeout_observations = []
    while True:
        remaining = deadline - time.monotonic()
        owned.require(remaining > 0, "Owned process group did not stop within its cleanup budget")
        # Read only numeric identities/state. No process names, global signals
        # or unrelated process-group operations are used.
        probe_timeout = min(2, remaining)
        observations += 1
        try:
            output = subprocess.check_output(["ps", "-axo", "pid=,pgid=,stat="], text=True,
                                             timeout=probe_timeout)
        except subprocess.TimeoutExpired as error:
            timeout_observations.append(dict(observation=observations, timeout_seconds=probe_timeout))
            error.timeout_observations = list(timeout_observations)
            if time.monotonic() >= deadline:
                raise
            continue
        live = []
        for line in output.splitlines():
            fields = line.split()
            owned.require(len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit(),
                          "Unexpected process inventory; cannot prove owned cleanup")
            if int(fields[1]) == pgid and not fields[2].startswith("Z"):
                live.append(int(fields[0]))
        if not live:
            return {"status": "PASS", "pgid": pgid, "live_members": 0, "observations": observations,
                    "timeout_observations": timeout_observations, "budget_seconds": seconds}
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def supervise(command, cwd, evidence, *, context, cleanup, timeout=owned.WORKER_SECONDS):
    evidence.mkdir(parents=True, exist_ok=True)
    destination = evidence / "single-lane-supervisor.json"
    owned.require(not destination.exists(), "Refuse stale supervisor evidence")
    result = dict(protocol=PROTOCOL, lane=LANE, status="FAIL", started_at=owned.now(),
                  full_matrix_accepted=False, release_accepted=False, **context)
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancelled = False
    finalizing = False

    def cancel(signum, frame):
        nonlocal cancelled
        if cancelled:
            return
        cancelled = True
        result["status"] = "CANCELLED"
        if not finalizing:
            raise KeyboardInterrupt("Owned single-lane cancellation")

    for number in previous:
        signal.signal(number, cancel)
    try:
        outcome = owned.run_worker_command(command, cwd, evidence / "single-lane-worker.log", timeout)
        result["worker_command"] = outcome
        original = json.loads((evidence / "execution.json").read_bytes())
        owned.require(all(original.get(key) == context[key]
                          for key in ("source_sha", "run_id", "run_attempt")),
                      "Original worker source/run identity differs")
        result["original_worker_status"] = original.get("status")
        owned.require(outcome["return_code"] == 0
                      and original.get("status") == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING"
                      and original.get("phase") == "COMPLETE", "Original lane has not passed")
        result["status"] = PASS
    except BaseException as error:
        result.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else
                      "TIMED_OUT" if isinstance(error, subprocess.TimeoutExpired) else "FAIL",
                      error_type=type(error).__name__, error=str(error))
        if isinstance(error, KeyboardInterrupt):
            cancelled = True
    finally:
        finalizing = True
        try:
            result["owned_group_quiescence"] = verify_owned_group_stopped(evidence / "single-lane-worker.command.json")
        except BaseException as error:
            result["owned_group_quiescence"] = {"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}
            if isinstance(error, KeyboardInterrupt):
                cancelled = True
            if result["status"] == PASS:
                result["status"] = "FAILED_PROCESS_CLEANUP"
        try:
            result["cleanup"] = cleanup()
        except BaseException as error:
            result.update(cleanup_error_type=type(error).__name__, cleanup_error=str(error))
            if isinstance(error, KeyboardInterrupt):
                cancelled = True
            if result["status"] == PASS:
                result["status"] = "FAILED_CLEANUP"
        try:
            for name in ("execution.json", "single-lane-worker.command.json"):
                path = evidence / name
                if path.exists():
                    result.setdefault("original_evidence", {})[name] = owned.digest(path)
            if cancelled:
                result["status"] = "CANCELLED"
            result["finished_at"] = owned.now()
            owned.write(destination, result)
            # A first signal may arrive while serializing a successful result.
            if cancelled:
                result["status"] = "CANCELLED"
                owned.write(destination, result)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == PASS else 1


def preflight_intent(evidence, context):
    preflight_path = evidence / "preflight/preflight.json"
    preflight = json.loads(preflight_path.read_bytes())
    owned.require(preflight.get("status") == "PREFLIGHT_PASS_UI_NOT_RUN"
                  and all(preflight.get(key) == context[key] for key in context),
                  "Original preflight source/run identity differs")
    selected = preflight.get("selected", {})
    owned.require(set(selected) == {"ipad", "iphone"}, "Original owned simulator pair differs")
    baseline_path = evidence / "preflight/simulator-inventory.json"
    baseline = json.loads(baseline_path.read_bytes())
    baseline_udids = [item["udid"] for items in baseline["devices"].values() for item in items]
    identities = []
    for kind, device in selected.items():
        owned.require(device["name"] == "Pinkha-UI27-" + context["run_id"] + "-" + kind
                      and owned.valid_udid(device.get("udid"))
                      and device["udid"].lower() not in {value.lower() for value in baseline_udids},
                      "Preflight simulator is not newly owned by this run")
        inventory = owned.scoped_device_inventory(device, timeout=30)
        owned.validate_owned_device(inventory, device, expected_state="Shutdown")
        identities.append(device)
    owned.require(len({device["udid"].lower() for device in identities}) == 2,
                  "Preflight simulator identities collide")
    intent = dict(protocol=PROTOCOL, lane=LANE, preflight_devices=identities,
                  lane_devices=[], baseline_udids=baseline_udids,
                  preflight_sha256=owned.digest(preflight_path),
                  baseline_sha256=owned.digest(baseline_path), **context)
    owned.write(evidence / "single-lane-intent.json", intent)
    return intent


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--check-cache-ready":
        evidence = Path(sys.argv[2]).resolve()
        supervisor = json.loads((evidence / "single-lane-supervisor.json").read_bytes())
        command_path = evidence / "single-lane-worker.command.json"
        command = json.loads(command_path.read_bytes())
        quiescence = supervisor.get("owned_group_quiescence", {})
        owned.require(supervisor.get("protocol") == PROTOCOL
                      and supervisor.get("finished_at")
                      and supervisor.get("original_evidence", {}).get(command_path.name) == owned.digest(command_path)
                      and command.get("owned_group_cleanup") == "TERM_THEN_KILL"
                      and not command.get("cleanup_error_type")
                      and quiescence.get("status") == "PASS"
                      and quiescence.get("pgid") == command.get("worker_pid")
                      and quiescence.get("live_members") == 0,
                      "Owned worker group has not finished cleanup; refuse cache publication")
        print("OWNED_WORKER_GROUP_QUIESCENT_CACHE_READY")
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--lane", choices=[LANE], required=True)
    parser.add_argument("--device", choices=["ipad"], required=True)
    parser.add_argument("--language", choices=["en"], required=True)
    parser.add_argument("--runtime-profile", required=True)
    parser.add_argument("--heart-source-run-id", required=True)
    args = parser.parse_args()
    owned.require(sys.platform == "darwin", "Actual Apple host required")
    evidence = args.evidence.resolve()
    owned.require(not any((evidence / name).exists() or (evidence / name).is_symlink()
                          for name in ("execution.json", "single-lane-supervisor.json",
                                       "single-lane-intent.json", "single-lane-worker.log")),
                  "Refuse stale single-lane evidence")
    context = {key: os.environ[variable] for key, variable in
               (("source_sha", "GITHUB_SHA"), ("run_id", "GITHUB_RUN_ID"),
                ("run_attempt", "GITHUB_RUN_ATTEMPT"))}
    owned.require(all(context.values()), "Source/run identity is required")
    intent = preflight_intent(evidence, context)
    command = [sys.executable, "-B", str(Path(__file__).with_name("run_wave15_acceptance.py")),
               "--app", str(args.app.resolve()), "--evidence", str(evidence),
               "--derived", str(args.derived.resolve()), "--lane", args.lane,
               "--device", args.device, "--language", args.language,
               "--runtime-profile", args.runtime_profile, "--heart-source-run-id", args.heart_source_run_id]
    return supervise(command, args.app.resolve(), evidence, context=context,
                     cleanup=lambda: owned.cleanup_owned(intent, evidence))


if __name__ == "__main__":
    raise SystemExit(main())
