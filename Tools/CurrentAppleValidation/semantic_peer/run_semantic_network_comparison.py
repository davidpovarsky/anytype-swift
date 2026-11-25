#!/usr/bin/env python3
"""Real semantic anchors and signed canonical claims across native AnySync-network accounts.

Uses the actual shared Swift codec/conditional editor/signed claim repository,
original native CLI, real private AnySync network, and a distinct OS-offline native process.
The separately retained original LAN discovery attempt failed before any semantic write.
Original driver lineage68a937 (SHA c2754d3a62abafd43e576c67c7e30b463dd202f2b6aecbf77356fee68d2a902d).
No App UI, physical device, file-transfer, whole-migration or cloud-custody claim.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodeconf", required=True, type=Path)
    parser.add_argument("--nodeconf-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("assertion-enabled controller is required")
    args.binary = Path("/Users/m1/builds/pinkha-c-recovered-native-cli-20261125/any548")
    args.binary_sha256 = "7f9124991e206657f21a9788b58f65de3ec57e019f425772dd4be6b677f803df"
    native_root = args.binary.parent
    swift_root = Path("/Users/m1/builds/e-semantic-peer-native-20261125")
    swift_binary = swift_root / "scratch/arm64-apple-macosx/debug/pinkha-any-host-probe"
    swift_sha256 = "d29ff41ecfa0e0dcdf1473489aa9a868e97ff4d053224d99d8cb6dc8fe096e63"
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    assert args.output.resolve() == args.output and not args.output.is_symlink()
    logdir = args.output / "private-logs"
    logdir.mkdir(mode=0o700)
    def regular_bytes(p, maximum=None):
        st = p.lstat()
        if not stat.S_ISREG(st.st_mode) or p.is_symlink() or p.resolve() != p:
            raise RuntimeError("canonical regular original required: " + str(p))
        if maximum is not None and st.st_size > maximum:
            raise RuntimeError("private original exceeds its bound")
        return p.read_bytes()
    def sha(p):
        return hashlib.sha256(regular_bytes(p)).hexdigest()
    assert sha(args.binary) == args.binary_sha256, "native binary identity changed"
    assert sha(swift_binary) == swift_sha256, "shared Swift probe identity changed"
    assert sha(args.nodeconf) == args.nodeconf_sha256, "actual public network configuration changed"
    assert sha(native_root / "build-attempt1/receipt.json") == "7a39a95cc03f7b6ab8f75d453c0795d8af019e47d8fc5815b854453b3c3faa7f"
    assert sha(swift_root / "probe-build1/receipt.json") == "adf8c8055268332670c2ea25f37e4e0b8a8498871ea148462471827f24c2910e"
    native_manifest = json.loads(regular_bytes(native_root / "build-attempt1/receipt.json"))
    swift_receipt = json.loads(regular_bytes(swift_root / "probe-build1/receipt.json"))
    swift_manifest = json.loads(regular_bytes(swift_root / "probe-build1/source-before.json"))
    assert native_manifest["sourceBefore"] == native_manifest["sourceAfter"]
    assert native_manifest["status"] == "PASS_BUILD_NOT_NATIVE_ACCEPTANCE" and native_manifest["exitCode"] == 0
    assert swift_receipt["status"] == "PASS_BUILD_NOT_PEER_ACCEPTANCE" and swift_receipt["exitCode"] == 0
    assert sha(swift_root / "probe-build1/source-before.json") == swift_receipt["sourceManifestSHA256"]
    assert regular_bytes(swift_root / "probe-build1/source-before.json") == regular_bytes(swift_root / "probe-build1/source-after.json")
    def verify_sources():
        assert sha(args.nodeconf) == args.nodeconf_sha256, "original public network configuration changed"
        for name, expected in native_manifest["sourceBefore"].items():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            assert sha(native_root / "source" / name) == expected, "original native source changed"
        for name, expected in swift_manifest.items():
            assert not Path(name).is_absolute() and ".." not in Path(name).parts
            data = regular_bytes(swift_root / "source" / name)
            assert len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"]
        for identity, revision in swift_receipt["actualDependencies"].items():
            root = swift_root / "scratch/checkouts" / ({"torahinspectorkit": "TorahInspectorKit"}.get(identity, identity))
            assert subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"]).decode().strip() == revision
            assert not subprocess.check_output(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"]).strip()
        assert sha(args.binary) == args.binary_sha256 and sha(swift_binary) == swift_sha256
        return {"nativeFiles": len(native_manifest["sourceBefore"]), "sharedSwiftFiles": len(swift_manifest),
                "nativeSourcesUnchanged": True, "sharedSourcesAndDependenciesUnchanged": True}

    result = {
        "scope": "real semantic marker, rich text and signed canonical associations synchronize bidirectionally across independent native accounts, then survive cold OS-offline reopen",
        "shared_swift_binary_sha256": swift_sha256,
        "ui_acceptance": False,
        "physical_device_acceptance": False,
        "native_and_app_builds": 0,
        "binary_sha256": args.binary_sha256,
        "nodeconf_sha256": args.nodeconf_sha256,
        "sources_before": verify_sources(),
        "cloud_custody_accepted": False,
        "whole_space_migration_accepted": False,
        "fixtures_retained": True,
        "result": "RUNNING",
        "phases": [],
        "probe_invocations": [],
        "processes": [],
        "resource_policy": {
            "estimated_new_disk_bytes": 256 * 1024**2,
            "emergency_free_bytes": 2 * 1024**3,
            "rationale": "No compile/download; one real anchored page, signed canonical claims, two encrypted native stores plus indexes/logs. A256MiB phase allowance and active-work2GiB emergency floor bound the runtime phase."
        }
    }
    prior_root = swift_root / "peer-attempt1"
    prior_path = prior_root / "result.json"
    assert sha(prior_path) == "7ecfbdee6744d793320c623c632100b9fbe548eb46a7638d457db6dd6f3996c7"
    prior = json.loads(regular_bytes(prior_path))
    assert prior["result"] == "FAIL" and prior["failed_phase"] == "genuine local discovery"
    assert prior["error"] == "genuine mDNS shared-space discovery missing"
    assert prior["probe_invocations"] == [] and not (prior_root / "semantic-original-fixture.json").exists()
    assert prior["cleanup"]["status"] == "PASS" and prior["cleanup"]["allOwnedProcessGroupsAbsent"] is True
    assert [r["name"] for r in prior["phases"]] == ["distinct native accounts and processes", "native invite accepted"]
    assert prior["recipient_role"] == "writer" and prior["nodeconf_sha256"] == args.nodeconf_sha256
    assert len(prior["processes"]) == 2 and {r["name"] for r in prior["processes"]} == {"alice", "bob"}
    assert set(prior["accounts"]) == {"alice", "bob"} and len(set(prior["accounts"].values())) == 2
    for row in prior["private_log_receipts"]:
        data = regular_bytes(prior_root / "private-logs" / row["name"])
        assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
    network_configs = {}
    for name in ("alice", "bob"):
        original = prior_root / name / "config.yaml"
        actual = regular_bytes(original, 16384).decode()
        old = "p2p:\n  enabled: true\n  localDiscovery: true\n"
        new = "p2p:\n  enabled: false\n  localDiscovery: false\n"
        assert actual.count(old) == 1 and "  global:\n    enabled: false\n" in actual
        target = args.output / (name + "-network-config.yaml")
        target.write_text(actual.replace(old, new))
        assert regular_bytes(target).decode().replace(new, old) == actual
        network_configs[name] = target
    result.update(scope="real semantic marker, rich text and signed canonical associations synchronize bidirectionally across distinct native accounts over actual private AnySync network, then survive cold OS-offline reopen",
                  priorInviteReceiptSHA256=sha(prior_path), priorLANResult="FAIL_BEFORE_SEMANTIC_WRITES",
                  lanAcceptance=False, fakeDiscovery=False, newAccountsCreated=0,
                  scenarioConfiguration="Only this case disables native LAN discovery; original failed LAN configuration and accounts remain retained unchanged",
                  originalConfigHashes={name:sha(prior_root/name/"config.yaml") for name in ("alice","bob")},
                  networkConfigHashes={name:sha(path) for name,path in network_configs.items()})
    started = time.monotonic()
    processes = []
    auxiliary_processes = []
    absent_groups = set()
    streams = []
    phase = "preflight"
    minimum_free = shutil.disk_usage(args.output).free
    assert minimum_free >= 2 * 1024**3 + 256 * 1024**2, "measured runtime phase does not fit"

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimum_free_bytes"] = minimum_free
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    def guard():
        nonlocal minimum_free
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        if minimum_free < 2 * 1024**3:
            raise RuntimeError("disk_emergency")
        if time.monotonic() - started > 720:
            raise RuntimeError("bounded_runtime_timeout")

    def mark(name, **values):
        result["phases"].append({"name": name, "seconds": round(time.monotonic() - started, 3), **values})
        save()

    def request(peer, method, path, body=None, headers=None, timeout=20):
        guard()
        h = dict(headers or {})
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(peer["base"] + path, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status, response.read(20 * 1024**2), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, error.read(65536), dict(error.headers)

    def json_request(peer, method, path, body=None, expected=200):
        status, data, _ = request(peer, method, path, body)
        if status != expected:
            try: code = json.loads(data).get("error", {}).get("code", "unknown")
            except (ValueError, AttributeError): code = "non_json"
            raise RuntimeError("HTTP " + str(status) + " expected " + str(expected) + " at " + path + " code=" + str(code))
        return json.loads(data) if data else None

    def until(seconds, predicate, message):
        deadline = time.monotonic() + seconds
        while True:
            guard()
            value = predicate()
            if value:
                return value
            if time.monotonic() >= deadline:
                raise RuntimeError(message)
            time.sleep(0.5)

    def free_port():
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    def observe_owned_group(group):
        # No global ps listing, and no re-probe of a historical ID already
        # observed absent. killpg(..., 0) is an observation, never a signal.
        if group in absent_groups:
            return True
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            absent_groups.add(group)
            return True
        except PermissionError:
            raise RuntimeError("owned group observation denied")
        return False

    def start_peer(name, data_dir, initialize=False, sandbox_profile=None):
        assert sha(args.nodeconf) == args.nodeconf_sha256, "public nodeconf changed before native start"
        data_dir.mkdir(mode=0o700, exist_ok=True)
        cfg = network_configs["bob" if name == "bob-cold-offline" else name]
        assert initialize is False, "this distinct scenario reuses the exact accepted native accounts without repeating init/invite"
        if initialize:
            cfg.write_text("network:\n  nodeconfPath: " + str(args.nodeconf) +
                           "\nindex:\n  embedder: none\np2p:\n  enabled: true\n  localDiscovery: true\n  serviceName: _pinkhasemantic._tcp\n  global:\n    enabled: false\n")
        assert cfg.is_file()
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        env.update({"ANY_DATA_DIR": str(data_dir), "GOMAXPROCS": "2", "GOMEMLIMIT": "2GiB"})
        if initialize:
            init_path = logdir / (name + "-init.log")
            with init_path.open("wb") as log:
                initialized = subprocess.Popen([str(args.binary), "init", "--config", str(cfg), "--data-dir", str(data_dir)],
                    env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                auxiliary_processes.append(initialized)
                initialized.wait(timeout=60)
            assert initialized.returncode == 0 and observe_owned_group(initialized.pid), name + " native account init did not exit cleanly"
        port = free_port()
        addr = "127.0.0.1:" + str(port)
        command = [str(args.binary), "run", "--config", str(cfg), "--data-dir", str(data_dir), "--addr", addr]
        if sandbox_profile:
            command = ["/usr/bin/sandbox-exec", "-f", str(sandbox_profile)] + command
        log = (logdir / (name + "-server.log")).open("wb")
        streams.append(log)
        proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        info = {"name": name, "pid": proc.pid, "data_dir": str(data_dir), "port": port,
                "sandboxed": bool(sandbox_profile), "started_seconds": round(time.monotonic() - started, 3)}
        result["processes"].append(info)
        peer = {"name": name, "base": "http://" + addr, "process": proc, "info": info}
        processes.append(peer)
        save()
        def ready():
            if proc.poll() is not None:
                raise RuntimeError(name + " exited before ready; private log retained")
            try:
                return request(peer, "GET", "/v1/health", timeout=1)[0] == 200
            except (OSError, urllib.error.URLError):
                return False
        until(60, ready, name + " native readiness timeout")
        return peer

    def stop_peer(peer):
        proc = peer["process"]
        forced = False
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try: proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                forced = True
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        peer["info"].update({"exit_code": proc.returncode, "forced_kill": forced})
        peer["info"]["ownedGroupAbsentAtExit"] = observe_owned_group(proc.pid)
        save()
        return not forced and proc.returncode == 0 and peer["info"]["ownedGroupAbsentAtExit"]

    def public_peer_status(peer, space_id):
        value = json_request(peer, "GET", "/v1/debug/p2p")
        return {
            "peerId": value.get("peerId"),
            "matching_connected_peers": [
                {"peerId": p.get("peerId"), "connected": p.get("connected"), "sources": p.get("sources"), "shared_space": True}
                for p in value.get("peers", []) if p.get("connected") and "lan" in (p.get("sources") or []) and space_id in (p.get("spaceIds") or [])
            ]
        }

    fixture_path = args.output / "semantic-original-fixture.json"
    fixture_sha = None
    probe_processes = []
    def run_probe(peer, account_id, space_id, mode, writes=False, allow_pending=False):
        guard()
        if mode == "prepare":
            assert not fixture_path.exists() and fixture_sha is None
        else:
            current = regular_bytes(fixture_path, 65_536)
            assert hashlib.sha256(current).hexdigest() == fixture_sha, "original fixture changed"
        assert not (writes and allow_pending), "mutations are never retried"
        number = len(result["probe_invocations"]) + 1
        name = f"probe-{number:02d}-{peer['name']}-{mode}"
        command = [str(swift_binary), peer["base"], space_id, account_id,
                   "--semantic-peer", mode, "--semantic-fixture", str(fixture_path)]
        if writes:
            command.append("--allow-disposable-writes")
        with (logdir / (name + ".log")).open("xb") as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            probe_processes.append(proc)
            row = {"name": name, "mode": mode, "pid": proc.pid, "pgid": proc.pid,
                   "writes": writes, "startedSeconds": round(time.monotonic() - started, 3)}
            result["probe_invocations"].append(row)
            save()
            cutoff = time.monotonic() + 60
            while proc.poll() is None:
                guard()
                if time.monotonic() > cutoff:
                    raise RuntimeError("bounded shared native probe timeout; private evidence retained")
                time.sleep(0.2)
            row["exitCode"] = proc.returncode
            row["ownedGroupAbsentAtExit"] = observe_owned_group(proc.pid)
        original = regular_bytes(logdir / (name + ".log"), 1024**2)
        row["originalLogSHA256"] = hashlib.sha256(original).hexdigest()
        row["originalLogBytes"] = len(original)
        save()
        assert row["ownedGroupAbsentAtExit"], "shared probe left an owned descendant"
        if proc.returncode != 0:
            if allow_pending:
                return False
            raise RuntimeError("shared native " + mode + " failed; exact private log retained")
        output = json.loads(original)
        assert output["status"] == "PASS" and output["phase"] == mode
        assert output["scope"] == "shared_semantic_codec_and_signed_native_repository_on_actual_peer"
        assert output["uiAcceptance"] is False and output["physicalDevice"] is False
        assert output["networkAndColdProcessProof"] == "required_from_independent_controller"
        required = {"authoritative_native_body_marker_and_canonical_payload_equality", "native_application_lease_drained"}
        if mode == "prepare": required.add("actual_guarded_native_marker_and_signed_canonical_claims")
        if mode == "edit": required.add("distinct_invited_account_real_conditional_edit_preserves_marker")
        if mode == "unlink": required.add("original_owner_removes_only_exact_semantic_association")
        assert set(output["checks"]) == required and len(output["checks"]) == len(required)
        if mode != "prepare":
            assert sha(fixture_path) == fixture_sha
        row["qualified"] = True
        save()
        return True

    try:
        phase = "same distinct native accounts and existing Writer grant"
        alice = start_peer("alice", prior_root / "alice")
        bob = start_peer("bob", prior_root / "bob")
        alice_id = json_request(alice, "GET", "/v1/account")["id"]
        bob_id = json_request(bob, "GET", "/v1/account")["id"]
        assert {"alice": alice_id, "bob": bob_id} == prior["accounts"] and alice_id != bob_id
        assert alice["process"].pid != bob["process"].pid
        space_id = prior["space_id"]
        member = json_request(bob, "GET", "/v1/spaces/" + space_id + "/members/me")
        assert member["identity"] == bob_id and member["permission"] == "writer" and member["status"] == "active"
        result.update(accounts={"alice":alice_id,"bob":bob_id},space_id=space_id,recipient_role="writer")
        mark("original distinct accounts and actual Writer membership revalidated")
        phase = "real AnySync network transport"
        def network_ready():
            observed = {}
            for name, peer in (("alice",alice),("bob",bob)):
                direct = json_request(peer,"GET","/v1/debug/p2p")
                assert direct["enabled"] is False and direct["localDiscovery"] is False
                state = json_request(peer,"GET","/v1/spaces/"+space_id+"/sync-status")
                assert state["localPeers"] == 0 and state["globalPeers"] == 0
                observed[name] = {"networkPeers":state["networkPeers"],"localPeers":state["localPeers"],
                                  "globalPeers":state["globalPeers"],"state":state["state"],
                                  "localDiscovery":direct["localDiscovery"],"p2pEnabled":direct["enabled"]}
            (args.output/"actual-network-status.json").write_text(json.dumps(observed,indent=2)+"\n")
            return observed if all(x["networkPeers"]>0 for x in observed.values()) else False
        result["actual_network_transport"] = until(90,network_ready,"actual native AnySync network peers missing")
        mark("both native accounts connected to real AnySync network; LAN and global P2P disabled only in this scenario")

        phase = "owner writes actual native marker and canonical links"
        run_probe(alice, alice_id, space_id, "prepare", writes=True)
        fixture_bytes = regular_bytes(fixture_path, 65_536)
        fixture_sha = hashlib.sha256(fixture_bytes).hexdigest()
        fixture = json.loads(fixture_bytes)
        assert fixture["spaceID"] == space_id and fixture["creatorAccountID"] == alice_id
        assert fixture["version"] == 1 and fixture["objectID"] and fixture["blockID"]
        result["fixture"] = {"bytes": len(fixture_bytes), "sha256": fixture_sha,
            "linkedCanonicalSHA256": hashlib.sha256(__import__('base64').b64decode(fixture["linkedCanonical"], validate=True)).hexdigest(),
            "unlinkedCanonicalSHA256": hashlib.sha256(__import__('base64').b64decode(fixture["unlinkedCanonical"], validate=True)).hexdigest()}
        mark("owner conditional marker and signed semantic/unrelated claims committed")
        phase = "independent writer receives exact semantic payload"
        until(90, lambda: run_probe(bob, bob_id, space_id, "read-linked", allow_pending=True),
              "writer did not observe exact native marker and canonical links")
        mark("recipient exact rich text marker and canonical payload equality")
        phase = "independent writer edits the anchored fragment"
        run_probe(bob, bob_id, space_id, "edit", writes=True)
        phase = "original owner receives independent edit"
        until(90, lambda: run_probe(alice, alice_id, space_id, "read-edited", allow_pending=True),
              "original owner did not observe exact independently edited semantic fragment")
        mark("independent writer edit synchronized back to original owner")
        phase = "original owner removes only the semantic source association"
        run_probe(alice, alice_id, space_id, "unlink", writes=True)
        phase = "independent writer receives exact unlink preserving unrelated data"
        until(90, lambda: run_probe(bob, bob_id, space_id, "read-unlinked", allow_pending=True),
              "recipient did not observe exact unlink and preserved unrelated canonical association")
        mark("exact semantic association removed; original marker, edited body and unrelated source preserved")
        phase = "orderly peer shutdown"
        assert stop_peer(alice), "sender did not close cleanly"
        assert stop_peer(bob), "initial recipient did not close cleanly"
        mark("both original native processes exited cleanly")

        phase = "OS outbound-denial validation"
        profile = args.output / "offline.sb"
        profile.write_text("(version 1)\n(allow default)\n(deny network-outbound)\n")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            probe_port = listener.getsockname()[1]
            baseline = socket.create_connection(("127.0.0.1", probe_port), timeout=2)
            baseline.close()
            probe_code = (
                "import socket,json,errno\n"
                "result={}\n"
                "try:\n socket.create_connection(('127.0.0.1'," + str(probe_port) + "),timeout=2);result['tcp_connect_denied']=False\n"
                "except OSError as e: result['tcp_connect_denied']=e.errno in (errno.EPERM,errno.EACCES);result['tcp_errno']=e.errno\n"
                "s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n"
                "try:\n s.sendto(b'private-offline-probe',('127.0.0.1'," + str(probe_port) + "));result['udp_send_denied']=False\n"
                "except OSError as e: result['udp_send_denied']=e.errno in (errno.EPERM,errno.EACCES);result['udp_errno']=e.errno\n"
                "finally:s.close()\n"
                "print(json.dumps(result))\n"
            )
            probe = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable, "-c", probe_code],
                                   capture_output=True, text=True, timeout=10)
            assert probe.returncode == 0, "sandbox outbound control did not run"
            checked = json.loads(probe.stdout)
            assert checked["tcp_connect_denied"] and checked["udp_send_denied"], "OS outbound sandbox control failed"
        result["offline_policy"] = {"profile_sha256": sha(profile), "probe": checked, "baseline_listener_reachable": True}
        mark("OS denied TCP connects and UDP sends")

        phase = "fresh recipient native process offline read"
        cold = start_peer("bob-cold-offline", prior_root / "bob", sandbox_profile=profile)
        assert cold["process"].pid not in (alice["process"].pid, bob["process"].pid)
        assert json_request(cold, "GET", "/v1/account")["id"] == bob_id
        state = json_request(cold, "GET", "/v1/spaces/" + space_id + "/sync-status")
        result["cold_sync_status"] = {key: state.get(key) for key in ("networkPeers", "localPeers", "globalPeers", "p2p", "state")}
        assert state["networkPeers"] == 0 and state["localPeers"] == 0 and state["globalPeers"] == 0
        run_probe(cold, bob_id, space_id, "read-unlinked")
        assert sha(fixture_path) == fixture_sha
        mark("distinct OS-offline process reproduces exact original semantic contract")
        assert stop_peer(cold), "cold native process did not close cleanly"
        mark("fresh offline native process retained original marker, edited text and remaining canonical association")
        result["sources_after"] = verify_sources()
        assert {name:sha(prior_root/name/"config.yaml") for name in ("alice","bob")} == result["originalConfigHashes"]
        result["result"] = "PASS"
        result["all_scoped_checks_passed"] = True
    except Exception as error:
        result["result"] = "FAIL"
        result["failed_phase"] = phase
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
        result["all_scoped_checks_passed"] = False
    finally:
        cleanup_errors = []
        for proc in auxiliary_processes + probe_processes:
            try:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try: proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=5)
                        cleanup_errors.append("shared probe or native init required forced kill")
            except Exception as error:
                cleanup_errors.append("owned auxiliary cleanup: " + type(error).__name__)
        for peer in processes:
            try:
                if peer["process"].poll() is None and not stop_peer(peer):
                    cleanup_errors.append("native peer did not close cleanly")
            except Exception as error:
                cleanup_errors.append("owned native peer cleanup: " + type(error).__name__)
        owned = {p.pid for p in auxiliary_processes + probe_processes} | {p["process"].pid for p in processes}
        observations = []
        for group in sorted(owned):
            try:
                known_absent = group in absent_groups
                absent = observe_owned_group(group)
                observations.append({"pgid": group, "absent": absent, "historicalGroupReprobed": not known_absent})
                if not absent:
                    cleanup_errors.append("owned group remains; historical ID not signalled")
            except Exception as error:
                observations.append({"pgid": group, "absent": False, "error": type(error).__name__})
                cleanup_errors.append("owned group observation: " + type(error).__name__)
        for stream in streams:
            try: stream.close()
            except Exception as error:
                cleanup_errors.append("private log close: " + type(error).__name__)
        result["private_log_receipts"] = []
        try:
            log_paths = sorted(logdir.iterdir())
        except Exception as error:
            log_paths = []
            cleanup_errors.append("private log inventory: " + type(error).__name__)
        for p in log_paths:
            try:
                result["private_log_receipts"].append({"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)})
            except Exception as error:
                cleanup_errors.append("private log receipt: " + type(error).__name__)
        try:
            assert sha(args.nodeconf) == args.nodeconf_sha256, "nodeconf changed before final retention"
            assert {name:sha(prior_root/name/"config.yaml") for name in ("alice","bob")} == result["originalConfigHashes"]
            assert {name:sha(path) for name,path in network_configs.items()} == result["networkConfigHashes"]
        except Exception as error:
            cleanup_errors.append("final network config verification: " + type(error).__name__)
        result["cleanup"] = {"status": "PASS" if not cleanup_errors else "FAIL", "errors": cleanup_errors,
            "allOwnedProcessGroupsAbsent": all(row["absent"] for row in observations),
            "groupObservations": observations, "accountsDeleted": False}
        if cleanup_errors:
            result["result"] = "FAIL"
            result["all_scoped_checks_passed"] = False
        try:
            save()
        except Exception as error:
            result["result"] = "FAIL"
            result["all_scoped_checks_passed"] = False
            result["terminalReceiptWriteError"] = type(error).__name__
            print(json.dumps({"result": "FAIL", "terminalReceiptWriteError": type(error).__name__}), flush=True)
    print(json.dumps({k: result[k] for k in ("result", "all_scoped_checks_passed", "scope", "seconds", "minimum_free_bytes",
                                           "cloud_custody_accepted", "whole_space_migration_accepted")}, ensure_ascii=False))
    if result.get("failed_phase"):
        print(json.dumps({"failed_phase": result["failed_phase"], "error_type": result["error_type"], "error": result["error"]}))
    return 0 if result["result"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())

