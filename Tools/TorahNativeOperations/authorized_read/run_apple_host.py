#!/usr/bin/env python3
"""One iOS SwiftPM test build using the separately qualified candidate Lib.

Only the fixed25 newly authored Heart methods execute. No ordinary App build,
previous native cases, shared/Any package methods, default install or activation.
"""
from __future__ import annotations
import argparse
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
import tarfile
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_apple as native

require, digest, git = native.require, native.digest, native.git
PACKAGE = "HeartAuthorizedReadHarness"
TARGET = PACKAGE + "Tests"
PROFILES = {
    "HeartAuthorizedOperationCodecTests": [
        "testRequestContainsOnlyOwnedSpaceAndOperationIdentity",
        "testCompleteConflictPreservesOpaqueBytesTargetsAndNativeReceipts",
        "testAbsenceRequiresCompleteNativeSnapshot",
        "testCanonicalMutationOrIdentityMismatchRejectsEntireClosure",
        "testAuthorityBindingUsesExactUTF8",
        "testDuplicateOrUnknownProvenanceCannotBeReleased",
        "testMalformedAndOversizedTransportCannotReleasePayload",
        "testNativeFailureRequiresAbsentPayloadAndMapsStableReason",
        "testCanonicalDecoderRejectsNoncanonicalObservedSetAndTrailingBytes",
    ],
    "HeartAuthorizedOperationSessionTests": [
        "testSameOwnerReadsAndPublishesCompleteNativeResult",
        "testInvalidationWhileNativeCallSuspendsDropsWholeSnapshot",
        "testCancellationWhileNativeCallSuspendsDropsWholeSnapshot",
        "testReopeningIdenticalPublicIDsCannotPublishOldLifetime",
        "testInvalidatedSessionNeverCallsNativeTransport",
    ],
    "HeartAuthorizedOperationNativeFixtureTests": [
        "testActualGeneratedNativeBytesDecodeAcrossColdReopenAndBlockUnreachability",
    ],
    "PinkhaNativeReadLifetimeTests": [
        "testOnlySuccessfulOwnedAccountAndSpaceOpenCreateLease",
        "testRetirementPrecedesNativeCompletionAndNeverReactivatesOldLease",
        "testOverlappingAccountSelectionsNeverActivateInEitherCompletionOrder",
        "testAccountAndSpaceOverlapCannotBindRegardlessOfDispatchOrCompletionOrder",
        "testOverlappingSameSpaceOpensNeverActivateInEitherCompletionOrder",
        "testActualSpaceClosureAndWorkspaceSelectionFencePendingOpen",
        "testIndependentSpacesStayIndependentInsideOneVerifiedAccount",
        "testEveryExistingAccountTransitionRetiresBeforeDispatch",
        "testByteResponseLimitIsDistinctFromMalformedEmptyResponse",
    ],
    "HeartAuthorizedOperationLibTests": [
        "testActualLibReadOwnsAccountAndSpaceAcrossNativeReopenAndRetirement",
    ],
}
SOURCES = {
    "HeartAuthorizedOperationCodecTests": "Modules/PinkhaHeartEngine/Tests/PinkhaHeartEngineTests/HeartAuthorizedOperationCodecTests.swift",
    "HeartAuthorizedOperationSessionTests": "Modules/PinkhaHeartEngine/Tests/PinkhaHeartEngineTests/HeartAuthorizedOperationSessionTests.swift",
    "HeartAuthorizedOperationNativeFixtureTests": "Modules/PinkhaHeartEngine/Tests/PinkhaHeartEngineTests/HeartAuthorizedOperationNativeFixtureTests.swift",
    "PinkhaNativeReadLifetimeTests": "Modules/ProtobufMessages/Tests/ProtobufMessagesTests/PinkhaNativeReadLifetimeTests.swift",
    "HeartAuthorizedOperationLibTests": "Tools/TorahNativeOperations/authorized_read/apple/HostTests/HeartAuthorizedOperationLibTests.swift",
}
PINS = {
    "torahinspectorkit": "511454e49450cb2581ddf77f644146ff3e30dbef",
    "swift-protobuf": "c6fe6442e6a64250495669325044052e113e990c",
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
}
MODULES = ["PinkhaKit", "PinkhaHeartEngine", "PinkhaHeartNative", "ProtobufMessages"]
GENERATED_FIXTURE = "Tools/TorahNativeOperations/authorized_read/apple/HostTests/Generated/pinkha_append_fixture.pb.swift"
GENERATED_FIXTURE_SHA = "df0e0d20cd620a0336e76a6ddb5ce603da34d44c6dfe76d55832bdbebea2d3ab"


