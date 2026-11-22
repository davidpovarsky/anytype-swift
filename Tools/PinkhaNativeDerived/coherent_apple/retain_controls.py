#!/usr/bin/env python3
"""Retain only the unchanged controls that passed before Apple bind failed."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import zipfile

import contract

ORIGINAL_RUN = "45030504099"
ORIGINAL_SOURCE = "22f4fa5aa8b29c167bcda100e23a30438a22adab"
PROOF = "docs/validation/20261122-coherent-heart-apple-failure"
ZIP_SHA = "43c61574eb4aeb2d9a19ccaba88748839b335032548e059a05ab278c17109ad1"
LOG_SHA = "10aa62a87285e947c694ce5882cf7daf5a7b1e57cd8fa6f590b058eb85837a92"
BUILD_SHA = "8297160846c1c4fa1505c1729fb7ddc6f2ffabee0f5bfe5c10298afe2602bfc3"
SOURCES = {
    "Tools/PinkhaNativeDerived/coherent_apple/test_controls.py": "2ad16ad3de0d1c1c2d2d7a5a0ab2f3e2916114da31063a4566e1b83d3ee1e714",
    "Tools/PinkhaNativeDerived/coherent_apple/contract.py": "7d285d1915cf4c48764adbdd913b87427bd9b87ba09d42dcfa4b31b4eb554578",
    "Tools/PinkhaNativeDerived/coherent_apple/fixture.py": "03d7a3f04ae90d38c55b12d17c455b3a5f3b5f8ec39c693fe80b2d5712ba95ee",
    "Tools/PinkhaNativeDerived/coherent_apple/run_host.py": "69ce00d646740b54c26739b8aa52a00f185fbe24e1e95855b5753193b173c054",
    "Tools/PinkhaNativeDerived/coherent_apple/fixture_bridge.go": "2970a522b338abed15ba8710a60c04b543ac93f66adce23a03dc724fb83ea61b",
    "Tools/PinkhaNativeDerived/coherent_read/account/coherent_authority_account_test.go": "3a1fcd0f370224e59137897467e59bb4d41e44ce580e3c0bacce48170019d71b",
    "Tools/PinkhaNativeDerived/coherent_read/account/native_signed_revocation_base_test.go": "389184e3ba40e1371143505c48eedd6420872f35f57d66784ee5262c62bed25d",
}
PYTHON_METHODS = {
    "test_build_identity_never_conflates_production_and_fixture",
    "test_go_assertion_adapter_rejects_failures_and_runs_cleanup",
    "test_native_producer_must_be_exact_successful_route",
    "test_original_assertions_are_exactly_bound_before_fixture_derivation",
    "test_raw_t5_denial_requires_exact_error_and_no_payload",
}
GO_METHODS = {"TestAssertionAdapterPositiveAndNegativeSemantics", "TestCleanupRunsOnceInReverseOrder",
              "TestFailureDiagnosticsExcludeAssertionValues"}
HOST = "Tools/PinkhaNativeDerived/coherent_apple/run_host.py"
# Derived from the exact original HOST bytes in SOURCES. The old controls call
# only qualify_t5_wire -> fields. Every import, top-level statement, function
# signature/decorator/default, and those two complete bodies remain pinned.
# Only the bodies of functions never invoked by those controls are excluded.
HOST_UNEXECUTED = frozenset({"load_helpers", "validate_execution", "qualify_observation", "source_snapshot",
                           "prepare_harness", "execute", "main"})
HOST_CONTROL_AST_SHA = "a222135fe50d341c269eb7f3eb1a76b4d83463838e51b478becc3023caf7a48c"


def host_control_scope(path):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    contract.require(len(functions) == len(set(functions))
                     and set(functions) == HOST_UNEXECUTED | {"fields", "qualify_t5_wire"},
                     "Retained host function declarations changed")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in HOST_UNEXECUTED:
            node.body = [ast.Pass()]
    def canonical(value):
        if isinstance(value, ast.AST):
            return {"node": type(value).__name__, **{key: canonical(child) for key, child in ast.iter_fields(value)
                    if not (key == "type_params" and child == [])}}
        if isinstance(value, list):
            return [canonical(child) for child in value]
        return value
    observed = hashlib.sha256(json.dumps(canonical(tree), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    contract.require(observed == HOST_CONTROL_AST_SHA, "Retained host control/import dependency AST changed")
    return dict(original_complete_source_sha256=SOURCES[HOST], current_complete_source_sha256=contract.digest(path),
                unchanged_control_ast_sha256=observed, executed_functions=["fields", "qualify_t5_wire"],
                excluded_unexecuted_function_bodies=sorted(HOST_UNEXECUTED),
                complete_host_file_claim=("UNCHANGED_COMPLETE_SOURCE" if contract.digest(path) == SOURCES[HOST]
                    else "CHANGED_OUTSIDE_RETAINED_CONTROL_DEPENDENCIES"),
                dependency_scope="Exact module imports/statements, declaration metadata, two executed bodies, and separately pinned contract.py")


def qualify(root):
    original = root / PROOF
    for name, expected in SOURCES.items():
        if name == HOST:
            continue
        contract.require(contract.digest(root / name) == expected, "Retained control dependency changed: " + name)
    host = host_control_scope(root / HOST)
    archive, log, build = original / "original-evidence.zip", original / "original-controls.log", original / "original-build.json"
    for path, expected in ((archive, ZIP_SHA), (log, LOG_SHA), (build, BUILD_SHA)):
        contract.require(contract.digest(path) == expected, "Original control evidence changed: " + path.name)
    with zipfile.ZipFile(archive) as bundle:
        for name, path in (("controls/results.log", log), ("proof/build.json", build)):
            contract.require(bundle.namelist().count(name) == 1 and bundle.read(name) == path.read_bytes(),
                             "Control evidence is not the original archived entry")
    receipt = json.loads(build.read_bytes())
    contract.require(receipt.get("app_sha") == ORIGINAL_SOURCE and receipt.get("run_id") == ORIGINAL_RUN
        and receipt.get("run_attempt") == "1" and receipt.get("status") == "FAIL"
        and receipt.get("phase") == "BIND_PRODUCTION" and receipt.get("frameworks") == {},
        "Original build failure scope changed")
    text = log.read_text(encoding="utf8")
    methods = re.findall(r"^(test_\w+) \(__main__\.CoherentAppleControls\.\1\) \.\.\. ok$", text, re.M)
    go = re.findall(r"^--- PASS: (Test\w+) \([0-9.]+s\)$", text, re.M)
    contract.require(len(methods) == 5 and set(methods) == PYTHON_METHODS
        and re.search(r"^Ran 5 tests in [0-9.]+s\n\nOK$", text, re.M)
        and len(go) == 3 and set(go) == GO_METHODS
        and not re.search(r"FAIL|ERROR|SKIP|skipped", text), "Original controls did not all pass")
    return dict(status="RETAINED_UNCHANGED_CONTROL_EXECUTION", original_run_id=ORIGINAL_RUN,
        original_source_sha=ORIGINAL_SOURCE, original_run_attempt=1, original_artifact_zip_sha256=ZIP_SHA,
        original_log_sha256=LOG_SHA, original_build_sha256=BUILD_SHA, original_source_sha256=SOURCES,
        unchanged_complete_source_sha256={name: sha for name, sha in SOURCES.items() if name != HOST},
        host_control_dependency_scope=host,
        python_methods_passed=5, embedded_go_methods_passed=3, fail=0, skip=0,
        python_methods=sorted(PYTHON_METHODS), embedded_go_methods=sorted(GO_METHODS),
        methods_executed_again=0, new_build_helpers_covered_by="test_binding_scope.py",
        apple_framework_status="NOT_PROVEN_BY_RETAINED_CONTROLS", ios_execution_status="NOT_RUN")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = qualify(args.control.resolve())
    contract.save(args.output, result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
