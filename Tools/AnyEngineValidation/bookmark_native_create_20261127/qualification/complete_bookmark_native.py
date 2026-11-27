#!/usr/bin/env python3
"""Complete 13 Bookmark methods: eight retained SDK passes and five new server tests.

Reuse the byte-exact original 1,626-file materialized source; new temporary,
fixture, evidence and one product outputs belong to a new development directory.
The original cap failure, qualified N1616 input, C313 worktree and C3 cache stay
unchanged. No retained test runs again; native warm/cold remains a separate proof.
"""
import argparse
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
PARENT = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-create-20261127')
HERE = PARENT/'prepared1'
RETAINED = PARENT/'qualification-attempt1'
RETAINED_RECEIPT_SHA = '2a453fd5aa39caddbbded6056be7b94eab5978fc3d12391b5caca4a73d38443b'
RETAINED_CONTROLLER_SHA = 'a45b10800f1ea89530e38b1c6a5b7e34ee3e2ded5bc9d326ccc98762186ed712'
RETAINED_INPUTS_SHA = '1bad7f2ca0bdee3d5957e8bb8647417aef8e823257c36e57ec9ea022f5659ca0'
RETAINED_SDK_LOG_SHA = 'f6b1fdbd7308d2c3875a3465821b8ccb5dea339917d33fe314548d5d21cbdbc1'
RETAINED_ENV_LOG_SHA = '865117f0fe0f842b406e0a216c4f9c249a7a2df9b66e478067066f5ef3485c1d'
EMPTY_SHA = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
BASE = Path('/var/lib/pinkha-c-filesv2-20261126/final-authority-native1')
BASE_SOURCE_SHA = '773f0a25422b3460a375182fb6f839fd71d7246ad8b489b6c20418bfab3b2471'
BASE_RECEIPT_SHA = '9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602'
DRAFT_SHA = 'ebd4b3c7379a9d8851118d42ba25a43e08bc6939d7e1328cc8b83c67693dbe4c'
COMPOSED_SHA = 'f45556ad8a93f7adfe2a9ff02bf19ae1536080695f23c13370882df7771a0bd3'
PLAN_SHA = '52cdc2db76be080c921ccd6801a4b7d27ea593f4fc4ea0cade585cceb46fee69'
FORMAT_PROOF = Path('/mnt/development/projects/evidence/pinkha-c-bookmark-format-20261127/attempt1/result.json')
FORMAT_PROOF_SHA = '74f095ea5ff1aa4216fc06fba5aa559afc306a3106f4d9570a09b2d42f580bf0'
FORMAT_WORKER_SHA = '54c8dfb8cf88b4b80a5c06958f1196eb1c99f3dbe39ac5a75e5550d98eac7db1'
FORMAT_CONTROLLER_SHA = '980d8a9edb6b67f054fde7bc55db50b943244ed66f69d39fc3f2caa3c58353e6'
GOFMT_SHA = '3ca5e23c92e957338205edb7c8a19a0c4f211b2cf606e21171925f3001d12825'
OWNER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
OWNER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_PROOF = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json')
OFFLINE_PROOF_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
CONFIG_NAME = 'internal/pinkha/migrationnative/testdata/local.yml'
CONFIG_SHA = 'a3fe3c21144c2c82afa03b58014752c6bca6e5a9f3e69a1bc1b2b38415434756'
MIB, GIB = 1024**2, 1024**3
ROOT_FLOOR, DEV_FLOOR = 2*GIB, 512*MIB
OUTPUT_CAP, CACHE_CAP, LOG_CAP = GIB, 512*MIB, 16*MIB
CONTROLLER_SECONDS, FINAL_SECONDS = 1260, 90


def require(value, message):
    if not value:
        raise RuntimeError(message)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def relative(name):
    path = PurePosixPath(name)
    require(name and not path.is_absolute() and str(path) == name and
            '..' not in path.parts and '\\' not in name, 'closed relative source path')
    return path


def physical(path, directory=False):
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'physical owned or public path')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'regular physical input kind')
    return info


def frozen(path, maximum=8*MIB):
    before = physical(path)
    require(0 <= before.st_size <= maximum, 'bounded immutable file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno()) == before, 'immutable descriptor identity')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno()) == before, 'immutable descriptor changed during read')
    require(path.lstat() == before and len(raw) == before.st_size, 'immutable pathname changed during read')
    return raw


def fsync_directory(path):
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
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), mode)
    fsync_directory(path.parent)
    require(frozen(path, max(len(raw), 1)) == raw, 'exclusive exact source readback')


