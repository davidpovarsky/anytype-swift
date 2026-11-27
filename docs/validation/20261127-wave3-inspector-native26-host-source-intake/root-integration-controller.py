#!/usr/bin/env python3
"""Prepared finite normal three-tip integration; final payload remains unbound.

Preserve accepted265 source-merge semantics and the original SDK publisher's
per-command ownership/positive process-group closure. No automatic reset,
abort, force push, runtime activation, build or SDK materialization.
"""
import base64
import difflib
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import time

ROOT = Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
BARE = ROOT
WORKTREE = ROOT
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
AGENT = PRE
START = '01bc25a63371c4c7640dc0c20b75500e28325f87'
START_TREE = '0733b6e8811302d978e6dba76726e4bd1d2bed58'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['c3f2b562f32540f7ba1e1d3d43601b6699ea676a',
          'd528e5413c72320c423ce9ccdbd4fbe423ca4a4a',
          'cde0b83a3f04f36232eed93e6ab2cb7be0e692a5']
PRIOR = Path('/tmp/pinkha-root-w2-sdk61-source-integration-20261127-attempt2.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-inspector-native26-host-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-inspector-native26-host-source-integration-20261127')
PRIVATE = Path('/tmp/pinkha-root-inspector-native26-host-source-index-20261127')
OUT = Path('/tmp/pinkha-root-inspector-native26-host-source-integration-20261127.json')
PREFIX = 'docs/validation/20261127-wave3-inspector-native26-host-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-inspector-native26-host-source-retention-final-20261127.json')
PACKED_BYTES = 1689256
PACKED_SHA = '0a10486a33587cc8633cd033443e66db863636fe9dff3903c2dfc6c2db3afefe'
PAYLOAD_BYTES = 6640057
PAYLOAD_SHA = '817ae2747e3175e94a1f5d73fe5ae7b40ff38a32120d30384077e6081c4f3b4a'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2

COMMON = '2752229aacf72f468f32a4bfe5fe0a91142f5dbe'
UNICODE = '13dc5b060c23527aeaedb1d1e250a86c9a2fc17c'
SDK = '5fffe60fbcec8b12ae2cc14bcb092884677f19b0'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
CONFLICT_PATH = 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift'
ORIGINAL_CONTROLLER_SHA = 'bc720d0b1fe92290e7fad5d9723a6f867d1ce79bcfd577bd9fb9daacc6bddb3a'
ORIGINAL_CONTROLLER_PATH = 'docs/validation/20261127-wave3-w2-sdk61-source-intake/root-integration-controller.py'
PRIOR_BYTES = 377272
PRIOR_SHA = 'f96c02721a655f3c24a3991c2cfb0d0911f245429a0b569aa22e3ae8125bcbfc'
FIRST_GATE_OUT = Path('/tmp/pinkha-root-inspector-native26-host-source-retention-first-20261127.json')


def require(value, message):
    if not value:
        raise ValueError(message)



def sha(raw):
    return hashlib.sha256(raw).hexdigest()



def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()



def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()



def no_symlinks(path):
    for part in [path, *path.parents]:
        require(not part.is_symlink(), 'Symbolic path component: ' + str(part))



def read_regular(path, maximum=MAX_LOG):
    no_symlinks(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'Nonregular or oversized input: ' + str(path))
        raw = stream.read(maximum + 1)
        require(len(raw) == before.st_size and os.fstat(stream.fileno()) == before, 'Input changed while read: ' + str(path))
        return raw



def exclusive(path, raw):
    no_symlinks(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())



def optional_file_identity(path):
    no_symlinks(path)
    if not path.exists():
        return {'path': str(path), 'absent': True}
    before = path.stat()
    raw = read_regular(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw),
            'device': before.st_dev, 'inode': before.st_ino, 'mode': before.st_mode,
            'uid': before.st_uid, 'gid': before.st_gid,
            'mtime_ns': before.st_mtime_ns, 'ctime_ns': before.st_ctime_ns}



def resources():
    result = {}
    for name, path, floor, growth in [('root', Path('/'), 2 * 1024**3, 64 * 1024**2),
                                     ('development', BARE, 512 * 1024**2, 64 * 1024**2)]:
        v = os.statvfs(path)
        free = v.f_bavail * v.f_frsize
        require(free >= floor + growth, name + ' below source-only floor plus bounded growth')
        result[name] = {'freeBytes': free, 'floorBytes': floor, 'growthAllowanceBytes': growth}
    memory = dict(re.findall(r'^(\w+):\s+(\d+) kB$', Path('/proc/meminfo').read_text(), re.M))
    available = int(memory['MemAvailable']) * 1024
    require(available >= 256 * 1024**2, 'Available memory below256MiB')
    result['memoryAvailableBytes'] = available
    return result



def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True



def join_group(process, row):
    row['originalGroupAbsentAfterLeader'] = group_absent(process.pid)
    row['cleanupSignals'] = []
    if not row['originalGroupAbsentAfterLeader']:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if group_absent(process.pid):
                break
            try:
                os.killpg(process.pid, sig)
                row['cleanupSignals'].append(sig.name)
            except ProcessLookupError:
                pass
            end = time.monotonic() + 5
            while not group_absent(process.pid) and time.monotonic() < end:
                try:
                    process.wait(timeout=0.05)
                except subprocess.TimeoutExpired:
                    pass
                time.sleep(0.05)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    row['originalProcessGroupAbsent'] = group_absent(process.pid)
    require(row['originalProcessGroupAbsent'], 'Owned process group remains: ' + str(process.pid))



