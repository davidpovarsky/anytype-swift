from pathlib import Path
import json,hashlib,shutil,subprocess,re,datetime,zipfile
temp=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
repo=Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
source="d8ea2be0f42e51b35001c35509dd27c9035c3c66";branch="codex/otzaria-original-schema-native-20261122"
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
proof=temp/"final-v7-git-seal";proof.mkdir(exist_ok=False);shutil.copyfile(__file__,proof/"ACTUAL_SEAL_SCRIPT.py")
commands=[]
sha=lambda b:hashlib.sha256(b).hexdigest()
def save():(proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout=60,input_bytes=None):
 row={"label":label,"argv":args,"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 op=proof/(label+".stdout");ep=proof/(label+".stderr")
 with op.open("wb") as o,ep.open("wb") as e:
  p=subprocess.Popen(args,cwd=repo,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:p.communicate(input=input_bytes,timeout=timeout);rc=p.returncode
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save();subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=20);p.communicate(timeout=20);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=rc,stdout_sha256=sha(op.read_bytes()),stderr_sha256=sha(ep.read_bytes()));save()
 assert rc==0,(label,ep.read_text(errors="replace"));return op.read_bytes()
assert run("source-head",["git","rev-parse","HEAD"]).decode().strip()==source
assert run("owned-branch",["git","branch","--show-current"]).decode().strip()==branch
assert not run("initial-clean",["git","status","--porcelain","--untracked-files=all"])
packet=temp/"controls-v7-r1";ib=(packet/"REVIEW_INDEX.json").read_bytes();assert sha(ib)=="6cff458c0b945e755325d906add452e0b0fa676291f9391276dd8237c38d5e64"
idx=json.loads(ib)
for e in idx["files"]:
 b=(packet/e["path"]).read_bytes();assert len(b)==e["bytes"] and sha(b)==e["sha256"],e["path"]
dest=repo/prefix/"controls-v7-r1";assert not dest.exists();shutil.copytree(packet,dest)
# Retain the one already downloaded actual V6 artifact and original finite ownership receipts.
result_dir=repo/prefix/"second-native-run-45012913358";assert not result_dir.exists();result_dir.mkdir()
exe=temp/"execution-d8ea2be0"
for f in exe.iterdir():
 if f.is_file():
  d=result_dir/"trigger"/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
shutil.copytree(exe/"observer-01",result_dir/"observer-01")
intake=exe/"artifact-intake-01"
for f in intake.iterdir():
 if f.is_file():
  d=result_dir/"artifact-intake-01"/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
z=result_dir/"artifact-intake-01/original-artifact.zip";assert z.stat().st_size==2707567 and sha(z.read_bytes())=="7e8890542a45c77d8c268f6c274a65652a118cb14633da90b1938e3b4fd231ea"
omitted=[]
for f in (intake/"extracted").iterdir():
 if f.is_file():
  if f.name in ("12-declared-dependency-inputs.stdout","DECLARED_NATIVE_INPUTS.json"):
   omitted.append({"path":f.name,"bytes":f.stat().st_size,"sha256":sha(f.read_bytes()),"retention":"Exact member in the unchanged complete original artifact ZIP; not duplicated as a loose Git file."})
  else:
   d=result_dir/"selected-extracted"/f.name;d.parent.mkdir(exist_ok=True);shutil.copyfile(f,d)
