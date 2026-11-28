#!/usr/bin/env python3
"""Separate source semantic cohort. No object, linker, XCTest or native execution.

The exact 131-file source graph and unchanged C3 Crypto admission are required.
All outputs stay in one newly owned /run tmpfs directory. This controller does
not change or satisfy any C20, Native97, Swift23 or application runtime gate.
"""
from pathlib import Path
import argparse
import ast
import datetime
import gzip
import hashlib
import json
import os
import re
import resource
import shutil
import signal
import stat
import sys
import time
import types
import zlib

MIB = 1024 * 1024
GIB = 1024 * MIB
OUTPUT = Path('/run/pinkha-e-swift-semantic131-20261128-attempt1')
TMPFS = Path('/run')
PREPARED = Path('/run/pinkha-e-swift-semantic131-20261128-prepared1')
C25 = Path('/mnt/development/projects/evidence/pinkha-original-type-runtime-provider25-20261127/prepared3')
CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
FRONTEND = TOOLCHAIN/'swift-frontend'
FRONTEND_BYTES = 208647456
FRONTEND_SHA = 'd98470fed50d4efc0075bcbd45ba1f908382dc9222c2b8213d1ff074efaa2083'
GRAPH_SHA = '748a0eb40a29a79198bbc396e7fb03061f7be1988a0259b670a76aeeeddb3597'
GRAPH_BYTES = 134037
CRYPTO_SHA = '9ec68e6db7ad722866236ab4494df3108fee60791a40a8d218c93a82d817805b'
SHARED_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
OWNER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HEADERS_SHA = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
CUSTODY_SHA = 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
LIFECYCLE = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
C3_COMMANDS = Path('/mnt/development/projects/evidence/pinkha-c-crypto-producer-20261127/observation3/result.json')
C3_COMMANDS_SHA = 'd93433b85ab53b941cde27af52d3612d21b2a93af3d5e838cff2126607f3af17'
C3_TASKS = PHYSICAL_CACHE/'out/Intermediates.noindex/XCBuildData/5f7ca1648219fca76b90928b9f530d1c2abba148c97b5a0410cbc00a30066ae3.xcbuilddata/task-store.msgpack'
C3_TASKS_SHA = '81dd4476f78ae077df1198d266910c2e570a7d364e5eb9ed965dbfb638e1257d'
STOP = {signal.SIGTERM, signal.SIGINT}
TARGETS = [
    ('TorahInspectorCore', [], 8, 52276),
    ('PinkhaKit', ['TorahInspectorCore'], 15, 100185),
    ('PinkhaAnyEngine', [], 14, 143799),
    ('PinkhaAnyIntegration', ['PinkhaKit', 'PinkhaAnyEngine'], 24, 282067),
    ('PinkhaAnyHost', ['PinkhaAnyEngine', 'PinkhaAnyIntegration'], 66, 972248),
]
TEST_TARGET = 'CaptureProducerContractTests'
LIMITS = {
    'wholeOwnedAllocatedBytes': 256*MIB,
    'maximumPreparedControlBytes': 2*MIB,
    'tmpfsFreeReserveBytes': 512*MIB,
    'initialMemAvailableBytes': 3*GIB,
    'liveMemAvailableBytes': GIB,
    'sampledOwnedGroupRSSBytes': GIB,
    'childAddressSpaceBytes': 2*GIB,
    'parentAddressSpaceBytes': 256*MIB,
    'childCPUSeconds': 120,
    'childWallSeconds': 180,
    'childRegularFileBytes': 64*MIB,
    'combinedDiagnosticsBytes': 16*MIB,
    'maximumNamespaceEntries': 4096,
    'maximumNamespaceDepth': 12,
    'maximumClangCacheFiles': 256,
    'maximumClangCacheBytes': 128*MIB,
    'maximumReceiptBytes': 8*MIB,
    'terminalPersistenceReserveBytes': 16*MIB,
    'rootReadOnlyEmergencyReserveBytes': GIB,
    'developmentReadOnlyEmergencyReserveBytes': 512*MIB,
    'mainSeconds': 900,
    'finalSeconds': 120,
    'requiredOuterSeconds': 1080,
    'coreDumpBytes': 0,
}
DRIVER_ALIASES = {
    TOOLCHAIN/'swift': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'swiftc': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'clang': TOOLCHAIN/'clang-21',
    TOOLCHAIN/'clang++': TOOLCHAIN/'clang-21',
}
_save_serial = 0
_owned_identity = None
_output_device = None


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(info, include_atime=True):
    values = (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
              info.st_uid, info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return values + (info.st_atime_ns,) if include_atime else values


def directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)


def physical(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(),
            'exact physical path: '+str(path))
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def own_path(path):
    path = Path(path)
    require(_owned_identity is not None, 'owned output not acquired')
    require(directory_identity(OUTPUT.lstat()) == _owned_identity, 'owned root replaced')
    require(path.is_relative_to(OUTPUT), 'write outside owned output')
    require(path.parent.resolve() == path.parent, 'write through parent alias')
    require(path.parent.stat().st_dev == _output_device, 'write crosses owned device')
    return path


def write_bytes(path, raw, exclusive=True):
    path = own_path(path)
    require(isinstance(raw, bytes) and len(raw) <= 8*MIB, 'bounded evidence/source write')
    flags = os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC
    flags |= os.O_EXCL if exclusive else 0
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            require(count > 0, 'finite write progress')
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    sync_dir(path.parent)


def save(path, value):
    global _save_serial
    path = own_path(path)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    require(len(raw) <= LIMITS['maximumReceiptBytes'], 'bounded structured evidence')
    _save_serial += 1
    pending = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(_save_serial))
    write_bytes(pending, raw)
    os.replace(pending, path)
    sync_dir(path.parent)


