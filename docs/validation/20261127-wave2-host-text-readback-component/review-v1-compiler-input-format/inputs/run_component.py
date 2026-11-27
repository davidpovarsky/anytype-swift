#!/usr/bin/env python3
"""One reviewed Host readback component, two XCTest methods and four HTTP flows.

Preparation is inert by default. This does not grant the coordinated runtime slot.
Every product/test source file is complete; this is not a full App/package build.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import traceback

sys.dont_write_bytecode = True
import owned_process

ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-host-text-readback-20261127')
INPUTS = ROOT / 'inputs'
COMPONENT = ROOT / 'component'
EVIDENCE = ROOT / 'attempt1'
SWIFT = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')
PRODUCT_COMMIT = 'cde0b83a3f04f36232eed93e6ab2cb7be0e692a5'
CLEANUP_SHA = '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924'
PROVENANCE_SHA = '4c2f95a4129fdb89125458c4a3a5874c97dbbf0ed9aaa3d1b15d638ccef734b1'
CRYPTO_SHA = '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'
SOURCE_CLOSURE_SHA = 'a70cf73dcb1ddda0767b36fa1046b2921ab7201aea154239d7e871b67e1ef6ad'
SOURCE_PINS = {'Package.swift': 'fdfcac028c96b46646bbafd01933fa58eb48f89753d1a42111f142b0c9c7564e', 'Sources/PinkhaAnyEngine/AnyGuardedTorahClaimsRepository.swift': 'cc9ee5e3eb159ef5ea68e7a87928fd94f047a8668c2f2483890faffdac8d73a1', 'Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift': '048ebd2d82e3a22265c3fea4ead6ba406b4f8d7d8f00367ec0c7779fac1b0d8f', 'Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift': '7205b72e687975bfda695bcccbcdbdd486af45c13ef7f0ddd20fcf58c9d5a312', 'Sources/PinkhaAnyEngine/AnyHTTPClient.swift': '8fce86456dfdfd7237a999fb56b6dcdf6d0917c068a797ed5d9a88c5e33d5182', 'Sources/PinkhaAnyEngine/AnyJSON.swift': 'fb8937994d7db5728a7872386670eaeb2e74dcb84abba92814316bb3d458008d', 'Sources/PinkhaAnyEngine/AnyLiveQuery.swift': '445930138f7aefe46f6d41995059acafad9363178da4bc17574d2a0e399c8cf4', 'Sources/PinkhaAnyEngine/AnyObjectCreationUncertain.swift': 'c4635b23304e60b1d27b546c53e8901a841160bd79bd43a066b50bc02b2b0704', 'Sources/PinkhaAnyEngine/AnySSEParser.swift': '1b5b55f99d357418d0df7ec43bc61e8bac1e1f246c613019f8c8b025c03cbdad', 'Sources/PinkhaAnyEngine/AnyTorahClaimsRepository.swift': 'cd11b4cc0e54b4593d5a9111ca37ef7556bf3bcaa71ddb1532e900dd94ac0145', 'Sources/PinkhaAnyEngine/AnyTorahLiveQuery.swift': 'd2cdada5bf2a639127e58dbbe7b422188df76cb145d32023d4b1011006fd69af', 'Sources/PinkhaAnyEngine/AnyTorahOperation.swift': 'c5cdbf04c36554a1c4a74dc164014a3cc9bd33b201479702d7c1224d3d661980', 'Sources/PinkhaAnyHost/AnyApplicationSession.swift': 'ff7480f71e2d0bdbd8de5825aca391fcbe237ca37a07dfe7e3d8f859af860acd', 'Sources/PinkhaAnyHost/AnyEditorDocumentStore.swift': '1ea82b556e9f16b7903de03bbe435a249c6c922ade9798a01d648c8394c2604d', 'Sources/PinkhaAnyHost/AnyEditorSnapshot.swift': 'd2956d5e698631a7ab90c039b2647ac518da2dea224f4e01c59dd4ca0cf9ea9f', 'Sources/PinkhaAnyHost/AnyHostCanonical.swift': 'd234b3d87ab9ec8317f159d413eb140eb94c1ae0aa0b1e20f30391b4e51c4840', 'Sources/PinkhaAnyIntegration/AnyNativeDocumentPolicy.swift': 'a4fa5fc4fc1185b1778ae960b60e39a03e3d4ce487c34bd4d69401946ff7e366', 'Sources/PinkhaAnyIntegration/AnyTorahWorkspace.swift': '7a51c02baafba146fac43ab0b5737ab3db6465ebdc142bce3d1a6ea33bf36c56', 'Sources/PinkhaKit/TorahAssociationModels.swift': '0007274a78d39fd4c8e0105eb50cec106c807cf53735caa0de1f4a85cd7fbde1', 'Sources/PinkhaKit/TorahAssociationRepository.swift': '63c789b1e14b85fb8032f2cf8fecb4fcb7e768453c03b9304e78ac77775fb66e', 'Sources/TorahInspectorCore/Models.swift': '59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0', 'Sources/TorahInspectorCore/ProviderProtocols.swift': '9f5f28f1d71a97831827dce5dfe2324a60460fc7760137b9527e4c3815d20273', 'Sources/TorahInspectorCore/TorahInspectorCoordinator.swift': 'fccfc25ee56e165c6559aba52a1ccec39d10db6fd6a94a91c867cd38dc693116', 'Sources/TorahInspectorCore/TorahInspectorRepository.swift': '519828f3d602811758d2698e00a06567b41d31d465b143175441f08873300040', 'Sources/TorahInspectorCore/TorahReaderScrollStateMachine.swift': '90173f3198133c6a746d00c9a6af9ad8cd854f5643f924d98e9095133da5bbdc', 'Sources/TorahInspectorCore/TorahRelatedDocumentsAccessError.swift': '0ff22bb5a56ddff0235e7b6c5188c737b110cb2848d7e17dcaefc3ca1d6df2e6', 'Sources/TorahInspectorCore/TorahSourceTransfer.swift': '994da5da2cb6b163083c7f3dea20cfe74c781211eea0f144b394a6d047affc97', 'Sources/TorahInspectorCore/TorahToolSelectorStateMachine.swift': '34dda44a571764ea98e43449422340ad7a00dbe4b0d43c0036d7d48ad8119729', 'Tests/Fixtures/editor_text_readback_server.py': 'd91554403d0fc9f84cd8792006ab150506923e0a003000fb4caff171a52800bd', 'Tests/PinkhaAnyHostTests/NativeHostTests.swift': '4cc5c251b525b36ab710d6fa05163ccb27a8e3c801c5e88eab44533253db13e5'}
METHODS = (
    'testCanonicalEquivalentTextReadbackCannotCertifyWriteOrMintUndo',
    'testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse',
)
SUITE = 'NativeTextEditReadbackHTTPTests'
ROOT_FLOOR = 2 * 1024**3
DEVELOPMENT_FLOOR = 512 * 1024**2
ALLOCATION_CAP = 256 * 1024**2
FINAL_EVIDENCE_RESERVE = 1024**2
ADMISSION_MARGIN = 32 * 1024**2
MEMORY_FLOOR = 512 * 1024**2
SECONDS = 300


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def pinned(path, expected, size=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.resolve(strict=True) == path, 'Physical path changed: ' + str(path)
    raw = path.read_bytes()
    assert sha(raw) == expected and (size is None or len(raw) == size), str(path)
    return raw


def source_inventory(folder):
    actual = {}
    for path in sorted(folder.rglob('*')):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            actual[path.relative_to(folder).as_posix()] = sha(path.read_bytes())
    assert actual == SOURCE_PINS, 'Complete source/Package inventory changed'
    return actual


def cleanup_custody():
    assert Path(owned_process.__file__).resolve(strict=True) == INPUTS / 'owned_process.py'
    pinned(INPUTS / 'owned_process.py', CLEANUP_SHA)
    value = json.loads(pinned(INPUTS / 'owned-process-provenance.json', PROVENANCE_SHA))
    assert value['originalRunnerSHA256'] == '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'
    assert value['outputSHA256'] == CLEANUP_SHA
    return value


def allocated_bytes():
    total = ROOT.stat().st_blocks * 512
    for base, directories, files in os.walk(ROOT, followlinks=False):
        for name in directories + files:
            p = Path(base) / name
            if p.is_symlink():
                # SwiftPM's debug/release convenience links stay inside this
                # owned scratch tree; walk never follows them or counts twice.
                assert p.is_relative_to(ROOT / 'build') and p.resolve().is_relative_to(ROOT / 'build'), str(p)
            total += p.lstat().st_blocks * 512
    return total


def resource_sample():
    memory = {line.split(':', 1)[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if line.startswith(('MemAvailable:', 'SwapFree:'))}
    return {'atUTC': owned_process.now(), 'rootFreeBytes': shutil.disk_usage('/').free,
            'developmentFreeBytes': shutil.disk_usage(ROOT).free,
            'ownedAllocatedBytes': allocated_bytes(), 'memAvailableBytes': memory['MemAvailable'],
            'swapFreeBytes': memory['SwapFree'], 'load': os.getloadavg()}


def require_budget(sample, admission=False):
    assert sample['rootFreeBytes'] >= ROOT_FLOOR + (ADMISSION_MARGIN if admission else 0), 'Root floor'
    assert sample['developmentFreeBytes'] >= DEVELOPMENT_FLOOR + (ALLOCATION_CAP + ADMISSION_MARGIN if admission else 0), 'Development floor'
    assert sample['ownedAllocatedBytes'] <= ALLOCATION_CAP - FINAL_EVIDENCE_RESERVE, 'Whole owned allocation cap with final-evidence reserve'
    assert sample['memAvailableBytes'] >= MEMORY_FLOOR, 'Memory floor'


def private_directory(path):
    path.mkdir(mode=0o700)
    path.chmod(0o700)  # Only this newly created owned directory; inherited setgid is removed.
    current = path.stat()
    assert stat.S_IMODE(current.st_mode) == 0o700 and current.st_uid == os.geteuid()


def copy_crypto():
    closure = json.loads(pinned(INPUTS / 'retained-crypto-closure.json', CRYPTO_SHA))
    assert len(closure['files']) == 102
    destinations = {'swift-import': 'retained-crypto-imports',
                    'c-header-or-module-map': 'retained-crypto-headers',
                    'aggregated-link-object': 'retained-crypto-objects'}
    for name in destinations.values():
        private_directory(ROOT / name)
    result = []
    for row in closure['files']:
        source = Path(row['freshCopySourcePath'])
        original = Path(row['originalManifestPath'])
        alias = Path(row['actualOriginalPackageLinkerPath'] if row['kind'] == 'aggregated-link-object'
                     else row['recordedHistoricalAliasPath'])
        assert alias.resolve(strict=True) == original.resolve(strict=True), 'Historical alias changed; stop before borrowing dependencies'
        raw = pinned(source, row['sha256'], row['bytes'])
        assert pinned(original, row['sha256'], row['bytes']) == raw
        relative = Path(row['relativePath'])
        assert not relative.is_absolute() and '..' not in relative.parts
        target = ROOT / destinations[row['kind']] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        target.chmod(0o600)
        assert pinned(target, row['sha256'], row['bytes']) == raw
        result.append({'kind': row['kind'], 'source': str(source), 'original': str(original),
                       'alias': str(alias), 'target': str(target), 'sha256': row['sha256'], 'bytes': row['bytes']})
    assert sum(x['bytes'] for x in result) == 19_775_715
    return result


def verify_crypto(copies):
    for item in copies:
        pinned(Path(item['source']), item['sha256'], item['bytes'])
        pinned(Path(item['original']), item['sha256'], item['bytes'])
        pinned(Path(item['target']), item['sha256'], item['bytes'])
        assert Path(item['alias']).resolve(strict=True) == Path(item['original']).resolve(strict=True)


def compiler_inputs(log):
    assert 'Swift version 6.4.3 (swift-6.4.3-RELEASE)' in log
    assert 'aarch64-unknown-linux-gnu' in log
    groups = {}
    for relative in SOURCE_PINS:
        parts = Path(relative).parts
        if len(parts) == 3 and parts[0] in ('Sources', 'Tests') and relative.endswith('.swift'):
            groups.setdefault(parts[1], set()).add(str(COMPONENT / relative))
    assert sum(len(x) for x in groups.values()) == 28
    proof = []
    for module, expected in sorted(groups.items()):
        candidates = list((ROOT / 'build').glob('**/' + module + '.build/sources'))
        assert len(candidates) == 1, 'Missing unique actual Swift source list: ' + module
        source_list = candidates[0]
        assert set(shlex.split(source_list.read_text())) == expected, module
        map_path = source_list.parent / 'output-file-map.json'
        output_map = json.loads(map_path.read_bytes())
        assert set(output_map) - {''} == expected, module
        witnesses = [line for line in log.splitlines()
                     if '/swiftc ' in line and '-module-name ' + module + ' ' in line
                     and ('@' + str(source_list) in line or all(p in line for p in expected))]
        assert witnesses, 'No actual swiftc witness for ' + module
        objects = []
        for source in sorted(expected):
            object_path = Path(output_map[source]['object'])
            assert object_path.is_relative_to(ROOT / 'build')
            assert object_path.is_file() and not object_path.is_symlink()
            raw = object_path.read_bytes()
            assert raw
            objects.append({'source': source, 'sourceSHA256': sha(Path(source).read_bytes()),
                            'object': str(object_path), 'objectSHA256': sha(raw), 'objectBytes': len(raw)})
        proof.append({'module': module, 'sourceList': str(source_list),
                      'sourceListSHA256': sha(source_list.read_bytes()), 'sourceListText': source_list.read_text(),
                      'outputFileMap': str(map_path), 'outputFileMapSHA256': sha(map_path.read_bytes()),
                      'actualCompilerLines': witnesses, 'objects': objects})
    return proof


def xctest_result(log):
    rows = re.findall(r"^Test Case '(?:[A-Za-z_][A-Za-z_0-9]*\.)*NativeTextEditReadbackHTTPTests\.([^']+)' (started|passed|failed|skipped)", log, re.M)
    started = [name for name, status in rows if status == 'started']
    passed = [name for name, status in rows if status == 'passed']
    assert sorted(started) == sorted(METHODS) and sorted(passed) == sorted(METHODS), 'Require exactly two actual selected XCTest methods'
    assert all(status in ('started', 'passed') for _, status in rows)
    all_started = re.findall(r"^Test Case '([^']+)' started", log, re.M)
    assert len(all_started) == 2 and all(SUITE + '.' in name for name in all_started), 'Unselected method ran'
    assert re.search(r'Executed 2 tests, with 0 failures(?: \(0 unexpected\))?', log)
    return {'actualXCTestMethods': list(METHODS), 'XCTestCases': 2, 'loopedHTTPFlows': 4,
            'oldMethodsExecuted': 0, 'SwiftTestingZeroTestFooterIsNotXCTestAuthority': True}


def fixture_directories():
    folder = ROOT / 'tmp'
    return sorted(folder.glob('pinkha-host-text-readback-*')) if folder.exists() else []


def retain_fixtures():
    rows = []
    for directory in fixture_directories():
        assert directory.is_dir() and not directory.is_symlink()
        assert directory.resolve(strict=True).parent == ROOT / 'tmp'
        item = {'directory': str(directory), 'files': []}
        for path in sorted(directory.iterdir()):
            assert path.is_file() and not path.is_symlink()
            raw = path.read_bytes()
            assert len(raw) <= 2 * 1024**2
            item['files'].append({'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)})
        rows.append(item)
    return rows


def qualify_fixtures(log):
    directories = fixture_directories()
    printed = re.findall(r'^Host text readback fixture evidence: (.+)$', log, re.M)
    assert len(directories) == len(printed) == 4 and set(printed) == {str(x) for x in directories}
    marker = 'pinkha-anchor://v1/c3BhY2U/b2JqZWN0/00000000-0000-0000-0000-000000000001'
    source = lambda text: '[Before ' + text + ' after](' + marker + ')'
    pairs = [(source('\u00e9'), source('e\u0301')), (source('\u05e9\u05b8\u05c1'), source('\u05e9\u05c1\u05b8'))]
    expected = {(a.encode(), b.encode(), reply.encode()) for a, b in pairs for reply in (a, b)}
    observed = set()
    proof = []
    for directory in directories:
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700 and directory.stat().st_uid == os.geteuid()
        read = lambda name: json.loads((directory / name).read_bytes())
        config, start, end = read('config.json'), read('fixture-start.json'), read('fixture-exit.json')
        assert set(config) == {'before', 'requested', 'reply'} and all(isinstance(x, str) for x in config.values())
        vector = tuple(config[x].encode() for x in ('before', 'requested', 'reply'))
        assert vector in expected and vector not in observed
        observed.add(vector)
        assert isinstance(start['pid'], int) and start['pid'] > 0 and end['pid'] == start['pid']
        assert start['scope'] == 'controlled-loopback-not-native' and end['stopReason'] == 'stdin-eof' and end['patches'] == 1
        port = read('port.json'); assert isinstance(port, int) and 1 <= port <= 65535
        requests = read('dispatch.json'); assert 0 < len(requests) <= 256
        patches = [row for row in requests if row['method'] == 'PATCH']; assert len(patches) == 1
        patch = patches[0]; body = patch['body']
        assert patch['path'] == '/v1/spaces/space/objects/object/editor/editor_blocks/blocks/block'
        assert set(body) == {'set', 'unset', 'ifVersion', 'ifStartedAt'} and set(body['set']) == {'text'}
        assert body['set']['text'].encode() == config['requested'].encode()
        assert patch['textUTF8'] == list(config['requested'].encode())
        assert body['unset'] == [] and body['ifVersion'] == 'editor-v1' and body['ifStartedAt'] == 'run1'
        markdown, query, acknowledgement = read('last-markdown-response.json'), read('last-query-response.json'), read('patch-acknowledgement.json')
        assert markdown['content'].encode() == config['reply'].encode() and markdown['version'] == 'editor-v2'
        assert query['total'] == 1 and query['hasNext'] is False and len(query['records']) == 1
        block = query['records'][0]
        assert block['id'] == 'block' and block['type'] == 'paragraph' and block['text'].encode() == config['reply'].encode()
        assert block['_ver']['text'] == 'editor-v2' and block['nav'] == {'parentId': '', 'pos': 'A'}
        assert acknowledgement == {'recordIds': ['block'], 'versionId': 'native-write-v2', 'engineStartedAt': 'run1', 'editorVersion': 'editor-v2'}
        assert (directory / 'stderr.log').read_bytes() == b'', 'Fixture emitted an unexpected server failure'
        proof.append({'directory': str(directory), 'pid': start['pid'], 'stopReason': end['stopReason'],
                      'beforeUTF8': list(vector[0]), 'requestedUTF8': list(vector[1]), 'replyUTF8': list(vector[2]),
                      'actualPatchCount': 1, 'nativeAcceptance': False,
                      'processExitAuthority': 'The two actual passed XCTest methods include the original Process.waitUntilExit/exit0 assertions; these raw EOF journals bind the same four PIDs. No historical PID probe.'})
    assert observed == expected
    return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-reviewed-candidate', action='store_true')
    args = parser.parse_args()
    if not args.execute_reviewed_candidate:
        print(json.dumps({'status': 'PREPARED_NOT_ADMITTED_OR_RUN', 'productCommit': PRODUCT_COMMIT,
                          'methods': list(METHODS), 'runtimeSlotGrantedByThisScript': False}))
        return
    assert ROOT.is_dir() and ROOT.resolve(strict=True) == ROOT
    assert ROOT.stat().st_uid == os.geteuid() and stat.S_IMODE(ROOT.stat().st_mode) == 0o700
    assert set(p.name for p in ROOT.iterdir()) == {'inputs'}, 'Never reuse an existing attempt or output'
    assert Path(__file__).resolve(strict=True) == INPUTS / 'run_component.py'
    custody = cleanup_custody()
    source_inventory(INPUTS / 'component')
    pinned(INPUTS / 'whole-source-closure.json', SOURCE_CLOSURE_SHA)
    pinned(INPUTS / 'retained-crypto-closure.json', CRYPTO_SHA)
    initial = resource_sample(); require_budget(initial, admission=True)
    private_directory(EVIDENCE)
    receipt = {'schema': 'pinkha-host-text-readback-component/v1', 'status': 'FAIL',
               'startedAtUTC': owned_process.now(), 'productCommit': PRODUCT_COMMIT,
               'controllerSHA256': sha(Path(__file__).read_bytes()), 'sourceBodiesModifiedForComponent': 0,
               'nativeCalls': 0, 'AppleCalls': 0, 'runtimeSlotGrantedByThisScript': False,
               'noGlobalRootWriteAuditClaim': True, 'declaredControlledOutputBytesOnRoot': 0,
               'budget': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEVELOPMENT_FLOOR,
                          'ownedAllocationCapBytes': ALLOCATION_CAP, 'admissionMarginBytes': ADMISSION_MARGIN,
                          'finalEvidenceReserveWithinCapBytes': FINAL_EVIDENCE_RESERVE,
                          'memoryFloorBytes': MEMORY_FLOOR, 'commandSeconds': SECONDS, 'jobs': 2},
               'safeToReleaseRuntimeSlot': False, 'errors': []}
    samples = [initial]; process = None; state = {}; copies = []; log = ''; first = None
    started = time.monotonic()
    try:
        copies = copy_crypto(); write(EVIDENCE / 'actual-dependency-copies.json', copies)
        shutil.copytree(INPUTS / 'component', COMPONENT)
        before = source_inventory(COMPONENT); write(EVIDENCE / 'source-inputs-before.json', before)
        for name in ('tmp', 'swift-cache', 'swift-config', 'swift-security', 'clang-module-cache', 'swift-module-cache', 'xdg-cache', 'xdg-config'):
            private_directory(ROOT / name)
        env = dict(os.environ)
        env.update(TMPDIR=str(ROOT / 'tmp'), CLANG_MODULE_CACHE_PATH=str(ROOT / 'clang-module-cache'),
                   SWIFTPM_MODULECACHE_OVERRIDE=str(ROOT / 'swift-module-cache'),
                   XDG_CACHE_HOME=str(ROOT / 'xdg-cache'), XDG_CONFIG_HOME=str(ROOT / 'xdg-config'),
                   PYTHONDONTWRITEBYTECODE='1', GIT_TERMINAL_PROMPT='0',
                   PATH=str(SWIFT.parent) + ':/usr/bin:/bin')
        # Keep all explicit source, module, object, cache, configuration, temporary and log paths on Development.
        argv = [str(SWIFT), 'test', '--package-path', str(COMPONENT), '--scratch-path', str(ROOT / 'build'),
                '--cache-path', str(ROOT / 'swift-cache'), '--config-path', str(ROOT / 'swift-config'),
                '--security-path', str(ROOT / 'swift-security'), '--disable-automatic-resolution',
                '--jobs', '2', '--no-parallel', '-v', '--filter', SUITE]
        receipt['command'] = {'argv': argv, 'cwd': str(COMPONENT), 'environmentOverrides': {k: env[k] for k in
            ('TMPDIR', 'CLANG_MODULE_CACHE_PATH', 'SWIFTPM_MODULECACHE_OVERRIDE', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'PYTHONDONTWRITEBYTECODE', 'GIT_TERMINAL_PROMPT', 'PATH')}}
        tool_binary = SWIFT.resolve(strict=True)
        receipt['actualToolchainExecutable'] = {'requestedPath': str(SWIFT), 'physicalPath': str(tool_binary),
                                               'bytes': tool_binary.stat().st_size, 'sha256': sha(tool_binary.read_bytes()),
                                               'versionAndTargetAuthority': 'Actual verbose compiler output is qualified after execution.'}
        write(EVIDENCE / 'command.json', receipt['command'])
        sample = resource_sample(); samples.append(sample); require_budget(sample)
        with (EVIDENCE / 'stdout.original.log').open('wb') as out, (EVIDENCE / 'stderr.original.log').open('wb') as err:
            process = subprocess.Popen(argv, cwd=COMPONENT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            write(EVIDENCE / 'process.json', {'pid': process.pid, 'processGroup': process.pid, 'startedAtUTC': owned_process.now()})
            deadline = time.monotonic() + SECONDS
            while process.poll() is None:
                sample = resource_sample(); samples.append(sample); require_budget(sample)
                if time.monotonic() >= deadline:
                    raise TimeoutError('Owned Host command exceeded300 seconds')
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
        receipt['processExit'] = process.returncode
        receipt['outerGroupAtExit'] = owned_process.observe_owned_group(process, state)
        assert receipt['outerGroupAtExit']['status'] == 'ABSENT_ESRCH'
        after = source_inventory(COMPONENT)
        assert after == before == source_inventory(INPUTS / 'component')
        assert cleanup_custody() == custody
        verify_crypto(copies)
        write(EVIDENCE / 'source-inputs-after.json', after)
        log = (EVIDENCE / 'stdout.original.log').read_text(errors='replace') + '\n' + (EVIDENCE / 'stderr.original.log').read_text(errors='replace')
        assert process.returncode == 0, 'Actual Swift compiler/test command failed'
        receipt['testResult'] = xctest_result(log)
        receipt['compilerInputs'] = compiler_inputs(log)
        receipt['fourControlledHTTPFlows'] = qualify_fixtures(log)
        receipt['status'] = 'PASS_TWO_XCTEST_METHODS_FOUR_HTTP_FLOWS_HOST_COMPONENT_ONLY'
    except BaseException as error:
        first = error
        receipt['errors'].append({'phase': 'actual-component', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
    finally:
        if process is not None:
            try:
                owned_process.finish_owned_process(process, state, receipt)
            except BaseException as error:
                if first is None:
                    first = error
                receipt['status'] = 'FAIL'
                receipt['errors'].append({'phase': 'original-owned-cleanup', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
        try:
            # A crashed Swift process still closes the fixture's sole stdin writer.
            # Wait only for this attempt's bounded raw end records; never probe/reuse recorded PIDs.
            end = time.monotonic() + 49
            while any((p / 'fixture-start.json').exists() and not (p / 'fixture-exit.json').exists() for p in fixture_directories()) and time.monotonic() < end:
                time.sleep(0.25)
            receipt['retainedFixtureFiles'] = retain_fixtures()
            write(EVIDENCE / 'fixture-artifacts.json', receipt['retainedFixtureFiles'])
            write(EVIDENCE / 'source-inputs-final.json', {'inputs': source_inventory(INPUTS / 'component'),
                  'compiledCopy': source_inventory(COMPONENT) if COMPONENT.exists() else None})
            sample = resource_sample(); samples.append(sample); require_budget(sample)
            write(EVIDENCE / 'resource-samples.json', samples)
            if copies:
                verify_crypto(copies)
            receipt['safeToReleaseRuntimeSlot'] = (
                (process is None or receipt.get('ownedCleanup', {}).get('status') == 'PASS_OWNED_GROUP_ABSENT')
                and (not fixture_directories() or (receipt['status'].startswith('PASS_') and len(receipt.get('fourControlledHTTPFlows', [])) == 4)))
        except BaseException as error:
            if first is None:
                first = error
            receipt['status'] = 'FAIL'
            receipt['errors'].append({'phase': 'retention-and-final-budget', 'type': type(error).__name__, 'traceback': traceback.format_exc()})
        receipt['finishedAtUTC'] = owned_process.now()
        receipt['seconds'] = round(time.monotonic() - started, 3)
        receipt['maximumOwnedAllocatedBytes'] = max(x['ownedAllocatedBytes'] for x in samples)
        receipt['minimumRootFreeBytes'] = min(x['rootFreeBytes'] for x in samples)
        receipt['minimumDevelopmentFreeBytes'] = min(x['developmentFreeBytes'] for x in samples)
        try:
            write(EVIDENCE / 'receipt.json', receipt)
        except BaseException as error:
            if first is not None:
                first.add_note('Final receipt save also failed: ' + repr(error))
                raise first from error
            raise
        print(json.dumps({'status': receipt['status'], 'receipt': str(EVIDENCE / 'receipt.json'),
                          'receiptSHA256': sha((EVIDENCE / 'receipt.json').read_bytes()),
                          'safeToReleaseRuntimeSlot': receipt['safeToReleaseRuntimeSlot'],
                          'firstFailure': repr(first) if first else None}), flush=True)
    raise SystemExit(0 if receipt['status'].startswith('PASS_') else 1)


if __name__ == '__main__':
    main()
