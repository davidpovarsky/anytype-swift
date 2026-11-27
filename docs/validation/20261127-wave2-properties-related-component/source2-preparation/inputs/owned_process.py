"""Exact owned-process cleanup primitives from the actual Properties runner99dc.
No historical process-group identifier is observed or signalled.
"""
from pathlib import Path
import datetime
import errno
import os
import signal
import subprocess
import time
import traceback


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def group_members(pgid):
    rows = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            stat = (p / 'stat').read_text()
            fields = stat[stat.rindex(')') + 2:].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                rows.append(int(p.name))
        except (OSError, ValueError, IndexError):
            pass
    return sorted(rows)


def observe_owned_group(process, state):
    """Observe only this new owned group; an absence latch is irreversible."""
    assert state.setdefault('processGroup', process.pid) == process.pid
    if state.get('absence') is not None:
        return state['absence']
    observation = {'atUTC': now(), 'processGroup': process.pid, 'signal': 0}
    try:
        os.killpg(process.pid, 0)
        observation['status'] = 'PRESENT'
    except OSError as error:
        observation.update(errno=error.errno, error=str(error))
        observation['status'] = 'ABSENT_ESRCH' if error.errno == errno.ESRCH else 'UNKNOWN_ERROR'
        if error.errno == errno.ESRCH:
            state['absence'] = observation
    state.setdefault('observations', []).append(observation)
    return observation


def drain_owned_process(process, state):
    """Resolve only this newly created session, including surviving children."""
    result = {'processGroup': process.pid, 'signals': [], 'errors': []}
    try:
        process.poll()  # Reap only this Popen child when it has already exited.
        if state.get('absence') is None:
            try:
                result['initialMembersDiagnosticOnly'] = group_members(process.pid)
            except Exception:
                result['memberDiagnosticFailure'] = traceback.format_exc()
        observation = observe_owned_group(process, state)
        result['terminationRequired'] = observation['status'] == 'PRESENT' or process.returncode is None
        for sig, allowance in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            if state.get('absence') is not None:
                break
            assert observation['status'] == 'PRESENT', 'Owned group observation is unknown; absence is not established'
            try:
                os.killpg(process.pid, sig)
                result['signals'].append(sig.name)
            except OSError as error:
                if error.errno != errno.ESRCH:
                    raise
                # An intervening exit retires this group ID immediately. Do not
                # probe it again to manufacture a signal-zero proof after reuse
                # could become possible. This race remains a failed strict proof.
                observation = {'atUTC': now(), 'processGroup': process.pid,
                    'signal': int(sig), 'errno': error.errno, 'status': 'ABSENT_DURING_SIGNAL_WITHOUT_ZERO_PROOF'}
                state['absence'] = observation
                state.setdefault('observations', []).append(observation)
                break
            end = time.monotonic() + allowance
            while time.monotonic() < end:
                try:
                    process.wait(timeout=0.1)
                except subprocess.TimeoutExpired:
                    pass
                observation = observe_owned_group(process, state)
                if state.get('absence') is not None:
                    break
                assert observation['status'] == 'PRESENT', 'Owned group observation is unknown; absence is not established'
                if process.poll() is not None:
                    time.sleep(0.1)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            result['errors'].append('Owned Popen child did not reap within the final one-second bound')
        result['processExit'] = process.poll()
        absence = state.get('absence')
        result['status'] = ('PASS_OWNED_GROUP_ABSENT'
            if absence is not None and absence['status'] == 'ABSENT_ESRCH'
            and absence['signal'] == 0 and process.returncode is not None
            else 'FAIL_OWNED_GROUP_ABSENCE_NOT_PROVEN')
    except BaseException:
        result['errors'].append(traceback.format_exc())
        result['status'] = 'FAIL_OWNED_GROUP_CLEANUP'
    result['absenceEvidence'] = state.get('absence')
    result['groupObservations'] = list(state.get('observations', []))
    result['historicalGroupReprobed'] = False
    return result


def finish_owned_process(process, state, receipt):
    """Preserve the original failure while resolving this owned process once."""
    if state.get('absence') is not None and state['absence']['status'] == 'ABSENT_ESRCH' and process.poll() is not None:
        receipt['ownedCleanup'] = {'status': 'PASS_OWNED_GROUP_ABSENT',
            'processGroup': process.pid, 'absenceEvidence': state['absence'],
            'historicalGroupReprobed': False}
    else:
        receipt['ownedCleanup'] = drain_owned_process(process, state)
        if receipt['ownedCleanup']['status'] != 'PASS_OWNED_GROUP_ABSENT' or receipt['ownedCleanup'].get('terminationRequired'):
            receipt['status'] = 'FAIL'
    receipt['processExit'] = process.poll()
