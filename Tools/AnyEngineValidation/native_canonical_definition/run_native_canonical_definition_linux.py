#!/usr/bin/env python3
"""Read eight additional exact-source canonical native definitions.

Reuses the qualified binary/source checker and account inventory implementation.
No accepted migration operations are reexecuted. The canonical descriptor
read path performs no domain writes or historical-value restamping.
"""
import argparse
import hashlib
import importlib.util
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

ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
COMMON = ROOT / "Tools/AnyEngineValidation/native_bookmark/run_native_bookmark_linux.py"
COMMON_SHA = "a6bf0a82bd690d2e0edc3b1f2c3be812842b48c1d2e837ff556ee71b7a8b7941"
assert hashlib.sha256(COMMON.read_bytes()).hexdigest() == COMMON_SHA
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
SOURCE_KEYS = {"rel-" + key for key in ["name", "description", "id", "spaceId", "type", "creator", "createdDate", "lastModifiedDate", "lastModifiedBy"]} | {"ot-space", "ot-objectType", "ot-participant"}
SOURCE_MANIFEST_SHA = "cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4"
ALLOCATION_RECEIPT = Path("/var/lib/pinkha-w1-functional-migration-20261127/canonical-native-allocation-measurement1/result.json")
ALLOCATION_SHA = "023e19116534d131b38553c979920602eb179be1d7d57b57e5b5e576816bb261"
MIB = 1024**2
CACHE_CUSTODY = Path("/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1/result.json")
CACHE_CUSTODY_SHA = "a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8"
CACHE_TARGET = Path("/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127")


