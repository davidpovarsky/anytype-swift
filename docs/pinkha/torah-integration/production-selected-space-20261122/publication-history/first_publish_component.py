import pathlib,subprocess,json,hashlib,shutil,datetime,os
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-selected-space-20261122")
temp=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
proposal=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-space-20261122")
base="37f48119609747c01ee92cf597e4216f63b7bfa4"
branch="codex/otzaria-original-selected-space-20261122"
proof=temp/"evidence-ready-v2"
rel="docs/pinkha/torah-integration/production-selected-space-20261122"
doc=repo/rel
checkpoint=temp/"PUBLICATION_CHECKPOINT.json"
assert not checkpoint.exists() and not doc.exists()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
commands=[]
def run(args,timeout=60):
 begin=stamp()
 p=subprocess.run(args,cwd=repo,capture_output=True,timeout=timeout)
 commands.append({"argv":args,"started_at":begin,"finished_at":stamp(),"returncode":p.returncode,"stdout":p.stdout.decode("utf-8",errors="replace"),"stderr":p.stderr.decode("utf-8",errors="replace")})
 assert p.returncode==0,commands[-1]
 return p.stdout
def git(*args,timeout=60):return run(["git",*args],timeout)
def phase(name,**fields):
 checkpoint.write_text(json.dumps({"phase":name,"at":stamp(),"pid":os.getpid(),**fields,"commands":commands},indent=2)+"\n",encoding="utf-8")
