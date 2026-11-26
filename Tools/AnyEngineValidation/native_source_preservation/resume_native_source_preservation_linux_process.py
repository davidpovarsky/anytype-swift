#!/usr/bin/env python3
"""Retain the qualified current Any CLI for full historical source preservation and cold reopen.

The external Swift test owns destination execution/readback. This controller
certifies process/source identity and lifecycle, not unsupported semantic usability.
"""
import argparse
import io
import sys
import tarfile
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import socket
import subprocess
import time
import urllib.request

BINARY_SHA = "1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"
MAC_BINARY_SHA = "8df7897ee6f45cdcef28c42fe025ad6f69062f15db779a660660cdc4016b00f7"
OFFLINE_HELPER_SHA = "6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1"
CONFIG_SHA = "6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060"
SOURCE_MANIFEST_SHA = "12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"

CUSTODY = Path("/mnt/development/projects/evidence/migration-final-20261125/full-source-preservation/native-resume1-custody")
PLAN_SHA = "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930"
def read_pinned(path, expected):
    assert path.resolve() == path and not path.is_symlink() and path.is_file()
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    identity = lambda s: (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns)
    assert before.st_nlink == 1 and identity(before) == identity(after)
    assert hashlib.sha256(raw).hexdigest() == expected
    return raw

def retained_inventory(root):
    rows, identities = {}, {}
    assert root.resolve() == root and not root.is_symlink() and root.is_dir()
    for path in [root] + sorted(root.rglob("*")):
        before = path.lstat()
        name = "." if path == root else path.relative_to(root).as_posix()
        assert path.resolve() == path and not path.is_symlink()
        identity = lambda s: [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns]
        if stat.S_ISREG(before.st_mode):
            assert before.st_nlink == 1 and before.st_size <= 32*1024**2
            raw = path.read_bytes()
            rows[name] = {"kind":"file","bytes":len(raw),"mode":stat.S_IMODE(before.st_mode),
                          "sha256":hashlib.sha256(raw).hexdigest()}
        else:
            assert stat.S_ISDIR(before.st_mode)
            rows[name] = {"kind":"directory","mode":stat.S_IMODE(before.st_mode)}
        assert identity(before) == identity(path.lstat())
        identities[name] = identity(before)
    return rows, identities

