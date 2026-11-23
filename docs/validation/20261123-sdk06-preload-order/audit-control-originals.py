import base64,hashlib,json,os,pathlib,shutil,stat,subprocess
from datetime import datetime,timezone
P=json.loads(base64.b64decode(PACKET_B64))
R=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-sdk-preload-order-20261123")
S="c099e7ebb968cd4c646a372b1632db4e9a0a6668"
N="docs/validation/20261123-sdk06-preload-order";D=R/N
O=pathlib.Path("/mnt/development/projects/diagnostics/sdk06-preload-order-controls-20261123/attempt1-controller")
I=O/"attempt1"; PEER=pathlib.Path("/mnt/development/projects/diagnostics/sdk06-preload-order-independent-peer-20261123")
env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","PYTHONDONTWRITEBYTECODE":"1"}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a,payload=None):return subprocess.check_output(["git","-C",str(R),*a],input=payload,env=env,timeout=30)
def jb(v):return(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
def raw(p):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and p.resolve()==p and s.st_size<=256*1024,str(p)
 b=p.read_bytes();assert len(b)==s.st_size
 return b,s
def j(p):return json.loads(raw(p)[0])
def write(p,b):
 assert shutil.disk_usage(R).free>=1024**3
 p.parent.mkdir(exist_ok=True,parents=True)
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o644)
assert git("rev-parse","HEAD").decode().strip()==S and not git("status","--porcelain").strip()
manifest=j(D/"control-inputs.json");assert len(manifest["inputs"])==90
before=j(I/"source-before.json");after=j(I/"source-after.json");assert before==after and len(before)==90
paths=[x["path"] for x in manifest["inputs"]]
request=b"".join((S+":"+p+"\n").encode() for p in paths)
batch=git("cat-file","--batch",payload=request);off=0
for row in manifest["inputs"]:
 p=row["path"];end=batch.index(b"\n",off);oid,kind,size=batch[off:end].split();size=int(size);off=end+1
 blob=batch[off:off+size];off+=size;assert batch[off:off+1]==b"\n";off+=1
 physical=(R/p).read_bytes();s=(R/p).lstat()
 assert kind==b"blob" and physical==blob and len(blob)==row["bytes"] and sha(blob)==row["sha256"]
 assert stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==row["physicalMode"]
 assert before[p]["sha256"]==row["sha256"] and before[p]["bytes"]==row["bytes"]
 assert before[p]["physicalMode"]==row["physicalMode"] and before[p]["gitMode"]==row["gitMode"]
 assert before[p]["gitBlob"]==oid.decode()
 assert before[p]["inode"]==str(s.st_ino) and before[p]["uid"]==s.st_uid
assert off==len(batch)
assert git("show",S+":"+N+"/control-inputs.json")==(D/"control-inputs.json").read_bytes()
contract=j(R/"Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json")
original=j(D/"control-data/original-controller-source.json")
assert contract["inputs"]==original["inputs"] and contract["modules"]==original["modules"]
assert len(contract["inputs"])==85 and len(contract["modules"])==70
assert contract["preload_modules"]==sorted(n for n in contract["modules"] if not n.startswith("test_") and n!="sdk06_original_native_continuation")
entry=j(I/"actual-entry-admission.json")
assert entry["source"]==S and len(entry["actualPhysicalGitInputs"])==86 and entry["inputRowsUnchanged"] is True
for p,v in entry["actualPhysicalGitInputs"].items():
 assert v=={"sha256":before[p]["sha256"],"git_mode":before[p]["gitMode"]}
loaded_before=j(I/"loaded-before.json");loaded_after=j(I/"loaded-after.json")
assert loaded_before=={} and set(loaded_after)==set(manifest["productionModuleNames"]) and len(loaded_after)==68
expected_paths={contract["modules"][n]:contract["inputs"][contract["modules"][n]]["sha256"] for n in manifest["productionModuleNames"]}
for n,r in loaded_after.items():
 p=contract["modules"][n]
 assert r=={"path":p,"sha256":before[p]["sha256"],"bytes":before[p]["bytes"]}
 assert not n.startswith("test_")
