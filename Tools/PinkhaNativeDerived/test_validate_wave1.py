"""Adversarial runtime-copy and receipt checks; no Xcode or native test claims."""
import json
from pathlib import Path
import tempfile
import unittest

from validate_wave1 import require_run_identity, verify_runtime_copies, with_receipt


class Wave1OracleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='wave1-oracle-')
        self.root = Path(self.temporary.name)
        self.bundle = self.root/'Anytype.app'
        self.evidence = self.root/'evidence'
        self.evidence.mkdir()

    def tearDown(self):
        self.assertEqual(self.root.resolve().parent, Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith('wave1-oracle-'))
        self.temporary.cleanup()

    def runtime(self, relative, marker=b'exact-marker'):
        path = self.bundle/relative/'ProtobufMessages.framework/ProtobufMessages'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'MachO fixture\0'+marker)
        return path

    def test_app_and_embedded_xctest_copies_are_both_validated(self):
        app = self.runtime('Frameworks')
        self.runtime('PlugIns/AnytypeTests.xctest/Frameworks')
        root, copies = verify_runtime_copies(self.bundle, b'exact-marker', self.evidence)
        self.assertEqual(root, app)
        self.assertEqual(len(copies), 2)
        self.assertTrue(all(value['marker_present'] for value in copies.values()))

    def test_stale_test_copy_rejects_even_when_app_marker_is_valid(self):
        self.runtime('Frameworks')
        self.runtime('PlugIns/AnytypeTests.xctest/Frameworks', b'old-marker')
        with self.assertRaises(RuntimeError):
            verify_runtime_copies(self.bundle, b'exact-marker', self.evidence)
        record = json.loads((self.evidence/'runtime-copies.json').read_text())
        self.assertFalse(all(value['marker_present'] for value in record['copies'].values()))

    def test_test_copy_cannot_substitute_for_missing_app_carrier(self):
        self.runtime('PlugIns/AnytypeTests.xctest/Frameworks')
        with self.assertRaises(RuntimeError):
            verify_runtime_copies(self.bundle, b'exact-marker', self.evidence)

    def test_app_copy_cannot_substitute_for_missing_test_host_carrier(self):
        self.runtime('Frameworks')
        with self.assertRaises(RuntimeError):
            verify_runtime_copies(self.bundle, b'exact-marker', self.evidence)

    def test_actual_run_identity_is_required_and_must_match_head(self):
        sha = 'a'*40
        for run_id, expected in [(None, sha), ('', sha), ('bad', sha), ('123', None), ('123', ''), ('123', 'b'*40)]:
            with self.subTest(run_id=run_id, expected=expected), self.assertRaises(RuntimeError):
                require_run_identity(sha, run_id, expected)

    def test_matching_actual_run_identity_is_accepted(self):
        require_run_identity('a'*40, '123', 'a'*40)

    def test_preflight_exception_overwrites_old_pass_with_current_attempt_failure(self):
        path = self.evidence/'wave1-native-receipt.json'
        path.write_text(json.dumps(dict(status='PASS', run_id='old', passed=1)))
        def fail():
            self.assertEqual(json.loads(path.read_text())['status'], 'RUNNING')
            raise RuntimeError('setup failed')
        with self.assertRaises(RuntimeError):
            with_receipt(self.evidence, dict(run_id='current', phase='PREFLIGHT'), fail)
        result = json.loads(path.read_text())
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['run_id'], 'current')
        self.assertNotIn('passed', result)


if __name__ == '__main__':
    unittest.main()
