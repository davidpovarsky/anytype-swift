"""Focused collection-layout profile controls; synthetic evidence is never UIKit acceptance."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
for directory in ("Tools/Hanlin", "Tools/PinkhaSimulatorGate", "Tools/PinkhaNativeDerived",
                  "Tools/AnyEnginePort", "Tools/CurrentAppleValidation"):
    sys.path.insert(0, str(ROOT / directory))
spec = importlib.util.spec_from_file_location(
    "wave2_focus_profile", Path(__file__).with_name("focus_lifecycle_profile.py"))
focus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(focus)
ADDED = "collectionLayoutResumesOnlyCurrentUnattemptedFocus"
DEVICE = "synthetic-profile-control-not-a-simulator"


class FocusProfileControls(unittest.TestCase):
    def setUp(self):
        self.nodes = []
        for name, method in focus.METHODS.items():
            identity = focus.SUITE + "/" + name + "(" + "".join(
                parameter["name"] + ":" for parameter in method["parameters"]) + ")"
            node = dict(nodeType="Test Case", nodeIdentifier=identity, result="Passed")
            if method["argument_collections"]:
                node["children"] = [
                    dict(nodeType="Arguments", name=json.dumps(values), result="Passed")
                    for values in itertools.product(*method["argument_collections"])]
            self.nodes.append(node)
        self.tree = dict(testNodes=self.nodes)
        self.summary = dict(totalTestCount=22, passedTests=22, failedTests=0, skippedTests=0,
            devicesAndConfigurations=[dict(device=dict(deviceId=DEVICE, osVersion="27.0",
                osBuildNumber="synthetic-control", architecture="arm64", modelName="iPad synthetic control"))])
        self.identifiers = ["AnytypeTests/" + node["nodeIdentifier"] for node in self.nodes]
        self.enumeration = dict(errors=[], values=[dict(testPlan="AnytypeTests",
            enabledTests=[dict(identifier=value) for value in self.identifiers], disabledTests=[])])
        self.contract = dict(compiled_identifiers=self.identifiers)

    def test_exact_current_source_and_old_profile_rejection(self):
        source = (ROOT / focus.SOURCE_PATH).read_text()
        self.assertEqual(len(focus.validate_source(source)), 22)
        self.assertEqual(focus.METHODS[ADDED], dict(
            parameters=[dict(name="superseded", type="Bool")],
            argument_collections=[[False, True]], case_count=2))
        old = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", "379ca3568f247d2fc218ed63df24796d461713c0:" + focus.SOURCE_PATH],
            text=True)
        for invalid in (old, source + "// unreviewed source change\n"):
            with self.assertRaises(ValueError):
                focus.validate_source(invalid)

    def test_distinct_methods_and_literal_cases_are_both_required(self):
        for count in (22, 34):
            result = focus.validate_results(
                dict(self.summary, totalTestCount=count, passedTests=count), self.tree, DEVICE)
            self.assertEqual(result["actual_method_count"], 22)
            self.assertEqual(result["declared_case_count"], 34)
        missing = copy.deepcopy(self.tree)
        missing["testNodes"] = [
            node for node in missing["testNodes"] if not node["nodeIdentifier"].startswith(focus.SUITE + "/" + ADDED)]
        with self.assertRaises(ValueError):
            focus.validate_results(self.summary, missing, DEVICE)
        with self.assertRaises(ValueError):
            focus.validate_results(dict(self.summary, totalTestCount=32, passedTests=32), self.tree, DEVICE)

    def test_each_added_acquisition_and_supersession_case_cannot_be_lost(self):
        for index in range(2):
            for mutation in ("missing", "duplicate", "failed", "skipped"):
                tree = copy.deepcopy(self.tree)
                node = next(n for n in tree["testNodes"] if n["nodeIdentifier"].startswith(focus.SUITE + "/" + ADDED))
                if mutation == "missing":
                    node["children"].pop(index)
                elif mutation == "duplicate":
                    node["children"][index]["name"] = node["children"][1 - index]["name"]
                else:
                    node["children"][index]["result"] = mutation.title()
                with self.subTest(case=index, mutation=mutation), self.assertRaises(ValueError):
                    focus.validate_results(self.summary, tree, DEVICE)

    def test_compiled_selection_is_exact(self):
        result = focus.validate_enumeration(self.enumeration, self.contract)
        self.assertEqual(len(result["identifiers"]), 22)
        for mutation in ("missing", "foreign", "duplicate", "disabled"):
            value = copy.deepcopy(self.enumeration)
            selected = value["values"][0]["enabledTests"]
            if mutation == "missing":
                selected.pop()
            elif mutation == "foreign":
                selected[-1]["identifier"] = "AnytypeTests/ForeignSuite/claimedPass()"
            elif mutation == "duplicate":
                selected[-1] = copy.deepcopy(selected[0])
            else:
                value["values"][0]["disabledTests"] = [copy.deepcopy(selected[-1])]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                focus.validate_enumeration(value, self.contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
