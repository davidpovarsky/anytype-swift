"""Exercise the unchanged real validators through a real temporary-root alias."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class TemporaryRootAliasControls(unittest.TestCase):
    def run_original_control(self, case):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            actual = root / 'actual'
            actual.mkdir()
            alias = root / 'alias'
            alias.symlink_to(actual, target_is_directory=True)
            self.assertNotEqual(alias, alias.resolve())
            self.assertTrue(alias.samefile(actual))
            # A separate process lets Python select this exact TMPDIR before
            # tempfile caches it. The original control runs its full body.
            result = subprocess.run(
                [sys.executable, '-m', 'unittest', case, '-v'],
                cwd=Path(__file__).resolve().parent,
                env={**os.environ, 'TMPDIR': str(alias), 'PYTHONDONTWRITEBYTECODE': '1'},
                capture_output=True, timeout=30,
            )
            output = result.stderr.decode('utf-8', errors='strict')
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('Ran 1 test in ', output)
            self.assertTrue(output.rstrip().endswith('OK'), output)
            self.assertNotIn('skipped', output)
            self.assertEqual(list(actual.iterdir()), [])

    def test_known_input_mutation_is_really_injected_and_refused_under_directory_alias(self):
        self.run_original_control(
            'test_framework_duplicates.KnownLibDuplicateControls.'
            'test_known_input_changed_during_copy_cannot_publish_success')

    def test_materialized_mutation_is_really_injected_and_refused_under_directory_alias(self):
        self.run_original_control(
            'test_framework_duplicates.KnownLibDuplicateControls.'
            'test_changed_materialized_output_cannot_publish_success')

    def test_original_raw_compiler_proofs_are_retained_under_directory_alias(self):
        self.run_original_control(
            'test_framework_source_retention.OriginalRawCompilerEvidenceControls.'
            'test_original_packager_retains_all_four_exact_raw_proofs_as_text')


if __name__ == '__main__':
    unittest.main()