def command_json(path):
    # Xcode can put a diagnostic before/after otherwise valid JSON. Retain the
    # entire original log and require exactly one top-level JSON document.
    text = path.read_text(encoding="utf8")
    decoder = json.JSONDecoder(); documents = []
    consumed_until = 0
    for match in re.finditer(r"(?m)^[\[{]", text):
        if match.start() < consumed_until: continue
        try: value, length = decoder.raw_decode(text[match.start():])
        except ValueError: continue
        documents.append(value); consumed_until = match.start() + length
    require(len(documents) == 1 and isinstance(documents[0], dict), "Ambiguous or absent command JSON")
    return documents[0]


def expected_methods():
    return {suite + "/" + method for suite, methods in PROFILES.items() for method in methods}


def source_selection(control):
    require(len(expected_methods()) == 25 and len(PROFILES) == 5, "Fixed25 candidate selection changed")
    hashes = {}
    for suite, name in SOURCES.items():
        source = (control/name).read_text(encoding="utf8")
        require(re.search(r"final class " + re.escape(suite) + r": XCTestCase", source), "Expected XCTest suite missing")
        actual = re.findall(r"^    func (test\w+)\(", source, re.M)
        require(len(actual) == len(set(actual)) and set(actual) == set(PROFILES[suite]), "Candidate method declaration changed")
        hashes[name] = digest(control/name)
    require(digest(control/GENERATED_FIXTURE) == GENERATED_FIXTURE_SHA, "Pinned actual generated append fixture changed")
    hashes[GENERATED_FIXTURE] = GENERATED_FIXTURE_SHA
    return hashes


def validate_execution(summary, tree, udid):
    expected = expected_methods()
    counts = {key: summary.get(key) for key in ["totalTestCount", "passedTests", "failedTests", "skippedTests"]}
    require(all(type(value) is int for value in counts.values())
            and counts == {"totalTestCount": 25, "passedTests": 25, "failedTests": 0, "skippedTests": 0},
            "Exactly25 actual passing candidate methods without skips required")
    destinations = summary.get("devicesAndConfigurations", [])
    require(len(destinations) == 1, "Exactly one owned test destination required")
    device = destinations[0].get("device", {})
    require(str(device.get("deviceId", "")).lower() == udid.lower()
            and str(device.get("osVersion", "")).split(".")[0] == "27"
            and device.get("osBuildNumber") and device.get("architecture") == "arm64",
            "Wrong actual iOS27 ARM64 destination")
    verifier_path = ROOT / "Tools/AnyEnginePort/verify_native_test_execution.py"
    spec = importlib.util.spec_from_file_location("retained_xcresult_case_parser", verifier_path)
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    cases = verifier.test_cases(tree)
    require(len(cases) == 25 and all(result == "Passed" for result in cases.values()), "Missing/nonpassing actual test node")
    observed = set()
    for identifier in cases:
        matches = [method for method in expected if re.search(r"(?:^|/)" + re.escape(method) + r"(?:\(|/|$)", identifier)]
        require(len(matches) == 1 and matches[0] not in observed, "Unexpected or duplicate actual candidate method")
        observed.add(matches[0])
    require(observed == expected, "Incomplete named candidate execution")
    return {"counts": counts, "methods": sorted(observed), "actual_cases": cases, "device": device}


