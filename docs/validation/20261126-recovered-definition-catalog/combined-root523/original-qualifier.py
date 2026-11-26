#!/usr/bin/env python3
"""Qualify the recorded root523 dependency transition without repeating tests."""
from pathlib import Path
import hashlib,json,re,subprocess,os
BASE=Path("/mnt/development/projects/evidence/migration-final-20261125/recovered-definition-controls/combined-root523")
ACT=BASE/"actual"
SOURCE=BASE/"source"
CACHE=Path("/tmp/pinkha-c-swift-cache-20261125")
OLD=Path("/mnt/development/projects/worktrees/anytype-migration-final-20261125")
COMMIT="523f0747e25d2012f05f3bbc4da0e082773f8afc"
PINS={
 "result.json":"a4f3ee112560e2b6e8093250d803d6122250ee33e71bfece3147ab63e3f24173",
 "dependencies-before.json":"5a401246574e5a03b4abd63b3081677e1bee61955e59abe7ad67bca6bfa76b61",
 "dependencies-after.json":"0e503dfee7208fae26f583edbdb0b447ec527aaee5d1cd63ce5f9197988faa37",
 "original.log":"b834eca85234e82315a56e78941e22e4de83a83304ab2ffbbbd8e2c137a23349",
 "command.json":"d9f1cad6e9d24a50182ef7e6ffcddd29f554aee055a762f5207fc3b32e0e2c3c"}
def h(b):return hashlib.sha256(b).hexdigest()
def raw(p):
 assert p.is_file() and not p.is_symlink(),str(p)
 return p.read_bytes()
def load(p,expected=None):
 b=raw(p)
 if expected is not None: assert h(b)==expected,str(p)
 return json.loads(b)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":")).encode()
