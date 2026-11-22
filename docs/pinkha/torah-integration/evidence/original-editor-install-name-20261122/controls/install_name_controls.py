"""New packaging boundaries only; fixtures never earn Apple/runtime credit."""
import ast
import hashlib
import json
from pathlib import Path
import plistlib
import struct
import sys
import tempfile
import unittest

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / 'candidate/Tools/OriginalEditor'))
sys.path.insert(1, str(PACKET / 'preimage/Tools/OriginalEditor'))
import framework_install_names as gate
from framework_profile import verify_project


def named(command, name):
    start = 12 if command == gate.RPATH else 24
    value = name.encode() + b'\0'
    size = (start + len(value) + 7) // 8 * 8
    header = struct.pack('<3I', command, size, start) + b'\0' * (start - 12)
    return header + value + b'\0' * (size - start - len(value))


def binary(kind, rows=(), platform=7, cpu=0x100000C):
    commands = [struct.pack('<6I', gate.BUILD_VERSION, 24, platform, 27 << 16, 27 << 16, 0)]
    commands.extend(named(*row) for row in rows)
    body = b''.join(commands)
    return struct.pack('<8I', 0xFEEDFACF, cpu, 0, kind, len(commands), len(body), 0, 0) + body


def image(path, kind, rows=(), **kwargs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(binary(kind, rows, **kwargs))
    return path


class InstallNameControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.app = self.root / 'OriginalEditorConsumer.app'
        self.app.mkdir()
        self.info = self.app / 'Info.plist'
        self.info.write_bytes(plistlib.dumps({'CFBundleIdentifier': 'org.otzaria.acceptance.original-editor',
                                           'CFBundleExecutable': gate.CONSUMER}))
        self.framework = self.app / 'Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor'
        image(self.framework, 6, [(gate.IDENTITY, gate.INSTALL_NAME)])
        self.main = self.app / gate.CONSUMER
        self.debug = self.app / (gate.CONSUMER + '.debug.dylib')
        self.main_rows = [(gate.LOAD, gate.DEBUG_NAME), (gate.RPATH, '@executable_path'),
                          (gate.RPATH, '@executable_path/Frameworks')]
        self.debug_rows = [(gate.IDENTITY, gate.DEBUG_NAME), (gate.LOAD, gate.INSTALL_NAME),
                           (gate.RPATH, '@executable_path/Frameworks')]
        image(self.main, 2, self.main_rows)
        image(self.debug, 6, self.debug_rows)

    def test_authentic_failed_framework_prefix_is_rejected(self):
        binding = json.loads((PACKET / 'fixtures/INSTALL_NAME_BINARY_EVIDENCE.json').read_bytes())
        row = binding['rows'][0]
        raw = bytes.fromhex(row['prefix_hex'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), row['load_command_prefix_sha256'])
        parsed = gate.parse_load_commands(raw, row['file_bytes'])
        with self.assertRaisesRegex(ValueError, 'LC_ID_DYLIB'):
            gate.require_framework_identity(parsed)

    def test_authentic_failed_consumer_debug_prefix_is_rejected(self):
        binding = json.loads((PACKET / 'fixtures/INSTALL_NAME_BINARY_EVIDENCE.json').read_bytes())
        row = binding['rows'][1]
        raw = bytes.fromhex(row['prefix_hex'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), row['load_command_prefix_sha256'])
        with self.assertRaisesRegex(ValueError, 'nonrelocatable'):
            gate.target_loads(gate.parse_load_commands(raw, row['file_bytes']))
        row = binding['rows'][2]
        main = gate.parse_load_commands(bytes.fromhex(row['prefix_hex']), row['file_bytes'])
        self.assertEqual([(x['command'], x['name']) for x in main['dylibs'] if '.debug.dylib' in x['name']],
                         [(gate.LOAD, gate.DEBUG_NAME)])

    def test_valid_framework_check_preserves_all_file_bytes(self):
        before = self.framework.read_bytes()
        result = gate.verify_framework_install_name(self.framework)
        self.assertEqual(result['expected_install_name'], gate.INSTALL_NAME)
        self.assertEqual(result['image']['file_sha256'], hashlib.sha256(before).hexdigest())
        self.assertFalse(result['runtime_execution'])
        self.assertEqual(self.framework.read_bytes(), before)

    def test_actual_stub_edge_reaches_the_debug_framework_load(self):
        result = gate.verify_consumer_install_name(self.app)
        self.assertEqual([Path(x['path']).name for x in result['reachable_consumer_images']],
                         [gate.CONSUMER, gate.CONSUMER + '.debug.dylib'])
        self.assertEqual(result['framework_loads'][0]['consumer_image'], str(self.debug))
        self.assertEqual(result['binary_mutations'], 0)

    def test_direct_main_framework_load_is_admitted_without_debug_file(self):
        image(self.main, 2, [(gate.LOAD, gate.INSTALL_NAME), (gate.RPATH, '@executable_path/Frameworks')])
        self.debug.unlink()
        result = gate.verify_consumer_install_name(self.app)
        self.assertEqual(len(result['reachable_consumer_images']), 1)

    def test_unused_debug_decoy_never_grants_framework_reachability(self):
        image(self.main, 2, [(gate.RPATH, '@executable_path/Frameworks')])
        with self.assertRaisesRegex(ValueError, 'No reachable'):
            gate.verify_consumer_install_name(self.app)

    def test_absolute_framework_load_is_refused(self):
        image(self.debug, 6, [(gate.IDENTITY, gate.DEBUG_NAME),
                             (gate.LOAD, '/Library/Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor')])
        with self.assertRaisesRegex(ValueError, 'nonrelocatable'):
            gate.verify_consumer_install_name(self.app)

    def test_weak_framework_load_cannot_grant_acceptance(self):
        image(self.debug, 6, [(gate.IDENTITY, gate.DEBUG_NAME), (0x80000018, gate.INSTALL_NAME)])
        with self.assertRaisesRegex(ValueError, 'weak'):
            gate.verify_consumer_install_name(self.app)

    def test_duplicate_framework_load_is_refused(self):
        image(self.debug, 6, self.debug_rows + [(gate.LOAD, gate.INSTALL_NAME)])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            gate.verify_consumer_install_name(self.app)

    def test_correct_debug_load_cannot_hide_bad_main_framework_load(self):
        image(self.main, 2, self.main_rows + [(gate.LOAD, '/wrong/AnytypeOriginalEditor')])
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            gate.verify_consumer_install_name(self.app)

    def test_absolute_debug_edge_is_refused(self):
        image(self.main, 2, [(gate.LOAD, '/tmp/OriginalEditorConsumer.debug.dylib'),
                            (gate.RPATH, '@executable_path/Frameworks')])
        with self.assertRaisesRegex(ValueError, 'debug-image edge'):
            gate.verify_consumer_install_name(self.app)

    def test_weak_debug_edge_is_refused(self):
        image(self.main, 2, [(0x80000018, gate.DEBUG_NAME), (gate.RPATH, '@executable_path/Frameworks')])
        with self.assertRaisesRegex(ValueError, 'debug-image edge'):
            gate.verify_consumer_install_name(self.app)

    def test_duplicate_debug_edge_is_refused(self):
        image(self.main, 2, self.main_rows + [(gate.LOAD, gate.DEBUG_NAME)])
        with self.assertRaisesRegex(ValueError, 'debug-image edge'):
            gate.verify_consumer_install_name(self.app)

    def test_wrong_debug_identity_is_refused(self):
        image(self.debug, 6, [(gate.IDENTITY, '@rpath/Other.debug.dylib'), (gate.LOAD, gate.INSTALL_NAME)])
        with self.assertRaisesRegex(ValueError, 'unexpected identity'):
            gate.verify_consumer_install_name(self.app)

    def test_missing_reachable_debug_file_is_refused(self):
        self.debug.unlink()
        with self.assertRaises(FileNotFoundError):
            gate.verify_consumer_install_name(self.app)

    def test_bad_embedded_framework_identity_is_refused(self):
        image(self.framework, 6, [(gate.IDENTITY, '/Library/Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor')])
        with self.assertRaisesRegex(ValueError, 'LC_ID_DYLIB'):
            gate.verify_consumer_install_name(self.app)

    def test_missing_or_duplicate_framework_identity_is_refused(self):
        for rows in [[], [(gate.IDENTITY, gate.INSTALL_NAME)] * 2]:
            with self.subTest(rows=rows):
                image(self.framework, 6, rows)
                with self.assertRaisesRegex(ValueError, 'LC_ID_DYLIB'):
                    gate.verify_framework_install_name(self.framework)

    def test_device_platform_is_refused(self):
        image(self.debug, 6, self.debug_rows, platform=2)
        with self.assertRaisesRegex(ValueError, 'iOS Simulator'):
            gate.verify_consumer_install_name(self.app)

    def test_foreign_or_fat_architecture_is_not_silently_skipped(self):
        for magic, cpu in [(0xFEEDFACF, 0x1000007), (0xCAFEBABE, 0x100000C)]:
            raw = bytearray(binary(6, [(gate.IDENTITY, gate.INSTALL_NAME)], cpu=cpu))
            struct.pack_into('<I', raw, 0, magic)
            with self.subTest(magic=magic, cpu=cpu), self.assertRaisesRegex(ValueError, 'thin arm64'):
                gate.parse_load_commands(bytes(raw), len(raw))

    def test_truncated_or_excess_load_region_is_refused(self):
        raw = binary(6, [(gate.IDENTITY, gate.INSTALL_NAME)])
        for candidate, size in [(raw[:-1], len(raw)), (raw + b'\0', len(raw) + 1), (raw, len(raw) - 1)]:
            with self.subTest(length=len(candidate), declared=size), self.assertRaisesRegex(ValueError, 'region'):
                gate.parse_load_commands(candidate, size)

    def test_bad_load_command_extent_alignment_and_count_are_refused(self):
        original = binary(6, [(gate.IDENTITY, gate.INSTALL_NAME)])
        for offset, value in [(36, 0), (36, 25), (36, 0x100000), (16, 1), (16, 3)]:
            raw = bytearray(original)
            struct.pack_into('<I', raw, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(ValueError):
                gate.parse_load_commands(bytes(raw), len(raw))

    def test_invalid_dylib_string_offset_or_termination_is_refused(self):
        original = binary(6, [(gate.IDENTITY, gate.INSTALL_NAME)])
        # The first command is the 24-byte build version; the dylib starts at 56.
        for value in [0, 23, 0x100000]:
            raw = bytearray(original)
            struct.pack_into('<I', raw, 64, value)
            with self.subTest(offset=value), self.assertRaisesRegex(ValueError, 'string offset'):
                gate.parse_load_commands(bytes(raw), len(raw))
        raw = original[:80] + original[80:].replace(b'\0', b'X')
        with self.assertRaisesRegex(ValueError, 'string'):
            gate.parse_load_commands(raw, len(raw))

    def test_alias_of_binary_is_refused(self):
        actual = self.root / 'actual-image'
        self.framework.rename(actual)
        self.framework.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'unaliased'):
            gate.verify_framework_install_name(self.framework)

    def test_wrong_consumer_bundle_identity_is_refused(self):
        self.info.write_bytes(plistlib.dumps({'CFBundleIdentifier': 'unrelated', 'CFBundleExecutable': gate.CONSUMER}))
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            gate.verify_consumer_install_name(self.app)

    def test_missing_framework_or_debug_resolution_path_is_refused(self):
        for rows in [[(gate.LOAD, gate.DEBUG_NAME), (gate.RPATH, '@executable_path')],
                     [(gate.LOAD, gate.DEBUG_NAME), (gate.RPATH, '@executable_path/Frameworks')]]:
            image(self.main, 2, rows)
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, 'rpath|resolvable'):
                gate.verify_consumer_install_name(self.app)

    def test_four_target_settings_pass_the_complete_original_project_inverse(self):
        raw = (PACKET / 'candidate/Anytype.xcodeproj/project.pbxproj').read_bytes()
        baseline = (PACKET / 'preimage/Tools/OriginalEditor/original_project.pbxproj').read_bytes()
        profile = json.loads((PACKET / 'candidate/Tools/OriginalEditor/framework_profile.json').read_bytes())
        proof = verify_project(raw, baseline, profile)
        self.assertTrue(proof['whole_project_inverse_exact'])
        self.assertEqual(proof['framework_install_name_setting'], '@rpath/$(EXECUTABLE_PATH)')
        self.assertEqual(raw.replace(b'\t\t\t\t"LD_DYLIB_INSTALL_NAME" = "@rpath/$(EXECUTABLE_PATH)";\n', b''),
                         (PACKET / 'preimage/Anytype.xcodeproj/project.pbxproj').read_bytes())

    def test_missing_target_setting_is_refused_even_with_rebound_project_hash(self):
        raw = (PACKET / 'candidate/Anytype.xcodeproj/project.pbxproj').read_bytes()
        baseline = (PACKET / 'preimage/Tools/OriginalEditor/original_project.pbxproj').read_bytes()
        profile = json.loads((PACKET / 'candidate/Tools/OriginalEditor/framework_profile.json').read_bytes())
        altered = raw.replace(b'"LD_DYLIB_INSTALL_NAME" = "@rpath/$(EXECUTABLE_PATH)";',
                              b'"LD_DYLIB_INSTALL_NAME" = "/Library/Frameworks/$(EXECUTABLE_PATH)";', 1)
        profile['candidate_project_sha256'] = hashlib.sha256(altered).hexdigest()
        with self.assertRaisesRegex(ValueError, 'explicitly relocatable'):
            verify_project(altered, baseline, profile)

    def test_old_flow_test_bodies_remain_exact_despite_two_new_explicit_boundaries(self):
        relative = 'Tools/OriginalEditor/test_framework_flow.py'
        before, after = [(PACKET / directory / relative).read_text() for directory in ['preimage', 'candidate']]
        def bodies(source):
            return {node.name: ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(source))
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}
        self.assertEqual(len(bodies(before)), 10)
        self.assertEqual(bodies(before), bodies(after))
        additions = "            stack.enter_context(patch.object(driver, 'verify_framework_install_name', return_value={\n                'scope': 'EXPLICIT_MACHO_BOUNDARY_DOUBLE_NO_NATIVE_BINARY_ACCEPTANCE'}))\n            stack.enter_context(patch.object(driver, 'verify_consumer_install_name', return_value={\n                'scope': 'EXPLICIT_MACHO_BOUNDARY_DOUBLE_NO_NATIVE_BINARY_ACCEPTANCE'}))\n"
        additions += "            stack.enter_context(patch.object(driver, 'retain_built_consumer', return_value={\n                'scope': 'EXPLICIT_SIGNED_APP_RETENTION_BOUNDARY_DOUBLE_NO_APP_ARCHIVE'}))\n"
        self.assertEqual(after.replace(additions, '', 1), before)


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print('START ' + test.id(), flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        print('PASS ' + test.id(), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2, testRunner=unittest.TextTestRunner(resultclass=RecordedResult, verbosity=2))
