"""Focused checks preventing a package proof from accepting omissions or skips."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from run_authorized_operation_read_packages import PINS, SUITES, qualified_cases, qualified_xctest_output, resolved_pins


class ReadPackageReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "original.xml"
        self.package = "PinkhaAnyEngine"
        self.suite, self.methods = SUITES[self.package]

    def fixture(self, methods=None):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite", name=self.suite)
        for method in self.methods if methods is None else methods:
            ET.SubElement(suite, "testcase", classname=f"{self.package}Tests.{self.suite}", name=method, time="0.001")
        return root

    def save(self, root):
        ET.ElementTree(root).write(self.path)

    def test_complete_original_case_set_is_required(self):
        self.save(self.fixture())
        self.assertEqual(len(qualified_cases(self.path, self.package)), 6)
        for methods in [[], self.methods[:-1], (*self.methods, self.methods[0]), (*self.methods, "testUnreviewed")]:
            self.save(self.fixture(methods))
            with self.assertRaises(ValueError):
                qualified_cases(self.path, self.package)

    def test_skipped_failed_or_errored_case_never_becomes_pass(self):
        for status in ["failure", "error", "skipped"]:
            root = self.fixture()
            ET.SubElement(next(root.iter("testcase")), status)
            self.save(root)
            with self.assertRaises(ValueError):
                qualified_cases(self.path, self.package)

    def test_foreign_class_and_malformed_original_xml_are_rejected(self):
        root = self.fixture()
        next(root.iter("testcase")).set("classname", "OtherTests")
        self.save(root)
        with self.assertRaises(ValueError):
            qualified_cases(self.path, self.package)
        self.path.write_text("<testsuites>")
        with self.assertRaises(ET.ParseError):
            qualified_cases(self.path, self.package)

    def test_actual_dependency_revisions_are_exact_and_unique(self):
        path = self.path.with_suffix(".json")
        pins = [{"identity": name, "state": {"revision": revision}} for name, revision in PINS.items()]
        path.write_text(json.dumps({"pins": pins}))
        self.assertEqual(resolved_pins(path, "PinkhaAnyIntegration"), PINS)
        for changed in [pins[:-1], [*pins, pins[0]], [*pins[:-1], {"identity": "torahinspectorkit", "state": {"revision": "4e59e909dd22685bb46f9396bc57e5f8c627d773"}}]]:
            path.write_text(json.dumps({"pins": changed}))
            with self.assertRaises(ValueError):
                resolved_pins(path, "PinkhaAnyIntegration")

    def test_original_darwin_and_swift_xctest_results_are_required(self):
        for objc in [True, False]:
            records = []
            for method in self.methods:
                name = f"-[{self.package}Tests.{self.suite} {method}]" if objc else f"{self.suite}.{method}"
                records.append(f"Test Case '{name}' passed (0.001 seconds).")
            self.assertEqual(qualified_xctest_output("\n".join(records), self.package), list(self.methods))

    def test_xunit_process_success_cannot_hide_a_skipped_method(self):
        self.save(self.fixture())
        self.assertEqual(len(qualified_cases(self.path, self.package)), 6)
        passed = [f"Test Case '-[{self.package}Tests.{self.suite} {method}]' passed (0.001 seconds)." for method in self.methods]
        for records in [passed[:-1], [*passed, passed[0]], [passed[0].replace(" passed ", " skipped "), *passed[1:]]]:
            with self.assertRaises(ValueError):
                qualified_xctest_output("\n".join(records), self.package)


if __name__ == "__main__":
    unittest.main()
