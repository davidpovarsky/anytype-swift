#!/usr/bin/env python3
"""Qualify the retained Swift executable at its actual SwiftPM output path."""
import argparse,hashlib,json,stat
from pathlib import Path
ROOT=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-host/shared-fixture-attempt1")
PINS={
 "receipt.json":"47f5e014c545b095c4bb03563d0c650520d65a0d5f4b17395652b4e07f561a5f",
 "source-before.json":"5f5567c7b3c996e48892c849e5658bf86731f860269f4f9b9650f090e901822c",
 "commands/build/result.json":"7895d0c26ef362d1305e0288cd57edae3169077c1f4cc06f58e06bda99a240c5",
 "commands/build/started.json":"1f24618d207c668928febb5540c8e75fab7852ddc6d3612e9c256320ec555d98",
 "commands/build/original.log":"a2a7c9e9717efa8c36b151d7336eb48c4f9a087b30dab8b97f2eab04e51f0d84",
 "swift-build/out/Products/Debug-linux-aarch64/CutoverSharedFixture":"6d7003d580ef253c5666b14c4bef9b9e712cafa9349ba9830ed1e5faa9b0d2a7",
}
CONTROLLER="88702292860ec1753ec15414683526da2a91905a27df0d572d05ad73e99f92fe"
GENERATOR="2afb93590e7b44353bc8ab3d6b67c80e3179ae34ab8a3d9e37a80a243c98a49d"
def digest(p):
 before=p.lstat()
 if p.resolve()!=p or not stat.S_ISREG(before.st_mode):raise ValueError("unaliased regular input")
 with p.open("rb") as stream:value=hashlib.file_digest(stream,"sha256").hexdigest()
 after=p.lstat()
 if (before.st_ino,before.st_dev,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_dev,after.st_size,after.st_mtime_ns):raise ValueError("changed input")
 return value
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","originalProducerStatus":"FAIL","appBuilds":0,"nativeCalls":0,"newBuilds":0,"testsExecuted":0}
 try:
  directory=Path(__file__).resolve().parent
  if digest(directory/"qualify_shared_fixture.py")!=CONTROLLER or digest(directory/"CutoverSharedFixture.swift")!=GENERATOR:raise ValueError("original producer/code")
  for rel,pin in PINS.items():
   if digest(ROOT/rel)!=pin:raise ValueError("original pin "+rel)
  original=json.loads((ROOT/"receipt.json").read_text());build=json.loads((ROOT/"commands/build/result.json").read_text())
  if original["status"]!="FAIL" or original["error"]!="ValueError: one actual executable" or original["cleanupFailures"]!=[]:raise ValueError("exact original failure")
  if original["commands"]!=[build] or build["exitCode"]!=0 or build["ownedProcessGroupRemaining"]!=[]:raise ValueError("actual build outcome")
  if build["argv"]!=["/usr/local/bin/swift","build","--package-path",str(ROOT/"package"),"--scratch-path",str(ROOT/"swift-build"),"--jobs","2","--product","CutoverSharedFixture"]:raise ValueError("actual argv")
  log=(ROOT/"commands/build/original.log").read_text()
  if "Build complete!" not in log or build["logSHA256"]!=PINS["commands/build/original.log"]:raise ValueError("original successful stdout")
  expected=json.loads((ROOT/"source-before.json").read_text())
  actual={str(p.relative_to(ROOT/"package")):{"bytes":p.stat().st_size,"sha256":digest(p)}
   for p in sorted((ROOT/"package").rglob("*")) if p.is_file()}
  if actual!=expected or len(actual)!=71:raise ValueError("entire original source changed")
  binary=ROOT/"swift-build/out/Products/Debug-linux-aarch64/CutoverSharedFixture"
  if binary.stat().st_size!=6613720 or stat.S_IMODE(binary.stat().st_mode)!=0o755:raise ValueError("actual executable size/mode")
  with binary.open("rb") as stream:
   if stream.read(4)!=b"\x7fELF":raise ValueError("actual ELF")
  for rel,pin in PINS.items():
   if digest(ROOT/rel)!=pin:raise ValueError("original changed during qualification")
  (a.output/"source-after.json").write_text(json.dumps(actual,indent=2,sort_keys=True)+"\n")
  result.update(status="PASS_RETAINED_SHARED_SWIFT_GENERATOR_NOT_NATIVE_ACCEPTANCE",
    originalFailurePreserved=True,originalPins=PINS,completeSourceFiles=71,sourceUnchanged=True,
    binary=str(binary),binarySHA256=PINS[str(binary.relative_to(ROOT))],bytes=binary.stat().st_size,
    collectorOnlyCorrection="actual SwiftPM out/Products/Debug-linux-aarch64 path, no original build replay")
 except Exception as e:result["error"]=type(e).__name__+": "+str(e)
 (a.output/"receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