class Commands:
    def __init__(self, receipt):
        self.receipt = receipt
        self.deadline = time.monotonic() + MAX_SECONDS
        self.blocked = False
        self.in_cleanup = False
        self.interrupted_signal = None

    def run(self, label, argv, *, data=None, env=None, timeout=25):
        require(not self.blocked, 'No command after abnormal or unresolved custody')
        remaining = self.deadline - time.monotonic()
        require(remaining > 1, 'Publication live-time budget exhausted')
        row = {'label': label, 'argv': argv, 'startedAt': time.time(), 'timeoutSeconds': min(timeout, remaining)}
        self.receipt['commands'].append(row)
        stem = EVIDENCE / ('command-%03d-' % len(self.receipt['commands']) + label)
        out_path, err_path = Path(str(stem) + '.stdout'), Path(str(stem) + '.stderr')
        stdin = None
        if data is not None:
            require(len(data) <= MAX_LOG, 'Oversized closed command input')
            input_path = Path(str(stem) + '.stdin')
            exclusive(input_path, data)
            row['stdin'] = {'path': str(input_path), 'bytes': len(data), 'sha256': sha(data)}
            stdin = input_path.open('rb')
        process = None
        first = None
        try:
            with out_path.open('xb') as out, err_path.open('xb') as err:
                try:
                    process = subprocess.Popen(argv, stdin=stdin if stdin else subprocess.DEVNULL,
                                               stdout=out, stderr=err, start_new_session=True,
                                               env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0',
                                                    'PYTHONDONTWRITEBYTECODE': '1', **(env or {})})
                    row.update({'pid': process.pid, 'pgid': process.pid})
                    row['exitCode'] = process.wait(timeout=row['timeoutSeconds'])
                    if row['exitCode'] != 0:
                        raise RuntimeError(label + ' exited ' + str(row['exitCode']))
                except BaseException as error:
                    first = error
                    row['firstFailure'] = {'type': type(error).__name__, 'message': str(error)}
                finally:
                    if process is not None:
                        self.in_cleanup = True
                        try:
                            join_group(process, row)
                        except BaseException as error:
                            row['cleanupFailure'] = {'type': type(error).__name__, 'message': str(error)}
                            if first is None:
                                first = error
                        finally:
                            self.in_cleanup = False
                        row['exitCode'] = process.returncode
                    row['finishedAt'] = time.time()
        finally:
            if stdin is not None:
                stdin.close()
        if self.interrupted_signal is not None:
            self.blocked = True
            if first is None:
                first = TimeoutError('Publication interrupted by signal ' + str(self.interrupted_signal))
        if row.get('cleanupSignals') or row.get('originalProcessGroupAbsent') is not True:
            self.blocked = True
            if first is None:
                first = RuntimeError(label + ': owned descendant cleanup required; command is not accepted')
        if first is not None and 'firstFailure' not in row:
            row['firstFailure'] = {'type': type(first).__name__, 'message': str(first)}
        try:
            for key, path in [('stdout', out_path), ('stderr', err_path)]:
                raw = read_regular(path)
                row[key] = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
            exclusive(Path(str(stem) + '.json'), encoded(row))
        except BaseException as error:
            self.blocked = True
            row['receiptFailure'] = {'type': type(error).__name__, 'message': str(error)}
            if first is None:
                first = error
        if first is not None:
            raise first
        return read_regular(out_path)

    def git(self, label, *args, data=None, private=False, publish=False, timeout=25, worktree=False):
        prefix = AGENT if worktree else PRE
        repo = WORKTREE if worktree else BARE
        # These assignments must occur AFTER sudo: its existing environment
        # filtering must never discard the private index or prompt boundary.
        argv = prefix + ['env', 'GIT_TERMINAL_PROMPT=0', 'GIT_OPTIONAL_LOCKS=0', 'PYTHONDONTWRITEBYTECODE=1']
        if private:
            argv += ['GIT_INDEX_FILE=' + str(PRIVATE / 'index')]
        argv += ['git', '--no-optional-locks', '--no-replace-objects', '-c', 'gc.auto=0', '-C', str(repo)]
        if publish:
            argv += ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential']
        return self.run(label, argv + list(args), data=data, timeout=timeout)



def parse_leaves(raw):
    result = {}
    for line in raw.split(b'\0'):
        if not line:
            continue
        header, path = line.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        require(path.decode() not in result, 'Duplicate Git leaf')
        result[path.decode()] = {'mode': mode, 'type': kind, 'sha': oid}
    return result



def safe_path(path):
    value = PurePosixPath(path)
    require(isinstance(path, str) and str(value) == path and not value.is_absolute()
            and '..' not in value.parts and '\0' not in path and '\n' not in path and '\t' not in path,
            'Invalid finite repository path')
    return path


def match(raw, identity):
    require(len(raw) == identity['bytes'] and sha(raw) == identity['sha256']
            and blob(raw) == identity['gitBlob'] and identity['gitMode'] == '100644',
            'Exact reviewed source identity differs')


def decode_rows(rows):
    values = {}
    for path, row in rows.items():
        safe_path(path)
        require(row['status'] in ('A', 'M'), 'No deletion or rename admitted')
        raw = base64.b64decode(row['base64'], validate=True)
        match(raw, row['after'])
        values[path] = raw
        if row['status'] == 'A':
            require(row['before'] is None and row['beforeBase64'] is None, 'Addition has a preimage')
        else:
            old = base64.b64decode(row['beforeBase64'], validate=True)
            match(old, row['before'])
    return values


def require_leaf(leaves, path, identity):
    expected = None if identity is None else {'mode': identity['gitMode'], 'type': 'blob', 'sha': identity['gitBlob']}
    require(leaves.get(path) == expected, 'Git tree preimage/absence differs: ' + path)


def batch_blobs(commands, label, identities):
    require(all(re.fullmatch('[a-f0-9]{40}', key) for key in identities), 'Invalid closed blob IDs')
    keys = sorted(identities)
    raw = commands.git(label, 'cat-file', '--batch', data=''.join(key + '\n' for key in keys).encode())
    result = {}
    cursor = 0
    for key in keys:
        end = raw.index(b'\n', cursor)
        oid, kind, length = raw[cursor:end].decode().split()
        length = int(length)
        value = raw[end + 1:end + 1 + length]
        require(oid == key and kind == 'blob' and len(value) == length
                and raw[end + 1 + length:end + 2 + length] == b'\n' and blob(value) == key,
                'Malformed original Git blob batch')
        if identities[key] is not None:
            require(value == identities[key], 'Original Git source bytes differ: ' + key)
        result[key] = value
        cursor = end + 2 + length
    require(cursor == len(raw), 'Unexpected trailing Git blob bytes')
    return result


def parse_changes(raw):
    values = raw.split(b'\0')
    require(values[-1] == b'', 'Unterminated Git change inventory')
    values.pop()
    require(len(values) % 2 == 0, 'Malformed Git change inventory')
    result = {}
    for status, path in zip(values[0::2], values[1::2]):
        path = path.decode()
        safe_path(path)
        require(path not in result and status in (b'A', b'M'), 'Unexpected rename/deletion/duplicate')
        result[path] = status.decode()
    return result


def changes(commands, label, before, after):
    return parse_changes(commands.git(label, 'diff', '--name-status', '-z', '--no-renames', before, after))


def tree_leaves(commands, label, tree):
    return parse_leaves(commands.git(label, 'ls-tree', '-r', '-z', tree))


def expected_leaves(base, rows):
    result = dict(base)
    for path, row in rows.items():
        result[path] = {'mode': row['after']['gitMode'], 'type': 'blob', 'sha': row['after']['gitBlob']}
    return result


def private_tree(commands, label, base, rows, expected):
    commands.git(label + '-read-full-start', 'read-tree', START, private=True)
    data = b''.join((row['after']['gitMode'] + ' ' + row['after']['gitBlob'] + '\t' + path).encode() + b'\0'
                    for path, row in sorted(rows.items()))
    commands.git(label + '-apply-exact-entries', 'update-index', '-z', '--index-info', data=data, private=True)
    tree = commands.git(label + '-complete-tree', 'write-tree', private=True).decode().strip()
    require(re.fullmatch('[a-f0-9]{40}', tree), 'Invalid private preview tree')
    require(tree_leaves(commands, label + '-complete-leaves', tree) == expected,
            'Private preview changed a path outside the finite payload')
    require(changes(commands, label + '-finite-diff', START, tree)
            == {path: row['status'] for path, row in rows.items()}, 'Private preview complete diff differs')
    return tree


def destination_preflight(path, previous, *, may_be_sparse=False):
    target = ROOT / safe_path(path)
    no_symlinks(target)
    if previous is None:
        require(not target.exists(), 'Preserve existing untracked destination: ' + path)
    elif target.exists():
        require(read_regular(target) == previous, 'Working-tree preimage differs: ' + path)
    else:
        require(may_be_sparse, 'Expected existing working-tree file is absent: ' + path)


