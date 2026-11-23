#!/usr/bin/env python3
"""Later current-controller audit only; no graph, Go, native test or container."""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import resource
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

CONTROL = pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
HEAD = "1b98b7a01acc3b08d48c30c566d207f499a103d2"
ROOT = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
ORIGINAL = ROOT/"ram-projected-graph-attempt1"
OFFLINE = ROOT/"ram-projected-offline-completion1"
OUTPUT = ROOT/"ram-projected-offline-final-controller1"
RESULT_SHA = "cedb78b0e5478e9697fec61e16f5da175bed7a50d2d371583d6a34c7361e2b9c"
BEFORE_SHA = "2a5d9b30dbde12e7dc8e489b7935a005d21ac316840f3374ba706a653a32cd7b"
GIT = pathlib.Path("/usr/bin/git")
GIT_SHA = "068c11a6747b848c3ed35599f714250864d2bd94b4165d27770ce5c36e83894f"
DOC = pathlib.Path("/usr/share/man/man1/git-config.1.gz")
DOC_SHA = "5fd1cd7f480c9890ccac7ff1a201043793dc090345c24c92527550b721828b19"
PACK = pathlib.Path("/mnt/development/projects/git-mirrors/anytype-swift.git/objects/pack/pack-d4a3bc7cad22923baea8797453958b68ed82ed1a.pack")
SELECTION = ("Tools/AnyEngineValidation/loaded_account_witness",
    "docs/validation/20261123-loaded-account-witness/projected-original-attempt1",
    "docs/validation/20261123-loaded-account-witness/offline-completion")
CONFIG = ("-c","core.packedGitWindowSize=16m","-c","core.packedGitLimit=64m")
FIELDS = ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
TOTAL = 16*1024*1024
READ_LIMIT = 16*1024*1024
AS_LIMIT = 512*1024*1024
FLOOR = 1024**3
SECONDS = 120
START = None
READ_BYTES = 0
COMMANDS = []

def require(value,reason):
    if not value:
        raise RuntimeError(reason)

def now():
    return datetime.now(timezone.utc).isoformat()

def guard():
    require(START is None or time.monotonic()-START<SECONDS,"later_audit_deadline")
    require(shutil.disk_usage("/mnt/development").free>=FLOOR,"later_audit_capacity")

def read(path):
    global READ_BYTES
    guard()
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink(),"later_input_not_regular")
    require(before.st_size<=4*1024*1024,"later_fixed_input_size")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(opened,k) for k in FIELDS),"later_input_open_identity")
        raw = stream.read()
    READ_BYTES += len(raw)
    require(READ_BYTES<=READ_LIMIT,"later_input_read_budget")
    after = path.lstat()
    require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(after,k) for k in FIELDS),"later_input_changed")
    value = dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),**{k:str(getattr(after,k)) for k in FIELDS})
    return raw,value

def pinned(path,digest):
    raw,value = read(path)
    require(value["sha256"]==digest,"later_fixed_input_hash")
    return raw,value

def used():
    total = 0
    for root in (ORIGINAL,OFFLINE,OUTPUT):
        if root.exists():
            for path in root.rglob("*"):
                require(not path.is_symlink(),"later_evidence_symlink")
                if path.is_file():
                    total += path.stat().st_size
    return total

