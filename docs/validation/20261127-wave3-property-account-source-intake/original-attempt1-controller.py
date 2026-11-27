#!/usr/bin/env python3
"""Closed property Unicode and account lifetime source integration.

Retain the complete property donor, exact account sources, map145, unchanged
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
START = '9b510b5ea80fba508d01314cefb646682943f7a9'
START_TREE = '5e473fcc6c5d744fb27e75c402bd4dca35cf9cd1'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
UNTRACKED = (
    'Tools/Hanlin/__pycache__/prepare_sdk.cpython-312.pyc',
    'Tools/Hanlin/__pycache__/wave15_core_profile.cpython-312.pyc',
    'Tools/MiniApps/__pycache__/owner_signing.cpython-312.pyc',
    'Tools/PinkhaSimulatorGate/__pycache__/retain_current_composition_controls.cpython-312.pyc',
)
DONORS = ['937a8167700481b71c3c2eeb8771634d2c6bbc4f']
PRIOR = Path('/tmp/pinkha-root-uploader-host2-source-integration-20261127.json')
PAYLOAD = Path('/var/lib/sentinelx/uploads/pinkha-root-property-account-source-payload.json.gz')
EVIDENCE = Path('/mnt/development/projects/evidence/pinkha-root-property-account-source-integration-20261127')
PRIVATE = Path('/tmp/pinkha-root-property-account-source-index-20261127')
OUT = Path('/tmp/pinkha-root-property-account-source-integration-20261127.json')
PREFIX = 'docs/validation/20261127-wave3-property-account-source-intake'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
GATE_OUT = Path('/tmp/pinkha-root-property-account-source-retention-20261127.json')
PACKED_BYTES = 713917
PACKED_SHA = '875f830cc7383dd5dbd0ba810cc94b4b3b5efe370b14d52a113940237b35d879'
PAYLOAD_BYTES = 2575219
PAYLOAD_SHA = 'a9dfb6a9ccd28a40fd4b923ddf7ad43bfc4c4f2d2dadd4f6b421cf9ffa2798ef'
MAX_SECONDS = 300
MAX_LOG = 16 * 1024**2
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
SOURCE_ROW_COUNT = 57
FIXED_EVIDENCE_COUNT = 8
EXPECTED_DONOR_TREE = '0798471302be402f7348d40b4472ec8638e94f87'
EXPECTED_SOURCE_TREE = '64cca3dd4c64f6aca832044cf3c3cbe1609b7c0d'

SDK = 'c0b118f4de28e6ca1e71219237d1ae1c7fabefd8'
MAP_PATH = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
ORIGINAL_CONTROLLER_SHA = 'f8088cc796d07ad4aa5c213c92e94d42721d958dad325bbec7eabab4e6f81e4c'
ORIGINAL_CONTROLLER_PATH = 'docs/validation/20261127-wave3-uploader-host2-source-intake/root-integration-controller.py'
PRIOR_BYTES = 308086
PRIOR_SHA = 'd4f588c4fe92095b0bee967c5a86bff9f03cf0dd92541874df45da0084e35bdf'
PRIOR_COMMAND_COUNT = 108
PRIOR_CONTROLLER_SHA = 'f8088cc796d07ad4aa5c213c92e94d42721d958dad325bbec7eabab4e6f81e4c'
PRIOR_PAYLOAD_SHA = '2d2920472063164b2e12f3bda5ab497ca85e0cfcbd79fa2d30123960f93726e6'


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
    require(isinstance(PRIOR_BYTES, int) and 0 < PRIOR_BYTES <= MAX_LOG
            and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '')
            and PRIOR_COMMAND_COUNT == 108, 'Positive actual uploader/Host2 publication receipt is unbound')
    raw = read_regular(PRIOR, PRIOR_BYTES)
    require(len(raw) == PRIOR_BYTES and sha(raw) == PRIOR_SHA, 'Actual original uploader/Host2 receipt differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-uploader-host2-source-integration/v1'
            and value['state'] == 'SOURCE_NORMAL_MERGE_PUBLISHED_RUNTIME_CLOSED'
            and value['head'] == value['normalPushReadback'] == START and value['tree'] == START_TREE
            and value['start'] == '2e312d361f6782ca7365d4bacc1e231b27571cd4'
            and value['startTree'] == '88aafd76799e8d13782d7d0d8a79b0a02b8c6a17'
            and value['controllerSHA256'] == PRIOR_CONTROLLER_SHA
            and value['payloadSHA256'] == PRIOR_PAYLOAD_SHA
            and value['sourceRetentionPassed'] is True and value['reviewedRefactors'] == 144
            and value['normalPushCompleted'] is True and value['commandCustodyBlocked'] is False
            and value['firstFailure'] is None and value['runtimeAcceptance'] is False
            and value['originalUntrackedPreserved'] is True,
            'Only the actual successful original uploader/Host2 source publication is admitted')
    parents = ['2e312d361f6782ca7365d4bacc1e231b27571cd4',
        '063d3ef0b16392f67e5044faa81cf8689a75dab2', '3b1560a4fb129c9f343fddd6559e9e472f165464']
    require(value['localMergeCommits'] == [{'head': START, 'tree': START_TREE, 'parents': parents}]
            and value['donorTips'] == parents[1:], 'Actual original normal merge ancestry differs')
    require(all(value[key] == 0 for key in ('compilerInvocations', 'testsExecuted', 'materializations')),
            'Prior source-only scope changed')
    require(value['outputPins']['sdk'] == SDK and len(value['outputPins']['allPackagePins']) == 56
            and value['inputPins'] == value['outputPins'] and value['outputPins']['reviewedRefactors'] == 144
            and len(value['outputPins']['closedActivation']) == 41, 'Published original pin and runtime closure differ')
    require(len(value['commands']) == PRIOR_COMMAND_COUNT, 'Actual prior command count differs')
    labels = {'all-donor-source-diff', 'complete-final-preview-diff', 'actual-complete-index-diff'}
    seen = set()
    for command in value['commands']:
        require(command.get('originalProcessGroupAbsent') is True and command.get('cleanupSignals') == []
                and not command.get('cleanupFailure') and not command.get('receiptFailure'),
                'Actual prior source publication has unresolved command custody')
        if command['label'] in labels:
            seen.add(command['label'])
            require(command['exitCode'] == 2 and command['stdout']['bytes'] == 1937
                    and command['stdout']['sha256'] == '3affcfbb81cc4e07189c9d8d584f317127ada5476d3c52e46711158f58c0de11'
                    and command['stderr']['bytes'] == 0, 'Original retained whitespace diagnostic differs')
        else:
            require(command['exitCode'] == 0, 'Unexpected prior publication command failure')
    require(seen == labels, 'Original three retained diff outcomes are incomplete')
    # Historical custody is read from the original receipt; old process IDs are never probed.
    return raw, value


def source_payload():
    require(re.fullmatch('[a-f0-9]{40}', START or '') and re.fullmatch('[a-f0-9]{40}', START_TREE or '')
            and isinstance(PRIOR_BYTES, int) and re.fullmatch('[a-f0-9]{64}', PRIOR_SHA or '')
            and PRIOR_COMMAND_COUNT == 108 and isinstance(PACKED_BYTES, int) and isinstance(PAYLOAD_BYTES, int)
            and re.fullmatch('[a-f0-9]{64}', PACKED_SHA or '')
            and re.fullmatch('[a-f0-9]{64}', PAYLOAD_SHA or ''), 'Final source tuple is unbound; no host action')
    require(0 < PAYLOAD_BYTES <= MAX_LOG and 0 < PACKED_BYTES <= MAX_LOG, 'Bounded exact source payload required')
    packed = read_regular(PAYLOAD, PACKED_BYTES)
    require(len(packed) == PACKED_BYTES and sha(packed) == PACKED_SHA, 'Packed source payload differs')
    raw = gzip.decompress(packed)
    require(len(raw) == PAYLOAD_BYTES and sha(raw) == PAYLOAD_SHA, 'Complete source payload differs')
    value = json.loads(raw)
    require(value['schema'] == 'pinkha-root-property-account-source-payload/v1'
            and value['start'] == START and value['startTree'] == START_TREE and value['bindingReady'] is True
            and value['priorReceipt'] == {'path': str(PRIOR), 'bytes': PRIOR_BYTES, 'sha256': PRIOR_SHA}
            and value['priorCommandCount'] == PRIOR_COMMAND_COUNT and value['donorTips'] == DONORS,
            'Closed source and actual publication tuple differ')
    require(value['runtimeAcceptance'] is False and all(value[key] == 0 for key in
            ('testsExecuted', 'compilerInvocations', 'materializations')), 'No runtime activation from source intake')
    require(len(value['donorRows']) == 32 and len(value['rootRows']) == 25
            and not (set(value['donorRows']) & set(value['rootRows']))
            and len(value['donorLinks']) == 1 and value['retainedDonorFiles'] == {},
            'Only the exact32 donor and25 reviewed account paths are admitted')
    rows = {**value['donorRows'], **value['rootRows']}
    values = decode_rows(rows)
    require(len(rows) == SOURCE_ROW_COUNT == 57
            and sum(row['status'] == 'M' for row in rows.values()) == 8
            and sum(row['status'] == 'A' for row in rows.values()) == 49,
            'Only the exact eight replacements and49 source/evidence additions are admitted')
    require(value['finalSourcePathCount'] == SOURCE_ROW_COUNT
            and value['guardInputs']['sdkRevision'] == SDK and value['guardInputs']['selectedKitRevision'] == KIT
            and value['expectedDonorTree'] == EXPECTED_DONOR_TREE
            and value['expectedSourceTree'] == EXPECTED_SOURCE_TREE,
            'SDK, Kit or complete source projection differs')
    require(set(value['diffChecks']) == {'donors', 'source', 'complete'}, 'Finite raw diff scopes required')
    for expected in value['diffChecks'].values():
        require(expected['exit'] in (0, 2) and isinstance(expected['stdout'], str) and isinstance(expected['stderr'], str),
                'Original finite Git diagnostic is not bound')
    require(len(value['evidence']) == FIXED_EVIDENCE_COUNT, 'Fixed source-intake evidence count differs')
    return raw, packed, value, rows, values


def validate_donors(commands, payload, start_leaves):
    commands.git('fetch-exact-property-donor', 'fetch', '--no-tags', '--refmap=', 'origin', *DONORS,
                 publish=True, timeout=60)
    require(DONORS == ['937a8167700481b71c3c2eeb8771634d2c6bbc4f']
            and payload['integratedAncestors'] == ['af63f6209c38bddf6ed851f0b894e2f627a671af'],
            'Exact property donor ancestry differs')
    ancestor = payload['integratedAncestors'][0]
    commands.git('original-property-base-integrated', 'merge-base', '--is-ancestor', ancestor, START)
    link = payload['donorLinks'][0]
    require(link['commit'] == DONORS[0] and link['parents'] == [ancestor]
            and link['tree'] == 'd23e68a911d2fe275c4dd1eb282d1b59d4bb260a', 'Original property link differs')
    actual = commands.git('property-donor-identity', 'show', '-s', '--format=%H %T %P', link['commit']).decode().split()
    require(actual == [link['commit'], link['tree'], *link['parents']], 'Published donor commit/tree/parent differs')
    require(changes(commands, 'property-donor-complete-diff', ancestor, link['commit'])
            == {path: row['status'] for path, row in link['files'].items()}, 'Unreviewed full donor delta')
    paths = sorted(safe_path(path) for path in link['files'])
    leaves = parse_leaves(commands.git('property-donor-exact-changed-leaves',
        'ls-tree', '-r', '-z', '--full-tree', link['tree'], '--', *paths))
    require(set(leaves) == set(paths) == set(payload['donorRows']), 'Whole32-path original donor set differs')
    original = batch_blobs(commands, 'all-original-property-donor-blobs',
                           {row['after']['gitBlob']: None for row in link['files'].values()})
    for path, row in payload['donorRows'].items():
        require_leaf(start_leaves, path, row['before'])
        require_leaf(leaves, path, row['after'])
        require(link['files'][path] == {'status': row['status'], 'after': row['after']}, 'Reviewed donor row differs')
        match(original[row['after']['gitBlob']], row['after'])
        require(original[row['after']['gitBlob']] == base64.b64decode(row['base64'], validate=True),
                'Final original donor bytes differ')
    return set(original)


def validate_guards(commands, payload, before_leaves, target_leaves, prior, stage):
    guards = payload['guardInputs']
    require(stage in ('before', 'after') and guards['originalRetentionRows'] == 144
            and guards['expectedRetentionRows'] == 145, 'Exact144-to145 retention scope required')
    protected = {path: leaf for path, leaf in before_leaves.items()
                 if path.endswith('/Package.swift') or path.endswith('/Package.resolved')
                 or path.endswith('/project.pbxproj') or path in ('Tools/Hanlin/source.json', MAP_PATH)}
    require(len(protected) == 77 and protected == guards['protectedLeaves'], 'Original77 protected paths differ')
    for path, leaf in protected.items():
        if path == MAP_PATH:
            require_leaf(target_leaves, path, payload['rootRows'][path]['after'])
        else:
            require(target_leaves.get(path) == leaf, 'Original package/lock/PBX/SDK source changed: ' + path)
    before = guards['files']
    after = guards['filesAfter']
    added = guards['addedClosedActivation']
    require(len(before) == 47 and len(after) == 51 and len(added) == 4
            and len({row['path'] for row in added}) == 4, 'Finite guard source inventory differs')
    allowed = {MAP_PATH, 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'}
    require(set(after) == set(before) | {row['path'] for row in added}
            and all(after[path] == identity for path, identity in before.items() if path not in allowed),
            'An original guard outside the exact map/register changed')
    for path in allowed | {row['path'] for row in added}:
        require(after[path] == payload['rootRows'][path]['after'], 'Guard does not bind exact reviewed root bytes')
    identities = {row['gitBlob']: None for row in before.values()}
    if stage == 'after':
        identities.update({row['gitBlob']: None for row in after.values()})
    values = batch_blobs(commands, 'guard-' + stage + '-original-files', identities)
    for path, identity in before.items():
        require_leaf(before_leaves, path, identity)
        match(values[identity['gitBlob']], identity)
    for path, identity in after.items():
        require_leaf(target_leaves, path, identity)
        if stage == 'after':
            match(values[identity['gitBlob']], identity)
    for witness in added:
        require(witness['path'] not in before_leaves, 'New account control overwrites an existing path')
    old_map_raw = values[before[MAP_PATH]['gitBlob']]
    new_map_raw = base64.b64decode(payload['rootRows'][MAP_PATH]['base64'], validate=True)
    match(new_map_raw, after[MAP_PATH])
    require(base64.b64decode(payload['rootRows'][MAP_PATH]['beforeBase64'], validate=True) == old_map_raw,
            'Original map preimage differs')
    operations = guards['mapByteInverse']
    require(len(operations) == 4, 'Only three exact replacement literals and one map appendix are admitted')
    restored = new_map_raw
    for operation in reversed(operations):
        lo, hi = operation['newStartByte'], operation['newEndByte']
        current = base64.b64decode(operation['newBase64'], validate=True)
        previous = base64.b64decode(operation['originalBase64'], validate=True)
        require(0 <= lo <= hi <= len(restored) and restored[lo:hi] == current, 'Exact raw map inverse span differs')
        restored = restored[:lo] + previous + restored[hi:]
    require(restored == old_map_raw, 'Every original map byte outside the four exact operations must be retained')
    old_map, new_map = json.loads(old_map_raw), json.loads(new_map_raw)
    require(len(old_map['changes']) == 144 and len(new_map['changes']) == 145
            and {key: value for key, value in old_map.items() if key != 'changes'}
                == {key: value for key, value in new_map.items() if key != 'changes'}, 'Map metadata or exact row count changed')
    updates = {15: 'Anytype/Sources/Pinkha/AI/PinkhaHanlinAuthService.swift',
               133: 'Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift',
               139: 'Anytype/Sources/Pinkha/Bootstrap/PinkhaBootstrapHook.swift'}
    for index, previous in enumerate(old_map['changes']):
        wanted = dict(previous)
        if index in updates:
            wanted['replacementBlob'] = payload['rootRows'][updates[index]]['after']['gitBlob']
        require(new_map['changes'][index] == wanted, 'Existing map row changed outside its exact replacement field')
    require(new_map['changes'][144] == guards['appendedMapping'], 'Exact original586 account-test mapping differs')
    test_path = 'AnyTypeTests/Pinkha/PinkhaBootstrapStateManagerTests.swift'
    require(guards['appendedMapping']['baselineBlob'] == '25931d7cfa84f8544f97aa11c5d57b470b1a2258'
            and guards['appendedMapping']['replacementBlob'] == payload['rootRows'][test_path]['after']['gitBlob'],
            'New test row is not bound to its original586 and actual reviewed test')
    register_path = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
    old_register = values[before[register_path]['gitBlob']]
    new_register = base64.b64decode(payload['rootRows'][register_path]['base64'], validate=True)
    require(base64.b64decode(payload['rootRows'][register_path]['beforeBase64'], validate=True) == old_register
            and len(new_register) > len(old_register) and new_register.startswith(old_register),
            'Original exception register is not preserved as an exact byte prefix')
    sdk = json.loads(values[before['Tools/Hanlin/source.json']['gitBlob']])
    lock_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    pins = json.loads(values[before[lock_path]['gitBlob']])['pins']
    require(sdk['revision'] == SDK == guards['sdkRevision'] and pins == prior['outputPins']['allPackagePins']
            and pins == guards['inputPins']['allPackagePins'] and len(pins) == 56,
            'Original SDK or56 selected main package pins changed')
    require([pin['state']['revision'] for pin in pins if pin['identity'].casefold() == 'torahinspectorkit'] == [KIT],
            'Selected original Kit26 changed')
    activation = guards['closedActivation']
    require(activation == prior['outputPins']['closedActivation'] and len(activation) == 41,
            'Original closed runtime-source tuple differs')
    for witness in activation:
        require(witness['path'] in before, 'Original closed activation source is not guarded')
        current = json.loads(values[before[witness['path']]['gitBlob']])
        for key, wanted in witness['fields'].items():
            require(type(current[key]) is type(wanted) and current[key] == wanted
                    and (wanted is None or wanted is False or wanted == []), 'Original runtime activation changed')
    new_controls = {}
    for witness in added:
        path = witness['path']
        raw = base64.b64decode(payload['rootRows'][path]['base64'], validate=True)
        match(raw, after[path])
        current = json.loads(raw)
        new_controls[path.rsplit('/', 1)[1]] = current
        for key, wanted in witness['fields'].items():
            require(type(current[key]) is type(wanted) and current[key] == wanted
                    and (wanted is None or wanted is False or wanted == []), 'New account runtime must remain closed')
    require(set(new_controls) == {'activation.json', 'profile-dependency.json', 'profile.json', 'source-inverse.json'},
            'Only four exact account control witnesses may be appended')
    a, d, p = (new_controls[name] for name in ('activation.json', 'profile-dependency.json', 'profile.json'))
    require(type(a['runtimeTestsExecuted']) is int and a['runtimeTestsExecuted'] == 0
            and type(p['testsExecuted']) is int and p['testsExecuted'] == 0
            and a['expectedMethods'] == d['reviewedMethodCount'] == p['methods'] == 4
            and a['expectedCases'] == d['reviewedCaseCount'] == p['declaredCases'] == 5
            and d['newTestImplementation'] is True and d['newFiniteProfileImplementation'] is True
            and p['compilerScope']['currentNativeSourcePaths'] == 61
            and p['compilerScope']['currentStage1UISourcePaths'] == 10
            and p['compilerScope']['separateNativeUIRunnerRequired'] is False
            and p['processContract']['newWorkflowOrRuntimeRouteCreated'] is False,
            'Declared account source scope was confused with actual compilation or execution')
    before_result = {'sdk': SDK, 'allPackagePins': pins, 'reviewedRefactors': 144,
                     'closedActivation': activation, 'sourceOnly': True}
    require(before_result == prior['outputPins'] == guards['inputPins'], 'Original complete source-only pin tuple changed')
    if stage == 'before':
        return before_result
    result = {'sdk': SDK, 'allPackagePins': pins, 'reviewedRefactors': 145,
              'closedActivation': [*activation, *added], 'sourceOnly': True}
    require(result == guards['outputPins'], 'Only the reviewed map and four closed account witnesses may extend output pins')
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
    donor_tree = private_tree(commands,'complete-property-donor-preview',base_leaves,payload['donorRows'],donor_leaves)
    require(donor_tree == EXPECTED_DONOR_TREE,'Complete original property donor tree differs')
    diff_check(commands,'all-property-donor-diff',['diff','--check','--no-renames',START,donor_tree],payload['diffChecks']['donors'],receipt)
    source_tree = private_tree(commands,'complete-composed-source-preview',base_leaves,rows,source_leaves)
    require(source_tree == EXPECTED_SOURCE_TREE,'Complete reviewed57-path source tree differs')
    diff_check(commands,'all-composed-source-diff',['diff','--check','--no-renames',START,source_tree],payload['diffChecks']['source'],receipt)
    final_guards = validate_guards(commands,payload,base_leaves,source_leaves,prior,'after')
    gate_leaf = base_leaves[GATE]
    require(gate_leaf == source_leaves[GATE] and gate_leaf['type'] == 'blob','Original retention gate source changed')
    gate_source = batch_blobs(commands,'original-retention-gate-source',{gate_leaf['sha']:None})[gate_leaf['sha']]
    require(read_regular(ROOT/GATE) == gate_source,'Working original retention gate differs')
    original_controller_leaf = base_leaves[ORIGINAL_CONTROLLER_PATH]
    require(original_controller_leaf['mode'] == '100644' and original_controller_leaf['type'] == 'blob',
            'Original f808 source controller is not retained')
    original_controller = batch_blobs(commands,'original-f808-controller',{original_controller_leaf['sha']:None})[original_controller_leaf['sha']]
    require(sha(original_controller) == ORIGINAL_CONTROLLER_SHA,'Original complete f808 controller differs')
    self_raw = read_regular(Path(__file__))
    intake = {'schema':'pinkha-root-property-account-source-intake/v1','start':START,'startTree':START_TREE,
        'normalMergeParents':[START,*DONORS],'donorTips':DONORS,'donorTree':donor_tree,'sourceTree':source_tree,
        'files':{path:{key:value for key,value in row.items() if key not in ('base64','beforeBase64')} for path,row in rows.items()},
        'controllerSHA256':sha(self_raw),'payloadSHA256':PAYLOAD_SHA,'positivePriorPublicationReceiptSHA256':sha(prior_raw),
        'originalUntrackedFiles':list(UNTRACKED),'originalUntrackedGroupedStatus':original['grouped'].decode(),
        'originalUntrackedFileIdentities':original['files'],'inputPins':before_guards,'outputPins':final_guards,
        'originalDiffChecks':payload['diffChecks'],'runtimeAcceptance':False,
        'compilerInvocations':0,'testsExecuted':0,'materializations':0,
        'historicalFailuresPreserved':True,'propertyReadbackRuntimeQualified':False,
        'accountDeclaredMethods':4,'accountDeclaredCases':5,'accountRuntimeQualified':False,
        'native26StoreWitnessUnchangedHistoricalClosed':True,'warm22Methods34CasesAndEditor4Unchanged':True}
    evidence = {'root-source-intake.json':encoded(intake),'root-integration-controller.py':self_raw,
        'prior-uploader-host2-publication.original.json':prior_raw,
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
    receipt.update(phase='NORMAL_PROPERTY_DONOR_MERGE',expectedDonorTree=donor_tree,expectedSourceTree=source_tree,expectedTree=whole_tree)
    resources()
    commands.git('normal-property-source-merge','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'merge','--no-ff','--no-commit',*DONORS,timeout=60)
    require(read_regular(merge_head).decode().split() == DONORS,'Normal property merge parent differs')
    require(commands.git('actual-donor-stage','write-tree').decode().strip() == donor_tree
            and tree_leaves(commands,'actual-donor-leaves',donor_tree) == donor_leaves,
            'Normal donor merge differs; preserve state without automatic resolution')
    root_rows = payload['rootRows']
    root_previous = {path:None if row['before'] is None else base64.b64decode(row['beforeBase64'],validate=True)
                     for path,row in root_rows.items()}
    write_owned_batch(commands,'write-exact-account-source',root_rows,values,root_previous)
    commands.git('stage-only-exact-account-source','add','--sparse','--',*sorted(root_rows))
    require(commands.git('actual-composed-source-stage','write-tree').decode().strip() == source_tree,
            'Actual57-path source composition differs')
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
    receipt['phase'] = 'NORMAL_TWO_PARENT_SOURCE_COMMIT'
    commands.git('normal-two-parent-source-commit','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com',
        'commit','-F','-',data=payload['finalCommitMessage'].encode(),timeout=45)
    head = commands.git('final-committed-head','rev-parse','HEAD').decode().strip()
    receipt['head'] = head
    require(commands.git('final-committed-parent-tree','show','-s','--format=%T %P',head).decode().split()
            == [whole_tree,START,*DONORS],'Normal two-parent merge ancestry differs')
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
    receipt = {'schema': 'pinkha-root-property-account-source-integration/v1', 'state': 'RUNNING',
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
