#!/usr/bin/env python3
"""Qualify explicit Bookmark component semantics on the retained native Linux CLI.

The historical 182-operation preservation account is copied byte-for-byte. This
adds only the eight unqualified Bookmark component operations, then compares a
second process with TCP and UDP outbound syscalls denied. It does not rerun or
promote the historical source-preservation/source-admission proof.
"""
import argparse
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
import urllib.request

BINARY_SHA = "1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"
SOURCE_MANIFEST_SHA = "12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c"
BUILD_SHA = "6d0f00da205846575bfd49e3fba8121aa1570a940ea3e13cc571aa4b4734e2f0"
CONFIG_SHA = "6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060"
OFFLINE_SHA = "6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1"
PRESERVATION_SHA = "f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b"
ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
SCRATCH = Path("/tmp/pinkha-w1-migration-swift-20261127")
NATIVE = Path("/var/lib/pinkha-root-t2-linux-20261126/build1/current")
RETAINED = Path("/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1")
OFFLINE = ROOT / "Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def inventory(root):
    assert root.is_dir() and not root.is_symlink() and root.resolve() == root
    rows, identities = {}, {}
    for path in [root] + sorted(root.rglob("*")):
        before = path.lstat()
        key = "." if path == root else path.relative_to(root).as_posix()
        identity = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns]
        assert not path.is_symlink() and path.resolve() == path
        if stat.S_ISREG(before.st_mode):
            assert before.st_nlink == 1 and before.st_size < 256 * 1024**2
            rows[key] = {"kind": "file", "bytes": before.st_size,
                         "mode": stat.S_IMODE(before.st_mode), "sha256": sha(path)}
        else:
            assert stat.S_ISDIR(before.st_mode)
            rows[key] = {"kind": "directory", "mode": stat.S_IMODE(before.st_mode)}
        assert identity(before) == identity(path.lstat())
        identities[key] = identity(before)
    return rows, identities


def swift_sources():
    rows = {}
    for module in ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"]:
        for path in sorted((ROOT / "Modules" / module).rglob("*")):
            if path.is_file() and (path.suffix == ".swift" or path.name == "Package.resolved"):
                rows[path.relative_to(ROOT).as_posix()] = sha(path)
    return rows


