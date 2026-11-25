"""Admission regression checks for resuming actual Release evidence."""
import copy
import unittest
from resume_release_ownership import admit_terminal
from release_contract import SOURCE, CONFIGURATION


def candidate():
    return dict(status='FAIL', phase='ACTUAL_RELEASE_SHARED_IMPLEMENTATION_OWNERSHIP',
        error_type='TimeoutExpired', owned_command_groups_drained=True,
        source_sha=SOURCE, configuration=CONFIGURATION, platform='iphonesimulator',
        original_framework_build='PASS', external_consumer_build='PASS',
        owned_simulator_cleanup={'status':'PASS'},
        actual_public_surface=dict(status='ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED',
            reviewed_host_and_spi_requirements_observed=89,
            debug_qualification_requirements_absent=22, public_host_scope_verified=True,
            qualification_spi_scope_verified=True, debug_qualification_symbols_observed=[]),
        verified_runtime_observations=[
            {'language':lang,'status':'ACTUAL_IMPORT_LINK_RESOURCE_RUNTIME_PASS'} for lang in ['en','he']])


class ResumeAdmissionTests(unittest.TestCase):
    def test_accepts_only_completed_prerequisites(self):
        admit_terminal(candidate())

    def test_rejects_undrained_or_non_timeout_or_wrong_phase(self):
        for key,value in [('owned_command_groups_drained',False),('error_type','RuntimeError'),
                          ('phase','ORIGINAL_RELEASE_FRAMEWORK_BUILD'),('status','PASS')]:
            with self.subTest(key=key):
                row=candidate();row[key]=value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_missing_framework_or_consumer(self):
        for key in ['original_framework_build','external_consumer_build']:
            row=candidate();row[key]='NOT_RUN'
            with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_changed_source_or_configuration(self):
        for key in ['source_sha','configuration']:
            row=candidate();row[key]='changed'
            with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_final_source_or_cleanup_errors(self):
        for key in ['final_observation_error','cleanup_error']:
            row=candidate();row[key]='actual failure'
            with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_incomplete_public_api(self):
        for key,value in [('reviewed_host_and_spi_requirements_observed',88),
                          ('debug_qualification_requirements_absent',21),
                          ('debug_qualification_symbols_observed',['unexpectedSPI']),
                          ('public_host_scope_verified',False),
                          ('qualification_spi_scope_verified',False)]:
            with self.subTest(key=key):
                row=candidate();row['actual_public_surface'][key]=value
                with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_missing_duplicate_or_failed_runtime(self):
        row=candidate();row['verified_runtime_observations'].pop()
        with self.assertRaises(RuntimeError): admit_terminal(row)
        row=candidate();row['verified_runtime_observations'][1]['language']='en'
        with self.assertRaises(RuntimeError): admit_terminal(row)
        row=candidate();row['verified_runtime_observations'][1]['status']='FAIL'
        with self.assertRaises(RuntimeError): admit_terminal(row)

    def test_rejects_unknown_platform(self):
        row=candidate();row['platform']='macosx'
        with self.assertRaises(RuntimeError): admit_terminal(row)


if __name__ == '__main__':
    unittest.main()
