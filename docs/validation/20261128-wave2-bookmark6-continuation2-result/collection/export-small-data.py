import os,stat,hashlib,json,sys,base64
from pathlib import Path
root=Path('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-continuation2-result-20261128')
spec=json.loads(sys.argv[1]);rows=[]
def ident(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
assert sum(r['bytes'] for r in spec)<45000
for row in spec:
 p=root/row['path'];assert '..' not in Path(row['path']).parts and not Path(row['path']).is_absolute()
 a=os.lstat(p);assert stat.S_ISREG(a.st_mode);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  assert ident(a)==ident(os.fstat(fd));b=b''
  while True:
   q=os.read(fd,65536)
   if not q:break
   b+=q;assert len(b)<=45000
  assert ident(a)==ident(os.fstat(fd))==ident(os.lstat(p))
 finally:os.close(fd)
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['gitBlob']
 rows.append(dict(row,base64=base64.b64encode(b).decode()))
print(json.dumps({'status':'PASS_EXACT_SMALL_DATA_EXPORT','files':rows,'children':0,'writes':0,'processQueries':0,'signals':0,'atimePreservationClaim':False},separators=(',',':')))
