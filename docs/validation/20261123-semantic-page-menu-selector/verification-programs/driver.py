#!/usr/bin/env python3
"""Finite static-source and Swift syntax-only checks. No build or test method."""
import datetime,hashlib,json,os,pathlib,resource,shutil,signal,subprocess,time,traceback
W=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-page-menu-selector-20261123")
SOURCE="894bb60f5d0d47a8629a5ace0bd5f0316f4905f5"
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"attempt1"
N="docs/validation/20261123-semantic-page-menu-selector"
UI="PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift"
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def capacity():assert shutil.disk_usage("/mnt/development").free>=1073741824+1024**2
def write(p,b):
 capacity();assert not p.exists()
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o600)
def js(p,v):write(p,(json.dumps(v,sort_keys=True,indent=2)+"\n").encode())
def git(*a):return subprocess.run(["git","-C",str(W),*a],capture_output=True,check=True,timeout=20,env={**os.environ,"GIT_OPTIONAL_LOCKS":"0"}).stdout
def snapshot():
 rows=json.loads((W/N/"source-inputs.json").read_bytes())["inputs"]
 out={}
 for row in rows:
  p=W/row["path"];b=p.read_bytes();s=p.stat()
  assert sha(b)==row["sha256"] and len(b)==row["bytes"] and s.st_mode&0o7777==row["physical_mode"]
  assert b==git("show",SOURCE+":"+row["path"])
  out[row["path"]]={"sha256":sha(b),"bytes":len(b),"mode":s.st_mode&0o7777,"inode":str(s.st_ino)}
 return out
def absent(pgid):
 try:os.killpg(pgid,0)
 except ProcessLookupError:return True
 return False
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536))
def command(label,argv,timeout):
 capacity();start=time.monotonic();first=None;cleanup=None;p=None;owned=None;actions=[]
 stdout=OUT/(label+".stdout");stderr=OUT/(label+".stderr")
 try:
  with stdout.open("xb") as so,stderr.open("xb") as se:
   p=subprocess.Popen(argv,cwd=W,env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","PYTHONDONTWRITEBYTECODE":"1","TMPDIR":str(OUT/"tmp"),"SWIFT_MODULECACHE_PATH":str(OUT/"tmp"),"CLANG_MODULE_CACHE_PATH":str(OUT/"tmp")},stdin=subprocess.DEVNULL,stdout=so,stderr=se,start_new_session=True,preexec_fn=limits)
   owned=p.pid;assert owned>1 and owned!=os.getpgrp() and os.getpgid(owned)==owned
   p.wait(timeout=timeout)
   assert time.monotonic()-start<timeout and p.returncode==0,("source_command_failed",p.returncode)
 except BaseException as error:first={"type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
 finally:
  if p is not None:
   try:
    stop=time.monotonic()+5
    if not absent(owned):
     actions.append("SIGKILL");os.killpg(owned,signal.SIGKILL)
    p.wait(timeout=max(0.001,stop-time.monotonic()))
    while not absent(owned) and time.monotonic()<stop:time.sleep(0.02)
    assert absent(owned) and time.monotonic()<stop
   except BaseException as error:cleanup={"type":type(error).__name__,"message":str(error)}
  for q in [stdout,stderr]:
   if q.exists():q.chmod(0o600)
  receipt={"label":label,"argv":argv,"startedAt":now(),"elapsedSeconds":time.monotonic()-start,"timeoutSeconds":timeout,
   "pid":owned,"pgid":owned,"returncode":None if p is None else p.returncode,
   "ownedGroupAbsent":owned is not None and absent(owned),"cleanupActions":actions,"firstFailure":first,"cleanupFailure":cleanup,
   "stdout":{"bytes":stdout.stat().st_size,"sha256":sha(stdout.read_bytes())} if stdout.exists() else None,
   "stderr":{"bytes":stderr.stat().st_size,"sha256":sha(stderr.read_bytes())} if stderr.exists() else None}
  js(OUT/(label+".command.json"),receipt)
 if first is not None or cleanup is not None:raise RuntimeError(label+"_failed")
 return receipt
capacity();assert not OUT.exists();assert git("rev-parse","HEAD").decode().strip()==SOURCE;assert not git("status","--porcelain=v1").strip()
OUT.mkdir(mode=0o700);(OUT/"tmp").mkdir(mode=0o700)
before=snapshot();js(OUT/"source-before.json",before)
failure=None;commands=[];static=None
try:
 commands.append(command("01-static-source",["python3","-B",str(W/N/"source-check.py"),"--expected-head",SOURCE],30))
 static=json.loads((OUT/"01-static-source.stdout").read_bytes());assert static["status"]=="PASS"
 swift=shutil.which("swiftc");assert swift and pathlib.Path(swift).is_file()
 commands.append(command("02-swift-version",[swift,"--version"],15))
 commands.append(command("03-swift-syntax",[swift,"-frontend","-parse",str(W/UI)],30))
except BaseException as error:failure={"type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
after=None
try:
 after=snapshot();js(OUT/"source-after.json",after)
 assert after==before and git("rev-parse","HEAD").decode().strip()==SOURCE and not git("status","--porcelain=v1").strip()
 assert not list((OUT/"tmp").rglob("*")),"syntax_only_created_unexpected_cache_output"
except BaseException as error:
 if failure is None:failure={"phase":"final-source-check","type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
receipt={"schema":"pinkha-page154-menu-selector-source-checks-v1","source":SOURCE,"status":"PASS" if failure is None else "FAIL",
"firstFailure":failure,"static_source_audit":"PASS" if static is not None else "NOT_COMPLETED",
"syntax_only_invocations":sum(x["label"]=="03-swift-syntax" for x in commands),"syntax_only_result":"PASS" if any(x["label"]=="03-swift-syntax" for x in commands) else "NOT_COMPLETED",
"source_input_count":len(before),"source_unchanged":before==after,"command_count":len(commands),"commands":commands,
"test_methods":0,"old_controls_replayed":0,"product_builds":0,"apple_typecheck":"NOT_RUN","actual_menu_behavior":"NOT_RUN",
"capacity_admission":"Root finite source-only1GiB floor/8MiB transient/4MiB retained; no test/build gate modified",
"free_bytes":shutil.disk_usage("/mnt/development").free}
js(OUT/"receipt.json",receipt)
files={}
for p in sorted(OUT.rglob("*")):
 if p.is_file():files[p.relative_to(OUT).as_posix()]={"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
js(OUT/"original-files.json",files)
print(json.dumps({"status":receipt["status"],"source":SOURCE,"receipt_sha256":sha((OUT/"receipt.json").read_bytes()),"originals":len(files),"test_methods":0,"syntax_only_invocations":receipt["syntax_only_invocations"],"firstFailure":failure},sort_keys=True))
if failure is not None:raise SystemExit(1)
