"""One actual Xcode/native Wave 1 test; no IPA, signing or broad UI matrix."""
import argparse
import json
from pathlib import Path
import platform
import plistlib
import subprocess

from build_custom_heart import command, contains, digest, git
from build_native_ipa import prepare_source_cache, run_xctest, test_configuration

KIT_SHA = 'c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9'
BRANCH = 'codex/anytype-wave1-integration-20261115'
SELECTION = 'AnytypeTests/TorahWave1IntegrationTests'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app-source', required=True, type=Path)
    parser.add_argument('--simulator-udid', required=True)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    app, evidence = args.app_source.resolve(), args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
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
    prepare_source_cache(app, derived)
    command(['xcodebuild', 'build-for-testing', '-project', 'Anytype.xcodeproj', '-scheme', 'Anytype',
             '-configuration', 'Release-Anytype', '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
             '-derivedDataPath', str(derived), '-parallel-testing-enabled', 'NO', '-only-testing:'+SELECTION,
             'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED', 'ENABLE_TESTABILITY=YES',
             'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone', 'CODE_SIGNING_ALLOWED=NO'], app, evidence)
    checkout = next((p for p in (derived/'SourcePackages/checkouts').iterdir()
                     if p.name.lower() == 'torahinspectorkit'), None)
    if checkout is None or git(checkout, 'rev-parse', 'HEAD') != KIT_SHA:
        raise RuntimeError('Xcode did not actually consume the published V3 checkout')
    lock_path = app/'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    lock = json.loads(lock_path.read_text())
    if next((p['state']['revision'] for p in lock['pins'] if p['identity'] == 'torahinspectorkit'), None) != KIT_SHA:
        raise RuntimeError('Actual resolved Kit revision differs')
    (evidence/'Package.resolved').write_bytes(lock_path.read_bytes())
    app_bundle = derived/'Build/Products/Release-Anytype-iphonesimulator/Anytype.app'
    runtimes = [p for p in app_bundle.rglob('ProtobufMessages') if p.is_file()]
    if len(runtimes) != 1 or not contains(runtimes[0], heart['marker'].encode()):
        raise RuntimeError('Built application does not embed the verified native runtime marker')
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
    run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(selected),
                '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
                '-parallel-testing-enabled', 'NO', '-only-testing:'+SELECTION,
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
    receipt = dict(status='PASS', app_sha=git(app, 'rev-parse', 'HEAD'), kit_sha=KIT_SHA,
                   actual_kit_checkout=str(checkout), pin_sites=['Modules/PinkhaKit/Package.swift',
                   'Anytype.xcodeproj/project.pbxproj'], selection=SELECTION,
                   passed=1, failed=0, skipped=0, passed_method_nodes=passed_methods,
                   runtime_sha256=digest(runtimes[0]),
                   native_marker=heart['marker'], simulator=simulator,
                   scope='Actual native API and host actions; no Inspector UI traversal or physical acceptance',
                   result_bundle=str(result))
    (evidence/'wave1-native-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
