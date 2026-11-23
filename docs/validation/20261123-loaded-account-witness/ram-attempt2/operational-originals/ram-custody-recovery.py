#!/usr/bin/env python3
"""Audit-only custody recovery. Never invokes Go, a container run, or tests."""
import copy
import gzip
import hashlib
import importlib.util
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

ROOT = pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
BASE = ROOT/"Tools/AnyEngineValidation/loaded_account_witness/ram_graph.py"
BASE_SHA = "3b7b1802213811b57174e93e7de0ea52b712c4e76c34d0f89c14889eeba21ba3"
ORIGINAL = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-graph-attempt2")
OUT = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-attempt2-custody-recovery")
CID = "df5ca74d1fa13270c3813862753eef508f0bef80c27ebb9914b80f039644405c"
RAM = pathlib.Path("/dev/shm/pinkha-loaded-account-source-graph-20261123")
ORIGINAL_RESULT_SHA = "26b3d52fb6baad3b1c7e1d36eedadcb7b39ed50abb56187cf155860f70b15f53"
ORIGINAL_INSPECT_SHA = "518c904a9de9a23ccc315cbd9a1fbd51f4e44f152a52a9d837e37afde9c639b9"
TOTAL = 16*1024*1024

def require(value,reason):
    if not value:
        raise RuntimeError(reason)

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(65536),b""):
            h.update(b)
    return h.hexdigest()

def sizes(root):
    count=0
    for p in root.rglob("*"):
        require(not p.is_symlink(),"evidence_symlink")
        if p.is_file():
            count+=p.stat().st_size
    return count

