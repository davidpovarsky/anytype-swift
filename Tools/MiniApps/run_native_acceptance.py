#!/usr/bin/env python3
"""Focused original Anytype editor -> installed MiniApps -> native saved document."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "Tools/Hanlin"), str(ROOT / "Tools/PinkhaNativeDerived")]
import run_host_tests as host
from build_native_ipa import prepare_source_cache, test_configuration
import heart_runtime_profile
from prepare_sdk import verify as verify_sdk
from validate_wave1 import verify_runtime_copies

PREPARE = "PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument"
VERIFY = "PinkhaMiniAppsNativePreparationTests/verifyReturnedNativeDocument"
UI_RETURN = "MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen"
UI_REPLAY = "MiniAppsNativeAcceptanceUITests/testDuplicateCallbackDoesNotInsertAgain"

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        while chunk := source.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()

def git(app, *args):
    return subprocess.check_output(["git", "-C", str(app), *args], text=True).strip()

def configure_tests(original, destination, environment):
    data = plistlib.loads(original.read_bytes())
    count = 0
    def visit(value):
        nonlocal count
        if isinstance(value, dict):
            if "TestBundlePath" in value:
                value.setdefault("EnvironmentVariables", {}).update(environment)
                count += 1
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        if isinstance(value, str):
            return value.replace("__TESTROOT__", str(original.parent))
        return value
    data = visit(data)
    require(count > 0, "Actual xctestrun contains no test target")
    destination.write_bytes(plistlib.dumps(data))
    return destination

def execute(args, receipt):
    app, evidence = args.app.resolve(), args.evidence.resolve()
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon/Xcode required")
    pin = json.loads((app / "Tools/MiniApps/producer.json").read_text())
    head = git(app, "rev-parse", "HEAD")
    require(head == os.environ["GITHUB_SHA"] and git(app, "branch", "--show-current") == pin["consumer_branch"],
            "Unreviewed MiniApps consumer source")
    require(not git(app, "diff", "--name-only", "HEAD"), "Tracked source differs before native build")
    require(args.runtime_profile == pin["runtime_profile"] and args.heart_source_run_id == pin["heart_source_run_id"],
            "Only the retained original Heart is selected")
    require(args.device == "ipad" and args.language == "en", "This focused UI selection requires its declared iPad/English fixture")
    sdk = verify_sdk(app / "Dependencies/Hanlin")
    require(sdk["revision"] == pin["revision"], "Actual bridge snapshot differs")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight["status"] == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight["source_sha"] == head
            and preflight["run_id"] == os.environ["GITHUB_RUN_ID"], "Disposable simulator source differs")
    udid = preflight["selected"]["ipad"]["udid"]
    installation = json.loads((evidence / "heart/heart-installation.json").read_text())
    binding = heart_runtime_profile.installed_binding(app, installation, head, args.runtime_profile, args.heart_source_run_id)
    producer = json.loads((evidence / "miniapps-producer.json").read_text())
    require(producer["status"] == "VERIFIED_COMPILED_COMPANION" and producer["pin"] == pin, "Original companion artifact is unverified")
    companion = Path(producer["app"])
    require(companion.is_dir(), "Verified companion app disappeared")
    derived = app / "build" / ("miniapps-derived-" + os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"])
    require(not derived.exists(), "This focused build requires fresh products")
    receipt.update(source_sha=head, run_id=os.environ["GITHUB_RUN_ID"], run_attempt=os.environ["GITHUB_RUN_ATTEMPT"],
                   companion=producer, heart=installation, native_binding=binding, device=udid,
                   selected_methods=[PREPARE, UI_RETURN, UI_REPLAY, VERIFY], configuration="Debug-Anytype",
                   release_accepted=False, physical_sharing="NOT_PROVEN_BY_SIMULATOR")

    def save(phase):
        receipt["phase"] = phase
        write(evidence / "execution.json", receipt)
        print(json.dumps({"phase": phase, "source": head}), flush=True)

    def command(argv, name, timeout=5400):
        save(name)
        with (evidence / (name + ".log")).open("w") as output:
            result = subprocess.run(argv, cwd=app, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        require(result.returncode == 0, f"{name} returned {result.returncode}; see the original log")

    subprocess.run(["xcrun", "simctl", "boot", udid], check=True, capture_output=True)
    command(["xcrun", "simctl", "bootstatus", udid, "-b"], "boot", timeout=120)
    prepare_source_cache(app, derived)
    flags = ["OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D DEBUG", "ENABLE_TESTABILITY=YES",
             "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
    common = ["-configuration", "Debug-Anytype", "-destination", "platform=iOS Simulator,id=" + udid,
              "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO"]
    command(["xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
             *common, "-only-testing:AnytypeTests/PinkhaMiniAppsNativePreparationTests", *flags], "build-native")
    native_configuration = test_configuration(derived / "Build/Products", "AnytypeTests")
    built, app_executable, bundle, test_executable = host.xctest_products(native_configuration)
    info = plistlib.loads((built / "Info.plist").read_bytes())
    source_bundle = info["CFBundleIdentifier"]
    schemes = [scheme for entry in info.get("CFBundleURLTypes", []) for scheme in entry.get("CFBundleURLSchemes", [])]
    source_scheme = next(value for value in schemes if value != "anytype")
    require("$(" not in source_scheme, "Callback scheme was not resolved")
    entitlement_bytes = subprocess.check_output(["codesign", "-d", "--entitlements", ":-", str(built)], stderr=subprocess.PIPE)
    entitlements = plistlib.loads(entitlement_bytes)
    require(set(entitlements["com.apple.security.application-groups"]) ==
            {"group.io.anytype.app.dev", "group.com.itorah.shared"}, "Native app has different real group entitlements")
    write(evidence / "built-entitlements.json", entitlements)
    verify_runtime_copies(built, binding["native_marker"].encode(), evidence)
    receipt["source_bundle"] = source_bundle
    receipt["native_build_succeeded"] = True
    verify_sdk(app / "Dependencies/Hanlin")
    command(["xcodebuild", "build-for-testing", "-workspace", "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace",
             "-scheme", "PinkhaStage1Acceptance", *common,
             "-only-testing:PinkhaStage1AcceptanceUITests/MiniAppsNativeAcceptanceUITests", *flags], "build-ui")
    ui_configuration = test_configuration(derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    # Both builds are complete; bind the exact products that will execute.
    receipt["app_files"] = {str(path.relative_to(built)): digest(path)
                            for path in built.rglob("*") if path.is_file() and not path.is_symlink()}
    receipt["test_executable_sha256"] = digest(test_executable)
    command(["xcrun", "simctl", "install", udid, str(companion)], "install-companion", timeout=120)
    environment = dict(PINKHA_SIMULATOR_UI_DISPOSABLE="1", PINKHA_MINIAPPS_NATIVE_TESTING="1",
                       GITHUB_SHA=head, GITHUB_RUN_ID=os.environ["GITHUB_RUN_ID"],
                       GITHUB_RUN_ATTEMPT=os.environ["GITHUB_RUN_ATTEMPT"])

    def test(configuration, target, method, name, additions=None):
        env = {**environment, **(additions or {})}
        configured = configure_tests(configuration, evidence / (name + ".xctestrun"), env)
        result_path = evidence / (name + ".xcresult")
        try:
            command(["xcodebuild", "test-without-building", "-xctestrun", str(configured),
                     "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                     "-only-testing:" + target + "/" + method, "-resultBundlePath", str(result_path)], name, timeout=600)
        finally:
            if result_path.exists():
                for mode in ("summary", "tests"):
                    output = subprocess.run(["xcrun", "xcresulttool", "get", "test-results", mode,
                        "--path", str(result_path), "--format", "json"], capture_output=True, text=True)
                    (evidence / (name + "-" + mode + ".json")).write_text(output.stdout)
                subprocess.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result_path),
                    "--output-path", str(evidence / (name + "-attachments"))], capture_output=True)
        summary = json.loads((evidence / (name + "-summary.json")).read_text())
        tree = json.loads((evidence / (name + "-tests.json")).read_text())
        receipt[name] = host.validate_results(summary, tree, {method}, udid)
        save(name + "-verified")

    def data_container():
        return Path(subprocess.check_output(
            ["xcrun", "simctl", "get_app_container", udid, source_bundle, "data"], text=True).strip())

    test(native_configuration, "AnytypeTests", PREPARE, "prepare")
    fixture_path = data_container() / "Library/Application Support/miniapps-native-fixture.json"
    fixture = json.loads(fixture_path.read_text())
    require(fixture["sourceSHA"] == head and fixture["runID"] == os.environ["GITHUB_RUN_ID"], "Prepared native fixture differs")
    write(evidence / "fixture.json", fixture)
    ui_env = dict(PINKHA_MINIAPPS_FIXTURE_JSON=json.dumps(fixture, ensure_ascii=False),
                  PINKHA_MINIAPPS_SOURCE_BUNDLE=source_bundle, PINKHA_MINIAPPS_SOURCE_SCHEME=source_scheme)
    test(ui_configuration, "PinkhaStage1AcceptanceUITests", UI_RETURN, "return-ui", ui_env)
    journals = []
    for path in (data_container() / "Library/Application Support/MiniAppsReceipts").glob("*/*.json"):
        value = json.loads(path.read_text())
        if value.get("completed"):
            journals.append((path, value))
    require(len(journals) == 2, "Expected actual completed warm and cold host receipts")
    ordered_journals = []
    for key in ("returnedText", "coldReturnedText"):
        matches = [value for _, value in journals
                   if [item.get("text") for item in value.get("additions", [])] == [fixture[key]]]
        require(len(matches) == 1 and len(matches[0]["insertedBlocks"]) == 1,
                "The actual warm/cold native insertion receipt is incomplete")
        ordered_journals.append(matches[0])
    request_ids = [journal["requestID"] for journal in ordered_journals]
    require(len(set(request_ids)) == 2, "Warm and cold invocations must have separate durable identities")
    write(evidence / "completed-host-receipts.json", ordered_journals)
    callbacks = dict(PINKHA_MINIAPPS_REQUEST_ID=request_ids[0], PINKHA_MINIAPPS_COLD_REQUEST_ID=request_ids[1])
    ui_env.update(callbacks)
    test(ui_configuration, "PinkhaStage1AcceptanceUITests", UI_REPLAY, "replay-ui", ui_env)
    test(native_configuration, "AnytypeTests", VERIFY, "native-readback", callbacks)
    proof_path = data_container() / "Library/Application Support/miniapps-native-readback.json"
    proof = json.loads(proof_path.read_text())
    require(proof["status"] == "NATIVE_HEART_READBACK_PASS" and proof["sourceSHA"] == head
            and proof["requestIDs"] == [value.lower() for value in request_ids], "Final native readback receipt differs")
    write(evidence / "native-readback.json", proof)
    require(git(app, "rev-parse", "HEAD") == head, "Source changed during native acceptance")
    verify_sdk(app / "Dependencies/Hanlin")
    receipt.update(status="MINIAPPS_TWO_APP_NATIVE_PASS", phase="COMPLETE",
                   actual_native_preparation=1, actual_ui_methods=2, actual_native_readback=1,
                   actual_companion_invocations=2, warm_callback=True, cold_callback=True,
                   physical_sharing="NOT_PROVEN_BY_SIMULATOR")
    save("COMPLETE")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("app", "evidence", "derived"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--lane", choices=["miniapps-native"], required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--runtime-profile", required=True)
    parser.add_argument("--heart-source-run-id", required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = dict(status="RUNNING", started_at=datetime.now(timezone.utc).isoformat())
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        print(json.dumps(receipt), flush=True)
    finally:
        try:
            host.cleanup(args.evidence, receipt)
        except Exception as error:
            receipt["cleanup_error"] = str(error)
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        write(args.evidence / "execution.json", receipt)
    return 0 if receipt["status"] == "MINIAPPS_TWO_APP_NATIVE_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
