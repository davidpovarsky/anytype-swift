"""New basename consumer controls; API/run values below are synthetic fixtures.

No usable admission is created. Temporary partial plan objects only exercise
the existing current-enumeration/argv plumbing; no Xcode, product or API runs.
"""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest import mock

import sdk06_qualified_selector as selected

APP = Path(__file__).resolve().parents[2]
UDID = "90000000-0000-4000-8000-000000000009"


def original_selection():
    return json.loads((APP / selected.BASENAME_PROOF_ROOT / "receipt.json").read_bytes())["selection_contract"]


def synthetic_metadata():
    name = selected.BASENAME_VARIANT
    paths = set(selected.BASENAME_EXTRA_INPUTS) | {
        "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py",
        "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"}
    head = subprocess.check_output(["git", "-C", str(APP), "rev-parse", "HEAD"], text=True).strip()
    files = {item: "f" * 64 for item in (
        "receipt.json", "original.xctestrun", "originals/execution.json",
        "originals/shared-editor-components/compiled-suite-enumeration.json",
        name + ".enumeration.json", name + ".xctestrun",
        "enumerate-" + name + ".command.json", "enumerate-" + name + ".log")}
    files["original.xctestrun"] = selected.probe.XCTESTRUN_SHA
    files["originals/execution.json"] = selected.probe.EXECUTION_SHA
    return dict(protocol=selected.PROTOCOL, probe_run_id="999000011", probe_run_attempt="1",
        probe_source_sha=head, artifact_id=999000012,
        artifact_name="Pinkha-SDK06-Enumeration-999000011-1", artifact_sha256="a" * 64,
        artifact_bytes=100, qualified_variant=name,
        probe_control_sources={path: selected.probe.sha(APP / path) for path in paths}, files=files)


def synthetic_record(value, selection):
    receipt = json.loads((APP / selected.BASENAME_PROOF_ROOT / "receipt.json").read_bytes())
    receipt.update(status=selected.probe.PROBE_PASS, control_source_sha=value["probe_source_sha"],
        run_id=value["probe_run_id"], run_attempt=value["probe_run_attempt"],
        control_source_hashes=value["probe_control_sources"], selection_contract=selection,
        finished_at="SYNTHETIC_OFFLINE_PARTIAL_RECORD_NOT_ACCEPTANCE",
        qualified_variant=selected.BASENAME_VARIANT,
        probes=[dict(name=selected.BASENAME_VARIANT, status=selected.probe.PROBE_PASS,
            command_return_code=0, actual_product_tests_executed=0,
            enumeration_sha256=value["files"][selected.BASENAME_VARIANT + ".enumeration.json"])])
    return receipt


def partial_plan_fixture(root, selection, variant):
    # This partial fixture never passes load_plan, API admission or original
    # evidence validation. It isolates the already-sealed plan's argv methods.
    raw = b"synthetic offline plumbing only"
    (root / "synthetic-original.bin").write_bytes(raw)
    value = {"files": {"synthetic-original.bin": hashlib.sha256(raw).hexdigest()}}
    admission = root / "synthetic-offline-partial-plan.json"
    admission.write_text(json.dumps(value))
    return selected.QualifiedSelectorPlan(admission_path=admission, control=root, current_grammar_json="{}",
        _seal=selected._PLAN_SEAL, admission_sha256=selected.probe.sha(admission), evidence=root,
        approved_json=json.dumps(value), selection_json=json.dumps(selection), variant_json=json.dumps(variant))


