#!/usr/bin/env python3
"""Source correspondence and real-file integrity controls only; no Go or native execution."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
BASE = "ce1e78576de6a3d586e849d5990d008944ff2777"
PACKET = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/bc-native-qualification-20261123"
SUPPORT = "017778c096eca985774bd1a4f1e1e117ac3dee6ac08082c2a9793273826aa196"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=30)

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    packet = repo / PACKET
    repair = packet / "closure-repair-20261123"
    old_raw = git(repo, "show", BASE + ":" + PACKET + "/run_native_closed_import.py")
    require(old_raw == (repair / "ORIGINAL_DRIVER.py").read_bytes(), "Retained original driver differs")
    new_raw = (packet / "run_native_closed_import.py").read_bytes()
    old, new = old_raw.decode(), new_raw.decode()
    transforms = json.loads((repair / "DRIVER_EXACT_TRANSFORMS.json").read_text())
    restored = new
    for row in reversed(transforms):
        require(restored.count(row["after"]) == 1, "Ambiguous exact inverse")
        restored = restored.replace(row["after"], row["before"], 1)
    require(restored.encode() == old_raw, "Whole driver inverse differs")

    old_tree, new_tree = ast.parse(old), ast.parse(new)
    old_functions = {x.name: ast.get_source_segment(old, x) for x in old_tree.body if isinstance(x, ast.FunctionDef)}
    new_functions = {x.name: ast.get_source_segment(new, x) for x in new_tree.body if isinstance(x, ast.FunctionDef)}
    unchanged = sorted(set(old_functions) - {"main", "stability"})
    require(all(old_functions[n] == new_functions[n] for n in unchanged),
            "An unrelated original gate function changed")
    require(set(new_functions) - set(old_functions) == {"compile_only_binary_stability"},
            "Unexpected additional gate function")
    def execution_call(tree):
        values = [x for x in ast.walk(tree) if isinstance(x, ast.Call) and x.args
                  and isinstance(x.args[0], ast.Constant) and
                  x.args[0].value == "execute-original-closed-import"]
        require(len(values) == 1, "Native execution call differs")
        return ast.dump(values[0], include_attributes=False)
    require(execution_call(old_tree) == execution_call(new_tree),
            "The original native nine-leaf execution changed")

    original_manifest = json.loads(git(repo, "show", BASE + ":" + PACKET + "/EXECUTION_INPUTS.json"))
    manifest = json.loads((packet / "EXECUTION_INPUTS.json").read_bytes())
    require({k: v for k, v in original_manifest.items() if k != "controls"} ==
            {k: v for k, v in manifest.items() if k != "controls"}, "A native source or assertion manifest input changed")
    old_controls = {x["path"]: x for x in original_manifest["controls"]}
    changed = [x["path"] for x in manifest["controls"] if x != old_controls[x["path"]]]
    require(sorted(changed) == ["run_native_closed_import.py", "workflow.template.yml"],
            "Unexpected execution-control changes")
    for row in manifest["controls"]:
        raw = (packet / row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"], "Control bytes differ")
    require(len(manifest["required_compiler_inputs"]) == 87, "Original required source coverage lost")
    template = (packet / "workflow.template.yml").read_bytes()
    original_template = git(repo, "show", BASE + ":" + PACKET + "/workflow.template.yml")
    require(template.replace(b"codex/otzaria-native-import-closure-20261123",
                             b"codex/otzaria-native-import-qualification-20261123") == original_template,
            "Workflow changed beyond the isolated branch binding")

    support_path = packet / "retained-inputs/support/run_original_application_compile.py"
    require(sha(support_path.read_bytes()) == SUPPORT, "Original command/digest owner changed")
    support = module(support_path, "closure_original_support")
    driver = module(packet / "run_native_closed_import.py", "closure_candidate_driver")
    cases = []
    # These are deliberately ordinary byte fixtures, not claimed compiler output.
    # They exercise the actual new integrity helper without any fake native runner.
    with tempfile.TemporaryDirectory(prefix="otzaria-closure-source-control-") as temporary:
        directory = Path(temporary)
        path = directory / "ordinary-integrity-fixture.bin"
        raw = b"ordinary source-only integrity fixture\n"
        path.write_bytes(raw)
        record = {"bytes": len(raw), "sha256": sha(raw)}
        require(driver.compile_only_binary_stability((path, record), support) is True,
                "Unchanged regular byte fixture was not admitted")
        cases.append({"name": "unchanged_regular_byte_fixture", "status": "PASS"})
        path.write_bytes(b"X" + raw[1:])
        try:
            driver.compile_only_binary_stability((path, record), support)
        except RuntimeError as error:
            require(str(error) == "Actual original core compile-only binary changed",
                    "Unexpected changed-content refusal")
        else:
            raise RuntimeError("Same-size changed bytes were admitted")
        cases.append({"name": "same_size_changed_content_refused", "status": "PASS"})
        target = directory / "same-byte-target.bin"
        target.write_bytes(raw)
        path.unlink()
        path.symlink_to(target)
        try:
            driver.compile_only_binary_stability((path, record), support)
        except RuntimeError as error:
            require(str(error) == "Original core compile-only output is not an owned regular file",
                    "Unexpected symlink refusal")
        else:
            raise RuntimeError("Same-byte symlink was admitted")
        cases.append({"name": "same_byte_symlink_refused", "status": "PASS"})
        require(driver.compile_only_binary_stability(None, support) is False,
                "No observed compiler output was relabeled as checked")
        cases.append({"name": "unobserved_compile_output_remains_unchecked", "status": "PASS"})

    result = {
        "schema": 1, "status": "PASS_SOURCE_AND_REAL_FILE_CONTROLS_ONLY",
        "observed_unix": time.time(), "base": BASE,
        "old_driver_sha256": sha(old_raw), "new_driver_sha256": sha(new_raw),
        "whole_driver_inverse": True, "unchanged_original_functions": unchanged,
        "unchanged_native_execution_call": True, "all_87_required_hashes_unchanged": True,
        "manifest_changed_control_rows": sorted(changed), "unchanged_source_manifest": True,
        "isolated_branch_only_template_delta": True,
        "new_controls": cases, "native_compilation": False, "native_tests": "NOT_RUN",
        "declaration_coverage_for_new_core_selection": "NOT_RUN",
        "core_compile_only_output": "NOT_RUN",
        "historical_native_components_replayed": False,
        "scope": "Four new ordinary filesystem integrity controls; no fake native binary, operation, ACK, dependency closure, Go invocation, or runtime pass."
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
