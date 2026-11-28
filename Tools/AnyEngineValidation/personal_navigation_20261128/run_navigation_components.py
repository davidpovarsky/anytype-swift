#!/usr/bin/env python3
"""Complete Navigation26 with 23 retained passes and three corrected fixture methods.

SOURCE-ONLY until this controller actually completes. It opens no native
account, compiles no dependency, and does not replay any FilesV2 or migration
proof. The two reused Crypto modules are admitted from the exact retained
producer; every product module under test is compiled from its full sources.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import datetime
import signal
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
PARENT = Path('/mnt/development/projects/evidence/pinkha-original-navigation26-20261128')
NAVIGATION_FAILURE = PARENT/'components-attempt1/result.json'
NAVIGATION_FAILURE_SHA = 'fad0f014de35e58948b5f6df57dc69f8dda569776eb2bd3b125bb39913d4f7ad'
NAVIGATION_FAILURE_LOG = PARENT/'components-attempt1/commands/swift-components/original.log'
NAVIGATION_FAILURE_LOG_SHA = '67f8b4ae0392d68226717a6be4bcab514987e8302ba69090dde89bc86213d20f'
NAVIGATION_FAILURE_INPUTS = PARENT/'components-attempt1/compiled-source-inputs.json'
NAVIGATION_FAILURE_INPUTS_SHA = '980f8486c446472adfc9d9a0483f850538003a4b90d03158132401f7d586e0c8'
NAVIGATION_PRIOR_CONTROLLER = PARENT/'prepared1/run_navigation_components.py'
NAVIGATION_PRIOR_CONTROLLER_SHA = 'fe40cfcad9883748574bd1df011f41beb2abaa84316ccc79ef33f94df3cd8403'
NAVIGATION_PRIOR_MANIFEST = PARENT/'prepared1/navigation-component-inputs.json'
NAVIGATION_PRIOR_MANIFEST_SHA = '2c2b82a39693c477ccd9fe255351d5f52dd78e3b0f378b12056fe18c02e91fd7'
TYPE25_PARENT = Path('/mnt/development/projects/evidence/pinkha-original-type-runtime-provider25-20261127')
METADATA6_PARENT = Path('/mnt/development/projects/evidence/pinkha-original-source-metadata6-20261127')
PREPARED = PARENT/'prepared3'
CONTROL = Path(__file__).parent
MANIFEST = CONTROL/'navigation-component-inputs.json'
MANIFEST_SHA = 'fdac37214d2f8c1ac561278df5ac37ad2606ea1e2333023a502b0ba3d8e5c0cf'
CRYPTO_HELPER = CONTROL/'qualify_provider_crypto_c3.py'
CRYPTO_HELPER_SHA = '9ec68e6db7ad722866236ab4494df3108fee60791a40a8d218c93a82d817805b'
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
OWNED_ALLOCATION_CAP = 384 * MIB
DEVELOPMENT_ADMISSION = DEVELOPMENT_FLOOR + OWNED_ALLOCATION_CAP + 32 * MIB
LOG_CAP = 16 * MIB
FIXTURE_CAP = 16 * MIB
RECEIPT_CAP = 4 * MIB
TOTAL_SECONDS = 900
SWIFT_SECONDS = 600
FIXTURE_INPUTS = CONTROL/'provider_fixture_inputs.py'
FIXTURE_INPUTS_SHA = '32cec96b4984b02d1cae76c94ccc73e958f0f890f32e68e9729ab7db4b13b5cf'
BUNDLE_INPUTS = CONTROL/'bundle_recovery_inputs.py'
BUNDLE_INPUTS_SHA = 'f7b8155be19a890cd7e7351c22ca46c4d337ca9b1052bc7b4c80be84abb4c3e4'
BASELINE_INPUTS = CONTROL/'compiled-source-313.json'
BASELINE_INPUTS_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
PRIOR_FAILURE = TYPE25_PARENT/'components-attempt1/result.json'
PRIOR_FAILURE_SHA = '82998f003873e5c3ba44f230003af78a6015d5b9f34f7ab6ce858b3e9466c18c'
PRIOR_LOG = TYPE25_PARENT/'components-attempt1/commands/swift-components/original.log'
PRIOR_LOG_SHA = '764276f2f20a858f9b8f1e9328d1a758d4359549df750efcb00bc1483f447a10'
SYNTAX_FAILURE = TYPE25_PARENT/'components-attempt2/result.json'
SYNTAX_FAILURE_SHA = 'ef9cd141fc26457463abd4beecab8399e6d5e2bef7a589c2a3b59fad5152b52f'
SYNTAX_LOG = TYPE25_PARENT/'components-attempt2/commands/swift-components/original.log'
SYNTAX_LOG_SHA = 'f91c2df2cab225e44e223bbb1d6e4e8d96d726091353eb7c0376dbc2f7502542'
TYPE25_RECEIPT = TYPE25_PARENT/'components-attempt3/result.json'
TYPE25_RECEIPT_SHA = 'f48358e0a4ac12cab0f354638c9f1fe15479378dcb0b3a7edd6dd4df2b6907e7'
TYPE25_MANIFEST = TYPE25_PARENT/'prepared3/provider-component-inputs.json'
TYPE25_MANIFEST_SHA = '4cabf3c455886e224e9df83aa0cc00f05eb487665306e891a67a53e9ede6bc98'
TYPE25_CONTROLLER = TYPE25_PARENT/'prepared3/run_provider_components.py'
TYPE25_CONTROLLER_SHA = 'b9d7e0748231ba9f34362f68508f27958abd6922eb5ea5e68cb01d093ca8d5e7'
METADATA6_RECEIPT = METADATA6_PARENT/'components-attempt1/result.json'
METADATA6_RECEIPT_SHA = 'c2c9713a4fc8fd99841d34dfec1b1fed25a8cc64d7687fc11919a4c893c53187'
METADATA6_MANIFEST = METADATA6_PARENT/'prepared2/metadata-component-inputs.json'
METADATA6_MANIFEST_SHA = 'cb47fb0293e32e7e4d8f9c2c89c0c4e21640b47439ca9d1b2a8199b710df2ec4'

RETAINED_NAVIGATION_ROOT = PARENT/'components-attempt2'
RETAINED_NAVIGATION_RESULT = RETAINED_NAVIGATION_ROOT/'result.json'
RETAINED_NAVIGATION_RESULT_SHA = 'f266f1f7dcc61be8ae8664b50b25e7078ab3ffc29572d07e4626b29eb1394a00'
RETAINED_NAVIGATION_LOG = RETAINED_NAVIGATION_ROOT/'commands/swift-components/original.log'
RETAINED_NAVIGATION_LOG_SHA = '3c77d6e2d017f23795e64131ba32a7c7ed69dfeb1223fc8e5e26c2f5ae11cad2'
RETAINED_NAVIGATION_INPUTS = RETAINED_NAVIGATION_ROOT/'compiled-source-inputs.json'
RETAINED_NAVIGATION_INPUTS_SHA = 'ce38612884f316845702391f443989f19fbef0cd493af915b7f75d3ea536c499'
RETAINED_NAVIGATION_CONTROLLER = PARENT/'prepared2/run_navigation_components.py'
RETAINED_NAVIGATION_CONTROLLER_SHA = 'e3dd22632d26fd6b7c2e9bc6adf911c99808193926beda8fccf68addc2860150'
RETAINED_NAVIGATION_MANIFEST = PARENT/'prepared2/navigation-component-inputs.json'
RETAINED_NAVIGATION_MANIFEST_SHA = '27396e6a6d5899029816edc457863c39426c9b4a0c6f0123c4efa594305c802a'
NEW_SELECTED_METHODS = {
    'NativePersonalNavigationContractTests.testOriginalLastOpenedDescriptorAndDecodedBindingKeepExactSourceIdentity',
    'NativePersonalNavigationContractTests.testHomePreservesAbsentEmptyUnknownAndClosedWireVariants',
    'NativePersonalNavigationHTTPTests.testAcknowledgmentSurvivesAnEnclosingSessionRetirementWithoutPrivateReadback',
}

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
    runners = [name for name in files if Path(name).name == 'NavigationContractTests-test-runner']
    assert len(runners) == 1 and runners[0] in executables, 'one actual executable Linux XCTest runner'
    libraries = [name for name in files if Path(name).name == 'NavigationContractTests.so']
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
    rows.append('        .testTarget(name: "NavigationContractTests", dependencies: ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost"], swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')], linkerSettings: [.unsafeFlags('+link_flags+')])')
    return '// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: "OriginalNavigationProof", targets: [\n'+',\n'.join(rows)+'\n])\n'


def fixture_audit(root, owner_record, owner, base, manifest, retained_failed_owner=False):
    """Retain exact synthetic request/ACK scope inside the qualified owner group."""
    assert root.resolve() == root and stat.S_IMODE(root.stat().st_mode) == 0o700
    directories = sorted(root.iterdir())
    expected_instances = 13 if retained_failed_owner else 1
    assert len(directories) == expected_instances, 'exact retained or targeted fixture inventory required'
    owner_sha = base.sha(owner_record)
    identities, rows, all_requests, modes, normal_writes = set(), [], [], [], []
    mandatory = {'config.json','server.py','account.txt','run.txt','port.json',
                 'start.json','exit.json','parent-stop.json','stderr.log','requests.json'}
    optional = {'owner-retired.json','removed.txt','applied.json'}
    allowed_modes = {'normal','retire-after-write','missing-ack','foreign-ack','shared-ack',
                     'nonlocal','foreign-target','unmaterialized','guest-member'}
    read_paths = {'/v1/auth','/v1/auth/engine-binding','/v1/spaces/space/members/me',
                  '/v1/spaces/space','/v1/spaces/space/types/any/properties',
                  '/v1/spaces/space/objects/object'}
    settings_path = '/v1/pinkha/bound/spaces/space/settings'
    property_path = '/v1/pinkha/bound/spaces/space/properties/object/set/any'
    for directory in directories:
        assert re.fullmatch(r'case-[0-9A-Fa-f-]{36}', directory.name)
        assert directory.resolve() == directory and directory.is_dir()
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        paths = {path.name:path for path in directory.iterdir()}
        assert mandatory <= set(paths) <= mandatory | optional, 'closed fixture artifact set'
        artifacts, values, text_files = {}, {}, {}
        for name, path in paths.items():
            info = path.lstat()
            assert path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            assert info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600
            raw = base.read(path, maximum=MIB)
            artifacts[name] = {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            if name.endswith('.json'):
                values[name] = json.loads(raw)
            elif name.endswith('.txt'):
                text_files[name] = raw.decode('utf-8')
        assert artifacts['server.py'] == manifest['fixtureScript'], 'exact compiled embedded fixture bytes'
        config = values['config.json']
        assert set(config) == {'mode','controlToken'} and config['controlToken'] == 'a'*64
        mode = config['mode']
        assert mode in allowed_modes
        if not retained_failed_owner:
            assert mode == 'retire-after-write', 'only the selected retirement method opens a new fixture'
        modes.append(mode)
        assert text_files['account.txt'] == 'account'
        assert text_files['run.txt'] in ('a'*64,'b'*64)
        if 'removed.txt' in text_files:
            assert mode == 'normal' and text_files['removed.txt'] == 'removed'
        assert type(values['port.json']) is int and 1 <= values['port.json'] <= 65535
        started, ended, stopped = (values[name] for name in ('start.json','exit.json','parent-stop.json'))
        assert started['controllerOwnedGroup'] is True
        assert started['ownerRecord'] == str(owner_record) and started['ownerRecordSHA256'] == owner_sha
        assert started['ownerPID'] == owner['pid'] == started['pgid'] == started['sessionID']
        identity = (started['pid'], started['startTimeTicks'])
        assert started['pid'] > 1 and identity not in identities
        identities.add(identity)
        assert started['startTimeTicks'] > 0 and re.fullmatch(r'[0-9a-f-]{36}',started['bootID'])
        assert 1 <= len(started['ownerAncestors']) <= 64
        assert started['ownerAncestors'][0]['pid'] == started['parentPID']
        assert started['ownerAncestors'][-1]['pid'] == owner['pid']
        assert all(item['startTimeTicks'] > 0 for item in started['ownerAncestors'])
        assert set(ended) == set(started) | {'reason','requestCount'}
        assert {key:ended[key] for key in started} == started and ended['reason'] == 'stdin-eof'
        assert set(stopped) == {'started','pid','leaderObservedExited','exitCode','ownership','errors'}
        assert stopped['started'] is True and stopped['pid'] == started['pid']
        assert stopped['leaderObservedExited'] is True and stopped['exitCode'] == 0
        assert stopped['ownership'] == started and stopped['errors'] == []
        assert artifacts['stderr.log']['bytes'] == 0, 'fixture error output fails qualification'
        requests = values['requests.json']
        assert type(requests) is list and 1 <= len(requests) <= 512
        assert ended['requestCount'] == len(requests)
        writes = []
        for request in requests:
            assert set(request) == {'method','path','body','expectedAccount','expectedRun'}
            if request['method'] == 'GET':
                assert request['path'] in read_paths and request['body'] is None
                assert request['expectedAccount'] is None and request['expectedRun'] is None
                continue
            assert request['expectedAccount'] == 'account' and request['expectedRun'] == 'a'*64
            if request['method'] == 'PATCH':
                assert request['path'] == settings_path
                body = request['body']
                if body != {'unset':['pinkhaHomeV1']}:
                    assert type(body) is dict and set(body) == {'set'}
                    assert type(body['set']) is dict and set(body['set']) == {'pinkhaHomeV1'}
                    value = body['set']['pinkhaHomeV1']
                    assert value in ('','{"contract":"pinkha-current-home-v1","kind":"object","objectId":"object"}')
            elif request['method'] == 'POST':
                assert request['path'] == property_path
                body = request['body']
                assert type(body) is dict and set(body) == {'patch'}
                assert type(body['patch']) is dict and set(body['patch']) == {'pinkhaLastOpenedV1'}
                value = body['patch']['pinkhaLastOpenedV1']
                assert type(value) is dict and set(value) == {'$date'}
                milliseconds = value['$date']
                assert type(milliseconds) is int and 0 <= milliseconds <= 253402300799000 and milliseconds % 1000 == 0
            else:
                raise AssertionError('undeclared navigation fixture method')
            writes.append(request)
        if mode == 'normal':
            normal_writes.append(len(writes))
        if mode in {'nonlocal','foreign-target','unmaterialized','guest-member'}:
            assert writes == [] and 'applied.json' not in values
        if mode == 'guest-member':
            assert not any(request['path'] in {
                '/v1/spaces/space/types/any/properties','/v1/spaces/space/objects/object'
            } for request in requests), 'synthetic foreign guest identity refused before private target preparation'
        if mode in {'missing-ack','foreign-ack','shared-ack','retire-after-write'}:
            assert len(writes) == 1 and writes[0]['method'] == 'POST', 'one attempt without resend'
        if text_files['run.txt'] == 'b'*64 or 'removed.txt' in text_files:
            assert mode == 'normal' and not writes and 'applied.json' not in values
        if writes:
            applied = values['applied.json']
            assert set(applied) == {'count','home','opened'} and applied['count'] == len(writes)
            if writes[-1]['method'] == 'POST':
                milliseconds = writes[-1]['body']['patch']['pinkhaLastOpenedV1']['$date']
                native_date = datetime.datetime.fromtimestamp(milliseconds//1000,datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
                assert applied['opened'] == {'$date':native_date} and applied['home'] is None
            else:
                assert len(writes) == 3 and all(request['method'] == 'PATCH' for request in writes)
                assert writes[0]['body'] == {'set':{'pinkhaHomeV1':''}}
                assert writes[1]['body'] == {'set':{'pinkhaHomeV1':'{"contract":"pinkha-current-home-v1","kind":"object","objectId":"object"}'}}
                assert writes[2]['body'] == {'unset':['pinkhaHomeV1']}
                assert applied['home'] is None and applied['opened'] is None
        if mode == 'retire-after-write':
            assert values.get('owner-retired.json') is True
            assert requests[-1] == writes[0], 'retired enclosing owner must prevent private readback dispatch'
        else:
            assert 'owner-retired.json' not in values
        all_requests.extend(requests)
        rows.append({'directory':str(directory),'fixturePID':started['pid'],'ownedGroup':started['pgid'],
                     'mode':mode,'stdinEOFExit':True,'requestCount':len(requests),
                     'syntheticWriteCount':len(writes),'artifacts':artifacts})
    expected_modes = ({
        'normal':5,'retire-after-write':1,'missing-ack':1,'foreign-ack':1,'shared-ack':1,
        'nonlocal':1,'foreign-target':1,'unmaterialized':1,'guest-member':1}
        if retained_failed_owner else {'retire-after-write':1})
    assert {mode:modes.count(mode) for mode in set(modes)} == expected_modes
    assert sorted(normal_writes) == ([0,0,1,1,3] if retained_failed_owner else [])
    posts = sum(request['method'] == 'POST' for request in all_requests)
    patches = sum(request['method'] == 'PATCH' for request in all_requests)
    gets = sum(request['method'] == 'GET' for request in all_requests)
    assert posts == (6 if retained_failed_owner else 1) and patches == (3 if retained_failed_owner else 0)
    assert gets+posts+patches == len(all_requests)
    assert owner['processGroupAbsent'] and owner['exitCode'] == (1 if retained_failed_owner else 0)
    assert not owner['forcedCleanup'] and not owner['signals'] and not owner['cleanupErrors']
    return {'instances':expected_instances,'requestCount':len(all_requests),'GETCount':gets,'POSTCount':posts,
            'PATCHCount':patches,'syntheticWriteCount':posts+patches,'nativeEffectsQualified':False,
            'historicalFailedOwner':retained_failed_owner,'observedOwnerExitCode':owner['exitCode'],
            'allOwnedOriginalGroup':True,'allCleanEOF':True,
            'syntheticGuestRefusedBeforeEffect':True if retained_failed_owner else None,'nativeGuestAuthorityQualified':False,
            'groupAbsenceSource':'qualified unreaped owner closure; no post-reap PID probing',
            'fixtureRows':rows}



def admit_retained_navigation(base, current_manifest, guard):
    """Read the exact failed command and retain only its 23 unaffected passes.

    Historical exit 1, both failures and the superseded Home pass remain
    explicit. This opens public source/evidence and synthetic fixture records;
    it neither imports historical build products nor probes historical PIDs.
    """
    guard()
    prior = json.loads(base.read(RETAINED_NAVIGATION_RESULT, maximum=RECEIPT_CAP))
    old_manifest = json.loads(base.read(RETAINED_NAVIGATION_MANIFEST, maximum=256*1024))
    source_ledger = json.loads(base.read(RETAINED_NAVIGATION_INPUTS, maximum=2*MIB))
    raw_log = base.read(RETAINED_NAVIGATION_LOG, maximum=LOG_CAP).decode('utf-8')
    assert prior['status'] == 'FAIL' and prior['errors'] == [
        {'message':'owned command did not finish normally: swift-components','type':'RuntimeError'},
        {'message':'','phase':'final-lifecycle-and-budget','type':'AssertionError'}]
    assert prior['controllerSHA256'] == RETAINED_NAVIGATION_CONTROLLER_SHA
    assert prior['inputManifestSHA256'] == RETAINED_NAVIGATION_MANIFEST_SHA
    assert prior['compiledSourceInputs'] == {
        'path':str(RETAINED_NAVIGATION_INPUTS),'bytes':777175,'sha256':RETAINED_NAVIGATION_INPUTS_SHA}
    assert all(prior[key] is True for key in ('sourceUnchanged','admittedInputsUnchanged',
        'compiledSourceInputsUnchanged','originalSourceFixtureInputsAndCopiesUnchanged',
        'allStartedOwnedGroupsPositivelyAbsent'))
    assert prior['earlierTestStarts'] == [] and prior['earlierTestReplayStatus'] == 'NOT_RUN'
    assert prior['nativeAccountsOpened'] is False and prior['nativeStorageQualified'] is False
    assert 'compiledProducts' not in prior, 'no historical qualified Products map is inferred'
    assert len(prior['commands']) == 4 and [row['exitCode'] for row in prior['commands']] == [0,0,0,1]
    assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['signals'] and
               not row['cleanupErrors'] and row['stopReason'] is None for row in prior['commands'])
    prior_swift = prior['commands'][3]
    assert prior_swift['logSHA256'] == RETAINED_NAVIGATION_LOG_SHA
    assert prior_swift['cwd'] == str(RETAINED_NAVIGATION_ROOT/'package')
    assert prior_swift['argv'] == [
        str(TOOLCHAIN/'swift'),'test','--package-path',str(RETAINED_NAVIGATION_ROOT/'package'),
        '--scratch-path',str(RETAINED_NAVIGATION_ROOT/'build'),
        '--cache-path',str(RETAINED_NAVIGATION_ROOT/'swift-cache'),
        '--config-path',str(RETAINED_NAVIGATION_ROOT/'swift-config'),
        '--security-path',str(RETAINED_NAVIGATION_ROOT/'swift-security'),
        '--disable-automatic-resolution','--jobs','2','--filter','|'.join(old_manifest['methods'])]
    original_names = {name+'.'+method for name,methods in old_manifest['methods'].items() for method in methods}
    current_names = {name+'.'+method for name,methods in current_manifest['methods'].items() for method in methods}
    selected_names = {name+'.'+method for name,methods in current_manifest['selectedMethods'].items() for method in methods}
    starts = re.findall(r"Test Case '([^']+)' started", raw_log)
    passes = re.findall(r"Test Case '([^']+)' passed", raw_log)
    failures = re.findall(r"Test Case '([^']+)' failed", raw_log)
    failed_names = {
        'NativePersonalNavigationContractTests.testOriginalLastOpenedDescriptorAndDecodedBindingKeepExactSourceIdentity',
        'NativePersonalNavigationHTTPTests.testAcknowledgmentSurvivesAnEnclosingSessionRetirementWithoutPrivateReadback',
    }
    superseded = ['NativePersonalNavigationContractTests.testHomePreservesAbsentEmptyUnknownAndClosedWireVariants']
    assert original_names == current_names and len(original_names) == 26
    assert len(starts) == len(set(starts)) == 26 and set(starts) == original_names
    assert len(passes) == len(set(passes)) == 24 and set(passes) == original_names-failed_names
    assert len(failures) == 2 and set(failures) == failed_names
    assert selected_names == NEW_SELECTED_METHODS == failed_names | set(superseded)
    assert re.search(r'Build complete! \(62\.57 secs\)', raw_log)
    assert re.search(r'Executed 26 tests, with 2 failures \(2 unexpected\)', raw_log)
    assert 'The given data was not valid JSON.' in raw_log and 'CancellationError()' in raw_log
    assert not re.search(r"Test Case '[^']+' skipped|Skipping XCTest discovery|XCTSkip", raw_log)
    retained = sorted(set(passes)-selected_names)
    assert len(retained) == 23 and retained == current_manifest['retainedMethods']
    assert set(retained).isdisjoint(selected_names)
    assert source_ledger['counts'] == old_manifest['expectedCounts']
    assert source_ledger['noExistingProjectModuleImportDirectories'] is True
    assert source_ledger['indexStore'] == 'enabled; no disable-index-store flag'
    assert len(source_ledger['originalInputs']) == 2159 and len(source_ledger['isolatedCopies']) == 530

    # All 112 whole sources are joined to the actual compiler input ledger.
    # Only two test-source byte sequences differ in the new composition.
    for key in ('originalProjectRoot','originalProjectFiles','originalCoreRoot','originalCoreFiles',
                'dependencySourcePins','originalCoreCommit','originalProjectCommit','fixtureScript',
                'methods','excludedEarlierMethods','sourceModes'):
        assert current_manifest[key] == old_manifest[key], 'unchanged source closure: '+key
    old_prepared = {row['path']:row for row in old_manifest['preparedSources']}
    new_prepared = {row['path']:row for row in current_manifest['preparedSources']}
    assert set(old_prepared) == set(new_prepared) and len(old_prepared) == 16
    corrected = current_manifest['fixtureCompletion']['correctedSources']
    assert set(corrected) == {
        'Tests/NativePersonalNavigationContractTests.swift',
        'Tests/NativePersonalNavigationHTTPTests.swift'}
    for name in old_prepared:
        if name not in corrected:
            assert old_prepared[name] == new_prepared[name]
        else:
            assert old_prepared[name]['kind'] == new_prepared[name]['kind'] == 'test'
            assert old_prepared[name]['target'] == new_prepared[name]['target'] == 'NavigationContractTests'
            assert old_prepared[name]['sha256'] == corrected[name]['before']['sha256']
            assert old_prepared[name]['bytes'] == corrected[name]['before']['bytes']
            assert new_prepared[name]['sha256'] == corrected[name]['after']['sha256']
            assert new_prepared[name]['bytes'] == corrected[name]['after']['bytes']
    joined = 0
    for entry in old_manifest['originalProjectFiles']:
        guard()
        if not entry['compile']:
            continue
        original = Path(old_manifest['originalProjectRoot'])/entry['path']
        isolated = ('Tests/NavigationContractTests' if entry['kind']=='test-helper'
                    else 'Sources/'+entry['target'])+'/'+original.name
        row = {key:entry[key] for key in ('bytes','sha256')}
        assert source_ledger['originalInputs'][str(original)] == row
        assert source_ledger['isolatedCopies'][str(RETAINED_NAVIGATION_ROOT/'package'/isolated)] == row
        joined += 1
    for entry in old_manifest['originalCoreFiles']:
        guard()
        original = Path(old_manifest['originalCoreRoot'])/entry['path']
        row = {key:entry[key] for key in ('bytes','sha256')}
        assert source_ledger['originalInputs'][str(original)] == row
        assert source_ledger['isolatedCopies'][str(RETAINED_NAVIGATION_ROOT/'package'/'Sources/TorahInspectorCore'/original.name)] == row
        joined += 1
    for entry in old_manifest['preparedSources']:
        guard()
        original = PARENT/'prepared2'/entry['path']
        isolated = ('Tests/NavigationContractTests' if entry['kind']=='test'
                    else 'Sources/'+entry['target'])+'/'+original.name
        row = {key:entry[key] for key in ('bytes','sha256')}
        assert base.row(original) == row
        assert source_ledger['originalInputs'][str(original)] == row
        assert source_ledger['isolatedCopies'][str(RETAINED_NAVIGATION_ROOT/'package'/isolated)] == row
        joined += 1
    assert joined == 112

    for name, correction in corrected.items():
        guard()
        old_bytes = base.read(PARENT/'prepared2'/name, maximum=65536)
        new_bytes = base.read(PREPARED/name, maximum=65536)
        assert {'bytes':len(old_bytes),'sha256':hashlib.sha256(old_bytes).hexdigest()} == correction['before']
        assert {'bytes':len(new_bytes),'sha256':hashlib.sha256(new_bytes).hexdigest()} == correction['after']
        inverse = new_bytes.decode('utf-8')
        for before, after in correction['replacements']:
            assert inverse.count(after) == 1 and old_bytes.decode('utf-8').count(before) == 1
            inverse = inverse.replace(after,before)
        addition = correction.get('addedHelper')
        if addition is not None:
            assert inverse.count(addition) == 1
            inverse = inverse.replace(addition,'')
        assert inverse.encode('utf-8') == old_bytes, 'precise fixture-only inverse'
    guard()
    assert allocation(RETAINED_NAVIGATION_ROOT/'http-fixtures') <= FIXTURE_CAP
    historical_fixtures = fixture_audit(RETAINED_NAVIGATION_ROOT/'http-fixtures',
        RETAINED_NAVIGATION_ROOT/'commands/swift-components/started.json',
        prior_swift, base, old_manifest, retained_failed_owner=True)
    guard()
    return {
        'receipt':str(RETAINED_NAVIGATION_RESULT),'receiptSHA256':RETAINED_NAVIGATION_RESULT_SHA,
        'log':str(RETAINED_NAVIGATION_LOG),'logSHA256':RETAINED_NAVIGATION_LOG_SHA,
        'compiledSourceInputsSHA256':RETAINED_NAVIGATION_INPUTS_SHA,
        'originalStatus':'FAIL','historicalExitCodes':[0,0,0,1],
        'historicalGroups':4,'historicalTestStarts':26,'historicalPasses':24,'historicalFailures':sorted(failed_names),
        'retainedPassedMethods':retained,'supersededHistoricalPasses':superseded,
        'retainedMethods':23,'newSelectedMethods':sorted(selected_names),
        'fullCompilerSourceCorrespondence':112,'unchangedWholeSources':110,'productionSourcesChanged':0,
        'testSourcesChanged':2,'historicalProductsQualifiedOrReused':False,
        'oldGroupsReprobedOrReplayed':False,'historicalHTTPObserved':historical_fixtures,
        'historicalHTTPIsNotAClaimThatFailedMethodPassed':True,
    }


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
                HEADER_MANIFEST:HEADER_MANIFEST_SHA, LIFECYCLE_RECEIPT:LIFECYCLE_RECEIPT_SHA,
                FIXTURE_INPUTS:FIXTURE_INPUTS_SHA, BUNDLE_INPUTS:BUNDLE_INPUTS_SHA,
                BASELINE_INPUTS:BASELINE_INPUTS_SHA,
                PRIOR_FAILURE:PRIOR_FAILURE_SHA, PRIOR_LOG:PRIOR_LOG_SHA,
                SYNTAX_FAILURE:SYNTAX_FAILURE_SHA, SYNTAX_LOG:SYNTAX_LOG_SHA,
                TYPE25_RECEIPT:TYPE25_RECEIPT_SHA, TYPE25_MANIFEST:TYPE25_MANIFEST_SHA,
                TYPE25_CONTROLLER:TYPE25_CONTROLLER_SHA,
                METADATA6_RECEIPT:METADATA6_RECEIPT_SHA, METADATA6_MANIFEST:METADATA6_MANIFEST_SHA,
                NAVIGATION_FAILURE:NAVIGATION_FAILURE_SHA,NAVIGATION_FAILURE_LOG:NAVIGATION_FAILURE_LOG_SHA,
                NAVIGATION_FAILURE_INPUTS:NAVIGATION_FAILURE_INPUTS_SHA,
                NAVIGATION_PRIOR_CONTROLLER:NAVIGATION_PRIOR_CONTROLLER_SHA,
                NAVIGATION_PRIOR_MANIFEST:NAVIGATION_PRIOR_MANIFEST_SHA,
                RETAINED_NAVIGATION_RESULT:RETAINED_NAVIGATION_RESULT_SHA,
                RETAINED_NAVIGATION_LOG:RETAINED_NAVIGATION_LOG_SHA,
                RETAINED_NAVIGATION_INPUTS:RETAINED_NAVIGATION_INPUTS_SHA,
                RETAINED_NAVIGATION_CONTROLLER:RETAINED_NAVIGATION_CONTROLLER_SHA,
                RETAINED_NAVIGATION_MANIFEST:RETAINED_NAVIGATION_MANIFEST_SHA}
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
    previous = json.loads(base.read(PRIOR_FAILURE,maximum=RECEIPT_CAP))
    assert previous['status']=='FAIL' and previous['controllerSHA256']=='6e2690f9693a00c5fbf6876274156e823426b0c4082cd7b23c00b23bf11cef91'
    assert previous['inputManifestSHA256']=='40d4d54cf15c1f239b4a181fa0aed627416fa74bc862dab87b99e126b9b8cec5'
    assert previous['errors']==[
        {'message':'owned command did not finish normally: swift-components','type':'RuntimeError'},
        {'message':'','phase':'final-lifecycle-and-budget','type':'AssertionError'}]
    assert previous['sourceUnchanged'] and previous['admittedInputsUnchanged'] and previous['compiledSourceInputsUnchanged']
    assert previous['originalSourceFixtureInputsAndCopiesUnchanged'] and previous['allStartedOwnedGroupsPositivelyAbsent']
    assert previous['earlierTestStarts']==[] and previous['earlierTestReplayStatus']=='NOT_RUN'
    assert len(previous['commands'])==4 and [row['exitCode'] for row in previous['commands']]==[0,0,0,1]
    assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] for row in previous['commands'])
    prior_log=base.read(PRIOR_LOG,maximum=LOG_CAP).decode()
    assert "type 'Self' has no member 'project'" in prior_log and not re.search(r"Test Case '[^']+' started",prior_log)
    assert previous['compiledSourceInputs']['sha256']=='e847a9b219c5053258ce8af7af6ac8e100faa0a77a8c7d0b323d4e253b965add'
    syntax_failure = json.loads(base.read(SYNTAX_FAILURE,maximum=RECEIPT_CAP))
    assert syntax_failure['status']=='FAIL'
    assert syntax_failure['controllerSHA256']=='65db477bdc8ac9d812bb5719c361e1815cf76672d8d9030e2b4b48305e517f4b'
    assert syntax_failure['inputManifestSHA256']=='47f4a1fc14b27c541d656ff707a22c6a45efb666566afa4bddaee3060b4c6d87'
    assert syntax_failure['errors']==previous['errors']
    assert all(syntax_failure[flag] is True for flag in ['sourceUnchanged','admittedInputsUnchanged',
        'compiledSourceInputsUnchanged','originalSourceFixtureInputsAndCopiesUnchanged','allStartedOwnedGroupsPositivelyAbsent'])
    assert syntax_failure['earlierTestStarts']==[] and syntax_failure['earlierTestReplayStatus']=='NOT_RUN'
    assert len(syntax_failure['commands'])==4 and [row['exitCode'] for row in syntax_failure['commands']]==[0,0,0,1]
    assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] and
               not row['signals'] and row['stopReason'] is None for row in syntax_failure['commands'])
    syntax_log=base.read(SYNTAX_LOG,maximum=LOG_CAP).decode()
    assert re.findall(r'(?m)^/[^\n]*NativeTypeReferenceTests\.swift:([0-9]+):([0-9]+):',syntax_log)==[('25','17'),('175','13')]
    assert not re.search(r"Test Case '[^']+' started",syntax_log)
    assert syntax_failure['compiledSourceInputs']['sha256']=='b94394911cb1c343440a941830b5eaaea218a85b327a7199bf4a0e0e6eb37797'


    navigation_failure = json.loads(base.read(NAVIGATION_FAILURE,maximum=RECEIPT_CAP))
    assert navigation_failure['status']=='FAIL' and navigation_failure['errors']==previous['errors']
    assert navigation_failure['controllerSHA256']==NAVIGATION_PRIOR_CONTROLLER_SHA
    assert navigation_failure['inputManifestSHA256']==NAVIGATION_PRIOR_MANIFEST_SHA
    assert navigation_failure['compiledSourceInputs']=={
        'bytes':775984,'path':str(NAVIGATION_FAILURE_INPUTS),'sha256':NAVIGATION_FAILURE_INPUTS_SHA}
    assert all(navigation_failure[flag] is True for flag in ('sourceUnchanged','admittedInputsUnchanged',
        'compiledSourceInputsUnchanged','originalSourceFixtureInputsAndCopiesUnchanged','allStartedOwnedGroupsPositivelyAbsent'))
    assert navigation_failure['earlierTestStarts']==[] and navigation_failure['earlierTestReplayStatus']=='NOT_RUN'
    assert navigation_failure['nativeAccountsOpened'] is False and navigation_failure['nativeStorageQualified'] is False
    assert len(navigation_failure['commands'])==4 and [row['exitCode'] for row in navigation_failure['commands']]==[0,0,0,1]
    assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] and
               not row['signals'] and row['stopReason'] is None for row in navigation_failure['commands'])
    navigation_failure_log=base.read(NAVIGATION_FAILURE_LOG,maximum=LOG_CAP).decode()
    assert not re.search(r"Test Case '[^']+' started",navigation_failure_log)
    assert "value of optional type 'String?' must be unwrapped" in navigation_failure_log
    assert '$0["path"]?.string.hasSuffix("/settings")' in navigation_failure_log
    prior_qualifications = []
    for label, receipt_path, source_manifest, selected, controller_sha in (
        ('Type25',TYPE25_RECEIPT,TYPE25_MANIFEST,25,TYPE25_CONTROLLER_SHA),
        ('Metadata6',METADATA6_RECEIPT,METADATA6_MANIFEST,6,
         'f8a32673477e71d90f5f9c9d1c64a9b7fe93117ad3841ae8fe074e58621e4ffe')):
        prior_actual = json.loads(base.read(receipt_path,maximum=RECEIPT_CAP))
        prior_manifest = json.loads(base.read(source_manifest,maximum=256*1024))
        assert prior_actual['status'] == 'PASS' and prior_actual['errors'] == []
        assert prior_actual['controllerSHA256'] == controller_sha
        assert prior_actual['inputManifestSHA256'] == controls[source_manifest]
        prior_expected = {name+'.'+method for name,methods in prior_manifest['methods'].items() for method in methods}
        assert len(prior_expected) == selected and prior_actual['actualMethods']['total'] == selected
        assert prior_actual['actualMethods']['skipped'] == 0
        assert set(prior_actual['actualMethods']['started']) == set(prior_actual['actualMethods']['passed']) == prior_expected
        assert len(prior_actual['actualMethods']['started']) == len(prior_actual['actualMethods']['passed']) == selected
        assert len(prior_actual['commands']) == 7 and prior_actual['allStartedOwnedGroupsPositivelyAbsent'] is True
        assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup'] and
                   not row['cleanupErrors'] and not row['signals'] for row in prior_actual['commands'])
        assert all(prior_actual[flag] is True for flag in ('sourceUnchanged','admittedInputsUnchanged',
            'compiledSourceInputsUnchanged','compiledProductsAndModesUnchanged','originalSourceFixtureInputsAndCopiesUnchanged'))
        assert prior_actual['nativeAccountsOpened'] is False and prior_actual['nativeStorageQualified'] is False
        prior_qualifications.append({'scope':label,'receipt':str(receipt_path),
            'receiptSHA256':controls[receipt_path],'manifest':str(source_manifest),
            'manifestSHA256':controls[source_manifest],'historicalMethods':selected,
            'historicalClosedGroups':7,'newCommands':0,'newMethodsExecuted':0,
            'historicalProductsReopenedOrImported':False,'sourceFilesFreshlyReadAndCompiled':True})
    owned = load_module(OWNED_HELPER, 'ordinary_upload_owned_commands', OWNED_HELPER_SHA, base)
    owned.install_interrupt_handlers()
    owned_output = False
    started_at = time.monotonic()
    result = {'status':'RUNNING', 'scope':'Navigation26 completion: 23 retained passes plus three corrected fixture methods; source and synthetic loopback HTTP only',
              'nativeAccountsOpened':False, 'nativeStorageQualified':False, 'cloudDurabilityQualified':False,
              'earlierTestReplayRequested':False, 'earlierTestReplayStatus':'NOT_DISPATCHED',
              'priorMigrationOrFilesV2MethodsReplayed':0, 'priorUpload35MethodsReplayed':0, 'priorType25MethodsReplayed':0, 'priorMetadata6MethodsReplayed':0, 'errors':[], 'commands':[], 'sourceUnchanged':False,
              'controllerSHA256':args.controller_sha, 'inputManifestSHA256':MANIFEST_SHA,
              'previousQualifiedSourceCohorts':prior_qualifications,
        'previousNavigationFixtureCompileFailure':{
            'receipt':str(NAVIGATION_FAILURE),'sha256':NAVIGATION_FAILURE_SHA,
            'swiftLog':str(NAVIGATION_FAILURE_LOG),'swiftLogSHA256':NAVIGATION_FAILURE_LOG_SHA,
            'compiledSourceInputsSHA256':NAVIGATION_FAILURE_INPUTS_SHA,
            'originalStatus':'FAIL','historicalExitCodes':[0,0,0,1],
            'historicalClosedGroups':4,'actualTestStarts':0,'newCommandsReused':0,
            'newMethodsReused':0,'oldGroupsReprobedOrReplayed':False,
            'testSourceAddedBytes':1,'productionSourcesChanged':0,
            'selectedMethodsChanged':False,'embeddedPythonAndFixtureLifecycleChanged':False},
              'personalNavigationScope':{'ordinaryAuthenticatedAccountOnly':True,
                  'guestAuthorityAccepted':False,'syntheticGuestControlIsNotNativeGuestProof':True},
              'previousTestSyntaxFailure':{'receipt':str(SYNTAX_FAILURE),'sha256':SYNTAX_FAILURE_SHA,
                  'swiftLog':str(SYNTAX_LOG),'swiftLogSHA256':SYNTAX_LOG_SHA,'originalStatus':'FAIL',
                  'actualTestStarts':0,'retainedClosedGroups':4,'historicalGroupsAreNotNewCommands':True,
                  'oldGroupsReprobedOrReplayed':False,'productionSourcesChanged':0,
                  'testSourcesChanged':1,'addedTryAnnotationBytes':8,'selectedMethodsChanged':False},
              'previousClosureFailure':{'receipt':str(PRIOR_FAILURE),'sha256':PRIOR_FAILURE_SHA,
                  'swiftLog':str(PRIOR_LOG),'swiftLogSHA256':PRIOR_LOG_SHA,'originalStatus':'FAIL',
                  'actualTestStarts':0,'retainedClosedGroups':4,'historicalGroupsAreNotNewCommands':True,
                  'oldGroupsReprobedOrReplayed':False,'unchangedPreparedSourceFiles':10,'newOriginalFullFiles':3},
              'unchangedOwnedHelperFiveControlsReused':{'path':str(LIFECYCLE_RECEIPT),'sha256':LIFECYCLE_RECEIPT_SHA,'newlyExecutedControls':0},
              'budget':{'rootRuntimeFloorBytes':ROOT_FLOOR, 'rootAdmissionBytes':ROOT_ADMISSION,
                        'developmentRuntimeFloorBytes':DEVELOPMENT_FLOOR, 'developmentAdmissionBytes':DEVELOPMENT_ADMISSION,
                        'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP, 'declaredControlledOutputBytesOnRoot':0,
                        'finalVerificationSeconds':120, 'mainControllerSeconds':TOTAL_SECONDS, 'requiredOuterSeconds':1080,
                        'allocationCapIsFiniteEstimateNotMeasuredPeak':True,
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
    fixture_input_helper = None
    fixture_input_admission = None
    final_deadline = None
    retained_navigation = None

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
            if final_deadline is None and time.monotonic()-started_at > TOTAL_SECONDS:
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
        setup_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            output.mkdir(mode=0o700)
            owned_output = True
            for path in (output, output.parent):
                descriptor = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, setup_mask)
        save(output/'result.json', result)
        for name in ('temporary','module-cache','clang-module-cache','swift-cache','swift-config','swift-security','http-fixtures'):
            (output/name).mkdir(mode=0o700)
        # Clear inherited setgid only on our new fixture parent; keep its strict700 input guard.
        os.chmod(output/'http-fixtures',0o700)
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('PINKHA_', 'SWIFT_', 'SWIFTPM_', 'CLANG_', 'DYLD_', 'LD_'))}
        env.update(TMPDIR=str(output/'temporary'), SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
                   CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'), XDG_CACHE_HOME=str(output/'swift-cache'),
                   GIT_OPTIONAL_LOCKS='0', SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2')
        manifest = json.loads(base.read(MANIFEST, maximum=256*1024))
        assert manifest['schema'] == 1 and manifest['scope'] == 'ISOLATED_NAVIGATION26_RETAINED23_TARGETED3_COMPLETION'
        assert manifest['expectedCounts']['methods']==26 and len(manifest['preparedSources'])==16
        assert manifest['expectedCounts']['newSelectedMethods']==3 and manifest['expectedCounts']['retainedMethods']==23
        retained_navigation = admit_retained_navigation(base, manifest, guard)
        result['retainedNavigationEvidence'] = retained_navigation
        assert manifest['expectedCounts']['compiledTestFiles']==5 and manifest['expectedCounts']['excludedEarlierMethods']==34
        assert manifest['expectedCounts']['compiledEarlierCanonicalMethods']==3
        assert set(manifest['excludedEarlierMethods'])=={'NativeCanonicalDefinitionSupplementTests',
            'NativeTypeReferenceTests','NativeRuntimeRelationBindingTests','NativeSharedSpacesLimitTests',
            'NativeRuntimeStateTests','NativeRuntimeStateHTTPTests','NativeImportedCatalogMetadataTests'}
        baseline = json.loads(base.read(BASELINE_INPUTS,maximum=131072))
        assert len(baseline)==313 and manifest['original313ManifestSHA256']==BASELINE_INPUTS_SHA
        assert len(manifest['originalProjectFiles'])==89
        assert sum(entry['compile'] for entry in manifest['originalProjectFiles'])==88
        replaced = [entry for entry in manifest['originalProjectFiles'] if not entry['compile']]
        assert len(replaced)==1 and replaced[0]['path']=='Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyHTTPClient.swift'
        assert replaced[0]['replacementPreparedPath']=='Sources/AnyHTTPClient.swift'
        assert all(baseline[entry['path']]==entry['sha256'] for entry in manifest['originalProjectFiles'])
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
        fixture_input_helper = load_module(FIXTURE_INPUTS, 'provider_fixture_inputs', FIXTURE_INPUTS_SHA, base)
        fixture_input_admission = fixture_input_helper.qualify(output/'source-fixtures', base, guard, immutable, copies)
        result['originalFixtureCustody'] = fixture_input_admission['receipt']
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
                target = package/'Tests/NavigationContractTests'/source.name if entry['kind']=='test-helper' else package/'Sources'/entry['target']/source.name
                materialize(source, target, entry)
        core_root = Path(manifest['originalCoreRoot'])
        assert {str(path.relative_to(core_root)) for path in (core_root/'Sources/TorahInspectorCore').rglob('*.swift')} == {entry['path'] for entry in manifest['originalCoreFiles']}
        for entry in manifest['originalCoreFiles']:
            source = core_root/entry['path']
            materialize(source, package/'Sources/TorahInspectorCore'/source.name, entry)
        for entry in manifest['preparedSources']:
            source = PREPARED/entry['path']
            if entry['kind']=='production':
                target = package/'Sources'/entry['target']/source.name
            elif entry['kind']=='test':
                target = package/'Tests/NavigationContractTests'/source.name
            else:
                raise AssertionError('undeclared new provider source kind')
            materialize(source,target,entry)
        assert len(list((package/'Sources').rglob('*.swift'))) == 107
        assert len(list((package/'Tests/NavigationContractTests').glob('*.swift'))) == 5
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
        filter_names = '|'.join(re.escape(name)+r'[/\.]'+re.escape(method)+r'$'
                                for name,methods in manifest['selectedMethods'].items() for method in methods)
        swift_folder = output/'commands'/'swift-components'
        test_env = dict(env, PINKHA_RUNTIME_STATE_FIXTURE_ROOT=str(output/'http-fixtures'),
                        PINKHA_RUNTIME_STATE_OWNER_RECORD=str(swift_folder/'started.json'),
                        PINKHA_RUNTIME_STATE_OWNER_CWD=str(package),
                        PINKHA_NATIVE_DEFINITION_RETAINED=fixture_input_admission['retainedDirectory'],
                        PINKHA_NATIVE_ORIGINAL156=fixture_input_admission['originalDirectory'])
        argv = [reused['swiftDriver'],'test','--package-path',str(package),'--scratch-path',str(output/'build'),
                '--cache-path',str(output/'swift-cache'),'--config-path',str(output/'swift-config'),
                '--security-path',str(output/'swift-security'),'--disable-automatic-resolution','--jobs','2',
                '--filter',filter_names]
        raw, swift = command('swift-components', argv, package, test_env, SWIFT_SECONDS)
        log = raw.decode(errors='strict')
        expected = {name+'.'+method for name,methods in manifest['selectedMethods'].items() for method in methods}
        starts = re.findall(r"Test Case '([^']+)' started", log)
        passes = re.findall(r"Test Case '([^']+)' passed", log)
        excluded = {name+'.'+method for name,methods in manifest['excludedEarlierMethods'].items() for method in methods}
        result['earlierTestStarts'] = [name for name in starts if name in excluded]
        result['earlierTestReplayStatus'] = 'NOT_RUN' if not result['earlierTestStarts'] else 'UNEXPECTED_COMPONENT_START'
        assert not result['earlierTestStarts'], 'original canonical methods were not selected by this controller'
        assert expected == NEW_SELECTED_METHODS and len(expected) == len(starts) == len(passes) == 3
        assert set(starts) == set(passes) == expected, 'actual XCTest inventory differs from the three exact corrected methods'
        assert all(starts.count(name) == passes.count(name) == 1 for name in expected)
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|Skipping XCTest discovery|XCTSkip", log)
        assert re.search(r'Executed 3 tests?, with 0 failures', log)
        result['actualMethods'] = {'started':starts, 'passed':passes, 'skipped':0,
                                  'personalContract':2, 'engineBinding':0, 'originalNavigation':0, 'personalHTTP':1, 'total':3}
        retained_names = retained_navigation['retainedPassedMethods']
        assert len(retained_names) == 23 and not set(retained_names) & expected
        aggregate_names = sorted(set(retained_names) | expected)
        assert len(aggregate_names) == 26
        assert set(aggregate_names) == {name+'.'+method for name,methods in manifest['methods'].items() for method in methods}
        result['qualifiedMethods'] = {'total':26,'retained':23,'newlyExecuted':3,
            'passed':aggregate_names,'retainedPassedMethods':retained_names,
            'newlyPassedMethods':passes,'aggregateIsNotOneExecution':True,
            'historicalFailedCommandRemainsFail':True,'supersededHistoricalPasses':retained_navigation['supersededHistoricalPasses']}
        result['historicalCommands'] = {'retainedFailureGroups':4,'newlyExecutedGroups':7,
            'oldGroupsReprobedOrReplayed':False,'historicalBuildProductsReused':False}
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
        final_deadline = time.monotonic()+120
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
            if retained_navigation is not None:
                assert admit_retained_navigation(base, manifest, guard) == retained_navigation
                result['retainedNavigationEvidenceUnchanged'] = True
            if reused is not None:
                helper.validate_after(reused, guard)
            if fixture_input_admission is not None:
                fixture_input_helper.validate_after(fixture_input_admission,base,guard)
                result['originalSourceFixtureInputsAndCopiesUnchanged']=True
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
                excluded = {name+'.'+method for name,methods in manifest['excludedEarlierMethods'].items() for method in methods}
                native_starts = [name for name in starts if name in excluded]
                result['earlierTestStarts'] = native_starts
                result['earlierTestReplayStatus'] = 'NOT_RUN' if not native_starts else 'UNEXPECTED_COMPONENT_START'
                assert not native_starts, 'unexpected earlier canonical test start in component command'
            reason = observe()
            if reason is not None:
                raise RuntimeError(reason)
            assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['commands'])
            if result['status'] == 'PASS':
                assert len(result['commands']) == 7 and result['actualMethods']['total'] == 3
                assert result['qualifiedMethods']['total'] == 26 and result['qualifiedMethods']['retained'] == 23
                assert result['retainedNavigationEvidenceUnchanged'] is True
                assert result['httpFixtureQualification']['instances'] == 1
                assert result['httpFixtureQualification']['syntheticWriteCount'] == 1
                assert result['httpFixtureQualification']['POSTCount'] == 1
                assert result['httpFixtureQualification']['PATCHCount'] == 0
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-lifecycle-and-budget', 'type':type(error).__name__, 'message':str(error)})
        try:
            result['seconds'] = round(time.monotonic()-started_at,3)
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-time-observation','type':type(error).__name__,'message':str(error)})
            result['seconds'] = None
        result['declaredControlledOutputBytesOnRoot'] = 0
        result['noGlobalRootWriteAuditClaim'] = True
        result['ownedOutputCreated'] = owned_output
        if owned_output:
            save(output/'result.json', result)
    print(json.dumps({'status':result['status'], 'receipt':str(output/'result.json') if owned_output else None,
                      'sha256':base.sha(output/'result.json') if owned_output else None,
                      'seconds':result['seconds'],'errors':result['errors']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
