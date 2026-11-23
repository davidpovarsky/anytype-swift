"""Focused controls for fresh, concurrent executable inventory reads.

All bytes and manifests come from real bounded filesystem fixtures. These
controller controls do not claim an Apple runtime or native UI pass.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
import run_ui27 as shared


class ConcurrentSourceScans(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.built = self.root / "built/Anytype.app"
        self.installed = self.root / "installed/Anytype.app"
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.magic = bytes.fromhex("cffaedfe")
        for app in (self.built, self.installed):
            app.mkdir(parents=True)
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Anytype"}))
            (app / "Anytype").write_bytes(self.magic + b"main executable")
            (app / "Anytype.debug.dylib").write_bytes(self.magic + b"original entrypoint")
            for index in range(110):
                carrier = app / "Frameworks" / f"Code{index}.framework" / f"Code{index}"
                carrier.parent.mkdir(parents=True)
                carrier.write_bytes(self.magic + bytes([index]) * 1024)
                (carrier.parent / "Info.plist").write_bytes(
                    plistlib.dumps({"CFBundleExecutable": carrier.name}))
            (app / "Resources").mkdir()
            for index in range(12):
                (app / "Resources" / f"text{index}.txt").write_text(f"resource {index}")
            (app / "entry-alias").symlink_to("Anytype.debug.dylib")
        self.timeout_calls = []
        def container(argv, **kwargs):
            self.assertEqual(argv, ["xcrun", "simctl", "get_app_container", "owned-device",
                                    "io.anytype.app", "app"])
            self.assertEqual(kwargs["timeout"], 10)
            return str(self.installed)
        patcher = patch.object(shared.subprocess, "check_output", side_effect=container)
        patcher.start()
        self.addCleanup(patcher.stop)

    def source(self):
        return shared.installed_runtime_source(
            "owned-device", self.evidence, self.built, {"source_sha": "a" * 40},
            command_timeout=lambda: 10)

    def test_both_fresh_full_inventories_overlap_with_identical_original_manifests(self):
        original_scan = shared.code_carriers
        expected = {app: original_scan(app) for app in (self.installed, self.built)}
        barrier = threading.Barrier(2, timeout=2)
        lock = threading.Lock()
        active, maximum, calls = [0], [0], []

        def scan(app):
            with lock:
                active[0] += 1
                maximum[0] = max(maximum[0], active[0])
                calls.append(app)
            try:
                barrier.wait()
                return original_scan(app)
            finally:
                with lock:
                    active[0] -= 1

        with patch.object(shared, "code_carriers", side_effect=scan):
            value = self.source()
        self.assertEqual(maximum, [2])
        self.assertEqual(active, [0])
        self.assertCountEqual(calls, [self.installed, self.built])
        self.assertEqual(value["installed_code_carriers"], expected[self.installed])
        self.assertEqual(value["built_code_carriers"], expected[self.built])
        self.assertEqual(len(value["installed_code_carriers"]["manifest"]["carriers"]), 112)
        self.assertEqual(value["installed_code_carriers"]["sha256"],
                         value["built_code_carriers"]["sha256"])
        self.assertEqual(value["status"], "MATCHED_BYTES_PROCESS_NOT_YET_VERIFIED")
        self.assertFalse(value["full_bundle_equivalence"])
        self.assertEqual(json.loads((self.evidence / "installed-app-source.json").read_text()), value)
        target = os.environ.get("HANLIN_SOURCE_SCAN_EVIDENCE")
        if target:
            directory = Path(target)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "concurrent-manifests.json").write_text(json.dumps({
                "scope": "CONTROLLER_FIXTURE_NOT_APPLE",
                "active_maximum": maximum[0], "active_after_return": active[0],
                "source_sha256": hashlib.sha256(Path(shared.__file__).read_bytes()).hexdigest(),
                "control_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "installed_manifest": value["installed_code_carriers"],
                "built_manifest": value["built_code_carriers"],
                "exact_original_manifest_equality": True,
            }, indent=2) + "\n")

    def test_mismatch_and_failed_scan_remain_closed_with_no_background_worker(self):
        target = self.installed / "Frameworks/Code7.framework/Code7"
        original = target.read_bytes()
        target.write_bytes(self.magic + b"modified code")
        with self.assertRaisesRegex(RuntimeError, "code carriers differ"):
            self.source()
        target.write_bytes(original)
        original_scan = shared.code_carriers
        active = [0]
        lock = threading.Lock()

        def scan(app):
            with lock:
                active[0] += 1
            try:
                return original_scan(app)
            finally:
                with lock:
                    active[0] -= 1

        outside = self.root / "outside"
        outside.write_bytes(self.magic + b"external bytes")
        target.unlink()
        target.symlink_to(outside)
        with patch.object(shared, "code_carriers", side_effect=scan):
            with self.assertRaisesRegex(RuntimeError, "outside the actual bundle|external dependency"):
                self.source()
        self.assertEqual(active, [0])
        self.assertEqual(json.loads((self.evidence / "installed-app-source.json").read_text())["status"],
                         "FAIL")


if __name__ == "__main__":
    unittest.main()
