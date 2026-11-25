#!/usr/bin/env python3
"""Source-bound component qualification, no engine calls or application activation."""
import argparse, hashlib, importlib.util, json, os, pathlib, shutil, signal, subprocess, time, traceback
import xml.etree.ElementTree as ET
BASE="6586b6664ed817b6cfb60f6c701530f59e0e2105"
TORAH="9058b489e9acc271b4f8ef69e2ed24648f93b4ed"
HELPER="559217c1b572fd42ed84ee913614bade58228d640e3fe23d999c08de9cca391e"
PINS={
 "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahImmutableAssociationPolicy.swift":"5e80cb95aaffd87d4ba69c594a33a8ca7fce019d61ba6db192fe5f709bf2a498",
 "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Storage/TorahImmutableAssociationPolicyTests.swift":"ffd5ec915e7244f362045d4a492686dee152a47b5573d40b8b6264ed64b02204"
}
EXPECTED={
"defaultDuplicatePolicyKeepsEveryVariantAndRefusesWrites",
"explicitEqualFactsKeepBothClaimsAndRemoveAllObservedClaims",
"canonicalEqualityIncludesUnknownEnvelopeRecordAndItemFields",
"sameStableIDWithChangedSourceRemainsExplicitConflict",
"nativeCollisionOrMissingPredecessorNeverDisappearsUnderCoalescing",
"replacementPreservesStableIdentityAndAllUnknownLevels",
"defaultNoOpComparisonRetainsExistingAnyRawByteBehavior",
"missingUpdateAndMissingRemovalRemainDifferentOutcomes",
"duplicateNativeClaimsAndForeignExactOwnerAreRefused",
"unrepresentableUnknownNumberAndDuplicateJSONAreRefusedBeforePlanning",
"distinctQuotesRemainIndependentAndRemovalIsExactlyScoped",
"nativeObservedBoundRefusesWithoutDroppingAnyClaim"
}
PKG="""// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "ImmutableAssociationPolicyQualification", defaultLocalization: "en",
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"], resources: [.process("Editor/Resources")]),
        .testTarget(name: "ImmutablePolicyTests", dependencies: ["PinkhaKit"])
    ], swiftLanguageModes: [.v6])
"""
def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n"); os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source-tree",type=pathlib.Path,required=True);ap.add_argument("--torah-tree",type=pathlib.Path,required=True);ap.add_argument("--root",type=pathlib.Path,required=True);a=ap.parse_args()
 a.root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","baseCommit":BASE,"torahCoreCommit":TORAH,"appBuilds":0,"nativeCalls":0,
         "scope":"Pure shared immutable association policy; no repository activation, migration or engine acceptance"}
 process=None;absent=False;started=time.monotonic();helper=None
 try:
  if shutil.disk_usage(a.root).free<3*1024**3: raise RuntimeError("admission-capacity")
  hp=a.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_json_guard.py"
  if hp.is_symlink() or sha(hp.read_bytes())!=HELPER: raise RuntimeError("helper-identity")
  spec=importlib.util.spec_from_file_location("qualified_json_helpers",hp);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
  if helper.git(a.source_tree,"rev-parse","HEAD").decode().strip()!=BASE: raise RuntimeError("source-HEAD")
  originals={}
  for n,h in PINS.items():
   p=a.source_tree/n
   if p.is_symlink(): raise RuntimeError("source-link")
   b=p.read_bytes()
   if sha(b)!=h: raise RuntimeError("source-pin:"+n)
   originals[n]=b
  package=a.root/"package";(package/"Sources").mkdir(parents=True)
  prefix="Modules/PinkhaKit/Sources/PinkhaKit/"
  tracked=helper.git(a.source_tree,"ls-tree","-r","--name-only",BASE,prefix).decode().splitlines()
  new=prefix+"Torah/TorahImmutableAssociationPolicy.swift"
  actual=sorted(p.relative_to(a.source_tree).as_posix() for p in (a.source_tree/prefix).rglob("*") if p.is_file())
  if actual!=sorted(tracked+[new]): raise RuntimeError("complete-PinkhaKit-source-set")
  for n in tracked:
   if (a.source_tree/n).read_bytes()!=helper.git(a.source_tree,"show",BASE+":"+n): raise RuntimeError("unreviewed-PinkhaKit:"+n)
  shutil.copytree(a.source_tree/prefix,package/"Sources/PinkhaKit",symlinks=True)
  torah=helper.git(a.torah_tree,"ls-tree","-r","--name-only",TORAH,"Sources/TorahInspectorCore").decode().splitlines()
  if len(torah)!=8: raise RuntimeError("complete-TorahCore-source-set")
  for n in torah:
   dst=package/n;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(helper.git(a.torah_tree,"show",TORAH+":"+n))
  tests=package/"Tests/ImmutablePolicyTests";tests.mkdir(parents=True)
  (tests/"TorahImmutableAssociationPolicyTests.swift").write_bytes(originals[next(n for n in PINS if "/Tests/" in n)])
  (package/"Package.swift").write_text(PKG)
  before=helper.snapshot(package);save(a.root/"source-before.json",before)
  save(a.root/"admission.json",{"base":BASE,"torah":TORAH,"pins":PINS,"helperSHA256":HELPER,"wholePinkhaKitFiles":len(actual),"wholeTorahCoreFiles":len(torah)})
  cmd=["/usr/local/bin/swift","test","--package-path",str(package),"--scratch-path",str(a.root/"build"),"--jobs","2","--xunit-output",str(a.root/"original.xml"),"--filter","TorahImmutableAssociationPolicyTests"]
  with (a.root/"original.log").open("wb") as log:
   process=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   result.update({"pid":process.pid,"pgid":process.pid,"command":cmd,"started":time.time()});save(a.root/"started.json",result)
   while process.poll() is None:
    if time.monotonic()-started>900: raise RuntimeError("deadline")
    if shutil.disk_usage(a.root).free<2*1024**3: raise RuntimeError("capacity-floor")
    time.sleep(1)
   result["exitCode"]=process.wait()
  rows=helper.group_present(process.pid);absent=not rows
  result["ownedGroupAbsent"]=absent
  if rows: raise RuntimeError("owned-group-remains")
  after=helper.snapshot(package);save(a.root/"source-after.json",after)
  if before!=after: raise RuntimeError("materialized-source-changed")
  for n,b in originals.items():
   if (a.source_tree/n).read_bytes()!=b: raise RuntimeError("original-source-changed:"+n)
  if result["exitCode"]!=0: raise RuntimeError("swift-tests-failed")
  report=a.root/"original-swift-testing.xml";cases=ET.parse(report).findall(".//testcase")
  names={c.attrib["name"].split("(")[0] for c in cases}
  if names!=EXPECTED or len(cases)!=len(EXPECTED) or any(list(c) for c in cases): raise RuntimeError("exact-original-method-results")
  result.update({"status":"PASS_COMPONENT_ONLY","tests":len(cases),"failures":0,"skips":0,"methods":sorted(names),"sourceManifestSHA256":sha((a.root/"source-before.json").read_bytes()),"originalLogSHA256":sha((a.root/"original.log").read_bytes()),"originalXMLSHA256":sha(report.read_bytes())})
 except Exception as e: result.update({"error":repr(e),"traceback":traceback.format_exc()})
 finally:
  if process is not None and not absent:
   try:
    if process.poll() is None:
     os.killpg(process.pid,signal.SIGTERM)
     try: process.wait(timeout=10)
     except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
    rows=helper.group_present(process.pid);absent=not rows
    result["cleanup"]={"pgid":process.pid,"absent":absent,"members":rows}
    if not absent: result["status"]="FAIL"
   except Exception as e: result["status"]="FAIL";result["cleanupError"]=repr(e)
  result["elapsed"]=time.monotonic()-started
  save(a.root/"result.json",result)
 print(json.dumps({k:result.get(k) for k in ["status","tests","failures","skips","error","elapsed"]}))
 return 0 if result["status"]=="PASS_COMPONENT_ONLY" else 1
if __name__=="__main__":raise SystemExit(main())
