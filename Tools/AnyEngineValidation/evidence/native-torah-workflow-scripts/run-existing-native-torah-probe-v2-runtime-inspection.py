#!/usr/bin/env python3
"""Run the already source-bound native T5 probe with the exact original19 assertions."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, ctypes, hashlib, importlib.util, json, os, subprocess, sys, time, urllib.request

ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def runtime_modules(process):
    """Inspect only the newly spawned owned process; never enumerate another process."""
    try:
        psapi=ctypes.WinDLL("psapi",use_last_error=True)
        handle=ctypes.c_void_p(int(process._handle))
        modules=(ctypes.c_void_p*2048)()
        needed=ctypes.c_ulong()
        enum=psapi.EnumProcessModulesEx
        enum.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_ulong]
        enum.restype=ctypes.c_int
        filename=psapi.GetModuleFileNameExW
        filename.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong]
        filename.restype=ctypes.c_ulong
        if not enum(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3):
            return {"status":"unavailable","win32Error":ctypes.get_last_error()}
        if needed.value>ctypes.sizeof(modules):return {"status":"unavailable","reason":"module_bound"}
        result=[]
        for item in modules[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
            buffer=ctypes.create_unicode_buffer(32768)
            if filename(handle,item,buffer,len(buffer)):
                path=Path(buffer.value);name=path.name.lower()
                if "foundation" in name or "swiftcore" in name:
                    result.append({"path":str(path),"sha256":sha(path),"bytes":path.stat().st_size})
        return {"status":"captured","modules":sorted(result,key=lambda item:item["path"].lower())}
    except Exception as error:return {"status":"unavailable","errorKind":type(error).__name__}

def run_owned_probe(command, *, env, stdout, stderr, record):
    started=time.monotonic()
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        time.sleep(0.25)
        record["loadedRuntimeModules"]=runtime_modules(process)
        return process.wait(timeout=max(0.01,300-(time.monotonic()-started)))
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        process.wait(timeout=30)
        raise

def runtime_candidates(probe, env):
    directories={probe.parent,Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin")}
    directories.update(Path(part) for part in env.get("PATH","").split(os.pathsep) if part)
    result=[]
    for directory in sorted(directories,key=str):
        if not directory.is_dir():continue
        for path in sorted(set(directory.glob("*Foundation*.dll"))|set(directory.glob("*swiftCore*.dll"))):
            if path.is_file():result.append({"path":str(path),"sha256":sha(path),"bytes":path.stat().st_size})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--fixture",type=Path,required=True)
    parser.add_argument("--probe",type=Path,required=True)
    parser.add_argument("--native-binary",type=Path,required=True)
    parser.add_argument("--native-manifest",type=Path,required=True)
    parser.add_argument("--allow-disposable-writes",action="store_true")
    parser.add_argument("--allow-probe-progress-source",action="store_true",
        help="Allow only the audited eight stderr progress lines in the CLI source; execute the unchanged baseline binary")
    args=parser.parse_args()
    if not args.allow_disposable_writes:parser.error("Owned disposable fixture authorization is required")
    spec=importlib.util.spec_from_file_location("native_torah_original_runner",ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py")
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    baseline=json.loads(args.baseline.read_text())
    fixture=json.loads(args.fixture.read_text())
    if baseline.get("sourceStable") is not True or baseline.get("buildExitCode")!=0:parser.error("Baseline did not bind a successful build")
    if sha(args.probe)!=baseline["probeSHA256"]:parser.error("Probe binary differs from the baseline successful build")
    current_source=original.manifest()
    changed=[path for path in sorted(set(current_source)|set(baseline["sourceManifest"]))
        if current_source.get(path)!=baseline["sourceManifest"].get(path)]
    progress_path="Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/TorahWorkflowProbe.swift"
    if changed:
        if not(args.allow_probe_progress_source and changed==[progress_path] and
               current_source[progress_path]=="7e065223f258ff5081dfba5d3aee96d1c9f0ff5de99f5ca8eb74b1222be6961f" and
               baseline["sourceManifest"][progress_path]=="1e1ad7719d21c64659855cf7881d94c61fd6438d71a1a205bda010ddbcf10bb3"):
            parser.error("Production source differs from the existing built probe outside the audited CLI-only progress lines")
    if sha(args.native_binary)!=original.NATIVE_SHA or sha(args.native_manifest)!=original.MANIFEST_SHA:parser.error("Native binary/source manifest mismatch")
    if fixture.get("status")!="READY_OWNED_NATIVE_V7_FIXTURE" or fixture["endpoint"]!="http://127.0.0.1:60663":parser.error("This rerun is confined to the assigned disposable60663 fixture")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    prefix=ROOT/"docs/any-engine-port/evidence/20261119"/("native-torah-existing-"+stamp)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    record={"schemaVersion":1,"status":"RUNNING","startedAt":datetime.now(timezone.utc).isoformat(),
            "scope":original.SCOPE,"buildPerformed":False,"baselineBuildReceipt":args.baseline.relative_to(ROOT).as_posix(),
            "baselineBuildReceiptSHA256":sha(args.baseline),"sourceManifest":current_source,
            "binarySourceManifest":baseline["sourceManifest"],"changedSourcesFromBinary":changed,
            "productionContractsMatchBinary":True,"cliProgressNotIncludedInBinary":bool(changed),
            "probeSHA256":sha(args.probe),"nativeBinarySHA256":original.NATIVE_SHA,
            "nativeSourceManifestSHA256":original.MANIFEST_SHA,"runnerSHA256":sha(Path(__file__)),
            "originalRunnerSHA256":sha(ROOT/"Tools/AnyEngineValidation/run_native_torah_probe.py"),
            "fixtureSHA256":sha(args.fixture),"protectedAppleJournal":False,"engineProcessRestart":False,
            "uiInteraction":False,"liveProviderTransport":False,"expectedCount":19}
    output=prefix.with_suffix(".json")
    output.write_text(json.dumps(record,indent=2)+"\n")
    env=dict(os.environ)
    env["PATH"]=r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin"+os.pathsep+env.get("PATH","")
    record["runtimeCandidates"]=runtime_candidates(args.probe,env)
    stdout_path=prefix.with_suffix(".stdout.log");stderr_path=prefix.with_suffix(".stderr.log")
    valid=False;stage="health"
    try:
        with urllib.request.urlopen(fixture["endpoint"]+"/v1/health",timeout=10) as response:health=json.load(response)
        if health.get("status")!="ok" or health.get("account")!=fixture["accountId"]:raise RuntimeError("Assigned fixture account mismatch")
        record["engineStartedAt"]=health.get("startedAt")
        record["health"]={key:health[key] for key in ("status","version","buildCommit") if key in health}
        stage="existing_probe"
        command=[str(args.probe),fixture["endpoint"],fixture["spaceId"],fixture["accountId"],"--torah-workflow","--allow-disposable-writes"]
        record["command"]=command
        with stdout_path.open("wb") as stdout,stderr_path.open("wb") as stderr:
            code=run_owned_probe(command,env=env,stdout=stdout,stderr=stderr,record=record)
        record["probeExitCode"]=code
        lines=stdout_path.read_text(encoding="utf-8").strip().splitlines()
        result=json.loads(lines[-1]) if lines else {}
        record["result"]=result
        valid=(code==0 and result.get("status")=="PASS" and result.get("scope")==original.SCOPE and
               result.get("protectedAppleJournal") is False and result.get("engineProcessRestart") is False and
               result.get("count")==19 and len(result.get("checks",[]))==19 and len(set(result["checks"]))==19)
    except Exception as error:
        record["failure"]={"kind":type(error).__name__,"stage":stage}
    for name,path in (("stdout",stdout_path),("stderr",stderr_path)):
        if path.is_file():
            record[name]=path.relative_to(ROOT).as_posix();record[name+"SHA256"]=sha(path)
    record.update(sourceStable=original.manifest()==current_source,
                  nativeBinaryUnchanged=sha(args.native_binary)==original.NATIVE_SHA,
                  nativeManifestUnchanged=sha(args.native_manifest)==original.MANIFEST_SHA,
                  probeUnchanged=sha(args.probe)==record["probeSHA256"],
                  runnerUnchanged=sha(Path(__file__))==record["runnerSHA256"],
                  finishedAt=datetime.now(timezone.utc).isoformat())
    stable=all(record[k] for k in ("sourceStable","nativeBinaryUnchanged","nativeManifestUnchanged","probeUnchanged","runnerUnchanged"))
    record["status"]="PASS" if valid and stable else "FAIL"
    output.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:v for k,v in record.items() if k not in ("sourceManifest","binarySourceManifest","command","runtimeCandidates")},indent=2))
    print(json.dumps({"receipt":output.relative_to(ROOT).as_posix()}))
    return 0 if record["status"]=="PASS" else 1

if __name__=="__main__":sys.exit(main())
