#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess,sys,platform,time,shutil
from datetime import datetime,timezone
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123")
OUT=Path("/mnt/development/projects/diagnostics/semantic-page-mounted-known-pair-20261123/attempt1")
FROZEN="ad7425fd60bb2c76e943c9cfc77af8e6984cb845"
REVIEW=ROOT/"docs/validation/20261123-semantic-page-mounted-known-pair/source-review.json"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(["git","-C",str(ROOT),*a])
def save(p,v):
 with p.open("x") as f:f.write(json.dumps(v,sort_keys=True,indent=2)+"\n")
assert git("rev-parse","HEAD").decode().strip()==FROZEN and not git("status","--porcelain")
assert sha(REVIEW)=="264cf5c2fdac46c22b467a4cebb8629c246f9708c9e89227addd8a8ca401708a"
free=shutil.disk_usage("/mnt/development").free;assert free>2500000000,free
review=json.loads(REVIEW.read_text())
rows={}
for raw in filter(None,git("ls-tree","-rz","HEAD").split(b"\0")):
 meta,name=raw.split(b"\t",1);mode,kind,oid=meta.decode().split();rows[name.decode()]={"mode":mode,"kind":kind,"oid":oid}
def snapshot():
 data={}
 for name,expected in review["source_sha256"].items():
  path=ROOT/name;raw=path.read_bytes()
  actual=hashlib.sha256(raw).hexdigest()
  assert actual==expected and name in rows,name
  row=rows[name];assert row["kind"]=="blob"
  assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==row["oid"],name
  data[name]={"sha256":actual,"bytes":len(raw),"git":row}
 return data
before=snapshot();save(OUT/"source-before.json",before)
tmp=OUT/"tmp";tmp.mkdir()
env=os.environ.copy();env["TMPDIR"]=str(tmp);env["PYTHONDONTWRITEBYTECODE"]="1"
started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
argv=[sys.executable,"-B",str(OUT/"runner.py")]
with (OUT/"controls.log").open("xb") as log:
 proc=subprocess.run(argv,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
 log.flush();os.fsync(log.fileno())
after=snapshot();save(OUT/"source-after.json",after);assert before==after
assert git("rev-parse","HEAD").decode().strip()==FROZEN and not git("status","--porcelain")
assert sha(REVIEW)=="264cf5c2fdac46c22b467a4cebb8629c246f9708c9e89227addd8a8ca401708a"
result=json.loads((OUT/"result.json").read_text()) if (OUT/"result.json").exists() else None
events=[json.loads(line) for line in (OUT/"events.jsonl").read_text().splitlines()] if (OUT/"events.jsonl").exists() else []
expected=review["new_selector"]
starts=[e["method"] for e in events if e["event"]=="START"]
passes=[e["method"] for e in events if e["event"]=="PASS"]
success=proc.returncode==0 and result is not None and result["tests_run"]==1 and result["failures"]==result["errors"]==result["skips"]==0 and starts==passes==[expected]
files={p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p.name!="receipt.json"}
receipt={"status":"PASS_ONE_NEW_MOUNTED_ADAPTER_CONTROL" if success else "FAIL_NEW_MOUNTED_ADAPTER_CONTROL","source_sha":FROZEN,"source_review_sha256":sha(REVIEW),"argv":argv,"cwd":str(ROOT),"started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"returncode":proc.returncode,"elapsed_seconds":time.monotonic()-clock,"result":result,"named_starts":starts,"named_passes":passes,"source_input_count":len(before),"source_unchanged":before==after,"python":sys.version,"platform":platform.platform(),"free_bytes_before":free,"free_bytes_after":shutil.disk_usage("/mnt/development").free,"old_pair_controls_rerun":0,"old_mounted_controls_rerun":0,"product_tests_executed":0,"simulator_commands_executed":0,"builds":0,"files":files,"outer_controller_sha256":sha(Path(__file__)),"limitations":{"mounted_acceptance":"NOT_RUN","Apple_cold_reopen":"NOT_RUN","physical_device":"NOT_RUN"}}
save(OUT/"receipt.json",receipt)
print(json.dumps({"status":receipt["status"],"returncode":proc.returncode,"receipt_sha256":sha(OUT/"receipt.json"),"events_sha256":sha(OUT/"events.jsonl"),"original_log_sha256":sha(OUT/"controls.log"),"elapsed_seconds":receipt["elapsed_seconds"],"free_bytes":receipt["free_bytes_after"]}),flush=True)
sys.exit(0 if success else 1)
