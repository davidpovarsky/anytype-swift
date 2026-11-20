#!/usr/bin/env python3
"""Build and run production T5 on an explicitly disposable, pinned native v7 fixture."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
NATIVE_SHA = "12c7fb62164c830410331aabf616194edb0711a083250f8e8dd34c3cba52078b"
MANIFEST_SHA = "62a13310a474d93d728258d0631618b09056a20c4454bd7be303f3ec071fb77c"
SCOPE = "production_t5_native_workflow_with_memory_creation_journal"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    result = {}
    for name in ("PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"):
        module = ROOT / "Modules" / name
        paths = [module / "Package.swift", module / "Package.resolved"]
        paths += list((module / "Sources").rglob("*.swift"))
        for path in sorted(set(paths)):
            if path.is_file():
                result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result

def bounded(command, *, cwd, env, stdout, stderr, seconds):
    windows = os.name == "nt"
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
        start_new_session=not windows,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if windows else 0)
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        # This PID belongs to the process just created by this runner.
        if process.poll() is None:
            if windows:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            else:
                os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=30)
        raise

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("swift", "native-binary", "native-manifest"):
        parser.add_argument("--" + key, type=Path, required=True)
    for key in ("endpoint", "account-id", "space-id"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true")
    args = parser.parse_args()
    if not args.allow_disposable_writes:
        parser.error("Requires the caller's explicit owned disposable-fixture authorization")
    if sha(args.native_binary) != NATIVE_SHA or sha(args.native_manifest) != MANIFEST_SHA:
        parser.error("The binary and source manifest must be the recorded native v7 pair")
    source = manifest()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    evidence = ROOT / "docs/any-engine-port/evidence/20261119"
    evidence.mkdir(parents=True, exist_ok=True)
    prefix = evidence / ("native-torah-workflow-" + stamp)
    env = dict(os.environ)
    env["PATH"] = str(args.swift.parent) + os.pathsep + env.get("PATH", "")
    record = {
        "schemaVersion": 1, "status": "FAIL", "startedAt": stamp,
        "scope": SCOPE, "sourceManifest": source,
        "nativeBinarySHA256": NATIVE_SHA, "nativeSourceManifestSHA256": MANIFEST_SHA,
        "protectedAppleJournal": False, "engineProcessRestart": False,
        "uiInteraction": False, "liveProviderTransport": False,
        "runnerSHA256": sha(Path(__file__)),
    }
    valid = False
    probe = None
    try:
        build_log = prefix.with_suffix(".build.log")
        with build_log.open("wb") as output:
            build_exit = bounded([str(args.swift), "build", "--product", "pinkha-any-host-probe",
                "--jobs", "4", "--disable-automatic-resolution"],
                cwd=ROOT / "Modules/PinkhaAnyHost", env=env, stdout=output,
                stderr=subprocess.STDOUT, seconds=900)
        record.update(buildExitCode=build_exit, buildLog=build_log.relative_to(ROOT).as_posix(),
                      buildLogSHA256=sha(build_log))
        if build_exit:
            raise RuntimeError("Production native Host/T5 probe failed to build")
        bin_path = subprocess.check_output([str(args.swift), "build", "--show-bin-path",
            "--disable-automatic-resolution"], cwd=ROOT / "Modules/PinkhaAnyHost",
            env=env, text=True, timeout=90).strip()
        probe = Path(bin_path) / ("pinkha-any-host-probe.exe" if os.name == "nt" else "pinkha-any-host-probe")
        record["probeSHA256"] = sha(probe)
        with urllib.request.urlopen(args.endpoint.rstrip("/") + "/v1/health", timeout=10) as response:
            health = json.load(response)
        record["health"] = {key: health[key] for key in ("status", "version", "buildCommit") if key in health}
        stdout_path, stderr_path = prefix.with_suffix(".stdout.log"), prefix.with_suffix(".stderr.log")
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            code = bounded([str(probe), args.endpoint, args.space_id, args.account_id,
                "--torah-workflow", "--allow-disposable-writes"],
                cwd=ROOT, env=env, stdout=stdout, stderr=stderr, seconds=300)
        record.update(probeExitCode=code, stdoutSHA256=sha(stdout_path), stderrSHA256=sha(stderr_path),
                      stdout=stdout_path.relative_to(ROOT).as_posix(),
                      stderr=stderr_path.relative_to(ROOT).as_posix())
        lines = stdout_path.read_text(encoding="utf-8").strip().splitlines()
        result = json.loads(lines[-1]) if lines else {}
        record["result"] = result
        valid = (code == 0 and result.get("status") == "PASS" and result.get("scope") == SCOPE
                 and result.get("protectedAppleJournal") is False
                 and result.get("engineProcessRestart") is False and result.get("count") == 19
                 and len(result.get("checks", [])) == 19 and len(set(result["checks"])) == 19)
    except Exception as error:
        record["failure"] = {"kind": type(error).__name__, "description": str(error)}
    record["sourceStable"] = source == manifest()
    record["nativeBinaryUnchanged"] = sha(args.native_binary) == NATIVE_SHA
    record["nativeManifestUnchanged"] = sha(args.native_manifest) == MANIFEST_SHA
    record["probeUnchanged"] = probe is not None and probe.exists() and sha(probe) == record.get("probeSHA256")
    record["runnerUnchanged"] = sha(Path(__file__)) == record["runnerSHA256"]
    stable = all(record[key] for key in ("sourceStable", "nativeBinaryUnchanged",
        "nativeManifestUnchanged", "probeUnchanged", "runnerUnchanged"))
    record["status"] = "PASS" if valid and stable else "FAIL"
    output_path = prefix.with_suffix(".json")
    output_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record.items() if key != "sourceManifest"}, indent=2))
    print(json.dumps({"receipt": output_path.relative_to(ROOT).as_posix()}))
    return 0 if record["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
