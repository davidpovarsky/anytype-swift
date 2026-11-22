from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
repo=Path(r"C:\Users\DAVID\Code\anytype-original-selected-space-20261122")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-published-git-root-review\register-path-continuation")
out.mkdir(parents=True,exist_ok=False)
prior_script=Path(r"C:\ProgramData\SentinelX\uploads\.sentinelx_uploads\script_job_517a29369ca1487fa9ea499413e1a2e1\selected_published_git_root_review.py")
shutil.copyfile(prior_script,out/"FIRST_READONLY_REVIEW_SCRIPT.py")
(out/"FIRST_READONLY_REVIEW_FAILURE.txt").write_text("First read-only root admission stopped before payload/Git binding because it expected the filename UPSTREAM_ARTIFACT_REGISTER.md. Actual retained path is docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md. Exact first source/parent/product-path checks had passed. No product, test, compiler, or packet changed.\n",encoding="utf-8")
base="37f48119609747c01ee92cf597e4216f63b7bfa4";source="6ac09deac37f3f537f54ad37c330014fe8af2c46";head="172c639348cab52ed76151c917f56691f25151b2"
prefix="docs/pinkha/torah-integration/production-selected-space-20261122"
products={"Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift":"bf33794809bff676321ae0265e0caf6539fd7feaa69edaf4d14829753c131ac1","Modules/Services/Sources/Services/Workspace/WorkspaceService.swift":"284c09888c8cf75b2fa54a0f529e0ac6401fbc9ba9c9a923973edaaace061c21"}
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*args,data=None):
 p=subprocess.run(["git",*args],cwd=repo,input=data,capture_output=True,timeout=30);assert p.returncode==0,(args,p.stderr.decode("utf-8","replace"));return p.stdout
assert git("rev-parse","HEAD").decode().strip()==head and not git("status","--porcelain")
assert git("show","-s","--format=%P",source).decode().split()==[base]
assert git("show","-s","--format=%P",head).decode().split()==[source]
sourcechanged=sorted(x.decode() for x in git("diff","--name-only","-z",base,source).split(b"\0") if x);assert sourcechanged==sorted(products)
changed=sorted(x.decode() for x in git("diff","--name-only","-z",base,head).split(b"\0") if x)
other=[x for x in changed if x not in products and not x.startswith(prefix+"/")]
assert len(other)==1 and other[0].endswith("UPSTREAM_EXCEPTION_REGISTER.md"),other
registry=other[0]
tree={}
for row in git("ls-tree","-r","-z",head).split(b"\0"):
 if row:
  meta,path=row.split(b"\t",1);mode,kind,oid=meta.decode().split();tree[path.decode()]=(mode,kind,oid)
batch=git("cat-file","--batch",data=("\n".join(tree[x][2] for x in changed)+"\n").encode())
offset=0;raws={};bindings=[]
for path in changed:
 end=batch.index(b"\n",offset);h=batch[offset:end].decode().split();n=int(h[2]);offset=end+1;b=batch[offset:offset+n];offset+=n+1
 assert h[0]==tree[path][2] and h[1]=="blob" and tree[path][0]=="100644"
 assert b==(repo/path).read_bytes(),path
 raws[path]=b;bindings.append({"path":path,"sha256":sha(b),"bytes":n,"git_blob":h[0]})
assert offset==len(batch)
indexraw=raws[prefix+"/INDEX.json"];assert sha(indexraw)=="cf833a6647cc73313a9ca0d6b78b1f8a297b8385ce81eec8a14d19a3a5eaac91"
index=json.loads(indexraw);rows=index["files"];assert len(rows)==104
assert sorted(x["path"] for x in rows)==sorted(x[len(prefix)+1:] for x in changed if x.startswith(prefix+"/") and x!=prefix+"/INDEX.json")
for x in rows:
 b=raws[prefix+"/"+x["path"]];assert sha(b)==x["sha256"] and len(b)==x["bytes"],x["path"]
for path,digest in products.items():assert sha(raws[path])==digest
required=["1c4bc8643d8f32556a87edcb88f8fec9a73804cce64e2dc0b3459e99312f39f6","64b7377b43792e53478aca183b83438ff40e105494479e682485ff365306955b","008d5489b07d8be7e4634ca3b8f945fd0686e24ff43f4289eb13cdcce19d44d5","1299b391644755a586e9481398ff303a464d82f60f88dabe7354f338c3d67cb7"]
for digest in required:assert any(sha(raw)==digest for raw in raws.values()),digest
oldregistry=git("show",base+":"+registry);newregistry=raws[registry]
assert newregistry.startswith(oldregistry),"Register must retain prior bytes unchanged"
entry=newregistry[len(oldregistry):].decode("utf-8")
assert source in entry and prefix in entry
(out/"REGISTER_ADDITION.md").write_bytes(newregistry[len(oldregistry):])
(out/"GIT_BLOB_BINDINGS.json").write_bytes((json.dumps(bindings,indent=2)+"\n").encode())
shutil.copyfile(__file__,out/"root_published_git_review.py")
result={"schema":"otzaria.selected-space-published-git-root-review/1","status":"PASS_FOR_TRUE_MERGE_WITHOUT_REEXECUTION","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"worktree":str(repo),"head":head,"source_commit":source,"base":base,"source_parent_exact":True,"evidence_parent_exact":True,"all_changed_files":len(changed),"outer_payloads":104,"all_committed_bytes_exact":True,"outer_index_sha256":sha(indexraw),"actual_control_root_review_sha256":required[1],"tested_product_sha256":products,"registry_path":registry,"old_registry_sha256":sha(oldregistry),"registry_prefix_retained_exact":True,"registry_appended_bytes":len(newregistry)-len(oldregistry),"tests_or_compilers_replayed":0,"limits":"Only ten actual portable selected-Space controls passed. Native current account startup, withChat:false follow-up and combined Apple SDK qualification remain separate dependencies."}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"ROOT_REVIEW.json").write_bytes(raw)
print(json.dumps({"result":result,"sha256":sha(raw),"path":str(out/"ROOT_REVIEW.json"),"registry_addition":entry}))
