"""Adversarial controller controls, not Apple or constructor-method execution."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import original_document_constructor_profile as profile
import original_editor_profile as original
import run_host_tests as host
import run_original_document_constructor_controls as controls

APP = Path(__file__).resolve().parents[2]

class ConstructorProfileControls(unittest.TestCase):
    def setUp(self):
        self.data = profile.manifest()
        self.old = {suite + '/' + name for suite, item in self.data['original_suites'].items()
                    for name in item['methods']}
        self.new = {profile.SUITE + '/' + name for name in self.data['constructor_suite']['methods']}
        self.expected = self.old | self.new
        self.tree = {'testNodes': [
            {'nodeType': 'Test Case', 'nodeIdentifier': name + '()', 'result': 'Passed',
             'children': [{'nodeType': 'Test Case Run', 'result': 'Passed'}]}
            for name in sorted(self.expected)]}
        self.summary = {'totalTestCount': 49, 'passedTests': 49, 'failedTests': 0, 'skippedTests': 0,
            'devicesAndConfigurations': [{'device': {'deviceId': 'owned-ipad', 'osVersion': '27.0',
                'osBuildNumber': '24A-SYNTHETIC-CONTROL', 'architecture': 'arm64', 'modelName': 'iPad Pro'}}]}

    def validate(self, summary=None, tree=None):
        return host.validate_results(self.summary if summary is None else summary,
            self.tree if tree is None else tree, self.expected, 'owned-ipad', host.HostTestProfile.ORIGINAL_CONSTRUCTORS)

    def test_actual_git_sources_bind_forty_nine_methods_in_eight_files(self):
        methods, inputs = profile.expected_methods(APP)
        self.assertEqual(methods, self.expected)
        self.assertEqual(len(inputs), 8)
        self.assertEqual(host.expected_methods(APP, host.HostTestProfile.ORIGINAL_CONSTRUCTORS), (methods, inputs))

    def test_original_inventory_validator_and_heart_remain_exact(self):
        old = original.manifest()
        self.assertEqual(self.data['original_suites'], old['suites'])
        self.assertEqual(self.data['heart'], old['heart'])
        self.assertEqual(len(self.old), 43)
        self.assertEqual(len(self.new), 6)
        self.assertEqual(set(profile.suite_counts()), set(original.suite_counts()) | {profile.SUITE})

    def test_new_dispatch_keeps_original_profile_selection_and_names(self):
        self.assertEqual(host.HostTestProfile.ORIGINAL_EDITOR.suites, original.suite_counts())
        self.assertEqual(host.HostTestProfile.ORIGINAL_EDITOR.result_prefix, 'original-editor')
        self.assertEqual(host.HostTestProfile.ORIGINAL_EDITOR.pass_status, 'ORIGINAL_EDITOR_COMPONENT_PASS')
        self.assertEqual(host.HostTestProfile.ORIGINAL_CONSTRUCTORS.result_prefix, 'original-constructors')
        self.assertEqual(host.HostTestProfile.ORIGINAL_CONSTRUCTORS.pass_status, 'ORIGINAL_CONSTRUCTORS_COMPONENT_PASS')
        self.assertEqual(sum(host.HostTestProfile.ORIGINAL_CONSTRUCTORS.suites.values()), 49)

    def test_complete_bound_synthetic_result_is_accepted_without_mutation(self):
        before = copy.deepcopy(self.tree)
        actual = self.validate()
        self.assertEqual(actual['actual_method_count'], 49)
        self.assertEqual(actual['original43']['actual_method_count'], 43)
        self.assertEqual(actual['actual_constructor_methods'], sorted(self.new))
        self.assertEqual(self.tree, before)

    def test_exact_original_nodes_are_forwarded_to_unchanged_validator(self):
        with patch.object(original, 'validate_execution', wraps=original.validate_execution) as validate:
            self.validate()
        validate.assert_called_once()
        passed_tree, names = validate.call_args.args
        self.assertEqual(names, self.old)
        actual_old = [x for x in self.tree['testNodes'] if x['nodeIdentifier'][:-2] in self.old]
        self.assertEqual(passed_tree['testNodes'], actual_old)
        self.assertTrue(all(any(x is y for y in actual_old) for x in passed_tree['testNodes']))

    def test_missing_duplicate_extra_and_foreign_nodes_are_rejected(self):
        variants = []
        tree = copy.deepcopy(self.tree); tree['testNodes'].pop(); variants.append(tree)
        tree = copy.deepcopy(self.tree); tree['testNodes'][-1] = copy.deepcopy(tree['testNodes'][0]); variants.append(tree)
        tree = copy.deepcopy(self.tree); tree['testNodes'].append(copy.deepcopy(tree['testNodes'][0])); variants.append(tree)
        tree = copy.deepcopy(self.tree); tree['testNodes'][-1]['nodeIdentifier'] = 'Other/testUnreviewed()'; variants.append(tree)
        for tree in variants:
            with self.subTest(tree=tree), self.assertRaises(ValueError):
                self.validate(tree=tree)

    def test_new_six_cannot_replace_original_forty_three(self):
        tree = {'testNodes': [x for x in self.tree['testNodes'] if x['nodeIdentifier'][:-2] in self.new]}
        with self.assertRaises(ValueError):
            profile.validate_execution(tree, self.new)

    def test_failed_skipped_and_missing_results_in_each_scope_fail(self):
        for names in [self.old, self.new]:
            index = next(i for i, x in enumerate(self.tree['testNodes']) if x['nodeIdentifier'][:-2] in names)
            for status in ['Failed', 'Skipped', None, True]:
                tree = copy.deepcopy(self.tree); tree['testNodes'][index]['result'] = status
                with self.subTest(scope=names is self.new, status=status), self.assertRaises(ValueError):
                    self.validate(tree=tree)

    def test_descendant_failures_arguments_and_unknown_shapes_remain_rejected(self):
        for names in [self.old, self.new]:
            index = next(i for i, x in enumerate(self.tree['testNodes']) if x['nodeIdentifier'][:-2] in names)
            for child in [None, {'nodeType': 'Test Case Run', 'result': 'Skipped'},
                          {'nodeType': 'Test Case Run', 'result': 'Failed'},
                          {'nodeType': 'Arguments', 'result': 'Passed'},
                          {'nodeType': 'Unknown', 'result': 'Passed'},
                          {'nodeType': 'Repetition', 'result': 'Passed', 'children': 'malformed'}]:
                tree = copy.deepcopy(self.tree); tree['testNodes'][index]['children'] = [child]
                with self.subTest(child=child), self.assertRaises(ValueError):
                    self.validate(tree=tree)

    def test_summary_boolean_skip_failure_and_wrong_totals_fail(self):
        for key, value in [('totalTestCount', True), ('totalTestCount', 48), ('totalTestCount', 50),
                           ('passedTests', 48), ('failedTests', 1), ('skippedTests', 1)]:
            summary = copy.deepcopy(self.summary); summary[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.validate(summary=summary)

    def test_actual_destination_and_platform_guards_are_unchanged(self):
        for key, value in [('deviceId', 'foreign'), ('osVersion', '26.0'),
                           ('architecture', 'x86_64'), ('modelName', 'iPhone')]:
            summary = copy.deepcopy(self.summary); summary['devicesAndConfigurations'][0]['device'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(summary=summary)

    def test_constructor_identity_requires_exact_head_branch_run_and_positive_attempt(self):
        good = ['a' * 40, 'a' * 40, profile.BRANCH, profile.BRANCH, '123', '2']
        profile.require_identity(*good)
        for index, value in [(0, 'b' * 40), (1, ''), (2, original.BRANCH), (3, 'main'),
                              (4, '0'), (4, ''), (5, '0'), (5, '-1'), (5, '')]:
            args = list(good); args[index] = value
            with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                profile.require_identity(*args)

    def test_push_authority_rejects_other_event_repository_ref_or_workflow(self):
        good = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REPOSITORY': profile.REPOSITORY,
                'GITHUB_REF': 'refs/heads/' + profile.BRANCH,
                'GITHUB_WORKFLOW_REF': profile.REPOSITORY + '/' + profile.WORKFLOW + '@refs/heads/' + profile.BRANCH}
        profile.require_workflow_environment(good)
        for key, value in [('GITHUB_EVENT_NAME', 'pull_request'), ('GITHUB_EVENT_NAME', 'workflow_dispatch'),
                           ('GITHUB_REPOSITORY', 'foreign/repo'), ('GITHUB_REF', 'refs/heads/main'),
                           ('GITHUB_WORKFLOW_REF', profile.REPOSITORY + '/other.yml@refs/heads/' + profile.BRANCH)]:
            changed = dict(good); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                profile.require_workflow_environment(changed)

    def test_constructor_declarations_require_real_actor_class_unique_names_and_no_arguments(self):
        item = self.data['constructor_suite']; text = (APP / item['path']).read_text()
        first = item['methods'][0]
        self.assertEqual(profile.validate_constructor_declarations(text, item['methods']), self.new)
        variants = [text.replace('@MainActor', '', 1), text.replace('XCTestCase', 'Other', 1),
                    text.replace('func ' + first + '(', 'func renamed(', 1),
                    text.replace('func ' + first + '()', 'func ' + first + '(value: Bool)', 1),
                    text + '\nfunc ' + first + '() {}\n']
        for changed in variants:
            with self.subTest(changed=changed[:40]), self.assertRaises(ValueError):
                profile.validate_constructor_declarations(changed, item['methods'])

    def test_wrong_application_tree_is_rejected_before_source_acceptance(self):
        actual = profile.git
        for path in self.data['application_trees']:
            def altered(root, *args):
                return '0' * 40 if args == ('rev-parse', 'HEAD:' + path) else actual(root, *args)
            with self.subTest(path=path), patch.object(profile, 'git', side_effect=altered), self.assertRaises(ValueError):
                profile.expected_methods(APP)

    def test_constructor_working_bytes_are_bound_to_reviewed_input(self):
        actual = profile.canonical
        for path in self.data['constructor_sources']:
            def altered(value):
                raw = actual(value)
                return raw + b'\n// CONTROL TAMPER\n' if value == APP / path else raw
            with self.subTest(path=path), patch.object(profile, 'canonical', side_effect=altered), self.assertRaises(ValueError):
                profile.expected_methods(APP)

    def test_original_test_working_bytes_are_still_bound(self):
        actual = profile.canonical
        path = next(iter(self.data['original_suites'].values()))['path']
        with patch.object(profile, 'canonical', side_effect=lambda p: actual(p) + (b'\n' if p == APP / path else b'')):
            with self.assertRaises(ValueError):
                profile.expected_methods(APP)

    def test_profile_runtime_must_match_actual_git_checkout(self):
        actual = profile.subprocess.check_output
        target = 'HEAD:Tools/Hanlin/original_document_constructor_profile.py'
        def altered(command, *args, **kwargs):
            raw = actual(command, *args, **kwargs)
            return raw + b'\n# CONTROL TAMPER\n' if command[-1] == target else raw
        with patch.object(profile.subprocess, 'check_output', side_effect=altered), self.assertRaises(ValueError):
            profile.expected_methods(APP)

    def test_imported_profile_from_another_directory_is_rejected(self):
        with patch.object(profile, '__file__', str(APP / 'foreign/profile.py')), self.assertRaises(ValueError):
            profile.expected_methods(APP)

    def test_original_validator_byte_change_cannot_be_hidden(self):
        actual = profile.canonical
        with patch.object(profile, 'canonical', side_effect=lambda p: actual(p) + (b'\n' if p == Path(original.__file__) else b'')):
            with self.assertRaises(ValueError):
                profile.manifest()

    def test_constructor_namespace_variants_remain_unique(self):
        for suffix in ['', '()']:
            tree = copy.deepcopy(self.tree)
            for node in tree['testNodes']:
                if node['nodeIdentifier'][:-2] in self.new:
                    node['nodeIdentifier'] = 'AnytypeTests/' + node['nodeIdentifier'][:-2] + suffix
            self.assertEqual(self.validate(tree=tree)['actual_method_count'], 49)
        tree = copy.deepcopy(self.tree)
        indexes = [i for i, x in enumerate(tree['testNodes']) if x['nodeIdentifier'][:-2] in self.new]
        tree['testNodes'][indexes[-1]]['nodeIdentifier'] = 'AnytypeTests/' + tree['testNodes'][indexes[0]]['nodeIdentifier']
        with self.assertRaises(ValueError):
            self.validate(tree=tree)

    def test_control_completion_rejects_crash_skip_duplicate_and_partial_output(self):
        names = ['fixture.Controls.testOne', 'fixture.Controls.testTwo']
        text = 'testOne (fixture.Controls.testOne) ... ok\ntestTwo (fixture.Controls.testTwo) ... ok\n\n----------------------------------------------------------------------\nRan 2 tests in 0.01s\n\nOK\n'
        self.assertEqual(controls.exact_success(text, names, 0), names)
        for rc in [-9, -15, 1, 2, 70, 137]:
            with self.subTest(rc=rc), self.assertRaises(ValueError):
                controls.exact_success(text, names, rc)
        for changed in [text.replace(' ... ok', ' ... skipped', 1), text.replace(names[1], names[0]),
                        text.split('Ran 2')[0], text.replace('Ran 2', 'Ran 1'), text.replace('OK\n', 'OK (skipped=1)\n')]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                controls.exact_success(changed, names, 0)

    def test_original_interleaved_command_logs_still_require_final_named_success(self):
        name = 'fixture.Controls.testCommand'
        text = 'testCommand (' + name + ') ... {"command": ["owned child"]}\npartial owned stdout\nok\n\n----------------------------------------------------------------------\nRan 1 tests in 0.01s\n\nOK\n'
        self.assertEqual(controls.exact_success(text, [name], 0), [name])
        for status in ['FAIL', 'ERROR', 'skipped', '']:
            with self.subTest(status=status), self.assertRaises(ValueError):
                controls.exact_success(text.replace('\nok\n', '\n' + status + '\n'), [name], 0)

if __name__ == '__main__':
    unittest.main()
