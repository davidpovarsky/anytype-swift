"""Preserve App14 originals, then reuse only its released compiler workspace for App15."""
from pathlib import Path
import os, json, hashlib, stat, subprocess, shutil, importlib.util, time

BASE=Path("/Users/m1/development/anytype-d-active-20261125")
ROOT=BASE/"main15"
PREVIOUS=BASE/"main14"
SOURCE=PREVIOUS/"source"
EXPECTED="379ca3568f247d2fc218ed63df24796d461713c0"
TREE="5ebb21544dcc0f81a468ad8e77beff2f96a73295"
OLD="76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
ASSEMBLY=BASE/"native8ac-combined"
MANIFEST="8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
PINS={
 "simulator":("evidence","946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b","efb1df9248d52f4ff69eb08e9a1ce9eeaed58b3b746960d86907fe7fc85fd903"),
 "device":("evidence-gateway-invocation-resume-1","c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208","fc251187ea1be539d41501da7b4e00ae2a249662684c1a5c6069235dacaee546")}
def require(ok,reason):
 if not ok:raise ValueError(reason)
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as stream:
  for block in iter(lambda:stream.read(1048576),b""):h.update(block)
 return h.hexdigest()
def write(path,value):
 with path.open("x") as stream:
  os.chmod(path,0o600);json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n");stream.flush();os.fsync(stream.fileno())
def load_module(path,name,expected):
 require(sha(path)==expected,"controller helper changed")
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def inventory(root):
 result={}
 require(root.resolve()==root and not root.is_symlink(),"canonical original root required")
 for path in sorted(root.rglob("*")):
  row={"mode":stat.S_IMODE(path.lstat().st_mode)}
  if path.is_symlink():row.update(kind="symlink",target=os.readlink(path))
  elif path.is_dir():row.update(kind="directory")
  elif path.is_file():row.update(kind="file",bytes=path.stat().st_size,sha256=sha(path))
  else:raise ValueError("unexpected nonpersistent workspace member")
  result[str(path.relative_to(root))]=row
 return result
def git(*args):
 result=subprocess.run(["git","-C",str(SOURCE),*args],capture_output=True,text=True,timeout=40)
 require(result.returncode==0,"read-only git failed:"+result.stderr)
 return result.stdout
