import os,sys,stat,json,time,resource,hashlib
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
began=time.monotonic();deadline=began+10
LIMIT=256; entries=0
ROOTS=[
 '/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1',
 '/var/lib/pinkha-c-filesv2-20261126/readguard-native1',
 '/var/lib/pinkha-c-filesv2-20261126/final-authority-native1',
 '/var/lib/pinkha-w1-closed-comparer-root-custody-20261127/attempt1']
PROOFS=[
 ('/var/lib/pinkha-w1-closed-comparer-root-custody-20261127/attempt1/result.json',3305,'6b176cc110e2f22d5449cad2b367c8c80e38551c308ea8e97868d5d21bb4d18d'),
 ('/mnt/development/projects/evidence/pinkha-e-final-authority-native-custody-20261128-attempt1/result.json',10604,'121542a245a70e8d9b5502e198b02e74f85f8348a6f356cbbaee40412dca4ded')]
def guard():
 if time.monotonic()>=deadline:raise RuntimeError('10-second metadata review bound')
def ident(s):
 return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_uid,s.st_gid,s.st_size,s.st_blocks,s.st_atime_ns,s.st_mtime_ns,s.st_ctime_ns]
def meta(s):
 return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'nlink':s.st_nlink,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'allocatedBytes':s.st_blocks*512,'atimeNS':s.st_atime_ns,'mtimeNS':s.st_mtime_ns,'ctimeNS':s.st_ctime_ns,'type':'directory' if stat.S_ISDIR(s.st_mode) else 'regular' if stat.S_ISREG(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'other'}
def open_parent(path):
 parts=path.split('/')[1:];fd=os.open('/',os.O_PATH|os.O_DIRECTORY|os.O_CLOEXEC)
 try:
  for part in parts[:-1]:
   guard()
   nxt=os.open(part,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
   os.close(fd);fd=nxt
  return fd,parts[-1]
 except BaseException:
  os.close(fd);raise
report={'schema':'pinkha-finite-owned-root-capacity-review-v1','status':'RUNNING','scope':'Four exact closed public producer/custody directories; direct children only. Two exact public custody receipts. No recursive census or file payload reads other than these receipts.','roots':[],'proofs':[],'errors':[],'entriesCap':LIMIT,'secondsCap':10,'changes':0,'children':0,'eligibleDisposableOrRelocatableBytesEstablished':0,'limitations':['Direct-entry allocation is not a recursive directory total.','Source, unique evidence, archives, all unknown descendants, accounts, current binaries, pending caches and other lanes remain protected.','No deletion/relocation or current-use clearance is granted by this observation.']}
rootdev=os.lstat('/').st_dev
try:
 for path in ROOTS:
  guard();row={'path':path,'children':[]};report['roots'].append(row)
  pfd=None;fd=None
  try:
   pfd,name=open_parent(path)
   before=os.stat(name,dir_fd=pfd,follow_symlinks=False)
   row['metadata']=meta(before)
   if not stat.S_ISDIR(before.st_mode) or before.st_dev!=rootdev:
    row['skipped']='not physical directory on ROOT';continue
   fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC,dir_fd=pfd)
   if ident(os.fstat(fd))!=ident(before):raise RuntimeError('directory identity changed before enumeration')
   with os.scandir(fd) as it:
    for entry in it:
     guard();entries+=1
     if entries>LIMIT:raise RuntimeError('256-entry direct-list bound')
     st=entry.stat(follow_symlinks=False)
     row['children'].append({'name':entry.name,'metadata':meta(st),'disposition':'unopened protected source/evidence or unclassified descendant; no disposal admission'})
   after=os.fstat(fd);named=os.stat(name,dir_fd=pfd,follow_symlinks=False)
   row['directoryIdentityUnchanged']=ident(before)==ident(after)==ident(named)
   row['directRegularAllocationBytes']=sum(x['metadata']['allocatedBytes'] for x in row['children'] if x['metadata']['type']=='regular')
   row['notRecursiveTotal']=True
   if not row['directoryIdentityUnchanged']:raise RuntimeError('directory changed during metadata observation')
  except FileNotFoundError:row['absent']=True
  except BaseException as e:
   row['error']={'type':type(e).__name__,'message':str(e)};raise
  finally:
   if fd is not None:os.close(fd)
   if pfd is not None:os.close(pfd)
 for path,length,expected in PROOFS:
  guard();pfd=None;fd=None
  try:
   pfd,name=open_parent(path);st=os.stat(name,dir_fd=pfd,follow_symlinks=False)
   if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size!=length:raise RuntimeError('fixed public receipt identity/size')
   fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC,dir_fd=pfd)
   if ident(os.fstat(fd))!=ident(st):raise RuntimeError('fixed receipt opening identity')
   data=bytearray()
   while len(data)<=length:
    guard();chunk=os.read(fd,min(65536,length+1-len(data)))
    if not chunk:break
    data.extend(chunk)
   if len(data)!=length or hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('fixed public receipt hash')
   if ident(st)!=ident(os.fstat(fd)) or ident(st)!=ident(os.stat(name,dir_fd=pfd,follow_symlinks=False)):raise RuntimeError('fixed receipt final identity')
   v=json.loads(data);scalars={k:x for k,x in v.items() if x is None or isinstance(x,(str,int,float,bool))}
   report['proofs'].append({'path':path,'bytes':length,'sha256':expected,'fullStableNOATIMERead':True,'topLevelScalars':scalars,'keys':list(v)})
  finally:
   if fd is not None:os.close(fd)
   if pfd is not None:os.close(pfd)
 report['status']='COMPLETE_FINITE_METADATA_REVIEW_NO_DISPOSAL_CANDIDATE_ADMITTED'
except BaseException as e:
 report['status']='PARTIAL_FINITE_REVIEW_NO_RETRY';report['errors'].append({'type':type(e).__name__,'message':str(e)})
report['entriesObserved']=entries;report['seconds']=round(time.monotonic()-began,6)
v=os.statvfs('/');report['rootAvailableBytes']=v.f_bavail*v.f_frsize
out=json.dumps(report,sort_keys=True)
if len(out.encode())>32768:
 report['status']='PARTIAL_OUTPUT_BOUND_NO_RETRY';report['errors'].append({'type':'OutputBound','message':'full proposed output exceeds32KiB; direct child details omitted'})
 for row in report['roots']:row['childCount']=len(row['children']);row.pop('children')
 out=json.dumps(report,sort_keys=True)
assert len(out.encode())<=32768
print(out)
