import pathlib,json,hashlib,subprocess,datetime,shutil
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\execution-d8ea2be0")
out=root/"observer-01";out.mkdir(exist_ok=False)
shutil.copyfile(__file__,out/"ACTUAL_OBSERVER_SCRIPT.py")
gh=r"C:\Program Files\GitHub CLI\gh.EXE";run_id=45012913358;head="d8ea2be0f42e51b35001c35509dd27c9035c3c66"
commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(out/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def invoke(label,argv,timeout,allow_failure=False):
 row={"label":label,"argv":argv,"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 op=out/(label+".stdout");ep=out/(label+".stderr")
 with op.open("wb") as o,ep.open("wb") as e:
  p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:rc=p.wait(timeout);timed=False
  except subprocess.TimeoutExpired:
   timed=True;row["timed_out"]=True;save()
   cleanup=subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=20)
   (out/(label+".cleanup.stdout")).write_bytes(cleanup.stdout);(out/(label+".cleanup.stderr")).write_bytes(cleanup.stderr)
   row["cleanup_exit"]=cleanup.returncode
   p.wait(timeout=20);rc=p.returncode
 row.update(status="TIMED_OUT" if timed else "COMPLETED",exit_code=rc,timed_out=timed,parent_reaped=p.poll() is not None,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout_sha256=sha(op.read_bytes()),stderr_sha256=sha(ep.read_bytes()));save()
 if (rc or timed) and not allow_failure:raise RuntimeError(label+" failed")
 return row,op.read_bytes()
_,before=invoke("bound-run-before",[gh,"api","repos/davidpovarsky/anytype-swift/actions/runs/"+str(run_id)],60)
initial=json.loads(before)
assert initial["head_sha"]==head and initial["run_attempt"]==1 and initial["event"]=="push" and initial["path"]==".github/workflows/otzaria-original-schema-native.yml"
watch,_=invoke("owned-gh-watch",[gh,"run","watch",str(run_id),"--repo","davidpovarsky/anytype-swift","--exit-status","--interval","30"],3300,allow_failure=True)
_,after=invoke("bound-run-after",[gh,"api","repos/davidpovarsky/anytype-swift/actions/runs/"+str(run_id)],60)
final=json.loads(after)
assert final["head_sha"]==head and final["run_attempt"]==1 and final["event"]=="push"
result={"run_id":run_id,"attempt":1,"head":head,"watch_exit":watch["exit_code"],"watch_timed_out":watch["timed_out"],"watch_parent_reaped":watch["parent_reaped"],"status":final["status"],"conclusion":final["conclusion"],"url":final["html_url"],"updated_at":final["updated_at"],"no_second_observer":True,"test_results_not_yet_artifact_verified":True}
(out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result))
