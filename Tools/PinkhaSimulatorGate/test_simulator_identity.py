"""Synthetic Mach-O parser controls; these do not prove actual simulator Keychain access."""
import plistlib
import struct
import unittest

from simulator_identity import inspect_simulator_entitlements, verify_simulator_keychain_identity


def control_binary(entitlements):
    raw = plistlib.dumps(entitlements)
    offset = 32 + 72 + 80 + 24
    header = struct.pack('<IIIIIIII', 0xfeedfacf, 0x0100000c, 0, 2, 2, 176, 0, 0)
    segment = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__TEXT', 0, offset + len(raw), 0,
                          offset + len(raw), 7, 5, 1, 0)
    section = struct.pack('<16s16sQQIIIIIIII', b'__entitlements', b'__TEXT', offset, len(raw),
                          offset, 0, 0, 0, 0, 0, 0, 0)
    build = struct.pack('<IIIIII', 0x32, 24, 7, 15 << 16, 27 << 16, 0)
    return header + segment + section + build + raw


class SimulatorIdentityControls(unittest.TestCase):
    def setUp(self):
        self.entitlements = {'application-identifier': 'FAKETEAMID.io.anytype.app',
                             'keychain-access-groups': ['FAKETEAMID.io.anytype.app']}

    def test_actual_section_is_required_instead_of_a_signature_only_assumption(self):
        result = inspect_simulator_entitlements(control_binary(self.entitlements))
        self.assertEqual(verify_simulator_keychain_identity(result), 'FAKETEAMID.io.anytype.app')
        self.assertEqual(result['entitlements'], self.entitlements)

    def test_foreign_bundle_identity_is_rejected(self):
        self.entitlements['application-identifier'] = 'FAKETEAMID.foreign.app'
        result = inspect_simulator_entitlements(control_binary(self.entitlements))
        with self.assertRaisesRegex(ValueError, 'expected application identity'):
            verify_simulator_keychain_identity(result)

    def test_missing_keychain_group_is_rejected_after_raw_section_inspection(self):
        self.entitlements['keychain-access-groups'] = []
        result = inspect_simulator_entitlements(control_binary(self.entitlements))
        with self.assertRaisesRegex(ValueError, 'default Keychain access group'):
            verify_simulator_keychain_identity(result)

    def test_invalid_section_offset_cannot_be_treated_as_an_entitlement(self):
        data = bytearray(control_binary(self.entitlements))
        struct.pack_into('<I', data, 32 + 72 + 48, len(data) + 100)
        with self.assertRaisesRegex(ValueError, 'section range'):
            inspect_simulator_entitlements(data)

    def test_physical_ios_macho_cannot_supply_simulator_identity(self):
        data = bytearray(control_binary(self.entitlements))
        struct.pack_into('<I', data, 32 + 72 + 80 + 8, 2)
        with self.assertRaisesRegex(ValueError, 'target iOS Simulator SDK27'):
            inspect_simulator_entitlements(data)
