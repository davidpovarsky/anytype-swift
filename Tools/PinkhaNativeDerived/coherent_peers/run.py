#!/usr/bin/env python3
"""Run only the new coherent authorized peer read, detach and cold reopen."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time

import contract

sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
import run_native_clients as retained
from build import source_snapshot

ARGS = ["-test.run", "^" + contract.METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=1000s"]


class OwnedPeers(retained.OwnedDocker):
    """Reuse the existing owner-labelled Docker process and cleanup machinery."""

    def start_peer(self, role, phase, network, directory, binary, build, deadline):
        contract.require(role in {"creator", "recovered"} and phase in {"online", "reopen"}
                         and (phase != "reopen" or (role == "recovered" and network is None)), "Unreviewed peer phase")
        resource = dict(kind="container", name=self.prefix + "-coherent-" + role + "-" + phase, id=None,
                        role=role, private=str(directory), log="reopen-native.log" if phase == "reopen" else "native.log")
        self.resources.append(resource)
        arguments = ["container", "create", "--name", resource["name"], "--label", retained.OWNER_LABEL + "=" + self.owner,
            "--platform", "linux/amd64", "--network", network["Name"] if network else "none", "--read-only", "--init=false",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
            "--cpus", "1", "--memory", "2g", "--pids-limit", "256", "--workdir", "/private",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777",
            "--mount", f"type=bind,src={directory},dst=/private",
            "--mount", f"type=bind,src={binary},dst=/fixture/native.test,readonly",
            "-e", "PINKHA_T2_CLIENT_ROLE=" + role, "-e", "PINKHA_T2_CLIENT_NONCE=" + self.owner,
            "-e", "PINKHA_T2_CLIENT_FIXTURE_SHA=" + build["fixture_sha256"], "-e", "PINKHA_COHERENT_PEER_PHASE=" + phase,
            "-e", "PINKHA_COHERENT_RUNTIME_VERSION=" + build["runtime_version"],
            "-e", "GOMAXPROCS=2", "-e", "GOMEMLIMIT=768MiB", contract.IMAGE, "/fixture/native.test", *ARGS]
        resource["id"] = self.command(arguments, "create-coherent-" + role + "-" + phase, self.remaining(deadline))
        contract.require(re.fullmatch("[0-9a-f]{64}", resource["id"]), "Missing native container identity")
        self.command(["container", "start", resource["id"]], "start-coherent-" + role + "-" + phase, self.remaining(deadline))
        return resource

    def wait_peer(self, resource, deadline, filename):
        contract.require(filename in {"ready.json", "offline.json", "reopen.json"}, "Unreviewed peer receipt selection")
        path = Path(resource["private"]) / filename
        next_check = 0
        while time.monotonic() < deadline:
            if path.exists():
                return contract.load(path)
            if time.monotonic() >= next_check:
                observed = self.find(resource, deadline)
                contract.require(observed and observed["State"].get("Running") is True, "Peer exited before actual read evidence")
                next_check = time.monotonic() + 5
            time.sleep(0.2)
        raise TimeoutError("Bounded new peer phase did not complete")


def validate_container(info, owner, role, phase, network, directory, binary, image_id, build):
    config, host, network_settings = info.get("Config", {}), info.get("HostConfig", {}), info.get("NetworkSettings", {})
    contract.require(config.get("Labels", {}).get(retained.OWNER_LABEL) == owner and config.get("Image") == contract.IMAGE
                     and info.get("Image") == image_id and config.get("User") == f"{os.getuid()}:{os.getgid()}"
                     and info.get("Path") == "/fixture/native.test" and info.get("Args") == ARGS, "Wrong owned native executable")
    contract.require(host.get("ReadonlyRootfs") is True and host.get("Privileged") is False and host.get("CapDrop") == ["ALL"]
                     and "no-new-privileges" in host.get("SecurityOpt", []) and not host.get("PortBindings")
                     and not host.get("PidMode") and not host.get("Init") and host.get("NanoCpus") == 1000000000
                     and host.get("Memory") == 2 * 1024**3 and host.get("PidsLimit") == 256,
                     "Native process isolation or resource limits differ")
    mounts = info.get("Mounts", [])
    destinations = [entry.get("Destination") for entry in mounts]
    contract.require(len(destinations) == len(set(destinations)), "Repeated native mount destination")
    binds = {entry["Destination"]: entry for entry in mounts if entry.get("Type") == "bind"}
    contract.require(set(binds) == {"/private", "/fixture/native.test"}
                     and binds["/private"].get("Source") == str(directory) and binds["/private"].get("RW") is True
                     and binds["/fixture/native.test"].get("Source") == str(binary) and binds["/fixture/native.test"].get("RW") is False
                     and all(entry.get("Type") == "bind" or (entry.get("Type") == "tmpfs" and entry.get("Destination") == "/tmp") for entry in mounts),
                     "Native process can see another store/build tree")
    networks = network_settings.get("Networks", {})
    if network:
        contract.require(host.get("NetworkMode") == network["Name"] and set(networks) == {network["Name"]}
                         and networks[network["Name"]].get("NetworkID") == network["Id"], "Peer has another network")
    else:
        contract.require(host.get("NetworkMode") == "none" and set(networks) == {"none"}
                         and not networks["none"].get("IPAddress"), "Cold reopen can reach a peer")
    env = dict(item.split("=", 1) for item in config.get("Env", []) if "=" in item)
    expected = dict(PINKHA_T2_CLIENT_ROLE=role, PINKHA_T2_CLIENT_NONCE=owner, PINKHA_T2_CLIENT_FIXTURE_SHA=build["fixture_sha256"],
                    PINKHA_COHERENT_PEER_PHASE=phase, PINKHA_COHERENT_RUNTIME_VERSION=build["runtime_version"])
    contract.require(all(env.get(key) == value for key, value in expected.items())
                     and not any(key in env for key in ("PINKHA_T2_CLIENT_SCENARIO", "PINKHA_T2_CRASH_PHASE",
                                                       "PINKHA_T2_OBSERVED_REMOVE_PHASE", "PINKHA_T2_CONCURRENT_REPLACE_PHASE")),
                     "Another old suite or phase was selected")


def live_identity(info, report):
    host_pid = info.get("State", {}).get("Pid")
    contract.require(type(host_pid) is int and host_pid > 0 and info["State"].get("Running") is True,
                     "Actual native host process not running")
    contract.require(os.readlink(f"/proc/{host_pid}/ns/net") == report["network_namespace"], "Observed native namespace differs")
    return dict(container_id=info["Id"], host_pid=host_pid, namespace=report["network_namespace"],
                sandbox_id=info["NetworkSettings"]["SandboxID"], peer_id=report["peer_id"])


def send(directory, phase, nonce):
    path = directory / (phase + ".command.json")
    contract.require(not path.exists(), "Owned phase command cannot be replayed")
    contract.save(path, dict(protocol=contract.PROTOCOL, nonce=nonce, phase=phase))


def complete(docker, resource, initial, build, state, state_hash, *, reopened=False):
    deadline = time.monotonic() + 90
    contract.require(docker.command(["container", "wait", resource["id"]], "wait-native-exit", docker.remaining(deadline, 90)) == "0",
                     "New native method failed")
    observed = docker.find(resource, deadline)
    contract.require(observed and observed["State"].get("Running") is False and observed["State"].get("ExitCode") == 0,
                     "Native exit not observed")
    directory = Path(resource["private"])
    prefix = "reopen-" if reopened else ""
    log = directory / (prefix + "native.log")
    docker.command(["container", "logs", resource["id"]], "read-native-log", docker.remaining(deadline), log)
    final = contract.load(directory / (prefix + "final.json"))
    positive_name = "reopen.pb" if reopened else ("offline.pb" if resource["role"] == "recovered" else "ready.pb")
    contract.validate_report(final, prefix + "final", resource["role"], docker.owner, build, state, state_hash,
                             (directory / positive_name).read_bytes())
    contract.validate_final(final, (directory / (prefix + "stopped.pb")).read_bytes(), log.read_text(), initial, reopened=reopened)
    return dict(method=contract.METHOD, passed=1, failed=0, skipped=0, log_sha256=contract.digest(log),
                final_sha256=contract.digest(directory / (prefix + "final.json")))


def execute(args, receipt, docker):
    build_path = args.evidence / "build.json"
    build = contract.load(build_path)
    contract.validate_build(build, args.expected_app_sha, receipt["run_id"], receipt["run_attempt"])
    before = source_snapshot(args.control)
    contract.require(before == contract.load(args.evidence / "build-control-source-after.json"), "Controller changed since native build")
    binary = args.native_work / build["binary_path"]
    contract.require(binary.is_file() and not binary.is_symlink() and contract.digest(binary) == build["binary_sha256"],
                     "Native executable differs from the original build")
    receipt.update(build_receipt_sha256=contract.digest(build_path), binary_sha256=build["binary_sha256"],
                   fixture_sha256=build["fixture_sha256"], native_source_run=contract.NATIVE_RUN,
                   patch_sha256=contract.PATCH, inventory_sha256=contract.INVENTORY)
    image = json.loads(docker.command(["image", "inspect", contract.IMAGE], "inspect-native-image"))[0]
    contract.require(image.get("Os") == "linux" and image.get("Architecture") == "amd64", "Wrong runtime platform")
    network_resource, network = docker.network()
    directories = {}
    for role in ("creator", "recovered"):
        directory = docker.private / role
        directory.mkdir(mode=0o700)
        (directory / "account-root").mkdir(mode=0o700)
        contract.save(directory / "ownership.json", dict(protocol=contract.PROTOCOL, nonce=docker.owner, role=role, synthetic_only=True))
        directories[role] = directory
    deadline = time.monotonic() + 360
    resources = {"creator": docker.start_peer("creator", "online", network, directories["creator"], binary, build, deadline)}
    reports = {"creator": docker.wait_peer(resources["creator"], deadline, "ready.json")}
    state_path = directories["creator"] / "state.json"
    state, state_hash = contract.load(state_path), contract.digest(state_path)
    contract.validate_state(state)
    key = directories["creator"] / "account-key.private"
    contract.require(key.is_file() and not key.is_symlink() and key.stat().st_size > 0 and key.stat().st_mode & 0o077 == 0,
                     "Private synthetic recovery key missing")
    key_hash = contract.digest(key)
    contract.require(not any((directories["recovered"] / "account-root").iterdir()), "B must begin empty")
    for source in (state_path, key):
        target = directories["recovered"] / source.name
        with target.open("xb") as stream:
            stream.write(source.read_bytes()); stream.flush(); os.fsync(stream.fileno())
        target.chmod(0o600)
    receipt["seed_files"] = ["account-key.private", "state.json"]
    deadline = time.monotonic() + 540
    resources["recovered"] = docker.start_peer("recovered", "online", network, directories["recovered"], binary, build, deadline)
    reports["recovered"] = docker.wait_peer(resources["recovered"], deadline, "ready.json")
    identities = {}
    for role in resources:
        observed = docker.find(resources[role], deadline)
        validate_container(observed, docker.owner, role, "online", network, directories[role], binary, image["Id"], build)
        contract.validate_report(reports[role], "ready", role, docker.owner, build, state, state_hash,
                                 (directories[role] / "ready.pb").read_bytes())
        identities[role] = live_identity(observed, reports[role])
    contract.validate_pair(reports["creator"], reports["recovered"])
    contract.require(all(identities["creator"][key] != identities["recovered"][key]
                         for key in ("container_id", "host_pid", "namespace", "sandbox_id", "peer_id")), "Native process/store ownership overlaps")
    current = docker.find(network_resource, deadline)
    contract.require(set(current.get("Containers", {})) == {value["id"] for value in resources.values()}, "Unexpected LAN member")
    receipt["native_peers"] = identities
    docker.checkpoint()
    # Actual daemon network detach precedes the command and both independent
    # inspections. A mocked DeviceNetworkStateSet cannot establish this gate.
    docker.command(["network", "disconnect", network_resource["id"], resources["recovered"]["id"]], "detach-reader", 30)
    disconnected = docker.find(resources["recovered"])
    contract.require(disconnected["NetworkSettings"].get("Networks") == {}
                     and set(docker.find(network_resource).get("Containers", {})) == {resources["creator"]["id"]},
                     "Actual native reader network was not detached")
    detached_identity = live_identity(disconnected, reports["recovered"])
    contract.require(detached_identity == identities["recovered"], "Detach replaced the native process")
    send(directories["recovered"], "offline", docker.owner)
    offline = docker.wait_peer(resources["recovered"], time.monotonic() + 70, "offline.json")
    contract.validate_report(offline, "offline", "recovered", docker.owner, build, state, state_hash,
                             (directories["recovered"] / "offline.pb").read_bytes())
    contract.require(offline["variant_sha256"] == reports["recovered"]["variant_sha256"]
                     and docker.find(resources["recovered"])["NetworkSettings"].get("Networks") == {},
                     "Disconnected read was repaired through a peer or changed the variant")
    receipt["network_detach"] = dict(status="OBSERVED_DAEMON_DETACH_AND_NATIVE_NO_INTERFACES", container_id=resources["recovered"]["id"],
                                     offline_receipt_sha256=contract.digest(directories["recovered"] / "offline.json"))
    for directory in directories.values():
        send(directory, "stop", docker.owner)
    results = {role: complete(docker, resource, offline if role == "recovered" else reports[role], build, state, state_hash)
               for role, resource in resources.items()}
    inodes = {}
    for role, directory in directories.items():
        files = list((directory / "account-root").rglob("*.db"))
        contract.require(files and all(path.is_file() and not path.is_symlink() for path in files), "Missing actual native database")
        inodes[role] = {(path.stat().st_dev, path.stat().st_ino) for path in files}
        contract.require(contract.digest(directory / "state.json") == state_hash and contract.digest(directory / "account-key.private") == key_hash,
                         "Public seed or original key changed")
    contract.require(not inodes["creator"].intersection(inodes["recovered"]), "Two native clients share database inodes")
    deadline = time.monotonic() + 300
    reopened = docker.start_peer("recovered", "reopen", None, directories["recovered"], binary, build, deadline)
    cold = docker.wait_peer(reopened, deadline, "reopen.json")
    observed = docker.find(reopened, deadline)
    validate_container(observed, docker.owner, "recovered", "reopen", None, directories["recovered"], binary, image["Id"], build)
    cold_identity = live_identity(observed, cold)
    contract.require(cold_identity["peer_id"] == identities["recovered"]["peer_id"]
                     and all(cold_identity[key] not in {value[key] for value in identities.values()}
                             for key in ("container_id", "host_pid", "namespace", "sandbox_id")), "Cold reopen did not use a new isolated process")
    contract.validate_report(cold, "reopen", "recovered", docker.owner, build, state, state_hash,
                             (directories["recovered"] / "reopen.pb").read_bytes())
    contract.require(cold["variant_sha256"] == offline["variant_sha256"], "Cold native disk read changed original provenance")
    send(directories["recovered"], "reopen-stop", docker.owner)
    results["reopened"] = complete(docker, reopened, cold, build, state, state_hash, reopened=True)
    contract.require(contract.digest(binary) == build["binary_sha256"] and source_snapshot(args.control) == before,
                     "Executed native binary or controller source changed")
    contract.save(args.evidence / "peer-control-source-after.json", source_snapshot(args.control))
    receipt.update(status=contract.PASS, native_results=results, cold_process=cold_identity, independent_empty_roots=True,
                   distinct_database_inodes=True, first_private_read="PinkhaTorahAuthorizedOperationRead",
                   old_test_methods_executed=0, actual_native_processes=3, actual_named_pass=3, actual_fail=0, actual_skip=0)


def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control", "native-work", "private", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    for name in ("control", "native_work", "private", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "receipt.json"
    contract.require(not path.exists() and not args.private.exists(), "Fresh owned peer attempt required")
    args.private.mkdir(mode=0o700)
    receipt = dict(protocol=contract.PROTOCOL, status="NOT_RUN", app_sha=args.expected_app_sha,
                   run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), commands=[], **contract.LIMITS)
    checkpoint = lambda: contract.save(path, receipt)
    docker = OwnedPeers(args.private, receipt, checkpoint)
    contract.save(args.private / "owner.json", dict(protocol=contract.PROTOCOL, nonce=docker.owner))
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    cancelled = False
    def cancel(number, _):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous:
        signal.signal(number, cancel)
    try:
        execute(args, receipt, docker)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__)
    finally:
        try:
            docker.cleanup()
            receipt["evidence_export"] = contract.export(args.private, args.evidence / "actual")
            if receipt["status"] == contract.PASS:
                expected = {role + "/" + name for role, names in contract.PUBLISHED.items() for name in names if name != "cancel.json"}
                contract.require(receipt["evidence_export"]["status"] == "PASS_EXACT_SYNTHETIC_SECRET_SCAN"
                                 and set(receipt["evidence_export"]["files"]) == expected, "Successful peer proof is incomplete")
            contract.require(contract.load(args.private / "owner.json") == dict(protocol=contract.PROTOCOL, nonce=docker.owner),
                             "Private data cleanup ownership changed")
            shutil.rmtree(args.private)
            receipt["owned_data_cleanup"] = "PASS"
        except BaseException as error:
            receipt.update(status="FAIL", cleanup_or_publication_error=type(error).__name__)
        for number, handler in previous.items():
            signal.signal(number, handler)
    finalized = retained.finish_evidence(receipt, args.evidence, path, checkpoint, emit_notice=False)
    return int(not finalized or receipt["status"] != contract.PASS)


if __name__ == "__main__":
    raise SystemExit(main())