def restore_closed_archive(archive, digest, expected, destination):
    raw = read_pinned(archive, digest)
    assert len(raw) <= 32*1024**2
    assert destination.parent.resolve() == destination.parent and not destination.exists()
    destination.mkdir(mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as source:
        members = source.getmembers()
        assert len(members) == len(expected) and len({m.name for m in members}) == len(members)
        assert {m.name for m in members} == set(expected)
        for member in members:
            name = member.name
            assert name == "." or (not Path(name).is_absolute() and
                all(c not in ("", ".", "..") for c in name.split("/")) and "\\" not in name)
            row = expected[name]
            path = destination if name == "." else destination / name
            assert member.mode == row["mode"] and not member.issym() and not member.islnk()
            if row["kind"] == "directory":
                assert member.isdir()
                path.mkdir(mode=row["mode"], exist_ok=True)
            else:
                assert row["kind"] == "file" and member.isfile() and member.size == row["bytes"]
                assert 0 <= member.size <= 32*1024**2
                content = source.extractfile(member).read(member.size + 1)
                assert len(content) == member.size and hashlib.sha256(content).hexdigest() == row["sha256"]
                assert path.parent.is_dir() and not path.exists()
                with path.open("xb") as stream: stream.write(content)
            os.chmod(path, row["mode"])
    assert retained_inventory(destination)[0] == expected
    assert read_pinned(archive, digest) == raw

def admit_retained_account(destination):
    receipt_raw = read_pinned(CUSTODY / "receipt.json",
        "8645070719620e263ab99cde5fc7232527b1a3caa20d1bafb5e759ed5e894d08")
    receipt = json.loads(receipt_raw)
    assert receipt["status"] == "PASS_ORIGINAL_FAILED_NATIVE_ACCOUNT_CUSTODY"
    assert receipt["priorResult"] == "FAIL" and receipt["accountOpened"] is False
    assert receipt["runtimeCalls"] == 0 and receipt["historicalGroupsProbed"] == 0
    offhost_raw = read_pinned(CUSTODY / "offhost-receipt.json",
        "ab149dc3ba2a64e774ac75bc6dcc362ec661e20e3b78c1f5725bf67538196b72")
    offhost = json.loads(offhost_raw)
    assert offhost["status"] == "PASS_OFFHOST_LATEST_FAILED_NATIVE_AND_ORACLE_JOURNAL"
    assert offhost["originalOutcome"] == "FAIL" and offhost["runtimeCalls"] == 0
    expected = json.loads(read_pinned(CUSTODY / "source-inventory.json",
        "0834b5d34c42a280a5b63deaafbfbb6c188e72f92f615dd0cd8f79c97f859b53"))
    original = destination.parent / "retained-mac-original"
    restore_closed_archive(CUSTODY / "original-native-account-and-evidence.tar.gz",
        "9824faee754cc8a2e81de7b4bf0432c116ed983816eb0f6523aa670fba3dea2d", expected, original)
    original_rows, original_ids = retained_inventory(original)
    prior_raw = read_pinned(original / "controller-result.json",
        "98367e76d7ea0f8ce8988d7e1443b9e3b8caaeb07dbd880e2cb04b3be10ce85d")
    prior = json.loads(prior_raw)
    assert prior["result"] == "FAIL" and prior["error"] == "runtime disk emergency"
    assert prior["minimumFreeBytes"] == 2127994880 and prior["phases"] == []
    assert prior["processes"] == [{"name":"resumed-native","pid":70048,"offline":False,
        "forcedKill":False,"exitCode":0,"groupPositivelyAbsent":True}]
    assert prior["binarySHA256"] == MAC_BINARY_SHA and prior["sourceManifestSHA256"] == SOURCE_MANIFEST_SHA
    assert prior["priorCustody"]["priorControllerReceiptSHA256"] == "01ae912fb7a53caef1b1105f813917ab1477dc2f910c22b2bcc8c108ec450386"
    assert prior["priorCustody"]["sameNativeAccount"] is True
    assert prior["priorCustody"]["accountInitialized"] is False and prior["priorCustody"]["spaceCreated"] is False
    account = json.loads(read_pinned(CUSTODY / "account-inventory.json",
        "cb088c0944d621a0d415dea1e9807ffce4260f18ab371760274fff962c48f35c"))
    source = original / "private-account"
    before, identities = retained_inventory(source)
    assert before == account
    assert destination.parent.resolve() == destination.parent and not destination.exists()
    shutil.copytree(source, destination, copy_function=shutil.copy2)
    assert retained_inventory(destination)[0] == account
    assert retained_inventory(source) == (before, identities)
    assert retained_inventory(original) == (original_rows, original_ids)
    return prior, {"priorResult":"FAIL","priorControllerReceiptSHA256":hashlib.sha256(prior_raw).hexdigest(),
        "custodyReceiptSHA256":hashlib.sha256(receipt_raw).hexdigest(),
        "offhostReceiptSHA256":hashlib.sha256(offhost_raw).hexdigest(),
        "sameNativeAccount":True,"accountInitialized":False,"spaceCreated":False,
        "historicalGroupsProbed":0,"originalAccountUnchanged":True,
        "copiedAccountBytesAndModesEqual":True,"originalAccountEntries":len(account),
        "interruptedPlanSHA256":PLAN_SHA,"platformChange":"darwin-arm64 to linux-arm64",
        "storageCompatibility":"pending actual native reopen and identity/owner readback"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    binary = Path("/var/lib/pinkha-root-t2-linux-20261126/build1/current/any")
    source = Path("/var/lib/pinkha-root-t2-linux-20261126/build1/current/source")
    nodeconf = source / "internal/config/nodeconf-prod.yml"
    manifest_path = source.parent / "source-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == SOURCE_MANIFEST_SHA
    receipt = json.loads(manifest_bytes)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(binary) == BINARY_SHA and sha(nodeconf) == CONFIG_SHA
    assert sha(manifest_path) == SOURCE_MANIFEST_SHA
    data = args.output / "private-account"
    logs = args.output / "private-logs"
    logs.mkdir(mode=0o700)
    config = args.output / "run-config.yaml"
    offline_helper = Path(__file__).resolve().with_name("linux_outbound_denial.py")
    assert hashlib.sha256(offline_helper.read_bytes()).hexdigest() == OFFLINE_HELPER_SHA
    started = time.monotonic()
    result = {"protocol": "pinkha-native-full-source-preservation-linux-resume-process-v1",
              "scope": "159 historical native heads and supported current Pages, 182 prepared operations, reversible native file, exact native links and a new cold-offline process",
              "whole_space_migration_accepted": False, "cloud_custody_accepted": False,
              "binarySHA256": BINARY_SHA, "nodeconfSHA256": CONFIG_SHA,
              "sourceManifestSHA256": SOURCE_MANIFEST_SHA, "network": "original shipped production nodeconf",
              "result": "RUNNING", "processes": [], "phases": [],
              "resourcePolicy": {"estimatedNewBytes": 512 * 1024**2,
                                 "emergencyFreeBytes": 2 * 1024**3,
                                 "reason": "Reused exact qualified 78.1MB Linux CLI from identical Any/SDK source; the copied exact interrupted account and its existing Space, 182 operations with a 1,634,696-byte reversible archive and 159 immutable source-head records. No Go compilation/dependency download. Additional 512MiB budget for native stores and logs; 2GiB floor."}}
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
        assert not offline_helper.is_symlink() and sha(offline_helper) == OFFLINE_HELPER_SHA
        assert nodeconf.read_bytes() and sha(nodeconf) == CONFIG_SHA
        current_manifest_bytes = manifest_path.read_bytes()
        assert not manifest_path.is_symlink() and current_manifest_bytes == manifest_bytes
        assert hashlib.sha256(current_manifest_bytes).hexdigest() == SOURCE_MANIFEST_SHA
        expected_commits = {"any":"8fbd1e819fb132ac0e0a848d2ddf5c5714189b81", "sdk":"c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"}
        assert receipt["schema"] == "pinkha-t2-permission-native-source-v1"
        assert receipt["commits"] == expected_commits and len(receipt["files"]) == 1594
        build_path = source.parent / "BUILD.json"
        build_bytes = build_path.read_bytes()
        assert hashlib.sha256(build_bytes).hexdigest() == "6d0f00da205846575bfd49e3fba8121aa1570a940ea3e13cc571aa4b4734e2f0"
        build = json.loads(build_bytes)
        assert build["status"] == "PASS_BUILD_ONLY" and build["exitCode"] == 0 and build["ownedGroupAbsent"] is True
        assert build["sourceUnchanged"] is True and build["sourceFiles"] == 1594
        assert build["commits"] == expected_commits and build["sourceManifestSHA256"] == SOURCE_MANIFEST_SHA
        assert build["cwd"] == str(source) and build["binary"] == {"bytes":78072016,"path":str(binary),"sha256":BINARY_SHA}
        assert build["command"] == ["/usr/local/bin/go","build","-p","2","-o",str(binary),"./cmd/any"]
        before = source.parent / "source-before.json"
        after = source.parent / "source-after.json"
        before_bytes = before.read_bytes(); after_bytes = after.read_bytes()
        assert not before.is_symlink() and not after.is_symlink()
        assert before_bytes == after_bytes
        assert hashlib.sha256(before_bytes).hexdigest() == "7101539ffeb0d039afd5ba6eca4827f6389b2ce0a1311ee493331e2f6db31138"
        original = json.loads(before_bytes)
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
        assert manifest_path.read_bytes() == manifest_bytes
        assert before.read_bytes() == before_bytes and after.read_bytes() == after_bytes
        return {"commits":receipt["commits"],"files":len(receipt["files"]),"unchanged":True,
                "buildReceiptSHA256":hashlib.sha256(build_bytes).hexdigest(),
                "sourceInventorySHA256":sha(before)}

    def guard():
        nonlocal minimum_free
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        assert minimum_free >= 2 * 1024**3, "runtime disk emergency"
        assert time.monotonic() - started < 3300, "bounded native controller timeout"
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
            assert profile == offline_helper and sha(profile) == OFFLINE_HELPER_SHA
            command = [sys.executable, "-B", str(profile), "--exec"] + command
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
        phase = "retained interrupted account admission"
        prior, custody = admit_retained_account(data)
        result["priorCustody"] = custody
        original_config = data / "config.yaml"
        old_nodeconf = "/Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/source/internal/config/nodeconf-prod.yml"
        expected_original_config = ("network:\n  nodeconfPath: " + old_nodeconf +
            "\nindex:\n  embedder: none\np2p:\n  enabled: false\n")
        assert original_config.read_text() == expected_original_config
        new_config = expected_original_config.replace(old_nodeconf, str(nodeconf))
        assert new_config.replace(str(nodeconf), old_nodeconf) == expected_original_config
        config.write_text(new_config)
        result["externalConfigRelocation"] = {"originalConfigSHA256": sha(original_config),
            "runtimeConfigSHA256":sha(config),"sameNodeconfSHA256":CONFIG_SHA,
            "originalAccountConfigChanged":False,"change":"only immutable nodeconf filesystem locator"}
        start("resumed-native")
        account = request("GET", "/v1/account")[1]["id"]
        space_id = prior["spaceID"]
        assert account == prior["accountID"]
        member = request("GET", "/v1/spaces/" + space_id + "/members/me")[1]
        assert member["identity"] == account and member["status"] == "active" and member["permission"] == "owner"
        runtime = {"baseURL": base, "accountID": account, "spaceID": space_id, "binarySHA256": BINARY_SHA,
                   "sourceManifestSHA256": SOURCE_MANIFEST_SHA,
                   "processID": process.pid, "phase": "execute", "wholeSpaceMigration": False,
                   "nativePlatform": "linux-arm64",
                   "interruptedPlanSHA256": PLAN_SHA}
        pending_runtime = args.output / "runtime.pending.json"
        pending_runtime.write_text(json.dumps(runtime, indent=2) + "\n")
        pending_runtime.replace(args.output / "runtime.json")
        result["accountID"] = account; result["spaceID"] = space_id
        phase = "external native execute/readback"
        await_signal("execute-complete")

        phase = "native process exit"
        stop()
        profile = offline_helper
        with socket.socket() as listener, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_listener:
            listener.bind(("127.0.0.1", 0)); listener.listen()
            probe_port = listener.getsockname()[1]
            udp_listener.bind(("127.0.0.1", probe_port))
            socket.create_connection(("127.0.0.1", probe_port), timeout=2).close()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                sender.sendto(b"owned-baseline", ("127.0.0.1", probe_port))
            udp_listener.settimeout(2)
            assert udp_listener.recvfrom(64)[0] == b"owned-baseline"
            checked = subprocess.run([sys.executable, "-B", str(profile), "--probe", str(probe_port)],
                                     capture_output=True, text=True, timeout=10)
            assert checked.returncode == 0
            controls = json.loads(checked.stdout)
            assert controls["tcpDenied"] and controls["udpDenied"]
            assert controls["noNewPrivileges"] and controls["seccompFilterActive"]
        result["offlinePolicy"] = {"sha256": sha(profile), "baselineListenerReachable": True,
            "baselineUDPSendReceived":True,"controls": controls,
            "scope":"only the new child process and its descendants; no global network mutation"}
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
