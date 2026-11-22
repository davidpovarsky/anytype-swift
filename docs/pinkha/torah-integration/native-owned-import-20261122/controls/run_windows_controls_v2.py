"""One bounded compile-and-run of the new owned upload/import unit closure.

The dependencies are explicitly recorded component fixtures. This execution
cannot qualify native account lifecycle, real upload, saved body or ACK.
"""
import base64
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

packet = globals().get("INPUT_PACKET")
if packet is None:
    packet = json.loads(Path(sys.argv[1]).read_bytes())
destination = Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-owned-import-controls-20261122-v2")
destination.mkdir(exist_ok=False)
module = destination / "module"
module.mkdir()
evidence = destination / "evidence"
evidence.mkdir()
go = Path(r"C:\Program Files\Go\bin\go.exe")
environment = dict(os.environ)
environment.update({"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off", "GOENV": "off", "GOFLAGS": ""})
deadline = time.monotonic() + 480
result = {
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "RUNNING", "native_executions": 0, "prior_suites_replayed": 0,
    "scope": packet["source_manifest"]["scope"],
    "fixture_scope": packet["source_manifest"]["fixture_scope"],
    "compiler": str(go), "compiler_sha256": hashlib.sha256(go.read_bytes()).hexdigest(),
    "source_manifest": packet["source_manifest"],
    "commands": [], "tests": [], "tests_run": 0,
    "expected_leaf_controls": len(packet["source_manifest"]["expected_tests"]),
}


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def command(name, args, timeout):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("owned execution deadline exceeded before command")
    started = time.monotonic()
    timed_out = False
    with (evidence / (name + ".stdout.log")).open("wb") as stdout, (evidence / (name + ".stderr.log")).open("wb") as stderr:
        process = subprocess.Popen(args, cwd=module, env=environment, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=min(timeout, remaining))
        except subprocess.TimeoutExpired:
            timed_out = True
            killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
            (evidence / (name + ".owned-timeout-cleanup.stdout.log")).write_bytes(killed.stdout)
            (evidence / (name + ".owned-timeout-cleanup.stderr.log")).write_bytes(killed.stderr)
            code = process.wait(timeout=15)
    record = {"name": name, "args": args, "exit": code, "timed_out": timed_out,
              "pid": process.pid, "process_wait_completed": True,
              "seconds": round(time.monotonic() - started, 3)}
    for stream in ["stdout", "stderr"]:
        record[stream] = identity(evidence / (name + "." + stream + ".log"))
    result["commands"].append(record)
    return code


try:
    names = set()
    for item in packet["files"]:
        relative = Path(item["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert item["path"] not in names
        names.add(item["path"])
        data = gzip.decompress(base64.b64decode(item["gzip_b64"]))
        assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
        path = module / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (evidence / "SOURCE.json").write_text(json.dumps(packet["source_manifest"], indent=2) + "\n", encoding="utf-8")
    assert command("go-version", [str(go), "version"], 15) == 0
    result["go_version"] = (evidence / "go-version.stdout.log").read_text().strip()
    assert result["go_version"] == "go version go1.25.6 windows/amd64"
    # Both fixture closures must compile before any new control can execute.
    for name, package in [("uploader", "./core/files/fileuploader"), ("importer", "./core/block/import")]:
        binary = destination / (name + "-unit.test.exe")
        code = command("compile-" + name, [str(go), "test", "-x", "-c", "-o", str(binary), package], 180)
        if code != 0:
            raise RuntimeError(name + " fixture closure compile failed; no control was executed")
        result[name + "_unit_binary"] = identity(binary)
    code = command("controls", [str(go), "test", "-json", "-count=1", "-timeout", "25s", "./core/files/fileuploader", "./core/block/import"], 90)
    events = [json.loads(line) for line in (evidence / "controls.stdout.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = {(item["package"], item["name"]) for item in packet["source_manifest"]["expected_tests"]}
    starts, outcomes = {}, {}
    for event in events:
        if "Test" not in event:
            continue
        key = (event["Package"], event["Test"])
        if event["Action"] == "run":
            starts[key] = starts.get(key, 0) + 1
        elif event["Action"] in ("pass", "fail", "skip"):
            outcomes.setdefault(key, []).append(event["Action"])
    result["tests"] = [{"package": key[0], "name": key[1], "starts": starts.get(key, 0), "outcomes": outcomes.get(key, [])} for key in sorted(expected | starts.keys() | outcomes.keys())]
    result["tests_run"] = sum(starts.values())
    result["tests_passed"] = sum(values == ["pass"] for values in outcomes.values())
    result["tests_failed"] = sum("fail" in values for values in outcomes.values())
    result["tests_skipped"] = sum("skip" in values for values in outcomes.values())
    assert code == 0
    assert starts.keys() == expected == outcomes.keys()
    assert all(starts[key] == 1 and outcomes[key] == ["pass"] for key in expected)
    result["source_after"] = []
    for item in packet["source_manifest"]["module_files"]:
        actual = identity(module / item["path"])
        assert actual == {"bytes": item["bytes"], "sha256": item["sha256"]}
        result["source_after"].append({"path": item["path"], **actual})
    result["status"] = "PASS_NEW_OWNED_UPLOAD_IMPORT_UNIT_BOUNDARIES"
except Exception as error:
    result["status"] = "FAILED_NEW_UNIT_CLOSURE_NO_AUTOMATIC_REPLAY"
    result["error"] = type(error).__name__ + ": " + str(error)
finally:
    result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (evidence / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"directory": str(destination), "status": result["status"], "tests_run": result["tests_run"], "tests_passed": result.get("tests_passed", 0), "tests_failed": result.get("tests_failed", 0), "tests_skipped": result.get("tests_skipped", 0), "native_executions": 0, "prior_suites_replayed": 0, "error": result.get("error"), "result_sha256": identity(evidence / "RESULT.json")["sha256"]}))
