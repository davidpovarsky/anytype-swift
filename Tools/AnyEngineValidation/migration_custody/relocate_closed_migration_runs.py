#!/usr/bin/env python3
"""Preserve exactly eight completed C proof/account-copy directories.

All original PASS/FAIL outcomes and private copied account bytes remain intact.
No account API, compiler, native process or original182 replay is dispatched.
The original182 account/private-work, canonical8 receipt, current Swift cache and
queued prepared3 stay physical and unchanged. Only verified duplicates retire.
"""
from pathlib import Path
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import stat
import sys
import time
import traceback

if sys.flags.optimize:
    raise RuntimeError('Custody guards require assertions; optimized Python execution is refused.')

HELPER = Path(__file__).with_name('relocate_cold_preservation_products.py')
HELPER_SHA = '691aa1bd72da1e39c1ef6b1be1d51d6732fe5dd62f4cb6d9337b8ed5c8c6d928'
HELPER_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-c-retained-preservation-products-relocated-20261127/result.json')
HELPER_RECEIPT_SHA = '09e189d3e33a5852636fd61304bcc1ee5ecb241312f2d705f77bbd753ae593fb'
BASE = Path('/var/lib/pinkha-w1-functional-migration-20261127')
OUT = Path('/mnt/development/projects/evidence/pinkha-c-completed-runs-relocated-20261127')
RETAINED = OUT / 'retained'
CANONICAL = BASE / 'canonical-definition-native-attempt3'
CANONICAL_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
EXPECTED = {
    'bookmark-native-attempt1': (24, 15, 8867840, '2d6ef0ebf1a5150f661cc224dcde15e5c7e3b17d30a4ded44e5465badd7fe011', 'FAIL'),
    'bookmark-native-attempt2': (36, 17, 9666560, '3bb95992e4f04f7b5dc0a04f2552763ab25f51cd7f4c1da5840ae4e9e52eaed1', 'FAIL'),
    'bookmark-native-attempt3': (36, 17, 9687040, 'ddc0ef623701dfeb0d9bbe5431f84bf495e73a5f6b485da4e60261d4bb40e902', 'FAIL'),
    'bookmark-native-attempt4': (39, 17, 9830400, 'c87d8170cb0ad9514f61731db773c1baee703d62ff520d2041e307f745be4756', 'FAIL'),
    'bookmark-native-attempt5': (49, 17, 10575872, '48a64384f9702df073c27d4e9a8f4d889a9a91af3521fee280d6098f17b5bc22', 'PASS'),
    'graph-native-attempt1': (28, 14, 9027584, 'b1473317fabd37b5e69a3da4eaf697eb9f72c3cc01363302f3d8a7ac1b3f8713', 'PASS'),
    'definition-directory-native-attempt1': (38, 14, 10539008, '88351df49119cf55b0dac3b3395569c6d6d244768f6061a2fb46bcce3bdba111', 'PASS'),
    'canonical-definition-native-attempt2': (26, 14, 8798208, 'e694ca01ea35c93c291de212b5de270e1cafb30099e6873fa9794ef7152dce40', 'FAIL'),
}
MIB = 1024**2
DEV_FLOOR = 512 * MIB
DEADLINE = 300
CONTROL_CAP = 8 * MIB


def import_helpers():
    fd = os.open(HELPER, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(65536)
    assert hashlib.sha256(raw).hexdigest() == HELPER_SHA
    # Execute the already qualified exact source without an ordinary loader
    # read that would change retained access times or create bytecode files.
    spec = importlib.util.spec_from_loader('qualified_cold_custody', loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(HELPER), 'exec'), module.__dict__)
    return module


