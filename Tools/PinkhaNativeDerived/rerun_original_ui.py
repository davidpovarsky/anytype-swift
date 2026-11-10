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
import sys
import xml.etree.ElementTree as ET

from build_custom_heart import command, digest, git
from build_native_ipa import run_xctest, test_configuration

VERIFIED_SHA = '8258841dab25764c0d9cfe3bee7eec566995f79d'
VERIFIED_RUN = 42786374694


def production_path(path):
    return not path.startswith(('AnytypeTests/', 'AnyTypeTests/', 'PinkhaStage1Acceptance/', 'Dependencies/Middleware/Lib.xcframework/',
        'docs/', '.github/', '.agents/', '.claude/', '.codex/', 'Tools/PinkhaNativeDerived/')) and not path.endswith('.md')


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
    # Even an unused subproject file/scheme causes SwiftPM to resolve the app's
    # binary dependencies. This generated copy is an independent UI runner.
    for section in ['PBXContainerItemProxy', 'PBXTargetDependency']:
        source, count = re.subn(r'/\* Begin '+section+r' section \*/.*?/\* End '+section+r' section \*/\n',
                                '', source, flags=re.S)
        if count != 1:
            raise RuntimeError('Unexpected original UI proxy/dependency section')
    source, count = re.subn(r'^.*A10000000000000000000004 /\* Anytype\.xcodeproj \*/.*\n', '', source, flags=re.M)
    if count != 2 or 'Anytype.xcodeproj' in source:
        raise RuntimeError('Unexpected original UI subproject references')
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
    original_scheme.unlink()  # Only the generated copy; the source scheme is untouched.
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


def export_ui_console(simulator, evidence):
    with (evidence/'pinkha-ui-console.log').open('w') as stream:
        try:
            subprocess.run(['xcrun', 'simctl', 'spawn', simulator, 'log', 'show', '--last', '30m',
                '--style', 'compact', '--info', '--predicate', 'subsystem == "com.anytype.pinkha"'],
                stdout=stream, stderr=subprocess.STDOUT, timeout=60, check=False)
        except subprocess.TimeoutExpired:
            stream.write('\nPassive console export timed out.\n')


