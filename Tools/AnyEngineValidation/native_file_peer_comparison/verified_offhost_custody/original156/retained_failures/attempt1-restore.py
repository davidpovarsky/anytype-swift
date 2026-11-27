#!/usr/bin/env python3
"""Exclusively restore the exact original156 compressed archive; do not extract."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,os,shutil,signal,sys,time,uuid


def digest(path):
    h=hashlib.sha256()
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as f:
        for part in iter(lambda:f.read(1024**2),b''):h.update(part)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map',type=Path,required=True);parser.add_argument('--map-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--oracle-hostname',required=True)
    args=parser.parse_args()
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename==args.oracle_hostname
    assert args.map.is_absolute() and args.map.name=='restoration-map.json' and args.map.parent.resolve()==args.map.parent
    assert str(args.map).startswith('/var/lib/pinkha-w1-original156-retirement-20261127/')
    assert len(args.map_sha256)==64 and digest(args.map)==args.map_sha256
    with os.fdopen(os.open(args.map,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as f:manifest=json.load(f)
    assert manifest['protocol']=='original156-compressed-archive-exclusive-restoration-v1'
    controller=args.map.with_name('original156_duplicate_retirement.py')
    assert digest(controller)==manifest['controllerSHA256'] and digest(Path(__file__))==manifest['restoreHelperSHA256']
    spec=importlib.util.spec_from_file_location('original156_custody',controller)
    custody=importlib.util.module_from_spec(spec);sys.dont_write_bytecode=True;spec.loader.exec_module(custody)
    module=custody.load_primitives(args.map.parent)
    assert manifest['primitivesSHA256']==custody.PRIMITIVE_SHA
    assert manifest['source']==str(custody.SOURCE) and manifest['bytes']==custody.SIZE and manifest['sha256']==custody.SHA
    assert manifest['windowsArchive']==custody.WINDOWS_ARCHIVE and manifest['windowsHost']=='DAVID_AND_GOLDY'
    assert manifest['reviewedProofSHA256']==custody.PROOF_SHA and manifest['protectedControlPins']==custody.CONTROL_PINS
    assert manifest['nativePins']==module.PINS and manifest['originalArchivePathUnavailableAfterRetirement'] is True
    source=custody.SOURCE;assert source.parent.is_dir() and not source.parent.is_symlink() and source.parent.resolve()==source.parent
    out=args.output;assert out.is_absolute() and str(out).startswith(custody.OUT_ROOT) and out.parent.resolve()==out.parent and out!=args.map.parent
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();tmp=source.with_name(source.name+'.restore-'+uuid.uuid4().hex)
    result={'protocol':'original156-exclusive-compressed-archive-restoration-v1','status':'RUNNING','source':str(source),'bytes':custody.SIZE,'sha256':custody.SHA,'restorationMapSHA256':args.map_sha256,'temporaryPath':str(tmp),'commands':[],'errors':[],'installed':False,'existingWindowsWriteOperations':0,'archiveExtractions':0,'accountOpens':0,'nativeRuns':0,'compilerRuns':0}
    def save():result['seconds']=round(time.monotonic()-started,3);module.atomic_json(out/'result.json',result)
    def guard():
        assert time.monotonic()-started<600,'bounded original156 archive restore'
        assert shutil.disk_usage('/var/lib').free>=2*1024**3,'unchanged root2GiB floor'
        assert shutil.disk_usage('/mnt/development').free>=512*1024**2,'unchanged development512MiB floor'
        assert not (out/'abort').exists()
        assert sum(p.stat().st_blocks*512 for p in out.iterdir() if p.is_file())<=4*1024**2
    def interrupted(*_):raise RuntimeError('owned original156 restoration interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def remote(code,label,**kwargs):return module.ssh_stream(code,label,save,guard,result['commands'],**kwargs)
    try:
        guard();assert shutil.disk_usage(source.parent).free>=2*1024**3+custody.SIZE+4*1024**2
        assert not os.path.lexists(source),'existing compressed archive is never overwritten'
        result['protectedControlsBefore']=custody.protected_controls(module)
        result['nativePinsBefore']={p:module.sha_file(p) for p in module.PINS};assert result['nativePinsBefore']==module.PINS;save()
        info=json.loads(remote(custody.existing_info(module),'inspect-existing-windows-archive'));custody.validate_info(info);result['existingWindowsBefore']=info
        remote(custody.existing_readback(module),'restore-full-existing-windows-archive',expected_size=custody.SIZE,expected_sha=custody.SHA,destination=tmp)
        after=json.loads(remote(custody.existing_info(module),'verify-existing-windows-archive-unchanged'));custody.validate_info(after);assert after==info
        result['existingWindowsAfter']=after;result['existingWindowsMetadataUnchanged']=True
        assert module.sha_file(tmp)==custody.SHA and tmp.stat().st_size==custody.SIZE
        expected=manifest['sourceMetadata'];assert expected['bytes']==custody.SIZE and expected['links']==1
        os.chown(tmp,expected['uid'],expected['gid'],follow_symlinks=False)
        os.chmod(tmp,expected['mode'],follow_symlinks=False)
        for name in os.listxattr(tmp,follow_symlinks=False):
            if name not in expected['xattrs']:os.removexattr(tmp,name,follow_symlinks=False)
        for name,value in expected['xattrs'].items():os.setxattr(tmp,name,base64.b64decode(value,validate=True),follow_symlinks=False)
        os.utime(tmp,ns=(expected['atime_ns'],expected['mtime_ns']),follow_symlinks=False)
        fd=os.open(tmp,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
        try:os.fsync(fd)
        finally:os.close(fd)
        fields=('bytes','mode','uid','gid','atime_ns','mtime_ns','xattrs','links')
        actual=module.metadata(tmp);assert all(actual[k]==expected[k] for k in fields)
        assert module.sha_file(tmp)==custody.SHA
        assert {p:module.sha_file(p) for p in module.PINS}==module.PINS
        assert custody.protected_controls(module)==result['protectedControlsBefore']
        assert all(x['status']=='PASS' and x['exitCode']==0 and x['groupPositivelyAbsent'] and not x['forcedCleanup'] for x in result['commands'])
        guard();assert not os.path.lexists(source) and source.parent.resolve()==source.parent
        result['installStage']='exclusive-link-intent';save()
        module.install_exclusively(tmp,source)
        result.update(installed=True,installStage='exclusive-install-complete');save()
        assert module.sha_file(source)==custody.SHA
        result['restoredMetadata']=module.metadata(source);assert all(result['restoredMetadata'][k]==expected[k] for k in fields)
        result['status']='PASS_ORIGINAL156_COMPRESSED_ARCHIVE_RESTORED_EXCLUSIVELY_NO_EXTRACTION'
    except BaseException as error:
        result['status']='FAIL_ORIGINAL156_EXCLUSIVE_RESTORE';result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        try:
            result['protectedControlsAfter']=custody.protected_controls(module);assert result['protectedControlsAfter']==result.get('protectedControlsBefore')
            result['nativePinsFinal']={p:module.sha_file(p) for p in module.PINS};assert result['nativePinsFinal']==module.PINS
        except BaseException as error:
            result['status']='FAIL_ORIGINAL156_EXCLUSIVE_RESTORE';result['errors'].append({'type':type(error).__name__,'message':'final controls/native pins: '+str(error)})
        result['allOwnedSSHGroupsAbsent']=all(x.get('groupPositivelyAbsent') for x in result['commands'])
        if not result['allOwnedSSHGroupsAbsent']:result['status']='FAIL_ORIGINAL156_EXCLUSIVE_RESTORE'
        # A failed or uncertain copy/install preserves its partial temporary
        # file and any destination. The existing Windows archive is never edited.
        result['temporaryPathPresent']=os.path.lexists(tmp);result['originalPathPresent']=os.path.lexists(source);save()
    print(json.dumps({'status':result['status'],'receipt':str(out/'result.json'),'sha256':module.sha_file(out/'result.json'),'seconds':result['seconds']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__':raise SystemExit(main())
