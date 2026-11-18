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
from uuid import uuid4

METHOD = "TorahStage2TypePreservationTests/verifyExistingTypeRoundtrip"
SUITE = METHOD.split("/")[0]
PREFIX = "type-preservation"
BASELINE = "pinkha-type-preservation-baseline.json"
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


def freeze(container, evidence, expected_binding, fixture, udid):
    container = container.resolve(strict=True)
    require(udid.lower() in {part.lower() for part in container.parts}, "Container is outside its owned simulator")
    destination = evidence / "type-preservation-baseline.json"
    require(not destination.resolve().is_relative_to(container), "Frozen baseline must be outside mutable App data")
    raw = read_bytes(container / "Library/Application Support" / BASELINE)
    directories = {"container": directory_identity(container),
                   "middleware": directory_identity(container / "Library/Application Support/Anytype/middleware-go")}
    value = validate_baseline(decode(raw), expected_binding, fixture, directories)
    with destination.open("xb") as stream:
        stream.write(raw)
    frozen = FrozenBaseline(destination, sha256(raw), value, directories, container, udid)
    verify_frozen(frozen)
    return frozen


def verify_frozen(frozen, observed_container=None):
    require(sha256(read_bytes(frozen.path)) == frozen.sha256, "Frozen original baseline bytes changed")
    if observed_container is not None:
        require(observed_container.resolve(strict=True) == frozen.container, "Postflight App data container changed")
    for name in ("container", "middleware"):
        require(directory_identity(Path(frozen.directories[name]["path"])) == frozen.directories[name],
                "Original container/store directory was recreated or replaced")


def environment(frozen):
    verify_frozen(frozen)
    result = {key: "0" for key in DISABLED_FLAGS}
    result.update(binding_environment(frozen.value["binding"]))
    result.update(PINKHA_TYPE_PRESERVATION_POSTFLIGHT="1", PINKHA_TYPE_PRESERVATION_BASELINE_SHA256=frozen.sha256,
                  PINKHA_TYPE_PRESERVATION_BASELINE_BASE64=base64.b64encode(read_bytes(frozen.path)).decode("ascii"))
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


def validate_native_receipt(baseline, baseline_sha, udid, receipt, result):
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
        "preparationPID", "postflightPID", "verifierCallsMutationAPI", "state"}, "Unknown native postflight receipt schema")
    require(type(receipt["schemaVersion"]) is int and receipt["schemaVersion"] == 1 and receipt["status"] == "PASS"
            and receipt["scope"] == "FINAL_UI_TYPE_ROUNDTRIP" and receipt["binding"] == baseline["binding"]
            and receipt["baselineSHA256"] == baseline_sha and receipt["preparationPID"] == baseline["preparationPID"]
            and type(receipt["postflightPID"]) is int and receipt["postflightPID"] > 1
            and receipt["postflightPID"] != receipt["preparationPID"]
            and receipt["verifierCallsMutationAPI"] is False and receipt["state"] == baseline["state"],
            "Native final preservation receipt differs from the original baseline")
    return {"status": "PASS", "scope": receipt["scope"], "baseline_sha256": baseline_sha,
            "native_preparations": 1, "ui_methods": 2, "native_postflight_methods": 1,
            "canonical_byte_preservation": True, "original_tag_and_links_preserved": True,
            "intermediate_canonical_states_verified": False, "full_stage2_accepted": False}


def validate_result(frozen, receipt, result):
    verify_frozen(frozen)
    return validate_native_receipt(frozen.value, frozen.sha256, frozen.udid, receipt, result)


def validate_saved(directory, execution, udid):
    """Parent qualification reads original baseline/receipt bytes, not a PASS label."""
    raw_baseline = read_bytes(directory / "type-preservation-baseline.json")
    raw_receipt = read_bytes(directory / "postflight/native-result.json")
    require(sha256(raw_baseline) == execution.get("preservation_baseline_sha256")
            and sha256(raw_receipt) == execution.get("preservation_native_receipt_sha256"),
            "Saved preservation baseline/receipt bytes changed")
    inputs = decode(read_bytes(directory / "type-preservation-inputs.json"))
    expected = execution.get("postflight_binding")
    require(isinstance(expected, dict) and expected.get("sourceSHA") == execution.get("source_sha")
            and expected.get("runID") == execution.get("run_id")
            and expected.get("runAttempt") == execution.get("run_attempt"), "Saved preservation execution binding differs")
    binding(expected["sourceSHA"], expected["runID"], expected["runAttempt"], expected["nonce"])
    require(inputs.get("binding") == expected and inputs.get("baseline_sha256") == sha256(raw_baseline)
            and inputs.get("simulator_udid") == udid and inputs.get("source") == "FROZEN_BEFORE_UI",
            "Saved preservation pre-UI input binding differs")
    fixture = json.loads((directory / "fixture-ids.json").read_text(encoding="utf8"))
    baseline = validate_baseline(decode(raw_baseline), expected, fixture, inputs["directories"])
    qualified = validate_native_receipt(baseline, sha256(raw_baseline), udid,
                                        decode(raw_receipt), execution.get("postflight", {}))
    require(execution.get("type_preservation") == qualified, "Saved preservation qualification differs")
    return qualified
