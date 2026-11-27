#!/usr/bin/env python3
"""Exact seven-file evidence preservation; no removal, unpacking, or new archive."""
from __future__ import annotations
import argparse
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

R = Path('/Users/m1/development/anytype-root-active-20261125')
D = Path('/Users/m1/development/anytype-d-active-20261125')
INPUT = R / 'shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs'
AUDIT = INPUT / 'seven-historical-archives-preservation2'
SCOPE = [
    (R / 't2-fixed-original-retention-20261126/t2-fixed-originals-private.tar.gz', 213543961),
    (D / 'bin-leaf-pass-original-outcome/originals.tar.gz', 163534849),
    (R / 'miniapps-runtime-retention-20261125T2348/original-runtime-recovery.tar.gz', 154238951),
    (D / 'retained-bin-and-c-ui-2330/bin-confirmation-aa261-failure.tar.gz', 78702741),
    (D / 'bin410b-original-outcome/originals.tar.gz', 67753205),
    (R / 't2-native-originals-retained-20261126/original-t2-mixed-build-and-executions.tar.gz', 54616872),
    (D / 'sdk9565-notification/original-retention/originals.tar.gz', 40522330),
]

def require(ok, why):
    if not ok:
        raise ValueError(why)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    os.chmod(path, 0o600)
    return {'path': str(path), 'sha256': digest(path), 'bytes': Path(path).stat().st_size}

def command(argv, timeout=45):
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return {'argv': argv, 'exitCode': proc.returncode,
            'stdout': proc.stdout.decode('utf-8', 'replace'), 'stderr': proc.stderr.decode('utf-8', 'replace')}

def extended_attributes(path):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    libc.listxattr.restype = ctypes.c_ssize_t
    libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    libc.getxattr.restype = ctypes.c_ssize_t
    encoded = os.fsencode(path)
    size = libc.listxattr(encoded, None, 0, 1)
    if size < 0:
        raise OSError(ctypes.get_errno(), 'listxattr failed', str(path))
    if not size:
        return {}
    names = ctypes.create_string_buffer(size)
    require(libc.listxattr(encoded, names, size, 1) == size, 'Original attribute names changed')
    result = {}
    for name in sorted(names.raw.split(b'\0')):
        if not name:
            continue
        count = libc.getxattr(encoded, name, None, 0, 0, 1)
        if count < 0:
            raise OSError(ctypes.get_errno(), 'getxattr size failed', str(path))
        value = ctypes.create_string_buffer(count)
        require(libc.getxattr(encoded, name, value, count, 0, 1) == count, 'Original attribute payload changed')
        result[os.fsdecode(name)] = base64.b64encode(value.raw[:count]).decode('ascii')
    return result

def metadata(path):
    require(path.resolve(strict=True) == path and not path.is_symlink(), 'Canonical nonsymlink file required')
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Only regular singly-linked original archives admitted')
    acl = command(['/bin/ls', '-lde', str(path)])
    require(acl['exitCode'] == 0 and acl['stderr'] == '', 'Original ACL observation failed')
    acl_entries = acl['stdout'].splitlines()[1:]
    require(not acl_entries, 'An archive with additional ACL requires separate restoration qualification')
    return {'path': str(path), 'kind': 'regular-file', 'symlink': False, 'linkCount': info.st_nlink,
            'device': info.st_dev, 'inode': info.st_ino, 'mode': stat.S_IMODE(info.st_mode),
            'uid': info.st_uid, 'gid': info.st_gid, 'bytes': info.st_size,
            'mtimeNS': info.st_mtime_ns, 'ctimeNS': info.st_ctime_ns,
            'birthtime': getattr(info, 'st_birthtime', None), 'flags': info.st_flags,
            'allocatedBytes': info.st_blocks * 512, 'extendedAttributesBase64': extended_attributes(path),
            'additionalACLEntries': acl_entries}

def full_row(path, size):
    before = metadata(path)
    require(before['bytes'] == size, 'Original archive size changed')
    sha = digest(path)
    require(before == metadata(path), 'Original archive metadata changed while hashing')
    return {**before, 'sha256': sha}

def owners():
    ps = command(['ps', '-axo', 'pid=,ppid=,etime=,command='])
    require(ps['exitCode'] == 0, 'Process census failed')
    matches = []
    for line in ps['stdout'].splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) >= 4 and int(fields[0]) != os.getpid() and any(str(p) in line for p, _ in SCOPE):
            matches.append(line)
    handles = command(['lsof', '-nP', '--', *[str(p) for p, _ in SCOPE]])
    require(not matches and handles['exitCode'] == 1 and not handles['stdout'] and not handles['stderr'],
            'Archive has a process reference or open handle')
    return {'observedAt': time.time(), 'scopedProcesses': matches, 'openHandles': handles}

