#!/usr/bin/env python3
"""Restore one admitted raw archive from stdin; never replace an existing path."""
from __future__ import annotations
import argparse
import base64
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HELPER = Path('/Users/m1/sentinelx/uploads/pinkha-wave3-preserve-seven-archives-reference-fixed-20261127.py')
HELPER_SHA = 'f953ab341db150651c93ae46f17703459e34455cdf4015d1b5817554e0cca405'
MANIFEST = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs/seven-historical-archives-preservation2/manifest-before.json')
MANIFEST_SHA = 'd6575b864418cd7b8fdde83776a0fdb4138c70ffb252f81f855fa96c7d7e8c86'

def require(ok, why):
    if not ok:
        raise ValueError(why)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=int, required=True)
    parser.add_argument('--controller-sha256', required=True)
    args = parser.parse_args()
    require(sha(__file__) == args.controller_sha256, 'Exact reviewed restoration controller required')
    require(sha(HELPER) == HELPER_SHA and sha(MANIFEST) == MANIFEST_SHA, 'Original metadata/helper changed')
    spec = importlib.util.spec_from_file_location('original_archive_helper', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    rows = json.loads(MANIFEST.read_text())['files']
    require(0 <= args.index < 7 and len(rows) == 7, 'Only original seven-file scope allowed')
    row = rows[args.index]
    path, expected_size = helper.SCOPE[args.index]
    require(str(path) == row['path'] and expected_size == row['bytes'], 'Original scope mismatch')
    require(path.parent.resolve(strict=True) == path.parent and not path.exists() and not path.is_symlink(),
            'Original parent must exist and exact archive path must be absent')
    require(os.getuid() == row['uid'] and row['gid'] in (set(os.getgroups()) | {os.getgid()}), 'Use original m1 owner and existing group')
    temporary = path.name + '.restore-in-progress'
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    result = {'schema': 'pinkha-exact-archive-restoration-v1', 'status': 'FAIL', 'index': args.index,
              'startedAt': time.time(), 'controllerSHA256': args.controller_sha256,
              'originalManifestSHA256': MANIFEST_SHA, 'path': str(path),
              'historicalIdentityNotRecreated': ['device', 'inode', 'ctimeNS', 'birthtime', 'allocatedBytes']}
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        with os.fdopen(fd, 'wb') as output:
            count, digest = 0, hashlib.sha256()
            while chunk := sys.stdin.buffer.read(1024 * 1024):
                count += len(chunk)
                require(count <= row['bytes'], 'Input exceeds exact original size')
                output.write(chunk)
                digest.update(chunk)
            require(count == row['bytes'] and digest.hexdigest() == row['sha256'], 'Restored raw archive differs')
            output.flush()
            os.fsync(output.fileno())
            st = os.fstat(output.fileno())
            if (st.st_uid, st.st_gid) != (row['uid'], row['gid']):
                os.fchown(output.fileno(), row['uid'], row['gid'])
            os.fchmod(output.fileno(), row['mode'])
            os.utime(output.fileno(), ns=(row['mtimeNS'], row['mtimeNS']))
        temp_path = path.parent / temporary
        libc = ctypes.CDLL(None, use_errno=True)
        libc.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
        libc.setxattr.restype = ctypes.c_int
        for name, encoded in row['extendedAttributesBase64'].items():
            raw = base64.b64decode(encoded, validate=True)
            buffer = ctypes.create_string_buffer(raw)
            require(libc.setxattr(os.fsencode(temp_path), os.fsencode(name), buffer, len(raw), 0, 1) == 0,
                    'Original xattr restoration failed')
        require(helper.extended_attributes(temp_path) == row['extendedAttributesBase64'], 'Restored xattrs differ')
        # link() fails atomically if another writer creates the canonical path.
        os.link(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.unlink(temporary, dir_fd=directory)
        os.chflags(path, row['flags'], follow_symlinks=False)
        actual = helper.full_row(path, row['bytes'])
        for key in ['path', 'kind', 'symlink', 'linkCount', 'mode', 'uid', 'gid', 'bytes', 'mtimeNS', 'flags',
                    'extendedAttributesBase64', 'additionalACLEntries', 'sha256']:
            require(actual[key] == row[key], 'Restored archive differs in ' + key)
        result['restored'] = actual
        result['status'] = 'PASS_EXACT_ARCHIVE_BYTES_AND_RESTORABLE_METADATA'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        os.close(directory)
    result['finishedAt'] = time.time()
    print(json.dumps(result))
    return 0 if result['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())
