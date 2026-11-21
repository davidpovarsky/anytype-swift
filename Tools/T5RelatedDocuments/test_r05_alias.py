"""Reject false exact-one alias receipts before consuming an Apple run."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from run_r05_alias import METHOD, PACKAGE, PIN, SUITE, original_cases, resolved_pin


class R05AliasReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "original.xml"

    def write(self, count=1, status=None, method=METHOD, suite=SUITE):
        root = ET.Element("testsuites")
        group = ET.SubElement(root, "testsuite")
        for _ in range(count):
            case = ET.SubElement(group, "testcase", classname=f"{PACKAGE}Tests.{suite}", name=method)
            if status:
                ET.SubElement(case, status)
        ET.ElementTree(root).write(self.path)

    def log(self, method=METHOD, status="passed"):
        return f"Test Case '-[{PACKAGE}Tests.{SUITE} {method}]' {status} (0.001 seconds)."

    def testExactOriginalXCTestAndXunitAreBothRequired(self):
        self.write()
        self.assertEqual(original_cases(self.path, self.log())["method"], METHOD)
        for log in ["", self.log(status="skipped"), self.log(status="failed"), self.log() + "\n" + self.log(),
                    self.log() + "\nTest Case '-[OtherTests testUnreviewed]' passed (0.001 seconds)."]:
            with self.assertRaises(ValueError):
                original_cases(self.path, log)

    def testMissingDuplicateOrUnrelatedMethodCannotQualify(self):
        for options in [{"count": 0}, {"count": 2}, {"method": "testUnreviewed"}, {"suite": "OtherTests"}]:
            self.write(**options)
            with self.assertRaises(ValueError):
                original_cases(self.path, self.log())

    def testNonpassXunitCannotBeHiddenByTerminalPass(self):
        for status in ["failure", "error", "skipped"]:
            self.write(status=status)
            with self.assertRaises(ValueError):
                original_cases(self.path, self.log())

    def testMalformedOriginalRecordIsRejected(self):
        self.path.write_text("<testsuites>")
        with self.assertRaises(ET.ParseError):
            original_cases(self.path, self.log())

    def testOnlyTheExactSingleDependencyPinIsAccepted(self):
        pin = {"identity": "torahinspectorkit", "state": {"revision": PIN}}
        path = self.path.with_suffix(".json")
        path.write_text(json.dumps({"pins": [pin]}))
        self.assertEqual(resolved_pin(path), PIN)
        for pins in [[], [pin, pin], [{"identity": "torahinspectorkit", "state": {"revision": "0" * 40}}]]:
            path.write_text(json.dumps({"pins": pins}))
            with self.assertRaises(ValueError):
                resolved_pin(path)


if __name__ == "__main__":
    unittest.main()
