#!/usr/bin/env python3
"""One failed-method-only continuation; the original four-control route stays fixed."""
import argparse,hashlib,importlib.util,json,os,pathlib,shutil,signal,stat,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
PARENT=HERE.parent
REPO=PARENT.parents[2]
OUT=pathlib.Path("/mnt/development/projects/evidence/native-owned-snapshot-20261123/failed-shutdown-attempt1")
ORIGINAL=OUT.parent/"attempt1"
METHOD="TestNativeOwnedSnapshotShutdownAndCanceledAcquire"
BASE_HASH="9fbd3a53f10caf7869f0a81ce69517c1d546747bea170c9ca9031a6c8e0b70c6"
ORIGINAL_EXECUTE_HASH="b0d8a59ab46b66125e4a903ee498743db319497000b98fbf9724f448a1945d0d"
NATIVE_SHA="ba965ac243c6501a1a7083ce0e07d3557650db00"
def require(ok,reason):
    if not ok:raise RuntimeError(reason)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_base():
    p=PARENT/"run.py";require(digest(p)==BASE_HASH,"original_controller_source_changed")
    spec=importlib.util.spec_from_file_location("native_owned_original_controller",p)
    require(spec is not None and spec.loader is not None,"original_controller_spec")
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    require(pathlib.Path(module.__file__).resolve()==p and module.METHODS[-1]==METHOD,"original_controller_origin")
    return module
def loaded(base):
    result={}
    for name,module in sorted(sys.modules.items()):
        file=getattr(module,"__file__",None)
        if not file:continue
        p=pathlib.Path(file)
        if p.suffix==".pyc" and p.with_suffix(".py").is_file():p=p.with_suffix(".py")
        if p.is_file():
            p=p.resolve();result[name]={"path":str(p),**base.physical(p)}
            if p.is_relative_to(pathlib.Path("/mnt/development/projects/worktrees")):
                require(p in (HERE/"run.py",PARENT/"run.py",PARENT/"audit.py"),"unexpected_repository_module")
    return result
def sources(base,manifest):
    result=base.source_snapshot(manifest)
    p=HERE/"source.json";rel=str(p.relative_to(REPO));current=base.physical(p)
    require(hashlib.sha256(base.git(REPO,"show","HEAD:"+rel)).hexdigest()==current["sha256"],"failed_manifest_physical_git_mismatch")
    result["controller"][rel]=current
    return result
def dependencies(base,manifest):
    p=HERE/"dependency-inputs.json"
    require(digest(p)==manifest["dependency_inputs_sha256"],"failed_scope_dependency_manifest_changed")
    rows=json.loads(p.read_bytes());result={}
    for name,row in rows.items():
        q=pathlib.Path(name)
        require(q.is_absolute() and any(q.is_relative_to(root) for root in (base.NATIVE,base.MODCACHE,base.GO.parent.parent,base.BUILDCACHE)),"dependency_outside_fixed_roots")
        result[name]=base.exact_file(q,row)
    require(len(result)==4189 and all(str(base.NATIVE/rel) in result for rel in manifest["native_source_inputs"] if rel.endswith(".go")),"failed_scope_dependency_coverage")
    return result
def inspect_one(audit,path):
    result=audit.inspect_events(path)
    require(result["starts"]==[METHOD] and result["passes"]==[METHOD] and set(result["observations"])=={METHOD} and not result["receipts"],"exact_failed_method_only")
    require(not any(x.get("Action") in ("fail","skip") for x in result["events"]),"failed_method_actual_failure")
    require(sum(x.get("Action")=="pass" and "Test" not in x for x in result["events"])==1,"actual_package_terminal_pass")
    stream=""
    for line in path.read_text().splitlines():
        event=audit.strict(line)
        if event.get("Test")==METHOD:stream+=event.get("Output","")
    prefix="NATIVE_OWNED_SHUTDOWN_FD_COUNTS "
    observations=[audit.strict(line[len(prefix):]) for line in stream.splitlines() if line.startswith(prefix)]
    require(len(observations)==1,"one_actual_fd_observation")
    fds=observations[0]
    require(type(fds) is dict and set(fds)=={"baseline","inflight","after_rejected_open","after_original_close"} and all(type(x) is int and x>=0 for x in fds.values()),"fd_observation_shape")
    counts=result["observations"][METHOD]["Counts"]
    require(fds["inflight"]>fds["baseline"]>0 and fds["after_original_close"]==0 and counts["baseline_native_db_fds"]==fds["baseline"] and counts["observed_inflight_native_db_fds"]==fds["inflight"],"actual_fd_lifetime_outcomes")
    return {"events":result["events"],"observation":result["observations"][METHOD],"fd_counts":fds,"actual_named_starts":result["starts"],"actual_named_passes":result["passes"],"original_four_method_aggregate_qualified":False}
