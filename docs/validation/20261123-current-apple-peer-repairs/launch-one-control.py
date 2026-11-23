import argparse,hashlib,json,os,pathlib,resource,signal,subprocess,time
a=argparse.ArgumentParser();a.add_argument("--directory",required=True);a.add_argument("--script",required=True);a.add_argument("--sha256",required=True);a.add_argument("--head",required=True);args=a.parse_args()
r=pathlib.Path("/run/anytapy-wave15-source-overlay-20261123/editor");d=r/args.directory;script=d/args.script
assert d.resolve().is_relative_to(r/"docs/validation/20261123-current-apple-peer-repairs")
assert hashlib.sha256(script.read_bytes()).hexdigest()==args.sha256
assert int(next(x.split()[1]for x in pathlib.Path("/proc/meminfo").read_text().splitlines()if x.startswith("MemAvailable:")))*1024>=2*1024**3
assert not(d/"attempt1").exists()
assert sum(p.stat().st_blocks*512 for p in r.rglob("*") if p.is_file())+1024**2<8*1024**2
argv=["python3","-B",str(script),"--expected-head",args.head]
record={"argv":argv,"sourceHead":args.head,"wrapperSHA256":args.sha256,"launcherSHA256":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),"executionLimitSeconds":20,"ownedCleanupLimitSeconds":5,"status":"FAIL"}
start=time.monotonic();primary=None;process=None
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536));resource.setrlimit(resource.RLIMIT_CPU,(10,10))
with(d/"control.stdout").open("xb")as out,(d/"control.stderr").open("xb")as err:
 try:
  process=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","GIT_OPTIONAL_LOCKS":"0"},preexec_fn=limits)
  record.update(pid=process.pid,pgid=process.pid);record["returnCode"]=process.wait(timeout=20)
 except BaseException as e:primary=e;record["failure"]={"type":type(e).__name__,"message":str(e)}
 finally:
  if process:
   deadline=time.monotonic()+5
   try:os.killpg(process.pid,0)
   except ProcessLookupError:record["ownedGroup"]="ABSENT_ESRCH"
   else:
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    while time.monotonic()<deadline:
     process.poll()
     try:os.killpg(process.pid,0)
     except ProcessLookupError:record["ownedGroup"]="ABSENT_ESRCH";break
     time.sleep(.01)
    if record.get("ownedGroup")!="ABSENT_ESRCH":
     try:os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     try:process.wait(timeout=1)
     except subprocess.TimeoutExpired:record["cleanupFailure"]="owned_child_not_reaped"
     try:os.killpg(process.pid,0)
     except ProcessLookupError:record["ownedGroup"]="ABSENT_ESRCH"
record["elapsedSeconds"]=time.monotonic()-start
record["status"]="PASS" if primary is None and record.get("returnCode")==0 and record.get("ownedGroup")=="ABSENT_ESRCH" else "FAIL"
for n in("control.stdout","control.stderr"):
 p=d/n;record[n]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
(d/"control-execution.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
print(json.dumps(record,sort_keys=True));print((d/"control.stdout").read_text()[:5000]);print((d/"control.stderr").read_text()[:2000])
raise SystemExit(0 if record["status"]=="PASS" else 1)
