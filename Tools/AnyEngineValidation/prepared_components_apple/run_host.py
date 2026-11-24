#!/usr/bin/env python3
"""One actual managed C-runtime/Swift full-file journey on the owned Mac."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from uuid import uuid4
import cleanup
import contract
import descriptor
import execution
import proof


def installed_fingerprints(control, artifact):
    receipt = json.loads((artifact / "native-artifact.json").read_bytes())
    vendor = control / "Modules/PinkhaAnyRuntime/Vendor"
    actual = {name: contract.digest(vendor / name) for name in receipt["files_sha256"]}
    contract.require(actual == receipt["files_sha256"], "Installed native slice/header changed")
    return actual


def collect_result(run, evidence, result, receipt, *, tolerant):
    if not result.is_dir():
        receipt["result_bundle_present"] = False
        return None
    receipt["result_bundle_present"] = True
    values = {}
    commands = [("summary", ["xcrun", "xcresulttool", "get", "test-results", "summary", "--path", str(result)]),
                ("tests", ["xcrun", "xcresulttool", "get", "test-results", "tests", "--path", str(result)]),
                ("attachments", ["xcrun", "xcresulttool", "export", "attachments", "--path", str(result),
                                 "--output-path", str(evidence / "attachments")])]
    for name, argv in commands:
        if "xcresult-" + name in {entry["name"] for entry in receipt["commands"]}:
            continue
        try:
            path = run(argv, "xcresult-" + name, timeout=90)
            if name != "attachments":
                values[name] = execution.command_json(path)
        except BaseException as error:
            receipt.setdefault("result_export_failures", {})[name] = dict(error_type=type(error).__name__, error=str(error))
            if not tolerant:
                raise
    return values


def selected_attachment(evidence):
    candidates = []
    for path in (evidence / "attachments").rglob("*"):
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
            continue
        try:
            value = json.loads(path.read_bytes())
        except (UnicodeError, ValueError):
            continue
        if (isinstance(value, dict) and value.get("schema") == "pinkha-prepared-components-apple-v1"
                and value.get("status") == "OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED"):
            candidates.append((path, value))
    contract.require(len(candidates) == 1, "Exactly one bounded original prepared-migration attachment required")
    return candidates[0]


def run_simulator(control, work, evidence, receipt, run, environment, package, scheme, cache):
    inventory = execution.command_json(run(["xcrun", "simctl", "list", "runtimes", "-j"], "runtimes", timeout=30))
    devices = execution.command_json(run(["xcrun", "simctl", "list", "devicetypes", "-j"], "device-types", timeout=30))
    selector = contract.load_module(control / "Tools/PinkhaSimulatorGate/simulator_selection.py", "prepared_simulator_selection")
    pair = selector.choose_pair(inventory, devices, product_family="iPad", major=27, architecture="arm64")
    receipt["simulator_selection"] = pair["selection"]
    identifier = run(["xcrun", "simctl", "create", "PreparedComponents-" + uuid4().hex,
                      pair["device"]["identifier"], pair["runtime"]["identifier"]], "create-owned-simulator", timeout=60)
    udid = identifier.read_text().strip()
    contract.require(proof.uuid(udid), "Invalid newly owned simulator identifier")
    receipt["owned_simulator"] = dict(udid=udid, runtime=pair["runtime"]["identifier"], type=pair["device"]["identifier"])
    contract.save(evidence / "receipt.json", receipt)
    result = evidence / "prepared-components.xcresult"
    products = work / "DerivedData/Build/Products"
    products_before = None
    bound_audit = None
    try:
        run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator", timeout=90)
        test = ["xcodebuild", "test-without-building", "-scheme", scheme, "-configuration", "Debug",
                "-destination", "platform=iOS Simulator,id=" + udid, "-derivedDataPath", str(work / "DerivedData"),
                *cache, "-disableAutomaticPackageResolution", "-parallel-testing-enabled", "NO", "-jobs", "2",
                "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "900",
                "-maximum-test-execution-time-allowance", "900", "-resultBundlePath", str(result),
                "-only-testing:" + contract.SELECTOR]
        build = list(test)
        build[1] = "build-for-testing"
        build[build.index("-resultBundlePath") + 1] = str(evidence / "prepared-components-build.xcresult")
        # One required build overlaps cold boot. Readiness is checked afterward
        # and is never inferred from build completion or stale simulator state.
        run(build, "ios-build-for-testing", cwd=package, env=environment, timeout=1800)
        receipt["harness_build"] = dict(status="BUILT_CURRENT_PACKAGE_NOT_EXECUTED", tests_executed=0)
        bound, bound_audit = descriptor.bind_generated(products, evidence, receipt["acceptance_binding"])
        receipt["owned_descriptor"] = bound_audit
        products_before = descriptor.product_inventory(products)
        contract.save(evidence / "compiled-products-before.json", products_before)
        run(["xcrun", "simctl", "bootstatus", udid, "-b"], "wait-owned-simulator", timeout=180)
        exact_test = ["xcodebuild", "test-without-building", "-xctestrun", str(bound),
                      "-destination", "platform=iOS Simulator,id=" + udid,
                      "-parallel-testing-enabled", "NO", "-jobs", "2",
                      "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "900",
                      "-maximum-test-execution-time-allowance", "900", "-resultBundlePath", str(result),
                      "-only-testing:" + contract.SELECTOR]
        run(exact_test, "ios-test-without-building", cwd=package, env=environment, timeout=1500)
        exports = collect_result(run, evidence, result, receipt, tolerant=False)
        verifier = contract.load_module(control / "Tools/AnyEnginePort/verify_native_test_execution.py", "prepared_xcresult_cases")
        receipt["actual_execution"] = proof.exact_execution(exports["summary"], exports["tests"], udid, verifier.test_cases)
        path, value = selected_attachment(evidence)
        receipt["qualified_observations"] = proof.observation(value, receipt["acceptance_binding"])
        receipt["actual_attachment_sha256"] = contract.digest(path)
        shutil.copyfile(path, evidence / "actual-prepared-components-proof.json")
    except BaseException as error:
        receipt["primary_failure"] = dict(error_type=type(error).__name__, error=str(error))
        contract.save(evidence / "receipt.json", receipt)
        collect_result(run, evidence, result, receipt, tolerant=True)
        diagnostics = [(["xcrun", "simctl", "list", "devices", "-j"], "owned-simulator-failure-state", 15),
                       (["/usr/bin/log", "show", "--last", "5m", "--style", "compact", "--predicate",
                         'subsystem BEGINSWITH "com.apple.CoreSimulator" AND eventMessage CONTAINS "' + udid + '"'],
                        "owned-simulator-failure-system-log", 20)]
        for argv, name, timeout in diagnostics:
            try:
                run(argv, name, timeout=timeout)
            except BaseException as diagnostic_error:
                receipt.setdefault("diagnostic_failures", {})[name] = dict(error_type=type(diagnostic_error).__name__, error=str(diagnostic_error))
        raise
    finally:
        if products_before is not None and bound_audit is not None:
            try:
                products_after = descriptor.product_inventory(products)
                contract.save(evidence / "compiled-products-after.json", products_after)
                contract.require(products_after == products_before
                                 and contract.digest(Path(bound_audit["source_descriptor"])) == bound_audit["source_descriptor_sha256"]
                                 and contract.digest(Path(bound_audit["bound_descriptor"])) == bound_audit["bound_descriptor_sha256"],
                                 "Executed Swift products or exact bound XCTest descriptor changed")
                receipt["compiled_products_unchanged"] = True
            except BaseException as product_error:
                receipt["compiled_products_unchanged"] = False
                receipt["compiled_product_verification_failure"] = dict(
                    error_type=type(product_error).__name__, error=str(product_error))
        cleanup.cleanup_owned_simulator(run, receipt, udid)


def execute(args, receipt, run):
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                     "Actual Apple ARM64 runtime consumer required")
    contract.clean_source(args.control, args.expected_app_sha)
    native, manifest = contract.candidate(args.control)
    receipt["selected_source"] = contract.selected_source(args.control)
    receipt["acceptance_binding"] = dict(sourceSHA=args.expected_app_sha,
                                        executionUUID=args.execution_uuid, nonce=uuid4().hex)
    descriptor.validate_binding(receipt["acceptance_binding"])
    before = contract.snapshot(args.control)
    contract.save(args.evidence / "control-source-before.json", before)
    primary = None
    try:
        contract.require(not args.work.exists(), "Preserve previous owned consumer work and products")
        args.work.mkdir(parents=True)
        producer = args.native_producer_commit or args.expected_app_sha
        artifact = native.validate_artifact(args.control, args.artifact, producer)
        receipt_sha = contract.digest(args.artifact / "native-artifact.json")
        archive_sha = contract.digest(args.artifact / "any.xcframework.zip")
        receipt["producer"] = dict(execution_kind=artifact["execution_kind"],
                                   execution_uuid=artifact["execution_uuid"], source_sha=producer)
        native.install(args.control, args.artifact, producer)
        native_files = installed_fingerprints(args.control, args.artifact)
        shutil.copyfile(args.artifact / "native-artifact.json", args.evidence / "original-native-artifact.json")
        shutil.copyfile(args.control / "Modules/PinkhaAnyRuntime/Vendor/consumer-binding.json",
                        args.evidence / "native-consumer-binding.json")
        receipt.update(native_artifact_receipt_sha256=receipt_sha, archive_sha256=archive_sha,
                       manifest_sha256=contract.MANIFEST_SHA, version=contract.VERSION,
                       native_tests_executed=0, retained_swift_tests_executed=0)
        environment = os.environ.copy()
        contract.require(not environment.get("PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE"),
                         "Separate acceptance candidate required")
        environment["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-prepared-components-v1"
        package = args.control / "Modules/PinkhaAnyRuntime"
        cache = ["-clonedSourcePackagesDirPath", str(args.work / "SourcePackages")]
        run(["xcodebuild", "-version"], "xcode-version", timeout=30)
        schemes = execution.command_json(run(["xcodebuild", "-list", "-json", *cache], "schemes",
                                              cwd=package, env=environment, timeout=300))
        available = schemes.get("workspace", schemes.get("project", {})).get("schemes", [])
        selected = [name for name in (contract.PACKAGE, contract.PACKAGE + "-Package") if name in available]
        contract.require(selected, "Actual full-file runtime package scheme missing")
        scheme = selected[0]
        run(["xcodebuild", "-resolvePackageDependencies", "-scheme", scheme, *cache],
            "resolve-packages", cwd=package, env=environment, timeout=600)
        pins = contract.resolved_pins(package)
        dependencies = contract.dependency_checkouts(args.work)
        receipt["resolved_packages"] = pins
        receipt["actual_dependency_sources"] = dependencies
        run_simulator(args.control, args.work, args.evidence, receipt, run, environment, package, scheme, cache)
        contract.require(contract.resolved_pins(package) == pins
                         and contract.dependency_checkouts(args.work) == dependencies
                         and installed_fingerprints(args.control, args.artifact) == native_files
                         and contract.digest(args.artifact / "native-artifact.json") == receipt_sha
                         and contract.digest(args.artifact / "any.xcframework.zip") == archive_sha,
                         "Actual native binary or dependencies changed during XCTest")
        contract.require(receipt.get("compiled_products_unchanged") is True,
                         "Compiled XCTest product identity is unverified")
        contract.require(receipt.get("owned_simulator_cleanup_status") == "COMPLETE",
                         "Owned simulator cleanup incomplete")
    except BaseException as error:
        primary = error
        raise
    finally:
        contract.source_after(args.control, before, args.evidence, receipt, primary)
    receipt.update(status=contract.PASS, full_migration_accepted=False, file_capability=0,
                   prepared_file_capability=1, minimum_bytes=4096, maximum_bytes=512 << 20,
                   network_verified=False,
                   runtime_reopen_scope="orderly SDK/store reopen in one XCTest OS process")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "artifact", "work", "evidence"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    parser.add_argument("--execution-uuid", required=True)
    parser.add_argument("--native-producer-commit", default="")
    args = parser.parse_args()
    for name in ("control", "artifact", "work", "evidence"):
        setattr(args, name, getattr(args, name).resolve())
    return execution.run_stage(args, execute)


if __name__ == "__main__":
    raise SystemExit(main())
