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
from owner_signing import verify as verify_owner_signing

from acceptance_profile import PREPARE, VERIFY, ADAPTER, UI_RETURN, UI_REPLAY, resolve_profile
from resolved_dependencies import ACTIVATION_ARGUMENTS, record_resolution, verify_recorded_resolution
from export_products import export_built_products, product_closure
from simulator_admission import verify_built_entitlements
from selection import configure_tests, selector, validate_enumeration
from consumer_runtime_boundary import inspect as inspect_runtime_boundary
from owned_commands import run_logged

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

def source_context(args, receipt, *, use_recorded_resolution=False):
    from types import SimpleNamespace
    app, evidence = args.app.resolve(), args.evidence.resolve()
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Apple silicon/Xcode required")
    pin = json.loads((app / "Tools/MiniApps/producer.json").read_text())
    owner = verify_owner_signing(app, require_profile_grants=False)
    require(owner["configuration"] == "Debug-MiniAppsOwner", "Unexpected owner configuration")
    head = git(app, "rev-parse", "HEAD")
    branch = git(app, "branch", "--show-current")
    local = getattr(args, "local_execution", None)
    execution_origin = "local-mac" if local else "github-actions"
    if local:
        from local_execution import identity
        execution = identity(app, local, args.local_execution_sha256)
        run_id, run_attempt = execution["run_id"], execution["run_attempt"]
        derived = Path(execution["derived"]).resolve()
        require(str(evidence) == execution["evidence"] and args.derived.resolve() == derived,
                "Local evidence or DerivedData differs from the immutable execution")
    else:
        require(head == os.environ["GITHUB_SHA"] and branch == pin["consumer_branch"],
                "Unreviewed MiniApps consumer source")
        run_id, run_attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
        execution = None
        derived = app / "build" / ("miniapps-derived-" + run_id + "-" + run_attempt)
    if use_recorded_resolution:
        receipt["dependency_resolution"] = verify_recorded_resolution(
            app, evidence, derived, head, run_id, run_attempt,
            activation_arguments=[] if local else None)
    else:
        require(not git(app, "diff", "--name-only", "HEAD"), "Tracked source differs before native build")
    profile = resolve_profile(app, args.lane, branch, local_execution=bool(local))
    require(profile is not None, "The explicit MiniApps source profile was not selected")
    receipt.update(profile)
    if not local:
        require(args.runtime_profile == pin["runtime_profile"] and args.heart_source_run_id == pin["heart_source_run_id"],
                "Only the retained original Heart is selected")
    require(args.device == "ipad" and args.language == "en", "This focused UI selection requires its declared iPad/English fixture")
    sdk = verify_sdk(app / "Dependencies/Hanlin")
    require(sdk["revision"] == pin["revision"], "Actual bridge snapshot differs")
    preflight = json.loads((evidence / "preflight/preflight.json").read_text())
    require(preflight["status"] == "PREFLIGHT_PASS_UI_NOT_RUN" and preflight["source_sha"] == head
            and preflight["run_id"] == run_id
            and preflight["run_attempt"] == run_attempt, "Disposable simulator source differs")
    udid = preflight["selected"]["ipad"]["udid"]
    if local:
        from local_execution import native_input
        require(preflight["execution_origin"] == "local-mac"
                and preflight["local_execution_sha256"] == args.local_execution_sha256,
                "Local preflight lost its actual execution binding")
        installation, binding = native_input(app, evidence)
        require(args.runtime_profile == binding["runtime_profile"]
                and args.heart_source_run_id is None, "Local native input cannot be labelled as an old GitHub artifact")
    else:
        installation = json.loads((evidence / "heart/heart-installation.json").read_text())
        binding = heart_runtime_profile.installed_binding(app, installation, head, args.runtime_profile, args.heart_source_run_id)
    receipt.update(source_sha=head, run_id=run_id, run_attempt=run_attempt,
                   execution_origin=execution_origin, local_execution=execution,
                   local_execution_sha256=args.local_execution_sha256 if local else None,
                   producer_pin=pin, heart=installation, native_binding=binding, device=udid,
                   configuration=owner["configuration"], owner_signing=owner, apple_profile_grants=owner["status"],
                   release_accepted=False, physical_sharing="NOT_PROVEN_BY_SIMULATOR",
                   original_preflight=preflight, original_preflight_sha256=digest(evidence / "preflight/preflight.json"))
    return SimpleNamespace(app=app, evidence=evidence, pin=pin, owner=owner, head=head,
                           udid=udid, binding=binding, derived=derived, local=bool(local))


