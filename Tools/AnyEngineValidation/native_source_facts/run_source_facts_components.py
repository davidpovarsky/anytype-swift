from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,time,signal,stat
ROOT=Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
CACHE=Path("/tmp/pinkha-w1-migration-swift-20261127")
CACHE_TARGET=Path("/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127")
MEASUREMENT=Path("/var/lib/pinkha-w1-functional-migration-20261127/source-facts-build-allocation1/result.json")
MEASUREMENT_SHA="371ab5bf4514da06aeade29ee43e6aa118aec3f116b461953174a4c75108437e"
CUSTODY=Path("/var/lib/pinkha-w1-functional-migration-20261127/swift-cache-relocation-continuation1/result.json")
CUSTODY_SHA="a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8"
MIB=1024**2
parser=argparse.ArgumentParser(description="Qualify three new source-facts methods without rerunning prior migration tests")
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--source-commit",required=True)
parser.add_argument("--preparation-manifest",type=Path,required=True)
parser.add_argument("--preparation-sha",required=True)
args=parser.parse_args()
assert re.fullmatch(r"[0-9a-f]{40}",args.source_commit)
assert re.fullmatch(r"[0-9a-f]{64}",args.preparation_sha)
assert args.preparation_manifest.resolve().is_relative_to(Path("/var/lib/pinkha-w1-functional-migration-20261127"))
OUT=args.output
assert OUT.is_absolute() and OUT.parent.resolve()==OUT.parent
assert str(OUT).startswith("/var/lib/pinkha-w1-functional-migration-20261127/")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
os.umask(0o077);OUT.mkdir(parents=True,exist_ok=False)
result={"status":"RUNNING","sourceCommit":args.source_commit,"scope":"Three new source-facts methods: exact retained two-row originals, complete historical values, changed-source refusals. Compile source-facts and prepared-association native fixtures without executing them; no182 replay.","errors":[]}
start=time.monotonic()
temporary=CACHE/("source-facts-temporary-"+OUT.name)
minimum_root=shutil.disk_usage("/").free
minimum_dev=shutil.disk_usage(CACHE).free
cache_allocated_before=None
last_allocation_check=0.0
def allocated_tree(root):
 total=0;seen=set()
 for base,dirs,files in os.walk(root,followlinks=False):
  for name in [None]+files:
   path=Path(base) if name is None else Path(base)/name
   try:s=path.lstat()
   except FileNotFoundError:continue
   identity=(s.st_dev,s.st_ino)
   if identity not in seen:total+=s.st_blocks*512;seen.add(identity)
 return total
def guard():
 global minimum_root,minimum_dev,last_allocation_check
 minimum_root=min(minimum_root,shutil.disk_usage("/").free)
 minimum_dev=min(minimum_dev,shutil.disk_usage(CACHE).free)
 assert minimum_root>=2*1024**3,"root2GiB emergency floor"
 assert minimum_dev>=512*MIB,"development512MiB emergency floor"
 assert time.monotonic()-start<900,"bounded incremental Swift build"
 assert not (OUT/"abort").exists(),"owned component build abort"
 if time.monotonic()-last_allocation_check>=2:
  last_allocation_check=time.monotonic()
  root_bytes=allocated_tree(OUT)
  result["maximumOwnedRootOutputBytes"]=max(root_bytes,result.get("maximumOwnedRootOutputBytes",0))
  assert root_bytes<=16*MIB,"bounded root control/log allocation"
  if cache_allocated_before is not None:
   growth=max(0,allocated_tree(CACHE)-cache_allocated_before)
   result["maximumOwnedDevelopmentGrowthBytes"]=max(growth,result.get("maximumOwnedDevelopmentGrowthBytes",0))
   assert growth<=256*MIB,"measured incremental development allocation cap"
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
SOURCE_OBJECT_HASHES={"617c89bab14769f612a69d726a58fc070c60f07a4304dcc2d52df3bb90a07bdc","8942e51b1fb58736a486dd484502614e9668b4ec48f5c794ac633feea7af0d34"}
def source_definitions():
 expected={
  "source-preservation-plan.json":"4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930",
  "execute-mappings.json":"eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3",
  "execute-verification.json":"fee4dc5cb8e689e01bf2d1fbe8bd262c42388fd706da4114be72af3e6cf97350"}
 for name,value in expected.items():assert sha(SOURCE/name)==value,name
 assert sha(BUNDLE/"manifest.json")==BUNDLE_SHA
 manifest=json.loads((BUNDLE/"manifest.json").read_bytes())
 rows=[v for v in manifest["Objects"] if hashlib.sha256(v["ObjectID"].encode()).hexdigest() in SOURCE_OBJECT_HASHES]
 assert len(rows)==len(SOURCE_OBJECT_HASHES)==2
 for row in rows:
  for field in ["Snapshot","NativeJSONView"]:
   member=row[field];file=BUNDLE/member["Path"]
   assert file.resolve().parent==BUNDLE and not file.is_symlink()
   assert file.stat().st_size==member["Bytes"] and sha(file)==member["SHA256"]
   expected["bundle/"+member["Path"]]=member["SHA256"]
 expected["bundle/manifest.json"]=BUNDLE_SHA
 return expected

def save():
 result["seconds"]=round(time.monotonic()-start,3)
 result["minimumRootFreeBytes"]=minimum_root
 result["minimumDevelopmentFreeBytes"]=minimum_dev
 write(OUT/"result.json",result)
