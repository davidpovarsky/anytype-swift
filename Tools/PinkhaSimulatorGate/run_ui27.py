"""Build once and execute real native/three-method UI smoke on disposable OS27 devices."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'PinkhaNativeDerived'))
from build_custom_heart import command, digest, git, contains
from build_native_ipa import prepare_source_cache, run_xctest
from validate_wave1 import verify_runtime_copies
from validate_release import method_results, candidate_identity
from rerun_original_ui import ui_only_project, install_ui_runner, export_ui_console

SMOKE = ['testObjectAddPropertyButtonAndPickerSearch', 'testDocumentSourceSearchPresentation',
         'testSourceChipOpensAndClosesInspector']
KIT = 'c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9'
MARKER = 'pinkha-native-derived-v1-fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def inject(value, blueprint, environment, app_path=None):
    if isinstance(value, dict):
        if value.get('BlueprintName') == blueprint or value.get('TestBundlePath', '').endswith(blueprint + '.xctest'):
            value.setdefault('EnvironmentVariables', {}).update(environment)
            if app_path:
                value['UITargetAppPath'] = str(app_path)
                value['UITargetAppBundleIdentifier'] = 'io.anytype.app'
        for child in value.values():
            inject(child, blueprint, environment, app_path)
    elif isinstance(value, list):
        for child in value:
            inject(child, blueprint, environment, app_path)


def run_selection(app, configuration, blueprint, udid, selections, environment, evidence, prefix, app_path=None):
    if evidence.exists() and any(evidence.iterdir()):
        raise RuntimeError('Refuse stale selection evidence; use a fresh attempt directory')
    evidence.mkdir(parents=True, exist_ok=True)
    result = dict(status='FAIL', selected=selections, phase='EXECUTION', prefix=prefix)
    write(evidence / 'result.json', result)
    try:
        with configuration.open('rb') as source:
            data = plistlib.load(source)
        inject(data, blueprint, environment, app_path)
        selected = configuration.with_name('UI27-' + prefix + '.xctestrun')
        with selected.open('wb') as target:
            plistlib.dump(data, target)
        bundle = evidence / (prefix + '.xcresult')
        filters = sorted({name.split('/')[0] for name in selections}) if blueprint == 'AnytypeTests' else selections
        run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(selected),
                    '-destination', 'platform=iOS Simulator,id=' + udid, '-parallel-testing-enabled', 'NO',
                    '-test-timeouts-enabled', 'YES', '-default-test-execution-time-allowance', '300',
                    '-maximum-test-execution-time-allowance', '300',
                    *['-only-testing:' + blueprint + '/' + name for name in filters],
                    '-resultBundlePath', str(bundle)], app, evidence, bundle, prefix)
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
    summary_path = evidence / (prefix + '-summary.json')
    tests_path = evidence / (prefix + '-tests.json')
    if summary_path.exists() and tests_path.exists():
        try:
            raw = json.loads(summary_path.read_text())
            result.update(passed=raw.get('passedTests'), failed=raw.get('failedTests'), skipped=raw.get('skippedTests'),
                          actual_methods=method_results(json.loads(tests_path.read_text())))
        except (ValueError, KeyError) as error:
            result.update(status='FAIL', evidence_error=str(error))
    write(evidence / 'result.json', result)
    return result


def test_configuration(products, blueprint):
    def matches(value):
        if isinstance(value, dict):
            return value.get('BlueprintName') == blueprint or any(matches(v) for v in value.values())
        return isinstance(value, list) and any(matches(v) for v in value)
    candidates = []
    for path in products.glob('*.xctestrun'):
        if path.name.startswith(('UI27-', 'PinkhaNativeDerived')):
            continue
        with path.open('rb') as source:
            if matches(plistlib.load(source)):
                candidates.append(path)
    if len(candidates) != 1:
        raise RuntimeError('Expected one actual current Xcode configuration for ' + blueprint)
    return candidates[0]


def verify_signed_simulator(app_bundle, evidence):
    command(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app_bundle)], app_bundle.parent, evidence)
    result = subprocess.run(['/usr/bin/codesign', '--display', '--entitlements', '-', '--xml', str(app_bundle)],
                            capture_output=True, check=True)
    entitlements = plistlib.loads(result.stdout)
    identifier = entitlements.get('application-identifier') or entitlements.get('com.apple.application-identifier', '')
    if not identifier.endswith('.io.anytype.app'):
        raise RuntimeError('Actual simulator app lacks its Keychain application identity')
    write(evidence / 'signed-simulator-entitlements.json', entitlements)


def live_runtime(udid, evidence, built):
    installed = Path(subprocess.check_output(['xcrun', 'simctl', 'get_app_container', udid,
                                             'io.anytype.app', 'app'], text=True).strip())
    runtime = installed / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
    launch = subprocess.check_output(['xcrun', 'simctl', 'launch', udid, 'io.anytype.app'], text=True)
    pid = int(re.search(r':\s*(\d+)', launch).group(1))
    mapping = subprocess.run(['/usr/bin/vmmap', '-w', str(pid)], capture_output=True, text=True)
    (evidence / 'live-runtime-vmmap.log').write_text(mapping.stdout + mapping.stderr)
    loaded = mapping.returncode == 0 and str(runtime) in mapping.stdout
    record = dict(pid=pid, installed_app=str(installed), runtime_path=str(runtime),
                  runtime_sha256=digest(runtime), marker_present=contains(runtime, MARKER.encode()),
                  runtime_loaded=loaded, vmmap_exit_code=mapping.returncode)
    write(evidence / 'live-runtime.json', record)
    if not record['marker_present'] or record['runtime_sha256'] != digest(built / 'Frameworks/ProtobufMessages.framework/ProtobufMessages'):
        raise RuntimeError('Installed runtime bytes/marker differ from the verified build')
    return record


def execute(args, receipt):
    app = args.app.resolve()
    evidence = args.evidence.resolve()
    derived = args.derived.resolve()
    preflight = json.loads((evidence / 'preflight/preflight.json').read_text())
    if preflight.get('status') != 'PREFLIGHT_PASS_UI_NOT_RUN':
        raise RuntimeError('Actual OS27 preflight did not pass')
    head = git(app, 'rev-parse', 'HEAD')
    if head != os.environ.get('GITHUB_SHA') or not os.environ.get('GITHUB_RUN_ID', '').isdigit():
        raise RuntimeError('Actual source/run identity differs')
    matrix = json.loads((app / 'Tools/PinkhaSimulatorGate/required-coverage.json').read_text())
    identity = candidate_identity(app, matrix)
    receipt.update(source_sha=head, kit_sha=KIT, native_marker=MARKER,
                   run_id=os.environ['GITHUB_RUN_ID'], run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
                   candidate_input_hashes=identity['hashes'], preflight=preflight)
    ipad = preflight['selected']['ipad']
    native_udid = subprocess.check_output(['xcrun', 'simctl', 'create',
        'Pinkha-UI27-native-' + receipt['run_id'], ipad['device']['identifier'], ipad['runtime']['identifier']], text=True).strip()
    receipt['native_proof_udid'] = native_udid
    for udid in [native_udid]:
        command(['xcrun', 'simctl', 'boot', udid], app, evidence)
        command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], app, evidence)
    prepare_source_cache(app, derived)
    flags = ['OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED', 'ENABLE_TESTABILITY=YES',
             'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone', 'CODE_SIGN_IDENTITY=-',
             'CODE_SIGNING_ALLOWED=YES', 'CODE_SIGNING_REQUIRED=YES', 'PROVISIONING_PROFILE_SPECIFIER=']
    base = ['xcodebuild', 'build-for-testing', '-configuration', 'Release-Anytype',
            '-destination', 'platform=iOS Simulator,id=' + native_udid, '-derivedDataPath', str(derived),
            '-parallel-testing-enabled', 'NO']
    receipt['phase'] = 'BUILD'
    command([*base, '-project', 'Anytype.xcodeproj', '-scheme', 'Anytype',
        '-only-testing:AnytypeTests/TorahWave1IntegrationTests',
        '-only-testing:AnytypeTests/SimulatorAcceptancePreparationTests', *flags], app, evidence)
    ui_project = ui_only_project(app)
    command([*base, '-project', str(ui_project), '-scheme', 'PinkhaPrebuiltUI',
        *['-only-testing:PinkhaStage1AcceptanceUITests/AnytypeComprehensiveAcceptanceUITests/' + name for name in SMOKE],
        *flags], app, evidence)
    products = derived / 'Build/Products'
    built = products / 'Release-Anytype-iphonesimulator/Anytype.app'
    verify_signed_simulator(built, evidence)
    verify_runtime_copies(built, MARKER.encode(), evidence)
    checkout = derived / 'SourcePackages/checkouts/TorahInspectorKit'
    if not checkout.exists():
        checkout = next(p for p in (derived / 'SourcePackages/checkouts').iterdir() if p.name.lower() == 'torahinspectorkit')
    if git(checkout, 'rev-parse', 'HEAD') != KIT:
        raise RuntimeError('Actual resolved Kit checkout differs')
    lock = json.loads((app / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_text())
    if next(p['state']['revision'] for p in lock['pins'] if p['identity'] == 'torahinspectorkit') != KIT:
        raise RuntimeError('Actual resolved Kit lock differs')
    write(evidence / 'actual-package-pins.json', lock)
    receipt['app_executable_sha256'] = digest(built / 'Anytype')
    native_configuration = test_configuration(products, 'AnytypeTests')
    ui_configuration = test_configuration(products, 'PinkhaStage1AcceptanceUITests')
    receipt['phase'] = 'EXECUTION'
    receipt['native'] = run_selection(app, native_configuration, 'AnytypeTests', native_udid,
        ['TorahWave1IntegrationTests/realNativeQueryAndNoteLifecycle'], {'PINKHA_WAVE1_ACCEPTANCE': '1'},
        evidence / 'native', 'native')
    for kind, selection in preflight['selected'].items():
        device_evidence = evidence / kind
        device_evidence.mkdir(exist_ok=True)
        udid = selection['udid']
        command(['xcrun', 'simctl', 'boot', udid], app, device_evidence)
        command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], app, device_evidence)
        preparation = run_selection(app, native_configuration, 'AnytypeTests', udid,
            ['SimulatorAcceptancePreparationTests/prepareRealUIFixture'],
            {'PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION': '1', 'PINKHA_SIMULATOR_UI_DISPOSABLE': '1'},
            device_evidence / 'preparation', 'prepare-' + kind)
        receipt[kind] = dict(preparation=preparation, ui_status='NOT_RUN')
        if preparation['status'] != 'PASS':
            continue
        container = Path(subprocess.check_output(['xcrun', 'simctl', 'get_app_container', udid, 'io.anytype.app', 'data'], text=True).strip())
        fixture = json.loads((container / 'Library/Application Support/pinkha-simulator-ui27-fixture.json').read_text())
        write(device_evidence / 'fixture-ids.json', fixture)
        live = live_runtime(udid, device_evidence, built)
        receipt[kind]['live_runtime'] = live
        install_ui_runner(udid, products, app, device_evidence)
        try:
            result = run_selection(app, ui_configuration, 'PinkhaStage1AcceptanceUITests', udid,
                ['AnytypeComprehensiveAcceptanceUITests/' + name for name in SMOKE],
                {'PINKHA_NATIVE_UI_DISPOSABLE': '1', 'PINKHA_NATIVE_UI_FIXTURE_JSON': json.dumps(fixture)},
                device_evidence / 'ui', 'smoke-' + kind, built)
        finally:
            export_ui_console(udid, device_evidence)
        receipt[kind].update(ui_status=result['status'], ui=result, configuration_id=kind + '-en-portrait-os27')
        write(evidence / 'execution.json', receipt)
    for label, key in [('passed', 'actual_ui_passed'), ('failed', 'actual_ui_failed'), ('skipped', 'actual_ui_skipped')]:
        receipt[key] = sum(receipt.get(k, {}).get('ui', {}).get(label) or 0 for k in ['iphone', 'ipad'])
    if receipt['native']['status'] != 'PASS' or any(receipt.get(k, {}).get('ui_status') != 'PASS' for k in ['iphone', 'ipad']):
        raise RuntimeError('One or more actual native/preparation/UI components did not pass')
    if any(not receipt[k]['live_runtime']['runtime_loaded'] for k in ['iphone', 'ipad']):
        raise RuntimeError('Actual UI results retained, but required live-runtime mapping is unverified')
    receipt.update(status='SMOKE_PASS_FULL_ACCEPTANCE_PENDING', actual_ui_passed=6, actual_ui_failed=0,
                   actual_ui_skipped=0, release_accepted=False,
                   limitations=['Only three English smoke methods per device', 'Full required matrix and visual review remain open'])


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--derived', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = dict(status='RUNNING', phase='PREFLIGHT', components={}, release_accepted=False,
                   started_at=datetime.now(timezone.utc).isoformat())
    write(args.evidence / 'execution.json', receipt)
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
    write(args.evidence / 'execution.json', receipt)
    print(json.dumps(receipt))
    return 0 if receipt['status'] == 'SMOKE_PASS_FULL_ACCEPTANCE_PENDING' else 1


if __name__ == '__main__':
    raise SystemExit(main())
