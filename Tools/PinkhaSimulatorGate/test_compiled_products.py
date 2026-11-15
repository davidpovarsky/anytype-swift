"""Small inventory controls; no actual build/test products or acceptance claim."""
import json
from pathlib import Path
import tempfile
import unittest

from compiled_products import capture_products


class CompiledProductControls(unittest.TestCase):
    def test_test_binary_configuration_and_dependency_changes_are_hash_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            products = root / 'derived/Build/Products'
            paths = ['Release/Anytype.app/PlugIns/AnytypeTests.xctest/AnytypeTests',
                     'Anytype.xctestrun', 'Release/Dependency.framework/Dependency', 'UI27-native.xctestrun']
            for path in paths:
                file = products / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(('synthetic-' + path).encode())
            (products.parent / 'PinkhaSourceInputs.json').write_text(json.dumps(dict(source_sha='a' * 40, inputs={})))
            captured = capture_products(root / 'derived', root / 'evidence', 'a' * 40, ['control'])
            manifest = json.loads((root / 'evidence/compiled-products/manifest.json').read_text())
            self.assertEqual(len(manifest['products']), 3)
            self.assertNotIn('UI27-native.xctestrun', manifest['products'])
            self.assertFalse(captured['build_reuse_enabled'])
            self.assertFalse(manifest['every_entry_build_origin_verified'])
            first = manifest['products']['Anytype.xctestrun']['sha256']
            (products / 'Anytype.xctestrun').write_text('different synthetic configuration')
            capture_products(root / 'derived', root / 'evidence2', 'a' * 40, ['control'])
            second = json.loads((root / 'evidence2/compiled-products/manifest.json').read_text())
            self.assertNotEqual(first, second['products']['Anytype.xctestrun']['sha256'])

    def test_missing_native_test_product_cannot_be_attested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'derived/Build/Products').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'configuration missing'):
                capture_products(root / 'derived', root / 'evidence', 'a' * 40, [])
