"""Root-authorized preservation of the terminal 6aab build; never retries it."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

ROOT = Path('/Users/m1/development/anytype-d-active-20261125/main16-wave3-6aab20344fcf')
SOURCE = ROOT.parent / 'main14/source'
DERIVED = ROOT.parent / 'main14/app-derived'
OUTPUT = ROOT / 'failed-preservation1'
COMMIT = '6aab20344fcf1c645d7c96e0b9ec034ef07003a9'
TREE = '69ca9d5d7e602b6f11d309faa9882f829ebc27c1'
ORIGINALS = {
    'source': SOURCE,
    'app-derived-Products': DERIVED / 'Build/Products',
    'build16': ROOT / 'build16',
    'root-dispatch1': ROOT / 'root-dispatch1',
    'control-dispatch1': ROOT / 'control-dispatch1',
}
EXPECTED = {
    'build16/app/result.json': '56360aceba2a10eefb952ad49324f4e484c86a5d19dd0516ce16261379d1d5ac',
    'build16/app/original.log': 'ac9a61ff8e68e42ed3dd1828ebf71ce78128caa45d936757adf38aeefb76cf75',
    'build16/app/process-exit.json': 'af41dd70fe18bb4e5a92f86fc46ad667d4e9c3c2efba22d5a5f76b6ba63f7d31',
    'build16/failure.json': 'fe20d23dd30d1faf852776b7cfe1b6ac68e4c95dd68c67072fbc14213743efc8',
    'build16/source-before.json': '7bb9ad1facb2563f49dcca8b8eab29a5a91897e4c8cecad4fd21bd40da6685dd',
    'build16/source-after.json': '7bb9ad1facb2563f49dcca8b8eab29a5a91897e4c8cecad4fd21bd40da6685dd',
    'root-dispatch1/exit.json': '3bb2acf2b5f55e35d5c0efaec7039bf63f9e481e4738a80f2c07bef06ea7693a',
    'control-dispatch1/root-approved-original-producer.py': 'f92a68e8829aec99a8f1a5ebe8a25af7ed3b7c14ee8206f9a2ca6aa2a7fe2c0b',
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(name, data):
    path = OUTPUT / name
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def command(argv, timeout=90):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                            env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    return {'argv': argv, 'exitCode': result.returncode, 'stdout': result.stdout,
            'stderr': result.stderr}


def identity():
    result = command(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), 'rev-parse', 'HEAD', 'HEAD^{tree}'])
    status = command(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), 'status', '--porcelain'])
    require(result['exitCode'] == 0 and result['stdout'].splitlines() == [COMMIT, TREE], 'Physical source identity differs')
    require(status['exitCode'] == 0 and status['stdout'] == '', 'Physical source is not clean')
    return {'sourceCommit': COMMIT, 'sourceTree': TREE, 'trackedStatus': ''}


def owners():
    absent = []
    for pgid in (16415, 16387):
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            absent.append({'pgid': pgid, 'status': 'ABSENT_ESRCH'})
        else:
            raise ValueError('Original compiler/supervisor group still exists: ' + str(pgid))
    ps = command(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,etime=,command='])
    shared = []
    foreign = []
    for line in ps['stdout'].splitlines():
        fields = line.strip().split(None, 4)
        if len(fields) != 5 or int(fields[0]) == os.getpid():
            continue
        cmd = fields[4]
        compiler = any(term in cmd for term in ('xcodebuild', 'swift-frontend', '/swiftc', '/clang', 'XCBBuildService'))
        if compiler and (str(SOURCE) in cmd or str(DERIVED) in cmd):
            shared.append(line)
        elif 'xcodebuild ' in cmd:
            foreign.append(line)
        if 'main16-wave2-20261127/control/launch_app16_when_compiler_admitted.py' in cmd:
            shared.append(line)
    require(not shared, 'Shared source/cache has an active compiler or obsolete launcher')
    handles = {}
    for name, path in ORIGINALS.items():
        observed = command(['/usr/sbin/lsof', '-nP', '-Fpcfatn', '+D', str(path)], 120)
        require(observed['exitCode'] in (0, 1) and observed['stderr'] == '', 'Cannot establish open-file state: ' + name)
        writes = [line for line in observed['stdout'].splitlines() if line in ('aw', 'au')]
        require(not writes, 'Original tree has an open writer: ' + name)
        handles[name] = observed
    database = DERIVED / 'Build/Intermediates.noindex/XCBuildData/build.db'
    if database.exists():
        opened = command(['/usr/sbin/lsof', '-nP', str(database)], 30)
        require(opened['exitCode'] == 1 and opened['stdout'] == opened['stderr'] == '', 'Shared Xcode database has an owner')
    else:
        opened = {'path': str(database), 'exists': False}
    return {'observedAt': time.time(), 'originalProcessGroups': absent,
            'sharedCompilerProcesses': shared, 'foreignXcodeBuildProcesses': foreign,
            'treeOpenHandles': handles, 'database': opened}


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), 'Physical original root required')
    paths = [root] + sorted(root.rglob('*'))
    require(len(paths) < 200000, 'Unexpected source/product size')
    rows, hardlinks = {}, {}
    for path in paths:
        name = str(path.relative_to(root))
        info = path.lstat()
        row = {'mode': stat.S_IMODE(info.st_mode), 'mtimeNS': info.st_mtime_ns}
        if stat.S_ISREG(info.st_mode):
            row.update(kind='file', bytes=info.st_size, sha256=sha(path))
            if info.st_nlink > 1:
                key = (info.st_dev, info.st_ino)
                if key in hardlinks:
                    row['hardlinkTo'] = hardlinks[key]
                else:
                    hardlinks[key] = name
            after = path.lstat()
            require((after.st_ino, after.st_size, after.st_mtime_ns) == (info.st_ino, info.st_size, info.st_mtime_ns), 'Original file changed while hashing: ' + name)
        elif stat.S_ISDIR(info.st_mode):
            row['kind'] = 'directory'
        elif stat.S_ISLNK(info.st_mode):
            row.update(kind='symlink', target=os.readlink(path))
        else:
            raise ValueError('Unsupported source/product node: ' + name)
        rows[name] = row
    return rows


def clone_tree(source, destination, rows):
    """Use Darwin clonefile per regular file; never fall back to a full copy."""
    libc = ctypes.CDLL(None, use_errno=True)
    clonefile = libc.clonefile
    clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clonefile.restype = ctypes.c_int
    require(not destination.exists() and not destination.is_symlink(), 'Retention destination exists')
    directories = []
    cloned, linked, symlinks = 0, 0, 0
    for name, row in rows.items():
        original, retained = source / name, destination / name
        if row['kind'] == 'directory':
            retained.mkdir()
            directories.append((original, retained))
        elif row['kind'] == 'symlink':
            os.symlink(row['target'], retained)
            shutil.copystat(original, retained, follow_symlinks=False)
            symlinks += 1
        elif 'hardlinkTo' in row:
            os.link(destination / row['hardlinkTo'], retained, follow_symlinks=False)
            linked += 1
        else:
            require(clonefile(os.fsencode(original), os.fsencode(retained), 0) == 0,
                    'Actual APFS clonefile failed; no copy fallback: errno=' + str(ctypes.get_errno()) + ' ' + name)
            require(original.stat().st_ino != retained.stat().st_ino, 'Retained file must not share original inode')
            cloned += 1
    for original, retained in reversed(directories):
        shutil.copystat(original, retained, follow_symlinks=False)
    return {'method': 'Darwin clonefile(flags=0), no regular-file copy fallback',
            'clonefileSuccesses': cloned, 'retainedInternalHardlinks': linked, 'retainedSymlinks': symlinks}


def main():
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Failed preservation path already exists')
    identity_before = identity()
    owners_before = owners()
    for relative, expected in EXPECTED.items():
        require(sha(ROOT / relative) == expected, 'Original failed evidence changed: ' + relative)
    app = json.loads((ROOT / 'build16/app/result.json').read_text())
    require(app['status'] == 'FAIL_BUILD' and app['exitCode'] == 65 and app['ownedProcessGroup'] == 'ABSENT_ESRCH', 'Original failure identity differs')
    require(not (ROOT / 'build16/ui').exists() and not (ROOT / 'build16/receipt.json').exists(), 'UI/final evidence unexpectedly exists')
    OUTPUT.mkdir(mode=0o700)
    report = {'schema': 'pinkha-terminal-failed-build-preservation-v1', 'startedAt': time.time(),
              'status': 'FAIL', 'sourceCommit': COMMIT, 'sourceTree': TREE,
              'sourceRoot': str(SOURCE), 'appDerived': str(DERIVED),
              'originalEvidence': EXPECTED, 'originalFailure': {'exitCode': 65, 'uiPhaseRun': False, 'applicationAccepted': False},
              'sourceMutated': False, 'currentProductsMutated': False, 'cacheMutated': False,
              'applicationBuilds': 0, 'testsExecuted': 0, 'controllerSHA256': sha(__file__), 'trees': {}}
    try:
        report['identityBefore'] = identity_before
        report['ownersBefore'] = write('owners-before.json', owners_before)
        report['capacityBefore'] = write('capacity-before.json', command(['/bin/df', '-k', '/System/Volumes/Data']))
        report['freeBytesBefore'] = shutil.disk_usage(ROOT).free
        require(report['freeBytesBefore'] > 1024 ** 3, 'Insufficient metadata/receipt capacity')
        for name, original in ORIGINALS.items():
            before = inventory(original)
            before_ref = write(name + '-original-before.json', {'root': str(original), 'entries': before})
            retained = OUTPUT / name
            method = clone_tree(original, retained, before)
            cloned = inventory(retained)
            clone_ref = write(name + '-retained.json', {'root': str(retained), 'entries': cloned})
            require(cloned == before, 'Full cloned node/mode/time/link/content verification differs: ' + name)
            after = inventory(original)
            after_ref = write(name + '-original-after.json', {'root': str(original), 'entries': after})
            require(before == after, 'Original changed during preservation: ' + name)
            report['trees'][name] = {'original': str(original), 'retained': str(retained),
                                     'entries': len(before), 'logicalFileBytes': sum(row.get('bytes', 0) for row in before.values()),
                                     'before': before_ref, 'retainedManifest': clone_ref, 'after': after_ref, 'clone': method}
        report['identityAfter'] = identity()
        report['ownersAfter'] = write('owners-after.json', owners())
        for relative, expected in EXPECTED.items():
            require(sha(ROOT / relative) == expected, 'Original failed evidence changed after retention')
        cache_sizes = command(['/usr/bin/du', '-sk', str(DERIVED / 'Build/Products'),
                               str(DERIVED / 'Build/Intermediates.noindex'), str(DERIVED / 'SourcePackages'),
                               str(DERIVED / 'SDKExplicitPrecompiledModules')])
        report['warmCacheObservation'] = write('warm-cache-observation.json', cache_sizes)
        report['freeBytesAfter'] = shutil.disk_usage(ROOT).free
        report['capacityAfter'] = write('capacity-after.json', command(['/bin/df', '-k', '/System/Volumes/Data']))
        report['status'] = 'PASS_FAILED_SOURCE_PRODUCTS_AND_ORIGINAL_EVIDENCE_RETAINED'
    except BaseException as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        report['finishedAt'] = time.time()
        ref = write('receipt.json', report)
        print(json.dumps({'status': report['status'], 'receipt': ref,
                          'freeBytesBefore': report.get('freeBytesBefore'), 'freeBytesAfter': report.get('freeBytesAfter'),
                          'treeCounts': {name: row['entries'] for name, row in report['trees'].items()}}))


if __name__ == '__main__':
    main()
