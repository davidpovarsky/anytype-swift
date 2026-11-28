import os,stat,hashlib,json,time,datetime
from pathlib import Path
p=Path('/mnt/development/projects/evidence/pinkha-c-crypto-producer-20261127/observation3/result.json')
expected=1504181;sha='d93433b85ab53b941cde27af52d3612d21b2a93af3d5e838cff2126607f3af17'
began=time.monotonic();assert p.resolve()==p
fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_atime_ns)
try:
 before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==expected
 out=bytearray()
 while len(out)<=expected:
  assert time.monotonic()-began<10
  b=os.read(fd,min(65536,expected+1-len(out)))
  if not b:break
  out.extend(b)
 assert len(out)==expected and hashlib.sha256(out).hexdigest()==sha
 assert identity(before)==identity(os.fstat(fd))==identity(os.lstat(p))
 data=json.loads(out);commands=data.get('currentCompilerCommands')
 result={'schema':'pinkha-current-c3-command-observation-v1','atUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'path':str(p),'bytes':len(out),'sha256':sha,'metadataUnchangedIncludingAtime':True,'currentCompilerCommands':commands,'otherTopLevelKeys':list(data),'runtimeInvocations':0,'compilerInvocations':0}
 print(json.dumps(result,sort_keys=True))
finally:os.close(fd)
