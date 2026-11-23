#!/usr/bin/env python3
"""Generate a reviewed RPC through original tools in two disposable source copies.

No app, SDK or native test is executed. The generated message packages receive
real Go compilation and a Darwin SwiftProtobuf-only typecheck; neither proves
the Middleware endpoint, Invocation hook, iOS framework or production wiring.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import stat
import sys
import time
import zipfile

HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
SDK = "3be6ecab805b17e2c90fee897fdab45a0b03bfdc"
PLUGIN = "c6fe6442e6a64250495669325044052e113e990c"
SUPPORT_SHA = "aae68a25c0499d1bf61e98eca0ace9ffc48997823fdce9a775b22b239e904cdf"
SWIFT_SPARSE = ["/Makefile", "/Scripts/", "/Modules/ProtobufMessages/", "/Modules/Services/", "/Tools/anytype-swift-codegen", "/Tools/anytype-swift-filesplit/"]
NATIVE_INPUT_SCOPES = ["Makefile", "makefiles", "go.mod", "go.sum", "pb/protos", "pkg/lib/pb/model/protos", "pkg/lib/pb/storage/protos", "pkg/lib/bundle"]
SWIFT_INPUT_SCOPES = ["Makefile", "Scripts/install-sourcery.sh", "Scripts/install-swiftprotobuf.sh", "Modules/ProtobufMessages/Scripts", "Modules/ProtobufMessages/Templates", "Modules/ProtobufMessages/anytypeGen.yml", "Modules/ProtobufMessages/sourcery.yml", "Modules/Services/Templates", "Modules/Services/swiftgen.yml", "Tools/anytype-swift-codegen", "Tools/anytype-swift-filesplit"]
SWIFT_OUTPUT_SCOPES = ["Modules/ProtobufMessages/Sources/Protocol", "Modules/ProtobufMessages/Sources/Generated/CommandsInvocation", "Modules/ProtobufMessages/Sources/Generated/service+invocation.swift", "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift", "Modules/Services/Sources/Generated/BundledPropertyKey.swift", "Modules/Services/Sources/Generated/BundledPropertiesValueProvider.swift", "Modules/Services/Sources/Generated/BundledPropertyKey+SystemKeys.swift", "Modules/Services/Sources/Generated/BundledPropertyKey+internalKeys.swift", "Modules/Services/Sources/Generated/ObjectTypeUniqueKey+Bundled.swift"]


def file_row(path, relative):
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}


def checked_tree(root, scopes, git, tracked=True):
    if tracked:
        names = git(root, "ls-files", "-z", "--", *scopes).split("\0")
        paths = [root / name for name in names if name]
    else:
        paths = []
        for scope in scopes:
            path = root / scope
            paths.extend([path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()])
    result = []
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("unexpected missing/symlink source: " + str(path))
        result.append(file_row(path, path.relative_to(root).as_posix()))
    if not result:
        raise RuntimeError("empty source/output inventory")
    return result


def native_outputs(root):
    result = []
    for source, destination in (("pkg/lib/pb/model/protos", "pkg/lib/pb/model"), ("pkg/lib/pb/storage/protos", "pkg/lib/pb/storage"), ("pb/protos", "pb")):
        for path in sorted((root / source).glob("*.proto")):
            result.append(destination + "/" + path.stem + ".pb.go")
    result += ["clientlibrary/service/service.pb.go", "pb/service/service.pb.go", "docs/proto.md"]
    return result


def remove_owned_outputs(root, scopes):
    for scope in scopes:
        path = root / scope
        if path.is_symlink():
            raise RuntimeError("refusing output symlink: " + str(path))
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def retain_outputs(root, scopes, destination, git):
    rows = checked_tree(root, scopes, git, tracked=False)
    for row in rows:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / row["path"], target)
    return rows


def compare_rows(before, after):
    left, right = {r["path"]: r for r in before}, {r["path"]: r for r in after}
    return [{"path": p, "before": left.get(p), "after": right.get(p)} for p in sorted(left.keys() | right.keys()) if left.get(p) != right.get(p)]


def safe_archive(tool, archive, target):
    if archive.stat().st_size != tool["bytes"] or hashlib.sha256(archive.read_bytes()).hexdigest() != tool["sha256"]:
        raise RuntimeError("tool archive identity mismatch: " + tool["name"])
    target.mkdir()
    with zipfile.ZipFile(archive) as source:
        if source.testzip() is not None or len(source.namelist()) != len(set(source.namelist())):
            raise RuntimeError("tool archive CRC/duplicate failure")
        if tool["name"] == "protoc":
            selected = [(row["path"], row["path"].removeprefix(tool["extract_prefix"])) for row in tool["members"]]
        else:
            selected = [(tool["binary_member"], tool["binary_relative"])]
        for name, relative in selected:
            path = (target / relative).resolve()
            if not relative or not path.is_relative_to(target.resolve()) or source.getinfo(name).is_dir():
                raise RuntimeError("invalid exact archive member")
            if stat.S_ISLNK(source.getinfo(name).external_attr >> 16):
                raise RuntimeError("unexpected tool symlink")
            raw = source.read(name)
            if tool["name"] == "protoc":
                row = next(r for r in tool["members"] if r["path"] == name)
                if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                    raise RuntimeError("exact protoc member mismatch")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        binary = target / tool["binary_relative"]
        if hashlib.sha256(binary.read_bytes()).hexdigest() != tool["binary_sha256"]:
            raise RuntimeError("tool executable identity mismatch")
        binary.chmod(0o755)
    return binary


def main():
    parser = argparse.ArgumentParser()
    for name in ("control-root", "control-head", "packet", "manifest-sha256", "support", "heart-input", "swift-input", "plugin-input", "work", "evidence"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control = Path(args.control_root).resolve()
    packet = (control / args.packet).resolve()
    support = (control / args.support).resolve()
    if not packet.is_relative_to(control) or not support.is_relative_to(control):
        raise RuntimeError("control source escapes checkout")
    if hashlib.sha256(support.read_bytes()).hexdigest() != SUPPORT_SHA:
        raise RuntimeError("original owned-command helper differs")
    spec = importlib.util.spec_from_file_location("reviewed_native_command_support", support)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    git, digest, write_json = helper.git, helper.digest, helper.write_json
    continuation_spec = importlib.util.spec_from_file_location("rpc_continuation", packet / "continuation_support.py")
    continuation = importlib.util.module_from_spec(continuation_spec); continuation_spec.loader.exec_module(continuation)
    evidence = (control / args.evidence).resolve()
    work = (control / args.work).resolve()
    if not evidence.is_relative_to(control) or not work.is_relative_to(control) or evidence == work or work in evidence.parents or evidence in work.parents:
        raise RuntimeError("owned evidence/work roots overlap or escape")
    evidence.mkdir(parents=True, exist_ok=False)
    manifest_path = packet / "EXECUTION_INPUTS.json"
    result = {"schema": "otzaria.original-schema-rpc-generation-result/1", "status": "NOT_STARTED", "control_head": args.control_head, "manifest_sha256": args.manifest_sha256, "native_tests_executed": 0, "ios_build": False, "full_sdk_typecheck": False, "integration_authority": False}
    env = os.environ.copy()
    env.update({"GOTOOLCHAIN": "local", "GOWORK": "off", "GOFLAGS": "-mod=readonly", "PROTOBUF_NO_PROTOC": "true", "SHELLOPTS": "errexit:pipefail"})
    commands = helper.Commands(evidence, env, args.job_deadline_unix - 180)
    outputs, lanes, work_owned = {}, {}, False

    def interrupted(signum, _frame):
        # Permit the existing owned-group drain to finish after the first signal.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        raise KeyboardInterrupt("generation interrupted by signal " + str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        if not 0 < args.job_deadline_unix - time.time() <= 7200:
            raise RuntimeError("invalid finite generation deadline")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("actual Darwin ARM64 required")
        if git(control, "rev-parse", "HEAD") != args.control_head or git(control, "status", "--porcelain", "--untracked-files=no"):
            raise RuntimeError("control checkout is not the clean exact reviewed head")
        if digest(manifest_path) != args.manifest_sha256:
            raise RuntimeError("execution manifest differs")
        manifest = json.loads(manifest_path.read_bytes())
        for row in manifest["control_inputs"]:
            helper.check_file(packet, row)
        toolpins = json.loads((packet / "TOOL_PINS.json").read_bytes())
        inputs = {"heart": (control / args.heart_input).resolve(), "swift": (control / args.swift_input).resolve(), "plugin": (control / args.plugin_input).resolve()}
        for kind, expected in (("heart", HEART), ("swift", SDK), ("plugin", PLUGIN)):
            source = inputs[kind]
            if not source.is_relative_to(control) or source.is_relative_to(work) or git(source, "rev-parse", "HEAD") != expected or git(source, "status", "--porcelain", "--untracked-files=no"):
                raise RuntimeError("immutable input checkout differs: " + kind)
        source_roots = {"anyproto/anytype-heart": inputs["heart"], "davidpovarsky/anytype-swift": inputs["swift"], "apple/swift-protobuf": inputs["plugin"]}
        for row in manifest["original_inputs"]:
            helper.check_file(source_roots[row["repository"]], row)
        go_version = commands.require("go-version", ["go", "version"], control, 30).read_text().strip()
        if go_version != "go version go1.26.5 darwin/arm64":
            raise RuntimeError("wrong original Go toolchain")
        commands.require("xcode-version", ["xcodebuild", "-version"], control, 30)
        commands.require("swift-version", ["xcrun", "swift", "--version"], control, 30)
        commands.require("swift-target", ["xcrun", "swiftc", "-print-target-info"], control, 30)
        commands.require("make-version", ["make", "--version"], control, 30)
        work.mkdir(parents=True, exist_ok=False)
        work_owned = True
        for lane in ("baseline", "candidate"):
            lanes[lane] = {}
            for kind in ("heart", "swift"):
                target = work / (lane + "-" + kind)
                if kind == "swift":
                    # Copy the already materialized sparse checkout. A local Git
                    # clone would serve omitted promisor objects via upload-pack.
                    commands.require(lane + "-copy-materialized-swift", [
                        sys.executable, "-I", str(packet / "copy_materialized_checkout.py"),
                        "--source", str(inputs[kind]), "--target", str(target),
                        "--expected-head", SDK, "--receipt", str(evidence / (lane.upper() + "_SDK_COPY.json")),
                    ], control, 180)
                else:
                    commands.require(lane + "-clone-" + kind, ["git", "clone", "--no-hardlinks", "--no-checkout", str(inputs[kind]), str(target)], control, 180)
                    commands.require(lane + "-checkout-" + kind, ["git", "checkout", "--detach", HEART], target, 180)
                lanes[lane][kind] = target
        initial = {lane: {"heart": checked_tree(roots["heart"], NATIVE_INPUT_SCOPES, git), "swift": checked_tree(roots["swift"], SWIFT_INPUT_SCOPES, git)} for lane, roots in lanes.items()}
        if initial["baseline"] != initial["candidate"]:
            raise RuntimeError("baseline/candidate original source copies differ")
        write_json(evidence / "ORIGINAL_GENERATOR_INPUTS.json", initial["baseline"])
        outputs, previous_tools = continuation.restore_verified_baseline(
            packet / continuation.BASELINE_ARCHIVE, initial["baseline"], lanes["baseline"], evidence)
        result["baseline_generation_and_go"] = "REUSED_FROM_45055852172"
        base_swift, base_heart = lanes["baseline"]["swift"], lanes["baseline"]["heart"]
        codegen = file_row(base_swift / toolpins["original_codegen"]["path"], toolpins["original_codegen"]["path"])
        if codegen["git_blob"] != toolpins["original_codegen"]["git_blob"] or codegen["bytes"] != toolpins["original_codegen"]["bytes"]:
            raise RuntimeError("original tracked Anytype generator differs")
        tool_root = work / "tools"; tool_root.mkdir()
        tools = {}
        for tool in toolpins["archives"]:
            archive = tool_root / tool["archive_name"]
            commands.require("download-" + tool["name"], ["curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20", "--max-time", "180", "--output", str(archive), tool["url"]], control, 190)
            tools[tool["name"]] = safe_archive(tool, archive, tool_root / tool["name"])
        env["PATH"] = str(tools["protoc"].parent) + os.pathsep + env["PATH"]
        actual_protoc = commands.require("protoc-version", [str(tools["protoc"]), "--version"], control, 30).read_text().strip()
        if actual_protoc != toolpins["archives"][0]["expected_version"]:
            raise RuntimeError("protoc actual version differs")
        for name in ("sourcery", "swiftgen"):
            commands.require(name + "-version", [str(tools[name]), "--version"], control, 30)
        (base_swift / "build").mkdir(exist_ok=True)
        plugin = base_swift / "build/swift-protobuf"
        commands.require("clone-swift-protobuf", ["git", "clone", "--no-hardlinks", "--no-checkout", str(inputs["plugin"]), str(plugin)], control, 120)
        commands.require("checkout-swift-protobuf", ["git", "checkout", "--detach", PLUGIN], plugin, 60)
        commands.require("build-original-swift-protobuf", ["swift", "build", "-c", "release"], plugin, 1500)
        actual_bin_path = commands.require("swift-protobuf-bin-path", ["swift", "build", "-c", "release", "--show-bin-path"], plugin, 60).read_text()
        tools["protoc-gen-swift"], protobuf_module = continuation.resolve_swiftprotobuf_products(plugin, actual_bin_path)
        protobuf_module_rows = continuation.retain_module(protobuf_module, evidence / "swiftprotobuf-module")
        write_json(evidence / "ACTUAL_SWIFTPROTOBUF_MODULE.json", {"bin_path_output": actual_bin_path, "module": str(protobuf_module), "import_search_path": str(protobuf_module.parent), "files": protobuf_module_rows})
        make = ["make", "SHELL=/bin/bash", ".SHELLFLAGS=-e -o pipefail -c"]
        commands.require("build-original-filesplit", make + ["setup-file-splitter"], base_swift, 1800)
        tools["filesplit"] = base_swift / "build/anytype-swift-filesplit-v1"
        env["PATH"] = str(tools["protoc-gen-swift"].parent) + os.pathsep + env["PATH"]
        commands.require("build-original-gogo-plugins", make + ["setup-protoc-go"], base_heart, 1200)
        module = json.loads(commands.require("actual-gogo-module", ["go", "list", "-m", "-json", "github.com/gogo/protobuf"], base_heart, 60).read_bytes())
        if module["Version"] != toolpins["gogo"]["version"] or module["Replace"]["Path"] != toolpins["gogo"]["replacement"] or module["Replace"]["Version"] != toolpins["gogo"]["replacement_version"]:
            raise RuntimeError("original custom protobuf replacement differs")
        write_json(evidence / "ACTUAL_GOGO_MODULE.json", module)
        for row in manifest["gogo_inputs"]:
            helper.check_file(Path(module["Replace"]["Dir"]), row)
        for name in ("protoc-gen-gogofaster", "protoc-gen-gogofast", "protoc-gen-doc"):
            tools[name] = base_heart / "deps" / name
            commands.require("buildinfo-" + name, ["go", "version", "-m", str(tools[name])], base_heart, 30)
        tools["anytype-swift-codegen"] = base_swift / "Tools/anytype-swift-codegen"
        for name in ("go", "make", "bash"):
            tools[name] = Path(shutil.which(name)).resolve()
        for name in ("swift", "swiftc"):
            tools[name] = Path(commands.require("locate-" + name, ["xcrun", "--find", name], control, 30).read_text().strip()).resolve()
        tool_rows = [file_row(path, name) for name, path in sorted(tools.items())]
        write_json(evidence / "BASELINE_TOOL_COMPARISON.json", {"previous": previous_tools["tools"], "current": tool_rows, "changes": compare_rows(previous_tools["tools"], tool_rows), "scope": "Tool binaries were not retained. Rebuilt binary differences are explicit; identical pins do not claim identical binaries."})
        write_json(evidence / "ACTUAL_TOOL_EXECUTABLES.json", {"go_version": go_version, "protoc_version": actual_protoc, "tools": tool_rows, "archive_pins": toolpins["archives"], "scope": "Actual binaries measured before baseline/candidate generation. Downloaded tools were hash-checked before their version probes; built generators derive from pinned original source. Tool versions/build metadata are retained; complete OS/SDK binary closure is not claimed."})
        commands.require("swift-protobuf-version", [str(tools["protoc-gen-swift"]), "--version"], control, 30)
        for lane, roots in lanes.items():
            heart, swift = roots["heart"], roots["swift"]
            (swift / "build").mkdir(exist_ok=True)
            if lane == "candidate":
                (swift / "build/swift-protobuf").symlink_to(plugin, target_is_directory=True)
                shutil.copyfile(tools["filesplit"], swift / "build/anytype-swift-filesplit-v1")
                (swift / "build/anytype-swift-filesplit-v1").chmod(0o755)
                (heart / "deps").mkdir(exist_ok=True)
                for name in ("protoc-gen-gogofaster", "protoc-gen-gogofast", "protoc-gen-doc"):
                    shutil.copyfile(tools[name], heart / "deps" / name); (heart / "deps" / name).chmod(0o755)
                for entry in manifest["proto_afterimages"]:
                    original = heart / entry["path"]
                    if digest(original) != entry["before_sha256"]:
                        raise RuntimeError("proto original beforeimage differs")
                    shutil.copyfile(helper.check_file(packet, entry), original)
            for name in ("sourcery", "swiftgen"):
                shutil.copyfile(tools[name], swift / "build" / name); (swift / "build" / name).chmod(0o755)
            expected_native = native_outputs(heart)
            if lane == "candidate":
                remove_owned_outputs(heart, expected_native)
                (heart / "dist/ios/protobuf").mkdir(parents=True, exist_ok=True)
                commands.require(lane + "-original-native-generation", make + ["protos-go", "protos-server", "swift-protos"], heart, 600)
                for path in expected_native:
                    if not (heart / path).is_file() or not (heart / path).stat().st_size:
                        raise RuntimeError("fresh required native generated output missing: " + path)
                source_protos = list((heart / "pb/protos").glob("*.proto")) + list((heart / "pkg/lib/pb/model/protos").glob("*.proto"))
                for source in source_protos:
                    output = heart / "protobuf" / (source.stem + ".pb.swift")
                    if not output.is_file() or not output.stat().st_size:
                        raise RuntimeError("fresh original raw Swift output missing: " + str(output))
                middleware = swift / "Dependencies/Middleware"; middleware.mkdir(parents=True, exist_ok=True)
                shutil.copytree(heart / "protobuf", middleware / "protobuf", dirs_exist_ok=False)
                shutil.copytree(heart / "json", middleware / "json", dirs_exist_ok=False)
                remove_owned_outputs(swift, SWIFT_OUTPUT_SCOPES)
                commands.require(lane + "-original-swift-generation", make + ["generate-middle"], swift, 900)
                for path in SWIFT_OUTPUT_SCOPES:
                    if not (swift / path).exists():
                        raise RuntimeError("fresh required original Swift output missing: " + path)
            protocol_files = sorted((swift / "Modules/ProtobufMessages/Sources/Protocol").rglob("*.swift"))
            if not protocol_files:
                raise RuntimeError("empty generated Swift protocol family")
            response_file = work / (lane + "-swift-generated-inputs.rsp")
            response_file.write_text("\n".join('"' + str(p).replace('\\', '\\\\').replace('"', '\\"') + '"' for p in protocol_files) + "\n")
            outputs[lane] = {"native": retain_outputs(heart, expected_native, evidence / "generated" / lane / "native", git), "swift": retain_outputs(swift, SWIFT_OUTPUT_SCOPES, evidence / "generated" / lane / "swift", git), "middleware": retain_outputs(swift, ["Dependencies/Middleware/protobuf", "Dependencies/Middleware/json", "Dependencies/Middleware/genmodels"], evidence / "generated" / lane / "swift", git)}
            write_json(evidence / "GENERATED_OUTPUT_INDEX.json", outputs)
            if lane == "candidate":
                commands.require(lane + "-compile-generated-go", ["go", "build", "./pb", "./pb/service"], heart, 600)
            commands.require(lane + "-typecheck-generated-swift", ["xcrun", "swiftc", "-typecheck", "-module-name", "OtzariaGeneratedProtocolMessages", "-I", str(protobuf_module.parent), "@" + str(response_file)], swift, 900)
            after_native = checked_tree(heart, NATIVE_INPUT_SCOPES, git)
            after_swift = checked_tree(swift, SWIFT_INPUT_SCOPES, git)
            expected_changes = {e["path"]: (e["sha256"], e["bytes"]) for e in manifest["proto_afterimages"]} if lane == "candidate" else {}
            changes = compare_rows(initial[lane]["heart"], after_native)
            if {r["path"]: (r["after"]["sha256"], r["after"]["bytes"]) for r in changes} != expected_changes or after_swift != initial[lane]["swift"]:
                raise RuntimeError("generation changed an undeclared original input")
            write_json(evidence / (lane.upper() + "_GENERATED_INPUTS.json"), {"native": after_native, "swift": after_swift})
        generated_delta = {kind: compare_rows(outputs["baseline"][kind], outputs["candidate"][kind]) for kind in ("native", "swift", "middleware")}
        baseline_drift = {kind: compare_rows(outputs["tracked"][kind], outputs["baseline"][kind]) for kind in ("native", "swift")}
        write_json(evidence / "GENERATED_OUTPUT_INDEX.json", outputs)
        write_json(evidence / "GENERATED_DELTA.json", {"candidate_vs_retained_baseline": generated_delta, "baseline_vs_original_tracked": baseline_drift, "scope": "Retained baseline generation/Go remain bound to run45055852172. Candidate uses rebuilt pinned tools with separately measured hashes; binary identity is not assumed."})
        allowed_native = {"pb/commands.pb.go", "pb/service/service.pb.go", "clientlibrary/service/service.pb.go", "docs/proto.md"}
        allowed_swift = ("Modules/ProtobufMessages/Sources/Protocol/Commands/", "Modules/ProtobufMessages/Sources/Generated/CommandsInvocation/", "Modules/ProtobufMessages/Sources/Generated/service+invocation.swift", "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift")
        if any(r["path"] not in allowed_native for r in generated_delta["native"]) or any(not r["path"].startswith(allowed_swift) for r in generated_delta["swift"]):
            raise RuntimeError("candidate changes generated state outside reviewed RPC output scope")
        if not generated_delta["native"] or not generated_delta["swift"]:
            raise RuntimeError("missing actual candidate generated RPC delta")
        if [file_row(path, name) for name, path in sorted(tools.items())] != tool_rows:
            raise RuntimeError("generator executable changed during use")
        if continuation.retain_module(protobuf_module, evidence / "swiftprotobuf-module-after") != protobuf_module_rows:
            raise RuntimeError("SwiftProtobuf module changed during use")
        for row in manifest["control_inputs"]:
            helper.check_file(packet, row)
        for kind, expected in (("heart", HEART), ("swift", SDK), ("plugin", PLUGIN)):
            if git(inputs[kind], "rev-parse", "HEAD") != expected or git(inputs[kind], "status", "--porcelain", "--untracked-files=no"):
                raise RuntimeError("immutable input checkout changed")
        result.update({"status": "GENERATED_AND_MESSAGE_COMPILE_VERIFIED", "generated_delta_counts": {k: len(v) for k, v in generated_delta.items()}, "baseline_drift_counts": {k: len(v) for k, v in baseline_drift.items()}, "go_message_packages_compiled": ["./pb", "./pb/service"], "swift_generated_models_typechecked": True, "endpoint_invocation_and_sdk_compiled": False, "generated_outputs_require_review_before_integration": True, "original_inputs_unchanged_except_two_candidate_protos": True, "tool_executables_unchanged": True})
    except BaseException as error:
        result.update({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
    finally:
        result["commands"] = len(commands.items)
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        if result["status"] == "FAIL" and work_owned:
            partial = {"scope": "Failure-time bytes only; these may include old tracked or partially generated files and confer no generation/compile success.", "lanes": {}}
            for lane, roots in lanes.items():
                partial["lanes"][lane] = {}
                for kind, root in roots.items():
                    scopes = native_outputs(root) + ["protobuf", "json"] if kind == "heart" else SWIFT_OUTPUT_SCOPES + ["Dependencies/Middleware"]
                    try:
                        partial["lanes"][lane][kind] = retain_outputs(root, scopes, evidence / "failure-time" / lane / kind, git)
                    except Exception as capture_error:
                        partial["lanes"][lane][kind] = {"capture_error": str(capture_error)}
            write_json(evidence / "FAILURE_OUTPUT_INDEX.json", partial)
        if commands.owned_groups_drained and work_owned and work.exists():
            try:
                shutil.rmtree(work)
                result["owned_work_removed"] = True
            except Exception as error:
                result["status"] = "FAIL"; result["cleanup_error"] = str(error)
        elif work_owned and work.exists():
            result["owned_work_removed"] = False; result["status"] = "FAIL"
        result["finished_unix"] = time.time()
        write_json(evidence / "RESULT.json", result)
        files = [file_row(p, p.relative_to(evidence).as_posix()) for p in sorted(evidence.rglob("*")) if p.is_file() and p.name != "EVIDENCE_INDEX.json"]
        write_json(evidence / "EVIDENCE_INDEX.json", {"files": files, "scope": "Complete generated source variants and owned command logs retained; no compiled application or runtime acceptance."})
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "GENERATED_AND_MESSAGE_COMPILE_VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
