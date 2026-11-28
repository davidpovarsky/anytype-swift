"""Forward-stage an explicitly bound source from the actual retained a72 cache.

The checked-in proposal is UNBOUND. This controller cannot admit a build, run
tests, replace native artifacts, delete caches, or re-probe historical groups.
Only a separately hash-bound root staging plan can enable the finite changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time

sys.dont_write_bytecode = True
SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main14/source')
DERIVED = SOURCE.parent / 'app-derived'
BASELINE = 'a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd'
BASELINE_TREE = '2adebea229e42c5ff56e50aaf0adebbacfbc4c41'
PRIOR_A72_ROOT = SOURCE.parent.parent / 'main16-wave3-forward-a72f2e1ee303'
PRIOR_ROOT = SOURCE.parent.parent / 'main16-wave3-8f2c11713fb8'
FAILED_ROOT = SOURCE.parent.parent / 'main16-wave3-6aab20344fcf'
FAILED_SHA = '6aab20344fcf1c645d7c96e0b9ec034ef07003a9'
FAILED_RECEIPT = 'ec5d9fd6979144eb452e0ba99c38653eb1b32dfdd1686a2eef48b580731cb0f3'
ORIGINAL15 = '11ab2f45511d8b7917709c1706475538b9ea4ed228e1dc908dfa55a331cacc74'
PRIOR_STAGE = '506620e9c9cb2aafe0c89076269c2a7d3a4cb6fa7334924a18dda4dff1b2f6bb'
SDK_BEFORE = '41445d6e8ea29da6460aeb340f006b7d0eaa7f0fb5a4a805d2c369ff4ef17124'
LOCK_BEFORE = '4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689'
KIT_BEFORE = '26beca175d64a4d34e3567f2bbb4bf308d714478'
KIT_AFTER = '414e0d3e95d53509381d233a23fcdd28ef24167a'
LOCK_RELATIVE = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
FLOOR = 2 * 1024 ** 3
STAGE_GROWTH = 512 * 1024 ** 2
CONTROL_HASHES = {
    'preservation': 'd0d696f29cfabcafa08a9dc0e7b50fb240ffab119fda19843420060e4647780c',
    'originalStager': '374c863440dd7920d607191f2626ff06621d2bf8ae54a2fad05722874617058d',
    'originalAdapter': '47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd',
    'census': '229222b72fd01aa515aef502aa8f8c889344f9e4cd60981421f49f53ecf3bd2a',
    'lifecycle': '73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a',
    'warmAdapter': '181b5f3ca42943e1dc8179d16a98d63998f966212920e63c3c8a5317e98b4d75',
    'phaseObserver': '75dfe996edc8ffd5eece2efbd6a64238e221a0d4b9e885edaf47d9cebe043826',
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_ref(row):
    path = Path(row['path'])
    require(path.is_absolute() and path.resolve() == path and path.is_file()
            and not path.is_symlink(), 'Physical original reference required')
    require(re.fullmatch('[0-9a-f]{64}', row['sha256'] or '')
            and sha(path) == row['sha256'], 'Original reference differs: ' + str(path))
    return path


def write(path, value):
    data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    Path(path).chmod(0o600)
    return {'path': str(path), 'sha256': sha(path)}


def load_control(name, row):
    require(row['sha256'] == CONTROL_HASHES[name], 'Reviewed control pin differs: ' + name)
    path = read_ref(row)
    spec = importlib.util.spec_from_file_location('forward_original_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StageCommands:
    """Use the unchanged original73bb owner; never act on historical PIDs."""

    def __init__(self, lifecycle, root, developer_dir):
        self.owner = lifecycle.Commands(root, SOURCE)
        self.owner.environment.update(DEVELOPER_DIR=developer_dir, GIT_OPTIONAL_LOCKS='0')
        self.sequence = 0

    def barrier(self):
        require(not self.owner.cancelled and set(self.owner.groups) <= self.owner.absent_groups,
                'An actual owned command is unresolved; no next command may start')

    def run(self, argv, label, timeout, checked=True):
        self.barrier()
        self.sequence += 1
        log, result = self.owner.run(argv, str(self.sequence) + '-' + label, timeout,
                                     checked=checked, capacity=True)
        self.barrier()
        return log.read_bytes(), result

    def git(self, *argv, timeout=60):
        text, result = self.run(['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), *argv],
                                'git-' + argv[0].lstrip('-'), timeout)
        require(result['exitCode'] == 0, 'Exact Git command failed')
        return text.decode('utf-8').strip()


def census(controls, output, plan, report, commands):
    commands.barrier()
    binding = plan['processObservation']
    row, ref = controls['phaseObserver'].observe(binding, output.stem, output, report,
        protected_paths=[Path(plan['buildRoot'])],
        control_paths=[str(Path(__file__).resolve()), *[item['path'] for item in plan['controls'].values()]],
        reader_roots=[plan['hanlinReadOnlySourceRoot'],
            '/Users/m1/development/anytype-root-active-20261125/shared-build-inputs-385289-20261127/hanlin-385289-source.git'])
    commands.barrier()
    require(row['originalSharedWarmPathPredicatePass'],
            'Original80c9 shared compiler/obsolete-launcher/build.db predicates did not pass')
    require(row['freeBytes'] >= FLOOR + STAGE_GROWTH, 'Source staging metadata allowance unavailable')
    return {'path': ref['path'], 'sha256': ref['sha256']}


def identity(commands, commit, tree):
    require(commands.git('rev-parse', 'HEAD', 'HEAD^{tree}').splitlines() == [commit, tree],
            'Exact physical source commit/tree differs')
    require(commands.git('status', '--porcelain', '--untracked-files=all') == '',
            'Source has tracked or nonignored untracked changes')


def lock_rows(raw):
    values = json.loads(raw)['pins']
    rows = {row['identity']: row for row in values}
    require(len(rows) == len(values) == 56, 'Exact56 locked package identities required')
    return rows


def package_transition(before_raw, after_raw, before, after):
    old, new = lock_rows(before_raw), lock_rows(after_raw)
    require(set(old) == set(new), 'Package identity added or removed')
    changed = [name for name in old if old[name] != new[name]]
    require(changed == ['torahinspectorkit'], 'Only the reviewed Kit pin may change')
    oldkit, newkit = old['torahinspectorkit'], new['torahinspectorkit']
    require(oldkit['state']['revision'] == KIT_BEFORE and newkit['state']['revision'] == KIT_AFTER,
            'Wrong Kit source transition')
    oldcopy, newcopy = json.loads(json.dumps(oldkit)), json.loads(json.dumps(newkit))
    oldcopy['state']['revision'] = newcopy['state']['revision']
    require(oldcopy == newcopy, 'Kit identity/location/kind/version/branch changed beyond its revision')
    require(set(before['checkouts']) == set(after['checkouts']) == set(new), 'Actual checkout set differs')
    for name in old:
        if name != 'torahinspectorkit':
            require(before['checkouts'][name] == after['checkouts'][name],
                    'Unchanged pinned checkout moved or changed: ' + name)
    require(before['checkouts']['torahinspectorkit']['path']
            == after['checkouts']['torahinspectorkit']['path'], 'Kit checkout path unexpectedly moved')
    require(before['localSDKPackages'] == after['localSDKPackages'], 'Original four local SDK paths changed')
    return {'status': 'PASS_EXACT_KIT_ONLY_LOCK_AND_CHECKOUT_TRANSITION',
            'changedIdentity': 'torahinspectorkit', 'beforeRevision': KIT_BEFORE, 'afterRevision': KIT_AFTER,
            'unchangedCount': 55, 'pinCount': 56,
            'beforeLockSHA256': hashlib.sha256(before_raw).hexdigest(),
            'afterLockSHA256': hashlib.sha256(after_raw).hexdigest(),
            'beforePackageState': before, 'afterPackageState': after}


def existing_retention(plan, preserve):
    old = read_ref(plan['originalRetention'])
    require(sha(old) == ORIGINAL15, 'Original App15 receipt changed')
    original15 = json.loads(old.read_bytes())
    require(original15['status'] == 'PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS',
            'App15 original retention required')
    for path in [original15['retainedSource']] + [row['retained'] for row in original15['products'].values()]:
        require(Path(path).is_dir() and not Path(path).is_symlink(), 'App15 physical retention is absent')
    oldstage = read_ref(plan['prior8f2Stage'])
    require(sha(oldstage) == PRIOR_STAGE, 'Original actual8f2 staging receipt differs')
    previous = json.loads(oldstage.read_bytes())
    require(previous['sourceCommit'] == '8f2c11713fb8a40ae13444104723666ffef68afe'
            and previous['tree'] == '7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a',
            'Prior staging must describe actual8f2')
    path = read_ref(plan['failedPreservation'])
    require(path == FAILED_ROOT / 'failed-preservation1/receipt.json' and sha(path) == FAILED_RECEIPT,
            'Original failed6aab retention differs')
    record = json.loads(path.read_bytes())
    require(record['status'] == 'PASS_FAILED_SOURCE_PRODUCTS_AND_ORIGINAL_EVIDENCE_RETAINED'
            and record['sourceCommit'] == FAILED_SHA, 'Original failed retention status differs')
    for row in record['trees'].values():
        states = [json.loads(read_ref(row[key]).read_bytes())['entries']
                  for key in ('before', 'retainedManifest', 'after')]
        require(states[0] == states[1] == states[2]
                == preserve.inventory(Path(row['retained'])), 'Retained failed tree differs')
    for relative, expected in record['originalEvidence'].items():
        require(sha(FAILED_ROOT / relative) == expected, 'Original failed evidence changed')
    # The historical original source/Products paths are mutable warm inputs.
    # Their fresh8f2 custody is separate; do not compare them to old6aab bytes.
    return {'status': 'PASS_ORIGINAL_APP15_AND_FAILED6AAB_CUSTODY_RETAINED',
            'original15ReceiptSHA256': ORIGINAL15, 'prior8f2StageSHA256': PRIOR_STAGE,
            'failedPreservationSHA256': FAILED_RECEIPT, 'historicalProcessGroupReprobes': 0}


def retain_current(preserve, destination, packages):
    destination.mkdir(mode=0o700)
    record = {'status': 'FAIL_FORWARD_BASELINE_PRESERVATION', 'sourceCommit': BASELINE,
              'sourceTree': BASELINE_TREE, 'sourceMutated': False, 'testsExecuted': 0, 'trees': {}}
    roots = {'source': SOURCE, 'app-derived-Products': DERIVED / 'Build/Products',
             'prior-kit-checkout': Path(packages['checkouts']['torahinspectorkit']['path'])}
    for name, original in roots.items():
        require(shutil.disk_usage(destination).free >= FLOOR + STAGE_GROWTH,
                'Preservation metadata envelope unavailable')
        before = preserve.inventory(original)
        before_ref = write(destination / (name + '-before.json'), {'root': str(original), 'entries': before})
        retained = destination / name
        method = preserve.clone_tree(original, retained, before)
        cloned = preserve.inventory(retained)
        clone_ref = write(destination / (name + '-retained.json'), {'root': str(retained), 'entries': cloned})
        after = preserve.inventory(original)
        after_ref = write(destination / (name + '-after.json'), {'root': str(original), 'entries': after})
        require(before == cloned == after, 'Full APFS clone node/mode/time/link/content verification differs')
        record['trees'][name] = {'original': str(original), 'retained': str(retained),
                                 'before': before_ref, 'retainedManifest': clone_ref, 'after': after_ref,
                                 'clone': method, 'entries': len(before)}
    record['status'] = 'PASS_FORWARD_BASELINE_SOURCE_PRODUCTS_AND_KIT_RETAINED'
    return write(destination / 'receipt.json', record)


def native_inputs(plan, original_stager):
    pins = plan['pins']
    native = Path(plan['nativeMaterializationRoot'])
    require(native.is_dir() and native.resolve() == native and not native.is_symlink(),
            'Native materialization root must be physical')
    require(sha(native / 'receipt.json') == pins['nativeAssemblyReceiptSHA256']
            and sha(native / 'framework-files.json') == pins['nativeFrameworkInventorySHA256'],
            'Exact previously produced native artifact closure required')
    require(json.loads((native / 'receipt.json').read_bytes())['status']
            == 'PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE', 'Unqualified native assembly')
    require(original_stager.native_files(SOURCE / 'Dependencies/Middleware/Lib.xcframework')
            == json.loads((native / 'framework-files.json').read_bytes()),
            'Installed native bytes differ; this stager cannot replace or compile them')


def toolchain_intake(commands, plan, directory):
    expected = plan['toolchain']['expectedOutputSHA256']
    argv = {
        'xcode': ['xcodebuild', '-version'],
        'swift': ['xcrun', 'swift', '--version'],
        'simulator-sdk': ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-build-version'],
    }
    require(set(expected) == set(argv), 'Three exact toolchain observations are required')
    require(plan['toolchain']['developerDir'] == plan['developerDir'], 'Toolchain environment differs')
    rows = []
    for name, command in argv.items():
        require(re.fullmatch('[0-9a-f]{64}', expected[name] or ''), 'Unbound toolchain observation')
        raw, outcome = commands.run(command, 'toolchain-' + name, 60)
        require(hashlib.sha256(raw).hexdigest() == expected[name], 'Actual toolchain differs: ' + name)
        rows.append({'name': name, 'argv': command, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'originalCommand': outcome})
    return write(directory / 'toolchain-intake.json',
                 {'status': 'PASS_ORIGINAL_SAME_ENVIRONMENT_TOOLCHAIN_OUTPUTS',
                  'developerDir': plan['developerDir'], 'observations': rows})


def compiler_sources(plan, template):
    path = read_ref(plan['compilerInputInventory'])
    data = json.loads(path.read_bytes())
    require(template['compilerInputEnumeration']['sourceCommit'] == plan['appSourceSHA']
            and template['compilerInputEnumeration']['sourceTree'] == plan['appSourceTree']
            and template['compilerInputEnumeration']['sha256'] == sha(path),
            'The final compiler inventory must bind the exact target source')
    for key in ('selectedNativeTestSources', 'selectedUITestSources'):
        require(data[key] == template[key] and len(data[key]) == len(set(data[key])),
                'Exact complete compiler selection differs')
    wanted = set(data['selectedNativeTestSources'] + data['selectedUITestSources'])
    rows = {row['path']: row for row in data['sources']}
    require(len(rows) == len(data['sources']) and set(rows) == wanted, 'Compiler source row set differs')
    for relative, row in rows.items():
        path = SOURCE / relative
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                and path.resolve().is_relative_to(SOURCE) and path.is_file() and not path.is_symlink(),
                'Original compiler source must be a contained regular file')
        require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
                'Actual final compiler source differs: ' + relative)
    return {'status': 'PASS_SELECTED_SOURCE_BYTES_NOT_COMPILER_EXECUTION',
            'nativeSources': len(data['selectedNativeTestSources']),
            'uiSources': len(data['selectedUITestSources']), 'sourceRows': len(rows),
            'inventorySHA256': sha(read_ref(plan['compilerInputInventory']))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--accepted-source', required=True)
    args = parser.parse_args()
    require(sha(args.plan) == args.plan_sha256, 'Exact root staging plan required')
    plan = json.loads(args.plan.read_bytes())
    require(plan['schema'] == 'pinkha-root-forward-warm-staging-plan-v1'
            and plan['readyForStaging'] is True, 'Unbound or unapproved staging cannot execute')
    require(re.fullmatch('[0-9a-f]{40}', args.accepted_source or '')
            and plan['appSourceSHA'] == args.accepted_source != BASELINE,
            'Actual published forward source required')
    require(plan['previousSourceSHA'] == BASELINE and plan['previousSourceTree'] == BASELINE_TREE
            and plan['sourceRoot'] == str(SOURCE) and plan['appDerived'] == str(DERIVED),
            'This route is scoped to the actual retained a72 physical cache')
    require(SOURCE.is_dir() and SOURCE.resolve() == SOURCE and not SOURCE.is_symlink()
            and DERIVED.is_dir() and DERIVED.resolve() == DERIVED and not DERIVED.is_symlink(),
            'The original source and warm DerivedData must be physical')
    require(re.fullmatch('[0-9a-f]{40}', plan['appSourceTree'] or '')
            and re.fullmatch('[0-9a-f]{40}', plan['sdkRevision'] or ''),
            'Final source tree and SDK revision must be bound before staging')
    require(plan['nativeMode'] == 'reuse-exact-installed-qualified-input'
            and plan['runtimeActivation'] is False, 'Native replacement and runtime remain separate')
    require(plan['rootWindow']['status'] == 'ROOT_REVIEWED_FINITE_OWNER_WINDOW',
            'A fresh root-coordinated finite window is required')
    read_ref(plan['rootWindow']['evidence'])
    controls = {name: load_control(name, plan['controls'][name]) for name in CONTROL_HASHES}
    root = Path(plan['buildRoot'])
    require(root.parent == SOURCE.parent.parent and root.name.startswith('main16-wave3-forward-')
            and not root.exists() and not root.is_symlink(), 'Exclusive fresh forward root required')
    require(all(not (PRIOR_ROOT / name).exists() for name in
                ('build16', 'root-dispatch1', 'control-dispatch1', 'build-admission.approved.json')),
            'The original8f2 build is no longer an untouched predispatch checkpoint')
    require(all(not (PRIOR_A72_ROOT / name).exists() for name in
                ('build16', 'root-dispatch1', 'control-dispatch1', 'build-admission.approved.json')),
            'The actual a72 stage is no longer an untouched prebuild checkpoint')
    bundle = read_ref(plan['gitBundle'])
    template_path = read_ref(plan['buildAdmissionTemplate'])
    template = json.loads(template_path.read_bytes())
    controls['warmAdapter'].validate_retry(template)
    require(template['readyForBuild'] is False and template['appSourceSHA'] == args.accepted_source
            and template['pins'] == plan['pins'] and template['buildRoot'] == str(root)
            and template['sourceRoot'] == str(SOURCE) and template['appDerived'] == str(DERIVED)
            and template['forwardWarm']['targetSDKRevision'] == plan['sdkRevision'],
            'Source staging must emit an unapproved exact build draft')
    require(template['forwardWarm']['priorForwardStage'] == plan['priorForwardStage'],
            'The source and build plans must retain the same exact prior a72 stage')
    require(shutil.disk_usage(SOURCE).free >= FLOOR + STAGE_GROWTH, 'Staging envelope unavailable')
    root.mkdir(mode=0o700)
    stage = root / 'source-staging1'
    stage.mkdir(mode=0o700)
    report = {'protocol': 'pinkha-root-forward-warm-staging-v1', 'status': 'FAIL_FORWARD_WARM_STAGING',
              'startedAt': time.time(), 'sourceCommit': args.accepted_source, 'priorSource': BASELINE,
              'sourceRoot': str(SOURCE), 'appDerived': str(DERIVED), 'uiDerived': str(root / 'ui-derived'),
              'applicationBuilds': 0, 'nativeBuilds': 0, 'tests': 0,
              'historicalProcessGroupReprobes': 0, 'planSHA256': args.plan_sha256,
              'controllerSHA256': sha(__file__), 'originalIntermediatesAndPackagePathsReused': True,
              'originalPreservationSHA256': ORIGINAL15, 'failedPreservationSHA256': FAILED_RECEIPT,
              'firstFailure': None, 'secondaryErrors': [], 'processObservationCustodyBlocked': False}
    commands = None
    first = None
    try:
        commands = StageCommands(controls['lifecycle'], stage / 'owned-commands', plan['developerDir'])
        identity(commands, BASELINE, BASELINE_TREE)
        report['ownersBefore'] = census(controls, stage / 'owners-before.json', plan, report, commands)
        report['toolchainIntake'] = toolchain_intake(commands, plan, stage)
        report['priorRetention'] = existing_retention(plan, controls['preservation'])
        report['priorForwardStage'] = plan['priorForwardStage']
        report['priorForwardQualification'] = controls['warmAdapter'].wr_prior_forward(plan['priorForwardStage'])
        packages_before = controls['warmAdapter'].wr_packages(SOURCE, DERIVED)
        before_lock = (SOURCE / LOCK_RELATIVE).read_bytes()
        require(hashlib.sha256(before_lock).hexdigest() == LOCK_BEFORE
                and sha(SOURCE / 'Dependencies/Hanlin/.pinkha-source.json') == SDK_BEFORE,
                'Fresh baseline SDK/lock differs from the actual a72 stage')
        write(stage / 'packages-before.json', packages_before)
        native_inputs(plan, controls['originalStager'])
        commands.git('bundle', 'verify', str(bundle))
        report['currentBaselinePreservation'] = retain_current(
            controls['preservation'], root / 'forward-preservation1', packages_before)
        report['baselinePreservationSHA256'] = report['currentBaselinePreservation']['sha256']
        census(controls, stage / 'owners-before-fetch.json', plan, report, commands)
        census(controls, stage / 'owners-before-mutation.json', plan, report, commands)
        identity(commands, BASELINE, BASELINE_TREE)
        commands.git('fetch', '--no-tags', str(bundle), args.accepted_source, timeout=90)
        commands.git('merge-base', '--is-ancestor', BASELINE, args.accepted_source)
        require(commands.git('rev-parse', args.accepted_source + '^{tree}') == plan['appSourceTree'],
                'Exact target source tree differs')
        target_lock, _ = commands.run(
            ['/usr/bin/git', '--no-replace-objects', '-C', str(SOURCE), 'show',
             args.accepted_source + ':' + LOCK_RELATIVE], 'exact-target-lock', 60)
        require(hashlib.sha256(target_lock).hexdigest() == plan['pins']['packageResolvedSHA256'],
                'Target lock bytes differ before fast-forward')
        # The exact full lock relation is checked before and after the resolver.
        before_rows, target_rows = lock_rows(before_lock), lock_rows(target_lock)
        require(set(before_rows) == set(target_rows)
                and [name for name in before_rows if before_rows[name] != target_rows[name]]
                == ['torahinspectorkit'], 'Only one explicitly reviewed Kit lock change is permitted')
        census(controls, stage / 'owners-before-fast-forward.json', plan, report, commands)
        identity(commands, BASELINE, BASELINE_TREE)
        commands.git('merge', '--ff-only', '--no-edit', args.accepted_source, timeout=90)
        identity(commands, args.accepted_source, plan['appSourceTree'])
        pins = plan['pins']
        require(sha(SOURCE / 'Tools/Hanlin/source.json') == pins['hanlinSourcePinSHA256']
                and sha(SOURCE / 'Tools/Hanlin/prepare_sdk.py') == pins['sdkMaterializerSHA256'],
                'Final canonical SDK pin/materializer differs')
        require(json.loads((SOURCE / 'Tools/Hanlin/source.json').read_bytes())['revision'] == plan['sdkRevision'],
                'Final source does not pin the admitted SDK revision')
        sdk = SOURCE / 'Dependencies/Hanlin'
        require(sha(sdk / '.pinkha-source.json') == SDK_BEFORE, 'Original SDK changed before retention move')
        prior_sdk = root / 'retained-prior-sdkc0'
        require(not prior_sdk.exists() and not prior_sdk.is_symlink(), 'Prior SDK retention destination exists')
        sdk.rename(prior_sdk)
        commands.run([sys.executable, '-B', str(SOURCE / 'Tools/Hanlin/prepare_sdk.py'),
                      '--source', plan['hanlinReadOnlySourceRoot']], 'canonical-sdk-materialization', 300)
        commands.run([sys.executable, '-B', str(SOURCE / 'Tools/Hanlin/prepare_sdk.py'), '--check'],
                     'canonical-sdk-check', 60)
        require(sha(sdk / '.pinkha-source.json') == pins['sdkMaterializationReceiptSHA256'],
                'Actual new SDK marker differs from the immutable target input')
        require((SOURCE / LOCK_RELATIVE).read_bytes() == target_lock, 'Locked packages changed while staging SDK')
        census(controls, stage / 'owners-before-exact-resolution.json', plan, report, commands)
        resolve = ['xcodebuild', '-resolvePackageDependencies', '-project', str(SOURCE / 'Anytype.xcodeproj'),
                   '-scheme', 'Anytype', '-configuration', 'Debug-Anytype', '-derivedDataPath', str(DERIVED),
                   '-clonedSourcePackagesDirPath', str(DERIVED / 'SourcePackages'),
                   '-onlyUsePackageVersionsFromResolvedFile', '-disableAutomaticPackageResolution']
        report['packageResolutionCommand'] = resolve
        commands.run(resolve, 'resolve-exact-final-packages', 600)
        require((SOURCE / LOCK_RELATIVE).read_bytes() == target_lock, 'Resolver rewrote the immutable package lock')
        packages_after = controls['warmAdapter'].wr_packages(SOURCE, DERIVED)
        transition = package_transition(before_lock, target_lock, packages_before, packages_after)
        write(stage / 'package-transition.json', transition)
        native_inputs(plan, controls['originalStager'])
        require(sha(SOURCE / 'Tools/PinkhaDualEngineRuntime/source-permission-manifest.json')
                == pins['nativeSourceManifestSHA256'], 'Final source/native manifest differs')
        report['selectedCompilerSources'] = compiler_sources(plan, template)
        ui_source = Path(plan['uiDerivedCloneSource'])
        require(ui_source == PRIOR_ROOT / 'ui-derived', 'Only the untouched8f2 private UI cache is a candidate')
        ui_before = controls['preservation'].inventory(ui_source)
        write(stage / 'ui-cache-before.json', {'root': str(ui_source), 'entries': ui_before})
        report['uiCacheClone'] = controls['preservation'].clone_tree(ui_source, root / 'ui-derived', ui_before)
        require(controls['preservation'].inventory(root / 'ui-derived') == ui_before
                == controls['preservation'].inventory(ui_source), 'Full original UI cache APFS clone differs')
        inputs = root / 'source-inputs'
        inputs.mkdir(mode=0o700)
        helper = read_ref(plan['controls']['lifecycle'])
        with (inputs / 'combined_heart_semantics_owned_outcomes.py').open('xb') as stream:
            stream.write(helper.read_bytes())
        require(sha(inputs / 'combined_heart_semantics_owned_outcomes.py') == CONTROL_HASHES['lifecycle'],
                'Original producer lifecycle input differs')
        identity(commands, args.accepted_source, plan['appSourceTree'])
        report['ownersAfter'] = census(controls, stage / 'owners-after.json', plan, report, commands)
        require(controls['warmAdapter'].wr_prior_forward(plan['priorForwardStage'])
                == report['priorForwardQualification'], 'Prior a72 evidence changed during staging')
        commands.barrier()
        report.update(status='PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED',
                      finishedAt=time.time(), tree=plan['appSourceTree'],
                      canonicalSDKRevision=plan['sdkRevision'],
                      sdkReceiptSHA256=pins['sdkMaterializationReceiptSHA256'],
                      sourceManifestSHA256=pins['nativeSourceManifestSHA256'])
        stage_ref = write(stage / 'receipt.json', report)
        paths = {'intermediates': DERIVED / 'Build/Intermediates.noindex',
                 'sourcePackages': DERIVED / 'SourcePackages', 'sdkModules': DERIVED / 'SDKExplicitPrecompiledModules',
                 'products': DERIVED / 'Build/Products'}
        observed = {name: {'path': str(path), 'exists': path.is_dir(), 'symlink': path.is_symlink()}
                    for name, path in paths.items()}
        require(all(row['exists'] and not row['symlink'] for row in observed.values()), 'Warm cache leaves are absent')
        sizes = {}
        for name, path in paths.items():
            text, _ = commands.run(['/usr/bin/du', '-sk', str(path)], 'allocated-' + name.lower(), 60)
            sizes[name] = int(text.split()[0]) * 1024
        cache = {'protocol': 'pinkha-forward-warm-cache-qualification-v1', 'sourceCommit': args.accepted_source,
                 'baselineSourceSHA': BASELINE, 'stageReceiptSHA256': stage_ref['sha256'],
                 'priorForwardStage': plan['priorForwardStage'],
                 'stageSourceAndNativePreservationRetained': True,
                 'priorFailedSourceCommit': FAILED_SHA, 'failedPreservationSHA256': FAILED_RECEIPT,
                 'baselinePreservationSHA256': report['baselinePreservationSHA256'],
                 'historicalProcessGroupReprobes': 0, 'originalIntermediatesAndPackagePathsReused': True,
                 'invalidatedStageMetadata': [], 'applicationBuilds': 0, 'testsExecuted': 0,
                 'observedPaths': observed, 'observedSizes': sizes, 'packageState': packages_after,
                 'packageTransition': transition, 'estimateNewAppPhaseBytes': 6 * 1024 ** 3,
                 'emergencyFloorBytes': FLOOR, 'concurrentGrowthAllowanceBytes': 512 * 1024 ** 2,
                 'observedAt': time.time(), 'freeBytes': shutil.disk_usage(root).free,
                 'estimateReason': 'Original conservative warm6GiB estimate; no claim of a measured future peak.'}
        cache_dir = root / 'cache-requalification1'
        cache_dir.mkdir(mode=0o700)
        cache_ref = write(cache_dir / 'receipt.json', cache)
        template.update(readyForBuild=False, sourceStaging=stage_ref, cacheQualification=cache_ref)
        template['forwardWarm']['currentBaselinePreservation'] = report['currentBaselinePreservation']
        write(root / 'build-admission.draft.json', template)
        print(json.dumps({'status': report['status'], 'stageReceipt': stage_ref, 'cacheReceipt': cache_ref,
                          'readyForBuild': False, 'applicationBuilds': 0, 'testsExecuted': 0}))
        return 0
    except BaseException as exc:
        first = exc
        if report['firstFailure'] is None:
            report['firstFailure'] = {'type': type(exc).__name__, 'message': str(exc)}
        else:
            report['secondaryErrors'].append({'phase': 'forward-staging', 'type': type(exc).__name__, 'message': str(exc)})
        report['status'] = 'FAIL_FORWARD_WARM_STAGING'
        raise
    finally:
        if first is not None:
            # No Git, process probes, cleanup or disk command may start here.
            # Preserve the first failure even if the terminal evidence write fails.
            report['finishedAt'] = time.time()
            if commands is not None:
                report['ownedGroups'] = list(commands.owner.groups)
                report['latchedAbsentGroups'] = sorted(commands.owner.absent_groups)
                report['allKnownGroupsClosed'] = (not report['processObservationCustodyBlocked']
                    and set(commands.owner.groups) <= commands.owner.absent_groups)
            try:
                write(stage / 'failure.json', report)
            except BaseException as terminal:
                print(json.dumps({'status': 'FAIL_TERMINAL_RECEIPT_WRITE', 'firstFailure': report['firstFailure'],
                                  'terminalWriteFailure': {'type': type(terminal).__name__, 'message': str(terminal)}}),
                      file=sys.stderr)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt('Owned forward staging interrupted by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    raise SystemExit(main())
