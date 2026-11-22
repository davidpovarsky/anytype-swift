import pathlib,json,hashlib,subprocess,datetime,shutil
base=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
proof=base/"final-v6-git-seal"/"patch-whitespace-continuation";proof.mkdir(exist_ok=False)
shutil.copyfile(__file__,proof/"ACTUAL_CONTINUATION_SCRIPT.py")
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
initial="382e5ac62575d4df533d5ad38286ca5a09049b45";evidence="66bdc665daea80efeb617199f92fb8c04a5289f2"
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122"
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,argv,timeout=60,input_bytes=None):
 row={"label":label,"argv":argv,"cwd":str(repo),"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 o=proof/(label+".stdout");e=proof/(label+".stderr")
 with o.open("wb") as out,e.open("wb") as err:
  p=subprocess.Popen(argv,cwd=repo,stdout=out,stderr=err,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL);row.update(status="RUNNING",pid=p.pid);save()
  try:
   p.communicate(input=input_bytes,timeout=timeout);code=p.returncode
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save();subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=15);p.communicate(timeout=15);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=code,stdout_sha256=sha(o.read_bytes()),stderr_sha256=sha(e.read_bytes()));save()
 if code:raise RuntimeError(label+" exit "+str(code))
 return o.read_bytes()
assert run("checkpoint-head",["git","rev-parse","HEAD"]).decode().strip()==evidence
assert run("owned-branch",["git","branch","--show-current"]).decode().strip()=="codex/otzaria-original-schema-native-20261122"
assert not run("unstaged-before",["git","diff","--name-only"])
failed=(proof.parent/"staged-diff-check.stdout").read_text(encoding="utf-8")
assert "V5_TO_V6.patch:" in failed and all("V5_TO_V6.patch:" in x for x in failed.splitlines() if ": space before tab" in x)
attr=repo/".gitattributes";old=attr.read_bytes()
rule=prefix+"/controls-v6-r1/V5_TO_V6.patch -whitespace\n"
assert rule.encode() not in old
attr.write_bytes(old+rule.encode())
run("add-exact-evidence-attribute",["git","add","--",".gitattributes"])
run("staged-diff-check",["git","diff","--cached","--check"])
packets={"controls-v6-r1":("REVIEW_INDEX.json","a1eed44cfbc80089ae97868d5cec16728f8c482879944824635a8d3531c04ca9"),"final-v6-review":("INDEX.json","ccf7efe135cae2ba278f5beedf68c59d5cf6f8cf96325febb241c3c68e2b4f90")}
expected={".gitattributes",".github/workflows/otzaria-original-schema-native.yml"}
for name,(idx,digest) in packets.items():
 folder=repo/prefix/name
 assert sha((folder/idx).read_bytes())==digest
 index=json.loads((folder/idx).read_text())
 for entry in index["files"]:
  assert sha((folder/entry["path"]).read_bytes())==entry["sha256"]
  expected.add(prefix+"/"+name+"/"+entry["path"])
 expected.add(prefix+"/"+name+"/"+idx)
assert sha((repo/".github/workflows/otzaria-original-schema-native.yml").read_bytes())=="8661e4e5989d5de33d89fafe1ec9d42d7b02d3b89e3c68aa25efbcc65ece1cb9"
staged=run("staged-paths",["git","diff","--cached","--name-only"]).decode().splitlines()
assert set(staged)==expected,(len(staged),len(expected),sorted(set(staged)^expected))
raw=run("verify-staged-git-blobs",["git","cat-file","--batch"],input_bytes=b"".join((":"+rel+"\n").encode() for rel in staged))
offset=0;verified=[]
for rel in staged:
 end=raw.index(b"\n",offset);header=raw[offset:end].decode();oid,kind,size=header.split();size=int(size)
 assert kind=="blob";start=end+1;blob=raw[start:start+size];offset=start+size+1;assert raw[offset-1:offset]==b"\n"
 expected_bytes=(repo/rel).read_bytes();assert blob==expected_bytes,rel
 verified.append({"path":rel,"bytes":size,"git_blob":oid,"sha256":sha(blob)})
assert offset==len(raw)
(proof/"STAGED_BLOB_VERIFICATION.json").write_text(json.dumps({"status":"PASS","count":len(verified),"files":verified},indent=2)+"\n",encoding="utf-8")
run("commit-reviewed-v6",["git","commit","-m","fix: use original tree keys and qualify native observer retry"],120)
head=run("sealed-head",["git","rev-parse","HEAD"]).decode().strip()
assert not run("sealed-status",["git","status","--porcelain","--untracked-files=all"])
assert not run("frozen-prior-packets",["git","diff","--name-only",initial,"HEAD","--",prefix+"/candidate-v5",prefix+"/controls-v5-r2",prefix+"/final-review"])
changed=run("all-changed-since-baseline",["git","diff","--name-only",initial,"HEAD"]).decode().splitlines()
assert all(p.startswith(prefix+"/") or p in (".gitattributes",".github/workflows/otzaria-original-schema-native.yml") for p in changed)
result={"status":"SEALED_LOCAL_ONLY_AWAITING_ROOT_FINAL_GIT_ADMISSION","head":head,"parent":evidence,"base_trigger_head":initial,"branch":"codex/otzaria-original-schema-native-20261122","worktree":str(repo),"staged_path_count":len(staged),"staged_paths":staged,"all_changed_since_baseline":changed,"all_changed_since_baseline_count":len(changed),"frozen_v5_r2_original_final_review_unchanged":True,"original_product_roots_unchanged":True,"v6_index_sha256":packets["controls-v6-r1"][1],"final_review_index_sha256":packets["final-v6-review"][1],"workflow_sha256":sha((repo/".github/workflows/otzaria-original-schema-native.yml").read_bytes()),"native_tests":0,"trigger_pushes":0,"staged_blob_verification_sha256":sha((proof/"STAGED_BLOB_VERIFICATION.json").read_bytes()),"previous_failed_diff_check_preserved":str(proof.parent),"exact_added_attribute_rule":rule.strip()}
p=proof/"LOCAL_GIT_ADMISSION.json";p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":result["status"],"head":head,"parent":evidence,"staged_paths":len(staged),"all_changed_since_baseline":len(changed),"receipt":str(p),"receipt_sha256":sha(p.read_bytes()),"tests":0,"pushes":0}))
