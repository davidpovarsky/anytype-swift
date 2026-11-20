#!/usr/bin/env python3
"""Build the complete v8 hierarchy probe with the tested Integration module.

The unchanged Engine/Kit/Crypto object closure and current Probe sources are
source-bound. This performs no SwiftPM planning or shared-cache replacement.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--integration-receipt", type=Path, required=True)
    parser.add_argument("--assertion-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.repo_root.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("owned_process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    shutil.copyfile(__file__, out / "executed-builder.py")
    shutil.copyfile(helper_path, out / "executed-process-helper.py")
    result = {"status": "FAIL", "scope": "Complete current four-file hierarchy Probe target, tested current Integration20 module, unchanged source-bound plain Engine/Kit/Crypto objects. No watchdog or transport override.", "steps": [], "startedAt": datetime.now(timezone.utc).isoformat()}
    before = helper.source_snapshot(root, Path(__file__))
    helper.write_json(out / "source-before.json", before)
    result["sourceInputs"] = {p: value["sha256"] for p, value in before["files"].items()}
    result["sourceInputs"][helper_path.relative_to(root).as_posix()] = helper.sha256(helper_path)
    retained = {}
    try:
        if shutil.disk_usage(root).free < 2 * 1024 ** 3:
            raise RuntimeError("fewer_than_2GiB_free")
        producer_path = args.integration_receipt.resolve()
        producer = json.loads(producer_path.read_text(encoding="utf-8"))
        if producer.get("status") != "PASS" or producer.get("executedTests") != 35 or not all(
            producer.get(key) is True for key in ["sourceStable", "cachedDependenciesStable", "dependencySourcesStable"]):
            raise RuntimeError("integration35_producer_not_verified")
        for relative, digest in producer["sourceBefore"].items():
            if helper.sha256(root / relative) != digest:
                raise RuntimeError("integration_producer_source_changed:" + relative)
        if before["dependencies"] != producer["dependencySourcesAfter"]:
            raise RuntimeError("external_dependency_source_changed")
        review_path = args.assertion_review.resolve()
        review = json.loads(review_path.read_text(encoding="utf-8"))
        probe_relative = "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/GuardedHierarchyProbe.swift"
        if review.get("status") != "PASS_SOURCE_REVIEW_ONLY" or review.get("assertionCount") != 20 or review.get("allOriginalAssertionExpressionsUnchanged") is not True or helper.sha256(root / probe_relative) != review["currentSHA256"]:
            raise RuntimeError("original_twenty_assertions_not_pinned")
        result["originalTwentyAssertionReview"] = {"path": str(review_path), "sha256": helper.sha256(review_path)}
        result["integration35Receipt"] = {"path": str(producer_path), "sha256": helper.sha256(producer_path)}
        shutil.copyfile(producer_path, out / "integration35-producer.json")
        shutil.copyfile(review_path, out / "original-twenty-assertions.json")
        for relative, digest in producer["cachedDependenciesAfter"].items():
            path = root / relative
            if helper.sha256(path) != digest:
                raise RuntimeError("cached_dependency_changed:" + relative)
            retained[str(path)] = digest
        integration_files = {name: Path(value["path"]) for name, value in producer["compiledFiles"].items()}
        for name, path in integration_files.items():
            digest = producer["compiledFiles"][name]["sha256"]
            if helper.sha256(path) != digest:
                raise RuntimeError("fresh_integration_object_changed:" + name)
            retained[str(path)] = digest
        result["retainedInputs"] = retained
        modules = out / "Modules"
        modules.mkdir()
        common = list(producer["commonArguments"])
        # New private modules precede the tested Integration module; old shared
        # modules remain read-only imports after both of them.
        common[1:1] = ["-I", str(modules)]
        index = common.index("-module-cache-path")
        common[index + 1] = str(out / "ModuleCache")
        swift = Path(common[0])
        if helper.sha256(swift) != producer["compilerSHA256"]:
            raise RuntimeError("compiler_changed")
        result["compilerSHA256"] = producer["compilerSHA256"]
        dll_dirs = [swift.parent, Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")]
        os.environ["PATH"] = os.pathsep.join(str(path) for path in dll_dirs) + os.pathsep + os.environ.get("PATH", "")
        files = sorted((root / "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe").glob("*.swift"))
        if len(files) != 4:
            raise RuntimeError("unexpected_complete_probe_source_graph")
        result["probeSourceFiles"] = [path.relative_to(root).as_posix() for path in files]
        result["compiledSourceCount"] = len(files)
        (out / "compiled-sources").mkdir()
        for path in files:
            shutil.copyfile(path, out / "compiled-sources" / path.name)

        def run(name, command, timeout):
            stage = out / name
            stage.mkdir()
            process = helper.run_process(command, root, stage, timeout)
            result["steps"].append({"name": name, **process})
            helper.write_json(out / "result.json", result)
            if process.get("exitCode") != 0 or process.get("timedOut") or process.get("cleanupErrors") or process.get("runnerErrorType"):
                raise RuntimeError("actual_component_step_failed:" + name)

        module = modules / "PinkhaAnyIntegrationProbe.swiftmodule"
        obj = out / "PinkhaAnyIntegrationProbe.o"
        wrap = out / "PinkhaAnyIntegrationProbe.swiftmodule.o"
        run("probe-compile", common + ["-module-name", "PinkhaAnyIntegrationProbe", "-whole-module-optimization",
            "-emit-module", "-emit-module-path", str(module), "-emit-object", "-o", str(obj)] + [str(path) for path in files], 180)
        run("probe-modulewrap", [str(swift), "-modulewrap", str(module), "-target",
            "x86_64-unknown-windows-msvc", "-o", str(wrap)], 45)
        cached_objects = [Path(path) for path in retained if Path(path).suffix == ".o"
                          and Path(path) not in integration_files.values()]
        if len(cached_objects) != producer["cachedObjectCount"]:
            raise RuntimeError("cached_object_closure_mismatch")
        objects = cached_objects + [integration_files["object"], integration_files["modulewrap"], obj, wrap]
        response = out / "Objects.LinkFileList"
        response.write_text("\n".join(subprocess.list2cmdline([str(path)]) for path in objects) + "\n", encoding="utf-8")
        executable = out / "guarded-hierarchy-v8-probe.exe"
        run("probe-link", common + ["-emit-executable", "@" + str(response),
            "-Xlinker", "/debug:none", "-Xlinker", "/threads:1",
            "-Xlinker", "/opt:noref", "-Xlinker", "/opt:noicf", "-o", str(executable)], 240)
        result["objectCount"] = len(objects)
        result["objectHashes"] = {str(path): helper.sha256(path) for path in objects}
        result["newTargetFiles"] = {str(path): helper.sha256(path) for path in [module, obj, wrap]}
        result["binary"] = str(executable)
        result["binarySHA256"] = helper.sha256(executable)
        result["status"] = "PASS_EXACT_SOURCE_COMPONENT_BUILD"
    except Exception as error:
        result["errorType"] = type(error).__name__
        result["errorCode"] = str(error)
    finally:
        after = helper.source_snapshot(root, Path(__file__))
        helper.write_json(out / "source-after.json", after)
        result["sourceStable"] = before["files"] == after["files"] and before["dependencies"] == after["dependencies"]
        result["retainedInputsStable"] = all(helper.sha256(Path(path)) == digest for path, digest in retained.items())
        if not result["sourceStable"] or not result["retainedInputsStable"]:
            result["status"] = "FAIL"
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        helper.write_json(out / "result.json", result)
    print(json.dumps({key: result.get(key) for key in ["status", "errorCode", "sourceStable", "retainedInputsStable", "objectCount", "binarySHA256"]}), flush=True)
    return 0 if result["status"] == "PASS_EXACT_SOURCE_COMPONENT_BUILD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
