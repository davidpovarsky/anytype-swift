from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
repo=Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
tmp=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\final-v6-git-seal\attributes-normalization-continuation")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v6-final-git-root-review")
out.mkdir(parents=True,exist_ok=False)
head="d8ea2be0f42e51b35001c35509dd27c9035c3c66";parent="66bdc665daea80efeb617199f92fb8c04a5289f2";base="382e5ac62575d4df533d5ad38286ca5a09049b45"
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
workflow=".github/workflows/otzaria-original-schema-native.yml"
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*args,data=None):
 p=subprocess.run(["git",*args],cwd=repo,input=data,capture_output=True,timeout=35);assert p.returncode==0,(args,p.stderr.decode("utf-8","replace"));return p.stdout
assert git("rev-parse","HEAD").decode().strip()==head
assert git("rev-parse","HEAD^").decode().strip()==parent
assert git("branch","--show-current").decode().strip()=="codex/otzaria-original-schema-native-20261122"
assert not git("status","--porcelain")
git("merge-base","--is-ancestor",base,head)
localraw=(tmp/"LOCAL_GIT_ADMISSION.json").read_bytes();assert sha(localraw)=="197600b431c41a42a88bdf10ec5722db07868d1a550cf25f47dd40e8c868014b";local=json.loads(localraw)
verifyraw=(tmp/"STAGED_BLOB_VERIFICATION.json").read_bytes();assert sha(verifyraw)=="8c5819574e315a7331ce34988067a049ce4b45a9b72d6966383de380f84942b4";v=json.loads(verifyraw)
changed=sorted(x.decode() for x in git("diff","--name-only","-z",parent,head).split(b"\0") if x)
allchanged=sorted(x.decode() for x in git("diff","--name-only","-z",base,head).split(b"\0") if x)
assert changed==sorted(local["staged_paths"]) and len(changed)==125
assert allchanged==sorted(local["all_changed_since_baseline"]) and len(allchanged)==191
allowed=[prefix+"/controls-v6-r1/",prefix+"/final-v6-review/",prefix+"/first-native-run-45008694456/"]
assert all(x in [".gitattributes",workflow] or any(x.startswith(a) for a in allowed) for x in allchanged)
tree={}
for row in git("ls-tree","-r","-z",head,"--",prefix,workflow,".gitattributes").split(b"\0"):
 if not row:continue
 meta,path=row.split(b"\t",1);mode,kind,oid=meta.split()
 tree[path.decode()]={"mode":mode.decode(),"kind":kind.decode(),"oid":oid.decode()}
records=v["files"];assert len(records)==125 and sorted(x["path"] for x in records)==changed
objects=git("cat-file","--batch",data=("\n".join(tree[x]["oid"] for x in changed)+"\n").encode())
offset=0;raws={};bindings=[]
for name in changed:
 end=objects.index(b"\n",offset);header=objects[offset:end].decode().split();size=int(header[2]);offset=end+1
 raw=objects[offset:offset+size];offset+=size;assert objects[offset:offset+1]==b"\n";offset+=1
 assert header[0]==tree[name]["oid"] and header[1]=="blob" and tree[name]["mode"]=="100644"
 original=next(x for x in records if x["path"]==name)
 assert sha(raw)==original["sha256"] and len(raw)==original["bytes"] and header[0]==original["git_blob"],name
 work=(repo/name).read_bytes()
 if name==".gitattributes":assert work.replace(b"\r\n",b"\n")==raw
 else:assert work==raw,name
 raws[name]=raw;bindings.append({"path":name,"sha256":sha(raw),"git_blob":header[0],"bytes":len(raw)})
