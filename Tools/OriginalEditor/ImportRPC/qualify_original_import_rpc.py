#!/usr/bin/env python3
"""Complete missing native RPC controls using actual generated and typechecked bytes.

No original generator, Swift typecheck or historical test is replayed. The exact
failed continuation remains failed; its real generation/typecheck evidence is
authenticated and retained while this run performs only the missing native work.
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

def intake_continuation(control, work, evidence, pin, commands, intake):
    metadata = {}
    for kind, endpoint in (("run", "actions/runs/" + str(pin["run_id"])),
                           ("artifact", "actions/artifacts/" + str(pin["artifact_id"]))):
        output = commands.require("reuse-continuation-" + kind,
            ["gh", "api", "repos/" + pin["repository"] + "/" + endpoint], control, 60)
        metadata[kind] = json.loads(output.read_bytes())
        intake.write(evidence / ("REUSED_CONTINUATION_" + kind.upper() + ".json"), metadata[kind])
    run, artifact = metadata["run"], metadata["artifact"]
    intake.require(run["id"] == pin["run_id"] and run["head_sha"] == pin["head_sha"]
        and run["head_branch"] == pin["head_branch"] and run["path"] == pin["workflow_path"]
        and run["run_attempt"] == 1 and run["status"] == "completed" and run["conclusion"] == "failure"
        and run["event"] == "push" and run["repository"]["full_name"] == pin["repository"],
        "Actual prior continuation identity differs")
    intake.require(artifact["id"] == pin["artifact_id"] and artifact["name"] == pin["artifact_name"]
        and artifact["size_in_bytes"] == pin["artifact_bytes"] and not artifact["expired"]
        and artifact["digest"] == "sha256:" + pin["artifact_sha256"]
        and artifact["workflow_run"]["id"] == pin["run_id"]
        and artifact["workflow_run"]["head_sha"] == pin["head_sha"],
        "Actual prior continuation artifact identity differs")
    archive = commands.require("download-actual-continuation",
        ["gh", "api", "repos/" + pin["repository"] + "/actions/artifacts/" + str(pin["artifact_id"]) + "/zip"],
        control, 240)
    root = work / "actual-continuation"
    receipt = intake.unpack(archive, root, pin)
    intake.require(receipt == {"crc_members": 2326, "indexed_files": 2325},
                   "Prior continuation index closure differs")
    intake.write(evidence / "REUSED_CONTINUATION_INTAKE.json",
        {**receipt, "artifact_sha256": pin["artifact_sha256"], "run_id": pin["run_id"],
         "archive_command_stdout": archive.name})
    result = json.loads((root / "RESULT.json").read_bytes())
    intake.require(result["schema"] == "otzaria.original-import-rpc-generation-continuation-result/1"
        and result["status"] == "FAIL" and result["error_type"] == "RuntimeError"
        and result["error"] == "declared native compiler input escapes original source"
        and result["control_head"] == pin["head_sha"]
        and result["manifest_sha256"] == pin["generation_manifest_sha256"]
        and result["pre_generation_native_tree"] == pin["pre_generation_native_tree"]
        and result["native_source_tree"] == pin["generated_native_tree"]
        and result["swift_protocol_typecheck"] == "PASS"
        and result["generator_native_invocations"] == 1 and result["generator_swift_invocations"] == 0
        and result["reused_generation_run"] == 45224590564
        and result["reused_generation_sha256"] == "49a3e4b9bce69168405a88796a5566fa87ec2bf52cb4f5cac59f004152170bdc"
        and result["reused_generator_native_invocations"] == 1
        and result["reused_generator_swift_invocations"] == 1
        and result["owned_command_groups_drained"] and result["commands"] == 37
        and not result["new_rpc_controls"] and result["historical_tests_replayed"] == 0,
        "Prior continuation boundary differs")
    recorded = json.loads((root / "COMMANDS.json").read_bytes())
    intake.require(len(recorded) == 37 and all(c["effective_returncode"] == 0 and not c["timed_out"] for c in recorded),
                   "Prior actual continuation commands did not finish normally")
    typed = [c for c in recorded if c["label"] == "typecheck-generated-swift-protocol"]
    intake.require(len(typed) == 1 and typed[0]["argv"][:5] ==
        ["xcrun", "swiftc", "-typecheck", "-module-name", "OtzariaGeneratedImportProtocol"]
        and typed[0]["duration_seconds"] > 0, "Original generated Swift protocol typecheck receipt differs")
    generated = json.loads((root / "GENERATED_OUTPUT_INDEX.json").read_bytes())
    intake.require({k: len(v) for k,v in generated.items()} == {"native": 11, "swift": 696, "middleware": 37},
                   "Actual generated output family differs")
    index = {r["path"]: r for r in json.loads((root / "EVIDENCE_INDEX.json").read_bytes())["files"]}
    for family, entries in generated.items():
        prefix = "generated/candidate/" + ("native/" if family == "native" else "swift/")
        failure = "failure-time/" + ("heart/" if family == "native" else "swift/")
        for entry in entries:
            intake.require(intake.row(root / prefix / entry["path"], entry["path"]) == entry
                and all(index[prefix + entry["path"]][k] == entry[k] for k in ("bytes", "sha256", "git_blob"))
                and intake.row(root / failure / entry["path"], entry["path"]) == entry,
                "Actual generated bytes differ before/after the real typecheck")
            target = evidence / prefix / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / prefix / entry["path"]).read_bytes())
    marker = json.loads((root / "ORIGINAL_OUTPUT_DIRECTORY_MARKER.json").read_bytes())
    intake.require(marker["restored_exact_original_bytes"]
        and marker["before"]["outside_generated_outputs"] == ["dist/ios/protobuf/.gitignore"]
        and not marker["after"]["outside_generated_outputs"]
        and marker["original_tracked_marker"]["git_blob"] == "a4dc73110580f00f0071a8493cc22cece6307cb4",
        "Original generator directory-marker proof differs")
    equality = json.loads((root / "REGENERATED_NATIVE_EQUALITY.json").read_bytes())
    intake.require(equality["exact_bytes_equal"] and equality["native"] == generated["native"]
        and equality["prior_run"] == 45224590564
        and equality["prior_archive_sha256"] == result["reused_generation_sha256"],
        "Actual original native regeneration equality differs")
    final_boundary = json.loads((root / "NATIVE_BOUNDARY_failure-final.json").read_bytes())
    intake.require(not final_boundary["changed_paths"], "Prior generated native source changed before failure")
    intake.write(evidence / "REUSED_CONTINUATION_RESULT.json", result)
    intake.write(evidence / "REUSED_CONTINUATION_COMMANDS.json", recorded)
    intake.write(evidence / "GENERATED_OUTPUT_INDEX.json", generated)
    intake.write(evidence / "REUSED_SWIFT_PROTOCOL_TYPECHECK.json",
        {"status": "PASS", "run_id": pin["run_id"], "head_sha": pin["head_sha"],
         "artifact_sha256": pin["artifact_sha256"], "actual_command": typed[0],
         "generated_source_before_after_equal": True,
         "scope": "The actual earlier generated protocol typecheck only. Its aggregate run and cleanup remain failed; no new compiler invocation or full Invocation/SDK/ABI acceptance."})
    for name in ("ORIGINAL_OUTPUT_DIRECTORY_MARKER.json", "REGENERATED_NATIVE_EQUALITY.json",
                 "ACTUAL_GENERATOR_INPUTS.json", "ACTUAL_TOOL_EXECUTABLES.json", "ACTUAL_SWIFTPROTOBUF_MODULE.json"):
        (evidence / ("REUSED_" + name)).write_bytes((root / name).read_bytes())
    return root, generated

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control-root", "control-head", "packet", "manifest-sha256", "heart-input",
                 "work", "evidence", "pin", "pin-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    packet, work, evidence, original_input = [(control / value).resolve()
        for value in (args.packet, args.work, args.evidence, args.heart_input)]
    roots = (packet, work, evidence, original_input)
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
    retained = packet / "retained-original"
    helper = support.load_module(retained / "run_native_defaults_repair.py", "original_owned_commands", support.COMMAND_HELPER_SHA)
    original = support.load_module(retained / "generate_original_schema_rpc.py", "original_generator_utilities", support.ORIGINAL_GENERATOR_SHA)
    git, write = support.git, helper.write_json
    evidence.mkdir(parents=True, exist_ok=False)
    result = {"schema": "otzaria.original-import-rpc-native-qualification-result/1", "status": "NOT_STARTED",
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
        intake.require(0 < args.job_deadline_unix - time.time() <= 7200, "Invalid finite native qualification deadline")
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
        reused, generated = intake_continuation(control, work, evidence, pin, commands, intake)
        result["reused_swift_protocol_typecheck"] = "PASS"
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
        for entry in manifest["rpc_controls"]:
            target = support.relative_path(heart, entry["native_path"])
            intake.require(not target.exists(), "New native RPC control would overwrite original source")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(support.relative_path(packet, entry["retained"]["path"]).read_bytes())
        control_names = [entry["native_path"] for entry in manifest["rpc_controls"]]
        commands.require("seal-exact-new-rpc-controls", ["git", "add", "--", *control_names], heart, 60)
        result["native_control_tree"] = commands.require("actual-native-control-tree",
            ["git", "write-tree"], heart, 30).read_text().strip()
        packages = ["./clientlibrary/service", "./core", "./core/application", "./cmd/grpcserver"]
        declaration = commands.require("declare-real-native-compile-inputs",
            ["go", "list", "-deps", "-test", "-json", *packages], heart, 1500)
        declared = compiler.collect(declaration, heart, Path(env["GOCACHE"]), evidence, packages)
        for entry in manifest["rpc_controls"]:
            expected = {**entry["retained"], "path": entry["native_path"]}
            intake.require(expected in declared["owned_source_inputs"], "Actual compiler closure omits a required RPC control")
        commands.require("compile-generated-go-and-original-mobile-export-source",
            ["go", "build", "-p", "2", "./pb", "./pb/service", "./clientlibrary/service"], heart, 3600)
        result["go_message_and_mobile_export_source_compile"] = "PASS"
        for entry in manifest["rpc_controls"]:
            pattern = "^(" + "|".join(entry["test_names"]) + ")$"
            output = commands.require("rpc-controls-" + entry["label"], ["go", "test", "-json", "-count=1", "-p", "2",
                "-timeout=240s", "-run", pattern, entry["package"]], heart, 1800)
            receipt = support.validate_go_test(output, entry["test_names"])
            result["new_rpc_controls"].append({"package": entry["package"], **receipt})
            write(evidence / "NEW_RPC_CONTROLS.json", result["new_rpc_controls"])
        stable = compiler.verify_unchanged(declared, heart, Path(env["GOCACHE"]))
        support.check_rows(heart, generated["native"])
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
            "scope": "Authenticated original generator/typecheck reuse plus newly executed native compile and nine RPC controls. No native wallet import, mobile ABI, full SDK, Host mapping or ACK acceptance."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
