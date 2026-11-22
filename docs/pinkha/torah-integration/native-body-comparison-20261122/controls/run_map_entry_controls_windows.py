#!/usr/bin/env python3
"""Only the new map-entry loss regression closure; prior results are retained."""
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
source, output = Path(args.source_root), Path(args.output_root)
output.mkdir(parents=True, exist_ok=False)
compiler = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
compiler_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
assert compiler_hash == "e1d0a0b20d95a92b22f4906e7ca331a7c8b89be86b2d9a2d215ac24f753e945a"
env = os.environ.copy()
env["PATH"] = r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin" + ";" + str(compiler.parent) + ";" + env.get("PATH", "")
paths = ["OriginalAnnotationNativeMapKeyGuard.swift", "NativeBodyMapEntryControls.swift", "map-entry-vectors.json"]
result = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "source_root": str(source), "output_root": str(output), "compiler": str(compiler),
          "compiler_sha256": compiler_hash, "status": "RUNNING", "commands": [],
          "prior_controls_rerun": 0, "native_executions": 0,
          "sources": [{"path": p, "sha256": hashlib.sha256((source / p).read_bytes()).hexdigest()} for p in paths]}


def save():
    (output / "RESULT.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def run(name, command, timeout):
    start = time.monotonic()
    p = subprocess.Popen(command, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out, cleanup = False, None
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill = subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, timeout=15)
        cleanup = {"pid": p.pid, "exit": kill.returncode}
        stdout, stderr = p.communicate(timeout=10)
    (output / (name + ".stdout.log")).write_bytes(stdout)
    (output / (name + ".stderr.log")).write_bytes(stderr)
    item = {"name": name, "args": command, "exit": p.returncode, "timed_out": timed_out,
            "seconds": round(time.monotonic() - start, 3),
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest()}
    if cleanup:
        item["owned_process_cleanup"] = cleanup
    result["commands"].append(item)
    save()
    if timed_out or p.returncode:
        raise RuntimeError(name + " failed; no automatic replay")
    return stdout


save()
try:
    binary = output / "NativeBodyMapEntryControls.exe"
    run("compile", [str(compiler), "-swift-version", "6", "-parse-as-library"]
        + [str(source / p) for p in paths[:2]] + ["-o", str(binary)], 90)
    result["controls"] = json.loads(run("controls", [str(binary), str(source / paths[2])], 20))
    assert result["controls"]["tests_run"] == 13 and result["controls"]["native_executions"] == 0
    result["status"] = "PASS_NEW_MAP_ENTRY_LOSS_CONTROLS"
except Exception as error:
    result["status"], result["error"] = "FAILED", str(error)
finally:
    result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    print(json.dumps(result))
    if result["status"] == "FAILED":
        raise SystemExit(1)
