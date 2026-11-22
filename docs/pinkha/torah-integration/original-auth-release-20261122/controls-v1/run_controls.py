import argparse, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, time

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    packet = pathlib.Path(__file__).resolve().parent
    repo = pathlib.Path(args.worktree).resolve()
    out = pathlib.Path(args.output).resolve()
    out.mkdir(exist_ok=False)
    shutil.copyfile(__file__, out / "ACTUAL_RUNNER.py")
    manifest_bytes = (packet / "EXECUTION_INPUTS.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if sha(pathlib.Path(__file__).read_bytes()) != manifest["runner_sha256"]:
        raise RuntimeError("reviewed runner changed")
    shutil.copyfile(packet / "EXECUTION_INPUTS.json", out / "EXECUTION_INPUTS.json")
    commands = []
    result = {"status": "STARTING", "scope": manifest["scope"], "commands": commands,
              "manifest_sha256": sha(manifest_bytes), "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def save():
        (out / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    def command(label, argv, timeout):
        row = {"label": label, "argv": argv, "cwd": str(out), "status": "STARTING",
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        commands.append(row); save()
        stdout = out / (label + ".stdout"); stderr = out / (label + ".stderr")
        with stdout.open("wb") as o, stderr.open("wb") as e:
            process = subprocess.Popen(argv, cwd=out, stdout=o, stderr=e, stdin=subprocess.DEVNULL)
            row.update(status="RUNNING", pid=process.pid); save()
            try:
                returncode = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                row["timed_out"] = True; save()
                cleanup = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                         capture_output=True, timeout=15)
                (out / (label + ".cleanup.stdout")).write_bytes(cleanup.stdout)
                (out / (label + ".cleanup.stderr")).write_bytes(cleanup.stderr)
                row["cleanup_exit"] = cleanup.returncode
                process.wait(timeout=15)
                returncode = process.returncode
        row.update(status="TIMED_OUT" if timed_out else "COMPLETED", exit_code=returncode,
                   timed_out=timed_out, parent_reaped=process.poll() is not None,
                   finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   stdout_sha256=sha(stdout.read_bytes()), stderr_sha256=sha(stderr.read_bytes()))
        save()
        if timed_out or returncode:
            raise RuntimeError(label + " failed; timed_out=" + str(timed_out) + " exit=" + str(returncode))
        return stdout.read_bytes()
    def verify_inputs():
        for entry in manifest["canonical_inputs"]:
            if entry["kind"] == "reviewed_candidate":
                data = (repo / entry["path"]).read_bytes()
            else:
                completed = subprocess.run(["git", "show", entry["commit"] + ":" + entry["path"]],
                                           cwd=repo, capture_output=True, timeout=20)
                if completed.returncode:
                    raise RuntimeError("immutable original input unavailable: " + entry["path"])
                data = completed.stdout
            if sha(data) != entry["sha256"]:
                raise RuntimeError("canonical input changed: " + entry["path"])
        for entry in manifest["compiled_inputs"]:
            if sha((packet / entry["path"]).read_bytes()) != entry["sha256"]:
                raise RuntimeError("compiled input changed: " + entry["path"])
        if sha((packet / "Controls.swift").read_bytes()) != manifest["controls_sha256"]:
            raise RuntimeError("control source changed")
    save()
    try:
        verify_inputs()
        result["canonical_and_compiled_inputs_before"] = "PASS"; save()
        compiler = shutil.which("swiftc")
        if compiler is None:
            raise RuntimeError("original configured Swift compiler unavailable")
        compiler = str(pathlib.Path(compiler).resolve())
        result["compiler_path"] = compiler
        result["compiler_executable_sha256"] = sha(pathlib.Path(compiler).read_bytes()); save()
        version = command("compiler-version", [compiler, "--version"], 20).decode(errors="replace")
        if "Swift version 6.3.3" not in version:
            raise RuntimeError("unreviewed Swift toolchain version")
        result["compiler_version"] = version
        compiled = out / "compiled-inputs"; compiled.mkdir()
        copied = []
        for entry in manifest["compiled_inputs"]:
            destination = compiled / pathlib.Path(entry["path"]).name
            shutil.copyfile(packet / entry["path"], destination)
            if sha(destination.read_bytes()) != entry["sha256"]:
                raise RuntimeError("compiled copy changed")
            copied.append({"path": str(destination), "sha256": entry["sha256"],
                           "bytes": destination.stat().st_size})
        control_copy = compiled / "Controls.swift"
        shutil.copyfile(packet / "Controls.swift", control_copy)
        copied.append({"path": str(control_copy), "sha256": sha(control_copy.read_bytes()),
                       "bytes": control_copy.stat().st_size})
        result["actual_compiled_copies"] = copied; save()
        binary = out / "original-account-transition-controls.exe"
        argv = [compiler, "-swift-version", "5", "-strict-concurrency=complete",
                "-parse-as-library", "-j", "1", "-whole-module-optimization", "-Onone"]
        argv += [entry["path"] for entry in copied]
        argv += ["-o", str(binary)]
        command("compile-six-new-controls", argv, 240)
        result["binary_before_execution"] = {"path": str(binary), "bytes": binary.stat().st_size,
                                              "sha256": sha(binary.read_bytes())}; save()
        output = command("execute-six-new-controls", [str(binary)], 45).decode()
        markers = [line[len("CONTROL_RESULT="):] for line in output.splitlines()
                   if line.startswith("CONTROL_RESULT=")]
        if len(markers) != 1:
            raise RuntimeError("expected exactly one actual result")
        actual = json.loads(markers[0])
        cases = actual.get("cases", [])
        names = [row["name"] for row in cases]
        if names != manifest["case_names"] or len(cases) != 6 or any(row["status"] != "PASS" for row in cases):
            raise RuntimeError("exact six new cases did not all pass")
        if [line[5:] for line in output.splitlines() if line.startswith("PASS ")] != manifest["case_names"]:
            raise RuntimeError("raw PASS lines differ from exact six named cases")
        if actual["status"] != "PASS":
            raise RuntimeError("actual control process did not report PASS")
        result["actual_cases"] = actual
        result["binary_after_execution_sha256"] = sha(binary.read_bytes())
        if result["binary_after_execution_sha256"] != result["binary_before_execution"]["sha256"]:
            raise RuntimeError("executed binary changed")
        for entry in copied:
            if sha(pathlib.Path(entry["path"]).read_bytes()) != entry["sha256"]:
                raise RuntimeError("compiled copy changed after execution")
        verify_inputs()
        result["canonical_and_compiled_inputs_after"] = "PASS"
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = str(error)
    finally:
        result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(json.dumps({"status": result["status"], "result_path": str(out / "RESULT.json"),
                      "result_sha256": sha((out / "RESULT.json").read_bytes()),
                      "error": result.get("error"), "new_cases": len(result.get("actual_cases", {}).get("cases", [])),
                      "native_calls": 0}))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