def save(path,value):
    raw = (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    require(len(raw)<=512*1024 and used()+len(raw)<=TOTAL-65536,"later_evidence_budget")
    with path.open("xb") as stream:
        os.chmod(path,0o600)
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return {"path":str(path),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def absent(pgid):
    try:
        os.killpg(pgid,0)
        return False
    except ProcessLookupError:
        return True

def stop(child,record):
    require(type(child) is subprocess.Popen and record["pid"]==child.pid and record["pgid"]==child.pid,
            "later_owned_git_identity")
    child.poll()
    if absent(child.pid):
        record["group_initially_absent"] = True
        return
    for label,signum in (("term",signal.SIGTERM),("kill",signal.SIGKILL)):
        try:
            os.killpg(child.pid,signum);record[label+"_sent"] = True
        except ProcessLookupError:
            record[label+"_sent"] = False
        until = time.monotonic()+5
        while not absent(child.pid) and time.monotonic()<until:
            child.poll();time.sleep(0.05)
        child.poll()
        if absent(child.pid):
            return
    require(absent(child.pid),"later_owned_git_group_remains")

def git(arguments,label):
    guard()
    argv = [str(GIT),*CONFIG,"-C",str(CONTROL),*arguments]
    record = {"argv":argv,"started":now(),"primary_error":None,"cleanup_error":None}
    child = None
    selector = selectors.DefaultSelector()
    chunks = {"stdout":bytearray(),"stderr":bytearray()}
    streams = []
    begun = time.monotonic()
    try:
        child = subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        record.update(pid=child.pid,pgid=os.getpgid(child.pid))
        require(record["pgid"]==child.pid,"later_git_pgid")
        for name,stream in (("stdout",child.stdout),("stderr",child.stderr)):
            streams.append(stream);os.set_blocking(stream.fileno(),False)
            selector.register(stream,selectors.EVENT_READ,name)
        while selector.get_map():
            guard()
            require(time.monotonic()-begun<20,"later_git_command_deadline")
            for key,_event in selector.select(0.1):
                raw = os.read(key.fileobj.fileno(),65536)
                if not raw:
                    selector.unregister(key.fileobj);continue
                remaining = 256*1024-len(chunks[key.data])
                chunks[key.data].extend(raw[:max(0,remaining)])
                require(len(raw)<=remaining,"later_git_output_budget")
        record["returncode"] = child.wait(timeout=max(0.001,min(20-(time.monotonic()-begun),SECONDS-(time.monotonic()-START))))
        require(record["returncode"]==0,"later_git_nonzero")
        guard()
    except BaseException as error:
        record["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        if child is not None:
            try:
                stop(child,record)
                record["returncode"] = child.wait(timeout=5)
                record["group_absent"] = absent(child.pid)
                require(record["group_absent"],"later_git_group_survived")
            except BaseException as error:
                record["cleanup_error"] = {"type":type(error).__name__,"message":str(error)}
        selector.close()
        for stream in streams:
            stream.close()
        record.update(stdout=bytes(chunks["stdout"]).decode("utf-8","replace"),
                      stderr=bytes(chunks["stderr"]).decode("utf-8","replace"),
                      finished=now(),elapsed_seconds=time.monotonic()-begun)
        COMMANDS.append(record)
        save(OUTPUT/(label+".json"),record)
    require(record["primary_error"] is None and record["cleanup_error"] is None,"later_git_failed_"+label)
    return bytes(chunks["stdout"])

def source_rows(before,tree):
    rows = {}
    for item in tree.split(b"\0"):
        if not item:
            continue
        header,name = item.split(b"\t",1)
        mode,kind,oid = header.split();name=name.decode()
        require(name in before["records"] and name not in rows and kind==b"blob" and mode in (b"100644",b"100755"),
                "later_controller_tree_shape")
        path = CONTROL/name
        require(path.resolve()==path,"later_controller_path")
        raw,value = read(path)
        require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==oid.decode(),
                "later_controller_git_bytes")
        value.update(git_blob=oid.decode(),git_mode=mode.decode())
        require(bool(int(value["st_mode"])&0o111)==(mode==b"100755"),"later_controller_mode")
        require(value==before["records"][name],"later_controller_differs_from_original_before")
        rows[name] = value
    require(set(rows)==set(before["records"]) and len(rows)==28,"later_controller_set_changed")
    old_loaded = before["actual_loaded_python"]
    require(set(old_loaded)=={"__main__"},"original_loaded_before_shape")
    original_path = pathlib.Path(old_loaded["__main__"]["path"])
    value = rows[original_path.relative_to(CONTROL).as_posix()]
    require({k:value[k] for k in old_loaded["__main__"]}==old_loaded["__main__"],"original_producer_file_changed")
    return rows

def actual_auditor_sources():
    result = {}
    own = pathlib.Path(__file__).resolve()
    for name,module in sorted(sys.modules.items()):
        filename = getattr(module,"__file__",None)
        if filename:
            path = pathlib.Path(filename).resolve()
            if path.is_relative_to(pathlib.Path("/mnt/development/projects")):
                require(path==own,"unexpected_later_project_module")
                result[name] = read(path)[1]
    require(set(result)=={"__main__"},"later_actual_loaded_auditor")
    return result

def interrupt(signum,_frame):
    raise InterruptedError("later_audit_signal_"+str(signum))

def main():
    global START
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha256",required=True)
    parser.add_argument("--execute",action="store_true")
    args = parser.parse_args()
    require(args.execute and sys.flags.isolated and sys.dont_write_bytecode,"isolated_later_audit_entry")
    require(os.getresuid()==(1001,1001,1001),"later_ordinary_owner")
    require(shutil.disk_usage("/mnt/development").free>=FLOOR+TOTAL,"later_initial_capacity")
    prior = resource.getrlimit(resource.RLIMIT_AS)
    selected = min([AS_LIMIT]+[v for v in prior if v>=0])
    resource.setrlimit(resource.RLIMIT_AS,(selected,prior[1]))
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(),"preserve_prior_later_audit")
    OUTPUT.mkdir(mode=0o700)
    START = time.monotonic()
    signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGALRM,interrupt)
    signal.setitimer(signal.ITIMER_REAL,SECONDS)
    result = {"schema":"later-current-controller-only-audit-v1","started":now(),"status":"FAILED",
        "primary_error":None,"final_errors":[],"controller":HEAD,"original_offline_result_sha256":RESULT_SHA,
        "original_offline_result_status":"FAILED","missing_historical_current_source_after":"NOT_RECREATED",
        "missing_historical_loaded_after":"NOT_RECREATED","new_queries_builds_tests":0,
        "dependency_graph_codec_source_tool_replay":False,"process_address_space_limit":selected,
        "command_local_pack_window_bytes":16777216,"command_local_pack_limit_bytes":67108864,
        "persistent_config_changed":False,"duration_limit_seconds":SECONDS,"fixed_input_read_limit_bytes":READ_LIMIT,
        "read_bytes_scope":"explicit auditor fixed-file reads; excludes separate Git pack I/O"}
    fixed = loaded = rows = None
    try:
        own_raw,own = pinned(pathlib.Path(__file__).resolve(),args.expected_sha256)
        result["auditor_source"] = own
        loaded = actual_auditor_sources()
        result["actual_later_loaded_before"] = loaded
        rb,rrow = pinned(OFFLINE/"result.json",RESULT_SHA)
        bb,brow = pinned(OFFLINE/"current-source-before.json.gz",BEFORE_SHA)
        result["original_receipts"] = [rrow,brow]
        old = json.loads(rb);before = json.loads(gzip.decompress(bb))
        require(old["status"]=="FAILED" and old["primary_error"] is None and len(old["final_errors"])==1 and
                old["final_errors"][0]["phase"]=="current-source" and
                old["final_errors"][0]["type"]=="CalledProcessError","original_final_failure_contract")
        require(old["dependency_inputs"]==11627 and old["dependency_plan_before"]["sha256"]==
                old["dependency_plan_after"]["sha256"]=="6f67e22560bc001fcdb314b3cbdfe8d562f357d9d5a513691692c66cf9b83269",
                "preserve_completed_dependency_scope")
        require(before["controller_commit"]==HEAD and "current_source_after" not in old,
                "original_controller_before_binding")
        _git_bytes,gitrow = pinned(GIT,GIT_SHA)
        _docs,docrow = pinned(DOC,DOC_SHA)
        result["git_tool_and_documentation"] = [gitrow,docrow]
        if PACK.exists():
            st=PACK.lstat();require(stat.S_ISREG(st.st_mode) and not PACK.is_symlink(),"current_pack_type")
            result["current_pack_stat_only"] = {"path":str(PACK),**{k:str(getattr(st,k)) for k in (*FIELDS,"st_blocks")}}
        else:
            result["current_pack_stat_only"] = {"path":str(PACK),"present":False}
        require(git(["rev-parse","HEAD"],"head-before").decode().strip()==HEAD,"later_controller_head")
        tree = git(["ls-tree","-rz",HEAD,"--",*SELECTION],"tree")
        rows = source_rows(before,tree)
        result["later_source_before"] = save(OUTPUT/"later-source-before.json",rows)
        require(not git(["status","--porcelain=v1","--untracked-files=all"],"status").strip(),"later_controller_dirty")
        require(git(["rev-parse","HEAD"],"head-after").decode().strip()==HEAD,"later_controller_head_changed")
        after = source_rows(before,tree)
        require(after==rows,"later_controller_changed_during_audit")
        result["later_source_after"] = save(OUTPUT/"later-source-after.json",after)
        require(pinned(OFFLINE/"result.json",RESULT_SHA)[1]==rrow and
                pinned(OFFLINE/"current-source-before.json.gz",BEFORE_SHA)[1]==brow,"original_receipt_changed")
        require(pinned(GIT,GIT_SHA)[1]==gitrow and pinned(DOC,DOC_SHA)[1]==docrow,"later_tool_changed")
        result["matched_current_controller_records"] = len(rows)
        result["separate_later_audit_matches_original_before"] = True
    except BaseException as error:
        result["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        try:
            after_loaded = actual_auditor_sources()
            result["actual_later_loaded_after"] = after_loaded
            require(loaded is not None and after_loaded==loaded,"later_auditor_source_changed")
        except BaseException as error:
            result["final_errors"].append({"phase":"later-auditor-source","type":type(error).__name__,"message":str(error)})
        result["commands"] = COMMANDS
        result["finished"] = now();result["elapsed_seconds"] = time.monotonic()-START
        result["read_bytes"] = READ_BYTES;result["free_final"] = shutil.disk_usage("/mnt/development").free
        result["effective_uid_final"] = os.geteuid()
        if result["elapsed_seconds"]>=SECONDS or result["free_final"]<FLOOR or result["effective_uid_final"]!=1001:
            result["final_errors"].append({"phase":"final-admission","message":"deadline_capacity_or_identity"})
        if result["primary_error"] is None and not result["final_errors"]:
            result["status"] = "PASS_LATER_CURRENT_CONTROLLER_AUDIT"
        saved = save(OUTPUT/"result.json",result)
        print(json.dumps({"status":result["status"],"result":saved,"matched_records":result.get("matched_current_controller_records"),
                          "graph_or_test_replays":0}))
    return 0 if result["status"]=="PASS_LATER_CURRENT_CONTROLLER_AUDIT" else 1

if __name__=="__main__":
    sys.exit(main())
