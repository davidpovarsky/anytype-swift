#!/usr/bin/env python3
"""Actual bounded transfer/exclusive-create controls; no native acceptance."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,signal,sys,time,uuid

MODULE=Path('/var/lib/pinkha-w1-offhost-custody-20261127/controllers-v3/offhost_frozen_blobs.py')
MODULE_SHA='6586c7f33defb342167fa4e31cf04fd361536d05e3b2908a2c20efe0cb357bbb'
OUT=Path('/var/lib/pinkha-w1-offhost-custody-20261127/sftp-boundary-probe1')

def main():
    if sys.flags.optimize:raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert hashlib.sha256(MODULE.read_bytes()).hexdigest()==MODULE_SHA
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_sftp_custody',MODULE)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert OUT.parent.resolve()==OUT.parent
    os.umask(0o077);OUT.mkdir(exist_ok=False)
    began=time.monotonic();token=uuid.uuid4().hex
    root=m.WIN_PARENT+'\\pinkha-frozen-e-20261127-'+token
    result={'protocol':'sftp-exclusive-upload-actual-boundary-controls-v1','status':'RUNNING',
            'moduleSHA256':MODULE_SHA,'windowsRoot':root,'token':token,'commands':[],'errors':[],
            'nativeRuns':0,'compilerRuns':0,'accountOpens':0,'existingArtifactWrites':0,'retirements':0}
    def save():
        result['seconds']=round(time.monotonic()-began,3);m.atomic_json(OUT/'result.json',result)
    def guard():
        assert time.monotonic()-began<600
        assert shutil.disk_usage('/var/lib').free>=256*1024**2
        assert not (OUT/'abort').exists()
        assert sum(p.stat().st_blocks*512 for p in OUT.iterdir() if p.is_file())<=4*1024**2
    def interrupted(*_):raise RuntimeError('owned transfer control interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def remote(code,label,**kwargs):return m.ssh_stream(code,label,save,guard,result['commands'],**kwargs)
    class ShortReader:
        def __init__(self,data):self.data=data;self.offset=0;self.closed=False
        def read(self,count):
            assert not self.closed and 0<count<=32768
            data=self.data[self.offset:self.offset+min(count,4093)];self.offset+=len(data);return data
        def close(self):self.closed=True
    reader=None
    try:
        guard();result['originalControlsBefore']=m.capture_original_controls()
        result['nativePinsBefore']={p:m.sha_file(p) for p in m.PINS};assert result['nativePinsBefore']==m.PINS
        data=bytes(range(256))*4097+b'\x00\x1a\r\n\xffEND';size=len(data);sha=hashlib.sha256(data).hexdigest()
        result['probe']={'bytes':size,'sha256':sha,'shortReadMaximumBytes':4093};assert size>1024**2
        owner=json.loads(remote(m.ps_create(root,token,size+1024**2),'create-owned-probe-root'))
        assert owner['root']==root and owner['token']==token and owner['host']==m.WIN_HOST
        name='exclusive-probe.bin';path=root+'\\'+name
        admission=json.loads(remote(m.ps_sftp_admit(root,token,name,size,size+1024**2),'admit-exclusive-probe'))
        assert admission['host']==m.WIN_HOST and admission['root']==root and admission['token']==token and admission['name']==name
        assert admission['bytes']==size and admission['destinationAbsent'] is True
        assert admission['availableFreeBytes']>=2*1024**3+size+1024**2
        reader=ShortReader(data)
        positive=m.sftp_upload(path,reader,size,sha,'positive-borrowed-short-read-upload',save,guard,result['commands'])
        assert positive['status']=='PASS' and positive['inputSHA256']==sha and positive['writeBytesAcknowledged']==size
        assert positive['exclusiveOpenConfirmed'] and positive['closeConfirmed'] and positive['openFlags']==42
        assert reader.offset==size and not reader.closed
        reader.close();result['borrowedStreamClosedOnlyByCaller']=True
        remote(m.ps_readback(root,token,name,size),'unsealed-positive-full-readback',expected_size=size,expected_sha=sha)
        code=m.ps_header(root,token)+'$p=$r+'+m.q('\\'+name)+';'
        code+="$a=[IO.File]::GetAttributes($p);if(($a-band ([IO.FileAttributes]::ReadOnly -bor [IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Directory))-ne 0){throw 'probe must be an ordinary writable file'};"
        code+="$f=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);try{$n=$f.Length}finally{$f.Dispose()};"
        code+="[Console]::Out.WriteLine((@{host=[Environment]::MachineName;bytes=$n;readOnly=$false;canOpenExistingForWrite=$true;bytesWritten=0}|ConvertTo-Json -Compress))"
        writable=json.loads(remote(m.ps_wrap(code),'prove-existing-probe-writable-before-refusal'))
        assert writable['host']==m.WIN_HOST and writable['bytes']==size and writable['readOnly'] is False
        assert writable['canOpenExistingForWrite'] is True and writable['bytesWritten']==0
        forbidden=b'SHOULD_NEVER_BE_WRITTEN'
        failed=False;negative_index=len(result['commands'])
        try:
            m.sftp_upload(path,forbidden,len(forbidden),hashlib.sha256(forbidden).hexdigest(),
                          'expected-existing-writable-file-refusal',save,guard,result['commands'])
        except RuntimeError as error:
            failed=True;result['expectedRefusalException']=str(error)
        assert failed and len(result['commands'])==negative_index+1
        negative=result['commands'][negative_index]
        assert negative['status']=='FAIL' and negative['lastServerError']['requestId']==1
        assert negative['lastServerError']['code']==4,'SFTPv3 existing-file refusal must be the correlated OPEN failure'
        assert negative['sourceBytesRead']==negative['writeBytesAcknowledged']==negative['writeStatusesAcknowledged']==0
        assert not negative.get('exclusiveOpenConfirmed',False) and negative['groupPositivelyAbsent'] and not negative['forcedCleanup']
        assert negative['exitCode']==0
        result['expectedRefusalCommandIndex']=negative_index
        remote(m.ps_readback(root,token,name,size),'post-refusal-exact-original-readback',expected_size=size,expected_sha=sha)
        sealed=json.loads(remote(m.ps_sftp_seal(root,token,name,size,sha),'flush-and-seal-verified-probe'))
        assert sealed['host']==m.WIN_HOST and sealed['root']==root and sealed['token']==token and sealed['name']==name
        assert sealed['bytes']==size and sealed['sha256']==sha and sealed['flushToDisk'] is True
        assert sealed['sealedClosedSFTPFile'] is True and sealed['readOnly'] is True
        result['sealedAcknowledgement']=sealed
        remote(m.ps_readback(root,token,name,size),'sealed-full-readback',expected_size=size,expected_sha=sha)
        assert all(i==negative_index or (r['status']=='PASS' and r['exitCode']==0 and not r['forcedCleanup']) for i,r in enumerate(result['commands']))
        result['status']='PASS_ACTUAL_SFTP_BORROWED_STREAM_AND_EXCLUSIVE_EXISTING_WRITABLE_FILE_REFUSAL'
    except BaseException as error:
        result['status']='FAIL_SFTP_BOUNDARY_CONTROLS';result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        if reader is not None and not reader.closed:reader.close()
        try:
            result['originalControlsAfter']=m.capture_original_controls()
            assert result['originalControlsAfter']==result.get('originalControlsBefore')
            result['nativePinsAfter']={p:m.sha_file(p) for p in m.PINS};assert result['nativePinsAfter']==m.PINS
        except BaseException as error:
            result['status']='FAIL_SFTP_BOUNDARY_CONTROLS';result['errors'].append({'type':type(error).__name__,'message':'original integrity: '+str(error)})
        result['allOwnedSSHGroupsAbsent']=all(r.get('groupPositivelyAbsent') for r in result['commands'])
        if not result['allOwnedSSHGroupsAbsent']:result['status']='FAIL_SFTP_BOUNDARY_CONTROLS'
        save()
    print(json.dumps({'status':result['status'],'receipt':str(OUT/'result.json'),'sha256':m.sha_file(OUT/'result.json'),'seconds':result['seconds']}))
    return 0 if result['status'].startswith('PASS') else 1

if __name__=='__main__':raise SystemExit(main())