assert offset==len(objects)
for dirname,indexname,digest,count in [("controls-v6-r1","REVIEW_INDEX.json","a1eed44cfbc80089ae97868d5cec16728f8c482879944824635a8d3531c04ca9",73),("final-v6-review","INDEX.json","ccf7efe135cae2ba278f5beedf68c59d5cf6f8cf96325febb241c3c68e2b4f90",48)]:
 root=prefix+"/"+dirname+"/";indexraw=raws[root+indexname];assert sha(indexraw)==digest
 index=json.loads(indexraw);assert len(index["files"])==count
 for row in index["files"]:
  raw=raws[root+row["path"]];assert sha(raw)==row["sha256"] and len(raw)==row["bytes"]
assert sha(raws[workflow])=="8661e4e5989d5de33d89fafe1ec9d42d7b02d3b89e3c68aa25efbcc65ece1cb9"
assert raws[workflow]==raws[prefix+"/controls-v6-r1/PROPOSED_WORKFLOW.yml"]
assert sha(raws[prefix+"/controls-v6-r1/EXECUTION_INPUTS.json"])=="dc843c2a08a1a55fc96ebe822f2c6e70b3c46bf83edd248266761a1cda8137e7"
assert sha(raws[prefix+"/controls-v6-r1/run_original_native_schema_controls.py"])=="de9b69ff773602a22042489fde5e1901bc9639315b623a072ae9f3e05d8225c7"
assert sha(raws[prefix+"/final-v6-review/root-source-review/ROOT_REVIEW.json"])=="5d5188ec6100c3323b51ac04c94364357a1ac284a6aa4c93ef78ae68531fb7d5"
attrdiff=git("diff",parent,head,"--",".gitattributes").decode("utf-8")
added=[x[1:] for x in attrdiff.splitlines() if x.startswith("+") and not x.startswith("+++")]
assert all(x.startswith(prefix+"/controls-v6-r1/") or x.startswith(prefix+"/final-v6-review/") or not x.strip() for x in added),added
manifest=json.loads(raws[prefix+"/controls-v6-r1/EXECUTION_INPUTS.json"])
assert len(manifest["expected_cases"]["native"])==20 and manifest["prior_cases_not_replayed"]=={"native":13,"strict":12}
shutil.copyfile(__file__,out/"root_final_git_review.py")
(out/"GIT_BLOB_BINDINGS.json").write_bytes((json.dumps(bindings,indent=2)+"\n").encode())
result={"schema":"otzaria.heart-v6-final-git-root-review/1","status":"PASS_FOR_ONE_SCOPED_NATIVE_RUN","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "head":head,"parent":parent,"base_trigger_head":base,"branch":"codex/otzaria-original-schema-native-20261122","worktree":str(repo),
 "changed_from_parent":125,"changed_from_baseline":191,"all125_committed_blob_bytes_independently_verified":True,"v6_payloads":73,"final_review_payloads":48,
 "full_source_root_review_sha256":"5d5188ec6100c3323b51ac04c94364357a1ac284a6aa4c93ef78ae68531fb7d5","manifest_sha256":"dc843c2a08a1a55fc96ebe822f2c6e70b3c46bf83edd248266761a1cda8137e7",
 "workflow_sha256":"8661e4e5989d5de33d89fafe1ec9d42d7b02d3b89e3c68aa25efbcc65ece1cb9","actual_workflow_matches_frozen_proposal":True,
 "attribute_delta":attrdiff,"source_scope_exact":True,"prior_product_roots_and_V5_R2_unchanged":True,"selected_cases":manifest["expected_cases"]["native"],
 "not_replayed":{"strict":12,"native":13},"new_builds_or_tests_executed_by_root":0,"allowed_next":"One normal push of this exact head by sole acceptance_inventory owner, one finite observer and one eventual artifact intake."}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"ROOT_REVIEW.json").write_bytes(raw)
print(json.dumps({"status":result["status"],"path":str(out/"ROOT_REVIEW.json"),"sha256":sha(raw),"head":head,"changed":125,"baseline_changes":191,"attribute_delta":attrdiff,"observed_at":result["observed_at"]}))
