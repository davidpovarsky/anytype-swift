"""Complete only the four pending native cases, then read one real account twice.

The 67 unchanged successful cases from44952909883 remain source-bound evidence.
The prior run stays FAIL; a constructor-only fixture repair cannot rewrite it.
No default runtime, capability, mixed-client or iOS acceptance is asserted here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

from . import profile
import run_account_lifecycle as lifecycle

PROTOCOL = "pinkha-authorized-read-account-v1"
METHOD = "TestPinkhaAuthorizedOperationAccountByteLifecycle"
PRIOR_RUN = "44952909883"
PRIOR_SHA = "a7db1f90241b7d4075eb768d3d38446887991ee3"
PRIOR_PROOF = "docs/validation/20261121-heart-authorized-read-native-linux"
REPAIRED_TEST = "core/pinkha_authorized_operation_read_rpc_test.go"
FAILED_METHOD = "TestPinkhaAuthorizedOperationRPCRejectsBeforeAccount"
PENDING = {
    FAILED_METHOD,
    "TestPinkhaAuthorizedOperationReadRejectsVersionBeforeAccount",
    "TestPinkhaAuthorizedOperationReadShapeAndCancellationBeforeAccount",
    "TestPinkhaAuthorizedOperationReadRequiresRunningAccount",
}
PENDING_PAIRS = {(name, profile.PACKAGE_ROOT + "core") for name in PENDING}
PHASES = ("create", "reopen")
FIXTURE_PATHS = {
    "Tools/TorahNativeOperations/account_lifecycle/account_phase_test.go",
    "Tools/TorahNativeOperations/account_lifecycle/new_runtime_test.go",
    "Tools/TorahNativeOperations/account_lifecycle/native_handler_test.go",
    "Tools/TorahNativeOperations/authorized_read/account/authorized_operation_account_test.go",
}
require, digest, relative = profile.require, profile.digest, profile.relative


def events(path: Path) -> list[dict]:
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("{"):
            result.append(json.loads(line))
        else:
            require(not line.strip() or line.startswith("go: downloading "), "Unexpected native event output")
    return result


def retain_prior_cases(control: Path, generation: dict) -> dict:
    proof = control / PRIOR_PROOF
    pins = json.loads((proof / "evidence.json").read_bytes())
    require(pins["run_id"] == PRIOR_RUN and pins["source_sha"] == PRIOR_SHA
            and pins["artifact_id"] == 14726736631, "Wrong retained native evidence")
    for name, sha in pins["files_sha256"].items():
        require(digest(proof / relative(name)) == sha, "Retained native evidence changed")
    old = json.loads((proof / "generation-receipt.json").read_bytes())
    failed = json.loads((proof / "receipt.json").read_bytes())
    require(old["status"] == "PASS_PINNED_RPC_GENERATION" and failed["status"] == "FAIL"
            and old["app_sha"] == failed["app_sha"] == PRIOR_SHA
            and str(old["run_id"]) == str(failed["run_id"]) == PRIOR_RUN,
            "Prior failed run cannot be relabelled")
    old_source, new_source = old["source_sha256"], generation["source_sha256"]
    require(set(old_source) == set(new_source), "Native source closure changed")
    changed = {name for name in old_source if old_source[name] != new_source[name]}
    require(changed == {REPAIRED_TEST}, "Only the known constructor fixture may change")
    original = (proof / "original_rpc_fixture.go.txt").read_bytes()
    repaired = control / "Tools/TorahNativeOperations/authorized_read/rpc/overlay" / REPAIRED_TEST
    require(hashlib.sha256(original).hexdigest() == old_source[REPAIRED_TEST]
            and original.count(b"mw := &Middleware{}") == 1
            and repaired.read_bytes() == original.replace(b"mw := &Middleware{}", b"mw := New()", 1)
            and digest(repaired) == new_source[REPAIRED_TEST], "Fixture repair differs from reviewed constructor change")
    for key in ["generated_sha256", "module_sha256", "protobuf_inputs_sha256", "native_read_inventory_sha256",
                "schema_patch_sha256", "authorized_schema_patch_sha256", "rpc_manifest_sha256"]:
        require(generation[key] == old[key], "Previously tested native input changed: " + key)
    rows = events(proof / "native-rpc-tests.log")
    terminal = [item for item in rows if item.get("Test") and item.get("Action") in {"pass", "fail", "skip"}]
    passed = [(item["Test"], item.get("Package")) for item in terminal if item["Action"] == "pass"]
    expected = profile.REQUIRED - PENDING_PAIRS
    require(len(passed) == len(expected) == 67 and set(passed) == expected, "Prior successful set is incomplete or repeated")
    failures = [(item["Test"], item.get("Package")) for item in terminal if item["Action"] != "pass"]
    require(failures == [(FAILED_METHOD, profile.PACKAGE_ROOT + "core")]
            and not any(item.get("Action") == "skip" for item in rows), "Prior failure differs from known constructor panic")
    return {"run_id": PRIOR_RUN, "app_sha": PRIOR_SHA, "run_status": "FAIL_RETAINED_WITHOUT_RELABELLING",
            "top_level_pass": 19, "terminal_pass": 67, "source_changes": [REPAIRED_TEST],
            "production_source_changes": 0, "generated_source_changes": 0,
            "evidence_manifest_sha256": digest(proof / "evidence.json")}


def validate_pending(rows: list[dict]) -> dict:
    terminal = [item for item in rows if item.get("Test") and item.get("Action") in {"pass", "fail", "skip"}]
    passed = [(item["Test"], item.get("Package")) for item in terminal if item["Action"] == "pass"]
    packages = [item.get("Package") for item in rows if not item.get("Test") and item.get("Action") == "pass"]
    require(not any(item.get("Action") in {"fail", "skip"} for item in rows)
            and len(passed) == 4 and set(passed) == PENDING_PAIRS
            and packages == [profile.PACKAGE_ROOT + "core"], "Exact four pending native cases did not pass")
    return {"top_level_pass": 4, "terminal_pass": 4, "fail": 0, "skip": 0, "methods": sorted(PENDING)}


def fixtures(control: Path) -> tuple[str, dict[str, str]]:
    manifest = control / "Tools/TorahNativeOperations/authorized_read/account/fixtures.json"
    value = json.loads(manifest.read_bytes())
    require(value["protocol"] == PROTOCOL and value["heart_sha"] == profile.HEART
            and set(value["files_sha256"]) == FIXTURE_PATHS, "Wrong positive-account fixture closure")
    hashes = {name: digest(control / relative(name)) for name in sorted(FIXTURE_PATHS)}
    require(hashes == value["files_sha256"], "Account fixture source changed")
    require({p.name for p in manifest.parent.glob("*.go")} == {"authorized_operation_account_test.go"},
            "Unexpected candidate account fixture")
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), hashes


def candidate_identity(generation: dict) -> str:
    value = {key: generation[key] for key in ["heart_sha", "source_sha256", "module_sha256", "generated_sha256",
             "native_read_inventory_sha256", "authorized_read_manifest_sha256", "rpc_manifest_sha256"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_phase(value: dict, phase: str, identity: dict, nonce: str, root: Path, pid: int,
                   state: dict, state_sha: str) -> None:
    lifecycle.validate_state(state)
    require(value.get("protocol") == PROTOCOL and value.get("phase") == phase
            and phase in PHASES and value.get("pid") == pid and pid > 0 and value.get("nonce") == nonce,
            "Stale or foreign native account phase")
    for key in ["heart_sha", "candidate_sha256", "fixture_sha256", "runtime_version"]:
        require(value.get(key) == identity[key], "Account binary/source marker differs: " + key)
    require(value.get("account_root") == str(root) and value.get("state_sha256") == state_sha,
            "Account root/state changed")
    for key, state_key in {"account_id": "AccountID", "space_id": "SpaceID", "document_id": "DocumentID",
                           "block_id": "BlockID", "private_root_id": "RootID"}.items():
        require(value.get(key) == state[state_key], "Original account identity differs: " + key)
    require(value.get("raw_changes_sha256") == state["RawChanges"] and value.get("heads") == state["Heads"]
            and value.get("canonical_sha256") == state["OperationSHA256"], "Exact immutable history changed")
    require(all(value.get(key) is True for key in ["exact_signed_provenance", "read_before_replay",
                "verified_local_absence", "account_stop_verified", "closed", "test_passed"]),
            "Positive native read/stop observation incomplete")
    require(value.get("orphan_history_preserved") is (phase == "reopen")
            and value.get("space_cleanup_verified") is (phase == "reopen"), "Native target/Space lifetime not exercised")
    require(value.get("app_capability") == "OFF" and value.get("two_app_clients") == "NOT_RUN"
            and value.get("ios_acceptance") == "NOT_RUN", "Native evidence overstates app acceptance")
    require(value.get("golden_file") == phase + "-live.pb"
            and re.fullmatch(r"[0-9a-f]{64}", value.get("golden_sha256", "")), "Missing exact generated response fixture")
    calls = value.get("rpc_calls", {})
    allowed = {"InitialSetParameters", "AppGetVersion", "WalletCreate", "AccountCreate", "WorkspaceCreate", "WorkspaceOpen",
               "ObjectSearch", "ObjectCreate", "BlockCreate", "PinkhaTorahOperationsAppend", "WalletRecover", "AccountSelect",
               "AccountMigrate", "BlockListDelete", "SpaceDelete", "AccountStop", "AppShutdown"}
    require(set(calls) <= allowed and all(type(count) is int and count > 0 for count in calls.values()), "Unexpected account mutation")
    for key in ["InitialSetParameters", "AppGetVersion", "WorkspaceOpen", "AccountStop", "AppShutdown"]:
        require(calls.get(key) == 1, "Required native lifecycle call missing: " + key)
    created = ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate", "PinkhaTorahOperationsAppend"]
    require(all(calls.get(key, 0) == (1 if phase == "create" else 0) for key in created), "Account or operation was recreated")
    require(calls.get("BlockListDelete", 0) == calls.get("SpaceDelete", 0) == (1 if phase == "reopen" else 0),
            "Unexpected deletion phase")
    if phase == "reopen":
        require(calls.get("WalletRecover") == 1 and calls.get("AccountSelect") in {1, 2}
                and calls.get("AccountMigrate", 0) == calls["AccountSelect"] - 1, "Existing account not reopened")


def export_evidence(work: Path, destination: Path) -> dict:
    require(not destination.exists(), "Fresh account evidence destination required")
    names = ["ownership.json", "result.json"]
    secrets_file = work / "sensitive-needles.private"
    needles = []
    if secrets_file.is_file() and not secrets_file.is_symlink():
        values = json.loads(secrets_file.read_bytes())
        require(len(values) == 2 and all(isinstance(value, str) and value for value in values), "Incomplete secret inventory")
        needles = [value.encode() for value in values]
        names += ["state.json", "reopen-unreachable.pb"]
        names += [phase + suffix for phase in PHASES for suffix in [".json", ".log", "-live.pb"]]
    selected = []
    for name in names:
        path = work / name
        if not path.exists():
            continue
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(work), "Unsafe evidence file")
        raw = path.read_bytes()
        require(not any(needle in raw for needle in needles), "Sensitive account material detected; export withheld")
        selected.append((name, path))
    destination.mkdir(mode=0o755)
    hashes = {}
    for name, path in selected:
        target = destination / name
        shutil.copyfile(path, target)
        target.chmod(0o644)
        hashes[name] = digest(target)
    return {"secret_scan": "PASS" if needles else "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY", "files_sha256": hashes}


def sequence(binary: Path, identity: dict, work: Path, evidence: Path, env: dict) -> dict:
    work.mkdir(mode=0o700)
    root = work / "account-root"
    root.mkdir(mode=0o700)
    owner = {"protocol": PROTOCOL, "nonce": str(uuid4()), "synthetic_only": True}
    lifecycle.write_json(work / "ownership.json", owner)
    result = {"status": "RUNNING", "phases": [], "app_capability": "OFF", "ios_acceptance": "NOT_RUN"}
    lifecycle.write_json(work / "result.json", result)
    pids, state_sha, key_sha = set(), None, None
    try:
        for phase in PHASES:
            require(shutil.disk_usage(work).free >= 8 * 1024**3, "Disk reserve below8GiB")
            require(lifecycle.digest(binary) == identity["binary_sha256"], "Native binary changed between processes")
            nonce = str(uuid4())
            phase_env = dict(env, PINKHA_T2_READ_PHASE=phase, PINKHA_T2_READ_ROOT=str(root),
                PINKHA_T2_READ_REPORT=str(work / (phase + ".json")), PINKHA_T2_READ_NONCE=nonce,
                PINKHA_T2_READ_FIXTURE_SHA=identity["fixture_sha256"], PINKHA_T2_READ_CANDIDATE_SHA=identity["candidate_sha256"],
                PINKHA_T2_READ_OWNER_TOKEN=(work / "ownership.json").read_text())
            log = work / (phase + ".log")
            pid = lifecycle.run_process([str(binary), "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"],
                                        work, phase_env, log, 330)
            require(pid not in pids, "Account reopen must use another actual process")
            pids.add(pid)
            output = log.read_text(encoding="utf-8", errors="replace")
            require(("--- PASS: " + METHOD + " ") in output and output.count("--- PASS:") == 1
                    and "--- FAIL:" not in output and "--- SKIP:" not in output, "Exact positive account test did not pass")
            state_path, key_path = work / "state.json", work / "account-key.private"
            require(key_path.is_file() and key_path.stat().st_size > 0 and key_path.stat().st_mode & 0o077 == 0,
                    "Synthetic account key must remain private")
            if state_sha is None:
                state_sha, key_sha = digest(state_path), digest(key_path)
            require(digest(state_path) == state_sha and digest(key_path) == key_sha, "Original account state/key was replaced")
            state = json.loads(state_path.read_bytes())
            report = json.loads((work / (phase + ".json")).read_bytes())
            validate_phase(report, phase, identity, nonce, root, pid, state, state_sha)
            require(digest(work / report["golden_file"]) == report["golden_sha256"], "Exact generated response fixture changed")
            result["phases"].append({"phase": phase, "pid": pid, "report_sha256": digest(work / (phase + ".json"))})
            lifecycle.write_json(work / "result.json", result)
        result.update(status="PASS_REAL_ACCOUNT_GENERATED_READ_TWO_PROCESSES", actual_pass=2, fail=0, skip=0)
    except BaseException as exc:
        result.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error=type(exc).__name__)
        raise
    finally:
        lifecycle.write_json(work / "result.json", result)
        exported = export_evidence(work, evidence / "account-sequence")
        lifecycle.write_json(evidence / "account-export.json", exported)
    return result


def execute(args, receipt: dict, run, generation: dict, env: dict, verify_source) -> None:
    require(args.rpc_profile == profile.PROFILE and args.stage == "account", "Positive read requires explicit candidate account stage")
    control, heart, work, evidence = args.control, args.heart_source, args.work, args.evidence
    retained = retain_prior_cases(control, generation)
    receipt["retained_native_evidence"] = retained
    pattern = "^(" + "|".join(sorted(PENDING)) + ")$"
    run(["go", "test", "-p", "1", "-parallel", "1", "-count=1", "-timeout=240s", "-json", "-tags", lifecycle.TAGS,
         "-ldflags=-extldflags=-static", "-run", pattern, "./core"], "pending-native-core", heart, env, 900)
    receipt["new_component_counts"] = validate_pending(events(evidence / "pending-native-core.log"))
    fixture_sha, hashes = fixtures(control)
    candidate_sha = candidate_identity(generation)
    build = work / "authorized-account-build"
    build.mkdir()
    replacements = {}
    for name in sorted(hashes):
        source = control / relative(name)
        target = heart / "clientlibrary/service" / ("pinkha_t2_read_" + source.name)
        require(not target.exists(), "Account fixture would replace native source")
        replacements[str(target)] = str(source)
    overlay = build / "overlay.json"
    lifecycle.write_json(overlay, {"Replace": replacements})
    version = "v0.51.7-nightly.20261014.1-pinkha-authorized-read-v1-" + candidate_sha
    flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + profile.HEART
             + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + version
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2ReadFixtureSHA=" + fixture_sha
             + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2ReadCandidateSHA=" + candidate_sha)
    binary = build / "pinkha-authorized-read-account.test"
    run(["go", "test", "-c", "-p", "1", "-tags", lifecycle.TAGS, "-overlay", str(overlay), "-ldflags", flags,
         "-o", str(binary), "./clientlibrary/service"], "compile-authorized-account", heart, env, 1200)
    with binary.open("rb") as stream:
        require(stream.read(6) == b"\x7fELF\x02\x01", "Actual Linux amd64 ELF required")
    require(all(lifecycle.contains(binary, marker) for marker in [profile.HEART, version, fixture_sha, PROTOCOL, METHOD]),
            "Native binary lacks linked candidate/fixture identity")
    identity = {"heart_sha": profile.HEART, "candidate_sha256": candidate_sha, "fixture_sha256": fixture_sha,
                "runtime_version": version, "binary_sha256": lifecycle.digest(binary), "fixture_sources_sha256": hashes}
    receipt["native_account_identity"] = identity
    lifecycle.write_json(evidence / "account-build.json", identity)
    verify_source()
    observed = sequence(binary, identity, work / "authorized-account-sequence", evidence, env)
    verify_source()
    require(fixtures(control) == (fixture_sha, hashes), "Account test source changed during execution")
    receipt.update(status="PASS_AUTHORIZED_READ_NATIVE_AND_REAL_ACCOUNT", native_account_counts={"pass": observed["actual_pass"], "fail": 0, "skip": 0},
                   combined_component_counts={"top_level_pass": 23, "terminal_pass": 71, "retained_from_prior_run": 67, "executed_this_run": 4},
                   account_wire_acceptance="PASS_SAME_NATIVE_ACCOUNT_TWO_PROCESSES",
                   unchanged_prior_tests_executed=0, app_capability="OFF", two_app_clients="NOT_RUN", ios_acceptance="NOT_RUN")