class BasenameSelectorControls(unittest.TestCase):
    def test_basename_provider_and_exact_nine_source_inputs_are_bound_without_extending_legacy_paths(self):
        value = synthetic_metadata()
        self.assertEqual(selected.admission(value), value)
        current = selected.original_control_sources(APP, value)
        self.assertEqual(set(current), set(selected.BASENAME_CURRENT_INPUTS) | {
            "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py",
            "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"})
        for path in selected.BASENAME_EXTRA_INPUTS:
            bad = copy.deepcopy(value); del bad["probe_control_sources"][path]
            with self.subTest(missing=path), self.assertRaisesRegex(ValueError, "nine exact"):
                selected.admission(bad)
        for path in selected.BASENAME_FIXED_HASHES:
            bad = copy.deepcopy(value); bad["probe_control_sources"][path] = "0" * 64
            with self.subTest(changed=path), self.assertRaisesRegex(ValueError, "must be pinned"):
                selected.admission(bad)
        for path in (".github/workflows/unreviewed.yml", "docs/unreviewed.json",
                     "Tools/PinkhaSimulatorGate/../unreviewed.py"):
            bad = copy.deepcopy(value); bad["probe_control_sources"][path] = "0" * 64
            with self.subTest(extra=path), self.assertRaisesRegex(ValueError, "Unsafe"):
                selected.admission(bad)
        bad = copy.deepcopy(value); bad["probe_source_sha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "exact Git blob"):
            selected.original_control_sources(APP, bad)
        # The added non-Python paths are accepted only for the one new name.
        legacy = copy.deepcopy(value); legacy["qualified_variant"] = "suites-minus-seven-cli"
        old_name = selected.BASENAME_VARIANT
        legacy["files"] = {name.replace(old_name, "suites-minus-seven-cli"): checksum
                           for name, checksum in legacy["files"].items()}
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            selected.admission(legacy)
        root = APP
        real_sha = selected.probe.sha
        with mock.patch.object(selected.probe, "sha", side_effect=lambda path:
                               "0" * 64 if Path(path) == root / selected.BASENAME_ENTRY else real_sha(path)), \
             mock.patch("importlib.import_module") as importer:
            with self.assertRaisesRegex(ValueError, "bytes differ"):
                selected._basename_provider()
            importer.assert_not_called()

    def test_basename_record_current_enumeration_and_execution_keep_exact23_and_identical_seven_skips(self):
        selection = original_selection()
        value = synthetic_metadata()
        receipt = synthetic_record(value, selection)
        record, variant = selected.qualified_record(receipt, value, selection)
        self.assertEqual(variant, selected._basename_provider().fixed_candidates(selection)[0])
        self.assertEqual(len(variant["cli_skip"]), 7)
        self.assertEqual(sum("(" not in name for name in variant["cli_skip"]), 3)
        for rows in ([], receipt["probes"] * 2,
                     [dict(receipt["probes"][0], name="suites-minus-seven-cli")]):
            wrong = copy.deepcopy(receipt); wrong["probes"] = rows
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                selected.qualified_record(wrong, value, selection)
        original = json.loads((APP / selected.BASENAME_PROOF_ROOT / "receipt.json").read_bytes())
        with self.assertRaises(ValueError):
            selected.qualified_record(original, value, selection)
        actual26 = json.loads((APP / selected.BASENAME_PROOF_ROOT / "suites-minus-seven-cli.enumeration.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "exactly the requested23"):
            selected.probe.qualify_enumeration(actual26, selection)
        # Even a synthetic partial PASS record cannot turn the original failed
        # command observations into evidence for the new request.
        command = json.loads((APP / selected.BASENAME_PROOF_ROOT / "enumerate-suites-minus-seven-cli.command.json").read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); log = root / "synthetic.log"; log.write_text("synthetic")
            with self.assertRaisesRegex(ValueError, "missing or duplicated"):
                selected.validate_original_command(receipt, record, command, log, variant)
        source = dict(source_hashes=selected.probe.SOURCES, expected_methods=23, declared_invocations=32,
            compiled_declarations={name: name for name in selection["declarations"]},
            methods=selection["selected"], unselected_existing_methods=selection["excluded"])
        for wrong_selection in (False, True):
            with self.subTest(selected26=wrong_selection), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); evidence = root / "evidence"; evidence.mkdir()
                plan = partial_plan_fixture(root, selection, variant)
                original_descriptor = root / "current.xctestrun"
                original_descriptor.write_bytes((APP / selected.BASENAME_PROOF_ROOT / "original.xctestrun").read_bytes())
                original_bytes = original_descriptor.read_bytes()
                calls = []
                class Runner:
                    def __init__(self, *args): pass
                    def run(self, argv, label, timeout):
                        calls.append(argv)
                        if label.endswith("discovery"):
                            enabled, disabled = selection["declarations"], []
                        elif wrong_selection:
                            output = Path(argv[argv.index("-test-enumeration-output-path") + 1])
                            output.write_text(json.dumps(actual26))
                            return output, {"return_code": 0}
                        else:
                            enabled, disabled = selection["selected"], selection["excluded"]
                        payload = dict(errors=[], values=[dict(testPlan="AnytypeTests",
                            enabledTests=[dict(identifier=name) for name in enabled],
                            disabledTests=[dict(identifier=name) for name in disabled])])
                        output = Path(argv[argv.index("-test-enumeration-output-path") + 1])
                        output.write_text(json.dumps(payload))
                        return output, {"return_code": 0}
                base = ["xcodebuild", "test-without-building", "-xctestrun", str(original_descriptor),
                        "-destination", "platform=iOS Simulator,id=" + UDID, "-parallel-testing-enabled", "NO"]
                with mock.patch.object(selected.probe, "Commands", Runner):
                    if wrong_selection:
                        with self.assertRaisesRegex(ValueError, "exactly the requested23"):
                            plan.enumerate_current(APP, base, evidence, object(), source)
                    else:
                        result = plan.enumerate_current(APP, base, evidence, object(), source)
                        args = plan.execution_arguments(result)
                        self.assertEqual(args, ["-only-testing:" + name for name in variant["cli"]] +
                                               ["-skip-testing:" + name for name in variant["cli_skip"]])
                        self.assertEqual(result["selected_method_count"], 23)
                        self.assertEqual(result["current_enumeration"]["qualification"]["expected_future_cases"], 32)
                        self.assertEqual([arg for arg in calls[1] if arg.startswith(
                            ("-only-testing:", "-skip-testing:"))], args)
                        changed = copy.deepcopy(result); changed["qualified_cli_arguments"] = args[:-1]
                        with self.assertRaises(ValueError): plan.execution_arguments(changed)
                self.assertEqual(original_descriptor.read_bytes(), original_bytes)
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(argv.count("-enumerate-tests") == 1 and "build-for-testing" not in argv
                                    for argv in calls))


if __name__ == "__main__":
    unittest.main()
