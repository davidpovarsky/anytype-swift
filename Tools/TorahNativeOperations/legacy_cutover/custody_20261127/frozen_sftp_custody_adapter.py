"""Narrow caller adapter for the frozen 6586 custody transport.

Callers own supplied readable producers and must close them in their own
finally block. This adapter never closes them, retries an upload, or deletes
an existing destination/partial. The transport module must be hash-pinned
before import as part of the caller's complete helper set.
"""
from pathlib import Path
import hashlib,json,os

TRANSPORT_SHA256='6586c7f33defb342167fa4e31cf04fd361536d05e3b2908a2c20efe0cb357bbb'


def upload_verified(transport,*,remote_root,token,name,source,length,digest,remaining,save,guard,commands):
    path=Path(transport.__file__)
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest()==TRANSPORT_SHA256
    def remote(code,label,**kwargs):
        return transport.ssh_stream(code,label,save,guard,commands,**kwargs)
    admitted=json.loads(remote(transport.ps_sftp_admit(remote_root,token,name,length,remaining),'admit-sftp-'+name))
    assert admitted['host']==transport.WIN_HOST and admitted['root']==remote_root and admitted['token']==token and admitted['name']==name
    assert admitted['bytes']==length and admitted['destinationAbsent'] is True
    assert admitted['availableFreeBytes']>=2*1024**3+remaining
    sent=transport.sftp_upload(remote_root+'\\'+name,source,length,digest,'sftp-upload-'+name,save,guard,commands)
    assert sent['status']=='PASS' and sent['exclusiveOpenConfirmed'] and sent['openFlags']==42 and sent['closeConfirmed']
    assert sent['inputBytes']==sent['writeBytesAcknowledged']==length and sent['inputSHA256']==digest
    ack=json.loads(remote(transport.ps_sftp_seal(remote_root,token,name,length,digest),'flush-and-seal-'+name))
    assert ack['host']==transport.WIN_HOST and ack['root']==remote_root and ack['token']==token and ack['name']==name
    assert ack['bytes']==length and ack['sha256']==digest and ack['flushToDisk'] is True and ack['sealedClosedSFTPFile'] is True and ack['readOnly'] is True
    ack.update(createNew=True,creationTransport='sftp-v3',exclusiveOpenFlags=42,sftpCloseConfirmed=True)
    remote(transport.ps_readback(remote_root,token,name,length),'readback-'+name,expected_size=length,expected_sha=digest)
    return ack