def source_inventory(root, guard):
    physical(root, True)
    found, modes, pending = {}, {}, [root]
    count = 0
    while pending:
        guard()
        directory = pending.pop()
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC)
        try:
            with os.scandir(fd) as rows:
                names = sorted(row.name for row in rows)
        finally:
            os.close(fd)
        for name in names:
            guard()
            member = directory/name
            info = member.lstat()
            count += 1
            require(count <= 10000 and not stat.S_ISLNK(info.st_mode), 'finite source without aliases')
            if stat.S_ISDIR(info.st_mode):
                pending.append(member)
            else:
                require(stat.S_ISREG(info.st_mode), 'regular source member')
                key = member.relative_to(root).as_posix()
                found[key] = identity(frozen(member, 32*MIB))
                modes[key] = stat.S_IMODE(info.st_mode)
    return {'files': found, 'modes': modes}


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
            with os.scandir(fd) as entries:
                names = [entry.name for entry in entries]
        finally:
            os.close(fd)
        for name in [None]+names:
            path = directory if name is None else directory/name
            try:
                info = path.lstat()
            except FileNotFoundError:
                if mutable:
                    continue
                raise
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'no output/cache aliases or special files')
            key = (info.st_dev, info.st_ino)
            if key not in seen:
                total += max(info.st_size, info.st_blocks*512) if stat.S_ISREG(info.st_mode) else info.st_blocks*512
                seen.add(key)
            if name is not None and stat.S_ISDIR(info.st_mode):
                pending.append(path)
            if name == 'original.log':
                require(info.st_size <= LOG_CAP, 'bounded original command log')
            count += 1
            require(count <= 100000 and time.monotonic()-began <= 8, 'bounded owned allocation census')
    return total


def parse_test_events(raw, expected):
    require(len(raw) <= LOG_CAP, 'bounded Go event stream')
    starts, passes = [], []
    for line in raw.splitlines():
        require(len(line) <= 2*MIB, 'bounded individual Go event')
        if not line:
            continue
        event = json.loads(line)
        require(isinstance(event, dict), 'Go JSON event object')
        name = event.get('Test')
        action = event.get('Action')
        require(action not in ('skip', 'fail'), 'no skipped or failed test/package')
        if name is not None:
            key = (event.get('Package'), name)
            require(key in expected, 'no old or undeclared method/subtest selected')
            if action == 'run':
                starts.append(key)
            if action == 'pass':
                passes.append(key)
    require(len(starts) == len(passes) == len(expected) and
            len(set(starts)) == len(starts) and set(starts) == set(passes) == set(expected),
            'exactly one start and pass per declared new method')
    return {'runs': len(starts), 'passes': len(passes), 'failures': 0, 'skips': 0,
            'methods': [{'package': package, 'name': name} for package, name in sorted(passes)]}


