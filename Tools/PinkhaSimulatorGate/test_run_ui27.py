"""Selection/evidence controls only; no Xcode or UI execution occurs here."""
import json
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from types import SimpleNamespace
import run_ui27 as runner


class UIExecutionControls(unittest.TestCase):
    def test_only_exact_properties_target_and_method_names_get_longer_ceilings(self):
        expected = {
            'PinkhaNativeDerivedAcceptanceUITests/testNativePropertiesPickerChipsSetMembershipAndRelaunch',
            'PinkhaNativeDerivedAcceptanceUITests/testUniversalPageNoteCustomPropertiesAndMixedSet',
        }
        self.assertEqual(runner.LONG_PROPERTIES_METHODS, expected)
        for method in expected:
            with self.subTest(method=method):
                budget = runner.selection_time_budget('PinkhaStage1AcceptanceUITests', [method])
                self.assertEqual(budget, dict(default_seconds=300, maximum_seconds=900,
                    method_seconds={method: 900}, total_method_seconds=900))
            foreign = [method + '()', method + 'Other', 'OtherSuite/' + method.split('/')[1],
                       method.split('/')[1], 'PinkhaStage1AcceptanceUITests/' + method]
            for name in foreign:
                with self.subTest(foreign=name):
                    self.assertEqual(runner.selection_time_budget('PinkhaStage1AcceptanceUITests', [name])['maximum_seconds'], 300)
            for target in ['AnytypeTests', 'OtherTests', 'PinkhaStage1AcceptanceUITestsOther']:
                with self.subTest(target=target):
                    self.assertEqual(runner.selection_time_budget(target, [method])['maximum_seconds'], 300)

    def test_selection_budget_sums_exact_ceilings_and_preserves_default(self):
        short = 'PinkhaNativeDerivedAcceptanceUITests/testSourceHeaderSelectionAndOverflow'
        methods = [*sorted(runner.LONG_PROPERTIES_METHODS), short]
        budget = runner.selection_time_budget('PinkhaStage1AcceptanceUITests', methods)
        self.assertEqual(budget['default_seconds'], 300)
        self.assertEqual(budget['maximum_seconds'], 900)
        self.assertEqual(budget['method_seconds'][short], 300)
        self.assertEqual(budget['total_method_seconds'], 2100)
        preparation = runner.selection_time_budget('AnytypeTests',
            ['TorahNativeDerivedProductIntegrationTests/originalProductPipeline'])
        self.assertEqual(preparation['total_method_seconds'], 300)
        self.assertEqual(budget['total_method_seconds'] + preparation['total_method_seconds'] + 180, 2580)

    def test_selection_time_budget_rejects_empty_duplicate_or_malformed_inputs(self):
        for names in [[], (), None, 'Suite/test', ['Suite/test', 'Suite/test'], [''], [None], [1], [' Suite/test']]:
            with self.subTest(names=names), self.assertRaises(ValueError):
                runner.selection_time_budget('PinkhaStage1AcceptanceUITests', names)
        for target in ['', None, 1, ' AnytypeTests']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                runner.selection_time_budget(target, ['Suite/test'])

    def test_swift_explicit_allowances_are_only_the_two_reviewed_methods(self):
        source = Path(runner.__file__).resolve().parents[2] / 'PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift'
        text = source.read_text(encoding='utf8')
        declarations = re.findall(r'func (test\w+)\(\) throws \{\s+executionTimeAllowance = (\d+)', text)
        expected = {(name.split('/')[1], '900') for name in runner.LONG_PROPERTIES_METHODS}
        self.assertEqual(set(declarations), expected)
        self.assertEqual(len(declarations), len(expected))
        self.assertEqual(len(re.findall(r'\bexecutionTimeAllowance\s*=', text)), 2)

    def budget_execution(self, selected, *, failed=0, skipped=0, missing=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = root / 'Original.xctestrun'
            configuration.write_bytes(plistlib.dumps(dict(BlueprintName='PinkhaStage1AcceptanceUITests')))
            original = configuration.read_bytes()
            calls = []
            def command(argv, app, evidence, bundle, prefix):
                calls.append(argv)
                count = len(selected) - int(missing)
                (evidence / (prefix + '-summary.json')).write_text(json.dumps(dict(
                    totalTestCount=count, passedTests=count - failed - skipped, failedTests=failed, skippedTests=skipped,
                    devicesAndConfigurations=[dict(device=dict(deviceId='disposable', osVersion='27.0', architecture='arm64'))])))
                cases = [dict(nodeType='Test Case', nodeIdentifier=name + '()',
                    result='Failed' if i < failed else 'Skipped' if i < failed + skipped else 'Passed')
                    for i, name in enumerate(selected[:count])]
                (evidence / (prefix + '-tests.json')).write_text(json.dumps(cases))
            with patch.object(runner, 'run_xctest', side_effect=command):
                result = runner.run_selection(root, configuration, 'PinkhaStage1AcceptanceUITests', 'disposable',
                    selected, {'PINKHA_UI27_SELECTION_SCOPE': 'WAVE15_ACCEPTANCE'}, root / 'fresh', 'budget')
            self.assertEqual(configuration.read_bytes(), original)
            inputs = json.loads((root / 'fresh/selection-inputs.json').read_text())
            self.assertEqual(inputs['time_budget'], result['time_budget'])
            self.assertEqual(inputs['selections'], selected)
            self.assertEqual(len(calls), 1)
            self.assertEqual([v for v in calls[0] if v.startswith('-only-testing:')],
                ['-only-testing:PinkhaStage1AcceptanceUITests/' + name for name in selected])
            return result, calls[0]

    def test_recorded_xcode_budget_changes_only_maximum_for_exact_long_selections(self):
        long = sorted(runner.LONG_PROPERTIES_METHODS)
        short = 'PinkhaNativeDerivedAcceptanceUITests/testSourceHeaderSelectionAndOverflow'
        for methods, maximum, total in [(long + [short], 900, 2100), ([short], 300, 300)]:
            with self.subTest(methods=methods):
                result, argv = self.budget_execution(methods)
                self.assertEqual(result['status'], 'PASS')
                self.assertEqual(argv[argv.index('-default-test-execution-time-allowance') + 1], '300')
                self.assertEqual(argv[argv.index('-maximum-test-execution-time-allowance') + 1], str(maximum))
                self.assertEqual(argv[argv.index('-test-timeouts-enabled') + 1], 'YES')
                self.assertEqual(result['time_budget']['total_method_seconds'], total)

    def test_longer_budget_does_not_accept_failed_skipped_or_missing_methods(self):
        methods = sorted(runner.LONG_PROPERTIES_METHODS)
        for arguments in [dict(failed=1), dict(skipped=1), dict(missing=True)]:
            with self.subTest(arguments=arguments):
                result, _ = self.budget_execution(methods, **arguments)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['time_budget']['maximum_seconds'], 900)

    def test_diagnostic_selection_keeps_default_and_cannot_claim_six_passes_or_release(self):
        devices = dict(iphone=dict(udid='phone'), ipad=dict(udid='pad'))
        full = runner.ui_scope_plan('FULL_SMOKE', devices)
        diagnostic = runner.ui_scope_plan('STARTUP_IPAD_DIAGNOSTIC', devices)
        self.assertEqual(full['selected_methods'], runner.SMOKE)
        self.assertEqual(full['expected_ui_executions'], 6)
        self.assertEqual(diagnostic['selected_methods'], ['testDocumentSourceSearchPresentation'])
        self.assertEqual(diagnostic['expected_ui_executions'], 1)
        self.assertEqual(len(diagnostic['unselected_smoke_pairs']), 5)
        self.assertTrue(all(p['status'] == 'NOT_RUN' for p in diagnostic['unselected_smoke_pairs']))
        self.assertFalse(diagnostic['release_accepted'])
        self.assertFalse(diagnostic['full_matrix_accepted'])
        self.assertEqual(runner.completion_status('STARTUP_IPAD_DIAGNOSTIC', 1),
                         'STARTUP_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING')
        for mode, count in [('STARTUP_IPAD_DIAGNOSTIC', 6), ('FULL_SMOKE', 2), ('UNKNOWN', 2), ('UNKNOWN', None)]:
            with self.assertRaises((RuntimeError, ValueError)):
                runner.completion_status(mode, count)
        with self.assertRaises(ValueError):
            runner.ui_scope_plan('UNKNOWN', devices)
        with self.assertRaises(ValueError):
            runner.ui_scope_plan('STARTUP_IPAD_DIAGNOSTIC', dict(iphone=dict(udid='phone')))

    def test_native_and_startup_diagnostics_are_independent_and_exclude_other_lane(self):
        devices = dict(ipad=dict(udid='pad'))
        startup = runner.ui_scope_plan('STARTUP_IPAD_DIAGNOSTIC', devices)
        self.assertEqual(startup['selected_device_families'], ['ipad'])
        self.assertEqual(startup['expected_native_executions'], 0)
        self.assertEqual(startup['expected_preparation_executions'], 1)
        native = runner.ui_scope_plan('NATIVE_CANCELLATION_DIAGNOSTIC', devices)
        self.assertEqual(native['expected_native_executions'], 1)
        self.assertEqual(native['expected_preparation_executions'], 0)
        self.assertEqual(native['expected_ui_executions'], 0)
        self.assertEqual(native['selected_methods'], [])
        self.assertEqual(len(native['unselected_smoke_pairs']), 6)
        self.assertEqual(runner.completion_status('NATIVE_CANCELLATION_DIAGNOSTIC', 0),
                         'NATIVE_DIAGNOSTIC_COMPLETE_FULL_ACCEPTANCE_PENDING')
        with self.assertRaises(RuntimeError):
            runner.completion_status('STARTUP_IPAD_DIAGNOSTIC', 2)

    def test_execute_dispatches_only_the_independently_selected_lane(self):
        for scope in ['NATIVE_CANCELLATION_DIAGNOSTIC', 'STARTUP_IPAD_DIAGNOSTIC']:
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                root = Path(directory)
                evidence = root / 'evidence'
                derived = root / 'derived'
                (evidence / 'preflight').mkdir(parents=True)
                device = dict(udid='pad', device=dict(identifier='device'), runtime=dict(identifier='runtime'))
                (evidence / 'preflight/preflight.json').write_text(json.dumps(dict(
                    status='PREFLIGHT_PASS_UI_NOT_RUN', selected=dict(ipad=device))))
                checkout = derived / 'SourcePackages/checkouts/TorahInspectorKit'
                checkout.mkdir(parents=True)
                lock = root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
                lock.parent.mkdir(parents=True)
                lock.write_text(json.dumps(dict(pins=[dict(identity='torahinspectorkit', state=dict(revision=runner.KIT))])))
                container = root / 'container'
                fixture = container / 'Library/Application Support/pinkha-simulator-ui27-fixture.json'
                fixture.parent.mkdir(parents=True)
                fixture.write_text('{}')
                calls = []
                def selection(app, configuration, blueprint, udid, selections, environment, target, prefix, *extra):
                    calls.append((blueprint, udid, selections))
                    return dict(status='PASS', passed=1, failed=0, skipped=0)
                def check_output(argv, **kwargs):
                    if argv[:3] == ['xcrun', 'simctl', 'create']:
                        return 'native-pad'
                    if argv[:3] == ['xcrun', 'simctl', 'get_app_container']:
                        return str(container)
                    raise AssertionError(argv)
                stack.enter_context(patch.dict(runner.os.environ, GITHUB_SHA='source', GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1'))
                for name, value in dict(git=lambda path, *args: runner.KIT if path == checkout else 'source',
                    candidate_identity=lambda *args: dict(hashes={}), prepare_source_cache=lambda *args: None,
                    command=lambda *args: None, digest=lambda *args: 'a' * 64,
                    verify_signed_simulator=lambda *args: None, verify_runtime_copies=lambda *args: None,
                    test_configuration=lambda *args: root / 'Original.xctestrun', run_selection=selection,
                    observe_restore_storage=lambda *args: dict(status='OBSERVATIONS_ONLY'),
                    export_ui_console=lambda *args: None, verify_ui_process_continuity=lambda *args: dict(status='PASS')).items():
                    stack.enter_context(patch.object(runner, name, side_effect=value))
                stack.enter_context(patch.object(runner.subprocess, 'check_output', side_effect=check_output))
                ui_project = stack.enter_context(patch.object(runner, 'ui_only_project', return_value=root / 'UI.xcodeproj'))
                install = stack.enter_context(patch.object(runner, 'install_ui_runner'))
                live = stack.enter_context(patch.object(runner, 'live_runtime', return_value=dict(pid=7, runtime_loaded=True)))
                (root / 'Tools/PinkhaSimulatorGate').mkdir(parents=True)
                (root / 'Tools/PinkhaSimulatorGate/required-coverage.json').write_text('{}')
                receipt = {}
                runner.execute(SimpleNamespace(app=root, evidence=evidence, derived=derived, ui_scope=scope), receipt)
                self.assertFalse(receipt['release_accepted'])
                if scope == 'NATIVE_CANCELLATION_DIAGNOSTIC':
                    self.assertEqual(calls, [('AnytypeTests', 'native-pad', ['TorahWave1IntegrationTests/realNativeQueryAndNoteLifecycle'])])
                    ui_project.assert_not_called()
                    install.assert_not_called()
                    live.assert_not_called()
                    self.assertEqual(receipt['actual_ui_passed'], 0)
                else:
                    self.assertEqual(calls, [
                        ('AnytypeTests', 'pad', ['SimulatorAcceptancePreparationTests/prepareRealUIFixture']),
                        ('PinkhaStage1AcceptanceUITests', 'pad', ['AnytypeComprehensiveAcceptanceUITests/testDocumentSourceSearchPresentation'])])
                    self.assertEqual(receipt['native']['status'], 'NOT_RUN')
                    self.assertEqual(receipt['actual_ui_passed'], 1)
                    ui_project.assert_called_once()
                    live.assert_called_once()

    def test_environment_reaches_only_actual_target(self):
        value = [dict(BlueprintName='AnytypeTests'), dict(BlueprintName='OtherTests')]
        runner.inject(value, 'AnytypeTests', {'REAL_ENV': '1'})
        self.assertEqual(value[0]['EnvironmentVariables'], {'REAL_ENV': '1'})
        self.assertNotIn('EnvironmentVariables', value[1])

    def test_restore_observation_never_exports_account_or_configuration_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preferences = root / 'Library/Preferences/io.anytype.app.plist'
            preferences.parent.mkdir(parents=True)
            preferences.write_bytes(plistlib.dumps(dict(userId=json.dumps('private-control-account').encode(),
                serverConfig=json.dumps({'file': {'_0': 'private-control-path.yml'}}).encode())))
            result = runner.observe_restore_storage(root, root, 'control')
            self.assertEqual(result['status'], 'OBSERVATIONS_ONLY')
            self.assertTrue(result['keys']['userId']['nonempty_string'])
            self.assertEqual(result['keys']['serverConfig']['configuration_case'], 'file')
            self.assertFalse(result['cold_process_effective_configuration_verified'])
            serialized = json.dumps(result)
            self.assertNotIn('private-control-account', serialized)
            self.assertNotIn('private-control-path', serialized)

    def test_generated_cached_configuration_is_not_selected_as_xcode_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['Original.xctestrun', 'UI27-old.xctestrun']:
                with (root / name).open('wb') as output:
                    plistlib.dump(dict(BlueprintName='AnytypeTests'), output)
            self.assertEqual(runner.test_configuration(root, 'AnytypeTests').name, 'Original.xctestrun')

    def exercise(self, passed=3, failed=0, command_failure=False, methods=None, os_version='27.0', scope='FULL_SMOKE'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = root / 'Original.xctestrun'
            with configuration.open('wb') as output:
                plistlib.dump(dict(BlueprintName='PinkhaStage1AcceptanceUITests'), output)
            names = runner.SMOKE if scope == 'FULL_SMOKE' else ['testDocumentSourceSearchPresentation']
            selected = ['Suite/' + name for name in names]
            def simulated_command(argv, app, evidence, result, prefix):
                self.assertEqual(len([v for v in argv if v.startswith('-only-testing:')]), len(selected))
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
                    selected, {'PINKHA_UI27_SELECTION_SCOPE': scope}, root / 'fresh', 'control')

    def test_diagnostic_actual_selection_is_one_named_method_per_device_and_never_release_acceptance(self):
        result = self.exercise(passed=1, scope='STARTUP_IPAD_DIAGNOSTIC')
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['ui_scope'], 'STARTUP_IPAD_DIAGNOSTIC')
        self.assertEqual(result['expected_selected_methods'], 1)
        self.assertFalse(result['release_accepted'])
        self.assertFalse(result['full_matrix_accepted'])
        self.assertEqual(self.exercise(passed=3, scope='STARTUP_IPAD_DIAGNOSTIC')['status'], 'FAIL')

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

    def test_failed_diagnostic_projection_does_not_change_actual_failure_or_counts(self):
        with patch.object(runner.diagnostics, 'selection_observation', side_effect=ValueError('private diagnostic error')):
            result = self.exercise(passed=2, failed=1, command_failure=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual((result['passed'], result['failed'], result['skipped']), (2, 1, 0))
        self.assertEqual(result['command_exit_code'], 65)
        self.assertEqual(result['error_type'], 'CalledProcessError')
        self.assertNotIn('public_diagnostics', result)
        self.assertNotIn('private diagnostic error', result['error'])

    def test_stale_pass_evidence_is_refused_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / 'result.json'
            receipt.write_text('{"status":"PASS","run":"old"}')
            with self.assertRaisesRegex(RuntimeError, 'stale selection'):
                runner.run_selection(root, root / 'unused', 'AnytypeTests', 'disposable', [], {}, root, 'control')
            self.assertEqual(json.loads(receipt.read_text())['run'], 'old')

    def exercise_runtime(self, mapped_pid=123, changed_identity=False, stale_main=False, stale_carrier=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'Installed' / 'Anytype.app'
            runtime = installed / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
            built = root / 'Anytype.app'
            for bundle in [installed, built]:
                target = bundle / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
                target.parent.mkdir(parents=True)
                target.write_bytes(bytes.fromhex('cffaedfe') + runner.MARKER.encode())
                (bundle / 'Anytype').write_bytes(bytes.fromhex('cffaedfe') + b'same main executable')
                (bundle / 'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleExecutable='Anytype')))
                for carrier in ['Anytype.debug.dylib', 'Frameworks/Other.framework/Other', 'PlugIns/Widget.appex/Widget']:
                    code = bundle / carrier
                    code.parent.mkdir(parents=True, exist_ok=True)
                    code.write_bytes(bytes.fromhex('cffaedfe') + b'same carrier bytes')
                metadata = bundle / 'Frameworks/Other.framework/Resources/Info.plist'
                metadata.parent.mkdir()
                metadata.write_bytes(plistlib.dumps(dict(CFBundleExecutable='Other')))
                (bundle / 'PlugIns/Widget.appex/Info.plist').write_bytes(plistlib.dumps(dict(CFBundleExecutable='Widget')))
            if stale_main:
                (installed / 'Anytype').write_bytes(bytes.fromhex('cffaedfe') + b'stale main executable')
            if stale_carrier:
                (installed / stale_carrier).write_bytes(bytes.fromhex('cffaedfe') + b'stale carrier bytes')
            identity = 'Sun Nov 15 09:00:00 2026 ' + str(installed / 'Anytype')
            def output(argv, **kwargs):
                if argv[:3] == ['xcrun', 'simctl', 'get_app_container']:
                    return str(installed)
                if argv[:3] == ['xcrun', 'simctl', 'launch']:
                    self.assertEqual(argv[3], '--terminate-running-process')
                    self.assertEqual(argv[-4:], ['-AppleLanguages', '(he)', '-AppleLocale', 'he_IL'])
                    self.assertEqual(kwargs['env']['SIMCTL_CHILD_PINKHA_UI27_ROUTE_OBSERVATION'], '1')
                    self.assertEqual(kwargs['env']['SIMCTL_CHILD_PINKHA_UI27_STARTUP_OBSERVATION'], '1')
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
            mapping = subprocess.CompletedProcess([], 0, 'Process: Anytype [' + str(mapped_pid) + ']\n'
                + str(runtime) + '\n' + str(installed / 'Anytype.debug.dylib'), '')
            with patch.object(runner.subprocess, 'check_output', side_effect=counted_output), \
                    patch.object(runner.subprocess, 'run', return_value=mapping):
                return runner.live_runtime('disposable', root, built, 'he',
                    source_identity=dict(source_sha='a' * 40, run_id='123', run_attempt='1', kit_sha=runner.KIT,
                                         native_marker=runner.MARKER, candidate_inputs_sha256='c' * 64))

    def test_runtime_mapping_is_bound_to_target_pid_and_stable_process_start(self):
        result = self.exercise_runtime()
        self.assertEqual(result['pid'], 123)
        self.assertTrue(result['runtime_loaded'])
        self.assertTrue(result['process_identity_unchanged'])
        self.assertFalse(result['every_launch_verified'])
        self.assertEqual(result['installed_app_executable_sha256'], result['built_app_executable_sha256'])
        self.assertEqual(result['source_sha'], 'a' * 40)

    def test_matching_runtime_cannot_hide_stale_installed_main_executable(self):
        with self.assertRaisesRegex(RuntimeError, 'main executable differs from the fresh build'):
            self.exercise_runtime(stale_main=True)

    def test_matching_main_and_runtime_cannot_hide_a_different_emitted_code_carrier(self):
        for path in ['Anytype.debug.dylib', 'Frameworks/Other.framework/Other', 'PlugIns/Widget.appex/Widget']:
            with self.subTest(possible_carrier=path), self.assertRaisesRegex(RuntimeError, 'code carriers differ'):
                self.exercise_runtime(stale_carrier=path)

    def test_resource_exclusions_are_explicit_and_do_not_claim_full_bundle_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / 'Anytype.app'
            app.mkdir()
            (app / 'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleExecutable='Anytype')))
            (app / 'Anytype').write_bytes(bytes.fromhex('cffaedfe') + b'control main bytes')
            before = runner.code_carriers(app)
            (app / 'Resource.txt').write_text('resource bytes are outside this binding')
            after = runner.code_carriers(app)
            self.assertEqual(before['sha256'], after['sha256'])
            self.assertNotEqual(before['manifest']['exclusions'], after['manifest']['exclusions'])
            self.assertFalse(after['manifest']['full_bundle_equivalence'])

    def test_runtime_mapping_alone_cannot_prove_an_emitted_debug_entrypoint_is_loaded(self):
        installed = Path('/control/Anytype.app')
        paths = ['Anytype', 'Anytype.debug.dylib', 'Frameworks/ProtobufMessages.framework/ProtobufMessages']
        carriers = dict(manifest=dict(carriers={p: {} for p in paths}, aliases={p: [p] for p in paths}))
        mapping = str(installed / paths[-1]) + '\n' + str(installed / 'Anytype')
        with self.assertRaisesRegex(RuntimeError, 'Anytype.debug.dylib'):
            runner.mapped_app_code(installed, carriers, mapping)

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
                    (attachments / filename).write_text("Attributes: Application, 0x10369b340, pid: 68005, label: 'Anytype'\n")
                    rows.append(dict(suggestedHumanReadableName=label + '_0_F18B1EC6-40DB-46EF-AC4D-E1DD3E49AF1E.txt',
                                     exportedFileName=filename))
                manifest.append(dict(testIdentifier=name + '()', attachments=rows))
            (attachments / 'manifest.json').write_text(json.dumps(manifest))
            app = root / 'installed' / 'Anytype.app'
            app.mkdir(parents=True)
            (app / 'Anytype').write_bytes(bytes.fromhex('cffaedfe') + b'actual main bytes')
            (app / 'Info.plist').write_bytes(plistlib.dumps(dict(CFBundleExecutable='Anytype')))
            main_hash = runner.digest(app / 'Anytype')
            live = dict(pid=68005, installed_app=str(app),
                        process_start_identity='start ' + str(app / 'Anytype'), runtime_sha256='runtime',
                        installed_app_executable_sha256=main_hash, built_app_executable_sha256=main_hash,
                        installed_code_carriers=runner.code_carriers(app), built_code_carriers=runner.code_carriers(app),
                        source_sha='a' * 40, run_id='123', run_attempt='1')
            live.update(kit_sha=runner.KIT, native_marker=runner.MARKER, candidate_inputs_sha256='c' * 64)
            with patch.object(runner, 'read_process_identity', return_value=live['process_start_identity']):
                result = runner.verify_ui_process_continuity(root, 'smoke', live, names)
            self.assertEqual(set(result['methods']), set(names))
            self.assertFalse(result['every_launch_verified'])
            with patch.object(runner, 'read_process_identity', return_value='recycled process start'), \
                    self.assertRaisesRegex(RuntimeError, 'start identity changed'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (app / 'Anytype').write_bytes(b'replaced main bytes')
            with patch.object(runner, 'read_process_identity', return_value=live['process_start_identity']), \
                    self.assertRaisesRegex(RuntimeError, 'main executable changed during UI'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (app / 'Anytype').write_bytes(bytes.fromhex('cffaedfe') + b'actual main bytes')
            (app / 'Anytype.debug.dylib').write_bytes(bytes.fromhex('cffaedfe') + b'unexpected code carrier')
            with patch.object(runner, 'read_process_identity', return_value=live['process_start_identity']), \
                    self.assertRaisesRegex(RuntimeError, 'code carriers changed during UI'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (attachments / '1-final-hierarchy.txt').write_text("Application, 0x10369b340, pid: 99999, label: 'Anytype'\n")
            with self.assertRaisesRegex(RuntimeError, 'differs from the mapped'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)
            (attachments / 'manifest.json').write_text(json.dumps(manifest[:1]))
            with self.assertRaisesRegex(RuntimeError, 'missing selected UI methods'):
                runner.verify_ui_process_continuity(root, 'smoke', live, names)


if __name__ == '__main__':
    unittest.main()
