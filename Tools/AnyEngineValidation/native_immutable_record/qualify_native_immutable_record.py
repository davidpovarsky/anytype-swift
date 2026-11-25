"""Exact source-bound native immutable-record qualification; no Apple build."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,tarfile,time,shutil,traceback

ROOT=Path("/Users/m1/development/anytype-c-active-20261125/native-immutable-c1fd-8b107")
SOURCE=ROOT/"source"
ARCHIVE="b8c658eb78704fd3ce0a61dd177e8ca829976a5d9ad75a0d05337a67b6896049"
MANIFEST="ff1c77f05c6594c39b8a0c93f9217e5a924bfa6744484a465d03f3359ca1b410"
GO="/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go"
EXPECTED={
"TestPreparedIntentExactBytesSurviveLostAckAndRestart",
"TestPreparedIntentConcurrentReservationSelectsOneEnvelope",
"TestPreparedIntentRejectsChangedPlanBeforeNewEntity",
"TestPreparedIntentRejectsChangedSpecOrCrossKind",
"TestPreparedIntentEntityCannotAcquireAnAlternateIntentID",
"TestPreparedIntentRejectsWrongOrReplacedStore",
"TestPreparedIntentSpacesShareProjectionDBWithoutSharingLedger",
"TestPreparedIntentRefusesWithoutDurabilityBarrier",
"TestImmutableRecordIntentRestartAndCrossRouteCollision",
"TestImmutableRecordDeclarationRejectsWritableOrUnownedShapes",
"TestImmutableRecordValuesRejectNativeStampAndMissingRequiredInput",
"TestPreparedImmutableRecordNativeRestartRefusalsAndPinnedMutability",
"TestPreparedImmutableRecordHTTPNativeCycleAndStrictInput",
}
FLOOR=2*1024**3
GROWTH=1536*1024**2
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def write(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_name(p.name+".new")
 tmp.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
 tmp.replace(p)
def require(value,reason):
 if not value:raise RuntimeError(reason)
def source_state(manifest):
 actual={}
 for p in sorted(SOURCE.rglob("*")):
  require(not p.is_symlink(),"Source contains a symlink")
  if p.is_file():
   rel=str(p.relative_to(SOURCE))
   actual[rel]={"bytes":p.stat().st_size,"sha256":sha(p),"mode":p.stat().st_mode&0o777}
 expected={p:{k:v[k] for k in ("bytes","sha256","mode")} for p,v in manifest["files"].items()}
 require(actual==expected,"Complete original source closure differs")
 return {"files":len(actual),"contentSHA256":hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"commits":manifest["commits"]}
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
  require(free>=FLOOR+GROWTH,"Measured 1.5 GiB warmed compiler/test growth plus emergency floor unavailable")
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
 result={"status":"RUNNING","started":time.time(),"sourceAdmission":False,"wholeSpaceMigration":False,"testsExecuted":0,"errors":[]}
 manifest=None
 try:
  require(sha(ROOT/"source.tar.gz")==ARCHIVE and sha(ROOT/"source-manifest.json")==MANIFEST,"Exact immutable source archive and manifest required")
  manifest=json.loads((ROOT/"source-manifest.json").read_text())
  require(manifest["commits"]=={"any":"8b107a50a3d07d985e978b40b376ba15c9b019ac","sdk":"c1fd59bd8f0ed62471234ec1a65a402d22eab6a9"} and len(manifest["files"])==1588,"Source identity changed")
  require(not SOURCE.exists(),"Existing source root cannot be overwritten")
  with tarfile.open(ROOT/"source.tar.gz","r:gz") as archive:
   seen=set()
   for member in archive.getmembers():
    rel=Path(member.name)
    require(member.isfile() and not rel.is_absolute() and ".." not in rel.parts and rel.parts[0]=="source" and member.name not in seen,"Unsafe source member")
    seen.add(member.name)
    name=str(Path(*rel.parts[1:]));expected=manifest["files"].get(name)
    require(expected is not None and member.size==expected["bytes"] and member.mode==expected["mode"],"Unexpected source member")
    data=archive.extractfile(member).read()
    require(hashlib.sha256(data).hexdigest()==expected["sha256"],"Source archive member differs")
    dest=ROOT/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);dest.chmod(expected["mode"])
   require(len(seen)==1588,"Incomplete source archive")
  result["sourceBefore"]=source_state(manifest)
  env=dict(os.environ,PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",GOTOOLCHAIN="local",GOWORK="off",GOCACHE="/Users/m1/caches/anytapy-go1.27.4-build",GOMODCACHE="/Users/m1/caches/anytapy-go-mod",GOPROXY="file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct",GOMAXPROCS="2",GOMEMLIMIT="2GiB",CGO_ENABLED="1",TMPDIR=str(ROOT/"tmp"),GOTMPDIR=str(ROOT/"gotmp"))
  for p in ("tmp","gotmp"): (ROOT/p).mkdir()
  result["resourceRationale"]="One warmed native Go qualification, 2 package workers/2 GiB soft Go heap; a separate owner runs the 4-worker Swift App. Initial source is 17.3 MB, prior 11.91-second exact CLI rebuild confirmed the cache is warm; additional compiler/test product growth is conservatively estimated at 1.5 GiB; fresh memory/free bytes retained. No fixed machine reservation or native/Apple duplicate."
  result["resources"]={"free":shutil.disk_usage(ROOT).free,"vmStat":subprocess.run(["vm_stat"],capture_output=True,text=True).stdout,"swap":subprocess.run(["sysctl","vm.swapusage"],capture_output=True,text=True).stdout}
  result["version"]=run_command("toolchain",[GO,"version"],SOURCE,env,30)
  require("go1.27.4 darwin/arm64" in (ROOT/"toolchain/original.jsonl").read_text(),"Different native Go toolchain")
  result["moduleGraph"]=run_command("module-graph",[GO,"list","-mod=readonly","-m","-json","all"],SOURCE,env,120)
  args=[GO,"test","-mod=readonly","-buildvcs=false","-json","-count=1","-p","2","-timeout","5m","-run","^("+"|".join(sorted(EXPECTED))+")$","github.com/anyproto/any-sync-sdk/internal/migrationintent","github.com/anyproto/any-sync-sdk/internal/spaceimpl","./internal/pinkha/migrationnative","./internal/server"]
  try:
   result["tests"]=run_command("original-tests",args,SOURCE,env,1800)
  finally:
   terminals={};packages=[];subtests=[]
   for line in (ROOT/"original-tests/original.jsonl").read_text().splitlines():
    try:row=json.loads(line)
    except json.JSONDecodeError:continue
    if row.get("Action") in ("pass","fail","skip"):
     if row.get("Test"):
      if "/" in row["Test"]:subtests.append(row)
      else:
       require(row["Test"] not in terminals,"Duplicate original test terminal")
       terminals[row["Test"]]=row
     elif row.get("Package"):packages.append(row)
   result["testTerminals"]=terminals;result["subtestTerminals"]=subtests;result["packageTerminals"]=packages
   result["testsExecuted"]=len(terminals)
  require(set(terminals)==EXPECTED and all(x["Action"]=="pass" for x in terminals.values()),"Every exact original/new method must execute and pass, no skips")
  require(len(packages)==4 and all(x["Action"]=="pass" for x in packages) and all(x["Action"]=="pass" for x in subtests),"Original package/subtest failure or skip")
  result["sourceAfter"]=source_state(manifest)
  require(result["sourceBefore"]==result["sourceAfter"],"Source changed during qualification")
  result["status"]="PASS_NATIVE_IMMUTABLE_RECORD_COMPONENT_AND_HTTP_NOT_FULL_MIGRATION"
 except BaseException as exc:
  result["status"]="FAIL";result["errors"].append({"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()})
 finally:
  if manifest is not None and SOURCE.exists():
   try:result["sourceAfter"]=source_state(manifest)
   except BaseException as exc:result["status"]="FAIL";result["errors"].append({"phase":"source-retention","reason":str(exc)})
  result["finished"]=time.time();result["controllerSHA256"]=sha(Path(__file__))
  write(ROOT/"result.json",result)
 print(json.dumps({"status":result["status"],"testsExecuted":result["testsExecuted"],"resultSHA256":sha(ROOT/"result.json"),"errors":result["errors"]}))
 return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":sys.exit(main())
