#!/usr/bin/env python3
"""Compile complete current Integration/probe targets using proven cached deps.

No SwiftPM resolver/planner, dependency compiler, or replacement implementation.
Exact SwiftPM compiler/linker arguments come from its existing description/YAML.
The two changed targets compile in full into a private output directory.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reuse-compiles", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = {"status": "FAIL", "scope": "Complete current PinkhaAnyIntegration and IntegrationProbe Swift targets; cached Kit/Engine/Crypto dependency source pins verified against the completed provider build; no SwiftPM planning success claim.", "steps": []}
    before = helper.source_snapshot(root, Path(__file__))
    helper.write_json(out / "source-before.json", before)
    shutil.copyfile(__file__, out / "executed-build-runner.py")
    shutil.copyfile(helper_path, out / "executed-process-helper.py")
    result["sourceInputs"] = {p: v["sha256"] for p, v in before["files"].items() if p.startswith("Modules/")}
    result["harnessInputs"] = {Path(__file__).resolve().relative_to(root).as_posix(): helper.sha256(Path(__file__)),
                               helper_path.relative_to(root).as_posix(): helper.sha256(helper_path)}
    try:
        prior_path = root / "Tools/AnyEngineValidation/evidence/live-public-provider-windows-v2/source-before.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        for relative, value in before["files"].items():
            if relative.startswith(("Modules/PinkhaKit/", "Modules/PinkhaAnyEngine/")):
                if prior["files"].get(relative) != value:
                    raise RuntimeError("cached_dependency_source_changed:" + relative)
        if prior["dependencies"] != before["dependencies"]:
            raise RuntimeError("cached_external_dependency_source_changed")
        result["cachedDependencySourceReceiptSHA256"] = helper.sha256(prior_path)
        build = root / "Modules/PinkhaAnyIntegration/.build"
        description_path = build / "x86_64-unknown-windows-msvc/debug/description.json"
        description = json.loads(description_path.read_text(encoding="utf-8"))
        result["swiftPMDescriptionSHA256"] = helper.sha256(description_path)
        yaml_path = build / "debug.yaml"
        result["swiftPMBuildYAMLSHA256"] = helper.sha256(yaml_path)
        commands = description["swiftCommands"]
        component_dir = out
        reuse = None
        if args.reuse_compiles:
            component_dir = args.reuse_compiles.resolve()
            reuse_path = component_dir / "result.json"
            reuse = json.loads(reuse_path.read_text(encoding="utf-8"))
            if reuse.get("status") != "FAIL" or reuse.get("errorCode") != "target_link_objects_not_complete" or reuse.get("sourceStable") is not True:
                raise RuntimeError("unsupported_compilation_reuse_receipt")
            if len(reuse.get("steps", [])) != 2:
                raise RuntimeError("reused_target_compile_steps_incomplete")
            for step in reuse["steps"]:
                if step.get("exitCode") != 0 or step.get("timedOut") or step.get("cleanupErrors") or step.get("runnerErrorType"):
                    raise RuntimeError("failed_compilation_cannot_be_reused")
            for relative, sha in result["sourceInputs"].items():
                if reuse["sourceInputs"].get(relative) != sha:
                    raise RuntimeError("reused_compilation_source_changed:" + relative)
            old_before = json.loads((component_dir / "source-before.json").read_text(encoding="utf-8"))
            script_key = "Tools/AnyEngineValidation/build_guarded_hierarchy_components.py"
            if helper.sha256(component_dir / "executed-build-runner.py") != old_before["files"][script_key]["sha256"]:
                raise RuntimeError("original_compile_harness_archive_mismatch")
            result["reusedSuccessfulCompilation"] = {"receipt": str(reuse_path), "sha256": helper.sha256(reuse_path),
                "originalFailureRetained": True, "reason": "Both complete compiler steps succeeded; only the old executable link-list preflight rejected the newly added source object."}
        module_dir = component_dir / "Modules"
        if not reuse:
            module_dir.mkdir()
        new_objects = []
        original_targets = set()
        added_targets = set()
        for name in ["PinkhaAnyIntegration", "PinkhaAnyIntegrationProbe"]:
            command = commands["C." + name + "-x86_64-unknown-windows-msvc-debug.module"]
            files = sorted((root / "Modules/PinkhaAnyIntegration/Sources" / name).glob("*.swift"))
            if {p.resolve() for p in files} != {Path(p).resolve() for p in command["sources"]}:
                raise RuntimeError("target_source_graph_differs:" + name)
            target_dir = component_dir / name
            if not reuse:
                target_dir.mkdir()
            output_map = {}
            for source in files:
                obj = target_dir / (source.name + ".o")
                output_map[str(source)] = {"object": str(obj)}
                new_objects.append(obj)
            original_map = json.loads(Path(command["outputFileMapPath"]).read_text(encoding="utf-8"))
            for source in files:
                if source.relative_to(root).as_posix() not in prior["files"]:
                    added_targets.add(Path(original_map[str(source)]["object"]).resolve())
            map_path = target_dir / "output-file-map.json"
            if not reuse:
                helper.write_json(map_path, output_map)
            original_targets.update(Path(p).resolve() for p in command["objects"])
            if reuse:
                producer = next((step for step in reuse["steps"] if step["name"] == name), None)
                if producer is None or producer.get("sourceCount") != len(files):
                    raise RuntimeError("reused_target_source_count_mismatch")
                if not all(Path(item["object"]).is_file() for item in output_map.values()):
                    raise RuntimeError("reused_target_object_missing")
                if not (module_dir / (name + ".swiftmodule")).is_file():
                    raise RuntimeError("reused_target_module_missing")
                result["steps"].append({**producer, "reusedFromRetainedCompilerReceipt": True})
                continue
            arguments = command["otherArguments"]
            filtered = []
            i = 0
            while i < len(arguments):
                arg = arguments[i]
                if arg in ("-incremental", "-serialize-diagnostics", "-parseable-output", "-emit-objc-header"):
                    i += 1
                    continue
                if arg in ("-index-store-path", "-emit-objc-header-path"):
                    i += 2
                    continue
                filtered.append(arg)
                i += 1
            argv = [command["executable"], "-module-name", name, "-emit-module", "-emit-module-path",
                    str(module_dir / (name + ".swiftmodule")), "-c", "-parse-as-library", "-I", str(module_dir),
                    "-I", command["importPath"], "-output-file-map", str(map_path)] + filtered + [str(p) for p in files]
            stage = target_dir / "process"
            stage.mkdir()
            status = helper.run_process(argv, root, stage, 240)
            result["steps"].append({"name": name, "sourceCount": len(files), **status})
            if status.get("exitCode") != 0 or status.get("timedOut") or status.get("cleanupErrors") or status.get("runnerErrorType"):
                raise RuntimeError("actual_target_compile_failed:" + name)
        # Select the actual executable link command, not the test product.
        link = None
        wrappers = {}
        for line in yaml_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("    args: ["):
                value = json.loads(line.split(": ", 1)[1])
                if "-modulewrap" in value and "-o" in value:
                    source = Path(value[value.index("-modulewrap") + 1]).resolve()
                    for name in ["PinkhaAnyIntegration", "PinkhaAnyIntegrationProbe"]:
                        expected = Path(commands["C." + name + "-x86_64-unknown-windows-msvc-debug.module"]["moduleOutputPath"]).resolve()
                        if source == expected:
                            if name in wrappers:
                                raise RuntimeError("duplicate_module_wrapper_command")
                            wrappers[name] = value
                if "-emit-executable" in value and "-o" in value and Path(value[value.index("-o") + 1]).name == "pinkha-any-integration-probe.exe":
                    if link is not None:
                        raise RuntimeError("multiple_link_commands")
                    link = value
        if link is None:
            raise RuntimeError("native_swift_link_command_missing")
        lists = [x[1:] for x in link if x.startswith("@")]
        if len(lists) != 1:
            raise RuntimeError("unexpected_link_response_files")
        cached_objects = [Path(line.strip().strip('"')).resolve() for line in Path(lists[0]).read_text(encoding="utf-8").splitlines() if line.strip()]
        missing = original_targets - set(cached_objects)
        if not missing.issubset(added_targets):
            raise RuntimeError("old_link_list_omits_existing_source_object")
        if set(wrappers) != {"PinkhaAnyIntegration", "PinkhaAnyIntegrationProbe"}:
            raise RuntimeError("target_module_wrapper_commands_missing")
        wrapper_outputs = {Path(command[command.index("-o") + 1]).resolve() for command in wrappers.values()}
        expected_old_targets = original_targets | wrapper_outputs
        existing_old_targets = {p for p in cached_objects if p.parent.name in {"PinkhaAnyIntegration.build", "PinkhaAnyIntegrationProbe.build"}}
        if existing_old_targets - expected_old_targets or not wrapper_outputs.issubset(set(cached_objects)):
            raise RuntimeError("old_target_link_closure_unrecognized")
        result["addedObjectsAbsentFromOldLinkList"] = [str(p) for p in sorted(missing)]
        for name, argv in wrappers.items():
            original = Path(argv[argv.index("-o") + 1])
            stage = out / ("wrap-" + name)
            stage.mkdir()
            wrapped = stage / original.name
            argv[argv.index("-modulewrap") + 1] = str(module_dir / (name + ".swiftmodule"))
            argv[argv.index("-o") + 1] = str(wrapped)
            status = helper.run_process(argv, root, stage, 60)
            result["steps"].append({"name": "fresh_module_wrapper_" + name, **status})
            if status.get("exitCode") != 0 or status.get("timedOut") or status.get("cleanupErrors") or status.get("runnerErrorType"):
                raise RuntimeError("actual_module_wrapper_failed:" + name)
            new_objects.append(wrapped)
        remaining = [p for p in cached_objects if p not in expected_old_targets]
        result["newTargetObjectHashes"] = {str(p): helper.sha256(p) for p in new_objects}
        result["cachedDependencyObjectHashes"] = {str(p): helper.sha256(p) for p in remaining}
        objects = remaining + new_objects
        link_list = out / "Objects.LinkFileList"
        link_list.write_text("\n".join(subprocess.list2cmdline([str(p)]) for p in objects) + "\n", encoding="utf-8")
        executable = out / "guarded-hierarchy-probe.exe"
        link[link.index("-o") + 1] = str(executable)
        link[link.index("@" + lists[0])] = "@" + str(link_list)
        stage = out / "link"
        stage.mkdir()
        status = helper.run_process(link, root, stage, 180)
        result["steps"].append({"name": "actual_executable_link", **status})
        if status.get("exitCode") != 0 or status.get("timedOut") or status.get("cleanupErrors") or status.get("runnerErrorType"):
            raise RuntimeError("actual_link_failed")
        if any(helper.sha256(Path(p)) != sha for p, sha in result["cachedDependencyObjectHashes"].items()):
            raise RuntimeError("cached_dependency_object_changed")
        if any(helper.sha256(Path(p)) != sha for p, sha in result["newTargetObjectHashes"].items()):
            raise RuntimeError("new_target_object_changed")
        result["binarySHA256"] = helper.sha256(executable)
        result["binary"] = str(executable)
        result["binaryBytes"] = executable.stat().st_size
        result["status"] = "PASS_EXACT_SOURCE_COMPONENT_BUILD"
    except Exception as error:
        result["errorType"] = type(error).__name__
        if type(error) is RuntimeError:
            result["errorCode"] = str(error)
    finally:
        after = helper.source_snapshot(root, Path(__file__))
        helper.write_json(out / "source-after.json", after)
        result["sourceStable"] = before["files"] == after["files"] and before["dependencies"] == after["dependencies"]
        if not result["sourceStable"]:
            result["status"] = "FAIL"
        helper.write_json(out / "result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "scope", "binary", "binarySHA256", "sourceStable", "errorType", "errorCode") if k in result}))
    return 0 if result["status"] == "PASS_EXACT_SOURCE_COMPONENT_BUILD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
