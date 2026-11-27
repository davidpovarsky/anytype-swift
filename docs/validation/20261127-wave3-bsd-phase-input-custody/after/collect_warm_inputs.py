#!/usr/bin/env python3
"""Prepare finite warm-input custody; checked-in plans are inert.

Only fresh owned export/read-only-reader/evidence paths may be written.  This
does not stage main14, materialize the SDK, resolve packages, build or test.
The original 73bb Commands owner is imported only after its whole-byte check.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import stat
import sys
import time

sys.dont_write_bytecode = True
GIB, MIB = 1024 ** 3, 1024 ** 2
LIFECYCLE = '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a'
CENSUS = '229222b72fd01aa515aef502aa8f8c889344f9e4cd60981421f49f53ecf3bd2a'
PHASE_OBSERVER = '75dfe996edc8ffd5eece2efbd6a64238e221a0d4b9e885edaf47d9cebe043826'
SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
SDK_TREE = '89485be6fc9db276c4359726a33b51284835b23b'
SDK_BASE = '38528941720d9b4f2da8dce7afbc788c2e554a0c'
APP_BASE = '8f2c11713fb8a40ae13444104723666ffef68afe'
APP_BASE_TREE = '7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a'
SDK_REPOSITORY = Path('/mnt/development/projects/git-mirrors/hanlin-ai.git')
APP_REPOSITORY = Path('/mnt/development/projects/git-mirrors/anytype-swift.git')
APP_ORACLE_WORKTREE = Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
OLD_SDK_READER = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/hanlin-385289-source.git')
APP_SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
DEVELOPER = '/Applications/Xcode.app/Contents/Developer'
MARKER_SHA = '41445d6e8ea29da6460aeb340f006b7d0eaa7f0fb5a4a805d2c369ff4ef17124'
SOURCE_ROWS_SHA = 'e7a00de30b0a050758b94505f3dc64ac31b575e03683c7369706f99d09f7fcf1'
MARKER_READ_RECEIPT_SHA = 'c0e63788c932788e81786c644dc6ac40e6396eb3e6cd27ddebeaf443903f13a5'
SDK_CLOSURE = 'c967e5488fc12feea85eb5b90a3984dcbff342a3450cfba219f593d06862c7b2'
SDK_PUBLICATION_SHA = 'c9ed7976a67792ec2d3ab3706eadd6a3071276d9f252b1c04f0e4cd01f34bdbd'
MAX_BUNDLE = 512 * MIB
MAX_LOGS = 8 * MIB
EXPORT_REF = {'sdk': 'refs/heads/pinkha-forward-sdk-c0b',
              'app': 'refs/heads/pinkha-forward-app-selected'}
TOOLCHAIN = {'xcode': ['xcodebuild', '-version'],
             'swift': ['xcrun', 'swift', '--version'],
             'simulator-sdk': ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-build-version']}


def require(value, message):
    if not value:
        raise ValueError(message)


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def error(exc):
    return {'type': type(exc).__name__, 'message': str(exc)}


def physical(path, *, exists=True, directory=False):
    path = Path(path)
    require(path.is_absolute() and str(path) == os.path.normpath(str(path)), 'Canonical absolute path required')
    for item in (path, *path.parents):
        require(not item.is_symlink(), 'Symbolic path component refused: ' + str(item))
    if exists:
        require(path.resolve(strict=True) == path and (path.is_dir() if directory else path.is_file()),
                'Original physical input missing: ' + str(path))
    else:
        require(path.parent.resolve(strict=True) == path.parent and not path.exists(), 'Fresh exclusive path required')
    return path


def read(row, maximum=16 * MIB):
    require(set(row) == {'path', 'bytes', 'sha256'}, 'Exact file identity is required')
    path = physical(row['path'])
    require(type(row['bytes']) is int and 0 <= row['bytes'] <= maximum, 'Bounded file size required')
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if sys.platform.startswith('linux'):
        flags |= os.O_NOATIME
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size == row['bytes'], 'Input kind/length differs')
        raw = stream.read(row['bytes'] + 1)
        after = os.fstat(stream.fileno())
    # Access time is not a portable immutability witness on the Mac.
    keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    require(all(getattr(before, k) == getattr(after, k) for k in keys)
            and len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'Input identity/content changed')
    return raw


def file_ref(path, maximum=MAX_BUNDLE):
    path = physical(path)
    before = path.stat()
    require(before.st_size <= maximum, 'Owned output exceeds its finite envelope')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            'Owned output changed while hashing')
    return {'path': str(path), 'bytes': before.st_size, 'sha256': digest}


def write(path, value):
    path = physical(path, exists=False)
    raw = value if isinstance(value, bytes) else encode(value)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    row = file_ref(path)
    require(row['bytes'] == len(raw) and row['sha256'] == sha(raw), 'Exclusive output readback differs')
    return row


def load(row, name, expected):
    require(row['sha256'] == expected, 'Original control pin differs: ' + name)
    read(row)
    spec = importlib.util.spec_from_file_location('warm_input_original_' + name, row['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resources(root, role):
    # These are input-custody envelopes, not the unchanged 8.5 GiB App gate.
    growth = 576 * MIB if role.startswith('export-') else (640 * MIB if role == 'receive-sdk' else 8 * MIB)
    result = {}
    if sys.platform.startswith('linux'):
        scopes = [('root', Path('/'), 2 * GIB, 64 * MIB),
                  ('development', root.parent, 512 * MIB, growth)]
    else:
        scopes = [('data', Path('/System/Volumes/Data'), 2 * GIB, growth)]
    for name, path, floor, allowance in scopes:
        st = os.statvfs(path)
        available = st.f_bavail * st.f_frsize
        result[name] = {'path': str(path), 'freeBytes': available, 'floorBytes': floor,
                        'ownedGrowthAllowanceBytes': allowance}
        require(available >= floor + allowance, 'Original live floor plus finite input allowance unavailable: ' + name)
    return result


class OriginalOutcomeWrites:
    """Preserve a real earlier outcome if this isolated owner's receipt write fails.

    The original73bb Commands implementation and writer are unchanged.  This
    adapter binds only the freshly imported lifecycle module instance and the
    currently owned command directory. It changes no successful result and
    starts no process, signal, or ownership probe.
    """

    def __init__(self, original_write, owner, record):
        self.original_write, self.owner, self.record = original_write, owner, record
        self.active = None
        self.pending = None

    def begin(self, directory):
        self.active, self.pending = Path(directory), None

    def end(self):
        self.active, self.pending = None, None

    def __call__(self, path, value):
        path = Path(path)
        selected = (self.active is not None and path.parent == self.active
                    and self.active.parent == self.owner.root
                    and path.name in ('interruption.json', 'process-exit.json', 'result.json')
                    and isinstance(value, dict))
        if selected and self.pending is None:
            cause = None
            if isinstance(value.get('interruption'), dict):
                cause = value['interruption']
            elif isinstance(value.get('spawnError'), dict):
                cause = value['spawnError']
            elif value.get('commandStatus') == 'FAIL_COMMAND':
                if type(value.get('exitCode')) is int and value['exitCode'] != 0:
                    cause = {'type': 'OriginalCommandOutcome',
                             'message': 'Original command exited with status ' + str(value['exitCode']),
                             'exitCode': value['exitCode']}
                elif value.get('cleanupErrors'):
                    cause = value['cleanupErrors'][0]
            elif (value.get('status') == 'FAIL_COMMAND'
                  and value.get('ownedGroupObservationStatus') not in (None, 'ABSENT_ESRCH')):
                cause = {'type': 'OriginalOwnedGroupOutcome',
                         'message': 'Original owned group absence did not qualify: '
                                    + str(value['ownedGroupObservationStatus']),
                         'ownedGroupObservationStatus': value['ownedGroupObservationStatus']}
            if isinstance(cause, dict) and 'type' in cause and 'message' in cause:
                self.pending = {'path': str(path), 'cause': copy.deepcopy(cause),
                                'originalOutcome': copy.deepcopy(value)}
        try:
            return self.original_write(path, value)
        except BaseException as exc:
            if selected and self.pending is not None:
                # Latch the actual earlier outcome only on this write failure;
                # a successful original write keeps the normal exception path.
                if self.record['firstFailure'] is None:
                    self.record['firstFailure'] = self.pending['cause']
                    self.record['originalCommandFirstOutcome'] = self.pending
                self.record['secondaryErrors'].append(
                    {'phase': 'original-command-receipt-write', 'path': str(path), **error(exc)})
            raise


class Commands:
    """An adapter around the unchanged original73bb owner, with no PID reuse probes."""

    def __init__(self, lifecycle, root, role, record):
        self.root, self.role, self.record = root, role, record
        self.deadline = time.monotonic() + (600 if role.startswith('export-') else 360)
        self.owner = lifecycle.Commands(root / 'commands', root)
        self.outcome_writes = OriginalOutcomeWrites(lifecycle.write, self.owner, record)
        lifecycle.write = self.outcome_writes
        for key in list(self.owner.environment):
            if key.startswith('GIT_'):
                del self.owner.environment[key]
        self.owner.environment.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0',
            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', PYTHONDONTWRITEBYTECODE='1',
            DEVELOPER_DIR=DEVELOPER)
        self.sequence = 0

    def barrier(self):
        require(not self.owner.cancelled and set(self.owner.groups) <= self.owner.absent_groups,
                'An original owned command is unresolved; no later command may start')
        require(self.record['firstFailure'] is None and time.monotonic() < self.deadline,
                'Earlier failure or whole-operation deadline prevents continuation')

    def run(self, argv, label, seconds=60, checked=True, maximum=MIB):
        self.barrier()
        resources(self.root, self.role)
        self.sequence += 1
        timeout = min(seconds, self.deadline - time.monotonic())
        require(timeout > 0, 'Finite command deadline exhausted')
        self.outcome_writes.begin(self.owner.root / (str(self.sequence) + '-' + label))
        try:
            log, result = self.owner.run(argv, str(self.sequence) + '-' + label, timeout,
                                         checked=checked, capacity=True)
            self.record['commands'].append({'label': label, 'result': result,
                                            'mergedOutput': file_ref(log, maximum)})
            self.barrier()
            require(sum(row['mergedOutput']['bytes'] for row in self.record['commands']) <= MAX_LOGS,
                    'Finite command-log envelope exceeded')
            return log.read_bytes(), result
        except BaseException as exc:
            if self.record['firstFailure'] is None:
                self.record['firstFailure'] = error(exc)
            raise
        finally:
            self.outcome_writes.end()

    def git(self, repository, *arguments, original=False, seconds=60, maximum=MIB):
        prefix = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent'] if original and sys.platform.startswith('linux') else []
        argv = prefix + ['/usr/bin/git', '--no-optional-locks', '--no-replace-objects',
            '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.hooksPath=/dev/null',
            '-c', 'pack.threads=1', '-c', 'pack.windowMemory=32m', '-c', 'pack.deltaCacheSize=16m',
            '-c', 'pack.window=10',
            '-c', 'fetch.fsckObjects=true', '-c', 'transfer.fsckObjects=true',
            '-C', str(repository), *arguments]
        return self.run(argv, 'git-' + arguments[0].lstrip('-'), seconds, maximum=maximum)[0]


def repository_metadata(repository):
    """Record only original Git control files and explicit alternates dependencies."""
    repository = physical(repository, directory=True)
    result, visited = {'repository': str(repository), 'files': {}, 'alternateObjectDirectories': []}, set()
    for name in ('config', 'HEAD', 'shallow'):
        path = repository / name
        if path.exists() or path.is_symlink():
            result['files'][name] = file_ref(path, MIB)

    def objects(path):
        path = physical(path, directory=True)
        require(path not in visited and len(visited) < 8, 'Cyclic or excessive original alternate dependencies')
        visited.add(path)
        item = path / 'info/alternates'
        if item.exists() or item.is_symlink():
            ref = file_ref(item, MIB)
            lines = read(ref).decode('utf-8').splitlines()
            require(lines and all(line and Path(line).is_absolute() for line in lines),
                    'Only explicit original absolute alternates are supported')
            result['files'][str(item)] = ref
            for line in lines:
                alternate = physical(line, directory=True)
                result['alternateObjectDirectories'].append(str(alternate))
                objects(alternate)
    objects(repository / 'objects')
    return result


def bundle_header(path):
    with physical(path).open('rb') as stream:
        raw = stream.read(MIB)
    require(b'\n\n' in raw, 'Bounded normal bundle header required')
    header = raw.split(b'\n\n', 1)[0]
    lines = header.decode('utf-8').splitlines()
    require(lines[0] == '# v2 git bundle', 'Exact normal SHA1 v2 bundle format required')
    prerequisites, refs = [], []
    for line in lines[1:]:
        if line.startswith('-'):
            oid = line[1:].split(' ', 1)[0]
            require(re.fullmatch('[0-9a-f]{40}', oid), 'Invalid prerequisite identity')
            prerequisites.append(oid)
        else:
            oid, name = line.split(' ', 1)
            require(re.fullmatch('[0-9a-f]{40}', oid), 'Invalid advertised source identity')
            refs.append({'commit': oid, 'ref': name})
    require(0 < len(prerequisites) <= 64 and len(prerequisites) == len(set(prerequisites)),
            'One bounded genuine incremental prerequisite set is required')
    return {'headerSHA256': sha(header + b'\n\n'), 'prerequisites': prerequisites, 'refs': refs}


def original_identity(commands, repository, commit, tree=None, original=False):
    raw = commands.git(repository, 'rev-parse', commit + '^{commit}', commit + '^{tree}', original=original)
    lines = raw.decode().splitlines()
    require(len(lines) == 2 and lines[0] == commit and re.fullmatch('[0-9a-f]{40}', lines[1]),
            'Exact original commit/tree unavailable; no fetch fallback')
    require(tree is None or lines[1] == tree, 'Original source tree differs')
    return {'commit': commit, 'tree': lines[1]}


def new_reader(commands, root, name, original_objects):
    destination = physical(root / name, exists=False)
    commands.run(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', 'init', '--bare', str(destination)],
                 'init-exclusive-bare', 30)
    write(destination / 'objects/info/alternates', (str(original_objects) + '\n').encode())
    return destination


def app_input_inventory(plan, commands, root, record):
    """Reuse the actual final worktree's 98 bytes; do not copy its source tree."""
    expected = json.loads(read(plan['expectedSourceInventory']))
    commit, tree = plan['sourceCommit'], plan['sourceTree']
    require(expected['sourceCommit'] == commit and expected['sourceTree'] == tree,
            'Exact selected candidate source inventory is required')
    rows = {row['path']: row for row in expected['sources']}
    require(len(rows) == len(expected['sources']) == 98, 'Complete finite98 input set is required')
    worktree = physical(APP_ORACLE_WORKTREE, directory=True)
    require(commands.git(worktree, 'rev-parse', 'HEAD', 'HEAD^{tree}', original=True).decode().splitlines()
            == [commit, tree], 'Existing Oracle source is not this exact selected candidate')
    raw = commands.git(APP_REPOSITORY, 'ls-tree', '-r', '-l', '-z', tree, '--', *sorted(rows), original=True)
    actual = {}
    for entry in raw.split(b'\0'):
        if entry:
            head, name = entry.split(b'\t', 1)
            mode, kind, oid, size = head.decode().split()
            require(kind == 'blob' and name.decode() not in actual, 'Original source inventory kind/duplicate differs')
            actual[name.decode()] = {'mode': mode, 'gitBlob': oid, 'bytes': int(size)}
    require(set(actual) == set(rows), 'Actual immutable tree is missing a required input')
    selected = []
    for name in sorted(rows):
        row = rows[name]
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and actual[name] == {key: row[key] for key in ('mode', 'gitBlob', 'bytes')},
                'Selected original Git source differs: ' + name)
        local = physical(worktree / name)
        original = {'path': str(local), 'bytes': row['bytes'], 'sha256': row['sha256']}
        content = read(original, 4 * MIB)
        require(hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() == row['gitBlob'],
                'Actual selected source content is not its immutable Git blob')
        selected.append({key: row[key] for key in ('path', 'mode', 'gitBlob', 'bytes', 'sha256')}
                        | {'localPath': str(local)})
    require(commands.git(worktree, 'rev-parse', 'HEAD', 'HEAD^{tree}', original=True).decode().splitlines()
            == [commit, tree], 'Existing Oracle source moved while reading finite inputs')
    record['sourceInventory'] = write(root / 'source-inputs.original.json',
        {'schema': 'pinkha-forward-warm-original-source-inputs-v1', 'sourceCommit': commit, 'sourceTree': tree,
         'sources': selected, 'runtimeActivation': False, 'readyForBuild': False})
    record['sourceCopyCount'] = 0