def qualify():
 inputs={n:raw(ACT/n) for n in PINS}
 for n,b in inputs.items():assert h(b)==PINS[n],n
 result=json.loads(inputs["result.json"])
 assert result["status"]=="FAIL" and result["errors"]==[{"error":"","type":"AssertionError"}]
 assert result["exitCode"]==0 and result["ownedGroupAbsent"] is True
 assert result["sourceCommit"]==COMMIT and result["sourceFiles"]==288
 assert result["sourceUnchanged"] is True and result["originalUnchanged"] is True
 assert result["dependenciesUnchanged"] is False and result["actualNativeCalls"]==0
 assert result["destinationWrites"] is False and result["sourceAdmission"] is False
 before=json.loads(inputs["dependencies-before.json"]);after=json.loads(inputs["dependencies-after.json"])
 assert len(before)==len(after)==6
 old={v["packageRef"]["identity"]:v for v in before}
 new={v["packageRef"]["identity"]:v for v in after}
 assert len(old)==len(new)==6 and old.keys()==new.keys()
 expected={k:json.loads(canonical(v)) for k,v in old.items()}
 local=[]
 for key,leaf in [("pinkhaanyengine","PinkhaAnyEngine"),("pinkhaanyintegration","PinkhaAnyIntegration"),("pinkhakit","PinkhaKit")]:
  row=expected[key];op=str(OLD/"Modules"/leaf);np=str(SOURCE/"Modules"/leaf)
  assert row["packageRef"]["kind"]=="fileSystem" and row["state"]["name"]=="fileSystem"
  assert row["packageRef"]["location"]==op and row["state"]["path"]==op
  row["packageRef"]["location"]=np;row["state"]["path"]=np
  local.append({"identity":key,"before":op,"after":np})
 row=expected["torahinspectorkit"]
 assert row["state"]["checkoutState"]=={"revision":"511454e49450cb2581ddf77f644146ff3e30dbef"}
 row["state"]["checkoutState"]={"revision":"9058b489e9acc271b4f8ef69e2ed24648f93b4ed"}
 assert expected==new
 source_before=load(ACT/"source-before.json");source_after=load(ACT/"source-after.json")
 assert source_before==source_after==load(BASE/"compiled-inputs.json") and len(source_before)==288
 for path,digest in source_before.items():
  p=SOURCE/path
  assert p.resolve().is_relative_to(SOURCE.resolve()) and h(raw(p))==digest,path
 locks=[]
 for path in sorted(source_before):
  if path.endswith("/Package.resolved"):
   pins={v["identity"]:v for v in load(SOURCE/path)["pins"]}
   for key in ["swift-asn1","swift-crypto","torahinspectorkit"]:
    assert pins[key]["state"]["revision"]==new[key]["state"]["checkoutState"]["revision"]
    assert pins[key]["location"]==new[key]["packageRef"]["location"]
   locks.append({"path":path,"sha256":source_before[path]})
 assert locks
 assert h(raw(BASE/"source-modules.tar"))=="0ce31eb28ba528effa3232c19e22c83c9c88a5349dcbbf8b1d7b803b69c9f6f2"
 current=load(CACHE/"workspace-state.json")["object"]["dependencies"]
 assert {v["packageRef"]["identity"]:v for v in current}==new
 checkouts=[]
 for key in ["swift-asn1","swift-crypto","torahinspectorkit"]:
  p=CACHE/"checkouts"/new[key]["subpath"]
  cmd=["git","-c","safe.directory="+str(p),"-C",str(p)]
  head=subprocess.run(cmd+["rev-parse","HEAD"],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
  assert head==new[key]["state"]["checkoutState"]["revision"]
  assert subprocess.run(cmd+["status","--porcelain","--untracked-files=no"],capture_output=True,text=True,check=True,timeout=15).stdout==""
  checkouts.append({"identity":key,"revision":head,"trackedClean":True})
 log=inputs["original.log"].decode()
 expected_methods=result["expectedMethods"]
 passed=re.findall(r"Test Case 'RecoveredCompiledDefinitionTests\.([^']+)' passed",log)
 assert len(passed)==len(expected_methods)==9 and set(passed)==set(expected_methods)==set(result["passedMethods"])
 assert "Executed 9 tests, with 0 failures" in log and "skipped" not in log.lower()
 assert "Build complete! (134.94 secs)" in log
 assert result["originalBefore"]==result["originalAfter"]=={"indexSHA256":"30420980bd3261a9e7284f7427ab47d8dc98f44e342549ea4d8c39a80073712b","originalBytes":1600701,"originalMemberCount":320,"unchanged":True}
 for n,b in inputs.items(): assert raw(ACT/n)==b,n
 return {"protocol":"pinkha-root523-observed-dependency-transition-v1",
  "status":"PASS_COMPONENT_ONLY_ORIGINAL_NINE_WITH_REQUESTED_ROOT_DEPENDENCIES",
  "originalControllerStatus":"FAIL","originalResultSHA256":PINS["result.json"],"originalLogSHA256":PINS["original.log"],
  "sourceCommit":COMMIT,"sourceFiles":288,"sourceUnchanged":True,
  "originalMethodsPassed":9,"originalFailures":0,"originalSkips":0,"repeatedMethods":0,
  "originalBuildSeconds":134.94,"originalTestSeconds":15.299,
  "localPackageRelocations":local,"dependencyTransition":{"identity":"torahinspectorkit","before":"511454e49450cb2581ddf77f644146ff3e30dbef","after":"9058b489e9acc271b4f8ef69e2ed24648f93b4ed"},
  "lockedInputs":locks,"currentTrackedCleanCheckouts":checkouts,
  "originalSourceMembersUnchanged":320,"originalOwnedGroupAbsentRecorded":True,
  "newProcessSignals":0,"actualNativeCalls":0,"sourceAdmission":False,"destinationWrites":False,
  "inputSHA256":PINS}
def main():
 out=BASE/"observed-resolution-qualification1"
 out.mkdir(mode=0o700,exist_ok=False)
 try:r=qualify()
 except BaseException as e:r={"protocol":"pinkha-root523-observed-dependency-transition-v1","status":"FAIL","errorType":type(e).__name__,"error":str(e),"repeatedMethods":0,"actualNativeCalls":0}
 r["qualifierSHA256"]=h(raw(Path(__file__)))
 b=json.dumps(r,indent=2,sort_keys=True).encode()+b"\n"
 (out/"result.json").write_bytes(b)
 print(json.dumps({"status":r["status"],"sha256":h(b),"path":str(out/"result.json")}))
 if r["status"]=="FAIL":raise SystemExit(1)
if __name__=="__main__": main()
