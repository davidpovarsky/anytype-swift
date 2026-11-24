"""Local provenance control over the existing filesystem fixture; no compiler."""
import tempfile
from pathlib import Path
import unittest

from test_clang_product_closure import Fixture, json_write
import clang_product_closure as closure
from framework_profile import sha256


class LocalClangIdentityControl(unittest.TestCase):
    def test_local_export_preserves_identity_and_requires_explicit_provenance(self):
        with tempfile.TemporaryDirectory(prefix='local-clang-control-') as temporary:
            fixture = Fixture(Path(temporary) / 'fixture')
            execution = 'local-9f89e2b3-4b56-4f7d-bb28-cc24bd8bb55a'
            fixture.source.update(run_id=execution, execution_identity={
                'producer_kind': 'local-mac', 'local_execution_sha256': 'a' * 64})
            fixture.collection['run_id'] = execution
            proof = fixture.export()
            self.assertEqual(proof['producer_kind'], 'local-mac')
            self.assertEqual(proof['local_execution_sha256'], 'a' * 64)
            self.assertEqual(fixture.read()['module_maps'], proof['module_maps'])
            del proof['producer_kind']
            manifest = fixture.exported / closure.MANIFEST
            json_write(manifest, proof)
            fixture.identity['manifest_sha256'] = sha256(manifest)
            with self.assertRaisesRegex(ValueError, 'explicit Mac execution provenance'):
                fixture.read()


if __name__ == '__main__':
    unittest.main()
