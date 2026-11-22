"""New retention-admission boundaries; no original test bodies execute here."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / 'candidate/Tools/OriginalEditor'))
sys.path.insert(1, str(PACKET / 'preimage/Tools/OriginalEditor'))
import admit_retained_source_controls as admission


class RetainedAdmissionControls(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((PACKET / 'admission/INPUTS.json').read_bytes())
        self.old = json.loads((PACKET / 'admission/original-source-before.json').read_bytes())
        self.controls = json.loads((PACKET / 'admission/original-source-controls-result.json').read_bytes())
        self.catalog = self.controls['expected_ids']
        self.current = copy.deepcopy(self.old)
        self.current.update(head_sha='b' * 40, run_id='91234567', run_attempt='1')
        for path, item in self.plan['reviewed_source_input_changes'].items():
            self.current['source_inputs'][path] = item['after']

    def validate(self):
        return admission.validate_retained(self.plan, self.controls, self.old, self.current, self.catalog)

    def test_authentic_245_receipt_admits_exact_changed_ledger_without_execution(self):
        result = self.validate()
        self.assertEqual(result['original_source_sha'], 'edce5b975b173059522f90adb71271fb95adf963')
        self.assertEqual(result['original_run_id'], '45041382512')
        self.assertEqual(result['original_count'], 245)
        self.assertTrue(result['historical_only'])
        self.assertFalse(result['whole_suite_replayed'])
        self.assertEqual(len(result['current_affected_ids']), 8)

    def test_duplicate_historical_success_cannot_replace_an_original_identity(self):
        self.controls['passed_ids'][0] = self.controls['passed_ids'][1]
        with self.assertRaisesRegex(ValueError, 'identity set'):
            self.validate()

    def test_historical_skip_or_failure_is_not_retained_as_pass(self):
        for key in ['errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes']:
            self.controls[key] = [{'EXPLICIT_FAILURE_FIXTURE': True}]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'failure/skip'):
                self.validate()
            self.controls[key] = []

    def test_wrong_historical_producer_is_refused(self):
        self.old['head_sha'] = self.current['head_sha']
        with self.assertRaisesRegex(ValueError, 'different original producer'):
            self.validate()

    def test_unreviewed_original_source_input_change_is_refused(self):
        untouched = next(path for path in self.old['source_inputs'] if path not in self.plan['reviewed_source_input_changes'])
        self.current['source_inputs'][untouched]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'exact reviewed delta'):
            self.validate()

    def test_extra_current_helper_is_refused(self):
        self.current['source_inputs']['Tools/OriginalEditor/UNREVIEWED.py'] = {
            'bytes': 1, 'sha256': '0' * 64, 'git_blob': '0' * 40}
        with self.assertRaisesRegex(ValueError, 'exact reviewed delta'):
            self.validate()

    def test_original_product_tree_change_is_refused(self):
        self.current['original_trees']['Anytype/Sources'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'product/source membership'):
            self.validate()

    def test_wrong_reviewed_source_preimage_is_refused(self):
        path = next(path for path, item in self.plan['reviewed_source_input_changes'].items() if item['before'] is not None)
        self.plan['reviewed_source_input_changes'][path]['before']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'preimage differs'):
            self.validate()

    def test_wrong_new_helper_afterimage_is_refused(self):
        path = 'Tools/OriginalEditor/admit_retained_source_controls.py'
        self.current['source_inputs'][path] = {**self.current['source_inputs'][path], 'sha256': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'exact reviewed delta'):
            self.validate()

    def test_affected_selection_cannot_expand_to_the_whole_old_suite(self):
        self.plan['current_affected_ids'] = self.catalog
        with self.assertRaisesRegex(ValueError, 'affected selection'):
            self.validate()

    def test_real_committed_input_read_rejects_dirty_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            relative = admission.PACKET + '/admission/fixture.json'
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text('{"EXPLICIT_GIT_INPUT_FIXTURE":true}\n')
            subprocess.run(['git', '-C', str(root), 'add', relative], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                            'commit', '-qm', 'explicit isolated input fixture'], check=True, capture_output=True)
            observed, identity = admission.read_committed(root, relative)
            self.assertTrue(observed['EXPLICIT_GIT_INPUT_FIXTURE'])
            self.assertEqual(identity['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError, 'reviewed source packet'):
                admission.read_committed(root, relative, {**identity, 'sha256': '0' * 64})
            path.write_text('{"EXPLICIT_GIT_INPUT_FIXTURE":false}\n')
            with self.assertRaisesRegex(ValueError, 'current Git input'):
                admission.read_committed(root, relative)


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print('START ' + test.id(), flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        print('PASS ' + test.id(), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2, testRunner=unittest.TextTestRunner(resultclass=RecordedResult, verbosity=2))
