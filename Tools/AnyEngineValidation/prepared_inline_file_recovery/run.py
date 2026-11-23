#!/usr/bin/env python3
"""Execute only the frozen, opt-in Linux native recovery fixture."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

PROTOCOL = "pinkha-inline-native-process-recovery-v1"
PACKAGE = "github.com/anyproto/any/internal/server"
MINIMUM_FREE = 2_500_000_000
MAXIMUM_INCREMENTAL = 1_000_000_000


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def original(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode().strip()


def inventory(root, expected_commit, expected_tree):
    if git(root, "rev-parse", "HEAD") != expected_commit:
        raise RuntimeError("repository HEAD differs from the frozen source")
    if git(root, "rev-parse", "HEAD^{tree}") != expected_tree:
        raise RuntimeError("repository tree differs from the frozen source")
    subprocess.run(["git", "-C", str(root), "diff", "--no-ext-diff", "--exit-code", "HEAD"], check=True, capture_output=True)
    entries = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-r", "-z", "HEAD"]).split(b"\0")
    result = []
    for entry in entries:
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, blob = meta.decode().split()
        name = raw_path.decode()
        if kind != "blob" or name.startswith("/") or ".." in Path(name).parts:
            raise RuntimeError("unexpected source entry shape")
        path = root / name
        if mode == "120000":
            raw = os.readlink(path).encode()
        else:
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("source file kind changed")
            raw = path.read_bytes()
        actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if actual_blob != blob:
            raise RuntimeError("working file differs from its exact Git object: " + name)
        result.append({"path": name, "mode": mode, "gitBlob": blob, "bytes": len(raw), "sha256": digest(raw)})
    return result


def run_owned(argv, cwd, env, log, timeout, receipt):
    before = shutil.disk_usage(cwd).free
    if before < MINIMUM_FREE + 100_000_000:
        raise RuntimeError("insufficient reserved development-volume headroom")
    began = time.monotonic()
    record = {"argv": argv, "cwd": str(cwd), "timeUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "timeoutSeconds": timeout, "freeBefore": before, "privateProcessGroup": True}
    stopped_for = None
    try:
        with log.open("xb") as output:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            record["pid"] = process.pid
            while process.poll() is None:
                elapsed = time.monotonic() - began
                free = shutil.disk_usage(cwd).free
                if elapsed > timeout:
                    stopped_for = "owned command deadline exceeded"
                elif free < MINIMUM_FREE or before - free > MAXIMUM_INCREMENTAL:
                    stopped_for = "development-volume reserve or incremental-growth guard reached"
                if stopped_for:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=20)
                    break
                time.sleep(1)
            record["returncode"] = process.returncode
            output.flush()
            os.fsync(output.fileno())
    except BaseException as error:
        record["controllerError"] = type(error).__name__ + ": " + str(error)
        if "process" in locals() and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=20)
        raise
    finally:
        record["elapsedSeconds"] = time.monotonic() - began
        record["freeAfter"] = shutil.disk_usage(cwd).free
        record["stoppedFor"] = stopped_for
        if log.exists():
            record["originalLogSHA256"] = digest(log.read_bytes())
            record["originalLogBytes"] = log.stat().st_size
        original(receipt, record)
    if stopped_for or record["returncode"] != 0:
        raise RuntimeError(stopped_for or "owned command returned nonzero; original receipt/log retained")
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("build", "execute"), required=True)
    parser.add_argument("--any", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--module-cache", type=Path, required=True)
    parser.add_argument("--build-cache", type=Path, required=True)
    parser.add_argument("--go-path", type=Path, required=True)
    parser.add_argument("--select", action="append", default=[])
    args = parser.parse_args()
    source_root = Path(__file__).resolve().parent
    plan_bytes = (source_root / "source.json").read_bytes()
    plan = json.loads(plan_bytes)
    if plan["protocol"] != PROTOCOL:
        raise RuntimeError("source protocol differs")
    root, evidence = args.any.resolve(), args.evidence.absolute()
    sdk = root / ".runtime-artifacts/sdk-source"
    if not all(p.is_absolute() for p in (args.any, args.evidence, args.module_cache, args.build_cache, args.go_path)):
        raise RuntimeError("explicit absolute owned paths are required")
    for cache in (args.module_cache, args.build_cache, args.go_path):
        if not cache.is_dir():
            raise RuntimeError("the selected prior cache must already exist")
    for row in plan["files"]:
        frozen = (source_root / Path(row["fixturePath"]).name).read_bytes()
        actual = (root / row["anyPath"]).read_bytes()
        if frozen != actual or digest(actual) != row["sha256"]:
            raise RuntimeError("new fixture bytes differ from their frozen source")
    selected = args.select or plan["selectors"]
    if len(set(selected)) != len(selected) or not selected or any(s not in plan["selectors"] for s in selected):
        raise RuntimeError("only distinct new explicitly qualified selectors are available")
    env = os.environ.copy()
    env.pop("PINKHA_INLINE_RECOVERY_LAUNCH", None)
    env.update({"GOTOOLCHAIN": "local", "GOWORK": "off", "GOMAXPROCS": "1", "CGO_ENABLED": "1",
                "GOPROXY": "off", "GOPATH": str(args.go_path), "GOMODCACHE": str(args.module_cache),
                "GOCACHE": str(args.build_cache), "GOTMPDIR": str(evidence / "go-tmp"),
                "TMPDIR": str(evidence / "tmp"), "PINKHA_INLINE_RECOVERY_PRIVATE": str(evidence / "private"),
                "PINKHA_INLINE_RECOVERY_EVIDENCE": str(evidence / "safe")})
    go = shutil.which("go")
    if not go or subprocess.check_output([go, "version"], env=env, text=True).strip() != "go version go1.27.4 linux/arm64":
        raise RuntimeError("the explicitly reviewed Go/Linux/ARM64 profile is unavailable")
    source = {"any": inventory(root, plan["any"]["fixtureCommit"], plan["any"]["fixtureTree"]),
              "sdk": inventory(sdk, plan["sdk"]["candidateCommit"], plan["sdk"]["candidateTree"])}
    if len(source["any"]) != 852 or len(source["sdk"]) != 683:
        raise RuntimeError("source closure count differs")
    controller_root = Path(git(source_root, "rev-parse", "--show-toplevel"))
    controller_inputs = []
    for path in sorted(source_root.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            name = str(path.relative_to(controller_root))
            frozen = subprocess.check_output(["git", "-C", str(controller_root), "show", "HEAD:" + name])
            if raw != frozen:
                raise RuntimeError("controller source is not its committed frozen input")
            controller_inputs.append({"path": name, "sha256": digest(raw), "bytes": len(raw)})
    binary = evidence / "qualified-products/inline-recovery.test"
    if args.phase == "build":
        evidence.mkdir(mode=0o700)
        for name in ("go-tmp", "tmp", "private", "safe", "qualified-products"):
            (evidence / name).mkdir(mode=0o700)
        original(evidence / "source-before.json", source)
        metadata = {"protocol": PROTOCOL, "sourcePlanSHA256": digest(plan_bytes),
                    "controllerCommit": git(controller_root, "rev-parse", "HEAD"), "controllerInputs": controller_inputs,
                    "environment": {k: env[k] for k in ("GOTOOLCHAIN", "GOWORK", "GOMAXPROCS", "CGO_ENABLED",
                        "GOPROXY", "GOPATH", "GOMODCACHE", "GOCACHE", "GOTMPDIR", "TMPDIR")},
                    "goExecutable": str(Path(go).resolve()), "goSHA256": digest(Path(go).resolve().read_bytes()),
                    "goVersion": "go version go1.27.4 linux/arm64", "actualProductMethodsExecuted": 0,
                    "privateStoreIsNeverAnArtifact": True}
        original(evidence / "build-metadata.json", metadata)
        argv = [go, "test", "-c", "-p=1", "-mod=readonly", "-tags=pinkha_inline_recovery",
                "-o", str(binary), "./internal/server"]
        build_failure = None
        try:
            run_owned(argv, root, env, evidence / "build-original.log", 1200, evidence / "build-command.json")
        except BaseException as error:
            build_failure = type(error).__name__ + ": " + str(error)
        after = {"any": inventory(root, plan["any"]["fixtureCommit"], plan["any"]["fixtureTree"]),
                 "sdk": inventory(sdk, plan["sdk"]["candidateCommit"], plan["sdk"]["candidateTree"])}
        original(evidence / "source-after-build.json", after)
        if source != after:
            raise RuntimeError("source changed during compilation")
        if build_failure:
            original(evidence / "failure.json", {"status": "FAILED_BUILD_NO_TESTS",
                "sourceUnchanged": True, "actualProductMethodsExecuted": 0,
                "childProcessesStarted": 0, "originalFailure": build_failure})
            raise RuntimeError(build_failure)
        listing = subprocess.check_output([str(binary), "-test.list=^TestPreparedInlineFile(ActualProcessCrashRecovery|ActualLostHTTPAcknowledgementRecovery|RecoveryChild)$"],
                                          cwd=root / "internal/server", env=env)
        (evidence / "registered-new-methods-original.txt").write_bytes(listing)
        if set(listing.decode().splitlines()) != set(plan["selectors"] + [plan["childSelector"]]):
            raise RuntimeError("actual compiled method registration differs")
        original(evidence / "build-qualified.json", {"status": "COMPILED_NOT_EXECUTED",
            "binarySHA256": digest(binary.read_bytes()), "binaryBytes": binary.stat().st_size,
            "registeredNewMethods": listing.decode().splitlines(), "sourceUnchanged": True,
            "actualProductMethodsExecuted": 0})
        print(json.dumps({"status": "COMPILED_NOT_EXECUTED", "evidence": str(evidence),
                          "freeBytes": shutil.disk_usage(root).free}))
        return
    metadata = json.loads((evidence / "build-metadata.json").read_text())
    if metadata["sourcePlanSHA256"] != digest(plan_bytes) or metadata["controllerInputs"] != controller_inputs:
        raise RuntimeError("controller or source plan differs from the original build")
    built = json.loads((evidence / "build-qualified.json").read_text())
    if built["status"] != "COMPILED_NOT_EXECUTED" or digest(binary.read_bytes()) != built["binarySHA256"]:
        raise RuntimeError("original compiled binary changed or has no admission")
    if json.loads((evidence / "source-before.json").read_text()) != source:
        raise RuntimeError("current source differs from the original build")
    original(evidence / "execution-start.json", {"protocol": PROTOCOL, "selectors": selected,
        "binarySHA256": built["binarySHA256"], "sourcePlanSHA256": digest(plan_bytes),
        "timeUTC": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    expression = "^(" + "|".join(selected) + ")$"
    argv = [go, "tool", "test2json", "-p", PACKAGE, "-t", str(binary),
            "-test.run=" + expression, "-test.count=1", "-test.v=test2json", "-test.timeout=360s"]
    failure = None
    try:
        run_owned(argv, root / "internal/server", env, evidence / "execution-original.jsonl", 420,
                  evidence / "execution-command.json")
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
    after = {"any": inventory(root, plan["any"]["fixtureCommit"], plan["any"]["fixtureTree"]),
             "sdk": inventory(sdk, plan["sdk"]["candidateCommit"], plan["sdk"]["candidateTree"])}
    original(evidence / "source-after-execution.json", after)
    events = []
    for line in (evidence / "execution-original.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            events.append({k: row[k] for k in ("Time", "Action", "Package", "Test", "Elapsed") if k in row})
    original(evidence / "named-events.json", events)
    runs = [e["Test"] for e in events if e.get("Action") == "run" and "Test" in e]
    passes = [e["Test"] for e in events if e.get("Action") == "pass" and "Test" in e]
    failed = [e for e in events if e.get("Action") in ("fail", "skip")]
    binary_unchanged = digest(binary.read_bytes()) == built["binarySHA256"]
    accepted = not failure and sorted(runs) == sorted(selected) and sorted(passes) == sorted(selected) and not failed and source == after and binary_unchanged
    original(evidence / "execution-status.json", {"status": "PASS_NEW_SCOPES" if accepted else "FAILED",
        "selectors": selected, "namedStarts": runs, "namedPasses": passes, "failureOrSkipEvents": failed,
        "controllerFailure": failure, "sourceUnchanged": source == after,
        "binaryUnchanged": binary_unchanged,
        "oldSuitesExecuted": False, "powerLossDurability": False, "swiftClientAcceptance": False,
        "AppleAcceptance": False, "networkAcceptance": False, "notificationOutboxDelivery": False,
        "fullMigrationComplete": False})
    print(json.dumps({"status": "PASS_NEW_SCOPES" if accepted else "FAILED", "namedStarts": runs,
                      "namedPasses": passes, "evidence": str(evidence), "freeBytes": shutil.disk_usage(root).free}))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
