"""Portable qualification controls using synthetic compiler/XCTest payloads.

No Swift compiler, Xcode, application or simulator is invoked. These controls
check that the profile rejects incomplete or mismatched evidence. They are
not native test, product, UI or acceptance results.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import rtl_hosted_profile as profile


SOURCE = Path(os.environ.get("PINKHA_RTL_CONTROL_SOURCE", Path(__file__).resolve().parents[4]))
SYNTHETIC_COMMIT = "a" * 40
SYNTHETIC_UDID = "SYNTHETIC-PORTABLE-CONTROL-NO-DEVICE"


class RTLHostedProfileControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pinkha-rtl-schema-control-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        paths = set(profile.PRODUCT_SOURCES)
        paths.update(spec["source_path"] for spec in profile.SUITES.values())
        for relative in paths:
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, destination)
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        self.declared = profile.declared_contract(self.source)
        rows = [{"repositoryPath": spec["source_path"],
                 "compiledPath": str(self.source / spec["source_path"]),
                 "sha256": spec["source_sha256"],
                 "bytes": (self.source / spec["source_path"]).stat().st_size}
                for spec in profile.SUITES.values()]
        self.filelist = self.root / "retained.SwiftFileList"
        self.filelist.write_text("".join('"' + row["compiledPath"] + '"\n' for row in rows))
        original = self.root / "Build/Intermediates.noindex/Anytype.build/AnytypeTests.build/AnytypeTests.SwiftFileList"
        # A string fixture only. This compiler command is NEVER executed.
        line = '/synthetic/swiftc -module-name AnytypeTests @"' + str(original) + '"'
        self.log = self.root / "synthetic-not-a-build.log"
        self.log.write_text("SYNTHETIC PORTABLE SCHEMA CONTROL\n" + line + "\n")
        witness = {"lineNumber": 2, "lineSHA256": profile.sha(line.encode()), "moduleName": profile.TARGET}
        self.proof = {
            "schema": "pinkha-exact-native-compiler-inputs-v1",
            "status": "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION",
            "sourceCommit": SYNTHETIC_COMMIT, "requiredSources": rows,
            "buildLog": self.pin(self.log), "testsExecuted": 0,
            "actualCompilerFileLists": [dict(self.pin(self.filelist), originalPath=str(original),
                requiredSourcePaths=[row["compiledPath"] for row in rows],
                compilerInvocation=witness, compilerInvocations=[witness])],
        }
        self.proof_path = self.root / "synthetic-compiler-proof.json"

    def pin(self, path):
        return {"path": str(path), "sha256": profile.sha(path.read_bytes())}

    def contract(self, proof=None):
        self.proof_path.write_text(json.dumps(self.proof if proof is None else proof))
        return profile.source_contract(self.source, source_commit=SYNTHETIC_COMMIT,
                                       native_compilation_proof=self.pin(self.proof_path))

    def test_exact_source_and_compiler_selection(self):
        selected = self.contract()
        self.assertEqual(selected["expected_methods"], 6)
        self.assertEqual(selected["declared_cases"], 10)
        self.assertEqual(selected["tests_executed"], 0)
        self.assertEqual(len(selected["actual_native_compiler_witnesses"]), 1)
        relative = next(iter(profile.SUITES.values()))["source_path"]
        path = self.source / relative
        path.write_text(path.read_text().replace("[1, 20]", "[1, 21]"))
        with self.assertRaisesRegex(ValueError, "Reviewed RTL source changed"):
            self.contract()

    def test_missing_or_foreign_compiler_evidence_fails(self):
        missing = copy.deepcopy(self.proof)
        missing["requiredSources"].pop()
        foreign = copy.deepcopy(self.proof)
        foreign["actualCompilerFileLists"][0]["originalPath"] = str(self.root / "PinkhaAnyUITests.build/tests.SwiftFileList")
        invented = copy.deepcopy(self.proof)
        invented["actualCompilerFileLists"][0]["compilerInvocations"][0]["lineSHA256"] = "0" * 64
        wrong_source = copy.deepcopy(self.proof)
        wrong_source["sourceCommit"] = "b" * 40
        for name, value in (("missing test", missing), ("package target", foreign),
                            ("invented compiler witness", invented), ("different source", wrong_source)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.contract(value)
        self.filelist.write_text(self.filelist.read_text().splitlines()[0] + "\n")
        omitted = copy.deepcopy(self.proof)
        omitted["actualCompilerFileLists"][0].update(self.pin(self.filelist))
        with self.assertRaisesRegex(ValueError, "missing or duplicated"):
            self.contract(omitted)

    def enumeration(self):
        return {"errors": [], "values": [{"testPlan": profile.TARGET,
            "enabledTests": [{"identifier": value} for value in self.declared["compiled_identifiers"]],
            "disabledTests": []}]}

    def test_exact_enumeration_rejects_partial_extra_or_disabled_cases(self):
        value = self.enumeration()
        contract = self.contract()
        self.assertEqual(profile.invocation_selectors(contract["compiled_identifiers"], contract),
                         [profile.TARGET + "/" + suite for suite in sorted(profile.SUITES)])
        with self.assertRaises(ValueError):
            profile.invocation_selectors(contract["compiled_identifiers"], self.declared)
        with self.assertRaises(ValueError):
            profile.invocation_selectors(contract["compiled_identifiers"][:-1], contract)
        result = profile.validate_enumeration(value, contract)
        self.assertEqual(len(result["identifiers"]), 6)
        self.assertEqual(result["tests_executed"], 0)
        missing, extra, disabled = (copy.deepcopy(value) for _ in range(3))
        missing["values"][0]["enabledTests"].pop()
        extra["values"][0]["enabledTests"].append({"identifier": "AnytypeTests/OtherSuite/testUnexpected()"})
        disabled["values"][0]["disabledTests"] = [disabled["values"][0]["enabledTests"][0]]
        for name, payload in (("missing", missing), ("extra", extra), ("disabled", disabled)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                profile.validate_enumeration(payload, self.declared)

    def result_fixture(self):
        nodes = []
        for suite, spec in profile.SUITES.items():
            for method, definition in spec["methods"].items():
                signature = "(" + "".join(item["name"] + ":" for item in definition["parameters"]) + ")"
                children = [{"nodeType": "Arguments", "name": "synthetic case " + str(value), "result": "Passed"}
                            for value in definition["argument_collections"][0]] if definition["argument_collections"] else []
                nodes.append({"nodeType": "Test Case", "nodeIdentifier": "AnytypeTests/" + suite + "/" + method + signature,
                              "result": "Passed", "children": children})
        summary = {"totalTestCount": 10, "passedTests": 10, "failedTests": 0, "skippedTests": 0,
                   "devicesAndConfigurations": [{"device": {"deviceId": SYNTHETIC_UDID,
                   "osVersion": "27.0", "osBuildNumber": "SYNTHETIC", "architecture": "arm64",
                   "modelName": "iPad synthetic control", "platform": "iOS Simulator"}}]}
        return summary, {"testNodes": nodes}

    def test_results_require_all_named_methods_and_distinct_literal_cases(self):
        summary, tree = self.result_fixture()
        result = profile.validate_results(summary, tree, SYNTHETIC_UDID)
        self.assertEqual(result["actual_method_count"], 6)
        self.assertEqual(result["declared_case_count"], 10)
        incomplete = copy.deepcopy(tree)
        incomplete["testNodes"][0]["children"].pop()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate actual core argument cases"):
            profile.validate_results(summary, incomplete, SYNTHETIC_UDID)
        unexpected = copy.deepcopy(tree)
        unexpected["testNodes"][0]["nodeIdentifier"] = "AnytypeTests/Unexpected/test()"
        with self.assertRaises(ValueError):
            profile.validate_results(summary, unexpected, SYNTHETIC_UDID)
        wrong_device = copy.deepcopy(summary)
        wrong_device["devicesAndConfigurations"][0]["device"]["modelName"] = "iPhone synthetic control"
        with self.assertRaises(ValueError):
            profile.validate_results(wrong_device, tree, SYNTHETIC_UDID)


if __name__ == "__main__":
    unittest.main()
