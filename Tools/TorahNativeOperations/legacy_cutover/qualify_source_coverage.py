#!/usr/bin/env python3
"""Actual shared-codec source coverage qualification; no native or App calls."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path

BASE="cfa4b9a3dacf64be4b9d0e0c12a306f010d8bc55"
TORAH="9058b489e9acc271b4f8ef69e2ed24648f93b4ed"
JSON_HELPER="559217c1b572fd42ed84ee913614bade58228d640e3fe23d999c08de9cca391e"
COMMAND_HELPER="c6104837aa3b5eca9abceda7bed4696d0249d840beefed7ec4f1be087138bd88"
PINS={
"Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahLegacyAssociationCutoverPlan.swift":"747e6f65713460e99bb9bac93ea73eb7c20f4aa2048001460a33308662bc13a8",
"Modules/PinkhaKit/Tests/PinkhaKitTests/TorahLegacyAssociationCutoverPlanTests.swift":"406f94811efeac796848c84b8064ab6b3a415a6aeb6c577c6aa1fa0b36df7757",
"Tools/TorahNativeOperations/legacy_cutover/overlay/pkg/lib/pinkha/torahcutovercontract/contract.go":"a725194a6a3e43ec7b65c1279831e6ac8289871fac4b938cd41f5940194d89cc",
"Tools/TorahNativeOperations/legacy_cutover/overlay/pkg/lib/pinkha/torahcutovercontract/source_coverage.go":"2e5874f24c836c023aada60b0ae89927cd3ef16a4ceec2fa985f0a7a304b3088",
"Tools/TorahNativeOperations/legacy_cutover/overlay/pkg/lib/pinkha/torahcutovercontract/source_coverage_test.go":"7aee45d4ae244bdfbe1b55b2f55f7f7bbfa825f7b83a7f2331511868712d4fe5",
}
SWIFT_EXPECTED={
"testWholeSourceKeepsEveryUnknownFieldAndExactCanonicalFact",
"testLegacyV1UsesActualSharedCodecAndRetainsOriginalBytes",
"testMissingEmptyAndExplicitEmptyDocumentRemainDistinct",
"testDuplicateIdentityIsRefusedWithoutDroppingOneRecord",
"testForeignOwnersMalformedTargetsAndProviderRefuse",
"testNumericPrecisionAndEscapedDuplicateKeyRefuse",
"testSemanticOwnersAndTwoSameVerseAnchorsStayDistinct",
"testUnrepresentableLegacyUnknownEnvelopeRefusesEvenWhenEmpty",
"testOwnedSourceAndCanonicalOrderingAreStable",
"testExportActualSharedCodecVectorsForIndependentNativeCoverage",
}
GO_EXPECTED=[
"TestSourceCoverageUsesActualSharedCodecAndCanonicalFraming",
"TestSourceCoverageRefusesMissingDuplicateAndForeignFacts",
"TestSourceCoverageRefusesUnknownFieldLossAtEveryLevel",
"TestSourceCoverageExactNumbersDuplicateKeysAndUnicodeRefuse",
"TestSourceCoverageMarkerCannotMoveToAnotherOwnerOrBlock",
"TestSourceCoverageRetainsUnknownReservedMetadataWithoutRewriting",
"TestSourceCoverageEmptySourceCannotInventFacts",
"TestSourceCoverageMalformedLegacyDoesNotBecomeEmpty",
]
PKG="""// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "LegacyCutoverSourceQualification", defaultLocalization: "en",
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"], resources: [.process("Editor/Resources")]),
        .testTarget(name: "CutoverSourceTests", dependencies: ["PinkhaKit"])
    ], swiftLanguageModes: [.v6])
