"""Two new offline controls for original-native admission and UI-only continuation."""
from __future__ import annotations

import argparse
import base64
import copy
from contextlib import ExitStack
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tarfile
import types
import unittest
from unittest import mock
import zipfile

import run_ui27 as shared
import run_wave15_acceptance as lane
import sdk06_enumeration_probe as probe
import sdk06_original_native as native
import sdk06_original_native_descriptors as descriptor_additions
import sdk06_original_native_selection as native_selection
import sdk06_original_native_continuation as continuation
import sdk06_original_tagged_selector as selector
import shared_editor_existing_build as component

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "docs/validation/20261123-sdk06-original-native-continuation/fixtures"


def control_root(name):
    result = Path(os.environ["PINKHA_SDK06_NEW_CONTROL_ARTIFACTS"]) / name
    result.mkdir(parents=True, exist_ok=False)
    return result


def fixed():
    return json.loads((ROOT / native.ADMISSION).read_bytes())


class OriginalNativeContinuationControls(unittest.TestCase):
    def test_fixed_original_origin_and_exact_restoration_refuse_source_or_entry_drift(self):
        output = control_root("original-origin")
        contract = fixed()
        run = {"id": int(native.RUN), "run_attempt": int(native.ATTEMPT), "head_sha": native.SOURCE,
               "head_branch": contract["original_branch"], "event": "workflow_dispatch",
               "status": "completed", "conclusion": "failure",
               "repository": {"full_name": native.REPOSITORY},
               "path": ".github/workflows/torah-inspector-ipados27.yml"}
        artifact = {"id": contract["artifact"]["id"], "name": contract["artifact"]["name"],
                    "size_in_bytes": contract["artifact"]["bytes"],
                    "digest": "sha256:" + contract["artifact"]["sha256"], "expired": False,
                    "workflow_run": {"id": int(native.RUN), "head_sha": native.SOURCE,
                                     "head_branch": contract["original_branch"]}}
        native.verify_api(run, artifact, contract)
        for label, target, key, value in (
                ("wrong_source", "run", "head_sha", "f" * 40),
                ("wrong_attempt", "run", "run_attempt", 2),
                ("relabelled_success", "run", "conclusion", "success"),
                ("wrong_artifact", "artifact", "id", contract["artifact"]["id"] + 1),
                ("expired", "artifact", "expired", True),
                ("wrong_size", "artifact", "size_in_bytes", contract["artifact"]["bytes"] - 1)):
            with self.subTest(scope=label):
                a, b = copy.deepcopy(run), copy.deepcopy(artifact)
                (a if target == "run" else b)[key] = value
                with self.assertRaises(ValueError):
                    native.verify_api(a, b, contract)
        raw = gzip.decompress((FIXTURES / "original-products-manifest.json.gz").read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         contract["metadata_members"]["sdk06-early-products/manifest.json"]["sha256"])
        manifest = json.loads(raw)
        self.assertEqual(len(native.validate_product_manifest(manifest, contract)), 5011)
        for label, mutate in (
                ("origin", lambda value: value.update(source_sha="f" * 40)),
                ("reuse_label", lambda value: value.update(native_acceptance_reused=True)),
                ("build_origin_label", lambda value: value.update(every_entry_build_origin_verified=True)),
                ("missing_entry", lambda value: value["products"].pop(next(iter(value["products"])))),
                ("changed_carrier", lambda value: value["products"][next(iter(contract["native_carriers"]))].update(sha256="0" * 64)),
                ("link", lambda value: value["products"][next(iter(contract["native_carriers"]))].update(kind="symlink"))):
            with self.subTest(scope="manifest_" + label):
                value = copy.deepcopy(manifest)
                mutate(value)
                with self.assertRaises(ValueError):
                    native.validate_product_manifest(value, contract)

        # Exercise the unchanged regular-entry extraction helper through the
        # new restoration contract, using explicitly tiny synthetic payloads.
        payload = b"SDK06_NEW_CONTROL_ONLY"
        expected = {"products": {
            "Build/Products": {"kind": "directory", "mode": 0o755},
            "Build/Products/control.bin": {"kind": "file", "mode": 0o755, "bytes": len(payload),
                                           "sha256": hashlib.sha256(payload).hexdigest()},
        }}
        def archive(name, *, altered=False, link=False, extra=False):
            path = output / name
            with tarfile.open(path, "w:gz") as packed:
                directory = tarfile.TarInfo("Build/Products")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                packed.addfile(directory)
                item = tarfile.TarInfo("Build/Products/control.bin")
                item.mode = 0o755
                if link:
                    item.type = tarfile.SYMTYPE
                    item.linkname = "/outside"
                    packed.addfile(item)
                else:
                    data = b"changed" if altered else payload
                    item.size = len(data)
                    packed.addfile(item, io.BytesIO(data))
                if extra:
                    item = tarfile.TarInfo("Build/Products/extra")
                    item.size = 1
                    packed.addfile(item, io.BytesIO(b"x"))
            return path
        actual = probe.extract_products(archive("valid.tar.gz"), output / "restored", expected)
        self.assertEqual(actual["entries"], 2)
        self.assertEqual((output / "restored/Build/Products/control.bin").read_bytes(), payload)
        for label in ("changed", "link", "extra"):
            with self.subTest(scope="restoration_" + label):
                path = archive(label + ".tar.gz", altered=label == "changed", link=label == "link", extra=label == "extra")
                with self.assertRaises((ValueError, RuntimeError)):
                    probe.extract_products(path, output / (label + "-restore"), expected)
        malicious = {"products": {"../outside": {"kind": "file", "mode": 0o644, "bytes": 0,
                                                 "sha256": hashlib.sha256(b"").hexdigest()}}}
        with self.subTest(scope="escaping_manifest"):
            with self.assertRaises((ValueError, RuntimeError)):
                probe.extract_products(output / "valid.tar.gz", output / "escape-restore", malicious)

        # Source bytes/modes are checked by the actual new source reader. Only
        # Git's fixed tree responses are synthetic; no actual75bd claim is made.
        app = output / "source-model"
        app.mkdir()
        (app / "One.swift").write_bytes(b"one")
        (app / "Two.swift").write_bytes(b"two")
        tree = {name: {"git_mode": "100644", "git_blob": str(index) * 40}
                for index, name in enumerate(("One.swift", "Two.swift"), start=1)}
        source_map = {"source_sha": native.SOURCE, "inputs": {
            name: {"sha256": native.sha(app / name)} for name in tree}}
        source_contract = {"tracked_source_count": 2, "original_untracked_framework_inputs": {}}
        def git(argv, **kwargs):
            if argv[-2:] == ["rev-parse", "HEAD"]:
                return native.SOURCE + "\n"
            if "status" in argv:
                return ""
            raise AssertionError("Unplanned control Git invocation")
        with mock.patch.object(native, "git_tree", return_value=tree), \
                mock.patch.object(native.subprocess, "check_output", side_effect=git):
            before = native.verify_app_source(app, source_map, source_contract)
            self.assertEqual(set(before), set(tree))
            (app / "One.swift").write_bytes(b"ONE")
            with self.subTest(scope="changed_source"):
                with self.assertRaisesRegex(ValueError, "source bytes differ"):
                    native.verify_app_source(app, source_map, source_contract)
            (app / "One.swift").write_bytes(b"one")
            (app / "Two.swift").chmod(0o755)
            with self.subTest(scope="changed_source_mode"):
                with self.assertRaisesRegex(ValueError, "executable mode"):
                    native.verify_app_source(app, source_map, source_contract)
        native.save(output / "scope.json", {
            "actual_original_manifest_entries": 5011,
            "original_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "synthetic_extraction_entries": 2, "source_model_files": 2,
            "original_archive_restored_by_this_control": False,
            "product_tests_executed": 0, "Apple_builds": 0, "old_controller_methods_executed": 0,
        }, original=True)

    def test_actual_lane_stops_on_original30_and_ui_builder_cannot_rebuild_native(self):
        output = control_root("lane-and-first-ui")
        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        branch_argv = ["git", "-C", str(ROOT), "branch", "--show-current"]
        actual_local_branch = subprocess.check_output(branch_argv, text=True).strip()
        branch = "codex/chatgpt-wave15-shared-20261121"
        self.assertIn(branch, lane.APPROVED_BRANCHES)
        branch_observations = []
        original_check_output = subprocess.check_output
        def synthetic_ci_branch(argv, *args, **kwargs):
            if argv == branch_argv:
                self.assertIs(kwargs.get("text"), True)
                branch_observations.append({
                    "argv": argv, "actual_local_branch": actual_local_branch,
                    "synthetic_approved_ci_branch": branch,
                    "actual_shared_writer_claim": False,
                })
                return branch + "\n"
            return original_check_output(argv, *args, **kwargs)
        actual_control_binding = {"source_sha": head, "run_id": "900000002", "run_attempt": "1"}
        with mock.patch.dict(os.environ, {"GITHUB_SHA": head, "GITHUB_REF": "refs/heads/" + branch,
                "GITHUB_RUN_ID": "900000002", "GITHUB_RUN_ATTEMPT": "1"}), \
                mock.patch.object(subprocess, "check_output", side_effect=synthetic_ci_branch):
            admitted = continuation.verify_controller(ROOT, actual_control_binding)
            self.assertEqual(admitted["binding"], actual_control_binding)
            foreign = types.ModuleType("sdk06_original_native")
            foreign.__file__ = str(output / "foreign-origin.py")
            with self.subTest(scope="initial_foreign_module_is_refused"):
                with mock.patch.dict(sys.modules, {"sdk06_original_native": foreign}):
                    with self.assertRaisesRegex(ValueError, "foreign origin"):
                        continuation.verify_controller(ROOT, actual_control_binding)
        self.assertEqual(len(branch_observations), 1)
        self.assertEqual(subprocess.check_output(branch_argv, text=True).strip(), actual_local_branch)
        contract = fixed()
        tag_raw = (ROOT / contract["tag_contract"]["path"]).read_bytes()
        tag = json.loads(tag_raw)
        descriptor_raw = (FIXTURES / "original-native.xctestrun").read_bytes()
        uid = "22222222-2222-4222-8222-222222222222"
        binding = {"source_sha": "b" * 40, "run_id": "900000002", "run_attempt": "1"}
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
        def fixture(name):
            directory = output / name
            directory.mkdir()
            app, evidence, derived = directory / "app", directory / "evidence", directory / "derived"
            app.mkdir()
            evidence.mkdir()
            tag_path = app / contract["tag_contract"]["path"]
            tag_path.parent.mkdir(parents=True)
            tag_path.write_bytes(tag_raw)
            (app / "Tools/PinkhaSimulatorGate/required-coverage.json").write_bytes(
                (ROOT / "Tools/PinkhaSimulatorGate/required-coverage.json").read_bytes())
            lock_path = app / contract["package_lock"]["path"]
            lock_path.parent.mkdir(parents=True)
            lock_path.write_bytes((FIXTURES / "original-Package.resolved").read_bytes())
            project = app / "PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj"
            scheme = project / "xcshareddata/xcschemes/PinkhaStage1Acceptance.xcscheme"
            scheme.parent.mkdir(parents=True)
            (project / "project.pbxproj").write_bytes((FIXTURES / "original-ui-project.pbxproj").read_bytes())
            scheme.write_bytes((FIXTURES / "original-ui-scheme.xcscheme").read_bytes())
            native_descriptor = derived / contract["descriptor"]["path"]
            native_descriptor.parent.mkdir(parents=True)
            native_descriptor.write_bytes(descriptor_raw)
            host = native_descriptor.with_name("UI27-original-sdk06-host.xctestrun")
            built = derived / "Build/Products/Debug-Anytype-iphonesimulator/Anytype.app"
            test = built / "PlugIns/AnytypeTests.xctest/AnytypeTests"
            test.parent.mkdir(parents=True)
            (built / "Anytype").write_bytes(b"ORIGINAL_NATIVE_MODEL")
            test.write_bytes(b"ORIGINAL_TEST_MODEL")
            cached = native_descriptor.with_name("UI27-prepare.xctestrun")
            cached.write_bytes(descriptor_raw)
            entries = descriptor_additions.tree(derived)
            for relative, row in entries.items():
                if row["kind"] == "file":
                    path = derived / relative
                    row.update(bytes=path.stat().st_size, sha256=native.sha(path))
            parents = descriptor_additions.original_tree(derived, entries)
            native.save(evidence / "original-native" / contract["native_archive"]["manifest_path"],
                        {"products": entries, "synthetic_control_fixture_only": True}, original=True)
            host.write_bytes(descriptor_raw)
            descriptor_binding = {
                "original_path": str(native_descriptor), "original_sha256": native.sha(native_descriptor),
                "host_path": str(host), "host_sha256": native.sha(host),
                "original_bytes_base64": base64.b64encode(descriptor_raw).decode(),
                "host_bytes_base64": __import__("base64").b64encode(descriptor_raw).decode(),
            }
            device = {"udid": uid, "name": "Pinkha-UI27-" + binding["run_id"] + "-ipad", "runtime": {}}
            context = native.SDK06OriginalNativeContext(ROOT, app, directory / "work", evidence, derived,
                json.dumps(binding, sort_keys=True), json.dumps({"structural_parent_directories": parents}),
                json.dumps(descriptor_binding, sort_keys=True),
                json.dumps(device, sort_keys=True), native._SEAL)
            host_row = descriptor_additions.register(derived, entries, parents, evidence, binding,
                host, "host-normalization")
            context._generated_descriptors[host_row["path"]] = host_row
            native.save(evidence / "preflight/preflight.json",
                {"status": "PREFLIGHT_PASS_UI_NOT_RUN", **binding, "selected": {"ipad": device}}, original=True)
            native.save(evidence / "heart/heart-installation.json", {"control_fixture_only": True}, original=True)
            native.save(evidence / "original-native/execution.json",
                {"candidate_input_hashes": {}, "kit_sha": contract["kit_sha"]}, original=True)
            originals = {path: native.sha(path) for path in (built / "Anytype", test, native_descriptor, host, cached)}
            return context, built, test, originals
        calls, enumerations = [], []
        context, built, test, originals = fixture("failed-original30")
        def verified(self, **kwargs):
            for path, digest in originals.items():
                self_test.assertEqual(native.sha(path), digest)
            return contract
        self_test = self
        class Actual30Enumeration:
            def __init__(self, app, evidence, receipt):
                self_test.assertEqual(app, context.app)
            def run(self, argv, label, timeout):
                enumerations.append(argv)
                output_path = Path(argv[argv.index("-test-enumeration-output-path") + 1])
                name = "original-discovery.enumeration.json" if label.endswith("discovery") else "original-selected.enumeration.json"
                output_path.write_bytes((FIXTURES / name).read_bytes())
                return output_path, {"return_code": 0}
        def command(argv, *args, **kwargs):
            calls.append(argv)
            if argv[:2] in (["xcrun", "simctl"],):
                self.assertIn(argv[2], ("boot", "bootstatus"))
                return None
            raise AssertionError("No native or UI build is permitted after this failed selection")
        env = {"GITHUB_SHA": binding["source_sha"], "GITHUB_RUN_ID": binding["run_id"],
               "GITHUB_RUN_ATTEMPT": binding["run_attempt"], "GITHUB_REF": "refs/heads/control-fixture"}
        with ExitStack() as stack:
            for patch in (
                mock.patch.dict(os.environ, env),
                mock.patch.object(native, "manifest", return_value=contract),
                mock.patch.object(native.SDK06OriginalNativeContext, "verify_current", verified),
                mock.patch.object(lane.platform, "system", return_value="Darwin"),
                mock.patch.object(lane, "source_methods", return_value=None),
                mock.patch.object(lane.text_native_ack, "source_contract", return_value={"control_fixture_only": True}),
                mock.patch.object(component, "source_contract", return_value=source),
                mock.patch.object(shared, "git", return_value=native.SOURCE),
                mock.patch.object(shared, "runtime_binding", return_value={"native_marker": "CONTROL_ONLY"}),
                mock.patch.object(shared, "candidate_identity", return_value={"hashes": {}}),
                mock.patch.object(shared, "command", side_effect=command),
                mock.patch.object(lane.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stdout="", stderr="")),
                mock.patch.object(shared, "prepare_source_cache", side_effect=AssertionError("Native source-cache preparation forbidden")),
                mock.patch.object(lane.early_build_products, "capture", side_effect=AssertionError("Original native recapture forbidden")),
                mock.patch.object(shared, "verify_signed_simulator", return_value=None),
                mock.patch.object(shared, "verify_runtime_copies", return_value=None),
                mock.patch.object(shared, "code_carriers", return_value={"sha256": "CONTROL_ONLY"}),
                mock.patch.object(component.host, "xctest_products",
                    return_value=(built, built / "Anytype", test.parent, test)),
                mock.patch.object(selector.probe, "Commands", Actual30Enumeration),
                mock.patch.object(shared, "run_xctest", side_effect=AssertionError("Product execution forbidden")),
                mock.patch.object(shared, "run_selection", side_effect=AssertionError("Ack/native/UI execution forbidden")),
            ):
                stack.enter_context(patch)
            plan = selector.load_plan(context)
            args = argparse.Namespace(app=context.app, evidence=context.evidence, derived=context.derived,
                lane="hanlin-native", device="ipad", language="en", runtime_profile=native.RUNTIME_PROFILE,
                heart_source_run_id=native.PRODUCER_RUN, include_text_native_ack=True, include_shared_editor=True,
                sdk06_original_native_tagged_plan=plan)
            receipt = {"status": "FAIL", **binding}
            with self.subTest(scope="actual_lane_original30_stops_before_all_pending_execution"):
                with self.assertRaisesRegex(ValueError, "exact23"):
                    lane.execute(args, receipt, sdk06_original_native=context)
                self.assertEqual(receipt["source_sha"], binding["source_sha"])
                self.assertEqual(receipt["app_source_sha"], native.SOURCE)
                self.assertEqual(receipt["native_builds_this_run"], 0)
                self.assertNotIn("native_build_succeeded", receipt)
                self.assertFalse(any(argv[0] == "xcodebuild" for argv in calls))
                self.assertEqual(len(enumerations), 2)
                self.assertFalse((context.evidence / "first-ui-only-build.json").exists())
            with self.subTest(scope="first_ui_build_refuses_failed_component_receipt"):
                with self.assertRaisesRegex(ValueError, "pending component"):
                    context.build_first_ui(
                        ["xcodebuild", "build-for-testing", "-configuration", "Debug-Anytype",
                         "-destination", "platform=iOS Simulator,id=" + uid, "-parallel-testing-enabled", "NO"],
                        contract["native_build_flags"], contract["ui_methods"],
                        context.derived.with_name(context.derived.name + "-ui"), shared)

        positive, positive_built, positive_test, positive_originals = fixture("synthetic-ui-prerequisites")
        def positive_verified(self, **kwargs):
            for path, digest in positive_originals.items():
                if native.sha(path) != digest:
                    raise ValueError("Original native model bytes changed")
            return contract
        ui_calls = []
        def ui_command(argv, app, evidence):
            self.assertEqual(argv[:2], ["xcodebuild", "build-for-testing"])
            self.assertEqual(argv[argv.index("-scheme") + 1], "PinkhaPrebuiltUI")
            self.assertNotIn("Anytype.xcodeproj", argv)
            self.assertEqual(argv[argv.index("-configuration") + 1], "Debug-Anytype")
            self.assertEqual([arg for arg in argv if arg.startswith("-only-testing:")],
                             ["-only-testing:PinkhaStage1AcceptanceUITests/" + contract["ui_methods"][0]])
            Path(argv[argv.index("-derivedDataPath") + 1]).mkdir()
            ui_calls.append(argv)
        with mock.patch.object(native, "manifest", return_value=contract), \
                mock.patch.object(native.SDK06OriginalNativeContext, "verify_current", positive_verified), \
                mock.patch.object(shared, "command", side_effect=ui_command):
            native.save(positive.evidence / "shared-editor-components/execution.json",
                {"status": component.PASS_STATUS, "build_mode": "ORIGINAL_NATIVE_PRODUCTS_EXACT_RESTORATION",
                 "original_native_origin": positive.origin_reference(),
                 "actual": {"actual_method_count": 23, "declared_case_count": 32},
                 "synthetic_control_fixture_not_actual_execution": True}, original=True)
            for name, count in (("text-native-ack", 7), ("preparation", 1)):
                native.save(positive.evidence / name / "result.json",
                    {"status": "PASS", "passed": count, "failed": 0, "skipped": 0,
                     "synthetic_control_fixture_not_actual_execution": True}, original=True)
            base = ["xcodebuild", "build-for-testing", "-configuration", "Debug-Anytype",
                    "-destination", "platform=iOS Simulator,id=" + uid, "-parallel-testing-enabled", "NO"]
            result = positive.build_first_ui(base, contract["native_build_flags"], contract["ui_methods"],
                positive.derived.with_name(positive.derived.name + "-ui"), shared)
            self.assertEqual(result["native_builds_this_run"], 0)
            self.assertEqual(len(ui_calls), 1)
            self.assertTrue(result["native_products_unchanged"])
            with self.subTest(scope="a_second_ui_build_attempt_is_refused"):
                with self.assertRaisesRegex(ValueError, "fresh separate"):
                    positive.build_first_ui(base, contract["native_build_flags"], contract["ui_methods"],
                        positive.derived.with_name(positive.derived.name + "-ui"), shared)

        collision, _, _, collision_originals = fixture("original-name-collision")
        entries = native.read(collision.evidence / "original-native" /
                              contract["native_archive"]["manifest_path"])["products"]
        parents = json.loads(collision.restoration_json)["structural_parent_directories"]
        actual_manifest = json.loads(gzip.decompress((FIXTURES / "original-products-manifest.json.gz").read_bytes()))
        self.assertIn("Build/Products/UI27-prepare.xctestrun", actual_manifest["products"])
        copied = []
        def selection_command(argv, app, evidence, bundle, prefix):
            self.assertEqual(prefix, "prepare")
            self.assertEqual(argv[:2], ["xcodebuild", "test-without-building"])
            selected_path = Path(argv[argv.index("-xctestrun") + 1])
            self.assertNotEqual(selected_path, collision.native_configuration.with_name("UI27-prepare.xctestrun"))
            current = descriptor_additions.verify(collision.derived, entries, parents,
                                                   collision.evidence, collision.execution_binding)
            self.assertEqual(current[selected_path.relative_to(collision.derived).as_posix()]["purpose"], "prepare")
            self.assertEqual(current, collision._generated_descriptors)
            for path, digest in collision_originals.items():
                self.assertEqual(native.sha(path), digest)
            copied.append(selected_path)
            raise RuntimeError("CONTROL_ONLY_STOP_BEFORE_XCTEST")
        with mock.patch.object(native.SDK06OriginalNativeContext, "verify_current", return_value=contract), \
                mock.patch.object(native_selection, "run_xctest", side_effect=selection_command):
            with self.subTest(scope="cached_original_prepare_is_preserved_and_copy_registered_before_command"):
                result = native_selection.run_selection(collision.app, collision.native_configuration,
                    "AnytypeTests", uid, [lane.LANES["hanlin-native"]["preparation"]], {},
                    collision.evidence / "preparation", "prepare",
                    register_descriptor=collision.register_generated_descriptor)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["error"], "CONTROL_ONLY_STOP_BEFORE_XCTEST")
                self.assertEqual(len(copied), 1)
                for path, digest in collision_originals.items():
                    self.assertEqual(native.sha(path), digest)
        unrecorded = collision.derived / "Build/Products/unrecorded.xctestrun"
        unrecorded.write_bytes(b"UNRECORDED_CONTROL_ONLY")
        with self.subTest(scope="unrecorded_generated_products_member_is_refused"):
            with self.assertRaisesRegex(ValueError, "unrecorded"):
                descriptor_additions.verify(collision.derived, entries, parents,
                                            collision.evidence, collision.execution_binding)
        unrecorded.unlink()
        copied[0].write_bytes(b"CHANGED_CONTROL_ONLY")
        with self.subTest(scope="changed_registered_descriptor_is_refused"):
            with self.assertRaisesRegex(ValueError, "recorded generated descriptor changed"):
                descriptor_additions.verify(collision.derived, entries, parents,
                                            collision.evidence, collision.execution_binding)

        native.save(output / "scope.json", {
            "actual_lane_reached_original30_refusal": True,
            "identity_branch_observation": branch_observations,
            "actual_frozen_head_and_Git_source_admission": head,
            "native_build_calls": 0, "native_cache_preparation_calls": 0, "native_recapture_calls": 0,
            "first_ui_only_build_command_fixture": ui_calls,
            "ui_project_generator": "ACTUAL_UNCHANGED_PRODUCTION_FUNCTION",
            "cached_original_prepare_collision_preserved": True,
            "finite_descriptor_ledger_refused_unrecorded_and_changed_members": True,
            "OS_build_execution": False, "synthetic_prerequisites_are_not_product_evidence": True,
            "product_tests_executed": 0, "old_controller_methods_executed": 0,
        }, original=True)
