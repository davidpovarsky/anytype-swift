#!/usr/bin/env python3
"""Finish only the exact archived Torah remainder after Git's permission failure."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import traceback

BASE = Path('/mnt/development/projects/evidence/wave2-owned-source-retirement-20261127')
SOURCE = Path('/mnt/development/projects/worktrees/anytype-wave2-torah-20261127')
COMMIT = '3406906e27c0f2c2d71abba52f30d20b7b612bc6'
BRANCH = 'refs/heads/codex/chatgpt-wave15-wave2-torah-20261127'
STABLE = Path('/mnt/development/projects/worktrees/anytype-wave2-property-lifecycle-20261127')
ORIGINAL = BASE / 'torah-1'
CONTROLLER = BASE / 'retire_owned_source_v2.py'


def main():
    raw = CONTROLLER.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'fdcac8721a432ce8846d76e30e21d482023e41922e644c25a00a3481166f189b'
    api = {'__name__': 'closed_source_original', '__file__': str(CONTROLLER)}
    exec(compile(raw, str(CONTROLLER), 'exec'), api)
    require, digest, write = api['require'], api['digest'], api['write_new']
    require(BASE.resolve() == BASE and not BASE.is_symlink(), 'Canonical original evidence required')
    lock = (BASE / 'source-custody-operation.lock').open('ab')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not os.path.lexists(BASE / 'active-removal.json'), 'Existing unresolved custody must not be superseded')
    output = BASE / 'torah-permission-recovery1'
    output.mkdir(mode=0o700)
    result = {'schema': 'pinkha.wave2.exact-partial-source-recovery/1', 'status': 'FAIL',
              'startedAt': api['now'](), 'source': str(SOURCE), 'sourceCommit': COMMIT,
              'controllerSHA256': digest(Path(__file__)), 'nativeStarts': 0, 'compilerStarts': 0,
              'branchDeletions': 0, 'GitConfigurationChanges': 0, 'historicalProcessGroupReprobed': False}
    claim = None
    try:
        expected = {'archive-receipt.json': 'fc080063c19e9c8585c7a359d9bcc28ddb5014f684f672e6bbb4b74dab3b2d66',
                    'retire-receipt.json': '3ebe7ec7f41da2e03ed047fc82dc56a89abd8212b53c1b6b340e6e442a561e14',
                    'removal-process-result.json': '746bb78c24bc05b0cdb83e1ddbdcb35b3362277babc50a07fada73ddb47b2f68'}
        for name, sha in expected.items():
            require(digest(ORIGINAL / name) == sha, 'Original failed attempt/custody changed')
        prepared = json.loads((ORIGINAL / 'archive-receipt.json').read_bytes())
        failed = json.loads((ORIGINAL / 'removal-process-result.json').read_bytes())
        require(prepared['status'] == 'ARCHIVED_VERIFIED_SOURCE_STILL_PRESENT'
                and prepared['identity']['commit'] == COMMIT, 'Original full source archive required')
        require(failed['exit'] == 255 and failed['status'] == 'FAIL'
                and failed['stderr'] == "error: failed to delete '" + str(SOURCE) + "': Permission denied\n"
                and failed['ownedCleanup']['status'] == 'PASS_OWNED_GROUP_ABSENT'
                and failed['ownedCleanup']['absenceEvidence']['status'] == 'ABSENT_ESRCH',
                'Only the exact terminal original permission failure is eligible')
        for name, ref in prepared['artifacts'].items():
            require(ref['path'] == str(ORIGINAL / name) and digest(ORIGINAL / name) == ref['sha256'],
                    'Original verified archive artifact changed')
        original_rows = json.loads((ORIGINAL / 'source-manifest.json').read_bytes())
        api['verify_archive'](ORIGINAL / 'source-original.tar.gz', original_rows)
        api['verify_archive'](ORIGINAL / 'git-metadata-original.tar.gz',
                              json.loads((ORIGINAL / 'git-metadata-manifest.json').read_bytes()))
        require(api['git'](STABLE, 'rev-parse', BRANCH).decode().strip() == COMMIT, 'Original branch changed')
        require(('worktree ' + str(SOURCE) + '\n').encode() not in api['git'](STABLE, 'worktree', 'list', '--porcelain'),
                'Original Git removal must already have removed this registration')
        require(not (Path('/mnt/development/projects/git-mirrors/anytype-swift.git/worktrees') / SOURCE.name).exists()
                and not os.path.lexists(SOURCE / '.git'), 'Old Git metadata unexpectedly remains or has been recreated')
        result['processObservation'] = api['active_users'](SOURCE)
        remaining = api['manifest'](SOURCE)
        originals = {row['path']: row for row in original_rows}
        for row in remaining:
            old = originals.get(row['path'])
            require(old is not None, 'A non-original path is present; refuse all cleanup')
            # Original partial unlink necessarily changed directory mtime. Every
            # other directory field and every complete file/link record must match.
            keys = set(row) - ({'mtimeNS'} if row['kind'] == 'directory' else set())
            require({key: row[key] for key in keys} == {key: old[key] for key in keys},
                    'An original remaining entry changed; refuse all cleanup')
        require(shutil.rmtree.avoids_symlink_attacks, 'Descriptor-based symlink-safe standard removal is required')
        write(output / 'qualified-remaining-manifest.json', remaining)
        result['qualifiedRemainingSHA256'] = digest(output / 'qualified-remaining-manifest.json')
        result['remainingEntries'] = len(remaining)
        result['remainingRegularBytes'] = sum(row.get('bytes', 0) for row in remaining)
        result['developmentFreeBefore'] = shutil.disk_usage(BASE).free
        source_stat = SOURCE.stat()
        claim = {'source': str(SOURCE), 'ownerPID': os.getpid(), 'at': api['now'](),
                 'phase': 'exact-permission-remainder', 'qualificationSHA256': result['qualifiedRemainingSHA256'],
                 'resultPath': str(output / 'receipt.json')}
        write(BASE / 'active-removal.json', claim)
        require(api['manifest'](SOURCE) == remaining and SOURCE.resolve() == SOURCE
                and (SOURCE.stat().st_dev, SOURCE.stat().st_ino) == (source_stat.st_dev, source_stat.st_ino),
                'Last remainder identity changed')
        shutil.rmtree(SOURCE)  # Root finishes only already-archived, exact matched remaining source files.
        api['sync_directory'](SOURCE.parent)
        require(not os.path.lexists(SOURCE), 'Closed original source remainder still exists')
        require(api['git'](STABLE, 'rev-parse', BRANCH).decode().strip() == COMMIT, 'Published branch identity changed')
        require(digest(ORIGINAL / 'source-original.tar.gz') == prepared['artifacts']['source-original.tar.gz']['sha256'],
                'Preserved full source archive changed')
        result['status'] = 'PASS_EXACT_ARCHIVED_REMAINDER_REMOVED_ORIGINAL_FAILURE_RETAINED'
        result['developmentFreeAfter'] = shutil.disk_usage(BASE).free
        result['originalFailureReceiptSHA256'] = expected['retire-receipt.json']
    except BaseException:
        result['failure'] = traceback.format_exc()
    result['finishedAt'] = api['now']()
    write(output / 'receipt.json', result)
    if result['status'].startswith('PASS_'):
        require(json.loads((BASE / 'active-removal.json').read_bytes()) == claim, 'Owned recovery claim changed')
        (BASE / 'active-removal.json').unlink()
        api['sync_directory'](BASE)
    lock.close()
    print(json.dumps({'status': result['status'], 'receipt': str(output / 'receipt.json'),
                      'sha256': digest(output / 'receipt.json'), 'failure': result.get('failure'),
                      'developmentFreeAfter': result.get('developmentFreeAfter')}), flush=True)
    return int(not result['status'].startswith('PASS_'))


if __name__ == '__main__':
    raise SystemExit(main())
