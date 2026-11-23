"""Fail-closed proof for one separate full-App Page154 consumer."""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import tarfile

REPOSITORY = "davidpovarsky/anytype-swift"
PRODUCER_RUN = "45098093058"
PRODUCER_SHA = "70c6aa3447baae2d8e2681228fb50236c4c60b3b"
MANIFEST_SHA = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
VERSION = "pinkha-semantic-anchor-native-page-candidate-v1-" + MANIFEST_SHA
ARTIFACTS = {
    "runtime": {"id": 14785215179, "name": "Pinkha-Semantic-Page-Production-Simulator-v1",
                "bytes": 88589034, "sha256": "e9b53214ed51e89f55f8bec0a6a53451340e8b974a58a07adbf15a8723152d44"},
    "proof": {"id": 14784363888, "name": "Pinkha-Semantic-Page-Apple-Runtime-Proof-45098093058-1",
              "bytes": 3058487, "sha256": "f5bc7c200e5b9d35f61cc5781877370a135ebb73bccdb5a39349033ea457390d"},
}
ARCHIVE_NAME = "Pinkha-Semantic-Page-Production-Simulator-v1.tar.gz"
ARCHIVE_BYTES = 88588818
ARCHIVE_SHA = "f698266c8c3cf26a3e2d5939248e2b799623cf9ef5ef944909e98648d1191144"
RECEIPT_NAME = "SemanticPageHeartBuild.json"
RECEIPT_SHA = "2fe5f2e16d083c1b05ec8297762788edf5d603f95293e87942731693d518cb93"
RUNTIME_MEMBER_BYTES = {'Lib.xcframework/Info.plist': 778,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Headers/Core.objc.h': 37635,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Headers/Lib.h': 361,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Headers/Service.objc.h': 147616,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Headers/Universe.objc.h': 563,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Headers/ref.h': 1163,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Info.plist': 547,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib': 316499632,
 'Lib.xcframework/ios-arm64-simulator/Lib.framework/Modules/module.modulemap': 157,
 'SemanticPageHeartBuild.json': 418414}
SUITE = "SemanticAnchorPage154NativeAcceptanceTests"
METHOD = "testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument"
SELECTOR = "AnytypeTests/" + SUITE + "/" + METHOD
TEST_PATH = "AnyTypeTests/Pinkha/" + SUITE + ".swift"
ATTACHMENT = "pinkha-semantic-page154-native-observation"
PROTOCOL = "pinkha-semantic-page154-apple-consumer-v1"
PASS = "PASS_ACTUAL_APP_FACTORY_EVENT_AND_READBACK"
BODY = "\u05dc\u05e4\u05e0\u05d9 e\u0301 \U0001f469\U0001f3fd\u200d\U0001f4bb \u05e1\u05d5\u05e3"
SELECTED = "e\u0301 \U0001f469\U0001f3fd\u200d\U0001f4bb"
BINDING_KEYS = {"sourceSHA", "runID", "runAttempt", "nonce"}
LIMITS = {"mountedEditorAcceptance": "NOT_RUN", "AppleColdReopen": "NOT_RUN",
          "independentStoredNativeChangeBytes": "NOT_EXPORTED",
          "physicalDevice": "NOT_RUN", "fullProductAcceptance": False}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular original evidence/source")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def relative(name):
    require(isinstance(name, str) and name and not PurePosixPath(name).is_absolute()
            and "\\" not in name and all(part not in {"", ".", ".."} for part in name.split("/")),
            "Unsafe evidence path")
    return Path(*PurePosixPath(name).parts)


def keys(value, names):
    require(isinstance(value, dict) and set(value) == set(names), "Unexpected or missing proof fields")


def hex_value(value, length=64):
    require(isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(length) + "}", value),
            "Invalid lowercase hexadecimal proof identity")


