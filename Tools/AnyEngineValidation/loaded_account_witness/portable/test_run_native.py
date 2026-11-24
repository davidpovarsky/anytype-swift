"""Controls for the two portable boundaries changed by this continuation."""
import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("run_native", Path(__file__).with_name("run_native.py"))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class PortableBoundaries(unittest.TestCase):
    def test_source_delta_refuses_tampering_ambiguous_callsite_and_symlink(self):
        before = b"if err = nativeLease.CheckCurrent(); err != nil {\n"
        after = before.replace(b"CheckCurrent()", b"CheckCurrent(f.ctx)")
        delta = {"before_bytes": len(before), "before_sha256": hashlib.sha256(before).hexdigest(),
                 "after_bytes": len(after), "after_sha256": hashlib.sha256(after).hexdigest(),
                 "replace_before": "nativeLease.CheckCurrent()", "replace_after": "nativeLease.CheckCurrent(f.ctx)"}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.go"
            path.write_bytes(before)
            native.replace_exact_source(path, delta)
            self.assertEqual(path.read_bytes(), after)
            with self.assertRaisesRegex(RuntimeError, "identity"):
                native.replace_exact_source(path, delta)
            path.write_bytes(before)
            bad = dict(delta, after_sha256="0" * 64)
            with self.assertRaisesRegex(RuntimeError, "result_identity"):
                native.replace_exact_source(path, bad)
            self.assertEqual(path.read_bytes(), before)
            ambiguous = before * 2
            path.write_bytes(ambiguous)
            bad = dict(delta, before_bytes=len(ambiguous), before_sha256=hashlib.sha256(ambiguous).hexdigest())
            with self.assertRaisesRegex(RuntimeError, "single_callsite"):
                native.replace_exact_source(path, bad)
            alias = Path(td) / "alias.go"
            alias.symlink_to(path)
            with self.assertRaisesRegex(RuntimeError, "regular"):
                native.replace_exact_source(alias, delta)

    def test_archive_paths_reject_escape_and_ambiguous_spellings(self):
        for value in ("/etc/passwd", "rootfs/../secret", "rootfs//a", "rootfs/./a", "rootfs\\a", ""):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                native.relative_member(value)
        self.assertEqual(str(native.relative_member("rootfs/mnt/development/file.go")), "rootfs/mnt/development/file.go")

    def test_generated_main_is_bound_to_actual_work_not_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            work = root / "go-build123"
            (work / "b001").mkdir(parents=True)
            source = work / "b001/_testmain.go"
            source.write_bytes(b"x" * 3282)
            log = root / "build.stderr"
            log.write_text("WORK=" + str(work) + "\n")
            with patch.object(native, "GENERATED_SHA", native.sha(source)):
                self.assertEqual(native.generated_main(root, log), source)
                source.write_bytes(b"y" * 3282)
                with self.assertRaisesRegex(RuntimeError, "identity"):
                    native.generated_main(root, log)

    def test_generated_main_rejects_external_work_and_ambiguous_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            log = root / "build.stderr"
            log.write_text("WORK=/tmp/go-build123\n")
            with self.assertRaisesRegex(RuntimeError, "scope"):
                native.generated_main(root, log)
            log.write_text("WORK=" + str(root / "go-build1") + "\nWORK=" + str(root / "go-build2") + "\n")
            with self.assertRaisesRegex(RuntimeError, "single"):
                native.generated_main(root, log)


if __name__ == "__main__":
    unittest.main()
