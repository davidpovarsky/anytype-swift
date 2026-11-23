import os,json,hashlib,resource,signal,subprocess,time
from pathlib import Path
ROOT=Path("/run/anytapy-wave15-source-overlay-20261123/editor")
DOC=ROOT/"docs/validation/20261123-current-page154"
SOURCE=DOC/"static-check.py"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def allocated():return sum(p.lstat().st_blocks*512 for p in ROOT.rglob("*"))
available=int(next(v.split()[1] for v in Path("/proc/meminfo").read_text().splitlines() if v.startswith("MemAvailable:")))*1024
assert allocated()+262144<=8*1024**2 and available>=2*1024**3
assert sha(SOURCE)=="911915ae5d4e860937c0b8efd5257cf34b684a7edd517bc1ed9b54077c22bc26"
OUT=DOC/"static-check-originals"/"attempt1";OUT.mkdir(mode=0o700,parents=True)
argv=["python3","-B",str(SOURCE)]
def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE,(131072,131072))
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))
record={"scope":"SOURCE_ONLY_AST_GIT_YAML_BASH","argv":argv,"sourceSHA256":sha(SOURCE),
 "deadlineSeconds":25,"cleanupSeconds":5,"hostMethods":0,"AppleBuilds":0,"productTests":0,
 "allocationBefore":allocated(),"MemAvailableBefore":available}
first=None;process=None;start=time.monotonic()
with (OUT/"original.stdout").open("xb") as stdout,(OUT/"original.stderr").open("xb") as stderr:
    try:
        process=subprocess.Popen(argv,cwd=ROOT,env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","PYTHONDONTWRITEBYTECODE":"1"},
          stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits)
        record.update(pid=process.pid,pgid=os.getpgid(process.pid))
        assert process.pid==record["pgid"]
        (OUT/"started.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
        process.wait(timeout=25);record["returnCode"]=process.returncode
        if process.returncode:raise RuntimeError("Source-only checker failed")
    except BaseException as error:first={"type":type(error).__name__,"message":str(error)}
    finally:
        if process is not None:
            cleanup=time.monotonic()+5
            try:
                os.killpg(process.pid,0)
                os.killpg(process.pid,signal.SIGTERM)
                while time.monotonic()<cleanup:
                    try:os.killpg(process.pid,0)
                    except ProcessLookupError:break
                    if time.monotonic()>cleanup-2:os.killpg(process.pid,signal.SIGKILL)
                    try:process.wait(timeout=.05)
                    except subprocess.TimeoutExpired:pass
                    time.sleep(.02)
            except ProcessLookupError:pass
            try:os.killpg(process.pid,0);record["ownedGroupAbsent"]=False
            except ProcessLookupError:record["ownedGroupAbsent"]=True
            if not record["ownedGroupAbsent"]:first=first or {"type":"OwnedGroupStillPresent"}
record["elapsedSeconds"]=time.monotonic()-start
record["sourceAfterSHA256"]=sha(SOURCE)
record["originals"]={n:{"sha256":sha(OUT/n),"bytes":(OUT/n).stat().st_size} for n in ("original.stdout","original.stderr")}
record["allocationAfter"]=allocated()
if record["sourceAfterSHA256"]!=record["sourceSHA256"] or record["allocationAfter"]>8*1024**2:
    first=first or {"type":"FinalSourceOrAllocationGuard"}
record["firstFailure"]=first
record["status"]="PASS_SOURCE_ONLY" if first is None else "FAIL"
(OUT/"execution-receipt.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
if first is None:
    result=json.loads((OUT/"original.stdout").read_bytes())
    assert result["status"]=="PASS_SOURCE_ONLY"
    (DOC/"source-qualification.json").write_text(json.dumps({"status":"PASS_SOURCE_ONLY","source":result,
      "executionReceiptSHA256":sha(OUT/"execution-receipt.json"),"originalStdoutSHA256":sha(OUT/"original.stdout"),
      "originalStderrSHA256":sha(OUT/"original.stderr")},indent=2,sort_keys=True)+"\n")
print(json.dumps(record))
raise SystemExit(0 if first is None else 1)
