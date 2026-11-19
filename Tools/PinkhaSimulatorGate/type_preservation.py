"""Source-bound, same-account native postflight for the real Type UI roundtrip."""
import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import time
from uuid import uuid4

METHOD = "TorahStage2TypePreservationTests/verifyExistingTypeRoundtrip"
SUITE = METHOD.split("/")[0]
PREFIX = "type-preservation"
BASELINE = "pinkha-type-preservation-baseline.json"
FIXTURE = "pinkha-native-derived-ui-fixture.json"
SUPPORT = Path("Library/Application Support")
STORE = SUPPORT / "Anytype/middleware-go"
INSTALLATION = "type-preservation-installation.json"
STOP_STAGES = ("BEFORE_INVENTORY", "BEFORE_INSTALL", "AFTER_INSTALL", "AFTER_INVENTORY")
QUERY_SECONDS = 30
PROCESS_SECONDS = 30
INVENTORY_SECONDS = 120
INSTALL_COMMAND_SECONDS = 120
# Reserve the complete transition before admitting a Properties batch lane.
# Hash/metadata work consumes this same deadline; it does not extend it.
INSTALLATION_SECONDS = 6 * QUERY_SECONDS + 4 * PROCESS_SECONDS + 2 * INVENTORY_SECONDS + INSTALL_COMMAND_SECONDS
LIMIT = 65_536
SECONDS = 300
DISABLED_FLAGS = (
    "PINKHA_NATIVE_DERIVED_ACCEPTANCE", "PINKHA_PREPARE_TYPE_PRESERVATION",
    "PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION", "PINKHA_SIMULATOR_UI_DISPOSABLE",
    "PINKHA_HANLIN_NATIVE_PREPARATION", "PINKHA_PREPARE_HANLIN_SELECTION_UI",
    "PINKHA_PROPERTIES_PREPARE", "PINKHA_T5_UI_PREPARATION", "PINKHA_T5_APPLE_PAIR",
)
STATE_KEYS = {"accountID", "spaceID", "subjectID", "chiddushTypeID", "canonicalPropertyKey",
              "canonicalRaw", "canonicalSHA256", "container", "middleware", "objects", "tagOption"}
