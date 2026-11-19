"""Synthetic Mach-O parser controls; these do not prove actual simulator Keychain access."""
import plistlib
import struct
import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import run_ui27

from simulator_identity import (inspect_simulator_entitlements, verify_simulator_keychain_identity,
                                verify_simulator_shared_app_group)


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

    def test_implicit_app_id_default_keychain_group_is_accepted(self):
        for groups in [[], None]:
            if groups is None:
                self.entitlements.pop('keychain-access-groups', None)
            else:
                self.entitlements['keychain-access-groups'] = groups
            result = inspect_simulator_entitlements(control_binary(self.entitlements))
            self.assertEqual(verify_simulator_keychain_identity(result), 'FAKETEAMID.io.anytype.app')

    def test_foreign_default_keychain_group_is_rejected(self):
        self.entitlements['keychain-access-groups'] = ['OTHER.group', 'FAKETEAMID.io.anytype.app']
        result = inspect_simulator_entitlements(control_binary(self.entitlements))
        with self.assertRaisesRegex(ValueError, 'unexpected default Keychain access group'):
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


class SimulatorSharedGroupControls(unittest.TestCase):
    bundle_ids = ('io.anytype.app', 'io.anytype.app.AnytypeShareExtension',
                  'io.anytype.app.AnytypeNotificationExtension')

    def result(self, bundle, groups):
        return inspect_simulator_entitlements(control_binary({
            'application-identifier': 'FAKETEAMID.' + bundle,
            'com.apple.security.application-groups': groups,
        }))

    def test_existing_runtime_conditions_select_their_original_group_for_all_consumers(self):
        for condition, group in [('DEBUG', 'group.io.anytype.app.dev'),
                                 ('RELEASE_NIGHTLY', 'group.io.anytype.app.dev'),
                                 ('RELEASE_ANYTYPE', 'group.io.anytype.app')]:
            for bundle in self.bundle_ids:
                with self.subTest(condition=condition, bundle=bundle):
                    identity = verify_simulator_shared_app_group(self.result(bundle, [group]),
                        dict(CFBundleIdentifier=bundle, CompilationCondition=condition),
                        application_prefix='FAKETEAMID', compilation_condition=condition)
                    self.assertEqual(identity['application_group'], group)
                    self.assertEqual(identity['bundle_identifier'], bundle)

    def test_observed_debug_production_mismatch_and_missing_or_extra_groups_are_rejected(self):
        for groups in [['group.io.anytype.app'], [], ['group.io.anytype.app.dev', 'group.io.anytype.app']]:
            with self.subTest(groups=groups), self.assertRaisesRegex(ValueError, 'app group differs'):
                verify_simulator_shared_app_group(self.result('io.anytype.app', groups),
                    dict(CFBundleIdentifier='io.anytype.app', CompilationCondition='DEBUG'),
                    application_prefix='FAKETEAMID', compilation_condition='DEBUG')

    def test_changed_extension_compilation_condition_cannot_hide_a_different_container(self):
        with self.assertRaisesRegex(ValueError, 'compilation conditions differ'):
            verify_simulator_shared_app_group(
                self.result(self.bundle_ids[1], ['group.io.anytype.app']),
                dict(CFBundleIdentifier=self.bundle_ids[1], CompilationCondition='RELEASE_ANYTYPE'),
                application_prefix='FAKETEAMID', compilation_condition='DEBUG')

    def test_missing_condition_or_foreign_team_cannot_qualify_original_group_identity(self):
        info = dict(CFBundleIdentifier='io.anytype.app', CompilationCondition='DEBUG')
        result = self.result('io.anytype.app', ['group.io.anytype.app.dev'])
        with self.assertRaisesRegex(ValueError, 'application identity differs'):
            verify_simulator_shared_app_group(result, info,
                application_prefix='OTHERTEAM', compilation_condition='DEBUG')
        info.pop('CompilationCondition')
        with self.assertRaisesRegex(ValueError, 'unsupported compilation condition'):
            verify_simulator_shared_app_group(result, info,
                application_prefix='FAKETEAMID', compilation_condition='DEBUG')

    def built_app(self, root, *, wrong_extension_group=False, missing_notification=False):
        app = root / 'Anytype.app'
        entries = [(app, 'io.anytype.app'),
                   (app / 'PlugIns/AnytypeShareExtension.appex', self.bundle_ids[1]),
                   (app / 'PlugIns/AnytypeWidgetExtension.appex', 'io.anytype.app.homewidget')]
        if not missing_notification:
            entries.append((app / 'PlugIns/AnytypeNotificationServiceExtension.appex', self.bundle_ids[2]))
        for directory, bundle in entries:
            directory.mkdir(parents=True)
            (directory / 'Info.plist').write_bytes(plistlib.dumps(dict(
                CFBundleIdentifier=bundle, CFBundleExecutable='ActualExecutable', CompilationCondition='DEBUG')))
            group = 'group.io.anytype.app' if wrong_extension_group and bundle == self.bundle_ids[1] else 'group.io.anytype.app.dev'
            entitlements = {'application-identifier': 'FAKETEAMID.' + bundle}
            if bundle != 'io.anytype.app.homewidget':
                entitlements['com.apple.security.application-groups'] = [group]
            (directory / 'ActualExecutable').write_bytes(control_binary(entitlements))
        return app

    def test_existing_build_gate_records_main_and_both_group_consumers_and_unchanged_widget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = self.built_app(root)
            with patch.object(run_ui27, 'command'), patch.object(run_ui27.subprocess, 'run',
                    return_value=SimpleNamespace(stdout=plistlib.dumps({}))):
                run_ui27.verify_signed_simulator(app, root)
            import json
            result = json.loads((root / 'simulator-shared-group-identities.json').read_text())
            self.assertEqual(len(result['identities']), 4)
            consumers = [x for x in result['identities'] if 'application_group' in x]
            self.assertEqual({x['bundle_identifier'] for x in consumers}, set(self.bundle_ids))
            self.assertTrue(all(x['application_group'] == 'group.io.anytype.app.dev' for x in consumers))
            self.assertIn('CONTAINER_ACCESS_NOT_YET_RUN', result['status'])

    def test_existing_build_gate_refuses_wrong_group_or_missing_original_extension(self):
        for kwargs, error in [(dict(wrong_extension_group=True), 'app group differs'),
                              (dict(missing_notification=True), 'extension is missing')]:
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                app = self.built_app(root, **kwargs)
                with patch.object(run_ui27, 'command'), patch.object(run_ui27.subprocess, 'run',
                        return_value=SimpleNamespace(stdout=plistlib.dumps({}))):
                    with self.assertRaisesRegex((ValueError, RuntimeError), error):
                        run_ui27.verify_signed_simulator(app, root)
                self.assertFalse((root / 'simulator-shared-group-identities.json').exists())
