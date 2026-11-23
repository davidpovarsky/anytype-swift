"""New SDK selector controls. All run/API values are synthetic test fixtures.

No accepted selector admission is authored by these tests. They invoke no Xcode,
product test, simulator, producer or GitHub API.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

import sdk06_qualified_selector as selected
import sdk06_qualified_continuation as current

APP = Path(__file__).resolve().parents[2]
UDID = "90000000-0000-4000-8000-000000000009"


def source_selection():
    # Preserve the real three tracked source bytes while modelling the case-
    # insensitive Xcode synchronized root inside a disposable Linux fixture.
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary)
        for name, checksum in selected.probe.SOURCES.items():
            data = (APP / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == checksum
            path = fixture / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (fixture / "AnytypeTests").symlink_to("AnyTypeTests", target_is_directory=True)
        tracked = ("\0".join(selected.probe.SOURCES) + "\0").encode()
        with mock.patch.object(selected.component.subprocess, "check_output", return_value=tracked):
            source = selected.component.source_contract(fixture)
    return source, selected.selection_from_source(source)


def approved(variant="suites-minus-seven-cli"):
    names = ["receipt.json", "original.xctestrun", "originals/execution.json",
        "originals/shared-editor-components/compiled-suite-enumeration.json",
        variant + ".enumeration.json", variant + ".xctestrun",
        "enumerate-" + variant + ".command.json", "enumerate-" + variant + ".log"]
    files = {name: "f" * 64 for name in names}
    files["original.xctestrun"] = selected.probe.XCTESTRUN_SHA
    files["originals/execution.json"] = selected.probe.EXECUTION_SHA
    return dict(protocol=selected.PROTOCOL, probe_run_id="999000001", probe_run_attempt="1",
        probe_source_sha="c" * 40, artifact_id=999000002,
        artifact_name="Pinkha-SDK06-Enumeration-999000001-1", artifact_sha256="a" * 64,
        artifact_bytes=100, qualified_variant=variant,
        probe_control_sources={**{"Tools/Synthetic/dependency" + str(i) + ".py": "b" * 64 for i in range(4)},
            "Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py": "b" * 64}, files=files)


def api_values(value):
    run = dict(id=int(value["probe_run_id"]), run_attempt=int(value["probe_run_attempt"]),
        head_sha=value["probe_source_sha"], event="workflow_dispatch", status="completed", conclusion="success",
        repository=dict(full_name=selected.probe.REPOSITORY), path=".github/workflows/torah-inspector-ipados27.yml")
    artifact = dict(id=value["artifact_id"], name=value["artifact_name"],
        digest="sha256:" + value["artifact_sha256"], size_in_bytes=value["artifact_bytes"], expired=False,
        workflow_run=dict(id=run["id"], head_sha=run["head_sha"]))
    return run, artifact


def synthetic_record(value, selection):
    variant = next(v for v in selected.probe.variants(selection) if v["name"] == value["qualified_variant"])
    rows = []
    for item in selected.probe.variants(selection):
        row = dict(name=item["name"], status="NOT_QUALIFIED", command_return_code=0,
                   actual_product_tests_executed=0)
        if item["name"] == variant["name"]:
            row.update(status=selected.probe.PROBE_PASS,
                enumeration_sha256=value["files"][item["name"] + ".enumeration.json"])
        rows.append(row)
        if item["name"] == variant["name"]: break
    return dict(protocol=selected.PROBE_PROTOCOL, status=selected.probe.PROBE_PASS,
        control_source_sha=value["probe_source_sha"], run_id=value["probe_run_id"],
        run_attempt=value["probe_run_attempt"], control_source_hashes=value["probe_control_sources"],
        original_source_sha=selected.probe.ORIGINAL_SOURCE, original_run_id=selected.probe.ORIGINAL_RUN,
        original_run_attempt=selected.probe.ORIGINAL_ATTEMPT, original_artifact_id=selected.probe.ARTIFACT_ID,
        original_artifact_sha256=selected.probe.OUTER_SHA, original_products_sha256=selected.probe.PRODUCTS_SHA,
        app_builds=0, actual_product_tests_executed=0, sdk06_accepted=False, release_accepted=False,
        full_matrix_accepted=False, control_sources_unchanged=True, original_products_unchanged=True,
        finished_at="SYNTHETIC_CONTROLLER_CONTROL_ONLY",
        owned_simulator_cleanup={action: dict(status="PASS", return_code=0) for action in ("shutdown", "delete")},
        restored_products=dict(entries=5007, status="ORIGINAL_BYTES_RESTORED_ENUMERATION_ONLY"),
        selection_contract=selection, probes=rows, qualified_variant=variant["name"])


def enumeration(enabled, disabled):
    return dict(errors=[], values=[dict(testPlan="AnytypeTests",
        enabledTests=[dict(identifier=name) for name in enabled],
        disabledTests=[dict(identifier=name) for name in disabled])])


def plan_fixture(root, selection, variant):
    path = root / "synthetic-test-admission.json"
    value = {"files": {"synthetic-original.json": hashlib.sha256(b"original").hexdigest()}}
    path.write_text(json.dumps(value)); (root / "synthetic-original.json").write_bytes(b"original")
    return selected.QualifiedSelectorPlan(admission_path=path, control=root, current_grammar_json="{}",
        _seal=selected._PLAN_SEAL, admission_sha256=selected.probe.sha(path), evidence=root,
        approved_json=json.dumps(value), selection_json=json.dumps(selection), variant_json=json.dumps(variant))


class QualifiedSelectorControls(unittest.TestCase):
    def test_api_replay_source_attempt_and_artifact_are_rejected(self):
        value = approved(); run, artifact = api_values(value)
        selected.original_api(run, artifact, value)
        mutations = [
            ("run", "run_attempt", 2), ("run", "head_sha", "d" * 40), ("run", "conclusion", "failure"),
            ("artifact", "expired", True), ("artifact", "digest", "sha256:" + "e" * 64),
            ("artifact", "size_in_bytes", 101)]
        for owner, key, wrong in mutations:
            with self.subTest(owner=owner, key=key):
                r, a = copy.deepcopy(run), copy.deepcopy(artifact)
                (r if owner == "run" else a)[key] = wrong
                with self.assertRaises(ValueError): selected.original_api(r, a, value)

    def test_actual_source_binds_all23_and_seven_exclusions(self):
        source, selection = source_selection()
        self.assertEqual((len(selection["selected"]), len(selection["excluded"])), (23, 7))
        self.assertEqual(sum(not name.endswith("()") for name in selection["excluded"]), 3)
        for key, value in [("expected_methods", 22), ("declared_invocations", 31)]:
            bad = copy.deepcopy(source); bad[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): selected.selection_from_source(bad)
        bad = copy.deepcopy(source)
        first = next(iter(bad["source_hashes"])); bad["source_hashes"][first] = "0" * 64
        with self.assertRaises(ValueError): selected.selection_from_source(bad)
        bad = copy.deepcopy(source); bad["unselected_existing_methods"].pop()
        with self.assertRaises(ValueError): selected.selection_from_source(bad)

    def test_failed_probe_product_claims_and_unqualified_cleanup_are_rejected(self):
        _, selection = source_selection(); value = approved(); receipt = synthetic_record(value, selection)
        selected.qualified_record(receipt, value, selection)
        for key, wrong in [("status", selected.probe.PROBE_FAIL), ("app_builds", 1),
                           ("actual_product_tests_executed", 1), ("sdk06_accepted", True),
                           ("original_source_sha", "e" * 40), ("control_sources_unchanged", False)]:
            bad = copy.deepcopy(receipt); bad[key] = wrong
            with self.subTest(field=key), self.assertRaises(ValueError):
                selected.qualified_record(bad, value, selection)
        bad = copy.deepcopy(receipt); bad["owned_simulator_cleanup"]["delete"]["status"] = "FAIL"
        with self.assertRaises(ValueError): selected.qualified_record(bad, value, selection)

    def test_unexecuted_or_reordered_variant_is_not_a_qualified_plan(self):
        _, selection = source_selection(); value = approved("parameter-signature-terminal-parens-cli")
        receipt = synthetic_record(value, selection)
        selected.qualified_record(receipt, value, selection)
        for rows in [receipt["probes"][1:], list(reversed(receipt["probes"])), []]:
            bad = copy.deepcopy(receipt); bad["probes"] = rows
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                selected.qualified_record(bad, value, selection)
        bad = copy.deepcopy(receipt); bad["probes"][0]["status"] = selected.probe.PROBE_PASS
        with self.assertRaises(ValueError): selected.qualified_record(bad, value, selection)

    def test_current_enumeration_and_execution_preserve_identical_qualified_cli(self):
        source, selection = source_selection()
        for variant in selected.probe.variants(selection):
            with self.subTest(variant=variant["name"]), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); evidence = root / "evidence"; evidence.mkdir()
                plan = plan_fixture(root, selection, variant)
                original = root / "current.xctestrun"
                original.write_bytes(plistlib.dumps({"__xctestrun_metadata__": {"FormatVersion": 2},
                    "TestConfigurations": [{"TestTargets": [{"BlueprintName": "AnytypeTests",
                        "TestHostPath": "__TESTROOT__/App.app", "TestBundlePath": "__TESTROOT__/Tests.xctest",
                        "TestingEnvironmentVariables": {"UNCHANGED": "real-current-injection"}}]}]}))
                before = original.read_bytes(); calls = []
                class Runner:
                    def __init__(self, *args): pass
                    def run(self, argv, label, timeout):
                        calls.append(argv)
                        if label.endswith("discovery"):
                            enabled, disabled = selection["declarations"], []
                        else: enabled, disabled = selection["selected"], selection["excluded"]
                        output = Path(argv[argv.index("-test-enumeration-output-path") + 1])
                        output.write_text(json.dumps(enumeration(enabled, disabled)))
                        return output, {"return_code": 0}
                base = ["xcodebuild", "test-without-building", "-xctestrun", str(original),
                        "-destination", "platform=iOS Simulator,id=" + UDID, "-parallel-testing-enabled", "NO"]
                with mock.patch.object(selected.probe, "Commands", Runner):
                    result = plan.enumerate_current(APP, base, evidence, current.lane.shared, source)
                wanted = plan.arguments()
                self.assertEqual(plan.execution_arguments(result), wanted)
                self.assertEqual([x for x in calls[1] if x.startswith(("-only-testing:", "-skip-testing:"))], wanted)
                self.assertEqual(original.read_bytes(), before)
                bad = copy.deepcopy(result); bad["qualified_cli_arguments"] = wanted[:-1]
                with self.assertRaises(ValueError): plan.execution_arguments(bad)
                self.assertTrue(all("-enumerate-tests" in c and "build-for-testing" not in c for c in calls))

    def test_current_missing_parameterized_method_blocks_any_execution_arguments(self):
        source, selection = source_selection()
        missing = next(name for name in selection["selected"] if not name.endswith("()"))
        payload = enumeration([name for name in selection["selected"] if name != missing],
                              selection["excluded"] + [missing])
        with self.assertRaises(ValueError): selected.probe.qualify_enumeration(payload, selection)

    def test_unsealed_plan_and_changed_original_evidence_are_rejected(self):
        _, selection = source_selection()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); plan = plan_fixture(root, selection, selected.probe.variants(selection)[0])
            plan.verify()
            bad = copy.copy(plan); object.__setattr__(bad, "_seal", object())
            with self.assertRaises(ValueError): bad.verify()
            (root / "synthetic-original.json").write_bytes(b"changed")
            with self.assertRaises(ValueError): plan.arguments()

    def test_original_command_cannot_change_exclusions_or_owned_process_identity(self):
        _, selection = source_selection(); variant = selected.probe.variants(selection)[0]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); log = root / "original.log"; log.write_text("synthetic original enumeration output")
            argv = selected.probe.enumeration_command(root / ("SDK06-nonce-" + variant["name"] + ".xctestrun"),
                UDID, root / (variant["name"] + ".enumeration.json"), root / (variant["name"] + ".xcresult"), variant)
            command = dict(argv=argv, worker_pid=92001, return_code=0, owned_group_cleanup="TERM_THEN_KILL")
            row = {**command, "name": "enumerate-" + variant["name"], "output_sha256": selected.probe.sha(log),
                   "owned_group_quiescence": dict(status="PASS", pgid=92001, live_members=0)}
            receipt = dict(commands=[row], owned_simulator=dict(udid=UDID, nonce="nonce"))
            selected.validate_original_command(receipt, {}, command, log, variant)
            bad = copy.deepcopy(receipt); bad["commands"][0]["owned_group_quiescence"]["pgid"] = 92002
            with self.assertRaises(ValueError): selected.validate_original_command(bad, {}, command, log, variant)
            badcommand = copy.deepcopy(command)
            badcommand["argv"] = [x for x in argv if not x.startswith("-skip-testing:")]
            bad = copy.deepcopy(receipt); bad["commands"][0]["argv"] = badcommand["argv"]
            with self.assertRaises(ValueError): selected.validate_original_command(bad, {}, badcommand, log, variant)

    def test_original_git_closure_and_current_result_validator_are_bound(self):
        names = ["Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py",
                 "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py"]
        originals = {name: (APP / name).read_bytes() for name in names}
        value = dict(probe_source_sha="c" * 40,
                     probe_control_sources={name: hashlib.sha256(raw).hexdigest() for name, raw in originals.items()})
        batch = b"".join(("0" * 40 + " blob " + str(len(originals[name])) + "\n").encode() +
                         originals[name] + b"\n" for name in sorted(names))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, raw in originals.items():
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            with mock.patch.object(selected.subprocess, "run", return_value=SimpleNamespace(stdout=batch)):
                selected.original_control_sources(root, value)
                component = root / names[1]
                component.write_text(component.read_text().replace("def validate_results(", "def altered_validate_results(", 1))
                with self.assertRaises(ValueError): selected.original_control_sources(root, value)
            wrong = batch.replace(b"Probe Xcode27", b"Probe Xcode99", 1)
            with mock.patch.object(selected.subprocess, "run", return_value=SimpleNamespace(stdout=wrong)):
                with self.assertRaises(ValueError): selected.original_control_sources(root, value)

    def test_missing_real_committed_admission_stops_before_api_or_work_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); evidence = root / "evidence"; evidence.mkdir(); work = root / "work"
            with mock.patch.object(current, "current_identity", return_value={}), \
                 mock.patch.object(current.probe, "Commands") as commands:
                with self.assertRaises(ValueError): current.admit(root, work, evidence)
            commands.assert_not_called(); self.assertFalse(work.exists())

    def test_extraction_accepts_only_pinned_bytes_and_rejects_unsafe_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); archive = root / "probe.zip"; raw = b'{"synthetic":true}'
            value = {"files": {"receipt.json": hashlib.sha256(raw).hexdigest()}}
            with zipfile.ZipFile(archive, "w") as packed: packed.writestr("receipt.json", raw)
            current.extract_probe_files(archive, root / "safe", value)
            self.assertEqual((root / "safe/receipt.json").read_bytes(), raw)
            with zipfile.ZipFile(archive, "w") as packed:
                packed.writestr("receipt.json", raw); packed.writestr("../unowned", b"bad")
            with self.assertRaises(ValueError): current.extract_probe_files(archive, root / "unsafe", value)
            self.assertFalse((root.parent / "unowned").exists())


if __name__ == "__main__":
    unittest.main()
