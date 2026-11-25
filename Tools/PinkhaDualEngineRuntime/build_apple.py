"""Build one Go runtime containing both Heart and Any for iPhone/iPad."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import plistlib
import shutil
import signal
import stat
import subprocess
import tarfile
import time
import uuid
import zipfile
import native_dependencies

MANIFEST_SHA = "70fb5342f2ff31d1cf5f7ce44bed7b16f6373f6bf95eb031d165339cf0f26683"
ARCHIVE_SHA = "376edcd9e784ae0ff4127c891893d57adb1d42555fe3e75beb82b0b839f1f3f4"
GO_ROOT = Path("/Users/m1/toolchains/anytapy-go1.27.4/go")
EMERGENCY_FREE_BYTES = 2 * 1024**3

def phase_space_estimate(root, manifest, phase):
    """A bounded working estimate from original native archive sizes.

    Cache/temp allowances are estimates, not claims about eventual disk use.
    Every command samples actual free space and terminates its own process
    group at the emergency floor. No other project's files are removed.
    """
    heart = Path("/Users/m1/builds/_retained-anytype/45456314424-1/build/"
                 "current-apple-release-return-rtl-45456314424-1/work/"
                 "heart-originals/verified-production/Lib.xcframework/"
                 "ios-arm64-simulator/Lib.framework/Lib")
    any_library = Path("/Users/m1/builds/anytapy-prepared-components-v2-3fb2ab37/"
                       "any/any.xcframework") / ("ios-arm64-simulator" if phase == "simulator"
                                               else "ios-arm64") / "anylib.a"
    references = [heart, any_library]
    for path in references:
        require(path.is_file() and not path.is_symlink(), "original_native_size_reference_missing")
    measured = [{"path": str(path), "bytes": path.stat().st_size,
                 "sha256": digest(path)} for path in references]
    native_bytes = sum(row["bytes"] for row in measured)
    components = {
        "sourceBytes": sum(item["bytes"] for item in manifest["files"].values()),
        "dependencyExtractionCopiesAllowanceBytes": 6 * (root / "native-dependencies.tar.gz").stat().st_size,
        "bindingToolsAllowanceBytes": 128 * 1024**2,
        "incrementalGoCacheAllowanceBytes": 4 * native_bytes,
        "compilerTemporaryAllowanceBytes": 4 * native_bytes,
        "outputRepackZipAllowanceBytes": 3 * native_bytes,
    }
    return {"phase": phase, "originalArchiveMeasurements": measured,
            "heartReferencePlatform": "simulator", "components": components,
            "estimatedAdditionalBytes": sum(components.values()),
            "emergencyFreeBytes": EMERGENCY_FREE_BYTES}

def require(value, why):
    if not value:
        raise ValueError(why)

def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024**2), b""):
            result.update(part)
    return result.hexdigest()

def write(path, value):
    with Path(path).open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

def check_source(root, manifest, native_files=None):
    native_files = native_files or {}
    require(not (set(native_files) & set(manifest["files"])), "native_dependency_overwrites_source")
    expected_files = {**manifest["files"], **native_files}
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    require(actual == set(expected_files) | {"source-manifest.json"}, "source_file_inventory_changed")
    for name, expected in expected_files.items():
        path = root / name
        require(path.resolve() == path and stat.S_ISREG(path.lstat().st_mode)
                and path.stat().st_size == expected["bytes"] and digest(path) == expected["sha256"],
                "source_bytes_changed:" + name)
    require(digest(root / "source-manifest.json") == MANIFEST_SHA, "manifest_changed")

def extract(archive, target, manifest):
    require(digest(archive) == ARCHIVE_SHA and not target.exists(), "fresh_verified_source_archive_required")
    target.mkdir(mode=0o700)
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        for item in tar:
            name = item.name
            require(name not in seen and item.isfile() and not name.startswith("/")
                    and all(p not in ("", ".", "..") for p in name.split("/"))
                    and "\\" not in name and "\0" not in name
                    and name in set(manifest["files"]) | {"source-manifest.json"},
                    "unexpected_source_archive_member")
            seen.add(name)
            destination = target / name
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tar.extractfile(item) as incoming, destination.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            destination.chmod(item.mode & 0o777)
    require(seen == set(manifest["files"]) | {"source-manifest.json"}, "source_archive_incomplete")
    check_source(target, manifest)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--controller-sha", required=True)
    parser.add_argument("--slice", choices=("simulator", "device"), required=True)
    args = parser.parse_args()
    root = args.root
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "actual_apple_silicon_host_required")
    require(root.is_dir() and root.resolve() == root and root.parent == Path("/Users/m1/builds")
            and root.name == "pinkha-dual-native-v1-" + MANIFEST_SHA[:12] + "-" + args.slice,
            "fixed_owned_build_root_required")
    require(len(args.controller_sha) == 40 and all(c in "0123456789abcdef" for c in args.controller_sha),
            "controller_commit_required")
    manifest_path = Path(__file__).with_name("source-manifest.json")
    require(digest(manifest_path) == MANIFEST_SHA, "controller_manifest_mismatch")
    manifest = json.loads(manifest_path.read_text())
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "executionKind": "local-mac", "executionUUID": str(uuid.uuid4()),
               "controllerCommit": args.controller_sha, "controllerSHA256": digest(__file__),
               "sourceManifestSHA256": MANIFEST_SHA, "sourceArchiveSHA256": ARCHIVE_SHA,
               "sourcePins": manifest["sourcePins"], "heartCaptureBridgeCommit": manifest["heartCaptureBridgeCommit"],
               "heartPage154ManifestSHA256": manifest["heartPage154ManifestSHA256"],
               "appleTestsExecuted": 0, "nativeAcceptanceTestsExecuted": 0,
               "applicationBuilds": 0, "independentGoRuntimeCount": 1,
               "slicePhase": args.slice, "commands": []}
    def run(argv, name, cwd=root, environment=None, timeout=3600):
        require(not (evidence / (name + ".log")).exists(), "command_replay_forbidden")
        item = {"name": name, "argv": [str(a) for a in argv], "cwd": str(cwd),
                "timeoutSeconds": timeout, "started": time.time(), "status": "FAIL"}
        receipt["commands"].append(item)
        with (evidence / (name + ".log")).open("xb") as stream:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            item.update(pid=process.pid, pgid=process.pid)
            write(evidence / (name + ".started.json"), item)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                free = shutil.disk_usage("/System/Volumes/Data").free
                item["minimumFreeBytes"] = min(item.get("minimumFreeBytes", free), free)
                if time.monotonic() > deadline or free < EMERGENCY_FREE_BYTES:
                    item["stopReason"] = "time_or_disk_limit"
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
                    break
                time.sleep(1)
            item.update(exitCode=process.returncode, elapsedSeconds=time.time() - item["started"])
        item["logSHA256"] = digest(evidence / (name + ".log"))
        item["status"] = "PASS_EXIT_0" if process.returncode == 0 else "FAIL"
        write(evidence / (name + ".command.json"), item)
        require(process.returncode == 0, "actual_command_failed:" + name)
        return evidence / (name + ".log")
    try:
        receipt["freeBytesBefore"] = shutil.disk_usage("/System/Volumes/Data").free
        receipt["phaseSpaceEstimate"] = phase_space_estimate(root, manifest, args.slice)
        write(evidence / "phase-space-estimate.json", receipt["phaseSpaceEstimate"])
        require(receipt["freeBytesBefore"] > receipt["phaseSpaceEstimate"]["estimatedAdditionalBytes"]
                + EMERGENCY_FREE_BYTES, "native_slice_estimated_space_unavailable")
        source = root / "source"
        extract(root / "native-source.tar.gz", source, manifest)
        receipt["sourceFilesVerified"] = len(manifest["files"])
        receipt["goVersion"] = run([GO_ROOT / "bin/go", "version"], "go-version", timeout=30).read_text().strip()
        require(receipt["goVersion"] == "go version go1.27.4 darwin/arm64", "pinned_go_toolchain_required")
        receipt["xcodeVersion"] = run(["xcodebuild", "-version"], "xcode-version", timeout=30).read_text().strip()
        require(receipt["xcodeVersion"].startswith("Xcode 27."), "xcode_27_required")
        for sdk in ("iphoneos", "iphonesimulator"):
            receipt[sdk] = run(["xcrun", "--sdk", sdk, "--show-sdk-version"], sdk + "-version", timeout=30).read_text().strip()
        tools = root / "tools"
        tools.mkdir(mode=0o700)
        (root / "tmp").mkdir(mode=0o700)
        shutil.copyfile(Path(__file__).with_name("runtime_go.py"), tools / "go")
        (tools / "go").chmod(0o755)
        receipt["generatedModuleLauncherSHA256"] = digest(tools / "go")
        workspace = root / "workspace"
        workspace.mkdir(mode=0o700)
        native_roots = [source / name for name in
                        ("sync", "heart", "any", "any/.runtime-artifacts/sdk-source")]
        (workspace / "go.work").write_text("go 1.27.4\n\nuse (\n"
            + "".join("\t" + str(path) + "\n" for path in native_roots) + ")\n")
        shutil.copyfile(source / "go.work.sum", workspace / "go.work.sum")
        receipt["effectiveWorkspaceSHA256"] = digest(workspace / "go.work")
        environment = {**os.environ, "GOROOT": str(GO_ROOT), "GOTOOLCHAIN": "local",
                       "CGO_ENABLED": "1", "GOWORK": str(workspace / "go.work"), "GOBIN": str(tools),
                       "TMPDIR": str(root / "tmp"), "GOTMPDIR": str(root / "tmp"),
                       "PINKHA_DUAL_REAL_GO": str(GO_ROOT / "bin/go"),
                       "PINKHA_DUAL_SOURCE": str(source), "PINKHA_DUAL_BUILD": str(root),
                       "PINKHA_DUAL_MANIFEST": MANIFEST_SHA,
                       "PINKHA_DUAL_GRAPH": str(evidence / "module-graph.log"),
                       "GOPATH": str(root / "go-state"), "GOCACHE": "/Users/m1/caches/anytapy-go1.27.4-build",
                       "GOMODCACHE": "/Users/m1/caches/anytapy-go-mod", "GOFLAGS": "-mod=readonly -p=2",
                       "GOMAXPROCS": "2", "GOMEMLIMIT": "3GiB", "DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer",
                       "PATH": str(tools) + ":" + str(GO_ROOT / "bin") + ":" + os.environ.get("PATH", "")}
        native_files, receipt["nativeDependencies"] = native_dependencies.prepare(root, source, run, environment)
        check_source(source, manifest, native_files)
        graph = run([GO_ROOT / "bin/go", "list", "-m", "-json", "all"], "module-graph", source, environment, 180)
        receipt["actualModuleGraphSHA256"] = digest(graph)
        run([GO_ROOT / "bin/go", "install", "golang.org/x/mobile/cmd/gomobile",
             "golang.org/x/mobile/cmd/gobind"], "install-bind-tools", source, environment, 600)
        run([tools / "gomobile", "init"], "gomobile-init", source, environment, 300)
        heart_version = "pinkha-dual-runtime-v1-" + MANIFEST_SHA
        any_version = "v0.5.0-pinkha.dual.1-" + MANIFEST_SHA
        flags = "-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + heart_version
        flags += " -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + manifest["sourcePins"]["heart"]
        flags += " -X github.com/anyproto/any/internal/version.Version=" + any_version
        flags += " -X github.com/anyproto/any/internal/version.Commit=" + manifest["sourcePins"]["any"]
        flags += " -X github.com/anyproto/any/internal/version.BuildDate=2026-11-25"
        output = root / "Lib.xcframework"
        run([tools / "gomobile", "bind", "-tags", " ".join(manifest["tags"]), "-ldflags", flags,
             "-target=" + ("iossimulator/arm64" if args.slice == "simulator" else "ios/arm64"),
             "-iosversion=" + manifest["deploymentTarget"],
             "-o", output, *manifest["packages"]], "combined-gomobile-bind", source, environment, 3600)
        check_source(source, manifest, native_files)
        info = plistlib.loads((output / "Info.plist").read_bytes())
        libraries = info["AvailableLibraries"]
        require(len(libraries) == 1 and all(x["SupportedArchitectures"] == ["arm64"]
                and x["SupportedPlatform"] == "ios" for x in libraries)
                and {x.get("SupportedPlatformVariant", "device") for x in libraries} == {args.slice},
                "exact_requested_arm64_slice_required")
        artifacts = {}
        for library in libraries:
            directory = output / library["LibraryIdentifier"] / library["LibraryPath"]
            binary = directory / "Lib"
            require(binary.is_file(), "combined_binary_missing")
            raw_sha = digest(binary)
            tantivy_platform = "ios-arm64-sim" if library.get("SupportedPlatformVariant") == "simulator" else "ios-arm64"
            packed = root / ("Lib-with-tantivy-" + tantivy_platform + ".a")
            run(["xcrun", "libtool", "-static", "-o", packed, binary,
                 source / "heart/deps/libs" / tantivy_platform / "libtantivy_go.a"],
                "tantivy-repack-" + tantivy_platform, environment=environment, timeout=180)
            shutil.copyfile(packed, binary)
            symbols = run(["xcrun", "nm", "--no-llvm-bc", "-gU", binary], "symbols-" + library["LibraryIdentifier"], timeout=120).read_text()
            for required in ("ServicePinkhaCaptureLoadedAccountSource", "ServicePinkhaCancelLoadedAccountSourceCapture",
                             "ServicePinkhaValidateLoadedAccountSourceCapture", "ServicePinkhaReleaseLoadedAccountSourceCapture",
                             "ServicePinkhaTorahAuthorizedOperationRead", "ServicePinkhaSemanticAnchorCapture",
                             "MobileStartWithResult", "MobileStopNow", "MobileVersion"):
                require("_" + required in symbols, "combined_export_missing:" + required)
            # Exactly one Go runtime's exported initialization symbols may exist.
            for symbol in ("_crosscall2", "__cgo_wait_runtime_init_done"):
                matches = [line for line in symbols.splitlines() if line.split() and line.split()[-1] == symbol]
                require(len(matches) == 1, "combined_go_runtime_symbol_count:" + symbol)
            artifacts[library["LibraryIdentifier"]] = {
                "rawGoArchiveSHA256": raw_sha, "binarySHA256": digest(binary),
                "binaryBytes": binary.stat().st_size, "tantivyPlatform": tantivy_platform}
        generated = root / "generated-entry.swift"
        generated.write_text("import Foundation\nimport Lib\n"
            "func checkGeneratedEntries() throws {\n"
            "  let version: String = Lib.MobileVersion()\n"
            "  let result = Lib.MobileStartWithResult(\"\", \"\", \"\", \"\", \"\", \"\", \"\")\n"
            "  if let result { let _: Int32 = result.code; let _: String = result.address; let _: String = result.message }\n"
            "  try Lib.MobileStop()\n  Lib.MobileStopNow()\n"
            "  let capture: Data? = try Lib.ServicePinkhaCaptureLoadedAccountSource(\"\", \"\", \"\", \"\", \"\")\n"
            "  let _: Bool = Lib.ServicePinkhaCancelLoadedAccountSourceCapture(\"\", \"\")\n"
            "  _ = try Lib.ServicePinkhaValidateLoadedAccountSourceCapture(\"\", \"\", \"\")\n"
            "  let _: Bool = Lib.ServicePinkhaReleaseLoadedAccountSourceCapture(\"\", \"\")\n"
            "  let _ = Lib.ServicePinkhaTorahAuthorizedOperationRead\n"
            "  let _ = Lib.ServicePinkhaSemanticAnchorCapture\n"
            "  _ = version; _ = capture\n}\n")
        sdk_name = "iphonesimulator" if args.slice == "simulator" else "iphoneos"
        swift_target = "arm64-apple-ios27.0" + ("-simulator" if args.slice == "simulator" else "")
        sdk = run(["xcrun", "--sdk", sdk_name, "--show-sdk-path"], "slice-sdk-path", timeout=30).read_text().strip()
        run(["xcrun", "swiftc", "-typecheck", "-target", swift_target,
             "-sdk", sdk, "-F", output / libraries[0]["LibraryIdentifier"],
             "-module-cache-path", root / "swift-module-cache", generated],
            "generated-actual-swift-entry-typecheck", environment=environment, timeout=180)
        receipt["generatedSwiftEntryCheckSHA256"] = digest(generated)
        receipt.update(status="SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED",
                       heartRuntimeVersion=heart_version, anyRuntimeVersion=any_version,
                       slices=artifacts, nativeLibraryBuildInvocations=1, sourceUnchanged=True)
        framework_files = {}
        for path in sorted(output.rglob("*")):
            if path.is_file():
                framework_files[str(path.relative_to(output))] = {"sha256": digest(path), "bytes": path.stat().st_size}
        write(root / "framework-files.json", framework_files)
        receipt["frameworkInventorySHA256"] = digest(root / "framework-files.json")
        archive = root / "Lib.xcframework.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zipped:
            for path in sorted(output.rglob("*")):
                if path.is_file():
                    zipped.write(path, str(path.relative_to(root)))
        receipt["archiveSHA256"] = digest(archive)
        receipt["archiveBytes"] = archive.stat().st_size
    except BaseException as failure:
        receipt["failure"] = {"type": type(failure).__name__, "message": str(failure)}
        raise
    finally:
        receipt["freeBytesAfter"] = shutil.disk_usage("/System/Volumes/Data").free
        write(evidence / "receipt.json", receipt)
        print(json.dumps({k: receipt.get(k) for k in ("status", "sourceManifestSHA256", "heartRuntimeVersion",
                                                    "anyRuntimeVersion", "archiveSHA256", "failure")}))

if __name__ == "__main__":
    main()