class Inputs:
    """NOATIME exact physical reads. Only the original C3 and driver aliases exist."""
    def __init__(self):
        self.alias_admitted = False
        self.originals = {}
        self.guard = lambda: None

    def admit_retained_crypto_alias(self, logical, actual, custody):
        require(logical == CACHE and actual == PHYSICAL_CACHE and custody == CUSTODY_SHA,
                'exact original Crypto alias contract')
        require(CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE),
                'original Crypto symlink target')
        physical(PHYSICAL_CACHE)
        self.alias_admitted = True

    def physical(self, value):
        path = Path(value)
        if path in DRIVER_ALIASES:
            target = DRIVER_ALIASES[path]
            wanted = 'swift-driver' if path.name in ('swift','swiftc') else ('clang' if path.name == 'clang++' else 'clang-21')
            require(path.is_symlink() and os.readlink(path) == wanted, 'original driver alias')
            if path.name == 'clang++':
                require(os.readlink(TOOLCHAIN/'clang') == 'clang-21', 'original clang chain')
            require(path.resolve() == target, 'original physical driver')
            return physical(target)
        if path.is_relative_to(CACHE):
            require(self.alias_admitted, 'Crypto alias used before original admission')
            require(CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE), 'original Crypto alias changed')
            return physical(PHYSICAL_CACHE/path.relative_to(CACHE))
        return physical(path)

    def consume(self, value, maximum, retain=False, destination=None):
        self.guard()
        path = self.physical(value)
        fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                    0 <= before.st_size <= maximum, 'bounded single-link regular input')
            require(identity(path.lstat()) == identity(before), 'input descriptor/path identity')
            digest = hashlib.sha256()
            chunks = [] if retain else None
            total = 0
            while total < before.st_size+1:
                self.guard()
                part = os.read(fd, min(MIB, before.st_size+1-total))
                if not part:
                    break
                total += len(part)
                require(total <= before.st_size and total <= maximum, 'input grew')
                digest.update(part)
                if retain:
                    chunks.append(part)
                if destination is not None:
                    view = memoryview(part)
                    while view:
                        count = os.write(destination, view)
                        require(count > 0, 'input copy progress')
                        view = view[count:]
            require(total == before.st_size, 'input size changed')
            require(identity(os.fstat(fd)) == identity(before) == identity(path.lstat()),
                    'input full nanosecond identity changed')
        finally:
            os.close(fd)
        row = {'bytes':total, 'sha256':digest.hexdigest()}
        if not path.is_relative_to(OUTPUT):
            # Executing the exact frontend may advance only its access time.
            witness = {'identity':list(identity(before, include_atime=path != FRONTEND)),
                       'includeAtime':path != FRONTEND, 'mode':stat.S_IMODE(before.st_mode),
                       **row}
            old = self.originals.get(str(path))
            require(old is None or old == witness, 'original input changed: '+str(path))
            self.originals[str(path)] = witness
        return (row, b''.join(chunks)) if retain else row

    def row(self, path):
        return self.consume(path, 512*MIB)

    def sha(self, path):
        return self.row(path)['sha256']

    def read(self, path, maximum):
        return self.consume(path, maximum, retain=True)[1]

    def pinned(self, path, expected):
        require(re.fullmatch(r'[0-9a-f]{64}', expected) is not None, 'full input digest')
        require(self.sha(path) == expected, 'pinned input changed: '+str(path))

    def copy_exact(self, original, destination, expected):
        destination = own_path(destination)
        fd = os.open(destination, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
        try:
            row = self.consume(original, 8*MIB, destination=fd)
            require(row == expected, 'copied input bytes')
            os.fsync(fd)
        finally:
            os.close(fd)
        sync_dir(destination.parent)
        require(self.row(destination) == expected, 'retained copy bytes')

    def save(self, path, value):
        save(path, value)

    def verify_originals(self):
        initial = dict(self.originals)
        for path, before in initial.items():
            self.guard()
            require(list(identity(Path(path).lstat(), before['includeAtime'])) == before['identity'],
                    'original full identity changed: '+path)
            require(self.row(path) == {key:before[key] for key in ('bytes','sha256')},
                    'original bytes changed: '+path)
        require(self.originals == initial, 'original input membership changed during final audit')


def load_module(path, expected, base, name):
    raw = base.read(path, maximum=256*1024)
    require(hashlib.sha256(raw).hexdigest() == expected, 'exact support body')
    ast.parse(raw)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    base.pinned(path, expected)
    return module


def mem_available():
    with open('/proc/meminfo','r',encoding='ascii') as source:
        raw = source.read(65537)
    require(len(raw) <= 65536, 'bounded memory record')
    matches = re.findall(r'(?m)^MemAvailable:\s+([0-9]+)\s+kB$', raw)
    require(len(matches) == 1, 'exact available memory')
    return int(matches[0])*1024


def tmpfs_mount():
    physical(TMPFS)
    with open('/proc/self/mountinfo','r',encoding='ascii') as source:
        raw = source.read(MIB+1)
    require(len(raw) <= MIB, 'bounded mount metadata')
    rows = []
    for line in raw.splitlines():
        left, sep, right = line.partition(' - ')
        fields = left.split()
        if sep and len(fields) >= 6 and fields[4] == str(TMPFS):
            tail = right.split()
            require(len(tail) >= 3 and tail[0] == 'tmpfs', 'owned output mount must be tmpfs')
            major, minor = map(int, fields[2].split(':'))
            require(TMPFS.stat().st_dev == os.makedev(major,minor), 'exact tmpfs device')
            rows.append({'mountID':int(fields[0]), 'parentMountID':int(fields[1]),
                         'device':TMPFS.stat().st_dev, 'mountPoint':fields[4],
                         'filesystem':tail[0], 'mountOptions':fields[5], 'superOptions':tail[2]})
    require(len(rows) == 1, 'one fixed existing tmpfs mount')
    return rows[0]


def namespace(root, hash_files=False, base=None):
    """Finite owned-only traversal; never follow a descendant alias or mount."""
    rows = {}
    allocated = 0
    started = time.monotonic()
    pending = [(Path(root), 0)]
    while pending:
        path, depth = pending.pop()
        require(depth <= LIMITS['maximumNamespaceDepth'], 'bounded owned namespace depth')
        require(time.monotonic()-started <= 8, 'bounded owned namespace census time')
        try:
            info = path.lstat()
        except FileNotFoundError:
            if hash_files:
                raise
            continue
        require(info.st_dev == _output_device, 'owned namespace crosses device')
        allocated += info.st_blocks*512
        relative = '.' if path == root else str(path.relative_to(root))
        row = {'mode':stat.S_IMODE(info.st_mode), 'allocated':info.st_blocks*512,
               'bytes':info.st_size, 'kind':'directory' if stat.S_ISDIR(info.st_mode) else
               ('file' if stat.S_ISREG(info.st_mode) else 'other')}
        rows[relative] = row
        require(len(rows) <= LIMITS['maximumNamespaceEntries'], 'bounded owned namespace entries')
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as items:
                children = list(items)
            require(len(children) <= LIMITS['maximumNamespaceEntries'], 'bounded directory children')
            pending.extend((Path(item.path),depth+1) for item in reversed(sorted(children,key=lambda item:item.name)))
        else:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    'owned namespace contains nonregular or linked output')
            if hash_files:
                row.update(base.row(path))
    return rows, allocated


def group_sample(row, owned):
    """Only the current unreaped f9 group is observed; closed numeric IDs stay closed."""
    if 'pid' not in row or row['processGroupAbsent']:
        return None
    leader = row['pid']
    members = [leader] + owned.other_group_members(leader)
    require(len(members) <= 8, 'finite current compiler group')
    total = 0
    actual = []
    for pid in members:
        try:
            with open('/proc/'+str(pid)+'/stat','rb') as source:
                raw = source.read(8193)
        except (FileNotFoundError, ProcessLookupError):
            if pid == leader:
                raise RuntimeError('unreaped compiler leader disappeared')
            continue
        require(len(raw) <= 8192, 'bounded owned process identity')
        marker = raw.rfind(b') ')
        require(marker >= 0, 'owned process identity syntax')
        fields = raw[marker+2:].split()
        require(len(fields) >= 22 and int(fields[2]) == leader and int(fields[3]) == leader,
                'current owned group/session identity')
        birth = int(fields[19])
        if pid == leader:
            previous = row.get('resourceLeaderStartTicks')
            require(previous is None or previous == birth, 'current leader identity changed')
            row['resourceLeaderStartTicks'] = birth
        rss = max(0,int(fields[21])) * os.sysconf('SC_PAGE_SIZE')
        total += rss
        actual.append({'pid':pid,'startTicks':birth,'rssBytes':rss})
    row['maximumSampledGroupRSSBytes'] = max(row.get('maximumSampledGroupRSSBytes',0),total)
    row['maximumSampledGroupMembers'] = max(row.get('maximumSampledGroupMembers',0),len(actual))
    # Direct frontend work requests neither a compiler plugin nor another command.
    require(len(actual) <= 1, 'unplanned descendant of direct semantic frontend')
    return total


def raw_record(record, expected=None, maximum=4*MIB):
    require(isinstance(record, dict) and isinstance(record.get('raw'), str), 'whole text record')
    raw = record['raw'].encode()
    require(len(raw) <= maximum and len(raw) == record['bytes'] and
            hashlib.sha256(raw).hexdigest() == record['sha256'], 'whole source record digest')
    if expected is not None:
        require(record['sha256'] == expected, 'required whole source record')
    return raw