def main():
 require(ROOT.is_dir() and ROOT.resolve()==ROOT,"original staged private root required")
 require(sha(ROOT/"source-inputs379/source379.bundle")=="3144c61910576a356c485ee93bfed63ecf53a59e5414e52ae03dccbeac63c96d","exact source bundle required")
 controls=load_module(ROOT/"source-inputs379/combined_heart_semantics_owned_outcomes.py","app15_owned_staging","73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a")
 evidence=ROOT/"source-staging1";evidence.mkdir(mode=0o700)
 commands=controls.Commands(evidence/"commands",ROOT)
 outcome={"status":"FAIL","started":time.time(),"sourceCommit":EXPECTED,"controllerSHA256":sha(Path(__file__)),"applicationBuilds":0,"nativeBuilds":0,"tests":0}
 try:
  require(git("rev-parse","HEAD").strip()==OLD and git("status","--porcelain")=="","original released source must remain clean App14")
  require(sha(PREVIOUS/"build14/receipt.json")=="b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6","original App14 producer receipt changed")
  require(sha(PREVIOUS/"build14/products-all.json")=="1941073f958baf7285b83ed411aef2b1a0d5dee75c2ff830510fb47b50d60109","original complete App14 products changed")
  old_sources=json.loads((PREVIOUS/"build14/source-before.json").read_bytes())
  require(old_sources["commit"]==OLD and old_sources==json.loads((PREVIOUS/"build14/source-after.json").read_bytes()),"original App14 source before/after mismatch")
  for relative,row in old_sources["files"].items():
   path=SOURCE/relative
   require(path.stat().st_size==row["bytes"] and sha(path)==row["sha256"],"original compiler source changed:"+relative)
  require(sha(ASSEMBLY/"receipt.json")=="c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231","actual assembly receipt required")
  require(sha(ASSEMBLY/"framework-files.json")=="fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf","actual assembled inventory required")
  assembly=json.loads((ASSEMBLY/"receipt.json").read_bytes())
  require(assembly["status"]=="PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE" and assembly["sourceManifestSHA256"]==MANIFEST,"actual coherent two-slice assembly required")
  # Only the released D compiler databases are inspected; no foreign process is signalled.
  for index,kind in enumerate(("app-derived","ui-derived")):
   database=PREVIOUS/kind/"Build/Intermediates.noindex/XCBuildData/build.db"
   if database.exists():
    result=subprocess.run(["/usr/sbin/lsof","-nP",str(database)],capture_output=True,text=True,timeout=10)
    write(evidence/("inactive-cache-"+str(index)+".json"),{"path":str(database),"exitCode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
    require(result.returncode==1 and not result.stdout and not result.stderr,"original mutable compiler cache is in use")
  free=shutil.disk_usage(ROOT).free
  require(free>=3*1024**3,"APFS clone metadata allowance plus original2GiB floor unavailable")
  retained=ROOT/"retained-App14";retained.mkdir(mode=0o700)
  before_source=inventory(SOURCE)
  write(evidence/"original-source-inventory.json",before_source)
  clone_mask=os.umask(0)
  try:
   commands.run(["/bin/cp","-cRp",str(SOURCE),str(retained/"source")],"preserve-original-source",240)
   require(inventory(retained/"source")==before_source==inventory(SOURCE),"full original source copy or original changed")
   old_products=json.loads((PREVIOUS/"build14/products-all.json").read_bytes())
   product_pins={}
   for kind in ("app-derived","ui-derived"):
    original=PREVIOUS/kind/"Build/Products"
    require(str(original)==old_products[kind]["base"],"original product root differs")
    expected=old_products[kind]["entries"]
    current=inventory(original)
    compact=[]
    for relative,row in current.items():
     if row["kind"]=="file":compact.append({"path":relative,"kind":"file","bytes":row["bytes"],"sha256":row["sha256"]})
     elif row["kind"]=="symlink":compact.append({"path":relative,"kind":"symlink","target":row["target"]})
    require(compact==expected,"all original App14 products must match producer")
    target=retained/(kind+"-Products")
    commands.run(["/bin/cp","-cRp",str(original),str(target)],"preserve-"+kind,180)
    require(inventory(target)==current==inventory(original),"all original product bytes/modes must be preserved")
    path=evidence/(kind+"-original-inventory.json");write(path,current)
    product_pins[kind]={"original":str(original),"retained":str(target),"inventorySHA256":sha(path),"entries":len(current)}
   require(git("rev-parse","HEAD").strip()==OLD and git("status","--porcelain")=="","original source changed before checked update")
   write(evidence/"original-preservation.json",{"status":"PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS","source":str(SOURCE),"retainedSource":str(retained/"source"),"sourceInventorySHA256":sha(evidence/"original-source-inventory.json"),"sourceEntries":len(before_source),"products":product_pins,"originalProducerSHA256":sha(PREVIOUS/"build14/receipt.json")})
   bundle=ROOT/"source-inputs379/source379.bundle"
   commands.run(["git","-C",str(SOURCE),"bundle","verify",str(bundle)],"source-bundle-verify",60)
   commands.run(["git","-C",str(SOURCE),"fetch",str(bundle),"HEAD"],"source-objects-import",60)
   commands.run(["git","-C",str(SOURCE),"checkout","--detach",EXPECTED],"source-checkout",60)
   require(git("rev-parse","HEAD").strip()==EXPECTED and git("rev-parse","HEAD^{tree}").strip()==TREE and git("status","--porcelain")=="","exact clean App15 source required")
   native=SOURCE/"Dependencies/Middleware/Lib.xcframework"
   require(inventory(native)==inventory(retained/"source/Dependencies/Middleware/Lib.xcframework"),"original native dependency changed before replacement")
   native.rename(retained/"original-native-dependency11619")
   commands.run(["/bin/cp","-cRp",str(ASSEMBLY/"Lib.xcframework"),str(native)],"materialize-native8ac",180)
   expected_native=json.loads((ASSEMBLY/"framework-files.json").read_bytes())
   actual_native={str(p.relative_to(native)):{"bytes":p.stat().st_size,"sha256":sha(p)} for p in sorted(native.rglob("*")) if p.is_file() and not p.is_symlink()}
   require(actual_native==expected_native and not any(p.is_symlink() for p in native.rglob("*")),"actual native8ac full framework differs")
   material=ROOT/"native-materialization-8ac";material.mkdir(mode=0o700)
   for name in ("receipt.json","framework-files.json"):
    data=(ASSEMBLY/name).read_bytes()
    with (material/name).open("xb") as f:f.write(data)
   inputs={}
   for kind,(folder,receipt_sha,command_sha) in PINS.items():
    origin=BASE/"native-permission8ac"/("pinkha-dual-native-v1-8ac407e75a4b-"+kind)/folder
    dest=material/kind;dest.mkdir(mode=0o700)
    values={}
    for key,name in (("receipt","receipt.json"),("command","combined-gomobile-bind.command.json"),("log","combined-gomobile-bind.log")):
     data=(origin/name).read_bytes();values[key]=data
     with (dest/name).open("xb") as f:f.write(data)
    require(hashlib.sha256(values["receipt"]).hexdigest()==receipt_sha and hashlib.sha256(values["command"]).hexdigest()==command_sha,"original actual slice provenance changed")
    receipt=json.loads(values["receipt"]);command=json.loads(values["command"])
    require([row for row in receipt["commands"] if row["name"]=="combined-gomobile-bind"]==[command],"exact original bind receipt row required")
    inputs[kind]=dict(values,expectedReceiptSHA256=receipt_sha,expectedCommandSHA256=command_sha)
   runtime=load_module(SOURCE/"Tools/PinkhaDualEngineRuntime/runtime_identity.py","app15_source_runtime_identity","306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0")
   manifest=(SOURCE/"Tools/PinkhaDualEngineRuntime/source-permission-manifest.json").read_bytes()
   require(hashlib.sha256(manifest).hexdigest()==MANIFEST,"exact native8ac source manifest required")
   binding=runtime.qualify_application(manifest,"2026-11-26",(SOURCE/"Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift").read_bytes(),inputs)
   require(binding["identity"]==assembly["runtimeIdentity"],"actual full native and Swift identities differ")
   write(evidence/"runtime-identity.json",binding)
   commands.run(["/bin/cp","-cRp",str(PREVIOUS/"ui-derived"),str(ROOT/"ui-derived")],"clone-small-ui-cache",180)
  finally:os.umask(clone_mask)
  require(git("rev-parse","HEAD").strip()==EXPECTED and git("status","--porcelain")=="","source changed during materialization")
  require(inventory(retained/"source")==before_source,"retained original source mutated")
  for kind in ("app-derived","ui-derived"):
   require(inventory(retained/(kind+"-Products"))==json.loads((evidence/(kind+"-original-inventory.json")).read_bytes()),"retained original products changed")
  require(sha(ASSEMBLY/"receipt.json")=="c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231","assembly changed")
  outcome.update(status="PASS_EXACT_APP15_SOURCE_AND_NATIVE_MATERIALIZED_ORIGINALS_RETAINED",sourceRoot=str(SOURCE),appDerived=str(PREVIOUS/"app-derived"),uiDerived=str(ROOT/"ui-derived"),tree=TREE,priorSource=OLD,originalPreservationSHA256=sha(evidence/"original-preservation.json"),runtimeIdentitySHA256=sha(evidence/"runtime-identity.json"),originalIntermediatesAndPackagePathsReused=True,freeBytesBefore=free)
 except BaseException as exc:
  outcome["error"]={"type":type(exc).__name__,"reason":str(exc)}
  raise
 finally:
  outcome["finished"]=time.time();outcome["freeBytesAfter"]=shutil.disk_usage(ROOT).free
  write(evidence/"receipt.json",outcome);print(json.dumps(outcome))
if __name__=="__main__":main()
