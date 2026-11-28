"""Bounded Linux command ownership for the two isolated Swift successors.

The leader remains an unreaped child until all other members of its newly
created process group have gone. Its PID therefore cannot be recycled while a
residual compiler group is being signalled. Positive group absence is latched;
that historical numeric ID is never probed or signalled again.
"""
import os
import signal
import subprocess
import time
from pathlib import Path

STOP_SIGNALS = {signal.SIGTERM, signal.SIGINT}


def install_interrupt_handlers():
    def interrupted(number, _frame):
        raise RuntimeError('owned Swift controller interrupted by signal '+str(number))
    for number in STOP_SIGNALS:
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, STOP_SIGNALS)


def ignore_interrupts():
    previous = {number:signal.getsignal(number) for number in STOP_SIGNALS}
    for number in STOP_SIGNALS:
        signal.signal(number, signal.SIG_IGN)
    return previous


def child_signals():
    for number in STOP_SIGNALS:
        signal.signal(number, signal.SIG_DFL)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, STOP_SIGNALS)


def other_group_members(pgid):
    """Bounded PID/session census; never retain command lines or process names."""
    members = []
    began = time.monotonic()
    count = 0
    for directory in Path('/proc').iterdir():
        if not directory.name.isdecimal() or int(directory.name) == pgid:
            continue
        count += 1
        if count > 200000 or time.monotonic()-began > 5:
            raise RuntimeError('bounded owned process-group census exceeded')
        try:
            with (directory/'stat').open('rb') as stream:
                raw = stream.read(8193)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if len(raw) > 8192:
            raise RuntimeError('bounded process identity record exceeded')
        closing = raw.rfind(b') ')
        if closing < 0:
            raise RuntimeError('malformed process identity record')
        fields = raw[closing+2:].split()
        if len(fields) < 20:
            raise RuntimeError('short process identity record')
        if int(fields[2]) == pgid:
            if int(fields[3]) != pgid:
                raise RuntimeError('owned group session identity changed')
            members.append(int(directory.name))
    return members


def run(folder, argv, cwd, env, timeout, observe, save, digest, ledger, statistics=None):
    """observe returns a stop reason or None; all original gates stay callers'."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    row = {'argv':argv, 'cwd':str(cwd), 'exitCode':None, 'stopReason':None,
           'processGroupAbsent':False, 'forcedCleanup':False, 'signals':[],
           'cleanupErrors':[], 'unreapedLeaderDuringGroupCleanup':True}
    ledger.append(row)
    process = None
    original_error = None
    absent = False
    reaped = False
    clean_handlers = None

    def remember(error):
        nonlocal original_error
        if original_error is None:
            original_error = error
            row['originalError'] = {'type':type(error).__name__, 'message':str(error)}

    def leader_exit():
        if process is None or reaped:
            raise RuntimeError('leader identity no longer eligible for group cleanup')
        return os.waitid(os.P_PID, process.pid, os.WEXITED|os.WNOHANG|os.WNOWAIT)

    def group_absent():
        nonlocal absent
        if absent:
            return True
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            absent = True
            row['absenceObservedAtSeconds'] = time.monotonic()-started
        return absent

    def send_owned(number):
        if absent:
            return
        if reaped:
            raise RuntimeError('refuse signalling after leader was reaped')
        # waitid also proves this is still our unreaped child, even if it has
        # exited. A PID belonging to another process can never satisfy it.
        leader_exit()
        if group_absent():
            return
        if os.getpgid(process.pid) != process.pid or os.getsid(process.pid) != process.pid:
            raise RuntimeError('owned leader group/session changed')
        try:
            os.killpg(process.pid, number)
            row['signals'].append(int(number))
        except ProcessLookupError:
            group_absent()

    def drain_unreaped(seconds):
        deadline = time.monotonic()+seconds
        while True:
            exited = leader_exit()
            members = other_group_members(process.pid)
            if exited is not None and not members:
                return True
            if time.monotonic() >= deadline:
                row['unresolvedOtherGroupMembers'] = members
                return False
            time.sleep(.05)

    try:
        reason = observe()
        if reason is not None:
            row['stopReason'] = reason
            raise RuntimeError(reason)
        with (folder/'original.log').open('xb') as output:
            # Do not let an asynchronous controller signal land between a
            # successful fork and retaining its Popen handle. The child resets
            # and unblocks these signals before exec, including inherited masks.
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
            try:
                process = subprocess.Popen(argv, cwd=cwd, env=env,
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                    start_new_session=True, preexec_fn=child_signals)
                row.update(pid=process.pid, pgid=process.pid)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            save(folder/'started.json', {'pid':process.pid, 'argv':argv, 'cwd':str(cwd), 'at':time.time()})
            while True:
                reason = observe()
                if reason is None and time.monotonic()-started > timeout:
                    reason = 'timeout'
                if reason is not None:
                    row['stopReason'] = reason
                    raise RuntimeError(reason)
                if leader_exit() is not None:
                    members = other_group_members(process.pid)
                    if members:
                        row['residualMembersAfterLeaderExit'] = members
                        raise RuntimeError('owned descendants outlived command leader')
                    break
                time.sleep(.2)
    except BaseException as error:
        remember(error)
    finally:
        clean_handlers = ignore_interrupts()
        if process is not None:
            try:
                if original_error is not None or leader_exit() is None or other_group_members(process.pid):
                    row['forcedCleanup'] = True
                    send_owned(signal.SIGTERM)
                    if not drain_unreaped(5):
                        send_owned(signal.SIGKILL)
                        if not drain_unreaped(5):
                            raise RuntimeError('owned command group remained unresolved after bounded cleanup')
                # Only now may the leader PID be reused. Never signal it again,
                # whether the following positive absence succeeds or fails.
                row['exitCode'] = process.wait(timeout=2)
                reaped = True
                row['processGroupAbsent'] = group_absent()
                if not row['processGroupAbsent']:
                    raise RuntimeError('owned group absence was not positively proved')
            except BaseException as error:
                row['cleanupErrors'].append({'type':type(error).__name__, 'message':str(error)})
                remember(error)
                if not reaped and not absent:
                    try:
                        send_owned(signal.SIGKILL)
                        if not drain_unreaped(5):
                            raise RuntimeError('final owned cleanup remained unresolved')
                        row['exitCode'] = process.wait(timeout=2)
                        reaped = True
                        row['processGroupAbsent'] = group_absent()
                    except BaseException as final_error:
                        row['cleanupErrors'].append({'type':type(final_error).__name__, 'message':str(final_error)})
        row['seconds'] = time.monotonic()-started
        try:
            reason = observe()
            if reason is not None:
                if row['stopReason'] is None:
                    row['stopReason'] = reason
                remember(RuntimeError(reason))
            if statistics is not None:
                row.update(statistics)
            if (folder/'original.log').is_file():
                row['logSHA256'] = digest(folder/'original.log')
            save(folder/'result.json', row)
        except BaseException as error:
            row['retentionError'] = {'type':type(error).__name__, 'message':str(error)}
            remember(error)
        if original_error is None:
            for number, handler in clean_handlers.items():
                signal.signal(number, handler)
    if original_error is not None:
        raise original_error
    if row['exitCode'] != 0 or not row['processGroupAbsent'] or row['forcedCleanup']:
        raise RuntimeError('owned command did not finish normally: '+folder.name)
    return folder/'original.log', row
