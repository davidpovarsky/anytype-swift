"""Bounded pure-source and false-PASS controls; never Apple/native acceptance."""
import argparse
import ast
import copy
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import combined_host_acceptance as f


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    helpers = f.load_helpers(args.helpers)
    import combined_t5_pending as pending
    import combined_t5_retry as retry
    import combined_t5_freshness as fresh
    s, results = f.shared, []

    def rejects(call):
        try:
            call()
        except (ValueError, RuntimeError, KeyError):
            return
        raise AssertionError("Expected strict rejection")

    original = subprocess.check_output(["git", "-C", str(args.repository), "show",
        "2e0bf98a1d3b0c4c9db84d311b65859220b18a39:Tools/CurrentAppleValidation/combined_heart_semantics/combined_heart_semantics.py"]).decode()
    assert s.sha(original.encode()) == "b1c26e13925318446e1574e90ca296913c8733afcc5106924dbc9630191bc0ba"

    class Aliases(ast.NodeTransformer):
        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == "args" and node.attr == "root":
                return ast.Name(id="root", ctx=node.ctx)
            return self.generic_visit(node)

        def visit_Subscript(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == "binding" and isinstance(node.slice, ast.Constant) and node.slice.value == "sourceSHA":
                return ast.parse('admission["sourceCommit"]').body[0].value
            return self.generic_visit(node)

        def visit_Assign(self, node):
            if (len(node.targets) == 1 and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == "result"
                    and isinstance(node.targets[0].slice, ast.Constant) and node.targets[0].slice.value == "sourceAdmission"):
                node.targets[0] = ast.Name(id="source_proof", ctx=ast.Store())
            return self.generic_visit(node)

    old = Aliases().visit(ast.parse(original))
    new = ast.parse(Path(s.__file__).read_text())
    old_main = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    helper = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == "admit_and_clone_products")
    candidates = [ast.dump(n, include_attributes=False) for n in ast.walk(old_main)]
    for node in helper.body[3:-1]:
        assert ast.dump(node, include_attributes=False) in candidates, ast.unparse(node)
    results.append({"name": "original-source-product-admission-preserved", "status": "PASS",
                    "statements": len(helper.body[3:-1]),
                    "explicitAliases": ["args.root -> root", "binding.sourceSHA -> admission.sourceCommit", "result.sourceAdmission -> source_proof"]})

    selected = ["AnytypeTests/A/first()", "AnytypeTests/A/second(value:)"]
    enumeration = {"errors": [], "values": [{"testPlan": "AnytypeTests",
        "enabledTests": [{"identifier": n} for n in selected], "disabledTests": []}]}
    f.exact_enumeration(enumeration, selected)
    mutations = [lambda x: x["values"][0].update(enabledTests=[]),
        lambda x: x["values"][0]["enabledTests"].append(x["values"][0]["enabledTests"][0]),
        lambda x: x["values"][0]["disabledTests"].append({"identifier": selected[0]}),
        lambda x: x["values"][0]["enabledTests"].__setitem__(0, {"identifier": "AnytypeTests/Foreign/test()"}),
        lambda x: x.update(errors=["native error"])]
    for mutate in mutations:
        bad = copy.deepcopy(enumeration); mutate(bad)
        rejects(lambda: f.exact_enumeration(bad, selected))
    results.append({"name": "reject-empty-duplicate-disabled-foreign-errored-enumeration", "status": "PASS", "negativeCases": 5})

    for value in ("r15-attachment-v1", "r15-attachment-authorized-current-read-v1", "dual-engine-runtime-v2", None):
        rejects(lambda: pending.expected_runtime_version(value))
    assert pending.expected_runtime_version("dual-engine-runtime-v1") == s.VERSION
    rejects(lambda: retry.validate_combined_receipt({"runtimeVersion": s.VERSION}, {}, b"{}", pending_only=False, runtime_profile=pending.RUNTIME_PROFILE))
    rejects(lambda: retry.validate_combined_receipt({"runtimeVersion": "old"}, {}, b"{}", pending_only=True, runtime_profile=pending.RUNTIME_PROFILE))
    rejects(lambda: fresh.validate_combined_receipt({}, runtime="old"))
    results.append({"name": "reject-old-or-unbound-combined-profile", "status": "PASS", "negativeCases": 7})

    class Missing:
        def run(self, *args, **kw):
            return Path("/does-not-exist"), {"exitCode": 1}
    with tempfile.TemporaryDirectory() as temporary:
        rejects(lambda: s.preserve_final_sandbox(Missing(), "00000000-0000-0000-0000-000000000000",
                                                Path(temporary) / "private", application_invoked=True))
    results.append({"name": "missing-original-sandbox-after-app-run-fails", "status": "PASS"})

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve(); app = root / "Debug-Anytype-iphonesimulator/Anytype.app"
        (app / "PlugIns/AnytypeTests.xctest").mkdir(parents=True)
        target = {"BlueprintName": "AnytypeTests", "TestHostPath": "__TESTROOT__/Debug-Anytype-iphonesimulator/Anytype.app",
                  "TestBundlePath": "__TESTHOST__/PlugIns/AnytypeTests.xctest", "EnvironmentVariables": {}, "TestingEnvironmentVariables": {}}
        original = {"__xctestrun_metadata__": {"FormatVersion": 2}, "TestConfigurations": [
            {"TestTargets": [{"BlueprintName": "DeepLinksTests"}, target, {"BlueprintName": "AnytypeCoreTests"}]}]}
        descriptor = root / "Original.xctestrun"; descriptor.write_bytes(plistlib.dumps(original))
        built = {"products": root, "descriptor": descriptor, "originalSelection": []}
        scoped, proof = f.scoped_descriptor(built, app, selected, {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"})
        assert plistlib.loads(scoped)["TestConfigurations"][0]["TestTargets"][0]["OnlyTestIdentifiers"] == ["A/first()", "A/second(value:)"]
        assert plistlib.loads(descriptor.read_bytes()) == original and proof["exactInverse"]
        for key, value in (("SkipTestIdentifiers", ["A/first()"]), ("EnvironmentVariables", {"PINKHA_STALE": "1"})):
            bad = copy.deepcopy(original); bad["TestConfigurations"][0]["TestTargets"][1][key] = value
            descriptor.write_bytes(plistlib.dumps(bad))
            rejects(lambda: f.scoped_descriptor(built, app, selected, {}))
    results.append({"name": "original-three-target-descriptor-exact-inverse-and-rejection", "status": "PASS", "negativeCases": 2})

    summary = {"passedTests": 1, "failedTests": 0, "skippedTests": 0, "totalTestCount": 1,
               "devicesAndConfigurations": [{"device": {"deviceId": "device", "architecture": "arm64", "osVersion": "27.0"}}]}
    validator = helpers["t5_native_ui_evidence"].validate_selection
    validator(summary, {"A/first()": "Passed"}, ["A/first"], "device")
    for bad, methods in ((dict(summary, passedTests=0), {"A/first()": "Passed"}),
                         (dict(summary, skippedTests=1), {"A/first()": "Passed"}),
                         (summary, {"A/foreign()": "Passed"}),
                         (summary, {"A/first()": "Failed"})):
        rejects(lambda: validator(bad, methods, ["A/first"], "device"))
    results.append({"name": "original-result-authority-rejects-zero-skip-foreign-failure", "status": "PASS", "negativeCases": 4})
    receipt = {"status": "PASS_SOURCE_AND_COLLECTOR_CONTROLS_NOT_APPLE_ACCEPTANCE", "controls": results,
               "AppleTestsExecuted": 0, "nativeCalls": 0, "old139GatesChanged": False,
               "controllerSHA256": s.digest(Path(f.__file__)), "sharedControllerSHA256": s.digest(Path(s.__file__))}
    s.write(args.output, receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
