#!/usr/bin/env python3
"""Focused exact native inline projection regressions in the real Hanlin package."""
import argparse, collections, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def manifest(root):
    result={}
    targets={
        "PinkhaAnyHanlin": ("PinkhaAnyHanlin","PinkhaHanlinCore","PinkhaHanlinUI"),
        "PinkhaAnyHost": ("PinkhaAnyHost",),
        "PinkhaAnyEngine": ("PinkhaAnyEngine",),
        "PinkhaAnyIntegration": ("PinkhaAnyIntegration",),
        "PinkhaKit": ("PinkhaKit",),
    }
    for name, names in targets.items():
        package=root/"Modules"/name
        paths=[package/"Package.swift",package/"Package.resolved"]
        for target in names: paths+=list((package/"Sources"/target).rglob("*.swift"))
        if name=="PinkhaAnyHanlin":paths+=list((package/"Tests").rglob("*.swift"))
        for path in sorted(set(paths)):
            if path.is_file(): result[path.relative_to(root).as_posix()]=sha(path)
    return result
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--swift",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve();package=root/"Modules/PinkhaAnyHanlin"
    before=manifest(root)
    receipt={"startedAt":now(),"scope":"real Hanlin Swift package; focused shared inline projection tests; no UIKit execution",
             "sourceManifest":before,"scriptSHA256":sha(Path(__file__))}
    env=dict(os.environ);env["PATH"]=str(args.swift.parent)+os.pathsep+env.get("PATH","")
    command=[str(args.swift),"test","--package-path",str(package),
             "--scratch-path",str(root/"Modules/PinkhaAnyEngine/.build"),"--jobs","2",
             "--filter","AnyHanlinPlainTextTests","--disable-automatic-resolution"]
    log=args.output.with_suffix(".log");log.parent.mkdir(parents=True,exist_ok=True)
    receipt["status"]="RUNNING"
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    harness_error=None
    with log.open("w",encoding="utf-8") as out:
        process=subprocess.Popen(command,cwd=package,env=env,stdout=out,stderr=subprocess.STDOUT)
        try:
            code=process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            harness_error="package_setup_or_build_timeout"
            if process.poll() is None:
                if os.name=="nt":
                    subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                                   stdout=out,stderr=subprocess.STDOUT,timeout=30)
                else:
                    process.kill()
            process.wait(timeout=30)
            code=124
    run=subprocess.CompletedProcess(command,code)
    text=log.read_text(encoding="utf-8",errors="replace")
    passed=sorted(set(re.findall(r"Test Case '([^']+)' passed",text)))
    skipped=sorted(set(re.findall(r"Test Case '([^']+)' skipped",text)))
    suites=dict(collections.Counter(name.rsplit(".",1)[0] for name in passed))
    expected={"AnyHanlinPlainTextTests":13}
    summary=re.findall(r"Executed (\d+) tests?, with (\d+) failures",text)
    count,failures=tuple(map(int,summary[-1])) if summary else (0,0)
    valid=run.returncode==0 and count==13 and failures==0 and not skipped and suites==expected
    receipt.update({"harnessError":harness_error,"exitCode":run.returncode,"count":count,"failures":failures,"skipped":skipped,
                    "passed":passed,"suites":suites,"expectedSuites":expected,
                    "log":str(log.relative_to(root)),"logSHA256":sha(log),"command":command,
                    "sourceStable":manifest(root)==before,"finishedAt":now()})
    receipt["status"]="PASS" if valid and receipt["sourceStable"] else "FAIL"
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:receipt[k] for k in ("status","count","failures","sourceStable","suites")}),flush=True)
    if not valid:print("\n".join(text.splitlines()[-100:]),flush=True)
    return 0 if receipt["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
