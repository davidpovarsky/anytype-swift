#!/usr/bin/env python3
"""Compile original Native UI tests against an already-built unified host.

This creates one UI-runner-only project from the existing exact reversible
projection. It never compiles, alters, signs or replaces the application.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--main-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner-source-commit")
    args = parser.parse_args()
    root, evidence, output = args.main_root, args.main_evidence, args.output
    for path in (root, evidence, output):
        require(path.is_absolute() and path.resolve() == path, "canonical_absolute_path_required")
    require(root in evidence.parents and root in output.parents, "one_owned_main_workspace_required")
    require(not output.exists(), "refuse_existing_native_ui_output")
    source = root / "source"
    original = json.loads((evidence / "receipt.json").read_bytes())
    require(original.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and original.get("testsExecuted") == 0 and original.get("sourceUnchanged") is True,
            "completed_original_main_build_required")
    origin = original["sourceCommit"]
    before = json.loads((evidence / "source-before.json").read_bytes())
    after = json.loads((evidence / "source-after.json").read_bytes())
    require(before == after and before["commit"] == origin and before["status"] == "",
            "unchanged_original_source_required")
    current = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                             check=True, capture_output=True, text=True).stdout.strip()
    clean = subprocess.run(["git", "-C", str(source), "status", "--porcelain"],
                           check=True, capture_output=True, text=True).stdout
    require(current == origin and clean == "", "frozen_main_checkout_required")
    profiles = {
        "70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683": {
            "name": "original-unified70fb-sdk44",
            "nativeSHA256": "08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc",
            "sdkReceiptSHA256": "67edd8f955524044428bf583b51f2357ca290e5ded0aacd8def0dff92f6b1521",
            "lockSHA256": "bb5582d3f0b9bc17b909ade4751904fd7b2fee2d066fea50b7a1ef913a8fe513",
        },
        "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72": {
            "name": "qualified-mobile70f0-sdk30e",
            "nativeSHA256": "c3374a58dffb64658fe6840ee9bd2711a4b1bf8c449c32da5bd51ede4901cece",
            "sdkReceiptSHA256": "0ae5a1476c899b1790f01a2a3b4118034e848d8ad8dcf2d97f12104f7387f798",
            "lockSHA256": "ffc47556534ee279d01bb771c6d49637766e8828bd872cce739e541d8ce4f124",
        },
    }
    profile = profiles.get(original["inputs"]["nativeSourceManifestSHA256"])
    require(profile is not None, "explicit_reviewed_unified_profile_required")
    for key in ("nativeSHA256", "sdkReceiptSHA256", "lockSHA256"):
        require(original["inputs"].get(key) == profile[key],
                "reviewed_unified_input_changed:" + key)
    require(digest(source / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")
            == profile["lockSHA256"], "reviewed_package_lock_changed")
    for phase in ("app", "ui"):
        require(original[phase]["exitCode"] == 0
                and original[phase]["status"] == "PASS_BUILD_EXIT_0",
                "both_original_build_phases_must_have_completed")
        require(digest(evidence / phase / "original.log") == original[phase]["logSHA256"],
                "original_build_log_changed:" + phase)
    native = source / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib"
    require(digest(native) == original["inputs"]["nativeSHA256"], "native_input_changed")
    require(digest(source / "Dependencies/Hanlin/.pinkha-source.json") ==
            original["inputs"]["sdkReceiptSHA256"], "canonical_sdk_changed")
    inputs = [
        "NativeApp/AnyNative.xcodeproj/project.pbxproj",
        "NativeApp/AnyNative.xcodeproj/xcshareddata/xcschemes/PinkhaAnyNativeApp.xcscheme",
        "NativeApp/UITests/NativeLaunchTests.swift",
        "NativeApp/UITests/NativeHistoryTests.swift",
    ]
    for relative in inputs:
        require(digest(source / relative) == before["files"][relative]["sha256"],
                "original_native_ui_source_changed:" + relative)
    runner_origin = args.runner_source_commit or origin
    require(len(runner_origin) == 40 and all(x in "0123456789abcdef" for x in runner_origin),
            "explicit_runner_source_commit_required")
    runner_launch = (source / inputs[2]).read_bytes()
    if runner_origin != origin:
        subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor",
                        origin, runner_origin], check=True, capture_output=True)
        changed = subprocess.run(["git", "-C", str(source), "diff", "--name-only",
            origin, runner_origin], check=True, capture_output=True, text=True).stdout.splitlines()
        require(all(name == inputs[2] or name.startswith(("Tools/", "docs/validation/"))
                    for name in changed), "runner_overlay_must_not_change_application_source")
        candidate = subprocess.run(["git", "-C", str(source), "show",
            runner_origin + ":" + inputs[2]], check=True, capture_output=True).stdout
        start = b"/// The existing native flows may run against the standalone acceptance app or\n"
        end = b"// Test-runner-only fixture protocol. These types never enter the app target.\n"
        require(runner_launch.count(start) == candidate.count(start) == 1
                and runner_launch.count(end) == candidate.count(end) == 1,
                "one_explicit_unified_launch_adapter_required")
        require(runner_launch.split(start)[0] == candidate.split(start)[0]
                and runner_launch.split(end)[1] == candidate.split(end)[1],
                "all_original_test_methods_and_fixture_contract_must_remain_byte_identical")
        runner_launch = candidate
    helper = source / "Tools/AnyEnginePort/native_ui_transition_project.py"
    original_helper = subprocess.run(["git", "-C", str(source), "show",
        origin + ":Tools/AnyEnginePort/native_ui_transition_project.py"],
        check=True, capture_output=True).stdout
    require(helper.read_bytes() == original_helper, "original_ui_projection_changed")
    # Loading the original helper must not write bytecode into frozen source.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("qualified_native_ui_projection", helper)
    projection = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(projection)
    project_bytes, transformation = projection.project_bytes((source / inputs[0]).read_bytes())
    scheme_bytes = projection.scheme_bytes((source / inputs[1]).read_bytes())

    output.mkdir(mode=0o700)
    project = output / "source" / projection.PROJECT_NAME
    files = {
        "source/" + projection.PROJECT_NAME + "/project.pbxproj": project_bytes,
        "source/" + projection.PROJECT_NAME + "/xcshareddata/xcschemes/"
        + projection.SCHEME_NAME + ".xcscheme": scheme_bytes,
        "source/UITests/NativeLaunchTests.swift": runner_launch,
        "source/UITests/NativeHistoryTests.swift": (source / inputs[3]).read_bytes(),
    }
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    sources = {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
               for name, raw in files.items()}
    write(output / "projection.json", {
        "mainSourceCommit": origin, "runnerSourceCommit": runner_origin,
        "mainReceiptSHA256": digest(evidence / "receipt.json"),
        "reviewedInputProfile": profile,
        "exactOriginalProjectAndScheme": transformation, "sourceFiles": sources,
        "applicationBuildTargets": 0, "nativeLibraryBuilds": 0,
        "allOriginalNativeUITestMethodsCompiled": True,
        "changedOriginalMethodAssertions": 0,
    })
    argv = [
        "xcodebuild", "build-for-testing", "-project", str(project),
        "-scheme", projection.SCHEME_NAME, "-configuration", "Debug",
        "-destination", "generic/platform=iOS Simulator",
        "-derivedDataPath", str(output / "derived"),
        "-resultBundlePath", str(output / "Build.xcresult"), "-jobs", "4",
        "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "ENABLE_TESTABILITY=YES",
        "SWIFT_OPTIMIZATION_LEVEL=-Onone", "CODE_SIGN_IDENTITY=-",
        "CODE_SIGNING_ALLOWED=YES", "CODE_SIGNING_REQUIRED=YES",
        "PROVISIONING_PROFILE_SPECIFIER=",
    ]
    free = shutil.disk_usage(root).free
    floor = 2 * 1024**3
    require(free >= floor, "owned_process_disk_floor")
    log = output / "original-build.log"
    started = time.time()
    environment = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with log.open("wb") as stream:
        process = subprocess.Popen(argv, cwd=source, env=environment, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        record = {"sourceCommit": origin, "runnerSourceCommit": runner_origin,
                  "mainReceiptSHA256": digest(evidence / "receipt.json"),
                  "reviewedInputProfile": profile,
                  "argv": argv, "pid": process.pid,
                  "pgid": process.pid, "started": started, "freeBytesBefore": free}
        write(output / "launch.json", record)
        stopped = None
        minimum = free
        while process.poll() is None:
            free = shutil.disk_usage(root).free
            minimum = min(minimum, free)
            if free < floor:
                stopped = "RESOURCE_DISK_FLOOR"
            elif time.time() - started > 1200:
                stopped = "TIMEOUT"
            if stopped:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                break
            write(output / "monitor.json", {"freeBytes": free, "minimumFreeBytes": minimum,
                                            "elapsedSeconds": time.time() - started})
            time.sleep(2)
        code = process.wait()
    require(all(digest(output / name) == row["sha256"] for name, row in sources.items()),
            "native_ui_source_mutated_during_build")
    products = output / "derived/Build/Products"
    rows = []
    for path in sorted(products.rglob("*")):
        if path.is_symlink():
            rows.append({"path": str(path.relative_to(products)), "kind": "symlink",
                         "target": os.readlink(path)})
        elif path.is_file():
            rows.append({"path": str(path.relative_to(products)), "kind": "file",
                         "bytes": path.stat().st_size, "sha256": digest(path)})
    write(output / "products-all.json", rows)
    record["completeProductsInventory"] = {
        "path": str(output / "products-all.json"),
        "sha256": digest(output / "products-all.json"), "entries": len(rows)}
    record.update(exitCode=code, elapsedSeconds=time.time() - started,
                  minimumFreeBytes=minimum, logSHA256=digest(log),
                  status=stopped or ("PASS_UI_RUNNER_BUILD_NOT_ACCEPTANCE" if code == 0 else "FAIL_BUILD"),
                  testsExecuted=0, applicationBuildTargets=0, sourceUnchanged=True)
    write(output / "receipt.json", record)
    require(code == 0 and stopped is None, "original_native_ui_runner_build_failed")


if __name__ == "__main__":
    main()
