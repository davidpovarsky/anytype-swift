import os, sys, json, base64, stat, hashlib, resource, subprocess, selectors, signal, time, fcntl, datetime
from pathlib import Path
FRONTEND='/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift-frontend'
FRONTEND_BYTES=208647456
FRONTEND_SHA='d98470fed50d4efc0075bcbd45ba1f908382dc9222c2b8213d1ff074efaa2083'
AS_LIMIT=1024*1024*1024
OUTPUT_LIMIT=65536
started=time.monotonic()
main_deadline=started+20
final_deadline=started+45
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT}
cancel_signal=None
captured_diagnostic_bytes=0
frontend_fd=None
result=json.loads("{\"schema\":\"pinkha-installed-serialized-mode-target-info-observation-v1\",\"status\":\"RUNNING\",\"commands\":[],\"errors\":[],\"limits\":{\"capabilityQueryOnly\":true,\"argv\":[\"swift-frontend\",\"-print-target-info\",\"-target\",\"aarch64-unknown-linux-gnu\",\"-module-load-mode\",\"only-serialized\"],\"sourceParsing\":false,\"typeChecking\":false,\"objectOrModuleEmission\":false,\"linking\":false,\"testInvocations\":0,\"nativeCalls\":0,\"runtimeAcceptance\":false,\"frozenComponentOrNativeControllersRun\":0,\"noProjectOrCacheWritesRequested\":true,\"globalFilesystemWriteAudit\":false,\"childRegularFileSizeLimit\":0,\"childAddressSpaceBytes\":1073741824,\"childCPUSeconds\":10,\"childWallSeconds\":12,\"mainWallSeconds\":20,\"finalWallSecondsFromStart\":45,\"combinedRetainedDiagnosticBytes\":65536,\"unchangedOwnedLifecycleDonor\":\"d8940f9a36bf11a1819e1cb4fbf72d301b565f74\"}}")
result['startedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024,128*1024))
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,AS_LIMIT))
identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def interrupted(number,_frame):
 global cancel_signal
 cancel_signal=number
for number in STOP_SIGNALS:signal.signal(number,interrupted)
signal.pthread_sigmask(signal.SIG_UNBLOCK,STOP_SIGNALS)
def require_main():
 if cancel_signal is not None:raise RuntimeError('controller cancellation signal '+str(cancel_signal))
 if time.monotonic()>=main_deadline:raise RuntimeError('bounded main deadline')
def hash_fd(fd,expected,deadline):
 os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256();total=0
 while total<=expected:
  if time.monotonic()>=deadline:raise RuntimeError('bounded hashing deadline')
  chunk=os.read(fd,min(1024*1024,expected-total+1))
  if not chunk:break
  total+=len(chunk)
  if total>expected:raise RuntimeError('hash input exceeded exact size')
  h.update(chunk)
 if total!=expected or time.monotonic()>=deadline:raise RuntimeError('hash input size/deadline mismatch')
 return h.hexdigest()
def other_group_members(pgid):
    """Bounded PID/session census; never retain command lines or process names."""
    members = []
    began = time.monotonic()
    count = 0
    for directory in Path('/proc').iterdir():
        if not directory.name.isdecimal() or int(directory.name) == pgid:
            continue
        count += 1
        if count > 200000 or time.monotonic()-began > 5:
            raise RuntimeError('bounded owned process-group census exceeded')
        try:
            with (directory/'stat').open('rb') as stream:
                raw = stream.read(8193)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if len(raw) > 8192:
            raise RuntimeError('bounded process identity record exceeded')
        closing = raw.rfind(b') ')
        if closing < 0:
            raise RuntimeError('malformed process identity record')
        fields = raw[closing+2:].split()
        if len(fields) < 20:
            raise RuntimeError('short process identity record')
        if int(fields[2]) == pgid:
            if int(fields[3]) != pgid:
                raise RuntimeError('owned group session identity changed')
            members.append(int(directory.name))
    return members

def limits():
 for number in STOP_SIGNALS:signal.signal(number,signal.SIG_DFL)
 signal.pthread_sigmask(signal.SIG_UNBLOCK,STOP_SIGNALS)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
 resource.setrlimit(resource.RLIMIT_AS,(AS_LIMIT,AS_LIMIT))
 resource.setrlimit(resource.RLIMIT_CPU,(10,10))
 resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
