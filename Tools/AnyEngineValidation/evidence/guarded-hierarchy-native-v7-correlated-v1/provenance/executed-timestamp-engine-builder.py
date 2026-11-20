#!/usr/bin/env python3
"""Build only the isolated v3 HTTP trace Engine with absolute Unix-ms timestamps."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/"Tools/AnyEngineValidation/evidence/native-torah-workflow-scripts"
V2_PROVENANCE_SHA="f60b68d1a5acc4c050a95569ea4a18d40e8aa37397e8e875ad5df4ac39a6f517"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def source_map():
    base=ROOT/"Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine"
    return {p.relative_to(base).as_posix():sha(p) for p in sorted(base.rglob("*.swift"))}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-private-diagnostic-build",action="store_true")
    args=parser.parse_args()
    if not args.allow_private_diagnostic_build:parser.error("Explicit diagnostic build authorization required")
    provenance_path=ARCHIVE/"reusable-trace-engine-v2.json"
    if sha(provenance_path)!=V2_PROVENANCE_SHA:parser.error("v2 provenance changed")
    provenance=json.loads(provenance_path.read_text(encoding="utf-8"))
    before=source_map()
    if before!=provenance["originalEngineSourceManifest"]:parser.error("Original Engine source drift")
    baseline_path=ROOT/provenance["buildReceipt"]
    if sha(baseline_path)!=provenance["buildReceiptSHA256"]:parser.error("v2 build receipt changed")
    baseline=json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline["status"]!="PASS" or baseline["result"]["count"]!=19:parser.error("v2 proof unavailable")
    if shutil.disk_usage(ROOT).free<1024**3:parser.error("Less than1GiB free; no compile started")
    v2_work=(ROOT/provenance["compiledFiles"]["PinkhaAnyEngine.o"]["path"]).parent
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    work=ROOT/"build/any-engine-port"/("http-trace-engine-v3-"+stamp)
    (work/"Modules").mkdir(parents=True,exist_ok=False)
    copied=[]
    for relative,expected in provenance["copiedEngineSourceManifest"].items():
        source=v2_work/"EngineSources"/relative
        if sha(source)!=expected:parser.error("v2 diagnostic source drift")
        target=work/"EngineSources"/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append(target)
    client=work/"EngineSources/AnyHTTPClient.swift"
    old='''        "elapsedMs": Int(max(0, ProcessInfo.processInfo.systemUptime - start) * 1000)
'''
    new='''        "elapsedMs": Int(max(0, ProcessInfo.processInfo.systemUptime - start) * 1000),
        "timestampUnixMs": Int64((Date().timeIntervalSince1970 * 1000).rounded(.down))
'''
    text=client.read_text(encoding="utf-8")
    if text.count(old)!=1:parser.error("Exact timestamp insertion point unavailable")
    client.write_text(text.replace(old,new),encoding="utf-8",newline="\n")
    copied_manifest={p.relative_to(work/"EngineSources").as_posix():sha(p) for p in copied}
    differences=[p for p,h in copied_manifest.items() if provenance["copiedEngineSourceManifest"].get(p)!=h]
    if differences!=["AnyHTTPClient.swift"]:parser.error("Unexpected additional v3 source changes")
    def rebased(command):return [value.replace(str(v2_work),str(work)) for value in command]
    engine_command=rebased(provenance["compilerCommand"])
    wrapper_command=rebased(provenance["modulewrapCommand"])
    dependencies={p:h for p,h in baseline["cachedDependencyManifest"].items() if p.endswith(".swiftmodule")}
    for p,h in dependencies.items():
        if sha(ROOT/p)!=h:parser.error("Cached imported Swift module drift")
    swiftc=Path(engine_command[0])
    compiler_sha=sha(swiftc)
    original_path=ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py"
    spec=importlib.util.spec_from_file_location("bounded_torah_runner",original_path)
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    record={"schemaVersion":1,"status":"RUNNING","scope":"isolated_http_trace_engine_with_absolute_time",
        "startedAt":now(),"buildOnly":True,"executedNativeChecks":0,"productionSourceChanged":False,
        "requestConfigurationChanged":False,"timeoutsChanged":False,"diagnosticChange":"timestampUnixMs only",
        "v2ProvenancePath":provenance_path.relative_to(ROOT).as_posix(),"v2ProvenanceSHA256":sha(provenance_path),
        "v2BuildReceipt":baseline_path.relative_to(ROOT).as_posix(),"v2BuildReceiptSHA256":sha(baseline_path),
        "originalEngineSourceManifest":before,"copiedEngineSourceManifest":copied_manifest,
        "changedFromV2":differences,"cachedModuleManifest":dependencies,"compilerSHA256":compiler_sha,
        "compilerCommand":engine_command,"modulewrapCommand":wrapper_command,
        "runnerPath":Path(__file__).relative_to(ROOT).as_posix(),"runnerSHA256":sha(Path(__file__)),
        "boundedRunnerSHA256":sha(original_path),"driverJobs":1,"parallelBackendThreads":0,
        "engineCompileDeadlineSeconds":120,"modulewrapDeadlineSeconds":30}
    receipt=work/"build-receipt.json";log=work/"build.log"
    receipt.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8",newline="\n")
    env=dict(os.environ);env["PATH"]=str(swiftc.parent)+os.pathsep+env.get("PATH","")
    valid=False;stage="engine_compile"
    try:
        with log.open("wb") as output:
            code=original.bounded(engine_command,cwd=work,env=env,stdout=output,stderr=subprocess.STDOUT,seconds=120)
        record["engineCompileExitCode"]=code
        if code:raise RuntimeError("Diagnostic Engine compile failed")
        stage="modulewrap"
        with log.open("ab") as output:
            code=original.bounded(wrapper_command,cwd=work,env=env,stdout=output,stderr=subprocess.STDOUT,seconds=30)
        record["modulewrapExitCode"]=code
        if code:raise RuntimeError("Diagnostic modulewrap failed")
        files={}
        for relative in ["PinkhaAnyEngine.o","PinkhaAnyEngine.swiftmodule.o",
            "Modules/PinkhaAnyEngine.swiftmodule","Modules/PinkhaAnyEngine.swiftdoc",
            "Modules/PinkhaAnyEngine.swiftsourceinfo"]:
            path=work/relative
            if path.is_file():files[relative]={"path":path.relative_to(ROOT).as_posix(),"sha256":sha(path),"bytes":path.stat().st_size}
        record["compiledFiles"]=files
        valid="PinkhaAnyEngine.o" in files and "PinkhaAnyEngine.swiftmodule.o" in files
    except Exception as error:
        record["failure"]={"stage":stage,"kind":type(error).__name__}
    record.update(sourceStable=source_map()==before,
        cachedModulesStable=all(sha(ROOT/p)==h for p,h in dependencies.items()),
        copiedSourcesStable=all(sha(work/"EngineSources"/p)==h for p,h in copied_manifest.items()),
        compilerUnchanged=sha(swiftc)==compiler_sha,
        runnerUnchanged=sha(Path(__file__))==record["runnerSHA256"],
        boundedRunnerUnchanged=sha(original_path)==record["boundedRunnerSHA256"],
        buildLog=log.relative_to(ROOT).as_posix(),buildLogSHA256=sha(log),
        finishedAt=now())
    stable=all(record[k] for k in ("sourceStable","cachedModulesStable","copiedSourcesStable",
        "compilerUnchanged","runnerUnchanged","boundedRunnerUnchanged"))
    record["status"]="PASS_BUILD_ONLY" if valid and stable else "FAIL"
    receipt.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8",newline="\n")
    omit={"originalEngineSourceManifest","copiedEngineSourceManifest","cachedModuleManifest","compilerCommand","modulewrapCommand"}
    print(json.dumps({k:v for k,v in record.items() if k not in omit},indent=2))
    print(json.dumps({"receipt":receipt.relative_to(ROOT).as_posix(),"receiptSHA256":sha(receipt)}))
    if not valid:print(log.read_text(encoding="utf-8",errors="replace")[-10000:])
    return 0 if record["status"]=="PASS_BUILD_ONLY" else 1
if __name__=="__main__":sys.exit(main())
