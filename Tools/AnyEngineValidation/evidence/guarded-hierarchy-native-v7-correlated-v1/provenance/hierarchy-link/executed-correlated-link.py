#!/usr/bin/env python3
"""Relink the retained hierarchy probe with the reviewed diagnostic Engine only."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess

DEPENDENCY_PINS = {
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input-build-dir", type=Path, required=True)
    parser.add_argument("--trace-manifest", type=Path, required=True)
    parser.add_argument("--trace-manifest-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, original, out = args.repo_root.resolve(), args.input_build_dir.resolve(), args.output_dir.resolve()
    if len(args.trace_manifest_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.trace_manifest_sha256):
        parser.error("trace manifest SHA256 must be an exact lowercase pin")
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = {
        "status": "FAIL", "diagnosticsOnly": True, "productionHTTPSettingsChanged": False,
        "transportReliabilityEstablished": False,
        "scope": "Unchanged production hierarchy and 20 assertions; the complete Engine is replaced only by its source-matched diagnostic HTTP logging build. No connection, timeout, request, response or assertion setting changes. This is behavior evidence with tracing, not a resolution of the original untraced timeout.",
    }
    before = helper.source_snapshot(root, Path(__file__))
    helper.write_json(out / "source-before.json", before)
    shutil.copyfile(__file__, out / "executed-correlated-link.py")
    shutil.copyfile(helper_path, out / "executed-process-helper.py")
    expected = {}
    try:
        producer = original / "result.json"
        proof = json.loads(producer.read_text(encoding="utf-8"))
        if proof.get("status") != "PASS_EXACT_SOURCE_COMPONENT_BUILD" or proof.get("sourceStable") is not True:
            raise RuntimeError("successful_original_link_proof_required")
        result["sourceInputs"] = proof["sourceInputs"]
        for path, sha in proof["sourceInputs"].items():
            if helper.sha256(root / path) != sha:
                raise RuntimeError("compiled_source_changed:" + path)
        result["producerReceiptSHA256"] = helper.sha256(producer)
        trace_path = args.trace_manifest.resolve()
        if helper.sha256(trace_path) != args.trace_manifest_sha256:
            raise RuntimeError("reviewed_trace_manifest_mismatch")
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace.get("diagnosticsOnly") is not True or trace.get("originalProductionBehaviorChanges") is not False or trace.get("changedEngineFiles") != ["AnyHTTPClient.swift"]:
            raise RuntimeError("diagnostic_only_trace_required")
        prefix = "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/"
        original_engine = {Path(path).name: sha for path, sha in proof["sourceInputs"].items() if path.startswith(prefix) and path.endswith(".swift")}
        if original_engine != trace["originalEngineSourceManifest"]:
            raise RuntimeError("traced_engine_original_sources_differ")
        changes = [name for name, sha in trace["copiedEngineSourceManifest"].items() if original_engine.get(name) != sha]
        if changes != ["AnyHTTPClient.swift"]:
            raise RuntimeError("unreviewed_trace_source_changes")
        dependency_proofs = {}
        for package in ("PinkhaAnyHost", "PinkhaAnyIntegration"):
            for name, pin in DEPENDENCY_PINS.items():
                checkout = root / "Modules" / package / ".build/checkouts" / name
                base = ["git", "--no-optional-locks", "-C", str(checkout)]
                head = subprocess.check_output(base + ["rev-parse", "HEAD"], timeout=20, encoding="utf-8").strip()
                status = subprocess.check_output(base + ["status", "--porcelain", "--untracked-files=normal"], timeout=20, encoding="utf-8")
                if head != pin or status.strip():
                    raise RuntimeError("trace_dependency_source_not_same_clean_pin")
                dependency_proofs[package + "/" + name] = {"gitHEAD": head, "clean": True}
        result["dependencySourceCompatibility"] = dependency_proofs
        trace_receipt = root / trace["buildReceipt"]
        if helper.sha256(trace_receipt) != trace["buildReceiptSHA256"]:
            raise RuntimeError("trace_actual_build_receipt_changed")
        trace_build = json.loads(trace_receipt.read_text(encoding="utf-8"))
        if trace_build.get("status") != "PASS_BUILD_ONLY" or trace_build.get("engineCompileExitCode") != 0 or trace_build.get("modulewrapExitCode") != 0:
            raise RuntimeError("timestamp_engine_compilation_not_successful")
        for flag in ("sourceStable", "cachedModulesStable", "copiedSourcesStable", "compilerUnchanged", "runnerUnchanged", "boundedRunnerUnchanged"):
            if trace_build.get(flag) is not True:
                raise RuntimeError("timestamp_engine_build_provenance_incomplete")
        if trace_build.get("diagnosticChange") != "timestampUnixMs only" or trace_build.get("requestConfigurationChanged") is not False or trace_build.get("timeoutsChanged") is not False:
            raise RuntimeError("timestamp_only_delta_not_proven")
        result["diagnosticCompilerSHA256"] = trace_build["compilerSHA256"]
        patch = root / trace["patch"]
        if helper.sha256(patch) != trace["patchSHA256"]:
            raise RuntimeError("reviewed_trace_diff_changed")
        compiled = trace["compiledFiles"]
        for value in compiled.values():
            if helper.sha256(root / value["path"]) != value["sha256"]:
                raise RuntimeError("traced_compiler_output_changed")
        trace_dir = (root / compiled["PinkhaAnyEngine.o"]["path"]).parent
        for name, sha in trace["copiedEngineSourceManifest"].items():
            if helper.sha256(trace_dir / "EngineSources" / name) != sha:
                raise RuntimeError("traced_compiler_source_changed")
        v2_path = root / trace_build["v2ProvenancePath"]
        if helper.sha256(v2_path) != trace_build["v2ProvenanceSHA256"]:
            raise RuntimeError("original_v2_trace_provenance_changed")
        v2_proof = json.loads(v2_path.read_text(encoding="utf-8"))
        v2_dir = (root / v2_proof["compiledFiles"]["PinkhaAnyEngine.o"]["path"]).parent
        v2_http = (v2_dir / "EngineSources/AnyHTTPClient.swift").read_text(encoding="utf-8")
        v3_http = (trace_dir / "EngineSources/AnyHTTPClient.swift").read_text(encoding="utf-8")
        old_field = '"elapsedMs": Int(max(0, ProcessInfo.processInfo.systemUptime - start) * 1000)'
        new_field = old_field + ',\n        "timestampUnixMs": Int64((Date().timeIntervalSince1970 * 1000).rounded(.down))'
        if v2_http.count(old_field) != 1 or v2_http.replace(old_field, new_field) != v3_http:
            raise RuntimeError("v3_change_exceeds_absolute_timestamp_field")
        result["absoluteTimestampOnlyDeltaVerified"] = True
        shutil.copyfile(trace_receipt, out / "diagnostic-engine-build-receipt.json")
        shutil.copyfile(trace_path, out / "reused-trace-manifest.json")
        shutil.copyfile(patch, out / "diagnostic-http-trace.diff")
        shutil.copyfile(trace_dir / "EngineSources/AnyHTTPClient.swift", out / "executed-diagnostic-http-client.swift")
        result.update(traceManifestSHA256=args.trace_manifest_sha256, traceBuildReceiptSHA256=helper.sha256(trace_receipt),
                      tracePatchSHA256=helper.sha256(patch), diagnosticSourceInputs=trace["copiedEngineSourceManifest"])
        original_objects = proof["objectHashes"]
        for path, sha in original_objects.items():
            if helper.sha256(Path(path)) != sha:
                raise RuntimeError("retained_original_object_changed")
        command = list(proof["process"]["command"])
        if Path(command[0]).resolve() != Path(trace["compilerCommand"][0]).resolve() or "x86_64-unknown-windows-msvc" not in trace["modulewrapCommand"]:
            raise RuntimeError("trace_toolchain_or_target_mismatch")
        response_indexes = [i for i, value in enumerate(command) if value.startswith("@")]
        if len(response_indexes) != 1:
            raise RuntimeError("unexpected_original_response_file_count")
        original_response = Path(command[response_indexes[0]][1:])
        objects = [Path(line.strip().strip('"')).resolve() for line in original_response.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(objects) != len(original_objects) or {str(p) for p in objects} != set(original_objects):
            raise RuntimeError("complete_original_object_set_mismatch")
        engine_objects = [p for p in objects if "PinkhaAnyEngine.build" in p.parts]
        expected_engine_names = {name + ".o" for name in original_engine} | {"PinkhaAnyEngine.swiftmodule.o"}
        if {p.name for p in engine_objects} != expected_engine_names or len(engine_objects) != len(expected_engine_names):
            raise RuntimeError("complete_engine_object_replacement_required")
        replacements = [root / compiled[name]["path"] for name in ("PinkhaAnyEngine.o", "PinkhaAnyEngine.swiftmodule.o")]
        objects = [p for p in objects if p not in engine_objects] + replacements
        if len(objects) != len(set(objects)):
            raise RuntimeError("duplicate_diagnostic_link_object")
        expected = {str(p): helper.sha256(p) for p in objects}
        response = out / "Objects.LinkFileList"
        response.write_text("\n".join('"' + str(p).replace('\\', '/') + '"' for p in objects) + "\n", encoding="utf-8")
        command[response_indexes[0]] = "@" + str(response)
        executable = out / "guarded-hierarchy-correlated-probe.exe"
        command[command.index("-o") + 1] = str(executable)
        if "/debug:none" not in command or "/threads:1" not in command:
            raise RuntimeError("bounded_link_profile_missing")
        result.update(objectCount=len(objects), objectHashes=expected, removedEngineObjects=[str(p) for p in engine_objects],
                      insertedEngineObjects=[str(p) for p in replacements], unchangedAssertionSourceSHA256=helper.sha256(root / "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegrationProbe/GuardedHierarchyProbe.swift"))
        stage = out / "link"
        stage.mkdir()
        result["process"] = helper.run_process(command, root, stage, 240)
        status = result["process"]
        if status.get("exitCode") != 0 or status.get("timedOut") or status.get("cleanupErrors") or status.get("runnerErrorType"):
            raise RuntimeError("diagnostic_hierarchy_link_failed")
        if any(helper.sha256(Path(path)) != sha for path, sha in expected.items()):
            raise RuntimeError("diagnostic_link_input_changed")
        result.update(status="PASS_EXACT_SOURCE_COMPONENT_BUILD", binary=str(executable), binarySHA256=helper.sha256(executable), binaryBytes=executable.stat().st_size)
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
    print(json.dumps({k: result[k] for k in ("status", "binarySHA256", "objectCount", "sourceStable", "diagnosticsOnly", "errorType", "errorCode") if k in result}))
    return 0 if result["status"] == "PASS_EXACT_SOURCE_COMPONENT_BUILD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
