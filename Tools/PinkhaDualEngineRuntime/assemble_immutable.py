"""Assemble the two actually qualified 11619 slices without another native build."""
from pathlib import Path
import hashlib
import json
import os
import plistlib
import shutil
import signal
import subprocess
import time
import zipfile

MANIFEST = "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
BASE = Path("/Users/m1/development/anytype-d-active-20261125")
INPUT = BASE / "native-immutable-retry1"
OUTPUT = BASE / "native11619-combined"
RETENTIONS = {
    "simulator": "44dd8248b245a588407011d7f70cfc59c592586355add8c16f502aabe983aec6",
    "device": "dba9ab48e9607fa0a9ba1829c883fba10121faf82f064bf9d61ba90a3e211e09",
}
SOURCE_MANIFEST = Path(__file__).with_name("source-immutable-manifest.json")
PHASES = {
    "simulator": ("ios-arm64-simulator", "aa9320f43659d56fe7f366ad6a77943a296f0fe55e545ff2e6516dafbde91e49", "9f64b4469e221cd27b04c0f46b7479cf1fb079b36fce8a26c0fd8b0521ecaf5e"),
    "device": ("ios-arm64", "f71d7d1108e427d79790c4e3bb99cd7667b7d62397cabe1ac53e0a7fd48c9f33", "539a8d5e1b888dddb423261002011db39b7ca7c15718ff4aaa7658ec18aaedaf"),
}

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):
            h.update(data)
    return h.hexdigest()

def write(path, value):
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

def inventory(root):
    out = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "unexpected_framework_symlink")
        if path.is_file():
            out[str(path.relative_to(root))] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    return out

def verify_original_source(root, manifest):
    for relative, expected in manifest["files"].items():
        path = root / relative
        require(path.is_file() and not path.is_symlink() and path.resolve() == path
                and path.stat().st_size == expected["bytes"] and digest(path) == expected["sha256"],
                "original_native_source_changed:" + relative)