child=None
before=None
controller_sha=sha(Path(__file__))
def interrupted(*_):raise RuntimeError("owned source-facts build interrupted")
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
try:
 (OUT/"controller.py").write_bytes(Path(__file__).read_bytes())
 assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==result["sourceCommit"]
 assert sha(args.preparation_manifest)==args.preparation_sha
 preparation=json.loads(args.preparation_manifest.read_bytes())
 assert preparation["status"]=="PREPARED_SOURCE_ONLY_NOT_COMPILED_OR_NATIVE_QUALIFIED"
 assert preparation["baseCommit"]==result["sourceCommit"]
 assert sha(args.preparation_manifest.with_name("swift-sources.json"))==preparation["swiftSourceClosureSHA256"]
 expected_source_closure=json.loads(args.preparation_manifest.with_name("swift-sources.json").read_bytes())
 for member in preparation["files"]:
  path=ROOT/member["path"]
  assert path.resolve().is_relative_to(ROOT) and not path.is_symlink()
  assert path.stat().st_size==member["bytes"] and sha(path)==member["sha256"]
 result["sourcePreparationManifestSHA256"]=args.preparation_sha
 result["preparedSwiftSourceClosureSHA256"]=preparation["swiftSourceClosureSHA256"]
 assert sha(MEASUREMENT)==MEASUREMENT_SHA and sha(CUSTODY)==CUSTODY_SHA
 measured=json.loads(MEASUREMENT.read_text())
 assert measured["status"]=="PASS_MEASUREMENT_ONLY_NO_COMPILER_OR_NATIVE_EXECUTION"
 assert measured["incrementalBuildBudgetBytes"]==256*MIB
 assert CACHE.is_symlink() and CACHE.resolve()==CACHE_TARGET
 result["allocationMeasurementSHA256"]=MEASUREMENT_SHA
 result["cacheCustodyReceiptSHA256"]=CUSTODY_SHA
 result["allocationPolicy"]={key:measured[key] for key in ["developmentBudgetMiB","rootInitialHeadroomBytes","rootControlOutputCapBytes","rootRuntimeEmergencyFloorBytes","developmentRuntimeEmergencyFloorBytes","rootInitialRequiredBytes","developmentInitialRequiredBytes"]}
 guard()
 assert minimum_root>=measured["rootInitialRequiredBytes"]
 assert minimum_dev>=measured["developmentInitialRequiredBytes"]
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
   assert subprocess.check_output(cmd+["rev-parse","HEAD"],text=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS="0")).strip()==expected[identity]
   assert not subprocess.check_output(cmd+["status","--porcelain","--untracked-files=no"],text=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS="0"))
  else:
   assert ref["kind"]=="fileSystem" and str(ROOT) in ref["location"]
 assert found==set(expected)
 result["dependencies"]=expected
 result["sourceDefinitionsBefore"]=source_definitions()
 before=inventory()
 assert before==expected_source_closure,"current Swift sources differ from the frozen prepared closure"
 write(OUT/"source-before.json",before)
 result["sourceBeforeSHA256"]=sha(OUT/"source-before.json")
 result["freeScratchBefore"]=shutil.disk_usage(CACHE).free
 result["freeRootBefore"]=shutil.disk_usage("/").free
 guard()
 assert result["freeRootBefore"]>=measured["rootInitialRequiredBytes"]
 assert result["freeScratchBefore"]>=measured["developmentInitialRequiredBytes"]
 cache_allocated_before=allocated_tree(CACHE)
 result["cacheAllocatedBefore"]=cache_allocated_before
 temporary.mkdir(mode=0o700,exist_ok=False)
 command=["/usr/local/bin/swift","test","--package-path",str(ROOT/"Modules/PinkhaAnyHost"),"--scratch-path",str(CACHE),"--disable-automatic-resolution","--jobs","2","--filter","NativeImportedSourceFactsTests"]
 result["command"]=command;save()
 with (OUT/"test.log").open("wb") as log:
  env={k:v for k,v in os.environ.items() if not k.startswith("PINKHA_NATIVE_")};env["PINKHA_NATIVE_DEFINITION_RETAINED"]=str(SOURCE);env["PINKHA_NATIVE_ORIGINAL156"]=str(BUNDLE.parent);env["TMPDIR"]=str(temporary)
  result["compilerTemporaryDirectory"]=str(temporary)
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
  result["pid"]=child.pid;save()
  while child.poll() is None:
   guard()
   time.sleep(.5)
  result["exitCode"]=child.wait(timeout=10)
 guard()
 after=inventory();write(OUT/"source-after.json",after)
 result["sourceAfterSHA256"]=sha(OUT/"source-after.json")
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
 expected_methods=["testTwoRetainedSourceFactsKeepCompleteOriginalBytesAndStructure","testHistoricalBindingsRequireCompleteOriginalDerivedValues","testSourceFactsRefuseChangedEvidenceAndInvalidMappings"]
 result["startLines"]=[line for line in log.splitlines() if "Test Case " in line and " started" in line]
 assert len(result["startLines"])==3
 assert all(sum(method in line for line in result["startLines"])==1 for method in expected_methods)
 assert all(sum(method in line for line in result["passLines"])==1 for method in expected_methods)
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
   result["sourceAfterSHA256"]=sha(OUT/"source-after.json")
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