def validate_native_result(value, configuration):
    expected = {"status": "PASS_ACTUAL_HEART_LIB_SHARED_READ", "run_id": configuration["runID"],
                "app_sha": configuration["appSHA"], "nonce": configuration["nonce"],
                "candidate_sha256": native.CANDIDATE, "native_version": native.VERSION,
                "actual_append_calls": 1, "signed_native_provenance": True, "verified_local_absence": True,
                "block_delete_preserved_history": True, "native_account_reopen_preserved_unreachable_history": True,
                "retirement_while_stop_pending": True, "publication_denied_at_retirement": True,
                "space_delete_retired_reader": True, "app_capability": "OFF",
                "fresh_ios_process_reopen": "NOT_RUN", "two_app_clients": "NOT_RUN"}
    require(all(value.get(key) == item and type(value.get(key)) is type(item) for key, item in expected.items()),
            "Actual native iOS journey is incomplete or from another source/runtime")
    extra = {"pid", "account_id_sha256", "space_id_sha256", "canonical_sha256"}
    require(set(value) == set(expected) | extra and type(value["pid"]) is int and value["pid"] > 0,
            "Missing owned native PID or unexpected native payload")
    require(all(isinstance(value[name], str) and re.fullmatch(r"[0-9a-f]{64}", value[name])
                for name in extra - {"pid"}), "Missing native byte/identity hashes")
    return value


def validate_runtime(receipt, run, qualified):
    require(run.get("status") == "completed" and run.get("conclusion") == "success"
            and str(run.get("id")) == str(receipt.get("run_id"))
            and str(run.get("run_attempt")) == str(receipt.get("run_attempt"))
            and run.get("head_sha") == receipt.get("app_sha")
            and run.get("head_branch") == "codex/chatgpt-wave15-shared-20261121"
            and run.get("event") == "workflow_dispatch"
            and run.get("display_title") == "Pinkha t2-authorized-read-apple-runtime \u00b7 " + str(run.get("head_sha"))
            and run.get("path") == ".github/workflows/torah-inspector-ipados27.yml",
            "Runtime was not produced by the successful controlled candidate route")
    require(receipt.get("status") == "APPLE_SIMULATOR_FRAMEWORK_BUILT_NOT_EXECUTED"
            and receipt.get("candidate_sha256") == native.CANDIDATE
            and receipt.get("expected_app_get_version") == native.VERSION
            and receipt.get("heart_sha") == native.rpc.HEART
            and receipt.get("native_tests_executed_this_run") == 0
            and receipt.get("qualified_native_run") == native.QUALIFIED_RUN,
            "Wrong native candidate build receipt")
    for actual_key, qualified_key in [("generated_sha256", "generated_sha256"),
                                       ("native_source_sha256", "source_sha256"), ("module_sha256", "module_sha256")]:
        require(receipt.get(actual_key) == qualified[qualified_key], "Candidate native input changed: " + actual_key)


def unpack_runtime(archive, destination):
    require(not destination.exists(), "Fresh candidate runtime directory required")
    destination.mkdir()
    names = set(); unpacked_bytes = 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            name = Path(member.name)
            require(name.parts and not name.is_absolute() and ".." not in name.parts and name.as_posix() not in names
                    and (member.isfile() or member.isdir())
                    and (name.as_posix() == "HeartAuthorizedReadBuild.json" or name.parts[0] == "Lib.xcframework"),
                    "Unsafe or unexpected runtime archive entry")
            names.add(name.as_posix()); unpacked_bytes += member.size
            require(len(names) <= 4096 and unpacked_bytes <= 2 * 1024**3, "Candidate archive exceeds bounded inventory")
            target = destination / name
            if member.isdir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open("xb") as output: shutil.copyfileobj(source, output)
    receipt = json.loads((destination/"HeartAuthorizedReadBuild.json").read_bytes())
    framework = destination/"Lib.xcframework"
    hashes = {p.relative_to(framework).as_posix(): digest(p) for p in framework.rglob("*") if p.is_file()}
    require(hashes == receipt.get("framework_files_sha256"), "Candidate framework archive changed")
    import plistlib
    native.validate_simulator_framework(plistlib.loads((framework/"Info.plist").read_bytes()), receipt["binary_slices"])
    require(all(hashes.get(item["path"]) == item["sha256"] for item in receipt["binary_slices"]),
            "Actual candidate binary differs from slice receipt")
    return receipt, framework