def main():
    require(not sys.flags.optimize, 'qualification assertions enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output
    require(os.geteuid() == 0 and os.uname().nodename == 'torah-social', 'authorized Oracle host')
    require(output.parent == PARENT and re.fullmatch(r'qualification-completion-attempt[1-9][0-9]{0,2}', output.name), 'fixed exclusive output scope')
    physical(PARENT, True)
    require(not os.path.lexists(output), 'preserve every previous attempt')
    os.umask(0o077)
    output.mkdir(mode=0o700)
    exclusive(output/'result.json', b'{}\n')
    began = time.monotonic()
    serial, final_deadline = 0, None
    source, temporary = RETAINED/'source', output/'temporary'
    cache_before = None
    baseline = candidate_before = None
    baseline_files = candidate_files = None
    admitted = {}
    result = {'protocol': 'pinkha-native-bookmark-conditional-create-completion-v1', 'status': 'RUNNING',
        'processes': [], 'errors': [], 'completionErrors': [], 'mutations': [],
        'priorTestMethodsReexecuted': 0, 'retainedActualMethodCount': 0, 'newActualMethodCount': 0,
        'newSourceMaterializations': 0, 'sourceRoot': str(source), 'originalAccountInputs': 0, 'nativeCLIAccountProcesses': 0,
        'C313SourceWrites': 0, 'C3CacheWrites': 0, 'nativeProductBuilds': 0,
        'runtimeBodylessWarmColdStatus': 'NOT_RUN_SEPARATE_CONSUMER',
        'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
            'rootAdmissionReserveBytes': 32*MIB, 'developmentAdmissionReserveBytes': OUTPUT_CAP+CACHE_CAP,
            'ownedOutputCapBytes': OUTPUT_CAP, 'sharedCacheGrowthCapBytes': CACHE_CAP,
            'controlledOutputPathsOnDevelopmentOnly': True, 'globalRootWritesMeasured': False,
            'allocationIsEstimateNotMeasuredNewPeak': True, 'controllerSeconds': CONTROLLER_SECONDS,
            'finalVerificationSeconds': FINAL_SECONDS, 'requiredOuterSeconds': 1410,
            'goMemoryLimit': '1GiB', 'workers': 2}}

    def save_json(path, value):
        nonlocal serial
        require(path.is_relative_to(output), 'owned result path')
        raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        require(len(raw) <= 8*MIB, 'bounded result content')
        serial += 1
        stage = path.with_name(path.name+'.pending-'+str(serial))
        exclusive(stage, raw)
        os.replace(stage, path)
        fsync_directory(path.parent)

    def save():
        result['seconds'] = time.monotonic()-began
        save_json(output/'result.json', result)

    def checkpoint(admission=False):
        require(time.monotonic() < (final_deadline if final_deadline is not None else began+CONTROLLER_SECONDS), 'finite controller/final phase')
        require(not (output/'abort').exists(), 'owned abort')
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', ROOT_FLOOR, 32*MIB), ('development', DEV_FLOOR, OUTPUT_CAP+CACHE_CAP)]:
            require(free[name] >= floor+(reserve if admission else 0), name+' unchanged reserve/floor')
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
        return free

    def guard(admission=False):
        free = checkpoint(admission)
        used = allocation(output, mutable=True)
        require(used <= OUTPUT_CAP, 'entire source/test/store/temp/product/evidence allocation cap')
        result['peakOwnedOutputBytes'] = max(used, result.get('peakOwnedOutputBytes', 0))
        if cache_before is not None:
            require(CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET, 'original admitted shared cache alias')
            growth = max(0, allocation(CACHE_TARGET, mutable=True)-cache_before)
            result['peakObservedCacheGrowthBytes'] = max(growth, result.get('peakObservedCacheGrowthBytes', 0))
            require(growth <= CACHE_CAP, 'measured shared cache incremental cap')
        checkpoint()
        return free

    def observe():
        try:
            guard()
            return None
        except BaseException as error:
            return type(error).__name__+': '+str(error)

    def pin(path, wanted, maximum=8*MIB):
        checkpoint()
        raw = frozen(path, maximum)
        require(identity(raw)['sha256'] == wanted, 'exact input/product hash')
        admitted[str(path)] = {'identity': identity(raw), 'maximum': maximum}
        return raw

    def validate_admitted():
        for name, wanted in admitted.items():
            checkpoint()
            path = Path(name)
            require(identity(frozen(path, wanted['maximum'])) == wanted['identity'], 'declared input or product changed')
            if 'mode' in wanted:
                require(stat.S_IMODE(physical(path).st_mode) == wanted['mode'], 'native product executable mode changed')
        return True

    def command(label, argv, cwd, environment, seconds):
        def persist(path, value):
            require(path.parent == output/label and path.name in ('started.json', 'result.json'), 'owned command record')
            save_json(path, value)
            save()
        log, row = owned.run(output/label, argv, cwd, environment, seconds, observe, persist,
            lambda path: identity(frozen(path, LOG_CAP))['sha256'], result['processes'])
        save()
        return log, row

    def interrupted(number, _frame):
        raise RuntimeError('Bookmark qualification interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        result['initialFreeBytes'] = guard(True)
        require(physical(output, True).st_dev == physical(Path('/mnt/development'), True).st_dev, 'all outputs physically on development')
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available >= 3*GIB, 'original 3 GiB memory admission')
        result['memAvailableBefore'] = available
        own = Path(__file__).absolute()
        raw = frozen(own)
        admitted[str(own)] = {'identity': identity(raw), 'maximum': 8*MIB}
        result['controller'] = identity(raw)
        draft = json.loads(pin(HERE/'BOOKMARK_SOURCE_FORMATTED.json', DRAFT_SHA))
        plan = json.loads(pin(HERE/'BOOKMARK_QUALIFICATION_PLAN_FORMATTED.json', PLAN_SHA))
        require(plan['status'] == 'SOURCE_ONLY_PROPOSED_NO_DISPATCH' and plan['sourceDraftSHA256'] == DRAFT_SHA, 'exact proposed qualification scope')
        require(draft['status'] == 'SOURCE_ONLY_FORMATTED_NOT_COMPILED_NOT_RUN', 'exact qualified formatting source successor')
        formatting = json.loads(pin(FORMAT_PROOF, FORMAT_PROOF_SHA))
        format_worker_raw = pin(FORMAT_PROOF.with_name('worker-result.json'), FORMAT_WORKER_SHA)
        format_worker = json.loads(format_worker_raw)
        require(formatting['status'] == 'PASS_CANONICAL_GOFMT17_SOURCE_ONLY' and
                formatting['sourceDraftSHA256'] == draft['originalDraft2SHA256'] and
                formatting['controller']['sha256'] == FORMAT_CONTROLLER_SHA and
                formatting['workerReceipt'] == identity(format_worker_raw) and
                formatting['confirmedFormatterInvocations'] == 17 and
                formatting['compilerInvocations'] == formatting['testMethodsExecuted'] == formatting['nativeAccountProcesses'] == 0 and
                formatting['errors'] == formatting['completionErrors'] == [] and
                formatting['allOwnedGroupsPositivelyAbsent'] is True and len(formatting['processes']) == 1 and
                all(row['exitCode'] == 0 and row['processGroupAbsent'] is True and not row['forcedCleanup'] and
                    not row['cleanupErrors'] and not row['signals'] for row in formatting['processes']), 'actual source-only canonical formatter closure')
        formatted_files = {name: {key: row[key] for key in ('bytes', 'sha256')} for name, row in draft['files'].items()}
        require(formatting['formattedFiles'] == formatted_files and
                draft['canonicalFormatting']['receiptSHA256'] == FORMAT_PROOF_SHA and
                draft['canonicalFormatting']['workerReceiptSHA256'] == FORMAT_WORKER_SHA and
                format_worker['toolSHA256'] == GOFMT_SHA and len(format_worker['rows']) == 17 and
                {row['path'] for row in format_worker['rows']} == set(formatted_files) and
                all(row['exitCode'] == 0 and row['sameOwnedGroupAtStart'] is True and
                    row['output'] == formatted_files[row['path']] and
                    row['input']['sha256'] == draft['files'][row['path']]['unformattedSHA256']
                    for row in format_worker['rows']), 'all 17 canonical outputs match their preserved inputs')
        result['canonicalFormattingReceiptSHA256'] = FORMAT_PROOF_SHA
        result['sourceDraftSHA256'] = DRAFT_SHA
        expected_raw = pin(HERE/'BOOKMARK_COMPOSED1625_FORMATTED.json', COMPOSED_SHA)
        candidate_files = json.loads(expected_raw)['files']
        base_raw = pin(BASE/'source-manifest.json', BASE_SOURCE_SHA)
        baseline_files = json.loads(base_raw)['files']
        prior = json.loads(pin(BASE/'result.json', BASE_RECEIPT_SHA))
        require(prior['status'] == 'PASS_FINAL_NATIVE_BUILD_AND_FILES_AUTHORITY34' and
                prior['sourceManifestSHA256'] == BASE_SOURCE_SHA and prior['sourceFiles'] == 1616 and
                prior['allOwnedGroupsPositivelyAbsent'] is True and prior['errors'] == prior['completionErrors'] == [] and
                len(prior['processes']) == 3 and all(row['exitCode'] == 0 and row['processGroupAbsent'] is True and
                    not row['forcedCleanup'] and not row['cleanupErrors'] for row in prior['processes']), 'actual closed latest N1616 product source')
        require(len(baseline_files) == 1616 and len(candidate_files) == 1625 and
                len(draft['files']) == 17 and sum(row['role'] == 'production' for row in draft['files'].values()) == 13 and
                draft['expectedMethods'] == 13 and draft['expectedSubtests'] == 0, 'closed source/method inventory')
        overlay = {}
        composed = dict(baseline_files)
        for name, wanted in draft['files'].items():
            relative(name)
            raw = pin(HERE/'formatted-overlay'/name, wanted['sha256'])
            require(len(raw) == wanted['bytes'], 'exact overlay source length')
            old = baseline_files.get(name)
            require((old['sha256'] if old else None) == wanted['beforeSHA256'], 'exact replacement preimage or absent addition')
            overlay[name] = raw
            composed[name] = identity(raw)
        require(composed == candidate_files and sum(name not in baseline_files for name in overlay) == 9, 'full original source plus only declared replacements/additions')
        baseline = source_inventory(BASE/'source', checkpoint)
        require(baseline['files'] == baseline_files, 'complete immutable original source identity')
        save_json(output/'original-source-before.json', baseline)
        owner_raw = pin(HERE/'owned_swift_commands.py', OWNER_SHA)
        controls = json.loads(pin(OWNER_PROOF, OWNER_PROOF_SHA))
        require(controls['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and
                controls['helperSHA256'] == OWNER_SHA and controls['allOwnedGroupsPositivelyAbsent'] is True and
                len(controls['methods']) == 5 and all(row['status'] == 'PASS' for row in controls['methods']), 'reuse five actual owner controls')
        owned = types.ModuleType('bookmark_owned_commands')
        owned.__file__ = str(HERE/'owned_swift_commands.py')
        exec(compile(owner_raw, owned.__file__, 'exec'), owned.__dict__)
        offline = HERE/'linux_outbound_denial.py'
        pin(offline, OFFLINE_SHA)
        offline_proof = json.loads(pin(OFFLINE_PROOF, OFFLINE_PROOF_SHA))
        require(offline_proof['status'] == 'PASS' and offline_proof['allOwnedGroupsPositivelyAbsent'] is True and
                offline_proof['offlinePolicy']['helperSHA256'] == OFFLINE_SHA, 'unchanged previously qualified process-only OS policy')
        require(CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET, 'exact original shared Go cache placement')
        physical(CACHE_TARGET, True)
        cache_before = allocation(CACHE_TARGET, mutable=True)
        result['cacheAllocationBefore'] = cache_before
        # Reuse exactly the already materialized 1,626-file source. Nothing is
        # rebuilt or re-run merely to replace the failed resource receipt.
        retained = json.loads(pin(RETAINED/'result.json', RETAINED_RECEIPT_SHA))
        pin(HERE/'qualify_bookmark_native.py', RETAINED_CONTROLLER_SHA)
        require(retained['status'] == 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED' and
                retained['controller'] == {'bytes': 30227, 'sha256': RETAINED_CONTROLLER_SHA} and
                retained['errors'] == [{'type': 'RuntimeError', 'message': 'RuntimeError: measured shared cache incremental cap'}] and
                retained['completionErrors'] == [{'boundary': 'acceptanceAndResources', 'type': 'RuntimeError', 'message': 'measured shared cache incremental cap'}],
                'only the exact retained cache-cap failure is eligible')
        require(retained['allOwnedGroupsPositivelyAbsent'] is True and len(retained['processes']) == 3 and
                retained['finalIntegrity'] == {'compiledSource': True, 'declaredInputsAndProducts': True, 'originalSource': True} and
                retained['sourceDraftSHA256'] == DRAFT_SHA and retained['sourceManifestSHA256'] == COMPOSED_SHA and
                retained['compiledSourceInputSHA256'] == RETAINED_INPUTS_SHA and retained['sourceFiles'] == 1625 and
                retained['nativeProductBuilds'] == retained['priorTestMethodsReexecuted'] == retained['originalAccountInputs'] ==
                retained['nativeCLIAccountProcesses'] == retained['C313SourceWrites'] == retained['C3CacheWrites'] == 0 and
                retained['runtimeBodylessWarmColdStatus'] == 'NOT_RUN_SEPARATE_CONSUMER', 'retained source/effect boundary')
        retained_rows = retained['processes']
        require(all(row['exitCode'] == 0 and row['processGroupAbsent'] is True and row['forcedCleanup'] is False and
                    row['signals'] == row['cleanupErrors'] == [] and row['stopReason'] is None and
                    row['unreapedLeaderDuringGroupCleanup'] is True for row in retained_rows[:2]),
                'two retained normal owned commands')
        interrupted_row = retained_rows[2]
        require(interrupted_row['exitCode'] == -signal.SIGTERM and interrupted_row['processGroupAbsent'] is True and
                interrupted_row['forcedCleanup'] is True and interrupted_row['signals'] == [signal.SIGTERM] and
                interrupted_row['cleanupErrors'] == [] and interrupted_row['unreapedLeaderDuringGroupCleanup'] is True and
                interrupted_row['logSHA256'] == EMPTY_SHA and
                interrupted_row['stopReason'] == 'RuntimeError: measured shared cache incremental cap',
                'retain the interrupted server compile as failure, never a qualified command')
        pin(RETAINED/'server-five'/'original.log', EMPTY_SHA, LOG_CAP)
        retained_source_raw = pin(RETAINED/'compiled-source-inputs.json', RETAINED_INPUTS_SHA)
        retained_source = json.loads(retained_source_raw)
        config_raw = frozen(source/CONFIG_NAME, 65536)
        require(identity(config_raw) == {'bytes': 1137, 'sha256': CONFIG_SHA} and 'staging.yml' not in candidate_files,
                'exact separately declared public runtime config')
        candidate_files = dict(candidate_files, **{'staging.yml': identity(config_raw)})
        candidate_before = source_inventory(source, checkpoint)
        require(candidate_before == retained_source and candidate_before['files'] == candidate_files and len(candidate_files) == 1626,
                'all original producer source bytes and modes remain identical')
        exclusive(output/'source-manifest.json', expected_raw)
        exclusive(output/'compiled-source-inputs.json', retained_source_raw)
        pin(output/'source-manifest.json', COMPOSED_SHA)
        pin(output/'compiled-source-inputs.json', RETAINED_INPUTS_SHA)
        result['compiledSourceInputSHA256'] = RETAINED_INPUTS_SHA
        result['sourceManifestSHA256'] = COMPOSED_SHA
        result['sourceFiles'] = 1625
        result['separatelyDeclaredRuntimeConfig'] = {'path': 'staging.yml', **identity(config_raw)}
        result['retainedQualification'] = {'receiptPath': str(RETAINED/'result.json'), 'receiptSHA256': RETAINED_RECEIPT_SHA,
            'sourceRoot': str(source), 'compiledSourceInputsSHA256': RETAINED_INPUTS_SHA,
            'qualifiedProcesses': retained_rows[:2], 'failedCompileProcess': interrupted_row,
            'originalFailureStatusUnchanged': True, 'historicalProcessIDsNeverProbedOrSignaled': True}
        save()
        temporary.mkdir(mode=0o700)
        environment = {key: value for key, value in os.environ.items() if not key.startswith(('GO', 'CGO_', 'ANY_', 'PINKHA_', 'PYTHON'))}
        environment.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE),
            GOMODCACHE='/root/go/pkg/mod', GOTMPDIR=str(temporary), TMPDIR=str(temporary), CGO_ENABLED='1',
            GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off', PYTHONDONTWRITEBYTECODE='1')
        known_go = prior['goToolchain']
        for row in [known_go['driver']]+list(known_go['tools'].values()):
            require(identity(pin(Path(row['path']), row['sha256'], 128*MIB)) == {key: row[key] for key in ('bytes', 'sha256')}, 'same actual Go driver/compiler/linker')
        driver = known_go['driver']['path']
        retained_env_raw = pin(RETAINED/'go-environment'/'original.log', RETAINED_ENV_LOG_SHA, 65536)
        require(retained['goToolchain'] == known_go and json.loads(retained_env_raw) == known_go['metadata'] and
                retained_rows[0]['logSHA256'] == RETAINED_ENV_LOG_SHA and retained_rows[0]['cwd'] == str(source) and
                retained_rows[0]['argv'] == [driver, 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH'],
                'exact retained metadata command and freshly pinned driver/compiler/linker')
        for key, value in retained['environment'].items():
            if key not in ('GOTMPDIR', 'TMPDIR'):
                require(environment.get(key) == value, 'same retained non-temporary compiler environment')
        result['permittedEnvironmentChange'] = {'GOTMPDIR': str(temporary), 'TMPDIR': str(temporary)}
        # The historical receipt never observed CC/CXX/AR or PATH. Keep that
        # limit explicit rather than reconstructing or relabeling old evidence.
        result['retainedCompilerEvidenceScope'] = {
            'originalGoDriverCompilerLinkerSourceAndRecordedEnvironmentOnly': True,
            'historicalNativeCompilerExecutablesObserved': False,
            'historicalPATHObserved': False, 'retainedSDKMethodsReexecuted': 0}
        default_environment = dict(environment)
        for key in ('CC', 'CXX', 'AR'):
            default_environment.pop(key, None)
        compiler_log, _ = command('current-native-compiler-environment',
            [driver, 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH',
             'GOOS', 'GOARCH', 'CGO_ENABLED', 'GOMODCACHE', 'GOCACHE', 'CC', 'CXX', 'AR'],
            source, default_environment, 15)
        native_environment = json.loads(frozen(compiler_log, 65536))
        require({key: native_environment.get(key) for key in known_go['metadata']} == known_go['metadata'] and
                native_environment.get('CGO_ENABLED') == '1' and native_environment.get('GOMODCACHE') == '/root/go/pkg/mod' and
                native_environment.get('GOCACHE') == str(CACHE), 'current original Go defaults and original cache/module placement')
        native_tools = {}
        current_path = environment.get('PATH', os.defpath)
        require(all(part and Path(part).is_absolute() for part in current_path.split(os.pathsep)), 'explicit absolute compiler lookup PATH')
        for key in ('CC', 'CXX', 'AR'):
            default_name = native_environment.get(key)
            require(isinstance(default_name, str) and re.fullmatch(r'[A-Za-z0-9_./+-]+', default_name),
                    'one original default native compiler executable')
            found = shutil.which(default_name, path=current_path)
            require(found is not None, 'original native compiler executable present')
            executable = Path(found).resolve()
            require(environment.get(key, default_name) in (default_name, str(executable)),
                    'conflicting inherited native compiler override refused: '+key)
            compiler_bytes = frozen(executable, 128*MIB)
            wanted = identity(compiler_bytes)
            pin(executable, wanted['sha256'], 128*MIB)
            mode = stat.S_IMODE(physical(executable).st_mode)
            require(mode & 0o111, 'current native compiler executable mode')
            admitted[str(executable)]['mode'] = mode
            native_tools[key] = {'observedDefault': default_name, 'path': str(executable), **wanted, 'mode': mode}
            environment[key] = str(executable)
        environment['PATH'] = current_path
        result['currentNativeCompilerObservation'] = {'metadata': native_environment, 'tools': native_tools,
            'PATH': current_path, 'explicitEnvironment': {key: environment[key] for key in ('CC', 'CXX', 'AR')},
            'appliesTo': ['five-new-server-methods', 'one-new-native-product'],
            'historicalCompilerEqualityClaimed': False}

        result['goToolchain'] = known_go
        result['environment'] = {key: environment[key] for key in ('GOTOOLCHAIN', 'GOMAXPROCS', 'GOMEMLIMIT', 'GOCACHE', 'GOMODCACHE', 'GOTMPDIR', 'TMPDIR', 'CGO_ENABLED', 'GOWORK', 'GOFLAGS', 'GOPROXY', 'GOSUMDB')}
        sdk_expected, server_expected = set(), set()
        for name, methods in draft['tests'].items():
            package = 'github.com/anyproto/any-sync-sdk/'+str(PurePosixPath(name.removeprefix(SDK_PREFIX)).parent) if name.startswith(SDK_PREFIX) else 'github.com/anyproto/any/'+str(PurePosixPath(name).parent)
            target = sdk_expected if name.startswith(SDK_PREFIX) else server_expected
            target.update((package, method) for method in methods)
        require(len(sdk_expected) == 8 and len(server_expected) == 5, 'exact eight/five new methods')
        retained_sdk_raw = pin(RETAINED/'sdk-eight'/'original.log', RETAINED_SDK_LOG_SHA, LOG_CAP)
        sdk_pattern = '^('+'|'.join(sorted(name for _, name in sdk_expected))+')$'
        retained_sdk_argv = [sys.executable, '-B', str(offline), '--exec', driver, 'test', '-json', '-p', '2',
            '-count=1', '-timeout=300s', '-run', sdk_pattern, './internal/bookmarkcreate', './internal/spaceobjects']
        retained_server_pattern = '^('+'|'.join(sorted(name for _, name in server_expected))+')$'
        require(retained_rows[1]['argv'] == retained_sdk_argv and retained_rows[1]['cwd'] == str(source/SDK_PREFIX) and
                retained_rows[1]['logSHA256'] == RETAINED_SDK_LOG_SHA and interrupted_row['cwd'] == str(source) and
                interrupted_row['argv'] == [sys.executable, '-B', str(offline), '--exec', driver, 'test', '-json', '-p', '2',
                    '-count=1', '-timeout=300s', '-run', retained_server_pattern, './internal/server'],
                'exact retained SDK invocation and failed server invocation')
        retained_sdk_events = parse_test_events(retained_sdk_raw, sdk_expected)
        require(retained_sdk_events == retained['sdk-eight'], 'eight exact actual SDK events independently parsed')
        result['sdk-eight'] = retained_sdk_events
        result['retainedActualMethodCount'] = 8
        result['retainedQualification']['sdkLogSHA256'] = RETAINED_SDK_LOG_SHA
        result['retainedQualification']['environmentLogSHA256'] = RETAINED_ENV_LOG_SHA
        save()
        for label, expected, cwd, packages in [('server-five', server_expected, source, ['./internal/server'])]:
            pattern = '^('+ '|'.join(sorted(name for _, name in expected))+')$'
            argv = [sys.executable, '-B', str(offline), '--exec', driver, 'test', '-json', '-p', '2', '-count=1', '-timeout=300s', '-run', pattern]+packages
            log, _ = command(label, argv, cwd, environment, 420)
            result[label] = parse_test_events(frozen(log, LOG_CAP), expected)
            result['newActualMethodCount'] = result[label]['passes']
            save()
        binary = output/'any'
        result['mutations'].append({'operation': 'build-one-native-product', 'state': 'dispatching'})
        save()
        command('native-build', [driver, 'build', '-p', '2', '-o', str(binary), './cmd/any'], source, environment, 360)
        result['nativeProductBuilds'] = 1
        result['mutations'][-1]['state'] = 'completed'
        raw = frozen(binary, 128*MIB)
        require(raw.startswith(b'\x7fELF') and physical(binary).st_mode & 0o111, 'one actual native executable product')
        result['nativeBinary'] = dict(identity(raw), mode=stat.S_IMODE(binary.lstat().st_mode), path=str(binary))
        admitted[str(binary)] = {'identity': identity(raw), 'maximum': 128*MIB,
                                'mode': result['nativeBinary']['mode']}
        metadata_log, _ = command('native-metadata', [driver, 'version', '-m', str(binary)], source, environment, 15)
        metadata = frozen(metadata_log, 65536).decode()
        require('github.com/anyproto/any/cmd/any' in metadata and 'github.com/anyproto/anytype-heart' not in metadata and
                '\tdep\tgithub.com/anyproto/any-sync\tv0.13.8\t' in metadata and
                '.runtime-artifacts/sdk-source' in metadata and known_go['metadata']['GOVERSION'] in metadata, 'same standalone module graph with local SDK overlay')
        result['binaryModuleMetadata'] = identity(metadata.encode())
        result['status'] = 'PASS_13_BOOKMARK_METHODS_8_RETAINED_5_NEW_AND_ONE_NATIVE_PRODUCT'
    except BaseException as error:
        result['status'] = 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') is True for row in result['processes'])
        final_deadline = time.monotonic()+FINAL_SECONDS
        for label, available, action in [
            ('declaredInputsAndProducts', bool(admitted), validate_admitted),
            ('originalSource', baseline is not None, lambda: source_inventory(BASE/'source', checkpoint) == baseline),
            ('compiledSource', candidate_before is not None, lambda: source_inventory(source, checkpoint) == candidate_before),
        ]:
            if not available:
                result.setdefault('finalIntegrity', {})[label] = 'NOT_ADMITTED'
                continue
            try:
                checkpoint()
                require(action(), label+' changed at finalization')
                result.setdefault('finalIntegrity', {})[label] = True
            except BaseException as error:
                result['status'] = 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED'
                result.setdefault('finalIntegrity', {})[label] = False
                result['completionErrors'].append({'boundary': label, 'type': type(error).__name__, 'message': str(error)})
        try:
            if result['status'].startswith('PASS_'):
                require(len(result['processes']) == 4 and result['allOwnedGroupsPositivelyAbsent'] and
                        all(row['exitCode'] == 0 and not row['forcedCleanup'] and not row['cleanupErrors'] and not row['signals'] for row in result['processes']), 'four new normal owned groups')
                require(result['sdk-eight']['passes'] == result['retainedActualMethodCount'] == 8 and
                        result['server-five']['passes'] == result['newActualMethodCount'] == 5 and result['nativeProductBuilds'] == 1 and
                        result['priorTestMethodsReexecuted'] == 0 and len(result['retainedQualification']['qualifiedProcesses']) == 2,
                        'eight retained plus five new methods; two retained plus four new qualified commands')
            result['finalFreeBytes'] = guard()
        except BaseException as error:
            result['status'] = 'FAIL_BOOKMARK_QUALIFICATION_PRESERVED'
            result['completionErrors'].append({'boundary': 'acceptanceAndResources', 'type': type(error).__name__, 'message': str(error)})
        save()
    print(json.dumps({'status': result['status'], 'receipt': str(output/'result.json'),
        'sha256': identity(frozen(output/'result.json'))['sha256'], 'allOwnedGroupsPositivelyAbsent': result['allOwnedGroupsPositivelyAbsent'],
        'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
