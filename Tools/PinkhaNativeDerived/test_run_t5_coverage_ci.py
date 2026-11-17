"""CI control checks; these never execute a native fixture."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('t5_ci', Path(__file__).with_name('run_t5_coverage_ci.py'))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class CIReceiptTests(unittest.TestCase):
    def test_missing_run_identity_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'real GitHub'):
                ci.require_identity(Path('.'))

    def test_mismatching_checkout_is_rejected(self):
        with patch.dict(os.environ, dict(GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2', GITHUB_SHA='a' * 40)), \
                patch.object(ci, 'git', return_value='b' * 40):
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                ci.require_identity(Path('.'))

    def test_exact_current_run_identity_is_recorded(self):
        with patch.dict(os.environ, dict(GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2', GITHUB_SHA='a' * 40)), \
                patch.object(ci, 'git', return_value='a' * 40):
            self.assertEqual(ci.require_identity(Path('.')), dict(
                github_run_id='123', github_run_attempt='2', integration_sha='a' * 40))

    def test_interruption_finalizes_current_attempt_as_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / 'new-attempt'
            def interrupted(*args):
                self.assertEqual(json.loads((evidence / 'ci-result.json').read_text())['status'], 'RUNNING')
                raise KeyboardInterrupt('interrupted native proof')
            with patch.object(ci, 'execute', side_effect=interrupted), contextlib.redirect_stdout(io.StringIO()):
                result = ci.main(['--source', '.', '--heart', '.', '--component', 'native-index',
                                  '--evidence', str(evidence)])
            receipt = json.loads((evidence / 'ci-result.json').read_text())
            self.assertEqual(result, 1)
            self.assertEqual(receipt['status'], 'FAIL')
            self.assertEqual(receipt['error_type'], 'KeyboardInterrupt')
            self.assertIn('finished_at', receipt)

    def test_existing_pass_evidence_is_immutable_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory)
            old = evidence / 'ci-result.json'
            old.write_text('{"status":"PASS","github_run_id":"old"}')
            with patch.object(ci, 'execute') as execute:
                with self.assertRaises(FileExistsError):
                    ci.main(['--source', '.', '--heart', '.', '--component', 'native-index',
                             '--evidence', str(evidence)])
                execute.assert_not_called()
            self.assertEqual(json.loads(old.read_text())['github_run_id'], 'old')


if __name__ == '__main__':
    unittest.main()
