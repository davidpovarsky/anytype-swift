"""New diagnostic boundaries using explicit local filesystem/command fixtures.

No Apple tool, simulator, real crash, native app or runtime acceptance executes.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'candidate/Tools/OriginalEditor/consumer_failure_capture.py'
spec = importlib.util.spec_from_file_location('consumer_failure_capture', SOURCE)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


class FailureCaptureControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()
        self.environment = patch.dict(os.environ, {'HOME': str(self.home), 'GITHUB_SHA': 'a' * 40,
                                                   'GITHUB_RUN_ID': '123456', 'GITHUB_RUN_ATTEMPT': '1'})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.udid = '11111111-1111-4111-8111-111111111111'
        self.app = self.home / 'Library/Developer/CoreSimulator/Devices' / self.udid / 'data/Containers/Bundle/Application/22222222-2222-4222-8222-222222222222/OriginalEditorConsumer.app'
        self.app.mkdir(parents=True)
        self.info = {'CFBundleIdentifier': helper.BUNDLE_ID, 'CFBundleExecutable': helper.EXECUTABLE}
        (self.app / 'Info.plist').write_bytes(plistlib.dumps(self.info))
        (self.app / helper.EXECUTABLE).write_bytes(b'CONTROLLED EXECUTABLE FIXTURE; NOT MACH-O')
        self.evidence = self.home / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.reports = self.home / 'Library/Logs/DiagnosticReports'
        self.reports.mkdir(parents=True)
        self.preflight = {'status': 'PREFLIGHT_PASS_UI_NOT_RUN', 'source_sha': 'a' * 40,
                          'run_id': '123456', 'run_attempt': '1',
                          'selected': {'ipad': {'udid': self.udid, 'name': 'Pinkha-UI27-123456-ipad'}}}
        self.original = ['xcrun', 'simctl', 'launch', '--terminate-running-process', self.udid, helper.BUNDLE_ID,
                         '--original-editor-nonce', '33333333-3333-4333-8333-333333333333',
                         '-AppleLanguages', '(en)', '-AppleLocale', 'en_US']
        self.help = 'CONTROLLED HELP FIXTURE: --stdout=<path> --stderr=<path>'

    def prepare(self):
        with patch.object(helper.time, 'time', return_value=100.0):
            self.argv, self.request_path = helper.prepare_launch_capture(self.evidence, self.preflight, str(self.app),
                                                                        self.original, 'en', self.help)
        self.request = json.loads(self.request_path.read_bytes())
        return self.request

    def terminal(self):
        if not hasattr(self, 'request'):
            self.prepare()
        command = {'command': self.argv, 'started_at': timestamp(100.1), 'finished_at': timestamp(100.2),
                   'returncode': 3, 'timed_out': False}
        for stream in ['stdout', 'stderr']:
            raw = (b'simctl fixture\r\n' if stream == 'stdout' else b'fixture launch error\x00\r\n')
            (self.evidence / ('consumer-en-launch.' + stream + '.log')).write_bytes(raw)
            command[stream + '_sha256'] = hashlib.sha256(raw).hexdigest()
            Path(self.request['streams'][stream]).write_bytes(b'consumer ' + stream.encode() + b'\r\n')
        self.command_path = self.evidence / 'consumer-en-launch.command.json'
        self.command_path.write_text(json.dumps(command))
        return command

    def ips(self, name='OriginalEditorConsumer-current.ips', **changes):
        body = {'procName': helper.EXECUTABLE, 'procPath': str(self.app / helper.EXECUTABLE),
                'captureTime': timestamp(100.5), 'bundleInfo': {'CFBundleIdentifier': helper.BUNDLE_ID},
                'fixture': 'NO REAL CRASH WAS EXECUTED'}
        body.update(changes)
        path = self.reports / name
        raw = (json.dumps({'bundleID': body['bundleInfo']['CFBundleIdentifier']}) + '\n' + json.dumps(body)).encode()
        path.write_bytes(raw)
        os.utime(path, (100.6, 100.6))
        return raw, path

    def collect(self):
        with patch.object(helper.time, 'time', return_value=101.0):
            return helper.collect_failure(self.request_path)

    def test_prepare_changes_only_two_output_options(self):
        self.prepare()
        self.assertEqual(self.argv[:3] + self.argv[5:], self.original)
        self.assertEqual(self.argv[3:5], ['--stdout=' + self.request['streams']['stdout'], '--stderr=' + self.request['streams']['stderr']])
        self.assertEqual(self.request['original_launch_argv'], self.original)
        self.assertFalse(self.request['runtime_authority'])
        for path in self.request['streams'].values():
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)

    def test_missing_actual_help_option_refuses_before_output_creation(self):
        self.help = '--stdout=<path>'
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertFalse((self.evidence / 'consumer-failure-capture').exists())

    def test_foreign_producer_refused(self):
        self.preflight['source_sha'] = 'b' * 40
        with self.assertRaises(RuntimeError):
            self.prepare()

    def test_wrong_owned_device_name_refused(self):
        self.preflight['selected']['ipad']['name'] = 'preexisting-other-device'
        with self.assertRaises(RuntimeError):
            self.prepare()

    def test_installed_bundle_identity_refused(self):
        self.info['CFBundleIdentifier'] = 'org.other.application'
        (self.app / 'Info.plist').write_bytes(plistlib.dumps(self.info))
        with self.assertRaises(RuntimeError):
            self.prepare()

    def test_foreign_device_container_refused(self):
        self.preflight['selected']['ipad']['udid'] = '44444444-4444-4444-8444-444444444444'
        self.original[4] = self.preflight['selected']['ipad']['udid']
        with self.assertRaises(RuntimeError):
            self.prepare()

    def test_changed_original_launch_arguments_refused(self):
        self.original[-1] = 'unexpected_LOCALE'
        with self.assertRaises(RuntimeError):
            self.prepare()

    def test_original_launch_error_and_raw_outputs_retained_without_authority(self):
        self.terminal()
        result = self.collect()
        self.assertEqual(result['launch_returncode'], 3)
        self.assertFalse(result['runtime_authority'])
        self.assertEqual(result['crash_delivery'], 'NO_ATTRIBUTABLE_REPORT_OBSERVED_IN_THIS_SNAPSHOT')
        for label, observation in result['streams'].items():
            self.assertEqual(observation['status'], 'OBSERVED_STABLE_AT_READ', label)
            raw = (self.evidence / observation['path']).read_bytes()
            self.assertEqual(observation['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse((self.evidence / 'QUALIFICATION.json').exists())

    def test_only_native_identity_bound_ips_and_text_reports_copied(self):
        self.terminal()
        ips_raw, _ = self.ips()
        crash = ('Process: OriginalEditorConsumer [456]\nPath: ' + str(self.app / helper.EXECUTABLE)
                 + '\nIdentifier: ' + helper.BUNDLE_ID + '\nDate/Time: ' + timestamp(100.55)
                 + '\nCONTROLLED TEXT REPORT; NO REAL CRASH\n').encode()
        path = self.reports / 'OriginalEditorConsumer_current.crash'
        path.write_bytes(crash)
        os.utime(path, (100.6, 100.6))
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 2)
        copied = {(self.request_path.parent / row['path']).read_bytes() for row in result['crash_reports']}
        self.assertEqual(copied, {ips_raw, crash})
        self.assertTrue(all(row['native_identity']['process_path'] == str(self.app / helper.EXECUTABLE) for row in result['crash_reports']))

    def test_foreign_bundle_and_device_reports_are_not_retained(self):
        self.terminal()
        self.ips('OriginalEditorConsumer-foreign-bundle.ips', bundleInfo={'CFBundleIdentifier': 'org.other'})
        self.ips('OriginalEditorConsumer-foreign-device.ips', procPath=str(self.app / helper.EXECUTABLE).replace(self.udid, '44444444-4444-4444-8444-444444444444'))
        self.ips('OriginalEditorConsumer-foreign-process.ips', procName='OtherProcess')
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 0)
        self.assertEqual(result['candidate_reports_unattributed_or_unreadable'], 3)
        self.assertEqual(list(self.request_path.parent.glob('crash-*')), [])

    def test_stale_and_future_report_times_are_not_retained(self):
        self.terminal()
        self.ips('OriginalEditorConsumer-old-native-time.ips', captureTime=timestamp(99))
        self.ips('OriginalEditorConsumer-future-native-time.ips', captureTime=timestamp(102))
        _, path = self.ips('OriginalEditorConsumer-old-file-time.ips')
        os.utime(path, (99, 99))
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 0)
        self.assertEqual(result['candidate_reports_read'], 2)

    def test_malformed_and_oversized_reports_are_not_retained(self):
        self.terminal()
        for name, data in [('OriginalEditorConsumer-malformed.ips', b'{broken'),
                           ('OriginalEditorConsumer-large.ips', b'x' * (helper.MAX_REPORT_BYTES + 1))]:
            path = self.reports / name
            path.write_bytes(data)
            os.utime(path, (100.6, 100.6))
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 0)
        self.assertEqual(result['candidate_reports_unattributed_or_unreadable'], 2)

    def test_symlink_reports_and_outputs_are_not_read_as_owned(self):
        self.terminal()
        _, target = self.ips('OriginalEditorConsumer-real.ips')
        (self.reports / 'OriginalEditorConsumer-alias.ips').symlink_to(target)
        output = Path(self.request['streams']['stderr'])
        output.unlink()
        output.symlink_to(target)
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 1)
        self.assertEqual(result['streams']['application_stderr']['status'], 'UNAVAILABLE_OR_UNSTABLE')

    def test_matching_report_count_is_bounded(self):
        self.terminal()
        for number in range(helper.MAX_REPORTS + 2):
            self.ips('OriginalEditorConsumer-' + str(number) + '.ips')
        result = self.collect()
        self.assertEqual(result['captured_report_count'], helper.MAX_REPORTS)
        self.assertTrue(result['scan_bound_reached'])

    def test_directory_scan_is_nonrecursive_and_bounded(self):
        self.terminal()
        for number in range(helper.MAX_DIRECTORY_ENTRIES + 2):
            (self.reports / ('OtherApplication-' + str(number) + '.ips')).touch()
        nested = self.reports / 'Retired'
        nested.mkdir()
        raw, path = self.ips('OriginalEditorConsumer-nested.ips')
        path.rename(nested / path.name)
        result = self.collect()
        self.assertEqual(result['captured_report_count'], 0)
        self.assertEqual(result['bounded_entries_examined'], helper.MAX_DIRECTORY_ENTRIES)
        self.assertTrue(result['scan_bound_reached'])

    def test_capture_request_tampering_refused(self):
        self.terminal()
        self.request['expected_process_path'] = '/unowned/OriginalEditorConsumer'
        self.request_path.write_text(json.dumps(self.request))
        with self.assertRaises(RuntimeError):
            self.collect()

    def test_actual_command_tampering_refused(self):
        command = self.terminal()
        command['command'] = ['unrelated-command']
        self.command_path.write_text(json.dumps(command))
        with self.assertRaises(RuntimeError):
            self.collect()

    def test_expired_attempt_refused(self):
        self.terminal()
        with patch.object(helper.time, 'time', return_value=221.0):
            with self.assertRaises(RuntimeError):
                helper.collect_failure(self.request_path)

    def test_changed_simctl_stream_is_not_claimed_as_original(self):
        self.terminal()
        (self.evidence / 'consumer-en-launch.stderr.log').write_bytes(b'changed after original command')
        result = self.collect()
        self.assertEqual(result['streams']['simctl_stderr']['status'], 'UNAVAILABLE_OR_UNSTABLE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
