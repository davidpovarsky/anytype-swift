"""Real Git/filesystem packaging controls; no Clang, Apple, native or API execution."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import clang_product_closure as closure
from framework_products import consumer_project
from framework_profile import TARGET, blob, sha256
from pbx_source import loads
from retain_unqualified_products import retain


FIXTURE = json.loads((Path(__file__).with_name('module_maps_fixture.json')).read_text())
GENERATED_ROOTS = {
    'GoogleUtilities-UserDefaults': 'GoogleUtilities/GoogleUtilities/UserDefaults/Public',
    'GoogleUtilities-Network': 'GoogleUtilities/GoogleUtilities/Network/Public',
    'GoogleUtilities-NSData': 'GoogleUtilities/GoogleUtilities/NSData+zlib/Public',
    'GoogleUtilities-AppDelegateSwizzler': 'GoogleUtilities/GoogleUtilities/AppDelegateSwizzler/Public',
    'GoogleUtilities-Logger': 'GoogleUtilities/GoogleUtilities/Logger/Public',
    'GoogleUtilities-Environment': 'GoogleUtilities/GoogleUtilities/Environment/Public',
    'third-party-IsAppEncrypted': 'GoogleUtilities/third_party/IsAppEncrypted/Public',
    'GoogleUtilities-Reachability': 'GoogleUtilities/GoogleUtilities/Reachability/Public',
    'GoogleDataTransport': 'GoogleDataTransport/GoogleDataTransport/GDTCORLibrary/Public',
    'nanopb': 'nanopb/spm_headers',
    'FirebaseInstallations': 'firebase-ios-sdk/FirebaseInstallations/Source/Library/Public',
    'FirebaseCore': 'firebase-ios-sdk/FirebaseCore/Sources/Public',
    'FirebaseMessaging': 'firebase-ios-sdk/FirebaseMessaging/Sources/Public',
}


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def json_write(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def git(root, *args):
    environment = {**os.environ, 'GIT_AUTHOR_DATE': '2026-11-22T00:00:00Z',
                   'GIT_COMMITTER_DATE': '2026-11-22T00:00:00Z',
                   'GIT_AUTHOR_NAME': 'Explicit Clang Fixture', 'GIT_COMMITTER_NAME': 'Explicit Clang Fixture',
                   'GIT_AUTHOR_EMAIL': 'fixture@invalid.example', 'GIT_COMMITTER_EMAIL': 'fixture@invalid.example'}
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                          check=True, timeout=30, env=environment).stdout.decode().strip()


class Fixture:
    def __init__(self, root):
        self.root = root.resolve()
        self.root.mkdir(parents=True)
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'core.autocrlf', 'false')
        write(self.root / '.gitignore', b'build/\n')
        write(self.root / 'EXPLICIT_FIXTURE.txt', b'Local Git/filesystem controls only; no dependency compilation.\n')
        self.work = self.root / 'build/work'
        self.evidence = self.root / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.derived = self.work / 'producer-derived'
        self.exported = self.work / 'distribution'
        self.checkouts = self.derived / 'SourcePackages/checkouts'
        self.generated = self.derived / 'Build/Intermediates.noindex/GeneratedModuleMaps-iphonesimulator'
        self.generated.mkdir(parents=True)
        (self.exported / 'Include').mkdir(parents=True)
        self.package_names = {'googledatatransport': 'GoogleDataTransport', 'googleutilities': 'GoogleUtilities',
                              'iosmath': 'iosMath'}
        self.packages = {}
        for pin in FIXTURE['actual_pins']:
            identity = pin['identity']
            name = self.package_names.get(identity, identity)
            package = self.checkouts / name
            package.mkdir(parents=True)
            git(package, 'init', '-q')
            git(package, 'config', 'core.autocrlf', 'false')
            write(package / '.gitignore', b'ignored.h\n')
            write(package / 'EXPLICIT_INTERNAL.h', b'/* explicit packaging fixture; no native API */\n')
            write(package / 'DoNotCompile.c', b'#error original translation units must never enter the consumer\n')
            self.packages[name] = package
        for row in FIXTURE['maps']:
            name = self.package_names.get(row['identity'], row['identity'])
            path = self.checkouts / name / row['path']
            raw = row['content'].encode()
            if blob(raw) != row['sha']:
                raise AssertionError('The six upstream module maps lost exact Git provenance')
            write(path, raw)
            for header in re.findall(rb'(?:umbrella\s+header|header)\s+"([^"]+)"', raw):
                write(path.parent / header.decode(), b'/* explicit packaging fixture; not the original header API */\n')
        catomic = self.checkouts / 'swift-markdown/Sources/CAtomic/include/CAtomic.h'
        write(catomic, FIXTURE['catomic']['content'].encode())
        if blob(catomic.read_bytes()) != FIXTURE['catomic']['sha']:
            raise AssertionError('The original CAtomic header lost exact Git provenance')
        for relative in GENERATED_ROOTS.values():
            write(self.checkouts / relative / 'EXPLICIT_GENERATED_HEADER.h',
                  b'/* explicit generated-map path fixture; no original API substituted */\n')
        nanopb = self.checkouts / 'nanopb'
        write(nanopb / 'Real.h', b'/* actual filesystem alias target fixture */\n')
        (nanopb / 'Middle.h').symlink_to('Real.h')
        (nanopb / 'spm_headers/Alias.h').symlink_to('../Middle.h')
        self.maps = [self.remap(path) for path in FIXTURE['actual_modulemap_paths']]
        self.arguments = []
        for path in self.maps:
            self.arguments += ['-Xcc', '-fmodule-map-file=' + str(path)]
            if path.parent == self.generated:
                header_root = self.checkouts / GENERATED_ROOTS[path.stem]
                raw = ('// EXPLICIT generated-map fixture, not retained Apple output\n'
                       'module EXPLICIT_' + re.sub('[^A-Za-z0-9_]', '_', path.stem)
                       + ' { umbrella "' + str(header_root) + '" export * module * { export * } }\n').encode()
                write(path, raw)
        for value in FIXTURE['actual_header_arguments']:
            if value.startswith('-I'):
                path = self.remap(value[2:])
                self.arguments += ['-Xcc', '-I' + str(path)]
                if path.suffix != '.hmap':
                    path.mkdir(parents=True, exist_ok=True)
        self.lock = self.root / 'Package.resolved'
        self.refresh_pins()
        git(self.root, 'add', '.gitignore', 'EXPLICIT_FIXTURE.txt', 'Package.resolved')
        git(self.root, 'commit', '-qm', 'Explicit package fixture only')
        self.source = {'head_sha': git(self.root, 'rev-parse', 'HEAD'), 'run_id': '90009422605', 'run_attempt': '1'}
        self.collection = {'status': 'ACTUAL_COMPILER_FULL_GRAPHS_COLLECTED_SURFACE_NOT_YET_VERIFIED',
                           'module': TARGET, 'target': 'arm64-apple-ios27.0-simulator',
                           'source_sha': self.source['head_sha'], 'run_id': self.source['run_id'],
                           'run_attempt': '1', 'compiler_line_sha256': '1' * 64,
                           'compiler_arguments': self.arguments,
                           'fixture_scope': 'EXPLICIT_SOURCE_AND_APPLE_COMPILER_RECEIPT_FIXTURE_NO_COMPILER_EXECUTION'}

    def remap(self, original):
        return self.derived / original.split('/producer-derived/', 1)[1]

    def refresh_pins(self):
        pins, dependencies = [], []
        for original in FIXTURE['actual_pins']:
            identity = original['identity']
            name = self.package_names.get(identity, identity)
            package = self.packages[name]
            git(package, 'add', '-A')
            git(package, 'commit', '--allow-empty', '-qm', 'Explicit packaging fixture, not upstream source')
            revision = git(package, 'rev-parse', 'HEAD')
            pins.append({'identity': identity, 'state': {'revision': revision}})
            dependencies.append({'packageRef': {'identity': identity}, 'subpath': name,
                                 'state': {'name': 'sourceControlCheckout', 'checkoutState': {'revision': revision}}})
        json_write(self.lock, {'pins': pins, 'fixture_original_pins': FIXTURE['actual_pins']})
        json_write(self.derived / 'SourcePackages/workspace-state.json', {'object': {'dependencies': dependencies}})

    def export(self):
        self.proof = closure.export_clang_declarations(self.derived, self.exported, self.collection, self.source, self.lock)
        self.identity = {key: self.proof[key] for key in ('source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256')}
        self.identity['manifest_sha256'] = sha256(self.exported / closure.MANIFEST)
        return self.proof

    def read(self):
        return closure.read_clang_imports(self.exported, self.identity)

    def retention_inputs(self):
        write(self.exported / ('Frameworks/' + TARGET + '.framework/' + TARGET), b'EXPLICIT_NOT_A_NATIVE_BINARY')
        self.execution = {'status': 'FAIL', 'original_framework_build': 'PASS', 'source_sha': self.source['head_sha'],
                          'run_id': self.source['run_id'], 'run_attempt': '1', 'phase': 'EXPLICIT_CONSUMER_FAILURE_FIXTURE',
                          'error': 'EXPLICIT_NO_APPLE_EXECUTION', 'external_consumer_build': 'NOT_RUN'}
        json_write(self.evidence / 'execution.json', self.execution)
        json_write(self.evidence / 'source-before.json', self.source)
        json_write(self.evidence / 'source-after.json', self.source)
        json_write(self.evidence / 'framework-build.command.json',
                   {'returncode': 0, 'timed_out': False, 'scope': 'EXPLICIT_BUILD_RECEIPT_NO_BUILD_EXECUTED'})
        with zipfile.ZipFile(self.evidence / 'Pinkha-Native-Derived-Evidence.zip', 'x') as archive:
            archive.writestr('EXPLICIT_FIXTURE.txt', 'Synthetic acceptance receipts; no native build')
        return {'GITHUB_SHA': self.source['head_sha'], 'GITHUB_RUN_ID': self.source['run_id'], 'GITHUB_RUN_ATTEMPT': '1'}


class OriginalClangDeclarationControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='original-clang-controls-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def fixture(self, name='fixture'):
        return Fixture(self.base / name)

    def test_all_nineteen_maps_and_six_original_bytes_export_without_producer_paths(self):
        f = self.fixture()
        proof = f.export()
        self.assertEqual(len(proof['module_maps']), 19)
        self.assertEqual(len(proof['packages']), 8)
        for row in FIXTURE['maps']:
            name = f.package_names.get(row['identity'], row['identity'])
            self.assertEqual((f.exported / 'Clang/Packages' / name / row['path']).read_bytes(), row['content'].encode())
        self.assertFalse(proof['consumer_or_native_qualification'])
        f.derived.rename(f.derived.with_name('producer-derived-preserved'))
        self.assertFalse(f.derived.exists())
        self.assertEqual(f.read()['module_maps'], proof['module_maps'])
        for relative in proof['module_maps']:
            self.assertNotIn(str(f.derived).encode(), (f.exported / relative).read_bytes())

    def test_generated_relocation_preserves_exact_nonpath_tokens_and_inverse(self):
        f = self.fixture()
        proof = f.export()
        generated = [row for row in proof['module_map_provenance'] if row['transformation'] == 'EXACT_DECLARATION_PATH_RELOCATION']
        self.assertEqual(len(generated), 13)
        for row in generated:
            original = Path(row['source']).read_bytes()
            actual = (f.exported / row['path']).read_bytes()
            expected = original
            for change in row['path_substitutions']:
                self.assertEqual(original[change['start']:change['finish']].decode(), change['original'])
                expected = expected.replace(('"' + change['original'] + '"').encode(),
                                            ('"' + change['replacement'] + '"').encode(), 1)
            self.assertEqual(actual, expected)
            self.assertEqual((f.exported / 'SourceProvenance/OriginalClangModuleMaps' / (Path(row['path']).name + '.txt')).read_bytes(), original)

    def test_git_tracked_alias_chain_is_materialized_and_translation_units_are_absent(self):
        f = self.fixture()
        proof = f.export()
        alias = f.exported / 'Clang/Packages/nanopb/spm_headers/Alias.h'
        self.assertFalse(alias.is_symlink())
        self.assertEqual(alias.read_bytes(), (f.checkouts / 'nanopb/Real.h').read_bytes())
        row = proof['packages']['nanopb']['original_tracked_declarations']['spm_headers/Alias.h']
        self.assertEqual(row['literal_alias'], '../Middle.h')
        self.assertEqual(row['target_provenance']['literal_alias'], 'Real.h')
        self.assertFalse(any(Path(name).suffix in {'.c', '.m', '.mm', '.cpp', '.swift'} for name in proof['files']))
        self.assertFalse(proof['implementation_translation_units_exported_or_added'])

    def test_committed_alias_escape_and_cycle_are_refused(self):
        for mode in ('escape', 'cycle'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                alias = f.checkouts / 'nanopb/spm_headers/Alias.h'
                alias.unlink()
                alias.symlink_to('../../swift-markdown/Sources/CAtomic/include/CAtomic.h' if mode == 'escape' else 'Alias.h')
                f.refresh_pins()
                with self.assertRaises(ValueError):
                    f.export()

    def test_changed_tracked_header_and_untracked_ignored_header_are_refused(self):
        for mode in ('tracked', 'ignored'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                path = f.checkouts / 'nanopb' / ('Real.h' if mode == 'tracked' else 'ignored.h')
                path.write_bytes(b'UNREVIEWED_INPUT')
                with self.assertRaisesRegex(ValueError, 'modified or untracked'):
                    f.export()

    def test_pin_drift_or_foreign_actual_compiler_identity_is_refused(self):
        for mode in ('pin', 'head', 'run', 'attempt', 'target'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                if mode == 'pin':
                    value = json.loads(f.lock.read_bytes())
                    value['pins'][0]['state']['revision'] = 'f' * 40
                    json_write(f.lock, value)
                else:
                    key = {'head': 'source_sha', 'run': 'run_id', 'attempt': 'run_attempt', 'target': 'target'}[mode]
                    f.collection[key] = 'FOREIGN'
                with self.assertRaises(ValueError):
                    f.export()

    def test_duplicate_missing_and_foreign_modulemap_inputs_are_refused(self):
        for mode in ('duplicate', 'missing', 'foreign'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                if mode == 'duplicate':
                    f.arguments += ['-Xcc', '-fmodule-map-file=' + str(f.maps[0])]
                elif mode == 'missing':
                    f.maps[5].unlink()
                else:
                    foreign = self.base / 'foreign.modulemap'
                    foreign.write_text('module FOREIGN {}')
                    f.arguments += ['-Xcc', '-fmodule-map-file=' + str(foreign)]
                with self.assertRaises((ValueError, FileNotFoundError)):
                    f.export()

    def test_foreign_header_root_and_generated_header_reference_are_refused(self):
        for mode in ('root', 'map'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                foreign = self.base / ('outside-' + mode)
                foreign.mkdir()
                if mode == 'root':
                    f.arguments += ['-Xcc', '-I' + str(foreign)]
                else:
                    f.maps[5].write_text('module EXPLICIT_BAD { umbrella "' + str(foreign) + '" export * }')
                with self.assertRaisesRegex(ValueError, 'Unreviewed non-package|escapes the original'):
                    f.export()

    def test_generated_unsupported_quoted_directive_is_refused_with_raw_evidence(self):
        f = self.fixture()
        raw = b'module EXPLICIT_BAD { link "borrowed-library" export * }\n'
        f.maps[5].write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'unsupported quoted directive'):
            f.export()
        retained = f.exported / 'SourceProvenance/OriginalClangModuleMaps' / (f.maps[5].name + '.txt')
        self.assertEqual(retained.read_bytes(), raw)

    def test_existing_export_and_aliased_export_root_cannot_be_overwritten(self):
        f = self.fixture('existing')
        f.export()
        digest = sha256(f.exported / closure.MANIFEST)
        with self.assertRaisesRegex(ValueError, 'stale Clang'):
            f.export()
        self.assertEqual(sha256(f.exported / closure.MANIFEST), digest)
        f = self.fixture('alias')
        real = f.exported.with_name('actual-distribution')
        f.exported.rename(real)
        f.exported.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'root is an alias'):
            f.export()

    def test_exported_mutation_extra_member_and_alias_are_refused(self):
        for mode in ('mutated', 'extra', 'alias', 'include-extra', 'translation-unit'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                f.export()
                path = f.exported / 'Clang/Packages/nanopb/Real.h'
                if mode == 'mutated':
                    path.write_bytes(b'CHANGED')
                elif mode == 'alias':
                    path.unlink()
                    path.symlink_to('Middle.h')
                else:
                    relative = {'include-extra': 'Include/EXTRA.h', 'translation-unit': 'Include/EXTRA.c'}.get(
                        mode, 'Clang/Packages/nanopb/EXTRA.h')
                    path = f.exported / relative
                    path.write_bytes(b'UNRECORDED')
                with self.assertRaisesRegex(ValueError, 'differs|alias|membership|translation unit'):
                    f.read()

    def test_manifest_traversal_and_missing_root_and_tampered_identity_are_refused(self):
        for mode in ('traversal', 'missing-root', 'source', 'run', 'attempt', 'lock', 'digest',
                     'duplicate-map', 'duplicate-root', 'provenance', 'schema'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                f.export()
                manifest = f.exported / closure.MANIFEST
                value = json.loads(manifest.read_bytes())
                if mode == 'traversal':
                    value['header_search_paths'][0] = '../outside'
                elif mode == 'missing-root':
                    value['header_search_paths'][0] = 'Clang/Packages/nanopb/ABSENT'
                elif mode == 'duplicate-map':
                    value['module_maps'].append(value['module_maps'][0])
                elif mode == 'duplicate-root':
                    value['header_search_paths'].append(value['header_search_paths'][0])
                elif mode == 'provenance':
                    value['module_map_provenance'][0]['exported_sha256'] = 'f' * 64
                elif mode == 'schema':
                    value['schema'] = 2
                else:
                    key = {'source': 'source_sha', 'run': 'run_id', 'attempt': 'run_attempt',
                           'lock': 'original_package_lock_sha256', 'digest': 'compiler_line_sha256'}[mode]
                    value[key] = 'FOREIGN'
                json_write(manifest, value)
                if mode != 'digest':
                    f.identity['manifest_sha256'] = sha256(manifest)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    f.read()

    def test_real_consumer_project_uses_only_exported_maps_headers_and_one_swift_source(self):
        f = self.fixture()
        proof = f.export()
        importer = f.root / 'ConsumerApp.swift'
        importer.write_text('import AnytypeOriginalEditor\n')
        f.derived.rename(f.derived.with_name('producer-derived-preserved'))
        project = consumer_project(f.work / 'consumer', f.exported, importer, [], f.identity)
        data = loads((project / 'project.pbxproj').read_text())['objects']
        swift = [value for value in data.values() if value.get('lastKnownFileType') == 'sourcecode.swift']
        self.assertEqual([value['path'] for value in swift], ['ConsumerApp.swift'])
        self.assertFalse(any(value['isa'] in {'XCSwiftPackageProductDependency', 'XCRemoteSwiftPackageReference'} for value in data.values()))
        configurations = [value['buildSettings'] for value in data.values()
                          if value.get('isa') == 'XCBuildConfiguration' and 'OTHER_SWIFT_FLAGS' in value.get('buildSettings', {})]
        self.assertTrue(configurations)
        for settings in configurations:
            flags = settings['OTHER_SWIFT_FLAGS']
            self.assertEqual(flags[0], '$(inherited)')
            self.assertEqual(flags[1::2], ['-Xcc'] * 19)
            self.assertEqual(flags[2::2], ['-fmodule-map-file=$(PROJECT_DIR)/../distribution/' + path for path in proof['module_maps']])
            self.assertEqual(settings['HEADER_SEARCH_PATHS'], ['$(inherited)'] + ['$(PROJECT_DIR)/../distribution/' + path for path in proof['header_search_paths']])
        self.assertNotIn(str(f.derived), (project / 'project.pbxproj').read_text())

    def test_failed_consumer_outputs_are_retained_only_as_unqualified_bytes(self):
        f = self.fixture()
        f.export()
        with patch.dict(os.environ, f.retention_inputs()):
            result = retain(f.root, f.evidence, f.work)
            self.assertEqual(result['status'], 'UNQUALIFIED_PRODUCER_OUTPUTS_RETAINED')
            value = json.loads((f.work / 'UNQUALIFIED_PRODUCER.json').read_bytes())
            self.assertFalse(value['qualified_distribution'])
            self.assertFalse(value['restore_as_sdk_allowed'])
            self.assertEqual(value['consumer_continuation_admission'], 'NOT_IMPLEMENTED_OR_GRANTED')
            self.assertEqual(value['distribution_files'], __import__('product_inventory').inventory(f.exported))
            self.assertFalse((f.exported / 'QUALIFICATION.json').exists())
            with self.assertRaisesRegex(ValueError, 'replace retained'):
                retain(f.root, f.evidence, f.work)

    def test_retention_refuses_source_drift_foreign_attempt_or_failed_build_command(self):
        for mode in ('source', 'attempt', 'build'):
            with self.subTest(mode=mode):
                f = self.fixture(mode)
                environment = f.retention_inputs()
                if mode == 'source':
                    json_write(f.evidence / 'source-after.json', {**f.source, 'head_sha': 'f' * 40})
                elif mode == 'attempt':
                    environment['GITHUB_RUN_ATTEMPT'] = '2'
                else:
                    json_write(f.evidence / 'framework-build.command.json', {'returncode': 65, 'timed_out': False})
                with patch.dict(os.environ, environment):
                    with self.assertRaises(ValueError):
                        retain(f.root, f.evidence, f.work)
                self.assertFalse((f.work / 'UNQUALIFIED_PRODUCER.json').exists())

    def test_absent_or_unbuilt_work_cannot_create_retained_acceptance(self):
        f = self.fixture()
        self.assertEqual(retain(f.root, f.evidence, f.root / 'build/missing')['status'], 'NO_WRITTEN_PRODUCER_OUTPUTS_TO_RETAIN')
        self.assertEqual(retain(f.root, f.evidence, f.work)['status'], 'NO_ACTUAL_FRAMEWORK_RECEIPT_TO_RETAIN')
        json_write(f.evidence / 'execution.json', {'status': 'FAIL', 'original_framework_build': 'NOT_RUN'})
        self.assertEqual(retain(f.root, f.evidence, f.work)['status'], 'NO_FAILED_CONSUMER_PRODUCER_TO_RETAIN')
        self.assertFalse((f.work / 'UNQUALIFIED_PRODUCER.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
