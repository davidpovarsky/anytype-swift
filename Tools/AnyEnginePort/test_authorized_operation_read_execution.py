"""Receipt controls reject accidental old-suite execution and changed binaries."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

import verify_authorized_operation_read_execution as check


class CandidateReadExecutionTests(unittest.TestCase):
    def fixture(self):
        summary = {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0,
            "devicesAndConfigurations": [{"device": {"deviceId": "owned", "osVersion": "27.0",
                "osBuildNumber": "24A123", "architecture": "arm64"}}]}
        tree = {"children": [{"nodeType": "Test Case", "nodeIdentifier": check.SUITE + "/" + check.METHOD + "()", "result": "Passed"}]}
        return summary, tree

    def test_exact_new_method_is_required(self):
        summary, tree = self.fixture()
        self.assertEqual(check.validate_execution(summary, tree, "owned")["counts"]["passedTests"], 1)
        for bad in ("DifferentClass/" + check.METHOD, check.SUITE + "/OldAcceptedMethod"):
            changed = copy.deepcopy(tree)
            changed["children"][0]["nodeIdentifier"] = bad
            with self.subTest(method=bad), self.assertRaises(RuntimeError):
                check.validate_execution(summary, changed, "owned")

    def test_zero_skipped_or_other_destination_never_qualifies(self):
        summary, tree = self.fixture()
        cases = []
        zero = copy.deepcopy(summary); zero.update(totalTestCount=0, passedTests=0); cases.append((zero, tree, "owned"))
        skip = copy.deepcopy(summary); skip.update(passedTests=0, skippedTests=1); cases.append((skip, tree, "owned"))
        cases.append((summary, tree, "unowned"))
        for i, args in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(RuntimeError):
                check.validate_execution(*args)

    def test_an_extra_previously_accepted_method_is_rejected(self):
        summary, tree = self.fixture()
        tree["children"].append({"nodeType": "Test Case", "nodeIdentifier": "AnyEmbeddedRuntimeTests/testRealManagedRuntimeLifecycleAndControlBoundary()", "result": "Passed"})
        summary.update(totalTestCount=2, passedTests=2)
        with self.assertRaises(RuntimeError):
            check.validate_execution(summary, tree, "owned")
        summary.update(totalTestCount=1, passedTests=1)
        with self.assertRaises(RuntimeError):
            check.validate_execution(summary, tree, "owned")

    def test_changed_missing_or_extra_installed_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary = root / "any.xcframework/ios-arm64/any.framework/any"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"source-bound-test-binary")
            receipt = {"filesSHA256": {binary.relative_to(root).as_posix(): hashlib.sha256(binary.read_bytes()).hexdigest()}}
            self.assertEqual(len(check.verify_installed_files(root, receipt)), 1)
            binary.write_bytes(b"different-binary")
            with self.assertRaises(RuntimeError): check.verify_installed_files(root, receipt)
            binary.unlink()
            with self.assertRaises(RuntimeError): check.verify_installed_files(root, receipt)
            binary.write_bytes(b"source-bound-test-binary")
            (root / "unexpected").write_bytes(b"extra")
            with self.assertRaises(RuntimeError): check.verify_installed_files(root, receipt)


if __name__ == "__main__":
    unittest.main()
