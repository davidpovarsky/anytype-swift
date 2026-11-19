#!/usr/bin/env python3
"""Source-bound bootstrap of two real native clients over an owned internal LAN.

The build stage retains the exact four-phase account/RPC baseline. The host
stage starts a new creator and a genuinely empty recovering client in separate
containers. Only the synthetic recovery key and public ID/hash expectations
cross the seed boundary; native peer transport must deliver all history.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from uuid import uuid4

import run_account_lifecycle as base
import run_account_rpc as account
import native_client_diagnostics as diagnostics
import native_client_observed_remove as observed_remove
import native_client_concurrent_replace as concurrent_replace

PROTOCOL = "pinkha-t2-two-native-clients-bootstrap-v1"
OFFLINE_PROTOCOL = "pinkha-t2-native-offline-conflict-reopen-v1"
METHOD = "TestT2NativeClientBootstrapPhase"
REOPEN_METHOD = "TestT2NativeClientOfflineReopenPhase"
CRASH_COMMIT_METHOD = "TestT2NativeClientCrashCommitPhase"
CRASH_RECOVER_METHOD = "TestT2NativeClientCrashRecoverPhase"
CRASH_PROTOCOL = "pinkha-t2-native-process-crash-after-commit-v1"
CRASH_METHODS = {CRASH_COMMIT_METHOD: ("crash-commit", "crash-native.log", "commit"),
                 CRASH_RECOVER_METHOD: ("crash-recover", "crash-recover-native.log", "recover")}
CRASH_CONTROL_METHODS = {
    "TestT2NativeCrashByteGateControls": {"actual_reply_is_held_until_failure_cancellation", "native_panic_never_arms_a_committed_reply",
                                         "fatal_close_still_runs_bounded_join"},
    "TestT2NativeCrashHistoryControls": {"one_signed_child_joins_both_existing_heads", "missing_commit", "extra_commit",
                                       "changed_original_bytes", "changed_original_parent", "missing_second_parent", "wrong_head"},
}
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"
OWNER_LABEL = "pinkha.t2.native-clients.owner"
GO_FILES = {"native_client_phase_test.go", "native_client_boundary_test.go",
            "native_client_offline_test.go", "native_client_reopen_test.go", "native_client_crash_test.go",
            "native_client_observed_remove_test.go", "native_client_concurrent_replace_test.go"}
STATE_KEYS = {"AccountID", "SpaceID", "DocumentID", "BlockID", "RootID", "OperationID",
              "OperationSHA256", "ClaimID", "ChangeID", "RawChanges", "Heads"}
CONTROL_METHODS = {
    "TestT2NativeClientByteBoundaryControls": {
        "success_owns_request_and_does_not_stop", "panic_is_redacted_and_native_stop_joins",
        "cancel_calls_stop_then_joins_original", "stuck_stop_and_call_leave_explicit_unjoined_failure"},
    "TestT2NativeClientReadReadinessControls": {
        "expected_claim_and_head_ready", "root_only_prefix_is_not_convergence", "history_unavailable_can_wait",
        "permission_denial_is_immediate_failure", "joined_denial_cannot_hide_in_transient_error",
        "foreign_claim_is_not_eventual_readiness", "failed_read_must_not_expose_a_snapshot"},
    "TestT2NativeClientReadObservationControls": {
        "invalid_envelope_is_fixed", "known_code_and_predicate_are_observed_without_private_fields",
        "unknown_code_is_not_exported"},
    "TestT2OfflineSnapshotConvergenceControls": {
        "complete_variants_and_unique_adds_converge", "local_sequence_is_not_a_cross_client_clock",
        "known_local_prefix_waits_without_convergence", "projection_catchup_can_wait",
        "known_account_history_cannot_disappear", "joined_permission_denial_is_not_retryable",
        "failed_read_cannot_expose_snapshot", "author_cannot_be_substituted", "opaque_payload_cannot_be_replaced",
        "removed_original_cannot_reappear", "duplicate_live_claims_are_rejected",
        "conflict_must_preserve_both_variants", "duplicate_conflict_variant_is_rejected", "conflict_has_no_live_winner"},
    "TestT2NativeLostReplyControls": {
        "exact_bytes_forwarded_once_reply_discarded", "panic_is_not_a_dropped_reply", "single_signed_commit_is_observed",
        "missing_commit_is_rejected", "additional_commit_is_rejected", "changed_original_is_rejected",
        "wrong_parent_is_rejected", "changed_original_parent_is_rejected", "wrong_head_is_rejected"},
}
require, digest, write = base.require, base.digest, base.write_json


def source_inputs(control: Path) -> tuple[dict, dict[str, Path]]:
    tools = control / "Tools/TorahNativeOperations"
    folder = tools / "two_clients"
    manifest = json.loads((folder / "fixture.json").read_text())
    require(manifest["protocol"] == PROTOCOL and manifest["image"] == IMAGE, "Different native-client contract/image")
    require(set(manifest["go_sources_sha256"]) == GO_FILES, "Different native-client test inputs")
    files = {name: folder / name for name in GO_FILES}
    require(all(path.is_file() and not path.is_symlink() and digest(path) == manifest["go_sources_sha256"][name]
                for name, path in files.items()), "Native-client test bytes differ")
    patch = folder / "native-read-observation.patch"
    require(patch.is_file() and not patch.is_symlink()
            and digest(patch) == manifest["native_read_observation_patch_sha256"] == account.NATIVE_READ_OBSERVATION["patch_sha256"],
            "Original native read observation differs")
    inputs = {**manifest["go_sources_sha256"], "native-read-observation.patch": digest(patch)}
    combined = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(combined == manifest["fixture_sha256"], "Native-client fixture identity differs")
    require(digest(tools / "run_account_rpc.py") == manifest["account_rpc_controller_sha256"], "Account build extension differs")
    decoder = tools / "native_client_diagnostics.py"
    require(decoder.is_file() and not decoder.is_symlink()
            and digest(decoder) == manifest["diagnostic_decoder_sha256"], "Fixed-schema diagnostic decoder differs")
    tail = tools / "native_client_observed_remove.py"
    require(tail.is_file() and not tail.is_symlink()
            and digest(tail) == manifest["observed_remove_controller_sha256"], "Observed-remove source-bound controller differs")
    for name, key in [("native_client_concurrent_replace.py", "concurrent_replace_controller_sha256"),
                      ("test_native_client_concurrent_replace.py", "concurrent_replace_controls_sha256")]:
        path = tools / name
        require(path.is_file() and not path.is_symlink() and digest(path) == manifest[key],
                "Concurrent-replace source-bound controller or controls differ")
    return manifest, files


def validate_native_controls(text: str) -> dict:
    actual = re.findall(r"^\s*--- PASS: (\S+) \(", text, re.M)
    expected = {name for name in CONTROL_METHODS}
    expected.update(name + "/" + subcase for name, cases in CONTROL_METHODS.items() for subcase in cases)
    require(set(actual) == expected and len(actual) == len(expected)
            and "--- FAIL:" not in text and "--- SKIP:" not in text, "Native boundary/readiness controls incomplete")
    return {"top_level": len(CONTROL_METHODS), "subcases": len(expected) - len(CONTROL_METHODS), "pass_terminals": len(actual),
            "fail": 0, "skip": 0}


def validate_public_state(state: dict) -> None:
    require(set(state) == STATE_KEYS, "Only public expected IDs/hashes may be seeded")
    base.validate_state(state)


def build(args, receipt, run) -> dict:
    manifest, files = source_inputs(args.control)
    result = account.execute(args, receipt, run, native_client_fixtures=files,
                             native_read_observation=args.control / "Tools/TorahNativeOperations/two_clients/native-read-observation.patch")
    require(result["status"] == account.PASS and result["native_client_fixture_sha256"] == manifest["fixture_sha256"],
            "Exact account baseline or native-client fixture linkage failed")
    receipt["baseline"] = result
    require(result["native_read_observation"] == {**account.NATIVE_READ_OBSERVATION,
            "scope": "TEST_COMPILE_OVERLAY_ONLY_ORIGINAL_READ_ERROR"}, "Original read observation source linkage failed")
    binary = Path(result["identities"]["new"]["binary"])
    methods = "^(" + "|".join(CONTROL_METHODS) + ")$"
    run([binary, "-test.run", methods, "-test.count=1", "-test.v", "-test.timeout=60s"],
        "native-client-boundary-controls", args.work, dict(os.environ, GOMAXPROCS="2"), 90)
    controls = validate_native_controls((args.evidence / "native-client-boundary-controls.log").read_text())
    crash_controls = {"status": "NOT_RUN"}
    if args.crash_after_commit:
        methods = "^(" + "|".join(CRASH_CONTROL_METHODS) + ")$"
        run([binary, "-test.run", methods, "-test.count=1", "-test.v", "-test.timeout=60s"],
            "native-client-crash-controls", args.work, dict(os.environ, GOMAXPROCS="2"), 90)
        crash_controls = validate_crash_native_controls((args.evidence / "native-client-crash-controls.log").read_text())
    require(source_inputs(args.control)[0] == manifest, "Native-client source changed during build")
    # This one executable is made readable to the host. Private account stores,
    # keys, build caches and generated source remain in their private work dirs.
    runtime = args.work.parent / "client-runtime"
    require(not runtime.exists(), "Fresh exported runtime directory required")
    runtime.mkdir(mode=0o755)
    runtime.chmod(0o755)
    target = runtime / "native.test"
    shutil.copyfile(binary, target)
    target.chmod(0o555)
    require(digest(target) == result["identities"]["new"]["binary_sha256"], "Runtime copy differs from compiled binary")
    return {"status": "PASS_NATIVE_BUILD_AND_BASELINE_ONLY", "baseline": result, "native_controls": controls,
            "crash_native_controls": crash_controls,
            "runtime": {"relative_path": "client-runtime/native.test", "sha256": digest(target), "uploaded": False},
            "fixture_sha256": manifest["fixture_sha256"], "two_native_clients": "NOT_RUN"}


def native_arguments(scenario="bootstrap", method=METHOD) -> list[str]:
    require(scenario in {"bootstrap", "offline"} and method in {METHOD, REOPEN_METHOD, *CRASH_METHODS,
            *observed_remove.METHODS.values(), *concurrent_replace.METHODS.values()}, "Unknown fixed native scenario")
    require(method == METHOD or scenario == "offline", "Reopen is exclusive to the offline scenario")
    limit = "480s" if method != METHOD else ("2000s" if scenario == "offline" else "1000s")
    if method in {*observed_remove.METHODS.values(), *concurrent_replace.METHODS.values()}:
        limit = "720s"  # Only the new fixed causal process; existing phase caps stay unchanged.
    return ["-test.run", "^" + method + "$", "-test.count=1", "-test.v", "-test.timeout=" + limit]


def validate_container(info: dict, owner: str, role: str, network: dict | None, private: Path, binary: Path,
                       image_id: str, uid: int, gid: int, *, scenario="bootstrap", method=METHOD) -> None:
    require(info.get("Config", {}).get("Labels", {}).get(OWNER_LABEL) == owner, "Foreign container ownership")
    require(info["Config"].get("Image") == IMAGE and info.get("Image") == image_id, "Different runtime image")
    require(info["Config"].get("User") == f"{uid}:{gid}" and info.get("Path") == "/fixture/native.test",
            "Container must directly run the native ELF as the owner")
    require(info.get("Args") == native_arguments(scenario, method),
            "Unexpected native executable arguments")
    host = info["HostConfig"]
    require(host.get("ReadonlyRootfs") is True and host.get("Privileged") is False
            and host.get("CapDrop") == ["ALL"] and "no-new-privileges" in host.get("SecurityOpt", [])
            and host.get("NetworkMode") == (network["Name"] if network else "none") and not host.get("PortBindings")
            and not host.get("PidMode") and not host.get("Init"), "Unexpected native container isolation")
    mounts = info.get("Mounts", [])
    binds = {m["Destination"]: m for m in mounts if m.get("Type") == "bind"}
    require(set(binds) == {"/private", "/fixture/native.test"}, "Container can see another client or build tree")
    require(binds["/private"]["Source"] == str(private) and binds["/private"]["RW"] is True
            and binds["/fixture/native.test"]["Source"] == str(binary)
            and binds["/fixture/native.test"]["RW"] is False, "Wrong native data/binary bind")
    require(all(m.get("Type") == "bind" or (m.get("Type") == "tmpfs" and m.get("Destination") == "/tmp") for m in mounts),
            "Unexpected data volume")
    networks = info["NetworkSettings"]["Networks"]
    if network:
        require(set(networks) == {network["Name"]} and networks[network["Name"]]["NetworkID"] == network["Id"],
                "Native client is not isolated to its owned internal LAN")
    else:
        require(set(networks) == {"none"} and not networks["none"].get("IPAddress"),
                "Reopen must have no network capable of peer repair")
    env = dict(value.split("=", 1) for value in info["Config"]["Env"] if "=" in value)
    require(env.get("PINKHA_T2_CLIENT_ROLE") == role and env.get("PINKHA_T2_CLIENT_NONCE") == owner,
            "Native container role/nonce differs")
    require(env.get("PINKHA_T2_CLIENT_SCENARIO") == (OFFLINE_PROTOCOL if scenario == "offline" else None),
            "Native scenario differs from the explicit controller selection")
    require(env.get("PINKHA_T2_CRASH_PHASE") == (CRASH_METHODS[method][2] if method in CRASH_METHODS else None),
            "Native crash phase differs from the exact selected method")
    require(env.get("PINKHA_T2_OBSERVED_REMOVE_PHASE") ==
            (observed_remove.PROTOCOL if method in observed_remove.METHODS.values() else None),
            "Native causal phase differs from the exact selected method")
    require(method not in observed_remove.METHODS.values() or method == observed_remove.METHODS[role],
            "Causal method must match its original device role")
    require(env.get("PINKHA_T2_CONCURRENT_REPLACE_PHASE") ==
            (concurrent_replace.PROTOCOL if method in concurrent_replace.METHODS.values() else None),
            "Native concurrent-replace phase differs from the exact selected method")
    require(method not in concurrent_replace.METHODS.values() or method == concurrent_replace.METHODS[role],
            "Concurrent-replace method must match its original device role")


def validate_ready(report: dict, role: str, nonce: str, state: dict, state_hash: str,
                   identity: dict, fixture_sha: str, info: dict, network: dict) -> None:
    require(report.get("protocol") == PROTOCOL and report.get("role") == role and report.get("nonce") == nonce,
            "Foreign native readiness receipt")
    require(report.get("pid") == 1 and type(info["State"].get("Pid")) is int and info["State"]["Pid"] > 0
            and info["State"].get("Running") is True, "Native client process is not alive")
    require(report.get("network_namespace") == os.readlink(f"/proc/{info['State']['Pid']}/ns/net"),
            "Native namespace is not the observed container process")
    require(report.get("bridge_ipv4") == info["NetworkSettings"]["Networks"][network["Name"]]["IPAddress"],
            "Native interface differs from its owned bridge")
    require(isinstance(report.get("peer_id"), str) and bool(report["peer_id"])
            and type(report.get("native_server_port")) is int and 0 < report["native_server_port"] < 65536,
            "Actual native peer/server identity missing")
    for key, source_key in {"heart_sha": "heart_sha", "runtime_version": "runtime_version",
                            "account_fixture_sha256": "fixture_sha256", "rpc_manifest_sha256": "rpc_manifest_sha256",
                            "registration_patch_sha256": "registration_patch_sha256"}.items():
        require(report.get(key) == identity[source_key], "Native source identity mismatch: " + key)
    require(report.get("client_fixture_sha256") == fixture_sha and report.get("state_sha256") == state_hash,
            "Native fixture or original expected state differs")
    for key, state_key in {"account_id": "AccountID", "space_id": "SpaceID", "document_id": "DocumentID",
                            "block_id": "BlockID", "private_root_id": "RootID"}.items():
        require(report.get(key) == state[state_key], "Different original native target")
    require(report.get("raw_changes_sha256") == state["RawChanges"] and report.get("heads") == state["Heads"],
            "Original signed history did not reach the independent client")
    require(report.get("initial_account_root") == "OBSERVED_EMPTY" and report.get("native_local_only_requested") is True
            and report.get("native_lan_enabled_requested") is True and report.get("ordinary_document") == "PASS_NATIVE_OBJECT_SHOW"
            and report.get("private_read") == "PASS_GENERATED_RPC_ORIGINAL_SIGNED_HISTORY", "Native bootstrap observations incomplete")
    require(report.get("active_private_append") == ("ONE_CREATOR_GENERATED_RPC_APPEND" if role == "creator" else "NONE_RECOVERED_CLIENT_READ_ONLY"),
            "Recovering client must not synthesize its own private history")
    require(report.get("app_capability") == "OFF" and report.get("two_ios_apps") == "NOT_RUN"
            and report.get("offline_conflict_merge") == "NOT_RUN" and not report.get("test_passed"), "Readiness overstates acceptance")


def validate_pair(reports: dict, inspections: dict) -> None:
    require(set(reports) == set(inspections) == {"creator", "recovered"}, "Both native clients required")
    for key in ["peer_id", "network_namespace", "bridge_ipv4"]:
        require(len({r[key] for r in reports.values()}) == 2, "Native clients share " + key)
    require(len({v["State"]["Pid"] for v in inspections.values()}) == 2, "Two distinct actual host processes required")
    require(len({v["NetworkSettings"]["SandboxID"] for v in inspections.values()}) == 2, "Two network sandboxes required")
    require(reports["creator"]["raw_changes_sha256"] == reports["recovered"]["raw_changes_sha256"], "Private history differs")


def validate_final(ready: dict, final: dict, log: str, role: str, *, scenario="bootstrap") -> None:
    require(all(final.get(key) == value for key, value in ready.items()), "Readiness facts changed before AccountStop")
    require(final.get("closed") is True and final.get("account_stop_verified") is True and final.get("test_passed") is True
            and final.get("post_stop_rpc") == "READ_AND_APPEND_NOT_LOGGED_IN", "Actual native shutdown/denial proof missing")
    require(("--- PASS: " + METHOD + " ") in log and log.count("--- PASS:") == 1
            and "--- FAIL:" not in log and "--- SKIP:" not in log, "Exact native named PASS required")
    calls = final.get("rpc_calls", {})
    require(calls == final.get("returned_byte_calls"), "Native byte call did not return")
    common = {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1,
              "DeviceNetworkStateSet": 3 if scenario == "offline" and role == "recovered" else 1,
              "ObjectShow": 1, "AccountStop": 1, "AppShutdown": 1,
              "PinkhaTorahOperationsAppend": (2 if role == "creator" else 1) + (8 if scenario == "offline" else 0)}
    require(all(calls.get(key) == count for key, count in common.items())
            and calls.get("PinkhaTorahOperationsReadTarget", 0) >= (11 if scenario == "offline" else 2), "Native call boundary incomplete")
    creator = {"WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"}
    recovery = {"WalletRecover", "AccountSelect"}
    require(all(calls.get(key, 0) == (1 if role == "creator" else 0) for key in creator)
            and all(calls.get(key, 0) == (1 if role == "recovered" else 0) for key in recovery)
            and calls.get("AccountMigrate", 0) == 0, "Cold recovery recreated or seeded native data")
    require(calls.get("ObjectSearch", 0) >= 1 if role == "creator" else calls.get("ObjectSearch", 0) == 0,
            "Unexpected native Page-readiness calls")
    require(set(calls) <= set(common) | creator | recovery | {"ObjectSearch", "PinkhaTorahOperationsReadTarget"},
            "Unexpected native operation outside LAN bootstrap")


def publish_native_evidence(private: Path, evidence: Path, *, scenario="bootstrap", crash_after_commit=False,
                            observed_remove_after_reopen=False, concurrent_replace_after_reopen=False) -> dict:
    concurrent_replace.validate_selection(scenario, crash_after_commit, observed_remove_after_reopen, concurrent_replace_after_reopen)
    needle_path = private / "creator/sensitive-needles.private"
    if not needle_path.is_file() or needle_path.is_symlink():
        return {"status": "WITHHELD_NO_SECRET_INVENTORY", "files_sha256": {}}
    needles = json.loads(needle_path.read_text())
    require(isinstance(needles, list) and len(needles) == 2 and len(set(needles)) == 2
            and all(isinstance(n, str) and len(n) >= 10 for n in needles), "Incomplete synthetic secret inventory")
    candidates = []
    for role in ["creator", "recovered"]:
        names = ["ownership.json", "state.json", "ready.json", "final.json", "cancel.json", "native.log"]
        if scenario == "offline":
            names += ["partitioned.json", "diverged.json", "reconnected.json", "converged.json",
                      "reopen-ready.json", "reopened.json", "reopen-native.log"]
        if crash_after_commit and role == "creator":
            names += ["crash-armed.json", "crash-recover-ready.json", "crash-recovered.json", "crash-native.log", "crash-recover-native.log"]
        if observed_remove_after_reopen:
            names += sorted(observed_remove.FILES) + [observed_remove.LOG]
        if concurrent_replace_after_reopen:
            names += sorted(concurrent_replace.FILES) + [concurrent_replace.LOG]
        for name in names:
            path = private / role / name
            if not path.exists():
                continue
            require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(private)
                    and path.stat().st_size <= 64 * 1024**2, "Unsafe native evidence file")
            require(not any(base.contains(path, needle) for needle in needles), "Synthetic secret detected; native evidence withheld")
            candidates.append(path)
    target = evidence / "native-clients"
    require(not target.exists(), "Fresh native publication directory required")
    target.mkdir(mode=0o755)
    files = {}
    for path in candidates:
        relative = path.relative_to(private)
        output = target / relative
        output.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        shutil.copyfile(path, output)
        output.chmod(0o644)
        files[relative.as_posix()] = digest(output)
    return {"status": "PASS_SECRET_SCANNED_EXACT_ALLOWLIST", "files_sha256": files}


class OwnedDocker:
    def __init__(self, private: Path, receipt: dict, checkpoint, *, scenario="bootstrap", crash_after_commit=False,
                 observed_remove_after_reopen=False, concurrent_replace_after_reopen=False):
        concurrent_replace.validate_selection(scenario, crash_after_commit, observed_remove_after_reopen, concurrent_replace_after_reopen)
        self.private, self.receipt, self.checkpoint = private, receipt, checkpoint
        self.owner = uuid4().hex
        self.prefix = "pinkha-t2-" + self.owner[:16]
        self.resources = []
        self.receipt["owned_resources"] = self.resources
        self.receipt["owner_nonce"] = self.owner
        self.command_index = 0
        self.scenario, self.crash_after_commit = scenario, crash_after_commit
        self.observed_remove_after_reopen = observed_remove_after_reopen
        self.concurrent_replace_after_reopen = concurrent_replace_after_reopen

    def command(self, args, name, timeout=30, destination=None):
        self.command_index += 1
        log = destination or self.private / f"docker-{self.command_index:04d}-{name}.log"
        entry = {"name": name, "argv": ["docker", *map(str, args)], "status": "RUNNING"}
        self.receipt["commands"].append(entry)
        self.checkpoint()
        try:
            entry["pid"] = base.run_process(entry["argv"], self.private, os.environ.copy(), log, timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry["status"] = "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            entry["finished_at"] = datetime.now(timezone.utc).isoformat()
            if log.exists():
                entry["output_sha256"] = digest(log)
            self.checkpoint()
        if destination is not None:
            return ""
        require(log.stat().st_size < 1024**2, "Unexpected Docker metadata size")
        return log.read_text().strip()

    @staticmethod
    def remaining(deadline, maximum=30):
        if deadline is None:
            return maximum
        remaining = deadline - time.monotonic()
        require(remaining > 0, "Fixed native phase deadline expired")
        return min(maximum, remaining)

    def find(self, resource, deadline=None):
        name_pattern = "^" + ("/" if resource["kind"] == "container" else "") + resource["name"] + "$"
        args = [resource["kind"], "ls", "--filter", "label=" + OWNER_LABEL + "=" + self.owner,
                "--filter", "name=" + name_pattern, "--format", "{{.ID}}"]
        if resource["kind"] == "container":
            args.insert(2, "--all")
        matches = self.command(args, "find-owned", self.remaining(deadline)).splitlines()
        require(len(matches) <= 1, "Ambiguous owned Docker resource")
        if not matches:
            return None
        value = json.loads(self.command([resource["kind"], "inspect", matches[0]], "inspect-owned", self.remaining(deadline)))[0]
        labels = value.get("Config", {}).get("Labels", {}) if resource["kind"] == "container" else value.get("Labels", {})
        require(labels.get(OWNER_LABEL) == self.owner and value.get("Name", "").lstrip("/") == resource["name"],
                "Refuse foreign Docker resource")
        if resource.get("id"):
            require(resource["id"] == value["Id"], "Owned Docker identity changed")
        resource["id"] = value["Id"]
        return value

    def network(self):
        resource = {"kind": "network", "name": self.prefix, "id": None}
        self.resources.append(resource)  # Record intent before daemon mutation.
        identifier = self.command(["network", "create", "--driver", "bridge", "--internal",
                                   "--label", OWNER_LABEL + "=" + self.owner, resource["name"]], "create-owned-lan")
        require(re.fullmatch(r"[0-9a-f]{64}", identifier), "Missing owned network identity")
        resource["id"] = identifier
        info = self.find(resource)
        require(info and info["Internal"] is True and info["Driver"] == "bridge" and not info.get("Containers"),
                "Fresh internal native LAN required")
        return resource, info

    def start(self, role, network, directory, binary, fixture_sha, deadline, *, method=METHOD):
        reopening = method == REOPEN_METHOD
        require(method not in CRASH_METHODS or (self.crash_after_commit and role == "creator" and network is None),
                "Crash process requires its explicit creator-only disconnected tail")
        require(method not in observed_remove.METHODS.values() or
                (self.observed_remove_after_reopen and method == observed_remove.METHODS[role] and network is not None),
                "Causal process requires its explicit original-role LAN tail")
        require(method not in concurrent_replace.METHODS.values() or
                (self.concurrent_replace_after_reopen and method == concurrent_replace.METHODS[role] and network is not None),
                "Concurrent-replace process requires its explicit original-role LAN tail")
        suffix, log_name = ("reopen", "reopen-native.log") if reopening else ("", "native.log")
        if method in CRASH_METHODS:
            suffix, log_name, _ = CRASH_METHODS[method]
        if method in observed_remove.METHODS.values():
            suffix, log_name = "observed-remove", observed_remove.LOG
        if method in concurrent_replace.METHODS.values():
            suffix, log_name = "concurrent-replace", concurrent_replace.LOG
        resource = {"kind": "container", "name": self.prefix + "-" + role + ("-" + suffix if suffix else ""),
                    "id": None, "role": role, "private": str(directory), "log": log_name}
        self.resources.append(resource)
        args = ["container", "create", "--name", resource["name"], "--label", OWNER_LABEL + "=" + self.owner,
                "--platform", "linux/amd64", "--network", network["Name"] if network else "none", "--read-only", "--init=false",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
                "--cpus", "1", "--memory", "2g", "--pids-limit", "256", "--workdir", "/private",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777",
                "--mount", f"type=bind,src={directory},dst=/private",
                "--mount", f"type=bind,src={binary},dst=/fixture/native.test,readonly",
                "-e", "PINKHA_T2_CLIENT_ROLE=" + role, "-e", "PINKHA_T2_CLIENT_NONCE=" + self.owner,
                "-e", "PINKHA_T2_CLIENT_FIXTURE_SHA=" + fixture_sha, "-e", "GOMAXPROCS=2", "-e", "GOMEMLIMIT=768MiB"]
        if self.scenario == "offline":
            args += ["-e", "PINKHA_T2_CLIENT_SCENARIO=" + OFFLINE_PROTOCOL]
        if method in CRASH_METHODS:
            args += ["-e", "PINKHA_T2_CRASH_PHASE=" + CRASH_METHODS[method][2]]
        if method in observed_remove.METHODS.values():
            args += ["-e", "PINKHA_T2_OBSERVED_REMOVE_PHASE=" + observed_remove.PROTOCOL]
        if method in concurrent_replace.METHODS.values():
            args += ["-e", "PINKHA_T2_CONCURRENT_REPLACE_PHASE=" + concurrent_replace.PROTOCOL]
        args += [IMAGE, "/fixture/native.test", *native_arguments(self.scenario, method)]
        resource["id"] = self.command(args, "create-" + role, self.remaining(deadline))
        require(re.fullmatch(r"[0-9a-f]{64}", resource["id"]), "Missing actual native container identity")
        self.command(["container", "start", resource["id"]], "start-" + role, self.remaining(deadline))
        return resource

    def wait_ready(self, resource, deadline, *, filename="ready.json"):
        require(filename in {"ready.json", "partitioned.json", "diverged.json", "reconnected.json", "converged.json", "reopen-ready.json", "crash-armed.json", "crash-recover-ready.json", *observed_remove.FILES - {"observed-final.json"},
                *concurrent_replace.FILES - {"replace-final.json"}},
                "Unexpected native receipt selection")
        path = Path(resource["private"]) / filename
        next_check = 0
        while time.monotonic() < deadline:
            if path.exists():
                require(path.is_file() and not path.is_symlink(), "Unsafe readiness receipt")
                return json.loads(path.read_text())
            if time.monotonic() >= next_check:
                info = self.find(resource, deadline)
                require(info and info["State"].get("Running") is True, "Native client exited before readiness")
                next_check = time.monotonic() + 5
            time.sleep(0.2)
        raise TimeoutError("Bounded native cold bootstrap did not become ready")

    def cleanup(self):
        errors = []
        for resource in reversed(self.resources):
            try:
                info = self.find(resource)
                if not info:
                    continue
                if resource["kind"] == "container":
                    try:
                        if info["State"].get("Running"):
                            # The successful path already used native AccountStop.
                            # This is bounded failure/cancellation cleanup only.
                            self.command(["container", "stop", "--time", "1", resource["id"]], "stop-owned", 10)
                        log = Path(resource["private"]) / resource.get("log", "native.log")
                        if not log.exists():
                            self.command(["container", "logs", resource["id"]], "capture-owned-log", 10, log)
                    except Exception as error:
                        errors.append({"kind": "container", "name": resource["name"], "error_type": type(error).__name__})
                    finally:
                        require(self.find(resource) is not None, "Owned container vanished before removal")
                        self.command(["container", "rm", "--force", resource["id"]], "remove-owned", 10)
                else:
                    require(not info.get("Containers"), "Owned network has active containers; refuse indirect removal")
                    self.command(["network", "rm", resource["id"]], "remove-owned-lan", 30)
            except Exception as error:
                errors.append({"kind": resource["kind"], "name": resource["name"], "error_type": type(error).__name__})
        self.receipt["owned_cleanup"] = {"status": "FAIL" if errors else "PASS", "errors": errors}
        self.checkpoint()
        require(not errors, "Owned native resource cleanup failed")


def validate_offline_report(report: dict, phase: str, role: str, ready: dict, expected_ips: list[str]) -> None:
    require(report.get("protocol") == OFFLINE_PROTOCOL and report.get("phase") == phase
            and report.get("role") == role and report.get("nonce") == ready["nonce"]
            and report.get("pid") == 1 and report.get("client_fixture_sha256") == ready["client_fixture_sha256"]
            and report.get("peer_id") == ready["peer_id"], "Foreign offline phase receipt")
    require(report.get("actual_ipv4") == expected_ips
            and report.get("native_network_state") == ("WIFI" if expected_ips else "NOT_CONNECTED"),
            "Native network notification does not match actual attachment")
    require(report.get("app_capability") == "OFF" and report.get("full_t2_acceptance") == "NOT_RUN", "Offline phase overclaims acceptance")


def validate_lost_client_reply(proof: dict, report: dict, state: dict) -> None:
    expected_keys = {"protocol", "scope", "first_reply_decoded", "fixed_deadline_ms", "discarded_responses",
                     "discarded_response_bytes", "native_append_attempts", "request_sha256", "retry_request_sha256",
                     "request_bytes", "claim_id", "committed_change_id", "commit_observed_before_read", "history_before",
                     "history_committed", "history_after_read", "history_after_retry", "retry_disposition", "retry_change_id",
                     "snapshot_before_retry_sha256", "snapshot_after_retry_sha256", "local_sequence_before_retry",
                     "local_sequence_after_retry", "crash_after_commit"}
    require(isinstance(proof, dict) and set(proof) == expected_keys, "Exact lost client-reply observations required")
    require(proof["protocol"] == "pinkha-t2-lost-client-reply-v1"
            and proof["scope"] == "DROPPED_CLIENT_BYTE_REPLY_NOT_PACKET_LOSS_OR_CRASH"
            and proof["first_reply_decoded"] is False and proof["commit_observed_before_read"] is True
            and proof["crash_after_commit"] == "NOT_RUN", "Lost-reply observation changed its acceptance scope")
    for key, count in {"discarded_responses": 1, "native_append_attempts": 2, "fixed_deadline_ms": 60000}.items():
        require(type(proof[key]) is int and proof[key] == count, "Lost-reply boundary count/deadline differs")
    for key in ["discarded_response_bytes", "request_bytes", "local_sequence_before_retry", "local_sequence_after_retry"]:
        require(type(proof[key]) is int and proof[key] > 0, "Lost-reply byte or sequence observation missing")
    for key in ["request_sha256", "retry_request_sha256", "snapshot_before_retry_sha256", "snapshot_after_retry_sha256"]:
        require(isinstance(proof[key], str) and re.fullmatch(r"[0-9a-f]{64}", proof[key]), "Lost-reply byte identity missing")
    require(proof["request_sha256"] == proof["retry_request_sha256"]
            and proof["snapshot_before_retry_sha256"] == proof["snapshot_after_retry_sha256"]
            and proof["local_sequence_before_retry"] == proof["local_sequence_after_retry"],
            "Lost-reply retry changed the request, complete snapshot or local sequence")
    change_id, claim_id = report["created_change_ids"][0], report["created_claim_ids"][0]
    before = {"changes_sha256": state["RawChanges"], "parents": {state["ChangeID"]: [state["RootID"]]}, "heads": state["Heads"]}
    committed = {"changes_sha256": {**state["RawChanges"], change_id: report["history"]["changes_sha256"][change_id]},
                 "parents": {state["ChangeID"]: [state["RootID"]], change_id: state["Heads"]}, "heads": [change_id]}
    require(proof["history_before"] == before and proof["history_committed"] == committed
            and proof["history_after_read"] == committed and proof["history_after_retry"] == committed,
            "Commit must precede ReadTarget; read and retry cannot add, remove or replace signed history")
    require(proof["claim_id"] == claim_id and proof["committed_change_id"] == change_id
            and proof["retry_disposition"] == "ALREADY_EXISTS_SAME_PAYLOAD" and proof["retry_change_id"] == "",
            "Lost-reply retry did not recover the one existing native claim")


def merge_offline_histories(reports: dict, state: dict) -> dict:
    require(set(reports) == {"creator", "recovered"}, "Two original branch histories required")
    common = set(state["RawChanges"])
    changes, parents, heads, branch_ids, claim_ids = dict(state["RawChanges"]), {}, [], set(), set()
    for role, report in reports.items():
        history, new_changes, new_claims = report["history"], report["created_change_ids"], report["created_claim_ids"]
        require(len(new_changes) == len(set(new_changes)) == 3 and len(new_claims) == len(set(new_claims)) == 3,
                "Each disconnected client must commit three distinct changes/claims")
        require(all(isinstance(value, str) and value and value not in common for value in new_changes)
                and not branch_ids.intersection(new_changes), "Private branches were shared or overwritten")
        require(all(re.fullmatch(r"[0-9a-f]{64}/[0-9a-f]{64}", value) for value in new_claims)
                and not claim_ids.intersection(new_claims), "Physical immutable claims must remain distinct")
        branch_ids.update(new_changes); claim_ids.update(new_claims)
        require(set(history) == {"changes_sha256", "parents", "heads"}
                and set(history["changes_sha256"]) == common | set(new_changes)
                and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in history["changes_sha256"].values()),
                "Only exact native change hashes may cross the expectation boundary")
        require(all(history["changes_sha256"][key] == value for key, value in state["RawChanges"].items()), "Original history changed offline")
        expected_parents = {state["ChangeID"]: [state["RootID"]], new_changes[0]: [state["ChangeID"]],
                            new_changes[1]: [new_changes[0]], new_changes[2]: [new_changes[1]]}
        require(history["parents"] == expected_parents and history["heads"] == [new_changes[2]],
                "Offline branch is not the independently signed three-operation chain")
        require(report.get("retry_and_collision") == "PASS_LOCAL_EXACT_RETRY_AND_REJECTED_DIFFERENT_BYTES"
                and report.get("removed_observed_original") is True
                and re.fullmatch(r"[0-9a-f]{64}", report.get("local_snapshot_sha256", "")), "Offline append/retry/remove proof incomplete")
        validate_lost_client_reply(report.get("lost_client_reply"), report, state)
        changes.update(history["changes_sha256"]); parents.update(expected_parents); heads += history["heads"]
    require(reports["creator"]["created_claim_ids"][1][:64] == reports["recovered"]["created_claim_ids"][1][:64],
            "Different-payload collision must use the same logical operation ID")
    require(reports["creator"]["local_snapshot_sha256"] != reports["recovered"]["local_snapshot_sha256"],
            "Disconnected clients did not observe different local states")
    require(len(changes) == 8 and len(parents) == 7 and len(set(heads)) == 2, "Complete original branch union required")
    return {"changes_sha256": changes, "parents": parents, "heads": sorted(heads)}


def validate_convergence(reports: dict, expected: dict) -> str:
    require(set(reports) == {"creator", "recovered"}, "Two actual convergence receipts required")
    hashes = set()
    for report in reports.values():
        require(report.get("history") == expected and report.get("live_count") == 2
                and report.get("conflict_count") == 1 and report.get("conflict_variants") == 2,
                "Native convergence dropped history, a concurrent add or a conflict variant")
        require(report.get("retry_and_collision") == "PASS_CONFLICT_VARIANTS_PRESERVED_IDEMPOTENT_REPLAY"
                and report.get("concurrent_remove_add_remove") == "OBSERVED_ORIGINAL_REMOVED_CONCURRENT_UNIQUE_ADDS_RETAINED"
                and report.get("restart") == "NOT_RUN" and report.get("crash_after_commit") == "NOT_RUN",
                "Native convergence assertion scope differs")
        value = report.get("snapshot_sha256_without_local_sequence", "")
        require(re.fullmatch(r"[0-9a-f]{64}", value) and type(report.get("local_applied_sequence")) is int
                and report["local_applied_sequence"] > 0, "Missing complete semantic snapshot/local sequence")
        hashes.add(value)
    require(len(hashes) == 1, "Native clients did not converge to the same complete semantic snapshot")
    return hashes.pop()


def offline_command(directory: Path, role: str, owner: str, phase: str, history: dict | None = None) -> None:
    require(phase in {"partition", "write", "reconnect", "reopen-stop"}, "Unknown fixed offline command")
    require((phase == "reconnect") == (history is not None), "History expectations belong only to reconnect")
    if history is not None:
        require(set(history) == {"changes_sha256", "parents", "heads"}, "Expected history cannot carry native bytes or extra fields")
        changes, parents, heads = history["changes_sha256"], history["parents"], history["heads"]
        require(isinstance(changes, dict) and len(changes) == 8
                and all(isinstance(key, str) and 0 < len(key) <= 512 and "\x00" not in key for key in changes)
                and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) for value in changes.values()),
                "Expected changes must contain exactly eight native identifiers and SHA256 hashes")
        require(isinstance(parents, dict) and len(parents) == 7 and set(parents) < set(changes)
                and all(isinstance(value, list) and len(value) == 1 and value[0] in changes and value[0] != key
                        for key, value in parents.items()), "Expected native parents differ from the two reviewed branches")
        require(isinstance(heads, list) and len(heads) == 2 and len(set(heads)) == 2 and heads == sorted(heads)
                and set(heads) == set(changes) - {value[0] for value in parents.values()}, "Expected native heads are not the exact two branch tips")
    path = directory / (phase + ".command.json")
    require(not path.exists(), "Offline command cannot be replayed or replaced")
    write(path, {"protocol": OFFLINE_PROTOCOL, "nonce": owner, "role": role, "phase": phase,
                 "expected_history": history or {"changes_sha256": {}, "parents": {}, "heads": []}})


def offline_sequence(docker: OwnedDocker, resources: dict, network_resource: dict, network: dict,
                     reports: dict, directories: dict, state: dict) -> dict:
    # One bounded phase budget covers all partition/write/reconnect operations.
    overall = time.monotonic() + 630
    deadline = min(overall, time.monotonic() + 90)
    b = docker.find(resources["recovered"], deadline)
    lan = docker.find(network_resource, deadline)
    require(b and b["State"].get("Running") is True and b["State"]["Pid"] == docker.receipt["native_peers"]["recovered"]["host_pid"]
            and set(b["NetworkSettings"]["Networks"]) == {network["Name"]}
            and set(lan.get("Containers", {})) == {r["id"] for r in resources.values()}, "Original owned native LAN membership changed")
    docker.command(["network", "disconnect", network["Id"], resources["recovered"]["id"]], "detach-owned-recovered", docker.remaining(deadline))
    detached = docker.find(resources["recovered"], deadline)
    lan = docker.find(network_resource, deadline)
    require(detached["State"].get("Running") is True and detached["State"]["Pid"] == b["State"]["Pid"]
            and detached["NetworkSettings"]["Networks"] == {} and set(lan.get("Containers", {})) == {resources["creator"]["id"]},
            "Actual native peer partition was not established")
    docker.receipt["native_partition"] = {"status": "OBSERVED_NETWORK_DETACH", "container_id": resources["recovered"]["id"],
                                          "host_pid": detached["State"]["Pid"], "network_ids": [], "network_id": network["Id"]}
    docker.checkpoint()
    for role in resources: offline_command(directories[role], role, docker.owner, "partition")
    for role, resource in resources.items():
        part = docker.wait_ready(resource, deadline, filename="partitioned.json")
        validate_offline_report(part, "partitioned", role, reports[role], [reports[role]["bridge_ipv4"]] if role == "creator" else [])
        require(part.get("network_detach_acknowledged") is (role == "recovered"), "Wrong native partition acknowledgment")
    deadline = min(overall, time.monotonic() + 240)
    for role in resources: offline_command(directories[role], role, docker.owner, "write")
    diverged = {}
    for role, resource in resources.items():
        diverged[role] = docker.wait_ready(resource, deadline, filename="diverged.json")
        validate_offline_report(diverged[role], "diverged", role, reports[role], [reports[role]["bridge_ipv4"]] if role == "creator" else [])
    expected = merge_offline_histories(diverged, state)
    # Recheck the real partition after both native write receipts exist.
    require(docker.find(resources["recovered"], deadline)["NetworkSettings"]["Networks"] == {}, "Native writes were not isolated")
    deadline = min(overall, time.monotonic() + 300)
    docker.command(["network", "connect", network["Id"], resources["recovered"]["id"]], "rejoin-owned-recovered", docker.remaining(deadline))
    infos = {role: docker.find(resource, deadline) for role, resource in resources.items()}
    lan = docker.find(network_resource, deadline)
    require(lan["Internal"] is True and set(lan.get("Containers", {})) == {r["id"] for r in resources.values()}, "Owned LAN reconnect failed")
    ips = {}
    for role, info in infos.items():
        require(info["State"].get("Running") is True and info["State"]["Pid"] == docker.receipt["native_peers"][role]["host_pid"]
                and set(info["NetworkSettings"]["Networks"]) == {network["Name"]}, "Reconnected native process is not the original process on the isolated LAN")
        endpoint = info["NetworkSettings"]["Networks"][network["Name"]]
        require(endpoint["NetworkID"] == network["Id"] and endpoint["IPAddress"], "Actual owned network attachment missing")
        ips[role] = [endpoint["IPAddress"]]
    require(infos["recovered"]["State"]["Pid"] == b["State"]["Pid"] and ips["creator"] != ips["recovered"], "Reconnect replaced a process or shared an interface")
    docker.receipt["native_reconnect"] = {"status": "OBSERVED_NATIVE_CLIENT_REATTACH", "network_id": network["Id"], "ipv4": ips}
    docker.checkpoint()
    for role in resources: offline_command(directories[role], role, docker.owner, "reconnect", expected)
    for role, resource in resources.items():
        report = docker.wait_ready(resource, deadline, filename="reconnected.json")
        validate_offline_report(report, "reconnected", role, reports[role], ips[role])
        require(report.get("actual_reconnect_acknowledged") is True, "Native reconnect acknowledgment missing")
    converged = {}
    for role, resource in resources.items():
        converged[role] = docker.wait_ready(resource, deadline, filename="converged.json")
        validate_offline_report(converged[role], "converged", role, reports[role], ips[role])
    semantic_hash = validate_convergence(converged, expected)
    return {"history": expected, "snapshot_sha256_without_local_sequence": semantic_hash,
            "converged": converged, "offline_writes": "TWO_DISTINCT_BRANCHES_OBSERVED", "network_state": "DETACH_AND_NATIVE_NOT_CONNECTED_THEN_ATTACH_AND_NATIVE_WIFI",
            "lost_client_reply": {"scope": "DROPPED_CLIENT_BYTE_REPLY_NOT_PACKET_LOSS_OR_CRASH",
                                  "clients": {role: value["lost_client_reply"] for role, value in diverged.items()}}}


def validate_reopen_ready(report: dict, role: str, original: dict, converged: dict, convergence_hash: str,
                          state_hash: str, identity: dict, info: dict) -> None:
    require(report.get("protocol") == OFFLINE_PROTOCOL and report.get("phase") == "reopened"
            and report.get("role") == role and report.get("nonce") == original["nonce"]
            and report.get("pid") == 1 and info["State"].get("Running") is True and info["State"].get("Pid", 0) > 0,
            "Actual new native reopen process missing")
    require(report.get("network_namespace") == os.readlink(f"/proc/{info['State']['Pid']}/ns/net")
            and report.get("actual_ipv4") == [] and report.get("native_network_mode") == "DISCONNECTED_REOPEN_NO_PEER_REPAIR",
            "Reopen may have received peer repair")
    require(report.get("peer_id") == original["peer_id"] and report.get("client_fixture_sha256") == original["client_fixture_sha256"]
            and report.get("state_sha256") == state_hash and report.get("convergence_receipt_sha256") == convergence_hash,
            "Original native device/source/expected state changed on reopen")
    for key in ["heart_sha", "runtime_version", "rpc_manifest_sha256", "registration_patch_sha256"]:
        require(report.get(key) == identity[key], "Reopened native source differs")
    require(report.get("history") == converged["history"]
            and report.get("snapshot_sha256_without_local_sequence") == converged["snapshot_sha256_without_local_sequence"],
            "Native disk reopen lost signed history or a conflict variant")
    require(type(report.get("local_applied_sequence")) is int and report["local_applied_sequence"] > 0
            and report.get("app_capability") == "OFF" and report.get("crash_after_commit") == "NOT_RUN"
            and report.get("two_ios_apps") == "NOT_RUN" and report.get("full_t2_acceptance") == "NOT_RUN"
            and not report.get("test_passed"), "Reopen readiness overstates acceptance")


def validate_reopen_final(ready: dict, final: dict, log: str) -> None:
    require(all(final.get(key) == value for key, value in ready.items()), "Reopen facts changed before native closure")
    require(final.get("closed") is True and final.get("account_stop_verified") is True and final.get("test_passed") is True
            and final.get("post_stop_rpc") == "READ_AND_APPEND_NOT_LOGGED_IN", "Reopened account was not closed and fenced")
    require(("--- PASS: " + REOPEN_METHOD + " ") in log and log.count("--- PASS:") == 1
            and "--- FAIL:" not in log and "--- SKIP:" not in log, "Exact reopened native named PASS required")
    expected = {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect", "WorkspaceOpen",
                                    "DeviceNetworkStateSet", "AccountStop", "AppShutdown", "PinkhaTorahOperationsAppend"]}
    expected["PinkhaTorahOperationsReadTarget"] = 2
    require(final.get("rpc_calls") == final.get("returned_byte_calls") == expected,
            "Reopen created, repaired, appended active data or missed its native shutdown boundary")


def offline_reopen(docker: OwnedDocker, resources: dict, directories: dict, binary: Path, fixture_sha: str,
                   original: dict, identity: dict, image_id: str, state_hash: str, key_hash: str, converged: dict) -> dict:
    deadline = time.monotonic() + 400
    original_ids = {resource["id"] for resource in resources.values()}
    for resource in resources.values():
        stopped = docker.find(resource, deadline)
        require(stopped and stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0,
                "Original native account still owns the database")
        docker.command(["container", "rm", resource["id"]], "retire-original-native-client", docker.remaining(deadline))
    restarted = {role: docker.start(role, None, directories[role], binary, fixture_sha, deadline, method=REOPEN_METHOD) for role in resources}
    require(not original_ids.intersection(resource["id"] for resource in restarted.values()), "Reopen reused the old native process")
    ready, infos = {}, {}
    for role, resource in restarted.items():
        ready[role] = docker.wait_ready(resource, deadline, filename="reopen-ready.json")
        infos[role] = docker.find(resource, deadline)
        validate_container(infos[role], docker.owner, role, None, directories[role], binary, image_id, os.getuid(), os.getgid(),
                           scenario="offline", method=REOPEN_METHOD)
        validate_reopen_ready(ready[role], role, original[role], converged[role], digest(directories[role] / "converged.json"),
                              state_hash, identity, infos[role])
    require(len({info["State"]["Pid"] for info in infos.values()}) == 2
            and len({report["network_namespace"] for report in ready.values()}) == 2, "Reopen processes do not have independent namespaces")
    for role in restarted: offline_command(directories[role], role, docker.owner, "reopen-stop")
    results = {}
    for role, resource in restarted.items():
        require(docker.command(["container", "wait", resource["id"]], "wait-native-reopen-" + role, docker.remaining(deadline, 90)) == "0",
                "Native disconnected reopen failed")
        final_info = docker.find(resource, deadline)
        require(final_info["State"].get("Running") is False and final_info["State"].get("ExitCode") == 0, "Reopen did not exit normally")
        log = directories[role] / "reopen-native.log"
        docker.command(["container", "logs", resource["id"]], "read-native-reopen-" + role, docker.remaining(deadline), log)
        final = json.loads((directories[role] / "reopened.json").read_text())
        validate_reopen_final(ready[role], final, log.read_text())
        require(digest(directories[role] / "state.json") == state_hash and digest(directories[role] / "account-key.private") == key_hash,
                "Original native recovery inputs changed on reopen")
        results[role] = {"container_id": resource["id"], "host_pid": infos[role]["State"]["Pid"], "network_namespace": ready[role]["network_namespace"],
                         "peer_id": ready[role]["peer_id"], "receipt_sha256": digest(directories[role] / "reopened.json"), "native_named_pass": 1}
    return {"status": "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK", "results": results}


# Inserted into the existing native-client controller; not a second dispatcher.
CRASH_COMMON_KEYS = {"protocol", "phase", "role", "nonce", "pid", "network_namespace", "actual_ipv4", "native_network_mode",
                     "peer_id", "heart_sha", "runtime_version", "client_fixture_sha256", "rpc_manifest_sha256",
                     "registration_patch_sha256", "state_sha256", "clean_reopen_receipt_sha256", "app_capability",
                     "power_loss", "two_ios_apps", "full_t2_acceptance"}
CRASH_ARM_KEYS = {"history_before", "history_committed", "baseline_snapshot_sha256", "request_sha256", "request_bytes",
                 "withheld_response_bytes", "claim_id", "committed_change_id", "first_reply_decoded", "client_append_returned",
                 "read_target_after_commit", "native_append_attempts", "rpc_calls", "returned_byte_calls",
                 "kill_deadline_unix_ns", "expected_termination", "test_passed"}
CRASH_RECOVER_KEYS = {"armed_receipt_sha256", "request_sha256", "retry_request_sha256", "request_bytes", "claim_id",
                     "committed_change_id", "history_before_read", "history_after_retry", "snapshot_before_retry_sha256",
                     "snapshot_after_retry_sha256", "local_sequence_before_retry", "local_sequence_after_retry",
                     "retry_disposition", "retry_change_id", "rpc_calls", "returned_byte_calls", "test_passed"}


def validate_crash_native_controls(text: str) -> dict:
    actual = re.findall(r"^\s*--- PASS: (\S+) \(", text, re.M)
    expected = set(CRASH_CONTROL_METHODS)
    expected.update(name + "/" + subcase for name, cases in CRASH_CONTROL_METHODS.items() for subcase in cases)
    require(set(actual) == expected and len(actual) == len(expected)
            and "--- FAIL:" not in text and "--- SKIP:" not in text, "Native crash controls incomplete")
    return {"top_level": 2, "subcases": 10, "pass_terminals": 12, "fail": 0, "skip": 0}


def crash_base_calls() -> dict:
    return {name: 1 for name in ["InitialSetParameters", "AppGetVersion", "WalletRecover", "AccountSelect",
                                "WorkspaceOpen", "DeviceNetworkStateSet"]}


def validate_crash_common(report: dict, phase: str, baseline: dict, baseline_hash: str, identity: dict) -> None:
    require(report.get("protocol") == CRASH_PROTOCOL and report.get("phase") == phase
            and report.get("role") == "creator" and report.get("nonce") == baseline["nonce"], "Foreign crash phase")
    require(type(report.get("pid")) is int and report["pid"] == 1
            and isinstance(report.get("network_namespace"), str) and report["network_namespace"]
            and report.get("actual_ipv4") == []
            and report.get("native_network_mode") == "DISCONNECTED_PROCESS_CRASH_NO_PEER_REPAIR", "Crash process isolation missing")
    require(report.get("peer_id") == baseline["peer_id"]
            and report.get("client_fixture_sha256") == baseline["client_fixture_sha256"]
            and report.get("state_sha256") == baseline["state_sha256"]
            and report.get("clean_reopen_receipt_sha256") == baseline_hash, "Crash phase changed its original store/device/source")
    for key in ["heart_sha", "runtime_version", "rpc_manifest_sha256", "registration_patch_sha256"]:
        require(report.get(key) == identity[key], "Crash native source mismatch")
    require(report.get("app_capability") == "OFF" and all(report.get(key) == "NOT_RUN"
            for key in ["power_loss", "two_ios_apps", "full_t2_acceptance"]), "Crash phase overclaims acceptance")


def validate_crash_arm(report: dict, baseline: dict, baseline_hash: str, identity: dict, now_ns: int) -> None:
    require(set(report) == CRASH_COMMON_KEYS | CRASH_ARM_KEYS, "Exact crash arm schema required")
    validate_crash_common(report, "armed_after_signed_commit_before_client_ack", baseline, baseline_hash, identity)
    require(report["test_passed"] is False and report["first_reply_decoded"] is False
            and report["client_append_returned"] is False and report["expected_termination"] == "OWNED_CONTAINER_SIGKILL",
            "Armed interrupted invocation cannot be a completed or acknowledged PASS")
    require(type(report["read_target_after_commit"]) is int and report["read_target_after_commit"] == 0
            and type(report["native_append_attempts"]) is int and report["native_append_attempts"] == 1,
            "Commit must precede any read or second mutation")
    require(type(report["kill_deadline_unix_ns"]) is int and 0 < report["kill_deadline_unix_ns"] - now_ns <= 31_000_000_000,
            "Crash arm is expired or outside its fixed kill window")
    require(re.fullmatch(r"[0-9a-f]{64}", report["request_sha256"])
            and type(report["request_bytes"]) is int and 0 < report["request_bytes"] <= 16384
            and type(report["withheld_response_bytes"]) is int and report["withheld_response_bytes"] > 0,
            "Actual encoded request and held reply observation missing")
    require(re.fullmatch(r"[0-9a-f]{64}/[0-9a-f]{64}", report["claim_id"]), "Native crash claim identity missing")
    before, after, new_id = report["history_before"], report["history_committed"], report["committed_change_id"]
    require(before == baseline["history"] and report["baseline_snapshot_sha256"] == baseline["snapshot_sha256_without_local_sequence"],
            "Crash phase did not start from the complete clean offline baseline")
    require(set(before) == set(after) == {"changes_sha256", "parents", "heads"}
            and len(before["changes_sha256"]) == 8 and len(before["parents"]) == 7 and len(set(before["heads"])) == 2,
            "Complete baseline signed history required")
    require(isinstance(new_id, str) and new_id and new_id not in before["changes_sha256"]
            and set(after["changes_sha256"]) == set(before["changes_sha256"]) | {new_id}
            and all(after["changes_sha256"][key] == value for key, value in before["changes_sha256"].items())
            and re.fullmatch(r"[0-9a-f]{64}", after["changes_sha256"][new_id]), "Exactly one unchanged-old/new signed commit required")
    require(after["parents"] == {**before["parents"], new_id: sorted(before["heads"])} and after["heads"] == [new_id],
            "Crash commit did not join both old heads")
    returned = {**crash_base_calls(), "PinkhaTorahOperationsReadTarget": 1}
    require(report["returned_byte_calls"] == returned
            and report["rpc_calls"] == {**returned, "PinkhaTorahOperationsAppend": 1},
            "Crash arm acknowledged its append, stopped the account or made extra native calls")


def crash_request_identity(path: Path) -> dict:
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o600
            and 0 < metadata.st_size <= 16384, "Retained original request must be private and bounded")
    return {"sha256": digest(path), "bytes": metadata.st_size}


def crash_store_identity(directory: Path) -> dict:
    root = directory / "account-root"
    metadata = root.lstat()
    require(stat.S_ISDIR(metadata.st_mode) and not root.is_symlink(), "Original crash account root missing")
    files = {}
    for path in root.rglob("*.db"):
        entry = path.lstat()
        require(stat.S_ISREG(entry.st_mode) and path.resolve().is_relative_to(root.resolve()), "Unsafe crash store entry")
        files[path.relative_to(root).as_posix()] = [entry.st_dev, entry.st_ino]
    require(files, "Actual original native databases required")
    return {"root_inode": [metadata.st_dev, metadata.st_ino], "databases": files}


def crash_live_identity(info: dict, report: dict) -> dict:
    state = info["State"]
    require(state.get("Running") is True and type(state.get("Pid")) is int and state["Pid"] > 0
            and info.get("RestartCount") == 0 and isinstance(state.get("StartedAt"), str) and state["StartedAt"],
            "Original crash process is not currently running")
    namespace = os.readlink(f"/proc/{state['Pid']}/ns/net")
    require(namespace == report["network_namespace"], "Crash native receipt belongs to another process namespace")
    return {"container_id": info["Id"], "host_pid": state["Pid"], "network_namespace": namespace,
            "started_at": state["StartedAt"]}


def kill_owned_crash_process(docker: OwnedDocker, resource: dict, live: dict, arm: dict, arm_hash: str,
                             baseline: dict, baseline_hash: str, identity: dict, directory: Path,
                             binary: Path, image_id: str, deadline: float) -> dict:
    info = docker.find(resource, deadline)  # Enforces exact owner label, name and immutable resource ID.
    require(info is not None, "Armed owned container disappeared before injection")
    validate_container(info, docker.owner, "creator", None, directory, binary, image_id, os.getuid(), os.getgid(),
                       scenario="offline", method=CRASH_COMMIT_METHOD)
    require(crash_live_identity(info, arm) == live and resource["id"] == live["container_id"],
            "Refuse to kill a replaced process or container")
    require(digest(directory / "crash-armed.json") == arm_hash, "Crash arm changed before injection")
    armed_monotonic, armed_wall_ns = time.monotonic(), time.time_ns()
    validate_crash_arm(arm, baseline, baseline_hash, identity, armed_wall_ns)
    # Fix a monotonic deadline once; later clock samples may shorten the arm's
    # remaining budget, never renew it or extend the existing phase deadline.
    kill_deadline = min(deadline, armed_monotonic + (arm["kill_deadline_unix_ns"] - armed_wall_ns) / 1_000_000_000)
    def kill_remaining(maximum):
        wall_remaining = (arm["kill_deadline_unix_ns"] - time.time_ns()) / 1_000_000_000
        require(wall_remaining > 0, "Crash termination was not observed inside its fixed arm window")
        return min(docker.remaining(kill_deadline, maximum), wall_remaining)
    # The only deliberate signal target is this revalidated immutable container
    # ID. No host PID, process name, wildcard or unrelated resource is signalled.
    docker.command(["container", "kill", "--signal", "KILL", resource["id"]], "inject-owned-crash", kill_remaining(10))
    require(docker.command(["container", "wait", resource["id"]], "wait-owned-crash", kill_remaining(15)) == "137",
            "Expected injected SIGKILL exit was not observed")
    kill_remaining(30)
    stopped = docker.find(resource, kill_deadline)
    termination_observed_ns = time.time_ns()
    require(termination_observed_ns < arm["kill_deadline_unix_ns"] and time.monotonic() < kill_deadline,
            "Crash termination was not observed inside its fixed arm window")
    require(stopped is not None, "Killed owned container disappeared before termination observation")
    state = stopped["State"]
    require(stopped["Id"] == live["container_id"] and state.get("Running") is False and state.get("ExitCode") == 137
            and state.get("OOMKilled") is False and state.get("StartedAt") == live["started_at"]
            and state.get("FinishedAt") and stopped.get("RestartCount") == 0, "Crash was not the intended owned process termination")
    log = directory / "crash-native.log"
    docker.command(["container", "logs", resource["id"]], "capture-owned-crash", docker.remaining(deadline), log)
    text = log.read_text()
    require(len(re.findall(r"^=== RUN[ \t]+" + re.escape(CRASH_COMMIT_METHOD) + r"[ \t]*$", text, re.M)) == 1
            and not re.search(r"--- (?:PASS|FAIL|SKIP):", text), "Interrupted native invocation cannot be counted as a terminal PASS")
    require(digest(directory / "crash-armed.json") == arm_hash, "Armed facts changed after process kill")
    return {"status": "OBSERVED_OWNED_CONTAINER_SIGKILL", **live, "exit_code": 137, "oom_killed": False,
            "intentional_kill_count": 1, "native_named_pass": 0, "normal_native_terminal_count": 0,
            "termination_observed_unix_ns": termination_observed_ns, "kill_deadline_unix_ns": arm["kill_deadline_unix_ns"],
            "armed_receipt_sha256": arm_hash, "log_sha256": digest(log)}


def validate_crash_recovery(report: dict, baseline: dict, baseline_hash: str, identity: dict, arm: dict, arm_hash: str,
                            *, finished: bool) -> None:
    extras = {"closed", "account_stop_verified", "post_stop_rpc"} if finished else set()
    require(set(report) == CRASH_COMMON_KEYS | CRASH_RECOVER_KEYS | extras, "Exact crash recovery schema required")
    validate_crash_common(report, "recovered_after_owned_sigkill" if finished else "recovered_state_before_native_stop",
                          baseline, baseline_hash, identity)
    require(report["armed_receipt_sha256"] == arm_hash
            and report["request_sha256"] == report["retry_request_sha256"] == arm["request_sha256"]
            and report["request_bytes"] == arm["request_bytes"]
            and report["claim_id"] == arm["claim_id"] and report["committed_change_id"] == arm["committed_change_id"],
            "Recovery changed the exact request, committed claim or signed change")
    require(report["history_before_read"] == report["history_after_retry"] == arm["history_committed"],
            "Recovery read/retry created, lost or replaced signed history")
    require(report["retry_disposition"] == "ALREADY_EXISTS_SAME_PAYLOAD" and report["retry_change_id"] == "",
            "Crash retry did not recover exactly the existing claim")
    require(re.fullmatch(r"[0-9a-f]{64}", report["snapshot_before_retry_sha256"])
            and report["snapshot_before_retry_sha256"] == report["snapshot_after_retry_sha256"]
            and type(report["local_sequence_before_retry"]) is int and report["local_sequence_before_retry"] > 0
            and report["local_sequence_before_retry"] == report["local_sequence_after_retry"],
            "Crash retry changed the complete snapshot or local sequence")
    calls = {**crash_base_calls(), "PinkhaTorahOperationsReadTarget": 3 if finished else 2,
             "PinkhaTorahOperationsAppend": 2 if finished else 1}
    if finished:
        calls.update(AccountStop=1, AppShutdown=1)
        require(report["closed"] is True and report["account_stop_verified"] is True
                and report["post_stop_rpc"] == "READ_AND_APPEND_NOT_LOGGED_IN", "Recovered account did not close and revoke authority")
    require(report["test_passed"] is finished and report["rpc_calls"] == report["returned_byte_calls"] == calls,
            "Crash recovery recreated data, lost a byte return or miscounted its native boundary")


def crash_sequence(docker: OwnedDocker, directory: Path, binary: Path, fixture_sha: str, identity: dict,
                   image_id: str, state_hash: str, key_hash: str, reopen: dict) -> dict:
    require(docker.crash_after_commit and docker.scenario == "offline", "Crash tail was not explicitly selected")
    overall = time.monotonic() + 600
    progress = {"status": "NOT_RUN_CRASH_PREFLIGHT", "scope": "OWNED_NATIVE_PROCESS_SIGKILL_NOT_POWER_LOSS",
                "killed_invocation_is_native_pass": False, "power_loss": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
    docker.receipt["crash_after_commit"] = progress
    baseline_path = directory / "reopened.json"
    baseline_hash, baseline = digest(baseline_path), json.loads(baseline_path.read_text())
    require(reopen["status"] == "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK"
            and baseline_hash == reopen["results"]["creator"]["receipt_sha256"]
            and baseline["test_passed"] is True and baseline["closed"] is True
            and baseline["state_sha256"] == state_hash, "Complete clean baseline must precede crash injection")
    previous = [r for r in docker.resources if r.get("id") == reopen["results"]["creator"]["container_id"]]
    require(len(previous) == 1, "Original completed creator process missing")
    stopped = docker.find(previous[0], overall)
    require(stopped and stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0,
            "Another process still owns the original crash database")
    docker.command(["container", "rm", previous[0]["id"]], "retire-clean-creator-reopen", docker.remaining(overall))
    for name in ["crash-request.private", "crash-armed.json", "crash-recover-ready.json", "crash-recovered.json",
                 "crash-recover-stop.command.json", "crash-native.log", "crash-recover-native.log"]:
        require(not (directory / name).exists(), "Fresh independent crash phase required")
    original_store = crash_store_identity(directory)
    docker.receipt["diagnostic_stage"] = "CRASH_ARM"
    docker.checkpoint()
    deadline = min(overall, time.monotonic() + 300)
    commit = docker.start("creator", None, directory, binary, fixture_sha, deadline, method=CRASH_COMMIT_METHOD)
    arm = docker.wait_ready(commit, deadline, filename="crash-armed.json")
    info = docker.find(commit, deadline)
    validate_container(info, docker.owner, "creator", None, directory, binary, image_id, os.getuid(), os.getgid(),
                       scenario="offline", method=CRASH_COMMIT_METHOD)
    validate_crash_arm(arm, baseline, baseline_hash, identity, time.time_ns())
    live = crash_live_identity(info, arm)
    require(live["host_pid"] not in {v["host_pid"] for v in reopen["results"].values()}, "Crash phase reused an old native process")
    request = crash_request_identity(directory / "crash-request.private")
    require(request == {"sha256": arm["request_sha256"], "bytes": arm["request_bytes"]}
            and crash_store_identity(directory) == original_store, "Crash request or original native store identity changed")
    arm_hash = digest(directory / "crash-armed.json")
    progress.update(status="ARMED_NATIVE_SIGNED_COMMIT_BEFORE_CLIENT_ACK", armed_receipt_sha256=arm_hash,
                    request=request, committed_signed_entries=9, client_acknowledged=False)
    docker.receipt["diagnostic_stage"] = "CRASH_KILL"
    docker.checkpoint()
    killed = kill_owned_crash_process(docker, commit, live, arm, arm_hash, baseline, baseline_hash, identity,
                                      directory, binary, image_id, deadline)
    require(crash_store_identity(directory) == original_store and crash_request_identity(directory / "crash-request.private") == request,
            "Original native store/request changed at the kill boundary")
    progress.update(status="EXPECTED_PROCESS_KILL_OBSERVED_RECOVERY_NOT_RUN", injected_termination=killed)
    docker.checkpoint()
    docker.command(["container", "rm", commit["id"]], "retire-injected-crash-container", docker.remaining(overall))
    docker.receipt["diagnostic_stage"] = "CRASH_RECOVER"
    docker.checkpoint()
    deadline = min(overall, time.monotonic() + 300)
    recovery = docker.start("creator", None, directory, binary, fixture_sha, deadline, method=CRASH_RECOVER_METHOD)
    ready = docker.wait_ready(recovery, deadline, filename="crash-recover-ready.json")
    info = docker.find(recovery, deadline)
    validate_container(info, docker.owner, "creator", None, directory, binary, image_id, os.getuid(), os.getgid(),
                       scenario="offline", method=CRASH_RECOVER_METHOD)
    validate_crash_recovery(ready, baseline, baseline_hash, identity, arm, arm_hash, finished=False)
    recovered_live = crash_live_identity(info, ready)
    require(recovery["id"] != commit["id"] and recovered_live["host_pid"] != live["host_pid"], "Recovery reused the killed process")
    require(crash_store_identity(directory) == original_store and digest(directory / "state.json") == state_hash
            and digest(directory / "account-key.private") == key_hash
            and crash_request_identity(directory / "crash-request.private") == request, "Recovery repaired or replaced original input/storage")
    write(directory / "crash-recover-stop.command.json", {"protocol": OFFLINE_PROTOCOL, "nonce": docker.owner,
          "role": "creator", "phase": "crash-recover-stop", "expected_history": {"changes_sha256": {}, "parents": {}, "heads": []}})
    require(docker.command(["container", "wait", recovery["id"]], "wait-crash-recovery", docker.remaining(deadline, 90)) == "0",
            "Actual crash recovery did not finish normally")
    stopped = docker.find(recovery, deadline)
    require(stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0
            and stopped["State"].get("OOMKilled") is False, "Recovery process did not exit normally")
    log = directory / "crash-recover-native.log"
    docker.command(["container", "logs", recovery["id"]], "capture-crash-recovery", docker.remaining(deadline), log)
    final = json.loads((directory / "crash-recovered.json").read_text())
    validate_crash_recovery(final, baseline, baseline_hash, identity, arm, arm_hash, finished=True)
    require(all(final.get(key) == value for key, value in ready.items()
                if key not in {"phase", "rpc_calls", "returned_byte_calls", "test_passed"}), "Recovery facts changed during native Stop")
    text = log.read_text()
    require(("--- PASS: " + CRASH_RECOVER_METHOD + " ") in text and text.count("--- PASS:") == 1
            and "--- FAIL:" not in text and "--- SKIP:" not in text, "Recovery requires exactly one actual Native PASS")
    require(crash_store_identity(directory) == original_store and digest(baseline_path) == baseline_hash
            and digest(directory / "crash-armed.json") == arm_hash
            and digest(directory / "state.json") == state_hash and digest(directory / "account-key.private") == key_hash
            and crash_request_identity(directory / "crash-request.private") == request, "Final crash evidence or original inputs changed")
    progress.update(status="PASS_NATIVE_OWNED_PROCESS_CRASH_EXACT_RETRY", recovery={**recovered_live,
        "receipt_sha256": digest(directory / "crash-recovered.json"), "log_sha256": digest(log), "native_named_pass": 1},
        actual_counts={"native_processes": 2, "native_named_pass": 1, "intentional_sigkill": 1, "unexpected_native_failure": 0, "native_skip": 0},
        original_store_identity=original_store, retry_disposition="ALREADY_EXISTS_SAME_PAYLOAD", new_change_id_on_retry=False,
        signed_history_entries_before_read=9, signed_history_and_complete_snapshot_unchanged=True,
        native_shutdown_and_post_stop_denial="PASS", app_capability="OFF")
    docker.checkpoint()
    return progress


def clients(args, receipt, docker: OwnedDocker):
    receipt["diagnostic_stage"] = "VERIFY_BUILD"
    manifest, _ = source_inputs(args.control)
    build_path = args.evidence / "native-clients-build.json"
    built = json.loads(build_path.read_text())
    require(built.get("status") == "PASS_NATIVE_BUILD_AND_BASELINE_ONLY" and built.get("app_sha") == args.expected_app_sha
            and built.get("run_id") == receipt["run_id"] and built.get("run_attempt") == receipt["run_attempt"]
            and built.get("scenario") == args.scenario and built.get("crash_after_commit_requested", False) == args.crash_after_commit
            and built.get("observed_remove_after_reopen_requested", False) == args.observed_remove_after_reopen
            and built.get("concurrent_replace_after_reopen_requested", False) == args.concurrent_replace_after_reopen
            and built.get("fixture_sha256") == manifest["fixture_sha256"], "Foreign or unsuccessful native build receipt")
    require(built["runtime"]["relative_path"] == "client-runtime/native.test", "Unexpected native runtime path")
    binary = args.native_work / built["runtime"]["relative_path"]
    require(binary.is_file() and not binary.is_symlink() and digest(binary) == built["runtime"]["sha256"]
            == built["baseline"]["identities"]["new"]["binary_sha256"], "Native runtime bytes differ")
    receipt.update(build_receipt_sha256=digest(build_path), fixture_sha256=manifest["fixture_sha256"],
                   binary_sha256=digest(binary), native_image=IMAGE)
    docker.checkpoint()
    image = json.loads(docker.command(["image", "inspect", IMAGE], "inspect-pinned-image"))[0]
    require(image.get("Os") == "linux" and image.get("Architecture") == "amd64", "Wrong runtime image platform")
    receipt["diagnostic_stage"] = "CREATE_NETWORK"
    network_resource, network = docker.network()
    directories = {}
    for role in ["creator", "recovered"]:
        directory = docker.private / role
        directory.mkdir(mode=0o700)
        (directory / "account-root").mkdir(mode=0o700)
        write(directory / "ownership.json", {"protocol": PROTOCOL, "nonce": docker.owner, "role": role, "synthetic_only": True})
        directories[role] = directory
    creator_deadline = time.monotonic() + 360
    receipt["diagnostic_stage"] = "START_CREATOR"
    creator = docker.start("creator", network, directories["creator"], binary, manifest["fixture_sha256"], creator_deadline)
    receipt["diagnostic_stage"] = "WAIT_CREATOR"
    reports = {"creator": docker.wait_ready(creator, creator_deadline)}
    recovered_deadline = time.monotonic() + 540
    receipt["diagnostic_stage"] = "SEED_RECOVERED"
    state_bytes = (directories["creator"] / "state.json").read_bytes()
    state = json.loads(state_bytes)
    validate_public_state(state)
    state_hash = hashlib.sha256(state_bytes).hexdigest()
    key_path = directories["creator"] / "account-key.private"
    require(key_path.is_file() and not key_path.is_symlink() and key_path.stat().st_mode & 0o077 == 0,
            "Synthetic account recovery key must remain private")
    key_hash = digest(key_path)
    require(key_path.stat().st_size > 0 and not any((directories["recovered"] / "account-root").iterdir()),
            "Recovering client root is not empty")
    # This is the complete and fixed seed allowlist. No directory copy occurs.
    for name, data in [("state.json", state_bytes), ("account-key.private", key_path.read_bytes())]:
        path = directories["recovered"] / name
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o600)
    receipt["diagnostic_stage"] = "START_RECOVERED"
    recovered = docker.start("recovered", network, directories["recovered"], binary, manifest["fixture_sha256"], recovered_deadline)
    receipt["diagnostic_stage"] = "WAIT_RECOVERED"
    reports["recovered"] = docker.wait_ready(recovered, recovered_deadline)
    receipt["diagnostic_stage"] = "VERIFY_PAIR"
    resources = {"creator": creator, "recovered": recovered}
    inspections = {role: docker.find(resource, recovered_deadline) for role, resource in resources.items()}
    current_network = docker.find(network_resource, recovered_deadline)
    require(set(current_network.get("Containers", {})) == {r["id"] for r in resources.values()}, "Unexpected peer in the owned LAN")
    identity = built["baseline"]["identities"]["new"]
    for role in resources:
        validate_container(inspections[role], docker.owner, role, network, directories[role], binary, image["Id"], os.getuid(), os.getgid(),
                           scenario=args.scenario)
        validate_ready(reports[role], role, docker.owner, state, state_hash, identity, manifest["fixture_sha256"], inspections[role], network)
    validate_pair(reports, inspections)
    receipt.update(state_sha256=state_hash, seed_files=["account-key.private", "state.json"],
                   native_peers={role: {"container_id": resources[role]["id"], "host_pid": info["State"]["Pid"],
                     "network_sandbox_id": info["NetworkSettings"]["SandboxID"], "native_peer_id": reports[role]["peer_id"],
                     "namespace": reports[role]["network_namespace"]} for role, info in inspections.items()},
                   original_signed_history_matches=True, independent_empty_roots=True)
    docker.checkpoint()
    docker.remaining(recovered_deadline)
    offline = None
    if args.scenario == "offline":
        receipt["diagnostic_stage"] = "OFFLINE_SEQUENCE"
        offline = offline_sequence(docker, resources, network_resource, network, reports, directories, state)
        receipt["offline_convergence"] = {"history": offline["history"], "snapshot_sha256_without_local_sequence": offline["snapshot_sha256_without_local_sequence"],
                                           "offline_writes": offline["offline_writes"], "network_state": offline["network_state"], "restart": "NOT_RUN",
                                           "lost_client_reply": offline["lost_client_reply"]}
        docker.checkpoint()
    receipt["diagnostic_stage"] = "REQUEST_NATIVE_STOP"
    for role in resources:
        write(directories[role] / "stop.json", {"protocol": PROTOCOL, "nonce": docker.owner})
    shutdown_deadline = time.monotonic() + 90
    final_reports = {}
    db_inodes = {}
    for role, resource in resources.items():
        receipt["diagnostic_stage"] = "WAIT_NATIVE_STOP"
        require(docker.command(["container", "wait", resource["id"]], "wait-native-" + role,
                               docker.remaining(shutdown_deadline, 90)) == "0", "Native process failed")
        receipt["diagnostic_stage"] = "VERIFY_FINAL"
        stopped = docker.find(resource, shutdown_deadline)
        require(stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0,
                "Native process did not complete cleanly")
        log = directories[role] / "native.log"
        docker.command(["container", "logs", resource["id"]], "read-native-" + role, docker.remaining(shutdown_deadline), log)
        final = json.loads((directories[role] / "final.json").read_text())
        validate_final(reports[role], final, log.read_text(), role, scenario=args.scenario)
        if offline is not None:
            phase = final.get("offline_scenario", {})
            require(all(offline["converged"][role].get(key) == value for key, value in phase.items())
                    and set(phase) == {"history", "snapshot_sha256_without_local_sequence", "local_applied_sequence", "live_count",
                                      "conflict_count", "conflict_variants", "retry_and_collision", "concurrent_remove_add_remove",
                                      "restart", "crash_after_commit", "full_t2_acceptance"}, "Final native process lost its original offline proof")
        require(digest(directories[role] / "state.json") == state_hash
                and digest(directories[role] / "account-key.private") == key_hash, "Recovery input changed")
        db_files = list((directories[role] / "account-root").rglob("*.db"))
        require(db_files and all(path.is_file() and not path.is_symlink() for path in db_files), "Real independent native databases missing")
        db_inodes[role] = {(path.stat().st_dev, path.stat().st_ino) for path in db_files}
        final_reports[role] = {"sha256": digest(directories[role] / "final.json"), "native_named_pass": 1,
                               "actual_database_files": len(db_files), "account_stop_verified": True}
    require(not db_inodes["creator"].intersection(db_inodes["recovered"]), "Native clients share a database inode")
    if offline is not None:
        receipt["diagnostic_stage"] = "OFFLINE_REOPEN"
        reopen = offline_reopen(docker, resources, directories, binary, manifest["fixture_sha256"], reports, identity,
                                image["Id"], state_hash, key_hash, offline["converged"])
        require(source_inputs(args.control)[0] == manifest, "Native client source changed during disconnected reopen")
        if args.crash_after_commit or args.observed_remove_after_reopen or args.concurrent_replace_after_reopen:
            receipt["completed_offline_baseline"] = {"native_results": final_reports, "disconnected_reopen": reopen,
                "actual_counts": {"independent_native_clients": 2, "native_processes": 4, "native_named_pass": 4, "native_fail": 0, "native_skip": 0}}
            receipt["actual_counts_scope"] = "UNCHANGED_TWO_NATIVE_CLIENTS_OFFLINE_BASELINE"
            docker.checkpoint()
        if args.crash_after_commit:
            require(built.get("crash_native_controls") == {"top_level": 2, "subcases": 10, "pass_terminals": 12, "fail": 0, "skip": 0},
                    "Exact new crash Native controls must precede injection")
            receipt["crash_after_commit"] = crash_sequence(docker, directories["creator"], binary, manifest["fixture_sha256"],
                                                          identity, image["Id"], state_hash, key_hash, reopen)
            require(receipt["crash_after_commit"].get("status") == "PASS_NATIVE_OWNED_PROCESS_CRASH_EXACT_RETRY",
                    "Optional crash tail did not complete")
        if args.observed_remove_after_reopen:
            receipt["diagnostic_stage"] = "OBSERVED_REMOVE_AFTER_REOPEN"
            receipt["observed_remove_after_reopen"] = {"status": "IN_PROGRESS", "phase": "START", "completed_native_named_pass": 0}
            docker.checkpoint()
            receipt["observed_remove_after_reopen"] = observed_remove.sequence(sys.modules[__name__], docker, directories, binary,
                manifest["fixture_sha256"], identity, image["Id"], state, state_hash, key_hash, reopen, network_resource, network)
            require(receipt["observed_remove_after_reopen"].get("status") == observed_remove.PASS, "Optional causal tail did not complete")
            require(source_inputs(args.control)[0] == manifest, "Native causal source changed during execution")
        if args.concurrent_replace_after_reopen:
            receipt["diagnostic_stage"] = "CONCURRENT_REPLACE_AFTER_REOPEN"
            receipt["concurrent_replace_after_reopen"] = {"status": "IN_PROGRESS", "phase": "START", "completed_native_named_pass": 0}
            docker.checkpoint()
            receipt["concurrent_replace_after_reopen"] = concurrent_replace.sequence(sys.modules[__name__], docker, directories, binary,
                manifest["fixture_sha256"], identity, image["Id"], state, state_hash, key_hash, reopen, network_resource, network)
            require(receipt["concurrent_replace_after_reopen"].get("status") == concurrent_replace.PASS,
                    "Optional concurrent-replace tail did not complete")
            require(source_inputs(args.control)[0] == manifest, "Native concurrent-replace source changed during execution")
        receipt["diagnostic_stage"] = "COMPLETE"
        return {"native_results": final_reports, "disconnected_reopen": reopen,
                "actual_counts": {"independent_native_clients": 2, "native_processes": 4, "native_named_pass": 4, "native_fail": 0, "native_skip": 0},
                "distinct_database_inodes": True, "offline_conflict_merge": "PASS_NATIVE_TWO_CLIENTS_NO_WINNER_OR_LOST_ADD",
                "restart": "PASS_TWO_ORIGINAL_STORES_REOPENED_WITHOUT_NETWORK",
                "transport_scope": "NATIVE_LAN_PARTITION_RECONNECT_CONFLICT_CONVERGENCE_THEN_DISCONNECTED_DISK_REOPEN"}
    require(source_inputs(args.control)[0] == manifest, "Native client source changed during execution")
    receipt["diagnostic_stage"] = "COMPLETE"
    return {"native_results": final_reports, "actual_counts": {"independent_native_clients": 2, "native_named_pass": 2,
            "native_fail": 0, "native_skip": 0}, "distinct_database_inodes": True,
            "transport_scope": "NATIVE_LOCAL_DISCOVERY_AND_AUTHENTICATED_PEER_TRANSPORT_ON_OWNED_INTERNAL_LAN"}


def normalize_evidence_entry(item: Path) -> None:
    metadata = item.lstat()
    require(stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode), "Unsafe evidence publication entry")
    wanted = 0o755 if stat.S_ISDIR(metadata.st_mode) else 0o644
    if stat.S_IMODE(metadata.st_mode) == wanted:
        # Build-stage files can belong to the container user. Even a no-op
        # chmod by a different host user may fail; verified mode is enough.
        return
    require(metadata.st_uid == os.geteuid(), "Foreign-owned evidence has an unsafe publication mode")
    item.chmod(wanted)


def normalize_evidence_permissions(evidence: Path) -> None:
    for item in evidence.rglob("*"):
        normalize_evidence_entry(item)


def finish_evidence(receipt: dict, evidence: Path, receipt_path: Path, checkpoint, *, emit_notice: bool) -> bool:
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    succeeded = True

    def attempt(error_key, operation):
        nonlocal succeeded
        try:
            operation()
        except Exception as error:
            succeeded = False
            receipt[error_key] = type(error).__name__
            if receipt.get("status") != "CANCELLED":
                receipt["status"] = "FAIL"

    # Atomic checkpoints create a new 0600 inode under the controller's
    # umask(077). Normalize after writing, never before the final replacement.
    attempt("receipt_write_error_type", checkpoint)
    attempt("evidence_permissions_error_type", lambda: normalize_evidence_permissions(evidence))
    if not succeeded:
        # Persist failure metadata once. This second replacement also needs its
        # own mode check; failure of either operation cannot restore success.
        attempt("receipt_write_error_type", checkpoint)
        attempt("evidence_permissions_error_type", lambda: normalize_evidence_entry(receipt_path))
    if emit_notice:
        diagnostics.emit_current_run_notice(receipt, evidence)
    return succeeded


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("stage", choices=["build", "clients"])
    parser.add_argument("--scenario", choices=["bootstrap", "offline"], default="bootstrap")
    tails = parser.add_mutually_exclusive_group()
    tails.add_argument("--crash-after-commit", action="store_true")
    tails.add_argument("--observed-remove-after-reopen", action="store_true")
    tails.add_argument("--concurrent-replace-after-reopen", action="store_true")
    parser.add_argument("--control", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "native-work"]:
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    concurrent_replace.validate_selection(args.scenario, args.crash_after_commit, args.observed_remove_after_reopen, args.concurrent_replace_after_reopen)
    for name in ["control", "evidence", "approved_source", "heart_legacy", "heart_new", "work", "native_work"]:
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    require(sys.platform == "linux" and os.name == "posix", "Native clients require Linux CI")
    require(args.control == Path(__file__).resolve().parents[2], "Controller must execute from its exact source checkout")
    require(args.control != args.evidence and args.control not in args.evidence.parents and args.evidence not in args.control.parents,
            "Evidence must be separate from source")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha) and base.git(args.control, "rev-parse", "HEAD") == args.expected_app_sha
            and not base.git(args.control, "status", "--porcelain"), "Exact clean source required")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(run_id.isdigit() and int(run_id) > 0 and attempt.isdigit() and int(attempt) > 0, "Actual workflow identity required")
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / ("native-clients-" + args.stage + ".json")
    require(not path.exists(), "Fresh native client receipt required")
    receipt = {"protocol": PROTOCOL, "status": "NOT_RUN_PREFLIGHT", "stage": args.stage, "diagnostic_stage": "PREFLIGHT", "scenario": args.scenario,
               "crash_after_commit_requested": args.crash_after_commit, "app_sha": args.expected_app_sha,
               "observed_remove_after_reopen_requested": args.observed_remove_after_reopen,
               "concurrent_replace_after_reopen_requested": args.concurrent_replace_after_reopen,
               "run_id": run_id, "run_attempt": attempt, "started_at": datetime.now(timezone.utc).isoformat(), "commands": [],
               "two_native_clients": "NOT_RUN", "app_capability": "OFF", "two_app_clients": "NOT_RUN",
               "offline_conflict_merge": "NOT_RUN", "ios_acceptance": "NOT_RUN", "full_t2_acceptance": "NOT_RUN"}
    checkpoint = lambda: write(path, receipt)
    checkpoint()
    old_handlers = {n: signal.getsignal(n) for n in [signal.SIGTERM, signal.SIGINT]}
    cancelled = False
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in old_handlers:
        signal.signal(number, cancel)
    docker, candidate, result = None, False, 1
    def run(command, name, cwd, env, timeout=900):
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}
        receipt["commands"].append(entry)
        checkpoint()
        try:
            entry["pid"] = base.run_process(entry["argv"], cwd, env, args.evidence / (name + ".log"), timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry["status"] = "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL"
            raise
        finally:
            checkpoint()
    try:
        if args.stage == "build":
            require(all(getattr(args, key) is not None for key in ["approved_source", "heart_legacy", "heart_new", "work"]), "Build paths required")
            receipt.update(build(args, receipt, run))
        else:
            require(args.native_work is not None and args.native_work.is_dir(), "Owned native work root required")
            roots = [args.control, args.evidence, args.native_work]
            require(len(set(roots)) == len(roots) and not any(a in b.parents for a in roots for b in roots if a != b),
                    "Native source, work and evidence roots must be distinct siblings")
            private = args.native_work / "two-client-bootstrap"
            require(not private.exists() and args.control not in private.parents and args.evidence not in private.parents,
                    "Fresh separate native client work required")
            require(shutil.disk_usage(args.native_work).free >= base.RESERVE, "Native disk reserve below 8 GiB")
            private.mkdir(mode=0o700)
            docker = OwnedDocker(private, receipt, checkpoint, scenario=args.scenario, crash_after_commit=args.crash_after_commit,
                                 observed_remove_after_reopen=args.observed_remove_after_reopen,
                                 concurrent_replace_after_reopen=args.concurrent_replace_after_reopen)
            receipt.update(clients(args, receipt, docker))
        candidate = True
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__)
    finally:
        if docker is not None:
            try:
                try:
                    docker.cleanup()
                except KeyboardInterrupt:
                    candidate = False
                    receipt.update(status="CANCELLED", error_type="KeyboardInterrupt")
                    docker.cleanup()
                receipt["native_publication"] = publish_native_evidence(docker.private, args.evidence, scenario=args.scenario,
                    crash_after_commit=args.crash_after_commit, observed_remove_after_reopen=args.observed_remove_after_reopen,
                    concurrent_replace_after_reopen=args.concurrent_replace_after_reopen)
                if candidate:
                    require(receipt["native_publication"]["status"] == "PASS_SECRET_SCANNED_EXACT_ALLOWLIST", "Native evidence withheld")
            except BaseException as error:
                candidate = False
                receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) or cancelled else "FAIL",
                               cleanup_or_publication_error_type=type(error).__name__)
        if candidate and not cancelled:
            if args.stage == "clients":
                receipt.update(status="PASS_TWO_NATIVE_CLIENTS_OFFLINE_CONFLICT_REOPEN" if args.scenario == "offline"
                               else "PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", two_native_clients="PASS_LAN_COLD_BOOTSTRAP")
            result = 0
        def finish():
            nonlocal result
            if not finish_evidence(receipt, args.evidence, path, checkpoint, emit_notice=args.stage == "clients"):
                result = 1
        try:
            try:
                finish()
            except KeyboardInterrupt:
                result = 1
                receipt.update(status="CANCELLED", error_type="KeyboardInterrupt")
                finish()
        finally:
            for number, handler in old_handlers.items():
                signal.signal(number, handler)
    print(json.dumps({key: receipt.get(key) for key in ["status", "app_sha", "run_id", "error_type", "two_native_clients"]}), flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
