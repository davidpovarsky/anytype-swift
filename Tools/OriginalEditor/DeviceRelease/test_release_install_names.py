#!/usr/bin/env python3
"""Focused parser/route refusal controls; fixtures grant no native runtime credit."""
import argparse
import hashlib
from pathlib import Path
import plistlib
import shutil
import struct
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_install_names as gate

INSTALL = '@rpath/AnytypeOriginalEditor.framework/AnytypeOriginalEditor'


def string_command(code, text):
    offset = 12 if code == 0x8000001c else 24
    encoded = text.encode() + b'\0'
    size = (offset + len(encoded) + 7) // 8 * 8
    return struct.pack('<3I', code, size, offset) + bytes(offset - 12) + encoded + bytes(size - offset - len(encoded))


def image(platform, kind=6, identity=INSTALL, weak=False, rpath=True, duplicate=False):
    build = struct.pack('<6I', 0x32, 24, platform, 0x001b0000, 0x001b0000, 0)
    commands = [build]
    if duplicate:
        commands.append(build)
    if kind == 6:
        commands.append(string_command(0xd, identity))
    else:
        if rpath:
            commands.append(string_command(0x8000001c, '@executable_path/Frameworks'))
        commands.append(string_command(0x80000018 if weak else 0xc, identity))
    return struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, kind, len(commands), sum(map(len, commands)), 0, 0) + b''.join(commands)


class ReleasePlatformControls(unittest.TestCase):
    source_root = None

    def parse(self, raw, platform):
        return gate.parse_load_commands(raw, len(raw), platform, source_root=self.source_root)

    def consumer(self, folder, platform=2, embedded=2, **options):
        app = folder / 'OriginalEditorConsumer.app'
        binary = app / 'Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(image(embedded))
        (app / 'OriginalEditorConsumer').write_bytes(image(platform, kind=2, **options))
        (app / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'org.otzaria.acceptance.original-editor', 'CFBundleExecutable': 'OriginalEditorConsumer'}))
        return app

    def test_simulator_parser_is_exact_original_result_and_ast(self):
        reader, proof = gate.original_reader(self.source_root, 'iphonesimulator')
        raw = image(7)
        self.assertEqual(self.parse(raw, 'iphonesimulator'), reader.parse_load_commands(raw, len(raw)))
        self.assertEqual(proof['original_ast_sha256'], proof['effective_ast_sha256'])
        self.assertEqual(proof['only_specialization'], 'none')

    def test_device_keeps_actual_platform_and_authentic_prefix_digest(self):
        raw = image(2)
        value = self.parse(raw, 'iphoneos')
        self.assertEqual(value['build_versions'][0]['platform'], 2)
        self.assertEqual(value['prefix_sha256'], hashlib.sha256(raw).hexdigest())

    def test_platforms_cannot_be_interchanged(self):
        for actual, requested in [(2, 'iphonesimulator'), (7, 'iphoneos'), (1, 'iphoneos')]:
            with self.subTest(actual=actual, requested=requested), self.assertRaises(ValueError):
                self.parse(image(actual), requested)

    def test_unsupported_platform_is_refused(self):
        for platform in ['macosx', '', None]:
            with self.subTest(platform=platform), self.assertRaises(ValueError):
                self.parse(image(2), platform)

    def test_duplicate_platform_commands_are_refused(self):
        with self.assertRaises(ValueError):
            self.parse(image(2, duplicate=True), 'iphoneos')

    def test_truncated_or_unbounded_original_regions_are_refused(self):
        raw = image(2)
        with self.assertRaises(ValueError):
            self.parse(raw[:-1], 'iphoneos')
        changed = bytearray(raw)
        struct.pack_into('<I', changed, 20, 1024 * 1024 + 8)
        with self.assertRaises(ValueError):
            self.parse(bytes(changed), 'iphoneos')

    def test_actual_file_framework_identity_and_alias_rules_remain(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            binary = folder / 'AnytypeOriginalEditor'
            binary.write_bytes(image(2))
            value = gate.verify_framework_install_name(binary, 'iphoneos', source_root=self.source_root)
            self.assertEqual(value['status'], 'ACTUAL_FRAMEWORK_INSTALL_NAME_PASS')
            self.assertEqual(value['binary_mutations'], 0)
            alias = folder / 'alias'
            alias.symlink_to(binary)
            with self.assertRaises(ValueError):
                gate.verify_framework_install_name(alias, 'iphoneos', source_root=self.source_root)
            binary.write_bytes(image(2, identity='/tmp/AnytypeOriginalEditor'))
            with self.assertRaises(ValueError):
                gate.verify_framework_install_name(binary, 'iphoneos', source_root=self.source_root)

    def test_device_consumer_and_embedded_framework_keep_real_platform2(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = self.consumer(Path(temporary).resolve())
            value = gate.verify_consumer_install_name(app, 'iphoneos', source_root=self.source_root)
            self.assertEqual(value['status'], 'ACTUAL_CONSUMER_RELOCATABLE_LOAD_PASS')
            self.assertEqual(value['embedded_framework']['image']['build_versions'][0]['platform'], 2)
            self.assertEqual(value['reachable_consumer_images'][0]['build_versions'][0]['platform'], 2)
            self.assertFalse(value['runtime_execution'])

    def test_device_consumer_rejects_embedded_simulator_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = self.consumer(Path(temporary).resolve(), embedded=7)
            with self.assertRaises(ValueError):
                gate.verify_consumer_install_name(app, 'iphoneos', source_root=self.source_root)

    def test_device_consumer_rejects_weak_load_and_missing_rpath(self):
        for options in [{'weak': True}, {'rpath': False}]:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as temporary:
                app = self.consumer(Path(temporary).resolve(), **options)
                with self.assertRaises(ValueError):
                    gate.verify_consumer_install_name(app, 'iphoneos', source_root=self.source_root)

    def test_changed_qualified_source_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            helper = root / 'Tools/OriginalEditor/framework_install_names.py'
            helper.parent.mkdir(parents=True)
            original = self.source_root / 'Tools/OriginalEditor/framework_install_names.py'
            helper.write_bytes(original.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                gate.original_reader(root, 'iphoneos')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    args, rest = parser.parse_known_args()
    ReleasePlatformControls.source_root = args.source_root
    unittest.main(argv=[sys.argv[0], *rest])