OBJECT_KEYS = {"objectID", "spaceID", "typeID", "tags", "links", "backlinks", "seededLinks"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def read_bytes(path):
    require(path.is_file() and not path.is_symlink(), "Preservation file is missing or a symlink")
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    require(0 < len(raw) <= LIMIT, "Preservation file size is outside its bound")
    return raw


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate preservation JSON key")
            result[key] = value
        return result
    require(0 < len(raw) <= LIMIT, "Preservation JSON size is outside its bound")
    return json.loads(raw, object_pairs_hook=pairs)


def binding(source_sha, run_id, run_attempt, nonce=None):
    value = {"sourceSHA": source_sha, "runID": run_id, "runAttempt": run_attempt,
             "nonce": uuid4().hex if nonce is None else nonce}
    require(isinstance(source_sha, str) and re.fullmatch(r"[0-9a-f]{40}", source_sha), "Invalid preservation source")
    require(all(isinstance(x, str) and re.fullmatch(r"[1-9][0-9]*", x) for x in (run_id, run_attempt)),
            "Invalid preservation run identity")
    require(isinstance(value["nonce"], str) and re.fullmatch(r"[0-9a-f]{32}", value["nonce"]), "Invalid preservation nonce")
    return value


def binding_environment(value):
    return {"PINKHA_TYPE_PRESERVATION_" + key: value[field] for key, field in
            (("SOURCE_SHA", "sourceSHA"), ("RUN_ID", "runID"), ("RUN_ATTEMPT", "runAttempt"), ("NONCE", "nonce"))}


def directory_identity(path):
    require(path.is_dir() and not path.is_symlink(), "Original preservation directory is missing or replaced")
    actual = path.resolve(strict=True)
    info = actual.stat()
    born = getattr(info, "st_birthtime", None)
    require(type(born) in (int, float) and math.isfinite(born) and born > 0,
            "Actual macOS directory creation identity is unavailable")
    return {"path": str(actual), "device": str(info.st_dev), "inode": str(info.st_ino), "createdAt": born}


def validate_directory(value, observed):
    require(isinstance(value, dict) and set(value) == {"path", "device", "inode", "createdAt"},
            "Native directory identity schema differs")
    require(all(value[key] == observed[key] for key in ("path", "device", "inode")),
            "Native directory identity differs from the controller")
    require(type(value["createdAt"]) in (int, float) and math.isfinite(value["createdAt"]) and value["createdAt"] > 0,
            "Native directory creation identity is missing")
    # Native Foundation and Python each compare their own original creation-time
    # representation after the UI; no float rounding tolerance replaces identity.


def validate_baseline(value, expected_binding, fixture, directories):
    require(isinstance(value, dict) and set(value) == {"schemaVersion", "binding", "preparationPID", "state"}
            and type(value["schemaVersion"]) is int and value["schemaVersion"] == 1,
            "Unknown preservation baseline schema")
    require(value["binding"] == expected_binding, "Preservation baseline has another source/run/nonce")
    require(type(value["preparationPID"]) is int and value["preparationPID"] > 1, "Original preparation process is missing")
    state = value["state"]
    require(isinstance(state, dict) and set(state) == STATE_KEYS, "Unknown preservation state schema")
    target = fixture["typeSwitch"]
    require(nonempty(state["accountID"]) and state["spaceID"] == fixture["spaceId"] == target["spaceId"]
            and state["subjectID"] == target["objectId"] and state["chiddushTypeID"] == target["initialTypeId"]
            and nonempty(state["canonicalPropertyKey"]), "Preservation target/account identity differs")
    for name in ("container", "middleware"):
        validate_directory(state[name], directories[name])
    raw = state["canonicalRaw"]
    require(nonempty(raw) and sha256(raw.encode("utf-8")) == state["canonicalSHA256"], "Original canonical bytes/hash differ")
    canonical = decode(raw.encode("utf-8"))
    require(type(canonical.get("version")) is int and canonical["version"] == 2,
            "Original canonical envelope must be v2 without a legacy lift")
    records = canonical.get("records")
    require(isinstance(records, list) and len(records) == 3, "Three original canonical records required")
    identities, ids = [], []
    for record in records:
        require(isinstance(record, dict) and record.get("spaceId") == state["spaceID"]
                and record.get("objectId") == state["subjectID"] and record.get("blockId") is None,
                "Canonical record location differs")
        item = record.get("item", {})
        require(nonempty(item.get("id")) and item.get("providerID") == "sefaria"
                and nonempty(item.get("createdAt")) and item.get("externalID") == item.get("canonicalKey"),
                "Canonical original identity/timestamp is missing")
        for key in ("createdAt", "updatedAt"):
            if key == "updatedAt" and item.get(key) is None:
                continue
            stamp = item.get(key)
            require(nonempty(stamp) and stamp.endswith("Z"), "Canonical original timestamp is not UTC")
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            require(math.isfinite(parsed.timestamp()), "Invalid canonical original timestamp")
        ids.append(item["id"]); identities.append((item.get("kind"), item.get("canonicalKey")))
    require(len(set(ids)) == 3 and set(identities) == {("ref", "Genesis 3:1"), ("topic", "creation"), ("word", "בראשית")},
            "Original canonical identities differ")
    objects = state["objects"]
    require(isinstance(objects, list) and len(objects) == 3 and all(isinstance(x, dict) and set(x) == OBJECT_KEYS for x in objects),
            "Three actual native object readbacks required")
    object_ids = [row["objectID"] for row in objects]
    require(all(nonempty(x) for x in object_ids) and len(set(object_ids)) == 3 and object_ids[0] == state["subjectID"],
            "Preservation peer identities are missing or reused")
    reserved = set(fixture["documents"].values()) | set(fixture["universalDocuments"].values())
    reserved |= {x["objectId"] for x in fixture["sourceHeaderCases"]}
    reserved |= {fixture["setId"], fixture["universalSetId"], state["subjectID"]}
    require(not (set(object_ids[1:]) & reserved), "A preservation peer reused another fixture")
    expected_types = [state["chiddushTypeID"], fixture["universalTypes"]["page"], fixture["universalTypes"]["page"]]
    for row, type_id in zip(objects, expected_types, strict=True):
        require(row["spaceID"] == state["spaceID"] and row["typeID"] == type_id, "Native peer Space/Type differs")
        for key in ("tags", "links", "backlinks"):
            values = row[key]
            require(isinstance(values, list) and all(nonempty(x) for x in values)
                    and values == sorted(set(values)), "Native property set is not complete/sorted/unique")
    tag = state["tagOption"]
    require(isinstance(tag, dict) and set(tag) == {"objectID", "spaceID", "name", "relationKey", "color"}
            and nonempty(tag["objectID"]) and tag["objectID"] not in reserved | set(object_ids)
            and tag["spaceID"] == state["spaceID"] and tag["relationKey"] == "tag"
            and tag["name"] == "Original native Type-preservation Tag" and nonempty(tag["color"])
            and objects[0]["tags"] == [tag["objectID"]], "Original native Tag readback differs")
    require(object_ids[1] in objects[0]["links"] and object_ids[0] in objects[1]["backlinks"]
            and object_ids[0] in objects[2]["links"] and object_ids[2] in objects[0]["backlinks"],
            "Actual reciprocal native links/backlinks are missing")
    link_ids = []
    for index, target_id in ((0, object_ids[1]), (2, object_ids[0])):
        links = objects[index]["seededLinks"]
        require(isinstance(links, list) and len(links) == 1 and set(links[0]) == {"blockID", "targetID"}
                and nonempty(links[0]["blockID"]) and links[0]["targetID"] == target_id,
                "Actual native link block identity/target is missing")
        link_ids.append(links[0]["blockID"])
    require(objects[1]["seededLinks"] == [] and len(set(link_ids)) == 2, "Seeded native link blocks differ")
    return value


@dataclass(frozen=True)
class FrozenBaseline:
    path: Path
    sha256: str
    value: dict
    directories: dict
    container: Path
    udid: str
    fixture_path: Path
    fixture_sha256: str


def freeze(container, evidence, expected_binding, fixture, udid):
    container = container.resolve(strict=True)
    require(udid.lower() in {part.lower() for part in container.parts}, "Container is outside its owned simulator")
    destination = evidence / "type-preservation-baseline.json"
    require(not destination.resolve().is_relative_to(container), "Frozen baseline must be outside mutable App data")
    raw = read_bytes(container / "Library/Application Support" / BASELINE)
    fixture_raw = read_bytes(container / SUPPORT / FIXTURE)
    require(decode(fixture_raw) == fixture, "Original native fixture bytes/identity differ")
    directories = {"container": directory_identity(container),
                   "middleware": directory_identity(container / "Library/Application Support/Anytype/middleware-go")}
    value = validate_baseline(decode(raw), expected_binding, fixture, directories)
    with destination.open("xb") as stream:
        stream.write(raw)
    fixture_path = evidence / "type-preservation-fixture.json"
    with fixture_path.open("xb") as stream:
        stream.write(fixture_raw)
    frozen = FrozenBaseline(destination, sha256(raw), value, directories, container, udid,
                            fixture_path, sha256(fixture_raw))
    verify_frozen(frozen)
    return frozen


def verify_original_bytes(frozen):
    require(sha256(read_bytes(frozen.path)) == frozen.sha256, "Frozen original baseline bytes changed")
    require(decode(read_bytes(frozen.path)) == frozen.value, "Frozen original baseline value changed")
    require(sha256(read_bytes(frozen.fixture_path)) == frozen.fixture_sha256, "Frozen original fixture bytes changed")


def verify_frozen(frozen, observed_container=None):
    verify_original_bytes(frozen)
    if observed_container is not None:
        require(observed_container.resolve(strict=True) == frozen.container, "Postflight App data container changed")
    for name in ("container", "middleware"):
        require(directory_identity(Path(frozen.directories[name]["path"])) == frozen.directories[name],
                "Original container/store directory was recreated or replaced")


def owned_container(path, udid):
    require(path.is_dir() and not path.is_symlink(), "Owned App container is missing or a symlink")
    path = path.resolve(strict=True)
    require(udid.lower() in {part.lower() for part in path.parts}, "App container is outside its owned simulator")
    return path


def remaining(deadline, ceiling):
    available = deadline - time.monotonic()
    require(available > 0, "Controlled install phase budget exhausted")
    return min(ceiling, available)


def app_container(udid, kind, *, timeout=QUERY_SECONDS):
    require(kind in ("data", "app"), "Unknown App container kind")
    result = subprocess.run(["xcrun", "simctl", "get_app_container", udid, "io.anytype.app", kind],
                            capture_output=True, timeout=timeout)
    require(result.returncode == 0 and 0 < len(result.stdout) <= 4096,
            "Owned App container query failed")
    text = result.stdout.decode("utf-8").strip()
    require("\n" not in text and Path(text).is_absolute(), "Owned App container query is ambiguous")
    return owned_container(Path(text), udid)


def assert_app_stopped(udid, installed, *, timeout=PROCESS_SECONDS):
    """Read only; never publish host command names, arguments or environments."""
    result = subprocess.run(["/bin/ps", "-ww", "-axo", "pid=,ucomm=,comm="],
                            capture_output=True, timeout=timeout)
    require(result.returncode == 0 and 0 < len(result.stdout) <= 1_048_576,
            "Stopped-App process observation failed")
    rows = result.stdout.decode("utf-8").splitlines()
    controller_seen = False
    expected = str(installed / "Anytype")
    for line in rows:
        fields = line.strip().split(None, 2)
        require(len(fields) == 3 and fields[0].isdigit(), "Unknown process observation format")
        controller_seen |= int(fields[0]) == os.getpid()
        name, command = fields[1:]
        # Apple's ps comm uses argv[0], with '(ucomm)' on a failed read.
        # Kernel ucomm is checked too: an unresolved Anytype cannot prove exit.
        if name == "Anytype" or command == expected or (
                udid.lower() in command.lower() and "/Anytype.app/" in command):
            path = Path(command)
            require(path.is_absolute() and command.endswith("/Anytype.app/Anytype")
                    and "\\" not in command, "Anytype process identity is unresolved")
            require(command != expected and udid.lower() not in {p.lower() for p in path.parts},
                    "Owned Anytype process is still running")
    require(controller_seen, "Incomplete process observation")
    return {"status": "PASS_APP_NOT_RUNNING", "commandExitCode": 0, "ownedAppMatches": 0,
            "unresolvedAppMatches": 0, "controllerPID": os.getpid(), "enumeratedProcesses": len(rows),
            "inventorySHA256": sha256(result.stdout), "executablePathSHA256": sha256(expected.encode())}


def native_inventory(container, frozen, *, deadline=None):
    """Exact stopped-store bytes; paths/private contents stay in controller memory."""
    container = owned_container(container, frozen.udid)
    root = container / STORE
    require(root.is_dir() and root.resolve(strict=True) == root,
            "Original native store is missing or contains a symlink")
    files, directories = {}, []
    inventory_deadline = time.monotonic() + INVENTORY_SECONDS
    if deadline is not None:
        inventory_deadline = min(inventory_deadline, deadline)
    def traversal_error(error):
        # os.walk otherwise silently omits unreadable children, which could
        # make two incomplete inventories appear byte-identical.
        raise ValueError("Unable to enumerate every original native store entry") from error
    for directory, children, names in os.walk(root, followlinks=False, onerror=traversal_error):
        remaining(inventory_deadline, INVENTORY_SECONDS)
        directory = Path(directory)
        for name in children:
            path = directory / name
            require(path.is_dir() and not path.is_symlink(), "Unexpected native store directory")
            directories.append(path.relative_to(root).as_posix())
        for name in names:
            path = directory / name
            require(not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode),
                    "Unexpected native store file")
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    remaining(inventory_deadline, INVENTORY_SECONDS)
                    digest.update(chunk)
                after = os.fstat(stream.fileno())
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            current = path.lstat()
            require(stat.S_ISREG(current.st_mode)
                    and all(getattr(before, k) == getattr(after, k) == getattr(current, k) for k in fields),
                    "Native store changed during its stopped inventory")
            files[path.relative_to(root).as_posix()] = {"bytes": before.st_size, "sha256": digest.hexdigest()}
        require(len(files) + len(directories) <= 20_000, "Stopped-store inventory is oversized")
    require(files and sum(item["bytes"] for item in files.values()) > 0, "Original native store is empty")
    private = {}
    for name, expected in ((BASELINE, frozen.sha256), (FIXTURE, frozen.fixture_sha256)):
        path = container / SUPPORT / name
        require(path.resolve(strict=True) == path, "Original native identity file contains a symlink")
        private[name] = sha256(read_bytes(path))
        require(private[name] == expected, "Original native baseline/fixture changed")
    remaining(inventory_deadline, INVENTORY_SECONDS)
    return {"directories": sorted(directories), "files": files, "identitySHA256": private}


