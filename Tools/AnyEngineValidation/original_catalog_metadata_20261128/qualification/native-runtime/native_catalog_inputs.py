"""Read-only byte, source, product, original-account and physical-custody gates.

This module never starts a process or opens an account/database API. The sole
copy routine writes only the caller's exclusive account copy, after admission.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MIB = 1024**2
PARENT = Path('/mnt/development/projects/evidence/pinkha-original-catalog-native1-20261127')
COMPILED = PARENT/'components-attempt1'
PREPARED = PARENT/'prepared1'
COMPILER = PREPARED/'run_native_catalog_components.py'
MANIFEST = PREPARED/'catalog-native-component-inputs.json'
METHOD = 'NativeImportedCatalogReadReopenTests.testAllOriginalCatalogRowsAndMetadataReadSignedNativeStateAndColdReopen'
NATIVE_ROOT = Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current')
OLD_BINARY = NATIVE_ROOT/'any'
NATIVE = Path('/mnt/development/projects/evidence/pinkha-w1-native1dc-physical-relocation-20261127/attempt1/any-1dc1803c')
BINARY_SHA = '1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636'
CUSTODY = NATIVE.with_name('result.json')
CUSTODY_SHA = '3687de9ce7e0531e2c7cf60c19c027c1c6a2f46efb8cf9cc67cdd5daa4ba96cc'
CUSTODY_CONTROLLER_SHA = '4ca6916a47f01963e74a3f8bd1d9e7ebae5b7a3d5c0db368c9170d596d0b71de'
CUSTODY_PLAN_SHA = 'cf3c8bddf3326714809d56cf20152f86cbfe7fb871ff9a5288d89a2161d617a8'
NATIVE_MANIFEST_SHA = '12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c'
BUILD_SHA = '6d0f00da205846575bfd49e3fba8121aa1570a940ea3e13cc571aa4b4734e2f0'
CONFIG = NATIVE_ROOT/'source/internal/config/nodeconf-prod.yml'
CONFIG_SHA = '6554bc5841fbef2a1ee6ab65ac3b14a9117dbb762d8cc8d419633c8cd413b060'
PROJECT = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127')
OFFLINE = PROJECT/'Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py'
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
SECCOMP = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
SECCOMP_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
POLICY = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-native-attempt3/result.json')
POLICY_SHA = 'afef209a66b65edf14dd2acff2d53b073e2bb37d1937928592af3f9378d0f3ab'
RETAINED = Path('/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1')
ORIGINAL_ACCOUNT = RETAINED/'native/private-account'
PRESERVATION_SHA = 'f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b'
ORIGINAL_NATIVE_RECEIPT_SHA = '5925bd5a08c972e3dbe7666b77f9e230fe340b36b46289c870384e66c516a899'
SOURCE_FACTS = Path('/var/lib/pinkha-w1-functional-migration-20261127/source-facts-native-attempt2/result.json')
SOURCE_FACTS_SHA = '75b89be27bae3a746ba2c6673b20c97429288f8336ceb5c428fc009d29001383'
ALLOCATION = Path('/var/lib/pinkha-w1-functional-migration-20261127/canonical-native-allocation-measurement1/result.json')
ALLOCATION_SHA = '023e19116534d131b38553c979920602eb179be1d7d57b57e5b5e576816bb261'
BASELINE_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
ORIGINAL_MAPPING_FILES = {
    'source-preservation-plan.json': '4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930',
    'execute-mappings.json': 'eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3',
    'execute-verification.json': 'fee4dc5cb8e689e01bf2d1fbe8bd262c42388fd706da4114be72af3e6cf97350',
}
SWIFT_ROOT = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
CACHE = Path('/tmp/pinkha-w1-migration-swift-20261127')
PHYSICAL_CACHE = Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127')
COMPILER_ALIASES = {
    SWIFT_ROOT/'swift': SWIFT_ROOT/'swift-driver',
    SWIFT_ROOT/'swiftc': SWIFT_ROOT/'swift-driver',
    SWIFT_ROOT/'clang': SWIFT_ROOT/'clang-21',
    SWIFT_ROOT/'clang++': SWIFT_ROOT/'clang-21',
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def physical(path, directory=False):
    path = Path(path)
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'exact physical input path')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'declared input kind')
    if not directory:
        require(info.st_nlink==1, 'one regular physical input link')
    return info


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid, info.st_gid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read(path, maximum=8*MIB):
    path = Path(path)
    before = physical(path)
    require(0<=before.st_size<=maximum, 'bounded complete regular input')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(signature(os.fstat(stream.fileno()))==signature(before), 'same opened input')
        raw = stream.read(maximum+1)
        require(signature(os.fstat(stream.fileno()))==signature(before), 'input changed during read')
    require(signature(path.lstat())==signature(before) and len(raw)==before.st_size, 'complete unchanged input')
    return raw


def row(path, guard=lambda: None, maximum=512*MIB):
    path = Path(path)
    before = physical(path)
    require(0<=before.st_size<=maximum, 'bounded complete hashed input')
    total, digest = 0, hashlib.sha256()
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(signature(os.fstat(stream.fileno()))==signature(before), 'same hashed input descriptor')
        while chunk := stream.read(MIB):
            guard(); total += len(chunk); digest.update(chunk)
            require(total<=before.st_size, 'bounded hashed input stream')
        require(signature(os.fstat(stream.fileno()))==signature(before), 'hashed input changed during read')
    require(signature(path.lstat())==signature(before) and total==before.st_size, 'hashed input changed at completion')
    return {'bytes': total, 'sha256': digest.hexdigest()}


def pin(path, digest, guard, sink, maximum=512*MIB):
    guard()
    actual = row(path, guard, maximum)
    require(actual['sha256']==digest, 'exact caller or original public input pin')
    sink[str(path)] = {**actual, 'mode': stat.S_IMODE(Path(path).lstat().st_mode)}
    return actual


def json_pin(path, digest, guard, sink, maximum=8*MIB):
    pin(path, digest, guard, sink, maximum)
    return json.loads(read(path, maximum))


def directory_entries(root):
    """No-atime directory census; never follow aliases or special members."""
    root = Path(root)
    physical(root, True)
    stack = [root]
    count = 0
    while stack:
        folder = stack.pop()
        fd = os.open(folder, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
        try:
            names = sorted(os.listdir(fd))
        finally:
            os.close(fd)
        for name in names:
            path = folder/name
            before = path.lstat()
            require(path.resolve()==path and not path.is_symlink(), 'no undeclared tree alias')
            require(stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode), 'regular tree members only')
            count += 1
            require(count<=20000, 'bounded admitted tree membership')
            yield path, before
            if stat.S_ISDIR(before.st_mode):
                stack.append(path)


def files(root, guard):
    result = {}
    for path, before in directory_entries(root):
        guard()
        if stat.S_ISREG(before.st_mode):
            result[path.relative_to(root).as_posix()] = row(path, guard)
            require(signature(path.lstat())==signature(before), 'tree input changed during census')
    return result


def products(root, guard):
    physical(root, True)
    entries = [(root, root.lstat())]+list(directory_entries(root))
    data, modes, directories, executables = {}, {}, {}, {}
    for path, before in entries:
        guard()
        key, mode = str(path), stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            directories[key] = mode
        else:
            data[key] = row(path, guard, 128*MIB)
            modes[key] = mode
            if mode & 0o111:
                executables[key] = {**data[key], 'mode': mode}
        require(signature(path.lstat())==signature(before), 'compiled product changed during census')
        require(len(data)+len(directories)<=4096, 'bounded complete product closure')
    runners = [key for key in data if Path(key).name=='CatalogNativeTests-test-runner']
    libraries = [key for key in data if Path(key).name=='CatalogNativeTests.so']
    require(len(runners)==len(libraries)==1 and runners[0] in executables, 'one qualified native catalog launcher and test library')
    require(any('PinkhaAnyEngine' in key and '.swiftmodule' in key for key in data) and
            any('PinkhaAnyHost' in key and '.swiftmodule' in key for key in data), 'actual Engine and Host module products')
    return {'root': str(root), 'files': data, 'modes': modes, 'directories': directories,
            'executables': executables, 'testRunner': {'path': runners[0], **executables[runners[0]]}}


def compiler_input_path(path):
    """Only the producer's four exact tool aliases and retained cache mapping."""
    path = Path(path)
    if path in COMPILER_ALIASES:
        target = COMPILER_ALIASES[path]
        require(path.resolve()==target and target.resolve()==target, 'exact producer tool alias target')
        if path.name in ('swift','swiftc'):
            require(os.readlink(path)=='swift-driver', 'unchanged Swift driver link')
        elif path.name=='clang':
            require(os.readlink(path)=='clang-21', 'unchanged Clang driver link')
        else:
            require(os.readlink(path)=='clang' and os.readlink(SWIFT_ROOT/'clang')=='clang-21', 'unchanged C++ driver links')
        physical(target)
        return target
    if path.is_relative_to(CACHE):
        require(CACHE.is_symlink() and os.readlink(CACHE)==str(PHYSICAL_CACHE), 'one retained cache alias')
        target = PHYSICAL_CACHE/path.relative_to(CACHE)
        require(path.resolve()==target, 'exact retained cache child')
        physical(target)
        return target
    physical(path)
    return path


