"""Run the actual native middleware test host and build an unsigned iPad IPA.

Requires a macOS/Xcode host and a disposable iPad simulator. Uses the previously
built custom framework; never downloads/replaces it with official middleware.
This does not claim physical-iPad, full D01-D34, or signing acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import zipfile

from build_custom_heart import command, contains, digest, git

def prepare_source_cache(app, derived):
    """Restore source timestamps only when cached and current bytes match.

    A fresh checkout otherwise invalidates unchanged Swift targets in restored
    DerivedData. This affects build inputs only, never simulator/test results.
    """
    manifest = derived/'Build/PinkhaSourceInputs.json'
    previous = {}
    if manifest.exists():
        try:
            decoded = json.loads(manifest.read_text())
            previous = decoded.get('inputs', {}) if isinstance(decoded, dict) else {}
        except (ValueError, OSError):
            pass  # A missing/invalid cache merely requires normal compilation.
    if not isinstance(previous, dict):
        previous = {}
    inputs = {}
    restored = 0
    paths = subprocess.check_output(['git', '-C', str(app), 'ls-files', '-z']).decode('utf8').split('\0')
    framework = app/'Dependencies/Middleware/Lib.xcframework'
    paths += [str(path.relative_to(app)) for path in framework.rglob('*') if path.is_file()]
    for relative in filter(None, paths):
        path = app/relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(app):
            continue
        sha = digest(path)
        cached = previous.get(relative, {})
        if not isinstance(cached, dict):
            cached = {}
        modified = cached.get('mtime_ns')
        if cached.get('sha256') == sha and isinstance(modified, int) and modified >= 0:
            os.utime(path, ns=(path.stat().st_atime_ns, modified))
            restored += 1
        inputs[relative] = dict(sha256=sha, mtime_ns=path.stat().st_mtime_ns)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(dict(source_sha=git(app, 'rev-parse', 'HEAD'), inputs=inputs), indent=2)+'\n')
    print(json.dumps(dict(content_verified_source_timestamps=restored)), flush=True)

def test_configuration(products, blueprint):
    """Select Xcode's current configuration, excluding our generated copies."""
    def contains_blueprint(value):
        if isinstance(value, dict):
            return value.get('BlueprintName') == blueprint or any(contains_blueprint(v) for v in value.values())
        if isinstance(value, list):
            return any(contains_blueprint(v) for v in value)
        return False
    matches = []
    for path in products.glob('*.xctestrun'):
        if path.name in {'PinkhaNativeDerived.xctestrun', 'PinkhaNativeDerivedUI.xctestrun'}:
            continue
        with path.open('rb') as stream:
            if contains_blueprint(plistlib.load(stream)):
                matches.append(path)
    if len(matches) != 1:
        raise RuntimeError('Expected one actual Xcode configuration for ' + blueprint)
    return matches[0]

def run_xctest(argv, app, evidence, result, prefix):
    # Failure evidence must survive the strict acceptance gate too. Exporting
    # diagnostics never changes the xcodebuild exit status or acceptance result.
    try:
        command(argv,app,evidence)
    finally:
        if result.exists():
            for mode in ['summary','tests']:
                with (evidence/(prefix+'-'+mode+'.json')).open('w') as stream:
                    subprocess.run(['xcrun','xcresulttool','get','test-results',mode,
                        '--path',str(result),'--format','json'],stdout=stream,stderr=subprocess.STDOUT)
            subprocess.run(['xcrun','xcresulttool','export','attachments','--path',str(result),
                '--output-path',str(evidence/(prefix+'-attachments'))],check=False)

