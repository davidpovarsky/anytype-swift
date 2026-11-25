#!/usr/bin/env python3
"""Real independent Any CLI file transfer and cold offline read.

Uses only the original HTTP/native APIs and genuine mDNS discovery. Every
fixture is retained outside Go TempDir. Cloud custody and whole-space migration
are explicitly outside this proof; an unsigned file must stay unsigned here.
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
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--nodeconf", required=True, type=Path)
    parser.add_argument("--nodeconf-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--source-receipt", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    logdir = args.output / "private-logs"
    logdir.mkdir(mode=0o700)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(args.binary) == args.binary_sha256, "binary identity changed"
    assert sha(args.nodeconf) == args.nodeconf_sha256, "network configuration changed"
    assert "fileV2" not in args.nodeconf.read_text(), "this proof needs no fileV2 source"
    manifest = json.loads(args.source_receipt.read_text())

    def verify_sources():
        result = []
        for item in manifest["source"]:
            root = args.source_root if item["commit"] == "548f5cd0430a723bd26ea724daeb99991f68b9c9" else args.source_root / ".runtime-artifacts/sdk-source"
            for entry in item["files"]:
                assert sha(root / entry["path"]) == entry["sha256"], "source file identity changed"
            result.append({"commit": item["commit"], "files": len(item["files"]), "unchanged": True})
        return result

    result = {
        "scope": "native non-inline file bytes across distinct accounts/processes and cold destination read under OS-denied outbound networking",
        "binary_sha256": args.binary_sha256,
        "nodeconf_sha256": args.nodeconf_sha256,
        "sources_before": verify_sources(),
        "cloud_custody_accepted": False,
        "whole_space_migration_accepted": False,
        "fixtures_retained": True,
        "result": "RUNNING",
        "phases": [],
        "files": [],
        "processes": [],
        "resource_policy": {
            "estimated_new_disk_bytes": 256 * 1024**2,
            "emergency_free_bytes": 2 * 1024**3,
            "rationale": "No compile/download; 11MiB+8KiB deterministic payloads, two complete encrypted native stores plus indexes/logs. A256MiB phase allowance and active-work2GiB emergency floor bound the small runtime phase."
        }
    }
    started = time.monotonic()
    processes = []
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

    def start_peer(name, data_dir, initialize=False, sandbox_profile=None):
        data_dir.mkdir(mode=0o700, exist_ok=True)
        cfg = data_dir / "config.yaml"
        if initialize:
            cfg.write_text("network:\n  nodeconfPath: " + str(args.nodeconf) +
                           "\nindex:\n  embedder: none\np2p:\n  enabled: true\n  localDiscovery: true\n  serviceName: _pinkhafile._tcp\n  global:\n    enabled: false\n")
        assert cfg.is_file()
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        env.update({"ANY_DATA_DIR": str(data_dir), "GOMAXPROCS": "2", "GOMEMLIMIT": "2GiB"})
        if initialize:
            init_path = logdir / (name + "-init.log")
            with init_path.open("wb") as log:
                initialized = subprocess.run([str(args.binary), "init", "--config", str(cfg), "--data-dir", str(data_dir)],
                    env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60)
            assert initialized.returncode == 0, name + " native account init failed (private log retained)"
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
        save()
        return not forced and proc.returncode == 0

    def public_peer_status(peer, space_id):
        value = json_request(peer, "GET", "/v1/debug/p2p")
        return {
            "peerId": value.get("peerId"),
            "matching_connected_peers": [
                {"peerId": p.get("peerId"), "connected": p.get("connected"), "sources": p.get("sources"), "shared_space": True}
                for p in value.get("peers", []) if p.get("connected") and "lan" in (p.get("sources") or []) and space_id in (p.get("spaceIds") or [])
            ]
        }

    try:
        phase = "independent native accounts"
        alice = start_peer("alice", args.output / "alice", initialize=True)
        bob = start_peer("bob", args.output / "bob", initialize=True)
        alice_id = json_request(alice, "GET", "/v1/account")["id"]
        bob_id = json_request(bob, "GET", "/v1/account")["id"]
        assert alice_id and bob_id and alice_id != bob_id, "accounts must differ"
        result["accounts"] = {"alice": alice_id, "bob": bob_id}
        assert alice["process"].pid != bob["process"].pid
        mark("distinct native accounts and processes")

        phase = "real native invite and reader acceptance"
        sp = json_request(alice, "POST", "/v1/spaces", {"name": "Pinkha C independent file comparison"}, 201)
        space_id = sp["id"]
        obj = json_request(alice, "POST", "/v1/spaces/" + space_id + "/objects", {"type": "page"}, 201)
        object_id = obj["objectId"]
        result["space_id"] = space_id
        result["object_id"] = object_id
        minted = json_request(alice, "POST", "/v1/spaces/" + space_id + "/invites", expected=201)
        joined = json_request(bob, "POST", "/v1/spaces/join", {"inviteToken": minted["inviteToken"]}, 202)
        del minted
        assert joined["id"] == space_id and joined["status"] == "joining"
        def pending():
            response = json_request(alice, "GET", "/v1/spaces/" + space_id + "/members/requests")
            return (response.get("requests") or [None])[0]
        join_request = until(90, pending, "owner never saw native request")
        json_request(alice, "POST", "/v1/spaces/" + space_id + "/acl/accept",
                     {"requestRecordId": join_request["recordId"], "permission": "reader"}, 204)
        def accepted():
            status, raw, _ = request(bob, "GET", "/v1/spaces/" + space_id + "/members/me")
            if status != 200: return False
            member = json.loads(raw)
            return member if member.get("status") == "active" else False
        member = until(90, accepted, "reader never became active")
        assert member["identity"] == bob_id and member["permission"] == "reader", "actual recipient identity/role mismatch"
        result["recipient_role"] = member["permission"]
        mark("native invite accepted", recipient_status=member["status"])

        phase = "genuine local discovery"
        def discovered():
            a, b = public_peer_status(alice, space_id), public_peer_status(bob, space_id)
            if a["matching_connected_peers"] and b["matching_connected_peers"]:
                return a, b
            return False
        pa, pb = until(90, discovered, "genuine mDNS shared-space discovery missing")
        assert pa["peerId"] and pb["peerId"] and pa["peerId"] != pb["peerId"]
        assert any(p["peerId"] == pb["peerId"] for p in pa["matching_connected_peers"])
        assert any(p["peerId"] == pa["peerId"] for p in pb["matching_connected_peers"])
        result["discovery"] = {"alice": pa, "bob": pb, "driver": "original native mDNS", "fake_driver": False}
        mark("genuine mDNS connected")

        phase = "non-inline encrypted files across independent peers"
        prefix = "/v1/spaces/" + space_id + "/files/"
        for index, size in enumerate((8192, 1024**2, 10 * 1024**2)):
            content = hashlib.shake_256(("Pinkha-C-file-peer-" + str(index)).encode()).digest(size)
            expected_hash = hashlib.sha256(content).hexdigest()
            status, body, _ = request(alice, "POST", "/v1/spaces/" + space_id + "/objects/" + object_id +
                                     "/files?name=fixture-" + str(size) + ".bin", content,
                                     {"Content-Type": "application/octet-stream"}, timeout=60)
            assert status == 201, "original native attach failed"
            attached = json.loads(body)
            assert attached["size"] == size and attached["objectId"] == object_id
            assert attached["inline"] is False and attached["durable"] is False and attached.get("rootCid")
            file_id = attached["fileId"]
            def row_arrived():
                status, raw, _ = request(bob, "GET", prefix + file_id)
                return json.loads(raw) if status == 200 else False
            before = until(90, row_arrived, "recipient payload row missing")
            assert before["rootCid"] == attached["rootCid"] and before["objectId"] == object_id
            assert before["size"] == size and before["cached"] is False, "recipient must have no bytes before first fetch"
            assert before["inline"] is False and before["durable"] is False
            src_status, src_bytes, _ = request(alice, "GET", prefix + file_id + "/content", timeout=60)
            assert src_status == 200 and hashlib.sha256(src_bytes).hexdigest() == expected_hash
            del src_bytes
            fetched_at = time.monotonic()
            code, destination_bytes, _ = request(bob, "GET", prefix + file_id + "/content", timeout=60)
            assert code == 200 and len(destination_bytes) == size
            assert hashlib.sha256(destination_bytes).hexdigest() == expected_hash, "native destination content differs"
            del destination_bytes
            after = json_request(bob, "GET", prefix + file_id)
            assert after["cached"] is True and after["durable"] is False
            offset = min(200000, size // 3)
            length = min(32768, size - offset)
            code, part, heads = request(bob, "GET", prefix + file_id + "/content",
                                       headers={"Range": "bytes=" + str(offset) + "-" + str(offset + length - 1)})
            assert code == 206 and part == content[offset:offset + length], "native range bytes differ"
            file_result = {
                "file_id": file_id, "object_id": object_id, "root_cid": attached["rootCid"],
                "plaintext_bytes": size, "source_sha256": expected_hash, "destination_sha256": expected_hash,
                "recipient_cached_before": False, "recipient_cached_after": True,
                "inline": False, "durable": False, "range_offset": offset, "range_bytes": length,
                "range_equal": True, "download_seconds": round(time.monotonic() - fetched_at, 3),
                "source_status": json_request(alice, "GET", prefix + file_id + "/status"),
                "recipient_status": json_request(bob, "GET", prefix + file_id + "/status")
            }
            result["files"].append(file_result)
            mark("byte equality and native range", size=size, sha256=expected_hash)
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
            probe = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), "/usr/bin/python3", "-c", probe_code],
                                   capture_output=True, text=True, timeout=10)
            assert probe.returncode == 0, "sandbox outbound control did not run"
            checked = json.loads(probe.stdout)
            assert checked["tcp_connect_denied"] and checked["udp_send_denied"], "OS outbound sandbox control failed"
        result["offline_policy"] = {"profile_sha256": sha(profile), "probe": checked, "baseline_listener_reachable": True}
        mark("OS denied TCP connects and UDP sends")

        phase = "fresh recipient native process offline read"
        cold = start_peer("bob-cold-offline", args.output / "bob", sandbox_profile=profile)
        assert cold["process"].pid not in (alice["process"].pid, bob["process"].pid)
        assert json_request(cold, "GET", "/v1/account")["id"] == bob_id
        state = json_request(cold, "GET", "/v1/spaces/" + space_id + "/sync-status")
        result["cold_sync_status"] = {key: state.get(key) for key in ("networkPeers", "localPeers", "globalPeers", "p2p", "state")}
        assert state["networkPeers"] == 0 and state["localPeers"] == 0 and state["globalPeers"] == 0
        for record in result["files"]:
            info = json_request(cold, "GET", prefix + record["file_id"])
            assert info["rootCid"] == record["root_cid"] and info["objectId"] == object_id
            assert info["size"] == record["plaintext_bytes"] and info["cached"] is True
            assert info["inline"] is False and info["durable"] is False
            code, data, _ = request(cold, "GET", prefix + record["file_id"] + "/content", timeout=60)
            assert code == 200 and len(data) == record["plaintext_bytes"]
            digest = hashlib.sha256(data).hexdigest()
            assert digest == record["source_sha256"], "cold offline plaintext differs"
            record["cold_offline_sha256"] = digest
            record["cold_offline_equal"] = True
            del data
        assert stop_peer(cold), "cold native process did not close cleanly"
        mark("fresh offline native process retained all original bytes")
        result["sources_after"] = verify_sources()
        result["result"] = "PASS"
        result["all_scoped_checks_passed"] = True
    except Exception as error:
        result["result"] = "FAIL"
        result["failed_phase"] = phase
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
        result["all_scoped_checks_passed"] = False
    finally:
        for peer in processes:
            if peer["process"].poll() is None:
                stop_peer(peer)
        for stream in streams:
            stream.close()
        result["private_log_receipts"] = [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted(logdir.iterdir()) if p.is_file()
        ]
        save()
    print(json.dumps({k: result[k] for k in ("result", "all_scoped_checks_passed", "scope", "seconds", "minimum_free_bytes",
                                           "cloud_custody_accepted", "whole_space_migration_accepted")}, ensure_ascii=False))
    if result.get("failed_phase"):
        print(json.dumps({"failed_phase": result["failed_phase"], "error_type": result["error_type"], "error": result["error"]}))
    return 0 if result["result"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
