#!/usr/bin/env python3
"""Read all original catalog rows, then reopen the same owned account copy.

This consumes one separately compiled, previously unexecuted native XCTest.
Original accounts, captured bytes, accepted operations and all compiler inputs
remain unchanged. The native service and Swift runner have distinct owned
process groups; the native leader remains unreaped during the complete test.
"""
import argparse
import base64
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import sys
import time
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
MIB = 1024**2
GIB = 1024**3
COMPILER_SHA = '6d9ab7f414d4035acc6242fe24c22c9835ef30c9433787a4d6952414fdec542f'
MANIFEST_SHA = '27a714acf039353cefa3d30a1726e4c36a35fef6aba4184d6c25ddd572ea8aa7'
COMPILED_RECEIPT_SHA = 'bd46d8b19f90ae4e544d530fb754426eecf244871b31dc14850ffec38fd9418a'
INPUT_HELPER_SHA = '0983b3b4d49bd3f73f7f995b5e234f882166554aff5b95bdcfb31cbfb4eeab70'
BOUNDARY_SHA = 'db3a44aded9c819115cc531ecf8f3682b7d8e43c25af8f64d9cbb51d13dfebfd'
CONTROL_PINS = {
    'native_catalog_inputs.py': INPUT_HELPER_SHA,
    'native_boundary_support.py': BOUNDARY_SHA,
    'owned_native_commands.py': 'c2e2c23d497d334431462cd5ee530aaa3b9e9b2cf160201fe0443c27672c5145',
    'owned_swift_commands_original.py': 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56',
    'absolute_http_source_original.py': '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84',
}
PARENT = Path('/mnt/development/projects/evidence/pinkha-original-catalog-native1-20261127')
OUTPUT = PARENT/'runtime-attempt3'
COMPILED_BUILD = PARENT/'components-attempt1/build'
PRIOR_RUNTIME_SHA = 'fa11738ec590a6ef6728da56f4f6a7eb51372f5978cb37c55710ff2135878db7'
PRIOR_CONTROLLER_SHA = 'f955131f30bca95ba9c53556aa00753d4eb52b8fca3216be36434c3a3d438465'
ORIGINAL_SPM_ALIAS = {'relative':'debug','target':'out/Products/Debug-linux-aarch64',
    'mode':0o777,'uid':0,'gid':1002,'bytes':32,'allocatedBytes':0,'nlink':1,
    'device':2064,'inode':938563,'mtimeNS':1795825136836727928}
SPM_ALIAS = dict(ORIGINAL_SPM_ALIAS,mtimeNS=1795829267333499955)
PRIOR_SKIP_BUILD_SHA = 'd8fc75ca82c6bfc545050562991d6fdd5ec690c6b8c1b0f23b0c0db7359d5c85'
PRIOR_SKIP_BUILD_CONTROLLER_SHA = 'b999c5575e063f323593774426ef669129ed56e5ccc7a617509ac7675803cb4c'
CUSTODY_SHA = '4586ba30301f754ec02c87233615f1dccf2522f97591d3f33cbb96859d37b314'
ENTRY_POINT = COMPILED_BUILD/'out/Intermediates.noindex/CatalogNativeProof.build/Debug-linux-aarch64/CatalogNativeTests-test-runner.build/DerivedSources/test_entry_point.swift'
ENTRY_POINT_SHA = '6f72edb72cf3ec158bb56458ac9be9777e93178ff0a8586ca0f61cdcb9a7693c'
OUTPUT_FILE_MAP = COMPILED_BUILD/'out/Intermediates.noindex/CatalogNativeProof.build/Debug-linux-aarch64/CatalogNativeTests-test-runner.build/Objects-normal/aarch64/CatalogNativeTests-test-runner-OutputFileMap.json'
OUTPUT_FILE_MAP_SHA = 'b48973a755d0f4da228327208b6b30feac6f9f3b82f232ef16361eaf9f9f7ab0'
XCTEST_LIBRARY = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/lib/swift/linux/libXCTest.so')
XCTEST_LIBRARY_SHA = 'd7cac136728527da145c21af1a1e463127b13670205bf12b7ecbd8a58a2093a2'
MAIN_SECONDS = 1100
FINAL_SECONDS = 120
REQUIRED_OUTER_SECONDS = 1260
ROOT_FLOOR = 2*GIB
ROOT_ADMISSION_RESERVE = 128*MIB
DEVELOPMENT_FLOOR = 512*MIB
OWNED_CAP = 160*MIB
DEVELOPMENT_RESERVE = 32*MIB
BUILD_INCREMENT_CAP = 16*MIB
NATIVE_PHASE_SECONDS = 500
SWIFT_PHASE_SECONDS = 400
METHOD = 'NativeImportedCatalogReadReopenTests.testAllOriginalCatalogRowsAndMetadataReadSignedNativeStateAndColdReopen'
DIRECT_TEST_SELECTOR = 'CatalogNativeTests.'+METHOD.replace('.', '/', 1)
DIRECT_TEST_NAMES = [
    'CatalogNativeTests.NativeCanonicalDefinitionSupplementTests/testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics',
    'CatalogNativeTests.NativeCanonicalDefinitionSupplementTests/testSupplementRefusesDuplicateExistingAndCallerChosenAliases',
    'CatalogNativeTests.NativeCanonicalDefinitionSupplementTests/testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace',
    DIRECT_TEST_SELECTOR,
]
STOP_SIGNALS = {signal.SIGTERM, signal.SIGINT}


def require(value, label):
    if not value:
        raise RuntimeError(label)


