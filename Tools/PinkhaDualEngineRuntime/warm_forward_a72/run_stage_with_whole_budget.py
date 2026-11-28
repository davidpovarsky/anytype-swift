#!/usr/bin/env python3.12
"""Run exactly one admitted original forward stager in this process.

The active alarm is delivered once and raises through the original stager's
BaseException/73bb cleanup. It is not rearmed inside that cleanup. The distinct
foreground SSH owner supplies the 3300-second whole-operation transport bound;
its Oracle launcher must allow the original owned cleanup within 3600 seconds.
No original function, per-command ceiling, signal handler or source is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time

sys.dont_write_bytecode = True
CONTROL_ROOT = Path('/Users/m1/builds/pinkha-warm-forward-bae-binding-20261128-1')
STAGE = CONTROL_ROOT / 'controls/stage_wave3_forward_warm.py'
STAGE_SHA = '38644915911ae3df8fa9d7d446a7ca1e9d1bc57fd95d5f0542dd35fd3413083a'
STAGE_BYTES = 32456
STAGE_PLAN = CONTROL_ROOT / 'stage-admission1/source-staging.authorized.json'
STAGE_PLAN_SHA = None
STAGE_PLAN_BYTES = None
WINDOW = CONTROL_ROOT / 'stage-admission1/root-window.json'
WINDOW_SHA = None
WINDOW_BYTES = None
SUPPLEMENT = CONTROL_ROOT / 'stage-admission1/stage-total-budget-supplement.json'
SUPPLEMENT_SHA = None
SUPPLEMENT_BYTES = None
SOURCE = 'bae68131a20fd7ef351c2b4034ebdf520c6d3b39'
BUILD_ROOT = Path('/Users/m1/development/anytype-d-active-20261125/main16-wave3-forward-bae68131a20f')
OUTPUT = CONTROL_ROOT / 'stage-admission1/whole-stage-budget-run1'
ACTIVE_SECONDS, WHOLE_SECONDS, OUTER_SECONDS = 3000, 3300, 3600
MIB = 1024 ** 2


def require(value, message):
    if not value:
        raise ValueError(message)


def error(exc):
    return {'type': type(exc).__name__, 'message': str(exc)}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def read_exact(path, expected=None, maximum=MIB):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and all(not item.is_symlink() for item in (path, *path.parents)),
            'Exact physical source/control path required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 501
                and before.st_nlink == 1 and before.st_size <= maximum,
                'Bounded original UID501 regular file required')
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    final = path.stat()
    keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    require(all(getattr(before, key) == getattr(after, key) == getattr(final, key) for key in keys)
            and len(raw) == before.st_size, 'Original input changed during read')
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or digest == expected, 'Exact original source/control hash differs')
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': digest}


def write_terminal(record):
    raw = encoded(record)
    require(len(raw) <= 64 * 1024, 'Finite wrapper receipt envelope exceeded')
    path = OUTPUT / 'receipt.json'
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    actual, ref = read_exact(path, hashlib.sha256(raw).hexdigest())
    require(actual == raw, 'Actual terminal receipt readback differs')
    fd = os.open(OUTPUT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return ref


def read_original_success():
    """Read current-invocation terminal files only; never probe a PID/group."""
    stage_root = BUILD_ROOT / 'source-staging1'
    raw, stage_ref = read_exact(stage_root / 'receipt.json', maximum=16 * MIB)
    stage = json.loads(raw)
    require(stage['status'] == 'PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED'
            and stage['sourceCommit'] == SOURCE and stage['controllerSHA256'] == STAGE_SHA
            and stage['planSHA256'] == STAGE_PLAN_SHA and stage['firstFailure'] is None
            and stage['secondaryErrors'] == [] and not stage['processObservationCustodyBlocked'],
            'The actual original successful stage receipt is required')
    phases = {'owners-before', 'owners-before-fetch', 'owners-before-mutation',
              'owners-before-fast-forward', 'owners-before-exact-resolution', 'owners-after'}
    observations = stage['processObservations']
    require(len(observations) == 6 and {row['phase'] for row in observations} == phases,
            'All six actual phase observations are required')
    phase_refs = []
    for row in observations:
        require(row['status'] == 'PASS_COMPLETE_OBSERVATION_AND_PHASE_PREDICATES'
                and row['allKnownGroupsClosed'] is True,
                'An actual phase reports incomplete original custody')
        actual, ref = read_exact(stage_root / (row['phase'] + '.json'), row['receipt']['sha256'], maximum=16 * MIB)
        value = json.loads(actual)
        require(value['status'] == row['status'] and value['allKnownGroupsClosed'] is True
                and value['firstFailure'] is None and value['secondaryErrors'] == [],
                'Original phase terminal differs from its stage reference')
        phase_refs.append(ref)
    command_root = stage_root / 'owned-commands'
    require(command_root.resolve(strict=True) == command_root and not command_root.is_symlink(),
            'Actual original command evidence directory is required')
    command_dirs = sorted(command_root.iterdir())
    require(len(command_dirs) == 26 and all(path.is_dir() and not path.is_symlink() for path in command_dirs),
            'Exact successful original 26-command stage path differs')
    command_refs = []
    for directory in command_dirs:
        raw, ref = read_exact(directory / 'result.json')
        value = json.loads(raw)
        require(value['pid'] == value['pgid'] and type(value['pid']) is int and value['pid'] > 1
                and value['status'] == value['commandStatus'] == 'PASS_COMMAND' and value['exitCode'] == 0
                and value['ownedGroupObservationStatus'] == 'ABSENT_ESRCH'
                and value['ownedGroupPresentAfterExit'] is False
                and value['cleanupErrors'] == [] and value['termination'] == [],
                'The actual original command did not close positively without intervention')
        command_refs.append(ref)
    cache_raw, cache_ref = read_exact(BUILD_ROOT / 'cache-requalification1/receipt.json', maximum=16 * MIB)
    cache = json.loads(cache_raw)
    require(cache['protocol'] == 'pinkha-forward-warm-cache-qualification-v1'
            and cache['sourceCommit'] == SOURCE and cache['stageReceiptSHA256'] == stage_ref['sha256']
            and cache['stageSourceAndNativePreservationRetained'] is True
            and cache['applicationBuilds'] == cache['testsExecuted'] == 0,
            'Original cache qualification must join the actual successful stage')
    build_raw, draft_ref = read_exact(BUILD_ROOT / 'build-admission.draft.json', maximum=MIB)
    draft = json.loads(build_raw)
    require(draft['readyForBuild'] is False and draft['appSourceSHA'] == SOURCE
            and draft['sourceStaging'] == {key: stage_ref[key] for key in ('path', 'sha256')}
            and draft['cacheQualification'] == {key: cache_ref[key] for key in ('path', 'sha256')},
            'Original inactive build draft must join the exact stage and cache receipts')
    return {'stage': stage_ref, 'cache': cache_ref, 'buildDraft': draft_ref,
            'originalCommandResults': command_refs, 'originalPhaseResults': phase_refs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    started_wall, started = time.time(), time.monotonic()
    record = {'schema': 'pinkha-original-warm-stage-whole-budget-receipt-v1', 'status': 'FAIL',
              'startedAt': started_wall, 'activeWorkBudgetSeconds': ACTIVE_SECONDS,
              'foregroundOperationBudgetSeconds': WHOLE_SECONDS, 'outerLauncherMaximumSeconds': OUTER_SECONDS,
              'alarmFired': False, 'firstFailure': None, 'secondaryErrors': [], 'originalExitCode': None,
              'stageInvocationCount': 0, 'wrapperChildProcesses': 0, 'applicationBuilds': 0,
              'nativeBuilds': 0, 'testsExecuted': 0, 'allKnownGroupsClosed': None,
              'runtimeActivation': False, 'readyForBuild': False, 'finalSourceSDKNativeProductTuple': None,
              'originalControlUnmodified': True, 'historicalProcessProbes': 0}
    record['groupClosureScope'] = 'Original 26 stage-owned command results and six current phase-observer results; no foreign/global process claim'
    claimed = False
    receipt = None
    original_error = None
    timer_owned = False
    old_argv = list(sys.argv)
    old_signals = {sig: signal.getsignal(sig) for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}

    def expire(signum, frame):
        # The original owner gets its complete cleanup path. A second timer
        # exception must not cut through its TERM15/KILL5/wait/receipt handling.
        signal.setitimer(signal.ITIMER_REAL, 0)
        record['alarmFired'] = True
        record['alarmAt'] = time.time()
        record['alarmMonotonicElapsedSeconds'] = time.monotonic() - started
        exc = TimeoutError('WHOLE_STAGE_ACTIVE_BUDGET_3000_SECONDS_EXPIRED')
        if record['firstFailure'] is None:
            record['firstFailure'] = error(exc)
        raise exc

    try:
        require(sys.platform == 'darwin' and os.getuid() == os.geteuid() == 501,
                'The actual UID501 Mac source-stage route is required')
        require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
                'An unrelated in-process real timer is already active')
        require(all(isinstance(value, str) and len(value) == 64
                    and all(character in '0123456789abcdef' for character in value)
                    for value in (STAGE_PLAN_SHA, WINDOW_SHA, SUPPLEMENT_SHA))
                and all(type(value) is int and 0 < value <= MIB
                        for value in (STAGE_PLAN_BYTES, WINDOW_BYTES, SUPPLEMENT_BYTES)),
                'This source-only wrapper requires exact root-bound plan/window/supplement literals')
        plan_raw, plan_ref = read_exact(args.plan, args.plan_sha256)
        plan = json.loads(plan_raw)
        own_raw, own_ref = read_exact(Path(__file__).resolve())
        require(plan['schema'] == 'pinkha-original-warm-stage-whole-budget-launch-v1'
                and plan['readyForStaging'] is True and plan['readyForBuild'] is False
                and plan['runtimeActivation'] is False and plan['controller'] == own_ref
                and plan['activeWorkBudgetSeconds'] == ACTIVE_SECONDS
                and plan['foregroundOperationBudgetSeconds'] == WHOLE_SECONDS
                and plan['outerLauncherMaximumSeconds'] == OUTER_SECONDS
                and plan['maximumInvocations'] == 1 and plan['outputRoot'] == str(OUTPUT),
                'Exact one-stage total-budget launch contract required')
        require(plan['stagePlan'] == {'path': str(STAGE_PLAN), 'bytes': STAGE_PLAN_BYTES, 'sha256': STAGE_PLAN_SHA}
                and plan['rootWindow'] == {'path': str(WINDOW), 'bytes': WINDOW_BYTES, 'sha256': WINDOW_SHA}
                and plan['budgetSupplement'] == {'path': str(SUPPLEMENT), 'bytes': SUPPLEMENT_BYTES, 'sha256': SUPPLEMENT_SHA},
                'Original stage/window identity is fixed')
        stage_raw, stage_ref = read_exact(STAGE, STAGE_SHA)
        require(len(stage_raw) == STAGE_BYTES, 'Exact original stager length differs')
        stage_plan_raw, _ = read_exact(STAGE_PLAN, STAGE_PLAN_SHA)
        window_raw, _ = read_exact(WINDOW, WINDOW_SHA)
        supplement_raw, supplement_ref = read_exact(SUPPLEMENT, SUPPLEMENT_SHA)
        stage_plan, window = json.loads(stage_plan_raw), json.loads(window_raw)
        require(stage_plan['readyForStaging'] is True and stage_plan['appSourceSHA'] == SOURCE
                and stage_plan['buildRoot'] == str(BUILD_ROOT)
                and stage_plan['runtimeActivation'] is False
                and window['maximumInvocations'] == 1 and window['readyForBuild'] is False,
                'This wrapper cannot admit another source/role or compiler')
        require(OUTPUT.parent.resolve(strict=True) == OUTPUT.parent
                and all(not item.is_symlink() for item in (OUTPUT, *OUTPUT.parents))
                and not OUTPUT.exists(), 'Fresh exact wrapper evidence root required')
        OUTPUT.mkdir(mode=0o700)
        claimed = True
        record.update(plan=plan_ref, controller=own_ref, originalStageController=stage_ref,
                      sourceCommit=SOURCE, buildRoot=str(BUILD_ROOT), outputRoot=str(OUTPUT),
                      budgetSupplement=supplement_ref)
        sys.argv = [str(STAGE), '--plan', str(STAGE_PLAN), '--plan-sha256', STAGE_PLAN_SHA,
                    '--accepted-source', SOURCE]
        record['stageArgv'] = list(sys.argv)
        record['stageInvocationCount'] = 1
        signal.signal(signal.SIGALRM, expire)
        timer_owned = True
        remaining = ACTIVE_SECONDS - (time.monotonic() - started)
        require(remaining > 0, 'The whole active-stage budget expired during file admission')
        signal.setitimer(signal.ITIMER_REAL, remaining)
        namespace = {'__name__': '__main__', '__file__': str(STAGE), '__package__': None,
                     '__spec__': None, '__builtins__': __builtins__}
        try:
            # Exact already-read bytes, not another import/reopen or exec(2).
            # The original __main__ installs its unchanged TERM/INT handlers.
            exec(compile(stage_raw, str(STAGE), 'exec'), namespace)
            record['originalExitCode'] = 0
        except SystemExit as exc:
            record['originalExitCode'] = exc.code if type(exc.code) is int else (0 if exc.code is None else 1)
            if record['originalExitCode'] != 0:
                original_error = error(exc)
        except BaseException as exc:
            original_error = error(exc)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        record['originalRaisedException'] = original_error
        record['originalReturnedAfterSeconds'] = time.monotonic() - started
        if original_error is not None and record['firstFailure'] is None:
            record['firstFailure'] = original_error
        require(record['originalExitCode'] == 0 and record['firstFailure'] is None
                and not record['alarmFired'] and record['originalReturnedAfterSeconds'] <= ACTIVE_SECONDS,
                'The original stage did not complete successfully within its active whole-operation budget')
        require(read_exact(STAGE, STAGE_SHA)[0] == stage_raw
                and read_exact(STAGE_PLAN, STAGE_PLAN_SHA)[0] == stage_plan_raw
                and read_exact(WINDOW, WINDOW_SHA)[0] == window_raw
                and read_exact(SUPPLEMENT, SUPPLEMENT_SHA)[0] == supplement_raw,
                'Original stage/control bytes changed during the one invocation')
        record['originalTerminalEvidence'] = read_original_success()
        record['allKnownGroupsClosed'] = True
        record['status'] = 'PASS_ORIGINAL_FORWARD_STAGE_WITHIN_WHOLE_BUDGET'
    except BaseException as exc:
        if record['firstFailure'] is None:
            record['firstFailure'] = error(exc)
        elif record['firstFailure'] != error(exc):
            record['secondaryErrors'].append({'phase': 'wrapper-boundary', **error(exc)})
        record['status'] = 'FAIL'
    finally:
        if timer_owned:
            signal.setitimer(signal.ITIMER_REAL, 0)
        sys.argv = old_argv
        for sig, handler in old_signals.items():
            signal.signal(sig, handler)
        record['finishedAt'] = time.time()
        record['elapsedSeconds'] = time.monotonic() - started
        record['withinWholeOperationBudget'] = record['elapsedSeconds'] <= WHOLE_SECONDS
        if not record['withinWholeOperationBudget']:
            late = {'type': 'WholeStageOperationBudgetExceeded', 'message': 'The 3300-second operation envelope did not close'}
            if record['firstFailure'] is None:
                record['firstFailure'] = late
            else:
                record['secondaryErrors'].append(late)
            record['status'] = 'FAIL'
        if claimed:
            try:
                receipt = write_terminal(record)
            except BaseException as exc:
                if record['firstFailure'] is None:
                    record['firstFailure'] = error(exc)
                else:
                    record['secondaryErrors'].append({'phase': 'terminal-receipt', **error(exc)})
                record['status'] = 'FAIL'
        print('PINKHA_WARM_STAGE_BUDGET_RESULT_V1 ' + json.dumps({
            'status': record['status'], 'receipt': receipt, 'firstFailure': record['firstFailure'],
            'secondaryErrors': record['secondaryErrors'], 'elapsedSeconds': record['elapsedSeconds'],
            'allKnownGroupsClosed': record['allKnownGroupsClosed'],
            'readyForBuild': False, 'runtimeActivation': False}, sort_keys=True), flush=True)
    return 0 if record['status'] == 'PASS_ORIGINAL_FORWARD_STAGE_WITHIN_WHOLE_BUDGET' else 1


if __name__ == '__main__':
    raise SystemExit(main())
