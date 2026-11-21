#!/usr/bin/env python3
"""Retain the original account-wire baseline, then run three separately composed races.

The instrumented binary is a test artifact only. Its result cannot replace the
unmodified four-process baseline or establish iOS, new-engine or full T2 parity.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
from uuid import uuid4

import run_account_lifecycle as base
import run_account_rpc as account

PROTOCOL = "pinkha-t2-generated-byte-lifecycle-races-v1"
METHOD = "TestT2GeneratedByteLifecycleRaces"
PASS = "PASS_NATIVE_GENERATED_BYTE_LIFECYCLE_RACES"
NATIVE_PASS = "PASS_ORIGINAL_NATIVE_LOG_AND_THREE_CASE_REPORT"
PRODUCT_BASE = "16b7493fa05bdc3abbae190c6e6c364c81874eea"
CANDIDATE_SHA = "b021c51a0541a4603036a579bb339318d15e6fbb0f100cd913db480aa3259799"
LANE_MANIFEST_SHA = "e2d66b4d480fd6f19ded13513406382ac279d85eeda6272d89af549ff6bf5546"
SCOPE = "original four-process generated-byte baseline plus three test-instrumented real-account lifecycle races"
CASES = {"delete_wins_first_add", "commit_wins_block_delete", "commit_wins_account_stop"}
LIMITS = {"app_capability": "OFF", "generated_byte_cancellation": "NOT_EXPOSED_NOT_CLAIMED",
          "settings_delete": "NOT_RUN", "standalone_space_close": "NOT_RUN", "account_switch": "NOT_RUN",
          "new_engine_parity": "NOT_PROVEN"}
require, digest, write_json = base.require, base.digest, base.write_json


def source_inputs(control: Path) -> dict:
    tools = control / "Tools/TorahNativeOperations"
    path = tools / "account_rpc_lifecycle_lane.json"
    require(digest(path) == LANE_MANIFEST_SHA, "Reviewed lifecycle lane manifest differs")
    value = json.loads(path.read_text())
    require(value.get("protocol") == PROTOCOL and value.get("product_base_sha") == PRODUCT_BASE
            and value.get("heart_sha") == base.HEART and value.get("candidate_sha256") == CANDIDATE_SHA
            and value.get("method") == METHOD, "Wrong reviewed lifecycle source contract")
    actual = {}
    for group in ["base_inputs_sha256", "candidate_inputs_sha256"]:
        require(isinstance(value.get(group), dict) and value[group], "Missing source input inventory")
        for name, expected in value[group].items():
            target = tools / base.relative(name)
            require(target.resolve().is_relative_to(tools) and digest(target) == expected,
                    "Reviewed lifecycle source input differs")
            actual[name] = expected
    require(actual.get("account_rpc_lifecycle/candidate.json") == CANDIDATE_SHA,
            "Missing exact reviewed test composition")
    return {"product_base_sha": PRODUCT_BASE, "candidate_sha256": CANDIDATE_SHA,
            "lane_manifest_sha256": digest(path), "files_sha256": actual}


def identifier(value) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 512 and not any(ch.isspace() for ch in value)


def hash_value(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_trace(value: dict, stages: list[str]) -> list[dict]:
    require(isinstance(value, dict) and set(value) == {"events", "counts", "gate_timeouts"}
            and value["gate_timeouts"] == [], "Missing or timed-out native lifecycle trace")
    counts, events = value["counts"], value["events"]
    require(isinstance(counts, dict) and set(counts) == set(stages)
            and all(type(v) is int and v == 1 for v in counts.values()), "Repeated or missing lifecycle stage")
    require(isinstance(events, list) and len(events) == len(stages), "Incomplete native event order")
    for index, (event, stage) in enumerate(zip(events, stages), 1):
        require(isinstance(event, dict) and set(event) == {"sequence", "stage", "id", "qualifier"}
                and type(event["sequence"]) is int and event["sequence"] == index and event["stage"] == stage,
                "Unexpected native event sequence")
        expected_qualifier = ("write" if stage in {"prelease", "append-native-return"}
                              else "basic.Unlinkable" if stage.startswith("delete-lock-") else "")
        require(event["qualifier"] == expected_qualifier, "Wrong native lock or operation interface")
        require(event["id"] == "" if stage in {"app-lease-held", "stop-lock-attempt", "stop-lock-acquired"}
                else identifier(event["id"]), "Wrong lifecycle target identity")
    return events


def validate_history(values: dict, heads: list, count: int, root: str) -> None:
    require(isinstance(values, dict) and len(values) == count and root in values
            and all(identifier(key) and hash_value(value) for key, value in values.items()),
            "Incomplete actual signed-history hashes")
    require(isinstance(heads, list) and len(heads) == 1 and heads[0] in values and heads[0] != root,
            "Wrong actual signed-history head")


def validate_report(report: dict, nonce: str, pid: int) -> None:
    expected = {"protocol", "nonce", "pid", "heart_sha", "fixture_sha256", "status", "cases",
                "account_stop_verified", "instrumentation", *LIMITS}
    require(isinstance(report, dict) and set(report) == expected, "Unknown native lifecycle report schema")
    require(report["protocol"] == PROTOCOL and report["nonce"] == nonce
            and type(report["pid"]) is int and report["pid"] == pid and pid > 0
            and report["heart_sha"] == base.HEART and report["fixture_sha256"] == CANDIDATE_SHA,
            "Native report does not bind this process/source/nonce")
    require(report["status"] == "PASS_THREE_REAL_ACCOUNT_BYTE_LIFECYCLE_CASES"
            and report["account_stop_verified"] is True
            and report["instrumentation"] == "SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT"
            and all(report[key] == value for key, value in LIMITS.items()), "Incomplete or overstated lifecycle result")
    cases = report["cases"]
    require(isinstance(cases, dict) and set(cases) == CASES, "All three actual lifecycle cases are required")
    require(all(isinstance(case, dict) and hash_value(case.get("request_sha256")) for case in cases.values())
            and len({case["request_sha256"] for case in cases.values()}) == 3, "Distinct original generated requests required")
    first = cases["delete_wins_first_add"]
    require(set(first) == {"trace", "request_sha256", "response", "private_root"}
            and first["response"] == "TARGET_UNAVAILABLE_NO_RECEIPT" and first["private_root"] == "ABSENT",
            "Rejected first append installed a root or returned a receipt")
    validate_trace(first["trace"], ["prelease"])
    deleted = cases["commit_wins_block_delete"]
    require(set(deleted) == {"trace", "request_sha256", "raw_changes_sha256", "heads", "private_history_count",
                            "target_pointer_identity", "post_delete_read_and_retry"}
            and type(deleted["private_history_count"]) is int and deleted["private_history_count"] == 3
            and deleted["target_pointer_identity"] == "EXACT_SAME_LIVE_SMARTBLOCK"
            and deleted["post_delete_read_and_retry"] == "TARGET_UNAVAILABLE_NO_RESULT", "Incomplete actual deletion boundary")
    events = validate_trace(deleted["trace"], ["commit-before-storage", "delete-lock-attempt",
                                              "commit-after-storage", "delete-lock-acquired"])
    require(events[0]["id"] == events[2]["id"] and events[1]["id"] == events[3]["id"]
            and events[0]["id"] != events[1]["id"], "Commit/deletion did not use the same observed objects")
    validate_history(deleted["raw_changes_sha256"], deleted["heads"], 3, events[0]["id"])
    stopped = cases["commit_wins_account_stop"]
    require(set(stopped) == {"trace", "request_sha256", "raw_changes_sha256_before_append", "heads_before_append",
                            "raw_changes_sha256_at_durable_boundary", "heads_at_durable_boundary",
                            "application_service_identity", "account_stop", "after_stop_read_and_retry"}
            and stopped["application_service_identity"] == "EXACT_SAME_LIVE_INSTANCE"
            and stopped["account_stop"] == "PASS_ORIGINAL_STOP"
            and stopped["after_stop_read_and_retry"] == "NOT_LOGGED_IN_NO_RESULT", "Incomplete original account Stop")
    events = validate_trace(stopped["trace"], ["app-lease-held", "commit-before-storage", "stop-lock-attempt",
                                              "commit-after-storage", "append-native-return", "stop-lock-acquired"])
    require(events[1]["id"] == events[3]["id"] and events[1]["id"] != events[4]["id"],
            "Account Stop observed a different private root")
    before, after = stopped["raw_changes_sha256_before_append"], stopped["raw_changes_sha256_at_durable_boundary"]
    validate_history(before, stopped["heads_before_append"], 2, events[1]["id"])
    validate_history(after, stopped["heads_at_durable_boundary"], 3, events[1]["id"])
    require(all(after.get(key) == value for key, value in before.items())
            and stopped["heads_at_durable_boundary"][0] not in before,
            "Original signed history was replaced or no new durable head was committed")


def validate_test_log(path: Path) -> None:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    require(sum(line == "=== RUN   " + METHOD for line in lines) == 1
            and sum(bool(re.fullmatch(r"--- PASS: " + METHOD + r" \([0-9.]+s\)", line)) for line in lines) == 1
            and sum(line.startswith("--- PASS:") for line in lines) == 1
            and not any("--- SKIP:" in line or "--- FAIL:" in line for line in lines)
            and lines.count("PASS") == 1, "Missing exact original named native PASS")


def native_snapshot(heart: Path, build: dict) -> dict:
    require(base.git(heart, "rev-parse", "HEAD") == base.HEART, "Wrong native Heart checkout")
    hashes = {name: digest(heart / base.relative(name)) for name in build["source_hashes"]}
    require(hashes == build["source_hashes"] and all(digest(heart / name) == value
            for name, value in build["module_hashes"].items()), "Native source changed after original baseline")
    return {"source_hashes": hashes, "module_hashes": build["module_hashes"],
            "tracked_changes": base.git(heart, "diff", "--name-only", "HEAD").splitlines(),
            "untracked_files": base.git(heart, "ls-files", "--others", "--exclude-standard").splitlines()}


def preserve_evidence(work: Path, destination: Path) -> dict:
    require(not destination.exists(), "Fresh lifecycle evidence destination required")
    candidates = [work / "ownership.json", work / "result.json"]
    secret = work / "sensitive-needles.private"
    needles = []
    if secret.is_file() and not secret.is_symlink():
        require(secret.stat().st_mode & 0o077 == 0, "Synthetic secret inventory is not private")
        values = json.loads(secret.read_text())
        require(isinstance(values, list) and len(values) == 2 and all(isinstance(v, str) and v for v in values),
                "Incomplete synthetic secret inventory")
        needles = [value.encode() for value in values]
        candidates += [work / "lifecycle.json", work / "native.log"]
    existing = [path for path in candidates if path.exists() or path.is_symlink()]
    for path in existing:
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(work)
                and path.stat().st_size <= 32 * 1024**2, "Unsafe lifecycle evidence file")
        require(not any(needle in path.read_bytes() for needle in needles), "Synthetic secret found; all lifecycle evidence withheld")
    destination.mkdir(mode=0o755)
    result = {}
    for path in existing:
        target = destination / path.name
        shutil.copyfile(path, target)
        target.chmod(0o644)
        result[path.name] = digest(target)
    return {"secret_scan": "PASS" if needles else "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY", "files_sha256": result}


def run_races(identity: dict, work: Path, evidence: Path, baseline_pids: set[int]) -> dict:
    work.mkdir(mode=0o700)
    owner = {"protocol": PROTOCOL, "nonce": str(uuid4()), "synthetic_only": True}
    write_json(work / "ownership.json", owner)
    owner_bytes = (work / "ownership.json").read_bytes()
    root = work / "account-root"
    root.mkdir(mode=0o700)
    nonce = str(uuid4())
    private = {"status": "NOT_RUN", "protocol": PROTOCOL, "nonce": nonce,
               "binary_sha256": identity["binary_sha256"], "candidate_sha256": CANDIDATE_SHA,
               "launch_requested": False, "native_processes": 0, "process_exit_observed": None,
               "passing_test_invocations": 0, "cases": 0}
    result = None
    try:
        require(shutil.disk_usage(work).free >= base.RESERVE, "Disk reserve below 8 GiB")
        require(digest(Path(identity["binary"])) == identity["binary_sha256"], "Race binary changed before execution")
        env = dict(os.environ, PINKHA_T2_LIFECYCLE_ROOT=str(root), PINKHA_T2_LIFECYCLE_REPORT=str(work / "lifecycle.json"),
                   PINKHA_T2_LIFECYCLE_NONCE=nonce, PINKHA_T2_LIFECYCLE_FIXTURE_SHA=CANDIDATE_SHA,
                   PINKHA_T2_LIFECYCLE_OWNER_TOKEN=owner_bytes.decode(), GOMAXPROCS="2")
        command = [identity["binary"], "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"]
        # The unchanged baseline supervisor returns its PID only after exit 0.
        # A failed/timeout/cancelled call may already have spawned a child, so
        # zero is no longer an honest process count once launch is requested.
        private.update(status="RUNNING", command=command, launch_requested=True, native_processes=None)
        write_json(work / "result.json", private)
        pid = base.run_process(command, work, env, work / "native.log", 330)
        private.update(pid=pid, native_processes=1, process_exit_observed=True)
        require(pid not in baseline_pids, "Additional lifecycle process must be distinct from original baseline")
        validate_test_log(work / "native.log")
        validate_report(json.loads((work / "lifecycle.json").read_text()), nonce, pid)
        require(digest(Path(identity["binary"])) == identity["binary_sha256"], "Race binary changed during execution")
        private.update(status=NATIVE_PASS, passing_test_invocations=1, cases=3)
        result = {"actual_counts": {"native_processes": 1, "passing_test_invocations": 1, "cases": 3},
                  "native_pid": pid, "native_report_sha256": digest(work / "lifecycle.json")}
    except BaseException as exc:
        private.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error_type=type(exc).__name__)
        raise
    finally:
        write_json(work / "result.json", private)
        try:
            copied = preserve_evidence(work, evidence / "lifecycle-sequence")
            write_json(evidence / "lifecycle-evidence-copy.json", copied)
            if private["status"] == NATIVE_PASS:
                require(copied["secret_scan"] == "PASS" and set(copied["files_sha256"]) == {
                    "ownership.json", "result.json", "lifecycle.json", "native.log"},
                        "Native success lacks its original secret-scanned evidence")
        finally:
            require(work.is_dir() and not work.is_symlink() and (work / "ownership.json").read_bytes() == owner_bytes,
                    "Owned lifecycle directory identity changed; cleanup refused")
            shutil.rmtree(work)
            write_json(evidence / "lifecycle-cleanup.json", {"status": "PASS_REMOVED_OWNED_DISPOSABLE_ACCOUNT",
                       "protocol": PROTOCOL, "owner_nonce": owner["nonce"], "path_absent": not work.exists(),
                       "process_exit_observed": private["process_exit_observed"]})
    return result


def execute(args, receipt, run) -> dict:
    control = Path(__file__).resolve().parents[2]
    tools = control / "Tools/TorahNativeOperations"
    inputs = source_inputs(control)
    receipt["source_inputs"] = inputs
    baseline_receipt = {"status": "NOT_RUN", "run_id": receipt["run_id"], "run_attempt": receipt["run_attempt"],
                        "workflow_ref": receipt["workflow_ref"], "app_sha": args.expected_app_sha,
                        "scope": account.SCOPE, "app_capability": "OFF", "commands": []}
    def baseline_run(command, name, cwd, env, timeout=900):
        return run(command, name, cwd, env, timeout, target=baseline_receipt, filename="receipt.json")
    try:
        baseline = account.execute(args, baseline_receipt, baseline_run)
        baseline_receipt.update(baseline)
        require(baseline["status"] == account.PASS and baseline["actual_counts"] == {
            "binaries": 2, "native_processes": 4, "passing_test_invocations": 4, "actual_export_files": 8},
                "Unmodified four-process account-wire baseline did not pass")
    except BaseException as exc:
        baseline_receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error_type=type(exc).__name__)
        raise
    finally:
        write_json(args.evidence / "receipt.json", baseline_receipt)
    receipt["baseline"] = {"status": baseline["status"], "actual_counts": baseline["actual_counts"],
                           "receipt_sha256": digest(args.evidence / "receipt.json"),
                           "account_receipt_sha256": baseline["account_receipt_sha256"]}
    hearts = {"new": args.heart_new, "legacy": args.heart_legacy}
    builds = {role: json.loads((args.evidence / (role + "-build.json")).read_text()) for role in hearts}
    snapshots = {role: native_snapshot(heart, builds[role]) for role, heart in hearts.items()}
    initial_bindings = {name: digest(args.evidence / name) for name in ["new-build.json", "legacy-build.json", "receipt.json",
                                                                   "generation/generation-receipt.json"]}
    original_overlay = args.work / "build-new/overlay.json"
    original_overlay_sha = digest(original_overlay)
    original_fixtures = {name: digest(Path(name)) for name in json.loads(original_overlay.read_text())["Replace"].values()}
    directory = args.work / "lifecycle-build"
    directory.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location("t2_lifecycle_materializer", tools / "account_rpc_lifecycle/materialize_test_overlay.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    overlay = directory / "overlay.json"
    composed = helper.prepare(args.heart_new, original_overlay, overlay)
    require(composed["candidate_sha256"] == CANDIDATE_SHA and composed["added_overlay_entries"] == 7
            and composed["product_source_mutations"] == 0, "Wrong test-only lifecycle composition")
    source = baseline["identities"]["new"]
    registration, schema = source["registration_patch_sha256"], source["rpc_manifest_sha256"]
    flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + base.HEART
             + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + source["runtime_version"]
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountFixtureSHA=" + source["fixture_sha256"]
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRuntimeRole=new"
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRegistrationSHA=" + registration
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2RPCAccountSchemaSHA=" + schema
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2LifecycleFixtureSHA=" + CANDIDATE_SHA)
    gowork = args.work / "build-new/go.work"
    gowork_sha = digest(gowork)
    env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2", GOMEMLIMIT="2048MiB",
               GOFLAGS="-mod=readonly", GOPROXY="off", CGO_LDFLAGS="-L" + str(args.heart_new / "deps/libs/linux-amd64-musl"))
    binary = directory / "pinkha-t2-rpc-lifecycle.test"
    require(shutil.disk_usage(directory).free >= base.RESERVE, "Disk reserve below 8 GiB")
    run(["go", "test", "-c", "-p", "1", "-tags", base.TAGS, "-overlay", str(overlay), "-ldflags", flags,
         "-o", str(binary), "./clientlibrary/service"], "lifecycle-compile", args.heart_new, env, 1800)
    identity = {**source, "binary": str(binary), "binary_sha256": digest(binary), "candidate_sha256": CANDIDATE_SHA,
                "scope": "SEPARATE_TEST_INSTRUMENTED_BINARY", "original_new_binary_sha256": source["binary_sha256"]}
    account.verify_rpc_binary("new", identity, registration, schema)
    require(identity["binary_sha256"] not in {value["binary_sha256"] for value in baseline["identities"].values()}
            and base.contains(binary, CANDIDATE_SHA) and base.contains(binary, METHOD), "Missing distinct linked lifecycle test")
    require(source_inputs(control) == inputs and digest(original_overlay) == original_overlay_sha
            and all(digest(Path(name)) == sha for name, sha in original_fixtures.items()),
            "Reviewed fixture or original overlay changed during compilation")
    for role, heart in hearts.items():
        require(native_snapshot(heart, builds[role]) == snapshots[role], "Instrumented build mutated original native sources")
    write_json(args.evidence / "lifecycle-build.json", {"identity": identity, "composition": composed,
               "source_inputs": inputs, "original_build_bindings": initial_bindings,
               "overlay": json.loads(overlay.read_text()), "original_fixture_sha256": original_fixtures,
               "gowork_sha256": gowork_sha})
    sequence = json.loads((args.evidence / "account-sequence/result.json").read_text())
    pids = {phase["pid"] for phase in sequence["phase_reports"]}
    require(len(pids) == 4, "Original account baseline process identity is incomplete")
    raced = run_races(identity, args.work / "lifecycle-sequence", args.evidence, pids)
    for role, heart in hearts.items():
        account.verify_rpc_binary(role, baseline["identities"][role], registration, schema)
        require(native_snapshot(heart, builds[role]) == snapshots[role], "Native source changed during lifecycle execution")
    require(source_inputs(control) == inputs and digest(gowork) == gowork_sha
            and digest(overlay) == composed["composed_overlay_sha256"] and digest(original_overlay) == original_overlay_sha
            and all(digest(Path(name)) == sha for name, sha in original_fixtures.items())
            and all(digest(args.evidence / name) == sha for name, sha in initial_bindings.items()),
            "Lifecycle run changed its original source/build/baseline binding")
    for root, pin in [(control, args.expected_app_sha), (args.approved_source, base.APPROVED_SOURCE)]:
        require(base.git(root, "rev-parse", "HEAD") == pin and not base.git(root, "status", "--porcelain"), "Control input changed")
    return {"status": PASS, "lifecycle": raced, "instrumented_identity": identity,
            "original_account_baseline": "PASS_UNMODIFIED_FOUR_PROCESSES_AND_EIGHT_EXPORTS",
            "source_after_execution": "PASS_UNCHANGED_PRODUCT_AND_EXACT_TEST_COMPOSITION",
            "artifact_runtime_binary_bytes": "NOT_RETAINED_BUILD_AND_PHASE_RECEIPTS_ONLY"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args(argv)
    for name in ["approved_source", "heart_legacy", "heart_new", "work", "evidence"]:
        setattr(args, name, getattr(args, name).resolve())
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "lifecycle-receipt.json"
    require(not path.exists() and not (args.evidence / "receipt.json").exists(), "Fresh lifecycle lane evidence required")
    receipt = {"status": "NOT_RUN_PREFLIGHT", "protocol": PROTOCOL, "scope": SCOPE, "app_sha": args.expected_app_sha,
               "product_base_sha": PRODUCT_BASE, "run_id": os.environ.get("GITHUB_RUN_ID"),
               "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
               "commands": [], "started_at": datetime.now(timezone.utc).isoformat(), **LIMITS,
               "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
    previous = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}
    cancelled = False
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous:
        signal.signal(number, cancel)
    def run(command, name, cwd, env, timeout=900, *, target=None, filename="lifecycle-receipt.json"):
        target = receipt if target is None else target
        destination = args.evidence / filename
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}
        target["commands"].append(entry)
        write_json(destination, target)
        try:
            entry["pid"] = base.run_process(entry["argv"], cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
            return entry["pid"]
        except BaseException as exc:
            entry["status"] = "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            write_json(destination, target)
    result = 1
    try:
        write_json(path, receipt)
        receipt.update(execute(args, receipt, run))
        result = 0
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error_type=type(exc).__name__)
        print(type(exc).__name__ + ": native lifecycle evidence did not satisfy its reviewed contract", file=sys.stderr)
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            write_json(path, receipt)
            for item in args.evidence.rglob("*"):
                if item.is_dir():
                    item.chmod(0o755)
                elif item.is_file() and not item.is_symlink():
                    item.chmod(0o644)
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