def admit_packet(packet):
    require(packet['schema'] == 'pinkha-semantic131-source-packet-v1', 'source packet version')
    graph_raw = raw_record(packet['graph'], GRAPH_SHA, 256*1024)
    require(len(graph_raw) == GRAPH_BYTES, 'complete frozen graph')
    graph = json.loads(graph_raw)
    expected_counts = {'wholeSwiftFiles':131, 'productionFiles':127, 'testFiles':4,
                       'selectedNewMethods':20, 'sourceBytes':1652921,
                       'productionSourceBytes':1550575, 'testSourceBytes':102346,
                       'oldMethodEventsReused':0, 'oldCompiledProductsReused':0,
                       'nativeAccounts':0, 'nativeHTTPRequests':0}
    require(all(graph['counts'][key] == value for key,value in expected_counts.items()), 'exact131 graph counts')
    require(graph['runnerRequirements']['coreDumpLimitBytes'] == 0 and
            graph['runnerRequirements']['sourceOnlyGraphDoesNotAuthorizeExecution'] is True,
            'original twenty-method runtime contract remains separate')
    require(packet['limits'] == LIMITS, 'fixed separate semantic policy')
    require(packet['sourceScope'] == {
        'wholeFiles':131,'physicalSourceRows':101,'gitSuppliedSourceRows':30,
        'sourceBytes':1652921,'testsExecuted':0,'privateFixturePayloadsOpened':0,
        'oldProjectProductsReused':0,'nativeCalls':0}, 'exact semantic scope')
    sources = graph['sourceFiles']
    require(len(sources) == 131 and len({row['isolatedPath'] for row in sources}) == 131,
            'full unique source members')
    require(sum(row['bytes'] for row in sources) == 1652921 and
            sum('sourcePath' in row for row in sources) == 101, 'exact physical/source byte partition')
    expected_git = {row['isolatedPath']:row for row in sources if 'sourcePath' not in row}
    require(set(packet['gitSources']) == set(expected_git), 'all thirty supplied sources, no extras')
    for key,row in expected_git.items():
        raw = raw_record(packet['gitSources'][key], row['sha256'], 128*1024)
        require(len(raw) == row['bytes'] and packet['gitSources'][key]['origin'] == row['sourcePin'],
                'full Git source provenance')
    targets = {name:(count,size) for name,_deps,count,size in TARGETS}
    targets[TEST_TARGET] = (4,102346)
    require({row['target'] for row in sources} == set(targets), 'six module identities')
    for name,(count,size) in targets.items():
        members = [row for row in sources if row['target'] == name]
        require(len(members) == count and sum(row['bytes'] for row in members) == size,
                'full target membership '+name)
        for row in members:
            path = Path(row['isolatedPath'])
            require(row['compile'] is True and not path.is_absolute() and len(path.parts) == 3 and
                    '..' not in path.parts and path.parts[1] == name and path.suffix == '.swift',
                    'closed isolated Swift path')
            require(path.parts[0] == ('Tests' if name == TEST_TARGET else 'Sources'), 'source target partition')
    require(packet['helpers'] == {
        'qualify_provider_crypto_c3.py':CRYPTO_SHA,
        'qualify_current_c3_crypto.py':SHARED_SHA,
        'owned_swift_commands.py':OWNER_SHA,
        'crypto-header-source-manifest.json':HEADERS_SHA}, 'unchanged exact helpers')
    commands = json.loads(raw_record(packet['projectCommandObservation'],
        '170bca7e5fb10e2a6e43d481f15b2b81f6e51c47c0bf40101252f3711b398e17',64*1024))
    require(commands['schema'] == 'pinkha-retained-c3-product-argv-observation-v1' and
            commands['compilerInvocations'] == commands['nativeCalls'] == 0 and commands['absent'] == [],
            'retained project command observation, not new execution')
    require(set(commands['observed']) == {item[0] for item in TARGETS}, 'all five retained project commands')
    require(commands['input']['sha256'] == C3_TASKS_SHA and commands['input']['bytes'] == 3017541,
            'retained task-store binding')
    require(commands['headerManifest']['sha256'] == HEADERS_SHA, 'header provenance join')
    for name,row in commands['observed'].items():
        argv = row['argv']
        require(row['identicalOccurrences'] == 2 and argv[0:3] == ['builtin-SwiftDriver','--',str(TOOLCHAIN/'swiftc')],
                'retained command owner')
        require(argv[argv.index('-target')+1] == 'aarch64-unknown-linux-gnu' and
                argv[argv.index('-swift-version')+1] == '6' and
                argv[argv.index('-module-name')+1] == name and
                all(flag in argv for flag in ('-parse-as-library','-Onone','-DSWIFT_PACKAGE','-DDEBUG','-DXcode','-enable-testing')),
                'retained target/language/debug convention')
    require(packet['configuration']['scope'] == 'EXPLICIT_SEMANTIC_CONFIGURATION_NOT_SWIFTPM_GENERATED_ARGV_EQUIVALENCE',
            'explicit configuration qualification limit')
    require(packet['configuration']['packageName'] == 'captureproducerproof' and
            packet['configuration']['resourceBundle'] == 'unavailable-in-the-isolated-resource-free-package' and
            packet['configuration']['wholeModuleTypecheckBeforeEachEmission'] is True,
            'fixed resource-free component topology')
    crypto_flags = ['-I',str(OUTPUT/'retained-crypto-imports')]
    for name in ('CCryptoBoringSSL','CCryptoBoringSSLShims'):
        include = OUTPUT/'retained-crypto-headers'/name/'include'
        crypto_flags += ['-Xcc','-fmodule-map-file='+str(include/'module.modulemap'),'-Xcc','-I'+str(include)]
    require(packet['configuration']['compilerImportFlags'] == crypto_flags, 'exact unchanged isolated Crypto import flags')
    phases = []
    for target in [row[0] for row in TARGETS]+[TEST_TARGET]:
        files = sorted(str(OUTPUT/'package'/row['isolatedPath']) for row in sources if row['target'] == target)
        for mode in (('typecheck',) if target == TEST_TARGET else ('typecheck','emit-module')):
            label = str(len(phases)+1).zfill(2)+'-'+target+'-'+mode
            phases.append({'label':label,'mode':mode,'target':target,'files':files,
                           'argv':frontend_arguments(target,mode,files,crypto_flags)})
    require(len(phases) == 11 and packet['plannedPhases'] == phases, 'all eleven exact frontend argv before output')
    return graph, graph_raw


def admit_owner_lifecycle(base):
    base.pinned(LIFECYCLE,LIFECYCLE_SHA)
    previous = json.loads(base.read(LIFECYCLE,maximum=MIB))
    require(previous['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and
            previous['helperSHA256'] == OWNER_SHA and previous['allOwnedGroupsPositivelyAbsent'] is True,
            'original f9 process ownership controls')
    require(len(previous['methods']) == len(previous['commands']) == 5 and
            {row['name'] for row in previous['methods']} ==
            {'normal','started-journal-failure','leader-exits-with-descendant','controller-SIGTERM','controller-SIGINT'},
            'exact five retained lifecycle controls')
    require(all(row['status'] == 'PASS' and row['groupPositivelyAbsent'] for row in previous['methods']) and
            all(row['processGroupAbsent'] for row in previous['commands']) and
            previous['compilerInvocations'] == previous['nativeInvocations'] == 0,
            'retained owner closure; no replay')
    return {'path':str(LIFECYCLE),'sha256':LIFECYCLE_SHA,'newControlRuns':0}


def copy_sources(graph, packet, base, guard):
    copies = {}
    external = {}
    root = OUTPUT/'package'
    for row in sorted(graph['sourceFiles'],key=lambda item:item['isolatedPath']):
        guard()
        target = root/row['isolatedPath']
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        expected = {key:row[key] for key in ('bytes','sha256')}
        if 'sourcePath' in row:
            original = physical(Path(row['sourcePath']))
            require(stat.S_IMODE(original.lstat().st_mode) == row['mode'], 'original source mode')
            base.copy_exact(original,target,expected)
            external[str(original)] = dict(expected,mode=row['mode'])
        else:
            original = None
            raw = raw_record(packet['gitSources'][row['isolatedPath']],row['sha256'],128*1024)
            write_bytes(target,raw)
        require(base.row(target) == expected and stat.S_IMODE(target.lstat().st_mode) == 0o600,
                'whole private source copy')
        copies[str(target)] = dict(expected,mode=0o600,target=row['target'],kind=row['kind'],
                                   originalPath=str(original) if original is not None else None)
    require(len(copies) == 131 and len(external) == 101, 'complete source copy census')
    # Old beforeimages remain source provenance; only declared physical rows are read.
    for pair in graph['modifiedProduction']:
        before = pair['before']
        if 'sourcePath' in before:
            path = physical(Path(before['sourcePath']))
            require(stat.S_IMODE(path.lstat().st_mode) == before['mode'] and
                    base.row(path) == {key:before[key] for key in ('bytes','sha256')},
                    'retained source beforeimage')
    return copies,external


def verify_copies(copies, base, guard):
    for name,expected in copies.items():
        guard()
        path = physical(Path(name))
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                stat.S_IMODE(info.st_mode) == expected['mode'], 'retained copy mode/type')
        require(base.row(path) == {key:expected[key] for key in ('bytes','sha256')},
                'retained copy changed: '+name)


