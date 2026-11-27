#!/usr/bin/env python3
"""SOURCE ONLY: build the one shared Any CLI from the qualified public union.

The signed unit and fresh Files.Open receipts are required completed inputs.
This controller only copies public source and builds/inspects a new executable;
it never initializes or opens an account, runs that executable, or repeats tests.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import sys
import time

sys.dont_write_bytecode = True
MIB = 1024**2
HERE = Path(__file__).resolve().parent
ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
BASE = ROOT/'lan-progress-native1'
BASE_SHA = 'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a'
BASE_BINARY_SHA = '0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07'
CANDIDATE = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-lifetime-draft-20261127-attempt2')
CANDIDATE_SHA = 'ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896'
PATCH_SHA = '874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f'
FIXTURE = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-source-20261127-attempt2/files_readguard_fresh_linux_test.go')
FIXTURE_SHA = 'b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b'
METHODS = ('TestFilesOpenFreshCachedReaderStopsAtSignedRemoval', 'TestFilesOpenFreshAwaitedFetchDiscardsAfterSignedRemoval')
UNITS_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127')
FRESH_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
TEMP_PARENT = Path('/mnt/development/projects/caches/pinkha-w1-files-readguard-native-20261127')
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
SDK_PREFIX = '.runtime-artifacts/sdk-source/'
HELPER = HERE/'owned_swift_commands.py'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
ROOT_CAP = 128*MIB
TEMP_CAP = 256*MIB
CACHE_GROWTH_CAP = 128*MIB
LOG_CAP = 8*MIB


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def physical(path, directory=False):
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical public path required')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'expected public path kind')
    return info


def frozen(path, maximum=8*MIB):
    before = physical(path)
    require(0<=before.st_size<=maximum, 'bounded public file')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno())==before, 'public file identity before read')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno())==before, 'public file changed during read')
    require(path.lstat()==before and len(raw)==before.st_size, 'public file changed after read')
    return raw


def json_object(raw):
    def unique(rows):
        value = {}
        for name, child in rows:
            require(name not in value, 'duplicate JSON key')
            value[name] = child
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'JSON object required')
    return value


def safe_relative(name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==name, 'exact relative source path')
    return relative


def new_file(path, raw, mode=0o600):
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def source_inventory(root):
    physical(root, True)
    found = {}; stack = [root]; count = 0
    while stack:
        directory = stack.pop()
        fd = os.open(directory, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        try:
            with os.scandir(fd) as entries: names = sorted(entry.name for entry in entries)
        finally:
            os.close(fd)
        for name in names:
            path = directory/name; info = path.lstat(); count += 1
            require(count<=10000 and not stat.S_ISLNK(info.st_mode), 'bounded physical public source tree')
            if stat.S_ISDIR(info.st_mode):
                stack.append(path)
            else:
                require(stat.S_ISREG(info.st_mode), 'regular public source member')
                found[path.relative_to(root).as_posix()] = identity(frozen(path, 128*MIB))
    return found


def allocated(root, maximum_entries=50000):
    """Read only allocation metadata; never remove or rewrite shared cache."""
    physical(root, True)
    used = 0; count = 0; stack = [root]; began = time.monotonic(); seen = set()
    while stack:
        directory = stack.pop()
        try:
            fd = os.open(directory, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        except FileNotFoundError:
            continue  # Only a current owned compiler may retire its transient directory.
        try:
            with os.scandir(fd) as entries: names = [entry.name for entry in entries]
        finally:
            os.close(fd)
        for name in [None]+names:
            path = directory if name is None else directory/name
            try: info = path.lstat()
            except FileNotFoundError: continue
            require(not stat.S_ISLNK(info.st_mode), 'owned allocation tree alias')
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'ordinary owned allocation member')
            key = (info.st_dev, info.st_ino)
            if key not in seen: used += info.st_blocks*512; seen.add(key)
            if name is not None and stat.S_ISDIR(info.st_mode): stack.append(path)
            if name=='original.log': require(info.st_size<=LOG_CAP, 'bounded original build log')
            count += 1
            require(count<=maximum_entries and time.monotonic()-began<5, 'bounded allocation census')
    return used


def main():
    require(not sys.flags.optimize, 'assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--signed-units-receipt', type=Path, required=True)
    parser.add_argument('--signed-units-sha256', required=True)
    parser.add_argument('--fresh-files-receipt', type=Path, required=True)
    parser.add_argument('--fresh-files-sha256', required=True)
    args = parser.parse_args()
    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'authorized Oracle host')
    output = args.output
    require(output.parent==ROOT and re.fullmatch(r'readguard-native[1-9][0-9]{0,2}', output.name), 'exclusive native producer output')
    for path, wanted_parent, digest in [(args.signed_units_receipt, UNITS_PARENT, args.signed_units_sha256),
                                      (args.fresh_files_receipt, FRESH_PARENT, args.fresh_files_sha256)]:
        require(path.name=='result.json' and path.parent.parent==wanted_parent and re.fullmatch(r'attempt[1-9][0-9]{0,2}', path.parent.name), 'fixed prerequisite receipt location')
        require(re.fullmatch(r'[0-9a-f]{64}', digest), 'exact prerequisite receipt hash')
    os.umask(0o077)
    physical(ROOT, True); physical(TEMP_PARENT.parent, True)
    output.mkdir(mode=0o700, exist_ok=False)
    receipt = output/'result.json'; new_file(receipt, b'{}\n')
    temporary = TEMP_PARENT/output.name
    began = time.monotonic(); serial = 0
    admitted = {}; base_expected = None; expected = None; fresh_expected = None
    cache_before = None; temporary_created = False
    result = {'protocol': 'pinkha-files-readguard-native-qualified-v1', 'status': 'RUNNING',
              'baseSourceManifestSHA256': BASE_SHA, 'sdkReadguardPatchSHA256': PATCH_SHA,
              'sdkReadguardCandidateSHA256': CANDIDATE_SHA,
              'commits': {'any': '8fbd1e819fb132ac0e0a848d2ddf5c5714189b81', 'sdk': 'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9'},
              'syncModule': 'github.com/anyproto/any-sync@v0.13.8', 'productionOverlayApplications': 0,
              'nativeAccountProcesses': 0, 'retainedPrivateInputs': 0, 'replayedTests': 0,
              'nativeCLIStarted': False, 'appleRuntimeQualified': False, 'heartProductEmbedded': False,
              'processes': [], 'errors': [], 'completionErrors': [],
              'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
                 'rootAdmissionReserveBytes': ROOT_CAP, 'developmentAdmissionReserveBytes': TEMP_CAP+CACHE_GROWTH_CAP,
                 'rootOutputCapBytes': ROOT_CAP, 'developmentTemporaryCapBytes': TEMP_CAP,
                 'sharedCacheGrowthCapBytes': CACHE_GROWTH_CAP, 'controllerSeconds': 480,
                 'buildSeconds': 360, 'metadataCommandSeconds': 15, 'finalVerificationSeconds': 60,
                 'requiredOuterSeconds': 570, 'workers': 2, 'goMemoryLimit': '1GiB',
                 'allocationEstimateNotMeasuredPeak': True,
                 'estimateBasis': 'Original standalone 1599-source plus78MB binary fitted128MiB; new source adds only qualified guard/test paths. Temporary256MiB and shared-cache growth128MiB are estimates, not native acceptance. Fresh live floors and caps apply throughout; no cache deletion.'}}

    def save_json(path, value):
        nonlocal serial
        require(path.is_relative_to(output), 'owned receipt destination')
        serial += 1
        stage = path.with_name(path.name+'.next-'+str(serial))
        raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        require(len(raw)<=8*MIB, 'bounded public receipt')
        new_file(stage, raw); os.replace(stage, path)
        fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def save():
        result['seconds'] = time.monotonic()-began; save_json(receipt, result)

    def pin(path, digest, maximum=8*MIB):
        raw = frozen(path, maximum); require(identity(raw)['sha256']==digest, 'public source/receipt hash mismatch')
        admitted[str(path)] = {'identity': identity(raw), 'maximum': maximum}
        return raw

    def guard(admit=False, final=False):
        require(final or time.monotonic()-began<480, 'bounded native producer deadline')
        require(not (output/'abort').exists(), 'owned abort')
        free = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', ROOT_FLOOR, ROOT_CAP), ('development', DEV_FLOOR, TEMP_CAP+CACHE_GROWTH_CAP)]:
            require(free[name]>=floor+(reserve if admit else 0), name+' unchanged capacity gate')
            result.setdefault('minimumFreeBytes', {})[name] = min(free[name], result.get('minimumFreeBytes', {}).get(name, free[name]))
        root_used = allocated(output, 12000)
        require(root_used<=ROOT_CAP, 'bounded entire native producer output')
        result['peakRootOutputBytes'] = max(root_used, result.get('peakRootOutputBytes', 0))
        if temporary_created:
            temp_used = allocated(temporary)
            require(temp_used<=TEMP_CAP, 'bounded owned native compiler temporary files')
            result['peakTemporaryBytes'] = max(temp_used, result.get('peakTemporaryBytes', 0))
        if cache_before is not None:
            require(CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET, 'same qualified cache placement')
            cache_used = allocated(CACHE_TARGET)
            require(cache_used-cache_before<=CACHE_GROWTH_CAP, 'bounded shared-cache allocation growth')
            result['peakObservedSharedCacheGrowthBytes'] = max(0, cache_used-cache_before, result.get('peakObservedSharedCacheGrowthBytes', 0))
        return free

    def observe():
        try: guard(); return None
        except BaseException as error: return type(error).__name__+': '+str(error)

    def command(label, argv, cwd, env, seconds):
        def persist(path, value):
            require(path.parent==output/label and path.name in ('started.json', 'result.json'), 'owned command receipt')
            save_json(path, value); save()
        log, row = owned.run(output/label, argv, cwd, env, seconds, observe, persist,
            lambda path: identity(frozen(path, LOG_CAP))['sha256'], result['processes'])
        save(); return log, row

    try:
        result['initialFreeBytes'] = guard(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available>=3*1024**3, 'native producer memory admission')
        result['memAvailableBefore'] = available
        own_path = Path(__file__).resolve(); own = frozen(own_path)
        admitted[str(own_path)] = {'identity': identity(own), 'maximum': 8*MIB}; result['controller'] = identity(own)
        pin(HELPER, HELPER_SHA)
        proof = json_object(pin(HELPER_PROOF, HELPER_PROOF_SHA))
        require(proof['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and proof['helperSHA256']==HELPER_SHA and proof['allOwnedGroupsPositivelyAbsent'], 'reused qualified owned-command helper')
        require(len(proof['methods'])==5 and all(row['status']=='PASS' for row in proof['methods']), 'five prior owned lifecycle controls')
        spec = importlib.util.spec_from_file_location('readguard_native_owned', HELPER)
        owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned); owned.install_interrupt_handlers()
        result['reusedOwnershipReceiptSHA256'] = HELPER_PROOF_SHA
        require(CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET, 'original qualified cache link')
        physical(CACHE_TARGET, True); cache_before = allocated(CACHE_TARGET)
        require(output.stat().st_dev!=CACHE_TARGET.stat().st_dev, 'explicit two-filesystem layout')

        base_expected = json_object(pin(BASE/'source-manifest.json', BASE_SHA))['files']
        require(len(base_expected)==1599, 'original source1599')
        require(source_inventory(BASE/'source')==base_expected, 'original public source unchanged')
        base_binary = identity(pin(BASE/'any', BASE_BINARY_SHA, 128*MIB))
        draft = json_object(pin(CANDIDATE/'manifest.json', CANDIDATE_SHA))
        pin(CANDIDATE/'sdk-files-readguard.patch', PATCH_SHA)
        require(draft['baseCurrentSourceManifestSHA256']==BASE_SHA and draft['patch']['sha256']==PATCH_SHA, 'guard candidate base')
        require(len(draft['paths'])==10 and draft['productionPaths']==7 and draft['testPaths']==3, 'exact seven production and three signed-test paths')
        union = dict(base_expected)
        require(sum(name.startswith(SDK_PREFIX) for name in union)==718, 'original SDK718')
        for name, delta in sorted(draft['paths'].items()):
            safe_relative(name); require(name.startswith('internal/'), 'qualified SDK internal overlay')
            key = SDK_PREFIX+name
            require(union.get(key)==delta['before'], 'exact overlay before-image')
            raw = pin(CANDIDATE/name, delta['after']['sha256'])
            require(identity(raw)==delta['after'], 'exact overlay after-image')
            union[key] = identity(raw)
        sdk_guard = {name.removeprefix(SDK_PREFIX): row for name, row in union.items() if name.startswith(SDK_PREFIX)}
        require(len(union)==1606 and len(sdk_guard)==725, 'guard-only source closure')
        fixture = identity(pin(FIXTURE, FIXTURE_SHA)); require(SDK_PREFIX+FIXTURE.name not in union, 'one fresh test source')
        union[SDK_PREFIX+FIXTURE.name] = fixture
        fresh_expected = {name.removeprefix(SDK_PREFIX): row for name, row in union.items() if name.startswith(SDK_PREFIX)}
        require(len(union)==1607 and len(fresh_expected)==726, 'full source1607 and SDK726')

        units = json_object(pin(args.signed_units_receipt, args.signed_units_sha256))
        fresh = json_object(pin(args.fresh_files_receipt, args.fresh_files_sha256))
        for value, wanted in [(units, 'PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE'), (fresh, 'PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2')]:
            require(value['status']==wanted and value['allOwnedGroupsPositivelyAbsent'] and value['errors']==[] and value['completionErrors']==[], 'completed actual prerequisite')
        ua = units['sourceAdmission']
        require(ua['baseManifestSHA256']==BASE_SHA and ua['candidateManifestSHA256']==CANDIDATE_SHA and ua['candidatePatchSHA256']==PATCH_SHA, 'actual signed unit source identity')
        require(units['actualMethods']['totalRuns']==35 and units['actualMethods']['totalPasses']==35 and units['actualMethods']['skips']==0, 'actual signed unit35')
        require(json_object(pin(args.signed_units_receipt.parent/'source-before.json', ua['sourceManifest']['sha256']))==sdk_guard, 'actual signed SDK725 closure')
        require(fresh['baseSourceManifestSHA256']==BASE_SHA and fresh['sdkReadguardCandidateSHA256']==CANDIDATE_SHA and fresh['sdkReadguardPatchSHA256']==PATCH_SHA and fresh['fixtureSource']==fixture, 'actual fresh SDK source identity')
        require(fresh['actualMethods']=={'names': sorted(METHODS), 'totalRuns': 2, 'totalPasses': 2, 'skips': 0}, 'two exact actual Files.Open methods')
        require(fresh['retainedPrivateInputs']==0 and fresh['actualOSDenialVerified'] is True, 'fresh-only actual OS-isolated SDK')
        require(json_object(pin(args.fresh_files_receipt.parent/'source-before.json', fresh['sourceManifestSHA256']))==fresh_expected, 'actual fresh SDK726 manifest')
        fresh_source = args.fresh_files_receipt.parent/'sdk-source'
        require(source_inventory(fresh_source)==fresh_expected, 'actual qualified SDK source bytes')
        result['qualifications'] = {'synthetic21': {'path': str(args.signed_units_receipt), 'sha256': args.signed_units_sha256},
                                    'freshFilesOpen2': {'path': str(args.fresh_files_receipt), 'sha256': args.fresh_files_sha256}}
        result['freshFilesFixture'] = fixture
        require(sum(row['bytes'] for row in union.values())+base_binary['bytes']<=ROOT_CAP-8*MIB, 'source and prior executable leave bounded output reserve')
        result['measuredBaseAllocationInputs'] = {'sourceLogicalBytes': sum(row['bytes'] for row in union.values()), 'priorNativeBinary': base_binary, 'additionalReserveBytes': 8*MIB}
        source = output/'source'; source.mkdir(mode=0o700)
        for index, (name, wanted) in enumerate(sorted(union.items())):
            safe_relative(name)
            if index%64==0: guard()
            original = fresh_source/name.removeprefix(SDK_PREFIX) if name.startswith(SDK_PREFIX) else BASE/'source'/name
            raw = frozen(original, 128*MIB); require(identity(raw)==wanted, 'exact qualified public source copy')
            target = source/name; target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            new_file(target, raw, stat.S_IMODE(original.lstat().st_mode))
        expected = union
        require(source_inventory(source)==expected, 'complete native union after copy')
        changed = {name for name in set(expected)|set(base_expected) if expected.get(name)!=base_expected.get(name)}
        require(changed=={SDK_PREFIX+name for name in draft['paths']}|{SDK_PREFIX+FIXTURE.name}, 'only qualified guard and fresh test source delta')
        result['productionOverlayApplications'] = 1; result['sourceChanges'] = sorted(changed)
        save_json(output/'source-manifest.json', {'protocol': 'pinkha-files-readguard-native-source-v1', 'baseSourceManifestSHA256': BASE_SHA,
            'sdkReadguardPatchSHA256': PATCH_SHA, 'sdkReadguardCandidateSHA256': CANDIDATE_SHA, 'files': expected})
        result['sourceManifestSHA256'] = identity(frozen(output/'source-manifest.json'))['sha256']
        result['sourceFiles'] = len(expected)

        if not TEMP_PARENT.exists(): TEMP_PARENT.mkdir(mode=0o700)
        physical(TEMP_PARENT, True); temporary.mkdir(mode=0o700, exist_ok=False); temporary_created = True
        physical(temporary, True); require(temporary.stat().st_dev==CACHE_TARGET.stat().st_dev, 'development compiler temporary placement')
        env = {key: value for key, value in os.environ.items() if not key.startswith(('ANY_', 'PINKHA_', 'PYTHON', 'CGO_', 'GO'))}
        env.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE), GOMODCACHE='/root/go/pkg/mod',
                   GOTMPDIR=str(temporary), TMPDIR=str(temporary), CGO_ENABLED='1', GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off')
        driver = Path('/usr/local/bin/go').resolve(strict=True); driver_raw = frozen(driver, 128*MIB)
        admitted[str(driver)] = {'identity': identity(driver_raw), 'maximum': 128*MIB}
        metadata_log, _ = command('toolchain', [str(driver), 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH'], source, env, 15)
        metadata = json_object(frozen(metadata_log, 65536))
        require(metadata['GOOS']==metadata['GOHOSTOS']=='linux' and metadata['GOARCH']==metadata['GOHOSTARCH']=='arm64', 'original Linux arm64 producer')
        require(fresh['goToolchain']['driver']=={'path': str(driver), **identity(driver_raw)} and fresh['goToolchain']['metadata']==metadata, 'same actual Files.Open toolchain')
        tools = {}
        for name in ('compile', 'link'):
            path = (Path(metadata['GOTOOLDIR'])/name).resolve(strict=True); raw = frozen(path, 128*MIB)
            admitted[str(path)] = {'identity': identity(raw), 'maximum': 128*MIB}
            tools[name] = {'path': str(path), **identity(raw)}
        require(tools==fresh['goToolchain']['tools'], 'same qualified compiler and linker bytes')
        result['goToolchain'] = {'driver': {'path': str(driver), **identity(driver_raw)}, 'metadata': metadata, 'tools': tools}
        result['environment'] = {name: env[name] for name in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB')}
        binary = output/'any'
        _, build_row = command('native-build', [str(driver), 'build', '-p', '2', '-o', str(binary), './cmd/any'], source, env, 360)
        result['buildExitCode'] = build_row['exitCode']
        built = frozen(binary, 128*MIB)
        require(built.startswith(b'\x7fELF') and physical(binary).st_mode&0o111, 'new executable ELF product')
        result['binarySHA256'] = identity(built)['sha256']; result['binaryBytes'] = len(built)
        admitted[str(binary)] = {'identity': identity(built), 'maximum': 128*MIB}
        module_log, _ = command('binary-module-metadata', [str(driver), 'version', '-m', str(binary)], source, env, 15)
        module_text = frozen(module_log, 65536).decode()
        require('github.com/anyproto/any/cmd/any' in module_text and 'github.com/anyproto/anytype-heart' not in module_text, 'standalone Any product, not Heart binding')
        require('\tdep\tgithub.com/anyproto/any-sync\tv0.13.8\t' in module_text and metadata['GOVERSION'] in module_text, 'actual linked Sync and Go versions')
        require('\tdep\tgithub.com/anyproto/any-sync-sdk\t' in module_text and '.runtime-artifacts/sdk-source' in module_text, 'actual local qualified SDK replacement')
        result['binaryModuleMetadata'] = identity(module_text.encode())
        require(source_inventory(source)==expected and source_inventory(fresh_source)==fresh_expected, 'qualified native and fresh SDK sources unchanged')
        result['status'] = 'PASS_NATIVE_BUILD_AND_FRESH_FILES_OPEN2'
    except BaseException as error:
        result['status'] = 'FAIL_NATIVE_BUILD_PRESERVED'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent'] = bool(result['processes']) and all(row.get('processGroupAbsent') for row in result['processes'])
        final_started = time.monotonic()
        try:
            for name, wanted in admitted.items():
                require(time.monotonic()-final_started<60, 'bounded final public input verification')
                require(identity(frozen(Path(name), wanted['maximum']))==wanted['identity'], 'public prerequisite/product changed')
            if base_expected is not None:
                require(source_inventory(BASE/'source')==base_expected, 'original native source unchanged')
                result['baseSourceUnchanged'] = True
            if fresh_expected is not None and 'fresh_source' in locals():
                require(source_inventory(fresh_source)==fresh_expected, 'qualified fresh source unchanged')
                result['qualifiedFreshSourceUnchanged'] = True
            if expected is not None:
                require(source_inventory(output/'source')==expected, 'new native source unchanged')
                result['sourceUnchanged'] = True
            require(time.monotonic()-final_started<60, 'bounded complete source finalization')
            result['admittedPublicInputsUnchanged'] = True
            if result['status'].startswith('PASS_'):
                require(len(result['processes'])==3 and result['allOwnedGroupsPositivelyAbsent'], 'three closed owned commands')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['processes']), 'three normal owned completions')
            result['finalFreeBytes'] = guard(final=True)
        except BaseException as error:
            result['status'] = 'FAIL_NATIVE_BUILD_PRESERVED'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        save()
    print(json.dumps({'status': result['status'], 'receipt': str(receipt), 'sha256': identity(frozen(receipt))['sha256'],
                      'allOwnedGroupsPositivelyAbsent': result['allOwnedGroupsPositivelyAbsent'], 'errors': result['errors'], 'completionErrors': result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
