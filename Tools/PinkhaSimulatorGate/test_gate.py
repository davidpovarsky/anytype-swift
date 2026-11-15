"""Adversarial gate controls; synthetic records here are never UI acceptance evidence."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('gate', Path(__file__).with_name('validate_release.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.required = dict(id='UI04', criteria=['actual-tap', 'visual-layout'], visual=True)
        self.configuration = 'ipad-en-portrait-os27'
        self.candidate = dict(kit_sha='c' * 40, native_patch_sha256='d' * 64, hashes={'source.swift': 'e' * 64})
        self.png = b'\x89PNG\r\n\x1a\n' + b'\0' * 8 + struct.pack('>II', 2048, 2732)
        self.files = {'summary.json': json.dumps(dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                          devicesAndConfigurations=[dict(device=dict(osVersion='27.0', osBuildNumber='actual-build',
                          deviceId='uuid', modelName='iPad', architecture='arm64'))])).encode(),
                      'tests.json': json.dumps(dict(nodeType='Test Case', nodeIdentifier='Suite/testActual()', result='Passed')).encode(),
                      'shot.png': self.png}
        self.record = dict(status='EXECUTED_PASS', case_id='UI04', configuration_id=self.configuration,
            criteria=self.required['criteria'], source_sha='a' * 40, run_id='123', run_attempt='1', ui_command_exit_code=0,
            identity=dict(kit_checkout_sha='c' * 40, kit_lock_sha='c' * 40, native_patch_sha256='d' * 64,
                os_version='27.0', os_build='actual-build', device_family='ipad', device_model='iPad', simulator_udid='uuid',
                xcode_version='Xcode 27.0', architecture='arm64', app_launched=True, live_pid=100,
                embedded_runtime_sha256='b' * 64, live_runtime_sha256='b' * 64, native_marker_present=True,
                live_runtime_loaded=True, app_executable_sha256='f' * 64, app_language='en', orientation='portrait', appearance='light'),
            candidate_input_hashes=self.candidate['hashes'], methods=['Suite/testActual()'],
            coverage_review=dict(reviewer='QA', criteria=self.required['criteria'], methods=['Suite/testActual()']),
            summary_path='summary.json', tests_path='tests.json', counts=dict(passed=1, failed=0, skipped=0),
            screenshots=[dict(path='shot.png', sha256=gate.digest(self.png))])
        self.reviews = [dict(case_id='UI04', configuration_id=self.configuration, run_id='123',
            screenshot_sha256=gate.digest(self.png), verdict='PASS', reviewer='QA', reviewer_thread_id='review-thread',
            criteria=self.required['criteria'])]

    def validate(self):
        return gate.validate_record(self.required, self.configuration, self.record, self.files, self.candidate, self.reviews)

    def test_diagnostic_run_cannot_supply_release_evidence(self):
        for scope in ['STARTUP_IPAD_DIAGNOSTIC', 'NATIVE_CANCELLATION_DIAGNOSTIC']:
            with self.subTest(scope=scope):
                self.files['execution.json'] = json.dumps(dict(ui_scope=scope)).encode()
                with self.assertRaisesRegex(ValueError, 'Diagnostic UI selection'):
                    self.validate()

    def test_consistent_control_record(self):
        self.assertEqual(self.validate()['status'], 'EXECUTED_PASS')

    def test_empty_actual_selection_rejected(self):
        summary = json.loads(self.files['summary.json'])
        summary.update(totalTestCount=0, passedTests=0)
        self.files['summary.json'] = json.dumps(summary).encode()
        with self.assertRaisesRegex(ValueError, 'Zero-test'):
            self.validate()

    def test_raw_os26_cannot_be_hidden_by_receipt_os27(self):
        summary = json.loads(self.files['summary.json'])
        summary['devicesAndConfigurations'][0]['device']['osVersion'] = '26.2'
        self.files['summary.json'] = json.dumps(summary).encode()
        with self.assertRaisesRegex(ValueError, 'Raw xcresult'):
            self.validate()

    def test_missing_or_skipped_named_method_rejected(self):
        for result in ['Skipped', 'Failed', None]:
            with self.subTest(result=result):
                self.files['tests.json'] = json.dumps(dict(nodeType='Test Case', nodeIdentifier='Suite/testActual()', result=result)).encode()
                with self.assertRaisesRegex(ValueError, 'absent, failed or skipped'):
                    self.validate()

    def test_os26_cannot_be_relabelled_as_os27(self):
        self.record['identity']['os_version'] = '26.2'
        with self.assertRaisesRegex(ValueError, 'Actual OS27'):
            self.validate()

    def test_stale_compiled_inputs_rejected(self):
        self.record['candidate_input_hashes'] = {'source.swift': '0' * 64}
        with self.assertRaisesRegex(ValueError, 'inputs are stale'):
            self.validate()

    def test_wrong_kit_and_live_runtime_rejected(self):
        for key in ['kit_lock_sha', 'live_runtime_sha256']:
            with self.subTest(key=key):
                original = self.record['identity'][key]
                self.record['identity'][key] = '0' * len(original)
                with self.assertRaises(ValueError):
                    self.validate()
                self.record['identity'][key] = original

    def test_partial_smoke_cannot_claim_full_behavior(self):
        self.record['criteria'] = ['actual-tap']
        self.record['coverage_review']['criteria'] = ['actual-tap']
        self.reviews[0]['criteria'] = ['actual-tap']
        partial = self.validate()
        with self.assertRaisesRegex(ValueError, 'coverage is incomplete'):
            gate.require_complete_case(self.required, [partial])

    def test_separate_verified_cases_can_complete_coverage_without_repeating(self):
        gate.require_complete_case(self.required, [dict(criteria=['actual-tap']), dict(criteria=['visual-layout'])])

    def test_missing_visual_review_rejected(self):
        self.reviews = []
        with self.assertRaisesRegex(ValueError, 'visual review missing'):
            self.validate()

    def test_changed_screenshot_rejected(self):
        self.files['shot.png'] += b'changed'
        with self.assertRaisesRegex(ValueError, 'content hash'):
            self.validate()

    def test_wrong_language_rejected(self):
        self.record['identity']['app_language'] = 'he'
        with self.assertRaisesRegex(ValueError, 'language differs'):
            self.validate()

    def test_os27_pair_selection_rejects_duo_only_and_os26(self):
        spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('preflight.py'))
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        inventory = dict(runtimes=[dict(name='iOS 27.1', version='27.1', isAvailable=True,
                                       supportedDeviceTypes=['duo'])],
                         devicetypes=[dict(name='iPhone Duo', identifier='duo'), dict(name='iPad Pro', identifier='ipad')])
        with self.assertRaisesRegex(RuntimeError, 'BOTH'):
            preflight.select_pairs(inventory)
        inventory['runtimes'][0].update(name='iOS 26.2', version='26.2', supportedDeviceTypes=[])
        with self.assertRaisesRegex(RuntimeError, 'BOTH'):
            preflight.select_pairs(inventory)

    def test_all_testflight_workflows_require_gate(self):
        import yaml
        root = Path(__file__).resolve().parents[2]
        for name in ['branch_build.yaml', 'dev_build.yaml', 'release_build.yaml']:
            with self.subTest(workflow=name):
                workflow = yaml.safe_load((root / '.github/workflows' / name).read_text(encoding='utf8'))
                self.assertEqual(workflow['jobs']['main']['needs'], 'ui27-acceptance-gate')
                self.assertNotIn('if', workflow['jobs']['main'])
                self.assertEqual(workflow['jobs']['ui27-acceptance-gate']['uses'], './.github/workflows/pinkha-ui27-release-gate.yml')

    def test_changed_proof_harness_blob_invalidates_old_case_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            paths = [root / 'Tools/PinkhaSimulatorGate' / name for name in [
                'run_ui27.py', 'validate_release.py', 'required-coverage.json']]
            paths[0].parent.mkdir(parents=True)
            for path in paths:
                path.write_text('original proof dependency')
            def commit():
                subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
                subprocess.run(['git', '-C', str(root), '-c', 'user.name=Gate Control',
                    '-c', 'user.email=gate-control@example.invalid', 'commit', '-qm', 'control'], check=True)
            commit()
            for path in paths:
                with self.subTest(proof_input=path.name):
                    self.record['candidate_input_hashes'] = gate.source_inputs(root)
                    path.write_text('changed proof dependency')
                    commit()
                    self.candidate['hashes'] = gate.source_inputs(root)
                    with self.assertRaisesRegex(ValueError, 'inputs are stale'):
                        self.validate()

    def matrix_case(self, case_id):
        matrix = json.loads(Path(__file__).with_name('required-coverage.json').read_text())
        return next(case for case in matrix['cases'] if case['id'] == case_id)

    def test_phone_cannot_supply_or_waive_ipad_window_transition(self):
        case = self.matrix_case('UI10')
        phone = gate.configuration_requirements(case, 'iphone-en-portrait-os27')
        ipad = gate.configuration_requirements(case, 'ipad-he-compact-os27')
        self.assertNotIn('actual-ipad-window-transition', phone['criteria'])
        self.assertIn('actual-ipad-window-transition', ipad['criteria'])
        with self.assertRaisesRegex(ValueError, 'coverage is incomplete'):
            gate.require_complete_case(ipad, [dict(criteria=phone['criteria'])])

    def test_phone_still_requires_its_own_compact_controls(self):
        phone = gate.configuration_requirements(self.matrix_case('UI10'), 'iphone-en-portrait-os27')
        with self.assertRaisesRegex(ValueError, 'compact-controls-usable'):
            gate.require_complete_case(phone, [dict(criteria=['orientation', 'selection-presentation-retained'])])

    def test_light_and_dark_accessibility_require_distinct_actual_configurations(self):
        case = self.matrix_case('UI09')
        light = gate.configuration_requirements(case, 'iphone-he-portrait-os27')
        dark = gate.configuration_requirements(case, 'ipad-he-landscape-dark-large-os27')
        self.assertIn('light-normal-type', light['criteria'])
        self.assertNotIn('dark-accessibility-type', light['criteria'])
        self.assertIn('dark-accessibility-type', dark['criteria'])


if __name__ == '__main__':
    unittest.main()
