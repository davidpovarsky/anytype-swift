"""Actual selector logic with inventory fixtures; no simulator/UI credit."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from local_execution import select_runtime_pairs

ROOT = Path(__file__).resolve().parents[2]
original = subprocess.check_output(['git', '-C', str(ROOT), 'show',
    'HEAD:Tools/PinkhaSimulatorGate/preflight.py'], text=True)
namespace = {'__name__': 'original_selector_control'}
exec(compile(original, 'original-preflight.py', 'exec'), namespace)
select_pairs = namespace['select_pairs']


class RuntimeSelectionControls(unittest.TestCase):
    def inventory(self):
        ids = ['com.apple.CoreSimulator.SimDeviceType.iPhone-17',
               'com.apple.CoreSimulator.SimDeviceType.iPad-Pro']
        return {'runtimes': [
            {'identifier': 'com.apple.CoreSimulator.SimRuntime.iOS-27-0', 'version': '27.0',
             'name': 'iOS 27.0', 'isAvailable': True, 'supportedDeviceTypes': ids},
            {'identifier': 'com.apple.CoreSimulator.SimRuntime.iOS-27-2', 'version': '27.2',
             'name': 'iOS 27.2', 'isAvailable': True, 'supportedDeviceTypes': ids}],
            'devicetypes': [{'identifier': ids[0], 'name': 'iPhone 17'},
                            {'identifier': ids[1], 'name': 'iPad Pro'}]}

    def test_default_preserves_original_runtime_policy(self):
        value, _ = select_runtime_pairs(self.inventory(), None, select_pairs)
        self.assertEqual(value['version'], '27.0')

    def test_explicit_available_27_2_requires_both_real_device_families(self):
        inventory = self.inventory()
        value, devices = select_runtime_pairs(inventory,
            'com.apple.CoreSimulator.SimRuntime.iOS-27-2', select_pairs)
        self.assertEqual(value['version'], '27.2')
        self.assertEqual(set(devices), {'ipad', 'iphone'})
        self.assertEqual(len(inventory['runtimes']), 2)

    def test_missing_or_unavailable_runtime_is_refused(self):
        for present in [True, False]:
            inventory = self.inventory()
            if present:
                inventory['runtimes'][1]['isAvailable'] = False
            else:
                inventory['runtimes'].pop()
            with self.assertRaises(RuntimeError):
                select_runtime_pairs(inventory, 'com.apple.CoreSimulator.SimRuntime.iOS-27-2', select_pairs)

    def test_duplicate_runtime_identity_is_refused(self):
        inventory = self.inventory(); inventory['runtimes'].append(inventory['runtimes'][1].copy())
        with self.assertRaises(RuntimeError):
            select_runtime_pairs(inventory, 'com.apple.CoreSimulator.SimRuntime.iOS-27-2', select_pairs)

    def test_non27_or_malformed_requested_runtime_is_refused(self):
        for value in ['com.apple.CoreSimulator.SimRuntime.iOS-26-2', 'comXappleXCoreSimulatorXSimRuntimeXiOS-27-2']:
            with self.assertRaises(RuntimeError):
                select_runtime_pairs(self.inventory(), value, select_pairs)

    def test_requested_runtime_without_both_families_is_refused(self):
        inventory = self.inventory()
        inventory['runtimes'][1]['supportedDeviceTypes'] = ['com.apple.CoreSimulator.SimDeviceType.iPhone-17']
        with self.assertRaises(RuntimeError):
            select_runtime_pairs(inventory, 'com.apple.CoreSimulator.SimRuntime.iOS-27-2', select_pairs)


if __name__ == '__main__':
    unittest.main(verbosity=2)
