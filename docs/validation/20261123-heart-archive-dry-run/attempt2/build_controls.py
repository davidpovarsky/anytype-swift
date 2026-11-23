from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,signal,subprocess,sys,time
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-heart-archive-dry-run-20261123")
SOURCE="f4d3e604bfa5b92a8d7afc1cbfe6887a8833400c"
OUT=Path(__file__).resolve().parent
CACHE=Path("/mnt/development/build-cache/heart-archive-dry-run-20261123")
SHARED_CACHE=Path("/mnt/development/build-cache/swift-package-cache")
SWIFT="/usr/local/bin/swift"
MIN_FREE=2_500_000_000
MAX_CACHE=1_000_000_000
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,data): (OUT/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
def git(*args,cwd=ROOT):return subprocess.check_output(["git",*args],cwd=cwd)
def frozen():return git("rev-parse","HEAD").decode().strip()==SOURCE and not git("status","--porcelain").strip()
def snapshot():
 result={}
 for rel in git("ls-files","Modules/PinkhaAnyIntegration","Modules/PinkhaAnyEngine","Modules/PinkhaKit").decode().splitlines():
  path=ROOT/rel; original=git("show",SOURCE+":"+rel)
  assert path.read_bytes()==original,rel
  result["repo/"+rel]={"sha256":sha(path),"bytes":path.stat().st_size,"git_blob":git("rev-parse",SOURCE+":"+rel).decode().strip()}
 pins=json.loads((ROOT/"Modules/PinkhaAnyIntegration/Package.resolved").read_text())["pins"]
 checkout_roots={}
 for pin in pins:
  matches=[p for p in (CACHE/"checkouts").iterdir() if p.name.lower()==pin["identity"]]
  assert len(matches)==1,(pin["identity"],matches)
  path=matches[0]; revision=git("rev-parse","HEAD",cwd=path).decode().strip()
  assert revision==pin["state"]["revision"],(pin["identity"],revision)
  assert not git("status","--porcelain",cwd=path).strip()
  checkout_roots[pin["identity"]]={"path":str(path),"revision":revision}
  for rel in git("ls-files",cwd=path).decode().splitlines():
   file=path/rel
   if file.is_symlink():
    result["dependency/"+pin["identity"]+"/"+rel]={"symlink":os.readlink(file)}
   elif file.is_file():
    result["dependency/"+pin["identity"]+"/"+rel]={"sha256":sha(file),"bytes":file.stat().st_size}
 save("dependencies.json",checkout_roots)
 return result
def zipped(name,data):
 raw=json.dumps(data,sort_keys=True,separators=(",",":")).encode()
 with (OUT/name).open("xb") as f:f.write(gzip.compress(raw,mtime=0))
def stop(proc):
 if proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=8)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=4)
def run(name,argv,timeout):
 started=time.monotonic(); row={"argv":argv,"started_at":now(),"timeout_seconds":timeout}
 error=None;observations=[];rc=None
 env=dict(os.environ,TMPDIR=str(CACHE/"tmp"),XDG_CACHE_HOME=str(CACHE/"local-cache"),PYTHONDONTWRITEBYTECODE="1")
 with (OUT/(name+".log")).open("xb") as log:
  proc=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  row["pid"]=proc.pid
  try:
   while proc.poll() is None:
    free=shutil.disk_usage("/mnt/development").free
    size=int(subprocess.check_output(["du","-sb",str(CACHE)]).split()[0])
    observations.append({"elapsed_seconds":time.monotonic()-started,"free_bytes":free,"task_cache_bytes":size})
    if free<MIN_FREE:raise RuntimeError("Free space guard: less than 2.5 GB")
    if size>MAX_CACHE:raise RuntimeError("New cache guard: exceeds 1 GB")
    if time.monotonic()-started>timeout:raise TimeoutError(name+" deadline")
    time.sleep(3)
   rc=proc.returncode
  except BaseException as e:
   error={"type":type(e).__name__,"message":str(e)}
   stop(proc);rc=proc.returncode
 row.update(finished_at=now(),elapsed_seconds=time.monotonic()-started,exit_code=rc,error=error,
            log_sha256=sha(OUT/(name+".log")),resource_observations=observations)
 save(name+".json",row)
 if error or rc!=0:raise RuntimeError(name+" failed; original log/command preserved")
 return row
assert frozen()
assert not CACHE.exists()
CACHE.mkdir();(CACHE/"tmp").mkdir();(CACHE/"config").mkdir();(CACHE/"security").mkdir()
save("toolchain.json",{"command":[SWIFT,"--version"],"output":subprocess.check_output([SWIFT,"--version"],text=True),"source_sha":SOURCE,
 "minimum_free_bytes":MIN_FREE,"maximum_task_cache_bytes":MAX_CACHE,"shared_package_cache":str(SHARED_CACHE),"started_at":now()})
common=["--package-path",str(ROOT/"Modules/PinkhaAnyIntegration"),"--scratch-path",str(CACHE),
        "--cache-path",str(SHARED_CACHE),"--config-path",str(CACHE/"config"),"--security-path",str(CACHE/"security"),
        "--disable-automatic-resolution","--skip-update"]
try:
 run("resolve",["nice","-n","10",SWIFT,"package",*common,"resolve"],300)
 assert frozen()
 before=snapshot();zipped("sources-before.json.gz",before)
 run("build",["nice","-n","10",SWIFT,"build",*common,"-j","1","--build-tests"],1800)
 after=snapshot();zipped("sources-after-build.json.gz",after)
 assert before==after and frozen()
 products=[]
 for p in CACHE.glob("out/Products/*/PinkhaAnyIntegrationTests*"):
  if p.is_file():products.append({"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size})
 assert products,"Actual Swift6 test products not found"
 save("products.json",products)
 save("build-result.json",{"status":"PASS_BUILD_ONLY","source_sha":SOURCE,"inputs":len(before),"source_unchanged":True,
     "old_product_methods_executed":0,"new_product_methods_executed":0,"finished_at":now()})
 print("PASS_BUILD_ONLY",len(before),"inputs",len(products),"products",flush=True)
except BaseException as e:
 save("build-result.json",{"status":"FAIL_BEFORE_TEST_EXECUTION","source_sha":SOURCE,"error_type":type(e).__name__,"error":str(e),
  "old_product_methods_executed":0,"new_product_methods_executed":0,"finished_at":now()})
 print("FAIL_BEFORE_TEST_EXECUTION",type(e).__name__,str(e),flush=True);raise