def main():
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=("build","execute"));args=parser.parse_args()
    base=load_base()
    require(base.free()>=(base.START_FREE if args.stage=="build" else base.STOP_FREE),"initial_capacity_guard")
    manifest=json.loads((HERE/"source.json").read_bytes())
    require(manifest["kind"]=="native-owned-shutdown-failed-method-continuation-v1" and manifest["native_source_sha"]==NATIVE_SHA and manifest["selected_top_level_methods"]==[METHOD] and manifest["old_methods_selected"]==0 and manifest["retained_named_methods"]==base.METHODS[:3],"fixed_failed_scope")
    require(digest(ORIGINAL/"execute.json")==ORIGINAL_EXECUTE_HASH,"original_failed_execution_changed")
    prior=json.loads((ORIGINAL/"execute.json").read_bytes())
    require(prior["status"]=="FAILED" and prior["actual_named_passes"]==base.METHODS[:3] and prior["actual_named_starts"]==base.METHODS,"retained_actual_three_passes")
    if args.stage=="build":
        require(not OUT.exists(),"unused_failed_scope_attempt_required")
        base.private_dir(OUT.parent);OUT.mkdir(mode=0o700)
        for rel in ("private","private/fixtures","tmp","products"):(OUT/rel).mkdir(mode=0o700)
    for p in (OUT,OUT/"private",OUT/"private/fixtures"):base.private_dir(p)
    receipt=OUT/(args.stage+".json");require(not receipt.exists(),"original_failed_stage_never_replaced")
    env=dict(os.environ,GOMAXPROCS="1",CGO_ENABLED="1",GOPROXY="off",GOSUMDB="off",GOTOOLCHAIN="local",GOFLAGS="",GOEXPERIMENT="",GOWORK="off",
             GOPATH=str(base.GOPATH),GOMODCACHE=str(base.MODCACHE),GOCACHE=str(base.BUILDCACHE),TMPDIR=str(OUT/"tmp"),GOTMPDIR=str(OUT/"tmp"),PINKHA_NATIVE_OWNED_SNAPSHOT_PRIVATE_ROOT=str(OUT/"private/fixtures"))
    result={"stage":args.stage,"status":"FAILED","started":base.now(),"native_source_sha":NATIVE_SHA,
            "controller_source_sha":base.git(REPO,"rev-parse","HEAD").decode().strip(),"manifest_sha256":digest(HERE/"source.json"),
            "controller_sha256":digest(HERE/"run.py"),"base_controller_sha256":BASE_HASH,"original_failed_execute_sha256":ORIGINAL_EXECUTE_HASH,
            "retained_named_passes":base.METHODS[:3],"retained_methods_reexecuted":0,"actual_named_starts":[],"actual_named_passes":[],
            "command":None,"primary_error":None,"final_errors":[],"accountSessionACLAuthorized":False,"hasNativeSourceAdmission":False,
            "permitsDestinationWrites":False,"semanticIdentityCensusComplete":False,"filePayloadCoverageComplete":False}
    before=None;deps=None;tools=None;loaded_before=None
    handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
    for s in handlers:signal.signal(s,base.interrupted)
    try:
        before=sources(base,manifest);base.save(OUT/(args.stage+"-source-before.json"),before)
        deps=dependencies(base,manifest);base.save(OUT/(args.stage+"-dependencies-before.json"),deps)
        tools=base.tool_snapshot(manifest);base.save(OUT/(args.stage+"-tools-before.json"),tools)
        audit=base.load_auditor(manifest);loaded_before=loaded(base);base.save(OUT/(args.stage+"-loaded-before.json"),loaded_before)
        binary=OUT/"products/native-owned-snapshot.test"
        if args.stage=="build":
            require(not binary.exists(),"unused_failed_scope_binary")
            result["environment"]={k:env[k] for k in ("GOMAXPROCS","CGO_ENABLED","GOPROXY","GOSUMDB","GOTOOLCHAIN","GOFLAGS","GOEXPERIMENT","GOWORK","GOPATH","GOMODCACHE","GOCACHE","TMPDIR","GOTMPDIR")}
            result["command"]=base.command([str(base.GO),"test","-mod=readonly","-c","-p=1","-tags=pinkha_localstore_witness","-o",str(binary),manifest["package"]],base.NATIVE,env,OUT/"private/build-original",900)
            require(result["command"]["status"]=="PASS","failed_scope_build_original_failed")
            result["binary"]=base.physical(binary)
            info=subprocess.check_output([str(base.GO),"version","-m",str(binary)],env=env,timeout=30)
            base.original(OUT/"binary-buildinfo-original.txt",info);result["buildinfo_sha256"]=digest(OUT/"binary-buildinfo-original.txt")
            result["status"]="BUILD_PASS_FAILED_METHOD_NOT_RUN"
        else:
            build=json.loads((OUT/"build.json").read_bytes())
            require(build["status"]=="BUILD_PASS_FAILED_METHOD_NOT_RUN" and build["binary"]==base.physical(binary),"qualified_failed_scope_binary_changed")
            for key in ("manifest_sha256","controller_sha256","native_source_sha","controller_source_sha"):
                require(build[key]==result[key],"failed_scope_build_execution_origin_changed")
            result["command"]=base.command([str(base.GO),"tool","test2json","-t","-p",base.PACKAGE,str(binary),"-test.v=test2json","-test.run=^"+METHOD+"$","-test.timeout=90s","-test.count=1"],base.NATIVE,env,OUT/"private/execution-original",120)
            inspected=audit.inspect_events(OUT/"private/execution-original.stdout")
            result["actual_named_starts"]=inspected["starts"];result["actual_named_passes"]=inspected["passes"]
            base.save(OUT/"safe-events.json",inspected["events"])
            require(result["command"]["status"]=="PASS","failed_method_original_failed")
            qualified=inspect_one(audit,OUT/"private/execution-original.stdout");base.save(OUT/"safe-shutdown-observation.json",qualified)
            require(not list((OUT/"private/fixtures").glob("native-case-*/*.witness.bin")),"old_witness_scope_reexecuted")
            result["fd_counts"]=qualified["fd_counts"];result["binary"]=base.physical(binary)
            require(result["binary"]==build["binary"],"executed_failed_scope_binary_changed")
            result["status"]="PASS_FAILED_SHUTDOWN_METHOD_ONLY"
    except BaseException as error:
        result["status"]="FAILED";result["primary_error"]={"type":type(error).__name__,"message":str(error)}
    finally:
        for scope,reader,original in (("source",lambda:sources(base,manifest),before),("dependencies",lambda:dependencies(base,manifest),deps),("tools",lambda:base.tool_snapshot(manifest),tools)):
            try:
                final=reader();base.save(OUT/(args.stage+"-"+scope+"-after.json"),final);require(original is not None and final==original,scope+"_integrity_changed")
            except BaseException as error:result["final_errors"].append({"scope":scope,"type":type(error).__name__,"message":str(error)})
        try:
            final=loaded(base);base.save(OUT/(args.stage+"-loaded-after.json"),final)
            require(loaded_before is not None and all(final.get(k)==v for k,v in loaded_before.items()),"loaded_source_integrity_changed")
            result["loaded_before_count"]=len(loaded_before);result["loaded_after_count"]=len(final)
        except BaseException as error:result["final_errors"].append({"scope":"loaded","type":type(error).__name__,"message":str(error)})
        for s,handler in handlers.items():signal.signal(s,handler)
        result["free_bytes_final"]=base.free();result["final_capacity_admitted"]=result["free_bytes_final"]>=base.MIN_FREE
        if not result["final_capacity_admitted"]:result["final_errors"].append({"scope":"capacity","type":"ReserveBreach","free_bytes":result["free_bytes_final"],"minimum_free_bytes":base.MIN_FREE})
        if result["final_errors"]:result["status"]="FAILED"
        result["finished"]=base.now();base.save(receipt,result)
        print(json.dumps({"stage":args.stage,"status":result["status"],"receipt":str(receipt),"sha256":digest(receipt),"actual_named_passes":len(result["actual_named_passes"]),"free_bytes":result["free_bytes_final"]}))
    return 0 if result["status"]!="FAILED" else 1
if __name__=="__main__":raise SystemExit(main())
