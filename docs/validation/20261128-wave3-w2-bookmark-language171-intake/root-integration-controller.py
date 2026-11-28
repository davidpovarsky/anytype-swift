#!/usr/bin/env python3
"""Closed original W2 Bookmark, localization and bounded-evidence source integration.

Retain four original donor tips and seven links, exact source/evidence, map145, unchanged
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
START = 'a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd'
START_TREE = '2adebea229e42c5ff56e50aaf0adebbacfbc4c41'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['d99a9b7869ecc58f3e29f260a6109f59375ccaf2', '8785a01f0b1d2cf4463cdb5c0f2757893a904055', 'e01176b6a15bdb6a8ff7fedbca5c880634a773ef', '2205057d97251f5ab2b9004d895a3ee1a55e50dc']
PRIOR = Path('/tmp/pinkha-root-shared62-c13-source-integration-20261127.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-w2-bookmark-language171-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-w2-bookmark-language171-source-integration-20261128')
PRIVATE = Path('/tmp/pinkha-root-w2-bookmark-language171-source-index-20261128')
OUT = Path('/tmp/pinkha-root-w2-bookmark-language171-source-integration-20261128.json')
PREFIX = 'docs/validation/20261128-wave3-w2-bookmark-language171-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-w2-bookmark-language171-source-retention-20261128.json')
PACKED_BYTES = 2004273
PACKED_SHA = '38eb43d1e365798a05c2ffbea3b557c6a91748d1a251d15dec21da0cfc073987'
PAYLOAD_BYTES = 6075412
PAYLOAD_SHA = '027e96b6e38aaf714dedd7a228d1f6761394b099cef380bbf575f9d41dede641'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
SOURCE_ROW_COUNT = 171
FIXED_EVIDENCE_COUNT = 10
EXPECTED_DONOR_TREE = 'df8432306a0f38e7b560b6160115db807c98d412'
EXPECTED_SOURCE_TREE = 'df8432306a0f38e7b560b6160115db807c98d412'

SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
ORIGINAL_CONTROLLER_SHA = '762221e5e2f018b2afb53f0061dc12df9a748fa860fa4e052bda0099c6d90a29'
ORIGINAL_CONTROLLER_PATH = 'docs/validation/20261127-wave3-shared62-c13-source-intake/root-integration-controller.py'
PRIOR_BYTES = 326287
PRIOR_SHA = '7b62387c41cf43f47e329679a1f3b3aa44b0ac71a857da3cffb36ded2e1c6e50'
PRIOR_COMMAND_COUNT = 148
PRIOR_CONTROLLER_SHA = '762221e5e2f018b2afb53f0061dc12df9a748fa860fa4e052bda0099c6d90a29'
PRIOR_PAYLOAD_SHA = '9b57080b7ebe93d87679d7f5decf4bbe5002ed0dfa30c01a5e44183b914790a6'


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
    require(isinstance(PRIOR_BYTES, int) and PRIOR_BYTES == 326287
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '') and PRIOR_COMMAND_COUNT == 148,
            'Actual published139 receipt is unbound')
    raw = read_regular(PRIOR, PRIOR_BYTES)
    require(len(raw) == PRIOR_BYTES and sha(raw) == PRIOR_SHA, 'Actual139 receipt bytes differ')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-shared62-c13-source-integration/v1'
            and value['state'] == 'SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['start'] == '5a45fe4af2c4601faad181f81d391057c1237654'
            and value['startTree'] == '13578db08a5e215fd70e88209e6ec409135440e2'
            and value['controllerSHA256'] == PRIOR_CONTROLLER_SHA
            and value['payloadSHA256'] == PRIOR_PAYLOAD_SHA
            and value['packedPayloadSHA256'] == '3def8329bfa7d2b4523a0da34fa8e2dddd50f688c8e6c126b47126f013cccc56'
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 145
            and value['normalPushCompleted'] is True and value['commandCustodyBlocked'] is False
            and value['firstFailure'] is None and value['runtimeAcceptance'] is False
            and value['originalUntrackedPreserved'] is True,
            'Only the actual successful139 source publication is admitted')
    parents = ['5a45fe4af2c4601faad181f81d391057c1237654',
               'e8331a3943db99cc8c73b9c61c6120b4ecf5ee7d']
    require(value['localMergeCommits'] == [{'head': START, 'tree': START_TREE, 'parents': parents}]
            and value['donorTips'] == parents[1:], 'Original normal two-parent ancestry differs')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Prior source-only scope changed')
    require(value['outputPins']['sdk'] == SDK and len(value['outputPins']['allPackagePins']) == 56
            and value['inputPins'] == value['outputPins'] and value['outputPins']['reviewedRefactors'] == 145
            and len(value['outputPins']['closedActivation']) == 45, 'Actual published pin/runtime closure differs')
    labels = ['all-c13-donor-diff', 'all-composed-source-diff',
              'complete-final-preview-diff', 'actual-complete-index-diff']
    diagnostic = 'dfdd3047836c73e724ed8526c67d4876fcfec839c87c6f1b3939292922e37aa6'
    empty = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    require(value['diffChecks'] == [
        {'exit': 2, 'label': label, 'scope': 'EXACT_RETAINED_ORIGINAL_EVIDENCE_DIAGNOSTICS_NOT_PASS',
         'stderrSHA256': empty, 'stdoutSHA256': diagnostic} for label in labels],
        'Four original whole-evidence exit2 rows must remain distinct from PASS')
    require(len(value['commands']) == PRIOR_COMMAND_COUNT, 'Actual prior command count differs')
    observed = []
    for command in value['commands']:
        require(command.get('originalProcessGroupAbsent') is True and command.get('cleanupSignals') == []
                and not command.get('cleanupFailure') and not command.get('receiptFailure'),
                'Actual prior source command has unresolved custody')
        if command['label'] in labels:
            require(command['exitCode'] == 2 and command['stdout']['bytes'] == 1039
                    and command['stdout']['sha256'] == diagnostic and command['stderr']['bytes'] == 0
                    and command['stderr']['sha256'] == empty
                    and command.get('firstFailure') == {'type': 'RuntimeError', 'message': command['label'] + ' exited 2'},
                    'Exact original raw evidence diagnostic differs')
            observed.append(command['label'])
        else:
            require(command['exitCode'] == 0 and command.get('firstFailure') is None,
                    'Only the four exact retained diagnostics may be nonzero')
    require(observed == labels, 'Missing or duplicated original diagnostic command')
    # Original receipt facts only: never probe historical numeric process groups.
    return raw, value


def source_payload():
    require(re.fullmatch('[a-f0-9]{40}', START or '') and re.fullmatch('[a-f0-9]{40}', START_TREE or '')
            and PRIOR_COMMAND_COUNT == 148 and isinstance(PRIOR_BYTES, int)
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
    require(value['schema'] == 'pinkha-root-w2-bookmark-language171-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE and value['bindingReady'] is True
            and value['priorReceipt'] == {'path': str(PRIOR), 'bytes': PRIOR_BYTES, 'sha256': PRIOR_SHA}
            and value['priorCommandCount'] == PRIOR_COMMAND_COUNT and value['donorTips'] == DONORS,
            'Closed source and actual publication tuple differ')
    require(value['runtimeAcceptance'] is False and all(value[key] == 0 for key in
            ('testsExecuted', 'compilerInvocations', 'materializations')), 'No runtime activation from source intake')
    require(len(value['donorRows']) == 171 and value['rootRows'] == {} and len(value['donorLinks']) == 7
            and len(value['retainedDonorFiles']) == 1, 'Only the exact171 donor paths and one original predecessor are admitted')
    rows = value['donorRows']
    values = decode_rows(rows)
    product_paths = [
        'Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift',
        'NativeApp/Sources/AnyNativeApp.swift',
        'NativeApp/Sources/NativeCustomTypeFixture.swift',
        'NativeApp/UITests/NativeLaunchTests.swift']
    require(sorted(path for path, row in rows.items() if row['status'] == 'M') == product_paths
            and all(row['status'] == 'M' or (row['status'] == 'A' and path.startswith('docs/validation/'))
                    for path, row in rows.items())
            and len(rows) == SOURCE_ROW_COUNT == 171
            and sum(row['status'] == 'A' for row in rows.values()) == 167,
            'Only the exact four product replacements and167 original evidence additions are admitted')
    retained = value['retainedDonorFiles']
    prior_view = '001f22cccfeb5bb78f0ccfe2caa52449e57101eb'
    require(set(retained) == {prior_view}
            and retained[prior_view]['path'] == product_paths[0]
            and retained[prior_view]['commit'] == '770bc4e4a38ec299a8f0ebcc3cc5e8f0c170dabc'
            and retained[prior_view]['after'] == {'bytes': 23642, 'sha256': 'de2ab55e962ee7f17b6eb6ff8bc7e932b48eee6d03c6bca43a818b8c2fe68045',
                'gitBlob': prior_view, 'gitMode': '100644'}, 'Only the original770 localization body may precede8785')
    match(base64.b64decode(retained[prior_view]['base64'], validate=True), retained[prior_view]['after'])
    require(value['donorSourcePacketSHA256'] == '135f51192848071bb653952fd3fbd772bb2a3ff011a8fa32f1f118052aca4958'
            and value['finalSourcePathCount'] == SOURCE_ROW_COUNT
            and value['guardInputs']['sdkRevision'] == SDK and value['guardInputs']['selectedKitRevision'] == KIT
            and value['expectedDonorTree'] == EXPECTED_DONOR_TREE
            and value['expectedSourceTree'] == EXPECTED_SOURCE_TREE == EXPECTED_DONOR_TREE,
            'Frozen full source inputs, SDK, Kit or complete source projection differ')
    require(set(value['diffChecks']) == {'donors', 'source', 'complete'}, 'Finite original diff scopes required')
    for expected in value['diffChecks'].values():
        require(expected['exit'] in (0, 2) and isinstance(expected['stdout'], str) and isinstance(expected['stderr'], str),
                'Literal finite Git diagnostic is unbound')
    require(value['productDiffCheck'] == {'exit': 0, 'stdout': '', 'stderr': ''}
            and value['productDiffCheckPaths'] == product_paths, 'The ordinary four-product source diff must be clean')
    require(len(value['evidence']) == FIXED_EVIDENCE_COUNT, 'Fixed source-intake evidence count differs')
    return raw, packed, value, rows, values


def validate_donors(commands, payload, start_leaves):
    commands.git('fetch-exact-four-w2-donors', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    require(DONORS == ['d99a9b7869ecc58f3e29f260a6109f59375ccaf2',
        '8785a01f0b1d2cf4463cdb5c0f2757893a904055', 'e01176b6a15bdb6a8ff7fedbca5c880634a773ef',
        '2205057d97251f5ab2b9004d895a3ee1a55e50dc'], 'Exact four published W2 tips differ')
    specs = [
        ('d99a9b7869ecc58f3e29f260a6109f59375ccaf2', 'a89c6ba9b3218fe214a27aae8acf478a8bb89825', START, 22),
        ('770bc4e4a38ec299a8f0ebcc3cc5e8f0c170dabc', 'c30e7e168db50c0f5ee7a0085b41ea701f0259ae', START, 14),
        ('8785a01f0b1d2cf4463cdb5c0f2757893a904055', '4e5fa7f47a764385418937f8c5d026056c573241',
            '770bc4e4a38ec299a8f0ebcc3cc5e8f0c170dabc', 17),
        ('9be0544199cde0009771df3305b4616662c35ee1', 'b7996bc93f0d13479976a23e4e8987c5e295c579',
            '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3', 47),
        ('3c086573076bdd4bb16b0ce55bef9f0331b38dd1', '57f5a4d1edb71f8f2fa58a378a1e0ee877e90220',
            '9be0544199cde0009771df3305b4616662c35ee1', 52),
        ('e01176b6a15bdb6a8ff7fedbca5c880634a773ef', 'fdaab65201112cc86a57d55d633cba9b2ef48335',
            '3c086573076bdd4bb16b0ce55bef9f0331b38dd1', 13),
        ('2205057d97251f5ab2b9004d895a3ee1a55e50dc', '643666bc6369460d478900f047c6e36cabcd8b18', START, 7)]
    ancestors = [START, '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3']
    require(payload['integratedAncestors'] == ancestors and len(payload['donorLinks']) == len(specs),
            'Original integrated base anchors or full seven-link closure differ')
    observed = {}
    object_ids = set()
    admitted = set()
    file_versions = 0
    overlap_count = 0
    view = 'Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift'
    for index, link in enumerate(payload['donorLinks']):
        commit, tree, parent, count = specs[index]
        prefix = 'original-donor-%02d' % (index + 1)
        require(link['commit'] == commit and link['tree'] == tree and link['parents'] == [parent]
                and len(link['files']) == count, 'Original full donor link differs')
        if parent in ancestors:
            commands.git(prefix + '-base-integrated', 'merge-base', '--is-ancestor', parent, START)
        else:
            require(parent in admitted, 'Donor parent is neither integrated nor an exact earlier admitted link')
        actual = commands.git(prefix + '-identity', 'show', '-s', '--format=%H %T %P', commit).decode().split()
        require(actual == [commit, tree, parent], 'Published donor commit/tree/parent differs')
        require(changes(commands, prefix + '-complete-diff', parent, commit)
                == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed full donor delta')
        paths = sorted(safe_path(path) for path in link['files'])
        leaves = parse_leaves(commands.git(prefix + '-exact-changed-leaves',
            'ls-tree', '-r', '-z', '--full-tree', tree, '--', *paths))
        require(set(leaves) == set(paths), 'Original complete donor paths differ')
        original = batch_blobs(commands, prefix + '-original-blobs',
                               {row['after']['gitBlob']: None for row in link['files'].values()})
        for path, donor_row in link['files'].items():
            row = payload['donorRows'][path]
            require_leaf(start_leaves, path, row['before'])
            require(donor_row['status'] == row['status'], 'Original donor status differs')
            if commit == specs[1][0] and path == view:
                selected = payload['retainedDonorFiles']['001f22cccfeb5bb78f0ccfe2caa52449e57101eb']
                require(path not in observed and selected['commit'] == commit, 'Original770 predecessor differs')
            else:
                selected = row
                require(row['donorCommit'] == commit, 'Final source must be the exact declared original donor')
            require(donor_row == {'status': row['status'], 'after': selected['after']}, 'Original whole donor identity differs')
            require_leaf(leaves, path, selected['after'])
            match(original[selected['after']['gitBlob']], selected['after'])
            require(original[selected['after']['gitBlob']] == base64.b64decode(selected['base64'], validate=True),
                    'Whole original donor bytes differ')
            if path in observed:
                require(path == view and commit == specs[2][0] and parent == specs[1][0]
                        and observed[path] == {'status': 'M', 'commit': specs[1][0],
                            'after': payload['retainedDonorFiles']['001f22cccfeb5bb78f0ccfe2caa52449e57101eb']['after']}
                        and selected['after']['gitBlob'] == '112250ced570144979043c9c0a5c58c4af33e22c',
                        'Only the exact770-to8785 RootView descendant may overlap')
                overlap_count += 1
            observed[path] = {'status': row['status'], 'commit': commit, 'after': selected['after']}
            file_versions += 1
        object_ids.update(original)
        admitted.add(commit)
    require(len(observed) == 171 and file_versions == 172 and overlap_count == 1
            and observed == {path: {'status': row['status'], 'commit': row['donorCommit'], 'after': row['after']}
                            for path, row in payload['donorRows'].items()}, 'Full172-version/171-path source closure differs')
    return object_ids


def validate_guards(commands, payload, before_leaves, target_leaves, prior, stage):
    guards = payload['guardInputs']
    require(stage in ('before', 'after') and guards['originalRetentionRows'] == 145
            and guards['expectedRetentionRows'] == 145 and guards['sourceMapUpdates'] == []
            and guards['sourceMapAppendedRows'] == [], 'The complete original145-row source map must remain unchanged')
    protected = {path: item for path, item in before_leaves.items()
                 if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
                 or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    target_protected = {path: item for path, item in target_leaves.items()
                 if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
                 or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    added_path = 'docs/validation/20261127-wave2-bookmark6-component-preparation/execution/Package.swift'
    added_leaf = {'mode': '100644', 'type': 'blob', 'sha': '735685e09fb81dc65d1f60f5930d19b21214f785'}
    require(len(protected) == 82 and protected == guards['protectedLeaves'] and added_path not in protected
            and guards['addedProtectedLeaves'] == {added_path: added_leaf} and guards['protectedUpdates'] == {}
            and len(target_protected) == guards['targetProtectedCount'] == 83
            and target_protected == {**protected, added_path: added_leaf},
            'All82 current protected leaves and only the exact original execution Package.swift must be retained')
    require(payload['donorRows'][added_path]['status'] == 'A'
            and payload['donorRows'][added_path]['after'] == {'bytes': 6987,
                'sha256': 'e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be',
                'gitBlob': added_leaf['sha'], 'gitMode': '100644'}, 'Original evidence package identity differs')
    before, after = guards['files'], guards['filesAfter']
    require(len(before) == len(after) == 52 and before == after and guards['reviewedGuardUpdates'] == {}
            and guards['addedClosedActivation'] == [] and guards['historicalNative26StorePromotionReapplied'] is False,
            'All52 current source witnesses must remain exact; no earlier promotion may be reapplied')
    values = batch_blobs(commands, 'guard-' + stage + '-original-files',
                         {row['gitBlob']: None for row in before.values()})
    for path, identity in before.items():
        require_leaf(before_leaves, path, identity)
        require_leaf(target_leaves, path, identity)
        require(path not in payload['donorRows'], 'Current source guard overlaps a new donor')
        match(values[identity['gitBlob']], identity)
    map_raw = values[before[MAP_PATH]['gitBlob']]
    require(len(json.loads(map_raw)['changes']) == 145
            and before[MAP_PATH]['gitBlob'] == '722a41b870957cf17f9724b8dd732b7d6088bde0',
            'Actual published map145 including row110 must remain byte-exact')
    store_path = 'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift'
    witness_path = 'Tools/PinkhaDualEngineRuntime/hosted_native26_properties/source_witnesses.json'
    witness = json.loads(values[before[witness_path]['gitBlob']])
    current_store = {'bytes': 53698, 'sha256': 'b91ed64c54ec552caa68a3b49c272ff8f008722b3a41fc76d9eadf4eaf9ef93b'}
    require(witness['appFixtureSources'][store_path] == current_store and len(witness['appFixtureSources']) == 7
            and witness['runtimeExecuted'] is False and witness['ordinaryStorage'] is False
            and before[witness_path]['gitBlob'] == '14d56994d8f02dd720018bdb827565ea6a551488'
            and guards['native26GuardPolicy'] == 'PRESERVE_CURRENT_FULL_BYTES_AND_CLOSED_FLAGS; NO_NATIVE27_PROMOTION',
            'Original closed Native26 witness must remain unchanged')
    actual_store = values[before[store_path]['gitBlob']]
    require(len(actual_store) == current_store['bytes'] and sha(actual_store) == current_store['sha256']
            and before[store_path]['gitBlob'] == 'b8de5482053e5f7e3bf6798608f09a98d291281a',
            'Current original Store source differs')
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
    for item in activation:
        path = item['path']
        require(path in before, 'Original closed activation source is not guarded')
        original = json.loads(values[before[path]['gitBlob']])
        for key, wanted in item['fields'].items():
            require(type(original[key]) is type(wanted) and original[key] == wanted
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
    donor_tree = private_tree(commands,'complete-w2-bookmark-language171-donor-preview',base_leaves,payload['donorRows'],donor_leaves)
    require(donor_tree == EXPECTED_DONOR_TREE,'Complete original171-path donor tree differs')
    diff_check(commands,'all-w2-bookmark-language171-donor-diff',['diff','--check','--no-renames',START,donor_tree],payload['diffChecks']['donors'],receipt)
    source_tree = private_tree(commands,'complete-composed-source-preview',base_leaves,rows,source_leaves)
    require(source_tree == EXPECTED_SOURCE_TREE,'Complete reviewed171-path source tree differs')
    diff_check(commands,'all-composed-source-diff',['diff','--check','--no-renames',START,source_tree],payload['diffChecks']['source'],receipt)
    final_guards = validate_guards(commands,payload,base_leaves,source_leaves,prior,'after')
    gate_leaf = base_leaves[GATE]
    require(gate_leaf == source_leaves[GATE] and gate_leaf['type'] == 'blob','Original retention gate source changed')
    gate_source = batch_blobs(commands,'original-retention-gate-source',{gate_leaf['sha']:None})[gate_leaf['sha']]
    require(read_regular(ROOT/GATE) == gate_source,'Working original retention gate differs')
    original_controller_leaf = base_leaves[ORIGINAL_CONTROLLER_PATH]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Original762 source controller is not retained')
    original_controller = batch_blobs(commands,'original-762-controller',{original_controller_leaf['sha']:None})[original_controller_leaf['sha']]
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA,'Original complete762 controller differs')
    self_raw = read_regular(Path(__file__))
    intake = {'schema':'pinkha-root-w2-bookmark-language171-source-intake/v1','start':START,'startTree':START_TREE,
        'normalMergeParents':[START,*DONORS],'donorTips':DONORS,'donorTree':donor_tree,'sourceTree':source_tree,
        'files':{path:{key:value for key,value in row.items() if key not in ('base64','beforeBase64')} for path,row in rows.items()},
        'controllerSHA256':sha(self_raw),'payloadSHA256':PAYLOAD_SHA,'positivePriorPublicationReceiptSHA256':sha(prior_raw),
        'originalUntrackedFiles':list(UNTRACKED),'originalUntrackedGroupedStatus':original['grouped'].decode(),
        'originalUntrackedFileIdentities':original['files'],'inputPins':before_guards,'outputPins':final_guards,
        'originalDiffChecks':payload['diffChecks'],'runtimeAcceptance':False,
        'compilerInvocations':0,'testsExecuted':0,'materializations':0,
        'historicalFailuresPreserved':True,
        'newRuntimeResultsClaimed':False,
        'normalDonorTipCount':4,
        'originalAncestryLinkCount':7,
        'originalFileVersionCount':172,
        'reviewedFinalDonorPaths':171,
        'modifiedProductPaths':4,
        'originalEvidenceAdditions':167,
        'explicitParentChildRootViewSupersession':True,
        'sourceMapRowsUnchanged':145,
        'protectedLeavesBefore':82,
        'protectedLeavesAfter':83,
        'currentWitnesses52Unchanged':True,
        'all45RuntimeTuplesRemainClosed':True,
        'originalNative26GuardsUnchanged':True,
        'newNative27StandaloneSelector':'NativeLaunchTests/testNativeBookmarkCancelCreateEditOpenAndColdReopen',
        'newNative27Status':'NOT_RUN_FUTURE_STANDALONE_ROUTE_CLOSED',
        'syntheticDefinitionsAreNotOriginalTypeMigration':True,
        'originalBookmark4XCTestResultsRetained':True,
        'missingTwoPreparationOnly':True,
        'missingTwoActualResult':'PENDING_NOT_INCLUDED',
        'mixedLanguageRuntimeAcceptance':False,
        'nativeCompilerSources':62,
        'stage1CompilerSources':10,
        'nativeUICompilerSources':2,
        'completeWarmSourceBindings':99,
        'warm22Methods34CasesThenPrepareAndEditor4Unchanged':True,
        'currentWarmSourceCommitUnchanged':'a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd',
        'noCurrentWarmReceiptRelabel':True,
    }
    evidence = {'root-source-intake.json':encoded(intake),'root-integration-controller.py':self_raw,
        'prior139-publication.original.json':prior_raw,
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
    receipt.update(phase='NORMAL_FOUR_TIP_SOURCE_MERGE',expectedDonorTree=donor_tree,expectedSourceTree=source_tree,expectedTree=whole_tree)
    resources()
    commands.git('normal-four-tip-w2-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'merge','--no-ff','--no-commit',*DONORS,timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS,'Normal four-tip donor parents differ')
    require(commands.git('actual-donor-stage','write-tree').decode().strip() == donor_tree
            and tree_leaves(commands,'actual-donor-leaves',donor_tree) == donor_leaves,
            'Normal donor merge differs; preserve state without automatic resolution')
    require(payload['rootRows'] == {}, 'No root product rewrite is part of this normal donor merge')
    require(commands.git('actual-composed-source-stage','write-tree').decode().strip() == source_tree,
            'Actual171-path source composition differs')
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
    receipt['phase'] = 'NORMAL_FIVE_PARENT_SOURCE_COMMIT'
    commands.git('normal-five-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'commit','-F','-',data=payload['finalCommitMessage'].encode(),timeout=45)
    head = commands.git('final-committed-head','rev-parse','HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree','show','-s','--format=%T %P',head).decode().split()
            == [whole_tree,START,*DONORS],'Normal five-parent merge ancestry differs')
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
    receipt = {'schema': 'pinkha-root-w2-bookmark-language171-source-integration/v1', 'state': 'RUNNING',
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
