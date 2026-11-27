#!/usr/bin/env python3
"""Recover root headroom by exact raw custody relocation of one closed superseded native."""
import hashlib,json,os,shutil,signal,stat,time
from pathlib import Path
SOURCE=Path('/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/any')
WANT='79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857'
CURRENT=Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/any')
CURRENT_SHA='0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07'
BASE=Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current/any')
BASE_SHA='1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636'
FAILED=Path('/mnt/development/projects/evidence/pinkha-w1-network-native792-archive-20261127')
FAILED_SHA='473afc8999467fe8450264e2ece0bd135e16f9aed015d99180f0272f0a0e1d47'
OUT=Path('/mnt/development/projects/evidence/pinkha-w1-network-native792-raw-20261127')
TARGET=OUT/'any-79248a63132a0146'
ROOT_BUILD_FLOOR=2*1024**3
DEV_FLOOR=512*1024**2
os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
started=time.monotonic();retired=False
result={'protocol':'exact-raw-native792-custody-recovery-v1','status':'RUNNING','source':str(SOURCE),'target':str(TARGET),'sourceSHA256':WANT,'duplicateSourceRetired':False,'bytesDeletedFromUniqueCustody':0,'errors':[],
 'resourcePolicy':{'purpose':'below-root-build-floor recovery; every large output is development; native/build floors unchanged','rootBuildFloorUnchanged':ROOT_BUILD_FLOOR,'developmentFloor':DEV_FLOOR,'developmentAdmissionReserve':80*1024**2,'maximumRootControlBytes':4*1024**2,'rootBulkBytesWritten':0,'compileRuns':0,'nativeAccountRuns':0,'compressionRuns':0}}

def fsync_dir(path):
 fd=os.open(path,os.O_RDONLY);os.fsync(fd);os.close(fd)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(1024**2),b''):h.update(data)
 return h.hexdigest()

def identity(st):return (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns)

