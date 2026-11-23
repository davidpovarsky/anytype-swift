from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,signal,subprocess,sys,time
root=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-original-native-20261123")
source="44aa9d3c64275917a79e6392ef619554d1af2990"
base=Path("/mnt/development/projects/diagnostics/sdk06-original-native-failed-third-controls-20261123")
assert not base.exists()
free=shutil.disk_usage(root).free
assert free-16*1024**2>=2500000000,free
assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==source
assert not subprocess.check_output(["git","-C",str(root),"status","--porcelain","--untracked-files=all"],text=True)
raw=(root/"docs/validation/20261123-sdk06-original-native-continuation/run-failed-lane-control.py").read_bytes()
assert hashlib.sha256(raw).hexdigest()=="4cf990027474f23cf6d7899ebbb76bb445ecce9f3d84ae61d072ea6a46f326e5"
base.mkdir(mode=0o700);wrapper=base/"run-failed-lane-control-44aa9d3.py"
with wrapper.open("xb") as f:f.write(raw)
attempt=base/"attempt2"
argv=[sys.executable,"-B",str(wrapper),"--repository",str(root),"--evidence",str(attempt),"--source",source]
started=time.monotonic()
child=subprocess.Popen(argv,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
pgid=os.getpgid(child.pid);assert pgid==child.pid
with (base/"launch-start.json").open("x") as f:
 json.dump({"source_sha":source,"wrapper_sha256":hashlib.sha256(raw).hexdigest(),"pid":child.pid,"pgid":pgid,"argv":argv,"timeout_seconds":180,"free_before":free,"tests_requested":1,"retained_original_passes_replayed":0,"started_at":datetime.now(timezone.utc).isoformat()},f,sort_keys=True,indent=2);f.write("\n")
timed_out=False
try:stdout,stderr=child.communicate(timeout=180)
except subprocess.TimeoutExpired:
 timed_out=True
 try:os.killpg(pgid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:stdout,stderr=child.communicate(timeout=10)
 except subprocess.TimeoutExpired:
  try:os.killpg(pgid,signal.SIGKILL)
  except ProcessLookupError:pass
  stdout,stderr=child.communicate(timeout=10)
for name,b in (("launch.stdout",stdout),("launch.stderr",stderr)):
 with (base/name).open("xb") as f:f.write(b)
receipt={"source_sha":source,"wrapper_sha256":hashlib.sha256(raw).hexdigest(),"pid":child.pid,"pgid":pgid,"returncode":child.returncode,"timed_out":timed_out,"elapsed_seconds":time.monotonic()-started,"stdout_sha256":hashlib.sha256(stdout).hexdigest(),"stderr_sha256":hashlib.sha256(stderr).hexdigest(),"free_after":shutil.disk_usage(root).free,"finished_at":datetime.now(timezone.utc).isoformat()}
with (base/"launch-result.json").open("x") as f:json.dump(receipt,f,sort_keys=True,indent=2);f.write("\n")
print(json.dumps(receipt,sort_keys=True))
if (attempt/"receipt.json").is_file():print((attempt/"receipt.json").read_text())
else:print(json.dumps({"receipt_missing":True,"stderr":stderr.decode()}))
