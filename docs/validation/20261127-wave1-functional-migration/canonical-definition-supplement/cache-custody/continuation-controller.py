#!/usr/bin/env python3
"""Preserve one inactive owned Swift cache across a physical-volume move.

No native or compiler dispatch. All original bytes stay until a durable exact
destination readback and stable-path readback succeed. ctime/inode/device are
recorded for source race checks, never claimed portable between filesystems.
"""
from pathlib import Path
import base64
import collections
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import time
import traceback

SRC = Path('/tmp/pinkha-w1-migration-swift-20261127')
DST = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
STAGE = DST.with_name(DST.name + '.copying-relocation2')
RETIRED = SRC.with_name(SRC.name + '.verified-retired-relocation2')
LINK = SRC.with_name(SRC.name + '.new-stable-link-relocation2')
OUT = Path('/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1')
PRIOR = OUT.parent / 'swift-cache-relocation2'
BUILD = OUT.parent / 'canonical-definition-components-attempt3/result.json'
BUILD_SHA = 'd9bf1c3911219e2227c17db48726a8508030a20f7557f19934504f599b76c69b'
MIB = 1024**2
NOATIME = os.O_NOATIME
os.umask(0o077)
OUT.mkdir(mode=0o700, exist_ok=False)
started = time.monotonic()
result = {'status': 'RUNNING', 'protocol': 'pinkha-owned-exact-swift-cache-relocation-v1',
          'source': str(SRC), 'destination': str(DST), 'staging': str(STAGE), 'retired': str(RETIRED),
          'compilerInvocations': 0, 'nativeInvocations': 0, 'errors': [], 'copiedFiles': 0,
          'originalDuplicateRemoved': False, 'stableSymlinkInstalled': False,
          'rootBefore': shutil.disk_usage('/').free, 'destinationBefore': shutil.disk_usage(DST.parent).free,
          'sourceRaceIdentityFields': ['device', 'inode', 'ctime_ns', 'nlink'],
          'portableMetadataFields': ['kind', 'mode', 'uid', 'gid', 'atime_ns', 'mtime_ns', 'xattrs', 'hardlinkTopology', 'symlinkTarget']}
phase = 'admission'

def interrupted(*_):
    raise RuntimeError('owned cache relocation interrupted')

signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

def durable_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | NOATIME)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def write(path, value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b'\n'
    temp = path.with_name(path.name + '.new')
    with temp.open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path); durable_directory(path.parent)

def save():
    result['phase'] = phase
    result['seconds'] = round(time.monotonic() - started, 3)
    write(OUT / 'result.json', result)

def guard():
    assert time.monotonic() - started < 900, 'bounded custody deadline'
    assert shutil.disk_usage(DST.parent).free >= 512 * MIB, 'destination emergency reserve'
    assert not (OUT / 'abort').exists(), 'owned relocation abort'

def hash_file(path):
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | NOATIME)
    try:
        while True:
            data = os.read(fd, MIB)
            if not data: break
            h.update(data)
    finally:
        os.close(fd)
    return h.hexdigest()

def users():
    roots = [str(p) for p in [SRC, DST, STAGE, RETIRED]]
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid(): continue
        try:
            command = (proc / 'cmdline').read_bytes()
            match = any(root.encode() in command for root in roots)
            links = [proc / 'cwd', proc / 'exe']
            if not match:
                links += list((proc / 'fd').iterdir())
            for link in links:
                try:
                    target = os.readlink(link)
                    if any(target == root or target.startswith(root + '/') for root in roots): match = True; break
                except OSError: pass
            if match:
                found.append({'pid': int(proc.name), 'comm': (proc / 'comm').read_text().strip()})
        except (FileNotFoundError, PermissionError, ProcessLookupError): pass
    return found

