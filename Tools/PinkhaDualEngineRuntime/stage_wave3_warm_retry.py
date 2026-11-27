"""Forward-stage a reviewed repair on the existing warm shared App cache.

No build, test, account change, native/SDK replacement, cleanup or reset occurs.
The failed source/products and all original evidence must already be retained.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
DERIVED = SOURCE.parent / 'app-derived'
FAILED = SOURCE.parent.parent / 'main16-wave3-6aab20344fcf'
PRIOR = '6aab20344fcf1c645d7c96e0b9ec034ef07003a9'
PRESERVE_SHA = 'ec5d9fd6979144eb452e0ba99c38653eb1b32dfdd1686a2eef48b580731cb0f3'
PRESERVE_CONTROL_SHA = 'd0d696f29cfabcafa08a9dc0e7b50fb240ffab119fda19843420060e4647780c'
D77_STAGE_SHA = '374c863440dd7920d607191f2626ff06621d2bf8ae54a2fad05722874617058d'
ORIGINAL15_SHA = '11ab2f45511d8b7917709c1706475538b9ea4ed228e1dc908dfa55a331cacc74'
LIFECYCLE_SHA = '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, data):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(data, indent=2, sort_keys=True) + '\n')
    return {'path': str(path), 'sha256': sha(path)}


def git(*arguments):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), *arguments], text=True,
                                   env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).strip()


def module(name, path, expected):
    require(sha(path) == expected, 'Exact reviewed control differs: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def preserved_failure(plan, preserve):
    reference = plan['failedPreservation']
    require(reference == {'path': str(FAILED / 'failed-preservation1/receipt.json'), 'sha256': PRESERVE_SHA},
            'This stage requires the exact failed6aab retention')
    require(sha(reference['path']) == PRESERVE_SHA, 'Failed retention receipt changed')
    receipt = json.loads(Path(reference['path']).read_text())
    require(receipt['status'] == 'PASS_FAILED_SOURCE_PRODUCTS_AND_ORIGINAL_EVIDENCE_RETAINED'
            and receipt['sourceCommit'] == PRIOR and not receipt['sourceMutated'] and not receipt['cacheMutated']
            and not receipt['currentProductsMutated'], 'Failed retention is incomplete')
    results = {}
    for name, row in receipt['trees'].items():
        manifests = {}
        for kind in ('before', 'retainedManifest', 'after'):
            ref = row[kind]
            require(sha(ref['path']) == ref['sha256'], 'Original failed manifest changed')
            manifests[kind] = json.loads(Path(ref['path']).read_text())['entries']
        require(manifests['before'] == manifests['retainedManifest'] == manifests['after'], 'Original retained manifest comparison differs')
        require(preserve.inventory(Path(row['retained'])) == manifests['retainedManifest'], 'Retained failed bytes/modes/links changed: ' + name)
        require(preserve.inventory(Path(row['original'])) == manifests['after'], 'Current failed source/product/evidence changed: ' + name)
        results[name] = {'nodes': len(manifests['after']), 'original': row['original'], 'retained': row['retained'],
                         'retainedManifestSHA256': row['retainedManifest']['sha256']}
    return {'status': 'PASS_FAILED_SOURCE_PRODUCTS_AND_EVIDENCE_REVERIFIED', 'receiptSHA256': PRESERVE_SHA, 'trees': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--accepted-source', required=True)
    args = parser.parse_args()
    require(sha(args.plan) == args.plan_sha256, 'Exact authorized staging plan required')
    plan = json.loads(args.plan.read_text())
    require(plan['schema'] == 'pinkha-root-warm-retry-staging-plan-v1' and plan['readyForStaging'] is True,
            'Warm source staging has not been authorized')
    require(plan['previousSourceSHA'] == PRIOR and plan['appSourceSHA'] == args.accepted_source != PRIOR,
            'Explicit new accepted source required')
    require(plan['sourceRoot'] == str(SOURCE) and plan['appDerived'] == str(DERIVED), 'Unreviewed physical source/cache')
    root = Path(plan['buildRoot'])
    require(root.parent == SOURCE.parent.parent and root.name.startswith('main16-wave3-') and root != FAILED
            and not root.exists() and not root.is_symlink(), 'Fresh retry output root required')
    require(git('rev-parse', 'HEAD') == PRIOR and git('status', '--porcelain') == '', 'Original failed source identity changed')
    controls = plan['controls']
    old_stage = module('original_d77_stager', controls['originalStager']['path'], D77_STAGE_SHA)
    old_adapter = module('original_d77_adapter', controls['originalAdapter']['path'],
                         '47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd')
    preserve = module('original_failed_preservation', controls['preservation']['path'], PRESERVE_CONTROL_SHA)
    warm = module('reviewed_warm_retry', controls['warmAdapter']['path'], controls['warmAdapter']['sha256'])
    require(sha(plan['gitBundle']['path']) == plan['gitBundle']['sha256'], 'New source bundle differs')
    require(sha(plan['buildAdmissionTemplate']['path']) == plan['buildAdmissionTemplate']['sha256'], 'Root build template differs')
    template = json.loads(Path(plan['buildAdmissionTemplate']['path']).read_text())
    warm.validate_retry(template)
    require(template['appSourceSHA'] == args.accepted_source and template['readyForBuild'] is False,
            'Staging must produce a reviewable unapproved build admission')
    require(sha(plan['originalPreservationReceipt']) == ORIGINAL15_SHA, 'Original App15 preservation receipt differs')
    original15 = json.loads(Path(plan['originalPreservationReceipt']).read_text())
    require(original15['status'] == 'PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS', 'Original App15 retention is missing')
    prior_reverify = plan['original15PriorReverification']
    require(prior_reverify == {'path': str(FAILED / 'source-staging1/preservation-reverified.json'),
                              'sha256': '9537b4c6c749945f9061b77fd5dfdb98188ce3969fc04417ed11fb5586caaece'}
            and sha(prior_reverify['path']) == prior_reverify['sha256'], 'Original15 prior reverification proof differs')
    # Original15 full bytes were reverified at the prior source stage. Its
    # separate retained trees remain untouched; do not repeat that large read.
    for path in [Path(original15['retainedSource'])] + [Path(row['retained']) for row in original15['products'].values()]:
        require(path.is_dir() and not path.is_symlink(), 'Original App15 retained tree is absent')
    owners_before = old_stage.no_compiler_or_queue()
    for group in (16415, 16387):
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            pass
        else:
            raise ValueError('Original failed process group still exists')
    retention = preserved_failure(plan, preserve)
    packages_before = warm.wr_packages(SOURCE, DERIVED)
    require(packages_before['packageResolvedSHA256'] == plan['pins']['packageResolvedSHA256'], 'Exact package lock changed')
    require(sha(SOURCE / 'Dependencies/Hanlin/.pinkha-source.json') == warm.SDK_MARKER_SHA,
            'Existing canonical SDK385 differs; this stage will not replace it')
    # Bundle verification is read-only and precedes the first source mutation.
    verified = subprocess.run(['/usr/bin/git', '-C', str(SOURCE), 'bundle', 'verify', plan['gitBundle']['path']],
                              capture_output=True, text=True, timeout=60)
    require(verified.returncode == 0, 'Source bundle prerequisite verification failed')
    old_stage.no_compiler_or_queue()
    root.mkdir(mode=0o700)
    stage = root / 'source-staging1'
    stage.mkdir()
    report = {'protocol': 'pinkha-root-warm-retry-forward-staging-v1', 'started': time.time(),
              'planSHA256': args.plan_sha256, 'sourceCommit': args.accepted_source, 'priorSource': PRIOR,
              'sourceRoot': str(SOURCE), 'appDerived': str(DERIVED), 'uiDerived': str(root / 'ui-derived'),
              'applicationBuilds': 0, 'nativeBuilds': 0, 'tests': 0, 'originalPreservationSHA256': ORIGINAL15_SHA,
              'failedPreservationSHA256': PRESERVE_SHA, 'originalIntermediatesAndPackagePathsReused': True,
              'controllerSHA256': sha(__file__)}
    try:
        write(stage / 'failed-preservation-reverified.json', retention)
        write(stage / 'owners-before.json', owners_before)
        write(stage / 'packages-before.json', packages_before)
        write(stage / 'bundle-verify.json', {'exitCode': verified.returncode, 'stdout': verified.stdout, 'stderr': verified.stderr})
        # Retain the actual failed compile's original FileList and swiftc log
        # witness before a later Xcode invocation may replace intermediates.
        failed_admission = FAILED / 'build-admission.approved.json'
        require(sha(failed_admission) == '503ec2057e1d548aaace6672c05b39d520d30271f733741fba3aad7816309646', 'Original failed root admission differs')
        old = json.loads(failed_admission.read_text())
        old_source = json.loads((FAILED / 'build16/source-before.json').read_text())
        selected = old_adapter.w3_sources(old['selectedNativeTestSources'], SOURCE, SOURCE, old_source)
        lists = old_adapter.w3_compiler_lists(DERIVED, 'AnytypeTests', selected, FAILED / 'build16/app/original.log', stage, 'failed-native')
        write(stage / 'failed-native-compiler-inputs.json', {'status': 'OBSERVED_FAILED_APP_COMPILER_INPUTS_NOT_ACCEPTANCE',
              'sourceCommit': PRIOR, 'originalLogSHA256': sha(FAILED / 'build16/app/original.log'),
              'requiredSources': selected, 'actualCompilerFileLists': lists, 'testsExecuted': 0})
        subprocess.run(['/usr/bin/git', '-C', str(SOURCE), 'fetch', '--no-tags', plan['gitBundle']['path'], args.accepted_source],
                       check=True, capture_output=True, timeout=90)
        subprocess.run(['/usr/bin/git', '-C', str(SOURCE), 'merge-base', '--is-ancestor', PRIOR, args.accepted_source], check=True)
        old_stage.no_compiler_or_queue()
        require(git('rev-parse', 'HEAD') == PRIOR and git('status', '--porcelain') == '', 'Shared source changed before fast-forward')
        subprocess.run(['/usr/bin/git', '-C', str(SOURCE), 'merge', '--ff-only', '--no-edit', args.accepted_source], check=True, capture_output=True, timeout=90)
        require(git('rev-parse', 'HEAD') == args.accepted_source and git('rev-parse', 'HEAD^{tree}') == plan['appSourceTree']
                and git('status', '--porcelain') == '', 'New exact source/tree/clean state differs')
        pins = plan['pins']
        require(sha(SOURCE / 'Tools/Hanlin/source.json') == pins['hanlinSourcePinSHA256']
                and sha(SOURCE / 'Tools/Hanlin/prepare_sdk.py') == pins['sdkMaterializerSHA256'], 'Canonical SDK pin/materializer differs')
        require(json.loads((SOURCE / 'Tools/Hanlin/source.json').read_text())['revision'] == '38528941720d9b4f2da8dce7afbc788c2e554a0c', 'Canonical SDK revision changed')
        with (stage / 'canonical-sdk-check.log').open('xb') as log:
            result = subprocess.run([sys.executable, '-B', str(SOURCE / 'Tools/Hanlin/prepare_sdk.py'), '--check'],
                                    cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        require(result.returncode == 0 and sha(SOURCE / 'Dependencies/Hanlin/.pinkha-source.json') == warm.SDK_MARKER_SHA,
                'Canonical SDK385 check failed; no SDK replacement attempted')
        native = Path(plan['nativeMaterializationRoot'])
        require(sha(native / 'receipt.json') == pins['nativeAssemblyReceiptSHA256']
                and sha(native / 'framework-files.json') == pins['nativeFrameworkInventorySHA256'], 'Original native assembly/inventory differs')
        require(old_stage.native_files(SOURCE / 'Dependencies/Middleware/Lib.xcframework') == json.loads((native / 'framework-files.json').read_text()), 'Native framework changed')
        require(sha(SOURCE / 'Tools/PinkhaDualEngineRuntime/source-permission-manifest.json') == pins['nativeSourceManifestSHA256'], 'Native8ac manifest changed')
        packages_after = warm.wr_packages(SOURCE, DERIVED)
        require(packages_after == packages_before, 'Warm package lock/checkout state changed while staging')
        ui_source = Path(plan['uiDerivedCloneSource'])
        require(ui_source == FAILED / 'ui-derived', 'Reuse only the prior never-invoked UI cache')
        require(not (FAILED / 'build16/ui').exists(), 'Original UI phase unexpectedly ran')
        ui_before = preserve.inventory(ui_source)
        write(stage / 'ui-cache-before.json', {'root': str(ui_source), 'entries': ui_before})
        clone = preserve.clone_tree(ui_source, root / 'ui-derived', ui_before)
        require(preserve.inventory(root / 'ui-derived') == ui_before == preserve.inventory(ui_source), 'UI cache clone differs')
        report['uiCacheClone'] = clone
        lifecycle = Path(plan['ownedLifecycleHelper']['path'])
        require(sha(lifecycle) == LIFECYCLE_SHA, 'Original lifecycle helper differs')
        (root / 'source-inputs').mkdir()
        shutil.copy2(lifecycle, root / 'source-inputs/combined_heart_semantics_owned_outcomes.py')
        require(sha(root / 'source-inputs/combined_heart_semantics_owned_outcomes.py') == LIFECYCLE_SHA, 'Lifecycle copy differs')
        write(stage / 'packages-after.json', packages_after)
        write(stage / 'owners-after.json', old_stage.no_compiler_or_queue())
        require(git('rev-parse', 'HEAD') == args.accepted_source and git('status', '--porcelain') == '', 'Accepted source changed during staging')
        report.update(status='PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED',
                      finished=time.time(), tree=git('rev-parse', 'HEAD^{tree}'),
                      originalPreservationReverifiedSHA256=prior_reverify['sha256'],
                      failedPreservationReverifiedSHA256=sha(stage / 'failed-preservation-reverified.json'),
                      sourceManifestSHA256=pins['nativeSourceManifestSHA256'], canonicalSDKRevision='38528941720d9b4f2da8dce7afbc788c2e554a0c',
                      sdkReceiptSHA256=warm.SDK_MARKER_SHA, freeBytesAfter=shutil.disk_usage(root).free)
        write(stage / 'receipt.json', report)
        paths = {'intermediates': DERIVED / 'Build/Intermediates.noindex', 'sourcePackages': DERIVED / 'SourcePackages',
                 'sdkModules': DERIVED / 'SDKExplicitPrecompiledModules', 'products': DERIVED / 'Build/Products'}
        observed = {name: {'path': str(path), 'exists': path.is_dir(), 'symlink': path.is_symlink()} for name, path in paths.items()}
        require(all(row['exists'] and not row['symlink'] for row in observed.values()), 'Current warm paths must all remain present')
        sizes = {name: int(subprocess.check_output(['/usr/bin/du', '-sk', str(path)], text=True).split()[0]) * 1024 for name, path in paths.items()}
        cache = {'protocol': 'pinkha-post-failure-warm-cache-qualification-v1', 'sourceCommit': args.accepted_source,
                 'stageReceiptSHA256': sha(stage / 'receipt.json'), 'stageSourceAndNativePreservationRetained': True,
                 'priorFailedSourceCommit': PRIOR, 'failedPreservationSHA256': PRESERVE_SHA,
                 'invalidatedStageMetadata': [], 'originalIntermediatesAndPackagePathsReused': True,
                 'applicationBuilds': 0, 'testsExecuted': 0, 'observedPaths': observed, 'observedSizes': sizes,
                 'packageState': packages_after, 'estimateNewAppPhaseBytes': 6442450944, 'emergencyFloorBytes': 2147483648,
                 'concurrentGrowthAllowanceBytes': template['warmRetry']['concurrentGrowthAllowanceBytes'],
                 'observedAt': time.time(), 'freeBytes': shutil.disk_usage(root).free,
                 'estimateReason': 'Conservative original 6 GiB App allowance retained despite actual warm compiler/package paths. No measured future peak is claimed.'}
        cache_dir = root / 'cache-requalification1'
        cache_dir.mkdir()
        write(cache_dir / 'receipt.json', cache)
        template.update(readyForBuild=False, sourceStaging={'path': str(stage / 'receipt.json'), 'sha256': sha(stage / 'receipt.json')},
                        cacheQualification={'path': str(cache_dir / 'receipt.json'), 'sha256': sha(cache_dir / 'receipt.json')})
        write(root / 'build-admission.draft.json', template)
        print(json.dumps({'status': report['status'], 'sourceCommit': args.accepted_source,
                          'stageReceiptSHA256': sha(stage / 'receipt.json'), 'cacheReceiptSHA256': sha(cache_dir / 'receipt.json'),
                          'draftAdmissionSHA256': sha(root / 'build-admission.draft.json'), 'builds': 0, 'tests': 0}))
    except BaseException as error:
        write(stage / 'failure.json', dict(report, status='FAIL_WARM_SOURCE_STAGING_ORIGINALS_RETAINED',
                                          error=repr(error), currentSourceSHA=git('rev-parse', 'HEAD'), finished=time.time()))
        raise


if __name__ == '__main__':
    raise SystemExit(main())