"""
def sha(path):
 with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(path,value):
 tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");tmp.replace(path)
def load_module(path,name,pin):
 if path.is_symlink() or sha(path)!=pin:raise ValueError("helper identity")
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source-tree",type=Path,required=True);ap.add_argument("--torah-tree",type=Path,required=True);ap.add_argument("--root",type=Path,required=True);args=ap.parse_args()
 root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","scope":"shared Swift codec and independent native coverage component only","nativeCalls":0,"appBuilds":0,"base":BASE,"torah":TORAH}
 commands=None;originals={}
 try:
  if shutil.disk_usage(root).free<3*1024**3:raise ValueError("capacity")
  helper=load_module(args.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_json_guard.py","source_helpers",JSON_HELPER)
  runner=load_module(args.source_tree/"Tools/TorahNativeOperations/legacy_cutover/qualify_store.py","owned_commands",COMMAND_HELPER)
  commands=runner.Commands(root)
  if helper.git(args.source_tree,"rev-parse","HEAD").decode().strip()!=BASE:raise ValueError("source HEAD")
  for rel,pin in PINS.items():
   path=args.source_tree/rel
   if path.is_symlink() or sha(path)!=pin:raise ValueError("new source pin: "+rel)
   originals[rel]=path.read_bytes()
  prefix="Modules/PinkhaKit/Sources/PinkhaKit/"
  tracked=helper.git(args.source_tree,"ls-tree","-r","--name-only",BASE,prefix).decode().splitlines()
  new=prefix+"Torah/TorahLegacyAssociationCutoverPlan.swift"
  actual=sorted(str(p.relative_to(args.source_tree)) for p in (args.source_tree/prefix).rglob("*") if p.is_file())
  if actual!=sorted(tracked+[new]):raise ValueError("whole shared source census")
  package=root/"swift-package";(package/"Sources").mkdir(parents=True)
  for rel in tracked:
   raw=helper.git(args.source_tree,"show",BASE+":"+rel)
   if (args.source_tree/rel).read_bytes()!=raw:raise ValueError("unreviewed shared source")
   path=package/"Sources/PinkhaKit"/rel.removeprefix(prefix);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  path=package/"Sources/PinkhaKit/Torah/TorahLegacyAssociationCutoverPlan.swift";path.write_bytes(originals[new])
  torah=helper.git(args.torah_tree,"ls-tree","-r","--name-only",TORAH,"Sources/TorahInspectorCore").decode().splitlines()
  if len(torah)!=8:raise ValueError("whole Torah Core")
  for rel in torah:
   path=package/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(helper.git(args.torah_tree,"show",TORAH+":"+rel))
  tests=package/"Tests/CutoverSourceTests";tests.mkdir(parents=True)
  (tests/"TorahLegacyAssociationCutoverPlanTests.swift").write_bytes(originals[next(k for k in PINS if "/Tests/" in k)])
  (package/"Package.swift").write_text(PKG)
  go=root/"go-package";go.mkdir();(go/"go.mod").write_text("module cutover-source-qualification\n\ngo 1.27.4\n")
  for rel,raw in originals.items():
   if rel.endswith(".go"):(go/Path(rel).name).write_bytes(raw)
  before={"swift":helper.snapshot(package),"go":helper.snapshot(go)}
  save(root/"source-before.json",before);save(root/"admission.json",{"pins":PINS,"base":BASE,"torah":TORAH,"wholeSharedFiles":len(actual),"wholeTorahCoreFiles":len(torah)})
  env=dict(os.environ,PINKHA_CUTOVER_VECTORS=str(root/"actual-shared-codec-vectors.json"))
  swiftlog=commands.run("swift-original",["/usr/local/bin/swift","test","--package-path",str(package),"--scratch-path",str(root/"swift-build"),"--jobs","2","--xunit-output",str(root/"original.xml"),"--filter","TorahLegacyAssociationCutoverPlanTests"],root,env,900)
  reports=[p for p in (root/"original.xml",root/"original-swift-testing.xml") if p.exists()]
  cases=[];selected=[]
  for report in reports:
   rows=ET.parse(report).findall(".//testcase")
   if rows:cases.extend(rows);selected.append({"path":report.name,"sha256":sha(report)})
  names=[c.attrib["name"].split("(")[0].split(".")[-1] for c in cases]
  if set(names)!=SWIFT_EXPECTED or len(cases)!=10 or any(c.find("failure") is not None or c.find("error") is not None or c.find("skipped") is not None for c in cases):raise ValueError("exact Swift original results")
  vectors=root/"actual-shared-codec-vectors.json"
  if vectors.is_symlink() or vectors.stat().st_size>2*1024**2 or len(json.loads(vectors.read_text()))!=9:raise ValueError("actual shared codec vectors")
  result.update(swiftMethods=names,swiftTests=10,swiftReports=selected,vectorsSHA256=sha(vectors),swiftLogSHA256=sha(swiftlog))
  env.update(GOWORK="off",GOTOOLCHAIN="local",GOMAXPROCS="2",GOCACHE=str(root/"go-cache"))
  golog=commands.run("go-original",["/usr/local/bin/go","test","-json","-count=1","-run","^TestSourceCoverage","."],go,env,300)
  rows=[json.loads(line) for line in golog.read_text().splitlines()]
  passed=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
  methods=[n for n in passed if "/" not in n]
  if methods!=GO_EXPECTED or len(passed)!=37 or any(r.get("Action") in ("skip","fail") for r in rows) or not any(r.get("Action")=="pass" and not r.get("Test") for r in rows):raise ValueError("exact native coverage component results")
  after={"swift":helper.snapshot(package),"go":helper.snapshot(go)};save(root/"source-after.json",after)
  if after!=before:raise ValueError("materialized source drift")
  for rel,raw in originals.items():
   if (args.source_tree/rel).read_bytes()!=raw:raise ValueError("candidate source changed")
  result.update(status="PASS_SHARED_CODEC_NATIVE_COVERAGE_COMPONENT",goMethods=methods,goCases=passed,failures=0,skips=0,goLogSHA256=sha(golog),sourceSHA256=sha(root/"source-before.json"))
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
