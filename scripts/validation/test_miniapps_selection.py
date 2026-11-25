#!/usr/bin/env python3
"""Pure MiniApps selector controls, including the authenticated original descriptors.

These checks do not execute the app and are not native acceptance evidence.
"""
from pathlib import Path
import copy
import json
import plistlib
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/MiniApps"))
from acceptance_profile import PREPARE, VERIFY, ADAPTER, UI_RETURN, UI_REPLAY, METHODS
from selection import TARGET_METHODS, configure_tests, selector, validate_enumeration

ORIGINALS = ROOT / "docs/validation/20261125-miniapps-final"


class MiniAppsSelectionTests(unittest.TestCase):
    def test_original_native_descriptor_scopes_all_three_real_swift_methods(self):
        original = ORIGINALS / "Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun"
        raw = original.read_bytes()
        original_target = next(x for x in plistlib.loads(raw)["TestConfigurations"][0]["TestTargets"]
                               if x["BlueprintName"] == "AnytypeTests")
        with tempfile.TemporaryDirectory() as tmp:
            for method in (PREPARE, VERIFY, ADAPTER):
                with self.subTest(method=method):
                    destination = configure_tests(original, Path(tmp) / "scoped.xctestrun",
                        {"PINKHA_MINIAPPS_NATIVE_TESTING": "1"}, "AnytypeTests", method)
                    targets = plistlib.loads(destination.read_bytes())["TestConfigurations"][0]["TestTargets"]
                    self.assertEqual(len(targets), 1)
                    target = targets[0]
                    self.assertEqual(target["OnlyTestIdentifiers"], [method + "()"])
                    self.assertEqual(selector("AnytypeTests", method), method + "()")
                    self.assertEqual(target.get("SkipTestIdentifiers"), original_target.get("SkipTestIdentifiers"))
                    self.assertEqual(target["TestBundlePath"], original_target["TestBundlePath"]
                                     .replace("__TESTROOT__", str(original.parent)))
                    self.assertEqual(target["TestHostPath"], original_target["TestHostPath"]
                                     .replace("__TESTROOT__", str(original.parent)))
                    self.assertEqual(original.read_bytes(), raw)

    def test_original_ui_descriptor_preserves_both_xctest_selectors(self):
        original = ORIGINALS / "PinkhaStage1Acceptance_iphonesimulator27.0-arm64.xctestrun"
        raw = original.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            for method in (UI_RETURN, UI_REPLAY):
                destination = configure_tests(original, Path(tmp) / "scoped.xctestrun",
                                              {}, "PinkhaStage1AcceptanceUITests", method)
                data = plistlib.loads(destination.read_bytes())
                target = data["PinkhaStage1AcceptanceUITests"]
                self.assertTrue(target["IsUITestBundle"])
                self.assertEqual(target["OnlyTestIdentifiers"], [method])
                self.assertEqual(selector("PinkhaStage1AcceptanceUITests", method), method)
                self.assertEqual(original.read_bytes(), raw)

    def test_only_the_original_five_methods_are_allowed(self):
        profile = json.loads((ROOT / "Tools/MiniApps/native-profile.json").read_text())
        self.assertEqual(profile["selected_methods"], METHODS)
        self.assertEqual(set(METHODS), {x for methods in TARGET_METHODS.values() for x in methods})
        for target, method in [("AnytypeTests", UI_RETURN), ("Other", PREPARE),
                               ("AnytypeTests", PREPARE + "()"), ("AnytypeTests", "Other/test")]:
            with self.assertRaises(ValueError):
                selector(target, method)

    def test_compiled_inventory_rejects_zero_foreign_duplicate_and_disabled_selection(self):
        expected = "AnytypeTests/" + PREPARE + "()"
        valid = {"errors": [], "values": [{"testPlan": "AnytypeTests",
            "enabledTests": [{"identifier": expected}], "disabledTests": []}]}
        self.assertEqual(validate_enumeration(valid, "AnytypeTests", PREPARE)["testsExecuted"], 0)
        cases = []
        empty = copy.deepcopy(valid); empty["values"][0]["enabledTests"] = []; cases.append(empty)
        foreign = copy.deepcopy(valid)
        foreign["values"][0]["enabledTests"].append({"identifier": "AnytypeTests/" + VERIFY + "()"})
        cases.append(foreign)
        duplicate = copy.deepcopy(valid)
        duplicate["values"][0]["enabledTests"].append({"identifier": expected}); cases.append(duplicate)
        disabled = copy.deepcopy(valid)
        disabled["values"][0]["disabledTests"] = [{"identifier": expected}]; cases.append(disabled)
        bare = copy.deepcopy(valid)
        bare["values"][0]["enabledTests"] = [{"identifier": expected[:-2]}]; cases.append(bare)
        wrong_plan = copy.deepcopy(valid); wrong_plan["values"][0]["testPlan"] = "Other"; cases.append(wrong_plan)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_enumeration(value, "AnytypeTests", PREPARE)

    def test_disabled_or_ambiguous_original_target_is_rejected(self):
        original = ORIGINALS / "Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun"
        value = plistlib.loads(original.read_bytes())
        targets = value["TestConfigurations"][0]["TestTargets"]
        target = next(x for x in targets if x["BlueprintName"] == "AnytypeTests")
        disabled = copy.deepcopy(value)
        next(x for x in disabled["TestConfigurations"][0]["TestTargets"]
             if x["BlueprintName"] == "AnytypeTests")["IsEnabled"] = False
        duplicate = copy.deepcopy(value)
        duplicate["TestConfigurations"][0]["TestTargets"].append(copy.deepcopy(target))
        with tempfile.TemporaryDirectory() as tmp:
            for changed in (disabled, duplicate):
                source = Path(tmp) / "original.xctestrun"; source.write_bytes(plistlib.dumps(changed))
                with self.assertRaises(ValueError):
                    configure_tests(source, Path(tmp) / "scoped.xctestrun", {}, "AnytypeTests", PREPARE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
