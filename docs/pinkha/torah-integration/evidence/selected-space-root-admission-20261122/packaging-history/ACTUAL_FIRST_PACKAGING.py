from pathlib import Path
import subprocess,json,hashlib,datetime,shutil
repo=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-canonical-merge")
proof=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-published-git-root-review\registry-text-continuation")
out.mkdir(parents=True,exist_ok=False)
left="37f48119609747c01ee92cf597e4216f63b7bfa4";right="172c639348cab52ed76151c917f56691f25151b2"
commands=[]
def git(label,*args,timeout=60):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(["git","-c","core.autocrlf=false","-c","core.eol=lf",*args],cwd=repo,capture_output=True,timeout=timeout)
 (out/(label+".stdout")).write_bytes(p.stdout);(out/(label+".stderr")).write_bytes(p.stderr)
 commands.append({"label":label,"args":list(args),"returncode":p.returncode,"started_at":started,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"stdout_sha256":hashlib.sha256(p.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr).hexdigest()})
 (out/"COMMANDS.json").write_bytes((json.dumps(commands,indent=2)+"\n").encode())
 assert p.returncode==0,(label,p.stderr.decode("utf-8","replace")[-2000:]);return p.stdout
assert git("head-before","rev-parse","HEAD").decode().strip()==left
assert not git("status-before","status","--porcelain")
branch=git("branch-before","branch","--show-current").decode().strip()
assert branch=="codex/otzaria-original-native-annotation-integration-20261122",branch
git("true-merge-selected","merge","--no-ff","--no-edit","-m","Merge tested original selected-Space lifecycle",right,timeout=120)
merged=git("merge-head","rev-parse","HEAD").decode().strip()
assert git("merge-parents","show","-s","--format=%P",merged).decode().split()==[left,right]
mergedtree=git("merge-tree","rev-parse","HEAD^{tree}").decode().strip()
assert mergedtree==git("tested-evidence-tree","rev-parse",right+"^{tree}").decode().strip()
assert not git("clean-after-source-merge","status","--porcelain")
dest=repo/"docs/pinkha/torah-integration/evidence/selected-space-root-admission-20261122"
assert not dest.exists();shutil.copytree(proof,dest)
assert hashlib.sha256((dest/"ROOT_REVIEW.json").read_bytes()).hexdigest()=="d1795b059984a96c4d0b04ea5321af49d8ff59a34cfca9dcd80d6dcfb2f7c0b3"
(dest/".gitattributes").write_bytes(b"* -text\n")
meta={"schema":"otzaria.original-selected-space-canonical-merge/1","source_merge":merged,"parents":[left,right],"tree":mergedtree,"same_as_published_tested_source_and_evidence_tree":True,"product_changes":"Only canonical ActiveSpaceManager bf337 and original WorkspaceService284c from source6ac09; ten actual new portable controls passed, old passing suites reused.","compiler_or_tests_replayed":0,"limits":"Apple/native SDK runtime, Auth startup/reopen and explicit withChat:false follow-up remain pending."}
(dest/"MERGE_BINDING.json").write_bytes((json.dumps(meta,indent=2)+"\n").encode())
(dest/"README.md").write_text("# Selected-Space canonical integration\n\nThe two reviewed original source files and their actual ten-case portable proof were integrated with a true two-parent merge. The resulting complete source/evidence tree equals the author's published172c6393 tree exactly. No compiler or test was replayed.\n\nRoot independently verified all104 outer evidence payloads, the two tested product files, actual four process receipts, exact ten named XML/stdout passes and the emitted linked PE. Native execution/child process identity and complete annotation authority remain outside this proof. The first reporting-wrapper failure and two read-only reviewer path/text assumptions are retained without rewriting their source.\n",encoding="utf-8")
rows=[]
for f in sorted(dest.rglob("*")):
 if f.is_file():
  b=f.read_bytes();rows.append({"path":f.relative_to(dest).as_posix(),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()})
index=(json.dumps({"schema":"otzaria.selected-space-root-admission-index/1","files":rows,"payload_count":len(rows)},indent=2)+"\n").encode();(dest/"INDEX.json").write_bytes(index)
rel=dest.relative_to(repo).as_posix()
git("stage-root-proof","add","--",rel)
git("proof-whitespace-check","diff","--cached","--check")
staged=[x.decode() for x in git("proof-staged-paths","diff","--cached","--name-only","-z").split(b"\0") if x]
assert len(staged)==len(rows)+1 and all(x.startswith(rel+"/") for x in staged)
git("commit-root-proof","commit","-m","Record independent selected-Space integration proof [skip ci]")
head=git("final-head","rev-parse","HEAD").decode().strip()
assert git("final-parent","rev-parse","HEAD^").decode().strip()==merged
for root in ["Anytype","Modules"]:
 assert git("final-"+root+"-tree","rev-parse","HEAD:"+root)==git("tested-"+root+"-tree","rev-parse",right+":"+root)
assert not git("clean-final","status","--porcelain")
shutil.copyfile(__file__,out/"ACTUAL_CANONICAL_MERGE.py")
result={"status":"CANONICAL_SELECTED_SPACE_MERGED_AND_PROOF_COMMITTED_LOCAL","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"branch":branch,"head":head,"merge":merged,"parents":[left,right],"tested_tree":mergedtree,"proof_path":rel,"proof_payloads":len(rows),"proof_index_sha256":hashlib.sha256(index).hexdigest(),"no_test_replay":True,"not_yet_pushed":True}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"RESULT.json").write_bytes(raw)
print(json.dumps({"result":result,"receipt_sha256":hashlib.sha256(raw).hexdigest()}))