def write(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data if isinstance(data,bytes) else data.encode("utf-8"))
def rec(p,root):return {"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
assert git("rev-parse","HEAD").decode().strip()==base
assert git("branch","--show-current").decode().strip()==branch
assert not git("status","--porcelain=v1","-uall").strip()
remote_before=git("ls-remote","--heads","origin","refs/heads/"+branch,timeout=90).decode().strip()
assert not remote_before or remote_before.split()[0]==base,remote_before
index_raw=(proof/"INDEX.json").read_bytes()
assert sha(index_raw)=="1c4bc8643d8f32556a87edcb88f8fec9a73804cce64e2dc0b3459e99312f39f6"
index=json.loads(index_raw);assert len(index["files"])==91
for item in index["files"]:
 p=proof/item["path"];assert p.stat().st_size==item["bytes"] and sha(p.read_bytes())==item["sha256"],item
root_review=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\selected-space-actual-root-review")
assert sha((root_review/"ROOT_REVIEW.json").read_bytes())=="64b7377b43792e53478aca183b83438ff40e105494479e682485ff365306955b"
canonical=json.loads((proposal/"CANONICAL_INPUTS.json").read_bytes())
assert sha((proposal/"CANONICAL_INPUTS.json").read_bytes())=="e571e1e0c7148a43d2f1e586093d01f3cb5f4347621c546ce3acafa35abee233"
paths=[]
for item in canonical["files"]:
 target=repo/item["product_path"];raw=(proposal/item["canonical_input"]).read_bytes()
 assert sha(raw)==item["canonical_sha256"]
 original=git("show",base+":"+item["product_path"])
 assert sha(original)==item["base_sha256"] and target.read_bytes().replace(b"\r\n",b"\n")==original
 write(target,raw);paths.append(item["product_path"])
changed=git("diff","--name-only").decode().splitlines()
assert set(changed)==set(paths),changed
git("diff","--check","--",*paths)
patch=git("diff","--binary","--",*paths)
git("add","--",*paths)
git("commit","-m","fix: bind original selected Space to frozen account and request",timeout=120)
source=git("rev-parse","HEAD").decode().strip()
assert git("rev-parse","HEAD^").decode().strip()==base
for item in canonical["files"]:assert sha(git("show",source+":"+item["product_path"]))==item["canonical_sha256"]
phase("SOURCE_COMMITTED",source=source,base=base)
doc.mkdir(parents=True)
write(doc/".gitattributes","* -text -diff\n")
shutil.copytree(proof,doc/"evidence")
for name in ("ROOT_REVIEW.json","root_review.py"):
 write(doc/"independent-root-review"/name,(root_review/name).read_bytes())
write(doc/"SOURCE.patch",patch)
write(doc/"publish_component.py",pathlib.Path(__file__).read_bytes())
publication={"schema":"original-selected-space-publication/v1","base":base,"source_commit":source,"branch":branch,"product_paths":paths,"canonical_inputs":canonical,"frozen_evidence_index_sha256":sha(index_raw),"independent_actual_root_review_sha256":sha((root_review/"ROOT_REVIEW.json").read_bytes()),"actual_controls":10,"new_executions_during_publication":0,"scope":"Original manager/account/request/SpaceView selection prerequisite and exact final WorkspaceService boundary; no annotation factory, receipt, create/schema/identity/ACK grant","framework_producer_unchanged":"5c1d08e327bb8155248885e496cf64200932a812","qualification_withChat_false_remains_separate":"Current reviewed manager path preserves original withChat:true; no qualification caller is changed"}
write(doc/"SOURCE_PUBLICATION.json",json.dumps(publication,indent=2)+"\n")
readme="# Original selected-Space prerequisite\n\nSource commit: "+source+". Parent: "+base+".\n\nThe original ActiveSpaceManager now retains exact account/request lifetimes, revokes before replacement/stop, serializes manager-owned transitions, drains admitted original WorkspaceOpen work and rejects stale callbacks. Opaque selection also retains the original callback-produced SpaceView generation when it existed at request creation; missing authority is not recaptured after suspension. The new statically dispatched Services extension accepts only the original final WorkspaceService and calls its unchanged original WorkspaceOpen method with the existing manager behavior withChat:true. Qualification's separate withChat:false path is not changed.\n\nThe ten new serialized Swift Testing groups passed once in the documented portable closure, along with complete original candidate parsing. The first wrapper failed afterward on a stdout-only emitted-binary-name assertion; that runner/traceback remain unchanged. The evidence-only continuation binds actual command receipts, fresh XML and matching named stdout, immutable original/compiled inputs and the emitted/linked PE, without inferring an independently observed OS child PID/invocation. The later evidence copy omission of XML/Package.swift/prior probe was corrected additively, preserving the complete earlier packet/index. Both continuations ran zero compilers/tests. Root independently reviewed the actual 91-file packet and all results.\n\nThe packet explicitly maps removed imports, test-only observation/counter additions and DI/publisher/subscription/native transport/value probes. It does not execute original native Invocation, Go, protobuf decoding, Apple frameworks or native UI. Shared widget/type/property readiness and native child shutdown, production auth/bootstrap, actual annotation destination factory/metadata/identity/body receipts/writer/ACK, device distribution and full StageB acceptance remain open. A retired admitted operation may have a side effect before its rejected return; no rollback is inferred.\n\nSee evidence/CONTRACT_V2.md, evidence/CORRECTED_RESULT.json, evidence/TEST_RESULTS.xml, evidence/INDEX.json, independent-root-review/ROOT_REVIEW.json and SOURCE_PUBLICATION.json. No earlier test suite was replayed during this publication.\n"
write(doc/"README.md",readme)
reg=repo/"docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md"
old=reg.read_bytes();assert sha(old)=="3af75ef09fac8f21ab7de3fc0dbf9173fdaf9ef7f5c216e82d0f5d220755639c"
append="\n\n## 2026-11-22 — Original selected-Space request and service boundary\n\nStanding owner authorization and full source/control/actual-evidence reviews cover source "+source+" on base "+base+". Original paths: Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift and Modules/Services/Sources/Services/Workspace/WorkspaceService.swift. Canonical SHA256 values are bf33794809bff676321ae0265e0caf6539fd7feaa69edaf4d14829753c131ac1 and 284c09888c8cf75b2fa54a0f529e0ac6401fbc9ba9c9a923973edaaace061c21.\n\nAn external observer of cached/throttled UI state cannot synchronously revoke the original manager request or serialize/drain its own transitions. The original hook preserves frozen account/request/SpaceView generations and actual AccountInfo identity, blocks starts during stop, joins duplicate stop and denies stale publication. The closed Services extension rejects replacement protocol conformers and invokes only the unchanged original final WorkspaceService; it preserves withChat:true for this original manager path. It grants no complete annotation destination or editor/create/schema authority.\n\nTen new actual portable Swift Testing groups passed once; four original command receipts, fresh XML, matching named stdout and the emitted/linked PE are retained. The first post-test reporting assertion failed; exact RED history plus evidence-only correction are preserved, without an OS child-process identity claim. No old controls were replayed. Root actual evidence review64b7377b independently verifies the immutable91-payload packet and exact compiled/source closure. Explicit DI/publisher/native transport/value probes do not qualify Apple/native/runtime/device or shared-provider readiness. Auth closing-lease/start ordering and qualification withChat:false remain separate dependencies; no factory, receipt, identity writer or ACK is enabled.\n\nRollback reverts only the exact two source files and dependent unwired integration; no persisted schema/native data migration is introduced. Prior register bytes remain unchanged. Packet: "+rel+".\n"
newline="\r\n" if b"\r\n" in old else "\n"
write(reg,old+append.replace("\n",newline).encode("utf-8"))
assert reg.read_bytes().startswith(old)
write(doc/"EXCEPTION_REGISTER_ADDITION.json",json.dumps({"path":reg.relative_to(repo).as_posix(),"preserved_prefix_bytes":len(old),"preserved_prefix_sha256":sha(old),"after_sha256":sha(reg.read_bytes())},indent=2)+"\n")
files=[rec(p,doc) for p in sorted(doc.rglob("*")) if p.is_file()]
write(doc/"INDEX.json",json.dumps({"schema":1,"files":files,"count":len(files),"index_excludes_itself":True},indent=2)+"\n")
git("diff","--check","--","docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md")
git("add","--",rel,"docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md")
git("commit","-m","docs: retain selected Space controls and authority boundary",timeout=120)
head=git("rev-parse","HEAD").decode().strip()
assert not git("status","--porcelain=v1","-uall").strip()
for item in canonical["files"]:assert sha(git("show",head+":"+item["product_path"]))==item["canonical_sha256"]
for item in json.loads((doc/"INDEX.json").read_bytes())["files"]:
 raw=git("show",head+":"+rel+"/"+item["path"]);assert len(raw)==item["bytes"] and sha(raw)==item["sha256"],item
assert git("ls-remote","--heads","origin","refs/heads/"+branch,timeout=90).decode().strip()==remote_before
phase("READY_FOR_SINGLE_PUSH",source=source,head=head)
git("push","--set-upstream","origin","HEAD:refs/heads/"+branch,timeout=180)
remote=git("ls-remote","--heads","origin","refs/heads/"+branch,timeout=90).decode().split()
assert remote[0]==head and remote[1]=="refs/heads/"+branch
phase("PUBLISHED_AND_REMOTE_VERIFIED",source=source,head=head,proof=rel,index_sha256=sha((doc/"INDEX.json").read_bytes()),files=len(files))
print(json.dumps({"status":"PUBLISHED_CLEAN_REMOTE_VERIFIED","source":source,"head":head,"base":base,"branch":branch,"proof":rel,"outer_index_sha256":sha((doc/"INDEX.json").read_bytes()),"outer_payloads":len(files),"frozen_controls_index_sha256":sha(index_raw),"source_paths":paths,"new_compiler_or_test_executions":0}))
