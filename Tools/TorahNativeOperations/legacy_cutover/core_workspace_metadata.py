#!/usr/bin/env python3
"""Admit only the eight observed go.mod checksums; original zero-test FAIL stays FAIL."""
import base64,hashlib,json
from pathlib import Path
ORIGINAL=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-core/attempt1")
PINS={
"receipt.json":"972b2542f0be9504e39480ad43a236ee8db6efa8ef3072c3d22437520a94cab0",
"source-before.json":"34ce0b14654b02f0e5e8ed955fc27e28f95e7a26f408c783650fcb8b10879de3",
"source-after.json":"e58408f9f9b1e9edd8e079788815f376bd628a4a8689b5c4dd7fe16e9f9ad174",
}
BEFORE={"bytes":27287,"sha256":"ddc42c4028fd3a0d1dc6ccac0941d8d607c084b3f64e4c7ae116c8dbfeb824e4"}
AFTER={"bytes":27989,"sha256":"0ce118248f3e2580833e915dbd3ef14925d3a71a1601e4c7d679b9217a368586"}
ADDITIONS=[
"github.com/kballard/go-shellquote v0.0.0-20180428030007-95032a82bc51/go.mod h1:CzGEWj7cYgsdH8dAjBGEr58BoE7ScuLd+fwFZ44+/x8=",
"lukechampine.com/uint128 v1.2.0/go.mod h1:c4eWIwlEGaxC/+H1VguhU4PHXNWDCDMUlWdIWl2j1gk=",
"modernc.org/cc/v3 v3.41.0/go.mod h1:Ni4zjJYJ04CDOhG7dn640WGfwBzfE0ecX8TyMB0Fv0Y=",
"modernc.org/ccgo/v3 v3.17.0/go.mod h1:Sg3fwVpmLvCUTaqEUjiBDAvshIaKDB0RXaf+zgqFu8I=",
"modernc.org/ccorpus2 v1.5.4/go.mod h1:Wifvo4Q/qS/h1aRoC2TffcHsnxwTikmi1AuLANuucJQ=",
"modernc.org/lex v1.1.1/go.mod h1:6r8o8DLJkAnOsQaGi8fMoi+Vt6LTbDaCrkUK729D8xM=",
"modernc.org/lexer v1.0.4/go.mod h1:tOajb8S4sdfOYitzCgXDFmbVJ/LE0v1fNJ7annTw36U=",
"modernc.org/scannertest v1.0.2/go.mod h1:RzTm5RwglF/6shsKoEivo8N91nQIoWtcWI7ns+zPyGA=",
]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
 if path.resolve()!=path or path.is_symlink() or not path.is_file():raise ValueError("canonical regular metadata")
 return path.read_bytes()
def checksum_delta(before,after,old,new):
 if set(before)!=set(after) or [k for k in before if before[k]!=after[k]]!=["go.work.sum"]:raise ValueError("only pinned workspace checksum differs")
 if before["go.work.sum"]!=BEFORE or after["go.work.sum"]!=AFTER:raise ValueError("exact observed checksum rows")
 if len(old)!=BEFORE["bytes"] or sha(old)!=BEFORE["sha256"] or len(new)!=AFTER["bytes"] or sha(new)!=AFTER["sha256"]:raise ValueError("actual checksum bytes")
 lines=new.decode().splitlines()
 if len(lines)!=len(set(lines)) or set(lines)-set(old.decode().splitlines())!=set(ADDITIONS):raise ValueError("exact eight metadata additions")
 if ("\n".join(x for x in lines if x not in ADDITIONS)+"\n").encode()!=old:raise ValueError("full inverse checksum bytes")
def admit():
 for name,pin in PINS.items():
  if sha(read(ORIGINAL/name))!=pin:raise ValueError("original failed producer pin: "+name)
 result=json.loads(read(ORIGINAL/"receipt.json"))
 if result.get("status")!="FAIL" or result.get("error")!="ValueError: module metadata changed before compilation" or result.get("cleanupFailures")!=[]:raise ValueError("original failure remains distinct")
 commands=result.get("commands",[])
 if len(commands)!=3 or [x["argv"][1] for x in commands]!=["version","env","list"] or any(x.get("status")!="PASS" or x.get("exitCode")!=0 or x.get("groupState")!="ABSENT_ESRCH" for x in commands):raise ValueError("zero compiler/account/test calls")
 if any((ORIGINAL/"commands"/n).exists() for n in ("build","actual-core")) or json.loads(read(ORIGINAL/"private-inventory.json"))!={}:raise ValueError("no original native invocation")
 before=json.loads(read(ORIGINAL/"source-before.json"));after=json.loads(read(ORIGINAL/"source-after.json"))
 base=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1/source/go.work.sum")
 old=read(base);new=read(ORIGINAL/"source/go.work.sum")
 checksum_delta(before,after,old,new)
 current={}
 for p in sorted((ORIGINAL/"source").rglob("*")):
  if p.is_symlink():raise ValueError("original source symlink")
  if p.is_file():current[str(p.relative_to(ORIGINAL/"source"))]={"bytes":p.stat().st_size,"sha256":sha(read(p))}
 if current!=after:raise ValueError("all original native source bytes")
 log=ORIGINAL/"commands/module-graph/original.log"
 if sha(read(log))!=commands[2]["logSHA256"]:raise ValueError("original actual module graph")
 proofs=[]
 for line in ADDITIONS:
  module,version,wanted=line.split()
  p=Path("/root/go/pkg/mod/cache/download")/module/"@v"/(version.removesuffix("/go.mod")+".mod")
  raw=read(p);observed="h1:"+base64.b64encode(hashlib.sha256((sha(raw)+"  go.mod\n").encode()).digest()).decode()
  if observed!=wanted:raise ValueError("actual native Go Hash1 module bytes")
  proofs.append({"module":module,"version":version,"sum":observed,"bytes":len(raw),"sha256":sha(raw),"raw":raw})
 proof={"protocol":"pinkha-core-metadata-admission-v1","status":"PASS_EXACT_METADATA_ONLY_NOT_NATIVE_ACCEPTANCE","originalProducerStatus":"FAIL","originalReceipts":PINS,"sourceEntries":len(before),"otherSourceEntriesUnchanged":len(before)-1,"before":BEFORE,"after":AFTER,"additions":[{k:v for k,v in x.items() if k!="raw"} for x in proofs],"originalModuleGraphSHA256":commands[2]["logSHA256"],"newBuilds":0,"newTests":0,"newNativeCalls":0}
 return new,proof,proofs