(result_dir/"LARGE_RAW_MEMBERS_RETAINED_IN_COMPLETE_ZIP.json").write_text(json.dumps(omitted,indent=2)+"\n",encoding="utf-8")
# Retain the final V6 source/Git admission and both precommit errors without reinterpretation.
shutil.copytree(temp/"final-v6-git-seal",result_dir/"v6-git-seal")
root6=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v6-final-git-root-review")
assert sha((root6/"ROOT_REVIEW.json").read_bytes())=="7ace486fd4620a497846563d51a59a04677f2b9bf855f67c893bd443e641576a"
shutil.copytree(root6,result_dir/"root-v6-final-git-review")
(result_dir/"README.md").write_text("""# Actual V6 native result: eighteen pass, two remain open

Run45012913358 / attempt1 / exact d8ea2be0f42e51b35001c35509dd27c9035c3c66 completed FAILURE at2026-11-22T10:37:41Z. Original native compilation succeeded. Exactly20 selected cases executed:18PASS,2FAIL,0SKIP. No strict12 or first-run13 replay occurred.

ActualLocalZeroCounterAccepted and NativeComputedRemoteCounterAccepted returned the unwrapped final ErrFixedSchemaChanged after original replay. The existing receipt does not identify the differing row. A source-supported asynchronous SetHash possibility is a hypothesis, not an actual cause attribution. V7's separately reviewed fixture instrumentation will preserve real row differences without weakening the production comparison.

The four previously masked replay negatives now reached their exact failure causes and passed. The two LocalOnly ACL controls also passed through the original owner builder and original native ingestion/validation path. ACTUAL_CASE_REVIEW retains every selected terminal and raw output; no generic unavailable result is upgraded into unobserved semantics.

The single artifact14751201046 was downloaded once and verified against the GitHub digest and CRC. Original ZIP2707567B SHA7e8890542a45c77d8c268f6c274a65652a118cb14633da90b1938e3b4fd231ea contains every one of the36 indexed payloads. Two large declared-dependency files remain inside that complete ZIP instead of being duplicated loosely. No artifact download or control was repeated for retention.

Actual environment was pinned Go1.26.5/macOSARM64/Xcode27 with original r14 and native Tantivy. The retained declared closure has11318 files and all8 required product/test sources. Original native libraries and post-execution sources matched,15 commands finished without timeout, and the disposable owned temporary directory was removed. Binary172851650B hash before/after e1d4e98009b962528674b88c0c788721bb75951caf36210ad4d3cbe42fe65d5e matched; executable bytes were not uploaded and no independent root binary rehash is claimed.

The one observer8c59393e77bb and one intakea96c01dcf1b3 are terminal. This evidence packet preserves their original scripts/commands/raw outputs, the actual trigger, complete artifact, source/Git final review, and precommit raw-whitespace/attribute-normalization failures. New documentation or exact evidence attributes do not change any source or test result.

This is partial native observer evidence only. Full observer acceptance, schema registration/repair, annotation create permission, native identity/body receipts, ledger writer/ACK, original Auth/StageB and broader StageC-F acceptance remain open.
""",encoding="utf-8")
def index_folder(p,name):
 items=[{"path":f.relative_to(p).as_posix(),"bytes":f.stat().st_size,"sha256":sha(f.read_bytes())} for f in sorted(p.rglob("*")) if f.is_file() and f.name!=name]
 b=(json.dumps({"payload_count":len(items),"payload_bytes":sum(e["bytes"] for e in items),"files":items},indent=2)+"\n").encode();(p/name).write_bytes(b);return {"path":p.relative_to(repo).as_posix()+"/"+name,"sha256":sha(b),"payload_count":len(items),"payload_bytes":sum(e["bytes"] for e in items)}
