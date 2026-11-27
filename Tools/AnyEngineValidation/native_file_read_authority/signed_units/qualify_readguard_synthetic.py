#!/usr/bin/env python3
"""Qualify only 21 synthetic signed-ACL/lifetime methods; never open retained accounts.

Source-only preparation until root reviews this controller and assigns a slot.
The selected tests generate their own in-memory ACL identities. No native Any
server, saved account, wallet, private snapshot, credential or export is used.
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
import signal
import stat
import sys
import time

PARENT=Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-synthetic-20261127')
BASE=Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/source/.runtime-artifacts/sdk-source')
BASE_MANIFEST=Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/source-manifest.json')
BASE_SHA='e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a'
DRAFT=Path('/mnt/development/projects/evidence/pinkha-w1-files-readguard-lifetime-draft-20261127-attempt2')
DRAFT_SHA='ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896'
PATCH_SHA='874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f'
CACHE=Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
CACHE_TARGET=Path('/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127')
OWNED_HELPER=Path(__file__).resolve().with_name('owned_swift_commands.py')
OWNED_HELPER_SHA='f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
OWNED_PROOF=Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
OWNED_PROOF_SHA='040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
ROOT_FLOOR=2*1024**3
DEV_FLOOR=512*1024**2
ROOT_RESERVE=32*1024**2
DEV_RESERVE=384*1024**2
OWNED_CAP=256*1024**2
GO_LOG_CAP=8*1024**2
PACKAGES=('github.com/anyproto/any-sync-sdk/internal/files/readguard',
          'github.com/anyproto/any-sync-sdk/internal/anysyncx')
TOP={
    'TestReadGuardPreservesCurrentSignedReaderAndGuest',
    'TestReadGuardUsesLoadedGuestIdentityAfterItsSignedRemoval',
    'TestReadGuardRefusesRevokedOpenBeforeContentLookup',
    'TestReadGuardHeldCachedReaderStopsAfterCurrentSignedRemoval',
    'TestReadGuardRechecksSignedAuthorityAfterAwaitedFetch',
    'TestReadGuardClosesOpenedReaderWhenAuthorityChangedDuringOpen',
    'TestReadGuardSeekThenReadRechecksCurrentSignedPermission',
    'TestReadGuardRechecksAfterAnAwaitedSeek',
    'TestReadGuardLateContextCancellationDiscardsFetchedPlaintext',
    'TestReadGuardCannotReadWithRetiredAuthorityLoader',
    'TestReadGuardPreservesByteRangesEOFAndBoundedPrivateMemory',
    'TestReadGuardCloseDoesNotWaitForFetchOrReleasePendingBytes',
    'TestReadGuardInvalidatedReaderRequiresFreshOpenAfterExplicitGrant',
    'TestReadGuardRejectsSignedRevokeRestoreABA',
    'TestReadGuardSignedHeadChangeRequiresFreshOpenEvenWithSameRole',
    'TestReadGuardCannotSwitchSignedAccountOrSpaceDuringFetch',
    'TestReadGuardRetirementAfterLoadBeforeFinalACLLock',
    'TestReadGuardPendingCloseWaitRevalidatesOrCancels',
    'TestReadGuardSameSpaceReloadRequiresNewReaderWithUnchangedACL',
    'TestFileReadLifetimeAppCloseRetiresBeforeCacheTeardown',
    'TestFileReadLifetimeWrapperCloseAndTryCloseBoundaries',
}
CHILDREN={
    'TestReadGuardPreservesCurrentSignedReaderAndGuest':('reader','guest'),
    'TestReadGuardRejectsSignedRevokeRestoreABA':('open','read'),
    'TestReadGuardRetirementAfterLoadBeforeFinalACLLock':('account','space'),
    'TestReadGuardPendingCloseWaitRevalidatesOrCancels':('declined','committed','declined-then-close','caller-cancel','reader-close'),
    'TestFileReadLifetimeWrapperCloseAndTryCloseBoundaries':('close','try-declined','try-committed'),
}
ALL_METHODS=TOP|{name+'/'+child for name,children in CHILDREN.items() for child in children}
assert len(TOP)==21 and len(ALL_METHODS)==35


def physical(path,directory=False):
    assert path.is_absolute() and path.resolve()==path and not path.is_symlink(),str(path)
    info=path.lstat()
    assert stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    return info


def frozen(path,limit=4*1024**2):
    before=physical(path)
    assert before.st_size<=limit
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd,'rb') as stream:
        assert os.fstat(stream.fileno())==before
        data=stream.read(limit+1)
        assert os.fstat(stream.fileno())==before
    assert path.lstat()==before and len(data)==before.st_size
    return data


def row(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def write_new(path,data,mode=0o600):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
    with os.fdopen(descriptor,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())


def inventory(root):
    physical(root,True)
    values={}
    stack=[root]
    while stack:
        parent=stack.pop()
        fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
        try:
            with os.scandir(fd) as entries:names=sorted(x.name for x in entries)
        finally:os.close(fd)
        for name in names:
            path=parent/name
            info=path.lstat()
            assert not stat.S_ISLNK(info.st_mode)
            if stat.S_ISDIR(info.st_mode):stack.append(path)
            else:
                assert stat.S_ISREG(info.st_mode)
                values[path.relative_to(root).as_posix()]=row(frozen(path))
        assert len(values)<=800 and len(stack)<=800
    return values


def main():
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must stay enabled')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    output=args.output
    assert output.parent==PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}',output.name)
    physical(PARENT.parent,True)
    if not PARENT.exists():PARENT.mkdir(mode=0o700)
    physical(PARENT,True)
    # Reservation is before the try/finally that persists receipts. Repeating an
    # occupied output cannot overwrite any prior evidence, including a FAIL.
    output.mkdir(mode=0o700,exist_ok=False)
    receipt=output/'result.json'
    write_new(receipt,b'{}\n')
    os.umask(0o077)
    began=time.monotonic()
    journal_serial=0
    owned=None
    base_expected=None
    expected=None
    input_rows={}
    input_limits={}
    source=output/'sdk-source'
    result={'protocol':'pinkha-readguard-synthetic-signed-acl-lifetime-v1','status':'RUNNING',
            'scope':'Only 21 synthetic signed-ACL/lifetime methods, 14 named subtests; no retained account/key access or export',
            'retainedAccountOpens':0,'retainedPrivateMaterialAccesses':0,'nativeServerStarts':0,
            'networkRPCs':0,'sourceProductEdits':0,'fullSDKOrAnyRuntimeAcceptance':False,
            'processes':[],'errors':[],'completionErrors':[],
            'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR,
                              'rootAdmissionReserveBytes':ROOT_RESERVE,'developmentAdmissionReserveBytes':DEV_RESERVE,
                              'ownedOutputCapBytes':OWNED_CAP,'workers':2,'goMemoryLimit':'1GiB',
                              'commandTimeoutSeconds':300,'metadataCommandTimeoutSeconds':15,
                              'controllerBudgetSeconds':360,'requiredOuterTimeoutSeconds':420,
                              'basis':'Prior exact anysyncx baseline+17-method run consumed100,048,896B peak development and18,968,576B root. This run adds the small readguard package and moves its6,625,763B source copy/log/tmp entirely to development;384MiB development+32MiB root reserve is conservative, unchanged2GiB/512MiB live floors.'}}

    def save():
        nonlocal journal_serial
        journal_serial+=1
        result['seconds']=round(time.monotonic()-began,3)
        temp=output/('result.json.next-'+str(journal_serial))
        write_new(temp,(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
        os.replace(temp,receipt)
        fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def save_command(path,value):
        nonlocal journal_serial
        assert path.parent in (output/'synthetic21-command',output/'go-toolchain-identity')
        assert path.name in ('started.json','result.json')
        journal_serial+=1
        temp=path.with_name(path.name+'.next-'+str(journal_serial))
        write_new(temp,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
        os.replace(temp,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        save()

    def capacity(admit=False):
        values={name:shutil.disk_usage(path).free for name,path in [('root','/'),('development','/mnt/development')]}
        for name,floor,reserve in [('root',ROOT_FLOOR,ROOT_RESERVE),('development',DEV_FLOOR,DEV_RESERVE)]:
            result.setdefault('minimumFreeBytes',{})[name]=min(values[name],result.get('minimumFreeBytes',{}).get(name,values[name]))
            assert values[name]>=floor+(reserve if admit else 0),name+' unchanged resource gate'
        assert time.monotonic()-began<360,'360s controller budget'
        assert not (output/'abort').exists(),'owned synthetic qualifier abort'
        return values

    def output_bound():
        count=0;allocated=0
        for parent,dirs,files in os.walk(output,followlinks=False):
            for name in dirs:assert not (Path(parent)/name).is_symlink()
            for name in files:
                path=Path(parent)/name
                try:info=path.lstat()
                except FileNotFoundError:
                    # Go may remove only its own transient output between the
                    # directory listing and this metadata observation. Fixed
                    # source, logs and receipts still fail if they disappear.
                    if path.is_relative_to(output/'go-tmp'):continue
                    raise
                assert stat.S_ISREG(info.st_mode)
                count+=1;allocated+=max(info.st_size,info.st_blocks*512)
        assert count<=10000 and allocated<=OWNED_CAP,'owned source/tmp/log budget'
        result['peakOwnedBytes']=max(result.get('peakOwnedBytes',0),allocated)

    def interrupt(number,_frame):raise RuntimeError('owned synthetic qualifier interrupted by signal '+str(number))
    for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,interrupt)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})

    try:
        controller=row(frozen(Path(__file__)));input_rows[str(Path(__file__))]=controller
        result['controller']=controller
        helper=frozen(OWNED_HELPER);assert row(helper)['sha256']==OWNED_HELPER_SHA
        proof=frozen(OWNED_PROOF);assert row(proof)['sha256']==OWNED_PROOF_SHA
        input_rows[str(OWNED_HELPER)]=row(helper);input_rows[str(OWNED_PROOF)]=row(proof)
        specification=importlib.util.spec_from_file_location('readguard_qualified_owned_commands',OWNED_HELPER)
        owned=importlib.util.module_from_spec(specification)
        specification.loader.exec_module(owned)
        result['processOwnershipReuse']={'helperSHA256':OWNED_HELPER_SHA,'actualFiveControlReceiptSHA256':OWNED_PROOF_SHA,
                                         'unchangedControlsRerun':False,'leaderRetainedUntilResidualGroupDrain':True}
        result['admissionFreeBytes']=capacity(True)
        available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
        assert available>=2*1024**3
        result['resourcePolicy']['memAvailableBefore']=available
        assert CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET
        physical(CACHE_TARGET,True)
        raw=frozen(BASE_MANIFEST);assert row(raw)['sha256']==BASE_SHA
        input_rows[str(BASE_MANIFEST)]=row(raw)
        manifest=json.loads(raw)['files'];prefix='.runtime-artifacts/sdk-source/'
        base_expected={key.removeprefix(prefix):value for key,value in manifest.items() if key.startswith(prefix)}
        assert len(base_expected)==718 and sum(x['bytes'] for x in base_expected.values())==6625763
        assert inventory(BASE)==base_expected
        draft_raw=frozen(DRAFT/'manifest.json');assert row(draft_raw)['sha256']==DRAFT_SHA
        input_rows[str(DRAFT/'manifest.json')]=row(draft_raw)
        draft=json.loads(draft_raw)
        assert draft['baseCurrentSourceManifestSHA256']==BASE_SHA and draft['patch']['sha256']==PATCH_SHA
        assert draft['status']=='UNCOMPILED_SOURCE_DRAFT_NOT_PRODUCT_ACCEPTANCE'
        assert len(draft['paths'])==10 and draft['productionPaths']==7 and draft['testPaths']==3
        assert set(draft['topLevelMethods'])==TOP and draft['testMethodCount']==21
        patch=frozen(DRAFT/'sdk-files-readguard.patch');assert row(patch)['sha256']==PATCH_SHA
        input_rows[str(DRAFT/'sdk-files-readguard.patch')]=row(patch)
        source.mkdir(mode=0o700)
        for n,(name,desired) in enumerate(sorted(base_expected.items())):
            if n%64==0:capacity()
            rel=PurePosixPath(name);assert str(rel)==name and not rel.is_absolute() and '..' not in rel.parts
            data=frozen(BASE/name);assert row(data)==desired
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
            write_new(target,data,0o644)
        assert inventory(source)==base_expected
        expected=dict(base_expected)
        for name,change in sorted(draft['paths'].items()):
            rel=PurePosixPath(name);assert str(rel)==name and '..' not in rel.parts and name.startswith('internal/')
            assert expected.get(name)==change['before'],name+' base differs'
            data=frozen(DRAFT/name);assert row(data)==change['after']
            input_rows[str(DRAFT/name)]=row(data)
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
            if change['before'] is None:write_new(target,data,0o644)
            else:
                replacement=target.with_name(target.name+'.candidate')
                write_new(replacement,data,0o644);os.replace(replacement,target)
            expected[name]=change['after']
        assert len(expected)==725 and inventory(source)==expected
        changed={name for name in set(expected)|set(base_expected) if expected.get(name)!=base_expected.get(name)}
        assert changed==set(draft['paths'])
        write_new(output/'source-before.json',(json.dumps(expected,sort_keys=True,indent=2)+'\n').encode())
        result['sourceAdmission']={'baseManifestSHA256':BASE_SHA,'baseSDKFiles':718,'baseSDKContentBytes':6625763,
                                  'candidateManifestSHA256':DRAFT_SHA,'candidatePatchSHA256':PATCH_SHA,
                                  'syntheticSDKFiles':725,'changedPaths':sorted(changed),
                                  'sourceManifest':row(frozen(output/'source-before.json')),
                                  'sourcePhysicalPath':str(source),'originalSDKUnchanged':True}
        output_bound();capacity()
        temporary=output/'go-tmp';temporary.mkdir(mode=0o700)
        env=os.environ.copy()
        env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE=str(CACHE),
                   GOMODCACHE='/root/go/pkg/mod',GOTMPDIR=str(temporary),TMPDIR=str(temporary),
                   CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
        # Bind the driver actually invoked, not a version inferred from a path
        # or from the old Any executable. This metadata command has its own
        # qualified owned-process row, counted separately from the test group.
        driver_alias=Path('/usr/local/bin/go')
        driver=driver_alias.resolve(strict=True);physical(driver)
        driver_identity=row(frozen(driver,128*1024**2))
        input_rows[str(driver)]=driver_identity;input_limits[str(driver)]=128*1024**2
        def metadata_observe():
            try:
                capacity();output_bound()
                metadata_log=output/'go-toolchain-identity/original.log'
                if metadata_log.exists():assert metadata_log.stat().st_size<=65536
                return None
            except Exception as error:return type(error).__name__+': '+str(error)
        metadata_argv=[str(driver),'env','-json','GOVERSION','GOROOT','GOTOOLDIR','GOHOSTOS','GOHOSTARCH','GOOS','GOARCH']
        metadata_log,metadata_process=owned.run(output/'go-toolchain-identity',metadata_argv,source,env,15,
            metadata_observe,save_command,lambda path:row(frozen(path,65536))['sha256'],result['processes'])
        metadata=json.loads(frozen(metadata_log,65536))
        assert set(metadata)=={'GOVERSION','GOROOT','GOTOOLDIR','GOHOSTOS','GOHOSTARCH','GOOS','GOARCH'}
        assert all(isinstance(v,str) and v for v in metadata.values())
        assert re.fullmatch(r'go[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[a-z0-9.-]*)?',metadata['GOVERSION'])
        assert metadata['GOOS']==metadata['GOHOSTOS']=='linux' and metadata['GOARCH']==metadata['GOHOSTARCH']
        root_path=Path(metadata['GOROOT']).resolve(strict=True);physical(root_path,True)
        tools_path=Path(metadata['GOTOOLDIR']).resolve(strict=True);physical(tools_path,True)
        tool_identities={}
        for name in ('compile','link'):
            tool=(tools_path/name).resolve(strict=True);physical(tool)
            identity=row(frozen(tool,128*1024**2))
            input_rows[str(tool)]=identity;input_limits[str(tool)]=128*1024**2
            tool_identities[name]={'canonicalPath':str(tool),**identity}
        assert driver_alias.resolve(strict=True)==driver and row(frozen(driver,128*1024**2))==driver_identity
        result['goToolchain']={'requestedDriverAlias':str(driver_alias),'canonicalDriverPath':str(driver),
                               'driver':driver_identity,'observedEnvironment':metadata,'canonicalGOROOT':str(root_path),
                               'canonicalGOTOOLDIR':str(tools_path),'tools':tool_identities,
                               'metadataRawLog':row(frozen(metadata_log,65536)),
                               'metadataGroupPositivelyAbsent':metadata_process['processGroupAbsent'],
                               'versionInferredFromPreviousRuntime':False}
        pattern='^('+'|'.join(sorted(TOP))+')$'
        command=[str(driver),'test','-json','-count=1','-p=2','-timeout=90s','-run',pattern,
                 './internal/files/readguard','./internal/anysyncx']
        result['environment']={k:env[k] for k in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB')}
        folder=output/'synthetic21-command';log=folder/'original.log'
        next_bound=time.monotonic()
        statistics={'resourceSamples':0}
        def observe():
            nonlocal next_bound
            try:
                capacity()
                if log.exists():assert log.stat().st_size<=GO_LOG_CAP,'bounded raw Go log'
                if time.monotonic()>=next_bound:
                    output_bound();next_bound=time.monotonic()+2
                statistics['resourceSamples']+=1
                return None
            except Exception as error:
                return type(error).__name__+': '+str(error)
        command_error=None
        try:
            returned_log,process_row=owned.run(folder,command,source,env,300,observe,
                save_command,lambda path:row(frozen(path,GO_LOG_CAP))['sha256'],result['processes'],statistics)
            assert returned_log==log and process_row is result['processes'][-1]
        except BaseException as error:
            command_error=error
        if not log.is_file():
            if command_error is not None:raise command_error
            raise AssertionError('owned command did not retain its raw log')
        raw_log=frozen(log,GO_LOG_CAP)
        events=[];non_json=0
        for line in raw_log.splitlines():
            try:value=json.loads(line)
            except json.JSONDecodeError:non_json+=1;continue
            assert isinstance(value,dict)
            if value.get('Action') in ('run','pass','fail','skip'):
                events.append({key:value[key] for key in ('Action','Package','Test','Elapsed') if key in value})
        test_runs=Counter((e['Package'],e['Test']) for e in events if e['Action']=='run' and 'Test' in e)
        test_pass=Counter((e['Package'],e['Test']) for e in events if e['Action']=='pass' and 'Test' in e)
        result['observedTestEvents']=events
        result['rawLog']=row(raw_log)
        result['observedTestCounts']={action:sum(e['Action']==action and 'Test' in e for e in events)
                                      for action in ('run','pass','fail','skip')}
        result['ignoredNonJSONLogLines']=non_json
        save()
        if command_error is not None:raise command_error
        assert process_row['exitCode']==0 and process_row['processGroupAbsent'],'Go process outcome'
        assert not process_row['forcedCleanup'] and process_row['cleanupErrors']==[] and process_row['stopReason'] is None
        assert process_row['unreapedLeaderDuringGroupCleanup']
        wanted={(PACKAGES[1] if name.startswith('TestFileReadLifetime') else PACKAGES[0],name) for name in ALL_METHODS}
        assert set(test_runs)==wanted and all(v==1 for v in test_runs.values())
        assert set(test_pass)==wanted and all(v==1 for v in test_pass.values())
        assert not any(e['Action'] in ('fail','skip') for e in events),'no failed or skipped test/package allowed'
        package_pass=Counter(e['Package'] for e in events if e['Action']=='pass' and 'Test' not in e)
        assert package_pass==Counter(PACKAGES)
        result['actualMethods']={'topLevel':21,'namedSubtests':14,'totalRuns':35,'totalPasses':35,'skips':0,
                                 'packages':list(PACKAGES),'ignoredNonJSONLogLines':non_json,'events':events}
        result['rawLog']=row(raw_log)
        assert inventory(source)==expected and inventory(BASE)==base_expected
        result['status']='PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE'
    except BaseException as error:
        result['status']='FAIL_SYNTHETIC_QUALIFICATION'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,signal.SIG_IGN)
        # The qualified helper already drained/reaped its owned command and
        # latched absence. Never probe or signal its historical numeric PGID.
        result['allOwnedGroupsPositivelyAbsent']=all(p.get('processGroupAbsent') for p in result['processes'])
        try:
            for name,desired in input_rows.items():
                assert row(frozen(Path(name),input_limits.get(name,4*1024**2)))==desired,name+' input changed'
            result['allUsedPublicInputsUnchanged']=True
            if base_expected is not None:
                assert inventory(BASE)==base_expected
                result['originalSDKUnchanged']=True
            if expected is not None:
                assert inventory(source)==expected
                result['candidateSourceUnchanged']=True
            log=output/'synthetic21-command/original.log'
            if log.exists():result['rawLog']=row(frozen(log,GO_LOG_CAP))
            if result['status'].startswith('PASS_'):
                assert len(result['processes'])==2 and result['allOwnedGroupsPositivelyAbsent']
                assert all(p['exitCode']==0 and not p['forcedCleanup'] and p['cleanupErrors']==[] for p in result['processes'])
                assert result['actualMethods']['totalPasses']==35 and result['actualMethods']['skips']==0
            output_bound();result['freeAfter']=capacity()
        except BaseException as error:
            result['status']='FAIL_SYNTHETIC_QUALIFICATION'
            result['completionErrors'].append({'finalIntegrity':type(error).__name__,'message':str(error)})
        retained=False
        try:save();retained=True
        except BaseException as error:
            result['status']='FAIL_SYNTHETIC_QUALIFICATION'
            result['completionErrors'].append({'receiptRetention':type(error).__name__,'message':str(error)})
    print(json.dumps({'status':result['status'],'result':str(receipt),'receiptRetained':retained,
                      'sha256':row(frozen(receipt))['sha256'] if retained else None,
                      'errors':result['errors'],'completionErrors':result['completionErrors']}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
