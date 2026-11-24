#!/usr/bin/env python3
"""Build one actual Release SDK variant using an externally owned controller.

The original qualified source and Import ABI remain owned by their original
Simulator execution. This invocation produces new compiler, API and platform
evidence, plus actual EN/HE resource observations only on Simulator.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_contract import (CONFIGURATION, DEVICE_PASS, SIMULATOR_PASS, REPOSITORY,
    admit_original_owner, controller_observation, create_execution, current_build_context,
    digest, identity, require, timestamp, validate_execution, verify_original_helpers, write)
from release_process import GROUPS, command, group_alive


def preflight(root, evidence, execution, platform_name):
    xcode = command(['xcodebuild', '-version'], root, evidence, 'actual-xcode', 30).strip()
    require(xcode == 'Xcode 27.0\nBuild version 27A266a', 'Unreviewed actual Xcode toolchain')
    sdk = command(['xcrun', '--sdk', platform_name, '--show-sdk-version'], root, evidence, 'actual-sdk', 30).strip()
    require(sdk.split('.')[0] == '27', 'Unreviewed actual Release SDK')
    sdk_path = command(['xcrun', '--sdk', platform_name, '--show-sdk-path'], root, evidence, 'actual-sdk-path', 30).strip()
    result = {'status': 'PREFLIGHT_PASS_UI_NOT_RUN', 'source_sha': execution['source_sha'],
              'run_id': execution['execution_id'], 'run_attempt': '1', 'platform': platform_name,
              'xcode': xcode, 'sdk': sdk, 'sdk_path': sdk_path, 'selected': {}}
    write(evidence / 'preflight.json', result)
    if platform_name == 'iphonesimulator':
        sys.path.insert(0, str(root / 'Tools/PinkhaSimulatorGate'))
        from preflight import select_pairs
        observed = json.loads(command(['xcrun', 'simctl', 'list', '--json'], root, evidence, 'simulator-inventory', 30))
        runtime, devices = select_pairs(observed)
        device = devices['ipad']
        name = 'OriginalEditor-Release-' + execution['execution_id'] + '-ipad'
        udid = command(['xcrun', 'simctl', 'create', name, device['identifier'], runtime['identifier']],
                       root, evidence, 'create-owned-simulator', 60).strip()
        require(re.fullmatch(r'[A-Fa-f0-9-]{36}', udid), 'Malformed owned Release simulator UUID')
        result['selected']['ipad'] = {'udid': udid, 'name': name, 'device': device, 'runtime': runtime}
        write(evidence / 'preflight.json', result)
    return result


def original_notices(root, derived, exported, profile, before, dependencies):
    notices = exported / 'SourceProvenance'
    notices.mkdir()
    shutil.copyfile(root / 'LICENSE.md', notices / 'OriginalAnytype-LICENSE.md')
    shutil.copyfile(root / profile['package_resolved_path'], notices / 'Original-Package.resolved')
    files = []
    for checkout in sorted((derived / 'SourcePackages/checkouts').iterdir()):
        if checkout.is_dir():
            for path in sorted(checkout.iterdir()):
                if path.is_file() and not path.is_symlink() and path.name.upper().split('.')[0] in {'LICENSE', 'LICENCE', 'NOTICE', 'COPYING'}:
                    require(path.stat().st_size <= 2_097_152, 'Unexpected original dependency notice size')
                    destination = notices / checkout.name / path.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, destination)
                    files.append({'path': destination.relative_to(exported).as_posix(), 'sha256': digest(destination)})
    write(notices / 'OriginalSource.json', {'application_source': before['head_sha'],
          'original_trees': before['original_trees'], 'dependencies': dependencies,
          'retained_original_dependency_notices': files,
          'scope': 'Original Release framework/compiler prerequisite; editable UI/save/reopen not exercised'})


def verify_frameworks(root, work, evidence, proof, platform_name):
    from framework_profile import TARGET
    from framework_install_names import verify_framework_install_name
    from release_signing import seal_framework
    exported = work / 'distribution'
    dynamic, seals = [], []
    for index, name in enumerate(proof['frameworks']):
        framework = exported / 'Frameworks' / name
        info = plistlib.loads((framework / 'Info.plist').read_bytes())
        executable = info.get('CFBundleExecutable')
        require(isinstance(executable, str) and Path(executable).name == executable, 'Invalid Release framework executable')
        binary = framework / executable
        header = command(['otool', '-hv', str(binary)], root, evidence, 'framework-header-' + str(index), 30)
        if re.search(r'\bDYLIB\b', header):
            dynamic.append(name)
            seals.append(seal_framework(root, exported, name, platform_name, evidence, command))
            command(['otool', '-L', str(binary)], root, evidence, 'framework-loads-' + str(index), 30)
    require(TARGET + '.framework' in dynamic, 'Missing real original Release dynamic framework')
    binary = exported / 'Frameworks' / (TARGET + '.framework') / TARGET
    install = verify_framework_install_name(binary)
    require(command(['lipo', '-archs', str(binary)], root, evidence, 'framework-architecture', 30).strip() == 'arm64',
            'Wrong actual Release target architecture')
    platform_output = command(['xcrun', 'vtool', '-show-build', str(binary)], root, evidence, 'framework-platform', 30)
    expected_platform = 'IOSSIMULATOR' if platform_name == 'iphonesimulator' else 'IOS'
    require(re.search(r'platform\s+' + expected_platform + r'\b', platform_output),
            'Wrong actual Release target platform')
    symbols = command(['nm', '-gU', str(binary)], root, evidence, 'original-framework-symbols', 60)
    require('AnytypeOriginalEditor' in symbols and not re.search(r'(?m)\s_main$', symbols),
            'Release framework lacks its own module or contains an app entrypoint')
    write(evidence / 'owned-export-signing.json', seals)
    return dynamic, install, seals


def actual_resource_runs(root, evidence, derived, app, preflight_value, oracle, receipt):
    from framework_products import verify_observation
    from consumer_failure_capture import combine_launch_help
    udid = preflight_value['selected']['ipad']['udid']
    bundle_id = 'org.otzaria.acceptance.original-editor'
    command(['xcrun', 'simctl', 'boot', udid], root, evidence, 'boot-owned-simulator', 60)
    command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], root, evidence, 'owned-simulator-bootstatus', 180)
    command(['xcrun', 'simctl', 'install', udid, str(app)], root, evidence, 'install-external-consumer', 300)
    installed = command(['xcrun', 'simctl', 'get_app_container', udid, bundle_id, 'app'],
                        root, evidence, 'consumer-app-container', 30).strip()
    data = Path(command(['xcrun', 'simctl', 'get_app_container', udid, bundle_id, 'data'],
                        root, evidence, 'consumer-data-container', 30).strip())
    require(Path(installed).is_dir() and data.is_dir() and udid in Path(installed).parts and udid in data.parts,
            'Release consumer containers are outside the owned Simulator')
    help_stdout = command(['xcrun', 'simctl', 'help', 'launch'], root, evidence, 'actual-simctl-launch-help', 15)
    combine_launch_help(help_stdout, (evidence / 'actual-simctl-launch-help.stderr.log').read_text(errors='replace'))
    for language in ['en', 'he']:
        nonce = str(uuid.uuid4()).upper()
        output = data / 'Documents' / ('original-editor-' + nonce + '.json')
        require(not output.exists(), 'Stale Release resource observation')
        streams = [evidence / ('consumer-' + language + '-application.' + stream + '.log') for stream in ['stdout', 'stderr']]
        for path in streams:
            with path.open('xb'):
                pass
            path.chmod(0o600)
        command(['xcrun', 'simctl', 'launch', '--stdout=' + str(streams[0]), '--stderr=' + str(streams[1]),
                 '--terminate-running-process', udid, bundle_id,
                 '--original-editor-nonce', nonce, '-AppleLanguages', '(' + language + ')',
                 '-AppleLocale', 'he_IL' if language == 'he' else 'en_US'],
                root, evidence, 'consumer-' + language + '-launch', 30)
        limit = time.monotonic() + 20
        while not output.exists() and time.monotonic() < limit:
            time.sleep(0.1)
        require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 65_536,
                'No bounded actual Release resource observation: ' + language)
        raw = output.read_bytes()
        (evidence / ('consumer-' + language + '-observation.json')).write_bytes(raw)
        value = verify_observation(json.loads(raw), nonce, language, installed, oracle)
        require(not derived.exists(), 'Producer absolute resource fallback was recreated')
        receipt['verified_runtime_observations'].append(value)
        write(evidence / 'execution.json', receipt)
        command(['xcrun', 'simctl', 'terminate', udid, bundle_id], root, evidence, 'consumer-' + language + '-terminate', 30)


def execute(args, receipt, execution, descriptor, control):
    root, work, evidence = args.root, args.work, args.evidence
    from framework_profile import read_manifest, source_observation
    from framework_products import export_products, inventory, original_oracles
    from framework_install_names import verify_consumer_install_name
    from run_framework_acceptance import source_file_proof, dependency_proof
    from collect_release_graphs import collect
    from release_surface import verify_public_surface
    from release_clang import export_clang_declarations
    from release_consumer_project import consumer_project
    from release_ownership import verify_ownership
    from import_abi_input import verify as verify_abi
    receipt['reused_original_controls'] = verify_original_helpers(root, args.control_root)
    before, installation, original_environment = admit_original_owner(
        root, args.abi_execution, args.abi_execution_sha256, args.abi_source_before,
        args.abi_receipt, args.abi_sha256, args.simulator_qualification,
        args.simulator_qualification_sha256, args.sdk_source)
    os.environ.update({key: original_environment[key] for key in ['OTZARIA_LOCAL_EXECUTION', 'OTZARIA_LOCAL_EXECUTION_SHA256']})
    shutil.copyfile(args.abi_source_before, evidence / 'source-before.json')
    context = current_build_context(before, execution, descriptor)
    write(evidence / 'current-build-source-context.json', context)
    write(evidence / 'import-abi-before.json', installation)
    receipt.update(heart=installation, abi_producer_identity=before['execution_identity'],
                   debug_simulator_qualification_sha256=args.simulator_qualification_sha256,
                   original_app_runtime='NOT_RUN', editable_mount='API_DECLARED_NATIVE_UI_NOT_RUN')
    sys.path.insert(0, str(root / 'Tools/Hanlin'))
    from prepare_sdk import verify as verify_hanlin
    hanlin = verify_hanlin(root / 'Dependencies/Hanlin')
    write(evidence / 'original-hanlin-snapshot.json', hanlin)
    profile = read_manifest()
    checked = preflight(root, evidence, execution, args.platform)
    receipt['preflight'] = checked
    work.mkdir()
    derived = work / 'producer-derived'
    destination = ('platform=iOS Simulator,id=' + checked['selected']['ipad']['udid']
                   if args.platform == 'iphonesimulator' else 'generic/platform=iOS')
    # Use the real Release product configuration. Emit its complete public/SPI
    # graph, including evidence that DEBUG qualification declarations are absent.
    flags = ['OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED $(ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS)',
        'ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS=-emit-symbol-graph -emit-symbol-graph-dir $(DERIVED_FILE_DIR)/OriginalEditorSymbolGraphs -symbol-graph-minimum-access-level public -include-spi-symbols',
        'ONLY_ACTIVE_ARCH=YES', 'ARCHS=arm64', 'CODE_SIGNING_ALLOWED=NO',
        'CODE_SIGNING_REQUIRED=NO', 'CODE_SIGN_IDENTITY=', 'PROVISIONING_PROFILE_SPECIFIER=']
    project = root / 'Anytype.xcodeproj'
    receipt['phase'] = 'STRICT_SHARED_PACKAGE_RESOLUTION'
    write(evidence / 'execution.json', receipt)
    command(['xcodebuild', '-resolvePackageDependencies', '-project', str(project), '-scheme', 'AnytypeOriginalEditor',
             '-configuration', CONFIGURATION, '-destination', destination, '-derivedDataPath', str(derived),
             '-onlyUsePackageVersionsFromResolvedFile'], root, evidence, 'exact-package-resolution', 900)
    require(source_observation(root) == before, 'Release resolver changed original source/lock')
    receipt['strict_dependency_resolution'] = 'PASS_EXACT_COMMITTED_LOCK_UNCHANGED'
    receipt['phase'] = 'ORIGINAL_RELEASE_FRAMEWORK_BUILD'
    write(evidence / 'execution.json', receipt)
    command(['xcodebuild', 'build', '-project', str(project), '-scheme', 'AnytypeOriginalEditor',
             '-configuration', CONFIGURATION, '-destination', destination, '-derivedDataPath', str(derived),
             '-resultBundlePath', str(evidence / 'framework-build.xcresult'),
             '-onlyUsePackageVersionsFromResolvedFile', *flags], root, evidence, 'framework-build', 6000)
    receipt['original_framework_build'] = 'PASS'
    receipt['actual_source_closure'] = source_file_proof(root, derived, before, evidence)
    receipt['dependencies'] = dependency_proof(root, derived, profile, evidence)
    products = derived / ('Build/Products/' + CONFIGURATION + '-' + args.platform)
    require(products.is_dir(), 'Actual Release products are absent')
    exported = work / 'distribution'
    exported_proof = export_products(products, exported, derived)
    original_notices(root, derived, exported, profile, before, receipt['dependencies'])
    dynamic, install, seals = verify_frameworks(root, work, evidence, exported_proof, args.platform)
    receipt['actual_framework_install_name'] = install
    receipt['owned_export_signing'] = {'status': 'OWNED_ADHOC_PREREQUISITE_ONLY', 'count': len(seals),
                                      'receipt_sha256': digest(evidence / 'owned-export-signing.json')}
    graph_dir = evidence / 'actual-public-symbol-graphs'
    collection = collect(root, derived, evidence, checked['sdk_path'], graph_dir, args.platform, context)
    graphs = [json.loads(p.read_text()) for p in sorted(graph_dir.glob('*.symbols.json'))]
    contract = json.loads((root / 'Tools/OriginalEditor/public_host_contract.json').read_text())
    receipt['actual_public_surface'] = verify_public_surface(graphs, root, contract)
    write(evidence / 'actual-public-surface.json', receipt['actual_public_surface'])
    clang = export_clang_declarations(derived, exported, collection, context,
                                      root / profile['package_resolved_path'], args.platform)
    write(evidence / 'clang-declaration-export.json', clang)
    receipt['original_clang_declarations'] = {'module_map_count': len(clang['module_maps']),
        'header_root_count': len(clang['header_search_paths']), 'declaration_file_count': len(clang['files']),
        'manifest_sha256': digest(exported / 'SourceProvenance/ClangImportContext.json')}
    clang_identity = {k: clang[k] for k in ['source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256']}
    clang_identity['manifest_sha256'] = receipt['original_clang_declarations']['manifest_sha256']
    exported_proof.update(files=inventory(exported))
    exported_proof['bytes'] = sum(r['bytes'] for r in exported_proof['files'].values())
    write(evidence / 'framework-distribution.json', exported_proof)
    oracle = original_oracles(root, profile)
    write(evidence / 'independent-original-resource-oracles.json', oracle)
    consumer = work / 'external-consumer'
    consumer_source = args.control_root / 'Tools/OriginalEditor/DeviceRelease/ReleaseConsumer.swift'
    consumer_project_path = consumer_project(consumer, exported, consumer_source, dynamic, clang_identity, args.platform)
    write(evidence / 'consumer-source-inputs.json', inventory(consumer))
    hidden = work / 'producer-derived-preserved'
    require(not hidden.exists(), 'Stale Release producer quarantine')
    derived.rename(hidden)
    require(not derived.exists(), 'Original absolute producer resource fallback still exists')
    write(evidence / 'producer-build-path-absent.json', {'original': str(derived), 'preserved_at': str(hidden),
                                                       'original_path_exists': False, 'deleted': False})
    receipt['phase'] = 'EXTERNAL_PRODUCTION_API_CONSUMER_BUILD'
    write(evidence / 'execution.json', receipt)
    consumer_derived = work / 'consumer-derived'
    command(['xcodebuild', 'build', '-project', str(consumer_project_path), '-scheme', 'OriginalEditorConsumer',
             '-configuration', 'Release', '-destination', destination, '-derivedDataPath', str(consumer_derived),
             '-resultBundlePath', str(evidence / 'consumer-build.xcresult'), 'ONLY_ACTIVE_ARCH=YES', 'ARCHS=arm64'],
            consumer, evidence, 'external-consumer-build', 1200)
    app = consumer_derived / ('Build/Products/Release-' + args.platform + '/OriginalEditorConsumer.app')
    require(app.is_dir() and not derived.exists() and inventory(exported) == exported_proof['files'],
            'External Release consumer is absent or changed/recreated original producer inputs')
    if args.platform == 'iphonesimulator':
        command(['codesign', '--verify', '--strict', str(app)], root, evidence, 'external-consumer-signature', 30)
    for name in dynamic:
        require(inventory(app / 'Frameworks' / name) == inventory(exported / 'Frameworks' / name),
                'External Release consumer did not embed exact original product: ' + name)
    receipt['actual_consumer_install_names'] = verify_consumer_install_name(app)
    receipt.update(external_consumer_build='PASS', public_host_api='EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN',
                   compiled_consumer_api_probe_sha256=digest(consumer_source))
    if args.platform == 'iphonesimulator':
        receipt['phase'] = 'ACTUAL_RELEASE_EXTERNAL_RESOURCE_RUNTIME'
        write(evidence / 'execution.json', receipt)
        actual_resource_runs(root, evidence, derived, app, checked, oracle, receipt)
        require(len(receipt['verified_runtime_observations']) == 2, 'Incomplete actual Release EN/HE resource execution')
    receipt['phase'] = 'ACTUAL_RELEASE_SHARED_IMPLEMENTATION_OWNERSHIP'
    write(evidence / 'execution.json', receipt)
    receipt['shared_runtime_ownership'] = verify_ownership(root, evidence, work, receipt, context, before, args.platform)
    require(source_observation(root) == before, 'Original source changed during Release execution')
    require(verify_hanlin(root / 'Dependencies/Hanlin') == hanlin, 'Canonical Hanlin changed during Release execution')
    after_abi = verify_abi(root, args.abi_receipt, args.abi_sha256, before)
    require(after_abi == installation, 'Original qualified Import ABI changed during Release execution')
    write(evidence / 'import-abi-after.json', after_abi)
    require(inventory(exported) == exported_proof['files'], 'Release distribution changed during acceptance')
    receipt.update(status=SIMULATOR_PASS if args.platform == 'iphonesimulator' else DEVICE_PASS,
        phase='COMPLETE', distribution=str(exported), same_toolchain_only=True,
        original_43_component_tests='NOT_RERUN', native_editor_ui_tests=0,
        editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN', device_runtime='NOT_RUN')


def cleanup_owned_simulator(root, evidence, execution):
    path = evidence / 'preflight.json'
    if not path.exists():
        return {'status': 'NO_OWNED_SIMULATOR_CREATED'}
    value = json.loads(path.read_text())
    require(value['run_id'] == execution['execution_id'], 'Cleanup cannot borrow another execution')
    selected = value.get('selected', {}).get('ipad')
    if not selected:
        return {'status': 'NO_OWNED_SIMULATOR_CREATED'}
    udid, name = selected['udid'], selected['name']
    observed = json.loads(command(['xcrun', 'simctl', 'list', 'devices', '--json'], root, evidence, 'cleanup-inventory-before', 30))
    matches = [v for values in observed['devices'].values() for v in values if v['udid'] == udid]
    require(len(matches) == 1 and matches[0]['name'] == name
            and name == 'OriginalEditor-Release-' + execution['execution_id'] + '-ipad',
            'Owned Simulator cleanup identity differs')
    if matches[0]['state'] != 'Shutdown':
        command(['xcrun', 'simctl', 'shutdown', udid], root, evidence, 'cleanup-shutdown', 60)
    command(['xcrun', 'simctl', 'delete', udid], root, evidence, 'cleanup-delete', 60)
    after = json.loads(command(['xcrun', 'simctl', 'list', 'devices', '--json'], root, evidence, 'cleanup-inventory-after', 30))
    require(not any(v['udid'] == udid for values in after['devices'].values() for v in values),
            'Owned Release Simulator remains after cleanup')
    return {'status': 'PASS', 'udid': udid, 'name': name, 'owned_simulator_removed': True}


def package(args, receipt, descriptor):
    from product_inventory import inventory
    root, evidence, exported = args.root, args.evidence, Path(receipt['distribution'])
    manifest = evidence / 'framework-distribution.json'
    expected = json.loads(manifest.read_text())['files']
    require(inventory(exported) == expected, 'Distribution differs before final qualification packaging')
    write(exported / 'QUALIFICATION.json', receipt)
    archive = evidence / 'Release-SDK.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(exported.rglob('*')):
            if p.is_file():
                require(not p.is_symlink(), 'Aliased Release archive member')
                z.write(p, p.relative_to(exported).as_posix())
    actual = inventory(exported)
    with zipfile.ZipFile(archive) as z:
        require(set(z.namelist()) == set(actual) and z.testzip() is None, 'Release archive CRC/membership differs')
        for name, row in actual.items():
            raw = z.read(name)
            require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                    'Release archive member bytes differ')
    roles = {'execution': descriptor, 'source_before': evidence / 'source-before.json',
             'source_after': evidence / 'source-after.json', 'abi': args.abi_receipt,
             'abi_source_before': args.abi_source_before, 'abi_execution': args.abi_execution}
    config = {'schema': 'otzaria.original-editor.production-input/1', 'producer_kind': 'local-mac',
        'repository': REPOSITORY, 'source_sha': receipt['source_sha'], 'control_sha': receipt['control_sha'],
        'run_id': receipt['run_id'], 'run_attempt': 1, 'configuration': 'Release', 'platform': args.platform,
        'architectures': ['arm64'], 'native_source_tree': receipt['heart']['native_qualification']['native_source_tree'],
        'local_execution_sha256': digest(descriptor), 'archive_path': archive.relative_to(root).as_posix(),
        'archive_bytes': archive.stat().st_size, 'archive_sha256': digest(archive),
        'distribution_manifest_path': manifest.relative_to(root).as_posix(), 'distribution_manifest_sha256': digest(manifest),
        'distribution_root': exported.relative_to(root).as_posix(), 'qualification_sha256': digest(exported / 'QUALIFICATION.json'),
        'original_source_sha256': digest(exported / 'SourceProvenance/OriginalSource.json'),
        'hanlin_source_path': (evidence / 'original-hanlin-snapshot.json').relative_to(root).as_posix(),
        'hanlin_source_sha256': digest(evidence / 'original-hanlin-snapshot.json'),
        'local_receipts': {k: {'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size,
                               'sha256': digest(p)} for k, p in roles.items()}}
    if args.platform == 'iphoneos':
        require(re.fullmatch(r'[A-Z0-9]{10}', args.signing_team_id or ''), 'Missing reviewed public Host signing team')
        config['signing_team_id'] = args.signing_team_id
    write(evidence / 'production-input.json', config)
    write(evidence / 'PACKAGING.json', {'status': 'EXACT_RELEASE_ARCHIVE_MEMBERS_VERIFIED',
          'members': len(actual), 'archive_sha256': config['archive_sha256'],
          'production_input_sha256': digest(evidence / 'production-input.json')})


def main():
    p = argparse.ArgumentParser(__doc__)
    for name in ['root', 'evidence', 'work', 'abi-execution', 'abi-source-before', 'abi-receipt', 'simulator-qualification']:
        p.add_argument('--' + name, type=Path, required=True)
    for name in ['sdk-source', 'abi-execution-sha256', 'abi-sha256', 'simulator-qualification-sha256']:
        p.add_argument('--' + name, required=True)
    p.add_argument('--platform', required=True, choices=['iphoneos', 'iphonesimulator'])
    p.add_argument('--control-root', type=Path, default=Path(__file__).resolve().parents[3])
    p.add_argument('--signing-team-id')
    args = p.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            require(value.is_absolute() and value.resolve() == value, 'Release inputs must use actual absolute paths')
    require(re.fullmatch(r'[a-f0-9]{40}', args.sdk_source), 'Missing exact actual SDK source')
    sys.path.insert(0, str(args.root / 'Tools/OriginalEditor'))
    sys.path.insert(0, str(args.root / 'Tools/OriginalEditor/SharedRuntime'))
    control = controller_observation(args.control_root)
    execution, descriptor = create_execution(args.root, control, args.evidence, args.work, args.platform, sys.argv, args.sdk_source)
    receipt = {'schema': 1, 'status': 'FAIL', 'phase': 'ORIGINAL_ABI_AND_DEBUG_SDK_ADMISSION',
        'source_sha': execution['source_sha'], 'control_sha': execution['control_sha'],
        'run_id': execution['execution_id'], 'run_attempt': '1', 'configuration': CONFIGURATION,
        'platform': args.platform, 'architectures': ['arm64'], 'execution_identity': identity(execution, descriptor),
        'started_at': timestamp(), 'original_framework_build': 'NOT_RUN', 'external_consumer_build': 'NOT_RUN',
        'verified_runtime_observations': [], 'native_editor_ui_tests': 0, 'device_runtime': 'NOT_RUN'}
    def interrupt(signum, frame):
        raise InterruptedError('Owned Release signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        execute(args, receipt, execution, descriptor, control)
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    finally:
        try:
            receipt['owned_simulator_cleanup'] = cleanup_owned_simulator(args.root, args.evidence, execution)
            write(args.evidence / 'owned-simulator-cleanup.json', receipt['owned_simulator_cleanup'])
        except BaseException as error:
            receipt.update(status='FAIL', cleanup_error=str(error))
        try:
            from framework_profile import source_observation
            before_path = args.evidence / 'source-before.json'
            if before_path.exists():
                after = source_observation(args.root)
                write(args.evidence / 'source-after.json', after)
                require(json.loads(before_path.read_text()) == after, 'Source differs at final Release observation')
            require(controller_observation(args.control_root) == control, 'Release controller changed during execution')
            validate_execution(execution, args.root, control, args.platform)
            require(json.loads(descriptor.read_text()) == execution
                    and digest(descriptor) == receipt['execution_identity']['local_execution_sha256'],
                    'Release execution descriptor changed during execution')
            require(all(not group_alive(group) for group in GROUPS), 'Owned Release command group remains')
            receipt['owned_command_groups_drained'] = True
        except BaseException as error:
            receipt.update(status='FAIL', final_observation_error=str(error))
        receipt['finished_at'] = timestamp()
        write(args.evidence / 'execution.json', receipt)
    if receipt['status'] in {SIMULATOR_PASS, DEVICE_PASS}:
        try:
            package(args, receipt, descriptor)
        except BaseException as error:
            receipt.update(status='FAIL', phase='PACKAGING', error_type=type(error).__name__, error=str(error))
            write(args.evidence / 'execution.json', receipt)
            write(Path(receipt['distribution']) / 'QUALIFICATION.json', receipt)
    print(json.dumps({'status': receipt['status'], 'phase': receipt['phase'], 'platform': args.platform,
                      'run_id': receipt['run_id'], 'evidence': str(args.evidence),
                      'error': receipt.get('error'), 'native_editor_ui_tests': 0}, indent=2))
    return 0 if receipt['status'] in {SIMULATOR_PASS, DEVICE_PASS} else 1


if __name__ == '__main__':
    raise SystemExit(main())