def write_owned_batch(commands, label, rows, values, expected_stage):
    # Every replacement is checked again inside the one existing-owner process.
    # No directory is removed; new files use exclusive creation.
    data = encoded({'root': str(ROOT), 'files': [
        {'path': path, 'after': base64.b64encode(values[path]).decode(),
         'before': None if expected_stage[path] is None else base64.b64encode(expected_stage[path]).decode()}
        for path in sorted(rows)]})
    code = '''import base64,json,os,pathlib,stat,sys
d=json.loads(sys.stdin.buffer.read());root=pathlib.Path(d['root'])
for r in d['files']:
 p=root/r['path']
 for q in [p,*p.parents]:
  assert not q.is_symlink(),str(q)
  if q==root:break
 old=None if r['before'] is None else base64.b64decode(r['before'],validate=True)
 existed=p.exists()
 if old is None:assert not existed,str(p)
 elif existed:assert p.is_file() and p.read_bytes()==old,str(p)
 p.parent.mkdir(parents=True,exist_ok=True)
 raw=base64.b64decode(r['after'],validate=True)
 flags=os.O_RDWR|os.O_NOFOLLOW|(os.O_CREAT|os.O_EXCL if not existed else 0)
 fd=os.open(p,flags,0o644)
 with os.fdopen(fd,'r+b') as f:
  assert stat.S_ISREG(os.fstat(f.fileno()).st_mode),str(p)
  if existed:assert f.read()==old,str(p)
  f.seek(0);f.truncate(0);f.write(raw);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==raw,str(p)
'''
    commands.run(label, PRE + ['python3', '-B', '-c', code], data=data, timeout=45)


def write_new_objects(commands, rows, values, existing_oids):
    for index, (path, row) in enumerate(sorted(rows.items()), 1):
        oid = row['after']['gitBlob']
        if oid in existing_oids:
            continue
        actual = commands.git('new-reviewed-blob-%03d' % index, 'hash-object', '-w', '--stdin', data=values[path]).decode().strip()
        require(actual == oid, 'New reviewed Git object differs: ' + path)
        existing_oids.add(oid)


def original_status(commands, label):
    status = commands.git(label + '-status', 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    untracked = commands.git(label + '-untracked-paths', 'ls-files', '--others', '--exclude-standard', '-z')
    grouped = commands.git(label + '-untracked-groups', 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    expected = b''.join(path.encode() + b'\0' for path in UNTRACKED)
    require(untracked == expected and sha(untracked) == '7dbac249bb04e50bb0e08159393acb49119dde6ebe33670d129ee8f691ab991b',
            'The four original full untracked paths changed')
    require(status == b''.join(b'?? ' + path.encode() + b'\0' for path in UNTRACKED),
            'Tracked cleanliness or full original untracked status changed')
    groups = [value for value in grouped.split(b'\0') if value]
    require(groups and all(row.startswith(b'?? ') for row in groups), 'Tracked grouped status changed')
    files = {path: optional_file_identity(ROOT / path) for path in UNTRACKED}
    require(all(not row.get('absent') for row in files.values()), 'Original untracked file disappeared')
    return {'status': status, 'untracked': untracked, 'grouped': grouped, 'files': files}

def exact_remote(commands, label, expected):
    value = commands.git(label, 'ls-remote', '--heads', 'origin', REF, publish=True, timeout=45).decode().splitlines()
    require(value == [expected + '\t' + REF], 'Final integration remote differs')


def prior_receipt():
    require(isinstance(PRIOR_BYTES, int) and 0 < PRIOR_BYTES <= MAX_LOG
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or ''), 'Positive actual288 receipt is unbound')
    raw = read_regular(PRIOR, PRIOR_BYTES)
    require(len(raw) == PRIOR_BYTES and sha(raw) == PRIOR_SHA, 'Actual positive288 original receipt changed')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-w2-sdk61-source-integration/v1'
            and value['state'] == 'SOURCE_MERGED_PUBLISHED_RUNTIME_CLOSED'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['start'] == COMMON and value['startTree'] == '2d8db7a1585d48b857578920fa19b3730dde488b'
            and value['controllerSHA256'] == ORIGINAL_CONTROLLER_SHA
            and value['payloadSHA256'] == '348959c6ba94bca61febac0a570179933bd0488db556048314fa9ca6ac974bee'
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 133
            and value['normalPushCompleted'] is True and value['commandCustodyBlocked'] is False
            and value['firstFailure'] is None and value['runtimeAcceptance'] is False,
            'Prior actual288 source, publication or custody differs')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Prior288 source-only scope changed')
    require(value['outputPins']['sdk'] == SDK and len(value['outputPins']['allPackagePins']) == 56,
            'Actual prior288 SDK or package lock scope differs')
    return raw, value


def source_payload():
    require(re.fullmatch('[a-f0-9]{40}', START or '') and re.fullmatch('[a-f0-9]{40}', START_TREE or '')
            and isinstance(PRIOR_BYTES, int) and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '')
            and isinstance(PACKED_BYTES, int) and isinstance(PAYLOAD_BYTES, int)
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA or '')
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA or ''), 'Final actual288 tuple is unbound; no host action')
    require(0 < PAYLOAD_BYTES <= MAX_LOG and 0 < PACKED_BYTES <= MAX_LOG, 'Bounded exact source payload required')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed source payload differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Complete source payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-inspector-native26-host-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE and value['bindingReady'] is True
            and value['priorReceipt'] == {'path': str(PRIOR), 'bytes': PRIOR_BYTES, 'sha256': PRIOR_SHA}
            and value['donorTips'] == DONORS and value['commonAncestor'] == COMMON,
            'Closed source/actual publication tuple differs')
    require(value['runtimeAcceptance'] is False and all(value[key] == 0 for key in
            ('testsExecuted', 'compilerInvocations', 'materializations')), 'Source payload cannot activate runtime acceptance')
    require(len(value['firstMergeRows']) == 33 and len(value['donorRows']) == 120
            and len(value['controlRows']) == 38 and len(value['donorLinks']) == 4,
            'Exact33/120/38 and four-link source closure differs')
    first_values = decode_rows(value['firstMergeRows'])
    donor_values = decode_rows(value['donorRows'])
    control_values = decode_rows(value['controlRows'])
    require(set(value['firstMergeRows']).issubset(value['donorRows'])
            and all(row == value['donorRows'][path] for path, row in value['firstMergeRows'].items()),
            'First normal merge rows must be the exact final donor subset')
    require(not set(value['donorRows']).intersection(value['controlRows']), 'No unreviewed source/control override')
    rows = {**value['donorRows'], **value['controlRows']}
    values = {**donor_values, **control_values}
    require(len(rows) == value['finalSourcePathCount'] == 158 and len(first_values) == 33,
            'Exact158 source union required')
    require(value['guardInputs']['sdkRevision'] == SDK and value['knownConflict']['path'] == CONFLICT_PATH,
            'Current SDK or sole allowed conflict differs')
    require(set(value['diffChecks']) == {'first', 'donors', 'source', 'complete'}, 'All finite raw diagnostic scopes required')
    for expected in value['diffChecks'].values():
        require(expected['exit'] in (0, 2) and isinstance(expected['stdout'], str) and isinstance(expected['stderr'], str),
                'Original static Git diagnostic is not bound')
    return raw, packed, value, rows, values


