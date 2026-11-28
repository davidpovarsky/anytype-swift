"""Controller-only lifetime and whole-request deadline provenance.

No product, account, or compiled fixture is modified by this module. The native
owner successor changes only the explicit expected-exit predicate for the one
already-authorized SIGKILL phase; the original f9de cleanup remains intact.
"""
from contextlib import contextmanager
import ast
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time
import types

HERE = Path(__file__).absolute().parent
OWNER_SHA = 'c2e2c23d497d334431462cd5ee530aaa3b9e9b2cf160201fe0443c27672c5145'
ORIGINAL_OWNER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
TIMER_SOURCE_SHA = '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84'
TIMER_FUNCTION_SHA = 'b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81'
LIFECYCLE = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
DEADLINE = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127/attempt1/result.json')
DEADLINE_SHA = '0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6'
_save_serial = 0


def require(value, label):
    if not value:
        raise RuntimeError(label)


def frozen(path, maximum=1024**2):
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'physical controller input')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'bounded regular controller input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno()) == before, 'controller input identity changed before read')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno()) == before, 'controller input changed during read')
    require(path.lstat() == before and len(raw) == before.st_size, 'controller input changed after read')
    return raw


def write(path, value):
    """Retain a previous complete receipt if interrupted during a later save."""
    global _save_serial
    _save_serial += 1
    temporary = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(_save_serial))
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def decorated_function(raw, name):
    nodes = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, 'one original deadline function')
    node = nodes[0]
    first = min([node.lineno]+[decorator.lineno for decorator in node.decorator_list])
    return b''.join(raw.splitlines(keepends=True)[first-1:node.end_lineno])


def owner_successor(original):
    """The complete declared delta; every other byte remains original f9de."""
    changes = [
        ('def run(folder, argv, cwd, env, timeout, observe, save, digest, ledger, statistics=None):',
         'def run(folder, argv, cwd, env, timeout, observe, save, digest, ledger, statistics=None, expected_exit=0):'),
        ('    folder = Path(folder)',
         "    if expected_exit not in (0, -signal.SIGKILL):\n        raise RuntimeError('only normal exit or an explicitly gated native SIGKILL is supported')\n    folder = Path(folder)"),
        ("           'cleanupErrors':[], 'unreapedLeaderDuringGroupCleanup':True}",
         "           'cleanupErrors':[], 'unreapedLeaderDuringGroupCleanup':True, 'expectedExitCode':expected_exit}"),
        ("    if row['exitCode'] != 0 or not row['processGroupAbsent'] or row['forcedCleanup']:",
         "    if expected_exit == -signal.SIGKILL and (row.get('intentionalCrashGateValidated') is not True or\n            row.get('intentionalCrashSignal') != int(signal.SIGKILL)):\n        raise RuntimeError('an expected SIGKILL requires the exact native mutation gate')\n    if row['exitCode'] != expected_exit or not row['processGroupAbsent'] or row['forcedCleanup']:")]
    text = original.decode('utf-8')
    for before, after in changes:
        require(text.count(before) == 1, 'one exact owner delta location')
        text = text.replace(before, after, 1)
    return text.encode('utf-8')


