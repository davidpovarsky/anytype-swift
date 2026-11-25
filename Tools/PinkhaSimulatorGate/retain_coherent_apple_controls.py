#!/usr/bin/env python3
"""Verify unchanged original controller evidence without executing tests again."""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

import retain_current_composition_controls as composition_controls

EVIDENCE = "docs/validation/20261122-coherent-heart-apple-build/continuation-controls"
REPORT_SHA = "7aa150c574dddb7eecb0ff9e29e79a28e9f3246e7d3f8e78a945183b49d5f169"
EQUIVALENCE_SHA = "4cca32f0235b49966a46518ca64a28429718b4f7e22a4b20b3e81de5da749ed9"
EQUIVALENCE_PATHS = frozenset({"Tools/PinkhaNativeDerived/attachment_runtime.py",
                             "Tools/PinkhaNativeDerived/build_custom_heart.py",
                             "Tools/PinkhaNativeDerived/install_verified_heart.py"})
SELECTOR_OBSERVATION_SHA = "f24099b8fb11041b975309a8873f598a37c62df8683ee3f5c9ddc8f5ea947264"
PROOF = "docs/validation/20261122-coherent-heart-apple-build/proof-original.zip"
PROOF_SHA = "ff35f54d028057cccc3125d63e681a257e371d37cacd3e7a5ea0aadf1b69b358"
SELECTOR_SOURCE = {
    "Tools/PinkhaSimulatorGate/simulator_selection.py": "2309bb55b3752774bffc588a7c489392daa7ceb3b7279f6a9ec870899a1f1d5f",
    "Tools/PinkhaSimulatorGate/test_simulator_selection.py": "31fd9d6c5713a598f6a370abd27f56e65d4c705ac3344dd426dba23dd2d1df04",
}
LOGS = {"new-build-reuse-controls.log": (6, "OriginalBuildReuseControls"),
        "new-admission-controls.log": (4, "CoherentReuseAdmissionControls")}
BOOT_EVIDENCE = "docs/validation/20261122-coherent-heart-apple-boot"
BOOT_REVIEW_SHA = "65cbedb38544d7f98102cf1411fbcfdb717ee6ab17877e763840a21e103c7fd3"
BOOT_REPORT_SHA = "bc6d1ca46ef7715ecefba5f67bca3e88fa24c4b75d4ed3b342e66006cfc6c13c"
BOOT_SOURCE_PATHS = frozenset({"Tools/PinkhaNativeDerived/coherent_apple/run_host.py",
                             "Tools/PinkhaNativeDerived/coherent_runtime_admission.py"})
BOOT_CONTROL = "Tools/PinkhaSimulatorGate/test_coherent_boot_orchestration.py"
COMPOSITION_REVIEW_SHA = "98cc4d863e1b848252996bd4d87c54e5c09f1d3954efec98261653296552c24d"
COMPOSITION_REPORT_SHA = "fd1ff896624fe88e3775d1bba09642d19699205d8dc88d5e5050427509dfa932"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(root, relative, limit=16 * 1024**2):
    path = PurePosixPath(relative)
    require(relative and not path.is_absolute() and "\\" not in relative
            and all(part not in ("", ".", "..") for part in path.parts), "Invalid evidence/source path")
    target = root / path
    require(target.resolve().is_relative_to(root) and not target.is_symlink()
            and not any(parent.is_symlink() for parent in target.parents if parent != root and parent.is_relative_to(root))
            and target.is_file() and 0 < target.stat().st_size <= limit, "Missing or unsafe bounded retained file: " + relative)
    return target.read_bytes()


def ast_digest(raw):
    def canonical(value):
        if isinstance(value, ast.AST):
            return {"node": type(value).__name__, **{key: canonical(child) for key, child in ast.iter_fields(value)
                    if not (key == "type_params" and child == [])}}
        if isinstance(value, list):
            return [canonical(child) for child in value]
        if isinstance(value, bytes):
            return {"python_bytes_base64": base64.b64encode(value).decode()}
        if value is Ellipsis:
            return {"python_ellipsis": True}
        return value
    return sha(json.dumps(canonical(ast.parse(raw)), sort_keys=True, separators=(",", ":")).encode())


