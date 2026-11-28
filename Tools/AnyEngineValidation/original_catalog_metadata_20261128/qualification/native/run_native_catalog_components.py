#!/usr/bin/env python3
"""Isolated real-source qualification of Compile one original native catalog proof; execute no test method.

SOURCE-ONLY until this controller actually completes. It opens no native
account, compiles no dependency, and does not replay any FilesV2 or migration
proof. The two reused Crypto modules are admitted from the exact retained
producer; every product module under test is compiled from its full sources.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import stat
import sys
import time


MIB = 1024 * 1024
GIB = 1024 * MIB
PARENT = Path('/mnt/development/projects/evidence/pinkha-original-catalog-native1-20261127')
PREPARED = PARENT/'prepared1'
CONTROL = Path(__file__).parent
MANIFEST = CONTROL/'catalog-native-component-inputs.json'
MANIFEST_SHA = '27a714acf039353cefa3d30a1726e4c36a35fef6aba4184d6c25ddd572ea8aa7'
CRYPTO_HELPER = CONTROL/'qualify_metadata_crypto_c3.py'
CRYPTO_HELPER_SHA = 'd9c89639fc615a5f3bfb55aa353314a292f2df74ed0a18dd4d16b9ccfda8feb4'
SHARED_CRYPTO_HELPER = CONTROL/'qualify_current_c3_crypto.py'
SHARED_CRYPTO_HELPER_SHA = '206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0'
OWNED_HELPER = CONTROL/'owned_swift_commands.py'
OWNED_HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HEADER_MANIFEST = CONTROL/'crypto-header-source-manifest.json'
HEADER_MANIFEST_SHA = '4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961'
LIFECYCLE_RECEIPT = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
LIFECYCLE_RECEIPT_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
TOOLCHAIN = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
DRIVER_ALIASES = {
    TOOLCHAIN/'swift': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'swiftc': TOOLCHAIN/'swift-driver',
    TOOLCHAIN/'clang': TOOLCHAIN/'clang-21',
    TOOLCHAIN/'clang++': TOOLCHAIN/'clang-21',
}
ROOT_FLOOR = 2 * GIB
ROOT_ADMISSION = ROOT_FLOOR + 32 * MIB
DEVELOPMENT_FLOOR = 512 * MIB
OWNED_ALLOCATION_CAP = 384 * MIB
DEVELOPMENT_ADMISSION = DEVELOPMENT_FLOOR + OWNED_ALLOCATION_CAP + 32 * MIB
LOG_CAP = 16 * MIB
FIXTURE_CAP = 16 * MIB
RECEIPT_CAP = 4 * MIB
TOTAL_SECONDS = 900
SWIFT_SECONDS = 600
FIXTURE_INPUTS = CONTROL/'provider_fixture_inputs.py'
FIXTURE_INPUTS_SHA = '32cec96b4984b02d1cae76c94ccc73e958f0f890f32e68e9729ab7db4b13b5cf'
BUNDLE_INPUTS = CONTROL/'bundle_recovery_inputs.py'
BUNDLE_INPUTS_SHA = 'f7b8155be19a890cd7e7351c22ca46c4d337ca9b1052bc7b4c80be84abb4c3e4'
BASELINE_INPUTS = CONTROL/'compiled-source-313.json'
BASELINE_INPUTS_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
CHUNK = MIB
_save_serial = 0


class Inputs:
    """Exact regular-file reads; no generic symlink admission or whole-file hash."""
    def __init__(self):
        self.alias_admitted = False

    def admit_retained_crypto_alias(self, original, physical, receipt_sha):
        assert original == CACHE and physical == PHYSICAL_CACHE
        assert receipt_sha == 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
        assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
        assert CACHE.resolve() == PHYSICAL_CACHE and PHYSICAL_CACHE.resolve() == PHYSICAL_CACHE
        self.alias_admitted = True

    def physical(self, value):
        path = Path(value)
        assert path.is_absolute()
        if path in DRIVER_ALIASES:
            target = DRIVER_ALIASES[path]
            assert path.resolve() == target and target.resolve() == target
            if path.name == 'swift' or path.name == 'swiftc':
                assert os.readlink(path) == 'swift-driver'
            elif path.name == 'clang':
                assert os.readlink(path) == 'clang-21'
            else:
                assert os.readlink(path) == 'clang' and os.readlink(TOOLCHAIN/'clang') == 'clang-21'
            return target
        if path.is_relative_to(CACHE):
            assert self.alias_admitted, 'retained cache custody not yet admitted'
            assert CACHE.is_symlink() and os.readlink(CACHE) == str(PHYSICAL_CACHE)
            target = PHYSICAL_CACHE/path.relative_to(CACHE)
            assert path.resolve() == target and target.resolve() == target
            return target
        assert path.resolve() == path and not path.is_symlink(), 'unqualified input alias'
        return path

    @staticmethod
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def consume(self, value, maximum, retain=False, destination=None):
        path = self.physical(value)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NOATIME)
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum
        assert self.identity(path.lstat()) == self.identity(before)
        digest = hashlib.sha256()
        collected = bytearray() if retain else None
        copied = 0
        try:
            while True:
                part = os.read(fd, CHUNK)
                if not part:
                    break
                copied += len(part)
                assert copied <= maximum and copied <= before.st_size
                digest.update(part)
                if retain:
                    collected.extend(part)
                if destination is not None:
                    view = memoryview(part)
                    while view:
                        written = os.write(destination, view)
                        assert written > 0
                        view = view[written:]
            assert copied == before.st_size
            assert self.identity(os.fstat(fd)) == self.identity(before)
            assert self.identity(path.lstat()) == self.identity(before)
        finally:
            os.close(fd)
        result = {'bytes': copied, 'sha256': digest.hexdigest()}
        return (result, bytes(collected)) if retain else result

    def row(self, path):
        return self.consume(path, maximum=512*MIB)

    def sha(self, path):
        return self.row(path)['sha256']

    def read(self, path, maximum):
        return self.consume(path, maximum=maximum, retain=True)[1]

    def pinned(self, path, expected):
        assert re.fullmatch(r'[0-9a-f]{64}', expected)
        assert self.sha(path) == expected, str(path)+' changed'

    def copy_exact(self, original, destination, expected):
        destination = Path(destination)
        assert destination.parent.resolve() == destination.parent
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            copied = self.consume(original, maximum=8*MIB, destination=descriptor)
            assert copied == expected
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        assert self.row(destination) == expected

    def save(self, path, value):
        save(path, value)


def save(path, value):
    global _save_serial
    path = Path(path)
    assert path.parent.resolve() == path.parent
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    assert len(data) <= RECEIPT_CAP
    _save_serial += 1
    # Retain an interrupted staging file; finalization always gets a fresh name.
    temporary = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(_save_serial))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            assert count > 0
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_module(path, name, expected, base):
    base.pinned(path, expected)
    ast.parse(base.read(path, maximum=256*1024))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base.pinned(path, expected)
    return module


def allocation(root):
    total = 0
    count = 0
    seen = set()
    began = time.monotonic()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for filename in [None]+dirs+files:
            path = Path(directory) if filename is None else Path(directory)/filename
            try:
                row = path.lstat()
            except FileNotFoundError:
                continue  # A compiler may retire its own temporary member.
            count += 1
            assert count <= 200000 and time.monotonic()-began <= 5
            key = (row.st_dev, row.st_ino)
            if key not in seen:
                seen.add(key)
                total += row.st_blocks * 512
    return total


def retained_products(build, base, guard):
    """Pin the complete physical Products tree, including Linux test launchers.

    A suffix list omits the executable *-test-runner which --skip-build uses.
    Keep every regular product file and every executable mode, and refuse any
    alias/special file. The independent source manifest is a separate input.
    """
    root = build/'out/Products'
    assert root.is_dir() and root.resolve() == root and not root.is_symlink()
    files, modes, directories, executables = {}, {}, {}, {}
    for path in [root]+sorted(root.rglob('*')):
        guard()
        before = path.lstat()
        assert path.resolve() == path and not path.is_symlink(), 'physical compiled product required'
        key = str(path)
        mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            directories[key] = mode
        else:
            assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'regular private compiled product required'
            assert before.st_size <= 128*1024**2, 'bounded compiled product file'
            files[key] = base.row(path)
            modes[key] = mode
            if mode & 0o111:
                executables[key] = dict(files[key], mode=mode)
        after = path.lstat()
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_nlink,
                                row.st_size, row.st_mtime_ns, row.st_ctime_ns)
        assert identity(before) == identity(after), 'compiled product changed during census'
        assert len(files)+len(directories) <= 4096, 'bounded compiled product tree'
    assert 1 <= len(files) <= 2048
    runners = [name for name in files if Path(name).name == 'CatalogNativeTests-test-runner']
    assert len(runners) == 1 and runners[0] in executables, 'one actual executable Linux XCTest runner'
    libraries = [name for name in files if Path(name).name == 'CatalogNativeTests.so']
    assert len(libraries) == 1, 'one actual test shared library'
    assert any('PinkhaAnyEngine' in name and '.swiftmodule' in name for name in files)
    assert any('PinkhaAnyHost' in name and '.swiftmodule' in name for name in files)
    return {'root':str(root), 'files':files, 'modes':modes, 'directories':directories,
            'executables':executables, 'testRunner':dict(path=runners[0], **executables[runners[0]])}


def package_text(flags, links):
    swift = lambda value: json.dumps(value, ensure_ascii=False)
    compile_flags = '['+', '.join(map(swift, flags))+']'
    link_flags = '['+', '.join(map(swift, links+['-lstdc++']))+']'
    targets = [
        ('TorahInspectorCore', []),
        ('PinkhaKit', ['TorahInspectorCore']),
        ('PinkhaAnyEngine', []),
        ('PinkhaAnyIntegration', ['PinkhaKit', 'PinkhaAnyEngine']),
        ('PinkhaAnyHost', ['PinkhaAnyEngine', 'PinkhaAnyIntegration']),
    ]
    rows = []
    for name, dependencies in targets:
        deps = '['+', '.join(map(swift, dependencies))+']'
        rows.append('        .target(name: '+swift(name)+', dependencies: '+deps+', swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')])')
    rows.append('        .testTarget(name: "CatalogNativeTests", dependencies: ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost"], swiftSettings: [.swiftLanguageMode(.v6), .unsafeFlags('+compile_flags+')], linkerSettings: [.unsafeFlags('+link_flags+')])')
    return '// swift-tools-version: 6.0\nimport PackageDescription\nlet package = Package(name: "CatalogNativeProof", targets: [\n'+',\n'.join(rows)+'\n])\n'



def main():
    if sys.flags.optimize:
        raise RuntimeError('qualification requires Python assertions enabled')
    sys.dont_write_bytecode = True
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controller-sha', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{64}', args.controller_sha)
    assert CONTROL.resolve() == CONTROL and CONTROL.is_relative_to(PREPARED)
    assert PREPARED.resolve() == PREPARED and PARENT.resolve() == PARENT
    output = args.output
    assert output.parent == PARENT and re.fullmatch(r'components-attempt[1-9][0-9]*', output.name)
    assert not output.exists() and not output.is_symlink()
    base = Inputs()
    controls = {Path(__file__):args.controller_sha, MANIFEST:MANIFEST_SHA,
                CRYPTO_HELPER:CRYPTO_HELPER_SHA, SHARED_CRYPTO_HELPER:SHARED_CRYPTO_HELPER_SHA,
                OWNED_HELPER:OWNED_HELPER_SHA,
                HEADER_MANIFEST:HEADER_MANIFEST_SHA, LIFECYCLE_RECEIPT:LIFECYCLE_RECEIPT_SHA,
                FIXTURE_INPUTS:FIXTURE_INPUTS_SHA, BUNDLE_INPUTS:BUNDLE_INPUTS_SHA,
                BASELINE_INPUTS:BASELINE_INPUTS_SHA}
    for path, expected in controls.items():
        base.pinned(path, expected)
    lifecycle = json.loads(base.read(LIFECYCLE_RECEIPT, maximum=MIB))
    assert lifecycle['status'] == 'PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
    assert lifecycle['helperSHA256'] == OWNED_HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'] is True
    assert len(lifecycle['methods']) == len(lifecycle['commands']) == 5
    assert {row['name'] for row in lifecycle['methods']} == {'normal','started-journal-failure','leader-exits-with-descendant','controller-SIGTERM','controller-SIGINT'}
    assert all(row['status'] == 'PASS' and row['groupPositivelyAbsent'] for row in lifecycle['methods'])
    assert all(row['processGroupAbsent'] for row in lifecycle['commands'])
    assert lifecycle['compilerInvocations'] == lifecycle['nativeInvocations'] == 0
    owned = load_module(OWNED_HELPER, 'ordinary_upload_owned_commands', OWNED_HELPER_SHA, base)
    owned.install_interrupt_handlers()
    owned_output = False
    started_at = time.monotonic()
    result = {'status':'RUNNING', 'scope':'Compiler-only Native catalog1; exact full original sources; no test or account invocation',
              'nativeAccountsOpened':False, 'nativeStorageQualified':False, 'cloudDurabilityQualified':False,
              'earlierTestReplayRequested':False, 'earlierTestReplayStatus':'NOT_DISPATCHED',
              'priorMigrationOrFilesV2MethodsReplayed':0, 'priorUpload35MethodsReplayed':0, 'errors':[], 'commands':[], 'sourceUnchanged':False,
              'controllerSHA256':args.controller_sha, 'inputManifestSHA256':MANIFEST_SHA,
              'unchangedOwnedHelperFiveControlsReused':{'path':str(LIFECYCLE_RECEIPT),'sha256':LIFECYCLE_RECEIPT_SHA,'newlyExecutedControls':0},
              'budget':{'rootRuntimeFloorBytes':ROOT_FLOOR, 'rootAdmissionBytes':ROOT_ADMISSION,
                        'developmentRuntimeFloorBytes':DEVELOPMENT_FLOOR, 'developmentAdmissionBytes':DEVELOPMENT_ADMISSION,
                        'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP, 'declaredControlledOutputBytesOnRoot':0,
                        'finalVerificationSeconds':120, 'mainControllerSeconds':TOTAL_SECONDS, 'requiredOuterSeconds':1080,
                        'allocationCapIsFiniteEstimateNotMeasuredPeak':True,
                        'allExplicitBuildIndexCacheTemporaryAndEvidencePathsOnDevelopment':True,
                        'noGlobalRootWriteAuditClaim':True},
              'minimumRootFreeBytes':shutil.disk_usage('/').free,
              'minimumDevelopmentFreeBytes':shutil.disk_usage(PARENT).free}
    immutable = {}
    copies = {}
    reused = None
    manifest = None
    helper = None
    env = None
    last_allocation = 0.0
    source_admission_complete = False
    fixture_input_helper = None
    fixture_input_admission = None
    final_deadline = None

    def observe():
        nonlocal last_allocation
        try:
            root_free = shutil.disk_usage('/').free
            development_free = shutil.disk_usage(PARENT).free
            result['minimumRootFreeBytes'] = min(result['minimumRootFreeBytes'], root_free)
            result['minimumDevelopmentFreeBytes'] = min(result['minimumDevelopmentFreeBytes'], development_free)
            if root_free < ROOT_FLOOR:
                return 'root 2 GiB runtime emergency floor'
            if development_free < DEVELOPMENT_FLOOR:
                return 'development 512 MiB runtime emergency floor'
            if final_deadline is None and time.monotonic()-started_at > TOTAL_SECONDS:
                return 'bounded component controller deadline'
            if final_deadline is not None and time.monotonic() >= final_deadline:
                return 'bounded component final verification deadline'
            if (output/'abort').exists():
                return 'owned component abort requested'
            for path in output.glob('commands/*/original.log'):
                if path.stat().st_size > LOG_CAP:
                    return 'bounded command log limit'
            if time.monotonic()-last_allocation >= 1:
                last_allocation = time.monotonic()
                used = allocation(output)
                result['maximumOwnedAllocatedBytes'] = max(result.get('maximumOwnedAllocatedBytes',0), used)
                if used > OWNED_ALLOCATION_CAP:
                    return 'bounded entire component allocation limit'
                fixtures = output/'http-fixtures'
                if fixtures.exists() and allocation(fixtures) > FIXTURE_CAP:
                    return 'bounded loopback fixture allocation limit'
        except BaseException as error:
            return 'resource observation failed: '+type(error).__name__
        return None

    def guard():
        reason = observe()
        if reason is not None:
            raise RuntimeError(reason)

    def remember_input(path, expected):
        guard()
        actual = base.row(path)
        assert actual == {'bytes':expected['bytes'], 'sha256':expected['sha256']}, str(path)+' source changed'
        immutable[str(path)] = actual

    def command(name, argv, cwd, command_env, timeout):
        log, row = owned.run(output/'commands'/name, argv, cwd, command_env, timeout,
                             observe, save, base.sha, result['commands'])
        return base.read(log, maximum=LOG_CAP), row

    def dependency_status(phase, manifest):
        for name, revision in manifest['dependencySourcePins'].items():
            directory = PHYSICAL_CACHE/'checkouts'/name
            assert directory.resolve() == directory
            raw, _ = command(phase+'-'+name, ['git','-c','safe.directory='+str(directory),'-C',str(directory),
                'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
            rows = raw.decode().splitlines()
            assert '# branch.oid '+revision in rows and all(row.startswith('# ') for row in rows), name+' source checkout changed'
        directory = Path(manifest['originalCoreRoot'])
        raw, _ = command(phase+'-torah-core', ['git','-c','safe.directory='+str(directory),'-C',str(directory),
            'status','--porcelain=v2','--branch','--untracked-files=all'], directory, env, 20)
        rows = raw.decode().splitlines()
        assert '# branch.oid '+manifest['originalCoreCommit'] in rows and all(row.startswith('# ') for row in rows), 'Core source checkout changed'

    try:
        assert result['minimumRootFreeBytes'] >= ROOT_ADMISSION, 'initial root 2 GiB plus 32 MiB admission'
        assert result['minimumDevelopmentFreeBytes'] >= DEVELOPMENT_ADMISSION, 'initial development budget admission'
        setup_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
        try:
            output.mkdir(mode=0o700)
            owned_output = True
            for path in (output, output.parent):
                descriptor = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, setup_mask)
        save(output/'result.json', result)
        for name in ('temporary','module-cache','clang-module-cache','swift-cache','swift-config','swift-security','http-fixtures'):
            (output/name).mkdir(mode=0o700)
        # Clear inherited setgid only on our new fixture parent; keep its strict700 input guard.
        os.chmod(output/'http-fixtures',0o700)
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('PINKHA_', 'SWIFT_', 'SWIFTPM_', 'CLANG_', 'DYLD_', 'LD_'))}
        env.update(TMPDIR=str(output/'temporary'), SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
                   CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'), XDG_CACHE_HOME=str(output/'swift-cache'),
                   GIT_OPTIONAL_LOCKS='0', SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2')
        manifest = json.loads(base.read(MANIFEST, maximum=256*1024))
        assert manifest['schema'] == 1 and manifest['scope'] == 'ISOLATED_ORIGINAL_CATALOG_NATIVE1_COMPILER_FULL_SOURCE_ONLY'
        assert manifest['expectedCounts']['methods']==0 and manifest['expectedCounts']['plannedNativeMethods']==1 and len(manifest['preparedSources'])==3
        assert manifest['expectedCounts']['compiledTestFiles']==2 and manifest['expectedCounts']['excludedEarlierMethods']==3
        assert set(manifest['excludedEarlierMethods'])=={'NativeCanonicalDefinitionSupplementTests'}
        baseline = json.loads(base.read(BASELINE_INPUTS,maximum=131072))
        assert len(baseline)==313 and manifest['original313ManifestSHA256']==BASELINE_INPUTS_SHA
        assert len(manifest['originalProjectFiles'])==85
        assert all(baseline[entry['path']]==entry['sha256'] for entry in manifest['originalProjectFiles'])
        for path, expected in controls.items():
            base.pinned(path, expected)
            immutable[str(path)] = base.row(path)
        dependency_status('before', manifest)
        helper = load_module(CRYPTO_HELPER, 'bookmark_creation_crypto', CRYPTO_HELPER_SHA, base)
        guard()
        reused = helper.qualify(output, base, guard)
        immutable.update(reused['immutableInputs'])
        copies.update(reused['copiedModules'])
        copies.update(reused['copiedHeaders'])
        copies[reused['receipt']['path']] = {key:reused['receipt'][key] for key in ('bytes','sha256')}
        guard()
        fixture_input_helper = load_module(FIXTURE_INPUTS, 'provider_fixture_inputs', FIXTURE_INPUTS_SHA, base)
        fixture_input_admission = fixture_input_helper.qualify(output/'source-fixtures', base, guard, immutable, copies)
        result['originalFixtureCustody'] = fixture_input_admission['receipt']
        guard()
        package = output/'package'
        package.mkdir(mode=0o700)

        def materialize(path, target, expected):
            remember_input(path, expected)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            base.copy_exact(path, target, {'bytes':expected['bytes'], 'sha256':expected['sha256']})
            copies[str(target)] = base.row(target)

        project_root = Path(manifest['originalProjectRoot'])
        for entry in manifest['originalProjectFiles']:
            source = project_root/entry['path']
            remember_input(source, entry)
            if entry['compile']:
                target = package/'Tests/CatalogNativeTests'/source.name if entry['kind']=='test-helper' else package/'Sources'/entry['target']/source.name
                materialize(source, target, entry)
        core_root = Path(manifest['originalCoreRoot'])
        assert {str(path.relative_to(core_root)) for path in (core_root/'Sources/TorahInspectorCore').rglob('*.swift')} == {entry['path'] for entry in manifest['originalCoreFiles']}
        for entry in manifest['originalCoreFiles']:
            source = core_root/entry['path']
            materialize(source, package/'Sources/TorahInspectorCore'/source.name, entry)
        for entry in manifest['preparedSources']:
            source = PREPARED/entry['path']
            if entry['kind']=='production':
                target = package/'Sources'/entry['target']/source.name
            elif entry['kind']=='test':
                target = package/'Tests/CatalogNativeTests'/source.name
            else:
                raise AssertionError('undeclared new provider source kind')
            materialize(source,target,entry)
        assert len(list((package/'Sources').rglob('*.swift'))) == 94
        assert len(list((package/'Tests/CatalogNativeTests').glob('*.swift'))) == 2
        package_file = package/'Package.swift'
        package_file.write_text(package_text(reused['compilerFlags'], reused['linkObjects']))
        os.chmod(package_file, 0o600)
        copies[str(package_file)] = base.row(package_file)
        source_admission_complete = True
        source_input_file = output/'compiled-source-inputs.json'
        save(source_input_file, {'originalInputs':immutable, 'isolatedCopies':copies,
              'counts':manifest['expectedCounts'], 'indexStore':'enabled; no disable-index-store flag',
              'noExistingProjectModuleImportDirectories':True})
        # Bind these exact generated Package/Crypto/source expectations to the
        # successful component receipt; a later consumer cannot replace this
        # manifest and merely compare a new self-consistent set of copies.
        result['compiledSourceInputs'] = dict(path=str(source_input_file), **base.row(source_input_file))
        copies[str(source_input_file)] = {key:result['compiledSourceInputs'][key] for key in ('bytes','sha256')}
        swift_folder = output/'commands'/'swift-components'
        test_env = dict(env, PINKHA_NATIVE_DEFINITION_RETAINED=fixture_input_admission['retainedDirectory'],
                        PINKHA_NATIVE_ORIGINAL156=fixture_input_admission['originalDirectory'])
        argv = [reused['swiftDriver'],'build','--package-path',str(package),'--scratch-path',str(output/'build'),
                '--cache-path',str(output/'swift-cache'),'--config-path',str(output/'swift-config'),
                '--security-path',str(output/'swift-security'),'--disable-automatic-resolution','--jobs','2',
                '--build-tests']
        raw, swift = command('swift-components', argv, package, test_env, SWIFT_SECONDS)
        log = raw.decode(errors='strict')
        expected = {name+'.'+method for name,methods in manifest['methods'].items() for method in methods}
        assert len(expected) == 1 and expected == {'NativeImportedCatalogReadReopenTests.testAllOriginalCatalogRowsAndMetadataReadSignedNativeStateAndColdReopen'}
        starts = re.findall(r"Test Case '([^']+)' started", log)
        passes = re.findall(r"Test Case '([^']+)' passed", log)
        assert not starts and not passes, 'compiler-only command must execute no XCTest'
        assert not re.search(r"Test Suite .* started|Executed [0-9]+ tests?|Test run with [0-9]+ tests?|XCTSkip|Skipping XCTest discovery", log)
        result['earlierTestStarts'] = []
        result['earlierTestReplayStatus'] = 'NOT_RUN'
        result['actualMethods'] = {'started':[], 'passed':[], 'skipped':0, 'total':0}
        result['plannedNativeMethods'] = sorted(expected)
        result['nativeMethodRuntimeStatus'] = 'NOT_RUN'
        result['compilerInvocation'] = {'swiftDriver':reused['swiftDriver'], 'packageRoot':str(package),
            'buildRoot':str(output/'build'), 'cacheRoot':str(output/'swift-cache'),
            'configRoot':str(output/'swift-config'), 'securityRoot':str(output/'swift-security'),
            'temporaryRoot':str(output/'temporary'), 'argv':argv, 'testMethodsExecuted':0}
        assert not list((output/'http-fixtures').iterdir()), 'this data-only cohort creates no HTTP fixture'
        result['httpFixtureQualification'] = {'instances':0,'fixtureDirectoryEmpty':True,'runtimeHTTPAcceptance':'NOT_IN_THIS_COHORT'}
        result['retainedDependencyProducts'] = reused['receipt']
        product_closure = retained_products(output/'build', base, guard)
        result['compiledProducts'] = product_closure['files']
        result['compiledProductModes'] = product_closure['modes']
        result['compiledProductDirectories'] = product_closure['directories']
        result['compiledExecutables'] = product_closure['executables']
        result['compiledTestRunner'] = product_closure['testRunner']
        result['compiledProductsRoot'] = product_closure['root']
        dependency_status('after', manifest)
        result['status'] = 'PASS_NATIVE_CATALOG1_COMPILED_NOT_RUN'
    except BaseException as error:
        result['status'] = 'FAIL'
        result['errors'].append({'type':type(error).__name__, 'message':str(error)})
    finally:
        owned.ignore_interrupts()
        final_deadline = time.monotonic()+120
        # Cached positive observations survive any later integrity/budget error.
        result['allStartedOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') is True for row in result['commands'])
        try:
            for path, expected in immutable.items():
                guard()
                assert base.row(Path(path)) == expected, path+' final original input mismatch'
            for path, expected in copies.items():
                guard()
                assert base.row(Path(path)) == expected, path+' final copied input mismatch'
            if 'compiledSourceInputs' in result:
                original = result['compiledSourceInputs']
                assert base.row(Path(original['path'])) == {key:original[key] for key in ('bytes','sha256')}
                result['compiledSourceInputsUnchanged'] = True
            if 'compiledProducts' in result:
                after_products = retained_products(output/'build', base, guard)
                assert after_products['root'] == result['compiledProductsRoot']
                assert after_products['files'] == result['compiledProducts']
                assert after_products['modes'] == result['compiledProductModes']
                assert after_products['directories'] == result['compiledProductDirectories']
                assert after_products['executables'] == result['compiledExecutables']
                assert after_products['testRunner'] == result['compiledTestRunner']
                result['compiledProductsAndModesUnchanged'] = True
            for path, expected in controls.items():
                guard()
                base.pinned(path, expected)
            if reused is not None:
                helper.validate_after(reused, guard)
            if fixture_input_admission is not None:
                fixture_input_helper.validate_after(fixture_input_admission,base,guard)
                result['originalSourceFixtureInputsAndCopiesUnchanged']=True
            result['admittedInputsUnchanged'] = True
            result['sourceUnchanged'] = source_admission_complete
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-integrity', 'type':type(error).__name__, 'message':str(error)})
        try:
            swift_log = output/'commands/swift-components/original.log'
            if swift_log.exists() and manifest is not None:
                raw_log = base.read(swift_log, maximum=LOG_CAP).decode(errors='replace')
                starts = re.findall(r"Test Case '([^']+)' started", raw_log)
                excluded = {name+'.'+method for name,methods in manifest['excludedEarlierMethods'].items() for method in methods}
                native_starts = [name for name in starts if name in excluded]
                result['earlierTestStarts'] = native_starts
                result['earlierTestReplayStatus'] = 'NOT_RUN' if not native_starts else 'UNEXPECTED_COMPONENT_START'
                assert not native_starts, 'unexpected earlier canonical test start in component command'
            reason = observe()
            if reason is not None:
                raise RuntimeError(reason)
            assert all(row['exitCode'] == 0 and row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] for row in result['commands'])
            if result['status'] == 'PASS_NATIVE_CATALOG1_COMPILED_NOT_RUN':
                assert len(result['commands']) == 7 and result['actualMethods']['total'] == 0 and result['nativeMethodRuntimeStatus'] == 'NOT_RUN'
                assert result['httpFixtureQualification']['instances'] == 0
                assert result['httpFixtureQualification']['fixtureDirectoryEmpty'] is True and not list((output/'http-fixtures').iterdir())
        except BaseException as error:
            result['status'] = 'FAIL'
            result['errors'].append({'phase':'final-lifecycle-and-budget', 'type':type(error).__name__, 'message':str(error)})
        result['seconds'] = round(time.monotonic()-started_at,3)
        result['declaredControlledOutputBytesOnRoot'] = 0
        result['noGlobalRootWriteAuditClaim'] = True
        result['ownedOutputCreated'] = owned_output
        if owned_output:
            save(output/'result.json', result)
    print(json.dumps({'status':result['status'], 'receipt':str(output/'result.json') if owned_output else None,
                      'sha256':base.sha(output/'result.json') if owned_output else None, 'seconds':result['seconds'],
                      'errors':result['errors']}))
    return 0 if result['status'] == 'PASS_NATIVE_CATALOG1_COMPILED_NOT_RUN' else 1


if __name__ == '__main__':
    raise SystemExit(main())