def export_bundle(plan, commands, root, record):
    role = plan['role'].removeprefix('export-')
    require(role in EXPORT_REF, 'Closed exporter role required')
    repository, baseline = (SDK_REPOSITORY, SDK_BASE) if role == 'sdk' else (APP_REPOSITORY, APP_BASE)
    commit, tree = plan['sourceCommit'], plan['sourceTree']
    require(re.fullmatch('[0-9a-f]{40}', commit or '') and re.fullmatch('[0-9a-f]{40}', tree or ''),
            'Final immutable source/tree input remains unbound')
    if role == 'sdk':
        require((commit, tree) == (SDK, SDK_TREE), 'Only the actually published c0b SDK is selected')
        publication = json.loads(read(plan['sourcePublication']))
        require(plan['sourcePublication']['sha256'] == SDK_PUBLICATION_SHA
                and publication['normalPushCompleted'] is True
                and publication['candidateCommit'] == SDK and publication['candidateTree'] == SDK_TREE
                and publication['firstFailure'] is None and publication['commandCustodyBlocked'] is False,
                'Exact positive SDK publication required')
    else:
        publication = json.loads(read(plan['sourcePublication']))
        require(publication['head'] == commit and publication['tree'] == tree
                and publication['normalPushCompleted'] is True and publication['sourceRetentionPassed'] is True
                and publication['firstFailure'] is None and publication['commandCustodyBlocked'] is False,
                'Selected final App original publication required')
    record['sourcePublication'] = plan['sourcePublication']
    before = repository_metadata(repository)
    require(commands.git(repository, 'rev-parse', '--is-bare-repository', original=True).strip() == b'true',
            'Expected original bare Git store required')
    record['sourceIdentity'] = original_identity(commands, repository, commit, tree, True)
    record['baselineIdentity'] = original_identity(commands, repository, baseline,
        APP_BASE_TREE if role == 'app' else None, True)
    commands.git(repository, 'merge-base', '--is-ancestor', baseline, commit, original=True)
    if role == 'app':
        app_input_inventory(plan, commands, root, record)
    bare = new_reader(commands, root, 'export.git', repository / 'objects')
    # The only new ref belongs to this fresh export reader, never the original mirror.
    commands.git(bare, 'update-ref', EXPORT_REF[role], commit, '0' * 40)
    bundle = physical(root / (role + '.bundle'), exists=False)
    commands.git(bare, 'bundle', 'create', '--version=2', str(bundle), EXPORT_REF[role], '^' + baseline,
                 seconds=180)
    bundle_ref = file_ref(bundle)
    header = bundle_header(bundle)
    require(header['refs'] == [{'commit': commit, 'ref': EXPORT_REF[role]}], 'Unexpected bundle advertised source')
    for prerequisite in header['prerequisites']:
        original_identity(commands, repository, prerequisite, original=True)
        commands.git(repository, 'merge-base', '--is-ancestor', prerequisite, baseline, original=True)
    commands.git(bare, 'bundle', 'verify', str(bundle), seconds=60)
    require(file_ref(bundle) == bundle_ref, 'Bundle changed during original verification')
    require(repository_metadata(repository) == before, 'Original Git control/alternate metadata changed')
    original_identity(commands, repository, commit, tree, True)
    record.update(bundle=bundle_ref, bundleHeader=header, sourceRepository=str(repository),
        sourceMetadataBefore=before, sourceMetadataAfter=repository_metadata(repository),
        excludedBaseline=baseline, originalMirrorMutations=0, transportPerformed=False,
        status='PASS_GENUINE_INCREMENTAL_BUNDLE_SOURCE_CUSTODY_ONLY')


