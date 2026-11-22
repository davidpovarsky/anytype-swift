from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
repo=Path(r"C:\Users\DAVID\Code\anytype-original-editor-composed-integration-20261122")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\sdk-source-join-selected-586")
out.mkdir(parents=True,exist_ok=False)
left="bfaa404efcfe6ea5ba753777772114879f13db71";right="58651e46136d3b889f8c34afee720b3593d0f0f9";base="37f48119609747c01ee92cf597e4216f63b7bfa4"
registry="docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md";commands=[]
def git(label,*args,data=None,accept=(0,)):
 p=subprocess.run(["git","-c","core.autocrlf=false","-c","core.eol=lf",*args],cwd=repo,input=data,capture_output=True,timeout=90)
 (out/(label+".stdout")).write_bytes(p.stdout);(out/(label+".stderr")).write_bytes(p.stderr)
 commands.append({"label":label,"args":list(args),"returncode":p.returncode,"stdout_sha256":hashlib.sha256(p.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr).hexdigest()})
 (out/"COMMANDS.json").write_bytes((json.dumps(commands,indent=2)+"\n").encode())
 assert p.returncode in accept,(label,p.stderr.decode("utf-8","replace")[-2000:]);return p.stdout,p.returncode
def tree(label,head):
 raw,_=git(label,"ls-tree","-r","-z",head);d={}
 for row in raw.split(b"\0"):
  if row:
   meta,path=row.split(b"\t",1);mode,kind,oid=meta.decode().split();assert kind=="blob";d[path.decode()]=(mode,oid)
 return d
assert git("current-head","rev-parse","HEAD")[0].decode().strip()==left
assert not git("clean-before","status","--porcelain")[0]
assert git("common-base","merge-base",left,right)[0].decode().strip()==base
trees={n:tree(n+"-tree",h) for n,h in [("base",base),("left",left),("right",right)]}
changes={n:{p for p in set(trees["base"])|set(trees[n]) if trees["base"].get(p)!=trees[n].get(p)} for n in ["left","right"]}
overlaps=changes["left"]&changes["right"];assert overlaps<={registry},sorted(overlaps)
resolved_registry=None
if registry in overlaps:
 original=git("registry-base","show",base+":"+registry)[0];a=git("registry-left","show",left+":"+registry)[0];b=git("registry-right","show",right+":"+registry)[0]
 assert a.startswith(original) and b.startswith(original),"Registry change is not append-only"
 added=b[len(original):]
 resolved_registry=a if added in a else a+added
_,rc=git("true-merge-selected-integration","merge","--no-ff","--no-commit","--no-edit",right,accept=(0,1))
unmerged=[x.decode() for x in git("unmerged-paths","diff","--name-only","--diff-filter=U","-z")[0].split(b"\0") if x]
assert set(unmerged)<={registry}
if unmerged:
 assert resolved_registry is not None
 (out/"REGISTER_CONFLICT.md").write_bytes((repo/registry).read_bytes())
 (repo/registry).write_bytes(resolved_registry);git("stage-original-registry-entries","add","--",registry)
expected=dict(trees["base"])
for side in ["left","right"]:
 for path in changes[side]:
  if path in trees[side]:expected[path]=trees[side][path]
  else:expected.pop(path,None)
if resolved_registry is not None:
 oid=git("resolved-register-blob","hash-object","--stdin",data=resolved_registry)[0].decode().strip()
 expected[registry]=(trees["left"][registry][0],oid)
raw=git("full-index","ls-files","--stage","-z")[0];actual={}
for row in raw.split(b"\0"):
 if row:
  meta,path=row.split(b"\t",1);mode,oid,stage=meta.decode().split();assert stage=="0";actual[path.decode()]=(mode,oid)
assert actual==expected,"Selected integration differs from exact expected source union"
treeid=git("write-tree","write-tree")[0].decode().strip()
git("commit-source-union","commit","-m","Merge verified original selected-Space lifecycle into editor SDK")
head=git("final-head","rev-parse","HEAD")[0].decode().strip()
assert git("actual-parents","show","-s","--format=%P","HEAD")[0].decode().split()==[left,right]
assert git("actual-tree","rev-parse","HEAD^{tree}")[0].decode().strip()==treeid
assert not git("clean-final","status","--porcelain")[0]
shutil.copyfile(__file__,out/"ACTUAL_SOURCE_JOIN.py")
result={"status":"COMMITTED_SELECTED_SPACE_AND_EDITOR_SDK_SOURCE_UNION","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":head,"parents":[left,right],"common_base":base,"tree":treeid,"index_entries_verified":len(actual),"left_changed":len(changes["left"]),"right_changed":len(changes["right"]),"overlap":sorted(overlaps),"conflicts":unmerged,"registry_merge":"Both exact append-only entries retained" if overlaps else "No overlapping paths","all_source_unions_verified":True,"new_tests_compilers":0,"qualification":"Combined Apple framework/public gate/external consumer still pending actual packaging repair build.","not_pushed":True}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"RESULT.json").write_bytes(raw)
print(json.dumps({"result":result,"receipt_sha256":hashlib.sha256(raw).hexdigest()}))
