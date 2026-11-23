"""SDK-only original-native selection copy; immutable old prefix and result contract.

Its literal function inverse is recorded alongside the new source. Only the
fresh descriptor filename/open and pre-command registration differ.
"""
import json
import plistlib
import subprocess
from uuid import uuid4

from run_ui27 import (selection_time_budget, write, inject, digest, run_xctest,
                      method_results, diagnostics)


def run_selection(app, configuration, blueprint, udid, selections, environment, evidence, prefix, app_path=None, *, register_descriptor):
    if evidence.exists() and any(evidence.iterdir()):
        raise RuntimeError('Refuse stale selection evidence; use a fresh attempt directory')
    time_budget = selection_time_budget(blueprint, selections)
    evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status='FAIL', selected=selections, phase='EXECUTION', prefix=prefix, command_exit_code=None,
                  time_budget=time_budget)
    if blueprint == 'PinkhaStage1AcceptanceUITests':
        scope = environment.get('PINKHA_UI27_SELECTION_SCOPE', 'FULL_SMOKE')
        if scope not in {'FULL_SMOKE', 'STARTUP_IPAD_DIAGNOSTIC', 'WAVE15_ACCEPTANCE'}:
            raise ValueError('Unsupported recorded UI selection scope')
        result.update(ui_scope=scope, expected_selected_methods=len(selections),
                      release_accepted=False, full_matrix_accepted=False)
    write(evidence / 'result.json', result)
    try:
        with configuration.open('rb') as source:
            data = plistlib.load(source)
        inject(data, blueprint, environment, app_path)
        selected = configuration.with_name('UI27-original-sdk06-selection-' + uuid4().hex + '.xctestrun')
        with selected.open('xb') as target:
            plistlib.dump(data, target)
        register_descriptor(selected, prefix)
        write(evidence / 'selection-inputs.json', dict(blueprint=blueprint, selections=selections,
            environment=environment, xctestrun_sha256=digest(selected), xctestrun_path=str(selected),
            device_udid=udid, time_budget=time_budget))
        bundle = evidence / (prefix + '.xcresult')
        filters = sorted({name.split('/')[0] for name in selections}) if blueprint == 'AnytypeTests' else selections
        run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(selected),
                    '-destination', 'platform=iOS Simulator,id=' + udid, '-parallel-testing-enabled', 'NO',
                    '-test-timeouts-enabled', 'YES',
                    '-default-test-execution-time-allowance', str(time_budget['default_seconds']),
                    '-maximum-test-execution-time-allowance', str(time_budget['maximum_seconds']),
                    *['-only-testing:' + blueprint + '/' + name for name in filters],
                    '-resultBundlePath', str(bundle)], app, evidence, bundle, prefix)
        result['command_exit_code'] = 0
        summary = json.loads((evidence / (prefix + '-summary.json')).read_text())
        devices = [row['device'] for row in summary.get('devicesAndConfigurations', [])]
        if not devices or any(d.get('osVersion', '').split('.')[0] != '27'
            or d.get('deviceId', '').lower() != udid.lower() or d.get('architecture') != 'arm64' for d in devices):
            raise RuntimeError('Actual xcresult OS27/device/architecture differs from the selected simulator')
        result['actual_devices'] = devices
        methods = method_results(json.loads((evidence / (prefix + '-tests.json')).read_text()))
        expected = {name.removesuffix('()') for name in selections}
        actual = {name.removesuffix('()'): outcome for name, outcome in methods.items()}
        if (summary.get('passedTests') != len(expected) or summary.get('failedTests') != 0
                or summary.get('skippedTests') != 0 or set(actual) != expected
                or any(outcome != 'Passed' for outcome in actual.values())):
            raise RuntimeError('Actual named method results/counts differ from exact selection')
        result.update(status='PASS', passed=len(expected), failed=0, skipped=0, actual_methods=methods)
    except BaseException as error:
        result.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        if isinstance(error, subprocess.CalledProcessError):
            result['command_exit_code'] = error.returncode
    summary_path = evidence / (prefix + '-summary.json')
    tests_path = evidence / (prefix + '-tests.json')
    diagnostic_summary = None
    if summary_path.exists() and tests_path.exists():
        try:
            raw = json.loads(summary_path.read_text())
            diagnostic_summary = raw
            result.update(passed=raw.get('passedTests'), failed=raw.get('failedTests'), skipped=raw.get('skippedTests'),
                          actual_methods=method_results(json.loads(tests_path.read_text())))
        except (ValueError, KeyError) as error:
            result.update(status='FAIL', evidence_error=str(error))
    observation = diagnostics.emit_selection(result, diagnostic_summary)
    if observation is not None:
        result['public_diagnostics'] = observation
    write(evidence / 'result.json', result)
    return result
