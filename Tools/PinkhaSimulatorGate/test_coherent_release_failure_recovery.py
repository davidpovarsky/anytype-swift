"""New controller controls only; synthetic fixtures are never Apple evidence."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import wave15_batch as batch
import run_wave15_acceptance as lane
import run_t5_apple_pair as pair
import test_wave15_batch as fixtures

PROFILE = batch.COHERENT_HEART_PROFILE
DEVICE = {**fixtures.DEVICE, "lane": "editor"}
SOURCE = "a" * 40


class CoherentReleaseRecoveryControls(unittest.TestCase):
    def readiness(self, root, fail_bootstatus=False):
        evidence = root / "evidence"
        evidence.mkdir()
        batch.write(evidence / "owned-simulator.json", DEVICE)
        context = replace(fixtures.frozen(root, DEVICE), profile=PROFILE)
        calls = []

        def run(argv, app, directory, name, timeout, *, output=None, **unused):
            calls.append((argv, timeout))
            record = {"argv": argv, "timeout_seconds": timeout, "return_code": 0,
                      "timed_out": False, "status": "SUCCESS",
                      "owned_group_quiescence": {"status": "PASS"}}
            log = directory / (name + ".log")
            log.write_text("controller fixture\n")
            if output is not None:
                batch.write(output, fixtures.inventory([DEVICE]))
            if fail_bootstatus and name == "boot-status":
                record.update(return_code=None, timed_out=True, status="TIMED_OUT")
                batch.write(directory / (name + ".command.json"), record)
                raise subprocess.TimeoutExpired(argv, timeout)
            batch.write(directory / (name + ".command.json"), record)
            return record, log

        return context, evidence, calls, run

    def test_exact_preboot_identity_and_bootstatus_avoid_redundant_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            context, evidence, calls, run = self.readiness(Path(temporary))
            negative = subprocess.CompletedProcess([], 1, b"", b"unclassified fixture error")
            with patch.object(pair, "run_logged", side_effect=run), \
                 patch.object(batch.subprocess, "check_output", side_effect=AssertionError("postboot inventory")), \
                 patch.object(batch.subprocess, "run", return_value=negative) as container:
                context.prepare_fresh_device(DEVICE["udid"], evidence)
                context.confirm_empty_container(DEVICE["udid"], evidence)
                ready = json.loads((evidence / "owned-readiness/readiness.json").read_bytes())
                fresh = json.loads((evidence / "fresh-container.json").read_bytes())
                self.assertEqual([argv[2] for argv, timeout in calls], ["list", "boot", "bootstatus"])
                self.assertEqual([timeout for argv, timeout in calls], [60, 120, 180])
                self.assertFalse(ready["postboot_inventory_performed"])
                self.assertEqual(ready["before"]["state"], "Shutdown")
                self.assertEqual(fresh["readiness_receipt_sha256"],
                                 batch.digest(evidence / "owned-readiness/readiness.json"))
                self.assertEqual(fresh["container_lookup_classification"], "NEGATIVE_UNCLASSIFIED")
                (evidence / "owned-readiness/boot-status.log").write_text("changed original log")
                with self.assertRaisesRegex(RuntimeError, "readiness evidence changed"):
                    context.confirm_empty_container(DEVICE["udid"], evidence)
                self.assertEqual(container.call_count, 1)

    def test_failed_bootstatus_blocks_readiness_and_container_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            context, evidence, calls, run = self.readiness(Path(temporary), fail_bootstatus=True)
            with patch.object(pair, "run_logged", side_effect=run), \
                 patch.object(batch.subprocess, "run") as container:
                with self.assertRaises(subprocess.TimeoutExpired) as failed:
                    context.prepare_fresh_device(DEVICE["udid"], evidence)
                self.assertEqual(failed.exception.timeout, 180)
                ready = json.loads((evidence / "owned-readiness/readiness.json").read_bytes())
                self.assertEqual(ready["status"], "FAIL")
                with self.assertRaisesRegex(RuntimeError, "readiness is incomplete"):
                    context.confirm_empty_container(DEVICE["udid"], evidence)
                container.assert_not_called()

    def test_coherent_execute_enters_readiness_before_first_container_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary)
            evidence = app / "build/evidence"
            (evidence / "preflight").mkdir(parents=True)
            (evidence / "heart").mkdir()
            (app / "Tools/PinkhaSimulatorGate").mkdir(parents=True)
            batch.write(app / "Tools/PinkhaSimulatorGate/required-coverage.json", {})
            batch.write(evidence / "heart/heart-installation.json", {})
            batch.write(evidence / "preflight/preflight.json", {
                "status": "PREFLIGHT_PASS_UI_NOT_RUN", "source_sha": SOURCE,
                "run_id": "123", "selected": {"ipad": DEVICE}})
            calls = []
            context = Mock(profile=PROFILE, device=DEVICE)
            context.prepare_fresh_device.side_effect = lambda *args: calls.append("readiness")
            def stop(*args):
                calls.append("container")
                raise RuntimeError("STOP_AFTER_READINESS")
            context.confirm_empty_container.side_effect = stop
            args = argparse.Namespace(app=app, evidence=evidence, derived=app / "build/derived",
                                      lane="editor", device="ipad", language="en")
            with patch.object(lane.platform, "system", return_value="Darwin"), \
                 patch.object(lane, "source_methods"), patch.object(lane, "require_source_identity"), \
                 patch.object(lane.shared, "git", return_value=SOURCE), \
                 patch.object(lane.shared, "runtime_binding", return_value={}), \
                 patch.object(lane.shared, "candidate_identity", return_value={"hashes": {}}), \
                 patch.object(lane.shared, "command") as legacy_boot, \
                 patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": SOURCE}):
                with self.assertRaisesRegex(RuntimeError, "STOP_AFTER_READINESS"):
                    lane.execute(args, {}, build_context=context)
            self.assertEqual(calls, ["readiness", "container"])
            legacy_boot.assert_not_called()
            self.assertEqual(json.loads((evidence / "execution.json").read_bytes())["phase"],
                             "OWNED_SIMULATOR_READINESS")

    def test_original_simctl_failure_survives_later_cleanup_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            spec = batch.profile_spec(PROFILE)
            original = {"protocol": batch.PROTOCOL, "profile": PROFILE,
                        "status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "phase": "LANE",
                        "current_lane": "editor", "error_type": "TimeoutExpired",
                        "error": "original owned simctl inventory timed out after 120 seconds",
                        "finished_at": "2026-11-22T18:19:03Z", "source": {"source_sha": SOURCE},
                        "planned_ui_methods": spec.ui_count,
                        "planned_native_preparations": spec.preparation_count,
                        "planned_native_postflights": spec.postflight_count,
                        "lane_statuses": {name: "NOT_RUN_SETUP" for name in spec.lanes}}
            original["lane_statuses"]["editor"] = "LANE_ABORTED_SETUP_OR_IDENTITY"
            path = evidence / "batch-worker.json"
            batch.write(path, original)
            exact = path.read_bytes()
            intent = {"profile": PROFILE, "source_sha": SOURCE}
            result = {"status": "BATCH_BUDGET_EXHAUSTED"}
            cleanup = subprocess.TimeoutExpired(["ps", "-axo", "pid=,pgid=,stat="], 2)
            self.assertTrue(batch.retain_first_worker_failure(result, intent, evidence, lane, cleanup))
            self.assertEqual(result["status"], original["status"])
            self.assertEqual(result["error"], original["error"])
            self.assertEqual(result["supervisor_error_type"], "TimeoutExpired")
            self.assertIn("ps", result["supervisor_error"])
            self.assertEqual(result["original_worker_failure_sha256"], batch.digest(path))
            self.assertEqual(path.read_bytes(), exact)
            self.assertFalse(batch.retain_first_worker_failure({}, {**intent, "source_sha": "b" * 40},
                                                               evidence, lane, cleanup))
            batch.write(path, {**original, "status": "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING"})
            self.assertFalse(batch.retain_first_worker_failure({}, intent, evidence, lane, cleanup))

    def test_native_and_ui_products_survive_their_first_failed_admission(self):
        import coherent_heart_release as coherent
        import tarfile
        from types import SimpleNamespace
        for failure_phase in ("native", "ui"):
            with self.subTest(failure_phase=failure_phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                evidence, derived = root / "build/evidence", root / "build/derived"
                args = argparse.Namespace(app=root, evidence=evidence, derived=derived)
                batch.write(evidence / "preflight/preflight.json", {
                    "status": "PREFLIGHT_PASS_UI_NOT_RUN", "source_sha": SOURCE, "run_id": "123",
                    "selected": {"ipad": {"udid": DEVICE["udid"]}}})
                batch.write(evidence / "heart/heart-installation.json", {})
                batch.write(root / "Tools/PinkhaSimulatorGate/required-coverage.json", {})
                source = {"source_sha": SOURCE}
                native = derived / "Build/Products/native.xctestrun"
                ui_derived = derived.with_name(derived.name + "-ui")
                ui = ui_derived / "Build/Products/ui.xctestrun"
                built = []
                def command(argv, app, directory):
                    if "build-for-testing" in argv:
                        is_native = "Anytype" == argv[argv.index("-scheme") + 1]
                        products = (derived if is_native else ui_derived) / "Build/Products"
                        products.mkdir(parents=True)
                        configuration = native if is_native else ui
                        configuration.write_bytes(b"original synthetic xctestrun")
                        (products / "original-binary").write_bytes(b"original synthetic executable")
                        built.append("native" if is_native else "ui")
                def snapshot(app, shared, *, stage):
                    if failure_phase == "native" and stage == "AFTER_APP_AND_NATIVE_TEST_BUILD":
                        raise RuntimeError("NATIVE_ADMISSION_STOP")
                    return source
                def configuration(products, blueprint):
                    if blueprint != "AnytypeTests":
                        raise RuntimeError("UI_ADMISSION_STOP")
                    return native
                shared = SimpleNamespace(git=lambda *args: SOURCE, runtime_binding=lambda *args: {"native_marker": "fixture"},
                    candidate_identity=lambda *args: {"hashes": {}}, command=command,
                    prepare_source_cache=Mock(), verify_signed_simulator=Mock(), verify_runtime_copies=Mock(),
                    ui_only_project=lambda app: root / "UI.xcodeproj", test_configuration=configuration)
                harness = SimpleNamespace(shared=shared, require_source_identity=Mock(), source_methods=Mock())
                receipt = {"profile": PROFILE}
                with patch.dict(os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": SOURCE}), \
                     patch.object(batch, "source_snapshot", side_effect=snapshot), \
                     patch.object(coherent, "build_selection", return_value=(["SyntheticNative"], ["SyntheticUI/test"])):
                    with self.assertRaisesRegex(RuntimeError, failure_phase.upper() + "_ADMISSION_STOP"):
                        batch.build_once(args, harness, batch.plan(lane, PROFILE), receipt)
                scopes = ["coherent-native"] if failure_phase == "native" else ["coherent-native", "coherent-ui"]
                self.assertEqual(built, ["native"] if failure_phase == "native" else ["native", "ui"])
                for scope in scopes:
                    archive = evidence / (scope + "-early-products/BuildProducts.tar.gz")
                    manifest = json.loads((archive.parent / "manifest.json").read_bytes())
                    self.assertEqual(manifest["status"], "OBSERVED_PRODUCTS_ARCHIVED_BEFORE_ADMISSION")
                    self.assertEqual(manifest["source_sha"], SOURCE)
                    self.assertFalse(manifest["build_reuse_enabled"])
                    self.assertEqual(manifest["archive_sha256"], batch.digest(archive))
                    with tarfile.open(archive) as products:
                        self.assertEqual(products.extractfile("Build/Products/original-binary").read(),
                                         b"original synthetic executable")
                        configuration_name = "native" if scope == "coherent-native" else "ui"
                        self.assertEqual(products.extractfile("Build/Products/" + configuration_name + ".xctestrun").read(),
                                         b"original synthetic xctestrun")
                self.assertIn("native_products_preservation", receipt)
                self.assertEqual("ui_products_preservation" in receipt, failure_phase == "ui")


if __name__ == "__main__":
    unittest.main()
