"""Regress the actual stderr-only Xcode27 help, without executing Apple tools."""
from pathlib import Path
import unittest
from consumer_failure_capture import combine_launch_help

PACKET = Path(__file__).resolve().parents[2] / 'docs/pinkha/torah-integration/evidence/original-editor-signed-consumer-20261123'


class LaunchHelpStreams(unittest.TestCase):
    def setUp(self):
        self.help = (PACKET / 'actual-simctl-launch-help.stderr.log').read_text()

    def test_actual_stderr_help_is_admitted_with_empty_stdout(self):
        stdout = (PACKET / 'actual-simctl-launch-help.stdout.log').read_text()
        self.assertEqual(stdout, '')
        self.assertIn('--stdout=<path>', combine_launch_help(stdout, self.help))
        self.assertIn('--stderr=<path>', combine_launch_help(stdout, self.help))

    def test_stdout_help_remains_supported(self):
        self.assertIn(self.help, combine_launch_help(self.help, ''))

    def test_missing_output_option_still_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'does not advertise'):
            combine_launch_help('', self.help.replace('--stderr', '--unavailable'))

    def test_oversized_help_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'bounded'):
            combine_launch_help(self.help, 'x' * 65537)



class ExactUploadMetadataProof(unittest.TestCase):
    """Source controls over authentic API/log evidence; no Apple execution."""
    def fixture(self):
        import json
        from run_runtime_continuation import verify_metadata
        inputs = json.loads((PACKET.parents[4] / 'Tools/OriginalEditor/signed_consumer_continuation_inputs.json').read_bytes())
        return (verify_metadata, inputs['producer'],
                json.loads((PACKET / 'original-run-metadata.json').read_bytes()),
                json.loads((PACKET / 'original-job-metadata.json').read_bytes()),
                json.loads((PACKET / 'original-consumer-artifact-metadata.json').read_bytes()),
                inputs['artifacts']['consumer'], (PACKET / 'original-signed-consumer-upload.log').read_bytes())

    def test_actual_artifact_binds_to_its_successful_upload(self):
        verify, producer, run, job, artifact, expected, log = self.fixture()
        proof = verify(producer, run, job, artifact, expected, upload_log=log)
        self.assertEqual(proof['status'], 'EXACT_SUCCESSFUL_UPLOAD_LOG_ARTIFACT_BINDING')
        self.assertEqual(proof['artifact_id'], 14769044048)
        self.assertEqual(proof['artifact_sha256'], expected['sha256'])
        self.assertEqual(proof['artifact_bytes'], 141878849)
        self.assertFalse(proof['timestamp_tolerance_applied'])
        self.assertEqual(proof['artifact_created_at'], '2026-11-22T19:41:12Z')
        self.assertEqual(proof['step_completed_at'], '2026-11-22T19:41:11Z')

    def test_original_caller_path_remains_strict(self):
        import copy
        verify, producer, run, job, artifact, expected, log = self.fixture()
        with self.assertRaisesRegex(RuntimeError, 'exact successful upload'):
            verify(producer, run, job, artifact, expected)
        control = copy.deepcopy(artifact)
        control['created_at'] = '2026-11-22T19:41:10Z'
        self.assertIsNone(verify(producer, run, job, control, expected))

    def test_wrong_artifact_finalization_id_digest_and_size_are_rejected(self):
        verify, producer, run, job, artifact, expected, log = self.fixture()
        for before, after in [(b'14769044048', b'14769044049'),
                              (expected['sha256'].encode(), b'0' * 64),
                              (b'141878849 bytes', b'141878848 bytes')]:
            with self.subTest(value=before.decode()), self.assertRaises(RuntimeError):
                verify(producer, run, job, artifact, expected, upload_log=log.replace(before, after))

    def test_wrong_producer_job_or_failed_upload_is_rejected(self):
        import copy
        verify, producer, run, job, artifact, expected, log = self.fixture()
        for field, replacement in [('id', job['id'] + 1), ('head_sha', '0' * 40)]:
            changed = copy.deepcopy(job)
            changed[field] = replacement
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                verify(producer, run, changed, artifact, expected, upload_log=log)
        changed = copy.deepcopy(job)
        next(step for step in changed['steps'] if step['name'] == expected['upload_step'])['conclusion'] = 'failure'
        with self.assertRaises(RuntimeError):
            verify(producer, run, changed, artifact, expected, upload_log=log)

    def test_artifact_outside_original_job_is_still_rejected(self):
        import copy
        verify, producer, run, job, artifact, expected, log = self.fixture()
        changed = copy.deepcopy(artifact)
        changed['created_at'] = '2026-11-22T19:42:00Z'
        with self.assertRaises(RuntimeError):
            verify(producer, run, job, changed, expected, upload_log=log)

    def test_missing_duplicate_or_misdated_finalization_is_rejected(self):
        verify, producer, run, job, artifact, expected, log = self.fixture()
        for changed in [b'', log + log, log.replace(b'19:41:11.', b'19:42:11.')]:
            with self.subTest(length=len(changed)), self.assertRaises(RuntimeError):
                verify(producer, run, job, artifact, expected, upload_log=changed)


class RawUploadLogCapture(unittest.TestCase):
    def test_documented_raw_flag_is_limited_to_the_exact_original_job_log(self):
        from run_signed_consumer_continuation import original_upload_log_argv
        observed = (PACKET / 'actual-gh-api-log-guard.stderr').read_text()
        self.assertIn('--allow-escape-sequences', observed)
        self.assertEqual(original_upload_log_argv(137324774911),
                         ['gh', 'api', '--allow-escape-sequences',
                          'repos/davidpovarsky/anytype-swift/actions/jobs/137324774911/logs'])
        for job in [True, 0, -1, '137324774911']:
            with self.subTest(job=job), self.assertRaises(RuntimeError):
                original_upload_log_argv(job)

    def test_actual_owned_capture_preserves_raw_bytes_and_nonzero_failure(self):
        import hashlib
        import os
        import sys
        import tempfile
        import time
        from runtime_continuation_process import Commands
        with tempfile.TemporaryDirectory(prefix='original-upload-capture-control-') as temporary:
            root = Path(temporary)
            commands = Commands(root, dict(os.environ), time.time() + 30)
            raw = b'original upload fixture: \x1b[31mretained\x1b[0m\n'
            program = 'import sys;sys.stdout.buffer.write(' + repr(raw) + ')'
            output = commands.require('owned-raw-fixture', [sys.executable, '-c', program], root, 10)
            self.assertEqual(output.parent, root)
            self.assertEqual(output.read_bytes(), raw)
            self.assertEqual(commands.items[-1]['stdout_sha256'], hashlib.sha256(raw).hexdigest())
            with self.assertRaisesRegex(RuntimeError, 'owned command failed'):
                commands.require('owned-raw-nonzero',
                                 [sys.executable, '-c', program + ';raise SystemExit(7)'], root, 10)
            self.assertEqual(commands.items[-1]['returncode'], 7)
            self.assertEqual(commands.items[-1]['effective_returncode'], 7)
            self.assertFalse(commands.items[-1]['timed_out'])
            self.assertTrue(commands.owned_groups_drained)

if __name__ == '__main__':
    unittest.main()
