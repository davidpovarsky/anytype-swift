"""Finite owned command groups with complete terminal evidence."""
import os
from pathlib import Path
import signal
import subprocess
import time

from release_contract import digest, require, timestamp, write

GROUPS = []


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def drain(pgid):
    if not group_alive(pgid):
        return
    os.killpg(pgid, signal.SIGTERM)
    limit = time.monotonic() + 10
    while group_alive(pgid) and time.monotonic() < limit:
        time.sleep(0.1)
    if group_alive(pgid):
        os.killpg(pgid, signal.SIGKILL)
        limit = time.monotonic() + 10
        while group_alive(pgid) and time.monotonic() < limit:
            time.sleep(0.1)
    require(not group_alive(pgid), 'Owned Release command group did not drain')


def command(arguments, cwd, evidence, name, timeout):
    evidence = Path(evidence)
    result = {'command': list(map(str, arguments)), 'cwd': str(cwd), 'started_at': timestamp(),
              'timeout_seconds': timeout, 'returncode': None, 'timed_out': False}
    stdout, stderr = evidence / (name + '.stdout.log'), evidence / (name + '.stderr.log')
    process = None
    try:
        with stdout.open('xb') as output, stderr.open('xb') as error:
            process = subprocess.Popen(arguments, cwd=cwd, stdout=output, stderr=error, start_new_session=True)
            result['process_group'] = process.pid
            GROUPS.append(process.pid)
            try:
                result['returncode'] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timed_out'] = True
                raise
    finally:
        if process is not None:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
            result['returncode'] = process.returncode
            # A successful command must not leave a child compiler behind.
            remaining = group_alive(process.pid)
            drain(process.pid)
            result['owned_group_drained'] = not group_alive(process.pid)
            result['unexpected_children_after_parent_exit'] = remaining
        result['finished_at'] = timestamp()
        result['stdout_sha256'] = digest(stdout) if stdout.exists() else None
        result['stderr_sha256'] = digest(stderr) if stderr.exists() else None
        write(evidence / (name + '.command.json'), result)
    require(result['returncode'] == 0 and result.get('owned_group_drained') is True
            and result.get('unexpected_children_after_parent_exit') is False,
            'Actual Release command failed or left an undrained child: ' + name)
    return stdout.read_text(errors='replace')
