#!/usr/bin/env python3
"""Execute full historical source preservation and compare a new native offline process.
This qualifies original byte preservation, never unsupported type usability or whole-source semantic admission.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, signal, socket, stat, subprocess, time

WORKTREE = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
BUILD = Path("/mnt/development/projects/evidence/migration-final-20261125/full-source-preservation/native-shared-build1")
CACHE = Path("/tmp/pinkha-c-swift-cache-20261125")
ORIGINAL = Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
MAC_SCRIPT = "/Users/m1/development/anytype-c-active-20261125/native-source-preservation/control/run_native_source_preservation_process.py"
MAC_SHA = "a377976508ec48782becdf5c9592219dcf4ac5ac23e2cb79fd08d84f99de15d4"
TEST = "AnyDestinationNativeSourcePreservationTests.testAllOriginalHeadsAndFileSurviveColdNativeReopen"
TEST_PATH = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeSourcePreservationTests.swift"
TEST_SHA = "bb3f62826b2df0c39ffe24d123cff038ca72d5b6391922f5b9abf4e295ce83a6"
BUILD_SHA = "44e16b16b9205995b9d62dad4dcc80eeaafcb9171c1e434ef90ebf4cef21c0ae"
SOURCE_SHA = "9006edab7e34612314db28a5549b9c1b5f13732b6c5d304140fe76168ad1305e"
DEPS_SHA = "25ac8fdff3cc6d56dee3cc021decd29048fb84d0f147bae5eade1e70801c911e"
BINARIES = {
    "PinkhaAnyHostTests-test-runner": "28c2cd2c4935bd59a8de614539115d1d5f54c573abf1dac5f9df43c4db426083",
    "PinkhaAnyHostTests.so": "2a2cc0fc297934da985c1513bae3bff6c585f53e964ec2ed0c1e52b1b70b2310",
}
SSH = ["sudo", "-n", "-u", "ubuntu", "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value):
    pending=p.with_name(p.name+".pending")
    pending.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n");pending.replace(p)
def remote(code, timeout=30):
    r = subprocess.run(SSH + ["scaleway-mac", "/opt/homebrew/bin/python3.12", "-B", "-"],
        input=code, text=True, capture_output=True, timeout=timeout)
    if r.returncode: raise RuntimeError("owned remote command failed; private stderr: " + r.stderr[-2000:])
    return r.stdout
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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mac-output", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    assert args.mac_output.startswith("/Users/m1/development/anytype-c-active-20261125/native-source-preservation/")
    assert ".." not in Path(args.mac_output).parts
    work = args.output / "private-work"; work.mkdir(mode=0o700)
    temporary = args.output / "tmp"; temporary.mkdir(mode=0o700)
    started = time.monotonic()
    native = forward = current_test = None
    native_log = forward_log = None
    known_absent = set()
    result = {"protocol": "pinkha-native-full-source-preservation-roundtrip-v1",
        "scope": "182 actual native operations; supported current Pages, all159 historical source heads, reversible file, exact links and cold-offline reopen",
        "sourceCommit": "0dd6c6f7a7ed4b89eb18797949ad1f369a22091e",
        "sourceAdmissionPromoted": False, "wholeSpaceMigration": False,
        "result": "RUNNING", "phases": [], "macOutput": args.mac_output, "errors": []}
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
        result["resourcePolicy"]={"maximumPhaseSeconds":1800,"estimatedPrivateOutputBytes":64*1024**2,
                                  "minimumOutputFreeBytes":64*1024**2,"nativeBuilds":0}
        result["inputsBefore"] = verify_inputs(); save()
        source = WORKTREE / "Tools/AnyEngineValidation/native_source_preservation/run_native_source_preservation_process.py"
        assert sha(source) == MAC_SHA
        staged = remote("from pathlib import Path\nimport hashlib,os,json\np=Path(" + repr(MAC_SCRIPT) +
            ")\np.parent.mkdir(mode=0o700,parents=True,exist_ok=True)\ns=" + repr(source.read_text()) +
            "\nif p.exists():assert p.read_text()==s\nelse:p.write_text(s);os.chmod(p,0o600)\n" +
            "assert hashlib.sha256(p.read_bytes()).hexdigest()==" + repr(MAC_SHA) +
            "\nprint(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\n")
        result["stagedController"] = json.loads(staged)
        native_command = SSH + ["scaleway-mac", "/opt/homebrew/bin/python3.12", "-B",
            MAC_SCRIPT, "--output", args.mac_output]
        write(args.output / "native-command.json", native_command)
        native_log = (args.output / "native-controller.log").open("wb")
        native = subprocess.Popen(native_command, stdout=native_log, stderr=subprocess.STDOUT, start_new_session=True)
        result["nativeSSHProcessID"] = native.pid; save()
        for phase in ("execute", "reopen"):
            item = {"phase": phase, "result": "RUNNING"}; result["phases"].append(item); save()
            expected_phase = "execute" if phase == "execute" else "cold-offline"
            deadline = time.monotonic() + 150
            while True:
                if native.poll() is not None:
                    observe_exit(native)
                    raise RuntimeError("native controller exited before phase readiness")
                runtime = json.loads(remote("from pathlib import Path\np=Path(" + repr(args.mac_output + "/runtime.json") +
                    ")\nprint(p.read_text() if p.exists() else '{}')\n"))
                if runtime.get("phase") == expected_phase: break
                if time.monotonic() >= deadline: raise RuntimeError("native phase readiness timeout")
                time.sleep(.5)
            write(args.output / (phase + "-runtime-original.json"), runtime)
            if forward is None:
                native_port = int(runtime["baseURL"].rsplit(":", 1)[1])
                assert runtime["baseURL"] == "http://127.0.0.1:" + str(native_port)
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0)); local_port = sock.getsockname()[1]
                forward_command = SSH + ["-N", "-L", "127.0.0.1:" + str(local_port) + ":127.0.0.1:" + str(native_port),
                    "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2",
                    "scaleway-mac"]
                write(args.output / "forward-command.json", forward_command)
                forward_log = (args.output / "forward.log").open("wb")
                forward = subprocess.Popen(forward_command, stdout=forward_log, stderr=subprocess.STDOUT, start_new_session=True)
                limit = time.monotonic() + 15
                while True:
                    if forward.poll() is not None:
                        observe_exit(forward); raise RuntimeError("owned forwarding process exited")
                    try: socket.create_connection(("127.0.0.1", local_port), timeout=.5).close(); break
                    except OSError:
                        if time.monotonic() >= limit: raise RuntimeError("owned forwarding readiness timeout")
                        time.sleep(.2)
            runtime["baseURL"] = "http://127.0.0.1:" + str(local_port)
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
                phase_deadline=time.monotonic()+1800
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
            remote("from pathlib import Path\np=Path(" + repr(args.mac_output + ("/execute-complete" if phase == "execute" else "/finish")) +
                ")\nassert not p.exists()\np.write_text('actual original compiled phase passed\\n')\n")
        native.wait(timeout=45)
        result["nativeControllerExitCode"] = observe_exit(native)
        native_data = json.loads(remote("from pathlib import Path\nprint(Path(" +
            repr(args.mac_output + "/controller-result.json") + ").read_text())\n"))
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
            remote("from pathlib import Path\np=Path(" + repr(args.mac_output) +
                ")\nif p.is_dir():(p/'abort').write_text('external qualification failed\\n')\n")
        except Exception as cleanup_error: result["errors"].append({"abort": type(cleanup_error).__name__})
    finally:
        try: stop_owned(current_test)
        except Exception as error: result["errors"].append({"testCleanup": type(error).__name__})
        if native is not None:
            try:
                native.wait(timeout=45); result["nativeControllerFinalExit"] = observe_exit(native)
            except Exception as error: result["errors"].append({"nativeCleanup": type(error).__name__})
            try:
                raw = remote("from pathlib import Path\np=Path(" + repr(args.mac_output + "/controller-result.json") +
                    ")\nprint(p.read_text() if p.exists() else '{}')\n")
                (args.output / "native-controller-result-final.json").write_text(raw)
            except Exception as error: result["errors"].append({"nativeReceipt": type(error).__name__})
        try: stop_owned(forward)
        except Exception as error: result["errors"].append({"forwardCleanup": type(error).__name__})
        for label, stream in (("native", native_log), ("forward", forward_log)):
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
