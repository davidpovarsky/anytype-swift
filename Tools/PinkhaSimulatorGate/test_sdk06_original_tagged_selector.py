"""One new offline control for the exact original descriptor/tag composition."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import unittest
from unittest import mock

import run_ui27 as shared
import sdk06_original_native as native
import sdk06_original_tagged_selector as selected
import sdk06_tagged_selector as retained
import shared_editor_existing_build as component

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/validation/20261123-sdk06-original-native-continuation/fixtures"


class OriginalTagSelectionControls(unittest.TestCase):
    def test_original_descriptor_has_one_tag_only_selection_and_requires_actual23(self):
        output = Path(os.environ["PINKHA_SDK06_NEW_CONTROL_ARTIFACTS"]) / "tag-selection"
        output.mkdir(parents=True, exist_ok=False)
        contract = json.loads((ROOT / native.ADMISSION).read_bytes())
        tag_raw = (ROOT / contract["tag_contract"]["path"]).read_bytes()
        tag = json.loads(tag_raw)
        source = {
            "source_hashes": {name: row["after_sha256"] for name, row in tag["source_inverses"].items()
                              if name.endswith(".swift")},
            "expected_methods": 23, "declared_invocations": 32,
            "methods": sorted(name.removeprefix("AnytypeTests/").split("(", 1)[0]
                              for name in tag["selection"]["selected"]),
            "unselected_existing_methods": sorted(name.removeprefix("AnytypeTests/").split("(", 1)[0]
                                                   for name in tag["selection"]["excluded"]),
            "compiled_declarations": {name.removeprefix("AnytypeTests/").split("(", 1)[0]: name
                                      for name in tag["selection"]["declarations"]},
        }
        descriptor_raw = (FIXTURES / "original-native.xctestrun").read_bytes()
        self.assertEqual(hashlib.sha256(descriptor_raw).hexdigest(), selected.ORIGINAL_DESCRIPTOR_SHA256)
        discovery_raw = (FIXTURES / "original-discovery.enumeration.json").read_bytes()
        actual_selected_raw = (FIXTURES / "original-selected.enumeration.json").read_bytes()
        self.assertEqual(hashlib.sha256(discovery_raw).hexdigest(),
                         "e524a1bde9cb30e1d237ea9cbc93ac846f7a3b9561a015602f082c47d65bb37c")
        self.assertEqual(hashlib.sha256(actual_selected_raw).hexdigest(),
                         "498d8cc08e27a2ffd6e7524085c94e16d0bea6c981ea8307f750452b54e75631")
        actual_selected = json.loads(actual_selected_raw)
        with self.subTest(scope="original_actual30_is_refused"):
            with self.assertRaisesRegex(ValueError, "exact23"):
                retained.qualify_enumeration(actual_selected, tag["selection"])
        synthetic = copy.deepcopy(actual_selected)
        row = synthetic["values"][0]
        exclusions = set(tag["selection"]["excluded"])
        removed = [item for item in row["enabledTests"] if item["identifier"] in exclusions]
        self.assertEqual(len(removed), 7)
        row["enabledTests"] = [item for item in row["enabledTests"] if item["identifier"] not in exclusions]
        row["disabledTests"].extend(removed)
        synthetic_raw = (json.dumps(synthetic, sort_keys=True) + "\n").encode()
        uid = "11111111-1111-4111-8111-111111111111"
        runtime_root = output / "synthetic-runtime"
        library = runtime_root / "usr/lib/libMainThreadChecker.dylib"
        library.parent.mkdir(parents=True)
        library.write_bytes(b"\xcf\xfa\xed\xfe" + b"CONTROL_ONLY_NOT_AN_APP_RUNTIME")
        runtime = {"isAvailable": True, "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0",
                   "supportedArchitectures": ["arm64"], "runtimeRoot": str(runtime_root),
                   "version": "27.0", "buildversion": "CONTROL_ONLY"}
        app = output / "synthetic-app"
        tag_path = app / contract["tag_contract"]["path"]
        tag_path.parent.mkdir(parents=True)
        tag_path.write_bytes(tag_raw)
        derived = output / "synthetic-products"
        descriptor = derived / contract["descriptor"]["path"]
        descriptor.parent.mkdir(parents=True)
        descriptor.write_bytes(descriptor_raw)
        evidence = output / "normalization"
        evidence.mkdir()
        descriptor_binding = native.normalize_descriptor(derived, evidence, runtime, contract)
        host = Path(descriptor_binding["host_path"])
        host_value = plistlib.loads(host.read_bytes())
        original_value = plistlib.loads(descriptor_raw)
        expected_host = copy.deepcopy(original_value)
        for target in expected_host["TestConfigurations"][0]["TestTargets"]:
            chain = target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"]
            target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = chain.replace(
                contract["descriptor"]["main_thread_checker_token"], str(library.resolve()))
        self.assertEqual(host_value, expected_host)
        self.assertEqual(descriptor.read_bytes(), descriptor_raw)
        selected_value = selected.tag_only_value(host_value)
        expected_selected = copy.deepcopy(host_value)
        expected_selected["TestConfigurations"][0]["TestTargets"] = [
            target for target in expected_selected["TestConfigurations"][0]["TestTargets"]
            if target["BlueprintName"] == "AnytypeTests"]
        self.assertEqual(selected_value, expected_selected)
        with self.subTest(scope="preexisting_selection_is_not_erased"):
            bad = copy.deepcopy(host_value)
            bad["TestConfigurations"][0]["TestTargets"][2]["OnlyTestIdentifiers"] = ["Other"]
            with self.assertRaisesRegex(ValueError, "selection metadata"):
                selected.tag_only_value(bad)
        binding = {"source_sha": "a" * 40, "run_id": "900000001", "run_attempt": "1"}
        context = native.SDK06OriginalNativeContext(ROOT, app, output / "work", evidence, derived,
            json.dumps(binding, sort_keys=True), "{}", json.dumps(descriptor_binding, sort_keys=True),
            json.dumps({"udid": uid, "runtime": runtime}, sort_keys=True), native._SEAL)
        base = ["xcodebuild", "test-without-building", "-xctestrun", str(host),
                "-destination", "platform=iOS Simulator,id=" + uid, "-parallel-testing-enabled", "NO"]
        commands = []
        owner = self
        current_payload = {"selected": actual_selected_raw}
        class OfflineEnumeration:
            def __init__(self, app_arg, directory, receipt):
                owner.assertEqual(app_arg, app)
                owner.assertEqual(receipt["product_tests_executed"], 0)
            def run(self, argv, label, timeout):
                owner.assertEqual(timeout, 600)
                commands.append(list(argv))
                descriptor_arg = Path(argv[argv.index("-xctestrun") + 1])
                value = plistlib.loads(descriptor_arg.read_bytes())
                targets = value["TestConfigurations"][0]["TestTargets"]
                owner.assertEqual([target["BlueprintName"] for target in targets], ["AnytypeTests"])
                if label == "tagged-selected":
                    owner.assertEqual(value, expected_selected)
                    owner.assertEqual([arg for arg in argv if arg.startswith(("-only-testing", "-skip-testing"))],
                                      ["-only-testing-tags"])
                    owner.assertEqual(argv[argv.index("-only-testing-tags") + 1], selected.TAG)
                    raw = current_payload["selected"]
                else:
                    owner.assertEqual(targets[0]["OnlyTestIdentifiers"], list(component.SUITES))
                    owner.assertNotIn("-only-testing-tags", argv)
                    raw = discovery_raw
                target = Path(argv[argv.index("-test-enumeration-output-path") + 1])
                target.write_bytes(raw)
                return target, {"return_code": 0}
        def record_descriptor(self, path, purpose):
            # The finite tree/ledger implementation is exercised in the third
            # new control; this control isolates exact selection composition.
            owner.assertIn(purpose, {"discovery", "tagged-selection"})
            owner.assertTrue(path.is_file() and not path.is_symlink())
            owner.assertEqual(path.parent, host.parent)
            return {"path": str(path), "sha256": native.sha(path), "control_fixture_only": True}
        with mock.patch.object(native, "manifest", return_value=contract), \
                mock.patch.object(native.SDK06OriginalNativeContext, "verify_current", return_value=contract), \
                mock.patch.object(native.SDK06OriginalNativeContext, "register_generated_descriptor", record_descriptor), \
                mock.patch.object(selected.probe, "Commands", OfflineEnumeration):
            failed = output / "actual30-refusal"
            failed.mkdir()
            plan = selected.load_plan(context)
            with self.subTest(scope="actual30_failure_keeps_both_original_observations"):
                with self.assertRaisesRegex(ValueError, "exact23"):
                    plan.enumerate_current(app, base, failed, shared, source)
                saved = json.loads((failed / "original-tag-enumeration-observations.json").read_bytes())
                self.assertEqual(set(saved["observations"]), {"discovery", "selected"})
                self.assertEqual(saved["observations"]["selected"]["sha256"],
                                 hashlib.sha256(actual_selected_raw).hexdigest())
                self.assertFalse(saved["qualified"])
                self.assertEqual(saved["tests_executed"], 0)
            current_payload["selected"] = synthetic_raw
            positive = output / "synthetic23-contract-only"
            positive.mkdir()
            plan = selected.load_plan(context)
            receipt = plan.enumerate_current(app, base, positive, shared, source)
            self.assertEqual(receipt["selected_method_count"], 23)
            self.assertEqual(receipt["unselected_identifiers"], tag["selection"]["excluded"])
            execution_base = list(base)
            execution_base[execution_base.index("-xctestrun") + 1] = receipt["selected_configuration"]["path"]
            with self.subTest(scope="exact_tag_argv_once"):
                self.assertEqual(plan.execution_arguments(receipt, execution_base),
                                 ["-only-testing-tags", "pinkhaSDK06Pending23"])
                with self.assertRaisesRegex(ValueError, "once"):
                    plan.execution_arguments(receipt, execution_base)
            changed = output / "synthetic23-descriptor-drift"
            changed.mkdir()
            plan = selected.load_plan(context)
            receipt = plan.enumerate_current(app, base, changed, shared, source)
            execution_base[execution_base.index("-xctestrun") + 1] = receipt["selected_configuration"]["path"]
            Path(receipt["selected_configuration"]["path"]).write_bytes(b"changed")
            with self.subTest(scope="changed_selected_descriptor_refused"):
                with self.assertRaisesRegex(ValueError, "descriptor changed"):
                    plan.execution_arguments(receipt, execution_base)
        # The existing result validator remains an exact source dependency.
        # It still delegates each actual method's literal argument nodes to all
        # three original component validators; none of those old tests rerun.
        path = "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"
        original = subprocess.check_output(["git", "-C", str(ROOT), "show",
            "26b61bbee7dac17339a90111602c7ec83c7844e4:" + path]).decode()
        current = (ROOT / path).read_text()
        def function(raw):
            node = next(item for item in ast.parse(raw).body
                        if isinstance(item, ast.FunctionDef) and item.name == "validate_results")
            return ast.get_source_segment(raw, node)
        self.assertEqual(function(current), function(original))
        self.assertIn('DECLARED_CASE_COUNT', function(current))
        self.assertIn('validator(selected, methods)', function(current))
        native.save(output / "scope.json", {
            "original_actual30_refused": True, "synthetic23_only_is_not_actual_selector_evidence": True,
            "original_descriptor_sha256": hashlib.sha256(descriptor_raw).hexdigest(),
            "commands": commands, "existing_32_argument_validator_unchanged": True,
            "product_tests_executed": 0, "Apple_builds": 0, "old_controller_methods_executed": 0,
        }, original=True)
