#!/usr/bin/env python3
"""Execute the exact hierarchy/fence tests with complete current Integration source.

No SwiftPM planning, dependency rebuild, cache mutation, transport override, or
replacement implementation is used. Every compiler/test subprocess is bounded
by the existing owned-process helper.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    out = args.output_dir.resolve()
    evidence = args.evidence_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("owned_process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    shutil.copyfile(__file__, evidence / "executed-runner.py")
    shutil.copyfile(helper_path, evidence / "executed-process-helper.py")
    debug = root / "Modules/PinkhaAnyIntegration/.build/x86_64-unknown-windows-msvc/debug"
    swift = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
    sdk = Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk")
    libraries = sdk.parents[1] / "Library"
    result = {
        "status": "RUNNING",
        "scope": "Complete current Integration module and 35 exact hierarchy/property-fence component tests; cached source-bound Engine/Kit/Crypto dependencies. Not native HTTP, native CRDT authority, Apple, or UI acceptance.",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "steps": [], "executedTests": 0,
    }
    modules = out / "Modules"
    modules.mkdir()
    source_files = sorted((root / "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration").glob("*.swift"))
    tests = [root / "Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests" / name
             for name in ["AnyHierarchyTests.swift", "AnyConditionalPropertyFenceTests.swift"]]
    expected = [name for path in tests for name in re.findall(r"@Test\s+func\s+(\w+)", path.read_text(encoding="utf-8"))]
    if len(expected) != 35 or len(set(expected)) != 35:
        raise RuntimeError("unexpected_exact_test_count")
    result["expectedTests"] = expected
    result["expectedCount"] = 35
    tracked = source_files + tests + [Path(__file__), helper_path]
    for package in ["PinkhaAnyEngine", "PinkhaKit"]:
        tracked += [p for p in (root / "Modules" / package / "Sources").rglob("*")
                    if p.is_file() and helper.is_source_artifact(p)]
    for package in ["PinkhaAnyIntegration", "PinkhaAnyEngine", "PinkhaKit"]:
        for name in ["Package.swift", "Package.resolved"]:
            path = root / "Modules" / package / name
            if path.is_file():
                tracked.append(path)

    def rel(path):
        return path.relative_to(root).as_posix()

    def hashes(paths):
        return {rel(path): helper.sha256(path) for path in sorted(set(paths))}

    before = hashes(tracked)
    result["sourceBefore"] = before
    result["integrationSourceFiles"] = [rel(path) for path in source_files]
    result["runnerSHA256"] = helper.sha256(Path(__file__))
    result["processHelperSHA256"] = helper.sha256(helper_path)
    result["compilerSHA256"] = helper.sha256(swift)
    helper.write_json(evidence / "result.json", result)
    cached = []
    cached_before = {}
    dependencies_before = None
    try:
        if shutil.disk_usage(root).free < 2 * 1024 ** 3:
            raise RuntimeError("fewer_than_2GiB_free")
        prior_path = root / "Tools/AnyEngineValidation/evidence/live-public-provider-windows-v2/source-before.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        current = helper.source_snapshot(root, Path(__file__))
        for path, digest in before.items():
            if path.startswith(("Modules/PinkhaAnyEngine/", "Modules/PinkhaKit/")):
                if prior["files"].get(path, {}).get("sha256") != digest:
                    raise RuntimeError("cached_dependency_source_changed:" + path)
        if prior["dependencies"] != current["dependencies"]:
            raise RuntimeError("cached_external_dependency_source_changed")
        dependencies_before = current["dependencies"]
        result["dependencySourcesBefore"] = dependencies_before
        result["cachedDependencySourceReceipt"] = {"path": rel(prior_path), "sha256": helper.sha256(prior_path)}
        link_list = debug / "pinkha-any-integration-probe.product/Objects.LinkFileList"
        originals = [Path(line.strip().strip(chr(34))).resolve()
                     for line in link_list.read_text(encoding="utf-8").splitlines() if line.strip()]
        excluded = [path for path in originals if
                    "PinkhaAnyIntegration.build" in path.parts or "PinkhaAnyIntegrationProbe.build" in path.parts]
        cached = [path for path in originals if path not in excluded]
        if not cached or not excluded or not all(path.is_file() for path in cached):
            raise RuntimeError("cached_dependency_objects_incomplete")
        cached_modules = [path for path in (debug / "Modules").glob("*.swiftmodule")
                          if path.stem not in {"PinkhaAnyIntegration", "PinkhaAnyIntegrationProbe"}]
        cached_before = hashes(cached + cached_modules)
        result["cachedDependenciesBefore"] = cached_before
        result["excludedOldTargetObjects"] = [rel(path) for path in excluded]
        result["cachedObjectCount"] = len(cached)
        response = out / "cached-objects.rsp"
        response.write_text("\n".join(subprocess.list2cmdline([str(path)]) for path in cached) + "\n", encoding="utf-8")
        driver = out / "Run.swift"
        driver.write_text(
            "import Testing\n@main struct ConditionalPropertyComponents {\n"
            " static func main() async { await Testing.__swiftPMEntryPoint() as Never }\n}\n",
            encoding="utf-8")
        shutil.copyfile(driver, evidence / "Run.swift")
        result["driverSHA256"] = helper.sha256(driver)
        common = [str(swift), "-swift-version", "6", "-parse-as-library", "-enable-testing",
                  "-target", "x86_64-unknown-windows-msvc", "-Onone", "-j1",
                  "-I", str(modules), "-I", str(debug / "Modules"),
                  "-module-cache-path", str(out / "ModuleCache"),
                  "-sdk", str(sdk), "-libc", "MD", "-use-ld=lld",
                  "-DSWIFT_PACKAGE", "-DDEBUG", "-DSWIFT_MODULE_RESOURCE_BUNDLE_UNAVAILABLE",
                  "-package-name", "pinkhaanyintegration"]
        for name in ["CCryptoBoringSSLShims", "CCryptoBoringSSL"]:
            include = root / "Modules/PinkhaAnyIntegration/.build/checkouts/swift-crypto/Sources" / name / "include"
            common += ["-Xcc", "-fmodule-map-file=" + str(include / "module.modulemap"), "-Xcc", "-I" + str(include)]
        dll_dirs = [swift.parent, Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin")]
        for family in ["Testing", "XCTest"]:
            lib = libraries / (family + "-6.3.3") / "usr/lib/swift/windows"
            common += ["-I", str(lib), "-I", str(lib / "x86_64"), "-L", str(lib / "x86_64")]
            dll = libraries / (family + "-6.3.3") / "usr/bin64"
            if not (dll / (family + ".dll")).is_file():
                raise RuntimeError("test_runtime_dll_missing:" + family)
            dll_dirs.append(dll)
        os.environ["PATH"] = os.pathsep.join(str(path) for path in dll_dirs) + os.pathsep + os.environ.get("PATH", "")
        result["runtimeDLLs"] = {
            str(path): helper.sha256(path) for directory in dll_dirs
            for path in directory.glob("*.dll") if path.name in {"Testing.dll", "XCTest.dll", "swiftCore.dll", "FoundationNetworking.dll"}}
        result["commonArguments"] = common

        def run(name, command, seconds):
            stage = evidence / name
            stage.mkdir()
            process = helper.run_process(command, out, stage, seconds)
            result["steps"].append({"name": name, **process})
            helper.write_json(evidence / "result.json", result)
            if process.get("exitCode") != 0 or process.get("timedOut") or process.get("cleanupErrors") or process.get("runnerErrorType"):
                raise RuntimeError("step_failed:" + name)

        module = modules / "PinkhaAnyIntegration.swiftmodule"
        obj = out / "PinkhaAnyIntegration.o"
        wrap = out / "PinkhaAnyIntegration.swiftmodule.o"
        run("integration-compile", common + ["-module-name", "PinkhaAnyIntegration",
            "-whole-module-optimization", "-emit-module", "-emit-module-path", str(module),
            "-emit-object", "-o", str(obj)] + [str(path) for path in source_files], 180)
        run("integration-modulewrap", [str(swift), "-modulewrap", str(module),
            "-target", "x86_64-unknown-windows-msvc", "-o", str(wrap)], 45)
        result["compiledFiles"] = {
            name: {"path": str(path), "sha256": helper.sha256(path)}
            for name, path in [("module", module), ("object", obj), ("modulewrap", wrap)]}
        result["compiledIntegrationSources"] = {rel(path): before[rel(path)] for path in source_files}
        helper.write_json(evidence / "integration-producer.json", {
            "status": "PASS_COMPILE_ONLY", "compiledFiles": result["compiledFiles"],
            "sourceManifest": result["compiledIntegrationSources"],
            "cachedDependencySources": dependencies_before,
            "cachedDependencySourceReceipt": result["cachedDependencySourceReceipt"],
            "compilerSHA256": result["compilerSHA256"],
            "producerSteps": list(result["steps"]),
            "sourceStableAtCompile": all(helper.sha256(root / path) == digest for path, digest in before.items()),
        })
        executable = out / "conditional-property-components.exe"
        run("component-compile-link", common + ["-module-name", "ConditionalPropertyComponents",
            str(driver)] + [str(path) for path in tests] + [str(obj), str(wrap), "@" + str(response),
            "-Xlinker", "/debug:none", "-Xlinker", "/threads:1",
            "-Xlinker", "/opt:noref", "-Xlinker", "/opt:noicf", "-o", str(executable)], 240)
        result["binarySHA256"] = helper.sha256(executable)
        run("component-tests", [str(executable)], 60)
        text = ((evidence / "component-tests/stdout.json").read_text(encoding="utf-8", errors="replace")
                + (evidence / "component-tests/stderr.log").read_text(encoding="utf-8", errors="replace"))
        passed = re.findall(r"Test (\w+)\(\) passed", text)
        result["passedTests"] = passed
        result["executedTests"] = len(passed)
        summaries = re.findall(r"Test run with (\d+) tests?(?: in \d+ suites?)? passed", text)
        if set(passed) != set(expected) or len(passed) != 35 or not summaries or int(summaries[-1]) != 35:
            raise RuntimeError("exact_35_test_execution_not_proven")
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["errorType"] = type(error).__name__
        result["error"] = str(error)
    finally:
        after = hashes(tracked)
        result["sourceAfter"] = after
        result["sourceStable"] = before == after
        if cached_before:
            result["cachedDependenciesAfter"] = {path: helper.sha256(root / path) for path in cached_before}
            result["cachedDependenciesStable"] = result["cachedDependenciesAfter"] == cached_before
        else:
            result["cachedDependenciesStable"] = None
        if dependencies_before is not None:
            result["dependencySourcesAfter"] = helper.source_snapshot(root, Path(__file__))["dependencies"]
            result["dependencySourcesStable"] = result["dependencySourcesAfter"] == dependencies_before
        if not result["sourceStable"] or result.get("cachedDependenciesStable") is False or result.get("dependencySourcesStable") is False:
            result["status"] = "FAIL"
        result["finishedAt"] = datetime.now(timezone.utc).isoformat()
        result["freeBytesAfter"] = shutil.disk_usage(root).free
        result["logHashes"] = {rel(path): helper.sha256(path) for path in evidence.rglob("*")
                               if path.is_file() and path.name in {"stdout.json", "stderr.log"}}
        helper.write_json(evidence / "result.json", result)
    print(json.dumps({key: result.get(key) for key in ["status", "error", "executedTests",
        "sourceStable", "cachedDependenciesStable", "dependencySourcesStable", "freeBytesAfter"]}), flush=True)
    for step in result["steps"][-1:]:
        folder = evidence / step["name"]
        for name in ["stdout.json", "stderr.log"]:
            text = (folder / name).read_text(encoding="utf-8", errors="replace")
            if text:
                print(text[-16000:])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
