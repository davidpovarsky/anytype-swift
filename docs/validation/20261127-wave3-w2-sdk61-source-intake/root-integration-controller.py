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
START = '2752229aacf72f468f32a4bfe5fe0a91142f5dbe'
START_TREE = '2d8db7a1585d48b857578920fa19b3730dde488b'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['f2fad4d9b07d49406bb8c20c838817fd9bc5ae8a',
          '9986f60d8e56d3835d755f1ed07b7255766d3451',
          '1a890015578962bc6eab8c6e9bb70c51ce189cf3']
PRIOR = Path('/tmp/pinkha-root-e-properties-app10-t5-source-integration-20261127.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-w2-sdk61-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-w2-sdk61-source-integration-20261127-attempt2')
PRIVATE = Path('/tmp/pinkha-root-w2-sdk61-source-index-20261127-attempt2')
OUT = Path('/tmp/pinkha-root-w2-sdk61-source-integration-20261127-attempt2.json')
PREFIX = 'docs/validation/20261127-wave3-w2-sdk61-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-w2-sdk61-source-retention-20261127-attempt2.json')
PACKED_BYTES = 3222015
PACKED_SHA = 'acf36d868aa2c6d5cf298b4ead01a5789ce3f23993ab44a2f0d7062627cb6ff7'
PAYLOAD_BYTES = 12748999
PAYLOAD_SHA = '348959c6ba94bca61febac0a570179933bd0488db556048314fa9ca6ac974bee'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2


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
    raw = read_regular(PRIOR, 77549)
    require(len(raw) == 77549 and sha(raw) == '5fb21559add1833d5b964620534e0cf59bf781ad4d888bba13faf1b8b0d010c2',
            'Actual positive275 original receipt changed')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-e-properties-app10-t5-source-integration/v1'
            and value['state'] == 'SOURCE_MERGED_E_DISABLED_APP10_T5_CLOSED_RUNTIME_PENDING'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['parent'] == '919626d8a5a2701c2dfb56277a657fa593700b98'
            and value['controllerSHA256'] == 'd5643f83d402d37feb6eca79d3a03852a1a2ba8ff34f424c235b327bf7174d82'
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 132
            and value['pushExit'] == 0 and value['newTestsExecuted'] == 0
            and value['eFactoryActivated'] is False and value['runtimeActivated'] is False,
            'Prior actual275 source/closed-runtime qualification differs')
    return raw, value


def source_payload():
    require(PACKED_BYTES is not None and PAYLOAD_BYTES is not None
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA or '')
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA or ''), 'Final payload is unbound; no host action')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed source payload differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Complete source payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-w2-sdk61-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE
            and value['donorTips'] == DONORS and value['rootCompositionPending'] is False,
            'Closed source tuple differs')
    require(value['runtimeAcceptance'] is False, 'Source payload cannot activate runtime acceptance')
    require(len(value['donorRows']) == 210 and len(value['donorLinks']) == 5, 'Exact donor closure differs')
    donor_values = decode_rows(value['donorRows'])
    root_values = decode_rows(value['rootRows'])
    rows = dict(value['donorRows'])
    rows.update(value['rootRows'])
    values = {**donor_values, **root_values}
    require(len(rows) == value['finalSourcePathCount'], 'Final finite path count differs')
    for path, row in value['rootRows'].items():
        stage = value['donorRows'][path]['after'] if path in value['donorRows'] else row['before']
        require(row['stageBefore'] == stage, 'Wrong root override stage preimage: ' + path)
        if stage is None:
            require(row['stageBeforeBase64'] is None, 'Addition has staged bytes')
        else:
            match(base64.b64decode(row['stageBeforeBase64'], validate=True), stage)
        if path in value['donorRows']:
            require(row['before'] == value['donorRows'][path]['before']
                    and row['beforeBase64'] == value['donorRows'][path]['beforeBase64']
                    and row['status'] == value['donorRows'][path]['status'], 'Root override changed original START identity')
    return raw, packed, value, rows, values


