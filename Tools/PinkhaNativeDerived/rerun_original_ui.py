"""Resume only failed original UI cases against the verified cached simulator app.

The unchanged compiled native fixture creates fresh disposable data. Native API,
policy and compact-header acceptance are reused from the recorded source run.
Only the downstream XCTest UI runner is compiled; no app/package target is built.
"""
import argparse
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from build_custom_heart import command, digest, git
from build_native_ipa import run_xctest, test_configuration

VERIFIED_SHA = 'dee60eef8395a8a92998f08d7e7eb66701e7febc'
VERIFIED_RUN = 42740484502


def production_path(path):
    return not path.startswith(('AnytypeTests/', 'AnyTypeTests/', 'PinkhaStage1Acceptance/',
        'Tools/', 'docs/', '.github/', '.agents/', '.claude/', '.codex/')) and not path.endswith('.md')


def ui_only_project(app):
    original = app/'PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj'
    target = original.with_name('PinkhaPrebuiltUI.xcodeproj')
    if target.exists():
        raise RuntimeError('Refusing to overwrite a generated UI project')
    shutil.copytree(original, target)
    project = target/'project.pbxproj'
    source = project.read_text()
    old = 'A1000000000000000000000E /* PBXTargetDependency */,'
    if source.count(old) != 1:
        raise RuntimeError('Unexpected original UI dependency structure')
    source = source.replace(old, '')
    source, count = re.subn(r'TEST_TARGET_NAME = Anytype;', 'TEST_TARGET_NAME = "";', source)
    if count != 4:
        raise RuntimeError('Unexpected UI configurations')
    source = source.replace('TestTargetID = 0303ECFA22D8EDAA005C552B;', '')
    project.write_text(source)
    original_scheme = target/'xcshareddata/xcschemes/PinkhaStage1Acceptance.xcscheme'
    tree = ET.parse(original_scheme)
    root = tree.getroot()
    root.find('BuildAction').set('buildImplicitDependencies', 'NO')
    entries = root.find('BuildAction/BuildActionEntries')
    for entry in list(entries):
        if entry.find('BuildableReference').get('BlueprintName') == 'Anytype':
            entries.remove(entry)
    for parent in root.iter():
        for child in list(parent):
            if child.tag in {'MacroExpansion', 'BuildableProductRunnable'}:
                parent.remove(child)
    for reference in root.iter('BuildableReference'):
        if reference.get('BlueprintName') == 'Anytype':
            raise RuntimeError('App build remains in the UI-only scheme')
        reference.set('ReferencedContainer', 'container:PinkhaPrebuiltUI.xcodeproj')
    tree.write(target/'xcshareddata/xcschemes/PinkhaPrebuiltUI.xcscheme', encoding='utf-8', xml_declaration=True)
    return target


