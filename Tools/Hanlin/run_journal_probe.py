#!/usr/bin/env python3
"""One UIKit-container platform probe; never SDK/native-write acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import signal
import subprocess
import time
from uuid import uuid4

BUNDLE = "io.anytype.sdk06.journal-probe"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
RUNTIME_BUILD = "24A434"
DEVICE = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"
XCODE = "Xcode 27.0\nBuild version 27A266a"
SOURCE = "Tools/Hanlin/JournalFilesystemProbe.swift"
SOURCE_FILES = [SOURCE, "Tools/Hanlin/run_journal_probe.py", ".github/workflows/pinkha-hanlin-journal-probe.yml"]


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def terminate_owned(process):
    for number in [signal.SIGTERM, signal.SIGKILL]:
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"[0-9a-f]{40}", args.source_sha) and run_id.isdigit() and attempt.isdigit(), "Exact source/run identity required")
    private = root / "build/hanlin-journal-probe-work"
    evidence = root / "build/hanlin-journal-probe-evidence"
    require(not private.exists() and not evidence.exists(), "Fresh owned probe directories required")
    private.mkdir(parents=True)
    evidence.mkdir(parents=True)
    token = uuid4().hex
    receipt = {"status": "NOT_RUN", "source_sha": args.source_sha, "run_id": run_id, "run_attempt": attempt,
               "token": token, "started_at": datetime.now(timezone.utc).isoformat(),
               "sdk_acceptance": False, "native_write_accepted": False, "physical_device_accepted": False,
               "commands": [], "source_sha256": {name: digest(root / name) for name in SOURCE_FILES}}
    path = evidence / "execution.json"
    write(path, receipt)
    old_handlers = {n: signal.getsignal(n) for n in [signal.SIGTERM, signal.SIGINT]}
    cancelled = False
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in old_handlers:
        signal.signal(number, cancel)
    owned = None
    result = 1

    def run(argv, name, timeout=120, check=True, env=None):
        log = evidence / (name + ".log")
        require(not log.exists(), "Refuse reused command evidence")
        entry = {"name": name, "argv": list(map(str, argv)), "status": "RUNNING"}
        receipt["commands"].append(entry)
        write(path, receipt)
        process = None
        with log.open("xb") as stream:
            try:
                process = subprocess.Popen(list(map(str, argv)), cwd=root, env=env,
                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                entry["pid"] = process.pid
                entry["exit_code"] = process.wait(timeout=timeout)
                entry["status"] = "SUCCEEDED" if process.returncode == 0 else "FAILED"
            except BaseException as error:
                entry.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAILED",
                             error_type=type(error).__name__)
                if process is not None:
                    terminate_owned(process)
                raise
            finally:
                stream.flush()
                os.fsync(stream.fileno())
                write(path, receipt)
        if check:
            require(entry["exit_code"] == 0, "Probe command failed: " + name)
        return log.read_text(encoding="utf-8").strip()

    try:
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual native Apple ARM64 host required")
        require(run(["git", "rev-parse", "HEAD"], "source-head") == args.source_sha, "Source HEAD differs")
        require(not run(["git", "status", "--porcelain", "--untracked-files=no"], "source-status"), "Tracked source modified")
        require(run(["xcodebuild", "-version"], "xcode-version") == XCODE, "Different Xcode from failing run")
        receipt["xcode"] = XCODE
        receipt["swift"] = run(["xcrun", "swiftc", "--version"], "swift-version")
        require(run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "sdk-version") == "27.0", "Different simulator SDK")
        sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], "sdk-path")
        runtimes = json.loads(run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtimes"))["runtimes"]
        runtime = [v for v in runtimes if v.get("identifier") == RUNTIME and v.get("isAvailable") is True]
        require(len(runtime) == 1 and runtime[0].get("buildversion") == RUNTIME_BUILD, "Different actual simulator runtime")
        receipt["runtime"] = {key: runtime[0].get(key) for key in ["identifier", "version", "buildversion"]}
        inventory = json.loads(run(["xcrun", "simctl", "list", "devices", "--json"], "devices-before"))["devices"]
        previous_ids = {d["udid"].lower() for devices in inventory.values() for d in devices}
        device_name = "Pinkha-Hanlin-Journal-Probe-" + run_id + "-" + token[:8]
        candidate = run(["xcrun", "simctl", "create", device_name, DEVICE, RUNTIME], "create-owned-simulator")
        require(re.fullmatch(r"[0-9A-Fa-f-]{36}", candidate) and candidate.lower() not in previous_ids, "Simulator was not freshly created")
        after = json.loads(run(["xcrun", "simctl", "list", "devices", "--json"], "devices-after"))["devices"]
        matches = [d for d in after.get(RUNTIME, []) if d.get("udid", "").lower() == candidate.lower()]
        require(len(matches) == 1 and matches[0].get("name") == device_name
                and matches[0].get("deviceTypeIdentifier") == DEVICE and matches[0].get("state") == "Shutdown",
                "Fresh simulator ownership/type/runtime differs")
        owned = candidate
        receipt["owned_simulator"] = {"udid": owned, "device_type": DEVICE, "name": device_name}
        run(["xcrun", "simctl", "boot", owned], "boot-owned-simulator")
        run(["xcrun", "simctl", "bootstatus", owned, "-b"], "boot-ready", 180)
        app = private / "JournalProbe.app"
        app.mkdir()
        executable = app / "JournalProbe"
        info = {"CFBundleIdentifier": BUNDLE, "CFBundleName": "JournalProbe", "CFBundleExecutable": "JournalProbe",
                "CFBundlePackageType": "APPL", "CFBundleVersion": "1", "CFBundleShortVersionString": "1.0",
                "CFBundleInfoDictionaryVersion": "6.0", "CFBundleSupportedPlatforms": ["iPhoneSimulator"],
                "MinimumOSVersion": "27.0", "LSRequiresIPhoneOS": True, "UIDeviceFamily": [2], "UILaunchScreen": {},
                "UIApplicationSceneManifest": {"UIApplicationSupportsMultipleScenes": False,
                    "UISceneConfigurations": {"UIWindowSceneSessionRoleApplication": [{"UISceneConfigurationName": "JournalProbe"}]}}}
        (app / "Info.plist").write_bytes(plistlib.dumps(info))
        run(["xcrun", "swiftc", "-swift-version", "6", "-parse-as-library", "-sdk", sdk,
             "-target", "arm64-apple-ios27.0-simulator", "-framework", "UIKit", "-framework", "Foundation",
             "-module-cache-path", private / "ModuleCache", root / SOURCE, "-o", executable], "compile-probe-only", 240)
        run(["codesign", "--force", "--sign", "-", "--timestamp=none", app], "sign-probe")
        receipt["probe_executable_sha256"] = digest(executable)
        run(["xcrun", "simctl", "install", owned, app], "install-probe")
        container = Path(run(["xcrun", "simctl", "get_app_container", owned, BUNDLE, "data"], "probe-container"))
        probe_path = container / "Library/Application Support/pinkha-hanlin-journal-probe.json"
        require(not probe_path.exists(), "Refuse stale platform receipt")
        environment = dict(os.environ, SIMCTL_CHILD_PINKHA_PROBE_SOURCE_SHA=args.source_sha,
            SIMCTL_CHILD_PINKHA_PROBE_RUN_ID=run_id, SIMCTL_CHILD_PINKHA_PROBE_RUN_ATTEMPT=attempt,
            SIMCTL_CHILD_PINKHA_PROBE_TOKEN=token)
        launched = run(["xcrun", "simctl", "launch", "--terminate-running-process", owned, BUNDLE], "launch-probe", env=environment)
        match = re.fullmatch(re.escape(BUNDLE) + r":\s*(\d+)", launched)
        require(match is not None, "Actual probe launch PID unavailable")
        deadline = time.monotonic() + 45
        while not probe_path.exists() and time.monotonic() < deadline:
            time.sleep(0.2)
        require(probe_path.is_file() and not probe_path.is_symlink() and probe_path.stat().st_size <= 65536, "Bounded actual platform receipt unavailable")
        raw = probe_path.read_bytes()
        observed = json.loads(raw)
        for key, value in {"protocolVersion": 1, "status": "SYNTHETIC_PLATFORM_OBSERVATION_COMPLETE",
                           "sourceSHA": args.source_sha, "runID": run_id, "runAttempt": attempt, "token": token,
                           "processID": int(match.group(1)), "bundleIdentifier": BUNDLE, "simulator": True,
                           "systemVersion": "27.0", "nativeWriteAccepted": False, "sdkAcceptance": False,
                           "physicalDeviceProtectionAccepted": False, "physicalPowerLossDurabilityAccepted": False}.items():
            require(type(observed.get(key)) is type(value) and observed.get(key) == value, "Actual platform identity differs: " + key)
        stages = observed.get("stages")
        scopes = ["application-support", "temporary-directory"]
        require(observed.get("storageScopes") == scopes and isinstance(stages, list) and stages
                and stages[0].get("name") == "application-support.host.create"
                and all(any(s.get("name") == scope + ".host.create" for s in stages) for scope in scopes)
                and all(any(s.get("name", "").startswith(scope + ".") for scope in scopes) for s in stages)
                and len({s.get("name") for s in stages}) == len(stages), "Actual ordered platform observations unavailable")
        require(all(type(s.get("satisfied")) is bool and type(s.get("requiredForInitialJournal")) is bool for s in stages), "Malformed stage outcomes")
        failed = [s for s in stages if s["requiredForInitialJournal"] and not s["satisfied"]]
        first_by_scope = {}
        for stage in failed:
            scope = stage["name"].split(".", 1)[0]
            first_by_scope.setdefault(scope, stage["name"])
        require(observed.get("firstUnsatisfiedStageByStorageScope") == first_by_scope, "Per-location diagnostic differs")
        require(observed.get("firstUnsatisfiedStage") == (failed[0]["name"] if failed else None)
                and observed.get("allInitialJournalRequirementsObserved") is (not failed), "Diagnostic status differs from actual stages")
        (evidence / "platform-observation.original.json").write_bytes(raw)
        receipt.update(status="DIAGNOSTIC_COMPLETE_NOT_SDK_ACCEPTANCE", platform_receipt_sha256=hashlib.sha256(raw).hexdigest(),
                       first_unsatisfied_stage=observed.get("firstUnsatisfiedStage"),
                       first_unsatisfied_stage_by_storage_scope=first_by_scope, actual_process_id=observed["processID"])
        require({name: digest(root / name) for name in SOURCE_FILES} == receipt["source_sha256"], "Probe source changed")
        result = 0
    except BaseException as error:
        result = 1
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__)
    finally:
        try:
            if owned:
                run(["xcrun", "simctl", "shutdown", owned], "shutdown-owned-simulator", 60, check=False)
                run(["xcrun", "simctl", "delete", owned], "delete-owned-simulator", 60)
                receipt["removed_owned_simulator"] = owned
        except BaseException as error:
            result = 1
            receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) or cancelled else "FAIL",
                           cleanup_error_type=type(error).__name__)
        def finish():
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            write(path, receipt)
        try:
            try:
                finish()
            except KeyboardInterrupt:
                result = 1
                receipt.update(status="CANCELLED", error_type="KeyboardInterrupt")
                finish()
        finally:
            for number, previous in old_handlers.items():
                signal.signal(number, previous)
    print(json.dumps({k: receipt.get(k) for k in ["status", "source_sha", "run_id", "first_unsatisfied_stage", "error_type"]}))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
