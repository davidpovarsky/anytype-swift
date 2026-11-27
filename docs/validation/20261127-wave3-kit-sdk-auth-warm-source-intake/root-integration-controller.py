#!/usr/bin/env python3
"""Closed coherent source integration over actual published af63.

Retain original N53/C21/78cc ancestry and compose only reviewed Kit, SDK,
account/Bootstrap and warm controls. Preserve original per-command custody,
all first failures, fixed300s and source resource floors. No automatic reset,
force push, runtime activation, build, resolver or SDK materialization.
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
START = 'af63f6209c38bddf6ed851f0b894e2f627a671af'
START_TREE = 'c3c3f46ec9241b6d446000bbdb3f5f89826b6a0c'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['e330c0230f352cadff76b4fa0feafd1032fa142e', '6b91db33d325f22b62d829051db203121c6cdb8e', '78ccffbc711affe743a96edcb79455998f8b73a6']
PRIOR = Path('/tmp/pinkha-root-inspector-native26-host-source-integration-20261127.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-kit-sdk-auth-warm-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-kit-sdk-auth-warm-source-integration-20261127')
PRIVATE = Path('/tmp/pinkha-root-kit-sdk-auth-warm-source-index-20261127')
OUT = Path('/tmp/pinkha-root-kit-sdk-auth-warm-source-integration-20261127.json')
PREFIX = 'docs/validation/20261127-wave3-kit-sdk-auth-warm-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-kit-sdk-auth-warm-source-retention-20261127.json')
PACKED_BYTES = 3851564
PACKED_SHA = '7c86dbb8a35dcd4209d9e2900175f4ad657e3d26fa412cd320a2304846a74a96'
PAYLOAD_BYTES = 14326115
PAYLOAD_SHA = '67fb22cbada8fb2182b35c307ac70e196a4cfa3452c96b4156c11192acc34538'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2
OLD_SDK = '5fffe60fbcec8b12ae2cc14bcb092884677f19b0'
OLD_KIT = '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
ROOT_ROW_COUNT = 232
SOURCE_ROW_COUNT = 346
EXPECTED_DONOR_TREE = '72ca00ae2fc3f48b3dbe45b3164f0ebc9f105454'
EXPECTED_SOURCE_TREE = 'b541771de1ad588b8c2fa4484222a0640cd9d212'

SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
ORIGINAL_CONTROLLER_SHA = '68a723263310fd9636be14c37682a5b86dee6d79dc478afce76708044c8815b1'
ORIGINAL_CONTROLLER_PATH = 'docs/validation/20261127-wave3-inspector-native26-host-source-intake/root-integration-controller.py'
PRIOR_BYTES = 421471
PRIOR_SHA = '8aafc88fa5b3f8b96ad1f0d8a261d945c32a7a5f2b8ba3275778dcc5d571306f'


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
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or ''), 'Positive actual158 receipt is unbound')
    raw = read_regular(PRIOR, PRIOR_BYTES)
    require(len(raw) == PRIOR_BYTES and sha(raw) == PRIOR_SHA, 'Actual positive158 original receipt changed')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-inspector-native26-host-source-integration/v1'
            and value['state'] == 'SOURCE_TWO_NORMAL_MERGES_PUBLISHED_RUNTIME_CLOSED'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['start'] == '01bc25a63371c4c7640dc0c20b75500e28325f87'
            and value['startTree'] == '0733b6e8811302d978e6dba76726e4bd1d2bed58'
            and value['controllerSHA256'] == ORIGINAL_CONTROLLER_SHA
            and value['payloadSHA256'] == '817ae2747e3175e94a1f5d73fe5ae7b40ff38a32120d30384077e6081c4f3b4a'
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 133
            and value['normalPushCompleted'] is True and value['commandCustodyBlocked'] is False
            and value['firstFailure'] is None and value['runtimeAcceptance'] is False,
            'Prior actual158 source, publication or custody differs')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Prior158 source-only scope changed')
    require(value['outputPins']['sdk'] == OLD_SDK and len(value['outputPins']['allPackagePins']) == 56
            and value['inputPins']['allPackagePins'] == value['outputPins']['allPackagePins']
            and value['inputPins']['sdk'] == value['outputPins']['sdk'], 'Actual prior158 SDK/package scope differs')
    require(len(value['commands']) == 181 and all(row.get('originalProcessGroupAbsent') is True
            and row.get('cleanupSignals') == [] and not row.get('cleanupFailure')
            and not row.get('receiptFailure') for row in value['commands']), 'Actual prior158 positive command custody differs')
    return raw, value



def source_payload():
    require(re.fullmatch('[a-f0-9]{40}', START or '') and re.fullmatch('[a-f0-9]{40}', START_TREE or '')
            and isinstance(PRIOR_BYTES, int) and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '')
            and isinstance(PACKED_BYTES, int) and isinstance(PAYLOAD_BYTES, int)
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA or '')
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA or ''), 'Final source tuple is unbound; no host action')
    require(0 < PAYLOAD_BYTES <= MAX_LOG and 0 < PACKED_BYTES <= MAX_LOG, 'Bounded exact source payload required')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed source payload differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Complete source payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-kit-sdk-auth-warm-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE and value['bindingReady'] is True
            and value['priorReceipt'] == {'path': str(PRIOR), 'bytes': PRIOR_BYTES, 'sha256': PRIOR_SHA}
            and value['donorTips'] == DONORS, 'Closed source/actual publication tuple differs')
    require(value['runtimeAcceptance'] is False and all(value[key] == 0 for key in
            ('testsExecuted', 'compilerInvocations', 'materializations')), 'Source payload cannot activate runtime acceptance')
    require(len(value['donorRows']) == 114 and len(value['rootRows']) == ROOT_ROW_COUNT
            and len(value['donorLinks']) == 6 and len(value['retainedDonorFiles']) == 41,
            'Exact114 donor/final root/six-link/41-retained scope differs')
    donor_values = decode_rows(value['donorRows'])
    root_values = decode_rows(value['rootRows'])
    require(not set(value['donorRows']).intersection(value['rootRows']), 'No unreviewed donor/root override')
    rows = {**value['donorRows'], **value['rootRows']}
    values = {**donor_values, **root_values}
    require(len(rows) == value['finalSourcePathCount'] == SOURCE_ROW_COUNT, 'Closed final path union differs')
    require(value['guardInputs']['sdkRevision'] == SDK and value['guardInputs']['selectedKitRevision'] == KIT
            and value['expectedDonorTree'] == EXPECTED_DONOR_TREE
            and value['expectedSourceTree'] == EXPECTED_SOURCE_TREE, 'Exact SDK/Kit/full-tree projection differs')
    require(set(value['diffChecks']) == {'donors', 'source', 'complete'}, 'All finite raw diagnostic scopes required')
    for expected in value['diffChecks'].values():
        require(expected['exit'] in (0, 2) and isinstance(expected['stdout'], str) and isinstance(expected['stderr'], str),
                'Original static Git diagnostic is not bound')
    return raw, packed, value, rows, values



def validate_donors(commands, payload, start_leaves):
    commands.git('fetch-three-exact-donor-tips', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    links = {row['commit']: row for row in payload['donorLinks']}
    expected_links = {
        DONORS[0]: ['92a2904112738619f2f689b137ba663b08378730'],
        'ffee3b05db8765b718a5cf6dab32f04a1ac75741': ['0925ff79df8f70be288f96ea117dbd7059e24219'],
        '12e49ea69efdde499a6b5343cbe77139073dfbd8': ['ffee3b05db8765b718a5cf6dab32f04a1ac75741'],
        DONORS[1]: ['12e49ea69efdde499a6b5343cbe77139073dfbd8'],
        '6eecb62f3bb101306b6036fbc04cc08257c3425f': ['d528e5413c72320c423ce9ccdbd4fbe423ca4a4a'],
        DONORS[2]: ['6eecb62f3bb101306b6036fbc04cc08257c3425f'],
    }
    require(set(links) == set(expected_links) and all(links[key]['parents'] == parents for key, parents in expected_links.items()),
            'Exact N53/C21/6eec/78cc ancestry differs')
    ancestors = ['92a2904112738619f2f689b137ba663b08378730', '0925ff79df8f70be288f96ea117dbd7059e24219',
                 'd528e5413c72320c423ce9ccdbd4fbe423ca4a4a']
    require(payload['integratedAncestors'] == ancestors, 'Closed integrated ancestor tuple differs')
    for index, ancestor in enumerate(ancestors):
        commands.git('original-donor-base-integrated-%02d' % index, 'merge-base', '--is-ancestor', ancestor, START)
    blobs, union, latest = {}, set(), {}
    for index, link in enumerate(payload['donorLinks']):
        result = commands.git('donor-identity-%02d' % index, 'show', '-s', '--format=%H %T %P', link['commit']).decode().split()
        require(result == [link['commit'], link['tree'], *link['parents']] and len(link['parents']) == 1,
                'Published donor commit/tree/parent changed')
        actual = changes(commands, 'donor-complete-diff-%02d' % index, link['parents'][0], link['commit'])
        require(actual == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed donor source delta')
        leaves = tree_leaves(commands, 'donor-complete-tree-%02d' % index, link['tree'])
        for path, row in link['files'].items():
            require_leaf(leaves, safe_path(path), row['after'])
            blobs[row['after']['gitBlob']] = None
            latest[path] = row['after']
        union.update(link['files'])
    require(union == set(payload['donorRows']) | set(payload['retainedDonorFiles'])
            and not set(payload['donorRows']).intersection(payload['retainedDonorFiles']),
            'Whole donor union or retained predecessor partition differs')
    original = batch_blobs(commands, 'all-original-donor-blobs', blobs)
    for link in payload['donorLinks']:
        for row in link['files'].values():
            match(original[row['after']['gitBlob']], row['after'])
    for path, identity in payload['retainedDonorFiles'].items():
        require(latest[path] == identity, 'Retained C predecessor does not bind its latest original bytes')
        require_leaf(start_leaves, path, identity)
    for path, row in payload['donorRows'].items():
        require_leaf(start_leaves, path, row['before'])
        require(latest[path] == row['after'] and original[row['after']['gitBlob']]
                == base64.b64decode(row['base64'], validate=True), 'Final source differs from immutable original donor')
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
    require(guards['originalRetentionRows'] == 133 and guards['expectedRetentionRows'] == 140,
            'Original133 plus seven original-baseline rows required')
    require(stage in ('before', 'after'), 'Finite source guard stage required')
    expected = guards['beforeFiles' if stage == 'before' else 'afterFiles']
    leaves = before_leaves if stage == 'before' else target_leaves
    values = batch_blobs(commands, 'guard-' + stage + '-original-files', {row['gitBlob']: None for row in expected.values()})
    for path, identity in expected.items():
        require_leaf(leaves, path, identity)
        match(values[identity['gitBlob']], identity)
    for path, identity in guards['unchangedFiles'].items():
        require_leaf(before_leaves, path, identity)
        require_leaf(target_leaves, path, identity)
    old_raw = base64.b64decode(guards['sourceMapBeforeBase64'], validate=True)
    new_raw = base64.b64decode(guards['sourceMapAfterBase64'], validate=True)
    match(old_raw, guards['beforeFiles'][MAP_PATH])
    match(new_raw, guards['afterFiles'][MAP_PATH])
    old_map, new_map = json.loads(old_raw), json.loads(new_raw)
    require(len(old_map['changes']) == 133 and len(new_map['changes']) == 140
            and len(guards['sourceMapAppendedRows']) == 7
            and new_map['changes'][133:] == guards['sourceMapAppendedRows'], 'Exact appended source baselines differ')
    require({key: value for key, value in old_map.items() if key != 'changes'}
            == {key: value for key, value in new_map.items() if key != 'changes'}, 'Original map envelope changed')
    updates = guards['sourceMapUpdates']
    require([row['index'] for row in updates] == [15, 59, 63, 102, 115, 129], 'Only six reviewed map entries may change')
    for index, old in enumerate(old_map['changes']):
        new = new_map['changes'][index]
        if index not in (15, 59, 63, 102, 115, 129):
            require(old == new, 'Unrelated original map metadata or descendant source changed')
            continue
        update = next(row for row in updates if row['index'] == index)
        require(update['before'] == old and update['after'] == new, 'Exact reviewed map update differs')
        if index == 129:
            projected = json.loads(json.dumps(old))
            dependency = projected['sharedSources'][3]
            require(dependency == {'path': 'Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift',
                                   'gitBlob': 'b712657e45feea1f05ca68a3aa2098fb9d053e5b'}, 'Original129 dependency differs')
            dependency['gitBlob'] = '74058e7b343365446b93db12395db7d2f948997a'
            require(projected == new and update['field'] == 'sharedSources[3].gitBlob', 'Row129 is shared-source-only')
        else:
            require({key: value for key, value in old.items() if key != 'replacementBlob'}
                    == {key: value for key, value in new.items() if key != 'replacementBlob'}
                    and update['field'] == 'replacementBlob', 'Original row baseline/reason/validation changed')
            path = new['to']
            require(new['replacementBlob'] == guards['afterFiles'][path]['gitBlob'], 'Map replacement does not bind reviewed actual source')
    for appended in guards['sourceMapAppendedRows']:
        require(appended['kind'] == 'refactor' and appended['from'] == appended['to']
                and appended['replacementBlob'] == guards['afterFiles'][appended['to']]['gitBlob'],
                'New baseline row does not bind exact reviewed original path')
    sdk_path = 'Tools/Hanlin/source.json'
    sdk_before = base64.b64decode(guards['sdkBeforeBase64'], validate=True)
    sdk_after = base64.b64decode(guards['sdkAfterBase64'], validate=True)
    match(sdk_before, guards['beforeFiles'][sdk_path])
    match(sdk_after, guards['afterFiles'][sdk_path])
    require(sdk_before.count(OLD_SDK.encode()) == 1 and sdk_after == sdk_before.replace(OLD_SDK.encode(), SDK.encode()),
            'Only the actual published SDK revision may change')
    require(values[expected[sdk_path]['gitBlob']] == (sdk_before if stage == 'before' else sdk_after)
            and json.loads(sdk_after)['revision'] == SDK, 'Current source SDK manifest differs')
    register_path = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
    register_before = base64.b64decode(guards['registerBeforeBase64'], validate=True)
    register_after = base64.b64decode(guards['registerAfterBase64'], validate=True)
    match(register_before, guards['beforeFiles'][register_path])
    match(register_after, guards['afterFiles'][register_path])
    require(register_after.startswith(register_before) and len(register_after) > len(register_before)
            and values[expected[register_path]['gitBlob']] == (register_before if stage == 'before' else register_after),
            'Original exception-register prefix changed')
    require(len(guards['kitRevisionOnlyRows']) == 10 and guards['selectedKitRevision'] == KIT,
            'Closed ten-file Kit revision correction differs')
    for path, identity in guards['kitRevisionOnlyRows'].items():
        source = payload['rootRows'][path]
        require(identity == {'before': source['before'], 'after': source['after']}, 'Kit guarded source identity differs')
        a = base64.b64decode(source['beforeBase64'], validate=True)
        z = base64.b64decode(source['base64'], validate=True)
        previous = b'511454e49450cb2581ddf77f644146ff3e30dbef' if path == 'NativeApp/AnyNative.xcodeproj/project.pbxproj' else OLD_KIT.encode()
        require(a.count(previous) == 1 and z == a.replace(previous, KIT.encode(), 1),
                'Kit change is not exactly one reviewed revision literal: ' + path)
        require(identity['before'] == guards['beforeFiles'][path] and identity['after'] == guards['afterFiles'][path],
                'Original Kit source manifest/lock/PBX guard missing')
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    require(lock_path in guards['unchangedFiles'], 'Original56-lock preservation missing')
    pins = json.loads(values[expected[lock_path]['gitBlob']])['pins']
    require(pins == prior['outputPins']['allPackagePins'] and len(pins) == 56,
            'Original Kit and55 other main package pins changed')
    kit_pins = [pin for pin in pins if pin['identity'].casefold() == 'torahinspectorkit']
    require(len(kit_pins) == 1 and kit_pins[0]['state']['revision'] == KIT, 'Selected original main Kit26 differs')
    activation = guards['closedActivationAfter' if stage == 'after' else 'closedActivationBefore']
    for witness in activation:
        require(witness['path'] in expected, 'Closed activation is not an exact guarded source')
        data = json.loads(values[expected[witness['path']]['gitBlob']])
        for key, wanted in witness['fields'].items():
            require(data[key] == wanted and type(data[key]) is type(wanted)
                    and (wanted is None or wanted is False or wanted == []), 'Runtime activation changed')
    return {'sdk': OLD_SDK if stage == 'before' else SDK, 'allPackagePins': pins,
            'reviewedRefactors': 133 if stage == 'before' else 140,
            'closedActivation': activation, 'sourceOnly': True}



def validate_sdk_publication(payload):
    identity = payload['guardInputs']['sdkPublication']
    require(identity == {'path': '/tmp/pinkha-root-sdk-mcp-title-window-publication-20261127.json',
                         'bytes': 190591, 'sha256': 'c9ed7976a67792ec2d3ab3706eadd6a3071276d9f252b1c04f0e4cd01f34bdbd'},
            'Exact actual c0b SDK publication receipt required')
    raw = read_regular(Path(identity['path']), identity['bytes'])
    require(len(raw) == identity['bytes'] and sha(raw) == identity['sha256'], 'Actual SDK source receipt differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-mcp-title-window-new-ref-publication/v1'
            and value['state'] == 'PASS_SOURCE_ONLY_NEW_REF_PUBLISHED'
            and value['candidateCommit'] == value['normalPushReadback'] == payload['guardInputs']['sdkRevision'] == SDK
            and value['candidateTree'] == value['expectedTree'] == '89485be6fc9db276c4359726a33b51284835b23b'
            and value['base'] == OLD_SDK and value['baseTree'] == 'a52fdb359190930d23a76877baf2fe8fa25101d6'
            and value['ref'] == 'refs/heads/codex/pinkha-sdk-mcp-title-window-20261127'
            and value['controllerSHA256'] == '3e9267b716d80bfa139972d5fb1b2bab54ac21453a61bf2cc189d9cd6ff343a2'
            and value['normalPushCompleted'] is True and value['originalSourceWorktreePreserved'] is True
            and value['commandCustodyBlocked'] is False and value['firstFailure'] is None,
            'Actual SDK source publication/custody was not accepted')
    require(value['actualPackageByteInventory'] == {'files': 1011, 'sourceBytes': 39812364,
            'gitInventorySHA256': 'ce82b072db824b0fbd4cdbab19a745c46349f53ee06874e23355c9c0c5058125'},
            'Original four-package1011 source projection changed')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'workflowDispatches', 'materializations')),
            'SDK source proof scope changed')
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







def gate_once(commands, receipt, label, tree, output):
    require(not output.exists(), 'Original gate output already exists')
    launcher = 'import os,runpy,sys;root,script=sys.argv[1:3];os.chdir(root);sys.argv=sys.argv[2:];runpy.run_path(script,run_name="__main__")'
    commands.run(label, PRE + ['python3', '-B', '-c', launcher, str(ROOT), str(ROOT / GATE), '--base',
                 '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(output)], timeout=120)
    raw = read_regular(output)
    result = json.loads(raw)
    require(result['sourceRetentionPassed'] is True and len(result['reviewedRefactors']) == 140,
            'Original source-retention gate did not qualify original133 plus seven exact baseline rows')
    receipt.setdefault('sourceRetentionGates', []).append({'label': label, 'tree': tree, 'path': str(output),
        'bytes': len(raw), 'sha256': sha(raw), 'sourceRetentionPassed': True, 'reviewedRefactors': 140})
    return raw



def generated_evidence_is_whitespace_clean(raw):
    require(not raw.endswith(b'\n\n')
            and all(not line.endswith((b' ', b'\t', b'\r')) for line in raw.split(b'\n')),
            'Generated source evidence introduces unreviewed whitespace diagnostics')



def validate_new_baselines(commands, payload):
    expected = payload['guardInputs']['newBaselineRows']
    require(len(expected) == 7 and len({row['path'] for row in expected}) == 7, 'Exactly seven distinct original baselines required')
    actual = parse_leaves(commands.git('seven-original-baseline-paths', 'ls-tree', '-r', '-z',
        '586c98bcc17dee425664224e508fc0e8df277678', '--', *[safe_path(row['path']) for row in expected]))
    require(set(actual) == {row['path'] for row in expected}, 'Original baseline path set differs')
    for row in expected:
        require(actual[row['path']] == {'mode': '100644', 'type': 'blob', 'sha': row['baselineBlob']},
                'New source-map baseline is not the exact original baseline file')
    return {'baselineCommit': '586c98bcc17dee425664224e508fc0e8df277678', 'files': expected,
            'allOriginalPathsAndBlobsMatched': True, 'runtimeAcceptance': False}



def hook_census(commands, source_tree):
    # Read the actual complete predicted Git tree, including unqualified callers.
    # The known positives are not represented as an exhaustive caller allowlist.
    raw = commands.git('actual-final-bootstrap-hook-callers', 'grep', '-n', '-F',
                       '-e', 'PinkhaBootstrapHook', '-e', 'handleSpaceActivated', source_tree, '--', 'Anytype', 'Modules')
    require(raw and b'Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift:' in raw
            and b'Anytype/Sources/Pinkha/Bootstrap/PinkhaBootstrapHook.swift:' in raw,
            'The original active-Space/Hook census positives are missing')
    require(raw.count(b'PinkhaBootstrapHook.handleSpaceActivated(spaceId: spaceId, accountCapture: accountCapture)') == 2,
            'The two exact captured selected-Space callers changed')
    return raw, {'schema': 'pinkha-actual-final-bootstrap-hook-source-census/v1', 'tree': source_tree,
                 'command': commands.receipt['commands'][-1]['argv'], 'bytes': len(raw), 'sha256': sha(raw),
                 'scope': 'COMPLETE_ORIGINAL_GIT_GREP_OVER_ANYTYPE_AND_MODULES_NOT_A_RUNTIME_CALL_PROOF',
                 'patterns': ['PinkhaBootstrapHook', 'handleSpaceActivated'],
                 'capturedOriginalActiveSpaceCallers': 2, 'additionalCallersRequireOriginalOutputInspection': True,
                 'runtimeAcceptance': False}



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
    baseline_proof = validate_new_baselines(commands, payload)
    donor_leaves = expected_leaves(base_leaves, payload['donorRows'])
    final_leaves = expected_leaves(base_leaves, rows)
    before_guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'before')
    receipt['resourceBeforeObjects'] = resources()
    commands.run('create-exclusive-private-index', PRE + ['python3', '-B', '-c',
                 'import os,sys;os.mkdir(sys.argv[1],0o700)', str(PRIVATE)])
    existing_oids = {row['sha'] for row in base_leaves.values() if row['type'] == 'blob'} | donor_oids
    write_new_objects(commands, rows, values, existing_oids)
    donor_tree = private_tree(commands, 'all-donor-preview', base_leaves, payload['donorRows'], donor_leaves)
    final_tree = private_tree(commands, 'final-source-preview', base_leaves, rows, final_leaves)
    require(donor_tree == EXPECTED_DONOR_TREE and final_tree == EXPECTED_SOURCE_TREE,
            'Complete actual source Merkle tree differs from the reviewed full af63 projection')
    diff_check(commands, 'all-donor-source-diff', ['diff', '--check', '--no-renames', START, donor_tree], payload['diffChecks']['donors'], receipt)
    diff_check(commands, 'final-source-diff', ['diff', '--check', '--no-renames', START, final_tree], payload['diffChecks']['source'], receipt)
    final_guards = validate_guards(commands, payload, base_leaves, final_leaves, prior, 'after')
    hook_raw, hook_proof = hook_census(commands, final_tree)
    receipt['actualHookCallerCensus'] = hook_proof
    gate_row = base_leaves[GATE]
    require(gate_row == final_leaves[GATE] and gate_row['type'] == 'blob', 'Original retention gate changed')
    gate = batch_blobs(commands, 'original-retention-gate-source', {gate_row['sha']: None})[gate_row['sha']]
    require(read_regular(ROOT / GATE) == gate, 'Working original retention gate differs')
    self_raw = read_regular(Path(__file__))
    original_controller_leaf = base_leaves[ORIGINAL_CONTROLLER_PATH]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Actual158 original controller not retained in START')
    original_controller = batch_blobs(commands, 'actual158-original-controller',
        {original_controller_leaf['sha']: None})[original_controller_leaf['sha']]
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA, 'Original complete actual158 controller differs')
    intake = {'schema': 'pinkha-root-kit-sdk-auth-warm-source-intake/v1', 'start': START, 'startTree': START_TREE,
        'normalMergeParents': [START, *DONORS], 'donorTips': DONORS, 'donorTree': donor_tree, 'finalSourceTree': final_tree,
        'files': {path: {key: value for key, value in row.items() if key not in ('base64', 'beforeBase64')} for path, row in rows.items()},
        'controllerSHA256': sha(self_raw), 'payloadSHA256': PAYLOAD_SHA, 'positivePrior158ReceiptSHA256': sha(prior_raw),
        'originalUntrackedFiles': list(UNTRACKED), 'originalUntrackedGroupedStatus': original['grouped'].decode(),
        'originalUntrackedFileIdentities': original['files'], 'inputPins': before_guards, 'outputPins': final_guards,
        'actualHookCallerCensus': hook_proof, 'originalBaselines': baseline_proof,
        'originalDiffChecks': payload['diffChecks'], 'runtimeAcceptance': False,
        'compilerInvocations': 0, 'testsExecuted': 0, 'materializations': 0}
    evidence = {'root-source-intake.json': encoded(intake), 'root-integration-controller.py': self_raw,
        'prior158-integration.original.json': prior_raw, 'original-final-sdk-publication.json': sdk_publication,
        'actual-bootstrap-hook-callers.original.txt': hook_raw, 'actual-bootstrap-hook-census.json': encoded(hook_proof),
        'actual-seven-original-baselines.json': encoded(baseline_proof),
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
        if name not in payload['evidence'] and name != 'actual-bootstrap-hook-callers.original.txt':
            generated_evidence_is_whitespace_clean(data)
        if name == 'actual-bootstrap-hook-callers.original.txt':
            # This is the original source output, never stripped or normalized.
            # Unexpected whitespace remains an explicit pre-mutation blocker.
            generated_evidence_is_whitespace_clean(data)
        evidence_rows[path] = {'status': 'A', 'before': None, 'beforeBase64': None,
            'after': {'bytes': len(data), 'sha256': sha(data), 'gitBlob': blob(data), 'gitMode': '100644'}}
        evidence_values[path] = data
    all_rows = {**rows, **evidence_rows}
    whole_leaves = expected_leaves(base_leaves, all_rows)
    write_new_objects(commands, evidence_rows, evidence_values, existing_oids)
    whole_tree = private_tree(commands, 'complete-final-preview', base_leaves, all_rows, whole_leaves)
    diff_check(commands, 'complete-final-preview-diff', ['diff', '--check', '--no-renames', START, whole_tree], payload['diffChecks']['complete'], receipt)
    require(commands.git('premerge-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [START, START_TREE]
            and commands.git('premerge-index-tree', 'write-tree').decode().strip() == START_TREE,
            'Original HEAD or index advanced before mutation')
    require(original_status(commands, 'premerge') == original and optional_file_identity(original_index_path) == original_index,
            'Original source/index/untracked custody changed before mutation')
    exact_remote(commands, 'premerge-remote', START)
    receipt.update(phase='NORMAL_THREE_DONOR_MERGE', expectedDonorTree=donor_tree,
                   expectedSourceTree=final_tree, expectedTree=whole_tree)
    resources()
    commands.git('normal-three-tip-source-merge', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'merge', '--no-ff', '--no-commit', *DONORS, timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS, 'Normal three-tip merge parents differ')
    require(commands.git('actual-all-donor-stage', 'write-tree').decode().strip() == donor_tree
            and tree_leaves(commands, 'actual-all-donor-leaves', donor_tree) == donor_leaves,
            'Normal donor merge differs; preserve all state without automatic resolution')
    root_preimages = {}
    for path, row in payload['rootRows'].items():
        require_leaf(donor_leaves, path, row['before'])
        previous = None if row['before'] is None else base64.b64decode(row['beforeBase64'], validate=True)
        destination_preflight(path, previous, may_be_sparse=True)
        root_preimages[path] = previous
    batch_blobs(commands, 'all-exact-root-stage-preimages',
                {payload['rootRows'][path]['before']['gitBlob']: data for path, data in root_preimages.items() if data is not None})
    write_owned_batch(commands, 'write-exact-reviewed-root-composition', payload['rootRows'], values, root_preimages)
    commands.git('stage-only-exact-root-composition', 'add', '--sparse', '--', *sorted(payload['rootRows']))
    require(commands.git('actual-final-source-stage', 'write-tree').decode().strip() == final_tree,
            'Actual source/control stage differs from full private preview')
    write_owned_batch(commands, 'write-exclusive-root-evidence', evidence_rows, evidence_values, {path: None for path in evidence_rows})
    commands.git('stage-only-exact-root-evidence', 'add', '--sparse', '--', *sorted(evidence_rows))
    require(commands.git('actual-complete-stage', 'write-tree').decode().strip() == whole_tree,
            'Complete staged tree differs from full predicted tree')
    require(changes(commands, 'actual-complete-path-diff', START, whole_tree) == {path: row['status'] for path, row in all_rows.items()},
            'Unexpected complete source path')
    require(commands.git('unstaged-source-check', 'diff', '--name-only') == b''
            and commands.git('original-untracked-check', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Staged source or original untracked paths changed')
    diff_check(commands, 'actual-complete-index-diff', ['diff', '--cached', '--check', '--no-renames', START], payload['diffChecks']['complete'], receipt)
    require(validate_guards(commands, payload, base_leaves, whole_leaves, prior, 'after') == final_guards,
            'Final actual stage pin guards differ')
    receipt['phase'] = 'ORIGINAL140_RETENTION_GATE'
    gate_raw = gate_once(commands, receipt, 'original-retention-gate', whole_tree, GATE_OUT)
    require(commands.git('final-precommit-head', 'rev-parse', 'HEAD').decode().strip() == START
            and commands.git('final-precommit-index', 'write-tree').decode().strip() == whole_tree,
            'Final source changed during original retention gate')
    require(commands.git('final-precommit-untracked', 'ls-files', '--others', '--exclude-standard', '-z') == original['untracked'],
            'Original untracked paths changed during final gate')
    receipt['phase'] = 'NORMAL_FOUR_PARENT_SOURCE_COMMIT'
    commands.git('normal-four-parent-source-commit', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'commit', '-F', '-', data=payload['finalCommitMessage'].encode(), timeout=45)
    head = commands.git('final-committed-head', 'rev-parse', 'HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree', 'show', '-s', '--format=%T %P', head).decode().split()
            == [whole_tree, START, *DONORS], 'Normal four-parent merge ancestry differs')
    require(original_status(commands, 'committed') == original and not merge_head.exists(), 'Committed source/untracked custody differs')
    require(commands.git('committed-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF, 'Original final branch changed')
    exact_remote(commands, 'prepush-remote', START)
    receipt.update(tree=whole_tree, donorTips=DONORS, files=sorted(all_rows), sourceRetentionPassed=True, reviewedRefactors=140,
        retentionSHA256=sha(gate_raw), inputPins=before_guards, outputPins=final_guards, originalUntrackedPreserved=True,
        localMergeCommits=[{'head': head, 'tree': whole_tree, 'parents': [START, *DONORS]}])
    receipt['phase'] = 'ONE_NORMAL_NONFORCE_PUSH'
    resources()
    commands.git('normal-exact-final-source-push', 'push', '--porcelain', '--no-follow-tags', 'origin', head + ':' + REF,
                 publish=True, timeout=90)
    receipt['normalPushCompleted'] = True
    exact_remote(commands, 'published-exact-readback', head)
    receipt['normalPushReadback'] = head
    require(original_status(commands, 'published') == original, 'Published worktree custody differs')
    receipt['state'] = 'SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED'



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
    receipt = {'schema': 'pinkha-root-kit-sdk-auth-warm-source-integration/v1', 'state': 'RUNNING',
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
