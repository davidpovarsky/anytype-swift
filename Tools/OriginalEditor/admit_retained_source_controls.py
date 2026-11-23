"""Admit historical evidence and execute only affected complete-source boundaries.

The original 245 results remain edce/450413 results. Only the listed project,
package-admission, driver, public-surface and complete-source controls execute.
The seven unchanged pure shared-symbol controls retain their real 5e0 result. This never
replays the historical whole suite or grants Apple build/runtime credit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unittest

from framework_profile import blob, git, sha256, source_observation

PACKET = 'docs/pinkha/torah-integration/evidence/original-editor-install-name-20261122'
ORIGINAL_SHA = 'edce5b975b173059522f90adb71271fb95adf963'
ORIGINAL_RUN = '45041382512'
ADDED_CURRENT_IDS = (
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_complete_original_source_and_facades_are_bound_without_native_credit',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_different_product_source_cannot_reuse_complete_continuation',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_missing_account_facade_cannot_hide_behind_matching_profile',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_missing_original_source_cannot_hide_behind_count_metadata',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_original_resources_cannot_change_with_matching_candidate_hash',
    'test_framework.OriginalProjectPreservation.test_duplicate_facade_compiler_input_cannot_replace_missing_import',
    'test_framework.OriginalProjectPreservation.test_new_import_facade_must_reach_actual_compiler_phase',
    'test_framework.OriginalProjectPreservation.test_original_asset_constants_compiler_input_remains_required',
    'test_framework_flow.OriginalDriverFlowControls.test_strict_resolver_failure_cannot_reach_original_build_or_consumer',
    'test_host_framework_contract.HostFrameworkContractControls.test_account_identity_presentation_import_history_and_attempt_have_no_public_constructor',
    'test_host_framework_contract.HostFrameworkContractControls.test_every_account_and_import_public_boundary_is_required',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_controller_afterimage_cannot_reuse_reviewed_delta',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_shared_symbol_implementation_requires_new_controls',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_source_membership_requires_explicit_reviewed_delta',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_explicit_complete_continuation_retains_only_historical_credit',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_foreign_complete_source_cannot_inherit_historical_credit',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_incomplete_recorded_shared_results_cannot_be_retained',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_seven_actual_unchanged_symbol_controls_retain_only_their_source_credit',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_actual_stderr_help_is_admitted_with_empty_stdout',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_missing_output_option_still_rejected',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_oversized_help_is_rejected',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_stdout_help_remains_supported',
)
AFFECTED_IDS = (
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_complete_original_source_and_facades_are_bound_without_native_credit',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_different_product_source_cannot_reuse_complete_continuation',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_missing_account_facade_cannot_hide_behind_matching_profile',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_missing_original_source_cannot_hide_behind_count_metadata',
    'test_complete_source_continuation.CompleteSourceContinuationControls.test_original_resources_cannot_change_with_matching_candidate_hash',
    'test_framework.OriginalProjectPreservation.test_any_additional_original_source_exclusion_is_rejected',
    'test_framework.OriginalProjectPreservation.test_changed_original_app_target_is_rejected_beyond_candidate_hash',
    'test_framework.OriginalProjectPreservation.test_changed_original_compilation_setting_is_rejected',
    'test_framework.OriginalProjectPreservation.test_duplicate_facade_compiler_input_cannot_replace_missing_import',
    'test_framework.OriginalProjectPreservation.test_entrypoint_exception_cannot_target_the_original_app',
    'test_framework.OriginalProjectPreservation.test_framework_cannot_be_an_application_product',
    'test_framework.OriginalProjectPreservation.test_framework_cannot_depend_on_the_original_app_or_test_binary',
    'test_framework.OriginalProjectPreservation.test_framework_has_no_original_app_boot_scripts_or_extensions',
    'test_framework.OriginalProjectPreservation.test_genuine_additive_target_preserves_all_original_app_objects',
    'test_framework.OriginalProjectPreservation.test_new_import_facade_must_reach_actual_compiler_phase',
    'test_framework.OriginalProjectPreservation.test_new_target_cannot_replace_real_source_groups',
    'test_framework.OriginalProjectPreservation.test_new_target_cannot_substitute_the_original_package_product',
    'test_framework.OriginalProjectPreservation.test_original_asset_constants_compiler_input_remains_required',
    'test_framework.OriginalProjectPreservation.test_original_baseline_snapshot_is_bound_to_its_git_blob',
    'test_framework.OriginalProjectPreservation.test_original_heart_installer_changes_only_one_new_branch_choice',
    'test_framework.OriginalProjectPreservation.test_original_project_does_not_already_claim_the_new_framework',
    'test_framework_flow.OriginalDriverFlowControls.test_boot_command_failure_keeps_build_evidence_but_never_runs_bootstatus_or_install',
    'test_framework_flow.OriginalDriverFlowControls.test_build_graph_consumer_and_signature_complete_before_original_boot_pair',
    'test_framework_flow.OriginalDriverFlowControls.test_consumer_compile_failure_cannot_boot_or_install',
    'test_framework_flow.OriginalDriverFlowControls.test_different_embedded_product_cannot_reach_boot_or_install',
    'test_framework_flow.OriginalDriverFlowControls.test_multiple_notices_preserve_exact_contents_and_consumer_destination',
    'test_framework_flow.OriginalDriverFlowControls.test_one_notice_preserves_selected_simulator_for_both_original_build_commands',
    'test_framework_flow.OriginalDriverFlowControls.test_original_public_surface_tool_failure_cannot_boot_or_install',
    'test_framework_flow.OriginalDriverFlowControls.test_same_180_second_boot_timeout_retains_partial_builds_without_runtime_credit',
    'test_framework_flow.OriginalDriverFlowControls.test_strict_resolver_failure_cannot_reach_original_build_or_consumer',
    'test_host_framework_contract.HostFrameworkContractControls.test_account_identity_presentation_import_history_and_attempt_have_no_public_constructor',
    'test_host_framework_contract.HostFrameworkContractControls.test_all_reviewed_public_and_spi_paths_are_required_without_ui_credit',
    'test_host_framework_contract.HostFrameworkContractControls.test_different_shared_package_pin_rejected_even_with_updated_project_hash',
    'test_host_framework_contract.HostFrameworkContractControls.test_every_account_and_import_public_boundary_is_required',
    'test_host_framework_contract.HostFrameworkContractControls.test_malformed_spi_marker_does_not_grant_qualification_scope',
    'test_host_framework_contract.HostFrameworkContractControls.test_missing_real_capture_entrypoint_rejects_inspection_only_surface',
    'test_host_framework_contract.HostFrameworkContractControls.test_new_resume_context_fields_and_operations_cannot_be_missing',
    'test_host_framework_contract.HostFrameworkContractControls.test_public_raw_runtime_helper_is_not_the_qualified_spi',
    'test_host_framework_contract.HostFrameworkContractControls.test_public_unowned_host_constructor_is_rejected',
    'test_host_framework_contract.HostFrameworkContractControls.test_qualification_declarations_require_actual_spi_scope',
    'test_host_framework_contract.HostFrameworkContractControls.test_regular_host_declarations_cannot_be_hidden_as_spi',
    'test_host_framework_contract.HostFrameworkContractControls.test_returned_process_receipt_cannot_be_publicly_constructed',
    'test_host_framework_contract.HostFrameworkContractControls.test_same_spelling_from_a_foreign_source_is_not_a_host_capability',
    'test_host_framework_contract.HostFrameworkContractControls.test_symbol_graph_emission_cannot_spill_into_original_application',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_controller_afterimage_cannot_reuse_reviewed_delta',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_shared_symbol_implementation_requires_new_controls',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_changed_source_membership_requires_explicit_reviewed_delta',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_explicit_complete_continuation_retains_only_historical_credit',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_foreign_complete_source_cannot_inherit_historical_credit',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_incomplete_recorded_shared_results_cannot_be_retained',
    'test_retained_complete_source.RetainedCompleteSourceControls.test_seven_actual_unchanged_symbol_controls_retain_only_their_source_credit',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_actual_stderr_help_is_admitted_with_empty_stdout',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_missing_output_option_still_rejected',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_oversized_help_is_rejected',
    'test_signed_consumer_continuation.LaunchHelpStreams.test_stdout_help_remains_supported',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_committed(root, relative, expected=None):
    require(isinstance(relative, str) and relative.startswith(PACKET + '/')
            and '..' not in Path(relative).parts, 'Unreviewed retained-evidence input path')
    path = root / relative
    require(path.is_file() and path.resolve(strict=True) == path and path.stat().st_size <= 4 * 1024 * 1024,
            'Missing, aliased or oversized retained-evidence input')
    raw = path.read_bytes()
    actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob': blob(raw)}
    require(actual['git_blob'] == git(root, 'rev-parse', 'HEAD:' + relative),
            'Retained-evidence bytes differ from the current Git input')
    if expected is not None:
        require(actual == expected, 'Retained-evidence bytes differ from the reviewed source packet')
    return json.loads(raw), actual


def validate_retained(plan, historical, original, current, catalog):
    require(plan.get('schema') == 1 and plan.get('original_source_sha') == ORIGINAL_SHA
            and plan.get('original_run_id') == ORIGINAL_RUN and plan.get('original_run_attempt') == '1',
            'Unreviewed historical source producer')
    require(original.get('head_sha') == ORIGINAL_SHA and original.get('run_id') == ORIGINAL_RUN
            and original.get('run_attempt') == '1' and original.get('schema') == 1,
            'Retained source inventory has a different original producer')
    expected = list(catalog)
    require(len(expected) == len(set(expected)) == 245 and expected == sorted(expected),
            'Original exact 245 identity catalog differs')
    require(historical.get('schema') == 1 and historical.get('status') == 'PASS_SOURCE_CONTROLS_245'
            and historical.get('phase') == 'COMPLETE' and historical.get('expected_count') == 245
            and historical.get('tests_run') == 245, 'Original source-controls result did not complete successfully')
    for key in ['expected_ids', 'discovered_ids', 'started_ids', 'passed_ids']:
        actual = historical.get(key)
        require(isinstance(actual, list) and len(actual) == len(set(actual)) == 245
                and sorted(actual) == expected, 'Original source-control identity set differs: ' + key)
    require(all(historical.get(key) == [] for key in
                ['errors', 'failures', 'skipped', 'expected_failures', 'unexpected_successes']),
            'Original source-controls result contains a failure/skip')
    require(plan.get('current_affected_ids') == list(AFFECTED_IDS)
            and plan.get('current_added_ids') == list(ADDED_CURRENT_IDS)
            and not set(ADDED_CURRENT_IDS) & set(expected)
            and set(AFFECTED_IDS) <= set(expected) | set(ADDED_CURRENT_IDS),
            'Current affected selection differs')
    product_keys = {'original_trees', 'source_files', 'original_swift_sources',
                    'framework_facade_sources', 'public_host_contract_sha256'}
    product_changes = plan.get('reviewed_product_source_changes', {})
    require(set(product_changes) == product_keys
            and plan.get('complete_product_source_sha') == '4fd99f19b0ec361ba84ac4b2822cae10c6818f99'
            and current.get('reviewed_complete_source_sha') == plan['complete_product_source_sha'],
            'Complete reviewed source continuation is missing')
    for key, change in product_changes.items():
        require(set(change) == {'before', 'after', 'scope'} and change['before'] == original.get(key)
                and change['after'] == current.get(key)
                and isinstance(change['scope'], str) and change['scope'],
                'Complete source continuation differs from its explicit reviewed delta: ' + key)
    require(current.get('original_swift_sources') == 2256
            and len(current.get('framework_facade_sources', [])) == 15,
            'Complete reviewed Swift/facade source count differs')
    expected_inputs = dict(original['source_inputs'])
    changes = plan.get('reviewed_source_input_changes')
    require(isinstance(changes, dict) and changes, 'No explicit reviewed source delta')
    for path, change in changes.items():
        require(set(change) == {'before', 'after', 'scope'} and change['before'] == expected_inputs.get(path)
                and isinstance(change['scope'], str) and change['scope'],
                'Reviewed source preimage differs: ' + path)
        after = change['after']
        require(isinstance(after, dict) and set(after) == {'bytes', 'sha256', 'git_blob'}
                and type(after['bytes']) is int and after['bytes'] > 0,
                'Invalid reviewed source afterimage: ' + path)
        expected_inputs[path] = after
    require(current['source_inputs'] == expected_inputs,
            'Current source inputs differ from original inputs plus the exact reviewed delta')
    return {'original_source_sha': ORIGINAL_SHA, 'original_run_id': ORIGINAL_RUN, 'original_run_attempt': '1',
            'original_count': 245, 'historical_only': True, 'whole_suite_replayed': False,
            'reviewed_complete_source_sha': current['reviewed_complete_source_sha'],
            'changed_product_properties': sorted(product_changes),
            'unchanged_old_source_input_count': len(set(original['source_inputs']) - set(changes)),
            'reviewed_changed_or_added_source_inputs': sorted(changes),
            'current_affected_ids': list(AFFECTED_IDS),
            'scope': 'Historical 245 results retain their original producer. Only listed current cases execute below.'}


def validate_shared_retained(plan, result, current):
    expected = plan['retained_shared_source_controls']
    require(result.get('status') == 'PASS_LOCAL_AFFECTED_33'
            and result.get('source_sha') == expected['source_sha'] == '5e0b51f951bfb274e1a7d60614e4b34ad47c7348'
            and result.get('source_tree') == 'fb9dcf32b782b5b6ba7c6bc6e2170498c3b938b6'
            and result.get('tests_run') == 33 and result.get('source_after_unchanged') is True
            and result.get('native_qualified') is False and result.get('native_builds') == 0,
            'Recorded shared-source controls did not pass on their actual immutable source')
    for key in ['expected_ids', 'started_ids', 'passed_ids']:
        require(isinstance(result.get(key), list) and len(set(result[key])) == len(result[key]) == 33
                and sorted(result[key]) == sorted(result['expected_ids']),
                'Recorded shared-source test identity set differs: ' + key)
    require(all(result.get(key) == [] for key in ['errors', 'failures', 'skipped']),
            'Recorded shared-source controls contain a failure or skip')
    require(len(expected['retained_ids']) == 7
            and set(expected['retained_ids']) <= set(result['passed_ids'])
            and all(i.startswith('SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.')
                    for i in expected['retained_ids']),
            'Retained pure shared-symbol controls differ')
    require(set(expected['unchanged_input_files']) == {
                'Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py',
                'Tools/OriginalEditor/SharedRuntime/test_shared_runtime_ownership.py'}
            and all(current['source_inputs'].get(path) == identity
                    for path, identity in expected['unchanged_input_files'].items()),
            'Retained shared-symbol implementation or control bytes changed')
    return {'source_sha': result['source_sha'], 'source_tree': result['source_tree'],
            'retained_ids': expected['retained_ids'], 'replayed': False, 'native_qualified': False}


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            require(isinstance(item, unittest.TestCase), 'Unexpected affected-test selection object')
            yield item


class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids, self.passed_ids = [], []

    def startTest(self, test):
        self.started_ids.append(test.id())
        print('START_CURRENT_AFFECTED ' + test.id(), flush=True)
        super().startTest(test)

    def addSuccess(self, test):
        self.passed_ids.append(test.id())
        print('PASS_CURRENT_AFFECTED ' + test.id(), flush=True)
        super().addSuccess(test)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    root, evidence = args.root.resolve(), args.evidence.resolve()
    require(evidence.is_relative_to(root / 'build') and evidence.is_dir(), 'Unowned source-admission evidence path')
    receipt = {'schema': 1, 'status': 'FAIL', 'phase': 'RETAINED_SOURCE_ADMISSION',
               'whole_historical_suite_replayed': False, 'current_tests_run': 0,
               'scope': 'Historical source evidence plus selected current Python orchestration controls; no Apple/runtime credit'}
    code = 1
    try:
        current = source_observation(root)
        require(json.loads((evidence / 'source-before.json').read_bytes()) == current,
                'Current source changed after producer admission')
        plan, plan_identity = read_committed(root, PACKET + '/admission/INPUTS.json')
        historical, historical_identity = read_committed(root, PACKET + '/admission/original-source-controls-result.json',
                                                       plan['retained_controls'])
        original, original_identity = read_committed(root, PACKET + '/admission/original-source-before.json',
                                                   plan['retained_source_inventory'])
        original_review, review_identity = read_committed(root, PACKET + '/admission/ROOT_ORIGINAL_EVIDENCE_REVIEW.json',
                                                        plan['original_root_evidence_review'])
        require(original_review.get('run') == int(ORIGINAL_RUN) and original_review.get('source') == ORIGINAL_SHA
                and original_review.get('source_controls_pass') == 245
                and original_review.get('public_spi_requirements_pass') == 38
                and original_review.get('qualified_sdk') is False,
                'Original retained phase review differs; the failed runtime must remain unqualified')
        from run_source_controls import EXPECTED_IDS
        retained = validate_retained(plan, historical, original, current, EXPECTED_IDS)
        shared_controls, shared_identity = read_committed(
            root, PACKET + '/admission/shared-source-controls-5e0b51f951.json',
            plan['retained_shared_source_controls']['receipt_identity'])
        retained_shared = validate_shared_retained(plan, shared_controls, current)
        receipt.update(current_source_sha=current['head_sha'], current_run_id=current['run_id'],
                       current_run_attempt=current['run_attempt'], retained=retained,
                       admission_inputs=plan_identity, original_controls=historical_identity,
                       retained_shared_controls=retained_shared, retained_shared_receipt=shared_identity,
                       original_source_inventory=original_identity, original_phase_review=review_identity,
                       historical_public_spi={'source_sha': ORIGINAL_SHA, 'run_id': ORIGINAL_RUN,
                                              'requirements': 38, 'historical_only': True},
                       phase='CURRENT_AFFECTED_EXECUTION')
        suite = unittest.defaultTestLoader.loadTestsFromNames(list(AFFECTED_IDS))
        selected = sorted(test.id() for test in cases(suite))
        require(selected == list(AFFECTED_IDS), 'Actual current affected selection differs')
        result = unittest.TextTestRunner(verbosity=2, resultclass=ObservedResult).run(suite)
        receipt.update(current_tests_run=result.testsRun, current_started_ids=result.started_ids,
                       current_passed_ids=result.passed_ids,
                       current_failures=[{'id': test.id(), 'traceback': trace} for test, trace in result.failures],
                       current_errors=[{'id': test.id(), 'traceback': trace} for test, trace in result.errors],
                       current_skipped=[{'id': test.id(), 'reason': why} for test, why in result.skipped],
                       current_expected_failures=[test.id() for test, _ in result.expectedFailures],
                       current_unexpected_successes=[test.id() for test in result.unexpectedSuccesses])
        require(result.testsRun == len(AFFECTED_IDS) and sorted(result.started_ids) == list(AFFECTED_IDS)
                and sorted(result.passed_ids) == list(AFFECTED_IDS) and result.wasSuccessful()
                and not result.failures and not result.errors and not result.skipped
                and not result.expectedFailures and not result.unexpectedSuccesses,
                'The selected current affected controls did not all pass without skips')
        require(source_observation(root) == current, 'Source changed during affected controls')
        receipt.update(status='RETAINED_ORIGINAL_245_AND_CURRENT_COMPLETE_SOURCE_PASS', phase='COMPLETE',
                       current_selected_count=len(AFFECTED_IDS))
        code = 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
    finally:
        (evidence / 'retained-source-controls-result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
