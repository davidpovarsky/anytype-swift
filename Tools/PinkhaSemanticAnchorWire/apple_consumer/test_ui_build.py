"""Only new build-preservation/selection controls; never Apple product evidence."""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import consumer_contract as proof
import run as consumer
import ui_build

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
UDID = "11111111-1111-1111-1111-111111111111"
BINDING = dict(sourceSHA="a"*40, runID="123", runAttempt="1", nonce="c"*32)


def frozen_source(app):
    plan = json.loads((HERE / "ui-build-plan.json").read_bytes())
    raw = subprocess.check_output(["git", "-C", str(ROOT), "show", ui_build.ORIGIN + ":" + ui_build.SOURCE_PLAN])
    source = json.loads(raw)
    names = set(source["files"]) | {ui_build.SOURCE_PLAN}
    names.update(ui_build.PROJECT + "/" + name for name in plan["project_files_sha256"])
    inputs = {}
    for name in names:
        value = subprocess.check_output(["git", "-C", str(ROOT), "show", ui_build.ORIGIN + ":" + name])
        path = app / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
        inputs[name] = hashlib.sha256(value).hexdigest()
    return plan, inputs


def synthetic_products(derived, *, native=False):
    products = derived / "Build/Products"; products.mkdir(parents=True)
    descriptor = products / ("original-native.xctestrun" if native else "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun")
    if native:
        descriptor.write_bytes(b"synthetic original native descriptor")
        binary = products / "original-executable"
    else:
        host = "__TESTROOT__/Debug-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
        value = {"__xctestrun_metadata__": {"FormatVersion": 1}, ui_build.BLUEPRINT: {
            "BlueprintName": ui_build.BLUEPRINT, "IsUITestBundle": True,
            "TestHostPath": host, "TestBundlePath": "__TESTHOST__/PlugIns/" + ui_build.BLUEPRINT + ".xctest"}}
        descriptor.write_bytes(plistlib.dumps(value))
        binary = products / host.removeprefix("__TESTROOT__/") / "PlugIns" / (ui_build.BLUEPRINT + ".xctest") / ui_build.BLUEPRINT
        binary.parent.mkdir(parents=True)
    binary.write_bytes(b"synthetic original executable; not Apple evidence")
    binary.chmod(0o755)
    return descriptor, binary


