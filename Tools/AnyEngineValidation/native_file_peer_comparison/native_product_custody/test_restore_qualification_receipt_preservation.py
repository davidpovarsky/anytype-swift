"""One disposable existing-receipt control; never enter native qualification."""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest


class RestoreQualificationReceiptPreservationTests(unittest.TestCase):
    def test_existing_result_is_preserved_before_native_custody_reads(self):
        original = Path(__file__).with_name('qualify_restore_exclusive.py').read_bytes()
        with tempfile.TemporaryDirectory(prefix='pinkha-receipt-preservation-disposable-') as name:
            root = Path(name)
            controller = root / 'qualify_restore_exclusive.py'
            controller.write_bytes(original)
            receipt = root / 'result.json'
            prior = b'{"status":"ORIGINAL_DISPOSABLE_RECEIPT","opaque":"preserve every byte"}\n'
            with receipt.open('xb') as stream:
                stream.write(prior)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(receipt, 0o640)
            os.utime(receipt, ns=(1600000000123456789, 1600000000987654321))

            def identity():
                value = receipt.stat()
                return (value.st_dev, value.st_ino, value.st_size, value.st_mode,
                        value.st_uid, value.st_gid, value.st_mtime_ns, value.st_ctime_ns,
                        value.st_nlink, hashlib.sha256(receipt.read_bytes()).hexdigest())

            before = identity()
            environment = os.environ.copy()
            environment['PYTHONDONTWRITEBYTECODE'] = '1'
            completed = subprocess.run([sys.executable, '-B', str(controller)],
                cwd=root, env=environment, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=5, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(completed.stdout, b'')
            self.assertIn(b'FileExistsError', completed.stderr)
            self.assertNotIn(b'AssertionError', completed.stderr)
            self.assertEqual(receipt.read_bytes(), prior)
            self.assertEqual(identity(), before)
            self.assertEqual(controller.read_bytes(), original)
            self.assertEqual(sorted(path.name for path in root.iterdir()),
                             ['qualify_restore_exclusive.py', 'result.json'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
