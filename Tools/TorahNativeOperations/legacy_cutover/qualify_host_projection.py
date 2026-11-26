#!/usr/bin/env python3
"""Compile the guarded native candidate and execute only new state-machine controls."""
import argparse,hashlib,importlib.util,json,os,shutil
from pathlib import Path
BASE=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1")
BASE_MANIFEST="32a701c389455d78d9a9271224921e3cc5772005481e3a7eac83312d2436c171"
CANDIDATE="7e3e56e9ae35d81aabb70868834137a71be257aa8b4a6eba6314a9c3538c2363"
HELPER="c6104837aa3b5eca9abceda7bed4696d0249d840beefed7ec4f1be087138bd88"
VECTORS=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-source-coverage/attempt2/actual-shared-codec-vectors.json")
VECTORS_SHA="e6c8a47abb2e1dca7702c5630e5f4259c48afc557caa673ff23f7e3b5eae46a2"
EXPECTED=[
"TestCutoverProjectionRequiresAllSourceFactsAndSecondPhase",
"TestCutoverProjectionTwoAuthorsRetainEveryPhysicalBinding",
"TestCutoverProjectionDurableSealSurvivesUnlinkWithoutLegacyResurrection",
"TestCutoverProjectionLateOfflineImportAfterRemovalIsVisibleConflict",
"TestCutoverProjectionOlderWriterDivergenceDoesNotUnionOrDelete",
"TestCutoverProjectionInvalidNativeReceiptCannotSeal",
"TestCutoverProjectionSameAuthorChangedRetryIsExplicitConflict",
"TestCutoverOriginalWriteGateRequiresSealAndRealObservedHistory",
]
def digest(p):
 if p.is_symlink() or not p.is_file():raise ValueError("not regular: "+str(p))
 with p.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(root,name,obj):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n");tmp.replace(p)
def inventory(root,names):
 return {n:{"bytes":(root/n).stat().st_size,"sha256":digest(root/n)} for n in sorted(names)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path);args=p.parse_args()
 root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","scope":"compile actual native host candidate and new pure interleaving projection controls","actualNativeCalls":0,"peers":0,"appBuilds":0,"existingAcceptedTestsReplayed":0}
 commands=None
 try:
  directory=Path(__file__).resolve().parent
  if digest(directory/"qualify_store.py")!=HELPER:raise ValueError("owned command helper")
  spec=importlib.util.spec_from_file_location("cutover_commands",directory/"qualify_store.py");runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner);commands=runner.Commands(root)
  if digest(directory/"native-host-candidate.json")!=CANDIDATE:raise ValueError("frozen source candidate")
  candidate=json.loads((directory/"native-host-candidate.json").read_text())
  if digest(BASE/"source-after.json")!=BASE_MANIFEST or digest(VECTORS)!=VECTORS_SHA:raise ValueError("original qualified sources or vectors")
  originals=json.loads((BASE/"source-after.json").read_text())
  if len(originals)!=4859:raise ValueError("baseline census")
  if shutil.disk_usage(root).free<2*1024**3:raise ValueError("capacity")
  source=root/"source";source.mkdir()
  for rel,row in originals.items():
   path=Path(rel)
   if path.is_absolute() or ".." in path.parts:raise ValueError("baseline path")
   donor=BASE/"source"/path
   if donor.stat().st_size!=row["bytes"] or digest(donor)!=row["sha256"]:raise ValueError("baseline source changed: "+rel)
   dest=source/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest)
  expected=dict(originals)
  for rel,row in candidate["sourceFiles"].items():
   donor=directory/"overlay"/rel
   if donor.stat().st_size!=row["bytes"] or digest(donor)!=row["sha256"]:raise ValueError("candidate source drift")
   name="heart/"+rel;dest=source/name
   if name in originals and originals[name]!=row:
    if rel!="core/block/editor/torahops/native_host.go" or originals[name]["sha256"]!=candidate["sourceBeforeNativeHostSHA256"]:raise ValueError("unexpected replacement")
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest);expected[name]=row
  before=inventory(source,expected)
  if before!=expected:raise ValueError("complete source")
  save(root,"source-before.json",before);save(root,"candidate.json",candidate)
  package=source/"heart/core/block/editor/torahops"
  selected=sorted(p.name for p in package.glob("*.go") if not p.name.endswith("_test.go"))+["cutover_projection_test.go"]
  save(root,"compiled-selection.json",{"files":{n:before[str((package/n).relative_to(source))] for n in selected},"selectors":EXPECTED})
  env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",
   GOCACHE=str(BASE/"cache"),PINKHA_CUTOVER_VECTORS=str(VECTORS))
  binary=root/"cutover-host-projection.test"
  commands.run("build",["/usr/local/bin/go","test","-c","-mod=readonly","-p","1","-o",str(binary)]+selected,package,env,600)
  save(root,"binary.json",{"bytes":binary.stat().st_size,"sha256":digest(binary)})
  commands.run("binary-modules",["/usr/local/bin/go","version","-m",str(binary)],package,env,20)
  log=commands.run("projection-controls",["/usr/local/bin/go","tool","test2json","-t","-p","cutover-native-projection",str(binary),"-test.v","-test.count=1","-test.timeout=60s","-test.run=^("+"|".join(EXPECTED)+")$"],package,env,90)
  rows=[json.loads(line) for line in log.read_text().splitlines()]
  passed=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
  result.update(passed=passed,logSHA256=digest(log))
  if passed!=EXPECTED or any(r.get("Action") in ("skip","fail") for r in rows):raise ValueError("exact original result")
  after=inventory(source,expected);save(root,"source-after.json",after)
  if after!=before:raise ValueError("materialized source drift")
  for rel,row in candidate["sourceFiles"].items():
   if digest(directory/"overlay"/rel)!=row["sha256"]:raise ValueError("candidate changed while compiling")
  if digest(VECTORS)!=VECTORS_SHA:raise ValueError("shared codec vectors changed")
  result.update(status="PASS_COMPILED_NATIVE_HOST_AND_PROJECTION_CONTROLS_NOT_NATIVE_ACCEPTANCE",methods=8,failures=0,skips=0,binarySHA256=digest(binary),sourceSHA256=digest(root/"source-before.json"),candidateSHA256=CANDIDATE)
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:
  if commands:
   try:
    failures=commands.cleanup();result["cleanupFailures"]=failures
    if failures:result["status"]="FAIL"
   except Exception as error:result.update(status="FAIL",cleanupError=str(error))
   result["commands"]=commands.rows
  save(root,"receipt.json",result)
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