def save(name,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
    require(len(raw)<512*1024 and sizes(ORIGINAL)+sizes(OUT)+len(raw)<=TOTAL,"combined_evidence_limit")
    p=OUT/name
    with p.open("xb") as f:
        os.chmod(p,0o600)
        if os.geteuid()==0:
            os.chown(p,1001,1002)
        require(p.stat().st_uid==1001,"private_recovery_file_owner")
        f.write(raw);f.flush();os.fsync(f.fileno())
    return {"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def bind():
    require(BASE.is_file() and not BASE.is_symlink() and digest(BASE)==BASE_SHA,"frozen_preserver_source")
    require(digest(ORIGINAL/"result.json")==ORIGINAL_RESULT_SHA,"original_failed_receipt_changed")
    require(digest(ORIGINAL/"container-before-cleanup.json")==ORIGINAL_INSPECT_SHA,"original_container_binding_changed")
    original=json.loads((ORIGINAL/"result.json").read_text())
    require(original["status"]=="FAILED" and original["primary_error"]["message"]=="source_query_stdout_limit","original_failure_identity")
    require(original["query"]["pid"]==3073131 and original["query"]["pgid"]==3073131,"original_query_ownership")
    require(original["ram_finalization"]["mounted"]["mount"]["mount_id"]=="738" and
            original["ram_finalization"]["mounted"]["mount"]["device"]=="0:71","original_ram_binding")
    for key in ("stdout","stderr"):
        item=original["query"][key]
        p=pathlib.Path(item["path"])
        require(p==ORIGINAL/(key+".log") and digest(p)==item["sha256"] and p.stat().st_size==int(item["st_size"]),"original_output_changed")
    spec=importlib.util.spec_from_file_location("original_ram_custody_helpers",BASE)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RAM_STATE=copy.deepcopy(original["ram_finalization"])
    module.ATTEMPT=OUT
    module.TOTAL_OUTPUT=TOTAL-sizes(ORIGINAL)
    require(module.TOTAL_OUTPUT>=1024*1024,"no_remaining_recovery_budget")
    module.ram_validate()
    return module,original

def group_absent(pgid):
    try:
        os.killpg(pgid,0)
        return False
    except ProcessLookupError:
        return True

def root_command(argv,seconds):
    require(os.getuid()==0,"privileged_custody_required")
    child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    record={"argv":argv,"pid":child.pid,"pgid":os.getpgid(child.pid),"primary_error":None,"cleanup_error":None}
    require(record["pgid"]==child.pid,"new_owned_observer_group")
    buffers={"stdout":bytearray(),"stderr":bytearray()}
    selector=selectors.DefaultSelector();started=time.monotonic()
    for name,stream in (("stdout",child.stdout),("stderr",child.stderr)):
        os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
    try:
        while selector.get_map():
            require(time.monotonic()-started<seconds,"privileged_operation_timeout")
            for key,_ in selector.select(0.1):
                b=os.read(key.fileobj.fileno(),65536)
                if not b:
                    selector.unregister(key.fileobj);continue
                remain=256*1024-sum(map(len,buffers.values()))
                buffers[key.data].extend(b[:max(0,remain)])
                require(len(b)<=remain,"privileged_operation_output_bound")
        record["returncode"]=child.wait(timeout=max(0.001,seconds-(time.monotonic()-started)))
        require(time.monotonic()-started<seconds,"privileged_operation_late")
    except BaseException as error:
        record["primary_error"]={"type":type(error).__name__,"message":str(error)}
    finally:
        try:
            for label,sig in (("term",signal.SIGTERM),("kill",signal.SIGKILL)):
                child.poll()
                if group_absent(child.pid):break
                os.killpg(child.pid,sig);record[label+"_sent"]=True
                end=time.monotonic()+3
                while time.monotonic()<end:
                    child.poll()
                    if group_absent(child.pid):break
                    time.sleep(0.05)
            record["owned_group_absent"]=group_absent(child.pid)
            require(record["owned_group_absent"],"new_privileged_observer_group_remains")
            record["returncode"]=child.wait(timeout=1)
        except BaseException as error:
            record["cleanup_error"]={"type":type(error).__name__,"message":str(error)}
        selector.close();child.stdout.close();child.stderr.close()
        record.update(stdout=bytes(buffers["stdout"]).decode("utf-8","replace"),
            stderr=bytes(buffers["stderr"]).decode("utf-8","replace"),elapsed_seconds=time.monotonic()-started)
    return record

def fresh_quiescence(module):
    observed=root_command(["docker","inspect",CID],15)
    require(observed["primary_error"] is None and observed["cleanup_error"] is None and observed["returncode"]==0,"current_container_inspection_failed")
    current=json.loads(observed["stdout"]);require(isinstance(current,list) and len(current)==1,"current_container_shape")
    value=current[0]
    old=json.loads(json.loads((ORIGINAL/"container-before-cleanup.json").read_text())["stdout"])[0]
    for field in ("Id","Name","Image","Path","Args","Config","HostConfig","Mounts"):
        require(value[field]==old[field],"current_container_binding_"+field)
    require(value["Id"]==CID and value["State"]["Running"] is False and value["State"]["Pid"]==0,"owned_container_not_stopped")
    members=[];denied=[]
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():continue
        try:
            text=(entry/"stat").read_text();fields=text[text.rfind(")")+2:].split()
            pid,pgid=int(entry.name),int(fields[2])
            if pid==3073171 or pgid in (3073131,3073290):
                members.append({"pid":str(pid),"pgid":str(pgid),"start_ticks":fields[19],"state":fields[0]})
        except FileNotFoundError:pass
        except PermissionError:denied.append(entry.name)
    require(not denied and not members,"original_process_custody_not_quiescent")
    require(group_absent(3073131) and group_absent(3073290),"original_group_still_exists")
    mount=module.ram_validate()
    return {"container_observation":observed,"container_state":value["State"],"original_processes":members,
        "process_scan_denied":denied,"original_groups_absent":True,"ram":mount,
        "meaning":"later_independent_quiescence_does_not_rewrite_original_cleanup_failure"}

def main(expected_source):
    require(os.getuid()==0 and os.geteuid()==0,"privileged_recovery_owner")
    require(digest(pathlib.Path(__file__).resolve())==expected_source,"frozen_recovery_source")
    require(shutil.disk_usage("/mnt/development").free>=1024**3+16*1024*1024,"recovery_disk_reserve")
    require(not OUT.exists(),"preserve_prior_recovery")
    OUT.mkdir(mode=0o700)
    os.chown(OUT,1001,1002)
    result={"protocol":"owned-ram-custody-recovery-v1","status":"FAILED","primary_error":None,
        "original_failure_sha256":ORIGINAL_RESULT_SHA,"original_query_status":"FAILED","original_cleanup_status":"FAILED",
        "actual_new_go_queries":0,"native_builds_tests":0,"frozen_source_sha256":expected_source}
    started=time.monotonic()
    signal.alarm(120)
    try:
        module,original=bind()
        result["initial_quiescence"]=fresh_quiescence(module)
        # File-only preservation runs with the original owner's effective IDs.
        # No child, privilege operation, Go, or container command runs in this block.
        prior_euid,prior_egid=os.geteuid(),os.getegid()
        try:
            os.setegid(1002);os.seteuid(1001)
            inventory=module.ram_inventory()
            inventory_receipt=module.save_map(OUT/"ram-inventory.json.gz",inventory)
            module.preserve_ram_inventory(inventory)
            require(not inventory["unexpected_payloads"],"unexpected_ram_payloads_preserved_mount_retained")
            proof={"original_failure_sha256":ORIGINAL_RESULT_SHA,"inventory":inventory_receipt,
                "archive":module.RAM_STATE["originals_archive"],"archive_readback":module.RAM_STATE["archive_readback"]}
            proof_receipt=save("preservation-readback.json",proof)
        finally:
            os.seteuid(prior_euid);os.setegid(prior_egid)
        result["preservation"]=proof_receipt
        require(digest(pathlib.Path(proof_receipt["path"]))==proof_receipt["sha256"],"preservation_receipt_changed")
        require(digest(pathlib.Path(proof["archive"]["path"]))==proof["archive"]["sha256"],"preserved_archive_changed")
        require(module.ram_inventory()==inventory,"ram_changed_after_full_readback")
        directory_fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
        result["pre_unmount_quiescence"]=fresh_quiescence(module)
        command=root_command(["umount",str(RAM)],10)
        result["normal_unmount"]=command
        require(command["primary_error"] is None and command["cleanup_error"] is None and command["returncode"]==0,"normal_unmount_failed")
        require(module.ram_mount() is None,"original_mount_still_present")
        require(module.directory_identity(RAM)==original["ram_finalization"]["underlying_directory"] and not any(RAM.iterdir()),"underlying_owned_directory_changed")
        RAM.rmdir()
        result["ram_absent"]=not RAM.exists()
        require(digest(BASE)==BASE_SHA and digest(ORIGINAL/"result.json")==ORIGINAL_RESULT_SHA,"originals_changed")
        result["status"]="PASS_LATER_CUSTODY_RECOVERY"
    except BaseException as error:
        result["primary_error"]={"type":type(error).__name__,"message":str(error)}
    signal.alarm(0)
    result["elapsed_seconds"]=time.monotonic()-started
    if result["elapsed_seconds"]>=120:
        result["final_deadline_error"]=True;result["status"]="FAILED"
    result["ram_still_exists"]=RAM.exists()
    result["combined_evidence_bytes"]=sizes(ORIGINAL)+sizes(OUT)
    result["free_final"]=shutil.disk_usage("/mnt/development").free
    if result["free_final"]<1024**3:
        result["final_capacity_error"]=True;result["status"]="FAILED"
    saved=save("result.json",result)
    print(json.dumps({"status":result["status"],"receipt":saved,"ram_still_exists":result["ram_still_exists"],"free_final":result["free_final"]}))
    return 0 if result["status"]=="PASS_LATER_CUSTODY_RECOVERY" else 1

def interrupted(signum,_frame):
    raise TimeoutError("owned_custody_recovery_deadline_or_signal_"+str(signum))

if __name__=="__main__":
    require(len(sys.argv)==2,"expected_source_sha_required")
    signal.signal(signal.SIGALRM,interrupted)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    sys.exit(main(sys.argv[1]))
