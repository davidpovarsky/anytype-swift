"""Ownership controls for the original Hanlin package route; no SDK acceptance."""
import copy
import unittest
from framework_profile import (ASSISTANT_CAPABILITY_ROUTE, TARGET,
                               verify_assistant_capability_route)


class AssistantCapabilityRouteControls(unittest.TestCase):
    def setUp(self):
        self.route = copy.deepcopy(ASSISTANT_CAPABILITY_ROUTE)
        r = self.route
        self.added = {r["package_id"], r["product_id"], r["build_file_id"]}
        self.profile = {"assistant_capability_route": copy.deepcopy(r)}
        self.candidate = {"rootObject": "PROJECT", "objects": {
            "PROJECT": {"isa": "PBXProject", "packageReferences": [r["package_id"]]},
            r["package_id"]: {"isa": "XCLocalSwiftPackageReference", "relativePath": "Dependencies/Hanlin"},
            r["product_id"]: {"isa": "XCSwiftPackageProductDependency", "package": r["package_id"],
                              "productName": "HanlinAssistantCapabilities"},
            r["build_file_id"]: {"isa": "PBXBuildFile", "productRef": r["product_id"]},
            r["framework_phase_id"]: {"isa": "PBXFrameworksBuildPhase", "files": [r["build_file_id"]]},
            r["target_id"]: {"isa": "PBXNativeTarget", "name": TARGET,
                              "packageProductDependencies": [r["product_id"]],
                              "buildPhases": [r["framework_phase_id"]]},
        }}

    def check(self):
        return verify_assistant_capability_route(self.candidate, self.added, self.profile)

    def test_exact_original_package_has_one_editor_owner(self):
        self.assertEqual(self.check()["productName"], "HanlinAssistantCapabilities")
        self.assertIsNone(verify_assistant_capability_route(self.candidate, self.added, {}))

    def test_changed_package_or_product_is_not_admitted(self):
        for identifier, key, value in [
            (self.route["package_id"], "relativePath", "Dependencies/OtherHanlin"),
            (self.route["product_id"], "productName", "OtherCapabilities"),
            (self.route["build_file_id"], "productRef", "UNREVIEWED")]:
            old = self.candidate["objects"][identifier][key]
            self.candidate["objects"][identifier][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check()
            self.candidate["objects"][identifier][key] = old

    def test_repeated_or_missing_link_is_rejected(self):
        phase = self.candidate["objects"][self.route["framework_phase_id"]]
        for files in [[], [self.route["build_file_id"]] * 2]:
            phase["files"] = files
            with self.subTest(files=files), self.assertRaises(ValueError):
                self.check()

    def test_another_implementation_owner_is_rejected(self):
        self.candidate["objects"]["OTHER_TARGET"] = {
            "isa": "PBXNativeTarget", "packageProductDependencies": [self.route["product_id"]]}
        with self.assertRaises(ValueError):
            self.check()

    def test_borrowed_instead_of_additive_object_is_rejected(self):
        for identifier in list(self.added):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                verify_assistant_capability_route(self.candidate, self.added - {identifier}, self.profile)