def module_members(expected, base):
    root = OUTPUT/'modules'
    actual = {path.name:path for path in root.iterdir()}
    require(set(actual) == {name+'.swiftmodule' for name in expected}, 'only declared new module outputs')
    for name,row in expected.items():
        path = actual[name+'.swiftmodule']
        require(physical(path) == path and stat.S_IMODE(path.lstat().st_mode) == 0o600 and
                base.row(path) == row, 'fresh project module changed')


def frontend_arguments(target, mode, files, crypto_flags):
    require(target in {row[0] for row in TARGETS}|{TEST_TARGET}, 'known semantic module')
    require(mode in ('typecheck','emit-module') and not (target == TEST_TARGET and mode != 'typecheck'),
            'only full semantic or production module emission')
    args = [str(FRONTEND),'-'+mode,'-parse-as-library','-module-name',target,
            '-target','aarch64-unknown-linux-gnu','-swift-version','6','-Onone',
            '-enable-testing','-D','SWIFT_PACKAGE','-D','DEBUG','-D','Xcode',
            '-D','SWIFT_MODULE_RESOURCE_BUNDLE_UNAVAILABLE',
            '-package-name','captureproducerproof',
            '-enable-experimental-feature','DebugDescriptionMacro',
            '-disable-implicit-swift-modules',
            '-module-cache-path',str(OUTPUT/'clang-module-cache'),
            '-clang-scanner-module-cache-path',str(OUTPUT/'clang-module-cache'),
            '-I',str(OUTPUT/'modules'),*crypto_flags,
            '-Xcc','-DSWIFT_PACKAGE','-Xcc','-DDEBUG=1',
            '-Xcc','-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG',
            '-no-color-diagnostics','-num-threads','1']
    if mode == 'emit-module':
        args += ['-o',str(OUTPUT/'modules'/(target+'.swiftmodule'))]
    args += files
    require(files and len(files) == len(set(files)) and all(
        Path(name).is_relative_to(OUTPUT/'package') and name.endswith('.swift') for name in files),
        'whole module source argv')
    forbidden = ('-c','-emit-object','-emit-ir','-emit-bc','-emit-sil','-emit-silgen',
                 '-emit-module-interface','-emit-module-interface-path','-emit-module-doc-path',
                 '-emit-module-source-info-path','-emit-objc-header','-emit-dependencies',
                 '-emit-reference-dependencies','-serialize-diagnostics','-index-store-path',
                 '-experimental-skip-all-function-bodies','-experimental-lazy-typecheck',
                 '-experimental-skip-non-inlinable-function-bodies',
                 '-experimental-skip-non-inlinable-function-bodies-without-types',
                 '-primary-file','-suppress-warnings','-external-plugin-path','-load-plugin-library',
                 '-disable-testable-attr-requires-testable-module','-experimental-allow-module-with-compiler-errors')
    require(not any(token == bad or token.startswith(bad+'=') for token in args for bad in forbidden),
            'forbidden code generation, skip, old import or plugin option')
    return args


def closed_artifacts(base, expected_modules, allowed_copies, completed_labels):
    rows,used = namespace(OUTPUT,hash_files=True,base=base)
    require(used <= LIMITS['wholeOwnedAllocatedBytes'], 'whole output cap')
    expected_fixed = {'controller.py','source-packet.json','SOURCE_GRAPH.json',
                      'source-inputs.json','retained-dependency-products.json','result.json',
                      'semantic-decision.json'}
    support = {'support/'+name for name in ('qualify_provider_crypto_c3.py','qualify_current_c3_crypto.py',
                                            'owned_swift_commands.py','crypto-header-source-manifest.json')}
    copied = {str(Path(name).relative_to(OUTPUT)) for name in allowed_copies}
    modules = {'modules/'+name+'.swiftmodule' for name in expected_modules}
    commands = {'commands/'+label+'/'+leaf for label in completed_labels
                for leaf in ('started.json','original.log','result.json')}
    permitted = expected_fixed|support|copied|modules|commands
    cache_files = 0
    cache_bytes = 0
    for relative,row in rows.items():
        if row['kind'] == 'directory':
            require(row['mode'] == 0o700, 'private owned directory mode')
            continue
        require(row['mode'] == 0o600, 'private owned output mode')
        if relative.startswith('clang-module-cache/'):
            parts = Path(relative).parts
            require(len(parts) <= 3 and
                    (parts[-1].endswith('.pcm') or parts[-1] in ('modules.idx','modules.timestamp')),
                    'only bounded final Clang PCM/cache metadata')
            cache_files += 1
            cache_bytes += row['bytes']
            require(row['bytes'] <= LIMITS['childRegularFileBytes'], 'bounded Clang cache file')
        else:
            require(relative in permitted, 'undeclared closed artifact: '+relative)
    require(permitted <= {name for name,row in rows.items() if row['kind'] == 'file'},
            'all declared final source/control/module/log files retained')
    require(cache_files <= LIMITS['maximumClangCacheFiles'] and
            cache_bytes <= LIMITS['maximumClangCacheBytes'], 'bounded Clang cache closure')
    require(not any(path.startswith(('home/','temporary/','cache-home/','config-home/')) and row['kind'] != 'directory'
                    for path,row in rows.items()), 'no unclassified temporary/home cache outputs')
    return rows,used


