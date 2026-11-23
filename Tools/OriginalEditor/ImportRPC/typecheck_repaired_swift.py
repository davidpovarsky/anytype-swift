#!/usr/bin/env python3
"""Typecheck the actual corrected Swift primary files with the original SDK.

Reuse immutable actual generator output and the actual built SwiftProtobuf module.
No generator, dependency build, Go/native test or whole SDK build is performed.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import sys
import time
import zipfile

sys.dont_write_bytecode = True
PACKET = "docs/pinkha/torah-integration/native-annotation-import-rpc-generation-20261123"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def authenticate_generation(control, work, evidence, pin, commands, support, intake, repair):
    expected = pin["generation"]
    metadata = {}
    for kind, endpoint in (("run", "actions/runs/" + str(expected["run_id"])),
                           ("artifact", "actions/artifacts/" + str(expected["artifact_id"]))):
        path = commands.require("actual-generation-" + kind,
            ["gh", "api", "repos/" + pin["repository"] + "/" + endpoint], control, 60)
        metadata[kind] = json.loads(path.read_bytes())
    run, artifact = metadata["run"], metadata["artifact"]
    require(run["id"] == expected["run_id"] and run["head_sha"] == expected["head_sha"]
        and run["head_branch"] == expected["head_branch"] and run["path"] == expected["workflow_path"]
        and run["run_attempt"] == 1 and run["event"] == "push" and run["status"] == "completed"
        and run["conclusion"] == "failure" and run["repository"]["full_name"] == pin["repository"],
        "Actual generation run identity/outcome differs")
    require(artifact["id"] == expected["artifact_id"] and artifact["name"] == expected["artifact_name"]
        and artifact["size_in_bytes"] == expected["artifact_bytes"] and not artifact["expired"]
        and artifact["digest"] == "sha256:" + expected["artifact_sha256"]
        and artifact["workflow_run"]["id"] == expected["run_id"]
        and artifact["workflow_run"]["head_sha"] == expected["head_sha"],
        "Actual generation artifact differs")
    archive = commands.require("download-actual-generation",
        ["gh", "api", "repos/" + pin["repository"] + "/actions/artifacts/" + str(expected["artifact_id"]) + "/zip"],
        control, 240)
    root = work / "actual-generation"
    receipt = intake.unpack(archive, root, expected)
    require(receipt == {"crc_members": 1607, "indexed_files": 1606}, "Generation evidence closure differs")
    result = json.loads((root / "RESULT.json").read_bytes())
    recorded = json.loads((root / "COMMANDS.json").read_bytes())
    require(result["schema"] == "otzaria.original-import-rpc-cancel-generation-result/1"
        and result["status"] == "FAIL" and result["control_head"] == expected["head_sha"]
        and result["manifest_sha256"] == pin["generation_manifest_sha256"]
        and result["qualification_pin_sha256"] == pin["generation_pin_sha256"]
        and result["native_source_tree"] == pin["generated_native_tree"]
        and result["error"] == "owned command failed: typecheck-changed-original-swift-primary-files"
        and result["generator_native_invocations"] == 1 and result["generator_swift_invocations"] == 2
        and result["generator_documentation_invocations"] == 1
        and result["original_filesplit_invocations"] == 1 and result["original_sourcery_invocations"] == 1
        and result["swift_typecheck_invocations"] == 1 and result["owned_command_groups_drained"]
        and result["owned_work_removed"] and result["cleanup"]["removed"]
        and not result["new_rpc_controls"] and result.get("new_rpc_control_passes", 0) == 0
        and result["rpc_controls"] == {"status": "NOT_RUN", "passes": 0, "failures": 0, "not_run": 9}
        and result["generated_cancel_panic_control"] ==
            {"status": "NOT_RUN", "passes": 0, "failures": 0, "not_run": 1},
        "Actual generation/typecheck failure boundary differs")
    require(len(recorded) == result["commands"] == 42
        and all(c["effective_returncode"] == 0 and not c["timed_out"] for c in recorded[:-1])
        and recorded[-1]["effective_returncode"] == 1 and not recorded[-1]["timed_out"]
        and recorded[-1]["label"] == "typecheck-changed-original-swift-primary-files",
        "Actual original generator command closure differs")
    require(support.sha(root / recorded[-1]["stderr"]) == expected["failed_swift_stderr_sha256"],
        "Actual missing-SDK diagnostic differs")
    for command in recorded:
        for field in ("stdout", "stderr"):
            require(support.sha(root / command[field]) == command[field + "_sha256"],
                    "Recorded generation command log differs")
    require(support.sha(root / "GENERATED_OUTPUT_INDEX.json") == pin["generated_index_sha256"],
            "Actual generated output index differs")
    generated = json.loads((root / "GENERATED_OUTPUT_INDEX.json").read_bytes())
    generation_pin = json.loads((control / pin["generation_pin_path"]).read_bytes())
    prior_archive = root / "05-download-actual-continuation.stdout"
    require(support.sha(prior_archive) == generation_pin["artifact_sha256"],
            "Previously authenticated original generation archive differs")
    with zipfile.ZipFile(prior_archive) as zipped:
        old_index = json.loads(zipped.read("EVIDENCE_INDEX.json"))["files"]
        record = next(r for r in old_index if r["path"] == "GENERATED_OUTPUT_INDEX.json")
        raw = zipped.read(record["path"])
        require(repair.bytes_row(raw, record["path"]) == record, "Original generated index bytes differ")
        before = json.loads(raw)
    delta = repair.validate_output_delta(before, generated, generation_pin["allowed_generated_deltas"])
    require(delta == json.loads((root / "CANCEL_ERROR_GENERATED_DELTA.json").read_bytes())["deltas"],
            "Actual original generated delta differs")
    for family, rows in generated.items():
        prefix = root / "generated/candidate" / ("native" if family == "native" else "swift")
        support.check_rows(prefix, rows)
    final = json.loads((root / "FAILURE_OUTPUT_INDEX.json").read_bytes())["roots"]
    require(final["native"] == generated["native"]
        and final["swift"] == sorted(generated["swift"] + generated["middleware"], key=lambda r:r["path"]),
        "Actual final generated output stability differs")
    for family, rows in final.items():
        support.check_rows(root / "failure-time" / family, rows)
    boundary = json.loads((root / "NATIVE_BOUNDARY_qualification-final.json").read_bytes())
    require(not boundary["changed_paths"] and not boundary["outside_generated_outputs"] and not boundary["rows"],
            "Actual native source changed after generation")
    support.check_rows(root / "schema-source", [generation_pin["schema_transform"]["after"]])
    write = intake.write
    write(evidence / "AUTHENTICATED_GENERATION.json",
        {"metadata": metadata, "intake": receipt, "result": result,
         "generation_commands": [c for c in recorded if c["label"] in (
            "original-protoc-changed-go-commands", "original-proto-documentation",
            "original-protoc-changed-raw-swift", "original-protoc-changed-swift-models",
            "original-split-changed-commands", "original-generate-changed-error-localization")],
         "all_744_outputs_stable": True, "native_unstaged_changes": [],
         "aggregate_outcome_preserved": "FAIL at missing-SDK Swift invocation"})
    return root, generated, generation_pin

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control-root", "control-head", "pin", "pin-sha256", "work", "evidence"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    work, evidence = [(control / value).resolve() for value in (args.work, args.evidence)]
    require(work.is_relative_to(control / "build") and evidence.is_relative_to(control / "build")
        and work != evidence and not work.is_relative_to(evidence) and not evidence.is_relative_to(work),
        "Owned Swift qualification roots escape or overlap")
    support = load(control / PACKET / "generation_support.py", "frozen_generation_support")
    intake = load(control / "Tools/OriginalEditor/ImportRPC/artifact_intake.py", "generation_intake")
    compiler = load(control / "Tools/OriginalEditor/ImportRPC/compiler_inputs.py", "owned_cleanup")
    repair = load(control / "Tools/OriginalEditor/ImportRPC/repair_cancel_schema.py", "original_schema_validation")
    pin_path = (control / args.pin).resolve()
    require(pin_path.is_relative_to(control) and support.sha(pin_path) == args.pin_sha256, "Exact Swift proof pin differs")
    pin = json.loads(pin_path.read_bytes())
    require(pin["schema"] == "otzaria.original-import-rpc-swift-sdk-pin/1", "Swift proof schema differs")
    for entry in pin["execution_tools"]:
        support.check_rows(control, [entry])
    require(support.sha(control / pin["generation_pin_path"]) == pin["generation_pin_sha256"],
            "Exact generation source pin differs")
    support.admit_packet(control / PACKET, pin["generation_manifest_sha256"])
    retained = control / PACKET / "retained-original"
    helper = support.load_module(retained / "run_native_defaults_repair.py", "shared_owned_commands", support.COMMAND_HELPER_SHA)
    evidence.mkdir(parents=True, exist_ok=False)
    commands = helper.Commands(evidence, os.environ.copy(), args.job_deadline_unix - 120)
    result = {"schema": "otzaria.original-import-rpc-changed-swift-sdk-typecheck/1",
        "status": "NOT_STARTED", "control_head": args.control_head, "pin_sha256": args.pin_sha256,
        "generation_run": pin["generation"]["run_id"], "generation_source": pin["generation"]["head_sha"],
        "generation_artifact_sha256": pin["generation"]["artifact_sha256"],
        "generated_native_tree": pin["generated_native_tree"],
        "generated_index_sha256": pin["generated_index_sha256"],
        "generator_invocations": 0, "dependency_builds": 0, "swift_typecheck_invocations": 0,
        "rpc_controls": "NOT_RUN; separate union owner", "native_tests": 0,
        "full_sdk_typechecked": False, "mobile_abi_built": False}
    owned, marker = False, None
    def interrupted(signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt("Swift qualification interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        require(0 < args.job_deadline_unix - time.time() <= 3600, "Invalid finite Swift deadline")
        require(platform.system() == "Darwin" and platform.machine() == "arm64", "Original Darwin ARM64 required")
        require(support.git(control, "rev-parse", "HEAD") == args.control_head
            and not support.git(control, "status", "--porcelain", "--untracked-files=no"),
            "Exact clean Swift proof source required")
        work.mkdir(parents=True, exist_ok=False)
        owned = True
        marker = (json.dumps({"control_head": args.control_head, "work": str(work)}, sort_keys=True) + "\n").encode()
        (work / ".original-rpc-owned-work.json").write_bytes(marker)
        root, generated, generation_pin = authenticate_generation(
            control, work, evidence, pin, commands, support, intake, repair)
        old_commands = json.loads((root / "COMMANDS.json").read_bytes())
        old_xcode = next(c for c in old_commands if c["label"] == "xcode-version")
        xcode = commands.require("actual-xcode-version", ["xcodebuild", "-version"], control, 30).read_bytes()
        require(xcode == (root / old_xcode["stdout"]).read_bytes(), "Actual original Xcode build differs")
        swiftc = Path(commands.require("actual-swiftc-path", ["xcrun", "--find", "swiftc"], control, 30).read_text().strip()).resolve()
        tools = json.loads((root / "ACTUAL_REPAIR_TOOL_EXECUTABLES.json").read_bytes())
        expected_swiftc = next(r for r in tools["tools"] if r["path"] == "swiftc")
        require(support.row(swiftc, "swiftc") == expected_swiftc, "Actual original Swift compiler driver differs")
        sdk = Path(commands.require("actual-macos-sdk-root",
            ["xcrun", "--sdk", "macosx", "--show-sdk-path"], control, 30).read_text().strip()).resolve()
        sdk_version = commands.require("actual-macos-sdk-version",
            ["xcrun", "--sdk", "macosx", "--show-sdk-version"], control, 30).read_text().strip()
        require(sdk.is_dir() and sdk.is_relative_to(Path(os.environ["DEVELOPER_DIR"]).resolve())
            and bool(sdk_version), "Actual selected macOS SDK context is absent")
        settings = sdk / "SDKSettings.plist"
        settings_row = support.row(settings, "SDKSettings.plist")
        plistlib.loads(settings.read_bytes())
        shutil.copyfile(settings, evidence / "ACTUAL_MACOS_SDKSettings.plist")
        require(support.row(evidence / "ACTUAL_MACOS_SDKSettings.plist", "SDKSettings.plist")
            == settings_row, "Retained actual SDK settings differ")
        target = json.loads(commands.require("actual-swift-target-context",
            ["xcrun", "swiftc", "-print-target-info", "-sdk", str(sdk)], control, 30).read_bytes())
        require(re.fullmatch(r"arm64-apple-macosx27\.0(?:\.0)?", target["target"]["triple"]) is not None,
                "Actual Swift target differs from the original failed command")
        frontend = Path(commands.require("actual-swift-frontend-path",
            ["xcrun", "--find", "swift-frontend"], control, 30).read_text().strip()).resolve()
        frontend_row = support.row(frontend, "swift-frontend")
        context = {"compiler_driver": expected_swiftc, "frontend": frontend_row, "target": target,
            "sdk_root": str(sdk), "sdk_version": sdk_version, "sdk_settings": settings_row,
            "scope": "Same original Xcode/Swift driver; explicit actual macOS SDK for direct frontend invocation"}
        intake.write(evidence / "ACTUAL_SWIFT_COMPILER_CONTEXT.json", context)
        module = json.loads((root / "ACTUAL_REPAIR_SWIFTPROTOBUF_MODULE.json").read_bytes())
        require(module["source"] == support.PLUGIN, "Original SwiftProtobuf source differs")
        support.check_rows(root / "swiftprotobuf-module", module["files"])
        module_root = work / "module"
        for entry in module["files"]:
            target_path = support.relative_path(module_root, entry["path"])
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / "swiftprotobuf-module" / entry["path"], target_path)
        source = work / "swift"
        inputs = sorted([r for r in generated["swift"]
            if r["path"].startswith("Modules/ProtobufMessages/Sources/Protocol/")
            or r["path"] == "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift"],
            key=lambda r:r["path"])
        primaries = generation_pin["changed_swift_typecheck_primary_paths"]
        require(sorted(primaries) == sorted(generation_pin["allowed_generated_deltas"]["swift"]),
                "Changed primary-file set differs")
        arguments = []
        for entry in inputs:
            target_path = support.relative_path(source, entry["path"])
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / "generated/candidate/swift" / entry["path"], target_path)
            if entry["path"] in primaries:
                arguments.append("-primary-file")
            arguments.append(str(target_path))
        require(arguments.count("-primary-file") == 2, "Changed primary inputs are incomplete")
        response = work / "changed-swift-primary-inputs.rsp"
        response.write_text("\n".join('"' + arg.replace("\\", "\\\\").replace('"', '\\"') + '"' for arg in arguments) + "\n")
        intake.write(evidence / "ACTUAL_SWIFT_TYPECHECK_INPUTS.json",
            {"files": inputs, "primary_paths": primaries, "module_files": module["files"],
             "generated_index_sha256": pin["generated_index_sha256"]})
        result["swift_typecheck_invocations"] = 1
        commands.require("typecheck-changed-original-swift-with-sdk",
            ["xcrun", "swiftc", "-frontend", "-typecheck", "-module-name", "OtzariaGeneratedImportProtocol",
             "-sdk", str(sdk), "-I", str(module_root), "@" + str(response)], source, 1200)
        support.check_rows(source, inputs)
        support.check_rows(module_root, module["files"])
        require(support.row(swiftc, "swiftc") == expected_swiftc
            and support.row(frontend, "swift-frontend") == frontend_row
            and support.row(settings, "SDKSettings.plist") == settings_row,
            "Actual compiler/SDK inputs changed during use")
        for entry in pin["execution_tools"]:
            support.check_rows(control, [entry])
        support.admit_packet(control / PACKET, pin["generation_manifest_sha256"])
        result.update({"status": "PASS", "changed_swift_primary_typecheck": "PASS",
            "primary_paths": primaries, "actual_input_files": len(inputs),
            "actual_compiler_context": context, "post_input_stability": "PASS",
            "scope": "Only the two changed original generated Swift primary files, all original protocol context, and actual SwiftProtobuf module. Whole SDK/Invocation/Native gates remain separate."})
    except BaseException as error:
        result.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
    finally:
        if commands.owned_groups_drained and owned and work.exists():
            try:
                result["cleanup"] = compiler.remove_owned_work(work, marker)
                result["owned_work_removed"] = True
            except BaseException as error:
                result.update({"status": "FAIL", "cleanup_error": str(error), "owned_work_removed": False})
        elif owned and work.exists():
            result.update({"status": "FAIL", "owned_work_removed": False})
        result["commands"] = len(commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        result["finished_unix"] = time.time()
        intake.write(evidence / "RESULT.json", result)
        intake.write(evidence / "EVIDENCE_INDEX.json", {"files": [
            support.row(path, path.relative_to(evidence).as_posix()) for path in sorted(evidence.rglob("*"))
            if path.is_file() and path.name != "EVIDENCE_INDEX.json"],
            "scope": "Actual changed Swift primary-file check with explicit original SDK context. No generators, native/RPC tests, ABI or full SDK build."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