def compiler(receipt_sha, controller_sha, manifest_sha, guard, sink):
    """Admit the future exact compiler-only product; never accept tests by label."""
    build = json_pin(COMPILED/'result.json', receipt_sha, guard, sink)
    pin(COMPILER, controller_sha, guard, sink)
    manifest = json_pin(MANIFEST, manifest_sha, guard, sink)
    require(build['status']=='PASS_NATIVE_CATALOG1_COMPILED_NOT_RUN' and build['errors']==[], 'successful compile-only catalog producer')
    require(build['controllerSHA256']==controller_sha and build['inputManifestSHA256']==manifest_sha, 'compiler source and independent manifest joined')
    require(all(build[key] is True for key in ['sourceUnchanged', 'admittedInputsUnchanged',
        'compiledSourceInputsUnchanged', 'originalSourceFixtureInputsAndCopiesUnchanged',
        'compiledProductsAndModesUnchanged', 'allStartedOwnedGroupsPositivelyAbsent']), 'all actual compiler input/product final gates')
    commands = build['commands']
    require(len(commands)==7 and all(item['exitCode']==0 and item['processGroupAbsent'] is True and
        not item['forcedCleanup'] and not item['cleanupErrors'] and not item['signals'] and item['stopReason'] is None
        for item in commands), 'seven actual closed normal compiler commands')
    require(build['earlierTestStarts']==[] and build['earlierTestReplayStatus']=='NOT_RUN', 'no earlier selected tests')
    source_file = build['compiledSourceInputs']
    require(source_file['path']==str(COMPILED/'compiled-source-inputs.json'), 'fixed compiled-source admission location')
    source = json_pin(Path(source_file['path']), source_file['sha256'], guard, sink)
    require(row(Path(source_file['path']), guard)=={key:source_file[key] for key in ('bytes','sha256')}, 'exact source manifest bytes')
    require(len(manifest['originalProjectFiles'])==85 and len(manifest['originalCoreFiles'])==8 and
            len(manifest['preparedSources'])==3, 'exact original/native catalog compile composition')
    require(manifest['expectedCounts']['productionCompiledFiles']==94 and
            manifest['expectedCounts']['compiledTestFiles']==2, '94 production and two full test files')
    package = COMPILED/'package'
    expected = {}
    for entry in manifest['originalProjectFiles']:
        original = Path(manifest['originalProjectRoot'])/entry['path']
        require(source['originalInputs'][str(original)]=={key:entry[key] for key in ('bytes','sha256')}, 'exact original full source row')
        if entry['compile']:
            target = package/'Tests/CatalogNativeTests'/original.name if entry['kind']=='test-helper' else package/'Sources'/entry['target']/original.name
            require(str(target) not in expected, 'no same-name source overwrite')
            expected[str(target)] = {key:entry[key] for key in ('bytes','sha256')}
    for entry in manifest['originalCoreFiles']:
        original = Path(manifest['originalCoreRoot'])/entry['path']
        target = package/'Sources/TorahInspectorCore'/original.name
        require(source['originalInputs'][str(original)]=={key:entry[key] for key in ('bytes','sha256')}, 'exact original Core source row')
        require(str(target) not in expected, 'unique original Core source target')
        expected[str(target)] = {key:entry[key] for key in ('bytes','sha256')}
    for entry in manifest['preparedSources']:
        original = PREPARED/entry['path']
        target = package/'Sources'/entry['target']/original.name if entry['kind']=='production' else package/'Tests/CatalogNativeTests'/original.name
        require(source['originalInputs'][str(original)]=={key:entry[key] for key in ('bytes','sha256')}, 'exact new catalog full source row')
        require(str(target) not in expected, 'unique new catalog source target')
        expected[str(target)] = {key:entry[key] for key in ('bytes','sha256')}
    require(len(expected)==96 and all(source['isolatedCopies'][key]==value for key,value in expected.items()), 'complete source-to-compiled-copy mapping')
    expected[str(package/'Package.swift')] = source['isolatedCopies'][str(package/'Package.swift')]
    require({str(package/key):value for key,value in files(package, guard).items()}==expected, 'no undeclared package source or manifest')
    dependency_row = build['retainedDependencyProducts']
    require(dependency_row['path']==str(COMPILED/'retained-dependency-products.json'), 'fixed retained dependency receipt')
    dependency = json_pin(Path(dependency_row['path']), dependency_row['sha256'], guard, sink)
    require(dependency['sharedAdmissionHelperSHA256']=='206bbf988fe28657ada7eb98079fad951d9cee66146da6a9204e7279fe845ad0' and
            dependency['dependencyCompilerInvocations']==0 and
            dependency['sharedProducerAdmission']['producerExactStableToPhysicalMapping']=={str(CACHE):str(PHYSICAL_CACHE)},
            'exact unchanged C3 dependency producer and admitted cache mapping')
    for field in ('originalInputs','isolatedCopies'):
        require(len(source[field])<=5000, 'bounded full compiler input membership')
        for name,wanted in source[field].items():
            path = compiler_input_path(name) if field=='originalInputs' else Path(name)
            require(row(path, guard)==wanted, 'every original and isolated compiler input unchanged')
            sink[str(path)] = {**wanted, 'mode':stat.S_IMODE(path.lstat().st_mode)}
    for name, mode in dependency['modes'].items():
        require(stat.S_IMODE(compiler_input_path(name).lstat().st_mode)==mode, 'all original C3 source/tool/product modes')
    baseline = json_pin(PREPARED/'compiled-source-313.json', BASELINE_SHA, guard, sink)
    require(len(baseline)==313, 'full historical C313 inventory')
    for name,digest in baseline.items():
        pin(PROJECT/name, digest, guard, sink)
    current = products(COMPILED/'build/out/Products', guard)
    for key, receipt_key in [('root','compiledProductsRoot'),('files','compiledProducts'),('modes','compiledProductModes'),
                             ('directories','compiledProductDirectories'),('executables','compiledExecutables'),('testRunner','compiledTestRunner')]:
        require(current[key]==build[receipt_key], 'complete compiler product/launcher binding')
    invocation = build['compilerInvocation']
    require(invocation['packageRoot']==str(package) and invocation['buildRoot']==str(COMPILED/'build'), 'fixed package and build locators')
    for field,leaf in [('cacheRoot','swift-cache'),('configRoot','swift-config'),('securityRoot','swift-security')]:
        require(invocation[field]==str(COMPILED/leaf), 'exact recorded Swift support locator')
    driver = Path(invocation['swiftDriver'])
    require(driver==SWIFT_ROOT/'swift' and driver.is_symlink() and os.readlink(driver)=='swift-driver', 'original exact Swift alias')
    driver_physical = SWIFT_ROOT/'swift-driver'
    require(driver.resolve()==driver_physical and str(driver_physical) in source['originalInputs'], 'physical driver is a compiled producer input')
    require(row(driver_physical, guard)==source['originalInputs'][str(driver_physical)], 'exact original Swift driver bytes')
    compile_row = commands[3]
    require(compile_row['argv']==invocation['argv'] and invocation['testMethodsExecuted']==0 and
            invocation['temporaryRoot']==str(COMPILED/'temporary'), 'exact emitted invocation agrees with owned compiler command')
    require(compile_row['argv'][:2]==[str(driver),'build'] and '--build-tests' in compile_row['argv'] and
            '--package-path' in compile_row['argv'] and '--scratch-path' in compile_row['argv'], 'actual build-tests-only Swift command')
    require(compile_row['cwd']==str(package), 'actual compiler package cwd')
    compile_log = COMPILED/'commands/swift-components/original.log'
    pin(compile_log, compile_row['logSHA256'], guard, sink, 16*MIB)
    log = read(compile_log, 16*MIB).decode()
    require(not re.search(r"Test Case '[^']+' (?:started|passed|failed|skipped)", log) and
            'Build complete!' in log, 'successful compile with zero XCTest execution')
    require(build['originalFixtureCustody']['path']==str(COMPILED/'source-fixtures/custody.json'), 'fixed original-fixture receipt')
    fixture = json_pin(COMPILED/'source-fixtures/custody.json', build['originalFixtureCustody']['sha256'], guard, sink)
    require(fixture['status']=='EXACT_ORIGINAL_FIXTURE_BYTES_COPIED_ONLY' and
            fixture['originalBundleMembers']==314 and fixture['retainedMappingDocuments']==3 and
            fixture['nativeAccountsOpened']==0 and fixture['original182OperationsReplayed']==0, 'complete original captured fixture custody only')
    require(build['actualMethods']=={'started':[],'passed':[],'skipped':0,'total':0} and
            build['plannedNativeMethods']==[METHOD] and build['nativeMethodRuntimeStatus']=='NOT_RUN', 'zero executed and one planned native method')
    return {'receipt':build, 'source':source, 'manifest':manifest, 'products':current, 'driver':str(driver),
            'package':str(package), 'scratch':str(COMPILED/'build'),
            'originalFixture':str(COMPILED/'source-fixtures/original156'),
            'retainedFixture':str(COMPILED/'source-fixtures/retained')}