def inventory_summary(value):
    return {"sha256": sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()),
            "files": len(value["files"]), "bytes": sum(item["bytes"] for item in value["files"].values()),
            "directories": len(value["directories"])}


@dataclass(frozen=True)
class Installation:
    path: Path
    sha256: str
    value: dict
    container: Path


def validate_installation(value, baseline, baseline_sha, fixture_sha, udid, original, code_sha):
    require(isinstance(value, dict) and set(value) == {
        "schemaVersion", "status", "binding", "baselineSHA256", "fixtureSHA256", "simulatorUDID",
        "accountID", "spaceID", "subjectID", "preparationPID", "codeCarriersSHA256",
        "installedBeforeCodeSHA256", "installedAfterCodeSHA256", "originalDirectories", "currentDirectories",
        "beforeInventory", "afterInventory", "stoppedProcessChecks", "containerRelocated"},
        "Unknown controlled-install schema")
    require(type(value["schemaVersion"]) is int and value["schemaVersion"] == 1
            and value["status"] == "PASS_STOPPED_NATIVE_STORE_UNCHANGED"
            and value["binding"] == baseline["binding"] and value["baselineSHA256"] == baseline_sha
            and value["fixtureSHA256"] == fixture_sha and value["simulatorUDID"] == udid
            and all(isinstance(value[k], str) and re.fullmatch(r"[0-9a-f]{64}", value[k])
                    for k in ("baselineSHA256", "fixtureSHA256"))
            and value["preparationPID"] == baseline["preparationPID"]
            and all(value[k] == baseline["state"][k] for k in ("accountID", "spaceID", "subjectID"))
            and re.fullmatch(r"[0-9a-f]{64}", code_sha or "")
            and value["codeCarriersSHA256"] == value["installedBeforeCodeSHA256"]
                == value["installedAfterCodeSHA256"] == code_sha,
            "Controlled install has another source/build/account/baseline")
    require(value["originalDirectories"] == original, "Controlled install lost the pre-UI directory binding")
    for pair in (value["originalDirectories"], value["currentDirectories"]):
        require(isinstance(pair, dict) and set(pair) == {"container", "middleware"}, "Unknown directory pair")
        for item in pair.values():
            validate_directory(item, item)
            require(all(isinstance(item[k], str) and item[k].isdigit() and int(item[k]) > 0
                        for k in ("device", "inode")), "Missing native directory identity")
        path = Path(pair["container"]["path"])
        require(path.is_absolute() and udid.lower() in {p.lower() for p in path.parts}
                and pair["middleware"]["path"] == str(path / STORE), "Controlled install escaped the owned store")
    require(type(value["containerRelocated"]) is bool and value["containerRelocated"] ==
            (value["originalDirectories"]["container"]["path"] != value["currentDirectories"]["container"]["path"]),
            "Controlled install relocation observation differs")
    summary = value["beforeInventory"]
    require(isinstance(summary, dict) and set(summary) == {"sha256", "files", "bytes", "directories"}
            and re.fullmatch(r"[0-9a-f]{64}", summary["sha256"] or "")
            and all(type(summary[k]) is int for k in ("files", "bytes", "directories"))
            and summary["files"] > 0 and summary["bytes"] > 0 and summary["directories"] >= 0
            and value["afterInventory"] == summary, "Controlled install did not preserve every original native file")
    checks = value["stoppedProcessChecks"]
    require(isinstance(checks, dict) and set(checks) == set(STOP_STAGES), "Stopped-App checks are incomplete")
    for check in checks.values():
        require(isinstance(check, dict) and set(check) == {"status", "commandExitCode", "ownedAppMatches",
                "unresolvedAppMatches", "controllerPID", "enumeratedProcesses", "inventorySHA256", "executablePathSHA256"}
                and check["status"] == "PASS_APP_NOT_RUNNING"
                and all(type(check[k]) is int and check[k] == 0
                        for k in ("commandExitCode", "ownedAppMatches", "unresolvedAppMatches"))
                and type(check["controllerPID"]) is int and check["controllerPID"] > 1
                and type(check["enumeratedProcesses"]) is int and check["enumeratedProcesses"] > 0
                and all(re.fullmatch(r"[0-9a-f]{64}", check[k] or "")
                        for k in ("inventorySHA256", "executablePathSHA256")),
                "Controlled install lacks an actual stopped-App observation")
    return value


