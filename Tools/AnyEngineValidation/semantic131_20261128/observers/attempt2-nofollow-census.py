import os,stat,hashlib,json,resource,signal,time,datetime
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
signal.alarm(18)
root=Path('/run/pinkha-e-swift-semantic131-20261128-attempt2')
start=time.monotonic()
def need(x,m):
 if not x: raise RuntimeError(m)
def ident(s):
 return [s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_atime_ns]
def stable(s):
 return ident(s)[:-1]
def guard():
 need(time.monotonic()-start<15,'bounded read deadline')
need(root.resolve()==root and root.parent.resolve()==root.parent and not root.is_symlink(),'physical declared output')
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
rootstat=os.fstat(fd)
need(rootstat.st_dev==os.stat('/run').st_dev and stat.S_IMODE(rootstat.st_mode)==0o700 and rootstat.st_uid==os.geteuid(),'owned tmpfs output')
result={'schema':'pinkha-semantic131-attempt2-failure-nofollow-observation-v1','startedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root':str(root),'rootIdentityBefore':ident(rootstat),'entries':0,'directories':0,'regularFiles':0,'allocatedBytes':rootstat.st_blocks*512,'anomalies':[],'rootNames':[],'selectedFiles':{},'errors':[],'compilerInvocations':0,'nativeInvocations':0,'historicalProcessReprobes':0,'outputsRemoved':False,'linksFollowed':False}
def walk(dfd,rel,depth):
 guard();need(depth<=12,'depth')
 entries=[]
 with os.scandir(dfd) as it:
  for ent in it:
   guard();need(result['entries']<4096,'entries')
   result['entries']+=1;entries.append(ent.name)
 for name in sorted(entries):
  guard();s=os.stat(name,dir_fd=dfd,follow_symlinks=False);p=(rel+'/'+name).lstrip('/')
  if not rel:result['rootNames'].append(name)
  result['allocatedBytes']+=s.st_blocks*512
  need(s.st_dev==rootstat.st_dev,'output device')
  if stat.S_ISDIR(s.st_mode):
   result['directories']+=1
   cfd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dfd)
   try:
    need(stable(os.fstat(cfd))==stable(s),'directory descriptor')
    walk(cfd,p,depth+1)
    need(stable(os.fstat(cfd))==stable(os.stat(name,dir_fd=dfd,follow_symlinks=False)),'directory remained')
   finally:os.close(cfd)
  else:
   if stat.S_ISREG(s.st_mode):result['regularFiles']+=1
   if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:
    row={'relativePath':p,'identity':ident(s),'allocatedBytes':s.st_blocks*512}
    if stat.S_ISLNK(s.st_mode):row['linkText']=os.readlink(name,dir_fd=dfd)
    result['anomalies'].append(row)
try:
 walk(fd,'',0)
 for rel,cap in [('terminal-persistence-failure.json',4096),('result.json',98304),('commands/01-TorahInspectorCore-typecheck/original.log',65536),('commands/01-TorahInspectorCore-typecheck/result.json',65536),('commands/01-TorahInspectorCore-typecheck/receipt.json',65536)]:
  guard();p=root/rel
  if not os.path.lexists(p):result['selectedFiles'][rel]={'absent':True};continue
  q=root
  for part in Path(rel).parts[:-1]:
   q=q/part;need(q.is_dir() and not q.is_symlink() and q.resolve()==q,'physical selected parents')
  f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
  try:
   before=os.fstat(f);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'regular selected evidence')
   need(ident(before)==ident(p.lstat()),'selected path identity')
   if before.st_size>cap:
    result['selectedFiles'][rel]={'bytes':before.st_size,'identity':ident(before),'notReadBecauseAboveReturnCap':True};continue
   raw=b''
   while len(raw)<=cap:
    guard();part=os.read(f,min(65536,cap+1-len(raw)))
    if not part:break
    raw+=part
   need(len(raw)==before.st_size and len(raw)<=cap,'selected bounded bytes')
   need(ident(os.fstat(f))==ident(before)==ident(p.lstat()),'selected unchanged')
   result['selectedFiles'][rel]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'identity':ident(before),'raw':raw.decode('utf-8')}
  finally:os.close(f)
 need(stable(os.fstat(fd))==stable(rootstat)==stable(root.lstat()),'same owned root')
 result['status']='PASS_BOUNDED_FAILURE_OBSERVATION_NOT_SEMANTIC_ACCEPTANCE'
except BaseException as e:
 result['status']='FAIL_OBSERVATION';result['errors'].append({'type':type(e).__name__,'message':str(e)})
finally:
 os.close(fd);result['seconds']=time.monotonic()-start;result['endedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 print(json.dumps(result,separators=(',',':'),sort_keys=True))
