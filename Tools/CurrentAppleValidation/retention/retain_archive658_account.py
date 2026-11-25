"""Retain the actual Archive658 derivative account after verified shutdown.

This is a backup, never a fixture factory or an acceptance substitute. It makes
no engine requests and does not upload private database or keychain contents.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import time


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(root):
    result = {}
    total = 0
    for path in sorted(root.rglob("*")):
        entry = path.lstat()
        relative = path.relative_to(root).as_posix()
        require(len(result) < 100_000, "Owned account inventory exceeded its bound")
        row = {"mode": stat.S_IMODE(entry.st_mode)}
        if stat.S_ISLNK(entry.st_mode):
            target = path.readlink()
            require(not target.is_absolute()
                    and path.resolve(strict=True).is_relative_to(root),
                    "Private account has an unresolved external or absolute symlink: " + relative)
            row.update(kind="symlink", target=str(target))
        elif stat.S_ISDIR(entry.st_mode):
            row.update(kind="directory")
        elif stat.S_ISREG(entry.st_mode):
            total += entry.st_size
            require(total <= 8 * 1024**3, "Owned private account exceeded its bounded backup size")
            row.update(kind="file", bytes=entry.st_size, sha256=digest(path))
        else:
            raise ValueError("Nonpersistent socket/device found in shutdown account: " + relative)
        result[relative] = row
    return result


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def retain(run_root, root, expected_execution_sha256, controller, expected_controller_sha256):
    """Back up one actually retained unified UI account, without boot or native calls."""
    run_root, root, controller = Path(run_root), Path(root), Path(controller)
    base = Path("/Users/m1/builds/pinkha-dual-main-20261125")
    require(all(p.is_absolute() and p.resolve() == p for p in (run_root, controller))
            and run_root.parent == base and controller.is_relative_to(base),
            "Exact original unified UI run and controller paths required")
    require(root.is_absolute() and root.parent.resolve() == root.parent and not root.exists()
            and root.is_relative_to(Path("/Users/m1/builds"))
            and not root.is_relative_to(run_root) and not run_root.is_relative_to(root),
            "Fresh separate private backup directory required")
    require(run_root == base / "native-ui-archive-658-grabber1"
            and expected_execution_sha256 == "8c032b25cc330eaa30f34dfd64b147cdf18563b4b8f534a2334f7e8efe61f116"
            and controller == base / "native-ui-controller-f06/Tools/PinkhaDualEngineRuntime/run_prebuilt_native_ui.py"
            and expected_controller_sha256 == "0af9cbfabf8f404cb7b0efe1b2cff56dc070788880e72142420ea28e40d01278",
            "Only the separately reviewed actual Archive658 execution is admitted")
    execution_path = run_root / "receipt.json"
    execution_bytes = execution_path.read_bytes()
    require(hashlib.sha256(execution_bytes).hexdigest() == expected_execution_sha256
            and digest(controller) == expected_controller_sha256,
            "Exact actual execution and separately pinned controller required")
    execution = json.loads(execution_bytes)
    runner_path = base / "native-ui-build-archive658-1/receipt.json"
    runner_bytes = runner_path.read_bytes()
    require(hashlib.sha256(runner_bytes).hexdigest() ==
            "e585c430ec93dd31f6de087949c3af63a713727246bf925e6121f942dc267c85",
            "The actual explicit UI derivative build receipt is required")
    runner = json.loads(runner_bytes)
    require(runner["status"] == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
            and runner["exitCode"] == 0 and runner["applicationBuildTargets"] == runner["testsExecuted"] == 0
            and runner["sourceUnchanged"] is True
            and runner["sourceCommit"] == execution["sourceCommit"]
            and runner["runnerSourceCommit"] == execution["runnerSourceCommit"]
            == "658f4af4380dffc55c65559ca9e0cc6d5ed9c931"
            and runner["archiveGrabberPreparation"] == execution["archiveGrabberPreparation"]
            and execution["archiveGrabberPreparation"]["allOriginalArchiveOutcomeAssertionsUnchanged"] is True
            and execution["archiveGrabberPreparation"]["peekContentSwipeAccepted"] is False
            and execution["stage"] == "archive" and execution["status"] == "FAIL"
            and execution["counts"] == {"failedTests": 1, "passedTests": 0, "skippedTests": 0, "totalTestCount": 1}
            and execution["testCommandIssued"] is True
            and execution["testCommand"]["ownedProcessGroup"] == "ABSENT_ESRCH",
            "The observed failed Archive result and explicit UI derivative must remain separate")
    require(execution["ownedSimulator"] == "805EAD29-B084-4D3F-9AFF-1CA630D3ABEB",
            "Only the observed Archive658-owned account is admitted")
    creation = json.loads((run_root / "simulator.json").read_bytes())
    device = execution["ownedSimulator"]
    require(isinstance(device, str) and re.fullmatch(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}", device)
            and creation["ownedUDID"] == device
            and creation["runtime"] == "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
            and creation["deviceType"] == "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"
            and creation["name"].startswith("PinkhaUnifiedD-" + execution["stage"] + "-"),
            "Original unified controller-created simulator identity required")
    require(execution["status"] in ("PASS", "FAIL")
            and execution["ownedSimulatorRetention"] == "Shutdown"
            and execution["sourceCommit"] == "6f1194f9b8c9540dea1187826dda6a256777dbbf"
            and execution["mainReceiptSHA256"] == "f6054279384d731c17014d78b0aa09c1f244130f2295119197a8bd9c50930983"
            and execution["runnerReceiptSHA256"] == "e585c430ec93dd31f6de087949c3af63a713727246bf925e6121f942dc267c85"
            and runner["mainReceiptSHA256"] == execution["mainReceiptSHA256"],
            "Exact original source/product provenance and explicit shutdown custody required")
    def original_command(label, expected_argv):
        row = json.loads((run_root / (label + ".result.json")).read_bytes())
        log = run_root / (label + ".log")
        require(row["argv"] == expected_argv and row["status"] == "PASS"
                and row["exitCode"] == 0 and row["ownedProcessGroup"] == "ABSENT_ESRCH"
                and row["logSHA256"] == digest(log), "Original successful owned command required: " + label)
        return log
    create_log = original_command("create-simulator",
        ["xcrun", "simctl", "create", creation["name"], creation["deviceType"], creation["runtime"]])
    require(create_log.read_text().strip() == device, "Actual created UUID differs")
    app_log = original_command("native-sandbox-path",
        ["xcrun", "simctl", "get_app_container", device, "io.anytype.app", "data"])
    original_command("shutdown-simulator", ["xcrun", "simctl", "shutdown", device])
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device
    app = Path(app_log.read_text().strip())
    require(app.resolve() == app and app.is_dir()
            and app.parent == device_root / "data/Containers/Data/Application"
            and re.fullmatch(r"[0-9A-F-]{36}", app.name), "Canonical original app container required")
    require(device_root.resolve() == device_root and device_root.is_dir(), "Original owned simulator disappeared")
    live = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
    found = [dict(row, runtime=runtime) for runtime, rows in live["devices"].items()
             for row in rows if row.get("udid") == device]
    require(len(found) == 1 and found[0].get("state") == "Shutdown"
            and found[0].get("name") == creation["name"] and found[0].get("runtime") == creation["runtime"]
            and found[0].get("deviceTypeIdentifier") == creation["deviceType"],
            "Actual original unified simulator must remain shutdown")
    plist_path = device_root / "device.plist"
    device_plist = plistlib.loads(plist_path.read_bytes())
    require(str(device_plist.get("UDID")).upper() == device, "Original device metadata owner differs")
    plist_sha256 = digest(plist_path)
    def identity(path):
        entry = path.lstat()
        require(path.resolve() == path and not stat.S_ISLNK(entry.st_mode),
                "Original account root was replaced by an alias")
        return (entry.st_dev, entry.st_ino, entry.st_mode)
    device_identity = identity(device_root)
    plist_identity = identity(plist_path)
    root.mkdir(mode=0o700); (root / "private").mkdir(mode=0o700)
    write(root / "original-admission.json", {
        "protocol": "pinkha-original-archive658-shutdown-admission-v1",
        "runRoot": str(run_root), "executionSHA256": expected_execution_sha256,
        "separatelyPinnedControllerSHA256": expected_controller_sha256,
        "sourceCommit": execution["sourceCommit"], "runnerSourceCommit": execution["runnerSourceCommit"],
        "runnerReceiptSHA256": execution["runnerReceiptSHA256"],
        "originalTestStatus": execution["status"],
        "originalTestCounts": execution.get("counts"),
        "device": device, "devicePlistSHA256": plist_sha256,
        "creation": creation, "newTestExecution": False, "nativeCalls": 0,
    })
    directory = root / "private/owned-account-originals"
    require(not directory.exists(), "Private account retention must never overwrite an original")
    directory.mkdir(mode=0o700)
    write(directory / "device-admission.json", found[0])
    shutil.copy2(plist_path, directory / "device.plist")
    roots = {"application-data": app,
             "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains",
             "device-preferences": device_root / "data/Library/Preferences"}
    for source in roots.values():
        require(not source.exists() or source.is_dir(), "Owned account scope must be a directory")
    root_identities = {label: identity(source) if source.exists() else None
                       for label, source in roots.items()}
    lifecycle_checks = []
    def require_same_shutdown(phase):
        require(identity(device_root) == device_identity and identity(plist_path) == plist_identity
                and digest(plist_path) == plist_sha256, "Owned simulator metadata or root changed during retention")
        state = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
        matches = [dict(row, runtime=runtime) for runtime, rows in state["devices"].items()
                   for row in rows if row.get("udid") == device]
        require(len(matches) == 1 and all(matches[0].get(key) == found[0].get(key)
                for key in ("udid", "name", "runtime", "deviceTypeIdentifier", "state"))
                and matches[0].get("state") == "Shutdown", "Owned simulator left the original shutdown state")
        for label, source in roots.items():
            expected = root_identities[label]
            if expected is None:
                require(not source.exists() and not source.is_symlink(), "An absent account scope appeared during retention")
            else:
                require(identity(source) == expected, "Original private account scope was replaced")
        lifecycle_checks.append({"phase": phase, "status": "SAME_OWNED_SHUTDOWN_AND_ROOT_IDENTITIES", "at": time.time()})
    receipt = {"protocol": "pinkha-owned-archive658-account-retention-v1", "status": "FAIL",
               "executionSHA256": expected_execution_sha256, "device": device,
               "startedAt": time.time(), "extraEngineCalls": 0, "restoredFixtures": 0,
               "fixtureDeadlineChanged": False, "rawPrivateDataUploaded": False, "scopes": {},
               "externalSymlinks": "REJECTED", "lifecycleChecks": lifecycle_checks}
    try:
        require_same_shutdown("before-all-copies")
        for label, source in roots.items():
            if not source.exists():
                require(label not in ("application-data", "keychains"), "Required owned private account scope is absent")
                receipt["scopes"][label] = {"status": "NOT_PRESENT"}
                require_same_shutdown("after-absent-" + label)
                continue
            require(source.resolve() == source and source.is_relative_to(device_root), "Owned private scope is aliased")
            before = inventory(source)
            before_path = directory / (label + "-before.json"); write(before_path, before)
            destination = directory / label
            require(shutil.disk_usage(directory).free >= 2 * 1024**3, "Owned 2 GiB emergency floor required")
            subprocess.run(["cp", "-cRp", str(source), str(destination)], check=True, timeout=180)
            copied = inventory(destination); after = inventory(source)
            write(directory / (label + "-copied.json"), copied)
            write(directory / (label + "-after.json"), after)
            require(before == copied == after, "Shutdown private account changed or clone differs")
            require_same_shutdown("after-copy-" + label)
            receipt["scopes"][label] = {"status": "PRESERVED_ORIGINAL_BYTES_AND_MODES",
                "entries": len(before), "manifestSHA256": digest(before_path),
                "regularBytes": sum(v.get("bytes", 0) for v in before.values())}
        require(digest(execution_path) == expected_execution_sha256, "Original execution receipt changed during retention")
        require_same_shutdown("immediately-before-pass")
        receipt["status"] = "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
    except BaseException as exc:
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        receipt["finishedAt"] = time.time()
        write(directory / "retention.json", receipt)
    return receipt

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-sha256", required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--controller-sha256", required=True)
    args = parser.parse_args()
    require(all(re.fullmatch(r"[0-9a-f]{64}", value)
                for value in (args.execution_sha256, args.controller_sha256)), "Exact provenance digests required")
    print(json.dumps(retain(args.run_root, args.output, args.execution_sha256,
                            args.controller, args.controller_sha256), sort_keys=True))
