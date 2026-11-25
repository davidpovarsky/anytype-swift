#!/usr/bin/env python3
"""Run original affected Any domain/adapter tests over the shared planner, with exact source closure."""
import argparse, hashlib, importlib.util, json, os, pathlib, re, shutil, signal, subprocess, time, traceback
import xml.etree.ElementTree as ET
BASE="2f7ad2ce4b5b9b048d8fb5184aa2872c70c7d304"
TORAH="9058b489e9acc271b4f8ef69e2ed24648f93b4ed"
HELPER="559217c1b572fd42ed84ee913614bade58228d640e3fe23d999c08de9cca391e"
PINS={
"Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahAssociationRepository.swift":"6b261cf6748118a743162234ab8d7cc2b7fdf8ad2a58b58280de87fa77c1aebb",
"Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahPreparedMutation.swift":"0ead560345400729b0e320a73df4bac99df3673aa164a18d570c06bcbb8b74a1",
"Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahSourceJSONGuard.swift":"a40e49f4d3424e5625498e1a95baad171e22391a786d16c3f3e0c4c1ea926541"
}
DEPS={"swift-crypto":"e8d6eba1fef23ae5b359c46b03f7d94be2f41fed","swift-asn1":"917b472dbe53ba699cbb0495f9a95a084bc6364d"}
SUITES={"AssociationBridgeTests":37,"AssociationObservationTests":7,"AnyTorahObjectScopeTests":7,
        "AnyTorahNotesTests":8,"AnyTorahRelatedDocumentsTests":8,"AnyTorahArchiveTests":13}
PKG="""// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "AnySharedAssociationQualification", defaultLocalization: "en",
    dependencies: [.package(path: "Dependencies/swift-crypto")],
    targets: [
        .target(name: "TorahInspectorCore"),
        .target(name: "PinkhaKit", dependencies: ["TorahInspectorCore"], resources: [.process("Editor/Resources")]),
        .target(name: "PinkhaAnyEngine", dependencies: [.product(name: "Crypto", package: "swift-crypto")]),
        .target(name: "PinkhaAnyIntegration", dependencies: ["PinkhaKit", "PinkhaAnyEngine"]),
        .testTarget(name: "PinkhaAnyIntegrationTests", dependencies: ["PinkhaKit", "PinkhaAnyEngine", "PinkhaAnyIntegration"])
    ], swiftLanguageModes: [.v6])
"""
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+".tmp")
 tmp.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n");os.replace(tmp,p)
def compatibility(old,new):
 intervals=[
 ("watch","    public func watch(target:","    /// Decode one target"),
 ("object-watch","    public func watchObject(","    private func decodeObject("),
 ("native-object-authority","    private func decoded(target:","    private func decoded(projection:"),
 ("frozen-retry","    @discardableResult\n    public func commitPrepared(","    private func mutate("),
 ("append-authorization","    private func mutate(","    private func plannedMutation("),
 ("space-and-serialization","    private func checkSpace(",None),
 ]
 rows=[]
 for name,start,end in intervals:
  a=old[old.index(start):];b=new[new.index(start):]
  if end:a=a[:a.index(end)];b=b[:b.index(end)]
  if a!=b:raise RuntimeError("unchanged-authority-section:"+name)
  rows.append({"name":name,"bytes":len(a.encode()),"sha256":sha(a.encode())})
 return rows
