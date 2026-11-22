#!/usr/bin/env python3
"""Parse eight exact complete Swift candidates; this is not Apple semantic/native qualification."""
from datetime import datetime, timezone
import hashlib,json,os
from pathlib import Path
import subprocess,sys,time,traceback

BASE=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-editor-process-resume-implementation-20261122")
PACKET=BASE/"controls-source-v1"
OUT=BASE/"controls-execution-v1"/"windows-full-parses"
INPUT_SHA="5bb06ba4f44a151026f190f6c2d7310ed812ce6f32b7a7aa4ab2153a4fbf7d97"
SWIFT=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.EXE")
SWIFT_SHA="e1d0a0b20d95a92b22f4906e7ca331a7c8b89be86b2d9a2d215ac24f753e945a"
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,v):
    t=p.with_suffix(p.suffix+".new")
    t.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    os.replace(t,p)
def require(v,m):
    if not v:raise RuntimeError(m)
def inputs(manifest):
    rows=[]
    for item in manifest["swiftFullFileParseInputs"]:
        p=Path(item["path"])
        require(p.is_file() and not p.is_symlink() and p.stat().st_size==item["bytes"] and sha(p)==item["sha256"],
                "Frozen complete Swift input differs: "+item["repoPath"])
        rows.append(item)
    require(len(rows)==8 and len({row["path"] for row in rows})==8,"Full Swift parse membership differs")
    return rows
OUT.mkdir(parents=True,exist_ok=False)
state={"schema":"otzaria.stageb-complete-swift-parse/1","status":"RUNNING","started":utc(),
       "ownerPID":os.getpid(),"commands":[],"childBudgetSeconds":60,"globalBudgetSeconds":540,
       "semanticCompilation":False,"nativeExecution":False,"testsExecuted":0,
       "scope":"Windows full-file syntax only; Apple conditional imports, UIKit/Security and simulator runtime remain unqualified"}
atomic(OUT/"RESULT.json",state)
deadline=time.monotonic()+540
process=None
try:
    require(os.name=="nt","Expected existing Windows Swift environment")
    require(sha(PACKET/"INPUTS.json")==INPUT_SHA,"Input manifest differs")
    manifest=json.loads((PACKET/"INPUTS.json").read_text())
    runner_root=BASE/"controls-runner-v1"
    runner_manifest=json.loads((runner_root/"RUNNERS.json").read_text())
    require(runner_manifest["inputManifestSha256"]==INPUT_SHA,"Runner/input binding differs")
    for item in runner_manifest["files"]:
        path=runner_root/item["path"]
        require(path.is_file() and not path.is_symlink() and path.stat().st_size==item["bytes"] and sha(path)==item["sha256"],"Runner bytes differ")
    state["sourceBefore"]=inputs(manifest)
    require(SWIFT.is_file() and sha(SWIFT)==SWIFT_SHA and SWIFT.read_bytes()[:2]==b"MZ","Compiler bytes differ")
    state["compiler"]={"path":str(SWIFT),"sha256":SWIFT_SHA,"bytes":SWIFT.stat().st_size}
    for index,source in enumerate([None,*state["sourceBefore"]]):
        command=([str(SWIFT),"--version"] if source is None else
                 [str(SWIFT),"-frontend","-parse","-D","DEBUG",source["path"]])
        label="compiler-version" if source is None else "parse-"+str(index)
        stdout=OUT/(label+".stdout");stderr=OUT/(label+".stderr")
        row={"command":command,"label":label,"status":"STARTING","started":utc(),
             "timedOut":False,"budgetSeconds":min(15 if source is None else 60,deadline-time.monotonic())}
        require(row["budgetSeconds"]>0,"Total parse budget exhausted")
        state["commands"].append(row);atomic(OUT/"RESULT.json",state)
        start=time.monotonic()
        with stdout.open("xb") as o,stderr.open("xb") as e:
            process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=o,stderr=e)
            row.update(pid=process.pid,status="RUNNING");atomic(OUT/"RESULT.json",state)
            try:rc=process.wait(timeout=row["budgetSeconds"])
            except subprocess.TimeoutExpired:
                row["timedOut"]=True
                killed=subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                                      capture_output=True,timeout=15)
                row["ownedTreeCleanup"]={"command":killed.args,"returncode":killed.returncode,
                    "stdout":killed.stdout.decode(errors="replace"),"stderr":killed.stderr.decode(errors="replace")}
                rc=process.wait(timeout=5)
        process=None
        row.update(returncode=rc,seconds=time.monotonic()-start,finished=utc(),
                   stdout={"path":str(stdout),"sha256":sha(stdout),"bytes":stdout.stat().st_size},
                   stderr={"path":str(stderr),"sha256":sha(stderr),"bytes":stderr.stat().st_size},
                   status="PASS" if rc==0 and not row["timedOut"] else "FAIL")
        atomic(OUT/"RESULT.json",state)
        require(row["status"]=="PASS","Full-file parse failed; no automatic replay")
        if source is None:state["compiler"]["version"]=stdout.read_text(errors="replace")
    state["sourceAfter"]=inputs(manifest)
    require(state["sourceBefore"]==state["sourceAfter"] and sha(SWIFT)==SWIFT_SHA,"Source/compiler changed")
    state.update(status="PASS",fullFilesParsed=8)
except BaseException as error:
    state.update(status="FAIL",errorType=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    if process is not None and process.poll() is None:
        cleanup=subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True,timeout=15)
        state["finalOwnedCleanup"]={"pid":process.pid,"returncode":cleanup.returncode}
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:state["ownedChildStillRunning"]=True
    state["finished"]=utc();atomic(OUT/"RESULT.json",state)
print(json.dumps({key:state.get(key) for key in ("status","fullFilesParsed","errorType","error","finished")}))
sys.exit(0 if state["status"]=="PASS" else 1)