def save():
 result['seconds']=round(time.monotonic()-started,3);tmp=OUT/'receipt.json.tmp'
 with tmp.open('w') as f:f.write(json.dumps(result,sort_keys=True,indent=2)+'\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,OUT/'receipt.json');fsync_dir(OUT)

def no_live_users():
 active=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
  try:
   argv=(proc/'cmdline').read_bytes()
   if str(SOURCE).encode() in argv or (proc/'exe').resolve()==SOURCE:active.append(int(proc.name))
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
 assert not active,'source binary still used'
 result['noLiveSourceUsers']=True

def guard():
 root_free=shutil.disk_usage('/').free;dev_free=shutil.disk_usage(OUT).free
 result['minimumObservedRootFreeBytes']=min(result.get('minimumObservedRootFreeBytes',root_free),root_free)
 result['minimumDevelopmentFreeBytes']=min(result.get('minimumDevelopmentFreeBytes',dev_free),dev_free)
 assert dev_free>=DEV_FLOOR,'unchanged512MiB development emergency floor'
 assert root_free>=4*1024**2,'bounded existing-root control overhead reserve'
 assert time.monotonic()-started<120,'bounded direct custody relocation deadline'
 return root_free,dev_free

def interrupted(*_):raise RuntimeError('owned raw custody relocation interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
try:
 root_before,dev_before=guard();assert dev_before>=DEV_FLOOR+80*1024**2
 result.update(rootFreeBefore=root_before,developmentFreeBefore=dev_before,rootInitiallyBelowBuildFloor=root_before<ROOT_BUILD_FLOOR)
 result['controllerSHA256']=sha(__file__)
 assert sha(FAILED/'result.json')==FAILED_SHA
 failed=json.loads((FAILED/'result.json').read_text());assert failed['status']=='FAIL_ARCHIVAL' and not failed['retiredDuplicateUncompressed']
 assert all(p['groupPositivelyAbsent'] and not p['forcedKill'] for p in failed['processes'])
 failed_archive=Path(failed['archive']);failed_archive_sha=sha(failed_archive)
 result['preservedFailedArchive']={'receiptSHA256':FAILED_SHA,'partialArchiveSHA256':failed_archive_sha,'partialArchiveBytes':failed_archive.stat().st_size}
 no_live_users();st=SOURCE.lstat()
 assert SOURCE.resolve()==SOURCE and stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size==78074642
 assert not os.listxattr(SOURCE),'extended attributes require explicit preservation'
 assert sha(SOURCE)==WANT and sha(CURRENT)==CURRENT_SHA and sha(BASE)==BASE_SHA
 assert SOURCE.stat().st_dev!=OUT.stat().st_dev and OUT.resolve()==OUT
 before=identity(SOURCE.stat());st=SOURCE.stat()
 result['sourceMetadata']={'device':st.st_dev,'inode':st.st_ino,'bytes':st.st_size,'allocatedBytes':st.st_blocks*512,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'atime_ns':st.st_atime_ns,'mtime_ns':st.st_mtime_ns}
 result['unchangedProductsBefore']={'current':CURRENT_SHA,'base':BASE_SHA}
 h=hashlib.sha256();count=0
 with SOURCE.open('rb') as src,TARGET.open('xb') as dst:
  assert identity(os.fstat(src.fileno()))==before
  while True:
   data=src.read(1024**2)
   if not data:break
   guard();dst.write(data);h.update(data);count+=len(data);assert count<=st.st_size
  dst.flush();os.fsync(dst.fileno())
 assert count==st.st_size and h.hexdigest()==WANT
 os.chmod(TARGET,stat.S_IMODE(st.st_mode));os.chown(TARGET,st.st_uid,st.st_gid);os.utime(TARGET,ns=(st.st_atime_ns,st.st_mtime_ns))
 fd=os.open(TARGET,os.O_RDONLY);os.fsync(fd);os.close(fd);fsync_dir(OUT)
 assert TARGET.is_file() and not TARGET.is_symlink() and TARGET.stat().st_nlink==1 and TARGET.stat().st_dev!=st.st_dev
 assert TARGET.stat().st_size==st.st_size and sha(TARGET)==WANT
 ts=TARGET.stat();assert stat.S_IMODE(ts.st_mode)==stat.S_IMODE(st.st_mode) and ts.st_uid==st.st_uid and ts.st_gid==st.st_gid and ts.st_mtime_ns==st.st_mtime_ns
 assert identity(SOURCE.stat())==before and sha(SOURCE)==WANT
 result['targetMetadata']={'device':ts.st_dev,'inode':ts.st_ino,'bytes':ts.st_size,'allocatedBytes':ts.st_blocks*512,'mode':stat.S_IMODE(ts.st_mode),'uid':ts.st_uid,'gid':ts.st_gid,'mtime_ns':ts.st_mtime_ns}
 result['verifiedRawCopySHA256']=WANT
 restore=r'''#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,shutil
root=Path(__file__).resolve().parent;r=json.loads((root/'receipt.json').read_text());src=Path(r['target']);dst=Path(r['source']);meta=r['sourceMetadata']
assert not dst.exists() and not dst.is_symlink(),'refuse overwrite'
assert src.is_file() and not src.is_symlink() and src.stat().st_nlink==1
assert src.stat().st_size==meta['bytes'] and hashlib.sha256(src.read_bytes()).hexdigest()==r['sourceSHA256']
assert shutil.disk_usage(dst.parent).free>=2*1024**3+meta['allocatedBytes']+4*1024**2
assert shutil.disk_usage(root).free>=512*1024**2
tmp=dst.with_name(dst.name+'.restore-79248a63');assert not tmp.exists()
h=hashlib.sha256();size=0
with src.open('rb') as a,tmp.open('xb') as b:
 for data in iter(lambda:a.read(1024**2),b''):b.write(data);h.update(data);size+=len(data)
 b.flush();os.fsync(b.fileno())
assert size==meta['bytes'] and h.hexdigest()==r['sourceSHA256']
os.chmod(tmp,meta['mode']);os.chown(tmp,meta['uid'],meta['gid']);os.utime(tmp,ns=(meta['atime_ns'],meta['mtime_ns']))
fd=os.open(tmp,os.O_RDONLY);os.fsync(fd);os.close(fd)
assert not dst.exists();os.replace(tmp,dst)
fd=os.open(dst.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
print(json.dumps({'restored':str(dst),'sha256':r['sourceSHA256'],'bytes':dst.stat().st_size,'mode':dst.stat().st_mode & 0o7777}))
'''
 with (OUT/'restore.py').open('w') as f:f.write(restore);f.flush();os.fsync(f.fileno())
 os.chmod(OUT/'restore.py',0o700)
 fd=os.open(OUT/'restore.py',os.O_RDONLY);os.fsync(fd);os.close(fd)
 result['restoreCommand']='/usr/bin/python3 -B '+str(OUT/'restore.py');result['restoreSHA256']=sha(OUT/'restore.py')
 result['status']='VERIFIED_RAW_CUSTODY_BEFORE_DUPLICATE_RETIREMENT';save()
 no_live_users();guard()
 assert sha(TARGET)==WANT and identity(SOURCE.stat())==before and sha(SOURCE)==WANT
 assert sha(FAILED/'result.json')==FAILED_SHA and sha(failed_archive)==failed_archive_sha
 SOURCE.unlink();retired=True;fsync_dir(SOURCE.parent)
 assert not SOURCE.exists() and sha(TARGET)==WANT
 assert sha(CURRENT)==CURRENT_SHA and sha(BASE)==BASE_SHA
 result['unchangedProductsAfter']={'current':CURRENT_SHA,'base':BASE_SHA}
 result['duplicateSourceRetired']=True
 result['status']='PASS_EXACT_RAW_NATIVE792_CUSTODY_RECOVERY'
except BaseException as error:
 result['status']='FAIL_RAW_CUSTODY_RECOVERY';result['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
 result['duplicateSourceRetired']=retired;result['rootFreeAfter']=shutil.disk_usage('/').free;result['developmentFreeAfter']=shutil.disk_usage(OUT).free
 save();print(json.dumps({'status':result['status'],'receipt':str(OUT/'receipt.json'),'sha256':sha(OUT/'receipt.json'),'rootFreeAfter':result['rootFreeAfter'],'developmentFreeAfter':result['developmentFreeAfter'],'duplicateSourceRetired':retired,'seconds':result['seconds'],'errors':result['errors']}))
raise SystemExit(0 if result['status']=='PASS_EXACT_RAW_NATIVE792_CUSTODY_RECOVERY' else 1)
