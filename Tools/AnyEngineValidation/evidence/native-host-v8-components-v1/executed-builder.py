#!/usr/bin/env python3
"""Build the unchanged four-file Host probe with tested Host23 and Integration35.

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
    parser.add_argument("--host-receipt", type=Path, required=True)
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
    result = {"status": "FAIL", "scope": "Complete unchanged four-file Host Probe target, tested Host23 and Integration35 modules, unchanged source-bound plain Engine/Kit/Crypto objects. No watchdog or transport override.", "steps": [], "startedAt": datetime.now(timezone.utc).isoformat()}
    def snapshot():
        value = helper.source_snapshot(root, Path(__file__))
        host_root = root / "Modules/PinkhaAnyHost"
        files = [host_root / "Package.swift", host_root / "Package.resolved"] + list((host_root / "Sources").rglob("*.swift"))
        for path in files:
            if path.is_file():
                value["files"][path.relative_to(root).as_posix()] = {"sha256": helper.sha256(path), "bytes": path.stat().st_size}
        return value
    before = snapshot()
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
        host_path = args.host_receipt.resolve()
        host = json.loads(host_path.read_text(encoding="utf-8"))
        if host.get("status") != "PASS" or host.get("executedTests") != 23 or not all(
            host.get(key) is True for key in ["sourceStable", "cachedDependenciesStable", "dependencySourcesStable", "integrationCompiledFilesStable"]):
            raise RuntimeError("host23_producer_not_verified")
        unrelated_probe_sources = []
        for relative, digest in host["sourceBefore"].items():
            if not relative.startswith("Modules/") or not ("/Sources/" in relative or relative.endswith(("Package.swift", "Package.resolved"))):
                continue
            if "/Sources/PinkhaAnyIntegrationProbe/" in relative or "/Sources/PinkhaAnyEngineProbe/" in relative:
                unrelated_probe_sources.append(relative)
                continue
            if helper.sha256(root / relative) != digest:
                raise RuntimeError("host_producer_source_changed:" + relative)
        if before["dependencies"] != host["dependencySourcesAfter"]:
            raise RuntimeError("host_external_dependency_source_changed")
        if host["integrationCompiledFiles"] != producer["compiledFiles"]:
            raise RuntimeError("host_integration_producer_mismatch")
        result["unlinkedDependencyProbeSourcesExcluded"] = unrelated_probe_sources
        result["integration35Receipt"] = {"path": str(producer_path), "sha256": helper.sha256(producer_path)}
        result["host23Receipt"] = {"path": str(host_path), "sha256": helper.sha256(host_path)}
        shutil.copyfile(producer_path, out / "integration35-producer.json")
        shutil.copyfile(host_path, out / "host23-producer.json")
        for relative, digest in host["cachedDependenciesAfter"].items():
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
        host_files = {name: Path(value["path"]) for name, value in host["compiledHostFiles"].items()}
        for name, path in host_files.items():
            digest = host["compiledHostFiles"][name]["sha256"]
            if helper.sha256(path) != digest:
                raise RuntimeError("fresh_host_object_changed:" + name)
            retained[str(path)] = digest
        result["retainedInputs"] = retained
        modules = out / "Modules"
        modules.mkdir()
        common = list(host["commonHostArguments"])
        # New private modules precede the tested Integration module; old shared
        # modules remain read-only imports after both of them.
        common[1:1] = ["-I", str(modules)]
        index = common.index("-module-cache-path")
        common[index + 1] = str(out / "ModuleCache")
        swift = Path(common[0])
        if helper.sha256(swift) != producer["compilerSHA256"] or helper.sha256(swift) != host["compilerSHA256"]:
            raise RuntimeError("compiler_changed")
        result["compilerSHA256"] = producer["compilerSHA256"]
        dll_dirs = [swift.parent, Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")]
        os.environ["PATH"] = os.pathsep.join(str(path) for path in dll_dirs) + os.pathsep + os.environ.get("PATH", "")
        files = sorted((root / "Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe").glob("*.swift"))
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

        module = modules / "PinkhaAnyHostProbe.swiftmodule"
        obj = out / "PinkhaAnyHostProbe.o"
        wrap = out / "PinkhaAnyHostProbe.swiftmodule.o"
        run("probe-compile", common + ["-module-name", "PinkhaAnyHostProbe", "-whole-module-optimization",
            "-emit-module", "-emit-module-path", str(module), "-emit-object", "-o", str(obj)] + [str(path) for path in files], 180)
        run("probe-modulewrap", [str(swift), "-modulewrap", str(module), "-target",
            "x86_64-unknown-windows-msvc", "-o", str(wrap)], 45)
        cached_objects = [Path(path) for path in retained if Path(path).suffix == ".o"
                          and Path(path) not in integration_files.values() and Path(path) not in host_files.values()]
        if len(cached_objects) != host["cachedObjectCount"]:
            raise RuntimeError("cached_object_closure_mismatch")
        objects = cached_objects + [integration_files["object"], integration_files["modulewrap"], host_files["object"], host_files["modulewrap"], obj, wrap]
        response = out / "Objects.LinkFileList"
        response.write_text("\n".join(subprocess.list2cmdline([str(path)]) for path in objects) + "\n", encoding="utf-8")
        executable = out / "native-host-v8-probe.exe"
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
        after = snapshot()
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
