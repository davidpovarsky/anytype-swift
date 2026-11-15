"""Run the actual packager against a small exported-attachment regression fixture."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


class EvidencePackagingTests(unittest.TestCase):
    def test_exported_media_and_extensionless_snapshots_survive_with_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            retained = ['ui/smoke-attachments/manifest.json',
                        'ui/smoke-attachments/EXTENSIONLESS-SNAPSHOT',
                        'ui/smoke-attachments/screen.mp4',
                        'ui/smoke-attachments/screen.heic',
                        'ui/smoke.xcresult/Data/data.0', 'execution.json']
            excluded = ['DerivedData-UI/large.bin', 'SourcePackages/checkout/source.txt',
                        'unrelated.bin']
            for name in retained + excluded:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            subprocess.run([sys.executable, str(Path(__file__).with_name('package_evidence.py')), str(root)],
                           check=True, capture_output=True)
            with zipfile.ZipFile(root / 'Pinkha-Native-Derived-Evidence.zip') as archive:
                self.assertEqual(set(archive.namelist()), set(retained))
                for name in retained:
                    self.assertEqual(archive.read(name), name.encode())


if __name__ == '__main__':
    unittest.main()