def main():
    require(BASE.resolve() == BASE and INPUT.resolve() == INPUT and not OUTPUT.exists(), "fresh_owned_output_required")
    require(digest(SOURCE_MANIFEST) == MANIFEST, "original_native_source_manifest_changed")
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    require(len(manifest["files"]) == 4862, "complete_original_native_source_required")
    retained = {}
    for phase, expected_sha in RETENTIONS.items():
        folder = INPUT / (phase + "-original-retention1")
        path = folder / "retention.json"
        require(digest(path) == expected_sha, "actual_retention_receipt_changed")
        item = json.loads(path.read_text())
        require(item["status"] == "PASS_EXACT_ORIGINAL_" + phase.upper() + "_SOURCE_DEPENDENCIES_PRODUCTS_AND_COMMANDS_RETAINED"
                and item["allOriginalsUnchanged"] is True
                and item["originalReceiptSHA256"] == PHASES[phase][1]
                and item["nativeBuildsNow"] == 0 and item["testsNow"] == 0
                and item["appleApplicationAcceptance"] is False
                and digest(folder / "members-before.json") == item["memberInventorySHA256"]
                and digest(Path(item["archive"])) == item["archiveSHA256"]
                and Path(item["archive"]).stat().st_size == item["archiveBytes"],
                "exact_original_slice_retention_required")
        retained[phase] = {"receiptSHA256": expected_sha, "archiveSHA256": item["archiveSHA256"],
                           "members": item["members"]}
    OUTPUT.mkdir(mode=0o700)
    result = {"status": "FAIL", "sourceManifestSHA256": MANIFEST, "started": time.time(),
              "controllerSHA256": digest(Path(__file__)), "originalRetention": retained,
              "applicationBuilds": 0, "nativeLibraryBuildsNow": 0, "testsExecutedNow": 0,
              "physicalDeviceAcceptance": False, "inputs": {}}
    try:
        frameworks = []
        for phase, (identifier, receipt_sha, library_sha) in PHASES.items():
            root = INPUT / ("pinkha-dual-native-v1-11619a9928d6-" + phase)
            path = root / "evidence/receipt.json"
            require(digest(path) == receipt_sha, "original_slice_receipt_changed")
            proof = json.loads(path.read_text())
            require(proof["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
                    and proof["sourceManifestSHA256"] == MANIFEST and proof["sourceUnchanged"] is True
                    and proof["sourceFilesVerified"] == 4862 and proof["independentGoRuntimeCount"] == 1
                    and proof["nativeLibraryBuildInvocations"] == 1 and proof["slicePhase"] == phase
                    and proof["controllerCommit"] == "ae86c032c93c1e6040e7c76fab6a7f05b913dc36"
                    and proof["controllerSHA256"] == "f9249a0238b32680f4f4d7ca58b9ab04da4de1c7ad30f4e4200214ab0b7e8aa2"
                    and not proof.get("failure") and all(x["exitCode"] == 0 for x in proof["commands"]),
                    "actual_slice_not_qualified")
            verify_original_source(root / "source", manifest)
            for command in proof["commands"]:
                require(digest(root / "evidence" / (command["name"] + ".log")) == command["logSHA256"],
                        "original_slice_command_log_changed")
            require(digest(root / "framework-files.json") == proof["frameworkInventorySHA256"],
                    "original_framework_inventory_changed")
            expected = json.loads((root / "framework-files.json").read_text())
            require(inventory(root / "Lib.xcframework") == expected, "actual_framework_bytes_changed")
            framework = root / "Lib.xcframework" / identifier / "Lib.framework"
            require(digest(framework / "Lib") == library_sha, "exact_native_binary_required")
            require(proof["heartRuntimeVersion"] == "pinkha-dual-runtime-v1-" + MANIFEST
                    and proof["anyRuntimeVersion"] == "v0.5.0-pinkha.dual.1-" + MANIFEST,
                    "coherent_runtime_versions_required")
            result["inputs"][phase] = {"root": str(root), "originalReceiptSHA256": receipt_sha,
                "binarySHA256": library_sha, "binaryBytes": (framework / "Lib").stat().st_size,
                "frameworkFiles": inventory(framework)}
            frameworks.append(framework)
        argv = ["/usr/bin/xcodebuild", "-create-xcframework"]
        for framework in frameworks:
            argv.extend(["-framework", str(framework)])
        argv.extend(["-output", str(OUTPUT / "Lib.xcframework")])
        env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
        with (OUTPUT / "create-xcframework.log").open("xb") as log:
            process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            command = {"argv": argv, "pid": process.pid, "pgid": process.pid, "started": time.time()}
            write(OUTPUT / "create-xcframework.started.json", command)
            try:
                command["exitCode"] = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                command["stopReason"] = "OWNED_ASSEMBLY_TIMEOUT"
                for signum in (signal.SIGTERM, signal.SIGKILL):
                    if process.poll() is not None:
                        break
                    try:
                        os.killpg(process.pid, signum)
                        process.wait(timeout=10)
                    except ProcessLookupError:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        continue
                    except PermissionError as error:
                        command["cleanupError"] = {"type": type(error).__name__, "reason": str(error)}
                        break
                raise
            finally:
                command["exitCode"] = process.poll()
                command["elapsedSeconds"] = time.time() - command["started"]
                command["logSHA256"] = digest(OUTPUT / "create-xcframework.log")
                write(OUTPUT / "create-xcframework.result.json", command)
        require(command["exitCode"] == 0, "actual_assembly_tool_failed")
        info = plistlib.loads((OUTPUT / "Lib.xcframework/Info.plist").read_bytes())
        rows = {x["LibraryIdentifier"]: x for x in info["AvailableLibraries"]}
        require(set(rows) == {x[0] for x in PHASES.values()}, "exact_two_platform_slices_required")
        for phase, (identifier, _, _) in PHASES.items():
            row = rows[identifier]
            require(row["LibraryPath"] == "Lib.framework" and row["SupportedArchitectures"] == ["arm64"]
                    and row["SupportedPlatform"] == "ios"
                    and row.get("SupportedPlatformVariant", "device") == phase, "output_platform_changed")
            require(inventory(OUTPUT / "Lib.xcframework" / identifier / "Lib.framework") == result["inputs"][phase]["frameworkFiles"],
                    "assembled_framework_changed")
        files = inventory(OUTPUT / "Lib.xcframework")
        write(OUTPUT / "framework-files.json", files)
        archive = OUTPUT / "Lib.xcframework.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zipped:
            for relative in files:
                path = OUTPUT / "Lib.xcframework" / relative
                zipped.write(path, str(path.relative_to(OUTPUT)))
        for phase, (identifier, receipt_sha, _) in PHASES.items():
            verify_original_source(INPUT / ("pinkha-dual-native-v1-11619a9928d6-" + phase) / "source", manifest)
            require(digest(INPUT / ("pinkha-dual-native-v1-11619a9928d6-" + phase) / "evidence/receipt.json") == receipt_sha
                    and inventory(INPUT / ("pinkha-dual-native-v1-11619a9928d6-" + phase) / "Lib.xcframework" / identifier / "Lib.framework")
                        == result["inputs"][phase]["frameworkFiles"], "original_input_changed_after_assembly")
        result.update(status="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE",
                      inputFrameworksUnchangedAfter=True,
                      archiveSHA256=digest(archive), archiveBytes=archive.stat().st_size,
                      frameworkInventorySHA256=digest(OUTPUT / "framework-files.json"),
                      heartRuntimeVersion="pinkha-dual-runtime-v1-" + MANIFEST,
                      anyRuntimeVersion="v0.5.0-pinkha.dual.1-" + MANIFEST)
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "reason": str(error)}
        raise
    finally:
        result["finished"] = time.time()
        result["freeBytesAfter"] = shutil.disk_usage("/System/Volumes/Data").free
        write(OUTPUT / "receipt.json", result)
        print(json.dumps({k: result.get(k) for k in ("status", "archiveSHA256", "archiveBytes", "failure")}))

if __name__ == "__main__":
    main()
