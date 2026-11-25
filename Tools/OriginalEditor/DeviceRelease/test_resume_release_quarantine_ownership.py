"""Fail-closed admission controls; no compiler or native UI execution credit."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from resume_release_quarantine_ownership import (
    COMPILER_CONTROL, CONFIGURATION, SOURCE, PHASE, FAILURE,
    admit_terminal, original_arguments, verify_previous_commands)

def valid_receipt():
    return {
        'status': 'FAIL', 'phase': PHASE, 'error_type': 'ValueError', 'error': FAILURE,
        'source_sha': SOURCE, 'control_sha': COMPILER_CONTROL, 'platform': 'iphoneos',
        'configuration': CONFIGURATION, 'owned_command_groups_drained': True,
        'original_framework_build': 'PASS', 'external_consumer_build': 'PASS',
        'native_editor_ui_tests': 0, 'device_runtime': 'NOT_RUN', 'original_app_runtime': 'NOT_RUN',
        'owned_simulator_cleanup': {'status': 'NO_OWNED_SIMULATOR_CREATED'},
        'actual_public_surface': {
            'status': 'ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED',
            'reviewed_host_and_spi_requirements_observed': 270,
            'debug_qualification_requirements_absent': 22,
            'public_host_scope_verified': True, 'qualification_spi_scope_verified': True,
            'debug_qualification_symbols_observed': []}}

class TerminalAdmissionTests(unittest.TestCase):
    def test_exact_mapping_failure_is_admitted(self):
        admit_terminal(valid_receipt())

    def test_success_or_other_failure_cannot_resume(self):
        for key, value in [('status', 'PASS'), ('phase', 'PACKAGING'),
                           ('error_type', 'TimeoutExpired'), ('error', 'Other failure')]:
            with self.subTest(key=key):
                row = valid_receipt(); row[key] = value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_wrong_compiler_source_configuration_platform_refused(self):
        for key, value in [('source_sha', '0' * 40), ('control_sha', '1' * 40),
                           ('platform', 'iphonesimulator'), ('configuration', 'Debug')]:
            with self.subTest(key=key):
                row = valid_receipt(); row[key] = value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_incomplete_builds_or_unresolved_processes_refused(self):
        for key, value in [('original_framework_build', 'NOT_RUN'), ('external_consumer_build', 'FAIL'),
                           ('owned_command_groups_drained', False), ('cleanup_error', 'busy'),
                           ('final_observation_error', 'source changed')]:
            with self.subTest(key=key):
                row = valid_receipt(); row[key] = value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_api_spi_and_absence_requirements_retained(self):
        for key, value in [('reviewed_host_and_spi_requirements_observed', 269),
                           ('debug_qualification_requirements_absent', 21),
                           ('public_host_scope_verified', False), ('qualification_spi_scope_verified', False),
                           ('debug_qualification_symbols_observed', ['_debug'])]:
            with self.subTest(key=key):
                row = valid_receipt(); row['actual_public_surface'][key] = value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_device_or_native_acceptance_cannot_be_borrowed(self):
        for key, value in [('native_editor_ui_tests', 1), ('device_runtime', 'PASS'),
                           ('original_app_runtime', 'PASS'), ('owned_simulator_cleanup', {'status': 'PASS'})]:
            with self.subTest(key=key):
                row = valid_receipt(); row[key] = value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_original_argv_must_be_unique_complete_and_same_team(self):
        values = {
            '--abi-execution': '/a', '--abi-execution-sha256': 'a', '--abi-source-before': '/b',
            '--abi-receipt': '/c', '--abi-sha256': 'c', '--simulator-qualification': '/d',
            '--simulator-qualification-sha256': 'd', '--signing-team-id': 'NA6HPWARQ2'}
        argv = ['run_release.py', *[v for pair in values.items() for v in pair]]
        self.assertEqual(original_arguments({'controller_argv': argv}), values)
        for wrong in [argv + ['--abi-execution', '/e'], argv[:-1], argv[:-2],
                      argv[:-1] + ['FOREIGN123']]:
            with self.assertRaises(RuntimeError):
                original_arguments({'controller_argv': wrong})

class CommandAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        names = ['framework-build', 'external-consumer-build', 'shared-provider-original-loads',
                 'shared-provider-definitions-AnytypeOriginalEditor',
                 'shared-provider-definitions-ProtobufMessages-table',
                 'shared-provider-definitions-ProtobufMessages-exports']
        names += ['command-' + str(i) for i in range(122)]
        for name in names:
            row = {'returncode': 0, 'timed_out': False, 'owned_group_drained': True,
                   'unexpected_children_after_parent_exit': False}
            for stream in ['stdout', 'stderr']:
                raw = (name + stream).encode()
                (self.root / (name + '.' + stream + '.log')).write_bytes(raw)
                row[stream + '_sha256'] = hashlib.sha256(raw).hexdigest()
            (self.root / (name + '.command.json')).write_text(json.dumps(row))
    def tearDown(self):
        self.temp.cleanup()
    def test_exact_complete_clean_commands_admitted(self):
        self.assertEqual(len(verify_previous_commands(self.root)), 128)
    def test_changed_command_output_refused(self):
        (self.root / 'external-consumer-build.stdout.log').write_text('altered')
        with self.assertRaises(RuntimeError): verify_previous_commands(self.root)
    def test_failed_timeout_or_undrained_command_refused(self):
        path = self.root / 'external-consumer-build.command.json'
        original = json.loads(path.read_text())
        for key, value in [('returncode', 65), ('timed_out', True), ('owned_group_drained', False),
                           ('unexpected_children_after_parent_exit', True)]:
            row = copy.deepcopy(original); row[key] = value; path.write_text(json.dumps(row))
            with self.assertRaises(RuntimeError): verify_previous_commands(self.root)
    def test_missing_actual_compiler_receipt_refused(self):
        (self.root / 'framework-build.command.json').unlink()
        with self.assertRaises(RuntimeError): verify_previous_commands(self.root)

if __name__ == '__main__':
    unittest.main()
