#!/usr/bin/env python3
"""Isolated real-source qualification of 31 new Bookmark and recovery component methods.

SOURCE-ONLY until this controller actually completes. It opens no native
account, compiles no dependency, and does not replay any FilesV2 or migration
proof. The two reused Crypto modules are admitted from the exact retained
producer; every product module under test is compiled from its full sources.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import time


MIB = 1024 * 1024
GIB = 1024 * MIB
PARENT = Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127')
PREPARED = PARENT/'prepared1'
RETAINED_UPLOAD_PREPARED = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/prepared3')
CONTROL = Path(__file__).parent
MANIFEST = CONTROL/'bookmark-component-inputs.json'
MANIFEST_SHA = 'eb2b91a339f9f2f9ccaf30220fc1fc52781d960e3efdc5d68a8ae270dcb9ef83'
CRYPTO_HELPER = CONTROL/'qualify_bookmark_crypto_c3.py'
CRYPTO_HELPER_SHA = 'faf63670a56f28a2c0ce4aa61d89957c7987074cd7ade6d483acb4a07d2ba1f4'
SHARED_CRYPTO_HELPER = CONTROL/'qualify_current_c3_crypto.py'
SHARED_CRYPTO_HELPER_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
OWNED_HELPER = CONTROL/'owned_swift_commands.py'
OWNED_HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HEADER_MANIFEST = CONTROL/'crypto-header-source-manifest.json'
HEADER_MANIFEST_SHA = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
LIFECYCLE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_RECEIPT_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
DRIVER_ALIASES = {
    TOOLCHAIN/'swift': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'swiftc': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'clang': TOOLCHAIN/'clang-21',
    TOOLCHAIN/'clang++': TOOLCHAIN/'clang-21',
}
ROOT_FLOOR = 2 * GIB
ROOT_ADMISSION = ROOT_FLOOR + 32 * MIB
DEVELOPMENT_FLOOR = 512 * MIB
OWNED_ALLOCATION_CAP = 256 * MIB
DEVELOPMENT_ADMISSION = DEVELOPMENT_FLOOR + OWNED_ALLOCATION_CAP + 32 * MIB
LOG_CAP = 16 * MIB
FIXTURE_CAP = 16 * MIB
RECEIPT_CAP = 4 * MIB
TOTAL_SECONDS = 900
SWIFT_SECONDS = 600
CHUNK = MIB
_save_serial = 0


class Inputs:
    """Exact regular-file reads; no generic symlink admission or whole-file hash."""
    def __init__(self):
        self.alias_admitted = False

    def admit_retained_crypto_alias(self, original, physical, receipt_sha):
        assert original == CACHE and physical == PHYSICAL_CACHE
        assert receipt_sha == 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
        assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
        assert CACHE.resolve() == PHYSICAL_CACHE and PHYSICAL_CACHE.resolve() == PHYSICAL_CACHE
        self.alias_admitted = True

    def physical(self, value):
        path = Path(value)
        assert path.is_absolute()
        if path in DRIVER_ALIASES:
            target = DRIVER_ALIASES[path]
            assert path.resolve() == target and target.resolve() == target
            if path.name == 'swift' or path.name == 'swiftc':
                assert os.readlink(path) == 'swift-driver'
            elif path.name == 'clang':
                assert os.readlink(path) == 'clang-21'
            else:
                assert os.readlink(path) == 'clang' and os.readlink(TOOLCHAIN/'clang') == 'clang-21'
            return target
        if path.is_relative_to(CACHE):
            assert self.alias_admitted, 'retained cache custody not yet admitted'
            assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
            target = PHYSICAL_CACHE/path.relative_to(CACHE)
            assert path.resolve() == target and target.resolve() == target
            return target
        assert path.resolve() == path and not path.is_symlink(), 'unqualified input alias'
        return path

    @staticmethod
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def consume(self, value, maximum, retain=False, destination=None):
        path = self.physical(value)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum
        assert self.identity(path.lstat()) == self.identity(before)
        digest = hashlib.sha256()
        collected = bytearray() if retain else None
        copied = 0
        try:
            while True:
                part = os.read(fd, CHUNK)
                if not part:
                    break
                copied += len(part)
                assert copied <= maximum and copied <= before.st_size
                digest.update(part)
                if retain:
                    collected.extend(part)
                if destination is not None:
                    view = memoryview(part)
                    while view:
                        written = os.write(destination, view)
                        assert written > 0
                        view = view[written:]
            assert copied == before.st_size
            assert self.identity(os.fstat(fd)) == self.identity(before)
            assert self.identity(path.lstat()) == self.identity(before)
        finally:
            os.close(fd)
        result = {'bytes': copied, 'sha256': digest.hexdigest()}
        return (result, bytes(collected)) if retain else result

    def row(self, path):
        return self.consume(path, maximum=512*MIB)

    def sha(self, path):
        return self.row(path)['sha256']

    def read(self, path, maximum):
        return self.consume(path, maximum=maximum, retain=True)[1]

    def pinned(self, path, expected):
        assert re.fullmatch(r'[0-9a-f]{64}', expected)
        assert self.sha(path) == expected, str(path)+' changed'

    def copy_exact(self, original, destination, expected):
        destination = Path(destination)
        assert destination.parent.resolve() == destination.parent
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            copied = self.consume(original, maximum=8*MIB, destination=descriptor)
            assert copied == expected
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        assert self.row(destination) == expected

    def save(self, path, value):
        save(path, value)


def save(path, value):
    global _save_serial
    path = Path(path)
    assert path.parent.resolve() == path.parent
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    assert len(data) <= RECEIPT_CAP
    _save_serial += 1
    # Retain an interrupted staging file; finalization always gets a fresh name.
    temporary = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(_save_serial))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            assert count > 0
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_module(path, name, expected, base):
    base.pinned(path, expected)
    ast.parse(base.read(path, maximum=256*1024))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base.pinned(path, expected)
    return module


def allocation(root):
    total = 0
    count = 0
    seen = set()
    began = time.monotonic()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for filename in [None]+dirs+files:
            path = Path(directory) if filename is None else Path(directory)/filename
            try:
                row = path.lstat()
            except FileNotFoundError:
                continue  # A compiler may retire its own temporary member.
            count += 1
            assert count <= 200000 and time.monotonic()-began <= 5
            key = (row.st_dev, row.st_ino)
            if key not in seen:
                seen.add(key)
                total += row.st_blocks * 512
    return total


def retained_products(build, base, guard):
    """Pin the complete physical Products tree, including Linux test launchers.

    A suffix list omits the executable *-test-runner which --skip-build uses.
    Keep every regular product file and every executable mode, and refuse any
    alias/special file. The independent source manifest is a separate input.
    """
    root = build/'out/Products'
    assert root.is_dir() and root.resolve() == root and not root.is_symlink()
    files, modes, directories, executables = {}, {}, {}, {}
    for path in [root]+sorted(root.rglob('*')):
        guard()
        before = path.lstat()
        assert path.resolve() == path and not path.is_symlink(), 'physical compiled product required'
        key = str(path)
        mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            directories[key] = mode
        else:
            assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'regular private compiled product required'
            assert before.st_size <= 128*1024**2, 'bounded compiled product file'
            files[key] = base.row(path)
            modes[key] = mode
            if mode & 0o111:
                executables[key] = dict(files[key], mode=mode)
        after = path.lstat()
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_nlink,
                                row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        assert identity(before) == identity(after), 'compiled product changed during census'
        assert len(files)+len(directories) <= 4096, 'bounded compiled product tree'
    assert 1 <= len(files) <= 2048
    runners = [name for name in files if Path(name).name == 'BookmarkCreationTests-test-runner']
    assert len(runners) == 1 and runners[0] in executables, 'one actual executable Linux XCTest runner'
    libraries = [name for name in files if Path(name).name == 'BookmarkCreationTests.so']
    assert len(libraries) == 1, 'one actual test shared library'
    assert any('PinkhaAnyEngine' in name and '.swiftmodule' in name for name in files)
    assert any('PinkhaAnyHost' in name and '.swiftmodule' in name for name in files)
    return {'root':str(root), 'files':files, 'modes':modes, 'directories':directories,
            'executables':executables, 'testRunner':dict(path=runners[0], **executables[runners[0]])}


def package_text(flags, links):
    swift = lambda value: json.dumps(value, ensure_ascii=False)
    compile_flags = '['+', '.join(map(swift, flags))+']'
    link_flags = '['+', '.join(map(swift, links+['-lstdc++']))+']'
    targets = [
        ('TorahInspectorCore', []),
        ('PinkhaKit', ['TorahInspectorCore']),
        ('PinkhaAnyEngine', []),
        ('PinkhaAnyIntegration', ['PinkhaKit', 'PinkhaAnyEngine']),
        ('PinkhaAnyHost', ['PinkhaAnyEngine', 'PinkhaAnyIntegration']),
    ]
    rows = []
    for name, dependencies in targets:
        deps = '['+', '.join(map(swift, dependencies))+']'
        rows.append('        .target(name: '+swift(name)+', dependencies: '+deps+', swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')])')
    rows.append('        .testTarget(name: "BookmarkCreationTests", dependencies: ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost"], swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')], linkerSettings: [.unsafeFlags('+link_flags+')])')
    return '// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: "BookmarkCreationProof", targets: [\n'+',\n'.join(rows)+'\n])\n'


def fixture_audit(root, owner_record, owner, base, manifest):
    """Verify retained EOF and request evidence inside the original owned group."""
    assert root.resolve() == root and stat.S_IMODE(root.stat().st_mode) == 0o700
    directories = sorted(root.iterdir())
    assert len(directories) == 17, 'exact 17 actual Bookmark HTTP fixture instances required'
    owner_sha = base.sha(owner_record)
    identities, rows, all_requests, modes = set(), [], [], []
    mandatory = {'config.json', 'server.py', 'account.txt', 'port.json',
                 'start.json', 'exit.json', 'parent-stop.json', 'stderr.log'}
    optional = {'requests.json', 'owner-retired.json'}
    for directory in directories:
        assert re.fullmatch(r'case-[0-9A-Fa-f-]{36}', directory.name)
        assert directory.resolve() == directory and directory.is_dir()
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        paths = {path.name: path for path in directory.iterdir()}
        assert mandatory <= set(paths) <= mandatory | optional, 'closed fixture artifact set'
        artifacts, values = {}, {}
        for name, path in paths.items():
            info = path.lstat()
            assert path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            assert info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
            raw = base.read(path, maximum=MIB)
            artifacts[name] = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
            if name.endswith('.json'):
                values[name] = json.loads(raw)
        assert artifacts['server.py'] == manifest['fixtureScript'], 'exact embedded fixture bytes'
        config = values['config.json']
        assert set(config) == {'body','capabilities','mode','controlToken'}
        assert config['controlToken'] == 'a'*64
        assert config['mode'] in ('normal','foreign-scope','switch-after-post','oversize','retire-on-final-auth')
        modes.append(config['mode'])
        assert type(values['port.json']) is int and 1 <= values['port.json'] <= 65535
        started, ended, stopped = (values[name] for name in ('start.json','exit.json','parent-stop.json'))
        assert started['controllerOwnedGroup'] is True
        assert started['ownerRecord'] == str(owner_record) and started['ownerRecordSHA256'] == owner_sha
        assert started['ownerPID'] == owner['pid'] == started['pgid'] == started['sessionID']
        identity = (started['pid'], started['startTimeTicks'])
        assert started['pid'] > 1 and identity not in identities
        identities.add(identity)
        assert started['startTimeTicks'] > 0 and re.fullmatch(r'[0-9a-f-]{36}', started['bootID'])
        assert 1 <= len(started['ownerAncestors']) <= 64
        assert started['ownerAncestors'][0]['pid'] == started['parentPID']
        assert started['ownerAncestors'][-1]['pid'] == owner['pid']
        assert all(row['startTimeTicks'] > 0 for row in started['ownerAncestors'])
        assert set(ended) == set(started) | {'reason','requestCount'}
        assert {key:ended[key] for key in started} == started and ended['reason'] == 'stdin-eof'
        assert set(stopped) == {'started','pid','leaderObservedExited','exitCode','ownership','errors'}
        assert stopped['started'] is True and stopped['pid'] == started['pid']
        assert stopped['leaderObservedExited'] is True and stopped['exitCode'] == 0
        assert stopped['ownership'] == started and stopped['errors'] == []
        assert artifacts['stderr.log']['bytes'] == 0, 'retained fixture error output fails qualification'
        requests = values.get('requests.json', [])
        assert type(requests) is list and len(requests) <= 64 and ended['requestCount'] == len(requests)
        for request in requests:
            assert set(request) == {'method','path','body'}
            if request['method'] == 'GET':
                assert request['path'] in ('/v1/auth','/v1/pinkha/capabilities') and request['body'] is None
            else:
                assert request['method'] == 'POST'
                assert request['path'] == '/v1/spaces/space/pinkha/bookmark-create-frame'
                body = request['body']
                assert type(body) is dict and set(body) == {'typeId','collections'}
                assert body['typeId'] == 'bookmark-type' and type(body['collections']) is list
                assert body['collections'] in ([], ['z','z']), 'exact original read request preserved'
        posts = [request for request in requests if request['method'] == 'POST']
        assert len(posts) <= 1, 'no read-only frame retry or object creation dispatch'
        if config['mode'] == 'retire-on-final-auth':
            assert values.get('owner-retired.json') is True
        else:
            assert 'owner-retired.json' not in values
        all_requests.extend(requests)
        rows.append({'directory':str(directory),'fixturePID':started['pid'],'ownedGroup':started['pgid'],
                     'stdinEOFExit':True,'requestCount':len(requests),'framePOSTCount':len(posts),'artifacts':artifacts})
    assert {mode:modes.count(mode) for mode in set(modes)} == {
        'normal':13,'foreign-scope':1,'switch-after-post':1,'oversize':1,'retire-on-final-auth':1}
    assert len(all_requests) == 76
    assert sum(row['method'] == 'GET' for row in all_requests) == 66
    assert sum(row['method'] == 'POST' for row in all_requests) == 10
    requests_with_body = [row['body'] for row in all_requests if row['method'] == 'POST']
    assert requests_with_body.count({'typeId':'bookmark-type','collections':[]}) == 9
    assert requests_with_body.count({'typeId':'bookmark-type','collections':['z','z']}) == 1
    # The unreaped-leader helper latched the entire original group's absence.
    # Never query or signal any historical numeric fixture or owner PID here.
    assert owner['processGroupAbsent'] and owner['exitCode'] == 0 and not owner['forcedCleanup']
    return {'instances':17,'requestCount':76,'GETCount':66,'readOnlyFramePOSTCount':10,
            'objectCreatePOSTCount':0,'allOwnedOriginalGroup':True,'allCleanEOF':True,
            'groupAbsenceSource':'qualified unreaped owner closure; no post-reap PID probing','fixtureRows':rows}

def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification requires Python assertions enabled')
    sys.dont_write_bytecode = True
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controller-sha', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{64}', args.controller_sha)
    assert CONTROL.resolve() == CONTROL and CONTROL.is_relative_to(PREPARED)
    assert PREPARED.resolve() == PREPARED and PARENT.resolve() == PARENT
    output = args.output
    assert output.parent == PARENT and re.fullmatch(r'components-attempt[1-9][0-9]*', output.name)
    assert not output.exists() and not output.is_symlink()
    base = Inputs()
    controls = {Path(__file__):args.controller_sha, MANIFEST:MANIFEST_SHA,
                CRYPTO_HELPER:CRYPTO_HELPER_SHA, SHARED_CRYPTO_HELPER:SHARED_CRYPTO_HELPER_SHA,
                OWNED_HELPER:OWNED_HELPER_SHA,
                HEADER_MANIFEST:HEADER_MANIFEST_SHA, LIFECYCLE_RECEIPT:LIFECYCLE_RECEIPT_SHA}
    for path, expected in controls.items():
        base.pinned(path, expected)
    lifecycle = json.loads(base.read(LIFECYCLE_RECEIPT, maximum=MIB))
    assert lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
    assert lifecycle['helperSHA256'] == OWNED_HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'] is True
    assert len(lifecycle['methods']) == len(lifecycle['commands']) == 5
    assert {row['name'] for row in lifecycle['methods']} == {'normal','started-journal-failure','leader-exits-with-descendant','controller-SIGTERM','controller-SIGINT'}
    assert all(row['status'] == 'PASS' and row['groupPositivelyAbsent'] for row in lifecycle['methods'])
    assert all(row['processGroupAbsent'] for row in lifecycle['commands'])
    assert lifecycle['compilerInvocations'] == lifecycle['nativeInvocations'] == 0
    owned = load_module(OWNED_HELPER, 'ordinary_upload_owned_commands', OWNED_HELPER_SHA, base)
    owned.install_interrupt_handlers()
    output.mkdir(mode=0o700)
    started_at = time.monotonic()
    result = {'status':'RUNNING', 'scope':'27 new Bookmark plus4 new post-close recovery component methods only',
              'nativeAccountsOpened':False, 'nativeStorageQualified':False, 'cloudDurabilityQualified':False,
              'separateNativeTestRequested':False, 'separateNativeTestStatus':'NOT_DISPATCHED',
              'priorMigrationOrFilesV2MethodsReplayed':0, 'priorUpload35MethodsReplayed':0, 'errors':[], 'commands':[], 'sourceUnchanged':False,
              'controllerSHA256':args.controller_sha, 'inputManifestSHA256':MANIFEST_SHA,
              'unchangedOwnedHelperFiveControlsReused':{'path':str(LIFECYCLE_RECEIPT),'sha256':LIFECYCLE_RECEIPT_SHA,'newlyExecutedControls':0},
              'budget':{'rootRuntimeFloorBytes':ROOT_FLOOR, 'rootAdmissionBytes':ROOT_ADMISSION,
                        'developmentRuntimeFloorBytes':DEVELOPMENT_FLOOR, 'developmentAdmissionBytes':DEVELOPMENT_ADMISSION,
                        'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP, 'declaredControlledOutputBytesOnRoot':0,
                        'finalVerificationSeconds':120, 'unchangedTotalControllerSeconds':TOTAL_SECONDS,
                        'allExplicitBuildIndexCacheTemporaryAndEvidencePathsOnDevelopment':True,
                        'noGlobalRootWriteAuditClaim':True},
              'minimumRootFreeBytes':shutil.disk_usage('/').free,
              'minimumDevelopmentFreeBytes':shutil.disk_usage(PARENT).free}
    immutable = {}
    copies = {}
    reused = None
    manifest = None
    helper = None
    env = None
    last_allocation = 0.0
    source_admission_complete = False
    final_deadline = None

    def observe():
        nonlocal last_allocation
        try:
            root_free = shutil.disk_usage('/').free
            development_free = shutil.disk_usage(PARENT).free
            result['minimumRootFreeBytes'] = min(result['minimumRootFreeBytes'], root_free)
            result['minimumDevelopmentFreeBytes'] = min(result['minimumDevelopmentFreeBytes'], development_free)
            if root_free < ROOT_FLOOR:
                return 'root 2 GiB runtime emergency floor'
            if development_free < DEVELOPMENT_FLOOR:
                return 'development 512 MiB runtime emergency floor'
            if time.monotonic()-started_at > TOTAL_SECONDS:
                return 'bounded component controller deadline'
            if final_deadline is not None and time.monotonic() >= final_deadline:
                return 'bounded component final verification deadline'
            if (output/'abort').exists():
                return 'owned component abort requested'
            for path in output.glob('commands/*/original.log'):
                if path.stat().st_size > LOG_CAP:
                    return 'bounded command log limit'
            if time.monotonic()-last_allocation >= 1:
                last_allocation = time.monotonic()
                used = allocation(output)
                result['maximumOwnedAllocatedBytes'] = max(result.get('maximumOwnedAllocatedBytes',0), used)
                if used > OWNED_ALLOCATION_CAP:
                    return 'bounded entire component allocation limit'
                fixtures = output/'http-fixtures'
                if fixtures.exists() and allocation(fixtures) > FIXTURE_CAP:
                    return 'bounded loopback fixture allocation limit'
        except BaseException as error:
            return 'resource observation failed: '+type(error).__name__
        return None

    def guard():
        reason = observe()
        if reason is not None:
            raise RuntimeError(reason)

    def remember_input(path, expected):
        guard()
        actual = base.row(path)
        assert actual == {'bytes':expected['bytes'], 'sha256':expected['sha256']}, str(path)+' source changed'
        immutable[str(path)] = actual

    def command(name, argv, cwd, command_env, timeout):
        log, row = owned.run(output/'commands'/name, argv, cwd, command_env, timeout,
                             observe, save, base.sha, result['commands'])
        return base.read(log, maximum=LOG_CAP), row

    def dependency_status(phase, manifest):
        for name, revision in manifest['dependencySourcePins'].items():
            directory = PHYSICAL_CACHE/'checkouts'/name
            assert directory.resolve() == directory
            raw, _ = command(phase+'-'+name, ['git','-c','safe.directory='+str(directory),'-C',str(directory),
                'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
            rows = raw.decode().splitlines()
            assert '# branch.oid '+revision in rows and all(row.startswith('# ') for row in rows), name+' source checkout changed'
        directory = Path(manifest['originalCoreRoot'])
        raw, _ = command(phase+'-torah-core', ['git','-c','safe.directory='+str(directory),'-C',str(directory),
            'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
        rows = raw.decode().splitlines()
        assert '# branch.oid '+manifest['originalCoreCommit'] in rows and all(row.startswith('# ') for row in rows), 'Core source checkout changed'

    try:
        assert result['minimumRootFreeBytes'] >= ROOT_ADMISSION, 'initial root 2 GiB plus 32 MiB admission'
        assert result['minimumDevelopmentFreeBytes'] >= DEVELOPMENT_ADMISSION, 'initial development budget admission'
        for name in ('temporary','module-cache','clang-module-cache','swift-cache','swift-config','swift-security','http-fixtures'):
            (output/name).mkdir(mode=0o700)
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('PINKHA_', 'SWIFT_', 'SWIFTPM_', 'CLANG_', 'DYLD_', 'LD_'))}
        env.update(TMPDIR=str(output/'temporary'), SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
                   CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'), XDG_CACHE_HOME=str(output/'swift-cache'),
                   GIT_OPTIONAL_LOCKS='0', SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2')
        manifest = json.loads(base.read(MANIFEST, maximum=256*1024))
        assert manifest['schema'] == 1 and manifest['scope'] == 'ISOLATED_BOOKMARK_CREATION_COMPONENT_SOURCE_CLOSURE_ONLY'
        assert manifest['expectedCounts']['methods'] == 31 and len(manifest['preparedSources']) == 9
        assert manifest['expectedCounts']['compiledTestFiles'] == 3 and manifest['expectedCounts']['excludedNativeMethods'] == 0
        assert manifest['excludedNativeMethods'] == {}
        assert manifest['retainedUploadSourceRoot'] == str(RETAINED_UPLOAD_PREPARED)
        for path, expected in controls.items():
            base.pinned(path, expected)
            immutable[str(path)] = base.row(path)
        dependency_status('before', manifest)
        helper = load_module(CRYPTO_HELPER, 'bookmark_creation_crypto', CRYPTO_HELPER_SHA, base)
        guard()
        reused = helper.qualify(output, base, guard)
        immutable.update(reused['immutableInputs'])
        copies.update(reused['copiedModules'])
        copies.update(reused['copiedHeaders'])
        copies[reused['receipt']['path']] = {key:reused['receipt'][key] for key in ('bytes','sha256')}
        guard()
        package = output/'package'
        package.mkdir(mode=0o700)

        def materialize(path, target, expected):
            remember_input(path, expected)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            base.copy_exact(path, target, {'bytes':expected['bytes'], 'sha256':expected['sha256']})
            copies[str(target)] = base.row(target)

        project_root = Path(manifest['originalProjectRoot'])
        for entry in manifest['originalProjectFiles']:
            source = project_root/entry['path']
            remember_input(source, entry)
            if entry['compile']:
                materialize(source, package/'Sources'/entry['target']/source.name, entry)
        core_root = Path(manifest['originalCoreRoot'])
        assert {str(path.relative_to(core_root)) for path in (core_root/'Sources/TorahInspectorCore').rglob('*.swift')} == {entry['path'] for entry in manifest['originalCoreFiles']}
        for entry in manifest['originalCoreFiles']:
            source = core_root/entry['path']
            materialize(source, package/'Sources/TorahInspectorCore'/source.name, entry)
        for entry in manifest['preparedSources']:
            assert entry['sourceBase'] in ('retained-upload-prepared3', 'bookmark-prepared1')
            source_root = RETAINED_UPLOAD_PREPARED if entry['sourceBase'] == 'retained-upload-prepared3' else PREPARED
            source = source_root/entry['path']
            if entry['kind'] == 'production':
                target = package/'Sources'/entry['target']/source.name
            elif entry['kind'] == 'test':
                target = package/'Tests/BookmarkCreationTests'/source.name
            else:
                raise AssertionError('undeclared new Bookmark source kind')
            materialize(source, target, entry)
        assert len(list((package/'Sources').rglob('*.swift'))) == 33
        assert len(list((package/'Tests/BookmarkCreationTests').glob('*.swift'))) == 3
        package_file = package/'Package.swift'
        package_file.write_text(package_text(reused['compilerFlags'], reused['linkObjects']))
        os.chmod(package_file, 0o600)
        copies[str(package_file)] = base.row(package_file)
        source_admission_complete = True
        source_input_file = output/'compiled-source-inputs.json'
        save(source_input_file, {'originalInputs':immutable, 'isolatedCopies':copies,
              'counts':manifest['expectedCounts'], 'indexStore':'enabled; no disable-index-store flag',
              'noExistingProjectModuleImportDirectories':True})
        # Bind these exact generated Package/Crypto/source expectations to the
        # successful component receipt; a later consumer cannot replace this
        # manifest and merely compare a new self-consistent set of copies.
        result['compiledSourceInputs'] = dict(path=str(source_input_file), **base.row(source_input_file))
        copies[str(source_input_file)] = {key:result['compiledSourceInputs'][key] for key in ('bytes','sha256')}
        filter_names = '|'.join(manifest['methods'])
        swift_folder = output/'commands'/'swift-components'
        test_env = dict(env, PINKHA_BOOKMARK_FRAME_FIXTURE_ROOT=str(output/'http-fixtures'),
                        PINKHA_BOOKMARK_FRAME_OWNER_RECORD=str(swift_folder/'started.json'),
                        PINKHA_BOOKMARK_FRAME_OWNER_CWD=str(package))
        argv = [reused['swiftDriver'],'test','--package-path',str(package),'--scratch-path',str(output/'build'),
                '--cache-path',str(output/'swift-cache'),'--config-path',str(output/'swift-config'),
                '--security-path',str(output/'swift-security'),'--disable-automatic-resolution','--jobs','2',
                '--filter',filter_names]
        raw, swift = command('swift-components', argv, package, test_env, SWIFT_SECONDS)
        log = raw.decode(errors='strict')
        expected = {name+'.'+method for name,methods in manifest['methods'].items() for method in methods}
        starts = re.findall(r"Test Case '([^']+)' started", log)
        passes = re.findall(r"Test Case '([^']+)' passed", log)
        excluded = {name+'.'+method for name,methods in manifest['excludedNativeMethods'].items() for method in methods}
        result['separateNativeTestStarts'] = [name for name in starts if name in excluded]
        result['separateNativeTestStatus'] = 'NOT_RUN' if not result['separateNativeTestStarts'] else 'UNEXPECTED_COMPONENT_START'
        assert not result['separateNativeTestStarts'], 'separate actual-native method was not selected by this controller'
        assert len(expected) == len(starts) == len(passes) == 31
        assert set(starts) == set(passes) == expected, 'actual XCTest inventory differs from the frozen 31 new methods'
        assert all(starts.count(name) == passes.count(name) == 1 for name in expected)
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|Skipping XCTest discovery|XCTSkip", log)
        assert re.search(r'Executed 31 tests?, with 0 failures', log)
        result['actualMethods'] = {'started':starts, 'passed':passes, 'skipped':0,
                                  'exactValue':7, 'frame':20, 'httpBearing':10, 'nonHTTP':21, 'postClose':4, 'total':31}
        result['httpFixtureQualification'] = fixture_audit(output/'http-fixtures', swift_folder/'started.json', swift, base, manifest)
        result['retainedDependencyProducts'] = reused['receipt']
        product_closure = retained_products(output/'build', base, guard)
        result['compiledProducts'] = product_closure['files']
        result['compiledProductModes'] = product_closure['modes']
        result['compiledProductDirectories'] = product_closure['directories']
        result['compiledExecutables'] = product_closure['executables']
        result['compiledTestRunner'] = product_closure['testRunner']
        result['compiledProductsRoot'] = product_closure['root']
        dependency_status('after', manifest)
        result['status'] = 'PASS'
    except BaseException as error:
        result['status'] = 'FAIL'
        result['errors'].append({'type':type(error).__name__, 'message':str(error)})
    finally:
        owned.ignore_interrupts()
        final_deadline = min(started_at+TOTAL_SECONDS, time.monotonic()+120)
        # Cached positive observations survive any later integrity/budget error.
        result['allStartedOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') is True for row in result['commands'])
        try:
            for path, expected in immutable.items():
                guard()
                assert base.row(Path(path)) == expected, path+' final original input mismatch'
            for path, expected in copies.items():
                guard()
                assert base.row(Path(path)) == expected, path+' final copied input mismatch'
            if 'compiledSourceInputs' in result:
                original = result['compiledSourceInputs']
                assert base.row(Path(original['path'])) == {key:original[key] for key in ('bytes','sha256')}
                result['compiledSourceInputsUnchanged'] = True
            if 'compiledProducts' in result:
                after_products = retained_products(output/'build', base, guard)
                assert after_products['root'] == result['compiledProductsRoot']
                assert after_products['files'] == result['compiledProducts']
                assert after_products['modes'] == result['compiledProductModes']
                assert after_products['directories'] == result['compiledProductDirectories']
                assert after_products['executables'] == result['compiledExecutables']
                assert after_products['testRunner'] == result['compiledTestRunner']
                result['compiledProductsAndModesUnchanged'] = True
            for path, expected in controls.items():
                guard()
                base.pinned(path, expected)
            if reused is not None:
                helper.validate_after(reused, guard)
            result['admittedInputsUnchanged'] = True
            result['sourceUnchanged'] = source_admission_complete
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-integrity', 'type':type(error).__name__, 'message':str(error)})
        try:
            swift_log = output/'commands/swift-components/original.log'
            if swift_log.exists() and manifest is not None:
                raw_log = base.read(swift_log, maximum=LOG_CAP).decode(errors='replace')
                starts = re.findall(r"Test Case '([^']+)' started", raw_log)
                excluded = {name+'.'+method for name,methods in manifest['excludedNativeMethods'].items() for method in methods}
                native_starts = [name for name in starts if name in excluded]
                result['separateNativeTestStarts'] = native_starts
                result['separateNativeTestStatus'] = 'NOT_RUN' if not native_starts else 'UNEXPECTED_COMPONENT_START'
                assert not native_starts, 'unexpected native test start in component command'
            reason = observe()
            if reason is not None:
                raise RuntimeError(reason)
            assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['commands'])
            if result['status'] == 'PASS':
                assert len(result['commands']) == 7 and result['actualMethods']['total'] == 31
                assert result['httpFixtureQualification']['instances'] == 17
                assert result['httpFixtureQualification']['requestCount'] == 76
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-lifecycle-and-budget', 'type':type(error).__name__, 'message':str(error)})
        result['seconds'] = round(time.monotonic()-started_at,3)
        result['declaredControlledOutputBytesOnRoot'] = 0
        result['noGlobalRootWriteAuditClaim'] = True
        save(output/'result.json', result)
    print(json.dumps({'status':result['status'], 'receipt':str(output/'result.json'),
                      'sha256':base.sha(output/'result.json'), 'seconds':result['seconds']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
