#!/usr/bin/env python3
"""New source-binding checks only; this does not execute an Apple build."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Tools/MiniApps"))
import resolved_dependencies as resolver


class DependencyResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.macro_source = Path(os.environ["PINKHA_MACRO_SOURCE"]).resolve()
        if subprocess.check_output(["git", "-C", str(cls.macro_source), "rev-parse", "HEAD"],
                                   text=True).strip() != resolver.MACRO["revision"]:
            raise RuntimeError("Checks require the actual original macro checkout")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="miniapps-resolution-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.app.mkdir()
        self.evidence = self.root / "evidence"
        self.derived = self.root / "derived"
        link = self.derived / "SourcePackages/checkouts/equatable"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.macro_source, target_is_directory=True)
        self.project = self.app / resolver.LOCKS[0]
        self.project.parent.mkdir(parents=True)
        self.original_pin = {"identity": "original", "kind": "remoteSourceControl",
                             "location": "https://github.com/example/original",
                             "state": {"version": "1.0.0", "revision": "1" * 40}}
        self.macro_pin = {"identity": resolver.MACRO["identity"], "kind": "remoteSourceControl",
                          "location": resolver.MACRO["location"],
                          "state": {"version": resolver.MACRO["version"],
                                    "revision": resolver.MACRO["revision"]}}
        self.write_lock(self.project, [self.original_pin])
        (self.app / "Source.swift").write_text("// Original application source.\n")
        self.git("init", "--quiet")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "-m", "Original fixture source")
        self.source = self.git("rev-parse", "HEAD").decode().strip()
        self.write_lock(self.project, [self.original_pin, self.macro_pin])

    def git(self, *arguments):
        return subprocess.check_output(["git", "-C", str(self.app), *arguments],
                                       stderr=subprocess.PIPE)

    @staticmethod
    def write_lock(path, pins):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 3, "pins": pins}, indent=2) + "\n")

    def record(self, stage="native"):
        return resolver.record_resolution(self.app, self.evidence, self.derived,
                                          self.source, "source-check-run", "1", stage)

    def verify(self, run="source-check-run"):
        return resolver.verify_recorded_resolution(self.app, self.evidence, self.derived,
                                                   self.source, run, "1")

    def test_native_and_ui_keep_the_real_macro_and_declared_resolution_delta(self):
        native = self.record()
        self.assertEqual(native["generated_tracked_deltas"], [resolver.LOCKS[0]])
        self.assertEqual(native["macro"]["revision"], resolver.MACRO["revision"])
        self.assertEqual(native["activation_arguments"], ["-skipMacroValidation"])
        self.assertEqual(self.verify(), native)
        self.write_lock(self.app / resolver.LOCKS[1], [self.original_pin, self.macro_pin])
        final = self.record("ui")
        self.assertEqual(self.verify(), final)
        self.assertEqual(final["source_integrity"], "TRACKED_RESOLUTION_DELTA_RECORDED")
        self.assertEqual(len(final["locks"]), 2)

    def test_changed_application_source_is_rejected(self):
        self.record()
        (self.app / "Source.swift").write_text("// Unexpected source edit.\n")
        with self.assertRaisesRegex(RuntimeError, "Tracked source changed"):
            self.verify()

    def test_lock_bytes_and_run_identity_cannot_change_after_recording(self):
        proof = self.record()
        with self.assertRaisesRegex(RuntimeError, "source/run"):
            self.verify("another-run")
        data = self.project.read_bytes()
        self.project.write_bytes(data + b" ")
        with self.assertRaisesRegex(RuntimeError, "dependency bytes changed"):
            self.verify()
        self.project.write_bytes(data)
        snapshot = self.evidence / proof["locks"][0]["resolved_snapshot"]
        snapshot.write_bytes(snapshot.read_bytes() + b" ")
        with self.assertRaisesRegex(RuntimeError, "dependency bytes changed"):
            self.verify()

    def test_ui_cannot_resolve_a_different_native_dependency(self):
        self.record()
        different = {**self.original_pin, "state": {"version": "1.1.0", "revision": "2" * 40}}
        self.write_lock(self.app / resolver.LOCKS[1], [different, self.macro_pin])
        with self.assertRaisesRegex(RuntimeError, "different source for original"):
            self.record("ui")

    def test_unapproved_macro_revision_is_rejected(self):
        wrong = {**self.macro_pin, "state": {**self.macro_pin["state"], "revision": "0" * 40}}
        self.write_lock(self.project, [self.original_pin, wrong])
        with self.assertRaisesRegex(RuntimeError, "original 1.4.1 source"):
            self.record()


if __name__ == "__main__":
    unittest.main(verbosity=2)
