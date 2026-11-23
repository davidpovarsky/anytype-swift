"""One focused native prerequisite for the reproduced Stage B link ownership conflict."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import time
import traceback
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pbx_source import render, loads, require

BRANCH = 'codex/otzaria-original-editor-shared-runtime-20261123'
NAME = 'SharedFirebaseProbe'
RUNTIME = 'OriginalEditorSharedFirebase'
BUNDLE = 'org.otzaria.acceptance.shared-firebase-runtime'
CLASSES = ['FIRApp', 'FIRInstallations', 'FIRMessaging', 'FBLPromise', 'GDTCORTransport']
ORIGINAL_TREES = {
    'Anytype/Sources': '7f60c27ac32ea66f889abd70edbb1cab1778f0a6',
    'Anytype/Resources': '0827010674c089cfe9846e592e1d801e9d3f7a9b',
    'Modules': 'a8a4b7688ea6295ae6c6b2f3baf90e18ab268e1b',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def project(directory, source):
    require(not directory.exists(), 'Probe project already exists')
    directory.mkdir(parents=True)
    shutil.copytree(source / 'Sources', directory / 'ProviderPackage/Sources')
    shutil.copyfile(source / 'Package.swift', directory / 'ProviderPackage/Package.swift')
    shutil.copyfile(source / 'ProbeApp.swift', directory / 'ProbeApp.swift')
    objects = {}

    def add(name, value):
        ident = hashlib.sha256(('SharedFirebaseProbe:' + name).encode()).hexdigest()[:24].upper()
        require(ident not in objects, 'Object identity collision')
        objects[ident] = value
        return ident

    product = add('App', {'isa': 'PBXFileReference', 'explicitFileType': 'wrapper.application',
                         'path': NAME + '.app', 'sourceTree': 'BUILT_PRODUCTS_DIR', 'includeInIndex': '0'})
    src = add('Source', {'isa': 'PBXFileReference', 'lastKnownFileType': 'sourcecode.swift',
                         'path': 'ProbeApp.swift', 'sourceTree': '<group>'})
    source_build = add('SourceBuild', {'isa': 'PBXBuildFile', 'fileRef': src})
    pkg = add('Package', {'isa': 'XCLocalSwiftPackageReference', 'relativePath': 'ProviderPackage'})
    dependency = add('Runtime', {'isa': 'XCSwiftPackageProductDependency',
                                'package': pkg, 'productName': RUNTIME})
    linked = add('RuntimeLink', {'isa': 'PBXBuildFile', 'productRef': dependency})
    runtime_file = add('RuntimeFile', {'isa': 'PBXFileReference', 'lastKnownFileType': 'wrapper.framework',
                                      'path': 'PackageFrameworks/' + RUNTIME + '.framework',
                                      'sourceTree': 'BUILT_PRODUCTS_DIR'})
    embedded = add('RuntimeEmbed', {'isa': 'PBXBuildFile', 'fileRef': runtime_file})
    phases = [
        add('Sources', {'isa': 'PBXSourcesBuildPhase', 'buildActionMask': '2147483647',
                        'files': [source_build], 'runOnlyForDeploymentPostprocessing': '0'}),
        add('Frameworks', {'isa': 'PBXFrameworksBuildPhase', 'buildActionMask': '2147483647',
                           'files': [linked], 'runOnlyForDeploymentPostprocessing': '0'}),
        add('Resources', {'isa': 'PBXResourcesBuildPhase', 'buildActionMask': '2147483647',
                          'files': [], 'runOnlyForDeploymentPostprocessing': '0'}),
    ]
    # The first real build produced the signed framework at PackageFrameworks,
    # but Xcode did not infer an embed phase for this generated project.
    # Copy its complete bytes; no RemoveHeadersOnCopy or re-signing adapter.
    phases.append(add('EmbedRuntime', {'isa': 'PBXCopyFilesBuildPhase', 'buildActionMask': '2147483647',
                                      'dstPath': '', 'dstSubfolderSpec': '10', 'files': [embedded],
                                      'name': 'Embed exact shared runtime',
                                      'runOnlyForDeploymentPostprocessing': '0'}))
    settings = {
        'PRODUCT_NAME': NAME, 'PRODUCT_BUNDLE_IDENTIFIER': BUNDLE,
        'GENERATE_INFOPLIST_FILE': 'NO', 'INFOPLIST_FILE': 'Info.plist',
        'IPHONEOS_DEPLOYMENT_TARGET': '27.0', 'SDKROOT': 'iphoneos',
        'SUPPORTED_PLATFORMS': 'iphoneos iphonesimulator', 'SWIFT_VERSION': '5.0',
        'SWIFT_OPTIMIZATION_LEVEL': '-Onone', 'DEAD_CODE_STRIPPING': 'NO', 'ENABLE_DEBUG_DYLIB': 'NO',
        'TARGETED_DEVICE_FAMILY': '1,2', 'ENABLE_USER_SCRIPT_SANDBOXING': 'YES',
        'CODE_SIGN_STYLE': 'Automatic', 'CODE_SIGN_IDENTITY': '-',
        'CODE_SIGNING_ALLOWED': 'YES', 'CODE_SIGNING_REQUIRED': 'YES',
        'DEVELOPMENT_TEAM': '', 'PROVISIONING_PROFILE_SPECIFIER': '',
        'LD_RUNPATH_SEARCH_PATHS': ['$(inherited)', '@executable_path/Frameworks'],
    }
    config = add('Debug', {'isa': 'XCBuildConfiguration', 'name': 'Debug', 'buildSettings': settings})
    configs = add('TargetConfigs', {'isa': 'XCConfigurationList', 'buildConfigurations': [config],
                                    'defaultConfigurationName': 'Debug', 'defaultConfigurationIsVisible': '0'})
    target = add('Target', {'isa': 'PBXNativeTarget', 'name': NAME, 'productName': NAME,
                           'productReference': product, 'productType': 'com.apple.product-type.application',
                           'buildConfigurationList': configs, 'buildPhases': phases, 'buildRules': [],
                           'dependencies': [], 'packageProductDependencies': [dependency]})
    products = add('Products', {'isa': 'PBXGroup', 'children': [product], 'name': 'Products', 'sourceTree': '<group>'})
    group = add('Main', {'isa': 'PBXGroup', 'children': [src, products, runtime_file], 'sourceTree': '<group>'})
    pc = add('ProjectDebug', {'isa': 'XCBuildConfiguration', 'name': 'Debug', 'buildSettings': {}})
    pcs = add('ProjectConfigs', {'isa': 'XCConfigurationList', 'buildConfigurations': [pc],
                                 'defaultConfigurationName': 'Debug', 'defaultConfigurationIsVisible': '0'})
    root = add('Project', {'isa': 'PBXProject', 'compatibilityVersion': 'Xcode 15.0',
                          'buildConfigurationList': pcs, 'developmentRegion': 'en',
                          'knownRegions': ['en', 'Base'], 'mainGroup': group, 'productRefGroup': products,
                          'projectDirPath': '', 'projectRoot': '', 'targets': [target], 'packageReferences': [pkg]})
    value = {'archiveVersion': '1', 'classes': {}, 'objectVersion': '60', 'objects': objects, 'rootObject': root}
    pbx = '// !$*UTF8*$!\n' + render(value) + '\n'
    require(loads(pbx) == value, 'Generated project does not round-trip')
    out = directory / (NAME + '.xcodeproj')
    out.mkdir()
    (out / 'project.pbxproj').write_text(pbx)
    scheme = ET.Element('Scheme', LastUpgradeVersion='2700', version='1.3')
    action = ET.SubElement(scheme, 'BuildAction', parallelizeBuildables='YES', buildImplicitDependencies='YES')
    entry = ET.SubElement(ET.SubElement(action, 'BuildActionEntries'), 'BuildActionEntry',
                          buildForTesting='NO', buildForRunning='YES', buildForProfiling='NO',
                          buildForArchiving='NO', buildForAnalyzing='YES')
    ET.SubElement(entry, 'BuildableReference', BuildableIdentifier='primary', BlueprintIdentifier=target,
                  BuildableName=NAME + '.app', BlueprintName=NAME,
                  ReferencedContainer='container:' + NAME + '.xcodeproj')
    shared = out / 'xcshareddata/xcschemes'
    shared.mkdir(parents=True)
    (shared / (NAME + '.xcscheme')).write_bytes(ET.tostring(scheme))
    with (directory / 'Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleIdentifier': '$(PRODUCT_BUNDLE_IDENTIFIER)',
                      'CFBundleExecutable': '$(EXECUTABLE_NAME)', 'CFBundleName': NAME,
                      'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
                      'CFBundleShortVersionString': '1.0', 'LSRequiresIPhoneOS': True,
                      'UILaunchScreen': {}}, stream)
    return out


def select_ipad_runtime(runtimes):
    eligible = []
    for runtime in runtimes:
        version = runtime.get('version', '').split('.')
        pads = [d for d in runtime.get('supportedDeviceTypes', []) if d.get('productFamily') == 'iPad']
        if (runtime.get('isAvailable') and 'arm64' in runtime.get('supportedArchitectures', [])
                and runtime.get('identifier', '').startswith('com.apple.CoreSimulator.SimRuntime.iOS-27-')
                and version and version[0] == '27' and all(v.isdigit() for v in version) and pads):
            eligible.append((tuple(int(v) for v in version), runtime, sorted(pads, key=lambda d: d['identifier'])))
    require(eligible, 'No observed available arm64 iOS 27 runtime supports iPad')
    newest = max(item[0] for item in eligible)
    chosen = [item for item in eligible if item[0] == newest]
    require(len(chosen) == 1, 'Ambiguous highest iPad-capable iOS 27 runtime')
    return chosen[0][1], chosen[0][2][0]


def execute(args, receipt):
    root, work, evidence = args.root.resolve(), args.work.resolve(), args.evidence.resolve()
    require(work.is_relative_to(root / 'build') and evidence.is_relative_to(root / 'build'),
            'Work and evidence must be under the owned build directory')
    require(not work.exists(), 'Refusing reused build output')
    evidence.mkdir(parents=True, exist_ok=True)
    head = git(root, 'rev-parse', 'HEAD')
    require(os.environ.get('GITHUB_REPOSITORY') == 'davidpovarsky/anytype-swift'
            and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF') == 'refs/heads/' + BRANCH
            and os.environ.get('GITHUB_SHA') == head
            and os.environ.get('GITHUB_WORKFLOW_REF') == 'davidpovarsky/anytype-swift/.github/workflows/pinkha-original-editor-shared-runtime.yml@refs/heads/' + BRANCH,
            'Wrong actual source-bound push')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all',
                    '--', 'Tools/OriginalEditor/SharedRuntime', '.github/workflows/pinkha-original-editor-shared-runtime.yml'),
            'Probe source changed')
    trees = {p: git(root, 'rev-parse', 'HEAD:' + p) for p in ORIGINAL_TREES}
    require(trees == ORIGINAL_TREES, 'Original implementation or resources changed')
    source = root / 'Tools/OriginalEditor/SharedRuntime'
    inputs = {p.relative_to(root).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()}
    receipt.update(source_sha=head, run_id=os.environ['GITHUB_RUN_ID'],
                   run_attempt=os.environ['GITHUB_RUN_ATTEMPT'], original_trees=trees, source_inputs=inputs)
    write(evidence / 'source.json', receipt)
    work.mkdir(parents=True)
    commands = []

    def command(name, argv, timeout=120, env=None):
        record = {'name': name, 'arguments': [str(v) for v in argv], 'timeout_seconds': timeout,
                  'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        commands.append(record)
        write(evidence / 'commands.json', commands)
        log = evidence / (name + '.log')
        with log.open('w') as stream:
            try:
                result = subprocess.run(record['arguments'], cwd=root, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, text=True, timeout=timeout)
                record['returncode'] = result.returncode
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                raise
            finally:
                record['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                record['log_sha256'] = digest(log)
                write(evidence / 'commands.json', commands)
        require(result.returncode == 0, 'Native command failed: ' + name)
        return log.read_text()

    command('xcode-version', ['xcodebuild', '-version'])
    require('Xcode 27' in (evidence / 'xcode-version.log').read_text(), 'Xcode 27 required')
    project_path = project(work / 'consumer', source)
    shutil.copyfile(project_path / 'project.pbxproj', evidence / 'project.pbxproj')
    common = ['xcodebuild', '-project', project_path, '-scheme', NAME, '-configuration', 'Debug',
              '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', work / 'DerivedData',
              '-clonedSourcePackagesDirPath', work / 'SourcePackages']
    receipt['phase'] = 'RESOLVE_EXACT_SHARED_DEPENDENCIES'
    command('resolve', [*common, '-resolvePackageDependencies'], 900)
    resolved = project_path / 'project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    require(resolved.is_file(), 'Actual resolver did not retain Package.resolved')
    shutil.copyfile(resolved, evidence / 'Package.resolved')
    pins = {pin['identity'].lower(): pin for pin in json.loads(resolved.read_text())['pins']}
    contract = json.loads((source / 'dependencies.json').read_text())
    require(set(contract['dependencies']) <= set(pins), 'Resolved graph misses a shared root')
    for identity, expected in contract['dependencies'].items():
        require(pins[identity]['state'] == {'revision': expected['revision'], 'version': expected['version']},
                'Resolved shared source/version differs: ' + identity)
    observed = {}
    for checkout in (work / 'SourcePackages/checkouts').iterdir():
        if checkout.is_dir() and (checkout / '.git').exists():
            revision = git(checkout, 'rev-parse', 'HEAD')
            require(not git(checkout, 'diff', '--name-only', 'HEAD'), 'Dependency source changed: ' + checkout.name)
            observed[checkout.name] = revision
    require({d['revision'] for d in contract['dependencies'].values()} <= set(observed.values()),
            'Actual checkouts do not contain every exact shared source')
    write(evidence / 'dependency-checkouts.json', observed)
    receipt['phase'] = 'REAL_SHARED_RUNTIME_BUILD_AND_CONSUMER_LINK'
    command('build', [*common, '-disableAutomaticPackageResolution', '-onlyUsePackageVersionsFromResolvedFile',
                      'DEAD_CODE_STRIPPING=NO', 'ARCHS=arm64', 'ONLY_ACTIVE_ARCH=YES', 'build'], 1200)
    require(digest(resolved) == digest(evidence / 'Package.resolved'), 'Build changed resolved inputs')
    app = work / 'DerivedData/Build/Products/Debug-iphonesimulator' / (NAME + '.app')
    framework = app / 'Frameworks' / (RUNTIME + '.framework')
    require(app.is_dir() and framework.is_dir(), 'Real dynamic package was not embedded')
    binary = framework / RUNTIME
    command('runtime-load-commands', ['xcrun', 'otool', '-L', binary])
    command('consumer-load-commands', ['xcrun', 'otool', '-L', app / NAME])
    runtime_symbols = set(command('runtime-symbols', ['xcrun', 'nm', '-gjU', binary]).splitlines())
    app_symbols = set(command('consumer-symbols', ['xcrun', 'nm', '-gjU', app / NAME]).splitlines())
    expected = {'_OBJC_CLASS_$_' + name for name in CLASSES}
    require(expected <= runtime_symbols, 'Dynamic provider lacks required original implementation classes')
    require(not expected & app_symbols, 'Consumer statically duplicated shared implementation classes')
    require('@rpath/' + RUNTIME + '.framework/' + RUNTIME in (evidence / 'consumer-load-commands.log').read_text(),
            'Consumer is not linked to the actual shared dynamic provider')
    command('signature', ['codesign', '--verify', '--deep', '--strict', app])
    receipt['binary_identity'] = {RUNTIME: digest(binary), NAME: digest(app / NAME)}
    # Preserve this signed build before runtime; any subsequent runtime-only
    # continuation must reuse these exact bytes instead of rebuilding accepted code.
    archive = evidence / 'shared-runtime-app.zip'
    command('retain-signed-app', ['ditto', '-c', '-k', '--keepParent', str(app), str(archive)], 120)
    app_inventory = {p.relative_to(app).as_posix(): {'bytes': p.stat().st_size, 'sha256': digest(p)}
                     for p in sorted(app.rglob('*')) if p.is_file()}
    write(evidence / 'retained-native-products.json', {
        'schema': 1, 'status': 'BUILD_LINK_EMBED_SIGNATURE_AND_DEFINITIONS_PASS_RUNTIME_NOT_RUN',
        'source_sha': head, 'run_id': os.environ['GITHUB_RUN_ID'],
        'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'], 'source_inputs': inputs,
        'binary_identity': receipt['binary_identity'], 'app_inventory': app_inventory,
        'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
        'stageb_qualified': False,
    })
    receipt['phase'] = 'SINGLE_PROVIDER_RUNTIME_OBSERVATION'
    runtimes = json.loads(command('runtimes', ['xcrun', 'simctl', 'list', 'runtimes', '--json']))['runtimes']
    selected, device_type = select_ipad_runtime(runtimes)
    runtime = selected['identifier']
    receipt['selected_runtime'] = {k: selected[k] for k in ['identifier', 'version', 'buildversion', 'supportedArchitectures']}
    receipt['selected_device_type'] = device_type
    write(evidence / 'selected-simulator.json', {'runtime': receipt['selected_runtime'], 'device_type': device_type})
    udid = command('create', ['xcrun', 'simctl', 'create',
                             'OtzariaSharedFirebase-' + os.environ['GITHUB_RUN_ID'],
                             device_type['identifier'], runtime]).strip()
    receipt['owned_simulator'] = udid
    try:
        command('boot', ['xcrun', 'simctl', 'boot', udid])
        command('bootstatus', ['xcrun', 'simctl', 'bootstatus', udid, '-b'], 180)
        command('install', ['xcrun', 'simctl', 'install', udid, app], 180)
        nonce = str(uuid.uuid4())
        child = os.environ.copy()
        child['SIMCTL_CHILD_SHARED_RUNTIME_PROBE_NONCE'] = nonce
        command('launch', ['xcrun', 'simctl', 'launch', udid, BUNDLE], 60, child)
        container = Path(command('container', ['xcrun', 'simctl', 'get_app_container', udid, BUNDLE, 'data']).strip())
        result = container / 'Documents/shared-runtime-result.json'
        deadline = time.monotonic() + 30
        while not result.is_file() and time.monotonic() < deadline:
            time.sleep(0.5)
        require(result.is_file(), 'Actual app did not emit runtime observation')
        shutil.copyfile(result, evidence / result.name)
        actual = json.loads(result.read_text())
        require(actual['status'] == 'PASS_SINGLE_LOADED_PROVIDER' and actual['nonce'] == nonce
                and type(actual['process_id']) is int and actual['process_id'] > 0,
                'Actual shared-provider runtime observation did not pass')
        require(set(actual['providers']) == set(CLASSES)
                and all(len(paths) == 1 and paths[0].endswith('/Frameworks/' + RUNTIME + '.framework/' + RUNTIME)
                        for paths in actual['providers'].values()), 'Runtime class owner is not unique')
        receipt['runtime'] = actual
    finally:
        for action in ['shutdown', 'delete']:
            try:
                command(action, ['xcrun', 'simctl', action, udid], 60)
            except Exception as cleanup:
                receipt.setdefault('cleanup_errors', []).append(str(cleanup))
    require(inputs == {p.relative_to(root).as_posix(): digest(p) for p in source.rglob('*') if p.is_file()},
            'Probe source changed during native execution')
    receipt.update(status='PASS_SHARED_FIREBASE_RUNTIME_BOUNDARY', phase='COMPLETE')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 1, 'status': 'FAIL', 'phase': 'SOURCE_ADMISSION',
               'original_editor_qualified': False, 'stageb_qualified': False}
    try:
        execute(args, receipt)
        return 0
    except BaseException as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        traceback.print_exc()
        return 1
    finally:
        write(args.evidence / 'RESULT.json', receipt)


if __name__ == '__main__':
    raise SystemExit(main())
