import json
PRIOR_TOOL_RESULT=json.loads("{\"ok\":false,\"interpreter\":\"python3\",\"sudo\":false,\"cwd\":null,\"cleanup\":false,\"command\":[\"C:\\\\ProgramData\\\\SentinelX\\\\.venv\\\\Scripts\\\\python.exe\",\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_a2b08a442301422eb01fb5e4715089cb\\\\heart_final_git_admission.py\"],\"output\":\"{\\\"schema\\\": \\\"otzaria.heart-v5-r2-final-root-git-admission/1\\\", \\\"status\\\": \\\"FAIL_FINAL_GIT_ADMISSION\\\", \\\"tests\\\": 0, \\\"builds\\\": 0, \\\"native_calls\\\": 0, \\\"pushes\\\": 0, \\\"error_type\\\": \\\"FileNotFoundError\\\", \\\"error\\\": \\\"[WinError 206] The filename or extension is too long\\\"}\\nTraceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_a2b08a442301422eb01fb5e4715089cb\\\\heart_final_git_admission.py\\\", line 61, in <module>\\r\\n    rawtree=cmd(\\\"ls-tree\\\",\\\"-r\\\",\\\"-z\\\",HEAD,\\\"--\\\",*paths)\\r\\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_a2b08a442301422eb01fb5e4715089cb\\\\heart_final_git_admission.py\\\", line 12, in cmd\\r\\n    p=subprocess.run([\\\"git\\\",\\\"-c\\\",\\\"core.autocrlf=false\\\",*args],cwd=R,input=input,capture_output=True,timeout=45)\\r\\n      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\n  File \\\"C:\\\\Users\\\\DAVID\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\Lib\\\\subprocess.py\\\", line 548, in run\\r\\n    with Popen(*popenargs, **kwargs) as process:\\r\\n         ^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\n  File \\\"C:\\\\Users\\\\DAVID\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\Lib\\\\subprocess.py\\\", line 1026, in __init__\\r\\n    self._execute_child(args, executable, preexec_fn, close_fds,\\r\\n  File \\\"C:\\\\Users\\\\DAVID\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\Lib\\\\subprocess.py\\\", line 1538, in _execute_child\\r\\n    hp, ht, pid, tid = _winapi.CreateProcess(executable, args,\\r\\n                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\nFileNotFoundError: [WinError 206] The filename or extension is too long\",\"duration\":3.9,\"returncode\":1,\"script_path\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_a2b08a442301422eb01fb5e4715089cb\\\\heart_final_git_admission.py\",\"workdir\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_a2b08a442301422eb01fb5e4715089cb\",\"hub_request_id\":\"hreq_3f8b22d2c1d04247\"}")
from pathlib import Path
import hashlib,subprocess,io,datetime
R=Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
D="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122";P=R/D
BASE="37f48119609747c01ee92cf597e4216f63b7bfa4";HEAD="382e5ac62575d4df533d5ad38286ca5a09049b45"
OLD=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-final-git-review")
OUT=OLD/"windows-command-length-continuation";assert not OUT.exists();OUT.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def wr(p,v):p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+"\n").encode())
def cmd(*args,input=None):
 p=subprocess.run(["git","-c","core.autocrlf=false",*args],cwd=R,input=input,capture_output=True,timeout=45)
 assert p.returncode==0,(args,p.returncode,p.stderr.decode(errors="replace"))
 return p.stdout
def git(*args):return cmd(*args).decode().strip()
first=read(OLD/"ROOT_FINAL_GIT_ADMISSION.json")
assert first["status"]=="FAIL_FINAL_GIT_ADMISSION" and "WinError 206" in first["error"]
assert PRIOR_TOOL_RESULT["returncode"]==1 and "rawtree=cmd" in PRIOR_TOOL_RESULT["output"]
firstscript=Path(PRIOR_TOOL_RESULT["script_path"]).read_bytes()
assert firstscript==(OLD/"ACTUAL_ROOT_REVIEW.py").read_bytes()
wr(OUT/"FIRST_TOOL_RESULT.json",PRIOR_TOOL_RESULT)
assert git("rev-parse","HEAD")==HEAD and git("show","-s","--format=%P",HEAD)==BASE
assert not git("status","--porcelain")
paths=read(P/"final-review/CHANGED_PATHS.json")["paths"];assert len(paths)==len(set(paths))==264
changes=git("diff","--name-status",BASE,HEAD).splitlines()
assert set(changes)=={"A\t"+p for p in paths}
rawtree=cmd("ls-tree","-r","-z",HEAD,"--",D,".gitattributes",".github/workflows/otzaria-original-schema-native.yml")
blobs={}
for raw in rawtree.split(b"\0"):
 if not raw:continue
 meta,path=raw.split(b"\t",1);mode,kind,blob=meta.decode().split()
 assert mode=="100644" and kind=="blob";blobs[path.decode()]=blob
assert set(blobs)==set(paths)
batch=cmd("cat-file","--batch",input=("\n".join(HEAD+":"+p for p in paths)+"\n").encode())
stream=io.BytesIO(batch);observed=[]
for p in paths:
 header=stream.readline().decode().split();assert header[:2]==[blobs[p],"blob"]
 raw=stream.read(int(header[2]));assert stream.read(1)==b"\n"
 assert raw==(R/p).read_bytes()
 assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==blobs[p]
 observed.append({"path":p,"git_blob":blobs[p],"bytes":len(raw),"sha256":sha(raw)})