def native(guard, sink):
    custody = json_pin(CUSTODY, CUSTODY_SHA, guard, sink)
    require(custody['status']=='PASS_UNCHANGED_PUBLIC_EXECUTABLE_PHYSICALLY_RELOCATED' and
            custody['errors']==custody['completionErrors']==[] and
            custody['controllerSHA256']==CUSTODY_CONTROLLER_SHA and custody['planSHA256']==CUSTODY_PLAN_SHA,
            'exact successful physical-location custody')
    require(custody['source']==str(OLD_BINARY) and custody['physicalDestination']['path']==str(NATIVE) and
            custody['physicalDestination']['sha256']==BINARY_SHA and custody['originalPhysicalCopyRelocated'] is True and
            custody['originalControlsUnchanged'] is True and custody['physicalDestinationVerifiedAtCompletion'] is True,
            'actual exact source-to-physical-destination preservation')
    require(OLD_BINARY.is_symlink() and os.readlink(OLD_BINARY)==str(NATIVE) and OLD_BINARY.resolve()==NATIVE and
            custody['logicalAliasFinal']['target']==str(NATIVE), 'one explicitly admitted logical alias')
    pin(NATIVE, BINARY_SHA, guard, sink)
    info = physical(NATIVE)
    saved = custody['physicalDestination']
    require(info.st_size==saved['bytes']==78072016 and stat.S_IMODE(info.st_mode)==saved['mode']==0o700 and
            info.st_uid==saved['uid']==0 and info.st_gid==saved['gid']==0 and info.st_nlink==1 and
            info.st_mtime_ns==int(saved['mtimeNS']) and os.listxattr(NATIVE,follow_symlinks=False)==[],
            'full original executable byte and portable metadata custody')
    # Access times can advance on execution. They are not a current-authority or
    # byte-integrity condition for a later legitimate consumer.
    manifest = json_pin(NATIVE_ROOT/'source-manifest.json', NATIVE_MANIFEST_SHA, guard, sink)
    build = json_pin(NATIVE_ROOT/'BUILD.json', BUILD_SHA, guard, sink)
    require(manifest['schema']=='pinkha-t2-permission-native-source-v1' and len(manifest['files'])==1594 and
            manifest['commits']=={'any':'8fbd1e819fb132ac0e0a848d2ddf5c5714189b81',
                'sdk':'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9'}, 'complete original native source identity')
    require(build['status']=='PASS_BUILD_ONLY' and build['exitCode']==0 and build['sourceUnchanged'] and build['ownedGroupAbsent'], 'original native producer closed')
    for name in ['source-before.json','source-after.json']:
        pin(NATIVE_ROOT/name, '7101539ffeb0d039afd5ba6eca4827f6389b2ce0a1311ee493331e2f6db31138', guard, sink)
    expected = {key:{field:value[field] for field in ('bytes','sha256')} for key,value in manifest['files'].items()}
    require(files(NATIVE_ROOT/'source', guard)==expected, 'all 1594 native source files remain exact')
    for key,value in manifest['files'].items():
        path = NATIVE_ROOT/'source'/key
        require(stat.S_IMODE(path.lstat().st_mode)==value['mode'], 'original native source modes')
        sink[str(path)] = {**expected[key], 'mode':value['mode']}
    pin(CONFIG, CONFIG_SHA, guard, sink)
    return {'binaryPath':str(NATIVE), 'binarySHA256':BINARY_SHA, 'custodyReceiptSHA256':CUSTODY_SHA,
            'originalBuildReceiptSHA256':BUILD_SHA, 'originalSourceManifestSHA256':NATIVE_MANIFEST_SHA,
            'sourceFiles':1594, 'executionAliasFallbackUsed':False}