def main():
    os.umask(0o077); helper = import_helpers()
    assert OUT.parent.resolve() == OUT.parent and not os.path.lexists(OUT)
    OUT.mkdir(mode=0o700); RETAINED.mkdir(mode=0o700)
    started = time.monotonic(); phase = 'admission'; protected = canonical_before = None
    parent_fd = None; locks = {}; snapshots = {}; copies = {}
    result = {'status': 'FAIL', 'protocol': 'pinkha-c-eight-completed-run-custody-v1', 'errors': [],
              'compilerInvocations': 0, 'nativeInvocations': 0, 'accountAPICalls': 0,
              'original182OperationsReplayed': 0, 'relocated': [], 'retiredMembers': {},
              'sourcePaths': [str(BASE / name) for name in sorted(EXPECTED)],
              'resourcePolicy': {'purpose': 'capacity recovery only; native/build floor unchanged',
                  'nativeRootFloorUnchanged': 2 * 1024**3, 'rootBulkBytesWritten': 0,
                  'developmentRuntimeFloor': DEV_FLOOR, 'controlCap': CONTROL_CAP,
                  'maximumSeconds': DEADLINE, 'rootControlAllowanceBytes': 4 * MIB}}

    def guard():
        root_free, dev_free = shutil.disk_usage('/').free, shutil.disk_usage(OUT).free
        result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes', root_free), root_free)
        result['minimumDevelopmentFreeBytes'] = min(result.get('minimumDevelopmentFreeBytes', dev_free), dev_free)
        assert time.monotonic() - started < DEADLINE
        assert dev_free >= DEV_FLOOR and root_free >= 4 * MIB
        controls = sum((OUT / name).lstat().st_size for name in helper.names(OUT)
                       if stat.S_ISREG((OUT / name).lstat().st_mode))
        assert controls <= CONTROL_CAP
        return root_free, dev_free

    def save():
        result.update(phase=phase, seconds=round(time.monotonic() - started, 3))
        helper.write(OUT / 'result.json', result, replace=True)

    def tree(root):
        assert root.resolve() == root and not root.is_symlink()
        directory = helper.metadata(root); stack = [root]; rows = {}
        while stack:
            path = stack.pop(); row = helper.metadata(path)
            relative = path.relative_to(root).as_posix()
            assert row['device'] == directory['device'], 'nested mounted data is not admitted'
            if stat.S_ISDIR(row['mode']):
                stack.extend(path / name for name in reversed(helper.names(path)))
            else:
                assert stat.S_ISREG(row['mode']) and row['links'] == 1, 'symlink/special/external-hardlink refused'
                row['sha256'] = helper.sha(path)
            assert helper.metadata(path) == {k: v for k, v in row.items() if k != 'sha256'}
            if relative != '.': rows[relative] = row
            assert len(rows) <= 256
        assert helper.metadata(root) == directory
        return {'directory': directory, 'files': rows}

    def portable(manifest):
        return {'directory': helper.portable(manifest['directory'], True),
                'files': {name: helper.portable(row, stat.S_ISDIR(row['mode']))
                          for name, row in manifest['files'].items()}}

    def all_rows(manifest):
        return [manifest['directory']] + list(manifest['files'].values())

    def copy_tree(source, target, manifest):
        target.mkdir(mode=0o700)
        for relative, row in sorted(manifest['files'].items(), key=lambda pair: (len(Path(pair[0]).parts), pair[0])):
            original, copied = source / relative, target / relative; guard()
            if stat.S_ISDIR(row['mode']):
                copied.mkdir(mode=0o700); continue
            incoming = os.open(original, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
            outgoing = os.open(copied, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(incoming)
                assert (info.st_dev, info.st_ino) == (row['device'], row['inode'])
                h, count = hashlib.sha256(), 0
                while data := os.read(incoming, MIB):
                    guard(); h.update(data); count += len(data); assert count <= row['bytes']
                    view = memoryview(data)
                    while view:
                        written = os.write(outgoing, view); assert written > 0; view = view[written:]
                assert count == row['bytes'] and h.hexdigest() == row['sha256']; os.fsync(outgoing)
            finally:
                os.close(incoming); os.close(outgoing)
            helper.restore_metadata(copied, row)
            fd = os.open(copied, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
            try: os.fsync(fd)
            finally: os.close(fd)
        directories = [('.', manifest['directory'])] + [
            (name, row) for name, row in manifest['files'].items() if stat.S_ISDIR(row['mode'])]
        for name, row in sorted(directories, key=lambda pair: len(Path(pair[0]).parts), reverse=True):
            helper.restore_metadata(target / name, row); helper.fsync_dir(target / name)
        helper.fsync_dir(target.parent)

    def unchanged_protected():
        assert helper.protected_inputs() == protected
        assert CANONICAL.resolve() == CANONICAL and not CANONICAL.is_symlink()
        assert helper.metadata(CANONICAL) == canonical_before
        assert helper.sha(CANONICAL / 'result.json') == CANONICAL_SHA
        assert helper.sha(HELPER) == HELPER_SHA

    try:
        signal.signal(signal.SIGTERM, helper.interrupted); signal.signal(signal.SIGINT, helper.interrupted)
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
        result['controllerSHA256'] = helper.sha(Path(__file__))
        result['qualifiedHelperSHA256'] = HELPER_SHA
        proof = helper.read_json(HELPER_RECEIPT, HELPER_RECEIPT_SHA)
        assert proof['status'] == 'PASS_EXACT_COLD_PRESERVATION_PRODUCTS_STABLE_PATH'
        assert proof['protectedAccountsPlansAndPrepared3Unchanged'] and proof['sourceDirectoryRetired']
        result['qualifiedHelperReceiptSHA256'] = HELPER_RECEIPT_SHA
        assert BASE.resolve() == BASE and not BASE.is_symlink()
        parent_fd = os.open(BASE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME)
        protected = helper.protected_inputs(); helper.write(OUT / 'protected-before.json', protected)
        assert CANONICAL.resolve() == CANONICAL and helper.sha(CANONICAL / 'result.json') == CANONICAL_SHA
        canonical_before = helper.metadata(CANONICAL)
        guard(); total_allocated = copy_bound = 0; block = os.statvfs(OUT).f_frsize
        for name, (files, dirs, allocated, receipt_sha, status) in EXPECTED.items():
            source = BASE / name
            assert not os.path.lexists(BASE / (name + '.verified-custody-exchange-20261127'))
            fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); locks[name] = fd
            snapshot = tree(source); rows = all_rows(snapshot)
            assert sum(stat.S_ISREG(row['mode']) for row in rows) == files
            assert sum(stat.S_ISDIR(row['mode']) for row in rows) == dirs
            assert sum(row['allocatedBytes'] for row in rows) == allocated
            assert snapshot['files']['result.json']['sha256'] == receipt_sha
            original = helper.read_json(source / 'result.json', receipt_sha)
            assert original.get('status', original.get('result')) == status
            snapshots[name] = snapshot; total_allocated += allocated
            copy_bound += sum(block if stat.S_ISDIR(row['mode']) else
                ((row['bytes'] + block - 1) // block) * block for row in rows)
        assert total_allocated == 76992512 and len(snapshots) == 8
        roots = [BASE / name for name in EXPECTED] + [RETAINED]
        result['liveUsesBefore'] = helper.live_uses(list(snapshots.values()), roots)
        assert not result['liveUsesBefore']
        root_free, dev_free = guard(); assert dev_free >= DEV_FLOOR + copy_bound + 16 * MIB
        result.update(rootFreeBefore=root_free, developmentFreeBefore=dev_free, copyUpperBytes=copy_bound,
                      originalAllocatedBytes=total_allocated, originalPassCount=3, originalFailCount=5)
        helper.write(OUT / 'all-source-before.json', snapshots)
        result['sourceManifestSHA256'] = helper.sha(OUT / 'all-source-before.json')
        phase = 'copying closed accounts and all evidence'; save()
        for name, snapshot in snapshots.items():
            copy_tree(BASE / name, RETAINED / name, snapshot)
            copies[name] = tree(RETAINED / name)
            assert portable(copies[name]) == portable(snapshot)
            assert tree(BASE / name) == snapshot
        helper.write(OUT / 'all-destination-before.json', copies)
        unchanged_protected(); assert not helper.live_uses(list(snapshots.values()) + list(copies.values()), roots)
        helper.write(OUT / 'restoration-map.json', {
            'roots': {str(BASE / name): str(RETAINED / name) for name in EXPECTED},
            'manifest': str(OUT / 'all-source-before.json'), 'manifestSHA256': result['sourceManifestSHA256'],
            'currentQueuedPhysicalDependenciesMoved': False, 'hardlinkTopology': [],
            'restoreRequires': ['no live use by inode/fd/maps/cwd/command',
                'root>=2GiB plus exact copy and16MiB; dev>=512MiB',
                'exclusive same-parent physical copy with full original portable metadata, hashes and fsync',
                'current stable-link inode/target fence and atomic renameat2 exchange',
                'keep the full development copy; never replace a raced source entry'],
            'completedControllerReuse': 'Restore its exact physical source path before any old controller needing resolve()==path; no such rerun is authorized by this custody.'})
        result['restorationMapSHA256'] = helper.sha(OUT / 'restoration-map.json')
        phase = 'verified before atomic exchanges'; save()
        libc = ctypes.CDLL(None, use_errno=True); exchange = libc.renameat2
        exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        exchange.restype = ctypes.c_int
        for name, snapshot in snapshots.items():
            guard(); source, target = BASE / name, RETAINED / name
            barrier = BASE / (name + '.verified-custody-exchange-20261127')
            assert tree(source) == snapshot and tree(target) == copies[name]
            assert not helper.live_uses([snapshot, copies[name]], [source, target, barrier])
            os.symlink(str(target), barrier.name, dir_fd=parent_fd); os.fsync(parent_fd)
            link = os.stat(barrier.name, dir_fd=parent_fd, follow_symlinks=False)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            original = snapshot['directory']
            assert (current.st_dev, current.st_ino, current.st_ctime_ns) == (original['device'], original['inode'], original['ctime_ns'])
            assert exchange(parent_fd, os.fsencode(name), parent_fd, os.fsencode(barrier.name), 2) == 0, os.strerror(ctypes.get_errno())
            os.fsync(parent_fd); result['relocated'].append(name)
            assert source.is_symlink() and source.resolve() == target
            assert (source.lstat().st_dev, source.lstat().st_ino) == (link.st_dev, link.st_ino)
            moved = tree(barrier)
            assert moved['files'] == snapshot['files']
            assert {k: v for k, v in moved['directory'].items() if k != 'ctime_ns'} == {
                k: v for k, v in original.items() if k != 'ctime_ns'}
            assert tree(target) == copies[name]
            for relative, row in snapshot['files'].items():
                if stat.S_ISREG(row['mode']): assert helper.sha(source / relative) == row['sha256']
            assert not helper.live_uses([snapshot, copies[name]], [source, target, barrier])
            phase = 'retiring verified duplicate ' + name; save(); guard()
            assert tree(barrier) == moved; result['retiredMembers'][name] = []
            for relative, row in sorted(snapshot['files'].items(), key=lambda pair: (len(Path(pair[0]).parts), pair[0]), reverse=True):
                member = barrier / relative
                if stat.S_ISDIR(row['mode']):
                    assert helper.names(member) == []
                    assert (member.lstat().st_dev, member.lstat().st_ino) == (row['device'], row['inode'])
                    member.rmdir()
                else:
                    assert helper.metadata(member) == {k: v for k, v in row.items() if k != 'sha256'}
                    assert helper.sha(member) == row['sha256'] and helper.sha(target / relative) == row['sha256']
                    assert (member.lstat().st_dev, member.lstat().st_ino) == (row['device'], row['inode'])
                    member.unlink()
                result['retiredMembers'][name].append(relative)
            assert helper.names(barrier) == []
            assert (barrier.lstat().st_dev, barrier.lstat().st_ino) == (original['device'], original['inode'])
            barrier.rmdir(); os.fsync(parent_fd)
            assert not os.path.lexists(barrier) and source.resolve() == target
            assert tree(target) == copies[name]
        assert len(result['relocated']) == 8
        assert helper.sha(Path(__file__)) == result['controllerSHA256']
        for name, expected in EXPECTED.items():
            assert tree(RETAINED / name) == copies[name]
            assert helper.sha(BASE / name / 'result.json') == expected[3]
        result.update(status='PASS_EXACT_EIGHT_COMPLETED_C_RUNS_STABLE_PATHS',
                      recoveredRootAllocatedBytes=total_allocated, allOriginalOutcomesAndAccountBytesRetained=True)
        phase = 'completed'
    except BaseException as error:
        result['status'] = 'FAIL_EIGHT_C_RUN_CUSTODY'
        result['errors'].append({'phase': phase, 'type': type(error).__name__, 'message': str(error)})
        helper.write(OUT / 'failure.json', {'phase': phase, 'traceback': traceback.format_exc()})
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN); signal.signal(signal.SIGINT, signal.SIG_IGN)
        if protected is not None:
            try:
                final = helper.protected_inputs(); helper.write(OUT / 'protected-final.json', final)
                unchanged_protected()
                result['protectedAccountsPlansCanonicalAndPrepared3Unchanged'] = True
                result['protectedFinalSHA256'] = helper.sha(OUT / 'protected-final.json')
            except BaseException as error:
                result['status'] = 'FAIL_EIGHT_C_RUN_CUSTODY'
                result['protectedAccountsPlansCanonicalAndPrepared3Unchanged'] = False
                result['errors'].append({'finalProtectedIntegrity': str(error), 'type': type(error).__name__})
        for fd in list(locks.values()) + ([parent_fd] if parent_fd is not None else []):
            try: os.close(fd)
            except OSError as error:
                result['status'] = 'FAIL_EIGHT_C_RUN_CUSTODY'; result['errors'].append({'close': str(error)})
        result['rootFreeAfter'] = shutil.disk_usage('/').free
        result['developmentFreeAfter'] = shutil.disk_usage(OUT).free
        save()
        print(json.dumps({'status': result['status'], 'result': str(OUT / 'result.json'),
            'sha256': helper.sha(OUT / 'result.json'), 'seconds': result['seconds'], 'errors': result['errors'],
            'rootFreeAfter': result['rootFreeAfter'], 'developmentFreeAfter': result['developmentFreeAfter']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
