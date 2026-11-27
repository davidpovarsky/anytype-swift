#!/usr/bin/env python3
"""Finish only the preserved pending source83 merge after the map110 correction.

Preserve the exact original failed145 gate and every product/control byte. No
fetch, remerge, reset, force push, build, resolver or SDK materialization.
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
START = '2fcfecefaa3d99d63c47e34823d18a45e13f11f9'
START_TREE = '7f009cbe4cd41b41f7e577cd569ebf6c903caf53'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['f9f86c7c8a5dea0e7fb2b7a9782483cd128d1406']
BASE = '586c98bcc17dee425664224e508fc0e8df277678'
FAILED_TREE = '6d1151a8affa5e18621756c4a07ccda4c12a13bd'
FAILED_RECEIPT = Path('/tmp/pinkha-root-heart-note-empty-warm-source-integration-20261127.json')
FAILED_RECEIPT_BYTES = 198278
FAILED_RECEIPT_SHA = '64e247cebc4cd43320bbe0a6dc1aaa8cc6062b640494985bcc3e16ef9114d5b5'
FAILED_GATE = Path('/tmp/pinkha-root-heart-note-empty-warm-source-retention-20261127.json')
FAILED_GATE_BYTES = 51296
FAILED_GATE_SHA = 'ca1a6c40fd849329e2b6eb8e12d3b8453afca69c2a3c2c41eed351165a65775e'
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-heart-test-map110-continuation-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-heart-test-map110-continuation-20261127')
PRIVATE = Path('/tmp/pinkha-root-heart-test-map110-continuation-index-20261127')
OUT = Path('/tmp/pinkha-root-heart-test-map110-continuation-20261127.json')
PREFIX = 'docs/validation/20261127-wave3-heart-test-map110-continuation'
OLD_PREFIX = 'docs/validation/20261127-wave3-heart-note-empty-warm-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-heart-test-map110-retention-20261127.json')
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
REGISTER_PATH = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
ORIGINAL_CONTROLLER_SHA = 'ff7b9dacf9a52fd50de89167516028fd3ce334bc90c0ff1a0684fd472995c0b7'
TEST_PATH = 'AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift'
BASIS_CONTROLLER_PATH = 'docs/validation/20261127-wave3-bootstrap-map144-continuation/continuation-controller.py'
PACKED_BYTES = 245031
PACKED_SHA = 'd59bc9fac50417798320ddc8b0a3cbb8ca43d4454476816d2f8e34ce237b9ff2'
PAYLOAD_BYTES = 1135504
PAYLOAD_SHA = '0794f7e4004fbaf22ffdf611e1fc78e0b5ec5ff21543fbcca46b3709804345f4'
FIXED_EVIDENCE_COUNT = 7
EXPECTED_METADATA_TREE = '60e9198e537082f42751c465bb726b115895a60a'



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
    for name, path, floor, growth in [('root', Path('/'), 1 * 1024**3, 64 * 1024**2),
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



def generated_evidence_is_whitespace_clean(raw):
    require(not raw.endswith(b'\n\n')
            and all(not line.endswith((b' ', b'\t', b'\r')) for line in raw.split(b'\n')),
            'Generated source evidence introduces unreviewed whitespace diagnostics')



h = sha


def failure_receipts():
    raw = read_regular(FAILED_RECEIPT, FAILED_RECEIPT_BYTES)
    require(len(raw) == FAILED_RECEIPT_BYTES and sha(raw) == FAILED_RECEIPT_SHA,
            'Exact original failed source83 receipt differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-heart-note-empty-warm-source-integration/v1'
            and value['state'] == 'FAILED_PRESERVED_NO_AUTOMATIC_RESET'
            and value['phase'] == 'ORIGINAL145_RETENTION_GATE'
            and value['start'] == START and value['startTree'] == START_TREE
            and value['expectedTree'] == FAILED_TREE
            and value['expectedSourceTree'] == '9db5615c0948a2782a4bd7075a4e09c93d43f0cd'
            and value['expectedDonorTree'] == 'beef7460f3b89748546c0c2305124df4abbbfb28'
            and value['controllerSHA256'] == '8d93db3644d72d46382ed0335ce2aec747d4457d78f679588ca53f1c336a91dc'
            and value['payloadSHA256'] == '3883460497c7e8525e7fb6f462f1cbe885abb9f14c0b24e37c188041f7df6d40'
            and value['packedPayloadSHA256'] == 'a796524c7eebf4afc44771edf712d40feec0b00247d0638d17118f922b8caed3'
            and value['positivePriorReceiptSHA256'] == '182c774cca6eb1d76800488ea6741e23f0a0dfb009a35545ae4560c67216adbf'
            and value['firstFailure'] == {'message': 'original-retention-gate exited 1', 'type': 'RuntimeError'}
            and value['commandCustodyBlocked'] is False and value['runtimeAcceptance'] is False,
            'Only the actual preserved source83 gate failure is admitted')
    require(not any(key in value for key in ('head', 'normalPushCompleted', 'normalPushReadback'))
            and all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Original failure no longer has the precommit source-only scope')
    require(len(value['commands']) == 113, 'Original failed command count differs')
    diagnostics = {
        'all-heart-note-donor-diff': (470, 'af88a484ea8eee6f63c935f30e98b1176c064dde69e3fb18ef1c698953d249ff'),
        'all-composed-source-diff': (1319, 'd63f8fcbec372fd12e3a2be6a2acc3396c09d5775abe85b60be285ed5a91701c'),
        'complete-final-preview-diff': (1319, 'd63f8fcbec372fd12e3a2be6a2acc3396c09d5775abe85b60be285ed5a91701c'),
        'actual-complete-index-diff': (1319, 'd63f8fcbec372fd12e3a2be6a2acc3396c09d5775abe85b60be285ed5a91701c')}
    seen = set()
    for index, command in enumerate(value['commands']):
        require(command.get('originalProcessGroupAbsent') is True and command.get('cleanupSignals') == []
                and not command.get('cleanupFailure') and not command.get('receiptFailure'),
                'Original failed attempt has unresolved command custody')
        if index == 112:
            require(command['label'] == 'original-retention-gate' and command['exitCode'] == 1
                    and command['stdout']['bytes'] == FAILED_GATE_BYTES
                    and command['stdout']['sha256'] == FAILED_GATE_SHA
                    and command['stderr']['bytes'] == 0, 'Original first failing command differs')
        elif command['label'] in diagnostics:
            expected = diagnostics[command['label']]
            require(command['label'] not in seen and command['exitCode'] == 2
                    and command['stdout']['bytes'] == expected[0]
                    and command['stdout']['sha256'] == expected[1]
                    and command['stderr']['bytes'] == 0, 'Retained historical whitespace diagnostic differs')
            seen.add(command['label'])
        else:
            require(command['exitCode'] == 0, 'Unexpected earlier original command failure')
    require(seen == set(diagnostics), 'The four exact original diagnostic scopes differ')
    gate_raw = read_regular(FAILED_GATE, FAILED_GATE_BYTES)
    require(len(gate_raw) == FAILED_GATE_BYTES and sha(gate_raw) == FAILED_GATE_SHA,
            'Original failed gate bytes differ')
    gate = json.loads(gate_raw)
    require(gate['base'] == BASE and gate['head'] == START and gate['checkedTree'] == FAILED_TREE
            and gate['baseIsAncestor'] is True and gate['sourceRetentionPassed'] is False
            and gate['inventoryErrors'] == ['Replacement blob mismatch: ' + TEST_PATH]
            and len(gate['reviewedRefactors']) == 145 and gate['unreviewedChangedExistingFiles'] == [],
            'Original gate is not exactly the one stale Heart test replacement identity')
    require(gate['reviewedRefactors'][110] == {
        'kind': 'refactor', 'from': TEST_PATH, 'to': TEST_PATH,
        'baselineBlob': 'c324e390f31bf794e5fdc44869481667fde5b788',
        'replacementBlob': 'aabdb85147a2a032b6ec89dfe82741032b0b488c'},
        'Original failed map110 row differs')
    return raw, value, gate_raw, gate


def source_payload():
    require(0 < PAYLOAD_BYTES <= MAX_LOG and 0 < PACKED_BYTES <= MAX_LOG
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA)
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA), 'Continuation input tuple is unbound')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed continuation input differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Continuation payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-heart-test-map110-continuation-inputs/v1'
            and value['start'] == START and value['startTree'] == START_TREE
            and value['failedTree'] == FAILED_TREE and value['normalMergeParents'] == [START, *DONORS]
            and value['expectedMetadataTree'] == EXPECTED_METADATA_TREE
            and value['runtimeAcceptance'] is False and value['firstFailurePreserved'] is True
            and all(value[key] == 0 for key in ('testsExecuted', 'compilerInvocations', 'materializations')),
            'Closed continuation source or parent tuple differs')
    rows = value['rows']
    require(set(rows) == {MAP_PATH} and rows[MAP_PATH]['status'] == 'M'
            and len(value['retainedRows']) == 83, 'Only the one source-map path may be replaced')
    values = decode_rows(rows)
    before_raw = base64.b64decode(rows[MAP_PATH]['beforeBase64'], validate=True)
    before, after = json.loads(before_raw), json.loads(values[MAP_PATH])
    old, new = before['changes'][110], after['changes'][110]
    require(len(before['changes']) == len(after['changes']) == 145
            and old['from'] == old['to'] == new['from'] == new['to'] == TEST_PATH
            and old['replacementBlob'] == 'aabdb85147a2a032b6ec89dfe82741032b0b488c'
            and new['replacementBlob'] == 'e187f8a307a79705010058cc4f21238398d72927'
            and new['reason'] == old['reason'] + value['reasonAppend']
            and new['validation'] == old['validation'] + [value['validationAppend']],
            'Only the exact full Heart test identity and appended source-only provenance are admitted')
    restored = json.loads(values[MAP_PATH])
    restored['changes'][110] = old
    require(restored == before
            and {key: item for key, item in new.items() if key not in ('replacementBlob', 'reason', 'validation')}
                == {key: item for key, item in old.items() if key not in ('replacementBlob', 'reason', 'validation')}
            and (json.dumps(before, ensure_ascii=False, indent=2) + '\n').encode() == before_raw
            and (json.dumps(after, ensure_ascii=False, indent=2) + '\n').encode() == values[MAP_PATH],
            'Any original map row, metadata or formatting differs')
    source = value['sourceWitness']
    require(source['path'] == TEST_PATH and source['after'] == value['retainedRows'][TEST_PATH]['after']
            and source['after'] == {'bytes': 98718,
                'sha256': '5c992907c09ab5a1fb249cb4d70d8e132735981709a030f1b3c3bba62e851e53',
                'gitBlob': 'e187f8a307a79705010058cc4f21238398d72927', 'gitMode': '100644'}
            and rows[MAP_PATH]['before'] == value['retainedRows'][MAP_PATH]['after'],
            'Corrected metadata must bind the original already-staged full test')
    require(value['inputPins'] == value['stagedInputPins']
            and value['stagedInputPins']['reviewedRefactors'] == 145
            and len(value['stagedInputPins']['closedActivation']) == 45,
            'Original pin or closed runtime scope changed')
    for path, source in value['evidence'].items():
        require(path.startswith(PREFIX + '/') and path not in value['retainedRows'] and source['status'] == 'A',
                'Failure evidence must be an exclusive new path')
    evidence_values = decode_rows(value['evidence'])
    require(len(value['evidence']) == FIXED_EVIDENCE_COUNT, 'Exact fixed failure evidence count differs')
    return raw, packed, value, rows, values, evidence_values


def pending_status(commands, label, expected_changes, payload):
    status = commands.git(label + '-status', 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    untracked = commands.git(label + '-untracked-paths', 'ls-files', '--others', '--exclude-standard', '-z')
    grouped = commands.git(label + '-untracked-groups', 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    expected = b''.join(path.encode() + b'\0' for path in UNTRACKED)
    require(untracked == expected and sha(untracked) == '7dbac249bb04e50bb0e08159393acb49119dde6ebe33670d129ee8f691ab991b',
            'The four original full untracked paths changed')
    changed = {}
    observed_untracked = []
    for entry in status.split(b'\0'):
        if not entry:
            continue
        require(len(entry) > 3 and entry[2:3] == b' ', 'Malformed original pending status')
        code, path = entry[:2], entry[3:].decode()
        require(code in (b'A ', b'M ', b'??'), 'Conflict, unstaged change, deletion or rename in pending source')
        if code == b'??':
            observed_untracked.append(path)
        else:
            require(path not in changed, 'Duplicate pending source path')
            changed[path] = code[:1].decode()
    require(changed == expected_changes and observed_untracked == list(UNTRACKED),
            'Pending status is not exactly the retained staged paths and four original files')
    grouped_untracked = b''.join(entry + b'\0' for entry in grouped.split(b'\0') if entry.startswith(b'?? '))
    require(grouped_untracked.decode() == payload['originalUntrackedGroupedStatus'], 'Original untracked grouping changed')
    require(commands.git(label + '-unmerged-index', 'ls-files', '-u', '-z') == b''
            and commands.git(label + '-unstaged-diff', 'diff', '--name-only') == b'',
            'The preserved pending merge contains conflicts or unstaged changes')
    files = {path: optional_file_identity(ROOT / path) for path in UNTRACKED}
    require(files == payload['originalUntrackedFileIdentities'], 'Original private untracked file identity changed')
    return {'status': status, 'untracked': untracked, 'grouped': grouped, 'files': files}



def merge_state(merge_head):
    require(read_regular(merge_head) == ''.join(parent + '\n' for parent in DONORS).encode(),
            'Only the exact original pending single-donor merge may continue')
    root = merge_head.parent
    require(read_regular(root / 'ORIG_HEAD') == (START + '\n').encode(), 'Original pending merge base changed')
    require(read_regular(root / 'MERGE_MODE') == b'no-ff', 'Original no-fast-forward merge mode changed')
    require(read_regular(root / 'MERGE_MSG'), 'Original pending merge message disappeared')
    require(not (root / 'MERGE_AUTOSTASH').exists(), 'Unexpected merge autostash must be preserved')
    return {name: optional_file_identity(root / name)
            for name in ('MERGE_HEAD', 'ORIG_HEAD', 'MERGE_MODE', 'MERGE_MSG', 'MERGE_AUTOSTASH')}



def continuation_guards(commands, payload, leaves):
    expected = payload['guards']
    require(len(expected) == 52, 'Exactly the original52 source guards are required')
    for path, identity in expected.items():
        require_leaf(leaves, path, identity)
    protected = {path: leaf for path, leaf in leaves.items()
        if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
        or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    require(len(protected) == 80 and protected == payload['protectedLeaves'],
            'Original80 protected sources changed in the retained stage')
    actual = batch_blobs(commands, 'original-continued-source-pin-and-closed-activation-guards',
                         {identity['gitBlob']: None for identity in expected.values()})
    for identity in expected.values():
        match(actual[identity['gitBlob']], identity)
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    pins = json.loads(actual[expected[lock_path]['gitBlob']])['pins']
    require(pins == payload['stagedInputPins']['allPackagePins'] == payload['inputPins']['allPackagePins']
            and len(pins) == 56, 'Original56 main package pins changed')
    require([pin['state']['revision'] for pin in pins if pin['identity'].casefold() == 'torahinspectorkit'] == [KIT],
            'Selected Kit26 original pin changed')
    sdk = json.loads(actual[expected['Tools/Hanlin/source.json']['gitBlob']])
    require(sdk['revision'] == SDK == payload['stagedInputPins']['sdk'], 'Actual staged c0b SDK pin changed')
    for witness in payload['stagedInputPins']['closedActivation']:
        data = json.loads(actual[expected[witness['path']]['gitBlob']])
        for key, wanted in witness['fields'].items():
            require(type(data[key]) is type(wanted) and data[key] == wanted
                    and (wanted is None or wanted is False or wanted == []), 'Runtime activation changed')
    return payload['stagedInputPins']


def gate_once(commands, receipt, tree):
    require(not GATE_OUT.exists(), 'Fresh original145 gate output already exists')
    launcher = 'import os,runpy,sys;root,script=sys.argv[1:3];os.chdir(root);sys.argv=sys.argv[2:];runpy.run_path(script,run_name="__main__")'
    stdout = commands.run('original145-retention-gate', PRE + ['python3', '-B', '-c', launcher, str(ROOT), str(ROOT / GATE),
        '--base', BASE, '--ref', tree, '--output', str(GATE_OUT)], timeout=120)
    raw = read_regular(GATE_OUT)
    result = json.loads(raw)
    require(stdout == raw and result['base'] == BASE and result['head'] == START and result['checkedTree'] == tree
            and result['sourceRetentionPassed'] is True and result['inventoryErrors'] == []
            and result['unreviewedChangedExistingFiles'] == [] and len(result['reviewedRefactors']) == 145,
            'Unchanged original gate did not qualify all145 exact original-baseline mappings')
    receipt['sourceRetentionGates'] = [{'tree': tree, 'path': str(GATE_OUT), 'bytes': len(raw), 'sha256': sha(raw),
        'sourceRetentionPassed': True, 'reviewedRefactors': 145}]
    return raw



def integrate(commands, receipt, payload, rows, values, evidence_values, failed_raw, failed, gate_raw):
    require(evidence_values[PREFIX + '/attempt1/receipt.original.json'] == failed_raw
            and evidence_values[PREFIX + '/attempt1/gate.original.json'] == gate_raw,
            'The exact original failed receipt and gate must be retained unchanged')
    require(commands.git('continued-head-tree', 'rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [START, START_TREE]
            and commands.git('continued-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF,
            'Original pending integration HEAD/tree/branch changed')
    merge_head = Path(commands.git('continued-merge-state-path', 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD').decode().strip())
    original_merge = merge_state(merge_head)
    retained_changes = {path: source['status'] for path, source in payload['retainedRows'].items()}
    original = pending_status(commands, 'continued-original', retained_changes, payload)
    exact_remote(commands, 'continued-original-remote', START)
    require(commands.git('continued-original-index-tree', 'write-tree').decode().strip() == FAILED_TREE,
            'The actual original failed staged tree changed')
    original_index_path = Path(commands.git('continued-original-index-path', 'rev-parse', '--path-format=absolute', '--git-path', 'index').decode().strip())
    original_index = optional_file_identity(original_index_path)
    start_leaves = tree_leaves(commands, 'complete-original-2fc-tree', START_TREE)
    failed_leaves = tree_leaves(commands, 'complete-original-failed6d11-tree', FAILED_TREE)
    require(expected_leaves(start_leaves, payload['retainedRows']) == failed_leaves
            and changes(commands, 'original-retained83-paths', START, FAILED_TREE) == retained_changes,
            'The complete original83-path staged tree no longer matches')
    for path, source in payload['retainedRows'].items():
        require_leaf(start_leaves, path, source['before'])
    intake_path = payload['retainedActualIntake']['path']
    require_leaf(failed_leaves, intake_path, payload['retainedActualIntake'])
    intake_raw = read_regular(ROOT / intake_path)
    match(intake_raw, payload['retainedActualIntake'])
    intake = json.loads(intake_raw)
    require(intake['inputPins'] == payload['inputPins'] and intake['outputPins'] == payload['stagedInputPins']
            and intake['originalUntrackedFileIdentities'] == payload['originalUntrackedFileIdentities']
            and intake['normalMergeParents'] == [START, *DONORS], 'Original staged intake provenance differs')
    continuation_guards(commands, payload, failed_leaves)
    witness = payload['sourceWitness']
    require_leaf(failed_leaves, TEST_PATH, witness['after'])
    test_raw = batch_blobs(commands, 'exact-already-staged-full-heart-test', {witness['after']['gitBlob']: None})[witness['after']['gitBlob']]
    match(test_raw, witness['after'])
    require(read_regular(ROOT / TEST_PATH) == test_raw, 'Working full Heart test source differs')
    preimages = {}
    for path, source in rows.items():
        require_leaf(failed_leaves, path, source['before'])
        previous = base64.b64decode(source['beforeBase64'], validate=True)
        destination_preflight(path, previous)
        preimages[source['before']['gitBlob']] = previous
    batch_blobs(commands, 'exact-original-map110-preimage', preimages)
    original_controller = read_regular(ROOT / BASIS_CONTROLLER_PATH)
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA
            and failed_leaves[BASIS_CONTROLLER_PATH]['sha'] == blob(original_controller),
            'Retained original map144 continuation controller differs')
    gate_leaf = failed_leaves[GATE]
    require(gate_leaf == start_leaves[GATE], 'Original retention verifier source changed')
    verifier = batch_blobs(commands, 'original-retention-verifier-bytes', {gate_leaf['sha']: None})[gate_leaf['sha']]
    require(read_regular(ROOT / GATE) == verifier, 'Working original retention verifier differs')
    self_raw = read_regular(Path(__file__))
    inverse_raw = encoded(controller_inverse(original_controller, self_raw))
    metadata_rows = rows
    metadata_values = values
    generated = {
        PREFIX + '/continuation-controller.py': self_raw,
        PREFIX + '/continuation-controller-full-inverse.json': inverse_raw,
        PREFIX + '/continuation-source-intake.json': encoded({
            'schema': 'pinkha-heart-test-map110-continuation-source-intake/v1',
            'scope': 'SOURCE_METADATA_ONLY_EXISTING_PENDING_MERGE_CONTINUATION',
            'start': START, 'startTree': START_TREE, 'originalPendingTree': FAILED_TREE,
            'normalMergeParents': [START, *DONORS], 'controllerSHA256': sha(self_raw),
            'payloadSHA256': PAYLOAD_SHA, 'originalFailedReceiptSHA256': sha(failed_raw),
            'originalFailedGateSHA256': sha(gate_raw), 'originalFailureRetained': failed['firstFailure'],
            'original113CommandsNotReplayed': True, 'original83PathsRetained': True,
            'metadataRows': {path: {key: source[key] for key in ('status', 'before', 'after')} for path, source in metadata_rows.items()},
            'correctedMappingIndex': 110, 'sourceWitness': payload['sourceWitness'], 'inputPins': payload['inputPins'],
            'stagedInputPins': payload['stagedInputPins'], 'newRetentionRows': 145,
            'testsExecuted': 0, 'compilerInvocations': 0, 'materializations': 0, 'runtimeAcceptance': False})
    }
    continuation_rows = dict(metadata_rows)
    continuation_values = dict(metadata_values)
    for path, source in payload['evidence'].items():
        continuation_rows[path] = source
        continuation_values[path] = evidence_values[path]
    for path, data in generated.items():
        require(path not in continuation_rows, 'Continuation evidence collision')
        generated_evidence_is_whitespace_clean(data)
        continuation_rows[path] = {'status': 'A', 'before': None, 'beforeBase64': None,
            'after': {'bytes': len(data), 'sha256': sha(data), 'gitBlob': blob(data), 'gitMode': '100644'}}
        continuation_values[path] = data
    for path, source in continuation_rows.items():
        require_leaf(failed_leaves, path, source['before'])
        destination_preflight(path, None if source['before'] is None else base64.b64decode(source['beforeBase64'], validate=True))
    all_rows = {**payload['retainedRows'], **continuation_rows}
    # The one metadata path keeps its original2fc preimage for the complete
    # START-to-merge tree proof. Its live write still requires exact6d11 bytes.
    for path in metadata_rows:
        all_rows[path] = {**all_rows[path], 'before': payload['retainedRows'][path]['before']}
    final_leaves = expected_leaves(failed_leaves, continuation_rows)
    expected_protected = dict(payload['protectedLeaves'])
    expected_protected[MAP_PATH] = {'mode': rows[MAP_PATH]['after']['gitMode'], 'type': 'blob', 'sha': rows[MAP_PATH]['after']['gitBlob']}
    actual_protected = {path: leaf for path, leaf in final_leaves.items() if path.endswith('/Package.swift') or path.endswith('/Package.resolved') or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    require(actual_protected == expected_protected and len(actual_protected) == 80, 'An unreviewed protected source changed in the continuation')
    for path, expected in payload['guards'].items():
        require_leaf(final_leaves, path, rows[MAP_PATH]['after'] if path == MAP_PATH else expected)
    receipt['resourceBeforeObjects'] = resources()
    commands.run('create-exclusive-continuation-private-index', PRE + ['python3', '-B', '-c',
        'import os,sys;os.mkdir(sys.argv[1],0o700)', str(PRIVATE)])
    write_new_objects(commands, continuation_rows, continuation_values,
                      {leaf['sha'] for leaf in failed_leaves.values() if leaf['type'] == 'blob'})
    final_tree = private_tree(commands, 'complete-continuation-preview', start_leaves, all_rows, final_leaves)
    require(changes(commands, 'only-map110-plus-new-evidence-preview', FAILED_TREE, final_tree)
            == {path: source['status'] for path, source in continuation_rows.items()}, 'Unexpected continuation source delta')
    diff_check(commands, 'narrow-continuation-whitespace', ['diff', '--check', '--no-renames', FAILED_TREE, final_tree],
               payload['continuationDiffCheck'], receipt)
    diff_check(commands, 'retained-whole-original-diagnostics', ['diff', '--check', '--no-renames', START, final_tree],
               payload['continuationWholeDiffCheck'], receipt)
    require(commands.git('prewrite-continued-head', 'rev-parse', 'HEAD').decode().strip() == START
            and commands.git('prewrite-continued-index', 'write-tree').decode().strip() == FAILED_TREE
            and pending_status(commands, 'prewrite-continued', retained_changes, payload) == original
            and merge_state(merge_head) == original_merge
            and optional_file_identity(original_index_path) == original_index,
            'Original pending source/index/merge/private-file custody changed before the narrow write')
    exact_remote(commands, 'prewrite-continued-remote', START)
    receipt.update(phase='ONLY_MAP110_AND_ORIGINAL_FAILURE_EVIDENCE', expectedTree=final_tree,
                   originalPendingMergeState=original_merge, originalPendingIndex=original_index)
    write_owned_batch(commands, 'write-only-map110-and-original-failure-evidence', continuation_rows, continuation_values,
        {path: None if source['before'] is None else base64.b64decode(source['beforeBase64'], validate=True)
         for path, source in continuation_rows.items()})
    commands.git('stage-only-explicit-continuation-paths', 'add', '--sparse', '--', *sorted(continuation_rows))
    require(commands.git('actual-continuation-complete-tree', 'write-tree').decode().strip() == final_tree
            and tree_leaves(commands, 'actual-continuation-complete-leaves', final_tree) == final_leaves,
            'Actual continuation stage differs from the complete private-index preview')
    final_changes = {path: source['status'] for path, source in all_rows.items()}
    pending_status(commands, 'final-continued', final_changes, payload)
    require(merge_state(merge_head) == original_merge, 'Original merge state changed while staging metadata')
    receipt['phase'] = 'ORIGINAL145_RETENTION_GATE'
    qualified_gate = gate_once(commands, receipt, final_tree)
    require(commands.git('final-precommit-head', 'rev-parse', 'HEAD').decode().strip() == START
            and commands.git('final-precommit-index', 'write-tree').decode().strip() == final_tree
            and commands.git('final-precommit-unstaged', 'diff', '--name-only') == b''
            and merge_state(merge_head) == original_merge,
            'Pending source or original merge changed during the original145 gate')
    require({path: optional_file_identity(ROOT / path) for path in UNTRACKED} == payload['originalUntrackedFileIdentities'],
            'Original private untracked files changed during the gate')
    receipt['phase'] = 'COMMIT_ORIGINAL_PENDING_TWO_PARENT_MERGE'
    commands.git('normal-existing-two-parent-merge-commit', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com',
                 'commit', '-F', '-', data=payload['finalCommitMessage'].encode(), timeout=45)
    head = commands.git('final-committed-head', 'rev-parse', 'HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree', 'show', '-s', '--format=%T %P', head).decode().split()
            == [final_tree, START, *DONORS], 'Original normal two-parent ancestry changed')
    clean = {'status': b''.join(b'?? ' + path.encode() + b'\0' for path in UNTRACKED),
             'untracked': original['untracked'], 'grouped': payload['originalUntrackedGroupedStatus'].encode(),
             'files': payload['originalUntrackedFileIdentities']}
    require(original_status(commands, 'committed') == clean and not merge_head.exists(),
            'Committed source/private-file custody differs')
    require(commands.git('committed-original-branch', 'symbolic-ref', 'HEAD').decode().strip() == REF,
            'Original integration branch changed')
    exact_remote(commands, 'prepush-original-remote', START)
    final_pins = dict(payload['stagedInputPins'])
    final_pins['reviewedRefactors'] = 145
    receipt.update(tree=final_tree, donorTips=DONORS, files=sorted(all_rows), sourceRetentionPassed=True,
        reviewedRefactors=145, retentionSHA256=sha(qualified_gate), inputPins=payload['inputPins'],
        stagedInputPins=payload['stagedInputPins'], outputPins=final_pins, originalUntrackedPreserved=True,
        localMergeCommits=[{'head': head, 'tree': final_tree, 'parents': [START, *DONORS]}],
        originalFailedGatePreserved=True, originalMergeContinued=True, mergesExecuted=0)
    receipt['phase'] = 'ONE_NORMAL_NONFORCE_PUSH'
    resources()
    commands.git('normal-exact-final-source-push', 'push', '--porcelain', '--no-follow-tags', 'origin', head + ':' + REF,
                 publish=True, timeout=90)
    receipt['normalPushCompleted'] = True
    exact_remote(commands, 'published-exact-readback', head)
    receipt['normalPushReadback'] = head
    require(original_status(commands, 'published') == clean, 'Published worktree/private-file custody differs')
    receipt['state'] = 'SOURCE_PENDING_TWO_PARENT_MERGE_CONTINUED_AND_PUBLISHED_RUNTIME_CLOSED'



def main():
    # Unbound source must stop before any evidence, process or host mutation.
    raw, packed, payload, rows, values, evidence_values = source_payload()
    require(os.geteuid() == 0 and sys.platform.startswith('linux'), 'Existing Oracle root context required')
    require(ROOT.resolve() == ROOT and ROOT.is_dir(), 'Exact existing integration worktree required')
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS'):
        require(not os.environ.get(name), 'Inherited Git override is not admitted')
    for path in (EVIDENCE, PRIVATE, OUT, GATE_OUT):
        no_symlinks(path)
        require(not path.exists(), 'Exclusive operation already has state; inspect without rerun: ' + str(path))
    failed_raw, failed, gate_raw, gate = failure_receipts()
    resource = resources()
    EVIDENCE.mkdir(mode=0o700)
    receipt = {'schema': 'pinkha-root-heart-test-map110-continuation/v1', 'state': 'RUNNING',
               'startedAt': time.time(), 'start': START, 'startTree': START_TREE, 'commands': [],
               'controllerSHA256': sha(read_regular(Path(__file__))), 'payloadSHA256': sha(raw),
               'packedPayloadSHA256': sha(packed), 'originalFailedReceiptSHA256': sha(failed_raw),
               'originalFailedGateSHA256': sha(gate_raw), 'originalFailurePreserved': failed['firstFailure'],
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
        integrate(commands, receipt, payload, rows, values, evidence_values, failed_raw, failed, gate_raw)
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



if __name__ == "__main__":
    main()
