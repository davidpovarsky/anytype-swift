#!/usr/bin/env python3
"""Compile current Host and all 16 block-creator actor seam cases against pinned dependencies."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--integration-producer", type=Path, required=True)
    p.add_argument("--reuse-host-receipt", type=Path, required=True)
    args = p.parse_args()
    root, out, evidence = args.repo_root.resolve(), args.output_dir.resolve(), args.evidence_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("owned_process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sha = helper.sha256
    rel = lambda path: path.resolve().relative_to(root).as_posix()
    tests = [root / ("Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/" + name)
             for name in ["AnyNativeBlockCreatorTests.swift"]]
    host_sources = sorted((root / "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost").glob("*.swift"))
    probe_sources = sorted((root / "Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe").glob("*.swift"))
    integration_sources = sorted((root / "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration").glob("*.swift"))
    source_paths = set(tests + host_sources + probe_sources + integration_sources + [Path(__file__).resolve(), helper_path])
    for package in ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"]:
        package_root = root / "Modules" / package
        source_paths.update(path for path in (package_root / "Sources").rglob("*")
                            if path.is_file() and helper.is_source_artifact(path))
        for name in ["Package.swift", "Package.resolved"]:
            if (package_root / name).exists():
                source_paths.add(package_root / name)
    snapshot = lambda: {rel(path): sha(path) for path in sorted(source_paths)}
    before = snapshot()
    result = {
        "schemaVersion": 1, "status": "RUNNING",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual complete Host library, 16 exact block-creator Swift Testing cases, and production HostProbe semantic check. Fresh source-bound v8 Integration module; cached verified Engine/Kit/Crypto. No native HTTP, Apple runtime, or mounted UI execution.",
        "sourceBefore": before, "expectedCount": 16, "executedTests": 0, "steps": [],
        "hostSourceFiles": [rel(path) for path in host_sources],
        "probeSourceFiles": [rel(path) for path in probe_sources]
    }
    shutil.copyfile(__file__, evidence / "executed-runner.py")
    shutil.copyfile(helper_path, evidence / "executed-process-helper.py")
    helper.write_json(evidence / "result.json", result)
    cached_before = {}
    dependencies_before = None
    integration_before = {}
    def persist():
        helper.write_json(evidence / "result.json", result)
    def run(name, command, timeout):
        stage = evidence / name
        stage.mkdir()
        process = helper.run_process(command, root, stage, timeout)
        result["steps"].append({"name": name, **process})
        persist()
        if process.get("exitCode") != 0 or process.get("timedOut") or process.get("cleanupErrors") or process.get("runnerErrorType"):
            raise RuntimeError("actual_process_failed:" + name)
        return stage
    try:
        producer_path = args.integration_producer.resolve()
        producer = json.loads(producer_path.read_text(encoding="utf-8"))
        if producer["status"] != "PASS_COMPILE_ONLY" or producer.get("sourceStableAtCompile") is not True:
            raise RuntimeError("integration_producer_not_source_stable")
        expected_integration = {rel(path): before[rel(path)] for path in integration_sources}
        if producer["sourceManifest"] != expected_integration:
            raise RuntimeError("integration_producer_source_mismatch")
        main_producer_path = producer_path.parent / "result.json"
        main_producer = json.loads(main_producer_path.read_text(encoding="utf-8"))
        if main_producer.get("status") != "PASS" or main_producer.get("sourceStable") is not True:
            raise RuntimeError("integration_component_producer_incomplete")
        integration = {name: Path(value["path"]) for name, value in producer["compiledFiles"].items()}
        for name, value in producer["compiledFiles"].items():
            if sha(integration[name]) != value["sha256"]:
                raise RuntimeError("compiled_integration_changed:" + name)
            integration_before[rel(integration[name])] = value["sha256"]
        result["integrationProducer"] = {"path": rel(producer_path), "sha256": sha(producer_path),
                                        "testReceipt": rel(main_producer_path), "testReceiptSHA256": sha(main_producer_path)}
        result["integrationCompiledFiles"] = producer["compiledFiles"]
        shutil.copyfile(producer_path, evidence / "integration-producer.json")
        source_receipt_path = root / "docs/any-engine-port/evidence/20261119/native-torah-workflow-20261119-201618-378627.json"
        source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        if source_receipt.get("buildExitCode") != 0 or source_receipt.get("sourceStable") is not True:
            raise RuntimeError("cached_host_dependency_build_not_verified")
        prior = source_receipt["sourceManifest"]
        for path, digest in before.items():
            if path.startswith(("Modules/PinkhaAnyEngine/", "Modules/PinkhaKit/")):
                old = prior.get(path)
                if isinstance(old, dict):
                    old = old.get("sha256")
                if old != digest:
                    raise RuntimeError("cached_dependency_source_changed:" + path)
        result["cachedDependencyBuildReceipt"] = {"path": rel(source_receipt_path), "sha256": sha(source_receipt_path),
            "scope": "Build succeeded; its unrelated native timeout remains a failure."}
        dependencies_before = helper.source_snapshot(root, Path(__file__))["dependencies"]
        if dependencies_before != producer["cachedDependencySources"]:
            raise RuntimeError("external_dependency_source_mismatch")
        result["dependencySourcesBefore"] = dependencies_before
        debug = root / "Modules/PinkhaAnyHost/.build/x86_64-unknown-windows-msvc/debug"
        description_path = debug / "description.json"
        description = json.loads(description_path.read_text(encoding="utf-8"))
        commands = description["swiftCommands"]
        command_for = lambda name: commands["C." + name + "-x86_64-unknown-windows-msvc-debug.module"]
        swift = Path(command_for("PinkhaAnyHost")["executable"])
        result["compilerSHA256"] = sha(swift)
        if result["compilerSHA256"] != producer["compilerSHA256"]:
            raise RuntimeError("integration_compiler_mismatch")
        result["swiftPMDescriptionSHA256"] = sha(description_path)
        yaml_path = debug.parent.parent / "debug.yaml"
        result["swiftPMBuildYAMLSHA256"] = sha(yaml_path)
        modules = out / "Modules"; modules.mkdir()
        module_cache = out / "ModuleCache"; module_cache.mkdir()
        def common(name, executable=False):
            original = command_for(name)["otherArguments"]
            filtered = []
            index = 0
            while index < len(original):
                arg = original[index]
                if arg in ["-index-store-path", "-emit-objc-header-path", "-module-cache-path"]:
                    index += 2; continue
                if arg in ["-incremental", "-serialize-diagnostics", "-parseable-output", "-enable-batch-mode",
                           "-emit-objc-header", "-static", "-g"] or re.fullmatch(r"-j[0-9]+", arg):
                    index += 1; continue
                if executable and arg == "-parse-as-library":
                    index += 1; continue
                if arg == "-Xcc" and index + 1 < len(original) and original[index + 1] == "-gdwarf":
                    index += 2; continue
                filtered.append(arg); index += 1
            return [str(swift), "-I", str(modules), "-I", str(integration["module"].parent),
                    "-I", str(debug / "Modules"), "-module-cache-path", str(module_cache), "-j1"] + filtered
        result["commonHostArguments"] = common("PinkhaAnyHost")
        link_file = debug / "pinkha-any-host-probe.product/Objects.LinkFileList"
        old_objects = [Path(line.strip().strip('"')) for line in link_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        replaced = {"PinkhaAnyHost.build", "PinkhaAnyHostProbe.build", "PinkhaAnyIntegration.build"}
        excluded = [path for path in old_objects if path.parent.name in replaced]
        cached = [path for path in old_objects if path.parent.name not in replaced]
        if {path.parent.name for path in excluded} != replaced:
            raise RuntimeError("old_link_target_closure_missing")
        if len(set(cached)) != len(cached) or not all(path.is_file() for path in cached):
            raise RuntimeError("cached_dependency_object_missing_or_duplicate")
        cached_modules = [path for path in (debug / "Modules").glob("*.swiftmodule")
                          if path.stem not in {"PinkhaAnyHost", "PinkhaAnyHostProbe", "PinkhaAnyIntegration",
                                               "PinkhaAnyIntegrationProbe", "PinkhaAnyHostTests"} and "Tests" not in path.stem]
        cached_before = {rel(path): sha(path) for path in cached + cached_modules}
        result["cachedDependenciesBefore"] = cached_before
        result["excludedOldTargetObjects"] = [rel(path) for path in excluded]
        result["cachedObjectCount"] = len(cached)
        response = out / "cached-objects.rsp"
        response.write_text("\n".join(subprocess.list2cmdline([str(path)]) for path in cached) + "\n", encoding="utf-8")
        swift_root = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift")
        runtime_paths = [
            swift_root / "Toolchains/6.3.3+Asserts/usr/bin",
            swift_root / "Runtimes/6.3.3/usr/bin",
            swift_root / "Platforms/6.3.3/Windows.platform/Developer/Library/XCTest-6.3.3/usr/bin64",
            swift_root / "Platforms/6.3.3/Windows.platform/Developer/Library/Testing-6.3.3/usr/bin64"
        ]
        if not (runtime_paths[2] / "XCTest.dll").is_file() or not (runtime_paths[3] / "Testing.dll").is_file():
            raise RuntimeError("test_runtime_dll_missing")
        os.environ["PATH"] = os.pathsep.join(str(path) for path in runtime_paths) + os.pathsep + os.environ.get("PATH", "")
        result["runtimeDLLs"] = {str(path): sha(path) for folder in runtime_paths for path in folder.glob("*.dll")}
        expected = re.findall(r"@Test func (\w+)\(", tests[0].read_text(encoding="utf-8"))
        if len(expected) != 16 or len(set(expected)) != 16:
            raise RuntimeError("exact_block_test_inventory_changed")
        driver = out / "Main.swift"
        driver.write_text("import Testing\n@main struct BlockCreatorComponents {\n static func main() async { await Testing.__swiftPMEntryPoint() as Never }\n}\n", encoding="utf-8")
        shutil.copyfile(driver, evidence / "Main.swift")
        result["expectedTests"] = expected
        result["driverSHA256"] = sha(driver)
        persist()
        module = modules / "PinkhaAnyHost.swiftmodule"
        obj = out / "PinkhaAnyHost.o"
        wrap = out / "PinkhaAnyHost.swiftmodule.o"
        prior_path = args.reuse_host_receipt.resolve()
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        if prior.get("sourceStable") is not True or prior.get("cachedDependenciesStable") is not True or prior.get("dependencySourcesStable") is not True:
            raise RuntimeError("host_producer_not_stable")
        stages = {step["name"]: step for step in prior["steps"]}
        for stage in ["host-compile", "host-modulewrap", "production-probe-typecheck"]:
            if stages[stage]["exitCode"] != 0 or stages[stage]["timedOut"] or stages[stage]["cleanupErrors"] or not stages[stage]["parentExited"]:
                raise RuntimeError("host_producer_stage_not_successful:" + stage)
        for path, digest in before.items():
            if path.startswith("Modules/") and "/Tests/" not in path and prior["sourceBefore"].get(path) != digest:
                raise RuntimeError("host_producer_source_mismatch:" + path)
        if prior["compilerSHA256"] != result["compilerSHA256"] or prior["cachedDependenciesBefore"] != cached_before or prior["dependencySourcesBefore"] != dependencies_before or prior["integrationCompiledFiles"] != result["integrationCompiledFiles"]:
            raise RuntimeError("host_producer_dependency_mismatch")
        for name, destination in [("module", module), ("object", obj), ("modulewrap", wrap)]:
            old = prior["compiledHostFiles"][name]
            if sha(Path(old["path"])) != old["sha256"]:
                raise RuntimeError("host_producer_output_changed:" + name)
            shutil.copyfile(Path(old["path"]), destination)
        result["reusedHostProduction"] = {"receipt": rel(prior_path), "receiptSHA256": sha(prior_path),
            "scope": "Reused only successful full Host compilation/modulewrap and production HostProbe typecheck; prior test macro compile failed and executed zero tests.",
            "successfulStages": ["host-compile", "host-modulewrap", "production-probe-typecheck"]}
        result["compiledHostFiles"] = {name: {"path": str(path), "sha256": sha(path)}
                                      for name, path in [("module", module), ("object", obj), ("modulewrap", wrap)]}
        shutil.copyfile(prior_path, evidence / "reused-host-producer.json")
        persist()
        executable = out / "native-empty-block-components.exe"
        run("component-compile-link", common("PinkhaAnyHostTests") +
            ["-module-name", "NativeEmptyBlockComponents", "-emit-executable", str(driver)] +
            [str(path) for path in tests] + [str(obj), str(wrap), str(integration["object"]), str(integration["modulewrap"]),
            "@" + str(response), "-Xlinker", "/debug:none", "-Xlinker", "/threads:1",
            "-Xlinker", "/opt:noref", "-Xlinker", "/opt:noicf", "-o", str(executable)], 180)
        result["binarySHA256"] = sha(executable)
        result["binary"] = str(executable)
        stage = run("component-execution", [str(executable)], 90)
        output = (stage / "stdout.json").read_text(encoding="utf-8", errors="replace")
        output += (stage / "stderr.log").read_text(encoding="utf-8", errors="replace")
        passed = re.findall(r"Test (\w+)\(\) passed", output)
        result["passedTests"] = passed
        result["executedTests"] = len(passed)
        if len(passed) != len(expected) or set(passed) != set(expected):
            raise RuntimeError("exact_test_identity_or_count_mismatch")
        if not re.search(r"Test run with 16 tests(?: in \d+ suites?)? passed", output):
            raise RuntimeError("zero_failure_summary_missing")
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["errorType"] = type(error).__name__
        result["error"] = str(error)
    finally:
        after = snapshot()
        result["sourceAfter"] = after
        result["sourceStable"] = after == before
        result["cachedDependenciesAfter"] = {path: sha(root / path) for path in cached_before}
        result["cachedDependenciesStable"] = result["cachedDependenciesAfter"] == cached_before
        result["integrationCompiledFilesStable"] = all(sha(root / path) == value for path, value in integration_before.items())
        if dependencies_before is not None:
            result["dependencySourcesAfter"] = helper.source_snapshot(root, Path(__file__))["dependencies"]
            result["dependencySourcesStable"] = result["dependencySourcesAfter"] == dependencies_before
        if not result["sourceStable"] or not result["cachedDependenciesStable"] or not result["integrationCompiledFilesStable"] or result.get("dependencySourcesStable") is False:
            result["status"] = "FAIL"
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        result["freeBytesAfter"] = shutil.disk_usage(root).free
        result["logHashes"] = {rel(path): sha(path) for path in evidence.rglob("*") if path.is_file() and path.name != "result.json"}
        persist()
    print(json.dumps({key: result.get(key) for key in ["status", "error", "executedTests", "sourceStable", "cachedDependenciesStable", "integrationCompiledFilesStable"]}))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
