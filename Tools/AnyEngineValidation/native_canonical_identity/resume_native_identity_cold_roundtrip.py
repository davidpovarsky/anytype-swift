#!/usr/bin/env python3
"""Run the one native identity component method in a new process and cold offline.
All native stores remain private. Neither this controller nor its result grants
source capture authority or whole-space migration acceptance.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shlex, shutil, signal, socket, subprocess, time

WORKTREE = Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
MAC_SCRIPT = "/Users/m1/builds/pinkha-c-recovered-native-cli-20261125/control/resume_native_identity_cold_process.py"
MAC_SHA = "315f652393a87c3215e52dfd547768d8cf203a96b1c4d55171cc1faa06e908a1"
TEST_SHA = "7e179640bed26e2fdf77d2a37f8c4a936f09a7ecd5ededdc516340b53948f277"
TEST = "AnyDestinationNativeIdentityTests.testActualCanonicalIdentityDescriptorsAndColdReopen"
BASE = Path("/mnt/development/projects/evidence/migration-final-20261125/compiled-resolver")
ORIGINAL = Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156")
SSH = ["sudo", "-n", "-u", "ubuntu", "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def remote(code, timeout=30):
    reply = subprocess.run(SSH + ["scaleway-mac", "/opt/homebrew/bin/python3.12", "-B", "-"],
        input=code, text=True, capture_output=True, timeout=timeout)
    if reply.returncode:
        raise RuntimeError("owned remote command failed; original private stderr retained by caller")
    return reply.stdout
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mac-output", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    prior = Path("/mnt/development/projects/evidence/migration-final-20261125/native-canonical-identity/attempt1")
    prior_pins = {
        "result.json": "9c42be9188d7b3a57309ad58184a15ebf43f4c192693ee929cb49c3c6166153a",
        "execute.log": "6a34d0b885140dde5c6196f21c5190b315d2b4640e0001592b5890c7ee72fe23",
        "native-controller-result-final.json": "1782e42c48bf396d4d4885524db804dbd8ab9552292c5e2b2c42fd363bb3960d",
        "swift-source.json": "a278c52ab78992fb4c941b3d08c6f658df181d5b05236742cf8219fb4bb33d66",
        "execute-runtime-original.json": "06c965057e18eed81f7c5525ba2ab05c87c382eecd251b95dd35d960aac59700",
        "private-work/plan.json": "fffc4c2b7f1fc3b5fb1ea28662a1c0e9d2923a82b4c3281661c9b94648acc247",
        "private-work/component-input.json": "5a7f6e3cee17b057f2f73b123e2c1a82052d1e2cd8efb8959e2f417219d7e6ad",
        "private-work/execute-identities.json": "a93c6340584db67c6ffb7215743d46c389cb91fa06e85dd52e6a4448ee86a0c3",
        "private-work/execute-verification.json": "35169a60d1d62fa9aa52ca54248feea6d76b6081d49311198bb907b791f27d03"
    }
    assert all(not (prior / p).is_symlink() and sha(prior / p) == digest for p, digest in prior_pins.items())
    prior_result = json.loads((prior / "result.json").read_bytes())
    assert prior_result["result"] == "FAIL" and len(prior_result["phases"]) == 1
    assert prior_result["phases"][0]["exitCode"] == 1 and prior_result["phases"][0]["sourceUnchanged"] is True
    actual_log = (prior / "execute.log").read_text()
    assert actual_log.count("Test Case 'AnyDestinationNativeIdentityTests.testActualCanonicalIdentityDescriptorsAndColdReopen' passed (59.458 seconds)") == 1
    assert "Executed 1 test, with 0 failures (0 unexpected)" in actual_log and "skipped" not in actual_log.lower()
    assert "NATIVE_IDENTITY_COMPONENT descriptors=3 target_types=1 target_objects=2 exact_query_count=2 source_admission=false whole_space_migration=false phase=execute" in actual_log
    assert "posix_spawn error: No such file or directory (2)" in actual_log and "PinkhaAnyHostTests (Swift Testing)" in actual_log
    assert " failed (" not in actual_log
    work = prior / "private-work"
    assert not (work / "reopen-identities.json").exists()
    tmp = args.output / "tmp"; tmp.mkdir(mode=0o700)
    native = forward = current_test = None
    native_log = forward_log = None
    started = time.monotonic()
    result = {"protocol": "pinkha-native-canonical-identity-cold-qualification-v1",
              "scope": "original canonical descriptor correspondence and three-operation native component",
              "sourceAdmissionPromoted": False, "wholeSpaceMigration": False,
              "result": "RUNNING", "phases": [], "macOutput": args.mac_output,
              "priorOriginalControllerStatus": "FAIL", "reusedOriginalXCTestMethods": 1,
              "originalXCTestExecuted": 1, "originalXCTestPassed": 1, "originalXCTestSkipped": 0,
              "priorOriginalProofs": prior_pins, "nativeCreationReplayed": False}
    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    def interrupted(signum, frame):
        raise RuntimeError("owned orchestration interrupted")
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    def stop_owned(process):
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
                raise RuntimeError("owned process required forced termination")
    module_roots = ["Modules/PinkhaAnyHost", "Modules/PinkhaAnyEngine",
                    "Modules/PinkhaAnyIntegration", "Modules/PinkhaKit"]
    listed = subprocess.run(["sudo", "-n", "-u", "ubuntu", "git", "-C", str(WORKTREE),
        "ls-files", "-z", "--"] + module_roots, capture_output=True, check=True, timeout=15)
    paths = {p.decode() for p in listed.stdout.split(b"\0") if p}
    test_path = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeIdentityTests.swift"
    paths.add(test_path)
    assert sha(WORKTREE / test_path) == TEST_SHA
    before = {p: sha(WORKTREE / p) for p in sorted(paths) if (WORKTREE / p).is_file()}
    assert before == json.loads((prior / "swift-source.json").read_bytes()), "exact original compiled source closure required"
    (args.output / "swift-source.json").write_text(json.dumps(before, indent=2) + "\n")
    command = ["/usr/local/bin/swift", "test", "--skip-build", "--disable-swift-testing", "--cache-path", str(BASE / "swift-common-cache"),
               "--manifest-cache", "local", "-Xswiftc", "-module-cache-path", "-Xswiftc", str(BASE / "swift-module-cache"),
               "--package-path", str(WORKTREE / "Modules/PinkhaAnyHost"),
               "--scratch-path", "/tmp/pinkha-c-swift-cache-20261125",
               "--disable-sandbox", "--disable-automatic-resolution", "--jobs", "2", "--filter", TEST]
    (args.output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    try:
        source = WORKTREE / "Tools/AnyEngineValidation/native_canonical_identity/resume_native_identity_cold_process.py"
        assert sha(source) == MAC_SHA
        staged = remote("from pathlib import Path\nimport hashlib,json,os\np=Path(" + repr(MAC_SCRIPT) +
            ")\np.parent.mkdir(mode=0o700,exist_ok=True)\ns=" + repr(source.read_text()) +
            "\nif p.exists():assert p.read_text()==s\nelse:p.write_text(s);os.chmod(p,0o600)\n"
            "assert hashlib.sha256(p.read_bytes()).hexdigest()==" + repr(MAC_SHA) +
            "\nprint(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\n")
        result["stagedController"] = json.loads(staged)
        assert shutil.disk_usage(args.output).free > 768 * 1024**2
        native_log = (args.output / "native-controller.log").open("wb")
        native_command = SSH + ["scaleway-mac", "/opt/homebrew/bin/python3.12", "-B",
                               MAC_SCRIPT, "--output", args.mac_output]
        (args.output / "native-command.json").write_text(json.dumps(native_command, indent=2) + "\n")
        native = subprocess.Popen(native_command, stdout=native_log, stderr=subprocess.STDOUT, start_new_session=True)
        result["nativeSSHProcessID"] = native.pid; save()
        for phase in ("reopen",):
            item = {"phase": phase, "result": "RUNNING"}; result["phases"].append(item); save()
            expected = "execute" if phase == "execute" else "cold-offline"
            deadline = time.monotonic() + 120
            while True:
                if native.poll() is not None: raise RuntimeError("native process controller ended before phase readiness")
                raw = remote("from pathlib import Path\np=Path(" + repr(args.mac_output + "/runtime.json") +
                             ")\nprint(p.read_text() if p.exists() else '{}')\n")
                runtime = json.loads(raw)
                if runtime.get("phase") == expected: break
                if time.monotonic() >= deadline: raise RuntimeError("native phase readiness timeout")
                time.sleep(0.5)
            (args.output / (phase + "-runtime-original.json")).write_text(json.dumps(runtime, indent=2) + "\n")
            if forward is None:
                port = int(runtime["baseURL"].rsplit(":", 1)[1])
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0)); local = sock.getsockname()[1]
                forward_command = SSH + ["-N", "-L", "127.0.0.1:" + str(local) + ":127.0.0.1:" + str(port),
                    "-o", "ExitOnForwardFailure=yes", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2",
                    "scaleway-mac"]
                (args.output / "forward-command.json").write_text(json.dumps(forward_command, indent=2) + "\n")
                forward_log = (args.output / "forward.log").open("wb")
                forward = subprocess.Popen(forward_command, stdout=forward_log, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 15
                while True:
                    if forward.poll() is not None: raise RuntimeError("owned forwarding process exited")
                    try:
                        socket.create_connection(("127.0.0.1", local), timeout=.5).close(); break
                    except OSError:
                        if time.monotonic() >= deadline: raise RuntimeError("owned forwarding readiness timeout")
                        time.sleep(.2)
            runtime["baseURL"] = "http://127.0.0.1:" + str(local)
            fixture = args.output / (phase + "-fixture.json")
            fixture.write_text(json.dumps(runtime, indent=2) + "\n")
            assert all(sha(WORKTREE / p) == digest for p, digest in before.items()), "frozen source changed"
            env = os.environ.copy()
            env.update(TMPDIR=str(tmp), CLANG_MODULE_CACHE_PATH=str(BASE / "swift-module-cache"),
                PINKHA_DESTINATION_NATIVE_FIXTURE=str(fixture), PINKHA_DESTINATION_NATIVE_WORK=str(work),
                PINKHA_DESTINATION_NATIVE_PHASE=phase, PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE=str(ORIGINAL))
            phase_start = time.monotonic()
            with (args.output / (phase + ".log")).open("wb") as log:
                current_test = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                item.update(testPID=current_test.pid, nativePID=runtime["processID"]); save()
                try: exit_code = current_test.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    stop_owned(current_test); raise
            current_test = None
            log_bytes = (args.output / (phase + ".log")).read_bytes()
            log_text = log_bytes.decode(errors="replace")
            item.update(exitCode=exit_code, seconds=round(time.monotonic() - phase_start, 3),
                        logSHA256=hashlib.sha256(log_bytes).hexdigest(),
                        sourceUnchanged=all(sha(WORKTREE / p) == digest for p, digest in before.items()))
            assert exit_code == 0 and item["sourceUnchanged"], "actual Swift native phase failed"
            assert "Executed 1 test, with 0 failures" in log_text and "skipped" not in log_text.lower(), "one actual unskipped method required"
            assert "NATIVE_IDENTITY_COMPONENT descriptors=3 target_types=1 target_objects=2 exact_query_count=2 source_admission=false whole_space_migration=false phase=" + phase in log_text
            item["result"] = "PASS"; save()
            signal_name = "execute-complete" if phase == "execute" else "finish"
            remote("from pathlib import Path\np=Path(" + repr(args.mac_output + "/" + signal_name) +
                   ")\nassert not p.exists()\np.write_text('actual Swift phase passed\\n')\n")
        result["nativeControllerExitCode"] = native.wait(timeout=45)
        native_data = json.loads(remote("from pathlib import Path\nprint(Path(" + repr(args.mac_output + "/controller-result.json") + ").read_text())\n"))
        (args.output / "native-controller-result.json").write_text(json.dumps(native_data, indent=2) + "\n")
        assert result["nativeControllerExitCode"] == 0 and native_data["result"] == "COLD_PROCESS_CONTINUATION_PASS"
        assert len(native_data["processes"]) == 1
        prior_runtime = json.loads((prior / "execute-runtime-original.json").read_bytes())
        assert native_data["processes"][0]["pid"] != prior_runtime["processID"]
        assert all(p["exitCode"] == 0 and not p["forcedKill"] for p in native_data["processes"])
        assert (work / "execute-identities.json").read_bytes() == (work / "reopen-identities.json").read_bytes()
        result.update(result="PASS", identityComparisonSHA256=sha(work / "execute-identities.json"),
                      sourceUnchanged=all(sha(WORKTREE / p) == digest for p, digest in before.items()))
        assert all(sha(prior / p) == digest for p, digest in prior_pins.items()), "original evidence changed"
    except Exception as error:
        result.update(result="FAIL", errorType=type(error).__name__, error=str(error))
        try:
            remote("from pathlib import Path\np=Path(" + repr(args.mac_output) +
                   ")\nif p.is_dir():(p/'abort').write_text('external qualification failed\\n')\n")
        except Exception as cleanup_error: result["abortSignalError"] = type(cleanup_error).__name__
    finally:
        if current_test is not None:
            try: stop_owned(current_test)
            except Exception as error: result["testCleanupError"] = type(error).__name__; result["result"] = "FAIL"
        if native is not None:
            try: result["nativeControllerFinalExit"] = native.wait(timeout=45)
            except subprocess.TimeoutExpired:
                result["nativeCleanupError"] = "controller still active; account retained"; result["result"] = "FAIL"
            try:
                data = remote("from pathlib import Path\np=Path(" + repr(args.mac_output + "/controller-result.json") +
                              ")\nprint(p.read_text() if p.exists() else '{}')\n")
                (args.output / "native-controller-result-final.json").write_text(data)
            except Exception as error: result["nativeReceiptError"] = type(error).__name__; result["result"] = "FAIL"
        try: stop_owned(forward)
        except Exception as error: result["forwardCleanupError"] = type(error).__name__; result["result"] = "FAIL"
        if native_log: native_log.close()
        if forward_log: forward_log.close()
        save()
    print(json.dumps({k: result[k] for k in ("protocol", "result", "seconds", "sourceAdmissionPromoted", "wholeSpaceMigration")}))
    return 0 if result["result"] == "PASS" else 1
if __name__ == "__main__":
    raise SystemExit(main())