def manifest(root, symlink_witness=None):
    rows, identities, links = [], {}, collections.defaultdict(list)
    stack = [root]
    while stack:
        path = stack.pop()
        before = path.lstat()
        relative = path.relative_to(root).as_posix()
        kind = ('directory' if stat.S_ISDIR(before.st_mode) else
                'file' if stat.S_ISREG(before.st_mode) else
                'symlink' if stat.S_ISLNK(before.st_mode) else 'special')
        assert kind != 'special', 'non-preservable special file: ' + relative
        row = {'path': relative, 'kind': kind, 'mode': stat.S_IMODE(before.st_mode),
               'uid': before.st_uid, 'gid': before.st_gid,
               'atime_ns': before.st_atime_ns, 'mtime_ns': before.st_mtime_ns,
               'xattrs': {key: base64.b64encode(os.getxattr(path, key, follow_symlinks=False)).decode()
                         for key in sorted(os.listxattr(path, follow_symlinks=False))}}
        assert sum(len(v) for v in row['xattrs'].values()) <= MIB
        if kind == 'file':
            row.update(bytes=before.st_size, sha256=hash_file(path), nlink=before.st_nlink)
            if before.st_nlink > 1: links[(before.st_dev, before.st_ino)].append(relative)
        elif kind == 'symlink':
            if symlink_witness is None:
                row['target'] = os.readlink(path)
            else:
                witness = symlink_witness[relative]
                stamp = [before.st_dev, before.st_ino, before.st_mode, before.st_uid, before.st_gid, before.st_size, before.st_atime_ns, before.st_mtime_ns, before.st_ctime_ns, before.st_nlink]
                assert stamp == witness['lstatIdentity'], 'verified symlink changed after target read/atime restoration'
                row['target'] = witness['target']
            row['bytes'] = before.st_size
        else:
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | NOATIME)
            try:
                with os.scandir(fd) as entries:
                    children = sorted(entry.name for entry in entries)
            finally:
                os.close(fd)
            stack.extend(path / name for name in reversed(children))
        after = path.lstat()
        identity = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_size,
                              s.st_mtime_ns, s.st_ctime_ns, s.st_nlink]
        assert identity(before) == identity(after), 'source changed while hashing: ' + relative
        # Reading an existing symlink may update its access time under
        # relatime. Capture that observed metadata, never a stale pre-read value.
        row['atime_ns'] = after.st_atime_ns
        identities[relative] = identity(after)
        rows.append(row)
        if len(rows) % 64 == 0: guard()
    rows.sort(key=lambda row: row['path'])
    topology = sorted(sorted(paths) for paths in links.values())
    by_path = {row['path']: row for row in rows}
    for paths in topology:
        assert all(by_path[p]['nlink'] == len(paths) for p in paths), 'hardlink escapes owned cache'
    return {'entries': rows, 'hardlinkTopology': topology}, identities

def restore_metadata(path, row):
    os.chown(path, row['uid'], row['gid'], follow_symlinks=False)
    if row['kind'] != 'symlink': os.chmod(path, row['mode'], follow_symlinks=False)
    else: assert stat.S_IMODE(path.lstat().st_mode) == row['mode']
    existing = set(os.listxattr(path, follow_symlinks=False))
    for key in existing - set(row['xattrs']): os.removexattr(path, key, follow_symlinks=False)
    for key, value in row['xattrs'].items(): os.setxattr(path, key, base64.b64decode(value), follow_symlinks=False)
    os.utime(path, ns=(row['atime_ns'], row['mtime_ns']), follow_symlinks=False)

