"""Build the exact qualified native immutable-record CLI for shared integration."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time,shutil,traceback
ROOT=Path("/Users/m1/development/anytype-c-active-20261125/immutable-cli-c1fd-41c07")
QUALIFIED=Path("/Users/m1/development/anytype-c-active-20261125/native-immutable-c1fd-41c07-retry1")
SOURCE=QUALIFIED/"source"
GO="/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go"
FLOOR=2*1024**3
GROWTH=768*1024**2
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+".new");tmp.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n");tmp.replace(p)
def require(value,reason):
 if not value:raise RuntimeError(reason)
def source_state(manifest):
 actual={}
 for p in sorted(SOURCE.rglob("*")):
  require(not p.is_symlink(),"Native source symlink")
  if p.is_file():
   actual[str(p.relative_to(SOURCE))]={"bytes":p.stat().st_size,"sha256":sha(p),"mode":p.stat().st_mode&0o777}
 expected={p:{k:v[k] for k in ("bytes","sha256","mode")} for p,v in manifest["files"].items()}
 expected["staging.yml"]={k:manifest["files"]["internal/pinkha/migrationnative/testdata/local.yml"][k] for k in ("bytes","sha256","mode")}
 require(actual==expected and len(actual)==1589,"Complete qualified source/config differs")
 return {"files":len(actual),"sha256":hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"commits":manifest["commits"]}
def run_command(name,args,cwd,env,timeout):
 directory=ROOT/name;directory.mkdir(exist_ok=False)
 log=directory/"original.jsonl"
 started=time.time();free=shutil.disk_usage(ROOT).free
 result={"argv":args,"cwd":str(cwd),"started":started,"status":"STARTING","freeBytesBefore":free,"timeoutSeconds":timeout,"errors":[]}
 process=None;absent=False
 def observe():
  nonlocal absent
  if absent:return False
  try:os.killpg(process.pid,0);return True
  except ProcessLookupError:absent=True;return False
 def stop():
  nonlocal absent
  if process is None or absent:return
  if process.poll() is not None:
   require(not observe(),"Post-exit group remains unresolved; no historical group signal is authorized")
   return
  if not observe():return
  try:os.killpg(process.pid,signal.SIGTERM)
  except ProcessLookupError:absent=True
  try:process.wait(timeout=15)
  except subprocess.TimeoutExpired:
   # The original live Popen still owns this process identity. A reaped or
   # positively absent historical group is never signalled again.
   if process.poll() is None and not absent:
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:absent=True
   process.wait(timeout=10)
  require(not observe(),"Owned process group remained after termination")
 try:
  require(free>=FLOOR+GROWTH,"Measured 768 MiB warmed two-method continuation growth plus emergency floor unavailable")
  with log.open("xb") as output:
   process=subprocess.Popen(args,cwd=cwd,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
   result.update(pid=process.pid,pgid=process.pid,status="RUNNING")
   write(directory/"started.json",result);write(ROOT/"active.json",result)
   minimum=free
   while process.poll() is None:
    current=shutil.disk_usage(ROOT).free;minimum=min(minimum,current)
    require(current>=FLOOR,"Owned phase stopped at 2 GiB emergency floor")
    require(time.time()-started<timeout,"Owned phase deadline exceeded")
    write(directory/"monitor.json",{"elapsed":time.time()-started,"free":current,"minimumFree":minimum,"pid":process.pid})
    time.sleep(1)
   result["exitCode"]=process.wait()
   # Establish absence immediately after reaping; never signal that historical
   # group again after logs, source verification or result serialization.
   require(not observe(),"Owned child group is still present after original command")
   result["minimumFreeBytes"]=minimum
  require(result["exitCode"]==0,"Original command returned a nonzero exit")
  result["status"]="PASS_ORIGINAL_COMMAND"
 except BaseException as exc:
  result["status"]="FAIL"
  result["errors"].append({"type":type(exc).__name__,"reason":str(exc)})
 finally:
  try:stop()
  except BaseException as exc:
   result["status"]="FAIL";result["errors"].append({"phase":"cleanup","type":type(exc).__name__,"reason":str(exc)})
  try:
   result.update(finished=time.time(),elapsedSeconds=time.time()-started,ownedGroupAbsent=absent,freeBytesAfter=shutil.disk_usage(ROOT).free)
   if log.exists():result.update(originalLogSHA256=sha(log),originalLogBytes=log.stat().st_size)
  except BaseException as exc:
   result["status"]="FAIL";result["errors"].append({"phase":"retention","type":type(exc).__name__,"reason":str(exc)})
  write(directory/"result.json",result);write(ROOT/"active.json",result)
 require(result["status"]=="PASS_ORIGINAL_COMMAND",name+" failed; original result retained")
 return result

def main():
 result={"status":"RUNNING","started":time.time(),"testsExecuted":0,"accountsCreated":0,"sourceAdmission":False,"wholeSpaceMigration":False,"errors":[]}
 manifest=None
 try:
  require(sha(QUALIFIED/"source-manifest.json")=="39f4ee580af8f2897b2f794f872327b7391828a3a57355cf0235dae7d1626e72","Source manifest differs")
  require(sha(QUALIFIED/"result.json")=="c37de86daf19dedf13aa1f6ba5d3a4c0ee8f304074894bf8992651832a62ee34","Native test provenance differs")
  qualified=json.loads((QUALIFIED/"result.json").read_text())
  require(qualified["status"]=="PASS_NATIVE_IMMUTABLE_RECORD_TWO_METHODS_AND_REUSED_ELEVEN_NOT_FULL_MIGRATION" and qualified["testsExecuted"]==2 and qualified["sourceBefore"]==qualified["sourceAfter"],"Native qualification failed")
  manifest=json.loads((QUALIFIED/"source-manifest.json").read_text())
  require(manifest["commits"]=={"any":"41c07bd32e95a54824a3d3c5d592accf5074ab68","sdk":"c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"},"Wrong native commits")
  result["sourceBefore"]=source_state(manifest)
  env=dict(os.environ,PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",GOTOOLCHAIN="local",GOWORK="off",GOCACHE="/Users/m1/caches/anytapy-go1.27.4-build",GOMODCACHE="/Users/m1/caches/anytapy-go-mod",GOPROXY="file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct",GOMAXPROCS="2",GOMEMLIMIT="2GiB",CGO_ENABLED="1",TMPDIR=str(ROOT/"tmp"),GOTMPDIR=str(ROOT/"gotmp"))
  for name in ("tmp","gotmp"):(ROOT/name).mkdir(exist_ok=False)
  result["resourceRationale"]="One warmed host executable, reusing original two-package native qualification caches; prior native CLI was80.9MB. Additional compilation/output budget768MiB plus2GiB emergency floor, two package workers and2GiB soft Go heap; no iOS/Apple producer or accepted test replay."
  result["resources"]={"free":shutil.disk_usage(ROOT).free,"vmStat":subprocess.run(["vm_stat"],capture_output=True,text=True).stdout,"swap":subprocess.run(["sysctl","vm.swapusage"],capture_output=True,text=True).stdout}
  result["build"]=run_command("build",[GO,"build","-mod=readonly","-buildvcs=false","-p","2","-o",str(ROOT/"any"),"./cmd/any"],SOURCE,env,900)
  result["goBuildInfo"]=run_command("build-info",[GO,"version","-m",str(ROOT/"any")],SOURCE,env,30)
  result["help"]=run_command("help",[str(ROOT/"any"),"--help"],ROOT,env,30)
  require("Usage:" in (ROOT/"help/original.jsonl").read_text(),"Actual command help not emitted")
  result["binary"]={"path":str(ROOT/"any"),"bytes":(ROOT/"any").stat().st_size,"sha256":sha(ROOT/"any")}
  result["sourceAfter"]=source_state(manifest)
  require(result["sourceBefore"]==result["sourceAfter"],"Native source changed")
  result["status"]="PASS_EXACT_HOST_CLI_BUILD_NOT_MIGRATION_ACCEPTANCE"
 except BaseException as exc:
  result["status"]="FAIL";result["errors"].append({"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()})
 finally:
  if manifest is not None:
   try:
    result["sourceAfter"]=source_state(manifest)
    if result.get("sourceBefore")!=result["sourceAfter"]:result["status"]="FAIL"
   except BaseException as exc:result["status"]="FAIL";result["errors"].append({"phase":"source-retention","reason":str(exc)})
  result["controllerSHA256"]=sha(Path(__file__));result["finished"]=time.time();write(ROOT/"result.json",result)
 print(json.dumps({"status":result["status"],"resultSHA256":sha(ROOT/"result.json"),"binary":result.get("binary"),"errors":result["errors"]}))
 return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":sys.exit(main())
