import pathlib,subprocess,json,hashlib,datetime,sys,shutil
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122")
packet=root/"controls-v2";execution=root/"execution-v2";launch=root/"execution-v2-launch";launch.mkdir(exist_ok=False)
shutil.copyfile(__file__,launch/"ACTUAL_LAUNCH_SCRIPT.py")
def sha(b):return hashlib.sha256(b).hexdigest()
assert not execution.exists()
index=(packet/"INDEX.json").read_bytes();assert sha(index)=="dd0caf3e22df95d03a090377c231e90dfe33866fdd971319b2164840961da01e"
for row in json.loads(index)["files"]:
 p=packet/row["path"];assert p.stat().st_size==row["bytes"] and sha(p.read_bytes())==row["sha256"],row["path"]
review=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\auth-release-controls-v2-root-review")
assert sha((review/"ROOT_REVIEW.json").read_bytes())=="a721efa0539a9c04c8973970325234b4ebe13b9efc42cb0f66dd3864b8c44636"
shutil.copytree(review,launch/"root-control-review")
args=[sys.executable,str(packet/"run_controls.py"),"--worktree",r"C:\Users\DAVID\Code\anytype-original-auth-startup-20261122","--output",str(execution)]
row={"status":"STARTING","argv":args,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"index_sha256":sha(index),"new_cases":6,"old_cases":0}
receipt=launch/"LAUNCH_RESULT.json"
def save():receipt.write_text(json.dumps(row,indent=2)+"\n",encoding="utf-8")
save()
op=launch/"runner.stdout";ep=launch/"runner.stderr"
with op.open("wb") as o,ep.open("wb") as e:
 p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=o,stderr=e)
 row.update(status="RUNNING",pid=p.pid);save()
 try:rc=p.wait(timeout=550);timed=False
 except subprocess.TimeoutExpired:
  timed=True;row["timed_out"]=True;save()
  cleanup=subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=20)
  (launch/"cleanup.stdout").write_bytes(cleanup.stdout);(launch/"cleanup.stderr").write_bytes(cleanup.stderr)
  row["cleanup_exit"]=cleanup.returncode;p.wait(timeout=20);rc=p.returncode
row.update(status="TIMED_OUT" if timed else "COMPLETED",exit_code=rc,timed_out=timed,parent_reaped=p.poll() is not None,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout_sha256=sha(op.read_bytes()),stderr_sha256=sha(ep.read_bytes()))
save()
print(json.dumps({"status":row["status"],"exit_code":rc,"timed_out":timed,"runner_output":op.read_text(errors="replace"),"runner_stderr":ep.read_text(errors="replace"),"launch_receipt":str(receipt),"launch_receipt_sha256":sha(receipt.read_bytes())}))
sys.exit(1 if timed else rc)