def read_control(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical public controller source')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=256*1024, 'bounded public control')
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        require(os.fstat(stream.fileno())==before, 'same public source descriptor')
        raw = stream.read(256*1024+1)
        require(os.fstat(stream.fileno())==before, 'public source changed during read')
    require(path.lstat()==before and len(raw)==before.st_size, 'complete public source read')
    return raw


def load_control(name, expected):
    path = HERE/name
    raw = read_control(path)
    require(hashlib.sha256(raw).hexdigest()==expected, 'exact complete controller helper')
    module = types.ModuleType('native_catalog_'+path.stem)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def compiler_build_alias():
    """Bind the one observed SPM link to the already qualified physical Products."""
    require(COMPILED_BUILD.resolve()==COMPILED_BUILD, 'physical original compiler build')
    link = COMPILED_BUILD/'debug'
    before = link.lstat()
    require(stat.S_ISLNK(before.st_mode), 'original SPM debug member is a link')
    observed = {'relative':'debug','target':os.readlink(link),
        'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,'gid':before.st_gid,
        'bytes':before.st_size,'allocatedBytes':before.st_blocks*512,'nlink':before.st_nlink,
        'device':before.st_dev,'inode':before.st_ino,'mtimeNS':before.st_mtime_ns}
    require(observed==SPM_ALIAS, 'exact observed compiler-only SPM alias metadata and text')
    target = COMPILED_BUILD/'out/Products/Debug-linux-aarch64'
    info = target.lstat()
    require(target.resolve()==target and not target.is_symlink() and stat.S_ISDIR(info.st_mode) and
            stat.S_IMODE(info.st_mode)==0o2700 and link.resolve()==target,
            'SPM alias names only the complete producer-qualified physical Products directory')
    after = link.lstat()
    identity = lambda item: (item.st_dev,item.st_ino,item.st_mode,item.st_nlink,item.st_uid,item.st_gid,
        item.st_size,item.st_blocks,item.st_mtime_ns,item.st_ctime_ns)
    require(identity(after)==identity(before), 'SPM alias unchanged during metadata observation')
    return {'link':observed,'physicalTarget':str(target),'targetMode':stat.S_IMODE(info.st_mode),
        'targetDevice':info.st_dev,'targetInode':info.st_ino,'targetUID':info.st_uid,'targetGID':info.st_gid}


def allocated(root, compiler_alias=None):
    """Count only a physical tree; the exact compiler link counts once, never followed."""
    if compiler_alias is not None:
        require(root==COMPILED_BUILD and compiler_build_alias()==compiler_alias,
                'only the fixed original compiler build admits its pinned SPM link')
    seen_aliases = set()
    if not root.exists():
        return 0
    require(root.resolve()==root and not root.is_symlink(), 'controlled physical allocation root')
    total = count = 0
    for folder, directories, names in os.walk(root, followlinks=False):
        for name in [None]+names:
            path = Path(folder) if name is None else Path(folder)/name
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'controlled allocation contains regular members only')
            if stat.S_ISREG(info.st_mode):
                require(info.st_nlink==1, 'no shared output hardlink')
            count += 1
            require(count<=100000, 'bounded controlled allocation membership')
            total += info.st_blocks*512
        for name in list(directories):
            path = Path(folder)/name
            if path.is_symlink():
                require(compiler_alias is not None and root==COMPILED_BUILD and path==COMPILED_BUILD/'debug',
                        'no runtime output alias or undeclared compiler alias')
                require(compiler_build_alias()==compiler_alias, 'same compiler alias before inode-only accounting')
                info = path.lstat()
                total += info.st_blocks*512
                count += 1
                require(count<=100000, 'bounded controlled allocation membership')
                seen_aliases.add('debug')
                directories.remove(name)
        require(all(not (Path(folder)/name).is_symlink() for name in directories), 'no followed output alias')
    require(seen_aliases==({'debug'} if compiler_alias is not None else set()), 'exact admitted alias membership')
    return total


def memory_available():
    with Path('/proc/meminfo').open() as stream:
        lines = stream.read(16385)
    require(len(lines)<=16384, 'bounded memory metadata')
    values = dict(line.split(':', 1) for line in lines.splitlines() if ':' in line)
    return int(values['MemAvailable'].split()[0])*1024


