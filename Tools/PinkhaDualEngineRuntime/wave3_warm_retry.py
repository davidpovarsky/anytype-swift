"""Add explicit terminal-failure warm-cache admission to the original producer.

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
    wr_require(cache['protocol'] == 'pinkha-post-failure-warm-cache-qualification-v1'
               and cache['sourceCommit'] == EXPECTED, 'Fresh post-failure warm-cache qualification required')
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


def validate_retry(data):
    retry = data['warmRetry']
    wr_require(retry['schema'] == 'pinkha-terminal-failure-warm-retry-v1', 'Explicit warm retry admission is required')
    wr_require(retry['priorFailedSourceCommit'] == FAILED_SOURCE and retry['priorBuildRoot'] == FAILED_ROOT,
               'This retry is scoped to the preserved first shared failure')
    wr_require(retry['failedPreservation'] == {'path': FAILED_ROOT + '/failed-preservation1/receipt.json',
                                              'sha256': PRESERVATION_SHA}, 'Exact original failed retention required')
    wr_require(data['appSourceSHA'] != FAILED_SOURCE and data['buildRoot'] != FAILED_ROOT, 'Fresh source/output required')
    wr_require(data['pins']['sdkMaterializationReceiptSHA256'] == SDK_MARKER_SHA
               and data['pins']['nativeSourceManifestSHA256'] == '8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b',
               'This retry preserves SDK385/native8ac')
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
                        '                 reasonForJobs4="Warm incremental retry from the retained terminal failed build. The same physical source and DerivedData retain actual compiler intermediates, all locked package checkouts, SDK explicit modules and Products. Original App15 and failed6aab source/Products/evidence remain separately preserved. Original four-job scheduling, 6 GiB App estimate and 2 GiB live own-process floor remain.",\n'
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
