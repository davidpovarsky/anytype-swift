#!/usr/bin/env python3
"""Real signed native host/ACL qualification, not App or peer acceptance."""
import argparse,hashlib,importlib.util,json,os,shutil,stat
from pathlib import Path
BASE=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1")
BASE_MANIFEST="32a701c389455d78d9a9271224921e3cc5772005481e3a7eac83312d2436c171"
CANDIDATE="559ef85407213d0f74b71a72f31b13af4f06d884bfd0dd163d20ed37d5c4a80c"
HELPER="c6104837aa3b5eca9abceda7bed4696d0249d840beefed7ec4f1be087138bd88"
FIXTURE_RECEIPT=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-host/shared-fixture-qualification1/receipt.json")
FIXTURE_RECEIPT_SHA="db5b5a4682a474730a78c2a2637fbd38f1ee8a3079ec5bd5a6a56a444571809c"
FIXTURE_BINARY_SHA="6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7"
NEW=[
"TestCutoverNativeSignedPhasesUnlinkAndReopen",
"TestCutoverNativeTwoAuthorsRetainAllBindingsAndOlderWriterDiverges",
"TestCutoverNativeCurrentACLAndRetiredLeaseRefuseReadAndRetry",
"TestCutoverNativeLostACKRetainsOneSignedBeginAndLeaseBoundary",
]
AFFECTED=[
"TestNativeCurrentWriteAuthority",
"TestNativeLocalAppendRequiresCommitGuard",
"TestNativeACLCommitFence",
"TestNativeCommitReceiptAfterHeadUpdateFailure",
"TestNativeCommitGuardKeepsHistoricalReplay",
"TestNativeTargetLeaseCoversDurableCommitAndReleasesBeforeHeadUpdate",
"TestNativeTargetLeaseReleasesOnCancelledPreparedAppend",
]
TEST_FILES=["native_transport_test.go","native_read_authority_test.go","native_write_authority_test.go",
"native_commit_guard_test.go","native_target_lease_test.go","cutover_native_host_test.go"]
def digest(p):
 if p.is_symlink() or not p.is_file():raise ValueError("regular input required: "+str(p))
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def save(root,name,value):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(".tmp")
 tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");tmp.replace(p)
