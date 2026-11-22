from pathlib import Path
import subprocess,sys,json,hashlib,datetime,time
repo=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
packet=repo/"docs/pinkha/torah-integration/production-held-read-20261122/controls"
runner=packet/"run-held-read-controls.py"
assert hashlib.sha256(runner.read_bytes()).hexdigest()=="2dbc182a479489baed81e9254f93d088694350ec4d128d94694c3609d0a7033c"
assert hashlib.sha256((packet/"INPUTS.json").read_bytes()).hexdigest()=="bf16b93b5ab6badcd405f436258f2b4e40d5069bdf58004f6249fa03adf241ad"
rootreview=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\held_read_root_preexecution_review.json")
raw=rootreview.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="185f977b99f552d5c37df7c5808e7f4016f587bf7a3a45fda193a635c7150d84"
dest=packet/"provenance"/"root-preexecution-review.json"
assert not dest.exists();dest.write_bytes(raw)
evidence=packet/"execution-launcher";assert not evidence.exists();evidence.mkdir()
issued=Path(__file__)
(evidence/"actual-host-launcher.py").write_bytes(issued.read_bytes())
args=[sys.executable,str(runner)]
started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
timed=False;cleanup=None
with (evidence/"stdout").open("wb") as out,(evidence/"stderr").open("wb") as err:
 proc=subprocess.Popen(args,cwd=repo,stdout=out,stderr=err)
 try:code=proc.wait(timeout=1120)
 except subprocess.TimeoutExpired:
  timed=True
  cleanup_process=subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],capture_output=True,timeout=30)
  (evidence/"cleanup.stdout").write_bytes(cleanup_process.stdout);(evidence/"cleanup.stderr").write_bytes(cleanup_process.stderr)
  cleanup={"exitCode":cleanup_process.returncode,"pid":proc.pid};code=proc.wait(timeout=30)
receipt={"args":args,"cwd":str(repo),"childPID":proc.pid,"started":started,"finished":datetime.datetime.now(datetime.timezone.utc).isoformat(),"durationSeconds":round(time.monotonic()-clock,6),"exitCode":code,"timedOut":timed,"timeoutSeconds":1120,"ownedCleanup":cleanup,"actualHostLauncher":{"path":str(issued),"sha256":hashlib.sha256(issued.read_bytes()).hexdigest()},"stdoutSHA256":hashlib.sha256((evidence/"stdout").read_bytes()).hexdigest(),"stderrSHA256":hashlib.sha256((evidence/"stderr").read_bytes()).hexdigest()}
(evidence/"RECEIPT.json").write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
print(json.dumps(receipt))
print((evidence/"stdout").read_text(encoding="utf-8"))
print((evidence/"stderr").read_text(encoding="utf-8"))
sys.exit(code)
