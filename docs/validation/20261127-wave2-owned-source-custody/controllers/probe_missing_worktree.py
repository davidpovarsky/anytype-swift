#!/usr/bin/env python3
"""One tiny disposable Git probe; no production repository mutation."""
from pathlib import Path
import datetime
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import traceback

BASE = Path('/mnt/development/projects/evidence/wave2-owned-source-retirement-20261127')
HELPER = Path('/var/lib/pinkha-wave2-property-lifecycle-20261127/inputs/run_component.py')
HELPER_SHA = '99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'


def main():
    raw = HELPER.read_bytes()
    assert HELPER.resolve() == HELPER and not HELPER.is_symlink() and hashlib.sha256(raw).hexdigest() == HELPER_SHA
    api = {'__name__': 'probe_original_owned_cleanup', '__file__': str(HELPER)}
    exec(compile(raw, str(HELPER), 'exec'), api)
    lock = (BASE / 'source-custody-operation.lock').open('ab')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not os.path.lexists(BASE / 'active-removal.json')
    output = BASE / 'missing-worktree-probe1.json'
    assert not output.exists()
    scratch = Path(tempfile.mkdtemp(prefix='pinkha-wave2-missing-worktree-probe-'))
    os.chown(scratch, 1001, 1002)  # Newly created probe directory only.
    os.chmod(scratch, 0o700)
    result = {'schema': 'pinkha.wave2.normal-git-missing-worktree-probe/1', 'status': 'FAIL',
              'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'scratch': str(scratch),
              'controllerSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cleanupHelperSHA256': HELPER_SHA, 'commands': [], 'productionRepositoryChanges': 0,
              'globalGitConfigurationChanges': 0, 'compilerStarts': 0, 'nativeStarts': 0,
              'historicalProcessGroupReprobed': False}

    def git(directory, *arguments, allow_failure=False):
        argv = ['runuser', '-u', 'ubuntu', '-g', 'chatgpt-agent', '--', 'git',
                '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'core.hooksPath=/dev/null',
                '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(directory), *arguments]
        record = {'argv': argv, 'status': 'FAIL'}
        result['commands'].append(record)
        process = None
        stdout, stderr = b'', b''
        try:
            process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            record.update(pid=process.pid, processGroup=process.pid)
            stdout, stderr = process.communicate(timeout=15)
            record.update(exit=process.returncode, status='PASS_EXIT0' if process.returncode == 0 else 'NONZERO_RECORDED')
        except BaseException:
            record['failure'] = traceback.format_exc()
        finally:
            if process is not None:
                api['finish_owned_process'](process, {}, record)
                if process.poll() is not None:
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                    except BaseException:
                        record['pipeFinalizationFailure'] = traceback.format_exc()
            record.update(stdout=stdout.decode(errors='replace'), stderr=stderr.decode(errors='replace'))
        cleanup = record.get('ownedCleanup', {})
        assert cleanup.get('status') == 'PASS_OWNED_GROUP_ABSENT' and (cleanup.get('absenceEvidence') or {}).get('status') == 'ABSENT_ESRCH'
        assert process is not None and process.poll() is not None and not record.get('failure') and not record.get('pipeFinalizationFailure')
        if not allow_failure:
            assert process.returncode == 0, record
        return record

    try:
        result['gitVersion'] = git(scratch, '--version')['stdout'].strip()
        repository, missing = scratch / 'repository', scratch / 'missing-worktree'
        git(scratch, 'init', '--initial-branch=probe-main', str(repository))
        (repository / 'probe.txt').write_text('Disposable normal Git missing-worktree probe only.\n')
        git(repository, 'add', '--', 'probe.txt')
        git(repository, 'commit', '-m', 'Create disposable source custody probe')
        before = git(repository, 'rev-parse', 'HEAD')['stdout'].strip()
        git(repository, 'worktree', 'add', '--detach', str(missing), 'HEAD')
        listing = git(repository, 'worktree', 'list', '--porcelain')['stdout']
        assert 'worktree ' + str(missing) + '\n' in listing
        assert missing.parent == scratch and missing.resolve() == missing and not missing.is_symlink()
        assert shutil.rmtree.avoids_symlink_attacks
        shutil.rmtree(missing)  # Only this newly created disposable probe worktree.
        assert not os.path.lexists(missing)
        removal = git(repository, 'worktree', 'remove', str(missing), allow_failure=True)
        result['normalRemoveExit'] = removal['exit']
        result['normalRemoveStdout'] = removal['stdout']
        result['normalRemoveStderr'] = removal['stderr']
        after_listing = git(repository, 'worktree', 'list', '--porcelain')['stdout']
        result['registrationRemoved'] = 'worktree ' + str(missing) + '\n' not in after_listing
        result['mainCommitUnchanged'] = git(repository, 'rev-parse', 'HEAD')['stdout'].strip() == before
        result['mainClean'] = git(repository, 'status', '--porcelain=v1', '--untracked-files=all')['stdout'] == ''
        if removal['exit'] == 0 and result['registrationRemoved'] and result['mainCommitUnchanged'] and result['mainClean']:
            result['status'] = 'PASS_NORMAL_GIT_REMOVE_ALREADY_MISSING_WORKTREE'
        else:
            result['status'] = 'UNSUPPORTED_NORMAL_REMOVE_RECORDED_NO_PRODUCTION_ACTION'
    except BaseException:
        result['failure'] = traceback.format_exc()
    result['finishedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    lock.close()
    print(json.dumps({'status': result['status'], 'receipt': str(output),
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'normalRemoveExit': result.get('normalRemoveExit'), 'failure': result.get('failure')}), flush=True)
    return int(result['status'] != 'PASS_NORMAL_GIT_REMOVE_ALREADY_MISSING_WORKTREE')


if __name__ == '__main__':
    raise SystemExit(main())
