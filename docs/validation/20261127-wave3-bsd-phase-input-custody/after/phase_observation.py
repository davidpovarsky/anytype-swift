"""Finite phase admission over the source-bound original-owned serial observer.

This source does not alter the original observation or its command owner.
The only callable projection renames owner() and returns its terminal record;
the calling operation retains its original signal handler. Every actual process
observation remains fresh, bounded, separately retained, and not a host lease.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
MIB = 1024 ** 2
GIB = 1024 ** 3
PROVIDER_SHA = '8052135ab77c7f6de6cda2dadf2c8833c7396e97c30c7d6633a353f22eae8292'
PROVIDER_BYTES = 38162
OWNER_SHA = 'f4e1cbe0cf54812636d1332e25cc21b3467770ca8d858ab89d975132c9aa08ea'
D2E3_SHA = 'd2e3aa399518d5e3ba24966559f12812856abb35c44cf589e5f54fddcd649f3c'
COLLECTOR_SHA = '7c61364134252b6a02b181caab19336ec85b380f45c95db0b30d6983aacd7906'
LIFECYCLE_SHA = '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a'
CONTROL_PARENT = Path('/Users/m1')
OBSERVATION_PARENT = Path('/Users/m1/development/anytype-root-active-20261125')
SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
DERIVED = SOURCE.parent / 'app-derived'
INPUT_PHASES = {'receive-sdk', 'observe-toolchain'}
STAGE_PHASES = {'owners-before', 'owners-before-fetch', 'owners-before-mutation',
                'owners-before-fast-forward', 'owners-before-exact-resolution', 'owners-after'}
BUILD_PHASES = {'build-cache-writer', 'build-resource'}
PHASES = INPUT_PHASES | STAGE_PHASES | BUILD_PHASES


def require(value, message):
    if not value:
        raise ValueError(message)


def error(exc):
    return {'type': type(exc).__name__, 'message': str(exc)}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def physical(path, *, directory=False, fresh=False):
    path = Path(path)
    require(path.is_absolute() and str(path) == os.path.normpath(str(path)), 'Canonical absolute path required')
    require(all(not item.is_symlink() for item in (path, *path.parents)), 'Symbolic path component refused')
    if fresh:
        require(not path.exists() and path.parent.resolve(strict=True) == path.parent,
                'Exclusive phase evidence path required')
    else:
        require(path.resolve(strict=True) == path and (path.is_dir() if directory else path.is_file()),
                'Physical phase input required: ' + str(path))
    return path


def read_ref(row, *, maximum=MIB):
    require(set(row) == {'path', 'bytes', 'sha256'} and type(row['bytes']) is int
            and 0 <= row['bytes'] <= maximum and re.fullmatch('[0-9a-f]{64}', row['sha256'] or ''),
            'Exact finite file reference required')
    path = physical(row['path'])
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(row['bytes'] + 1)
        after = os.fstat(stream.fileno())
    final = path.stat()
    keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_nlink')
    require(all(getattr(before, key) == getattr(after, key) == getattr(final, key) for key in keys)
            and len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
            'Phase input identity/content changed: ' + str(path))
    return raw


def own_ref():
    path = physical(Path(__file__).resolve())
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path = physical(path, fresh=True)
    raw = encoded(value)
    require(len(raw) <= 16 * MIB, 'Finite phase receipt envelope exceeded')
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(read_ref(row, maximum=16 * MIB) == raw, 'Phase receipt readback differs')
    return row


def project_owner(source):
    """Three exact syntax adaptations; the complete inverse is checked every time."""
    functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'owner']
    require(len(functions) == 1, 'Exactly one original observation entry is required')
    original = ast.get_source_segment(source, functions[0])
    require(hashlib.sha256(original.encode()).hexdigest() == OWNER_SHA, 'Exact original serial owner differs')
    changes = [
        ('def owner(args):\n', 'def phase_owner(args):\n'),
        ("        print(json.dumps({'status': record['status'], 'receipt': receipt, 'firstFailure': record['firstFailure'],\n"
         "                          'secondaryErrors': record['secondaryErrors'], 'allKnownGroupsClosed': record['allKnownGroupsClosed'],\n"
         "                          'readyForBuild': False}, allow_nan=False), flush=True)\n", ''),
        ("    return 0 if record['status'] == 'PASS_COMPLETE_BOUNDED_OBSERVATION' else 1",
         '    return record, receipt'),
    ]
    projected, positions = original, []
    for old, new in changes:
        require(projected.count(old) == 1, 'Original callable projection seam differs')
        offset = projected.index(old)
        projected = projected[:offset] + new + projected[offset + len(old):]
        positions.append((offset, old, new))
    inverse = projected
    for offset, old, new in reversed(positions):
        require(inverse[offset:offset + len(new)] == new, 'Callable inverse position differs')
        inverse = inverse[:offset] + old + inverse[offset + len(new):]
    require(inverse == original, 'Callable inverse must restore every original entry byte')
    return projected


def load_provider(binding):
    require(binding['schema'] == 'pinkha-phase-bsd-observation-binding-v1'
            and binding['readyForObservation'] is True and binding['readyForBuild'] is False,
            'A source-only phase binding cannot execute')
    require(binding['adapter'] == own_ref(), 'Actual phase adapter differs from the root binding')
    read_ref(binding['adapter'])
    provider = binding['provider']
    require(provider['bytes'] == PROVIDER_BYTES and provider['sha256'] == PROVIDER_SHA,
            'Exact reviewed serial observation is required')
    raw = read_ref(provider)
    spec = importlib.util.spec_from_file_location('pinkha_phase_original_serial', provider['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    projected = project_owner(raw.decode('utf-8'))
    exec(compile(projected, provider['path'] + ':phase-main', 'exec'), module.__dict__)
    require(read_ref(provider) == raw, 'Original provider changed during the isolated load')
    return module, hashlib.sha256(projected.encode()).hexdigest()


def namespace_roots(binding, control_paths, protected_paths):
    """Only physical root-owned controls and the caller's concrete namespaces.

    BSD/bridge are borrowed immutable owner inputs, not root-owned directories.
    Their complete bytes remain fenced by the unchanged original observer.
    A matching nonself argv is conservatively a conflict; no comm-only exemption
    or presumed read-only parent can turn an ambiguous reference into permission.
    """
    roots = binding['protectedControlRoots']
    require(isinstance(roots, list) and 1 <= len(roots) <= 8 and len(roots) == len(set(roots)),
            'Finite explicit root-owned control directories are required')
    physical_roots = [physical(path, directory=True) for path in roots]
    require(all(path.is_relative_to(CONTROL_PARENT) and path != CONTROL_PARENT for path in physical_roots),
            'Only concrete existing Mac control directories are permitted')
    require(all(any(Path(path).is_relative_to(root) for root in physical_roots) for path in control_paths),
            'Every actual root-owned observation/control input must be protected')
    for path in protected_paths:
        path = Path(path)
        require(path.is_absolute() and str(path) == os.path.normpath(str(path))
                and all(not item.is_symlink() for item in (path, *path.parents)),
                'Canonical protected namespace required')
        require(path.resolve(strict=True) == path and path.is_dir(), 'Protected namespace must already exist')
        physical_roots.append(path)
    return sorted(set(map(str, physical_roots)))


def reader_namespaces(metadata_owner, readers):
    """Derive real Git-dir/worktree spellings for each observed object store.

    A Git writer can name its repository without spelling /objects. Admit only
    the original physical Git layout actually found here; no guessed paths,
    Git commands, parent-wide namespace, or unrelated process exemption.
    """
    paths = list(readers)
    alternates = sorted({path for row in readers.values()
                         for path in row['alternateObjectDirectories']})
    require(len(alternates) <= 16, 'Two original readers have at most sixteen observed alternates')
    repositories = {}
    for name in alternates:
        objects = physical(name, directory=True)
        require(objects.name == 'objects', 'Unreviewed custom alternate object layout is closed')
        git_dir = physical(objects.parent, directory=True)
        metadata = metadata_owner.repository_metadata(git_dir)
        require('HEAD' in metadata['files'] and 'config' in metadata['files'],
                'Actual alternate repository controls are required before deriving its namespace')
        repositories[str(git_dir)] = metadata
        paths.extend((str(objects), str(git_dir)))
        if git_dir.name == '.git':
            worktree = physical(git_dir.parent, directory=True)
            require(worktree / '.git' == git_dir and git_dir / 'objects' == objects,
                    'Original literal worktree/.git/objects relationship differs')
            paths.append(str(worktree))
    return sorted(set(paths)), repositories


def latch(outer, first, *, phase, observation=None, blocked=False):
    if outer.get('firstFailure') is None:
        outer['firstFailure'] = copy.deepcopy(first)
        outer['firstFailurePhase'] = phase
    elif outer['firstFailure'] != first:
        outer.setdefault('secondaryErrors', []).append({'phase': phase, **copy.deepcopy(first)})
    outer['processObservationCustodyBlocked'] = bool(outer.get('processObservationCustodyBlocked') or blocked)
    outer['commandCustodyBlocked'] = bool(outer.get('commandCustodyBlocked') or blocked)
    if observation is not None:
        outer.setdefault('failedProcessObservations', []).append(copy.deepcopy(observation))


def observe(binding, phase, output, outer, *, protected_paths=(), control_paths=(), reader_roots=()):
    """Run one fresh finite observation, then the caller's exact phase policy.

    The 64 MiB observation allowance is a separate pre-phase evidence envelope.
    Original receive640/toolchain8/staging512/build6GiB resource checks follow
    on actual remaining space. This function starts no compiler or Git command.
    """
    result = {'schema': 'pinkha-phase-bsd-observation-result-v1', 'status': 'FAIL',
              'phase': phase, 'readyForBuild': False, 'observationOnly': True,
              'doesNotReserveHost': True, 'globalIdleRequired': False,
              'firstFailure': None, 'secondaryErrors': [], 'allKnownGroupsClosed': True,
              'startedAt': time.time()}
    first, original, original_receipt = None, None, None
    try:
        require(phase in PHASES, 'Unreviewed observation phase')
        require(outer.get('firstFailure') is None and not outer.get('commandCustodyBlocked')
                and not outer.get('processObservationCustodyBlocked'),
                'Earlier cause or unresolved command custody prevents a new observation')
        physical(output, fresh=True)
        require(isinstance(binding['observations'], dict) and set(binding['observations']) <= PHASES
                and phase in binding['observations'], 'Exact finite observation slot is required')
        plan_ref = binding['observations'][phase]
        plan = json.loads(read_ref(plan_ref))
        require(plan['collector']['sha256'] == COLLECTOR_SHA and plan['lifecycle']['sha256'] == LIFECYCLE_SHA,
                'Original command owner references differ')
        require(Path(plan['outputRoot']).parent == OBSERVATION_PARENT,
                'Observation evidence belongs to the existing private root namespace')
        provider, projection_sha = load_provider(binding)
        require(isinstance(reader_roots, (tuple, list)) and len(reader_roots) <= 2,
                'Only the concrete original and selected SDK readers may be inspected')
        metadata_owner = provider.load(plan['collector']['path'], COLLECTOR_SHA, 'phase_original_reader_metadata')
        reader_metadata = {str(physical(path, directory=True)): metadata_owner.repository_metadata(Path(path))
                           for path in reader_roots}
        reader_paths, alternate_repository_metadata = reader_namespaces(metadata_owner, reader_metadata)
        roots = namespace_roots(binding,
            [binding['adapter']['path'], binding['provider']['path'], plan_ref['path'],
             plan['originalProvider']['path'], plan['collector']['path'], plan['lifecycle']['path'], *control_paths],
            [*protected_paths, *reader_paths])
        result.update(adapter=binding['adapter'], originalProvider=binding['provider'],
                      originalOwnerSHA256=OWNER_SHA, callableProjectionSHA256=projection_sha,
                      execution='EXACT_SERIAL_WORKER_WITH_SOURCE_BOUND_CALLABLE_OWNER',
                      observationPlan=plan_ref, protectedNamespaces=roots,
                      originalReaderMetadataBefore=reader_metadata,
                      alternateRepositoryMetadataBefore=alternate_repository_metadata)
        # A nonreturning owner call has unknown custody. Only its actual
        # terminal record can restore positive closure for this bridge.
        result['allKnownGroupsClosed'] = False
        original, original_receipt = provider.phase_owner(
            SimpleNamespace(plan=Path(plan_ref['path']), plan_sha256=plan_ref['sha256']))
        result.update(originalObservation=original_receipt,
                      allKnownGroupsClosed=original['allKnownGroupsClosed'],
                      originalFirstFailure=original['firstFailure'],
                      originalSecondaryErrors=original['secondaryErrors'])
        if original['firstFailure'] is not None:
            latch(outer, original['firstFailure'], phase=phase, observation=original_receipt,
                  blocked=not original['allKnownGroupsClosed'])
            result['firstFailure'] = copy.deepcopy(original['firstFailure'])
        require(original['status'] == 'PASS_COMPLETE_BOUNDED_OBSERVATION'
                and original['firstFailure'] is None and original['allKnownGroupsClosed']
                and original_receipt is not None, 'Actual complete original observation is required')
        worker = json.loads(read_ref(original['workerReceipt'], maximum=16 * MIB))
        require(worker['workerParentPID'] == os.getpid()
                and worker['workerPID'] == original['workerOutcome']['pid']
                and worker['allDirectChildrenReaped'] and worker['firstFailure'] is None,
                'The serial observation must be the current caller\'s actual owned worker')
        complete = json.loads(read_ref(original['completeProcessArguments'], maximum=16 * MIB))
        # Restore the original caller context: old80c9 excludes this current
        # operation itself, and old229 separately excludes its current parent.
        # The only additional worker was the exact73bb child now positively
        # absent. No foreign PID, ancestor chain, or same-PG cohort is omitted.
        self_rows = [row for row in complete if row['pid'] == os.getpid()]
        require(len(self_rows) == 1, 'Complete actual coverage must contain this live observer caller')
        processes = [row for row in complete if row['pid'] != os.getpid()]
        require(plan['originalProvider']['sha256'] == D2E3_SHA,
                'Original229/80c9 policy source differs')
        predicates = provider.load(plan['originalProvider']['path'], D2E3_SHA, 'phase_original_policy').original_predicates(processes)
        warm_pass = (original['originalBuildDatabasePredicatePass']
                     and not predicates['sharedSourceCacheWriters'] and not predicates['obsoleteLaunchers'])
        # This is actual complete argv from the final identity-bracketed sweep.
        # The calling process is already excluded by d2e3; every other live PID,
        # including its parent, remains subject to these namespace predicates.
        conflicts = []
        for row in processes:
            matches = [path for path in roots if path in row['command']]
            if matches:
                conflicts.append({'pid': row['pid'], 'ppid': row['ppid'], 'comm': row['comm'],
                                  'command': row['command'], 'identity': row['identity'],
                                  'protectedNamespaces': matches})
        reader_conflicts = [row for row in conflicts
                            if any(path in reader_paths for path in row['protectedNamespaces'])]
        result.update(predicates=predicates, originalWorkerContextPredicates=original['predicates'],
                      originalGlobalResourcePredicatePass=not predicates['heavyCompilerOrCopyProcesses'] and not predicates['queuedLaunchers'],
                      originalBuildDatabasePredicatePass=original['originalBuildDatabasePredicatePass'],
                      originalSharedWarmPathPredicatePass=warm_pass,
                      protectedNamespaceArgumentConflicts=conflicts,
                      protectedReaderArgumentConflicts=reader_conflicts,
                      completeProcessArguments=original['completeProcessArguments'],
                      actualCurrentCallerIdentity=self_rows[0]['identity'],
                      allLiveArgumentCoverage=worker['allLiveArgumentCoverage'])
        if phase in INPUT_PHASES:
            require(not conflicts, 'A live nonself argv references an exact protected input/control namespace')
        else:
            # The original build launcher is a legitimate parent control reader.
            # Warm phases retain80c9's exact nonself compiler/path predicates;
            # they do not add an all-parent/control-path idle test. Any explicit
            # original SDK reader dependency remains protected separately.
            require(not reader_conflicts, 'A live nonself argv references an exact protected SDK reader namespace')
        if phase in STAGE_PHASES | BUILD_PHASES:
            require(warm_pass,
                    'Original80c9 shared compiler/obsolete-launcher/build.db predicates did not pass')
        # No global no-heavy/no-copy/no-queue test is introduced here. Those
        # unchanged229 facts remain available to actual root resource planning.
        read_ref(binding['provider'])
        read_ref(binding['adapter'])
        read_ref(plan_ref)
        after_metadata = {path: metadata_owner.repository_metadata(Path(path)) for path in reader_metadata}
        require(after_metadata == reader_metadata, 'Original SDK reader/alternate metadata changed during observation')
        after_paths, after_alternate_metadata = reader_namespaces(metadata_owner, after_metadata)
        require(after_paths == reader_paths and after_alternate_metadata == alternate_repository_metadata,
                'Actual alternate Git/worktree namespaces or original controls changed during observation')
        result['originalReaderMetadataAfter'] = after_metadata
        result['alternateRepositoryMetadataAfter'] = after_alternate_metadata
        st = os.statvfs('/System/Volumes/Data')
        result.update(freeBytes=st.f_bavail * st.f_frsize,
                      status='PASS_COMPLETE_OBSERVATION_AND_PHASE_PREDICATES')
    except BaseException as exc:
        first = exc
        if result['firstFailure'] is None:
            result['firstFailure'] = error(exc)
        else:
            result['secondaryErrors'].append(error(exc))
        latch(outer, result['firstFailure'], phase=phase, observation=original_receipt,
              blocked=not result['allKnownGroupsClosed'])
    result['finishedAt'] = time.time()
    result_ref = None
    try:
        result_ref = write(output, result)
    except BaseException as exc:
        if first is None:
            first = exc
            result['firstFailure'] = error(exc)
        else:
            result['secondaryErrors'].append(error(exc))
        result['status'] = 'FAIL'
        latch(outer, result['firstFailure'], phase=phase,
              observation=original_receipt, blocked=not result['allKnownGroupsClosed'])
        outer.setdefault('secondaryErrors', []).append({'phase': phase + '-receipt-write', **error(exc)})
    outer.setdefault('processObservations', []).append(
        {'phase': phase, 'receipt': result_ref, 'originalObservation': original_receipt,
         'status': result['status'], 'allKnownGroupsClosed': result['allKnownGroupsClosed']})
    if first is not None:
        raise first
    return result, result_ref
