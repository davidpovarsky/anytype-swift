#!/usr/bin/env python3
"""Build the original Import mobile ABI on the owner's dedicated Mac.

Consumes source-bound qualifications from their sole execution owners. The
original gomobile input observer, generated-source verifier and Invocation
consumer are reused byte-for-byte. It does not run a generator or Native test.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
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

from local_execution import current_identity, git, require, sha
from import_abi_input import EXPORTS, LIB, exact_file
from reused_abi_history import history_proofs


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def row(path, name):
    require(path.is_file() and not path.is_symlink(), 'Expected regular source/evidence')
    size = path.stat().st_size
    content, blob = hashlib.sha256(), hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
    count = 0
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            count += len(block)
            content.update(block)
            blob.update(block)
    require(count == size and path.stat().st_size == size, 'Source/evidence changed during inventory')
    return {'path': name, 'bytes': size, 'sha256': content.hexdigest(), 'git_blob': blob.hexdigest()}


def reference(path, evidence):
    value = row(path, path.relative_to(evidence).as_posix())
    value.pop('git_blob')
    return value


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Commands:
    def __init__(self, evidence, env, deadline):
        self.evidence, self.env, self.deadline, self.items = evidence, env, deadline, []
        self.owned_groups_drained = True

    @staticmethod
    def group_exists(group):
        try:
            os.killpg(group, 0)
            return True
        except ProcessLookupError:
            return False

    @classmethod
    def drain(cls, process):
        for signum in (signal.SIGTERM, signal.SIGKILL):
            if not cls.group_exists(process.pid):
                return True
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                return True
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                process.poll()
                if not cls.group_exists(process.pid):
                    return True
                time.sleep(0.05)
        return not cls.group_exists(process.pid)

    def require(self, name, argv, cwd, timeout):
        require(not any(item['label'] == name for item in self.items), 'Repeated command label')
        timeout = min(timeout, self.deadline - time.time())
        require(timeout > 0, 'Owned ABI job deadline expired')
        out, err = self.evidence / (name + '.stdout.log'), self.evidence / (name + '.stderr.log')
        receipt = {'label': name, 'argv': list(map(str, argv)), 'cwd': str(cwd),
                   'started_at': datetime.now(timezone.utc).isoformat(),
                   'stdout': out.name, 'stderr': err.name, 'timed_out': False}
        process = None
        try:
            with out.open('xb') as stdout, err.open('xb') as stderr:
                process = subprocess.Popen(receipt['argv'], cwd=cwd, env=self.env,
                                           stdout=stdout, stderr=stderr, start_new_session=True)
                receipt['pid'] = process.pid
                try:
                    receipt['returncode'] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    receipt['timed_out'] = True
                    raise
        finally:
            if process is not None:
                receipt['owned_group_drained'] = self.drain(process)
                self.owned_groups_drained &= receipt['owned_group_drained']
                receipt['returncode'] = process.returncode
            receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
            receipt['stdout_row'], receipt['stderr_row'] = reference(out, self.evidence), reference(err, self.evidence)
            proof = {**receipt, 'command': receipt['argv'],
                     'stdout': receipt['stdout_row'], 'stderr': receipt['stderr_row']}
            write(self.evidence / (name + '.command.json'), proof)
            self.items.append(receipt)
            write(self.evidence / 'COMMANDS.json', self.items)
        require(receipt['returncode'] == 0 and not receipt['timed_out'] and self.owned_groups_drained,
                'Actual ABI command failed or left a child process: ' + name)
        return out


def execute(args, result):
    root, heart, work, evidence, proof_index = map(lambda p: Path(p).resolve(),
        (args.root, args.native_heart, args.work, args.evidence, args.proof_index))
    identity = current_identity()
    require(identity['producer_kind'] == 'local-mac' and identity['local_execution']['root'] == str(root),
            'Actual local SDK execution required')
    require(not git(root, 'diff', '--name-only', 'HEAD') and 0 < args.timeout <= 10800,
            'Clean exact SDK source and finite build deadline required')
    require(work.is_relative_to(root / 'build') and evidence.is_relative_to(root / 'build')
            and work != evidence and not work.is_relative_to(evidence)
            and not evidence.is_relative_to(work) and not work.exists() and not evidence.exists(),
            'Fresh owned disjoint ABI roots required')
    require(proof_index.is_file() and not proof_index.is_symlink() and sha(proof_index) == args.proof_index_sha256,
            'Frozen input qualification index differs')
    frozen = json.loads(proof_index.read_bytes())
    require(frozen['schema'] in ('otzaria.local-abi-input-qualifications/1',
                                  'otzaria.local-abi-input-qualifications/2')
            and frozen['sdk_source_sha'] == identity['source_sha']
            and set(frozen['proofs']) == {'generation_qualification', 'changed_swift_qualification', 'final_native_rpc_union'},
            'Missing separate qualified generation, Swift and Native inputs')
    proofs = {name: json.loads(exact_file(proof_index.parent, item).read_bytes())
              for name, item in frozen['proofs'].items()}
    fresh_swift = frozen['schema'].endswith('/2')
    if fresh_swift:
        from fresh_swift_input import qualify, copy_evidence
        historical = qualify(proof_index.parent, frozen['historical_receipts'],
                             frozen['fresh_changed_swift'], exact_file)
    else:
        require('fresh_changed_swift' not in frozen, 'Legacy input cannot silently admit fresh Swift proof')
        historical = history_proofs(proof_index.parent, frozen['historical_receipts'], exact_file)
    require(all(proofs[name] == value for name, value in historical.items()),
            'Historical evidence normalization differs from authenticated source bytes')
    native = proofs['final_native_rpc_union']
    counts = {'native9': 9, 'rpc9': 9, 'cancel_panic': 1, 'bundled_semantic': 6,
              'schema_closure': 11, 'relation_target_closure': 12,
              'imported_creation_date': 6, 'bounded_native_metadata': 12}
    require(native.get('status') == 'PASS' and native['counts'] == {
        key: {'passes': count, 'failures': 0, 'skipped': 0, 'not_run': 0} for key, count in counts.items()}
            and native['source_module_link_stability'] == 'PASS' and native['owned_command_groups_drained'],
            'The complete actual native union must pass before any ABI build')
    native_tree = native['native_source_tree']
    require(git(heart, 'write-tree') == native_tree and not git(heart, 'diff', '--name-only'),
            'Materialized original Heart source differs from qualified union')
    require(not (root / LIB).exists() and not (heart / 'dist/ios/Lib.xcframework').exists(),
            'Refusing existing ABI products')
    helper_manifest = json.loads((root / 'Tools/OriginalEditor/ImportRPC/REUSED_ABI_HELPERS.json').read_bytes())
    for item in helper_manifest['files']:
        require(row(root / item['path'], item['path']) == item
                and git(root, 'rev-parse', 'HEAD:' + item['path']) == item['git_blob'],
                'The original reused ABI helper differs')
    original = load(root / 'Tools/OriginalEditor/ImportRPC/build_original_import_abi.py', 'original_abi_helpers')
    mobile = load(root / 'Tools/OriginalEditor/ImportRPC/abi_mobile_inputs.py', 'original_mobile_observer')
    pinned = load(root / 'Tools/OriginalEditor/ABIPinnedWrapper/pinned_wrapper.py', 'audited_pinned_wrapper')
    installer = load(root / 'Tools/OriginalEditor/ImportRPC/install_import_rpc_abi.py', 'original_generated_verifier')
    heart_helper_path = root / 'Tools/PinkhaNativeDerived/build_custom_heart.py'
    require(sha(heart_helper_path) == original.HELPER_SHA, 'Original Heart binary inspector differs')
    heart_helper = load(heart_helper_path, 'original_heart_inspector')
    outputs = json.loads((root / 'Tools/OriginalEditor/GeneratedImport/GENERATED_OUTPUT_INDEX.json').read_bytes())
    generated = sorted(outputs['swift'] + outputs['middleware'], key=lambda r: r['path'])
    require(len(generated) == 733, 'Original generated source inventory differs')
    installer.verify_committed_generated(root, generated)
    work.mkdir(parents=True); evidence.mkdir(parents=True)
    result['_owned_evidence'] = True
    for name, item in frozen['proofs'].items():
        shutil.copyfile(proof_index.parent / item['path'], evidence / (name + '.json'))
    historical_receipts = {}
    for name, item in frozen['historical_receipts'].items():
        target = evidence / 'historical' / (name + '.json')
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(exact_file(proof_index.parent, item), target)
        historical_receipts[name] = reference(target, evidence)
    fresh_receipt = None
    if fresh_swift:
        fresh_receipt = copy_evidence(proof_index.parent, frozen['fresh_changed_swift'],
                                      evidence / 'fresh-swift', exact_file, reference)
        require(qualify(evidence, historical_receipts, fresh_receipt, exact_file) == historical,
                'Copied fresh Swift evidence differs from its actual producer')
    result.update(phase='ORIGINAL_MOBILE_BUILD', sdk_source_sha=identity['source_sha'], native_source_tree=native_tree)
    write(evidence / 'RESULT.json', result)
    env = os.environ.copy()
    env['PATH'] = str(Path(args.go_root).resolve() / 'bin') + os.pathsep + env['PATH']
    env['GOPATH'] = str(work / 'go')
    env['GOMODCACHE'] = str(Path(args.go_mod_cache).resolve())
    env['GOCACHE'] = str(Path(args.go_build_cache).resolve())
    env['GOMAXPROCS'] = '4'
    env.pop('GOWORK', None)
    env['TMPDIR'] = str(work / 'tmp'); Path(env['TMPDIR']).mkdir()
    commands = Commands(evidence, env, time.time() + args.timeout)
    require(commands.require('go-version', ['go', 'version'], heart, 30).read_text().strip()
            == 'go version go1.26.5 darwin/arm64', 'Qualified original Go toolchain required')
    require(commands.require('xcode-version', ['xcodebuild', '-version'], heart, 30).read_text().strip()
            == 'Xcode 27.0\nBuild version 27A266a', 'Qualified Xcode27 required')
    go_compiler = Path(args.go_root).resolve() / 'bin/go'
    toolchain = {'go': row(go_compiler, 'go')}
    require(toolchain['go'] == proofs['generation_qualification']['go_compiler_driver'],
            'ABI Go compiler differs from the qualified original generation')
    swiftc = Path(commands.require('swiftc-path', ['xcrun', '--find', 'swiftc'], root, 30).read_text().strip()).resolve()
    toolchain['swiftc'] = row(swiftc, 'swiftc')
    require(toolchain['swiftc'] == proofs['changed_swift_qualification']['actual_compiler_context']['compiler_driver'],
            'ABI compiler differs from the reused changed-Swift qualification')
    observed_tools = [{'file': str(go_compiler), 'identity': toolchain['go']},
                      {'file': str(swiftc), 'identity': toolchain['swiftc']}]
    require(Path(commands.require('go-root', ['go', 'env', 'GOROOT'], heart, 30).read_text().strip()).resolve()
            == Path(args.go_root).resolve(), 'Actual Go installation root differs')
    sdk_context = {}
    for sdk in ('iphoneos', 'iphonesimulator'):
        sdk_context[sdk] = {
            'sdk_root': commands.require(sdk + '-root', ['xcrun', '--sdk', sdk, '--show-sdk-path'], root, 30).read_text().strip(),
            'clang': commands.require(sdk + '-clang', ['xcrun', '--sdk', sdk, '--find', 'clang'], root, 30).read_text().strip(),
            'sdk_version': commands.require(sdk + '-version', ['xcrun', '--sdk', sdk, '--show-sdk-version'], root, 30).read_text().strip()}
        clang = Path(sdk_context[sdk]['clang']).resolve()
        require(clang.parent == swiftc.parent, 'Actual C and Swift toolchains differ')
        settings = Path(sdk_context[sdk]['sdk_root']) / 'SDKSettings.plist'
        sdk_context[sdk]['sdk_settings'] = row(settings, str(settings))
        observed_tools.append({'file': str(clang), 'identity': row(clang, sdk + '-clang')})
    for name in ('lipo', 'nm', 'otool'):
        tool = Path(commands.require(name + '-path', ['xcrun', '--find', name], root, 30).read_text().strip()).resolve()
        observed_tools.append({'file': str(tool), 'identity': row(tool, name)})
    write(evidence / 'TOOLCHAIN.json', {'executables': observed_tools, 'sdks': sdk_context})
    for arch in ('darwin-arm64', 'darwin-amd64', 'ios-arm64', 'ios-arm64-sim', 'ios-amd64'):
        destination = heart / 'deps/libs' / (arch + '.tar.gz')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            commands.require('tantivy-download-' + arch, ['curl', '--fail', '--location', '--silent', '--show-error',
                '--connect-timeout', '20', '--max-time', '180', '--output', str(destination),
                'https://github.com/anyproto/tantivy-go/releases/download/v1.0.6/' + destination.name], heart, 190)
        write(evidence / ('TANTIVY_' + arch + '.json'), heart_helper.fetch_tantivy(heart, arch))
    link_inputs = original.source_inventory(heart, ['deps/libs'])
    write(evidence / 'NATIVE_LINK_INPUTS.json', {'files': link_inputs})
    modules = mobile.json_objects(commands.require('module-versions', ['go', 'list', '-m', '-json', 'all'], heart, 1500).read_text())
    commands.require('download-gomobile-module', ['go', 'mod', 'download', 'golang.org/x/mobile'], heart, 180)
    module = json.loads(commands.require('mobile-module', ['go', 'list', '-m', '-json', 'golang.org/x/mobile'], heart, 60).read_text())
    mobile_module = mobile.admit_mobile_module(module, env['GOMODCACHE'], row)
    write(evidence / 'GOMOBILE_SOURCE.json', mobile_module)
    commands.require('modules-before', ['go', 'mod', 'verify'], heart, 900)
    for name in ('gomobile', 'gobind'):
        commands.require('build-' + name, ['go', 'build', '-o', str(work / name), 'golang.org/x/mobile/cmd/' + name], heart, 1200)
        commands.require('buildinfo-' + name, ['go', 'version', '-m', str(work / name)], heart, 30)
    env['PATH'] = str(work) + os.pathsep + env['PATH']
    commands.require('gomobile-init', [str(work / 'gomobile'), 'init'], heart, 1200)
    framework = heart / 'dist/ios/Lib.xcframework'; framework.parent.mkdir(parents=True, exist_ok=True)
    marker = 'otzaria-original-import-rpc-' + native_tree
    ldflags = ('-X github.com/anyproto/anytype-heart/util/vcs.GitSummary=' + marker
               + ' -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=d98420b1113536afd08cde6de9a5816f6d27ffff')
    launch = pinned.prepare(root, heart, work, evidence, env, modules,
                            Path(args.go_root).resolve(), sdk_context, ldflags, commands.deadline)
    ordinary_path = env['PATH']
    try:
        env['PATH'] = launch['path_prefix'] + os.pathsep + ordinary_path
        commands.require('gomobile_bind', [str(work / 'gomobile'), 'bind', '-x', '-work', '-tags', mobile.TAGS,
            '-ldflags', ldflags, '-target=ios', '-o', str(framework),
            'github.com/anyproto/anytype-heart/clientlibrary/service', 'github.com/anyproto/anytype-heart/core'], heart, 6000)
        bind = commands.items[-1]
    finally:
        env['PATH'] = ordinary_path
    pinned_row, pinned_observation = pinned.collect(launch)
    compiler_inputs = mobile.capture(commands, bind, heart, work, evidence, env, sdk_context,
                                    modules, Path(args.go_root).resolve(), ldflags, row, write)
    commands.require('modules-after', ['go', 'mod', 'verify'], heart, 900)
    commands.require('iosrepack', ['go', 'run', 'cmd/iosrepack/main.go'], heart, 600)
    slices = heart_helper.verify_framework_slices(framework, marker)
    write(evidence / 'MOBILE_SLICES.json', slices)
    libraries = plistlib.loads((framework / 'Info.plist').read_bytes())['AvailableLibraries']
    require(len(libraries) == 2, 'Original mobile distribution must contain iOS and Simulator libraries')
    platforms, exports = {}, []
    for library in libraries:
        require(library['SupportedPlatform'] == 'ios'
                and library.get('SupportedPlatformVariant') in (None, 'simulator'), 'Unexpected mobile platform')
        platform = 'ios-simulator' if library.get('SupportedPlatformVariant') else 'ios'
        require(platform not in platforms and library['LibraryPath'] == 'Lib.framework', 'Repeated or unexpected original mobile library')
        platforms[platform] = library
    require({name: sorted(item['SupportedArchitectures']) for name, item in platforms.items()}
            == {'ios': ['arm64'], 'ios-simulator': ['arm64', 'x86_64']}, 'Original mobile architecture closure differs')
    for number, part in enumerate(slices):
        binary = framework / part['path']
        matches = [name for name, library in platforms.items()
                   if part['path'] == library['LibraryIdentifier'] + '/Lib.framework/Lib'
                   and part['architecture'] in library['SupportedArchitectures']]
        require(len(matches) == 1, 'Actual binary slice does not match mobile distribution metadata')
        thin = binary
        if sum(other['path'] == part['path'] for other in slices) > 1:
            thin = work / ('exports-' + str(number))
            commands.require('thin-' + str(number), ['xcrun', 'lipo', str(binary), '-thin', part['architecture'], '-output', str(thin)], heart, 120)
        require(sha(thin) == part['sha256'], 'Actual mobile slice differs')
        text = commands.require('exports-' + str(number), ['xcrun', 'nm', '-gU', str(thin)], heart, 120).read_text()
        names = {line.split()[-1] for line in text.splitlines() if line.split()}
        require({'_' + symbol for symbol in EXPORTS} <= names, 'Required original Import exports absent')
        headers = '\n'.join(p.read_text() for p in binary.parent.rglob('*.h'))
        require(all(re.search(r'\b' + symbol + r'\b', headers) for symbol in EXPORTS), 'Original mobile declarations absent')
        exports.append({**part, 'platform': matches[0], 'required_exports': sorted(EXPORTS),
                        'command': reference(evidence / ('exports-' + str(number) + '.command.json'), evidence)})
    require(len(slices) == 3 and {(item['platform'], item['architecture']) for item in exports}
            == {('ios', 'arm64'), ('ios-simulator', 'arm64'), ('ios-simulator', 'x86_64')},
            'Actual original mobile slices are incomplete or repeated')
    write(evidence / 'MOBILE_EXPORTS.json', exports)
    shutil.copytree(framework, root / LIB)
    swift_scopes = ['Modules/ProtobufMessages/Package.swift', 'Modules/ProtobufMessages/Sources', LIB]
    swift_inputs = original.source_inventory(root, swift_scopes)
    write(evidence / 'SWIFT_ABI_COMPILER_INPUTS.json', {'files': swift_inputs})
    project = original.probe_project(work / 'consumer', root / 'Modules/ProtobufMessages')
    shutil.copytree(project.parent, evidence / 'consumer-source')
    common = ['xcodebuild', '-project', str(project), '-scheme', 'ImportABIProbe', '-configuration', 'Debug',
              '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', str(work / 'DerivedData'),
              '-clonedSourcePackagesDirPath', str(work / 'SourcePackages'), 'ARCHS=arm64', 'CODE_SIGNING_ALLOWED=NO']
    commands.require('resolve-protobuf', common + ['-resolvePackageDependencies'], project.parent, 1500)
    lock = json.loads((project / 'project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_bytes())['pins']
    original_lock = json.loads((root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_bytes())['pins']
    expected = next(p for p in original_lock if p['identity'] == 'swift-protobuf')
    require(len(lock) == 1 and lock[0]['identity'] == 'swift-protobuf' and lock[0]['state'] == expected['state'],
            'Actual generated invocation resolved another SwiftProtobuf')
    resolved = project / 'project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    shutil.copyfile(resolved, evidence / 'ACTUAL_PACKAGE_RESOLVED.json')
    protobuf = work / 'SourcePackages/checkouts/swift-protobuf'
    require(git(protobuf, 'rev-parse', 'HEAD') == expected['state']['revision']
            and not git(protobuf, 'status', '--porcelain', '--untracked-files=no'), 'Actual SwiftProtobuf checkout differs')
    protobuf_scopes = ['Package.swift', 'Sources']
    protobuf_inputs = original.source_inventory(protobuf, protobuf_scopes)
    write(evidence / 'SWIFTPROTOBUF_COMPILER_INPUTS.json', {'files': protobuf_inputs})
    commands.require('generated_invocation_link', common + ['-disableAutomaticPackageResolution',
        '-resultBundlePath', str(evidence / 'ImportABIProbe.xcresult'), 'build'], project.parent, 3600)
    product = work / 'DerivedData/Build/Products/Debug-iphonesimulator/ImportABIProbe.app/ImportABIProbe'
    require(product.is_file(), 'Actual generated Invocation consumer not linked')
    commands.require('linked-libraries', ['xcrun', 'otool', '-L', str(product)], root, 60)
    require(git(heart, 'write-tree') == native_tree and not git(heart, 'diff', '--name-only')
            and original.source_inventory(heart, ['deps/libs']) == link_inputs, 'Original ABI source/link inputs changed')
    write(evidence / 'MOBILE_SOURCE_STABILITY.json', mobile.recheck(compiler_inputs, row))
    require(original.source_inventory(root, swift_scopes) == swift_inputs
            and original.source_inventory(protobuf, protobuf_scopes) == protobuf_inputs
            and git(protobuf, 'rev-parse', 'HEAD') == expected['state']['revision']
            and not git(protobuf, 'status', '--porcelain', '--untracked-files=no')
            and sha(resolved) == sha(evidence / 'ACTUAL_PACKAGE_RESOLVED.json')
            and mobile.admit_mobile_module(module, env['GOMODCACHE'], row) == mobile_module,
            'Original Swift, Protobuf, dependency lock or gomobile compiler inputs changed')
    for tool in observed_tools:
        require(row(Path(tool['file']), tool['identity']['path']) == tool['identity'], 'ABI compiler executable changed')
    for sdk in sdk_context.values():
        item = sdk['sdk_settings']
        require(row(Path(item['path']), item['path']) == item, 'Actual SDK settings changed')
    require(current_identity() == identity and not git(root, 'diff', '--name-only', 'HEAD')
            and sha(proof_index) == args.proof_index_sha256, 'Local ABI source or qualification inputs changed')
    installer.verify_committed_generated(root, generated)
    lib_files = [reference(p, root) for p in sorted((root / LIB).rglob('*')) if p.is_file()]
    # Individual measured command receipts are kept even when one observed binary
    # supplies both architectures; these aliases index the exact actual command.
    selected_commands = {name: reference(evidence / (name + '.command.json'), evidence)
                         for name in ('gomobile_bind', 'generated_invocation_link')}
    selected_commands.update({item['platform'] + '_' + item['architecture'] + '_exports': item['command']
                              for item in exports})
    admission = {'schema': ('otzaria.original-import-local-sdk-input/3' if fresh_swift
                            else 'otzaria.original-import-local-sdk-input/2'), 'status': 'PASS',
        'producer_kind': 'local-mac', 'sdk_source_sha': identity['source_sha'],
        'local_execution_sha256': identity['local_execution_sha256'],
        'generated_files_verified': 733, 'generated_files_written': 0, 'generators_replayed': 0,
        'full_sdk_accepted': False, 'editor_ui_accepted': False, 'native_qualification': native,
        'qualification_receipts': {name: reference(evidence / (name + '.json'), evidence) for name in proofs},
        'historical_receipts': historical_receipts,
        **({'fresh_changed_swift': fresh_receipt} if fresh_swift else {}),
        'pinned_wrapper': reference(Path(pinned_row['path']), evidence),
        'commands': selected_commands,
        'defined_exports': sorted(EXPORTS), 'verified_architectures': {'ios': ['arm64'], 'ios-simulator': ['arm64', 'x86_64']},
        'source_unchanged_after_bind': True, 'owned_command_groups_drained': commands.owned_groups_drained,
        'lib_files': lib_files}
    write(evidence / 'ABI_INPUT.json', admission)
    from import_abi_input import verify
    checked = verify(root, evidence / 'ABI_INPUT.json', sha(evidence / 'ABI_INPUT.json'),
                     {'head_sha': identity['source_sha'], 'execution_identity': identity})
    result.update(status='PASS', phase='COMPLETE', input_receipt=str(evidence / 'ABI_INPUT.json'),
                  input_receipt_sha256=sha(evidence / 'ABI_INPUT.json'), qualification=checked,
                  actual_mobile_targets=len(compiler_inputs['groups']), source_inputs_stable=True,
                  full_editor_built=False, editor_ui_tests=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('root', 'native-heart', 'work', 'evidence', 'proof-index', 'proof-index-sha256',
                 'go-root', 'go-mod-cache', 'go-build-cache'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--timeout', type=int, default=10800)
    args = parser.parse_args()
    result = {'schema': 'otzaria.local-original-import-abi-build/1', 'status': 'FAIL', 'phase': 'INPUT_ADMISSION',
              'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        def stop(signum, _frame):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            raise KeyboardInterrupt('Owned ABI execution interrupted: ' + str(signum))
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        execute(args, result)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
    finally:
        result['finished_at'] = datetime.now(timezone.utc).isoformat()
        if result.pop('_owned_evidence', False):
            write(Path(args.evidence) / 'RESULT.json', result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
