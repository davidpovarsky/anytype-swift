import argparse,errno,hashlib,json,os,resource,shutil,signal,stat,subprocess,time,traceback
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk-compile-support-20261123")
BASE=Path("/mnt/development/projects/diagnostics/sdk06-compile-support-controls-20261123/attempt1-controller")
parser=argparse.ArgumentParser()
parser.add_argument("--source",required=True)
SOURCE=parser.parse_args().source
assert len(SOURCE)==40 and all(c in "0123456789abcdef" for c in SOURCE),"full_frozen_source_required"
WRAPPER="docs/validation/20261123-sdk06-compile-support/run-control.py"
WRAPPER_SHA="9d11f39589afe4baef3955819d3befb40b7cee48722b1b6642c70ae3e1f27827"
OBSERVED_PEAK={"logicalBytes":0,"allocatedBytes":0}
def stamp():return datetime.now(timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def permitted_fixture_link(output, path):
    """Only two negative-control links; inspect the link itself, never follow it."""
    parts = path.relative_to(output).parts
    if parts and parts[0] == "attempt1":
        parts = parts[1:]
    if len(parts) < 3 or parts[0] != "temporary-controls" or not parts[1].startswith("sdk06-compile-support-control-"):
        return False
    return parts[2:] in {
        ("linked-project",),
        ("support-project", "CompileSupport", "GeneratedModuleMaps-iphonesimulator",
         "GoogleUtilities-UserDefaults.modulemap"),
    }

def output_usage():
 logical=allocated=entries=vanished=0
 if not BASE.exists():return {"logicalBytes":0,"allocatedBytes":0,"entries":0,"concurrentlyRemoved":0}
 for path in (BASE,*BASE.rglob("*")):
  try:info=path.lstat()
  except FileNotFoundError:
   vanished+=1;continue
  assert stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or (stat.S_ISLNK(info.st_mode) and permitted_fixture_link(BASE,path)),"unexpected_output_type"
  logical+=info.st_size;allocated+=info.st_blocks*512;entries+=1
 return {"logicalBytes":logical,"allocatedBytes":allocated,"entries":entries,"concurrentlyRemoved":vanished}
def capacity(start=False):
 free=shutil.disk_usage(ROOT).free
 assert free>=1073741824,("measured_capacity_guard",free)
 usage=output_usage()
 assert usage["logicalBytes"]<=8*1024**2-64*1024 and usage["allocatedBytes"]<=8*1024**2-64*1024,"measured_output_budget"
 for key in OBSERVED_PEAK:OBSERVED_PEAK[key]=max(OBSERVED_PEAK[key],usage[key])
 return free
def save(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
 with path.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 path.chmod(0o600)
def absent(pgid):
 try:os.killpg(pgid,0)
 except ProcessLookupError:return True
 return False
start_free=capacity(True)
assert not BASE.exists()
assert Path(__file__).read_bytes()==subprocess.check_output(["git","-C",str(ROOT),"show",SOURCE+":docs/validation/20261123-sdk06-compile-support/launch-control.py"],timeout=20),"frozen_outer_source_changed"
raw=(ROOT/WRAPPER).read_bytes()
assert sha(raw)==WRAPPER_SHA
assert raw==subprocess.check_output(["git","-C",str(ROOT),"show",SOURCE+":"+WRAPPER],timeout=20)
assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],timeout=10).decode().strip()==SOURCE
BASE.mkdir(mode=0o700)
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
       "argv":command,"source":SOURCE,"wrapperSHA256":WRAPPER_SHA,"startFree":start_free})
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
  final_free=shutil.disk_usage(ROOT).free
 result={"status":"PASS" if primary is None and cleanup_error is None else "FAIL",
   "source":SOURCE,"wrapperSHA256":WRAPPER_SHA,"pid":None if proc is None else proc.pid,"pgid":owned,
   "returncode":rc,"primaryFailure":primary,"cleanupFailure":cleanup_error,
   "ownedGroupAbsent":owned is not None and absent(owned),"cleanupObservations":observations,
   "elapsed":time.monotonic()-started,"startFree":start_free,"finalFree":final_free,
   "newMethodsRequested":1,"oldMethodsRequested":0,"buildsRequested":0,"productMethodsRequested":0,
   "resourceProfile":"fixed-pure-compile-support-1gib-8mib-v1","observedOutputPeak":dict(OBSERVED_PEAK),"finalOutputUsageBeforeReceipt":output_usage()}
 save(BASE/"launch-result.json",result)
 print(json.dumps(result,sort_keys=True))
if result["status"]!="PASS":raise SystemExit(1)
