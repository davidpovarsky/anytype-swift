#!/usr/bin/env python3
"""Read-only warm-cache requalification and resource-only producer previews."""
from __future__ import annotations
import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
INPUT = Path('/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/warm-retry-8f2c11713fb8-inputs')
ROOT = Path('/Users/m1/development/anytype-d-active-20261125/main16-wave3-8f2c11713fb8')
OUT = INPUT / 'resource-reassessment-original512-1'
SOURCE = ROOT.parent / 'main14/source'
DERIVED = ROOT.parent / 'main14/app-derived'
SHA = '8f2c11713fb8a40ae13444104723666ffef68afe'
TREE = '7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a'
CONCURRENT = 512 * 1024 ** 2
PHASE = 6 * 1024 ** 3
FLOOR = 2 * 1024 ** 3
ORIGINALS = {
    ROOT / 'build-admission.draft.json': 'cf48a0fa5e5a3acdabff9a9e6df77c6abd9098b1b446af107ebf8c397541c640',
    ROOT / 'cache-requalification1/receipt.json': 'cf181ce88ac84618868a4c1c9faed69288bcb191599e8015271d629bcd0be00a',
    ROOT / 'source-staging1/receipt.json': '506620e9c9cb2aafe0c89076269c2a7d3a4cb6fa7334924a18dda4dff1b2f6bb',
    INPUT / 'producer-review1/receipt.json': '099943b4a88ad78f0efb810d8fd421eae67c436c5bedd3153dcafbeb0cb777fc',
    INPUT / 'producer-review1/expanded-producer.preview.txt': '84f1b5569b89d4e6b3ba7bfac98e697930200a870d181536fd35725706cec528',
    INPUT / 'resource-concurrency-review1/receipt.json': '8d10b6e8dbc578035f97990529ee78a1d964422f927c88695fad6629d5b20ea7',
    INPUT / 'resource-concurrency-review1/foreign-controller-observation.json': '0e6f75eff0058daa3d06875089454819c7ef732b2e1cc533a9445fd76cc7ad02',
}
CONTROLS = {
    'warmAdapter': ('wave3_warm_retry.py', 'c4b67858674156894a29b326c2766d043ce0308c065029bd5c1a6ae1aa254fff'),
    'originalAdapter': ('wave3_shared_build.py', '47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd'),
    'originalProducer': ('build_wave2_app16_compiler_qualified.py', '9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c'),
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ref(path):
    return {'path': str(path), 'sha256': digest(path), 'bytes': Path(path).stat().st_size}


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    return ref(path)


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    return {'argv': args, 'exitCode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def source_identity():
    out = {}
    for name, args, expected in [('head', ['rev-parse', 'HEAD'], SHA),
                                 ('tree', ['rev-parse', 'HEAD^{tree}'], TREE),
                                 ('status', ['status', '--porcelain', '--untracked-files=all'], '')]:
        row = command(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), *args])
        require(row['exitCode'] == 0 and row['stdout'].strip() == expected, 'Frozen source identity differs: ' + name)
        out[name] = row
    return out


def census():
    observed = command(['/bin/ps', '-axo', 'pid=,ppid=,comm='])
    require(observed['exitCode'] == 0, 'All-host process census failed')
    heavy, launchers, other = [], [], []
    for line in observed['stdout'].splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) != 3 or int(fields[0]) in {os.getpid(), os.getppid()}:
            continue
        pid, ppid, comm = fields
        name = Path(comm).name.lower()
        if not (any(x in name for x in ('xcodebuild', 'swift', 'clang', 'xcbuild', 'python'))
                or name in {'tar', 'gtar', 'bsdtar', 'rsync', 'scp', 'ditto', 'cp', 'dd', 'zip', 'gzip', 'zstd'}):
            continue
        args = command(['/bin/ps', '-p', pid, '-o', 'command='])
        if args['exitCode'] != 0 or not args['stdout'].strip():
            continue  # A process that terminated between the two observations.
        argv = args['stdout'].strip()
        row = {'pid': int(pid), 'ppid': int(ppid), 'comm': comm, 'command': argv}
        if any(x in name for x in ('xcodebuild', 'swift-frontend', 'swiftc', 'clang', 'xcbuild')):
            heavy.append(row)
        elif name in {'tar', 'gtar', 'bsdtar', 'rsync', 'scp', 'ditto', 'cp', 'dd', 'zip', 'gzip', 'zstd'}:
            heavy.append(row)
        elif name.startswith('swift') and '--skip-build' not in argv:
            heavy.append(row)
        elif 'python' in name:
            tokens = shlex.split(argv)
            scripts = [Path(x).name.lower() for x in tokens if x.endswith('.py')]
            if any(x.startswith(('queue-', 'queue_', 'launch-', 'launch_')) for x in scripts):
                launchers.append(row)
            else:
                other.append(row)
        else:
            other.append(row)
    return {'observedAt': time.time(), 'heavyCompilerOrCopyProcesses': heavy, 'queuedLaunchers': launchers,
            'otherObservedPythonOrSwiftProcesses': other, 'originalProcessCensusSHA256': hashlib.sha256(observed['stdout'].encode()).hexdigest(),
            'freeBytes': shutil.disk_usage('/System/Volumes/Data').free,
            'memoryPressure': command(['/usr/bin/memory_pressure', '-Q']),
            'swap': command(['/usr/sbin/sysctl', 'vm.swapusage'])}


