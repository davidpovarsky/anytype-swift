from pathlib import Path
import datetime,gzip,hashlib,json,os,re,shutil,signal,subprocess,sys,time
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
assert json.loads((OUT/"build-result.json").read_text())["status"]=="PASS_BUILD_ONLY"
products=json.loads((OUT/"products.json").read_text())
assert products and all(sha(Path(row["path"]))==row["sha256"] for row in products)
before=snapshot();zipped("sources-before-tests.json.gz",before)
preparation=json.loads((ROOT/"docs/validation/20261123-heart-archive-dry-run/SOURCE_PREPARATION.json").read_text())
methods=preparation["new_selected_methods"];assert len(methods)==18 and len(set(methods))==18
expected={"PinkhaAnyIntegrationTests.HeartSpaceMigrationDryRunTests/"+method for method in methods}
common=["--package-path",str(ROOT/"Modules/PinkhaAnyIntegration"),"--scratch-path",str(CACHE),
        "--cache-path",str(SHARED_CACHE),"--config-path",str(CACHE/"config"),"--security-path",str(CACHE/"security"),
        "--disable-automatic-resolution","--skip-update","--skip-build","-j","1"]
run("list",["nice","-n","10",SWIFT,"test",*common,"list"],120)
listed=[line.strip() for line in (OUT/"list.log").read_text().splitlines()
        if line.strip().startswith("PinkhaAnyIntegrationTests.HeartSpaceMigrationDryRunTests/")]
assert len(listed)==18 and set(listed)==expected,listed
assert all(sha(Path(row["path"]))==row["sha256"] for row in products)
save("registration.json",{"status":"EXACT_EIGHTEEN_NEW_METHODS_REGISTERED","source_sha":SOURCE,
    "listed_methods":listed,"new_methods_executed":0,"old_methods_executed":0,"products_unchanged":True})
pattern=r"^PinkhaAnyIntegrationTests\.HeartSpaceMigrationDryRunTests/(?:"+"|".join(sorted(methods))+r")$"
failure=None
try:run("execute",["nice","-n","10",SWIFT,"test",*common,"--filter",pattern],300)
except BaseException as error:failure={"error_type":type(error).__name__,"error":str(error)}
log=(OUT/"execute.log").read_text(errors="replace")
events=[]
for line in log.splitlines():
 match=re.search(r"Test Case '([^']+)' (started|passed|failed|skipped)(?: at | \()",line)
 if match:
  events.append({"test":match.group(1),"action":match.group(2),"original_line":line})
expected_events={"HeartSpaceMigrationDryRunTests."+method for method in methods}
starts=[row["test"] for row in events if row["action"]=="started"]
passes=[row["test"] for row in events if row["action"]=="passed"]
failed=[row for row in events if row["action"] in ("failed","skipped")]
save("events.json",events)
after=snapshot();zipped("sources-after-tests.json.gz",after)
unchanged=before==after and frozen() and all(sha(Path(row["path"]))==row["sha256"] for row in products)
qualified=(failure is None and unchanged and len(starts)==18 and len(passes)==18
           and set(starts)==expected_events and set(passes)==expected_events and not failed)
save("test-result.json",{"status":"PASS_EIGHTEEN_NEW_DRY_RUN_METHODS" if qualified else "FAIL",
    "source_sha":SOURCE,"started":len(starts),"passed":len(passes),"failed_or_skipped":failed,
    "expected_methods":sorted(expected_events),"source_and_products_unchanged":unchanged,"original_command_failure":failure,
    "old_product_methods_executed":0,"native_migration":"NOT_RUN","apple":"NOT_RUN","network":"NOT_RUN",
    "full_migration_accepted":False,"finished_at":now()})
if not qualified:raise SystemExit("Original execution did not qualify; preserve failure")
preserved=OUT/"qualified-products";preserved.mkdir()
copied=[]
for row in products:
 target=preserved/Path(row["path"]).name;shutil.copyfile(row["path"],target)
 assert sha(target)==row["sha256"]
 copied.append(dict(row,preserved_path=str(target)))
save("qualified-products.json",copied)
print("PASS_EIGHTEEN_NEW_DRY_RUN_METHODS",flush=True)
