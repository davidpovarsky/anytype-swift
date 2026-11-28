#!/usr/bin/env python3.12
"""Run the exact root-bound warm App/Stage1 producer in the current process.

Original29b/d77 generation remains an immutable, fully reversible input. A
separate finite projection owns only direct commands and run_phase cleanup.
The one active-work alarm is never rearmed during cleanup. The existing outer
foreground owner retains its 3300/3600-second operation/launcher envelopes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

sys.dont_write_bytecode = True
CONTROL_ROOT = Path('/Users/m1/builds/pinkha-warm-forward-bae-binding-20261128-1')
SOURCE_ROOT = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
APP_DERIVED = SOURCE_ROOT.parent / 'app-derived'
OUTPUT = None
ACTIVE_SECONDS, WHOLE_SECONDS, OUTER_SECONDS = 3000, 3300, 3600
MIB = 1024 ** 2
REQUIRED_ADMISSION_BYTES = 9126805504
ORIGINALS = {
    'warm': ('wave3_forward_warm.py', 30106, '181b5f3ca42943e1dc8179d16a98d63998f966212920e63c3c8a5317e98b4d75'),
    'producer': ('build_wave2_app16_compiler_qualified.py', 18767, '9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c'),
    'adapter': ('wave3_shared_build.py', 23103, '47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd'),
    'lifecycle': ('combined_heart_semantics_owned_outcomes.py', 63344, '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a'),
    'observation': ('phase_observation.py', 21626, '75dfe996edc8ffd5eece2efbd6a64238e221a0d4b9e885edaf47d9cebe043826'),
}
CUSTODY_SHA = 'e7e630f78b3abdd1a86b7c5376c39351fa4fd01d48ecb2380137aac20cecfd6d'
CUSTODY_BYTES = 19641

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


def read_ref(row, maximum=MIB):
    require(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int
            and 0 <= row['bytes'] <= maximum and re.fullmatch('[0-9a-f]{64}', row['sha256'] or ''),
            'An exact bounded file reference is required')
    raw, actual = read_exact(row['path'], row['sha256'], maximum)
    require(actual == row, 'Full original file identity differs')
    return raw


def write_new(path, raw):
    path = Path(path)
    require(path.parent.resolve(strict=True) == path.parent and not path.exists()
            and all(not item.is_symlink() for item in (path, *path.parents)),
            'Fresh owned source/evidence output required')
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    actual, ref = read_exact(path, hashlib.sha256(raw).hexdigest(), maximum=16 * MIB)
    require(actual == raw, 'Owned output readback differs')
    return ref


def load_original(raw, path, name):
    # Exact bytes, with the original __main__ branch inactive. No on-disk
    # replacement, global module patch, helper process, or source alias.
    namespace = {'__name__': name, '__file__': str(path), '__package__': None,
                 '__spec__': None, '__builtins__': __builtins__}
    exec(compile(raw, str(path), 'exec'), namespace)
    return namespace


def project_producer(expanded, base):
    """Four finite edits; inverse restores the entire original generated text."""
    require(hashlib.sha256(base.encode()).hexdigest() == ORIGINALS['producer'][2],
            'Original 204f producer bytes differ')
    original = next(node for node in ast.parse(base).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'run_phase')
    old_phase = ast.get_source_segment(base, original)
    observed = next(node for node in ast.parse(expanded).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'run_phase')
    require(ast.get_source_segment(expanded, observed) == old_phase,
            'Original generated run_phase must remain byte exact before projection')
    new_phase = ('def run_phase(name,argv,timeout=7200):\n'
                 ' return FOREGROUND_COMMANDS.run_phase(globals(),name,argv,timeout)')
    import_line = base.splitlines(keepends=True)[0]
    changes = [
        (import_line, import_line + 'subprocess=FOREGROUND_COMMANDS\n'),
        (old_phase, new_phase),
        ('except BaseException as exc:\n EVIDENCE.mkdir(exist_ok=True)',
         'except BaseException as exc:\n FOREGROUND_COMMANDS.absorb_observer()\n'
         ' FOREGROUND_COMMANDS.fail(exc,"original-producer-fatal")\n EVIDENCE.mkdir(exist_ok=True)'),
        (' if not globals().get("WR_PHASE_OBSERVATION_STATE", {}).get("commandCustodyBlocked", False):\n'
         '  try:write(EVIDENCE/"source-after.json",source_state())\n  except BaseException:pass\n',
         ' # Fatal preservation is file-only; no later Git, child or device operation.\n'),
    ]
    result, positions = expanded, []
    for old, new in changes:
        require(result.count(old) == 1, 'Exact foreground projection seam differs')
        offset = result.index(old)
        result = result[:offset] + new + result[offset + len(old):]
        positions.append({'offset': offset, 'old': old, 'new': new})
    inverse = result
    for item in reversed(positions):
        at, old, new = item['offset'], item['old'], item['new']
        require(inverse[at:at + len(new)] == new, 'Whole foreground inverse offset differs')
        inverse = inverse[:at] + old + inverse[at + len(new):]
    require(inverse == expanded, 'Foreground inverse must restore every original generated byte')
    old_nodes = {node.name: ast.get_source_segment(expanded, node) for node in ast.parse(expanded).body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    new_nodes = {node.name: ast.get_source_segment(result, node) for node in ast.parse(result).body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    require(set(old_nodes) == set(new_nodes) and
            all(old_nodes[name] == new_nodes[name] for name in old_nodes if name != 'run_phase'),
            'Only run_phase may change among original generated declarations')
    return result, {'schema': 'pinkha-warm-producer-foreground-full-inverse-v1',
                    'expandedSHA256': hashlib.sha256(expanded.encode()).hexdigest(),
                    'derivedSHA256': hashlib.sha256(result.encode()).hexdigest(),
                    'changes': positions, 'wholeInverseRestoresEveryExpandedByte': True,
                    'changedDeclaration': 'run_phase',
                    'unchangedDeclarations': sorted(name for name in old_nodes if name != 'run_phase'),
                    'subprocessScope': 'This generated producer namespace only',
                    'applicationBuilds': 0, 'testsExecuted': 0}



def read_log_identity(path, expected_sha, expected_bytes):
    """Stream actual compiler logs; never load a whole log into wrapper memory."""
    path = Path(path)
    require(type(expected_bytes) is int and expected_bytes >= 0
            and re.fullmatch('[0-9a-f]{64}', expected_sha or '')
            and path.resolve(strict=True) == path
            and all(not item.is_symlink() for item in (path, *path.parents)),
            'Exact physical original compiler log required')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_uid == 501
                and before.st_nlink == 1 and before.st_size == expected_bytes,
                'Actual compiler log size or ownership differs')
        digest_value = hashlib.sha256()
        total = 0
        while True:
            block = stream.read(min(MIB, expected_bytes - total + 1))
            if not block:
                break
            total += len(block)
            require(total <= expected_bytes, 'Compiler log grew during final readback')
            digest_value.update(block)
        after = os.fstat(stream.fileno())
    final = path.stat()
    keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    require(all(getattr(before, key) == getattr(after, key) == getattr(final, key) for key in keys)
            and total == expected_bytes and digest_value.hexdigest() == expected_sha,
            'Actual original compiler log changed during streaming readback')
    return {'path': str(path), 'bytes': total, 'sha256': digest_value.hexdigest()}


def read_original_success(data, namespace, derived_ref, admission_ref):
    """Qualify the current producer's actual files; never query a PID or device."""
    evidence = Path(data['buildRoot']) / 'build16'
    raw, receipt_ref = read_exact(evidence / 'receipt.json', maximum=16 * MIB)
    receipt = json.loads(raw)
    require(receipt['status'] == 'PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE'
            and receipt['sourceCommit'] == data['appSourceSHA'] and receipt['testsExecuted'] == 0
            and receipt['sourceUnchanged'] is True and receipt['controllerSHA256'] == derived_ref['sha256'],
            'Actual current App and complete Stage1 UI producer success is required')
    control = receipt['controlAdmission']
    require(control['admission'] == {'path': admission_ref['path'], 'sha256': admission_ref['sha256']}
            and control['adapterSHA256'] == ORIGINALS['warm'][2]
            and control['originalProducerSHA256'] == ORIGINALS['producer'][2],
            'Actual original producer/admission ancestry differs')
    phases = []
    for name in ('app', 'ui'):
        phase_raw, phase_ref = read_exact(evidence / name / 'result.json', maximum=MIB)
        phase = json.loads(phase_raw)
        require(phase == receipt[name] and phase['status'] == 'PASS_BUILD_EXIT_0'
                and phase['exitCode'] == 0 and phase['ownedProcessGroup'] == 'ABSENT_ESRCH'
                and phase['cleanupErrors'] == [] and phase['termination'] == []
                and phase['firstFailure'] is None and phase['jobs'] == 4 and phase['timeoutSeconds'] == 7200,
                'Actual App/UI phase did not positively close with its original bounds')
        read_log_identity(evidence / name / 'original.log', phase['logSHA256'], phase['logBytes'])
        read_exact(evidence / name / 'process-exit.json', phase['processExitReceiptSHA256'], maximum=MIB)
        phases.append(phase_ref)
    proofs = []
    for kind, name, count, key in (
            ('nativeCompilationProof', 'native-selected-compiler-inputs.json', 62, 'selectedNativeTestSources'),
            ('uiCompilationProof', 'ui-compiled-inputs.json', 10, 'selectedUITestSources')):
        ref = receipt[kind]
        require(ref['path'] == str(evidence / name), 'Actual compiler proof path differs')
        proof_raw, proof_ref = read_exact(ref['path'], ref['sha256'], maximum=16 * MIB)
        proof = json.loads(proof_raw)
        paths = [row['repositoryPath'] for row in proof['requiredSources']]
        require(proof['sourceCommit'] == data['appSourceSHA'] and proof['testsExecuted'] == 0
                and len(paths) == count and len(paths) == len(set(paths)) and set(paths) == set(data[key])
                and proof['actualCompilerFileLists'],
                'Actual complete source62/Stage1UI10 compiler witness differs')
        proofs.append(proof_ref)
    before, before_ref = read_exact(evidence / 'source-before.json', receipt['sourceBeforeSHA256'], maximum=16 * MIB)
    after, after_ref = read_exact(evidence / 'source-after.json', receipt['sourceAfterSHA256'], maximum=16 * MIB)
    require(before == after, 'Actual producer source before/after files differ')
    product = receipt['completeProductsInventory']
    require(product['path'] == str(evidence / 'products-all.json') and product['entries'] > 0,
            'Original complete Products inventory is required')
    _, product_ref = read_exact(product['path'], product['sha256'], maximum=16 * MIB)
    state = namespace.get('WR_PHASE_OBSERVATION_STATE', {})
    require(state.get('firstFailure') is None and not state.get('commandCustodyBlocked')
            and not state.get('processObservationCustodyBlocked'), 'Original observer custody must be closed')
    observations = state.get('processObservations', [])
    require(len(observations) == 2 and {row['phase'] for row in observations} ==
            {'build-cache-writer', 'build-resource'}, 'Both fresh original build observations are required')
    observed_refs = []
    for row in observations:
        require(row['status'] == 'PASS_COMPLETE_OBSERVATION_AND_PHASE_PREDICATES'
                and row['allKnownGroupsClosed'] is True, 'Actual phase observation did not pass and close')
        actual = json.loads(read_ref(row['receipt'], maximum=16 * MIB))
        require(actual['phase'] == row['phase'] and actual['status'] == row['status']
                and actual['allKnownGroupsClosed'] is True and actual['firstFailure'] is None
                and actual['secondaryErrors'] == [], 'Original phase receipt differs from producer state')
        observed_refs.append(row['receipt'])
    return {'producer': receipt_ref, 'phases': phases, 'compilerProofs': proofs,
            'sourceBefore': before_ref, 'sourceAfter': after_ref, 'completeProducts': product_ref,
            'originalPhaseObservations': observed_refs}


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    started_wall, started = time.time(), time.monotonic()
    record = {'schema': 'pinkha-original-warm-build-whole-budget-receipt-v1', 'status': 'FAIL',
              'startedAt': started_wall, 'activeWorkBudgetSeconds': ACTIVE_SECONDS,
              'foregroundOperationBudgetSeconds': WHOLE_SECONDS, 'outerLauncherMaximumSeconds': OUTER_SECONDS,
              'alarmFired': False, 'firstFailure': None, 'secondaryErrors': [],
              'workAdmissionClosed': False, 'commandCustodyBlocked': False,
              'allKnownGroupsClosed': None, 'allDirectProducerGroupsClosed': None,
              'producerInvocationCount': 0, 'wrapperChildProcesses': 0,
              'nativeBuilds': 0, 'testsExecuted': 0, 'runtimeActivation': False,
              'readyForRuntime': False, 'finalSourceSDKNativeProductTuple': None,
              'historicalProcessProbes': 0, 'originalExitCode': None,
              'groupClosureScope': 'Current direct producer children plus two exact75df phase observers only'}
    claimed, timer_owned = False, False
    receipt, owner, namespace = None, None, None
    old_argv = list(sys.argv)
    old_signals = {sig: signal.getsignal(sig) for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
    first_exception = None
    try:
        require(sys.platform == 'darwin' and os.getuid() == os.geteuid() == 501,
                'Actual UID501 Mac warm App route required')
        require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'An unrelated real timer is active')
        plan_raw, plan_ref = read_exact(args.plan, args.plan_sha256)
        plan = json.loads(plan_raw)
        _, own_ref = read_exact(Path(__file__).resolve())
        require(plan['schema'] == 'pinkha-original-warm-build-whole-budget-launch-v1'
                and plan['readyForBuild'] is True and plan['runtimeActivation'] is False
                and plan['readyForRuntime'] is False and plan['controller'] == own_ref
                and plan['activeWorkBudgetSeconds'] == ACTIVE_SECONDS
                and plan['foregroundOperationBudgetSeconds'] == WHOLE_SECONDS
                and plan['outerLauncherMaximumSeconds'] == OUTER_SECONDS
                and plan['maximumInvocations'] == 1 and plan['jobs'] == 4
                and plan['requiredAppAdmissionBytes'] == REQUIRED_ADMISSION_BYTES
                and plan['selectedNativeSourceCount'] == 62 and plan['selectedUISourceCount'] == 10,
                'Exact one-build source62/UI10 original budget contract required')
        source = plan['sourceCommit']
        require(re.fullmatch('[0-9a-f]{40}', source or ''), 'Actual root-bound source commit required')
        window = json.loads(read_ref(plan['rootWindow']))
        require(window['schema'] == 'pinkha-root-warm-app-build-window-v1'
                and window['sourceCommit'] == source and window['readyForBuild'] is True
                and window['runtimeActivation'] is False and window['maximumInvocations'] == 1
                and window['activeWorkBudgetSeconds'] == ACTIVE_SECONDS
                and window['foregroundOperationBudgetSeconds'] == WHOLE_SECONDS
                and window['outerLauncherMaximumSeconds'] == OUTER_SECONDS,
                'Exact current one-build root window required')
        controls, control_refs = {}, {}
        require(set(plan['originalControls']) == set(ORIGINALS), 'Complete exact original control set required')
        for key, (name, size, digest_value) in ORIGINALS.items():
            row = plan['originalControls'][key]
            require(row == {'path': str(CONTROL_ROOT / 'controls' / name), 'bytes': size, 'sha256': digest_value},
                    'Original control path or identity differs: ' + key)
            controls[key] = read_ref(row)
            control_refs[key] = row
        helper_ref = plan['custodyHelper']
        require(helper_ref['sha256'] == CUSTODY_SHA and helper_ref['bytes'] == CUSTODY_BYTES
                and Path(helper_ref['path']).parent == Path(__file__).resolve().parent,
                'Exact adjacent foreground ownership helper required')
        helper_raw = read_ref(helper_ref)
        admission_raw = read_ref(plan['buildAdmission'])
        warm = load_original(controls['warm'], control_refs['warm']['path'], 'original_warm29b')
        adapter = load_original(controls['adapter'], control_refs['adapter']['path'], 'original_d77')
        adapter_object = type('ExactOriginalAdapter', (), {})()
        for key, value in adapter.items():
            if not key.startswith('__'):
                setattr(adapter_object, key, value)
        data = adapter['load_admission'](Path(plan['buildAdmission']['path']),
                                         plan['buildAdmission']['sha256'], source)
        require(json.loads(admission_raw) == data and data['sourceRoot'] == str(SOURCE_ROOT)
                and data['appDerived'] == str(APP_DERIVED)
                and len(data['selectedNativeTestSources']) == 62 and len(data['selectedUITestSources']) == 10,
                'Actual warm producer admission/source membership differs')
        require(data['forwardWarm']['processObservation']['adapter'] == control_refs['observation'],
                'Only the original75df phase observer is permitted')
        lifecycle_copy = Path(data['buildRoot']) / 'source-inputs' / ORIGINALS['lifecycle'][0]
        require(read_exact(lifecycle_copy, ORIGINALS['lifecycle'][2])[0] == controls['lifecycle'],
                'Producer lifecycle copy differs from the retained original73bb')
        OUTPUT = Path(plan['outputRoot'])
        require(OUTPUT.parent == CONTROL_ROOT and re.fullmatch('whole-app-build-[a-z0-9-]+', OUTPUT.name)
                and OUTPUT.parent.resolve(strict=True) == OUTPUT.parent
                and not OUTPUT.exists() and all(not item.is_symlink() for item in (OUTPUT, *OUTPUT.parents)),
                'Fresh concrete root-owned build wrapper directory required')
        OUTPUT.mkdir(mode=0o700)
        claimed = True
        record.update(plan=plan_ref, controller=own_ref, originalControls=control_refs,
                      custodyHelper=helper_ref, rootWindow=plan['rootWindow'], sourceCommit=source,
                      buildRoot=data['buildRoot'], outputRoot=str(OUTPUT), buildAdmission=plan['buildAdmission'],
                      requiredAppAdmissionBytes=REQUIRED_ADMISSION_BYTES, jobs=4)
        core = load_original(controls['lifecycle'], control_refs['lifecycle']['path'], 'original_73bb_build_owner')
        helper = load_original(helper_raw, helper_ref['path'], 'foreground_build_custody')
        lifecycle = core['Commands'](OUTPUT / 'original-lifecycle', SOURCE_ROOT)
        owner = helper['ForegroundCommands'](OUTPUT, SOURCE_ROOT, lifecycle, started, record)
        def interrupted(signum, frame):
            owner.on_signal(signum)
        for sig in old_signals:
            signal.signal(sig, interrupted)
        timer_owned = True
        remaining = ACTIVE_SECONDS - (time.monotonic() - started)
        require(remaining > 0, 'The whole active budget expired during exact file admission')
        signal.setitimer(signal.ITIMER_REAL, remaining)
        expanded, old_inverse = warm['expand'](controls['producer'].decode(), data,
            Path(plan['buildAdmission']['path']), plan['buildAdmission']['sha256'],
            adapter_object, ORIGINALS['warm'][2])
        expanded_ref = write_new(OUTPUT / 'root-approved-original-producer.py', expanded.encode())
        old_inverse_ref = write_new(OUTPUT / 'original-byte-inverse-delta.json', encoded(old_inverse))
        derived, foreground_inverse = project_producer(expanded, controls['producer'].decode())
        derived_ref = write_new(OUTPUT / 'foreground-original-producer.py', derived.encode())
        inverse_ref = write_new(OUTPUT / 'foreground-full-inverse.json', encoded(foreground_inverse))
        record.update(originalExpandedProducer=expanded_ref, originalProducerInverse=old_inverse_ref,
                      foregroundProducer=derived_ref, foregroundInverse=inverse_ref)
        require(read_ref(plan['buildAdmission']) == admission_raw, 'Actual build admission changed during source preparation')
        owner.check()
        namespace = {'__name__': '__main__', '__file__': derived_ref['path'], '__package__': None,
                     '__spec__': None, '__builtins__': __builtins__, 'FOREGROUND_COMMANDS': owner}
        owner.namespace = namespace
        sys.argv = [derived_ref['path'], source]
        record['producerInvocationCount'] = 1
        # This is the only producer execution, in this process. Original29b's
        # final subprocess.run([python, producer]) is never called.
        exec(compile(derived, derived_ref['path'], 'exec'), namespace)
        record['originalExitCode'] = 0
        owner.check()
        require(owner.phase_names == ['app', 'ui'], 'Both original compiler phases are required')
        require(all(item['outcome'].get('exitCode') == 0 and item['absence'] == 'ABSENT_ESRCH'
                    for item in owner.entries), 'Every actual direct command must positively close')
        record['originalTerminalEvidence'] = read_original_success(data, namespace, derived_ref, plan['buildAdmission'])
        require(time.monotonic() - started <= ACTIVE_SECONDS, 'Actual producer exceeded the whole active budget')
        for key in ORIGINALS:
            require(read_ref(control_refs[key]) == controls[key], 'An original control changed during execution')
        require(read_ref(helper_ref) == helper_raw and read_ref(plan['buildAdmission']) == admission_raw,
                'Ownership/admission source changed during execution')
        record['allKnownGroupsClosed'] = True
        record['status'] = 'PASS_ORIGINAL_APP_AND_STAGE1_BUILD_WITHIN_WHOLE_BUDGET_NOT_ACCEPTANCE'
    except BaseException as exc:
        first_exception = exc
        if owner is not None:
            owner.absorb_observer()
            owner.fail(exc, 'foreground-wrapper')
        elif record['firstFailure'] is None:
            record['firstFailure'] = error(exc)
        else:
            record['secondaryErrors'].append({'phase': 'foreground-wrapper', **error(exc)})
        record['status'] = 'FAIL'
    finally:
        if owner is not None:
            owner.cleaning = True
            record["workAdmissionClosed"] = True
        if timer_owned:
            signal.setitimer(signal.ITIMER_REAL, 0)
        if owner is not None:
            try:
                record['ownedCommandIndex'] = owner.close_all()
                state = namespace.get('WR_PHASE_OBSERVATION_STATE', {}) if namespace is not None else {}
                record['allKnownGroupsClosed'] = bool(record['allDirectProducerGroupsClosed']
                    and not state.get('commandCustodyBlocked') and not state.get('processObservationCustodyBlocked'))
                record['compilerPhasesStarted'] = list(owner.phase_names)
            except BaseException as exc:
                owner.fail(exc, 'foreground-final-owned-closure')
                record['allKnownGroupsClosed'] = False
        sys.argv = old_argv
        for sig, handler in old_signals.items():
            signal.signal(sig, handler)
        record['finishedAt'] = time.time()
        record['elapsedSeconds'] = time.monotonic() - started
        record['withinWholeOperationBudget'] = record['elapsedSeconds'] <= WHOLE_SECONDS
        if not record['withinWholeOperationBudget']:
            exc = TimeoutError('WHOLE_BUILD_OPERATION_3300_SECONDS_NOT_CLOSED')
            if record['firstFailure'] is None:
                record['firstFailure'] = error(exc)
            else:
                record['secondaryErrors'].append({'phase': 'whole-operation-envelope', **error(exc)})
        if record['firstFailure'] is not None or record['allKnownGroupsClosed'] is not True:
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
        print('PINKHA_WARM_APP_BUILD_BUDGET_RESULT_V1 ' + json.dumps({
            'status': record['status'], 'receipt': receipt, 'firstFailure': record['firstFailure'],
            'secondaryErrors': record['secondaryErrors'], 'elapsedSeconds': record['elapsedSeconds'],
            'allKnownGroupsClosed': record['allKnownGroupsClosed'], 'readyForRuntime': False,
            'runtimeActivation': False}, sort_keys=True), flush=True)
    return 0 if record['status'] == 'PASS_ORIGINAL_APP_AND_STAGE1_BUILD_WITHIN_WHOLE_BUDGET_NOT_ACCEPTANCE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
