#!/usr/bin/env python3
"""One offline build; exactly four new native owner/lease controls once."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE=pathlib.Path(__file__).resolve().parent
REPO=HERE.parents[2]
NATIVE=pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-native-owned-snapshot-20261123")
EVIDENCE=pathlib.Path("/mnt/development/projects/evidence/native-owned-snapshot-20261123")
PARENT="35c169e7a39e3dafc0a1281f56a1fe37fce57533"
GO=pathlib.Path("/mnt/development/toolchains/go1.27.4/go/bin/go")
MODCACHE=pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache/go-mod")
BUILDCACHE=pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-build-glibc")
GOPATH=pathlib.Path("/mnt/development/projects/diagnostics/inline-http-20261123/cache/go-path")
START_FREE=2_950_000_000
STOP_FREE=2_600_000_000
MIN_FREE=2_500_000_000
METHODS=[
    "TestNativeOwnedSnapshotBindsActualServiceHandle",
    "TestNativeOwnedSnapshotCloseRevokesAndDrains",
    "TestNativeOwnedSnapshotDeletePreservesLeaseBoundary",
    "TestNativeOwnedSnapshotShutdownAndCanceledAcquire",
]
PACKAGE="github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
CURRENT_CHILD=None

def require(ok,reason):
    if not ok:raise RuntimeError(reason)
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def free():return shutil.disk_usage("/mnt/development").free
def save(path,value):
    with path.open("x") as f:
        os.chmod(path,0o600)
        json.dump(value,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
def original(path,raw):
    with path.open("xb") as f:
        os.chmod(path,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],timeout=30)
def physical(path):
    st=path.lstat()
    require(stat.S_ISREG(st.st_mode) and not path.is_symlink(),"source_not_regular")
    return {"sha256":sha(path),"bytes":st.st_size,"mode":stat.S_IMODE(st.st_mode)}
def private_dir(path):
    st=path.lstat()
    require(stat.S_ISDIR(st.st_mode) and not path.is_symlink() and stat.S_IMODE(st.st_mode) in (0o700,0o2700),"private_directory_boundary")
def exact_file(path,row):
    observed=physical(path)
    require(observed==row,"frozen_source_bytes_mode_or_size_changed")
    return observed
def loaded():
    result={}
    for name,module in sorted(sys.modules.items()):
        file=getattr(module,"__file__",None)
        if not file:continue
        p=pathlib.Path(file)
        if p.suffix==".pyc" and p.with_suffix(".py").is_file():p=p.with_suffix(".py")
        if p.is_file():
            p=p.resolve();result[name]={"path":str(p),**physical(p)}
            if p.is_relative_to(pathlib.Path("/mnt/development/projects/worktrees")):
                require(p in (HERE/"run.py",HERE/"audit.py"),"unexpected_repository_module_loaded")
    return result
def source_snapshot(manifest):
    require(git(NATIVE,"rev-parse","HEAD").decode().strip()==manifest["native_source_sha"],"native_commit_changed")
    require(not git(NATIVE,"status","--porcelain").strip(),"native_worktree_dirty")
    require(git(NATIVE,"merge-base","HEAD",PARENT).decode().strip()==PARENT,"native_parent_changed")
    require(git(NATIVE,"diff","--name-only",PARENT,"HEAD").decode().splitlines()==sorted(manifest["authored_native"]),"native_change_scope_changed")
    require(not git(REPO,"status","--porcelain").strip(),"controller_worktree_dirty")
    require(git(REPO,"merge-base","HEAD",manifest["controller_base_sha"]).decode().strip()==manifest["controller_base_sha"],"controller_base_changed")
    native={}
    for rel,row in manifest["native_source_inputs"].items():
        p=NATIVE/rel;native[rel]=exact_file(p,row)
        require(hashlib.sha256(git(NATIVE,"show","HEAD:"+rel)).hexdigest()==row["sha256"],"native_physical_git_mismatch")
    for rel,expected in manifest["retained_native_original_sha256"].items():
        require(native[rel]["sha256"]==expected and hashlib.sha256(git(NATIVE,"show",PARENT+":"+rel)).hexdigest()==expected,"retained_native_source_changed")
    controller={}
    for rel,row in manifest["controller_inputs"].items():
        p=REPO/rel;controller[rel]=exact_file(p,row)
        require(hashlib.sha256(git(REPO,"show","HEAD:"+rel)).hexdigest()==row["sha256"],"controller_physical_git_mismatch")
    source_rel=str((HERE/"source.json").relative_to(REPO))
    controller[source_rel]=physical(HERE/"source.json")
    require(hashlib.sha256(git(REPO,"show","HEAD:"+source_rel)).hexdigest()==controller[source_rel]["sha256"],"source_manifest_git_mismatch")
    require(str(HERE/"run.py") in (str(REPO/rel) for rel in controller),"controller_not_bound")
    return {"native":native,"controller":controller,
            "native_head":manifest["native_source_sha"],"controller_head":git(REPO,"rev-parse","HEAD").decode().strip()}
def dependency_snapshot(manifest):
    path=HERE/"dependency-inputs.json"
    require(sha(path)==manifest["dependency_inputs_sha256"],"fixed_dependency_manifest_changed")
    expected=json.loads(path.read_text());current={}
    for name,row in expected.items():
        p=pathlib.Path(name)
        require(p.is_absolute() and any(p.is_relative_to(root) for root in (NATIVE,MODCACHE,GO.parent.parent,BUILDCACHE)),"dependency_outside_pinned_roots")
        current[name]=exact_file(p,row)
    require(all(str(NATIVE/rel) in current for rel in manifest["native_source_inputs"] if rel.endswith(".go")),"compiled_native_or_fixture_source_missing")
    return current
def tool_snapshot(manifest):
    result={}
    for name,row in manifest["tool_inputs"].items():
        result[name]=exact_file(pathlib.Path(name),row)
    return result
def load_auditor(manifest):
    path=HERE/"audit.py";rel=str(path.relative_to(REPO))
    exact_file(path,manifest["controller_inputs"][rel])
    spec=importlib.util.spec_from_file_location("native_owned_control_audit",path)
    require(spec is not None and spec.loader is not None,"audit_module_spec")
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    require(pathlib.Path(module.__file__).resolve()==path and module.METHODS==METHODS and module.PACKAGE==PACKAGE,"audit_origin_and_selection")
    return module
def stop_owned(child,record):
    if child.poll() is not None:return
    try:os.killpg(child.pid,signal.SIGTERM);record["term_sent"]=True
    except ProcessLookupError:record["term_sent"]=False
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:os.killpg(child.pid,signal.SIGKILL);record["kill_sent"]=True
        except ProcessLookupError:record["kill_sent"]=False
        child.wait(timeout=5)
def interrupted(signum,_frame):
    raise InterruptedError("owned_controller_signal_"+str(signum))
def command(argv,cwd,env,prefix,timeout):
    global CURRENT_CHILD
    record={"argv":argv,"cwd":str(cwd),"started":now(),"timeout_seconds":timeout,"free_before":free(),"status":"FAILED",
            "primary_error":None,"cleanup_error":None,"interruption":None,"owned_group_absent":False}
    require(record["free_before"]>=STOP_FREE,"insufficient_capacity_before_owned_command")
    child=None;start=time.monotonic()
    try:
        with prefix.with_suffix(".stdout").open("xb") as stdout,prefix.with_suffix(".stderr").open("xb") as stderr:
            os.chmod(prefix.with_suffix(".stdout"),0o600);os.chmod(prefix.with_suffix(".stderr"),0o600)
            child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            CURRENT_CHILD=child;record["pid"]=child.pid;record["pgid"]=os.getpgid(child.pid)
            require(record["pid"]==record["pgid"],"owned_process_session_identity")
            while child.poll() is None:
                if free()<STOP_FREE:
                    record["interruption"]="disk-reserve";raise RuntimeError("owned_command_disk_reserve")
                if time.monotonic()-start>=timeout:
                    record["interruption"]="timeout";raise subprocess.TimeoutExpired(argv,timeout)
                time.sleep(0.25)
            record["returncode"]=child.wait()
            if record["returncode"]!=0:record["primary_error"]={"type":"ChildProcessError","message":"owned_command_nonzero","returncode":record["returncode"]}
            stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
    except BaseException as error:
        if record["primary_error"] is None:record["primary_error"]={"type":type(error).__name__,"message":str(error)}
    finally:
        if child is not None:
            try:
                stop_owned(child,record);record["returncode"]=child.wait(timeout=5)
                deadline=time.monotonic()+3
                while True:
                    try:os.killpg(child.pid,0);absent=False
                    except ProcessLookupError:absent=True
                    if absent or time.monotonic()>=deadline:break
                    time.sleep(0.05)
                record["owned_group_absent"]=absent
                require(absent,"owned_process_group_remains")
            except BaseException as error:record["cleanup_error"]={"type":type(error).__name__,"message":str(error)}
        CURRENT_CHILD=None
        record.update(finished=now(),elapsed_seconds=time.monotonic()-start,free_after=free())
        for suffix in (".stdout",".stderr"):
            p=prefix.with_suffix(suffix)
            if p.exists():record[suffix[1:]]=physical(p)
        if record["primary_error"] is None and record["cleanup_error"] is None and record.get("returncode")==0 and record["owned_group_absent"]:record["status"]="PASS"
        save(prefix.with_suffix(".command.json"),record)
    return record
def main():
    parser=argparse.ArgumentParser();parser.add_argument("stage",choices=("build","execute"))
    parser.add_argument("--evidence",type=pathlib.Path,required=True)
    args=parser.parse_args();out=args.evidence
    require(out.is_absolute() and out.parent==EVIDENCE and re.fullmatch("attempt[1-9][0-9]*",out.name),"fixed_owned_evidence_path")
    require(str(REPO)=="/mnt/development/projects/worktrees/anytype-wave15-native-owned-snapshot-20261123","fixed_controller_writer")
    require(free()>=(START_FREE if args.stage=="build" else STOP_FREE),"initial_capacity_guard")
    manifest=json.loads((HERE/"source.json").read_text())
    require(manifest["selected_top_level_methods"]==METHODS and manifest["old_methods_selected"]==0 and
            manifest["native_parent_sha"]==PARENT and manifest["package"]=="./core/pinkha/localstorewitness" and
            manifest["native_storage_lifetime_issuer"] is True and manifest["hasNativeSourceAdmission"] is False and
            manifest["permitsDestinationWrites"] is False,"four_method_native_scope_contract")
    if args.stage=="build":
        require(not out.exists(),"original_attempt_already_exists")
        EVIDENCE.mkdir(mode=0o700,exist_ok=True);private_dir(EVIDENCE)
        out.mkdir(mode=0o700)
        for rel in ("private","private/fixtures","tmp","products"):(out/rel).mkdir(mode=0o700)
    private_dir(out);private_dir(out/"private");private_dir(out/"private/fixtures")
    receipt=out/(args.stage+".json");require(not receipt.exists(),"never_replace_original_stage")
    env=dict(os.environ,GOMAXPROCS="1",CGO_ENABLED="1",GOPROXY="off",GOSUMDB="off",GOTOOLCHAIN="local",
             GOFLAGS="",GOEXPERIMENT="",GOWORK="off",GOPATH=str(GOPATH),GOMODCACHE=str(MODCACHE),GOCACHE=str(BUILDCACHE),
             TMPDIR=str(out/"tmp"),GOTMPDIR=str(out/"tmp"),PINKHA_NATIVE_OWNED_SNAPSHOT_PRIVATE_ROOT=str(out/"private/fixtures"))
    result={"stage":args.stage,"status":"FAILED","started":now(),"scope":"native-owned-local-store-readonly-v1",
            "old_methods_executed":0,"actual_named_starts":[],"actual_named_passes":[],
            "native_storage_lifetime_issuer":True,"accountSessionACLAuthorized":False,"hasNativeSourceAdmission":False,
            "permitsDestinationWrites":False,"semanticIdentityCensusComplete":False,"filePayloadCoverageComplete":False,
            "manifest_sha256":sha(HERE/"source.json"),"controller_sha256":sha(HERE/"run.py"),
            "native_source_sha":manifest["native_source_sha"],"controller_source_sha":git(REPO,"rev-parse","HEAD").decode().strip(),
            "command":None,"primary_error":None,"final_errors":[]}
    before=None;deps=None;tools=None;loaded_before=None
    handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT)}
    for s in handlers:signal.signal(s,interrupted)
    try:
        before=source_snapshot(manifest);save(out/(args.stage+"-source-before.json"),before)
        deps=dependency_snapshot(manifest);save(out/(args.stage+"-dependencies-before.json"),deps)
        tools=tool_snapshot(manifest);save(out/(args.stage+"-tools-before.json"),tools)
        audit=load_auditor(manifest);loaded_before=loaded();save(out/(args.stage+"-loaded-before.json"),loaded_before)
        binary=out/"products/native-owned-snapshot.test"
        if args.stage=="build":
            require(not binary.exists(),"original_binary_already_exists")
            result["environment"]={k:env[k] for k in ("GOMAXPROCS","CGO_ENABLED","GOPROXY","GOSUMDB","GOTOOLCHAIN","GOFLAGS","GOEXPERIMENT","GOWORK","GOPATH","GOMODCACHE","GOCACHE","TMPDIR","GOTMPDIR")}
            result["command"]=command([str(GO),"test","-mod=readonly","-c","-p=1","-tags=pinkha_localstore_witness","-o",str(binary),manifest["package"]],NATIVE,env,out/"private/build-original",900)
            require(result["command"]["status"]=="PASS","native_build_failed_original_preserved")
            result["binary"]=physical(binary)
            info=subprocess.check_output([str(GO),"version","-m",str(binary)],env=env,timeout=30)
            original(out/"binary-buildinfo-original.txt",info)
            result["buildinfo_sha256"]=sha(out/"binary-buildinfo-original.txt")
            result["status"]="BUILD_PASS_EXECUTION_NOT_RUN"
        else:
            build=json.loads((out/"build.json").read_text())
            require(build["status"]=="BUILD_PASS_EXECUTION_NOT_RUN" and build["binary"]==physical(binary),"original_qualified_binary_changed")
            for key in ("manifest_sha256","controller_sha256","native_source_sha","controller_source_sha"):
                require(build[key]==result[key],"build_execution_origin_changed")
            selector="^("+"|".join(METHODS)+")$"
            result["command"]=command([str(GO),"tool","test2json","-t","-p",PACKAGE,str(binary),"-test.v=test2json","-test.run="+selector,"-test.timeout=90s","-test.count=1"],NATIVE,env,out/"private/execution-original",120)
            inspected=audit.inspect_events(out/"private/execution-original.stdout")
            save(out/"safe-events.json",inspected["events"])
            result["actual_named_starts"]=inspected["starts"];result["actual_named_passes"]=inspected["passes"]
            result["old_methods_executed"]=len([name for name in inspected["starts"] if name not in METHODS])
            save(out/"safe-native-observations.json",inspected["observations"]);save(out/"safe-native-receipts.json",inspected["receipts"])
            require(result["command"]["status"]=="PASS" and inspected["qualified"],"four_native_controls_failed_original_preserved")
            private_audit=audit.audit_private(out/"private/fixtures",inspected["receipts"])
            save(out/"private-frame-accounting.json",private_audit)
            result["binary"]=physical(binary);require(result["binary"]==build["binary"],"executed_binary_changed")
            result["private_frames_audited"]=len(private_audit)
            result["status"]="PASS_NATIVE_OWNED_LOCAL_STORE_ONLY"
    except BaseException as error:
        result["status"]="FAILED";result["primary_error"]={"type":type(error).__name__,"message":str(error)}
    finally:
        try:
            final=source_snapshot(manifest);save(out/(args.stage+"-source-after.json"),final)
            require(before is not None and final==before,"source_integrity_changed")
        except BaseException as e:result["final_errors"].append({"scope":"source","type":type(e).__name__,"message":str(e)})
        try:
            final=dependency_snapshot(manifest);save(out/(args.stage+"-dependencies-after.json"),final)
            require(deps is not None and final==deps,"dependency_integrity_changed")
        except BaseException as e:result["final_errors"].append({"scope":"dependency","type":type(e).__name__,"message":str(e)})
        try:
            final=tool_snapshot(manifest);save(out/(args.stage+"-tools-after.json"),final)
            require(tools is not None and final==tools,"tool_integrity_changed")
        except BaseException as e:result["final_errors"].append({"scope":"tool","type":type(e).__name__,"message":str(e)})
        try:
            final=loaded();save(out/(args.stage+"-loaded-after.json"),final)
            require(loaded_before is not None and all(final.get(k)==v for k,v in loaded_before.items()),"loaded_source_integrity_changed")
            result["loaded_before_count"]=len(loaded_before);result["loaded_after_count"]=len(final)
        except BaseException as e:result["final_errors"].append({"scope":"loaded","type":type(e).__name__,"message":str(e)})
        for s,handler in handlers.items():signal.signal(s,handler)
        if result["final_errors"]:result["status"]="FAILED"
        result["finished"]=now();result["free_bytes_final"]=free()
        save(receipt,result)
        print(json.dumps({"stage":args.stage,"status":result["status"],"receipt":str(receipt),"sha256":sha(receipt),
                          "actual_named_passes":len(result["actual_named_passes"]),"free_bytes":result["free_bytes_final"]}))
    return 0 if result["status"]!="FAILED" else 1
if __name__=="__main__":raise SystemExit(main())
