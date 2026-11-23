#!/usr/bin/env python3
"""Two new offline controls; real retained bytes, explicitly synthetic live paths.

No original UI/host method is loaded or executed. The native App, Mach-O runtime
fixture and current run context below are small control fixtures, not Mac proof.
"""
from __future__ import annotations
import copy
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

import native_ui_runner_reuse as reuse
import native_ui_runner_continuation as entrypoint
import native_ui_transition as transition
import native_ui_transition_contract as contract
import native_ui_original_products_contract as original

FIXTURES = Path(__file__).with_name("native_ui_runner_fixtures")
UUID = "D31EA15A-669B-4C11-8C2B-8012C0DD7B45"


def fixture(path):
    return (FIXTURES / path).read_bytes()


def context_fixture(root):
    app = root / "immutable-app/PinkhaAnyNative.app"
    app.mkdir(parents=True)
    (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": contract.APP_BUNDLE}))
    runtime_root = root / "synthetic-runtime"
    library = runtime_root / "usr/lib/libMainThreadChecker.dylib"
    library.parent.mkdir(parents=True)
    library.write_bytes(b"\xcf\xfa\xed\xfeCONTROL_FIXTURE_NOT_EXECUTABLE")
    runtime = {"isAvailable": True, "identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-2",
               "supportedArchitectures": ["arm64"], "runtimeRoot": str(runtime_root),
               "version": "27.2", "buildversion": "CONTROL_FIXTURE"}
    return app, runtime


def write_copy(path, raw, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(mode)


class RetainedRunnerControls(unittest.TestCase):
    def test_actual_descriptor_mode_app_dependency_and_exact_field_refusals(self):
        manifest = reuse.fixed()
        source = fixture("original-ui-only.xctestrun")
        working = fixture("working-app-bound.xctestrun")
        self.assertEqual(contract.sha(source), manifest["originalDescriptor"]["sha256"])
        self.assertEqual(contract.sha(working), manifest["workingDescriptor"]["sha256"])
        before = plistlib.loads(source)
        old_working = plistlib.loads(working)[contract.TARGET]
        self.assertIs(before[contract.TARGET]["UseUITargetAppProvidedByTests"], True)
        self.assertNotIn("UseUITargetAppProvidedByTests", old_working)
        self.assertEqual(old_working["DependentProductPaths"][0], old_working["UITargetAppPath"])
        with tempfile.TemporaryDirectory(prefix="ui-retained-descriptor-") as temporary:
            root = Path(temporary).resolve()
            products = root / "Products"
            products.mkdir()
            app, runtime = context_fixture(root)
            with mock.patch.object(reuse.owned, "run_owned", side_effect=AssertionError("no_product_command")):
                for stage, (_, _, methods) in contract.STAGES.items():
                    with self.subTest(stage=stage, scope="exact_actual_template_composition"):
                        raw, proof = reuse.compose_descriptor(
                            source, products=products, application=app, stage=stage, runtime=runtime)
                        value = plistlib.loads(raw)
                        target = value[contract.TARGET]
                        self.assertNotIn("UseUITargetAppProvidedByTests", target)
                        self.assertEqual(target["UITargetAppPath"], str(app))
                        self.assertEqual(target["UITargetAppBundleIdentifier"], contract.APP_BUNDLE)
                        self.assertEqual(target["DependentProductPaths"],
                                         [str(app), *before[contract.TARGET]["DependentProductPaths"]])
                        self.assertEqual(target["OnlyTestIdentifiers"], list(methods))
                        self.assertEqual(proof["originalSHA256"], manifest["originalDescriptor"]["sha256"])
                        self.assertEqual(proof["additionalChangedFields"],
                                         ["UseUITargetAppProvidedByTests", "DependentProductPaths"])
                        inverse = copy.deepcopy(value)
                        for key in ("UITargetAppPath", "UITargetAppBundleIdentifier", "OnlyTestIdentifiers",
                                    "UseUITargetAppProvidedByTests", "DependentProductPaths"):
                            if key in before[contract.TARGET]:
                                inverse[contract.TARGET][key] = before[contract.TARGET][key]
                            else:
                                inverse[contract.TARGET].pop(key, None)
                        inverse[contract.TARGET]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"] = (
                            before[contract.TARGET]["TestingEnvironmentVariables"]["DYLD_INSERT_LIBRARIES"])
                        self.assertEqual(inverse, before)
                        plan = contract.command(stage, products / contract.COPY_NAMES[stage], UUID,
                                                root / (stage + ".xcresult"))
                        enum = contract.enumeration_command(plan, root / (stage + ".json"))
                        selectors = ["-only-testing:" + contract.TARGET + "/" + method for method in methods]
                        self.assertEqual([x for x in plan["command"] if x.startswith("-only-testing:")], selectors)
                        self.assertEqual([x for x in enum if x.startswith("-only-testing:")], selectors)
                        self.assertEqual(plan["command"][1], "test-without-building")
                        self.assertNotIn("build-for-testing", plan["command"])
                        self.assertIs(proof["exactOriginalTemplateInverse"], True)
                    with self.subTest(stage=stage, scope="exact_broken_original_preserved"):
                        binding = json.loads(fixture("originals/" + reuse.PREFIX + stage + "/descriptor-binding.json"))
                        old = copy.deepcopy(before)
                        old[contract.TARGET].update(
                            UITargetAppPath=binding["originalApplicationPath"],
                            UITargetAppBundleIdentifier=contract.APP_BUNDLE,
                            OnlyTestIdentifiers=list(methods))
                        self.assertEqual(contract.sha(plistlib.dumps(old, sort_keys=False)), binding["copiedSHA256"])
                        self.assertIs(old[contract.TARGET]["UseUITargetAppProvidedByTests"], True)
                        self.assertNotIn(binding["originalApplicationPath"], old[contract.TARGET]["DependentProductPaths"])
                        self.assertNotEqual(old[contract.TARGET], target)
                for name, changed in (
                    ("mode", lambda value: value[contract.TARGET].pop("UseUITargetAppProvidedByTests")),
                    ("extra_filter", lambda value: value[contract.TARGET].update(OnlyTestIdentifiers=["oldPassedMethod"])),
                    ("injection", lambda value: value[contract.TARGET]["TestingEnvironmentVariables"].update(
                        DYLD_INSERT_LIBRARIES="/unadmitted/libMainThreadChecker.dylib")),
                ):
                    with self.subTest(refusal=name):
                        value = copy.deepcopy(before)
                        changed(value)
                        with self.assertRaisesRegex(ValueError, "exact_original_ui_template_required"):
                            reuse.compose_descriptor(plistlib.dumps(value), products=products,
                                                     application=app, stage="native-ui-continuation", runtime=runtime)
                with self.subTest(refusal="wrong_app_bundle"):
                    (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "foreign.app"}))
                    with self.assertRaisesRegex(ValueError, "sealed_original_application_bundle_required"):
                        reuse.compose_descriptor(source, products=products, application=app,
                                                 stage="native-ui-continuation", runtime=runtime)
                self.assertEqual(fixture("original-ui-only.xctestrun"), source)
                self.assertEqual(fixture("working-app-bound.xctestrun"), working)

    def test_original_runner_restore_origin_ledger_and_zero_build_separation(self):
        manifest = reuse.fixed()
        artifact = json.loads(fixture("artifact-api-original.json"))
        jobs = json.loads(fixture("jobs-api-original.json"))
        observer = json.loads(fixture("observer-result.json"))
        job = next(x for x in jobs["jobs"] if str(x["id"]) == manifest["origin"]["jobID"])
        # Exact fields observed in the retained jobs API and bounded observer;
        # this projection is a control input, not a new API observation.
        run = {"id": job["run_id"], "run_attempt": job["run_attempt"],
               "head_sha": job["head_sha"], "head_branch": job["head_branch"],
               "status": observer["run_status"], "conclusion": observer["run_conclusion"]}
        with self.subTest(scope="actual_original_api_identity_and_failure"):
            proof = reuse.validate_api(run, artifact, jobs, manifest)
            self.assertEqual(proof["originalConclusion"], "failure")
            self.assertEqual(proof["runAttempt"], 2)
        for name, changed, code in (
            ("run_attempt", {"run_attempt": 3}, "exact_original_failed_run_required"),
            ("run_source", {"head_sha": "0" * 40}, "exact_original_failed_run_required"),
        ):
            with self.subTest(refusal=name):
                with self.assertRaisesRegex(ValueError, code):
                    reuse.validate_api({**run, **changed}, artifact, jobs, manifest)
        with self.subTest(refusal="artifact_digest"):
            with self.assertRaisesRegex(ValueError, "exact_original_runner_artifact_required"):
                reuse.validate_api(run, {**artifact, "digest": "sha256:" + "0" * 64}, jobs, manifest)
        with self.subTest(refusal="no_build_cli_operation"):
            with mock.patch("sys.argv", ["native_ui_runner_continuation.py", "build"]), mock.patch("sys.stderr", new=io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    entrypoint.main()
                self.assertEqual(raised.exception.code, 2)
        with tempfile.TemporaryDirectory(prefix="ui-retained-origin-") as temporary:
            root = Path(temporary).resolve()
            app, runtime = context_fixture(root)
            work, evidence = root / "runner", root / "evidence"
            evidence.mkdir()
            origin_root = evidence / "retained-runner-origin"
            origin_root.mkdir()
            originals = origin_root / "originals"
            shutil.copytree(FIXTURES / "originals", originals)
            archive = evidence / "UIRunnerProducts.tar.gz"
            shutil.copyfile(FIXTURES / "UIRunnerProducts.tar.gz", archive)
            self.assertEqual(owned_hash(archive), manifest["runnerArchive"]["sha256"])
            restored = reuse.restore_tree(archive, work, manifest)
            self.assertEqual((restored["originalEntries"], restored["originalProducts"],
                              restored["originalGeneratedSources"]), (24, 20, 4))
            products = work / "derived/Build/Products"
            old_build = originals / (reuse.PREFIX + "build.json")
            app_admission = root / "synthetic-original-app-admission.json"
            app_admission.write_text('{"fixtureOnly":true}\n')
            current_head = subprocess.check_output(
                ["git", "-C", str(reuse.ROOT), "rev-parse", "HEAD"], text=True, timeout=30).strip()
            admission = {"controlCommit": current_head, "currentRunID": "999000000000001",
                         "currentRunAttempt": 1, "applicationCommit": contract.APP_COMMIT,
                         "ownedSimulatorUDID": UUID}
            state = {"context": {"controlCommit": current_head, "currentRunID": admission["currentRunID"],
                                 "currentRunAttempt": 1},
                     "admission": admission, "fixed": original.contract(),
                     "locations": {"evidence": evidence}, "application": app}
            write_copy(evidence / "native-ui-original-runtime.json",
                       (json.dumps({"ownedSimulatorUDID": UUID, "runtime": runtime}) + "\n").encode())
            patches = [
                mock.patch.multiple(transition, WORK=work, EVIDENCE=evidence, GENERATED=work / "source",
                                    DERIVED=work / "derived", PRODUCTS=products, BUILD_RECEIPT=old_build),
                mock.patch.multiple(reuse, REUSE=origin_root, ORIGINALS=originals,
                                    ADMISSION=origin_root / "admission.json",
                                    LEDGER=origin_root / "generated-descriptors.json", ARCHIVE=archive),
                mock.patch.object(original, "ADMISSION", app_admission),
                mock.patch.object(reuse.owned, "run_owned", side_effect=AssertionError("no_build_or_product_command")),
            ]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for patch in patches:
                    stack.enter_context(patch)
                values = reuse.original_metadata(originals, manifest)
                self.assertEqual(values[reuse.PREFIX + "build.json"]["uiRunnerBuildInvocations"], 1)
                self.assertEqual(values[reuse.PREFIX + "final.json"]["status"], "INCOMPLETE")
                current = transition.context_record(state)
                sources = reuse.current_inputs(state, manifest)
                reuse.write_json(reuse.LEDGER, {"protocol": reuse.PROFILE, "descriptors": {}})
                record = {"status": "ADMITTED_RETAINED_UI_RUNNER_NO_BUILD", "profile": reuse.PROFILE,
                          "manifestSHA256": reuse.MANIFEST_SHA, "currentContext": current,
                          "currentSources": sources, "originalRunnerOrigin": manifest["origin"],
                          "currentUIRunnerBuilds": 0, "currentAppBuilds": 0, "currentNativeBuilds": 0,
                          "methodsExecutedAtAdmission": 0, "fixtureOnlySyntheticCurrentContext": True}
                reuse.write_json(reuse.ADMISSION, record)
                reference = reuse.reference()
                with self.subTest(scope="original_and_current_build_receipts_are_not_conflated"):
                    built, descriptor = transition.admitted_build(state, restored_runner=reference)
                    self.assertEqual(built["controlCommit"], manifest["origin"]["sourceCommit"])
                    self.assertNotEqual(built["controlCommit"], current_head)
                    self.assertEqual(reference.record_fields()["uiRunnerBuildInvocations"], 0)
                    self.assertEqual(reference.record_fields()["originalUIRunnerBuildInvocations"], 1)
                    self.assertTrue(reference.record_fields()["originalFailedUIRunRemainsFailure"])
                    with self.assertRaisesRegex(ValueError, "current_candidate_build_origin_changed"):
                        transition.admitted_build(state)
                    with self.assertRaisesRegex(ValueError, "sealed_original_runner_reference_required"):
                        transition.admitted_build(state, restored_runner=object())
                stage = "native-ui-continuation"
                stage_root = evidence / stage
                stage_root.mkdir()
                path = products / contract.COPY_NAMES[stage]
                binding_path = stage_root / "descriptor-binding.json"
                raw, binding = reference.descriptor_bytes(contract.regular(descriptor), state, stage)
                binding.update(copiedSHA256=contract.sha(raw), copiedPath=str(path))
                with self.subTest(refusal="actual_conflicting_app_mode_and_missing_dependency"):
                    broken = plistlib.loads(raw)
                    broken[contract.TARGET]["UseUITargetAppProvidedByTests"] = True
                    broken[contract.TARGET]["DependentProductPaths"].remove(str(app))
                    write_copy(path, plistlib.dumps(broken, sort_keys=False))
                    reuse.write_json(binding_path, binding)
                    with self.assertRaisesRegex(ValueError, "generated_descriptor_not_exact_approved_composition"):
                        reference.register_descriptor(stage, path, binding_path, state)
                    self.assertEqual(reuse.read_ledger(reuse.LEDGER)["descriptors"], {})
                    path.unlink()
                    binding_path.unlink()
                with self.subTest(scope="exact_sibling_descriptor_registered_before_any_command"):
                    write_copy(path, raw)
                    reuse.write_json(binding_path, binding)
                    reference.register_descriptor(stage, path, binding_path, state)
                    verified = reuse.verify_tree(work, manifest, reuse.read_ledger(reuse.LEDGER))
                    self.assertEqual(verified["generatedDescriptors"], 1)
                    self.assertEqual(owned_hash(descriptor), manifest["originalDescriptor"]["sha256"])
                    with self.assertRaisesRegex(ValueError, "generated_descriptor_purpose_already_used"):
                        reference.register_descriptor(stage, path, binding_path, state)
                with self.subTest(refusal="unrecorded_descriptor"):
                    extra = products / "Unrecorded.xctestrun"
                    write_copy(extra, raw)
                    with self.assertRaisesRegex(ValueError, "unrecorded_runner_tree_member"):
                        reference.verify(state)
                    extra.unlink()
                with self.subTest(refusal="changed_registered_descriptor"):
                    old = path.read_bytes()
                    path.write_bytes(old + b"\n")
                    with self.assertRaisesRegex(ValueError, "restored_runner_payload_changed"):
                        reference.verify(state)
                    path.write_bytes(old)
                with self.subTest(refusal="changed_original_payload"):
                    payload = products / "Debug-iphonesimulator/PinkhaAnyNativeUITests-Runner.app/PkgInfo"
                    old = payload.read_bytes()
                    payload.write_bytes(b"X" + old[1:])
                    with self.assertRaisesRegex(ValueError, "restored_runner_payload_changed"):
                        reference.verify(state)
                    payload.write_bytes(old)
                with self.subTest(refusal="changed_original_mode"):
                    mode = stat.S_IMODE(payload.lstat().st_mode)
                    payload.chmod(0o600)
                    with self.assertRaisesRegex(ValueError, "restored_runner_type_or_mode_changed"):
                        reference.verify(state)
                    payload.chmod(mode)
                with self.subTest(refusal="changed_current_origin"):
                    saved = reuse.ADMISSION.read_bytes()
                    altered = json.loads(saved)
                    altered["currentContext"]["currentRunAttempt"] += 1
                    reuse.ADMISSION.chmod(0o600)
                    reuse.ADMISSION.write_text(json.dumps(altered))
                    with self.assertRaisesRegex(ValueError, "retained_runner_current_admission_changed"):
                        reference.verify(state)
                    reuse.ADMISSION.write_bytes(saved)
                    reuse.ADMISSION.chmod(0o400)
                with self.subTest(refusal="changed_original_metadata"):
                    saved = old_build.read_bytes()
                    old_build.write_bytes(saved + b"\n")
                    with self.assertRaisesRegex(ValueError, "retained_runner_original_metadata_changed"):
                        reference.verify(state)
                    old_build.write_bytes(saved)
                with self.subTest(refusal="changed_original_tar"):
                    saved = archive.read_bytes()
                    archive.write_bytes(saved + b"unadmitted")
                    with self.assertRaisesRegex(ValueError, "retained_ui_archive_changed"):
                        reference.verify(state)
                    archive.write_bytes(saved)
                with self.subTest(scope="second_and_final_exact_descriptor_purpose"):
                    stage2 = "archive-roundtrip"
                    directory2 = evidence / stage2
                    directory2.mkdir()
                    path2 = products / contract.COPY_NAMES[stage2]
                    binding2_path = directory2 / "descriptor-binding.json"
                    raw2, binding2 = reference.descriptor_bytes(contract.regular(descriptor), state, stage2)
                    binding2.update(copiedSHA256=contract.sha(raw2), copiedPath=str(path2))
                    write_copy(path2, raw2)
                    reuse.write_json(binding2_path, binding2)
                    reference.register_descriptor(stage2, path2, binding2_path, state)
                    self.assertEqual(reuse.verify_tree(work, manifest, reuse.read_ledger(reuse.LEDGER))["generatedDescriptors"], 2)
                with self.subTest(refusal="third_or_path_overriding_descriptor"):
                    saved = reuse.LEDGER.read_bytes()
                    changed = json.loads(saved)
                    changed["descriptors"]["third"] = copy.deepcopy(changed["descriptors"][stage])
                    reuse.LEDGER.chmod(0o600)
                    reuse.LEDGER.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError, "only_two_fixed_generated_descriptor_purposes"):
                        reference.verify(state)
                    changed = json.loads(saved)
                    changed["descriptors"][stage]["relative"] = "../outside.xctestrun"
                    reuse.LEDGER.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError, "generated_descriptor_ledger_schema_or_path_changed"):
                        reference.verify(state)
                    reuse.LEDGER.write_bytes(saved)
                    reuse.LEDGER.chmod(0o400)
                reference.verify(state)
                self.assertFalse((evidence / "build.json").exists())
                self.assertEqual(owned_hash(archive), manifest["runnerArchive"]["sha256"])
                self.assertEqual(reuse.original_metadata(originals, manifest), values)
                workflow = (reuse.ROOT / reuse.WORKFLOW).read_text()
                self.assertNotIn("native_ui_transition.py build", workflow)
                self.assertNotIn("build-for-testing", workflow)
                self.assertIn("native_ui_runner_continuation.py restore", workflow)
                self.assertEqual(workflow.count("native_ui_runner_continuation.py execute --stage"), 2)


def owned_hash(path):
    return reuse.owned.digest(path)


if __name__ == "__main__":
    unittest.main()
