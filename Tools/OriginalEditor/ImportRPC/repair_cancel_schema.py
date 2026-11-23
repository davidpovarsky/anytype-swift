#!/usr/bin/env python3
"""Append the missing Cancel error and regenerate its original dependency closure.

Generated source is produced only by pinned original protoc/plugins, filesplit and
Sourcery. Earlier successful output/typecheck evidence applies only to identical
files; the changed Swift primary files receive a new actual compiler invocation.
"""
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True

def apply_schema(raw, spec, row_bytes):
    before = spec["before"]
    if row_bytes(raw, before["path"]) != before:
        raise RuntimeError("Cancel schema preimage differs")
    old, new = spec["before_fragment"].encode(), spec["after_fragment"].encode()
    if raw.count(old) != 1 or new != old.replace(
            b"                            RUNTIME_UNAVAILABLE = 2;\n",
            b"                            RUNTIME_UNAVAILABLE = 2;\n"
            b"                            UNKNOWN_ERROR = 3;\n", 1):
        raise RuntimeError("Cancel schema transform is not the one reviewed append")
    changed = raw.replace(old, new, 1)
    if row_bytes(changed, spec["after"]["path"]) != spec["after"]:
        raise RuntimeError("Cancel schema afterimage differs")
    return changed

def bytes_row(raw, path):
    import hashlib
    return {"path": path, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}

def validate_output_delta(before, after, expected):
    if set(before) != set(after) or set(before) != set(expected):
        raise RuntimeError("Generated family set differs")
    delta = {}
    for family in before:
        left = {r["path"]: r for r in before[family]}
        right = {r["path"]: r for r in after[family]}
        if len(left) != len(before[family]) or len(right) != len(after[family]) or left.keys() != right.keys():
            raise RuntimeError("Original generated file set changed")
        names = sorted(p for p in left if left[p] != right[p])
        if names != sorted(expected[family]):
            raise RuntimeError("Unreviewed generated delta in " + family + ": " + repr(names))
        delta[family] = [{"path": p, "before": left[p], "after": right[p]} for p in names]
    return delta

def authenticate_failure(control, work, evidence, pin, commands, intake):
    failure = pin["compile_failure"]
    values = {}
    for kind, endpoint in (("run", "actions/runs/" + str(failure["run_id"])),
                           ("artifact", "actions/artifacts/" + str(failure["artifact_id"]))):
        p = commands.require("reuse-compile-failure-" + kind,
            ["gh", "api", "repos/" + pin["repository"] + "/" + endpoint], control, 60)
        values[kind] = json.loads(p.read_bytes())
    run, artifact = values["run"], values["artifact"]
    intake.require(run["head_sha"] == failure["head_sha"] and run["run_attempt"] == 1
        and run["id"] == failure["run_id"] and run["status"] == "completed"
        and run["conclusion"] == "failure" and run["event"] == "push"
        and run["head_branch"] == failure["head_branch"] and run["path"] == failure["workflow_path"]
        and run["repository"]["full_name"] == pin["repository"], "Actual compiler failure run differs")
    intake.require(artifact["id"] == failure["artifact_id"] and not artifact["expired"]
        and artifact["name"] == failure["artifact_name"]
        and artifact["size_in_bytes"] == failure["artifact_bytes"]
        and artifact["digest"] == "sha256:" + failure["artifact_sha256"]
        and artifact["workflow_run"]["id"] == failure["run_id"]
        and artifact["workflow_run"]["head_sha"] == failure["head_sha"], "Compiler failure artifact differs")
    archive = commands.require("download-actual-compile-failure",
        ["gh","api","repos/" + pin["repository"] + "/actions/artifacts/" + str(failure["artifact_id"]) + "/zip"],
        control, 240)
    root = work / "actual-compile-failure"
    receipt = intake.unpack(archive, root, failure)
    intake.require(receipt == {"crc_members":805, "indexed_files":804}, "Compiler failure index closure differs")
    result = json.loads((root / "RESULT.json").read_bytes())
    recorded = json.loads((root / "COMMANDS.json").read_bytes())
    intake.require(result["status"] == "FAIL" and result["control_head"] == failure["head_sha"]
        and result["schema"] == "otzaria.original-import-rpc-native-qualification-result/1"
        and result["native_source_tree"] == pin["generated_native_tree"]
        and result["error"] == "owned command failed: compile-generated-go-and-original-mobile-export-source"
        and result["owned_command_groups_drained"] and result["owned_work_removed"]
        and not result["new_rpc_controls"] and len(recorded) == result["commands"] == 17
        and all(c["effective_returncode"] == 0 and not c["timed_out"] for c in recorded[:-1])
        and recorded[-1]["effective_returncode"] == 1 and not recorded[-1]["timed_out"]
        and recorded[-1]["argv"] == ["go","build","-p","2","./pb","./pb/service","./clientlibrary/service"],
        "Actual compiler failure boundary differs")
    log = root / recorded[-1]["stderr"]
    intake.require(intake.sha(log) == failure["compiler_stderr_sha256"], "Actual compiler diagnostic differs")
    intake.write(evidence / "AUTHENTICATED_COMPILE_FAILURE.json",
        {"metadata":values,"intake":receipt,"result":result,"command":recorded[-1],
         "raw_stderr":log.read_text(),"scope":"Historical failure retained; it supplies no RPC pass."})
    return root