def inventory(root,names):
 return {n:{"bytes":(root/n).stat().st_size,"sha256":digest(root/n)} for n in sorted(names)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);args=ap.parse_args()
 os.umask(0o077);root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","scope":"actual signed SyncTree/native ACL host; component legacy-property lease",
 "appBuilds":0,"peerTransport":False,"appRegistry":False,"actualAppPropertyLease":False,"newMethods":NEW,"affectedOriginalMethods":AFFECTED}
 commands=None;expected={};source=None
 try:
  directory=Path(__file__).resolve().parent
  if digest(directory/"qualify_store.py")!=HELPER:raise ValueError("owned command helper")
  spec=importlib.util.spec_from_file_location("cutover_runtime_commands",directory/"qualify_store.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);commands=module.Commands(root)
  if digest(directory/"native-host-runtime-candidate.json")!=CANDIDATE or digest(BASE/"source-after.json")!=BASE_MANIFEST:
   raise ValueError("source candidate/baseline")
  if digest(FIXTURE_RECEIPT)!=FIXTURE_RECEIPT_SHA:raise ValueError("original shared Swift generator qualification")
  fixture=json.loads(FIXTURE_RECEIPT.read_text());binary=Path(fixture["binary"])
  if fixture["status"]!="PASS_RETAINED_SHARED_SWIFT_GENERATOR_NOT_NATIVE_ACCEPTANCE" or digest(binary)!=FIXTURE_BINARY_SHA:raise ValueError("actual shared generator")
  candidate=json.loads((directory/"native-host-runtime-candidate.json").read_text())
  originals=json.loads((BASE/"source-after.json").read_text())
  if len(originals)!=4859 or shutil.disk_usage(root).free<3*1024**3:raise ValueError("baseline census/capacity")
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
    if rel!="core/block/editor/torahops/native_host.go" or originals[name]["sha256"]!=candidate["sourceBeforeNativeHostSHA256"]:raise ValueError("unexpected original replacement")
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest);expected[name]=row
  before=inventory(source,expected)
  if before!=expected:raise ValueError("whole source materialization")
  save(root,"source-before.json",before);save(root,"candidate.json",candidate)
  package=source/"heart/core/block/editor/torahops"
  selected=sorted(p.name for p in package.glob("*.go") if not p.name.endswith("_test.go"))+TEST_FILES
  save(root,"compiled-selection.json",{"files":{n:before[str((package/n).relative_to(source))] for n in selected},"new":NEW,"affected":AFFECTED,
   "reason":"original v1 Append body extracted, so original durable storage/signature/ACL/target lease cases are affected"})
  private=root/"private";private.mkdir(mode=0o700);(private/"native").mkdir(mode=0o700)
  env=dict(os.environ,GOWORK=str(source/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOCACHE=str(BASE/"cache"),
   PINKHA_CUTOVER_SHARED_FIXTURE=str(binary),PINKHA_CUTOVER_NATIVE_WORK=str(private/"native"))
  test=root/"cutover-native-host.test"
  commands.run("build",["/usr/local/bin/go","test","-c","-mod=readonly","-p","1","-o",str(test)]+selected,package,env,600)
  save(root,"binary.json",{"bytes":test.stat().st_size,"sha256":digest(test)})
  commands.run("binary-modules",["/usr/local/bin/go","version","-m",str(test)],package,env,30)
  log=commands.run("native-host",["/usr/local/bin/go","tool","test2json","-t","-p","cutover-native-host",str(test),
   "-test.v","-test.count=1","-test.timeout=240s","-test.run=^("+"|".join(NEW+AFFECTED)+")$"],package,env,300)
  rows=[json.loads(line) for line in log.read_text().splitlines()]
  passed=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
  methods=[n for n in passed if "/" not in n]
  result.update(methods=methods,passedRecords=passed,logSHA256=digest(log))
  if sorted(methods)!=sorted(NEW+AFFECTED) or len(methods)!=len(set(methods)) or any(r.get("Action") in ("skip","fail") for r in rows) or not any(r.get("Action")=="pass" and not r.get("Test") for r in rows):
   raise ValueError("exact native results")
  for rel,row in candidate["sourceFiles"].items():
   if digest(directory/"overlay"/rel)!=row["sha256"]:raise ValueError("candidate changed")
  if digest(binary)!=FIXTURE_BINARY_SHA or digest(FIXTURE_RECEIPT)!=FIXTURE_RECEIPT_SHA:raise ValueError("shared codec producer changed")
  result.update(status="PASS_SIGNED_NATIVE_CUTOVER_HOST_NOT_APP_OR_PEER_ACCEPTANCE",nativeHostMethods=len(NEW),
   originalAffectedMethods=len(AFFECTED),failures=0,skips=0,binarySHA256=digest(test),
   sharedCodecBinarySHA256=FIXTURE_BINARY_SHA,candidateSHA256=CANDIDATE)
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:
  if commands:
   try:
    failures=commands.cleanup();result["cleanupFailures"]=failures
    if failures:result["status"]="FAIL"
   except Exception as error:result.update(status="FAIL",cleanupError=str(error))
   result["commands"]=commands.rows
  if source is not None and expected:
   try:
    after=inventory(source,expected);save(root,"source-after.json",after)
    if after!=expected:raise ValueError("source changed")
    result["sourceUnchanged"]=True;result["sourceSHA256"]=digest(root/"source-after.json")
   except Exception as error:result.update(status="FAIL",sourceError=str(error))
  if (root/"private").exists():
   try:
    files=[str(p.relative_to(root/"private")) for p in (root/"private").rglob("*") if p.is_file()]
    save(root,"private-inventory.json",inventory(root/"private",files))
   except Exception as error:result.update(status="FAIL",retentionError=str(error))
  save(root,"receipt.json",result)
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