def qualify_exact_terminal_lf(raw, expected, review):
    require(review is not None and review.get("tested_sha256") == expected
            and review.get("exact_transformation") == "tested_bytes = canonical_git_bytes + one LF byte"
            and raw.endswith(b"\n") and not raw.endswith(b"\n\n")
            and len(raw) == review.get("canonical_git_bytes")
            and len(raw) + 1 == review.get("tested_bytes")
            and sha(raw) == review.get("canonical_git_sha256") and sha(raw + b"\n") == expected
            and hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == review.get("canonical_git_blob")
            and ast_digest(raw) == ast_digest(raw + b"\n") == review.get("canonical_ast_sha256"),
            "Source differs from the exact reviewed terminal-LF/Git/AST pair")


def qualify_boot_source(raw, expected, review):
    require(review.get("before_sha256") == expected and sha(raw) == review.get("after_sha256"),
            "Source differs from the exact reviewed boot repair")
    tree = ast.parse(raw)
    if review.get("path") == "Tools/PinkhaNativeDerived/coherent_apple/run_host.py":
        excluded = {"load_helpers", "validate_execution", "qualify_observation", "source_snapshot",
                    "prepare_harness", "execute", "main"}
        names = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        require(len(names) == len(set(names)) and set(names) == excluded | {"fields", "qualify_t5_wire"}
                and review.get("excluded_unexecuted_function_bodies") == sorted(excluded)
                and review.get("retained_executed_functions") == ["fields", "qualify_t5_wire"],
                "Original host control function scope changed")
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in excluded:
                node.body = [ast.Pass()]
    else:
        require(review.get("path") == "Tools/PinkhaNativeDerived/coherent_runtime_admission.py",
                "Unreviewed boot source path")
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "qualify_apple"]
        require(len(functions) == 1, "Original admission function is missing or duplicated")
        function = functions[0]
        branches = [node for node in function.body if isinstance(node, ast.If)
                    and ast_digest(ast.unparse(node.test).encode()) == review.get("new_branch_condition_ast_sha256")]
        require(len(branches) == 1 and len(branches[0].orelse) == 1,
                "Exact new split-build condition or unchanged legacy branch changed")
        branch = branches[0]
        index = function.body.index(branch)
        function.body[index:index + 1] = branch.orelse
    require(ast_digest(ast.unparse(tree).encode()) == review.get("original_ast_sha256"),
            "A retained original control dependency changed outside the exact new execution branch")


