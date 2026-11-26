#!/usr/bin/env python3
"""Run the original ten cutover tests against the whole integrated PinkhaKit source."""
from pathlib import Path
import subprocess,hashlib,json,os,sys,time,signal,re,shutil
sys.dont_write_bytecode=True
SOURCE=Path("/mnt/development/projects/worktrees/anytype-final-integration-20261125")
COMMIT="88f1eacc261385a805cf2cf5253ac466db1fa390"
PRIOR=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-source-coverage/attempt2")
ROOT=Path("/mnt/development/projects/evidence/pinkha-integration-20261126T0258/swift-cutover-88f1")
PREFIX="Modules/PinkhaKit/Sources/PinkhaKit/"
TEST="Modules/PinkhaKit/Tests/PinkhaKitTests/TorahLegacyAssociationCutoverPlanTests.swift"
EXPECTED={
"testWholeSourceKeepsEveryUnknownFieldAndExactCanonicalFact",
"testLegacyV1UsesActualSharedCodecAndRetainsOriginalBytes",
"testMissingEmptyAndExplicitEmptyDocumentRemainDistinct",
"testDuplicateIdentityIsRefusedWithoutDroppingOneRecord",
"testForeignOwnersMalformedTargetsAndProviderRefuse",
"testNumericPrecisionAndEscapedDuplicateKeyRefuse",
"testSemanticOwnersAndTwoSameVerseAnchorsStayDistinct",
"testUnrepresentableLegacyUnknownEnvelopeRefusesEvenWhenEmpty",
"testOwnedSourceAndCanonicalOrderingAreStable",
"testExportActualSharedCodecVectorsForIndependentNativeCoverage"}
GO_PINS={"contract.go":"a725194a6a3e43ec7b65c1279831e6ac8289871fac4b938cd41f5940194d89cc","source_coverage.go":"2e5874f24c836c023aada60b0ae89927cd3ef16a4ceec2fa985f0a7a304b3088","source_coverage_test.go":"7aee45d4ae244bdfbe1b55b2f55f7f7bbfa825f7b83a7f2331511868712d4fe5"}
def require(c,m):
 if not c:raise ValueError(m)
