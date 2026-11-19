#!/usr/bin/env python3
"""Probe-only progress compile/relink; all production objects and19 assertions retained."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, urllib.request

ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("baseline","fixture","native-binary","native-manifest"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--allow-disposable-writes",action="store_true")
    args=parser.parse_args()
    if not args.allow_disposable_writes:parser.error("Owned disposable fixture authorization required")
    original_path=ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py"
    spec=importlib.util.spec_from_file_location("original_torah_runner",original_path)
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    baseline=json.loads(args.baseline.read_text());fixture=json.loads(args.fixture.read_text())
    source=original.manifest()
    changed=[p for p in set(source)|set(baseline["sourceManifest"]) if source.get(p)!=baseline["sourceManifest"].get(p)]
    expected="Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/TorahWorkflowProbe.swift"
    if changed!=[expected]:parser.error("Only the CLI progress source may differ from the successful baseline build")
    if source[expected]!="7e065223f258ff5081dfba5d3aee96d1c9f0ff5de99f5ca8eb74b1222be6961f":parser.error("Unexpected progress instrumentation source")
    if sha(args.native_binary)!=original.NATIVE_SHA or sha(args.native_manifest)!=original.MANIFEST_SHA:parser.error("Pinned native mismatch")
    if fixture.get("endpoint")!="http://127.0.0.1:60663":parser.error("Assigned fixture60663 only")
    if shutil.disk_usage(ROOT).free<1024**3:parser.error("Less than1GiB free; no compile started")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    prefix=ROOT/"docs/any-engine-port/evidence/20261119"/("native-torah-direct-progress-"+stamp)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    work=ROOT/"build/any-engine-port"/("torah-direct-progress-"+stamp)
    work.mkdir(parents=True,exist_ok=True)
    debug=ROOT/"Modules/PinkhaAnyHost/.build/x86_64-unknown-windows-msvc/debug"
    listed=(debug/"pinkha-any-host-probe.product/Objects.LinkFileList").read_text().splitlines()
    objects=[Path(p.strip()) for p in listed if p.strip() and "PinkhaAnyHostProbe" not in p]
    if not objects or not all(p.is_file() for p in objects):parser.error("Retained production object list unavailable")
    dependencies={p.relative_to(ROOT).as_posix():sha(p) for p in objects}
    for p in (debug/"Modules").glob("*.swiftmodule"):dependencies[p.relative_to(ROOT).as_posix()]=sha(p)
    (work/"objects.rsp").write_text("\n".join('"'+str(p)+'"' for p in objects),encoding="utf-8")
    sources=sorted((ROOT/"Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe").glob("*.swift"))
    swiftc=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
    sdk=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk")
    probe=work/"pinkha-any-host-progress.exe"
    # This private import cache is already warm; no shared package cache is mutated.
    module_cache=ROOT/"build/any-engine-port/inline-hanlin-components-v5/ModuleCache"
    command=[str(swiftc),"-parse-as-library","-swift-version","6","-module-name","PinkhaAnyHostProbe",
             "-j1","-whole-module-optimization","-num-threads","1","-Onone","-gnone",
             "-I",str(debug/"Modules"),"-module-cache-path",str(module_cache),
             "-sdk",str(sdk),"-use-ld=lld","-Xlinker","/threads:1","-Xlinker","/debug:none",
             "-Xlinker","/incremental:no"]
    for module in ("swift-crypto/Sources/CCryptoBoringSSLShims/include","swift-crypto/Sources/CCryptoBoringSSL/include"):
        path=ROOT/"Modules/PinkhaAnyHost/.build/checkouts"/module
        command+=["-Xcc","-fmodule-map-file="+str(path/"module.modulemap"),"-Xcc","-I"+str(path)]
    command += [str(p) for p in sources]+["@"+str(work/"objects.rsp"),"-o",str(probe)]
    record={"schemaVersion":1,"status":"RUNNING","startedAt":now(),"scope":"direct_native_t5_with_probe_only_progress",
            "businessScope":original.SCOPE,"sourceManifest":source,"changedSourcesFromBaseline":changed,
            "baselineBuildReceiptSHA256":sha(args.baseline),"productionContractsChanged":False,
            "cliInstrumentationOnly":True,"expectedCount":19,"productionTimeoutsChanged":False,
            "cachedDependencyManifest":dependencies,"cachedDependencyObjectCount":len(objects),
            "nativeBinarySHA256":original.NATIVE_SHA,"nativeSourceManifestSHA256":original.MANIFEST_SHA,
            "runnerSHA256":sha(Path(__file__)),"compileCommand":command,"compileDeadlineSeconds":120,
            "compilerThreads":1,"debugInformationRequested":False,
            "protectedAppleJournal":False,"engineProcessRestart":False,"uiInteraction":False,"liveProviderTransport":False}
    receipt=prefix.with_suffix(".json");receipt.write_text(json.dumps(record,indent=2)+"\n")
    env=dict(os.environ);env["PATH"]=str(swiftc.parent)+os.pathsep+env.get("PATH","")
    build_log=prefix.with_suffix(".build.log");stdout_path=prefix.with_suffix(".stdout.log");stderr_path=prefix.with_suffix(".stderr.log")
    valid=False;stage="compile_and_link"
    try:
        with build_log.open("wb") as out:
            code=original.bounded(command,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT,seconds=120)
        record["compileExitCode"]=code
        if code:raise RuntimeError("Probe-only compile/link failed")
        record["probeSHA256"]=sha(probe)
        stage="native_health"
        with urllib.request.urlopen(fixture["endpoint"]+"/v1/health",timeout=10) as response:health=json.load(response)
        if health.get("status")!="ok" or health.get("account")!=fixture["accountId"]:raise RuntimeError("Assigned fixture account mismatch")
        record["engineStartedAt"]=health.get("startedAt")
        stage="direct_native_probe"
        run=[str(probe),fixture["endpoint"],fixture["spaceId"],fixture["accountId"],"--torah-workflow","--allow-disposable-writes"]
        with stdout_path.open("wb") as out,stderr_path.open("wb") as err:
            code=original.bounded(run,cwd=ROOT,env=env,stdout=out,stderr=err,seconds=300)
        record["probeExitCode"]=code
        lines=stdout_path.read_text(encoding="utf-8").strip().splitlines()
        result=json.loads(lines[-1]) if lines else {}
        record["result"]=result
        progress=[line for line in stderr_path.read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith("T5_PROGRESS ")]
        record["progress"]=progress
        valid=(code==0 and result.get("status")=="PASS" and result.get("scope")==original.SCOPE and
               result.get("count")==19 and len(set(result.get("checks",[])))==19 and
               result.get("protectedAppleJournal") is False and result.get("engineProcessRestart") is False)
    except Exception as error:
        record["failure"]={"kind":type(error).__name__,"stage":stage}
    for name,path in (("buildLog",build_log),("stdout",stdout_path),("stderr",stderr_path)):
        if path.is_file():record[name]=path.relative_to(ROOT).as_posix();record[name+"SHA256"]=sha(path)
    record.update(sourceStable=source==original.manifest(),
                  cachedDependenciesStable=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in dependencies.items()),
                  nativeBinaryUnchanged=sha(args.native_binary)==original.NATIVE_SHA,
                  nativeManifestUnchanged=sha(args.native_manifest)==original.MANIFEST_SHA,
                  finishedAt=now())
    stable=all(record[k] for k in ("sourceStable","cachedDependenciesStable","nativeBinaryUnchanged","nativeManifestUnchanged"))
    record["status"]="PASS" if valid and stable else "FAIL"
    receipt.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in ("sourceManifest","cachedDependencyManifest","compileCommand")},indent=2))
    if record.get("compileExitCode")!=0 and build_log.is_file():print(build_log.read_text(errors="replace")[-12000:])
    print(json.dumps({"receipt":receipt.relative_to(ROOT).as_posix(),"probe":str(probe)}))
    return 0 if record["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