refusal=j(I/"original-list-refusal.json")
assert refusal["loadedSourcesUnchanged"] is True and refusal["loadedBefore"]==refusal["loadedAfter"]
assert len(refusal["loadedBefore"])==41 and set(refusal["loadedBefore"])<=set(expected_paths)
for p,h in refusal["loadedBefore"].items():assert expected_paths[p]==h
corrected=j(I/"corrected-preloader-result.json")
assert corrected["actualLoadedSources"]==dict(sorted(expected_paths.items()))
assert corrected["productionPreloadCount"]==67 and corrected["productionModuleCountIncludingEntry"]==68
assert corrected["oldTestModulesImported"]==[] and corrected["archiveRestoration"]==0 and corrected["builds"]==0
events=[json.loads(x) for x in (I/"events.jsonl").read_text().splitlines()]
name="__main__.PreloadOrderControl.test_actual_preloader_refuses_original_order_and_loads_fixed_closure"
assert [x["outcome"] for x in events]==["START","SUBCASE_PASS","SUBCASE_PASS","PASS"]
assert all(x["test"]==name for x in events)
receipt=j(I/"receipt.json")
assert receipt["status"]=="PASS" and receipt["failure"] is None and receipt["source"]==S
assert receipt["actualMethodsStarted"]==[name] and receipt["actualMethodsPassed"]==[name]
assert receipt["testResult"]=={"methods":1,"failures":0,"errors":0,"skips":0,"wasSuccessful":True}
assert receipt["sourceInputs"]==90 and receipt["sourceUnchanged"] and receipt["loadedAfter"]==68
assert receipt["oldMethods"]==receipt["productTests"]==receipt["builds"]==receipt["archiveRestoration"]==0
readonly=j(I/"actual-git-events.json")
assert len(readonly)==3 and readonly==corrected["gitEvents"]
allowed=[
 ["git","-C",str(R),"rev-parse","HEAD"],
 ["git","-C",str(R),"ls-tree","-r","-z",S,"--",*manifest["productionSourcePaths"]],
 ["git","-C",str(R),"cat-file","--batch"]]
assert [x["argv"] for x in readonly]==allowed and all(x["cwd"] is None and x["GIT_OPTIONAL_LOCKS"]=="0" for x in readonly)
log=(I/"original-tests.log").read_text();assert "Ran 1 test in 1.093s" in log and log.endswith("\nOK\n")
launch=j(O/"launch-result.json");owned=j(O/"owned-process.json")
assert launch["status"]=="PASS" and launch["source"]==S and launch["returncode"]==0
assert launch["primaryFailure"] is None and launch["cleanupFailure"] is None and launch["ownedGroupAbsent"] is True
assert launch["pid"]==launch["pgid"]==owned["pid"]==owned["pgid"]==3148815
assert launch["elapsed"]<60 and launch["startFree"]>=1024**3 and launch["finalFree"]>=1024**3
assert max(launch["observedOutputPeak"].values())<8*1024**2-65536
assert sha((O/"run-controls.py").read_bytes())=="19f8ca5cc968568f3b2b557efd7044eb678076aad9f36b3a4d65a76d57b0594c"
assert (O/"run-controls.py").read_bytes()==(D/"run-control.py").read_bytes()
for n,row in j(I/"original-files.json").items():
 b,_=raw(I/n);assert row=={"bytes":len(b),"sha256":sha(b)}
assert sha((PEER/"review.json").read_bytes())=="4525a4b60a5e6e313ea2b241ef15b1ef16157795e60fab0c0baf015b8feb9929"
seal={}
def copy_set(source,dest,prefix):
 for p in sorted(source.rglob("*")):
  if stat.S_ISDIR(p.lstat().st_mode):continue
  b,s=raw(p);relative=p.relative_to(source)
  target=dest/relative;write(target,b);assert target.read_bytes()==b
  after=p.lstat();assert (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid,s.st_gid)==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_mode,after.st_uid,after.st_gid)
  seal[prefix+"/"+relative.as_posix()]={"originalPath":str(p),"bytes":len(b),"sha256":sha(b),
    "originalMode":stat.S_IMODE(s.st_mode),"originalInode":str(s.st_ino),"originalUID":s.st_uid,
    "originalMtimeNs":str(s.st_mtime_ns),"copyByteExact":True}
