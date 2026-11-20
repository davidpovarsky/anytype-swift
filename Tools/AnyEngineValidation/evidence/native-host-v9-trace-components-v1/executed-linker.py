#!/usr/bin/env python3
"""Link the unchanged current Host probe with the reviewed timestamp-only Engine."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,os,shutil,subprocess
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args();root=a.repo_root.resolve();out=a.output_dir.resolve()
    out.mkdir(parents=True,exist_ok=False)
    hp=root/"Tools/AnyEnginePort/run_live_provider_probe.py"
    spec=importlib.util.spec_from_file_location("host15_trace_process",hp)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    basepath=root/"build/any-engine-port/native-host-v8-components-v1/result.json"
    tracepath=root/"build/any-engine-port/http-trace-engine-v3-20261119-213528-034500/reusable-trace-engine-v3.json"
    expected_base="d837c95dc648cdd4d798c292e3b593a274269cc0e186bec35220dc7d71fc3f35"
    expected_trace="823620ea96ab33feb9e26f0013bec018a7ec55acfe1631a212eb170575de8181"
    result={"status":"FAIL","startedAt":datetime.now(timezone.utc).isoformat(),
        "scope":"Unchanged current HostProbe4/Host23/Integration35; only all plain Engine objects replaced by the reviewed timestamp-only diagnostic Engine. Original15 business assertions and original transport configuration remain unchanged.",
        "diagnosticsOnly":True,"productionBehaviorChanged":False,"requestConfigurationChanged":False,
        "timeoutsChanged":False,"watchdog":False,"sourceStable":False,"retainedInputsStable":False}
    retained={}
    def snapshot():
        v=helper.source_snapshot(root,Path(__file__))
        host=root/"Modules/PinkhaAnyHost"
        for f in [host/"Package.swift",host/"Package.resolved"]+list((host/"Sources").rglob("*.swift")):
            if f.is_file():v["files"][f.relative_to(root).as_posix()]={"sha256":helper.sha256(f),"bytes":f.stat().st_size}
        return v
    before=snapshot();helper.write_json(out/"source-before.json",before)
    result["sourceInputs"]={k:v["sha256"] for k,v in before["files"].items()}
    try:
        if helper.sha256(basepath)!=expected_base or helper.sha256(tracepath)!=expected_trace:raise RuntimeError("producer_pin")
        base=json.loads(basepath.read_text());trace=json.loads(tracepath.read_text())
        if base["status"]!="PASS_EXACT_SOURCE_COMPONENT_BUILD" or not base["sourceStable"] or not base["retainedInputsStable"]:raise RuntimeError("base_not_verified")
        for relative,digest in base["sourceInputs"].items():
            if helper.sha256(root/relative)!=digest:raise RuntimeError("base_source_changed:"+relative)
        base_before=json.loads((basepath.parent/"source-before.json").read_text())
        if before["dependencies"]!=base_before["dependencies"]:raise RuntimeError("dependency_sources_changed")
        tracebuildpath=root/trace["buildReceipt"]
        if helper.sha256(tracebuildpath)!=trace["buildReceiptSHA256"]:raise RuntimeError("trace_build_pin")
        tracebuild=json.loads(tracebuildpath.read_text())
        if tracebuild["status"]!="PASS_BUILD_ONLY" or not all(tracebuild[k] for k in ["sourceStable","cachedModulesStable","copiedSourcesStable","compilerUnchanged"]):raise RuntimeError("trace_not_verified")
        if trace["changedEngineFiles"]!=["AnyHTTPClient.swift"] or trace["originalProductionBehaviorChanges"] is not False or trace["diagnosticsOnly"] is not True:raise RuntimeError("trace_scope")
        source=root/"Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine"
        original={f.name:helper.sha256(f) for f in source.glob("*.swift")}
        if original!=trace["originalEngineSourceManifest"]:raise RuntimeError("original_engine_source_mismatch")
        copied=tracepath.parent/"EngineSources"
        if {f.name:helper.sha256(f) for f in copied.glob("*.swift")}!=trace["copiedEngineSourceManifest"]:raise RuntimeError("trace_copy_mismatch")
        patch=root/trace["patch"]
        if helper.sha256(patch)!=trace["patchSHA256"] or trace["patchSHA256"]!="9f000f982825a46a3c6ebed1e743070bb7486bd914fda44b8c4184a44160ddfc":raise RuntimeError("reviewed_patch_mismatch")
        retained.update(base["retainedInputs"]);retained.update(base["objectHashes"])
        for v in trace["compiledFiles"].values():retained[str(root/v["path"])]=v["sha256"]
        for relative,value in tracebuild["cachedModuleManifest"].items():
            if Path(relative).name not in ["Crypto.swiftmodule","CryptoBoringWrapper.swiftmodule"]:continue
            digest=value["sha256"] if isinstance(value,dict) else value
            if helper.sha256(root/relative)!=digest:raise RuntimeError("trace_crypto_abi_mismatch")
            retained[str(root/relative)]=digest
        for path,digest in retained.items():
            if helper.sha256(Path(path))!=digest:raise RuntimeError("retained_artifact_mismatch:"+path)
        cmd=list(next(step["command"] for step in base["steps"] if step["name"]=="probe-link"))
        swift=Path(cmd[0])
        if helper.sha256(swift)!=base["compilerSHA256"] or helper.sha256(swift)!=tracebuild["compilerSHA256"]:raise RuntimeError("toolchain_mismatch")
        if trace["modulewrapCommand"][trace["modulewrapCommand"].index("-target")+1]!="x86_64-unknown-windows-msvc":raise RuntimeError("target_mismatch")
        objects=[Path(x) for x in base["objectHashes"]]
        removed=[x for x in objects if "PinkhaAnyEngine.build" in x.parts]
        if len(removed)!=len(original)+1:raise RuntimeError("incomplete_engine_removal")
        replacements=[root/trace["compiledFiles"][name]["path"] for name in ["PinkhaAnyEngine.o","PinkhaAnyEngine.swiftmodule.o"]]
        linked=[x for x in objects if x not in removed]+replacements
        if len(set(linked))!=len(linked):raise RuntimeError("duplicate_object")
        response=out/"Objects.LinkFileList"
        response.write_text("\n".join(subprocess.list2cmdline([str(x)]) for x in linked)+"\n",encoding="utf-8")
        exe=out/"native-host-v9-trace-probe.exe"
        for i,value in enumerate(cmd):
            if value.startswith("@"):cmd[i]="@"+str(response)
        cmd[cmd.index("-o")+1]=str(exe)
        if "-module-cache-path" in cmd:cmd[cmd.index("-module-cache-path")+1]=str(out/"ModuleCache")
        cmd[1:1]=["-I",str(tracepath.parent/"Modules")]
        os.environ["PATH"]=str(swift.parent)+os.pathsep+str(Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Runtimes\6.3.3\usr\bin"))+os.pathsep+os.environ.get("PATH","")
        for src,name in [(Path(__file__),"executed-linker.py"),(hp,"executed-process-helper.py"),
                         (basepath,"original-host-build.json"),(tracepath,"reusable-trace-engine-v3.json"),
                         (tracebuildpath,"trace-engine-build.json"),(patch,"reviewed-trace-only.diff")]:
            shutil.copyfile(src,out/name)
        (out/"trace-engine-sources").mkdir()
        for src in copied.glob("*.swift"):shutil.copyfile(src,out/"trace-engine-sources"/src.name)
        result["retainedInputs"]=retained
        result["compilerSHA256"]=helper.sha256(swift)
        result["removedEngineObjects"]=[str(x) for x in removed]
        result["objectCount"]=len(linked)
        result["objectHashes"]={str(x):helper.sha256(x) for x in linked}
        result["originalEngineSourceManifest"]=original
        result["traceManifestSHA256"]=expected_trace
        result["originalBuildReceiptSHA256"]=expected_base
        result["unchangedProbeSourceFiles"]=base["probeSourceFiles"]
        (out/"link").mkdir()
        process=helper.run_process(cmd,root,out/"link",180)
        result["process"]=process
        if process.get("exitCode")!=0 or process.get("timedOut") or process.get("cleanupErrors") or process.get("runnerErrorType"):raise RuntimeError("link_failed")
        result["binary"]=str(exe);result["binarySHA256"]=helper.sha256(exe)
        result["status"]="PASS_EXACT_SOURCE_COMPONENT_BUILD"
    except Exception as error:
        result["errorType"]=type(error).__name__;result["errorCode"]=str(error)
    finally:
        after=snapshot();helper.write_json(out/"source-after.json",after)
        result["sourceStable"]=before["files"]==after["files"] and before["dependencies"]==after["dependencies"]
        result["retainedInputsStable"]=all(Path(k).is_file() and helper.sha256(Path(k))==v for k,v in retained.items())
        if not result["sourceStable"] or not result["retainedInputsStable"]:result["status"]="FAIL"
        result["finishedAt"]=datetime.now(timezone.utc).isoformat()
        helper.write_json(out/"result.json",result)
    print(json.dumps({k:result.get(k) for k in ["status","errorCode","sourceStable","retainedInputsStable","objectCount","binarySHA256"]}),flush=True)
    return 0 if result["status"]=="PASS_EXACT_SOURCE_COMPONENT_BUILD" else 1
if __name__=="__main__":raise SystemExit(main())
