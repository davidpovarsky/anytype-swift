#!/usr/bin/env python3
"""Read the accepted original graph through the new scoped typed adapters.

Reuses the qualified binary/source checker and account inventory implementation.
No accepted 182-operation or eight-operation migration is reexecuted. The
already qualified original relation is read without any new domain writes.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
COMMON = ROOT / "Tools/AnyEngineValidation/native_bookmark/run_native_bookmark_linux.py"
spec = importlib.util.spec_from_file_location("qualified_native_bookmark", COMMON)
assert spec is not None and spec.loader is not None
qualified = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualified)
sha, write, inventory = qualified.sha, qualified.write, qualified.inventory
swift_sources, qualify_native = qualified.swift_sources, qualified.qualify_native
SCRATCH, NATIVE, RETAINED, OFFLINE = qualified.SCRATCH, qualified.NATIVE, qualified.RETAINED, qualified.OFFLINE
BINARY_SHA, PRESERVATION_SHA = qualified.BINARY_SHA, qualified.PRESERVATION_SHA
OFFLINE_SHA, CONFIG_SHA = qualified.OFFLINE_SHA, qualified.CONFIG_SHA
SOURCE = Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156/bundle")
AUDIT = Path("/var/lib/pinkha-w1-engine-contracts-20261127/original156-coherence-audit/result.json")
AUDIT_SHA = "68319ff3adca0da6191ce0a4df8ff9654bac6d5be745306922662da5d5454244"
SOURCE_STEMS = ["snapshot-499c3540377351bb70bd1c7cd9eaaafc40acc45dffb31820ed89110e0e592fb4",
                "snapshot-c9c4bed807a227f8ecfe6d68093e99c89b48814361c328f59b5533513e082b86"]


def source_members():
    assert sha(AUDIT) == AUDIT_SHA
    audit = json.loads(AUDIT.read_text())
    assert audit["status"] == "PASS_RETAINED_CAPTURE_COHERENCE_AND_MEMBER_HASHES_ONLY"
    expected = {row["path"]: row for row in audit["members"]}
    assert len(expected) == 313
    result = {}
    for stem in SOURCE_STEMS:
        for suffix in [".json", ".pb"]:
            name = stem + suffix
            path = SOURCE / name
            before = path.lstat()
            assert not path.is_symlink() and path.resolve() == path
            row = {"path": name, "bytes": before.st_size, "sha256": sha(path)}
            after = path.lstat()
            identity = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size, value.st_mtime_ns)
            assert identity(before) == identity(after)
            assert row == expected[name]
            result[name] = row
    assert len(result) == 4
    return result


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
    result = {"protocol": "pinkha-retained-original-graph-adapter-linux-v1", "status": "RUNNING",
              "sourceCommit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "scope": "New typed source bindings read the accepted original outgoing/backlink graph; zero new domain writes",
              "historicalPreservationReexecuted": False, "sourceAdmissionPromoted": False,
              "wholeSpaceMigration": False, "appleUIPresentationAccepted": False,
              "processes": [], "testLaunches": [], "phases": [], "errors": []}
    process = None
    test_process = None
    native_log = None
    known_absent = set()
    before_account = None
    before_swift = None
    source_before = None
    controller_before = {"graph": sha(Path(__file__)), "bookmark": sha(COMMON)}
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
        assert not (args.output / "abort").exists(), "owned graph controller abort"

    def interrupted(*_):
        raise RuntimeError("owned graph controller interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

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
        if not absent(child.pid):
            os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if not absent(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
            raise RuntimeError("owned process required forced termination")
        deadline = time.monotonic() + 5
        while not absent(child.pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if not absent(child.pid):
            os.killpg(child.pid, signal.SIGKILL)
            raise RuntimeError("owned descendants required forced termination")
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
            raw = reply.read((1 << 20) + 1)
            assert len(raw) <= 1 << 20, "bounded native response"
            return json.loads(raw)

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
        guard()
        assert sha(NATIVE / "any") == BINARY_SHA and sha(OFFLINE) == OFFLINE_SHA
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
        fields = dict(line.split(":", 1) for line in (Path("/proc") / str(process.pid) / "status").read_text().splitlines() if ":" in line)
        assert fields["NoNewPrivs"].strip() == "1" and fields["Seccomp"].strip() == "2"
        executable = (Path("/proc") / str(process.pid) / "exe").resolve()
        assert executable == NATIVE / "any" and sha(executable) == BINARY_SHA
        result["processes"][-1].update(actualInheritedNoNewPrivileges=True,
            actualInheritedSeccompFilter=True, actualExecutableSHA256=BINARY_SHA)
        account = request("/v1/account")["id"]
        assert account == prior_native_receipt["accountID"]
        space = prior_native_receipt["spaceID"]
        member = request("/v1/spaces/" + space + "/members/me")
        assert member["identity"] == account and member["status"] == "active" and member["permission"] == "owner"
        sync = request("/v1/spaces/" + space + "/sync-status")
        assert sync["networkPeers"] == sync["localPeers"] == sync["globalPeers"] == 0
        fixture = {"baseURL": base, "accountID": account, "spaceID": space, "binarySHA256": BINARY_SHA,
                   "componentScope": "retained-original-native-graph-adapter-v1", "outboundDeniedByOS": True,
                   "networkPeerCount": 0, "processID": process.pid, "phase": phase}
        write(work / "runtime.json", fixture)
        save()

    def run_test(phase):
        nonlocal test_process
        before_products = {str(p.relative_to(SCRATCH)): sha(p) for p in sorted(SCRATCH.rglob("*"))
                           if p.is_file() and p.name in ["PinkhaAnyHostTests-test-runner", "PinkhaAnyHostTests.so"]}
        assert len(before_products) == 2
        env = os.environ.copy()
        env.update(PINKHA_NATIVE_GRAPH_FIXTURE=str(work / "runtime.json"),
                   PINKHA_NATIVE_GRAPH_WORK=str(work), PINKHA_NATIVE_GRAPH_PHASE=phase,
                   PINKHA_NATIVE_ORIGINAL156=str(SOURCE.parent))
        method = "testRetainedOriginalGraphReadOnlyAdapterAndColdIdentity"
        command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
                   "--scratch-path", str(SCRATCH), "--disable-automatic-resolution", "--skip-build",
                   "--filter", "AnyDestinationNativeGraphTests." + method]
        started_test = time.monotonic()
        path = args.output / (phase + "-test.log")
        with path.open("wb") as log:
            test_process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result["testLaunches"].append({"phase": phase, "pid": test_process.pid, "method": method})
            save()
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
        assert row["exitCode"] == 0 and row["testGroupPositivelyAbsent"], "native test failed"
        test_process = None
        assert "Executed 1 test, with 0 failures" in text
        assert method + "' passed" in text
        marker = "NATIVE_GRAPH_ADAPTER new_domain_writes=0 retained_outgoing=1 retained_backlinks=1"
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
        previous = json.loads((RETAINED / "result.json").read_text())
        assert previous["result"] == "PASS" and previous["sourceAdmissionPromoted"] is False
        assert not previous["wholeSpaceMigration"]
        assert sha(RETAINED / "native/controller-result.json") == "5925bd5a08c972e3dbe7666b77f9e230fe340b36b46289c870384e66c516a899"
        prior_native_receipt = json.loads((RETAINED / "native/controller-result.json").read_text())
        assert prior_native_receipt["result"] == "PROCESS_LIFECYCLE_PASS"
        assert prior_native_receipt["binarySHA256"] == BINARY_SHA
        assert len(prior_native_receipt["processes"]) == 2
        assert all(row["exitCode"] == 0 and row["groupPositivelyAbsent"] for row in prior_native_receipt["processes"])
        original_account = RETAINED / "native/private-account"
        result["sourceDefinitionMembersBefore"] = source_members()
        source_before = result["sourceDefinitionMembersBefore"]
        result["originalCoherenceAuditReceiptSHA256"] = AUDIT_SHA
        prior_work = RETAINED / "private-work"
        comparison = "7c39a72aec3e9c87cef67ffabbe982cd76501f195d36aafd354bea13e5a71ac5"
        assert previous["fullSourcePreservationComparisonSHA256"] == comparison
        assert sha(prior_work / "execute-content.json") == sha(prior_work / "reopen-content.json") == comparison
        previous_content = json.loads((prior_work / "execute-content.json").read_text())
        links = previous_content["actualLinkIndex"]
        assert len(links["forward"]["links"]) == 1
        assert links["reverse"]["object"] == links["forward"]["links"]
        assert links["reverse"]["parts"] == [] and links["emptySource"]["links"] == []
        write(work / "accepted-native-graph.json", {
            "sourceReceiptSHA256": PRESERVATION_SHA, "sourceComparisonSHA256": comparison,
            "actualLinkIndex": links, "sourceGraphAlreadyAccepted": True,
            "sourceAdmissionPromoted": False})
        result["retainedNativeGraphComparisonSHA256"] = comparison
        result["graphInputSHA256"] = sha(work / "accepted-native-graph.json")
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
        assert build["status"] == "PASS" and build["compiled"] and build["sourceUnchanged"] and build["exitCode"] == 0
        assert len(build["passLines"]) == 4 and not build["failLines"] and build["ownedGroupAbsent"]
        assert build["compiled"] and build["ownedGroupAbsent"]
        assert before_swift == json.loads(args.swift_receipt.with_name("source-after.json").read_text())
        assert build["sourceCommit"] == result["sourceCommit"]
        assert build["status"] == "PASS" and len(build["passLines"]) == 4 and not build["failLines"]
        result["retainedComponentReceiptSHA256"] = PRESERVATION_SHA
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
        for phase in ["read", "reopen"]:
            start_native(phase, config)
            run_test(phase)
            stop_native()
        assert len({row["pid"] for row in result["processes"]}) == 2
        assert (work / "read-graph.json").read_bytes() == (work / "reopen-graph.json").read_bytes()
        proof = json.loads((work / "read-graph.json").read_text())
        assert proof["expectedRelationDelivered"] and not proof["indexResponseTruncated"]
        assert not proof["sourceAdmissionPromoted"] and not proof["replicationCompletenessClaim"]
        assert proof["newDomainWrites"] == 0
        result["comparisonSHA256"] = sha(work / "read-graph.json")
        result["actualPreparedOperations"] = 0
        result["actualConditionalRelationWrites"] = 0
        result["uniqueTestMethods"] = 1
        result["testInvocations"] = 2
        result["revokedSessionReadRefused"] = True
        assert sha(work / "accepted-native-graph.json") == result["graphInputSHA256"]
        result["nativeAfter"] = qualify_native()
        assert result["nativeAfter"] == result["nativeBefore"]
        result["status"] = "PASS"
    except BaseException as error:
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
                result["originalAccountAndAcceptedReceiptsUnchanged"] = True
            except Exception as error:
                result["status"] = "FAIL"
                result["errors"].append({"originalAccountIntegrity": str(error)})
        if before_swift is not None:
            try:
                after_swift = swift_sources()
                write(args.output / "swift-sources-after.json", after_swift)
                result["swiftSourcesUnchanged"] = before_swift == after_swift
                assert result["swiftSourcesUnchanged"]
            except Exception as error:
                result["status"] = "FAIL"
                result["errors"].append({"swiftSourceIntegrity": str(error)})
        try:
            assert {"graph": sha(Path(__file__)), "bookmark": sha(COMMON)} == controller_before
            result["controllerSources"] = controller_before
            if source_before is not None:
                result["sourceDefinitionMembersAfter"] = source_members()
                assert result["sourceDefinitionMembersAfter"] == source_before
                result["sourceDefinitionsUnchanged"] = True
        except Exception as error:
            result["status"] = "FAIL"
            result["errors"].append({"sourceIntegrity": str(error)})
        try:
            result["privateLogReceipts"] = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)}
                                            for p in sorted(logs.iterdir()) if p.is_file()]
        except Exception as error:
            result["status"] = "FAIL"
            result["errors"].append({"privateLogInventory": str(error)})
        result["allOwnedGroupsPositivelyAbsent"] = all(row["pid"] in known_absent for row in result["processes"] + result["testLaunches"])
        if not result["allOwnedGroupsPositivelyAbsent"]:
            result["status"] = "FAIL"
        save()
    print(json.dumps({k: result[k] for k in ["status", "scope", "seconds", "errors", "sourceAdmissionPromoted"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