def changes(old, new, path=''):
    if isinstance(old, dict) and isinstance(new, dict):
        rows = []
        for key in sorted(set(old) | set(new)):
            if key not in old or key not in new:
                rows.append({'path': path + '/' + key, 'before': old.get(key), 'after': new.get(key)})
            else:
                rows += changes(old[key], new[key], path + '/' + key)
        return rows
    return [] if old == new else [{'path': path, 'before': old, 'after': new}]


def main():
    OUT.mkdir(exist_ok=False)
    result = {'schema': 'pinkha-resource-only-warm-requalification-preview-v1', 'status': 'FAIL',
              'controllerSHA256': digest(__file__), 'startedAt': time.time(), 'applicationBuilds': 0, 'testsExecuted': 0,
              'sourceCacheProductsMutated': False, 'effectiveBuildApprovalCreated': False}
    try:
        for path, expected in ORIGINALS.items():
            require(digest(path) == expected, 'Preserved original changed: ' + str(path))
        result['originalsBefore'] = [ref(p) for p in ORIGINALS]
        result['controls'] = {}
        for key, (name, expected) in CONTROLS.items():
            path = INPUT / 'controls' / name
            require(digest(path) == expected, 'Reviewed control changed: ' + key)
            result['controls'][key] = ref(path)
        for name in ('build16', 'control-dispatch1', 'build-admission.approved.json'):
            require(not (ROOT / name).exists(), 'An actual build/admission already exists: ' + name)
        result['sourceBefore'] = source_identity()
        before = census()
        result['resourceBefore'] = write(OUT / 'resource-before.json', before)
        spec = importlib.util.spec_from_file_location('reviewed_warm_adapter', INPUT / 'controls/wave3_warm_retry.py')
        warm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(warm)
        adapter = warm.load_adapter(INPUT / 'controls/wave3_shared_build.py')
        warm.wr_no_shared_writer(SOURCE, DERIVED)
        old_cache = json.loads((ROOT / 'cache-requalification1/receipt.json').read_text())
        cache = copy.deepcopy(old_cache)
        cache['packageState'] = warm.wr_packages(SOURCE, DERIVED)
        require(cache['packageState'] == old_cache['packageState'], 'Exact warm package source differs')
        for name, row in cache['observedPaths'].items():
            path = Path(row['path'])
            require(path.is_dir() and not path.is_symlink() and path.resolve() == path, 'Warm cache root changed')
            require(row == {'path': str(path), 'exists': True, 'symlink': False}, 'Original cache path shape differs')
            measured = command(['/usr/bin/du', '-sk', str(path)])
            require(measured['exitCode'] == 0, 'Warm allocated-size observation failed')
            cache['observedSizes'][name] = int(measured['stdout'].split()[0]) * 1024
        policy = {'schema': 'pinkha-finite-window-resource-reassessment-v1', 'preparationOnly': True,
                  'effectiveApproval': False, 'sourceCommit': SHA,
                  'window': 'One root-owned sequential App then complete shared UI build. No independent Pinkha heavy work.',
                  'originalProducerSHA256': CONTROLS['originalProducer'][1],
                  'originalProducerConcurrentMinimumBytes': CONCURRENT,
                  'priorConcurrentAllowanceBytes': 4 * 1024 ** 3, 'proposedConcurrentAllowanceBytes': CONCURRENT,
                  'ownAppEstimateBytes': PHASE, 'ownUIEstimateBytes': 1024 ** 3, 'liveEmergencyFloorBytes': FLOOR,
                  'proposedAppEnvelopeBytes': PHASE + FLOOR + CONCURRENT,
                  'proposedUIEnvelopeBytes': 1024 ** 3 + FLOOR + CONCURRENT,
                  'basis': ['The original reviewed204f producer already defines512MiB unrelated growth; the warm4GiB was a blanket estimate without a per-owner measured allocation.',
                            'Wave2 HQ1220943104205391 explicitly reports zero Mac build/test/simulator/cache writers and no independent Apple dispatch.',
                            'SDK child explicitly reports zero current or planned Mac compiler/staging/copy work during8f2; later canonical45 qualification remains a separate root-admitted phase.',
                            'This Apple child has no compiler or copy work. Optional small-cache retirement is deferred.',
                            'The actually observed foreign Lorvex skip-build XML probe terminated04:00:55; its five retained files total130963 bytes. Its validator failed; no foreign test acceptance is claimed.',
                            'Original Hanlin r5 and its once-dispatched queue are terminal. Last release-readiness observation was read-only partial, not an active archive.'],
                  'foreignEvidence': ref(INPUT / 'resource-concurrency-review1/foreign-controller-observation.json'),
                  'limitations': ['No explicit foreign-owner promise about future work has been received. This is an estimate for a currently quiescent phase, not a measured upper bound or host-wide lease.',
                                  'Root must announce the finite Pinkha window and repeat all-host heavy compiler/copy/queued-launcher census immediately before dispatch; any new heavy writer blocks dispatch.',
                                  'Original7200s per-phase monitor, owned-process cleanup, source/package/runtime controls, four-job scheduling and live2GiB stop remain unchanged.'],
                  'resourceObservation': result['resourceBefore']}
        policy_ref = write(OUT / 'resource-reassessment.json', policy)
        cache.update(observedAt=time.time(), freeBytes=shutil.disk_usage('/System/Volumes/Data').free,
                     concurrentGrowthAllowanceBytes=CONCURRENT,
                     priorCacheQualification={'path': str(ROOT / 'cache-requalification1/receipt.json'), 'sha256': ORIGINALS[ROOT / 'cache-requalification1/receipt.json']},
                     resourceReassessment=policy_ref)
        require(cache['estimateNewAppPhaseBytes'] == PHASE and cache['emergencyFloorBytes'] == FLOOR,
                'Own phase allowance or live floor changed')
        cache_ref = write(OUT / 'cache-requalification.json', cache)
        old_draft = json.loads((ROOT / 'build-admission.draft.json').read_text())
        draft = copy.deepcopy(old_draft)
        require(draft['readyForBuild'] is False and draft['warmRetry']['concurrentGrowthAllowanceBytes'] == 4 * 1024 ** 3,
                'Original false draft/resource boundary differs')
        draft['warmRetry']['concurrentGrowthAllowanceBytes'] = CONCURRENT
        draft['cacheQualification'] = {'path': cache_ref['path'], 'sha256': cache_ref['sha256']}
        require('explicit4GiB concurrent allowance' in draft['notes'][3], 'Original resource note differs')
        draft['notes'][3] = ('Resource-only successor: own6GiB App and live2GiB floor remain; original512MiB concurrent minimum yields8.5GiB (9126805504 bytes) for the finite root-owned App then UI window. '
                             'Original4GiB cache cf181 and draft cf48 remain immutable. Fresh all-host heavy-writer/queued-launcher census is mandatory immediately before root dispatch. '
                             'Resource basis ' + policy_ref['path'] + ' SHA256 ' + policy_ref['sha256'] + '.')
        draft_ref = write(OUT / 'build-admission.ready-false.json', draft)
        try:
            adapter.load_admission(Path(draft_ref['path']), draft_ref['sha256'], SHA)
        except ValueError as exc:
            require(str(exc) == 'A finalized build admission is required', 'Unexpected closed-admission failure')
        else:
            raise ValueError('The original adapter admitted a false draft')
        proposed = copy.deepcopy(draft)
        proposed['readyForBuild'] = True
        preview_ref = write(OUT / 'proposed-admission.preview.txt', proposed)
        future = ROOT / 'build-admission.approved.json'
        warm.WAVE3_ADMISSION, warm.EXPECTED = proposed, SHA
        warm.SOURCE, warm.APP_DERIVED = SOURCE, DERIVED
        warm.PHASE_GROWTH, warm.FLOOR, warm.CONCURRENT_GROWTH = {'app': PHASE, 'ui': 1024 ** 3}, FLOOR, CONCURRENT
        warm.sha = digest
        warm.wr_validate_cache(cache, json.loads((ROOT / 'source-staging1/receipt.json').read_text()))
        inventory_ref = draft['compilerInputEnumeration']
        require(digest(inventory_ref['path']) == inventory_ref['sha256'], 'Frozen compiler enumeration changed')
        inventory = json.loads(Path(inventory_ref['path']).read_text())
        require(inventory['selectedNativeTestSources'] == draft['selectedNativeTestSources']
                and inventory['selectedUITestSources'] == draft['selectedUITestSources'], 'Selected compiler inputs changed')
        for row in inventory['sources']:
            path = SOURCE / row['path']
            require(path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], 'Selected compiler input changed: ' + row['path'])
        base = (INPUT / 'controls/build_wave2_app16_compiler_qualified.py').read_text()
        expanded, inverse = warm.expand(base, proposed, future, preview_ref['sha256'], adapter, CONTROLS['warmAdapter'][1])
        expanded_path = OUT / 'expanded-producer.preview.txt'
        with expanded_path.open('x') as stream:
            stream.write(expanded)
        inverse_ref = write(OUT / 'byte-inverse-delta.json', inverse)
        deltas = {'admission': changes(old_draft, draft), 'cache': changes(old_cache, cache),
                  'oldExpandedProducerSHA256': ORIGINALS[INPUT / 'producer-review1/expanded-producer.preview.txt'],
                  'newExpandedProducerSHA256': digest(expanded_path), 'allControlsUnchanged': True,
                  'originalSourceStagingPlanSHA256': 'd22db29bd444895e0152cc9234b3631cfb085684d23bd5ac9c074b64e51e5f3d'}
        delta_ref = write(OUT / 'exact-resource-only-delta.json', deltas)
        diff_path = OUT / 'expanded-versus-original84f.diff'
        with diff_path.open('x') as stream:
            stream.write(''.join(difflib.unified_diff((INPUT / 'producer-review1/expanded-producer.preview.txt').read_text().splitlines(True),
                                                   expanded.splitlines(True), fromfile='original84f1', tofile='resource-only-successor')))
        after = census()
        result.update(resourcePolicy=policy_ref, newCacheQualification=cache_ref, readyFalseAdmission=draft_ref,
                      proposedApprovedPreview=preview_ref, futureApprovedAdmissionPath=str(future),
                      expandedProducerPreview=ref(expanded_path), byteInverseProof=inverse_ref,
                      exactResourceDelta=delta_ref, expandedProducerDelta=ref(diff_path),
                      inverseRestoresEveryOriginalByte=inverse['inverseRestoresEveryOriginalByte'],
                      byteIdenticalOriginalFunctions=['run_phase', 'source_state'], allSelectedSourceRowsVerified=len(inventory['sources']),
                      resourceAfter=write(OUT / 'resource-after.json', after), sourceAfter=source_identity(),
                      prospectiveResourceObservation={'observedFreeBytes': after['freeBytes'],
                          'proposedAppEnvelopeBytes': PHASE + FLOOR + CONCURRENT,
                          'heavyOrQueuedProcessesAbsent': not after['heavyCompilerOrCopyProcesses'] and not after['queuedLaunchers'],
                          'requiresFreshRootCensusAndDecision': True})
        require(result['sourceBefore'] == result['sourceAfter'], 'Frozen source changed during read-only qualification')
        result['originalsAfter'] = [ref(p) for p in ORIGINALS]
        require(result['originalsBefore'] == result['originalsAfter'], 'Historical original changed during qualification')
        require(not future.exists() and not (ROOT / 'build16').exists() and not (ROOT / 'control-dispatch1').exists(),
                'No effective build/admission may be created')
        result['dispatchCommandAfterRootReviewOnly'] = [sys.executable, '-B', str(INPUT / 'controls/wave3_warm_retry.py'),
            '--admission', str(future), '--admission-sha256', preview_ref['sha256'], '--accepted-source', SHA,
            '--original-adapter', str(INPUT / 'controls/wave3_shared_build.py'),
            '--original-producer', str(INPUT / 'controls/build_wave2_app16_compiler_qualified.py'),
            '--output', str(ROOT / 'control-dispatch1'), '--execute']
        result['status'] = 'PASS_READONLY_RESOURCE_SUCCESSOR_PREPARED_NOT_ADMITTED_NOT_BUILT'
    except BaseException as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    result['finishedAt'] = time.time()
    receipt = write(OUT / 'receipt.json', result)
    print(json.dumps({'receipt': receipt, 'result': result}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