try:
    assert SRC.is_dir() and not SRC.is_symlink()
    assert STAGE.is_dir() and not STAGE.is_symlink()
    assert all(not p.exists() and not p.is_symlink() for p in [DST, RETIRED, LINK])
    assert hash_file(PRIOR / 'result.json') == '4ef5b081ca0792d328ca4e570ebefbf57d9f964fd71e886c4fab3007582ff103'
    assert hash_file(PRIOR / 'source-before.json') == 'a98bab098d0f9f091bd8c280f23cc1863d76264f180474a00417deae810858a1'
    assert hash_file(PRIOR / 'destination-copy.json') == '7e8e34ed3a467169ffafdb95a02b620b1660cb139ab2fbb4d8bd3e64a4bf6606'
    previous = json.loads((PRIOR / 'result.json').read_bytes())
    assert previous['status'] == 'FAIL_CUSTODY_ORIGINAL_DATA_NOT_AUTHORIZED_FOR_RETIREMENT'
    assert previous['phase'] == 'independent durable destination readback'
    assert not previous['originalDuplicateRemoved'] and not previous['stableSymlinkInstalled']
    before = json.loads((PRIOR / 'source-before.json').read_bytes())
    before_identity = json.loads((PRIOR / 'source-identities-before.json').read_bytes())
    old_copy = json.loads((PRIOR / 'destination-copy.json').read_bytes())
    assert before['hardlinkTopology'] == old_copy['hardlinkTopology'] == []
    original_rows = {r['path']: r for r in before['entries']}
    copied_rows = {r['path']: r for r in old_copy['entries']}
    assert set(original_rows) == set(copied_rows) and len(original_rows) == 6906
    deltas = [(name, key) for name in original_rows for key in set(original_rows[name]) | set(copied_rows[name])
              if original_rows[name].get(key) != copied_rows[name].get(key)]
    assert deltas == [('debug', 'atime_ns')]
    result['mode'] = 'CONTINUE_EXACT_EXISTING_STAGED_COPY_WITHOUT_RECOPY'
    result['priorFailureReceiptSHA256'] = hash_file(PRIOR / 'result.json')
    result['readbackSideEffect'] = {'path': 'debug', 'field': 'atime_ns',
        'sourceValue': original_rows['debug']['atime_ns'], 'priorCopyValue': copied_rows['debug']['atime_ns'],
        'cause': 'readlink updates symlink access time on destination filesystem',
        'sourceBytesOrMetadataChangedByCorrection': False}
    assert hash_file(BUILD) == BUILD_SHA
    build = json.loads(BUILD.read_bytes())
    assert build['status'] == 'PASS' and build['compiled'] and build['ownedGroupAbsent']
    result['qualifiedProducts'] = build['compiledProducts']
    result['usersBefore'] = users(); assert not result['usersBefore']
    current, identity = manifest(SRC)
    assert current == before and identity == before_identity, 'original cache changed since accepted copy admission'
    write(OUT / 'source-before.json', before)
    write(OUT / 'source-identities-before.json', before_identity)
    result['sourceManifestSHA256'] = hash_file(OUT / 'source-before.json')
    result['sourceIdentitySHA256'] = hash_file(OUT / 'source-identities-before.json')
    result['entryCount'] = len(before['entries'])
    result['kinds'] = dict(collections.Counter(row['kind'] for row in before['entries']))
    result['hardlinkGroups'] = 0
    result['priorCopiedRegularFiles'] = previous['copiedFiles']
    result['newCopiedBytes'] = 0
    for relative, expected in build['compiledProducts'].items(): assert hash_file(SRC / relative) == expected
    guard()
    link = STAGE / 'debug'; row = original_rows['debug']
    assert link.is_symlink() and row['kind'] == 'symlink'
    assert os.readlink(link) == row['target']
    os.utime(link, ns=(row['atime_ns'], row['mtime_ns']), follow_symlinks=False)
    info = link.lstat()
    assert info.st_atime_ns == row['atime_ns'] and info.st_mtime_ns == row['mtime_ns']
    symlink_witness = {'debug': {'target': row['target'], 'lstatIdentity': [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid, info.st_size, info.st_atime_ns, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink]}}
    write(OUT / 'staged-symlink-target-and-restored-atime.json', symlink_witness)
    durable_directory(STAGE)
    result['symlinkVerification'] = 'Exact target read once, then only lstat identity/metadata checks after restoring original atime'
    phase = 'independent durable destination readback'; save()
    copied, _ = manifest(STAGE, symlink_witness)
    write(OUT / 'destination-copy.json', copied)
    assert copied == before, 'destination bytes/metadata/link topology mismatch'
    current, identity = manifest(SRC)
    assert current == before and identity == before_identity, 'original cache changed during copy'
    result['usersBeforeSwitch'] = users(); assert not result['usersBeforeSwitch']
    os.rename(STAGE, DST); durable_directory(DST.parent)
    os.symlink(str(DST), LINK); durable_directory(SRC.parent)
    os.rename(SRC, RETIRED)
    os.replace(LINK, SRC); durable_directory(SRC.parent)
    result['stableSymlinkInstalled'] = True
    phase = 'stable path products and dependency readback'; save()
    assert SRC.is_symlink() and os.readlink(SRC) == str(DST) and SRC.resolve() == DST
    stable, _ = manifest(SRC.resolve(), symlink_witness)
    assert stable == before
    for relative, expected in build['compiledProducts'].items(): assert hash_file(SRC / relative) == expected
    state_fd = os.open(SRC / 'workspace-state.json', os.O_RDONLY | NOATIME)
    with os.fdopen(state_fd, 'rb') as stream: state = json.load(stream)
    pins = {'swift-asn1': '917b472dbe53ba699cbb0495f9a95a084bc6364d',
            'swift-crypto': 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed',
            'torahinspectorkit': '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'}
    checked = {}
    for dep in state['object']['dependencies']:
        identity = dep['packageRef']['identity']
        if identity not in pins: continue
        checkout = SRC / 'checkouts' / dep['subpath']
        command = ['git', '-c', 'safe.directory=' + str(checkout), '-C', str(checkout)]
        env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
        actual = subprocess.check_output(command + ['rev-parse', 'HEAD'], env=env, text=True, timeout=20).strip()
        assert actual == pins[identity]
        assert not subprocess.check_output(command + ['status', '--porcelain', '--untracked-files=no'], env=env, text=True, timeout=30)
        checked[identity] = actual
    assert checked == pins
    # The read-only Git commands use ordinary reads and can update atime.
    # Restore only those access times before the exact portable-metadata
    # readback; optional Git index writes were disabled above.
    for row in before['entries']:
        target = DST / row['path']
        info = target.lstat()
        assert info.st_mtime_ns == row['mtime_ns']
        if info.st_atime_ns != row['atime_ns']:
            os.utime(target, ns=(row['atime_ns'], row['mtime_ns']), follow_symlinks=False)
    result['readbackAccessTimesRestored'] = True
    stable, _ = manifest(SRC.resolve(), symlink_witness); assert stable == before
    write(OUT / 'stable-path-after.json', stable)
    result['stablePathManifestSHA256'] = hash_file(OUT / 'stable-path-after.json')
    result['dependencyPinsAtStablePath'] = checked
    result['productsAndDependencyClosureUnchanged'] = True
    result['usersBeforeRetirement'] = users(); assert not result['usersBeforeRetirement']
    retained, _ = manifest(RETIRED); assert retained == before
    write(OUT / 'verified-retired-manifest.json', retained)
    result['destinationCopyManifestSHA256'] = hash_file(OUT / 'destination-copy.json')
    assert result['destinationCopyManifestSHA256'] == result['sourceManifestSHA256'] == result['stablePathManifestSHA256']
    result['restoration'] = {'stablePath': str(SRC), 'durableCopy': str(DST), 'sourceManifestSHA256': result['sourceManifestSHA256'],
                             'metadataPreserved': True, 'hardlinksAndSymlinksPreserved': True,
                             'privateSourceDuplicate': str(RETIRED), 'verifiedBeforeRemoval': True}
    phase = 'retiring only verified duplicate'; save()
    assert RETIRED.is_dir() and not RETIRED.is_symlink() and SRC.is_symlink() and SRC.resolve() == DST
    shutil.rmtree(RETIRED)
    durable_directory(SRC.parent)
    result['originalDuplicateRemoved'] = True
    assert not RETIRED.exists() and not RETIRED.is_symlink()
    final, _ = manifest(DST, symlink_witness); assert final == before
    result['rootAfter'] = shutil.disk_usage('/').free
    result['destinationAfter'] = shutil.disk_usage(DST).free
    result['allExactPortableMetadataAndBytesRetained'] = True
    result['status'] = 'PASS_EXACT_OWNED_SWIFT_CACHE_RELOCATED_STABLE_PATH_RETAINED'
    phase = 'completed'
except BaseException as error:
    result['status'] = 'FAIL_CUSTODY_ORIGINAL_DATA_NOT_AUTHORIZED_FOR_RETIREMENT'
    result['errors'].append({'type': type(error).__name__, 'message': str(error), 'phase': phase})
    (OUT / 'traceback.txt').write_text(traceback.format_exc())
    # If the transition stopped between source rename and link installation,
    # restore the original path immediately. All destination bytes are kept.
    if not SRC.exists() and not SRC.is_symlink() and RETIRED.is_dir():
        os.rename(RETIRED, SRC); durable_directory(SRC.parent)
        result['restoredOriginalPathAfterIncompleteSwitch'] = True
finally:
    result['controllerSHA256'] = hash_file(Path(__file__))
    result['rootFinalFree'] = shutil.disk_usage('/').free
    result['destinationFinalFree'] = shutil.disk_usage(DST.parent).free
    save()
    print(json.dumps({'status': result['status'], 'result': str(OUT / 'result.json'),
                      'resultSHA256': hash_file(OUT / 'result.json'), 'phase': phase,
                      'seconds': result['seconds'], 'errors': result['errors'],
                      'rootFree': result['rootFinalFree'], 'destinationFree': result['destinationFinalFree']}))
raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
