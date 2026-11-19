#!/usr/bin/env python3
"""Source-bound focused regressions for native creation recovery and editor preservation."""
import argparse, collections, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def manifest(root):
    result={}
    for name in ("PinkhaAnyHost", "PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaKit"):
        package=root/"Modules"/name
        paths=[package/"Package.swift",package/"Package.resolved"]+list((package/"Sources").rglob("*.swift"))
        if name in ("PinkhaAnyHost", "PinkhaAnyEngine"): paths+=list((package/"Tests").rglob("*.swift"))
        for path in sorted(set(paths)):
            if path.is_file(): result[path.relative_to(root).as_posix()]=sha(path)
    return result
def main():
    ap=argparse.ArgumentParser()
    for key in ("root","swift","output"): ap.add_argument("--"+key,type=Path,required=True)
    ap.add_argument("--package", choices=("PinkhaAnyEngine","PinkhaAnyHost"))
    ap.add_argument("--include-block-creator",action="store_true")
    args=ap.parse_args();root=args.root.resolve();scratch=root/"Modules/PinkhaAnyEngine/.build"
    env=dict(os.environ);env["PATH"]=str(args.swift.parent)+os.pathsep+env.get("PATH","")
    before=manifest(root)
    receipt={"startedAt":now(),"scope":"focused portable native-creation/editor contract regressions; iOS filesystem and actual native API are separate",
             "sourceManifest":before,"scriptSHA256":sha(Path(__file__)),"packages":[]}
    cases=[("PinkhaAnyEngine","ObjectCreationRecoveryTests",{"ObjectCreationRecoveryTests":3}),
           ("PinkhaAnyHost","NativeCreationTests|NativeSnapshotTests.testReachableEditPreservesUnrelatedOrphanAndRefusesOrphanTarget|NativeSnapshotTests.testPrepareEditPreservesUneditedStyleAndCapturesExactInverse",
            {"NativeCreationTests":16,"NativeSnapshotTests":2})]
    if args.package: cases=[case for case in cases if case[0]==args.package]
    if args.include_block_creator: cases.append(("PinkhaAnyHost","AnyNativeBlockCreatorTests",{"AnyNativeBlockCreatorTests":9}))
    valid=True
    for name,pattern,expected in cases:
        module=root/"Modules"/name
        swift_testing=pattern=="AnyNativeBlockCreatorTests"
        log=module/("partial-creation-focused-blocks.log" if swift_testing else "partial-creation-focused-xctest.log")
        with log.open("w",encoding="utf-8") as output:
            run=subprocess.run([str(args.swift),"test","--package-path",str(module),"--scratch-path",str(scratch),
                "--jobs","2","--filter",pattern,"--disable-automatic-resolution"],cwd=module,env=env,
                stdout=output,stderr=subprocess.STDOUT,timeout=1800)
        text=log.read_text(encoding="utf-8",errors="replace")
        passed=sorted(set(re.findall(r"Test Case '([^']+)' passed",text)))
        skipped=sorted(set(re.findall(r"Test Case '([^']+)' skipped",text)))
        suites=dict(collections.Counter(x.rsplit(".",1)[0] for x in passed))
        summary=re.findall(r"Executed (\d+) tests?, with (\d+) failures",text)
        count,failures=tuple(map(int,summary[-1])) if summary else (0,0)
        if swift_testing:
            expected_names=set(re.findall(r"@Test func ([A-Za-z0-9_]+)\(", (module/"Tests/PinkhaAnyHostTests/AnyNativeBlockCreatorTests.swift").read_text(encoding="utf-8")))
            names=set(re.findall(r"Test ([A-Za-z0-9_]+)\(\) passed",text))
            passed=sorted("AnyNativeBlockCreatorTests."+name for name in names)
            suites={"AnyNativeBlockCreatorTests":len(names)}
            totals=re.findall(r"Test run with (\d+) tests?(?: in \d+ suites?)? passed",text)
            count=int(totals[-1]) if totals else 0
            failures=1 if re.search(r"Test run with .*failed|Test .* failed|recorded an issue",text) else 0
            skipped=["unexpected skipped test"] if re.search(r"Test .* skipped",text) else []
            exact_names=names==expected_names and len(expected_names)==9
        else: exact_names=True
        ok=run.returncode==0 and count==sum(expected.values()) and failures==0 and not skipped and suites==expected and exact_names
        receipt["packages"].append({"package":name,"valid":ok,"exitCode":run.returncode,"count":count,
            "failures":failures,"suites":suites,"expectedSuites":expected,"passed":passed,"skipped":skipped,"logSHA256":sha(log)})
        print(json.dumps({"package":name,"valid":ok,"count":count,"failures":failures,"suites":suites}),flush=True)
        if not ok:
            valid=False;print("\n".join(text.splitlines()[-100:]),flush=True)
        elif name=="PinkhaAnyHost":
            source=scratch/"x86_64-unknown-windows-msvc/debug/pinkha-any-host-probe.exe"
            target=root/"build/any-engine-port/host-probe-v3.exe"
            shutil.copyfile(source,target)
            receipt["hostProbe"]={"path":target.relative_to(root).as_posix(),"sha256":sha(target)}
    receipt["sourceStable"]=manifest(root)==before
    receipt["status"]="PASS" if valid and receipt["sourceStable"] else "FAIL"
    receipt["finishedAt"]=now()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":receipt["status"],"sourceStable":receipt["sourceStable"],"receipt":str(args.output)}),flush=True)
    return 0 if receipt["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