def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--app-source',required=True,type=Path)
    parser.add_argument('--simulator-udid',required=True)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--tests-only',action='store_true')
    parser.add_argument('--reuse-policy-and-header-from-run', type=int)
    parser.add_argument('--relink-verified-swift-from-run', type=int)
    args=parser.parse_args()
    if platform.system()!='Darwin': raise RuntimeError('Actual macOS/Xcode required')
    app=args.app_source.resolve()
    if git(app,'branch','--show-current')!='codex/torah-native-derived-properties-20261103': raise RuntimeError('Wrong application branch')
    evidence=args.evidence.resolve()
    evidence.mkdir(parents=True,exist_ok=True)
    middleware=app/'Dependencies/Middleware'
    heart=json.loads((middleware/'PinkhaNativeHeartBuild.json').read_text())
    if heart['status']!='PASS' or heart['target']!='ios': raise RuntimeError('Custom iOS Heart build is missing')
    marker=heart['marker'].encode()
    framework=middleware/'Lib.xcframework'
    for entry in heart['artifacts']:
        if digest(framework/entry['path'])!=entry['sha256']: raise RuntimeError('Installed XCFramework differs from tested build')
    command(['xcodebuild','-version'],app,evidence)
    simulator=json.loads(subprocess.check_output(['xcrun','simctl','list','devices','available','--json'],text=True))
    devices=[device for devices in simulator['devices'].values() for device in devices]
    selected=next((device for device in devices if device['udid']==args.simulator_udid),None)
    simulator_receipt=json.loads((evidence.parent/'disposable-simulator.json').read_text())
    if (not selected or not selected['name'].startswith('Pinkha-Native-Derived-')
        or simulator_receipt['udid']!=args.simulator_udid
        or 'iPad' not in simulator_receipt['device']['name']):
        raise RuntimeError('Use the freshly created Pinkha-Native-Derived disposable iPad simulator')
    derived=evidence/'DerivedData-NativeAcceptance'
    common=['-project','Anytype.xcodeproj','-scheme','Anytype','-configuration','Release-Anytype',
            'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED']
    if args.relink_verified_swift_from_run:
        if args.relink_verified_swift_from_run != 42740484502:
            raise RuntimeError('Unknown accepted compiled Swift authority')
        from relink_verified_simulator import relink
        relink(app, derived, evidence, heart)
        prepare_source_cache(app, derived)
    else:
        prepare_source_cache(app, derived)
        command(['xcodebuild','build-for-testing',*common,'-destination','platform=iOS Simulator,id='+args.simulator_udid,
                 '-derivedDataPath',str(derived),'-parallel-testing-enabled','NO','ENABLE_TESTABILITY=YES','ONLY_ACTIVE_ARCH=YES',
                 'SWIFT_OPTIMIZATION_LEVEL=-Onone'],app,evidence)
    configuration=test_configuration(derived/'Build/Products', 'AnytypeTests')
    with configuration.open('rb') as stream: run=plistlib.load(stream)
    def inject(value):
        if isinstance(value,dict):
            if value.get('BlueprintName')=='AnytypeTests' or value.get('TestBundlePath','').endswith('AnytypeTests.xctest'):
                value.setdefault('EnvironmentVariables',{})['PINKHA_NATIVE_DERIVED_ACCEPTANCE']='1'
            for child in value.values(): inject(child)
        elif isinstance(value,list):
            for child in value: inject(child)
    inject(run)
    native_run=configuration.with_name('PinkhaNativeDerived.xctestrun')
    with native_run.open('wb') as stream: plistlib.dump(run,stream)
    result=evidence/'NativeDerivedProduct.xcresult'
    run_xctest(['xcodebuild','test-without-building','-xctestrun',str(native_run),'-destination',
             'platform=iOS Simulator,id='+args.simulator_udid,'-parallel-testing-enabled','NO',
             '-only-testing:AnytypeTests/TorahNativeDerivedProductIntegrationTests','-resultBundlePath',str(result)],app,evidence,result,'native-product')
    summary=json.loads(subprocess.check_output(['xcrun','xcresulttool','get','test-results','summary','--path',str(result),'--format','json'],text=True))
    (evidence/'native-product-test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def count(key):
        pending=[summary]
        while pending:
            value=pending.pop()
            if isinstance(value,dict):
                if key in value and isinstance(value[key],int): return value[key]
                pending.extend(value.values())
            elif isinstance(value,list): pending.extend(value)
        raise RuntimeError('Missing actual test count: '+key)
    if count('passedTests')<1 or count('failedTests') or count('skippedTests'): raise RuntimeError('Native product acceptance did not pass without skips')
    native_passed=count('passedTests')
    policy_passed=0
    policy_reused=0
    header_reused=0
    if args.reuse_policy_and_header_from_run:
        if args.reuse_policy_and_header_from_run != 42740484502:
            raise RuntimeError('Unknown accepted policy/header evidence')
        accepted_sha='dee60eef8395a8a92998f08d7e7eb66701e7febc'
        from relink_verified_simulator import ensure_accepted_commit
        ensure_accepted_commit(app,evidence,accepted_sha)
        changed=git(app,'diff','--name-only',accepted_sha,'--','Anytype/Sources','Modules',
            'AnyTypeTests/Pinkha/TorahNativeUIParityTests.swift',
            'AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift',
            '*.xcconfig','Anytype.xcodeproj').splitlines()
        if any(path.endswith(('.swift','.xcconfig','.pbxproj','.xcscheme')) for path in changed):
            raise RuntimeError('Swift policy/header dependencies changed; cannot reuse their acceptance')
        source=app/'docs/pinkha/torah-integration/evidence/universal-properties-r13/xcode-42740484502'
        prior=json.loads((source/'native-policy-summary.json').read_text())
        if prior['passedTests'] != 19 or prior['failedTests'] or prior['skippedTests']:
            raise RuntimeError('Prior policy acceptance did not pass')
        ui_nodes=json.loads((source/'native-ui-tests.json').read_text())
        def header_passed(value):
            if isinstance(value,dict):
                return (value.get('name')=='testSourceHeaderSelectionAndOverflow()' and value.get('result')=='Passed') or any(header_passed(v) for v in value.values())
            if isinstance(value,list): return any(header_passed(v) for v in value)
            return False
        if not header_passed(ui_nodes): raise RuntimeError('Prior compact-header UI acceptance did not pass')
        policy_reused=19
        header_reused=1
        (evidence/'reused-policy-and-header.json').write_text(json.dumps(dict(status='REUSED_VERIFIED_PASS',
            source_run_id=42740484502, source_sha=accepted_sha, policy_tests=19,
            header_ui_tests=1, unchanged_swift_dependencies=True),indent=2)+'\n')
    else:
        policy_result=evidence/'NativePropertyPolicy.xcresult'
        run_xctest(['xcodebuild','test-without-building','-xctestrun',str(native_run),'-destination',
                 'platform=iOS Simulator,id='+args.simulator_udid,'-parallel-testing-enabled','NO',
                 '-only-testing:AnytypeTests/TorahNativeUIParityTests',
                 '-only-testing:AnytypeTests/TorahCanonicalManifestIsolationTests',
                 '-resultBundlePath',str(policy_result)],app,evidence,policy_result,'native-policy')
        summary=json.loads(subprocess.check_output(['xcrun','xcresulttool','get','test-results','summary','--path',str(policy_result),'--format','json'],text=True))
        (evidence/'native-policy-test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        if count('passedTests')<1 or count('failedTests') or count('skippedTests'): raise RuntimeError('Native property policy tests did not pass without skips')
        policy_passed=count('passedTests')
    # Drive the original app after its real native account/Space preparation.
    # Only fixture IDs/names cross into the test runner; no canonical mirror or
    # authentication secret is supplied to the UI or written into the repository.
    container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',args.simulator_udid,'io.anytype.app','data'],text=True).strip())
    fixture_path=container/'Library/Application Support/pinkha-native-derived-ui-fixture.json'
    fixture=json.loads(fixture_path.read_text())
    if len(set(fixture['documents'].values()))!=3: raise RuntimeError('Native UI fixture must contain three actual writing Objects')
    (evidence/'native-ui-fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
    from rerun_original_ui import ui_only_project, export_ui_console, install_ui_runner
    ui_project=ui_only_project(app)
    command(['xcodebuild','build-for-testing','-project',str(ui_project),
             '-scheme','PinkhaPrebuiltUI','-configuration','Release-Anytype',
             'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED',
             '-destination','platform=iOS Simulator,id='+args.simulator_udid,'-derivedDataPath',str(derived),
             '-parallel-testing-enabled','NO','ENABLE_TESTABILITY=YES','ONLY_ACTIVE_ARCH=YES',
             'SWIFT_OPTIMIZATION_LEVEL=-Onone'],app,evidence)
    ui_configurations=list((derived/'Build/Products').glob('PinkhaPrebuiltUI_*.xctestrun'))
    if len(ui_configurations)!=1: raise RuntimeError('Expected the generated UI-only configuration')
    ui_configuration_source=ui_configurations[0]
    with ui_configuration_source.open('rb') as stream: ui_run=plistlib.load(stream)
    def inject_ui(value):
        if isinstance(value,dict):
            if value.get('BlueprintName')=='PinkhaStage1AcceptanceUITests' or value.get('TestBundlePath','').endswith('PinkhaStage1AcceptanceUITests.xctest'):
                value['UITargetAppPath']=str(derived/'Build/Products/Release-Anytype-iphonesimulator/Anytype.app')
                value['UITargetAppBundleIdentifier']='io.anytype.app'
                environment=value.setdefault('EnvironmentVariables',{})
                environment['PINKHA_NATIVE_UI_DISPOSABLE']='1'
                environment['PINKHA_NATIVE_UI_FIXTURE_JSON']=json.dumps(fixture)
            for child in value.values(): inject_ui(child)
        elif isinstance(value,list):
            for child in value: inject_ui(child)
    inject_ui(ui_run)
    ui_configuration=ui_configuration_source.with_name('PinkhaNativeDerivedUI.xctestrun')
    with ui_configuration.open('wb') as stream: plistlib.dump(ui_run,stream)
    (evidence/'ui-xctestrun-source.json').write_text(json.dumps(ui_run,default=str,indent=2)+'\n')
    install_ui_runner(args.simulator_udid,derived/'Build/Products',app,evidence)
    ui_result=evidence/'NativeDerivedOriginalAppUI.xcresult'
    ui_selection=['-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests']
    if header_reused:
        ui_selection=[
            '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testNativePropertiesPickerChipsSetMembershipAndRelaunch',
            '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testUniversalPageNoteCustomPropertiesAndMixedSet']
    try:
        run_xctest(['xcodebuild','test-without-building','-xctestrun',str(ui_configuration),'-destination',
                 'platform=iOS Simulator,id='+args.simulator_udid,'-parallel-testing-enabled','NO',
                 *ui_selection,
                 '-resultBundlePath',str(ui_result)],app,evidence,ui_result,'native-ui')
    finally:
        export_ui_console(args.simulator_udid, evidence)
    summary=json.loads(subprocess.check_output(['xcrun','xcresulttool','get','test-results','summary','--path',str(ui_result),'--format','json'],text=True))
    (evidence/'native-ui-test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if count('passedTests')!=(2 if header_reused else 3) or count('failedTests') or count('skippedTests'): raise RuntimeError('Original application UI acceptance did not pass without skips')
    ui_passed=count('passedTests')
    command(['xcrun','xcresulttool','export','attachments','--path',str(ui_result),'--output-path',str(evidence/'screenshots')],app,evidence)
    if args.tests_only:
        receipt=dict(status='PASS',app_base_sha=git(app,'rev-parse','HEAD'),heart=heart,
                     simulator_build_mode='RELINK_VERIFIED_SWIFT' if args.relink_verified_swift_from_run else 'XCODE_BUILD',
                     passed_native_tests=native_passed,passed_original_app_ui_tests=ui_passed,
                     passed_policy_and_repository_tests=policy_passed,
                     reused_policy_and_repository_tests=policy_reused,
                     reused_original_app_ui_tests=header_reused,
                     physical_ipad_verified=False,ipa='NOT_BUILT_TESTS_ONLY')
        (evidence/'native-acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n')
        return
    # Reuse dependency checkouts; Xcode keeps each SDK's products separate.
    # The real device build retains the original Release optimization settings.
    device=derived
    command(['xcodebuild','build',*common,'-destination','generic/platform=iOS','-sdk','iphoneos',
             '-derivedDataPath',str(device),'CODE_SIGNING_ALLOWED=NO','CODE_SIGNING_REQUIRED=NO',
             'CODE_SIGN_IDENTITY=','CODE_SIGN_ENTITLEMENTS=','PROVISIONING_PROFILE_SPECIFIER=',
             'AD_HOC_CODE_SIGNING_ALLOWED=YES'],app,evidence)
    built=device/'Build/Products/Release-Anytype-iphoneos/Anytype.app'
    with (built/'Info.plist').open('rb') as stream: info=plistlib.load(stream)
    if 2 not in info['UIDeviceFamily']: raise RuntimeError('Device target lacks iPad support')
    if not contains(built/info['CFBundleExecutable'],marker): raise RuntimeError('Actual app executable lacks custom Heart identity')
    if (built/'_CodeSignature').exists(): raise RuntimeError('Unexpected signature: this route is explicitly unsigned')
    payload=evidence/'ipa/Payload/Anytype.app'
    if payload.exists(): raise RuntimeError('Refusing to reuse a stale IPA payload')
    shutil.copytree(built,payload,symlinks=True)
    info.update(PinkhaNativeHeartPatchSHA256=heart['patch_sha256'],PinkhaNativeAppBaseSHA=git(app,'rev-parse','HEAD'))
    with (payload/'Info.plist').open('wb') as stream: plistlib.dump(info,stream,fmt=plistlib.FMT_BINARY)
    ipa=evidence/'Pinkha-Native-Derived-iPad-Unsigned.ipa'
    # ditto preserves the framework/bundle layout and symlinks expected by iOS.
    command(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(payload.parent),str(ipa)],app,evidence)
    receipt=dict(status='PASS',scope='native product API integration test + unsigned iPad build; physical device and full acceptance remain required',
                 app_base_sha=git(app,'rev-parse','HEAD'),app_branch=git(app,'branch','--show-current'),
                 heart=heart,ipa=str(ipa),ipa_sha256=digest(ipa),passed_native_tests=native_passed,
                 passed_original_app_ui_tests=ui_passed,physical_ipad_verified=False)
    receipt['simulator_swift_optimization']='-Onone'
    (evidence/'native-ipad-build.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(ipa=str(ipa),sha256=receipt['ipa_sha256'])))

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        if '--evidence' in sys.argv:
            target=Path(sys.argv[sys.argv.index('--evidence')+1]).resolve()
            target.mkdir(parents=True,exist_ok=True)
            (target/'native-build-error.json').write_text(json.dumps(dict(
                error_type=type(error).__name__,error=str(error)),indent=2)+'\n')
        raise