def archive_artifacts(rows, base, guard, prepared_allocated, partial_failure=False):
    """One deterministic gzip stream and a complete offset/hash manifest; no deletion."""
    excluded = {'result.json'}
    members = [(name,row) for name,row in sorted(rows.items()) if row['kind'] == 'file' and name not in excluded]
    offset = 0
    entries = []
    for name,row in members:
        entries.append({'relativePath':name,'bytes':row['bytes'],'sha256':row['sha256'],
                        'mode':row['mode'],'offset':offset})
        offset += row['bytes']
    # A conservative DEFLATE bound is an admission, never predicted compression credit.
    worst = offset + ((offset+16382)//16383)*5 + 65536
    _,current = namespace(OUTPUT)
    require(current+prepared_allocated+worst+LIMITS['terminalPersistenceReserveBytes'] <= LIMITS['wholeOwnedAllocatedBytes'],
            'archive transient does not fit the same whole-owned cap')
    archive_dir = OUTPUT/'archive'
    archive_dir.mkdir(mode=0o700)
    sync_dir(OUTPUT)
    manifest = {'schema':'pinkha-semantic-offset-archive-v1','format':'gzip of concatenated exact file bytes',
                'sourceRows':entries,'fileCount':len(entries),'uncompressedBytes':offset,
                'originalOutputsRemoved':False,'portableMetadataRestorationClaimed':False,
                'partialFailureOutputs':partial_failure}
    save(archive_dir/'manifest.json',manifest)
    target = archive_dir/'content.bin.gz'
    fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb',buffering=0) as sink:
        with gzip.GzipFile(filename='',fileobj=sink,mode='wb',compresslevel=6,mtime=0) as packed:
            for entry in entries:
                guard()
                path = OUTPUT/entry['relativePath']
                before = path.lstat()
                raw_fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
                digest = hashlib.sha256()
                length = 0
                try:
                    require(identity(os.fstat(raw_fd)) == identity(before), 'archive descriptor identity')
                    while length < entry['bytes']+1:
                        guard()
                        part = os.read(raw_fd,min(MIB,entry['bytes']+1-length))
                        if not part:
                            break
                        length += len(part)
                        require(length <= entry['bytes'], 'archive input grew')
                        digest.update(part)
                        packed.write(part)
                    require(length == entry['bytes'] and digest.hexdigest() == entry['sha256'] and
                            identity(os.fstat(raw_fd)) == identity(before) == identity(path.lstat()),
                            'archive full input mismatch')
                finally:
                    os.close(raw_fd)
        os.fsync(sink.fileno())
    sync_dir(archive_dir)
    packed_row = base.row(target)
    require(packed_row['bytes'] <= worst, 'conservative archive output bound')
    decoder = zlib.decompressobj(31)
    index = 0
    entry_bytes = 0
    digest = hashlib.sha256()
    total = 0
    def accept(chunk):
        nonlocal index,entry_bytes,digest,total
        start = 0
        while start < len(chunk):
            require(index < len(entries), 'archive inverse extra bytes')
            entry = entries[index]
            amount = min(len(chunk)-start,entry['bytes']-entry_bytes)
            if amount:
                digest.update(chunk[start:start+amount])
                entry_bytes += amount
                total += amount
                start += amount
            if entry_bytes == entry['bytes']:
                require(digest.hexdigest() == entry['sha256'], 'archive full inverse hash')
                index += 1
                entry_bytes = 0
                digest = hashlib.sha256()
    archive_fd = os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    compressed_read = 0
    archive_before = os.fstat(archive_fd)
    try:
        require(archive_before.st_size == packed_row['bytes'], 'archive inverse initial size')
        while compressed_read < packed_row['bytes']+1:
            guard()
            part = os.read(archive_fd,min(128*1024,packed_row['bytes']+1-compressed_read))
            if not part:
                break
            compressed_read += len(part)
            require(compressed_read <= packed_row['bytes'], 'archive inverse input grew')
            require(not decoder.eof, 'no concatenated gzip members')
            pending = part
            while pending:
                guard()
                chunk = decoder.decompress(pending,128*1024)
                pending = decoder.unconsumed_tail
                accept(chunk)
                require(total <= offset, 'bounded archive inverse')
            require(not decoder.unused_data, 'no gzip trailing data')
        require(compressed_read == packed_row['bytes'] and
                identity(os.fstat(archive_fd)) == identity(archive_before) == identity(target.lstat()),
                'archive inverse descriptor/path changed')
        # Every gzip byte was consumed with a bounded output slice; no unbounded flush allocation.
        require(decoder.eof, 'complete gzip trailer before inverse finish')
    finally:
        os.close(archive_fd)
    # Empty log files can legitimately occur between or after nonempty members.
    while index < len(entries) and entries[index]['bytes'] == 0:
        require(entries[index]['sha256'] == hashlib.sha256(b'').hexdigest(), 'empty archive member')
        index += 1
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail and
            total == offset and index == len(entries) and entry_bytes == 0,
            'complete sole-member archive inverse')
    require(base.row(target) == packed_row, 'archive changed after inverse')
    return {'archive':{'path':str(target),**packed_row},
            'manifest':{'path':str(archive_dir/'manifest.json'),**base.row(archive_dir/'manifest.json')},
            'fileCount':len(entries),'uncompressedBytes':offset,'completeInverseVerified':True,
            'originalOutputsRetained':True,'durableOffTmpfsCopyClaimed':False,
            'partialFailureOutputs':partial_failure}