def main():
    require(not sys.flags.optimize, 'all original qualification guards remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    require(args.output==OUTPUT and OUTPUT.parent.resolve()==OUTPUT.parent, 'one declared physical output namespace')
    inputs = load_control('native_catalog_inputs.py', INPUT_HELPER_SHA)
    boundary = load_control('native_boundary_support.py', BOUNDARY_SHA)
    os.umask(0o077)
    began = time.monotonic()
    final_deadline = None
    active_native_deadline = None
    owned_output = False
    serial = 0
    last_allocation = 0.0
    build_allocation_before = None
    compiler_alias_before = None
    owner = lifecycle = compiled = source_identity = account_before = None
    current_native = None
    admitted = {}
    control_before = {}
    minimum_root = minimum_dev = None
    work, logs, account_copy = OUTPUT/'private-work', OUTPUT/'private-logs', OUTPUT/'private-account'
    runtime_support = OUTPUT/'swift-runtime'
    result = {
        'protocol':'pinkha-original-catalog-native-read-reopen-v1',
        'status':'RUNNING', 'scope':'159 original catalog Records, 156 exact captured snapshots, 3 uncaptured heads; 11 original metadata definitions through signed native reads and cold reopen',
        'compiledProducerReceiptSHA256':COMPILED_RECEIPT_SHA,
        'compilerControllerSHA256':COMPILER_SHA, 'compilerInputManifestSHA256':MANIFEST_SHA,
        'nativeMethod':METHOD, 'plannedPhases':['read','reopen'],
        'plannedOwnedGroups':6, 'directXCTestSelector':DIRECT_TEST_SELECTOR,
        'swiftPMTestInvocations':0, 'directRunnerListBeforeAccountCopy':False,
        'metadataCommands':[], 'nativeProcesses':[], 'swiftLaunches':[], 'phases':[],
        'requestLedger':[], 'errors':[], 'completionErrors':[],
        'allStartedOwnedGroupsPositivelyAbsent':False,
        'originalAccountsInitialized':0, 'newAccountsCreated':0, 'spacesCreated':0,
        'migrationOperationsReexecuted':0, 'priorComponentMethodsReexecuted':0,
        'domainWriteOperationsRequested':0, 'controllerHTTPMethods':['GET'],
        'nativeMethodMayUseReadOnlyQueryPOST':True,
        'compilerInvocations':0, 'dependencyCompilersInvoked':0,
        'sourceAdmissionPromoted':False, 'wholeSpaceMigration':False,
        'originalHistoryReconstructed':False, 'historicalAuthorIsDestinationSigner':False,
        'controlledOutputPathsOnRoot':[], 'noGlobalRootWriteAuditClaim':True,
        'resourcePolicy':{
            'mainSeconds':MAIN_SECONDS, 'finalSeconds':FINAL_SECONDS,
            'requiredOuterSeconds':REQUIRED_OUTER_SECONDS,
            'rootLiveFloorBytes':ROOT_FLOOR, 'rootAdmissionReserveBytes':ROOT_ADMISSION_RESERVE,
            'developmentLiveFloorBytes':DEVELOPMENT_FLOOR,
            'developmentAdmissionReserveBytes':DEVELOPMENT_RESERVE,
            'wholeOwnedOutputAndCompilerBuildIncrementCapBytes':OWNED_CAP,
            'compilerBuildAuxiliaryIncrementCapBytes':BUILD_INCREMENT_CAP,
            'nativePhaseSeconds':NATIVE_PHASE_SECONDS, 'swiftPhaseSeconds':SWIFT_PHASE_SECONDS,
            'initialMemoryAvailableBytesRequired':3*GIB,
            'allocationObservationMaximumIntervalSeconds':1,
            'budgetIsFiniteEstimateNotMeasuredPeak':True,
        },
        'maximumAllocationBytes':{'output':0,'compilerBuildIncrement':0,'combined':0},
        'finalIntegrity':{},
    }

    def record_failure(boundary_name, error, completion=False):
        result['status'] = 'FAIL_NATIVE_CATALOG_READ_REOPEN_PRESERVED'
        target = result['completionErrors'] if completion else result['errors']
        # Private response/account payloads never become public error strings.
        target.append({'boundary':boundary_name, 'type':type(error).__name__,
                       'message':str(error) if isinstance(error, RuntimeError) else 'bounded operation failed; retained private evidence'})

    def persist(path, value):
        nonlocal serial
        require(owned_output and path.is_relative_to(OUTPUT) and path.parent.resolve()==path.parent,
                'persist only inside the newly owned output')
        serial += 1
        raw = (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        require(len(raw)<=8*MIB, 'bounded owned JSON evidence')
        temporary = path.with_name(path.name+'.pending-'+str(os.getpid())+'-'+str(serial))
        fd = os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        fsync_directory(path.parent)

    def save():
        result['seconds'] = round(time.monotonic()-began,3)
        result['minimumRootFreeBytes'] = minimum_root
        result['minimumDevelopmentFreeBytes'] = minimum_dev
        if owned_output:
            persist(OUTPUT/'result.json',result)

    def budget(force=False):
        nonlocal minimum_root, minimum_dev, last_allocation
        now = time.monotonic()
        deadline = final_deadline if final_deadline is not None else began+MAIN_SECONDS
        if active_native_deadline is not None:
            deadline = min(deadline,active_native_deadline)
        require(now<deadline, 'bounded main or independent final deadline')
        root_free = shutil.disk_usage('/').free
        dev_free = shutil.disk_usage(PARENT).free
        minimum_root = root_free if minimum_root is None else min(root_free,minimum_root)
        minimum_dev = dev_free if minimum_dev is None else min(dev_free,minimum_dev)
        require(root_free>ROOT_FLOOR, 'unchanged root live floor')
        require(dev_free>DEVELOPMENT_FLOOR, 'unchanged development live floor')
        require(not (OUTPUT/'abort').exists(), 'explicit owned controller abort')
        if owned_output and (force or now-last_allocation>=1):
            output_bytes = allocated(OUTPUT)
            increment = 0 if build_allocation_before is None else max(0,allocated(inputs.COMPILED/'build',compiler_alias_before)-build_allocation_before)
            values = {'output':output_bytes,'compilerBuildIncrement':increment,'combined':output_bytes+increment}
            for key,value in values.items():
                result['maximumAllocationBytes'][key] = max(value,result['maximumAllocationBytes'][key])
            require(increment<=BUILD_INCREMENT_CAP, 'bounded skip-build auxiliary output increment')
            require(output_bytes+increment<=OWNED_CAP, 'bounded complete owned runtime output')
            require(allocated(account_copy)<=73*MIB, 'original retained account runtime allocation bound')
            require(allocated(logs)<=16*MIB, 'bounded complete private process and HTTP logs')
            last_allocation = now

    def guard():
        budget(False)

    def digest(path):
        return inputs.row(Path(path),guard)['sha256']

    def normal_command(row):
        return (row.get('exitCode')==0 and row.get('processGroupAbsent') is True and
                row.get('forcedCleanup') is False and row.get('cleanupErrors')==[] and
                row.get('signals')==[] and row.get('stopReason') is None)

    def observe():
        try:
            guard()
            if current_native is not None:
                pid = current_native['pid']
                require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None,
                        'original native leader remains live and unreaped through the test')
                require(os.getpgid(pid)==os.getsid(pid)==pid, 'same live owned native session during test')
            return None
        except BaseException as error:
            return type(error).__name__+': '+str(error)

    def expected_phase(phase):
        return {
            'phase':phase,'nativeCatalogRecords':159,'originalSnapshots':156,'uncapturedHeads':3,
            'originalMetadataDefinitions':11,'metadataPresentExamples':5,'metadataAbsentExamples':11,
            'uncapturedSnapshotRefusals':3,'allOriginalBytesEqual':True,
            'allCurrentRowsEqualSignedCreation':True,'forgedMappingFingerprintRefused':True,
            'foreignSpaceRefused':True,'revokedLeaseRefused':True,
            'preparedOperations':0,'domainWriteOperationsRequested':0,
            'historicalAuthorIsDestinationSigner':False,'originalHistoryReconstructed':False,
            'sourceAdmissionPromoted':False,'wholeSpaceMigration':False,
        }

    def validate_comparison(path):
        raw = inputs.read(path,32*MIB)
        value = json.loads(raw)
        require(set(value)=={'catalog','metadata'} and len(value['catalog'])==159 and len(value['metadata'])==16,
                'complete native catalog and metadata comparison shape')
        identities = [row['sourceObjectID'] for row in value['catalog']]
        require(len(set(identities))==159 and all(isinstance(x,str) and x for x in identities), '159 unique original catalog identities')
        captured = uncaptured = 0
        for observed in value['catalog']:
            guard()
            original = observed['original']
            require(observed['destinationCreation']['author']==source_identity['accountID'] and
                    observed['sourceAccountID']!=source_identity['accountID'], 'original author remains distinct from destination signer')
            if original['snapshotPresent'] is True:
                captured += 1
                stem = 'snapshot-'+hashlib.sha256(observed['sourceObjectID'].encode()).hexdigest()
                for suffix,key,hash_key in [('.pb','originalProtobufBase64','protobufSHA256'),
                                            ('.json','originalJSONBase64','jsonSHA256')]:
                    original_path = Path(compiled['originalFixture'])/'bundle'/(stem+suffix)
                    pinned = compiled['source']['isolatedCopies'][str(original_path)]
                    decoded = base64.b64decode(original[key],validate=True)
                    require(len(decoded)==pinned['bytes'] and hashlib.sha256(decoded).hexdigest()==
                            original[hash_key]==pinned['sha256'], 'each original captured byte pair remains exact')
            else:
                require(original=={'snapshotPresent':False}, 'uncaptured head cannot invent a snapshot')
                uncaptured += 1
        require(captured==156 and uncaptured==3, 'exact 156 captured and three uncaptured original heads')
        occurrences = {'addedDate':11,'createdInContext':0,'globalName':0,'importType':0,
                       'internalFlags':150,'oldAnytypeID':0,'origin':138,'revision':138,
                       'sourceObject':138,'timestamp':0,'uniqueKey':0}
        cases = {key:[] for key in occurrences}
        for observed in value['metadata']:
            role = observed['role']
            require(role in cases and observed['sourceObjectID'] in identities and
                    observed['originalOccurrenceCount']==occurrences[role], 'exact original metadata role and occurrence census')
            present = observed['observed']['present']
            require(type(present) is bool and set(observed['observed'])==({'present','value'} if present else {'present'}),
                    'preserved metadata presence including null and empty values')
            cases[role].append(present)
        require(all(sorted(cases[key])==([False,True] if count else [False]) for key,count in occurrences.items()),
                'one actual present example when available and one absent example per original definition')
        return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                'catalogRows':159,'originalBytePairs':156,'uncapturedHeads':3,'metadataExamples':16}

    def run_test(phase,native):
        budget(True)
        require(inputs.products(inputs.COMPILED/'build/out/Products',guard)==compiled['products'],
                'full original compiler products before selected native method')
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('PINKHA_','ANY_','SWIFT_')) and key not in
               {'TMPDIR','TMP','TEMP','SDKROOT','LD_PRELOAD','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH'}}
        env.update(PINKHA_NATIVE_CATALOG_FIXTURE=str(work/'runtime.json'),
                   PINKHA_NATIVE_CATALOG_WORK=str(work),PINKHA_NATIVE_CATALOG_PHASE=phase,
                   PINKHA_NATIVE_ORIGINAL156=compiled['originalFixture'],
                   PINKHA_NATIVE_DEFINITION_RETAINED=compiled['retainedFixture'],
                   TMPDIR=str(runtime_support/'temporary'),
                   SWIFT_MODULECACHE_PATH=str(runtime_support/'module-cache'),
                   CLANG_MODULE_CACHE_PATH=str(runtime_support/'clang-module-cache'))
        require(result['directRunnerListBeforeAccountCopy'] is True and
                result['actualListedXCTestNames']==DIRECT_TEST_NAMES,
                'one exact direct selector only after the physical runner list qualification')
        command = [compiled['products']['testRunner']['path'],DIRECT_TEST_SELECTOR]
        require(active_native_deadline is not None, 'nested test retains the original native phase deadline')
        test_timeout = min(SWIFT_PHASE_SECONDS,active_native_deadline-time.monotonic(),began+MAIN_SECONDS-time.monotonic())
        require(test_timeout>0, 'positive remaining native and main time for selected Swift method')
        path,row = owner.run(logs/(phase+'-swift'),command,Path(compiled['package']),env,
                             test_timeout,observe,persist,digest,result['swiftLaunches'])
        row.update(phase=phase,method=METHOD,nativePID=native['pid'],invocation='direct-compiled-XCTest',selector=DIRECT_TEST_SELECTOR)
        save()
        require(normal_command(row), 'selected native XCTest runner exited normally with positive owned absence')
        text = inputs.read(path,8*MIB).decode()
        started = re.findall(r"Test Case '([^']+)' started",text)
        passed = re.findall(r"Test Case '([^']+)' passed",text)
        require(started==passed==[METHOD] and 'Executed 1 test, with 0 failures' in text,
                'exact one new native method starts and passes per phase')
        require(not re.search(r"Test Case '[^']+' (?:failed|skipped)|Build complete!|Building for debugging|Compiling |Linking |Skipping XCTest discovery",text)
                and 'skipped' not in text.lower(), 'no failed/skipped method or hidden compilation')
        require(text.count('PINKHA_NATIVE_CATALOG_PHASE_PASS '+phase)==1, 'exact post-drain native phase marker')
        proof_path = work/(phase+'-result.json')
        proof = json.loads(inputs.read(proof_path,65536))
        expected = expected_phase(phase)
        require(proof==expected and all(type(proof[key]) is type(value) for key,value in expected.items()),
                'every exact typed functional and authority assertion is present in the native phase result')
        comparison = validate_comparison(work/(phase+'-catalog.json'))
        if phase=='reopen':
            require(inputs.read(work/'read-catalog.json',32*MIB)==inputs.read(work/'reopen-catalog.json',32*MIB),
                    'complete catalog and original metadata bytes survive native cold reopen')
        require(inputs.products(inputs.COMPILED/'build/out/Products',guard)==compiled['products'],
                'all compiler products unchanged after direct compiled selected method')
        result['phases'].append({'phase':phase,'method':METHOD,'status':'PASS','nativePID':native['pid'],
            'swiftPID':row['pid'],'logSHA256':row['logSHA256'],'phaseProofSHA256':digest(proof_path),
            'comparison':comparison,'actualTestStarts':started,'actualTestPasses':passed,'skipped':0,
            'allFunctionalPredicates':proof})
        budget(True);save()

    def run_phase(phase,config):
        nonlocal current_native, active_native_deadline
        budget(True)
        require(inputs.row(inputs.NATIVE,guard)['sha256']==inputs.BINARY_SHA and
                inputs.row(inputs.OFFLINE,guard)['sha256']==inputs.OFFLINE_SHA, 'exact native and OS wrapper immediately before spawn')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));port = listener.getsockname()[1]
        base = 'http://127.0.0.1:'+str(port)
        command = [sys.executable,'-B',str(inputs.OFFLINE),'--exec',str(inputs.NATIVE),'run',
                   '--config',str(config),'--data-dir',str(account_copy),'--addr','127.0.0.1:'+str(port)]
        env = {key:value for key,value in os.environ.items()
               if not key.startswith(('ANY_','PINKHA_')) and key not in {'LD_PRELOAD','LD_LIBRARY_PATH','TMPDIR','TMP','TEMP'}}
        env.update(ANY_DATA_DIR=str(account_copy),GOMAXPROCS='2',GOMEMLIMIT='2GiB',TMPDIR=str(OUTPUT/'native-temporary'))
        phase_began,index = time.monotonic(),len(result['nativeProcesses'])
        require(active_native_deadline is None, 'only one active native phase')
        active_native_deadline = phase_began+NATIVE_PHASE_SECONDS
        state = {'complete':False,'stopRequested':False,'stopAt':None}

        def request(route,timeout=5):
            guard()
            require(route.startswith('/v1/') and '\r' not in route and '\n' not in route, 'fixed ordinary native GET route')
            remaining = min(timeout,phase_began+NATIVE_PHASE_SECONDS-time.monotonic(),began+MAIN_SECONDS-time.monotonic())
            require(remaining>0, 'remaining complete native HTTP request budget')
            entry = {'phase':phase,'method':'GET','route':route,'status':None,'bodyBytes':None,'bodySHA256':None}
            result['requestLedger'].append(entry)
            require(len(result['requestLedger'])<=256, 'bounded readiness and native controller requests')
            with boundary.absolute_http_deadline(remaining):
                connection = http.client.HTTPConnection('127.0.0.1',port,timeout=remaining)
                try:
                    connection.request('GET',route,headers={'Connection':'close'})
                    response = connection.getresponse()
                    raw = response.read(MIB+1)
                    require(len(raw)<=MIB, 'bounded native controller response')
                    entry.update(status=response.status,bodyBytes=len(raw),bodySHA256=hashlib.sha256(raw).hexdigest())
                    require(response.status==200, 'ordinary native read returned expected HTTP200 without redirect')
                    value = json.loads(raw)
                finally:
                    connection.close()
            return value

        def service_observer():
            nonlocal current_native
            try:
                guard()
                if len(result['nativeProcesses'])<=index:
                    return None
                row = result['nativeProcesses'][index]
                if row.get('exitCode') is not None or row.get('processGroupAbsent') or 'pid' not in row:
                    return None
                if state['stopRequested']:
                    require(time.monotonic()-state['stopAt']<20, 'bounded native graceful shutdown')
                    return None
                pid = row['pid']
                require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None,
                        'native leader remains live and unreaped before the test')
                require(os.getpgid(pid)==os.getsid(pid)==pid, 'original owned native group and session')
                try:
                    request('/v1/health',1)
                except (ConnectionRefusedError,ConnectionResetError,TimeoutError,http.client.RemoteDisconnected):
                    require(time.monotonic()-phase_began<60, 'bounded native readiness')
                    return None
                # procfs reports a zero stat size for generated status content;
                # bound the actual read under the still-unreaped child identity.
                status_fd = os.open(Path('/proc')/str(pid)/'status',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
                with os.fdopen(status_fd,'rb') as stream:
                    status_raw = stream.read(65537)
                require(len(status_raw)<=65536 and
                        os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and
                        os.getpgid(pid)==os.getsid(pid)==pid, 'bounded status from the same live unreaped child')
                status = status_raw.decode()
                fields = dict(line.split(':',1) for line in status.splitlines() if ':' in line)
                require(fields['NoNewPrivs'].strip()=='1' and fields['Seccomp'].strip()=='2',
                        'actual new native PID inherited both OS denial controls')
                executable = Path(os.readlink(Path('/proc')/str(pid)/'exe'))
                require(executable==inputs.NATIVE and inputs.row(executable,guard)['sha256']==inputs.BINARY_SHA,
                        'actual native executable is the qualified physical custody target')
                account = request('/v1/account')['id']
                require(account==source_identity['accountID'], 'original retained account identity from normal native API')
                space = source_identity['spaceID']
                member = request('/v1/spaces/'+space+'/members/me')
                require(member['identity']==account and member['status']=='active' and member['permission']=='owner',
                        'current signed original owner admission')
                sync = request('/v1/spaces/'+space+'/sync-status')
                require(sync['networkPeers']==sync['localPeers']==sync['globalPeers']==0, 'no native network peers')
                row.update(phase=phase,outboundDeniedByOS=True,actualInheritedNoNewPrivileges=True,
                    actualInheritedSeccompFilter=True,actualExecutableSHA256=inputs.BINARY_SHA,
                    actualExecutablePath=str(inputs.NATIVE),networkPeers=0,currentOwnerConfirmed=True)
                persist(work/'runtime.json',{'baseURL':base,'accountID':account,'spaceID':space,
                    'binarySHA256':inputs.BINARY_SHA,'componentScope':'retained-original-catalog-metadata-v1',
                    'outboundDeniedByOS':True,'networkPeerCount':0,'processID':pid,'phase':phase})
                save()
                current_native = row
                try:
                    run_test(phase,row)
                finally:
                    current_native = None
                require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None and
                        os.getpgid(pid)==os.getsid(pid)==pid, 'same live unreaped native owner before normal shutdown')
                row['gracefulStopIntent'] = {'signal':int(signal.SIGTERM),'leaderUnreaped':True,'validatedPhase':phase}
                save()
                state.update(complete=True,stopRequested=True,stopAt=time.monotonic())
                os.killpg(pid,signal.SIGTERM)
                row['expectedServiceShutdown'] = True
                return None
            except BaseException as error:
                return type(error).__name__+': '+str(error)

        try:
            _,row = owner.run(logs/(phase+'-native'),command,OUTPUT,env,NATIVE_PHASE_SECONDS,
                              service_observer,persist,digest,result['nativeProcesses'])
        finally:
            # The unchanged owner has completed its cleanup/absence path before
            # this phase bound can be released, including on an inner failure.
            active_native_deadline = None
        require(state['complete'] and state['stopRequested'] and normal_command(row),
                'native phase completed and original owned group closed normally')
        require(row.get('expectedServiceShutdown') is True and row['gracefulStopIntent']['validatedPhase']==phase,
                'one graceful live-owner signal after full functional phase acceptance')
        budget(True);save()

    def interrupted(*_):
        raise RuntimeError('owned native catalog controller interrupted')

    for number in STOP_SIGNALS:
        signal.signal(number,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,STOP_SIGNALS)
    try:
        guard()
        require(shutil.disk_usage('/').free>ROOT_FLOOR+ROOT_ADMISSION_RESERVE, 'unchanged original native root admission reserve')
        require(shutil.disk_usage(PARENT).free>DEVELOPMENT_FLOOR+OWNED_CAP+DEVELOPMENT_RESERVE,
                'complete new finite runtime development reservation')
        result['initialMemoryAvailableBytes'] = memory_available()
        require(result['initialMemoryAvailableBytes']>=3*GIB, 'native and selected Swift runtime memory admission')
        require(not os.path.lexists(OUTPUT), 'exclusive new runtime evidence namespace')
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
        try:
            OUTPUT.mkdir(mode=0o700);owned_output = True
            os.chmod(OUTPUT,0o700)
            fsync_directory(OUTPUT);fsync_directory(PARENT)
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
        result['ownedOutputCreated'] = True
        save()
        for path in (work,logs,runtime_support,OUTPUT/'native-temporary'):
            path.mkdir(mode=0o700);os.chmod(path,0o700)
        for name in ('temporary','module-cache','clang-module-cache','cache','config','security'):
            path = runtime_support/name;path.mkdir(mode=0o700);os.chmod(path,0o700)
        for name,wanted in CONTROL_PINS.items():
            raw = read_control(HERE/name)
            require(hashlib.sha256(raw).hexdigest()==wanted, 'all declared complete runtime helper bytes')
            control_before[str(HERE/name)] = {'bytes':len(raw),'sha256':wanted}
        raw_self = read_control(Path(__file__).absolute())
        control_before[str(Path(__file__).absolute())] = {'bytes':len(raw_self),'sha256':hashlib.sha256(raw_self).hexdigest()}
        result['controllerSources'] = control_before
        owner,lifecycle = boundary.qualify()
        owner.install_interrupt_handlers()
        result['reusedLifecycleAndDeadlineControls'] = lifecycle
        prior = inputs.json_pin(PARENT/'runtime-attempt1/result.json',PRIOR_RUNTIME_SHA,guard,admitted)
        require(prior['status']=='FAIL_NATIVE_CATALOG_READ_REOPEN_PRESERVED' and
                prior['errors']==[{'boundary':'main','message':'no followed output alias','type':'RuntimeError'}] and
                prior['completionErrors']==[] and prior['startedOwnedGroups']==0 and
                prior['allStartedOwnedGroupsPositivelyAbsent'] is False and
                prior['metadataCommands']==prior['nativeProcesses']==prior['swiftLaunches']==prior['phases']==prior['requestLedger']==[] and
                prior['compilerInvocations']==prior['originalAccountsInitialized']==prior['newAccountsCreated']==0 and
                'originalAccountInventorySHA256' not in prior and
                prior['compiledProducerReceiptSHA256']==COMPILED_RECEIPT_SHA and
                prior['finalIntegrity']=={key:True for key in ['allAdmittedInputsAndModes',
                    'completeCompilerInputsProductsAndModes','controllerAndLifecycle','nativeSourceAndPhysicalCustody',
                    'originalRetainedAccount','ownedCommandClosure','resources']},
                'exact original zero-group alias refusal stays failed with its original false aggregate')
        require(prior['controllerSources'][str(PARENT/'runtime-prepared1/run_native_catalog.py')]['sha256']==PRIOR_CONTROLLER_SHA,
                'original failed controller identity')
        for name,wanted in prior['controllerSources'].items():
            require(inputs.pin(Path(name),wanted['sha256'],guard,admitted)==wanted,
                    'every original failed runtime control stays byte-identical')
        result['preservedPriorFailure'] = {'path':str(PARENT/'runtime-attempt1/result.json'),
            'sha256':PRIOR_RUNTIME_SHA,'controllerSHA256':PRIOR_CONTROLLER_SHA,
            'status':prior['status'],'startedOwnedGroups':0,'actualTests':0,'accountCopyCreated':False,
            'originalAggregateAbsence':False,'replayedMethods':0}
        prior_skip = inputs.json_pin(PARENT/'runtime-attempt2/result.json',PRIOR_SKIP_BUILD_SHA,guard,admitted)
        old_rows = prior_skip['metadataCommands']+prior_skip['nativeProcesses']+prior_skip['swiftLaunches']
        require(prior_skip['status']=='FAIL_NATIVE_CATALOG_READ_REOPEN_PRESERVED' and
                prior_skip['errors']==[{'boundary':'main','message':'RuntimeError: RuntimeError: exact observed compiler-only SPM alias metadata and text','type':'RuntimeError'}] and
                len(prior_skip['completionErrors'])==6 and
                prior_skip['finalIntegrity']=={'allAdmittedInputsAndModes':False,'completeCompilerInputsProductsAndModes':False,
                    'controllerAndLifecycle':True,'nativeSourceAndPhysicalCustody':False,'originalRetainedAccount':False,
                    'ownedCommandClosure':False,'resources':False} and
                [len(prior_skip[key]) for key in ('metadataCommands','nativeProcesses','swiftLaunches')]==[1,1,1] and
                prior_skip['startedOwnedGroups']==3 and prior_skip['allStartedOwnedGroupsPositivelyAbsent'] is True and
                [row['exitCode'] for row in old_rows]==[0,0,-15] and
                [row['forcedCleanup'] for row in old_rows]==[False,True,True] and
                [row['signals'] for row in old_rows]==[[],[15],[15]] and
                all(row['processGroupAbsent'] is True and row['cleanupErrors']==[] for row in old_rows) and
                prior_skip['phases']==[] and prior_skip['compilerInvocations']==prior_skip['domainWriteOperationsRequested']==0 and
                prior_skip['originalAccountCopyPortableMetadataAndBytesEqual'] is True and
                prior_skip['compilerBuildAliasBefore']['link']==ORIGINAL_SPM_ALIAS and
                prior_skip['controllerSources'][str(PARENT/'runtime-prepared2/run_native_catalog.py')]['sha256']==PRIOR_SKIP_BUILD_CONTROLLER_SHA,
                'exact second failed runtime, abnormal cleanup and failed final audits remain historical')
        for name,wanted in prior_skip['controllerSources'].items():
            require(inputs.pin(Path(name),wanted['sha256'],guard,admitted)==wanted,
                    'every second failed runtime control stays byte-identical')
        prior_log = PARENT/'runtime-attempt2/private-logs/read-swift/original.log'
        inputs.pin(prior_log,'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',guard,admitted,65536)
        require(inputs.read(prior_log,65536)==b'', 'second attempt retains its zero-byte log without invented functional acceptance')
        result['preservedPriorSkipBuildFailure'] = {'path':str(PARENT/'runtime-attempt2/result.json'),
            'sha256':PRIOR_SKIP_BUILD_SHA,'controllerSHA256':PRIOR_SKIP_BUILD_CONTROLLER_SHA,
            'status':prior_skip['status'],'startedOwnedGroups':3,'forcedCleanupGroups':2,
            'allStartedOwnedGroupsPositivelyAbsent':True,'loggedTestEvents':0,'completedFunctionalPhases':0,
            'accountCopyCreatedAndPreserved':True,'originalFinalIntegrity':prior_skip['finalIntegrity'],
            'failureReclassified':False,'historicalPIDsProbed':False}
        compiled = inputs.compiler(COMPILED_RECEIPT_SHA,COMPILER_SHA,MANIFEST_SHA,guard,admitted)
        custody = inputs.json_pin(HERE/'post-skip-build-custody.json',CUSTODY_SHA,guard,admitted,256*1024)
        require(custody['status']=='PASS_CURRENT_SOURCE_AND_PRODUCTS_CUSTODY_ONLY_NOT_RUNTIME_ACCEPTANCE' and
                custody['compiledProducerReceiptSHA256']==COMPILED_RECEIPT_SHA and
                custody['preservedFailedRuntimeSHA256']==PRIOR_SKIP_BUILD_SHA and
                custody['preservedFailedControllerSHA256']==PRIOR_SKIP_BUILD_CONTROLLER_SHA and
                custody['historicalFailureReclassified'] is False and custody['newRuntimeAcceptance'] is False and
                custody['historicalFinalIntegrity']==prior_skip['finalIntegrity'] and
                custody['originalCompilerAlias']==prior_skip['compilerBuildAliasBefore'] and
                custody['observedCompilerAlias']['link']==SPM_ALIAS and
                custody['onlyAliasIdentityFieldChanged']=='link.mtimeNS' and
                custody['aliasInodeAndTargetTextUnchanged'] is True and
                custody['freshOriginalAndCopiedInputsRechecked'] is True and
                custody['freshCompleteProductsAndModesEqualOriginalProducer'] is True and
                custody['compiledProducts']==compiled['products'] and
                custody['compiledSourceInputs']==compiled['receipt']['compiledSourceInputs'],
                'new post-failure custody keeps the exact original source/products and an explicit changed alias timestamp')
        for path,wanted in ((ENTRY_POINT,ENTRY_POINT_SHA),(OUTPUT_FILE_MAP,OUTPUT_FILE_MAP_SHA),
                            (XCTEST_LIBRARY,XCTEST_LIBRARY_SHA)):
            inputs.pin(path,wanted,guard,admitted)
        require(custody['generatedEntryPoint']['sha256']==ENTRY_POINT_SHA and
                custody['generatedOutputFileMap']['sha256']==OUTPUT_FILE_MAP_SHA and
                custody['currentXCTestLibrary']['sha256']==XCTEST_LIBRARY_SHA,
                'captured generated entry and current linked XCTest runtime')
        result['postFailureCompilerCustody'] = {'path':str(HERE/'post-skip-build-custody.json'),
            'sha256':CUSTODY_SHA,'preservedFailureSHA256':PRIOR_SKIP_BUILD_SHA,
            'fullSourceAndProductsFreshlyMatched':True,'oldAliasTimestampRetainedAsHistorical':True,
            'currentAliasTimestampPinnedBeforeAndAfter':True,'historicalFailureReclassified':False}
        compiler_alias_before = compiler_build_alias()
        require(compiler_alias_before==custody['observedCompilerAlias'],
                'exact complete recaptured alias and physical target identity')
        require(compiled['products']['directories'][compiler_alias_before['physicalTarget']]==compiler_alias_before['targetMode'],
                'alias target mode joins the complete producer Products inventory')
        result['compilerBuildAliasBefore'] = compiler_alias_before
        result['compilerBuildAliasAccounting'] = {'followed':False,'linkInodeOnly':True,
            'runtimeOutputAliasesAllowed':False,'observationScope':'one compiler-build/debug member only'}
        build_allocation_before = allocated(inputs.COMPILED/'build',compiler_alias_before)
        result['compilerBuildAllocatedBytesBeforeRuntime'] = build_allocation_before
        result['compiledSourceInputs'] = compiled['receipt']['compiledSourceInputs']
        result['compiledTestRunner'] = compiled['products']['testRunner']
        result['compiledProductFiles'] = len(compiled['products']['files'])
        result['nativeAdmission'] = inputs.native(guard,admitted)
        source_identity = inputs.original_receipts(guard,admitted)
        result['retainedPolicyReceiptSHA256'] = source_identity['retainedPolicyReceiptSHA256']
        result['oldProofMethodsReexecuted'] = source_identity['oldProofMethodsReexecuted']
        path,row = owner.run(logs/'metadata-swift-version',[compiled['driver'],'--version'],OUTPUT,
                              dict(os.environ),10,observe,persist,digest,result['metadataCommands'])
        require(normal_command(row) and 'Swift version 6.4.3' in inputs.read(path,65536).decode(),
                'actual original Swift driver metadata command')
        list_environment = {key:value for key,value in os.environ.items()
                            if not key.startswith(('PINKHA_','ANY_','SWIFT_')) and key not in
                            {'TMPDIR','TMP','TEMP','SDKROOT','LD_PRELOAD','LD_LIBRARY_PATH','DYLD_LIBRARY_PATH'}}
        list_environment.update(TMPDIR=str(runtime_support/'temporary'),
            SWIFT_MODULECACHE_PATH=str(runtime_support/'module-cache'),
            CLANG_MODULE_CACHE_PATH=str(runtime_support/'clang-module-cache'))
        require(not account_copy.exists(), 'list-only qualification must precede any original account copy')
        path,row = owner.run(logs/'metadata-xctest-list',
            [compiled['products']['testRunner']['path'],'--list-tests'],Path(compiled['package']),
            list_environment,20,observe,persist,digest,result['metadataCommands'])
        require(normal_command(row), 'direct physical XCTest list command closes normally')
        listing = inputs.read(path,65536).decode()
        listed_lines = [line for line in listing.splitlines() if line]
        require(len(listed_lines)==5 and re.fullmatch(r'Listing 4 tests in [^\r\n]{1,1024}:',listed_lines[0]) and
                listed_lines[1:]==DIRECT_TEST_NAMES and not re.search(r"Test (?:Case|Suite) '[^']+' (?:started|passed|failed|skipped)|Executed [0-9]+ tests?",listing),
                'exact four compiled names listed with zero test execution events')
        require(not account_copy.exists() and
                inputs.products(inputs.COMPILED/'build/out/Products',guard)==compiled['products'] and
                compiler_build_alias()==compiler_alias_before,
                'list-only command leaves account absent and complete compiler products/alias unchanged')
        row.update(invocation='direct-compiled-XCTest-list-only',listedMethods=DIRECT_TEST_NAMES,
                   actualTestEvents=0,accountCopyExisted=False)
        result['actualListedXCTestNames'] = DIRECT_TEST_NAMES
        result['directRunnerListBeforeAccountCopy'] = True
        budget(True);save()
        result['currentOriginalAccountUsersBeforeCopy'] = inputs.no_account_users(inputs.ORIGINAL_ACCOUNT,guard)
        account_before = inputs.account_inventory(inputs.ORIGINAL_ACCOUNT,guard)
        persist(OUTPUT/'private-original-account-inventory.json',account_before)
        result['originalAccountInventorySHA256'] = digest(OUTPUT/'private-original-account-inventory.json')
        result['sourceAccountCopyRoundedUpperBytes'] = inputs.copy_account(inputs.ORIGINAL_ACCOUNT,account_copy,account_before,guard)
        result['originalAccountCopyPortableMetadataAndBytesEqual'] = True
        result['currentOriginalAccountUsersAfterCopy'] = inputs.no_account_users(inputs.ORIGINAL_ACCOUNT,guard)
        original_config = account_copy/'config.yaml'
        wanted_config = ('network:\n  nodeconfPath: /Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/source/internal/config/nodeconf-prod.yml\n'
                         'index:\n  embedder: none\np2p:\n  enabled: false\n')
        raw_config = inputs.read(original_config,65536)
        require(raw_config.decode()==wanted_config, 'exact original retained native configuration')
        updated_config = raw_config.decode().replace('/Users/m1/development/anytype-root-active-20261125/t2-fixed-permission-20261126/build-attempt3/current/source/internal/config/nodeconf-prod.yml',str(inputs.CONFIG))
        config = OUTPUT/'owned-config.yml'
        fd = os.open(config,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        with os.fdopen(fd,'w') as stream:
            stream.write(updated_config);stream.flush();os.fsync(stream.fileno())
        require(inputs.read(original_config,65536)==raw_config, 'original copied configuration remains intact')
        result['configurationChange'] = 'one owned config file uses the exact qualified physical nodeconf path; original account config unchanged'
        persist(OUTPUT/'admitted-inputs.json',admitted)
        result['admittedInputs'] = {'path':str(OUTPUT/'admitted-inputs.json'),**inputs.row(OUTPUT/'admitted-inputs.json',guard)}
        budget(True);save()
        run_phase('read',config)
        require(len(result['nativeProcesses'])==1 and normal_command(result['nativeProcesses'][0]),
                'first native process positively closed before cold reopen')
        run_phase('reopen',config)
        require(len(result['metadataCommands'])==2 and len(result['nativeProcesses'])==len(result['swiftLaunches'])==2,
                'two metadata plus two native plus two selected direct XCTest groups')
        require([entry['phase'] for entry in result['phases']]==['read','reopen'] and
                result['nativeProcesses'][0]['pid']!=result['nativeProcesses'][1]['pid'], 'two actual fresh native PIDs and ordered phases')
        require(all(normal_command(row) for row in result['metadataCommands']+result['nativeProcesses']+result['swiftLaunches']),
                'all six started groups completed normally with positive absence')
        result['status'] = 'PASS_ORIGINAL_CATALOG159_METADATA11_SIGNED_READ_AND_COLD_REOPEN'
        result['actualNativeCatalogRowsPerPhase'] = 159
        result['actualOriginalSnapshotPairsPerPhase'] = 156
        result['actualUncapturedHeadsPerPhase'] = 3
        result['actualMethodInvocations'] = 2
        result['distinctNewMethods'] = 1
        result['coldReadbackComparisonEqual'] = True
    except BaseException as error:
        record_failure('main',error)
    finally:
        for number in STOP_SIGNALS:
            signal.signal(number,signal.SIG_IGN)
        rows = result['metadataCommands']+result['nativeProcesses']+result['swiftLaunches']
        result['allStartedOwnedGroupsPositivelyAbsent'] = bool(rows) and all(row.get('processGroupAbsent') is True for row in rows)
        result['startedOwnedGroups'] = len([row for row in rows if 'pid' in row])
        final_deadline = time.monotonic()+FINAL_SECONDS

        def finish(name,operation):
            try:
                operation();result['finalIntegrity'][name] = True
            except BaseException as error:
                result['finalIntegrity'][name] = False
                record_failure(name,error,True)

        def final_controls():
            for name,wanted in control_before.items():
                raw = read_control(Path(name))
                require({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}==wanted, 'every complete controller source unchanged')
            if lifecycle is not None:
                boundary.recheck(lifecycle)

        def final_account():
            if account_before is not None:
                require(inputs.account_inventory(inputs.ORIGINAL_ACCOUNT,guard)==account_before,
                        'original retained account bytes identities and portable metadata unchanged')
                result['currentOriginalAccountUsersAtCompletion'] = inputs.no_account_users(inputs.ORIGINAL_ACCOUNT,guard)

        def final_compiler():
            if compiled is not None:
                refreshed = inputs.compiler(COMPILED_RECEIPT_SHA,COMPILER_SHA,MANIFEST_SHA,guard,{})
                require(refreshed==compiled, 'full original/copy/source/Products/alias admission unchanged at completion')
            if compiler_alias_before is not None:
                alias_after = compiler_build_alias()
                require(alias_after==compiler_alias_before, 'exact compiler alias and physical target identity before and after')
                result['compilerBuildAliasAfter'] = alias_after

        def final_native():
            if 'nativeAdmission' in result:
                require(inputs.native(guard,{})==result['nativeAdmission'], 'complete native source and exact physical custody unchanged')

        def final_groups():
            require(not rows or result['allStartedOwnedGroupsPositivelyAbsent'], 'every actually started owned group is positively absent')
            require(all(normal_command(row) for row in rows), 'no forced cleanup or abnormal command can pass')
            if result['status'].startswith('PASS_'):
                require(len(rows)==6 and len(result['phases'])==2 and all(row['status']=='PASS' for row in result['phases']),
                        'all six normal groups and two actual completed phase proofs')

        finish('controllerAndLifecycle',final_controls)
        finish('originalRetainedAccount',final_account)
        finish('completeCompilerInputsProductsAndModes',final_compiler)
        finish('nativeSourceAndPhysicalCustody',final_native)
        finish('allAdmittedInputsAndModes',lambda:inputs.recheck(admitted,guard))
        finish('ownedCommandClosure',final_groups)
        finish('resources',lambda:budget(True))
        if owned_output:
            try:
                result['freeAfter'] = {'root':shutil.disk_usage('/').free,'development':shutil.disk_usage(PARENT).free}
                result['ownedOutputAllocatedBytesAtCompletion'] = allocated(OUTPUT)
            except BaseException as error:
                record_failure('finalResourceObservation',error,True)
            try:
                save()
                raw = inputs.read(OUTPUT/'result.json',8*MIB)
                require(json.loads(raw)==result, 'full final result readback')
            except BaseException as error:
                record_failure('finalResultPersistence',error,True)
                try:
                    persist(OUTPUT/'result.json',result)
                except BaseException:
                    pass
    summary = {key:result[key] for key in ['status','scope','errors','completionErrors','allStartedOwnedGroupsPositivelyAbsent','startedOwnedGroups']}
    summary['ownedOutputCreated'] = owned_output
    if owned_output and (OUTPUT/'result.json').exists():
        try:
            summary['receipt'] = {'path':str(OUTPUT/'result.json'),**inputs.row(OUTPUT/'result.json',lambda:None,8*MIB)}
        except BaseException:
            summary['receiptReadbackFailed'] = True
    print(json.dumps(summary,sort_keys=True))
    return 0 if result['status'].startswith('PASS_') and not result['errors'] and not result['completionErrors'] else 1


if __name__=='__main__':
    raise SystemExit(main())
