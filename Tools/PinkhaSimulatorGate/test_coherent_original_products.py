"""New origin/admission controls; no simulator, build or product execution."""
import copy
from pathlib import Path
import plistlib
import tempfile
import unittest

import coherent_original_products as original
import coherent_heart_release as coherent
import wave15_batch as batch


class OriginalProductsControls(unittest.TestCase):
    def admission(self):
        return dict(protocol=original.PROTOCOL, continuation=original.NAME,
            build_origin=original.origin_fields(),
            execution_origin=dict(control_source_sha="a" * 40, run_id="90000001", run_attempt="1"),
            app_source_sha=original.SOURCE, source_tree_sha=original.SOURCE_TREE,
            app_builds_this_run=0, ui_runner_builds_this_run=0,
            original_app_builds=1, original_ui_runner_builds=1, original_product_tests_executed=0,
            current_shared_app_accepted=False, previous_test_acceptance_reused=False,
            every_archived_entry_build_origin_verified=False)

    def test_origin_rejects_current_app_and_mixed_original_producer(self):
        value = self.admission()
        original.validate_origins(value, "a" * 40, "90000001", "1")
        variants = []
        changed = copy.deepcopy(value); changed["app_source_sha"] = "a" * 40; variants.append(changed)
        changed = copy.deepcopy(value); changed["build_origin"]["run_id"] = "45091223011"; variants.append(changed)
        changed = copy.deepcopy(value); changed["execution_origin"]["control_source_sha"] = original.SOURCE; variants.append(changed)
        changed = copy.deepcopy(value); changed["previous_test_acceptance_reused"] = True; variants.append(changed)
        changed = copy.deepcopy(value); changed["current_shared_app_accepted"] = True; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                original.validate_origins(changed, "a" * 40, "90000001", "1")

    def test_active_carrier_mutation_and_executable_mode_change_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            from types import SimpleNamespace
            native_derived, ui_derived = root / "Native", root / "Native-ui"
            app = native_derived / "Build/Products/Release-Anytype-iphonesimulator/Anytype.app"
            test = app / "PlugIns/AnytypeTests.xctest"
            runner = ui_derived / "Build/Products/Release-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app"
            test.mkdir(parents=True); runner.mkdir(parents=True)
            binary = app / "Anytype"; binary.write_bytes(b"original-app-code"); binary.chmod(0o755)
            (test / "AnytypeTests").write_bytes(b"original-native-tests")
            (runner / "Runner").write_bytes(b"original-ui-tests")
            owner = original.ContinuationOrigin.__new__(original.ContinuationOrigin)
            owner.args = SimpleNamespace(derived=native_derived)
            owner.manifests = {}
            for key, derived, parent in (("native", native_derived, app), ("ui", ui_derived, runner)):
                owner.manifests[key] = {"products": {
                    path.relative_to(derived).as_posix(): dict(kind="directory" if path.is_dir() else "file",
                        mode=path.stat().st_mode & 0o7777)
                    for path in [parent, *parent.rglob("*")]}}
            def observe():
                return dict(app=batch.bundle_manifest(app), ui_runner=batch.bundle_manifest(runner),
                    native_test_bundles={str(test): batch.bundle_manifest(test)},
                    active_modes=owner.active_modes(observed=True))
            expected = observe()
            self.assertEqual(expected["active_modes"], owner.active_modes(observed=False))
            original.validate_carriers(observe(), expected)
            binary.write_bytes(b"changed-app-code")
            with self.assertRaises(RuntimeError):
                original.validate_carriers(observe(), expected)
            binary.write_bytes(b"original-app-code"); binary.chmod(0o644)
            with self.assertRaises(RuntimeError):
                original.validate_carriers(observe(), expected)
            binary.chmod(0o755)
            incomplete = observe(); incomplete["native_test_bundles"] = {}
            with self.assertRaises(RuntimeError):
                original.validate_carriers(incomplete, expected)

    def test_runtime_cannot_mix_current_composition_and_another_framework_origin(self):
        installation = dict(status="PASS", app_source_sha=original.SOURCE,
            source_run_id=original.HEART_SOURCE_RUN,
            producer=dict(source_sha=original.HEART_SOURCE_SHA),
            build_producer=dict(run_id=original.HEART_BUILD_RUN, source_sha=original.HEART_BUILD_SOURCE),
            heart_build_receipt_sha256=original.HEART_BUILD_SHA,
            runtime_profile=original.RUNTIME, installed_fixture=False,
            target_architecture="arm64", target_environment="simulator", expected_app_get_version="original-version")
        native = dict(github_run_id=original.HEART_BUILD_RUN, integration_sha=original.HEART_BUILD_SOURCE,
                      runtime_variant=original.RUNTIME, expected_app_get_version="original-version")
        original.validate_runtime(installation, native)
        for key, value in (("runtime_profile", "semantic-page154"),
                           ("installed_fixture", True), ("target_environment", "device")):
            changed = copy.deepcopy(installation); changed[key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                original.validate_runtime(changed, native)
        changed = copy.deepcopy(installation); changed["build_producer"]["source_sha"] = original.HEART_SOURCE_SHA
        with self.assertRaises(RuntimeError):
            original.validate_runtime(changed, native)
        changed = dict(native, expected_app_get_version="new-version")
        with self.assertRaises(RuntimeError):
            original.validate_runtime(installation, changed)

    def test_zero_new_build_counts_and_original_reference_preserve_behavior_requirements(self):
        expected = original.counts()
        original.validate_counts(expected)
        self.assertEqual({k: v for k, v in expected.items() if k not in ("app_builds", "ui_runner_builds")},
                         {k: v for k, v in coherent.COUNTS.items() if k not in ("app_builds", "ui_runner_builds")})
        for key, value in (("app_builds", 1), ("ui_runner_builds", 1), ("failed", 1),
                           ("pending_retry_service_queries", 8), ("host_action_methods", 10)):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                original.validate_counts(dict(expected, **{key: value}))
        with self.assertRaises(RuntimeError):
            coherent.validate_counts(expected)
        build = dict(role=original.ROLE, build_origin_protocol=original.PROTOCOL,
                     **{original.REFERENCE: "b" * 64})
        record = original.reuse_fields(build)
        self.assertTrue(original.reuse_matches(record, build))
        self.assertNotIn(original.SAME_JOB_REFERENCE, record)
        self.assertNotIn("ui_runner_reused_from_same_job", record)
        self.assertFalse(original.reuse_matches(dict(record, ui_runner_reused_from_same_job=True), build))
        self.assertFalse(original.reference_matches(dict(record, **{original.SAME_JOB_REFERENCE: "b" * 64}), build))
        with self.assertRaises(RuntimeError):
            coherent.validate_build(build, original.SOURCE, None, None, None)

    def test_current_intent_binds_exact_owned_app_and_products_paths(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            control = root / "Control"
            app = control / "build/owned/App"
            derived = app / "build/Native"
            derived.mkdir(parents=True)
            def owner(app_path=app, products_path=derived):
                value = original.ContinuationOrigin.__new__(original.ContinuationOrigin)
                value.control = control
                value.app = app_path.resolve()
                value.args = SimpleNamespace(derived=products_path)
                value.control_sha = "a" * 40
                value.verify_control = lambda: {}
                return value
            def seed():
                return dict(profile=batch.COHERENT_HEART_PROFILE, run_id="90000001", run_attempt="1")
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "90000001", "GITHUB_RUN_ATTEMPT": "1"}):
                current = owner()
                intent = current.bind_intent(seed())
                self.assertEqual(intent["original_app_checkout"], str(app))
                self.assertEqual(intent["original_products_directory"], str(derived))
                self.assertEqual(intent["control_source_sha"], current.control_sha)
                self.assertEqual(intent["source_sha"], original.SOURCE)
                current.validate_intent(intent)
                for key, invalid in (
                    ("original_app_checkout", str(control / "build/foreign/App")),
                    ("original_products_directory", str(app / "build/Other")),
                    ("original_products_directory", str(app / "build/../Other")),
                    ("original_app_checkout", None)):
                    with self.subTest(key=key, invalid=invalid), self.assertRaises(RuntimeError):
                        current.validate_intent(dict(intent, **{key: invalid}))
                for outside_app, outside_products in (
                    (root / "Foreign/App", root / "Foreign/App/build/Native"),
                    (control / "build/../../Foreign/App", root / "Foreign/App/build/Native"),
                    (app, control / "build/Other/Native"),
                    (app, app / "build/../../EscapingProducts")):
                    with self.subTest(app=str(outside_app), products=str(outside_products)):
                        outside = owner(outside_app, outside_products)
                        bound = outside.bind_intent(seed())
                        with self.assertRaises(RuntimeError):
                            outside.validate_intent(bound)

    def test_both_pinned_original_descriptors_only_relocate_their_exact_runtime_token(self):
        fixture = Path(__file__).resolve().parents[2] / "docs/validation/20261123-release-original-products/originals"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); runtime_root = root / "RuntimeRoot"
            library = runtime_root / "usr/lib/libMainThreadChecker.dylib"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"\xcf\xfa\xed\xfe" + b"fixture-code-bytes")
            runtime = dict(isAvailable=True, identifier="com.apple.CoreSimulator.SimRuntime.iOS-27-0",
                           supportedArchitectures=["arm64"], runtimeRoot=str(runtime_root),
                           version="27.0", buildversion="fixture")
            for key, spec in original.ARCHIVES.items():
                source = fixture / (key + ".xctestrun"); raw = source.read_bytes()
                result = original.copied_runtime_descriptor(source, root / (key + ".xctestrun"),
                    spec, runtime, ui=key == "ui")
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(result["original_sha256"], spec["descriptor_sha"])
                self.assertEqual(len(result["targets"]), 1 if key == "ui" else 3)
                decoded = plistlib.loads((root / (key + ".xctestrun")).read_bytes())
                targets = ([value for value in decoded.values() if isinstance(value, dict) and value.get("BlueprintName")]
                           if key == "ui" else decoded["TestConfigurations"][0]["TestTargets"])
                for target in targets:
                    self.assertIn(str(library), target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
                    self.assertNotIn(original.MTC, target["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
                if key == "ui":
                    self.assertTrue(targets[0]["UseUITargetAppProvidedByTests"])
                    self.assertNotIn("UITargetAppPath", targets[0])
                damaged = root / ("wrong-" + key + ".xctestrun")
                damaged.write_bytes(raw.replace(b"libMainThreadChecker", b"libWrongThreadCheck"))
                with self.assertRaises(RuntimeError):
                    original.copied_runtime_descriptor(damaged, root / ("rejected-" + key), spec, runtime, ui=key == "ui")


if __name__ == "__main__":
    unittest.main()