def uuid(value):
    return isinstance(value, str) and re.fullmatch(
        "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value) is not None


def identity(value):
    require(isinstance(value, str) and 0 < len(value.encode("utf8")) <= 1024
            and all(0x21 <= ord(character) <= 0x7e for character in value),
            "Invalid actual native identity")


def binding(value):
    keys(value, BINDING_KEYS)
    hex_value(value["sourceSHA"], 40); hex_value(value["nonce"], 32)
    for name in ("runID", "runAttempt"):
        require(isinstance(value[name], str) and re.fullmatch("[1-9][0-9]{0,19}", value[name])
                and int(value[name]) < 2**64, "Invalid actual run binding")
    return value


def api_run(value):
    require(isinstance(value, dict) and type(value.get("id")) is int
            and value["id"] == int(PRODUCER_RUN) and type(value.get("run_attempt")) is int
            and value["run_attempt"] == 1 and value.get("head_sha") == PRODUCER_SHA
            and value.get("event") == "workflow_dispatch" and value.get("status") == "completed"
            and value.get("conclusion") == "success"
            and value.get("repository", {}).get("full_name") == REPOSITORY
            and value.get("path") == ".github/workflows/torah-inspector-ipados27.yml",
            "The exact qualified Page154 producer run is required")


def api_artifact(value, kind):
    expected = ARTIFACTS[kind]
    require(isinstance(value, dict) and type(value.get("id")) is int
            and value["id"] == expected["id"] and value.get("name") == expected["name"]
            and value.get("size_in_bytes") == expected["bytes"]
            and value.get("digest") == "sha256:" + expected["sha256"] and value.get("expired") is False
            and value.get("workflow_run", {}).get("id") == int(PRODUCER_RUN)
            and value.get("workflow_run", {}).get("head_sha") == PRODUCER_SHA,
            "Exact Page154 artifact identity/digest required")


def producer_proof(build, packaged, manifest, expected_files):
    expected_source = {name: row["after_sha256"] for name, row in manifest["files"].items()}
    require(build.get("status") == "BUILT_PAGE154_APPLE_FRAMEWORK_NOT_EXECUTED"
            and build.get("phase") == "COMPLETE" and build.get("app_sha") == PRODUCER_SHA
            and build.get("run_id") == PRODUCER_RUN and build.get("run_attempt") == "1"
            and build.get("source_manifest_sha256") == MANIFEST_SHA
            and build.get("runtime_version") == VERSION and build.get("native_source_count") == 154
            and build.get("native_source_sha256") == expected_source
            and build.get("native_module_sha256") == manifest["module_sha256"]
            and build.get("framework_files_sha256") == expected_files
            and build.get("archive_sha256") == ARCHIVE_SHA and build.get("archive_bytes") == ARCHIVE_BYTES
            and build.get("packaged_receipt_sha256") == RECEIPT_SHA
            and all(type(build.get(key)) is int and build[key] == 0
                    for key in ("native_tests_executed", "old_tests_executed", "apple_product_tests_executed", "app_builds")),
            "Original Apple producer proof/byte closure differs")
    require(packaged.get("status") == "APPLE_FRAMEWORK_BUILT_NOT_EXECUTED"
            and packaged.get("integration_sha") == PRODUCER_SHA
            and packaged.get("github_run_id") == PRODUCER_RUN and packaged.get("github_run_attempt") == "1"
            and packaged.get("source_manifest_sha256") == MANIFEST_SHA
            and packaged.get("expected_app_get_version") == VERSION
            and packaged.get("native_source_sha256") == expected_source
            and packaged.get("native_module_sha256") == manifest["module_sha256"]
            and packaged.get("files_sha256") == expected_files
            and packaged.get("fixture_included") is False
            and packaged.get("target_architecture") == "arm64"
            and packaged.get("target_environment") == "simulator",
            "Packaged production framework identity differs")
    require(len(expected_files) == 9, "Exact nine-file production framework required")
    generated = packaged.get("generated_entry", {})
    require(generated.get("entry") == "ServicePinkhaSemanticAnchorCapture"
            and generated.get("swift_typecheck") == "PASS_ACTUAL_GENERATED_MODULE"
            and generated.get("runtime_execution") == "NOT_RUN"
            and generated.get("status") == "ACTUAL_GENERATED_HEADER_AND_DEFINED_BINARY_SYMBOL",
            "Original actual generated entry proof is absent")


def install_runtime(archive, middleware, expected_files):
    """Extract only pinned regular framework files; never generic tar extraction."""
    require(archive.stat().st_size == ARCHIVE_BYTES and digest(archive) == ARCHIVE_SHA,
            "Exact original compressed runtime bytes required")
    framework = middleware / "Lib.xcframework"
    packaged = middleware / RECEIPT_NAME
    require(not framework.exists() and not packaged.exists(), "Fresh distinct runtime installation required")
    allowed = {"Lib.xcframework/" + name: value for name, value in expected_files.items()}
    allowed[RECEIPT_NAME] = RECEIPT_SHA
    directories = {parent.as_posix() for name in allowed for parent in PurePosixPath(name).parents
                   if parent.as_posix() != "."}
    observed = set()
    with tarfile.open(archive, "r:gz") as stream:
        for member in stream:
            # BSD tar may append a slash to directory names only.
            name = member.name.rstrip("/") if member.isdir() else member.name
            path = relative(name)
            require(name not in observed and not member.issym() and not member.islnk(),
                    "Duplicate or linked runtime archive member")
            observed.add(name)
            destination = middleware / path
            require(destination.resolve().is_relative_to(middleware.resolve()), "Runtime path escapes installation")
            if member.isdir():
                require(name in directories, "Unreviewed runtime directory")
                destination.mkdir(parents=True, exist_ok=True)
            else:
                require(member.isfile() and name in allowed and member.size == RUNTIME_MEMBER_BYTES.get(name),
                        "Unreviewed runtime regular member")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                destination.chmod(member.mode & 0o777)
                require(digest(destination) == allowed[name], "Original framework member bytes differ")
    require(set(allowed) <= observed and observed <= set(allowed) | directories, "Incomplete runtime archive")
    framework_unchanged(framework, expected_files)
    return json.loads(packaged.read_bytes())


def framework_unchanged(framework, expected_files):
    observed = {path.relative_to(framework).as_posix(): digest(path)
                for path in framework.rglob("*") if path.is_file() or path.is_symlink()}
    require(observed == expected_files, "Installed production framework bytes changed")


def copied_descriptor(original, destination, expected_binding):
    binding(expected_binding)
    require(original != destination and original.parent.resolve() == destination.parent.resolve()
            and not destination.exists(), "Fresh sibling xctestrun required")
    raw = original.read_bytes()
    value = plistlib.loads(raw)
    require(value.get("__xctestrun_metadata__", {}).get("FormatVersion") == 2
            and len(value.get("TestConfigurations", [])) == 1, "One original v2 test configuration required")
    configuration = value["TestConfigurations"][0]
    selected = [target for target in configuration.get("TestTargets", [])
                if target.get("BlueprintName") == "AnytypeTests"]
    require(len(selected) == 1 and selected[0].get("IsEnabled", True) is True,
            "Actual AnytypeTests target is absent or disabled")
    before = copy.deepcopy(selected[0]); target = selected[0]
    existing = target.get("EnvironmentVariables", {})
    require(isinstance(existing, dict) and all(isinstance(k, str) and isinstance(v, str)
                                             for k, v in existing.items()), "Malformed original test environment")
    additions = {"PINKHA_SEMANTIC_PAGE154_APPLE_CONSUMER": "1"}
    for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"),
                        ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
        additions["PINKHA_SEMANTIC_PAGE154_" + suffix] = expected_binding[key]
    require(not set(additions).intersection(existing), "Refuse stale/replayed descriptor binding")
    target["EnvironmentVariables"] = existing | additions
    target["OnlyTestIdentifiers"] = [SUITE + "/" + METHOD]
    configuration["TestTargets"] = [target]
    with destination.open("xb") as output:
        plistlib.dump(value, output, sort_keys=False)
    restored = copy.deepcopy(target)
    if "OnlyTestIdentifiers" in before: restored["OnlyTestIdentifiers"] = before["OnlyTestIdentifiers"]
    else: restored.pop("OnlyTestIdentifiers", None)
    if "EnvironmentVariables" in before: restored["EnvironmentVariables"] = before["EnvironmentVariables"]
    else: restored.pop("EnvironmentVariables", None)
    require(restored == before and original.read_bytes() == raw,
            "Original descriptor or non-binding values changed")
    return dict(original_sha256=digest(original), copied_sha256=digest(destination),
                binding=expected_binding, environment_keys=sorted(additions),
                testing_environment_unchanged=target.get("TestingEnvironmentVariables") ==
                    before.get("TestingEnvironmentVariables"), selector=SELECTOR)


def canonical_case(value):
    require(isinstance(value, str), "Missing actual test identity")
    value = value.removeprefix("AnytypeTests/")
    return value.removesuffix("()")


def exact_execution(summary, tree, udid):
    counts = {key: summary.get(key) for key in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(value) is int for value in counts.values()) and counts ==
            dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0)
            and summary.get("result") == "Passed", "Exactly one actual XCTest PASS and zero fail/skip required")
    destinations = summary.get("devicesAndConfigurations", [])
    require(isinstance(destinations, list) and len(destinations) == 1, "One actual test destination required")
    device = destinations[0].get("device", {})
    require(uuid(udid.lower()) and str(device.get("deviceId", "")).lower() == udid.lower()
            and str(device.get("osVersion", "")).split(".")[0] == "27"
            and device.get("architecture") == "arm64" and device.get("platform") == "iOS Simulator"
            and isinstance(device.get("osBuildNumber"), str) and device["osBuildNumber"],
            "XCTest did not run on the owned iOS27 ARM64 simulator")
    cases = []
    def walk(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                cases.append((value.get("nodeIdentifier"), value.get("result")))
            for child in value.values():
                if isinstance(child, (dict, list)): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(tree)
    require(len(cases) == 1 and canonical_case(cases[0][0]) == SUITE + "/" + METHOD
            and cases[0][1] == "Passed", "Wrong, duplicate or nonpassing actual test terminal")
    return dict(counts=counts, actual_cases=cases, device=device, selector=SELECTOR)


def decode64(value):
    require(isinstance(value, str) and len(value) <= 65536, "Unbounded base64 field")
    try: raw = base64.b64decode(value, validate=True)
    except (binascii.Error, UnicodeError, ValueError) as error: raise ValueError("Invalid proof base64") from error
    require(base64.b64encode(raw).decode("ascii") == value, "Noncanonical proof base64")
    return raw


def protobuf(raw):
    """Read bounded wire fields, retaining exact non-mark field bytes."""
    require(isinstance(raw, bytes) and len(raw) <= 65536, "Unbounded protobuf observation")
    fields = []; offset = 0
    def varint():
        nonlocal offset
        result = 0
        for index in range(10):
            require(offset < len(raw), "Truncated protobuf varint")
            byte = raw[offset]; offset += 1
            require(index < 9 or byte <= 1, "Overflow protobuf varint")
            result |= (byte & 0x7f) << (7 * index)
            if byte < 0x80: return result
        raise ValueError("Oversized protobuf varint")
    while offset < len(raw):
        start = offset; tag = varint(); number, wire = tag >> 3, tag & 7
        require(0 < number < 2**29 and wire in {0, 1, 2, 5}, "Unsupported protobuf field")
        if wire == 0: value = varint()
        else:
            length = varint() if wire == 2 else (8 if wire == 1 else 4)
            require(offset + length <= len(raw), "Truncated protobuf field")
            value = raw[offset:offset+length]; offset += length
        fields.append((number, wire, value, raw[start:offset]))
        require(len(fields) <= 4096, "Too many protobuf fields")
    return fields


def one(fields, number, wire, default=None):
    values = [row for row in fields if row[0] == number]
    require(len(values) <= 1 and (not values or values[0][1] == wire), "Ambiguous protobuf field")
    return values[0][2] if values else default


def marks(raw):
    rows = protobuf(raw); result = []
    require(all(number == 1 and wire == 2 for number, wire, _, _ in rows), "Unknown mark container fields")
    for _, _, value, _ in rows:
        fields = protobuf(value)
        require({row[0] for row in fields} <= {1, 2, 3}, "Unexpected native mark field")
        extent = protobuf(one(fields, 1, 2, b""))
        require({row[0] for row in extent} <= {1, 2}, "Unexpected native mark range field")
        result.append(dict(from_=one(extent, 1, 0, 0), to=one(extent, 2, 0, 0),
                           kind=one(fields, 2, 0, 0), param=one(fields, 3, 2, b"").decode("utf8")))
    return [{"from": row["from_"], "to": row["to"], "kind": row["kind"], "param": row["param"]} for row in result]


def block(raw, block_id):
    fields = protobuf(raw)
    require(one(fields, 1, 2) == block_id.encode("utf8") and one(fields, 3, 2) == b"",
            "Actual block identity/explicit-empty restrictions differs")
    require([row[0] for row in fields if row[0] >= 11] == [14], "Only native text block content is admitted")
    text = protobuf(one(fields, 14, 2, b""))
    require(one(text, 1, 2) == BODY.encode("utf8") and one(text, 2, 0, 0) == 0,
            "Actual native paragraph text bytes differ")
    raw_marks = one(text, 3, 2)
    require(raw_marks is not None, "Native marks field missing")
    return dict(fields=fields, text=text, marks=marks(raw_marks), raw_marks=raw_marks)


def snapshot_digest(native_marks):
    raw = json.dumps({"text": BODY, "marks": native_marks}, ensure_ascii=False, separators=(",", ":"))
    for character in ("&", "<", ">", "\u2028", "\u2029"):
        raw = raw.replace(character, "\\u%04x" % ord(character))
    return hashlib.sha256(raw.encode("utf8")).hexdigest()


def observation(value, expected_binding):
    binding(expected_binding)
    keys(value, {"protocol", "status", "binding", "runtime", "identity", "selection",
                 "native", "document", "publication", "cleanup", "limits"})
    require(len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf8")) <= 65536,
            "Observation exceeds attachment bound")
    require(value["protocol"] == PROTOCOL and value["status"] == PASS
            and value["binding"] == expected_binding, "Wrong observation or replayed source/run/nonce")
    runtime = value["runtime"]; keys(runtime, {"version", "manifestSHA256", "producerRunID", "processID"})
    require(runtime["version"] == VERSION and runtime["manifestSHA256"] == MANIFEST_SHA
            and runtime["producerRunID"] == PRODUCER_RUN and type(runtime["processID"]) is int
            and runtime["processID"] > 1, "Actual runtime/process identity differs")
    owner = value["identity"]; keys(owner, {"accountID", "spaceID", "objectID", "blockID", "anchorID", "ownerGeneration"})
    for name in ("accountID", "spaceID", "objectID", "blockID"): identity(owner[name])
    require(uuid(owner["anchorID"]) and uuid(owner["ownerGeneration"]), "Actual anchor/owner generation missing")
    selection = value["selection"]; keys(selection, {"location", "length", "textUTF8Base64", "selectedUTF8Base64"})
    require(type(selection["location"]) is int and selection["location"] == 5
            and type(selection["length"]) is int and selection["length"] == 10
            and decode64(selection["textUTF8Base64"]) == BODY.encode("utf8")
            and decode64(selection["selectedUTF8Base64"]) == SELECTED.encode("utf8"),
            "Exact decomposed/emoji UTF16 selection differs")
    native = value["native"]; keys(native, {"beforeBlockBase64", "afterBlockBase64", "receipt"})
    before = block(decode64(native["beforeBlockBase64"]), owner["blockID"])
    after = block(decode64(native["afterBlockBase64"]), owner["blockID"])
    require([row[3] for row in before["fields"] if row[0] != 14] ==
            [row[3] for row in after["fields"] if row[0] != 14]
            and [row[3] for row in before["text"] if row[0] != 3] ==
                [row[3] for row in after["text"] if row[0] != 3], "Native non-mark block bytes changed")
    component = lambda text: base64.urlsafe_b64encode(text.encode("utf8")).decode("ascii").rstrip("=")
    marker = "pinkha-anchor://v1/" + component(owner["spaceID"]) + "/" + component(owner["objectID"]) + "/" + owner["anchorID"]
    original_mark = {"from": 0, "to": 4, "kind": 3, "param": ""}
    added_mark = {"from": 5, "to": 15, "kind": 5, "param": marker}
    require(before["marks"] == [original_mark] and len(after["marks"]) == 2
            and sorted(after["marks"], key=lambda row: row["from"]) == [original_mark, added_mark],
            "Original native bold mark or exact added semantic link differs")
    receipt = native["receipt"]; keys(receipt, {"version", "spaceID", "objectID", "blockID", "anchorID", "marker",
        "changeID", "nativeChangeSHA256", "beforeTextMarksSHA256", "afterTextMarksSHA256"})
    require(type(receipt["version"]) is int and receipt["version"] == 1
            and all(receipt[key] == owner[key] for key in ("spaceID", "objectID", "blockID", "anchorID"))
            and receipt["marker"] == marker, "Native receipt carrier/anchor identity differs")
    identity(receipt["changeID"]); hex_value(receipt["nativeChangeSHA256"])
    require(receipt["beforeTextMarksSHA256"] == snapshot_digest(before["marks"])
            and receipt["afterTextMarksSHA256"] == snapshot_digest(after["marks"]),
            "Returned native snapshot digests differ from original protobuf bytes")
    document = value["document"]; keys(document, {"spaceID", "objectID", "beforeTextUTF8Base64",
        "afterTextUTF8Base64", "beforeMarksBase64", "afterMarksBase64"})
    require(document["spaceID"] == owner["spaceID"] and document["objectID"] == owner["objectID"]
            and decode64(document["beforeTextUTF8Base64"]) == decode64(document["afterTextUTF8Base64"]) ==
                BODY.encode("utf8")
            and decode64(document["beforeMarksBase64"]) == before["raw_marks"]
            and decode64(document["afterMarksBase64"]) == after["raw_marks"],
            "Existing BaseDocument did not reflect exact native bytes")
    require(value["publication"] == {"handler": "InvocationMesagesHandler", "serviceApplyCalls": 1,
                "ownerGeneration": owner["ownerGeneration"], "documentObservedBeforeIndependentReadback": True}
            and type(value["publication"]["serviceApplyCalls"]) is int
            and value["publication"]["documentObservedBeforeIndependentReadback"] is True,
            "Ordinary App event publication/owner generation observation differs")
    require(value["cleanup"] == {key: True for key in ("documentClosed", "accountStopped", "accountNotRunning",
                                                     "leaseRetired", "appShutdown")}
            and all(item is True for item in value["cleanup"].values()), "Actual orderly cleanup incomplete")
    require(value["limits"] == LIMITS and value["limits"]["fullProductAcceptance"] is False,
            "Consumer proof scope was broadened")
    return dict(status=PASS, binding=expected_binding, identity=owner, runtime=runtime,
                native_change_id=receipt["changeID"], native_change_sha256=receipt["nativeChangeSHA256"],
                before_snapshot_sha256=receipt["beforeTextMarksSHA256"],
                after_snapshot_sha256=receipt["afterTextMarksSHA256"], limits=LIMITS)


def attachment(directory, udid):
    manifest = json.loads((directory / "manifest.json").read_bytes())
    require(isinstance(manifest, list), "Actual xcresult attachment manifest missing")
    found = []
    for row in manifest:
        require(isinstance(row, dict), "Malformed actual attachment row")
        for item in row.get("attachments", []):
            if not str(item.get("suggestedHumanReadableName", "")).startswith(ATTACHMENT + "_"): continue
            require(canonical_case(row.get("testIdentifier")) == SUITE + "/" + METHOD
                    and str(item.get("deviceId", "")).lower() == udid.lower()
                    and item.get("isAssociatedWithFailure") is False,
                    "Observation attachment belongs to another XCTest/device")
            path = directory / relative(item.get("exportedFileName"))
            require(path.parent == directory and path.is_file() and not path.is_symlink()
                    and path.stat().st_size <= 65536, "Unbounded/unsafe actual observation attachment")
            found.append(path)
    require(len(found) == 1, "Exactly one original observation attachment required")
    return found[0]