def original_receipts(guard, sink):
    preservation = json_pin(RETAINED/'result.json', PRESERVATION_SHA, guard, sink)
    require(preservation['result']=='PASS' and preservation['sourceAdmissionPromoted'] is False and
            preservation['wholeSpaceMigration'] is False, 'original narrow preservation result')
    native_result = json_pin(RETAINED/'native/controller-result.json', ORIGINAL_NATIVE_RECEIPT_SHA, guard, sink)
    require(native_result['result']=='PROCESS_LIFECYCLE_PASS' and native_result['binarySHA256']==BINARY_SHA and
            len(native_result['processes'])==2 and all(item['exitCode']==0 and item['groupPositivelyAbsent']
                for item in native_result['processes']), 'original accepted retained account process closure')
    facts = json_pin(SOURCE_FACTS, SOURCE_FACTS_SHA, guard, sink)
    require(facts['status']=='PASS' and facts['errors']==[] and facts['allOwnedGroupsPositivelyAbsent'] is True and
            facts['originalAccountAndAcceptedReceiptsUnchanged'] is True and facts['sourceFactRecords']==2,
            'actually qualified predecessor boundary/account use remains historical')
    allocation = json_pin(ALLOCATION, ALLOCATION_SHA, guard, sink)
    require(allocation['status']=='MEASURED_ALLOCATION_BUDGET_ONLY_NOT_NATIVE_QUALIFICATION' and
            allocation['copyBlockRoundedUpperBoundBytes']==8637368 and
            allocation['resourcePolicy']['initialReserveMiB']==128, 'original retained-account copy bound and reserve')
    for name,digest in ORIGINAL_MAPPING_FILES.items():
        pin(RETAINED/'private-work'/name, digest, guard, sink)
    pin(OFFLINE, OFFLINE_SHA, guard, sink)
    pin(SECCOMP, SECCOMP_SHA, guard, sink)
    canonical = json_pin(POLICY, POLICY_SHA, guard, sink)
    policy = canonical['offlinePolicy']
    require(canonical['status']=='PASS' and canonical['allOwnedGroupsPositivelyAbsent'] is True and
            policy['helperSHA256']==OFFLINE_SHA and policy['baselineTCPReachable'] is True and
            policy['baselineUDPReceived'] is True and all(policy['controls'][key] is True for key in
                ['tcpDenied','udpDenied','noNewPrivileges','seccompFilterActive']), 'actual original OS denial proof reused without replay')
    return {'accountID':native_result['accountID'], 'spaceID':native_result['spaceID'],
            'policy':policy, 'retainedPolicyReceiptSHA256':POLICY_SHA,
            'historicalSourceFactsReceiptSHA256':SOURCE_FACTS_SHA, 'oldProofMethodsReexecuted':0}