def validate_donors(commands, payload, start_leaves):
    commands.git('fetch-three-exact-donor-tips', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    links = {row['commit']: row for row in payload['donorLinks']}
    require(set(links) == {DONORS[0], UNICODE, DONORS[1], DONORS[2]}, 'Exact reviewed four-link ancestry required')
    reached, external = set(), set()
    def visit(commit):
        if commit not in links:
            external.add(commit)
            return
        if commit in reached:
            return
        reached.add(commit)
        for parent in links[commit]['parents']:
            visit(parent)
    for tip in DONORS:
        visit(tip)
    require(reached == set(links) and external == {COMMON}, 'Unrelated donor ancestry or missing reviewed link')
    commands.git('original-common-base-integrated', 'merge-base', '--is-ancestor', COMMON, START)
    require(commands.git('exact-inspector-merge-base', 'merge-base', START, DONORS[0]).decode().split() == [COMMON],
            'The sole reviewed three-way merge base differs')
    blobs, union = {}, set()
    for index, link in enumerate(payload['donorLinks']):
        result = commands.git('donor-identity-%02d' % index, 'show', '-s', '--format=%H %T %P', link['commit']).decode().split()
        require(result == [link['commit'], link['tree'], *link['parents']] and len(link['parents']) == 1,
                'Published donor commit/tree/parent changed')
        require(link['parents'] == ([UNICODE] if link['commit'] == DONORS[1] else [COMMON]),
                'Exact original13dc/d528 ancestry required')
        actual = changes(commands, 'donor-complete-diff-%02d' % index, link['parents'][0], link['commit'])
        require(actual == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed donor source delta')
        leaves = tree_leaves(commands, 'donor-complete-tree-%02d' % index, link['tree'])
        for path, row in link['files'].items():
            require_leaf(leaves, safe_path(path), row['after'])
            blobs[row['after']['gitBlob']] = None
        union.update(link['files'])
    require(union == set(payload['donorRows']) and set(links[DONORS[0]]['files']) == set(payload['firstMergeRows']),
            'Published source union or first merge path set differs')
    original = batch_blobs(commands, 'all-original-donor-blobs', blobs)
    for link in payload['donorLinks']:
        for row in link['files'].values():
            match(original[row['after']['gitBlob']], row['after'])
    for path, row in payload['donorRows'].items():
        require_leaf(start_leaves, path, row['before'])
        if path == MAP_PATH:
            require(row['base64'] == payload['guardInputs']['sourceMapAfterBase64'],
                    'Only the exact reviewed current133-row map composition is permitted')
        else:
            require(row['after']['gitBlob'] in original
                    and original[row['after']['gitBlob']] == base64.b64decode(row['base64'], validate=True),
                    'Final source row differs from immutable donor bytes')
    return set(blobs)


def diff_check(commands, label, arguments, expected, receipt):
    try:
        commands.git(label, *arguments)
    except RuntimeError:
        row = receipt['commands'][-1]
        require(row['label'] == label and row.get('exitCode') == expected['exit']
                and row.get('originalProcessGroupAbsent') is True and row.get('cleanupSignals') == []
                and not row.get('receiptFailure') and not commands.blocked and commands.interrupted_signal is None,
                'Unexpected diff failure or abnormal command custody')
    row = receipt['commands'][-1]
    stdout = read_regular(Path(row['stdout']['path']))
    stderr = read_regular(Path(row['stderr']['path']))
    require(row['exitCode'] == expected['exit'] and stdout == expected['stdout'].encode()
            and stderr == expected['stderr'].encode(), 'Literal original diff diagnostics changed')
    receipt.setdefault('diffChecks', []).append({'label': label, 'exit': row['exitCode'],
        'stdoutSHA256': sha(stdout), 'stderrSHA256': sha(stderr),
        'scope': 'PASS' if row['exitCode'] == 0 else 'EXACT_RETAINED_ORIGINAL_EVIDENCE_DIAGNOSTICS_NOT_PASS'})


def validate_guards(commands, payload, before_leaves, target_leaves, prior, stage):
    guards = payload['guardInputs']
    require(guards['originalRetentionRows'] == guards['expectedRetentionRows'] == 133,
            'All133 original retention rows must remain')
    require(stage in ('before', 'first', 'after'), 'Finite source guard stage required')
    expected = guards[{'before': 'beforeFiles', 'first': 'firstFiles', 'after': 'afterFiles'}[stage]]
    leaves = before_leaves if stage == 'before' else target_leaves
    values = batch_blobs(commands, 'guard-' + stage + '-original-files', {row['gitBlob']: None for row in expected.values()})
    for path, row in expected.items():
        require_leaf(leaves, path, row)
        match(values[row['gitBlob']], row)
    for path, row in guards['unchangedFiles'].items():
        require_leaf(before_leaves, path, row)
        require_leaf(target_leaves, path, row)
    old_raw = base64.b64decode(guards['sourceMapBeforeBase64'], validate=True)
    new_raw = base64.b64decode(guards['sourceMapAfterBase64'], validate=True)
    match(old_raw, guards['beforeFiles'][MAP_PATH])
    match(new_raw, guards['firstFiles'][MAP_PATH])
    require(guards['firstFiles'][MAP_PATH] == guards['afterFiles'][MAP_PATH], 'No map change in the second merge')
    old_map, new_map = json.loads(old_raw), json.loads(new_raw)
    require(len(old_map['changes']) == len(new_map['changes']) == 133 and guards['sourceMapAppendedRows'] == [],
            'No added or removed source-map row is admitted')
    require({key: value for key, value in old_map.items() if key != 'changes'}
            == {key: value for key, value in new_map.items() if key != 'changes'}, 'Original map envelope changed')
    updates = guards['sourceMapUpdates']
    require(len(updates) == 2 and {row['index'] for row in updates} == {43, 114}, 'Only two original Inspector map pins may change')
    for index, old in enumerate(old_map['changes']):
        new = new_map['changes'][index]
        if index not in (43, 114):
            require(old == new, 'Current SDK/Pasteboard or another original source-map row changed')
            continue
        update = next(row for row in updates if row['index'] == index)
        require(update['before'] == old and update['after'] == new, 'Reviewed Inspector map update differs')
        field = 'sharedSources' if index == 43 else 'replacementBlob'
        require({key: value for key, value in old.items() if key != field}
                == {key: value for key, value in new.items() if key != field}, 'Inspector map metadata/baseline changed')
        if index == 43:
            require(len(old[field]) == len(new[field])
                    and all({key: value for key, value in a.items() if key != 'gitBlob'}
                            == {key: value for key, value in b.items() if key != 'gitBlob'}
                            for a, b in zip(old[field], new[field])), 'Original shared-source paths or metadata changed')
    sdk_path = 'Tools/Hanlin/source.json'
    sdk_raw = base64.b64decode(guards['sdkBase64'], validate=True)
    match(sdk_raw, guards['unchangedFiles'][sdk_path])
    require(values[expected[sdk_path]['gitBlob']] == sdk_raw and json.loads(sdk_raw)['revision'] == SDK,
            'Current5fff SDK source manifest must remain byte-exact')
    register_path = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
    register = base64.b64decode(guards['registerBase64'], validate=True)
    match(register, guards['unchangedFiles'][register_path])
    require(values[expected[register_path]['gitBlob']] == register, 'Current exception register changed')
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    require(lock_path in guards['unchangedFiles'], 'Original56-lock preservation missing')
    pins = json.loads(values[expected[lock_path]['gitBlob']])['pins']
    require(pins == prior['outputPins']['allPackagePins'] and len(pins) == 56,
            'Original Kit and55 other package pins changed')
    activation = guards['closedActivationAfter' if stage == 'after' else 'closedActivationBefore']
    for row in activation:
        require(row['path'] in expected, 'Closed activation is not an exact guarded source')
        data = json.loads(values[expected[row['path']]['gitBlob']])
        for key, wanted in row['fields'].items():
            require(data[key] == wanted and type(data[key]) is type(wanted), 'Runtime activation changed')
    return {'sdk': SDK, 'allPackagePins': pins, 'reviewedRefactors': 133,
            'closedActivation': activation, 'sourceOnly': True}


def validate_sdk_publication(payload):
    row = payload['guardInputs']['sdkPublication']
    require(re.fullmatch('[a-f0-9]{64}', row['sha256']) and 0 < row['bytes'] <= MAX_LOG,
            'Final SDK publication receipt is not bound')
    raw = read_regular(Path(row['path']), row['bytes'])
    require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'Actual final SDK source receipt differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-native-follow-binding-new-ref-publication/v1'
            and value['state'] == 'PASS_SOURCE_ONLY_NEW_REF_PUBLISHED'
            and value['candidateCommit'] == value['normalPushReadback'] == payload['guardInputs']['sdkRevision']
            and value['candidateTree'] == 'a52fdb359190930d23a76877baf2fe8fa25101d6'
            and value['baseTree'] == 'c381d5c97207b30dfd0494bd54b74919010c7b1e'
            and value['ref'] == 'refs/heads/codex/pinkha-sdk-native-follow-binding-20261127'
            and value['controllerSHA256'] == 'e03bf9046ed18e4a72958c7067666dc600534fd9c707ed909ef501b408408a13'
            and value['base'] == '8b548bbe5b1340a48e741191c41d6b30c73537df'
            and value['positiveBasePublicationReceiptSHA256'] == '3afc5bbe91fee176fab2ba0323ad7be5381e1b3c068335716c95f1ab4a723c4f'
            and value['normalPushCompleted'] is True and value['originalSourceWorktreePreserved'] is True
            and value['commandCustodyBlocked'] is False and value['firstFailure'] is None,
            'Final SDK publication/provenance/custody was not accepted')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'workflowDispatches', 'materializations')),
            'Final SDK source proof scope changed')
    return raw


