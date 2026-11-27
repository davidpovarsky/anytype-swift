#!/usr/bin/env python3
"""Explicit restoration of exact closed build roots from verified Windows custody.

Requires empty original paths, a caller-pinned restoration map, enough measured
local space and the complete matching helper bundle. It never overwrites a
replacement cache or deletes current products. A partial failure retains its
download/staging and any already installed exact roots for reconciliation.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import uuid

MIB=1024**2
ALLOWED={'indexed':'/tmp/pinkha-w1-engine-contracts-indexed-20261127',
         'cache':'/tmp/pinkha-w1-engine-contracts-cache-20261127',
         'legacy':'/var/lib/pinkha-root-t2-linux-20261126/build1/legacy'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',type=Path,required=True);parser.add_argument('--mapping-sha256',required=True)
    parser.add_argument('--oracle-hostname',required=True);args=parser.parse_args()
    if sys.flags.optimize:
        raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename==args.oracle_hostname
    assert args.mapping.is_absolute() and args.mapping.parent.resolve()==args.mapping.parent and not args.mapping.is_symlink()
    with os.fdopen(os.open(args.mapping,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as stream:mapping_bytes=stream.read(16*MIB+1)
    assert len(mapping_bytes)<=16*MIB and hashlib.sha256(mapping_bytes).hexdigest()==args.mapping_sha256
    mapping=json.loads(mapping_bytes);assert mapping['protocol']=='pinkha-closed-native-build-restoration-v1'
    expected_helpers={'offhost_root_swift_caches.py','restore_offhost_root_swift_caches.py',
                      'root_swift_archive_format.py','root_swift_archive_transport.py','frozen_sftp_custody_adapter.py'}
    assert set(mapping['helperSHA256'])==expected_helpers,'exact restore helper set required'
    # Authenticate support code before import/execution, using only the bounded
    # caller-pinned map and Python standard library. A changed helper cannot
    # perform a side effect before its mismatch is discovered.
    for name,pin in mapping['helperSHA256'].items():
        path=Path(__file__).with_name(name);assert not path.is_symlink()
        with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as stream:data=stream.read(MIB+1)
        assert len(data)<=MIB and hashlib.sha256(data).hexdigest()==pin,'restore helper bundle differs'
    import root_swift_archive_format as fmt
    import root_swift_archive_transport as transport
    assert mapping['windowsHost']==transport.WIN_HOST
    token=mapping['token'];assert len(token)==32 and all(c in '0123456789abcdef' for c in token)
    remote_root=mapping['windowsRoot'];assert remote_root==transport.WIN_PARENT+'\\pinkha-root-closed-builds-20261127-'+token
    wanted=mapping['manifest'];assert wanted['version']==1 and hashlib.sha256(fmt.canonical_json(wanted)).hexdigest()==mapping['manifestSHA256']
    assert set(wanted['roots']) in ({'indexed','cache'},{'indexed','cache','legacy'})
    assert all(ALLOWED[key]==value for key,value in wanted['roots'].items())
    roots={key:Path(value) for key,value in wanted['roots'].items()}
    for key,path in roots.items():
        assert path.parent.resolve()==path.parent and not path.exists() and not path.is_symlink(),'original path is occupied; never overwrite it'
    archive=mapping['archive'];assert archive['encoding']=='gzip-level-1-tar-pax'
    assert 0<archive['bytes']<=1024*MIB and 0<archive['tarBytes']<=2*1024*MIB
    block=os.statvfs('/tmp').f_frsize
    allocation=sum(((row['bytes']+block-1)//block)*block if row['kind']=='file' else block for row in wanted['entries'])
    assert allocation<=2*1024*MIB
    required=2*1024**3+allocation+archive['bytes']+128*MIB
    assert shutil.disk_usage('/').free>=required,'measured full restoration root reserve'
    assert shutil.disk_usage('/mnt/development').free>=512*MIB,'unchanged development floor'
    os.umask(0o077)
    out=Path('/tmp')/('pinkha-root-closed-build-restore-'+token[:8]+'-'+uuid.uuid4().hex)
    out.mkdir(mode=0o700,exist_ok=False);stage=out/'stage';stage.mkdir(mode=0o700)
    assert all(path.parent.stat().st_dev==stage.stat().st_dev for path in roots.values()),'atomic install requires original filesystem'
    started=time.monotonic();result={'protocol':'pinkha-closed-native-build-restore-v1','status':'RUNNING',
        'mappingSHA256':args.mapping_sha256,'windowsRoot':remote_root,'commands':[],'installedRoots':[],
        'errors':[],'compilerRuns':0,'nativeRuns':0,'accountOpens':0,'originalPathOverwrites':0,
        'requiredRootFreeAtAdmission':required,'output':str(out),'archive':archive}
    def save():result['seconds']=round(time.monotonic()-started,3);transport.atomic_json(out/'result.json',result)
    def guard():
        assert time.monotonic()-started<1800,'bounded restore deadline'
        assert shutil.disk_usage('/').free>=2*1024**3,'unchanged root floor during restore'
        assert shutil.disk_usage('/mnt/development').free>=512*MIB,'unchanged development floor during restore'
        assert not (out/'abort').exists(),'owned restore abort'
    def interrupted(*_):raise RuntimeError('owned restore interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    try:
        save();guard();download=out/'closed-builds.tar.gz'
        transport.ssh_stream(transport.ps_readback(remote_root,token,mapping['archiveName'],archive['bytes']),
            'full-archive-restore-readback',save,guard,result['commands'],expected_size=archive['bytes'],
            expected_sha=archive['sha256'],destination=download)
        result['downloadSHA256']=fmt.digest_file(download,guard);assert result['downloadSHA256']==archive['sha256']
        raw_digest=hashlib.sha256();raw_length=0
        with fmt.read_file(download) as source, gzip.GzipFile(fileobj=source,mode='rb') as uncompressed:
            while data:=uncompressed.read(MIB):
                guard();raw_length+=len(data);assert raw_length<=archive['tarBytes'];raw_digest.update(data)
        assert raw_length==archive['tarBytes'] and raw_digest.hexdigest()==archive['tarSHA256']
        with fmt.read_file(download) as source:
            identities,links=fmt.extract_stream(source,stage,wanted,guard)
        result['completeArchiveAndEntryManifestVerified']=True;save()
        # Both roots are fully restored and verified before installing either.
        # RENAME_NOREPLACE is the final race fence, even if a new cache appears
        # after the preliminary absence checks. Partial installs stay recorded.
        for label,path in roots.items():
            guard();assert not path.exists() and not path.is_symlink()
            transport.rename_exclusively(stage/label,path);fmt.fsync_dir(path.parent)
            result['installedRoots'].append(label);save()
        actual,_,_,access=fmt.manifest(roots,guard,links)
        assert actual==wanted and not access,'installed full manifest differs'
        assert all(row['status']=='PASS' and row['groupPositivelyAbsent'] and not row['forcedCleanup'] and row['exitCode']==0 for row in result['commands'])
        result['status']='PASS_EXACT_ORIGINAL_CLOSED_BUILD_PATHS_RESTORED'
        result['archiveRetainedForAudit']=str(download)
    except BaseException as error:
        result['status']='FAIL_RESTORE_STAGING_AND_ANY_EXACT_INSTALLED_ROOTS_RETAINED'
        result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        result['rootFreeAfter']=shutil.disk_usage('/').free;result['completedUTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());save()
    print(json.dumps({key:result.get(key) for key in ('status','seconds','errors','installedRoots','output','rootFreeAfter')},sort_keys=True))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':raise SystemExit(main())
