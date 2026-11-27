from pathlib import Path
import hashlib,json,os,shutil,subprocess,time,signal
ROOT=Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
CACHE=Path("/tmp/pinkha-w1-migration-swift-20261127")
OUT=Path("/var/lib/pinkha-w1-functional-migration-20261127/canonical-definition-components-attempt1")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
os.umask(0o077);OUT.mkdir(parents=True,exist_ok=False)
result={"status":"RUNNING","sourceCommit":"5235bf902f8820fdc41fe802265ff5444407b363","scope":"Three exact-source canonical supplement methods; compile the readonly native eight-definition cold-process fixture without executing it","errors":[]}
start=time.monotonic()
def inventory():
 out={}
 for name in ["PinkhaAnyEngine","PinkhaAnyIntegration","PinkhaAnyHost","PinkhaKit"]:
  d=ROOT/"Modules"/name
  for p in sorted(d.rglob("*")):
   if p.is_file() and (p.suffix==".swift" or p.name=="Package.resolved"):out[p.relative_to(ROOT).as_posix()]=sha(p)
 return out

SOURCE=Path("/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1/private-work")
BUNDLE=Path("/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156/bundle")
BUNDLE_SHA="cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4"
SOURCE_KEYS={"rel-"+key for key in ["name","description","id","spaceId","type","creator","createdDate","lastModifiedDate","lastModifiedBy"]}|{"ot-space","ot-objectType","ot-participant"}
def source_definitions():
 expected={
  "source-preservation-plan.json":"4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930",
  "execute-mappings.json":"eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3",
  "execute-verification.json":"fee4dc5cb8e689e01bf2d1fbe8bd262c42388fd706da4114be72af3e6cf97350"}
 for name,value in expected.items():assert sha(SOURCE/name)==value,name
 assert sha(BUNDLE/"manifest.json")==BUNDLE_SHA
 manifest=json.loads((BUNDLE/"manifest.json").read_bytes())
 rows=[v for v in manifest["Objects"] if v["UniqueKey"] in SOURCE_KEYS]
 assert len(rows)==len(SOURCE_KEYS)==12
 for row in rows:
  for field in ["Snapshot","NativeJSONView"]:
   member=row[field];file=BUNDLE/member["Path"]
   assert file.resolve().parent==BUNDLE and not file.is_symlink()
   assert file.stat().st_size==member["Bytes"] and sha(file)==member["SHA256"]
   expected["bundle/"+member["Path"]]=member["SHA256"]
 expected["bundle/manifest.json"]=BUNDLE_SHA
 return expected

def save():result["seconds"]=round(time.monotonic()-start,3);write(OUT/"result.json",result)
child=None
before=None
controller_sha=sha(Path(__file__))
def interrupted(*_):raise RuntimeError("owned definition directory build interrupted")
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
try:
 assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==result["sourceCommit"]
 repair=Path("/var/lib/pinkha-w1-functional-migration-20261127/dependency-locator-repair1/result.json")
 result["dependencyLocatorRepairReceiptSHA256"]=sha(repair)
 assert result["dependencyLocatorRepairReceiptSHA256"]=="d2318aec75ba8eb2bcb8786009cb6af2b1f2ec99daf6fd68bdd8b4fdf779a300"
 repair_result=json.loads(repair.read_text())
 assert repair_result["status"]=="PASS_OWNED_DEPENDENCY_LOCATORS_REPAIRED"
 assert repair_result["allDependencySourceFilesAndModesUnchanged"] and repair_result["acceptedCompiledProductsUnchanged"]
 assert CACHE.is_dir()
 expected={"swift-asn1":"917b472dbe53ba699cbb0495f9a95a084bc6364d","swift-crypto":"e8d6eba1fef23ae5b359c46b03f7d94be2f41fed","torahinspectorkit":"9058b489e9acc271b4f8ef69e2ed24648f93b4ed"}
 workspace=json.loads((CACHE/"workspace-state.json").read_bytes())
 found=set()
 for row in workspace["object"]["dependencies"]:
  ref=row["packageRef"];identity=ref["identity"]
  if identity in expected:
   found.add(identity)
   checkout=CACHE/"checkouts"/row["subpath"];cmd=["git","-c","safe.directory="+str(checkout),"-C",str(checkout)]
   assert subprocess.check_output(cmd+["rev-parse","HEAD"],text=True).strip()==expected[identity]
   assert not subprocess.check_output(cmd+["status","--porcelain","--untracked-files=no"],text=True)
  else:
   assert ref["kind"]=="fileSystem" and str(ROOT) in ref["location"]
 assert found==set(expected)
 result["dependencies"]=expected
 result["sourceDefinitionsBefore"]=source_definitions()
 before=inventory();write(OUT/"source-before.json",before)
 result["freeScratchBefore"]=shutil.disk_usage(CACHE).free
 assert result["freeScratchBefore"]>2*1024**3+128*1024**2, "2 GiB emergency floor plus bounded incremental build estimate"
 command=["/usr/local/bin/swift","test","--package-path",str(ROOT/"Modules/PinkhaAnyHost"),"--scratch-path",str(CACHE),"--disable-automatic-resolution","--jobs","2","--filter","NativeCanonicalDefinitionSupplementTests"]
 result["command"]=command;save()
 with (OUT/"test.log").open("wb") as log:
  env={k:v for k,v in os.environ.items() if not k.startswith("PINKHA_NATIVE_")};env["PINKHA_NATIVE_DEFINITION_RETAINED"]=str(SOURCE);env["PINKHA_NATIVE_ORIGINAL156"]=str(BUNDLE.parent)
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
 assert len(result["passLines"])==3 and not result["failLines"] and "skipped" not in log.lower()
 expected_methods=["testEightOriginalCanonicalDefinitionsRetainEvidenceAndDistinctValueSemantics", "testSupplementRefusesDuplicateExistingAndCallerChosenAliases", "testSupplementRefusesSelfConsistentChangedWireAndForeignSourceSpace"]
 result["startLines"]=[x for x in log.splitlines() if "Test Case " in x and " started" in x]
 assert len(result["startLines"])==3
 assert all(sum(method in line for line in result["passLines"])==1 for method in expected_methods)
 assert all(sum(method in line for line in result["startLines"])==1 for method in expected_methods)
 result["compiledProducts"]={str(p.relative_to(CACHE)):sha(p) for p in sorted(CACHE.rglob("*")) if p.is_file() and p.name in ["PinkhaAnyHostTests-test-runner","PinkhaAnyHostTests.so"]}
 assert len(result["compiledProducts"])==2
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
 try:
  if before is not None:
   after=inventory();write(OUT/"source-after.json",after)
   result["sourceUnchanged"]=before==after
   assert result["sourceUnchanged"]
  result["sourceDefinitionsAfter"]=source_definitions()
  assert result["sourceDefinitionsAfter"]==result.get("sourceDefinitionsBefore",result["sourceDefinitionsAfter"])
  assert sha(Path(__file__))==controller_sha
  result["controllerSHA256"]=controller_sha
  if (OUT/"test.log").exists():result["logSHA256"]=sha(OUT/"test.log")
 except BaseException as e:
  result["status"]="FAIL";result["errors"].append({"type":type(e).__name__,"message":"final integrity: "+str(e)})
 save()
print(json.dumps({k:result[k] for k in ["status","sourceCommit","scope","seconds","errors"]}))
raise SystemExit(0 if result["status"]=="PASS" else 1)