def prepare_harness(control, work, framework, configuration):
    client = work/"client"; client.mkdir()
    names = subprocess.check_output(["git", "-C", str(control), "ls-files", "-z", "--",
                                      *("Modules/"+name for name in MODULES)]).decode().split("\0")
    hashes = {}
    for name in filter(None, names):
        source, target = control/name, client/name
        require(source.is_file() and not source.is_symlink(), "Only tracked regular module source may enter host")
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
        hashes[name] = digest(source)
        require(digest(target) == hashes[name], "Owned module copy differs")
    destination = client/"Dependencies/Middleware/Lib.xcframework"
    destination.parent.mkdir(parents=True); shutil.copytree(framework, destination)
    harness = client/"Harness"; tests = harness/"Tests"/TARGET; tests.mkdir(parents=True)
    template = control/"Tools/TorahNativeOperations/authorized_read/apple/HarnessPackage.swift"
    shutil.copyfile(template, harness/"Package.swift")
    stub = harness/"Sources"/PACKAGE/"Harness.swift"; stub.parent.mkdir(parents=True)
    stub.write_text("public enum HeartAuthorizedReadHarness {}\n")
    for name in SOURCES.values(): shutil.copyfile(control/name, tests/Path(name).name)
    shutil.copyfile(control/GENERATED_FIXTURE, tests/Path(GENERATED_FIXTURE).name)
    fixtures = control/"Modules/PinkhaHeartEngine/Tests/PinkhaHeartEngineTests/Fixtures"
    shutil.copytree(fixtures, tests/"Fixtures")
    (tests/"host-config.json").write_text(json.dumps(configuration, sort_keys=True)+"\n")
    return harness, hashes


def validate_pins(harness):
    paths = list(harness.rglob("Package.resolved"))
    require(paths, "No actual Xcode package resolution receipt")
    accepted = []
    for path in paths:
        value = json.loads(path.read_bytes())
        actual = {item["identity"]: item["state"]["revision"] for item in value.get("pins", [])}
        require(actual == PINS, "Resolved dependency revisions differ from fixed reviewed inputs")
        accepted.append({"path": str(path.relative_to(harness)), "sha256": digest(path)})
    return accepted


