"""One actual Xcode/native Wave 1 test; no IPA, signing or broad UI matrix."""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import subprocess

from build_custom_heart import command, contains, digest, git
from build_native_ipa import prepare_source_cache, run_xctest, test_configuration

KIT_SHA = '5aa16f616910d70e54e74b2a0e58e107e07a90e3'
BRANCH = 'codex/anytype-wave1-integration-20261115'
SELECTION = 'AnytypeTests/TorahWave1IntegrationTests'


def write_receipt(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n')
    temporary.replace(path)


def with_receipt(evidence, context, action):
    path = evidence/'wave1-native-receipt.json'
    write_receipt(path, dict(context, status='RUNNING'))
    try:
        result = dict(context, **action())
        write_receipt(path, result)
        return result
    except BaseException as error:
        write_receipt(path, dict(context, status='FAIL', error=type(error).__name__+': '+str(error)))
        raise


def verify_runtime_copies(bundle, marker, evidence):
    root = bundle/'Frameworks/ProtobufMessages.framework/ProtobufMessages'
    test_host = bundle/'PlugIns/AnytypeTests.xctest/Frameworks/ProtobufMessages.framework/ProtobufMessages'
    copies = sorted(p for p in bundle.rglob('ProtobufMessages.framework/ProtobufMessages') if p.is_file())
    records = {str(p.relative_to(bundle)): dict(sha256=digest(p), marker_present=contains(p, marker)) for p in copies}
    write_receipt(evidence/'runtime-copies.json', dict(root_present=root in copies,
                  test_host_present=test_host in copies, copies=records))
    if root not in copies or test_host not in copies or not all(v['marker_present'] for v in records.values()):
        raise RuntimeError('The app or an embedded test runtime lacks the exact verified marker; see runtime-copies.json')
    return root, records


def bundle_hashes(bundle):
    return {str(p.relative_to(bundle)): digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()}


def require_run_identity(actual_sha, run_id, expected_sha):
    if not run_id or not re.fullmatch(r'[0-9]+', run_id):
        raise RuntimeError('A nonempty actual GITHUB_RUN_ID is required')
    if not expected_sha or not re.fullmatch(r'[0-9a-f]{40}', expected_sha) or actual_sha != expected_sha:
        raise RuntimeError('Actual Git HEAD must match the nonempty GITHUB_SHA')


def validate(args, app, evidence, context):
    context['app_sha'] = git(app, 'rev-parse', 'HEAD')
    require_run_identity(context['app_sha'], context['run_id'], context['expected_run_sha'])
    if platform.system() != 'Darwin' or git(app, 'branch', '--show-current') != BRANCH:
        raise RuntimeError('Requires macOS and the isolated Wave 1 integration branch')
    package = (app/'Modules/PinkhaKit/Package.swift').read_text()
    project = (app/'Anytype.xcodeproj/project.pbxproj').read_text()
    if f'revision: "{KIT_SHA}"' not in package or f'revision = {KIT_SHA};' not in project:
        raise RuntimeError('Both production Kit pins must match the published V3 SHA')
    simulator = json.loads((evidence.parent/'disposable-simulator.json').read_text())
    if simulator['udid'] != args.simulator_udid or not simulator['name'].startswith('Pinkha-Native-Derived-'):
        raise RuntimeError('Requires the fresh disposable simulator receipt')
    middleware = app/'Dependencies/Middleware'
    heart = json.loads((middleware/'PinkhaNativeHeartBuild.json').read_text())
    if heart['status'] != 'PASS' or heart['target'] != 'ios':
        raise RuntimeError('Verified custom iOS Heart is required')
    framework = middleware/'Lib.xcframework'
    for artifact in heart['artifacts']:
        if digest(framework/artifact['path']) != artifact['sha256']:
            raise RuntimeError('Installed Heart bytes differ from the verified artifact')
    command(['xcodebuild', '-version'], app, evidence)
    derived = evidence/'DerivedData-NativeAcceptance'
    app_bundle = derived/'Build/Products/Release-Anytype-iphonesimulator/Anytype.app'
    cached_manifest = derived/'Build/PinkhaSourceInputs.json'
    cached_inputs = json.loads(cached_manifest.read_text()) if cached_manifest.exists() else {}
    cached_source = cached_inputs.get('source_sha')
    old_inputs = cached_inputs.get('inputs', {})
    tracked = set(subprocess.check_output(['git', '-C', str(app), 'ls-files', '-z']).decode().split('\0')) - {''}
    changed = sorted(p for p in tracked | set(old_inputs)
                     if not (app/p).is_file() or digest(app/p) != old_inputs.get(p, {}).get('sha256'))
    before = bundle_hashes(app_bundle)
    context['phase'] = 'BUILD'
    prepare_source_cache(app, derived)
    command(['xcodebuild', 'build-for-testing', '-project', 'Anytype.xcodeproj', '-scheme', 'Anytype',
             '-configuration', 'Release-Anytype', '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
             '-derivedDataPath', str(derived), '-parallel-testing-enabled', 'NO', '-only-testing:'+SELECTION,
             'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED', 'ENABLE_TESTABILITY=YES',
             'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone', 'CODE_SIGNING_ALLOWED=NO'], app, evidence)
    after = bundle_hashes(app_bundle)
    build_input_change = [p for p in changed if not (p.startswith('docs/') or p in {
        'Tools/PinkhaNativeDerived/validate_wave1.py', 'Tools/PinkhaNativeDerived/test_validate_wave1.py'
    })]
    reuse = dict(cached_build_source_sha=cached_source, current_run_source_sha=context['app_sha'],
                 changed_paths=changed, changed_build_input_paths=build_input_change,
                 before=before, after=after,
                 exact_cached_bundle_bytes_reused=bool(cached_source and re.fullmatch(r'[0-9a-f]{40}', cached_source))
                 and bool(before) and before == after and not build_input_change,
                 xcode_build_for_testing='SUCCEEDED')
    write_receipt(evidence/'compiled-build-equivalence.json', reuse)
    context['phase'] = 'RUNTIME_VERIFICATION'
    checkout = next((p for p in (derived/'SourcePackages/checkouts').iterdir()
                     if p.name.lower() == 'torahinspectorkit'), None)
    if checkout is None or git(checkout, 'rev-parse', 'HEAD') != KIT_SHA:
        raise RuntimeError('Xcode did not actually consume the published V3 checkout')
    lock_path = app/'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    lock = json.loads(lock_path.read_text())
    if next((p['state']['revision'] for p in lock['pins'] if p['identity'] == 'torahinspectorkit'), None) != KIT_SHA:
        raise RuntimeError('Actual resolved Kit revision differs')
    write_receipt(evidence/'resolved-package-pins.json', lock)
    runtime, runtime_copies = verify_runtime_copies(app_bundle, heart['marker'].encode(), evidence)
    (derived/'Build/Products/Wave1Native.xctestrun').unlink(missing_ok=True)
    configuration = test_configuration(derived/'Build/Products', 'AnytypeTests')
    with configuration.open('rb') as stream:
        run = plistlib.load(stream)

    def inject(value):
        if isinstance(value, dict):
            if value.get('BlueprintName') == 'AnytypeTests' or value.get('TestBundlePath', '').endswith('AnytypeTests.xctest'):
                value.setdefault('EnvironmentVariables', {})['PINKHA_WAVE1_ACCEPTANCE'] = '1'
            for child in value.values():
                inject(child)
        elif isinstance(value, list):
            for child in value:
                inject(child)

    inject(run)
    selected = configuration.with_name('Wave1Native.xctestrun')
    with selected.open('wb') as stream:
        plistlib.dump(run, stream)
    result = evidence/'Wave1Native.xcresult'
    context['phase'] = 'NATIVE_TEST'
    run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(selected),
                '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
                '-parallel-testing-enabled', 'NO', '-only-testing:'+SELECTION,
                '-test-timeouts-enabled', 'YES', '-default-test-execution-time-allowance', '300',
                '-maximum-test-execution-time-allowance', '300',
                '-resultBundlePath', str(result)], app, evidence, result, 'wave1-native')
    summary = json.loads((evidence/'wave1-native-summary.json').read_text())
    if summary.get('passedTests') != 1 or summary.get('failedTests') != 0 or summary.get('skippedTests') != 0:
        raise RuntimeError('Expected exactly one executed native test, zero failures and zero skips')
    tests = json.loads((evidence/'wave1-native-tests.json').read_text())
    passed_methods = []

    def find_passed_method(value):
        if isinstance(value, dict):
            names = [v for v in value.values() if isinstance(v, str)
                     and 'realNativeQueryAndNoteLifecycle' in v]
            if value.get('result') == 'Passed' and names:
                passed_methods.extend(names)
            for child in value.values():
                find_passed_method(child)
        elif isinstance(value, list):
            for child in value:
                find_passed_method(child)

    find_passed_method(tests)
    if not passed_methods:
        raise RuntimeError('The actual changed host/query method is not Passed in xcresult')
    require_run_identity(git(app, 'rev-parse', 'HEAD'), context['run_id'], context['expected_run_sha'])
    receipt = dict(status='PASS', app_sha=git(app, 'rev-parse', 'HEAD'), kit_sha=KIT_SHA,
                   actual_kit_checkout=str(checkout), pin_sites=['Modules/PinkhaKit/Package.swift',
                   'Anytype.xcodeproj/project.pbxproj'], selection=SELECTION,
                   passed=1, failed=0, skipped=0, passed_method_nodes=passed_methods,
                   runtime_sha256=digest(runtime), embedded_runtime_copies=runtime_copies,
                   cached_build_source_sha=cached_source,
                   exact_cached_bundle_bytes_reused=reuse['exact_cached_bundle_bytes_reused'],
                   native_marker=heart['marker'], simulator=simulator,
                   scope='Actual native API and host actions; no Inspector UI traversal or physical acceptance',
                   result_bundle=str(result))
    return receipt


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app-source', required=True, type=Path)
    parser.add_argument('--simulator-udid', required=True)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    app, evidence = args.app_source.resolve(), args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    context = dict(run_id=os.environ.get('GITHUB_RUN_ID'), expected_run_sha=os.environ.get('GITHUB_SHA'),
                   run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'), kit_sha=KIT_SHA, phase='PREFLIGHT')
    receipt = with_receipt(evidence, context, lambda: validate(args, app, evidence, context))
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
