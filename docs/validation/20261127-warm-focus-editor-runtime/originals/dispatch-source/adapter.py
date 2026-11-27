"""Admit a forward source/SDK/Kit transition on the retained 8f2 warm cache.

The original d77 adapter and 204f producer remain immutable inputs. Every new
substitution is reversible; run_phase and source_state remain byte identical.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pathlib
import re
import subprocess
import sys

D77_SHA = '47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd'
FAILED_SOURCE = '6aab20344fcf1c645d7c96e0b9ec034ef07003a9'
FAILED_ROOT = '/Users/m1/development/anytype-d-active-20261125/main16-wave3-6aab20344fcf'
PRESERVATION_SHA = 'ec5d9fd6979144eb452e0ba99c38653eb1b32dfdd1686a2eef48b580731cb0f3'
SDK_MARKER_SHA = 'b10eb0805789a04f9f48721230961e45ba6a93ceb5d95cb90437a59c87ae9528'


def wr_require(condition, message):
    if not condition:
        raise ValueError(message)


def wr_sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def wr_packages(source, derived):
    source, derived = pathlib.Path(source), pathlib.Path(derived)
    lock = source / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    workspace = derived / 'SourcePackages/workspace-state.json'
    wr_require(workspace.is_file() and not workspace.is_symlink(), 'Original warm SwiftPM workspace is missing')
    pins = json.loads(lock.read_text())['pins']
    expected = {row['identity']: row['state'] for row in pins}
    wr_require(len(expected) == len(pins), 'Duplicate package lock identities')
    observed = json.loads(workspace.read_text())
    rows, local = {}, {}
    for dependency in observed['object']['dependencies']:
        name = dependency['packageRef']['identity']
        state = dependency['state']
        if state['name'] == 'fileSystem':
            path = pathlib.Path(state['path'])
            wr_require(path.is_relative_to(source / 'Dependencies/Hanlin/Packages') and path.is_dir()
                       and not path.is_symlink(), 'Unreviewed local package path')
            local[name] = str(path)
            continue
        wr_require(state['name'] == 'sourceControlCheckout' and name in expected and name not in rows,
                   'Unexpected or duplicate warm package checkout')
        wr_require(state['checkoutState'] == expected[name], 'Workspace state differs from exact package lock: ' + name)
        subpath = pathlib.PurePosixPath(dependency['subpath'])
        wr_require(not subpath.is_absolute() and '..' not in subpath.parts, 'Invalid package checkout path')
        checkout = derived / 'SourcePackages/checkouts' / subpath
        wr_require(checkout.is_dir() and not checkout.is_symlink(), 'Physical checkout missing: ' + name)
        git = ['/usr/bin/git', '--no-replace-objects', '-C', str(checkout)]
        head = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, timeout=30,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        status = subprocess.run(git + ['status', '--porcelain', '--untracked-files=all'], capture_output=True, text=True,
                                timeout=30, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        wr_require(head.returncode == status.returncode == 0 and head.stdout.strip() == expected[name]['revision']
                   and status.stdout == '', 'Actual pinned package checkout differs: ' + name)
        rows[name] = {'path': str(checkout), 'revision': head.stdout.strip(), 'trackedStatus': '',
                      'state': state['checkoutState']}
    wr_require(set(rows) == set(expected), 'Warm checkout set differs from complete package lock')
    wr_require(set(local) == {'hanlinagentsdk', 'hanlinminiappsbridge', 'hanlinplatform', 'hanlinpresentationsdk'},
               'Canonical four-package SDK set differs')
    return {'packageResolvedSHA256': wr_sha(lock), 'workspaceStatePath': str(workspace),
            'workspaceStateSHA256': wr_sha(workspace), 'checkouts': rows, 'localSDKPackages': local}


def wr_no_shared_writer(source, derived):
    source, derived = pathlib.Path(source), pathlib.Path(derived)
    processes = subprocess.check_output(['/bin/ps', '-axo', 'pid=,ppid=,args='], text=True)
    for line in processes.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3 or int(parts[0]) == os.getpid():
            continue
        cmd = parts[2]
        compiler = any(item in cmd for item in ('xcodebuild', 'swift-frontend', '/swiftc', '/clang', 'XCBBuildService'))
        wr_require(not (compiler and (str(source) in cmd or str(derived) in cmd)), 'Shared source/cache compiler is active')
        wr_require('main16-wave2-20261127/control/launch_app16_when_compiler_admitted.py' not in cmd,
                   'Obsolete queued launcher is active')
    database = derived / 'Build/Intermediates.noindex/XCBuildData/build.db'
    wr_require(database.is_file() and not database.is_symlink(), 'Warm build database is absent')
    opened = subprocess.run(['/usr/sbin/lsof', '-nP', str(database)], capture_output=True, text=True, timeout=30)
    wr_require(opened.returncode == 1 and opened.stdout == opened.stderr == '', 'Warm build database has an owner')


def wr_validate_cache(cache, staging):
    retry = WAVE3_ADMISSION['warmRetry']
    wr_require(cache['protocol'] == 'pinkha-forward-warm-cache-qualification-v1'
               and cache['sourceCommit'] == EXPECTED, 'Fresh forward warm-cache qualification required')
    wr_require(cache['stageReceiptSHA256'] == sha(pathlib.Path(WAVE3_ADMISSION['sourceStaging']['path']))
               and cache['stageSourceAndNativePreservationRetained'] is True, 'Warm staging receipt differs')
    wr_require(cache['priorFailedSourceCommit'] == retry['priorFailedSourceCommit'], 'Prior failed source differs')
    wr_require(cache['originalIntermediatesAndPackagePathsReused'] is True
               and cache['invalidatedStageMetadata'] == [], 'Warm retry cannot reuse stale absence metadata')
    wr_require(cache['applicationBuilds'] == 0 and cache['testsExecuted'] == 0, 'Cache observation cannot claim a build/test')
    wr_require(cache['estimateNewAppPhaseBytes'] == PHASE_GROWTH['app'] and cache['emergencyFloorBytes'] == FLOOR
               and cache['concurrentGrowthAllowanceBytes'] == CONCURRENT_GROWTH, 'Resource allowance differs')
    preservation = retry['failedPreservation']
    wr_require(wr_sha(preservation['path']) == preservation['sha256'] == cache['failedPreservationSHA256']
               == staging['failedPreservationSHA256'], 'Failed build preservation differs')
    retained = json.loads(pathlib.Path(preservation['path']).read_text())
    wr_require(retained['status'] == 'PASS_FAILED_SOURCE_PRODUCTS_AND_ORIGINAL_EVIDENCE_RETAINED'
               and retained['sourceCommit'] == retry['priorFailedSourceCommit']
               and retained['originalFailure'] == {'exitCode': 65, 'uiPhaseRun': False, 'applicationAccepted': False},
               'Terminal failed build preservation is required')
    wr_require(not retained['sourceMutated'] and not retained['currentProductsMutated'] and not retained['cacheMutated'],
               'Preservation mutated original source/cache/products')
    wr_require(set(retained['trees']) == {'source', 'app-derived-Products', 'build16', 'root-dispatch1', 'control-dispatch1'},
               'Complete failed source/products/original evidence retention required')
    for row in retained['trees'].values():
        path = pathlib.Path(row['retained'])
        wr_require(path.is_dir() and not path.is_symlink(), 'Failed retained physical tree missing')
        for name in ('before', 'retainedManifest', 'after'):
            wr_require(wr_sha(row[name]['path']) == row[name]['sha256'], 'Failed retained manifest changed')
    for relative, expected in retained['originalEvidence'].items():
        wr_require(wr_sha(pathlib.Path(retry['priorBuildRoot']) / relative) == expected,
                   'Original terminal failed evidence changed')
    for name, path in [('intermediates', APP_DERIVED / 'Build/Intermediates.noindex'),
                       ('sourcePackages', APP_DERIVED / 'SourcePackages'),
                       ('sdkModules', APP_DERIVED / 'SDKExplicitPrecompiledModules'),
                       ('products', APP_DERIVED / 'Build/Products')]:
        wr_require(cache['observedPaths'][name] == {'path': str(path), 'exists': True, 'symlink': False}
                   and path.is_dir() and not path.is_symlink(), 'Warm cache root changed')
    wr_no_shared_writer(SOURCE, APP_DERIVED)
    wr_require(wr_packages(SOURCE, APP_DERIVED) == cache['packageState'], 'Pinned warm package checkout identity changed')
    wr_forward_cache(cache, staging)


def wr_forward_cache(cache, staging):
    forward = WAVE3_ADMISSION['forwardWarm']
    wr_require(forward['schema'] == 'pinkha-forward-warm-lineage-v1', 'Exact forward lineage required')
    wr_require(cache['baselineSourceSHA'] == staging['priorSource'] == forward['baselineSourceSHA']
               == '8f2c11713fb8a40ae13444104723666ffef68afe', 'Actual clean8f2 baseline required')
    ref = forward['currentBaselinePreservation']
    wr_require(set(ref) == {'path', 'sha256'} and wr_sha(ref['path']) == ref['sha256']
               == cache['baselinePreservationSHA256'] == staging['baselinePreservationSHA256'],
               'Fresh full8f2 custody differs')
    preserved = json.loads(pathlib.Path(ref['path']).read_text())
    wr_require(preserved['status'] == 'PASS_FORWARD_BASELINE_SOURCE_PRODUCTS_AND_KIT_RETAINED'
               and preserved['sourceCommit'] == forward['baselineSourceSHA']
               and preserved['sourceTree'] == forward['baselineSourceTree']
               and preserved['sourceMutated'] is False and preserved['testsExecuted'] == 0,
               'Actual pre-transition preservation is required')
    wr_require(set(preserved['trees']) == {'source', 'app-derived-Products', 'prior-kit-checkout'},
               'Complete source, current Products and prior Kit checkout custody required')
    for row in preserved['trees'].values():
        root = pathlib.Path(row['retained'])
        wr_require(root.is_dir() and not root.is_symlink(), 'Physical retained forward baseline is absent')
        for key in ('before', 'retainedManifest', 'after'):
            wr_require(wr_sha(row[key]['path']) == row[key]['sha256'], 'Forward retention manifest changed')
    transition = cache['packageTransition']
    wr_require(transition['status'] == 'PASS_EXACT_KIT_ONLY_LOCK_AND_CHECKOUT_TRANSITION'
               and transition['changedIdentity'] == 'torahinspectorkit'
               and transition['beforeRevision'] == '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'
               and transition['afterRevision'] == '26beca175d64a4d34e3567f2bbb4bf308d714478'
               and transition['unchangedCount'] == 55 and transition['pinCount'] == 56,
               'Only the exact reviewed Kit transition is admitted')
    wr_require(transition['afterPackageState'] == cache['packageState']
               and transition['afterLockSHA256'] == WAVE3_ADMISSION['pins']['packageResolvedSHA256']
               and transition['beforeLockSHA256'] == forward['baselinePackageResolvedSHA256'],
               'Forward package receipt differs')
    wr_require(staging['canonicalSDKRevision'] == forward['targetSDKRevision']
               and staging['sdkReceiptSHA256'] == WAVE3_ADMISSION['pins']['sdkMaterializationReceiptSHA256'],
               'Final SDK source/marker differs')
    wr_require(cache['historicalProcessGroupReprobes'] == 0
               and staging['historicalProcessGroupReprobes'] == 0,
               'Historical groups are receipt evidence only')
    census_ref = forward['resourceCensusControl']
    census_path = pathlib.Path(census_ref['path'])
    wr_require(census_path.resolve() == census_path and not census_path.is_symlink()
               and wr_sha(census_path) == census_ref['sha256']
               == '229222b72fd01aa515aef502aa8f8c889344f9e4cd60981421f49f53ecf3bd2a',
               'Exact original all-host resource observer required')
    spec = importlib.util.spec_from_file_location('forward_original_resource_observer', census_path)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    observed = observer.census()
    w3_write(EVIDENCE / 'forward-global-census.json', observed)
    wr_require(not observed['heavyCompilerOrCopyProcesses'] and not observed['queuedLaunchers'],
               'A fresh all-host heavy writer or queue blocks the finite build window')
    wr_require(observed['freeBytes'] >= PHASE_GROWTH['app'] + FLOOR + CONCURRENT_GROWTH,
               'The original6GiB+2GiB+512MiB warm App envelope is unavailable')



def validate_forward(data):
    forward = data['forwardWarm']
    wr_require(forward['schema'] == 'pinkha-forward-warm-lineage-v1'
               and forward['baselineSourceSHA'] == '8f2c11713fb8a40ae13444104723666ffef68afe'
               and forward['baselineSourceTree'] == '7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a',
               'This source successor starts only from the actual clean8f2 checkpoint')
    wr_require(forward['baselineSDKMarkerSHA256'] == 'b10eb0805789a04f9f48721230961e45ba6a93ceb5d95cb90437a59c87ae9528'
               and forward['baselinePackageResolvedSHA256'] == 'e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd',
               'Observed baseline SDK/lock differs')
    wr_require(re.fullmatch('[0-9a-f]{40}', forward['targetSDKRevision'] or '') is not None
               and forward['targetSDKRevision'] != '38528941720d9b4f2da8dce7afbc788c2e554a0c',
               'Explicit published target SDK required; an unbound plan cannot run')
    wr_require(re.fullmatch('[0-9a-f]{40}', data['appSourceSHA'] or '') is not None
               and data['appSourceSHA'] != forward['baselineSourceSHA'], 'Exact forward App source required')
    for key in ('sdkMaterializationReceiptSHA256', 'packageResolvedSHA256', 'nativeSourceManifestSHA256'):
        wr_require(re.fullmatch('[0-9a-f]{64}', data['pins'].get(key) or '') is not None,
                   'Exact final source dependency required: ' + key)
    wr_require(data['warmRetry']['concurrentGrowthAllowanceBytes'] == 512 * 1024 ** 2,
               'This finite-window source successor retains the exact512MiB estimate')
    wr_require(forward['buildsDuringStaging'] == 0 and forward['testsDuringStaging'] == 0,
               'Staging and runtime admission are separate')


def validate_retry(data):
    retry = data['warmRetry']
    wr_require(retry['schema'] == 'pinkha-terminal-failure-warm-retry-v1', 'Explicit warm retry admission is required')
    wr_require(retry['priorFailedSourceCommit'] == FAILED_SOURCE and retry['priorBuildRoot'] == FAILED_ROOT,
               'This retry is scoped to the preserved first shared failure')
    wr_require(retry['failedPreservation'] == {'path': FAILED_ROOT + '/failed-preservation1/receipt.json',
                                              'sha256': PRESERVATION_SHA}, 'Exact original failed retention required')
    wr_require(data['appSourceSHA'] != FAILED_SOURCE and data['buildRoot'] != FAILED_ROOT, 'Fresh source/output required')
    validate_forward(data)
    wr_require(type(retry['concurrentGrowthAllowanceBytes']) is int and retry['concurrentGrowthAllowanceBytes'] >= 512 * 1024 ** 2,
               'Concurrent growth allowance cannot be reduced')


def load_adapter(path):
    wr_require(wr_sha(path) == D77_SHA, 'Original d77 adapter bytes differ')
    spec = importlib.util.spec_from_file_location('reviewed_d77_build_adapter', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expand(base, data, admission_path, admission_sha, adapter, controller_sha):
    validate_retry(data)
    candidate, original_delta = adapter.expand_controller(base, data, admission_path, admission_sha, controller_sha)
    changes = []

    def replace(old, new):
        nonlocal candidate
        wr_require(candidate.count(old) == 1, 'Original expanded producer structure differs')
        candidate = candidate.replace(old, new, 1)
        changes.append({'old': old, 'new': new, 'count': 1})

    begin = candidate.index(' assert cache["protocol"]=="app16-observed-cache-requalification-v1"')
    end = candidate.index(' write(EVIDENCE/"cache-requalification.json"', begin)
    replace(candidate[begin:end], ' wr_validate_cache(cache,staging)\n')
    concurrent = data['warmRetry']['concurrentGrowthAllowanceBytes']
    if concurrent != 512 * 1024 ** 2:
        replace('CONCURRENT_GROWTH=512*1024**2', 'CONCURRENT_GROWTH=' + str(concurrent))
    before_write = ' write(EVIDENCE/"input-and-resource-admission.json",baseline)'
    correct_metadata = (' baseline.update(originalIntermediatesAndPackagePathsReused=True,\n'
                        '                 reasonForJobs4="Forward warm build from preserved clean8f2 using the same physical source and DerivedData. The full baseline source, current Products and changed Kit checkout are separately retained by actual APFS clones before the source/SDK/one-lock-pin transition. All55 other locked checkout revisions remain exact; all56 final checkout HEADs and untracked-source status are requalified. Original App15 and failed6aab custody remains separate. Original four-job scheduling, 6 GiB App estimate and 2 GiB live own-process floor remain.",\n'
                        '                 phaseBudgetEvidence={"warmCacheObservedSizes":cache["observedSizes"],\n'
                        '                                     "interpretation":"The 6 GiB App allowance is retained conservatively; it is not a measured future incremental peak. Current post-failure compiler/package paths are physically present and qualified. The exact root-approved concurrent growth allowance remains additional."})\n')
    replace(before_write, correct_metadata + before_write)
    own_source = Path(__file__).read_text()
    helpers = [ast.get_source_segment(own_source, node) for node in ast.parse(own_source).body
               if isinstance(node, ast.FunctionDef) and node.name.startswith('wr_')]
    marker = '\ntry:\n w3_control_admission()'
    replace(marker, '\n\n' + '\n\n'.join(helpers) + '\n' + marker)
    inverse = candidate
    all_changes = original_delta['changes'] + changes
    for change in reversed(all_changes):
        wr_require(inverse.count(change['new']) == change['count'], 'Ambiguous warm producer inverse')
        inverse = inverse.replace(change['new'], change['old'])
    wr_require(inverse == base, 'Warm producer inverse did not restore every original 204f byte')
    for name in ('run_phase', 'source_state'):
        wr_require(adapter.function_source(candidate, name) == adapter.function_source(base, name), 'Original function changed: ' + name)
    compile(candidate, '<root-bound-warm-original-producer>', 'exec')
    return candidate, dict(original_delta, schema='pinkha-root-warm-producer-byte-inverse-v1',
                           originalAdapterSHA256=D77_SHA, candidateSHA256=hashlib.sha256(candidate.encode()).hexdigest(),
                           changes=all_changes, warmRetryChanges=len(changes), inverseRestoresEveryOriginalByte=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--admission-sha256', required=True)
    parser.add_argument('--accepted-source', required=True)
    parser.add_argument('--original-adapter', type=Path, required=True)
    parser.add_argument('--original-producer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    adapter = load_adapter(args.original_adapter)
    data = adapter.load_admission(args.admission, args.admission_sha256, args.accepted_source)
    candidate, delta = expand(args.original_producer.read_text(), data, args.admission, args.admission_sha256,
                              adapter, wr_sha(__file__))
    args.output.mkdir(exist_ok=False)
    path = args.output / 'root-approved-original-producer.py'
    path.write_text(candidate)
    (args.output / 'byte-inverse-delta.json').write_text(json.dumps(delta, indent=2, sort_keys=True) + '\n')
    if not args.execute:
        print(json.dumps({'status': 'PREPARED_WARM_RETRY_NOT_BUILT', 'controller': str(path), 'sha256': wr_sha(path)}))
        return 0
    wr_require(wr_sha(args.admission) == args.admission_sha256, 'Root admission changed during preparation')
    return subprocess.run([sys.executable, '-B', str(path), data['appSourceSHA']], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
