#!/usr/bin/env python3
"""DRAFT: exact streamed off-host custody of two closed Swift cache directories.

The optional third root is the explicitly approved dormant legacy native build,
never its current sibling. This controller is capacity recovery only. Original
paths become unavailable only after full remote custody and require restoration
before any historical rebuild/rerun. No current product or account is moved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import sys
import time
import uuid

import root_swift_archive_format as fmt
import root_swift_archive_transport as transport
import frozen_sftp_custody_adapter as adapter

MIB=1024**2
ROOTS={'indexed':Path('/tmp/pinkha-w1-engine-contracts-indexed-20261127'),
       'cache':Path('/tmp/pinkha-w1-engine-contracts-cache-20261127')}
LEGACY=Path('/var/lib/pinkha-root-t2-linux-20261126/build1/legacy')
UPPER_ALLOCATED=295596032
LEGACY_UPPER_ALLOCATED=100425728
PINS={
 '/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-components2/result.json':'25a6c48dfb95dec2689682bdf80da6798dabb1a670f769f740e2357de7c8882e',
 '/var/lib/pinkha-w1-engine-contracts-20261127/native-related-functional1/result.json':'9e26b39507fcaf32fed97cc10f9ad8ff23e0c7a6f35fcde993ae831d6ea59f9c',
 '/mnt/development/projects/worktrees/anytype-engine-contracts-20261127/Modules/PinkhaAnyEngine/Package.resolved':'50ddc3fc5398afb197e62f3cd8aa251315dbdd8d9d1d67e0dc665862ef3258af',
 **transport.PINS}
OUTPUT_PARENT=Path('/var/lib/pinkha-w1-root-swift-offhost-custody-20261127')
MODULES=('offhost_root_swift_caches.py','restore_offhost_root_swift_caches.py',
         'root_swift_archive_format.py','root_swift_archive_transport.py','frozen_sftp_custody_adapter.py')


def no_live(identities):
    inodes={(s[0],s[1]):relative for relative,s in identities.items()};found=[];inspected=0;start=time.monotonic()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal() or int(proc.name)==os.getpid():continue
        assert time.monotonic()-start<40,'bounded live-use scan'
        try:
            refs=[proc/'cwd',proc/'exe']+list((proc/'fd').iterdir())
            for ref in refs:
                inspected+=1;assert inspected<=250000
                try:s=ref.stat()
                except (FileNotFoundError,ProcessLookupError):continue
                if (s.st_dev,s.st_ino) in inodes:found.append({'pid':int(proc.name),'reference':str(ref),'entry':inodes[(s.st_dev,s.st_ino)]})
            with (proc/'maps').open('rb') as stream:raw=stream.read(4*MIB+1)
            assert len(raw)<=4*MIB
            for line in raw.splitlines():
                fields=line.split(None,5)
                if len(fields)<5 or not fields[4].isdigit():continue
                major,minor=fields[3].split(b':');identity=(os.makedev(int(major,16),int(minor,16)),int(fields[4]))
                if identity in inodes:found.append({'pid':int(proc.name),'mapping':True,'entry':inodes[identity]})
        except (FileNotFoundError,ProcessLookupError):continue
    assert not found,'approved closed directory has live users: '+json.dumps(found)
    return {'matchingLiveUsers':0,'fdAndPathEntriesInspected':inspected,'seconds':round(time.monotonic()-start,3)}


def allocated_roots(roots,identities):
    seen=set();total=0
    for relative,identity in identities.items():
        label,_,tail=relative.partition('/');p=roots[label]/tail;s=p.lstat()
        assert fmt.stamp(s)==identity
        key=(s.st_dev,s.st_ino)
        if key not in seen:total+=s.st_blocks*512;seen.add(key)
    return total


def match_source(roots,wanted,identities,links,guard,allow_root_ctime=False):
    actual,now,_,access=fmt.manifest(roots,guard,links)
    actual['roots']=wanted['roots'];assert actual==wanted and not access,'original full manifest changed'
    for path,before in identities.items():
        current=now[path]
        if allow_root_ctime and '/' not in path:
            assert current[:7]+current[8:]==before[:7]+before[8:]
        else:assert current==before,'original race witness changed: '+path
    return now


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--oracle-hostname',required=True);p.add_argument('--include-legacy',action='store_true');args=p.parse_args()
    if sys.flags.optimize:
        raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename==args.oracle_hostname
    out=args.output;assert out.is_absolute() and out.parent==OUTPUT_PARENT and out.name not in ('','.','..')
    assert OUTPUT_PARENT.parent.resolve()==OUTPUT_PARENT.parent
    os.umask(0o077);OUTPUT_PARENT.mkdir(mode=0o700,exist_ok=True);assert OUTPUT_PARENT.resolve()==OUTPUT_PARENT
    out.mkdir(mode=0o700,exist_ok=False)
    roots=dict(ROOTS)
    if args.include_legacy:roots['legacy']=LEGACY
    initial_free=shutil.disk_usage('/').free;started=time.monotonic();token=uuid.uuid4().hex
    remote_root=transport.WIN_PARENT+'\\pinkha-root-closed-builds-20261127-'+token
    result={'protocol':'pinkha-closed-native-build-offhost-custody-v1','status':'RUNNING','token':token,
            'windowsHost':transport.WIN_HOST,'windowsRoot':remote_root,'roots':{k:str(v) for k,v in roots.items()},
            'commands':[],'errors':[],'quarantines':{},'retiredRoots':[],
            'compilerRuns':0,'nativeRuns':0,'accountOpens':0,'historicalReruns':0,'currentSourceMoves':0,
            'originalAbsolutePathsRemainAvailableAfterRetirement':False,'uniqueBytesLost':0,
            'resourcePolicy':{'recoveryOnly':True,'rootEmergencyFreeBytes':256*MIB,'ownedRootOutputCapBytes':16*MIB,
                'allLargeNewBytesOnWindowsOnly':True,'windowsFreeReserveBytes':2*1024**3,
                'nativeCompilerRootFloorUnchanged':2*1024**3,'nativeCompilerDevelopmentFloorUnchanged':512*MIB,
                'ambientFreeDeltasObservedButNotAttributed':True}}
    def save():
        result['seconds']=round(time.monotonic()-started,3);transport.atomic_json(out/'result.json',result)
    def guard():
        assert time.monotonic()-started<1800,'bounded recovery deadline'
        free=shutil.disk_usage('/').free;result['minimumRootFreeBytes']=min(free,result.get('minimumRootFreeBytes',free))
        result['ambientRootFreeDeltaBytes']=free-initial_free;assert free>=256*MIB,'recovery-only root emergency floor'
        assert not (out/'abort').exists(),'owned recovery abort'
        allocated=0
        for path in out.rglob('*'):
            info=path.lstat();allocated+=info.st_blocks*512
        result['ownedOutputAllocatedBytes']=allocated;assert allocated<=16*MIB,'owned root control allocation cap'
    def interrupted(*_):raise RuntimeError('owned closed-build custody interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def remote(code,label,**kwargs):return transport.ssh_stream(code,label,save,guard,result['commands'],**kwargs)
    def upload(name,source,length,digest,remaining):
        return adapter.upload_verified(transport,remote_root=remote_root,token=token,name=name,
            source=source,length=length,digest=digest,remaining=remaining,save=save,guard=guard,
            commands=result['commands'])
    try:
        guard();save()
        # Actual tiny archive/metadata and refusal controls precede full input
        # traversal and remote allocation. The previous failed local preflight
        # remains a separate retained file; this controller never rewrites it.
        result['formatRoundtrip']=fmt.tiny_roundtrip(out)
        transport.atomic_json(out/'journal-roundtrip.json',{'unicode':'בדיקת שימור','count':1})
        assert json.loads((out/'journal-roundtrip.json').read_bytes())=={'unicode':'בדיקת שימור','count':1}
        result['journalRoundtrip']=True
        result['protectedPinsBefore']={path:fmt.digest_file(path,guard) for path in PINS}
        assert result['protectedPinsBefore']==PINS
        assert Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current').resolve()==Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current')
        wanted,identities,links,access=fmt.manifest(roots,guard)
        result['firstSymlinkReadAccessObservations']=access
        result['entryCount']=len(wanted['entries']);result['hardlinkGroups']=len(wanted['hardlinkTopology'])
        result['sourceAllocatedBytes']=allocated_roots(roots,identities)
        upper=UPPER_ALLOCATED+(LEGACY_UPPER_ALLOCATED if args.include_legacy else 0)
        assert result['sourceAllocatedBytes']<=upper,'approved closed roots grew beyond measured allocation'
        result['noLiveBefore']=no_live(identities)
        transport.atomic_json(out/'source-manifest.json',wanted)
        transport.atomic_json(out/'source-race-identities.json',identities)
        # This pass compresses to a counting hash sink, never to a local file.
        # Its exact byte count determines Windows admission before dispatch.
        archive=fmt.measured_archive(roots,wanted,identities,guard);result['archive']=archive;save()
        assert archive['bytes']<=1024*MIB and archive['tarBytes']<=2*1024*MIB,'bounded measured archive'
        match_source(roots,wanted,identities,links,guard)
        result['noLiveBeforeTransfer']=no_live(identities)
        module_bytes={name:Path(__file__).with_name(name).read_bytes() for name in MODULES}
        module_pins={name:hashlib.sha256(value).hexdigest() for name,value in module_bytes.items()}
        mapping={'protocol':'pinkha-closed-native-build-restoration-v1','token':token,'windowsRoot':remote_root,
            'windowsHost':transport.WIN_HOST,'archiveName':'closed-builds.tar.gz','archive':archive,
            'manifest':wanted,'manifestSHA256':hashlib.sha256(fmt.canonical_json(wanted)).hexdigest(),
            'producerQualificationPins':PINS,'helperSHA256':module_pins,
            'restoreNeedsExclusiveOriginalPaths':True,'originalPathsUnavailableAfterRetirement':True,
            'inodeDeviceCtimeAreAuditWitnessesNotPortableMetadata':True,
            'newClientQualificationUsesSeparateRetainedCProducer':True}
        transport.atomic_json(out/'restoration-map.json',mapping)
        mapping_bytes=(out/'restoration-map.json').read_bytes()
        total=archive['bytes']+sum(map(len,module_bytes.values()))+len(mapping_bytes)+MIB
        owner=json.loads(remote(transport.ps_create(remote_root,token,total),'create-exclusive-windows-root'))
        assert owner['root']==remote_root and owner['token']==token and owner['host']==transport.WIN_HOST
        result['windowsOwner']=owner
        probe=bytes(range(256))*257+b'\x00\x1a\r\n\xffEND'
        result['rawBinaryRoundtrip']=upload('transport-probe.bin',probe,len(probe),hashlib.sha256(probe).hexdigest(),total)
        for name,data in module_bytes.items():
            with (out/name).open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            upload(name,data,len(data),module_pins[name],total)
        upload('restoration-map.json',mapping_bytes,len(mapping_bytes),hashlib.sha256(mapping_bytes).hexdigest(),total)
        source=fmt.GzipArchiveReader(roots,wanted,identities,guard)
        try:
            result['archiveAcknowledgement']=upload('closed-builds.tar.gz',source,archive['bytes'],archive['sha256'],archive['bytes']+MIB)
            assert source.rawBytes==archive['tarBytes'] and source.rawSHA256.hexdigest()==archive['tarSHA256']
        finally:source.close()
        result['firstFullStreamReadbackVerified']=True;save()
        remote(transport.ps_readback(remote_root,token,'closed-builds.tar.gz',archive['bytes']),'second-full-archive-readback',
               expected_size=archive['bytes'],expected_sha=archive['sha256'])
        result['secondFullStreamReadbackVerified']=True
        assert all(row['status']=='PASS' and row['exitCode']==0 and row['groupPositivelyAbsent'] and not row['forcedCleanup'] for row in result['commands'])
        match_source(roots,wanted,identities,links,guard);result['noLiveBeforeQuarantine']=no_live(identities)
        assert {path:fmt.digest_file(path,guard) for path in PINS}==PINS
        ready={'protocol':'pinkha-closed-native-build-remote-custody-ready-v1','archive':archive,
               'restorationMapSHA256':hashlib.sha256(mapping_bytes).hexdigest(),'allFullRemoteReadbacksVerified':True,
               'originalQualificationOutcomesUnchanged':True,'roots':mapping['manifest']['roots']}
        transport.atomic_json(out/'READY-TO-RETIRE.json',ready);ready_bytes=(out/'READY-TO-RETIRE.json').read_bytes()
        upload('READY-TO-RETIRE.json',ready_bytes,len(ready_bytes),hashlib.sha256(ready_bytes).hexdigest(),MIB)
        quarantines={}
        for label,root in roots.items():
            guard();destination=root.with_name(root.name+'.verified-offhost-'+token)
            assert not destination.exists() and not destination.is_symlink()
            transport.rename_exclusively(root,destination);fmt.fsync_dir(root.parent)
            quarantines[label]=destination;result['quarantines'][label]=str(destination);save()
        match_source(quarantines,wanted,identities,links,guard,allow_root_ctime=True)
        result['noLiveAfterQuarantine']=no_live(identities);save()
        # No recursive wildcard deletion: only exact manifest entries from the
        # atomically captured, fully verified remote duplicate are retired.
        for label in roots:
            guard();rows=[row for row in wanted['entries'] if row['path']==label or row['path'].startswith(label+'/')]
            for row in sorted(rows,key=lambda r:len(Path(r['path']).parts),reverse=True):
                _,_,tail=row['path'].partition('/');path=quarantines[label]/tail;info=path.lstat();prior=identities[row['path']]
                assert [info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid]==prior[:5]
                if row['kind']=='directory':path.rmdir()
                else:
                    assert info.st_size==row['bytes'] and info.st_mtime_ns==row['mtimeNS']
                    if row['kind']=='file':assert fmt.digest_file(path,guard)==row['sha256']
                    path.unlink()
            fmt.fsync_dir(roots[label].parent);result['retiredRoots'].append(label);save()
        assert {path:fmt.digest_file(path,guard) for path in PINS}==PINS
        result['status']='PASS_EXACT_CLOSED_BUILDS_OFFHOST_CUSTODY_ORIGINAL_PATHS_REQUIRE_RESTORE'
    except BaseException as error:
        result['status']='FAIL_SOURCE_OR_VERIFIED_REMOTE_CUSTODY_RETAINED'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        result['allOwnedSSHGroupsAbsent']=all(row.get('groupPositivelyAbsent') is True for row in result['commands'])
        result['ownedSSHDispatchCount']=sum(1 for row in result['commands'] if row.get('pid') is not None)
        final_pins={}
        for path,pin in PINS.items():
            try:final_pins[path]=fmt.digest_file(path)
            except BaseException as diagnostic:
                result['errors'].append({'phase':'protected-pin-final-check','path':path,
                    'type':type(diagnostic).__name__,'message':str(diagnostic)})
        result['protectedPinsAfter']=final_pins
        result['protectedPinsAfterEqual']=final_pins==PINS
        if not result['allOwnedSSHGroupsAbsent'] or not result['protectedPinsAfterEqual']:
            result['status']='FAIL_FINAL_LIFECYCLE_OR_PROTECTED_PIN_CHECK'
        result['rootFreeAfter']=shutil.disk_usage('/').free;result['developmentFreeAfter']=shutil.disk_usage('/mnt/development').free
        result['completedUTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    print(json.dumps({key:result.get(key) for key in ('status','seconds','errors','archive','entryCount','retiredRoots','rootFreeAfter','developmentFreeAfter')},sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
