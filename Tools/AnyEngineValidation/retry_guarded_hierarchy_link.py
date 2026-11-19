#!/usr/bin/env python3
"""Retry only the retained hierarchy link with a smaller validation profile."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input-build-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, original, out = args.repo_root.resolve(), args.input_build_dir.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    helper_path = root / "Tools/AnyEnginePort/run_live_provider_probe.py"
    spec = importlib.util.spec_from_file_location("process_helper", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    result = {"status": "FAIL", "scope": "Same complete Integration18/probe4 compilation and542 original/fresh object inputs; link-only retry disables DWARF and multithreading, with no production-source or assertion change."}
    before = helper.source_snapshot(root, Path(__file__))
    helper.write_json(out / "source-before.json", before)
    shutil.copyfile(__file__, out / "executed-link-retry.py")
    shutil.copyfile(helper_path, out / "executed-process-helper.py")
    try:
        original_receipt = original / "result.json"
        proof = json.loads(original_receipt.read_text(encoding="utf-8"))
        if proof.get("status") != "FAIL" or proof.get("errorCode") != "actual_link_failed" or proof.get("sourceStable") is not True:
            raise RuntimeError("expected_retained_link_failure_missing")
        if proof["steps"][-1].get("timedOut") is not True or proof["steps"][-1].get("exitCode") != 124:
            raise RuntimeError("expected_original_link_deadline_missing")
        if any(step.get("exitCode") != 0 or step.get("timedOut") or step.get("cleanupErrors") for step in proof["steps"][:-1]):
            raise RuntimeError("producer_compile_or_wrapper_not_successful")
        for path, sha in proof["sourceInputs"].items():
            if helper.sha256(root / path) != sha:
                raise RuntimeError("compiled_source_changed:" + path)
        expected = {**proof["cachedDependencyObjectHashes"], **proof["newTargetObjectHashes"]}
        for path, sha in expected.items():
            if helper.sha256(Path(path)) != sha:
                raise RuntimeError("retained_object_changed")
        argv = list(proof["steps"][-1]["command"])
        response_files = [Path(value[1:]) for value in argv if value.startswith("@")]
        if len(response_files) != 1:
            raise RuntimeError("unexpected_link_response_file_count")
        objects = [Path(line.strip().strip('"')).resolve() for line in response_files[0].read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(objects) != len(expected) or {str(p) for p in objects} != set(expected):
            raise RuntimeError("complete_original_object_set_mismatch")
        result.update(sourceInputs=proof["sourceInputs"], objectCount=len(objects), objectHashes=expected,
                      retainedProducerReceipt={"path": str(original_receipt), "sha256": helper.sha256(original_receipt)},
                      responseFileSHA256=helper.sha256(response_files[0]), prior180SecondFailureRetained=True)
        executable = out / "guarded-hierarchy-probe.exe"
        argv[argv.index("-o") + 1] = str(executable)
        filtered, removed, i = [], [], 0
        while i < len(argv):
            if argv[i] == "-g":
                removed.append(argv[i]); i += 1; continue
            if argv[i:i+2] == ["-Xlinker", "-debug:dwarf"]:
                removed.extend(argv[i:i+2]); i += 2; continue
            filtered.append(argv[i]); i += 1
        if removed != ["-g", "-Xlinker", "-debug:dwarf"]:
            raise RuntimeError("unexpected_original_debug_link_profile")
        additions = ["-Xlinker", "/debug:none", "-Xlinker", "/threads:1",
                     "-Xlinker", "/opt:noref", "-Xlinker", "/opt:noicf"]
        result["profileChanges"] = {"removed": removed, "added": additions,
            "explanation": "Disable DWARF work and linker parallelism; keep non-ref/non-ICF behavior of the original debug profile. Compiled code, inputs and assertions are unchanged."}
        stage = out / "link"
        stage.mkdir()
        result["process"] = helper.run_process(filtered + additions, root, stage, 240)
        status = result["process"]
        if status.get("exitCode") != 0 or status.get("timedOut") or status.get("cleanupErrors") or status.get("runnerErrorType"):
            raise RuntimeError("bounded_low_memory_link_failed")
        if any(helper.sha256(Path(path)) != sha for path, sha in expected.items()):
            raise RuntimeError("retained_object_changed_during_link")
        result.update(status="PASS_EXACT_SOURCE_COMPONENT_BUILD", binary=str(executable),
                      binarySHA256=helper.sha256(executable), binaryBytes=executable.stat().st_size)
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
    print(json.dumps({k: result[k] for k in ["status", "binarySHA256", "objectCount", "sourceStable", "errorType", "errorCode"] if k in result}))
    return 0 if result["status"] == "PASS_EXACT_SOURCE_COMPONENT_BUILD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
