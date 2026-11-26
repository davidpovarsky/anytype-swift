"""Exact prior failure, sealed account and installed-product admission; no mutation."""
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


def admit_prior(root, expected_execution_sha256):
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
    device_plist_bytes = plist_path.read_bytes()
    device_plist = plistlib.loads(device_plist_bytes)
    require(str(device_plist.get("UDID")).upper() == device, "Original device metadata owner differs")
    plist_sha256 = hashlib.sha256(device_plist_bytes).hexdigest()
    def identity(path):
        entry = path.lstat()
        require(path.resolve() == path and not stat.S_ISLNK(entry.st_mode),
                "Original account root was replaced by an alias")
        return (entry.st_dev, entry.st_ino, entry.st_mode)
    device_identity = identity(device_root)
    plist_identity = identity(plist_path)
    container_metadata_identity = identity(container_metadata)

    directory = Path("/Users/m1/development/anytype-c-active-20261125/terminal-custody/app14-miniapps-b35a-mcm1/private/owned-account-originals")
    pins = {"retention.json": "7a500ea5a7474b6b82f4eabffcd030d80c8b116a632bcec890c458487b532ec0",
            "container-admission.json": "ff530525c72640b101d1b5d965ff043da9cd4f87ae9221902de6f6f7a444b4bc",
            "device-admission.json": "b48b61ff69066a44123a338ecf008adac23fbfffe53604e0a4ab8d34b74448a0",
            "device.plist": "8ed232ef8870840ab35e766d2fb41bce41a54193cae883e68634d0e0bfcf2fef"}
    values = {}
    for name, expected in pins.items():
        data = (directory / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == expected, "Original sealed custody changed: " + name)
        values[name] = data
    seal = json.loads(values["retention.json"])
    require(seal["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
            and seal["executionSHA256"] == expected_execution_sha256 and seal["device"] == device
            and seal["originalAcceptance"] == "FAIL" and seal["originalMethodCount"] == 0
            and seal["originalContainerResolution"] == "FAIL_COMMAND",
            "Exact separately qualified shutdown custody required")
    require(json.loads(values["container-admission.json"]) == container_admission
            and values["device.plist"] == device_plist_bytes,
            "Current native container/device no longer matches sealed originals")
    retained_device = json.loads(values["device-admission.json"])
    require(all(found[0].get(k) == retained_device.get(k)
                for k in ("udid", "name", "runtime", "deviceTypeIdentifier", "state")),
            "Current shutdown owner differs from retained device")
    roots = {"application-data": app,
             "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains",
             "device-preferences": device_root / "data/Library/Preferences"}
    root_identities = {label: identity(source) if source.exists() else None for label, source in roots.items()}
    require(set(seal["scopes"]) == set(roots), "Complete four-scope custody required")
    for label, source in roots.items():
        row = seal["scopes"][label]
        require(row["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES" and source.is_dir(),
                "Required current scope missing")
        original = (directory / (label + "-before.json")).read_bytes()
        require(hashlib.sha256(original).hexdigest() == row["manifestSHA256"],
                "Retained scope declaration changed")
        expected = json.loads(original)
        require(json.loads((directory / (label + "-copied.json")).read_bytes()) == expected
                == json.loads((directory / (label + "-after.json")).read_bytes()),
                "Original before/copy/after scope differs")
        require(inventory(directory / label) == expected and inventory(source) == expected,
                "Current or retained private scope changed")
        require(len(expected) == row["entries"]
                and sum(x.get("bytes", 0) for x in expected.values()) == row["regularBytes"],
                "Original scope counts differ")
    for name in ("miniapps-native-fixture.json", "miniapps-native-readback.json", "miniapps-native-adapter-readback.json"):
        require(not (app / "Library/Application Support" / name).exists(),
                "An original preparation already produced a fixture")
    require(identity(device_root) == device_identity and identity(plist_path) == plist_identity
            and digest(plist_path) == plist_sha256
            and identity(container_metadata) == container_metadata_identity
            and digest(container_metadata) == container_metadata_sha,
            "Owned device or native metadata changed during admission")
    for label, source in roots.items():
        require(identity(source) == root_identities[label], "Private scope root identity changed")
    state = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"], timeout=30))
    matches = [dict(row, runtime=runtime) for runtime, rows in state["devices"].items()
               for row in rows if row.get("udid") == device]
    require(len(matches) == 1 and all(matches[0].get(k) == found[0].get(k)
                for k in ("udid", "name", "runtime", "deviceTypeIdentifier", "state"))
            and matches[0]["state"] == "Shutdown", "Owned device left admitted shutdown")
    for name, data in values.items():
        require((directory / name).read_bytes() == data, "Custody input changed during admission")
    require(digest(root / "evidence/execution.json") == expected_execution_sha256,
            "Original zero-method failure changed")
    return {"protocol": "pinkha-b35a-zero-preparation-continuation-admission-v1",
            "status": "PASS_ORIGINAL_FAILURE_AND_CURRENT_SEALED_CUSTODY",
            "device": device, "name": expected_name, "runtime": expected_runtime,
            "deviceType": expected_type, "applicationData": str(app), "deviceRoot": str(device_root),
            "devicePlistSHA256": plist_sha256, "scopeRootIdentities": root_identities,
            "nativeMetadataSHA256": container_metadata_sha, "retentionSHA256": pins["retention.json"],
            "scopes": seal["scopes"], "priorExecutionSHA256": expected_execution_sha256,
            "priorTestCommands": 0, "historicalGroupsReprobed": False, "bootCalls": 0, "tests": 0}

def admit_installed_products(prior, source_app, companion_app):
    root = Path("/Users/m1/development/anytype-d-active-20261125/main14")
    path = root / "heart-miniapps86-installed-finalization1/receipt.json"
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == "b664c6cf5e1570cb4d72a5c734dbda0d1d0064fcf835f58e7170bce58b8c68dc",
            "Exact independent installed product census required")
    proof = json.loads(data)
    require(proof["status"] == "PASS_EXACT_INSTALLED_BYTES_WITH_CLOSED_OBSERVED_MODES"
            and proof["tests"] == proof["bootCalls"] == proof["engineCalls"] == 0,
            "Installed census is not acceptance")
    specs = {"source": (3494, 186, "io.anytype.app"), "companion": (6825, 160, "com.itorah.hanlinminiapps")}
    products = {"source": Path(source_app), "companion": Path(companion_app)}
    admitted = {}
    for name, (count, mode_count, bundle) in specs.items():
        row = proof["apps"][name]
        original_raw = (root / "heart-miniapps86-installed-readback2" / (name + "-original.json")).read_bytes()
        installed_raw = (root / "heart-miniapps86-installed-readback2" / (name + "-installed.json")).read_bytes()
        require(hashlib.sha256(original_raw).hexdigest() == row["originalInventorySHA256"]
                and hashlib.sha256(installed_raw).hexdigest() == row["installedInventorySHA256"],
                "Exact original installed manifests changed")
        original, installed = json.loads(original_raw), json.loads(installed_raw)
        require(len(original) == len(installed) == count == row["entries"], "Complete installed census differs")
        stripped = lambda m: {k: {f: v for f, v in item.items() if f != "mode"} for k, item in m.items()}
        require(stripped(original) == stripped(installed), "Installed content/path/kind/link differs")
        modes = {k: {"originalMode": original[k]["mode"], "installedMode": installed[k]["mode"]}
                 for k in original if original[k]["mode"] != installed[k]["mode"]}
        require(modes == row["closedModeDifferences"] and len(modes) == mode_count,
                "Only the closed actual installation mode map is admitted")
        app = Path(row["installed"])
        require(app.resolve() == app and app.is_relative_to(Path(prior["deviceRoot"]))
                and plistlib.loads((app / "Info.plist").read_bytes())["CFBundleIdentifier"] == bundle,
                "Installed app identity differs")
        require(inventory(products[name]) == original and inventory(app) == installed,
                "Currently admitted or installed product changed")
        admitted[name] = {"bundle": bundle, "path": str(app), "entries": count,
                         "installedInventorySHA256": row["installedInventorySHA256"],
                         "originalInventorySHA256": row["originalInventorySHA256"],
                         "closedModeDifferences": mode_count}
    require(path.read_bytes() == data, "Installed census changed while admitting")
    return {"status": "PASS_EXACT_EXISTING_SOURCE_AND_COMPANION_NO_INSTALL",
            "originalCensusSHA256": hashlib.sha256(data).hexdigest(), "apps": admitted,
            "installs": 0, "builds": 0, "tests": 0}
