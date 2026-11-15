import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import validate_t5_coverage


class T5ValidationReceiptTests(unittest.TestCase):
    def arguments(self, directory):
        return ['--heart-source', str(directory / 'heart'), '--inventory', str(directory / 'missing.json'),
                '--go', 'not-launched', '--tantivy-directory', str(directory / 'tantivy'),
                '--evidence', str(directory / 'evidence'), '--component', 'native-index']

    def invoke(self, directory):
        with contextlib.redirect_stdout(io.StringIO()):
            return validate_t5_coverage.main(self.arguments(directory))

    def test_existing_pass_receipt_is_refused_before_any_preflight_or_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            evidence = directory / 'evidence'
            evidence.mkdir()
            receipt = evidence / 'native-index-result.json'
            original = b'{"status":"PASS","run_id":"old-run"}\n'
            receipt.write_bytes(original)
            with patch.object(validate_t5_coverage, 'execute') as execute:
                self.assertEqual(self.invoke(directory), 1)
                execute.assert_not_called()
            self.assertEqual(receipt.read_bytes(), original)

    def test_existing_log_without_receipt_is_also_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            evidence = directory / 'evidence'
            evidence.mkdir()
            (evidence / 'native-index.log').write_text('old output')
            self.assertEqual(self.invoke(directory), 1)
            self.assertFalse((evidence / 'native-index-result.json').exists())

    def test_new_preflight_failure_leaves_current_failure_with_run_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.assertEqual(self.invoke(directory), 1)
            receipt = json.loads((directory / 'evidence/native-index-result.json').read_text())
            self.assertEqual(receipt['status'], 'FAIL')
            self.assertEqual(receipt['error_type'], 'FileNotFoundError')
            self.assertEqual(receipt['reason'], 'PREFLIGHT_OR_EXECUTION_EXCEPTION')
            self.assertTrue(receipt['run_id'])
            self.assertIn('finished_at', receipt)

    def test_launch_exception_cannot_leave_a_pass_or_unfinalized_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.object(validate_t5_coverage, 'execute', side_effect=OSError('launch failure')):
                self.assertEqual(self.invoke(directory), 1)
            receipt = json.loads((directory / 'evidence/native-index-result.json').read_text())
            self.assertEqual(receipt['status'], 'FAIL')
            self.assertEqual(receipt['error_type'], 'OSError')
            self.assertNotEqual(receipt['reason'], 'ATTEMPT_NOT_COMPLETED')
            self.assertEqual(receipt['client_enablement'], 'DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF')


if __name__ == '__main__':
    unittest.main()
