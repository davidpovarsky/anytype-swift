"""Exact build-time contract between the unified Go library and its Swift consumer.

This checks source and original linker receipts; it does not execute MobileVersion,
start an account, or confer application acceptance.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex

PROTOCOL = "pinkha-unified-runtime-full-identity-v1"
FORMATTER = "any/internal/version/version.go"
FORMATTER_SHA256 = "c0e23de416f43ba36e11f6defe7cb7aa4019888820c0158d97ae19423e8fb89c"
EMBEDDED_ENTRY = "any/internal/embedded/embedded.go"
EMBEDDED_ENTRY_SHA256 = "a1b52dda8a4232d544242f27bf13bc8a6f4b4832be5d90be2baf0ffa222c2088"
MOBILE_ENTRY = "any/mobile/android/mobile.go"
MOBILE_ENTRY_SHA256 = "5b79bbb5cce7de5f820203604327d9d391bae989233d1aff4d899f9f1707ebc9"
PROFILE = re.compile(r"public enum PinkhaUnifiedRuntimeProfile \{[^{}]*\}", re.MULTILINE)
VERSION_PACKAGE = "github.com/anyproto/any/internal/version."
HEART_PACKAGE = "github.com/anyproto/anytype-heart/util/vcs."


class IdentityError(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise IdentityError(reason)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(manifest_bytes: bytes, build_date: str) -> dict:
    manifest = json.loads(manifest_bytes)
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", build_date) is not None,
            "explicit_iso_build_date_required")
    require(datetime.date.fromisoformat(build_date).isoformat() == build_date,
            "invalid_build_date")
    pins = manifest["sourcePins"]
    require(set(pins) == {"any", "heart", "sdk", "sync"}
            and all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{40}", v) for v in pins.values()),
            "exact_four_native_source_pins_required")
    require(manifest["purpose"] == "ONE_GO_RUNTIME_HEART_ANY_APPLE_LIBRARY"
            and manifest["schemaVersion"] == 1, "unified_source_manifest_required")
    for path, expected in ((FORMATTER, FORMATTER_SHA256), (MOBILE_ENTRY, MOBILE_ENTRY_SHA256),
                           (EMBEDDED_ENTRY, EMBEDDED_ENTRY_SHA256)):
        require(manifest["files"][path]["sha256"] == expected,
                "native_version_route_changed:" + path)
    # New manifests bind the date before computing their SHA. Historical ones
    # can be inspected using an explicit date from their original linker receipt.
    if "runtimeBuildDate" in manifest:
        require(manifest["runtimeBuildDate"] == build_date, "manifest_build_date_differs")
    manifest_sha = sha(manifest_bytes)
    version = "v0.5.0-pinkha.dual.1-" + manifest_sha
    return {
        "protocol": PROTOCOL,
        "sourceManifestSHA256": manifest_sha,
        "sourcePins": dict(pins),
        "buildDate": build_date,
        "heartVersion": "pinkha-dual-runtime-v1-" + manifest_sha,
        "anyVersion": version,
        "anyRuntimeVersion": "any " + version + " (commit " + pins["any"] + ", built " + build_date + ")",
        "nativeVersionSourceSHA256": {FORMATTER: FORMATTER_SHA256, MOBILE_ENTRY: MOBILE_ENTRY_SHA256,
                                       EMBEDDED_ENTRY: EMBEDDED_ENTRY_SHA256},
    }


def swift_profile(expected: dict) -> str:
    return (
        "public enum PinkhaUnifiedRuntimeProfile {\n"
        '    public static let sourceManifestSHA256 = "' + expected["sourceManifestSHA256"] + '"\n'
        '    public static let heartVersion = "pinkha-dual-runtime-v1-" + sourceManifestSHA256\n'
        '    public static let anyVersion = "v0.5.0-pinkha.dual.1-" + sourceManifestSHA256\n'
        '    public static let anyCommit = "' + expected["sourcePins"]["any"] + '"\n'
        '    public static let anyBuildDate = "' + expected["buildDate"] + '"\n'
        '    public static let anyRuntimeVersion = "any " + anyVersion\n'
        '        + " (commit " + anyCommit + ", built " + anyBuildDate + ")"\n'
        "}"
    )


def replacing_swift_profile(original: bytes, expected: dict) -> bytes:
    text = original.decode("utf-8")
    matches = list(PROFILE.finditer(text))
    require(len(matches) == 1, "one_original_consumer_profile_required")
    match = matches[0]
    return (text[:match.start()] + swift_profile(expected) + text[match.end():]).encode("utf-8")


def qualify_consumer(bridge_bytes: bytes, expected: dict) -> dict:
    matches = list(PROFILE.finditer(bridge_bytes.decode("utf-8")))
    require(len(matches) == 1 and matches[0].group() == swift_profile(expected),
            "consumer_full_native_identity_differs")
    return {
        "bridgeSHA256": sha(bridge_bytes),
        "profileSHA256": sha(matches[0].group().encode()),
        "anyRuntimeVersion": expected["anyRuntimeVersion"],
        "profileComparedExactly": True,
    }


def linker_bindings(expected: dict) -> dict[str, str]:
    return {
        HEART_PACKAGE + "GitSummary": expected["heartVersion"],
        HEART_PACKAGE + "GitCommit": expected["sourcePins"]["heart"],
        VERSION_PACKAGE + "Version": expected["anyVersion"],
        VERSION_PACKAGE + "Commit": expected["sourcePins"]["any"],
        VERSION_PACKAGE + "BuildDate": expected["buildDate"],
    }


def linker_flags(expected: dict) -> str:
    return " ".join("-X " + name + "=" + value for name, value in linker_bindings(expected).items())


def qualify_bind_command(command_bytes: bytes, manifest_bytes: bytes,
                         expected: dict, kind: str) -> dict:
    require(kind in ("device", "simulator"), "exact_apple_slice_required")
    manifest = json.loads(manifest_bytes)
    command = json.loads(command_bytes)
    require(command["status"] == "PASS_EXIT_0" and type(command["exitCode"]) is int
            and command["exitCode"] == 0 and command["name"] == "combined-gomobile-bind",
            "actual_successful_original_bind_required")
    argv = command["argv"]
    require(isinstance(argv, list) and all(isinstance(x, str) for x in argv)
            and len(argv) > 10 and Path(argv[0]).name == "gomobile" and argv[1] == "bind",
            "original_gomobile_bind_argv_required")
    require(argv.count("-ldflags") == 1 and not any(x.startswith("-ldflags=") for x in argv),
            "unambiguous_single_linker_flag_input_required")
    index = argv.index("-ldflags")
    require(index + 1 < len(argv), "missing_linker_flags")
    tokens = shlex.split(argv[index + 1])
    require(len(tokens) == 10 and all(tokens[i] == "-X" for i in range(0, 10, 2)),
            "exact_five_version_bindings_required")
    actual = {}
    for value in tokens[1::2]:
        name, separator, body = value.partition("=")
        require(separator == "=" and name not in actual, "ambiguous_native_version_binding")
        actual[name] = body
    require(actual == linker_bindings(expected), "actual_linker_full_identity_differs")
    target = "-target=" + ("iossimulator/arm64" if kind == "simulator" else "ios/arm64")
    require([x for x in argv if x.startswith("-target=")] == [target], "native_slice_target_differs")
    require([x for x in argv if x.startswith("-iosversion=")] == ["-iosversion=" + manifest["deploymentTarget"]],
            "native_deployment_target_differs")
    require(argv.count("-tags") == 1 and argv[argv.index("-tags") + 1] == " ".join(manifest["tags"])
            and argv[-len(manifest["packages"]):] == manifest["packages"],
            "original_native_tags_or_packages_differ")
    require(re.fullmatch(r"[0-9a-f]{64}", command["logSHA256"]) is not None,
            "original_bind_log_hash_required")
    return {
        "commandSHA256": sha(command_bytes),
        "originalLogSHA256": command["logSHA256"],
        "kind": kind,
        "bindings": actual,
        "anyRuntimeVersion": expected["anyRuntimeVersion"],
    }


def qualify_slice(receipt_bytes: bytes, command_bytes: bytes, log_bytes: bytes,
                  manifest_bytes: bytes, expected: dict, kind: str) -> dict:
    receipt = json.loads(receipt_bytes)
    require(receipt["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
            and receipt["sourceManifestSHA256"] == expected["sourceManifestSHA256"]
            and receipt["sourcePins"] == expected["sourcePins"]
            and receipt["heartRuntimeVersion"] == expected["heartVersion"]
            and receipt["anyRuntimeVersion"] == expected["anyVersion"]
            and receipt["sourceUnchanged"] is True and receipt["independentGoRuntimeCount"] == 1,
            "original_qualified_slice_identity_differs")
    bind = qualify_bind_command(command_bytes, manifest_bytes, expected, kind)
    require(sha(log_bytes) == bind["originalLogSHA256"], "original_bind_log_changed")
    require(set(receipt["slices"]) == {"ios-arm64-simulator" if kind == "simulator" else "ios-arm64"},
            "one_exact_original_native_slice_required")
    row = next(iter(receipt["slices"].values()))
    require(type(row["binaryBytes"]) is int and row["binaryBytes"] > 0
            and re.fullmatch(r"[0-9a-f]{64}", row["binarySHA256"]) is not None,
            "original_native_binary_identity_required")
    return dict(bind, receiptSHA256=sha(receipt_bytes),
                binarySHA256=row["binarySHA256"], binaryBytes=row["binaryBytes"])


def qualify_application(manifest_bytes: bytes, build_date: str, bridge_bytes: bytes,
                        slices: dict) -> dict:
    expected = identity(manifest_bytes, build_date)
    consumer = qualify_consumer(bridge_bytes, expected)
    require(set(slices) == {"device", "simulator"}, "both_original_apple_slices_required")
    proofs = {}
    for kind, inputs in slices.items():
        require(set(inputs) == {"receipt", "command", "log", "expectedReceiptSHA256", "expectedCommandSHA256"},
                "closed_original_slice_inputs_required")
        require(sha(inputs["receipt"]) == inputs["expectedReceiptSHA256"]
                and sha(inputs["command"]) == inputs["expectedCommandSHA256"],
                "pinned_original_slice_provenance_changed")
        proofs[kind] = qualify_slice(inputs["receipt"], inputs["command"], inputs["log"],
                                     manifest_bytes, expected, kind)
    return {
        "protocol": PROTOCOL,
        "status": "PASS_EXACT_CONSUMER_AND_ORIGINAL_LINKER_IDENTITIES_NOT_RUNTIME_ACCEPTANCE",
        "identity": expected,
        "consumer": consumer,
        "slices": proofs,
        "nativeVersionExecutedByThisCheck": False,
        "applicationBuilds": 0,
        "applicationAcceptanceClaimed": False,
    }
