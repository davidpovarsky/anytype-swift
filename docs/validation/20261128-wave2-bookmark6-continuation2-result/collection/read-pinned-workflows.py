import os,stat,hashlib,json,sys
from pathlib import Path
spec=json.loads(sys.argv[1]); base=Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
rows=[]
def ident(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
for row in spec:
 p=base/row['path']; a=os.lstat(p); assert stat.S_ISREG(a.st_mode) and not stat.S_ISLNK(a.st_mode)
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  assert ident(a)==ident(os.fstat(fd)); b=b''
  while True:
   q=os.read(fd,65536)
   if not q:break
   b+=q
   assert len(b)<=1048576
  assert ident(a)==ident(os.fstat(fd))==ident(os.lstat(p))
 finally:os.close(fd)
 sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert len(b)==row['bytes'] and sha==row['gitBlob'],row['path']
 lines=b.decode().splitlines(); section=[]; active=False
 for line in lines:
  if not active and line.startswith(('on:',"'on':",'"on":')):active=True
  elif active and line and not line[0].isspace() and not line.startswith('#'):break
  if active:section.append(line)
 rows.append({'path':row['path'],'bytes':len(b),'gitBlob':sha,'onSection':'\n'.join(section)})
print(json.dumps({'status':'PASS_EXACT_WORKFLOW_PRIMARY_READ','files':rows,'filesRead':len(rows),'children':0,'writes':0,'processQueries':0,'signals':0,'atimePreservationClaim':False},separators=(',',':')))
