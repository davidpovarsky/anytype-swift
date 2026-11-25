#!/usr/bin/env python3
"""Retain a genuine Any CLI and restart it in a new OS-offline process.

The external Swift test owns destination execution/readback. This controller
certifies process/source identity and lifecycle, not whole-space migration.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import urllib.request

BINARY_SHA = "bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49"
CONFIG_SHA = "08b54369643aede09a12ce2710abb0a11375f265bb85c5c3363f0526a4b766f9"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    binary = Path("/Users/m1/builds/pinkha-c-native-file-peer-20261125/any548")
    source = Path("/Users/m1/builds/pinkha-t2-network-20261125/source-any548-sdk195")
    nodeconf = source / "staging.yml"
    receipt = json.loads((source.parent / "source-receipt.json").read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(binary) == BINARY_SHA and sha(nodeconf) == CONFIG_SHA
    data = args.output / "private-account"
    logs = args.output / "private-logs"
    data.mkdir(mode=0o700); logs.mkdir(mode=0o700)
    config = data / "config.yaml"
    config.write_text("network:\n  nodeconfPath: " + str(nodeconf) +
                      "\nindex:\n  embedder: none\np2p:\n  enabled: false\n")
    started = time.monotonic()
    result = {"scope": "native process/source and offline-reopen control for destination component input",
              "whole_space_migration_accepted": False, "cloud_custody_accepted": False,
              "binarySHA256": BINARY_SHA, "nodeconfSHA256": CONFIG_SHA,
              "result": "RUNNING", "processes": [], "phases": [],
              "resourcePolicy": {"estimatedNewBytes": 256 * 1024**2,
                                 "emergencyFreeBytes": 2 * 1024**3,
                                 "reason": "Reused exact binary, one native fixture account, seventeen prepared operations, <9KiB source payload; no compilation or dependency download."}}
    minimum_free = shutil.disk_usage(args.output).free
    assert minimum_free > 2 * 1024**3 + 256 * 1024**2
    process = None
    output = None
    phase = "source verification"

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumFreeBytes"] = minimum_free
        (args.output / "controller-result.json").write_text(json.dumps(result, indent=2) + "\n")

    def verify_sources():
        observations = []
        for entry in receipt["source"]:
            root = source if entry["commit"] == "548f5cd0430a723bd26ea724daeb99991f68b9c9" else source / ".runtime-artifacts/sdk-source"
            for item in entry["files"]:
                assert sha(root / item["path"]) == item["sha256"], "native source changed"
            observations.append({"commit": entry["commit"], "files": len(entry["files"]), "unchanged": True})
        return observations

    def guard():
        nonlocal minimum_free
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        assert minimum_free >= 2 * 1024**3, "runtime disk emergency"
        assert time.monotonic() - started < 1800, "bounded native controller timeout"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = "http://127.0.0.1:" + str(port)

    def request(method, path, body=None, timeout=15):
        headers = {}
        if body is not None:
            body = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(base + path, method=method, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as reply:
            raw = reply.read(1 << 20)
            return reply.status, json.loads(raw) if raw else None

    def stop():
        nonlocal process, output
        if process is None:
            return
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                result["processes"][-1]["forcedKill"] = True
        result["processes"][-1]["exitCode"] = process.returncode
        output.close()
        stopped = process.returncode == 0 and not result["processes"][-1]["forcedKill"]
        process = None
        save()
        assert stopped, "native process did not exit cleanly"

    def start(name, profile=None):
        nonlocal process, output
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        env.update(ANY_DATA_DIR=str(data), GOMAXPROCS="2", GOMEMLIMIT="2GiB")
        command = [str(binary), "run", "--config", str(config), "--data-dir", str(data),
                   "--addr", "127.0.0.1:" + str(port)]
        if profile:
            command = ["/usr/bin/sandbox-exec", "-f", str(profile)] + command
        output = (logs / (name + ".log")).open("wb")
        process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        result["processes"].append({"name": name, "pid": process.pid, "offline": bool(profile), "forcedKill": False})
        deadline = time.monotonic() + 60
        while True:
            guard()
            assert process.poll() is None, "native process ended before health"
            try:
                if request("GET", "/v1/health", timeout=1)[0] == 200:
                    break
            except OSError:
                pass
            assert time.monotonic() < deadline, "native readiness timeout"
            time.sleep(0.25)
        save()

    def await_signal(name):
        path = args.output / name
        while not path.exists():
            guard()
            assert process is not None and process.poll() is None, "native process stopped unexpectedly"
            time.sleep(0.5)
        result["phases"].append({"received": name, "seconds": round(time.monotonic() - started, 3)})
        save()

    try:
        result["sourcesBefore"] = verify_sources()
        phase = "new generated native account"
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        env["ANY_DATA_DIR"] = str(data)
        with (logs / "account-init.log").open("wb") as init_log:
            initialized = subprocess.run([str(binary), "init", "--config", str(config), "--data-dir", str(data)],
                                         env=env, stdout=init_log, stderr=subprocess.STDOUT, timeout=60)
        assert initialized.returncode == 0, "native init failed; private log retained"
        start("initial-native")
        account = request("GET", "/v1/account")[1]["id"]
        code, space = request("POST", "/v1/spaces", {"name": "Pinkha C destination content qualification"})
        assert code == 201
        space_id = space["id"]
        runtime = {"baseURL": base, "accountID": account, "spaceID": space_id, "binarySHA256": BINARY_SHA,
                   "processID": process.pid, "phase": "initial", "wholeSpaceMigration": False}
        (args.output / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
        result["accountID"] = account; result["spaceID"] = space_id
        phase = "external native execute/readback"
        await_signal("execute-complete")

        phase = "native process exit"
        stop()
        profile = args.output / "offline.sb"
        profile.write_text("(version 1)\n(allow default)\n(deny network-outbound)\n")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0)); listener.listen()
            probe_port = listener.getsockname()[1]
            socket.create_connection(("127.0.0.1", probe_port), timeout=2).close()
            code = (
                "import socket,json,errno\nresult={}\n"
                "try:\n socket.create_connection(('127.0.0.1'," + str(probe_port) + "),timeout=2);result['tcpDenied']=False\n"
                "except OSError as e:result['tcpDenied']=e.errno in (errno.EPERM,errno.EACCES);result['tcpErrno']=e.errno\n"
                "s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\n"
                "try:\n s.sendto(b'private-offline-probe',('127.0.0.1'," + str(probe_port) + "));result['udpDenied']=False\n"
                "except OSError as e:result['udpDenied']=e.errno in (errno.EPERM,errno.EACCES);result['udpErrno']=e.errno\n"
                "finally:s.close()\nprint(json.dumps(result))\n"
            )
            checked = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), "/usr/bin/python3", "-c", code],
                                     capture_output=True, text=True, timeout=10)
            assert checked.returncode == 0
            controls = json.loads(checked.stdout)
            assert controls["tcpDenied"] and controls["udpDenied"]
        result["offlinePolicy"] = {"sha256": sha(profile), "baselineListenerReachable": True, "controls": controls}
        phase = "fresh native process under OS outbound denial"
        start("cold-offline-native", profile)
        assert request("GET", "/v1/account")[1]["id"] == account
        sync = request("GET", "/v1/spaces/" + space_id + "/sync-status")[1]
        result["coldSyncStatus"] = {k: sync.get(k) for k in ("state", "networkPeers", "localPeers", "globalPeers", "p2p")}
        assert sync["networkPeers"] == 0 and sync["localPeers"] == 0 and sync["globalPeers"] == 0
        runtime.update(phase="cold-offline", processID=process.pid)
        (args.output / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n")
        phase = "external cold content readback and refusal control"
        await_signal("finish")
        stop()
        result["sourcesAfter"] = verify_sources()
        result["result"] = "PROCESS_LIFECYCLE_PASS"
    except Exception as error:
        result.update(result="FAIL", failedPhase=phase, errorType=type(error).__name__, error=str(error))
    finally:
        if process is not None:
            try: stop()
            except Exception as error: result["cleanupFailure"] = type(error).__name__
        result["privateLogReceipts"] = [
            {"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in logs.iterdir() if p.is_file()
        ]
        save()
    print(json.dumps({k: result[k] for k in ("result", "scope", "seconds", "minimumFreeBytes",
                                             "whole_space_migration_accepted", "cloud_custody_accepted")}))
    return 0 if result["result"] == "PROCESS_LIFECYCLE_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
