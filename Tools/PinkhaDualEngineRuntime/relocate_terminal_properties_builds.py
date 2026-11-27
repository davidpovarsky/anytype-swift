#!/usr/bin/env python3
"""Two fixed terminal build trees; storage custody only, never a build/test.

No historical process ID/group is probed or signalled. A current path/inode
reader census is separate from the retained terminal absence receipts.
An exclusive destination prevents automatic replay after any interruption.
"""
from pathlib import Path
import argparse
import base64
import ctypes
import fcntl
import grp
import hashlib
import json
import os
import pwd
import shutil
import signal
import stat
import sys
import time
import traceback

MIB = 1024 ** 2
OUT = Path('/mnt/development/projects/evidence/wave2-properties-related-build-custody-20261127')
LOCK = OUT.parent / '.pinkha-wave2-component-cache-custody.lock'
BUILD_LINK = 'out/Products/Debug-linux-aarch64'
SCOPES = {
    'original-failed-build': {
        'root': '/var/lib/pinkha-wave2-properties-related-lifetime-20261127',
        'files': 578, 'directories': 409, 'logicalBytes': 32046990, 'allocatedBytes': 35352576,
        'receiptSHA256': '8fbaf3c6dd6b57bc577d7f91ba54403f2ee57ee350d37a0280da74d17c405ceb',
        'status': 'FAIL', 'exit': 1,
    },
    'source2-passed-build': {
        'root': '/var/lib/pinkha-wave2-properties-related-lifetime-source2-20261127',
        'files': 631, 'directories': 417, 'logicalBytes': 54576050, 'allocatedBytes': 58060800,
        'receiptSHA256': '05971770c170562bc9ab8d01efff29ad459c440f6901f19ca84c116f07d543b4',
        'status': 'PASS_FIVE_METHODS_ELEVEN_DECLARED_CASES_EXACT_SOURCE_MODEL_COMPONENT_ONLY', 'exit': 0,
    },
}
ROOT_FLOOR = 2 * 1024 ** 3
DESTINATION_FLOOR = 512 * MIB
EVIDENCE_ALLOWANCE = 16 * MIB
ROOT_METADATA_ALLOWANCE = MIB
MAX_COPY_BYTES = 128 * MIB
MAX_ENTRIES = 2500
IDENTITY_FIELDS = {'dev', 'ino', 'ctime_ns', 'allocated', 'nlink'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(path):
    s = os.lstat(path)
    kind = ('dir' if stat.S_ISDIR(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode)
            else 'link' if stat.S_ISLNK(s.st_mode) else 'other')
    require(kind != 'other', 'Special filesystem entry is outside this custody')
    attrs = {k: base64.b64encode(os.getxattr(path, k, follow_symlinks=False)).decode()
             for k in sorted(os.listxattr(path, follow_symlinks=False))}
    require(sum(map(len, attrs.values())) <= MIB, 'Bounded extended attributes')
    row = dict(kind=kind, mode=stat.S_IMODE(s.st_mode), uid=s.st_uid, gid=s.st_gid,
               dev=s.st_dev, ino=s.st_ino, nlink=s.st_nlink, allocated=s.st_blocks * 512,
               atime_ns=s.st_atime_ns, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, xattrs=attrs)
    if kind != 'dir':
        row['bytes'] = s.st_size
    return row


def names(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME)
    try:
        with os.scandir(fd) as entries:
            return sorted(e.name for e in entries)
    finally:
        os.close(fd)


def bytes_at(path, guard, limit=None):
    before = metadata(path)
    require(before['kind'] == 'file', 'Exact regular file required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
    h = hashlib.sha256(); data = bytearray(); size = 0
    try:
        opened = os.fstat(fd)
        require((opened.st_dev, opened.st_ino) == (before['dev'], before['ino']), 'Opened file identity drift')
        while part := os.read(fd, MIB):
            guard(); h.update(part); size += len(part)
            if limit is not None:
                require(size <= limit, 'Bounded exact input read'); data.extend(part)
    finally:
        os.close(fd)
    require(metadata(path) == before and size == before['bytes'], 'File changed during capture')
    return (bytes(data) if limit is not None else h.hexdigest()), before


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def owner_traversal(path, uid, groups):
    for parent in reversed((path,) + tuple(path.parents)):
        row = metadata(parent)
        require(row['kind'] == 'dir' and 'system.posix_acl_access' not in row['xattrs'],
                'Destination traversal requires the observed ordinary POSIX directories')
        bit = 0o100 if row['uid'] == uid else 0o010 if row['gid'] in groups else 0o001
        require(row['mode'] & bit, 'Original component owner cannot traverse destination parent')


def immutable_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    require(len(raw) <= 8 * MIB, 'Bounded receipt')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view); require(count > 0, 'Short receipt write'); view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    sync_dir(path.parent)
    return digest(raw)


def portable(row):
    return {k: v for k, v in row.items() if k not in IDENTITY_FIELDS}


def tree(root, guard, copied=False):
    require(root.resolve(strict=True) == root and not root.is_symlink(), 'Physical fixed tree required')
    rows = {}; pending = [root]; device = os.lstat(root).st_dev
    while pending:
        guard(); path = pending.pop(); rel = str(path.relative_to(root)); before = metadata(path)
        require(before['dev'] == device, 'Nested mount is outside custody')
        if before['kind'] == 'file':
            h, observed = bytes_at(path, guard)
            require(observed == before, 'File identity drift'); row = dict(before, sha256=h)
        elif before['kind'] == 'link':
            require(rel == 'debug' and before['nlink'] == 1 and before['mode'] == 0o777,
                    'Only the original non-hardlinked build/debug symlink is admitted')
            target = os.readlink(path)
            require(target == BUILD_LINK and before['bytes'] == len(os.fsencode(target)), 'Unexpected link target')
            after = metadata(path)
            if copied and after['atime_ns'] != before['atime_ns']:
                require({k: v for k, v in after.items() if k != 'atime_ns'} ==
                        {k: v for k, v in before.items() if k != 'atime_ns'}, 'Copied link changed beyond access time')
                os.utime(path, ns=(before['atime_ns'], before['mtime_ns']), follow_symlinks=False)
                restored = metadata(path)
                require({k: v for k, v in restored.items() if k != 'ctime_ns'} ==
                        {k: v for k, v in before.items() if k != 'ctime_ns'}, 'Copied link time restore failed')
                before = restored
            else:
                require(after == before, 'Original link metadata drift during read')
            row = dict(before, target=target)
        else:
            children = names(path); row = dict(before, children=children)
            pending.extend(path / child for child in reversed(children))
        require(metadata(path) == before, 'Entry changed during tree capture')
        rows[rel] = row
        require(len(rows) <= MAX_ENTRIES, 'Fixed-tree entry bound')
    require(rows.get('debug', {}).get('kind') == 'link' and rows.get(BUILD_LINK, {}).get('kind') == 'dir',
            'Internal build link target must be present in the same tree')
    return rows


def hardlink_classes(manifests):
    groups = {}
    for scope, rows in manifests.items():
        for rel, row in rows.items():
            if row['kind'] == 'file':
                groups.setdefault((row['dev'], row['ino']), []).append((scope, rel, row))
    for entries in groups.values():
        require(all(row['nlink'] == len(entries) for _, _, row in entries),
                'A regular-file hardlink escapes these two owned trees')
        require(all(portable(row) == portable(entries[0][2]) for _, _, row in entries), 'Hardlink metadata mismatch')
    return sorted(sorted(scope + '/' + rel for scope, rel, _ in group) for group in groups.values())


def equal_copies(expected, actual):
    require(set(expected) == set(actual), 'Copied scope set changed')
    require({s: {p: portable(r) for p, r in rows.items()} for s, rows in expected.items()} ==
            {s: {p: portable(r) for p, r in rows.items()} for s, rows in actual.items()}, 'Copy bytes/metadata/topology mismatch')
    require(hardlink_classes(expected) == hardlink_classes(actual), 'Hardlink equivalence classes changed')


def restore_metadata(path, row):
    os.chown(path, row['uid'], row['gid'], follow_symlinks=False)
    if row['kind'] != 'link':
        os.chmod(path, row['mode'], follow_symlinks=False)
    else:
        require(stat.S_IMODE(os.lstat(path).st_mode) == row['mode'] == 0o777, 'Symlink mode')
    for key in set(os.listxattr(path, follow_symlinks=False)) - set(row['xattrs']):
        os.removexattr(path, key, follow_symlinks=False)
    for key, value in row['xattrs'].items():
        os.setxattr(path, key, base64.b64decode(value, validate=True), follow_symlinks=False)
    os.utime(path, ns=(row['atime_ns'], row['mtime_ns']), follow_symlinks=False)


def no_current_users(paths, manifests, guard):
    """Fresh path/inode census, not a probe of any retained PID or group."""
    prefixes = [str(p) for p in paths]
    identities = {(r['dev'], r['ino']) for rows in manifests.values() for r in rows.values()}
    hits = []
    for proc in Path('/proc').iterdir():
        guard()
        if not proc.name.isdecimal() or int(proc.name) == os.getpid():
            continue
        try:
            with (proc / 'cmdline').open('rb') as stream:
                command = stream.read(128 * 1024 + 1)
            require(len(command) <= 128 * 1024, 'Bounded live command identity')
            if any(os.fsencode(p) in command for p in prefixes):
                hits.append({'pid': int(proc.name), 'reference': 'fixed-path-command'})
            for ref in [proc / 'cwd', proc / 'exe'] + list((proc / 'fd').iterdir()):
                try:
                    s = ref.stat(); target = os.readlink(ref).removesuffix(' (deleted)')
                    if (s.st_dev, s.st_ino) in identities or any(target == p or target.startswith(p + '/') for p in prefixes):
                        hits.append({'pid': int(proc.name), 'reference': ref.name})
                except (FileNotFoundError, ProcessLookupError):
                    pass
            with (proc / 'maps').open('r') as stream:
                mappings = stream.read(4 * MIB + 1)
            require(len(mappings) <= 4 * MIB, 'Bounded live mapping census')
            for line in mappings.splitlines():
                fields = line.split(None, 5)
                if len(fields) < 5:
                    continue
                major, minor = fields[3].split(':')
                key = (os.makedev(int(major, 16), int(minor, 16)), int(fields[4]))
                path = fields[5].removesuffix(' (deleted)') if len(fields) == 6 else ''
                if key in identities or any(path == p or path.startswith(p + '/') for p in prefixes):
                    hits.append({'pid': int(proc.name), 'reference': 'fixed-path-mapping'})
        except (FileNotFoundError, ProcessLookupError):
            pass
    require(not hits, 'Current source/copy user observed; no exchange or retirement: ' + repr(hits))


def protected_inputs(guard):
    pinned = {}
    for spec in SCOPES.values():
        root = Path(spec['root']); receipt_path = root / 'attempt1/receipt.json'
        raw, meta = bytes_at(receipt_path, guard, MIB)
        require(digest(raw) == spec['receiptSHA256'], 'Original terminal receipt changed')
        receipt = json.loads(raw)
        require(receipt['status'] == spec['status'] and receipt['processExit'] == spec['exit'], 'Terminal result identity')
        closure = receipt['ownedCleanup']; absence = closure['absenceEvidence']
        require(closure['status'] == 'PASS_OWNED_GROUP_ABSENT' and absence['status'] == 'ABSENT_ESRCH'
                and absence['signal'] == 0 and absence['errno'] == 3
                and closure['historicalGroupReprobed'] is False, 'Original terminal absence latch required')
        # These numbers are evidence only. No process operation uses them.
        require(receipt['argv'][receipt['argv'].index('--scratch-path') + 1] == str(root / 'build'), 'Exact original build path')
        pinned[str(receipt_path)] = dict(meta, sha256=digest(raw))
        require(len(receipt['artifacts']) == 8, 'Exact original artifact set')
        for item in receipt['artifacts']:
            path = Path(item['path'])
            require(path.parent == root / 'attempt1' and path.resolve(strict=True) == path, 'Original evidence scope')
            h, entry = bytes_at(path, guard)
            require(h == item['sha256'] and entry['bytes'] == item['bytes'], 'Original evidence changed')
            pinned[str(path)] = dict(entry, sha256=h)
        source_raw, _ = bytes_at(root / 'attempt1/source-inputs-before.json', guard, MIB)
        source_after, _ = bytes_at(root / 'attempt1/source-inputs-after.json', guard, MIB)
        require(source_raw == source_after, 'Original component source equality')
        sources = json.loads(source_raw); require(len(sources) == 4, 'Exact four original component source inputs')
        for rel, pin in sources.items():
            require(not Path(rel).is_absolute() and '..' not in Path(rel).parts, 'Relative source path')
            for area in ('component', 'inputs'):
                path = root / area / rel
                require(path.resolve(strict=True) == path, 'Physical source input required')
                h, entry = bytes_at(path, guard)
                require(h == pin['sha256'] and entry['bytes'] == pin['bytes'], 'Original source changed')
                pinned[str(path)] = dict(entry, sha256=h)
        for name, want in [('run_component.py', receipt['runnerSHA256']),
                           ('owned_process.py', receipt['cleanupSourceProvenance']['outputSHA256'])]:
            path = root / 'inputs' / name; h, entry = bytes_at(path, guard)
            require(h == want, 'Original controller changed'); pinned[str(path)] = dict(entry, sha256=h)
    return pinned


def exchange(a, b):
    op = ctypes.CDLL(None, use_errno=True).renameat2
    op.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    op.restype = ctypes.c_int
    if op(-100, os.fsencode(a), -100, os.fsencode(b), 2):
        number = ctypes.get_errno(); raise OSError(number, os.strerror(number))


def copy_trees(manifests, guard):
    linked = {}; directories = []
    for scope, rows in manifests.items():
        src_root = Path(SCOPES[scope]['root']) / 'build'; dst_root = OUT / 'retained' / scope
        dst_root.mkdir(mode=0o700)
        for rel, row in sorted(rows.items()):
            guard(); src = src_root / rel; dst = dst_root / rel
            if row['kind'] == 'dir':
                if rel != '.':
                    dst.mkdir(mode=0o700)
                directories.append((dst, row)); continue
            if row['kind'] == 'link':
                os.symlink(row['target'], dst); restore_metadata(dst, row); continue
            key = (row['dev'], row['ino'])
            if key in linked:
                os.link(linked[key], dst, follow_symlinks=False); continue
            require(metadata(src) == {k: v for k, v in row.items() if k != 'sha256'}, 'Source drift before copy')
            incoming = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
            outgoing = None
            h = hashlib.sha256(); size = 0
            try:
                outgoing = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                opened = os.fstat(incoming)
                require((opened.st_dev, opened.st_ino) == key, 'Copy source descriptor identity')
                while part := os.read(incoming, MIB):
                    guard(); h.update(part); size += len(part); view = memoryview(part)
                    while view:
                        count = os.write(outgoing, view); require(count > 0, 'Short copy write'); view = view[count:]
                os.fsync(outgoing)
            finally:
                os.close(incoming)
                if outgoing is not None:
                    os.close(outgoing)
            require(size == row['bytes'] and h.hexdigest() == row['sha256'], 'Copy byte mismatch')
            restore_metadata(dst, row)
            fd = os.open(dst, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            linked[key] = dst
    for path, row in sorted(directories, key=lambda x: len(x[0].parts), reverse=True):
        restore_metadata(path, row); sync_dir(path)
    sync_dir(OUT / 'retained')


def run(story):
    began = time.monotonic(); created = False; protected = None; original = {}; switched = {}; first = None
    result = dict(protocol='two-terminal-properties-build-custody-v1', status='RUNNING', phase='admission',
                  coordinationStory=story, compilerInvocations=0, testsInvoked=0, nativeCalls=0,
                  historicalProcessProbes=0, processSignals=0, retired=[], events=[], errors=[])
    def guard():
        require(time.monotonic() - began < 300, 'Bounded storage-only operation deadline')
        root_free = shutil.disk_usage('/').free; dest_free = shutil.disk_usage(OUT.parent).free
        result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes', root_free), root_free)
        result['minimumDestinationFreeBytes'] = min(result.get('minimumDestinationFreeBytes', dest_free), dest_free)
        require(root_free >= ROOT_FLOOR and dest_free >= DESTINATION_FLOOR, 'Existing live storage floor')
    def event(phase, details):
        result['phase'] = phase
        pin = immutable_json(OUT / ('phase-%02d.json' % len(result['events'])), dict(phase=phase, **details))
        result['events'].append(dict(phase=phase, sha256=pin))
    def interrupt(*_):
        raise RuntimeError('Owned storage operation interrupted; preserve all remaining copies')
    signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
    try:
        guard(); user = pwd.getpwnam('ubuntu'); group = grp.getgrnam('chatgpt-agent')
        require(shutil.disk_usage('/').free >= ROOT_FLOOR + ROOT_METADATA_ALLOWANCE, 'Root metadata allowance')
        require(OUT.parent.resolve(strict=True) == OUT.parent and not os.path.lexists(OUT), 'Exclusive physical destination')
        owner_traversal(OUT.parent, user.pw_uid, os.getgrouplist(user.pw_name, user.pw_gid))
        protected = protected_inputs(guard)
        parents = {}
        for scope, spec in SCOPES.items():
            root = Path(spec['root']); require(root.resolve(strict=True) == root, 'Physical original component parent')
            parent = metadata(root)
            require((parent['kind'], parent['uid'], parent['gid'], parent['mode'], parent['xattrs']) ==
                    ('dir', user.pw_uid, group.gr_gid, 0o700, {}), 'Original owner-only component parent drift')
            parents[scope] = parent; rows = tree(root / 'build', guard); original[scope] = rows
            require(sum(r['kind'] == 'file' for r in rows.values()) == spec['files'] and
                    sum(r['kind'] == 'dir' for r in rows.values()) == spec['directories'] and
                    sum(r['kind'] == 'link' for r in rows.values()) == 1, 'Exact original inventory counts')
            require(sum(r.get('bytes', 0) for r in rows.values() if r['kind'] == 'file') == spec['logicalBytes'], 'Original logical bytes')
            unique = {(r['dev'], r['ino']): r['allocated'] for r in rows.values()}
            require(sum(unique.values()) == spec['allocatedBytes'], 'Original allocation drift')
        topology = hardlink_classes(original)
        block = os.statvfs(OUT.parent).f_frsize
        upper = sum(((r['bytes'] + block - 1) // block) * block if r['kind'] == 'file' else block
                    for rows in original.values() for r in rows.values())
        require(upper <= MAX_COPY_BYTES, 'Fixed copy allocation ceiling')
        require(shutil.disk_usage(OUT.parent).free >= DESTINATION_FLOOR + upper + EVIDENCE_ALLOWANCE, 'Destination copy plus evidence margin')
        require(all(os.lstat(OUT.parent).st_dev != rows['.']['dev'] for rows in original.values()), 'Destination must relieve another filesystem')
        no_current_users([Path(s['root']) / 'build' for s in SCOPES.values()], original, guard)
        os.umask(0o077); OUT.mkdir(mode=0o700); created = True
        os.chown(OUT, user.pw_uid, group.gr_gid)
        require(metadata(OUT)['xattrs'] == {}, 'No inherited destination access policy')
        retained = OUT / 'retained'; retained.mkdir(mode=0o700); os.chown(retained, user.pw_uid, group.gr_gid)
        sync_dir(OUT); sync_dir(OUT.parent)
        unique_source = {(r['dev'], r['ino']): r['allocated'] for rows in original.values() for r in rows.values()}
        result.update(controllerSHA256=bytes_at(Path(__file__).resolve(), guard)[0], measuredCopyUpperBytes=upper,
                      sourceInventoryAllocationSumBytes=sum(s['allocatedBytes'] for s in SCOPES.values()),
                      measuredSourceUniqueAllocationBytes=sum(unique_source.values()),
                      rootFreeBefore=shutil.disk_usage('/').free, destinationFreeBefore=shutil.disk_usage(OUT).free)
        event('originals-pinned', dict(originalManifestsSHA256=immutable_json(OUT / 'original-manifests.json', original),
                                     protectedInputsSHA256=immutable_json(OUT / 'protected-inputs.json', protected),
                                     hardlinkClasses=topology, parentMetadata=parents))
        copy_trees(original, guard)
        copied = {s: tree(retained / s, guard, copied=True) for s in SCOPES}
        equal_copies(original, copied)
        require({s: tree(Path(x['root']) / 'build', guard) for s, x in SCOPES.items()} == original, 'Originals changed during copy')
        require(protected_inputs(guard) == protected, 'Protected original input/evidence changed')
        event('copies-durable-and-verified', dict(copiedManifestsSHA256=immutable_json(OUT / 'copied-manifests.json', copied)))
        for scope, spec in SCOPES.items():
            root = Path(spec['root']); source = root / 'build'; destination = retained / scope
            duplicate = root / 'build.verified-wave2-custody-original-20261127'
            require(not os.path.lexists(duplicate), 'Unresolved original duplicate exists; no automatic replay')
            require(tree(source, guard) == original[scope], 'Original drift before atomic exchange')
            fresh = {s: tree(retained / s, guard, copied=True) for s in SCOPES}; equal_copies(original, fresh)
            no_current_users([source, destination], {scope: original[scope], 'copy': fresh[scope]}, guard)
            event('before-exchange-' + scope, dict(original=str(source), retained=str(destination), duplicate=str(duplicate)))
            os.symlink(str(destination), duplicate); os.lchown(duplicate, user.pw_uid, group.gr_gid); sync_dir(root)
            exchange(source, duplicate); sync_dir(root); switched[scope] = duplicate
            require(source.is_symlink() and os.readlink(source) == str(destination) and source.resolve(strict=True) == destination, 'Stable original alias failed')
            old = tree(duplicate, guard)
            require((old['.']['dev'], old['.']['ino']) == (original[scope]['.']['dev'], original[scope]['.']['ino']), 'Exchanged original identity')
            require({p: portable(r) for p, r in old.items()} == {p: portable(r) for p, r in original[scope].items()}, 'Exchanged original content')
            event('exchanged-' + scope, dict(stableAlias=str(source), verifiedOriginalDuplicate=str(duplicate)))
        # Both stable aliases and both exact durable copies exist before any deletion.
        duplicates = {s: tree(p, guard) for s, p in switched.items()}
        copied = {s: tree(retained / s, guard, copied=True) for s in SCOPES}; equal_copies(duplicates, copied)
        no_current_users(list(switched.values()) + [retained / s for s in SCOPES] +
                         [Path(x['root']) / 'build' for x in SCOPES.values()],
                         {**duplicates, **{'copy-' + s: rows for s, rows in copied.items()}}, guard)
        event('before-duplicate-retirement', dict(duplicateManifestsSHA256=immutable_json(OUT / 'duplicate-manifests.json', duplicates)))
        remaining_links = {}
        for rows in duplicates.values():
            for row in rows.values():
                if row['kind'] == 'file':
                    remaining_links[(row['dev'], row['ino'])] = row['nlink']
        for scope, duplicate in switched.items():
            source = Path(SCOPES[scope]['root']) / 'build'
            require(source.is_symlink() and os.readlink(source) == str(retained / scope), 'Original alias changed before retirement')
            equal_copies(original, {s: tree(retained / s, guard, copied=True) for s in SCOPES})
            no_current_users([source, duplicate, retained / scope],
                             {scope: duplicates[scope], 'copy': copied[scope]}, guard)
            for rel, row in sorted(duplicates[scope].items(), key=lambda x: len(Path(x[0]).parts), reverse=True):
                guard(); path = duplicate / rel; current = metadata(path)
                require((current['dev'], current['ino']) == (row['dev'], row['ino']), 'Retiring duplicate identity changed')
                if row['kind'] == 'dir':
                    require(all(current[k] == row[k] for k in ('kind', 'mode', 'uid', 'gid', 'xattrs')),
                            'Retiring duplicate directory protection changed')
                    require(not names(path), 'Duplicate directory unexpectedly nonempty'); path.rmdir()
                else:
                    compare = {k: v for k, v in current.items() if k not in ('ctime_ns', 'nlink')}
                    expected = {k: v for k, v in row.items() if k not in ('ctime_ns', 'nlink', 'sha256', 'target')}
                    require(compare == expected, 'Duplicate metadata changed before unlink')
                    if row['kind'] == 'file':
                        key = (row['dev'], row['ino']); require(current['nlink'] == remaining_links[key], 'Duplicate hardlink count changed')
                        require(bytes_at(path, guard)[0] == row['sha256'], 'Duplicate bytes changed before unlink')
                    else:
                        require(os.readlink(path) == BUILD_LINK, 'Duplicate symlink target changed')
                    path.unlink()
                    if row['kind'] == 'file':
                        remaining_links[key] -= 1
            sync_dir(duplicate.parent); result['retired'].append(scope)
            event('retired-' + scope, dict(retiredOriginalDuplicate=str(duplicate)))
        equal_copies(original, {s: tree(retained / s, guard, copied=True) for s in SCOPES})
        require(protected_inputs(guard) == protected, 'Protected sources/receipts changed after custody')
        result['status'] = 'PASS_TWO_TERMINAL_BUILD_TREES_RELOCATED_NO_NEW_ACCEPTANCE'
        result['phase'] = 'complete'
    except BaseException as error:
        first = error; result['status'] = 'FAIL_CUSTODY_PRESERVE_ALL_REMAINING_COPIES'
        result['errors'].append(dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN); signal.signal(signal.SIGINT, signal.SIG_IGN)
        final_deadline = time.monotonic() + 60
        def final_guard():
            require(time.monotonic() < final_deadline, 'Bounded final integrity read')
        try:
            if protected is not None:
                require(protected_inputs(final_guard) == protected, 'Original sources/evidence changed at final read')
            if switched:
                observed = {s: tree(OUT / 'retained' / s, final_guard, copied=True) for s in SCOPES}
                equal_copies(original, observed)
                owner_traversal(OUT / 'retained', user.pw_uid, os.getgrouplist(user.pw_name, user.pw_gid))
                for s in switched:
                    source = Path(SCOPES[s]['root']) / 'build'; target = OUT / 'retained' / s
                    require(source.is_symlink() and os.readlink(source) == str(target)
                            and source.resolve(strict=True) == target, 'Final stable original path failed')
                    current_parent = metadata(source.parent)
                    require(all(current_parent[k] == parents[s][k] for k in ('kind', 'mode', 'uid', 'gid', 'xattrs')),
                            'Original component parent protection changed')
                result['allSwitchedPathsRetainVerifiedCopies'] = True
            if created and 'controllerSHA256' in result:
                require(bytes_at(Path(__file__).resolve(), final_guard)[0] == result['controllerSHA256'], 'Controller source changed')
        except BaseException as error:
            result['status'] = 'FAIL_CUSTODY_FINAL_INTEGRITY'
            result['errors'].append(dict(type=type(error).__name__, message=str(error), phase='final-integrity'))
            if first is None:
                first = error
        result['seconds'] = round(time.monotonic() - began, 3)
        try:
            result['rootFreeAfter'] = shutil.disk_usage('/').free
            result['destinationFreeAfter'] = shutil.disk_usage(OUT.parent).free
            result['finalPaths'] = {s: dict(original=str(Path(x['root']) / 'build'),
                originalIsSymlink=(Path(x['root']) / 'build').is_symlink(), retainedExists=os.path.lexists(OUT / 'retained' / s),
                duplicateExists=os.path.lexists(Path(x['root']) / 'build.verified-wave2-custody-original-20261127')) for s, x in SCOPES.items()}
        except BaseException as error:
            result['status'] = 'FAIL_CUSTODY_FINAL_STATE_READ'
            result['errors'].append(dict(type=type(error).__name__, message=str(error), phase='final-state'))
            if first is None:
                first = error
        if created:
            try:
                result['receiptSHA256'] = immutable_json(OUT / 'result.json', result)
            except BaseException as error:
                result['status'] = 'FAIL_CUSTODY_RECEIPT_WRITE'
                result['errors'].append(dict(type=type(error).__name__, message=str(error), phase='final-receipt'))
                if first is None:
                    first = error
        print(json.dumps(result, sort_keys=True))
    return 1 if first is not None else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coordination-story', required=True)
    args = parser.parse_args()
    require(args.coordination_story.isdecimal() and len(args.coordination_story) == 16, 'Actual coordinated storage slot required')
    require(os.geteuid() == 0 and os.uname().nodename == 'torah-social', 'Exact Oracle root execution only')
    require(OUT.parent.resolve(strict=True) == OUT.parent, 'Physical existing evidence parent')
    require(not os.path.lexists(OUT), 'This fixed destination is exclusive; interrupted runs are not replayed')
    lock = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        lock_meta = os.fstat(lock)
        require(stat.S_ISREG(lock_meta.st_mode) and lock_meta.st_nlink == 1
                and lock_meta.st_uid == 0 and stat.S_IMODE(lock_meta.st_mode) == 0o600, 'Exact custody lock file')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args.coordination_story)
    finally:
        os.close(lock)


if __name__ == '__main__':
    sys.exit(main())