def visit_targets(value, blueprint, action):
    if isinstance(value, dict):
        if value.get('BlueprintName') == blueprint:
            action(value)
        for child in value.values():
            visit_targets(child, blueprint, action)
    elif isinstance(value, list):
        for child in value:
            visit_targets(child, blueprint, action)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app-source', required=True, type=Path)
    parser.add_argument('--simulator-udid', required=True)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    app = args.app_source.resolve()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    derived = evidence/'DerivedData-NativeAcceptance'
    previous = json.loads((derived/'Build/PinkhaSourceInputs.json').read_text())
    if previous['source_sha'] != VERIFIED_SHA:
        raise RuntimeError('Required verified app cache was not restored; no full-build fallback')
    current_paths = subprocess.check_output(['git', '-C', str(app), 'ls-files', '-z']).decode().split('\0')
    current = {p: digest(app/p) for p in current_paths if p and production_path(p) and (app/p).is_file()}
    cached = {p: entry['sha256'] for p, entry in previous['inputs'].items() if production_path(p)}
    if current != cached:
        raise RuntimeError('Production inputs changed; cannot reuse the simulator app')
    receipts = app/f'docs/pinkha/torah-integration/evidence/universal-properties-r13/xcode-{VERIFIED_RUN}'
    for name, expected in [('native-product-summary.json', 1), ('native-policy-summary.json', 19)]:
        summary = json.loads((receipts/name).read_text())
        if summary['passedTests'] != expected or summary['failedTests'] or summary['skippedTests']:
            raise RuntimeError('Required verified acceptance evidence is missing')
    heart = json.loads((app/'Dependencies/Middleware/PinkhaNativeHeartBuild.json').read_text())
    source_heart = json.loads((receipts/'custom-heart-build.json').read_text())
    if heart != source_heart:
        raise RuntimeError('Framework differs from the accepted simulator build')
    products = derived/'Build/Products'
    built_app = products/'Release-Anytype-iphonesimulator/Anytype.app'
    with (built_app/'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    if info['CFBundleIdentifier'] != 'io.anytype.app':
        raise RuntimeError('Unexpected cached application')
    binaries = {p.name: digest(p) for p in built_app.iterdir()
                if p.is_file() and (p.name == info['CFBundleExecutable'] or p.suffix == '.dylib')}
    reuse = dict(status='REUSED_VERIFIED_PASS', source_run_id=VERIFIED_RUN, compiled_source_sha=VERIFIED_SHA,
        current_source_sha=git(app, 'rev-parse', 'HEAD'), identical_production_inputs=len(current),
        app_binaries=binaries, policy_tests='REUSED_VERIFIED_PASS', compact_header_ui='REUSED_VERIFIED_PASS')
    (evidence/'prebuilt-app-reuse.json').write_text(json.dumps(reuse, indent=2)+'\n')
    native = test_configuration(products, 'AnytypeTests')
    with native.open('rb') as stream:
        native_run = plistlib.load(stream)
    visit_targets(native_run, 'AnytypeTests', lambda value: value.setdefault('EnvironmentVariables', {}).update(
        PINKHA_NATIVE_DERIVED_ACCEPTANCE='1'))
    prepared = products/'PinkhaNativeDerived.xctestrun'
    with prepared.open('wb') as stream:
        plistlib.dump(native_run, stream)
    # A new simulator has no account data. Invoke only the already compiled
    # disposable fixture; this is setup for UI, not a rerun of broader validation.
    run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(prepared), '-destination',
        'platform=iOS Simulator,id='+args.simulator_udid, '-parallel-testing-enabled', 'NO',
        '-only-testing:AnytypeTests/TorahNativeDerivedProductIntegrationTests',
        '-resultBundlePath', str(evidence/'FreshUIFixture.xcresult')], app, evidence,
        evidence/'FreshUIFixture.xcresult', 'fixture-preparation')
    container = Path(subprocess.check_output(['xcrun', 'simctl', 'get_app_container', args.simulator_udid,
        'io.anytype.app', 'data'], text=True).strip())
    fixture = json.loads((container/'Library/Application Support/pinkha-native-derived-ui-fixture.json').read_text())
    (evidence/'native-ui-fixture.json').write_text(json.dumps(fixture, indent=2)+'\n')
    project = ui_only_project(app)
    ui_derived = evidence/'DerivedData-UIOnly'
    command(['xcodebuild', 'build-for-testing', '-project', str(project), '-scheme', 'PinkhaPrebuiltUI',
        '-configuration', 'Release-Anytype', '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
        '-derivedDataPath', str(ui_derived), '-parallel-testing-enabled', 'NO',
        'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone'], app, evidence)
    configuration = test_configuration(ui_derived/'Build/Products', 'PinkhaStage1AcceptanceUITests')
    with configuration.open('rb') as stream:
        ui_run = plistlib.load(stream)

    def inject(value):
        value['UITargetAppPath'] = str(built_app)
        value['UITargetAppBundleIdentifier'] = 'io.anytype.app'
        value.setdefault('EnvironmentVariables', {}).update(PINKHA_NATIVE_UI_DISPOSABLE='1',
            PINKHA_NATIVE_UI_FIXTURE_JSON=json.dumps(fixture))
    visit_targets(ui_run, 'PinkhaStage1AcceptanceUITests', inject)
    generated = configuration.with_name('PinkhaNativeDerivedUI.xctestrun')
    with generated.open('wb') as stream:
        plistlib.dump(ui_run, stream)
    result = evidence/'NativeDerivedOriginalAppUI.xcresult'
    ui_failed = True
    try:
        run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(generated), '-destination',
            'platform=iOS Simulator,id='+args.simulator_udid, '-parallel-testing-enabled', 'NO',
            '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testNativePropertiesPickerChipsSetMembershipAndRelaunch',
            '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testUniversalPageNoteCustomPropertiesAndMixedSet',
            '-resultBundlePath', str(result)], app, evidence, result, 'native-ui')
        ui_failed = False
    finally:
        with (evidence/'pinkha-ui-console.log').open('w') as stream:
            subprocess.run(['xcrun', 'simctl', 'spawn', args.simulator_udid, 'log', 'show', '--last', '30m',
                '--style', 'compact', '--info', '--predicate', 'subsystem == "com.anytype.pinkha"'],
                stdout=stream, stderr=subprocess.STDOUT, timeout=60, check=False)
        if ui_failed:
            # Read only this disposable app's existing lookup diagnostics. No
            # credentials, canonical payload or owner account is inspected.
            jobs = subprocess.run(['xcrun', 'simctl', 'spawn', args.simulator_udid, 'launchctl', 'list'],
                capture_output=True, text=True, timeout=15).stdout.splitlines()
            pid = next((line.split()[0] for line in jobs if 'UIKitApplication:io.anytype.app' in line
                        and line.split()[0].isdigit()), None)
            if pid:
                with (evidence/'native-lookup-diagnostics.txt').open('w') as stream:
                    try:
                        subprocess.run(['xcrun', 'lldb', '--batch', '-p', pid,
                            '-o', 'expr -l Swift -- import Anytype',
                            '-o', 'expr -l Swift -- print(Anytype.PinkhaTorahNativePropertyCatalog.shared.lastLookupDiagnostics(spaceId: '+json.dumps(fixture['spaceId'])+'))',
                            '-o', 'expr -l Swift -- print(Anytype.PinkhaTorahPropertyPolicy.shared.internalIdentityStatus(spaceId: '+json.dumps(fixture['spaceId'])+'))',
                            '-o', 'detach'], stdout=stream, stderr=subprocess.STDOUT, timeout=45, check=False)
                    except subprocess.TimeoutExpired:
                        stream.write('\nRead-only debugger diagnostics timed out.\n')
    summary = json.loads((evidence/'native-ui-summary.json').read_text())
    if summary['passedTests'] != 2 or summary['failedTests'] or summary['skippedTests']:
        raise RuntimeError('The two failed original UI scenarios have not passed')
    if binaries != {name: digest(built_app/name) for name in binaries}:
        raise RuntimeError('A reused app executable changed during the UI-only build')
    (evidence/'native-acceptance.json').write_text(json.dumps(dict(status='PASS', app_reuse=reuse,
        passed_original_app_ui_tests=2, reused_original_app_ui_tests=1,
        reused_native_api_tests=1, reused_policy_tests=19, physical_ipad_verified=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
