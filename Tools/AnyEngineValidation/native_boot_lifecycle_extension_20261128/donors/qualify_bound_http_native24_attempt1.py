#!/usr/bin/env python3
"""Qualify24 new bound-HTTP/ACL-error events and one standalone Any native product.

Compose exact Runtime18 source with16 production changes and four new test files.
Retain C13 and Runtime18 acceptance as historical evidence without replay. All
new tests run under the qualified OS outbound denial helper and f9de ownership.
Fresh handler fixtures use local synthetic identities, never retained accounts.
The E cache requires actual Native117, subsequent Swift23 and Root's explicit
release. The current fixed release candidate has failed and cannot admit a run.
No cloud/quota call, legacy ACL mutation fence, dynamic-owner atomicity, Apple
binding, or live CLI HTTP account proof is inferred from this qualification.
"""
import argparse
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
PREPARATION = Path('/mnt/development/projects/evidence/pinkha-n-bound-http-native24-preparation-20261128-attempt1')
PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
OUTPUT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt8')
BASE = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt7/source')
CACHE = Path('/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1/cache')
PLAN_SHA = '241d6781d993632e82d17bfb343a751545a58addeb15b0156ffd7694e9d1caad'
INPUT_HELPER_SHA = '6848a0660fecc245e74e22e8bdd40c4ee5bf99cb60cbfa3a4248000b33628f3e'
INPUT_HELPER_BYTES = 29166
OWNED = Path('/mnt/development/projects/evidence/pinkha-n-runtime-state-publication-controls-20261127-attempt1/owned_swift_commands.py')
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNED_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
OWNED_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_PROOF = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json')
OFFLINE_PROOF_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
SECCOMP = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
SECCOMP_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
ROOT_FLOOR, DEV_FLOOR = 2*GIB, 512*MIB
OUTPUT_CAP, CACHE_CAP, LOG_CAP = 640*MIB, 512*MIB, 16*MIB
MAIN_SECONDS, FINAL_SECONDS = 900, 90
GROUPS = json.loads("{\"server-units\":{\"github.com/anyproto/any/internal/server\":[\"TestBoundEngineGateRejectsABAAndDrainsOriginalGeneration\",\"TestBoundEngineAdmissionPreservesOriginalOutcomeAfterRetirement\",\"TestBoundEngineHeadersFailBeforeDispatchAndBindingIsExplicit\",\"TestBoundEngineRequestAvoidsAuthMutexAndUsesCapturedCancellation\",\"TestACLConsumedRecordErrorsKeepTypedContract\"]},\"fresh-sdk\":{\"github.com/anyproto/any-sync-sdk\":[\"TestCurrentReaderLocalSettingsAndBuiltinStopAtSignedRemoval\"]},\"fresh-http\":{\"github.com/anyproto/any/internal/server\":[\"TestBoundHTTPFreshOwnerSettingsAndDeclaredLocalBuiltin\",\"TestBoundHTTPTechSpaceRefusalUsesCapturedSDK\",\"TestBoundHTTPDrainTimeoutKeepsCapturedSDKUntilHolderLeaves\"]}}")
SUBCASES = json.loads("{\"TestBoundEngineAdmissionPreservesOriginalOutcomeAfterRetirement\":[\"No_Content\",\"Conflict\"],\"TestBoundEngineHeadersFailBeforeDispatchAndBindingIsExplicit\":[\"missing\",\"duplicate-account\",\"duplicate-run\",\"combined-run\",\"upper-run\",\"foreign-account\",\"stale-run\"],\"TestACLConsumedRecordErrorsKeepTypedContract\":[\"missing_request\",\"consumed_request_wrapped\",\"missing_record\",\"consumed_record_wrapped\",\"cancelled_or_deadline\",\"untyped_lookalike\"]}")

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


