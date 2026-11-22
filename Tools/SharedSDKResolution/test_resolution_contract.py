"""New portable lock-admission controls only; no simulated Apple pass."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('resolution', HERE / 'resolve_packages.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CONTRACT = json.loads((HERE / 'contract.json').read_bytes())
ORIGINAL = json.loads((HERE / 'original-anytype-Package.resolved').read_bytes())


class OriginalLockAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.original = copy.deepcopy(ORIGINAL)
        self.target = copy.deepcopy(CONTRACT['targets']['anytype'])
        self.expected = MODULE.expected_pins(self.original, self.target)
        self.actual = MODULE.seed_lock(self.original, self.expected)

    def test_real44_plus_exact7_retains_every_original_pin_and_metadata(self):
        self.assertEqual(len(self.expected), 51)
        self.assertEqual({k: v for k, v in self.actual.items() if k != 'pins'},
                         {k: v for k, v in self.original.items() if k != 'pins'})
        for pin in self.original['pins']:
            self.assertEqual(pin, self.expected[pin['identity']])
        MODULE.verify_resolved(self.actual, self.expected)

    def test_existing_revision_change_is_rejected(self):
        self.actual['pins'] = copy.deepcopy(self.actual['pins'])
        self.actual['pins'][0]['state']['revision'] = '0' * 40
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_existing_url_change_is_rejected_even_with_same_revision(self):
        self.actual['pins'] = copy.deepcopy(self.actual['pins'])
        self.actual['pins'][0]['location'] += '.git'
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_existing_version_change_is_rejected_even_with_same_revision(self):
        self.actual['pins'] = copy.deepcopy(self.actual['pins'])
        self.actual['pins'][0]['state']['version'] = '999.0.0'
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_missing_runtime_addition_is_rejected(self):
        self.actual['pins'] = [p for p in self.actual['pins'] if p['identity'] != 'iosmath']
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_unreviewed_transitive_addition_is_rejected(self):
        pin = copy.deepcopy(self.actual['pins'][0])
        pin['identity'] = 'unreviewed-package'
        self.actual['pins'] = [*self.actual['pins'], pin]
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_duplicate_identity_is_rejected(self):
        self.actual['pins'] = [*self.actual['pins'], copy.deepcopy(self.actual['pins'][0])]
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            MODULE.verify_resolved(self.actual, self.expected)

    def test_seed_cannot_replace_existing_pin(self):
        self.target['expected_new_pins'].append(copy.deepcopy(self.original['pins'][0]))
        with self.assertRaisesRegex(RuntimeError, 'replaces an original pin'):
            MODULE.expected_pins(self.original, self.target)

    def test_actual_version2_lock_does_not_require_invented_origin_hash(self):
        original = {'pins': copy.deepcopy(self.original['pins']), 'version': 2}
        MODULE.verify_resolved(original, MODULE.pin_map(original))
        original['originHash'] = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'version2'):
            MODULE.verify_resolved(original, MODULE.pin_map(original))

    def test_missing_or_malformed_version3_hash_is_rejected(self):
        for value in (None, '', 'fake', True):
            with self.subTest(value=value):
                candidate = dict(self.actual, originHash=value)
                with self.assertRaisesRegex(RuntimeError, 'originHash'):
                    MODULE.verify_resolved(candidate, self.expected)


if __name__ == '__main__':
    unittest.main()