def account_inventory(root, guard):
    physical(root, True)
    entries = [(root,root.lstat())]+list(directory_entries(root))
    require(len(entries)<=512, 'bounded retained account membership')
    rows, identities = {}, {}
    for path,before in entries:
        guard()
        name = '.' if path==root else path.relative_to(root).as_posix()
        value = {'kind':'directory' if stat.S_ISDIR(before.st_mode) else 'file',
                 'mode':stat.S_IMODE(before.st_mode), 'uid':before.st_uid, 'gid':before.st_gid,
                 'mtimeNS':str(before.st_mtime_ns),
                 'xattrsHex':{key:os.getxattr(path,key,follow_symlinks=False).hex()
                              for key in sorted(os.listxattr(path,follow_symlinks=False))}}
        if value['kind']=='file':
            value.update(row(path,guard,16*MIB))
        require(signature(path.lstat())==signature(before), 'retained account changed during read-only inventory')
        rows[name], identities[name] = value, list(signature(before))
    return {'rows':rows,'identities':identities}


def no_account_users(root, guard):
    """Current pathname observations only; no old PID probe or signalling."""
    prefix = str(root)
    processes = descriptors = aggregate_maps = 0
    matched = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name)==os.getpid():
            continue
        guard(); processes += 1
        require(processes<=16384, 'bounded current process census')
        reasons = set()
        try:
            with (proc/'cmdline').open('rb') as stream:
                command = stream.read(MIB+1)
            require(len(command)<=MIB, 'bounded process command metadata')
            if prefix.encode() in command:
                reasons.add('original-account-command')
            for name in ('cwd','root','exe'):
                try:
                    value = os.readlink(proc/name).removesuffix(' (deleted)')
                    if value==prefix or value.startswith(prefix+'/'):
                        reasons.add('original-account-'+name)
                except (FileNotFoundError,ProcessLookupError):
                    pass
            with (proc/'maps').open('rb') as stream:
                mapping = stream.read(8*MIB+1)
            aggregate_maps += len(mapping)
            require(len(mapping)<=8*MIB and aggregate_maps<=128*MIB, 'bounded current mapping metadata')
            if prefix.encode() in mapping:
                reasons.add('original-account-mapping')
            process_descriptors = 0
            for descriptor in (proc/'fd').iterdir():
                descriptors += 1; process_descriptors += 1
                require(descriptors<=262144 and process_descriptors<=16384, 'bounded descriptor metadata')
                try:
                    value = os.readlink(descriptor).removesuffix(' (deleted)')
                    if value==prefix or value.startswith(prefix+'/'):
                        reasons.add('original-account-descriptor')
                except (FileNotFoundError,ProcessLookupError):
                    pass
        except (FileNotFoundError,ProcessLookupError):
            continue
        if reasons:
            matched.append({'pid':int(proc.name),'reasons':sorted(reasons)})
    require(not matched, 'retained original account must have no active consumer')
    return {'processesExamined':processes,'descriptorsExamined':descriptors,'matching':[],
            'oldRecordedPIDReprobes':0,'processPayloadRetained':False}


