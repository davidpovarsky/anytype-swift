#!/usr/bin/env python3
"""Qualify retained, already-executed SQLite tests; preserve original producer FAIL."""
import argparse,base64,hashlib,json,tarfile
from pathlib import Path

ORIGINAL=Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1")
ARCHIVE=Path("/mnt/development/projects/evidence/native-d-final-20261125/native410b-inputs/native-source-410b441e5726.tar.gz")
ARCHIVE_SHA="eba6a0354006c9cfc363c4769bd08951d3b4be4ef3fa8a65eb0cde9b6376e008"
PINS={
 "result.json":"7b7dcfa554a2b5505dc6c2fcc770a4cc97debffcb99f427ed27aa48184151fb8",
 "source-before.json":"1014909a5d5e79f8e6390117ef07f624198d2e1c8e002a362dc6ff10dd8132c9",
 "source-after.json":"32a701c389455d78d9a9271224921e3cc5772005481e3a7eac83312d2436c171",
 "compiled-source-selection.json":"01172f1643787d03f0cdd33d980cd623a9af7800226fa53ebca9de3ff72c75d3",
 "binary.json":"8979da05aa30b62002fb04a2b779c4b8ce4caa37e1876e89f31c9763d4ce5f65",
 "commands/toolchain/result.json":"0962086a778218f36207aed081b200a84653427d4ee6683188b3d1918c47c7d4",
 "commands/build/result.json":"f5fd548800f4d5342ca603a013b327af7e6a7c06b95beb444abc93540313647c",
 "commands/binary-modules/result.json":"90fa06af6b6e68384546a25d59550ceb06634077d7c8537f5eb0cb7e1be3aaed",
 "commands/original-tests/result.json":"83efbe0f808d227ce09f6254fff1eaf5fadd068bdae483e5b21eeb7c8e039fe4",
}
ADDITIONS=[
"github.com/mattn/go-isatty v0.0.20/go.mod h1:W+V8PltTTMOvKvAeJH7IuucS94S2C6jfK/D7dTCTo3Y=",
"github.com/stretchr/testify v1.11.1/go.mod h1:wZwfW3scLgRK+23gO65QZefKpKQRnfz6sD981Nm4B6U=",
"golang.org/x/exp v0.0.0-20250620022241-b7579e27df2b/go.mod h1:3//PLf8L/X+8b4vuAfHzxeRUl04Adcb341+IGKfnqS8=",
"golang.org/x/mod v0.27.0/go.mod h1:rWI627Fq0DEoudcK+MBkNkCe0EetEaDSwJJkCcjpazc=",
"golang.org/x/sync v0.16.0/go.mod h1:1dzgHSNfp02xaA81J2MS99Qcpr2w7fw1gpm99rleRqA=",
"golang.org/x/sys v0.34.0/go.mod h1:BJP2sWEmIv4KK5OTEluFJCKSidICx8ciO85XgH3Ak8k=",
"golang.org/x/tools v0.36.0/go.mod h1:WBDiHKJK8YgLHlcQPYQzNCkUxUypCaa5ZegCVutKm+s=",
"modernc.org/libc v1.66.3/go.mod h1:XD9zO8kt59cANKvHPXpx7yS2ELPheAey0vjIuZOhOU8=",
]
EXPECTED=[
"TestCutoverMetadataKeepsV1NamespaceAndOrdinaryClaims",
"TestCutoverMetadataIndependentDisksRetainActualComponentAuthors",
"TestCutoverMetadataRecordCollisionHasNoWinnerOrSilentRetry",
"TestCutoverMetadataCommitExitAndFrozenRetry",
"TestCutoverMetadataRefusesForeignAuthorSpaceAndMissingACL",
"TestCutoverMetadataNeverTruncatesHistoryOrHidesCrossObjectCollision",
"TestCutoverMetadataModifyDeleteAndRawWireForgeryRefuse",
"TestCutoverMetadataCancelledContextCannotWrite",
]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
 if path.is_symlink() or not path.is_file():raise ValueError("not regular: "+str(path))
 return path.read_bytes()
def digest(path):return sha(read(path))
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def inventory(source):
 out={}
 for path in sorted(source.rglob("*")):
  if path.is_symlink():raise ValueError("source symlink")
  if path.is_file():out[str(path.relative_to(source))]={"bytes":path.stat().st_size,"sha256":digest(path)}
 return out
def metadata_delta(before,after,original,current):
 if len(before)!=4859 or set(before)!=set(after):raise ValueError("source census")
 if [k for k in before if before[k]!=after[k]]!=["go.work.sum"]:raise ValueError("only original checksum metadata may differ")
 if before["go.work.sum"]!={"bytes":26596,"sha256":"7d6858a4c4c1fe098b3f4e35647e72ab50b29893ff4a769a94c217f34f670899"}:raise ValueError("original sum")
 if after["go.work.sum"]!={"bytes":27287,"sha256":"ddc42c4028fd3a0d1dc6ccac0941d8d607c084b3f64e4c7ae116c8dbfeb824e4"}:raise ValueError("actual sum")
 if sha(original)!=before["go.work.sum"]["sha256"] or sha(current)!=after["go.work.sum"]["sha256"]:raise ValueError("actual metadata bytes")
 lines=original.decode().splitlines()
 actual=current.decode().splitlines()
 if len(lines)!=len(set(lines)) or len(actual)!=len(set(actual)) or len(actual)!=len(lines)+len(ADDITIONS):raise ValueError("exact checksum census")
 if set(actual)-set(lines)!=set(ADDITIONS) or ("\n".join(line for line in actual if line not in ADDITIONS)+"\n").encode()!=original or not current.endswith(b"\n"):raise ValueError("exact eight additive go.mod checksums")
