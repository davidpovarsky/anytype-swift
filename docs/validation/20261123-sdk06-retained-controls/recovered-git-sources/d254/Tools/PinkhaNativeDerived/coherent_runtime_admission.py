"""Admit only the frozen coherent production simulator Lib and original Apple proof.

This installer re-reads an existing xcresult; it never executes a product test.
The fixture executable's passing journey remains separate from production-app
acceptance. No test-tagged framework can be installed by this route.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import re
import shutil
import stat
import tarfile
import zipfile

from build_custom_heart import contains, digest, git, verify_framework_slices
import heart_runtime_profile as profiles

NATIVE_SOURCE = "b2fc3804426067dd1ec8318d6ea92a4bcb8e9545"
ORIGINAL_FIXTURE = "be8136a6108c00b5b687d3e587cacce611b8f2ac7dcde01efc5cb11bdd59786d"
FIXTURE_TAG = "pinkha_coherent_apple_fixture"
METHOD = "CoherentHeartAuthorityTests/testActualCombinedLibSignedAuthorityAndSharedSwiftDecoding"
APPLE_PASS = "PASS_COHERENT_HEART_IOS_FIXTURE_AND_SWIFT_CODEC"
BINARY = "ios-arm64-simulator/Lib.framework/Lib"
RAW_FILES = frozenset({"ownership.json", "native-observation.json", "coherent-observation.json",
                      "coherent-owner.pb", "coherent-reader.pb", "coherent-removed.pb",
                      "object-search-removed.pb", "object-show-removed.pb"})
MAX_ARCHIVE_BYTES = 2 * 1024**3
MAX_PROOF_FILES = 20000
MAX_JSON_BYTES = 16 * 1024**2
MODULES = ("Modules/PinkhaKit", "Modules/PinkhaHeartEngine")
require = profiles.require


def expected_producer_branch(consumer_branch):
    """The explicit continuation consumes the original shared producer proof."""
    if consumer_branch == "codex/chatgpt-wave15-acceptance-continuation-20261122":
        return "codex/chatgpt-wave15-shared-20261121"
    return consumer_branch


def json_value(raw, label):
    require(len(raw) <= MAX_JSON_BYTES, "Oversized JSON: " + label)
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "Duplicate JSON key in " + label)
            result[key] = value
        return result
    def constant(_):
        raise RuntimeError("Non-finite JSON value in " + label)
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError) as error:
        raise RuntimeError("Invalid JSON: " + label) from error


def read_bounded(path):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= MAX_JSON_BYTES,
            "Missing or oversized original source/receipt: " + str(path))
    return path.read_bytes()


def read_json(path):
    value = json_value(read_bounded(path), str(path))
    require(isinstance(value, dict), "Expected original JSON object: " + str(path))
    return value


def relative(name, directory=False):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name
            and "\x00" not in name, "Unsafe archive member")
    value = name[:-1] if directory and name.endswith("/") else name
    parts = value.split("/")
    require(all(part not in ("", ".", "..") for part in parts)
            and not PurePosixPath(value).is_absolute(), "Unsafe archive path: " + name)
    return Path(*parts)


def _member_plan(items, kind):
    require(0 < len(items) <= MAX_PROOF_FILES, "Archive member count is empty or unbounded")
    plan, seen, total = [], {}, 0
    for item in items:
        if kind == "zip":
            directory = item.is_dir()
            mode = stat.S_IFMT(item.external_attr >> 16)
            require(mode in (0, stat.S_IFDIR if directory else stat.S_IFREG)
                    and not (item.flag_bits & 1), "Archive links, special or encrypted entries are forbidden")
            name, size = item.filename, item.file_size
        else:
            directory = item.isdir()
            require((directory or item.type in (tarfile.REGTYPE, tarfile.AREGTYPE))
                    and not item.sparse, "Archive links, sparse and special files are forbidden")
            name, size = item.name, item.size
        path = relative(name, directory)
        key = path.as_posix()
        require(key not in seen, "Repeated archive member: " + key)
        require(type(size) is int and 0 <= size <= MAX_ARCHIVE_BYTES
                and (not directory or size == 0), "Unbounded archive member")
        seen[key] = directory
        total += size
        require(total <= MAX_ARCHIVE_BYTES, "Archive expands beyond its bound")
        plan.append((item, path, directory, size))
    for _, path, _, _ in plan:
        for parent in path.parents:
            if parent != Path("."):
                require(seen.get(parent.as_posix(), True), "File used as archive directory")
    return plan


def _copy_member(source, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output:
        copied = 0
        while block := source.read(min(1024**2, expected - copied + 1)):
            copied += len(block)
            require(copied <= expected, "Archive member exceeded its declared size")
            output.write(block)
    require(copied == expected, "Truncated archive member")


def safe_zip(archive, directory, expected_single=None):
    require(not directory.exists(), "Fresh ZIP staging directory required")
    with zipfile.ZipFile(archive) as zipped:
        plan = _member_plan(zipped.infolist(), "zip")
        if expected_single is not None:
            require(len(plan) == 1 and plan[0][1].as_posix() == expected_single
                    and not plan[0][2] and plan[0][3] > 0, "Unexpected original runtime artifact payload")
        directory.mkdir()
        for item, path, is_dir, size in plan:
            destination = directory / path
            if is_dir:
                destination.mkdir(parents=True, exist_ok=True)
            else:
                with zipped.open(item) as source:
                    _copy_member(source, destination, size)


def safe_tar(archive, directory):
    require(not directory.exists(), "Fresh runtime tar staging directory required")
    with tarfile.open(archive, mode="r:gz") as packed:
        plan = _member_plan(packed.getmembers(), "tar")
        require({path.parts[0] for _, path, _, _ in plan} == {"Lib.xcframework", "PinkhaNativeHeartBuild.json"},
                "Only the production framework and its receipt may be installed")
        directory.mkdir()
        for item, path, is_dir, size in plan:
            destination = directory / path
            if is_dir:
                destination.mkdir(parents=True, exist_ok=True)
            else:
                source = packed.extractfile(item)
                require(source is not None, "Missing regular archive member")
                with source:
                    _copy_member(source, destination, size)


def _sha_map(value, label):
    require(isinstance(value, dict) and value, "Missing file hashes: " + label)
    for name, sha in value.items():
        relative(name)
        require(profiles.is_sha(sha), "Invalid file hash: " + label)
    return value


def _file_map(directory):
    require(directory.is_dir() and not directory.is_symlink(), "Missing original directory")
    result = {}
    for path in directory.rglob("*"):
        require(not path.is_symlink(), "Symlink in original evidence or framework")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = digest(path)
        else:
            require(path.is_dir(), "Special original evidence file")
    return result


def consumer_modules(app):
    require(not git(app, "status", "--porcelain", "--untracked-files=all", "--", *MODULES),
            "Shared consumer modules must match their clean source checkout")
    names = [name for name in git(app, "ls-files", "-z", "--", *MODULES).split("\0") if name]
    require(names and len(names) == len(set(names)), "Missing or repeated tracked consumer module files")
    observed = {}
    for name in names:
        path = app / relative(name)
        require(name.startswith(tuple(module + "/" for module in MODULES)) and path.is_file()
                and all(not parent.is_symlink() for parent in (path, *path.parents) if parent != app),
                "Missing or linked consumer module source")
        observed[name] = digest(path)
    return observed


def validate_framework(framework, receipt, profile):
    entries = receipt.get("artifacts", [])
    require(isinstance(entries, list) and entries, "Missing production file inventory")
    names = [entry.get("path") for entry in entries]
    require(all(isinstance(name, str) for name in names) and len(names) == len(set(names)),
            "Duplicate or invalid production file inventory")
    expected = _sha_map({entry["path"]: entry.get("sha256") for entry in entries}, "production framework")
    observed = _file_map(framework)
    require(observed == expected and BINARY in observed, "Production framework bytes or file inventory differ")
    try:
        plist = plistlib.loads((framework / "Info.plist").read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException) as error:
        raise RuntimeError("Invalid production XCFramework descriptor") from error
    libraries = plist.get("AvailableLibraries", [])
    require(isinstance(libraries, list) and len(libraries) == 1, "Exactly one simulator library is required")
    library = libraries[0]
    require(library.get("LibraryIdentifier") == "ios-arm64-simulator"
            and library.get("LibraryPath") == "Lib.framework"
            and library.get("SupportedArchitectures") == ["arm64"]
            and library.get("SupportedPlatform") == "ios"
            and library.get("SupportedPlatformVariant") == "simulator", "Wrong native platform or architecture")
    for name in observed:
        for forbidden in (b"PinkhaCoherentAppleAuthorityFixture", b"pinkha_coherent_apple_fixture", b"coherentAppleBridgeSHA"):
            require(not contains(framework / name, forbidden), "Test-only bridge found in production framework")
    slices = verify_framework_slices(framework, profile.binary_marker)
    expected_slice = dict(path=BINARY, architecture="arm64", sha256=observed[BINARY], marker=profile.binary_marker)
    require(slices == [expected_slice] and receipt.get("binary_slices") == slices,
            "Actual production binary slice differs from its original receipt")
    return observed


def validate_build(proof, receipt_raw, inventory, profile, producer, archive_sha):
    receipt = json_value(receipt_raw, "packaged build receipt")
    profiles.validate_build(profile, receipt, inventory, producer["run_id"], producer)
    require(receipt.get("selected_framework") == "production" and receipt.get("fixture_tag") is None
            and receipt.get("bridge_sha256") is None and receipt.get("fixture_source_sha256") == {}
            and receipt.get("native_source_run") == profiles.COHERENT_NATIVE_RUN
            and receipt.get("native_source_sha") == NATIVE_SOURCE
            and type(receipt.get("native_source_count")) is int and receipt["native_source_count"] == 139
            and type(receipt.get("native_test_invocations")) is int and receipt["native_test_invocations"] == 0
            and receipt.get("capability_marker") == "pinkha-native-t5-lookup-v1-" + profile.patch_sha256,
            "Production receipt has a fixture or an unqualified native source")
    require(read_bounded(proof / "production/custom-heart-build.json") == receipt_raw,
            "Production tar and original producer proof have different receipts")
    artifact = read_json(proof / "production/runtime-artifact.json")
    required = dict(status="APPLE_RUNTIME_ARTIFACT_BUILT_NOT_EXECUTED", path=profile.archive_name,
                    sha256=archive_sha, receipt_sha256=profiles.digest_bytes(receipt_raw),
                    runtime_variant=profile.name, fixture_included=False,
                    integration_sha=producer["source_sha"], github_run_id=producer["run_id"],
                    github_run_attempt=producer["run_attempt"], patch_sha256=profile.patch_sha256,
                    inventory_sha256=profile.inventory_sha256, heart_sha=inventory["heart_sha"])
    require(all(artifact.get(key) == value and type(artifact.get(key)) is type(value) for key, value in required.items()),
            "Original artifact receipt lost its source/run/attempt/bytes")
    build = read_json(proof / "build.json")
    required = dict(status="BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED",
                    app_sha=producer["source_sha"], run_id=producer["run_id"], run_attempt=producer["run_attempt"],
                    native_run=profiles.COHERENT_NATIVE_RUN, native_source=NATIVE_SOURCE,
                    native_source_count=139, patch_sha256=profile.patch_sha256,
                    inventory_sha256=profile.inventory_sha256, runtime_version=profile.version,
                    old_tests_executed=0, production_binary_execution="NOT_RUN")
    require(all(build.get(key) == value and type(build.get(key)) is type(value) for key, value in required.items()),
            "Original combined Apple build scope/source differs")
    sources = {entry["path"]: entry["after_sha256"] for entry in inventory["files"]}
    require(build.get("native_source_sha256") == sources
            and read_json(proof / "native-source-after.json") == sources,
            "Original combined build changed the qualified139 native source")
    frameworks = build.get("frameworks", {})
    require(set(frameworks) == {"production", "fixture"}, "Missing separate production/fixture build")
    production, fixture = frameworks["production"], frameworks["fixture"]
    require(production.get("fixture_compiled") is False and production.get("fixture_tag") is None
            and fixture.get("fixture_compiled") is True and fixture.get("fixture_tag") == FIXTURE_TAG
            and profiles.is_sha(production.get("binary_sha256")) and profiles.is_sha(fixture.get("binary_sha256"))
            and production["binary_sha256"] != fixture["binary_sha256"]
            and production.get("artifact_name") == profile.archive_name
            and production.get("artifact_sha256") == archive_sha
            and production.get("binary_slices") == receipt["binary_slices"],
            "Fixture binary was substituted for the production binary")
    files = {entry["path"]: entry["sha256"] for entry in receipt["artifacts"]}
    require(production.get("files_sha256") == files and files.get(BINARY) == production["binary_sha256"],
            "Original build does not bind the installed production binary")
    fixture_files = _sha_map(fixture.get("files_sha256"), "fixture framework")
    require(fixture_files.get(BINARY) == fixture["binary_sha256"] and profiles.is_sha(build.get("bridge_sha256"))
            and build.get("original_fixture_sha256") == ORIGINAL_FIXTURE,
            "Fixture runtime or its native assertion identity is incomplete")
    return receipt, build


def _fields(raw):
    require(isinstance(raw, bytes) and len(raw) <= 2 * 1024**2, "Unbounded original protobuf")
    position, result = 0, []
    def varint():
        nonlocal position
        value = 0
        for shift in range(0, 70, 7):
            require(position < len(raw), "Truncated protobuf varint")
            byte = raw[position]; position += 1
            value |= (byte & 127) << shift
            if byte < 128:
                require(shift == 0 or byte != 0, "Overlong protobuf varint")
                return value
        raise RuntimeError("Oversized protobuf varint")
    while position < len(raw):
        key = varint(); number, kind = key >> 3, key & 7
        require(number > 0 and kind in (0, 2), "Unexpected protobuf field")
        if kind == 0:
            value = varint()
        else:
            size = varint()
            require(size <= len(raw) - position, "Truncated protobuf bytes")
            value = raw[position:position+size]; position += size
        result.append((number, kind, value))
        require(len(result) <= 1024, "Too many protobuf fields")
    return result


def _one(fields, number, kind, default=None):
    values = [value for field, wire, value in fields if field == number and wire == kind]
    require(len(values) <= 1 and not any(field == number and wire != kind for field, wire, _ in fields),
            "Repeated or mistyped singleton protobuf field")
    return values[0] if values else default


def validate_raw_native(actual, build, profile, producer, native_dir):
    expected = dict(status=APPLE_PASS, app_sha=producer["source_sha"], run_id=producer["run_id"],
                    run_attempt=producer["run_attempt"], production_binary_execution="NOT_RUN",
                    full_app_acceptance="NOT_RUN", network_acl_transport="NOT_RUN", fresh_ios_process_reopen="NOT_RUN")
    require(set(actual) == set(expected) | {"nonce", "pid", "native", "shared_swift_codec"}
            and all(actual.get(key) == value for key, value in expected.items())
            and type(actual["pid"]) is int and actual["pid"] > 0
            and isinstance(actual["nonce"], str) and re.fullmatch(r"[0-9a-f]{32}", actual["nonce"]),
            "Wrong original actual Apple attachment")
    native = actual["native"]
    expected_native = dict(status="PASS_ACTUAL_COHERENT_APPLE_FIXTURE", nonce=actual["nonce"], pid=actual["pid"],
        bridge_sha256=build["bridge_sha256"], original_fixture_sha256=ORIGINAL_FIXTURE,
        runtime_version=profile.version, heart_sha=profiles.attachment.HEART_SHA,
        production_binary_executed=False, fixture_tag=FIXTURE_TAG,
        network_acl_transport="NOT_RUN", full_app_acceptance="NOT_RUN")
    require(isinstance(native, dict) and set(native) == set(expected_native) | {"files", "files_sha256", "account_id", "space_id", "operation_id"}
            and all(native.get(key) == value and type(native.get(key)) is type(value) for key, value in expected_native.items())
            and native.get("operation_id") == actual["nonce"]
            and all(isinstance(native[key], str) and native[key] for key in ("account_id", "space_id")),
            "Wrong native bridge attachment")
    require(isinstance(native["files"], dict) and isinstance(native["files_sha256"], dict)
            and set(native["files"]) == set(native["files_sha256"]) == RAW_FILES
            and set(_file_map(native_dir)) == RAW_FILES, "Missing or extra original native files")
    raw = {}
    for name in RAW_FILES:
        require(isinstance(native["files"][name], str) and len(native["files"][name]) < 3 * 1024**2,
                "Unbounded original native attachment file")
        try:
            raw[name] = base64.b64decode(native["files"][name], validate=True)
        except ValueError as error:
            raise RuntimeError("Invalid original native attachment encoding") from error
        require(0 < len(raw[name]) < 2 * 1024**2 and raw[name] == (native_dir / name).read_bytes()
                and profiles.digest_bytes(raw[name]) == native["files_sha256"][name], "Original native bytes were changed")
    coherent = json_value(raw["coherent-observation.json"], "coherent native observation")
    t5 = json_value(raw["native-observation.json"], "T5 native observation")
    owner = json_value(raw["ownership.json"], "native account ownership")
    require(owner == dict(nonce=actual["nonce"], protocol="pinkha-t5-signed-local-revocation-v2", synthetic_only=True),
            "Original account ownership is missing")
    require(coherent.get("status") == "PASS_COHERENT_SIGNED_AUTHORITY"
            and t5.get("status") == "PASS_LOCAL_SIGNED_REVOCATION", "Native journeys did not pass")
    for key in ("account_id_sha256", "space_id_sha256", "object_id_sha256", "pid", "nonce", "heart_sha", "runtime_version", "fixture_sha256"):
        require(coherent.get(key) == t5.get(key), "T2 and T5 used different native authority: " + key)
    require(coherent.get("pid") == actual["pid"] and coherent.get("nonce") == actual["nonce"]
            and coherent.get("heart_sha") == native["heart_sha"] and coherent.get("runtime_version") == profile.version
            and coherent.get("fixture_sha256") == ORIGINAL_FIXTURE
            and coherent.get("stages") == ["owner", "reader", "removed"]
            and coherent.get("rpc_calls") == {"PinkhaTorahOperationsAppend": 1, "PinkhaTorahAuthorizedOperationRead": 3},
            "Original coherent journey source/process/stages differ")
    for key in ("same_runtime_account_space_target", "owner_positive", "reader_positive", "exact_signed_bytes_and_provenance", "account_stop_verified"):
        require(coherent.get(key) is True, "Missing coherent assertion: " + key)
    for key in ("same_engine_account", "populated_native_cache", "reader_positive", "had_read_permission", "read_key_rotated", "account_stop_verified", "object_search_explicit_denial", "object_show_explicit_denial"):
        require(t5.get(key) is True, "Missing actual T5 assertion: " + key)
    require(t5.get("current_permission") == "none" and t5.get("read_key_id_before") != t5.get("read_key_id_after")
            and isinstance(t5.get("read_key_id_after"), str) and t5["read_key_id_after"]
            and t5.get("native_acl_updater") == "NOT_REPLACED_OR_SUPPRESSED" and t5.get("local_signed_delivery") is True
            and all(type(t5.get(key)) is int and t5[key] == 0 for key in ("object_search_rows", "object_search_total"))
            and t5.get("object_show_has_payload") is False,
            "Revoked native cache or ACL evidence is incomplete")
    require(coherent.get("ios_acceptance") == t5.get("ios_acceptance") == "NOT_RUN"
            and coherent.get("network_acl_transport") == t5.get("network_acl_transport") == "NOT_RUN"
            and coherent.get("automatic_t2_to_t5_projection") == "NOT_PROVEN"
            and t5.get("offline_unknown_revocation") == t5.get("full_t5_acceptance") == "NOT_PROVEN",
            "Original native fixture scope was relabeled")
    snapshots, variants = {}, {}
    for stage in ("owner", "reader"):
        response = _fields(raw["coherent-" + stage + ".pb"])
        error = _fields(_one(response, 1, 2))
        require({number for number, _, _ in response} == {1, 2, 3}
                and _one(error, 1, 0, 0) == 0 and _one(error, 2, 2, b"") == b""
                and _one(response, 2, 0) == 1, "Original positive wire response is not success")
        snapshot = _fields(_one(response, 3, 2)); snapshots[stage] = snapshot
        variant_raw = _one(snapshot, 8, 2)
        variant = _fields(variant_raw); variants[stage] = variant
        target = _fields(_one(variant, 5, 2)); provenance = _fields(_one(variant, 7, 2))
        require(_one(snapshot, 5, 0) == 1 and _one(snapshot, 6, 0) == 1
                and len(_one(snapshot, 7, 2, b"")) == 64 and _one(variant, 8, 0) == 2,
                "Original positive snapshot is not complete/live")
        hashes = {"account_id_sha256": _one(snapshot, 2, 2), "space_id_sha256": _one(snapshot, 3, 2),
                  "object_id_sha256": _one(target, 1, 2), "block_id_sha256": _one(target, 2, 2),
                  "claim_id_sha256": _one(variant, 1, 2), "canonical_sha256": _one(variant, 6, 2),
                  "native_change_id_sha256": _one(provenance, 2, 2)}
        require(all(isinstance(value, bytes) and value and profiles.digest_bytes(value) == coherent.get(key) for key, value in hashes.items()),
                "Original canonical operation/provenance/target differs")
        require(_one(snapshot, 2, 2) == _one(variant, 4, 2) == _one(provenance, 1, 2) == native["account_id"].encode()
                and _one(snapshot, 3, 2) == _one(variant, 3, 2) == native["space_id"].encode()
                and _one(snapshot, 4, 2) == _one(variant, 2, 2) == actual["nonce"].encode()
                and _one(provenance, 3, 2), "Original positive response has another native scope")
    require(_one(snapshots["owner"], 8, 2) == _one(snapshots["reader"], 8, 2)
            and _one(snapshots["owner"], 7, 2) != _one(snapshots["reader"], 7, 2),
            "Reader downgrade did not preserve bytes/provenance and change authority")
    removed = _fields(raw["coherent-removed.pb"])
    error = _fields(_one(removed, 1, 2)); code = _one(error, 1, 0)
    label = {4: b"native permission denied", 9: b"native candidate closure changed"}
    require(len(removed) == 2 and {number for number, _, _ in removed} == {1, 2}
            and _one(removed, 2, 0) == 1 and code in label and _one(error, 2, 2) == label[code]
            and coherent.get("removed_error_code") == code and coherent.get("removed_has_payload") is False,
            "Original revoked operation wire contains a payload or lacks typed denial")
    for stage in ("owner", "reader", "removed"):
        require(profiles.digest_bytes(raw["coherent-" + stage + ".pb"]) == coherent.get(stage + "_wire_sha256"),
                "Original native observation lost its response hash")
    for kind in ("search", "show"):
        outer = _fields(raw["object-" + kind + "-removed.pb"])
        permitted = {(1, 2)} | ({(3, 0)} if kind == "search" else set())
        description = t5.get("object_" + kind + "_error_description")
        require(description in ("PINKHA_CURRENT_SPACE_READ_DENIED_V1", "PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1")
                and t5.get("object_" + kind + "_error_code") == 2
                and len({number for number, _, _ in outer}) == len(outer)
                and all((number, wire) in permitted for number, wire, _ in outer)
                and _one(outer, 3, 0, 0) == 0
                and _fields(_one(outer, 1, 2)) == [(1, 0, 2), (2, 2, description.encode())],
                "Original revoked T5 response contains data or lacks exact authority denial")
    codec = actual["shared_swift_codec"]
    require(isinstance(codec, dict) and set(codec) == {"owner_decoded", "reader_decoded", "exact_variants", "removed_rejected", "removed_error"}
            and all(codec[name] is True for name in codec if name != "removed_error")
            and codec["removed_error"] == {4: "permissionDenied", 9: "snapshotChanged"}[code],
            "Actual shared Swift codec did not qualify the native responses")
    return codec


def validate_execution(summary, tree, actual_execution):
    expected = dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0)
    require(all(summary.get(key) == value and type(summary.get(key)) is int for key, value in expected.items())
            and all(actual_execution.get(key) == value and type(actual_execution.get(key)) is int for key, value in expected.items())
            and actual_execution.get("method") == METHOD, "Exactly one original passing Apple test without skips is required")
    destinations = summary.get("devicesAndConfigurations", [])
    require(isinstance(destinations, list) and len(destinations) == 1, "Original Apple destination is ambiguous")
    device = destinations[0].get("device", {})
    udid = actual_execution.get("udid")
    require(isinstance(udid, str) and re.fullmatch(r"[0-9A-Fa-f-]{36}", udid)
            and str(device.get("deviceId", "")).lower() == udid.lower()
            and str(device.get("osVersion", "")).split(".")[0] == "27"
            and device.get("architecture") == "arm64" and device.get("osBuildNumber")
            and actual_execution.get("device") == device, "Original proof did not execute on its iOS27 ARM64 simulator")
    cases = {}
    def visit(value):
        if isinstance(value, dict):
            if value.get("nodeType") == "Test Case":
                name = value.get("nodeIdentifier")
                require(isinstance(name, str) and name and name not in cases, "Missing or duplicate actual XCTest identifier")
                cases[name] = value.get("result")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(tree)
    require(len(cases) == 1 and list(cases.values()) == ["Passed"]
            and re.search(r"(?:^|/)" + re.escape(METHOD) + r"(?:\(|/|$)", next(iter(cases)))
            and actual_execution.get("actual_cases") == cases, "Missing, extra or nonpassing original named XCTest")


def qualify_apple(proof, profile, producer, build, evidence, command, build_lineage=None):
    host = proof / "host"
    receipt = read_json(host / "receipt.json")
    required = dict(status=APPLE_PASS, app_sha=producer["source_sha"], run_id=producer["run_id"],
                    run_attempt=producer["run_attempt"], native_run=profiles.COHERENT_NATIVE_RUN,
                    production_binary_execution="NOT_RUN", full_app_acceptance="NOT_RUN", network_acl_transport="NOT_RUN",
                    fresh_ios_process_reopen="NOT_RUN", old_native_methods_executed=0, old_swift_methods_executed=0,
                    app_capability="OFF")
    require(all(receipt.get(key) == value and type(receipt.get(key)) is type(value) for key, value in required.items()),
            "Original Apple host receipt is incomplete or overstates acceptance")
    require(receipt.get("build_receipt_sha256") == digest(proof / "build.json")
            and receipt.get("production_binary_sha256") == build["frameworks"]["production"]["binary_sha256"]
            and receipt.get("fixture_binary_sha256") == build["frameworks"]["fixture"]["binary_sha256"]
            and receipt.get("bridge_sha256") == build["bridge_sha256"], "Apple proof has another production/fixture build")
    before, after = read_json(host / "control-source-before.json"), read_json(host / "control-source-after.json")
    require(before == after and _sha_map(before, "Apple source snapshot")
            and receipt.get("source_snapshot_sha256") == profiles.json_digest(before), "Source changed during actual Apple execution")
    modules = _sha_map(receipt.get("copied_module_sha256"), "actual shared module copies")
    require(modules == {name: sha for name, sha in before.items() if name.startswith(tuple(module + "/" for module in MODULES))}
            and any(name.startswith("Modules/PinkhaKit/") for name in modules)
            and any(name.startswith("Modules/PinkhaHeartEngine/") for name in modules), "Actual shared module provenance differs")
    if build_lineage is None:
        require("build_origin" not in receipt and "build_reuse_receipt_sha256" not in receipt,
                "A distinct build origin requires separately verified immutable lineage")
    else:
        require(receipt.get("build_origin") == build_lineage["build_producer"]
                and receipt.get("build_reuse_receipt_sha256") == build_lineage["receipt_sha256"]
                and before == build_lineage["current_source"] and modules == build_lineage["modules"],
                "Actual Apple execution differs from its qualified current controller or original build lineage")
    commands = receipt.get("commands", [])
    selected = [entry for entry in commands if entry.get("name") == "ios-coherent-tests"]
    if selected and selected[0].get("argv", [])[:2] == ["xcodebuild", "test-without-building"]:
        test = selected[0]
        require(len(selected) == 1 and test.get("status") == "PASS_EXIT_0"
                and isinstance(test.get("argv"), list) and all(isinstance(value, str) for value in test["argv"])
                and [value for value in test["argv"] if value.startswith("-only-testing:")] ==
                    ["-only-testing:CoherentHeartAuthorityHarnessTests/" + METHOD]
                and test["argv"].count("-resultBundlePath") == test["argv"].count("-destination") == 1,
                "Split Apple execution is not the sole successful selected journey")
        bundle_index = test["argv"].index("-resultBundlePath") + 1
        destination_index = test["argv"].index("-destination") + 1
        require(bundle_index < len(test["argv"]) and Path(test["argv"][bundle_index]).name == "coherent-heart.xcresult",
                "Split Apple execution has another result bundle")
        owned_udid = receipt.get("owned_simulator", {}).get("udid")
        require(isinstance(owned_udid, str) and re.fullmatch(r"[0-9A-Fa-f-]{36}", owned_udid)
                and owned_udid == receipt.get("actual_execution", {}).get("udid")
                and destination_index < len(test["argv"])
                and test["argv"][destination_index] == "platform=iOS Simulator,id=" + owned_udid,
                "Split Apple execution is not bound to its actual owned destination")
        expected_build = list(test["argv"])
        expected_build[1] = "build-for-testing"
        expected_build[bundle_index] = str(Path(expected_build[bundle_index]).with_name("coherent-heart-build.xcresult"))
        built = [entry for entry in commands if entry.get("name") == "ios-coherent-build"]
        boot = [entry for entry in commands if entry.get("name") == "boot-owned-simulator"]
        waited = [entry for entry in commands if entry.get("name") == "wait-owned-simulator"]
        require(len(built) == len(boot) == len(waited) == 1
                and all(entry.get("status") == "PASS_EXIT_0" for entry in (built[0], boot[0], waited[0]))
                and built[0].get("argv") == expected_build
                and boot[0].get("argv") == ["xcrun", "simctl", "boot", receipt.get("owned_simulator", {}).get("udid")]
                and waited[0].get("argv") == ["xcrun", "simctl", "bootstatus", receipt.get("owned_simulator", {}).get("udid"), "-b"]
                and commands.index(boot[0]) < commands.index(built[0]) < commands.index(waited[0]) < commands.index(test)
                and type(receipt.get("harness_build", {}).get("tests_executed")) is int
                and receipt.get("harness_build") == dict(status="BUILT_CURRENT_HARNESS_NOT_EXECUTED", tests_executed=0,
                                                        boot_readiness="SEPARATE_BOUNDED_CHECK_REQUIRED"),
                "Split Apple execution lacks its exact preceding successful build and owned-device readiness")
    else:
        require(len(selected) == 1 and selected[0].get("status") == "PASS_EXIT_0"
                and selected[0].get("argv", [])[:2] == ["xcodebuild", "test"]
                and "-only-testing:CoherentHeartAuthorityHarnessTests/" + METHOD in selected[0]["argv"],
                "Original Apple test process was not the selected successful journey")
    bundle = host / "coherent-heart.xcresult"
    require(bundle.is_dir() and (bundle / "Info.plist").is_file() and _file_map(bundle), "Missing original xcresult bundle")
    original_summary, original_tree = read_json(host / "xcresult-summary.log"), read_json(host / "xcresult-tests.log")
    for name in ("summary", "tests"):
        command(["xcrun", "xcresulttool", "get", "test-results", name, "--path", str(bundle)],
                evidence / ("replayed-xcresult-" + name + ".json"), timeout=120)
    summary, tree = read_json(evidence / "replayed-xcresult-summary.json"), read_json(evidence / "replayed-xcresult-tests.json")
    require(summary == original_summary and tree == original_tree, "Original xcresult differs from its archived result JSON")
    validate_execution(summary, tree, receipt.get("actual_execution", {}))
    actual_raw = read_bounded(host / "actual.json")
    require(profiles.digest_bytes(actual_raw) == receipt.get("actual_attachment_sha256"), "Original actual Apple attachment changed")
    actual = json_value(actual_raw, "actual Apple attachment")
    attachments = evidence / "replayed-attachments"
    require(not attachments.exists(), "Fresh replay attachment directory required")
    command(["xcrun", "xcresulttool", "export", "attachments", "--path", str(bundle), "--output-path", str(attachments)],
            evidence / "replayed-attachments-export.log", timeout=120)
    attached = []
    files = list(attachments.rglob("*"))
    require(0 < len(files) <= MAX_PROOF_FILES, "Original attachment export is missing or unbounded")
    for path in files:
        require(not path.is_symlink(), "Symlink in original attachment export")
        if path.is_file() and 0 < path.stat().st_size < 4 * 1024**2:
            try:
                value = json_value(path.read_bytes(), "replayed attachment")
            except RuntimeError:
                continue
            if isinstance(value, dict) and value.get("status") == APPLE_PASS:
                attached.append(path)
    require(len(attached) == 1 and attached[0].read_bytes() == actual_raw,
            "Actual native/Swift observation was not the sole original xcresult attachment")
    codec = validate_raw_native(actual, build, profile, producer, host / "native")
    require(receipt.get("shared_swift_codec") == codec, "Apple receipt differs from actual shared Swift codec result")
    configuration = dict(appSHA=producer["source_sha"], runID=producer["run_id"], runAttempt=producer["run_attempt"],
                         nonce=actual["nonce"], bridgeSHA=build["bridge_sha256"], originalFixtureSHA=ORIGINAL_FIXTURE,
                         runtimeVersion=profile.version)
    require(receipt.get("configuration") == configuration, "Original host configuration differs from the actual attachment")
    return receipt


def execute(args, profile, command):
    """Called after download_heart_runtime creates fresh work/evidence paths."""
    require(profile == profiles.select(profiles.COHERENT), "Only the exact frozen coherent profile is accepted")
    require(isinstance(args.source_run_id, str) and args.source_run_id.isascii()
            and args.source_run_id.isdigit() and int(args.source_run_id) > 0, "Positive original Apple producer ID required")
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository or ""), "Explicit GitHub repository required")
    branch = git(args.app_source, "branch", "--show-current")
    head = git(args.app_source, "rev-parse", "HEAD")
    require(branch == args.expected_app_branch and profiles.is_sha(head, 40), "Wrong consumer application source")
    modules = consumer_modules(args.app_source)
    destination = args.app_source / "Dependencies/Middleware"
    for parent in (args.app_source / "Dependencies", destination):
        require(not parent.is_symlink(), "Middleware destination cannot be a symlink")
    require(not (destination / "Lib.xcframework").exists() and not (destination / "PinkhaNativeHeartBuild.json").exists()
            and not (destination / "Lib.xcframework").is_symlink() and not (destination / "PinkhaNativeHeartBuild.json").is_symlink(),
            "Refusing to overwrite an existing middleware installation")
    for name in ("heart-installation.json", "custom-heart-build.json", "original-runtime-download.json",
                 "original-coherent-apple-host-receipt.json", "original-coherent-apple-build.json", "original-coherent-apple-actual.json",
                 "original-coherent-apple-build-reuse.json"):
        require(not (args.evidence / name).exists() and not (args.evidence / name).is_symlink(),
                "Refusing to overwrite prior installation evidence")
    run_path = args.evidence / "original-producer-run.json"
    command(["gh", "api", "repos/" + args.repository + "/actions/runs/" + args.source_run_id], run_path, timeout=120)
    run = read_json(run_path)
    producer = profiles.validate_producer(run, args.source_run_id, args.repository,
                                         expected_producer_branch(args.expected_app_branch), profiles.COHERENT)
    list_path = args.evidence / "original-artifact-list.json"
    command(["gh", "api", "repos/" + args.repository + "/actions/runs/" + args.source_run_id + "/artifacts?per_page=100"], list_path, timeout=120)
    listing = read_json(list_path)
    items = listing.get("artifacts", [])
    require(isinstance(items, list) and type(listing.get("total_count")) is int
            and listing["total_count"] == len(items) <= 100, "Original artifact inventory is incomplete; explicit pagination is required")
    names = {"runtime": profile.artifact_name,
             "proof": "Pinkha-Coherent-Heart-Apple-" + producer["run_id"] + "-" + producer["run_attempt"]}
    downloaded = dict(status="VERIFYING", producer=producer, artifacts={}, archive_sha256={})
    archives = {}
    for kind, name in names.items():
        matches = [item for item in items if item.get("name") == name]
        require(len(matches) == 1, "Exactly one original artifact is required: " + name)
        item = matches[0]
        expected = profiles.validate_artifact(item, run, name)
        require(item["size_in_bytes"] <= MAX_ARCHIVE_BYTES, "Oversized original artifact")
        workflow = item.get("workflow_run", {})
        require(workflow.get("head_branch") == producer["source_branch"], "Artifact branch differs from its producer")
        archive = args.work / (kind + "-original.zip")
        command(["gh", "api", "repos/" + args.repository + "/actions/artifacts/" + str(item["id"]) + "/zip"], archive, timeout=600)
        require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size == item["size_in_bytes"]
                and digest(archive) == expected, "Original GitHub artifact digest or size differs")
        downloaded["artifacts"][kind] = item
        downloaded["archive_sha256"][kind] = expected
        archives[kind] = archive
    runtime_dir, proof_dir = args.work / "runtime", args.work / "proof-artifact"
    safe_zip(archives["runtime"], runtime_dir, profile.archive_name)
    safe_zip(archives["proof"], proof_dir)
    require((proof_dir / "proof").is_dir(), "Original Apple proof root is missing")
    proof = proof_dir / "proof"
    patch_raw = read_bounded(proof / "native-source/native-heart-integration.patch")
    inventory_raw = read_bounded(proof / "native-source/native-heart-integration.json")
    inventory = profiles.verify_source(profile, patch_raw, inventory_raw)
    runtime_archive = runtime_dir / profile.archive_name
    staging = args.work / "verified-production"
    safe_tar(runtime_archive, staging)
    receipt_raw = read_bounded(staging / "PinkhaNativeHeartBuild.json")
    build_lineage, build_producer = None, producer
    if (proof / "build-reuse.json").exists():
        from coherent_apple import reuse_build
        build_lineage = reuse_build.validate_admission_lineage(proof, producer, args.work, args.evidence, command)
        build_producer = build_lineage["build_producer"]
    receipt, build = validate_build(proof, receipt_raw, inventory, profile, build_producer, digest(runtime_archive))
    observed = validate_framework(staging / "Lib.xcframework", receipt, profile)
    host = qualify_apple(proof, profile, producer, build, args.evidence, command, build_lineage)
    require(host["copied_module_sha256"] == modules == consumer_modules(args.app_source),
            "Consumer shared modules differ from those actually executed in the admitted Apple proof")
    require(git(args.app_source, "branch", "--show-current") == branch and git(args.app_source, "rev-parse", "HEAD") == head,
            "Application branch or HEAD changed during artifact admission")
    require(_file_map(staging / "Lib.xcframework") == observed, "Verified production bytes changed before installation")
    require(not destination.is_symlink() and not destination.parent.is_symlink(), "Middleware destination changed to a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(staging / "Lib.xcframework", destination / "Lib.xcframework")
    with (destination / "PinkhaNativeHeartBuild.json").open("xb") as output:
        output.write(receipt_raw)
    require(_file_map(destination / "Lib.xcframework") == observed
            and (destination / "PinkhaNativeHeartBuild.json").read_bytes() == receipt_raw,
            "Installed production files differ from admitted originals")
    downloaded.update(status="VERIFIED_ORIGINAL_COHERENT_APPLE_ARTIFACTS", runtime_payload_sha256=digest(runtime_archive),
                      original_host_receipt_sha256=digest(proof / "host/receipt.json"),
                      original_actual_attachment_sha256=host["actual_attachment_sha256"])
    saved = {
        "original-runtime-download.json": (json.dumps(downloaded, indent=2) + "\n").encode(),
        "custom-heart-build.json": receipt_raw,
        "original-coherent-apple-host-receipt.json": read_bounded(proof / "host/receipt.json"),
        "original-coherent-apple-build.json": read_bounded(proof / "build.json"),
        "original-coherent-apple-actual.json": read_bounded(proof / "host/actual.json"),
    }
    if build_lineage is not None:
        saved["original-coherent-apple-build-reuse.json"] = read_bounded(proof / "build-reuse.json")
    for name, raw in saved.items():
        with (args.evidence / name).open("xb") as output:
            output.write(raw)
    installation = dict(status="PASS", source_run_id=producer["run_id"], archive_sha256=digest(runtime_archive),
        patch_sha256=profile.patch_sha256, inventory_sha256=profile.inventory_sha256, app_source_sha=head,
        original_build_app_sha=build_producer["source_sha"], marker=profile.receipt_marker, runtime_profile=profile.name,
        native_marker=profile.binary_marker, expected_app_get_version=profile.version, producer=producer,
        heart_build_receipt_sha256=profiles.digest_bytes(receipt_raw),
        heart_artifact_id=downloaded["artifacts"]["runtime"]["id"], heart_artifact_sha256=downloaded["archive_sha256"]["runtime"],
        heart_proof_artifact_id=downloaded["artifacts"]["proof"]["id"], heart_proof_artifact_sha256=downloaded["archive_sha256"]["proof"],
        original_apple_receipt_sha256=downloaded["original_host_receipt_sha256"],
        original_actual_attachment_sha256=host["actual_attachment_sha256"],
        coherent_fixture_ios_acceptance=APPLE_PASS, production_binary_execution="NOT_RUN", full_app_acceptance="NOT_RUN",
        native_source_run_id=profiles.COHERENT_NATIVE_RUN, native_source_sha=NATIVE_SOURCE,
        installed_fixture=False, target_architecture="arm64", target_environment="simulator")
    if build_lineage is not None:
        originals = build_lineage["original_artifacts"]
        installation.update(build_producer=build_producer,
            build_reuse_receipt_sha256=build_lineage["receipt_sha256"],
            original_build_artifact_id=originals["production"]["id"],
            original_build_artifact_sha256=originals["production"]["zip_sha256"],
            original_build_proof_artifact_id=originals["proof"]["id"],
            original_build_proof_artifact_sha256=originals["proof"]["zip_sha256"])
    with (args.evidence / "heart-installation.json").open("x", encoding="utf8") as output:
        output.write(json.dumps(installation, indent=2) + "\n")
    return installation
