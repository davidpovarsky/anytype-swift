"""Admit historical source evidence and execute 33 changed source boundaries.

The original 245 results remain edce/450413 results. Only the listed project,
package-admission, driver, and new symbol-ownership controls execute. This never
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
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_cmark_implementation_cannot_move_to_an_unreviewed_image',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_complete_unique_synthetic_definitions_have_no_native_credit',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_duplicate_shared_hanlin_symbols_are_rejected',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_external_consumer_cannot_embed_a_second_promise_class',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_original_editor_cannot_embed_a_second_firebase_class',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_runtime_cannot_omit_an_original_messaging_implementation',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_swift_module_declarations_without_defined_functions_are_insufficient',
    'test_framework_flow.OriginalDriverFlowControls.test_strict_resolver_failure_cannot_reach_original_build_or_consumer',
)
AFFECTED_IDS = (
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_cmark_implementation_cannot_move_to_an_unreviewed_image',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_complete_unique_synthetic_definitions_have_no_native_credit',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_duplicate_shared_hanlin_symbols_are_rejected',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_external_consumer_cannot_embed_a_second_promise_class',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_original_editor_cannot_embed_a_second_firebase_class',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_runtime_cannot_omit_an_original_messaging_implementation',
    'SharedRuntime.test_shared_runtime_ownership.SharedDefinitionControls.test_swift_module_declarations_without_defined_functions_are_insufficient',
    'test_framework.OriginalProjectPreservation.test_any_additional_original_source_exclusion_is_rejected',
    'test_framework.OriginalProjectPreservation.test_changed_original_app_target_is_rejected_beyond_candidate_hash',
    'test_framework.OriginalProjectPreservation.test_changed_original_compilation_setting_is_rejected',
    'test_framework.OriginalProjectPreservation.test_entrypoint_exception_cannot_target_the_original_app',
    'test_framework.OriginalProjectPreservation.test_framework_cannot_be_an_application_product',
    'test_framework.OriginalProjectPreservation.test_framework_cannot_depend_on_the_original_app_or_test_binary',
    'test_framework.OriginalProjectPreservation.test_framework_has_no_original_app_boot_scripts_or_extensions',
    'test_framework.OriginalProjectPreservation.test_genuine_additive_target_preserves_all_original_app_objects',
    'test_framework.OriginalProjectPreservation.test_new_target_cannot_replace_real_source_groups',
    'test_framework.OriginalProjectPreservation.test_new_target_cannot_substitute_the_original_package_product',
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
    'test_host_framework_contract.HostFrameworkContractControls.test_different_shared_package_pin_rejected_even_with_updated_project_hash',
    'test_host_framework_contract.HostFrameworkContractControls.test_symbol_graph_emission_cannot_spill_into_original_application',
    'test_observed_package_simulator_signing.DependencyCheckoutSourceClosureControls.test_unchanged_source_accepts_separate_owned_generated_build_metadata',
    'test_observed_package_simulator_signing.DependencyCheckoutSourceClosureControls.test_untracked_swift_resource_and_ignored_source_are_rejected_without_cleanup',
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
    for key in ['original_trees', 'source_files', 'original_swift_sources',
                'framework_facade_sources', 'public_host_contract_sha256']:
        require(current.get(key) == original.get(key), 'Original product/source membership changed: ' + key)
    require(current.get('original_swift_sources') == 2254
            and len(current.get('framework_facade_sources', [])) == 12,
            'Original Swift/facade source count differs')
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
            'unchanged_old_source_input_count': len(set(original['source_inputs']) - set(changes)),
            'reviewed_changed_or_added_source_inputs': sorted(changes),
            'current_affected_ids': list(AFFECTED_IDS),
            'scope': 'Historical 245 results retain their original producer. Only listed current cases execute below.'}


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
        receipt.update(current_source_sha=current['head_sha'], current_run_id=current['run_id'],
                       current_run_attempt=current['run_attempt'], retained=retained,
                       admission_inputs=plan_identity, original_controls=historical_identity,
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
                'The 33 current affected controls did not all pass without skips')
        require(source_observation(root) == current, 'Source changed during affected controls')
        receipt.update(status='RETAINED_ORIGINAL_245_AND_CURRENT_AFFECTED_33_PASS', phase='COMPLETE')
        code = 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
    finally:
        (evidence / 'retained-source-controls-result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