def prepared_controls():
    physical(PREPARED)
    info = PREPARED.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid() and
            stat.S_IMODE(info.st_mode) == 0o700 and info.st_dev == TMPFS.stat().st_dev,
            'physical private prepared tmpfs namespace')
    fd = os.open(PREPARED,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        with os.scandir(fd) as scan:
            names = sorted(item.name for item in scan)
    finally:
        os.close(fd)
    require(names == ['qualify_semantic131.py','source-packet.json'], 'exact two prepared controls')
    total = info.st_blocks*512
    witnesses = {}
    for name in names:
        path = PREPARED/name
        before = path.lstat()
        require(path.resolve() == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_uid == os.geteuid() and stat.S_IMODE(before.st_mode) == 0o600 and
                before.st_dev == info.st_dev, 'prepared control identity')
        total += before.st_blocks*512
        witnesses[name] = list(identity(before))
    require(total <= LIMITS['maximumPreparedControlBytes'], 'bounded source-preparation allocation')
    return {'directoryIdentity':list(identity(info)),'files':witnesses,'allocatedBytes':total}


def admit_capability(packet):
    actual_raw = raw_record(packet['capabilityObservation'],
        '12645f41c87fc66c9066165be80d9cd50b35a316aceeb2308a6ffa9477c20d19',64*1024)
    actual = json.loads(actual_raw)
    require(actual['schema'] == 'pinkha-installed-frontend-help-observation-v1' and
            actual['status'] == 'PASS_FRONTEND_HELP_OBSERVATION' and actual['errors'] == [] and
            actual['frontendUnchanged'] is True and len(actual['commands']) == 1,
            'actual installed frontend help observation')
    previous = actual['commands'][0]
    require(previous['command'] == [str(FRONTEND),'-help'] and previous['exitCode'] == 0 and
            previous['processGroupAbsent'] is True and previous['reaped'] is True and
            previous['forcedCleanup'] is False and previous['cleanupErrors'] == previous['signals'] == [] and
            previous['diagnosticsComplete'] is True and previous['stderr'] == '',
            'actual help command closed without new semantic evidence')
    help_raw = previous['stdout'].encode()
    require(len(help_raw) == 37141 and hashlib.sha256(help_raw).hexdigest() ==
            '2c6c42af8588c519e10482034565861d2a427e195dc75ed9a3405e438a4f67f0',
            'entire installed help bytes')
    for flag in ('-typecheck','-emit-module','-parse-as-library','-module-name','-target',
                 '-package-name','-module-cache-path','-disable-implicit-swift-modules',
                 '-clang-scanner-module-cache-path',
                 '-num-threads','-no-color-diagnostics','-enable-experimental-feature'):
        require(re.search(r'(?m)^  '+re.escape(flag)+r'(?:\s|$)',previous['stdout']) is not None,
                'installed public frontend option '+flag)
    tool = actual['toolchain']
    require(tool['path'] == str(FRONTEND) and tool['bytes'] == FRONTEND_BYTES and
            tool['sha256'] == FRONTEND_SHA and tool['mode'] == 0o755 and
            tool['notWholeToolchainAdmission'] is True, 'exact observed frontend only')
    return {'observationSHA256':packet['capabilityObservation']['sha256'],
            'helpSHA256':hashlib.sha256(help_raw).hexdigest(),'newHelpRuns':0,
            'sourceParsingOrSemanticClaimFromHelp':False,
            'hiddenSwiftVersionTestingOptionsBoundSeparatelyToRetainedProjectArgv':True}


def main():
    global _owned_identity, _output_device
    require(not sys.flags.optimize, 'assertions may not be disabled')
    sys.dont_write_bytecode = True
    os.umask(0o077)
    started = time.monotonic()
    main_deadline = started + LIMITS['mainSeconds']
    final_deadline = None
    owned_output = False
    preparation = None
    packet = None
    graph = None
    base = Inputs()
    owned = None
    helper = None
    reused = None
    copies = {}
    source_copies = {}
    module_outputs = {}
    labels = []
    last_scan = 0.0
    source_admitted = False
    final_inputs_ok = False
    archive = None
    result = {
        'schema':'pinkha-separate-swift-semantic131-v1',
        'status':'RUNNING',
        'startedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope':'Full-body source semantic checks and five fresh importable modules; no object, link, test or native mode',
        'sourceGraphSHA256':GRAPH_SHA,'limits':LIMITS,
        'errors':[],'completionErrors':[],'commands':[],'phases':[],
        'plannedFrontendCommands':11,'completedFullBodyTypechecks':[],
        'completedModuleOnlyEmissions':[],'testMethodsStarted':0,'testMethodsPassed':0,
        'testInvocations':0,'linkInvocations':0,'objectGenerationInvocations':0,
        'nativeInvocations':0,'accountOpens':0,'privateFixturePayloadsOpened':0,
        'oldProjectProductsImported':0,'oldLifecycleControlsReplayed':0,
        'C20OrNativeControllerDispatched':False,'C20AndNativeResourcePoliciesChanged':False,
        'currentApplicationGraphEquivalenceClaimed':False,
        'globalFilesystemWriteAuditClaimed':False,
        'sampledRSSIsNotContinuousPeakProof':True,
        'sampledAllocationIsNotFilesystemQuota':True,
        'systemToolchainResourceFilesIndividuallyPinned':False,
        'standardLibraryImportScope':'Installed frontend default toolchain imports; no independent whole SDK/resource-file closure claim',
        'ownedOutputsRemoved':False,'durableOffTmpfsCopyClaimed':False,
        'sourceUnchanged':False,'originalCryptoAdmissionUnchanged':False,
        'allStartedOwnedGroupsPositivelyAbsent':False,
        'terminalReceiptQualified':False,
    }

    def interrupted(number,_frame):
        raise RuntimeError('semantic cohort interrupted by signal '+str(number))

    for number in STOP:
        signal.signal(number,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,STOP)

    def observe():
        nonlocal last_scan
        try:
            now = time.monotonic()
            if final_deadline is None and now >= main_deadline:
                return 'finite semantic main deadline'
            if final_deadline is not None and now >= final_deadline:
                return 'finite semantic finalization deadline'
            root_free = shutil.disk_usage('/').free
            dev_free = shutil.disk_usage('/mnt/development').free
            tmp_free = shutil.disk_usage(TMPFS).free
            memory = mem_available()
            for name,value in (('Root',root_free),('Development',dev_free),('Tmpfs',tmp_free),('MemAvailable',memory)):
                key = 'minimum'+name+'Bytes'
                result[key] = min(result.get(key,value),value)
            if root_free < LIMITS['rootReadOnlyEmergencyReserveBytes']:
                return 'separate read-only root emergency reserve'
            if dev_free < LIMITS['developmentReadOnlyEmergencyReserveBytes']:
                return 'separate read-only development emergency reserve'
            if tmp_free < LIMITS['tmpfsFreeReserveBytes']:
                return 'tmpfs 512 MiB live free reserve'
            if memory < LIMITS['liveMemAvailableBytes']:
                return 'live MemAvailable 1 GiB floor'
            if owned_output:
                if directory_identity(OUTPUT.lstat()) != _owned_identity:
                    return 'owned semantic namespace replaced'
                if (OUTPUT/'abort').exists():
                    return 'owned semantic abort requested'
                diagnostic_bytes = 0
                for phase in result['phases']:
                    path = OUTPUT/'commands'/phase['label']/'original.log'
                    if path.exists():
                        require(path.resolve() == path and stat.S_ISREG(path.lstat().st_mode), 'physical owned log')
                        diagnostic_bytes += path.lstat().st_size
                result['maximumObservedCombinedDiagnosticBytes'] = max(
                    result.get('maximumObservedCombinedDiagnosticBytes',0),diagnostic_bytes)
                if diagnostic_bytes > LIMITS['combinedDiagnosticsBytes']:
                    return 'combined diagnostic cap'
                if now-last_scan >= 0.5:
                    last_scan = now
                    _rows,allocated = namespace(OUTPUT)
                    allocated += preparation['allocatedBytes']
                    result['maximumObservedWholeOwnedAllocatedBytes'] = max(
                        result.get('maximumObservedWholeOwnedAllocatedBytes',0),allocated)
                    if allocated+LIMITS['terminalPersistenceReserveBytes'] > LIMITS['wholeOwnedAllocatedBytes']:
                        return 'whole prepared-plus-output cap with terminal persistence reserve'
            if owned is not None and result['commands']:
                current = result['commands'][-1]
                if 'pid' in current and not current['processGroupAbsent']:
                    amount = group_sample(current,owned)
                    if amount is not None and amount > LIMITS['sampledOwnedGroupRSSBytes']:
                        return 'sampled current compiler group RSS cap'
        except BaseException as error:
            return 'resource observation failed: '+type(error).__name__+': '+str(error)
        return None

    def guard():
        reason = observe()
        if reason is not None:
            raise RuntimeError(reason)

    def command(label,argv,mode,target,files,env):
        require(not result['commands'] or result['commands'][-1].get('processGroupAbsent') is True,
                'previous exact group must be positively closed before another frontend')
        index = len(result['commands'])
        require(packet['plannedPhases'][index] == {'label':label,'mode':mode,'target':target,
                'files':files,'argv':argv}, 'exact reviewed semantic phase before spawn')
        phase = {'label':label,'commandIndex':index,'mode':mode,'target':target,
                 'sourceFiles':files,'sourceCount':len(files),'normalCompletion':False}
        result['phases'].append(phase)
        log,row = owned.run(OUTPUT/'commands'/label,argv,OUTPUT/'package',env,
                            LIMITS['childWallSeconds'],observe,save,base.sha,result['commands'])
        require(row is result['commands'][index] and row['argv'] == argv and
                row['cwd'] == str(OUTPUT/'package') and row['exitCode'] == 0 and
                row['processGroupAbsent'] and not row['forcedCleanup'] and
                row['signals'] == row['cleanupErrors'] == [],
                'exact normal semantic command closure')
        phase['normalCompletion'] = True
        phase['log'] = {'path':str(log),**base.row(log)}
        labels.append(label)
        save(OUTPUT/'result.json',result)

    def final_check():
        nonlocal final_inputs_ok
        guard()
        require(prepared_controls() == preparation,'prepared source namespace changed')
        base.verify_originals()
        if copies:
            verify_copies(copies,base,guard)
        if reused is not None:
            require(helper is not None, 'retained original Crypto verifier')
            helper.validate_after(reused,guard)
            for name,expected in reused['immutableInputs'].items():
                guard()
                require(base.row(name) == expected,'original Crypto input changed')
            result['originalCryptoAdmissionUnchanged'] = True
        if owned_output and (OUTPUT/'modules').is_dir():
            module_members(module_outputs,base)
        require(tmpfs_mount() == result['tmpfsMount'],'tmpfs mount identity changed')
        require(prepared_controls() == preparation,'prepared controls changed through final audit')
        result['sourceUnchanged'] = source_admitted
        result['allStartedOwnedGroupsPositivelyAbsent'] = all(
            row.get('processGroupAbsent') is True for row in result['commands'] if 'pid' in row)
        require(result['allStartedOwnedGroupsPositivelyAbsent'],'unresolved current owned group')
        guard()
        final_inputs_ok = True

    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--self-sha',required=True)
        parser.add_argument('--packet-sha',required=True)
        args = parser.parse_args()
        require(all(re.fullmatch(r'[0-9a-f]{64}',value) is not None
                    for value in (args.self_sha,args.packet_sha)),'caller-pinned full controls')
        require(Path(__file__) == PREPARED/'qualify_semantic131.py','one declared prepared entrypoint')
        result['controllerSHA256'] = args.self_sha
        result['sourcePacketSHA256'] = args.packet_sha
        result['output'] = str(OUTPUT)
        result['tmpfsMount'] = tmpfs_mount()
        preparation = prepared_controls()
        result['preparedNamespace'] = preparation
        require(not OUTPUT.exists() and not OUTPUT.is_symlink(),'fresh exclusive output namespace')
        base.pinned(Path(__file__),args.self_sha)
        self_raw = base.read(Path(__file__),maximum=256*1024)
        packet_path = PREPARED/'source-packet.json'
        packet_raw = base.read(packet_path,maximum=2*MIB)
        require(hashlib.sha256(packet_raw).hexdigest() == args.packet_sha,'caller-pinned packet bytes')
        packet = json.loads(packet_raw)
        graph,graph_raw = admit_packet(packet)
        result['configuration'] = packet['configuration']
        result['capabilityAdmission'] = admit_capability(packet)
        result['ownerAdmission'] = admit_owner_lifecycle(base)
        result['sourceCounts'] = {'wholeFiles':131,'productionFiles':127,'testFiles':4,
                                  'physicalSourceRows':101,'gitSuppliedRows':30,'sourceBytes':1652921,
                                  'twentyRuntimeMethodsRemainNotRun':True}
        for name,expected in packet['helpers'].items():
            base.pinned(C25/name,expected)
        base.pinned(C3_COMMANDS,C3_COMMANDS_SHA)
        base.pinned(C3_TASKS,C3_TASKS_SHA)
        require(base.row(FRONTEND) == {'bytes':FRONTEND_BYTES,'sha256':FRONTEND_SHA} and
                stat.S_IMODE(FRONTEND.lstat().st_mode) == 0o755,'exact fresh frontend bytes/mode')
        owned = load_module(C25/'owned_swift_commands.py',OWNER_SHA,base,'semantic131_owned_f9')
        owned.install_interrupt_handlers()
        original_child_signals = owned.child_signals

        def child_limits():
            original_child_signals()
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['childRegularFileBytes'],LIMITS['childRegularFileBytes']))
            resource.setrlimit(resource.RLIMIT_AS,(LIMITS['childAddressSpaceBytes'],LIMITS['childAddressSpaceBytes']))
            resource.setrlimit(resource.RLIMIT_CPU,(LIMITS['childCPUSeconds'],LIMITS['childCPUSeconds']))
            resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))

        # Only the f9 child pre-exec signal callback is wrapped with stricter limits.
        # f9 run(), all unreaped ownership and all cleanup bodies stay exact.
        owned.child_signals = child_limits
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_FSIZE,(256*MIB,256*MIB))
        resource.setrlimit(resource.RLIMIT_AS,(LIMITS['parentAddressSpaceBytes'],LIMITS['childAddressSpaceBytes']))
        resource.setrlimit(resource.RLIMIT_CPU,(LIMITS['mainSeconds']+LIMITS['finalSeconds'],
                                                LIMITS['mainSeconds']+LIMITS['finalSeconds']))
        guard()
        require(shutil.disk_usage(TMPFS).free >= LIMITS['wholeOwnedAllocatedBytes']+LIMITS['tmpfsFreeReserveBytes'],
                'tmpfs 256 MiB whole cap plus 512 MiB admission reserve')
        require(mem_available() >= LIMITS['initialMemAvailableBytes'],'initial 3 GiB available memory')
        mask = signal.pthread_sigmask(signal.SIG_BLOCK,STOP)
        try:
            OUTPUT.mkdir(mode=0o700)
            owned_output = True
            _owned_identity = directory_identity(OUTPUT.lstat())
            _output_device = OUTPUT.lstat().st_dev
            require(_output_device == result['tmpfsMount']['device'],'owned output on exact admitted tmpfs')
            sync_dir(OUTPUT)
            sync_dir(TMPFS)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        save(OUTPUT/'result.json',result)
        for name in ('support','package','modules','commands','clang-module-cache','home','temporary','cache-home','config-home'):
            (OUTPUT/name).mkdir(mode=0o700)
        sync_dir(OUTPUT)
        write_bytes(OUTPUT/'controller.py',self_raw)
        write_bytes(OUTPUT/'source-packet.json',packet_raw)
        write_bytes(OUTPUT/'SOURCE_GRAPH.json',graph_raw)
        for name,expected in packet['helpers'].items():
            original = C25/name
            base.copy_exact(original,OUTPUT/'support'/name,base.row(original))
            require(base.sha(OUTPUT/'support'/name) == expected,'unchanged support copy')
        base.guard = guard
        helper = load_module(OUTPUT/'support/qualify_provider_crypto_c3.py',CRYPTO_SHA,base,'semantic131_crypto')
        reused = helper.qualify(OUTPUT,base,guard)
        result['qualifiedDependencyAdmission'] = {
            'sharedHelperSHA256':SHARED_SHA,'wrapperSHA256':CRYPTO_SHA,
            'receipt':reused['receipt'],'moduleNames':['Crypto','CryptoBoringWrapper'],
            'dependencyCompilerInvocations':0,'linkObjectsUsed':False,
            'ASN1CompiledProductClaimed':False}
        require(reused['producerExactStableToPhysicalMapping'] == {str(CACHE):str(PHYSICAL_CACHE)},
                'original complete C3 admission')
        require(reused['compilerFlags'] == packet['configuration']['compilerImportFlags'],
                'actual unchanged wrapper import flags match every planned phase')
        source_copies,physical_sources = copy_sources(graph,packet,base,guard)
        copies.update(source_copies)
        for name,row in {**reused['copiedModules'],**reused['copiedHeaders']}.items():
            copies[name] = dict(row,mode=0o600)
        copies[reused['receipt']['path']] = {key:reused['receipt'][key] for key in ('bytes','sha256')}
        copies[reused['receipt']['path']]['mode'] = 0o600
        for name,expected in packet['helpers'].items():
            path = OUTPUT/'support'/name
            copies[str(path)] = dict(base.row(path),mode=0o600)
        for name in ('controller.py','source-packet.json','SOURCE_GRAPH.json'):
            copies[str(OUTPUT/name)] = dict(base.row(OUTPUT/name),mode=0o600)
        source_admitted = True
        save(OUTPUT/'source-inputs.json',{
            'graphSHA256':GRAPH_SHA,'completeSourceCopies':source_copies,
            'physicalSourceRows':physical_sources,'originalInputsBefore':base.originals,
            'qualifiedCryptoReceipt':reused['receipt'],
            'all131FullFiles':True,'privateFixturePayloadsOpened':0})
        copies[str(OUTPUT/'source-inputs.json')] = dict(base.row(OUTPUT/'source-inputs.json'),mode=0o600)
        env = {'PATH':str(TOOLCHAIN)+':/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8','TZ':'UTC',
               'HOME':str(OUTPUT/'home'),'TMPDIR':str(OUTPUT/'temporary'),
               'TMP':str(OUTPUT/'temporary'),'TEMP':str(OUTPUT/'temporary'),
               'XDG_CACHE_HOME':str(OUTPUT/'cache-home'),'XDG_CONFIG_HOME':str(OUTPUT/'config-home'),
               'CLANG_MODULE_CACHE_PATH':str(OUTPUT/'clang-module-cache'),
               'SWIFT_BACKTRACE':'enable=no'}
        result['environment'] = env
        result['commandPlan'] = []
        for target,deps,count,_size in TARGETS:
            files = sorted(name for name,row in source_copies.items() if row['target'] == target)
            require(len(files) == count and set(deps) <= set(module_outputs),'topological whole module admission')
            for mode in ('typecheck','emit-module'):
                guard()
                module_members(module_outputs,base)
                verify_copies(copies,base,guard)
                label = str(len(result['phases'])+1).zfill(2)+'-'+target+'-'+mode
                argv = frontend_arguments(target,mode,files,reused['compilerFlags'])
                result['commandPlan'].append({'label':label,'argv':argv,'mode':mode,'target':target})
                command(label,argv,mode,target,files,env)
                if mode == 'typecheck':
                    module_members(module_outputs,base)
                    result['completedFullBodyTypechecks'].append(target)
                else:
                    path = OUTPUT/'modules'/(target+'.swiftmodule')
                    require(path.is_file() and not path.is_symlink() and
                            0 < path.lstat().st_size <= LIMITS['childRegularFileBytes'],'new importable module output')
                    module_outputs[target] = base.row(path)
                    module_members(module_outputs,base)
                    result['completedModuleOnlyEmissions'].append(target)
                save(OUTPUT/'result.json',result)
        files = sorted(name for name,row in source_copies.items() if row['target'] == TEST_TARGET)
        require(len(files) == 4 and set(module_outputs) == {row[0] for row in TARGETS},'fresh imports before test-source typecheck')
        verify_copies(copies,base,guard)
        label = '11-'+TEST_TARGET+'-typecheck'
        argv = frontend_arguments(TEST_TARGET,'typecheck',files,reused['compilerFlags'])
        result['commandPlan'].append({'label':label,'argv':argv,'mode':'typecheck','target':TEST_TARGET})
        command(label,argv,'typecheck',TEST_TARGET,files,env)
        result['completedFullBodyTypechecks'].append(TEST_TARGET)
        module_members(module_outputs,base)
        require(len(result['commands']) == len(result['phases']) == 11 and
                len(result['completedFullBodyTypechecks']) == 6 and
                len(result['completedModuleOnlyEmissions']) == 5,'all exact semantic phases completed')
        result['moduleOutputs'] = module_outputs
        result['status'] = 'SEMANTIC_PHASES_COMPLETE_PENDING_FINAL_AUDIT'
    except BaseException as error:
        result['status'] = 'FAIL'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in STOP:
            signal.signal(number,signal.SIG_IGN)
        final_deadline = time.monotonic()+LIMITS['finalSeconds']
        signal.signal(signal.SIGALRM,interrupted)
        signal.setitimer(signal.ITIMER_REAL,LIMITS['finalSeconds'])
        base.guard = guard
        if preparation is not None:
            try:
                final_check()
            except BaseException as error:
                result['status'] = 'FAIL'
                result['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        if owned_output:
            try:
                require(directory_identity(OUTPUT.lstat()) == _owned_identity,'owned output before final retention')
                if result['status'] == 'SEMANTIC_PHASES_COMPLETE_PENDING_FINAL_AUDIT' and final_inputs_ok:
                    decision = {key:result[key] for key in (
                        'schema','scope','sourceGraphSHA256','sourceCounts','completedFullBodyTypechecks',
                        'completedModuleOnlyEmissions','sourceUnchanged','originalCryptoAdmissionUnchanged',
                        'allStartedOwnedGroupsPositivelyAbsent','testInvocations','nativeInvocations',
                        'linkInvocations','objectGenerationInvocations')}
                    decision['status'] = 'SOURCE_SEMANTICS_COMPLETE_PENDING_ARCHIVE_AND_TERMINAL_RECEIPT'
                    decision['moduleOutputs'] = module_outputs
                    save(OUTPUT/'semantic-decision.json',decision)
                    rows,_used = closed_artifacts(base,module_outputs,copies,labels)
                    archive = archive_artifacts(rows,base,guard,preparation['allocatedBytes'])
                    result['archive'] = archive
                    # Archive work reads owned files only. Original current inputs are checked once more.
                    base.verify_originals()
                    verify_copies(copies,base,guard)
                    module_members(module_outputs,base)
                    require(prepared_controls() == preparation,'prepared controls after archive')
                    require(tmpfs_mount() == result['tmpfsMount'],'exact tmpfs after archive')
                    guard()
                    result['status'] = 'PASS_SEMANTIC_131_NO_OBJECT_NO_TEST'
                elif final_inputs_ok and result['allStartedOwnedGroupsPositivelyAbsent']:
                    # Failed compiler diagnostics and partial outputs stay attributed to this failure.
                    # Archive only after the same immutable input/f9 closure audit; never promote it.
                    guard()
                    rows,_used = namespace(OUTPUT,hash_files=True,base=base)
                    archive = archive_artifacts(rows,base,guard,preparation['allocatedBytes'],partial_failure=True)
                    result['archive'] = archive
                    base.verify_originals()
                    verify_copies(copies,base,guard)
                    require(prepared_controls() == preparation,'prepared controls after failure archive')
                    guard()
                rows,used = namespace(OUTPUT)
                result['ownedNamespaceBeforeTerminalReceipt'] = rows
                result['wholeOwnedAllocatedBeforeTerminalReceiptBytes'] = used+preparation['allocatedBytes']
                require(result['wholeOwnedAllocatedBeforeTerminalReceiptBytes']+
                        LIMITS['terminalPersistenceReserveBytes'] <= LIMITS['wholeOwnedAllocatedBytes'],
                        'final whole allocation with bounded terminal persistence reserve')
            except BaseException as error:
                result['status'] = 'FAIL'
                result['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        result['endedAtUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result['seconds'] = time.monotonic()-started
        result['startedFrontendCommands'] = sum('pid' in row for row in result['commands'])
        result['allStartedOwnedGroupsPositivelyAbsent'] = all(
            row.get('processGroupAbsent') is True for row in result['commands'] if 'pid' in row)
        terminal_path = None
        terminal_row = None
        whole_allocated_after_terminal = None
        if owned_output:
            try:
                require(directory_identity(OUTPUT.lstat()) == _owned_identity,'owned root before terminal write')
                result['terminalReceiptQualified'] = result['status'] == 'PASS_SEMANTIC_131_NO_OBJECT_NO_TEST'
                save(OUTPUT/'result.json',result)
                # Exact encoded bytes are independent of resource-guard failure.
                encoded = (json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
                base.guard = lambda: None
                terminal_row = base.row(OUTPUT/'result.json')
                require(terminal_row == {'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest()},
                        'exact retained terminal receipt')
                _closed_rows,terminal_used = namespace(OUTPUT)
                whole_allocated_after_terminal = terminal_used+preparation['allocatedBytes']
                require(whole_allocated_after_terminal <= LIMITS['wholeOwnedAllocatedBytes'],
                        'actual whole allocation after terminal receipt')
                guard()
                terminal_path = str(OUTPUT/'result.json')
            except BaseException as error:
                result['status'] = 'FAIL'
                result['terminalReceiptQualified'] = False
                result['completionErrors'].append({'type':type(error).__name__,'message':str(error),
                                                   'phase':'terminal-persistence'})
                terminal_path = None
                terminal_row = None
                try:
                    fallback = {'status':'FAIL_TERMINAL_PERSISTENCE','controllerSHA256':result.get('controllerSHA256'),
                                'errors':result['errors'],'completionErrors':result['completionErrors'],
                                'anyPrimaryReceiptIsUnqualified':True,'ownedOutputsRetained':True,
                                'allStartedOwnedGroupsPositivelyAbsent':result['allStartedOwnedGroupsPositivelyAbsent']}
                    path = OUTPUT/'terminal-persistence-failure.json'
                    require(not path.exists() and not path.is_symlink(),'exclusive persistence failure receipt')
                    write_bytes(path,(json.dumps(fallback,sort_keys=True,indent=2)+'\n').encode())
                    terminal_row = base.row(path)
                    terminal_path = str(path)
                except BaseException as fallback_error:
                    result['completionErrors'].append({'type':type(fallback_error).__name__,'message':str(fallback_error),
                                                       'phase':'fallback-persistence'})
        signal.setitimer(signal.ITIMER_REAL,0)
        summary = {'status':result['status'],'receipt':dict(path=terminal_path,**terminal_row) if terminal_row else None,
                   'sourceGraphSHA256':GRAPH_SHA,'startedFrontendCommands':result['startedFrontendCommands'],
                   'fullBodyTypechecks':result['completedFullBodyTypechecks'],
                   'moduleOnlyEmissions':result['completedModuleOnlyEmissions'],
                   'testInvocations':0,'nativeInvocations':0,'allStartedOwnedGroupsPositivelyAbsent':result['allStartedOwnedGroupsPositivelyAbsent'],
                   'ownedOutputCreated':owned_output,'ownedOutputsRemoved':False,
                   'wholeOwnedAllocatedAfterTerminalReceiptBytes':whole_allocated_after_terminal,
                   'errors':result['errors'],'completionErrors':result['completionErrors'],
                   'terminalReceiptQualified':result['terminalReceiptQualified']}
        print(json.dumps(summary,sort_keys=True),flush=True)
    return 0 if result['status'] == 'PASS_SEMANTIC_131_NO_OBJECT_NO_TEST' and result['terminalReceiptQualified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
