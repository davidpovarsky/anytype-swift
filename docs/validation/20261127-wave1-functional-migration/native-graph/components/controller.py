from pathlib import Path
import hashlib,json,os,shutil,subprocess,time,signal
ROOT=Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
CACHE=Path("/tmp/pinkha-w1-migration-swift-20261127")
OUT=Path("/var/lib/pinkha-w1-functional-migration-20261127/graph-bindings-attempt1")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
os.umask(0o077);OUT.mkdir(parents=True,exist_ok=False)
result={"status":"RUNNING","sourceCommit":"75bfb53fa4573d13be9d9f4bc5e199b6725e6c66","scope":"Four new computed relation binding methods including the exact retained original156 definitions; compile new native graph adapter fixture without executing it","errors":[]}
start=time.monotonic()
def inventory():
 out={}
 for name in ["PinkhaAnyEngine","PinkhaAnyIntegration","PinkhaAnyHost","PinkhaKit"]:
  d=ROOT/"Modules"/name
  for p in sorted(d.rglob("*")):
   if p.is_file() and (p.suffix==".swift" or p.name=="Package.resolved"):out[p.relative_to(ROOT).as_posix()]=sha(p)
 return out

SOURCE=Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156/bundle")
def source_definitions():
 expected={
  "snapshot-499c3540377351bb70bd1c7cd9eaaafc40acc45dffb31820ed89110e0e592fb4.pb":"9fc4f110df693b58bb1e27f97536dce7993a3a2c45923b6c600bcbec66ba749f",
  "snapshot-499c3540377351bb70bd1c7cd9eaaafc40acc45dffb31820ed89110e0e592fb4.json":"125c14522563fe24ddbc8c096f6f34d6e9a3bd7886fcf9035dc949547370ea00",
  "snapshot-c9c4bed807a227f8ecfe6d68093e99c89b48814361c328f59b5533513e082b86.pb":"26be3a39dc64803426488cca81d3c07c97da095b384ea1bb0e34746101c47da1",
  "snapshot-c9c4bed807a227f8ecfe6d68093e99c89b48814361c328f59b5533513e082b86.json":"881679863df59ccd5673678c400cd22f4170bef148d773c587f86424a4fd4a89"}
 for name,value in expected.items():assert sha(SOURCE/name)==value,name
 return expected

def save():result["seconds"]=round(time.monotonic()-start,3);write(OUT/"result.json",result)
child=None
def interrupted(*_):raise RuntimeError("owned computed binding build interrupted")
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
try:
 assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==result["sourceCommit"]
 assert CACHE.is_dir()
 expected={"swift-asn1":"917b472dbe53ba699cbb0495f9a95a084bc6364d","swift-crypto":"e8d6eba1fef23ae5b359c46b03f7d94be2f41fed","torahinspectorkit":"9058b489e9acc271b4f8ef69e2ed24648f93b4ed"}
 workspace=json.loads((CACHE/"workspace-state.json").read_bytes())
 for row in workspace["object"]["dependencies"]:
  ref=row["packageRef"];identity=ref["identity"]
  if identity in expected:
   checkout=CACHE/"checkouts"/row["subpath"];cmd=["git","-c","safe.directory="+str(checkout),"-C",str(checkout)]
   assert subprocess.check_output(cmd+["rev-parse","HEAD"],text=True).strip()==expected[identity]
   assert not subprocess.check_output(cmd+["status","--porcelain","--untracked-files=no"],text=True)
  else:
   assert ref["kind"]=="fileSystem" and str(ROOT) in ref["location"]
 result["dependencies"]=expected
 result["sourceDefinitionsBefore"]=source_definitions()
 before=inventory();write(OUT/"source-before.json",before)
 result["freeScratchBefore"]=shutil.disk_usage(CACHE).free
 assert result["freeScratchBefore"]>2*1024**3+128*1024**2, "2 GiB emergency floor plus bounded incremental build estimate"
 command=["/usr/local/bin/swift","test","--package-path",str(ROOT/"Modules/PinkhaAnyHost"),"--scratch-path",str(CACHE),"--disable-automatic-resolution","--jobs","2","--filter","NativeComputedRelationBindingTests"]
 result["command"]=command;save()
 with (OUT/"test.log").open("wb") as log:
  env=os.environ.copy();env["PINKHA_NATIVE_ORIGINAL156"]="/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156"
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
  result["pid"]=child.pid;save()
  result["minimumFreeBytes"]=result["freeScratchBefore"]
  while child.poll() is None:
   result["minimumFreeBytes"]=min(result["minimumFreeBytes"],shutil.disk_usage(CACHE).free)
   assert result["minimumFreeBytes"]>=2*1024**3,"2 GiB disk emergency"
   assert time.monotonic()-start<900,"bounded incremental Swift build"
   assert not (OUT/"abort").exists(),"owned component build abort"
   time.sleep(.5)
  result["exitCode"]=child.wait(timeout=10)
 after=inventory();write(OUT/"source-after.json",after)
 result["sourceUnchanged"]=before==after
 result["sourceDefinitionsAfter"]=source_definitions()
 assert result["sourceDefinitionsBefore"]==result["sourceDefinitionsAfter"]
 result["logSHA256"]=sha(OUT/"test.log")
 log=(OUT/"test.log").read_text(errors="replace")
 result["compiled"]="Build complete!" in log
 result["passLines"]=[x for x in log.splitlines() if "Test Case " in x and " passed " in x]
 result["failLines"]=[x for x in log.splitlines() if "Test Case " in x and " failed " in x]
 assert before==after
 assert result["compiled"],"test target was not compiled"
 assert len(result["passLines"])==4 and not result["failLines"] and "skipped" not in log.lower()
 try:os.killpg(child.pid,0);result["ownedGroupAbsent"]=False
 except ProcessLookupError:result["ownedGroupAbsent"]=True
 result["status"]="PASS" if result["exitCode"]==0 and result["ownedGroupAbsent"] else "FAIL"
except BaseException as e:result["status"]="FAIL";result["errors"].append({"type":type(e).__name__,"message":str(e)})
finally:
 signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
 if child is not None:
  try:
   try:os.killpg(child.pid,0);alive=True
   except ProcessLookupError:alive=False
   result["cleanupRequired"]=alive
   result["cleanupForcedKill"]=False
   if alive:
    result["status"]="FAIL"
    os.killpg(child.pid,signal.SIGTERM)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
     child.poll()
     try:os.killpg(child.pid,0)
     except ProcessLookupError:break
     time.sleep(.1)
    try:os.killpg(child.pid,0);alive=True
    except ProcessLookupError:alive=False
    if alive:
     result["cleanupForcedKill"]=True;os.killpg(child.pid,signal.SIGKILL)
    child.wait(timeout=10)
   try:os.killpg(child.pid,0);result["ownedGroupAbsent"]=False
   except ProcessLookupError:result["ownedGroupAbsent"]=True
   if not result["ownedGroupAbsent"]:result["status"]="FAIL"
  except BaseException as e:
   result["status"]="FAIL";result["errors"].append({"type":type(e).__name__,"message":"cleanup: "+str(e)})
 save()
print(json.dumps(result))