def sha(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def save(p,v):
 with p.open("x") as f:json.dump(v,f,indent=2,sort_keys=True);f.write("\n")
def git(*args):
 return subprocess.check_output(["sudo","-n","-u","ubuntu","-g","chatgpt-agent","git","-C",str(SOURCE),*args],timeout=30)
def snapshot(p):
 rows=[]
 for f in sorted(p.rglob("*")):
  require(not f.is_symlink(),"symlink in qualification source")
  if f.is_file():rows.append({"path":str(f.relative_to(p)),"bytes":f.stat().st_size,"sha256":sha(f)})
 return rows
def main():
 ROOT.mkdir(mode=0o750)
 result={"status":"FAIL","sourceCommit":COMMIT,"scope":"whole integrated shared Swift sources with original ten cutover component methods","nativeCalls":0,"appBuilds":0,"fullEAcceptance":False,"goTestsReplayed":0}
 child=None;originals={}
 try:
  require(shutil.disk_usage(ROOT).free>512*1024**2,"measured component build capacity")
  require(git("rev-parse","HEAD").decode().strip()==COMMIT,"initial exact integration HEAD")
  require(sha(PRIOR/"source-before.json")=="4e4a4d658b9912a89ff38ed247cc8742fbd9bf71a14ba4754da32892411c6427","original source manifest")
  before_prior=json.loads((PRIOR/"source-before.json").read_text())
  package=ROOT/"swift-package";package.mkdir()
  rels=git("ls-tree","-r","--name-only",COMMIT,"--",PREFIX).decode().splitlines()
  actual=sorted(str(f.relative_to(SOURCE)) for f in (SOURCE/PREFIX).rglob("*") if f.is_file())
  require(sorted(rels)==actual,"whole current PinkhaKit source census")
  production=[]
  for rel in rels+[TEST]:
   data=git("show",COMMIT+":"+rel)
   require((SOURCE/rel).read_bytes()==data,"current production differs from Git "+rel)
   originals[rel]=hashlib.sha256(data).hexdigest()
   production.append({"path":rel,"bytes":len(data),"sha256":originals[rel]})
   target=package/("Sources/PinkhaKit/"+rel.removeprefix(PREFIX) if rel!=TEST else "Tests/CutoverSourceTests/"+Path(rel).name)
   target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  require(originals[TEST]=="406f94811efeac796848c84b8064ab6b3a415a6aeb6c577c6aa1fa0b36df7757","original ten test source")
  core=[r for r in before_prior["swift"] if r["path"].startswith("Sources/TorahInspectorCore/")]
  require(len(core)==8,"whole original Torah Core source")
  for row in core:
   src=PRIOR/"swift-package"/row["path"]
   require(src.stat().st_size==row["bytes"] and sha(src)==row["sha256"],"original Torah Core")
   target=package/row["path"];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src.read_bytes())
  pkg=PRIOR/"swift-package/Package.swift"
  require(sha(pkg)=="6d4fd2141db95e153f15967c9dc6a416b3c14c335ea29014f1f4872692c276e9","explicit original standalone package projection")
  (package/"Package.swift").write_bytes(pkg.read_bytes())
  for name,pin in GO_PINS.items():
   p=SOURCE/"Tools/TorahNativeOperations/legacy_cutover/overlay/pkg/lib/pinkha/torahcutovercontract"/name
   require(sha(p)==pin,"retained Go evidence source impacted "+name);originals[str(p.relative_to(SOURCE))]=pin
  before=snapshot(package);save(ROOT/"source-before.json",before)
  save(ROOT/"production-admission.json",{"sourceCommit":COMMIT,"productionFiles":production,"torahCommit":"9058b489e9acc271b4f8ef69e2ed24648f93b4ed","torahFiles":core,"standalonePackageProjectionSHA256":sha(pkg),"goSourcePins":GO_PINS,"scope":result["scope"]})
  env=dict(os.environ,PINKHA_CUTOVER_VECTORS=str(ROOT/"actual-shared-codec-vectors.json"))
  argv=["/usr/local/bin/swift","test","--package-path",str(package),"--scratch-path",str(ROOT/"swift-build"),"--jobs","2","--xunit-output",str(ROOT/"original.xml"),"--filter","TorahLegacyAssociationCutoverPlanTests"]
  started=time.time()
  with (ROOT/"original.log").open("xb") as log:
   child=subprocess.Popen(argv,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   pgid=os.getpgid(child.pid)
   save(ROOT/"started.json",{"argv":argv,"pid":child.pid,"pgid":pgid,"startedAt":started})
   timed_out=False
   try:code=child.wait(timeout=900)
   except subprocess.TimeoutExpired:
    timed_out=True;os.killpg(pgid,signal.SIGTERM)
    try:code=child.wait(timeout=15)
    except subprocess.TimeoutExpired:os.killpg(pgid,signal.SIGKILL);code=child.wait(timeout=5)
  outcome={"exitCode":code,"pid":child.pid,"pgid":pgid,"timedOut":timed_out,"elapsed":time.time()-started,"logSHA256":sha(ROOT/"original.log")}
  save(ROOT/"process-exit.json",outcome)
  observations=[];absent=False
  for delay in [0,.05,.1,.2,.4,.8,1]:
   if delay:time.sleep(delay)
   try:os.killpg(pgid,0);observations.append({"pgid":pgid,"state":"PRESENT"})
   except ProcessLookupError:observations.append({"pgid":pgid,"state":"ABSENT_ESRCH"});absent=True;break
   except PermissionError:observations.append({"pgid":pgid,"state":"UNKNOWN_EPERM"});break
  save(ROOT/"owned-group-observations.json",observations)
  require(code==0 and not timed_out and absent,"actual command exit or group absence")
  log=(ROOT/"original.log").read_text()
  ran=re.findall(r"^Test Case 'TorahLegacyAssociationCutoverPlanTests\.([^']+)' started at .+$",log,re.M)
  passed=re.findall(r"^Test Case 'TorahLegacyAssociationCutoverPlanTests\.([^']+)' passed \([0-9.]+ seconds\)$",log,re.M)
  require(len(ran)==10 and ran==passed and set(passed)==EXPECTED,"actual exact XCTest method pairs")
  require(not re.search(r"^Test Case .*(?:failed|skipped)",log,re.M) and not re.search(r"^.*(?:error:|fatal error:)",log,re.M),"actual failure or skip")
  require(len(re.findall(r"^\s*Executed 10 tests, with 0 failures \(0 unexpected\) in [0-9.]+ \([0-9.]+\) seconds$",log,re.M))==2,"two actual zero-failure summaries")
  require(len(re.findall(r"^Test Suite '(?:Selected tests|TorahLegacyAssociationCutoverPlanTests)' passed at .+$",log,re.M))==2,"actual suites")
  vectors=ROOT/"actual-shared-codec-vectors.json"
  require(sha(vectors)=="e6c8a47abb2e1dca7702c5630e5f4259c48afc557caa673ff23f7e3b5eae46a2" and len(json.loads(vectors.read_text()))==9,"unchanged actual shared vectors required for Go evidence reuse")
  after=snapshot(package);save(ROOT/"source-after.json",after)
  require(after==before,"materialized source drift")
  for rel,pin in originals.items():require(sha(SOURCE/rel)==pin,"production source drift "+rel)
  result.update(status="PASS_TEN_ORIGINAL_CUTOVER_METHODS_ON_INTEGRATED_SHARED_SOURCES",methods=passed,passed=10,failed=0,skipped=0,wholeSharedSourceFiles=len(rels),sourceUnchanged=True,sourceManifestSHA256=sha(ROOT/"source-before.json"),logSHA256=sha(ROOT/"original.log"),vectorsSHA256=sha(vectors),ownedGroupAbsent=True,command=outcome,goOriginalEvidenceReusableBecauseSourceAndActualVectorsUnchanged=True)
 except BaseException as exc:
  result["error"]={"type":type(exc).__name__,"message":str(exc)}
 finally:
  save(ROOT/"RESULT.json",result)
 print(json.dumps(result,sort_keys=True))
 return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
