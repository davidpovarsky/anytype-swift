"""Assemble the two actually qualified 8ac permission-qualified slices without another native build."""
from pathlib import Path
import hashlib
import json
import importlib.util
import os
import plistlib
import shutil
import signal
import subprocess
import time
import zipfile

MANIFEST = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
BASE = Path("/Users/m1/development/anytype-d-active-20261125")
INPUT = BASE / "native-permission8ac"
OUTPUT = BASE / "native8ac-combined"
RETENTIONS = {
    "simulator": "52a02c34a90ca4ad84dff7e27c6255fd01861c7905dd7aea8bea4b01a77e8738",
    "device": "6ad534380b0fb5f9cd2092782437a32808157efc902785c18484f037c8829567",
}
SOURCE_MANIFEST = Path(__file__).with_name("source-permission-manifest.json")
PHASES = {
    "simulator": ("ios-arm64-simulator", "946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b", "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763"),
    "device": ("ios-arm64", "c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208", "8592fb526b8796b3e118f1a18bacc276e89894459207d5df294b17b0c3859c50"),
}

EVIDENCE = {"simulator": "evidence", "device": "evidence-gateway-invocation-resume-1"}
CONTROLLERS = {
    "simulator": ("e185fd77f691c08b9e59ad3a4fbb8ab2a4e703f9", "cb9477dc383ada4ab5d2361ca5105ff9c7c18f1d1db6d861f034b91f48337077"),
    "device": ("04f501a166a2feb62ee57a09803b77c5dc8c601c", "e993303f60619afb05bb65449ea73253365e9e0e446339a9f7b0ba586742866a"),
}
IDENTITY_HELPER_SHA = "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0"
HTTP_QUALIFICATION_SHA = "d50faf7ce50c6c418b8cc55dd7e46d86aa1a9d5783819b0b943e74c3ddb09da0"
PRIOR_DEVICE_REFUSAL = "c33de905244e6f77d94f9491d4930e8aa4b1445547b5c8b9c73ebb812e61f9dc"

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
    manifest_bytes = SOURCE_MANIFEST.read_bytes()
    require(hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST, "original_native_source_manifest_changed")
    manifest = json.loads(manifest_bytes)
    require(len(manifest["files"]) == 4868, "complete_original_native_source_required")
    helper = Path(__file__).with_name("runtime_identity.py")
    require(digest(helper) == IDENTITY_HELPER_SHA, "original_runtime_identity_helper_changed")
    specification = importlib.util.spec_from_file_location("qualified_8ac_runtime_identity", helper)
    runtime = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(runtime)
    identity = runtime.identity(manifest_bytes, "2026-11-26")
    retained = {}
    for phase, expected_sha in RETENTIONS.items():
        folder = INPUT / (phase + "-original-retention1")
        path = folder / "retention.json"
        require(digest(path) == expected_sha, "actual_retention_receipt_changed")
        item = json.loads(path.read_text())
        require(item["status"] == "PASS_ORIGINAL_STREAM_AND_SOURCE_UNCHANGED"
                and item["sourceManifestSHA256"] == MANIFEST and item["sourceFiles"] == 4868
                and item["allOriginalsUnchanged"] is True
                and item["originalReceiptSHA256"] == PHASES[phase][1]
                and item["nativeBuildsNow"] == 0 and item["testsNow"] == 0
                and item["appleApplicationAcceptance"] is False
                and digest(folder / "members-before.json") == item["memberInventorySHA256"]
                and (folder / "members-before.json").read_bytes() == (folder / "members-after.json").read_bytes()
                and digest(INPUT / "original-archives" / (phase + "8ac-originals.tar.gz")) == item["archiveSHA256"]
                and (INPUT / "original-archives" / (phase + "8ac-originals.tar.gz")).stat().st_size == item["archiveBytes"],
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
            root = INPUT / ("pinkha-dual-native-v1-8ac407e75a4b-" + phase)
            path = root / EVIDENCE[phase] / "receipt.json"
            require(digest(path) == receipt_sha, "original_slice_receipt_changed")
            proof = json.loads(path.read_text())
            require(proof["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
                    and proof["sourceManifestSHA256"] == MANIFEST and proof["sourceUnchanged"] is True
                    and proof["sourceFilesVerified"] == 4868 and proof["independentGoRuntimeCount"] == 1
                    and proof["nativeLibraryBuildInvocations"] == 1 and proof["slicePhase"] == phase
                    and (proof["controllerCommit"], proof["controllerSHA256"]) == CONTROLLERS[phase]
                    and not proof.get("failure") and all(x["exitCode"] == 0 for x in proof["commands"]),
                    "actual_slice_not_qualified")
            command_path = root / EVIDENCE[phase] / "combined-gomobile-bind.command.json"
            command_bytes = command_path.read_bytes()
            bind_rows = [row for row in proof["commands"] if row["name"] == "combined-gomobile-bind"]
            require(len(bind_rows) == 1 and json.loads(command_bytes) == bind_rows[0],
                    "actual_bind_command_must_equal_original_receipt_row")
            runtime_proof = runtime.qualify_slice(
                path.read_bytes(), command_bytes,
                (root / EVIDENCE[phase] / "combined-gomobile-bind.log").read_bytes(),
                manifest_bytes, identity, phase)
            require(proof["runtimeIdentity"] == identity
                    and proof["fullAnyRuntimeVersion"] == identity["anyRuntimeVersion"]
                    and proof["runtimeIdentityHelperSHA256"] == IDENTITY_HELPER_SHA
                    and proof["nativeHTTPQualificationSHA256"] == "b8694dbd2ac3facce43771bdb7f206461d1b95924a5ccb1248114185a394ce1d"
                    and proof["nativeHTTPQualification"]["sourceQualificationSHA256"] == HTTP_QUALIFICATION_SHA,
                    "full_actual_native_identity_and_real_HTTP_qualification_required")
            if phase == "device":
                require(proof["originalGatewayInvocationRefusalSHA256"] == PRIOR_DEVICE_REFUSAL
                        and digest(root / "evidence/receipt.json") == PRIOR_DEVICE_REFUSAL,
                        "original_zero_bind_gateway_refusal_must_remain_preserved")
            verify_original_source(root / "source", manifest)
            for command in proof["commands"]:
                require(digest(root / EVIDENCE[phase] / (command["name"] + ".log")) == command["logSHA256"],
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
                "frameworkFiles": inventory(framework), "runtimeIdentityQualification": runtime_proof}
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
            verify_original_source(INPUT / ("pinkha-dual-native-v1-8ac407e75a4b-" + phase) / "source", manifest)
            require(digest(INPUT / ("pinkha-dual-native-v1-8ac407e75a4b-" + phase) / EVIDENCE[phase] / "receipt.json") == receipt_sha
                    and inventory(INPUT / ("pinkha-dual-native-v1-8ac407e75a4b-" + phase) / "Lib.xcframework" / identifier / "Lib.framework")
                        == result["inputs"][phase]["frameworkFiles"], "original_input_changed_after_assembly")
        result.update(status="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE",
                      inputFrameworksUnchangedAfter=True,
                      archiveSHA256=digest(archive), archiveBytes=archive.stat().st_size,
                      frameworkInventorySHA256=digest(OUTPUT / "framework-files.json"),
                      heartRuntimeVersion="pinkha-dual-runtime-v1-" + MANIFEST,
                      anyRuntimeVersion="v0.5.0-pinkha.dual.1-" + MANIFEST,
                      fullAnyRuntimeVersion=identity["anyRuntimeVersion"], runtimeIdentity=identity)
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
