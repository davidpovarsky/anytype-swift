#!/usr/bin/env python3
"""Continue the original component build after the one pure-helper isolation correction."""
import argparse,hashlib,importlib.util,json,os,pathlib,shutil,signal,subprocess,tarfile,time,traceback
import xml.etree.ElementTree as ET
PRIOR={"result.json":"28c753631a6219ffb288fdf5f1122be810d9ef71c744377f0b629a54f6dd1cc7","admission.json":"105024463fed9557086dfc7b56d3b7e58e001977c456afd3ae528f2ccaf83cc3","source-before.json":"a3e05a083760b33847471b623abefc8b3484ec0fc9770d5d5ddf76f7040c36e6","source-after.json":"a3e05a083760b33847471b623abefc8b3484ec0fc9770d5d5ddf76f7040c36e6","original.log":"fd08df6d5c27a0b15fc8024b43b31258daf078922e42c73cc35d84a679da8c8a"}
SOURCE="Sources/PinkhaAnyIntegration/AnyTorahAssociationRepository.swift"
OLD="b86c5c2f95aa262bd873f9c847728232d10c0b3c9a941fdc9dfec1fa9c542063"
NEW="6b261cf6748118a743162234ab8d7cc2b7fdf8ad2a58b58280de87fa77c1aebb"
QUALIFIER="486ef80a974d9fb2b32c209a2dda41391a748ad4b2c1d403a40da3ab283091d5"
HELPER="559217c1b572fd42ed84ee913614bade58228d640e3fe23d999c08de9cca391e"
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+".tmp");t.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n");os.replace(t,p)
def load(p,pin,name):
 if p.is_symlink() or sha(p.read_bytes())!=pin:raise RuntimeError("controller-pin:"+name)
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 ap=argparse.ArgumentParser()
 for n in ["source-tree","prior","root"]:ap.add_argument("--"+n,type=pathlib.Path,required=True)
 a=ap.parse_args();a.root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","appBuilds":0,"nativeCalls":0,"scope":"Original80 Any component methods, incremental build after pure nonisolated helper correction"}
 p=None;absent=False;h=None;begin=time.monotonic()
 try:
  h=load(a.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_json_guard.py",HELPER,"original_json_helpers")
  q=load(a.source_tree/"Tools/TorahNativeOperations/heart_association_repository/qualify_any_shared_policy.py",QUALIFIER,"qualified_any_sources")
  for n,pin in PRIOR.items():
   if sha((a.prior/n).read_bytes())!=pin:raise RuntimeError("prior-original:"+n)
  prior=json.loads((a.prior/"result.json").read_text())
  if prior.get("status")!="FAIL" or prior.get("exitCode")!=1 or prior.get("ownedGroupAbsent") is not True or prior.get("error")!="RuntimeError('swift-tests-failed')":raise RuntimeError("prior-result")
  if "actor-isolated instance method 'nativeOperation(_:operationID:)' cannot be called" not in (a.prior/"original.log").read_text():raise RuntimeError("original-compiler-diagnostic")
  package=a.prior/"package";before=json.loads((a.prior/"source-before.json").read_text())
  if h.snapshot(package)!=before:raise RuntimeError("original-source-inventory")
  if h.git(a.source_tree,"rev-parse","HEAD").decode().strip()!=q.BASE:raise RuntimeError("source-head")
  for n,pin in q.PINS.items():
   if sha((a.source_tree/n).read_bytes())!=pin:raise RuntimeError("current-source-pin:"+n)
  old=(package/SOURCE).read_bytes();new=(a.source_tree/"Modules/PinkhaAnyIntegration"/SOURCE).read_bytes()
  if sha(old)!=OLD or sha(new)!=NEW or new.replace(b"private nonisolated func nativeOperation(",b"private func nativeOperation(")!=old:raise RuntimeError("single-isolation-delta")
  # Preserve every original production/dependency/test source before sequential cache reuse.
  archive=a.root/"prior-original-sources.tar.gz"
  with tarfile.open(archive,"w:gz") as t:
   for row in before:t.add(package/row["path"],arcname=row["path"],recursive=False)
  with tarfile.open(archive) as t:
   members=t.getmembers()
   if [m.name for m in members]!=[r["path"] for r in before]:raise RuntimeError("archive-path-census")
   for m,row in zip(members,before):
    if not m.isfile() or m.size!=row["bytes"] or sha(t.extractfile(m).read())!=row["sha256"]:raise RuntimeError("original-archive-bytes")
  if h.snapshot(package)!=before:raise RuntimeError("original-source-changed-during-retention")
  (package/SOURCE).write_bytes(new)
  expected=[dict(r,bytes=len(new),sha256=NEW) if r["path"]==SOURCE else r for r in before]
  if h.snapshot(package)!=expected:raise RuntimeError("single-updated-source-inventory")
  save(a.root/"source-before.json",expected)
  native="Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyTorahAssociationRepository.swift"
  gates=q.compatibility(h.git(a.source_tree,"show",q.BASE+":"+native).decode(),new.decode())
  admission=json.loads((a.prior/"admission.json").read_text())
  save(a.root/"admission.json",{"base":q.BASE,"priorOriginals":PRIOR,"priorOriginalSourceArchiveSHA256":sha(archive.read_bytes()),"sourceDelta":{"path":SOURCE,"before":OLD,"after":NEW},"originalTests":admission["originalTests"],"unchangedAuthoritySections":gates,"currentPins":q.PINS,"reusedOwnCache":str(a.prior/"build")})
  cmd=list(prior["command"]);cmd[cmd.index("--xunit-output")+1]=str(a.root/"original.xml")
  env=os.environ.copy();env["SWIFTCI_USE_LOCAL_DEPS"]="1"
  if shutil.disk_usage(a.root).free<3*1024**3:raise RuntimeError("capacity-admission")
  with (a.root/"original.log").open("wb") as log:
   p=subprocess.Popen(cmd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   result.update({"command":cmd,"pid":p.pid,"pgid":p.pid,"started":time.time()});save(a.root/"started.json",result)
   while p.poll() is None:
    if time.monotonic()-begin>1200:raise RuntimeError("deadline")
    if shutil.disk_usage(a.root).free<2*1024**3:raise RuntimeError("capacity-floor")
    time.sleep(1)
   result["exitCode"]=p.wait()
  rows=h.group_present(p.pid);absent=not rows;result["ownedGroupAbsent"]=absent
  if rows:raise RuntimeError("owned-group-remains")
  after=h.snapshot(package);save(a.root/"source-after.json",after)
  if after!=expected:raise RuntimeError("source-changed")
  for n,pin in q.PINS.items():
   if sha((a.source_tree/n).read_bytes())!=pin:raise RuntimeError("current-source-changed:"+n)
  if result["exitCode"]!=0:raise RuntimeError("swift-tests-failed")
  report=a.root/"original-swift-testing.xml";cases=ET.parse(report).findall(".//testcase")
  names={c.attrib["name"].split("(")[0] for c in cases};want={n for r in admission["originalTests"] for n in r["methods"]}
  if names!=want or len(cases)!=80 or len(want)!=80 or any(list(c) for c in cases):raise RuntimeError("original-exact-method-results")
  result.update({"status":"PASS_ORIGINAL_COMPONENTS_ONLY","tests":80,"failures":0,"skips":0,"methods":sorted(names),"sourceManifestSHA256":sha((a.root/"source-before.json").read_bytes()),"originalLogSHA256":sha((a.root/"original.log").read_bytes()),"originalXMLSHA256":sha(report.read_bytes())})
 except Exception as e:result.update({"error":repr(e),"traceback":traceback.format_exc()})
 finally:
  if p is not None and not absent:
   try:
    if p.poll() is None:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
    rows=h.group_present(p.pid);absent=not rows;result["cleanup"]={"pgid":p.pid,"absent":absent,"members":rows}
    if not absent:result["status"]="FAIL"
   except Exception as e:result["status"]="FAIL";result["cleanupError"]=repr(e)
  result["elapsed"]=time.monotonic()-begin;save(a.root/"result.json",result)
 print(json.dumps({k:result.get(k) for k in ["status","tests","failures","skips","error","elapsed"]}))
 return 0 if result["status"]=="PASS_ORIGINAL_COMPONENTS_ONLY" else 1
if __name__=="__main__":raise SystemExit(main())