h = sha


def controller_inverse(original,current):
    # Exact byte spans, not semantic substitutions or normalization.
    old_lines=original.splitlines(keepends=True);new_lines=current.splitlines(keepends=True)
    old_offsets=[0];new_offsets=[0]
    for line in old_lines:old_offsets.append(old_offsets[-1]+len(line))
    for line in new_lines:new_offsets.append(new_offsets[-1]+len(line))
    operations=[]
    for tag,a,z,c,d in difflib.SequenceMatcher(a=old_lines,b=new_lines,autojunk=False).get_opcodes():
        if tag=='equal':continue
        operations.append({'originalStartByte':old_offsets[a],'originalEndByte':old_offsets[z],
                           'newStartByte':new_offsets[c],'newEndByte':new_offsets[d],
                           'originalBase64':base64.b64encode(original[old_offsets[a]:old_offsets[z]]).decode(),
                           'newBase64':base64.b64encode(current[new_offsets[c]:new_offsets[d]]).decode()})
    restored=current
    for op in reversed(operations):
        start,end=op['newStartByte'],op['newEndByte'];assert restored[start:end]==base64.b64decode(op['newBase64'])
        restored=restored[:start]+base64.b64decode(op['originalBase64'])+restored[end:]
    assert restored==original
    return {'schema':'pinkha-full-original-controller-byte-inverse-v1','originalSHA256':h(original),'currentSHA256':h(current),'originalBytes':len(original),'currentBytes':len(current),'operations':operations,'fullOriginalRestored':True}



def parse_index_stages(raw):
    stages = {}
    for value in raw.split(b'\0'):
        if not value:
            continue
        header, path_raw = value.split(b'\t', 1)
        mode, oid, stage = header.decode().split()
        path = safe_path(path_raw.decode())
        require(re.fullmatch('[a-f0-9]{40}', oid) and stage in ('0', '1', '2', '3')
                and mode in ('100644', '100755', '120000', '160000'), 'Malformed original index entry')
        require(stage not in stages.setdefault(path, {}), 'Duplicate original index stage')
        stages[path][stage] = {'mode': mode, 'type': 'commit' if mode == '160000' else 'blob', 'sha': oid}
    return stages


