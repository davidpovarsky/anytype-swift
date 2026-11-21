#!/usr/bin/env python3
"""Run the original account-wire baseline, then close/reopen one separate account.

The new binary is explicitly instrumented only for this native Space.Close
proof. It never replaces the four-process baseline or the prior three races.
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
import subprocess
import sys
from uuid import uuid4

import run_account_lifecycle as base
import run_account_rpc as account
import run_account_rpc_lifecycle as accepted

PROTOCOL = "pinkha-t2-generated-byte-space-close-v1"
METHOD = "TestT2GeneratedByteSpaceClose"
PASS = "PASS_NATIVE_GENERATED_BYTE_SPACE_CLOSE_AND_COLD_REOPEN"
PRODUCT_BASE = "16b7493fa05bdc3abbae190c6e6c364c81874eea"
CANDIDATE_SHA = "994107eacbc2e09335fac38f34d2f3e626cb048bbc87ce25cbe7a9af040f7f0a"
LANE_MANIFEST_SHA = "fe55fe1c3d95d462dd7b4f75f720634ac7450da7a01eb80aa290078c796974be"
PHASES = ("race", "reopen")
SCOPE = "original four-process generated-byte baseline plus one real Space.Close race and one cold reopen"
LIMITS = {"app_capability": "OFF", "response_return_order_relative_to_close": "NOT_ASSERTED",
          "duplicate_close_completion": "NOT_CLAIMED", "settings_delete": "NOT_RUN",
          "account_switch": "NOT_RUN", "new_engine_parity": "NOT_PROVEN"}
STAGES = {
    "lease-settings-held": "", "append-before-native": "",
    "cache-entry-closing-target": "", "cache-entry-closing-private": "",
    "cache-deadline-target": "DEADLINE_EXCEEDED", "cache-deadline-private": "DEADLINE_EXCEEDED",
    "client-cache-close-return": "OK", "settings-close-attempt": "",
    "commit-before-storage": "", "commit-after-storage": "OK", "lease-before-release": "",
    "settings-close-return": "OK", "native-storage-close-attempt": "",
    "native-storage-close-return": "OK", "client-space-close-return": "OK",
}
ORDERS = [
    ["lease-settings-held", "append-before-native", "cache-entry-closing-target", "cache-entry-closing-private"],
    ["cache-entry-closing-private", "cache-deadline-target", "client-cache-close-return"],
    ["cache-entry-closing-private", "cache-deadline-private", "client-cache-close-return"],
    ["client-cache-close-return", "settings-close-attempt", "commit-before-storage", "commit-after-storage",
     "lease-before-release", "settings-close-return", "native-storage-close-attempt",
     "native-storage-close-return", "client-space-close-return"],
]
require, digest, write_json = base.require, base.digest, base.write_json
identifier, hash_value = accepted.identifier, accepted.hash_value


def source_inputs(control):
    tools = control / "Tools/TorahNativeOperations"
    path = tools / "account_rpc_space_close_lane.json"
    require(digest(path) == LANE_MANIFEST_SHA, "Reviewed Space.Close lane manifest differs")
    value = json.loads(path.read_text())
    require(value.get("protocol") == PROTOCOL and value.get("product_base_sha") == PRODUCT_BASE
            and value.get("heart_sha") == base.HEART and value.get("candidate_sha256") == CANDIDATE_SHA
            and value.get("method") == METHOD and value.get("phases") == list(PHASES),
            "Wrong reviewed Space.Close source contract")
    actual = {}
    for group in ["base_inputs_sha256", "candidate_inputs_sha256"]:
        require(isinstance(value.get(group), dict) and value[group], "Missing exact source inventory")
        for name, expected in value[group].items():
            target = tools / base.relative(name)
            require(name not in actual and target.resolve(strict=True).is_relative_to(tools)
                    and digest(target) == expected, "Reviewed Space.Close source input differs")
            actual[name] = expected
    require(actual.get("account_rpc_space_close/candidate.json") == CANDIDATE_SHA,
            "Missing exact reviewed native composition")
    return {"product_base_sha": PRODUCT_BASE, "candidate_sha256": CANDIDATE_SHA,
            "lane_manifest_sha256": digest(path), "files_sha256": actual}


def validate_trace(value, report):
    require(isinstance(value, dict) and set(value) == {
        "events", "counts", "gate_timeouts", "gate_cancellations", "overflow"}
        and value["gate_timeouts"] == [] and value["gate_cancellations"] == []
        and value["overflow"] is False, "Incomplete, cancelled or timed-out native Space.Close trace")
    events, counts = value["events"], value["counts"]
    require(isinstance(events, list) and len(events) == len(STAGES) and isinstance(counts, dict)
            and set(counts) == set(STAGES) and all(type(n) is int and n == 1 for n in counts.values()),
            "Every original Space.Close stage must occur exactly once")
    positions, identities = {}, {}
    for index, event in enumerate(events, 1):
        require(isinstance(event, dict) and set(event) == {"sequence", "stage", "id", "result"}
                and type(event["sequence"]) is int and event["sequence"] == index
                and event["stage"] in STAGES and event["stage"] not in positions
                and event["result"] == STAGES[event["stage"]] and identifier(event["id"]),
                "Wrong original Space.Close event")
        positions[event["stage"]], identities[event["stage"]] = index, event["id"]
    for sequence in ORDERS:
        require(all(positions[a] < positions[b] for a, b in zip(sequence, sequence[1:])),
                "Native lifetime or durable-write ordering differs")
    settings_id = identities["lease-settings-held"]
    require(settings_id not in {report["private_root_id"], report["target_id"], report["space_id"]},
            "Settings fence is not a distinct native object")
    for stage, actual in identities.items():
        if stage in {"lease-settings-held", "settings-close-attempt", "settings-close-return", "lease-before-release"}:
            expected = settings_id
        elif stage in {"cache-entry-closing-target", "cache-deadline-target"}:
            expected = report["target_id"]
        elif stage in {"append-before-native", "cache-entry-closing-private", "cache-deadline-private",
                       "commit-before-storage", "commit-after-storage"}:
            expected = report["private_root_id"]
        else:
            expected = report["space_id"]
        require(actual == expected, "Space.Close observation used a foreign native object")


def validate_report(report, phase, nonce, pid):
    expected = {"protocol", "phase", "nonce", "pid", "heart_sha", "fixture_sha256", "status", "account_id",
                "space_id", "target_id", "block_id", "private_root_id", "request_sha256", "state_sha256",
                "created_claim_id", "created_change_id", "observation", "account_stop_verified",
                "app_shutdown_verified", "instrumentation", *LIMITS}
    require(isinstance(report, dict) and set(report) == expected and phase in PHASES,
            "Unknown native Space.Close report schema")
    require(report["protocol"] == PROTOCOL and report["phase"] == phase and report["nonce"] == nonce
            and type(report["pid"]) is int and report["pid"] == pid and pid > 0
            and report["heart_sha"] == base.HEART and report["fixture_sha256"] == CANDIDATE_SHA,
            "Native report is not bound to this exact process/phase/source/nonce")
    require(report["status"] == "PASS_ORIGINAL_NATIVE_SPACE_CLOSE_PHASE"
            and report["account_stop_verified"] is True and report["app_shutdown_verified"] is True
            and report["instrumentation"] == "SEPARATE_PINNED_TEST_COMPILE_OVERLAY_NOT_SHIPPED_PRODUCT"
            and all(report[key] == value for key, value in LIMITS.items()), "Incomplete or overstated Space.Close result")
    require(all(identifier(report[key]) for key in ["account_id", "space_id", "target_id", "block_id",
                                                  "private_root_id", "created_claim_id", "created_change_id"])
            and len({report[key] for key in ["space_id", "target_id", "private_root_id"]}) == 3
            and all(hash_value(report[key]) for key in ["request_sha256", "state_sha256"]),
            "Incomplete original account/Space/claim identity")
    observation = report["observation"]
    require(isinstance(observation, dict), "Original phase observation required")
    if phase == "race":
        require(set(observation) == {"trace", "identity_checks", "cache_close_timeout_seconds",
            "both_entries_closing_before_controller_close", "settings_fence_observed_before_and_after_durable_commit",
            "post_physical_close_read", "native_append", "original_controller_close_calls",
            "raced_generated_append_calls", "raw_changes_sha256_before_append", "heads_before_append",
            "raw_changes_sha256_at_durable_boundary", "heads_at_durable_boundary"}, "Wrong race observation schema")
        require(observation["identity_checks"] == "ALL_EIGHT_PAIRS_EXACT_SAME_LIVE_INSTANCE"
                and type(observation["cache_close_timeout_seconds"]) is int and observation["cache_close_timeout_seconds"] == 10
                and observation["both_entries_closing_before_controller_close"] is True
                and observation["settings_fence_observed_before_and_after_durable_commit"] is True
                and observation["post_physical_close_read"] == "DENIED_WITH_LIVE_PROBE_CONTEXT"
                and observation["native_append"] == "CREATED_ORIGINAL_RESPONSE"
                and all(type(observation[key]) is int and observation[key] == 1
                        for key in ["original_controller_close_calls", "raced_generated_append_calls"]),
                "Native controller close/durable-write fence was not observed")
        validate_trace(observation["trace"], report)
        before, after = observation["raw_changes_sha256_before_append"], observation["raw_changes_sha256_at_durable_boundary"]
        accepted.validate_history(before, observation["heads_before_append"], 2, report["private_root_id"])
        accepted.validate_history(after, observation["heads_at_durable_boundary"], 3, report["private_root_id"])
        require(all(after.get(key) == value for key, value in before.items())
                and report["created_change_id"] not in before
                and observation["heads_at_durable_boundary"] == [report["created_change_id"]],
                "No exact new durable commit or original signed history was replaced")
    else:
        require(set(observation) == {"raw_changes_sha256_before_retry", "heads_before_retry",
            "raw_changes_sha256_after_retry", "heads_after_retry", "read_before_retry", "original_byte_retry",
            "read_after_retry", "original_request_forwards"}, "Wrong cold-reopen observation schema")
        require(observation["read_before_retry"] == "TWO_EXACT_PERSISTED_CLAIMS_LOCAL_VERIFIED_TREE"
                and observation["original_byte_retry"] == "ALREADY_EXISTS_SAME_PAYLOAD_NO_CHANGE_ID"
                and observation["read_after_retry"] == "PROTO_EQUAL_INCLUDING_LOCAL_WATERMARK"
                and type(observation["original_request_forwards"]) is int and observation["original_request_forwards"] == 1,
                "Cold reopen or exact original byte retry was not proved")
        for suffix in ["before_retry", "after_retry"]:
            accepted.validate_history(observation["raw_changes_sha256_" + suffix], observation["heads_" + suffix],
                                      3, report["private_root_id"])
            require(observation["heads_" + suffix] == [report["created_change_id"]], "Reopened a different durable head")
        require(observation["raw_changes_sha256_before_retry"] == observation["raw_changes_sha256_after_retry"]
                and observation["heads_before_retry"] == observation["heads_after_retry"], "Exact retry mutated native history")


def validate_pair(race, reopened):
    require(race["pid"] != reopened["pid"] and race["nonce"] != reopened["nonce"],
            "Cold reopen requires a separate original process and invocation")
    for key in ["account_id", "space_id", "target_id", "block_id", "private_root_id", "request_sha256",
                "state_sha256", "created_claim_id", "created_change_id", "heart_sha", "fixture_sha256"]:
        require(race[key] == reopened[key], "Reopen substituted the original account, request or native history")
    a, b = race["observation"], reopened["observation"]
    require(a["raw_changes_sha256_at_durable_boundary"] == b["raw_changes_sha256_before_retry"]
            and a["heads_at_durable_boundary"] == b["heads_before_retry"],
            "Cold reopen did not retain the actual original signed-history bytes")


def validate_test_log(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    require(lines.count("=== RUN   " + METHOD) == 1
            and sum(bool(re.fullmatch(r"--- PASS: " + METHOD + r" \([0-9.]+s\)", line)) for line in lines) == 1
            and sum(line.startswith("--- PASS:") for line in lines) == 1
            and not any("--- SKIP:" in line or "--- FAIL:" in line for line in lines)
            and lines.count("PASS") == 1, "Missing exact original named native Space.Close PASS")


def run_owned(command, cwd, env, log, timeout, entry, checkpoint):
    """Retain launch/PID/exit evidence even when native execution fails."""
    require(os.name == "posix" and not log.exists(), "Fresh Linux command log required")
    entry.update(argv=list(map(str, command)), status="LAUNCH_REQUESTED", launch_requested=True,
                 pid=None, exit_code=None, process_exit_observed=False)
    checkpoint()
    process = None
    with log.open("xb") as stream:
        try:
            process = subprocess.Popen(entry["argv"], cwd=cwd, env=env, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            entry.update(status="STARTED", pid=process.pid)
            checkpoint()
            code = process.wait(timeout=timeout)
            entry.update(exit_code=code, process_exit_observed=True)
            require(code == 0, "Native command failed: " + log.name)
            entry["status"] = "PASS_EXIT_0"
            return process.pid
        except BaseException as exc:
            entry.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL",
                         error_type=type(exc).__name__)
            if process is not None:
                base.terminate_owned(process)
                entry.update(exit_code=process.returncode, process_exit_observed=process.returncode is not None)
            raise
        finally:
            stream.flush()
            os.fsync(stream.fileno())
            checkpoint()


def preserve_evidence(work, destination):
    require(not destination.exists(), "Fresh Space.Close evidence destination required")
    names = ["ownership.json", "result.json"]
    needles_path = work / "sensitive-needles.private"
    needles = []
    if needles_path.is_file() and not needles_path.is_symlink():
        require(needles_path.stat().st_mode & 0o077 == 0, "Synthetic secret inventory is not private")
        values = json.loads(needles_path.read_text())
        require(isinstance(values, list) and len(values) == 2 and all(isinstance(v, str) and v for v in values),
                "Incomplete synthetic secret inventory")
        needles = [value.encode() for value in values]
        names += ["race.json", "reopen.json", "race-trace.json", "race.log", "reopen.log"]
    present = [work / name for name in names if (work / name).exists() or (work / name).is_symlink()]
    for path in present:
        require(path.is_file() and not path.is_symlink() and path.resolve(strict=True).is_relative_to(work)
                and path.stat().st_size <= 32 * 1024**2, "Unsafe Space.Close evidence file")
        require(not any(needle in path.read_bytes() for needle in needles),
                "Synthetic secret found; all Space.Close phase evidence withheld")
    destination.mkdir(mode=0o755)
    result = {}
    for source in present:
        target = destination / source.name
        shutil.copyfile(source, target)
        target.chmod(0o644)
        result[target.name] = digest(target)
    return {"secret_scan": "PASS" if needles else "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY",
            "files_sha256": result}


def run_sequence(identity, work, evidence, baseline_pids):
    work.mkdir(mode=0o700)
    owner = {"protocol": PROTOCOL, "nonce": str(uuid4()), "synthetic_only": True}
    write_json(work / "ownership.json", owner)
    owner_bytes = (work / "ownership.json").read_bytes()
    directory_identity = (work.stat().st_dev, work.stat().st_ino)
    account_root = work / "account-root"
    account_root.mkdir(mode=0o700)
    private = {"status": "NOT_RUN", "protocol": PROTOCOL, "candidate_sha256": CANDIDATE_SHA,
               "binary_sha256": identity["binary_sha256"], "phases": [], "actual_counts": {
                   "native_processes": 0, "passing_test_invocations": 0}}
    checkpoint = lambda: write_json(work / "result.json", private)
    reports, primary, cleanup_error = [], None, None
    try:
        for phase in PHASES:
            require(shutil.disk_usage(work).free >= base.RESERVE, "Disk reserve below 8 GiB")
            require(digest(Path(identity["binary"])) == identity["binary_sha256"], "Instrumented binary changed")
            nonce = str(uuid4())
            entry = {"phase": phase, "nonce": nonce, "status": "NOT_RUN", "report_qualification": "NOT_RUN"}
            private["phases"].append(entry)
            private["status"] = "RUNNING_" + phase.upper()
            env = dict(os.environ, PINKHA_T2_SPACE_CLOSE_PHASE=phase, PINKHA_T2_SPACE_CLOSE_ROOT=str(account_root),
                       PINKHA_T2_SPACE_CLOSE_REPORT=str(work / (phase + ".json")), PINKHA_T2_SPACE_CLOSE_NONCE=nonce,
                       PINKHA_T2_SPACE_CLOSE_FIXTURE_SHA=CANDIDATE_SHA,
                       PINKHA_T2_SPACE_CLOSE_OWNER_TOKEN=owner_bytes.decode(), GOMAXPROCS="2")
            if phase == "reopen":
                require(reports and digest(work / "state.json") == reports[0]["state_sha256"],
                        "Original private state changed before cold reopen")
                env["PINKHA_T2_SPACE_CLOSE_STATE_SHA"] = reports[0]["state_sha256"]
            command = [identity["binary"], "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"]
            pid = run_owned(command, work, env, work / (phase + ".log"), 330, entry, checkpoint)
            private["actual_counts"]["native_processes"] = len([p for p in private["phases"] if p.get("pid")])
            entry["report_qualification"] = "STARTED"
            checkpoint()
            try:
                require(pid not in baseline_pids and pid not in {r["pid"] for r in reports},
                        "Space.Close phases must be separate from the four baseline processes")
                validate_test_log(work / (phase + ".log"))
                report = json.loads((work / (phase + ".json")).read_text())
                validate_report(report, phase, nonce, pid)
                require(digest(work / "state.json") == report["state_sha256"], "Native state/report binding differs")
            except BaseException:
                entry["report_qualification"] = "FAIL"
                raise
            entry.update(report_qualification="PASS_ORIGINAL_LOG_AND_NATIVE_PHASE", report_sha256=digest(work / (phase + ".json")))
            reports.append(report)
            private["actual_counts"]["passing_test_invocations"] += 1
            checkpoint()
        validate_pair(*reports)
        require(digest(Path(identity["binary"])) == identity["binary_sha256"], "Instrumented binary changed during execution")
        private["status"] = "PASS_ORIGINAL_RACE_AND_COLD_REOPEN"
    except BaseException as exc:
        primary = exc
        private.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error_type=type(exc).__name__)
    finally:
        private["actual_counts"]["native_processes"] = len([p for p in private["phases"] if p.get("pid")])
        checkpoint()
        try:
            copied = preserve_evidence(work, evidence / "space-close-sequence")
            write_json(evidence / "space-close-evidence-copy.json", copied)
            if private["status"] == "PASS_ORIGINAL_RACE_AND_COLD_REOPEN":
                require(copied["secret_scan"] == "PASS" and set(copied["files_sha256"]) == {
                    "ownership.json", "result.json", "race.json", "reopen.json", "race-trace.json", "race.log", "reopen.log"},
                        "Native success lacks complete original secret-scanned evidence")
        except BaseException as exc:
            cleanup_error = exc
        try:
            require(work.is_dir() and not work.is_symlink()
                    and (work.stat().st_dev, work.stat().st_ino) == directory_identity
                    and (work / "ownership.json").read_bytes() == owner_bytes,
                    "Owned disposable directory identity changed; cleanup refused")
            require(all(not p.get("pid") or p.get("process_exit_observed") is True for p in private["phases"]),
                    "Owned native process exit was not observed; account cleanup refused")
            shutil.rmtree(work)
            write_json(evidence / "space-close-cleanup.json", {
                "status": "PASS_REMOVED_OWNED_DISPOSABLE_ACCOUNT", "protocol": PROTOCOL,
                "owner_nonce": owner["nonce"], "path_absent": not work.exists(),
                "processes_started": private["actual_counts"]["native_processes"],
                "all_started_process_exits_observed": True})
        except BaseException as exc:
            write_json(evidence / "space-close-cleanup.json", {"status": "FAIL_CLEANUP_WITHHELD",
                       "protocol": PROTOCOL, "owner_nonce": owner["nonce"], "error_type": type(exc).__name__})
            cleanup_error = cleanup_error or exc
    if primary is not None:
        if cleanup_error is not None:
            write_json(evidence / "space-close-secondary-error.json", {"primary_error_type": type(primary).__name__,
                       "secondary_error_type": type(cleanup_error).__name__})
        raise primary
    if cleanup_error is not None:
        raise cleanup_error
    return {"actual_counts": private["actual_counts"], "native_pids": [r["pid"] for r in reports],
            "phase_report_sha256": {p["phase"]: p["report_sha256"] for p in private["phases"]},
            "same_account_space_request_and_durable_history": "PASS_TWO_ORIGINAL_PHASE_REPORTS"}


def execute(args, receipt, run):
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
        baseline_receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL",
                                error_type=type(exc).__name__)
        raise
    finally:
        write_json(args.evidence / "receipt.json", baseline_receipt)
    receipt["baseline"] = {"status": baseline["status"], "actual_counts": baseline["actual_counts"],
                           "receipt_sha256": digest(args.evidence / "receipt.json"),
                           "account_receipt_sha256": baseline["account_receipt_sha256"]}
    hearts = {"new": args.heart_new, "legacy": args.heart_legacy}
    builds = {role: json.loads((args.evidence / (role + "-build.json")).read_text()) for role in hearts}
    snapshots = {role: accepted.native_snapshot(heart, builds[role]) for role, heart in hearts.items()}
    initial_bindings = {name: digest(args.evidence / name) for name in [
        "new-build.json", "legacy-build.json", "receipt.json", "generation/generation-receipt.json"]}
    original_overlay = args.work / "build-new/overlay.json"
    original_overlay_sha = digest(original_overlay)
    original_fixtures = {name: digest(Path(name)) for name in json.loads(original_overlay.read_text())["Replace"].values()}
    directory = args.work / "space-close-build"
    directory.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location("t2_space_close_materializer",
                                                 tools / "account_rpc_space_close/materialize_test_overlay.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    gowork = args.work / "build-new/go.work"
    gowork_sha = digest(gowork)
    env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2",
               GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly", GOPROXY="off",
               CGO_LDFLAGS="-L" + str(args.heart_new / "deps/libs/linux-amd64-musl"))
    run(["go", "list", "-m", "-json", helper.ANY_SYNC], "space-close-any-sync-selection", args.heart_new, env, 60)
    selected = json.loads((args.evidence / "space-close-any-sync-selection.log").read_text())
    overlay = directory / "overlay.json"
    composed = helper.prepare(args.heart_new, selected, original_overlay, overlay)
    require(composed["candidate_sha256"] == CANDIDATE_SHA and composed["added_overlay_entries"] == 10
            and composed["product_source_mutations"] == composed["module_cache_mutations"] == 0,
            "Wrong test-only Space.Close composition")
    # Go rejects overlays inside GOMODCACHE. Bind the exact selected module
    # version to its byte-verified copy in a separate test-only workspace.
    test_gowork = directory / "go.work"
    test_gowork.write_text(gowork.read_text() + "\nreplace " + helper.ANY_SYNC + " " + helper.VERSION
                          + " => " + json.dumps(composed["any_sync_copy"]["copy_dir"]) + "\n")
    if gowork.with_suffix(".work.sum").exists():
        shutil.copyfile(gowork.with_suffix(".work.sum"), test_gowork.with_suffix(".work.sum"))
    test_gowork_sha = digest(test_gowork)
    env["GOWORK"] = str(test_gowork)
    run(["go", "list", "-m", "-json", helper.ANY_SYNC], "space-close-any-sync-copy-selection",
        args.heart_new, env, 60)
    copied_selection = json.loads((args.evidence / "space-close-any-sync-copy-selection.log").read_text())
    require(copied_selection.get("Path") == helper.ANY_SYNC
            and copied_selection.get("Version") == helper.VERSION
            and copied_selection.get("Dir") == composed["any_sync_copy"]["copy_dir"]
            and copied_selection.get("Replace", {}).get("Dir") == composed["any_sync_copy"]["copy_dir"]
            and Path(copied_selection["GoMod"]).read_bytes() == Path(selected["GoMod"]).read_bytes(),
            "Separate test workspace did not select the exact owned AnySync copy")
    source = baseline["identities"]["new"]
    registration, schema = source["registration_patch_sha256"], source["rpc_manifest_sha256"]
    flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + base.HEART
             + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + source["runtime_version"]
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountFixtureSHA=" + source["fixture_sha256"]
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRuntimeRole=new"
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRegistrationSHA=" + registration
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2RPCAccountSchemaSHA=" + schema
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2SpaceCloseFixtureSHA=" + CANDIDATE_SHA)
    binary = directory / "pinkha-t2-rpc-space-close.test"
    write_json(args.evidence / "space-close-composition.json", composed)
    primary, integrity_error, identity, sequence = None, None, None, None

    def verify_unchanged():
        require(source_inputs(control) == inputs and digest(gowork) == gowork_sha
                and digest(test_gowork) == test_gowork_sha
                and digest(overlay) == composed["composed_overlay_sha256"]
                and digest(original_overlay) == original_overlay_sha
                and all(digest(Path(name)) == sha for name, sha in original_fixtures.items())
                and all(digest(args.evidence / name) == sha for name, sha in initial_bindings.items()),
                "Space.Close build/run changed its original source/build/baseline binding")
        for group in ["source_before_sha256", "replacement_after_sha256"]:
            require(all(digest(Path(name)) == sha for name, sha in composed[group].items()),
                    "An original or instrumented native source changed")
        require(helper.module_identity(args.heart_new, selected) == composed["any_sync"],
                "Selected immutable AnySync module changed")
        helper.verify_module_copy(composed["any_sync"], composed["any_sync_copy"])
        for role, heart in hearts.items():
            account.verify_rpc_binary(role, baseline["identities"][role], registration, schema)
            require(accepted.native_snapshot(heart, builds[role]) == snapshots[role],
                    "Space.Close build/run mutated original native sources")
        for root, pin in [(control, args.expected_app_sha), (args.approved_source, base.APPROVED_SOURCE)]:
            require(base.git(root, "rev-parse", "HEAD") == pin and not base.git(root, "status", "--porcelain"),
                    "Control or immutable approved source changed")

    try:
        verify_unchanged()
        require(shutil.disk_usage(directory).free >= base.RESERVE, "Disk reserve below 8 GiB")
        run(["go", "test", "-c", "-p", "1", "-tags", base.TAGS, "-overlay", str(overlay), "-ldflags", flags,
             "-o", str(binary), "./clientlibrary/service"], "space-close-compile", args.heart_new, env, 1800)
        identity = {**source, "binary": str(binary), "binary_sha256": digest(binary), "candidate_sha256": CANDIDATE_SHA,
                    "scope": "SEPARATE_TEST_INSTRUMENTED_BINARY", "original_new_binary_sha256": source["binary_sha256"]}
        account.verify_rpc_binary("new", identity, registration, schema)
        require(identity["binary_sha256"] not in {item["binary_sha256"] for item in baseline["identities"].values()}
                and base.contains(binary, CANDIDATE_SHA) and base.contains(binary, METHOD),
                "Missing distinct linked Space.Close test binary")
        verify_unchanged()
        write_json(args.evidence / "space-close-build.json", {"identity": identity, "composition": composed,
                   "source_inputs": inputs, "original_build_bindings": initial_bindings,
                   "overlay": json.loads(overlay.read_text()), "original_fixture_sha256": original_fixtures,
                   "gowork_sha256": gowork_sha, "test_gowork_sha256": test_gowork_sha,
                   "test_any_sync_selection": copied_selection})
        prior = json.loads((args.evidence / "account-sequence/result.json").read_text())
        pids = {phase["pid"] for phase in prior["phase_reports"]}
        require(len(pids) == 4, "Original baseline process identities are incomplete")
        receipt["space_close_execution"] = "STARTED"
        sequence = run_sequence(identity, args.work / "space-close-sequence", args.evidence, pids)
        require(sequence["actual_counts"] == {"native_processes": 2, "passing_test_invocations": 2},
                "Both original native processes must pass")
        receipt["space_close_execution"] = "PASS_ORIGINAL_RACE_AND_COLD_REOPEN"
    except BaseException as exc:
        primary = exc
        if receipt.get("space_close_execution") == "STARTED":
            receipt["space_close_execution"] = "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL"
    finally:
        try:
            verify_unchanged()
            if identity is not None:
                require(digest(binary) == identity["binary_sha256"], "Instrumented binary changed after native execution")
            write_json(args.evidence / "space-close-source-after-execution.json", {
                "status": "PASS_EXACT_REVIEWED_INPUTS_UNCHANGED", "source_inputs": inputs,
                "original_build_bindings": initial_bindings, "composition": composed,
                "native_execution_status": receipt.get("space_close_execution", "NOT_RUN")})
        except BaseException as exc:
            integrity_error = exc
            write_json(args.evidence / "space-close-source-after-execution.json", {
                "status": "FAIL_SOURCE_INTEGRITY", "error_type": type(exc).__name__,
                "primary_error_type": type(primary).__name__ if primary else None,
                "native_execution_status": receipt.get("space_close_execution", "NOT_RUN")})
    if primary is not None:
        raise primary
    if integrity_error is not None:
        raise integrity_error
    return {"status": PASS, "space_close": sequence, "instrumented_identity": identity,
            "original_account_baseline": "PASS_UNMODIFIED_FOUR_PROCESSES_AND_EIGHT_EXPORTS",
            "prior_three_race_fixture": "UNCHANGED_NOT_RERUN_BY_THIS_LANE",
            "source_after_execution": "PASS_UNCHANGED_PRODUCT_AND_EXACT_TEST_COMPOSITION",
            "artifact_runtime_binary_bytes": "NOT_RETAINED_BUILD_AND_PHASE_RECEIPTS_ONLY"}


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args(argv)
    for name in ["approved_source", "heart_legacy", "heart_new", "work", "evidence"]:
        setattr(args, name, getattr(args, name).resolve())
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "space-close-receipt.json"
    require(not path.exists() and not (args.evidence / "receipt.json").exists(), "Fresh Space.Close evidence required")
    receipt = {"status": "NOT_RUN_PREFLIGHT", "protocol": PROTOCOL, "scope": SCOPE,
               "app_sha": args.expected_app_sha, "product_base_sha": PRODUCT_BASE,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"), "commands": [],
               "started_at": datetime.now(timezone.utc).isoformat(), "space_close_execution": "NOT_RUN", **LIMITS,
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

    def run(command, name, cwd, env, timeout=900, *, target=None, filename="space-close-receipt.json"):
        target = receipt if target is None else target
        entry = {"name": name, "status": "NOT_RUN"}
        target["commands"].append(entry)
        return run_owned(command, cwd, env, args.evidence / (name + ".log"), timeout, entry,
                         lambda: write_json(args.evidence / filename, target))

    result = 1
    try:
        write_json(path, receipt)
        receipt.update(execute(args, receipt, run))
        result = 0
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error_type=type(exc).__name__)
        print(type(exc).__name__ + ": native Space.Close evidence did not satisfy its reviewed contract", file=sys.stderr)
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
