#!/usr/bin/env python3
"""Draft: retire only the independently verified original156 archive duplicate.

The existing Windows archive is opened for reading only. No account, compiler,
native process, decompression, archive rewrite, or original receipt edit occurs.
This recovery is distinct from the unchanged native/build resource gates.
"""
from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, os, shutil, signal, sys, time, uuid

SOURCE = Path('/var/lib/pinkha-w1-functional-migration-20261127/original156-source-custody2/private-evidence.tar.gz')
SIZE = 106036361
SHA = 'f85036744b0cb76ffecb4e29f752dd293a74a1f76c2d13c273df57691a4a8c64'
WINDOWS_ARCHIVE = r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-file-peer-45492064232-1\private-evidence.tar.gz'
WINDOWS_PARENT = r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\native-file-peer-45492064232-1'
PROOF = Path('/var/lib/pinkha-w1-engine-contracts-20261127/original156-duplicate-custody1/result.json')
PROOF_SHA = '71b728e45d328202fc507cba87bbc1f626c7a3a762bddce48d8cacfedc9f1610'
PRIMITIVE_SHA = '15cb1dcb9cfa45d5bc2b35e8ad2d8f13e636c0da8b0c59679739e88af95b226b'
CONTROL_PINS = {
    str(SOURCE.with_name('result.json')):'e69254e077b9c06b37e1e9b47e91042e20dc9cb1d7ec84371517bead4f3a2e96',
    str(SOURCE.with_name('private-original-index.json')):'9e4fc63d587d194cf13fff4002329c25404490c166dd9ffc4fac9778767167b1',
    str(SOURCE.with_name('recipient-readback.json')):'afc6663622d8ff47c09c08baa8b2f2909d0268269241b45f0833b2c51b79fc4d',
    str(PROOF):PROOF_SHA,
}
OUT_ROOT = '/var/lib/pinkha-w1-original156-retirement-20261127/'
MIB = 1024**2


def digest(path):
    h=hashlib.sha256()
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as f:
        for part in iter(lambda:f.read(MIB),b''):h.update(part)
    return h.hexdigest()


def load_primitives(directory):
    path=directory/'offhost_frozen_blobs.py'
    assert digest(path)==PRIMITIVE_SHA
    spec=importlib.util.spec_from_file_location('frozen_custody_primitives',path)
    module=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(module)
    return module


def protected_controls(module):
    result={}
    for path,expected in CONTROL_PINS.items():
        module.require_canonical_file(path);before=module.metadata(path)
        actual=module.sha_file(path);assert actual==expected and module.metadata(path)==before
        result[path]={'sha256':actual,'metadata':before}
    return result


def admit_existing_proof(module):
    module.require_canonical_file(PROOF);assert module.sha_file(PROOF)==PROOF_SHA
    with module.read_noatime(PROOF) as f:proof=json.load(f)
    assert proof['status']=='VERIFIED_EXISTING_WINDOWS_DUPLICATE_SOURCE_RETAINED'
    assert proof['source']==str(SOURCE) and proof['sourceBytes']==SIZE and proof['sourceSHA256']==SHA
    assert proof['remotePath'].replace('/','\\')==WINDOWS_ARCHIVE
    assert proof['expectedComputerName']=='DAVID_AND_GOLDY' and proof['remoteHostAlias']=='david-win'
    assert proof['streamBytes']==SIZE and proof['streamSHA256']==SHA
    assert proof['sourceUnchanged'] is True and proof['sourceRetired'] is False
    assert proof['exitCode']==0 and proof['ownedGroupAbsent'] is True and not proof['errors']
    assert proof['windowsWrites']==proof['accountOpens']==proof['nativeInvocations']==0
    expected=proof['sourceMetadata']
    renamed={'dev':'device','nlink':'links','atimeNS':'atime_ns','mtimeNS':'mtime_ns','ctimeNS':'ctime_ns'}
    mapped={renamed.get(k,k):v for k,v in expected.items()}
    module.require_canonical_file(SOURCE)
    assert module.metadata(SOURCE)==mapped and module.sha_file(SOURCE)==SHA and module.metadata(SOURCE)==mapped
    return proof,mapped


