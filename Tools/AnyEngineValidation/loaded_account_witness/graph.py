#!/usr/bin/env python3
"""One bounded offline source graph for the opt-in loaded-account candidate.

No compile, export, test, download, extraction, source rewrite or cache cleanup.
The only long-running child is a fixed go-list process in a new owned container.
"""
import argparse
import hashlib
import gzip
import json
import os
import pathlib
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
CONTROL = HERE.parents[2]
HEART = pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-loaded-account-witness-20261123")
SYNC = pathlib.Path("/mnt/development/projects/worktrees/any-sync-loaded-account-witness-20261123")
HEART_SHA = "24dc6393b30e6d1d80ec28ff624060af9bb4327a"
SYNC_SHA = "c005bd6cde8d8f8a6007c35f06894f3d89f9f07c"
EVIDENCE = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
ATTEMPT = EVIDENCE / "graph-attempt1"
CACHE = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/attempt4/cache")
CACHE_REAL = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache")
GOROOT = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/toolchains/go1.26.5/go")
GO = GOROOT / "bin/go"
LIBDIR = pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-semantic-page-20261123/deps/libs/linux-arm64-musl")
LIBRARY = LIBDIR / "libtantivy_go.a"
IMAGE = "sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d"
NAME = "pinkha-loaded-account-graph-20261123"
LABEL = "pinkha.loaded-account-witness.graph"
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg pinkha_loaded_account_witness pinkha_loaded_account_witness_acceptance"
GO_SHA256 = "22201b57b855105df064a291863c3fc04f22a7431187a9205122aff42a0c825b"
LIB_SHA256 = "efee68b0fdf23fd8c1c630f10f4cad497bbbcb7372b6b985933324ebe730a601"
MOD_SHA256 = "73cbdd42c8002c7bf68561ebc11b14ac58aad5aa018a41b27d56adaa9b87636c"
SUM_SHA256 = "7c873be1e5b4c65e5e46d18167ae6bc29f0f5b51c459a8398d75ab22f0b2432d"
START_FREE = 2_650_000_000
STOP_FREE = 2_600_000_000
FINAL_FREE = 2_500_000_000
TOTAL_OUTPUT = 16 * 1024 * 1024
STDOUT_LIMIT = 8 * 1024 * 1024
STDERR_LIMIT = 1 * 1024 * 1024
METADATA_LIMIT = 6 * 1024 * 1024
QUERY_SECONDS = 120
DOCKER = ["sudo", "-n", "docker"]
CURRENT = None

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def now():
    return datetime.now(timezone.utc).isoformat()

def free():
    return shutil.disk_usage("/mnt/development").free

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def row(path):
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink(), "input_not_regular")
    digest = sha(path)
    after = path.stat()
    fields = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    require(tuple(getattr(before,k) for k in fields) == tuple(getattr(after,k) for k in fields), "input_changed_during_read")
    return dict(path=str(path), sha256=digest, **{k:str(getattr(after,k)) for k in fields})

def used():
    if not ATTEMPT.exists():
        return 0
    return sum(p.stat().st_size for p in ATTEMPT.rglob("*") if p.is_file() and not p.is_symlink())