def install_for_postflight(frozen, built, code_sha, evidence, code_carriers):
    """One same-build install; a failed/cancelled/changed transition has no fallback."""
    observation = {"status": "FAIL", "phase": "BEFORE_INSTALL", "binding": frozen.value["binding"],
                   "phaseBudgetSeconds": INSTALLATION_SECONDS}
    started = time.monotonic()
    deadline = started + INSTALLATION_SECONDS
    def current_container(kind):
        return app_container(frozen.udid, kind, timeout=remaining(deadline, QUERY_SECONDS))
    def stopped(installed):
        return assert_app_stopped(frozen.udid, installed, timeout=remaining(deadline, PROCESS_SECONDS))
    try:
        require(not (evidence / INSTALLATION).exists(), "Refuse stale controlled-install evidence")
        verify_frozen(frozen, current_container("data"))
        require(code_carriers(built)["sha256"] == code_sha, "Built executable bytes changed before controlled install")
        metadata = plistlib.loads((built / "Info.plist").read_bytes())
        require(metadata.get("CFBundleIdentifier") == "io.anytype.app", "Controlled install bundle differs")
        installed = current_container("app")
        before_code = code_carriers(installed)["sha256"]
        require(before_code == code_sha, "Installed executable bytes changed before controlled install")
        checks = {STOP_STAGES[0]: stopped(installed)}
        prior = native_inventory(frozen.container, frozen, deadline=deadline)
        checks[STOP_STAGES[1]] = stopped(installed)
        verify_frozen(frozen, current_container("data"))
        timeout = remaining(deadline, INSTALL_COMMAND_SECONDS)
        observation.update(phase="INSTALL", timeoutSeconds=timeout)
        installed_result = subprocess.run(["xcrun", "simctl", "install", frozen.udid, str(built)],
                                         capture_output=True, timeout=timeout)
        observation["installExitCode"] = installed_result.returncode
        require(installed_result.returncode == 0, "Controlled same-build install failed")
        observation["phase"] = "AFTER_INSTALL"
        current = current_container("data")
        installed = current_container("app")
        after_code = code_carriers(installed)["sha256"]
        require(after_code == code_sha == code_carriers(built)["sha256"],
                "Controlled install changed executable bytes")
        checks[STOP_STAGES[2]] = stopped(installed)
        after = native_inventory(current, frozen, deadline=deadline)
        checks[STOP_STAGES[3]] = stopped(installed)
        require(prior == after, "Controlled install changed or removed original native account data")
        directories = {"container": directory_identity(current), "middleware": directory_identity(current / STORE)}
        value = {"schemaVersion": 1, "status": "PASS_STOPPED_NATIVE_STORE_UNCHANGED",
                 "binding": frozen.value["binding"], "baselineSHA256": frozen.sha256,
                 "fixtureSHA256": frozen.fixture_sha256, "simulatorUDID": frozen.udid,
                 **{k: frozen.value["state"][k] for k in ("accountID", "spaceID", "subjectID")},
                 "preparationPID": frozen.value["preparationPID"], "codeCarriersSHA256": code_sha,
                 "installedBeforeCodeSHA256": before_code, "installedAfterCodeSHA256": after_code,
                 "originalDirectories": frozen.directories, "currentDirectories": directories,
                 "beforeInventory": inventory_summary(prior), "afterInventory": inventory_summary(after),
                 "stoppedProcessChecks": checks, "containerRelocated": current != frozen.container}
        validate_installation(value, frozen.value, frozen.sha256, frozen.fixture_sha256,
                              frozen.udid, frozen.directories, code_sha)
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        require(len(raw) <= LIMIT, "Controlled install receipt exceeded its bound")
        destination = evidence / INSTALLATION
        with destination.open("xb") as stream:
            stream.write(raw)
        installation = Installation(destination, sha256(raw), value, current)
        verify_installed(frozen, installation, current_container("data"))
        remaining(deadline, INSTALLATION_SECONDS)
        observation.update(status="PASS", phase="COMPLETE", installationSHA256=installation.sha256)
        return installation
    except BaseException as error:
        observation["errorType"] = type(error).__name__
        raise
    finally:
        observation["elapsedSeconds"] = round(time.monotonic() - started, 6)
        (evidence / "type-preservation-install-observation.json").write_text(
            json.dumps(observation, sort_keys=True), encoding="utf-8")


