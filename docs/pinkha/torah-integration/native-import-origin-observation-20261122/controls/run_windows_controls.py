"""One bounded execution of the new observation unit closure on real Go."""
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
destination = Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-import-origin-controls-20261122-v1")
destination.mkdir(exist_ok=False)
module = destination / "module"
module.mkdir()
evidence = destination / "evidence"
evidence.mkdir()
go = Path(r"C:\Program Files\Go\bin\go.exe")
environment = dict(os.environ)
environment.update({"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOWORK": "off", "GOENV": "off", "GOFLAGS": ""})
result = {
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "RUNNING", "native_executions": 0, "prior_suites_replayed": 0,
    "scope": packet["source_manifest"]["scope"],
    "compiler": str(go), "compiler_sha256": hashlib.sha256(go.read_bytes()).hexdigest(),
    "source_manifest": packet["source_manifest"], "product_files": packet["product_files"],
    "commands": [], "tests": [], "tests_run": 0,
    "expected_leaf_controls": 50,
}


def command(name, args, timeout):
    started = time.monotonic()
    timed_out = False
    with (evidence / (name + ".stdout.log")).open("wb") as stdout, (evidence / (name + ".stderr.log")).open("wb") as stderr:
        process = subprocess.Popen(args, cwd=module, env=environment, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
            (evidence / (name + ".owned-timeout-cleanup.stdout.log")).write_bytes(killed.stdout)
            (evidence / (name + ".owned-timeout-cleanup.stderr.log")).write_bytes(killed.stderr)
            code = process.wait(timeout=15)
    record = {"name": name, "args": args, "exit": code, "timed_out": timed_out, "seconds": round(time.monotonic() - started, 3)}
    for stream in ["stdout", "stderr"]:
        record[stream + "_sha256"] = hashlib.sha256((evidence / (name + "." + stream + ".log")).read_bytes()).hexdigest()
    result["commands"].append(record)
    return code


try:
    for item in packet["files"]:
        relative = Path(item["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        data = gzip.decompress(base64.b64decode(item["gzip_b64"]))
        assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
        path = module / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    assert command("go-version", [str(go), "version"], 15) == 0
    result["go_version"] = (evidence / "go-version.stdout.log").read_text().strip()
    assert result["go_version"] == "go version go1.25.6 windows/amd64"
    code = command("controls", [str(go), "test", "-json", "-count=1", "-timeout", "25s", "./core/block/import/..."], 180)
    events = [json.loads(line) for line in (evidence / "controls.stdout.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    outcomes = {event["Test"]: event["Action"] for event in events if "Test" in event and event["Action"] in ("pass", "fail", "skip")}
    leaves = sorted(name for name in outcomes if not any(other.startswith(name + "/") for other in outcomes))
    result["tests"] = [{"name": name, "status": outcomes[name].upper()} for name in leaves]
    result["tests_run"] = len(leaves)
    result["tests_passed"] = sum(outcomes[name] == "pass" for name in leaves)
    result["tests_failed"] = sum(outcomes[name] == "fail" for name in leaves)
    result["tests_skipped"] = sum(outcomes[name] == "skip" for name in leaves)
    assert code == 0 and len(leaves) == result["expected_leaf_controls"] and all(outcomes[name] == "pass" for name in leaves)
    result["status"] = "PASS_NATIVE_IMPORT_ORIGIN_UNIT_CONTROLS"
except Exception as error:
    result["status"] = "FAILED_NEW_UNIT_CLOSURE_NO_AUTOMATIC_REPLAY"
    result["error"] = type(error).__name__ + ": " + str(error)
finally:
    result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (evidence / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"directory": str(destination), "status": result["status"], "tests_run": result["tests_run"], "tests_passed": result.get("tests_passed", 0), "tests_failed": result.get("tests_failed", 0), "tests_skipped": result.get("tests_skipped", 0), "native_executions": 0, "prior_suites_replayed": 0, "error": result.get("error"), "result_sha256": hashlib.sha256((evidence / "RESULT.json").read_bytes()).hexdigest()}))
