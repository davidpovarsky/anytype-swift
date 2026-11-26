#!/usr/bin/env python3
"""Qualify the typed contract only. This never grants native or app acceptance."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, signal, subprocess, time

PINS = {
    "contract.go": "a725194a6a3e43ec7b65c1279831e6ac8289871fac4b938cd41f5940194d89cc",
    "contract_test.go": "a600720c34e80532bc487bbc939c1e38059627b8f86ca1f43225deed91a3dfeb",
}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(root, name, value):
    p=root/name; temporary=p.with_suffix(p.suffix+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    temporary.replace(p)
def group_members(pgid):
    members=[]
    for directory in Path("/proc").iterdir():
        if not directory.name.isdigit(): continue
        try:
            stat=(directory/"stat").read_text()
            fields=stat[stat.rfind(")")+2:].split()
            if int(fields[2])==pgid: members.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError): pass
    return sorted(members)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--cache",type=Path,required=True)
    args=parser.parse_args()
    source=Path(__file__).resolve().parent/"overlay/pkg/lib/pinkha/torahcutovercontract"
    root=args.root.resolve()
    root.mkdir(parents=True,exist_ok=False)
    result={"status":"FAIL","scope":"pure typed metadata bytes/identity only","nativeCalls":0,"applicationTests":0}
    process=None; proved_absent=False; code=None
    try:
        before={}
        for name,expected in PINS.items():
            p=source/name
            if not p.is_file() or p.is_symlink() or digest(p)!=expected: raise ValueError("source pin: "+name)
            before[name]={"bytes":p.stat().st_size,"sha256":expected}
        package=root/"source";package.mkdir()
        for name in PINS: (package/name).write_bytes((source/name).read_bytes())
        (package/"go.mod").write_text("module pinkha.invalid/cutover-contract\n\ngo 1.27.0\n")
        version=subprocess.check_output(["/usr/local/bin/go","version"],text=True,timeout=5).strip()
        if version!="go version go1.27.4 linux/arm64": raise ValueError("unqualified toolchain")
        save(root,"source-before.json",before)
        env=dict(os.environ,GOWORK="off",GOTOOLCHAIN="local",GOMAXPROCS="2",GOCACHE=str(args.cache.resolve()))
        argv=["/usr/local/bin/go","test","-json","-count=1","-p","2","./..."]
        save(root,"command.json",{"argv":argv,"cwd":str(package),"toolchain":version,
             "sourceProducerSHA256":digest(Path(__file__)),"startedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "environment":{k:env[k] for k in ("GOWORK","GOTOOLCHAIN","GOMAXPROCS","GOCACHE")}})
        start=time.monotonic()
        with (root/"original.jsonl").open("wb") as log:
            process=subprocess.Popen(argv,cwd=package,env=env,stdin=subprocess.DEVNULL,
                                     stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save(root,"started.json",{"pid":process.pid,"pgid":process.pid})
            try: code=process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                for sig in (signal.SIGTERM,signal.SIGKILL):
                    try: os.killpg(process.pid,sig)
                    except ProcessLookupError: proved_absent=True;break
                    try: code=process.wait(timeout=5);break
                    except subprocess.TimeoutExpired: continue
                raise RuntimeError("actual contract compiler/test deadline")
        remaining=group_members(process.pid)
        proved_absent=not remaining
        result["ownedProcessGroupRemaining"]=remaining
        result["exitCode"]=code; result["durationSeconds"]=time.monotonic()-start
        after={n:{"bytes":(package/n).stat().st_size,"sha256":digest(package/n)} for n in PINS}
        save(root,"source-after.json",after)
        rows=[]
        for line in (root/"original.jsonl").read_text().splitlines():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
        expected=re.findall(r"^func (Test\w+)\(", (package/"contract_test.go").read_text(),re.M)
        outcomes={kind:[r["Test"] for r in rows if r.get("Action")==kind and r.get("Test")] for kind in ("pass","fail","skip")}
        result.update(expected=expected,outcomes=outcomes,sourceUnchanged=before==after,
                      originalLogSHA256=digest(root/"original.jsonl"))
        if code!=0 or not proved_absent or before!=after or outcomes["pass"]!=expected or outcomes["fail"] or outcomes["skip"]:
            raise RuntimeError("original contract result did not qualify")
        if any(digest(source/n)!=pin for n,pin in PINS.items()): raise RuntimeError("source changed during qualification")
        result["status"]="PASS"
    except Exception as error:
        result["error"]=type(error).__name__+": "+str(error)
    finally:
        if process is not None and not proved_absent:
            try:
                members=group_members(process.pid)
                result["finalOwnedProcessGroupRemaining"]=members
                if members: result["status"]="FAIL"
            except Exception as error:
                result["cleanupError"]=type(error).__name__+": "+str(error);result["status"]="FAIL"
        save(root,"result.json",result)
    print(json.dumps(result))
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