def existing_ps_header(module):
    # No OWNER marker, attributes, timestamps, permissions, or other data is
    # written under this existing private evidence directory.
    code="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
    code+="if([Environment]::MachineName-cne 'DAVID_AND_GOLDY'){throw 'wrong existing archive host'};"
    code+='$p='+module.q(WINDOWS_ARCHIVE)+';$d='+module.q(WINDOWS_PARENT)+';'
    code+="if([IO.Path]::GetFullPath($p)-cne $p-or [IO.Path]::GetDirectoryName($p)-cne $d){throw 'archive path mismatch'};"
    code+="if(-not [IO.File]::Exists($p)-or -not [IO.Directory]::Exists($d)){throw 'missing existing archive'};"
    code+="$walk=$d;while($walk){if(([IO.File]::GetAttributes($walk)-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'existing ancestor reparse point'};$walk=[IO.Path]::GetDirectoryName($walk)};"
    code+="if(([IO.File]::GetAttributes($p)-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'archive reparse point'};"
    code+='if([IO.FileInfo]::new($p).Length-ne '+str(SIZE)+"){throw 'existing archive length'};"
    return code


def existing_info(module):
    code=existing_ps_header(module)
    code+="$f=[IO.FileInfo]::new($p);$dinfo=[IO.DirectoryInfo]::new($d);"
    code+="[Console]::Out.WriteLine((@{host=[Environment]::MachineName;path=$p;parent=$d;bytes=$f.Length;fileAttributes=[int]$f.Attributes;fileCreationTicks=$f.CreationTimeUtc.Ticks;fileWriteTicks=$f.LastWriteTimeUtc.Ticks;fileAccessTicks=$f.LastAccessTimeUtc.Ticks;parentAttributes=[int]$dinfo.Attributes;parentCreationTicks=$dinfo.CreationTimeUtc.Ticks;parentWriteTicks=$dinfo.LastWriteTimeUtc.Ticks;parentAccessTicks=$dinfo.LastAccessTimeUtc.Ticks;writeOperations=0}|ConvertTo-Json -Compress))"
    return module.ps_wrap(code)


def existing_readback(module):
    code=existing_ps_header(module)
    code+="$f=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);"
    code+='try{if($f.Length-ne '+str(SIZE)+"){throw 'open existing archive length'};$o=[Console]::OpenStandardOutput();$task=$f.CopyToAsync($o,65536);if(-not $task.Wait(240000)){throw 'existing readback deadline'};$o.Flush()}finally{$f.Dispose()}"
    return module.ps_wrap(code)


def validate_info(info):
    assert info['host']=='DAVID_AND_GOLDY' and info['path']==WINDOWS_ARCHIVE and info['parent']==WINDOWS_PARENT
    assert info['bytes']==SIZE and info['writeOperations']==0
    assert not (info['fileAttributes']&0x400 or info['parentAttributes']&0x400)


