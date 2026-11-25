#!/usr/bin/env python3
"""Run one unchanged native UI journey in the source-qualified unified app.

No application/native/UI compilation is performed. The original complete main
and UI build receipts are mandatory. All mutable test descriptors, simulator
data and any finite Hanlin HTTPS fixture belong to this explicit invocation.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import ssl
import subprocess
import sys
import time
import traceback
import uuid

TARGET = "PinkhaAnyNativeUITests"
STAGES = {
    "drag": ("NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen", 600),
    "archive": ("NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies", 1800),
    "history": ("NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen", 600),
    "hanlin": ("NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen", 600),
    "custom-type": ("NativeLaunchTests/testCustomCanonicalTypeTransitionPreservesNativeDocumentAcrossColdReopen", 600),
    "bin": ("NativeLaunchTests/testNativeBinRestoreKeepsIdentityAndBodyAcrossColdReopen", 600),
}
FLOOR = 2 * 1024**3


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def inventory(base):
    rows = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            rows.append({"path": str(path.relative_to(base)), "kind": "symlink",
                         "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": str(path.relative_to(base)), "kind": "file",
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    return rows


def original_module(path, name):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, directory, label, *, timeout=120, environment=None, allow_failure=False, cleanup=False):
    require(not (directory / (label + ".command.json")).exists(), "unique_command_label_required")
    started = time.time()
    log = directory / (label + ".log")
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
               PYTHONDONTWRITEBYTECODE="1")
    if environment:
        env.update(environment)
    minimum = shutil.disk_usage(directory).free
    require(cleanup or minimum >= FLOOR, "owned_process_emergency_floor")
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=directory, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record = {"argv": argv, "pid": process.pid, "pgid": process.pid,
                  "started": started, "freeBytesBefore": minimum}
        write(directory / (label + ".command.json"), record)
        stopped = None
        while process.poll() is None:
            free = shutil.disk_usage(directory).free
            minimum = min(minimum, free)
            if free < FLOOR and not cleanup:
                stopped = "RESOURCE_DISK_FLOOR"
            elif time.time() - started > timeout:
                stopped = "TIMEOUT"
            if stopped:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                break
            time.sleep(1)
        code = process.wait()
    try:
        os.killpg(process.pid, 0)
        group = "STILL_PRESENT"
    except ProcessLookupError:
        group = "ABSENT_ESRCH"
    record.update(exitCode=code, elapsedSeconds=time.time() - started,
                  minimumFreeBytes=minimum, stopped=stopped, ownedProcessGroup=group,
                  logSHA256=digest(log), status="PASS" if code == 0 and not stopped and
                  group == "ABSENT_ESRCH" else "FAIL")
    write(directory / (label + ".result.json"), record)
    if not allow_failure:
        require(record["status"] == "PASS", "owned_command_failed:" + label)
    return record, log.read_bytes()


def bind(original, products, app, selector, runtime_root):
    require(set(original) == {TARGET, "__xctestrun_metadata__"}
            and original["__xctestrun_metadata__"]["FormatVersion"] == 1,
            "one_original_ui_target_required")
    target = original[TARGET]
    require(target["IsUITestBundle"] is True
            and target.get("UseUITargetAppProvidedByTests") is True
            and not target.get("SkipTestIdentifiers")
            and not target.get("OnlyTestIdentifiers")
            and not target.get("UITargetAppPath"), "unmodified_ui_only_descriptor_required")
    info = plistlib.loads((app / "Info.plist").read_bytes())
    require(info["CFBundleIdentifier"] == "io.anytype.app",
            "source_qualified_debug_application_identifier_required")
    value = copy.deepcopy(original)
    changed = value[TARGET]
    changed.pop("UseUITargetAppProvidedByTests")
    changed["UITargetAppPath"] = str(app)
    changed["UITargetAppBundleIdentifier"] = info["CFBundleIdentifier"]
    changed["OnlyTestIdentifiers"] = [selector]
    changed["DependentProductPaths"] = [str(app), *target["DependentProductPaths"]]
    changed["EnvironmentVariables"]["PINKHA_NATIVE_UI_UNIFIED_HOST"] = "1"
    changed["SystemAttachmentLifetime"] = "keepAlways"
    changed["UserAttachmentLifetime"] = "keepAlways"
    injections = {}
    for key in ("EnvironmentVariables", "TestingEnvironmentVariables",
                "UITargetAppEnvironmentVariables"):
        env = changed.get(key, {})
        if "DYLD_INSERT_LIBRARIES" in env:
            old = env["DYLD_INSERT_LIBRARIES"]
            parts = old.split(":")
            rewritten = []
            for part in parts:
                if part.endswith("/libMainThreadChecker.dylib"):
                    actual = runtime_root / "usr/lib/libMainThreadChecker.dylib"
                    require(actual.is_file(), "actual_runtime_main_thread_checker_required")
                    rewritten.append(str(actual))
                else:
                    rewritten.append(part)
            env["DYLD_INSERT_LIBRARIES"] = ":".join(rewritten)
            if old != env["DYLD_INSERT_LIBRARIES"]:
                injections[key] = {"before": old, "after": env["DYLD_INSERT_LIBRARIES"]}
    # The only descriptor changes are explicit app/selection/environment binding.
    inverse = copy.deepcopy(value)
    for key in ("UseUITargetAppProvidedByTests", "UITargetAppPath", "UITargetAppBundleIdentifier",
                "OnlyTestIdentifiers", "DependentProductPaths", "EnvironmentVariables",
                "TestingEnvironmentVariables", "UITargetAppEnvironmentVariables",
                "SystemAttachmentLifetime", "UserAttachmentLifetime"):
        if key in target:
            inverse[TARGET][key] = copy.deepcopy(target[key])
        else:
            inverse[TARGET].pop(key, None)
    require(inverse == original, "unexpected_test_descriptor_delta")

    def absolute_paths(item):
        if isinstance(item, str):
            return item.replace("__TESTROOT__", str(products))
        if isinstance(item, list):
            return [absolute_paths(x) for x in item]
        if isinstance(item, dict):
            return {k: absolute_paths(v) for k, v in item.items()}
        return item
    value = absolute_paths(value)
    return value, {"exactOriginalInverse": True, "runtimeInjection": injections,
                   "application": str(app), "bundleIdentifier": info["CFBundleIdentifier"],
                   "selector": TARGET + "/" + selector, "realVisibleEngineSelection": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path, required=True)
    parser.add_argument("--ui-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    args = parser.parse_args()
    for path in (args.main_root, args.main_evidence, args.ui_build, args.output):
        require(path.is_absolute() and path.resolve() == path, "canonical_absolute_path_required")
    require(all(args.main_root in p.parents for p in
                (args.main_evidence, args.ui_build, args.output)), "owned_workspace_required")
    require(not args.output.exists(), "refuse_existing_execution_output")
    args.output.mkdir(mode=0o700)
    os.umask(0o077)
    out = args.output
    source = args.main_root / "source"
    receipt = {"status": "FAIL", "stage": args.stage, "applicationBuilds": 0,
               "nativeLibraryBuilds": 0, "uiRunnerBuilds": 0, "testsExecuted": 0}
    udid = None
    fixture_config = None
    products = None
    app = None
    app_original = None
    original_app_inventory = None
    copied_ui_inventory = None
    first_error = None
    cleanup_errors = []
    try:
        main_record = json.loads((args.main_evidence / "receipt.json").read_bytes())
        ui_record = json.loads((args.ui_build / "receipt.json").read_bytes())
        require(main_record["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                and main_record["sourceUnchanged"] is True and main_record["testsExecuted"] == 0,
                "complete_original_main_build_required")
        require(ui_record["status"] == "PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE"
                and ui_record["sourceCommit"] == main_record["sourceCommit"]
                and ui_record["testsExecuted"] == 0
                and ui_record.get("mainReceiptSHA256") == digest(args.main_evidence / "receipt.json"),
                "same_source_exact_main_receipt_ui_runner_build_required")
        before = json.loads((args.main_evidence / "source-before.json").read_bytes())
        require(before == json.loads((args.main_evidence / "source-after.json").read_bytes()),
                "unchanged_built_source_required")
        source_head = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                                     capture_output=True, text=True, check=True).stdout.strip()
        require(source_head == before["commit"], "frozen_checkout_required")
        for name, row in before["files"].items():
            require(digest(source / name) == row["sha256"], "source_changed:" + name)
        all_products = args.main_evidence / "products-all.json"
        require(digest(all_products) == main_record["completeProductsInventory"]["sha256"],
                "original_product_inventory_changed")
        original_products = json.loads(all_products.read_bytes())["app-derived"]
        app_original = Path(original_products["base"]) / "Debug-Anytype-iphonesimulator/Anytype.app"
        prefix = "Debug-Anytype-iphonesimulator/Anytype.app/"
        original_app_inventory = []
        for row in original_products["entries"]:
            if row["path"].startswith(prefix):
                original_app_inventory.append(dict(row, path=row["path"][len(prefix):]))
        require(original_app_inventory and inventory(app_original) == original_app_inventory,
                "built_main_application_changed")
        ui_products = args.ui_build / "derived/Build/Products"
        templates = list(ui_products.glob("*.xctestrun"))
        require(len(templates) == 1, "one_original_native_ui_descriptor_required")
        product_record = args.ui_build / "products-all.json"
        require(digest(product_record) == ui_record["completeProductsInventory"]["sha256"],
                "native_ui_build_product_record_changed")
        ui_inventory = json.loads(product_record.read_bytes())
        require(ui_inventory and inventory(ui_products) == ui_inventory,
                "original_native_ui_products_changed")
        products = out / "ui-products"
        run(["cp", "-cR", str(ui_products), str(products)], out, "clone-ui-products")
        require(inventory(products) == ui_inventory, "ui_product_clone_mismatch")
        copied_ui_inventory = ui_inventory
        app = out / "Anytype.app"
        run(["cp", "-cR", str(app_original), str(app)], out, "clone-unified-app")
        require(inventory(app) == original_app_inventory, "app_clone_mismatch")
        receipt.update(sourceCommit=source_head,
                       mainReceiptSHA256=digest(args.main_evidence / "receipt.json"),
                       runnerReceiptSHA256=digest(args.ui_build / "receipt.json"),
                       originalAppFileCount=len(original_app_inventory))
        _, raw = run(["xcrun", "simctl", "list", "runtimes", "--json"], out, "runtimes")
        runtimes = [x for x in json.loads(raw)["runtimes"] if
                    x.get("isAvailable") is True and x.get("version") == "27.0"
                    and "iOS" in x.get("name", "")]
        require(len(runtimes) == 1, "one_available_original_ios27_runtime_required")
        _, raw = run(["xcrun", "simctl", "list", "devicetypes", "--json"], out, "device-types")
        types = [x for x in json.loads(raw)["devicetypes"] if
                 x.get("identifier") == "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB"]
        require(len(types) == 1, "one_available_ipad_pro_m5_device_type_required")
        runtime = runtimes[0]
        name = "PinkhaUnifiedD-" + args.stage + "-" + str(uuid.uuid4())
        _, raw = run(["xcrun", "simctl", "create", name, types[0]["identifier"],
                      runtime["identifier"]], out, "create-simulator")
        udid = str(uuid.UUID(raw.decode().strip())).upper()
        write(out / "simulator.json", {"ownedUDID": udid, "name": name,
              "runtime": runtime["identifier"], "deviceType": types[0]["identifier"]})
        run(["xcrun", "simctl", "boot", udid], out, "boot-simulator")
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], out, "bootstatus", timeout=180)
        _, raw = run(["xcrun", "simctl", "getenv", udid, "SIMULATOR_ROOT"],
                     out, "simulator-runtime-root")
        runtime_root = Path(raw.decode().strip())
        require(runtime_root.is_dir(), "observed_runtime_root_required")
        run(["xcrun", "simctl", "install", udid, str(app)], out, "install-unified-app", timeout=120)
        selector, allowance = STAGES[args.stage]
        original_template = plistlib.loads(templates[0].read_bytes())
        configured, binding = bind(original_template, products, app, selector, runtime_root)
        fixture_environment = {}
        if args.stage == "hanlin":
            private = out / "private-provider"
            private.mkdir(mode=0o700)
            fixture = source / "Tools/AnyEngineValidation/HanlinProviderFixture/fixture.py"
            fixture_config = private / "private-config.json"
            run([sys.executable, "-B", str(fixture), "start", "--private-dir", str(private),
                 "--safe-result", str(out / "provider-start.json")], out, "start-provider", timeout=90)
            fixture_config = private / "private-config.json"
            conf = json.loads(fixture_config.read_bytes())
            ca = private / "root-ca.pem"
            require(hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca.read_text())).hexdigest()
                    == conf["rootCAFingerprintSHA256"], "original_fixture_ca_mismatch")
            fixture_environment = conf["testRunnerEnvironment"]
            expected_keys = {"TEST_RUNNER_PINKHA_HANLIN_FIXTURE_" + suffix for suffix in
                             ("URL", "MODEL", "KEY", "CONTROL_URL", "CONTROL_TOKEN")}
            require(set(fixture_environment) == expected_keys, "exact_fixture_environment_required")
            run(["xcrun", "simctl", "keychain", udid, "add-root-cert", str(ca)],
                out, "owned-simulator-fixture-trust")
        descriptor = out / "Selected.xctestrun"
        descriptor.write_bytes(plistlib.dumps(configured, sort_keys=False))
        descriptor.chmod(0o600)
        binding.update(originalSHA256=digest(templates[0]), copiedSHA256=digest(descriptor),
                       originalMainReceiptSHA256=receipt["mainReceiptSHA256"])
        write(out / "descriptor-binding.json", binding)
        plan = ["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
                "-destination", "platform=iOS Simulator,id=" + udid,
                "-parallel-testing-enabled", "NO", "-test-timeouts-enabled", "YES",
                "-default-test-execution-time-allowance", str(allowance),
                "-maximum-test-execution-time-allowance", str(allowance),
                "-only-testing:" + TARGET + "/" + selector,
                "-collect-test-diagnostics", "never",
                "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGN_IDENTITY=-",
                "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES"]
        enumeration = out / "enumeration.json"
        run(plan + ["-enumerate-tests", "-test-enumeration-style", "flat",
                    "-test-enumeration-format", "json", "-test-enumeration-output-path",
                    str(enumeration)], out, "enumerate", timeout=180,
                    environment=fixture_environment)
        contract = original_module(source / "Tools/AnyEnginePort/native_ui_transition_contract.py",
                                   "original_native_ui_selection")
        label, enabled, disabled = contract.enumerated_identifiers(
            json.loads(enumeration.read_bytes()))
        require(enabled == {TARGET + "/" + selector + "()"}, "exact_compiled_method_not_selected")
        require(digest(descriptor) == binding["copiedSHA256"], "descriptor_changed_after_enumeration")
        record, _ = run(plan + ["-resultBundlePath", str(out / "Original.xcresult")],
                        out, "execute", timeout=allowance + 300,
                        environment=fixture_environment, allow_failure=True)
        receipt["testCommand"] = record
        require(record["status"] == "PASS", "actual_original_ui_execution_failed")
        if args.stage == "hanlin":
            run([sys.executable, "-B", str(fixture), "verify", "--private-config",
                 str(fixture_config), "--safe-result", str(out / "provider-contract.json")],
                out, "verify-provider", timeout=60)
    except BaseException as exc:
        first_error = {"type": type(exc).__name__, "reason": str(exc)}
        write(out / "first-failure.json", {**first_error, "traceback": traceback.format_exc()})
    finally:
        # Only the original xcresult may establish completed test counts.
        # A terminated xcodebuild can leave an incomplete result bundle.
        issued = (out / "execute.command.json").is_file()
        receipt["testCommandIssued"] = issued
        receipt["testsExecuted"] = None if issued else 0
        receipt["testResultAvailability"] = "UNAVAILABLE" if issued else "NOT_STARTED"
        result_path = out / "Original.xcresult"
        if result_path.is_dir():
            try:
                values = {}
                for kind in ("summary", "tests"):
                    _, raw = run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                  "--path", str(result_path), "--format", "json"],
                                 out, "original-" + kind, timeout=120, cleanup=True)
                    values[kind] = json.loads(raw)
                    write(out / (kind + ".json"), values[kind])
                parser_module = original_module(
                    source / "Tools/AnyEnginePort/verify_native_test_execution.py",
                    "original_native_ui_results")
                cases = parser_module.test_cases(values["tests"])
                counts = {k: values["summary"].get(k) for k in
                          ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
                receipt.update(counts=counts, actualCases=cases,
                               testsExecuted=counts.get("totalTestCount"),
                               testResultAvailability="ORIGINAL_XCRESULT")
                selector = STAGES[args.stage][0]
                require(counts == {"totalTestCount": 1, "passedTests": 1,
                                   "failedTests": 0, "skippedTests": 0}
                        and len(cases) == 1 and all(x == "Passed" for x in cases.values())
                        and any(re.search(r"(?:^|/)" + re.escape(selector) + r"(?:\(|/|$)", x)
                                for x in cases), "exact_original_method_did_not_pass")
                devices = values["summary"]["devicesAndConfigurations"]
                require(len(devices) == 1
                        and devices[0]["device"]["deviceId"].upper() == udid
                        and devices[0]["device"]["architecture"] == "arm64",
                        "original_result_destination_mismatch")
            except BaseException as exc:
                cleanup_errors.append({"phase": "original-results", "reason": str(exc)})
        if fixture_config is not None and fixture_config.is_file():
            try:
                run([sys.executable, "-B", str(source / "Tools/AnyEngineValidation/"
                     "HanlinProviderFixture/fixture.py"), "stop", "--private-config",
                     str(fixture_config)], out, "stop-provider", timeout=60, cleanup=True)
            except BaseException as exc:
                cleanup_errors.append({"phase": "provider-stop", "reason": str(exc)})
        if udid is not None:
            sandbox = None
            try:
                _, raw = run(["xcrun", "simctl", "get_app_container", udid,
                              "io.anytype.app", "data"], out, "native-sandbox-path",
                             cleanup=True)
                sandbox = Path(raw.decode().strip())
                require(sandbox.is_absolute() and sandbox.resolve() == sandbox
                        and udid in sandbox.parts and sandbox.is_dir(),
                        "owned_native_sandbox_path_required")
            except BaseException as exc:
                cleanup_errors.append({"phase": "private-native-sandbox", "reason": str(exc)})
            try:
                run(["xcrun", "simctl", "shutdown", udid], out, "shutdown-simulator",
                    timeout=60, cleanup=True)
                if sandbox is not None:
                    retained = out / "private-native-sandbox"
                    run(["cp", "-cR", str(sandbox), str(retained)], out,
                        "retain-native-sandbox", timeout=120, cleanup=True)
                    retained.chmod(0o700)
                    write(out / "private-native-sandbox-retention.json",
                          {"original": str(sandbox), "retained": str(retained),
                           "sourceSimulator": udid, "containsPrivateNativeAccountData": True})
            except BaseException as exc:
                cleanup_errors.append({"phase": "native-sandbox-retention", "reason": str(exc)})
            for label, command in (("delete-simulator", ["xcrun", "simctl", "delete", udid]),):
                try:
                    run(command, out, label, timeout=60, cleanup=True)
                except BaseException as exc:
                    cleanup_errors.append({"phase": label, "reason": str(exc)})
            try:
                _, raw = run(["xcrun", "simctl", "list", "devices", "--json"],
                             out, "final-devices", cleanup=True)
                require(not any(d["udid"].upper() == udid for group in
                        json.loads(raw)["devices"].values() for d in group),
                        "owned_simulator_still_exists")
            except BaseException as exc:
                cleanup_errors.append({"phase": "device-absence", "reason": str(exc)})
        try:
            if app_original is not None and original_app_inventory is not None:
                require(inventory(app_original) == original_app_inventory,
                        "original_main_products_changed")
            if app is not None and original_app_inventory is not None:
                require(inventory(app) == original_app_inventory, "copied_main_products_changed")
            if products is not None and copied_ui_inventory is not None:
                require(inventory(products) == copied_ui_inventory, "copied_ui_products_changed")
            write(out / "products-after.json", {
                "originalAppUnchanged": app_original is not None,
                "copiedAppUnchanged": app is not None,
                "copiedUIUnchanged": products is not None,
                "privateNativeSandboxRetained": (out / "private-native-sandbox").is_dir()})
        except BaseException as exc:
            cleanup_errors.append({"phase": "product-integrity", "reason": str(exc)})
        receipt.update(firstFailure=first_error, diagnosticFailures=cleanup_errors,
                       ownedSimulator=udid, finished=time.time())
        receipt["status"] = "PASS" if first_error is None and not cleanup_errors and \
            receipt.get("counts", {}).get("passedTests") == 1 else "FAIL"
        write(out / "receipt.json", receipt)
    require(receipt["status"] == "PASS", "scoped_unified_native_ui_acceptance_failed")


if __name__ == "__main__":
    main()
