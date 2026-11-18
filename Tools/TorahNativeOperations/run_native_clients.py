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
import subprocess
import sys
import time
from uuid import uuid4

import run_account_lifecycle as base
import run_account_rpc as account

PROTOCOL = "pinkha-t2-two-native-clients-bootstrap-v1"
METHOD = "TestT2NativeClientBootstrapPhase"
IMAGE = "golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8"
OWNER_LABEL = "pinkha.t2.native-clients.owner"
GO_FILES = {"native_client_phase_test.go", "native_client_boundary_test.go"}
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
            "runtime": {"relative_path": "client-runtime/native.test", "sha256": digest(target), "uploaded": False},
            "fixture_sha256": manifest["fixture_sha256"], "two_native_clients": "NOT_RUN"}


def validate_container(info: dict, owner: str, role: str, network: dict, private: Path, binary: Path,
                       image_id: str, uid: int, gid: int) -> None:
    require(info.get("Config", {}).get("Labels", {}).get(OWNER_LABEL) == owner, "Foreign container ownership")
    require(info["Config"].get("Image") == IMAGE and info.get("Image") == image_id, "Different runtime image")
    require(info["Config"].get("User") == f"{uid}:{gid}" and info.get("Path") == "/fixture/native.test",
            "Container must directly run the native ELF as the owner")
    require(info.get("Args") == ["-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=1000s"],
            "Unexpected native executable arguments")
    host = info["HostConfig"]
    require(host.get("ReadonlyRootfs") is True and host.get("Privileged") is False
            and host.get("CapDrop") == ["ALL"] and "no-new-privileges" in host.get("SecurityOpt", [])
            and host.get("NetworkMode") == network["Name"] and not host.get("PortBindings")
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
    require(set(networks) == {network["Name"]} and networks[network["Name"]]["NetworkID"] == network["Id"],
            "Native client is not isolated to its owned internal LAN")
    env = dict(value.split("=", 1) for value in info["Config"]["Env"] if "=" in value)
    require(env.get("PINKHA_T2_CLIENT_ROLE") == role and env.get("PINKHA_T2_CLIENT_NONCE") == owner,
            "Native container role/nonce differs")


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


def validate_final(ready: dict, final: dict, log: str, role: str) -> None:
    require(all(final.get(key) == value for key, value in ready.items()), "Readiness facts changed before AccountStop")
    require(final.get("closed") is True and final.get("account_stop_verified") is True and final.get("test_passed") is True
            and final.get("post_stop_rpc") == "READ_AND_APPEND_NOT_LOGGED_IN", "Actual native shutdown/denial proof missing")
    require(("--- PASS: " + METHOD + " ") in log and log.count("--- PASS:") == 1
            and "--- FAIL:" not in log and "--- SKIP:" not in log, "Exact native named PASS required")
    calls = final.get("rpc_calls", {})
    require(calls == final.get("returned_byte_calls"), "Native byte call did not return")
    common = {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1, "DeviceNetworkStateSet": 1,
              "ObjectShow": 1, "AccountStop": 1, "AppShutdown": 1,
              "PinkhaTorahOperationsAppend": 2 if role == "creator" else 1}
    require(all(calls.get(key) == count for key, count in common.items())
            and calls.get("PinkhaTorahOperationsReadTarget", 0) >= 2, "Native call boundary incomplete")
    creator = {"WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"}
    recovery = {"WalletRecover", "AccountSelect"}
    require(all(calls.get(key, 0) == (1 if role == "creator" else 0) for key in creator)
            and all(calls.get(key, 0) == (1 if role == "recovered" else 0) for key in recovery)
            and calls.get("AccountMigrate", 0) == 0, "Cold recovery recreated or seeded native data")
    require(calls.get("ObjectSearch", 0) >= 1 if role == "creator" else calls.get("ObjectSearch", 0) == 0,
            "Unexpected native Page-readiness calls")
    require(set(calls) <= set(common) | creator | recovery | {"ObjectSearch", "PinkhaTorahOperationsReadTarget"},
            "Unexpected native operation outside LAN bootstrap")


def publish_native_evidence(private: Path, evidence: Path) -> dict:
    needle_path = private / "creator/sensitive-needles.private"
    if not needle_path.is_file() or needle_path.is_symlink():
        return {"status": "WITHHELD_NO_SECRET_INVENTORY", "files_sha256": {}}
    needles = json.loads(needle_path.read_text())
    require(isinstance(needles, list) and len(needles) == 2 and len(set(needles)) == 2
            and all(isinstance(n, str) and len(n) >= 10 for n in needles), "Incomplete synthetic secret inventory")
    candidates = []
    for role in ["creator", "recovered"]:
        for name in ["ownership.json", "state.json", "ready.json", "final.json", "cancel.json", "native.log"]:
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
    def __init__(self, private: Path, receipt: dict, checkpoint):
        self.private, self.receipt, self.checkpoint = private, receipt, checkpoint
        self.owner = uuid4().hex
        self.prefix = "pinkha-t2-" + self.owner[:16]
        self.resources = []
        self.receipt["owned_resources"] = self.resources
        self.receipt["owner_nonce"] = self.owner
        self.command_index = 0

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

    def start(self, role, network, directory, binary, fixture_sha, deadline):
        resource = {"kind": "container", "name": self.prefix + "-" + role, "id": None, "role": role,
                    "private": str(directory)}
        self.resources.append(resource)
        args = ["container", "create", "--name", resource["name"], "--label", OWNER_LABEL + "=" + self.owner,
                "--platform", "linux/amd64", "--network", network["Name"], "--read-only", "--init=false",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
                "--cpus", "1", "--memory", "2g", "--pids-limit", "256", "--workdir", "/private",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777",
                "--mount", f"type=bind,src={directory},dst=/private",
                "--mount", f"type=bind,src={binary},dst=/fixture/native.test,readonly",
                "-e", "PINKHA_T2_CLIENT_ROLE=" + role, "-e", "PINKHA_T2_CLIENT_NONCE=" + self.owner,
                "-e", "PINKHA_T2_CLIENT_FIXTURE_SHA=" + fixture_sha, "-e", "GOMAXPROCS=2", "-e", "GOMEMLIMIT=768MiB",
                IMAGE, "/fixture/native.test", "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=1000s"]
        resource["id"] = self.command(args, "create-" + role, self.remaining(deadline))
        require(re.fullmatch(r"[0-9a-f]{64}", resource["id"]), "Missing actual native container identity")
        self.command(["container", "start", resource["id"]], "start-" + role, self.remaining(deadline))
        return resource

    def wait_ready(self, resource, deadline):
        path = Path(resource["private"]) / "ready.json"
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
                        log = Path(resource["private"]) / "native.log"
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


def clients(args, receipt, docker: OwnedDocker):
    manifest, _ = source_inputs(args.control)
    build_path = args.evidence / "native-clients-build.json"
    built = json.loads(build_path.read_text())
    require(built.get("status") == "PASS_NATIVE_BUILD_AND_BASELINE_ONLY" and built.get("app_sha") == args.expected_app_sha
            and built.get("run_id") == receipt["run_id"] and built.get("run_attempt") == receipt["run_attempt"]
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
    network_resource, network = docker.network()
    directories = {}
    for role in ["creator", "recovered"]:
        directory = docker.private / role
        directory.mkdir(mode=0o700)
        (directory / "account-root").mkdir(mode=0o700)
        write(directory / "ownership.json", {"protocol": PROTOCOL, "nonce": docker.owner, "role": role, "synthetic_only": True})
        directories[role] = directory
    creator_deadline = time.monotonic() + 360
    creator = docker.start("creator", network, directories["creator"], binary, manifest["fixture_sha256"], creator_deadline)
    reports = {"creator": docker.wait_ready(creator, creator_deadline)}
    recovered_deadline = time.monotonic() + 540
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
    recovered = docker.start("recovered", network, directories["recovered"], binary, manifest["fixture_sha256"], recovered_deadline)
    reports["recovered"] = docker.wait_ready(recovered, recovered_deadline)
    resources = {"creator": creator, "recovered": recovered}
    inspections = {role: docker.find(resource, recovered_deadline) for role, resource in resources.items()}
    current_network = docker.find(network_resource, recovered_deadline)
    require(set(current_network.get("Containers", {})) == {r["id"] for r in resources.values()}, "Unexpected peer in the owned LAN")
    identity = built["baseline"]["identities"]["new"]
    for role in resources:
        validate_container(inspections[role], docker.owner, role, network, directories[role], binary, image["Id"], os.getuid(), os.getgid())
        validate_ready(reports[role], role, docker.owner, state, state_hash, identity, manifest["fixture_sha256"], inspections[role], network)
    validate_pair(reports, inspections)
    receipt.update(state_sha256=state_hash, seed_files=["account-key.private", "state.json"],
                   native_peers={role: {"container_id": resources[role]["id"], "host_pid": info["State"]["Pid"],
                     "network_sandbox_id": info["NetworkSettings"]["SandboxID"], "native_peer_id": reports[role]["peer_id"],
                     "namespace": reports[role]["network_namespace"]} for role, info in inspections.items()},
                   original_signed_history_matches=True, independent_empty_roots=True)
    docker.checkpoint()
    docker.remaining(recovered_deadline)
    for role in resources:
        write(directories[role] / "stop.json", {"protocol": PROTOCOL, "nonce": docker.owner})
    shutdown_deadline = time.monotonic() + 90
    final_reports = {}
    db_inodes = {}
    for role, resource in resources.items():
        require(docker.command(["container", "wait", resource["id"]], "wait-native-" + role,
                               docker.remaining(shutdown_deadline, 90)) == "0", "Native process failed")
        stopped = docker.find(resource, shutdown_deadline)
        require(stopped["State"].get("Running") is False and stopped["State"].get("ExitCode") == 0,
                "Native process did not complete cleanly")
        log = directories[role] / "native.log"
        docker.command(["container", "logs", resource["id"]], "read-native-" + role, docker.remaining(shutdown_deadline), log)
        final = json.loads((directories[role] / "final.json").read_text())
        validate_final(reports[role], final, log.read_text(), role)
        require(digest(directories[role] / "state.json") == state_hash
                and digest(directories[role] / "account-key.private") == key_hash, "Recovery input changed")
        db_files = list((directories[role] / "account-root").rglob("*.db"))
        require(db_files and all(path.is_file() and not path.is_symlink() for path in db_files), "Real independent native databases missing")
        db_inodes[role] = {(path.stat().st_dev, path.stat().st_ino) for path in db_files}
        final_reports[role] = {"sha256": digest(directories[role] / "final.json"), "native_named_pass": 1,
                               "actual_database_files": len(db_files), "account_stop_verified": True}
    require(not db_inodes["creator"].intersection(db_inodes["recovered"]), "Native clients share a database inode")
    require(source_inputs(args.control)[0] == manifest, "Native client source changed during execution")
    return {"native_results": final_reports, "actual_counts": {"independent_native_clients": 2, "native_named_pass": 2,
            "native_fail": 0, "native_skip": 0}, "distinct_database_inodes": True,
            "transport_scope": "NATIVE_LOCAL_DISCOVERY_AND_AUTHENTICATED_PEER_TRANSPORT_ON_OWNED_INTERNAL_LAN"}


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("stage", choices=["build", "clients"])
    parser.add_argument("--control", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "native-work"]:
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
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
    receipt = {"protocol": PROTOCOL, "status": "NOT_RUN_PREFLIGHT", "stage": args.stage, "app_sha": args.expected_app_sha,
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
            docker = OwnedDocker(private, receipt, checkpoint)
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
                receipt["native_publication"] = publish_native_evidence(docker.private, args.evidence)
                if candidate:
                    require(receipt["native_publication"]["status"] == "PASS_SECRET_SCANNED_EXACT_ALLOWLIST", "Native evidence withheld")
            except BaseException as error:
                candidate = False
                receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) or cancelled else "FAIL",
                               cleanup_or_publication_error_type=type(error).__name__)
        if candidate and not cancelled:
            if args.stage == "clients":
                receipt.update(status="PASS_TWO_NATIVE_CLIENTS_LAN_COLD_BOOTSTRAP", two_native_clients="PASS_LAN_COLD_BOOTSTRAP")
            result = 0
        def finish():
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            checkpoint()
            for item in args.evidence.rglob("*"):
                if item.is_dir(): item.chmod(0o755)
                elif item.is_file() and not item.is_symlink(): item.chmod(0o644)
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