def validate_donors(commands, payload, start_leaves):
    # Fetch only the three published immutable tips, without remote ref mapping.
    commands.git('fetch-three-exact-donor-tips', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    links = {row['commit']: row for row in payload['donorLinks']}
    require(len(links) == 5, 'Duplicate donor commit')
    reached = set()
    external = set()
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
    require(reached == set(links), 'Unrelated donor evidence or missing donor link')
    for index, parent in enumerate(sorted(external)):
        commands.git('donor-base-already-integrated-%02d' % index, 'merge-base', '--is-ancestor', parent, START)
    blobs = {}
    union = set()
    for index, link in enumerate(payload['donorLinks']):
        result = commands.git('donor-identity-%02d' % index, 'show', '-s', '--format=%H %T %P', link['commit']).decode().split()
        require(result == [link['commit'], link['tree'], *link['parents']] and len(link['parents']) == 1,
                'Published donor commit/tree/parent changed')
        actual = changes(commands, 'donor-complete-diff-%02d' % index, link['parents'][0], link['commit'])
        require(actual == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed donor ancestry source')
        leaves = tree_leaves(commands, 'donor-complete-tree-%02d' % index, link['tree'])
        for path, row in link['files'].items():
            require_leaf(leaves, safe_path(path), row['after'])
            blobs[row['after']['gitBlob']] = None
        union.update(link['files'])
    require(union == set(payload['donorRows']), 'Published five-link union differs from exact210')
    original_bytes = batch_blobs(commands, 'original-donor-and-start-blobs', blobs)
    for link in payload['donorLinks']:
        for row in link['files'].values():
            match(original_bytes[row['after']['gitBlob']], row['after'])
    for path, row in payload['donorRows'].items():
        require_leaf(start_leaves, path, row['before'])
        require(row['after']['gitBlob'] in blobs
                and original_bytes[row['after']['gitBlob']] == base64.b64decode(row['base64'], validate=True),
                'Final donor row is not original published bytes')


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


def validate_guards(commands, payload, before_leaves, final_leaves, prior, stage):
    # Bound guard inputs will be supplied with the final reviewed root payload.
    # All source bytes are read by their actual Git object identities, not from
    # a fabricated temporary checkout or reconstructed current account state.
    guards = payload['guardInputs']
    require(guards['originalRetentionRows'] == 132 and guards['expectedRetentionRows'] in (132, 133),
            'Original132 retention or bounded optional append changed')
    expected = guards['beforeFiles'] if stage == 'before' else guards['afterFiles']
    leaves = before_leaves if stage == 'before' else final_leaves
    values = batch_blobs(commands, 'guard-' + stage + '-original-files',
                         {row['gitBlob']: None for row in expected.values()})
    for path, row in expected.items():
        require_leaf(leaves, path, row)
        match(values[row['gitBlob']], row)
    for path, row in guards['unchangedFiles'].items():
        require_leaf(before_leaves, path, row)
        require_leaf(final_leaves, path, row)
    map_path = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
    old_map_raw = base64.b64decode(guards['sourceMapBeforeBase64'], validate=True)
    new_map_raw = base64.b64decode(guards['sourceMapAfterBase64'], validate=True)
    match(old_map_raw, guards['beforeFiles'][map_path])
    match(new_map_raw, guards['afterFiles'][map_path])
    old_map = json.loads(old_map_raw)
    new_map = json.loads(new_map_raw)
    require(len(old_map['changes']) == 132 and len(new_map['changes']) == guards['expectedRetentionRows'],
            'Source map row count differs')
    require({key: value for key, value in old_map.items() if key != 'changes'}
            == {key: value for key, value in new_map.items() if key != 'changes'}, 'Source map envelope changed')
    updates = guards['sourceMapUpdates']
    require(len({row['index'] for row in updates}) == len(updates), 'Duplicate source-map override')
    changed = {row['index'] for row in updates}
    require(changed == {17, 102}, 'Only the two reviewed existing source-map rows may change')
    for index, old in enumerate(old_map['changes']):
        new = new_map['changes'][index]
        require(all(new.get(key) == old.get(key) for key in ('kind', 'from', 'to', 'baselineBlob')),
                'Original retention baseline/path/kind changed')
        if index not in changed:
            require(new == old, 'Unreviewed original map row changed')
        else:
            row = next(value for value in updates if value['index'] == index)
            require(old == row['before'] and new == row['after'], 'Exact source-map reviewed row differs')
            field = 'sharedSources' if index == 17 else 'replacementBlob'
            require({key: value for key, value in old.items() if key != field}
                    == {key: value for key, value in new.items() if key != field},
                    'Reviewed source-map update changes another field')
            if index == 17:
                require(len(old[field]) == len(new[field])
                        and all({key: value for key, value in a.items() if key != 'gitBlob'}
                                == {key: value for key, value in b.items() if key != 'gitBlob'}
                                for a, b in zip(old[field], new[field])),
                        'Original shared-source paths/metadata changed')
    require(new_map['changes'][132:] == guards['sourceMapAppendedRows'], 'Unreviewed added source-map row')
    sdk_path = 'Tools/Hanlin/source.json'
    old_sdk_raw = base64.b64decode(guards['sdkBeforeBase64'], validate=True)
    new_sdk_raw = base64.b64decode(guards['sdkAfterBase64'], validate=True)
    match(old_sdk_raw, guards['beforeFiles'][sdk_path])
    match(new_sdk_raw, guards['afterFiles'][sdk_path])
    old_sdk = json.loads(old_sdk_raw)
    new_sdk = json.loads(new_sdk_raw)
    require(old_sdk['revision'] == '4cb6454c1c6e110ead73179c06ada9e909bf250b'
            and new_sdk['revision'] == guards['sdkRevision']
            and {key: value for key, value in old_sdk.items() if key != 'revision'}
                == {key: value for key, value in new_sdk.items() if key != 'revision'}, 'SDK manifest changes exceed exact revision')
    require(sdk_path in guards['beforeFiles'] and sdk_path in guards['afterFiles'], 'SDK source pin guard missing')
    register_path = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
    register_before = base64.b64decode(guards['registerBeforeBase64'], validate=True)
    register_after = base64.b64decode(guards['registerAfterBase64'], validate=True)
    match(register_before, guards['beforeFiles'][register_path])
    match(register_after, guards['afterFiles'][register_path])
    require(register_after.startswith(register_before) and len(register_after) > len(register_before),
            'Original exception register prefix was not preserved')
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    require(lock_path in guards['unchangedFiles'], 'Original56-lock preservation missing')
    lock = batch_blobs(commands, 'guard-' + stage + '-original-lock', {guards['unchangedFiles'][lock_path]['gitBlob']: None})
    pin_values = json.loads(next(iter(lock.values())))['pins']
    require(pin_values == prior['inputPins']['allPackagePins'] and len(pin_values) == 56,
            'Original Kit26/55 other locked package identities changed')
    activation = guards['closedActivation']
    require(activation and all(row['path'] in guards['afterFiles'] for row in activation),
            'Closed control inputs are not actual final guarded source')
    if stage == 'after':
        for row in activation:
            data = json.loads(values[expected[row['path']]['gitBlob']])
            for key, wanted in row['fields'].items():
                require(data[key] == wanted and type(data[key]) is type(wanted), 'Runtime activation scope changed')
    return {'sdk': old_sdk['revision'] if stage == 'before' else new_sdk['revision'],
            'allPackagePins': pin_values, 'reviewedRefactors': guards['expectedRetentionRows'],
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
    raw_preimages = {}
    for path, row in rows.items():
        require_leaf(base_leaves, path, row['before'])
        old = None if row['before'] is None else base64.b64decode(row['beforeBase64'], validate=True)
        destination_preflight(path, old, may_be_sparse=True)
        if old is not None:
            raw_preimages[row['before']['gitBlob']] = old
    batch_blobs(commands, 'all-original-start-preimages', raw_preimages)
    validate_donors(commands, payload, base_leaves)
    donor_leaves = expected_leaves(base_leaves, payload['donorRows'])
    final_leaves = expected_leaves(base_leaves, rows)
    before_guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'before')
    receipt['resourceBeforeObjects'] = resources()
    commands.run('create-exclusive-private-index', PRE + ['python3', '-B', '-c',
                 'import os,sys;os.mkdir(sys.argv[1],0o700)', str(PRIVATE)])
    existing_oids = {row['sha'] for row in base_leaves.values() if row['type'] == 'blob'}
    existing_oids.update(row['after']['gitBlob'] for row in payload['donorRows'].values())
    write_new_objects(commands, payload['rootRows'], values, existing_oids)
    donor_tree = private_tree(commands, 'donor-preview', base_leaves, payload['donorRows'], donor_leaves)
    final_tree = private_tree(commands, 'final-source-preview', base_leaves, rows, final_leaves)
    diff_check(commands, 'source-preview-diff-check', ['diff', '--check', START, final_tree], payload['diffCheck'], receipt)
    guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'after')
    self_raw = read_regular(Path(__file__))
    original_controller_path = 'docs/validation/20261127-wave3-e-properties-app10-t5-intake/root-integration-controller.py'
    original_controller_leaf = base_leaves[original_controller_path]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Prior actual integration controller is not retained in START')
    original_controller = batch_blobs(commands, 'prior-actual-controller-original',
                                     {original_controller_leaf['sha']: None})[original_controller_leaf['sha']]
    require(sha(original_controller) == 'd5643f83d402d37feb6eca79d3a03852a1a2ba8ff34f424c235b327bf7174d82',
            'Prior actual complete controller source differs')
    intake = {'schema': 'pinkha-root-w2-sdk61-source-intake/v1', 'start': START, 'startTree': START_TREE,
              'donors': DONORS, 'donorTree': donor_tree, 'finalSourceTree': final_tree,
              'files': {path: {key: value for key, value in row.items() if key not in ('base64', 'beforeBase64', 'stageBeforeBase64')}
                        for path, row in rows.items()},
              'controllerSHA256': sha(self_raw), 'payloadSHA256': PAYLOAD_SHA,
              'positivePriorReceiptSHA256': sha(prior_raw),
              'originalUntrackedFiles': list(UNTRACKED),
              'originalUntrackedGroupedStatus': original['grouped'].decode(),
              'originalUntrackedFileIdentities': original['files'],
              'allUntrackedPathListSHA256': sha(original['untracked']),
              'inputGuards': before_guards, 'outputGuards': guards,
              'sourceDiffCheck': payload['diffCheck'], 'runtimeAcceptance': False,
              'compilerInvocations': 0, 'testsExecuted': 0, 'materializations': 0}
    evidence = {'root-source-intake.json': encoded(intake), 'root-integration-controller.py': self_raw,
                'prior275-integration.original.json': prior_raw,
                'original-final-sdk-publication.json': sdk_publication}
    for name, row in payload['evidence'].items():
        safe_path(name)
        require(name not in evidence, 'Root evidence collision')
        value = base64.b64decode(row['base64'], validate=True)
        match(value, row['after'])
        evidence[name] = value
    require('root-controller-full-original-inverse.json' not in evidence, 'Generated inverse path collision')
    evidence['root-controller-full-original-inverse.json'] = encoded(controller_inverse(original_controller, self_raw))
    evidence_rows = {}
    evidence_values = {}
    for name, raw in evidence.items():
        path = PREFIX + '/' + name
        require(path not in rows and path not in base_leaves, 'Root evidence path already exists')
        destination_preflight(path, None)
        evidence_rows[path] = {'status': 'A', 'before': None, 'beforeBase64': None,
            'after': {'bytes': len(raw), 'sha256': sha(raw), 'gitBlob': blob(raw), 'gitMode': '100644'}}
        evidence_values[path] = raw
    all_rows = {**rows, **evidence_rows}
    all_values = {**values, **evidence_values}
    write_new_objects(commands, evidence_rows, evidence_values, existing_oids)
    whole_leaves = expected_leaves(base_leaves, all_rows)
    whole_tree = private_tree(commands, 'complete-preview', base_leaves, all_rows, whole_leaves)
    diff_check(commands, 'complete-preview-diff-check', ['diff', '--check', START, whole_tree], payload['completeDiffCheck'], receipt)
    gate_row = base_leaves[GATE]
    require(gate_row == whole_leaves[GATE] and gate_row['type'] == 'blob', 'Original source-retention gate changed')
    gate = batch_blobs(commands, 'original-retention-gate', {gate_row['sha']: None})[gate_row['sha']]
    require(read_regular(ROOT / GATE) == gate, 'Working original source-retention gate differs')
    require(commands.git('premerge-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [START, START_TREE]
            and commands.git('premerge-index-tree', 'write-tree').decode().strip() == START_TREE,
            'Original HEAD or index advanced before mutation')
    require(original_status(commands, 'premerge') == original and optional_file_identity(original_index_path) == original_index,
            'Original source/index/untracked custody changed before mutation')
    exact_remote(commands, 'premerge-remote', START)
    receipt.update(phase='NORMAL_THREE_TIP_MERGE', expectedDonorTree=donor_tree,
                   expectedSourceTree=final_tree, expectedTree=whole_tree)
    resources()
    commands.git('normal-three-tip-merge', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'merge', '--no-ff', '--no-commit', *DONORS, timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS, 'Normal merge parents differ')
    require(commands.git('actual-donor-stage', 'write-tree').decode().strip() == donor_tree,
            'Actual donor merge differs; preserve it without automatic resolution/reset')
    require(tree_leaves(commands, 'actual-donor-leaves', donor_tree) == donor_leaves, 'Actual complete donor source differs')
    stage_bytes = {}
    for path, row in payload['rootRows'].items():
        require_leaf(donor_leaves, path, row['stageBefore'])
        previous = None if row['stageBefore'] is None else base64.b64decode(row['stageBeforeBase64'], validate=True)
        destination_preflight(path, previous, may_be_sparse=True)
        stage_bytes[path] = previous
    expected_stage_blobs = {payload['rootRows'][path]['stageBefore']['gitBlob']: raw
                            for path, raw in stage_bytes.items() if raw is not None}
    batch_blobs(commands, 'all-actual-staged-root-preimages', expected_stage_blobs)
    write_owned_batch(commands, 'write-exact-root-overrides', payload['rootRows'], values, stage_bytes)
    commands.git('stage-only-root-overrides', 'add', '--sparse', '--', *sorted(payload['rootRows']))
    require(commands.git('actual-final-source-stage', 'write-tree').decode().strip() == final_tree,
            'Root source overrides differ from full START preview')
    write_owned_batch(commands, 'write-exclusive-root-evidence', evidence_rows, evidence_values,
                      {path: None for path in evidence_rows})
    commands.git('stage-only-exact-evidence', 'add', '--sparse', '--', *sorted(evidence_rows))
    require(commands.git('actual-complete-stage', 'write-tree').decode().strip() == whole_tree,
            'Complete staged tree differs from full private preview')
    require(changes(commands, 'actual-staged-complete-diff', START, whole_tree)
            == {path: row['status'] for path, row in all_rows.items()}, 'Unexpected complete staged path')
    require(commands.git('unstaged-source-check', 'diff', '--name-only') == b'', 'Unstaged source differs')
    require(commands.git('untracked-after-staging', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Original untracked paths changed')
    diff_check(commands, 'actual-index-diff-check', ['diff', '--cached', '--check'], payload['completeDiffCheck'], receipt)
    require(validate_guards(commands, payload, base_leaves, whole_leaves, prior, 'after') == guards, 'Staged pin guards differ')
    receipt['phase'] = 'ORIGINAL_SOURCE_RETENTION_GATE'
    require(not GATE_OUT.exists(), 'Original gate output already exists')
    gate_launcher = 'import os,runpy,sys;root,script=sys.argv[1:3];os.chdir(root);sys.argv=sys.argv[2:];runpy.run_path(script,run_name="__main__")'
    commands.run('original-retention-gate', PRE + ['python3', '-B', '-c', gate_launcher, str(ROOT), str(ROOT / GATE), '--base',
                 '586c98bcc17dee425664224e508fc0e8df277678', '--ref', whole_tree, '--output', str(GATE_OUT)], timeout=120)
    gate_result_raw = read_regular(GATE_OUT)
    gate_result = json.loads(gate_result_raw)
    require(gate_result['sourceRetentionPassed'] is True
            and len(gate_result['reviewedRefactors']) == payload['guardInputs']['expectedRetentionRows'],
            'Original source-retention gate did not qualify all reviewed rows')
    require(commands.git('precommit-unchanged-head', 'rev-parse', 'HEAD').decode().strip() == START
            and commands.git('precommit-exact-index', 'write-tree').decode().strip() == whole_tree,
            'Source changed during retention verification')
    require(commands.git('precommit-untracked', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Original untracked paths changed during gate')
    receipt['phase'] = 'NORMAL_MERGE_COMMIT'
    commands.git('normal-reviewed-merge-commit', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'commit', '-F', '-', data=payload['commitMessage'].encode(), timeout=45)
    head = commands.git('committed-source-head', 'rev-parse', 'HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('committed-parent-tree', 'show', '-s', '--format=%T %P', head).decode().split()
            == [whole_tree, START, *DONORS], 'Normal complete merge ancestry/tree differs')
    require(original_status(commands, 'committed') == original, 'Original untracked or tracked clean state differs after commit')
    require(commands.git('committed-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF, 'Original integration branch changed')
    exact_remote(commands, 'prepush-remote', START)
    receipt.update(tree=whole_tree, donorTips=DONORS, files=sorted(all_rows), sourceRetentionPassed=True,
                   reviewedRefactors=len(gate_result['reviewedRefactors']), retentionSHA256=sha(gate_result_raw),
                   inputPins=before_guards, outputPins=guards, originalUntrackedPreserved=True)
    receipt['phase'] = 'NORMAL_NONFORCE_PUSH'
    resources()
    commands.git('normal-exact-source-push', 'push', '--porcelain', '--no-follow-tags', 'origin', head + ':' + REF,
                 publish=True, timeout=90)
    receipt['normalPushCompleted'] = True
    exact_remote(commands, 'published-exact-readback', head)
    receipt['normalPushReadback'] = head
    require(original_status(commands, 'published') == original, 'Published worktree custody differs')
    receipt['state'] = 'SOURCE_MERGED_PUBLISHED_RUNTIME_CLOSED'


def main():
    # Unbound source must stop before any evidence, process or host mutation.
    raw, packed, payload, rows, values = source_payload()
    require(os.geteuid() == 0 and sys.platform.startswith('linux'), 'Existing Oracle root context required')
    require(ROOT.resolve() == ROOT and ROOT.is_dir(), 'Exact existing integration worktree required')
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        require(not os.environ.get(name), 'Inherited Git override is not admitted')
    for path in (EVIDENCE, PRIVATE, OUT, GATE_OUT):
        no_symlinks(path)
        require(not path.exists(), 'Exclusive operation already has state; inspect without rerun: ' + str(path))
    prior_raw, prior = prior_receipt()
    resource = resources()
    EVIDENCE.mkdir(mode=0o700)
    receipt = {'schema': 'pinkha-root-w2-sdk61-source-integration/v1', 'state': 'RUNNING',
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