def repair(control, packet, heart, swift_input, plugin_input, work, evidence,
           prior, generated, pin, commands, env, support, original, intake, result):
    spec = pin["schema_transform"]
    intake.require(spec["native_path"] == "pb/protos/commands.proto", "Unexpected schema transform path")
    schema = support.relative_path(heart, spec["native_path"])
    raw = schema.read_bytes()
    after = apply_schema(raw, spec, bytes_row)
    schema.write_bytes(after)
    retained_schema = evidence / "schema-source/pb/protos/commands.proto"
    retained_schema.parent.mkdir(parents=True, exist_ok=True)
    retained_schema.write_bytes(after)
    intake.write(evidence / "CANCEL_ERROR_SCHEMA_TRANSFORM.json", spec)
    commands.require("seal-reviewed-cancel-schema", ["git","add","--",spec["native_path"]], heart, 60)

    retained = packet / "retained-original"
    continuation = support.load_module(retained / "continuation_support.py",
                                      "cancel_repair_swift_products", support.CONTINUATION_SHA)
    swift = work / "candidate-swift"
    for source, expected in ((swift_input,support.SWIFT),(plugin_input,support.PLUGIN)):
        intake.require(support.git(source,"rev-parse","HEAD") == expected
            and not support.git(source,"status","--porcelain","--untracked-files=no"),
            "Immutable original Swift/tool input differs")
    commands.require("copy-original-swift-input", [
        sys.executable,"-I",str(retained / "copy_materialized_checkout.py"),
        "--source",str(swift_input),"--target",str(swift),"--expected-head",support.SWIFT,
        "--receipt",str(evidence / "SWIFT_COPY.json")], control, 180)
    swift_inputs = original.checked_tree(swift, original.SWIFT_INPUT_SCOPES, support.git)
    previous_inputs = json.loads((prior / "ACTUAL_GENERATOR_INPUTS.json").read_bytes())
    intake.require(swift_inputs == previous_inputs["swift"], "Original Swift generator source differs")
    invocation = support.row(swift / "Modules/ProtobufMessages/Sources/Invocation.swift",
                             "Modules/ProtobufMessages/Sources/Invocation.swift")
    intake.require(invocation == previous_inputs["preserved_invocation"], "Original typed Invocation differs")
    original.remove_owned_outputs(swift, original.SWIFT_OUTPUT_SCOPES)
    for family in ("swift","middleware"):
        for item in generated[family]:
            dest = support.relative_path(swift, item["path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(prior / "generated/candidate/swift" / item["path"], dest)

    native_inputs = original.checked_tree(heart, original.NATIVE_INPUT_SCOPES, support.git)
    delta_inputs = original.compare_rows(previous_inputs["native"], native_inputs)
    intake.require(delta_inputs == [{"path":spec["native_path"],"before":spec["before"],"after":spec["after"]}],
                   "Original native generator inputs changed beyond reviewed Cancel enum")
    intake.write(evidence / "ACTUAL_REPAIRED_GENERATOR_INPUTS.json",
        {"native":native_inputs,"swift":swift_inputs,"preserved_invocation":invocation,
         "native_delta":delta_inputs})

    tools_root = work / "repair-tools"
    tools_root.mkdir()
    tools = {}
    toolpins = json.loads((retained / "TOOL_PINS.json").read_bytes())
    for tool in (t for t in toolpins["archives"] if t["name"] in ("protoc","sourcery")):
        archive = tools_root / tool["archive_name"]
        commands.require("download-original-" + tool["name"], ["curl","--fail","--location","--silent",
            "--show-error","--connect-timeout","20","--max-time","180","--output",str(archive),tool["url"]],control,190)
        tools[tool["name"]] = original.safe_archive(tool,archive,tools_root / tool["name"])
    env["PATH"] = str(tools["protoc"].parent) + os.pathsep + env["PATH"]
    env["SHELLOPTS"] = "errexit:pipefail"
    version = commands.require("original-protoc-version",[str(tools["protoc"]),"--version"],control,30).read_text().strip()
    intake.require(version == "libprotoc 32.1", "Original protoc version differs")
    commands.require("original-sourcery-version",[str(tools["sourcery"]),"--version"],control,30)
    (swift / "build").mkdir(exist_ok=True)
    plugin = swift / "build/swift-protobuf"
    commands.require("clone-original-swift-protobuf",["git","clone","--no-hardlinks","--no-checkout",
        str(plugin_input),str(plugin)],control,180)
    commands.require("checkout-original-swift-protobuf",["git","checkout","--detach",support.PLUGIN],plugin,60)
    commands.require("build-original-swift-protobuf",["swift","build","-c","release"],plugin,1500)
    bin_path = commands.require("original-swift-protobuf-bin-path",
        ["swift","build","-c","release","--show-bin-path"],plugin,60).read_text()
    tools["protoc-gen-swift"], protobuf_module = continuation.resolve_swiftprotobuf_products(plugin,bin_path)
    module_rows = continuation.retain_module(protobuf_module,evidence / "swiftprotobuf-module")
    intake.write(evidence / "ACTUAL_REPAIR_SWIFTPROTOBUF_MODULE.json",
        {"module":str(protobuf_module),"files":module_rows,"source":support.PLUGIN,"bin_path_output":bin_path})
    make = ["make","SHELL=/bin/bash",".SHELLFLAGS=-e -o pipefail -c"]
    commands.require("build-original-filesplit",make + ["setup-file-splitter"],swift,1800)
    tools["filesplit"] = swift / "build/anytype-swift-filesplit-v1"
    resolved = json.loads((swift / "Tools/anytype-swift-filesplit/Package.resolved").read_bytes())
    pins = resolved.get("pins",resolved.get("object",{}).get("pins",[]))
    observed = [{"identity":p["identity"],"version":p["state"].get("version"),"revision":p["state"]["revision"]} for p in pins]
    intake.require(sorted(observed,key=lambda p:p["identity"]) == sorted(toolpins["filesplit"]["pins"],key=lambda p:p["identity"]),
                   "Original filesplit resolved dependencies differ")
    commands.require("build-original-gogo-plugins",make + ["setup-protoc-go"],heart,1200)
    gogo = json.loads(commands.require("actual-original-gogo-module",
        ["go","list","-m","-json","github.com/gogo/protobuf"],heart,60).read_bytes())
    intake.require(gogo["Version"] == toolpins["gogo"]["version"]
        and gogo["Replace"]["Path"] == toolpins["gogo"]["replacement"]
        and gogo["Replace"]["Version"] == toolpins["gogo"]["replacement_version"],
        "Original gogo replacement differs")
    manifest = json.loads((packet / "EXECUTION_INPUTS.json").read_bytes())
    support.check_rows(Path(gogo["Replace"]["Dir"]), manifest["gogo_inputs"])
    intake.write(evidence / "ACTUAL_REPAIR_GOGO_MODULE.json",gogo)
    for name in ("protoc-gen-gogofaster","protoc-gen-gogofast","protoc-gen-doc"):
        tools[name] = heart / "deps" / name
        commands.require("buildinfo-" + name,["go","version","-m",str(tools[name])],heart,30)
    for name in ("swift","swiftc"):
        tools[name] = Path(commands.require("locate-" + name,["xcrun","--find",name],control,30).read_text().strip()).resolve()
    old_tools = json.loads((prior / "ACTUAL_TOOL_EXECUTABLES.json").read_bytes())
    prior_swiftc = next(r for r in old_tools["tools"] if r["path"] == "swiftc")
    intake.require(support.row(tools["swiftc"],"swiftc") == prior_swiftc,
        "Compiler identity changed; prior unchanged-file typecheck cannot be reused")
    for name in ("go","make","bash"):
        tools[name] = Path(shutil.which(name,path=env["PATH"])).resolve()
    env["PATH"] = str(heart / "deps") + os.pathsep + str(tools["protoc-gen-swift"].parent) + os.pathsep + env["PATH"]
    tool_rows = [support.row(path,name) for name,path in sorted(tools.items())]
    intake.write(evidence / "ACTUAL_REPAIR_TOOL_EXECUTABLES.json",
        {"tools":tool_rows,"protoc_version":version,"original_swiftc_exactly_reused":True})

    # Same original Makefile package map and plugin settings. Only commands.proto
    # changed; other native message files and service wrappers are reused exactly.
    pkgmap = ",".join([
        "Mgoogle/protobuf/timestamp.proto=github.com/gogo/protobuf/types",
        "Mgoogle/protobuf/struct.proto=github.com/gogo/protobuf/types",
        "Mpkg/lib/pb/model/protos/models.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
        "Mpkg/lib/pb/model/protos/export_report.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
        "Mpkg/lib/pb/model/protos/localstore.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
        "",
        "Mgoogle/protobuf/descriptor.proto=github.com/gogo/protobuf/protoc-gen-gogo/descriptor"])
    env["GOGO_NO_UNDERSCORE"] = "1"
    env["GOGO_EXPORT_ONEOF_INTERFACE"] = "1"
    result["generator_native_invocations"] += 1
    commands.require("original-protoc-changed-go-commands",
        ["protoc","-I",".","--gogofaster_out=" + pkgmap + ":.","./pb/protos/commands.proto"],heart,600)
    staged_go = heart / "pb/protos/commands.pb.go"
    intake.require(staged_go.is_file(), "Original generator did not emit changed Go commands")
    shutil.move(str(staged_go),str(heart / "pb/commands.pb.go"))
    result["generator_documentation_invocations"] = 1
    commands.require("original-proto-documentation",make + ["protos-docs"],heart,600)

    raw_swift = work / "raw-swift-commands"
    raw_swift.mkdir()
    result["generator_swift_invocations"] += 1
    commands.require("original-protoc-changed-raw-swift",
        ["protoc","-I","./","--swift_opt=FileNaming=DropPath","--swift_opt=Visibility=Public",
         "--swift_out=" + str(raw_swift),"pb/protos/commands.proto"],heart,600)
    middle = swift / "Dependencies/Middleware"
    shutil.copyfile(raw_swift / "commands.pb.swift",middle / "protobuf/commands.pb.swift")
    flat_proto = middle / "protobuf/protos/commands.proto"
    flat_proto.write_bytes(after)
    # Verbatim sed expression from original generate_models.sh; .bak retains raw input.
    sed = r'/import[[:space:]]+"google\/protobuf\//! s#(import[[:space:]]+")([^"/]+/)*([^"/]+\.proto)"#\1\3"#g'
    commands.require("original-flatten-changed-proto-imports",
        ["sed","-i.bak","-E",sed,str(flat_proto)],swift,60)
    intake.require(flat_proto.with_suffix(".proto.bak").read_bytes() == after, "Original raw proto backup differs")
    result["generator_swift_invocations"] += 1
    commands.require("original-protoc-changed-swift-models",
        ["protoc","--plugin=protoc-gen-swift=" + str(tools["protoc-gen-swift"]),
         "--swift_opt=FileNaming=DropPath","--swift_opt=Visibility=Public",
         "--swift_out=" + str(middle / "genmodels"),"--proto_path=" + str(flat_proto.parent),str(flat_proto)],swift,600)
    commands_dir = swift / "Modules/ProtobufMessages/Sources/Protocol/Commands"
    original.remove_owned_outputs(swift,["Modules/ProtobufMessages/Sources/Protocol/Commands"])
    result["original_filesplit_invocations"] = 1
    commands.require("original-split-changed-commands",
        [str(tools["filesplit"]),"--path",str(middle / "genmodels/commands.pb.swift"),
         "--output-dir",str(commands_dir),"--other-name","CommandsOther.swift"],swift,600)
    result["original_sourcery_invocations"] = 1
    commands.require("original-generate-changed-error-localization",
        [str(tools["sourcery"]),"--config",str(swift / "Modules/ProtobufMessages/Scripts/Loc/sourcery.yml")],swift,600)

    regenerated = {
        "native":original.retain_outputs(heart,original.native_outputs(heart),evidence / "generated/candidate/native",support.git),
        "swift":original.retain_outputs(swift,original.SWIFT_OUTPUT_SCOPES,evidence / "generated/candidate/swift",support.git),
        "middleware":original.retain_outputs(swift,["Dependencies/Middleware/protobuf","Dependencies/Middleware/json",
            "Dependencies/Middleware/genmodels"],evidence / "generated/candidate/swift",support.git)}
    delta = validate_output_delta(generated,regenerated,pin["allowed_generated_deltas"])
    intake.write(evidence / "GENERATED_OUTPUT_INDEX.json",regenerated)
    intake.write(evidence / "CANCEL_ERROR_GENERATED_DELTA.json", {
        "deltas":delta,"unchanged_files_reused":{k:len(v)-len(delta[k]) for k,v in generated.items()},
        "scope":"Only explicitly changed original generated bytes require new typecheck; all other files exactly equal authenticated prior generation."})
    commands.require("seal-repaired-native-output",["git","add","--",spec["native_path"],
        *[r["path"] for r in regenerated["native"]]],heart,60)
    native_tree = commands.require("actual-repaired-native-tree",["git","write-tree"],heart,30).read_text().strip()
    result["native_source_tree"] = native_tree
    intake.write(evidence / "GENERATED_NATIVE_SOURCE_TREE.json",
        {"base":support.HEART,"prior_generated_tree":pin["generated_native_tree"],
         "native_source_tree":native_tree,"schema_transform":spec,"generated_inputs":regenerated["native"]})

    protocol_files = sorted((swift / "Modules/ProtobufMessages/Sources/Protocol").rglob("*.swift"))
    primary_names = pin["changed_swift_typecheck_primary_paths"]
    primaries = [support.relative_path(swift,p) for p in primary_names]
    intake.require(sorted(primary_names) == sorted(pin["allowed_generated_deltas"]["swift"]),
                   "Changed Swift primary-file set differs from generated delta")
    arguments = []
    for path in protocol_files + [swift / "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift"]:
        if path in primaries:
            arguments.append("-primary-file")
        arguments.append(str(path))
    response = work / "changed-swift-primary-inputs.rsp"
    response.write_text("\n".join('"' + value.replace("\\","\\\\").replace('"','\\"') + '"' for value in arguments) + "\n")
    result["swift_typecheck_invocations"] += 1
    commands.require("typecheck-changed-original-swift-primary-files",
        ["xcrun","swiftc","-frontend","-typecheck","-module-name","OtzariaGeneratedImportProtocol",
         "-I",str(protobuf_module.parent),"@" + str(response)],swift,1200)
    result["changed_swift_primary_typecheck"] = "PASS"
    result["changed_swift_primary_paths"] = primary_names
    intake.write(evidence / "CHANGED_SWIFT_PRIMARY_TYPECHECK.json",
        {"status":"PASS","primary_paths":primary_names,
         "all_input_files":[support.row(p,p.relative_to(swift).as_posix()) for p in protocol_files + [primaries[-1]]],
         "prior_typecheck_scope":"Only unchanged files at their exact authenticated hashes. Changed primary bytes checked in this new invocation.",
         "compiler":support.row(tools["swiftc"],"swiftc"),"swift_protobuf_module":module_rows})

    support.check_rows(heart,native_inputs)
    support.check_rows(swift,swift_inputs)
    support.check_rows(swift,regenerated["swift"])
    support.check_rows(swift,regenerated["middleware"])
    intake.require(support.row(swift / invocation["path"],invocation["path"]) == invocation,
                   "Original typed Invocation changed")
    intake.require([support.row(path,name) for name,path in sorted(tools.items())] == tool_rows,
                   "Original generator tool changed during use")
    intake.require(continuation.retain_module(protobuf_module,evidence / "swiftprotobuf-module-after") == module_rows,
                   "Actual SwiftProtobuf module changed during affected typecheck")
    for source,expected in ((swift_input,support.SWIFT),(plugin_input,support.PLUGIN)):
        intake.require(support.git(source,"rev-parse","HEAD") == expected
            and not support.git(source,"status","--porcelain","--untracked-files=no"),
            "Immutable original Swift/tool input changed")
    result["schema_repair_generated_output_closure"] = "PASS"
    result["unchanged_generated_typecheck_reuse_only"] = True
    return regenerated