def install_ui_runner(simulator, products, app, evidence):
    """Register the actual built XCTest runner before Xcode asks FrontBoard to launch it."""
    runner = products/'Release-Anytype-iphonesimulator/PinkhaStage1AcceptanceUITests-Runner.app'
    with (runner/'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    identifier = info['CFBundleIdentifier']
    if identifier != 'com.gloiiire.PinkhaStage1AcceptanceUITests.xctrunner':
        raise RuntimeError('Unexpected real UI runner bundle identifier: '+identifier)
    command(['xcrun','simctl','install',simulator,str(runner)],app,evidence)
    registered = subprocess.check_output(['xcrun','simctl','get_app_container',simulator,
                                         identifier,'app'],text=True).strip()
    if not registered:
        raise RuntimeError('The UI runner was not registered in the disposable simulator')
    (evidence/'ui-runner-installation.json').write_text(json.dumps(dict(
        status='REGISTERED',bundle_identifier=identifier,built_runner=str(runner),
        registered_runner=registered),indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--app-source', required=True, type=Path)
    parser.add_argument('--simulator-udid', required=True)
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    app = args.app_source.resolve()
    if git(app, 'branch', '--show-current') != 'codex/torah-native-derived-properties-20261103':
        raise RuntimeError('Wrong application branch')
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
        differences = sorted(p for p in set(current) | set(cached) if current.get(p) != cached.get(p))
        raise RuntimeError('Production inputs changed; cannot reuse the simulator app: '+', '.join(differences))
    receipts = app/f'docs/pinkha/torah-integration/evidence/universal-properties-r14/xcode-{VERIFIED_RUN}/app'
    policy_receipts = app/'docs/pinkha/torah-integration/evidence/universal-properties-r13/xcode-42740484502'
    for location, name, expected in [(receipts,'native-product-summary.json',1),
                                     (policy_receipts,'native-policy-summary.json',19)]:
        summary = json.loads((location/name).read_text())
        if summary['passedTests'] != expected or summary['failedTests'] or summary['skippedTests']:
            raise RuntimeError('Required verified acceptance evidence is missing')
    retained_set = app/'docs/pinkha/torah-integration/evidence/universal-properties-r14/xcode-42830150133/app'
    def has_mixed_set_pass(value):
        if isinstance(value, dict):
            return (value.get('nodeIdentifier') == 'PinkhaNativeDerivedAcceptanceUITests/testRemainingUniversalTypePickersAndMixedSet()'
                    and value.get('result') == 'Passed') or any(has_mixed_set_pass(v) for v in value.values())
        return isinstance(value, list) and any(has_mixed_set_pass(v) for v in value)
    if not has_mixed_set_pass(json.loads((retained_set/'native-ui-tests.json').read_text())):
        raise RuntimeError('The unchanged mixed-Set UI case has no actual passing receipt')
    source_heart = json.loads((app/'docs/pinkha/torah-integration/evidence/universal-properties-r14/xcode-42760706087/heart/custom-heart-build.json').read_text())
    patch = app/'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14/native-heart-integration.patch'
    if digest(patch) != source_heart['patch_sha256']:
        raise RuntimeError('Heart patch differs from the accepted simulator build')
    installed = app/'Dependencies/Middleware/PinkhaNativeHeartBuild.json'
    if installed.exists() and json.loads(installed.read_text()) != source_heart:
        raise RuntimeError('Installed framework differs from the accepted simulator build')
    # The accepted app already contains Heart. UI-only work needs neither a
    # second framework download/verification nor another framework upload.
    heart_evidence = evidence.parent/'heart'
    heart_evidence.mkdir(parents=True, exist_ok=True)
    (heart_evidence/'custom-heart-build.json').write_text(json.dumps(source_heart, indent=2)+'\n')
    products = derived/'Build/Products'
    built_app = products/'Release-Anytype-iphonesimulator/Anytype.app'
    with (built_app/'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    if info['CFBundleIdentifier'] != 'io.anytype.app':
        raise RuntimeError('Unexpected cached application')
    link = json.loads((receipts/'relinked-simulator.json').read_text())
    runtime = 'Frameworks/ProtobufMessages.framework/ProtobufMessages'
    if (link['native_patch_sha256'] != source_heart['patch_sha256']
            or digest(built_app/runtime) != link['embedded_runtime_sha256'][runtime]
            or not link['actual_runtime_marker_present']):
        raise RuntimeError('The cached app does not contain the accepted new runtime')
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
    ui_derived = derived
    configurations = list((ui_derived/'Build/Products').glob('PinkhaPrebuiltUI_*.xctestrun'))
    ui_sources = [p for p in current_paths if p.startswith('PinkhaStage1Acceptance/') and (app/p).is_file()]
    same_ui = ui_sources and all(previous['inputs'].get(p,{}).get('sha256')==digest(app/p) for p in ui_sources)
    if len(configurations)==1 and same_ui:
        (evidence/'ui-runner-reuse.json').write_text(json.dumps(dict(
            status='REUSED_COMPILED_UI_RUNNER',source_run_id=VERIFIED_RUN,
            unchanged_inputs={p:digest(app/p) for p in ui_sources}),indent=2)+'\n')
    else:
        project = ui_only_project(app)
        command(['xcodebuild', 'build-for-testing', '-project', str(project), '-scheme', 'PinkhaPrebuiltUI',
            '-configuration', 'Release-Anytype', '-destination', 'platform=iOS Simulator,id='+args.simulator_udid,
            '-derivedDataPath', str(ui_derived), '-parallel-testing-enabled', 'NO',
            'ONLY_ACTIVE_ARCH=YES', 'SWIFT_OPTIMIZATION_LEVEL=-Onone'], app, evidence)
        configurations = list((ui_derived/'Build/Products').glob('PinkhaPrebuiltUI_*.xctestrun'))
    if len(configurations) != 1:
        raise RuntimeError('Expected the current generated UI-only configuration')
    configuration = configurations[0]
    with configuration.open('rb') as stream:
        ui_run = plistlib.load(stream)
    (evidence/'ui-xctestrun-source.json').write_text(json.dumps(ui_run,default=str,indent=2)+'\n')

    def inject(value):
        value['UITargetAppPath'] = str(built_app)
        value['UITargetAppBundleIdentifier'] = 'io.anytype.app'
        value.setdefault('EnvironmentVariables', {}).update(PINKHA_NATIVE_UI_DISPOSABLE='1',
            PINKHA_NATIVE_UI_FIXTURE_JSON=json.dumps(fixture))
    visit_targets(ui_run, 'PinkhaStage1AcceptanceUITests', inject)
    generated = configuration.with_name('PinkhaNativeDerivedUI.xctestrun')
    with generated.open('wb') as stream:
        plistlib.dump(ui_run, stream)
    install_ui_runner(args.simulator_udid,products,app,evidence)
    result = evidence/'NativeDerivedOriginalAppUI.xcresult'
    try:
        run_xctest(['xcodebuild', 'test-without-building', '-xctestrun', str(generated), '-destination',
            'platform=iOS Simulator,id='+args.simulator_udid, '-parallel-testing-enabled', 'NO',
            '-only-testing:PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testRemainingNativeSourceFilterEditing',
            '-resultBundlePath', str(result)], app, evidence, result, 'native-ui')
    finally:
        # Keep compact proof and actionable failures in the job log even when
        # GitHub's artifact service is temporarily unavailable.
        for name in ['native-ui-summary.json', 'prebuilt-app-reuse.json']:
            receipt = evidence/name
            if receipt.exists():
                print(name+': '+receipt.read_text(), flush=True)
        for log in sorted(evidence.glob('command-*.log')):
            lines = log.read_text(errors='replace').splitlines()
            for index, line in enumerate(lines):
                if 'Native Set fixture picker:' in line or 'Native picker failure hierarchy:' in line or 'Native Set settings hierarchy:' in line:
                    print('\n'.join(lines[index:index+90]), flush=True)
        export_ui_console(args.simulator_udid, evidence)
    summary = json.loads((evidence/'native-ui-summary.json').read_text())
    if summary['passedTests'] != 1 or summary['failedTests'] or summary['skippedTests']:
        raise RuntimeError('The remaining native source-filter UI scenario has not passed')
    if binaries != {name: digest(built_app/name) for name in binaries}:
        raise RuntimeError('A reused app executable changed during the UI-only build')
    (evidence/'native-acceptance.json').write_text(json.dumps(dict(status='PASS', app_reuse=reuse,
        passed_original_app_ui_tests=1, reused_original_app_ui_tests=2,
        reused_mixed_set_ui_run=42830150133,
        retained_ui_phases=json.loads((app/'docs/pinkha/torah-integration/evidence/universal-properties-r14/retained-ui-phases.json').read_text()),
        reused_native_api_tests=1, reused_policy_tests=19, physical_ipad_verified=False), indent=2)+'\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--evidence' in sys.argv:
            evidence = Path(sys.argv[sys.argv.index('--evidence')+1]).resolve()
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence/'ui-resume-error.json').write_text(json.dumps(dict(
                error_type=type(error).__name__, error=str(error)), indent=2)+'\n')
        raise
