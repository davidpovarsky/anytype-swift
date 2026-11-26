#!/usr/bin/env python3
"""Retain the qualified current Any CLI for full historical source preservation and cold reopen.

The external Swift test owns destination execution/readback. This controller
certifies process/source identity and lifecycle, not unsupported semantic usability.
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

BINARY_SHA = "8df7897ee6f45cdcef28c42fe025ad6f69062f15db779a660660cdc4016b00f7"
CONFIG_SHA = "6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060"
SOURCE_MANIFEST_SHA = "12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    binary = Path("/Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/any")
    source = Path("/Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/source")
    nodeconf = source / "internal/config/nodeconf-prod.yml"
    manifest_path = source.parent / "source-manifest.json"
    receipt = json.loads(manifest_path.read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(binary) == BINARY_SHA and sha(nodeconf) == CONFIG_SHA
    assert sha(manifest_path) == SOURCE_MANIFEST_SHA
    data = args.output / "private-account"
    logs = args.output / "private-logs"
    data.mkdir(mode=0o700); logs.mkdir(mode=0o700)
    config = data / "config.yaml"
    config.write_text("network:\n  nodeconfPath: " + str(nodeconf) +
                      "\nindex:\n  embedder: none\np2p:\n  enabled: false\n")
    started = time.monotonic()
    result = {"protocol": "pinkha-native-full-source-preservation-process-v1",
              "scope": "159 historical native heads and supported current Pages, 182 prepared operations, reversible native file, exact native links and a new cold-offline process",
              "whole_space_migration_accepted": False, "cloud_custody_accepted": False,
              "binarySHA256": BINARY_SHA, "nodeconfSHA256": CONFIG_SHA,
              "sourceManifestSHA256": SOURCE_MANIFEST_SHA, "network": "original shipped production nodeconf",
              "result": "RUNNING", "processes": [], "phases": [],
              "resourcePolicy": {"estimatedNewBytes": 512 * 1024**2,
                                 "emergencyFreeBytes": 2 * 1024**3,
                                 "reason": "Reused exact qualified 80.9MB current CLI; one fresh generated account and Space, 182 operations with a 1,634,696-byte reversible archive and 159 immutable source-head records. No Go compilation/dependency download. Additional 512MiB budget for native stores and logs; 2GiB floor."}}
    minimum_free = shutil.disk_usage(args.output).free
    assert minimum_free > 2 * 1024**3 + 512 * 1024**2
    process = None
    output = None
    initialization = None
    known_absent = set()
    phase = "source verification"
    def interrupted(signum, frame):
        raise RuntimeError("owned controller interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumFreeBytes"] = minimum_free
        pending = args.output / "controller-result.pending.json"
        pending.write_text(json.dumps(result, indent=2) + "\n")
        pending.replace(args.output / "controller-result.json")

    def verify_sources():
        assert not binary.is_symlink() and sha(binary) == BINARY_SHA
        assert not manifest_path.is_symlink() and sha(manifest_path) == SOURCE_MANIFEST_SHA
        expected_commits = {"any":"8fbd1e819fb132ac0e0a848d2ddf5c5714189b81", "sdk":"c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"}
        assert receipt["schema"] == "pinkha-t2-permission-native-source-v1"
        assert receipt["commits"] == expected_commits and len(receipt["files"]) == 1594
        build_path = source.parent / "BUILD.json"
        build_bytes = build_path.read_bytes()
        assert hashlib.sha256(build_bytes).hexdigest() == "3241e434144c399e52c1bd199f4b75a142d2ae62e8de82206721f65f993e94b1"
        build = json.loads(build_bytes)
        assert build["status"] == "PASS_BUILD_ONLY" and build["exitCode"] == 0 and build["ownedGroupAbsent"] is True
        assert build["sourceUnchanged"] is True and build["sourceFiles"] == 1594
        assert build["commits"] == expected_commits and build["sourceManifestSHA256"] == SOURCE_MANIFEST_SHA
        assert build["cwd"] == str(source) and build["binary"] == {"bytes":80951234,"path":str(binary),"sha256":BINARY_SHA}
        assert build["command"] == ["/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go","build","-p","2","-o",str(binary),"./cmd/any"]
        before = source.parent / "source-before.json"
        after = source.parent / "source-after.json"
        assert sha(before) == sha(after) == "7101539ffeb0d039afd5ba6eca4827f6389b2ce0a1311ee493331e2f6db31138"
        original = json.loads(before.read_bytes())
        assert set(original) == set(receipt["files"])
        found = set()
        for p in source.rglob("*"):
            assert not p.is_symlink(), "source symlink outside pinned regular-file closure"
            if p.is_file(): found.add(p.relative_to(source).as_posix())
        assert found == set(original), "complete native source closure changed"
        for relative,item in receipt["files"].items():
            path = source / relative
            assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
            assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(source.resolve())
            assert item["kind"] == "file" and original[relative] == {k:item[k] for k in ("bytes","kind","mode","sha256")}
            current = path.stat()
            assert current.st_size == item["bytes"] and current.st_mode & 0o777 == item["mode"]
            assert sha(path) == item["sha256"], "native source changed"
        assert sha(build_path) == hashlib.sha256(build_bytes).hexdigest()
        return {"commits":receipt["commits"],"files":len(receipt["files"]),"unchanged":True,
                "buildReceiptSHA256":hashlib.sha256(build_bytes).hexdigest(),
                "sourceInventorySHA256":sha(before)}

    def guard():
        nonlocal minimum_free
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        assert minimum_free >= 2 * 1024**3, "runtime disk emergency"
        assert time.monotonic() - started < 3900, "bounded native controller timeout"
        assert not (args.output / "abort").exists(), "external qualification stopped"

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

    def absent(group):
        if group in known_absent:
            return True
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            known_absent.add(group)
            return True
        return False

    def finish_owned(child, timeout):
        # Never signal an identifier after absence has already been proved.
        if child.pid not in known_absent and child.poll() is None:
            if not absent(child.pid):
                os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if not absent(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
                raise RuntimeError("owned native process required forced termination")
        child.wait(timeout=5)
        assert absent(child.pid), "owned native process group remains active"

    def stop():
        nonlocal process, output
        if process is None:
            return
        child = process
        finish_owned(child, 20)
        result["processes"][-1]["exitCode"] = child.returncode
        result["processes"][-1]["groupPositivelyAbsent"] = child.pid in known_absent
        output.close()
        stopped = child.returncode == 0
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
            initialization = subprocess.Popen([str(binary), "init", "--config", str(config), "--data-dir", str(data)],
                env=env, stdout=init_log, stderr=subprocess.STDOUT, start_new_session=True)
            result["initializationPID"] = initialization.pid
            initialization.wait(timeout=60)
            assert absent(initialization.pid), "account initialization group remains active"
        assert initialization.returncode == 0, "native init failed; private log retained"
        result["initializationExitCode"] = initialization.returncode
        result["initializationGroupPositivelyAbsent"] = True
        start("initial-native")
        account = request("GET", "/v1/account")[1]["id"]
        code, space = request("POST", "/v1/spaces", {"name": "Pinkha C historical source preservation"}, timeout=60)
        assert code == 201
        space_id = space["id"]
        runtime = {"baseURL": base, "accountID": account, "spaceID": space_id, "binarySHA256": BINARY_SHA,
                   "sourceManifestSHA256": SOURCE_MANIFEST_SHA,
                   "processID": process.pid, "phase": "execute", "wholeSpaceMigration": False}
        pending_runtime = args.output / "runtime.pending.json"
        pending_runtime.write_text(json.dumps(runtime, indent=2) + "\n")
        pending_runtime.replace(args.output / "runtime.json")
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
            checked = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), "/opt/homebrew/bin/python3.12", "-c", code],
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
        runtime.update(phase="cold-offline", processID=process.pid, outboundDeniedByOS=True, networkPeerCount=0)
        pending_runtime = args.output / "runtime.pending.json"
        pending_runtime.write_text(json.dumps(runtime, indent=2) + "\n")
        pending_runtime.replace(args.output / "runtime.json")
        phase = "external cold full preservation, file restoration and signed-history readback"
        await_signal("finish")
        stop()
        result["sourcesAfter"] = verify_sources()
        result["result"] = "PROCESS_LIFECYCLE_PASS"
    except Exception as error:
        result.update(result="FAIL", failedPhase=phase, errorType=type(error).__name__, error=str(error))
    finally:
        if initialization is not None:
            try: finish_owned(initialization, 10)
            except Exception as error:
                result["initializationCleanupFailure"] = type(error).__name__
                result["result"] = "FAIL"
        if process is not None:
            try: stop()
            except Exception as error:
                result["cleanupFailure"] = type(error).__name__
                result["result"] = "FAIL"
        try:
            result["privateLogReceipts"] = [
                {"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
                for p in logs.iterdir() if p.is_file()
            ]
        except Exception as error:
            result["privateLogReceiptFailure"] = type(error).__name__
            result["result"] = "FAIL"
        save()
    print(json.dumps({k: result[k] for k in ("result", "scope", "seconds", "minimumFreeBytes",
                                             "whole_space_migration_accepted", "cloud_custody_accepted")}))
    return 0 if result["result"] == "PROCESS_LIFECYCLE_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
