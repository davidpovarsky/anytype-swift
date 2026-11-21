"""Focused controls for binding the unchanged profile to the existing SDK06 build."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import shared_editor_existing_build as runner
import test_shared_editor_profile as fixtures

class ExistingBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "Anytype.app"
        self.app.mkdir()
        self.app_executable = self.app / "Anytype"
        self.test_bundle = self.app / "AnytypeTests.xctest"
        self.test_bundle.mkdir()
        self.test_executable = self.test_bundle / "AnytypeTests"
        self.configuration = self.root / "Anytype.xctestrun"
        for path in (self.app_executable, self.test_executable, self.configuration):
            path.write_bytes(path.name.encode())
        self.source = dict(methods=sorted(fixtures.EXPECTED), source_hashes={"source.swift": "a" * 64},
                           expected_methods=10, declared_invocations=15, profile=runner.PROFILE.value)
        self.report, self.tree = fixtures.summary(), fixtures.tree()
        self.commands, self.after_run = [], None
        self.shared = SimpleNamespace(write=self.write, digest=self.digest, run_xctest=self.run_xctest)
        self.products = (self.app, self.app_executable, self.test_bundle, self.test_executable)
        source_patch = patch.object(runner, "source_contract", return_value=self.source)
        self.source_mock = source_patch.start()
        self.addCleanup(source_patch.stop)
        product_patch = patch.object(runner.host, "xctest_products", return_value=self.products)
        self.product_mock = product_patch.start()
        self.addCleanup(product_patch.stop)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run_xctest(self, command, app, evidence, bundle, prefix, *, command_runner):
        self.commands.append(command)
        self.assertIs(command_runner, runner.host.command)
        self.write(evidence / (prefix + "-summary.json"), self.report)
        self.write(evidence / (prefix + "-tests.json"), self.tree)
        if self.after_run:
            self.after_run()

    def execute(self, directory="evidence"):
        return runner.execute(self.root, self.configuration, fixtures.UDID, self.app,
                              self.root / directory, self.shared)

    def test_one_existing_build_executes_only_the_original_ten_methods_and_fifteen_cases(self):
        for count in (10, 15):
            self.report = fixtures.summary(count)
            result = self.execute("evidence-" + str(count))
            self.assertEqual(result["status"], runner.PROFILE.pass_status)
            self.assertEqual(result["actual"]["actual_method_count"], 10)
            self.assertEqual(result["actual"]["declared_case_count"], 15)
            self.assertEqual(result["additional_app_builds"], 0)
            self.assertFalse(result["real_native_persistence_accepted"])
            command = self.commands[-1]
            self.assertEqual(command[:2], ["xcodebuild", "test-without-building"])
            self.assertEqual({item for item in command if item.startswith("-only-testing:")},
                             {"-only-testing:AnytypeTests/" + runner.SUITE})
            self.assertNotIn("build-for-testing", command)
        self.assertEqual(len(self.commands), 2)

    def test_wrong_app_product_is_rejected_before_xcode(self):
        self.product_mock.return_value = (self.root / "different.app", *self.products[1:])
        with self.assertRaisesRegex(ValueError, "SDK06 app build"):
            self.execute()
        self.assertEqual(self.commands, [])

    def test_missing_argument_cannot_be_hidden_by_all_passing_summary(self):
        next(item for item in self.tree["children"] if item.get("children"))["children"].pop()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate"):
            self.execute()
        result = json.loads((self.root / "evidence/execution.json").read_text())
        self.assertEqual(result["status"], "FAIL")

    def test_source_mutation_during_execution_is_rejected(self):
        changed = copy.deepcopy(self.source)
        changed["source_hashes"]["source.swift"] = "b" * 64
        self.source_mock.side_effect = [self.source, changed]
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.execute()
        self.assertEqual(len(self.commands), 1)

    def test_mutated_app_test_or_configuration_is_rejected(self):
        for index, path in enumerate((self.app_executable, self.test_executable, self.configuration)):
            with self.subTest(path=path.name):
                self.after_run = lambda path=path: path.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "built products changed"):
                    self.execute("mutation-" + str(index))

    def test_stale_evidence_is_rejected_before_xcode(self):
        self.write(self.root / "evidence/execution.json", {"status": "old"})
        with self.assertRaisesRegex(ValueError, "stale"):
            self.execute()
        self.assertEqual(self.commands, [])

class TrackedContractTests(unittest.TestCase):
    def test_actual_tracked_profile_keeps_exact_selection(self):
        source = runner.source_contract(Path(__file__).resolve().parents[2])
        self.assertEqual(source["methods"], sorted(fixtures.EXPECTED))
        self.assertEqual(source["declared_invocations"], 15)
        self.assertEqual(len(source["source_hashes"]), 1)

if __name__ == "__main__":
    unittest.main()
