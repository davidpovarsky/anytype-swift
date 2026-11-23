#!/usr/bin/env python3
"""Run the original generators once for reviewed Annotation Import/Cancel source.

The previous Schema generation is authenticated and reused as comparison evidence.
The new run qualifies actual generated messages, Go/mobile export SOURCE, and nine
new RPC controls. It does not produce Lib.framework or run an account/editor.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True

def import_support(packet):
    spec = importlib.util.spec_from_file_location("import_generation_support", packet / "generation_support.py")
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    return support

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("control-root", "control-head", "packet", "manifest-sha256", "heart-input",
                 "swift-input", "plugin-input", "work", "evidence"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    packet = (control / args.packet).resolve()
    evidence = (control / args.evidence).resolve()
    work = (control / args.work).resolve()
    if (not packet.is_relative_to(control) or packet == control
            or not evidence.is_relative_to(control) or evidence == control
            or not work.is_relative_to(control) or work == control
            or work == evidence or work in evidence.parents or evidence in work.parents
            or packet == work or packet in work.parents or work in packet.parents
            or packet == evidence or packet in evidence.parents or evidence in packet.parents):
        raise RuntimeError("owned packet/work/evidence roots overlap or escape")
    support = import_support(packet)
    manifest, admission = support.admit_packet(packet, args.manifest_sha256)
    retained = packet / "retained-original"
    helper = support.load_module(retained / "run_native_defaults_repair.py", "original_owned_commands", support.COMMAND_HELPER_SHA)
    original = support.load_module(retained / "generate_original_schema_rpc.py", "original_generator_utilities", support.ORIGINAL_GENERATOR_SHA)
    continuation = support.load_module(retained / "continuation_support.py", "original_swift_products", support.CONTINUATION_SHA)
    git, write_json = support.git, helper.write_json
    evidence.mkdir(parents=True, exist_ok=False)
    result = {"schema": "otzaria.original-import-rpc-generation-result/1", "status": "NOT_STARTED",
              "control_head": args.control_head, "manifest_sha256": args.manifest_sha256,
              "heart_base": support.HEART, "swift_base": support.SWIFT,
              "pre_generation_native_tree": support.NATIVE_TREE,
              "generator_native_invocations": 0, "generator_swift_invocations": 0,
              "historical_tests_replayed": 0, "native_wallet_editor_tests_executed": 0,
              "ios_framework_built": False, "full_invocation_compiled": False,
              "production_import_activated": False, "new_rpc_controls": []}
    env = os.environ.copy()
    env.update({"GOTOOLCHAIN": "local", "GOWORK": "off", "GOENV": "off", "GOFLAGS": "-mod=readonly",
                "CGO_ENABLED": "1", "GOMAXPROCS": "2", "PROTOBUF_NO_PROTOC": "true",
                "SHELLOPTS": "errexit:pipefail"})
    commands = helper.Commands(evidence, env, args.job_deadline_unix - 180)
    roots, tools, work_owned, generated = {}, {}, False, {}
    def interrupted(signum, _frame):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt("generation interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if not 0 < args.job_deadline_unix - time.time() <= 7200:
            raise RuntimeError("invalid finite job deadline")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("actual Darwin ARM64 generator host required")
        if git(control, "rev-parse", "HEAD") != args.control_head or git(control, "status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError("control source is not the clean exact reviewed head")
        write_json(evidence / "CONTROL_SOURCE_ADMISSION.json", admission)
        inputs = {"heart": (control / args.heart_input).resolve(), "swift": (control / args.swift_input).resolve(),
                  "plugin": (control / args.plugin_input).resolve()}
        for kind, expected in (("heart", support.HEART), ("swift", support.SWIFT), ("plugin", support.PLUGIN)):
            source = inputs[kind]
            if (not source.is_relative_to(control) or source == control or source.is_relative_to(work)
                    or work.is_relative_to(source) or source.is_relative_to(evidence)
                    or git(source, "rev-parse", "HEAD") != expected
                    or git(source, "status", "--porcelain", "--untracked-files=no")):
                raise RuntimeError("immutable original checkout differs: " + kind)
        source_roots = {"anyproto/anytype-heart": inputs["heart"],
                        "davidpovarsky/anytype-swift": inputs["swift"], "apple/swift-protobuf": inputs["plugin"]}
        for entry in manifest["original_inputs"]:
            support.check_rows(source_roots[entry["repository"]], [entry])
        for entry in manifest["swift_generator_correspondence"]:
            support.check_rows(inputs["swift"], [entry])
        previous, previous_tools, historical = support.retained_qualification(packet)
        write_json(evidence / "REUSED_45101449367.json", historical)
        write_json(evidence / "PREVIOUS_GENERATED_OUTPUT_INDEX.json", previous)
        go_version = commands.require("go-version", ["go", "version"], control, 30).read_text().strip()
        if go_version != "go version go1.26.5 darwin/arm64":
            raise RuntimeError("original Go toolchain differs")
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], control, 30).read_text()
        if xcode.splitlines()[0] != "Xcode 27.0":
            raise RuntimeError("actual Xcode 27.0 required")
        commands.require("swift-version", ["xcrun", "swift", "--version"], control, 30)
        commands.require("swift-target", ["xcrun", "swiftc", "-print-target-info"], control, 30)
        commands.require("make-version", ["make", "--version"], control, 30)
        work.mkdir(parents=True, exist_ok=False)
        work_owned = True
        roots = {"heart": work / "candidate-heart", "swift": work / "candidate-swift"}
        heart, swift = roots["heart"], roots["swift"]
        commands.require("copy-materialized-swift", [
            sys.executable, "-I", str(retained / "copy_materialized_checkout.py"),
            "--source", str(inputs["swift"]), "--target", str(swift), "--expected-head", support.SWIFT,
            "--receipt", str(evidence / "SWIFT_COPY.json")], control, 180)
        commands.require("clone-original-heart", ["git", "clone", "--no-hardlinks", "--no-checkout", str(inputs["heart"]), str(heart)], control, 180)
        commands.require("checkout-original-heart", ["git", "checkout", "--detach", support.HEART], heart, 120)
        tracked = {"native": original.retain_outputs(heart, original.native_outputs(heart), evidence / "generated/tracked/native", git),
                   "swift": original.retain_outputs(swift, original.SWIFT_OUTPUT_SCOPES, evidence / "generated/tracked/swift", git)}
        write_json(evidence / "TRACKED_GENERATED_OUTPUT_INDEX.json", tracked)
        composition = support.apply_composition(packet, heart, commands, evidence)
        write_json(evidence / "ACTUAL_NATIVE_COMPOSITION.json", composition)
        native_inputs = original.checked_tree(heart, original.NATIVE_INPUT_SCOPES, git)
        swift_inputs = original.checked_tree(swift, original.SWIFT_INPUT_SCOPES, git)
        invocation_before = support.row(swift / "Modules/ProtobufMessages/Sources/Invocation.swift",
                                        "Modules/ProtobufMessages/Sources/Invocation.swift")
        write_json(evidence / "ACTUAL_GENERATOR_INPUTS.json", {"native": native_inputs, "swift": swift_inputs,
                   "preserved_invocation": invocation_before})
        if support.sha(swift / "Tools/anytype-swift-codegen") != support.CODEGEN_SHA:
            raise RuntimeError("actual original Swift codegen binary differs")
        tools_root = work / "tools"
        tools_root.mkdir()
        toolpins = json.loads((retained / "TOOL_PINS.json").read_bytes())
        for tool in toolpins["archives"]:
            archive = tools_root / tool["archive_name"]
            commands.require("download-" + tool["name"], [
                "curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20",
                "--max-time", "180", "--output", str(archive), tool["url"]], control, 190)
            tools[tool["name"]] = original.safe_archive(tool, archive, tools_root / tool["name"])
        env["PATH"] = str(tools["protoc"].parent) + os.pathsep + env["PATH"]
        protoc_version = commands.require("protoc-version", [str(tools["protoc"]), "--version"], control, 30).read_text().strip()
        if protoc_version != toolpins["archives"][0]["expected_version"]:
            raise RuntimeError("actual pinned protoc version differs")
        for name in ("sourcery", "swiftgen"):
            commands.require(name + "-version", [str(tools[name]), "--version"], control, 30)
        (swift / "build").mkdir(exist_ok=True)
        plugin = swift / "build/swift-protobuf"
        commands.require("clone-original-swift-protobuf", ["git", "clone", "--no-hardlinks", "--no-checkout", str(inputs["plugin"]), str(plugin)], control, 180)
        commands.require("checkout-original-swift-protobuf", ["git", "checkout", "--detach", support.PLUGIN], plugin, 60)
        commands.require("build-original-swift-protobuf", ["swift", "build", "-c", "release"], plugin, 1500)
        bin_path = commands.require("swift-protobuf-bin-path", ["swift", "build", "-c", "release", "--show-bin-path"], plugin, 60).read_text()
        tools["protoc-gen-swift"], protobuf_module = continuation.resolve_swiftprotobuf_products(plugin, bin_path)
        module_rows = continuation.retain_module(protobuf_module, evidence / "swiftprotobuf-module")
        write_json(evidence / "ACTUAL_SWIFTPROTOBUF_MODULE.json",
                   {"bin_path_output": bin_path, "module": str(protobuf_module), "files": module_rows})
        make = ["make", "SHELL=/bin/bash", ".SHELLFLAGS=-e -o pipefail -c"]
        commands.require("build-original-filesplit", make + ["setup-file-splitter"], swift, 1800)
        tools["filesplit"] = swift / "build/anytype-swift-filesplit-v1"
        env["PATH"] = str(tools["protoc-gen-swift"].parent) + os.pathsep + env["PATH"]
        commands.require("build-original-gogo-plugins", make + ["setup-protoc-go"], heart, 1200)
        gogo = json.loads(commands.require("actual-gogo-module", ["go", "list", "-m", "-json", "github.com/gogo/protobuf"], heart, 60).read_bytes())
        if (gogo["Version"] != toolpins["gogo"]["version"] or gogo["Replace"]["Path"] != toolpins["gogo"]["replacement"]
                or gogo["Replace"]["Version"] != toolpins["gogo"]["replacement_version"]):
            raise RuntimeError("actual original custom protobuf replacement differs")
        support.check_rows(Path(gogo["Replace"]["Dir"]), manifest["gogo_inputs"])
        write_json(evidence / "ACTUAL_GOGO_MODULE.json", gogo)
        for name in ("protoc-gen-gogofaster", "protoc-gen-gogofast", "protoc-gen-doc"):
            tools[name] = heart / "deps" / name
            commands.require("buildinfo-" + name, ["go", "version", "-m", str(tools[name])], heart, 30)
        for name in ("sourcery", "swiftgen"):
            target = swift / "build" / name
            shutil.copyfile(tools[name], target)
            target.chmod(0o755)
            tools[name + "-invoked-copy"] = target
        tools["anytype-swift-codegen"] = swift / "Tools/anytype-swift-codegen"
        for name in ("go", "make", "bash"):
            tools[name] = Path(shutil.which(name, path=env["PATH"])).resolve()
        for name in ("swift", "swiftc"):
            tools[name] = Path(commands.require("locate-" + name, ["xcrun", "--find", name], control, 30).read_text().strip()).resolve()
        tool_rows = [support.row(path, name) for name, path in sorted(tools.items())]
        write_json(evidence / "ACTUAL_TOOL_EXECUTABLES.json", {
            "go_version": go_version, "protoc_version": protoc_version, "tools": tool_rows,
            "historical_changes": original.compare_rows(previous_tools["tools"], tool_rows),
            "scope": "Actual rebuilt original pinned binaries; source pins do not imply identical executable hashes."})
        commands.require("swift-protobuf-version", [str(tools["protoc-gen-swift"]), "--version"], control, 30)
        native_outputs = original.native_outputs(heart)
        original.remove_owned_outputs(heart, native_outputs)
        (heart / "dist/ios/protobuf").mkdir(parents=True, exist_ok=True)
        result["generator_native_invocations"] += 1
        commands.require("original-native-generation", make + ["protos-go", "protos-server", "swift-protos"], heart, 600)
        for name in native_outputs:
            path = support.relative_path(heart, name)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError("fresh original native output absent: " + name)
        for source in list((heart / "pb/protos").glob("*.proto")) + list((heart / "pkg/lib/pb/model/protos").glob("*.proto")):
            path = heart / "protobuf" / (source.stem + ".pb.swift")
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError("fresh original raw Swift output absent")
        middleware = swift / "Dependencies/Middleware"
        middleware.mkdir(parents=True, exist_ok=True)
        for name in ("protobuf", "json"):
            if (middleware / name).exists():
                raise RuntimeError("unexpected pre-existing generated middleware")
            shutil.copytree(heart / name, middleware / name)
        original.remove_owned_outputs(swift, original.SWIFT_OUTPUT_SCOPES)
        result["generator_swift_invocations"] += 1
        commands.require("original-swift-generation", make + ["generate-middle"], swift, 900)
        for name in original.SWIFT_OUTPUT_SCOPES:
            if not (swift / name).exists():
                raise RuntimeError("fresh original Swift output family absent")
        generated = {
            "native": original.retain_outputs(heart, native_outputs, evidence / "generated/candidate/native", git),
            "swift": original.retain_outputs(swift, original.SWIFT_OUTPUT_SCOPES, evidence / "generated/candidate/swift", git),
            "middleware": original.retain_outputs(swift, ["Dependencies/Middleware/protobuf", "Dependencies/Middleware/json",
                "Dependencies/Middleware/genmodels"], evidence / "generated/candidate/swift", git)}
        write_json(evidence / "GENERATED_OUTPUT_INDEX.json", generated)
        deltas = {kind: original.compare_rows(previous[kind], generated[kind]) for kind in generated}
        write_json(evidence / "GENERATED_DELTA.json", {"candidate_vs_authenticated_schema": deltas,
            "candidate_vs_tracked": {kind: original.compare_rows(tracked[kind], generated[kind]) for kind in tracked},
            "scope": "All original output families retained, including bundled service Swift. Counts are observed, never guessed."})
        if not deltas["native"] or not deltas["swift"]:
            raise RuntimeError("fresh Import/Cancel generation produced no actual delta")
        changed_native = set(filter(None, git(heart, "diff", "--name-only", "-z").split("\0")))
        if not changed_native.issubset(set(native_outputs)):
            raise RuntimeError("original generator modified native source outside generated output family")
        changed_swift = set(filter(None, git(swift, "diff", "--name-only", "-z").split("\0")))
        if any(not any(name == scope or name.startswith(scope + "/") for scope in original.SWIFT_OUTPUT_SCOPES) for name in changed_swift):
            raise RuntimeError("original generator modified Swift source outside original output families")
        write_json(evidence / "ACTUAL_GENERATED_SERVICE_SYMBOLS.json", support.retain_symbols(heart, swift))
        commands.require("seal-generated-native-index", ["git", "add", "--", *native_outputs], heart, 60)
        generated_tree = commands.require("read-generated-native-tree", ["git", "write-tree"], heart, 30).read_text().strip()
        if not re.fullmatch("[0-9a-f]{40}", generated_tree):
            raise RuntimeError("invalid generated native source tree")
        result["native_source_tree"] = generated_tree
        result["generated_inputs"] = [
            {"native_path": entry["path"], "artifact_path": "generated/candidate/native/" + entry["path"],
             **{k: entry[k] for k in ("bytes", "sha256", "git_blob")}} for entry in generated["native"]]
        write_json(evidence / "GENERATED_NATIVE_SOURCE_TREE.json", {
            "base": support.HEART, "pre_generation_tree": support.NATIVE_TREE,
            "native_source_tree": generated_tree, "generated_inputs": result["generated_inputs"]})
        protocol_files = sorted((swift / "Modules/ProtobufMessages/Sources/Protocol").rglob("*.swift"))
        if not protocol_files:
            raise RuntimeError("fresh generated Swift protocol family is empty")
        response_file = work / "generated-swift-inputs.rsp"
        response_file.write_text("\n".join('"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"' for path in protocol_files) + "\n")
        commands.require("typecheck-generated-swift-protocol", [
            "xcrun", "swiftc", "-typecheck", "-module-name", "OtzariaGeneratedImportProtocol",
            "-I", str(protobuf_module.parent), "@" + str(response_file)], swift, 1200)
        result["swift_protocol_typecheck"] = "PASS"
        commands.require("original-tantivy", [
            sys.executable, "-I", str(retained / "prepare_original_tantivy.py"), "--heart", str(heart),
            "--helper", str(retained / "build_custom_heart.py"), "--helper-sha256",
            "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
            "--receipt", str(evidence / "TANTIVY_SETUP.json")], heart, 600)
        native_libraries = heart / "deps/libs/darwin-arm64"
        actual_tantivy = {"architecture": "darwin-arm64",
            "archive_sha256": support.sha(heart / "deps/libs/darwin-arm64.tar.gz"),
            "files": [{"path": path.relative_to(native_libraries).as_posix(), "bytes": path.stat().st_size, "sha256": support.sha(path)}
                      for path in sorted(native_libraries.rglob("*")) if path.is_file()]}
        if actual_tantivy != manifest["expected_tantivy_inputs"]:
            raise RuntimeError("original native library closure differs")
        write_json(evidence / "ACTUAL_NATIVE_LIBRARIES.json", actual_tantivy)
        env["CGO_LDFLAGS"] = "-L" + str(native_libraries)
        commands.require("actual-go-compile-environment", ["go", "env", "-json", "GOMOD", "GOWORK", "GOTOOLCHAIN",
            "GOENV", "GOFLAGS", "GOARCH", "GOOS", "GOPATH", "GOMODCACHE", "CGO_ENABLED"], heart, 30)
        for entry in manifest["rpc_controls"]:
            target = support.relative_path(heart, entry["native_path"])
            if target.exists():
                raise RuntimeError("new RPC control would overwrite an original source")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(support.relative_path(packet, entry["retained"]["path"]).read_bytes())
        declaration = commands.require("declare-real-native-compile-inputs", [
            "go", "list", "-deps", "-test", "-json", "./clientlibrary/service", "./core", "./core/application", "./cmd/grpcserver"], heart, 1500)
        declared = support.declared_native_inputs(declaration, heart)
        write_json(evidence / "DECLARED_NATIVE_COMPILER_INPUTS.json", declared)
        commands.require("compile-generated-go-and-original-mobile-export-source", [
            "go", "build", "-p", "2", "./pb", "./pb/service", "./clientlibrary/service"], heart, 3600)
        result["go_message_and_mobile_export_source_compile"] = "PASS"
        for entry in manifest["rpc_controls"]:
            pattern = "^(" + "|".join(entry["test_names"]) + ")$"
            output = commands.require("rpc-controls-" + entry["label"], [
                "go", "test", "-json", "-count=1", "-p", "2", "-timeout=240s", "-run", pattern,
                entry["package"]], heart, 1800)
            receipt = support.validate_go_test(output, entry["test_names"])
            result["new_rpc_controls"].append({"package": entry["package"], **receipt})
            write_json(evidence / "NEW_RPC_CONTROLS.json", result["new_rpc_controls"])
        support.check_rows(heart, declared["owned_source_inputs"])
        if original.checked_tree(heart, original.NATIVE_INPUT_SCOPES, git) != native_inputs:
            raise RuntimeError("original native generator inputs changed during execution")
        if original.checked_tree(swift, original.SWIFT_INPUT_SCOPES, git) != swift_inputs:
            raise RuntimeError("original Swift generator inputs changed during execution")
        if support.row(swift / invocation_before["path"], invocation_before["path"]) != invocation_before:
            raise RuntimeError("source-bound original Invocation history changed")
        if [support.row(path, name) for name, path in sorted(tools.items())] != tool_rows:
            raise RuntimeError("actual generator executable changed during use")
        if continuation.retain_module(protobuf_module, evidence / "swiftprotobuf-module-after") != module_rows:
            raise RuntimeError("actual SwiftProtobuf module changed during typecheck")
        support.admit_packet(packet, args.manifest_sha256)
        for kind, expected in (("heart", support.HEART), ("swift", support.SWIFT), ("plugin", support.PLUGIN)):
            if git(inputs[kind], "rev-parse", "HEAD") != expected or git(inputs[kind], "status", "--porcelain", "--untracked-files=no"):
                raise RuntimeError("immutable original checkout changed during use")
        result.update({"status": "PASS", "generated_counts": {k: len(v) for k, v in generated.items()},
                       "generated_delta_counts": {k: len(v) for k, v in deltas.items()},
                       "new_rpc_control_passes": sum(len(x["passed"]) for x in result["new_rpc_controls"]),
                       "original_inputs_and_tools_unchanged": True,
                       "generated_outputs_require_review_before_integration": True})
    except BaseException as error:
        result.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
    finally:
        result["commands"] = len(commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        if result["status"] != "PASS" and work_owned:
            partial = {"scope": "Failure-time bytes only; may contain old or partially generated files. No success credit.", "roots": {}}
            for kind, root in roots.items():
                if not root.exists():
                    continue
                scopes = original.native_outputs(root) + ["protobuf", "json"] if kind == "heart" else original.SWIFT_OUTPUT_SCOPES + ["Dependencies/Middleware"]
                try:
                    partial["roots"][kind] = original.retain_outputs(root, scopes, evidence / "failure-time" / kind, git)
                except Exception as error:
                    partial["roots"][kind] = {"capture_error": str(error)}
            write_json(evidence / "FAILURE_OUTPUT_INDEX.json", partial)
        if commands.owned_groups_drained and work_owned and work.exists():
            try:
                shutil.rmtree(work)
                result["owned_work_removed"] = True
            except Exception as error:
                result.update({"status": "FAIL", "cleanup_error": str(error), "owned_work_removed": False})
        elif work_owned and work.exists():
            result.update({"status": "FAIL", "owned_work_removed": False})
        result["finished_unix"] = time.time()
        write_json(evidence / "RESULT.json", result)
        rows = [support.row(path, path.relative_to(evidence).as_posix()) for path in sorted(evidence.rglob("*"))
                if path.is_file() and path.name != "EVIDENCE_INDEX.json"]
        write_json(evidence / "EVIDENCE_INDEX.json", {
            "files": rows, "scope": "Actual generated source, compiler/new RPC control evidence and owned cleanup. No iOS framework, wallet/editor or production import acceptance."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
