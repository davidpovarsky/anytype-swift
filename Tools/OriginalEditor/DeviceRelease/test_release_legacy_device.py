#!/usr/bin/env python3
"""Actual original AmplitudeCore refusal controls, without device/UI credit."""
import argparse
import hashlib
from pathlib import Path
import struct
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_signing import (LEGACY_AMPLITUDE_DEVICE_BYTES,
    LEGACY_AMPLITUDE_DEVICE_SHA256, preserve_thin, thin_layout)


class ActualLegacyDeviceControls(unittest.TestCase):
    before = after = None

    def check(self, before=None, after=None, executable='AmplitudeCore', platform='iphoneos'):
        return preserve_thin(self.before if before is None else before,
                             self.after if after is None else after, executable, platform)

    def platform_offset(self, raw):
        count = struct.unpack_from('<I', raw, 16)[0]
        cursor = 32
        for _ in range(count):
            code, length = struct.unpack_from('<II', raw, cursor)
            if code == 0x25:
                return cursor
            cursor += length
        raise AssertionError('Actual original legacy platform is absent')

    def test_actual_original_signed_export_preserves_every_nonsignature_byte(self):
        self.assertEqual(len(self.before), LEGACY_AMPLITUDE_DEVICE_BYTES)
        self.assertEqual(hashlib.sha256(self.before).hexdigest(), LEGACY_AMPLITUDE_DEVICE_SHA256)
        value = self.check()
        self.assertEqual(value['status'], 'ALL_NONSIGNATURE_BYTES_PRESERVED')
        self.assertTrue(value['added_signature_command'])

    def test_unbound_legacy_layout_is_refused(self):
        with self.assertRaises(RuntimeError):
            thin_layout(self.before, 'AmplitudeCore', 'iphoneos')

    def test_changed_original_input_is_refused(self):
        changed = bytearray(self.before)
        changed[16384] ^= 1
        with self.assertRaises(RuntimeError):
            self.check(before=bytes(changed))

    def test_other_executable_is_refused(self):
        with self.assertRaises(RuntimeError):
            self.check(executable='AnytypeOriginalEditor')

    def test_simulator_platform_is_refused(self):
        with self.assertRaises(RuntimeError):
            self.check(platform='iphonesimulator')

    def test_changed_legacy_minimum_or_sdk_is_refused(self):
        offset = self.platform_offset(self.after)
        for field in (8, 12):
            with self.subTest(field=field):
                changed = bytearray(self.after)
                changed[offset + field] ^= 1
                with self.assertRaises(RuntimeError):
                    self.check(after=bytes(changed))

    def test_other_legacy_platform_command_is_refused(self):
        offset = self.platform_offset(self.after)
        for code in (0x24, 0x2f, 0x30):
            with self.subTest(code=code):
                changed = bytearray(self.after)
                struct.pack_into('<I', changed, offset, code)
                with self.assertRaises(RuntimeError):
                    self.check(after=bytes(changed))

    def test_changed_signed_payload_is_refused(self):
        changed = bytearray(self.after)
        changed[16384] ^= 1
        with self.assertRaises(RuntimeError):
            self.check(after=bytes(changed))

    def test_truncated_platform_command_is_refused(self):
        changed = bytearray(self.after)
        struct.pack_into('<I', changed, self.platform_offset(self.after) + 4, 8)
        with self.assertRaises(RuntimeError):
            self.check(after=bytes(changed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    ActualLegacyDeviceControls.before = args.before.read_bytes()
    ActualLegacyDeviceControls.after = args.after.read_bytes()
    unittest.main(argv=[sys.argv[0], *remaining])
