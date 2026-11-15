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


if __name__ == '__main__':
    unittest.main()
