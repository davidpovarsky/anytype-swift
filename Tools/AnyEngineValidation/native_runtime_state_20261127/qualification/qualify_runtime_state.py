#!/usr/bin/env python3
"""Qualify eighteen new runtime-observation events and one coherent Any product.

The immutable actual C13 source is copied into one exclusive development output.
Only the reviewed runtime-state overlay is composed there. No retained account,
old test method, C313 worktree, C3 Swift cache, quota activation or HTTP account
process is opened. The one new SDK fixture owns fresh identities and data.
Real HTTP current-authority verification is a separate, read-only obligation.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import sys
import time
import types

sys.dont_write_bytecode = True
MIB, GIB = 1024**2, 1024**3
HERE = Path(__file__).absolute().parent
INPUT = HERE.parent
PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
C13 = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127')
BASE = C13/'qualification-attempt1/source'
COMPLETION = C13/'qualification-completion-attempt1'
BASE_RECEIPT_SHA = 'a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d'
BASE_INPUTS_SHA = '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0'
BASE_MANIFEST_SHA = 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3'
BASE_FAILURE_SHA = '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b'
BASE_BINARY_SHA = 'b6fb8137bfce60e5af23e5c912ed133ca0e15fc10c368d2eabddc0641379b482'
BASE_MODULE_SHA = 'e0b3fc887d2fbfa4f81ff3f32d1a2d438aadefedd2357643fe0d1208cd1d99c1'
DRAFT_SHA = 'f042531d9fb204aa7d92e9c73e375e839753b46b796330c7c2cce8d79a58daa4'
PATCH_SHA = '3d6a7d1175429f2dedf4993fbaf47c91ff8cfbaf9202e2c6ef1de15efcf7c478'
WIRE_SHA = '3d13cb658cb45cf6b690c0d052aa6ebdae06174ec72c7e1826ff0f04019f896d'
PLAN_SHA = '2b8749bea0f82f4fcacabe73715ba8caf8b4c7851ccd8a6f884cfdf6d7400439'
COMPOSED_SHA = '12277084b55ab7ff17f865711e15cb3580fca253eb51ec114c0fb707f24a56b9'
FORMAT = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-gofmt-20261127-attempt1/result.json')
FORMAT_SHA = '070c6e482c923a7428ff7b6580a0acefa7ec0097844df515cc2b0a1f5d79e109'
FORMAT_WORKER_SHA = 'bdb21b0817be7602e8b9f812d1ca809b635a84cb292804bdaaf86335dcc314d0'
GOFMT_SHA = '3ca5e23c92e957338205edb7c8a19a0c4f211b2cf606e21171925f3001d12825'
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNED_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
OWNED_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_PROOF = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json')
OFFLINE_PROOF_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
SECCOMP = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
SECCOMP_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
ROOT_FLOOR, DEV_FLOOR = 2*GIB, 512*MIB
OUTPUT_CAP, CACHE_CAP, LOG_CAP = 640*MIB, 512*MIB, 16*MIB
MAIN_SECONDS, FINAL_SECONDS = 900, 90
GROUPS = {
    'sdk-units': {
        'github.com/anyproto/any-sync-sdk/internal/files/readguard': (
            'TestRuntimeObservationBindsActualReaderAndGuestHead',
            'TestRuntimeObservationWithholdsAfterCurrentAuthorityChanges',
            'TestRuntimeObservationUsesOriginalACLIsEmptyIncludingInvites'),
        'github.com/anyproto/any-sync-sdk/internal/spaceimpl': (
            'TestRuntimeCoordinatorMissingLimitsAndExplicitZeroStayDistinct',
            'TestRuntimeCoordinatorRejectsMalformedAndForeignCachedAnswers',
            'TestRuntimeCoordinatorPersistsSuccessfulAnswerAcrossOfflineReopen',
            'TestRuntimeCoordinatorCoalescesFetchAndDrainsOwnerCancellation',
            'TestRuntimeAccessNeedsPositiveOriginalPersonalProvenance'),
        'github.com/anyproto/any-sync-sdk/internal/syncstatus': (
            'TestRuntimeSyncObservationPreservesOriginalDomainsAndPrecedence',
            'TestRuntimeSyncObservationDistinguishesInheritedAndUnobserved')},
    'server-units': {'github.com/anyproto/any/internal/server': (
        'TestRuntimeStateWirePreservesAbsenceZeroAndOriginalAccessDomain',
        'TestRuntimeObjectWireDoesNotCastSDKSyncIntoHeartDomain',
        'TestRuntimeStateRoutesAdvertiseOnlyVersionedOptionalReads')},
    'fresh-sdk': {'github.com/anyproto/any-sync-sdk': (
        'TestRuntimeStateFreshScopeAndSyncStopAtSignedRemoval',)},
}
SUBCASES = {'TestRuntimeObservationWithholdsAfterCurrentAuthorityChanges': (
    'signed-removal', 'signed-head', 'account-retirement', 'space-retirement')}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def physical(path, directory=False):
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'physical canonical path required')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'regular physical input kind')
    return info


def frozen(path, maximum=4*MIB):
    before = physical(path)
    require(0 <= before.st_size <= maximum, 'bounded immutable input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno()) == before, 'immutable descriptor identity')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno()) == before, 'immutable descriptor changed')
    require(path.lstat() == before and len(raw) == before.st_size, 'immutable pathname or bytes changed')
    return raw


def relative(name):
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and str(path) == name and '..' not in path.parts and '\\' not in name,
            'closed source-relative path')
    return path


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive(path, raw, mode=0o600):
    physical(path.parent, True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())
    sync_directory(path.parent)
    require(frozen(path, max(1, len(raw))) == raw, 'exclusive complete byte readback')


def source_inventory(root, checkpoint):
    physical(root, True)
    files, modes, pending = {}, {}, [root]
    count = 0
    while pending:
        checkpoint()
        directory = pending.pop()
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
        try:
            with os.scandir(fd) as rows:
                names = sorted(row.name for row in rows)
        finally:
            os.close(fd)
        for name in names:
            checkpoint()
            member = directory/name
            info = member.lstat()
            count += 1
            require(count <= 10000 and not stat.S_ISLNK(info.st_mode), 'bounded source without aliases')
            if stat.S_ISDIR(info.st_mode):
                pending.append(member)
            else:
                require(stat.S_ISREG(info.st_mode), 'regular source member')
                key = member.relative_to(root).as_posix()
                files[key] = identity(frozen(member, 32*MIB))
                modes[key] = stat.S_IMODE(info.st_mode)
    return {'files': files, 'modes': modes}


def allocation(root, mutable=False):
    physical(root, True)
    count, total, seen, pending = 0, 0, set(), [root]
    began = time.monotonic()
    while pending:
        directory = pending.pop()
        try:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
        except FileNotFoundError:
            if mutable:
                continue
            raise
        try:
            with os.scandir(fd) as rows:
                names = [row.name for row in rows]
        finally:
            os.close(fd)
        for name in [None]+names:
            member = directory if name is None else directory/name
            try:
                info = member.lstat()
            except FileNotFoundError:
                if mutable:
                    continue
                raise
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'no output/cache special files or aliases')
            key = (info.st_dev, info.st_ino)
            if key not in seen:
                total += max(info.st_size, info.st_blocks*512) if stat.S_ISREG(info.st_mode) else info.st_blocks*512
                seen.add(key)
            if name is not None and stat.S_ISDIR(info.st_mode):
                pending.append(member)
            if name == 'original.log':
                require(info.st_size <= LOG_CAP, 'bounded original command log')
            count += 1
            require(count <= 100000 and time.monotonic()-began <= 8, 'finite allocation census')
    return total


def normal(row):
    return row.get('exitCode') == 0 and row.get('processGroupAbsent') is True and not row.get('forcedCleanup') and \
        row.get('cleanupErrors') == [] and row.get('signals') == []


def parse_events(raw, packages):
    require(len(raw) <= LOG_CAP, 'bounded Go event stream')
    expected = Counter()
    for package, methods in packages.items():
        for method in methods:
            expected[(package, method)] += 1
            for child in SUBCASES.get(method, ()):
                expected[(package, method+'/'+child)] += 1
    starts, passes, package_passes = Counter(), Counter(), Counter()
    for line in raw.splitlines():
        require(len(line) <= 2*MIB, 'bounded Go event line')
        if not line:
            continue
        event = json.loads(line)
        require(isinstance(event, dict) and event.get('Package') in packages, 'every event belongs to a selected package')
        action, name = event.get('Action'), event.get('Test')
        require(action not in ('skip', 'fail'), 'no skipped or failed method/package')
        if name is not None:
            key = (event['Package'], name)
            require(key in expected, 'no old or undeclared test/subcase')
            if action == 'run':
                starts[key] += 1
            if action == 'pass':
                passes[key] += 1
        elif action == 'pass':
            package_passes[event['Package']] += 1
    require(starts == passes == expected and package_passes == Counter({p: 1 for p in packages}),
            'one exact run/pass per new method/subcase and package')
    return {'runs': sum(starts.values()), 'passes': sum(passes.values()), 'skips': 0, 'failures': 0,
            'methods': [{'package': p, 'name': n} for p, n in sorted(expected)],
            'packages': sorted(package_passes)}


def main():
    require(not sys.flags.optimize, 'qualification requires assertions enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(os.geteuid() == 0 and os.uname().nodename == 'torah-social', 'authorized Oracle host')
    output = args.output
    require(output.parent == PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', output.name) and
            int(output.name.removeprefix('attempt')) >= 7, 'new existing-constructor namespace only')
    physical(PARENT, True)
    own = Path(__file__).absolute()
    own_raw = frozen(own)  # Capture the actual controller before the first mkdir.
    require(not os.path.lexists(output), 'exclusive new attempt; preserve all previous results')
    os.umask(0o077)
    output.mkdir(mode=0o700)
    os.chmod(output, 0o700)  # Clear inherited SGID; keep the fixture's strict0700 guard.
    sync_directory(PARENT)
    exclusive(output/'result.json', b'{}\n')
    began, final_deadline, last_census = time.monotonic(), None, 0.0
    serial, cache_before = 0, None
    base_before = source_before = None
    source, temporary, fixtures = output/'source', output/'temporary', output/'fixtures'
    admitted = {str(own): {'identity': identity(own_raw), 'maximum': 4*MIB}}
    result = {'protocol': 'pinkha-native-runtime-state-qualification-v1', 'status': 'RUNNING',
        'controller': identity(own_raw), 'processes': [], 'errors': [], 'completionErrors': [], 'mutations': [],
        'priorTestMethodsReexecuted': 0, 'retainedPrivateAccountInputs': 0, 'privateRecordExports': 0,
        'C313SourceWrites': 0, 'C3CacheWrites': 0, 'nativeCLIAccountProcesses': 0, 'nativeProductBuilds': 0,
        'nativeHTTPRuntimeRoutes': 'NOT_RUN_SEPARATE_READ_ONLY_FOUR_DECISIONS_REQUIRED',
        'personalProvenance': 'UNAVAILABLE_EXPLICIT_NULL', 'heartSyncDateProduced': False,
        'cloudQuotaActivationOrAccessCodeCalls': 0,
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
            'rootAdmissionReserveBytes': 32*MIB, 'developmentAdmissionReserveBytes': OUTPUT_CAP+CACHE_CAP,
            'ownedOutputCapBytes': OUTPUT_CAP, 'observedSharedCacheGrowthCapBytes': CACHE_CAP,
            'controlledOutputsOnDevelopmentOnly': True, 'globalRootWritesMeasured': False,
            'allocationIsEstimateNotMeasuredNewPeak': True, 'controllerSeconds': MAIN_SECONDS,
            'finalVerificationSeconds': FINAL_SECONDS, 'requiredOuterSeconds': 1050,
            'goWorkers': 2, 'goMemoryLimit': '1GiB', 'memoryAdmissionBytes': 3*GIB,
            'allocationCensusMinimumIntervalSeconds': 1,
            'estimateBasis': 'Reuse actual C13 cache/toolchain; 17.6 MB source, four unit packages, one fresh SDK fixture, and one78MB-class native product. Original C13 observed405577728B cache growth under512MiB. New peak remains unmeasured.'}}

    def save_json(path, value):
        nonlocal serial
        require(path.is_relative_to(output), 'owned evidence only')
        raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        require(len(raw) <= 8*MIB, 'bounded receipt content')
        serial += 1
        stage = path.with_name(path.name+'.pending-'+str(serial))
        exclusive(stage, raw)
        os.replace(stage, path)
        sync_directory(path.parent)

    def save():
        result['seconds'] = time.monotonic()-began
        save_json(output/'result.json', result)

    def checkpoint(admission=False):
        require(time.monotonic() < (final_deadline if final_deadline is not None else began+MAIN_SECONDS),
                'finite qualification/final audit')
        require(not (output/'abort').exists(), 'owned abort requested')
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', ROOT_FLOOR, 32*MIB), ('development', DEV_FLOOR, OUTPUT_CAP+CACHE_CAP)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
            require(free[name] >= floor+(reserve if admission else 0), name+' unchanged reserve/floor')
        return free

    def guard(admission=False, force=False):
        nonlocal last_census
        free = checkpoint(admission)
        if force or admission or time.monotonic()-last_census >= 1:
            used = allocation(output, mutable=True)
            result['peakOwnedOutputBytes'] = max(used, result.get('peakOwnedOutputBytes', 0))
            require(used <= OUTPUT_CAP, 'all owned source/test/fixture/temp/product/evidence allocation')
            if cache_before is not None:
                require(CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET, 'unchanged admitted cache alias')
                growth = max(0, allocation(CACHE_TARGET, mutable=True)-cache_before)
                result['peakObservedCacheGrowthBytes'] = max(growth, result.get('peakObservedCacheGrowthBytes', 0))
                require(growth <= CACHE_CAP, 'measured shared-cache growth cap')
            last_census = time.monotonic()
        checkpoint()
        return free

    def observe():
        try:
            guard()
            return None
        except BaseException as error:
            return type(error).__name__+': '+str(error)

    def pin(path, sha, maximum=4*MIB, mode=None):
        checkpoint()
        raw = frozen(path, maximum)
        require(identity(raw)['sha256'] == sha, 'exact frozen public input/product hash')
        admitted[str(path)] = {'identity': identity(raw), 'maximum': maximum}
        if mode is not None:
            require(stat.S_IMODE(physical(path).st_mode) == mode, 'pinned executable mode')
            admitted[str(path)]['mode'] = mode
        return raw

    def command(label, argv, cwd, environment, seconds):
        guard(force=True)
        def persist(path, value):
            require(path.parent == output/label and path.name in ('started.json', 'result.json'), 'owned command journal')
            save_json(path, value)
            save()
        log, row = owned.run(output/label, argv, cwd, environment, seconds, observe, persist,
            lambda path: identity(frozen(path, LOG_CAP))['sha256'], result['processes'])
        require(normal(row), 'normal exit and latched positive owned-group absence')
        guard(force=True)
        save()
        return log, row

    def validate_inputs():
        for name, wanted in admitted.items():
            checkpoint()
            member = Path(name)
            require(identity(frozen(member, wanted['maximum'])) == wanted['identity'], 'admitted bytes changed')
            if 'mode' in wanted:
                require(stat.S_IMODE(physical(member).st_mode) == wanted['mode'], 'admitted executable mode changed')
        return True

    def interrupted(number, _frame):
        raise RuntimeError('runtime-state qualification interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        result['initialFreeBytes'] = guard(admission=True, force=True)
        require(physical(output, True).st_dev == physical(Path('/mnt/development'), True).st_dev,
                'owned output lives on development')
        memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                          if line.startswith('MemAvailable:')))*1024
        require(memory >= 3*GIB, 'unchanged3GiB memory admission')
        result['memAvailableBefore'] = memory
        draft = json.loads(pin(INPUT/'SOURCE_DRAFT2.json', DRAFT_SHA))
        pin(INPUT/'runtime-state.draft2.patch', PATCH_SHA)
        pin(INPUT/'WIRE_CONTRACT.json', WIRE_SHA)
        plan = json.loads(pin(HERE/'QUALIFICATION_PLAN.json', PLAN_SHA))
        candidate = json.loads(pin(HERE/'COMPOSED1638.json', COMPOSED_SHA))
        require(draft['status'] == 'SOURCE_ONLY_CANONICALLY_FORMATTED_NOT_COMPILED_OR_RUN' and
                draft['wireSHA256'] == WIRE_SHA and draft['newParentMethods'] == 14 and draft['newSubcases'] == 4 and
                draft['futureExactRunAndPassEvents'] == 18 and len(draft['files']) == 15 and
                draft['productionPaths'] == 10 and draft['testPaths'] == 5 and
                draft['addedPaths'] == 12 and draft['replacedPaths'] == 3, 'reviewed15-path18-event source scope')
        require(plan['sourceDraftSHA256'] == DRAFT_SHA and plan['sourcePatchSHA256'] == PATCH_SHA and
                plan['wireSHA256'] == WIRE_SHA and plan['baseC13CompletionSHA256'] == BASE_RECEIPT_SHA and
                plan['baseC13CompiledInputsSHA256'] == BASE_INPUTS_SHA and plan['ownedCommands'] == 6 and
                plan['exactRunPassEvents'] == 18 and plan['priorMethodsRerun'] == 0,
                'closed planned source/proof/command scope')
        require(plan['subcases'] == {n: list(v) for n, v in SUBCASES.items()} and set(plan['groups']) == set(GROUPS), 'exact new subcase/group selection')
        for label, packages in GROUPS.items():
            require(plan['groups'][label]['packages'] == {p: list(v) for p, v in packages.items()}, 'exact new package/method selection')

        formatted = json.loads(pin(FORMAT, FORMAT_SHA))
        require(formatted['status'] == 'PASS_SOURCE_FORMAT15_NOT_COMPILED_NOT_TESTED' and
                formatted['workerSHA256'] == FORMAT_WORKER_SHA and formatted['helperSHA256'] == OWNED_SHA and
                formatted['errors'] == formatted['completionErrors'] == [] and
                formatted['allOwnedGroupsPositivelyAbsent'] is True and len(formatted['commands']) == 1 and
                all(normal(row) for row in formatted['commands']) and formatted['compilerInvocations'] == 0 and
                formatted['nativeSDKInvocations'] == 0 and formatted['accountInputs'] == 0,
                'actual source-only15-format closure')
        worker = formatted['worker']
        require(worker['status'] == 'PASS_SOURCE_FORMATTING_REQUIRES_OUTER_CLOSURE' and
                worker['tool']['sha256'] == GOFMT_SHA and len(worker['rows']) == 15 and
                worker['sourceFileWrites'] == worker['compilerInvocations'] == worker['nativeSDKInvocations'] ==
                worker['accountInputs'] == 0 and formatted['helperUnchangedAtCompletion'] is True,
                'exact canonical formatter/source count and unchanged source-only scope')
        overlay = {}
        for row in worker['rows']:
            name = row['path']
            require(name in draft['files'] and name not in overlay and row['exitCode'] == 0 and
                    row['sameOwnedGroupAtStart'] is True and row['stderr'] == '' and
                    row['output'] == draft['files'][name]['after'], 'one qualified output per path')
            raw = pin(INPUT/'overlay'/relative(name), row['output']['sha256'])
            require(identity(raw) == row['output'] and base64.b64decode(row['source'], validate=True) == raw,
                    'local overlay equals actual canonical stdout bytes')
            overlay[name] = raw

        original = json.loads(pin(C13/'qualification-attempt1/result.json', BASE_FAILURE_SHA))
        prior = json.loads(pin(COMPLETION/'result.json', BASE_RECEIPT_SHA))
        base_input = json.loads(pin(COMPLETION/'compiled-source-inputs.json', BASE_INPUTS_SHA))
        base_map = json.loads(pin(COMPLETION/'source-manifest.json', BASE_MANIFEST_SHA))['files']
        require(original['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
                prior['status'] == 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT' and
                prior['errors'] == prior['completionErrors'] == [] and prior['allOwnedGroupsPositivelyAbsent'] is True and
                len(prior['processes']) == 4 and all(normal(row) for row in prior['processes']) and
                prior['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True, 'originalSource': True} and
                prior['retainedQualification']['receiptSHA256'] == BASE_FAILURE_SHA and
                prior['retainedActualMethodCount'] == 8 and prior['newActualMethodCount'] == 5 and
                prior['sdk-eight']['runs'] == prior['sdk-eight']['passes'] == 8 and
                prior['server-five']['runs'] == prior['server-five']['passes'] == 5 and
                prior['priorTestMethodsReexecuted'] == 0, 'actual C13 retained8/new5; original overallFAIL unchanged')
        require(prior['compiledSourceInputSHA256'] == BASE_INPUTS_SHA and prior['sourceManifestSHA256'] == BASE_MANIFEST_SHA and
                prior['sourceRoot'] == str(BASE) and len(base_map) == 1625 and len(base_input['files']) == 1626,
                'actual coherentC13 compiled source')
        config = prior['separatelyDeclaredRuntimeConfig']
        require(config == {'path': 'staging.yml', 'bytes': 1137,
                'sha256': 'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'}, 'original separately admitted fixture config')
        expected_base = dict(base_map, **{config['path']: {k: config[k] for k in ('bytes', 'sha256')}})
        require(base_input['files'] == expected_base, 'no unjoined source extension')
        base_before = source_inventory(BASE, checkpoint)
        require(base_before == base_input, 'full actual1626 source bytes and modes before any compile')
        base_binary = prior['nativeBinary']
        require(base_binary == {'path': str(COMPLETION/'any'), 'bytes': 78262881,
                'mode': 0o700, 'sha256': BASE_BINARY_SHA}, 'exact prior standalone product')
        pin(COMPLETION/'any', BASE_BINARY_SHA, 128*MIB, 0o700)
        base_metadata = pin(COMPLETION/'native-metadata/original.log', BASE_MODULE_SHA, 65536)
        require(identity(base_metadata) == prior['binaryModuleMetadata'], 'actual prior native module metadata')
        result['retainedC13'] = {'completionSHA256': BASE_RECEIPT_SHA, 'originalFailureSHA256': BASE_FAILURE_SHA,
            'compiledSourceInputsSHA256': BASE_INPUTS_SHA, 'sourceManifestSHA256': BASE_MANIFEST_SHA,
            'actualMethodsRetained': {'sdk': 8, 'server': 5}, 'priorMethodReexecution': 0,
            'historicalProcessIDsProbedOrSignaled': False, 'binary': base_binary}

        expected = dict(expected_base)
        expected_modes = dict(base_input['modes'])
        for name, change in draft['files'].items():
            require(expected_base.get(name) == change['before'], 'exact C13/runtime source before-image join')
            expected[name] = change['after']
            expected_modes[name] = 0o644
        require(candidate['sourceDraftSHA256'] == DRAFT_SHA and candidate['baseCompiledInputsSHA256'] == BASE_INPUTS_SHA and
                candidate['files'] == expected and len(expected) == 1638 and
                sum(n.startswith(SDK_PREFIX) for n in expected) == 750, 'complete C13+runtime1638/SDK750 composition')
        source.mkdir(mode=0o700)
        os.chmod(source, 0o700)
        result['mutations'].append({'operation': 'compose-new-1638-public-source', 'state': 'dispatching'})
        save()
        for name, wanted in sorted(expected.items()):
            checkpoint()
            raw = overlay[name] if name in overlay else frozen(BASE/relative(name), 32*MIB)
            require(identity(raw) == wanted, 'complete current source bytes')
            destination = source/relative(name)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            exclusive(destination, raw, expected_modes[name])
        source_before = source_inventory(source, checkpoint)
        require(source_before == {'files': expected, 'modes': expected_modes}, 'complete isolated source readback')
        save_json(output/'compiled-source-inputs.json', source_before)
        save_json(output/'source-manifest.json', candidate)
        result['compiledSourceInputSHA256'] = identity(frozen(output/'compiled-source-inputs.json'))['sha256']
        result['sourceManifestSHA256'] = identity(frozen(output/'source-manifest.json'))['sha256']
        result['sourceDraftSHA256'] = DRAFT_SHA
        result['sourceRoot'] = str(source)
        result['sourceFiles'] = 1638
        result['sdkSourceFiles'] = 750
        result['sourceComposition'] = {'baseFiles': 1626, 'changed': 15, 'added': 12, 'replaced': 3,
                                     'baseSDKFiles': 741, 'newSDKFiles': 750, 'C13MethodsReexecuted': 0}
        result['mutations'][-1]['state'] = 'completed'

        helper = pin(HERE/'owned_swift_commands.py', OWNED_SHA)
        lifecycle = json.loads(pin(OWNED_PROOF, OWNED_PROOF_SHA))
        require(lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and
                lifecycle['helperSHA256'] == OWNED_SHA and len(lifecycle['methods']) == 5 and
                all(row['status'] == 'PASS' for row in lifecycle['methods']) and
                lifecycle['allOwnedGroupsPositivelyAbsent'] is True, 'actual unchanged owner-helper lifecycle proof')
        owned = types.ModuleType('runtime_state_owned_commands')
        exec(compile(helper, str(HERE/'owned_swift_commands.py'), 'exec'), owned.__dict__)
        pin(OFFLINE, OFFLINE_SHA, 65536)
        pin(SECCOMP, SECCOMP_SHA)
        policy = json.loads(pin(OFFLINE_PROOF, OFFLINE_PROOF_SHA))
        require(policy['offlinePolicy']['helperSHA256'] == OFFLINE_SHA and
                policy['offlinePolicy']['baselineTCPReachable'] is True and
                policy['offlinePolicy']['baselineUDPReceived'] is True and
                policy['offlinePolicy']['controls']['librarySHA256'] == SECCOMP_SHA and
                policy['offlinePolicy']['controls']['tcpErrno'] == policy['offlinePolicy']['controls']['udpErrno'] == 1 and
                all(policy['offlinePolicy']['controls'][name] is True for name in
                    ('tcpDenied', 'udpDenied', 'noNewPrivileges', 'seccompFilterActive')), 'actual original OS-denial control schema')
        require(CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET, 'existing admitted Go cache location')
        physical(CACHE_TARGET, True)
        cache_before = allocation(CACHE_TARGET, mutable=True)
        result['cacheAllocationBefore'] = cache_before
        for directory in (temporary, fixtures):
            directory.mkdir(mode=0o700)
            os.chmod(directory, 0o700)
            sync_directory(directory.parent)
        require(stat.S_IMODE(physical(fixtures, True).st_mode) == 0o700, 'unchanged private fresh-fixture root guard')
        environment = {key: value for key, value in os.environ.items() if not key.startswith(('GO', 'CGO_', 'ANY_', 'PINKHA_', 'PYTHON'))}
        environment.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE),
            GOMODCACHE='/root/go/pkg/mod', GOTMPDIR=str(temporary), TMPDIR=str(temporary), CGO_ENABLED='1',
            GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off', PYTHONDONTWRITEBYTECODE='1',
            PINKHA_FRESH_FILES_FIXTURE_ROOT=str(fixtures))
        known_go = prior['goToolchain']
        for tool in [known_go['driver'], *known_go['tools'].values()]:
            require(identity(pin(Path(tool['path']), tool['sha256'], 128*MIB)) ==
                    {k: tool[k] for k in ('bytes', 'sha256')}, 'exact Go driver/compiler/linker')
        native_tools = prior['currentNativeCompilerObservation']
        require(set(native_tools['explicitEnvironment']) == {'CC', 'CXX', 'AR'} and
                set(native_tools['tools']) == {'CC', 'CXX', 'AR'}, 'actual C13 native compiler observation')
        for name, tool in native_tools['tools'].items():
            require(native_tools['explicitEnvironment'][name] == tool['path'], 'physical pinned native compiler')
            require(identity(pin(Path(tool['path']), tool['sha256'], 8*MIB, tool['mode'])) ==
                    {k: tool[k] for k in ('bytes', 'sha256')}, 'exact C13 compiler binary')
        environment.update(native_tools['explicitEnvironment'])
        environment['PATH'] = native_tools['PATH']
        python = Path(sys.executable).resolve(strict=True)
        python_raw = frozen(python, 32*MIB)
        admitted[str(python)] = {'identity': identity(python_raw), 'maximum': 32*MIB}
        result['OSExecPython'] = {'path': str(python), **identity(python_raw)}
        result['OSPolicy'] = {'helperSHA256': OFFLINE_SHA, 'librarySHA256': SECCOMP_SHA,
                             'actualOriginalControlReceiptSHA256': OFFLINE_PROOF_SHA,
                             'appliedBeforeEveryTestCommand': True, 'newFreshFixtureRequiresLiveEPERM': True}
        driver = known_go['driver']['path']
        fields = ['GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH',
                  'CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR']
        metadata_log, _ = command('toolchain', [driver, 'env', '-json', *fields], source, environment, 15)
        metadata = json.loads(frozen(metadata_log, 65536))
        require({key: metadata[key] for key in known_go['metadata']} == known_go['metadata'] and
                all(metadata[key] == environment[key] for key in ('CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR')),
                'actual compiler metadata equals exact admitted tools/environment')
        result['goToolchain'] = known_go
        result['currentNativeCompilerObservation'] = {'tools': native_tools['tools'], 'metadata': metadata,
                'explicitEnvironment': native_tools['explicitEnvironment'], 'PATH': environment['PATH']}
        result['environment'] = {key: environment[key] for key in ('GOTOOLCHAIN', 'GOMAXPROCS', 'GOMEMLIMIT',
            'GOCACHE', 'GOMODCACHE', 'GOTMPDIR', 'TMPDIR', 'CGO_ENABLED', 'GOWORK', 'GOFLAGS', 'GOPROXY',
            'GOSUMDB', 'CC', 'CXX', 'AR', 'PATH', 'PINKHA_FRESH_FILES_FIXTURE_ROOT')}
        for label, packages in GROUPS.items():
            require(source_inventory(source, checkpoint) == source_before, 'unchanged full source before each new selection')
            spec = plan['groups'][label]
            cwd = source/SDK_PREFIX if spec['cwd'] == 'sdk' else source
            methods = sorted(method for group in packages.values() for method in group)
            argv = [str(python), '-B', str(OFFLINE), '--exec', driver, 'test', '-json', '-count=1', '-p', '2',
                    '-parallel=1', '-timeout='+spec['testTimeout'], '-run', '^('+'|'.join(methods)+')$', *packages]
            log, _ = command(label, argv, cwd, environment, spec['commandSeconds'])
            raw = frozen(log, LOG_CAP)
            result.setdefault('rawLogs', {})[label] = {'path': str(log), **identity(raw)}
            result[label] = parse_events(raw, packages)
            save()
        require(sum(result[label]['runs'] for label in GROUPS) == 18 and
                sum(result[label]['passes'] for label in GROUPS) == 18, 'exact14 parents plus4 subcases')
        require(sorted(path.name for path in fixtures.iterdir()) == list(GROUPS['fresh-sdk']['github.com/anyproto/any-sync-sdk']),
                'one wholly fresh SDK fixture, no prior account input')
        result['actualMethods'] = {'parents': 14, 'subcases': 4, 'runs': 18, 'passes': 18,
                                 'skips': 0, 'oldMethodsRerun': 0, 'freshSDKMethods': 1}
        result['actualFreshSDKOSDenialVerified'] = True
        binary = output/'any'
        result['mutations'].append({'operation': 'build-one-coherent-native-product', 'state': 'dispatching'})
        save()
        command('native-build', [driver, 'build', '-p', '2', '-o', str(binary), './cmd/any'], source, environment, 240)
        result['nativeProductBuilds'] = 1
        result['mutations'][-1]['state'] = 'completed'
        raw = frozen(binary, 128*MIB)
        mode = stat.S_IMODE(physical(binary).st_mode)
        require(raw.startswith(b'\x7fELF') and mode & 0o111, 'one actual standalone native executable')
        result['nativeBinary'] = {'path': str(binary), 'mode': mode, **identity(raw)}
        admitted[str(binary)] = {'identity': identity(raw), 'maximum': 128*MIB, 'mode': mode}
        module_log, _ = command('native-metadata', [driver, 'version', '-m', str(binary)], source, environment, 15)
        module = frozen(module_log, 65536)
        require(module.splitlines()[1:] == base_metadata.splitlines()[1:] and
                known_go['metadata']['GOVERSION'].encode() in module.splitlines()[0] and
                b'github.com/anyproto/anytype-heart' not in module, 'same original standalone module/toolchain graph')
        result['binaryModuleMetadata'] = identity(module)
        result['standaloneAnySDKProducerNotEmbeddedHeart'] = True
        result['status'] = 'PASS_RUNTIME_STATE18_AND_ONE_C13_RUNTIME_NATIVE_PRODUCT'
    except BaseException as error:
        result['status'] = 'FAIL_RUNTIME_STATE_QUALIFICATION_PRESERVED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        # Only helper-latched observations: never probe or signal a historical PID.
        result['allOwnedGroupsPositivelyAbsent'] = bool(result['processes']) and all(
            row.get('processGroupAbsent') is True for row in result['processes'])
        final_deadline = time.monotonic()+FINAL_SECONDS
        for label, available, action in [
            ('declaredInputsAndProducts', True, validate_inputs),
            ('originalC13Source', base_before is not None, lambda: source_inventory(BASE, checkpoint) == base_before),
            ('compiledSource', source_before is not None, lambda: source_inventory(source, checkpoint) == source_before),
        ]:
            if not available:
                result.setdefault('finalIntegrity', {})[label] = 'NOT_ADMITTED'
                continue
            try:
                checkpoint()
                require(action(), label+' changed during qualification')
                result.setdefault('finalIntegrity', {})[label] = True
            except BaseException as error:
                result['status'] = 'FAIL_RUNTIME_STATE_QUALIFICATION_PRESERVED'
                result['completionErrors'].append({'scope': label, 'type': type(error).__name__, 'message': str(error)})
        try:
            result['finalFreeBytes'] = guard(force=True)
            if result['status'].startswith('PASS_'):
                require(len(result['processes']) == 6 and all(normal(row) for row in result['processes']) and
                        result['allOwnedGroupsPositivelyAbsent'] is True and
                        all(value is True for value in result['finalIntegrity'].values()) and
                        result['nativeProductBuilds'] == 1 and result['errors'] == result['completionErrors'] == [],
                        'six normal owned commands and complete source/product finalization')
        except BaseException as error:
            result['status'] = 'FAIL_RUNTIME_STATE_QUALIFICATION_PRESERVED'
            result['completionErrors'].append({'scope': 'final-resources-and-closure', 'type': type(error).__name__, 'message': str(error)})
        try:
            save()
        except BaseException as error:
            result['status'] = 'FAIL_RUNTIME_STATE_QUALIFICATION_PRESERVED'
            result['completionErrors'].append({'scope': 'receipt-retention', 'type': type(error).__name__, 'message': str(error)})
            print(json.dumps(result, sort_keys=True), flush=True)
            raise
    raw = frozen(output/'result.json', 8*MIB)
    print(json.dumps({'path': str(output/'result.json'), 'status': result['status'], **identity(raw),
        'allOwnedGroupsPositivelyAbsent': result['allOwnedGroupsPositivelyAbsent'],
        'newRunPassEvents': result.get('actualMethods'), 'errors': result['errors'],
        'completionErrors': result['completionErrors']}, sort_keys=True), flush=True)
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
