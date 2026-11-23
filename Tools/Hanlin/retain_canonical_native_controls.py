#!/usr/bin/env python3
"""Reuse the original 69 native-lane controls for one reviewed SDK consumer.

No controller method or product test is executed. Original failure conclusions
remain unchanged; actual native/UI execution is a separate required gate.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

POLICY_PATH = "Tools/Hanlin/canonical-native-control-reuse.json"
POLICY_SHA256 = "25773e452cabf62eac2dca31b9a9051928c0d249a3ca5533a94e4c455ffc527b"
BRANCH = "codex/chatgpt-wave15-canonical-hanlin-20261123"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bootstrap_read(root, name, expected):
    path = root / name
    require(path.resolve().is_relative_to(root)
            and not any(part.is_symlink() for part in (path, *path.parents) if part != root),
            "Linked or escaping native-control admission input")
    raw = path.read_bytes()
    require(sha(raw) == expected, "Changed native-control admission: " + name)
    return raw


def verify(app):
    root = Path(app).resolve(strict=True)
    policy = json.loads(bootstrap_read(root, POLICY_PATH, POLICY_SHA256))
    require(policy["schema"] == "pinkha-canonical-native-control-reuse-v1"
            and policy["consumer_branch"] == BRANCH and policy["native_controller_methods"] == 69,
            "Unknown canonical native-control scope")
    helper = root / policy["owner_helper_path"]
    bootstrap_read(root, policy["owner_helper_path"], policy["owner_helper_sha256"])
    spec = importlib.util.spec_from_file_location("original_sdk06_control_retention", helper)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    original_raw = original.read_bound(root, policy["owner_manifest_path"], original.ADMISSION_SHA256)
    require(sha(original_raw) == policy["owner_manifest_sha256"], "Changed original control admission")
    admission = original.decode_json(original_raw)
    proofs = {item["path"]: original.read_bound(root, item["path"], item["sha256"])
              for item in admission["proof_files"]}
    require(len(proofs) == len(admission["proof_files"]), "Duplicate original proof input")
    imported = original.decode_json(original.read_bound(root, **{
        "relative": policy["import_receipt"]["path"], "expected": policy["import_receipt"]["sha256"]}))
    require(imported["controller_methods_executed"] == imported["product_tests_executed"] == 0
            and len(imported["source_inputs"]) == 28
            and set(policy["source_inputs"]) == set(imported["source_inputs"]) | {"Tools/Hanlin/wave15-core-tests.json"},
            "Actual native-controller input closure differs")
    original_inputs = {item["path"]: item for item in admission["source_inputs"]}
    sources = {}
    for path in policy["source_inputs"]:
        item = original_inputs[path]
        delta = policy["source_deltas"].get(path)
        current = original.read_bound(root, path, delta["current_sha256"] if delta else item["current_sha256"])
        if path in imported["source_inputs"]:
            require(sha(current) == imported["source_inputs"][path]["sha256"], "Imported source closure changed")
        reviewed = current
        if delta:
            text = current.decode("utf-8")
            for replacement in delta["replacements"]:
                require(text.count(replacement["current"]) == 1, "Candidate admission change is not exact")
                text = text.replace(replacement["current"], replacement["original"])
            reviewed = text.encode("utf-8")
            require(sha(reviewed) == delta["reviewed_base_sha256"] == item["current_sha256"],
                    "Candidate changed more than the reviewed admission/pin-reader scope")
        before = proofs[item["original_snapshot"]]
        require(sha(before) == item["original_sha256"], "Original dependency source differs")
        mode = item["retention"]
        if mode == "byte_identical":
            require(reviewed == before, "Previously tested dependency changed: " + path)
        elif mode == "wave_scoped":
            require(original.wave_scope(reviewed) == original.wave_scope(before) == item["scopes"]
                    and original.namespace_tree(reviewed) == original.namespace_tree(before),
                    "Original native UI/identity scope changed")
            for alternate in item.get("alternate_original_snapshots", []):
                prior = proofs[alternate["path"]]
                require(sha(prior) == alternate["sha256"]
                        and original.wave_scope(prior) == item["scopes"]
                        and original.namespace_tree(prior) == original.namespace_tree(reviewed),
                        "Original alternate UI/identity scope changed")
        elif mode == "import_surface_only":
            require(original.namespace_tree(reviewed) == original.namespace_tree(before), "Imported declaration surface changed")
        else:
            require(mode in {"qualified_observer_production", "qualified_observer_tests"}, "Unknown source retention")
        sources[path] = current
    observer = admission["observer_extension"]
    review = original.decode_json(proofs[observer["review"]])
    require(review["actual_control_passes"] == 7 and review["old_controls_rerun"] == 0
            and review["source_base"] == admission["origins"]["hanlin"]["source_sha"], "Observer proof origin changed")
    for path, expected in review["source_sha256"].items():
        require(sha(sources[path]) == expected, "Actual observer qualification source changed")
    tests = observer["test_path"]
    require(original.observer_remainder(sources[tests], observer["current_only_declarations"])
            == original.observer_remainder(proofs[original_inputs[tests]["original_snapshot"]], observer["retired_declarations"]),
            "Previously retained observer methods/helpers changed")
    modules = [item for item in admission["modules"] if item["path"] in policy["modules"]]
    require(len(modules) == 2, "Exactly the two original native control modules are required")
    requested = {value["batch"] for module in modules for value in module["methods"].values()}
    batches = {}
    for item in admission["batches"]:
        if item["id"] not in requested:
            continue
        parsed = original.unittest_batches(proofs[item["log"]])
        require(len(parsed) == item["log_batch_count"], "Original log batch count changed")
        batch = parsed[item["batch_index"]]
        require(batch["count"] == item["count"] and batch["seconds"] == item["seconds"]
                and sorted(value["name"] for value in batch["methods"]) == item["methods"], "Original named PASS scope changed")
        batches[item["id"]] = batch
    require(set(batches) == requested, "An original proof batch is missing")
    catalog = []
    for module in modules:
        current = original.test_declarations(sources[module["path"]])
        require(current == module["current_declarations"] and set(current) == set(module["methods"])
                and len(current) == policy["modules"][module["path"]], "Current native control declarations changed")
        for name, binding in module["methods"].items():
            require(current[name] == binding["declaration_sha256"]
                    and name in {item["name"] for item in batches[binding["batch"]]["methods"]}
                    and original.test_declarations(proofs[binding["tested_source_snapshot"]]).get(name) == current[name],
                    "Current native control lacks its exact original named PASS/source")
            catalog.append({"module": module["path"], "method": name, "proof_batch": binding["batch"]})
    require(len(catalog) == 69 and len({(item["module"], item["method"]) for item in catalog}) == 69,
            "The retained native control selection is not exactly69")
    execution = original.decode_json(proofs[admission["origins"]["hanlin"]["execution"]])
    require(execution["status"] == "FAIL" and execution["run_id"] == "45096079315"
            and execution["run_attempt"] == "1"
            and execution["source_sha"] == admission["origins"]["hanlin"]["source_sha"], "Original failed native lane identity changed")
    return {"status": "PASS_RETAINED_NATIVE_CONTROLLER_CONTROLS_ONLY", "policy_sha256": POLICY_SHA256,
            "current_control_methods": 69, "retained_original_methods": 62, "qualified_observer_methods": 7,
            "controller_methods_executed_now": 0, "product_tests_executed_now": 0,
            "source_inputs": {path: sha(raw) for path, raw in sources.items()}, "catalog": catalog,
            "original_failed_run": "45096079315", "original_failure_preserved": True,
            "scope_limit": "Original Python native-lane controls only. Current app build, live mapping, native1/UI1 and SDK23/32+ACK remain separate."}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    app = args.app.resolve(strict=True)
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(app), *arguments], text=True).strip()
    head, branch = git("rev-parse", "HEAD"), git("branch", "--show-current")
    require(branch == BRANCH and not git("status", "--porcelain", "--untracked-files=no"),
            "Exact clean canonical consumer branch required")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(head == os.environ.get("GITHUB_SHA") and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH,
                "Actual caller source/ref differs")
    result = verify(app)
    result.update(application_source_sha=head, application_source_tree=git("rev-parse", "HEAD^{tree}"), branch=branch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"source_inputs", "catalog"}}))


if __name__ == "__main__":
    main()