def verify_installed(frozen, installation, observed_container=None):
    require(isinstance(installation, Installation), "A proved controlled install is required")
    verify_original_bytes(frozen)
    require(sha256(read_bytes(installation.path)) == installation.sha256, "Controlled install receipt changed")
    require(decode(read_bytes(installation.path)) == installation.value, "Controlled install value changed")
    if observed_container is not None:
        require(owned_container(observed_container, frozen.udid) == installation.container,
                "Additional unproved postflight App relocation")
    for name, observed in installation.value["currentDirectories"].items():
        require(directory_identity(Path(observed["path"])) == observed,
                "Installed container/store directory was recreated or replaced")
    for name, expected in ((BASELINE, frozen.sha256), (FIXTURE, frozen.fixture_sha256)):
        require(sha256(read_bytes(installation.container / SUPPORT / name)) == expected,
                "Installed native baseline/fixture changed")


def environment(frozen, installation):
    verify_installed(frozen, installation)
    result = {key: "0" for key in DISABLED_FLAGS}
    result.update(binding_environment(frozen.value["binding"]))
    result.update(PINKHA_TYPE_PRESERVATION_POSTFLIGHT="1", PINKHA_TYPE_PRESERVATION_BASELINE_SHA256=frozen.sha256,
                  PINKHA_TYPE_PRESERVATION_BASELINE_BASE64=base64.b64encode(read_bytes(frozen.path)).decode("ascii"),
                  PINKHA_TYPE_PRESERVATION_INSTALLATION_SHA256=installation.sha256,
                  PINKHA_TYPE_PRESERVATION_INSTALLATION_BASE64=base64.b64encode(read_bytes(installation.path)).decode("ascii"))
    return result


