#!/usr/bin/env python3
"""Qualify the current prepared-association boundary on a private original account copy.

Only three new signed claims are allowed: explicit seed, intervening B and frozen A.
Exact retries must keep six total claims and retain both semantic variants. A real
SIGKILL followed by a new OS-network-denied native process proves the cold retry.
No original Heart history admission, new object, editor block or install is claimed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.request
import uuid

ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
COMMON = ROOT / "Tools/AnyEngineValidation/native_bookmark/run_native_bookmark_linux.py"
COMMON_SHA = "a6bf0a82bd690d2e0edc3b1f2c3be812842b48c1d2e837ff556ee71b7a8b7941"
assert hashlib.sha256(COMMON.read_bytes()).hexdigest() == COMMON_SHA
spec = importlib.util.spec_from_file_location("qualified_bookmark", COMMON)
assert spec is not None and spec.loader is not None
qualified = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualified)
sha, write = qualified.sha, qualified.write
SCRATCH, NATIVE, OFFLINE = qualified.SCRATCH, qualified.NATIVE, qualified.OFFLINE
BINARY_SHA, OFFLINE_SHA, CONFIG_SHA = qualified.BINARY_SHA, qualified.OFFLINE_SHA, qualified.CONFIG_SHA
ARCHIVE = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network/private-native-account-retention1/actual-accounts-and-originals.tar.gz")
ARCHIVE_SHA = "be1806e5c72c3ee30dc2612fb3cb4148747247cb4771262f779303cf6a51b147"
FIXTURE_SHA = "2103428a0bac1645b612936bde7b13ba6e707ad9e172059f44a618b941cd3e1f"
ACCOUNT = "A7uNCqK2QB6J48HEDWGGX2Zv37vxFXZMxvF96R6sjzk7YPbx"
SPACE = "bafyreicbctkf6ogqxta4pn2lfoijoesvmrtub2spj2ei2wbagywgcqau2y.11113vcq7lykz"
OBJECT = "bafyreigcv3i3omngn7eivsxmumj2ihui2kyke5v7aivrytxq6anwbag3e4"
CANONICAL_RECEIPT = Path("/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json")
CANONICAL_SHA = "afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab"
CACHE_CUSTODY = Path("/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1/result.json")
CACHE_CUSTODY_SHA = "a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8"
CACHE_TARGET = Path("/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127")
MIB = 1024**2
BOUNDARY = {
    "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift": "cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1",
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyGuardedTorahOperationStore.swift": "6560662e18373ee92685922efca7a61713eebac89db74347a671995fb48ad41d",
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahAssociationRepository.swift": "6b261cf6748118a743162234ab8d7cc2b7fdf8ad2a58b58280de87fa77c1aebb",
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahPreparedMutation.swift": "0ead560345400729b0e320a73df4bac99df3673aa164a18d570c06bcbb8b74a1",
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahImmutableAssociationPolicy.swift": "5e80cb95aaffd87d4ba69c594a33a8ca7fce019d61ba6db192fe5f709bf2a498",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--swift-receipt", type=Path, required=True)
    parser.add_argument("--swift-receipt-sha", required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{64}", args.swift_receipt_sha)
    assert args.output.is_absolute() and args.output.parent.resolve() == args.output.parent
    assert str(args.output).startswith("/var/lib/pinkha-w1-functional-migration-20261127/")
    os.umask(0o077)
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    private, work, logs = [args.output / name for name in ("private-account", "component", "private-logs")]
    for path in (private, work, logs):
        path.mkdir(mode=0o700)
    started = time.monotonic()
    result = {"protocol": "pinkha-retained-prepared-association-linux-v1", "status": "RUNNING",
              "sourceCommit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
              "scope": "Current Any prepared-mutation boundary: explicit new seed, frozen observed set, intervening semantic variant, exact retries and actual SIGKILL/offline cold reopen",
              "originalSourceAdmissionPromoted": False, "originalHeartHistoryReconstructed": False,
              "historicalPreservationReexecuted": False, "originalAccountModified": False,
              "independentClientSignatureVerification": False, "swiftBuilds": 0, "goBuilds": 0,
              "processes": [], "testLaunches": [], "phases": [], "errors": []}
    children = []
    minimum_root, minimum_dev = shutil.disk_usage("/").free, shutil.disk_usage(SCRATCH).free
    source_before = None
    build = None
    controller_sha = sha(Path(__file__))
    phase = "preflight"

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumRootFreeBytes"] = minimum_root
        result["minimumDevelopmentFreeBytes"] = minimum_dev
        write(args.output / "result.json", result)

    def guard():
        nonlocal minimum_root, minimum_dev
        minimum_root = min(minimum_root, shutil.disk_usage("/").free)
        minimum_dev = min(minimum_dev, shutil.disk_usage(SCRATCH).free)
        assert minimum_root >= 2 * 1024**3, "root runtime emergency floor"
        assert minimum_dev >= 512 * MIB, "development runtime emergency floor"
        assert time.monotonic() - started < 1100, "bounded prepared-association controller"
        assert not (args.output / "abort").exists(), "owned controller abort"
        usage = {"privateAccount": 0, "logs": 0, "otherOutput": 0, "wholeOutput": 0}
        entries = 0
        for walk_dir, dirs, files in os.walk(args.output, followlinks=False):
            for name in [None] + files:
                path = Path(walk_dir) if name is None else Path(walk_dir) / name
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue  # Native SQLite may retire an owned temporary file.
                assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)
                entries += 1
                assert entries <= 512
                size = info.st_blocks * 512
                usage["wholeOutput"] += size
                if path == private or private in path.parents:
                    usage["privateAccount"] += size
                elif name is not None and path.suffix == ".log":
                    usage["logs"] += size
                else:
                    usage["otherOutput"] += size
            assert all(not (Path(walk_dir) / name).is_symlink() for name in dirs)
        peak = result.setdefault("maxObservedAllocationBytes", {key: 0 for key in usage})
        for key, value in usage.items():
            peak[key] = max(peak[key], value)
        assert usage["privateAccount"] <= 73 * MIB
        assert usage["logs"] <= 16 * MIB and usage["otherOutput"] <= 4 * MIB
        assert usage["wholeOutput"] <= 96 * MIB

    def interrupted(*_):
        raise RuntimeError("owned prepared-association controller interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    def absent(child):
        if child["row"].get("groupPositivelyAbsent") is True:
            return True
        try:
            os.killpg(child["p"].pid, 0)
        except ProcessLookupError:
            child["row"]["groupPositivelyAbsent"] = True
            return True
        return False

    def spawn(name, command, env, native=False):
        guard()
        path = logs / (name + ".log")
        handle = path.open("xb")
        child = {"p": subprocess.Popen(command, env=env, stdout=handle, stderr=subprocess.STDOUT,
                                       start_new_session=True), "log": handle}
        row = {"name": name, "pid": child["p"].pid, "command": command, "log": str(path), "intentionalCrash": False}
        child["row"] = row
        children.append(child)
        result["processes" if native else "testLaunches"].append(row)
        save()
        return child

    def close(child, expected=0, terminate=True):
        process, row = child["p"], child["row"]
        if process.poll() is None:
            if terminate and not absent(child):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                row["forcedUnexpectedKill"] = True
                if not absent(child):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while not absent(child) and time.monotonic() < deadline:
            time.sleep(0.05)
        if not absent(child):
            row["forcedUnexpectedKill"] = True
            os.killpg(process.pid, signal.SIGKILL)
        row["exitCode"] = process.returncode
        child["log"].close()
        row["logSHA256"] = sha(Path(row["log"]))
        save()
        assert absent(child), "owned process group remains"
        assert process.returncode == expected and not row.get("forcedUnexpectedKill"), "owned process exit differs"

    def request(child, path):
        guard()
        assert child["p"].poll() is None
        with urllib.request.urlopen(child["base"] + path, timeout=5) as response:
            assert response.status == 200
            raw = response.read(4 * MIB + 1)
            assert len(raw) <= 4 * MIB
            return json.loads(raw)

    def start_native(name, config):
        assert sha(NATIVE / "any") == BINARY_SHA and sha(OFFLINE) == OFFLINE_SHA
        assert sha(config) == result["configSHA256"]
        with socket.socket() as socket_probe:
            socket_probe.bind(("127.0.0.1", 0))
            port = socket_probe.getsockname()[1]
        command = [sys.executable, "-B", str(OFFLINE), "--exec", str(NATIVE / "any"), "run", "--config", str(config),
                   "--data-dir", str(private), "--addr", "127.0.0.1:" + str(port)]
        env = {key: value for key, value in os.environ.items() if not key.startswith("ANY_")}
        env.update(ANY_DATA_DIR=str(private), GOMAXPROCS="2", GOMEMLIMIT="1GiB")
        child = spawn(name, command, env, native=True)
        child["base"] = "http://127.0.0.1:" + str(port)
        deadline = time.monotonic() + 60
        while True:
            assert child["p"].poll() is None, "native exited before health"
            try:
                request(child, "/v1/health")
                break
            except OSError:
                pass
            guard()
            assert time.monotonic() < deadline, "native readiness deadline"
            time.sleep(0.25)
        proc = Path("/proc") / str(child["p"].pid)
        fields = dict(line.split(":", 1) for line in (proc / "status").read_text().splitlines() if ":" in line)
        assert fields["NoNewPrivs"].strip() == "1" and fields["Seccomp"].strip() == "2"
        assert (proc / "exe").resolve() == NATIVE / "any"
        assert request(child, "/v1/account")["id"] == ACCOUNT
        member = request(child, "/v1/spaces/" + SPACE + "/members/me")
        assert member["identity"] == ACCOUNT and member["status"] == "active" and member["permission"] == "owner"
        sync = request(child, "/v1/spaces/" + SPACE + "/sync-status")
        assert all(sync[key] == 0 for key in ("networkPeers", "localPeers", "globalPeers"))
        child["row"].update(outboundDeniedByOS=True, actualInheritedNoNewPrivileges=True, actualInheritedSeccompFilter=True,
                            actualExecutableSHA256=BINARY_SHA, peerCounts={key: sync[key] for key in ("networkPeers", "localPeers", "globalPeers")})
        write(work / "runtime.json", {"componentScope": "retained-native-prepared-association-v1", "baseURL": child["base"],
              "accountID": ACCOUNT, "spaceID": SPACE, "runID": result["runID"], "binarySHA256": BINARY_SHA,
              "outboundDeniedByOS": True, "networkPeerCount": 0, "processID": child["p"].pid})
        save()
        return child

    def products():
        value = {str(path.relative_to(SCRATCH)): sha(path) for path in sorted(SCRATCH.rglob("*"))
                 if path.is_file() and path.name in ("PinkhaAnyHostTests-test-runner", "PinkhaAnyHostTests.so")}
        assert len(value) == 2
        return value

    def test(name, native):
        assert products() == build["compiledProducts"], "Products differ from qualified compile"
        assert qualified.swift_sources() == source_before
        method = "testPreparedSemanticAssociationKeepsObservedSetConflictAndColdRetry"
        env = {key: value for key, value in os.environ.items() if not key.startswith("PINKHA_NATIVE_")}
        env.update(PINKHA_NATIVE_PREPARED_ASSOCIATION_FIXTURE=str(work / "runtime.json"),
                   PINKHA_NATIVE_PREPARED_ASSOCIATION_WORK=str(work), PINKHA_NATIVE_PREPARED_ASSOCIATION_PHASE=name)
        command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
                   "--scratch-path", str(SCRATCH), "--disable-automatic-resolution", "--skip-build", "--filter",
                   "AnyDestinationNativePreparedAssociationTests." + method]
        before = time.monotonic()
        child = spawn("swift-" + name, command, env)
        child["row"].update(phase=name, method=method, nativePID=native["p"].pid)
        while child["p"].poll() is None:
            guard()
            assert native["p"].poll() is None
            assert time.monotonic() - before < 400
            time.sleep(0.25)
        close(child, terminate=False)
        text = Path(child["row"]["log"]).read_text()
        starts = [line for line in text.splitlines() if "Test Case " in line and " started" in line]
        passes = [line for line in text.splitlines() if "Test Case " in line and " passed " in line]
        assert len(starts) == len(passes) == 1 and all(method in line for line in starts + passes)
        assert "Executed 1 test, with 0 failures" in text and " skipped" not in text.lower()
        assert "PINKHA_NATIVE_PREPARED_ASSOCIATION_PHASE_PASS " + name in text
        assert products() == build["compiledProducts"] and qualified.swift_sources() == source_before
        proof = json.loads((work / (name + "-result.json")).read_text())
        assert proof["phase"] == name and proof["baselineNativeClaims"] == 3 and proof["finalNativeClaims"] == 6
        assert proof["newDistinctClaims"] == 3 and proof["explicitSemanticConflicts"] == 1
        for key in ("historicalClaimsAndProvenanceUnchanged", "frozenObservedSetRetained", "interveningVariantRetained",
                    "unrelatedAssociationUnchanged", "originalMarkerBlockAndBodyUnchanged", "unknownPayloadFieldsUnchanged", "retiredLeaseRefused"):
            assert proof[key] is True
        assert proof["newObjects"] == proof["newEditorBlocks"] == proof["moduleInstalls"] == 0
        assert proof["originalSourceAdmissionPromoted"] is False and proof["independentClientSignatureVerification"] is False
        result["phases"].append({"phase": name, "result": "PASS", "seconds": round(time.monotonic() - before, 3),
                                 "proofSHA256": sha(work / (name + "-result.json")), "nativePID": native["p"].pid,
                                 "method": method, "newCompilerInvocations": 0})
        save()

    try:
        guard()
        assert minimum_root >= 2 * 1024**3 + 128 * MIB, "bounded private native account reserve"
        result["allocationBudget"] = {"rootInitialHeadroomBytes": 128 * MIB, "rootEmergencyFloorBytes": 2 * 1024**3,
            "developmentEmergencyFloorBytes": 512 * MIB, "copiedAccountLogicalBytes": 610070,
            "budgetMiB": {"copyRoundedUpper": 9, "nativeWAL": 64, "logs": 16, "proofs": 4, "skipBuildTemporary": 16, "slack": 19}}
        assert sha(CACHE_CUSTODY) == CACHE_CUSTODY_SHA and SCRATCH.is_symlink() and SCRATCH.resolve() == CACHE_TARGET
        custody = json.loads(CACHE_CUSTODY.read_text())
        assert custody["status"].startswith("PASS")
        result["cacheCustodyReceiptSHA256"] = CACHE_CUSTODY_SHA
        assert sha(CANONICAL_RECEIPT) == CANONICAL_SHA
        canonical = json.loads(CANONICAL_RECEIPT.read_text())
        assert canonical["status"] == "PASS" and canonical["allOwnedGroupsPositivelyAbsent"]
        policy = canonical["offlinePolicy"]
        assert policy["helperSHA256"] == OFFLINE_SHA
        assert policy["controls"]["tcpDenied"] and policy["controls"]["udpDenied"]
        assert policy["controls"]["noNewPrivileges"] and policy["controls"]["seccompFilterActive"]
        result["reusedOSDenialProbe"] = {"sourceReceiptSHA256": CANONICAL_SHA, "policy": policy, "newNativePIDFlagsChecked": True}
        result["nativeBefore"] = qualified.qualify_native()
        source_before = qualified.swift_sources()
        write(args.output / "swift-sources-before.json", source_before)
        assert sha(args.swift_receipt) == args.swift_receipt_sha
        build = json.loads(args.swift_receipt.read_text())
        assert sha(args.swift_receipt.with_name("source-before.json")) == build["sourceBeforeSHA256"]
        assert sha(args.swift_receipt.with_name("source-after.json")) == build["sourceAfterSHA256"]
        assert build["sourceBeforeSHA256"] == build["sourceAfterSHA256"], "compiled source closure changed"
        assert build["status"] == "PASS" and build["compiled"] and build["exitCode"] == 0 and build["sourceUnchanged"] and build["ownedGroupAbsent"]
        assert len(build["startLines"]) == len(build["passLines"]) == 3 and not build["failLines"]
        assert build["sourceCommit"] == result["sourceCommit"]
        assert source_before == json.loads(args.swift_receipt.with_name("source-after.json").read_text())
        assert products() == build["compiledProducts"]
        result["swiftBuildReceiptSHA256"] = args.swift_receipt_sha
        result["compiledProducts"] = build["compiledProducts"]
        for path, expected in BOUNDARY.items():
            assert source_before[path] == expected
        result["unchangedSharedPolicyBoundaryMembers"] = BOUNDARY
        result["componentEvidenceScope"] = "Retains original accepted component controls; this is a new actual native boundary proof, not complete prior build-closure equivalence"
        assert ARCHIVE.stat().st_size == 204378 and sha(ARCHIVE) == ARCHIVE_SHA
        result["sourceArchiveSHA256"] = ARCHIVE_SHA
        prefix = "peer-attempt1/alice/"
        copied, names, directories = [], set(), []
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            all_members = archive.getmembers()
            assert len(all_members) == 81
            members = [member for member in all_members if member.name.startswith(prefix)]
            assert len(members) == 23 and sum(member.size for member in members) == 610070
            for member in members:
                relative = PurePosixPath(member.name[len(prefix):])
                assert str(relative) not in ("", ".") and not relative.is_absolute() and ".." not in relative.parts
                assert str(relative) not in names and (member.isfile() or member.isdir())
                names.add(str(relative))
                target = private.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(mode=member.mode, parents=True, exist_ok=True)
                    directories.append((target, member.mode))
                else:
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open("xb") as destination:
                        digest = hashlib.sha256()
                        for chunk in iter(lambda: source.read(65536), b""):
                            digest.update(chunk); destination.write(chunk)
                        destination.flush(); os.fsync(destination.fileno())
                    os.chmod(target, member.mode)
                    assert target.stat().st_size == member.size and sha(target) == digest.hexdigest()
                    assert stat.S_IMODE(target.stat().st_mode) == member.mode
                    copied.append({"path": str(relative), "bytes": member.size, "mode": member.mode, "sha256": sha(target)})
            for target, mode in reversed(directories):
                os.chmod(target, mode)
                assert stat.S_IMODE(target.stat().st_mode) == mode
            fixture_members = [member for member in all_members if member.name == "network-attempt1/semantic-original-fixture.json"]
            assert len(fixture_members) == 1 and fixture_members[0].isfile() and fixture_members[0].size < 65536
            fixture_bytes = archive.extractfile(fixture_members[0]).read()
        assert hashlib.sha256(fixture_bytes).hexdigest() == FIXTURE_SHA
        (work / "semantic-original-fixture.json").write_bytes(fixture_bytes)
        fixture = json.loads(fixture_bytes)
        assert fixture["creatorAccountID"] == ACCOUNT and fixture["spaceID"] == SPACE and fixture["objectID"] == OBJECT
        write(args.output / "private-copy-inventory.json", copied)
        result["retainedCopy"] = {"accountInitialized": False, "spaceCreated": False, "originalArchiveOpenedReadOnly": True,
                                   "members": 23, "files": len(copied), "logicalBytes": 610070,
                                   "inventorySHA256": sha(args.output / "private-copy-inventory.json")}
        result["runID"] = uuid.uuid4().hex
        config = args.output / "offline-native-config.yml"
        config.write_text("network:\n  nodeconfPath: " + str(NATIVE / "source/internal/config/nodeconf-prod.yml") +
                          "\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n")
        result["configSHA256"] = sha(config)
        assert sha(NATIVE / "source/internal/config/nodeconf-prod.yml") == CONFIG_SHA
        phase = "execute explicit seed, B, frozen A and exact retry"
        warm = start_native("execute-native", config)
        test("execute", warm)
        rows = json.loads((work / "dispatch-ledger.json").read_text())
        assert len(rows) == 5
        assert [row["name"] for row in rows] == ["explicit-new-seed", "intervening-B", "frozen-A", "exact-A-retry", "retired-lease-execute"]
        assert [row["state"] for row in rows] == ["acknowledged-validated"] * 4 + ["confirmed-retired-lease-refusal"]
        phase = "intentional native SIGKILL after validated mutations"
        assert warm["p"].poll() is None and not absent(warm)
        warm["row"]["intentionalCrash"] = True
        save()
        os.killpg(warm["p"].pid, signal.SIGKILL)
        warm["p"].wait(timeout=10)
        close(warm, expected=-signal.SIGKILL, terminate=False)
        phase = "new OS-offline process and cold exact retry"
        cold = start_native("reopen-native", config)
        assert cold["p"].pid != warm["p"].pid
        test("reopen", cold)
        close(cold)
        assert (work / "execute-claims.json").read_bytes() == (work / "reopen-claims.json").read_bytes()
        assert (work / "execute-body.json").read_bytes() == (work / "reopen-body.json").read_bytes() == (work / "baseline-body.json").read_bytes()
        rows = json.loads((work / "dispatch-ledger.json").read_text())
        assert len(rows) == 7
        assert [row["name"] for row in rows] == ["explicit-new-seed", "intervening-B", "frozen-A", "exact-A-retry", "retired-lease-execute", "cold-exact-A-retry", "retired-lease-reopen"]
        assert [row["state"] for row in rows] == ["acknowledged-validated"] * 4 + ["confirmed-retired-lease-refusal", "acknowledged-validated", "confirmed-retired-lease-refusal"]
        assert len({row["claimID"] for row in rows}) == len({row["operationID"] for row in rows}) == 3
        assert all(rows[index][key] == rows[2][key] for index in (3, 4, 5, 6) for key in ("operationID", "claimID", "payloadSHA256", "observed"))
        assert rows[0]["observed"] == [] and rows[1]["observed"] == rows[2]["observed"] == [rows[0]["claimID"]]
        result.update(baselineClaims=3, finalClaims=6, newDistinctClaims=3, nativeWriteRequestsAcknowledged=5,
                      retiredLeaseRefusals=2, semanticConflictsRetained=1, newObjects=0, newEditorBlocks=0, moduleInstalls=0,
                      dispatchLedgerSHA256=sha(work / "dispatch-ledger.json"), claimsSHA256=sha(work / "execute-claims.json"),
                      bodySHA256=sha(work / "execute-body.json"), uniqueNativeMethods=1, nativeTestInvocations=2)
        result["status"] = "PASS"
    except BaseException as error:
        result["status"] = "FAIL"
        result["failedPhase"] = phase
        result["errors"].append({"type": type(error).__name__, "message": str(error)})
        (args.output / "traceback.txt").write_text(traceback.format_exc())
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for child in reversed(children):
            if child["row"].get("groupPositivelyAbsent") is True:
                continue
            try:
                close(child, expected=-signal.SIGKILL if child["row"]["intentionalCrash"] else 0)
            except BaseException as error:
                result["status"] = "FAIL"
                result["errors"].append({"cleanup": child["row"]["name"], "error": str(error)})
        result["allOwnedGroupsPositivelyAbsent"] = all(child["row"].get("groupPositivelyAbsent") is True for child in children)
        try:
            assert sha(Path(__file__)) == controller_sha and sha(COMMON) == COMMON_SHA
            result["controllerSHA256"] = controller_sha
            assert sha(ARCHIVE) == ARCHIVE_SHA
            result["originalArchiveUnchanged"] = True
            if (work / "semantic-original-fixture.json").exists():
                assert sha(work / "semantic-original-fixture.json") == FIXTURE_SHA
            if source_before is not None:
                after = qualified.swift_sources()
                write(args.output / "swift-sources-after.json", after)
                assert after == source_before
                result["swiftSourcesUnchanged"] = True
            if build is not None:
                assert products() == build["compiledProducts"]
                result["compiledProductsUnchanged"] = True
            if "nativeBefore" in result:
                result["nativeAfter"] = qualified.qualify_native()
                assert result["nativeAfter"] == result["nativeBefore"]
            if result["status"] == "PASS":
                assert len(result["processes"]) == len(result["testLaunches"]) == len(result["phases"]) == 2
                assert [row["exitCode"] for row in result["processes"]] == [-signal.SIGKILL, 0]
                assert all(row["exitCode"] == 0 for row in result["testLaunches"])
                assert sum(row["intentionalCrash"] for row in result["processes"]) == 1
            assert result["allOwnedGroupsPositivelyAbsent"]
        except BaseException as error:
            result["status"] = "FAIL"
            result["errors"].append({"finalIntegrity": str(error)})
        save()
    print(json.dumps({"status": result["status"], "result": str(args.output / "result.json"),
                      "sha256": sha(args.output / "result.json"), "seconds": result["seconds"], "errors": result["errors"]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
