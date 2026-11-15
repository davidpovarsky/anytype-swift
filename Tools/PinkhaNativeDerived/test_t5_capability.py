import copy
import json
from pathlib import Path
import unittest

from build_custom_heart import t5_related_capability


class T5CapabilityTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.inventory = json.loads((root / 'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-15/native-heart-integration.json').read_text())
        self.patch = self.inventory['patch_sha256']

    def test_old_inventory_does_not_advertise_expanded_feature(self):
        self.assertIsNone(t5_related_capability({'patch_sha256': 'old'}, 'old'))

    def test_exact_new_pair_has_independent_marker_but_remains_disabled(self):
        capability = t5_related_capability(self.inventory, self.patch)
        self.assertEqual(capability['marker'], 'pinkha-native-t5-lookup-v1-' + self.patch)
        self.assertEqual(capability['version'], 1)
        self.assertEqual(capability['client_enablement'], 'DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF')

    def test_wrong_patch_version_generation_or_missing_fixture_fails_closed(self):
        for key, value in [('patch_sha256', 'other'), ('public_projection_version', 2),
                           ('cache_proof_generation', 'pinkha-torah-cache-v1'),
                           ('client_enablement', 'ENABLED')]:
            with self.subTest(key=key):
                inventory = copy.deepcopy(self.inventory)
                inventory[key] = value
                with self.assertRaises(RuntimeError):
                    t5_related_capability(inventory, self.patch)
        inventory = copy.deepcopy(self.inventory)
        inventory['features']['t5_related_lookup'] = 2
        with self.assertRaises(RuntimeError):
            t5_related_capability(inventory, self.patch)
        inventory = copy.deepcopy(self.inventory)
        inventory['files'] = []
        with self.assertRaises(RuntimeError):
            t5_related_capability(inventory, self.patch)


if __name__ == '__main__':
    unittest.main()
