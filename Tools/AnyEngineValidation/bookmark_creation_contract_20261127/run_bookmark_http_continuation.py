#!/usr/bin/env python3
"""Qualify only ten remaining Bookmark HTTP methods against the retained build.

The original 9aa1 component receipt remains FAIL. Its actual 21 passes are
reused without compilation or replay. New, exclusive 0700 output and fixture
directories correct inherited setgid setup; no production or test byte changes.
Complete Products identity is a later observation, never attributed to the
failed producer. Current source, copied inputs and original C3 dependencies
must remain exact before and after the one owned skip-build command.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
import types


PARENT = Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127')
ORIGINAL = PARENT/'components-attempt1'
CONTROL = PARENT/'prepared1/qualification'
CONTROLLER = CONTROL/'run_bookmark_components.py'
CONTROLLER_SHA = '6e715e0dc316f3b08ded6322121339a61f2044b55a909cb61dca4fa72852d9e0'
ORIGINAL_SHA = '9aa1b527c5df731f27f103cdeab2d93f672ba5d13bd9061167826ce5ef6aa465'
ORIGINAL_LOG_SHA = 'cf3eecc59f0d97efc0b760d1bbbd2da8d70d2e2c56898e745a48aea4bae8efb4'
SOURCE_SHA = '01c2db0d00d02e123c4697fcf034b4afe8214430fabf406e64192379af2da7c5'
MANIFEST_SHA = 'eb2b91a339f9f2f9ccaf30220fc1fc52781d960e3efdc5d68a8ae270dcb9ef83'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
CRYPTO_SHA = 'faf63670a56f28a2c0ce4aa61d89957c7987074cd7ade6d483acb4a07d2ba1f4'
SHARED_CRYPTO_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
HEADERS_SHA = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
LIFECYCLE_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
CUSTODY_SHA = 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
HTTP_METHODS = (
    'testAccountSwitchInsideFinalReadCheckIsRefused',
    'testCancellationWhileFinalReadCheckSuspendsWithholdsParsedFrame',
    'testCancelledEntryAndInvalidRequestHaveNoHTTPDispatch',
    'testGenericUnicodeWorkspaceConstructionRemainsLazyAndMakesNoHTTPCall',
    'testGuardedCreationRequiresNativeCapabilityBeforeJournalOrAnyPOST',
    'testMissingOrMistypedCapabilityRefusesBeforeFramePOST',
    'testOwnerRetiredDuringFinalAccountResponseIsRefused',
    'testReadAuthorizationRefusalAtDispatchResponseAndFinalDelivery',
    'testReaderUsesOnlyCapabilityAndFrameReadsWithExactRequest',
    'testResponseScopeAccountChangeAndOversizeNeverDeliverFrame',
)
MIB = 1024**2
ROOT_FLOOR, DEV_FLOOR = 2*1024**3, 512*MIB
OWNED_CAP, LOG_CAP, FIXTURE_CAP = 64*MIB, 8*MIB, 16*MIB
TOTAL_SECONDS, SWIFT_SECONDS, FINAL_SECONDS = 900, 120, 120


def read_exact(path, wanted, maximum=65536):
    """Capture a bounded physical public source before it is imported or used."""
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
    try:
        before = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_uid,
            row.st_gid, row.st_nlink, row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        assert stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum
        assert identity(before) == identity(path.lstat())
        chunks, count = [], 0
        while True:
            part = os.read(fd, min(MIB, maximum+1-count))
            if not part:
                break
            chunks.append(part)
            count += len(part)
            assert count <= maximum
        assert count == before.st_size
        assert identity(before) == identity(os.fstat(fd)) == identity(path.lstat())
    finally:
        os.close(fd)
    raw = b''.join(chunks)
    assert hashlib.sha256(raw).hexdigest() == wanted, str(path)+' pinned bytes changed'
    return raw


def load_exact(path, name, wanted):
    raw = read_exact(path, wanted)
    ast.parse(raw)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    assert read_exact(path, wanted) == raw
    return module


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    if sys.flags.optimize:
        raise RuntimeError('assertions must remain enabled')
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controller-sha', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0 and os.uname().nodename == 'torah-social'
    assert re.fullmatch(r'[0-9a-f]{64}', args.controller_sha)
    own = Path(__file__).absolute()
    own_raw = read_exact(own, args.controller_sha)
    ast.parse(own_raw)
    original_control = load_exact(CONTROLLER, 'bookmark31_original_control', CONTROLLER_SHA)
    base = original_control.Inputs()
    owned = load_exact(CONTROL/'owned_swift_commands.py', 'bookmark_http10_owned', HELPER_SHA)
    output = args.output
    assert output.parent == PARENT and re.fullmatch(r'http10-attempt[1-9][0-9]{0,2}', output.name)
    assert PARENT.resolve() == PARENT and output.resolve() == output
    assert not output.exists() and not output.is_symlink()
    os.umask(0o077)
    owned.install_interrupt_handlers()
    output.mkdir(mode=0o700, exist_ok=False)
    # This newly owned root alone loses inherited SGID. The failed original
    # 02700 fixture root and the original package/build remain untouched.
    os.chmod(output, 0o700)
    assert stat.S_IMODE(output.lstat().st_mode) == 0o700
    fsync_directory(output)
    fsync_directory(PARENT)
    descriptor = os.open(output/'result.json',
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    os.fsync(descriptor)
    os.close(descriptor)
    fsync_directory(output)
    began = time.monotonic()
    report = {
        'protocol':'pinkha-bookmark-http10-continuation-v1', 'status':'RUNNING',
        'controllerSHA256':args.controller_sha, 'originalComponentControllerSHA256':CONTROLLER_SHA,
        'inputManifestSHA256':MANIFEST_SHA, 'originalComponentRoot':str(ORIGINAL),
        'compilerInvocations':0, 'priorPassingMethodsReplayed':0, 'priorUpload35MethodsReplayed':0,
        'nativeAccountsOpened':False, 'nativeStorageQualified':False, 'cloudDurabilityQualified':False,
        'commands':[], 'errors':[], 'completionErrors':[], 'sourceUnchanged':False,
        'separateNativeTestStatus':'NOT_RUN', 'separateNativeTestStarts':[],
        'originalFailureReclassified':False, 'productCensusIsLaterObservation':True,
        'historicalProcessIDsProbed':False,
        'resourcePolicy':{
            'rootFloorBytes':ROOT_FLOOR, 'rootAdmissionReserveBytes':32*MIB,
            'developmentFloorBytes':DEV_FLOOR, 'developmentAdmissionReserveBytes':OWNED_CAP+16*MIB,
            'ownedOutputCapBytes':OWNED_CAP, 'fixtureCapBytes':FIXTURE_CAP, 'logCapBytes':LOG_CAP,
            'totalControllerSeconds':TOTAL_SECONDS, 'swiftSkipBuildSeconds':SWIFT_SECONDS,
            'finalVerificationSeconds':FINAL_SECONDS, 'finalVerificationWithinTotal':True,
            'allocationSampleSeconds':1, 'requiredOuterSeconds':1050,
            'declaredControlledOutputBytesOnRoot':0, 'noGlobalRootWriteAuditClaim':True}}
    immutable, copies, copied_modes = {}, {}, {}
    products = crypto = crypto_binding = old_fixture = None
    current_fixture = None
    admitted = False
    last_allocation = 0.0
    final_deadline = None

    def save():
        report['seconds'] = round(time.monotonic()-began, 3)
        original_control.save(output/'result.json', report)

    def guard(admission=False, final=False, force_allocation=False):
        nonlocal last_allocation
        now = time.monotonic()
        assert now < began+TOTAL_SECONDS, 'bounded Bookmark continuation total deadline'
        if final:
            assert final_deadline is not None and now < final_deadline, 'bounded final verification'
        assert not (output/'abort').exists(), 'owned continuation abort'
        free = {'root':shutil.disk_usage('/').free, 'development':shutil.disk_usage(PARENT).free}
        assert free['root'] >= ROOT_FLOOR+(32*MIB if admission else 0), 'original root floor/reserve'
        assert free['development'] >= DEV_FLOOR+(OWNED_CAP+16*MIB if admission else 0), 'development floor/reserve'
        for name, value in free.items():
            report.setdefault('minimumFreeBytes', {})[name] = min(
                value, report.get('minimumFreeBytes', {}).get(name, value))
        for path in output.glob('commands/*/original.log'):
            assert path.stat().st_size <= LOG_CAP, 'bounded actual log'
        # Every immutable row checks deadlines and floors; only the recursive
        # allocation census is throttled. Force one at both final boundaries.
        if now-last_allocation >= 1 or force_allocation:
            last_allocation = now
            used = original_control.allocation(output)
            assert used <= OWNED_CAP, 'bounded new output allocation'
            report['maximumOwnedAllocatedBytes'] = max(used, report.get('maximumOwnedAllocatedBytes', 0))
            fixtures = output/'http-fixtures'
            if fixtures.exists():
                assert original_control.allocation(fixtures) <= FIXTURE_CAP, 'bounded loopback fixture allocation'
        assert time.monotonic() < began+TOTAL_SECONDS, 'bounded Bookmark continuation total deadline'
        if final:
            assert time.monotonic() < final_deadline, 'bounded final verification'

    def observe():
        try:
            guard()
            return None
        except BaseException as error:
            return type(error).__name__+': '+str(error)

    def remember(rows, path, value):
        key = str(path)
        assert key not in rows or rows[key] == value, 'conflicting exact input binding'
        rows[key] = value

    def pin(path, wanted):
        guard()
        raw = base.read(path, maximum=8*MIB)
        row = {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
        assert row['sha256'] == wanted, str(path)+' changed'
        remember(immutable, path, row)
        guard()
        return raw

    def verify_rows(rows, final=False):
        for name, wanted in rows.items():
            guard(final=final)
            assert base.row(Path(name)) == wanted, 'bound original input or copy changed: '+name
            guard(final=final)

    def fixture_metadata(path):
        info = path.lstat()
        assert stat.S_ISDIR(info.st_mode) and path.resolve() == path and not path.is_symlink()
        return {'path':str(path), 'mode':stat.S_IMODE(info.st_mode), 'uid':info.st_uid,
            'gid':info.st_gid, 'device':info.st_dev, 'inode':info.st_ino,
            'entries':sorted(entry.name for entry in path.iterdir())}

    def product_census(final=False):
        guard(final=final)
        value = original_control.retained_products(ORIGINAL/'build', base, lambda:guard(final=final))
        guard(final=final)
        return value

    def copy_modes(final=False):
        result = {}
        for name in copies:
            guard(final=final)
            path = Path(name)
            info = path.lstat()
            assert path.resolve() == path and not path.is_symlink()
            assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid()
            assert stat.S_IMODE(info.st_mode) == 0o600, 'unchanged original private source copy mode'
            result[name] = stat.S_IMODE(info.st_mode)
        return result

    def source_membership(expected_copies, final=False):
        observed = set()
        for prefix in ('Sources', 'Tests'):
            root = ORIGINAL/'package'/prefix
            for path in [root]+sorted(root.rglob('*')):
                guard(final=final)
                info = path.lstat()
                assert path.resolve() == path and not path.is_symlink()
                assert stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)
                if stat.S_ISREG(info.st_mode):
                    observed.add(str(path))
                assert len(observed) <= 36, 'bounded original package source membership'
        assert observed == set(expected_copies), 'complete original 33 production and3 test source membership'

    expected_copies = {}
    try:
        save()
        guard(admission=True, force_allocation=True)
        lifecycle = json.loads(pin(original_control.LIFECYCLE_RECEIPT, LIFECYCLE_SHA))
        assert lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
        assert lifecycle['helperSHA256'] == HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'] is True
        assert len(lifecycle['methods']) == len(lifecycle['commands']) == 5
        assert {row['name'] for row in lifecycle['methods']} == {
            'normal', 'started-journal-failure', 'leader-exits-with-descendant', 'controller-SIGTERM', 'controller-SIGINT'}
        assert all(row['status'] == 'PASS' and row['groupPositivelyAbsent'] for row in lifecycle['methods'])
        assert all(row['processGroupAbsent'] for row in lifecycle['commands'])
        assert lifecycle['compilerInvocations'] == lifecycle['nativeInvocations'] == 0
        report['unchangedOwnedHelperFiveControlsReused'] = {
            'path':str(original_control.LIFECYCLE_RECEIPT), 'sha256':LIFECYCLE_SHA, 'newlyExecutedControls':0}
        pin(CONTROLLER, CONTROLLER_SHA)
        assert pin(own, args.controller_sha) == own_raw
        pin(CONTROL/'owned_swift_commands.py', HELPER_SHA)
        pin(CONTROL/'qualify_bookmark_crypto_c3.py', CRYPTO_SHA)
        pin(CONTROL/'qualify_current_c3_crypto.py', SHARED_CRYPTO_SHA)
        pin(CONTROL/'crypto-header-source-manifest.json', HEADERS_SHA)
        manifest = json.loads(pin(CONTROL/'bookmark-component-inputs.json', MANIFEST_SHA))
        assert manifest['schema'] == 1 and manifest['scope'] == 'ISOLATED_BOOKMARK_CREATION_COMPONENT_SOURCE_CLOSURE_ONLY'
        assert manifest['expectedCounts'] == {
            'compiledTestFiles':3, 'exactValueMethods':7, 'excludedNativeMethods':0, 'frameMethods':20,
            'httpBearingMethods':10, 'httpFixtureInstances':17, 'httpGETs':66, 'httpRequests':76,
            'methods':31, 'nonHTTPMethods':21, 'objectCreatePOSTs':0, 'originalCoreCompiledFiles':8,
            'originalProjectCompiledFiles':19, 'originalProjectReadFiles':20, 'postCloseMethods':4,
            'preparedProductionCompiledFiles':6, 'productionCompiledFiles':33, 'readOnlyFramePOSTs':10}
        assert manifest['excludedNativeMethods'] == {} and len(manifest['preparedSources']) == 9
        original = json.loads(pin(ORIGINAL/'result.json', ORIGINAL_SHA))
        assert original['status'] == 'FAIL' and original['controllerSHA256'] == CONTROLLER_SHA
        assert original['inputManifestSHA256'] == MANIFEST_SHA
        assert original['sourceUnchanged'] and original['admittedInputsUnchanged'] and original['compiledSourceInputsUnchanged']
        assert original['allStartedOwnedGroupsPositivelyAbsent'] and len(original['commands']) == 4
        assert [row['exitCode'] for row in original['commands']] == [0, 0, 0, 1]
        assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors']
            and not row['signals'] for row in original['commands'])
        assert original['errors'] == [
            {'message':'owned command did not finish normally: swift-components', 'type':'RuntimeError'},
            {'message':'', 'phase':'final-lifecycle-and-budget', 'type':'AssertionError'}]
        assert original['separateNativeTestStarts'] == [] and original['separateNativeTestStatus'] == 'NOT_RUN'
        assert original['nativeAccountsOpened'] is False and 'compiledProducts' not in original
        original_log = pin(ORIGINAL/'commands/swift-components/original.log', ORIGINAL_LOG_SHA).decode()
        starts = re.findall(r"Test Case '([^']+)' started", original_log)
        passes = re.findall(r"Test Case '([^']+)' passed", original_log)
        failures = re.findall(r"Test Case '([^']+)' failed", original_log)
        http = {'AnyNativeBookmarkCreationFrameTests.'+method for method in HTTP_METHODS}
        expected = {name+'.'+method for name, methods in manifest['methods'].items() for method in methods}
        reused = expected-http
        assert len(http) == 10 and len(reused) == 21 and len(expected) == 31 and http <= expected
        assert Counter(starts) == Counter({name:1 for name in expected})
        assert Counter(passes) == Counter({name:1 for name in reused})
        assert Counter(failures) == Counter({name:1 for name in http})
        assert len(re.findall(r'threw error "fixture"', original_log)) == 10
        assert 'Build complete! (35.55 secs)' in original_log
        assert 'Executed 31 tests, with 10 failures (10 unexpected)' in original_log
        assert not re.search(r"Test Case '[^']+' skipped|XCTSkip|Skipping XCTest discovery", original_log)
        old_fixture = fixture_metadata(ORIGINAL/'http-fixtures')
        assert old_fixture['mode'] == 0o2700 and old_fixture['uid'] == os.geteuid() and old_fixture['gid'] == 1002
        assert old_fixture['entries'] == []
        report['originalFixtureSetupFailure'] = {'observed':old_fixture, 'requiredMode':0o700,
            'productAndTestsUnchanged':True, 'originalDirectoryModified':False}
        report['reusedMethods'] = {'frameNonHTTP':10, 'exactValue':7, 'postClose':4, 'total':21,
            'started':sorted(reused), 'passed':sorted(reused), 'newExecutions':0,
            'originalReceipt':{'path':str(ORIGINAL/'result.json'), 'sha256':ORIGINAL_SHA, 'status':'FAIL'},
            'originalLog':{'path':str(ORIGINAL/'commands/swift-components/original.log'), 'sha256':ORIGINAL_LOG_SHA}}
        binding = original['compiledSourceInputs']
        assert binding == {'path':str(ORIGINAL/'compiled-source-inputs.json'), 'bytes':526234, 'sha256':SOURCE_SHA}
        source = json.loads(pin(Path(binding['path']), SOURCE_SHA))
        assert source['counts'] == manifest['expectedCounts']
        assert source['indexStore'] == 'enabled; no disable-index-store flag'
        assert source['noExistingProjectModuleImportDirectories'] is True
        base.admit_retained_crypto_alias(original_control.CACHE, original_control.PHYSICAL_CACHE, CUSTODY_SHA)
        for name, row in source['originalInputs'].items():
            remember(immutable, name, row)
        copies = source['isolatedCopies']
        assert type(copies) is dict and all(Path(name).is_relative_to(ORIGINAL) for name in copies)
        for row in manifest['originalProjectFiles']:
            path = Path(manifest['originalProjectRoot'])/row['path']
            wanted = {key:row[key] for key in ('bytes', 'sha256')}
            assert immutable.get(str(path)) == wanted
            if row['compile']:
                expected_copies[str(ORIGINAL/'package/Sources'/row['target']/Path(row['path']).name)] = wanted
        for row in manifest['originalCoreFiles']:
            path = Path(manifest['originalCoreRoot'])/row['path']
            wanted = {key:row[key] for key in ('bytes', 'sha256')}
            assert immutable.get(str(path)) == wanted
            expected_copies[str(ORIGINAL/'package/Sources/TorahInspectorCore'/Path(row['path']).name)] = wanted
        for row in manifest['preparedSources']:
            assert row['sourceBase'] in ('retained-upload-prepared3', 'bookmark-prepared1')
            root = original_control.RETAINED_UPLOAD_PREPARED if row['sourceBase'] == 'retained-upload-prepared3' else PARENT/'prepared1'
            wanted = {key:row[key] for key in ('bytes', 'sha256')}
            assert immutable.get(str(root/row['path'])) == wanted
            if row['kind'] == 'production':
                target = ORIGINAL/'package/Sources'/row['target']/Path(row['path']).name
            else:
                assert row['kind'] == 'test'
                target = ORIGINAL/'package/Tests/BookmarkCreationTests'/Path(row['path']).name
            expected_copies[str(target)] = wanted
        assert len(expected_copies) == 36
        assert all(copies.get(name) == wanted for name, wanted in expected_copies.items())
        source_membership(expected_copies)
        verify_rows(immutable)
        verify_rows(copies)
        copied_modes = copy_modes()
        crypto = load_exact(CONTROL/'qualify_bookmark_crypto_c3.py', 'bookmark_http10_crypto', CRYPTO_SHA)
        crypto_receipt = ORIGINAL/'retained-dependency-products.json'
        assert str(crypto_receipt) in copies
        crypto_data = json.loads(base.read(crypto_receipt, maximum=4*MIB))
        assert crypto_data['status'] == 'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_BOOKMARK_COMPONENTS_ONLY'
        assert crypto_data['sharedAdmissionHelperSHA256'] == SHARED_CRYPTO_SHA
        assert crypto_data['dependencyCompilerInvocations'] == 0
        assert crypto_data['exactGitBoundHeaderProvenance'] == {
            'path':str(CONTROL/'crypto-header-source-manifest.json'), 'sha256':HEADERS_SHA}
        for name, row in crypto_data['immutableFiles'].items():
            assert immutable.get(name) == row
        crypto_copies = dict(crypto_data['isolatedCryptoModuleCopies'])
        crypto_copies.update(crypto_data['isolatedCryptoHeaderCopies'])
        assert len(crypto_data['isolatedCryptoModuleCopies']) == 4
        assert len(crypto_data['isolatedCryptoHeaderCopies']) == 94 and len(crypto_copies) == 98
        assert all(copies.get(name) == row for name, row in crypto_copies.items())
        assert set(copies) == set(expected_copies) | set(crypto_copies) | {
            str(ORIGINAL/'package/Package.swift'), str(crypto_receipt)}
        crypto_binding = {'sharedAdmission':crypto_data['sharedProducerAdmission'], 'inputModes':crypto_data['modes']}
        crypto.validate_after(crypto_binding, guard)
        wanted_package = original_control.package_text(crypto_data['compilerImportFlags'], crypto_data['linkObjects']).encode()
        assert base.read(ORIGINAL/'package/Package.swift', maximum=MIB) == wanted_package
        assert immutable[str(original_control.TOOLCHAIN/'swift-driver')] == {
            key:crypto_data['sharedProducerAdmission']['liveInputs'][str(original_control.TOOLCHAIN/'swift-driver')][key]
            for key in ('bytes', 'sha256')}
        products = product_census()
        original_control.save(output/'retained-products-before.json', {
            'phase':'LATER_CENSUS_BEFORE_HTTP10_NOT_ORIGINAL_PRODUCER_OUTPUT',
            'originalReceiptSHA256':ORIGINAL_SHA, 'originalCompiledSourceInputsSHA256':SOURCE_SHA,
            'originalBuildLogSHA256':ORIGINAL_LOG_SHA, 'products':products})
        report['compiledSourceInputs'] = binding
        report['productCensusBefore'] = {'path':str(output/'retained-products-before.json'), **base.row(output/'retained-products-before.json')}
        report['retainedDependencyProducts'] = {'path':str(crypto_receipt), **base.row(crypto_receipt)}
        for key, name in [('root','compiledProductsRoot'), ('files','compiledProducts'), ('modes','compiledProductModes'),
            ('directories','compiledProductDirectories'), ('executables','compiledExecutables'), ('testRunner','compiledTestRunner')]:
            report[name] = products[key]
        original_swift = original['commands'][3]
        expected_argv = [str(original_control.TOOLCHAIN/'swift'), 'test', '--package-path', str(ORIGINAL/'package'),
            '--scratch-path', str(ORIGINAL/'build'), '--cache-path', str(ORIGINAL/'swift-cache'),
            '--config-path', str(ORIGINAL/'swift-config'), '--security-path', str(ORIGINAL/'swift-security'),
            '--disable-automatic-resolution', '--jobs', '2', '--filter', '|'.join(manifest['methods'])]
        assert original_swift['argv'] == expected_argv and original_swift['cwd'] == str(ORIGINAL/'package')
        assert original_swift['logSHA256'] == ORIGINAL_LOG_SHA
        report['originalCompilerCommand'] = original_swift
        for name in ('temporary', 'module-cache', 'clang-module-cache', 'swift-cache', 'swift-config', 'swift-security', 'http-fixtures'):
            directory = output/name
            directory.mkdir(mode=0o700, exist_ok=False)
            os.chmod(directory, 0o700)
            assert stat.S_IMODE(directory.lstat().st_mode) == 0o700 and directory.resolve() == directory
            fsync_directory(directory)
        fsync_directory(output)
        env = {key:value for key, value in os.environ.items()
            if not key.startswith(('PINKHA_', 'SWIFT_', 'SWIFTPM_', 'CLANG_', 'DYLD_', 'LD_'))}
        env.update(TMPDIR=str(output/'temporary'), SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
            CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'), XDG_CACHE_HOME=str(output/'swift-cache'),
            GIT_OPTIONAL_LOCKS='0', SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2',
            PINKHA_BOOKMARK_FRAME_FIXTURE_ROOT=str(output/'http-fixtures'),
            PINKHA_BOOKMARK_FRAME_OWNER_RECORD=str(output/'commands/http10/started.json'),
            PINKHA_BOOKMARK_FRAME_OWNER_CWD=str(ORIGINAL/'package'))
        argv = list(expected_argv)
        argv[argv.index('--filter')+1] = 'AnyNativeBookmarkCreationFrameTests.('+'|'.join(HTTP_METHODS)+')$'
        for option, name in [('--cache-path','swift-cache'), ('--config-path','swift-config'), ('--security-path','swift-security')]:
            argv[argv.index(option)+1] = str(output/name)
        argv.append('--skip-build')
        report['fixtureRootBefore'] = fixture_metadata(output/'http-fixtures')
        assert report['fixtureRootBefore']['mode'] == 0o700 and report['fixtureRootBefore']['entries'] == []
        admitted = True
        save()
        path, row = owned.run(output/'commands/http10', argv, ORIGINAL/'package', env, SWIFT_SECONDS,
            observe, original_control.save, base.sha, report['commands'])
        log = base.read(path, maximum=LOG_CAP).decode()
        current_starts = re.findall(r"Test Case '([^']+)' started", log)
        current_passes = re.findall(r"Test Case '([^']+)' passed", log)
        assert Counter(current_starts) == Counter(current_passes) == Counter({name:1 for name in http})
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|XCTSkip|Skipping XCTest discovery|Build complete!|Building for|\] Compiling", log)
        assert 'Executed 10 tests, with 0 failures' in log
        report['actualMethods'] = {'started':current_starts, 'passed':current_passes,
            'httpBearing':10, 'nonHTTP':0, 'postClose':0, 'exactValue':0, 'total':10, 'skipped':0}
        # Reuse the exact 6e715 fixture audit, including all 17/76 source-derived
        # obligations and latched original-group identity, without modification.
        class BoundedFixtureInputs:
            def read(self, path, maximum):
                guard()
                value = base.read(path, maximum=maximum)
                guard()
                return value

            def sha(self, path):
                guard()
                value = base.sha(path)
                guard()
                return value

        report['httpFixtureQualification'] = original_control.fixture_audit(output/'http-fixtures',
            output/'commands/http10/started.json', row, BoundedFixtureInputs(), manifest)
        current_fixture = fixture_metadata(output/'http-fixtures')
        report['fixtureRootAfterActualMethods'] = current_fixture
        report['qualifiedComponentMethods'] = {
            'started':sorted(reused)+current_starts, 'passed':sorted(reused)+current_passes,
            'frame':20, 'httpBearing':10, 'nonHTTP':21, 'exactValue':7, 'postClose':4,
            'total':31, 'skipped':0, 'reusedActualPasses':21, 'newActualPasses':10}
        report['status'] = 'PASS_COMPONENT31_WITH_REUSED21_AND_NEW_HTTP10'
    except BaseException as error:
        report['status'] = 'FAIL_HTTP10_CONTINUATION'
        report['errors'].append({'type':type(error).__name__, 'message':str(error)})
    finally:
        owned.ignore_interrupts()
        # Preserve terminal ownership evidence even if a later source audit
        # fails. Never probe or signal the old producer or a returned owner PID.
        report['allStartedOwnedGroupsPositivelyAbsent'] = all(
            row.get('processGroupAbsent') is True for row in report['commands'])
        report['newOwnedCommandCount'] = len(report['commands'])
        final_deadline = min(began+TOTAL_SECONDS, time.monotonic()+FINAL_SECONDS)
        try:
            guard(final=True, force_allocation=True)
            verify_rows(immutable, final=True)
            verify_rows(copies, final=True)
            if copied_modes:
                assert copy_modes(final=True) == copied_modes
                report['isolatedSourceCopyModesUnchanged'] = True
            if admitted:
                source_membership(expected_copies, final=True)
            if products is not None:
                assert product_census(final=True) == products
                report['compiledProductsAndModesUnchanged'] = True
            if crypto_binding is not None:
                crypto.validate_after(crypto_binding, lambda:guard(final=True))
                report['currentCryptoClosureUnchanged'] = True
            if old_fixture is not None:
                assert fixture_metadata(ORIGINAL/'http-fixtures') == old_fixture
                report['originalFixtureRootUnchanged'] = True
            if current_fixture is not None:
                assert fixture_metadata(output/'http-fixtures') == current_fixture
                report['newFixtureRootFinalVerified'] = True
            guard(final=True)
            assert base.read(own, maximum=65536) == own_raw
            report['controllerUnchanged'] = True
            report['admittedInputsUnchanged'] = admitted
            report['compiledSourceInputsUnchanged'] = str(ORIGINAL/'compiled-source-inputs.json') in immutable
            report['sourceUnchanged'] = admitted
            assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup']
                and not row['cleanupErrors'] and not row['signals'] for row in report['commands'])
            if report['status'].startswith('PASS_'):
                assert admitted and len(report['commands']) == 1 and report['actualMethods']['total'] == 10
                assert report['qualifiedComponentMethods']['total'] == 31
                assert report['httpFixtureQualification']['instances'] == 17
                assert report['httpFixtureQualification']['requestCount'] == 76
                assert report['httpFixtureQualification']['GETCount'] == 66
                assert report['httpFixtureQualification']['readOnlyFramePOSTCount'] == 10
                assert report['httpFixtureQualification']['objectCreatePOSTCount'] == 0
                assert report['compiledProductsAndModesUnchanged'] and report['currentCryptoClosureUnchanged']
                assert report['newFixtureRootFinalVerified'] and report['originalFixtureRootUnchanged']
            guard(final=True, force_allocation=True)
        except BaseException as error:
            report['status'] = 'FAIL_HTTP10_CONTINUATION'
            report['completionErrors'].append({'type':type(error).__name__, 'message':str(error)})
        try:
            save()
        except BaseException as error:
            report['status'] = 'FAIL_HTTP10_CONTINUATION'
            report['completionErrors'].append({'phase':'receipt-retention', 'type':type(error).__name__, 'message':str(error)})
            print(json.dumps(report))
            return 1
    print(json.dumps({'status':report['status'], 'path':str(output/'result.json'),
        'sha256':base.sha(output/'result.json'), 'newOwnedCommandCount':len(report['commands'])}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
