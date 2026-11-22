import pathlib,subprocess,json,hashlib,shutil,datetime,time,os
base=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
proof=base/"neutral-result-publication";proof.mkdir(exist_ok=False)
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
target=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-results-20261122")
branch="codex/otzaria-original-schema-native-results-20261122";head="382e5ac62575d4df533d5ad38286ca5a09049b45"
commands=[]
def save():
 (proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,argv,cwd,timeout=60):
 row={"label":label,"argv":argv,"cwd":str(cwd),"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 commands.append(row);save()
 stdout=proof/(label+".stdout");stderr=proof/(label+".stderr")
 with stdout.open("wb") as out,stderr.open("wb") as err:
  proc=subprocess.Popen(argv,cwd=cwd,stdout=out,stderr=err);row.update(status="RUNNING",pid=proc.pid);save()
  try:code=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save()
   subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],capture_output=True,timeout=15)
   proc.wait(timeout=15);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=code,stdout_sha256=hashlib.sha256(stdout.read_bytes()).hexdigest(),stderr_sha256=hashlib.sha256(stderr.read_bytes()).hexdigest());save()
 if code:raise RuntimeError(label+" exit "+str(code))
 return stdout.read_bytes().decode("utf-8")
assert not target.exists()
assert subprocess.run(["git","-C",str(repo),"show-ref","--verify","--quiet","refs/heads/"+branch],capture_output=True,timeout=15).returncode==1
assert run("base-head",["git","rev-parse","HEAD"],repo).strip()==head
assert not run("base-status",["git","status","--porcelain","--untracked-files=all"],repo)
run("create-owned-worktree",["git","worktree","add","-b",branch,str(target),head],repo,120)
src=base/"first-native-execution-45008694456";prefix=pathlib.Path("docs/pinkha/torah-integration/native-fixed-schema-observer-20261122/first-native-run-45008694456")
dest=target/prefix;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copytree(src,dest)
index=json.loads((src/"EVIDENCE_INDEX.json").read_text())
for e in index["files"]:assert hashlib.sha256((dest/e["path"]).read_bytes()).hexdigest()==e["sha256"]
run("add-evidence",["git","add","--",prefix.as_posix()],target)
run("diff-check",["git","diff","--cached","--check"],target)
paths=run("staged-paths",["git","diff","--cached","--name-only"],target).splitlines()
assert len(paths)==66 and all(p.startswith(prefix.as_posix()+"/") for p in paths)
run("commit-evidence",["git","commit","-m","docs: retain first original Heart observer native result [skip ci]"],target,120)
new=run("evidence-head",["git","rev-parse","HEAD"],target).strip()
assert not run("evidence-status",["git","status","--porcelain","--untracked-files=all"],target)
result={"status":"COMMITTED_NEUTRAL_DOCS_ONLY_NOT_PUSHED","worktree":str(target),"branch":branch,"base":head,"head":new,"paths":paths,"payloads":65,"payload_bytes":index["payload_bytes"],"evidence_index_sha256":hashlib.sha256((dest/"EVIDENCE_INDEX.json").read_bytes()).hexdigest(),"source_branch_unchanged":run("base-head-after",["git","rev-parse","HEAD"],repo).strip()==head,"native_tests":0,"trigger_pushes":0}
p=proof/"RESULT.json";p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
