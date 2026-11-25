import unittest
from pathlib import Path
from release_symbols import parse_export_trie

BINARY = Path('/tmp/Original.framework/Original')
HEADER = str(BINARY) + ' [arm64]:\n    -exports:\n        offset      symbol\n'


class NativeExportParserTests(unittest.TestCase):
    def test_preserves_regular_weak_and_thread_local_definitions(self):
        names, kinds = parse_export_trie(HEADER + '  0x10 _regular\n  0x20 _weak [weak-def]\n  0x30 _tls [per-thread]\n', BINARY)
        self.assertEqual(names, {'_regular', '_weak', '_tls'})
        self.assertEqual(kinds, {'regular':1, 'weak-def':1, 'per-thread':1})

    def test_rejects_truncated_header_and_empty_rows(self):
        for raw in [HEADER, HEADER.replace(' [arm64]', ' [x86_64]') + '  0x10 _a\n',
                    HEADER.replace('offset', 'address') + '  0x10 _a\n']:
            with self.assertRaises(RuntimeError): parse_export_trie(raw, BINARY)

    def test_rejects_unknown_flags_and_reexport_formats(self):
        for line in [' 0x10 _a [unreviewed]', ' [re-export] _a from X', '0x10 _a extra', 'truncated']:
            with self.assertRaises(RuntimeError): parse_export_trie(HEADER + line + '\n', BINARY)

    def test_rejects_duplicate_export_names(self):
        with self.assertRaises(RuntimeError): parse_export_trie(HEADER+' 0x10 _a\n 0x20 _a\n', BINARY)


if __name__ == '__main__':
    unittest.main()
