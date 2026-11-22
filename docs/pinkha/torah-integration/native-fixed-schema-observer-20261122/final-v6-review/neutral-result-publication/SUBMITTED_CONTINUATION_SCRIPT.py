import pathlib,subprocess,json,hashlib,datetime,shutil
base=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
proof=base/"neutral-result-publication"/"raw-whitespace-continuation";proof.mkdir(exist_ok=False)
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-results-20261122")
head="382e5ac62575d4df533d5ad38286ca5a09049b45";branch="codex/otzaria-original-schema-native-results-20261122"
prefix="docs/pinkha/torah-integration/native-fixed-schema-observer-20261122/first-native-run-45008694456"
commands=[]
def save():(proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,argv,timeout=60,allow=()):
 row={"label":label,"argv":argv,"cwd":str(repo),"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 op=proof/(label+".stdout");ep=proof/(label+".stderr")
 with op.open("wb") as o,ep.open("wb") as e:
  p=subprocess.Popen(argv,cwd=repo,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:code=p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save()
   subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=15);p.wait(timeout=15)
   row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=code,stdout_sha256=hashlib.sha256(op.read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256(ep.read_bytes()).hexdigest());save()
 if code and code not in allow:raise RuntimeError(label+" exit "+str(code))
 return op.read_bytes().decode()
assert run("head-before",["git","rev-parse","HEAD"]).strip()==head
assert run("branch-before",["git","branch","--show-current"]).strip()==branch
staged=run("staged-before",["git","diff","--cached","--name-only"]).splitlines()
assert len(staged)==66 and all(p.startswith(prefix+"/") for p in staged)
attr=repo/".gitattributes";before=attr.read_bytes()
rules=[prefix+"/"+p+" -whitespace" for p in ["normal-trigger-push.stderr","observer-01/owned-gh-watch.stdout","selected-artifact-files/12-buildinfo-native.stdout","selected-artifact-files/15-buildinfo-strict.stdout"]]
assert all(r.encode() not in before for r in rules)
attr.write_bytes(before+b"".join((r+"\n").encode() for r in rules))
run("add-raw-output-attributes",["git","add","--",".gitattributes"])
run("diff-check-after-attributes",["git","diff","--cached","--check"])
index=json.loads((repo/prefix/"EVIDENCE_INDEX.json").read_text())
entries=run("staged-exact-index",["git","ls-files","-s","--",prefix]).splitlines()
gitblobs={line.split("\t",1)[1]:line.split()[1] for line in entries}
for e in [*index["files"],{"path":"EVIDENCE_INDEX.json","sha256":hashlib.sha256((repo/prefix/"EVIDENCE_INDEX.json").read_bytes()).hexdigest()}]:
 data=(repo/prefix/e["path"]).read_bytes()
 assert hashlib.sha256(data).hexdigest()==e["sha256"]
 assert gitblobs[prefix+"/"+e["path"]]==hashlib.sha1(("blob "+str(len(data))+"\0").encode()+data).hexdigest()
assert len(gitblobs)==66
run("commit-retained-evidence",["git","commit","-m","docs: retain first original Heart observer native result [skip ci]"],120)
new=run("committed-head",["git","rev-parse","HEAD"]).strip()
assert not run("clean-before-push",["git","status","--porcelain","--untracked-files=all"])
result={"status":"COMMITTED_NOT_YET_PUSHED","base":head,"head":new,"branch":branch,"evidence_index_sha256":hashlib.sha256((repo/prefix/"EVIDENCE_INDEX.json").read_bytes()).hexdigest(),"payloads":65,"payload_bytes":index["payload_bytes"],"exact_staged_git_blobs_verified":66,"raw_bytes_changed":False,"attribute_scope":rules,"native_tests":0,"trigger_branch_changed":False}
result_path=proof/"RESULT.json";result_path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
remote=run("remote-before",["git","ls-remote","--heads","origin","refs/heads/"+branch],60)
assert not remote.strip(),"remote branch unexpectedly exists"
run("normal-neutral-docs-push",["git","push","-u","origin",branch],120)
remote=run("remote-after",["git","ls-remote","--heads","origin","refs/heads/"+branch],60)
assert remote.split()[0]==new
assert not run("clean-after-push",["git","status","--porcelain","--untracked-files=all"])
result.update(status="PUBLISHED_NEUTRAL_DOCS_ONLY",remote_head=new,normal_neutral_pushes=1)
result_path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