def product_inventory(native_configuration, ui_configuration):
    """Bind both actual Xcode hosts/bundles and configuration bytes for same-run reuse."""
    products = native_configuration.parent.resolve()
    require(ui_configuration.parent.resolve() == products, "Native/UI products are not from the same owned build")
    roots = set()
    for configuration, blueprint in ((native_configuration, "AnytypeTests"),
                                      (ui_configuration, "PinkhaStage1AcceptanceUITests")):
        entries = []
        def visit(value):
            if isinstance(value, dict):
                if value.get("BlueprintName") == blueprint and "TestBundlePath" in value:
                    entries.append(value)
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
        visit(plistlib.loads(configuration.read_bytes()))
        require(len(entries) == 1, "Expected one actual test bundle declaration for " + blueprint)
        entry = entries[0]
        host_path = Path(entry["TestHostPath"].replace("__TESTROOT__", str(products))).resolve()
        bundle_path = Path(entry["TestBundlePath"].replace("__TESTROOT__", str(products))
                           .replace("__TESTHOST__", str(host_path))).resolve()
        for path in (host_path, bundle_path):
            require(path.is_dir() and path.is_relative_to(products), "Actual test product is missing/outside owned build")
            roots.add(path)
    _, files, references, platform_references = product_closure(
        products, [native_configuration, ui_configuration])
    require(files, "No actual compiled products were found")
    return dict(files=files, original_test_product_references=references,
                xcode_platform_provided_references=platform_references,
                native_configuration_sha256=digest(native_configuration),
                ui_configuration_sha256=digest(ui_configuration))


