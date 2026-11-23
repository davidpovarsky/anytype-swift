"""Four new tagged-continuation controls; all Apple commands below are simulated.

Only retained source/proof metadata is read. No previous test method, Xcode,
product build, simulator command, GitHub request or runtime method is executed.
"""
from contextlib import ExitStack
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import sdk06_tagged_continuation as current
import sdk06_tagged_selector as tagged

APP = Path(__file__).resolve().parents[2]
UDID = "90000000-0000-4000-8000-000000000023"
BINDING = dict(source_sha="c" * 40, run_id="999000023", run_attempt="1")


def source_selection():
    contract = tagged.manifest(APP)
    names = [name for name in contract["source_inverses"] if name.endswith(".swift")]
    with tempfile.TemporaryDirectory() as directory:
        fixture = Path(directory)
        for name in names:
            path = fixture / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((APP / name).read_bytes())
        # Model the existing case-insensitive synchronized Xcode root in a
        # disposable Linux fixture only, never in the actual Git worktree.
        (fixture / "AnytypeTests").symlink_to("AnyTypeTests", target_is_directory=True)
        tracked = ("\0".join(names) + "\0").encode()
        with mock.patch.object(tagged.component.subprocess, "check_output", return_value=tracked):
            source = tagged.component.source_contract(fixture)
    return source, tagged.source_selection(source, contract)


def payload(enabled, disabled=(), plan="AnytypeTests"):
    return dict(errors=[], values=[dict(testPlan=plan,
        enabledTests=[dict(identifier=name) for name in enabled],
        disabledTests=[dict(identifier=name) for name in disabled])])


def products(root):
    directory = root / "Build/Products"
    app = directory / "Debug-Anytype-iphonesimulator/Anytype.app"
    test = app / "PlugIns/AnytypeTests.xctest"
    test.mkdir(parents=True)
    (app / "Anytype").write_bytes(b"synthetic-current-app-control")
    (test / "AnytypeTests").write_bytes(b"synthetic-current-test-control")
    configuration = directory / "Current.xctestrun"
    configuration.write_bytes(plistlib.dumps({
        "__xctestrun_metadata__": {"FormatVersion": 2},
        "TestConfigurations": [{"IsEnabled": True, "TestTargets": [{
            "BlueprintName": "AnytypeTests",
            "TestHostPath": "__TESTROOT__/Debug-Anytype-iphonesimulator/Anytype.app",
            "TestBundlePath": "__TESTROOT__/Debug-Anytype-iphonesimulator/Anytype.app/PlugIns/AnytypeTests.xctest",
            "TestingEnvironmentVariables": {"UNCHANGED": "original-current-injection"},
            "EnvironmentVariables": {"UNCHANGED_CURRENT": "original-value"}
        }]}]
    }))
    return configuration, app, app / "Anytype", test, test / "AnytypeTests"


def base(configuration):
    return ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
            "-destination", "platform=iOS Simulator,id=" + UDID, "-parallel-testing-enabled", "NO"]


def runner_type(selection, calls, *, selected=None, events=None):
    class Runner:
        def __init__(self, *args): pass
        def run(self, argv, label, timeout):
            calls.append(list(argv))
            assert timeout == 600 and "-enumerate-tests" in argv and "build-for-testing" not in argv
            if events is not None: events.append(label)
            if label.endswith("discovery"):
                enabled, disabled = selection["declarations"], []
            else:
                enabled = selection["selected"] if selected is None else selected
                disabled = sorted(set(selection["declarations"]) - set(enabled))
            path = Path(argv[argv.index("-test-enumeration-output-path") + 1])
            path.write_text(json.dumps(payload(enabled, disabled)))
            return path, {"return_code": 0}
    return Runner


