"""Reconstructed source controls; no Apple compilation or Native acceptance.

The old observed compiler line is relocated into a temporary checkout and the
proposed target emission arguments are appended explicitly. Graph JSON and the
successful command receipt are test fixtures, never reported as native evidence.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

import collect_compiler_symbolgraphs as collector
from framework_profile import HERE


class CompilerSymbolGraphCollectionControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.evidence = self.root / 'build/evidence'
        self.derived = self.root / 'build/work/producer-derived'
        self.target_build = self.derived / ('Build/Intermediates.noindex/Anytype.build/'
                            'Debug-Anytype-iphonesimulator/AnytypeOriginalEditor.build')
        self.graph_directory = self.target_build / 'DerivedSources/OriginalEditorSymbolGraphs'
        self.graph_directory.mkdir(parents=True)
        self.evidence.mkdir(parents=True)
        self.output = self.evidence / 'actual-public-symbol-graphs'
        original = (HERE / 'fixtures/v9-original-swift-driver.txt').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         '4a109408517a12f6a274d032a90bf5b52db560bab196d14583a4347682dabfd7')
        arguments = shlex.split(original.decode().strip())
        old_root = arguments[arguments.index('-working-directory') + 1]
        old_derived = str(Path(arguments[arguments.index('-clang-scanner-module-cache-path') + 1]).parent)
        self.arguments = [value.replace(old_derived, str(self.derived)).replace(old_root, str(self.root))
                          for value in arguments]
        self.sdk = self.arguments[self.arguments.index('-sdk') + 1]
        self.arguments.extend(['-emit-symbol-graph', '-emit-symbol-graph-dir', str(self.graph_directory),
                               '-symbol-graph-minimum-access-level', 'public', '-include-spi-symbols'])
        self.source = {'head_sha': '1' * 40, 'run_id': '2', 'run_attempt': '1',
                       'scope': 'SYNTHETIC_SOURCE_CONTROL_NO_APPLE_OR_NATIVE_EXECUTION'}
        self.source_path = self.evidence / 'source-before.json'
        self.source_path.write_text(json.dumps(self.source))
        self.observation = patch.object(collector, 'source_observation', return_value=self.source)
        self.observation.start()
        self.addCleanup(self.observation.stop)
        self.started = datetime.now(timezone.utc) - timedelta(seconds=5)
        self.finished = datetime.now(timezone.utc) + timedelta(seconds=5)
        self.write_graph('AnytypeOriginalEditor.symbols.json', 'AnytypeOriginalEditor', [
            {'identifier': {'precise': 'public-fixture'}, 'accessLevel': 'public'},
            {'identifier': {'precise': 'spi-fixture'}, 'accessLevel': 'public', 'spi': True}])
        self.write_graph('AnytypeOriginalEditor@Foundation.symbols.json', 'Foundation', [
            {'identifier': {'precise': 'extension-fixture'}, 'accessLevel': 'public'}])
        self.write_build()

    def write_graph(self, name, module, symbols):
        path = self.graph_directory / name
        path.write_text(json.dumps({'module': {'name': module}, 'symbols': symbols,
                                    'relationships': [{'kind': 'memberOf', 'source': 'a', 'target': 'b'}]},
                                   indent=3) + '\n')
        return path

    def write_build(self, **overrides):
        self.log = self.evidence / 'framework-build.stdout.log'
        self.log.write_text(shlex.join(self.arguments) + '\n')
        self.receipt = {'command': ['xcodebuild', 'build', '-project', str(self.root / 'Anytype.xcodeproj'),
                        '-scheme', 'AnytypeOriginalEditor', '-configuration', 'Debug-Anytype',
                        '-derivedDataPath', str(self.derived), '-resultBundlePath',
                        str(self.evidence / 'framework-build.xcresult')], 'cwd': str(self.root),
                        'started_at': self.started.isoformat(), 'finished_at': self.finished.isoformat(),
                        'returncode': 0, 'timed_out': False, 'timeout_seconds': 6000,
                        'stdout_sha256': collector.sha256(self.log),
                        'scope': 'RECONSTRUCTED_SUCCESSFUL_RECEIPT_NO_APPLE_EXECUTION'}
        self.receipt.update(overrides)
        self.receipt_path = self.evidence / 'framework-build.command.json'
        self.receipt_path.write_text(json.dumps(self.receipt))

    def collect(self):
        return collector.collect(self.root, self.derived, self.evidence, self.sdk, self.output)

    def test_full_public_spi_and_extension_bytes_are_retained_without_filtering(self):
        expected = {path.name: path.read_bytes() for path in self.graph_directory.iterdir()}
        receipt = self.collect()
        self.assertEqual({path.name: path.read_bytes() for path in self.output.iterdir()}, expected)
        self.assertEqual(receipt['graphs'][0]['symbols'], 2)
        self.assertEqual(len(receipt['graphs']), 2)
        self.assertTrue(receipt['all_emitted_graphs_copied_without_filtering'])
        self.assertTrue(receipt['include_spi_symbols'])
        self.assertEqual(receipt['standalone_extractor_invocations'], 0)
        self.assertEqual(receipt['native_editor_ui_tests'], 0)
        self.assertEqual(receipt['framework_build_stdout']['sha256'], collector.sha256(self.log))
        self.assertEqual(json.loads((self.evidence / 'compiler-symbolgraph-collection.json').read_text()), receipt)

    def test_separate_collection_keeps_original_build_records_byte_identical(self):
        original = {p.name: p.read_bytes() for p in self.evidence.iterdir() if p.is_file()}
        continuation = self.root / "build/continuation"
        continuation.mkdir()
        receipt = collector.collect(self.root, self.derived, continuation, self.sdk,
                                    continuation / "actual-public-symbol-graphs",
                                    build_evidence=self.evidence)
        self.assertEqual(receipt["original_build_evidence_directory"], str(self.evidence))
        self.assertEqual({p.name: p.read_bytes() for p in self.evidence.iterdir() if p.is_file()},
                         original)
        self.assertEqual(receipt["framework_build_command"]["sha256"],
                         collector.sha256(self.receipt_path))

    def test_continuation_cannot_relabel_original_result_bundle_path(self):
        continuation = self.root / "build/continuation"
        continuation.mkdir()
        self.receipt["command"][-1] = str(continuation / "framework-build.xcresult")
        self.receipt_path.write_text(json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError, "build identity"):
            collector.collect(self.root, self.derived, continuation, self.sdk,
                              continuation / "actual-public-symbol-graphs",
                              build_evidence=self.evidence)

    def test_source_change_rejects_collection(self):
        self.source_path.write_text(json.dumps({**self.source, 'head_sha': '3' * 40}))
        with self.assertRaisesRegex(ValueError, 'Source differs'):
            self.collect()
        self.assertFalse(self.output.exists())

    def test_changed_log_is_not_build_authority(self):
        self.log.write_text(self.log.read_text() + 'UNRECORDED CHANGE\n')
        with self.assertRaisesRegex(ValueError, 'successful original framework build'):
            self.collect()

    def test_failed_timed_out_foreign_or_changed_timeout_receipt_is_rejected(self):
        for changes in [{'returncode': 1}, {'timed_out': True}, {'cwd': '/foreign'}, {'timeout_seconds': 120}]:
            with self.subTest(changes=changes):
                self.write_build(**changes)
                with self.assertRaisesRegex(ValueError, 'successful original framework build'):
                    self.collect()

    def test_wrong_build_scheme_configuration_or_derived_is_rejected(self):
        for option in ['-scheme', '-configuration', '-derivedDataPath', '-project', '-resultBundlePath']:
            with self.subTest(option=option):
                self.write_build()
                self.receipt['command'][self.receipt['command'].index(option) + 1] = '/foreign'
                self.receipt_path.write_text(json.dumps(self.receipt))
                with self.assertRaisesRegex(ValueError, 'build identity'):
                    self.collect()

    def test_duplicate_target_compiler_is_rejected(self):
        self.log.write_text(self.log.read_text() * 2)
        self.receipt['stdout_sha256'] = collector.sha256(self.log)
        self.receipt_path.write_text(json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError, 'ambiguous original target compiler'):
            self.collect()

    def test_wrong_actual_module_target_sdk_swift_or_working_directory_is_rejected(self):
        original = list(self.arguments)
        for option in ['-module-name', '-target', '-sdk', '-swift-version', '-working-directory']:
            with self.subTest(option=option):
                self.arguments = list(original)
                self.arguments[self.arguments.index(option) + 1] = '/foreign'
                self.write_build()
                with self.assertRaises(ValueError):
                    self.collect()

    def test_missing_emit_or_spi_flag_is_rejected(self):
        original = list(self.arguments)
        for option in ['-emit-symbol-graph', '-include-spi-symbols']:
            with self.subTest(option=option):
                self.arguments = [value for value in original if value != option]
                self.write_build()
                with self.assertRaisesRegex(ValueError, 'Full public/SPI'):
                    self.collect()

    def test_changed_access_level_or_filter_flags_are_rejected(self):
        original = list(self.arguments)
        for level in ['private', 'internal', 'open']:
            with self.subTest(level=level):
                self.arguments = list(original)
                self.arguments[self.arguments.index('-symbol-graph-minimum-access-level') + 1] = level
                self.write_build()
                with self.assertRaisesRegex(ValueError, 'Full public/SPI'):
                    self.collect()
        for option in ['-symbol-graph-skip-synthesized-members', '-skip-synthesized-members',
                       '-symbol-graph-skip-inherited-docs', '-include-spi-symbols=false']:
            with self.subTest(option=option):
                self.arguments = [*original, option]
                self.write_build()
                with self.assertRaisesRegex(ValueError, 'Full public/SPI'):
                    self.collect()

    def test_duplicate_emission_or_path_flags_are_rejected(self):
        original = list(self.arguments)
        for extra in [['-include-spi-symbols'], ['-emit-symbol-graph'],
                      ['-emit-symbol-graph-dir', str(self.graph_directory)],
                      ['-symbol-graph-minimum-access-level', 'public']]:
            with self.subTest(extra=extra):
                self.arguments = [*original, *extra]
                self.write_build()
                with self.assertRaises(ValueError):
                    self.collect()

    def test_original_debug_and_heart_definitions_are_required(self):
        original = list(self.arguments)
        for definition in ['DEBUG', 'PINKHA_NATIVE_DERIVED']:
            with self.subTest(definition=definition):
                self.arguments = [value.replace(definition, 'UNQUALIFIED') for value in original]
                self.write_build()
                with self.assertRaisesRegex(ValueError, 'definitions'):
                    self.collect()

    def test_foreign_target_derivedsources_or_module_output_is_rejected(self):
        original = list(self.arguments)
        for option in ['-emit-symbol-graph-dir', '-emit-module-path']:
            with self.subTest(option=option):
                self.arguments = list(original)
                self.arguments[self.arguments.index(option) + 1] = str(self.derived / 'foreign')
                self.write_build()
                with self.assertRaisesRegex(ValueError, 'actual owned framework target'):
                    self.collect()

    def test_stale_graph_is_rejected(self):
        path = self.graph_directory / 'AnytypeOriginalEditor.symbols.json'
        stale = int((self.started - timedelta(seconds=60)).timestamp() * 1_000_000_000)
        os.utime(path, ns=(stale, stale))
        with self.assertRaisesRegex(ValueError, 'within this original build interval'):
            self.collect()

    def test_missing_empty_or_wrong_main_graph_is_rejected(self):
        path = self.graph_directory / 'AnytypeOriginalEditor.symbols.json'
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'full target symbol graph'):
            self.collect()
        self.write_graph(path.name, 'AnytypeOriginalEditor', [])
        with self.assertRaisesRegex(ValueError, 'empty or names another'):
            self.collect()

    def test_unexpected_graph_directory_member_is_rejected(self):
        (self.graph_directory / 'partial.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'graph-only directory'):
            self.collect()

    def test_aliased_graph_is_rejected(self):
        path = self.graph_directory / 'AnytypeOriginalEditor.symbols.json'
        outside = self.root / 'foreign.symbols.json'
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Aliased'):
            self.collect()

    def test_preexisting_collection_is_rejected_without_overwrite(self):
        self.output.mkdir()
        marker = self.output / 'preserved'
        marker.write_text('existing')
        with self.assertRaisesRegex(ValueError, 'Refusing stale'):
            self.collect()
        self.assertEqual(marker.read_text(), 'existing')

    def test_source_retirement_during_collection_prevents_success_receipt(self):
        with patch.object(collector, 'source_observation', side_effect=[self.source, {**self.source, 'changed': True}]):
            with self.assertRaisesRegex(ValueError, 'changed during collection'):
                self.collect()
        self.assertFalse((self.evidence / 'compiler-symbolgraph-collection.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
