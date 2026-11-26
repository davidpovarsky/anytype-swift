#!/usr/bin/env python3
"""Execute full historical source preservation and compare a new native offline process.
This qualifies original byte preservation, never unsupported type usability or whole-source semantic admission.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, signal, socket, stat, subprocess, sys, time

WORKTREE = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
BUILD = Path("/var/lib/pinkha-c-native-preservation-20261126/native-shared-build-linux1")
CACHE = Path("/tmp/pinkha-c-swift-cache-20261125")
ORIGINAL = Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
PROCESS_SCRIPT = Path(__file__).resolve().with_name("resume_native_source_preservation_linux_process.py")
PROCESS_SHA = "349726aa8a85787af8524c9f0f02a8141cfe622592c7ef9f9929bf74e9603e59"
TEST = "AnyDestinationNativeSourcePreservationTests.testAllOriginalHeadsAndFileSurviveColdNativeReopen"
TEST_PATH = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeSourcePreservationTests.swift"
TEST_SHA = "4b89b5873c75f7d13096219e07dd83a0c83cd96d94021fb8c62948759563c6d7"
BUILD_SHA = "c98bf8875f16b9cf07d0663609a936e8fade42c2e2477472c9252544d8374562"
SOURCE_SHA = "bde84f2a7066242cc5abf9461b232dc22067ff92dcb448b36c9d9356400d7358"
DEPS_SHA = "25ac8fdff3cc6d56dee3cc021decd29048fb84d0f147bae5eade1e70801c911e"
BINARIES = {
    "PinkhaAnyHostTests-test-runner": "28c2cd2c4935bd59a8de614539115d1d5f54c573abf1dac5f9df43c4db426083",
    "PinkhaAnyHostTests.so": "2c86b12a7d9eff7b2f2011f6a1117b25ecfb9a19eb78b3196b8fe698e704578a",
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value):
    pending=p.with_name(p.name+".pending")
    pending.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n");pending.replace(p)
def verify_original():
    index = ORIGINAL.parent / "original156-member-index.json"
    assert index.is_file() and not index.is_symlink()
    index_bytes = index.read_bytes()
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    assert index_sha == "30420980bd3261a9e7284f7427ab47d8dc98f44e342549ea4d8c39a80073712b"
    assert ORIGINAL.resolve() == ORIGINAL and ORIGINAL.is_dir() and not ORIGINAL.is_symlink()
    root_before = ORIGINAL.stat()
    rows = json.loads(index_bytes)
    expected = set()
    total = 0
    for row in rows:
        relative = row["path"]
        path = Path(relative)
        assert not path.is_absolute() and path.as_posix() == relative and "\\" not in relative and "\0" not in relative
        assert all(v not in ("", ".", "..") for v in relative.split("/")) and relative not in expected
        expected.add(relative)
        cursor = ORIGINAL
        for component in path.parts[:-1]:
            cursor = cursor / component
            assert stat.S_ISDIR(cursor.lstat().st_mode)
        p = ORIGINAL / relative
        before = p.lstat()
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == row["bytes"]
        assert 0 <= before.st_size <= 32 * 1024**2 and sha(p) == row["sha256"]
        after = p.lstat()
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns")
        assert tuple(getattr(before, x) for x in fields) == tuple(getattr(after, x) for x in fields)
        total += before.st_size
    actual = {p.relative_to(ORIGINAL).as_posix() for p in ORIGINAL.rglob("*") if not p.is_dir() or p.is_symlink()}
    assert actual == expected
    root_after = ORIGINAL.stat()
    assert (root_before.st_dev, root_before.st_ino, root_before.st_mode) == (root_after.st_dev, root_after.st_ino, root_after.st_mode)
    assert sha(index) == index_sha
    return {"indexSHA256":index_sha,"originalMemberCount":len(rows),"originalBytes":total,"unchanged":True}

def verify_recovery():
    root=WORKTREE/"docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export"
    pinned={
        "historical156-binding.json":"3434ad74ec339f1d08818e2cb0bac069ec479c8e2f55e411754c63b31c6964b4",
        "receipt.json":"b4561fa708141c463fce941ba4e266e42d12760d81cc63524d1cb96766ad7eb6",
        "descriptors/export.json":"50458de19c0c9c8ae0bfc1b9cca1b6c5e29fbcf53d63bf32c5caabd0a3358ebb"}
    assert root.resolve()==root and not root.is_symlink()
    for relative,digest in pinned.items():
        p=root/relative
        assert p.is_file() and not p.is_symlink() and p.stat().st_size<=4*1024**2 and sha(p)==digest
    export=json.loads((root/"descriptors/export.json").read_bytes())
    paths=set()
    for row in export["Descriptors"]:
        for kind in ["Protobuf","JSONView"]:
            item=row[kind];relative=item["Path"]
            assert relative not in paths and Path(relative).name==relative and ".." not in relative and "\\" not in relative
            paths.add(relative);p=root/"descriptors"/relative
            assert p.is_file() and not p.is_symlink() and p.stat().st_size==item["Bytes"] and sha(p)==item["SHA256"]
    assert len(paths)==14
    producer=WORKTREE/"Tools/AnyEngineValidation/native_file_peer/retained-scheduling-45492064232/producer-result.json"
    assert producer.is_file() and not producer.is_symlink() and sha(producer)=="10dcb731241232985f626fcb8d084ec8a138c9e0aeffa46190f417d2da05c157"
    return {"bindingSHA256":pinned["historical156-binding.json"],"descriptorFiles":14,
            "originalProducerFAILUnchanged":True,"capturedMembersReplaced":False}

PRIOR = Path("/mnt/development/projects/evidence/migration-final-20261125/full-source-preservation/native-roundtrip-resume1")
CUSTODY = PRIOR.parent / "native-resume1-custody"
PLAN_SHA = "4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930"
def read_pinned(path, digest):
    assert path.resolve() == path and not path.is_symlink() and path.is_file()
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    identity = lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns)
    assert before.st_nlink == 1 and identity(before) == identity(after)
    assert hashlib.sha256(raw).hexdigest() == digest
    return raw
def retained_files(root):
    assert root.resolve() == root and not root.is_symlink() and root.is_dir()
    rows,identities={},{}
    for path in [root]+sorted(root.rglob("*")):
        before=path.lstat()
        assert path.resolve()==path and not path.is_symlink()
        name="." if path==root else path.relative_to(root).as_posix()
        identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns)
        if stat.S_ISREG(before.st_mode):
            assert before.st_nlink==1 and before.st_size<=32*1024**2
            raw=path.read_bytes()
            rows[name]={"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"mode":stat.S_IMODE(before.st_mode)}
        else:assert stat.S_ISDIR(before.st_mode)
        assert identity(before)==identity(path.lstat());identities[name]=identity(before)
    return rows,identities
def admit_interrupted_journal(destination):
    raw=read_pinned(PRIOR/"result.json","ea2bc4b7df3988953dfe4b507fa7232809d00862c7c83a41766d4d9e3fe565a4")
    prior=json.loads(raw)
    assert prior["result"]=="FAIL" and prior["errors"]==[]
    assert prior["ownedGroupsPositivelyAbsent"]==[3595365,3595501,3595514]
    assert len(prior["phases"])==1 and prior["phases"][0]["result"]=="FAIL"
    assert prior["phases"][0]["phase"]=="execute" and prior["phases"][0]["exitCode"]==1
    assert prior["phases"][0]["testGroupPositivelyAbsent"] is True
    assert prior["inputsBefore"]==prior["inputsFinally"]==prior["phases"][0]["inputsAfter"]
    assert prior["priorInterruption"]["originalReceiptSHA256"]=="adf64ea4e7b2e4bd2ffbe681395d1fdb30bed5125f62375975e2f58b5bfda44b"
    assert prior["priorInterruption"]["interruptedPlanSHA256"]==PLAN_SHA
    assert prior["priorInterruption"]["newAccountOrSpaceCreated"] is False
    log=read_pinned(PRIOR/"execute.log","514c1c1f538e3644b0d5aed0b6c620a1f9d8f85ade7a14837c382201c8a769bd").decode()
    assert 'threw error "accountChanged"' in log and "Executed 1 test, with 1 failure" in log
    native=json.loads(read_pinned(PRIOR/"native-controller-result-final.json",
        "af92f890954d9fb676296b3b19d8320f614fbf1556921037ce0ecfa31438225b"))
    assert native["result"]=="FAIL" and native["error"]=="runtime disk emergency"
    assert native["minimumFreeBytes"]==2127994880 and native["phases"]==[]
    assert native["processes"]==[{"name":"resumed-native","pid":70048,"offline":False,
        "forcedKill":False,"exitCode":0,"groupPositivelyAbsent":True}]
    offhost=json.loads(read_pinned(CUSTODY/"offhost-receipt.json",
        "ab149dc3ba2a64e774ac75bc6dcc362ec661e20e3b78c1f5725bf67538196b72"))
    assert offhost["status"]=="PASS_OFFHOST_LATEST_FAILED_NATIVE_AND_ORACLE_JOURNAL"
    assert offhost["originalOutcome"]=="FAIL" and offhost["runtimeCalls"]==0
    read_pinned(CUSTODY/"original-native-account-and-evidence.tar.gz","9824faee754cc8a2e81de7b4bf0432c116ed983816eb0f6523aa670fba3dea2d")
    read_pinned(CUSTODY/"oracle-original-roundtrip.tar.gz","4190af1390fe8fa1abd4528601f3dd2355834287c87c4af50af9c1adb6e282fa")
    expected=json.loads(read_pinned(CUSTODY/"oracle-original-inventory.json",
        "a8eef7c4b16067ea9584833d18442bfa1611a4a8b7f614ae1d20128a8b5a11b2"))
    expected_ids=json.loads(read_pinned(CUSTODY/"oracle-original-identities.json",
        "9cd614d8698df4a397ed05171603a8e3ac4f8d31700613699da3834b8dc04fc3"))
    before,identities=retained_files(PRIOR)
    assert before=={k:{f:v[f] for f in ("sha256","bytes","mode")} for k,v in expected.items() if v["kind"]=="file"}
    assert set(identities)==set(expected_ids)
    assert all(list(identities[k])==expected_ids[k] for k in identities)
    work=PRIOR/"private-work"
    assert sha(work/"source-preservation-plan.json")==PLAN_SHA
    assert sha(work/"original-source.pinkha-heart-source")=="5d72e36849884da3da3fe9ddde0a01f49a03cde3b417f49456e3558bea8db463"
    assert not (work/"execute-content.json").exists() and not (work/"execute-mappings.json").exists()
    assert not (PRIOR/"reopen.log").exists()
    import base64
    entries=[]
    for path in (work/"journal").rglob("entry-*.json"):
        wrapper=json.loads(path.read_bytes());content=base64.b64decode(wrapper["content"],validate=True)
        assert hashlib.sha256(content).hexdigest()==wrapper["contentSHA256"]
        entries.append(json.loads(content))
    assert len(entries)==63 and sorted(row["index"] for row in entries)==list(range(63))
    assert sorted(len(row["receipts"]) for row in entries)==[1]+[2]*62
    work_before,work_ids=retained_files(work)
    assert destination.parent.resolve()==destination.parent and not destination.exists()
    shutil.copytree(work,destination,copy_function=shutil.copy2)
    copied,copied_ids=retained_files(destination)
    assert copied==work_before and set(copied_ids)==set(work_ids)
    assert all(copied_ids[name][2]==work_ids[name][2] for name in work_ids)
    assert retained_files(work)==(work_before,work_ids)
    assert retained_files(PRIOR)==(before,identities)
    return {"originalResult":"FAIL","originalReceiptSHA256":hashlib.sha256(raw).hexdigest(),
        "originalNativeResourceFailure":True,"nativeAccountAndJournalBackedUpOffhost":True,
        "originalFilesUnchanged":True,"copiedJournalFilesEqual":True,"historicalGroupsProbed":0,
        "initialCheckpointEntries":63,"initialEntriesWithTwoReceipts":62,
        "interruptedPlanSHA256":PLAN_SHA,"newAccountOrSpaceCreated":False,
        "latestMacAccountUsed":True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    assert str(args.output).startswith("/var/lib/pinkha-c-native-preservation-20261126/")
    assert args.output.resolve() == args.output and ".." not in args.output.parts
    native_output = args.output / "native"
    work = args.output / "private-work"
    temporary = args.output / "tmp"; temporary.mkdir(mode=0o700)
    started = time.monotonic()
    native = current_test = None
    native_log = None
    known_absent = set()
    result = {"protocol": "pinkha-native-full-source-preservation-linux-resume-roundtrip-v1",
        "scope": "182 actual native operations; supported current Pages, all159 historical source heads, reversible file, exact links and cold-offline reopen",
        "sourceCommit": "d3f03d2a1e9b1bd31cfe82d4d3aa895df78c72ea",
        "sourceAdmissionPromoted": False, "wholeSpaceMigration": False,
        "result": "RUNNING", "phases": [], "nativeOutput": str(native_output), "errors": [],
        "nativePlatform":"linux-arm64","sameInterruptedMacAccount":True}
    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        write(args.output / "result.json", result)
    def absent(group):
        if group in known_absent: return True
        try: os.killpg(group, 0)
        except ProcessLookupError:
            known_absent.add(group); return True
        return False
    def observe_exit(child):
        code = child.wait(timeout=5)
        if not absent(child.pid): raise RuntimeError("owned child exited but its group remains present")
        return code
    def stop_owned(child):
        if child is None or child.pid in known_absent: return
        if child.poll() is not None:
            # Do not signal an historical identifier after the original child exited.
            if not absent(child.pid): raise RuntimeError("exited child's group unresolved; no signal sent")
            return
        if not absent(child.pid): os.killpg(child.pid, signal.SIGTERM)
        try: child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            if not absent(child.pid): os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
            raise RuntimeError("owned child required forced termination")
        assert absent(child.pid), "owned group remains after termination"
    def interrupted(signum, frame): raise RuntimeError("owned orchestration interrupted")
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    def verify_inputs():
        assert sha(BUILD / "result.json") == BUILD_SHA
        built = json.loads((BUILD / "result.json").read_bytes())
        assert built["status"] == "PASS_BUILD_ONLY_NO_NATIVE_CALLS" and built["exitCode"] == 0
        assert built["sourceCommit"] == result["sourceCommit"] and built["sourceUnchanged"] and built["dependenciesUnchanged"]
        assert built["ownedGroupAbsent"] and built["testsInvoked"] == 0 and built["actualNativeCalls"] == 0
        assert sha(BUILD / "original.log") == built["logSHA256"]
        assert sha(BUILD / "source-before.json") == SOURCE_SHA
        assert sha(BUILD / "source-after.json") == SOURCE_SHA
        assert sha(BUILD / "dependencies-before.json") == DEPS_SHA
        assert sha(BUILD / "dependencies-after.json") == DEPS_SHA
        expected = json.loads((BUILD / "source-before.json").read_bytes())
        roots = ["Modules/PinkhaAnyHost", "Modules/PinkhaAnyEngine", "Modules/PinkhaAnyIntegration", "Modules/PinkhaKit"]
        listed = subprocess.run(["git", "-c", "safe.directory=" + str(WORKTREE), "-C", str(WORKTREE),
            "ls-files", "-z", "--"] + roots, capture_output=True, check=True, timeout=15)
        actual = {p.decode() for p in listed.stdout.split(b"\0") if p and (p.endswith(b".swift") or p.endswith(b"/Package.resolved"))}
        assert set(expected) == actual
        assert all(not (WORKTREE / p).is_symlink() and sha(WORKTREE / p) == value for p, value in expected.items())
        assert sha(WORKTREE / TEST_PATH) == TEST_SHA
        dependencies = json.loads((CACHE / "workspace-state.json").read_bytes())["object"]["dependencies"]
        assert dependencies == json.loads((BUILD / "dependencies-before.json").read_bytes())
        products = CACHE / "out/Products/Debug-linux-aarch64"
        assert all(sha(products / p) == value for p, value in BINARIES.items())
        return {"originalCapture": verify_original(), "recovery":verify_recovery(), "sourceFileCount": len(expected), "buildReceiptSHA256": BUILD_SHA,
            "sourceManifestSHA256": SOURCE_SHA, "dependenciesSHA256": DEPS_SHA, "compiledProducts": BINARIES}
    command = ["/usr/local/bin/swift", "test", "--skip-build", "--package-path",
        str(WORKTREE / "Modules/PinkhaAnyHost"), "--scratch-path", str(CACHE), "--jobs", "2", "--filter", TEST]
    write(args.output / "command.json", command)
    try:
        assert shutil.disk_usage(args.output).free >= 128*1024**2, "bounded private evidence headroom"
        result["resourcePolicy"]={"maximumPhaseSeconds":1500,"estimatedPrivateOutputBytes":64*1024**2,
                                  "minimumOutputFreeBytes":64*1024**2,"nativeBuilds":0}
        result["inputsBefore"] = verify_inputs(); save()
        result["priorInterruption"] = admit_interrupted_journal(work); save()
        assert PROCESS_SCRIPT.is_file() and not PROCESS_SCRIPT.is_symlink() and sha(PROCESS_SCRIPT) == PROCESS_SHA
        assert sha(PROCESS_SCRIPT.with_name("linux_outbound_denial.py")) == "6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1"
        native_command = [sys.executable, "-B", str(PROCESS_SCRIPT), "--output", str(native_output)]
        write(args.output / "native-command.json", native_command)
        native_log = (args.output / "native-controller.log").open("wb")
        native = subprocess.Popen(native_command, stdout=native_log, stderr=subprocess.STDOUT, start_new_session=True)
        result["nativeControllerProcessID"] = native.pid; save()
        for phase in ("execute", "reopen"):
            item = {"phase": phase, "result": "RUNNING"}; result["phases"].append(item); save()
            expected_phase = "execute" if phase == "execute" else "cold-offline"
            deadline = time.monotonic() + 150
            while True:
                if native.poll() is not None:
                    observe_exit(native)
                    raise RuntimeError("native controller exited before phase readiness")
                runtime_path = native_output / "runtime.json"
                runtime = json.loads(runtime_path.read_bytes()) if runtime_path.is_file() else {}
                if runtime.get("phase") == expected_phase: break
                if time.monotonic() >= deadline: raise RuntimeError("native phase readiness timeout")
                time.sleep(.5)
            assert runtime["interruptedPlanSHA256"] == PLAN_SHA
            write(args.output / (phase + "-runtime-original.json"), runtime)
            assert runtime["nativePlatform"] == "linux-arm64"
            assert runtime["binarySHA256"] == "1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636"
            native_port = int(runtime["baseURL"].rsplit(":", 1)[1])
            assert runtime["baseURL"] == "http://127.0.0.1:" + str(native_port)
            fixture = args.output / (phase + "-fixture.json"); write(fixture, runtime)
            verify_inputs()
            env = os.environ.copy()
            env.update(TMPDIR=str(temporary), PINKHA_DESTINATION_NATIVE_FIXTURE=str(fixture),
                PINKHA_DESTINATION_NATIVE_WORK=str(work), PINKHA_DESTINATION_NATIVE_PHASE=phase,
                PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE=str(ORIGINAL),
                PINKHA_RECOVERED_DEFINITION_EVIDENCE=str(WORKTREE/"docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export"),
                PINKHA_RECOVERED_DEFINITION_REPOSITORY=str(WORKTREE))
            phase_started = time.monotonic()
            with (args.output / (phase + ".log")).open("wb") as log:
                current_test = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                item.update(testPID=current_test.pid, nativePID=runtime["processID"]); save()
                phase_deadline=time.monotonic()+1500
                while current_test.poll() is None:
                    assert time.monotonic()<phase_deadline,"bounded full-preservation phase"
                    assert shutil.disk_usage(args.output).free>=64*1024**2,"owned qualification output emergency floor"
                    time.sleep(.5)
                code = observe_exit(current_test)
            item["testGroupPositivelyAbsent"] = current_test.pid in known_absent
            current_test = None
            log_bytes = (args.output / (phase + ".log")).read_bytes()
            log_text = log_bytes.decode(errors="replace")
            item.update(exitCode=code, seconds=round(time.monotonic() - phase_started, 3),
                logSHA256=hashlib.sha256(log_bytes).hexdigest(), inputsAfter=verify_inputs())
            item["result"] = "FAIL"
            save()
            assert code == 0, "original compiled Swift phase failed"
            assert "Executed 1 test, with 0 failures" in log_text and "skipped" not in log_text.lower()
            assert "Test Case '" + TEST + "' passed" in log_text
            marker = "NATIVE_FULL_SOURCE_PRESERVATION prepared_operations=182 original_pages=2 native_heads=159 snapshot_objects=156 restored_members=332 source_admission=false all_imported_types_usable=false phase=" + phase
            assert marker in log_text
            item["result"] = "PASS"; save()
            signal_path = native_output / ("execute-complete" if phase == "execute" else "finish")
            with signal_path.open("x") as stream: stream.write("actual original compiled phase passed\n")
        native.wait(timeout=45)
        result["nativeControllerExitCode"] = observe_exit(native)
        native_data = json.loads((native_output / "controller-result.json").read_bytes())
        write(args.output / "native-controller-result.json", native_data)
        assert result["nativeControllerExitCode"] == 0 and native_data["result"] == "PROCESS_LIFECYCLE_PASS"
        assert len(native_data["processes"]) == 2 and len({p["pid"] for p in native_data["processes"]}) == 2
        assert all(p["exitCode"] == 0 and not p["forcedKill"] and p["groupPositivelyAbsent"] for p in native_data["processes"])
        assert (work / "execute-content.json").read_bytes() == (work / "reopen-content.json").read_bytes()
        result.update(result="PASS", fullSourcePreservationComparisonSHA256=sha(work / "execute-content.json"),
            inputsAfter=verify_inputs())
    except BaseException as error:
        result.update(result="FAIL", errorType=type(error).__name__, error=str(error))
        try:
            if native_output.is_dir(): (native_output / "abort").write_text("external qualification failed\n")
        except Exception as cleanup_error: result["errors"].append({"abort": type(cleanup_error).__name__})
    finally:
        try: stop_owned(current_test)
        except Exception as error: result["errors"].append({"testCleanup": type(error).__name__})
        if native is not None:
            try:
                native.wait(timeout=45); result["nativeControllerFinalExit"] = observe_exit(native)
            except Exception as error: result["errors"].append({"nativeCleanup": type(error).__name__})
            try:
                source_receipt = native_output / "controller-result.json"
                raw = source_receipt.read_bytes() if source_receipt.is_file() else b"{}"
                (args.output / "native-controller-result-final.json").write_bytes(raw)
            except Exception as error: result["errors"].append({"nativeReceipt": type(error).__name__})
        for label, stream in (("native", native_log),):
            if stream:
                try: stream.close()
                except Exception as error: result["errors"].append({label + "LogClose": type(error).__name__})
        result["ownedGroupsPositivelyAbsent"] = sorted(known_absent)
        if result["errors"]: result["result"] = "FAIL"
        try: result["inputsFinally"] = verify_inputs()
        except Exception as error: result.update(result="FAIL", finalInputsError=type(error).__name__)
        save()
    print(json.dumps({k: result[k] for k in ("protocol", "result", "seconds", "sourceAdmissionPromoted", "wholeSpaceMigration")}))
    return 0 if result["result"] == "PASS" else 1
if __name__ == "__main__": raise SystemExit(main())