def references():
    roots = [D / 'main14/source/Tools', R / 't5-current-controls-b68ee97c-20261127']
    require(all(p.is_dir() for p in roots), 'Known current controller roots missing')
    patterns = []
    for path, _ in SCOPE:
        patterns += [str(path), str(path.parent.relative_to(R if path.is_relative_to(R) else D))]
    matches, files, total = [], 0, 0
    for root in roots:
        for path in sorted(root.rglob('*')):
            if path.is_symlink() or not path.is_file() or path.suffix not in {'.py', '.json', '.sh'}:
                continue
            size = path.stat().st_size
            require(size <= 8 * 1024 * 1024, 'Individual current control input exceeds scan bound')
            total += size
            files += 1
            require(files <= 12000 and total <= 96 * 1024 * 1024, 'Current controller scan exceeds bound')
            for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
                hits = [pattern for pattern in patterns if pattern in line]
                if hits:
                    matches.append({'path': str(path), 'lineNumber': number, 'patterns': hits,
                                    'lineSHA256': hashlib.sha256(line.encode()).hexdigest()})
    return {'roots': list(map(str, roots)), 'patterns': patterns, 'filesRead': files,
            'bytesRead': total, 'matches': matches,
            'fallbackReason': 'Original rg invocation unavailable; exact bounded Python text scan.'}


def observe():
    AUDIT.mkdir(mode=0o700, exist_ok=False)
    result = {'schema': 'pinkha-seven-existing-evidence-archives-observation-v1', 'status': 'FAIL',
              'startedAt': time.time(), 'controllerSHA256': digest(__file__), 'removedFiles': 0,
              'newMacArchiveBytes': 0, 'unpackedFiles': 0}
    try:
        result['ownersBefore'] = owners()
        rows = [full_row(path, size) for path, size in SCOPE]
        result['manifest'] = write(AUDIT / 'manifest-before.json', {'schema': 'pinkha-seven-archive-original-file-manifest-v1', 'files': rows})
        result['bytes'] = sum(row['bytes'] for row in rows)
        result['allocatedBytesNotUniqueReclamation'] = sum(row['allocatedBytes'] for row in rows)
        result['currentControllerReferences'] = references()
        result['parentChildren'] = {str(path.parent): sorted(p.name for p in path.parent.iterdir()) for path, _ in SCOPE}
        result['ownersAfter'] = owners()
        result['freeBytes'] = shutil.disk_usage('/System/Volumes/Data').free
        result['status'] = 'PASS_ORIGINAL_ARCHIVE_OBSERVATION_NOT_RETIRED'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    ref = write(AUDIT / 'observation.json', result)
    print(json.dumps({'result': result, 'receipt': ref}))
    return 0 if result['status'].startswith('PASS_') else 1

def stream(index, expected_manifest_sha):
    manifest = AUDIT / 'manifest-before.json'
    require(digest(manifest) == expected_manifest_sha, 'Exact original manifest hash required')
    document = json.loads(manifest.read_text())
    require(0 <= index < len(SCOPE), 'Archive index outside approved scope')
    path, size = SCOPE[index]
    expected = document['files'][index]
    result_path = AUDIT / ('stream-' + str(index + 1) + '.json')
    require(not result_path.exists(), 'Original archive stream receipt already exists')
    result = {'schema': 'pinkha-seven-existing-archive-stream-v1', 'status': 'FAIL', 'index': index,
              'startedAt': time.time(), 'path': str(path), 'manifestSHA256': expected_manifest_sha,
              'controllerSHA256': digest(__file__), 'sourceRemoved': False}
    try:
        result['ownersBefore'] = owners()
        require(full_row(path, size) == expected, 'Original archive changed before transfer')
        hasher = hashlib.sha256()
        count = 0
        with path.open('rb') as source:
            while block := source.read(1024 * 1024):
                require(sys.stdout.buffer.write(block) == len(block), 'Incomplete binary stream write')
                hasher.update(block)
                count += len(block)
        sys.stdout.buffer.flush()
        require(count == size and hasher.hexdigest() == expected['sha256'], 'Stream bytes differ from original')
        after = full_row(path, size)
        require(after == expected, 'Original bytes or metadata changed during transfer')
        result['sourceAfter'] = after
        result['stream'] = {'bytes': count, 'sha256': hasher.hexdigest()}
        result['ownersAfter'] = owners()
        result['status'] = 'PASS_EXACT_STREAM_ORIGINAL_BYTES_AND_METADATA_UNCHANGED'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    ref = write(result_path, result)
    print(json.dumps({'status': result['status'], 'receipt': ref}), file=sys.stderr)
    return 0 if result['status'].startswith('PASS_') else 1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--observe', action='store_true')
    parser.add_argument('--stream-index', type=int)
    parser.add_argument('--manifest-sha256')
    args = parser.parse_args()
    if args.observe:
        require(args.stream_index is None, 'One mode only')
        return observe()
    require(args.stream_index is not None and args.manifest_sha256, 'Stream identity required')
    return stream(args.stream_index, args.manifest_sha256)

if __name__ == '__main__':
    raise SystemExit(main())
