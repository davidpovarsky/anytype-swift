#!/usr/bin/env python3
"""Build the genuine original framework and execute a separate binary consumer.

Only a real Xcode27/OS27 execution can produce the final PASS. The exported Host
and Debug Simulator SPI must compile and pass the full public-surface gate. This
driver does not mount a document, create an account, or claim editor UI tests.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import shlex
import signal
import subprocess
import sys
import time
import uuid

from clang_product_closure import export_clang_declarations
from framework_profile import BRANCH, TARGET, blob, git, read_manifest, sha256, source_observation
from framework_products import consumer_project, export_products, inventory, original_oracles, verify_observation, verify_public_surface
from amplitude_simulator_signing import prepare_amplitude_simulator_export
from anycrypto_simulator_signing import (NAME as ANYCRYPTO_NAME, EXECUTABLE as ANYCRYPTO_EXECUTABLE,
                                        diagnose_generated_package_exports, prepare_anycrypto_simulator_export)
from observed_package_simulator_signing import (PROFILES as OBSERVED_PACKAGE_PROFILES,
                                               prepare_observed_package_simulator_export)
from pbx_source import require
from framework_install_names import verify_framework_install_name, verify_consumer_install_name
from consumer_failure_capture import prepare_launch_capture, combine_launch_help, read_regular
from framework_consumer_retention import retain_built_consumer
from local_execution import current_identity


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def command(arguments, cwd, evidence, name, timeout):
    evidence = Path(evidence)
    result = {'command': [str(value) for value in arguments], 'cwd': str(cwd),
              'started_at': timestamp(), 'timeout_seconds': timeout, 'returncode': None, 'timed_out': False}
    stdout, stderr = evidence / (name + '.stdout.log'), evidence / (name + '.stderr.log')
    process = None
    try:
        with stdout.open('xb') as output, stderr.open('xb') as error:
            process = subprocess.Popen(arguments, cwd=cwd, stdout=output, stderr=error, start_new_session=True)
            try:
                result['returncode'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timed_out'] = True
                raise
    except BaseException:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        if process is not None:
            result['returncode'] = process.returncode
        raise
    finally:
        result['finished_at'] = timestamp()
        result['stdout_sha256'] = sha256(stdout) if stdout.exists() else None
        result['stderr_sha256'] = sha256(stderr) if stderr.exists() else None
        write(evidence / (name + '.command.json'), result)
    require(result['returncode'] == 0, 'Actual command failed: ' + name)
    return stdout.read_text(errors='replace')


def symbolgraph_import_context(root, derived, products, sdk_path, evidence):
    """Reuse this build's actual import context without filtering its public API.

    The standalone extractor imports modules implicitly. Xcode's explicit Swift
    module cache is a different input from its Clang scanner/implicit cache;
    carry the latter using the extractor's supported module-cache option.
    """
    root, derived, products, evidence = map(Path, (root, derived, products, evidence))
    log = evidence / 'framework-build.stdout.log'
    build = json.loads((evidence / 'framework-build.command.json').read_text())
    require(build.get('returncode') == 0 and build.get('timed_out') is False
            and build.get('cwd') == str(root)
            and build.get('stdout_sha256') == sha256(log),
            'Symbol graph import context is not from the successful original build')
    candidates = []
    with log.open() as stream:
        for line in stream:
            if 'builtin-SwiftDriver --' not in line:
                continue
            arguments = shlex.split(line.strip())
            if '-module-name' in arguments and arguments[arguments.index('-module-name') + 1] == TARGET:
                candidates.append((line.rstrip('\n'), arguments))
    require(len(candidates) == 1, 'Missing or ambiguous original target compiler import context')
    line, arguments = candidates[0]

    def values(option):
        indices = [index for index, value in enumerate(arguments) if value == option]
        require(all(index + 1 < len(arguments) for index in indices), 'Missing compiler option value: ' + option)
        return [arguments[index + 1] for index in indices]

    require(values('-module-name') == [TARGET]
            and values('-target') == ['arm64-apple-ios27.0-simulator']
            and values('-sdk') == [str(sdk_path)]
            and values('-swift-version') == ['5'],
            'Original compiler target, SDK or language mode differs')
    implicit_cache = str(derived / 'ModuleCache.noindex')
    require(values('-clang-scanner-module-cache-path') == [implicit_cache]
            and implicit_cache in values('-module-cache-path'),
            'Original Clang scanner cache is not the owned producer cache')
    # Keep the driver's existing import paths and order. Append every additional
    # search path and each original Clang import argument, including module maps,
    # header maps and the SDK stat/VFS caches. Do not guess dependency paths.
    seen = {'-F': {str(products), str(products / 'PackageFrameworks')},
            '-I': {str(products), str(products / 'Modules')}}
    extra = []
    for option in ['-F', '-I']:
        for value in values(option):
            if value not in seen[option]:
                extra.extend([option, value])
                seen[option].add(value)
    clang_arguments = values('-Xcc')
    for value in clang_arguments:
        extra.extend(['-Xcc', value])
    result = ['-module-cache-path', implicit_cache, '-swift-version', '5', '-v', *extra]
    write(evidence / 'symbolgraph-import-context.json', {
        'source_build_stdout_sha256': sha256(log),
        'source_compiler_line_sha256': hashlib.sha256(line.encode()).hexdigest(),
        'source_compiler_arguments': arguments,
        'original_explicit_and_implicit_module_cache_options': values('-module-cache-path'),
        'extractor_cache_role': 'ORIGINAL_CLANG_SCANNER_IMPLICIT_CACHE',
        'original_clang_import_arguments': clang_arguments,
        'extractor_additional_arguments': result,
        'public_symbol_filtering_added': False,
        'status': 'ACTUAL_BUILD_IMPORT_CONTEXT_BOUND_EXTRACTION_NOT_YET_PASSED'})
    return result


def source_file_proof(root, derived, before, evidence):
    paths = [p for p in Path(derived).rglob('*.SwiftFileList') if TARGET + '.build' in p.parts]
    require(paths, 'Actual original framework compiler input lists are absent')
    expected = {(root / path).resolve() for path in before['source_files']
                if path != 'Anytype/Sources/ApplicationLayer/AppScene.swift'}
    expected.add(root / 'Anytype/Resources/AssetConstants.swift')
    expected.update(root / path for path in before['framework_facade_sources'])
    observed = set()
    retained = []
    for number, path in enumerate(sorted(paths)):
        raw = path.read_bytes()
        destination = evidence / ('framework-inputs-' + str(number) + '.SwiftFileList.txt')
        destination.write_bytes(raw)
        for line in raw.decode().splitlines():
            values = shlex.split(line)
            require(len(values) == 1, 'Malformed actual Swift source input')
            observed.add(Path(values[0]).resolve())
        retained.append({'path': str(path), 'evidence_path': destination.name,
                         'sha256': sha256(path), 'bytes': len(raw)})
    actual_original = {path for path in observed if path.is_relative_to(root)
                       and not path.is_relative_to(derived)}
    require(actual_original == expected, 'Actual framework source list is not the complete original source closure')
    require(all(path.is_relative_to(derived) for path in observed - expected),
            'Unexpected external Swift source compiled into the framework')
    require(not any(path.name == 'AppScene.swift' or 'AnytypeTests' in path.parts for path in observed),
            'An app entrypoint/test source was compiled into the framework')
    generated = []
    for path in sorted(Path(derived).rglob('resource_bundle_accessor.swift')):
        if any(name + '.build' in path.parts for name in ['Assets', 'Loc', 'DesignKit']):
            raw = path.read_bytes()
            name = next(name for name in ['Assets', 'Loc', 'DesignKit'] if name + '.build' in path.parts)
            require(name not in [row['module'] for row in generated], 'Ambiguous generated resource accessor')
            destination = evidence / ('original-generated-' + name + '-resource-accessor.swift.txt')
            destination.write_bytes(raw)
            generated.append({'module': name, 'path': str(path), 'evidence_path': destination.name,
                              'sha256': sha256(path), 'bytes': len(raw)})
    require({row['module'] for row in generated} == {'Assets', 'Loc', 'DesignKit'},
            'Original generated package bundle accessors are missing')
    value = {'complete_original_swift_input_count': len(expected), 'generated_swift_input_count': len(observed - expected),
             'lists': retained, 'generated_bundle_accessors': generated,
             'source_is_original': True, 'app_or_test_binary_repackaged': False}
    write(evidence / 'actual-framework-source-inputs.json', value)
    return value


def dependency_proof(root, derived, profile, evidence):
    pins = json.loads((root / profile['package_resolved_path']).read_text())['pins']
    expected = {row['identity'].lower(): row['state']['revision'] for row in pins}
    workspace = json.loads((derived / 'SourcePackages/workspace-state.json').read_text())
    actual = {}
    for dependency in workspace['object']['dependencies']:
        reference = dependency['packageRef']
        identity = reference['identity'].lower()
        state = dependency['state']
        if state.get('name') in {'local', 'fileSystem'}:
            location = Path(reference.get('location', '')).resolve()
            require(location.is_relative_to(root / 'Modules') or location.is_relative_to(root / 'Dependencies/Hanlin')
                    or location == root / 'Tools/OriginalEditor/SharedRuntime',
                    'Unreviewed local package source')
            continue
        require(identity in expected and identity not in actual, 'Unpinned or repeated dependency checkout')
        revision = state.get('checkoutState', {}).get('revision')
        require(revision == expected[identity], 'Resolved dependency changed: ' + identity)
        checkout = derived / 'SourcePackages/checkouts' / dependency['subpath']
        require(checkout.resolve().is_relative_to((derived / 'SourcePackages/checkouts').resolve()), 'Dependency checkout escapes cache')
        require(git(checkout, 'rev-parse', 'HEAD') == revision, 'Actual dependency Git HEAD differs: ' + identity)
        require(not git(checkout, 'diff', '--name-only', 'HEAD'), 'Actual dependency source was modified: ' + identity)
        # Generated compiler/accessor outputs belong to owned DerivedData, not
        # immutable source checkouts. Include Git-ignored additions: SwiftPM can
        # still compile them or copy them as resources. Do not clean either.
        untracked = [path for path in git(checkout, 'ls-files', '--others', '-z').split('\0') if path]
        require(not untracked, 'Untracked dependency inputs: ' + identity + ': ' + repr(untracked[:8]))
        actual[identity] = revision
    require({'torahinspectorkit', 'swift-ai-sdk'} <= set(actual), 'Canonical inspector/Hanlin dependency checkout missing')
    receipt = {'original_pin_count': len(expected), 'actual_checkout_revisions': actual,
               'locked_but_not_materialized': sorted(set(expected) - set(actual)),
               'all_checkout_files_tracked': True}
    write(evidence / 'dependency-checkouts.json', receipt)
    return receipt


def execute(args, receipt):
    root, evidence, work = args.root.resolve(), args.evidence.resolve(), args.work.resolve()
    require(evidence.is_relative_to(root / 'build') and work.is_relative_to(root / 'build')
            and not work.is_relative_to(evidence) and not evidence.is_relative_to(work), 'Unowned or overlapping CI output')
    profile = read_manifest()
    before = source_observation(root)
    initial_path = evidence / 'source-before.json'
    if initial_path.exists():
        require(json.loads(initial_path.read_text()) == before, 'Source changed since initial CI admission')
    else:
        write(initial_path, before)
    receipt.update(source_sha=before['head_sha'], run_id=before['run_id'], run_attempt=before['run_attempt'])
    if args.source_only:
        receipt.update(status='SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN')
        return
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Actual Apple silicon execution is required')
    require(not work.exists(), 'Refusing stale producer/consumer work directory')
    work.mkdir(parents=True)
    preflight = json.loads((evidence / 'preflight/preflight.json').read_text())
    require(preflight.get('status') == 'PREFLIGHT_PASS_UI_NOT_RUN'
            and preflight.get('source_sha') == before['head_sha'] and preflight.get('run_id') == before['run_id']
            and preflight.get('run_attempt') == before['run_attempt'], 'Original actual Xcode/OS27 preflight differs')
    if args.import_abi_receipt:
        from import_abi_input import verify as verify_import_abi
        require(before['execution_identity']['producer_kind'] == 'local-mac',
                'The local Import ABI route requires genuine local producer identity')
        installation = verify_import_abi(root, args.import_abi_receipt, args.import_abi_sha256, before)
        write(evidence / 'import-abi-before.json', installation)
    else:
        require(before['execution_identity']['producer_kind'] == 'github-actions',
                'A local SDK build must use the qualified new Import ABI')
        installation = json.loads((evidence / 'heart/heart-installation.json').read_text())
        require(installation.get('status') == 'PASS' and installation.get('app_source_sha') == before['head_sha']
                and installation.get('source_run_id') == '44203168617', 'Original Heart producer/install identity differs')
        heart = json.loads((root / 'Dependencies/Middleware/PinkhaNativeHeartBuild.json').read_text())
        require(heart.get('status') == 'PASS' and heart.get('marker') == installation['marker'], 'Installed Heart marker differs')
        for item in heart['artifacts']:
            member = root / 'Dependencies/Middleware/Lib.xcframework' / item['path']
            require(member.resolve().is_relative_to((root / 'Dependencies/Middleware/Lib.xcframework').resolve())
                    and sha256(member) == item['sha256'], 'Verified Heart source changed')
    sys.path.insert(0, str(root / 'Tools/Hanlin'))
    from prepare_sdk import verify as verify_hanlin
    hanlin_before = verify_hanlin(root / 'Dependencies/Hanlin')
    write(evidence / 'original-hanlin-snapshot.json', hanlin_before)
    sdk = command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], root, evidence, 'actual-simulator-sdk', 30).strip()
    require(sdk.split('.')[0] == '27', 'Framework SDK is not the reviewed OS27 SDK')
    swift = command(['xcrun', 'swiftc', '--version'], root, evidence, 'actual-swift', 30).strip()
    receipt.update(preflight=preflight, sdk=sdk, swift=swift, heart=installation,
                   original_app_runtime='NOT_RUN', editable_mount='API_DECLARED_NATIVE_UI_NOT_RUN', native_editor_ui_tests=0)
    udid = preflight['selected']['ipad']['udid']
    derived = work / 'producer-derived'
    destination = 'platform=iOS Simulator,id=' + udid
    flags = ['OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED $(ORIGINAL_EDITOR_SYMBOL_GRAPH_FLAGS)', 'ONLY_ACTIVE_ARCH=YES',
             'ARCHS=arm64', 'SWIFT_OPTIMIZATION_LEVEL=-Onone', 'CODE_SIGN_IDENTITY=-',
             'CODE_SIGNING_ALLOWED=YES', 'CODE_SIGNING_REQUIRED=YES', 'PROVISIONING_PROFILE_SPECIFIER=']
    build = ['xcodebuild', 'build', '-project', str(root / 'Anytype.xcodeproj'), '-scheme', TARGET,
             '-configuration', 'Debug-Anytype', '-destination', destination, '-derivedDataPath', str(derived),
             '-resultBundlePath', str(evidence / 'framework-build.xcresult'),
             '-onlyUsePackageVersionsFromResolvedFile', *flags]
    receipt['phase'] = 'STRICT_SHARED_PACKAGE_RESOLUTION'
    write(evidence / 'execution.json', receipt)
    command(['xcodebuild', '-resolvePackageDependencies', '-project', str(root / 'Anytype.xcodeproj'),
             '-scheme', TARGET, '-configuration', 'Debug-Anytype', '-destination', destination,
             '-derivedDataPath', str(derived), '-onlyUsePackageVersionsFromResolvedFile'],
            root, evidence, 'exact-package-resolution', 900)
    require(source_observation(root) == before, 'Strict resolver changed a committed source or lock')
    receipt['strict_dependency_resolution'] = 'PASS_EXACT_COMMITTED_LOCK_UNCHANGED'
    receipt['phase'] = 'ORIGINAL_FRAMEWORK_BUILD'
    write(evidence / 'execution.json', receipt)
    command(build, root, evidence, 'framework-build', 6000)
    receipt['original_framework_build'] = 'PASS'
    receipt['actual_source_closure'] = source_file_proof(root, derived, before, evidence)
    receipt['dependencies'] = dependency_proof(root, derived, profile, evidence)
    products = derived / 'Build/Products/Debug-Anytype-iphonesimulator'
    require(products.is_dir(), 'Actual expected Debug-Anytype simulator products are absent')
    exported = work / 'distribution'
    exported_proof = export_products(products, exported, derived)
    notices = exported / 'SourceProvenance'
    notices.mkdir()
    shutil.copyfile(root / 'LICENSE.md', notices / 'OriginalAnytype-LICENSE.md')
    shutil.copyfile(root / profile['package_resolved_path'], notices / 'Original-Package.resolved')
    notice_files = []
    for checkout in sorted((derived / 'SourcePackages/checkouts').iterdir()):
        if not checkout.is_dir():
            continue
        for source in sorted(checkout.iterdir()):
            if source.is_file() and not source.is_symlink() and source.name.upper().split('.')[0] in {'LICENSE', 'LICENCE', 'NOTICE', 'COPYING'}:
                require(source.stat().st_size <= 2_097_152, 'Unexpected dependency notice size')
                notice_destination = notices / checkout.name / source.name
                notice_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, notice_destination)
                notice_files.append({'path': notice_destination.relative_to(exported).as_posix(), 'sha256': sha256(notice_destination)})
    write(notices / 'OriginalSource.json', {'application_source': before['head_sha'],
          'original_trees': before['original_trees'], 'dependencies': receipt['dependencies'],
          'retained_original_dependency_notices': notice_files,
          'scope': 'Original Host API framework prerequisite; editable UI/save/reopen is not exercised'})
    exported_proof['files'] = inventory(exported)
    exported_proof['bytes'] = sum(item['bytes'] for item in exported_proof['files'].values())
    write(evidence / 'framework-distribution.json', exported_proof)
    diagnose_generated_package_exports(root, products, exported, evidence,
                                       exported_proof['frameworks'], before['head_sha'], command)
    dynamic = []
    for number, name in enumerate(exported_proof['frameworks']):
        framework = exported / 'Frameworks' / name
        info = plistlib.loads((framework / 'Info.plist').read_bytes())
        executable = info.get('CFBundleExecutable')
        require(isinstance(executable, str) and Path(executable).name == executable, 'Malformed exported framework executable')
        binary = framework / executable
        header = command(['otool', '-hv', str(binary)], root, evidence, 'framework-header-' + str(number), 30)
        if re.search(r'\bDYLIB\b', header):
            dynamic.append(name)
            if name == 'AmplitudeCore.framework':
                # This exact upstream Simulator product is byte-authenticated but
                # has two missing sealed compiler modules. Preserve its failed
                # seal, then sign only the owned export; the original strict
                # gate below and exact consumer embedding remain mandatory.
                write(evidence / 'framework-distribution-before-simulator-signing.json', exported_proof)
                try:
                    transformation = prepare_amplitude_simulator_export(root, products, exported, evidence, command)
                except BaseException:
                    # Preserve a full after-state even when the narrow parser
                    # refuses the transformation. It never grants qualification.
                    try:
                        write(evidence / 'framework-distribution-after-failed-signing.json',
                              {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': inventory(exported)})
                    except BaseException as observation_error:
                        receipt['after_failed_signing_inventory_error'] = {
                            'type': type(observation_error).__name__, 'message': str(observation_error)}
                    raise
                after_signing = inventory(exported)
                write(evidence / 'framework-distribution-after-simulator-signing.json',
                      {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': after_signing})
                permitted = {'Frameworks/AmplitudeCore.framework/AmplitudeCore',
                             'Frameworks/AmplitudeCore.framework/_CodeSignature/CodeResources'}
                require(set(after_signing) == set(exported_proof['files'])
                        and {path for path in after_signing
                             if after_signing[path] != exported_proof['files'][path]} == permitted,
                        'Simulator signing changed unrelated distribution bytes')
                exported_proof['files'] = after_signing
                exported_proof['bytes'] = sum(item['bytes'] for item in after_signing.values())
                exported_proof['simulator_signing_transformations'] = [transformation]
                write(evidence / 'framework-distribution.json', exported_proof)
            elif name == ANYCRYPTO_NAME:
                write(evidence / 'framework-distribution-before-anycrypto-signing.json', exported_proof)
                try:
                    transformation = prepare_anycrypto_simulator_export(root, products, exported, evidence, command)
                except BaseException:
                    try:
                        write(evidence / 'framework-distribution-after-failed-anycrypto-signing.json',
                              {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': inventory(exported)})
                    except BaseException as observation_error:
                        receipt['after_failed_anycrypto_inventory_error'] = {
                            'type': type(observation_error).__name__, 'message': str(observation_error)}
                    raise
                after_signing = inventory(exported)
                write(evidence / 'framework-distribution-after-anycrypto-signing.json',
                      {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': after_signing})
                prefix = 'Frameworks/' + ANYCRYPTO_NAME + '/'
                require(set(after_signing) == set(exported_proof['files']) | {prefix + '_CodeSignature/CodeResources'}
                        and {path for path in exported_proof['files']
                             if after_signing[path] != exported_proof['files'][path]} == {prefix + ANYCRYPTO_EXECUTABLE},
                        'AnyCrypto export sealing changed unrelated distribution bytes')
                exported_proof['files'] = after_signing
                exported_proof['bytes'] = sum(item['bytes'] for item in after_signing.values())
                exported_proof.setdefault('simulator_signing_transformations', []).append(transformation)
                write(evidence / 'framework-distribution.json', exported_proof)
            elif name in OBSERVED_PACKAGE_PROFILES:
                label = 'observed-' + OBSERVED_PACKAGE_PROFILES[name]['label']
                write(evidence / ('framework-distribution-before-' + label + '-signing.json'), exported_proof)
                try:
                    transformation = prepare_observed_package_simulator_export(
                        root, products, exported, evidence, name, command)
                except BaseException:
                    try:
                        write(evidence / ('framework-distribution-after-failed-' + label + '-signing.json'),
                              {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': inventory(exported)})
                    except BaseException as observation_error:
                        receipt['after_failed_' + label + '_inventory_error'] = {
                            'type': type(observation_error).__name__, 'message': str(observation_error)}
                    raise
                after_signing = inventory(exported)
                write(evidence / ('framework-distribution-after-' + label + '-signing.json'),
                      {'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'files': after_signing})
                prefix = 'Frameworks/' + name + '/'
                require(set(after_signing) == set(exported_proof['files']) | {prefix + '_CodeSignature/CodeResources'}
                        and {path for path in exported_proof['files']
                             if after_signing[path] != exported_proof['files'][path]} == {prefix + executable},
                        'Observed package export sealing changed unrelated distribution bytes')
                exported_proof['files'] = after_signing
                exported_proof['bytes'] = sum(item['bytes'] for item in after_signing.values())
                exported_proof.setdefault('simulator_signing_transformations', []).append(transformation)
                write(evidence / 'framework-distribution.json', exported_proof)
            command(['codesign', '--verify', '--strict', str(framework)], root, evidence,
                    'framework-signature-' + str(number), 30)
            command(['otool', '-L', str(binary)], root, evidence, 'framework-load-commands-' + str(number), 30)
    require(TARGET + '.framework' in dynamic, 'The original editor product is not a real dynamic framework')
    original_binary = exported / 'Frameworks' / (TARGET + '.framework') / TARGET
    receipt['actual_framework_install_name'] = verify_framework_install_name(original_binary)
    write(evidence / 'framework-install-name.json', receipt['actual_framework_install_name'])
    architecture = command(['lipo', '-archs', str(original_binary)], root, evidence, 'framework-architecture', 30).strip()
    require(architecture == 'arm64', 'Wrong actual simulator framework architecture')
    platform_output = command(['xcrun', 'vtool', '-show-build', str(original_binary)], root, evidence, 'framework-platform', 30)
    require(re.search(r'platform\s+IOSSIMULATOR\b', platform_output), 'Framework is not an iOS Simulator binary')
    symbols = command(['nm', '-gU', str(original_binary)], root, evidence, 'original-framework-symbols', 60)
    require('AnytypeOriginalEditor' in symbols and not re.search(r'(?m)\s_main$', symbols),
            'Framework contains an app entrypoint or lacks its real module')
    sdk_path = command(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], root, evidence,
                       'actual-simulator-sdk-path', 30).strip()
    graph_directory = evidence / 'actual-public-symbol-graphs'
    command([sys.executable, str(root / 'Tools/OriginalEditor/collect_compiler_symbolgraphs.py'),
             '--root', str(root), '--derived', str(derived), '--evidence', str(evidence),
             '--sdk', sdk_path, '--output-dir', str(graph_directory)],
            root, evidence, 'actual-target-public-symbol-graph', 120)
    graphs = sorted(graph_directory.glob('*.symbols.json'))
    require(graphs and (graph_directory / (TARGET + '.symbols.json')).is_file(),
            'Actual public module graph is absent')
    host_contract = json.loads((root / 'Tools/OriginalEditor/public_host_contract.json').read_text())
    receipt['actual_public_surface'] = verify_public_surface(
        [json.loads(path.read_text()) for path in graphs], root, host_contract=host_contract)
    write(evidence / 'actual-public-surface.json', receipt['actual_public_surface'])
    clang_collection = json.loads((evidence / 'compiler-symbolgraph-collection.json').read_text())
    clang_proof = export_clang_declarations(
        derived, exported, clang_collection, before, root / profile['package_resolved_path'])
    write(evidence / 'clang-declaration-export.json', clang_proof)
    receipt['original_clang_declarations'] = {
        'module_map_count': len(clang_proof['module_maps']),
        'header_root_count': len(clang_proof['header_search_paths']),
        'declaration_file_count': len(clang_proof['files']),
        'manifest_sha256': sha256(exported / 'SourceProvenance/ClangImportContext.json')}
    clang_identity = {key: clang_proof[key] for key in (
        'source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256')}
    clang_identity['manifest_sha256'] = receipt['original_clang_declarations']['manifest_sha256']
    exported_proof['files'] = inventory(exported)
    exported_proof['bytes'] = sum(item['bytes'] for item in exported_proof['files'].values())
    write(evidence / 'framework-distribution.json', exported_proof)
    oracle = original_oracles(root, profile)
    write(evidence / 'independent-original-resource-oracles.json', oracle)
    consumer = work / 'external-consumer'
    project = consumer_project(consumer, exported, root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift',
                               dynamic, clang_identity)
    write(evidence / 'consumer-source-inputs.json', inventory(consumer))
    # Preserve all real products/evidence but remove the original absolute path
    # used by generated Bundle.module build-path fallback before consumer build.
    hidden = work / 'producer-derived-preserved'
    require(not hidden.exists(), 'Producer quarantine already exists')
    derived.rename(hidden)
    require(not derived.exists(), 'Producer build-path fallback remains available')
    write(evidence / 'producer-build-path-absent.json', {'original': str(derived), 'preserved_at': str(hidden),
                                                        'original_path_exists': False, 'deleted': False})
    receipt['phase'] = 'EXTERNAL_BINARY_CONSUMER_BUILD'
    write(evidence / 'execution.json', receipt)
    consumer_derived = work / 'consumer-derived'
    command(['xcodebuild', 'build', '-project', str(project), '-scheme', 'OriginalEditorConsumer',
             '-configuration', 'Debug', '-destination', destination, '-derivedDataPath', str(consumer_derived),
             '-resultBundlePath', str(evidence / 'consumer-build.xcresult'), 'ONLY_ACTIVE_ARCH=YES', 'ARCHS=arm64'],
            consumer, evidence, 'external-consumer-build', 600)
    require(not derived.exists() and inventory(exported) == exported_proof['files'], 'External build modified/recreated its producer inputs')
    app = consumer_derived / 'Build/Products/Debug-iphonesimulator/OriginalEditorConsumer.app'
    require(app.is_dir(), 'Actual external consumer app is missing')
    command(['codesign', '--verify', '--strict', str(app)], root, evidence, 'external-consumer-signature', 30)
    for name in dynamic:
        require(inventory(app / 'Frameworks' / name) == inventory(exported / 'Frameworks' / name),
                'The actual consumer did not embed the exact exported framework: ' + name)
    command(['otool', '-l', str(app / 'OriginalEditorConsumer')], root, evidence, 'consumer-main-load-commands', 30)
    if (app / 'OriginalEditorConsumer.debug.dylib').exists():
        command(['otool', '-l', str(app / 'OriginalEditorConsumer.debug.dylib')], root, evidence,
                'consumer-debug-load-commands', 30)
    receipt['actual_consumer_install_names'] = verify_consumer_install_name(app)
    write(evidence / 'consumer-install-names.json', receipt['actual_consumer_install_names'])
    receipt['external_consumer_build'] = 'PASS'
    receipt['public_host_api'] = 'EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN'
    receipt['compiled_consumer_api_probe_sha256'] = sha256(root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift')
    receipt['phase'] = 'RETAIN_SIGNED_CONSUMER'
    write(evidence / 'execution.json', receipt)
    receipt['retained_signed_consumer'] = retain_built_consumer(app, root, evidence, work, before)
    write(evidence / 'retained-consumer.json', receipt['retained_signed_consumer'])
    receipt['phase'] = 'ACTUAL_EXTERNAL_RESOURCE_RUNTIME'
    receipt['verified_runtime_observations'] = []
    write(evidence / 'execution.json', receipt)
    bundle_id = 'org.otzaria.acceptance.original-editor'
    command(['xcrun', 'simctl', 'boot', udid], root, evidence, 'boot-owned-simulator', 60)
    command(['xcrun', 'simctl', 'bootstatus', udid, '-b'], root, evidence, 'boot-status', 180)
    command(['xcrun', 'simctl', 'install', udid, str(app)], root, evidence, 'install-external-consumer', 300)
    installed = command(['xcrun', 'simctl', 'get_app_container', udid, bundle_id, 'app'], root, evidence, 'actual-consumer-app-container', 30).strip()
    data = Path(command(['xcrun', 'simctl', 'get_app_container', udid, bundle_id, 'data'], root, evidence, 'actual-consumer-data-container', 30).strip())
    require(Path(installed).is_dir() and data.is_dir() and udid in Path(installed).parts and udid in data.parts,
            'Actual consumer containers are not in the owned simulator')
    launch_stdout = command(['xcrun', 'simctl', 'help', 'launch'], root, evidence, 'actual-simctl-launch-help', 15)
    launch_stderr, _ = read_regular(evidence / 'actual-simctl-launch-help.stderr.log', 65536)
    launch_help = combine_launch_help(launch_stdout, launch_stderr.decode(errors='replace'))
    for language in ['en', 'he']:
        nonce = str(uuid.uuid4()).upper()
        name = 'consumer-' + language
        output = data / 'Documents' / ('original-editor-' + nonce + '.json')
        require(not output.exists(), 'Stale consumer result')
        original_launch = ['xcrun', 'simctl', 'launch', '--terminate-running-process', udid, bundle_id,
                           '--original-editor-nonce', nonce, '-AppleLanguages', '(' + language + ')',
                           '-AppleLocale', 'he_IL' if language == 'he' else 'en_US']
        launch, capture_request = prepare_launch_capture(evidence, preflight, installed, original_launch, language, launch_help)
        try:
            command(launch, root, evidence, name + '-launch', 30)
            deadline = time.monotonic() + 20
            while not output.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            require(output.is_file() and not output.is_symlink() and 0 < output.stat().st_size <= 65_536,
                    'No bounded actual external consumer result: ' + language)
            raw = output.read_bytes()
            (evidence / (name + '-observation.json')).write_bytes(raw)
            value = verify_observation(json.loads(raw), nonce, language, installed, oracle)
            require(not derived.exists(), 'Producer fallback was recreated before runtime')
            receipt['verified_runtime_observations'].append(value)
            write(evidence / 'execution.json', receipt)
        except BaseException:
            try:
                command([sys.executable, str(root / 'Tools/OriginalEditor/consumer_failure_capture.py'),
                         '--capture-failure', str(capture_request)], root, evidence, name + '-failure-capture', 15)
            except BaseException as diagnostic_error:
                try:
                    write(evidence / (name + '-failure-capture-error.json'),
                          {'error_type': type(diagnostic_error).__name__, 'error': str(diagnostic_error),
                           'primary_launch_or_observation_error_preserved': True})
                except BaseException:
                    # Unavailable diagnostic storage cannot replace the primary failure.
                    pass
            raise
        command(['xcrun', 'simctl', 'terminate', udid, bundle_id], root, evidence, name + '-terminate', 30)
    require(len(receipt['verified_runtime_observations']) == 2, 'Incomplete actual resource-language execution')
    require(source_observation(root) == before, 'Tracked source closure changed during actual framework execution')
    require(verify_hanlin(root / 'Dependencies/Hanlin') == hanlin_before, 'Canonical Hanlin source changed')
    require(inventory(exported) == exported_proof['files'], 'Framework distribution changed during consumer qualification')
    if args.import_abi_receipt:
        after_abi = verify_import_abi(root, args.import_abi_receipt, args.import_abi_sha256, before)
        require(after_abi == installation, 'Original Import ABI changed during SDK build/runtime')
        write(evidence / 'import-abi-after.json', after_abi)
    write(evidence / 'source-after.json', source_observation(root))
    receipt.update(status='ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS', phase='COMPLETE',
                   distribution=str(exported), same_toolchain_only=True, device_framework_build='NOT_RUN',
                   original_43_component_tests='NOT_RERUN', native_editor_ui_tests=0,
                   editable_mount='API_COMPILED_NATIVE_UI_NOT_RUN')
    write(exported / 'QUALIFICATION.json', receipt)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--work', required=True, type=Path)
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--import-abi-receipt', type=Path)
    parser.add_argument('--import-abi-sha256')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    receipt = {'schema': 1, 'status': 'FAIL', 'phase': 'SOURCE_ADMISSION', 'started_at': timestamp(),
               'original_framework_build': 'NOT_RUN', 'external_consumer_build': 'NOT_RUN',
               'native_editor_ui_tests': 0, 'verified_runtime_observations': []}
    def interrupt(signum, frame):
        raise InterruptedError('CI signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        execute(args, receipt)
    except BaseException as error:
        receipt.update(status='FAIL', error_type=type(error).__name__, error=str(error))
    finally:
        if not args.source_only:
            try:
                after = source_observation(args.root.resolve())
                write(args.evidence / 'source-after.json', after)
                before_path = args.evidence / 'source-before.json'
                require(before_path.is_file() and json.loads(before_path.read_text()) == after,
                        'Source closure differs at final observation')
            except BaseException as error:
                write(args.evidence / 'source-after-failure.json', {'error_type': type(error).__name__, 'error': str(error)})
                receipt.update(status='FAIL', source_after_error=str(error))
        receipt['finished_at'] = timestamp()
        write(args.evidence / ('source-admission.json' if args.source_only else 'execution.json'), receipt)
        if receipt.get('distribution'):
            write(Path(receipt['distribution']) / 'QUALIFICATION.json', receipt)
        if not args.source_only:
            preflight_path = args.evidence / 'preflight/preflight.json'
            if preflight_path.is_file():
                preflight = json.loads(preflight_path.read_text())
                identity = current_identity()
                if (preflight.get('source_sha') == identity['source_sha']
                        and preflight.get('run_id') == identity['run_id']
                        and preflight.get('run_attempt') == identity['run_attempt']):
                    cleanup = []
                    for kind, selected in preflight.get('selected', {}).items():
                        udid = selected.get('udid', '')
                        if (kind in {'ipad', 'iphone'} and re.fullmatch(r'[0-9A-Fa-f-]{36}', udid)
                                and selected.get('name') == 'Pinkha-UI27-' + identity['run_id'] + '-' + kind):
                            for operation in ['shutdown', 'delete']:
                                try:
                                    result = subprocess.run(['xcrun', 'simctl', operation, udid], capture_output=True, timeout=60)
                                    cleanup.append({'operation': operation, 'udid': udid, 'returncode': result.returncode,
                                                    'stdout': result.stdout.decode(errors='replace'), 'stderr': result.stderr.decode(errors='replace')})
                                except BaseException as error:
                                    cleanup.append({'operation': operation, 'udid': udid,
                                                    'error_type': type(error).__name__, 'error': str(error)})
                    write(args.evidence / 'owned-simulator-cleanup.json', cleanup)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt['status'] in {'SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN',
              'ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
