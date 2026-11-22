from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
origin=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
repo=Path(r"C:\Users\DAVID\Code\anytype-original-editor-composed-integration-20261122")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\sdk-source-join-37f-5c")
out.mkdir(parents=True,exist_ok=False)
left="37f48119609747c01ee92cf597e4216f63b7bfa4";right="5c1d08e327bb8155248885e496cf64200932a812";base="cb2df9baa201db0ce404ba37eac853424bae6204"
branch="codex/otzaria-original-editor-composed-integration-20261122"
overlap="Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift"
commands=[]
def git(root,label,*args,accept=(0,),timeout=90):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(["git","-c","core.autocrlf=false","-c","core.eol=lf",*args],cwd=root,capture_output=True,timeout=timeout)
 (out/(label+".stdout")).write_bytes(p.stdout);(out/(label+".stderr")).write_bytes(p.stderr)
 commands.append({"label":label,"args":list(args),"cwd":str(root),"returncode":p.returncode,"started_at":start,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"stdout_sha256":hashlib.sha256(p.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr).hexdigest()})
 (out/"COMMANDS.json").write_bytes((json.dumps(commands,indent=2)+"\n").encode())
 assert p.returncode in accept,(label,p.returncode,p.stderr.decode("utf-8","replace")[-2000:]);return p.stdout,p.returncode
def tree(root,label,head):
 raw,_=git(root,label,"ls-tree","-r","-z",head);d={}
 for row in raw.split(b"\0"):
  if row:
   meta,name=row.split(b"\t",1);mode,kind,oid=meta.decode().split();assert kind=="blob";d[name.decode()]=(mode,oid)
 return d
assert not repo.exists()
assert git(origin,"branch-existence","branch","--list",branch)[0].strip()==b""
assert git(origin,"root-head","rev-parse","HEAD")[0].decode().strip()==left
assert not git(origin,"root-clean","status","--porcelain")[0]
assert git(origin,"common-base","merge-base",left,right)[0].decode().strip()==base
trees={name:tree(origin,name+"-tree",head) for name,head in [("base",base),("left",left),("right",right)]}
changes={}
for side in ["left","right"]:
 changes[side]={x for x in set(trees["base"])|set(trees[side]) if trees["base"].get(x)!=trees[side].get(x)}
assert changes["left"]&changes["right"]=={overlap}
assert len(changes["left"])==641 and len(changes["right"])==794
git(origin,"create-owned-integration-worktree","worktree","add","-b",branch,str(repo),left,timeout=120)
_,mergecode=git(repo,"merge-original-producer","merge","--no-ff","--no-commit","--no-edit",right,accept=(0,1),timeout=120)
raw,_=git(repo,"unmerged-paths","diff","--name-only","--diff-filter=U","-z")
unmerged=[x.decode() for x in raw.split(b"\0") if x]
assert unmerged==[overlap] if mergecode else not unmerged
if unmerged:
 (out/"ParticipantsStorage.conflicted.swift").write_bytes((repo/overlap).read_bytes())
 original,_=git(repo,"retained-root-participants","show",left+":"+overlap)
 assert hashlib.sha256(original).hexdigest()=="7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1"
 assert b"await self?.publishParticipants(" in original
 (repo/overlap).write_bytes(original)
 git(repo,"stage-exact-participant-resolution","add","--",overlap)
else:
 assert hashlib.sha256((repo/overlap).read_bytes()).hexdigest()=="7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1"
expected=dict(trees["base"])
for side in ["left","right"]:
 for path in changes[side]:
  if side=="right" and path==overlap:continue
  if path in trees[side]:expected[path]=trees[side][path]
  else:expected.pop(path,None)
raw,_=git(repo,"exact-union-index","ls-files","--stage","-z");actual={}
for row in raw.split(b"\0"):
 if row:
  meta,path=row.split(b"\t",1);mode,oid,stage=meta.decode().split();assert stage=="0";actual[path.decode()]=(mode,oid)
assert actual==expected,"Merged index differs from exact source union"
for path in changes["left"]:assert actual.get(path)==trees["left"].get(path)
for path in changes["right"]-{overlap}:assert actual.get(path)==trees["right"].get(path)
treeid=git(repo,"merged-tree","write-tree")[0].decode().strip()
git(repo,"commit-source-union","commit","-m","Merge original editor producer with native annotation lifecycle",timeout=120)
head=git(repo,"committed-head","rev-parse","HEAD")[0].decode().strip()
parents=git(repo,"committed-parents","show","-s","--format=%P","HEAD")[0].decode().split();assert parents==[left,right]
assert git(repo,"committed-tree","rev-parse","HEAD^{tree}")[0].decode().strip()==treeid
assert not git(repo,"clean-after-join","status","--porcelain")[0]
shutil.copyfile(__file__,out/"ACTUAL_SOURCE_JOIN.py")
result={"schema":"otzaria.original-editor-source-join/1","status":"COMMITTED_EXACT_SOURCE_UNION_PENDING_COMBINED_SDK_QUALIFICATION","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"worktree":str(repo),"branch":branch,"head":head,"parents":parents,"tree":treeid,"common_base":base,"all_index_entries_verified":len(actual),"left_changes_preserved":len(changes["left"]),"producer_changes":len(changes["right"]),"sole_overlap":overlap,"sole_resolution_sha256":"7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1","resolution":"Retain complete published original Participant actor/lifecycle; it already includes producer's sole await fix.","original_conflict_retained":bool(unmerged),"source_rewritten_beyond_exact_union":False,"compiler_test_execution":0,"pushes":0,"qualification":"Historical component passes are retained; combined-source Apple build and public/binary-consumer gates remain required after packaging repair."}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"RESULT.json").write_bytes(raw)
print(json.dumps({"result":result,"receipt_sha256":hashlib.sha256(raw).hexdigest(),"receipt_path":str(out/"RESULT.json")}))