def stat_identity(info):
    return tuple(getattr(info, name) for name in
                 ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_blocks', 'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns'))


def frozen(path, maximum=4*MIB):
    before = physical(path)
    require(before.st_nlink == 1 and 0 <= before.st_size <= maximum, 'bounded single-link immutable input')
    original = stat_identity(before)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(stat_identity(os.fstat(stream.fileno())) == original, 'immutable descriptor full identity')
        raw = stream.read(before.st_size+1)
        require(stat_identity(os.fstat(stream.fileno())) == original, 'immutable descriptor changed')
    require(stat_identity(path.lstat()) == original and len(raw) == before.st_size,
            'immutable pathname, nanosecond metadata, or bytes changed')
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


def parse_events(raw, packages, subcases=SUBCASES):
    require(len(raw) <= LOG_CAP, 'bounded Go event stream')
    expected = Counter()
    for package, methods in packages.items():
        for method in methods:
            expected[(package, method)] += 1
            for child in subcases.get(method, ()):
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
    parser.add_argument('--self-sha256', required=True)
    parser.add_argument('--e-native-receipt-sha256', required=True)
    parser.add_argument('--e-swift-receipt-sha256', required=True)
    parser.add_argument('--root-cache-release-confirmed', action='store_true', required=True)
    args = parser.parse_args()
    for value in (args.self_sha256, args.e_native_receipt_sha256, args.e_swift_receipt_sha256):
        require(re.fullmatch(r'[0-9a-f]{64}', value), 'exact caller-supplied SHA256 required')
    require(os.geteuid() == 0 and os.uname().nodename == 'torah-social', 'authorized Oracle host')
    require(HERE == PREPARATION and OUTPUT.parent == PARENT and OUTPUT.name == 'attempt8',
            'fixed exclusive preparation and existing fresh-fixture namespace')
    physical(PREPARATION, True)
    physical(PARENT, True)
    own = Path(__file__).absolute()
    own_raw = frozen(own)
    require(identity(own_raw)['sha256'] == args.self_sha256, 'actual executing controller before any mutation')
    output = OUTPUT
    began, final_deadline, last_census = time.monotonic(), None, 0.0
    owned_output, serial, cache_before, cache_anchor = False, 0, None, None
    base_before = source_before = None
    source, temporary, fixtures = output/'source', output/'temporary', output/'fixtures'
    admitted = {str(own): {'identity': identity(own_raw), 'maximum': 4*MIB,
                           'mode': stat.S_IMODE(physical(own).st_mode)}}
    result = {
        'protocol': 'pinkha-bound-http-native24-qualification-v1', 'status': 'RUNNING',
        'controller': identity(own_raw), 'processes': [], 'errors': [], 'completionErrors': [], 'mutations': [],
        'priorTestMethodsReexecuted': 0, 'retainedPrivateAccountInputs': 0, 'privateRecordExports': 0,
        'C313SourceWrites': 0, 'C3CacheWrites': 0, 'nativeCLIAccountProcesses': 0, 'nativeProductBuilds': 0,
        'newRequiredEvents': {'originalUnrunBoundObligations': 17, 'addedTypedACLErrorObligations': 7, 'total': 24},
        'freshHTTPProofScope': 'IN_PROCESS_ORIGINAL_HANDLERS_WITH_FRESH_SDK_UNDER_OS_NETWORK_DENIAL',
        'liveCLIHTTPProof': 'NOT_RUN_BY_THIS_CONTROLLER',
        'boundLocalOwner': 'any', 'dynamicDefinitionOwnerAtomicity': 'UNSUPPORTED',
        'declineExpectedRequestRecordId': False, 'legacyACLMutationRunBinding': 'NOT_ESTABLISHED',
        'cloudQuotaActivationOrAccessCodeCalls': 0, 'newCloudUploads': 0,
        'RootCacheReleaseAcknowledgedByCaller': args.root_cache_release_confirmed,
        'archivedNGoCacheUsedOrRestored': False, 'rootOwnershipGrantIsNotInferredFromReceiptStatus': True,
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
            'rootAdmissionReserveBytes': 32*MIB, 'developmentAdmissionReserveBytes': OUTPUT_CAP+CACHE_CAP,
            'ownedOutputCapBytes': OUTPUT_CAP, 'observedSharedCacheGrowthCapBytes': CACHE_CAP,
            'controlledOutputsOnDevelopmentOnly': True, 'globalRootWritesMeasured': False,
            'allocationIsEstimateNotMeasuredNewPeak': True, 'controllerSeconds': MAIN_SECONDS,
            'finalVerificationSeconds': FINAL_SECONDS, 'requiredOuterSeconds': 1050,
            'goWorkers': 2, 'goMemoryLimit': '1GiB', 'memoryAdmissionBytes': 3*GIB,
            'allocationCensusMinimumIntervalSeconds': 1,
            'estimateBasis': 'Actual Runtime18 owned peak265449472B and cache growth276299776B. New24 source/test/product peak on the separately released E cache is unmeasured.'}}

    def save_json(path, value):
        nonlocal serial
        require(owned_output and path.is_relative_to(output), 'owned evidence only')
        raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        require(len(raw) <= 8*MIB, 'bounded receipt content')
        serial += 1
        stage = path.with_name(path.name+'.pending-'+str(serial))
        exclusive(stage, raw)
        os.replace(stage, path)
        sync_directory(path.parent)

    def save():
        require(owned_output, 'never write an unowned output')
        result['seconds'] = time.monotonic()-began
        save_json(output/'result.json', result)

    def checkpoint(admission=False):
        require(time.monotonic() < (final_deadline if final_deadline is not None else began+MAIN_SECONDS),
                'finite qualification/final audit')
        if owned_output:
            require(not (output/'abort').exists(), 'owned abort requested')
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', ROOT_FLOOR, 32*MIB),
                                     ('development', DEV_FLOOR, OUTPUT_CAP+CACHE_CAP)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(
                free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
            require(free[name] >= floor+(reserve if admission else 0), name+' unchanged reserve/floor')
        return free

    def cache_identity():
        info = physical(CACHE, True)
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid)

    def guard(admission=False, force=False):
        nonlocal last_census
        free = checkpoint(admission)
        if force or admission or time.monotonic()-last_census >= 1:
            used = allocation(output, mutable=True) if owned_output else 0
            result['peakOwnedOutputBytes'] = max(used, result.get('peakOwnedOutputBytes', 0))
            require(used <= OUTPUT_CAP, 'all owned source/test/fixture/temp/product/evidence allocation')
            if cache_before is not None:
                require(cache_identity() == cache_anchor, 'same admitted physical E cache root, no alias substitution')
                now_allocated = allocation(CACHE, mutable=True)
                growth = max(0, now_allocated-cache_before)
                result['cacheAllocationObservedAfter'] = now_allocated
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
        admitted[str(path)] = {'identity': identity(raw), 'maximum': maximum,
                               'mode': stat.S_IMODE(physical(path).st_mode)}
        if mode is not None:
            require(admitted[str(path)]['mode'] == mode, 'pinned original input/executable mode')
        return raw

    def mkdir_owned(directory):
        require(owned_output and directory.is_relative_to(output), 'directory belongs to this output')
        current = output
        for part in directory.relative_to(output).parts:
            current = current/part
            if not os.path.lexists(current):
                current.mkdir(mode=0o700)
                os.chmod(current, 0o700)
                sync_directory(current)
                sync_directory(current.parent)
            info = physical(current, True)
            require(stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.geteuid(),
                    'owned directory physical and strict0700')

    def command(label, argv, cwd, environment, seconds):
        guard(force=True)
        remaining = began+MAIN_SECONDS-time.monotonic()
        require(remaining > 0, 'positive finite command budget')
        def persist(path, value):
            require(path.parent == output/label and path.name in ('started.json', 'result.json'),
                    'owned command journal')
            save_json(path, value)
            save()
        log, row = owned.run(output/label, argv, cwd, environment, min(seconds, remaining), observe, persist,
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
            require(stat.S_IMODE(physical(member).st_mode) == wanted['mode'], 'admitted original mode changed')
        return True

    def fixture_directories():
        physical(fixtures, True)
        fd = os.open(fixtures, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
        try:
            with os.scandir(fd) as rows:
                names = sorted(row.name for row in rows)
        finally:
            os.close(fd)
        require(len(names) == 4, 'exact four new method fixture directories')
        for name in names:
            info = physical(fixtures/name, True)
            require(stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.geteuid(),
                    'fresh owned private fixture directory; payload is not read by controller')
        return names

    def interrupted(number, _frame):
        raise RuntimeError('native24 qualification interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        result['initialFreeBytes'] = guard(admission=True, force=True)
        require(not os.path.lexists(output), 'exclusive new attempt, preserve all previous results')
        os.umask(0o077)
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            output.mkdir(mode=0o700)
            owned_output = True
            os.chmod(output, 0o700)
            sync_directory(output)
            sync_directory(PARENT)
            exclusive(output/'result.json', b'{}\n')
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        require(physical(output, True).st_dev == physical(Path('/mnt/development'), True).st_dev and
                stat.S_IMODE(physical(output, True).st_mode) == 0o700, 'new exclusive0700 development output')
        save()
        memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                          if line.startswith('MemAvailable:')))*1024
        require(memory >= 3*GIB, 'unchanged3GiB memory admission')
        result['memAvailableBefore'] = memory
        plan = json.loads(pin(HERE/'QUALIFICATION_PLAN.json', PLAN_SHA))
        require(plan['protocol'] == 'pinkha-native-bound-http-acl24-qualification-plan-v1' and
                plan['status'] == 'SOURCE_ONLY_NOT_RUN' and plan['preparation'] == str(HERE) and
                plan['output'] == str(output) and plan['ownedCommands'] == 6 and
                plan['oneNativeProductBuild'] is True and plan['priorMethodsRerun'] == 0 and
                plan['retainedPrivateAccountInputs'] == 0 and plan['exactRunPassEvents'] == 24 and
                plan['newParents'] == 9 and plan['newSubcases'] == 15 and
                plan['retainedUnrunOriginalObligations'] == 17 and plan['addedUnrunACLObligations'] == 7 and
                plan['subcases'] == SUBCASES and set(plan['groups']) == set(GROUPS),
                'closed source-only24-event/six-command plan')
        for label, groups in GROUPS.items():
            require(plan['groups'][label]['packages'] == groups, 'exact package and new method selection')
        require(plan['ECache']['path'] == str(CACHE) and
                plan['ECache']['archivedNCacheUsedOrRestored'] is False and
                plan['ECache']['requiresRootExplicitOwnershipRelease'] is True and
                args.root_cache_release_confirmed is True, 'separate caller-confirmed Root cache ownership grant')
        helper_raw = pin(HERE/'native24_inputs.py', INPUT_HELPER_SHA)
        require(len(helper_raw) == INPUT_HELPER_BYTES, 'complete exact source/receipt admission helper')
        inputs = types.ModuleType('native24_inputs')
        exec(compile(helper_raw, str(HERE/'native24_inputs.py'), 'exec'), inputs.__dict__)

        # This admission is deliberately before cache access, source copying,
        # any compiler or any fresh identity. A FAIL receipt never releases it.
        inputs.admit_e_cache_release(plan, args.e_native_receipt_sha256, args.e_swift_receipt_sha256,
                                     pin, require, normal, identity, result)
        released = physical(CACHE, True)
        cache_anchor = cache_identity()
        cache_before = allocation(CACHE, mutable=True)
        result['cacheAllocationBefore'] = cache_before
        result['cachePhysicalMetadataBefore'] = {
            name: getattr(released, name) for name in ('st_dev', 'st_ino', 'st_mode', 'st_nlink',
                'st_uid', 'st_gid', 'st_size', 'st_blocks', 'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns')}
        result['cacheRootStableIdentity'] = list(cache_anchor)
        result['cacheBaselineProvenance'] = 'NEW_N_OBSERVATION_AFTER_ACTUAL_E_NATIVE_SWIFT_AND_ROOT_RELEASE'
        guard(admission=True, force=True)

        admitted_source = inputs.admit_sources(plan, pin, require, normal, identity,
                                                source_inventory, checkpoint, parse_events, result)
        prior = admitted_source['prior']
        base_before = admitted_source['baseBefore']
        base_metadata = admitted_source['baseModule']
        manifest = admitted_source['manifest']
        candidate = admitted_source['candidate']
        production = admitted_source['production']
        overlay = admitted_source['overlay']
        expected, expected_modes = candidate['files'], candidate['modes']
        mkdir_owned(source)
        result['mutations'].append({'operation': 'compose-new-1649-public-source', 'state': 'dispatching'})
        save()
        for name, wanted in sorted(expected.items()):
            checkpoint()
            raw = overlay[name] if name in overlay else frozen(BASE/relative(name), 32*MIB)
            require(identity(raw) == wanted, 'complete current qualification source bytes')
            destination = source/relative(name)
            mkdir_owned(destination.parent)
            exclusive(destination, raw, expected_modes[name])
        source_before = source_inventory(source, checkpoint)
        require(source_before == candidate, 'complete isolated source bytes/modes readback')
        save_json(output/'compiled-source-inputs.json', source_before)
        save_json(output/'production-source-map.json', production)
        save_json(output/'sdk-production-source-map.json', {
            'files': {n[len(SDK_PREFIX):]: r for n, r in production['files'].items() if n.startswith(SDK_PREFIX)},
            'modes': {n[len(SDK_PREFIX):]: r for n, r in production['modes'].items() if n.startswith(SDK_PREFIX)}})
        save_json(output/'source-manifest.json', manifest)
        result['compiledSourceInputSHA256'] = identity(frozen(output/'compiled-source-inputs.json'))['sha256']
        result['sourceManifestSHA256'] = identity(frozen(output/'source-manifest.json'))['sha256']
        result['productionSourceMapSHA256'] = identity(frozen(output/'production-source-map.json'))['sha256']
        result['sdkProductionSourceMapSHA256'] = identity(frozen(output/'sdk-production-source-map.json'))['sha256']
        for filename in ('compiled-source-inputs.json', 'source-manifest.json', 'production-source-map.json',
                         'sdk-production-source-map.json'):
            raw = frozen(output/filename)
            pin(output/filename, identity(raw)['sha256'])
        result['formattedSourceManifestSHA256'] = plan['formatted']['manifest']['sha256']
        result['sourceRoot'] = str(source)
        result['sourceFiles'], result['sdkSourceFiles'] = 1649, 756
        result['productionFiles'], result['sdkProductionFiles'] = 1645, 755
        result['sourceComposition'] = {'baseFiles': 1638, 'baseSDKFiles': 750,
            'productionChanges': 16, 'productionAdditions': 7, 'productionReplacements': 9,
            'newTestFiles': 4, 'qualifiedFiles': 1649, 'qualifiedSDKFiles': 756,
            'oldC13OrRuntime18MethodsReexecuted': 0}
        result['wireContract'] = manifest['wire']
        result['localBuiltin'] = manifest['localBuiltin']
        result['typedACLConsumedRecordContract'] = manifest['aclConsumedRecordContract']
        result['mutations'][-1]['state'] = 'completed'

        helper = pin(OWNED, OWNED_SHA)
        require(len(helper) == plan['ownershipHelper']['bytes'] and
                plan['ownershipHelper']['path'] == str(OWNED), 'same actual-qualified process owner')
        lifecycle = json.loads(pin(OWNED_PROOF, OWNED_PROOF_SHA))
        require(lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and
                lifecycle['helperSHA256'] == OWNED_SHA and len(lifecycle['methods']) == 5 and
                all(row['status'] == 'PASS' for row in lifecycle['methods']) and
                lifecycle['allOwnedGroupsPositivelyAbsent'] is True, 'actual unchanged owner-helper lifecycle proof')
        owned = types.ModuleType('native24_owned_commands')
        exec(compile(helper, str(OWNED), 'exec'), owned.__dict__)
        pin(OFFLINE, OFFLINE_SHA, 65536)
        pin(SECCOMP, SECCOMP_SHA)
        policy = json.loads(pin(OFFLINE_PROOF, OFFLINE_PROOF_SHA))
        require(policy['offlinePolicy']['helperSHA256'] == OFFLINE_SHA and
                policy['offlinePolicy']['baselineTCPReachable'] is True and
                policy['offlinePolicy']['baselineUDPReceived'] is True and
                policy['offlinePolicy']['controls']['librarySHA256'] == SECCOMP_SHA and
                policy['offlinePolicy']['controls']['tcpErrno'] == policy['offlinePolicy']['controls']['udpErrno'] == 1 and
                all(policy['offlinePolicy']['controls'][name] is True for name in
                    ('tcpDenied', 'udpDenied', 'noNewPrivileges', 'seccompFilterActive')),
                'actual original OS-denial positive baselines and control schema')
        for directory in (temporary, fixtures):
            mkdir_owned(directory)
        require(stat.S_IMODE(physical(fixtures, True).st_mode) == 0o700,
                'unchanged private fresh-fixture root guard')
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(('GO', 'CGO_', 'ANY_', 'PINKHA_', 'PYTHON'))}
        environment.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE),
            GOMODCACHE='/root/go/pkg/mod', GOTMPDIR=str(temporary), TMPDIR=str(temporary), CGO_ENABLED='1',
            GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off', PYTHONDONTWRITEBYTECODE='1',
            PINKHA_FRESH_FILES_FIXTURE_ROOT=str(fixtures))
        known_go = prior['goToolchain']
        for tool in [known_go['driver'], *known_go['tools'].values()]:
            require(identity(pin(Path(tool['path']), tool['sha256'], 128*MIB)) ==
                    {key: tool[key] for key in ('bytes', 'sha256')}, 'exact Go driver/compiler/linker')
        native_tools = prior['currentNativeCompilerObservation']
        require(set(native_tools['explicitEnvironment']) == {'CC', 'CXX', 'AR'} and
                set(native_tools['tools']) == {'CC', 'CXX', 'AR'}, 'actual Runtime18 native compiler observation')
        for name, tool in native_tools['tools'].items():
            require(native_tools['explicitEnvironment'][name] == tool['path'], 'physical pinned native compiler')
            require(identity(pin(Path(tool['path']), tool['sha256'], 8*MIB, tool['mode'])) ==
                    {key: tool[key] for key in ('bytes', 'sha256')}, 'exact native compiler binary and mode')
        environment.update(native_tools['explicitEnvironment'])
        environment['PATH'] = native_tools['PATH']
        python = Path(sys.executable).resolve(strict=True)
        python_raw = frozen(python, 32*MIB)
        pin(python, identity(python_raw)['sha256'], 32*MIB, stat.S_IMODE(physical(python).st_mode))
        result['OSExecPython'] = {'path': str(python), **identity(python_raw)}
        result['OSPolicy'] = {'helperSHA256': OFFLINE_SHA, 'librarySHA256': SECCOMP_SHA,
            'actualOriginalControlReceiptSHA256': OFFLINE_PROOF_SHA,
            'appliedBeforeEveryTestCommand': True, 'newFreshFixturesRequireLiveEPERM': True}
        driver = known_go['driver']['path']
        fields = ['GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH',
                  'CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR']
        metadata_log, _ = command('toolchain', [driver, 'env', '-json', *fields], source, environment, 15)
        metadata = json.loads(frozen(metadata_log, 65536))
        require({key: metadata[key] for key in known_go['metadata']} == known_go['metadata'] and
                all(metadata[key] == environment[key] for key in
                    ('CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR')),
                'actual compiler metadata equals exact admitted tools and separately released cache')
        result['goToolchain'] = dict(known_go, actualEnvironment=metadata)
        result['currentNativeCompilerObservation'] = {'tools': native_tools['tools'], 'metadata': metadata,
            'explicitEnvironment': native_tools['explicitEnvironment'], 'PATH': environment['PATH']}
        result['environment'] = {key: environment[key] for key in ('GOTOOLCHAIN', 'GOMAXPROCS', 'GOMEMLIMIT',
            'GOCACHE', 'GOMODCACHE', 'GOTMPDIR', 'TMPDIR', 'CGO_ENABLED', 'GOWORK', 'GOFLAGS', 'GOPROXY',
            'GOSUMDB', 'CC', 'CXX', 'AR', 'PATH', 'PINKHA_FRESH_FILES_FIXTURE_ROOT')}
        result['operationalCacheDifferenceFromRuntime18'] = {
            'historical': prior['environment']['GOCACHE'], 'currentPhysical': str(CACHE),
            'originalModuleAndCompilerInputsUnchanged': True, 'historicalCacheContentsNotAssumed': True}
        for label, packages in GROUPS.items():
            require(source_inventory(source, checkpoint) == source_before,
                    'unchanged full source before each exact new selection')
            spec = plan['groups'][label]
            cwd = source/SDK_PREFIX if spec['cwd'] == 'sdk' else source
            methods = sorted(method for methods_in_package in packages.values() for method in methods_in_package)
            argv = [str(python), '-B', str(OFFLINE), '--exec', driver, 'test', '-json', '-count=1', '-p', '2',
                    '-parallel=1', '-timeout='+spec['testTimeout'], '-run', '^('+'|'.join(methods)+')$', *packages]
            log, _ = command(label, argv, cwd, environment, spec['commandSeconds'])
            raw = frozen(log, LOG_CAP)
            result.setdefault('rawLogs', {})[label] = {'path': str(log), **identity(raw)}
            result[label] = parse_events(raw, packages)
            save()
        require(sum(result[label]['runs'] for label in GROUPS) == 24 and
                sum(result[label]['passes'] for label in GROUPS) == 24 and
                result['server-units']['passes'] == 20 and result['fresh-sdk']['passes'] == 1 and
                result['fresh-http']['passes'] == 3, 'exact9 parents plus15 subcases, no omitted original17')
        require(fixture_directories() == plan['fixtureMethodDirectories'],
                'one fresh SDK plus three fresh original-handler fixtures, no prior account input')
        result['actualMethods'] = {'parents': 9, 'subcases': 15, 'runs': 24, 'passes': 24,
            'skips': 0, 'oldMethodsRerun': 0, 'freshSDKMethods': 1, 'freshInProcessHTTPMethods': 3,
            'originalNewObligations': {'parents': 8, 'subcases': 9, 'events': 17},
            'typedACLNewObligations': {'parents': 1, 'subcases': 6, 'events': 7}}
        result['actualFreshOSDenialVerified'] = True
        result['controllerReadFreshPrivatePayloads'] = False
        binary = output/'any'
        result['mutations'].append({'operation': 'build-one-coherent-native-product', 'state': 'dispatching'})
        save()
        command('native-build', [driver, 'build', '-p', '2', '-o', str(binary), './cmd/any'],
                source, environment, 240)
        result['nativeProductBuilds'] = 1
        result['mutations'][-1]['state'] = 'completed'
        raw = frozen(binary, 128*MIB)
        mode = stat.S_IMODE(physical(binary).st_mode)
        require(raw.startswith(b'\x7fELF') and mode & 0o111, 'one actual standalone native executable')
        result['nativeBinary'] = {'path': str(binary), 'mode': mode, **identity(raw)}
        pin(binary, identity(raw)['sha256'], 128*MIB, mode)
        module_log, _ = command('native-metadata', [driver, 'version', '-m', str(binary)],
                                source, environment, 15)
        module = frozen(module_log, 65536)
        require(module.splitlines()[1:] == base_metadata.splitlines()[1:] and
                known_go['metadata']['GOVERSION'].encode() in module.splitlines()[0] and
                b'github.com/anyproto/anytype-heart' not in module,
                'same original standalone module and toolchain graph')
        result['binaryModuleMetadata'] = identity(module)
        pin(module_log, identity(module)['sha256'], 65536)
        result['standaloneAnySDKProducerNotEmbeddedHeart'] = True
        result['status'] = 'PASS_NATIVE24_BOUND_HTTP_AND_TYPED_ACL_ERRORS_ONE_STANDALONE_PRODUCT'
    except BaseException as error:
        result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        # These are only f9de's own latched rows. No old PID is inspected.
        result['allOwnedGroupsPositivelyAbsent'] = bool(result['processes']) and all(
            row.get('processGroupAbsent') is True for row in result['processes'])
        result['ownedGroupsStarted'] = sum('pid' in row for row in result['processes'])
        result['noOwnedGroupEverStarted'] = result['ownedGroupsStarted'] == 0
        final_deadline = min(time.monotonic()+FINAL_SECONDS, began+MAIN_SECONDS+FINAL_SECONDS)
        for label, available, action in [
            ('declaredInputsAndProducts', True, validate_inputs),
            ('originalRuntime18Source', base_before is not None,
                lambda: source_inventory(BASE, checkpoint) == base_before),
            ('compiledSource', source_before is not None,
                lambda: source_inventory(source, checkpoint) == source_before),
            ('releasedECacheRootIdentity', cache_anchor is not None,
                lambda: cache_identity() == cache_anchor),
        ]:
            if not available:
                result.setdefault('finalIntegrity', {})[label] = 'NOT_ADMITTED'
                continue
            try:
                checkpoint()
                require(action(), label+' changed during qualification')
                result.setdefault('finalIntegrity', {})[label] = True
            except BaseException as error:
                result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
                result['completionErrors'].append({'scope': label, 'type': type(error).__name__, 'message': str(error)})
        try:
            result['finalFreeBytes'] = guard(force=True)
            result['immutableInputManifest'] = {
                name: dict(wanted['identity'], mode=wanted['mode']) for name, wanted in admitted.items()}
            if result['status'].startswith('PASS_'):
                require(len(result['processes']) == 6 and all(normal(row) for row in result['processes']) and
                        result['allOwnedGroupsPositivelyAbsent'] is True and
                        all(value is True for value in result['finalIntegrity'].values()) and
                        result['nativeProductBuilds'] == 1 and result['errors'] == result['completionErrors'] == [] and
                        result['actualMethods']['runs'] == result['actualMethods']['passes'] == 24,
                        'six normal owned commands,24 exact events and complete source/product finalization')
        except BaseException as error:
            result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
            result['completionErrors'].append({'scope': 'final-resources-and-closure',
                                               'type': type(error).__name__, 'message': str(error)})
        if owned_output:
            try:
                save()
            except BaseException as error:
                result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
                result['completionErrors'].append({'scope': 'receipt-retention',
                                                   'type': type(error).__name__, 'message': str(error)})
                print(json.dumps({'retention': 'STDOUT_FAILURE_FALLBACK', 'result': result}, sort_keys=True), flush=True)
                return 1
        else:
            result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
            print(json.dumps({'retention': 'NO_OUTPUT_OWNERSHIP_STDOUT_ONLY', 'result': result}, sort_keys=True), flush=True)
            return 1
    try:
        raw = frozen(output/'result.json', 8*MIB)
        require(json.loads(raw) == result, 'final retained receipt exact readback')
        print(json.dumps({'path': str(output/'result.json'), 'status': result['status'], **identity(raw),
            'allOwnedGroupsPositivelyAbsent': result['allOwnedGroupsPositivelyAbsent'],
            'newRunPassEvents': result.get('actualMethods'), 'errors': result['errors'],
            'completionErrors': result['completionErrors']}, sort_keys=True), flush=True)
        return 0 if result['status'].startswith('PASS_') else 1
    except BaseException as error:
        result['status'] = 'FAIL_NATIVE24_QUALIFICATION_PRESERVED'
        result['completionErrors'].append({'scope': 'terminal-readback',
                                           'type': type(error).__name__, 'message': str(error)})
        print(json.dumps({'retention': 'TERMINAL_READBACK_STDOUT_FAILURE', 'result': result}, sort_keys=True), flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
