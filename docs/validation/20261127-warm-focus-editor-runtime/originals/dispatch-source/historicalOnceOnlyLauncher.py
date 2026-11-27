#!/usr/bin/env python3
"""Root-only one-shot dispatch; --check-cherri is bounded and read-only.

No global resource lock is invented. The original producer/supervisor remain
byte-identical. Fresh process admission is a snapshot, not a host-wide lease.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pathlib
import shutil
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
INPUT = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs')
REVIEW = INPUT / 'resource-reassessment-original512-1'
ROOT = Path('/Users/m1/development/anytype-d-active-20261125/main16-wave3-8f2c11713fb8')
SOURCE = ROOT.parent / 'main14/source'
DERIVED = ROOT.parent / 'main14/app-derived'
CLAIM = ROOT / 'root-dispatch1'
SOURCE_SHA = '8f2c11713fb8a40ae13444104723666ffef68afe'
PREVIEW_SHA = 'e40ccaabe400abda4800e9a065e094e7d2ffbd8969eb776e173bb04c2e24752a'
PRODUCER_SHA = '6c648e2e9af511013d20ce0a3fb300e59783917fc49a5d909f042917860fa200'
ENVELOPE = 6 * 1024 ** 3 + 2 * 1024 ** 3 + 512 * 1024 ** 2
HELPER = Path('/Users/m1/sentinelx/uploads/pinkha-wave3-resource-reassessment-original512-20261127.py')
HELPER_SHA = '229222b72fd01aa515aef502aa8f8c889344f9e4cd60981421f49f53ecf3bd2a'
SUPERVISOR = ROOT.parent / 'main16-wave3-6aab20344fcf/root-dispatch1/supervisor.py'
SUPERVISOR_SHA = 'bd0ee535786b2a7c95b4da1b6dfdbd1b1f409438a6214cb4252d0c386cebf42e'
CHERRI = Path('/Users/m1/builds/_preflight/cherri-ui-fixed-five-local-0fd3-20261127-01')
CHERRI_DERIVED = Path('/Users/m1/caches/DerivedData/cherri-ui-296-fixed-five-xcode27-20261127-02')
REVIEW_REFS = {
    'receipt.json': '8928287e8c00c26cef3bae695832660b443c6d8eee473fef7b4b0025def70a8c',
    'resource-reassessment.json': 'e1507aac15ddd17c4fee7201b5ad06603cbb9c98da701e6de65fc5eb7428bc5a',
    'cache-requalification.json': '11575f9d03aaa36c2bddcc12ba2c01b1614631c73bedabc598c3abf57e4d8a7d',
    'build-admission.ready-false.json': '3fd2073f9a935e3d66bd16471f120997577daca36610fdbf8d62a08f1cdeaf66',
    'proposed-admission.preview.txt': PREVIEW_SHA,
    'expanded-producer.preview.txt': PRODUCER_SHA,
    'byte-inverse-delta.json': '04c61f57a088819a3a0cba3e29bc8c436e7a1356cfcbabf6dddcfc849e16ef78',
    'exact-resource-only-delta.json': '822ee801ddd0e5635d5ea8ad1830b4e5bb0236c0c24fac971e7ce3dcc0bfdab6',
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def reference(path):
    return {'path': str(path), 'sha256': digest(path), 'bytes': Path(path).stat().st_size}


def original_json(path, maximum=1024 * 1024):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink() and info.st_size <= maximum,
            'Bounded original regular file required: ' + str(path))
    data = path.read_bytes()
    after = path.lstat()
    require((info.st_ino, info.st_size, info.st_mtime_ns) ==
            (after.st_ino, after.st_size, after.st_mtime_ns), 'Original changed while reading')
    return json.loads(data), {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def command(argv, timeout=15):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    return {'argv': argv, 'exitCode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def cherri_terminal():
    """Read original terminal/drain evidence and one process census; never signal."""
    result = {'schema': 'pinkha-cherri-terminal-resource-check-v1', 'status': 'BLOCKED',
              'observedAt': time.time(), 'foreignMutations': False, 'signalsSent': 0,
              'foreignTestAcceptanceGranted': False}
    try:
        controller = CHERRI / 'qualified-owner-01/local_owner.py'
        require(controller.is_file() and not controller.is_symlink() and controller.stat().st_size == 20421,
                'Exact bounded foreign controller file required')
        require(digest(controller) == 'bec9662f8a11c11da5082556721040d8a361adbf9068a82aa30d99fd3ebc8834',
                'Observed foreign controller changed')
        result['originalController'] = reference(controller)
        context, context_ref = original_json(CHERRI / 'execution-01/context.original.json')
        require(context_ref['sha256'] == '6380d91155edd4680e6d01ee0668542e85e5abf940bd047d457964b20c7f3624',
                'Observed Cherri execution identity changed')
        terminal_path = CHERRI / 'execution-01/result.original.json'
        require(terminal_path.is_file(), 'Original terminal result is not present')
        terminal, terminal_ref = original_json(terminal_path)
        require(terminal['schema'] == 'cherri-local-fixed-five-diagnostic/1'
                and terminal['context'] == context
                and terminal['status'] in {'COMPLETED_DIAGNOSTIC', 'INCOMPLETE'},
                'Original foreign terminal identity/status differs')
        started, started_ref = original_json(CHERRI / 'execution-01/xcode-test/started.original.json')
        finished, finished_ref = original_json(CHERRI / 'execution-01/xcode-test/finished.original.json')
        require(started['pid'] == finished['pid'] == 99371, 'Actual observed foreign process identity differs')
        require(finished['cleanupParentReaped'] is True and finished['groupPresentAfterCleanup'] is False
                and finished['groupAfterCleanup']['state'] == 'ABSENT', 'Original foreign group drain is not proven')
        process = command(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,command='])
        require(process['exitCode'] == 0, 'Read-only process census failed')
        matching = []
        for line in process['stdout'].splitlines():
            fields = line.strip().split(None, 3)
            if len(fields) != 4 or int(fields[0]) in {os.getpid(), os.getppid()}:
                continue
            pid, ppid, pgid, argv = fields
            if int(pid) in {99343, 99371} or int(pgid) == 99371 or str(CHERRI) in argv or str(CHERRI_DERIVED) in argv:
                matching.append(line)
        result.update(originalContext=context_ref, originalTerminal=terminal_ref,
                      originalStarted=started_ref, originalFinished=finished_ref,
                      originalExitCode=terminal.get('xcodebuildExitCode'), originalTerminalStatus=terminal['status'],
                      originalDrainPID=finished['pid'], matchingProcesses=matching,
                      processCensusSHA256=hashlib.sha256(process['stdout'].encode()).hexdigest())
        require(not matching, 'Foreign owner/process group or scoped worker is still present')
        database = CHERRI_DERIVED / 'Build/Intermediates.noindex/XCBuildData/build.db'
        if database.is_file():
            opened = command(['/usr/sbin/lsof', '-nP', str(database)])
            result['buildDatabaseOpenHandles'] = opened
            require(opened['exitCode'] == 1 and opened['stdout'] == opened['stderr'] == '',
                    'Foreign build database still has an owner')
        else:
            result['buildDatabaseOpenHandles'] = {'path': str(database), 'exists': False}
        require(digest(terminal_path) == terminal_ref['sha256'], 'Foreign terminal evidence changed during observation')
        result['status'] = 'PASS_ORIGINAL_TERMINAL_AND_PROCESS_ABSENCE_NOT_TEST_ACCEPTANCE'
    except BaseException as exc:
        result['blocker'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    return result


def write_bytes(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return reference(path)


def write(path, value):
    return write_bytes(path, (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


def load_module(name, path, expected):
    require(digest(path) == expected, 'Reviewed helper differs: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def global_admission(helper):
    observed = helper.census()
    try:
        require(not observed['heavyCompilerOrCopyProcesses'] and not observed['queuedLaunchers'],
                'Foreign heavy compiler/copy or queued launcher is present')
        require(observed['freeBytes'] >= ENVELOPE, 'Original finite-window phase allowance is unavailable')
    except BaseException as exc:
        exc.resource_census = observed
        raise
    return observed


def native_preflight(expanded, admission):
    """Execute only four unchanged original read-only dependency functions."""
    parsed = ast.parse(expanded)
    names = {'write', 'sha', 'verify_runtime_identity', 'verify_dependencies'}
    segments = {n.name: ast.get_source_segment(expanded, n) for n in parsed.body
                if isinstance(n, ast.FunctionDef) and n.name in names}
    require(set(segments) == names, 'Original dependency function closure differs')
    evidence = CLAIM / 'native-sdk-preflight'
    evidence.mkdir()
    env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer',
               PINKHA_ANY_NATIVE_ARTIFACT='verified-unified-v1', PINKHA_NATIVE_T2_AUTHORIZED_READ_V1='1',
               PYTHONDONTWRITEBYTECODE='1')
    env['PATH'] = '/opt/homebrew/bin:/usr/local/bin:' + env.get('PATH', '/usr/bin:/bin')
    scope = {'pathlib': pathlib, 'os': os, 'subprocess': subprocess, 'json': json, 'hashlib': hashlib,
             'importlib': importlib, 'ROOT': ROOT, 'SOURCE': SOURCE, 'APP_DERIVED': DERIVED,
             'EVIDENCE': evidence, 'EXPECTED': SOURCE_SHA, 'ENV': env}
    for source in segments.values():
        exec(compile(source, '<unchanged-original-readonly-dependency-function>', 'exec'), scope)
    scope['verify_dependencies']('root-predispatch')
    return {'scope': 'Actual original native inventory/runtime/SDK checks only; no compiler, build or simulator.',
            'functionSHA256': {name: hashlib.sha256(source.encode()).hexdigest() for name, source in segments.items()},
            'evidence': [reference(p) for p in sorted(evidence.iterdir()) if p.is_file()],
            'nativeSourceManifestSHA256': admission['pins']['nativeSourceManifestSHA256']}


def execute_once():
    helper = load_module('reviewed_resource_reassessment', HELPER, HELPER_SHA)
    foreign = None
    try:
        foreign = cherri_terminal()
        require(foreign['status'].startswith('PASS_'), 'Foreign terminal resource check is blocked: ' + json.dumps(foreign.get('blocker')))
        initial_resource = global_admission(helper)
    except BaseException as exc:
        print(json.dumps({'schema': 'pinkha-root-warm8f2-blocked-before-claim-v1',
            'status': 'BLOCKED_BEFORE_CLAIM_AND_DISPATCH', 'observedAt': time.time(),
            'launcherSHA256': digest(__file__), 'sourceCommit': SOURCE_SHA,
            'foreignTerminal': foreign, 'initialResource': getattr(exc, 'resource_census', None),
            'error': {'type': type(exc).__name__, 'message': str(exc)},
            'rootClaimCreated': False, 'effectiveAdmissionCreated': False,
            'supervisorStarted': False}, sort_keys=True), flush=True)
        return 1
    for name in ('build16', 'control-dispatch1', 'build-admission.approved.json', 'root-dispatch1'):
        require(not (ROOT / name).exists() and not (ROOT / name).is_symlink(), 'One-shot root output already exists: ' + name)
    require(ROOT.resolve(strict=True) == ROOT, 'Exact canonical build root required')
    CLAIM.mkdir(exist_ok=False)  # A scoped one-shot claim, not a host-wide lock.
    result = {'schema': 'pinkha-root-warm8f2-one-shot-dispatch-v1', 'status': 'FAIL_BEFORE_DISPATCH',
              'startedAt': time.time(), 'launcherSHA256': digest(__file__), 'sourceCommit': SOURCE_SHA,
              'effectiveAdmissionCreated': False, 'supervisorStarted': False,
              'globalResourceLock': 'NONE_OBSERVED; fresh census and root coordination only',
              'originalPhaseTimeoutSeconds': 7200, 'rootClaim': str(CLAIM)}
    try:
        result['foreignTerminal'] = write(CLAIM / 'foreign-terminal.json', foreign)
        result['initialResource'] = write(CLAIM / 'resource-initial.json', initial_resource)
        for path, expected in helper.ORIGINALS.items():
            require(digest(path) == expected, 'Historical original changed: ' + str(path))
        for name, expected in REVIEW_REFS.items():
            require(digest(REVIEW / name) == expected, 'Reviewed resource original changed: ' + name)
        result['reviewedOriginals'] = [reference(REVIEW / name) for name in REVIEW_REFS]
        require(digest(SUPERVISOR) == SUPERVISOR_SHA, 'Original supervised process handler changed')
        result['sourceBefore'] = helper.source_identity()
        original_draft = json.loads((REVIEW / 'build-admission.ready-false.json').read_text())
        admission = json.loads((REVIEW / 'proposed-admission.preview.txt').read_text())
        expected = copy.deepcopy(original_draft)
        expected['readyForBuild'] = True
        require(original_draft['readyForBuild'] is False and admission == expected, 'Proposed admission differs beyond root readiness')
        controls = INPUT / 'controls'
        warm = load_module('reviewed_warm_dispatch_adapter', controls / 'wave3_warm_retry.py', helper.CONTROLS['warmAdapter'][1])
        adapter = warm.load_adapter(controls / 'wave3_shared_build.py')
        base = (controls / 'build_wave2_app16_compiler_qualified.py').read_text()
        future = ROOT / 'build-admission.approved.json'
        expanded, inverse = warm.expand(base, admission, future, PREVIEW_SHA, adapter, helper.CONTROLS['warmAdapter'][1])
        require(hashlib.sha256(expanded.encode()).hexdigest() == PRODUCER_SHA
                and expanded.encode() == (REVIEW / 'expanded-producer.preview.txt').read_bytes(), 'Executed expansion would differ from exact review')
        require(inverse == json.loads((REVIEW / 'byte-inverse-delta.json').read_text()), 'Original full-byte inverse differs')
        warm.WAVE3_ADMISSION, warm.EXPECTED = admission, SOURCE_SHA
        warm.SOURCE, warm.APP_DERIVED = SOURCE, DERIVED
        warm.PHASE_GROWTH = {'app': 6 * 1024 ** 3, 'ui': 1024 ** 3}
        warm.FLOOR, warm.CONCURRENT_GROWTH, warm.sha = 2 * 1024 ** 3, 512 * 1024 ** 2, digest
        cache = json.loads(Path(admission['cacheQualification']['path']).read_text())
        staging = json.loads(Path(admission['sourceStaging']['path']).read_text())
        warm.wr_validate_cache(cache, staging)
        result['freshSmallDependencyPins'] = []
        for path, expected in [
            (SOURCE / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved', admission['pins']['packageResolvedSHA256']),
            (SOURCE / 'Dependencies/Hanlin/.pinkha-source.json', admission['pins']['sdkMaterializationReceiptSHA256']),
            (ROOT / 'source-inputs/combined_heart_semantics_owned_outcomes.py',
             '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a'),
        ]:
            require(digest(path) == expected, 'Original dependency/lifecycle input differs: ' + str(path))
            result['freshSmallDependencyPins'].append(reference(path))
        inventory_ref = admission['compilerInputEnumeration']
        require(digest(inventory_ref['path']) == inventory_ref['sha256'], 'Selected compiler enumeration changed')
        inventory = json.loads(Path(inventory_ref['path']).read_text())
        require(inventory['selectedNativeTestSources'] == admission['selectedNativeTestSources']
                and inventory['selectedUITestSources'] == admission['selectedUITestSources'], 'Compiler selection differs')
        for row in inventory['sources']:
            path = SOURCE / row['path']
            require(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'Actual selected source differs: ' + row['path'])
        result['selectedCompilerSourcesVerified'] = len(inventory['sources'])
        result['freshWarmPackageAndRetentionChecks'] = {'checkouts': len(cache['packageState']['checkouts']),
            'localSDKRoots': len(cache['packageState']['localSDKPackages']), 'cacheQualification': admission['cacheQualification'],
            'originalFailurePreservation': admission['warmRetry']['failedPreservation']}
        result['nativeSDKPreflight'] = native_preflight(expanded, admission)
        require(digest(admission['originalRetention']['path']) == admission['originalRetention']['sha256'], 'Original App15 retention receipt differs')
        result['sourceAfter'] = helper.source_identity()
        require(result['sourceBefore'] == result['sourceAfter'], 'Frozen source changed during predispatch qualification')
        for name, expected in REVIEW_REFS.items():
            require(digest(REVIEW / name) == expected, 'Reviewed resource original changed during qualification')
        for path, expected in helper.ORIGINALS.items():
            require(digest(path) == expected, 'Historical original changed during qualification')
        supervisor_copy = CLAIM / 'supervisor.py'
        result['supervisor'] = write_bytes(supervisor_copy, SUPERVISOR.read_bytes())
        require(result['supervisor']['sha256'] == SUPERVISOR_SHA, 'Original supervisor copy differs')
        argv = [sys.executable, '-B', str(controls / 'wave3_warm_retry.py'), '--admission', str(future),
                '--admission-sha256', PREVIEW_SHA, '--accepted-source', SOURCE_SHA,
                '--original-adapter', str(controls / 'wave3_shared_build.py'),
                '--original-producer', str(controls / 'build_wave2_app16_compiler_qualified.py'),
                '--output', str(ROOT / 'control-dispatch1'), '--execute']
        spec = {'schema': 'pinkha-root-supervised-dispatch-input-v1', 'argv': argv,
                'controlDirectory': str(controls), 'sourceCommit': SOURCE_SHA,
                'producerReceipt': str(ROOT / 'build16/receipt.json'),
                'actualProducer': str(ROOT / 'control-dispatch1/root-approved-original-producer.py'),
                'expectedProducerSHA256': PRODUCER_SHA, 'admissionSHA256': PREVIEW_SHA,
                'resourceEnvelopeBytes': ENVELOPE, 'originalPhaseTimeoutSeconds': 7200}
        result['dispatchSpec'] = write(CLAIM / 'dispatch.json', spec)
        sealed = CLAIM / 'complete-admission-bytes.preview'
        result['sealedCompleteAdmissionBytes'] = write_bytes(sealed, (REVIEW / 'proposed-admission.preview.txt').read_bytes())
        require(result['sealedCompleteAdmissionBytes']['sha256'] == PREVIEW_SHA, 'Complete approved bytes differ')
        # These checks are deliberately immediately before the atomic effective name.
        warm.wr_no_shared_writer(SOURCE, DERIVED)
        final_foreign = cherri_terminal()
        require(final_foreign['status'].startswith('PASS_'), 'Foreign terminal/process absence changed before dispatch')
        result['finalForeignTerminal'] = write(CLAIM / 'foreign-terminal-final.json', final_foreign)
        final_resource = global_admission(helper)
        result['finalResource'] = write(CLAIM / 'resource-final.json', final_resource)
        require(not future.exists() and not future.is_symlink() and not (ROOT / 'build16').exists()
                and not (ROOT / 'control-dispatch1').exists(), 'Another effective admission/build appeared')
        result['preflightReceipt'] = write(CLAIM / 'predispatch.json', dict(result, status='PASS_PREDISPATCH_NOT_YET_LAUNCHED'))
        os.link(sealed, future, follow_symlinks=False)  # Atomic, complete and no-overwrite; no fallback.
        result['effectiveAdmissionCreated'] = True
        require(digest(future) == PREVIEW_SHA, 'Atomic effective admission differs')
        with (CLAIM / 'supervisor-original.log').open('xb') as log:
            child = subprocess.Popen([sys.executable, '-B', str(supervisor_copy)], cwd=CLAIM,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True)
        result.update(status='DISPATCHED_ONCE_BUILD_OUTCOME_PENDING', supervisorStarted=True,
                      supervisorPID=child.pid, supervisorPGID=child.pid,
                      processObservation=command(['/bin/ps', '-p', str(child.pid), '-o', 'pid=,ppid=,pgid=,command=']),
                      effectiveAdmission=reference(future))
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    receipt = write(CLAIM / 'launch.json', result)
    print(json.dumps({'receipt': receipt, 'result': result}))
    return 0 if result['status'] == 'DISPATCHED_ONCE_BUILD_OUTCOME_PENDING' else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--launcher-sha256', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-cherri', action='store_true')
    mode.add_argument('--execute-once', action='store_true')
    args = parser.parse_args()
    require(digest(__file__) == args.launcher_sha256, 'Exact root-reviewed launcher required')
    if args.check_cherri:
        result = cherri_terminal()
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'].startswith('PASS_') else 3
    return execute_once()


if __name__ == '__main__':
    raise SystemExit(main())
