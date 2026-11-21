"""Controller controls only; synthetic xcresult nodes never certify Apple tests."""
import copy
from pathlib import Path
import unittest

import t5_host_actions as gate

APP = Path(__file__).resolve().parents[2]
UDID = "12345678-1234-1234-1234-123456789abc"


def tree():
    values = []
    for name, specification in gate.METHODS.items():
        signature = "(" + "".join(p["name"] + ":" for p in specification["parameters"]) + ")"
        node = dict(nodeType="Test Case", nodeIdentifier="AnytypeTests/" + gate.SUITE + "/" + name + signature,
                    result="Passed", children=[])
        if specification["case_count"] == 2:
            node["children"] = [dict(nodeType="Arguments", name="isNote: " + value,
                                     result="Passed", children=[]) for value in ("false", "true")]
        values.append(node)
    return values


def summary(total=11):
    return dict(totalTestCount=total, passedTests=total, failedTests=0, skippedTests=0,
                devicesAndConfigurations=[dict(device=dict(deviceId=UDID, osVersion="27.0",
                    osBuildNumber="24Afixture", architecture="arm64", modelName="iPad Pro"))])


class T5HostActionControls(unittest.TestCase):
    def test_actual_tracked_source_has_exact_pending_inventory(self):
        value = gate.source_contract(APP)
        self.assertEqual(value["expected_methods"], 11)
        self.assertEqual(value["declared_cases"], 12)
        self.assertEqual(len(value["compiled_identifiers"]), 11)
        self.assertIn("AnytypeTests/" + gate.SUITE
            + "/lateUnlinkFailureIsIgnoredAfterDocumentLifetimeEnds(isNote:)", value["compiled_identifiers"])

    def test_source_rejects_new_missing_or_changed_argument_cases(self):
        source = (APP / gate.SOURCE_PATH).read_text(encoding="utf-8")
        changes = [source + "\n@Test func unreviewedExtra() {}\n",
                   source.replace("@Test(\"Unlink removes only the selected canonical source\")", ""),
                   source.replace("arguments: [false, true]", "arguments: [false]")]
        for changed in changes:
            with self.subTest(source=changed[-50:]), self.assertRaises(ValueError):
                gate.validate_source(changed)

    def test_named_results_accept_both_summary_forms_but_require_actual_argument_nodes(self):
        for total in (11, 12):
            with self.subTest(total=total):
                value = gate.validate_results(summary(total), tree(), UDID)
                self.assertEqual(value["actual_method_count"], 11)
                self.assertEqual(value["declared_case_count"], 12)

    def test_aggregate_cannot_hide_missing_duplicate_or_failed_argument(self):
        for mode in ("missing", "duplicate", "failed"):
            actual = tree()
            arguments = next(node["children"] for node in actual if node["children"])
            if mode == "missing": arguments.pop()
            elif mode == "duplicate": arguments[1] = copy.deepcopy(arguments[0])
            else: arguments[1]["result"] = "Failed"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                gate.validate_results(summary(12), actual, UDID)

    def test_results_reject_extra_missing_skipped_or_foreign_destination(self):
        scenarios = [(summary(12), tree()[:-1], UDID),
                     (summary(13), tree(), UDID),
                     (dict(summary(), passedTests=10, skippedTests=1), tree(), UDID),
                     (summary(), tree(), "foreign")]
        extra = tree()
        extra.append(dict(nodeType="Test Case", nodeIdentifier="AnytypeTests/OtherSuite/oldPassed()", result="Passed"))
        scenarios.append((summary(12), extra, UDID))
        for counts, actual, udid in scenarios:
            with self.subTest(counts=counts, udid=udid), self.assertRaises(ValueError):
                gate.validate_results(counts, actual, udid)

    def test_enumeration_requires_exact_pending_suite_before_execution(self):
        contract = gate.source_contract(APP)
        payload = dict(errors=[], values=[dict(testPlan="Anytype", enabledTests=[dict(identifier=value)
            for value in contract["compiled_identifiers"]], disabledTests=[])])
        self.assertEqual(len(gate.validate_enumeration(payload, contract)["identifiers"]), 11)
        changes = [lambda v: v["values"][0]["enabledTests"].pop(),
                   lambda v: v["values"][0]["enabledTests"].append(dict(identifier="AnytypeTests/Other/oldPassed()")),
                   lambda v: v["values"][0]["disabledTests"].append(v["values"][0]["enabledTests"][0]),
                   lambda v: v["errors"].append("failed discovery")]
        for change in changes:
            changed = copy.deepcopy(payload)
            change(changed)
            with self.subTest(payload=changed), self.assertRaises(ValueError):
                gate.validate_enumeration(changed, contract)


if __name__ == "__main__":
    unittest.main()
