#!/usr/bin/env python3
"""Finite synthetic qualification controls; never runs Swift, XCTest or an App."""
import argparse
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reject(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Negative control unexpectedly accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--validator-root", type=Path, required=True)
    parser.add_argument("--witness-root", type=Path, required=True)
    parser.add_argument("--source-inputs", type=Path, required=True)
    parser.add_argument("--materialized", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    assert not args.receipt.exists()
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(args.root), str(args.validator_root), str(args.witness_root)]
    profile = importlib.import_module("native_core_hosted_profile")
    inputs = json.loads(args.source_inputs.read_bytes())
    began = time.monotonic()
    results = []
    def control(name, body):
        body()
        results.append({"name": name, "status": "PASS", "evidenceKind": "synthetic_control_not_Apple_execution"})

    def isolated_import():
        code = """import importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('isolated_native_core', p)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert 'run_host_tests' not in sys.modules and 'wave15_core_profile' not in sys.modules
try:
    module.require_runtime_ready({'plan': 'native-typography-hosted-only', 'readyForExecution': True}, p.parent)
except ValueError as exc:
    assert 'runtime is closed' in str(exc)
else:
    raise AssertionError('closed entrypoint accepted without the helper closure')
"""
        result = subprocess.run([sys.executable, "-I", "-S", "-c", code, str(args.root / "native_core_hosted_profile.py")],
                                capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr.decode()
    control("closed_startup_import_needs_no_unqualified_original_helper_module", isolated_import)

    def source_scope():
        with tempfile.TemporaryDirectory(prefix="native-core-source-control-") as tmp:
            root = Path(tmp)
            for suite, spec in profile.SUITES.items():
                pin = inputs[suite]
                value = Path(pin["path"]).read_bytes()
                assert sha(value) == pin["sha256"] == spec["source_sha256"]
                dest = root / spec["source_path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(value)
            counts = [profile.declared_contract(root, kind)["expected_methods"] for kind in profile.PROFILES]
            assert counts == [9, 2, 2]
            spec = profile.SUITES["AnyNativeTextTypographyTests"]
            path = root / spec["source_path"]
            path.write_bytes(path.read_bytes().replace(b"func testNativeHeadingLevels", b"func unselectedHeadingLevels", 1))
            reject(lambda: profile.declared_contract(root, "native-typography-hosted"))
    control("exact_published_source_scope_9_2_2_and_source_drift_rejected", source_scope)

    contract = profile.fixed_contract("native-typography-hosted")
    contract.update(actual_native_compiler_witnesses=[{"synthetic": True}],
                    native_compilation_proof={"synthetic": True},
                    hosted_original_source_directly_compiled=True)
    validators = profile.validators("native-typography-hosted")
    payload = {"errors": [], "values": [{
        "testPlan": "AnytypeTests",
        "enabledTests": [{"identifier": value} for value in contract["compiled_identifiers"]],
        "disabledTests": [],
    }]}
    def enumeration():
        assert profile.invocation_selectors(contract["compiled_identifiers"], contract) == [
            "AnytypeTests/AnyNativeTextTypographyTests"]
        validators.validate_enumeration(payload, contract)
        missing = copy.deepcopy(payload); missing["values"][0]["enabledTests"].pop()
        extra = copy.deepcopy(payload); extra["values"][0]["enabledTests"].append({"identifier": "AnytypeTests/AnyNativeTextTypographyTests/testUnreviewed()"})
        foreign = copy.deepcopy(payload); foreign["values"][0]["testPlan"] = "OtherTests"
        for value in (missing, extra, foreign):
            reject(lambda value=value: validators.validate_enumeration(value, contract))
    control("exact_XCTest_suite_enumeration_rejects_missing_extra_and_foreign_plan", enumeration)

    methods = contract["methods"]
    tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": method + "()",
                           "result": "Passed", "children": []} for method in methods]}
    udid = "CONTROL-ONLY-NO-SIMULATOR"
    summary = {"totalTestCount": 2, "passedTests": 2, "failedTests": 0, "skippedTests": 0,
               "devicesAndConfigurations": [{"device": {
                   "deviceId": udid, "osVersion": "27.0", "osBuildNumber": "CONTROL",
                   "architecture": "arm64", "modelName": "iPad control",
               }}]}
    def counts():
        result = validators.validate_results(summary, tree, udid)
        assert result["actual_method_count"] == result["declared_case_count"] == 2
        inflated = copy.deepcopy(summary); inflated.update(totalTestCount=16, passedTests=16)
        skipped = copy.deepcopy(summary); skipped.update(passedTests=1, skippedTests=1)
        reject(lambda: validators.validate_results(inflated, tree, udid))
        reject(lambda: validators.validate_results(skipped, tree, udid))
        repeated = copy.deepcopy(tree); repeated["testNodes"][1] = copy.deepcopy(repeated["testNodes"][0])
        reject(lambda: validators.validate_results(summary, repeated, udid))
    control("XCTest_results_reject_loop_count_inflation_skip_and_duplicate_method", counts)

    def closed():
        for plan in profile.PLANS:
            for ready in (False, True):
                reject(lambda plan=plan, ready=ready: profile.require_runtime_ready(
                    {"plan": plan, "readyForExecution": ready, "producerReceipt": {"synthetic": True}}, args.root))
    control("all_three_runtime_plans_closed_even_if_ready_flag_is_flipped", closed)

    def custody():
        inverse = json.loads((args.materialized / "source-inverse.json").read_bytes())
        for label, name in (("project", "project.pbxproj"), ("gate", "receipt_admission_native_core.py"),
                            ("host", "combined_host_acceptance_app15.py")):
            source = (args.materialized / name).read_text()
            spec = inverse[label]
            assert sha(source.encode()) == spec["candidateSHA256"]
            for change in reversed(spec["edits"]):
                assert source.count(change["after"]) == 1
                source = source.replace(change["after"], change["before"], 1)
            assert sha(source.encode()) == spec["originalSHA256"]
        source = (args.materialized / "receipt_admission_native_core.py").read_text()
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "HOSTED_PACKAGE_TEST_SOURCES" for t in n.targets))
        allowed = ast.literal_eval(node.value.args[0])
        assert len(allowed) == 7 and all(spec["source_path"] in allowed for spec in profile.SUITES.values())
        assert "Modules/Unreviewed/Tests/Extra.swift" not in allowed
        inventory = json.loads((args.materialized / "future-compiler-inputs.closed.json").read_bytes())
        assert len(inventory["selectedNativeTestSources"]) == 46 and len(inventory["selectedUITestSources"]) == 9
        assert inventory["historical43ContentHashesReused"] is False
        assert inventory["futureCompleteNativeSourceHashes"] is None and inventory["futureSourceCommit"] is None
        assert inverse["current13FileClosureChanged"] is False and inverse["currentG02ClosureChanged"] is False
    control("three_exact_inverses_and_closed_path_inventory_without_old_hash_reuse", custody)

    receipt = {
        "schema": "pinkha-native-core-portable-controls-v1",
        "status": "PASS_SYNTHETIC_CONTROL_BOUNDARIES_NOT_APP_OR_XCTEST",
        "controllerSHA256": sha(Path(__file__).read_bytes()),
        "profileSHA256": sha((args.root / "native_core_hosted_profile.py").read_bytes()),
        "sourceInputsSHA256": sha(args.source_inputs.read_bytes()),
        "materializationSHA256": sha((args.materialized / "materialization.json").read_bytes()),
        "results": results, "controlsPassed": len(results), "durationSeconds": time.monotonic() - began,
        "appleInvocations": 0, "SwiftCompilations": 0, "XCTestMethodsExecuted": 0, "nativeCalls": 0,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
