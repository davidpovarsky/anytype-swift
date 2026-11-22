from pathlib import Path
import subprocess,sys,json,hashlib,datetime,time
repo=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
packet=repo/"docs/pinkha/torah-integration/production-held-read-20261122/controls-null-fixture-continuation"
runner=packet/"run-held-read-controls-continuation.py"
assert hashlib.sha256(runner.read_bytes()).hexdigest()=="8c7a4fb6abeba4207afcfe1b6940640c3c02a6512f666509ab09b8957d53cde9"
assert hashlib.sha256((packet/"INPUTS.json").read_bytes()).hexdigest()=="afdec7917149611b064631589085388d26ff5bdcb2d0d6b24c097b818bf3efea"
evidence=packet/"execution-launcher";assert not evidence.exists();evidence.mkdir()
issued=Path(__file__);(evidence/"actual-host-launcher.py").write_bytes(issued.read_bytes())
args=[sys.executable,str(runner)]
started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
timed=False;cleanup=None
with (evidence/"stdout").open("wb") as out,(evidence/"stderr").open("wb") as err:
 proc=subprocess.Popen(args,cwd=repo,stdout=out,stderr=err)
 try:code=proc.wait(timeout=1120)
 except subprocess.TimeoutExpired:
  timed=True
  cp=subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],capture_output=True,timeout=30)
  (evidence/"cleanup.stdout").write_bytes(cp.stdout);(evidence/"cleanup.stderr").write_bytes(cp.stderr)
  cleanup={"exitCode":cp.returncode,"pid":proc.pid};code=proc.wait(timeout=30)
receipt={"args":args,"cwd":str(repo),"childPID":proc.pid,"started":started,"finished":datetime.datetime.now(datetime.timezone.utc).isoformat(),"durationSeconds":round(time.monotonic()-clock,6),"exitCode":code,"timedOut":timed,"timeoutSeconds":1120,"ownedCleanup":cleanup,"actualHostLauncher":{"path":str(issued),"sha256":hashlib.sha256(issued.read_bytes()).hexdigest()},"stdoutSHA256":hashlib.sha256((evidence/"stdout").read_bytes()).hexdigest(),"stderrSHA256":hashlib.sha256((evidence/"stderr").read_bytes()).hexdigest()}
(evidence/"RECEIPT.json").write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
print(json.dumps(receipt))
print((evidence/"stdout").read_text(encoding="utf-8"))
print((evidence/"stderr").read_text(encoding="utf-8"))
sys.exit(code)
