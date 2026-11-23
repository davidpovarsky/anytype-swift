"""Focused checks for actual retained baseline reuse and observed SwiftPM layouts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

PACKET = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("continuation_support", PACKET / "continuation_support.py")
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


class ModuleProducts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.plugin = Path(self.temp.name) / "plugin"
        self.binary = self.plugin / ".build/arm64-apple-macosx/release"
        self.binary.mkdir(parents=True)
        (self.binary / "protoc-gen-swift").write_bytes(b"owned generator fixture")

    def module(self, relative="Modules/SwiftProtobuf.swiftmodule"):
        path = self.binary / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"owned module fixture")
        return path

    def resolve(self, output=None):
        return support.resolve_swiftprotobuf_products(self.plugin, output or str(self.binary) + "\n")

    def test_modules_layout(self):
        module = self.module()
        self.assertEqual(self.resolve()[1], module)

    def test_flat_layout(self):
        module = self.module("SwiftProtobuf.swiftmodule")
        self.assertEqual(self.resolve()[1], module)

    def test_target_build_layout(self):
        module = self.module("SwiftProtobuf.build/SwiftProtobuf.swiftmodule")
        self.assertEqual(self.resolve()[1], module)

    def test_architecture_module_directory(self):
        module = self.binary / "Modules/SwiftProtobuf.swiftmodule"
        module.mkdir(parents=True)
        (module / "arm64-apple-macos.swiftmodule").write_bytes(b"owned architecture fixture")
        self.assertEqual(self.resolve()[1], module)
        self.assertEqual(len(support.retain_module(module, Path(self.temp.name) / "retained")), 1)

    def test_missing_module_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "one observed"):
            self.resolve()

    def test_ambiguous_modules_rejected(self):
        self.module()
        self.module("SwiftProtobuf.build/SwiftProtobuf.swiftmodule")
        with self.assertRaisesRegex(RuntimeError, "one observed"):
            self.resolve()

    def test_foreign_bin_path_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            self.resolve(self.temp.name)

    def test_empty_generator_rejected(self):
        self.module()
        (self.binary / "protoc-gen-swift").write_bytes(b"")
        with self.assertRaisesRegex(RuntimeError, "absent or foreign"):
            self.resolve()

    def test_foreign_module_symlink_rejected(self):
        outside = Path(self.temp.name) / "foreign.swiftmodule"
        outside.write_bytes(b"foreign fixture")
        (self.binary / "SwiftProtobuf.swiftmodule").symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            self.resolve()

    def test_multiline_bin_path_rejected(self):
        self.module()
        with self.assertRaisesRegex(RuntimeError, "one absolute"):
            self.resolve(str(self.binary) + "\n" + str(self.binary))


class BaselineReuse(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.roots = {name: self.base / name for name in ("heart", "swift")}
        for root in self.roots.values():
            root.mkdir()
        self.evidence = self.base / "evidence"
        self.evidence.mkdir()
        self.archive = PACKET / support.BASELINE_ARCHIVE
        with zipfile.ZipFile(self.archive) as archive:
            self.inputs = json.loads(archive.read("ORIGINAL_GENERATOR_INPUTS.json"))
            self.outputs = json.loads(archive.read("GENERATED_OUTPUT_INDEX.json"))
            for kind, rows in self.outputs["tracked"].items():
                root = self.roots["heart" if kind == "native" else "swift"]
                for row in rows:
                    target = root / row["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read("generated/tracked/" + kind + "/" + row["path"]))

    def restore(self, archive=None):
        return support.restore_verified_baseline(
            archive or self.archive, self.inputs, self.roots, self.evidence)

    def test_actual_baseline_restores_all_741_original_rows(self):
        outputs, _ = self.restore()
        self.assertEqual(outputs, self.outputs)
        for kind, rows in outputs["baseline"].items():
            root = self.roots["heart" if kind == "native" else "swift"]
            for row in rows:
                raw = (root / row["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])
        reuse = json.loads((self.evidence / "BASELINE_REUSE.json").read_text())
        self.assertEqual(sum(reuse["rows"].values()), 741)
        self.assertEqual(reuse["baseline_swift_typecheck"], "NOT_REUSED_PREVIOUSLY_FAILED")
        self.assertEqual(set(row["status"] for row in reuse["checks"].values()), {"REUSED"})

    def test_foreign_archive_rejected_before_restore(self):
        wrong = self.base / "wrong.zip"
        wrong.write_bytes(b"wrong archive")
        with self.assertRaisesRegex(RuntimeError, "archive identity"):
            self.restore(wrong)
        self.assertFalse(any(self.evidence.iterdir()))

    def test_changed_generator_input_rejected_before_restore(self):
        self.inputs["heart"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "generator inputs differ"):
            self.restore()
        self.assertFalse(any(self.evidence.iterdir()))

    def test_changed_tracked_preimage_rejected_before_restore(self):
        target = self.roots["heart"] / self.outputs["tracked"]["native"][0]["path"]
        target.write_bytes(b"unrelated preexisting content")
        with self.assertRaisesRegex(RuntimeError, "tracked output differs"):
            self.restore()
        self.assertEqual(target.read_bytes(), b"unrelated preexisting content")
        self.assertFalse(any(self.evidence.iterdir()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
