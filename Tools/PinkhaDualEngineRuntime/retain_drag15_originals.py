#!/usr/bin/env python3
"""Archive exact terminal App15 Drag originals; this is not simulator/account backup."""
import hashlib,json,os,stat,tarfile,time
from pathlib import Path
ROOT=Path("/Users/m1/development/anytype-d-active-20261125/main15")
OUT=ROOT/"drag-original-retention1"
PINS={
"native-drag-attempt1/receipt.json":"2cc75bb2b06f7325ffe8192520961b7ab93ff255596dffe3bf97399ff98b70b5",
"native-drag-attempt2/receipt.json":"a74fa451a820c9797354b3d067c41a9b91704ab5cf6cf4a064e93f16c56c3008",
"native-drag-attempt2-custody1/retention.json":"43dc39dec80e21aa78c59de302a0f504a4a3af7bef346c67ef5ca7042d40efb3",
}
SOURCES={name:ROOT/name for name in ("native-drag-attempt1","native-drag-attempt2","native-drag-attempt2-custody1","native-ui8ac-control-e6c4")}
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1024**2),b""):h.update(b)
 return h.hexdigest()
def identity(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns]
def write(path,value):
 with path.open("x") as f:json.dump(value,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
def inventory():
 rows={}
 for label,root in SOURCES.items():
  assert root.is_dir() and root.resolve()==root and not root.is_symlink()
  for p in [root]+sorted(root.rglob("*")):
   s=p.lstat();name=label+("/"+p.relative_to(root).as_posix() if p!=root else "")
   row={"mode":stat.S_IMODE(s.st_mode)}
   if stat.S_ISDIR(s.st_mode):row["kind"]="directory"
   elif stat.S_ISLNK(s.st_mode):row.update(kind="symlink",link=os.readlink(p))
   elif stat.S_ISREG(s.st_mode):row.update(kind="file",bytes=s.st_size,sha256=digest(p))
   else:raise RuntimeError("unsupported original entry")
   assert identity(p.lstat())==identity(s)
   rows[name]=row
 return rows
def verify_tar(path,expected):
 seen=set()
 with tarfile.open(path,"r:gz") as tf:
  for m in tf:
   name=m.name.rstrip("/")
   assert name not in seen and name in expected;seen.add(name)
   row=expected[name];assert m.mode==row["mode"]
   if m.isdir():assert row["kind"]=="directory"
   elif m.issym():assert row["kind"]=="symlink" and m.linkname==row["link"]
   elif m.isfile() or m.islnk():
    assert row["kind"]=="file"
    h=hashlib.sha256();n=0
    f=tf.extractfile(m);assert f is not None
    for b in iter(lambda:f.read(1024**2),b""):h.update(b);n+=len(b)
    assert n==row["bytes"] and h.hexdigest()==row["sha256"]
   else:raise RuntimeError("unsupported archive member")
 assert seen==set(expected)
 return len(seen)
def main():
 os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
 result={"protocol":"pinkha-app15-drag-terminal-originals-retention-v1","status":"FAIL",
 "appBuilds":0,"nativeCalls":0,"testCalls":0,"boots":0,"restores":0,
 "originalFirstAttemptStatus":"FAIL_ZERO_METHODS","originalSecondAttemptStatus":"PASS_ONE_ORIGINAL_METHOD",
 "fullSimulatorAccountCustody":False,"custodyLimitation":"Original owned device root absent at sealed 43dc custody attempt; surviving controller output and private native sandbox only.",
 "sources":{k:str(v) for k,v in SOURCES.items()},"pinnedReceipts":PINS,"startedEpoch":time.time()}
 try:
  for rel,expected in PINS.items():assert digest(ROOT/rel)==expected
  custody=json.loads((ROOT/"native-drag-attempt2-custody1/retention.json").read_bytes())
  assert custody["status"]=="FAIL"
  before=inventory();write(OUT/"inventory-before.json",before)
  archive=OUT/"originals.private.tar.gz"
  with tarfile.open(archive,"x:gz",compresslevel=1,format=tarfile.PAX_FORMAT) as tf:
   for name in sorted(before):
    label,_,rest=name.partition("/")
    p=SOURCES[label]/rest if rest else SOURCES[label]
    tf.add(p,arcname=name,recursive=False)
  n=verify_tar(archive,before)
  after=inventory();write(OUT/"inventory-after.json",after);assert before==after
  for rel,expected in PINS.items():assert digest(ROOT/rel)==expected
  result.update(status="PASS_SURVIVING_ORIGINALS_NOT_FULL_ACCOUNT_BACKUP",members=n,
   archive={"path":str(archive),"bytes":archive.stat().st_size,"sha256":digest(archive)},
   inventoryBeforeSHA256=digest(OUT/"inventory-before.json"),inventoryAfterSHA256=digest(OUT/"inventory-after.json"),
   allSourceEntriesUnchanged=True,sourceBytes=sum(r.get("bytes",0) for r in before.values()),
   sourceFiles=sum(r["kind"]=="file" for r in before.values()))
 except BaseException as e:result["failure"]={"type":type(e).__name__,"reason":str(e)}
 finally:
  result["finishedEpoch"]=time.time();write(OUT/"retention.json",result)
 print(json.dumps({"status":result["status"],"receipt":str(OUT/"retention.json"),"receiptSHA256":digest(OUT/"retention.json"),"archive":result.get("archive"),"members":result.get("members")}))
 return 0 if result["status"].startswith("PASS") else 1
if __name__=="__main__":raise SystemExit(main())
