"""Selection/evidence controls only; no Xcode or UI execution occurs here."""
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import run_ui27 as runner


class UIExecutionControls(unittest.TestCase):
    def test_environment_reaches_only_actual_target(self):
        value = [dict(BlueprintName='AnytypeTests'), dict(BlueprintName='OtherTests')]
        runner.inject(value, 'AnytypeTests', {'REAL_ENV': '1'})
        self.assertEqual(value[0]['EnvironmentVariables'], {'REAL_ENV': '1'})
        self.assertNotIn('EnvironmentVariables', value[1])

    def test_generated_cached_configuration_is_not_selected_as_xcode_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['Original.xctestrun', 'UI27-old.xctestrun']:
                with (root / name).open('wb') as output:
                    plistlib.dump(dict(BlueprintName='AnytypeTests'), output)
            self.assertEqual(runner.test_configuration(root, 'AnytypeTests').name, 'Original.xctestrun')

    def exercise(self, passed=3, failed=0, command_failure=False, methods=None, os_version='27.0'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = root / 'Original.xctestrun'
            with configuration.open('wb') as output:
                plistlib.dump(dict(BlueprintName='PinkhaStage1AcceptanceUITests'), output)
            selected = ['Suite/' + name for name in runner.SMOKE]
            def simulated_command(argv, app, evidence, result, prefix):
                self.assertEqual(len([v for v in argv if v.startswith('-only-testing:')]), 3)
                (evidence / (prefix + '-summary.json')).write_text(json.dumps(dict(
                    passedTests=passed, failedTests=failed, skippedTests=0, totalTestCount=passed + failed,
                    devicesAndConfigurations=[dict(device=dict(deviceId='disposable', osVersion=os_version, architecture='arm64'))])))
                cases = methods if methods is not None else [dict(nodeType='Test Case', nodeIdentifier=name + '()',
                    result='Passed' if i < passed else 'Failed') for i, name in enumerate(selected)]
                (evidence / (prefix + '-tests.json')).write_text(json.dumps(cases))
                if command_failure:
                    raise subprocess.CalledProcessError(65, ['xcodebuild'])
            with patch.object(runner, 'run_xctest', side_effect=simulated_command):
                return runner.run_selection(root, configuration, 'PinkhaStage1AcceptanceUITests', 'disposable',
                    selected, {}, root / 'fresh', 'control')

    def test_exact_three_actual_methods_are_required(self):
        result = self.exercise()
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['passed'], 3)
        self.assertEqual(result['command_exit_code'], 0)

    def test_zero_test_green_command_is_rejected(self):
        self.assertEqual(self.exercise(passed=0, methods=[])['status'], 'FAIL')

    def test_actual_os26_results_cannot_satisfy_os27_selection(self):
        self.assertEqual(self.exercise(os_version='26.2')['status'], 'FAIL')

    def test_partial_failure_retains_actual_passed_and_failed_counts(self):
        result = self.exercise(passed=2, failed=1, command_failure=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual((result['passed'], result['failed'], result['skipped']), (2, 1, 0))
        self.assertEqual(result['command_exit_code'], 65)

    def test_stale_pass_evidence_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / 'result.json'
            receipt.write_text('{"status":"PASS","run":"old"}')
            with self.assertRaisesRegex(RuntimeError, 'stale selection'):
                runner.run_selection(root, root / 'unused', 'AnytypeTests', 'disposable', [], {}, root, 'control')
            self.assertEqual(json.loads(receipt.read_text())['run'], 'old')

    def exercise_runtime(self, mapped_pid=123, changed_identity=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'Installed' / 'Anytype.app'
            runtime = installed / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
            identity = 'Sun Nov 15 09:00:00 2026 ' + str(installed / 'Anytype')
            def output(argv, **kwargs):
                if argv[:3] == ['xcrun', 'simctl', 'get_app_container']:
                    return str(installed)
                if argv[:3] == ['xcrun', 'simctl', 'launch']:
                    self.assertEqual(argv[3], '--terminate-running-process')
                    self.assertEqual(argv[-4:], ['-AppleLanguages', '(he)', '-AppleLocale', 'he_IL'])
                    self.assertEqual(kwargs['env']['SIMCTL_CHILD_PINKHA_UI27_ROUTE_OBSERVATION'], '1')
                    return 'io.anytype.app: 123'
                self.assertEqual(argv[:4], ['ps', '-ww', '-p', '123'])
                if len(argv) == 6:
                    return str(installed / 'Anytype')
                return identity + (' changed' if changed_identity and output.calls else '')
            output.calls = 0
            def counted_output(argv, **kwargs):
                result = output(argv, **kwargs)
                if argv[0] == 'ps' and len(argv) == 8:
                    output.calls += 1
                return result
            mapping = subprocess.CompletedProcess([], 0, 'Process: Anytype [' + str(mapped_pid) + ']\n' + str(runtime), '')
            with patch.object(runner.subprocess, 'check_output', side_effect=counted_output), \
                    patch.object(runner.subprocess, 'run', return_value=mapping), \
                    patch.object(runner, 'digest', return_value='same-bytes'), \
                    patch.object(runner, 'contains', return_value=True):
                return runner.live_runtime('disposable', root, root / 'Anytype.app', 'he')

    def test_runtime_mapping_is_bound_to_target_pid_and_stable_process_start(self):
        result = self.exercise_runtime()
        self.assertEqual(result['pid'], 123)
        self.assertTrue(result['runtime_loaded'])
        self.assertTrue(result['process_identity_unchanged'])
        self.assertFalse(result['every_launch_verified'])

    def test_another_pid_mapping_or_recycled_identity_is_rejected(self):
        for arguments in [dict(mapped_pid=124), dict(changed_identity=True)]:
            with self.subTest(arguments=arguments), self.assertRaisesRegex(RuntimeError, 'process identity/runtime'):
                self.exercise_runtime(**arguments)

    def test_actual_boundary_attachments_must_bind_all_selected_methods_to_mapped_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            attachments = root / 'smoke-attachments'
            attachments.mkdir()
            names = ['Suite/one', 'Suite/two']
            manifest = []
            for index, name in enumerate(names):
                rows = []
                for label in ['entry-hierarchy', 'final-hierarchy']:
                    filename = str(index) + '-' + label + '.txt'
                    (attachments / filename).write_text("Application, 0x10369b340, pid: 68005, label: 'Anytype'\n")
                    rows.append(dict(suggestedHumanReadableName=label, exportedFileName=filename))
                manifest.append(dict(testIdentifier=name + '()', attachments=rows))
            (attachments / 'manifest.json').write_text(json.dumps(manifest))
            live = dict(pid=68005, installed_app='/installed/Anytype.app',
                        process_start_identity='start /installed/Anytype.app/Anytype', runtime_sha256='runtime')
            with patch.object(runner, 'read_process_identity', return_value=live['process_start_identity']):
                result = runner.verify_ui_process_continuity(root, 'smoke', live, names)
            self.assertEqual(set(result['methods']), set(names))
            self.assertFalse(result['every_launch_verified'])
            with patch.object(runner, 'read_process_identity', return_value='recycled process start'), \
                    self.assertRaisesRegex(RuntimeError, 'start identity changed'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (attachments / '1-final-hierarchy.txt').write_text("Application, 0x10369b340, pid: 99999, label: 'Anytype'\n")
            with self.assertRaisesRegex(RuntimeError, 'differs from the mapped'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (attachments / 'manifest.json').write_text(json.dumps(manifest[:1]))
            with self.assertRaisesRegex(RuntimeError, 'missing selected UI methods'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)


if __name__ == '__main__':
    unittest.main()
