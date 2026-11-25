"""Qualify the original completed native slice after a Swift C-ABI correction.

The failed producer receipt remains immutable. This continuation is allowed only
after every native build/verification command succeeded and only its final Swift
typecheck failed. It never invokes Go, changes a framework or reruns app tests.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import plistlib
import shutil
import signal
import subprocess
import time
import zipfile
import os
import build_apple as build
import native_dependencies

EXPECTED_BINARY = "08f8b8dab68ed21cabec955fbde1323983f02f549dd67aa3e2e4d11c4f818bfc"
EXPECTED_ORIGINAL_CONTROLLER = "05d4937b3f55d806738e3112606c4a4ccdc1dad8"
PASS = "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha", required=True)
    parser.add_argument("--wrapper-directory", type=Path, required=True)
    args = parser.parse_args()
    root, wrappers = args.root, args.wrapper_directory
    build.require(root.resolve() == root and root == Path("/Users/m1/builds/pinkha-dual-native-v1-"
                  + build.MANIFEST_SHA[:12] + "-simulator"), "exact_original_simulator_root_required")
    build.require(len(args.controller_sha) == 40 and all(c in "0123456789abcdef" for c in args.controller_sha),
                  "committed_controller_required")
    build.require(wrappers.resolve() == wrappers and wrappers.parent == root,
                  "owned_wrapper_directory_required")
    destination = root / "swift-abi-qualification"
    destination.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "controllerCommit": args.controller_sha,
               "controllerSHA256": build.digest(__file__), "sourceManifestSHA256": build.MANIFEST_SHA,
               "nativeLibraryBuildInvocations": 0, "reusedNativeLibraryBuildInvocations": 1,
               "applicationBuilds": 0, "appleTestsExecuted": 0, "nativeAcceptanceTestsExecuted": 0,
               "originalProducerFailurePreserved": True, "commands": []}
    def run(argv, name, timeout=180):
        item = {"name": name, "argv": [str(a) for a in argv], "started": time.time()}
        path = destination / (name + ".log")
        with path.open("xb") as output:
            process = subprocess.Popen(argv, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            item.update(pid=process.pid, pgid=process.pid)
            build.write(destination / (name + ".started.json"), item)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                free = shutil.disk_usage(root).free
                item["minimumFreeBytes"] = min(item.get("minimumFreeBytes", free), free)
                if time.monotonic() > deadline or free < build.EMERGENCY_FREE_BYTES:
                    item["stopReason"] = "time_or_disk_limit"
                    os.killpg(process.pid, signal.SIGTERM)
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=10)
                    break
                time.sleep(1)
        item.update(exitCode=process.returncode, elapsedSeconds=time.time() - item["started"],
                    logSHA256=build.digest(path))
        receipt["commands"].append(item)
        build.write(destination / (name + ".command.json"), item)
        build.require(process.returncode == 0, "actual_swift_command_failed:" + name)
        return path
    try:
        original_path = root / "evidence/receipt.json"
        original_digest = build.digest(original_path)
        original = json.loads(original_path.read_text())
        build.require(original["status"] == "FAIL"
                      and original["controllerCommit"] == EXPECTED_ORIGINAL_CONTROLLER
                      and original["sourceManifestSHA256"] == build.MANIFEST_SHA
                      and original["failure"]["message"] == "actual_command_failed:generated-actual-swift-entry-typecheck"
                      and original["slicePhase"] == "simulator", "exact_prior_typecheck_failure_required")
        commands = original["commands"]
        build.require(commands and commands[-1]["name"] == "generated-actual-swift-entry-typecheck"
                      and commands[-1]["exitCode"] != 0
                      and all(row["exitCode"] == 0 for row in commands[:-1]),
                      "prior_native_command_failed")
        for command in commands:
            log = root / "evidence" / (command["name"] + ".log")
            build.require(build.digest(log) == command["logSHA256"], "original_command_log_changed")
        receipt["originalProducerReceiptSHA256"] = original_digest
        receipt["originalNativeCommands"] = [row for row in commands if row["name"] != commands[-1]["name"]]
        source = root / "source"
        manifest = json.loads((source / "source-manifest.json").read_text())
        extra = {}
        for platform, (_, native_sha) in native_dependencies.PLATFORMS.items():
            relative = "heart/deps/libs/" + platform + "/libtantivy_go.a"
            extra[relative] = {"sha256": native_sha, "bytes": (source / relative).stat().st_size}
        build.check_source(source, manifest, extra)
        output = root / "Lib.xcframework"
        info = plistlib.loads((output / "Info.plist").read_bytes())
        libraries = info["AvailableLibraries"]
        build.require(len(libraries) == 1 and libraries[0]["SupportedArchitectures"] == ["arm64"]
                      and libraries[0]["SupportedPlatform"] == "ios"
                      and libraries[0].get("SupportedPlatformVariant") == "simulator", "original_slice_changed")
        library = libraries[0]
        binary = output / library["LibraryIdentifier"] / library["LibraryPath"] / "Lib"
        build.require(build.digest(binary) == EXPECTED_BINARY, "original_native_binary_changed")
        symbols = (root / "evidence" / ("symbols-" + library["LibraryIdentifier"] + ".log")).read_text()
        for symbol in ("_crosscall2", "__cgo_wait_runtime_init_done"):
            build.require(sum(line.split()[-1:] == [symbol] for line in symbols.splitlines()) == 1,
                          "single_go_runtime_census_changed")
        wrapper_manifest = json.loads((wrappers / "wrapper-files.json").read_text())
        build.require(wrapper_manifest["commit"] == args.controller_sha
                      and set(wrapper_manifest["files"]) == {"PinkhaAnyEmbeddedBridge.swift", "PinkhaLoadedAccountSourceNative.swift"},
                      "exact_committed_wrappers_required")
        for name, identity in wrapper_manifest["files"].items():
            path = wrappers / name
            build.require(path.is_file() and not path.is_symlink()
                          and path.stat().st_size == identity["bytes"]
                          and build.digest(path) == identity["sha256"], "production_wrapper_changed")
        receipt["productionWrapperInputs"] = wrapper_manifest
        generated = build.generated_swift_entry(destination)
        sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], "sdk", 30).read_text().strip()
        common = ["xcrun", "swiftc", "-typecheck", "-target", "arm64-apple-ios27.0-simulator",
                  "-sdk", sdk, "-F", output / library["LibraryIdentifier"],
                  "-module-cache-path", root / "swift-module-cache"]
        run([*common, generated], "generated-actual-swift-entry-typecheck")
        run([*common, "-D", "PINKHA_DUAL_ENGINE_RUNTIME",
             *[wrappers / name for name in sorted(wrapper_manifest["files"])]],
            "actual-production-protobuf-wrapper-typecheck")
        build.require(build.digest(original_path) == original_digest and build.digest(binary) == EXPECTED_BINARY,
                      "original_evidence_or_binary_changed_during_typecheck")
        build.check_source(source, manifest, extra)
        inventory = {str(p.relative_to(output)): {"bytes": p.stat().st_size, "sha256": build.digest(p)}
                     for p in sorted(output.rglob("*")) if p.is_file()}
        build.write(destination / "framework-files.json", inventory)
        archive = root / "Lib.xcframework.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zipped:
            for p in sorted(output.rglob("*")):
                if p.is_file(): zipped.write(p, str(p.relative_to(root)))
        receipt.update(status=PASS, slicePhase="simulator", independentGoRuntimeCount=1,
                       binarySHA256=EXPECTED_BINARY, binaryBytes=binary.stat().st_size,
                       sourceUnchanged=True, frameworkUnchanged=True,
                       sourcePins=manifest["sourcePins"], heartCaptureBridgeCommit=manifest["heartCaptureBridgeCommit"],
                       heartRuntimeVersion="pinkha-dual-runtime-v1-" + build.MANIFEST_SHA,
                       anyRuntimeVersion="v0.5.0-pinkha.dual.1-" + build.MANIFEST_SHA,
                       archiveSHA256=build.digest(archive), archiveBytes=archive.stat().st_size,
                       frameworkInventorySHA256=build.digest(destination / "framework-files.json"))
    except BaseException as error:
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        receipt["freeBytesAfter"] = shutil.disk_usage(root).free
        build.write(destination / "receipt.json", receipt)
        print(json.dumps({key: receipt.get(key) for key in ("status", "failure", "binarySHA256", "archiveSHA256")}))

if __name__ == "__main__":
    main()
