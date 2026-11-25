#!/usr/bin/env python3
"""Execute exactly one compiled source-order test, replay and new-process offline.
This qualifies a six-operation component, never whole-space source admission.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, signal, socket, subprocess, time

WORKTREE = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
BUILD = Path("/mnt/development/projects/evidence/migration-final-20261125/native-type-order/native-build1")
CACHE = Path("/tmp/pinkha-c-swift-cache-20261125")
ORIGINAL = Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
MAC_SCRIPT = "/Users/m1/builds/pinkha-c-recovered-native-cli-20261125/control/run_native_type_order_process.py"
MAC_SHA = "5e364545ebb58c52ff95fe14bd60a0723542e5e3cdae598adfc342f617868169"
TEST = "AnyDestinationNativeTypeOrderTests.testActualSourceTypeRanksPersistThroughPreparedReplayAndColdCatalog"
TEST_PATH = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeTypeOrderTests.swift"
TEST_SHA = "996be987157333db0b220d5bd6ca5fe69ec5415b0c9c754e778153277182e435"
BUILD_SHA = "559b781c854738136f83efb80de68b0e83094b2e26d0079ac01f0ef84f323d54"
SOURCE_SHA = "084dbdb85d95cc172b49769e13a14b80e3fd766e11e75098cb84d197578b3895"
DEPS_SHA = "5a401246574e5a03b4abd63b3081677e1bee61955e59abe7ad67bca6bfa76b61"
BINARIES = {
    "PinkhaAnyHostTests-test-runner": "c59f815f64bfbc782ac69562984b7b42ac9fff21ec4f8c9c06789ea16b5bf987",
    "PinkhaAnyHostTests.so": "b899d9155c66be38f1dc869a32f8f13e7bb117a462c965352a9f13206b631028",
}
SSH = ["sudo", "-n", "-u", "ubuntu", "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, value): p.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
def remote(code, timeout=30):
    r = subprocess.run(SSH + ["scaleway-mac", "/opt/homebrew/bin/python3.12", "-B", "-"],
        input=code, text=True, capture_output=True, timeout=timeout)
    if r.returncode: raise RuntimeError("owned remote command failed; private stderr: " + r.stderr[-2000:])
    return r.stdout
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mac-output", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    assert args.mac_output.startswith("/Users/m1/builds/pinkha-c-native-type-order-20261125/")
    assert ".." not in Path(args.mac_output).parts
    work = args.output / "private-work"; work.mkdir(mode=0o700)
    temporary = args.output / "tmp"; temporary.mkdir(mode=0o700)
    started = time.monotonic()
    native = forward = current_test = None
    native_log = forward_log = None
    known_absent = set()
    result = {"protocol": "pinkha-native-source-type-order-roundtrip-v1",
        "scope": "three actual original type ranks; six native prepared operations, replay and cold-offline catalog",
        "sourceCommit": "d1fc2eb3dc22da9c294716fcae01c958e9622e4b",
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
        assert built["status"] == "PASS_BUILD_ONLY_NO_NATIVE_CALLS" and built["returncode"] == 0
        assert built["sourceCommit"] == result["sourceCommit"] and built["sourceUnchanged"] and built["dependenciesUnchanged"]
        assert built["ownedGroupPositivelyAbsent"] and built["counts"] == {"failed": 0, "passed": 0, "skipped": 0}
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
        return {"sourceFileCount": len(expected), "buildReceiptSHA256": BUILD_SHA,
            "sourceManifestSHA256": SOURCE_SHA, "dependenciesSHA256": DEPS_SHA, "compiledProducts": BINARIES}
    command = ["/usr/local/bin/swift", "test", "--skip-build", "--package-path",
        str(WORKTREE / "Modules/PinkhaAnyHost"), "--scratch-path", str(CACHE), "--jobs", "2", "--filter", TEST]
    write(args.output / "command.json", command)
    try:
        result["inputsBefore"] = verify_inputs(); save()
        source = WORKTREE / "Tools/AnyEngineValidation/native_type_order/run_native_type_order_process.py"
        assert sha(source) == MAC_SHA
        staged = remote("from pathlib import Path\nimport hashlib,os,json\np=Path(" + repr(MAC_SCRIPT) +
            ")\np.parent.mkdir(mode=0o700,exist_ok=True)\ns=" + repr(source.read_text()) +
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
                PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE=str(ORIGINAL))
            phase_started = time.monotonic()
            with (args.output / (phase + ".log")).open("wb") as log:
                current_test = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                item.update(testPID=current_test.pid, nativePID=runtime["processID"]); save()
                current_test.wait(timeout=600)
                code = observe_exit(current_test)
            item["testGroupPositivelyAbsent"] = current_test.pid in known_absent
            current_test = None
            log_bytes = (args.output / (phase + ".log")).read_bytes()
            log_text = log_bytes.decode(errors="replace")
            item.update(exitCode=code, seconds=round(time.monotonic() - phase_started, 3),
                logSHA256=hashlib.sha256(log_bytes).hexdigest(), inputsAfter=verify_inputs())
            save()
            assert code == 0, "original compiled Swift phase failed"
            assert "Executed 1 test, with 0 failures" in log_text and "skipped" not in log_text.lower()
            assert "Test Case '" + TEST + "' passed" in log_text
            marker = "NATIVE_TYPE_ORDER_COMPONENT target_types=3 native_editor_parts=3 prepared_operations=6 exact_type_handles=3 source_admission=false whole_space_migration=false phase=" + phase
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
        assert (work / "execute-type-order.json").read_bytes() == (work / "reopen-type-order.json").read_bytes()
        result.update(result="PASS", typeOrderComparisonSHA256=sha(work / "execute-type-order.json"),
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