def leader_exit(proc,state):
 if state['reaped']:raise RuntimeError('leader already reaped')
 return os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
def group_absent(proc,state):
 if state['absenceObserved']:return True
 try:os.killpg(proc.pid,0)
 except ProcessLookupError:state['absenceObserved']=True
 return state['absenceObserved']
def send_owned(proc,state,number):
 if state['absenceObserved']:return
 if state['reaped']:raise RuntimeError('refuse signalling after leader reap')
 leader_exit(proc,state)
 if group_absent(proc,state):return
 if os.getpgid(proc.pid)!=proc.pid or os.getsid(proc.pid)!=proc.pid:raise RuntimeError('owned group/session changed')
 try:
  os.killpg(proc.pid,number);state['signals'].append(int(number))
 except ProcessLookupError:group_absent(proc,state)
def drain_unreaped(proc,state,seconds):
 deadline=min(time.monotonic()+seconds,final_deadline)
 while True:
  done=leader_exit(proc,state)
  members=other_group_members(proc.pid)
  if done is not None and not members:return True
  if time.monotonic()>=deadline:
   state['unresolvedOtherGroupMembers']=members
   return False
  time.sleep(.05)
def finish_owned(proc,state,failed):
 if state['finished']:return
 try:
  if failed or leader_exit(proc,state) is None or other_group_members(proc.pid):
   state['forcedCleanup']=True
   send_owned(proc,state,signal.SIGTERM)
   if not drain_unreaped(proc,state,3):
    send_owned(proc,state,signal.SIGKILL)
    if not drain_unreaped(proc,state,4):raise RuntimeError('owned group unresolved after TERM/KILL')
  state['exitCode']=proc.wait(timeout=1);state['reaped']=True
  state['processGroupAbsent']=group_absent(proc,state)
  if not state['processGroupAbsent']:raise RuntimeError('positive group absence not established')
 except BaseException as first:
  state['cleanupErrors'].append({'type':type(first).__name__,'message':str(first)})
  if not state['reaped'] and not state['absenceObserved']:
   try:
    send_owned(proc,state,signal.SIGKILL)
    if not drain_unreaped(proc,state,3):raise RuntimeError('final owned group unresolved')
    state['exitCode']=proc.wait(timeout=1);state['reaped']=True
    state['processGroupAbsent']=group_absent(proc,state)
   except BaseException as last:state['cleanupErrors'].append({'type':type(last).__name__,'message':str(last)})
 finally:state['finished']=True
def observe_help():
 global captured_diagnostic_bytes
 require_main()
 proc=None;selector=None;out=bytearray();err=bytearray();reason=None
 command=[FRONTEND,'-print-target-info','-target','aarch64-unknown-linux-gnu','-module-load-mode','only-serialized']
 row_result={'capability':'installed-frontend-target-info','command':command,'exitCode':None,'diagnosticsComplete':True,'observedDiagnosticBytes':0,'signals':[],'cleanupErrors':[],'reaped':False,'absenceObserved':False,'finished':False,'forcedCleanup':False,'processGroupAbsent':False,'unreapedLeaderDuringGroupCleanup':True}
 result['commands'].append(row_result)
 began=time.monotonic()
 try:
  env=os.environ.copy()
  for name in ('TMPDIR','TMP','TEMP','SWIFT_MODULECACHE_PATH','CLANG_MODULE_CACHE_PATH'):env[name]='/dev/null'
  require_main()
  previous_mask=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
  try:
   proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd='/',start_new_session=True,preexec_fn=limits)
   row_result.update(pid=proc.pid,pgid=proc.pid)
  finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous_mask)
  selector=selectors.DefaultSelector()
  for stream,tag in ((proc.stdout,'stdout'),(proc.stderr,'stderr')):
   os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,tag)
  while selector.get_map():
   require_main()
   if time.monotonic()-began>12:raise RuntimeError('finite frontend-target-info timeout')
   for key,_ in selector.select(.1):
    remaining=OUTPUT_LIMIT-captured_diagnostic_bytes
    chunk=os.read(key.fileobj.fileno(),min(8192,remaining+1))
    if chunk:
     row_result['observedDiagnosticBytes']+=len(chunk)
     retained=chunk[:remaining]
     (out if key.data=='stdout' else err).extend(retained)
     captured_diagnostic_bytes+=len(retained)
     if len(chunk)>remaining:
      row_result['diagnosticsComplete']=False
      raise RuntimeError('whole-invocation diagnostic limit')
    else:selector.unregister(key.fileobj)
   if leader_exit(proc,row_result) is not None and other_group_members(proc.pid):
    raise RuntimeError('owned descendants outlived frontend-target-info leader')
  # Wait for normal terminal status without reaping or losing group ownership.
  while leader_exit(proc,row_result) is None:
   require_main()
   if time.monotonic()-began>12:raise RuntimeError('finite frontend-target-info terminal timeout')
   time.sleep(.01)
 except BaseException as e:
  reason={'type':type(e).__name__,'message':str(e)}
 finally:
  if selector is not None:selector.close()
  if proc is not None:
   finish_owned(proc,row_result,reason is not None or cancel_signal is not None)
   for stream in (proc.stdout,proc.stderr):stream.close()
  row_result.update(seconds=round(time.monotonic()-began,6),stdout=bytes(out).decode('utf-8','replace'),stderr=bytes(err).decode('utf-8','replace'),retainedDiagnosticBytes=len(out)+len(err),failureReason=reason)
 if reason or row_result['cleanupErrors'] or row_result['forcedCleanup'] or row_result['exitCode']!=0 or not row_result['processGroupAbsent']:
  raise RuntimeError('frontend target-info command failed')
 require_main()
