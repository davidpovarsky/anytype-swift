#!/usr/bin/env python3
"""Install an exact native producer and execute one actual prepared-migration XCTest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from uuid import uuid4

import contract
import cleanup
import descriptor
import execution
import proof


def validate_producer(build, artifact, observed, jobs, run_id, attempt, commit):
    contract.require(build.get("status") == contract.BUILD_PASS and build.get("app_sha") == commit
                     and str(build.get("run_id")) == run_id and str(build.get("run_attempt")) == attempt
                     and build.get("version") == contract.VERSION and build.get("manifest_sha256") == contract.MANIFEST_SHA
                     and build.get("source_unchanged") is True, "Original native producer did not complete exact source verification")
    contract.require(all(type(build.get(k)) is int and build[k] == 0 for k in ("native_tests_executed", "apple_tests_executed")),
                     "Native build evidence must not relabel product tests")
    contract.require(build.get("artifact_name") == contract.artifact_name(run_id, attempt, commit), "Original producer artifact identity differs")
    contract.require(artifact.get("schemaVersion") == 1 and artifact.get("version") == contract.VERSION
                     and artifact.get("sourceCommit") == commit and artifact.get("sourceManifestSHA256") == contract.MANIFEST_SHA
                     and artifact.get("archive") == "any.xcframework.zip"
                     and artifact.get("archiveSHA256") == build.get("archive_sha256"), "Native archive receipt differs from its producer")
    contract.require(type(observed.get("id")) is int and str(observed["id"]) == run_id
                     and type(observed.get("run_attempt")) is int and str(observed["run_attempt"]) == attempt
                     and observed.get("head_sha") == commit and observed.get("event") == "workflow_dispatch"
                     and observed.get("path") in (contract.WORKFLOW, ".github/workflows/torah-inspector-ipados27.yml")
                     and observed.get("repository", {}).get("full_name") == contract.REPOSITORY
                     and observed.get("head_repository", {}).get("full_name") == contract.REPOSITORY,
                     "Original producer API source/attempt/workflow differs")
    # Overall run failure is allowed when the separate consumer failed. The
    # producer job and its immutable native artifact must independently pass.
    selected = [job for job in jobs if job.get("name") == contract.PRODUCER_JOB
                or str(job.get("name", "")).endswith(" / " + contract.PRODUCER_JOB)]
    contract.require(len(selected) == 1 and selected[0].get("status") == "completed"
                     and selected[0].get("conclusion") == "success"
                     and str(selected[0].get("run_id")) == run_id
                     and str(selected[0].get("run_attempt")) == attempt
                     and selected[0].get("head_sha") == commit, "Native producer job did not independently pass this exact attempt")
    commands = build.get("commands", [])
    expected = ["xcode-version", "device-sdk-version", "simulator-sdk-version", "go-version",
                "apply-exact-native-candidate", "native-build-both-slices", "record-exact-native-artifact"]
    contract.require(isinstance(commands, list) and [c.get("name") for c in commands] == expected
                     and all(c.get("status") == "PASS_EXIT_0" and type(c.get("pid")) is int and c["pid"] > 0 for c in commands),
                     "Incomplete native producer command evidence")
    return dict(run_id=run_id, run_attempt=attempt, source_commit=commit,
                original_run_status=observed.get("status"), original_run_conclusion=observed.get("conclusion"),
                producer_job_id=selected[0].get("id"), producer_job_conclusion="success",
                test_results_relabelled=False)


def producer_api(run, run_id, attempt):
    prefix = "repos/" + contract.REPOSITORY + "/actions/runs/" + run_id + "/attempts/" + attempt
    observed = execution.command_json(run(["gh", "api", prefix], "original-producer-run", timeout=45))
    jobs = []
    for page in range(1, 11):
        value = execution.command_json(run(["gh", "api", prefix + "/jobs?per_page=100&page=" + str(page)],
                                           "original-producer-jobs-" + str(page), timeout=45))
        contract.require(type(value.get("total_count")) is int and 0 < value["total_count"] <= 1000
                         and isinstance(value.get("jobs"), list), "Unexpected original producer job inventory")
        jobs.extend(value["jobs"])
        if len(jobs) >= value["total_count"]:
            contract.require(len(jobs) == value["total_count"] and len({j.get("id") for j in jobs}) == len(jobs),
                             "Duplicate or incomplete original producer job inventory")
            return observed, jobs
    raise ValueError("Original producer job inventory exceeded its bound")


def installed_fingerprints(control, artifact, native):
    vendor = control / "Modules/PinkhaAnyRuntime/Vendor"
    result = {}
    for path, expected in artifact["filesSHA256"].items():
        relative = native.safe_relative(path)
        result[str(relative)] = contract.digest(vendor / relative)
        contract.require(result[str(relative)] == expected, "Installed native framework differs")
    actual = {str(p.relative_to(vendor)) for p in (vendor / "any.xcframework").rglob("*") if p.is_file()}
    contract.require(actual == set(result), "Unexpected or missing installed framework member")
    return result


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
        if (isinstance(value, dict) and value.get("schema") == "pinkha-prepared-inline-file-apple-v1"
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
    identifier = run(["xcrun", "simctl", "create", "PreparedInlineFile-" + uuid4().hex,
                      pair["device"]["identifier"], pair["runtime"]["identifier"]], "create-owned-simulator", timeout=60)
    udid = identifier.read_text().strip()
    contract.require(proof.uuid(udid), "Invalid newly owned simulator identifier")
    receipt["owned_simulator"] = dict(udid=udid, runtime=pair["runtime"]["identifier"], type=pair["device"]["identifier"])
    contract.save(evidence / "receipt.json", receipt)
    result = evidence / "prepared-inline-file.xcresult"
    products = work / "DerivedData/Build/Products"
    products_before = None
    bound_audit = None
    try:
        run(["xcrun", "simctl", "boot", udid], "boot-owned-simulator", timeout=90)
        test = ["xcodebuild", "test-without-building", "-scheme", scheme, "-configuration", "Debug",
                "-destination", "platform=iOS Simulator,id=" + udid, "-derivedDataPath", str(work / "DerivedData"),
                *cache, "-disableAutomaticPackageResolution", "-parallel-testing-enabled", "NO", "-jobs", "4",
                "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "900",
                "-maximum-test-execution-time-allowance", "900", "-resultBundlePath", str(result),
                "-only-testing:" + contract.SELECTOR]
        build = list(test)
        build[1] = "build-for-testing"
        build[build.index("-resultBundlePath") + 1] = str(evidence / "prepared-inline-file-build.xcresult")
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
                      "-parallel-testing-enabled", "NO", "-jobs", "4",
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
        shutil.copyfile(path, evidence / "actual-prepared-inline-file-proof.json")
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
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Actual Xcode ARM64 consumer required")
    contract.clean_source(args.control, args.expected_app_sha)
    native, manifest = contract.candidate(args.control)
    receipt["selected_source"] = contract.selected_source(args.control)
    receipt["acceptance_binding"] = dict(sourceSHA=args.expected_app_sha, runID=str(receipt["run_id"]),
                                        runAttempt=str(receipt["run_attempt"]), nonce=uuid4().hex)
    descriptor.validate_binding(receipt["acceptance_binding"])
    before = contract.snapshot(args.control)
    contract.save(args.evidence / "control-source-before.json", before)
    primary = None
    try:
        contract.require(not args.work.exists(), "Fresh owned consumer work directory required")
        args.work.mkdir(parents=True)
        reused = contract.reuse_inputs(args.native_artifact_run_id, args.native_artifact_run_attempt, args.native_producer_commit)
        producer_run = args.native_artifact_run_id if reused else receipt["run_id"]
        producer_attempt = args.native_artifact_run_attempt if reused else receipt["run_attempt"]
        producer_commit = args.native_producer_commit if reused else args.expected_app_sha
        build = json.loads((args.artifact / "native-build.json").read_bytes())
        artifact = json.loads((args.artifact / "native-artifact.json").read_bytes())
        receipt_sha = contract.digest(args.artifact / "native-artifact.json")
        archive_sha = contract.digest(args.artifact / "any.xcframework.zip")
        contract.require(build.get("native_artifact_receipt_sha256") == receipt_sha
                         and build.get("archive_sha256") == archive_sha, "Downloaded native artifact changed")
        observed, jobs = producer_api(run, producer_run, producer_attempt)
        receipt["producer"] = validate_producer(build, artifact, observed, jobs, producer_run, producer_attempt, producer_commit)
        # Match producer-recorded source to its immutable Git commit. The
        # existing helper separately requires ancestry and unchanged native
        # manifest/patch bytes; Swift-only repairs do not force a native rebuild.
        for name in (contract.HERE + "/build.py", contract.HELPER, contract.MANIFEST):
            original = subprocess.check_output(["git", "-C", str(args.control), "show", producer_commit + ":" + name], timeout=60)
            contract.require(hashlib.sha256(original).hexdigest() == build["original_control_sources"].get(name),
                             "Original native producer source receipt does not match Git")
        native.validate_artifact_source(artifact, manifest, args.control / contract.MANIFEST, producer_commit)
        contract.require(native.archive_files(args.artifact / "any.xcframework.zip") == artifact["filesSHA256"],
                         "Native device/simulator archive members differ")
        helper = [sys.executable, "-B", str(args.control / contract.HELPER), "--manifest", str(args.control / contract.MANIFEST)]
        run([*helper, "install", "--artifact", str(args.artifact), "--producer-commit", producer_commit],
            "install-exact-native-artifact", timeout=300)
        native_files = installed_fingerprints(args.control, artifact, native)
        for source, destination in (("native-build.json", "original-native-build.json"),
                                    ("native-artifact.json", "original-native-artifact.json")):
            shutil.copyfile(args.artifact / source, args.evidence / destination)
        vendor = args.control / "Modules/PinkhaAnyRuntime/Vendor"
        shutil.copyfile(vendor / "consumer-binding.json", args.evidence / "native-consumer-binding.json")
        receipt.update(native_artifact_receipt_sha256=receipt_sha, archive_sha256=archive_sha,
                       manifest_sha256=contract.MANIFEST_SHA, version=contract.VERSION, binary_reused=reused,
                       native_tests_executed=0, retained_swift_tests_executed=0)
        environment = os.environ.copy()
        contract.require(not environment.get("PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE"), "Do not combine acceptance candidates")
        environment["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-prepared-inline-v1"
        package = args.control / "Modules/PinkhaAnyRuntime"
        cache = ["-clonedSourcePackagesDirPath", str(args.work / "SourcePackages")]
        run(["xcodebuild", "-version"], "xcode-version", timeout=30)
        schemes = execution.command_json(run(["xcodebuild", "-list", "-json", *cache], "schemes", cwd=package, env=environment, timeout=300))
        available = schemes.get("workspace", schemes.get("project", {})).get("schemes", [])
        selected = [name for name in (contract.PACKAGE, contract.PACKAGE + "-Package") if name in available]
        contract.require(selected, "Actual prepared runtime package scheme missing")
        scheme = selected[0]
        run(["xcodebuild", "-resolvePackageDependencies", "-scheme", scheme, *cache], "resolve-packages",
            cwd=package, env=environment, timeout=600)
        pins = contract.resolved_pins(package)
        dependencies = contract.dependency_checkouts(args.work)
        receipt["resolved_packages"] = pins
        receipt["actual_dependency_sources"] = dependencies
        run_simulator(args.control, args.work, args.evidence, receipt, run, environment, package, scheme, cache)
        contract.require(contract.resolved_pins(package) == pins and contract.dependency_checkouts(args.work) == dependencies
                         and installed_fingerprints(args.control, artifact, native) == native_files
                         and contract.digest(args.artifact / "native-artifact.json") == receipt_sha
                         and contract.digest(args.artifact / "any.xcframework.zip") == archive_sha,
                         "Executed native binary or resolved dependencies changed")
        contract.require(receipt.get("compiled_products_unchanged") is True, "Current compiled test product proof did not complete")
        contract.require(receipt.get("owned_simulator_cleanup_status") == "COMPLETE", "Owned simulator cleanup did not complete")
    except BaseException as error:
        primary = error
        raise
    finally:
        contract.source_after(args.control, before, args.evidence, receipt, primary)
    receipt.update(status=contract.PASS, full_migration_accepted=False, file_capability=0, inline_file_capability=1, maximum_inline_bytes=4095,
                   network_verified=False, runtime_reopen_scope="orderly SDK/store reopen in one XCTest OS process")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "work", "evidence", "artifact"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    for name in ("native-artifact-run-id", "native-artifact-run-attempt", "native-producer-commit"):
        parser.add_argument("--" + name, default="")
    args = parser.parse_args()
    for name in ("control", "work", "evidence", "artifact"):
        setattr(args, name, getattr(args, name).resolve())
    return execution.run_stage(args, execute)


if __name__ == "__main__":
    raise SystemExit(main())