def execute(args, receipt, run):
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual ARM64 iOS simulator host required")
    control, work, evidence = args.control, args.work, args.evidence
    require(git(control, "rev-parse", "HEAD") == args.expected_app_sha and not git(control, "status", "--porcelain"), "Exact clean source required")
    require(not work.exists(), "Fresh owned host work required"); work.mkdir()
    sources = source_selection(control)
    observed_run = command_json(run(["gh", "api", "repos/davidpovarsky/anytype-swift/actions/runs/"+args.runtime_run], "runtime-source-run"))
    runtime_receipt, framework = unpack_runtime(args.runtime_archive, work/"runtime")
    validate_runtime(runtime_receipt, observed_run, native.qualified_generation(control))
    require(str(runtime_receipt["run_id"]) == args.runtime_run, "Downloaded runtime is from another run")
    configuration = {"runID": receipt["run_id"], "appSHA": args.expected_app_sha, "nonce": str(uuid4()),
                     "candidate": native.CANDIDATE, "runtimeVersion": native.VERSION}
    harness, module_hashes = prepare_harness(control, work, framework, configuration)
    env = dict(os.environ, PINKHA_NATIVE_T2_AUTHORIZED_READ_V1="1", PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE="1")
    receipt.update(test_source_sha256=sources, copied_module_sha256=module_hashes, configuration=configuration,
                   native_runtime_source={"run_id": args.runtime_run, "app_sha": runtime_receipt["app_sha"],
                        "archive_sha256": digest(args.runtime_archive), "binary_slices": runtime_receipt["binary_slices"]})
    package_cache = ["-clonedSourcePackagesDirPath", str(work/"SourcePackages")]
    schemes = command_json(run(["xcodebuild", "-list", "-json", *package_cache], "schemes", env, harness))
    available = schemes.get("workspace", schemes.get("project", {})).get("schemes", [])
    allowed = [name for name in [PACKAGE, PACKAGE+"-Package"] if name in available]
    require(allowed, "Expected minimal package scheme missing")
    scheme = allowed[0]; receipt["actual_package_scheme"] = scheme
    run(["xcodebuild", "-resolvePackageDependencies", "-scheme", scheme, *package_cache], "resolve-packages", env, harness)
    pins = validate_pins(harness); receipt["resolved_packages"] = pins
    data = command_json(run(["xcrun", "simctl", "list", "runtimes", "-j"], "runtimes"))
    runtimes = [value for value in data["runtimes"] if value.get("isAvailable")
                and value.get("identifier", "").startswith("com.apple.CoreSimulator.SimRuntime.iOS-")
                and str(value.get("version", "")).split(".")[0] == "27"]
    require(runtimes, "No available iOS27 runtime")
    runtime = sorted(runtimes, key=lambda item: tuple(map(int, item["version"].split("."))))[-1]
    devices = command_json(run(["xcrun", "simctl", "list", "devicetypes", "-j"], "device-types"))["devicetypes"]
    tablets = [item for item in devices if item.get("productFamily") == "iPad"
               and item.get("minRuntimeVersion", 0) <= 27*65536 <= item.get("maxRuntimeVersion", 2**32)]
    require(tablets, "No compatible iPad simulator type")
    device_type = sorted(tablets, key=lambda item: (item.get("minRuntimeVersion", 0), item["name"]))[-1]
    udid = run(["xcrun", "simctl", "create", "HeartRead-"+configuration["nonce"], device_type["identifier"], runtime["identifier"]],
               "create-owned-simulator").read_text().strip()
    require(re.fullmatch(r"[0-9A-Fa-f-]{36}", udid), "Invalid owned simulator ID")
    receipt["owned_simulator"] = {"udid": udid, "runtime": runtime["identifier"], "type": device_type["identifier"]}
    result = evidence/"heart-read.xcresult"
    try:
        run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator")
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], "wait-owned-simulator", timeout=180)
        selection = ["-only-testing:"+TARGET+"/"+method for method in sorted(expected_methods())]
        run(["xcodebuild", "test", "-scheme", scheme, "-configuration", "Debug", "-destination", "platform=iOS Simulator,id="+udid,
             "-derivedDataPath", str(work/"DerivedData"), *package_cache,
             "-disableAutomaticPackageResolution", "-parallel-testing-enabled", "NO", "-jobs", "4",
             "-test-timeouts-enabled", "YES", "-maximum-test-execution-time-allowance", "420",
             "-resultBundlePath", str(result), *selection], "ios-candidate-tests", env, harness, timeout=1800)
        summary = command_json(run(["xcrun", "xcresulttool", "get", "test-results", "summary", "--path", str(result)], "xcresult-summary"))
        tree = command_json(run(["xcrun", "xcresulttool", "get", "test-results", "tests", "--path", str(result)], "xcresult-tests"))
        receipt["actual_execution"] = validate_execution(summary, tree, udid)
        attachments = evidence/"attachments"
        run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result), "--output-path", str(attachments)], "export-native-receipt")
        actual = []
        for path in attachments.rglob("*"):
            if path.is_file() and path.stat().st_size < 128*1024:
                try: value = json.loads(path.read_bytes())
                except (ValueError, UnicodeError): continue
                if isinstance(value, dict) and value.get("status") == "PASS_ACTUAL_HEART_LIB_SHARED_READ": actual.append(value)
        require(len(actual) == 1, "Exactly one actual native journey attachment required")
        receipt["actual_native_journey"] = validate_native_result(actual[0], configuration)
        require(validate_pins(harness) == pins and source_selection(control) == sources, "Test source/dependencies changed during execution")
        for name, expected in module_hashes.items():
            require(digest(control/name) == expected and digest(work/"client"/name) == expected, "Module source changed during execution")
        require(git(control, "rev-parse", "HEAD") == args.expected_app_sha and not git(control, "status", "--porcelain"), "Control source changed")
        receipt.update(status="PASS_FIXED25_ACTUAL_HEART_LIB_IOS", fresh_ios_process_reopen="NOT_RUN",
                       prior_native_cases_executed=0, prior_shared_any_package_methods_executed=0)
    finally:
        # This controller owns only this freshly created UDID. Other simulators
        # and native/user process trees are never shutdown or reset here.
        for action in ["shutdown", "delete"]:
            completed = subprocess.run(["xcrun", "simctl", action, udid], capture_output=True, timeout=60)
            receipt.setdefault("owned_simulator_cleanup", {})[action] = completed.returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["control", "work", "evidence", "runtime-archive"]: parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True); parser.add_argument("--runtime-run", required=True)
    args = parser.parse_args(argv)
    for name in ["control", "work", "evidence", "runtime_archive"]: setattr(args, name, getattr(args, name).resolve())
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha) and re.fullmatch(r"[0-9]+", args.runtime_run), "Exact source/run required")
    require(len({args.control, args.work, args.evidence, args.runtime_archive}) == 4, "Separate source/work/evidence/runtime paths required")
    args.evidence.mkdir(parents=True, exist_ok=False)
    receipt_path = args.evidence/"result.json"
    receipt = {"status": "NOT_RUN_PREFLIGHT", "app_sha": args.expected_app_sha,
               "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
               "commands": [], "app_capability": "OFF", "two_app_clients": "NOT_RUN", "default_runtime_changed": False,
               "started_at": datetime.now(timezone.utc).isoformat()}
    handlers = {number: signal.getsignal(number) for number in [signal.SIGTERM, signal.SIGINT]}; cancelling = False
    def cancel(number, frame):
        nonlocal cancelling
        if not cancelling: cancelling = True; raise KeyboardInterrupt(signal.Signals(number).name)
    for number in handlers: signal.signal(number, cancel)
    def run(command, name, env=None, cwd=args.control, timeout=900):
        entry = {"name": name, "argv": list(map(str, command)), "status": "RUNNING"}; receipt["commands"].append(entry)
        native.coverage.write_receipt(receipt_path, receipt)
        try:
            entry["pid"] = native.process_control.run_process(list(map(str, command)), cwd, env or os.environ.copy(), args.evidence/(name+".log"), timeout)
            entry["status"] = "PASS_EXIT_0"; return args.evidence/(name+".log")
        except BaseException: entry["status"] = "FAIL"; raise
        finally: native.coverage.write_receipt(receipt_path, receipt)
    code = 1
    try: execute(args, receipt, run); code = 0
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL", error=type(error).__name__)
        print(type(error).__name__+": "+str(error), file=sys.stderr)
    finally:
        try:
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat(); native.coverage.write_receipt(receipt_path, receipt)
        finally:
            for number, handler in handlers.items(): signal.signal(number, handler)
    return code


if __name__ == "__main__": raise SystemExit(main())