assert not stream.read()
lookup={e["path"]:e for e in observed};counts={}
for folder,idxname,indexsha,count,bytecount in [
 ("candidate-v5","SOURCE_REVIEW_INDEX.json","3487663a830281fc33bef1f944d68047c784819918f03dc76341bd35413e7581",138,4198338),
 ("controls-v5-r2","REVIEW_INDEX.json","c8a125a81915b88b5da80f62f9cb7758d777630a652c501de0c24171f9d94e61",112,1944458),
 ("final-review","FINAL_REVIEW_INDEX.json","f2983336b0b13a23dee59d2229a7b1277f86efa7d88487f930550e090375f321",9,171322)]:
 key=D+"/"+folder+"/"+idxname
 assert lookup[key]["sha256"]==indexsha
 rows=read(P/folder/idxname)["files"];assert len(rows)==count and sum(x["bytes"] for x in rows)==bytecount
 for e in rows:
  actual=lookup[D+"/"+folder+"/"+e["path"]]
  assert actual["sha256"]==e["sha256"] and actual["bytes"]==e["bytes"]
 counts[folder]={"payloads":count,"bytes":bytecount,"index_sha256":indexsha}
workflow=(R/".github/workflows/otzaria-original-schema-native.yml").read_bytes()
assert workflow==(P/"controls-v5-r2/PROPOSED_WORKFLOW.yml").read_bytes()
assert sha(workflow)=="3f19c5958bb026b50e4d0fccc48d4a4a090bf9e4e4c68b06bb9596b6970a2f36"
assert (R/".gitattributes").read_text(encoding="utf-8").splitlines()==[D+"/** -text whitespace=cr-at-eol",".github/workflows/otzaria-original-schema-native.yml -text whitespace=cr-at-eol"]
root_receipt=P/"final-review/root-r2/ROOT_CONTROL_REVIEW.json"
assert sha(root_receipt.read_bytes())=="05a8db798601ccd07683f11ca5ca38fb79d4db052b1060b8729ee4294fa7df34"
assert root_receipt.read_bytes()==Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v5-r2-root-controls-review\ROOT_CONTROL_REVIEW.json").read_bytes()
peer=P/"final-review/PEER_R2_RUNNER_REVIEW.json"
assert sha(peer.read_bytes())=="810b73cbea035411a91ae575fc406d726dd87a1305a7c15990c4d760f91d6f58"
assert peer.read_bytes()==Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-heart-v5-r2-runner-independent-review-20261122.json").read_bytes()
local=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\final-git-composition\LOCAL_GIT_COMPOSITION.json").read_bytes()
assert sha(local)=="ae8602dc2df56c7435c2e09a2a4533b99805dffca67662496a4717a26fa64919"
lj=json.loads(local);assert lj["head"]==HEAD and lj["clean"] and lj["changed_path_count"]==264
result={"schema":"otzaria.heart-v5-r2-final-root-git-admission/1",
 "status":"PASS_EXACT_LOCAL_HEAD_APPROVED_FOR_ONE_NORMAL_PUSH",
 "utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":HEAD,"parent":BASE,
 "tree":git("rev-parse",HEAD+"^{tree}"),"branch":git("branch","--show-current"),
 "verified_git_blobs":264,"verified_payload_bytes":sum(x["bytes"] for x in observed),"packets":counts,
 "workflow_sha256":sha(workflow),"original_product_root_entries_unchanged":True,
 "root_entry_verification":"Completed in first actual script before its Windows argv-length failure; immutable sameHEAD/parent and all264 added-only Git blobs reconfirmed in this continuation.",
 "first_review_script_sha256":sha(firstscript),"first_failure_receipt_sha256":sha((OLD/"ROOT_FINAL_GIT_ADMISSION.json").read_bytes()),
 "continuation_reason":"Read-only Windows32767-character process command-line limit; use three validated prefixes for ls-tree and original264 Git object expressions on stdin. No product/source/commit/test/patch change.",
 "expected_new_cases":{"native":33,"strict":12},"sole_future_owner":"/root/acceptance_inventory",
 "native_scope":"Genuine disposable LocalOnly original Heart runtime only; no schema provisioning, annotation authority/receipt, iOS build, original editor acceptance or ACK.",
 "binary_scope":"Future executable pre/post hashes remain runner attestations; excluded binary bytes cannot be independently rehashed.",
 "tests":0,"builds":0,"native_calls":0,"patch_applies":0,"pushes":0,"downloads":0,"all_git_blobs":observed}
wr(OUT/"ROOT_FINAL_GIT_ADMISSION.json",result)
(OUT/"ACTUAL_CONTINUATION.py").write_bytes(Path(__file__).read_bytes())
print(json.dumps({"status":result["status"],"head":HEAD,"path":str(OUT),"receipt_sha256":sha((OUT/"ROOT_FINAL_GIT_ADMISSION.json").read_bytes()),"exact_git_blobs":264,"payload_bytes":result["verified_payload_bytes"],"new_executions":0,"prior_failure_preserved":True}))
