#!/usr/bin/env python3
"""Qualify the retained actual XCTest stdout, then run only the pending Go cases."""
import argparse, hashlib, importlib.util, json, os, re, shutil, xml.etree.ElementTree as ET
from pathlib import Path
ORIGINAL = Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-source-coverage/attempt2")
PRODUCER_SHA = "993c83f0c939b4537087b1c5a0cdcc8b795c4a52288fec990ef09a6c7acafd79"
ORIGINAL_PINS = {
 "receipt.json":"2409fb9a1a93bbacc0227edded442bb090ea2b63722fe2207800dd8bff738481",
 "admission.json":"d3d8027cfdd9c3d7cd8231d5cb007536fb843bbd189ef9698ae04a49f67dbfd8",
 "source-before.json":"4e4a4d658b9912a89ff38ed247cc8742fbd9bf71a14ba4754da32892411c6427",
 "actual-shared-codec-vectors.json":"e6c8a47abb2e1dca7702c5630e5f4259c48afc557caa673ff23f7e3b5eae46a2",
 "original-swift-testing.xml":"bee37f49bd66bea9b0acb8292c4d1452c23eb471cf803f82ce557ce2a5f17a1d",
 "commands/swift-original/started.json":"286b4bcf2fea127e9dd41386a32c75c528c8a18f8a156c0f96efe3545cf82ea7",
 "commands/swift-original/result.json":"fabbadfa4a3e2a8a374d9bb61fb4f8e372c0d5434cf6e99dafb5bf8ba22fadf5",
 "commands/swift-original/original.log":"8c9895b4c25f632fa3ce8de18721b6e2296c4b6d7535fb011310dadea080a609",
}
def digest(path):
 if path.is_symlink() or not path.is_file():raise ValueError("original is not a regular file: "+str(path))
 with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(path,value):
 tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");tmp.replace(path)
def verify_original():
 for rel,expected in ORIGINAL_PINS.items():
  if digest(ORIGINAL/rel)!=expected:raise ValueError("original changed: "+rel)