def merge_known_inspector_conflict(commands, receipt, payload, merge_head, expected_first):
    label = 'normal-inspector-merge-original-conflict'
    failed = False
    try:
        commands.git(label, '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                     '-c', 'merge.conflictStyle=diff3', '-c', 'merge.renormalize=false',
                     'merge', '--no-ff', '--no-commit', DONORS[0], timeout=60)
    except RuntimeError:
        row = receipt['commands'][-1]
        require(row['label'] == label and row.get('exitCode') == 1
                and row.get('originalProcessGroupAbsent') is True and row.get('cleanupSignals') == []
                and not row.get('receiptFailure') and not row.get('cleanupFailure')
                and not commands.blocked and commands.interrupted_signal is None,
                'Unexpected merge failure or abnormal command custody; preserve all original state')
        failed = True
    require(failed, 'The sole reviewed conflict was not observed; stop without invented resolution')
    command = receipt['commands'][-1]
    require(read_regular(merge_head).decode().split() == [DONORS[0]], 'First normal merge parent differs')
    stages_raw = commands.git('original-full-three-stage-index', 'ls-files', '--stage', '-z')
    stages = parse_index_stages(stages_raw)
    unmerged = {path: value for path, value in stages.items() if set(value) != {'0'}}
    require(set(unmerged) == {CONFLICT_PATH} and set(unmerged[CONFLICT_PATH]) == {'1', '2', '3'},
            'Only the reviewed View may be conflicted')
    conflict = payload['knownConflict']
    for stage, expected in conflict['indexStages'].items():
        require(unmerged[CONFLICT_PATH][stage] == {'mode': expected['gitMode'], 'type': 'blob', 'sha': expected['gitBlob']},
                'Original base/ours/theirs index blob differs')
    clean = {path: value['0'] for path, value in stages.items() if set(value) == {'0'}}
    require(clean == {path: leaf for path, leaf in expected_first.items() if path != CONFLICT_PATH},
            'A clean merged path differs from the complete reviewed first tree')
    batch_blobs(commands, 'three-original-conflict-blobs', {row['gitBlob']: None for row in conflict['indexStages'].values()})
    actual = read_regular(ROOT / CONFLICT_PATH, 1024**2)
    pattern = re.compile(br'^<<<<<<< ([^\r\n]{1,256})\n(.*?)^\|\|\|\|\|\|\| ([^\r\n]{1,256})\n(.*?)^=======\n(.*?)^>>>>>>> ([^\r\n]{1,256})\n', re.M | re.S)
    found = list(pattern.finditer(actual))
    require(len(found) == 1, 'One complete original diff3 conflict required')
    part = found[0]
    normalized = (b'<<<<<<< current288-unpublished-source-projection\n' + part[2]
                  + b'||||||| common275\n' + part[4] + b'=======\n' + part[5] + b'>>>>>>> published-c3\n')
    replacement = conflict['replacement']
    original_span = base64.b64decode(replacement['originalSpanBase64'], validate=True)
    next_span = base64.b64decode(replacement['replacementBase64'], validate=True)
    require(normalized == original_span and len(original_span) == 748 and len(next_span) == 313
            and part.start() == replacement['offset'], 'Original logical Retry conflict differs')
    normalized_whole = actual[:part.start()] + normalized + actual[part.end():]
    match(normalized_whole, conflict['originalConflictOutput'])
    match(next_span, replacement['replacement'])
    resolved = actual[:part.start()] + next_span + actual[part.end():]
    match(resolved, conflict['resolvedWholeSource'])
    require(resolved == base64.b64decode(payload['firstMergeRows'][CONFLICT_PATH]['base64'], validate=True),
            'Single-span output differs from complete reviewed31f source')
    exclusive(EVIDENCE / 'first-merge-original-conflict.swift', actual)
    proof = {'schema': 'pinkha-actual-inspector-single-conflict-resolution/v1',
        'originalCommand': command, 'fullOriginalIndex': {'bytes': len(stages_raw), 'sha256': sha(stages_raw)},
        'indexStages': conflict['indexStages'], 'onlyUnmergedPath': CONFLICT_PATH,
        'actualConflict': {'bytes': len(actual), 'sha256': sha(actual), 'base64': base64.b64encode(actual).decode()},
        'actualMarkerLabels': [part[index].decode() for index in (1, 3, 6)],
        'normalizedConflictSHA256': sha(normalized_whole), 'logicalOriginalSpanSHA256': sha(normalized),
        'actualSpanOffset': part.start(), 'actualSpanBytes': part.end() - part.start(),
        'reviewedLogicalSpanBytes': 748, 'replacementBytes': 313, 'replacementSHA256': sha(next_span),
        'resolvedBytes': len(resolved), 'resolvedSHA256': sha(resolved), 'resolvedGitBlob': blob(resolved),
        'allOutsideBytesUnchanged': True, 'allCleanMergedPathsExact': True,
        'originalRootReview': conflict['originalRootReview'], 'runtimeAcceptance': False}
    exclusive(EVIDENCE / 'first-merge-conflict-proof.json', encoded(proof))
    write_owned_batch(commands, 'resolve-only-reviewed-retry-span', {CONFLICT_PATH: payload['firstMergeRows'][CONFLICT_PATH]},
                      {CONFLICT_PATH: resolved}, {CONFLICT_PATH: actual})
    commands.git('stage-only-reviewed-view-resolution', 'add', '--sparse', '--', CONFLICT_PATH)
    receipt['expectedOriginalMergeConflict'] = proof
    return proof