class TaggedSDK06Controls(unittest.TestCase):
    def test_pending_tag_preserves_all_bodies_arguments_exclusions_and_target_membership(self):
        contract = tagged.manifest(APP)
        admitted = tagged.source_admission(APP)
        source, selection = source_selection()
        self.assertEqual(selection, contract["selection"])
        self.assertEqual((source["expected_methods"], source["declared_invocations"]), (23, 32))
        self.assertFalse(admitted["selector_qualified"])
        self.assertEqual(admitted["product_tests_executed_now"], 0)
        counts = {}
        for name, row in contract["source_inverses"].items():
            raw = (APP / name).read_bytes()
            recovered = tagged.recover_source(name, raw, contract)
            original = subprocess.check_output(
                ["git", "-C", str(APP), "show", contract["baseline_source_sha"] + ":" + name], timeout=30)
            self.assertEqual(recovered, original)
            if name.endswith(".swift"):
                counts[Path(name).stem] = raw.count((".tags(." + tagged.TAG + ")").encode())
                self.assertEqual(tagged.component.host.core_profile.inspect_declarations(raw.decode()),
                                 tagged.component.host.core_profile.inspect_declarations(recovered.decode()))
            else:
                before = ast.parse(recovered); after = ast.parse(raw)
                untouched = "validate_results" if name.endswith("shared_editor_existing_build.py") else "require_source_identity"
                extract = lambda tree: next(ast.dump(node, include_attributes=False) for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == untouched)
                self.assertEqual(extract(before), extract(after))
        self.assertEqual(counts, {"TextBlockFocusLifecycleTests": 10,
            "SimpleTableTextPersistenceTests": 11, "TorahRelatedReadAuthorityMappingTests": 2})
        focus = "AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift"
        raw = (APP / focus).read_bytes()
        for label, altered in (
            ("argument", raw.replace(b"arguments: [false, true]", b"arguments: [false, false]", 1)),
            ("body", raw + b"\n// unreviewed body/source change\n"),
            ("missing-tag", raw.replace((".tags(." + tagged.TAG + ")").encode(), b".tags(.wrongPendingTag)", 1)),
        ):
            with self.subTest(label=label), self.assertRaises(ValueError):
                tagged.recover_source(focus, altered, contract)
        project = (APP / contract["project_membership"]["path"]).read_bytes()
        membership = tagged.project_membership(project, contract)
        self.assertEqual(membership["target"], "AnytypeTests")
        self.assertFalse(membership["explicit_project_edit_required"])
        with self.assertRaises(ValueError):
            tagged.project_membership(project.replace(b"path = AnytypeTests;", b"path = WrongTests;", 1), contract)

    def test_historical_view_retains_only_its_original_scope_and_rejects_dependency_or_member_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            view = Path(directory) / "historical"
            result = tagged.historical_retained_view(APP, view)
            self.assertEqual(result["source_scope"], "HISTORICAL_RETAINED_VIEW")
            self.assertFalse(result["historical_view_is_app_build_source"])
            self.assertFalse(result["current_selector_qualified"])
            self.assertEqual(result["old_controller_methods_executed_now"], 0)
            historical = result["historical_original_receipt"]
            self.assertEqual(historical["source_root"], str(view.resolve()))
            self.assertEqual(historical["current_control_methods"], 98)
            self.assertEqual(historical["controller_methods_executed_now"], 0)
            self.assertEqual(historical["original_lane_conclusions"],
                             {"45096079315": "FAIL", "45087685319": "failure"})
            contract = tagged.manifest(APP)
            for name, row in contract["source_inverses"].items():
                self.assertEqual(result["actual_current_inputs"][name]["sha256"], row["after_sha256"])
                self.assertEqual(hashlib.sha256((view / name).read_bytes()).hexdigest(), row["before_sha256"])
                self.assertNotEqual(row["before_sha256"], row["after_sha256"])
            proof = view / "Tools/PinkhaSimulatorGate/text_native_ack.py"
            original = proof.read_bytes(); original_mode = proof.stat().st_mode
            proof.write_bytes(original + b"\n")
            with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)
            proof.write_bytes(original)
            proof.chmod(0o755 if not original_mode & 0o111 else 0o644)
            with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)
            proof.chmod(original_mode & 0o777)
            extra = view / "unreviewed.txt"; extra.write_text("not an admitted member")
            with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)
            extra.unlink()
            link = view / "unreviewed-link"; link.symlink_to(proof)
            with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)
            link.unlink()
            read = tagged.read_regular
            def changed(root, relative, *args):
                data, mode = read(root, relative, *args)
                if Path(root) == APP and relative == "Tools/PinkhaSimulatorGate/text_native_ack.py":
                    return data + b"\n", mode
                return data, mode
            with mock.patch.object(tagged, "read_regular", side_effect=changed):
                with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)
            with self.assertRaises(ValueError): tagged.historical_retained_view(APP, APP)
            composed = tagged.composition.contract(APP, tagged.read_regular)
            retained = result["retained_current_shared_composition"]
            self.assertEqual(retained["original_actual_loaded_count"], 9)
            self.assertEqual(retained["original_source_inventory_count"], 300)
            self.assertFalse(retained["original_inventory_is_exercised_coverage"])
            self.assertFalse(retained["workflow_view_executed"])
            self.assertFalse(retained["current_selector_qualified"])
            self.assertEqual(retained["old_controller_methods_executed_now"], 0)
            self.assertEqual(retained["coherent_reader_caller_scope"],
                             "STATIC_CALLER_BINDING_NOT_AN_ACTUAL_LOADED_METHOD_CLAIM")
            self.assertEqual(len(retained["original_coherent_methods"]), 2)
            central = ".github/workflows/torah-inspector-ipados27.yml"
            for name, row in composed["historical_inverses"].items():
                self.assertEqual(result["actual_current_inputs"][name]["sha256"], row["after_sha256"])
                self.assertEqual(hashlib.sha256((view / name).read_bytes()).hexdigest(), row["before_sha256"])
            self.assertEqual(retained["executing_workflows"][central],
                             composed["historical_inverses"][central]["after_sha256"])
            self.assertNotEqual(retained["executing_workflows"][central],
                                hashlib.sha256((view / central).read_bytes()).hexdigest())
            for name, row in retained["original_actual_loaded_source_views"].items():
                self.assertEqual(row["actual_current_sha256"], hashlib.sha256((APP / name).read_bytes()).hexdigest())
                original = subprocess.check_output(["git", "-C", str(APP), "show",
                    composed["root_qualification"]["source_commit"] + ":" + name], timeout=30)
                self.assertEqual(row["original_loaded_sha256"], hashlib.sha256(original).hexdigest())
            prefix = tagged.composition.PREFIX
            empty = prefix + "root-audit.stderr"
            self.assertEqual(tagged.read_regular(APP, empty)[0], b"")
            negative_paths = [
                central, ".github/workflows/pinkha-sdk06-tagged-continuation.yml",
                "Tools/PinkhaSimulatorGate/coherent_controller_sources.py",
                "Tools/PinkhaSimulatorGate/run_owned_single_lane.py",
                "Tools/PinkhaSimulatorGate/wave15_batch.py",
                prefix + "attempt1/events.json", prefix + "attempt1/controls.log",
                prefix + "attempt1/source-before.json", empty, tagged.composition.MANIFEST,
            ]
            for target in negative_paths:
                def drift(root, relative, *args):
                    data, mode = read(root, relative, *args)
                    return (data + b"\n", mode) if Path(root) == APP and relative == target else (data, mode)
                with self.subTest(composed_dependency=target):
                    with mock.patch.object(tagged, "read_regular", side_effect=drift):
                        with self.assertRaises(ValueError): tagged.historical_retained_view(APP, view)

    def test_actual_current_tag_enumeration_binds_exact23_and_one_use_execution_argv(self):
        source, selection = source_selection()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration, *_ = products(root)
            original = configuration.read_bytes()
            evidence = root / "evidence"; evidence.mkdir()
            plan = tagged.load_plan(APP, BINDING); calls = []
            with mock.patch.object(tagged.probe, "Commands", runner_type(selection, calls)):
                observed = plan.enumerate_current(APP, base(configuration), evidence, current.lane.shared, source)
            self.assertEqual(len(calls), 2)
            self.assertNotIn("-only-testing-tags", calls[0])
            start = calls[1].index("-only-testing-tags")
            self.assertEqual(calls[1][start:start+2], ["-only-testing-tags", tagged.TAG])
            self.assertEqual([arg for arg in calls[1] if arg.startswith("-only-testing:")],
                ["-only-testing:AnytypeTests/" + suite for suite in tagged.component.SUITES])
            self.assertEqual(configuration.read_bytes(), original)
            self.assertEqual(observed["selected_identifiers"], selection["selected"])
            selected_base = base(Path(observed["selected_configuration"]["path"]))
            for field, value in (("run_id", "999000024"), ("source_sha", "d" * 40), ("run_attempt", "2")):
                wrong = copy.deepcopy(observed); wrong["binding"][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    plan.execution_arguments(wrong, selected_base)
            wrong_base = list(selected_base)
            wrong_base[wrong_base.index("-destination") + 1] = "platform=iOS Simulator,id=90000000-0000-4000-8000-000000000024"
            with self.assertRaises(ValueError): plan.execution_arguments(observed, wrong_base)
            selected_output = Path(observed["current_enumeration"]["selected"]["output_path"])
            raw = selected_output.read_bytes(); selected_output.write_bytes(raw + b"\n")
            with self.assertRaises(ValueError): plan.execution_arguments(observed, selected_base)
            selected_output.write_bytes(raw)
            self.assertEqual(plan.execution_arguments(observed, selected_base), tagged.selection_arguments())
            with self.assertRaises(ValueError): plan.execution_arguments(observed, selected_base)
            with self.assertRaises(ValueError):
                plan.enumerate_current(APP, base(configuration), evidence, current.lane.shared, source)
        bad = [
            payload(selection["selected"] + selection["excluded"][:3], selection["excluded"][3:]),
            payload(selection["selected"][:-1], selection["excluded"] + selection["selected"][-1:]),
            payload(selection["selected"] + selection["selected"][:1], selection["excluded"]),
            payload(selection["selected"], selection["excluded"][1:]),
            payload(selection["selected"], selection["excluded"], plan="Anytype"),
        ]
        for index, value in enumerate(bad):
            with self.subTest(negative=index), self.assertRaises(ValueError):
                tagged.qualify_enumeration(value, selection)

    def test_one_current_build_archives_then_refuses_all_product_phases_on_wrong_tag_enumeration(self):
        source, selection = source_selection()
        plan = tagged.load_plan(APP, BINDING)
        lane = current.lane
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); derived = root / "derived"; evidence = root / "evidence"
            evidence.mkdir(); (evidence / "preflight").mkdir(); (evidence / "heart").mkdir()
            configuration, built, executable, test_bundle, test_executable = products(derived)
            (derived / "SourcePackages/checkouts/TorahInspectorKit").mkdir(parents=True)
            (evidence / "preflight/preflight.json").write_text(json.dumps(dict(
                status="PREFLIGHT_PASS_UI_NOT_RUN", **BINDING, selected=dict(ipad=dict(
                    udid=UDID, name="Pinkha-UI27-" + BINDING["run_id"] + "-ipad")))))
            (evidence / "heart/heart-installation.json").write_text("{}")
            args = SimpleNamespace(app=APP, evidence=evidence, derived=derived, lane="hanlin-native",
                device="ipad", language="en", include_text_native_ack=True, include_shared_editor=True,
                sdk06_tagged_selection_plan=plan,
                runtime_profile=current.original.RUNTIME_PROFILE, heart_source_run_id=current.original.PRODUCER_RUN)
            events, commands, enumeration_commands = [], [], []
            def command(argv, *args, **kwargs):
                commands.append(list(argv))
                if "build-for-testing" in argv: events.append("current-build")
            def archive(*args, **kwargs):
                events.append("original-products-preserved")
                self.assertEqual(kwargs["source_sha"], BINDING["source_sha"])
                return {"status": "SYNTHETIC_CAPTURE_CONTROL_ONLY"}
            def git(path, *arguments):
                if Path(path).name == "TorahInspectorKit": return lane.shared.KIT
                if arguments == ("rev-parse", "HEAD"): return BINDING["source_sha"]
                if arguments == ("branch", "--show-current"): return lane.SHARED_BRANCH
                raise AssertionError("unexpected Git command")
            def patch(owner, name, **kwargs):
                return stack.enter_context(mock.patch.object(owner, name, **kwargs))
            stack.enter_context(mock.patch.dict(os.environ, dict(GITHUB_SHA=BINDING["source_sha"],
                GITHUB_RUN_ID=BINDING["run_id"], GITHUB_RUN_ATTEMPT="1",
                GITHUB_REF="refs/heads/" + lane.SHARED_BRANCH)))
            patch(lane.platform, "system", return_value="Darwin")
            patch(lane, "source_methods", return_value=None)
            patch(lane.text_native_ack, "source_contract", return_value={"status": "SOURCE_CONTROL_ONLY"})
            patch(tagged.component, "source_contract", return_value=source)
            patch(lane.shared, "git", side_effect=git)
            patch(lane.shared, "runtime_binding", return_value={"native_marker": "synthetic-marker"})
            patch(lane.shared, "candidate_identity", return_value={"hashes": {"synthetic": "0" * 64}})
            patch(lane.shared, "command", side_effect=command)
            patch(lane.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout='("en")', stderr=""))
            patch(lane.shared, "prepare_source_cache", return_value=None)
            patch(lane.shared, "verify_signed_simulator", return_value=None)
            patch(lane.shared, "verify_runtime_copies", return_value=None)
            patch(lane.shared, "code_carriers", return_value={"sha256": "0" * 64})
            patch(lane.shared, "test_configuration", return_value=configuration)
            patch(lane.early_build_products, "capture", side_effect=archive)
            patch(tagged.component.host, "xctest_products",
                  return_value=(built, executable, test_bundle, test_executable))
            xctest = patch(lane.shared, "run_xctest")
            later = patch(lane.shared, "run_selection")
            ui_build = patch(lane.shared, "ui_only_project")
            # This models the concrete previous failure shape: 26 != 23. It is
            # a fixture, never an asserted result of the unrun compiled tag.
            patch(tagged.probe, "Commands", new=runner_type(selection, enumeration_commands,
                selected=selection["selected"] + [name for name in selection["excluded"] if not name.endswith("()")], events=events))
            receipt = {}
            with self.assertRaises(ValueError):
                lane.execute(args, receipt)
            self.assertEqual(events, ["current-build", "original-products-preserved",
                                      "tagged-discovery", "tagged-selected"])
            build_commands = [argv for argv in commands if "build-for-testing" in argv]
            self.assertEqual(len(build_commands), 1)
            self.assertEqual(build_commands[0][build_commands[0].index("-configuration") + 1], "Debug-Anytype")
            self.assertTrue(receipt["native_build_succeeded"])
            self.assertEqual(receipt["shared_editor_components"]["status"], "FAIL")
            self.assertEqual(receipt["shared_editor_components"]["phase"], "ENUMERATION_PRECHECK")
            xctest.assert_not_called(); later.assert_not_called(); ui_build.assert_not_called()
            self.assertNotIn("preparation", receipt)
            self.assertNotIn("ui", receipt)
            self.assertTrue((evidence / "shared-editor-components/tagged-selected.enumeration.json").is_file())


if __name__ == "__main__":
    unittest.main()