def qualify_swift(producer):
 verify_original()
 prior=json.loads((ORIGINAL/"receipt.json").read_text())
 command=json.loads((ORIGINAL/"commands/swift-original/result.json").read_text())
 started=json.loads((ORIGINAL/"commands/swift-original/started.json").read_text())
 if prior["status"]!="FAIL" or prior.get("error")!="ValueError: exact Swift original results" or prior.get("cleanupFailures")!=[] or prior.get("commands")!=[command]:
  raise ValueError("exact failed collector origin")
 if command.get("exitCode")!=0 or command.get("ownedProcessGroupRemaining")!=[] or command.get("timedOut") or command.get("observationError"):
  raise ValueError("actual Swift command")
 if not all(command.get(k)==v for k,v in started.items()):raise ValueError("original command start/end")
 expected=["/usr/local/bin/swift","test","--package-path",str(ORIGINAL/"swift-package"),"--scratch-path",str(ORIGINAL/"swift-build"),"--jobs","2","--xunit-output",str(ORIGINAL/"original.xml"),"--filter","TorahLegacyAssociationCutoverPlanTests"]
 if command["argv"]!=expected or command["logSHA256"]!=ORIGINAL_PINS["commands/swift-original/original.log"]:raise ValueError("exact original invocation")
 empty=ET.parse(ORIGINAL/"original-swift-testing.xml")
 suites=empty.findall(".//testsuite")
 if len(suites)!=1 or suites[0].attrib.get("tests")!="0" or empty.findall(".//testcase") or (ORIGINAL/"original.xml").exists():raise ValueError("original empty Swift Testing report")
 raw=(ORIGINAL/"commands/swift-original/original.log").read_text()
 started_names=re.findall(r"^Test Case 'TorahLegacyAssociationCutoverPlanTests\.([^']+)' started at .+$",raw,re.M)
 passed_names=re.findall(r"^Test Case 'TorahLegacyAssociationCutoverPlanTests\.([^']+)' passed \([0-9.]+ seconds\)$",raw,re.M)
 if len(started_names)!=10 or started_names!=passed_names or set(passed_names)!=producer.SWIFT_EXPECTED:raise ValueError("actual exact XCTest method pairs")
 if re.search(r"^Test Case .*(?:failed|skipped)",raw,re.M) or re.search(r"^.*(?:error:|fatal error:)",raw,re.M):raise ValueError("original XCTest failure")
 if len(re.findall(r"^\s*Executed 10 tests, with 0 failures \(0 unexpected\) in [0-9.]+ \([0-9.]+\) seconds$",raw,re.M))!=2:raise ValueError("original actual summary")
 if len(re.findall(r"^Test Suite '(?:Selected tests|TorahLegacyAssociationCutoverPlanTests)' passed at .+$",raw,re.M))!=2:raise ValueError("original suites")
 return {"methods":passed_names,"failures":0,"skips":0,"actualCommandExit":0,"stdoutSHA256":digest(ORIGINAL/"commands/swift-original/original.log"),"xmlContainsOnlyZeroSwiftTestingCases":True,"originalProducerStatusRetained":"FAIL","replayedSwiftMethods":0}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source-tree",required=True,type=Path);ap.add_argument("--root",required=True,type=Path);args=ap.parse_args()
 root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","nativeCalls":0,"appBuilds":0,"replayedSwiftMethods":0,"scope":"actual retained shared Swift codec tests plus independent Go coverage component"}
 commands=None
 try:
  p=args.source_tree/"Tools/TorahNativeOperations/legacy_cutover/qualify_source_coverage.py"
  if digest(p)!=PRODUCER_SHA:raise ValueError("original producer source")
  spec=importlib.util.spec_from_file_location("original_coverage_producer",p);producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
  helper=producer.load_module(args.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_json_guard.py","whole_source",producer.JSON_HELPER)
  runner=producer.load_module(args.source_tree/"Tools/TorahNativeOperations/legacy_cutover/qualify_store.py","owned_commands",producer.COMMAND_HELPER)
  commands=runner.Commands(root)
  swift=qualify_swift(producer);result["swiftQualification"]=swift
  before=json.loads((ORIGINAL/"source-before.json").read_text())
  current={"swift":helper.snapshot(ORIGINAL/"swift-package"),"go":helper.snapshot(ORIGINAL/"go-package")}
  if current!=before:raise ValueError("original complete materialized source")
  for rel,pin in producer.PINS.items():
   if digest(args.source_tree/rel)!=pin:raise ValueError("candidate source changed")
  if shutil.disk_usage(root).free<1024**3:raise ValueError("capacity")
  go=root/"go-package";shutil.copytree(ORIGINAL/"go-package",go)
  if helper.snapshot(go)!=before["go"]:raise ValueError("new exact Go source copy")
  save(root/"source-before.json",current)
  vectors=ORIGINAL/"actual-shared-codec-vectors.json"
  if vectors.stat().st_size>2*1024**2 or len(json.loads(vectors.read_text()))!=9:raise ValueError("actual codec vectors")
  env=dict(os.environ,GOWORK="off",GOTOOLCHAIN="local",GOMAXPROCS="2",GOCACHE=str(root/"go-cache"),PINKHA_CUTOVER_VECTORS=str(vectors))
  log=commands.run("go-original",["/usr/local/bin/go","test","-json","-count=1","-run","^TestSourceCoverage","."],go,env,300)
  rows=[json.loads(line) for line in log.read_text().splitlines()]
  passed=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
  methods=[name for name in passed if "/" not in name]
  result.update(goMethods=methods,goCases=passed,goLogSHA256=digest(log))
  if methods!=producer.GO_EXPECTED or len(passed)!=37 or any(r.get("Action") in ("skip","fail") for r in rows) or not any(r.get("Action")=="pass" and not r.get("Test") for r in rows):raise ValueError("exact Go actual results")
  after={"swift":helper.snapshot(ORIGINAL/"swift-package"),"go":helper.snapshot(ORIGINAL/"go-package")}
  if after!=before or helper.snapshot(go)!=before["go"]:raise ValueError("source drift")
  for rel,pin in producer.PINS.items():
   if digest(args.source_tree/rel)!=pin:raise ValueError("candidate drift")
  verify_original();save(root/"source-after.json",after)
  result.update(status="PASS_SHARED_CODEC_NATIVE_COVERAGE_COMPONENT",failures=0,skips=0,vectorsSHA256=digest(vectors),originalPins=ORIGINAL_PINS,candidatePins=producer.PINS)
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:
  if commands:
   try:
    failures=commands.cleanup();result["cleanupFailures"]=failures
    if failures:result["status"]="FAIL"
   except Exception as error:result.update(status="FAIL",cleanupError=str(error))
   result["commands"]=commands.rows
  save(root/"receipt.json",result)
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
