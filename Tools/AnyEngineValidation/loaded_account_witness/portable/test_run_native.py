"""Controls for the two portable boundaries changed by this continuation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("run_native", Path(__file__).with_name("run_native.py"))
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class PortableBoundaries(unittest.TestCase):
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