def actual_results(rows):
 passes=[r["Test"] for r in rows if r.get("Action")=="pass" and r.get("Test")]
 methods=[v for v in passes if "/" not in v]
 expectedcases=EXPECTED+["TestCutoverMetadataRefusesForeignAuthorSpaceAndMissingACL/"+x for x in ("author","space","acl","change")]
 if methods!=EXPECTED or len(passes)!=12 or set(passes)!=set(expectedcases):raise ValueError("exact actual cases")
 if any(r.get("Action") in ("fail","skip") for r in rows):raise ValueError("original failure or skip")
 if not any(r.get("Action")=="pass" and not r.get("Test") for r in rows):raise ValueError("package terminal")
 return passes
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
 output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
 result={"status":"FAIL","scope":"retained actual native StoreState/SQLite component only","nativePeers":0,"applicationTests":0,"newTestInvocations":0,"newBuildInvocations":0,"originalProducerStatus":"FAIL"}
 try:
  for rel,pin in PINS.items():
   if digest(ORIGINAL/rel)!=pin:raise ValueError("original receipt: "+rel)
  if digest(ARCHIVE)!=ARCHIVE_SHA:raise ValueError("archive")
  original=json.loads(read(ORIGINAL/"result.json"))
  if original.get("status")!="FAIL" or original.get("error")!="ValueError: source changed during compile/run" or original.get("cleanupFailures")!=[]:raise ValueError("original failure classification")
  before=json.loads(read(ORIGINAL/"source-before.json"));after=json.loads(read(ORIGINAL/"source-after.json"))
  with tarfile.open(ARCHIVE) as archive:
   rawsum=archive.extractfile("go.work.sum").read()
   baseline=json.loads(archive.extractfile("source-manifest.json").read())
  if len(baseline["files"])!=4855:raise ValueError("baseline")
  for rel,entry in baseline["files"].items():
   if before[rel]!=entry:raise ValueError("baseline source changed before build")
  current=read(ORIGINAL/"source/go.work.sum")
  metadata_delta(before,after,rawsum,current)
  if inventory(ORIGINAL/"source")!=after:raise ValueError("current complete source drift")
  mod_proof=[]
  for line in ADDITIONS:
   module,version,expected=line.split()
   path=Path("/root/go/pkg/mod/cache/download")/module/"@v"/(version.removesuffix("/go.mod")+".mod")
   raw=read(path)
   observed="h1:"+base64.b64encode(hashlib.sha256((sha(raw)+"  go.mod\n").encode()).digest()).decode()
   if observed!=expected:raise ValueError("actual Go module metadata sum")
   filename=str(len(mod_proof)+1)+".mod";(output/filename).write_bytes(raw)
   mod_proof.append({"module":module,"version":version,"sum":observed,"file":filename,"bytes":len(raw),"sha256":sha(raw)})
  save(output/"added-module-metadata.json",mod_proof)
  for name in ("toolchain","build","binary-modules","original-tests"):
   folder=ORIGINAL/"commands"/name;command=json.loads(read(folder/"result.json"))
   if command.get("exitCode")!=0 or command.get("timedOut") or command.get("ownedProcessGroupRemaining")!=[] or command.get("observationError"):raise ValueError("original command not qualified")
   if digest(folder/"original.log")!=command["logSHA256"]:raise ValueError("original command log")
  binary=json.loads(read(ORIGINAL/"binary.json"))
  if binary!={"bytes":49589221,"sha256":"edb3778daf3b1edfc17db9a31563712f81f07dfaf2c31c446e0cd907ba409ba1"} or digest(ORIGINAL/"cutover-store.test")!=binary["sha256"]:raise ValueError("actual compiled binary")
  log=read(ORIGINAL/"commands/original-tests/original.log")
  if sha(log)!="2a2f901fa7159db89384d031a972fbedea89b8442add47d79226cb5c4155e101":raise ValueError("original result")
  rows=[json.loads(line) for line in log.decode().splitlines()]
  passed=actual_results(rows)
  # Pure refusal controls never modify original files or invoke tests.
  controls=[]
  changed=dict(after);changed["heart/go.mod"]=dict(after["heart/go.mod"],sha256="0"*64)
  for label,call in [
   ("changed production source",lambda:metadata_delta(before,changed,rawsum,current)),
   ("missing checksum metadata",lambda:metadata_delta(before,after,rawsum,current[:-1])),
   ("added skipped method",lambda:actual_results(rows+[{"Action":"skip","Test":EXPECTED[0]}])),
  ]:
   try:call()
   except ValueError:controls.append(label)
   else:raise ValueError("refusal control admitted")
  if inventory(ORIGINAL/"source")!=after or digest(ORIGINAL/"result.json")!=PINS["result.json"]:raise ValueError("originals changed during collection")
  result.update(status="PASS_RETAINED_STORE_COMPONENT_WITH_EXACT_METADATA_HYDRATION",passedMethods=EXPECTED,passedCases=passed,failed=0,skipped=0,sourceFilesUnchangedExceptExactGoChecksumMetadata=4858,metadataAdditions=mod_proof,refusalControls=controls,originals=PINS,binary=binary,originalLogSHA256=sha(log),compiledDependencyReceiptSHA256=digest(ORIGINAL/"commands/binary-modules/original.log"),collectorSHA256=digest(Path(__file__)))
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:save(output/"receipt.json",result)
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
