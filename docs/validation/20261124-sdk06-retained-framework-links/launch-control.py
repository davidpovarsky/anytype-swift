import argparse,errno,hashlib,json,os,resource,shutil,signal,stat,subprocess,time,traceback
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path("/run/anytapy-wave15-source-overlay-20261123/sdk-retained-framework-links")
BASE=Path("/run/anytapy-wave15-source-overlay-20261123/sdk-retained-framework-links-control-attempt1")
parser=argparse.ArgumentParser()
parser.add_argument("--source",required=True)
SOURCE=parser.parse_args().source
assert len(SOURCE)==40 and all(c in "0123456789abcdef" for c in SOURCE),"full_frozen_source_required"
WRAPPER="docs/validation/20261124-sdk06-retained-framework-links/run-control.py"
WRAPPER_SHA="3466baa77cc9ff38a5f251a64f707f7d82c04801ad5e387b86fc5f12723e5c67"
OBSERVED_PEAK={"logicalBytes":0,"allocatedBytes":0}
def stamp():return datetime.now(timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def permitted_fixture_link(output, path):
    """No link fixtures belong to this current projection control."""
    return False

def output_usage():
 logical=allocated=entries=vanished=0
 if not BASE.exists():return {"logicalBytes":0,"allocatedBytes":0,"entries":0,"concurrentlyRemoved":0}
 for path in (BASE,*BASE.rglob("*")):
  try:info=path.lstat()
  except FileNotFoundError:
   vanished+=1;continue
  assert stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or (stat.S_ISLNK(info.st_mode) and permitted_fixture_link(BASE,path)),"unexpected_output_type"
  assert not stat.S_ISREG(info.st_mode) or info.st_size<=256*1024,"control_output_file_cap"
  logical+=info.st_size;allocated+=info.st_blocks*512;entries+=1
 assert entries<=256,"finite_control_output_entries"
 return {"logicalBytes":logical,"allocatedBytes":allocated,"entries":entries,"concurrentlyRemoved":vanished}
def capacity(start=False):
 mount=Path("/run/anytapy-wave15-source-overlay-20261123")
 assert ROOT.parent==mount and BASE.parent==mount,"fixed_RAM_parent_required"
 lines=[x for x in Path("/proc/self/mountinfo").read_text().splitlines() if x.split()[4]==str(mount)]
 assert len(lines)==1 and " - tmpfs " in lines[0],"dedicated_source_tmpfs_required"
 available=[int(x.split()[1])*1024 for x in Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")]
 assert len(available)==1 and available[0]>=2*1024**3,"RAM_memory_reserve"
 free=shutil.disk_usage(ROOT).free
 assert free>=(8*1024**2 if start else 4*1024**2),("RAM_volume_reserve",free)
 usage=output_usage()
 assert usage["logicalBytes"]<=2*1024**2-64*1024 and usage["allocatedBytes"]<=2*1024**2-64*1024,"measured_output_budget"
 for key in OBSERVED_PEAK:OBSERVED_PEAK[key]=max(OBSERVED_PEAK[key],usage[key])
 return {"ramFreeBytes":free,"memAvailableBytes":available[0]}
def save(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
 with path.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 path.chmod(0o600)
def absent(pgid):
 try:os.killpg(pgid,0)
 except ProcessLookupError:return True
 return False
start_free=capacity(True)
assert not BASE.exists() and not BASE.is_symlink()
assert Path(__file__).read_bytes()==subprocess.check_output(["git","-c","core.packedGitWindowSize=16m","-c","core.packedGitLimit=64m","-C",str(ROOT),"show",SOURCE+":docs/validation/20261124-sdk06-retained-framework-links/launch-control.py"],timeout=20),"frozen_outer_source_changed"
raw=(ROOT/WRAPPER).read_bytes()
assert sha(raw)==WRAPPER_SHA
assert raw==subprocess.check_output(["git","-c","core.packedGitWindowSize=16m","-c","core.packedGitLimit=64m","-C",str(ROOT),"show",SOURCE+":"+WRAPPER],timeout=20)
assert subprocess.check_output(["git","-c","core.packedGitWindowSize=16m","-c","core.packedGitLimit=64m","-C",str(ROOT),"rev-parse","HEAD"],timeout=10).decode().strip()==SOURCE
BASE.mkdir(mode=0o700)
BASE.chmod(0o700)
outside=BASE/"run-controls.py"
with outside.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
outside.chmod(0o600)
proc=None;owned=None;primary=None;cleanup_error=None;observations=[];rc=None
started=time.monotonic()
def child_limits():
 resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","GIT_OPTIONAL_LOCKS":"0"}
command=["python3","-B",str(outside),"--root",str(ROOT),"--source",SOURCE,"--output",str(BASE/"attempt1")]
try:
 with (BASE/"process.stdout").open("xb") as out,(BASE/"process.stderr").open("xb") as err:
  proc=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                        start_new_session=True,preexec_fn=child_limits)
  owned=proc.pid
  assert os.getpgid(proc.pid)==owned and owned>1 and owned!=os.getpgrp()
  save(BASE/"owned-process.json",{"createdAt":stamp(),"pid":proc.pid,"pgid":owned,
       "argv":command,"source":SOURCE,"wrapperSHA256":WRAPPER_SHA,"startResources":start_free})
  deadline=started+60
  while proc.poll() is None:
   capacity()
   assert time.monotonic()<deadline,"bounded_control_deadline"
   time.sleep(0.1)
  rc=proc.wait()
  capacity()
  assert time.monotonic()<deadline,"control_returned_after_deadline"
  assert rc==0,("control_exit",rc)
except BaseException as error:
 primary={"type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
finally:
 try:
  if proc is not None and owned is not None:
   stop_deadline=time.monotonic()+10
   if not absent(owned):
    observations.append({"at":stamp(),"action":"SIGTERM","pgid":owned})
    try:os.killpg(owned,signal.SIGTERM)
    except ProcessLookupError:pass
    grace=min(stop_deadline,time.monotonic()+2)
    while not absent(owned) and time.monotonic()<grace:
     proc.poll();time.sleep(0.05)
   if not absent(owned):
    observations.append({"at":stamp(),"action":"SIGKILL","pgid":owned})
    try:os.killpg(owned,signal.SIGKILL)
    except ProcessLookupError:pass
   while not absent(owned) and time.monotonic()<stop_deadline:
    proc.poll();time.sleep(0.05)
   assert absent(owned) and time.monotonic()<stop_deadline,"owned_group_not_absent_in_budget"
   proc.wait(timeout=max(0.001,stop_deadline-time.monotonic()))
   rc=proc.returncode
  final_free=capacity()
 except BaseException as error:
  cleanup_error={"type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
  final_free={"resourceObservationFailed":True}
 final_usage=None;final_absence=None;final_observation_errors=[]
 for phase,observe in (
     ("final_output_usage",output_usage),
     ("final_owned_group_absence",lambda: owned is not None and absent(owned))):
  try:
   value=observe()
   if phase=="final_output_usage":final_usage=value
   else:final_absence=value
  except BaseException as error:
   final_observation_errors.append({"phase":phase,"type":type(error).__name__,
       "message":str(error),"traceback":traceback.format_exc()})
 result={"status":"PASS" if primary is None and cleanup_error is None
         and not final_observation_errors and final_absence is True else "FAIL",
   "source":SOURCE,"wrapperSHA256":WRAPPER_SHA,"pid":None if proc is None else proc.pid,"pgid":owned,
   "returncode":rc,"primaryFailure":primary,"cleanupFailure":cleanup_error,
   "ownedGroupAbsent":final_absence,"cleanupObservations":observations,
   "finalObservationFailures":final_observation_errors,"finalReceiptFailure":None,
   "elapsed":time.monotonic()-started,"startResources":start_free,"finalResources":final_free,
   "newFocusedMethodsRequested":1,"unaffectedOldMethodsRequested":0,"newUniqueAcceptanceCredit":0,"buildsRequested":0,"productMethodsRequested":0,
   "resourceProfile":"fixed-retained-framework-link-ram-2mib-v1","observedOutputPeak":dict(OBSERVED_PEAK),"finalOutputUsageBeforeReceipt":final_usage}
 try:
  save(BASE/"launch-result.json",result)
 except BaseException as error:
  result["status"]="FAIL"
  result["finalReceiptFailure"]={"phase":"final_receipt_write","type":type(error).__name__,
      "message":str(error),"traceback":traceback.format_exc()}
 print(json.dumps(result,sort_keys=True))
if result["status"]!="PASS":raise SystemExit(1)
