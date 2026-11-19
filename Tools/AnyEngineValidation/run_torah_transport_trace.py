#!/usr/bin/env python3
"""One direct diagnostic run using an isolated HTTP timing/framing trace; production unchanged."""
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
    prefix=ROOT/"docs/any-engine-port/evidence/20261119"/("native-torah-direct-transport-trace-"+stamp)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    work=ROOT/"build/any-engine-port"/("torah-direct-transport-trace-"+stamp)
    work.mkdir(parents=True,exist_ok=True)
    debug=ROOT/"Modules/PinkhaAnyHost/.build/x86_64-unknown-windows-msvc/debug"
    listed=(debug/"pinkha-any-host-probe.product/Objects.LinkFileList").read_text().splitlines()
    objects=[Path(p.strip()) for p in listed if p.strip() and "PinkhaAnyHostProbe" not in p and "PinkhaAnyEngine" not in p]
    if not objects or not all(p.is_file() for p in objects):parser.error("Retained production object list unavailable")
    dependencies={p.relative_to(ROOT).as_posix():sha(p) for p in objects}
    for p in (debug/"Modules").glob("*.swiftmodule"):dependencies[p.relative_to(ROOT).as_posix()]=sha(p)
    engine_object=work/"PinkhaAnyEngine.o"
    engine_wrapper=work/"PinkhaAnyEngine.swiftmodule.o"
    (work/"objects.rsp").write_text("\n".join('"'+str(p)+'"' for p in objects+[engine_object,engine_wrapper]),encoding="utf-8")
    sources=sorted((ROOT/"Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe").glob("*.swift"))
    swiftc=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe")
    sdk=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Platforms\6.3.3\Windows.platform\Developer\SDKs\Windows.sdk")
    probe=work/"pinkha-any-host-http-trace.exe"
    copied_engine=work/"EngineSources"
    modules=work/"Modules"
    modules.mkdir()
    engine_source_root=ROOT/"Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine"
    engine_sources=[]
    for path in sorted(engine_source_root.rglob("*.swift")):
        copied=copied_engine/path.relative_to(engine_source_root)
        copied.parent.mkdir(parents=True,exist_ok=True)
        copied.write_bytes(path.read_bytes())
        engine_sources.append(copied)
    client_copy=copied_engine/"AnyHTTPClient.swift"
    if sha(client_copy)!="5da381da640730ffcb82c60cd6effc0ced56710deefe743cd2fe20d4ed0a8c57":
        raise RuntimeError("Unexpected exact production HTTP source")
    client_source=client_copy.read_text(encoding="utf-8")
    old='''        do { (data, response) = try await session.data(for: request) }
        catch { if method == "GET" { throw error }; throw AnyEngineError.writeUncertain }'''
    traced='''        let diagnosticID = UUID().uuidString
        let diagnosticStart = ProcessInfo.processInfo.systemUptime
        pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "begin", method: method,
            path: request.url?.path ?? "", start: diagnosticStart, response: nil, error: nil)
        do { (data, response) = try await session.data(for: request) }
        catch {
            pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "error", method: method,
                path: request.url?.path ?? "", start: diagnosticStart, response: nil, error: error)
            if method == "GET" { throw error }; throw AnyEngineError.writeUncertain
        }
        pinkhaDiagnosticHTTPTrace(id: diagnosticID, phase: "response", method: method,
            path: request.url?.path ?? "", start: diagnosticStart,
            response: response as? HTTPURLResponse, error: nil)'''
    if client_source.count(old)!=1:raise RuntimeError("Exact HTTP await patch not found")
    client_source=client_source.replace(old,traced)
    client_source+='''

// DIAGNOSTIC COPY ONLY: no body, query, authorization or arbitrary header values.
private func pinkhaDiagnosticHTTPTrace(
    id: String, phase: String, method: String, path: String, start: TimeInterval,
    response: HTTPURLResponse?, error: (any Error)?
) {
    var event: [String: Any] = [
        "id": id, "phase": phase, "method": method, "path": path,
        "elapsedMs": Int(max(0, ProcessInfo.processInfo.systemUptime - start) * 1000)
    ]
    if let response {
        event["status"] = response.statusCode
        var framing: [String: String] = [:]
        if let value = response.value(forHTTPHeaderField: "Content-Length") {
            framing["Content-Length"] = value.utf8.count <= 20 && !value.isEmpty &&
                value.utf8.allSatisfy({ (48...57).contains($0) }) ? value : "invalid"
        }
        if let value = response.value(forHTTPHeaderField: "Transfer-Encoding") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Transfer-Encoding"] = ["chunked", "identity", "gzip", "deflate"].contains(value) ? value : "other"
        }
        if let value = response.value(forHTTPHeaderField: "Connection") {
            let value = value.lowercased().trimmingCharacters(in: .whitespaces)
            framing["Connection"] = ["close", "keep-alive"].contains(value) ? value : "other"
        }
        event["framing"] = framing
    }
    if let error {
        let nsError = error as NSError
        event["errorDomain"] = nsError.domain == NSURLErrorDomain ? "NSURLErrorDomain" : "other"
        event["errorCode"] = nsError.code
    }
    if let data = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys]) {
        var line = Data("ANY_HTTP_TRACE ".utf8)
        line.append(data)
        line.append(Data([10]))
        FileHandle.standardError.write(line)
    }
}
'''
    client_copy.write_text(client_source,encoding="utf-8",newline="\n")
    copied_manifest={p.relative_to(work).as_posix():sha(p) for p in engine_sources}
    if any(sha(p)!=sha(engine_source_root/p.relative_to(copied_engine)) for p in engine_sources if p!=client_copy):
        raise RuntimeError("Unexpected secondary diagnostic source edit")
    # This private import cache is already warm; no shared package cache is mutated.
    module_cache=ROOT/"build/any-engine-port/inline-hanlin-components-v5/ModuleCache"
    command=[str(swiftc),"-parse-as-library","-swift-version","6","-module-name","PinkhaAnyHostProbe",
             "-j1","-whole-module-optimization","-num-threads","1","-Onone","-gnone",
             "-I",str(modules),"-I",str(debug/"Modules"),"-module-cache-path",str(module_cache),
             "-sdk",str(sdk),"-use-ld=lld","-Xlinker","/threads:1","-Xlinker","/debug:none",
             "-Xlinker","/incremental:no"]
    for module in ("swift-crypto/Sources/CCryptoBoringSSLShims/include","swift-crypto/Sources/CCryptoBoringSSL/include"):
        path=ROOT/"Modules/PinkhaAnyHost/.build/checkouts"/module
        command+=["-Xcc","-fmodule-map-file="+str(path/"module.modulemap"),"-Xcc","-I"+str(path)]
    engine_command=[str(swiftc),"-parse-as-library","-swift-version","6","-module-name","PinkhaAnyEngine",
        "-j1","-whole-module-optimization","-num-threads","0","-Onone","-gnone",
        "-I",str(debug/"Modules"),"-module-cache-path",str(module_cache),"-sdk",str(sdk),
        "-emit-object","-emit-module","-emit-module-path",str(modules/"PinkhaAnyEngine.swiftmodule")]
    for module in ("swift-crypto/Sources/CCryptoBoringSSLShims/include","swift-crypto/Sources/CCryptoBoringSSL/include"):
        path=ROOT/"Modules/PinkhaAnyHost/.build/checkouts"/module
        engine_command+=["-Xcc","-fmodule-map-file="+str(path/"module.modulemap"),"-Xcc","-I"+str(path)]
    engine_command += [str(p) for p in engine_sources]+["-o",str(engine_object)]
    wrapper_command=[str(swiftc),"-modulewrap",str(modules/"PinkhaAnyEngine.swiftmodule"),
        "-target","x86_64-unknown-windows-msvc","-o",str(engine_wrapper)]
    command += [str(p) for p in sources]+["@"+str(work/"objects.rsp"),"-o",str(probe)]
    record={"schemaVersion":1,"status":"RUNNING","startedAt":now(),"scope":"direct_native_t5_with_isolated_http_trace",
            "businessScope":original.SCOPE,"sourceManifest":source,"changedSourcesFromBaseline":changed,
            "baselineBuildReceiptSHA256":sha(args.baseline),"productionContractsChanged":False,
            "cliInstrumentationOnly":False,"isolatedEngineTraceCopy":True,"expectedCount":19,"productionTimeoutsChanged":False,
            "copiedEngineSourceManifest":copied_manifest,"traceMutation":"fixed timing, path and allowlisted framing diagnostics only",
            "cachedDependencyManifest":dependencies,"cachedDependencyObjectCount":len(objects),
            "nativeBinarySHA256":original.NATIVE_SHA,"nativeSourceManifestSHA256":original.MANIFEST_SHA,
            "runnerSHA256":sha(Path(__file__)),"compileCommand":command,"engineCompileCommand":engine_command,
            "modulewrapCommand":wrapper_command,"compileDeadlineSeconds":120,
            "compilerThreads":1,"debugInformationRequested":False,
            "protectedAppleJournal":False,"engineProcessRestart":False,"uiInteraction":False,"liveProviderTransport":False}
    receipt=prefix.with_suffix(".json");receipt.write_text(json.dumps(record,indent=2)+"\n")
    env=dict(os.environ);env["PATH"]=str(swiftc.parent)+os.pathsep+env.get("PATH","")
    build_log=prefix.with_suffix(".build.log");stdout_path=prefix.with_suffix(".stdout.log");stderr_path=prefix.with_suffix(".stderr.log")
    control_path=ROOT/"Tools/AnyEngineValidation/run_existing_native_torah_probe.py"
    control_spec=importlib.util.spec_from_file_location("owned_t5_control",control_path)
    control=importlib.util.module_from_spec(control_spec);control_spec.loader.exec_module(control)
    record["ownedProcessRunnerSHA256"]=sha(control_path)
    valid=False;stage="engine_compile"
    try:
        with build_log.open("wb") as out:
            code=original.bounded(engine_command,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT,seconds=120)
        record["engineCompileExitCode"]=code
        if code:raise RuntimeError("Isolated Engine compile failed")
        stage="engine_modulewrap"
        with build_log.open("ab") as out:
            code=original.bounded(wrapper_command,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT,seconds=30)
        record["engineModulewrapExitCode"]=code
        if code:raise RuntimeError("Isolated Engine modulewrap failed")
        stage="probe_compile_link"
        with build_log.open("ab") as out:
            code=original.bounded(command,cwd=work,env=env,stdout=out,stderr=subprocess.STDOUT,seconds=120)
        record["compileExitCode"]=code
        if code:raise RuntimeError("Diagnostic probe compile/link failed")
        record["probeSHA256"]=sha(probe)
        stage="native_health"
        with urllib.request.urlopen(fixture["endpoint"]+"/v1/health",timeout=10) as response:health=json.load(response)
        if health.get("status")!="ok" or health.get("account")!=fixture["accountId"]:raise RuntimeError("Assigned fixture account mismatch")
        record["engineStartedAt"]=health.get("startedAt")
        stage="direct_native_probe"
        run=[str(probe),fixture["endpoint"],fixture["spaceId"],fixture["accountId"],"--torah-workflow","--allow-disposable-writes"]
        with stdout_path.open("wb") as out,stderr_path.open("wb") as err:
            code=control.run_owned_probe(run,env=env,stdout=out,stderr=err,record=record)
        record["probeExitCode"]=code
        lines=stdout_path.read_text(encoding="utf-8").strip().splitlines()
        result=json.loads(lines[-1]) if lines else {}
        record["result"]=result
        progress=[line for line in stderr_path.read_text(encoding="utf-8",errors="replace").splitlines() if line.startswith("T5_PROGRESS ")]
        record["progress"]=progress
        trace=[]
        for line in stderr_path.read_text(encoding="utf-8",errors="strict").splitlines():
            if line.startswith("ANY_HTTP_TRACE "):
                trace.append(json.loads(line[len("ANY_HTTP_TRACE "):]))
        trace_path=prefix.with_suffix(".requests.jsonl")
        trace_path.write_text("".join(json.dumps(item,sort_keys=True)+"\n" for item in trace),encoding="utf-8")
        record["tracePath"]=trace_path.relative_to(ROOT).as_posix()
        record["traceSHA256"]=sha(trace_path)
        record["traceEventCount"]=len(trace)
        record["traceRequestCount"]=sum(item.get("phase")=="begin" for item in trace)
        record["traceErrors"]=[item for item in trace if item.get("phase")=="error"]
        finished_ids={item["id"] for item in trace if item.get("phase") in ("response","error")}
        record["traceUnfinished"]=[item for item in trace if item.get("phase")=="begin" and item["id"] not in finished_ids]
        original_runtime=ROOT/"docs/any-engine-port/evidence/20261119/native-torah-existing-20261119-210154-834308.json"
        original_dlls=json.loads(original_runtime.read_text()).get("loadedRuntimeModules",{}).get("modules",[])
        current_dlls=record.get("loadedRuntimeModules",{}).get("modules",[])
        record["runtimeDLLsMatchOriginalControl"]=bool(original_dlls) and {
            Path(item["path"]).name.lower():item["sha256"] for item in original_dlls
        }=={Path(item["path"]).name.lower():item["sha256"] for item in current_dlls}
        valid=(code==0 and result.get("status")=="PASS" and result.get("scope")==original.SCOPE and
               result.get("count")==19 and len(set(result.get("checks",[])))==19 and
               result.get("protectedAppleJournal") is False and result.get("engineProcessRestart") is False and len(trace)>0 and not record["traceUnfinished"])
    except Exception as error:
        record["failure"]={"kind":type(error).__name__,"stage":stage}
    for name,path in (("buildLog",build_log),("stdout",stdout_path),("stderr",stderr_path)):
        if path.is_file():record[name]=path.relative_to(ROOT).as_posix();record[name+"SHA256"]=sha(path)
    record.update(sourceStable=source==original.manifest(),
                  cachedDependenciesStable=all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in dependencies.items()),
                  nativeBinaryUnchanged=sha(args.native_binary)==original.NATIVE_SHA,
                  nativeManifestUnchanged=sha(args.native_manifest)==original.MANIFEST_SHA,
                  copiedEngineSourcesStable=all(sha(work/p)==h for p,h in copied_manifest.items()),
                  ownedProcessRunnerUnchanged=sha(control_path)==record["ownedProcessRunnerSHA256"],
                  finishedAt=now())
    stable=all(record[k] for k in ("sourceStable","cachedDependenciesStable","nativeBinaryUnchanged","nativeManifestUnchanged","copiedEngineSourcesStable","ownedProcessRunnerUnchanged"))
    record["status"]="PASS" if valid and stable else "FAIL"
    receipt.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in ("sourceManifest","cachedDependencyManifest","copiedEngineSourceManifest","compileCommand","engineCompileCommand","modulewrapCommand")},indent=2))
    if record.get("compileExitCode")!=0 and build_log.is_file():print(build_log.read_text(errors="replace")[-12000:])
    print(json.dumps({"receipt":receipt.relative_to(ROOT).as_posix(),"probe":str(probe)}))
    return 0 if record["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
