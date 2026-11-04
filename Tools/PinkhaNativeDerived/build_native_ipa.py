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
import zipfile

from build_custom_heart import command, contains, digest, git

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
    command(['xcodebuild','build-for-testing',*common,'-destination','platform=iOS Simulator,id='+args.simulator_udid,
             '-derivedDataPath',str(derived),'-parallel-testing-enabled','NO','ENABLE_TESTABILITY=YES','ONLY_ACTIVE_ARCH=YES',
             'SWIFT_OPTIMIZATION_LEVEL=-Onone'],app,evidence)
    runs=list((derived/'Build/Products').glob('*.xctestrun'))
    if len(runs)!=1: raise RuntimeError('Expected one native test-host configuration')
    with runs[0].open('rb') as stream: run=plistlib.load(stream)
    def inject(value):
        if isinstance(value,dict):
            if value.get('BlueprintName')=='AnytypeTests' or value.get('TestBundlePath','').endswith('AnytypeTests.xctest'):
                value.setdefault('EnvironmentVariables',{})['PINKHA_NATIVE_DERIVED_ACCEPTANCE']='1'
            for child in value.values(): inject(child)
        elif isinstance(value,list):
            for child in value: inject(child)
    inject(run)
    native_run=runs[0].with_name('PinkhaNativeDerived.xctestrun')
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
    # Drive the original app after its real native account/Space preparation.
    # Only fixture IDs/names cross into the test runner; no canonical mirror or
    # authentication secret is supplied to the UI or written into the repository.
    container=Path(subprocess.check_output(['xcrun','simctl','get_app_container',args.simulator_udid,'io.anytype.app','data'],text=True).strip())
    fixture_path=container/'Library/Application Support/pinkha-native-derived-ui-fixture.json'
    fixture=json.loads(fixture_path.read_text())
    if len(set(fixture['documents'].values()))!=3: raise RuntimeError('Native UI fixture must contain three actual writing Objects')
    (evidence/'native-ui-fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
    command(['xcodebuild','build-for-testing','-workspace','PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace',
             '-scheme','PinkhaStage1Acceptance','-configuration','Release-Anytype',
             'OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED',
             '-destination','platform=iOS Simulator,id='+args.simulator_udid,'-derivedDataPath',str(derived),
             '-parallel-testing-enabled','NO','ENABLE_TESTABILITY=YES','ONLY_ACTIVE_ARCH=YES',
             'SWIFT_OPTIMIZATION_LEVEL=-Onone'],app,evidence)
    ui_runs=[path for path in (derived/'Build/Products').glob('*.xctestrun') if 'PinkhaStage1Acceptance' in path.name]
    if len(ui_runs)!=1: raise RuntimeError('Expected the real application UI-test configuration')
    with ui_runs[0].open('rb') as stream: ui_run=plistlib.load(stream)
    def inject_ui(value):
        if isinstance(value,dict):
            if value.get('BlueprintName')=='PinkhaStage1AcceptanceUITests' or value.get('TestBundlePath','').endswith('PinkhaStage1AcceptanceUITests.xctest'):
                environment=value.setdefault('EnvironmentVariables',{})
                environment['PINKHA_NATIVE_UI_DISPOSABLE']='1'
                environment['PINKHA_NATIVE_UI_FIXTURE_JSON']=json.dumps(fixture)
            for child in value.values(): inject_ui(child)
        elif isinstance(value,list):
            for child in value: inject_ui(child)
    inject_ui(ui_run)
    ui_configuration=ui_runs[0].with_name('PinkhaNativeDerivedUI.xctestrun')
    with ui_configuration.open('wb') as stream: plistlib.dump(ui_run,stream)
    ui_result=evidence/'NativeDerivedOriginalAppUI.xcresult'
    run_xctest(['xcodebuild','test-without-building','-xctestrun',str(ui_configuration),'-destination',
             'platform=iOS Simulator,id='+args.simulator_udid,'-parallel-testing-enabled','NO',
             '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests',
             '-resultBundlePath',str(ui_result)],app,evidence,ui_result,'native-ui')
    summary=json.loads(subprocess.check_output(['xcrun','xcresulttool','get','test-results','summary','--path',str(ui_result),'--format','json'],text=True))
    (evidence/'native-ui-test-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if count('passedTests')<1 or count('failedTests') or count('skippedTests'): raise RuntimeError('Original application UI acceptance did not pass without skips')
    ui_passed=count('passedTests')
    command(['xcrun','xcresulttool','export','attachments','--path',str(ui_result),'--output-path',str(evidence/'screenshots')],app,evidence)
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

if __name__=='__main__': main()
