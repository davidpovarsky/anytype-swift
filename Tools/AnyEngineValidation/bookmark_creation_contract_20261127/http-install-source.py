#!/usr/bin/env python3
"""Install one frozen public HTTP10 controller; never execute it."""
from pathlib import Path
import ast, hashlib, json, os, shutil, signal, stat, sys, time

PARENT=Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127')
OUT=PARENT/'http10-controls1'
UPLOAD=Path('/var/lib/sentinelx/uploads/pinkha-host-http10-control-3554-20261127.py')
DEST=OUT/'run_bookmark_http_continuation.py'
SHA='3554d3bda474f6fd6db2ae9ebadeccf2173ef5a06efc77b5fc680443bf4bdbdc'
PINS={
 PARENT/'prepared1/qualification/run_bookmark_components.py':'6e715e0dc316f3b08ded6322121339a61f2044b55a909cb61dca4fa72852d9e0',
 PARENT/'prepared1/qualification/bookmark-component-inputs.json':'eb2b91a339f9f2f9ccaf30220fc1fc52781d960e3efdc5d68a8ae270dcb9ef83',
 PARENT/'components-attempt1/result.json':'9aa1b527c5df731f27f103cdeab2d93f672ba5d13bd9061167826ce5ef6aa465',
 PARENT/'components-attempt1/commands/swift-components/original.log':'cf3eecc59f0d97efc0b760d1bbbd2da8d70d2e2c56898e745a48aea4bae8efb4',
 PARENT/'components-attempt1/compiled-source-inputs.json':'01c2db0d00d02e123c4697fcf034b4afe8214430fabf406e64192379af2da7c5'}
MIB=1024**2
began=time.monotonic(); final_deadline=None; owns=False; serial=0; before={}
report={'protocol':'pinkha-bookmark-http10-source-install-v1','status':'RUNNING','compilerInvocations':0,'nativeInvocations':0,'testMethodsExecuted':0,'childCommands':0,'accountInputs':0,'originalPathsModified':0,'errors':[],'completionErrors':[]}

def frozen(path, maximum=2*MIB):
 assert path.is_absolute() and path.resolve()==path and not path.is_symlink()
 fd=os.open(path,os.O_RDONLY|os.O_NOATIME|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  info=os.fstat(fd); assert stat.S_ISREG(info.st_mode) and info.st_size<=maximum
  raw=b''
  while True:
   part=os.read(fd,65536)
   if not part: break
   raw+=part; assert len(raw)<=maximum
  assert info==os.fstat(fd)==path.lstat() and len(raw)==info.st_size
 finally: os.close(fd)
 return raw

def row(raw): return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def sync(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try: os.fsync(fd)
 finally: os.close(fd)

def write_new(path,raw):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
 try:
  view=memoryview(raw)
  while view:
   n=os.write(fd,view); assert n>0; view=view[n:]
  os.fsync(fd)
 finally: os.close(fd)
 sync(path.parent)
 assert frozen(path)==raw and stat.S_IMODE(path.stat().st_mode)==0o600

def guard(initial=False):
 assert time.monotonic() < (final_deadline if final_deadline is not None else began+45)
 free={'root':shutil.disk_usage('/').free,'development':shutil.disk_usage('/mnt/development').free}
 assert free['root']>=2*1024**3+(32*MIB if initial else 0)
 assert free['development']>=512*MIB+(8*MIB if initial else 0)
 if owns:
  paths=[OUT]+list(OUT.iterdir()); assert len(paths)<=32
  assert sum(p.lstat().st_blocks*512 for p in paths)<=8*MIB
 return free

def save():
 global serial
 report['seconds']=round(time.monotonic()-began,6)
 raw=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode(); assert len(raw)<MIB
 serial+=1; tmp=OUT/('installation-result.pending-'+str(serial))
 write_new(tmp,raw); os.replace(tmp,OUT/'installation-result.json'); sync(OUT)

own=Path(__file__).absolute(); own_raw=None; source=None
try:
 assert not sys.flags.optimize and os.geteuid()==0 and os.uname().nodename=='torah-social'
 assert PARENT.resolve()==PARENT and PARENT.is_dir() and not os.path.lexists(OUT)
 own_raw=frozen(own); assert len(sys.argv)==2 and hashlib.sha256(own_raw).hexdigest()==sys.argv[1]
 ast.parse(own_raw)
 def interrupted(number,_): raise RuntimeError('source-only installation interrupted by signal '+str(number))
 for number in (signal.SIGTERM,signal.SIGINT): signal.signal(number,interrupted)
 signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
 report['freeBefore']=guard(True)
 source=frozen(UPLOAD); assert row(source)=={'bytes':32151,'sha256':SHA}; ast.parse(source)
 for path,wanted in PINS.items():
  guard(); raw=frozen(path); assert hashlib.sha256(raw).hexdigest()==wanted; before[str(path)]=row(raw)
 os.umask(0o077); OUT.mkdir(mode=0o700,exist_ok=False); owns=True; os.chmod(OUT,0o700); sync(OUT); sync(PARENT)
 assert stat.S_IMODE(OUT.stat().st_mode)==0o700
 write_new(OUT/'installation-result.json',b'{}\n'); save()
 write_new(DEST,source)
 report['installedSource']={'path':str(DEST),**row(frozen(DEST)),'mode':stat.S_IMODE(DEST.stat().st_mode)}
 report['status']='PASS_EXACT_HTTP10_SOURCE_INSTALLED_ONLY_NOT_RUN'
except BaseException as error:
 report['status']='FAIL_HTTP10_SOURCE_INSTALL_RETAINED'; report['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
 for number in (signal.SIGTERM,signal.SIGINT): signal.signal(number,signal.SIG_IGN)
 final_deadline=min(began+60,time.monotonic()+15)
 try:
  for name,wanted in before.items(): guard(); assert row(frozen(Path(name)))==wanted
  if own_raw is not None: guard(); assert frozen(own)==own_raw; report['installerUnchanged']=True
  if source is not None: guard(); assert frozen(UPLOAD)==source; report['uploadedSourceUnchanged']=True
  if 'installedSource' in report:
   guard(); assert frozen(DEST)==source and stat.S_IMODE(DEST.stat().st_mode)==0o600; report['installedSourceUnchanged']=True
  report['originalPublicInputsUnchanged']=len(before)==len(PINS)
  report['freeAfter']=guard()
 except BaseException as error:
  report['status']='FAIL_HTTP10_SOURCE_INSTALL_RETAINED'; report['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
 if owns:
  try: save()
  except BaseException as error:
   report['status']='FAIL_HTTP10_SOURCE_INSTALL_RETAINED'; report['completionErrors'].append({'phase':'receipt-retention','type':type(error).__name__,'message':str(error)})
 print(json.dumps(report,sort_keys=True))
raise SystemExit(0 if report['status']=='PASS_EXACT_HTTP10_SOURCE_INSTALLED_ONLY_NOT_RUN' else 1)
