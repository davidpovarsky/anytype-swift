"""Synthetic Release refusal controls; no Apple build or runtime acceptance."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shlex
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import collect_release_graphs as collector
from release_contract import current_build_context, write
from release_signing import preserve_thin
from release_surface import verify_public_surface

CONTRACT = json.loads((HERE.parent / 'public_host_contract.json').read_text())
ROOT = HERE.parents[2]


class ProductionSurfaceControls(unittest.TestCase):
    def graph(self):
        symbols = []
        for path, contract in CONTRACT['facades'].items():
            if contract.get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY':
                continue
            for components in contract['required']:
                symbols.append({'accessLevel': 'public', 'pathComponents': components,
                    'identifier': {'precise': 's:21AnytypeOriginalEditorSynthetic' + str(len(symbols))},
                    'location': {'uri': (ROOT / path).as_uri()}})
        return {'module': {'name': 'AnytypeOriginalEditor'}, 'symbols': symbols}

    def verify(self, graph):
        return verify_public_surface([graph], ROOT, CONTRACT)

    def test_all64_production_and22_debug_absences_are_required(self):
        value = self.verify(self.graph())
        self.assertEqual(value['reviewed_host_and_spi_requirements_observed'], 64)
        self.assertEqual(value['debug_qualification_requirements_absent'], 22)
        self.assertTrue(all(v['spi'] is False for v in value['own_public_symbols']))

    def test_every_missing_production_requirement_is_refused(self):
        for index in range(64):
            with self.subTest(index=index):
                graph = self.graph()
                graph['symbols'].pop(index)
                with self.assertRaises(ValueError):
                    self.verify(graph)

    def test_every_own_spi_marker_is_refused(self):
        for marker in [True, 1, 'true', None]:
            with self.subTest(marker=marker):
                graph = self.graph()
                graph['symbols'][0]['spi'] = marker
                with self.assertRaises(ValueError):
                    self.verify(graph)

    def test_debug_declarations_cannot_be_relabelled_public_or_relocated(self):
        debug_path = next(p for p, c in CONTRACT['facades'].items() if c.get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY')
        for location in [debug_path, 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift', None]:
            for components in CONTRACT['facades'][debug_path]['required']:
                with self.subTest(location=location, components=components):
                    graph = self.graph()
                    symbol = {'accessLevel': 'public', 'pathComponents': components,
                              'identifier': {'precise': 's:21AnytypeOriginalEditorSyntheticDebug'}}
                    if location:
                        symbol['location'] = {'uri': (ROOT / location).as_uri()}
                    graph['symbols'].append(symbol)
                    with self.assertRaises(ValueError):
                        self.verify(graph)

    def test_unowned_constructor_and_private_editor_are_refused(self):
        for components, location in [(['AnytypeOriginalEditorAccountSession', 'init()'],
                'OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift'),
                (['EditorPage'], 'Anytype/Sources/PresentationLayer/TextEditor/EditorPage.swift')]:
            graph = self.graph()
            graph['symbols'].append({'accessLevel': 'public', 'pathComponents': components,
                'identifier': {'precise': 's:21AnytypeOriginalEditorUnowned'}, 'location': {'uri': (ROOT / location).as_uri()}})
            with self.assertRaises(ValueError):
                self.verify(graph)


class ReleaseGraphControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.evidence = self.root / 'build/evidence'
        self.derived = self.root / 'build/work/producer-derived'
        target = self.derived / 'Build/Intermediates.noindex/Anytype.build/Release-Anytype-iphonesimulator/AnytypeOriginalEditor.build'
        self.graphs = target / 'DerivedSources/OriginalEditorSymbolGraphs'
        self.graphs.mkdir(parents=True)
        self.evidence.mkdir(parents=True)
        self.output = self.evidence / 'actual-public-symbol-graphs'
        self.sdk = '/SYNTHETIC/Simulator.sdk'
        self.before = {'head_sha': '1' * 40, 'run_id': 'local-11111111-1111-4111-8111-111111111111', 'run_attempt': '1',
                       'scope': 'SYNTHETIC_NO_APPLE_EXECUTION'}
        write(self.evidence / 'source-before.json', self.before)
        self.execution = {'source_sha': self.before['head_sha'], 'platform': 'iphonesimulator',
                          'execution_id': 'local-22222222-2222-4222-8222-222222222222', 'scope': 'SYNTHETIC_NO_APPLE_EXECUTION'}
        self.descriptor = self.evidence / 'release-execution.json'
        write(self.descriptor, self.execution)
        self.context = current_build_context(self.before, self.execution, self.descriptor)
        observation = patch.object(collector, 'source_observation', return_value=self.before)
        observation.start()
        self.addCleanup(observation.stop)
        self.arguments = ['builtin-SwiftDriver', '--', '/SYNTHETIC/swiftc', '-module-name', 'AnytypeOriginalEditor',
            '-target', 'arm64-apple-ios27.0-simulator', '-sdk', self.sdk, '-swift-version', '5', '-working-directory', str(self.root),
            '-D', 'RELEASE_ANYTYPE', '-D', 'PINKHA_NATIVE_DERIVED', '-O', '-emit-symbol-graph', '-emit-symbol-graph-dir', str(self.graphs),
            '-symbol-graph-minimum-access-level', 'public', '-include-spi-symbols', '-emit-module-path',
            str(target / 'Objects-normal/arm64/AnytypeOriginalEditor.swiftmodule')]
        for name, module in [('AnytypeOriginalEditor.symbols.json', 'AnytypeOriginalEditor'),
                             ('AnytypeOriginalEditor@Foundation.symbols.json', 'Foundation')]:
            write(self.graphs / name, {'module': {'name': module}, 'symbols': [{'scope': 'SYNTHETIC'}], 'relationships': []})
        self.write_build()

    def write_build(self, **changes):
        log = self.evidence / 'framework-build.stdout.log'
        log.write_text(shlex.join(self.arguments) + '\n')
        now = datetime.now(timezone.utc)
        value = {'command': ['xcodebuild', 'build', '-project', str(self.root / 'Anytype.xcodeproj'), '-scheme', 'AnytypeOriginalEditor',
            '-configuration', 'Release-Anytype', '-derivedDataPath', str(self.derived), '-resultBundlePath', str(self.evidence / 'framework-build.xcresult')],
            'cwd': str(self.root), 'started_at': (now - timedelta(seconds=5)).isoformat(), 'finished_at': (now + timedelta(seconds=5)).isoformat(),
            'returncode': 0, 'timed_out': False, 'timeout_seconds': 6000, 'stdout_sha256': collector.sha256(log),
            'scope': 'SYNTHETIC_NO_APPLE_EXECUTION'}
        value.update(changes)
        write(self.evidence / 'framework-build.command.json', value)

    def collect(self):
        return collector.collect(self.root, self.derived, self.evidence, self.sdk, self.output, 'iphonesimulator', self.context)

    def test_full_graphs_retain_bytes_and_new_owner_without_rewriting_old_source(self):
        before = (self.evidence / 'source-before.json').read_bytes()
        value = self.collect()
        self.assertEqual(value['run_id'], self.execution['execution_id'])
        self.assertEqual(before, (self.evidence / 'source-before.json').read_bytes())
        self.assertEqual({p.name: p.read_bytes() for p in self.graphs.iterdir()},
                         {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertTrue(value['include_spi_symbols'])

    def test_debug_or_unoptimized_or_filtered_compiler_is_refused(self):
        original = self.arguments[:]
        for extra in [['-D', 'DEBUG'], ['-Onone'], ['-skip-synthesized-members'], ['-include-spi-symbols=false']]:
            with self.subTest(extra=extra):
                self.arguments = [*original, *extra]
                self.write_build()
                with self.assertRaises(ValueError):
                    self.collect()

    def test_wrong_platform_missing_spi_failed_or_changed_build_is_refused(self):
        original = self.arguments[:]
        for change in ['platform', 'spi', 'failed', 'log']:
            with self.subTest(change=change):
                self.arguments = original[:]
                if change == 'platform':
                    self.arguments[self.arguments.index('-target') + 1] = 'arm64-apple-ios27.0'
                if change == 'spi':
                    self.arguments.remove('-include-spi-symbols')
                self.write_build(**({'returncode': 1} if change == 'failed' else {}))
                if change == 'log':
                    with (self.evidence / 'framework-build.stdout.log').open('a') as f:
                        f.write('UNRECORDED CHANGE\n')
                with self.assertRaises(ValueError):
                    self.collect()

    def test_old_abi_owner_cannot_be_substituted_for_new_release_compiler(self):
        self.context['run_id'] = self.before['run_id']
        with self.assertRaises(ValueError):
            self.collect()


def synthetic_image(platform_number, signature=True, signature_bytes=64):
    # A deliberately small structural fixture, never an actual executable.
    linkedit = bytearray(72)
    struct.pack_into('<II16s4Q4I', linkedit, 0, 0x19, 72, b'__LINKEDIT', 0x4000, 16384,
                     512, 64 + (signature_bytes if signature else 0), 1, 1, 0, 0)
    build = struct.pack('<6I', 0x32, 24, platform_number, 27 << 16, 27 << 16, 0)
    name = b'@rpath/Fixture.framework/Fixture\0'
    length = (24 + len(name) + 7) // 8 * 8
    install = struct.pack('<6I', 0xd, length, 24, 0, 0, 0) + name + bytes(length - 24 - len(name))
    uuid_command = struct.pack('<II16s', 0x1b, 24, bytes(range(16)))
    commands = [bytes(linkedit), build, install, uuid_command]
    if signature:
        commands.append(struct.pack('<4I', 0x1d, 16, 576, signature_bytes))
    raw_commands = b''.join(commands)
    header = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 6, len(commands), len(raw_commands), 0, 0)
    raw = header + raw_commands + bytes(384 - len(header) - len(raw_commands)) + b'C' * 128 + b'L' * 64
    if signature:
        raw += struct.pack('>3I', 0xfade0cc0, signature_bytes, 0) + bytes(signature_bytes - 12)
    return raw


class ReleaseSigningControls(unittest.TestCase):
    def test_signed_device_and_simulator_keep_every_nonsignature_byte(self):
        for platform_name, number in [('iphoneos', 2), ('iphonesimulator', 7)]:
            value = preserve_thin(synthetic_image(number), synthetic_image(number, signature_bytes=80), 'Fixture', platform_name)
            self.assertFalse(value['added_signature_command'])

    def test_first_device_signature_uses_only_zero_header_space(self):
        value = preserve_thin(synthetic_image(2, False), synthetic_image(2), 'Fixture', 'iphoneos')
        self.assertTrue(value['added_signature_command'])

    def test_changed_code_uuid_platform_or_install_name_is_refused(self):
        before = synthetic_image(2)
        for offset in [400, 32 + 72 + 24 + 56 + 12, 32 + 72 + 8, 32 + 72 + 24 + 25]:
            after = bytearray(synthetic_image(2, signature_bytes=80))
            after[offset] ^= 1
            with self.assertRaises(RuntimeError):
                preserve_thin(before, bytes(after), 'Fixture', 'iphoneos')

    def test_new_signature_cannot_replace_nonzero_header_padding(self):
        before = bytearray(synthetic_image(2, False))
        offset = 32 + struct.unpack_from('<I', before, 20)[0]
        before[offset] = 1
        with self.assertRaises(RuntimeError):
            preserve_thin(bytes(before), synthetic_image(2), 'Fixture', 'iphoneos')


if __name__ == '__main__':
    unittest.main(verbosity=2)