class BuildOnlyControls(unittest.TestCase):
    def test_exact_native_cli_and_actual_test_plan_admit_only_one_method(self):
        descriptor = Path("/owned/Build/Products/bound.xctestrun")
        for option in [dict(enumeration=Path("/evidence/enumeration.json")), dict(result=Path("/evidence/actual.xcresult"))]:
            command = consumer.xctest_command(descriptor, UDID, **option)
            self.assertEqual(command.count("-only-testing"), 1)
            self.assertEqual(command[command.index("-only-testing")+1], proof.SELECTOR)
            self.assertEqual(command[command.index("-xctestrun")+1], str(descriptor))
            self.assertNotIn("build-for-testing", command)
            self.assertEqual("-enumerate-tests" in command, "enumeration" in option)
        with patch.object(consumer.component, "enumerated_identifiers",
                          return_value=("AnytypeTests", {proof.SELECTOR}, set())):
            self.assertEqual(consumer.exact_native_enumeration({})["plan"], "AnytypeTests")
        for value in [("Anytype", {proof.SELECTOR}, set()),
                      ("AnytypeTests", set(), set()),
                      ("AnytypeTests", {proof.SELECTOR, "AnytypeTests/Other/test"}, set()),
                      ("AnytypeTests", {proof.SELECTOR}, {proof.SELECTOR})]:
            with self.subTest(value=value), patch.object(consumer.component, "enumerated_identifiers", return_value=value), \
                 self.assertRaises(ValueError):
                consumer.exact_native_enumeration({})

    def test_consumer_quiescence_retains_profile_timeouts_and_late_actual_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); receipt = {}
            error = RuntimeError("late zero-member observation")
            error.timeout_observations = [{"observation": 1, "timeout_seconds": 2}]
            error.quiescence_observation = dict(status="FAIL_DEADLINE", live_members=0, observations=2)
            def worker(argv, cwd, path, timeout):
                path.write_text("synthetic successful original command\n")
                record = dict(worker_pid=987654, return_code=0, owned_group_cleanup="TERM_THEN_KILL")
                proof.save(path.with_suffix(".command.json"), record)
                return record
            with patch.object(consumer.owned, "run_worker_command", side_effect=worker), \
                 patch.object(consumer.supervisor, "verify_owned_group_stopped", side_effect=error) as verify, \
                 self.assertRaises(RuntimeError):
                consumer.Commands(root, root, receipt).run(["synthetic"], "owned-command")
            self.assertEqual(verify.call_args.kwargs, {"cleanup_profile": "semantic-page154"})
            failure = json.loads((root/"execution.json").read_bytes())["commands"][0]["quiescence_failure"]
            self.assertEqual(failure["timeout_observations"], error.timeout_observations)
            self.assertEqual(failure["quiescence_observation"], error.quiescence_observation)

    def fixture(self, temporary, failure=None):
        app = Path(temporary) / "app"; app.mkdir()
        work, evidence = app/"work", app/"evidence"; work.mkdir(); evidence.mkdir()
        plan, inputs = frozen_source(app)
        ui_build.read_plan(app, inputs)
        calls = []
        receipt = dict(native_boundary_status=proof.PASS, actual_product_methods_passed=1)
        def run(argv, name, timeout):
            calls.append((argv, name, timeout))
            if failure == "build": raise RuntimeError("synthetic UI build failed")
            derived = Path(argv[argv.index("-derivedDataPath")+1])
            synthetic_products(derived)
        runner = SimpleNamespace(run=run)
        shared = SimpleNamespace(ui_only_project=consumer.shared.ui_only_project,
            test_configuration=lambda products, blueprint: products/"PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun")
        return app, work, evidence, plan, inputs, calls, receipt, runner, shared

    def test_ui_build_preserves_v1_runner_and_native_boundary_without_product_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, work, evidence, plan, _, calls, receipt, runner, shared = self.fixture(temporary)
            result = ui_build.build_mounted_ui(runner, app, work, evidence, BINDING, consumer.BUILD_FLAGS,
                                               plan, shared, receipt, UDID)
            self.assertEqual(len(calls), 1)
            self.assertIn("build-for-testing", calls[0][0])
            self.assertNotIn("test-without-building", calls[0][0])
            self.assertIn("-only-testing:"+ui_build.SELECTOR, calls[0][0])
            self.assertEqual(calls[0][0][calls[0][0].index("-scheme")+1], "PinkhaPrebuiltUI")
            self.assertEqual(result["status"], ui_build.STATUS)
            self.assertEqual(result["descriptor"]["format_version"], 1)
            self.assertEqual(result["preparation_executions"], 0); self.assertEqual(result["ui_executions"], 0)
            self.assertEqual(result["acceptance"], "NOT_RUN")
            self.assertEqual(result["early_products"]["archive_path"], "ui-runner/"+ui_build.SCOPE+"/BuildProducts.tar.gz")
            self.assertEqual(result["original_xctestrun"]["path"], "ui-runner/original.xctestrun")
            self.assertEqual(receipt["native_boundary_status"], proof.PASS)
            self.assertEqual(receipt["actual_product_methods_passed"], 1)
            generated = (app/result["generated_project"]/"project.pbxproj").read_text()
            self.assertIn("SemanticAnchorPage154MountedUITests.swift in Sources", generated)
            self.assertNotIn("Anytype.xcodeproj", generated)
            self.assertEqual(ui_build.project_files(app/ui_build.PROJECT), plan["project_files_sha256"])

    def test_ui_admission_failure_keeps_successful_original_archive_and_native_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, work, evidence, plan, _, calls, receipt, runner, shared = self.fixture(temporary)
            with patch.object(ui_build, "descriptor_summary", side_effect=ValueError("synthetic admission failed")), \
                 self.assertRaises(ValueError):
                ui_build.build_mounted_ui(runner, app, work, evidence, BINDING, consumer.BUILD_FLAGS,
                                          plan, shared, receipt, UDID)
            self.assertEqual(receipt["ui_runner_build"]["status"], "FAIL")
            archive = evidence/receipt["ui_runner_build"]["early_products"]["archive_path"]
            self.assertTrue(archive.is_file())
            self.assertEqual(proof.digest(archive), receipt["ui_runner_build"]["early_products"]["archive_sha256"])
            self.assertEqual(receipt["native_boundary_status"], proof.PASS)
            self.assertEqual(receipt["actual_product_methods_passed"], 1)

    def test_failed_ui_compile_cannot_relabel_or_repeat_prior_native_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            app, work, evidence, plan, _, calls, receipt, runner, shared = self.fixture(temporary, failure="build")
            with self.assertRaisesRegex(RuntimeError, "UI build failed"):
                ui_build.build_mounted_ui(runner, app, work, evidence, BINDING, consumer.BUILD_FLAGS,
                                          plan, shared, receipt, UDID)
            self.assertEqual(len(calls), 1)
            self.assertEqual(receipt["native_boundary_status"], proof.PASS)
            self.assertNotIn("early_products", receipt["ui_runner_build"])
            self.assertEqual(receipt["ui_runner_build"]["status"], "FAIL")

    def test_source_plan_requires_frozen_registered_ui_project_before_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            plan, inputs = frozen_source(app)
            ui_build.read_plan(app, inputs)
            project = app/ui_build.PROJECT/"project.pbxproj"
            original = project.read_bytes()
            project.write_bytes(original.replace(b"SemanticAnchorPage154MountedUITests.swift in Sources", b"Unregistered.swift in Sources"))
            with self.assertRaises(ValueError): ui_build.read_plan(app, inputs)
            project.write_bytes(original)
            (project.parent/"extra-build-input").write_text("unexpected")
            with self.assertRaises(ValueError): ui_build.read_plan(app, inputs)

    def product_fixture(self, root):
        derived, evidence = root/"derived", root/"evidence"; evidence.mkdir()
        descriptor, binary = synthetic_products(derived, native=True)
        preservation = consumer.early_build_products.capture(derived, evidence, source_sha=BINDING["sourceSHA"],
            run_id=BINDING["runID"], run_attempt=BINDING["runAttempt"], build_flags=consumer.BUILD_FLAGS,
            scope="semantic-page154")
        return derived, evidence, preservation, descriptor, binary

    def test_original_product_guard_rejects_bytes_modes_missing_and_extra_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            derived, evidence, preservation, descriptor, binary = self.product_fixture(Path(temporary))
            check = lambda: ui_build.verify_preserved_products(derived, evidence, preservation, BINDING, consumer.BUILD_FLAGS)
            self.assertEqual(check()["status"], "ALL_ORIGINAL_PRODUCT_ENTRIES_UNCHANGED")
            original = binary.read_bytes()
            binary.write_bytes(b"changed")
            with self.assertRaises(ValueError): check()
            binary.write_bytes(original); binary.chmod(0o644)
            with self.assertRaises(ValueError): check()
            binary.chmod(0o755)
            saved = descriptor.read_bytes(); descriptor.unlink()
            with self.assertRaises(ValueError): check()
            descriptor.write_bytes(saved)
            extra = binary.with_name("unreviewed-extra"); extra.write_bytes(b"extra")
            with self.assertRaises(ValueError): check()
            extra.unlink(); self.assertEqual(check()["entries"], preservation["entries"])

    def test_only_exact_bound_native_descriptor_addition_is_permitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            derived, evidence, preservation, _, binary = self.product_fixture(Path(temporary))
            extra = binary.parent/("Page154-"+BINDING["nonce"]+".xctestrun"); extra.write_bytes(b"bound")
            additions = {extra.relative_to(derived).as_posix(): proof.digest(extra)}
            ui_build.verify_preserved_products(derived, evidence, preservation, BINDING, consumer.BUILD_FLAGS,
                                               descriptor_additions=additions)
            extra.write_bytes(b"changed-bound")
            with self.assertRaises(ValueError):
                ui_build.verify_preserved_products(derived, evidence, preservation, BINDING, consumer.BUILD_FLAGS,
                                                   descriptor_additions=additions)
            with self.assertRaises(ValueError):
                ui_build.verify_preserved_products(derived, evidence, preservation, BINDING, consumer.BUILD_FLAGS,
                                                   descriptor_additions={"Build/Products/another.xctestrun": "a"*64})

    def test_ui_descriptor_formats_keep_exact_one_compiled_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            derived = Path(temporary)
            descriptor, binary = synthetic_products(derived)
            value = plistlib.loads(descriptor.read_bytes())
            target = value[ui_build.BLUEPRINT]
            value = {"__xctestrun_metadata__": {"FormatVersion": 2},
                     "TestConfigurations": [{"TestTargets": [target]}]}
            descriptor.write_bytes(plistlib.dumps(value))
            self.assertEqual(ui_build.descriptor_summary(descriptor, derived/"Build/Products")["format_version"], 2)
            value["TestConfigurations"][0]["TestTargets"].append(copy.deepcopy(target))
            descriptor.write_bytes(plistlib.dumps(value))
            with self.assertRaises(ValueError): ui_build.descriptor_summary(descriptor, derived/"Build/Products")


if __name__ == "__main__":
    unittest.main()
