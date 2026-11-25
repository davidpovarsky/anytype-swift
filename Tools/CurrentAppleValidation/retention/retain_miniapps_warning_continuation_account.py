"""Retain the actual MiniApps warning-continuation account after its UI failure.

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
    base = Path("/Users/m1/builds/pinkha-unified-miniapps-20261125")
    prior_root = base / "heart-five-attempt4"
    require(all(p.is_absolute() and p.resolve() == p for p in (run_root, controller))
            and run_root == base / "heart-warning-continuation1"
            and controller == base / "resume-warning-ui-eaa935e7.py"
            and expected_execution_sha256 == "c066f21871d706b3b5a0d5139facc33f40284b8ece4b4eb179327f1292bae9cc"
            and expected_controller_sha256 == "c4626ee64b160b2c2a2ebf9910eedf6625dff048ae279271119b357c5b62617d",
            "Only the exact separately reviewed MiniApps warning continuation is admitted")
    require(root.is_absolute() and root.parent.resolve() == root.parent and not root.exists()
            and root.is_relative_to(Path("/Users/m1/builds"))
            and not root.is_relative_to(run_root) and not run_root.is_relative_to(root),
            "Fresh separate private backup directory required")
    execution_path = run_root / "evidence/execution.json"
    execution_bytes = execution_path.read_bytes()
    require(hashlib.sha256(execution_bytes).hexdigest() == expected_execution_sha256
            and digest(controller) == expected_controller_sha256,
            "Exact actual execution and separately pinned controller required")
    execution = json.loads(execution_bytes)
    prior_path = prior_root / "evidence/execution.json"
    prior_bytes = prior_path.read_bytes()
    require(hashlib.sha256(prior_bytes).hexdigest() ==
            "144b17e9892ec99056771a5ec9417f8bdc5d2101863ace71f99f0fc0c3b5ca47",
            "Original preparation and failed warning UI receipt required")
    prior = json.loads(prior_bytes)
    require(prior["protocol"] == "pinkha-unified-miniapps-original-five-v1"
            and prior["status"] == "FAIL"
            and [x["status"] for x in prior["methods"]] == ["PASS", "FAIL"]
            and prior["ownedSimulator"] == execution["ownedSimulator"]
            and prior["sourceCommit"] == execution["sourceCommit"]
            and prior["companionSourceCommit"] == execution["companionSourceCommit"]
            and prior["companionManifestSHA256"] == execution["companionManifestSHA256"],
            "The earlier preparation pass and warning UI failure remain unchanged")
    prior_seal = Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/d-miniapps-prepared-ui-account-seal1/private/owned-account-originals/retention.json")
    require(digest(prior_seal) == "9816e5828b056636475776f215008c6c95db303d2f463ab9dd44d31a3de4f0bb"
            and execution["priorAccountSealSHA256"] == digest(prior_seal)
            and execution["priorExecutionSHA256"] == hashlib.sha256(prior_bytes).hexdigest()
            and execution["priorControllerSHA256"] == prior["controllerSHA256"],
            "Actual predecessor custody and preparation authority are distinct")
    ui_path = base / "warning-ui-a3e3-build1/evidence/receipt.json"
    require(digest(ui_path) == "516cb74c53e3c6e5e202cedc0fb7a15cf21133241e7b94f75c4a290ff0ddfb28"
            and execution["uiProducerReceiptSHA256"] == digest(ui_path)
            and execution["uiSourceCommit"] == "a3e3b21455e7ff517d34b0b16c897fed8845fc22",
            "Actual full UI derivative source/build receipt required")
    require(execution["protocol"] == "pinkha-unified-miniapps-warning-continuation-v1"
            and execution["status"] == "FAIL"
            and execution["sourceCommit"] == "6f1194f9b8c9540dea1187826dda6a256777dbbf"
            and execution["controllerSHA256"] == expected_controller_sha256
            and execution["coreSHA256"] == "7adb3118bbf584d6475f1bffc483c2055994ce50ac3031471226762df23dc501"
            and execution["admissionSHA256"] == "82ede074604e6ac8e80f631dfd2d61e4f19fc54cd0a5a68c482fda6bc310e697"
            and execution["companionSourceCommit"] == "70eb9c2d2cdfd920a65da59643dff7d4e7b775ff"
            and execution["companionManifestSHA256"] == "350af7b55f5e981d2029778b75d61a17ea4db1b6df670ed623f630d283afb370"
            and execution["builds"] == execution["fixtureResets"] == execution["nativePreparationReplays"] == 0
            and execution["testCommandsInvoked"] == execution["testsExecuted"] == 1
            and execution["ownedSimulator"] == "026E9F43-C4AF-4087-B300-8870B82FAFA4"
            and execution["ownedSimulatorRetention"] == "Shutdown"
            and execution["ownedGroupsRemaining"] == []
            and len(execution["methods"]) == 1
            and execution["methods"][0]["method"] ==
                "MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen"
            and execution["methods"][0]["status"] == "FAIL"
            and execution["methods"][0]["testInvoked"] is True,
            "Original failed actual return UI remains failed; no methods are replayed")
    original_method_counts = {}
    for phase_root, phase, key, expected_summary, expected_command, expected_counts, expected_exit in [
        (prior_root, "prepare", "original-preparation",
         "ecc598d8bfa071cb2caa3341d0dcc837e89af0cb22ac02c65c24d5104eab3185",
         "1091d011be041667e348c8c87a767c21adef034cf652e54fcd88ce339b2858af",
         {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0}, 0),
        (prior_root, "return-ui", "prior-warning-failure",
         "0f581c8eb04e27b04b26ac1e1c34e740612d85b68d99cd69f0630d80e64258d2",
         "7d0b34a92d4dd48ced8ba3a3c0c160df63b940bb39a9bfb6db578ea2a7eebaf5",
         {"totalTestCount": 1, "passedTests": 0, "failedTests": 1, "skippedTests": 0}, 65),
        (run_root, "return-ui", "actual-continuation-failure",
         "b0531be2d949925666ccc52cdcf4be2f8b50ee4e3d13cd43281539464e8e1d00",
         "514e743f68c23a5fa6fc206dd03ad9d7b9fedf6d0368910bf9255eed53bc6129",
         {"totalTestCount": 1, "passedTests": 0, "failedTests": 1, "skippedTests": 0}, 65),
    ]:
        summary_path = phase_root / "evidence" / phase / "summary.json"
        require(digest(summary_path) == expected_summary, "Exact original method summary required")
        summary = json.loads(summary_path.read_bytes())
        counts = {name: summary[name] for name in expected_counts}
        require(counts == expected_counts, "Original method counts must remain unchanged")
        original_method_counts[key] = counts
        command_root = phase_root / "commands" / (phase + "-test")
        require(digest(command_root / "result.json") == expected_command
                and (command_root / "started.json").is_file(), "Exact actual original test invocation required")
        row = json.loads((command_root / "result.json").read_bytes())
        require(row["exitCode"] == expected_exit and row["ownedGroupPresentAfterExit"] is False
                and row["status"] == ("PASS_COMMAND" if expected_exit == 0 else "FAIL_COMMAND")
                and row["logSHA256"] == digest(command_root / "original.log"),
                "Original passed preparation and both failed UI commands must remain explicit")
    device = execution["ownedSimulator"]
    pins = {
        "create-device": (prior_root, "0406cc55f1620354bb22c8137842562a1efb61d85349e024d238a87d4b11443f"),
        "postboot-original-container": (run_root, "f06faf02173d929ceeeba0adc5b1e3f480c736181ccb1b3c5066262406bd8fa5"),
        "shutdown": (run_root, "88cf95f6339b9cfc84717620c906d89d7794f361bd6cb4e40c410e45904520f4"),
    }
    def original_command(label, expected_argv):
        command_root, pin = pins[label]
        directory = command_root / "commands" / label
        row_path = directory / "result.json"
        require(digest(row_path) == pin, "Exact original command receipt required")
        row = json.loads(row_path.read_bytes()); log = directory / "original.log"
        require(row["argv"] == expected_argv and row["status"] == "PASS_COMMAND"
                and row["exitCode"] == 0 and row["ownedGroupPresentAfterExit"] is False
                and row["logSHA256"] == digest(log), "Original successful owned command required: " + label)
        return log
    creation = {
        "ownedUDID": device, "runtime": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
        "deviceType": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB",
        "name": "PinkhaUnifiedMiniApps-6bbf9f0a-0465-47e3-ac16-32643ac65dba",
    }
    create_log = original_command("create-device",
        ["xcrun", "simctl", "create", creation["name"], creation["deviceType"], creation["runtime"]])
    require(create_log.read_text().strip() == device, "Actual created MiniApps UUID differs")
    app_log = original_command("postboot-original-container",
        ["xcrun", "simctl", "get_app_container", device, "io.anytype.app", "data"])
    require(app_log.read_text().strip() == execution["privateAppContainer"],
            "Actual final MiniApps app container differs")
    original_command("shutdown", ["xcrun", "simctl", "shutdown", device])
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
        "protocol": "pinkha-original-miniapps-warning-continuation-shutdown-admission-v1",
        "runRoot": str(run_root), "executionSHA256": expected_execution_sha256,
        "separatelyPinnedControllerSHA256": expected_controller_sha256,
        "sourceCommit": execution["sourceCommit"], "companionSourceCommit": execution["companionSourceCommit"],
        "companionManifestSHA256": execution["companionManifestSHA256"],
        "originalTestMethodsExecuted": execution["testsExecuted"],
        "originalOwnedGroupAbsenceReceiptsBound": True,
        "uiSourceCommit": execution["uiSourceCommit"],
        "uiProducerReceiptSHA256": execution["uiProducerReceiptSHA256"],
        "originalPreparationAndUIFailurePreserved": True,
        "originalTestStatus": execution["status"],
        "originalTestCounts": original_method_counts,
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
    receipt = {"protocol": "pinkha-owned-miniapps-warning-continuation-account-retention-v1", "status": "FAIL",
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
