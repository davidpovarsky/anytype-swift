#!/usr/bin/env python3
"""New continuation boundary controls; no old suite or Apple runtime is executed.

Historical receipts are read as immutable inputs. ZIP restoration fixtures use
small synthetic files and stub only the already qualified Clang parser at its
call boundary; the actual continuation still invokes that unmodified parser.
"""
import argparse
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import run_runtime_continuation as subject

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / subject.EVIDENCE_PREFIX
HISTORICAL_SHA = '3e60e0c4532013cd0557763495e63d35d014fe218d5740f2ef6f31dc537941d9'


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def commitment(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class ContinuationBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix='otzaria-continuation-fixtures-')
        cls.base = Path(cls.storage.name)
        cls.historical = cls.base / 'historical'
        cls.historical.mkdir()
        archive = PACKET / 'historical/compact-terminal-evidence.zip'
        assert subject.digest(archive) == HISTORICAL_SHA
        with zipfile.ZipFile(archive) as zipped:
            members = subject.zip_members(zipped)
            for name, entry in members.items():
                output = cls.historical / name
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(zipped.read(entry))
        cls.producer = json.loads((ROOT / 'Tools/OriginalEditor/runtime_continuation_inputs.json').read_bytes())['framework_producer']
        cls.original_run = json.loads((cls.historical / 'RUN_TERMINAL_OR_LAST.json').read_bytes())
        jobs = json.loads((cls.historical / 'JOBS.json').read_bytes())['jobs']
        cls.job = next(j for j in jobs if j['id'] == cls.producer['job_id'])
        cls.artifacts = json.loads((cls.historical / 'ARTIFACTS.json').read_bytes())['artifacts']
        cls.exported = json.loads((cls.historical / 'framework-distribution.json').read_bytes())
        cls.supplements = {}
        for item in cls.producer['archive_omissions']:
            label = 'app' if item['repository'] == subject.REPOSITORY else 'hanlin'
            cls.supplements[item['distribution_path']] = (PACKET / 'omissions' / (label + '-attributes.txt')).read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.directory = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def metadata(self, run=None, job=None, artifact=None):
        item = self.producer['framework_artifact']
        actual = next(a for a in self.artifacts if a['id'] == item['id'])
        subject.verify_metadata(self.producer, run or self.original_run, job or self.job, artifact or actual, item)

    def test_exact_historical_phase_and_both_artifacts_are_admitted(self):
        phase = subject.verify_retained_phase(self.producer, self.historical)
        self.assertEqual(phase['verified_runtime_observations'], [])
        for key in ['framework_artifact', 'evidence_artifact']:
            item = self.producer[key]
            actual = next(a for a in self.artifacts if a['id'] == item['id'])
            subject.verify_metadata(self.producer, self.original_run, self.job, actual, item)

    def test_wrong_original_head_is_rejected(self):
        run = copy.deepcopy(self.original_run)
        run['head_sha'] = 'a' * 40
        with self.assertRaisesRegex(RuntimeError, 'Original producer run'):
            self.metadata(run=run)

    def test_wrong_original_attempt_is_rejected(self):
        run = copy.deepcopy(self.original_run)
        run['run_attempt'] += 1
        with self.assertRaisesRegex(RuntimeError, 'Original producer run'):
            self.metadata(run=run)

    def test_wrong_repository_is_rejected(self):
        run = copy.deepcopy(self.original_run)
        run['head_repository']['id'] += 1
        with self.assertRaisesRegex(RuntimeError, 'repository'):
            self.metadata(run=run)

    def test_aggregate_success_cannot_replace_original_install_failure(self):
        job = copy.deepcopy(self.job)
        job['conclusion'] = 'success'
        with self.assertRaisesRegex(RuntimeError, 'Original failed job'):
            self.metadata(job=job)

    def test_expired_original_artifact_is_rejected(self):
        artifact = copy.deepcopy(next(a for a in self.artifacts if a['id'] == self.producer['framework_artifact']['id']))
        artifact['expired'] = True
        with self.assertRaisesRegex(RuntimeError, 'artifact identity'):
            self.metadata(artifact=artifact)

    def test_artifact_outside_its_upload_window_is_rejected(self):
        artifact = copy.deepcopy(next(a for a in self.artifacts if a['id'] == self.producer['framework_artifact']['id']))
        artifact['created_at'] = '2026-11-21T00:00:00Z'
        with self.assertRaisesRegex(RuntimeError, 'exact successful upload'):
            self.metadata(artifact=artifact)

    def changed_receipt(self, name, mutate):
        original = self.directory / 'original'
        shutil.copytree(self.historical, original)
        value = json.loads((original / name).read_bytes())
        mutate(value)
        (original / name).write_bytes(encoded(value))
        producer = copy.deepcopy(self.producer)
        producer['retained_input_sha256'][name] = subject.digest(original / name)
        return producer, original

    def test_other_failure_phase_is_not_admitted(self):
        producer, original = self.changed_receipt('execution.json', lambda v: v.update(phase='FRAMEWORK_BUILD'))
        with self.assertRaisesRegex(RuntimeError, 'install boundary'):
            subject.verify_retained_phase(producer, original)

    def test_missing_source_control_identity_is_not_admitted(self):
        producer, original = self.changed_receipt('source-controls-result.json', lambda v: v['passed_ids'].pop())
        with self.assertRaisesRegex(RuntimeError, 'identity set'):
            subject.verify_retained_phase(producer, original)

    def test_original_toolchain_must_match_all_three_values(self):
        subject.validate_toolchain(self.producer['toolchain'], self.producer['toolchain'])
        changed = dict(self.producer['toolchain'], sdk_version='27.2')
        with self.assertRaisesRegex(RuntimeError, 'toolchain'):
            subject.validate_toolchain(changed, self.producer['toolchain'])

    def source_response(self, item):
        return {'type': 'file', 'path': item['source_path'], 'sha': item['git_blob'], 'encoding': 'base64',
                'content': base64.b64encode(self.supplements[item['distribution_path']]).decode()}

    def test_both_actual_dotfiles_match_source_git_and_original_manifest(self):
        for item in self.producer['archive_omissions']:
            raw = subject.validate_original_dotfile(item, self.source_response(item), self.exported, self.historical)
            self.assertEqual(raw, self.supplements[item['distribution_path']])

    def test_dotfile_wrong_git_blob_is_rejected(self):
        item = self.producer['archive_omissions'][0]
        response = self.source_response(item)
        response['sha'] = 'b' * 40
        with self.assertRaisesRegex(RuntimeError, 'blob metadata'):
            subject.validate_original_dotfile(item, response, self.exported, self.historical)

    def test_dotfile_changed_bytes_are_rejected(self):
        item = self.producer['archive_omissions'][0]
        response = self.source_response(item)
        response['content'] = base64.b64encode(b'changed bytes\n').decode()
        with self.assertRaisesRegex(RuntimeError, 'dotfile bytes'):
            subject.validate_original_dotfile(item, response, self.exported, self.historical)

    def test_unreviewed_supplement_path_is_rejected(self):
        item = dict(self.producer['archive_omissions'][0], distribution_path='Frameworks/other.framework/.gitattributes')
        with self.assertRaisesRegex(RuntimeError, 'original exported dotfile'):
            subject.validate_original_dotfile(item, {}, self.exported, self.historical)

    def test_hanlin_supplement_must_use_the_original_snapshot_revision(self):
        item = dict(self.producer['archive_omissions'][1], source_sha='c' * 40)
        with self.assertRaisesRegex(RuntimeError, 'Hanlin source binding'):
            subject.validate_original_dotfile(item, self.source_response(item), self.exported, self.historical)

    def archive_fixture(self, change=None):
        producer = copy.deepcopy(self.producer)
        original = encoded({'application_source': producer['source_sha'], 'original_trees': producer['source_trees']})
        clang = encoded({'source_sha': producer['source_sha'], 'run_id': producer['run_id'], 'run_attempt': 1,
                         'original_package_lock_sha256': '0' * 64})
        producer['original_source_sha256'] = hashlib.sha256(original).hexdigest()
        producer['clang_manifest_sha256'] = hashlib.sha256(clang).hexdigest()
        files = {**self.supplements, 'SourceProvenance/OriginalSource.json': original,
                 'SourceProvenance/ClangImportContext.json': clang, 'fixture/actual-product': b'original fixture product\n'}
        exported = {'files': {k: commitment(v) for k,v in files.items()}, 'bytes': sum(map(len, files.values()))}
        record = {'source_sha': producer['source_sha'], 'run_id': producer['run_id'], 'run_attempt': 1,
                  'qualified_distribution': False, 'restore_as_sdk_allowed': False,
                  'consumer_continuation_admission': 'NOT_IMPLEMENTED_OR_GRANTED',
                  'distribution_files': exported['files'], 'distribution_bytes': exported['bytes'],
                  'actual_execution_sha256': producer['retained_input_sha256']['execution.json'],
                  'source_before_sha256': producer['retained_input_sha256']['source-before.json'],
                  'source_after_sha256': producer['retained_input_sha256']['source-after.json'],
                  'successful_build_command_sha256': producer['retained_input_sha256']['framework-build.command.json'],
                  'source_evidence_archive': {'sha256': producer['evidence_inner_sha256'], 'bytes': producer['evidence_inner_bytes']}}
        receipt = encoded(record)
        producer['retention_receipt_sha256'] = hashlib.sha256(receipt).hexdigest()
        members = {'distribution/' + k: v for k,v in files.items() if k not in self.supplements}
        members['UNQUALIFIED_PRODUCER.json'] = receipt
        if change: change(members)
        archive = self.directory / 'original.zip'
        with zipfile.ZipFile(archive, 'x') as zipped:
            for name, data in members.items(): zipped.writestr(name, data)
        evidence = self.directory / 'evidence'
        evidence.mkdir()
        return producer, exported, archive, evidence, receipt

    def restore_fixture(self, change=None, supplements=None):
        producer, exported, archive, evidence, receipt = self.archive_fixture(change)
        destination = self.directory / 'distribution'
        before = subject.digest(archive)
        with patch.object(subject, 'read_clang_imports') as clang_parser:
            identity = subject.restore_original_distribution(archive, destination, evidence, producer, exported,
                                                             self.supplements if supplements is None else supplements)
            clang_parser.assert_called_once_with(destination, identity)
        self.assertEqual(subject.digest(archive), before)
        self.assertEqual(subject.inventory(destination), exported['files'])
        self.assertEqual((evidence / 'UNQUALIFIED_PRODUCER.json').read_bytes(), receipt)
        self.assertFalse((destination / 'QUALIFICATION.json').exists())
        return json.loads((evidence / 'RESTORATION.json').read_bytes())

    def test_restore_preserves_archive_and_recovers_only_two_exact_source_files(self):
        result = self.restore_fixture()
        self.assertEqual(result['restored_product_members'] - result['archive_product_members'], 2)
        self.assertTrue(result['historical_archive_unchanged'])

    def test_a_third_missing_archive_member_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'membership differs'):
            self.restore_fixture(lambda m: m.pop('distribution/fixture/actual-product'))

    def test_an_unexpected_archive_member_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'membership differs'):
            self.restore_fixture(lambda m: m.update({'distribution/unexpected': b'extra'}))

    def test_an_already_present_omission_is_rejected(self):
        name, data = next(iter(self.supplements.items()))
        with self.assertRaisesRegex(RuntimeError, 'membership differs'):
            self.restore_fixture(lambda m: m.update({'distribution/' + name: data}))

    def test_a_changed_supplement_cannot_complete_restoration(self):
        supplements = dict(self.supplements)
        supplements[next(iter(supplements))] = b'not original'
        with self.assertRaisesRegex(RuntimeError, 'source supplement differs'):
            self.restore_fixture(supplements=supplements)

    def test_a_changed_archived_product_cannot_complete_restoration(self):
        with self.assertRaisesRegex(RuntimeError, 'size differs|bytes differ'):
            self.restore_fixture(lambda m: m.update({'distribution/fixture/actual-product': b'changed fixture product\n'}))

    def validate_zip(self, entries):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zipped:
            for name, data in entries: zipped.writestr(name, data)
        stream.seek(0)
        with zipfile.ZipFile(stream) as zipped: return subject.zip_members(zipped)

    def test_zip_parent_traversal_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            self.validate_zip([('../outside', b'bad')])

    def test_zip_case_aliases_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Aliased'):
            self.validate_zip([('Source/File', b'one'), ('source/file', b'two')])

    def test_zip_symbolic_links_are_rejected(self):
        entry = zipfile.ZipInfo('distribution/link')
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaisesRegex(RuntimeError, 'Nonregular'):
            self.validate_zip([(entry, b'outside')])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, required=True)
    arguments = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationBoundaries)
    expected = [t.id().split('.')[-1] for t in suite]
    passed = []
    class Results(unittest.TextTestResult):
        def addSuccess(self, test):
            passed.append(test.id().split('.')[-1])
            super().addSuccess(test)
    outcome = unittest.TextTestRunner(verbosity=2, resultclass=Results).run(suite)
    paths = ['run_runtime_continuation.py', 'runtime_continuation_process.py',
             'runtime_continuation_inputs.json', 'test_runtime_continuation.py']
    result = {'status': 'PASS_NEW_CONTINUATION_BOUNDARY_CONTROLS' if outcome.wasSuccessful() else 'FAIL',
              'tests_run': outcome.testsRun, 'expected_ids': expected, 'passed_ids': passed,
              'failures': [str(t) for t,_ in outcome.failures], 'errors': [str(t) for t,_ in outcome.errors],
              'skipped': [str(t) for t,_ in outcome.skipped],
              'source_sha256': {'Tools/OriginalEditor/' + p: subject.digest(ROOT / 'Tools/OriginalEditor' / p) for p in paths},
              'prior_test_bodies_replayed': 0, 'apple_build_or_runtime_executed': False,
              'restoration_fixture_scope': 'Synthetic small products; only existing Clang parser call is stubbed. Runtime uses the real parser.',
              'historical_receipt_fixture_sha256': HISTORICAL_SHA}
    arguments.result.parent.mkdir(parents=True, exist_ok=True)
    arguments.result.write_bytes(encoded(result))
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
