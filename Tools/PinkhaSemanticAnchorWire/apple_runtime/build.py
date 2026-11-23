#!/usr/bin/env python3
"""Build one distinct Page154 ARM64 simulator Lib; no Go tests or App execution."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import subprocess
import sys

import contract

sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
sys.path.insert(0, str(contract.ROOT / "Tools/PinkhaNativeDerived"))
sys.path.insert(0, str(contract.ROOT / "Tools/PinkhaSimulatorGate"))
from authorized_read import build_apple as binding
import run_owned_single_lane as supervisor
import wave15_batch as owned

TAGS = "nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
SWIFT_CHECK = """import Foundation
import Lib

public func page154GeneratedByteEntry(_ request: Data) -> Data? {
    Lib.ServicePinkhaSemanticAnchorCapture(request)
}
"""


def source_closure(control, head, helper_path):
    contract.require(contract.git(control, "rev-parse", "HEAD") == head
                     and not contract.git(control, "status", "--porcelain"), "Exact clean controller required")
    paths = {helper_path.resolve()}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename:
            path = Path(filename).resolve()
            if path.suffix == ".py" and path.is_relative_to(control):
                paths.add(path)
    hashes = {}
    for path in sorted(paths):
        name = path.relative_to(control).as_posix()
        original = subprocess.check_output(["git", "-C", str(control), "show", head + ":" + name], timeout=30)
        observed = contract.digest(path)
        contract.require(__import__("hashlib").sha256(original).hexdigest() == observed,
                         "Loaded controller helper differs from exact Git source")
        hashes[name] = observed
    return hashes


def bind_command(heart, framework):
    ldflags = "-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + contract.VERSION
    ldflags += " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + contract.HEART
    return [str(heart / "deps/gomobile"), "bind", "-tags", TAGS, "-ldflags", ldflags,
            "-target=iossimulator/arm64", "-iosversion=17.0", "-o", str(framework),
            contract.PACKAGE, "github.com/anyproto/anytype-heart/core"]


def execute(args, receipt, run):
    control, heart, work = args.control, args.heart_source, args.work
    contract.require(platform.system() == "Darwin" and platform.machine() == "arm64",
                     "Actual Apple ARM64 build host required")
    contract.require(not work.exists() and not args.artifacts.exists(), "Fresh owned work/output required")
    contract.require(shutil.disk_usage(work.parent).free >= 12 * 1024**3, "Disk reserve below 12 GiB")
    helper_path = control / "Tools/PinkhaNativeDerived/build_custom_heart.py"
    contract.require(contract.digest(helper_path) == binding.binding.HELPER_SHA, "Reviewed binary helper changed")
    helper = binding.pair_ci.load_module("page154_binary_helper", helper_path)
    before = source_closure(control, args.expected_app_sha, helper_path)
    receipt["control_source_sha256"] = before
    manifest = contract.candidate(control)
    retained = contract.retained_native(control, manifest)
    contract.save(args.evidence / "retained-native-page2.json", retained)
    native_proof = args.evidence / "original-native-page2"
    for name in retained["evidence_sha256"]:
        target = native_proof / contract.relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(control / contract.PROOF / contract.relative(name), target)
    shutil.copyfile(control / contract.MANIFEST_PATH, args.evidence / "page-source.json")
    work.mkdir()
    args.artifacts.mkdir()
    source = contract.prepare_source(control, heart, manifest, run)
    contract.save(args.evidence / "native-source-before.json", source)
    receipt.update(phase="TOOLCHAIN_AND_DEPENDENCIES", native_source_count=154, source_manifest_sha256=contract.MANIFEST_SHA,
                   native_source_sha256=source, native_module_sha256=manifest["module_sha256"],
                   native_tests_executed=0, old_tests_executed=0, protobuf_generators_executed=0,
                   retained_native_page_methods=2, fixture_included=False, runtime_version=contract.VERSION)
    real_go = Path(shutil.which("go") or "").resolve(strict=True)
    go_version = run([str(real_go), "version"], "go-version").read_text().strip()
    contract.require(go_version == "go version go1.26.5 darwin/arm64", "Pinned Go1.26.5 ARM64 compiler required")
    xcode = run(["xcodebuild", "-version"], "xcode-version").read_text().strip()
    sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "simulator-sdk").read_text().strip()
    sdk_path = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], "simulator-sdk-path").read_text().strip()
    contract.require(xcode.startswith("Xcode 27") and sdk.split(".")[0] == "27", "Xcode27/iOS27 SDK required")
    dependencies = [helper.fetch_tantivy(heart, architecture) for architecture in ("darwin-arm64", "ios-arm64-sim")]
    bind_work = work / "binding"
    bind_work.mkdir()
    gowork = bind_work / "go.work"
    gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + binding.pair_ci.GENPROTO_PATH
                     + " => " + binding.pair_ci.GENPROTO_PATH + " " + binding.pair_ci.GENPROTO_VERSION + "\n",
                     encoding="utf8")
    env = dict(os.environ, CGO_ENABLED="1", GOMAXPROCS="2", GOMEMLIMIT="4096MiB", GOTOOLCHAIN="local",
               GOWORK=str(gowork), GOFLAGS="-mod=readonly")
    # Reuse only the original immutable module declaration seed. The Page154
    # product identity and native proof above remain completely separate.
    prepared = binding.prepare_binding(control, heart, bind_work, args.evidence, real_go, env, gowork,
                                       helper, run, binding.CANDIDATE)
    env = prepared["env"]
    binding.launcher.load_seed_contract(Path(env["PINKHA_T5_GENERATED_CONTRACT"]),
        env["PINKHA_T5_GENERATED_CONTRACT_SHA256"], heart, Path(env["PINKHA_T5_MOBILE_TMP"]))
    shutil.copyfile(prepared["graph_contract_path"], args.evidence / "generated-bind-contract.json")
    contract.require(contract.digest(args.evidence / "generated-bind-contract.json") == prepared["graph_contract_sha"],
                     "Retained generated module contract differs")
    receipt.update(phase="BIND_SINGLE_PRODUCTION_SLICE", go_version=go_version, xcode=xcode,
                   simulator_sdk=sdk, native_dependencies=dependencies,
                   dependency_seed_original_candidate=binding.CANDIDATE,
                   dependency_seed_reuses_module_declarations_only=True)
    destination = work / "production"
    destination.mkdir()
    framework = destination / "Lib.xcframework"
    run(bind_command(heart, framework), "page154-gomobile-bind", env, timeout=3600)
    scopes = binding.validate_generated_scopes(prepared, heart)
    binary = framework / "ios-arm64-simulator/Lib.framework/Lib"
    contract.require(binary.is_file(), "Missing actual ARM64 simulator framework")
    raw_sha = contract.digest(binary)
    combined = destination / "Lib-with-tantivy.a"
    run(["xcrun", "libtool", "-static", "-o", str(combined), str(binary),
         str(heart / "deps/libs/ios-arm64-sim/libtantivy_go.a")], "tantivy-repack", env)
    shutil.copyfile(combined, binary)
    header_root = framework / "ios-arm64-simulator/Lib.framework/Headers"
    header_paths = sorted(header_root.glob("*.h"))
    contract.require(header_paths, "Actual generated framework headers missing")
    headers = "\n".join(path.read_text() for path in header_paths)
    symbols = run(["xcrun", "nm", "-gU", str(binary)], "actual-exported-symbols", env)
    generated = contract.generated_entry(headers, symbols.read_text())
    exported_headers = args.evidence / "generated-headers"
    exported_headers.mkdir()
    for header in header_paths:
        shutil.copyfile(header, exported_headers / header.name)
    slices = helper.verify_framework_slices(framework, contract.VERSION)
    binding.validate_simulator_framework(plistlib.loads((framework / "Info.plist").read_bytes()),
                                         slices, expected_version=contract.VERSION)
    swift = args.evidence / "GeneratedEntryCheck.swift"
    swift.write_text(SWIFT_CHECK, encoding="utf8")
    run(["xcrun", "swiftc", "-typecheck", "-target", "arm64-apple-ios17.0-simulator",
         "-sdk", sdk_path, "-F", str(framework / "ios-arm64-simulator"),
         "-module-cache-path", str(work / "swift-module-cache"),
         "-module-name", "PinkhaPage154GeneratedEntry", str(swift)], "actual-swift-entry-typecheck", env)
    generated.update(swift_typecheck="PASS_ACTUAL_GENERATED_MODULE", swift_source_sha256=contract.digest(swift),
                     header_sha256={path.name: contract.digest(path) for path in header_paths},
                     symbol_log_sha256=contract.digest(symbols), runtime_execution="NOT_RUN")
    contract.save(args.evidence / "generated-entry.json", generated)
    contract.require(contract.verify_source(heart, manifest) == source, "Page154 source changed during compilation")
    after = source_closure(control, args.expected_app_sha, helper_path)
    contract.require(before == after, "Controller/helper source closure changed during compilation")
    contract.save(args.evidence / "native-source-after.json", source)
    contract.save(args.evidence / "controller-source-after.json", after)
    hashes = {path.relative_to(framework).as_posix(): contract.digest(path)
              for path in sorted(framework.rglob("*")) if path.is_file()}
    packaged = dict(schemaVersion=1, status="APPLE_FRAMEWORK_BUILT_NOT_EXECUTED", runtime_variant=contract.VARIANT,
        source_manifest_sha256=contract.MANIFEST_SHA, expected_app_get_version=contract.VERSION,
        heart_sha=contract.HEART, native_source_count=154, native_source_sha256=source,
        native_module_sha256=manifest["module_sha256"], native_source_origin=contract.NATIVE_SOURCE,
        retained_native_page2_acceptance_sha256=contract.ACCEPTANCE_SHA, retained_native_page2_audit_sha256=contract.AUDIT_SHA,
        github_run_id=receipt["run_id"], github_run_attempt=receipt["run_attempt"], integration_sha=args.expected_app_sha,
        target="ios", target_architecture="arm64", target_environment="simulator", fixture_included=False,
        binary_sha256=contract.digest(binary), unmerged_go_archive_sha256=raw_sha, binary_slices=slices,
        files_sha256=hashes, generated_entry=generated, generated_scopes=scopes,
        native_test_invocations=0, native_generators_executed=0, retained_original_native_methods=2,
        app_get_version_status="NOT_RUN_BUILD_ONLY", apple_product_tests_executed=0,
        product_acceptance="NOT_RUN", mounted_editor_acceptance="NOT_RUN",
        client_enablement="DISABLED_PENDING_SEPARATE_APPLE_AND_EDITOR_ACCEPTANCE",
        existing_coherent139_archive_reused=False, existing_runtime_profiles_modified=False)
    packaged_name = "SemanticPageHeartBuild.json"
    contract.save(destination / packaged_name, packaged)
    contract.save(args.evidence / "runtime-build-receipt.json", packaged)
    archive = args.artifacts / (contract.ARTIFACT + ".tar.gz")
    run(["tar", "-czf", str(archive), "-C", str(destination), "Lib.xcframework", packaged_name],
         "archive-distinct-page154-runtime", dict(env, COPYFILE_DISABLE="1"))
    receipt.update(status=contract.PASS, phase="COMPLETE", framework_files_sha256=hashes, generated_entry=generated,
                   archive_sha256=contract.digest(archive), archive_bytes=archive.stat().st_size,
                   packaged_receipt_sha256=contract.digest(destination / packaged_name),
                   artifact_name=archive.name, app_get_version_status="NOT_RUN_BUILD_ONLY",
                   product_acceptance="NOT_RUN", mounted_editor_acceptance="NOT_RUN")
    contract.save(args.evidence / "runtime-artifact.json",
                  {key: receipt[key] for key in ("status", "artifact_name", "archive_sha256", "archive_bytes",
                                                 "packaged_receipt_sha256", "run_id", "run_attempt")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "heart-source", "work", "evidence", "artifacts"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    for name in ("control", "heart_source", "work", "evidence", "artifacts"):
        setattr(args, name, getattr(args, name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    path = args.evidence / "build.json"
    contract.require(not path.exists(), "Fresh build receipt required")
    receipt = dict(status="NOT_RUN", phase="PREFLIGHT", app_sha=args.expected_app_sha,
        run_id=os.environ.get("GITHUB_RUN_ID"), run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
        native_tests_executed=0, app_builds=0, apple_product_tests_executed=0,
        app_capability="OFF", commands=[], started_at=datetime.now(timezone.utc).isoformat())
    contract.require(re.fullmatch("[0-9a-f]{40}", args.expected_app_sha) and args.expected_app_sha == os.environ.get("GITHUB_SHA")
                     and (receipt["run_id"] or "").isdigit() and (receipt["run_attempt"] or "").isdigit(),
                     "Exact original CI source/run/attempt required")
    previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    cancelled = False

    def cancel(number, frame):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            raise KeyboardInterrupt(signal.Signals(number).name)

    for number in previous:
        signal.signal(number, cancel)

    def run(command, name, env=None, cwd=None, timeout=900):
        contract.require(re.fullmatch("[a-z0-9-]+", name), "Invalid owned command name")
        log = args.evidence / (name + ".log")
        contract.require(not log.exists(), "Refuse existing owned command log")
        entry = dict(name=name, argv=list(map(str, command)), status="RUNNING", timeout_seconds=timeout)
        receipt["commands"].append(entry)
        contract.save(path, receipt)
        process, primary = None, None
        try:
            with log.open("xb") as output:
                try:
                    process = subprocess.Popen(entry["argv"], cwd=cwd or args.heart_source,
                        env=env or os.environ.copy(), stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                    entry["worker_pid"] = process.pid
                    entry["return_code"] = process.wait(timeout=timeout)
                    entry["status"] = "PASS_EXIT_0" if process.returncode == 0 else "FAIL_EXIT_NONZERO"
                except BaseException as error:
                    primary = error
                    entry.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                                 error_type=type(error).__name__)
                finally:
                    if process is not None:
                        try:
                            owned.terminate_owned(process)
                            entry["owned_group_cleanup"] = "TERM_THEN_KILL"
                        except BaseException as error:
                            entry["cleanup_error_type"] = type(error).__name__
                            if primary is None:
                                primary = error
                    output.flush()
                    os.fsync(output.fileno())
        finally:
            if process is not None:
                entry["return_code"] = process.returncode
            command_path = log.with_suffix(".command.json")
            contract.save(command_path, entry)
            if process is not None:
                try:
                    entry["owned_group_quiescence"] = supervisor.verify_owned_group_stopped(command_path)
                except BaseException as error:
                    entry["quiescence_failure"] = dict(error_type=type(error).__name__, error=str(error))
                    if primary is None:
                        primary = error
            entry["log_sha256"] = contract.digest(log) if log.is_file() else None
            contract.save(command_path, entry)
            contract.save(path, receipt)
        if primary:
            raise primary
        contract.require(entry.get("return_code") == 0, "Owned native build command failed: " + name)
        return log

    try:
        execute(args, receipt, run)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL",
                       error_type=type(error).__name__, error=str(error))
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        contract.save(path, receipt)
        for number, handler in previous.items():
            signal.signal(number, handler)
    return int(receipt["status"] != contract.PASS)


if __name__ == "__main__":
    raise SystemExit(main())
