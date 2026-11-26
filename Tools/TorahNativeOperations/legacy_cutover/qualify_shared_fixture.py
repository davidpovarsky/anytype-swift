#!/usr/bin/env python3
"""Build the actual shared Swift codec fixture generator; no App/native calls."""
import argparse,hashlib,importlib.util,json,os,shutil,stat
from pathlib import Path
BASE=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-source-coverage/attempt2")
BASE_MANIFEST="4e4a4d658b9912a89ff38ed247cc8742fbd9bf71a14ba4754da32892411c6427"
GENERATOR="2afb93590e7b44353bc8ab3d6b67c80e3179ae34ab8a3d9e37a80a243c98a49d"
HELPER="c6104837aa3b5eca9abceda7bed4696d0249d840beefed7ec4f1be087138bd88"
def digest(path):
 if path.is_symlink() or not path.is_file():raise ValueError("regular original required: "+str(path))
 with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()
def save(root,name,value):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(".tmp")
 tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");tmp.replace(p)
def snapshot(root):
 return {str(p.relative_to(root)):{"bytes":p.stat().st_size,"sha256":digest(p)}
  for p in sorted(root.rglob("*")) if p.is_file()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);args=ap.parse_args()
 root=args.root.resolve();root.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","scope":"actual shared-codec generator compilation only","appBuilds":0,"nativeCalls":0,"testsExecuted":0}
 commands=None
 try:
  directory=Path(__file__).resolve().parent
  if digest(directory/"qualify_store.py")!=HELPER:raise ValueError("owned helper")
  spec=importlib.util.spec_from_file_location("fixture_commands",directory/"qualify_store.py")
  helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);commands=helper.Commands(root)
  if digest(BASE/"source-before.json")!=BASE_MANIFEST or digest(directory/"CutoverSharedFixture.swift")!=GENERATOR:
   raise ValueError("original source binding")
  expected={row["path"]:{"bytes":row["bytes"],"sha256":row["sha256"]} for row in json.loads((BASE/"source-before.json").read_text())["swift"]}
  if len(expected)!=70 or shutil.disk_usage(root).free<3*1024**3:raise ValueError("source census/capacity")
  package=root/"package";package.mkdir()
  for rel,row in expected.items():
   path=Path(rel)
   if path.is_absolute() or ".." in path.parts:raise ValueError("source path")
   donor=BASE/"swift-package"/path
   if donor.stat().st_size!=row["bytes"] or digest(donor)!=row["sha256"]:raise ValueError("source drift: "+rel)
   dest=package/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(donor,dest)
  old=(package/"Package.swift").read_text()
  before='    targets: [\n'
  after='    products: [.executable(name: "CutoverSharedFixture", targets: ["CutoverSharedFixture"])],\n    targets: [\n        .executableTarget(name: "CutoverSharedFixture", dependencies: ["PinkhaKit"], path: "Fixture"),\n'
  if old.count(before)!=1:raise ValueError("original package shape")
  new=old.replace(before,after)
  if new.replace(after,before)!=old:raise ValueError("package inverse")
  (package/"Package.swift").write_text(new)
  target=package/"Fixture/CutoverSharedFixture.swift";target.parent.mkdir()
  shutil.copyfile(directory/"CutoverSharedFixture.swift",target)
  actual=snapshot(package)
  if set(actual)!=set(expected)|{"Fixture/CutoverSharedFixture.swift"}:raise ValueError("complete source census")
  for name,row in expected.items():
   if name!="Package.swift" and actual[name]!=row:raise ValueError("unrelated source drift")
  save(root,"source-before.json",actual)
  save(root,"source-admission.json",{"originalSnapshotSHA256":BASE_MANIFEST,"originalFiles":70,
   "unrelatedFilesUnchanged":69,"wholePackageInverse":True,"generatorSHA256":GENERATOR})
  commands.run("build",["/usr/local/bin/swift","build","--package-path",str(package),"--scratch-path",str(root/"swift-build"),"--jobs","2","--product","CutoverSharedFixture"],root,dict(os.environ),900)
  binaries=list((root/"swift-build").glob("*/debug/CutoverSharedFixture"))
  if len(binaries)!=1 or binaries[0].is_symlink() or not stat.S_IMODE(binaries[0].stat().st_mode)&0o111:
   raise ValueError("one actual executable")
  binary=binaries[0]
  if binary.read_bytes()[:4]!=b"\x7fELF":raise ValueError("native Linux executable")
  after=snapshot(package);save(root,"source-after.json",after)
  if after!=actual or digest(directory/"CutoverSharedFixture.swift")!=GENERATOR:raise ValueError("source changed")
  save(root,"binary.json",{"path":str(binary),"bytes":binary.stat().st_size,"sha256":digest(binary)})
  result.update(status="PASS_COMPILED_SHARED_SWIFT_FIXTURE_NOT_NATIVE_ACCEPTANCE",binary=str(binary),binarySHA256=digest(binary),
   sourceSHA256=digest(root/"source-before.json"),generatorSHA256=GENERATOR)
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