def source_members():
    assert sha(AUDIT) == AUDIT_SHA
    audit = json.loads(AUDIT.read_text())
    assert audit["status"] == "PASS_RETAINED_CAPTURE_COHERENCE_AND_MEMBER_HASHES_ONLY"
    expected = {row["path"]: row for row in audit["members"]}
    assert len(expected) == 313
    result = {}
    assert sha(SOURCE / "manifest.json") == SOURCE_MANIFEST_SHA
    manifest = json.loads((SOURCE / "manifest.json").read_bytes())
    selected = [row for row in manifest["Objects"] if row["UniqueKey"] in SOURCE_KEYS]
    assert len(selected) == len(SOURCE_KEYS) == 12
    stems = [row["NativeJSONView"]["Path"][:-5] for row in selected]
    assert len(set(stems)) == 12
    for stem in stems:
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
    assert len(result) == 24
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--swift-receipt", type=Path, required=True)
    parser.add_argument("--swift-receipt-sha", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    private = args.output / "private-account"
    work = args.output / "component"
    logs = args.output / "private-logs"
    work.mkdir(mode=0o700)
    logs.mkdir(mode=0o700)
    started = time.monotonic()
    result = {"protocol": "pinkha-retained-original-canonical-definition-linux-v1", "status": "RUNNING",
              "sourceCommit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "scope": "Eight supplemental canonical source-definition bindings read exact native schemas; no original history or literal identity equivalence claimed",
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
    controller_before = {"canonicalDefinitions": sha(Path(__file__)), "bookmark": sha(COMMON)}
    minimum_free = shutil.disk_usage(args.output).free
    prior_native_receipt = None
    minimum_cache_free = shutil.disk_usage(SCRATCH).free

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumFreeBytes"] = minimum_free
        result["minimumDevelopmentCacheFreeBytes"] = minimum_cache_free
        write(args.output / "result.json", result)

    def guard():
        nonlocal minimum_free, minimum_cache_free
        minimum_cache_free = min(minimum_cache_free, shutil.disk_usage(SCRATCH).free)
        assert minimum_cache_free >= 512 * MIB, "development cache emergency reserve"
        minimum_free = min(minimum_free, shutil.disk_usage(args.output).free)
        assert minimum_free > 2 * 1024**3, "runtime disk emergency"
        assert time.monotonic() - started < 1100, "bounded component timeout"
        assert not (args.output / "abort").exists(), "owned canonical definition controller abort"
        usage = {"privateAccount": 0, "logs": 0, "otherOutput": 0, "wholeOutput": 0}
        entries = 0
        for base, folders, files in os.walk(args.output, followlinks=False):
            for name in [None] + files:
                path = Path(base) if name is None else Path(base) / name
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue  # A native SQLite temporary file was retired.
                assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "owned output contains a non-regular entry"
                entries += 1
                assert entries <= 512, "bounded owned output inventory"
                allocated = info.st_blocks * 512
                usage["wholeOutput"] += allocated
                if path == private or private in path.parents:
                    usage["privateAccount"] += allocated
                if name is not None and path.suffix == ".log":
                    usage["logs"] += allocated
                elif path != private and private not in path.parents:
                    usage["otherOutput"] += allocated
            assert all(not (Path(base) / name).is_symlink() for name in folders)
        peak = result.setdefault("maxObservedAllocationBytes", {key: 0 for key in usage})
        for key, value in usage.items():
            peak[key] = max(peak[key], value)
        assert usage["privateAccount"] <= 73 * MIB, "copied native account/WAL allocation cap"
        assert usage["logs"] <= 16 * MIB, "owned log allocation cap"
        assert usage["otherOutput"] <= 4 * MIB, "owned receipt/manifest allocation cap"
        assert usage["wholeOutput"] <= 96 * MIB, "owned total allocation cap"

    def interrupted(*_):
        raise RuntimeError("owned canonical definition controller interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

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
                   "componentScope": "retained-original-canonical-definitions-v1", "outboundDeniedByOS": True,
                   "networkPeerCount": 0, "processID": process.pid, "phase": phase}
        write(work / "runtime.json", fixture)
        save()

    def run_test(phase):
        nonlocal test_process
        before_products = {str(p.relative_to(SCRATCH)): sha(p) for p in sorted(SCRATCH.rglob("*"))
                           if p.is_file() and p.name in ["PinkhaAnyHostTests-test-runner", "PinkhaAnyHostTests.so"]}
        assert len(before_products) == 2
        assert before_products == build["compiledProducts"], "Products differ from qualified Swift receipt"
        env = {k: v for k, v in os.environ.items() if not k.startswith("PINKHA_NATIVE_")}
        env.update(PINKHA_NATIVE_CANONICAL_FIXTURE=str(work / "runtime.json"),
                   PINKHA_NATIVE_CANONICAL_WORK=str(work), PINKHA_NATIVE_CANONICAL_PHASE=phase,
                   PINKHA_NATIVE_ORIGINAL156=str(SOURCE.parent),
                   PINKHA_NATIVE_DEFINITION_RETAINED=str(RETAINED / "private-work"))
        method = "testEightOriginalCanonicalDescriptorsAndColdProcessKeepSourceValueMeaningSeparate"
        command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
                   "--scratch-path", str(SCRATCH), "--disable-automatic-resolution", "--skip-build",
                   "--filter", "AnyDestinationNativeCanonicalSupplementTests." + method]
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
        marker = "PINKHA_NATIVE_CANONICAL_DEFINITION_PHASE_PASS " + phase
        assert marker in text
        assert "skipped" not in text.lower()
        assert swift_sources() == before_swift
        assert {name: sha(SCRATCH / name) for name in before_products} == before_products
        row["result"] = "PASS"
        save()

    try:
        guard()
        assert sha(CACHE_CUSTODY) == CACHE_CUSTODY_SHA
        custody = json.loads(CACHE_CUSTODY.read_bytes())
        assert custody["status"] == "PASS_EXACT_OWNED_SWIFT_CACHE_RELOCATED_STABLE_PATH_RETAINED"
        assert custody["allExactPortableMetadataAndBytesRetained"] and custody["productsAndDependencyClosureUnchanged"]
        assert custody["originalDuplicateRemoved"] and custody["stableSymlinkInstalled"]
        assert SCRATCH.is_symlink() and SCRATCH.resolve() == CACHE_TARGET
        result["cacheCustodyReceiptSHA256"] = CACHE_CUSTODY_SHA
        result["stableCachePath"] = str(SCRATCH)
        result["physicalCachePath"] = str(CACHE_TARGET)
        (args.output / "cache-custody-result.json").write_bytes(CACHE_CUSTODY.read_bytes())
        assert sha(ALLOCATION_RECEIPT) == ALLOCATION_SHA
        allocation = json.loads(ALLOCATION_RECEIPT.read_text())
        assert allocation["status"] == "MEASURED_ALLOCATION_BUDGET_ONLY_NOT_NATIVE_QUALIFICATION"
        assert allocation["copyBlockRoundedUpperBoundBytes"] == 8_637_368
        assert allocation["priorUnexecutedControllerSHA256"] == "994dc8a11c5e5d413e87d6a46fbb0af655da7920de9098e47eca2f91402d63a0"
        assert sha(ALLOCATION_RECEIPT.with_name("previous-unexecuted-controller.py")) == allocation["priorUnexecutedControllerSHA256"]
        assert allocation["resourcePolicy"]["initialReserveMiB"] == 128
        assert allocation["resourcePolicy"]["liveRootEmergencyFloorMiB"] == 2048
        result["measuredAllocationReceiptSHA256"] = ALLOCATION_SHA
        result["allocationControllerDeltaSHA256"] = sha(ALLOCATION_RECEIPT.with_name("controller.diff"))
        result["resourcePolicy"] = allocation["resourcePolicy"]
        (args.output / "allocation-measurement.json").write_bytes(ALLOCATION_RECEIPT.read_bytes())
        (args.output / "controller.py").write_bytes(Path(__file__).read_bytes())
        assert minimum_free > 2 * 1024**3 + 128 * MIB, "measured native initialization reserve"
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
        original_inputs = {
            "source-preservation-plan.json": "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930",
            "execute-mappings.json": "eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3",
            "execute-verification.json": "fee4dc5cb8e689e01bf2d1fbe8bd262c42388fd706da4114be72af3e6cf97350"}
        for name, expected in original_inputs.items():
            assert sha(RETAINED / "private-work" / name) == expected
        write(work / "accepted-canonical-inputs.json", {"sourceReceiptSHA256": PRESERVATION_SHA,
            "originalInputs": original_inputs, "originalOperationsReexecuted": 0,
            "sourceAdmissionPromoted": False, "originalHistoryValuesRestamped": False})
        result["canonicalInputSHA256"] = sha(work / "accepted-canonical-inputs.json")
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
        block_bytes = os.statvfs(args.output).f_frsize
        copy_upper_bound = 0
        for copy_walk_dir, folders, files in os.walk(original_account, followlinks=False):
            copy_upper_bound += block_bytes
            for name in files:
                info = (Path(copy_walk_dir) / name).lstat()
                assert stat.S_ISREG(info.st_mode)
                copy_upper_bound += ((info.st_size + block_bytes - 1) // block_bytes) * block_bytes
        assert copy_upper_bound <= 9 * MIB, "measured source-account copy bound changed"
        result["sourceAccountCopyRoundedUpperBytes"] = copy_upper_bound
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
        assert sha(args.swift_receipt) == args.swift_receipt_sha
        build = json.loads(args.swift_receipt.read_text())
        assert build["status"] == "PASS" and build["compiled"] and build["sourceUnchanged"] and build["exitCode"] == 0
        assert len(build["passLines"]) == len(build["startLines"]) == 1 and not build["failLines"] and build["ownedGroupAbsent"]
        positive = "testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics"
        negatives = ["testSupplementRefusesDuplicateExistingAndCallerChosenAliases", "testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace"]
        assert positive in build["passLines"][0] and positive in build["startLines"][0]
        qualification = build["qualification"]
        assert qualification == {"newlyExecutedMethods": 1, "retainedUnchangedMethods": 2, "totalQualifiedMethods": 3,
                                 "qualifiedMethods": [positive] + negatives, "priorOverallFailurePreserved": True}
        reused = build["retainedNegativeEvidence"]
        prior = args.swift_receipt.parent.with_name("canonical-definition-components-attempt1")
        assert reused["priorReceiptSHA256"] == sha(prior / "result.json") == "77d727e8ce35c23f0a0ea82edb7e86c66aec977d32bb9b90cfcabe7a9916a37e"
        assert reused["priorLogSHA256"] == sha(prior / "test.log") == "9b4f04fec020fd89c7705dd0536f57a2730455202aa8128be8e5ccd5ee3a0886"
        assert reused["priorOverallStatus"] == json.loads((prior / "result.json").read_text())["status"] == "FAIL"
        assert reused["allOtherSwiftSourcesUnchanged"] and reused["negativeMethodBodiesAndHelpersUnchanged"] and reused["sourceInputsAndDependenciesUnchanged"]
        assert len(reused["retainedMethods"]) == 2
        assert [row["method"] for row in reused["retainedMethods"]] == negatives
        for row in reused["retainedMethods"]:
            assert row["method"] in row["startLine"] and " started" in row["startLine"]
            assert row["method"] in row["passLine"] and " passed " in row["passLine"]
        assert build["compiledProducts"] == custody["qualifiedProducts"]
        result["componentQualification"] = qualification
        assert before_swift == json.loads(args.swift_receipt.with_name("source-after.json").read_text())
        assert build["sourceCommit"] == result["sourceCommit"]
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
        assert (work / "read-canonical.json").read_bytes() == (work / "reopen-canonical.json").read_bytes()
        rows = json.loads((work / "read-canonical.json").read_bytes())
        assert len(rows) == 8 and len({r["sourceObjectID"] for r in rows}) == 8
        assert {r["nativePropertyID"] for r in rows} == {"description", "id", "spaceId", "type", "author", "createdAt", "modifiedAt", "modifiedBy"}
        assert all(r["nativeOwnerID"] == "any" for r in rows)
        for phase in ["read", "reopen"]:
            proof = json.loads((work / (phase + "-result.json")).read_bytes())
            assert proof["newCanonicalDefinitions"] == 8 and proof["allDirectoryEntries"] == 21 and proof["unresolvedSourceDefinitions"] == 129
            assert proof["foreignSpaceRefused"] and proof["revokedLeaseRefused"]
            assert proof["preparedOperations"] == proof["domainWrites"] == 0
            assert not proof["originalHistoryValuesRestamped"] and not proof["literalNativeIdentityEquivalenceClaim"]
            assert not proof["sourceAdmissionPromoted"] and not proof["wholeSpaceMigration"]
        result["comparisonSHA256"] = sha(work / "read-canonical.json")
        result["actualPreparedOperations"] = 0
        result["actualDomainWrites"] = 0
        result["uniqueTestMethods"] = 1
        result["testInvocations"] = 2
        result["revokedSessionReadRefused"] = True
        result["originalHistoryValuesRestamped"] = False
        result["literalNativeIdentityEquivalenceClaim"] = False
        result["newCanonicalDefinitions"] = 8
        result["allDirectoryEntries"] = 21
        result["unresolvedSourceDefinitions"] = 129
        assert sha(work / "accepted-canonical-inputs.json") == result["canonicalInputSHA256"]
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
                for name, expected in original_inputs.items():
                    assert sha(RETAINED / "private-work" / name) == expected
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
            assert {"canonicalDefinitions": sha(Path(__file__)), "bookmark": sha(COMMON)} == controller_before
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
            if result["status"] == "PASS":
                guard()
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
