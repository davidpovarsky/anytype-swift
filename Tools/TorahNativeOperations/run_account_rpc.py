#!/usr/bin/env python3
"""Prove generated native RPCs in the existing four-process disposable account.

Generation is a separate host stage with a same-run receipt. Only the new
binary receives generated schema/mapper and account-wire fixture additions.
The legacy, visibility, export, history and secret boundaries remain intact.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys

import run_account_lifecycle as base
import run_native_rpc as rpc
import run_native_registration as closure

PASS = "PASS_NATIVE_ACCOUNT_GENERATED_RPC_LIFECYCLE"
SCOPE = "generated protobuf bytes in four processes reopening one synthetic account; not two App clients or iOS"
require, digest, write_json = base.require, base.digest, base.write_json


def expected_observation(phase: str, state: dict, schema_sha: str) -> dict:
    return {"private_registry": "ACTUAL_NATIVE_FACTORY", "private_read": "EXACT_PERSISTED_CLAIM",
            "idempotent_retry": "already_exists_same_payload", "operation_sha256": state["OperationSHA256"],
            "claim_id": state["ClaimID"], "signed_change_id": state["ChangeID"], "private_type": 0x504B0001,
            "handler_boundary": {"scope": "ACCOUNT_SCOPED_TYPED_BOUNDARY_NOT_REGISTERED_RPC",
                                 "creation": ("EXISTING_HISTORY_CREATED_THROUGH_GENERATED_RPC"
                                              if phase == "new-create" else "EXISTING_HISTORY_REOPENED"),
                                 "read": "EXACT_PERSISTED_CLAIM_NATIVE_AUTHOR", "read_guards": "VERSION_AND_LIMIT_REJECTED",
                                 "retry": "already_exists_same_payload", "collision": "collision_different_payload",
                                 "after_stop": "NATIVE_READ_AND_APPEND_NOT_LOGGED_IN"},
            "wire_boundary": {"scope": "ACCOUNT_SCOPED_GENERATED_BYTE_RPC_NOT_TWO_CLIENTS",
                              "schema_inventory_sha256": schema_sha,
                              "creation": ("REJECTED_WIRE_CALLS_NO_ROOT_THEN_VALID_WIRE_APPEND_CREATED_ROOT"
                                           if phase == "new-create" else "EXISTING_HISTORY_REOPENED_THROUGH_GENERATED_RPC"),
                              "read": "EXACT_PERSISTED_CLAIM_NATIVE_AUTHOR", "read_guards": "VERSION_AND_LIMIT_REJECTED",
                              "retry": "ALREADY_EXISTS_SAME_PAYLOAD", "collision": "NON_NULL_COLLISION_WITH_COMPLETE_RECEIPT",
                              "snapshot_scope": "LOCAL_VERIFIED_TREE", "after_stop": "GENERATED_READ_AND_APPEND_NOT_LOGGED_IN"}}


def validate_phase(report, phase, role, identity, nonce, account_root, pid, state, state_hash):
    # This is an additional exact observation, not a replacement for baseline
    # state/source/PID/nonce/visibility/export/cleanup/RPC-count validation.
    expected = None
    if role == "new":
        schema_sha = identity.get("rpc_manifest_sha256", "")
        require(re.fullmatch(r"[0-9a-f]{64}", schema_sha), "Missing linked RPC source identity")
        expected = expected_observation(phase, state, schema_sha)
    base.validate_phase(report, phase, role, identity, nonce, account_root, pid, state, state_hash,
                        expected_observation=expected)


def generation_identity(value: dict, source_sha: str, run_id: str, attempt: str,
                        manifest_sha: str, generated: dict) -> None:
    require(isinstance(run_id, str) and run_id.isdigit() and int(run_id) > 0
            and isinstance(attempt, str) and attempt.isdigit() and int(attempt) > 0,
            "Explicit native workflow run identity required")
    require(value.get("status") == "PASS_PINNED_RPC_GENERATION"
            and value.get("app_sha") == source_sha and value.get("run_id") == run_id
            and value.get("run_attempt") == attempt and value.get("rpc_manifest_sha256") == manifest_sha,
            "Generation receipt is not from this exact source/run/attempt")
    require(value.get("generated_sha256") == generated, "Generated bindings differ from the proved pinned inputs")
    require(value.get("app_capability") == "OFF" and value.get("account_wire_acceptance") == "NOT_RUN",
            "Generation receipt overstates account acceptance")


def fixture_inputs(control: Path) -> tuple[dict, str, Path]:
    tools = control / "Tools/TorahNativeOperations"
    folder = tools / "account_rpc"
    manifest_path = folder / "fixture.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest["protocol"] == "pinkha-t2-account-generated-rpc-v1", "Wrong fixture contract")
    require(digest(tools / "run_account_lifecycle.py") == manifest["base_controller_sha256"], "Baseline controller differs")
    require(digest(tools / "rpc/heart-rpc.json") == manifest["rpc_manifest_sha256"], "RPC source inventory differs")
    require(digest(folder / "fixture.patch") == manifest["fixture_patch_sha256"], "Account-wire hooks differ")
    require(digest(folder / "native_rpc_account_test.go") == manifest["new_helper_sha256"], "Account-wire helper differs")
    actual = {p.name: digest(p) for p in (tools / "account_lifecycle").glob("*.go")}
    require(actual == manifest["baseline_fixtures"], "Baseline account fixtures differ")
    require(set(manifest["transformed_fixtures"]) == {"new_runtime_test.go", "native_handler_test.go"},
            "Account-wire hooks may only change new-client fixtures")
    for name in [*actual, *manifest["transformed_fixtures"]]:
        require(base.relative(name).name == name, "Unsafe fixture path")
    # Both binaries carry the same complete fixture-input identity, while only
    # the new binary includes the additional helper and changed Go files.
    return manifest, digest(manifest_path), folder


def prepare_fixtures(control: Path, work: Path, manifest: dict, folder: Path, run) -> Path:
    target = work / "new-fixtures"
    target.mkdir()
    for name in manifest["baseline_fixtures"]:
        shutil.copyfile(control / "Tools/TorahNativeOperations/account_lifecycle" / name, target / name)
    run(["git", "apply", "--check", str(folder / "fixture.patch")], "fixture-check", target, os.environ.copy())
    run(["git", "apply", str(folder / "fixture.patch")], "fixture-apply", target, os.environ.copy())
    shutil.copyfile(folder / "native_rpc_account_test.go", target / "native_rpc_account_test.go")
    verify_fixture_copy(target, manifest)
    return target


def verify_fixture_copy(target: Path, manifest: dict) -> None:
    expected = {**manifest["baseline_fixtures"], **manifest["transformed_fixtures"],
                "native_rpc_account_test.go": manifest["new_helper_sha256"]}
    require({p.name: digest(p) for p in target.glob("*.go")} == expected, "Transformed account fixture bytes differ")


def extend_generated_source(heart: Path, generation: dict, old: dict, patch: Path, run) -> dict:
    rpc.verify_composed_source(heart, generation["source_sha256"], set(generation["tracked_paths"]), generation["module_sha256"])
    require(not set(old).intersection(generation["source_sha256"]), "r14/generated registry RPC source collision")
    for name, entry in old.items():
        before = entry["before_sha256"]
        require(not (heart / name).exists() if before is None else digest(heart / name) == before,
                "r14 base differs after generation")
    expected = dict(old)
    for name, sha in generation["source_sha256"].items():
        original = (subprocess.check_output(["git", "-C", str(heart), "show", base.HEART + ":" + name], timeout=30)
                    if name in generation["tracked_paths"] else None)
        expected[name] = {"before_sha256": hashlib.sha256(original).hexdigest() if original is not None else None,
                          "after_sha256": sha}
    run(["git", "apply", "--check", str(patch)], "new-r14-check", heart, os.environ.copy())
    run(["git", "apply", str(patch)], "new-r14-apply", heart, os.environ.copy())
    base.verify_source(heart, expected, generation["module_sha256"])
    return expected


def verify_rpc_binary(role: str, identity: dict, registration_sha: str, schema_sha: str) -> None:
    base.verify_binary(role, identity, registration_sha)
    binary = Path(identity["binary"])
    for marker in [schema_sha, "PinkhaTorahOperationsAppend", "PinkhaTorahOperationsReadTarget"]:
        require(base.contains(binary, marker) == (role == "new"), "Generated RPC appeared in the wrong native binary")
    require(identity.get("rpc_manifest_sha256") == (schema_sha if role == "new" else "none"), "Wrong RPC binary role")


NATIVE_READ_OBSERVATION = {
    "source_path": "core/pinkha_torah_rpc.go",
    "before_sha256": "3e3325bb724c75ae9023b6386416278af4327de8243be90ce245c6de6b22a8e5",
    "after_sha256": "8a33180223b57dc79c8c7aa8bd8cca628b43f00cededb6f4010b2a095784eb93",
    "patch_sha256": "3b68ed7a7dc51f4fa90b096c1be4d454b522661ae9c615d9dbf06eb8d71034ec",
}


def prepare_native_read_observation(heart: Path, patch: Path, work: Path, run) -> tuple[Path, dict]:
    """Observe the original native error only in an explicitly bound test binary.

    The checked Heart source remains untouched. A copied, exact-context patch is
    used solely through Go's compile overlay; it neither repeats the read nor
    changes its result/error. No production/source inventory is relabelled.
    """
    source = heart / NATIVE_READ_OBSERVATION["source_path"]
    require(source.is_file() and not source.is_symlink()
            and digest(source) == NATIVE_READ_OBSERVATION["before_sha256"], "Unexpected native read source")
    require(patch.is_file() and not patch.is_symlink()
            and digest(patch) == NATIVE_READ_OBSERVATION["patch_sha256"], "Unexpected native read observation patch")
    target = work / "native-read-observation"
    require(not target.exists(), "Fresh native read observation work required")
    replacement = target / NATIVE_READ_OBSERVATION["source_path"]
    replacement.parent.mkdir(parents=True, mode=0o700)
    shutil.copyfile(source, replacement)
    run(["git", "apply", "--check", str(patch)], "native-read-observation-check", target, os.environ.copy())
    run(["git", "apply", str(patch)], "native-read-observation-apply", target, os.environ.copy())
    require(digest(replacement) == NATIVE_READ_OBSERVATION["after_sha256"]
            and digest(source) == NATIVE_READ_OBSERVATION["before_sha256"], "Native read observation changed unexpected bytes")
    return replacement, {**NATIVE_READ_OBSERVATION, "scope": "TEST_COMPILE_OVERLAY_ONLY_ORIGINAL_READ_ERROR"}


def execute(args, receipt, run, *, native_client_fixtures: dict[str, Path] | None = None,
            native_read_observation: Path | None = None) -> dict:
    control = Path(__file__).resolve().parents[2]
    tools = control / "Tools/TorahNativeOperations"
    source, work, evidence = args.approved_source, args.work, args.evidence
    hearts = {"legacy": args.heart_legacy, "new": args.heart_new}
    require(sys.platform == "linux" and os.name == "posix", "Native account-RPC builds require Linux CI")
    paths = [control, source, work, evidence, *hearts.values()]
    require(len(set(paths)) == len(paths) and not any(a in b.parents for a in paths for b in paths if a != b),
            "Source/work/evidence trees must be distinct siblings")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha), "Exact source SHA required")
    for root, pin in [(control, args.expected_app_sha), (source, base.APPROVED_SOURCE)]:
        require(base.git(root, "rev-parse", "HEAD") == pin and not base.git(root, "status", "--porcelain"), "Exact clean source required")
    require(subprocess.check_output(["go", "version"], text=True, timeout=30).strip() == rpc.VERSION, "Pinned Go required")
    require(shutil.disk_usage(work.parent).free >= base.RESERVE, "Disk reserve below 8 GiB")
    work.mkdir(mode=0o700, exist_ok=False)
    manifest, fixture_sha, folder = fixture_inputs(control)
    client_sources = {}
    if native_client_fixtures is not None:
        require(set(native_client_fixtures) == {"native_client_phase_test.go", "native_client_boundary_test.go",
                                                "native_client_offline_test.go", "native_client_reopen_test.go", "native_client_crash_test.go",
                                                "native_client_observed_remove_test.go", "native_client_concurrent_replace_test.go"},
                "Only the seven explicit native-client test overlays are supported")
        for name, path in native_client_fixtures.items():
            require(path == tools / "two_clients" / name and path.is_file() and not path.is_symlink(),
                    "Native-client fixtures must be the exact source-bound test files")
            client_sources[name] = digest(path)
    if native_read_observation is not None:
        require(native_client_fixtures is not None
                and native_read_observation == tools / "two_clients/native-read-observation.patch"
                and digest(native_read_observation) == NATIVE_READ_OBSERVATION["patch_sha256"],
                "Observation requires the explicit source-bound native-client fixture")
        client_sources["native-read-observation.patch"] = digest(native_read_observation)
    client_fixture_sha = (hashlib.sha256(json.dumps(client_sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                          if client_sources else "none")
    rpc_manifest, registry = rpc.source_inputs(control, tools / "rpc")
    schema_sha = manifest["rpc_manifest_sha256"]
    generation_path = evidence / "generation/generation-receipt.json"
    generation = json.loads(generation_path.read_text())
    generation_identity(generation, args.expected_app_sha, receipt["run_id"], receipt["run_attempt"],
                        schema_sha, manifest["generated_sha256"])
    require(generation["schema_patch_sha256"] == rpc_manifest["patch_sha256"], "Different generated RPC schema")
    approval = source / base.APPROVAL
    old_patch = approval / "native-heart-integration.patch"
    old_inventory = approval / "native-heart-integration.json"
    require(digest(old_patch) == base.LEGACY_PATCH and digest(old_inventory) == base.LEGACY_INVENTORY
            and digest(source / base.BUILDER) == base.BUILDER_SHA, "Immutable r14/builder differs")
    old, _ = base.composition(json.loads(old_inventory.read_text()), registry)
    registration_sha = digest(tools / "heart-registration.patch")
    require(registration_sha == registry["patch_sha256"], "Private registry patch differs")
    new_fixtures = prepare_fixtures(control, work, manifest, folder, run)
    expected = {"legacy": old, "new": extend_generated_source(hearts["new"], generation, old, old_patch, run)}
    builds = {"new": {"module_hashes": generation["module_sha256"],
                       "source_hashes": base.verify_source(hearts["new"], expected["new"], generation["module_sha256"])}}
    builds["legacy"] = base.apply_composition(hearts["legacy"], old_patch, tools / "heart-registration.patch",
                                               tools / "overlay", registry, old, "legacy")
    observed_source, observation = None, None
    if native_read_observation is not None:
        observed_source, observation = prepare_native_read_observation(hearts["new"], native_read_observation, work, run)
    receipt.update(generation_receipt_sha256=digest(generation_path), fixture_sha256=fixture_sha,
                   rpc_manifest_sha256=schema_sha, generated_sha256=generation["generated_sha256"],
                   legacy_patch_sha256=base.LEGACY_PATCH, registration_patch_sha256=registration_sha,
                   composition_paths={role: sorted(value) for role, value in expected.items()},
                   native_read_observation=observation)
    spec = importlib.util.spec_from_file_location("t2_account_rpc_builder", source / base.BUILDER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    identities = {}
    for role, heart in hearts.items():
        role_work = work / ("build-" + role)
        role_work.mkdir()
        native = helper.fetch_tantivy(heart, "linux-amd64-musl")
        require(native["archive_sha256"] == closure.TANTIVY_SHA, "Wrong pinned Tantivy archive")
        gowork = role_work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + closure.GENPROTO_PATH + " => "
                          + closure.GENPROTO_PATH + " " + closure.GENPROTO_VERSION + "\n")
        env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2",
                   GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly", CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        run(["go", "mod", "download"], role + "-module-download", heart, env)
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", closure.GENPROTO_PATH], role + "-genproto", heart, env)
        selected = json.loads((evidence / (role + "-genproto.log")).read_text())
        effective = selected.get("Replace", selected)
        require(effective.get("Path") == closure.GENPROTO_PATH and effective.get("Version") == closure.GENPROTO_VERSION
                and effective.get("Sum") == closure.GENPROTO_SUM and effective.get("GoModSum") == closure.GENPROTO_MOD_SUM,
                "Wrong native genproto closure")
        names = ["account_phase_test.go", role + "_runtime_test.go"]
        fixture_root = tools / "account_lifecycle"
        if role == "new":
            names += ["native_handler_test.go", "native_rpc_account_test.go"]
            fixture_root = new_fixtures
        replacements = {}
        for name in names:
            target = heart / "clientlibrary/service" / ("pinkha_t2_" + name)
            require(not target.exists(), "Account fixture would replace native source")
            replacements[str(target)] = str(fixture_root / name)
        if role == "new" and native_client_fixtures:
            for name, path in native_client_fixtures.items():
                target = heart / "clientlibrary/service" / ("pinkha_t2_" + name)
                require(not target.exists(), "Native-client fixture would replace native source")
                replacements[str(target)] = str(path)
        if role == "new" and observed_source is not None:
            replacements[str(heart / NATIVE_READ_OBSERVATION["source_path"])] = str(observed_source)
        overlay = role_work / "overlay.json"
        write_json(overlay, {"Replace": replacements})
        summary = base.runtime_version(role, registration_sha)
        linked_registration = registration_sha if role == "new" else "none"
        flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + base.HEART
                 + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + summary
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountFixtureSHA=" + fixture_sha
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRuntimeRole=" + role
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRegistrationSHA=" + linked_registration)
        if role == "new":
            flags += " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2RPCAccountSchemaSHA=" + schema_sha
        if role == "new" and client_sources:
            flags += " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2NativeClientFixtureSHA=" + client_fixture_sha
        binary = role_work / ("pinkha-t2-rpc-" + role + ".test")
        run(["go", "test", "-c", "-p", "1", "-tags", base.TAGS, "-overlay", str(overlay), "-ldflags", flags,
             "-o", str(binary), "./clientlibrary/service"], role + "-compile", heart, env, 1800)
        identity = {"role": role, "heart_sha": base.HEART, "legacy_patch_sha256": base.LEGACY_PATCH,
                    "registration_patch_sha256": linked_registration, "fixture_sha256": fixture_sha,
                    "runtime_version": summary, "binary": str(binary), "binary_sha256": digest(binary),
                    "rpc_manifest_sha256": schema_sha if role == "new" else "none",
                    "native_client_fixture_sha256": client_fixture_sha if role == "new" else "none",
                    "native_read_observation": observation if role == "new" else None}
        verify_rpc_binary(role, identity, registration_sha, schema_sha)
        if client_sources:
            require(base.contains(binary, client_fixture_sha) == (role == "new"), "Native-client test linked into the wrong binary")
            actual_client_sources = {name: digest(path) for name, path in native_client_fixtures.items()}
            if native_read_observation is not None:
                actual_client_sources["native-read-observation.patch"] = digest(native_read_observation)
                require(digest(observed_source) == NATIVE_READ_OBSERVATION["after_sha256"], "Native observation source changed")
            require(actual_client_sources == client_sources,
                    "Native-client test source changed during compilation")
        verify_fixture_copy(new_fixtures, manifest)
        require(base.verify_source(heart, expected[role], builds[role]["module_hashes"]) == builds[role]["source_hashes"],
                "Native source changed during compilation")
        identities[role] = identity
        write_json(evidence / (role + "-build.json"), {**identity, **builds[role], "tantivy": native,
                                                      "genproto": effective, "overlay": replacements})
    require(identities["new"]["binary_sha256"] != identities["legacy"]["binary_sha256"], "Two distinct native binaries required")
    sequence = base.run_sequence(identities, registration_sha, work / "account-sequence", evidence, phase_validator=validate_phase)
    for role, heart in hearts.items():
        verify_rpc_binary(role, identities[role], registration_sha, schema_sha)
        require(base.verify_source(heart, expected[role], builds[role]["module_hashes"]) == builds[role]["source_hashes"],
                "Native source changed during account sequence")
    require(fixture_inputs(control)[1] == fixture_sha and digest(generation_path) == receipt["generation_receipt_sha256"],
            "Fixture or generation evidence changed during execution")
    verify_fixture_copy(new_fixtures, manifest)
    for root, pin in [(control, args.expected_app_sha), (source, base.APPROVED_SOURCE)]:
        require(base.git(root, "rev-parse", "HEAD") == pin and not base.git(root, "status", "--porcelain"), "Input source changed")
    if native_client_fixtures is not None:
        actual_client_sources = {name: digest(path) for name, path in native_client_fixtures.items()}
        if native_read_observation is not None:
            actual_client_sources["native-read-observation.patch"] = digest(native_read_observation)
            require(digest(observed_source) == NATIVE_READ_OBSERVATION["after_sha256"], "Native observation source changed")
        require(actual_client_sources == client_sources,
                "Native-client test source changed during baseline account proof")
    return {"status": PASS, "actual_counts": sequence["actual_counts"], "identities": identities,
            "native_client_fixture_sha256": client_fixture_sha, "native_client_source_sha256": client_sources,
            "native_read_observation": observation,
            "account_receipt_sha256": digest(evidence / "account-sequence/result.json"),
            "account_wire_acceptance": "PASS_REGISTERED_NATIVE_BYTES_SAME_ACCOUNT_FOUR_PROCESSES",
            "unknown_client_preservation": "PASS_R14_PRIVATE_HISTORY_BYTES",
            "search_export_cleanup": "PASS_UNCHANGED_BASELINE_ASSERTIONS"}


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
    path = args.evidence / "receipt.json"
    require(not path.exists(), "Fresh account-wire evidence required")
    receipt = {"status": "NOT_RUN_PREFLIGHT", "scope": SCOPE, "run_id": os.environ.get("GITHUB_RUN_ID"),
               "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
               "app_sha": args.expected_app_sha, "account_wire_acceptance": "NOT_RUN", "app_capability": "OFF",
               "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN", "full_t2_acceptance": "NOT_RUN",
               "commands": [], "started_at": datetime.now(timezone.utc).isoformat()}
    previous = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}
    cancelled = False
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous:
        signal.signal(number, cancel)
    def run(command, name, cwd, env, timeout=900):
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}
        receipt["commands"].append(entry)
        write_json(path, receipt)
        try:
            entry["pid"] = base.run_process(entry["argv"], cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as exc:
            entry["status"] = "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            write_json(path, receipt)
    result = 1
    try:
        receipt.update(execute(args, receipt, run))
        result = 0
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error=type(exc).__name__)
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    finally:
        def finish():
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            write_json(path, receipt)
            for item in args.evidence.rglob("*"):
                if item.is_dir():
                    item.chmod(0o755)
                elif item.is_file() and not item.is_symlink():
                    item.chmod(0o644)
        try:
            try:
                finish()
            except KeyboardInterrupt:
                result = 1
                receipt.update(status="CANCELLED", error="KeyboardInterrupt")
                finish()
        finally:
            for number, handler in previous.items():
                signal.signal(number, handler)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