def qualify():
    require(not sys.flags.optimize, 'all qualification guards must remain enabled')
    expected = {
        HERE/'owned_native_commands.py':OWNER_SHA,
        HERE/'owned_swift_commands_original.py':ORIGINAL_OWNER_SHA,
        HERE/'absolute_http_source_original.py':TIMER_SOURCE_SHA,
        LIFECYCLE:LIFECYCLE_SHA, DEADLINE:DEADLINE_SHA}
    raw = {}
    inputs = {}
    for path, digest in expected.items():
        raw[path] = frozen(path)
        require(hashlib.sha256(raw[path]).hexdigest() == digest, 'exact original controller/proof pin')
        inputs[str(path)] = {'bytes':len(raw[path]), 'sha256':digest}
    require(owner_successor(raw[HERE/'owned_swift_commands_original.py']) == raw[HERE/'owned_native_commands.py'],
            'native owner must differ only in its explicit expected-exit predicate')
    original_timer = decorated_function(raw[HERE/'absolute_http_source_original.py'], 'absolute_http_deadline')
    own_timer = decorated_function(frozen(Path(__file__).absolute()), 'absolute_http_deadline')
    require(len(original_timer) == 1745 and hashlib.sha256(original_timer).hexdigest() == TIMER_FUNCTION_SHA and
            own_timer == original_timer, 'byte-identical actually qualified whole-request deadline')
    lifecycle = json.loads(raw[LIFECYCLE])
    require(lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and
            lifecycle['helperSHA256'] == ORIGINAL_OWNER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'] and
            len(lifecycle['methods']) == 5 and all(row['status'] == 'PASS' for row in lifecycle['methods']),
            'five actual original unreaped-owner controls')
    deadline = json.loads(raw[DEADLINE])
    require(deadline['status'] == 'PASS_TWO_ACTUAL_HTTP_DEADLINES_AND_OWNED_CLOSURE' and
            deadline['allOwnedGroupsPositivelyAbsent'] and
            deadline['actualControls']['controllerSHA256'] == TIMER_SOURCE_SHA and
            deadline['actualControls']['actualMethods'] == {'errors':0, 'failures':0, 'runs':2, 'skips':0},
            'two actual complete-header/body deadline controls')
    owner = types.ModuleType('qualified_native_expected_exit_owner')
    owner.__file__ = str(HERE/'owned_native_commands.py')
    exec(compile(raw[HERE/'owned_native_commands.py'], owner.__file__, 'exec'), owner.__dict__)
    return owner, {'inputFiles':inputs, 'originalOwnerSHA256':ORIGINAL_OWNER_SHA,
        'ownerSuccessorSHA256':OWNER_SHA, 'ownerDelta':'explicit expected exit 0 or gated -SIGKILL only',
        'originalLifecycleReceiptSHA256':LIFECYCLE_SHA, 'originalDeadlineReceiptSHA256':DEADLINE_SHA,
        'deadlineFunctionSHA256':TIMER_FUNCTION_SHA, 'priorControlsReexecuted':0,
        'expectedCrashExtensionPreviouslyExecuted':False,
        'completeConnectHeadersBodyAndCloseBounded':True}


def recheck(admission):
    for path, expected in admission['inputFiles'].items():
        raw = frozen(Path(path))
        require(len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256'],
                'original deadline/ownership input changed')


# The exact decorated original function is appended below. Its bytes are
# independently joined to original26ed and the accepted two-control receipt.

@contextmanager
def absolute_http_deadline(seconds):
    """A complete GET must finish even if a peer trickles header/body bytes.

    Native commands have already been spawned before this main-thread scope;
    no child launch happens while its process-wide timer is active. Preserve
    the caller's handler/mask, refuse a pre-existing timer, and consume only a
    pending alarm from this owned timer before restoring the previous handler.
    """
    handoff_signals = {signal.SIGALRM, signal.SIGTERM, signal.SIGINT}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, handoff_signals)
    previous_handler = signal.getsignal(signal.SIGALRM)
    deadline = time.monotonic()+seconds
    timer_owned = False

    def expired(_number, _frame):
        raise TimeoutError('absolute HTTP request deadline')

    try:
        require(signal.getitimer(signal.ITIMER_REAL)==(0.0, 0.0), 'an existing timer prevents HTTP deadline ownership')
        require(signal.SIGALRM not in signal.sigpending(), 'an existing alarm is pending')
        signal.signal(signal.SIGALRM, expired)
        timer_owned = True
        signal.setitimer(signal.ITIMER_REAL, seconds)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask-{signal.SIGALRM})
        yield
        require(time.monotonic()<=deadline, 'absolute HTTP deadline expired at completion')
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, handoff_signals)
        if timer_owned:
            signal.setitimer(signal.ITIMER_REAL, 0)
            if signal.SIGALRM in signal.sigpending():
                signal.sigtimedwait({signal.SIGALRM}, 0)
            signal.signal(signal.SIGALRM, previous_handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
