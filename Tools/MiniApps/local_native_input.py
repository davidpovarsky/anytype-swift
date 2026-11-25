"""Admit the actual current unified native slices without borrowing SDK/UI credit."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import subprocess

from local_execution import digest, git, read_exact, require, write

MANIFEST = "70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72"


def file_row(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased actual native input: " + str(path))
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def exact_files(root, expected):
    root = Path(root)
    actual = {}
    require(root.is_dir() and root.resolve() == root, "Native input root is absent or aliased")
    for p in sorted(root.rglob("*")):
        require(not p.is_symlink(), "Native framework contains an unreviewed alias")
        if p.is_file():
            actual[p.relative_to(root).as_posix()] = file_row(p)
    require(actual == expected, "Complete native framework membership/bytes differ")
    return actual


def validate_receipts(policy, native, stopped, union, wrapper):
    require(policy.get("schema") == "miniapps.original-local-native/2"
            and policy.get("source_manifest_sha256") == MANIFEST,
            "Unreviewed actual unified native source")
    require(native.get("status") == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
            and native.get("executionKind") == "local-mac"
            and native.get("sourceUnchanged") is True
            and native.get("sourceFilesVerified") == 4855
            and native.get("independentGoRuntimeCount") == 1
            and native.get("applicationBuilds") == native.get("appleTestsExecuted")
                == native.get("nativeAcceptanceTestsExecuted") == 0,
            "Native input scope is not its actual source-only Apple build")
    require(native.get("sourceManifestSHA256") == stopped.get("sourceManifestSHA256") == MANIFEST
            and native.get("sourcePins") == stopped.get("sourcePins") == policy["source_pins"]
            and native.get("sourceArchiveSHA256") == policy["source_archive_sha256"],
            "Native source manifest/archive/pins differ")
    require(stopped.get("status") == "FAIL"
            and stopped.get("failure", {}).get("message") == "gateway_and_apple_native_module_graphs_differ"
            and native.get("originalPreparationStopReceiptSHA256")
                == policy["original_build_receipt"]["sha256"],
            "Original failed preparation history must remain intact")
    require(native.get("verifiedGatewayMetadataHydration", {}).get("unchangedModuleIdentities") == 760
            and native["verifiedGatewayMetadataHydration"]["hydratedGraphSHA256"]
                == native["actualModuleGraphSHA256"],
            "Native graph correction lost its original module identity proof")
    commands = {row["name"]: row for row in native["commands"]}
    require(len(commands) == len(native["commands"])
            and {"combined-gomobile-bind", "generated-actual-swift-entry-typecheck",
                 "symbols-ios-arm64-simulator", "tantivy-repack-ios-arm64-sim"} <= commands.keys()
            and all(row["exitCode"] == 0 and row["status"] == "PASS_EXIT_0"
                    for row in commands.values())
            and "-target=iossimulator/arm64" in commands["combined-gomobile-bind"]["argv"],
            "Actual native compiler/ABI commands did not succeed")
    require(native["slices"]["ios-arm64-simulator"]["binarySHA256"] == policy["binary_sha256"]
            and native["archiveSHA256"] == policy["archive_sha256"]
            and native["frameworkInventorySHA256"] == policy["framework_inventory"]["sha256"],
            "Native output identity differs")
    require(union.get("status") == "PASS_INDEPENDENT_EXACT_SLICE_ASSEMBLY_NOT_APP_BUILD"
            and union.get("allPayloadBytesEqualOriginalSlices") is True
            and union.get("metadataEqualsExactOriginalUnion") is True
            and union.get("sourceManifestSHA256") == MANIFEST
            and union.get("frameworkInventorySHA256") == policy["assembly_inventory"]["sha256"]
            and union.get("appTestsExecuted") == union.get("appleBuildsRepeated") == 0,
            "Original native slice union is not its exact observed assembly")
    require(union["slices"]["ios-arm64-simulator"]["producerReceiptSHA256"]
                == policy["abi_receipt"]["sha256"]
            and union["slices"]["ios-arm64-simulator"]["binarySHA256"] == policy["binary_sha256"],
            "Native simulator slice lost its actual producer")
    require(wrapper.get("status") == "PASS_ORIGINAL_PRODUCTION_WRAPPERS_TYPECHECK_ONLY"
            and wrapper.get("returncode") == 0 and wrapper.get("framework_unchanged") is True
            and wrapper.get("application_tests_executed") == 0
            and wrapper.get("native_manifest") == MANIFEST
            and wrapper.get("native_build_receipt_sha256") == policy["abi_receipt"]["sha256"]
            and wrapper.get("source_sha") == policy["wrapper_source_sha"],
            "Current original production Swift wrappers have not passed their actual gate")
    require(native["heartRuntimeVersion"] == "pinkha-dual-runtime-v1-" + MANIFEST
            and native["anyRuntimeVersion"] == "v0.5.0-pinkha.dual.1-" + MANIFEST,
            "Original native runtime markers differ")
    return commands


def admit(app, evidence, policy, policy_sha256):
    app, evidence = Path(app), Path(evidence)
    root, assembly = Path(policy["root"]), Path(policy["assembly_root"])
    require(root.is_absolute() and root.resolve() == root
            and assembly.is_absolute() and assembly.resolve() == assembly,
            "Original native producer roots are aliased")
    native = read_exact(root, policy["abi_receipt"])
    stopped = read_exact(root, policy["original_build_receipt"])
    union = read_exact(assembly, policy["assembly_receipt"])
    wrapper_root = Path(policy["wrapper_root"])
    wrapper = read_exact(wrapper_root, policy["wrapper_receipt"])
    commands = validate_receipts(policy, native, stopped, union, wrapper)
    manifest_path = root / "source/source-manifest.json"
    require(digest(manifest_path) == MANIFEST
            and digest(root / "native-source.tar.gz") == policy["source_archive_sha256"]
            and digest(root / "Lib.xcframework.zip") == policy["archive_sha256"],
            "Original native source/archive bytes changed")
    source = json.loads(manifest_path.read_text())
    require(len(source["files"]) == native["sourceFilesVerified"]
            and source["sourcePins"] == policy["source_pins"], "Original source inventory differs")
    for name, row in source["files"].items():
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts
                and str(relative) == name, "Native source inventory escapes its root")
        require(file_row(root / "source" / name) == row, "Native source bytes changed: " + name)
    for name, row in commands.items():
        require(digest(root / "evidence-gateway-resume-1" / (name + ".log")) == row["logSHA256"],
                "Original native command log differs: " + name)
    simulator_files = read_exact(root, policy["framework_inventory"])
    exact_files(root / "Lib.xcframework", simulator_files)
    installed_files = read_exact(assembly, policy["assembly_inventory"])
    actual = exact_files(app / "Dependencies/Middleware/Lib.xcframework", installed_files)
    # Full union metadata and both original payloads stay intact. This grants no
    # physical signing or device execution, and does not build a second Go copy.
    metadata = plistlib.loads((app / "Dependencies/Middleware/Lib.xcframework/Info.plist").read_bytes())
    require({row["LibraryIdentifier"] for row in metadata["AvailableLibraries"]}
            == {"ios-arm64", "ios-arm64-simulator"}, "Original native slice union changed")
    for slice_name, original in union["slices"].items():
        path = Path(original["producerReceipt"])
        require(path.resolve() == path and digest(path) == original["producerReceiptSHA256"],
                "An original native slice receipt changed")
        receipt = json.loads(path.read_text())
        require(receipt["sourceManifestSHA256"] == MANIFEST
                and receipt["status"] == "SOURCE_VERIFIED_SINGLE_GO_RUNTIME_APPLE_SLICE_BUILT_NOT_ACCEPTED"
                and receipt["independentGoRuntimeCount"] == 1
                and receipt["slices"][slice_name]["binarySHA256"] == original["binarySHA256"],
                "Native slice identity differs from the original compiled source")
        original_root = path.parent.parent
        expected_payload = {name[len(slice_name) + 1:]: row for name, row in actual.items()
                            if name.startswith(slice_name + "/")}
        exact_files(original_root / "Lib.xcframework" / slice_name, expected_payload)
    for name, row in wrapper["source_files"].items():
        require(name.startswith("Modules/ProtobufMessages/Sources/")
                and file_row(app / name) == row, "Original production wrapper source changed")
        committed = subprocess.check_output(["git", "-c", "gc.auto=0", "-C", str(app),
                                             "show", policy["wrapper_source_sha"] + ":" + name])
        require(hashlib.sha256(committed).hexdigest() == row["sha256"],
                "Wrapper check lost its original committed source")
    for stream in ("stdout", "stderr"):
        require(digest(wrapper_root / (stream + ".log")) == wrapper[stream + "_sha256"],
                "Original production wrapper compiler output differs")
    require(not __import__("os").environ.get("PINKHA_NATIVE_T2_AUTHORIZED_READ_FIXTURE"),
            "The original application cannot substitute a fixture native library")
    installation = {
        "status": "VERIFIED_EXACT_NATIVE_INPUT_APP_ACCEPTANCE_PENDING",
        "execution_origin": "local-mac", "github_run_id": None,
        "source_sha": git(app, "rev-parse", "HEAD"), "policy_sha256": policy_sha256,
        "native_source_manifest_sha256": MANIFEST,
        "abi_receipt_sha256": policy["abi_receipt"]["sha256"],
        "original_failed_receipt_sha256": policy["original_build_receipt"]["sha256"],
        "production_wrapper_receipt_sha256": policy["wrapper_receipt"]["sha256"],
        "assembly_receipt_sha256": policy["assembly_receipt"]["sha256"],
        "native_framework_files": actual, "original_native_acceptance_tests": 0,
        "current_native_tests_executed": 0, "original_editor_sdk_abi_reused": False}
    binding = {"runtime_profile": policy["runtime_profile"],
               "native_marker": "pinkha-dual-runtime-v1-" + MANIFEST,
               "native_source_manifest_sha256": MANIFEST, "native_binary_sha256": policy["binary_sha256"],
               "native_abi_receipt_sha256": policy["abi_receipt"]["sha256"],
               "independent_go_runtime_count": 1, "execution_origin": "local-mac"}
    write(evidence / "local-native-input.json", installation)
    return installation, binding
