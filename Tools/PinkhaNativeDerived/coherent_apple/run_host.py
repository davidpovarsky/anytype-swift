#!/usr/bin/env python3
"""Execute one new combined-authority XCTest with a distinct test-only Lib."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
from uuid import uuid4

import contract

RAW_FILES = {"ownership.json", "native-observation.json", "coherent-observation.json",
             "coherent-owner.pb", "coherent-reader.pb", "coherent-removed.pb",
             "object-search-removed.pb", "object-show-removed.pb"}
MODULES = ("PinkhaKit", "PinkhaHeartEngine")


def load_helpers():
    sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
    sys.path.insert(0, str(contract.ROOT / "Tools/PinkhaNativeDerived"))
    from authorized_read import run_apple_host as original
    import coherent_read_native as native
    return original, native


def fields(raw):
    """Bounded independent decoder for the native Search/Show error envelope."""
    contract.require(0 < len(raw) <= 4096, "Native denial envelope is empty/oversized")
    position, result = 0, []
    def varint():
        nonlocal position
        value = 0
        for index in range(10):
            contract.require(position < len(raw), "Truncated native denial")
            byte = raw[position]; position += 1
            value |= (byte & 127) << (7 * index)
            if byte < 128:
                contract.require(index == 0 or byte != 0, "Overlong native varint")
                return value
        raise ValueError("Oversized native varint")
    while position < len(raw):
        key = varint(); number, wire = key >> 3, key & 7
        contract.require(number > 0 and wire in (0, 2), "Unexpected native denial field")
        if wire == 0:
            value = varint()
        else:
            count = varint()
            contract.require(count <= len(raw) - position, "Truncated native denial payload")
            value = raw[position:position + count]; position += count
        result.append((number, wire, value))
        contract.require(len(result) <= 8, "Too many native denial fields")
    return result


def qualify_t5_wire(raw, kind, expected_description):
    # anyproto/anytype-heart@d98420b pb/protos/commands.proto:
    # Object.Show.Response: error1/objectView2. Search: error1/records2/total3.
    outer = fields(raw)
    errors = [value for number, wire, value in outer if (number, wire) == (1, 2)]
    allowed = {(1, 2)} | ({(3, 0)} if kind == "search" else set())
    contract.require(len(errors) == 1 and len({number for number, _, _ in outer}) == len(outer)
                     and all((number, wire) in allowed for number, wire, _ in outer)
                     and all(value == 0 for number, _, value in outer if number == 3),
                     "Revoked raw response contains a payload, duplicate or unexpected field")
    inner = fields(errors[0])
    contract.require(inner == [(1, 0, 2), (2, 2, expected_description.encode())]
                     and expected_description in ("PINKHA_CURRENT_SPACE_READ_DENIED_V1", "PINKHA_CURRENT_SPACE_READ_INVALIDATED_V1"),
                     "Native raw response lacks exact typed authority denial")
    return dict(error_code=2, description=expected_description, payload_absent=True, total=0 if kind == "search" else None,
                sha256=hashlib.sha256(raw).hexdigest())


def validate_execution(summary, tree, udid, control):
    counts = {name: summary.get(name) for name in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    contract.require(all(type(value) is int for value in counts.values())
                     and counts == dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0),
                     "Exactly one successful actual XCTest without skips required")
    destinations = summary.get("devicesAndConfigurations", [])
    contract.require(len(destinations) == 1, "Exactly one actual simulator required")
    device = destinations[0].get("device", {})
    contract.require(str(device.get("deviceId", "")).lower() == udid.lower()
                     and str(device.get("osVersion", "")).split(".")[0] == "27"
                     and device.get("architecture") == "arm64" and device.get("osBuildNumber"), "Wrong actual Apple destination")
    spec = importlib.util.spec_from_file_location("coherent_retained_xcresult_parser", control / "Tools/AnyEnginePort/verify_native_test_execution.py")
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    cases = verifier.test_cases(tree)
    contract.require(len(cases) == 1 and list(cases.values()) == ["Passed"]
                     and re.search(r"(?:^|/)" + re.escape(contract.METHOD) + r"(?:\(|/|$)", next(iter(cases))),
                     "Missing or wrong actual named XCTest")
    return dict(counts, method=contract.METHOD, udid=udid, device=device, actual_cases=cases)


def qualify_observation(value, configuration, build, output):
    expected = dict(status=contract.PASS, app_sha=configuration["appSHA"], run_id=configuration["runID"],
                    run_attempt=configuration["runAttempt"], nonce=configuration["nonce"],
                    production_binary_execution="NOT_RUN", full_app_acceptance="NOT_RUN",
                    network_acl_transport="NOT_RUN", fresh_ios_process_reopen="NOT_RUN")
    contract.require(set(value) == set(expected) | {"pid", "native", "shared_swift_codec"}
                     and all(value.get(key) == item for key, item in expected.items())
                     and type(value["pid"]) is int and value["pid"] > 0, "Wrong actual Swift receipt scope/source")
    native = value["native"]
    expected_native = dict(status="PASS_ACTUAL_COHERENT_APPLE_FIXTURE", nonce=configuration["nonce"], pid=value["pid"],
        bridge_sha256=build["bridge_sha256"], original_fixture_sha256=contract.ORIGINAL_FIXTURE,
        runtime_version=build["runtime_version"], heart_sha=contract.HEART,
        production_binary_executed=False, fixture_tag=contract.FIXTURE_TAG,
        network_acl_transport="NOT_RUN", full_app_acceptance="NOT_RUN")
    contract.require(set(native) == set(expected_native) | {"files", "files_sha256", "account_id", "space_id", "operation_id"}
                     and all(native.get(key) == item and type(native.get(key)) is type(item) for key, item in expected_native.items())
                     and native["operation_id"] == configuration["nonce"]
                     and all(isinstance(native[key], str) and native[key] for key in ("account_id", "space_id")), "Wrong native bridge receipt")
    contract.require(set(native["files"]) == set(native["files_sha256"]) == RAW_FILES, "Missing or unexpected raw native export")
    output.mkdir(parents=True, exist_ok=False)
    for name in sorted(RAW_FILES):
        raw = base64.b64decode(native["files"][name], validate=True)
        contract.require(0 < len(raw) < 2*1024**2 and hashlib.sha256(raw).hexdigest() == native["files_sha256"][name], "Raw native export changed")
        (output / name).write_bytes(raw)
    coherent = json.loads((output / "coherent-observation.json").read_bytes())
    t5 = json.loads((output / "native-observation.json").read_bytes())
    original, native_validator = load_helpers()
    identity = dict(heart_sha=contract.HEART, runtime_version=build["runtime_version"], fixture_sha256=contract.ORIGINAL_FIXTURE,
                    patch_sha256=contract.PATCH, runtime_profile=contract.VARIANT)
    qualified = native_validator.validate_observations(coherent, t5, identity, value["pid"], configuration["nonce"], output)
    contract.require(coherent["account_id_sha256"] == hashlib.sha256(native["account_id"].encode()).hexdigest()
                     and coherent["space_id_sha256"] == hashlib.sha256(native["space_id"].encode()).hexdigest(), "Swift/native account scope differs")
    codec = value["shared_swift_codec"]
    contract.require(set(codec) == {"owner_decoded", "reader_decoded", "exact_variants", "removed_rejected", "removed_error"}
                     and all(codec[name] is True for name in codec if name != "removed_error")
                     and codec["removed_error"] == {4: "permissionDenied", 9: "snapshotChanged"}[coherent["removed_error_code"]],
                     "Unchanged shared Swift codec did not reject the actual native denial")
    wire = {kind: qualify_t5_wire((output / ("object-" + kind + "-removed.pb")).read_bytes(), kind,
                                 t5["object_" + kind + "_error_description"]) for kind in ("search", "show")}
    return qualified, codec, wire


def source_snapshot(control):
    paths = ["Tools/PinkhaNativeDerived", "Tools/TorahNativeOperations", "Tools/AnyEnginePort/verify_native_test_execution.py",
             "Tools/PinkhaSimulatorGate/simulator_selection.py",
             ".github/workflows/pinkha-coherent-heart-apple.yml", *("Modules/" + name for name in MODULES)]
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--", *paths]).decode().split("\0")
    return {name: contract.digest(control / name) for name in names if name}


def prepare_harness(control, work, framework, configuration):
    client = work / "client"; client.mkdir()
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--", *("Modules/" + name for name in MODULES)]).decode().split("\0")
    copied = {}
    for name in filter(None, names):
        source, target = control / name, client / name
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
        copied[name] = contract.digest(source)
        contract.require(contract.digest(target) == copied[name], "Copied shared module differs")
    destination = client / "Dependencies/Middleware/Lib.xcframework"
    destination.parent.mkdir(parents=True); shutil.copytree(framework, destination)
    harness = client / "Harness"
    tests = harness / "Tests" / contract.TARGET; tests.mkdir(parents=True)
    shutil.copyfile(contract.HERE / "HarnessPackage.swift", harness / "Package.swift")
    shutil.copyfile(contract.HERE / "HostTests/CoherentHeartAuthorityTests.swift", tests / "CoherentHeartAuthorityTests.swift")
    stub = harness / "Sources" / contract.PACKAGE / "Harness.swift"; stub.parent.mkdir(parents=True)
    stub.write_text("public enum CoherentHeartAuthorityHarness {}\n")
    contract.save(tests / "host-config.json", configuration)
    return harness, copied


def execute(args, receipt, run):
    original, native = load_helpers()
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual ARM64 iOS host required")
    contract.require(original.git(args.control, "rev-parse", "HEAD") == args.expected_app_sha
                     and not original.git(args.control, "status", "--porcelain"), "Exact clean source required")
    contract.require(not args.work.exists(), "Fresh owned test work required"); args.work.mkdir()
    build = json.loads(args.build_receipt.read_bytes())
    if args.build_reuse_receipt is not None:
        import reuse_build
        build_origin = reuse_build.validate_host_lineage(args.control, args.build_receipt, args.build_reuse_receipt,
            args.expected_app_sha, receipt["run_id"], receipt["run_attempt"])
        contract.validate_build_receipt(build, build_origin["source_sha"], build_origin["run_id"])
        contract.require(build["run_attempt"] == build_origin["run_attempt"], "Original build attempt differs")
        receipt.update(build_origin=build_origin, build_reuse_receipt_sha256=contract.digest(args.build_reuse_receipt))
    else:
        contract.validate_build_receipt(build, args.expected_app_sha, receipt["run_id"])
        contract.require(build["run_attempt"] == receipt["run_attempt"], "Build/test attempts differ")
    for kind in ("production", "fixture"):
        contract.verify_framework(args.frameworks / kind / "Lib.xcframework", build["frameworks"][kind])
    source = source_snapshot(args.control)
    snapshot_sha = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    contract.save(args.evidence / "control-source-before.json", source)
    configuration = dict(appSHA=args.expected_app_sha, runID=receipt["run_id"], runAttempt=receipt["run_attempt"],
                         nonce=uuid4().hex, bridgeSHA=build["bridge_sha256"], originalFixtureSHA=contract.ORIGINAL_FIXTURE,
                         runtimeVersion=build["runtime_version"])
    harness, copied = prepare_harness(args.control, args.work, args.frameworks / "fixture/Lib.xcframework", configuration)
    receipt.update(configuration=configuration, source_snapshot_sha256=snapshot_sha, copied_module_sha256=copied,
        production_binary_sha256=build["frameworks"]["production"]["binary_sha256"],
        fixture_binary_sha256=build["frameworks"]["fixture"]["binary_sha256"], bridge_sha256=build["bridge_sha256"],
        build_receipt_sha256=contract.digest(args.build_receipt), native_run=contract.NATIVE_RUN,
        production_binary_execution="NOT_RUN", full_app_acceptance="NOT_RUN", network_acl_transport="NOT_RUN")
    cache = ["-clonedSourcePackagesDirPath", str(args.work / "SourcePackages")]
    schemes = original.command_json(run(["xcodebuild", "-list", "-json", *cache], "schemes", cwd=harness))
    available = schemes.get("workspace", schemes.get("project", {})).get("schemes", [])
    options = [name for name in (contract.PACKAGE, contract.PACKAGE + "-Package") if name in available]
    contract.require(options, "Missing actual minimal scheme")
    scheme = options[0]
    run(["xcodebuild", "-resolvePackageDependencies", "-scheme", scheme, *cache], "resolve-packages", cwd=harness)
    pins = original.validate_pins(harness)
    receipt["resolved_packages"] = pins
    runtime_data = original.command_json(run(["xcrun", "simctl", "list", "runtimes", "-j"], "runtimes"))
    type_data = original.command_json(run(["xcrun", "simctl", "list", "devicetypes", "-j"], "device-types"))
    sys.path.insert(0, str(args.control / "Tools/PinkhaSimulatorGate"))
    from simulator_selection import choose_pair
    pair = choose_pair(runtime_data, type_data, product_family="iPad", major=27, architecture="arm64")
    runtime, selected = pair["runtime"], pair["device"]
    receipt["simulator_selection"] = pair["selection"]
    udid = run(["xcrun", "simctl", "create", "CoherentHeart-" + configuration["nonce"], selected["identifier"], runtime["identifier"]],
               "create-owned-simulator").read_text().strip()
    contract.require(re.fullmatch(r"[0-9A-Fa-f-]{36}", udid), "Invalid owned simulator identifier")
    receipt["owned_simulator"] = dict(udid=udid, runtime=runtime["identifier"], type=selected["identifier"])
    result = args.evidence / "coherent-heart.xcresult"
    try:
        run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator")
        test_command = ["xcodebuild", "test-without-building", "-scheme", scheme, "-configuration", "Debug", "-destination", "platform=iOS Simulator,id=" + udid,
             "-derivedDataPath", str(args.work / "DerivedData"), *cache, "-disableAutomaticPackageResolution",
             "-parallel-testing-enabled", "NO", "-jobs", "4", "-test-timeouts-enabled", "YES",
             "-maximum-test-execution-time-allowance", "420", "-resultBundlePath", str(result),
             "-only-testing:" + contract.TARGET + "/" + contract.METHOD]
        build_command = list(test_command)
        build_command[1] = "build-for-testing"
        build_command[build_command.index("-resultBundlePath") + 1] = str(args.evidence / "coherent-heart-build.xcresult")
        # The required current harness build overlaps cold boot, as in the
        # successful Any iPad-mini/iOS-27.2 bootstrap. This executes no tests.
        run(build_command, "ios-coherent-build", cwd=harness, timeout=1800)
        receipt["harness_build"] = dict(status="BUILT_CURRENT_HARNESS_NOT_EXECUTED", tests_executed=0,
                                       boot_readiness="SEPARATE_BOUNDED_CHECK_REQUIRED")
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], "wait-owned-simulator", timeout=180)
        run(test_command, "ios-coherent-tests", cwd=harness, timeout=1800)
        summary = original.command_json(run(["xcrun", "xcresulttool", "get", "test-results", "summary", "--path", str(result)], "xcresult-summary"))
        tree = original.command_json(run(["xcrun", "xcresulttool", "get", "test-results", "tests", "--path", str(result)], "xcresult-tests"))
        receipt["actual_execution"] = validate_execution(summary, tree, udid, args.control)
        attachments = args.evidence / "attachments"
        run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result), "--output-path", str(attachments)], "export-native-receipt")
        candidates = []
        for path in attachments.rglob("*"):
            if path.is_file() and path.stat().st_size < 4*1024**2:
                try:
                    value = json.loads(path.read_bytes())
                except (UnicodeError, ValueError):
                    continue
                if isinstance(value, dict) and value.get("status") == contract.PASS:
                    candidates.append((path, value))
        contract.require(len(candidates) == 1, "Exactly one actual Swift/native attachment required")
        path, actual = candidates[0]
        shutil.copyfile(path, args.evidence / "actual.json")
        journey, codec, wire = qualify_observation(actual, configuration, build, args.evidence / "native")
        receipt.update(native_journey=journey, shared_swift_codec=codec, raw_t5_denial=wire,
                       actual_attachment_sha256=contract.digest(path))
        contract.require(source_snapshot(args.control) == source and original.validate_pins(harness) == pins,
                         "Shared source/dependencies changed during actual execution")
        for name, expected in copied.items():
            contract.require(contract.digest(args.work / "client" / name) == expected, "Executed module copy changed")
        for kind in ("production", "fixture"):
            contract.verify_framework(args.frameworks / kind / "Lib.xcframework", build["frameworks"][kind])
        contract.verify_framework(args.work / "client/Dependencies/Middleware/Lib.xcframework", build["frameworks"]["fixture"])
        contract.require(contract.digest(args.build_receipt) == receipt["build_receipt_sha256"], "Build receipt changed")
        if args.build_reuse_receipt is not None:
            contract.require(contract.digest(args.build_reuse_receipt) == receipt["build_reuse_receipt_sha256"],
                             "Original build reuse lineage changed during actual execution")
        contract.save(args.evidence / "control-source-after.json", source_snapshot(args.control))
        receipt.update(status=contract.PASS, old_native_methods_executed=0, old_swift_methods_executed=0,
                       fresh_ios_process_reopen="NOT_RUN", app_capability="OFF")
    except BaseException as error:
        # Persist the first failure before diagnostic or cleanup subprocesses.
        # A timed-out bootstatus may legitimately have an empty original log.
        receipt["primary_failure"] = dict(error_type=type(error).__name__, error=str(error))
        diagnostics = [(["xcrun", "simctl", "list", "devices", "-j"], "owned-simulator-failure-state", 15),
                       (["/usr/bin/log", "show", "--last", "5m", "--style", "compact", "--predicate",
                         'eventMessage CONTAINS "' + udid + '"'], "owned-simulator-failure-system-log", 20)]
        for command, name, allowance in diagnostics:
            try:
                run(command, name, timeout=allowance)
            except BaseException as diagnostic_error:
                receipt.setdefault("diagnostic_failures", {})[name] = dict(
                    error_type=type(diagnostic_error).__name__, error=str(diagnostic_error))
        raise
    finally:
        for action in ("shutdown", "delete"):
            try:
                run(["xcrun", "simctl", action, udid], "cleanup-owned-simulator-" + action, timeout=30)
                receipt.setdefault("owned_simulator_cleanup", {})[action] = dict(status="PASS_EXIT_0")
            except BaseException as cleanup_error:
                # Always attempt both bounded actions; neither can replace a
                # build/readiness/XCTest error or its original diagnostic log.
                receipt.setdefault("owned_simulator_cleanup", {})[action] = dict(
                    status="FAIL", error_type=type(cleanup_error).__name__, error=str(cleanup_error))
        receipt["owned_simulator_cleanup_status"] = ("COMPLETE" if all(
            item["status"] == "PASS_EXIT_0" for item in receipt["owned_simulator_cleanup"].values()) else "INCOMPLETE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "work", "evidence", "build-receipt", "frameworks"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--build-reuse-receipt", type=Path)
    args = parser.parse_args()
    for name in ("control", "work", "evidence", "build_receipt", "frameworks"):
        setattr(args, name, getattr(args, name).resolve())
    if args.build_reuse_receipt is not None:
        args.build_reuse_receipt = args.build_reuse_receipt.resolve()
    args.evidence.mkdir(parents=True, exist_ok=False)
    path = args.evidence / "receipt.json"
    receipt = dict(status="NOT_RUN", app_sha=args.expected_app_sha, run_id=os.environ.get("GITHUB_RUN_ID"),
                   run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), commands=[], started_at=datetime.now(timezone.utc).isoformat())
    contract.require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha) and (receipt["run_id"] or "").isdigit()
                     and (receipt["run_attempt"] or "").isdigit(), "Exact source and actual run required")
    original, _ = load_helpers()
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancelled = False
    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in handlers:
        signal.signal(number, cancel)
    def run(command, name, env=None, cwd=None, timeout=900):
        started = datetime.now(timezone.utc)
        entry = dict(name=name, argv=list(map(str, command)), status="RUNNING", timeout_seconds=timeout,
                     started_at=started.isoformat()); receipt["commands"].append(entry)
        contract.save(path, receipt)
        log = args.evidence / (name + ".log")
        try:
            entry["pid"] = original.native.process_control.run_process(entry["argv"], cwd or args.control,
                                                                       env or os.environ.copy(), log, timeout)
            entry["status"] = "PASS_EXIT_0"
        except BaseException as error:
            entry["status"] = "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL"
            entry.update(error_type=type(error).__name__, error=str(error))
            raise
        finally:
            finished = datetime.now(timezone.utc)
            entry.update(finished_at=finished.isoformat(), elapsed_seconds=(finished - started).total_seconds())
            if log.is_file():
                entry.update(log=log.name, log_bytes=log.stat().st_size, log_sha256=contract.digest(log))
            contract.save(path, receipt)
        return log
    try:
        execute(args, receipt, run)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat(); contract.save(path, receipt)
        for number, handler in handlers.items():
            signal.signal(number, handler)
    return int(receipt["status"] != contract.PASS)


if __name__ == "__main__":
    raise SystemExit(main())
