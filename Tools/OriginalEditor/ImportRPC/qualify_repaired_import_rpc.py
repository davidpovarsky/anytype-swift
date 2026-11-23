#!/usr/bin/env python3
"""Qualify the corrected Cancel schema using only original generators.

Reuse unchanged original generated/typechecked bytes; refresh only the changed
schema dependency closure and run the still-missing RPC controls exactly once.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control-root", "control-head", "packet", "manifest-sha256", "heart-input",
                 "work", "evidence", "pin", "pin-sha256", "swift-input", "plugin-input"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    packet, work, evidence, original_input = [(control / value).resolve()
        for value in (args.packet, args.work, args.evidence, args.heart_input)]
    swift_input, plugin_input = [(control / value).resolve() for value in (args.swift_input,args.plugin_input)]
    roots = (packet, work, evidence, original_input, swift_input, plugin_input)
    if any(root == control or not root.is_relative_to(control) for root in roots):
        raise RuntimeError("Owned qualification roots escape control checkout")
    if any(a == b or a in b.parents or b in a.parents for i,a in enumerate(roots) for b in roots[i+1:]):
        raise RuntimeError("Qualification roots overlap")
    support = load(packet / "generation_support.py", "frozen_import_generation_support")
    manifest, admission = support.admit_packet(packet, args.manifest_sha256)
    pin_path = (control / args.pin).resolve()
    if not pin_path.is_relative_to(control) or support.sha(pin_path) != args.pin_sha256:
        raise RuntimeError("Exact native qualification pin differs")
    pin = json.loads(pin_path.read_bytes())
    if pin["generation_manifest_sha256"] != args.manifest_sha256:
        raise RuntimeError("Native qualification generation source differs")
    for entry in pin["execution_tools"]:
        support.check_rows(control, [entry])
    intake = load(control / "Tools/OriginalEditor/ImportRPC/artifact_intake.py", "actual_generation_intake")
    compiler = load(control / "Tools/OriginalEditor/ImportRPC/compiler_inputs.py", "actual_native_compiler_inputs")
    legacy = load(control / "Tools/OriginalEditor/ImportRPC/qualify_original_import_rpc.py", "unchanged_original_qualification")
    schema_repair = load(control / "Tools/OriginalEditor/ImportRPC/repair_cancel_schema.py", "reviewed_cancel_schema_repair")
    retained = packet / "retained-original"
    helper = support.load_module(retained / "run_native_defaults_repair.py", "original_owned_commands", support.COMMAND_HELPER_SHA)
    original = support.load_module(retained / "generate_original_schema_rpc.py", "original_generator_utilities", support.ORIGINAL_GENERATOR_SHA)
    git, write = support.git, helper.write_json
    evidence.mkdir(parents=True, exist_ok=False)
    result = {"schema": "otzaria.original-import-rpc-cancel-error-qualification-result/1", "status": "NOT_STARTED",
        "control_head": args.control_head, "manifest_sha256": args.manifest_sha256,
        "qualification_pin_sha256": args.pin_sha256, "heart_base": support.HEART, "swift_base": support.SWIFT,
        "pre_generation_native_tree": support.NATIVE_TREE,
        "generator_native_invocations": 0, "generator_swift_invocations": 0,
        "swift_typecheck_invocations": 0, "reused_continuation_run": pin["run_id"],
        "reused_continuation_artifact_sha256": pin["artifact_sha256"],
        "historical_tests_replayed": 0, "native_wallet_editor_tests_executed": 0,
        "ios_framework_built": False, "full_invocation_compiled": False,
        "production_import_activated": False, "new_rpc_controls": []}
    env = os.environ.copy()
    env.update({"GOTOOLCHAIN": "local", "GOWORK": "off", "GOENV": "off", "GOFLAGS": "-mod=readonly",
                "CGO_ENABLED": "1", "GOMAXPROCS": "2", "PROTOBUF_NO_PROTOC": "true",
                "GOPATH": str(work / "go"), "GOMODCACHE": str(work / "go/pkg/mod"),
                "GOCACHE": str(work / "go-build")})
    commands = helper.Commands(evidence, env, args.job_deadline_unix - 180)
    work_owned, marker, heart = False, None, work / "candidate-heart"
    def interrupted(signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt("native qualification interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        intake.require(0 < args.job_deadline_unix - time.time() <= 10800, "Invalid finite native qualification deadline")
        intake.require(platform.system() == "Darwin" and platform.machine() == "arm64", "Original Darwin ARM64 native qualification required")
        intake.require(git(control, "rev-parse", "HEAD") == args.control_head
            and not git(control, "status", "--porcelain", "--untracked-files=no"), "Exact control source is not clean")
        intake.require(git(original_input, "rev-parse", "HEAD") == support.HEART
            and not git(original_input, "status", "--porcelain", "--untracked-files=no"), "Immutable original Heart differs")
        for entry in manifest["original_inputs"]:
            if entry["repository"] == "anyproto/anytype-heart":
                support.check_rows(original_input, [entry])
        write(evidence / "CONTROL_SOURCE_ADMISSION.json", admission)
        work.mkdir(parents=True, exist_ok=False)
        work_owned = True
        marker = (json.dumps({"control_head": args.control_head, "work": str(work)}, sort_keys=True) + "\n").encode()
        (work / ".original-rpc-owned-work.json").write_bytes(marker)
        go_version = commands.require("go-version", ["go", "version"], control, 30).read_text().strip()
        intake.require(go_version == "go version go1.26.5 darwin/arm64", "Original Go toolchain differs")
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], control, 30).read_text()
        intake.require(xcode.splitlines()[0] == "Xcode 27.0", "Original Xcode 27.0 required")
        go_executable = Path(shutil.which("go")).resolve()
        go_before = support.row(go_executable, "go")
        write(evidence / "ACTUAL_GO_EXECUTABLE.json", {**go_before, "absolute_path": str(go_executable)})
        reused, generated = legacy.intake_continuation(control, work, evidence, pin, commands, intake)
        failure_root = schema_repair.authenticate_failure(control,work,evidence,pin,commands,intake)
        intake.require(json.loads((failure_root / "GENERATED_OUTPUT_INDEX.json").read_bytes()) == generated,
                       "Actual compiler failure used different generated bytes")
        result["reused_swift_protocol_typecheck"] = "PASS_FOR_UNCHANGED_FILES_ONLY"
        commands.require("clone-original-heart", ["git", "clone", "--no-hardlinks", "--no-checkout",
            str(original_input), str(heart)], control, 180)
        commands.require("checkout-original-heart", ["git", "checkout", "--detach", support.HEART], heart, 120)
        composition = support.apply_composition(packet, heart, commands, evidence)
        write(evidence / "ACTUAL_NATIVE_COMPOSITION.json", composition)
        for entry in generated["native"]:
            target = support.relative_path(heart, entry["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((reused / "generated/candidate/native" / entry["path"]).read_bytes())
        native_names = [entry["path"] for entry in generated["native"]]
        commands.require("seal-actual-generated-native", ["git", "add", "--", *native_names], heart, 60)
        tree = commands.require("actual-generated-native-tree", ["git", "write-tree"], heart, 30).read_text().strip()
        intake.require(tree == pin["generated_native_tree"], "Actual reused generated native source tree differs")
        result["native_source_tree"] = tree
        write(evidence / "GENERATED_NATIVE_SOURCE_TREE.json", {"base": support.HEART,
            "pre_generation_tree": support.NATIVE_TREE, "native_source_tree": tree,
            "generated_inputs": generated["native"], "actual_generation_run": pin["run_id"],
            "actual_generation_archive_sha256": pin["artifact_sha256"]})
        generated = schema_repair.repair(control,packet,heart,swift_input,plugin_input,work,evidence,
            reused,generated,pin,commands,env,support,original,intake,result)
        commands.require("original-tantivy", [sys.executable, "-I", str(retained / "prepare_original_tantivy.py"),
            "--heart", str(heart), "--helper", str(retained / "build_custom_heart.py"),
            "--helper-sha256", "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
            "--receipt", str(evidence / "TANTIVY_SETUP.json")], heart, 600)
        libraries = heart / "deps/libs/darwin-arm64"
        library_inputs = {"architecture": "darwin-arm64",
            "archive_sha256": support.sha(heart / "deps/libs/darwin-arm64.tar.gz"),
            "files": [{"path": path.relative_to(libraries).as_posix(), "bytes": path.stat().st_size,
                       "sha256": support.sha(path)} for path in sorted(libraries.rglob("*")) if path.is_file()]}
        intake.require(library_inputs == manifest["expected_tantivy_inputs"], "Original native link inputs differ")
        write(evidence / "ACTUAL_NATIVE_LIBRARIES.json", library_inputs)
        env["CGO_LDFLAGS"] = "-L" + str(libraries)
        declared_env_path = commands.require("actual-go-compile-environment", ["go", "env", "-json", "GOMOD", "GOWORK",
            "GOTOOLCHAIN", "GOENV", "GOFLAGS", "GOARCH", "GOOS", "GOPATH", "GOMODCACHE", "GOCACHE", "CGO_ENABLED"], heart, 30)
        declared_env = json.loads(declared_env_path.read_bytes())
        intake.require(declared_env["GOCACHE"] == env["GOCACHE"] and declared_env["GOMODCACHE"] == env["GOMODCACHE"]
            and declared_env["GOMOD"] == str(heart / "go.mod") and declared_env["GOWORK"] == "off"
            and declared_env["GOFLAGS"] == "-mod=readonly" and declared_env["GOTOOLCHAIN"] == "local",
            "Actual native compiler environment differs")
        controls = manifest["rpc_controls"] + [pin["cancel_panic_control"]]
        for entry in controls:
            target = support.relative_path(heart, entry["native_path"])
            intake.require(not target.exists(), "New native RPC control would overwrite original source")
            target.parent.mkdir(parents=True, exist_ok=True)
            source_root = control if entry is pin["cancel_panic_control"] else packet
            support.check_rows(source_root,[entry["retained"]])
            target.write_bytes(support.relative_path(source_root, entry["retained"]["path"]).read_bytes())
        control_names = [entry["native_path"] for entry in controls]
        commands.require("seal-exact-new-rpc-controls", ["git", "add", "--", *control_names], heart, 60)
        result["native_control_tree"] = commands.require("actual-native-control-tree",
            ["git", "write-tree"], heart, 30).read_text().strip()
        packages = ["./clientlibrary/service", "./core", "./core/application", "./cmd/grpcserver"]
        declaration = commands.require("declare-real-native-compile-inputs",
            ["go", "list", "-deps", "-test", "-json", *packages], heart, 1500)
        declared = compiler.collect(declaration, heart, Path(env["GOCACHE"]), evidence, packages)
        for entry in controls:
            expected = {**entry["retained"], "path": entry["native_path"]}
            intake.require(expected in declared["owned_source_inputs"], "Actual compiler closure omits a required RPC control")
        commands.require("compile-generated-go-and-original-mobile-export-source",
            ["go", "build", "-p", "2", "./pb", "./pb/service", "./clientlibrary/service"], heart, 3600)
        result["go_message_and_mobile_export_source_compile"] = "PASS"
        panic = pin["cancel_panic_control"]
        panic_output = commands.require("generated-cancel-panic-control",[
            "go","test","-json","-count=1","-p","2","-timeout=240s","-run",
            "^(" + "|".join(panic["test_names"]) + ")$",panic["package"]],heart,1800)
        panic_receipt = support.validate_go_test(panic_output,panic["test_names"])
        result["generated_cancel_panic_control"] = {"package":panic["package"],**panic_receipt}
        write(evidence / "GENERATED_CANCEL_PANIC_CONTROL.json",result["generated_cancel_panic_control"])

        for entry in manifest["rpc_controls"]:
            pattern = "^(" + "|".join(entry["test_names"]) + ")$"
            output = commands.require("rpc-controls-" + entry["label"], ["go", "test", "-json", "-count=1", "-p", "2",
                "-timeout=240s", "-run", pattern, entry["package"]], heart, 1800)
            receipt = support.validate_go_test(output, entry["test_names"])
            result["new_rpc_controls"].append({"package": entry["package"], **receipt})
            write(evidence / "NEW_RPC_CONTROLS.json", result["new_rpc_controls"])
        stable = compiler.verify_unchanged(declared, heart, Path(env["GOCACHE"]))
        support.check_rows(heart, generated["native"])
        support.check_rows(heart,[pin["schema_transform"]["after"]])
        for entry in library_inputs["files"]:
            support.check_rows(libraries, [entry])
        intake.require(support.sha(heart / "deps/libs/darwin-arm64.tar.gz") == library_inputs["archive_sha256"],
                       "Original native link archive changed")
        intake.require(support.row(go_executable, "go") == go_before, "Actual Go executable changed during use")
        intake.require(not git(heart, "diff", "--name-only", "-z")
            and git(heart, "write-tree") == result["native_control_tree"],
            "Native source/index changed during compilation or controls")
        intake.require(git(original_input, "rev-parse", "HEAD") == support.HEART
            and not git(original_input, "status", "--porcelain", "--untracked-files=no"), "Immutable original Heart changed")
        support.admit_packet(packet, args.manifest_sha256)
        for entry in pin["execution_tools"]:
            support.check_rows(control, [entry])
        write(evidence / "POST_NATIVE_COMPILER_INPUT_STABILITY.json", stable)
        result.update({"status": "PASS", "generated_counts": {k:len(v) for k,v in generated.items()},
            "new_rpc_control_passes": sum(len(item["passed"]) for item in result["new_rpc_controls"]),
            "original_inputs_tools_and_link_inputs_unchanged": True,
            "compiler_input_stability": stable, "generated_outputs_require_review_before_integration": True})
    except BaseException as error:
        result.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
    finally:
        result["commands"] = len(commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        if result["status"] != "PASS" and heart.exists():
            try:
                intake.capture_native_boundary(heart, evidence, "qualification-final",
                    original.native_outputs(heart), git, commands)
            except Exception as error:
                write(evidence / "NATIVE_BOUNDARY_CAPTURE_ERROR.json", {"error": str(error)})
        if result["status"] != "PASS" and work_owned:
            partial = {}
            for kind,root,scopes in (
                ("native",heart,original.native_outputs(heart) if heart.exists() else []),
                ("swift",work / "candidate-swift",original.SWIFT_OUTPUT_SCOPES + [
                    "Dependencies/Middleware/protobuf","Dependencies/Middleware/json","Dependencies/Middleware/genmodels"])):
                if root.exists() and scopes:
                    try:
                        present = [scope for scope in scopes if (root / scope).exists()]
                        partial[kind] = original.retain_outputs(root,present,evidence / "failure-time" / kind,git)
                    except Exception as capture_error:
                        partial[kind] = {"capture_error":str(capture_error)}
            write(evidence / "FAILURE_OUTPUT_INDEX.json",{"scope":"Failure-time partial bytes only; no success credit.","roots":partial})
        if commands.owned_groups_drained and work_owned and work.exists():
            try:
                result["cleanup"] = compiler.remove_owned_work(work, marker)
                result["owned_work_removed"] = True
            except Exception as error:
                result.update({"status": "FAIL", "cleanup_error": str(error), "owned_work_removed": False})
        elif work_owned and work.exists():
            result.update({"status": "FAIL", "owned_work_removed": False})
        result["commands"] = len(commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        result["finished_unix"] = time.time()
        write(evidence / "RESULT.json", result)
        rows = [support.row(path, path.relative_to(evidence).as_posix())
                for path in sorted(evidence.rglob("*")) if path.is_file() and path.name != "EVIDENCE_INDEX.json"]
        write(evidence / "EVIDENCE_INDEX.json", {"files": rows,
            "scope": "Reviewed append-only Cancel enum and original affected generation/typecheck, then native compile, generated panic control and nine original RPC controls. Prior whole typecheck reused only for identical bytes. No native wallet import, mobile ABI, full SDK, Host mapping or ACK acceptance."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