def configure_target(target, environment):
    require(environment.get("PINKHA_TYPE_PRESERVATION_POSTFLIGHT") == "1"
            and all(environment.get(key) == "0" for key in DISABLED_FLAGS), "Postflight preparation flags are not disabled")
    for key, value in target.items():
        if key.endswith("CommandLineArguments"):
            require(isinstance(value, list) and not any("PINKHA_" in str(x) for x in value),
                    "Inherited test injection argument in postflight")
        if key.endswith("EnvironmentVariables"):
            require(isinstance(value, dict), "Unexpected testhost environment schema")
            for name in tuple(value):
                if name.startswith(("PINKHA_", "SIMCTL_CHILD_PINKHA_")):
                    value[name] = "0"
    env = target.setdefault("EnvironmentVariables", {})
    # Explicit zeroes also defeat known test flags inherited from the caller.
    for key in os.environ:
        if key.startswith(("PINKHA_", "SIMCTL_CHILD_PINKHA_")):
            env[key] = "0"
    env.update(environment)
    target["OnlyTestIdentifiers"] = [METHOD]
    target["SkipTestIdentifiers"] = []


def selected_configuration(original, environment):
    raw = original.read_bytes()
    data = plistlib.loads(raw)
    targets = []
    def visit(value):
        if isinstance(value, dict):
            if value.get("BlueprintName") == "AnytypeTests" or value.get("TestBundlePath", "").endswith("AnytypeTests.xctest"):
                targets.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(data)
    require(len(targets) == 1, "Exactly one original native XCTest target required")
    configure_target(targets[0], environment)
    selected = original.with_name("UI27-Type-Preservation-" + uuid4().hex + ".xctestrun")
    with selected.open("xb") as stream:
        plistlib.dump(data, stream)
    require(original.read_bytes() == raw, "Original native test configuration changed")
    return selected


