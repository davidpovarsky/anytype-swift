"""Focused candidate identity controls, with no native or Apple execution."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HELPER = Path(__file__).with_name("prepare_native_runtime.py")
spec = importlib.util.spec_from_file_location("prepared_runtime_helper", HELPER)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class PreparedRuntimeVersionTests(unittest.TestCase):
    def manifest(self, version=None, explicit=False):
        value = {
            "any": {"upstreamCommit": runtime.PINNED_COMMITS["any"]},
            "sdk": {"upstreamCommit": runtime.PINNED_COMMITS["sdk"],
                    "upstreamTagObject": "b161a0475479bbe7d9d693bc496c6fdd90c3969b"},
        }
        if explicit:
            value["nativeVersion"] = version
        return value

    def test_default_and_candidate_identity_do_not_mutate_manifest(self):
        for manifest, expected in (
            (self.manifest(), runtime.VERSION),
            (self.manifest(runtime.VERSION, True), runtime.VERSION),
            (self.manifest(runtime.PREPARED_MIGRATION_VERSION, True), runtime.PREPARED_MIGRATION_VERSION),
        ):
            before = copy.deepcopy(manifest)
            self.assertEqual(runtime.native_version(manifest), expected)
            self.assertEqual(manifest, before)

    def test_unknown_identity_is_rejected_before_any_source_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "candidate.json"
            for version in (None, False, [], {}, 42, "", "v0.5.0-pinkha.2", "v0.5.0-pinkha.prepared.1 "):
                path.write_text(json.dumps(self.manifest(version, True)), encoding="utf-8")
                with patch.object(runtime, "git", side_effect=AssertionError("source access before rejection")):
                    with self.assertRaisesRegex(ValueError, "Unknown native source-manifest version"):
                        runtime.apply(SimpleNamespace(manifest=path, any_root=root / "native", output=root / "receipt.json"))
                self.assertFalse((root / "receipt.json").exists())

    def test_production_and_candidate_artifacts_cannot_cross_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "candidate.json"
            artifact = root / "artifact"
            artifact.mkdir()
            for manifest, artifact_version in (
                (self.manifest(), runtime.PREPARED_MIGRATION_VERSION),
                (self.manifest(runtime.PREPARED_MIGRATION_VERSION, True), runtime.VERSION),
            ):
                path.write_text(json.dumps(manifest), encoding="utf-8")
                (artifact / "native-artifact.json").write_text(json.dumps({
                    "schemaVersion": 1, "version": artifact_version,
                }), encoding="utf-8")
                with patch.object(runtime, "validate_artifact_source", side_effect=AssertionError("wrong binary admitted")):
                    with self.assertRaisesRegex(ValueError, "Unrecognized native artifact"):
                        runtime.install(SimpleNamespace(manifest=path, artifact=artifact, producer_commit=None))
            self.assertFalse((root / "Vendor").exists())

    def test_actual_version_cli_uses_manifest_not_ambient_build_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            for manifest, expected in (
                (self.manifest(), runtime.VERSION),
                (self.manifest(runtime.PREPARED_MIGRATION_VERSION, True), runtime.PREPARED_MIGRATION_VERSION),
            ):
                path.write_text(json.dumps(manifest), encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(HELPER), "--manifest", str(path), "version"],
                    capture_output=True, text=True, encoding="utf-8", timeout=20,
                    env={**os.environ, "ANY_BUILD_VERSION": "unrelated-ambient-value"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected + "\n")


if __name__ == "__main__":
    unittest.main()
