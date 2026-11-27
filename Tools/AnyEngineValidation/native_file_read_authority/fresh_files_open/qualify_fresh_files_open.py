#!/usr/bin/env python3
"""SOURCE ONLY: qualify two fresh actual SDK Files.Open authority boundaries.

Only new fixture-owned identities/data are used. The prior signed unit receipt
is a public prerequisite; no retained account, private database, key, snapshot
or raw ACL export is read. No Any CLI process or original-pair operation runs.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import signal
import stat
import sys
import time

MIB = 1024**2
ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127')
UNITS_PARENT = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127')
HERE = Path(__file__).resolve().parent
SOURCE_FIXTURE = HERE/'files_readguard_fresh_linux_test.go'
FIXTURE_SHA = 'b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b'
BASE_MANIFEST = ROOT/'lan-progress-native1/source-manifest.json'
BASE_SHA = 'e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a'
CANDIDATE = Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-lifetime-draft-20261127-attempt2')
CANDIDATE_SHA = 'ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896'
PATCH_SHA = '874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
SECCOMP = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
SECCOMP_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OWNED = HERE/'owned_swift_commands.py'
OWNED_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNED_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
OWNED_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
METHODS = ('TestFilesOpenFreshCachedReaderStopsAtSignedRemoval', 'TestFilesOpenFreshAwaitedFetchDiscardsAfterSignedRemoval')
PACKAGE = 'github.com/anyproto/any-sync-sdk'
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
ROOT_RESERVE = 32*MIB
DEV_RESERVE = 512*MIB
OWNED_CAP = 384*MIB
LOG_CAP = 8*MIB


def physical(path, directory=False):
    assert path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical input path required'
    info = path.lstat()
    assert stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    return info


def frozen(path, maximum=4*MIB):
    before = physical(path)
    assert before.st_size<=maximum
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        assert os.fstat(stream.fileno())==before
        data = stream.read(maximum+1)
        assert os.fstat(stream.fileno())==before
    assert path.lstat()==before and len(data)==before.st_size
    return data


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write_new(path, data, mode=0o600):
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def inventory(root):
    physical(root, True)
    found = {}; stack = [root]
    while stack:
        directory = stack.pop()
        fd = os.open(directory, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        try:
            with os.scandir(fd) as entries: names = sorted(entry.name for entry in entries)
        finally: os.close(fd)
        for name in names:
            path = directory/name; info = path.lstat()
            assert not stat.S_ISLNK(info.st_mode)
            if stat.S_ISDIR(info.st_mode): stack.append(path)
            else:
                assert stat.S_ISREG(info.st_mode)
                found[path.relative_to(root).as_posix()] = identity(frozen(path))
        assert len(found)<=800 and len(stack)<=800
    return found


def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification requires assertions enabled')
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--signed-units-receipt', type=Path, required=True)
    parser.add_argument('--signed-units-sha256', required=True)
    args = parser.parse_args()
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert args.output.parent==PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', args.output.name)
    assert args.signed_units_receipt.parent.parent==UNITS_PARENT
    assert re.fullmatch(r'attempt[1-9][0-9]{0,2}', args.signed_units_receipt.parent.name)
    assert args.signed_units_receipt.name=='result.json' and re.fullmatch(r'[0-9a-f]{64}', args.signed_units_sha256)
    os.umask(0o077)
    physical(PARENT.parent, True)
    if not PARENT.exists(): PARENT.mkdir(mode=0o700)
    physical(PARENT, True)
    output = args.output; output.mkdir(mode=0o700, exist_ok=False)
    receipt = output/'result.json'; write_new(receipt, b'{}\n')
    source = output/'sdk-source'
    prior_source = args.signed_units_receipt.parent/'sdk-source'
    began = time.monotonic(); serial = 0
    admitted = {}; source_expected = None; prior_expected = None
    result = {'protocol': 'pinkha-fresh-files-open-signed-authority-v1', 'status': 'RUNNING',
              'baseSourceManifestSHA256': BASE_SHA, 'sdkReadguardCandidateSHA256': CANDIDATE_SHA,
              'sdkReadguardPatchSHA256': PATCH_SHA, 'retainedPrivateInputs': 0,
              'retainedAccountOpens': 0, 'nativeCLIServers': 0, 'originalRoleMutations': 0,
              'actualOSDenialVerified': False, 'processes': [], 'errors': [], 'completionErrors': [],
              'resourcePolicy': {'rootFloorBytes': ROOT_FLOOR, 'developmentFloorBytes': DEV_FLOOR,
                'rootAdmissionReserveBytes': ROOT_RESERVE, 'developmentAdmissionReserveBytes': DEV_RESERVE,
                'entireOwnedOutputCapBytes': OWNED_CAP, 'logCapBytes': LOG_CAP,
                'controllerDeadlineSeconds': 420, 'metadataCommandSeconds': 15,
                'compileAndTwoMethodCommandSeconds': 360, 'testBinaryTimeoutSeconds': 90,
                'requiredOuterTimeoutSeconds': 480, 'workers': 2, 'goMemoryLimit': '1GiB',
                'allocationEstimateNotMeasuredPeak': True,
                'estimateBasis': 'Existing qualified native binary is78MB and SDK source6.6MB; source/product/freshCARs/logs plus bounded compiler temporary output cap384MiB, separate128MiB shared-cache growth allowance. No cache deletion/relocation. Full SDK-root test compilation has not yet been measured.'}}

    def save_json(path, value):
        nonlocal serial
        assert path.is_relative_to(output)
        serial += 1
        temporary = path.with_name(path.name+'.next-'+str(serial))
        write_new(temporary, (json.dumps(value, sort_keys=True, indent=2)+'\n').encode())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def save():
        result['seconds'] = time.monotonic()-began
        save_json(receipt, result)

    def save_command(path, value):
        assert path.parent in (output/'toolchain', output/'files-open2') and path.name in ('started.json', 'result.json')
        save_json(path, value); save()

    def pin(path, sha, maximum=4*MIB):
        data = frozen(path, maximum); assert identity(data)['sha256']==sha
        admitted[str(path)] = {'identity': identity(data), 'maximum': maximum}
        return data

    def capacity(admit=False):
        values = {'root': shutil.disk_usage('/').free, 'development': shutil.disk_usage('/mnt/development').free}
        for name, floor, reserve in [('root', ROOT_FLOOR, ROOT_RESERVE), ('development', DEV_FLOOR, DEV_RESERVE)]:
            result.setdefault('minimumFreeBytes', {})[name] = min(values[name], result.get('minimumFreeBytes', {}).get(name, values[name]))
            assert values[name]>=floor+(reserve if admit else 0), name+' unchanged capacity gate'
        assert time.monotonic()-began<420 and not (output/'abort').exists(), 'bounded fresh Files.Open qualification'
        return values

    def allocation():
        count = 0; used = 0; started = time.monotonic()
        for directory, dirs, files in os.walk(output, followlinks=False):
            for name in dirs:
                assert not (Path(directory)/name).is_symlink()
            for name in files:
                path = Path(directory)/name
                try: info = path.lstat()
                except FileNotFoundError: continue  # Only this owned compiler/SDK can retire a transient member.
                assert stat.S_ISREG(info.st_mode)
                used += max(info.st_size, info.st_blocks*512); count += 1
                if name=='original.log': assert info.st_size<=LOG_CAP
            assert count<=20000 and time.monotonic()-started<5
        assert used<=OWNED_CAP, 'bounded source/product/fresh fixture/log/temp output'
        result['peakOwnedBytes'] = max(used, result.get('peakOwnedBytes', 0))

    def observe():
        try: capacity(); allocation(); return None
        except BaseException as error: return type(error).__name__+': '+str(error)

    def interrupted(number, _frame):
        raise RuntimeError('fresh Files.Open qualifier interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    try:
        own_path = Path(__file__).resolve(); own_raw = frozen(own_path)
        admitted[str(own_path)] = {'identity': identity(own_raw), 'maximum': 4*MIB}
        result['controller'] = identity(own_raw)
        pin(OWNED, OWNED_SHA)
        lifecycle = json.loads(pin(OWNED_PROOF, OWNED_PROOF_SHA))
        assert lifecycle['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
        assert lifecycle['helperSHA256']==OWNED_SHA and lifecycle['allOwnedGroupsPositivelyAbsent']
        assert len(lifecycle['methods'])==5 and all(row['status']=='PASS' for row in lifecycle['methods'])
        specification = importlib.util.spec_from_file_location('fresh_files_owned', OWNED)
        owned = importlib.util.module_from_spec(specification); specification.loader.exec_module(owned)
        result['reusedOwnershipReceiptSHA256'] = OWNED_PROOF_SHA
        result['admissionFreeBytes'] = capacity(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        assert available>=3*1024**3
        result['memAvailableBefore'] = available
        assert CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET
        physical(CACHE_TARGET, True)
        assert CACHE_TARGET.stat().st_dev==output.stat().st_dev
        unit = json.loads(pin(args.signed_units_receipt, args.signed_units_sha256, 8*MIB))
        assert unit['status']=='PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE'
        assert unit['allOwnedGroupsPositivelyAbsent'] and unit['errors']==[] and unit['completionErrors']==[]
        assert unit['actualMethods']['totalRuns']==unit['actualMethods']['totalPasses']==35 and unit['actualMethods']['skips']==0
        assert unit['sourceAdmission']['baseManifestSHA256']==BASE_SHA
        assert unit['sourceAdmission']['candidateManifestSHA256']==CANDIDATE_SHA and unit['sourceAdmission']['candidatePatchSHA256']==PATCH_SHA
        assert unit['sourceAdmission']['sourcePhysicalPath']==str(prior_source)
        base = json.loads(pin(BASE_MANIFEST, BASE_SHA))['files']; prefix = '.runtime-artifacts/sdk-source/'
        expected = {name.removeprefix(prefix): value for name, value in base.items() if name.startswith(prefix)}
        assert len(base)==1599 and len(expected)==718
        draft = json.loads(pin(CANDIDATE/'manifest.json', CANDIDATE_SHA))
        pin(CANDIDATE/'sdk-files-readguard.patch', PATCH_SHA)
        assert draft['baseCurrentSourceManifestSHA256']==BASE_SHA and draft['patch']['sha256']==PATCH_SHA
        assert len(draft['paths'])==10 and draft['productionPaths']==7 and draft['testPaths']==3
        for name, change in draft['paths'].items():
            assert expected.get(name)==change['before']
            expected[name] = change['after']
        prior_expected = json.loads(pin(args.signed_units_receipt.parent/'source-before.json', unit['sourceAdmission']['sourceManifest']['sha256']))
        assert prior_expected==expected and len(expected)==725 and inventory(prior_source)==prior_expected
        result['reusedSignedUnitReceiptSHA256'] = args.signed_units_sha256
        source.mkdir(mode=0o700)
        for index, (name, wanted) in enumerate(sorted(prior_expected.items())):
            if index%64==0: capacity()
            rel = PurePosixPath(name)
            assert not rel.is_absolute() and str(rel)==name and '..' not in rel.parts
            data = frozen(prior_source/name); assert identity(data)==wanted
            target = source/name; target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            write_new(target, data, 0o644)
        assert inventory(source)==expected
        fixture = pin(SOURCE_FIXTURE, FIXTURE_SHA)
        assert SOURCE_FIXTURE.name not in expected
        write_new(source/SOURCE_FIXTURE.name, fixture, 0o644)
        expected[SOURCE_FIXTURE.name] = identity(fixture)
        source_expected = expected
        assert len(expected)==726 and inventory(source)==source_expected
        write_new(output/'source-before.json', (json.dumps(source_expected, sort_keys=True, indent=2)+'\n').encode())
        result['sourceManifestSHA256'] = identity(frozen(output/'source-before.json'))['sha256']
        result['fixtureSource'] = identity(fixture)
        pin(OFFLINE, OFFLINE_SHA, 65536); pin(SECCOMP, SECCOMP_SHA)
        result['OSPolicy'] = {'helperSHA256': OFFLINE_SHA, 'librarySHA256': SECCOMP_SHA,
                             'installedBeforeSDKInitialization': True, 'newProcessConnectAndSendtoMustReturnEPERM': True}
        temporary = output/'go-tmp'; temporary.mkdir(mode=0o700)
        fixtures = output/'fixtures'; fixtures.mkdir(mode=0o700)
        env = {key: value for key, value in os.environ.items() if not key.startswith(('ANY_', 'PINKHA_', 'PYTHON'))}
        env.update(GOTOOLCHAIN='local', GOMAXPROCS='2', GOMEMLIMIT='1GiB', GOCACHE=str(CACHE),
                   GOMODCACHE='/root/go/pkg/mod', GOTMPDIR=str(temporary), TMPDIR=str(temporary),
                   CGO_ENABLED='1', GOWORK='off', GOFLAGS='-mod=readonly', GOPROXY='off', GOSUMDB='off',
                   PINKHA_FRESH_FILES_FIXTURE_ROOT=str(fixtures))
        driver = Path('/usr/local/bin/go').resolve(strict=True)
        raw_driver = frozen(driver, 128*MIB)
        admitted[str(driver)] = {'identity': identity(raw_driver), 'maximum': 128*MIB}
        python = Path(sys.executable).resolve(strict=True); raw_python = frozen(python, 32*MIB)
        admitted[str(python)] = {'identity': identity(raw_python), 'maximum': 32*MIB}
        metadata_log, metadata_command = owned.run(output/'toolchain', [str(driver), 'env', '-json', 'GOVERSION', 'GOROOT', 'GOTOOLDIR', 'GOHOSTOS', 'GOHOSTARCH', 'GOOS', 'GOARCH'],
            source, env, 15, observe, save_command, lambda path: identity(frozen(path, LOG_CAP))['sha256'], result['processes'])
        metadata = json.loads(frozen(metadata_log, 65536))
        assert metadata['GOOS']==metadata['GOHOSTOS']=='linux' and metadata['GOARCH']==metadata['GOHOSTARCH']=='arm64'
        assert re.fullmatch(r'go[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[a-z0-9.-]*)?', metadata['GOVERSION'])
        tool_dir = Path(metadata['GOTOOLDIR']).resolve(strict=True); physical(tool_dir, True)
        tool_rows = {}
        for name in ('compile', 'link'):
            path = (tool_dir/name).resolve(strict=True); raw = frozen(path, 128*MIB)
            admitted[str(path)] = {'identity': identity(raw), 'maximum': 128*MIB}
            tool_rows[name] = {'path': str(path), **identity(raw)}
        result['goToolchain'] = {'driver': {'path': str(driver), **identity(raw_driver)}, 'metadata': metadata, 'tools': tool_rows}
        assert unit['goToolchain']['canonicalDriverPath']==str(driver) and unit['goToolchain']['driver']==identity(raw_driver)
        assert unit['goToolchain']['observedEnvironment']==metadata, 'same actual signed-unit Go toolchain'
        for name, actual in tool_rows.items():
            previous = unit['goToolchain']['tools'][name]
            assert previous['canonicalPath']==actual['path']
            assert {key: previous[key] for key in ('bytes','sha256')}=={key: actual[key] for key in ('bytes','sha256')}
        result['OSExecPython'] = {'path': str(python), **identity(raw_python)}
        result['environment'] = {key: env[key] for key in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB','PINKHA_FRESH_FILES_FIXTURE_ROOT')}
        exec_prefix = shlex.join([str(python), '-B', str(OFFLINE), '--exec'])
        pattern = '^('+'|'.join(sorted(METHODS))+')$'
        argv = [str(driver), 'test', '-json', '-count=1', '-p=2', '-timeout=90s', '-exec', exec_prefix, '-run', pattern, '.']
        command_error = None
        try:
            log_path, command = owned.run(output/'files-open2', argv, source, env, 360, observe, save_command,
                lambda path: identity(frozen(path, LOG_CAP))['sha256'], result['processes'])
        except BaseException as error:
            command_error = error
        log_path = output/'files-open2/original.log'
        if not log_path.is_file():
            if command_error is not None: raise command_error
            raise AssertionError('no actual SDK test log')
        raw_log = frozen(log_path, LOG_CAP); events = []
        for line in raw_log.splitlines():
            try: event = json.loads(line)
            except json.JSONDecodeError: continue
            if event.get('Action') in ('run','pass','fail','skip'):
                events.append({key: event[key] for key in ('Action','Package','Test','Elapsed') if key in event})
        result['events'] = events; result['rawLog'] = identity(raw_log); save()
        if command_error is not None: raise command_error
        wanted = Counter({(PACKAGE, name): 1 for name in METHODS})
        for action in ('run','pass'):
            actual = Counter((e['Package'],e['Test']) for e in events if e['Action']==action and 'Test' in e)
            assert actual==wanted, 'two exact actual SDK methods required'
        assert not any(e['Action'] in ('fail','skip') for e in events)
        assert Counter(e['Package'] for e in events if e['Action']=='pass' and 'Test' not in e)==Counter({PACKAGE:1})
        assert command['exitCode']==0 and command['processGroupAbsent'] and not command['forcedCleanup'] and not command['cleanupErrors']
        result['actualMethods'] = {'names': sorted(METHODS), 'totalRuns': 2, 'totalPasses': 2, 'skips': 0}
        result['actualOSDenialVerified'] = True  # Both pinned methods assert live policy + EPERM before any SDK.Open.
        assert sorted(path.name for path in fixtures.iterdir())==sorted(METHODS)
        assert inventory(source)==source_expected and inventory(prior_source)==prior_expected
        result['status'] = 'PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2'
    except BaseException as error:
        result['status'] = 'FAIL_FRESH_SYNTHETIC_FILES_OPEN2'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT): signal.signal(number, signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') for row in result['processes'])
        try:
            for name, wanted in admitted.items():
                assert identity(frozen(Path(name), wanted['maximum']))==wanted['identity']
            result['usedPublicInputsUnchanged'] = True
            if source_expected is not None:
                assert inventory(source)==source_expected; result['sourceUnchanged'] = True
            if prior_expected is not None:
                assert inventory(prior_source)==prior_expected; result['qualifiedSignedUnitSourceUnchanged'] = True
            if result['status'].startswith('PASS_'):
                assert len(result['processes'])==2 and result['allOwnedGroupsPositivelyAbsent']
                assert all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['processes'])
            allocation(); result['freeAfter'] = capacity()
        except BaseException as error:
            result['status'] = 'FAIL_FRESH_SYNTHETIC_FILES_OPEN2'
            result['completionErrors'].append({'type': type(error).__name__, 'message': str(error)})
        save()
    print(json.dumps({'status': result['status'], 'result': str(receipt), 'sha256': identity(frozen(receipt, 8*MIB))['sha256']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