def qualify(control):
    root = control.resolve()
    composition = composition_controls.qualify(root, COMPOSITION_REVIEW_SHA, COMPOSITION_REPORT_SHA)
    raw = read(root, EVIDENCE + "/python-controls.json")
    require(sha(raw) == REPORT_SHA, "Original Python control report changed")
    report = json.loads(raw)
    require(report.get("schemaVersion") == 1 and report.get("status") == "PASS_NEW_PYTHON_CONTROLS_ONLY"
            and report.get("passed") == 10 and report.get("failed") == report.get("skipped") == 0
            and report.get("apple_execution") == "NOT_RUN" and report.get("frameworks_built") == 0
            and report.get("old_native_go_and_xctest_methods_executed") == 0,
            "Original local control execution scope differs")
    review_raw = read(root, EVIDENCE + "/source-equivalence-review.json")
    require(sha(review_raw) == EQUIVALENCE_SHA, "Exact source-equivalence review changed")
    review = json.loads(review_raw)
    entries = review.get("reviewed_sources", [])
    require(review.get("status") == "REVIEWED_EXACT_TERMINAL_LF_EQUIVALENCE"
            and review.get("original_python_report_sha256") == REPORT_SHA
            and len(entries) == 3 and {entry.get("path") for entry in entries} == EQUIVALENCE_PATHS,
            "Unexpected source-equivalence scope")
    reviewed = {entry["path"]: entry for entry in entries}
    boot_raw = read(root, BOOT_EVIDENCE + "/orchestration-review.json")
    require(sha(boot_raw) == BOOT_REVIEW_SHA, "Exact boot orchestration review changed")
    boot = json.loads(boot_raw)
    boot_entries = boot.get("reviewed_sources", [])
    require(boot.get("status") == "REVIEWED_EXACT_BOOT_ORCHESTRATION_AND_LEGACY_ADMISSION_BRANCH"
            and boot.get("original_controls_report_sha256") == REPORT_SHA
            and len(boot_entries) == 2 and {entry.get("path") for entry in boot_entries} == BOOT_SOURCE_PATHS,
            "Unexpected boot orchestration retention scope")
    boot_reviewed = {entry["path"]: entry for entry in boot_entries}
    observed_sources, applied_equivalence, applied_boot_review = {}, [], []
    for group, count in (("source_sha256", 13), ("input_sha256", 9)):
        entries = report.get(group, {})
        require(isinstance(entries, dict) and len(entries) == count, "Incomplete retained dependency/input map")
        for name, expected in entries.items():
            require(re.fullmatch(r"[0-9a-f]{64}", expected or ""), "Malformed original dependency digest")
            observed = read(root, name)
            current = observed
            if name in composition["source_before"]:
                require(sha(observed) == composition["receipt"]["source_sha256"][name],
                        "Current composition source changed during retention: " + name)
                current = composition["source_before"][name]
            if sha(current) != expected:
                require(group == "source_sha256" and name in reviewed.keys() | boot_reviewed.keys(),
                        "Retained controller dependency/input changed: " + name)
                if name in boot_reviewed:
                    qualify_boot_source(current, expected, boot_reviewed[name])
                    applied_boot_review.append(name)
                else:
                    qualify_exact_terminal_lf(current, expected, reviewed[name])
                    applied_equivalence.append(name)
            if group == "source_sha256":
                observed_sources[name] = sha(observed)
    checks = report.get("checks", [])
    require(isinstance(checks, list) and len(checks) == 2 and {entry.get("log") for entry in checks} == LOGS.keys(),
            "Missing or duplicate original controller logs")
    methods = []
    for check in checks:
        name = check["log"]; count, suite = LOGS[name]
        log = read(root, EVIDENCE + "/" + name, 128 * 1024)
        require(sha(log) == check.get("sha256"), "Original raw controller output changed: " + name)
        text = log.decode("utf8")
        actual = re.findall(r"^(test_\w+) \(__main__\." + re.escape(suite) + r"\.\1\) \.\.\. ok$", text, re.M)
        require(len(actual) == count and len(set(actual)) == count and actual == check.get("methods")
                and check.get("passed") == count and check.get("failed") == check.get("skipped") == 0
                and re.search(r"\nRan " + str(count) + r" tests in [0-9.]+s\n\nOK\n\Z", text)
                and not re.search(r"FAIL|ERROR|SKIP|skipped", text), "Original control method outcomes differ")
        methods.extend(actual)
    new_raw = read(root, BOOT_EVIDENCE + "/new-orchestration-controls.json")
    require(sha(new_raw) == BOOT_REPORT_SHA, "Original new boot-control report changed")
    new = json.loads(new_raw)
    require(new.get("status") == "PASS_NEW_BOOT_ORCHESTRATION_CONTROLS_ONLY"
            and new.get("passed") == 2 and new.get("failed") == new.get("skipped") == 0
            and new.get("apple_execution") == "NOT_RUN" and new.get("simulators_created") == new.get("frameworks_built") == 0
            and new.get("old_native_go_and_xctest_methods_executed") == new.get("old_python_test_methods_executed") == 0
            and set(new.get("source_sha256", {})) == set(report["source_sha256"]) |
                {"Tools/PinkhaSimulatorGate/simulator_selection.py", BOOT_CONTROL}
            and new.get("input_sha256") == {name: value for name, value in report["input_sha256"].items() if name != PROOF},
            "New boot-control scope or dependency inventory differs")
    for name, expected in new["source_sha256"].items():
        observed = read(root, name)
        current = observed
        if name in composition["source_before"]:
            require(sha(observed) == composition["receipt"]["source_sha256"][name],
                    "Current composition source changed during boot retention: " + name)
            current = composition["source_before"][name]
        if sha(current) != expected:
            require(name in reviewed, "New boot-control dependency changed: " + name)
            qualify_exact_terminal_lf(current, expected, reviewed[name])
    new_log = read(root, BOOT_EVIDENCE + "/new-orchestration-controls.log", 128 * 1024)
    require(sha(new_log) == new.get("log_sha256"), "Original new boot-control log changed")
    new_text = new_log.decode("utf8")
    new_methods = re.findall(r"^(test_\w+) \(__main__\.CoherentBootOrchestrationControls\.\1\) \.\.\. ok$", new_text, re.M)
    require(len(new_methods) == len(set(new_methods)) == 2 and new_methods == new.get("methods")
            and re.search(r"\nRan 2 tests in [0-9.]+s\n\nOK\n\Z", new_text)
            and not re.search(r"FAIL|ERROR|SKIP|skipped", new_text), "Original new boot-control outcomes differ")
    observation_raw = read(root, EVIDENCE + "/selector-observation.json")
    require(sha(observation_raw) == SELECTOR_OBSERVATION_SHA, "Original selector observation record changed")
    observation = json.loads(observation_raw)
    require(observation.get("runID") == 45035194823 and observation.get("newControlsPassed") == 5
            and observation.get("appleExecution") == "NOT_RUN"
            and observation.get("scope") == "original inventory replay, no simulator created",
            "Selector observation is not the separately labeled prior tool output")
    for name, expected in SELECTOR_SOURCE.items():
        require(sha(read(root, name)) == expected, "Observed selector dependency changed: " + name)
    proof = read(root, PROOF)
    require(sha(proof) == PROOF_SHA and len(proof) == 3791782, "Original inventory proof ZIP changed")
    with zipfile.ZipFile(root / PROOF) as archive:
        for name, key in (("proof/host/runtimes.log", "runtimeInventorySHA256"),
                          ("proof/host/device-types.log", "deviceInventorySHA256")):
            require(archive.namelist().count(name) == 1 and sha(archive.read(name)) == observation.get(key),
                    "Selector observation has another original runtime/device inventory")
    return dict(status="RETAINED_UNCHANGED_COHERENT_APPLE_CONTROLLER_EVIDENCE",
                python_report_sha256=REPORT_SHA, retained_raw_log_methods=10, methods=methods,
                source_sha256=report["source_sha256"], input_sha256=report["input_sha256"],
                observed_source_sha256=observed_sources, exact_source_equivalence_review_sha256=EQUIVALENCE_SHA,
                applied_terminal_lf_equivalence=applied_equivalence,
                applied_boot_source_review=applied_boot_review, boot_source_review_sha256=BOOT_REVIEW_SHA,
                retained_new_orchestration_control_methods=2, new_orchestration_methods=new_methods,
                new_orchestration_report_sha256=BOOT_REPORT_SHA, total_retained_python_methods=12,
                source_python=report["python"], source_platform=report["platform"], tests_executed_this_run=0,
                frameworks_built_this_run=0, apple_execution="NOT_RUN", production_binary_execution="NOT_RUN",
                selector_observation=dict(evidence_kind="PRIOR_TOOL_OUTPUT_OBSERVATION_WITHOUT_RAW_UNITTEST_LOG",
                    reported_controls_passed=5, raw_unittest_log_available=False,
                    observation_sha256=SELECTOR_OBSERVATION_SHA, source_sha256=SELECTOR_SOURCE,
                    actual_compatible_simulator_creation_and_xctest="STILL_REQUIRED"),
                current_composition_controls=composition["receipt"],
                verifier_sha256=sha(Path(__file__).read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = qualify(args.control)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(json.dumps(dict(status=value["status"], retained_raw_log_methods=10,
                         selector_evidence_kind=value["selector_observation"]["evidence_kind"],
                         tests_executed_this_run=0, apple_execution="NOT_RUN"), sort_keys=True))


if __name__ == "__main__":
    main()
