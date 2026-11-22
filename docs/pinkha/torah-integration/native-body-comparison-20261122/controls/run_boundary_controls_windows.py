#!/usr/bin/env python3
"""Execute only this new source closure; never replay the historical 52 tests."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", required=True)
parser.add_argument("--output-root", required=True)
args = parser.parse_args()
source = Path(args.source_root)
output = Path(args.output_root)
output.mkdir(parents=True, exist_ok=False)
compiler = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
compiler_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
assert compiler_hash == "e1d0a0b20d95a92b22f4906e7ca331a7c8b89be86b2d9a2d215ac24f753e945a"
env = os.environ.copy()
env["PATH"] = r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin" + ";" + str(compiler.parent) + ";" + env.get("PATH", "")
sources = [
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveLayout.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeMapKeyGuard.swift",
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAnnotationCreateRecovery.swift",
    "controls/TorahAnnotationNativeIdentity.swift",
    "controls/NativeBodyBoundaryControls.swift",
]
parses = [
    "OriginalEditorFramework/OriginalAnnotationNativeSnapshotWire.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift",
    "OriginalEditorFramework/AnytypeOriginalEditorNativeBodyReadback.swift",
    "Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift",
]
result = {
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_root": str(source), "output_root": str(output),
    "compiler": str(compiler), "compiler_sha256": compiler_hash,
    "scope": "new affected body boundary/policy controls and syntax; no old suites rerun; native executions=0",
    "native_executions": 0, "commands": [], "status": "RUNNING",
    "sources": [{"path": p, "sha256": hashlib.sha256((source / p).read_bytes()).hexdigest()}
                for p in sources + parses + ["controls/boundary-vectors.json"]],
}


def save():
    (output / "RESULT.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def run(name, command, timeout):
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out, cleanup = False, None
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        # Kill only this runner's exact owned process tree, never a process-name
        # search or another ongoing build/qualification operation.
        killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
        cleanup = {"pid": process.pid, "exit": killed.returncode,
                   "stdout": killed.stdout.decode(errors="replace"), "stderr": killed.stderr.decode(errors="replace")}
        stdout, stderr = process.communicate(timeout=10)
    (output / (name + ".stdout.log")).write_bytes(stdout)
    (output / (name + ".stderr.log")).write_bytes(stderr)
    row = {"name": name, "args": command, "exit": process.returncode, "timed_out": timed_out,
           "seconds": round(time.monotonic() - start, 3),
           "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(stderr).hexdigest()}
    if cleanup:
        row["owned_process_cleanup"] = cleanup
    result["commands"].append(row)
    save()
    if timed_out or process.returncode:
        raise RuntimeError(name + " failed or timed out; no automatic replay")
    return stdout


save()
try:
    binary = output / "NativeBodyBoundaryControls.exe"
    run("compile", [str(compiler), "-swift-version", "6", "-parse-as-library"]
        + [str(source / p) for p in sources] + ["-o", str(binary)], 120)
    report = json.loads(run("controls", [str(binary), str(source / "controls/boundary-vectors.json")], 30))
    result["controls"] = report
    assert report["tests_run"] == 40 and report["native_executions"] == 0
    for index, path in enumerate(parses, 1):
        run("parse-" + str(index), [str(compiler), "-frontend", "-parse", str(source / path)], 25)
    result["status"] = "PASS_NEW_BOUNDARY_CONTROLS_AND_FOUR_SYNTAX_PARSES"
except Exception as error:
    result["status"], result["error"] = "FAILED", str(error)
finally:
    result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    print(json.dumps({"status": result["status"], "output_root": str(output),
                      "tests_run": result.get("controls", {}).get("tests_run", 0),
                      "commands": result["commands"], "error": result.get("error")}))
    if result["status"] == "FAILED":
        raise SystemExit(1)