def mac_census(plan, root, record):
    binding = plan['processObservation']
    observer = load(binding['adapter'], 'phase_observer', PHASE_OBSERVER)
    control_paths = [str(Path(__file__).resolve()), record['plan']['path'], plan['lifecycle']['path']]
    if 'sdkClosureHelper' in plan:
        control_paths.append(plan['sdkClosureHelper']['path'])
    protected = [root]
    if plan['role'] == 'observe-toolchain':
        protected.append(APP_SOURCE)
    observed, ref = observer.observe(binding, plan['role'], root / 'mac-owner-census.json', record,
        protected_paths=protected, control_paths=control_paths, reader_roots=[OLD_SDK_READER])
    record['macOwnerCensus'] = ref
    record['originalReaderMetadataAtObservation'] = observed['originalReaderMetadataAfter'][str(OLD_SDK_READER)]
    # Observation evidence has its own64MiB allowance. Recheck this original
    # input role's640MiB/8MiB+2GiB on actual remaining capacity before any Git/tool.
    record['resourcesAfterProcessObservation'] = resources(root, plan['role'])


def receive_sdk(plan, commands, root, record):
    marker_read = json.loads(read(plan['markerReadReceipt']))
    require(plan['markerReadReceipt']['sha256'] == MARKER_READ_RECEIPT_SHA
            and marker_read['status'] == 'PASS_ORIGINAL_C0B_MARKER_DERIVED_FROM_ALL1011_SOURCE_BYTES'
            and marker_read['sourceCommit'] == SDK and marker_read['sourceTree'] == SDK_TREE
            and marker_read['sourceFilesHashed'] == 1011 and marker_read['sourceBytesHashed'] == 39812364
            and marker_read['firstFailure'] is None and marker_read['commandCustodyBlocked'] is False,
            'Actual original source marker derivation receipt is required')
    original_metadata = repository_metadata(OLD_SDK_READER)
    require(original_metadata == record['originalReaderMetadataAtObservation'],
            'Original385/actual transitive object metadata changed after the complete observation')
    record['retained385Identity'] = original_identity(commands, OLD_SDK_READER, SDK_BASE)
    require(commands.git(OLD_SDK_READER, 'rev-parse', '--is-bare-repository').strip() == b'true',
            'Retained385 source must be the original bare reader')
    exported = json.loads(read(plan['exportReceipt']))
    require(exported['role'] == 'export-sdk'
            and exported['status'] == 'PASS_GENUINE_INCREMENTAL_BUNDLE_SOURCE_CUSTODY_ONLY'
            and exported['firstFailure'] is None and exported['commandCustodyBlocked'] is False
            and exported['sourceIdentity'] == {'commit': SDK, 'tree': SDK_TREE}
            and exported['excludedBaseline'] == SDK_BASE,
            'Actual successful exact c0b bundle producer is required')
    bundle = physical(plan['bundle']['path'])
    bundle_ref = file_ref(bundle)
    require(bundle_ref == plan['bundle'] and all(bundle_ref[key] == exported['bundle'][key]
            for key in ('bytes', 'sha256')), 'Transported original bundle size/hash differs')
    header = bundle_header(bundle)
    require(header == exported['bundleHeader']
            and header['refs'] == [{'commit': SDK, 'ref': EXPORT_REF['sdk']}], 'Transported bundle header differs')
    for prerequisite in header['prerequisites']:
        original_identity(commands, OLD_SDK_READER, prerequisite)
        commands.git(OLD_SDK_READER, 'merge-base', '--is-ancestor', prerequisite, SDK_BASE)
    bare = new_reader(commands, root, 'hanlin-c0b-source.git', OLD_SDK_READER / 'objects')
    commands.git(bare, 'bundle', 'verify', str(bundle))
    commands.git(bare, '-c', 'fetch.unpackLimit=1', 'fetch', '--no-tags', '--no-write-fetch-head',
                 '--no-recurse-submodules', '--no-auto-maintenance', str(bundle),
                 EXPORT_REF['sdk'] + ':refs/heads/source', seconds=180)
    original_identity(commands, bare, SDK, SDK_TREE)
    closure = load(plan['sdkClosureHelper'], 'sdk_closure', SDK_CLOSURE)
    inventory_raw = commands.git(bare, 'ls-tree', '-r', '-l', '-z', SDK_TREE, '--', *closure.PACKAGES)
    inventory = closure.parse_inventory(inventory_raw)
    archive = physical(root / 'selected-sdk-source.original.tar', exists=False)
    commands.git(bare, 'archive', '--format=tar', '--output=' + str(archive), SDK, *closure.PACKAGES, seconds=60)
    archive_ref = file_ref(archive, 64 * MIB)
    marker, rows = closure.marker_from_archive(read(archive_ref, 64 * MIB), inventory, commands.deadline)
    expected_marker = read(plan['expectedMarker'])
    expected_rows = json.loads(read(plan['expectedSourceRows']))
    require(plan['expectedMarker']['sha256'] == MARKER_SHA and marker == expected_marker,
            'All1011 actual reader source bytes must produce the original41445 marker')
    require(plan['expectedSourceRows']['sha256'] == SOURCE_ROWS_SHA
            and expected_rows['revision'] == SDK and expected_rows['tree'] == SDK_TREE
            and expected_rows['count'] == 1011 and expected_rows['sourceBytes'] == 39812364
            and [{'path': name, **rows[name]} for name in sorted(rows)] == expected_rows['files'],
            'Complete original1011 Git modes/blobs/sizes/content closure differs')
    require(commands.git(bare, 'ls-tree', '-r', '-l', '-z', SDK_TREE, '--', *closure.PACKAGES) == inventory_raw,
            'Selected source inventory changed during actual readback')
    original_identity(commands, bare, SDK, SDK_TREE)
    require(repository_metadata(OLD_SDK_READER) == original_metadata,
            'Retained385/9565 original metadata or explicit alternate dependency changed')
    require(file_ref(bundle) == bundle_ref, 'Original transported bundle changed during intake')
    record.update(status='PASS_FRESH_DEPENDENT_C0B_GIT_READER_ALL1011_SOURCE_BYTES',
        sourceIdentity={'commit': SDK, 'tree': SDK_TREE}, sourceRoot=str(bare), bundle=bundle_ref,
        bundleHeader=header, exportReceipt=plan['exportReceipt'], selectedArchive=archive_ref,
        expectedMarker=write(root / 'reader-expected-marker.json', marker),
        actualSelectedInventory=write(root / 'reader-source-file-hashes.json', expected_rows),
        originalReaderMetadataBefore=original_metadata,
        originalReaderMetadataAfter=repository_metadata(OLD_SDK_READER),
        markerReadReceipt=plan['markerReadReceipt'],
        borrowedObjects=str(OLD_SDK_READER / 'objects'),
        retainedAlternateDependencies=original_metadata['alternateObjectDirectories'],
        fullRepositoryCloneClaimed=False, standaloneRecoveryClaimed=False,
        originalReaderMutations=0, materializations=0,
        scope='SELECTED_FOUR_PACKAGE_READ_ONLY_GIT_SOURCE; RETAIN_ORIGINAL385_AND_TRANSITIVE9565_OBJECTS')