def gate_once(commands, receipt, label, tree, output):
    require(not output.exists(), 'Original gate output already exists')
    launcher = 'import os,runpy,sys;root,script=sys.argv[1:3];os.chdir(root);sys.argv=sys.argv[2:];runpy.run_path(script,run_name="__main__")'
    commands.run(label, PRE + ['python3', '-B', '-c', launcher, str(ROOT), str(ROOT / GATE), '--base',
                 '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(output)], timeout=120)
    raw = read_regular(output)
    result = json.loads(raw)
    require(result['sourceRetentionPassed'] is True and len(result['reviewedRefactors']) == 133,
            'Original source-retention gate did not qualify all133 rows')
    receipt.setdefault('sourceRetentionGates', []).append({'label': label, 'tree': tree, 'path': str(output),
        'bytes': len(raw), 'sha256': sha(raw), 'sourceRetentionPassed': True, 'reviewedRefactors': 133})
    return raw


def generated_evidence_is_whitespace_clean(raw):
    require(not raw.endswith(b'\n\n')
            and all(not line.endswith((b' ', b'\t', b'\r')) for line in raw.split(b'\n')),
            'Generated source evidence introduces unreviewed whitespace diagnostics')


def integrate(commands, receipt, payload, rows, values, prior_raw, prior):
    sdk_publication = validate_sdk_publication(payload)
    require(commands.git('original-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [START, START_TREE]
            and commands.git('original-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF,
            'Original integration HEAD/tree/branch differs')
    merge_head = Path(commands.git('merge-state-path', 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD').decode().strip())
    require(not merge_head.exists(), 'Existing merge must be preserved')
    original = original_status(commands, 'original')
    exact_remote(commands, 'original-remote', START)
    original_index_path = Path(commands.git('original-index-path', 'rev-parse', '--path-format=absolute', '--git-path', 'index').decode().strip())
    original_index = optional_file_identity(original_index_path)
    base_leaves = tree_leaves(commands, 'complete-start-tree', START_TREE)
    preimages = {}
    for path, row in rows.items():
        require_leaf(base_leaves, path, row['before'])
        old = None if row['before'] is None else base64.b64decode(row['beforeBase64'], validate=True)
        destination_preflight(path, old, may_be_sparse=True)
        if old is not None:
            preimages[row['before']['gitBlob']] = old
    batch_blobs(commands, 'all-original-start-preimages', preimages)
    donor_oids = validate_donors(commands, payload, base_leaves)
    first_leaves = expected_leaves(base_leaves, payload['firstMergeRows'])
    donor_leaves = expected_leaves(base_leaves, payload['donorRows'])
    final_leaves = expected_leaves(base_leaves, rows)
    before_guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'before')
    receipt['resourceBeforeObjects'] = resources()
    commands.run('create-exclusive-private-index', PRE + ['python3', '-B', '-c',
                 'import os,sys;os.mkdir(sys.argv[1],0o700)', str(PRIVATE)])
    existing_oids = {row['sha'] for row in base_leaves.values() if row['type'] == 'blob'} | donor_oids
    write_new_objects(commands, rows, values, existing_oids)
    first_tree = private_tree(commands, 'first-merge-preview', base_leaves, payload['firstMergeRows'], first_leaves)
    donor_tree = private_tree(commands, 'all-donor-preview', base_leaves, payload['donorRows'], donor_leaves)
    final_tree = private_tree(commands, 'final-source-preview', base_leaves, rows, final_leaves)
    for label, tree, key in [('first-source-diff', first_tree, 'first'), ('all-donor-source-diff', donor_tree, 'donors'),
                             ('final-source-diff', final_tree, 'source')]:
        diff_check(commands, label, ['diff', '--check', '--no-renames', START, tree], payload['diffChecks'][key], receipt)
    first_guards = validate_guards(commands, payload, base_leaves, first_leaves, prior, 'first')
    final_guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'after')
    gate_row = base_leaves[GATE]
    require(gate_row == first_leaves[GATE] == final_leaves[GATE] and gate_row['type'] == 'blob', 'Original retention gate changed')
    gate = batch_blobs(commands, 'original-retention-gate-source', {gate_row['sha']: None})[gate_row['sha']]
    require(read_regular(ROOT / GATE) == gate, 'Working original retention gate differs')
    require(commands.git('premerge-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [START, START_TREE]
            and commands.git('premerge-index-tree', 'write-tree').decode().strip() == START_TREE,
            'Original HEAD or index advanced before mutation')
    require(original_status(commands, 'premerge') == original and optional_file_identity(original_index_path) == original_index,
            'Original source/index/untracked custody changed before mutation')
    exact_remote(commands, 'premerge-remote', START)
    receipt.update(phase='FIRST_NORMAL_INSPECTOR_MERGE', expectedFirstTree=first_tree,
                   expectedDonorTree=donor_tree, expectedSourceTree=final_tree)
    resources()
    conflict_proof = merge_known_inspector_conflict(commands, receipt, payload, merge_head, first_leaves)
    require(commands.git('resolved-first-index-tree', 'write-tree').decode().strip() == first_tree
            and tree_leaves(commands, 'resolved-first-complete-leaves', first_tree) == first_leaves,
            'Complete first resolution differs from the predicted full tree')
    require(commands.git('first-unstaged-check', 'diff', '--name-only') == b'', 'Unstaged first-merge source differs')
    require(commands.git('first-untracked-check', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Original untracked paths changed')
    diff_check(commands, 'first-actual-index-diff', ['diff', '--cached', '--check', '--no-renames', START], payload['diffChecks']['first'], receipt)
    require(validate_guards(commands, payload, base_leaves, first_leaves, prior, 'first') == first_guards,
            'First staged pin guards differ')
    receipt['phase'] = 'FIRST_ORIGINAL133_RETENTION_GATE'
    first_gate_raw = gate_once(commands, receipt, 'first-original-retention-gate', first_tree, FIRST_GATE_OUT)
    require(commands.git('first-precommit-head', 'rev-parse', 'HEAD').decode().strip() == START
            and commands.git('first-precommit-index', 'write-tree').decode().strip() == first_tree,
            'First source changed during original retention gate')
    commands.git('normal-two-parent-inspector-commit', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'commit', '-F', '-', data=payload['firstCommitMessage'].encode(), timeout=45)
    first_head = commands.git('first-committed-head', 'rev-parse', 'HEAD').decode().strip()
    receipt['firstMergeCommit'] = first_head
    require(commands.git('first-committed-parent-tree', 'show', '-s', '--format=%T %P', first_head).decode().split()
            == [first_tree, START, DONORS[0]], 'First normal two-parent merge ancestry differs')
    require(original_status(commands, 'first-committed') == original and not merge_head.exists(),
            'First committed source or original untracked custody differs')

    self_raw = read_regular(Path(__file__))
    original_controller_leaf = base_leaves[ORIGINAL_CONTROLLER_PATH]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Actual288 original controller not retained in START')
    original_controller = batch_blobs(commands, 'actual288-original-controller',
        {original_controller_leaf['sha']: None})[original_controller_leaf['sha']]
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA, 'Original394 complete controller differs')
    intake = {'schema': 'pinkha-root-inspector-native26-host-source-intake/v1', 'start': START, 'startTree': START_TREE,
        'firstMergeCommit': first_head, 'firstTree': first_tree, 'secondMergeParents': [first_head, *DONORS[1:]],
        'donorTips': DONORS, 'donorTree': donor_tree, 'finalSourceTree': final_tree,
        'files': {path: {key: value for key, value in row.items() if key not in ('base64', 'beforeBase64')} for path, row in rows.items()},
        'controllerSHA256': sha(self_raw), 'payloadSHA256': PAYLOAD_SHA, 'positivePrior288ReceiptSHA256': sha(prior_raw),
        'originalUntrackedFiles': list(UNTRACKED), 'originalUntrackedGroupedStatus': original['grouped'].decode(),
        'originalUntrackedFileIdentities': original['files'], 'inputPins': before_guards, 'firstPins': first_guards, 'outputPins': final_guards,
        'originalExpectedConflictExit': 1, 'originalConflictProofSHA256': sha(encoded(conflict_proof)),
        'firstOriginalGateSHA256': sha(first_gate_raw), 'originalDiffChecks': payload['diffChecks'],
        'runtimeAcceptance': False, 'compilerInvocations': 0, 'testsExecuted': 0, 'materializations': 0}
    evidence = {'root-source-intake.json': encoded(intake), 'root-integration-controller.py': self_raw,
        'prior288-integration.original.json': prior_raw, 'original-final-sdk-publication.json': sdk_publication,
        'actual-first-merge-conflict-proof.json': encoded(conflict_proof), 'actual-first-source-retention.json': first_gate_raw,
        'root-controller-full-original-inverse.json': encoded(controller_inverse(original_controller, self_raw))}
    for name, item in payload['evidence'].items():
        safe_path(name)
        require(name not in evidence, 'Root evidence collision')
        data = base64.b64decode(item['base64'], validate=True)
        match(data, item['after'])
        evidence[name] = data
    evidence_rows, evidence_values = {}, {}
    for name, data in evidence.items():
        path = PREFIX + '/' + name
        require(path not in rows and path not in base_leaves, 'Root evidence destination already exists')
        destination_preflight(path, None)
        if name not in payload['evidence']:
            generated_evidence_is_whitespace_clean(data)
        evidence_rows[path] = {'status': 'A', 'before': None, 'beforeBase64': None,
            'after': {'bytes': len(data), 'sha256': sha(data), 'gitBlob': blob(data), 'gitMode': '100644'}}
        evidence_values[path] = data
    all_rows = {**rows, **evidence_rows}
    whole_leaves = expected_leaves(base_leaves, all_rows)
    write_new_objects(commands, evidence_rows, evidence_values, existing_oids)
    whole_tree = private_tree(commands, 'complete-final-preview', base_leaves, all_rows, whole_leaves)
    diff_check(commands, 'complete-final-preview-diff', ['diff', '--check', '--no-renames', START, whole_tree], payload['diffChecks']['complete'], receipt)
    require(commands.git('second-premerge-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [first_head, first_tree]
            and commands.git('second-premerge-index-tree', 'write-tree').decode().strip() == first_tree
            and original_status(commands, 'second-premerge') == original, 'First local merge changed before second normal merge')
    exact_remote(commands, 'second-premerge-remote', START)
    receipt.update(phase='SECOND_NORMAL_DISJOINT_MERGE', expectedTree=whole_tree)
    resources()
    commands.git('normal-d528-host-two-tip-merge', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'merge', '--no-ff', '--no-commit', *DONORS[1:], timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS[1:], 'Second normal merge parents differ')
    require(commands.git('actual-all-donor-stage', 'write-tree').decode().strip() == donor_tree
            and tree_leaves(commands, 'actual-all-donor-leaves', donor_tree) == donor_leaves,
            'Disjoint second merge differs; preserve all state without automatic resolution')
    control_preimages = {}
    for path, row in payload['controlRows'].items():
        require_leaf(donor_leaves, path, row['before'])
        previous = None if row['before'] is None else base64.b64decode(row['beforeBase64'], validate=True)
        destination_preflight(path, previous, may_be_sparse=True)
        control_preimages[path] = previous
    batch_blobs(commands, 'all-exact-control-stage-preimages',
                {payload['controlRows'][path]['before']['gitBlob']: data for path, data in control_preimages.items() if data is not None})
    write_owned_batch(commands, 'write-exact38-closed-controls', payload['controlRows'], values, control_preimages)
    commands.git('stage-only-exact38-controls', 'add', '--sparse', '--', *sorted(payload['controlRows']))
    require(commands.git('actual-final-source-stage', 'write-tree').decode().strip() == final_tree,
            'Closed source/control stage differs from full private preview')
    write_owned_batch(commands, 'write-exclusive-root-evidence', evidence_rows, evidence_values, {path: None for path in evidence_rows})
    commands.git('stage-only-exact-root-evidence', 'add', '--sparse', '--', *sorted(evidence_rows))
    require(commands.git('actual-complete-stage', 'write-tree').decode().strip() == whole_tree,
            'Complete staged tree differs from full predicted tree')
    require(changes(commands, 'actual-complete-path-diff', START, whole_tree) == {path: row['status'] for path, row in all_rows.items()},
            'Unexpected complete source path')
    require(commands.git('second-unstaged-check', 'diff', '--name-only') == b''
            and commands.git('second-untracked-check', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Staged source or original untracked paths changed')
    diff_check(commands, 'second-actual-index-diff', ['diff', '--cached', '--check', '--no-renames', START], payload['diffChecks']['complete'], receipt)
    require(validate_guards(commands, payload, base_leaves, whole_leaves, prior, 'after') == final_guards,
            'Final actual stage pin guards differ')
    receipt['phase'] = 'SECOND_ORIGINAL133_RETENTION_GATE'
    final_gate_raw = gate_once(commands, receipt, 'second-original-retention-gate', whole_tree, GATE_OUT)
    require(commands.git('final-precommit-head', 'rev-parse', 'HEAD').decode().strip() == first_head
            and commands.git('final-precommit-index', 'write-tree').decode().strip() == whole_tree,
            'Final source changed during original retention gate')
    require(commands.git('final-precommit-untracked', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Original untracked paths changed during final gate')
    receipt['phase'] = 'NORMAL_THREE_PARENT_FINAL_COMMIT'
    commands.git('normal-three-parent-final-commit', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'commit', '-F', '-', data=payload['finalCommitMessage'].encode(), timeout=45)
    head = commands.git('final-committed-head', 'rev-parse', 'HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree', 'show', '-s', '--format=%T %P', head).decode().split()
            == [whole_tree, first_head, *DONORS[1:]], 'Final normal three-parent merge ancestry differs')
    require(original_status(commands, 'committed') == original and not merge_head.exists(), 'Committed source/untracked custody differs')
    require(commands.git('committed-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF, 'Original final branch changed')
    exact_remote(commands, 'prepush-remote', START)
    receipt.update(tree=whole_tree, donorTips=DONORS, files=sorted(all_rows), sourceRetentionPassed=True, reviewedRefactors=133,
        retentionSHA256=sha(final_gate_raw), inputPins=before_guards, outputPins=final_guards, originalUntrackedPreserved=True,
        localMergeCommits=[{'head': first_head, 'tree': first_tree, 'parents': [START, DONORS[0]]},
                           {'head': head, 'tree': whole_tree, 'parents': [first_head, *DONORS[1:]]}])
    receipt['phase'] = 'ONE_NORMAL_NONFORCE_PUSH'
    resources()
    commands.git('normal-exact-final-source-push', 'push', '--porcelain', '--no-follow-tags', 'origin', head + ':' + REF,
                 publish=True, timeout=90)
    receipt['normalPushCompleted'] = True
    exact_remote(commands, 'published-exact-readback', head)
    receipt['normalPushReadback'] = head
    require(original_status(commands, 'published') == original, 'Published worktree custody differs')
    receipt['state'] = 'SOURCE_TWO_NORMAL_MERGES_PUBLISHED_RUNTIME_CLOSED'


def main():
    # Unbound source must stop before any evidence, process or host mutation.
    raw, packed, payload, rows, values = source_payload()
    require(os.geteuid() == 0 and sys.platform.startswith('linux'), 'Existing Oracle root context required')
    require(ROOT.resolve() == ROOT and ROOT.is_dir(), 'Exact existing integration worktree required')
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        require(not os.environ.get(name), 'Inherited Git override is not admitted')
    for path in (EVIDENCE, PRIVATE, OUT, FIRST_GATE_OUT, GATE_OUT):
        no_symlinks(path)
        require(not path.exists(), 'Exclusive operation already has state; inspect without rerun: ' + str(path))
    prior_raw, prior = prior_receipt()
    resource = resources()
    EVIDENCE.mkdir(mode=0o700)
    receipt = {'schema': 'pinkha-root-inspector-native26-host-source-integration/v1', 'state': 'RUNNING',
               'startedAt': time.time(), 'start': START, 'startTree': START_TREE, 'commands': [],
               'controllerSHA256': sha(read_regular(Path(__file__))), 'payloadSHA256': sha(raw),
               'packedPayloadSHA256': sha(packed), 'positivePriorReceiptSHA256': sha(prior_raw),
               'resourceBefore': resource, 'firstFailure': None, 'runtimeAcceptance': False,
               'compilerInvocations': 0, 'testsExecuted': 0, 'materializations': 0}
    exclusive(EVIDENCE / 'started.json', encoded(receipt))
    commands = Commands(receipt)
    def interrupted(signum, frame):
        commands.interrupted_signal = signum
        commands.blocked = True
        if not commands.in_cleanup:
            raise TimeoutError('Source integration interrupted by signal ' + str(signum))
    old_handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
    for sig in old_handlers:
        signal.signal(sig, interrupted)
    signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS)
    first = None
    try:
        integrate(commands, receipt, payload, rows, values, prior_raw, prior)
    except BaseException as error:
        first = error
        receipt['state'] = 'FAILED_PRESERVED_NO_AUTOMATIC_RESET'
        receipt['firstFailure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        receipt['finishedAt'] = time.time()
        receipt['commandCustodyBlocked'] = commands.blocked
        try:
            terminal = encoded(receipt)
            exclusive(EVIDENCE / 'receipt.json', terminal)
            exclusive(OUT, terminal)
        except BaseException as error:
            receipt['terminalReceiptFailure'] = {'type': type(error).__name__, 'message': str(error)}
            if first is None:
                first = error
                receipt['firstFailure'] = receipt['terminalReceiptFailure']
                receipt['state'] = 'FAILED_TERMINAL_RECEIPT'
            try:
                exclusive(EVIDENCE / 'terminal-receipt-failure.json', encoded(receipt))
            except BaseException:
                pass
        print(json.dumps({'state': receipt['state'], 'head': receipt.get('head'), 'tree': receipt.get('tree'),
                          'receipt': str(OUT), 'firstFailure': receipt['firstFailure'],
                          'commandCustodyBlocked': commands.blocked}), flush=True)
    if first is not None:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
