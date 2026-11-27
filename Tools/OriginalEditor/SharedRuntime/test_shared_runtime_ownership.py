"""Explicit synthetic symbol decisions; these tests do not execute Apple tools."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from SharedRuntime.verify_framework_ownership import (
    EDITOR, RUNTIME, FIREBASE_CLASSES, HOST_PRODUCTS, verify_definitions, dependency_source_inventory,
    DEPENDENCY_MODULE_OWNERS,
)


class SharedDefinitionControls(unittest.TestCase):
    def fixture(self):
        return {
            RUNTIME: {'_OBJC_CLASS_$_' + c for c in FIREBASE_CLASSES},
            EDITOR: {'_OBJC_CLASS_$_MTMathUILabel', '_cmark_parse_document',
                     *{'_$s' + str(len(m)) + m + 'ExplicitSyntheticFunction' for m in HOST_PRODUCTS}},
            'Logger': {'_$s7LoggingExplicitSyntheticFunction'},
            'external-consumer-0': {'_main'},
        }

    def test_complete_unique_synthetic_definitions_have_no_native_credit(self):
        result = verify_definitions(self.fixture())
        self.assertEqual(len(result['host_module_definition_counts']), 14)
        self.assertEqual(result['required_module_owners']['AI_Hanlin'], EDITOR)
        self.assertEqual(DEPENDENCY_MODULE_OWNERS, {'Logging': 'Logger'})
        self.assertNotIn('status', result)
        self.assertNotIn('native', result)

    def test_original_editor_cannot_embed_a_second_firebase_class(self):
        symbols = self.fixture()
        symbols[EDITOR].add('_OBJC_CLASS_$_FIRApp')
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_external_consumer_cannot_embed_a_second_promise_class(self):
        symbols = self.fixture()
        symbols['external-consumer-0'].add('_OBJC_CLASS_$_FBLPromise')
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_runtime_cannot_omit_an_original_messaging_implementation(self):
        symbols = self.fixture()
        symbols[RUNTIME].remove('_OBJC_CLASS_$_FIRMessaging')
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_swift_module_declarations_without_defined_functions_are_insufficient(self):
        symbols = self.fixture()
        symbols[EDITOR] = {s for s in symbols[EDITOR] if 'HanlinRichUI' not in s}
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_cmark_implementation_cannot_move_to_an_unreviewed_image(self):
        symbols = self.fixture()
        symbols[EDITOR].remove('_cmark_parse_document')
        symbols[RUNTIME].add('_cmark_parse_document')
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_duplicate_shared_hanlin_symbols_are_rejected(self):
        symbols = self.fixture()
        symbol = next(s for s in symbols[EDITOR] if 'HanlinHostContracts' in s)
        symbols['external-consumer-0'].add(symbol)
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_editor_cannot_link_a_second_original_logging_implementation(self):
        symbols = self.fixture()
        symbols[EDITOR].update(symbols['Logger'])
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_logging_cannot_move_out_of_its_original_dynamic_owner(self):
        symbols = self.fixture()
        symbols[EDITOR].update(symbols.pop('Logger'))
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_original_logging_implementation_cannot_be_missing(self):
        symbols = self.fixture()
        symbols.pop('Logger')
        with self.assertRaises(ValueError):
            verify_definitions(symbols)

    def test_external_consumer_cannot_link_the_original_logging_again(self):
        symbols = self.fixture()
        symbols['external-consumer-0'].update(symbols['Logger'])
        with self.assertRaises(ValueError):
            verify_definitions(symbols)


class RetainedDependencyControls(unittest.TestCase):
    """Real temporary Git objects reproduce the quarantine failure; no Apple credit."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.old = self.root / 'producer-derived'
        self.kept = self.root / 'producer-derived-preserved'
        self.original_checkouts = self.old / 'SourcePackages/checkouts'
        self.checkouts = self.kept / 'SourcePackages/checkouts'
        self.seed = self.root / 'seed'
        self.seed.mkdir()
        self.git('init', str(self.seed))
        (self.seed / 'GoogleDataTransport').mkdir()
        (self.seed / 'GoogleDataTransport/source.c').write_text('int observed_original = 1;\n')
        self.git('-C', str(self.seed), 'add', '.')
        self.git('-C', str(self.seed), '-c', 'user.name=Explicit control', '-c',
                 'user.email=control@example.invalid', 'commit', '-m', 'Original fixture')
        revision = self.git('-C', str(self.seed), 'rev-parse', 'HEAD').strip()
        repository = self.old / 'SourcePackages/repositories/GoogleDataTransport-control'
        repository.parent.mkdir(parents=True)
        self.git('clone', '--bare', str(self.seed), str(repository))
        self.original_checkouts.mkdir()
        self.git('clone', '--shared', str(repository), str(self.original_checkouts / 'GoogleDataTransport'))
        self.contract = {'dependencies': {'googledatatransport': {'revision': revision}}}
        self.original = dependency_source_inventory(self.original_checkouts, self.contract)
        self.old.rename(self.kept)
        self.directory = self.checkouts / 'GoogleDataTransport'
        self.alternate = self.directory / '.git/objects/info/alternates'
        self.alternate_bytes = self.alternate.read_bytes()
        self.objects = self.kept / 'SourcePackages/repositories/GoogleDataTransport-control/objects'

    def git(self, *arguments):
        environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.check_output(['git', *arguments], text=True, stderr=subprocess.DEVNULL,
                                       env=environment)

    def observe(self):
        return dependency_source_inventory(self.checkouts, self.contract,
                                           original_checkouts=self.original_checkouts)

    def test_real_quarantine_resolves_exact_objects_without_restoring_resources_or_metadata(self):
        with self.assertRaises(subprocess.CalledProcessError):
            dependency_source_inventory(self.checkouts, self.contract)
        observed = self.observe()['googledatatransport']
        proof = observed.pop('git_object_resolution')
        self.assertEqual(observed, self.original['googledatatransport'])
        self.assertFalse(self.old.exists())
        self.assertEqual(self.alternate.read_bytes(), self.alternate_bytes)
        self.assertEqual(proof['retained_objects'], str(self.objects))
        self.assertFalse(proof['git_metadata_modified'])

    def test_original_blob_comparison_still_refuses_modified_source(self):
        (self.directory / 'GoogleDataTransport/source.c').write_text('int modified = 2;\n')
        with self.assertRaisesRegex(ValueError, 'Original shared source bytes differ'):
            self.observe()

    def test_original_dependency_revision_still_must_match(self):
        self.contract['dependencies']['googledatatransport']['revision'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'Incomplete shared dependency source closure'):
            self.observe()

    def test_recreated_original_resource_path_is_refused(self):
        self.old.mkdir()
        with self.assertRaisesRegex(ValueError, 'Producer resource fallback was recreated'):
            self.observe()

    def test_unrelated_alternate_root_is_refused(self):
        self.alternate.write_text(str(self.seed / '.git/objects') + '\n')
        with self.assertRaisesRegex(ValueError, 'does not belong to the original producer'):
            self.observe()

    def test_aliased_or_transitively_redirected_object_root_is_refused(self):
        (self.objects / 'info/alternates').write_text(str(self.seed / '.git/objects') + '\n')
        with self.assertRaisesRegex(ValueError, 'transitively redirected'):
            self.observe()
        (self.objects / 'info/alternates').unlink()
        saved = self.objects.with_name('saved-objects')
        self.objects.rename(saved)
        self.objects.symlink_to(saved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'aliased'):
            self.observe()
