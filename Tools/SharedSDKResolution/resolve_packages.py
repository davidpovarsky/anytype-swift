#!/usr/bin/env python3
"""Resolve immutable original graphs on Xcode; never compile or qualify an app.

The only proposed source change is Xcode's actual Package.resolved output.
All original pin objects, including URL/kind/version/revision, must be retained.
The Anytype seed adds only seven source-reviewed Hanlin dependencies; it retains
the old metadata unchanged and is explicitly not an accepted resolved file.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], timeout=120).decode().strip()


def pin_map(lock):
    require(type(lock) is dict and lock.get('version') in (2, 3), 'Unsupported actual resolved-file schema')
    require(type(lock.get('pins')) is list, 'Missing pin array')
    result = {}
    for pin in lock['pins']:
        require(type(pin) is dict and type(pin.get('identity')) is str, 'Malformed pin')
        name = pin['identity']
        require(name and name == name.lower() and name not in result, 'Duplicate or noncanonical package identity')
        require(pin.get('kind') == 'remoteSourceControl' and type(pin.get('location')) is str
                and pin['location'].startswith('https://'), 'Unreviewed package location/kind')
        state = pin.get('state', {})
        require(type(state) is dict and re.fullmatch('[0-9a-f]{40}', state.get('revision', '')),
                'A package revision is not immutable')
        result[name] = pin
    return result


def expected_pins(original, target):
    result = pin_map(original)
    require(len(result) == target['original_pin_count'], 'Original pin count changed')
    for pin in target['expected_new_pins']:
        name = pin['identity']
        require(name not in result, 'A proposed addition replaces an original pin')
        result[name] = pin
    require(len(result) == target['expected_pin_count'], 'Reviewed closure count differs')
    # Validate new entries with the same exact immutable shape check.
    pin_map({'version': original['version'], 'pins': list(result.values())})
    return result


def verify_resolved(actual, expected):
    require(pin_map(actual) == expected, 'Xcode changed an original pin or selected an unreviewed dependency')
    require(set(actual) <= {'version', 'pins', 'originHash'}, 'Unreviewed resolved-file metadata')
    if actual['version'] == 3:
        require(type(actual.get('originHash')) is str and re.fullmatch('[0-9a-f]{64}', actual['originHash']),
                'Xcode did not retain a valid version3 originHash')
    else:
        require('originHash' not in actual, 'Unexpected metadata in version2 lock')


def seed_lock(original, expected):
    seed = dict(original)
    seed['pins'] = [expected[name] for name in sorted(expected)]
    return seed


def run(command, cwd, evidence, name, timeout=1200, *, require_success=True):
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    stdout = evidence / (name + '.stdout.log')
    stderr = evidence / (name + '.stderr.log')
    record = {'argv': [str(x) for x in command], 'cwd': str(cwd), 'timeout_seconds': timeout,
              'started_at': datetime.now(timezone.utc).isoformat(), 'returncode': None, 'timed_out': False}
    process = None
    start = time.monotonic()
    try:
        with stdout.open('xb') as out, stderr.open('xb') as err:
            process = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err, start_new_session=True)
            try:
                record['returncode'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                record['timed_out'] = True
                raise
    except BaseException:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        raise
    finally:
        if process is not None:
            record['returncode'] = process.returncode
        record.update(finished_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - start,
                      stdout_sha256=sha256(stdout) if stdout.exists() else None,
                      stderr_sha256=sha256(stderr) if stderr.exists() else None)
        write(evidence / (name + '.command.json'), record)
    if require_success:
        require(record['returncode'] == 0, 'Actual command failed: ' + name)
    return stdout.read_text(errors='replace')


def stale_lock_failure(record, stdout, stderr):
    diagnostic = (stdout + '\n' + stderr).lower()
    return (record.get('returncode') == 74 and record.get('timed_out') is False
            and 'could not resolve package dependencies' in diagnostic
            and 'an out-of-date resolved file was detected' in diagnostic
            and 'automatic dependency resolution is disabled' in diagnostic
            and 'requirements have changed' in diagnostic
            and not any(message in diagnostic for message in (
                'authentication failed', 'repository not found', 'failed to clone',
                'could not connect', "couldn't connect", 'ssl error', 'tls error', 'permission denied')))


def resolve_strict_first(command, root, output, active_lock, canonical_lock, expected, *, runner=run):
    """Never automatically resolve an already acceptable or unrelated failing graph."""
    strict = [*command, '-onlyUsePackageVersionsFromResolvedFile']
    runner(strict, root, output, 'actual-strict-first', 1800, require_success=False)
    first = json.loads((output / 'actual-strict-first.command.json').read_bytes())
    if first['returncode'] == 0:
        raw = active_lock.read_bytes()
        verify_resolved(json.loads(raw), expected)
        # These are actual successful strict-resolver bytes. No automatic
        # resolution or second strict invocation is needed in this case.
        canonical_lock.write_bytes(raw)
        return raw, {'mode': 'ORIGINAL_STRICT_RESOLVER_ACCEPTED', 'automatic_resolution_invocations': 0,
                     'strict_resolution_invocations': 1}
    stdout = (output / 'actual-strict-first.stdout.log').read_text(errors='replace')
    stderr = (output / 'actual-strict-first.stderr.log').read_text(errors='replace')
    require(stale_lock_failure(first, stdout, stderr), 'Strict resolution failed for a reason not admitted for metadata refresh')
    (output / 'Package.resolved.after-strict-failure').write_bytes(active_lock.read_bytes())
    verify_resolved(json.loads(active_lock.read_bytes()), expected)
    runner(command, root, output, 'actual-resolve-packages', 1800)
    raw = active_lock.read_bytes()
    verify_resolved(json.loads(raw), expected)
    canonical_lock.write_bytes(raw)
    runner(strict, root, output, 'actual-strict-replay', 900)
    require(active_lock.read_bytes() == raw and canonical_lock.read_bytes() == raw,
            'Strict replay changed the actual Xcode-generated lock')
    return raw, {'mode': 'ACTUAL_STALE_LOCK_RESOLVED_AND_STRICTLY_REPLAYED', 'automatic_resolution_invocations': 1,
                 'strict_resolution_invocations': 2}


def identity(root, target):
    require(git(root, 'rev-parse', 'HEAD') == target['sha'], 'Unexpected immutable source checkout')
    require(not git(root, 'diff', '--name-only', 'HEAD'), 'Preserve and inspect changed source checkout')
    require(not git(root, 'ls-files', '--others', '--exclude-standard', '-z'), 'Fresh source checkout has untracked inputs')
    records = {}
    for name, expected in target['inputs'].items():
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'Missing or aliased original preparation input: ' + name)
        raw = path.read_bytes()
        require(len(raw) == expected['bytes'] and git_blob(raw) == expected['git_blob']
                and git(root, 'rev-parse', 'HEAD:' + name) == expected['git_blob'],
                'Actual original input bytes differ: ' + name)
        records[name] = {'git_blob': expected['git_blob'], 'bytes': len(raw), 'sha256': sha256(path)}
    return {'repository': target['repository'], 'sha': target['sha'], 'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
            'inputs': records}


def graph_inputs(root):
    """Hash actual graph declarations, not merely commit labels or a lock file."""
    rows = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    selected = [p for p in rows if p and (
        re.search(r'(^|/)Package(?:@swift[^/]*)?\.swift$', p)
        or p.endswith(('/project.pbxproj', '.xcscheme', '.xcconfig', '/Package.resolved'))
        or p in ('.gitmodules', 'Podfile')
    ) and not p.startswith(('docs/', 'Tests/', 'Tools/OriginalEditor/original_project'))]
    records = {}
    for name in sorted(selected):
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'Graph input missing/aliased: ' + name)
        records[name] = {'bytes': path.stat().st_size, 'sha256': sha256(path), 'git_blob': git_blob(path.read_bytes())}
    return records


def package_graph(actual):
    objects = actual['objects']
    references = {key: value for key, value in objects.items() if value.get('isa') in {
        'XCLocalSwiftPackageReference', 'XCRemoteSwiftPackageReference', 'XCSwiftPackageProductDependency'}}
    owners = {}
    for key, value in objects.items():
        if value.get('isa') not in {'PBXProject', 'PBXNativeTarget'}:
            continue
        owner = {'isa': value['isa'], 'name': value.get('name')}
        for field in ('packageReferences', 'packageProductDependencies'):
            attachment = value.get(field)
            require(attachment is None or (type(attachment) is list
                    and all(type(item) is str for item in attachment)
                    and len(attachment) == len(set(attachment))), 'Malformed package ownership attachment')
            for item in attachment or []:
                allowed = {'XCLocalSwiftPackageReference', 'XCRemoteSwiftPackageReference'} if field == 'packageReferences' else {'XCSwiftPackageProductDependency'}
                require(item in references and references[item]['isa'] in allowed,
                        'Dangling or mismatched package ownership attachment')
            owner[field] = attachment
        owners[key] = owner
    return {'references': references, 'owners': owners}


def project_package_references(path):
    actual = json.loads(subprocess.check_output(['plutil', '-convert', 'json', '-o', '-', str(path)], timeout=60))
    return package_graph(actual)


def require_unchanged_package_graph(before, after):
    require(after == before, 'Original package requirements/products or owning project/target attachments changed')


def has_package_graph(graph):
    return bool(graph['references']) or any(owner[field] for owner in graph['owners'].values()
                                           for field in ('packageReferences', 'packageProductDependencies'))


def workspace_inputs(root):
    """Capture the real CocoaPods workspace graph and actual generated settings."""
    workspace = root / 'Maktabah.xcworkspace'
    declaration = workspace / 'contents.xcworkspacedata'
    require(declaration.is_file() and not declaration.is_symlink(), 'Missing real generated workspace declaration')
    references = [entry.attrib.get('location', '') for entry in ET.fromstring(declaration.read_bytes()).iter('FileRef')]
    require(sorted(references) == ['group:Maktabah.xcodeproj', 'group:Pods/Pods.xcodeproj'],
            'Unreviewed generated workspace project membership')
    pods_packages = project_package_references(root / 'Pods/Pods.xcodeproj/project.pbxproj')
    require(not has_package_graph(pods_packages),
            'Generated CocoaPods project added an unreviewed Swift package graph')
    paths = {declaration, root / 'Pods/Pods.xcodeproj/project.pbxproj', root / 'Podfile.lock', root / 'Pods/Manifest.lock'}
    for directory in (workspace / 'xcshareddata', root / 'Pods/Pods.xcodeproj/xcshareddata', root / 'Pods/Target Support Files'):
        if directory.exists():
            paths.update(p for p in directory.rglob('*') if p.is_file() and p.suffix in {'.xcscheme', '.xcconfig', '.xcsettings'})
    records = {}
    for path in sorted(paths):
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root),
                'Missing or aliased generated workspace graph input')
        records[path.relative_to(root).as_posix()] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    require(any(name.endswith('.xcconfig') for name in records), 'Missing actual CocoaPods generated settings')
    return {'project_references': references, 'files': records,
            'app_package_references': project_package_references(root / 'Maktabah.xcodeproj/project.pbxproj'),
            'pods_package_graph': pods_packages,
            'pods_has_additional_swift_package_references': False}


def load_original_stage2(root):
    path = root / 'Scripts/CI/hq-stage2-focused-apple.py'
    spec = importlib.util.spec_from_file_location('original_stage2_lock_preparation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_maktabah(root, output, hanlin_sha):
    """Call only three original preparation operations; no engine or app build."""
    module = load_original_stage2(root)
    config = json.loads(module.INPUTS.read_bytes())
    require(config['hanlin_gitlink'] == hanlin_sha, 'Unexpected original Hanlin gitlink')
    # The original logger requires evidence to be inside its actual app root.
    module.OUT = root / 'build/lock-resolution-preparation-waxqv0pw'
    module.OUT.mkdir(parents=True, exist_ok=False)
    report = {'status': 'PREPARING_RESOLVER_INPUTS_ONLY', 'app_build_executed': False,
              'package_pins': module.pins(root / 'Maktabah.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved')}
    try:
        module.prepare_original_hanlin(config, report)
        module.prepare_react_sources(config, report)
        module.install_real_pods(report)
        module.prepare_original_hanlin(config, report, verify_only=True)
        privacy = 'Source/PrivacyInfo.xcprivacy'
        if git(root, 'diff', '--name-only', 'HEAD', '--', privacy):
            module.audit_generated_privacy(report, git(root, 'rev-parse', 'HEAD:' + privacy))
        report['status'] = 'ORIGINAL_RESOLVER_INPUTS_PREPARED_NO_BUILD'
    finally:
        write(module.OUT / 'preparation.json', report)
        shutil.copytree(module.OUT, output / 'original-preparation')


def prepare_anytype(root, target, output, hanlin_source):
    require(git(hanlin_source, 'rev-parse', 'HEAD') == 'e00498e33f106cc43be0476ffa2e09329c8ca300',
            'Wrong actual original Hanlin checkout')
    require(not (root / 'Dependencies/Hanlin').exists()
            and not (root / 'Dependencies/Middleware/Lib.xcframework').exists()
            and not (root / 'Dependencies/Middleware/PinkhaNativeHeartBuild.json').exists(),
            'Preserve an occupied original dependency installation')
    require(git(root, 'branch', '--show-current') == target['heart_branch'], 'Wrong fresh installer checkout branch')
    run([sys.executable, 'Tools/Hanlin/prepare_sdk.py', '--source', str(hanlin_source)], root, output, 'prepare-hanlin', 300)
    run([sys.executable, 'Tools/Hanlin/prepare_sdk.py', '--check'], root, output, 'verify-hanlin', 120)
    heart = root / 'build/lock-resolution-verified-heart-waxqv0pw'
    require(not heart.exists(), 'Heart verification output already exists')
    heart_evidence = root / 'build/lock-resolution-heart-evidence-waxqv0pw'
    require(not heart_evidence.exists(), 'Heart evidence path already exists')
    run([sys.executable, 'Tools/Hanlin/prepare_original_editor_heart.py', '--source-run-id', target['heart_source_run_id'],
         '--output', str(heart), '--evidence', str(heart_evidence / 'source')], root, output, 'verify-original-heart', 1200)
    run([sys.executable, 'Tools/PinkhaNativeDerived/install_verified_heart.py',
         '--archive', str(heart / 'Pinkha-Universal-Verified-Heart-r14.tar.gz'),
         '--inventory', 'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14/native-heart-integration.json',
         '--patch', 'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14/native-heart-integration.patch',
         '--app-source', str(root), '--source-run-id', target['heart_source_run_id'],
         '--expected-app-branch', target['heart_branch'], '--evidence', str(heart_evidence / 'installation')],
        root, output, 'install-original-heart', 300)
    require((root / target['binary_path'] / 'Info.plist').is_file(), 'Original local binaryTarget is absent')
    shutil.copytree(heart_evidence, output / 'original-heart')


def checkout_proof(checkouts, expected):
    require(checkouts.is_dir() and not checkouts.is_symlink(), 'Missing real Xcode dependency checkouts')
    records = {}
    for folder in sorted(checkouts.iterdir()):
        require(folder.is_dir() and not folder.is_symlink(), 'Unexpected checkout entry')
        name = folder.name.lower()
        require(name in expected and name not in records, 'Unreviewed dependency checkout: ' + name)
        actual = git(folder, 'rev-parse', 'HEAD')
        require(actual == expected[name]['state']['revision'], 'Actual dependency revision changed: ' + name)
        require(not git(folder, 'diff', '--name-only', 'HEAD'), 'Dirty dependency source: ' + name)
        require(not git(folder, 'ls-files', '--others', '-z'), 'Extra tracked-or-ignored build inputs: ' + name)
        records[name] = {'revision': actual, 'package_manifest_sha256': sha256(folder / 'Package.swift')}
    required = {'hanlin-streaming-markdown', 'equatable', 'highlightswift', 'iosmath', 'swiftui-shimmer',
                'swift-markdown', 'swift-cmark', 'torahinspectorkit'}
    require(required <= set(records), 'A required shared runtime package was not actually materialized')
    return {'checkouts': records, 'locked_but_not_materialized': sorted(set(expected) - set(records)),
            'all_actual_checkout_files_tracked': True}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--kind', choices=['anytype', 'maktabah'], required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hanlin-source', type=Path)
    parser.add_argument('--prepare-maktabah-only', action='store_true')
    args = parser.parse_args()
    contract = json.loads(args.contract.read_bytes())
    require(contract['schema'] == 1 and contract['context'] == 'waxqv0pw', 'Wrong reviewed resolution contract')
    target = contract['targets'][args.kind]
    require(not target.get('execution_blocked'), target.get('execution_blocked', 'Target execution is blocked'))
    root, output = args.root.resolve(), args.output.resolve()
    require(platform.system() == 'Darwin' and platform.machine() == 'arm64', 'Requires actual native Apple ARM64 Xcode')
    require(os.environ.get('GITHUB_REPOSITORY') == contract['repository']
            and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF') == 'refs/heads/' + contract['workflow_branch']
            and os.environ.get('GITHUB_WORKFLOW_REF') == contract['repository'] + '/' + contract['workflow_file']
                + '@refs/heads/' + contract['workflow_branch'], 'Not the one reviewed isolated resolver workflow')
    workspace = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    require(root == workspace / target['source_path'] and root.is_dir(), 'Wrong owned immutable checkout path')
    expected_output = workspace / 'resolution-evidence-waxqv0pw' / args.kind
    if args.prepare_maktabah_only:
        require(args.kind == 'maktabah' and output == expected_output and output.is_dir()
                and git(root, 'rev-parse', 'HEAD') == target['sha'], 'Invalid original preparation subprocess')
        prepare_maktabah(root, output, contract['hanlin_sha'])
        return
    require(output == expected_output and not output.exists(), 'Preserve existing/foreign resolution evidence')
    output.mkdir(parents=True)
    def interrupted(*_):
        raise InterruptedError('Owned resolver interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    report = {'status': 'FAILED', 'scope': 'REAL_XCODE_PACKAGE_RESOLUTION_ONLY', 'source': target['sha'],
              'run_id': os.environ.get('GITHUB_RUN_ID'), 'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
              'workflow_sha': os.environ.get('GITHUB_SHA'), 'contract_sha256': sha256(args.contract),
              'application_or_framework_compilation_executed': False,
              'package_manifest_evaluation_by_xcode': True,
              'tests_executed': 0, 'native_acceptance': 'NOT_RUN'}
    try:
        toolkit = Path(__file__).resolve().parents[2]
        require(toolkit == workspace / 'resolver-kit' and git(toolkit, 'rev-parse', 'HEAD') == os.environ['GITHUB_SHA'],
                'Actual resolver implementation checkout differs from workflow SHA')
        for name in ('Tools/SharedSDKResolution/resolve_packages.py', 'Tools/SharedSDKResolution/contract.json',
                     contract['workflow_file']):
            require(git_blob((toolkit / name).read_bytes()) == git(toolkit, 'rev-parse', 'HEAD:' + name),
                    'Resolver implementation working bytes changed: ' + name)
        write(output / 'source-before.json', identity(root, target))
        initial_graph = graph_inputs(root)
        write(output / 'graph-before-preparation.json', initial_graph)
        original_package_references = project_package_references(root / target['project'] / 'project.pbxproj')
        if 'local_package_paths' in target:
            actual_local_paths = sorted(value['relativePath'] for value in original_package_references['references'].values()
                                        if value.get('isa') == 'XCLocalSwiftPackageReference')
            require(actual_local_paths == sorted(target['local_package_paths']), 'Unreviewed original local package membership')
        write(output / 'project-package-references-original.json', original_package_references)
        lock = root / target['lock']
        original_raw = lock.read_bytes()
        original = json.loads(original_raw)
        expected = expected_pins(original, target)
        (output / 'Package.resolved.original').write_bytes(original_raw)
        write(output / 'expected-pin-closure.json', expected)
        xcode = run(['xcodebuild', '-version'], root, output, 'xcode-version', 60)
        require(xcode.strip() == contract['xcode_version'], 'Requires the original exact Xcode27 toolchain')
        sdk = run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version'], root, output, 'sdk-version', 60).strip()
        require(sdk == contract['simulator_sdk_version'], 'Unexpected Simulator SDK')
        swift = run(['xcrun', 'swiftc', '--version'], root, output, 'swift-version', 60)
        require(swift.splitlines()[0] == contract['swift_compiler_version'], 'Unexpected original Swift compiler')
        help_text = run(['xcodebuild', '-help'], root, output, 'xcode-help', 60)
        help_text += (output / 'xcode-help.stderr.log').read_text(errors='replace')
        require('-resolvePackageDependencies' in help_text and '-onlyUsePackageVersionsFromResolvedFile' in help_text,
                'Original strict resolver flags unavailable')
        if args.kind == 'anytype':
            require(args.hanlin_source is not None, 'Original canonical Hanlin source required')
            prepare_anytype(root, target, output, args.hanlin_source.resolve())
            # Metadata is copied verbatim from the prior actual lock. Only Xcode
            # may produce a new originHash. This seed is not admitted output.
            seed = seed_lock(original, expected)
            seed_raw = (json.dumps(seed, indent=2) + '\n').encode()
            lock.write_bytes(seed_raw)
            active_lock = lock
            clone_root = root / 'build/lock-resolution-derived-waxqv0pw/SourcePackages'
            project_args = ['-project', target['project'], '-scheme', target['scheme'], '-configuration', target['configuration']]
        else:
            run([sys.executable, str(Path(__file__).resolve()), '--contract', str(args.contract.resolve()),
                 '--kind', args.kind, '--root', str(root), '--output', str(output), '--prepare-maktabah-only'],
                root, output, 'original-workspace-preparation', 2400)
            active_lock = root / target['workspace_lock']
            require(active_lock.read_bytes() == original_raw, 'Original workspace did not stage the exact committed lock')
            clone_root = root / 'build/SourcePackages'
            project_args = ['-workspace', target['workspace'], '-scheme', target['scheme']]
        require(not clone_root.exists(), 'Preserve an occupied package-resolution cache')
        prepared_graph = graph_inputs(root)
        allowed = {target['lock']}
        if args.kind == 'maktabah':
            allowed.add('Maktabah.xcodeproj/project.pbxproj')
        require(set(initial_graph) == set(prepared_graph)
                and all(initial_graph[p] == prepared_graph[p] for p in initial_graph if p not in allowed),
                'Original preparation changed a package-graph input beyond its reviewed boundary')
        write(output / 'graph-prepared.json', prepared_graph)
        prepared_workspace = workspace_inputs(root) if args.kind == 'maktabah' else None
        if prepared_workspace is not None:
            require_unchanged_package_graph(original_package_references, prepared_workspace['app_package_references'])
            write(output / 'workspace-graph-prepared.json', prepared_workspace)
        (output / 'Package.resolved.seed').write_bytes(active_lock.read_bytes())
        command = ['xcodebuild', '-resolvePackageDependencies', *project_args,
                   '-clonedSourcePackagesDirPath', str(clone_root)]
        resolved_raw, resolution_path = resolve_strict_first(command, root, output, active_lock, lock, expected)
        resolved = json.loads(resolved_raw)
        (output / 'Package.resolved.xcode-output').write_bytes(resolved_raw)
        require(active_lock.read_bytes() == resolved_raw and lock.read_bytes() == resolved_raw,
                'Accepted actual lock output changed after resolution')
        if prepared_workspace is not None:
            after_workspace = workspace_inputs(root)
            write(output / 'workspace-graph-after.json', after_workspace)
            require(after_workspace == prepared_workspace, 'Resolution changed actual CocoaPods workspace graph/settings')
        proof = checkout_proof(clone_root / 'checkouts', expected)
        write(output / 'actual-package-checkouts.json', proof)
        final_graph = graph_inputs(root)
        require(set(final_graph) == set(prepared_graph)
                and all(final_graph[p] == prepared_graph[p] for p in final_graph if p != target['lock']),
                'Package resolution changed another actual graph input')
        write(output / 'graph-after.json', final_graph)
        changed = git(root, 'diff', '--name-only', '--ignore-submodules=untracked', 'HEAD').splitlines()
        allowed_source_changes = {target['lock']}
        if args.kind == 'maktabah':
            allowed_source_changes.update({'Maktabah.xcodeproj/project.pbxproj', 'Source/PrivacyInfo.xcprivacy'})
        require(set(changed) <= allowed_source_changes, 'Source changed outside original preparation/lock output')
        require(git(root, 'rev-parse', 'HEAD') == target['sha'], 'Immutable source HEAD changed')
        run([sys.executable, 'Tools/Hanlin/prepare_sdk.py', '--check'], root, output, 'hanlin-final', 120) if args.kind == 'anytype' else run(
            [sys.executable, 'Scripts/CI/prepare-hanlin-sdk.py', '--sha', contract['hanlin_sha'], '--verify-only',
             '--output', str(output / 'hanlin-final.json')], root, output, 'hanlin-final', 120)
        report.update(status='ACTUAL_XCODE_STRICT_PACKAGE_GRAPH_ACCEPTED_NO_BUILD', resolution_path=resolution_path,
                      original_pin_count=len(pin_map(original)), actual_pin_count=len(expected),
                      all_original_pin_objects_unchanged=True,
                      exact_added_identities=sorted(p['identity'] for p in target['expected_new_pins']),
                      original_lock_version=original['version'], actual_lock_version=resolved['version'],
                      original_originHash=original.get('originHash'), actual_originHash=resolved.get('originHash'),
                      proposed_project_lock=target['lock'], output_sha256=hashlib.sha256(resolved_raw).hexdigest(),
                      output_git_blob=git_blob(resolved_raw), original_source_sha_unchanged=True,
                      tracked_preparation_changes=changed)
        write(output / 'source-after.json', {'sha': target['sha'], 'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
                                           'actual_graph_inputs': final_graph, 'tracked_changes': changed})
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        try:
            write(output / 'source-after-attempt.json', {
                'sha': git(root, 'rev-parse', 'HEAD'), 'tree': git(root, 'rev-parse', 'HEAD^{tree}'),
                'actual_graph_inputs': graph_inputs(root),
                'tracked_changes': git(root, 'diff', '--name-only', '--ignore-submodules=untracked', 'HEAD').splitlines()})
            for label, name in [('project', target['lock']), ('workspace', target.get('workspace_lock'))]:
                if name and (root / name).is_file():
                    (output / ('Package.resolved.last-observed-' + label)).write_bytes((root / name).read_bytes())
        except BaseException as evidence_error:
            report['final_readonly_evidence_error'] = type(evidence_error).__name__ + ': ' + str(evidence_error)
        write(output / 'RESOLUTION.json', report)
        print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