def build_consumer(args, receipt):
    context = source_context(args, receipt)
    app, evidence, owner, derived = context.app, context.evidence, context.owner, context.derived
    if context.local and derived.exists():
        if getattr(args, "local_failed_cache_snapshot", None) is not None:
            from local_failed_cache_input import admit
            receipt["compiler_cache_input"] = admit(app, derived, evidence,
                args.local_failed_cache_snapshot, args.local_failed_cache_snapshot_sha256)
        else:
            from local_cache_input import admit
            receipt["compiler_cache_input"] = admit(app, derived, evidence, args.local_cache_snapshot,
                                                    args.local_cache_snapshot_sha256)
    else:
        require(not derived.exists(), "This focused build requires fresh products")
    def save(phase):
        receipt["phase"] = phase
        write(evidence / "miniapps-build.json", receipt)
        print(json.dumps({"phase": phase, "source": context.head}), flush=True)
    def command(argv, name, timeout=5400):
        save(name)
        result = run_logged(argv, app, evidence / (name + ".log"), timeout)
        receipt.setdefault("completed_build_commands", {})[name] = {
            "arguments": argv, "return_code": result.returncode, "log_sha256": digest(evidence / (name + ".log"))}
        save(name + "-finished")
        require(result.returncode == 0, f"{name} returned {result.returncode}; see the original log")
    # First boot of a disposable runtime can take longer than the readiness check.
    # Let it initialize while compiling; build-for-testing does not execute the app.
    command(["xcrun", "simctl", "boot", context.udid], "boot-start", timeout=120)
    receipt["simulator_boot_requested"] = True
    receipt["simulator_readiness"] = "NOT_CHECKED_UNTIL_EXECUTION"
    prepare_source_cache(app, derived)
    activation_arguments = [] if context.local else ACTIVATION_ARGUMENTS
    swift_flags = "OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D DEBUG"
    if context.local:
        from local_execution import POLICY
        local_policy = json.loads(POLICY.read_text())
        swift_flags = "OTHER_SWIFT_FLAGS=$(inherited) " + " ".join("-D " + value for value in local_policy["swift_defines"])
        for key, value in local_policy["build_environment"].items():
            require(os.environ.get(key) == value, "Original combined native build environment differs: " + key)
    flags = [swift_flags, "ENABLE_TESTABILITY=YES",
             "ONLY_ACTIVE_ARCH=YES", "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
             "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES", "PROVISIONING_PROFILE_SPECIFIER="]
    if context.local:
        # Copied PCMs retain nonrelocatable paths even when a textual donor scan is empty.
        # Use an empty owned cache without deleting the original copied evidence.
        module_cache = derived / "MiniAppsCurrentModuleCache.noindex"
        cache = receipt.get("compiler_cache_input")
        require(not module_cache.exists() or
                (cache is not None
                 and cache["status"] in {
                     "ADMITTED_SAME_PATH_SOURCE_IDENTICAL_OWNED_COMPILER_CACHE",
                     "ADMITTED_FAILED_OWN_CACHE_FOR_ACTUAL_REBUILD_ONLY"}
                 and cache["module_cache"] == str(module_cache)
                 and cache.get("new_native_or_ui_credit") == 0
                 and cache.get("both_actual_compiler_commands_and_postgates_required") is True),
                "Existing module cache must be the exact admitted same-path cache with actual rebuild gates")
        flags += ["ARCHS=arm64", "CLANG_MODULE_CACHE_PATH=" + str(module_cache),
                  "SWIFT_MODULE_CACHE_PATH=" + str(module_cache)]
    scheduling = ["-jobs", "2"] if context.local else []
    common = [*scheduling, "-configuration", owner["configuration"], "-destination", "platform=iOS Simulator,id=" + context.udid,
              "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO"]
    command(["xcodebuild", "-resolvePackageDependencies", "-project", "Anytype.xcodeproj",
             "-scheme", "Anytype", *common], "resolve-native-packages", timeout=1800)
    receipt["dependency_resolution"] = record_resolution(
        app, evidence, derived, context.head, receipt["run_id"], receipt["run_attempt"], "native",
        activation_arguments=activation_arguments)
    command(["xcodebuild", "build-for-testing", "-project", "Anytype.xcodeproj", "-scheme", "Anytype",
             *common, "-disableAutomaticPackageResolution", *activation_arguments,
             "-only-testing:AnytypeTests/PinkhaMiniAppsNativePreparationTests", *flags], "build-native")
    receipt.update(native_build_succeeded=True, ui_build_succeeded=False, actual_test_methods=0,
                   status="NATIVE_BUILD_PASS_UI_NOT_BUILT")
    save("NATIVE_BUILD_COMPLETE_POSTBUILD_VALIDATION_PENDING")
    native_configuration = test_configuration(derived / "Build/Products", "AnytypeTests")
    receipt["native_early_products"] = export_built_products(derived / "Build/Products",
        [native_configuration], evidence / "miniapps-native-early-products", receipt)
    save("NATIVE_PRODUCTS_EXPORTED")
    built, app_executable, bundle, test_executable = host.xctest_products(native_configuration)
    info = plistlib.loads((built / "Info.plist").read_bytes())
    source_bundle = info["CFBundleIdentifier"]
    require(source_bundle == owner["bundle_ids"]["Anytype"], "Built app is not the registered owner family")
    require(info.get("PinkhaNativeAppGroup") == owner["native_app_group"], "Built native storage group differs")
    schemes = [scheme for entry in info.get("CFBundleURLTypes", []) for scheme in entry.get("CFBundleURLSchemes", [])]
    source_scheme = (source_bundle if source_bundle in schemes else
                     next(value for value in schemes if value != "anytype")).lower()
    require("$(" not in source_scheme, "Callback scheme was not resolved")
    receipt["native_entitlement_admission"] = verify_built_entitlements(
        app, built, app_executable, owner, evidence, "built-native")
    verify_runtime_copies(built, context.binding["native_marker"].encode(), evidence)
    receipt.update(source_bundle=source_bundle, source_scheme=source_scheme, native_build_succeeded=True)
    verify_sdk(app / "Dependencies/Hanlin")
    verify_recorded_resolution(app, evidence, derived, context.head, receipt["run_id"], receipt["run_attempt"],
                               activation_arguments=[] if context.local else None)
    command(["xcodebuild", "-resolvePackageDependencies", "-workspace",
             "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace",
             "-scheme", "PinkhaStage1Acceptance", *common], "resolve-ui-packages", timeout=1800)
    receipt["dependency_resolution"] = record_resolution(
        app, evidence, derived, context.head, receipt["run_id"], receipt["run_attempt"], "ui",
        activation_arguments=activation_arguments)
    command(["xcodebuild", "build-for-testing", "-workspace", "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace",
             "-scheme", "PinkhaStage1Acceptance", *common, "-disableAutomaticPackageResolution", *activation_arguments,
             "-only-testing:PinkhaStage1AcceptanceUITests/MiniAppsNativeAcceptanceUITests", *flags], "build-ui")
    receipt.update(ui_build_succeeded=True, status="NATIVE_AND_UI_BUILD_PASS_VALIDATION_PENDING")
    save("UI_BUILD_COMPLETE_POSTBUILD_VALIDATION_PENDING")
    ui_configuration = test_configuration(derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    receipt["complete_early_products"] = export_built_products(derived / "Build/Products",
        [native_configuration, ui_configuration], evidence / "miniapps-complete-early-products", receipt)
    save("COMPLETE_PRODUCTS_EXPORTED")
    verify_recorded_resolution(app, evidence, derived, context.head, receipt["run_id"], receipt["run_attempt"],
                               activation_arguments=[] if context.local else None)
    receipt["final_entitlement_admission"] = verify_built_entitlements(
        app, built, app_executable, owner, evidence, "built-final")
    receipt["standalone_runtime_boundary"] = inspect_runtime_boundary(app, built, evidence)
    receipt.update(status="BUILD_PASS_TESTS_NOT_RUN", native_configuration=str(native_configuration),
                   ui_configuration=str(ui_configuration), built_app=str(built),
                   product_inventory=product_inventory(native_configuration, ui_configuration),
                   app_files={str(path.relative_to(built)): digest(path) for path in built.rglob("*")
                              if path.is_file() and not path.is_symlink()},
                   test_executable_sha256=digest(test_executable), actual_test_methods=0,
                   finished_at=datetime.now(timezone.utc).isoformat())
    save("CONSUMER_BUILD_COMPLETE_PRODUCER_PENDING")


def prepare_authenticated_dependencies(app, evidence, producer_work, requested_lane, runtime_profile, heart_source_run_id):
    """Build first; use the existing authenticated step only for the exact artifact read."""
    from types import SimpleNamespace
    from download_producer import download
    args = SimpleNamespace(app=Path(app), evidence=Path(evidence), lane=requested_lane,
        device=os.environ.get("UI27_DEVICE_FAMILY", ""), language=os.environ.get("UI27_LANGUAGE", ""),
        runtime_profile=runtime_profile, heart_source_run_id=heart_source_run_id)
    receipt = dict(status="BUILDING", started_at=datetime.now(timezone.utc).isoformat())
    stage = "CONSUMER_BUILD"
    try:
        build_consumer(args, receipt)
        stage = "PRODUCER_DEPENDENCY_WAIT_AFTER_CONSUMER_BUILD"
        download(args.app, producer_work, args.evidence)
    except BaseException as error:
        if receipt.get("status") != "BUILD_PASS_TESTS_NOT_RUN":
            status = ("BUILD_PASS_POSTBUILD_VALIDATION_FAILED_TESTS_NOT_RUN" if receipt.get("ui_build_succeeded")
                      else "NATIVE_BUILD_PASS_LATER_STAGE_FAILED_TESTS_NOT_RUN" if receipt.get("native_build_succeeded")
                      else "BUILD_FAILED_TESTS_NOT_RUN")
            receipt.update(status=status, error_type=type(error).__name__, error=str(error),
                           finished_at=datetime.now(timezone.utc).isoformat())
            write(args.evidence / "miniapps-build.json", receipt)
        failure = dict(status="FAIL", phase=stage, build_receipt="miniapps-build.json",
                       consumer_build_status=receipt.get("status"), actual_test_methods=0,
                       error_type=type(error).__name__, error=str(error),
                       requested_lane=requested_lane, effective_lane="miniapps-native",
                       physical_sharing="NOT_PROVEN_BY_SIMULATOR")
        try:
            host.cleanup(args.evidence, failure)
        except Exception as cleanup_error:
            failure["cleanup_error"] = str(cleanup_error)
        write(args.evidence / "execution.json", failure)
        raise


def execute(args, receipt):
    context = source_context(args, receipt, use_recorded_resolution=True)
    app, evidence, head, udid, owner = context.app, context.evidence, context.head, context.udid, context.owner
    build = json.loads((evidence / "miniapps-build.json").read_text())
    require(build["status"] == "BUILD_PASS_TESTS_NOT_RUN", "The consumer must have actually compiled before producer waiting")
    for key in ("source_sha", "run_id", "run_attempt", "requested_lane", "effective_lane", "source_profile_sha256",
                "selected_methods", "configuration", "owner_signing", "producer_pin", "device", "heart", "native_binding",
                "dependency_resolution", "original_preflight", "original_preflight_sha256",
                "execution_origin", "local_execution", "local_execution_sha256"):
        require(build[key] == receipt[key], "Prepared consumer build identity differs: " + key)
    native_configuration = test_configuration(context.derived / "Build/Products", "AnytypeTests")
    ui_configuration = test_configuration(context.derived / "Build/Products", "PinkhaStage1AcceptanceUITests")
    require(str(native_configuration) == build["native_configuration"] and str(ui_configuration) == build["ui_configuration"],
            "Prepared Xcode test configurations differ")
    require(product_inventory(native_configuration, ui_configuration) == build["product_inventory"],
            "Actual consumer/test products changed during producer dependency waiting")
    source_bundle, source_scheme = build["source_bundle"], build["source_scheme"]
    _, current_executable, _, _ = host.xctest_products(native_configuration)
    require(digest(current_executable) == build["final_entitlement_admission"]["embedded"]["executable_sha256"],
            "The actual entitlement-admitted executable changed before execution")
    receipt["simulator_entitlement_admission"] = build["final_entitlement_admission"]
    receipt.update(native_build_succeeded=True, build_receipt="miniapps-build.json", reused_same_run_build=True,
                   source_bundle=source_bundle, app_files=build["app_files"],
                   test_executable_sha256=build["test_executable_sha256"])
    producer = json.loads((evidence / "miniapps-producer.json").read_text())
    require(producer["status"] == "VERIFIED_COMPILED_COMPANION" and producer["pin"] == context.pin,
            "Original companion artifact is unverified")
    companion = Path(producer["app"])
    require(companion.is_dir(), "Verified companion app disappeared")
    receipt["companion"] = producer
    def save(phase):
        receipt["phase"] = phase
        write(evidence / "execution.json", receipt)
        print(json.dumps({"phase": phase, "source": head}), flush=True)
    def command(argv, name, timeout=5400):
        save(name)
        result = run_logged(argv, app, evidence / (name + ".log"), timeout)
        require(result.returncode == 0, f"{name} returned {result.returncode}; see the original log")
    # Preserve the genuine build receipt even if the runtime is unavailable.
    # Readiness is still mandatory, with the original bound, before any install/test.
    try:
        command(["xcrun", "simctl", "bootstatus", udid, "-b"], "simulator-readiness", timeout=120)
        receipt["simulator_readiness"] = "SIMCTL_BOOTSTATUS_PASS"
    finally:
        try:
            state = subprocess.run(["xcrun", "simctl", "list", "devices", "--json"],
                                   capture_output=True, text=True, timeout=30)
            if state.returncode == 0:
                devices = json.loads(state.stdout).get("devices", {})
                owned = [device for entries in devices.values() for device in entries
                         if device.get("udid") == udid]
                write(evidence / "simulator-readiness-state.json", dict(device=udid, observed=owned))
            else:
                write(evidence / "simulator-readiness-state.json",
                      dict(device=udid, diagnostic_returncode=state.returncode, stderr=state.stderr))
        except Exception as diagnostic_error:
            write(evidence / "simulator-readiness-state.json",
                  dict(device=udid, diagnostic_error=str(diagnostic_error)))
    command(["xcrun", "simctl", "install", udid, str(companion)], "install-companion", timeout=120)
    from local_execution import test_environment
    environment = dict(PINKHA_SIMULATOR_UI_DISPOSABLE="1", PINKHA_MINIAPPS_NATIVE_TESTING="1",
                       PINKHA_MINIAPPS_NATIVE_GROUP=owner["native_app_group"],
                       PINKHA_MINIAPPS_SOURCE_BUNDLE=source_bundle, **test_environment(receipt))

    def test(configuration, target, method, name, additions=None):
        env = {**environment, **(additions or {})}
        configured = configure_tests(configuration, evidence / (name + ".xctestrun"), env, target, method)
        result_path = evidence / (name + ".xcresult")
        arguments = ["xcodebuild", "test-without-building", "-xctestrun", str(configured),
                     "-destination", "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO",
                     "-only-testing:" + target + "/" + selector(target, method)]
        enumeration_path = evidence / (name + "-enumeration.json")
        command([*arguments, "-enumerate-tests", "-test-enumeration-style", "flat",
                 "-test-enumeration-format", "json", "-test-enumeration-output-path", str(enumeration_path)],
                name + "-enumeration", timeout=120)
        receipt[name + "_selection"] = validate_enumeration(
            json.loads(enumeration_path.read_text()), target, method)
        save(name + "-selection-verified")
        try:
            command([*arguments, "-resultBundlePath", str(result_path)], name, timeout=600)
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
    require(fixture["sourceSHA"] == head and fixture["runID"] == receipt["run_id"], "Prepared native fixture differs")
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
    test(native_configuration, "AnytypeTests", ADAPTER, "native-adapter")
    adapter = json.loads((data_container() / "Library/Application Support/miniapps-native-adapter-readback.json").read_text())
    require(adapter["status"] == "NATIVE_MINIAPPS_ADAPTER_PASS" and adapter["sourceSHA"] == head
            and adapter["runID"] == receipt["run_id"] and adapter["producerRoundTrips"] == 0
            and adapter["preservedOutputCount"] == 1 and adapter["nativeAttachmentCount"] == 1,
            "Native selected-text/file adapter receipt differs")
    for key in ("replacementPreservedBlockID", "replacementPreservedTree", "nativeMarksPreserved",
                "replayPreservedNewerText", "conflictPreservedNewerText",
                "nativeAttachmentUploaded", "nativeAttachmentByteReadback", "nestedTableSelectionCaptured",
                "nestedTableReplacementPersisted", "expiredSelectionDidNotFallback"):
        require(adapter[key] is True, "Native adapter did not prove " + key)
    write(evidence / "native-adapter-readback.json", adapter)
    if getattr(args, "include_file_workshop", False):
        require(context.local, "The additional real-file lane requires its actual local identity")
        import file_acceptance
        staged = file_acceptance.stage(app, udid, source_bundle, evidence, receipt["run_id"])
        file_environment = dict(ui_env,
            PINKHA_MINIAPPS_SHARED_BRIDGE=staged["bridge"],
            PINKHA_MINIAPPS_FILE_ARCHIVE=staged["archive"],
            PINKHA_MINIAPPS_FILE_ARCHIVE_SHA256=staged["archive_sha256"],
            PINKHA_MINIAPPS_FILE_REPORT_NAME=staged["report_name"])
        test(ui_configuration, "PinkhaStage1AcceptanceUITests",
             file_acceptance.METHOD, "native-file-ui", file_environment)
        file_proof = file_acceptance.verify(staged, data_container(), fixture, source_bundle, evidence)
        receipt.update(additional_file_ui_methods=1, actual_file_companion_invocations=4,
                       native_file_roundtrip_status=file_proof["status"],
                       original_five_methods_passed=True)
    require(git(app, "rev-parse", "HEAD") == head, "Source changed during native acceptance")
    verify_recorded_resolution(app, evidence, context.derived, head, receipt["run_id"], receipt["run_attempt"],
                               activation_arguments=[] if context.local else None)
    verify_sdk(app / "Dependencies/Hanlin")
    receipt.update(status="MINIAPPS_TWO_APP_NATIVE_PASS", phase="COMPLETE",
                   actual_native_preparation=1, actual_ui_methods=2, actual_native_readback=1, actual_native_adapter=1,
                   actual_companion_invocations=2, warm_callback=True, cold_callback=True,
                   physical_sharing="NOT_PROVEN_BY_SIMULATOR")
    save("COMPLETE")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("app", "evidence", "derived"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--lane", choices=["hanlin-selection", "miniapps-native"], required=True)
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
