"""Source/evidence rejection controls, not Apple component acceptance."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import unittest

import wave15_core_profile as core
from run_host_tests import HostTestProfile, validate_results


class CoreScopeGateTests(unittest.TestCase):
    def setUp(self):
        self.specs = core.load_manifest()
        self.expected = {suite + "/" + name for suite, spec in self.specs.items()
                         for name in spec["methods"]}
        self.nodes = []
        for suite, spec in self.specs.items():
            for name, method in spec["methods"].items():
                identity = suite + "/" + name + "(" + "".join(
                    parameter["name"] + ":" for parameter in method["parameters"]) + ")"
                node = dict(nodeType="Test Case", nodeIdentifier=identity, result="Passed")
                if method["argument_collections"]:
                    node["children"] = [
                        dict(nodeType="Arguments", name=json.dumps(values, ensure_ascii=True), result="Passed")
                        for values in product(*method["argument_collections"])]
                self.nodes.append(node)
        self.tree = dict(testNodes=self.nodes)
        self.summary = dict(totalTestCount=41, passedTests=41, failedTests=0, skippedTests=0,
            devicesAndConfigurations=[dict(device=dict(deviceId="core-disposable", osVersion="27.0",
                osBuildNumber="24A-control", architecture="arm64", modelName="iPad (A16)"))])

    def validate(self, tree=None, summary=None):
        return validate_results(summary or self.summary, tree or self.tree, self.expected,
                                "core-disposable", HostTestProfile.CORE)

    def test_actual_distinct_cases_required_independently_of_summary_unit(self):
        for total in (41, 57):
            value = self.validate(summary=dict(self.summary, totalTestCount=total, passedTests=total))
            self.assertEqual(value["actual_method_count"], 41)
            self.assertEqual(value["declared_case_count"], 57)
        self.assertEqual(HostTestProfile.CORE.pass_status, "WAVE15_CORE_COMPONENT_PASS")
        self.assertEqual(HostTestProfile.CORE.result_prefix, "wave15-core")

    def test_missing_method_or_foreign_identity_cannot_hide_in_a_passing_total(self):
        tree = deepcopy(self.tree)
        tree["testNodes"].pop()
        with self.assertRaises(ValueError):
            self.validate(tree=tree)
        tree = deepcopy(self.tree)
        tree["testNodes"][0]["nodeIdentifier"] = "ForeignTests/claimedPass()"
        with self.assertRaises(ValueError):
            self.validate(tree=tree)

    def test_missing_duplicate_failed_and_skipped_arguments_are_rejected(self):
        for mutation in ("missing", "duplicate", "failed", "skipped"):
            tree = deepcopy(self.tree)
            node = next(node for node in tree["testNodes"] if node.get("children"))
            if mutation == "missing":
                node["children"].pop()
            elif mutation == "duplicate":
                node["children"][1]["name"] = node["children"][0]["name"]
            else:
                node["children"][0]["result"] = "Failed" if mutation == "failed" else "Skipped"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.validate(tree=tree)

    def test_unknown_argument_schema_requires_raw_evidence_review(self):
        tree = deepcopy(self.tree)
        node = next(node for node in tree["testNodes"] if node.get("children"))
        node["children"][0]["nodeType"] = "UnrecognizedResult"
        with self.assertRaises(core.CoreEvidenceReviewPending):
            self.validate(tree=tree)
        node["children"][0]["nodeType"] = "Arguments"
        del node["children"][0]["name"]
        with self.assertRaises(core.CoreEvidenceReviewPending):
            self.validate(tree=tree)

    def test_changed_source_or_literal_matrix_requires_explicit_inventory_review(self):
        source = '@Test("literal combinations", arguments: [false, true], ["first", "second"])\n' \
                 'func sample(flag: Bool, text: String) throws {}\n'
        spec = dict(source_lf_sha256=core.source_digest(source), methods=core.inspect_declarations(source))
        self.assertEqual(spec["methods"]["sample"]["case_count"], 4)
        self.assertEqual(core.validate_source(source.replace("\n", "\r\n"), spec), {"sample"})
        for changed in (source.replace('"second"', '"third"'), source + "// changed test body source\n"):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                core.validate_source(changed, spec)
        for changed in (source.replace('[false, true]', '[false, false]'),
                        source.replace('[false, true]', 'dynamicValues')):
            with self.subTest(changed=changed), self.assertRaises((ValueError, json.JSONDecodeError)):
                core.inspect_declarations(changed)

    def test_wrong_summary_unit_and_unknown_selection_are_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(summary=dict(self.summary, totalTestCount=58, passedTests=58))
        with self.assertRaises(ValueError):
            core.validate_arguments(self.tree, {"OtherSuite/method"})

    def test_nonparameterized_method_cannot_gain_unreported_argument_execution(self):
        tree = deepcopy(self.tree)
        node = next(node for node in tree["testNodes"] if not node.get("children"))
        node["children"] = [dict(nodeType="Arguments", name="extra", result="Passed")]
        with self.assertRaises(ValueError):
            self.validate(tree=tree)


if __name__ == "__main__":
    unittest.main()
