import pathlib, subprocess, hashlib, json, datetime, sys
BASE=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122")
OUT=BASE/"auth-release-dual-integration-01"
OUT.mkdir(exist_ok=False)
(OUT/"ACTUAL_INTEGRATION.py").write_bytes(pathlib.Path(__file__).read_bytes())
REVIEW=BASE/"auth-release-published-root-review"
reviewraw=(REVIEW/"output-marker-continuation/ROOT_REVIEW.json").read_bytes()
assert hashlib.sha256(reviewraw).hexdigest()=="a1826431f634cb3f6c8b2f71efa7d4b827c2fa9e244a0a0cd1f7d83d45b471ee"
assert json.loads(reviewraw)["status"]=="PASS"
prod="Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift"
sourcehash="65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e"
all_results=[]
def integrate(label,root,left,right,branch,proofrel,copy_review):
 d=OUT/label;d.mkdir()
 commands=[]
 def g(name,*args,allowed=(0,),inp=None):
  p=subprocess.run(["git","-c","core.autocrlf=false","-c","core.eol=lf","-C",str(root),*args],input=inp,capture_output=True,timeout=120)
  (d/(name+".stdout")).write_bytes(p.stdout);(d/(name+".stderr")).write_bytes(p.stderr)
  commands.append({"label":name,"args":list(args),"returncode":p.returncode,"stdout_sha256":hashlib.sha256(p.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(p.stderr).hexdigest()})
  (d/"COMMANDS.json").write_bytes((json.dumps(commands,indent=2)+"\n").encode())
  if p.returncode not in allowed: raise RuntimeError(label+"/"+name+" failed")
  return p.stdout
 def tree(label,ref):
  rows={}
  for rec in g(label,"ls-tree","-rz",ref).split(b"\0"):
   if rec:
    meta,name=rec.split(b"\t",1);mode,kind,oid=meta.decode().split()
    rows[name.decode()]=(mode,kind,oid)
  return rows
 assert g("initial-head","rev-parse","HEAD").decode().strip()==left
 assert not g("initial-clean","status","--porcelain=v1")
 assert g("initial-branch","branch","--show-current").decode().strip()==branch
 common=g("common-base","merge-base",left,right).decode().strip()
 b,l,r=tree("base-tree",common),tree("left-tree",left),tree("right-tree",right)
 lc={k for k in b.keys()|l.keys() if b.get(k)!=l.get(k)}
 rc={k for k in b.keys()|r.keys() if b.get(k)!=r.get(k)}
 overlap=lc&rc
 assert overlap <= {".gitattributes"},sorted(overlap)
 expected=dict(b)
 for rows,changed in [(l,lc),(r,rc)]:
  for k in changed:
   if k in rows: expected[k]=rows[k]
   else: expected.pop(k,None)
 attr=None
 if overlap:
  leftattrs=g("left-attributes","show",left+":.gitattributes")
  rightattrs=g("right-attributes","show",right+":.gitattributes")
  lines=[]
  for line in (leftattrs+rightattrs).decode().splitlines():
   if line not in lines: lines.append(line)
  assert all(not line.strip() or line.startswith("docs/") or line.startswith("#") for line in lines)
  attr=("\n".join(lines)+"\n").encode()
  oid=hashlib.sha1(("blob "+str(len(attr))+"\0").encode()+attr).hexdigest()
  expected[".gitattributes"]=("100644","blob",oid)
 g("merge-reviewed-source","merge","--no-ff","--no-commit",right,allowed=(0,1))
 conflicts=g("conflicts","diff","--name-only","--diff-filter=U","-z").decode().strip("\0").split("\0")
 conflicts=[p for p in conflicts if p]
 assert set(conflicts) <= {".gitattributes"},conflicts
 if attr is not None:
  (root/".gitattributes").write_bytes(attr);g("stage-attributes-union","add","--",".gitattributes")
 assert not g("no-unmerged","ls-files","-u")
 actual={}
 for rec in g("actual-index","ls-files","-s","-z").split(b"\0"):
  if rec:
   meta,name=rec.split(b"\t",1);mode,oid,stage=meta.decode().split()
   assert stage=="0";actual[name.decode()]=(mode,"commit" if mode=="160000" else "blob",oid)
 assert actual==expected
 raw=g("exact-transition-index","show",":"+prod)
 assert hashlib.sha256(raw).hexdigest()==sourcehash
 treeid=g("exact-union-tree","write-tree").decode().strip()
 g("merge-diff-check","diff","--cached","--check")
 g("commit-source-merge","commit","-m","merge(otzaria): integrate reviewed original account release seam [skip ci]")
 merge=g("source-merge-head","rev-parse","HEAD").decode().strip()
 assert g("source-merge-parents","show","-s","--format=%P","HEAD").decode().split()==[left,right]
 assert g("source-merge-tree","rev-parse","HEAD^{tree}").decode().strip()==treeid
 merge_result={"status":"SOURCE_UNION_VERIFIED_NO_NEW_EXECUTION","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"merge_commit":merge,"parents":[left,right],"common_base":common,"tree":treeid,"all_entries_verified":len(actual),"left_changed":len(lc),"right_changed":len(rc),"overlap":sorted(overlap),"conflicts":conflicts,"attribute_resolution":"Exact unique union of evidence-scoped rules" if overlap else "No overlap","product_transition_sha256":sourcehash,"actual_control_passes_reused":6,"new_test_build_download_count":0}
 (d/"MERGE.json").write_bytes((json.dumps(merge_result,indent=2)+"\n").encode())
 dest=root/proofrel
 assert not dest.exists();dest.mkdir(parents=True)
 (dest/"MERGE.json").write_bytes((d/"MERGE.json").read_bytes())
 (dest/"ACTUAL_INTEGRATION.py").write_bytes((OUT/"ACTUAL_INTEGRATION.py").read_bytes())
 (dest/"MERGE_COMMANDS.json").write_bytes((d/"COMMANDS.json").read_bytes())
 for name in ["merge-reviewed-source.stdout","merge-reviewed-source.stderr","conflicts.stdout","conflicts.stderr","commit-source-merge.stdout","commit-source-merge.stderr"]:
  (dest/name).write_bytes((d/name).read_bytes())
 if copy_review:
  for p in REVIEW.rglob("*"):
   if p.is_file():
    target=dest/"root-review"/p.relative_to(REVIEW);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
 (dest/".gitattributes").write_bytes(b"* -text\n**/*.py whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n")
 readme=("# Original account release integration\n\n"
 "The exact published source 15ea8755 and six-case execution from 18668c3e are integrated by true merge "+merge+". All "+str(len(actual))+" Git entries were checked against the two-parent source union. The production transition is exactly SHA-256 "+sourcehash+".\n\n"
 "Root independently verified all 138 published changed blobs, 121 packet payloads, the six original PASS records, all three successful commands and their raw streams, actual executable PID 4420, the unchanged executable ad8035e5 and 16 exact retained execution copies. The original read-only checker expected a space after CONTROL_RESULT; its failed receipt is retained, and the continuation accepts the actual frozen '=' delimiter without changing any input or rerunning any control.\n\n"
 "The shared finishAndWaitForRelease waits for the original transition's admitted native drain and completed release effects. Its Void return does not certify an available account or subscriptions. Full Auth/LoginState/Hanlin attempt ownership and StageB/native framework qualification remain open. No tests, compiler runs or downloads were repeated for this merge.\n\n"
 "Actual source/controls: https://github.com/davidpovarsky/anytype-swift/tree/18668c3ec0521871c6993add297dbb91ffa8bef3/docs/pinkha/torah-integration/original-auth-release-20261122\n"
 "Root publication review: a1826431f634cb3f6c8b2f71efa7d4b827c2fa9e244a0a0cd1f7d83d45b471ee. Raw full-tree/index observations remain in the recorded host execution directory; all referenced original Git trees are retained by the real merge parents.\n")
 (dest/"README.md").write_bytes(readme.encode())
 index={p.relative_to(dest).as_posix():{"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob("*")) if p.is_file()}
 (dest/"INDEX.json").write_bytes((json.dumps({"files":index,"payload_count":len(index)},indent=2,sort_keys=True)+"\n").encode())
 g("stage-root-proof","add","--",proofrel)
 staged=g("proof-staged-paths","diff","--cached","--name-only","-z").decode().strip("\0").split("\0")
 assert all(p.startswith(proofrel+"/") for p in staged)
 g("proof-diff-check","diff","--cached","--check")
 g("commit-root-proof","commit","-m","docs(otzaria): retain shared release integration and actual controls [skip ci]")
 head=g("final-head","rev-parse","HEAD").decode().strip()
 assert not g("final-clean","status","--porcelain=v1")
 final={**merge_result,"published_proof_head":head,"branch":branch,"proof_path":proofrel,"proof_payload_count":len(index),"proof_index_sha256":hashlib.sha256((dest/"INDEX.json").read_bytes()).hexdigest(),"push":"PENDING"}
 (d/"RESULT.json").write_bytes((json.dumps(final,indent=2)+"\n").encode())
 all_results.append(final)
 (OUT/"RESULTS.json").write_bytes((json.dumps(all_results,indent=2)+"\n").encode())
 return head
try:
 canonical=integrate("canonical",pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122"),"58651e46136d3b889f8c34afee720b3593d0f0f9","18668c3ec0521871c6993add297dbb91ffa8bef3","codex/otzaria-original-native-annotation-integration-20261122","docs/pinkha/torah-integration/evidence/account-release-root-admission-20261122",True)
 composed=integrate("composed-sdk",pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-composed-integration-20261122"),"69281b65f04803ddccad7ee09d99cfda1a4d04fc",canonical,"codex/otzaria-original-editor-composed-integration-20261122","docs/pinkha/torah-integration/evidence/composed-sdk-account-release-20261122",False)
 print(json.dumps({"status":"BOTH_SOURCE_INTEGRATIONS_COMMITTED_PENDING_PUSH","results":all_results}))
except BaseException as e:
 failure={"status":"FAIL","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"type":type(e).__name__,"error":str(e),"traceback":__import__("traceback").format_exc(),"completed":all_results}
 (OUT/"FAILURE.json").write_bytes((json.dumps(failure,indent=2)+"\n").encode());print(json.dumps(failure));sys.exit(1)
