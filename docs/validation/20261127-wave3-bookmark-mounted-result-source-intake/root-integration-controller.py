#!/usr/bin/env python3
"""Closed original Bookmark UI, mounted attachment and rename-result source integration.

Retain all three original donor ancestries, exact reviewed source/evidence, map145, unchanged
package/lock/PBX/SDK guards and all original runtime closure. No reset, force push,
compiler, test replay, resolver, materialization or runtime activation.
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
START = '3208bdb32e043d9a9b333ec45e017bc5a966ce0b'
START_TREE = '1bbf243c96eef7bd1c19b8f9b4ad73e59af8925e'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['3d2abbf8b1017204e2b93b53ea83ff6f053e67b3', '9a2c8e7abd6311293f7eb8c35d2e9f6ed43ab33c', '0b748192d230966160df010b93987638f5e161b9']
PRIOR = Path('/tmp/pinkha-root-heart-test-map110-continuation-20261127.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-bookmark-mounted-result-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-bookmark-mounted-result-source-integration-20261127')
PRIVATE = Path('/tmp/pinkha-root-bookmark-mounted-result-source-index-20261127')
OUT = Path('/tmp/pinkha-root-bookmark-mounted-result-source-integration-20261127.json')
PREFIX = 'docs/validation/20261127-wave3-bookmark-mounted-result-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-bookmark-mounted-result-source-retention-20261127.json')
PACKED_BYTES = 1962977
PACKED_SHA = '1abe9fd64c2c5b6b57a492ff0b728951d10ce4181ffc5ef0a3695771c098f6c4'
PAYLOAD_BYTES = 6784751
PAYLOAD_SHA = '55506ec7956dc5cbc350770ebde599f3a693008623a8cd6063f01ea66d8ade0f'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
SOURCE_ROW_COUNT = 227
FIXED_EVIDENCE_COUNT = 22
EXPECTED_DONOR_TREE = '2d9493598cd240b07dfda95f7e4e40fbe5fa8672'
EXPECTED_SOURCE_TREE = '548bda0ff10daed8d7219eb126153760d79452b7'

SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
ORIGINAL_CONTROLLER_SHA = '8d93db3644d72d46382ed0335ce2aec747d4457d78f679588ca53f1c336a91dc'
ORIGINAL_CONTROLLER_PATH = 'docs/validation/20261127-wave3-heart-note-empty-warm-source-intake/root-integration-controller.py'
PRIOR_BYTES = 210426
PRIOR_SHA = '7084ef28ce4ec7ecc185306ece17cf2791617ef6d5d1788775d90994dd55baea'
PRIOR_COMMAND_COUNT = 71
PRIOR_CONTROLLER_SHA = '34c19b8a50ace528d4f9b5628756c1de39ce02e9329dc571e2d12d7c4ffaeb73'
PRIOR_PAYLOAD_SHA = '0794f7e4004fbaf22ffdf611e1fc78e0b5ec5ff21543fbcca46b3709804345f4'


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


# Source template only. The local authoring program reads this as text.
# No candidate controller is imported or executed during preparation.


def prior_receipt():
    require(isinstance(PRIOR_BYTES, int) and PRIOR_BYTES == 210426
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '') and PRIOR_COMMAND_COUNT == 71,
            'Actual published map110 continuation receipt is unbound')
    raw = read_regular(PRIOR, PRIOR_BYTES)
    require(len(raw) == PRIOR_BYTES and sha(raw) == PRIOR_SHA, 'Actual map110 receipt bytes differ')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-heart-test-map110-continuation/v1'
            and value['state'] == 'SOURCE_PENDING_TWO_PARENT_MERGE_CONTINUED_AND_PUBLISHED_RUNTIME_CLOSED'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['start'] == '2fcfecefaa3d99d63c47e34823d18a45e13f11f9'
            and value['startTree'] == '7f009cbe4cd41b41f7e577cd569ebf6c903caf53'
            and value['controllerSHA256'] == PRIOR_CONTROLLER_SHA
            and value['payloadSHA256'] == PRIOR_PAYLOAD_SHA
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 145
            and value['normalPushCompleted'] is True and value['commandCustodyBlocked'] is False
            and value['firstFailure'] is None and value['runtimeAcceptance'] is False
            and value['originalUntrackedPreserved'] is True,
            'Only the actual successful map110 source continuation is admitted')
    parents = ['2fcfecefaa3d99d63c47e34823d18a45e13f11f9',
               'f9f86c7c8a5dea0e7fb2b7a9782483cd128d1406']
    require(value['localMergeCommits'] == [{'head': START, 'tree': START_TREE, 'parents': parents}]
            and value['donorTips'] == parents[1:] and value['mergesExecuted'] == 0
            and value['originalMergeContinued'] is True and value['originalFailedGatePreserved'] is True
            and value['originalFailurePreserved'] == {'type': 'RuntimeError', 'message': 'original-retention-gate exited 1'}
            and value['originalFailedReceiptSHA256'] == '64e247cebc4cd43320bbe0a6dc1aaa8cc6062b640494985bcc3e16ef9114d5b5'
            and value['originalFailedGateSHA256'] == 'ca1a6c40fd849329e2b6eb8e12d3b8453afca69c2a3c2c41eed351165a65775e',
            'Original failed attempt or normal continued merge ancestry differs')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Prior source-only scope changed')
    require(value['outputPins']['sdk'] == SDK and len(value['outputPins']['allPackagePins']) == 56
            and value['inputPins'] == value['outputPins'] and value['outputPins']['reviewedRefactors'] == 145
            and len(value['outputPins']['closedActivation']) == 45, 'Actual published pin/runtime closure differs')
    label = 'retained-whole-original-diagnostics'
    diagnostic = 'd63f8fcbec372fd12e3a2be6a2acc3396c09d5775abe85b60be285ed5a91701c'
    empty = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    require(value['diffChecks'] == [
        {'exit': 0, 'label': 'narrow-continuation-whitespace', 'scope': 'PASS',
         'stderrSHA256': empty, 'stdoutSHA256': empty},
        {'exit': 2, 'label': label, 'scope': 'EXACT_RETAINED_ORIGINAL_EVIDENCE_DIAGNOSTICS_NOT_PASS',
         'stderrSHA256': empty, 'stdoutSHA256': diagnostic}],
        'Original narrow PASS and retained whole exit2 must remain distinct')
    require(len(value['commands']) == PRIOR_COMMAND_COUNT, 'Actual prior command count differs')
    observed = []
    for command in value['commands']:
        require(command.get('originalProcessGroupAbsent') is True and command.get('cleanupSignals') == []
                and not command.get('cleanupFailure') and not command.get('receiptFailure'),
                'Actual prior source command has unresolved custody')
        if command['label'] == label:
            require(command['exitCode'] == 2 and command['stdout']['bytes'] == 1319
                    and command['stdout']['sha256'] == diagnostic and command['stderr']['bytes'] == 0
                    and command['stderr']['sha256'] == empty
                    and command.get('firstFailure') == {'type': 'RuntimeError', 'message': label + ' exited 2'},
                    'Exact original raw evidence diagnostic differs')
            observed.append(label)
        else:
            require(command['exitCode'] == 0 and command.get('firstFailure') is None,
                    'Only the one exact retained diagnostic may be nonzero')
    require(observed == [label], 'Missing or duplicated original diagnostic command')
    # This reads original receipts only; historical process groups are never probed.
    return raw, value


def source_payload():
    require(re.fullmatch('[a-f0-9]{40}', START or '') and re.fullmatch('[a-f0-9]{40}', START_TREE or '')
            and PRIOR_COMMAND_COUNT == 71 and isinstance(PRIOR_BYTES, int)
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '')
            and isinstance(PACKED_BYTES, int) and isinstance(PAYLOAD_BYTES, int)
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA or '')
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA or ''), 'Final source tuple is unbound; no host action')
    require(0 < PAYLOAD_BYTES <= MAX_LOG and 0 < PACKED_BYTES <= MAX_LOG, 'Bounded exact source payload required')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed source payload differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Complete source payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-bookmark-mounted-result-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE and value['bindingReady'] is True
            and value['priorReceipt'] == {'path': str(PRIOR), 'bytes': PRIOR_BYTES, 'sha256': PRIOR_SHA}
            and value['priorCommandCount'] == PRIOR_COMMAND_COUNT and value['donorTips'] == DONORS,
            'Closed source and actual publication tuple differ')
    require(value['runtimeAcceptance'] is False and all(value[key] == 0 for key in
            ('testsExecuted', 'compilerInvocations', 'materializations')), 'No runtime activation from source intake')
    require(len(value['donorRows']) == 226 and len(value['rootRows']) == 1
            and not (set(value['donorRows']) & set(value['rootRows']))
            and len(value['donorLinks']) == 4 and value['retainedDonorFiles'] == {},
            'Only the exact three donor tips, preparation ancestor and one source-guard proof are admitted')
    proof_path = PREFIX + '/source-guard-proof.json'
    require(set(value['rootRows']) == {proof_path} and value['rootRows'][proof_path]['status'] == 'A',
            'Root source row is not the exact additive guard/provenance proof')
    rows = {**value['donorRows'], **value['rootRows']}
    values = decode_rows(rows)
    product_paths = [
        'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift',
        'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift',
        'Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHierarchyRepository.swift',
        'Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/AnyHierarchyTests.swift',
        'Modules/PinkhaAnyUI/Package.swift',
        'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyLibraryPresentation.swift',
        'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryView.swift']
    mounted = 'AnyTypeTests/Pinkha/AnyNativeAttachmentMountedRecoveryTests.swift'
    require(sorted(path for path, row in rows.items() if row['status'] == 'M') == product_paths
            and value['donorRows'][mounted]['status'] == 'A'
            and value['donorRows'][mounted]['after']['bytes'] == 55563
            and value['donorRows'][mounted]['after']['sha256'] == '05767e33a0e169e7e8beb4a4c29137f59c33d74e1794e74c7837dbd52575d0bc'
            and all(path in product_paths or path == mounted or path.startswith('docs/validation/') for path in rows),
            'Reviewed finite product/test/source-provenance scope differs')
    require(len(rows) == SOURCE_ROW_COUNT == 227
            and sum(row['status'] == 'M' for row in rows.values()) == 7
            and sum(row['status'] == 'A' for row in rows.values()) == 220,
            'Only the exact seven replacements and220 additions are admitted')
    require(value['finalSourcePathCount'] == SOURCE_ROW_COUNT
            and value['guardInputs']['sdkRevision'] == SDK and value['guardInputs']['selectedKitRevision'] == KIT
            and value['expectedDonorTree'] == EXPECTED_DONOR_TREE
            and value['expectedSourceTree'] == EXPECTED_SOURCE_TREE,
            'SDK, Kit or complete source projection differs')
    require(set(value['diffChecks']) == {'donors', 'source', 'complete'}, 'Finite original diff scopes required')
    for expected in value['diffChecks'].values():
        require(expected['exit'] in (0, 2) and isinstance(expected['stdout'], str) and isinstance(expected['stderr'], str),
                'Literal finite Git diagnostic is unbound')
    require(value['productDiffCheck'] == {'exit': 0, 'stdout': '', 'stderr': ''},
            'The ordinary source-only diff must be clean')
    require(len(value['evidence']) == FIXED_EVIDENCE_COUNT, 'Fixed source-intake evidence count differs')
    return raw, packed, value, rows, values


def validate_donors(commands, payload, start_leaves):
    commands.git('fetch-exact-bookmark-mounted-result-donors', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    require(DONORS == ['3d2abbf8b1017204e2b93b53ea83ff6f053e67b3',
                       '9a2c8e7abd6311293f7eb8c35d2e9f6ed43ab33c',
                       '0b748192d230966160df010b93987638f5e161b9'], 'Exact three published donor tips differ')
    specs = [
        ('3d2abbf8b1017204e2b93b53ea83ff6f053e67b3', '2eca933c726346da539b378180f20da56cdef2a0',
         '2fcfecefaa3d99d63c47e34823d18a45e13f11f9', 55),
        ('9a2c8e7abd6311293f7eb8c35d2e9f6ed43ab33c', 'fe082661e58acf00eba72e91297b32edd7286db8',
         '25fb60a3d1b32fbc8879f1631c8c85d38c76e510', 27),
        ('8b70497157758f3ae8148842f1236d215d6d2d50', 'b6e575e259b15015623e1fa8e20cee792a527915',
         '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce', 103),
        ('0b748192d230966160df010b93987638f5e161b9', '66030762e3a36362a699a71f960db8715c7ef20e',
         '8b70497157758f3ae8148842f1236d215d6d2d50', 41)]
    ancestors = [spec[2] for spec in specs[:3]]
    require(payload['integratedAncestors'] == ancestors, 'Original integrated ancestry differs')
    observed = {}
    object_ids = set()
    admitted_commits = set()
    for index, link in enumerate(payload['donorLinks']):
        commit, tree, parent, count = specs[index]
        prefix = 'original-donor-%02d' % (index + 1)
        require(link['commit'] == commit and link['tree'] == tree and link['parents'] == [parent]
                and len(link['files']) == count, 'Original full donor link differs')
        if parent in ancestors:
            commands.git(prefix + '-base-integrated', 'merge-base', '--is-ancestor', parent, START)
        else:
            require(parent in admitted_commits, 'Result preparation ancestor was not independently admitted')
        actual = commands.git(prefix + '-identity', 'show', '-s', '--format=%H %T %P', commit).decode().split()
        require(actual == [commit, tree, parent], 'Published donor commit/tree/parent differs')
        require(changes(commands, prefix + '-complete-diff', parent, commit)
                == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed full donor delta')
        paths = sorted(safe_path(path) for path in link['files'])
        leaves = parse_leaves(commands.git(prefix + '-exact-changed-leaves',
            'ls-tree', '-r', '-z', '--full-tree', tree, '--', *paths))
        require(set(leaves) == set(paths) and not (set(observed) & set(paths)), 'Donor paths overlap or differ')
        original = batch_blobs(commands, prefix + '-original-blobs',
                               {row['after']['gitBlob']: None for row in link['files'].values()})
        for path, donor_row in link['files'].items():
            row = payload['donorRows'][path]
            require_leaf(start_leaves, path, row['before'])
            require_leaf(leaves, path, row['after'])
            require(donor_row == {'status': row['status'], 'after': row['after']}, 'Reviewed donor row differs')
            match(original[row['after']['gitBlob']], row['after'])
            require(original[row['after']['gitBlob']] == base64.b64decode(row['base64'], validate=True),
                    'Whole original donor bytes differ')
            observed[path] = row
        object_ids.update(original)
        admitted_commits.add(commit)
    require(observed == payload['donorRows'] and len(observed) == 226, 'Whole226-path donor union differs')
    return object_ids


def validate_guards(commands, payload, before_leaves, target_leaves, prior, stage):
    guards = payload['guardInputs']
    require(stage in ('before', 'after') and guards['originalRetentionRows'] == 145
            and guards['expectedRetentionRows'] == 145 and guards['sourceMapUpdates'] == [],
            'The complete original145-row source map must remain unchanged')
    protected = {path: leaf for path, leaf in before_leaves.items()
                 if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
                 or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    ui_package = 'Modules/PinkhaAnyUI/Package.swift'
    added_paths = [
        'docs/validation/20261127-wave2-bookmark-native-frame/source/Modules/PinkhaAnyUI/Package.swift',
        'docs/validation/20261127-wave2-hierarchy-rename-component-preparation/execution/inputs/component/Package.swift']
    require(len(protected) == 80 and protected == guards['protectedLeaves']
            and sorted(guards['addedProtectedLeaves']) == added_paths
            and protected[ui_package] == {'mode': '100644', 'type': 'blob', 'sha': 'b0a0df61c5a62c8a0fb4fc7419c9b947f6fc06d8'},
            'Original80 protected leaves or two explicit evidence manifests differ')
    package_row = payload['donorRows'][ui_package]
    require(package_row['before']['gitBlob'] == protected[ui_package]['sha']
            and package_row['after']['gitBlob'] == 'd45cd6ba0b21a92266942220e50f0d7c40d8b9f7',
            'Only the exact reviewed UI package dependency addition is admitted')
    expected_package = {'mode': '100644', 'type': 'blob', 'sha': package_row['after']['gitBlob']}
    require(guards['protectedUpdates'] == {ui_package: {'before': protected[ui_package], 'after': expected_package}},
            'Unreviewed original protected identity update')
    expected_protected = {**protected, ui_package: expected_package}
    for path in added_paths:
        row = payload['donorRows'][path]
        expected = {'mode': '100644', 'type': 'blob', 'sha': row['after']['gitBlob']}
        require(path not in before_leaves and row['before'] is None and row['status'] == 'A'
                and row['after']['gitMode'] == '100644' and guards['addedProtectedLeaves'][path] == expected,
                'Added evidence package must be an exact original donor leaf')
        expected_protected[path] = expected
    target_protected = {path: leaf for path, leaf in target_leaves.items()
                 if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
                 or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    require(len(target_protected) == 82 and target_protected == expected_protected,
            'Unreviewed protected source path or identity change')
    before, after = guards['files'], guards['filesAfter']
    store_path = 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift'
    witness_path = 'Tools/PinkhaDualEngineRuntime/hosted_native26_properties/source_witnesses.json'
    store_row = payload['donorRows'][store_path]
    require(len(before) == len(after) == 52 and set(before) == set(after)
            and [path for path in before if before[path] != after[path]] == [store_path]
            and before[store_path] == store_row['before'] and after[store_path] == store_row['after']
            and before[store_path]['gitBlob'] == 'e11bb97a37c323b43d3842b081b7c8e2d5eee8e3'
            and after[store_path]['gitBlob'] == 'b8de5482053e5f7e3bf6798608f09a98d291281a'
            and guards['addedClosedActivation'] == [], 'Only the reviewed whole Store may change among52 witnesses')
    values = batch_blobs(commands, 'guard-' + stage + '-original-files',
                         {row['gitBlob']: None for row in before.values()})
    for path, identity in before.items():
        require_leaf(before_leaves, path, identity)
        require_leaf(target_leaves, path, after[path])
        match(values[identity['gitBlob']], identity)
    map_raw = values[before[MAP_PATH]['gitBlob']]
    require(before[MAP_PATH] == after[MAP_PATH] and len(json.loads(map_raw)['changes']) == 145
            and before[MAP_PATH]['gitBlob'] == '722a41b870957cf17f9724b8dd732b7d6088bde0',
            'Actual published map145 including row110 must remain byte-exact')
    current_witness = json.loads(values[before[witness_path]['gitBlob']])
    current_row = current_witness['appFixtureSources'][store_path]
    require(current_row == {'bytes': 44570, 'sha256': 'c653fa8489f7f9dc7d835d57ab4ec27be0bc46e189a29d226524d81e70e6db48'}
            and len(current_witness['appFixtureSources']) == 7 and current_witness['runtimeExecuted'] is False
            and current_witness['ordinaryStorage'] is False and before[witness_path] == after[witness_path],
            'Original closed Native26 Store witness or historical scope changed')
    actual_store = values[before[store_path]['gitBlob']]
    require(len(actual_store) == current_row['bytes'] and sha(actual_store) == current_row['sha256'],
            'Actual previous Store does not match its retained original witness')
    store_after = base64.b64decode(store_row['base64'], validate=True)
    match(store_after, after[store_path])
    require(len(store_after) == 53698
            and sha(store_after) == 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b'
            and guards['native26StoreCompatibility'] == {
                'retainedWitnessIsHistoricalForNewStore': True,
                'separateReviewedSourceSuccessorRequired': True,
                'runtimeActivation': False},
            'New Store source cannot silently promote old Native26 runtime admission')
    sdk = json.loads(values[before['Tools/Hanlin/source.json']['gitBlob']])
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    pins = json.loads(values[before[lock_path]['gitBlob']])['pins']
    require(sdk['revision'] == SDK == guards['sdkRevision'] and pins == prior['outputPins']['allPackagePins']
            and pins == guards['inputPins']['allPackagePins'] and len(pins) == 56,
            'Original SDK or56 selected main package pins changed')
    require([pin['state']['revision'] for pin in pins if pin['identity'].casefold() == 'torahinspectorkit'] == [KIT],
            'Selected original Kit26 changed')
    activation = guards['closedActivation']
    require(activation == prior['outputPins']['closedActivation'] and len(activation) == 45,
            'Original45 closed runtime tuples differ')
    for witness in activation:
        require(witness['path'] in before and before[witness['path']] == after[witness['path']],
                'Original closed activation source is not guarded unchanged')
        current = json.loads(values[before[witness['path']]['gitBlob']])
        for key, wanted in witness['fields'].items():
            require(type(current[key]) is type(wanted) and current[key] == wanted
                    and (wanted is None or wanted is False or wanted == []), 'Original runtime activation changed')
    result = {'sdk': SDK, 'allPackagePins': pins, 'reviewedRefactors': 145,
              'closedActivation': activation, 'sourceOnly': True}
    require(result == prior['outputPins'] == guards['inputPins'] == guards['outputPins'],
            'Original source-only pins and closed-runtime tuple differ')
    return result


def gate_once(commands, receipt, label, tree, output):
    require(not output.exists(), 'Original gate output already exists')
    launcher = 'import os,runpy,sys;root,script=sys.argv[1:3];os.chdir(root);sys.argv=sys.argv[2:];runpy.run_path(script,run_name="__main__")'
    stdout = commands.run(label, PRE + ['python3','-B','-c',launcher,str(ROOT),str(ROOT / GATE),'--base',
        '586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(output)],timeout=120)
    raw = read_regular(output)
    result = json.loads(raw)
    require(stdout == raw and result['sourceRetentionPassed'] is True and len(result['reviewedRefactors']) == 145
            and result['base'] == '586c98bcc17dee425664224e508fc0e8df277678' and result['head'] == START
            and result['checkedTree'] == tree and result['inventoryErrors'] == []
            and result['unreviewedChangedExistingFiles'] == [], 'Original145 retention gate did not pass')
    receipt.setdefault('sourceRetentionGates',[]).append({'label':label,'tree':tree,'path':str(output),
        'bytes':len(raw),'sha256':sha(raw),'sourceRetentionPassed':True,'reviewedRefactors':145})
    return raw


def integrate(commands, receipt, payload, rows, values, prior_raw, prior):
    require(commands.git('original-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines() == [START,START_TREE]
            and commands.git('original-branch','symbolic-ref','HEAD').decode().strip() == REF,
            'Original integration HEAD/tree/branch differs')
    merge_head = Path(commands.git('merge-state-path','rev-parse','--path-format=absolute','--git-path','MERGE_HEAD').decode().strip())
    require(not merge_head.exists(), 'Existing merge must be preserved')
    original = original_status(commands,'original')
    exact_remote(commands,'original-remote',START)
    original_index_path = Path(commands.git('original-index-path','rev-parse','--path-format=absolute','--git-path','index').decode().strip())
    original_index = optional_file_identity(original_index_path)
    base_leaves = tree_leaves(commands,'complete-start-tree',START_TREE)
    preimages = {}
    for path,row in rows.items():
        require_leaf(base_leaves,path,row['before'])
        previous = None if row['before'] is None else base64.b64decode(row['beforeBase64'],validate=True)
        destination_preflight(path,previous,may_be_sparse=True)
        if previous is not None:
            preimages[row['before']['gitBlob']] = previous
    batch_blobs(commands,'all-original-start-preimages',preimages)
    donor_oids = validate_donors(commands,payload,base_leaves)
    donor_leaves = expected_leaves(base_leaves,payload['donorRows'])
    source_leaves = expected_leaves(base_leaves,rows)
    before_guards = validate_guards(commands,payload,base_leaves,source_leaves,prior,'before')
    receipt['resourceBeforeObjects'] = resources()
    commands.run('create-exclusive-private-index',PRE+['python3','-B','-c','import os,sys;os.mkdir(sys.argv[1],0o700)',str(PRIVATE)])
    existing_oids = {leaf['sha'] for leaf in base_leaves.values() if leaf['type'] == 'blob'} | donor_oids
    write_new_objects(commands,payload['rootRows'],values,existing_oids)
    donor_tree = private_tree(commands,'complete-bookmark-mounted-result-donor-preview',base_leaves,payload['donorRows'],donor_leaves)
    require(donor_tree == EXPECTED_DONOR_TREE,'Complete original three-donor tree differs')
    diff_check(commands,'all-bookmark-mounted-result-donor-diff',['diff','--check','--no-renames',START,donor_tree],payload['diffChecks']['donors'],receipt)
    source_tree = private_tree(commands,'complete-composed-source-preview',base_leaves,rows,source_leaves)
    require(source_tree == EXPECTED_SOURCE_TREE,'Complete reviewed227-path source tree differs')
    diff_check(commands,'all-composed-source-diff',['diff','--check','--no-renames',START,source_tree],payload['diffChecks']['source'],receipt)
    final_guards = validate_guards(commands,payload,base_leaves,source_leaves,prior,'after')
    gate_leaf = base_leaves[GATE]
    require(gate_leaf == source_leaves[GATE] and gate_leaf['type'] == 'blob','Original retention gate source changed')
    gate_source = batch_blobs(commands,'original-retention-gate-source',{gate_leaf['sha']:None})[gate_leaf['sha']]
    require(read_regular(ROOT/GATE) == gate_source,'Working original retention gate differs')
    original_controller_leaf = base_leaves[ORIGINAL_CONTROLLER_PATH]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Original8d93 source controller is not retained')
    original_controller = batch_blobs(commands,'original-8d93-controller',{original_controller_leaf['sha']:None})[original_controller_leaf['sha']]
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA,'Original complete8d93 controller differs')
    self_raw = read_regular(Path(__file__))
    intake = {'schema':'pinkha-root-bookmark-mounted-result-source-intake/v1','start':START,'startTree':START_TREE,
        'normalMergeParents':[START,*DONORS],'donorTips':DONORS,'donorTree':donor_tree,'sourceTree':source_tree,
        'files':{path:{key:value for key,value in row.items() if key not in ('base64','beforeBase64')} for path,row in rows.items()},
        'controllerSHA256':sha(self_raw),'payloadSHA256':PAYLOAD_SHA,'positivePriorPublicationReceiptSHA256':sha(prior_raw),
        'originalUntrackedFiles':list(UNTRACKED),'originalUntrackedGroupedStatus':original['grouped'].decode(),
        'originalUntrackedFileIdentities':original['files'],'inputPins':before_guards,'outputPins':final_guards,
        'originalDiffChecks':payload['diffChecks'],'runtimeAcceptance':False,
        'compilerInvocations':0,'testsExecuted':0,'materializations':0,
        'historicalFailuresPreserved':True,
        'newRuntimeResultsClaimed':False,
        'bookmarkChangedSourceFiles':7,
        'bookmarkNewHostMethodsNotRun':4,
        'bookmarkNewIntegrationMethodsNotRun':2,
        'mountedRecoveryMethodsNotRun':1,
        'mountedRecoveryNewSourceNotAdmittedToExisting61CompilerPlan':True,
        'originalHierarchyRenameMethodsQualified':4,
        'originalHierarchyRenameCasesQualified':8,
        'originalHierarchyResultReceiptSHA256':'42d6a0b7b5bd09bf253fcabb814120397da615fc6db8647b633c4ba677cf8266',
        'originalHierarchyResultDoesNotExecuteNewBookmarkRouting':True,
        'native26StoreWitnessPreservedAsHistorical':True,
        'native26StoreCompatibilityRequiresSeparateSourceSuccessor':True,
        'allRuntimeActivationRemainsClosed':True,
        'warm22Methods34CasesAndEditor4Unchanged':True}
    evidence = {'root-source-intake.json':encoded(intake),'root-integration-controller.py':self_raw,
        'prior-map110-publication.original.json':prior_raw,
        'root-controller-full-original-inverse.json':encoded(controller_inverse(original_controller,self_raw))}
    for name,item in payload['evidence'].items():
        safe_path(name)
        require(name not in evidence,'Root evidence collision')
        raw = base64.b64decode(item['base64'],validate=True)
        match(raw,item['after'])
        evidence[name] = raw
    evidence_rows,evidence_values = {},{}
    for name,raw in evidence.items():
        path = PREFIX+'/'+name
        require(path not in rows and path not in base_leaves,'Root evidence destination already exists')
        destination_preflight(path,None)
        if name not in payload['evidence']:
            generated_evidence_is_whitespace_clean(raw)
        evidence_rows[path] = {'status':'A','before':None,'beforeBase64':None,
            'after':{'bytes':len(raw),'sha256':sha(raw),'gitBlob':blob(raw),'gitMode':'100644'}}
        evidence_values[path] = raw
    all_rows = {**rows,**evidence_rows}
    whole_leaves = expected_leaves(base_leaves,all_rows)
    write_new_objects(commands,evidence_rows,evidence_values,existing_oids)
    whole_tree = private_tree(commands,'complete-final-preview',base_leaves,all_rows,whole_leaves)
    diff_check(commands,'complete-final-preview-diff',['diff','--check','--no-renames',START,whole_tree],payload['diffChecks']['complete'],receipt)
    require(commands.git('premerge-head-tree','rev-parse','HEAD','HEAD^{tree}').decode().splitlines() == [START,START_TREE]
            and commands.git('premerge-index-tree','write-tree').decode().strip() == START_TREE,
            'Original HEAD or index advanced before mutation')
    require(original_status(commands,'premerge') == original and optional_file_identity(original_index_path) == original_index,
            'Original source/index/private-file custody changed before mutation')
    exact_remote(commands,'premerge-remote',START)
    receipt.update(phase='NORMAL_BOOKMARK_MOUNTED_RESULT_DONOR_MERGE',expectedDonorTree=donor_tree,expectedSourceTree=source_tree,expectedTree=whole_tree)
    resources()
    commands.git('normal-bookmark-mounted-result-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'merge','--no-ff','--no-commit',*DONORS,timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS,'Normal three-donor merge parent order differs')
    require(commands.git('actual-donor-stage','write-tree').decode().strip() == donor_tree
            and tree_leaves(commands,'actual-donor-leaves',donor_tree) == donor_leaves,
            'Normal donor merge differs; preserve state without automatic resolution')
    root_rows = payload['rootRows']
    root_previous = {path:None if row['before'] is None else base64.b64decode(row['beforeBase64'],validate=True)
                     for path,row in root_rows.items()}
    write_owned_batch(commands,'write-exact-source-guard-proof',root_rows,values,root_previous)
    commands.git('stage-only-exact-source-guard-proof','add','--sparse','--',*sorted(root_rows))
    require(commands.git('actual-composed-source-stage','write-tree').decode().strip() == source_tree,
            'Actual227-path source composition differs')
    write_owned_batch(commands,'write-exclusive-root-evidence',evidence_rows,evidence_values,{path:None for path in evidence_rows})
    commands.git('stage-only-exact-root-evidence','add','--sparse','--',*sorted(evidence_rows))
    require(commands.git('actual-complete-stage','write-tree').decode().strip() == whole_tree,
            'Complete staged tree differs from predicted full tree')
    require(changes(commands,'actual-complete-path-diff',START,whole_tree) == {path:row['status'] for path,row in all_rows.items()},
            'Unexpected complete source path')
    require(commands.git('unstaged-source-check','diff','--name-only') == b''
            and commands.git('original-untracked-check','ls-files','--others','--exclude-standard','-z') == original['untracked'],
            'Staged source or original untracked paths changed')
    diff_check(commands,'actual-complete-index-diff',['diff','--cached','--check','--no-renames',START],payload['diffChecks']['complete'],receipt)
    require(validate_guards(commands,payload,base_leaves,whole_leaves,prior,'after') == final_guards,'Final stage pin guards differ')
    receipt['phase'] = 'ORIGINAL145_RETENTION_GATE'
    gate_raw = gate_once(commands,receipt,'original-retention-gate',whole_tree,GATE_OUT)
    require(commands.git('final-precommit-head','rev-parse','HEAD').decode().strip() == START
            and commands.git('final-precommit-index','write-tree').decode().strip() == whole_tree,
            'Final source changed during original gate')
    require(commands.git('final-precommit-untracked','ls-files','--others','--exclude-standard','-z') == original['untracked'],
            'Original private files changed during final gate')
    receipt['phase'] = 'NORMAL_FOUR_PARENT_SOURCE_COMMIT'
    commands.git('normal-four-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'commit','-F','-',data=payload['finalCommitMessage'].encode(),timeout=45)
    head = commands.git('final-committed-head','rev-parse','HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree','show','-s','--format=%T %P',head).decode().split()
            == [whole_tree,START,*DONORS],'Normal four-parent merge ancestry differs')
    require(original_status(commands,'committed') == original and not merge_head.exists(),'Committed source/private-file custody differs')
    require(commands.git('committed-branch','symbolic-ref','HEAD').decode().strip() == REF,'Original integration branch changed')
    exact_remote(commands,'prepush-remote',START)
    receipt.update(tree=whole_tree,donorTips=DONORS,files=sorted(all_rows),sourceRetentionPassed=True,reviewedRefactors=145,
        retentionSHA256=sha(gate_raw),inputPins=before_guards,outputPins=final_guards,originalUntrackedPreserved=True,
        localMergeCommits=[{'head':head,'tree':whole_tree,'parents':[START,*DONORS]}])
    receipt['phase'] = 'ONE_NORMAL_NONFORCE_PUSH'
    resources()
    commands.git('normal-exact-final-source-push','push','--porcelain','--no-follow-tags','origin',head+':'+REF,publish=True,timeout=90)
    receipt['normalPushCompleted'] = True
    exact_remote(commands,'published-exact-readback',head)
    receipt['normalPushReadback'] = head
    require(original_status(commands,'published') == original,'Published worktree custody differs')
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
    receipt = {'schema': 'pinkha-root-bookmark-mounted-result-source-integration/v1', 'state': 'RUNNING',
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
