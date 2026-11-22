from pathlib import Path
import hashlib,json,subprocess,io,datetime
R=Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
B=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
D="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
P=R/D
BASE="37f48119609747c01ee92cf597e4216f63b7bfa4";HEAD="382e5ac62575d4df533d5ad38286ca5a09049b45"
OUT=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-final-git-review")
assert not OUT.exists();OUT.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def cmd(*args,input=None):
 p=subprocess.run(["git","-c","core.autocrlf=false",*args],cwd=R,input=input,capture_output=True,timeout=45)
 assert p.returncode==0,(args,p.returncode,p.stderr.decode(errors="replace"))
 return p.stdout
def git(*args):return cmd(*args).decode().strip()
def read(p):return json.loads(p.read_bytes())
def wr(p,v):p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+"\n").encode())
result={"schema":"otzaria.heart-v5-r2-final-root-git-admission/1","status":"REVIEWING","tests":0,"builds":0,"native_calls":0,"pushes":0}
try:
 assert git("rev-parse","HEAD")==HEAD
 assert git("show","-s","--format=%P",HEAD)==BASE
 assert git("rev-parse",HEAD+"^{tree}")=="7a95a018e895dce199ffd9bfb502dddc1901180a"
 assert git("branch","--show-current")=="codex/otzaria-original-schema-native-20261122"
 assert not git("status","--porcelain")
 changed=git("diff","--name-status",BASE,HEAD).splitlines()
 assert len(changed)==264 and all(x.startswith("A\t") for x in changed)
 paths=[x[2:] for x in changed]
 declared=read(P/"final-review/CHANGED_PATHS.json")
 assert declared["count"]==264 and set(paths)==set(declared["paths"])
 expected={".gitattributes",".github/workflows/otzaria-original-schema-native.yml"}
 counts={}
 for folder,indexname,indexsha,count,bytecount in [
  ("candidate-v5","SOURCE_REVIEW_INDEX.json","3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581",138,4198338),
  ("controls-v5-r2","REVIEW_INDEX.json","c8a125a81915b88b5da80f62f9cb7758d777630a652c501de0c24171f9d94e61",112,1944458),
  ("final-review","FINAL_REVIEW_INDEX.json","f2983336b0b13a23dee59d2229a7b1277f86efa7d88487f930550e090375f321",9,171322)]:
  q=P/folder;idxraw=(q/indexname).read_bytes();assert sha(idxraw)==indexsha
  idx=json.loads(idxraw);rows=idx["files"];assert len(rows)==count and sum(x["bytes"] for x in rows)==bytecount
  assert {x["path"] for x in rows}|{indexname}=={p.relative_to(q).as_posix() for p in q.rglob("*") if p.is_file()}
  for e in rows:
   raw=(q/e["path"]).read_bytes();assert sha(raw)==e["sha256"] and len(raw)==e["bytes"]
   if folder!="final-review":assert raw==(B/folder/e["path"]).read_bytes()
  if folder!="final-review":assert idxraw==(B/folder/indexname).read_bytes()
  expected|={D+"/"+folder+"/"+x for x in {e["path"] for e in rows}|{indexname}}
  counts[folder]={"payloads":count,"bytes":bytecount,"index_sha256":indexsha}
 assert set(paths)==expected
 workflow=(R/".github/workflows/otzaria-original-schema-native.yml").read_bytes()
 assert workflow==(P/"controls-v5-r2/PROPOSED_WORKFLOW.yml").read_bytes()
 assert sha(workflow)=="3f19c5958bb026b50e4d0fccc48d4a4a090bf9e4e4c68b06bb9596b6970a2f36"
 attrs=(R/".gitattributes").read_text(encoding="utf-8").splitlines()
 assert attrs==[D+"/** -text whitespace=cr-at-eol",".github/workflows/otzaria-original-schema-native.yml -text whitespace=cr-at-eol"]
 def root_tree(ref):
  out={}
  for x in cmd("ls-tree","-z",ref).split(b"\0"):
   if x:
    meta,path=x.split(b"\t",1);out[path.decode()]=meta.decode()
  return out
 roots_before=root_tree(BASE);roots_after=root_tree(HEAD)
 assert ".gitattributes" not in roots_before
 for path,identity in roots_before.items():
  if path not in ("docs",".github"):assert roots_after[path]==identity,path
 rawtree=cmd("ls-tree","-r","-z",HEAD,"--",*paths)
 blobs={}
 for x in rawtree.split(b"\0"):
  if not x:continue
  meta,path=x.split(b"\t",1);mode,kind,blob=meta.decode().split()
  assert mode=="100644" and kind=="blob";blobs[path.decode()]=blob
 assert set(blobs)==set(paths)
 batch=cmd("cat-file","--batch",input=("\n".join(HEAD+":"+p for p in paths)+"\n").encode())
 stream=io.BytesIO(batch);observed=[]
 for p in paths:
  header=stream.readline().decode().split();assert header[:2]==[blobs[p],"blob"]
  raw=stream.read(int(header[2]));assert stream.read(1)==b"\n"
  assert raw==(R/p).read_bytes(),p
  assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==blobs[p]
  observed.append({"path":p,"git_blob":blobs[p],"bytes":len(raw),"sha256":sha(raw)})
 assert not stream.read()
 root_receipt=P/"final-review/root-r2/ROOT_CONTROL_REVIEW.json"
 assert sha(root_receipt.read_bytes())=="05a8db798601ccd07683f11ca5ca38fb79d4db052b1060b8729ee4294fa7df34"
 assert root_receipt.read_bytes()==Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-root-controls-review\ROOT_CONTROL_REVIEW.json").read_bytes()
 peer=P/"final-review/PEER_R2_RUNNER_REVIEW.json"
 assert sha(peer.read_bytes())=="810b73cbea035411a91ae575fc406d726dd87a1305a7c15990c4d760f91d6f58"
 assert peer.read_bytes()==Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-heart-v5-r2-runner-independent-review-20261122.json").read_bytes()
 local=(B/"final-git-composition/LOCAL_GIT_COMPOSITION.json").read_bytes()
 assert sha(local)=="ae8602dc2df56c7435c2e09a2a4533b99805dffca67662496a4717a26fa64919"
 local_j=json.loads(local);assert local_j["head"]==HEAD and local_j["clean"] and local_j["changed_path_count"]==264
 result.update({"status":"PASS_EXACT_LOCAL_HEAD_APPROVED_FOR_ONE_NORMAL_PUSH","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "head":HEAD,"parent":BASE,"tree":git("rev-parse",HEAD+"^{tree}"),"branch":git("branch","--show-current"),
 "verified_git_blobs":len(observed),"verified_payload_bytes":sum(e["bytes"] for e in observed),"packets":counts,
 "workflow_sha256":sha(workflow),"original_product_root_entries_unchanged":True,
 "only_added_workflow":".github/workflows/otzaria-original-schema-native.yml",
 "expected_new_cases":{"native":33,"strict":12},"sole_future_owner":"/root/acceptance_inventory",
 "native_scope":"Genuine disposable LocalOnly original Heart runtime; not schema provisioning, annotation authority/receipt, iOS build, full original editor or ACK.",
 "binary_scope":"Future pre/post executable hashes are runner attestations; excluded executable bytes are not independently rehashed by root.",
 "all_git_blobs":observed})
except BaseException as e:
 result.update({"status":"FAIL_FINAL_GIT_ADMISSION","error_type":type(e).__name__,"error":str(e)})
 wr(OUT/"ROOT_FINAL_GIT_ADMISSION.json",result);(OUT/"ACTUAL_ROOT_REVIEW.py").write_bytes(Path(__file__).read_bytes());print(json.dumps({k:v for k,v in result.items() if k!="all_git_blobs"}));raise
wr(OUT/"ROOT_FINAL_GIT_ADMISSION.json",result)
(OUT/"ACTUAL_ROOT_REVIEW.py").write_bytes(Path(__file__).read_bytes())
print(json.dumps({"status":result["status"],"head":HEAD,"path":str(OUT),"receipt_sha256":sha((OUT/"ROOT_FINAL_GIT_ADMISSION.json").read_bytes()),"exact_git_blobs":264,"payload_bytes":result["verified_payload_bytes"],"new_executions":0}))
