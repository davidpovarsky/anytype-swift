#!/usr/bin/env python3
"""Retire one exact archived cold source, preserving original modes/owners.

The actual tiny Git2.43 probe proves normal removal of a missing linked
worktree. Root removes only this fully archived, identity-bound source tree;
normal unprivileged Git then removes only its missing registration. One global
lock and a durable claim cover both operations and all final postconditions.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import traceback
import uuid

BASE = Path('/mnt/development/projects/evidence/wave2-owned-source-retirement-20261127')
SOURCE = Path('/mnt/development/projects/worktrees/anytype-wave2-interfaces-20261127')
COMMIT = '2f18fe876b0d87f76403ed849dcad880c8369f28'
BRANCH = 'refs/heads/codex/chatgpt-wave15-wave2-interfaces-20261127'
STABLE = Path('/mnt/development/projects/worktrees/anytype-wave2-property-lifecycle-20261127')
ORIGINAL = BASE / 'interfaces-1'
CONTROLLER = BASE / 'retire_owned_source_v2.py'
CONTROLLER_SHA = 'fdcac8721a432ce8846d76e30e21d482023e41922e644c25a00a3481166f189b'
ARCHIVE_RECEIPT_SHA = '5c0e070323828c53e6e2092a1981787831c06384b11cb8a354e0d8dd23486104'
PROBE_SHA = '3313463a0caa452ededa7b9606617845e1c400a382a79bf969b06cf9ea5fa7f3'
PROBE_CONTROLLER_SHA = 'c2dfa66859a4bd823b81061645e279ec4aae049b9b13310dbabb751abd1cf585'
HELPER_SHA = '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'


def remove_missing_registration(api, cleanup, output, claim_sha):
    """Same original Git command/99dc closure; the caller retains the claim."""
    require, write = api['require'], api['write_new']
    require(not os.path.lexists(SOURCE), 'Source must already be exactly archived and absent')
    argv = ['runuser', '-u', 'ubuntu', '-g', 'chatgpt-agent', '--', 'git',
            '--no-optional-locks', '-c', 'gc.auto=0', '-C', str(STABLE), 'worktree', 'remove', str(SOURCE)]
    result = {'status': 'FAIL', 'argv': argv, 'claimSHA256': claim_sha, 'startedAt': api['now'](),
              'cleanupHelperSHA256': HELPER_SHA, 'timeoutSeconds': 60}
    process, first = None, None
    stdout, stderr = b'', b''
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        write(output / 'removal-process-start.json',
              {'pid': process.pid, 'processGroup': process.pid, 'claimSHA256': claim_sha, 'at': api['now']()})
        stdout, stderr = process.communicate(timeout=60)
        result['exit'] = process.returncode
        require(process.returncode == 0, 'Normal missing-worktree Git removal returned nonzero')
        result['status'] = 'PASS_NORMAL_GIT_MISSING_WORKTREE_REMOVAL'
    except BaseException as error:
        first = error
        result['failure'] = traceback.format_exc()
    finally:
        if process is not None:
            try:
                cleanup['finish_owned_process'](process, {}, result)
            except BaseException as error:
                result['cleanupFailure'] = traceback.format_exc()
                result['status'] = 'FAIL'
                first = first or error
            if process.poll() is not None:
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except BaseException as error:
                    result['pipeFinalizationFailure'] = traceback.format_exc()
                    result['status'] = 'FAIL'
                    first = first or error
        result.update(stdout=stdout.decode(errors='replace'), stderr=stderr.decode(errors='replace'), finishedAt=api['now']())
        observed = result.get('ownedCleanup', {})
        result['ownedChildTerminal'] = (process is not None and process.poll() is not None
            and observed.get('status') == 'PASS_OWNED_GROUP_ABSENT'
            and (observed.get('absenceEvidence') or {}).get('status') == 'ABSENT_ESRCH')
        try:
            write(output / 'removal-process-result.json', result)
        except BaseException as save_error:
            if first is not None:
                first.add_note('Original process-result write also failed: ' + repr(save_error))
                raise first from save_error
            raise
    if first is not None:
        raise first
    require(result['ownedChildTerminal'] and result['status'] == 'PASS_NORMAL_GIT_MISSING_WORKTREE_REMOVAL',
            'Original Git result/owned closure did not pass; persistent caller claim remains')
    return result


def metadata_permissions(api, gitdir, rows):
    """Actual ubuntu permissions, before either production mutation."""
    paths = [str(gitdir.parent)] + [str(gitdir / row['path']) for row in rows if row['kind'] == 'directory']
    code = 'import os,json,sys; p=json.loads(sys.argv[1]); print(json.dumps({"uid":os.geteuid(),"gid":os.getegid(),"directories":[{"path":x,"writeExecute":os.access(x,os.W_OK|os.X_OK)} for x in p]}))'
    completed = subprocess.run(['runuser', '-u', 'ubuntu', '-g', 'chatgpt-agent', '--',
                                'python3', '-c', code, json.dumps(paths)], capture_output=True, timeout=15)
    api['require'](completed.returncode == 0, 'Original Git metadata permission observation failed')
    value = json.loads(completed.stdout)
    api['require'](value['uid'] == 1001 and value['gid'] == 1002
                   and [row['path'] for row in value['directories']] == paths
                   and all(row['writeExecute'] is True for row in value['directories']),
                   'Normal Git cannot remove the original metadata directories; source must remain')
    return value


def main():
    assert len(sys.argv) == 1 and os.geteuid() == 0
    raw = CONTROLLER.read_bytes()
    assert CONTROLLER.resolve() == CONTROLLER and not CONTROLLER.is_symlink()
    assert hashlib.sha256(raw).hexdigest() == CONTROLLER_SHA
    api = {'__name__': 'interfaces_archived_original', '__file__': str(CONTROLLER)}
    exec(compile(raw, str(CONTROLLER), 'exec'), api)
    require, digest, write = api['require'], api['digest'], api['write_new']
    require(api['STABLE'] == STABLE and api['SOURCES']['interfaces'] == (COMMIT, BRANCH.removeprefix('refs/heads/')),
            'Exact approved original source scope required')
    helper = api['CLEANUP_PATH']
    helper_raw = helper.read_bytes()
    require(helper.resolve() == helper and not helper.is_symlink() and hashlib.sha256(helper_raw).hexdigest() == HELPER_SHA,
            'Exact original owned-process cleanup must exist before source removal')
    cleanup = {'__name__': 'interfaces_original_owned_cleanup', '__file__': str(helper)}
    exec(compile(helper_raw, str(helper), 'exec'), cleanup)
    require(BASE.resolve() == BASE and not BASE.is_symlink(), 'Canonical original evidence root required')
    lock = (BASE / 'source-custody-operation.lock').open('ab')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not os.path.lexists(BASE / 'active-removal.json'), 'Existing unresolved custody must not be superseded')
    output = BASE / 'interfaces-archived-removal1'
    output.mkdir(mode=0o700)
    result = {'schema': 'pinkha.wave2.exact-archived-source-retirement/1', 'status': 'FAIL',
              'startedAt': api['now'](), 'source': str(SOURCE), 'sourceCommit': COMMIT,
              'controllerSHA256': digest(Path(__file__)), 'originalControllerSHA256': CONTROLLER_SHA,
              'archiveReceiptSHA256': ARCHIVE_RECEIPT_SHA, 'missingWorktreeProbeSHA256': PROBE_SHA,
              'nativeStarts': 0, 'compilerStarts': 0, 'branchDeletions': 0, 'GitConfigurationChanges': 0,
              'existingPermissionsOrOwnershipChanges': 0, 'historicalProcessGroupReprobed': False,
              'freeSpaceDeltaIsWholeHostObservation': True}
    claim_sha, first = None, None
    try:
        require(digest(BASE / 'missing-worktree-probe1.json') == PROBE_SHA, 'Original actual missing-worktree probe changed')
        probe = json.loads((BASE / 'missing-worktree-probe1.json').read_bytes())
        require(probe['status'] == 'PASS_NORMAL_GIT_REMOVE_ALREADY_MISSING_WORKTREE'
                and probe['normalRemoveExit'] == 0 and probe['registrationRemoved'] is True
                and probe['mainCommitUnchanged'] is True and probe['mainClean'] is True
                and probe['productionRepositoryChanges'] == 0 and probe['controllerSHA256'] == PROBE_CONTROLLER_SHA
                and probe['cleanupHelperSHA256'] == HELPER_SHA
                and api['git'](STABLE, '--version').decode().strip() == probe['gitVersion'],
                'Actual same-Git normal missing-registration removal proof required')
        require(digest(ORIGINAL / 'archive-receipt.json') == ARCHIVE_RECEIPT_SHA, 'Original completed archive receipt changed')
        prepared = json.loads((ORIGINAL / 'archive-receipt.json').read_bytes())
        require(prepared['status'] == 'ARCHIVED_VERIFIED_SOURCE_STILL_PRESENT'
                and prepared['source'] == str(SOURCE) and prepared['identity']['commit'] == COMMIT
                and prepared['identity']['branch'] == BRANCH.removeprefix('refs/heads/')
                and prepared['controllerSHA256'] == CONTROLLER_SHA, 'Exact approved completed source archive required')
        require(set(prepared['artifacts']) == {'source-manifest.json', 'git-metadata-manifest.json',
                                              'source-original.tar.gz', 'git-metadata-original.tar.gz'},
                'Exactly the original four source-custody artifacts required')
        for name, ref in prepared['artifacts'].items():
            path = ORIGINAL / name
            require(ref['path'] == str(path) and path.resolve() == path and not path.is_symlink()
                    and path.stat().st_size == ref['bytes'] and digest(path) == ref['sha256'],
                    'Original source/metadata/archive artifact changed')
        identity, current, gitdir = api['source_state'](SOURCE, COMMIT, BRANCH.removeprefix('refs/heads/'))
        original_rows = json.loads((ORIGINAL / 'source-manifest.json').read_bytes())
        metadata = json.loads((ORIGINAL / 'git-metadata-manifest.json').read_bytes())
        require(identity == prepared['identity'] and current == original_rows, 'Every original live source entry must match its archive')
        require(api['manifest'](gitdir) == metadata, 'Every original live Git metadata entry must match its archive')
        api['verify_archive'](ORIGINAL / 'source-original.tar.gz', original_rows)
        api['verify_archive'](ORIGINAL / 'git-metadata-original.tar.gz', metadata)
        registration = ('worktree ' + str(SOURCE) + '\n').encode()
        require(api['git'](STABLE, 'worktree', 'list', '--porcelain').count(registration) == 1,
                'Exactly one original linked-worktree registration required')
        result['metadataPermissions'] = metadata_permissions(api, gitdir, metadata)
        result['processObservation'] = api['active_users'](SOURCE)
        require(shutil.rmtree.avoids_symlink_attacks, 'Descriptor-safe standard source removal required')
        require(SOURCE.resolve() == SOURCE and SOURCE.parent.resolve() == SOURCE.parent and not SOURCE.is_symlink(),
                'Exact canonical fixed cold source root required')
        source_stat = SOURCE.lstat()
        require(stat.S_ISDIR(source_stat.st_mode), 'Original fixed source directory required')
        result.update(identity=identity, sourceEntries=len(current), gitMetadataPath=str(gitdir),
                      sourceRegularBytes=sum(row.get('bytes', 0) for row in current),
                      sourceAllocatedBytes=sum((SOURCE / row['path']).lstat().st_blocks * 512 for row in current),
                      rootFreeBefore=shutil.disk_usage('/var/lib').free,
                      developmentFreeBefore=shutil.disk_usage(BASE).free)
        claim = {'nonce': str(uuid.uuid4()), 'ownerPID': os.getpid(), 'at': api['now'](),
                 'source': str(SOURCE), 'sourceCommit': COMMIT, 'metadata': str(gitdir),
                 'sourceDevice': source_stat.st_dev, 'sourceInode': source_stat.st_ino,
                 'phase': 'exact-archived-source-and-missing-registration', 'resultPath': str(output / 'receipt.json'),
                 'archiveReceiptSHA256': ARCHIVE_RECEIPT_SHA, 'controllerSHA256': result['controllerSHA256']}
        write(output / 'retirement-invocation.json', claim)
        write(BASE / 'active-removal.json', claim)
        claim_sha = digest(BASE / 'active-removal.json')
        result['persistentClaimSHA256'] = claim_sha
        # All original metadata, modes and owners are still unchanged here.
        require(api['manifest'](SOURCE) == current and api['manifest'](gitdir) == metadata
                and api['identity'](SOURCE, COMMIT, BRANCH.removeprefix('refs/heads/')) == identity,
                'Last original source/metadata/published identity observation changed')
        parent_fd = os.open(SOURCE.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            final_stat = os.stat(SOURCE.name, dir_fd=parent_fd, follow_symlinks=False)
            require(stat.S_ISDIR(final_stat.st_mode) and (final_stat.st_dev, final_stat.st_ino)
                    == (source_stat.st_dev, source_stat.st_ino), 'Final fixed source inode changed')
            shutil.rmtree(SOURCE.name, dir_fd=parent_fd)
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        require(not os.path.lexists(SOURCE), 'Exact archived source materialization remains')
        result['sourceRemovedAt'] = api['now']()
        result['normalGitRemoval'] = remove_missing_registration(api, cleanup, output, claim_sha)
        require(not os.path.lexists(SOURCE) and not os.path.lexists(gitdir), 'Original source or registration metadata remains')
        require(registration not in api['git'](STABLE, 'worktree', 'list', '--porcelain'), 'Original registration remains')
        require(api['git'](STABLE, 'rev-parse', BRANCH).decode().strip() == COMMIT, 'Original published branch identity changed')
        for name in ('source-original.tar.gz', 'git-metadata-original.tar.gz'):
            require(digest(ORIGINAL / name) == prepared['artifacts'][name]['sha256'], 'Retained original archive changed')
        result.update(status='PASS_EXACT_ARCHIVED_SOURCE_AND_REGISTRATION_RETIRED',
                      developmentFreeAfter=shutil.disk_usage(BASE).free, rootFreeAfter=shutil.disk_usage('/var/lib').free,
                      originalModesOwnersAndMtimesRetainedInArchives=True, branchPreserved=COMMIT)
    except BaseException as error:
        first = error
        result['failure'] = traceback.format_exc()
    result['finishedAt'] = api['now']()
    result['persistentHoldRequired'] = result['status'] != 'PASS_EXACT_ARCHIVED_SOURCE_AND_REGISTRATION_RETIRED' and claim_sha is not None
    try:
        write(output / 'receipt.json', result)
    except BaseException as save_error:
        if first is not None:
            first.add_note('Final retirement receipt write also failed: ' + repr(save_error))
            raise first from save_error
        raise
    if result['status'] == 'PASS_EXACT_ARCHIVED_SOURCE_AND_REGISTRATION_RETIRED':
        require(claim_sha is not None and digest(BASE / 'active-removal.json') == claim_sha, 'Owned retirement claim changed')
        (BASE / 'active-removal.json').unlink()
        api['sync_directory'](BASE)
    lock.close()
    print(json.dumps({'status': result['status'], 'receipt': str(output / 'receipt.json'),
                      'sha256': digest(output / 'receipt.json'), 'failure': result.get('failure'),
                      'persistentHoldPresent': os.path.lexists(BASE / 'active-removal.json'),
                      'developmentFreeAfter': result.get('developmentFreeAfter'), 'rootFreeAfter': result.get('rootFreeAfter')}), flush=True)
    return int(result['status'] != 'PASS_EXACT_ARCHIVED_SOURCE_AND_REGISTRATION_RETIRED')


if __name__ == '__main__':
    raise SystemExit(main())
