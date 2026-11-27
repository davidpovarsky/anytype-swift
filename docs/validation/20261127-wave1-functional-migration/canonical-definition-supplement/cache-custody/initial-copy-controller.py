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
OUT = Path('/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation2')
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

def manifest(root):
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
            row['target'] = os.readlink(path)
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
    assert all(not p.exists() and not p.is_symlink() for p in [DST, STAGE, RETIRED, LINK])
    assert SRC.parent.resolve() == SRC.parent and DST.parent.resolve() == DST.parent
    assert hash_file(BUILD) == BUILD_SHA
    build = json.loads(BUILD.read_bytes())
    assert build['status'] == 'PASS' and build['compiled'] and build['ownedGroupAbsent']
    result['qualifiedProducts'] = build['compiledProducts']
    result['usersBefore'] = users(); assert not result['usersBefore'], 'cache in active use'
    before, before_identity = manifest(SRC)
    write(OUT / 'source-before.json', before)
    write(OUT / 'source-identities-before.json', before_identity)
    result['sourceManifestSHA256'] = hash_file(OUT / 'source-before.json')
    result['sourceIdentitySHA256'] = hash_file(OUT / 'source-identities-before.json')
    result['entryCount'] = len(before['entries'])
    result['kinds'] = dict(collections.Counter(row['kind'] for row in before['entries']))
    result['hardlinkGroups'] = len(before['hardlinkTopology'])
    block = os.statvfs(DST.parent).f_frsize
    upper = sum((((row['bytes'] + block - 1) // block) * block) if row['kind'] == 'file' else block
                for row in before['entries'])
    result['measuredCopyUpperBytes'] = upper
    result['freshDestinationAdmissionFree'] = shutil.disk_usage(DST.parent).free
    assert result['freshDestinationAdmissionFree'] >= 512 * MIB + upper + 64 * MIB, 'measured copy plus512MiB+64MiB admission'
    for relative, expected in build['compiledProducts'].items(): assert hash_file(SRC / relative) == expected
    result['usersAtCopy'] = users(); assert not result['usersAtCopy']
    phase = 'fsynced exact destination copy'; save()
    STAGE.mkdir(mode=0o700)
    first_hardlink = {path: paths[0] for paths in before['hardlinkTopology'] for path in paths[1:]}
    directories = []
    for row in before['entries']:
        source, target = SRC / row['path'], STAGE / row['path']
        guard()
        if row['kind'] == 'directory':
            if row['path'] != '.': target.mkdir(mode=0o700)
            directories.append((target, row)); continue
        if row['kind'] == 'symlink': os.symlink(row['target'], target)
        elif row['path'] in first_hardlink: os.link(STAGE / first_hardlink[row['path']], target)
        else:
            source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | NOATIME)
            target_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            digest = hashlib.sha256(); written = 0
            try:
                while True:
                    data = os.read(source_fd, MIB)
                    if not data: break
                    digest.update(data); written += len(data)
                    view = memoryview(data)
                    while view:
                        amount = os.write(target_fd, view); assert amount > 0
                        view = view[amount:]
                    guard()
                os.fsync(target_fd)
            finally:
                os.close(source_fd); os.close(target_fd)
            assert written == row['bytes'] and digest.hexdigest() == row['sha256']
            result['copiedFiles'] += 1
        restore_metadata(target, row)
        if row['kind'] == 'file':
            fd = os.open(target, os.O_RDONLY | NOATIME)
            try: os.fsync(fd)
            finally: os.close(fd)
    for target, row in sorted(directories, key=lambda pair: len(pair[0].parts), reverse=True):
        restore_metadata(target, row); durable_directory(target)
    durable_directory(STAGE.parent)
    phase = 'independent durable destination readback'; save()
    copied, _ = manifest(STAGE)
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
    stable, _ = manifest(SRC.resolve())
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
    stable, _ = manifest(SRC.resolve()); assert stable == before
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
    final, _ = manifest(DST); assert final == before
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
