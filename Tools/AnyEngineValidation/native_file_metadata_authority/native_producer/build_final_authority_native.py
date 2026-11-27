#!/usr/bin/env python3
"""Build one final standalone Any from actual-qualified public Files sources.

Requires the separately completed final34 receipt. No account initialization,
native server, API call, source-test replay, or private-store input is permitted.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import sys
import time

sys.dont_write_bytecode = True
MIB = 1024**2
GIB = 1024**3
HERE = Path(__file__).absolute().parent
ROOT = Path('/var/lib/pinkha-c-filesv2-20261126')
TEMP_PARENT = Path('/mnt/development/projects/caches/pinkha-w1-final-files-authority-native-20261127')
CACHE = Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET = Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
ADMISSION = HERE/'final_product_admission.py'
ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'
HELPER = HERE/'owned_swift_commands.py'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
ROOT_FLOOR, DEV_FLOOR = 2*GIB, 512*MIB
ROOT_CAP, TEMP_CAP, CACHE_GROWTH_CAP, LOG_CAP = 128*MIB, 256*MIB, 128*MIB, 8*MIB


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def identity(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def physical(path, directory=False):
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'physical public path required')
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'ordinary public path kind')
    return info


def frozen(path, maximum=8*MIB):
    before = physical(path)
    require(0<=before.st_size<=maximum, 'bounded public file')
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd,'rb') as stream:
        require(os.fstat(stream.fileno())==before,'public input identity before read')
        raw = stream.read(maximum+1)
        require(os.fstat(stream.fileno())==before,'public input changed during read')
    require(path.lstat()==before and len(raw)==before.st_size,'public input changed after read')
    return raw


def new_file(path, raw, mode=0o600):
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def inventory(root, check):
    physical(root,True)
    found = {}; stack = [root]; count = 0
    while stack:
        check()
        directory = stack.pop()
        fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        try:
            with os.scandir(fd) as entries: names = sorted(entry.name for entry in entries)
        finally: os.close(fd)
        for name in names:
            check()
            path = directory/name; info = path.lstat(); count += 1
            require(count<=10000 and not stat.S_ISLNK(info.st_mode),'bounded physical public source tree')
            if stat.S_ISDIR(info.st_mode): stack.append(path)
            else:
                require(stat.S_ISREG(info.st_mode),'regular public source member')
                found[path.relative_to(root).as_posix()] = identity(frozen(path,128*MIB))
    return found


def allocation(root, mutable=False, maximum_entries=50000):
    """Only current compiler temp/cache may have entries disappear during census."""
    physical(root,True)
    used = 0; count = 0; stack = [root]; began = time.monotonic(); seen = set()
    while stack:
        directory = stack.pop()
        try: fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        except FileNotFoundError:
            if mutable: continue
            raise
        try:
            with os.scandir(fd) as entries: names = [entry.name for entry in entries]
        finally: os.close(fd)
        for name in [None]+names:
            path = directory if name is None else directory/name
            try: info = path.lstat()
            except FileNotFoundError:
                if mutable: continue
                raise
            require(not stat.S_ISLNK(info.st_mode),'allocation tree alias')
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),'ordinary allocation member')
            key = (info.st_dev,info.st_ino)
            if key not in seen:
                used += max(info.st_size,info.st_blocks*512) if stat.S_ISREG(info.st_mode) else info.st_blocks*512
                seen.add(key)
            if name is not None and stat.S_ISDIR(info.st_mode): stack.append(path)
            if name=='original.log': require(info.st_size<=LOG_CAP,'bounded original command log')
            count += 1
            require(count<=maximum_entries and time.monotonic()-began<8,'bounded allocation census')
    return used


def main():
    require(not sys.flags.optimize,'assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--final-qualification',type=Path,required=True)
    parser.add_argument('--final-qualification-sha256',required=True)
    args = parser.parse_args()
    require(os.geteuid()==0 and os.uname().nodename=='torah-social','authorized Oracle host')
    output = args.output
    require(output.parent==ROOT and re.fullmatch(r'final-authority-native[1-9][0-9]{0,2}',output.name),'exclusive final producer output')
    os.umask(0o077)
    physical(ROOT,True); physical(TEMP_PARENT.parent,True)
    output.mkdir(mode=0o700,exist_ok=False)
    receipt = output/'result.json'; new_file(receipt,b'{}\n')
    temporary = TEMP_PARENT/output.name
    began = time.monotonic(); serial = 0; final_deadline = None
    admitted = {}; joined = None; expected = None; cache_before = None; temporary_created = False
    result = {'protocol':'pinkha-final-files-authority-native-qualified-v1','status':'RUNNING',
        'nativeAccountProcesses':0,'retainedPrivateInputs':0,'replayedTests':0,'nativeCLIStarted':False,
        'appleRuntimeQualified':False,'heartProductEmbedded':False,'productionOverlayApplications':0,
        'processes':[],'errors':[],'completionErrors':[],
        'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR,
            'rootAdmissionReserveBytes':ROOT_CAP,'developmentAdmissionReserveBytes':TEMP_CAP+CACHE_GROWTH_CAP,
            'rootOutputCapBytes':ROOT_CAP,'developmentTemporaryCapBytes':TEMP_CAP,
            'sharedCacheGrowthCapBytes':CACHE_GROWTH_CAP,'controllerSeconds':480,'buildSeconds':360,
            'metadataCommandSeconds':15,'finalVerificationSeconds':60,'requiredOuterSeconds':570,
            'workers':2,'goMemoryLimit':'1GiB','allocationEstimateNotMeasuredPeak':True,
            'estimateBasis':'Prior actual e265 native build measured root99852288/temp182853632/cache111902720 B within the same128/256/128MiB caps. Final source adds nine files and replaces four, with one unchanged build command. Fresh floors and measured caps apply; no cache deletion.'}}

    def save_json(path,value):
        nonlocal serial
        require(path.is_relative_to(output),'owned receipt destination')
        serial += 1
        raw = (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
        require(len(raw)<=8*MIB,'bounded public receipt')
        stage = path.with_name(path.name+'.next-'+str(serial))
        new_file(stage,raw); os.replace(stage,path)
        fd = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: os.fsync(fd)
        finally: os.close(fd)

    def save():
        result['seconds'] = time.monotonic()-began; save_json(receipt,result)

    def pin(path,digest,maximum=8*MIB):
        checkpoint()
        raw = frozen(path,maximum)
        require(identity(raw)['sha256']==digest,'public source/receipt hash mismatch')
        admitted[str(path)] = {'identity':identity(raw),'maximum':maximum}
        return raw

    def checkpoint(admit=False):
        if final_deadline is None:
            require(time.monotonic()-began<480,'bounded final producer deadline')
        else:
            require(time.monotonic()<final_deadline,'bounded final source/product verification')
        require(not (output/'abort').exists(),'owned abort')
        values = {'root':shutil.disk_usage('/').free,'development':shutil.disk_usage('/mnt/development').free}
        for name,floor,reserve in [('root',ROOT_FLOOR,ROOT_CAP),('development',DEV_FLOOR,TEMP_CAP+CACHE_GROWTH_CAP)]:
            require(values[name]>=floor+(reserve if admit else 0),name+' unchanged storage gate')
            result.setdefault('minimumFreeBytes',{})[name] = min(values[name],result.get('minimumFreeBytes',{}).get(name,values[name]))
        return values

    def guard(admit=False):
        values = checkpoint(admit)
        used = allocation(output,maximum_entries=12000)
        require(used<=ROOT_CAP,'entire root producer output cap')
        result['peakRootOutputBytes'] = max(used,result.get('peakRootOutputBytes',0))
        if temporary_created:
            used = allocation(temporary,mutable=True)
            require(used<=TEMP_CAP,'owned compiler temporary cap')
            result['peakTemporaryBytes'] = max(used,result.get('peakTemporaryBytes',0))
        if cache_before is not None:
            require(CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET,'same qualified cache placement')
            used = max(0,allocation(CACHE_TARGET,mutable=True)-cache_before)
            require(used<=CACHE_GROWTH_CAP,'measured shared-cache growth cap')
            result['peakObservedSharedCacheGrowthBytes'] = max(used,result.get('peakObservedSharedCacheGrowthBytes',0))
        checkpoint()
        return values

    def observe():
        try: guard(); return None
        except BaseException as error: return type(error).__name__+': '+str(error)

    def command(label,argv,cwd,env,seconds):
        def persist(path,value):
            require(path.parent==output/label and path.name in ('started.json','result.json'),'owned command receipt')
            save_json(path,value); save()
        log,row = owned.run(output/label,argv,cwd,env,seconds,observe,persist,
            lambda path:identity(frozen(path,LOG_CAP))['sha256'],result['processes'])
        save(); return log,row

    def interrupted(number,_frame):
        raise RuntimeError('final producer interrupted by signal '+str(number))
    for number in (signal.SIGTERM,signal.SIGINT): signal.signal(number,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})

    try:
        result['initialFreeBytes'] = guard(True)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
        require(available>=3*GIB,'native producer memory admission')
        result['memAvailableBefore'] = available
        own = Path(__file__).absolute(); raw = frozen(own)
        admitted[str(own)] = {'identity':identity(raw),'maximum':8*MIB}; result['controller'] = identity(raw)
        result['admissionModule'] = identity(pin(ADMISSION,ADMISSION_SHA))
        spec = importlib.util.spec_from_file_location('final_files_product_admission',ADMISSION)
        admission = importlib.util.module_from_spec(spec); spec.loader.exec_module(admission)
        pin(HELPER,HELPER_SHA)
        proof = admission.object_json(pin(HELPER_PROOF,HELPER_PROOF_SHA))
        require(proof['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and proof['helperSHA256']==HELPER_SHA and proof['allOwnedGroupsPositivelyAbsent'],'actual lifecycle proof reuse')
        require(len(proof['methods'])==5 and all(row['status']=='PASS' for row in proof['methods']),'five prior lifecycle controls')
        spec = importlib.util.spec_from_file_location('final_files_native_owned',HELPER)
        owned = importlib.util.module_from_spec(spec); spec.loader.exec_module(owned)
        result['reusedOwnershipReceiptSHA256'] = HELPER_PROOF_SHA
        require(CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET,'qualified cache alias')
        physical(CACHE_TARGET,True); cache_before = allocation(CACHE_TARGET,mutable=True)
        require(output.stat().st_dev!=CACHE_TARGET.stat().st_dev,'explicit two-filesystem layout')
        result['sharedCacheAllocationBefore'] = cache_before
        joined = admission.qualified_union(pin,inventory,args.final_qualification,args.final_qualification_sha256,checkpoint)
        expected = joined['files']
        result.update(baseNativeReceiptSHA256=admission.BASE_RECEIPT_SHA,baseSourceManifestSHA256=admission.BASE_MANIFEST_SHA,
            finalCandidateSHA256=admission.CANDIDATE_SHA,finalPatchSHA256=admission.PATCH_SHA,
            commits=admission.COMMITS,syncModule=admission.SYNC_MODULE,qualification=joined['qualificationReference'])
        result['reusedActualReceipts'] = joined['qualification']['reusedActualReceipts']
        result['actualScopesFromQualification'] = joined['qualification']['actualScopes']
        base_binary = identity(pin(admission.BASE/'any',admission.BASE_BINARY_SHA,128*MIB))
        require(sum(row['bytes'] for row in expected.values())+base_binary['bytes']<=ROOT_CAP-8*MIB,'source and prior binary leave root output reserve')
        result['measuredBaseAllocationInputs'] = {'sourceLogicalBytes':sum(row['bytes'] for row in expected.values()),'priorNativeBinary':base_binary,'additionalReserveBytes':8*MIB}
        source = output/'source'; source.mkdir(mode=0o700)
        for index,(name,wanted) in enumerate(sorted(expected.items())):
            checkpoint(); admission.relative(name)
            if index%64==0: guard()
            original = joined['qualifiedSDKSource']/name.removeprefix(admission.SDK_PREFIX) if name.startswith(admission.SDK_PREFIX) else admission.BASE/'source'/name
            raw = frozen(original,128*MIB); require(identity(raw)==wanted,'exact qualified public source copy')
            target = source/name; target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            new_file(target,raw,stat.S_IMODE(original.lstat().st_mode))
        require(inventory(source,checkpoint)==expected,'full1616 source after copy')
        result['productionOverlayApplications'] = 1; result['sourceChanges'] = joined['changedPaths']
        save_json(output/'source-manifest.json',{'protocol':'pinkha-final-files-authority-native-source-v1',
            'baseSourceManifestSHA256':admission.BASE_MANIFEST_SHA,'finalCandidateSHA256':admission.CANDIDATE_SHA,
            'finalPatchSHA256':admission.PATCH_SHA,'files':expected})
        result['sourceManifestSHA256'] = identity(frozen(output/'source-manifest.json'))['sha256']
        result['sourceFiles'] = len(expected); result['sdkSourceFiles'] = len(joined['sdkFiles'])
        if not TEMP_PARENT.exists(): TEMP_PARENT.mkdir(mode=0o700)
        physical(TEMP_PARENT,True); temporary.mkdir(mode=0o700,exist_ok=False); temporary_created = True
        require(physical(temporary,True).st_dev==CACHE_TARGET.stat().st_dev,'development compiler temporary placement')
        env = {key:value for key,value in os.environ.items() if not key.startswith(('ANY_','PINKHA_','PYTHON','CGO_','GO'))}
        env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE=str(CACHE),GOMODCACHE='/root/go/pkg/mod',
            GOTMPDIR=str(temporary),TMPDIR=str(temporary),CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
        known_go = joined['qualification']['goToolchain']
        driver = Path(known_go['driver']['path'])
        require(identity(pin(driver,known_go['driver']['sha256'],128*MIB))=={key:known_go['driver'][key] for key in ('bytes','sha256')},'same actual Go driver bytes')
        for row in known_go['tools'].values():
            require(identity(pin(Path(row['path']),row['sha256'],128*MIB))=={key:row[key] for key in ('bytes','sha256')},'same qualified compiler/linker bytes')
        metadata_log,_ = command('toolchain',[str(driver),'env','-json','GOVERSION','GOROOT','GOTOOLDIR','GOHOSTOS','GOHOSTARCH','GOOS','GOARCH'],source,env,15)
        metadata = admission.object_json(frozen(metadata_log,65536))
        require(metadata==known_go['metadata'] and metadata['GOOS']==metadata['GOHOSTOS']=='linux' and metadata['GOARCH']==metadata['GOHOSTARCH']=='arm64','same actual final34 Linux toolchain')
        result['goToolchain'] = known_go
        result['environment'] = {key:env[key] for key in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB')}
        binary = output/'any'
        _,build = command('native-build',[str(driver),'build','-p','2','-o',str(binary),'./cmd/any'],source,env,360)
        result['buildExitCode'] = build['exitCode']
        raw = frozen(binary,128*MIB)
        require(raw.startswith(b'\x7fELF') and physical(binary).st_mode&0o111,'new executable ELF product')
        result['binarySHA256'] = identity(raw)['sha256']; result['binaryBytes'] = len(raw)
        admitted[str(binary)] = {'identity':identity(raw),'maximum':128*MIB}
        module_log,_ = command('binary-module-metadata',[str(driver),'version','-m',str(binary)],source,env,15)
        module = frozen(module_log,65536).decode()
        require('github.com/anyproto/any/cmd/any' in module and 'github.com/anyproto/anytype-heart' not in module,'standalone Any without Heart binding')
        require('\tdep\tgithub.com/anyproto/any-sync\tv0.13.8\t' in module and metadata['GOVERSION'] in module,'actual Sync and Go versions')
        require('\tdep\tgithub.com/anyproto/any-sync-sdk\t' in module and '.runtime-artifacts/sdk-source' in module,'actual local final SDK replacement')
        result['binaryModuleMetadata'] = identity(module.encode())
        require(inventory(source,checkpoint)==expected,'source unchanged after actual build')
        result['status'] = 'PASS_FINAL_NATIVE_BUILD_AND_FILES_AUTHORITY34'
    except BaseException as error:
        result['status'] = 'FAIL_FINAL_NATIVE_BUILD_PRESERVED'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in (signal.SIGTERM,signal.SIGINT): signal.signal(number,signal.SIG_IGN)
        result['allOwnedGroupsPositivelyAbsent'] = all(row.get('processGroupAbsent') for row in result['processes'])
        final_deadline = time.monotonic()+60
        try:
            for name,wanted in admitted.items():
                checkpoint()
                require(identity(frozen(Path(name),wanted['maximum']))==wanted['identity'],'admitted public input/product changed')
            result['admittedPublicInputsUnchanged'] = True
            if joined is not None:
                require(inventory(admission.BASE/'source',checkpoint)==joined['baseFiles'],'original public base source unchanged')
                result['baseSourceUnchanged'] = True
                require(inventory(joined['qualifiedSDKSource'],checkpoint)==joined['sdkFiles'],'actual qualified SDK source unchanged')
                result['qualifiedSDKSourceUnchanged'] = True
            if expected is not None and (output/'source').is_dir():
                require(inventory(output/'source',checkpoint)==expected,'new complete source unchanged')
                result['sourceUnchanged'] = True
            if result['status'].startswith('PASS_'):
                require(len(result['processes'])==3 and result['allOwnedGroupsPositivelyAbsent'],'three owned commands closed')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and row['cleanupErrors']==[] for row in result['processes']),'normal producer completions')
            result['finalFreeBytes'] = guard()
        except BaseException as error:
            result['status'] = 'FAIL_FINAL_NATIVE_BUILD_PRESERVED'
            result['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        save()
    print(json.dumps({'status':result['status'],'receipt':str(receipt),'sha256':identity(frozen(receipt))['sha256'],
        'allOwnedGroupsPositivelyAbsent':result['allOwnedGroupsPositivelyAbsent'],'errors':result['errors'],'completionErrors':result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
