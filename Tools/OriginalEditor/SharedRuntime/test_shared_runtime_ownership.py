"""Explicit synthetic symbol decisions; these tests do not execute Apple tools."""
import unittest

from SharedRuntime.verify_framework_ownership import (
    EDITOR, RUNTIME, FIREBASE_CLASSES, HOST_PRODUCTS, verify_definitions,
)


class SharedDefinitionControls(unittest.TestCase):
    def fixture(self):
        return {
            RUNTIME: {'_OBJC_CLASS_$_' + c for c in FIREBASE_CLASSES},
            EDITOR: {'_OBJC_CLASS_$_MTMathUILabel', '_cmark_parse_document',
                     *{'_$s' + str(len(m)) + m + 'ExplicitSyntheticFunction' for m in HOST_PRODUCTS}},
            'external-consumer-0': {'_main'},
        }

    def test_complete_unique_synthetic_definitions_have_no_native_credit(self):
        result = verify_definitions(self.fixture())
        self.assertEqual(len(result['host_module_definition_counts']), 12)
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
