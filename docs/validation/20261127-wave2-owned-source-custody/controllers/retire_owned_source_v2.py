#!/usr/bin/env python3
"""Archive and retire only three closed, published Wave2 source worktrees.

This never removes a branch, Git history, a compiler cache, an account or a
current worktree. Archive and retirement are separate, receipt-bound phases.
"""
from pathlib import Path
import datetime
from decimal import Decimal
import gzip
import fcntl
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import traceback
import uuid

EVIDENCE = Path('/mnt/development/projects/evidence/wave2-owned-source-retirement-20261127')
STABLE = Path('/mnt/development/projects/worktrees/anytype-wave2-property-lifecycle-20261127')
SOURCES = {
    'editor': ('ac606cc0add9a861ed02edb38af956924e7b017c', 'codex/chatgpt-wave15-wave2-editor-20261127'),
    'torah': ('3406906e27c0f2c2d71abba52f30d20b7b612bc6', 'codex/chatgpt-wave15-wave2-torah-20261127'),
    'interfaces': ('2f18fe876b0d87f76403ed849dcad880c8369f28', 'codex/chatgpt-wave15-wave2-interfaces-20261127'),
}
SOURCE_RESERVE = 64 * 1024**2
CLEANUP_PATH = Path('/var/lib/pinkha-wave2-property-lifecycle-20261127/inputs/run_component.py')
CLEANUP_SHA256 = '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def git(root, *args, timeout=30):
    # Read-only Git operations. The sole destructive command uses the separate
    # reviewed owned-process boundary below, never subprocess.run's wrapper timeout.
    command = ['runuser', '-u', 'ubuntu', '-g', 'chatgpt-agent', '--',
               'git', '--no-optional-locks', '-c', 'gc.auto=0', '-C', str(root), *args]
    result = subprocess.run(command, capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'Git command failed: ' + repr(args) + '\n' + result.stderr.decode(errors='replace'))
    return result.stdout


def remove_closed_worktree(root, directory):
    require(root in {Path('/mnt/development/projects/worktrees/anytype-wave2-' + lane + '-20261127')
                     for lane in SOURCES}, 'Only the three fixed closed source paths are eligible')
    raw = CLEANUP_PATH.read_bytes()
    require(CLEANUP_PATH.resolve() == CLEANUP_PATH and not CLEANUP_PATH.is_symlink()
            and hashlib.sha256(raw).hexdigest() == CLEANUP_SHA256, 'Exact reviewed process cleanup helper required')
    namespace = {'__name__': 'wave2_cold_source_cleanup', '__file__': str(CLEANUP_PATH)}
    exec(compile(raw, str(CLEANUP_PATH), 'exec'), namespace)
    argv = ['runuser', '-u', 'ubuntu', '-g', 'chatgpt-agent', '--', 'git',
            '--no-optional-locks', '-c', 'gc.auto=0', '-C', str(STABLE), 'worktree', 'remove', str(root)]
    claim_path = EVIDENCE / 'active-removal.json'
    claim = {'nonce': str(uuid.uuid4()), 'controllerPID': os.getpid(), 'source': str(root),
             'directory': str(directory), 'argv': argv, 'createdAt': now(),
             'rule': 'Persistent custody hold until the original process group is positively absent'}
    write_new(directory / 'removal-invocation.json', claim)
    write_new(claim_path, claim)  # Durable hold exists before any mutation starts.
    claim_sha = digest(claim_path)
    process, state = None, {}
    outcome = {'status': 'FAIL', 'startedAt': now(), 'claimSHA256': claim_sha,
               'cleanupHelperSHA256': CLEANUP_SHA256, 'timeoutSeconds': 60}
    stdout, stderr = b'', b''
    try:
        # Actual read-only probe88e92a3d established that this exact runuser form
        # retains its exec'd Git child in this newly owned process group/session.
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        write_new(directory / 'removal-process-start.json',
                  {'pid': process.pid, 'processGroup': process.pid, 'claimSHA256': claim_sha, 'at': now()})
        stdout, stderr = process.communicate(timeout=60)
        outcome['exit'] = process.returncode
        require(process.returncode == 0, 'Normal Git worktree removal returned nonzero')
        outcome['status'] = 'PASS_NORMAL_GIT_WORKTREE_REMOVAL'
    except BaseException:
        outcome['failure'] = traceback.format_exc()
    finally:
        # Every post-Popen exception, including a write/timeout failure, crosses
        # the same already-reviewed cleanup boundary before custody can be released.
        if process is not None:
            namespace['finish_owned_process'](process, state, outcome)
            if process.poll() is not None:
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except BaseException:
                    outcome['pipeFinalizationFailure'] = traceback.format_exc()
                    outcome['status'] = 'FAIL'
        outcome['stdout'] = stdout.decode(errors='replace')
        outcome['stderr'] = stderr.decode(errors='replace')
        outcome['finishedAt'] = now()
        cleanup = outcome.get('ownedCleanup', {})
        terminal = (process is not None and process.poll() is not None
                    and cleanup.get('status') == 'PASS_OWNED_GROUP_ABSENT'
                    and (cleanup.get('absenceEvidence') or {}).get('status') == 'ABSENT_ESRCH')
        outcome['custodyMayBeReleased'] = terminal
        outcome['persistentHoldRetained'] = not terminal
        write_new(directory / 'removal-process-result.json', outcome)
        if terminal:
            require(digest(claim_path) == claim_sha, 'Owned custody claim changed')
            claim_path.unlink()
            sync_directory(EVIDENCE)
        # An unresolved cleanup retains the durable global hold. Every future
        # archive/retire invocation refuses it, even after this process exits.
    require(outcome['custodyMayBeReleased'], 'Owned Git closure unresolved; persistent custody hold retained')
    require(outcome['status'] == 'PASS_NORMAL_GIT_WORKTREE_REMOVAL',
            'Original Git removal failed; see retained first failure and separate cleanup result')
    return outcome['stdout']