def require_ui_passed(result, methods):
    expected = {"PinkhaNativeDerivedAcceptanceUITests/testRemainingNativeSourceFilterEditing",
                "PinkhaNativeDerivedAcceptanceUITests/testRemainingUniversalTypePickersAndMixedSet"}
    require(len(methods) == 2 and set(methods) == expected and result.get("status") == "PASS"
            and all(type(result.get(k)) is int for k in ("command_exit_code", "passed", "failed", "skipped"))
            and result["command_exit_code"] == 0 and result["passed"] == 2 and result["failed"] == result["skipped"] == 0
            and len(result.get("actual_methods", {})) == 2
            and {k.removesuffix("()"): v for k, v in result.get("actual_methods", {}).items()} == {k: "Passed" for k in expected},
            "Both exact UI methods and their owned-App teardown must pass before native postflight")


def validate_native_receipt(baseline, baseline_sha, udid, receipt, result, installation, installation_sha):
    validate_installation(installation, baseline, baseline_sha, installation.get("fixtureSHA256"), udid,
                          installation.get("originalDirectories"), installation.get("codeCarriersSHA256"))
    require(sha256(json.dumps(installation, sort_keys=True, separators=(",", ":")).encode()) == installation_sha,
            "Native postflight installation bytes differ")
    require(result.get("status") == "PASS" and result.get("command_exit_code") == 0
            and all(type(result.get(key)) is int for key in ("passed", "failed", "skipped", "command_exit_code"))
            and result.get("passed") == 1 and result.get("failed") == 0 and result.get("skipped") == 0
            and result.get("selected") == [METHOD] and len(result.get("actual_methods", {})) == 1
            and {k.removesuffix("()"): v for k, v in result.get("actual_methods", {}).items()} == {METHOD: "Passed"},
            "Native postflight must pass exactly its one selected method")
    devices = result.get("actual_devices")
    require(isinstance(devices, list) and devices and all(
        d.get("deviceId", "").lower() == udid.lower() and d.get("architecture") == "arm64"
        and d.get("osVersion", "").split(".")[0] == "27" for d in devices), "Postflight actual device differs")
    require(isinstance(receipt, dict) and set(receipt) == {"schemaVersion", "status", "scope", "binding", "baselineSHA256",
        "installationSHA256", "directoriesBefore", "preparationPID", "postflightPID", "verifierCallsMutationAPI", "state"},
        "Unknown native postflight receipt schema")
    require(type(receipt["schemaVersion"]) is int and receipt["schemaVersion"] == 2 and receipt["status"] == "PASS"
            and receipt["scope"] == "FINAL_UI_TYPE_ROUNDTRIP" and receipt["binding"] == baseline["binding"]
            and receipt["baselineSHA256"] == baseline_sha and receipt["preparationPID"] == baseline["preparationPID"]
            and receipt["installationSHA256"] == installation_sha
            and type(receipt["postflightPID"]) is int and receipt["postflightPID"] > 1
            and receipt["postflightPID"] != receipt["preparationPID"]
            and receipt["verifierCallsMutationAPI"] is False,
            "Native final preservation receipt differs from the original baseline")
    observed = receipt["directoriesBefore"]
    require(isinstance(observed, dict) and set(observed) == {"container", "middleware"},
            "Native initial directory proof is missing")
    for name in ("container", "middleware"):
        validate_directory(observed[name], installation["currentDirectories"][name])
    # Only the OS-proved location is replaced. All original account, canonical
    # bytes/IDs/timestamps, complete Tag/link sets and Type fields stay exact.
    expected = {**baseline["state"], **observed}
    require(receipt["state"] == expected, "Native final preservation state differs from the original baseline")
    return {"status": "PASS", "scope": receipt["scope"], "baseline_sha256": baseline_sha,
            "installation_sha256": installation_sha, "stopped_native_install_continuity": True,
            "native_preparations": 1, "ui_methods": 2, "native_postflight_methods": 1,
            "canonical_byte_preservation": True, "original_tag_and_links_preserved": True,
            "intermediate_canonical_states_verified": False, "full_stage2_accepted": False}


