import pathlib,json,hashlib,subprocess,datetime,shutil
repo=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-schema-native-controls-20261122")
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
out=root/"execution-d8ea2be0";out.mkdir(exist_ok=False)
shutil.copyfile(__file__,out/"ACTUAL_TRIGGER_SCRIPT.py")
head="d8ea2be0f42e51b35001c35509dd27c9035c3c66"
branch="codex/otzaria-original-schema-native-20261122"
gh=r"C:\Program Files\GitHub CLI\gh.EXE"
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(out/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout=60):
 row={"label":label,"argv":args,"cwd":str(repo),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"STARTING"};commands.append(row);save()
 stdout=out/(label+".stdout");stderr=out/(label+".stderr")
 with stdout.open("wb") as o,stderr.open("wb") as e:
  p=subprocess.Popen(args,cwd=repo,stdin=subprocess.DEVNULL,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:rc=p.wait(timeout)
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save();subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=15);p.wait(timeout=15);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=rc,stdout_sha256=sha(stdout.read_bytes()),stderr_sha256=sha(stderr.read_bytes()));save()
 if rc:raise RuntimeError(label+" failed "+str(rc))
 return stdout.read_bytes()
assert run("head",["git","rev-parse","HEAD"]).decode().strip()==head
assert run("branch",["git","branch","--show-current"]).decode().strip()==branch
assert not run("status",["git","status","--porcelain","--untracked-files=all"])
rootreview=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\heart-v6-final-git-root-review\ROOT_REVIEW.json")
assert sha(rootreview.read_bytes())=="7ace486fd4620a497846563d51a59a04677f2b9bf855f67c893bd443e641576a"
run("ONE-normal-trigger-push",["git","push","origin","HEAD:refs/heads/"+branch],120)
remote=run("remote-head",["git","ls-remote","--heads","origin","refs/heads/"+branch],60).decode().split()
assert len(remote)==2 and remote[0]==head
runs=json.loads(run("actual-run-query",[gh,"api","repos/davidpovarsky/anytype-swift/actions/runs?branch="+branch+"&event=push&per_page=10"],60))
matched=[r for r in runs["workflow_runs"] if r["head_sha"]==head and r["path"]==".github/workflows/otzaria-original-schema-native.yml"]
assert len(matched)<=1
result={"status":"PUSHED_RUN_IDENTIFIED" if matched else "PUSHED_RUN_NOT_YET_LISTED","head":head,"branch":branch,"normal_push_count":1,"root_review_sha256":sha(rootreview.read_bytes()),"selected_native_cases":20,"strict_cases":0,"other_native_passes_replayed":0,"run":({k:matched[0].get(k) for k in ["id","run_attempt","head_sha","event","status","conclusion","html_url","created_at","path"]} if matched else None)}
(out/"TRIGGER_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