def verify_existing_read_observation(before, after):
    """Keep exact data/write metadata; record the observed read-access clock.

    The original FAIL is retained: Windows updated LastAccessTime during the
    verified read. Do not claim that clock stayed unchanged or write it back.
    Every other observed field, including both directory clocks, must match.
    Full bytes are independently authenticated by the surrounding readback.
    """
    validate_info(before);validate_info(after)
    assert set(before)==set(after), 'existing metadata fields changed'
    changes={k:{'before':before[k],'after':after[k]} for k in before if before[k]!=after[k]}
    assert set(changes)<= {'fileAccessTicks'}, 'existing data/write/parent metadata changed'
    assert type(before['fileAccessTicks']) is int and type(after['fileAccessTicks']) is int
    assert after['fileAccessTicks']>=before['fileAccessTicks'], 'read-access clock moved backwards'
    return {'allObservedMetadataUnchanged':not changes,'dataAndWriteMetadataUnchanged':True,
            'observedReadAccessChanges':changes,'existingWindowsMetadataWrites':0,
            'causeOfAccessTimeAdvanceInferred':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--oracle-hostname',required=True)
    args=parser.parse_args()
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename==args.oracle_hostname
    module=load_primitives(Path(__file__).parent)
    out=args.output;assert out.is_absolute() and str(out).startswith(OUT_ROOT) and out.parent.resolve()==out.parent
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();initial_free=shutil.disk_usage('/var/lib').free;token=uuid.uuid4().hex
    remote_root=module.WIN_PARENT+'\\pinkha-original156-custody-20261127-'+token
    result={'protocol':'original156-existing-windows-duplicate-retirement-v1','status':'RUNNING','source':str(SOURCE),'bytes':SIZE,'sha256':SHA,'windowsArchive':WINDOWS_ARCHIVE,'windowsControlRoot':remote_root,'token':token,'commands':[],'errors':[],'retired':False,'existingWindowsArchiveWriteOperations':0,'originalReceiptWriteOperations':0,'accountOpens':0,'compilerRuns':0,'nativeRuns':0,'archiveExtractions':0}
    def save():result['seconds']=round(time.monotonic()-started,3);module.atomic_json(out/'result.json',result)
    def guard():
        assert time.monotonic()-started<900,'bounded original156 duplicate retirement'
        free=shutil.disk_usage('/var/lib').free;result['minimumRootFreeBytes']=min(result.get('minimumRootFreeBytes',free),free)
        result['observedGlobalRootFreeDeltaBytes']=free-initial_free
        assert free>=256*MIB,'recovery-only absolute root emergency floor'
        allocated=sum(p.stat().st_blocks*512 for p in out.iterdir() if p.is_file());result['ownedOutputAllocatedBytes']=allocated
        assert allocated<=4*MIB and not (out/'abort').exists(),'bounded owned recovery controls'
    def interrupted(*_):raise RuntimeError('original156 custody recovery interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def remote(code,label,**kwargs):return module.ssh_stream(code,label,save,guard,result['commands'],**kwargs)
    def upload_control(name,data):
        assert name in {'original156_duplicate_retirement.py','restore_original156_blob.py','offhost_frozen_blobs.py','restoration-map.json','reviewed-existing-duplicate-proof.json'}
        h=hashlib.sha256(data).hexdigest()
        ack=json.loads(remote(module.ps_upload(remote_root,token,name,len(data),h,4*MIB),'upload-new-control-'+name,source=data))
        assert ack['host']==module.WIN_HOST and ack['root']==remote_root and ack['token']==token and ack['name']==name
        assert ack['bytes']==len(data) and ack['sha256']==h and ack['flushToDisk'] is True and ack['createNew'] is True and ack['readOnly'] is True
        sent=result['commands'][-1];assert sent['inputBytes']==len(data) and sent['inputSHA256']==h
        remote(module.ps_readback(remote_root,token,name,len(data)),'verify-new-control-'+name,expected_size=len(data),expected_sha=h)
    try:
        guard();result['resourcePolicy']={'recoveryOnly':True,'rootEmergencyFloorBytes':256*MIB,'ownedControlAllocationCapBytes':4*MIB,'newLargeOracleBytes':0,'unchangedNativeRootFloorBytes':2*1024**3,'unchangedNativeDevelopmentFloorBytes':512*MIB,'ambientGlobalFreeDeltaAuditedSeparately':True}
        proof,before=admit_existing_proof(module);result['reviewedFullStreamProofSHA256']=PROOF_SHA;result['sourceBefore']=before
        result['protectedControlsBefore']=protected_controls(module)
        result['nativePinsBefore']={p:module.sha_file(p) for p in module.PINS};assert result['nativePinsBefore']==module.PINS
        result['noLiveBefore']=module.no_live_inodes([SOURCE]);save()
        info=json.loads(remote(existing_info(module),'inspect-existing-windows-archive'));validate_info(info);result['existingWindowsBefore']=info
        owner=json.loads(remote(module.ps_create(remote_root,token,4*MIB),'create-new-tiny-control-root'))
        assert owner['root']==remote_root and owner['token']==token and owner['host']==module.WIN_HOST;result['windowsControlOwner']=owner
        script=Path(__file__).read_bytes();restore=Path(__file__).with_name('restore_original156_blob.py').read_bytes();primitives=Path(__file__).with_name('offhost_frozen_blobs.py').read_bytes()
        assert hashlib.sha256(primitives).hexdigest()==PRIMITIVE_SHA
        manifest={'protocol':'original156-compressed-archive-exclusive-restoration-v1','source':str(SOURCE),'bytes':SIZE,'sha256':SHA,'sourceMetadata':before,'windowsArchive':WINDOWS_ARCHIVE,'windowsHost':module.WIN_HOST,'windowsBefore':info,'windowsControlRoot':remote_root,'token':token,'reviewedProofSHA256':PROOF_SHA,'controllerSHA256':hashlib.sha256(script).hexdigest(),'restoreHelperSHA256':hashlib.sha256(restore).hexdigest(),'primitivesSHA256':PRIMITIVE_SHA,'nativePins':module.PINS,'protectedControlPins':CONTROL_PINS,'originalArchivePathUnavailableAfterRetirement':True,'restorePrerequisite':'Restore this exact compressed archive exclusively to its original Oracle path before reusing completed audit_original156_history_authority.py or audit_original156_history_headers.py. Neither audit is rerun here.','restoredMetadata':['mode','uid','gid','atime_ns','mtime_ns','xattrs'],'inodeDeviceCtimeRecordedButNotRecreated':True}
        module.atomic_json(out/'restoration-map.json',manifest);result['restorationMapSHA256']=module.sha_file(out/'restoration-map.json');save()
        with module.read_noatime(PROOF) as f:proof_bytes=f.read()
        for name,data in [('original156_duplicate_retirement.py',script),('restore_original156_blob.py',restore),('offhost_frozen_blobs.py',primitives),('restoration-map.json',(out/'restoration-map.json').read_bytes()),('reviewed-existing-duplicate-proof.json',proof_bytes)]:
            if name!='restoration-map.json':
                with (out/name).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
            upload_control(name,data)
        module.fsync_dir(out)
        # Only this full streamed read of the existing archive occurs here;
        # the fourE binary transport control is not rerun or relabelled.
        remote(existing_readback(module),'fresh-full-existing-archive-readback',expected_size=SIZE,expected_sha=SHA)
        readback_ended=time.monotonic();result['freshFullStreamBytes']=SIZE;result['freshFullStreamSHA256']=SHA
        after=json.loads(remote(existing_info(module),'reinspect-existing-windows-archive'));result['existingWindowsAfter']=after
        result['existingWindowsReadObservation']=verify_existing_read_observation(info,after)
        module.require_canonical_file(SOURCE);assert module.metadata(SOURCE)==before and module.sha_file(SOURCE)==SHA
        assert protected_controls(module)==result['protectedControlsBefore']
        assert {p:module.sha_file(p) for p in module.PINS}==module.PINS
        result['noLiveBeforeCapture']=module.no_live_inodes([SOURCE])
        assert all(x['status']=='PASS' and x['exitCode']==0 and x['groupPositivelyAbsent'] and not x['forcedCleanup'] for x in result['commands'])
        guard();assert time.monotonic()-readback_ended<60,'full stream must immediately precede capture'
        quarantine=SOURCE.with_name(SOURCE.name+'.custody-'+token)
        result.update(retirementStage='exclusive-capture-intent',quarantine=str(quarantine),freshReadbackToCaptureSeconds=round(time.monotonic()-readback_ended,3));save()
        module.rename_exclusively(SOURCE,quarantine);module.fsync_dir(SOURCE.parent);result['retirementStage']='captured';save()
        try:
            module.require_canonical_file(quarantine);captured=module.metadata(quarantine)
            assert {k:v for k,v in captured.items() if k!='ctime_ns'}=={k:v for k,v in before.items() if k!='ctime_ns'}
            assert module.sha_file(quarantine)==SHA
            result['noLiveCaptured']=module.no_live_inodes([quarantine]);assert module.metadata(quarantine)==captured
            quarantine.unlink();module.fsync_dir(SOURCE.parent)
            result.update(retired=True,retirementStage='retired-verified-duplicate',allocatedRootBytesRecovered=before['allocatedBytes']);save()
            assert not os.path.lexists(SOURCE)
        except BaseException:
            if os.path.lexists(quarantine):
                try:module.rename_exclusively(quarantine,SOURCE);module.fsync_dir(SOURCE.parent);result['rollback']='restored-original-name-exclusively'
                except OSError as error:result['rollback']='quarantine-preserved-no-overwrite';result['rollbackError']=str(error)
            save();raise
        result['status']='PASS_ORIGINAL156_DUPLICATE_RETIRED_WITH_VERIFIED_BYTES_AND_RECORDED_READ_ACCESS_TIME_NO_NATIVE_ACCEPTANCE'
    except BaseException as error:
        result['status']='FAIL_ORIGINAL156_DUPLICATE_CUSTODY';result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        try:
            result['protectedControlsAfter']=protected_controls(module);result['protectedControlsUnchanged']=result['protectedControlsAfter']==result.get('protectedControlsBefore');assert result['protectedControlsUnchanged']
            result['nativePinsFinal']={p:module.sha_file(p) for p in module.PINS};assert result['nativePinsFinal']==module.PINS
        except BaseException as error:
            result['status']='FAIL_ORIGINAL156_DUPLICATE_CUSTODY';result['errors'].append({'type':type(error).__name__,'message':'final protected controls/native pins: '+str(error)})
        result['allOwnedSSHGroupsAbsent']=all(x.get('groupPositivelyAbsent') for x in result['commands'])
        if not result['allOwnedSSHGroupsAbsent']:result['status']='FAIL_ORIGINAL156_DUPLICATE_CUSTODY'
        result['originalArchivePathPresent']=os.path.lexists(SOURCE);result['originalDirectoryMtimeEqualityClaimed']=False;save()
    print(json.dumps({'status':result['status'],'receipt':str(out/'result.json'),'sha256':module.sha_file(out/'result.json'),'seconds':result['seconds'],'retired':result['retired']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