def validate_result(frozen, installation, receipt, result):
    verify_installed(frozen, installation)
    validate_installation(installation.value, frozen.value, frozen.sha256, frozen.fixture_sha256,
                          frozen.udid, frozen.directories, installation.value["codeCarriersSHA256"])
    return validate_native_receipt(frozen.value, frozen.sha256, frozen.udid, receipt, result,
                                   installation.value, installation.sha256)


def validate_saved(directory, execution, udid):
    """Parent qualification reads original baseline/receipt bytes, not a PASS label."""
    raw_baseline = read_bytes(directory / "type-preservation-baseline.json")
    raw_fixture = read_bytes(directory / "type-preservation-fixture.json")
    raw_installation = read_bytes(directory / INSTALLATION)
    raw_receipt = read_bytes(directory / "postflight/native-result.json")
    require(sha256(raw_baseline) == execution.get("preservation_baseline_sha256")
            and sha256(raw_fixture) == execution.get("preservation_fixture_sha256")
            and sha256(raw_installation) == execution.get("preservation_installation_sha256")
            and sha256(raw_receipt) == execution.get("preservation_native_receipt_sha256"),
            "Saved preservation baseline/receipt bytes changed")
    inputs = decode(read_bytes(directory / "type-preservation-inputs.json"))
    expected = execution.get("postflight_binding")
    require(isinstance(expected, dict) and expected.get("sourceSHA") == execution.get("source_sha")
            and expected.get("runID") == execution.get("run_id")
            and expected.get("runAttempt") == execution.get("run_attempt"), "Saved preservation execution binding differs")
    binding(expected["sourceSHA"], expected["runID"], expected["runAttempt"], expected["nonce"])
    require(inputs.get("binding") == expected and inputs.get("baseline_sha256") == sha256(raw_baseline)
            and inputs.get("fixture_sha256") == sha256(raw_fixture)
            and inputs.get("simulator_udid") == udid and inputs.get("source") == "FROZEN_BEFORE_UI",
            "Saved preservation pre-UI input binding differs")
    fixture = json.loads((directory / "fixture-ids.json").read_text(encoding="utf8"))
    require(decode(raw_fixture) == fixture, "Saved original fixture bytes/identity differ")
    baseline = validate_baseline(decode(raw_baseline), expected, fixture, inputs["directories"])
    carriers = json.loads((directory / "built-code-carriers.json").read_text(encoding="utf8"))
    installation = validate_installation(decode(raw_installation), baseline, sha256(raw_baseline),
        sha256(raw_fixture), udid, inputs["directories"], carriers["sha256"])
    qualified = validate_native_receipt(baseline, sha256(raw_baseline), udid,
        decode(raw_receipt), execution.get("postflight", {}), installation, sha256(raw_installation))
    require(execution.get("type_preservation") == qualified, "Saved preservation qualification differs")
    return qualified