def save(path, value):
    raw = (json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
    require(len(raw) <= METADATA_LIMIT, "single_metadata_limit")
    require(used()+len(raw) <= TOTAL_OUTPUT, "total_metadata_limit")
    with path.open("xb") as target:
        os.chmod(path,0o600)
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    return {"path":str(path),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def save_map(path, value):
    raw = (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    require(len(raw)<=METADATA_LIMIT,"expanded_source_map_limit")
    packed = gzip.compress(raw,compresslevel=6,mtime=0)
    require(len(packed)<=2*1024*1024 and used()+len(packed)<=TOTAL_OUTPUT-1024*1024,"compressed_source_map_budget")
    with path.open("xb") as target:
        os.chmod(path,0o600)
        target.write(packed)
        target.flush()
        os.fsync(target.fileno())
    return {"path":str(path),"bytes":len(packed),"sha256":hashlib.sha256(packed).hexdigest(),
            "encoding":"gzip-json","expanded_bytes":len(raw),"expanded_sha256":hashlib.sha256(raw).hexdigest()}

def git(root, *args):
    return subprocess.check_output(["git","-C",str(root),*args],timeout=30)

def tracked_snapshot(root, pin, *, control=False):
    require(git(root,"rev-parse","HEAD").decode().strip()==pin,"source_commit_changed")
    require(not git(root,"status","--porcelain=v1","--untracked-files=all").strip(),"source_worktree_dirty")
    selected = ["Tools/AnyEngineValidation/loaded_account_witness"] if control else []
    records = {}
    for item in git(root,"ls-tree","-rz",pin,"--",*selected).split(b"\0"):
        if not item:
            continue
        header,name = item.split(b"\t",1)
        mode,kind,oid = header.split()
        name = name.decode()
        if not control and name.startswith(("docs/",".github/")):
            continue
        require(kind==b"blob" and mode in (b"100644",b"100755"),"unsupported_source_tree_entry")
        path = root/name
        require(path.is_file() and path.resolve()==path,"source_missing_or_relocated")
        raw = path.read_bytes()
        actual = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        require(actual==oid.decode(),"physical_source_differs_from_git")
        require(bool(path.stat().st_mode&0o111)==(mode==b"100755"),"source_executable_mode_changed")
        records[name] = dict(row(path),git_blob=oid.decode(),git_mode=mode.decode())
    require(bool(records),"empty_source_snapshot")
    return {"root":str(root),"commit":pin,"inputs":records}

def loaded_python_sources():
    records = {}
    all_worktrees = HEART.parent
    own = pathlib.Path(__file__).resolve()
    for name,module in sorted(sys.modules.items()):
        filename = getattr(module,"__file__",None)
        if not filename:
            continue
        path = pathlib.Path(filename).resolve()
        if path.is_relative_to(all_worktrees):
            require(path==own,"unexpected_repository_python_module")
            records[name] = row(path)
    require(records.get("__main__",{}).get("path")==str(own),"actual_graph_module_binding_missing")
    return records

def source_snapshot(control_sha):
    require(re.fullmatch(r"[0-9a-f]{40}",control_sha) is not None,"invalid_controller_identity")
    require(CACHE.is_symlink() and os.readlink(CACHE)=="../cache" and CACHE.resolve()==CACHE_REAL,"qualified_cache_spelling_changed")
    require(sha(GO)==GO_SHA256,"go_tool_identity_changed")
    require(sha(LIBRARY)==LIB_SHA256,"tantivy_library_identity_changed")
    require(sha(HERE/"candidate.mod")==MOD_SHA256 and sha(HERE/"candidate.sum")==SUM_SHA256,"candidate_module_inputs_changed")
    require(sha(HEART/"go.sum")==SUM_SHA256,"original_go_sum_changed")
    require((HERE/"candidate.mod").read_bytes()==(HEART/"go.mod").read_bytes()+
        ("\nreplace github.com/anyproto/any-sync => "+str(SYNC)+"\n").encode(),"candidate_modfile_inverse_changed")
    return {
        "heart":tracked_snapshot(HEART,HEART_SHA),
        "any_sync":tracked_snapshot(SYNC,SYNC_SHA),
        "controller":tracked_snapshot(CONTROL,control_sha,control=True),
        "tools":{"go":row(GO),"tantivy_library":row(LIBRARY)},
        "actual_loaded_python":loaded_python_sources(),
    }

def group_absent(pgid):
    try:
        os.killpg(pgid,0)
        return False
    except ProcessLookupError:
        return True

def stop_owned(child, record):
    require(record.get("pid")==child.pid and record.get("pgid")==child.pid,"owned_cleanup_pid_pgid_binding")
    child.poll()
    absent = group_absent(child.pid)
    record["cleanup_group_initially_absent"] = absent
    if absent:
        return
    for name,sig in (("term",signal.SIGTERM),("kill",signal.SIGKILL)):
        try:
            os.killpg(child.pid,sig)
            record[name+"_sent"] = True
        except ProcessLookupError:
            record[name+"_sent"] = False
        deadline = time.monotonic()+5
        while True:
            child.poll()
            absent = group_absent(child.pid)
            if absent or time.monotonic()>=deadline:
                break
            time.sleep(0.05)
        record["group_absent_after_"+name] = absent
        if absent:
            return
    require(absent,"owned_process_group_survived_kill")

def interrupt(signum, _frame):
    raise InterruptedError("owned_graph_signal_"+str(signum))

def query_command(argv):
    global CURRENT
    record = {"argv":argv,"cwd":str(HEART),"started":now(),"status":"FAILED",
              "primary_error":None,"cleanup_error":None,"owned_group_absent":False,
              "stdout_complete":False,"stderr_complete":False,"source_enumeration_only":True}
    files = {}
    streams = {}
    child = None
    start = time.monotonic()
    counts = {"stdout":0,"stderr":0}
    limits = {"stdout":STDOUT_LIMIT,"stderr":STDERR_LIMIT}
    selector = selectors.DefaultSelector()
    try:
        require(free()>=START_FREE,"source_query_start_reserve")
        for name in counts:
            path = ATTEMPT/(name+".log")
            files[name] = path.open("xb")
            os.chmod(path,0o600)
        record["launch_attempted"] = True
        child = subprocess.Popen(argv,cwd=HEART,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        CURRENT = child
        record.update(pid=child.pid,pgid=os.getpgid(child.pid))
        require(child.pid==record["pgid"],"owned_cli_process_group")
        for name,stream in (("stdout",child.stdout),("stderr",child.stderr)):
            os.set_blocking(stream.fileno(),False)
            selector.register(stream,selectors.EVENT_READ,name)
            streams[name] = stream
        while selector.get_map():
            require(time.monotonic()-start<QUERY_SECONDS,"source_query_timeout")
            require(free()>=STOP_FREE,"source_query_stop_reserve")
            for key,_event in selector.select(0.25):
                name = key.data
                chunk = os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    record[name+"_complete"] = True
                    continue
                remain = limits[name]-counts[name]
                if len(chunk)>remain:
                    files[name].write(chunk[:max(remain,0)])
                    counts[name] += max(remain,0)
                    record["output_limit_observation"] = {"stream":name,"bytes_observed_at_least":counts[name]+len(chunk)-max(remain,0)}
                    raise RuntimeError("source_query_"+name+"_limit")
                files[name].write(chunk)
                counts[name] += len(chunk)
        record["returncode"] = child.wait(timeout=max(0.001,QUERY_SECONDS-(time.monotonic()-start)))
        if record["returncode"]!=0:
            record["primary_error"] = {"type":"ChildProcessError","message":"source_query_nonzero","returncode":record["returncode"]}
        elapsed,available = time.monotonic()-start,free()
        record["post_exit_observation"] = {"elapsed_seconds":elapsed,"free_bytes":available}
        require(elapsed<QUERY_SECONDS and available>=STOP_FREE,"source_query_late_or_low_completion")
    except BaseException as error:
        if record["primary_error"] is None:
            record["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        if record.get("launch_attempted"):
            try:
                record["container_cleanup"] = owned_container_cleanup()
            except BaseException as error:
                record["cleanup_error"] = {"phase":"container","type":type(error).__name__,"message":str(error)}
        if child is not None:
            try:
                stop_owned(child,record)
                record["returncode"] = child.wait(timeout=5)
                record["owned_group_absent"] = group_absent(child.pid)
                require(record["owned_group_absent"],"source_query_cli_group_remains")
            except BaseException as error:
                record.setdefault("additional_cleanup_errors",[]).append({"phase":"cli-group","type":type(error).__name__,"message":str(error)})
                if record["cleanup_error"] is None:
                    record["cleanup_error"] = record["additional_cleanup_errors"][-1]
        CURRENT = None
        selector.close()
        for stream in streams.values():
            stream.close()
        for name,target in files.items():
            target.flush()
            os.fsync(target.fileno())
            target.close()
            record[name] = row(ATTEMPT/(name+".log"))
        record.update(finished=now(),elapsed_seconds=time.monotonic()-start,free_after=free())
        if record["primary_error"] is None and record["cleanup_error"] is None and record.get("returncode")==0 and record["owned_group_absent"] and all(record[x+"_complete"] for x in counts) and record.get("container_cleanup",{}).get("final_state",{}).get("ExitCode")==0:
            record["status"] = "PASS"
        save(ATTEMPT/"query-command.json",record)
    return record

def docker_observe(args, label, timeout=20):
    argv = DOCKER+args
    observation = {"argv":argv,"started":now(),"primary_error":None,"cleanup_error":None}
    child = None
    streams = {}
    buffers = {"stdout":bytearray(),"stderr":bytearray()}
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    try:
        child = subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        observation.update(pid=child.pid,pgid=os.getpgid(child.pid))
        require(observation["pgid"]==child.pid,"docker_observation_group_binding")
        for name,stream in (("stdout",child.stdout),("stderr",child.stderr)):
            streams[name] = stream
            os.set_blocking(stream.fileno(),False)
            selector.register(stream,selectors.EVENT_READ,name)
        while selector.get_map():
            require(time.monotonic()-started<timeout,"docker_observation_timeout")
            for key,_event in selector.select(min(0.1,max(0.001,timeout-(time.monotonic()-started)))):
                chunk = os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remain = 256*1024-sum(len(b) for b in buffers.values())
                buffers[key.data].extend(chunk[:max(0,remain)])
                require(len(chunk)<=remain,"docker_observation_output_limit")
        observation["returncode"] = child.wait(timeout=max(0.001,timeout-(time.monotonic()-started)))
        require(time.monotonic()-started<timeout,"docker_observation_late_completion")
    except BaseException as error:
        observation["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        if child is not None:
            try:
                stop_owned(child,observation)
                observation["returncode"] = child.wait(timeout=5)
                observation["owned_group_absent"] = group_absent(child.pid)
                require(observation["owned_group_absent"],"docker_observation_group_remains")
            except BaseException as error:
                observation["cleanup_error"] = {"type":type(error).__name__,"message":str(error)}
        selector.close()
        for stream in streams.values():
            stream.close()
        observation.update(stdout=bytes(buffers["stdout"]).decode("utf-8","replace"),
                           stderr=bytes(buffers["stderr"]).decode("utf-8","replace"),
                           finished=now(),elapsed_seconds=time.monotonic()-started)
        save(ATTEMPT/(label+".json"),observation)
    require(observation["primary_error"] is None and observation["cleanup_error"] is None,
            "docker_observation_failed_"+label)
    return subprocess.CompletedProcess(argv,observation["returncode"],bytes(buffers["stdout"]),bytes(buffers["stderr"]))

def environment():
    return {
        "CGO_ENABLED":"1","CC":"gcc","CXX":"g++","GOOS":"linux","GOARCH":"arm64",
        "GOMAXPROCS":"1","GOMEMLIMIT":"3072MiB","GOTOOLCHAIN":"local","GOWORK":"off",
        "GOFLAGS":"-mod=readonly -p=1","GOPROXY":"off","GOSUMDB":"off",
        "GOMODCACHE":str(CACHE/"go-mod"),"GOCACHE":str(CACHE/"go-build"),
        "GOPATH":str(ATTEMPT/"gopath"),"GOTMPDIR":str(ATTEMPT/"tmp"),"TMPDIR":str(ATTEMPT/"tmp"),
        "CGO_LDFLAGS":"-L"+str(LIBDIR),
        "PATH":str(GOROOT/"bin")+":/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }

def mounts():
    return [
        (HEART,HEART,False),(SYNC,SYNC,False),(HERE,HERE,False),(GOROOT,GOROOT,False),
        ((CACHE/"go-mod").resolve(),CACHE/"go-mod",False),
        ((CACHE/"go-build").resolve(),CACHE/"go-build",True),
        (LIBDIR,LIBDIR,False),(ATTEMPT,ATTEMPT,True),
        (ATTEMPT/"image-data-empty",pathlib.Path("/var/lib/postgresql/data"),False),
    ]

def query_argv():
    args = DOCKER+["run","--pull=never","--name",NAME,"--cidfile",str(ATTEMPT/"container.cid"),
        "--label",LABEL+"="+HEART_SHA,"--network","none","--read-only","--user","1001:1001",
        "--cpus","1","--memory","6g","--pids-limit","256","--cap-drop","ALL",
        "--security-opt","no-new-privileges","--workdir",str(HEART),"--entrypoint",str(GO)]
    for source,destination,writable in mounts():
        args += ["--mount","type=bind,source="+str(source)+",target="+str(destination)+("" if writable else ",readonly")]
    for key,value in sorted(environment().items()):
        args += ["--env",key+"="+value]
    args += [IMAGE,"list","-deps","-test","-json","-modfile="+str(HERE/"candidate.mod"),"-tags",TAGS,"./core/application"]
    return args

def owned_container_cleanup():
    cidpath = ATTEMPT/"container.cid"
    if not cidpath.exists():
        result = docker_observe(["inspect",NAME],"container-no-cid")
        require(result.returncode!=0 and b"No such object" in result.stderr,"container_state_unknown_without_cid")
        return {"state":"ABSENT","container_started":False}
    require(cidpath.is_file() and not cidpath.is_symlink(),"container_cid_not_regular")
    cid = cidpath.read_text().strip()
    require(re.fullmatch(r"[0-9a-f]{64}",cid) is not None,"invalid_owned_container_id")
    observed = docker_observe(["inspect",cid],"container-before-cleanup")
    require(observed.returncode==0,"owned_container_inspection_failed")
    values = json.loads(observed.stdout)
    require(isinstance(values,list) and len(values)==1,"container_inspection_shape")
    value = values[0]
    require(value["Id"]==cid and value["Name"]=="/"+NAME and value["Image"]==IMAGE,"container_identity_changed")
    require(value["Config"]["Labels"].get(LABEL)==HEART_SHA and value["Config"]["User"]=="1001:1001","container_owner_changed")
    require(value["HostConfig"]["NetworkMode"]=="none" and value["HostConfig"]["ReadonlyRootfs"] is True,"container_isolation_changed")
    actual_mounts = {(m["Source"],m["Destination"],m["RW"],m["Type"]) for m in value["Mounts"]}
    expected_mounts = {(str(a.resolve()),str(b),rw,"bind") for a,b,rw in mounts()}
    require(actual_mounts==expected_mounts,"container_mounts_changed")
    require(value["Path"]==str(GO) and value["Args"]==query_argv()[query_argv().index(IMAGE)+1:],"container_query_changed")
    configured = {}
    for item in value["Config"]["Env"]:
        key,content = item.split("=",1)
        require(key not in configured,"duplicate_container_environment")
        configured[key] = content
    require(all(configured.get(k)==v for k,v in environment().items()),"container_environment_changed")
    require(value["Config"]["WorkingDir"]==str(HEART),"container_working_directory_changed")
    require(value["HostConfig"]["NanoCpus"]==1_000_000_000 and value["HostConfig"]["Memory"]==6*1024**3 and value["HostConfig"]["PidsLimit"]==256,"container_resource_binding_changed")
    require(set(value["HostConfig"]["CapDrop"] or [])=={"ALL"} and "no-new-privileges" in value["HostConfig"]["SecurityOpt"],"container_privilege_binding_changed")
    initial_state = value["State"]
    if initial_state["Running"]:
        stopped = docker_observe(["kill",cid],"container-owned-kill")
        require(stopped.returncode==0,"owned_container_kill_failed")
    after = docker_observe(["inspect",cid],"container-after-cleanup")
    require(after.returncode==0,"owned_container_final_inspection_failed")
    final = json.loads(after.stdout)[0]
    require(final["Id"]==cid and final["State"]["Running"] is False and final["State"]["Pid"]==0,"owned_container_still_running")
    return {"state":"STOPPED_RETAINED","id":cid,"initial_state":initial_state,"final_state":final["State"],
            "removed":False,"native_builds_or_tests_requested":False}

def dependency_plan(raw):
    decoder = json.JSONDecoder()
    text = raw.decode()
    offset = 0
    packages = []
    inputs = {}
    modules = {}
    fields = ("GoFiles","CgoFiles","CFiles","CXXFiles","MFiles","HFiles","FFiles","SFiles","SwigFiles","SwigCXXFiles","SysoFiles",
              "EmbedFiles","TestGoFiles","XTestGoFiles","TestEmbedFiles","XTestEmbedFiles")
    allowed = (HEART,SYNC,CACHE_REAL/"go-mod",GOROOT)
    while offset<len(text):
        while offset<len(text) and text[offset].isspace():
            offset += 1
        if offset==len(text):
            break
        package,offset = decoder.raw_decode(text,offset)
        require(isinstance(package,dict) and not package.get("Error") and not package.get("DepsErrors"),"incomplete_go_package_graph")
        packages.append({"import_path":package["ImportPath"],"directory":package.get("Dir"),"for_test":package.get("ForTest"),
                         "standard":package.get("Standard",False),"module":package.get("Module")})
        directory = pathlib.Path(package.get("Dir",""))
        for field in fields:
            for name in package.get(field,[]):
                relative = pathlib.Path(name)
                generated = relative.is_absolute()
                if generated:
                    path = relative
                    cache_relative = path.relative_to(CACHE/"go-build")
                    require(package["ImportPath"]=="github.com/anyproto/anytype-heart/core/application.test" and
                            package.get("Name")=="main" and field=="GoFiles" and
                            re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{64}-d",cache_relative.as_posix()) is not None,
                            "unadmitted_generated_graph_input")
                    require(path.stat().st_size<=128*1024,"generated_test_main_size")
                    raw_generated = path.read_bytes()
                    require(raw_generated.startswith(b"\n// Code generated by 'go test'. DO NOT EDIT.\n\npackage main\n") and
                            hashlib.sha256(raw_generated).hexdigest()==path.name[:-2],
                            "generated_test_main_identity")
                    require(path.resolve().is_relative_to(CACHE_REAL/"go-build"),"generated_test_main_escape")
                else:
                    require(".." not in relative.parts,"dependency_file_escape")
                    path = directory/relative
                resolved = path.resolve()
                require(generated or any(resolved.is_relative_to(root) for root in allowed),"unbound_dependency_root")
                inputs[str(path)] = dict(row(path),resolved_path=str(resolved),generated_test_main=generated)
        module = package.get("Module")
        if module:
            effective = module.get("Replace",module)
            modules[(module["Path"],module.get("Version",""))] = module
            gomod = effective.get("GoMod")
            if gomod:
                path = pathlib.Path(gomod)
                resolved = path.resolve()
                require(any(resolved.is_relative_to(root) for root in allowed) or path==HERE/"candidate.mod","unbound_module_manifest")
                inputs[str(path)] = dict(row(path),resolved_path=str(resolved))
    require(any(p["import_path"]=="github.com/anyproto/anytype-heart/core/application" for p in packages),"application_graph_missing")
    sync_rows = [m for (path,_version),m in modules.items() if path=="github.com/anyproto/any-sync"]
    require(len(sync_rows)==1 and sync_rows[0].get("Version")=="v0.13.8","any_sync_version_changed")
    replacement = sync_rows[0].get("Replace",{})
    require(replacement.get("Dir")==str(SYNC) and replacement.get("Path")==str(SYNC),"tracked_any_sync_replacement_not_resolved")
    require(str(HEART/"core/application/loaded_witness_test.go") in inputs and str(HEART/"core/application/loaded_witness_fixture_test.go") in inputs,"new_acceptance_controls_missing")
    require(str(SYNC/"commonspace/object/acl/syncacl/witness_read.go") in inputs,"new_native_acl_feature_missing")
    require(len(inputs)<=20000 and len(packages)<=5000,"dependency_graph_row_limit")
    return {"protocol":"loaded-account-offline-source-graph-v1","packages":packages,
            "modules":[modules[key] for key in sorted(modules)],"inputs":inputs,
            "source_only":True,"compile_export_or_test_requested":False,"module_cache_mounted_readonly":True,
            "go_build_cache_metadata_writes_possible":True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-controller-sha",required=True)
    parser.add_argument("--execute",action="store_true")
    args = parser.parse_args()
    require(args.execute,"explicit_source_graph_execution_flag_required")
    require(os.getuid()==1001,"expected_oracle_owner_required")
    require(free()>=START_FREE,"source_graph_start_reserve")
    require(not ATTEMPT.exists(),"preserve_prior_graph_attempt")
    EVIDENCE.mkdir(mode=0o700,exist_ok=True)
    ATTEMPT.mkdir(mode=0o700)
    for name in ("tmp","gopath","image-data-empty"):
        (ATTEMPT/name).mkdir(mode=0o700)
    record = {"protocol":"loaded-account-offline-source-graph-v1","started":now(),"status":"FAILED",
              "primary_error":None,"final_errors":[],"native_builds":0,"actual_test_methods":0,
              "source_graph_start_floor":START_FREE,"source_graph_stop_floor":STOP_FREE,
              "source_graph_budget_seconds":QUERY_SECONDS,"metadata_limit_bytes":TOTAL_OUTPUT,
              "expected_controller_sha":args.expected_controller_sha,"environment":environment()}
    before = None
    query = None
    try:
        before = source_snapshot(args.expected_controller_sha)
        record["source_before"] = save_map(ATTEMPT/"source-before.json.gz",before)
        absence = docker_observe(["inspect",NAME],"container-preflight-absence")
        require(absence.returncode!=0 and b"No such object" in absence.stderr,"container_name_already_present_or_unobservable")
        image = docker_observe(["image","inspect",IMAGE],"image-original")
        require(image.returncode==0 and json.loads(image.stdout)[0]["Id"]==IMAGE,"pinned_image_unavailable")
        require(set(json.loads(image.stdout)[0]["Config"].get("Volumes") or {})=={"/var/lib/postgresql/data"},"unreviewed_image_volume")
        query = query_command(query_argv())
        record["query"] = query
        require(query["status"]=="PASS","source_query_failed")
        plan = dependency_plan((ATTEMPT/"stdout.log").read_bytes())
        record["dependency_plan"] = save_map(ATTEMPT/"dependency-plan.json.gz",plan)
        record["dependency_files"] = len(plan["inputs"])
        record["packages"] = len(plan["packages"])
    except BaseException as error:
        record["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        record["container_cleanup"] = query.get("container_cleanup") if query else {"state":"NOT_STARTED"}
        if query and query.get("cleanup_error") is not None:
            record["final_errors"].append({"phase":"container-or-cli-cleanup","error":query["cleanup_error"]})
        try:
            after = source_snapshot(args.expected_controller_sha)
            record["source_after"] = save_map(ATTEMPT/"source-after.json.gz",after)
            require(before==after,"source_before_after_mismatch")
            record["source_unchanged"] = True
        except BaseException as error:
            record["final_errors"].append({"phase":"source-integrity","type":type(error).__name__,"message":str(error)})
        record["free_final"] = free()
        if record["free_final"]<FINAL_FREE:
            record["final_errors"].append({"phase":"final-capacity","free_bytes":record["free_final"],"minimum":FINAL_FREE})
        record["finished"] = now()
        record["retained_container_is_not_build_or_test_evidence"] = True
        if record["primary_error"] is None and not record["final_errors"]:
            record["status"] = "PASS_SOURCE_ONLY_GRAPH"
        result = save(ATTEMPT/"result.json",record)
        print(json.dumps({"status":record["status"],"result":result,"dependency_files":record.get("dependency_files"),
                          "packages":record.get("packages"),"free_final":record["free_final"]}))
    return 0 if record["status"]=="PASS_SOURCE_ONLY_GRAPH" else 1

if __name__=="__main__":
    signal.signal(signal.SIGTERM,interrupt)
    signal.signal(signal.SIGINT,interrupt)
    sys.exit(main())