def observe_toolchain(plan, commands, root, record):
    require(plan['developerDir'] == DEVELOPER, 'The original selected developer directory is required')
    require(commands.git(APP_SOURCE, 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines()
            == [APP_BASE, APP_BASE_TREE], 'Retained8f2 source identity differs before the planned forward stage')
    require(commands.git(APP_SOURCE, 'status', '--porcelain', '--untracked-files=all') == b'',
            'Retained8f2 source is not clean')
    observations = {}
    for name, argv in TOOLCHAIN.items():
        raw, outcome = commands.run(argv, 'toolchain-' + name, 60, maximum=256 * 1024)
        require(outcome['status'] == 'PASS_COMMAND', 'Original toolchain command did not qualify')
        original = write(root / (name + '.merged-original.log'), raw)
        observations[name] = {'argv': argv, 'developerDir': DEVELOPER, 'exitCode': outcome['exitCode'],
                              'stream': 'STDOUT_WITH_STDERR_STDOUT_FROM_UNCHANGED73BB_COMMANDS',
                              'original': original}
    require(b'Xcode 27.0\nBuild version 27A266a\n' in read(observations['xcode']['original']),
            'Actual original Xcode27.0/27A266a is required')
    require(read(observations['simulator-sdk']['original']).strip() == b'24A430',
            'Original selected simulator SDK build differs')
    swift = read(observations['swift']['original'])
    require(b'swiftlang-6.4.0.34.1 clang-2100.3.34.1' in swift and b'Target: arm64-apple-macosx27.0.0\n' in swift,
            'Original selected Swift compiler differs')
    record.update(status='PASS_ACTUAL_SAME_DEVELOPER_DIR_MERGED_TOOLCHAIN_OUTPUTS',
                  toolchainOriginals=observations, developerDir=DEVELOPER,
                  binderToolchainOriginals={name: {key: row[key] for key in ('argv', 'developerDir', 'exitCode')}
                      | {'original': {key: row['original'][key] for key in ('path', 'sha256')}}
                      for name, row in observations.items()},
                  resolvedDeveloperDir=str(Path(DEVELOPER).resolve(strict=True)),
                  compilerInvocations=0, toolVersionQueries=3)


def interrupted(signum, _frame):
    raise InterruptedError('Warm input custody interrupted by signal ' + str(signum))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    plan_path = physical(args.plan)
    plan_ref = file_ref(plan_path, MIB)
    require(plan_ref['sha256'] == args.plan_sha256, 'Root-reviewed plan bytes differ')
    plan = json.loads(read(plan_ref))
    require(plan['schema'] == 'pinkha-warm-input-custody-plan-v1' and plan['readyForExecution'] is True,
            'This source-only input plan is not authorized for execution')
    require(plan['controllerSHA256'] == file_ref(Path(__file__).resolve())['sha256'], 'Executed controller differs')
    role = plan['role']
    require(role in ('export-sdk', 'export-app', 'receive-sdk', 'observe-toolchain'), 'Closed finite role required')
    require((role.startswith('export-') and platform.system() == 'Linux' and os.geteuid() == 0)
            or (not role.startswith('export-') and platform.system() == 'Darwin' and os.geteuid() == 501),
            'Exact existing root Oracle or m1 Mac execution context is required')
    require(plan['rootWindow']['status'] == 'ROOT_AUTHORIZED_FINITE_INPUT_CUSTODY_WINDOW',
            'Actual root window handoff is required')
    read(plan['rootWindow']['evidence'])
    root = physical(plan['outputRoot'], exists=False)
    expected_parent = Path('/mnt/development/projects/evidence') if role.startswith('export-') else Path('/Users/m1/builds')
    require(root.parent == expected_parent and root.name.startswith('pinkha-warm-input-'),
            'One fresh owned input namespace is required')
    before = resources(root, role)
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    # Inherited file-size cap bounds a genuine pack/bundle write, without changing
    # the original process owner or permitting any existing file to be truncated.
    previous_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
    ceiling = MAX_BUNDLE if previous_limit[1] == resource.RLIM_INFINITY else min(MAX_BUNDLE, previous_limit[1])
    resource.setrlimit(resource.RLIMIT_FSIZE, (ceiling, ceiling))
    root.mkdir(mode=0o700)
    record = {'schema': 'pinkha-warm-input-custody-receipt-v1', 'role': role, 'status': 'STARTED',
        'startedAt': time.time(), 'controllerSHA256': plan['controllerSHA256'], 'plan': plan_ref,
        'rootWindow': plan['rootWindow'], 'outputRoot': str(root), 'resourcesBefore': before,
        'commands': [], 'firstFailure': None, 'secondaryErrors': [], 'commandCustodyBlocked': False,
        'runtimeActivation': False, 'readyForStaging': False, 'readyForBuild': False,
        'finalSourceSDKNativeProductTuple': None, 'materializations': 0, 'compilerInvocations': 0, 'testsExecuted': 0}
    commands, first = None, None
    try:
        lifecycle = load(plan['lifecycle'], 'lifecycle', LIFECYCLE)
        if not role.startswith('export-'):
            mac_census(plan, root, record)
        commands = Commands(lifecycle, root, role, record)
        if role.startswith('export-'):
            export_bundle(plan, commands, root, record)
        elif role == 'receive-sdk':
            receive_sdk(plan, commands, root, record)
        else:
            observe_toolchain(plan, commands, root, record)
        commands.barrier()
    except BaseException as exc:
        first = exc
        record['status'] = 'FAIL_WARM_INPUT_CUSTODY'
        if record['firstFailure'] is None:
            record['firstFailure'] = error(exc)
    if commands is not None:
        record['ownedGroups'] = commands.owner.groups
        record['latchedAbsentGroups'] = sorted(commands.owner.absent_groups)
        record['commandCustodyBlocked'] = bool(record.get('processObservationCustodyBlocked')
            or not (set(commands.owner.groups) <= commands.owner.absent_groups))
        if record['commandCustodyBlocked'] and first is None:
            first = ValueError('Known original owned command group remains unresolved')
            record['firstFailure'] = error(first)
            record['status'] = 'FAIL_WARM_INPUT_CUSTODY'
    try:
        record['resourcesAfter'] = resources(root, role)
    except BaseException as exc:
        record['secondaryErrors'].append({'phase': 'terminal-resource-observation', **error(exc)})
        if first is None:
            first = exc
            record['firstFailure'] = error(exc)
            record['status'] = 'FAIL_WARM_INPUT_CUSTODY'
    record['finishedAt'] = time.time()
    try:
        write(root / 'receipt.json', record)
    except BaseException as exc:
        record['secondaryErrors'].append({'phase': 'terminal-receipt-write', **error(exc)})
        if first is None:
            first = exc
            record['firstFailure'] = error(exc)
            record['status'] = 'FAIL_WARM_INPUT_CUSTODY'
    print(json.dumps(record, sort_keys=True, allow_nan=False), flush=True)
    return 0 if first is None else 1


if __name__ == '__main__':
    sys.exit(main())