def copy_account(root, destination, inventory, guard):
    require(not os.path.lexists(destination), 'one exclusive private account copy')
    block = os.statvfs(destination.parent).f_frsize
    upper = sum(block if value['kind']=='directory' else ((value['bytes']+block-1)//block)*block
                for value in inventory['rows'].values())
    require(upper<=9*MIB, 'original measured account-copy allocation remains bounded')
    destination.mkdir(mode=0o700)
    for name,value in sorted(inventory['rows'].items(),key=lambda item:(len(Path(item[0]).parts),item[0])):
        guard()
        source, target = root/name,destination/name
        if name=='.':
            continue
        if value['kind']=='directory':
            target.mkdir(mode=0o700)
            continue
        before = physical(source)
        require(list(signature(before))==inventory['identities'][name], 'exact original immediately before private copy')
        source_fd = os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
        target_fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        with os.fdopen(source_fd,'rb') as reader, os.fdopen(target_fd,'wb') as writer:
            require(signature(os.fstat(reader.fileno()))==signature(before), 'same original account descriptor')
            total,digest = 0,hashlib.sha256()
            while chunk:=reader.read(MIB):
                guard();total+=len(chunk);digest.update(chunk);writer.write(chunk)
                require(total<=value['bytes'], 'bounded original account copy')
            writer.flush();os.fsync(writer.fileno())
            require(total==value['bytes'] and digest.hexdigest()==value['sha256'] and
                    signature(os.fstat(reader.fileno()))==signature(before), 'complete unchanged original copied once')
        require(list(signature(source.lstat()))==inventory['identities'][name], 'original copy input remains unchanged')
    for name,value in sorted(inventory['rows'].items(),key=lambda item:(-len(Path(item[0]).parts),item[0])):
        target = destination if name=='.' else destination/name
        os.chown(target,value['uid'],value['gid'],follow_symlinks=False)
        os.chmod(target,value['mode'],follow_symlinks=False)
        for key,hex_value in value['xattrsHex'].items():
            os.setxattr(target,key,bytes.fromhex(hex_value),follow_symlinks=False)
        os.utime(target,ns=(int(value['mtimeNS']),int(value['mtimeNS'])),follow_symlinks=False)
        fd = os.open(target,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|(os.O_DIRECTORY if value['kind']=='directory' else 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    require(account_inventory(destination,guard)['rows']==inventory['rows'], 'full private copy bytes and portable metadata')
    require(account_inventory(root,guard)==inventory, 'original account unchanged by copy')
    return upper


def recheck(sink, guard):
    for name,wanted in sink.items():
        path = Path(name)
        require(row(path,guard)=={key:wanted[key] for key in ('bytes','sha256')} and
                stat.S_IMODE(path.lstat().st_mode)==wanted['mode'], 'all admitted immutable inputs and modes unchanged')