try:
 assert sys.flags.optimize==0
 mem={}
 for line in Path('/proc/meminfo').read_text().splitlines():
  if line.startswith('MemAvailable:'):mem['availableBefore']=int(line.split()[1])*1024
 assert mem['availableBefore']>=2*1024*1024*1024
 result['memory']=mem
 fp=Path(FRONTEND)
 assert fp.resolve()==fp
 frontend_fd=os.open(fp,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
 initial=os.fstat(frontend_fd)
 assert stat.S_ISREG(initial.st_mode) and initial.st_mode&0o7777==0o755 and initial.st_size==FRONTEND_BYTES and initial.st_nlink==1
 assert hash_fd(frontend_fd,FRONTEND_BYTES,main_deadline)==FRONTEND_SHA
 assert identity(initial)==identity(os.fstat(frontend_fd))==identity(os.lstat(fp))
 result['toolchain']={'path':FRONTEND,'bytes':FRONTEND_BYTES,'sha256':FRONTEND_SHA,'mode':0o755,'identityBefore':identity(initial),'provenanceObservationSHA256':'d93433b85ab53b941cde27af52d3612d21b2a93af3d5e838cff2126607f3af17','notWholeToolchainAdmission':True}
 observe_help()
 assert result['commands'][0]['stdout'] and not result['commands'][0]['stderr']
 require_main()
 result['status']='PASS_FRONTEND_TARGET_INFO_OBSERVATION'
except BaseException as e:
 result['status']='FAIL_FRONTEND_TARGET_INFO_OBSERVATION';result['errors'].append({'type':type(e).__name__,'message':str(e)})
finally:
 if frontend_fd is not None:
  try:
   assert identity(initial)==identity(os.fstat(frontend_fd))==identity(os.lstat(FRONTEND))
   assert hash_fd(frontend_fd,FRONTEND_BYTES,final_deadline)==FRONTEND_SHA
   result['frontendUnchanged']=True
  except BaseException as e:
   result['status']='FAIL_FRONTEND_TARGET_INFO_OBSERVATION';result['errors'].append({'phase':'final-frontend-identity','type':type(e).__name__,'message':str(e)})
  os.close(frontend_fd)
 if cancel_signal is not None:
  result['status']='FAIL_FRONTEND_TARGET_INFO_OBSERVATION';result['errors'].append({'phase':'cancellation','signal':cancel_signal})
 if time.monotonic()>final_deadline:
  result['status']='FAIL_FRONTEND_TARGET_INFO_OBSERVATION';result['errors'].append({'phase':'final-deadline','message':'45 second bound exceeded'})
 result['retainedDiagnosticBytes']=captured_diagnostic_bytes
 result['seconds']=round(time.monotonic()-started,6);result['endedAtUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 print(json.dumps(result,sort_keys=True))
sys.exit(0 if result['status']=='PASS_FRONTEND_TARGET_INFO_OBSERVATION' else 1)