def identity(root, expected, branch):
    require(root.is_dir() and root.resolve() == root and not root.is_symlink(), 'Canonical source directory required')
    require((root / '.git').is_file() and not (root / '.git').is_symlink(), 'Original linked-worktree pointer required')
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == expected, 'Source HEAD changed')
    require(git(root, 'symbolic-ref', 'HEAD').decode().strip() == 'refs/heads/' + branch, 'Source branch changed')
    require(git(root, 'status', '--porcelain=v1', '--untracked-files=all') == b'', 'Dirty or untracked source refused')
    remote = git(root, '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
                 'ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch).decode().strip()
    require(remote == expected + '\trefs/heads/' + branch, 'Exact published branch readback required')
    return {'commit': expected, 'tree': git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
            'branch': branch, 'remoteReadback': remote}


def manifest(root):
    require(root.resolve() == root and root.is_dir() and not root.is_symlink(), 'Canonical manifest root required')
    paths = [root]
    for directory, folders, files in os.walk(root, followlinks=False):
        paths.extend(Path(directory) / name for name in folders + files)
    rows = []
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        value = path.lstat()
        row = {'path': path.relative_to(root).as_posix(), 'mode': stat.S_IMODE(value.st_mode),
               'uid': value.st_uid, 'gid': value.st_gid, 'mtimeNS': value.st_mtime_ns}
        if stat.S_ISREG(value.st_mode):
            require(value.st_nlink == 1, 'Hard-linked regular input refused: ' + str(path))
            row.update(kind='file', bytes=value.st_size, sha256=digest(path))
        elif stat.S_ISLNK(value.st_mode):
            row.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(value.st_mode):
            row.update(kind='directory')
        else:
            raise RuntimeError('Non-source filesystem kind refused: ' + str(path))
        rows.append(row)
    return rows


def active_users(root):
    """Bounded diagnostic; owner handoffs are also required, no process signals."""
    matches, unavailable = [], 0
    prefix = str(root)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        reasons = []
        try:
            cwd = os.readlink(proc / 'cwd')
            if cwd == prefix or cwd.startswith(prefix + '/'):
                reasons.append('cwd')
            arguments = (proc / 'cmdline').read_bytes().split(b'\0')
            if any(prefix.encode() in arg for arg in arguments):
                reasons.append('argument-path')
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                    if target == prefix or target.startswith(prefix + '/'):
                        reasons.append('open-source-fd')
                        break
                except FileNotFoundError:
                    pass
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            unavailable += 1
        if reasons:
            matches.append({'pid': int(proc.name), 'reasons': sorted(set(reasons))})
    require(not matches, 'An observed process is using the source: ' + json.dumps(matches))
    return {'observedMatches': matches, 'transientOrInaccessibleProcesses': unavailable,
            'scope': 'Current diagnostic plus explicit lane-owner cold-source handoff; not historical process-group proof'}


def pack(root, rows, destination):
    with destination.open('xb') as output:
        with gzip.GzipFile(filename='', fileobj=output, mode='wb', compresslevel=1, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT, dereference=False) as archive:
                for row in rows:
                    require(shutil.disk_usage(destination.parent).free >= SOURCE_RESERVE,
                            'Source-archive reserve exhausted; original worktree remains')
                    path = root / row['path']
                    info = archive.gettarinfo(str(path), arcname=row['path'])
                    info.pax_headers['mtime'] = str(Decimal(row['mtimeNS']) / Decimal(10**9))
                    if row['kind'] == 'file':
                        with path.open('rb') as stream:
                            archive.addfile(info, stream)
                    else:
                        archive.addfile(info)
        output.flush()
        os.fsync(output.fileno())
    sync_directory(destination.parent)
    verify_archive(destination, rows)


def verify_archive(path, rows):
    expected = {row['path']: row for row in rows}
    require(len(expected) == len(rows), 'Duplicate original manifest entry')
    seen = set()
    with tarfile.open(path, mode='r:gz') as archive:
        for member in archive:
            require(member.name in expected and member.name not in seen, 'Unexpected or duplicate archive member')
            seen.add(member.name)
            row = expected[member.name]
            require((member.mode, member.uid, member.gid) == (row['mode'], row['uid'], row['gid']), 'Archive metadata mismatch')
            require(Decimal(member.pax_headers.get('mtime', str(member.mtime))) * Decimal(10**9) == row['mtimeNS'],
                    'Archive mtime mismatch')
            if row['kind'] == 'file':
                require(member.isreg() and member.size == row['bytes'], 'Archive regular file mismatch')
                stream = archive.extractfile(member)
                require(stream is not None, 'Missing archive file stream')
                with stream:
                    require(hashlib.file_digest(stream, 'sha256').hexdigest() == row['sha256'], 'Archive bytes differ')
            elif row['kind'] == 'symlink':
                require(member.issym() and member.linkname == row['target'], 'Archive symlink differs')
            else:
                require(member.isdir(), 'Archive directory differs')
    require(seen == set(expected), 'Archive omitted an original member')


def source_state(root, commit, branch):
    observed = identity(root, commit, branch)
    rows = manifest(root)
    tracked = set(git(root, 'ls-files', '-z').decode().rstrip('\0').split('\0'))
    physical = {row['path'] for row in rows if row['kind'] != 'directory'}
    require(physical <= tracked | {'.git'}, 'Ignored/untracked non-source files refused')
    gitdir = Path(git(root, 'rev-parse', '--absolute-git-dir').decode().strip())
    common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    require(gitdir.parent == common / 'worktrees' and gitdir != common, 'Separate linked-worktree metadata required')
    return observed, rows, gitdir


def main():
    phase, lane, attempt, *pins = sys.argv[1:]
    require(phase in {'archive', 'retire'} and lane in SOURCES, 'Fixed operation and owned lane required')
    require(attempt.isdigit() and 1 <= int(attempt) <= 9, 'Bounded attempt number required')
    require(len(pins) == (1 if phase == 'retire' else 0), 'Retirement requires exact prepared receipt SHA256')
    commit, branch = SOURCES[lane]
    root = Path('/mnt/development/projects/worktrees/anytype-wave2-' + lane + '-20261127')
    EVIDENCE.mkdir(mode=0o700, exist_ok=True)
    require(EVIDENCE.resolve() == EVIDENCE and not EVIDENCE.is_symlink(), 'Canonical private evidence root required')
    # One stable global custody lock covers all sources, phases and attempts,
    # acquired before creating a phase directory and held through its final receipt.
    operation_lock = (EVIDENCE / 'source-custody-operation.lock').open('ab')
    fcntl.flock(operation_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not os.path.lexists(EVIDENCE / 'active-removal.json'),
            'An earlier mutation has unresolved custody; inspect original evidence before any further action')
    directory = EVIDENCE / (lane + '-' + attempt)
    if phase == 'archive':
        directory.mkdir(mode=0o700)
    else:
        require(directory.is_dir() and directory.resolve() == directory, 'Original archive phase required')
    require(not (directory / (phase + '-receipt.json')).exists(), 'Original phase receipt must never be replaced or repeated')
    result = {'schema': 'pinkha.wave2.cold-source-custody/1', 'phase': phase, 'lane': lane,
              'source': str(root), 'startedAt': now(), 'status': 'FAIL', 'sourceCommit': commit,
              'controllerSHA256': digest(Path(__file__)), 'compilerStarts': 0, 'nativeStarts': 0,
              'branchesDeleted': 0, 'foreignPathsChanged': 0, 'buildAdmissionChanged': False}
    try:
        result['processObservation'] = active_users(root)
        observed, rows, gitdir = source_state(root, commit, branch)
        result['identity'] = observed
        result['sourceEntries'] = len(rows)
        result['rootFreeBefore'] = shutil.disk_usage('/var/lib').free
        result['developmentFreeBefore'] = shutil.disk_usage(EVIDENCE).free
        if phase == 'archive':
            source_bytes = sum(row.get('bytes', 0) for row in rows)
            require(result['developmentFreeBefore'] >= source_bytes + 2 * SOURCE_RESERVE,
                    'Uncompressed source plus two64MiB source reserves do not fit')
            metadata = manifest(gitdir)
            write_new(directory / 'source-manifest.json', rows)
            write_new(directory / 'git-metadata-manifest.json', metadata)
            pack(root, rows, directory / 'source-original.tar.gz')
            pack(gitdir, metadata, directory / 'git-metadata-original.tar.gz')
            require(manifest(root) == rows, 'Original materialized source changed during archive')
            require(manifest(gitdir) == metadata, 'Original worktree metadata changed during archive')
            require(identity(root, commit, branch) == observed, 'Published identity changed during archive')
            result['artifacts'] = {name: {'path': str(directory / name), 'bytes': (directory / name).stat().st_size,
                                         'sha256': digest(directory / name)} for name in
                                   ['source-manifest.json', 'git-metadata-manifest.json',
                                    'source-original.tar.gz', 'git-metadata-original.tar.gz']}
            result['status'] = 'ARCHIVED_VERIFIED_SOURCE_STILL_PRESENT'
        else:
            prepared_path = directory / 'archive-receipt.json'
            require(digest(prepared_path) == pins[0], 'Prepared receipt changed')
            prepared = json.loads(prepared_path.read_bytes())
            require(prepared['status'] == 'ARCHIVED_VERIFIED_SOURCE_STILL_PRESENT'
                    and prepared['source'] == str(root) and prepared['identity'] == observed
                    and prepared['controllerSHA256'] == result['controllerSHA256'], 'Prepared custody differs')
            for name, ref in prepared['artifacts'].items():
                require(ref['path'] == str(directory / name) and (directory / name).stat().st_size == ref['bytes']
                        and digest(directory / name) == ref['sha256'], 'Retained original artifact changed')
            require(rows == json.loads((directory / 'source-manifest.json').read_bytes()), 'Live source differs from archive')
            metadata = json.loads((directory / 'git-metadata-manifest.json').read_bytes())
            require(manifest(gitdir) == metadata, 'Live Git metadata differs from archive')
            verify_archive(directory / 'source-original.tar.gz', rows)
            verify_archive(directory / 'git-metadata-original.tar.gz', metadata)
            require(manifest(root) == rows and identity(root, commit, branch) == observed,
                    'Last source/identity observation changed')
            result['lastProcessObservation'] = active_users(root)
            result['preparedReceiptSHA256'] = pins[0]
            result['removalCommand'] = ['git', '-C', str(STABLE), 'worktree', 'remove', str(root)]
            # Normal Git refuses dirty worktrees. No --force, branch deletion,
            # cache deletion, source mutation or direct recursive unlink exists.
            result['removalStdout'] = remove_closed_worktree(root, directory)
            require(not os.path.lexists(root) and not gitdir.exists(), 'Original materialization remains')
            require(git(STABLE, 'rev-parse', 'refs/heads/' + branch).decode().strip() == commit,
                    'Original published branch identity changed')
            require(('worktree ' + str(root) + '\n').encode() not in git(STABLE, 'worktree', 'list', '--porcelain'),
                    'Retired source still registered')
            require(digest(directory / 'source-original.tar.gz') == prepared['artifacts']['source-original.tar.gz']['sha256'],
                    'Preserved source archive changed')
            result['status'] = 'PASS_OWN_COLD_SOURCE_MATERIALIZATION_RETIRED_ARCHIVE_RETAINED'
        result['developmentFreeAfter'] = shutil.disk_usage(EVIDENCE).free
        result['rootFreeAfter'] = shutil.disk_usage('/var/lib').free
        result['freeSpaceDeltaIsWholeHostObservation'] = True
        result['preservationScope'] = 'Exact paths, regular bytes, symlink targets, modes, owner/group and mtime; atime/ctime/inode identity is not claimed'
    except BaseException:
        result['failure'] = traceback.format_exc()
    result['finishedAt'] = now()
    output = directory / (phase + '-receipt.json')
    write_new(output, result)
    operation_lock.close()
    print(json.dumps({'status': result['status'], 'receipt': str(output), 'sha256': digest(output),
                      'failure': result.get('failure'), 'sourceEntries': result.get('sourceEntries'),
                      'developmentFreeAfter': result.get('developmentFreeAfter')}), flush=True)
    return 1 if result['status'] == 'FAIL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