def main():
 ap=argparse.ArgumentParser()
 for n in ["source-tree","torah-tree","dependencies","root"]:ap.add_argument("--"+n,type=pathlib.Path,required=True)
 a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","baseCommit":BASE,"torahCoreCommit":TORAH,"appBuilds":0,"nativeCalls":0,
         "scope":"80 original Any adapter/domain component methods; not native or Apple acceptance"}
 process=None;absent=False;started=time.monotonic();h=None
 try:
  if shutil.disk_usage(a.root).free<3*1024**3:raise RuntimeError("capacity-admission")
  hp=a.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_json_guard.py"
  if hp.is_symlink() or sha(hp.read_bytes())!=HELPER:raise RuntimeError("helper-identity")
  spec=importlib.util.spec_from_file_location("original_helpers",hp);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
  if h.git(a.source_tree,"rev-parse","HEAD").decode().strip()!=BASE:raise RuntimeError("source-head")
  originals={}
  for n,pin in PINS.items():
   p=a.source_tree/n;b=p.read_bytes()
   if p.is_symlink() or sha(b)!=pin:raise RuntimeError("source-pin:"+n)
   originals[n]=b
  repo="Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahAssociationRepository.swift"
  unchanged=compatibility(h.git(a.source_tree,"show",BASE+":"+repo).decode(),originals[repo].decode())
  package=a.root/"package";(package/"Sources").mkdir(parents=True)
  whole={}
  for module in ["PinkhaKit","PinkhaAnyEngine","PinkhaAnyIntegration"]:
   prefix="Modules/"+module+"/Sources/"+module+"/"
   names=h.git(a.source_tree,"ls-tree","-r","--name-only",BASE,prefix).decode().splitlines()
   actual=sorted(p.relative_to(a.source_tree).as_posix() for p in (a.source_tree/prefix).rglob("*") if p.is_file())
   if actual!=sorted(names):raise RuntimeError("whole-source-set:"+module)
   for n in names:
    b=(a.source_tree/n).read_bytes()
    if b!=originals.get(n,h.git(a.source_tree,"show",BASE+":"+n)):raise RuntimeError("unreviewed-source:"+n)
   shutil.copytree(a.source_tree/prefix,package/"Sources"/module,symlinks=True);whole[module]=len(names)
  tnames=h.git(a.torah_tree,"ls-tree","-r","--name-only",TORAH,"Sources/TorahInspectorCore").decode().splitlines()
  if len(tnames)!=8:raise RuntimeError("TorahCore-source-set")
  for n in tnames:
   dst=package/n;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(h.git(a.torah_tree,"show",TORAH+":"+n))
  original_tests=[];expected=set();testdir=package/"Tests/PinkhaAnyIntegrationTests";testdir.mkdir(parents=True)
  for suite,count in SUITES.items():
   n="Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/"+suite+".swift"
   b=h.git(a.source_tree,"show",BASE+":"+n)
   if (a.source_tree/n).read_bytes()!=b:raise RuntimeError("original-test-body-changed:"+suite)
   names=re.findall(r"@Test(?:\([^\n]*\))?\s+func\s+(\w+)",b.decode())
   if len(names)!=count:raise RuntimeError("original-method-census:"+suite)
   expected.update(names);(testdir/(suite+".swift")).write_bytes(b)
   original_tests.append({"suite":suite,"methods":names,"sha256":sha(b)})
  if len(expected)!=80:raise RuntimeError("original-exact-method-total")
  dependency_rows=[]
  for name,pin in DEPS.items():
   src=a.dependencies/name
   if h.git(src,"rev-parse","HEAD").decode().strip()!=pin or h.git(src,"status","--porcelain").strip():raise RuntimeError("dependency-git-pin:"+name)
   dst=package/"Dependencies"/name;shutil.copytree(src,dst,symlinks=True,ignore=shutil.ignore_patterns(".git"))
   dependency_rows.append({"name":name,"revision":pin})
  (package/"Package.swift").write_text(PKG)
  before=h.snapshot(package);save(a.root/"source-before.json",before)
  save(a.root/"admission.json",{"base":BASE,"pins":PINS,"wholeModules":whole,"torah":TORAH,"dependencies":dependency_rows,"originalTests":original_tests,"unchangedAuthoritySections":unchanged,"helperSHA256":HELPER})
  cmd=["/usr/local/bin/swift","test","--package-path",str(package),"--scratch-path",str(a.root/"build"),
       "--jobs","2","--xunit-output",str(a.root/"original.xml"),"--filter","|".join(SUITES)]
  env=os.environ.copy();env["SWIFTCI_USE_LOCAL_DEPS"]="1"
  with (a.root/"original.log").open("wb") as log:
   process=subprocess.Popen(cmd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   result.update({"pid":process.pid,"pgid":process.pid,"command":cmd,"localDependencyMode":"upstream SWIFTCI_USE_LOCAL_DEPS=1","started":time.time()});save(a.root/"started.json",result)
   while process.poll() is None:
    if time.monotonic()-started>1200:raise RuntimeError("deadline")
    if shutil.disk_usage(a.root).free<2*1024**3:raise RuntimeError("capacity-floor")
    time.sleep(1)
   result["exitCode"]=process.wait()
  rows=h.group_present(process.pid);absent=not rows;result["ownedGroupAbsent"]=absent
  if rows:raise RuntimeError("owned-group-remains")
  after=h.snapshot(package);save(a.root/"source-after.json",after)
  if before!=after:raise RuntimeError("materialized-source-changed")
  for n,b in originals.items():
   if (a.source_tree/n).read_bytes()!=b:raise RuntimeError("source-changed:"+n)
  if result["exitCode"]!=0:raise RuntimeError("swift-tests-failed")
  report=a.root/"original-swift-testing.xml";cases=ET.parse(report).findall(".//testcase")
  names={c.attrib["name"].split("(")[0] for c in cases}
  if names!=expected or len(cases)!=80 or any(list(c) for c in cases):raise RuntimeError("exact-original-method-results")
  result.update({"status":"PASS_ORIGINAL_COMPONENTS_ONLY","tests":80,"failures":0,"skips":0,"methods":sorted(names),
                "sourceManifestSHA256":sha((a.root/"source-before.json").read_bytes()),"originalLogSHA256":sha((a.root/"original.log").read_bytes()),"originalXMLSHA256":sha(report.read_bytes())})
 except Exception as e:result.update({"error":repr(e),"traceback":traceback.format_exc()})
 finally:
  if process is not None and not absent:
   try:
    if process.poll() is None:
     os.killpg(process.pid,signal.SIGTERM)
     try:process.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
    rows=h.group_present(process.pid);absent=not rows;result["cleanup"]={"pgid":process.pid,"absent":absent,"members":rows}
    if not absent:result["status"]="FAIL"
   except Exception as e:result["status"]="FAIL";result["cleanupError"]=repr(e)
  result["elapsed"]=time.monotonic()-started;save(a.root/"result.json",result)
 print(json.dumps({k:result.get(k) for k in ["status","tests","failures","skips","error","elapsed"]}))
 return 0 if result["status"]=="PASS_ORIGINAL_COMPONENTS_ONLY" else 1
if __name__=="__main__":raise SystemExit(main())