copy_set(O,D/"attempt1-originals","attempt1-originals")
copy_set(PEER,D/"independent-peer","independent-peer")
side=O.parent/"source-sidecars"
copy_set(side,D/"source-sidecars","source-sidecars")
write(D/"source-transfer/seal-client-packet-first-failure.json",jb({"stage":"client packet assembly before any remote audit execution","error":"TypeError: Cannot read properties of undefined (reading structuredContent)","effect":"No remote command or control invocation; actual filesystem originals remain available","cause":"Transient client store no longer contained transport response","controlReplay":False}))
write(D/"audit-control-originals.py",P["auditorSource"].encode())
audit={
 "protocol":"sdk06-preload-order-original-control-audit-v1","status":"PASS_ORIGINALS_ONLY",
 "source":S,"sourceInputsPhysicalGitModeUnchanged":90,"manifestSelfGitBound":True,
 "all85ProductionInputRecordsRetained":True,"unchangedPython":True,
 "actualNewMethods":1,"actualNewSubcasesPassed":2,"actualOldMethods":0,
 "actualBuilds":0,"actualProductMethods":0,"actualArchiveRestorations":0,
 "actualLoadedBefore":0,"actualAfterEntryImport":41,"actualAfterOldRefusal":41,"actualLoadedAfter":68,
 "actualReadonlyGitCalls":3,"namedMethod":name,
 "receiptSHA256":sha((I/"receipt.json").read_bytes()),"eventsSHA256":sha((I/"events.jsonl").read_bytes()),
 "unittestLogSHA256":sha((I/"original-tests.log").read_bytes()),"unittestSeconds":1.093,
 "launchReceiptSHA256":sha((O/"launch-result.json").read_bytes()),
 "outerSeconds":launch["elapsed"],"ownedPid":3148815,"ownedPgid":3148815,
 "ownedGroupAbsentFromOriginalReceipt":True,"cleanupError":None,
 "maximumSampledOutputAllocated":launch["observedOutputPeak"]["allocatedBytes"],
 "independentSourcePeerSHA256":"4525a4b60a5e6e313ea2b241ef15b1ef16157795e60fab0c0baf015b8feb9929",
 "noControlReexecutionByAuditor":True,"originalFilesPreserved":len(seal),
 "qualifiedScope":"actual strict preload equality and canonical import closure only",
 "unproved":["current CI identity/admit flow","archive restoration","component compile/link","23-method/32-case product result","UI/acknowledgment"]
}
write(D/"control-originals-audit.json",jb(audit))
qualification={
 "protocol":"sdk06-preload-order-qualification-v1","status":"PASS_FOCUSED_LOADER_ONLY",
 "source":S,"base":"1a09867d88f475fd2b3192fabc4dd803986e5281",
 "newProductionManifestSHA256":sha((R/"Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json").read_bytes()),
 "originalFailureAuditSHA256":sha((D/"original-failure/audit.json").read_bytes()),
 "controlAuditSHA256":sha(jb(audit)),"actualMethods":1,"actualSubcasesPassed":2,"oldMethodsRerun":0,
 "sourceInputs":90,"actualProductionModules":68,"ownedGroupAbsent":True,
 "actualArchiveRestoration":False,"actualNativeOrAppBuild":False,"actualComponentBuild":False,
 "actualProductAcceptance":False,"ciRedispatched":False,
 "retainedHistory":"Original CI restore-stage failure remains FAILED; prior compile-support pure control remains its original passing scope.",
 "originalsSeal":"evidence-seal.json","rootOwnsIntegrationPublicationDispatch":True
}
write(D/"qualification.json",jb(qualification))
seal_doc={"protocol":"sdk06-preload-order-exact-originals-seal-v1","source":S,"files":seal,
          "qualificationSHA256":sha(jb(qualification)),"auditSHA256":sha(jb(audit)),
          "controlWasNotRerunToSeal":True}
write(D/"evidence-seal.json",jb(seal_doc))
git("add","--",N)
changed=git("diff","--cached","--name-only").decode().splitlines()
assert changed and all(p.startswith(N+"/") for p in changed)
git("diff","--cached","--check")
git("-c","user.name=davidpovarsky","-c","user.email=your-email@example.com","commit","-m","Seal one actual SDK preload control and original restore failure evidence")
head=git("rev-parse","HEAD").decode().strip();assert not git("status","--porcelain").strip()
assert git("diff","--name-only",S,head,"--","Tools",".github").strip()==b""
print(json.dumps({"status":"SEALED_FOCUSED_LOADER_PASS","source":S,"evidenceHead":head,
 "writer":str(R),"qualificationSHA256":sha(jb(qualification)),"auditSHA256":sha(jb(audit)),
 "sealSHA256":sha(jb(seal_doc)),"receiptSHA256":audit["receiptSHA256"],
 "originalFilesPreserved":len(seal),"fixedRows":90,"loadedBefore":0,"loadedAfter":68,
 "methods":1,"subcasesPassed":2,"noOldReplay":True,"noProductOrBuild":True,
 "free":shutil.disk_usage(R).free,"evidenceCommitOnlyDocs":True},sort_keys=True))