def qualify_native():
    assert sha(NATIVE / "any") == BINARY_SHA
    assert sha(NATIVE / "source-manifest.json") == SOURCE_MANIFEST_SHA
    manifest = json.loads((NATIVE / "source-manifest.json").read_text())
    assert manifest["schema"] == "pinkha-t2-permission-native-source-v1"
    assert manifest["commits"] == {"any": "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81",
                                    "sdk": "c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"}
    assert len(manifest["files"]) == 1594
    assert sha(NATIVE / "BUILD.json") == BUILD_SHA
    build = json.loads((NATIVE / "BUILD.json").read_text())
    assert build["status"] == "PASS_BUILD_ONLY" and build["exitCode"] == 0
    assert build["sourceUnchanged"] and build["ownedGroupAbsent"]
    assert (NATIVE / "source-before.json").read_bytes() == (NATIVE / "source-after.json").read_bytes()
    assert sha(NATIVE / "source-before.json") == "7101539ffeb0d039afd5ba6eca4827f6389b2ce0a1311ee493331e2f6db31138"
    files = {}
    for path in sorted((NATIVE / "source").rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            files[path.relative_to(NATIVE / "source").as_posix()] = {
                "kind": "file", "bytes": path.stat().st_size,
                "mode": stat.S_IMODE(path.stat().st_mode), "sha256": sha(path)}
    expected = {key: {k: row[k] for k in ["kind", "bytes", "mode", "sha256"]}
                for key, row in manifest["files"].items()}
    assert files == expected
    assert sha(NATIVE / "source/internal/config/nodeconf-prod.yml") == CONFIG_SHA
    assert sha(OFFLINE) == OFFLINE_SHA
    return {"binarySHA256": BINARY_SHA, "sourceManifestSHA256": SOURCE_MANIFEST_SHA,
            "buildReceiptSHA256": BUILD_SHA, "sourceFiles": len(files),
            "commits": manifest["commits"], "unchanged": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--swift-receipt", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    private = args.output / "private-account"
    work = args.output / "component"
    logs = args.output / "private-logs"
    work.mkdir(mode=0o700)
    logs.mkdir(mode=0o700)
    started = time.monotonic()
    result = {"protocol": "pinkha-native-bookmark-linux-component-v1", "status": "RUNNING",
              "sourceCommit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "scope": "Eight actual Bookmark component operations and two conditional URL edit/undo writes; new-process OS-offline readback",
              "historicalPreservationReexecuted": False, "sourceAdmissionPromoted": False,
              "wholeSpaceMigration": False, "appleUIPresentationAccepted": False,
              "processes": [], "phases": [], "errors": []}
    process = None
    test_process = None
    native_log = None
    known_absent = set()
    before_account = None
    before_swift = None
    minimum_free = shutil.disk_usage(args.output).free
    prior_native_receipt = None

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumFreeBytes"] = minimum_free
        write(args.output / "result.json", result)

    def guard():
        nonlocal minimum_free
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        assert minimum_free > 2 * 1024**3, "runtime disk emergency"
        assert time.monotonic() - started < 1100, "bounded component timeout"

    def absent(pid):
        if pid in known_absent:
            return True
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            known_absent.add(pid)
            return True
        return False

    def finish(child, timeout):
        if child.poll() is None and not absent(child.pid):
            os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if not absent(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
            raise RuntimeError("owned process required forced termination")
        assert absent(child.pid)

    def stop_native():
        nonlocal process, native_log
        if process is None:
            return
        child = process
        finish(child, 20)
        result["processes"][-1].update(exitCode=child.returncode, groupPositivelyAbsent=absent(child.pid))
        native_log.close()
        process = None
        save()
        assert child.returncode == 0, "native process unclean exit"

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = "http://127.0.0.1:" + str(port)

    def request(path, timeout=5):
        with urllib.request.urlopen(base + path, timeout=timeout) as reply:
            assert reply.status == 200
            return json.loads(reply.read(1 << 20))

    def offline_controls():
        with socket.socket() as tcp, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            tcp.bind(("127.0.0.1", 0))
            tcp.listen()
            probe_port = tcp.getsockname()[1]
            udp.bind(("127.0.0.1", probe_port))
            socket.create_connection(("127.0.0.1", probe_port), timeout=2).close()
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                sender.sendto(b"owned-baseline", ("127.0.0.1", probe_port))
            udp.settimeout(2)
            assert udp.recvfrom(64)[0] == b"owned-baseline"
            probe = subprocess.run([sys.executable, "-B", str(OFFLINE), "--probe", str(probe_port)],
                                   capture_output=True, text=True, timeout=10)
            assert probe.returncode == 0
            controls = json.loads(probe.stdout)
            assert controls["tcpDenied"] and controls["udpDenied"]
            assert controls["noNewPrivileges"] and controls["seccompFilterActive"]
        return {"helperSHA256": OFFLINE_SHA, "controls": controls,
                "baselineTCPReachable": True, "baselineUDPReceived": True,
                "scope": "only each owned native child and descendants; no global network change"}

    def start_native(phase, config):
        nonlocal process, native_log
        command = [sys.executable, "-B", str(OFFLINE), "--exec", str(NATIVE / "any"), "run",
                   "--config", str(config), "--data-dir", str(private), "--addr", "127.0.0.1:" + str(port)]
        env = {k: v for k, v in os.environ.items() if not k.startswith("ANY_")}
        env.update(ANY_DATA_DIR=str(private), GOMAXPROCS="2", GOMEMLIMIT="2GiB")
        native_log = (logs / (phase + ".log")).open("wb")
        process = subprocess.Popen(command, env=env, stdout=native_log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        result["processes"].append({"phase": phase, "pid": process.pid, "outboundDeniedByOS": True})
        deadline = time.monotonic() + 60
        while True:
            guard()
            assert process.poll() is None, "native process ended before health"
            try:
                request("/v1/health", timeout=1)
                break
            except OSError:
                pass
            assert time.monotonic() < deadline, "native readiness timeout"
            time.sleep(0.25)
        account = request("/v1/account")["id"]
        assert account == prior_native_receipt["accountID"]
        space = prior_native_receipt["spaceID"]
        member = request("/v1/spaces/" + space + "/members/me")
        assert member["identity"] == account and member["status"] == "active" and member["permission"] == "owner"
        sync = request("/v1/spaces/" + space + "/sync-status")
        assert sync["networkPeers"] == sync["localPeers"] == sync["globalPeers"] == 0
        fixture = {"baseURL": base, "accountID": account, "spaceID": space, "binarySHA256": BINARY_SHA,
                   "componentScope": "explicit-native-bookmark-v1", "outboundDeniedByOS": True,
                   "networkPeerCount": 0, "processID": process.pid, "phase": phase}
        write(work / "runtime.json", fixture)
        save()

    def run_test(phase):
        nonlocal test_process
        before_products = {str(p.relative_to(SCRATCH)): sha(p) for p in sorted(SCRATCH.rglob("*"))
                           if p.is_file() and p.name in ["PinkhaAnyHostTests-test-runner", "PinkhaAnyHostTests.so"]}
        assert len(before_products) == 2
        env = os.environ.copy()
        env.update(PINKHA_DESTINATION_NATIVE_FIXTURE=str(work / "runtime.json"),
                   PINKHA_DESTINATION_NATIVE_WORK=str(work), PINKHA_DESTINATION_NATIVE_PHASE=phase)
        migration = phase in ["execute", "reopen"]
        method = ("testActualNativeBookmarkURLAndEditorNotesColdReopen" if migration
                  else "testNativeBookmarkEditUndoAndEditedColdReopen")
        command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
                   "--scratch-path", str(SCRATCH), "--disable-automatic-resolution", "--skip-build",
                   "--filter", "AnyDestinationNativeBookmarkTests." + method]
        started_test = time.monotonic()
        path = args.output / (phase + "-test.log")
        with path.open("wb") as log:
            test_process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            while test_process.poll() is None:
                guard()
                assert time.monotonic() - started_test < 400, "native test timeout"
                assert process.poll() is None, "native stopped during test"
                time.sleep(0.5)
        text = path.read_text()
        row = {"phase": phase, "method": method, "exitCode": test_process.returncode, "testPID": test_process.pid,
               "nativePID": process.pid, "seconds": round(time.monotonic() - started_test, 3),
               "logSHA256": sha(path), "compiledProducts": before_products,
               "testGroupPositivelyAbsent": absent(test_process.pid)}
        result["phases"].append(row)
        test_process = None
        assert row["exitCode"] == 0 and row["testGroupPositivelyAbsent"], "native test failed"
        assert "Executed 1 test, with 0 failures" in text
        assert method + "' passed" in text
        marker = ("NATIVE_BOOKMARK_COMPONENT prepared_operations=8" if migration
                  else "NATIVE_BOOKMARK_EDIT_LIFECYCLE actual_conditional_writes=2")
        assert marker in text
        assert "skipped" not in text.lower()
        assert swift_sources() == before_swift
        assert {name: sha(SCRATCH / name) for name in before_products} == before_products
        row["result"] = "PASS"
        save()

    try:
        guard()
        result["nativeBefore"] = qualify_native()
        assert sha(RETAINED / "result.json") == PRESERVATION_SHA
        original = json.loads((RETAINED / "result.json").read_text())
        assert original["result"] == "PASS" and original["sourceAdmissionPromoted"] is False
        assert original["nativeOutput"] == str(RETAINED / "native")
        prior_native_receipt = json.loads((RETAINED / "native/controller-result.json").read_text())
        assert prior_native_receipt["result"] == "PROCESS_LIFECYCLE_PASS"
        assert prior_native_receipt["binarySHA256"] == BINARY_SHA
        assert len(prior_native_receipt["processes"]) == 2
        assert all(row["exitCode"] == 0 and row["groupPositivelyAbsent"] for row in prior_native_receipt["processes"])
        original_account = RETAINED / "native/private-account"
        active = []
        for proc in Path("/proc").iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if str(original_account).encode() in (proc / "cmdline").read_bytes():
                    active.append(int(proc.name))
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                pass
        assert not active, "retained account has an active process"
        before_account = inventory(original_account)
        write(args.output / "retained-account-inventory.json", before_account[0])
        shutil.copytree(original_account, private, copy_function=shutil.copy2)
        assert inventory(private)[0] == before_account[0]
        assert inventory(original_account) == before_account
        result["retainedInput"] = {"preservationReceiptSHA256": PRESERVATION_SHA,
                                   "controllerReceiptSHA256": sha(RETAINED / "native/controller-result.json"),
                                   "inventorySHA256": sha(args.output / "retained-account-inventory.json"),
                                   "entries": len(before_account[0]), "copyBytesAndModesEqual": True,
                                   "activeOriginalAccountProcesses": 0, "accountInitialized": False,
                                   "spaceCreated": False}
        before_swift = swift_sources()
        write(args.output / "swift-sources-before.json", before_swift)
        build = json.loads(args.swift_receipt.read_text())
        assert build["status"] in ["PASS", "PASS_BUILD_ONLY"] and build["sourceUnchanged"] and build["exitCode"] == 0
        assert build["compiled"] and build["ownedGroupAbsent"]
        assert before_swift == json.loads(args.swift_receipt.with_name("source-after.json").read_text())
        prior_components = args.output.parent / "derived-after-fix"
        accepted = json.loads((prior_components / "result.json").read_text())
        assert accepted["status"] == "PASS" and len(accepted["passLines"]) == 20 and not accepted["failLines"]
        accepted_sources = json.loads((prior_components / "source-after.json").read_text())
        assert {k: v for k, v in before_swift.items() if "/Sources/" in k} == {k: v for k, v in accepted_sources.items() if "/Sources/" in k}
        result["retainedComponentReceiptSHA256"] = sha(prior_components / "result.json")
        result["swiftBuildReceiptSHA256"] = sha(args.swift_receipt)
        old_config = (private / "config.yaml").read_text()
        old_nodeconf = "/Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/source/internal/config/nodeconf-prod.yml"
        expected_config = "network:\n  nodeconfPath: " + old_nodeconf + "\nindex:\n  embedder: none\np2p:\n  enabled: false\n"
        assert old_config == expected_config
        config = args.output / "run-config.yaml"
        config.write_text(old_config.replace(old_nodeconf, str(NATIVE / "source/internal/config/nodeconf-prod.yml")))
        result["configRelocation"] = {"originalAccountConfigChanged": False,
                                      "change": "Only immutable nodeconf filesystem locator", "nodeconfSHA256": CONFIG_SHA}
        result["offlinePolicy"] = offline_controls()
        for phase in ["execute", "reopen", "reopen-edited"]:
            start_native(phase, config)
            run_test(phase)
            if phase == "reopen":
                # Ordinary editing starts only after the original migration
                # has passed strict verification in both native processes.
                run_test("edit")
            stop_native()
        assert len({row["pid"] for row in result["processes"]}) == 3
        assert (work / "execute-bookmark.json").read_bytes() == (work / "reopen-bookmark.json").read_bytes()
        assert (work / "edit-lifecycle.json").read_bytes() == (work / "reopen-edited-lifecycle.json").read_bytes()
        edit = json.loads((work / "execute-property-edit.json").read_text())
        assert edit["actualConditionalWrites"] == 2 and edit["readbacksVerified"] and edit["inputRestored"]
        assert edit["migrationVerifiedBeforeEdits"]
        result["comparisonSHA256"] = sha(work / "execute-bookmark.json")
        result["editedColdComparisonSHA256"] = sha(work / "edit-lifecycle.json")
        result["actualPreparedOperations"] = 8
        result["actualConditionalURLWrites"] = 2
        result["uniqueTestMethods"] = 2
        result["testInvocations"] = 4
        result["modifiedOriginalMigrationReceiptRefused"] = True
        result["nativeAfter"] = qualify_native()
        assert result["nativeAfter"] == result["nativeBefore"]
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["errors"].append({"type": type(error).__name__, "message": str(error)})
    finally:
        for child in [test_process]:
            if child is not None:
                try:
                    finish(child, 10)
                except Exception as error:
                    result["status"] = "FAIL"
                    result["errors"].append({"cleanup": str(error)})
        try:
            stop_native()
        except Exception as error:
            result["status"] = "FAIL"
            result["errors"].append({"nativeCleanup": str(error)})
        if before_account is not None:
            try:
                assert inventory(RETAINED / "native/private-account") == before_account
                assert sha(RETAINED / "result.json") == PRESERVATION_SHA
                result["originalAccountAndPreservationReceiptUnchanged"] = True
            except Exception as error:
                result["status"] = "FAIL"
                result["errors"].append({"originalAccountIntegrity": str(error)})
        if before_swift is not None:
            after_swift = swift_sources()
            write(args.output / "swift-sources-after.json", after_swift)
            result["swiftSourcesUnchanged"] = before_swift == after_swift
            if not result["swiftSourcesUnchanged"]:
                result["status"] = "FAIL"
        result["privateLogReceipts"] = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
                                        for p in sorted(logs.iterdir()) if p.is_file()]
        save()
    print(json.dumps({k: result[k] for k in ["status", "scope", "seconds", "errors", "sourceAdmissionPromoted"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
