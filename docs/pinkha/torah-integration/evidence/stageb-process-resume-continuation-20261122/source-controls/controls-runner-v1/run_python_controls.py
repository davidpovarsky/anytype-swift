#!/usr/bin/env python3
"""Finite POSIX-only owner for the exact four plus twenty new source controls."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
import traceback

INPUT_SHA = "5bb06ba4f44a151026f190f6c2d7310ed812ce6f32b7a7aa4ab2153a4fbf7d97"
def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path, value):
    tmp = path.with_suffix(path.suffix + ".new")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
def require(value, reason):
    if not value: raise RuntimeError(reason)
def regular(path, root):
    path = Path(path)
    for part in [path, *path.parents]:
        require(not part.is_symlink(), "Aliased control input: " + str(part))
        if part == root: break
    require(path.is_relative_to(root) and stat.S_ISREG(path.stat().st_mode), "Nonregular control input")
    return path
def source_inventory(packet, manifest):
    rows = {}
    for item in manifest["pythonInputs"]:
        path = regular(packet / "python-closure" / item["path"], packet)
        require(path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], "Changed Python input: " + item["path"])
        rows[path.relative_to(packet).as_posix()] = {"bytes":item["bytes"], "sha256":item["sha256"]}
    actual = {path.relative_to(packet/"python-closure").as_posix()
              for path in (packet/"python-closure").rglob("*") if path.is_file() or path.is_symlink()}
    require(actual == {item["path"] for item in manifest["pythonInputs"]}, "Unexpected Python source closure")
    item=manifest["collectorControl"]
    path=regular(packet/"test_process_receipts.py",packet)
    require(path.stat().st_size==item["bytes"] and sha(path)==item["sha256"], "Changed collector assertions")
    rows["test_process_receipts.py"]={"bytes":item["bytes"],"sha256":item["sha256"]}
    return rows
def group_exists(pgid):
    try: os.killpg(pgid,0); return True
    except ProcessLookupError: return False
def cleanup_group(pgid):
    if not group_exists(pgid): return {"survived":False,"term":False,"kill":False}
    result={"survived":True,"term":True,"kill":False}
    os.killpg(pgid,signal.SIGTERM)
    deadline=time.monotonic()+3
    while group_exists(pgid) and time.monotonic()<deadline: time.sleep(0.05)
    if group_exists(pgid):
        os.killpg(pgid,signal.SIGKILL);result["kill"]=True
        deadline=time.monotonic()+3
        while group_exists(pgid) and time.monotonic()<deadline:time.sleep(0.05)
    result["remaining"]=group_exists(pgid)
    return result
parser=argparse.ArgumentParser()
parser.add_argument("--packet",required=True)
parser.add_argument("--runners",required=True)
parser.add_argument("--out",required=True)
args=parser.parse_args()
packet=Path(args.packet).resolve(strict=True)
runners=Path(args.runners).resolve(strict=True)
out=Path(args.out).resolve()
out.mkdir(parents=True,exist_ok=False)
state={"schema":"otzaria.stageb-portable-source-controls/1","status":"RUNNING","started":utc(),
       "ownerPID":os.getpid(),"globalBudgetSeconds":300,"childBudgetSeconds":120,"commands":[],
       "nativeExecution":False,"automaticRetries":0,"oldUnchangedSuitesSelected":[]}
atomic(out/"RESULT.json",state)
deadline=time.monotonic()+300
process=None
active_row=None
try:
    require(os.name=="posix" and sys.platform.startswith("linux") and hasattr(os,"O_NOFOLLOW"),
            "These controls require actual Linux POSIX no-follow/symlink semantics")
    require(sha(packet/"INPUTS.json")==INPUT_SHA,"Frozen input manifest differs")
    manifest=json.loads((packet/"INPUTS.json").read_text())
    proof=json.loads((runners/"RUNNERS.json").read_text())
    for item in proof["files"]:
        path=regular(runners/item["path"],runners)
        require(path.stat().st_size==item["bytes"] and sha(path)==item["sha256"],"Runner differs")
    require(proof["inputManifestSha256"]==INPUT_SHA,"Runner/input binding differs")
    before=source_inventory(packet,manifest)
    state["sourceBefore"]=before
    interpreter=Path(sys.executable).resolve(strict=True)
    state["interpreter"]={"path":str(interpreter),"sha256":sha(interpreter),"version":sys.version,
                           "bytes":interpreter.stat().st_size,"binaryKind":"ELF" if interpreter.read_bytes()[:4]==b"\x7fELF" else "OTHER"}
    require(state["interpreter"]["binaryKind"]=="ELF","Actual Python interpreter is not an ELF executable")
    for group,count in [("public",4),("collector",20)]:
        child_out=out/group;child_out.mkdir()
        command=[str(interpreter),"-I","-B",str(runners/"control_child.py"),
                 "--packet",str(packet),"--out",str(child_out),"--group",group]
        row={"group":group,"command":command,"budgetSeconds":min(120,deadline-time.monotonic()),
             "started":utc(),"timedOut":False,"status":"STARTING"}
        require(row["budgetSeconds"]>0,"Overall control budget exhausted")
        state["commands"].append(row);atomic(out/"RESULT.json",state)
        started=time.monotonic()
        with (child_out/"stdout.txt").open("xb") as stdout,(child_out/"stderr.txt").open("xb") as stderr:
            process=subprocess.Popen(command,cwd=packet,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,
                                     start_new_session=True,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","PYTHONUTF8":"1"})
            active_row=row;row.update(pid=process.pid,pgid=process.pid,status="RUNNING")
            atomic(out/"RESULT.json",state)
            try:code=process.wait(timeout=row["budgetSeconds"])
            except subprocess.TimeoutExpired:
                row["timedOut"]=True
                row["timeoutCleanup"]=cleanup_group(process.pid)
                code=process.wait(timeout=5)
            row.update(returncode=code,seconds=time.monotonic()-started,finished=utc())
            row["survivorCleanup"]=cleanup_group(process.pid)
        process=None;active_row=None
        child_result=child_out/"RESULT.json"
        child=json.loads(child_result.read_text()) if child_result.is_file() else None
        row["childResult"]=child
        row["stdout"]={"bytes":(child_out/"stdout.txt").stat().st_size,"sha256":sha(child_out/"stdout.txt")}
        row["stderr"]={"bytes":(child_out/"stderr.txt").stat().st_size,"sha256":sha(child_out/"stderr.txt")}
        success=(code==0 and not row["timedOut"] and not row["survivorCleanup"]["survived"]
                 and child is not None and child.get("status")=="PASS" and child.get("caseCount")==count)
        row["status"]="PASS" if success else "FAIL";atomic(out/"RESULT.json",state)
        require(success,"Focused group failed; preserving raw evidence without automatic replay: "+group)
    state["sourceAfter"]=source_inventory(packet,manifest)
    require(state["sourceBefore"]==state["sourceAfter"],"Inputs changed while controls executed")
    require(sha(interpreter)==state["interpreter"]["sha256"],"Python executable changed")
    loaded=set().union(*(set(row["childResult"]["loadedSources"]) for row in state["commands"]))
    require(loaded=={key for key in before if key.endswith(".py")},"Incomplete observed target Python source coverage")
    state.update(status="PASS",actualCaseCount=24,observedImportedSources=sorted(loaded))
except BaseException as error:
    state.update(status="FAIL",errorType=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    if process is not None:
        state["finalOwnedCleanup"]=cleanup_group(process.pid)
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: state["finalOwnedChildStillRunning"]=True
    state["finished"]=utc()
    atomic(out/"RESULT.json",state)
print(json.dumps({key:state.get(key) for key in ("status","actualCaseCount","errorType","error","finished")}))
sys.exit(0 if state["status"]=="PASS" else 1)
