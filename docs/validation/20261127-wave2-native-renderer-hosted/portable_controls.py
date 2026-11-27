#!/usr/bin/env python3
"""Affected Renderer3 controls only. Synthetic records are not XCTest results."""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import time
import traceback
from unittest import mock


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reject(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Negative control unexpectedly accepted")


def definitions(text):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materialized", type=Path, required=True)
    parser.add_argument("--core-input", type=Path, required=True)
    parser.add_argument("--validator-root", type=Path, required=True)
    parser.add_argument("--renderer-source", type=Path, required=True)
    parser.add_argument("--typography-source", type=Path, required=True)
    parser.add_argument("--original-core-controls", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    assert not args.receipt.exists()
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(args.materialized.resolve()), str(args.validator_root.resolve())]
    profile = importlib.import_module("native_core_hosted_profile")
    original_controls = json.loads(args.original_core_controls.read_bytes())
    assert original_controls["controlsPassed"] == 6
    assert original_controls["profileSHA256"] == "b3dc895536c615c453f2856cd33c29b1394a6e954c218e4e7c67b59dfdb211ee"
    began = time.monotonic()
    results = []

    def control(name, body):
        started = time.monotonic()
        try:
            detail = body()
            results.append({"name": name, "status": "PASS", "details": detail,
                            "seconds": time.monotonic() - started})
        except Exception:
            results.append({"name": name, "status": "FAIL", "traceback": traceback.format_exc(),
                            "seconds": time.monotonic() - started})

    def exact_signatures_and_drift():
        with tempfile.TemporaryDirectory(prefix="renderer3-source-control-") as tmp:
            root = Path(tmp)
            for suite, source in (("AnyNativeTextRendererTests", args.renderer_source),
                                  ("AnyNativeTextTypographyTests", args.typography_source)):
                spec = profile.SUITES[suite]
                data = source.read_bytes()
                assert sha(data) == spec["source_sha256"]
                target = root / spec["source_path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            renderer = profile.declared_contract(root, "native-renderer-hosted")
            typography = profile.declared_contract(root, "native-typography-hosted")
            assert renderer["expected_methods"] == renderer["declared_cases"] == 3
            assert typography["expected_methods"] == typography["declared_cases"] == 2
            spec = profile.SUITES["AnyNativeTextRendererTests"]
            target = root / spec["source_path"]
            original = target.read_bytes()
            changes = [
                original.replace(b"func testEqualNativeText", b"func unselectedEqualNativeText", 1),
                original.replace(b"() {", b"() throws {", 1),
                original.replace(b"final class AnyNativeTextRendererTests", b"final class OtherRendererTests", 1),
                original.replace(b"\n}\n#endif", b"\n    func testUnreviewed() {}\n}\n#endif", 1),
            ]
            assert all(value != original for value in changes)
            for changed in changes:
                target.write_bytes(changed)
                reject(lambda: profile.declared_contract(root, "native-renderer-hosted"))
            return {"actualSourcesParsed": ["Renderer3 non-throwing", "Typography2 throwing"],
                    "sourceDriftsRejected": len(changes), "XCTestInvocations": 0}
    control("two_fixed_XCTest_signatures_and_exact_renderer_source_drift", exact_signatures_and_drift)

    contract = profile.fixed_contract("native-renderer-hosted")
    contract.update(actual_native_compiler_witnesses=[{"syntheticControlOnly": True}],
                    native_compilation_proof={"syntheticControlOnly": True},
                    hosted_original_source_directly_compiled=True)
    validators = profile.validators("native-renderer-hosted")
    payload = {"errors": [], "values": [{
        "testPlan": "AnytypeTests", "enabledTests": [{"identifier": item} for item in contract["compiled_identifiers"]],
        "disabledTests": [],
    }]}

    def exact_enumeration():
        assert profile.invocation_selectors(contract["compiled_identifiers"], contract) == ["AnytypeTests/AnyNativeTextRendererTests"]
        actual = validators.validate_enumeration(payload, contract)
        assert len(actual["identifiers"]) == 3 and actual["tests_executed"] == 0
        missing = copy.deepcopy(payload); missing["values"][0]["enabledTests"].pop()
        extra = copy.deepcopy(payload); extra["values"][0]["enabledTests"].append({"identifier": "AnytypeTests/AnyNativeTextRendererTests/testExtra()"})
        disabled = copy.deepcopy(payload); disabled["values"][0]["disabledTests"].append(disabled["values"][0]["enabledTests"][0])
        foreign = copy.deepcopy(payload); foreign["values"][0]["testPlan"] = "OtherTests"
        for changed in (missing, extra, disabled, foreign):
            reject(lambda changed=changed: validators.validate_enumeration(changed, contract))
        no_proof = dict(contract, actual_native_compiler_witnesses=[])
        reject(lambda: profile.invocation_selectors(no_proof["compiled_identifiers"], no_proof))
        return {"syntheticExactMethods": 3, "negativeControls": 5, "actualCompilerProofValidated": False}
    control("original_enumeration_validator_on_new_exact_three_method_scope", exact_enumeration)

    tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": method + "()", "result": "Passed", "children": []}
                           for method in contract["methods"]]}
    udid = "SYNTHETIC-RENDERER-CONTROL-NO-DEVICE"
    summary = {"totalTestCount": 3, "passedTests": 3, "failedTests": 0, "skippedTests": 0,
               "devicesAndConfigurations": [{"device": {"deviceId": udid, "osVersion": "27.0", "osBuildNumber": "CONTROL",
                                                          "architecture": "arm64", "modelName": "iPad control"}}]}

    def exact_results():
        actual = validators.validate_results(summary, tree, udid)
        assert actual["actual_method_count"] == actual["declared_case_count"] == 3
        inflated = copy.deepcopy(summary); inflated.update(totalTestCount=16, passedTests=16)
        skipped = copy.deepcopy(summary); skipped.update(passedTests=2, skippedTests=1)
        repeated = copy.deepcopy(tree); repeated["testNodes"][1] = copy.deepcopy(repeated["testNodes"][0])
        incomplete = copy.deepcopy(tree); incomplete["testNodes"].pop()
        reject(lambda: validators.validate_results(inflated, tree, udid))
        reject(lambda: validators.validate_results(skipped, tree, udid))
        reject(lambda: validators.validate_results(summary, repeated, udid))
        reject(lambda: validators.validate_results(summary, incomplete, udid))
        return {"syntheticCaseCount": 3, "negativeControls": 4, "actualXCTestMethods": 0}
    control("original_results_validator_rejects_extra_skip_duplicate_and_missing", exact_results)

    def source_inverse_and_closed_boundary():
        inverse = json.loads((args.materialized / "source-inverse.json").read_bytes())
        for name, entry in inverse["files"].items():
            original = (args.core_input / name).read_text()
            candidate = (args.materialized / name).read_text()
            assert sha(original.encode()) == entry["originalSHA256"]
            assert sha(candidate.encode()) == entry["candidateSHA256"]
            restored = candidate
            for change in reversed(entry["edits"]):
                assert restored.count(change["after"]) == 1
                restored = restored.replace(change["after"], change["before"], 1)
            assert restored == original
        host_name = "combined_host_acceptance_app15.py"
        assert definitions((args.core_input / host_name).read_text()) == definitions((args.materialized / host_name).read_text())
        profile_name = "native_core_hosted_profile.py"
        old = definitions((args.core_input / profile_name).read_text())
        new = definitions((args.materialized / profile_name).read_text())
        for name in ("source_contract", "invocation_selectors", "OriginalValidators", "run_hosted"):
            assert old[name] == new[name]
        closed = json.loads((args.materialized / "native-core-closed-profile.json").read_bytes())
        assert closed["nativeMethods"] == closed["nativeDeclaredCases"] == 16
        assert closed["readyForExecution"] is False and closed["runtimeAccepted"] is False
        assert all(closed[key] is None for key in ("futureSourceCommit", "actualProducerReceipt", "actualSharedAdmission"))
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("Closed runtime read an external input")), \
             mock.patch.object(Path, "write_bytes", side_effect=AssertionError("Closed runtime wrote a product")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("Closed runtime launched a process")):
            for ready in (False, True):
                reject(lambda ready=ready: profile.require_runtime_ready(
                    {"plan": "native-renderer-hosted-only", "readyForExecution": ready}, args.materialized))
        return {"completeInverses": 3, "originalFDefinitionsUnchanged": True,
                "originalWitnessStageLifecycleValidatorsUnchanged": True,
                "closedEvenWithReadyFlag": True, "futureProductsAdmitted": 0}
    control("three_exact_inverses_and_new_lane_closed_before_external_IO", source_inverse_and_closed_boundary)

    passed = sum(row["status"] == "PASS" for row in results)
    receipt = {
        "schema": "pinkha-renderer3-affected-portable-controls-v1",
        "status": "PASS_SYNTHETIC_CONTROLS_ONLY" if passed == len(results) else "FAIL_SYNTHETIC_CONTROLS",
        "controllerSHA256": sha(Path(__file__).read_bytes()),
        "profileSHA256": sha((args.materialized / "native_core_hosted_profile.py").read_bytes()),
        "materializationSHA256": sha((args.materialized / "materialization.json").read_bytes()),
        "originalCore13ControlsSHA256": sha(args.original_core_controls.read_bytes()),
        "originalSixCoreControlsReusedWithoutRerun": True,
        "validatorSources": {name: sha((args.validator_root / name).read_bytes())
                             for name in ("wave15_core_profile.py", "run_host_tests.py", "shared_editor_existing_build.py")},
        "results": results, "controlsPassed": passed, "controlsTotal": len(results),
        "durationSeconds": time.monotonic() - began,
        "appleInvocations": 0, "nativeCalls": 0, "SwiftCompilations": 0, "XCTestMethodsExecuted": 0,
    }
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