result_index=index_folder(result_dir,"EVIDENCE_INDEX.json")
# Final source reviews remain outside the frozen112 packet.
review=repo/prefix/"final-v7-review";assert not review.exists();review.mkdir()
root7=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v7-root-source-review")
assert sha((root7/"ROOT_REVIEW.json").read_bytes())=="c9b2cccd9057d4c88683394fe87984f400f79574cbfcb3381d99779f70e04954"
shutil.copytree(root7,review/"root")
peer=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-heart-v7-counter-peer-review-20261122.json")
assert sha(peer.read_bytes())=="edba61bb5268c16060e823fba5e6a9ba6ac711bb2010817455c95d3c27055327";shutil.copyfile(peer,review/peer.name)
shutil.copyfile(__file__,review/"ACTUAL_FINAL_GIT_SEAL_SCRIPT.py")
(review/"SCOPE.json").write_text(json.dumps({"status":"SEALED_AWAITING_ROOT_FINAL_GIT_ADMISSION","source_parent":source,"reviewed_v7_index_sha256":sha(ib),"selected_native_cases":["ActualLocalZeroCounterAccepted","NativeComputedRemoteCounterAccepted"],"new_native_runs":0,"product_source_delta":0,"old_cases_replayed":0},indent=2)+"\n",encoding="utf-8")
review_index=index_folder(review,"INDEX.json")
workflow=packet/"PROPOSED_WORKFLOW.yml";assert sha(workflow.read_bytes())=="53414fb807fd95d1526da6881be9979c90dbc9340adb187cce646fe7da9cce82"
shutil.copyfile(workflow,repo/".github/workflows/otzaria-original-schema-native.yml")
paths=[prefix+"/controls-v7-r1",prefix+"/second-native-run-45012913358",prefix+"/final-v7-review"]
attrs=repo/".gitattributes";old=attrs.read_bytes();rules=[]
for pfx in paths:
 rules.append(pfx+"/** -text whitespace=cr-at-eol")
 for f in sorted((repo/pfx).rglob("*")):
  if not f.is_file():continue
  b=f.read_bytes()
  try:b.decode("utf-8")
  except UnicodeDecodeError:continue
  # Preserve exact raw CR CR LF and original patch/comment whitespace.
  if b"\r\r\n" in b or any(x.endswith((b" ",b"\t")) or re.match(rb" +\t",x) for x in b.splitlines()) or b.endswith((b"\n\n",b"\r\n\r\n")):
   rules.append(f.relative_to(repo).as_posix()+" -whitespace")
rules.append(".github/workflows/otzaria-original-schema-native.yml -text")
for rule in rules:
 if rule.encode() not in old:old+=(b"" if not old or old.endswith(b"\n") else b"\n")+(rule+"\n").encode()
attrs.write_bytes(old)
run("stage-exact-reviewed-v7-and-retained-v6",["git","add","--",*paths,".gitattributes",".github/workflows/otzaria-original-schema-native.yml"],120)
run("staged-diff-check",["git","diff","--cached","--check"],60)
staged=run("staged-paths",["git","diff","--cached","--name-only"]).decode().splitlines()
expected={".gitattributes",".github/workflows/otzaria-original-schema-native.yml"}|{p.relative_to(repo).as_posix() for prefixpath in paths for p in (repo/prefixpath).rglob("*") if p.is_file()}
assert set(staged)==expected
raw=run("exact-staged-git-blobs",["git","cat-file","--batch"],timeout=120,input_bytes=b"".join((":"+p+"\n").encode() for p in staged))
offset=0;bindings=[]
for rel in staged:
 end=raw.index(b"\n",offset);oid,kind,size=raw[offset:end].decode().split();size=int(size);assert kind=="blob"
 b=raw[end+1:end+1+size];offset=end+2+size;expectedbytes=(repo/rel).read_bytes()
 if rel==".gitattributes":expectedbytes=expectedbytes.replace(b"\r\n",b"\n")
 assert b==expectedbytes,rel
 bindings.append({"path":rel,"git_blob":oid,"bytes":len(b),"sha256":sha(b)})
assert offset==len(raw)
(proof/"GIT_BLOB_BINDINGS.json").write_text(json.dumps(bindings,indent=2)+"\n",encoding="utf-8")
run("ONE-reviewed-control-seal-commit",["git","commit","-m","test: observe two unresolved native counter snapshots"],120)
head=run("sealed-head",["git","rev-parse","HEAD"]).decode().strip()
assert not run("no-application-product-delta",["git","diff","--name-only",source,"HEAD","--","Anytype","Modules","OriginalEditorFramework"])
assert not run("sealed-clean",["git","status","--porcelain","--untracked-files=all"])
result={"status":"SEALED_AWAITING_ROOT_FINAL_GIT_ADMISSION_NO_PUSH","head":head,"parent":source,"branch":branch,"all_git_blobs":len(bindings),"all_payload_bytes":sum(b["bytes"] for b in bindings),"frozen_v7_index_sha256":sha(ib),"v6_result_index":result_index,"v7_review_index":review_index,"workflow_sha256":sha(workflow.read_bytes()),"normal_pushes":0,"new_native_runs":0,"tests_replayed":0,"changed_paths":staged}
(proof/"LOCAL_FINAL_GIT_ADMISSION.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k!="changed_paths"}))
