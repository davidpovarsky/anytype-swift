#!/usr/bin/env python3
"""Losslessly archive only the closed superseded native792; retain exact restore custody."""
import hashlib,json,os,select,shutil,signal,stat,subprocess,time
from pathlib import Path
ROOT=Path('/var/lib/pinkha-c-filesv2-20261126')
SOURCE=ROOT/'acl-refresh-native1/any'
WANT='79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857'
OUT=Path('/mnt/development/projects/evidence/pinkha-w1-network-native792-archive-20261127')
ARCHIVE=OUT/'any-79248a63.xz'
FLOOR=2*1024**3
DEV_FLOOR=512*1024**2
os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
result={'protocol':'lossless-superseded-native792-archival-v1','status':'RUNNING','source':str(SOURCE),'archive':str(ARCHIVE),'sourceSHA256':WANT,'retiredDuplicateUncompressed':False,'uniqueBinaryRetainedInVerifiedArchive':False,'processes':[],'errors':[]}
start=time.monotonic();retired=False

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
 return h.hexdigest()

def save():
 result['seconds']=round(time.monotonic()-start,3)
 temp=OUT/'result.json.tmp'
 with temp.open('w') as stream:
  stream.write(json.dumps(result,sort_keys=True,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
 os.replace(temp,OUT/'result.json')
 fd=os.open(OUT,os.O_RDONLY);os.fsync(fd);os.close(fd)

def absent(pid):
 try:os.killpg(pid,0)
 except ProcessLookupError:return True
 return False

def no_live_users():
 found=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
  try:
   args=(proc/'cmdline').read_bytes()
   if str(SOURCE).encode() in args:found.append(int(proc.name));continue
   if (proc/'exe').resolve()==SOURCE:found.append(int(proc.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 assert not found,'superseded binary is in use'
 return []

def guard():
 free=shutil.disk_usage(ROOT).free
 dev=shutil.disk_usage(OUT).free
 result['minimumDevelopmentFreeBytes']=min(result.get('minimumDevelopmentFreeBytes',dev),dev)
 assert dev>=DEV_FLOOR,'512MiB development emergency floor'
 result['minimumRootFreeBytes']=min(result.get('minimumRootFreeBytes',free),free)
 assert free>=FLOOR,'2GiB root emergency floor'
 assert time.monotonic()-start<180,'bounded single-native archival deadline'
 return free

def interrupt(*_):raise RuntimeError('owned archive interrupted')
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
try:
 result['rootFreeBefore']=guard()
 result['developmentFreeBefore']=shutil.disk_usage(OUT).free;assert result['developmentFreeBefore']>=DEV_FLOOR+80*1024**2
 result['memAvailableBefore']=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 assert result['memAvailableBefore']>=512*1024**2
 result['loadAverageBefore']=os.getloadavg()
 result['resourcePolicy']={'rootFloor':FLOOR,'developmentFloor':DEV_FLOOR,'developmentInitialReserve':80*1024**2,'largeRootWrites':False,'xzThreads':1,'nice':10,'ioClass':'idle'}
 no_live_users();st=SOURCE.stat()
 assert SOURCE.resolve()==SOURCE and not SOURCE.is_symlink() and stat.S_ISREG(st.st_mode) and st.st_nlink==1
 assert st.st_size==78074642 and sha(SOURCE)==WANT
 assert not os.listxattr(SOURCE),'extended attributes require explicit preservation'
 before=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,st.st_mode,st.st_uid,st.st_gid)
 result['metadata']={'bytes':st.st_size,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'atime_ns':st.st_atime_ns,'mtime_ns':st.st_mtime_ns,'allocatedBytes':st.st_blocks*512}
 current=ROOT/'lan-progress-native1/any';baseline=Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current/any')
 # This controller does not touch current0796 or base1dc. Pin the current product.
 assert sha(current)=='0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07'
 result['currentNativeUnchangedSHA256']=sha(current)
 command=['/usr/bin/nice','-n','10','/usr/bin/ionice','-c','3','/usr/bin/xz','--threads=1','-6','--stdout',str(SOURCE)]
 row={'name':'compress','command':command,'forcedKill':False};result['processes'].append(row)
 with ARCHIVE.open('xb') as stream, (OUT/'compress.log').open('xb') as err:
  p=subprocess.Popen(command,stdout=stream,stderr=err,start_new_session=True);row.update(pid=p.pid,pgid=p.pid);save()
  try:
   while p.poll() is None:
    guard();assert ARCHIVE.stat().st_size<=st.st_size+1024**2;time.sleep(.3)
  finally:
   if p.poll() is None:
    if not absent(p.pid):os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
     if not absent(p.pid):os.killpg(p.pid,signal.SIGKILL);row['forcedKill']=True
     p.wait(timeout=5)
   row.update(exitCode=p.returncode,groupPositivelyAbsent=absent(p.pid))
 assert row['exitCode']==0 and row['groupPositivelyAbsent'] and not row['forcedKill']
 fd=os.open(ARCHIVE,os.O_RDONLY);os.fsync(fd);os.close(fd)
 result['archiveSHA256']=sha(ARCHIVE);result['archiveBytes']=ARCHIVE.stat().st_size
 assert 0<result['archiveBytes']<st.st_size
 # Stream verification writes no decompressed duplicate.
 command=['/usr/bin/nice','-n','10','/usr/bin/ionice','-c','3','/usr/bin/xz','--decompress','--stdout',str(ARCHIVE)]
 row={'name':'verify-decompression','command':command,'forcedKill':False};result['processes'].append(row)
 h=hashlib.sha256();size=0
 with (OUT/'verify.log').open('xb') as err:
  p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=err,start_new_session=True);row.update(pid=p.pid,pgid=p.pid);save()
  try:
   os.set_blocking(p.stdout.fileno(),False)
   while True:
    guard()
    if not select.select([p.stdout],[],[],.3)[0]:continue
    data=os.read(p.stdout.fileno(),1024**2)
    if not data:break
    h.update(data);size+=len(data);assert size<=st.st_size
   p.wait(timeout=10)
  finally:
   if p.stdout:p.stdout.close()
   if p.poll() is None:
    if not absent(p.pid):os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:
     if not absent(p.pid):os.killpg(p.pid,signal.SIGKILL);row['forcedKill']=True
     p.wait(timeout=5)
   row.update(exitCode=p.returncode,groupPositivelyAbsent=absent(p.pid))
 assert row['exitCode']==0 and row['groupPositivelyAbsent'] and not row['forcedKill']
 assert h.hexdigest()==WANT and size==st.st_size
 result['verifiedDecompressedSHA256']=h.hexdigest();result['verifiedDecompressedBytes']=size
 result['uniqueBinaryRetainedInVerifiedArchive']=True
 no_live_users();now=SOURCE.stat()
 assert (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns,now.st_mode,now.st_uid,now.st_gid)==before and sha(SOURCE)==WANT
 restore=r'''#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
r=json.loads((root/'result.json').read_text());dst=Path(r['source']);arc=Path(r['archive'])
assert not dst.exists() and not dst.is_symlink(),'refuse overwrite'
assert hashlib.sha256(arc.read_bytes()).hexdigest()==r['archiveSHA256']
assert shutil.disk_usage(dst.parent).free>=2*1024**3+r['metadata']['bytes']
assert shutil.disk_usage(root).free>=512*1024**2
tmp=dst.with_name(dst.name+'.restore-79248a63');assert not tmp.exists()
with tmp.open('xb') as f:subprocess.run(['/usr/bin/xz','--decompress','--stdout',str(arc)],stdout=f,check=True,timeout=60)
assert tmp.stat().st_size==r['metadata']['bytes'] and hashlib.sha256(tmp.read_bytes()).hexdigest()==r['sourceSHA256']
os.chmod(tmp,r['metadata']['mode']);os.chown(tmp,r['metadata']['uid'],r['metadata']['gid']);os.utime(tmp,ns=(r['metadata']['atime_ns'],r['metadata']['mtime_ns']))
assert not dst.exists();os.replace(tmp,dst)
print(json.dumps({'restored':str(dst),'sha256':r['sourceSHA256'],'bytes':dst.stat().st_size,'mode':dst.stat().st_mode & 0o7777}))
'''
 (OUT/'restore.py').write_text(restore);os.chmod(OUT/'restore.py',0o700)
 fd=os.open(OUT/'restore.py',os.O_RDONLY);os.fsync(fd);os.close(fd)
 result['restoreCommand']='/usr/bin/python3 -B '+str(OUT/'restore.py')
 result['restoreControllerSHA256']=sha(OUT/'restore.py')
 result['status']='VERIFIED_ARCHIVE_BEFORE_DUPLICATE_RETIREMENT';save()
 no_live_users();assert sha(ARCHIVE)==result['archiveSHA256'] and sha(SOURCE)==WANT
 SOURCE.unlink();retired=True
 fd=os.open(SOURCE.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
 result['retiredDuplicateUncompressed']=True
 result['allOwnedGroupsPositivelyAbsent']=all(x['groupPositivelyAbsent'] and not x['forcedKill'] and x['exitCode']==0 for x in result['processes'])
 assert result['allOwnedGroupsPositivelyAbsent'] and not SOURCE.exists()
 assert sha(current)==result['currentNativeUnchangedSHA256']
 result['status']='PASS_LOSSLESS_SUPERSEDED_NATIVE792_ARCHIVAL'
except BaseException as error:
 result['status']='FAIL_ARCHIVAL';result['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
 result['retiredDuplicateUncompressed']=retired
 result['rootFreeAfter']=shutil.disk_usage(ROOT).free
 result['developmentFreeAfter']=shutil.disk_usage(OUT).free
 save();print(json.dumps({'status':result['status'],'receipt':str(OUT/'result.json'),'receiptSHA256':sha(OUT/'result.json'),'retiredDuplicateUncompressed':retired,'rootFreeAfter':result['rootFreeAfter'],'errors':result['errors']}))
raise SystemExit(0 if result['status']=='PASS_LOSSLESS_SUPERSEDED_NATIVE792_ARCHIVAL' else 1)
