"""Assemble the two actually qualified 410b slices without another native build."""
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

MANIFEST = "410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9"
BASE = Path("/Users/m1/development/anytype-d-active-20261125")
INPUT = BASE / "native410b"
OUTPUT = BASE / "native410b-combined"
RETENTION = "a3aacb3baf900d15421e42ff7e07292663c01109b3677ee3d458733a81c2bfe7"
PHASES = {
    "simulator": ("ios-arm64-simulator", "160579568aee542356e0e1a2ed90e369f291aa36fb3d8b4b28f842673e93f7f8", "48905b7312d7228fe88a60517ec90c1c23d73f2ada762877c05ace9752103342"),
    "device": ("ios-arm64", "817586f97ab25e4fbed7be48d030ba8f17238baedecb27187e6b807fb03c6050", "cb22fa4733aa2021214f2fc84699ac137cf12cd37c63de0e02585ccd8308925f"),
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

def main():
    require(BASE.resolve() == BASE and INPUT.resolve() == INPUT and not OUTPUT.exists(), "fresh_owned_output_required")
    require(digest(INPUT / "retention.json") == RETENTION, "actual_retention_receipt_changed")
    retained = json.loads((INPUT / "retention.json").read_text())
    require(retained["status"] == "PASS_NATIVE_CRITICAL_ARTIFACTS_AND_COMPLETE_SOURCE_RETAINED_APP_COPY_PENDING_FULL_INVENTORY"
            and len(retained["copied"]) == 2 and not retained["errors"], "both_actual_slice_copies_required")
    OUTPUT.mkdir(mode=0o700)
    result = {"status": "FAIL", "sourceManifestSHA256": MANIFEST, "started": time.time(),
              "controllerSHA256": digest(Path(__file__)), "retentionReceiptSHA256": RETENTION,
              "applicationBuilds": 0, "nativeLibraryBuildsNow": 0, "testsExecutedNow": 0,
              "physicalDeviceAcceptance": False, "inputs": {}}
    try:
        frameworks = []
        for phase, (identifier, receipt_sha, library_sha) in PHASES.items():
            root = INPUT / phase
            path = root / "evidence/receipt.json"
            require(digest(path) == receipt_sha, "original_slice_receipt_changed")
            proof = json.loads(path.read_text())
            require(proof["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
                    and proof["sourceManifestSHA256"] == MANIFEST and proof["sourceUnchanged"] is True
                    and proof["sourceFilesVerified"] == 4855 and proof["independentGoRuntimeCount"] == 1
                    and proof["nativeLibraryBuildInvocations"] == 1 and proof["slicePhase"] == phase
                    and proof["controllerCommit"] == "2a96048023569ec27a02fe1fdb1127bd702ee10c"
                    and not proof.get("failure") and all(x["exitCode"] == 0 for x in proof["commands"]),
                    "actual_slice_not_qualified")
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
            require(digest(INPUT / phase / "evidence/receipt.json") == receipt_sha
                    and inventory(INPUT / phase / "Lib.xcframework" / identifier / "Lib.framework")
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
