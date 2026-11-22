"""New genuine-producer/unchanged-archiver adapter boundaries only."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / 'candidate/Tools/OriginalEditor'))
sys.path.insert(1, str(PACKET / 'preimage/Tools/OriginalEditor'))
import framework_consumer_retention as adapter


class RetentionAdapterControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.evidence, self.work = self.root / 'build/evidence', self.root / 'build/work'
        self.evidence.mkdir(parents=True)
        self.work.mkdir()
        self.app = self.work / 'OriginalEditorConsumer.app'
        self.app.mkdir()
        (self.app / 'OriginalEditorConsumer').write_bytes(b'EXPLICIT_ARCHIVE_FIXTURE_NOT_NATIVE_BINARY')
        (self.app / 'OriginalEditorConsumer').chmod(0o755)
        self.source = {'head_sha': 'a' * 40, 'run_id': '912345', 'run_attempt': '1'}
        self.environment = {'GITHUB_SHA': self.source['head_sha'], 'GITHUB_RUN_ID': self.source['run_id'],
                            'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REPOSITORY': adapter.REPOSITORY,
                            'GITHUB_REPOSITORY_ID': '1289863025', 'GITHUB_REF': 'refs/heads/' + adapter.BRANCH}
        self.signature = {'command': ['codesign', '--verify', '--strict', str(self.app)],
                          'cwd': str(self.root), 'returncode': 0, 'timed_out': False}
        for stream in ['stdout', 'stderr']:
            raw = ('EXPLICIT_SIGNATURE_COMMAND_' + stream).encode()
            (self.evidence / ('external-consumer-signature.' + stream + '.log')).write_bytes(raw)
            self.signature[stream + '_sha256'] = hashlib.sha256(raw).hexdigest()
        self.save_signature()

    def save_signature(self):
        self.command_path = self.evidence / 'external-consumer-signature.command.json'
        self.command_path.write_text(json.dumps(self.signature))

    def test_success_adapter_binds_exact_original_command_without_extra_drain_claim(self):
        value = adapter.adapt_signature(self.app, self.root, self.evidence)
        self.assertEqual(value['original_command_sha256'], hashlib.sha256(self.command_path.read_bytes()).hexdigest())
        self.assertEqual(value['argv'], self.signature['command'])
        self.assertEqual(value['effective_returncode'], 0)
        self.assertIn('no additional process-group drain claim', value['scope'])

    def test_failed_signature_cannot_be_adapted(self):
        self.signature['returncode'] = 1
        self.save_signature()
        with self.assertRaisesRegex(ValueError, 'did not succeed'):
            adapter.adapt_signature(self.app, self.root, self.evidence)

    def test_timed_out_signature_cannot_be_adapted(self):
        self.signature['timed_out'] = True
        self.save_signature()
        with self.assertRaisesRegex(ValueError, 'did not succeed'):
            adapter.adapt_signature(self.app, self.root, self.evidence)

    def test_changed_signature_stream_cannot_be_adapted(self):
        (self.evidence / 'external-consumer-signature.stderr.log').write_text('CHANGED')
        with self.assertRaisesRegex(ValueError, 'output differs'):
            adapter.adapt_signature(self.app, self.root, self.evidence)

    def test_genuine_framework_and_consumer_are_both_bound_to_this_producer(self):
        consumer, framework = adapter.current_producers(self.source, self.environment)
        self.assertEqual(consumer['control_sha'], framework['source_sha'])
        self.assertEqual(consumer['run_id'], framework['run_id'])
        self.assertEqual(consumer['workflow_path'], '.github/workflows/pinkha-original-editor-framework.yml')
        self.assertEqual(framework['job_name'], 'original-editor-framework')

    def test_foreign_source_run_or_branch_is_refused(self):
        for key, value in [('GITHUB_SHA', 'b' * 40), ('GITHUB_RUN_ID', '912346'),
                           ('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_REF', 'refs/heads/other')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'this original producer'):
                adapter.current_producers(self.source, {**self.environment, key: value})

    def test_real_unchanged_archiver_preserves_new_adapter_bytes_modes_and_false_qualification(self):
        probe = self.root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift'
        probe.parent.mkdir(parents=True)
        probe.write_text('EXPLICIT_PROBE_SOURCE_FIXTURE')
        (self.evidence / 'consumer-source-inputs.json').write_text('{"EXPLICIT_SOURCE_INVENTORY_FIXTURE": true}')
        with patch.dict(os.environ, self.environment):
            value = adapter.retain_built_consumer(self.app, self.root, self.evidence, self.work, self.source)
        self.assertFalse(value['runtime_qualified'])
        self.assertFalse(value['restore_as_original_sdk_allowed'])
        self.assertEqual(value['consumer_producer']['control_sha'], value['framework_producer']['source_sha'])
        with zipfile.ZipFile(self.work / 'retained-consumer/consumer-app.zip') as archive:
            self.assertEqual(archive.read('OriginalEditorConsumer.app/OriginalEditorConsumer'),
                             (self.app / 'OriginalEditorConsumer').read_bytes())
            self.assertEqual((archive.getinfo('OriginalEditorConsumer.app/OriginalEditorConsumer').external_attr >> 16) & 0o777, 0o755)
            self.assertIsNone(archive.testzip())

    def test_complete_new_fixture_inverse_preserves_all_ten_old_test_bodies(self):
        relative = 'Tools/OriginalEditor/test_framework_flow.py'
        before, after = [(PACKET / part / relative).read_text() for part in ['preimage', 'candidate']]
        additions = "            stack.enter_context(patch.object(driver, 'verify_framework_install_name', return_value={\n                'scope': 'EXPLICIT_MACHO_BOUNDARY_DOUBLE_NO_NATIVE_BINARY_ACCEPTANCE'}))\n            stack.enter_context(patch.object(driver, 'verify_consumer_install_name', return_value={\n                'scope': 'EXPLICIT_MACHO_BOUNDARY_DOUBLE_NO_NATIVE_BINARY_ACCEPTANCE'}))\n            stack.enter_context(patch.object(driver, 'retain_built_consumer', return_value={\n                'scope': 'EXPLICIT_SIGNED_APP_RETENTION_BOUNDARY_DOUBLE_NO_APP_ARCHIVE'}))\n"
        self.assertEqual(after.replace(additions, '', 1), before)
        def tests(source):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(source))
                    if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
        self.assertEqual(len(tests(before)), 10)
        self.assertEqual(tests(before), tests(after))


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print('START ' + test.id(), flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        print('PASS ' + test.id(), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2, testRunner=unittest.TextTestRunner(resultclass=RecordedResult, verbosity=2))
