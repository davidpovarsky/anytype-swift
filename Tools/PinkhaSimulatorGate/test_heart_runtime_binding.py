"""Synthetic runtime-observer controls; no simulator is launched."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import run_ui27 as shared
import run_wave15_acceptance as wave
import wave15_batch as batch
import test_hanlin_ui_runtime as original

profiles = shared.heart_profiles


class CorrectedRuntimeObservationControls(unittest.TestCase):
    def setUp(self):
        self.fixture = original.ExistingProcessMappingControls(
            "test_existing_process_mapping_has_no_launch_and_each_command_is_bounded")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile = profiles.select(profiles.CORRECTED)
        self.binding = dict(
            runtime_profile=profiles.CORRECTED, native_marker=self.profile.binary_marker,
            heart_patch_sha256=self.profile.patch_sha256, heart_inventory_sha256=self.profile.inventory_sha256,
            heart_source_run_id="9991", heart_source_sha="a" * 40, heart_source_attempt="1",
            heart_build_receipt_sha256="b" * 64, heart_artifact_id=1001, heart_artifact_sha256="c" * 64,
            heart_proof_artifact_id=1002, heart_proof_artifact_sha256="d" * 64)
        self.relative = "Frameworks/ProtobufMessages.framework/ProtobufMessages"
        for app in (self.fixture.built, self.fixture.installed):
            (app / self.relative).write_bytes(self.profile.binary_marker.encode())

    def mapped(self, binding=None):
        source = shared.installed_runtime_source(
            original.UDID, self.fixture.evidence, self.fixture.built,
            {**original.SOURCE, **(self.binding if binding is None else binding)}, command_timeout=lambda: 7)
        return shared.observe_running_runtime(
            51457, self.fixture.evidence, self.fixture.built, source, command_timeout=lambda: 7)

    def test_exact_corrected_runtime_and_original_producer_are_bound_to_the_observed_pid(self):
        result = self.mapped()
        self.assertEqual(result["pid"], 51457)
        self.assertTrue(result["runtime_loaded"] and result["marker_present"])
        self.assertEqual({key: result[key] for key in profiles.BINDING_KEYS}, self.binding)
        self.assertTrue(all("launch" not in argv for argv, _ in self.fixture.commands))
        self.assertTrue(all(timeout == 7 for _, timeout in self.fixture.commands))

    def test_original_r14_and_partial_corrected_markers_cannot_substitute_for_the_full_runtime(self):
        for marker in (profiles.select().binary_marker, self.profile.receipt_marker,
                       self.profile.version.rsplit("-pinkha-torah-attachment", 1)[0]):
            with self.subTest(marker=marker):
                for app in (self.fixture.built, self.fixture.installed):
                    (app / self.relative).write_bytes(marker.encode())
                with self.assertRaisesRegex(RuntimeError, "bytes/marker"):
                    self.mapped()

    def test_missing_producer_proof_is_rejected_before_mapping_any_process(self):
        for key in ("heart_source_sha", "heart_source_attempt", "heart_proof_artifact_sha256"):
            value = dict(self.binding); value.pop(key)
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                self.mapped(value)
        self.assertFalse(any(argv[0] in {"ps", "/usr/bin/vmmap"} for argv, _ in self.fixture.commands))

    def test_foreign_profile_cannot_be_inferred_from_a_correct_marker(self):
        value = dict(self.binding, runtime_profile="r14")
        with self.assertRaisesRegex(RuntimeError, "selected exact full marker"):
            self.mapped(value)

    def test_a_full_marker_does_not_hide_installed_binary_drift(self):
        path = self.fixture.installed / self.relative
        path.write_bytes(path.read_bytes() + b"changed native bytes")
        with self.assertRaisesRegex(RuntimeError, "bytes/marker"):
            self.mapped()

    def test_dispatch_arguments_reach_the_actual_batch_entrypoint(self):
        for name in profiles.PROFILE_NAMES:
            argv = ["run_wave15_acceptance.py", "--app", str(self.fixture.root),
                    "--evidence", str(self.fixture.evidence), "--derived", str(self.fixture.root / "derived"),
                    "--lane", batch.RETAINED_HEART_PROFILE, "--device", "ipad", "--language", "en",
                    "--runtime-profile", name, "--heart-source-run-id", "9991"]
            with self.subTest(profile=name), patch.object(sys, "argv", argv), \
                 patch.object(batch, "run", return_value=0) as execute:
                self.assertEqual(wave.main(), 0)
                arguments = execute.call_args.args[0]
                self.assertEqual(arguments.runtime_profile, name)
                self.assertEqual(arguments.heart_source_run_id, "9991")


if __name__ == "__main__":
    unittest.main(verbosity=2)
