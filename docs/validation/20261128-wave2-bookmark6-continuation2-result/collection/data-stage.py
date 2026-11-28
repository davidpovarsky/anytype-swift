import os, stat, json, hashlib, base64, gzip, sys, shutil
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
ARCH = Path('/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-continuation2-actual-6da55ee2.json.gz')
OUT = Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-continuation2-result-20261128')
FILES = {'command.json','process.json','receipt.json','resource-samples.json','immutable-witness-before.json','immutable-witness-after.json','immutable-witness-final.json','stdout.original.log','stderr.original.log'}
def digest(raw): return hashlib.sha256(raw).hexdigest()
def identity(s): return {k:getattr(s,'st_'+k) for k in ('dev','ino','mode','uid','gid','nlink','size','mtime_ns','ctime_ns')}
def read_fixed(path, maximum):
    assert path.resolve(strict=True) == path and not path.is_symlink()
    fd=os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        a=os.fstat(fd); assert stat.S_ISREG(a.st_mode) and a.st_size <= maximum
        with os.fdopen(fd,'rb',closefd=False) as f: raw=f.read(maximum+1)
        z=os.fstat(fd)
        assert len(raw)==a.st_size and identity(a)==identity(z)==identity(path.stat())
        return raw,identity(z)
    finally: os.close(fd)
def put(relative, raw):
    p=OUT/relative
    assert p.is_relative_to(OUT) and '..' not in p.parts
    p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with p.open('xb') as f: f.write(raw)
    os.chmod(p,0o600)
    return {'path':relative,'bytes':len(raw),'sha256':digest(raw),'gitBlob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
archive,_=read_fixed(ARCH,200000)
assert len(archive)==131758 and digest(archive)=='6da55ee22dd25cefd861eca3fbc8765eeaf0c4124620c645dd2d2af565c05cbc'
raw=gzip.decompress(archive)
assert len(raw)==685217 and digest(raw)=='5f37b8703eaaabf50cb31004f7955aabac9a43060fd637e5c8bc70eb110e22b4'
bundle=json.loads(raw)
assert bundle['status']=='ALL_NINE_CONTINUATION_ORIGINALS_COLLECTED' and not bundle['collectionIssues']
assert bundle['originalRoot']==str(ROOT/'continuation2') and {r['path'] for r in bundle['entries']}==FILES
originals=[]
for row in bundle['entries']:
    body=base64.b64decode(row['contentBase64'],validate=True)
    assert len(body)==row['bytes'] and digest(body)==row['sha256']
    current,current_stat=read_fixed(ROOT/'continuation2'/row['path'],2*1024**2)
    assert current==body and current_stat==row['statAfterPath']
    originals.append((row['path'],body))
assert sum(len(b) for _,b in originals)==506150
job_raw=base64.b64decode(bundle['completedJob']['contentBase64'],validate=True)
assert len(job_raw)==bundle['completedJob']['bytes'] and digest(job_raw)==bundle['completedJob']['sha256']
job=json.loads(job_raw); assert job['ok'] and job['job']['id']=='job_0c6933032622' and job['job']['status']=='succeeded' and job['job']['exit_code']==0
metadata=json.loads(sys.argv[1])
allowed={'actual-notification-tool.json','actual-dispatch.json','dispatch-spec.json','source-upload-result.json','root-phase-coordination.json','terminal-notice.json','archive-upload-result.json','coordination-context.json'}
assert set(metadata)==allowed and sum(len(v.encode('utf-8')) for v in metadata.values()) < 131072
assert all(isinstance(v,str) for v in metadata.values())
for v in metadata.values(): json.loads(v)
assert not OUT.exists() and not OUT.is_symlink()
assert OUT.parent.resolve(strict=True)==OUT.parent
free_before={'root':shutil.disk_usage('/').free,'development':shutil.disk_usage('/mnt/development').free}
assert free_before['root']>=2*1024**3 and free_before['development']>=512*1024**2+4*1024**2
OUT.mkdir(mode=0o700)
index=[]
for name,body in originals: index.append(put('original-continuation2/'+name,body))
index.append(put('custody/actual-completed-job.original.json',job_raw))
for name,body in metadata.items(): index.append(put('custody/'+name,body.encode('utf-8')))
index.append(put('transport/original-collection.json.gz',archive))
index.append(put('transport/original-collection.json',raw))
receipt={'schema':'pinkha-continuation2-data-stage/v1','status':'PASS_EXACT_DATA_ONLY_STAGING','atUTC':datetime.now(timezone.utc).isoformat(),'root':str(OUT),'originalRoot':str(ROOT/'continuation2'),'originalFiles':9,'originalBytes':506150,'originalBodyAndRecordedPhysicalIdentityMatched':True,'sourceArchiveSHA256':digest(archive),'rawCollectionSHA256':digest(raw),'metadataRepresentation':'Exact captured tool response objects serialized to JSON by root; coordination-context is newly derived and labeled. Completed-job raw body is exact from the original collected transport.','files':index,'freeBefore':free_before,'freeAfter':{'root':shutil.disk_usage('/').free,'development':shutil.disk_usage('/mnt/development').free},'childCommands':0,'tests':0,'compiler':0,'nativeCalls':0,'processQueries':0,'signals':0,'originalWrites':0,'atimePreservationClaim':False}
encoded=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
item=put('stage-receipt.json',encoded)
print(json.dumps({'receipt':receipt,'receiptIdentity':item},sort_keys=True))
