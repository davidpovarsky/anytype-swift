"""Retain real owned simulator account data privately after actual shutdown.

This is a backup, never a fixture factory or an acceptance substitute. It makes
no engine requests and does not upload private database or keychain contents.
"""
import hashlib
import os
import errno
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


def retain(root, expected_execution_sha256):
    """A new custody observation; original failed execution remains immutable."""
    root = Path(root)
    prior_path = Path("/Users/m1/development/anytype-c-active-20261125/terminal-custody/app14-miniapps-b35a/evidence/result.json")
    prior_bytes = prior_path.read_bytes()
    require(hashlib.sha256(prior_bytes).hexdigest() ==
            "2efe63f8972bd013ca443676319fb8c8433fa97e30c3f753a55247b87dd6e5ea",
            "Original metadata equality refusal changed")
    prior = json.loads(prior_bytes)
    require(prior["status"] == "FAIL" and prior["originalAcceptance"] == "FAIL"
            and prior["actualMethods"] == prior["bootCalls"] == prior["engineCalls"] == 0
            and prior["error"] == {"type": "ValueError", "message": "Native metadata UUID differs from the container"},
            "Original custody refusal must remain separate")
    require(root == Path("/Users/m1/development/anytype-d-active-20261125/main14/heart-miniapps86-attempt1")
            and root.resolve() == root, "Only the exact original MiniApps attempt is admitted")
    require(expected_execution_sha256 == "2ce146a369cb38b79e1b449cdc929449fc5e5259d2c117af1a8b0c978f1860a5",
            "Exact original zero-method failure required")
    execution_path = root / "evidence/execution.json"
    original_bytes = execution_path.read_bytes()
    require(hashlib.sha256(original_bytes).hexdigest() == expected_execution_sha256,
            "Original execution changed before retention")
    execution = json.loads(original_bytes)
    require(execution["protocol"] == "pinkha-App14-MiniApps86-original-five-v1"
            and execution["sourceCommit"] == "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
            and execution["controllerSHA256"] == "31e415e1266cb3162508f8326955b62613d4b2266401b371750f4a92f4c4d4d5"
            and execution["coreSHA256"] == "59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de"
            and execution["admissionSHA256"] == "e3871c16ccaa3147d90c1c3061690cca2551a54ff8b3c81583196720abaace9e"
            and execution["companionSourceCommit"] == "86a6dde354947be9329fe1e8f4d45a433fe488c4",
            "Original App14/source/controller/companion authority differs")
    require(execution["status"] == "FAIL" and execution["testsExecuted"] == 0
            and execution["testCommandsInvoked"] == 0 and execution["builds"] == 0
            and execution["ownedGroupsRemaining"] == [44255]
            and execution["ownedSimulatorRetention"] == "Shutdown",
            "Original zero-method failure must remain failed")
    methods = execution["methods"]
    require(len(methods) == 1
            and methods[0]["method"] == "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"
            and methods[0]["target"] == "AnytypeTests"
            and methods[0]["status"] == "FAIL" and methods[0]["testInvoked"] is False,
            "No completed original method may be hidden")
    require(not list((root / "commands").glob("*-test/started.json")),
            "No method invocation is admitted")
    device = execution["ownedSimulator"]
    require(device == "B35A314F-E546-465B-B86A-A65589125CF5", "Exact owned device required")
    pins = {
        "create-device": "d9603e95a3c3806ab41f99abadc9eb283931538daf54fd9d6d1f014e20fcb88a",
        "shutdown": "f6fc71e50f868a037a5ab297ad303dcd21eb886448ffa1e5bf26d3e835223817",
        "shutdown-state": "542b68f5e9d38ed550a683dbf0c2bc8f22b524a9b1876b3d6bde4d1c0eab7f9f",
        "final-app-container": "db926dd9b5f2bd53e51f9b7eaddaaffe774fcd455dc237fcafd7b9f7673f5ae5",
    }
    commands = {}
    for name, expected in pins.items():
        command_path = root / "commands" / name / "result.json"
        command_bytes = command_path.read_bytes()
        require(hashlib.sha256(command_bytes).hexdigest() == expected, "Original command changed: " + name)
        command = json.loads(command_bytes)
        require(digest(command_path.with_name("original.log")) == command["logSHA256"],
                "Original command log changed: " + name)
        commands[name] = command
    create = commands["create-device"]
    expected_name = "PinkhaUnifiedMiniApps-9200e7e9-4c48-4b4f-b6c4-9f446cbcecd9"
    expected_type = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"
    expected_runtime = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
    require(create["argv"] == ["xcrun", "simctl", "create", expected_name, expected_type, expected_runtime]
            and create["status"] == "PASS_COMMAND" and create["exitCode"] == 0
            and (root / "commands/create-device/original.log").read_text().strip() == device,
            "Original device creation differs")
    require(commands["shutdown"]["argv"] == ["xcrun", "simctl", "shutdown", device]
            and commands["shutdown"]["status"] == "PASS_COMMAND" and commands["shutdown"]["exitCode"] == 0,
            "Actual original shutdown required")
    require(commands["shutdown-state"]["status"] == "PASS_COMMAND"
            and commands["shutdown-state"]["exitCode"] == 0,
            "Actual original shutdown observation required")
    require(commands["final-app-container"]["status"] == "FAIL_COMMAND"
            and commands["final-app-container"]["logBytes"] == 0,
            "Original failed container lookup must remain failed")
    observed_path = root.parent / "heart-miniapps86-attempt1-owned-observation1/kernel-observation.json"
    observed_bytes = observed_path.read_bytes()
    require(hashlib.sha256(observed_bytes).hexdigest() ==
            "faf5405f5b0ef45faf5a84e88d95c776b789461da63fbae0c6139aa5e3efa6fb",
            "Independent post-terminal group observation changed")
    observation = json.loads(observed_bytes)
    require(observation["protocol"] == "pinkha-owned-post-terminal-observation-v1"
            and observation["priorExecutionSHA256"] == expected_execution_sha256
            and observation["originalStatus"] == "FAIL" and observation["acceptanceReclassified"] is False
            and observation["signalsSent"] == 0
            and observation["groups"] == [{"pgid": 41438, "status": "ABSENT_ESRCH"},
                                          {"pgid": 44255, "status": "ABSENT_ESRCH"},
                                          {"pgid": 53318, "status": "ABSENT_ESRCH"}],
            "All exact original groups must already be positively absent")
    # Historical absent IDs are not re-probed or signalled: they may be reused.
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device
    require(device_root.resolve() == device_root and device_root.is_dir(),
            "Original owned simulator disappeared")
    live = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
    found = [dict(row, runtime=runtime) for runtime, rows in live["devices"].items()
             for row in rows if row.get("udid") == device]
    require(len(found) == 1 and found[0].get("state") == "Shutdown"
            and found[0].get("name") == expected_name
            and found[0].get("runtime") == expected_runtime
            and found[0].get("deviceTypeIdentifier") == expected_type,
            "Exact current owned shutdown device required")
    original_state = json.loads((root / "commands/shutdown-state/original.log").read_bytes())
    original_rows = [dict(row, runtime=runtime) for runtime, rows in original_state["devices"].items()
                     for row in rows if row.get("udid") == device]
    require(len(original_rows) == 1 and all(original_rows[0].get(key) == found[0].get(key)
                for key in ("udid", "name", "runtime", "deviceTypeIdentifier", "state")),
            "Original and current device identities differ")
    application_root = device_root / "data/Containers/Data/Application"
    require(application_root.resolve() == application_root and application_root.is_dir(),
            "Canonical owned application container root required")
    candidates = []
    children = list(application_root.iterdir())
    require(len(children) <= 1024, "Owned application container census exceeded its bound")
    for child in children:
        require(child.resolve() == child and not child.is_symlink() and child.is_dir(),
                "Owned application container root is aliased")
        metadata = child / ".com.apple.mobile_container_manager.metadata.plist"
        if not metadata.exists():
            continue
        require(metadata.is_file() and not metadata.is_symlink()
                and metadata.stat().st_size <= 1_048_576, "Invalid native container metadata")
        metadata_before = metadata.lstat()
        metadata_bytes = metadata.read_bytes()
        metadata_after = metadata.lstat()
        require((metadata_before.st_dev, metadata_before.st_ino, metadata_before.st_mode, metadata_before.st_size)
                == (metadata_after.st_dev, metadata_after.st_ino, metadata_after.st_mode, metadata_after.st_size)
                and len(metadata_bytes) == metadata_before.st_size,
                "Native container metadata changed while reading")
        metadata_parsed_sha = hashlib.sha256(metadata_bytes).hexdigest()
        value = plistlib.loads(metadata_bytes)
        if value.get("MCMMetadataIdentifier") == "io.anytype.app":
            require(re.fullmatch(r"[0-9A-F-]{36}", child.name), "Invalid native container UUID")
            # This exact device has distinct filesystem and native logical UUIDs.
            # Bind both observed namespaces and the same parsed metadata bytes;
            # neither is substituted for the other or for a successful simctl lookup.
            require(child.name == "33BA9B08-3BE2-49DC-A412-C559AA02EF7F"
                    and value.get("MCMMetadataUUID") == "6FDEAF40-98D3-4A58-A396-B5D09802B6CE"
                    and metadata_parsed_sha == "c44fbff39d2dc03d71708b12414bcddcbcf6d5eb844950200107957d21cf6cbe",
                    "Exact separately observed native and filesystem container identity changed")
            candidates.append((child, metadata, metadata_parsed_sha))
    require(len(candidates) == 1, "Exactly one native io.anytype.app data container is required")
    app, container_metadata, container_metadata_sha = candidates[0]
    require(digest(container_metadata) == container_metadata_sha,
            "Selected native metadata changed after identity parsing")
    container_admission = {
        "protocol": "pinkha-owned-shutdown-mcm-container-custody-v1",
        "origin": "native-mobile-container-manager-metadata",
        "bundleIdentifier": "io.anytype.app", "containerPath": str(app),
        "nativeMetadataSHA256": container_metadata_sha,
        "filesystemContainerUUID": "33BA9B08-3BE2-49DC-A412-C559AA02EF7F",
        "nativeLogicalContainerUUID": "6FDEAF40-98D3-4A58-A396-B5D09802B6CE",
        "priorCustodyRefusalSHA256": hashlib.sha256(prior_bytes).hexdigest(),
        "originalContainerCommandStatus": "FAIL_COMMAND",
        "newSimctlContainerCommandClaimed": False, "engineCalls": 0,
    }
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
    container_metadata_identity = identity(container_metadata)
    directory = Path("/Users/m1/development/anytype-c-active-20261125/terminal-custody/app14-miniapps-b35a-mcm1/private/owned-account-originals")
    require(not directory.exists(), "Private account retention must never overwrite an original")
    directory.mkdir(mode=0o700, parents=True)
    write(directory / "container-admission.json", container_admission)
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
                and digest(plist_path) == plist_sha256
                and identity(container_metadata) == container_metadata_identity
                and digest(container_metadata) == container_metadata_sha,
                "Owned simulator/container metadata or root changed during retention")
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
    receipt = {"protocol": "pinkha-app14-miniapps-zero-method-postterminal-custody-v1", "status": "FAIL",
               "executionSHA256": expected_execution_sha256, "device": device,
               "originalAcceptance": "FAIL", "originalMethodCount": 0,
               "postTerminalGroupObservation": observation,
               "historicalGroupsReprobed": False, "signalsSent": 0,
               "originalContainerResolution": "FAIL_COMMAND",
               "containerAdmissionSHA256": digest(directory / "container-admission.json"),
               "originalWitnessComparisonAvailable": False,
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
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execution-sha256", required=True)
    args = parser.parse_args()
    evidence = Path("/Users/m1/development/anytype-c-active-20261125/terminal-custody/app14-miniapps-b35a-mcm1/evidence")
    evidence.mkdir(mode=0o700, parents=True, exist_ok=False)
    outcome = {"protocol": "pinkha-b35a-postterminal-custody-result-v1", "status": "FAIL",
               "originalAcceptance": "FAIL", "actualMethods": 0, "bootCalls": 0, "engineCalls": 0}
    try:
        receipt = retain(args.root, args.execution_sha256)
        outcome.update(status=receipt["status"],
            retentionSHA256=digest(evidence.parent / "private/owned-account-originals/retention.json"),
            device=receipt["device"], scopes=receipt["scopes"])
    except BaseException as error:
        outcome["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        write(evidence / "result.json", outcome)
    print(json.dumps(outcome, sort_keys=True))
    raise SystemExit(0 if outcome["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE" else 1)
