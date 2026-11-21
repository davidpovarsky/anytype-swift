"""Check original build-context admission using the observed v9 compiler line.

These are Python controls with an explicitly reconstructed command receipt.
They do not execute an Apple compiler, extractor, consumer or editor.
"""
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import unittest

import run_framework_acceptance as driver
from framework_profile import HERE


class ActualCompilerImportContextControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.evidence = Path(self.temporary.name)
        raw = (HERE / 'fixtures/v9-original-swift-driver.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '4a109408517a12f6a274d032a90bf5b52db560bab196d14583a4347682dabfd7')
        self.arguments = shlex.split(raw.decode().strip())
        self.root = Path(self.arguments[self.arguments.index('-working-directory') + 1])
        self.cache = Path(self.arguments[self.arguments.index('-clang-scanner-module-cache-path') + 1])
        self.derived = self.cache.parent
        self.products = self.derived / 'Build/Products/Debug-Anytype-iphonesimulator'
        self.sdk = self.arguments[self.arguments.index('-sdk') + 1]
        self.log = self.evidence / 'framework-build.stdout.log'
        self.log.write_bytes(raw)
        self.write_receipt()

    def write_receipt(self, **overrides):
        value = {'returncode': 0, 'timed_out': False, 'cwd': str(self.root),
                 'stdout_sha256': hashlib.sha256(self.log.read_bytes()).hexdigest(),
                 'scope': 'RECONSTRUCTED_RECEIPT_AROUND_ONE_OBSERVED_COMPILER_LINE_NO_APPLE_EXECUTION'}
        value.update(overrides)
        driver.write(self.evidence / 'framework-build.command.json', value)

    def context(self):
        return driver.symbolgraph_import_context(
            self.root, self.derived, self.products, self.sdk, self.evidence)

    def test_observed_original_context_keeps_all_clang_imports_and_implicit_cache(self):
        actual = self.context()
        xcc = [self.arguments[i + 1] for i, value in enumerate(self.arguments) if value == '-Xcc']
        maps = [value for value in xcc if value.startswith('-fmodule-map-file=')]
        self.assertEqual(len(maps), 15)
        self.assertEqual([actual[i + 1] for i, value in enumerate(actual) if value == '-Xcc'], xcc)
        self.assertEqual(actual[actual.index('-module-cache-path') + 1], str(self.cache))
        self.assertNotIn('SwiftExplicitPrecompiledModules', actual[actual.index('-module-cache-path') + 1])
        self.assertEqual(actual[actual.index('-swift-version') + 1], '5')
        self.assertIn('-v', actual)
        self.assertFalse(any('skip' in value or 'reexported' in value for value in actual))
        for path in [str(self.root), str(self.root / 'Dependencies/Middleware')]:
            self.assertIn(path, actual)
        proof = json.loads((self.evidence / 'symbolgraph-import-context.json').read_text())
        self.assertEqual(proof['source_compiler_line_sha256'],
                         '820cce823b850e24d2a1b5cbdc7325285c3f06ee4df59c60dbeffa5a36b9038f')
        self.assertFalse(proof['public_symbol_filtering_added'])

    def test_changed_log_is_rejected_before_any_extraction_authority(self):
        self.log.write_bytes(self.log.read_bytes() + b'UNRECORDED_CHANGE\n')
        with self.assertRaisesRegex(ValueError, 'successful original build'):
            self.context()

    def test_ambiguous_original_target_command_is_rejected(self):
        self.log.write_bytes(self.log.read_bytes() * 2)
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            self.context()

    def test_wrong_target_sdk_language_or_cache_is_rejected(self):
        original = self.log.read_text()
        replacements = [
            ('arm64-apple-ios27.0-simulator', 'x86_64-apple-ios27.0-simulator'),
            ('-sdk ' + self.sdk, '-sdk /UNRELATED_SDK'),
            ('-swift-version 5', '-swift-version 6'),
            ('-clang-scanner-module-cache-path ' + str(self.cache),
             '-clang-scanner-module-cache-path /UNRELATED_CACHE'),
        ]
        for old, new in replacements:
            with self.subTest(changed=old):
                self.assertIn(old, original)
                self.log.write_text(original.replace(old, new))
                self.write_receipt()
                with self.assertRaises(ValueError):
                    self.context()

    def test_failed_timed_out_or_foreign_build_is_not_import_authority(self):
        for change in [{'returncode': 1}, {'timed_out': True}, {'cwd': '/UNRELATED_CHECKOUT'}]:
            with self.subTest(change=change):
                self.write_receipt(**change)
                with self.assertRaisesRegex(ValueError, 'successful original build'):
                    self.context()


if __name__ == '__main__':
    unittest.main(verbosity=2)
