#!/usr/bin/env python3
"""One bounded native build and four loaded-account controls; retain RAM custody."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import pathlib
import pwd
import re
import resource
import selectors
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone

ORDINARY_UID = 1001
ORDINARY_GID = 1001
ORDINARY_GROUPS = [4, 24, 27, 30, 104, 1001]
def process_credentials():
    return {"uids":list(os.getresuid()),"gids":list(os.getresgid()),
            "groups":sorted(os.getgroups())}

def adopt_owner_for_cleanup():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("isolated_no_bytecode_python_entry_required")
    initial = process_credentials()
    if initial!={"uids":[0,0,0],"gids":[0,0,0],"groups":[0]}:
        raise RuntimeError("expected_privileged_entry_identity")
    if os.environ.get("SUDO_UID")!="1001" or os.environ.get("SUDO_GID")!="1001":
        raise RuntimeError("expected_original_sudo_owner")
    account = pwd.getpwuid(ORDINARY_UID)
    if account.pw_gid!=ORDINARY_GID or sorted(os.getgrouplist(account.pw_name,ORDINARY_GID))!=ORDINARY_GROUPS:
        raise RuntimeError("original_ordinary_groups_changed")
    os.setgroups(ORDINARY_GROUPS)
    os.setresgid(ORDINARY_GID,ORDINARY_GID,ORDINARY_GID)
    os.setresuid(ORDINARY_UID,ORDINARY_UID,0)
    final = process_credentials()
    if final!={"uids":[1001,1001,0],"gids":[1001,1001,1001],"groups":ORDINARY_GROUPS}:
        raise RuntimeError("ordinary_source_owner_adoption_failed")
    return {"entry":initial,"adopted":final,"persistent_permissions_changed":False,
            "saved_uid_scope":"only_registered_child_stop_owned"}

ENTRY_CREDENTIALS = adopt_owner_for_cleanup() if __name__ == "__main__" else None

HERE = pathlib.Path(__file__).resolve().parent
CONTROL = HERE.parents[2]
HEART = pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-loaded-account-witness-20261123")
SYNC = pathlib.Path("/mnt/development/projects/worktrees/any-sync-loaded-account-witness-20261123")
HEART_SHA = "24dc6393b30e6d1d80ec28ff624060af9bb4327a"
SYNC_SHA = "c005bd6cde8d8f8a6007c35f06894f3d89f9f07c"
EVIDENCE = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
ATTEMPT = EVIDENCE / "native-attempt1"
PROOF = CONTROL / "docs/validation/20261123-loaded-account-witness/offline-qualified"
CACHE = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/attempt4/cache")
CACHE_REAL = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache")
GOROOT = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/toolchains/go1.26.5/go")
GO = GOROOT / "bin/go"
LIBDIR = pathlib.Path("/mnt/development/projects/worktrees/anytype-heart-semantic-page-20261123/deps/libs/linux-arm64-musl")
LIBRARY = LIBDIR / "libtantivy_go.a"
IMAGE = "sha256:f2f98726820d0342055351c6e9d36e705f5bfffb3dd53ff556325114b08afb6d"
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg pinkha_loaded_account_witness pinkha_loaded_account_witness_acceptance"
METHODS = [
 "TestLoadedAccountWitnessBindsActualAccountSessionAndHead",
 "TestLoadedAccountWitnessRefusesUnboundSessionsAndLoadFallback",
 "TestLoadedAccountWitnessACLAndSessionCancellationReleaseActualLocks",
 "TestLoadedAccountWitnessRejectsForeignOwnerStoredHeadAndStoppedApp",
]
START_FREE = 2_950_000_000
STOP_FREE = 2_600_000_000
FINAL_FREE = 2_500_000_000
MEM_START = 9 * 1024**3
MEM_STOP = 1024**3
MEM_COMMAND_START = 5 * 1024**3
ADDRESS_LIMIT = 512 * 1024**2
ATTEMPT_LIMIT = 160 * 1024**2
METADATA_LIMIT = 16 * 1024**2
CACHE_SOURCE_MAX = 15 * 1024**3 // 4
CACHE_ENTRY_MAX = 131072
CACHE_MANIFEST_RAW_MAX = 32 * 1024**2
CACHE_MANIFEST_GZIP_MAX = 4 * 1024**2
BUILD_SECONDS = 900
TEST_SECONDS = 240
GO_TEST_TIMEOUT = "210s"
BINARY_MAX = 256 * 1024**2
DOCKER = ["sudo","-n","docker"]
RAM_SPECS = {
 "cache":{"path":pathlib.Path("/dev/shm/pinkha-loaded-account-native-cache-20261123"),
          "bytes":17*1024**3//4,"inodes":262144,"noexec":True},
 "tmp":{"path":pathlib.Path("/dev/shm/pinkha-loaded-account-native-tmp-20261123"),
        "bytes":512*1024**2,"inodes":32768,"noexec":False},
 "products":{"path":pathlib.Path("/dev/shm/pinkha-loaded-account-native-products-20261123"),
             "bytes":BINARY_MAX,"inodes":1024,"noexec":False},
}
HELPER_SHA = "cd5e46269f566870489f338471f9c63e14dfd6a8dd842be221fed5b1cccff6cf"
PLAN_SHA = "6f67e22560bc001fcdb314b3cbdfe8d562f357d9d5a513691692c66cf9b83269"
QUALIFICATION_SHA = "2fe6dc18b127cf6411a9b458230ab50523ac8eaa49146ab70eee884b8871eef8"
GENERATED_SHA = "749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715"
RAM_STATE = {}
COMMANDS = []
STAGE = None
STAGE_DIR = None
CURRENT = None
PROCESS = None
AUDIT = None
META_WRITTEN = 0
READ_BYTES = 0
FIXED_READ_BYTES = 0
OP_INDEX = 0
FROZEN = None

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def now():
    return datetime.now(timezone.utc).isoformat()

def free():
    return shutil.disk_usage("/mnt/development").free

def memory_available():
    fields = dict(line.split(":",1) for line in pathlib.Path("/proc/meminfo").read_text().splitlines())
    return int(fields["MemAvailable"].split()[0]) * 1024

def exact_private_dir(path):
    value = path.lstat()
    require(path.resolve()==path and stat.S_ISDIR(value.st_mode) and
            stat.S_IMODE(value.st_mode) in (0o700,0o2700) and value.st_uid==1001,
            "owned_private_directory")
    return {k:str(getattr(value,k)) for k in ("st_dev","st_ino","st_mode","st_uid","st_gid")}

def attempt_usage():
    result={"total":0,"metadata":0,"private_fixture":0,"raw_command_logs":0,"entries":0}
    if not ATTEMPT.exists():return result
    for root,dirs,files in os.walk(ATTEMPT,followlinks=False):
        for name in dirs+files:
            path=pathlib.Path(root)/name;value=path.lstat()
            result["entries"]+=1
            require(result["entries"]<=65536,"native_attempt_entry_budget")
            require(not stat.S_ISLNK(value.st_mode),"attempt_contains_symlink")
            if stat.S_ISREG(value.st_mode):
                result["total"]+=value.st_size
                kind=("private_fixture" if path.is_relative_to(ATTEMPT/"private") else
                      "raw_command_logs" if path.suffix in (".stdout",".stderr") else "metadata")
                result[kind]+=value.st_size
            else:require(stat.S_ISDIR(value.st_mode),"attempt_contains_special_entry")
    return result

def used_attempt():
    return attempt_usage()["total"]

def resource_guard(*,start=False,final=False,check_attempt=True):
    observed={"disk_free":free(),"memory_available":memory_available()}
    minimum = START_FREE if start else (FINAL_FREE if final else STOP_FREE)
    require(observed["disk_free"]>=minimum,"native_disk_resource_gate")
    require(observed["memory_available"]>=(MEM_START if start else MEM_STOP),"native_memory_resource_gate")
    if check_attempt:
        observed["attempt_usage"]=attempt_usage()
        observed["attempt_bytes"]=observed["attempt_usage"]["total"]
        require(observed["attempt_bytes"]<=ATTEMPT_LIMIT,"native_attempt_storage_budget")
        require(observed["attempt_usage"]["metadata"]<=METADATA_LIMIT,"native_combined_metadata_budget")
    return observed

def strict(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,"duplicate_json_key")
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite_json")))

def raw_file(path,raw,*,metadata=True):
    global META_WRITTEN
    require(type(raw) is bytes and not path.exists() and not path.is_symlink(),"preserve_original_output")
    if metadata:
        require(attempt_usage()["metadata"]+len(raw)<=METADATA_LIMIT-1024*1024,"native_metadata_budget_with_final_reserve")
    require(used_attempt()+len(raw)<=ATTEMPT_LIMIT,"native_attempt_output_budget")
    with path.open("xb") as out:
        os.chmod(path,0o600);out.write(raw);out.flush();os.fsync(out.fileno())
    if metadata:META_WRITTEN+=len(raw)
    return {"path":str(path),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def save(path,value,*,packed=False):
    raw=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()
    require(len(raw)<=6*1024**2,"native_expanded_metadata_budget")
    if packed:
        encoded=gzip.compress(raw,compresslevel=6,mtime=0)
        require(len(encoded)<=2*1024**2,"native_gzip_metadata_budget")
    else:encoded=raw
    result=raw_file(path,encoded)
    if packed:result.update(encoding="gzip-json",expanded_bytes=len(raw),expanded_sha256=hashlib.sha256(raw).hexdigest())
    return result

def file_row(path,*,maximum=256*1024**2,guard=True):
    global READ_BYTES
    if guard:resource_guard(check_attempt=False)
    before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink() and before.st_size<=maximum,
            "native_input_regular_size")
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    digest=hashlib.sha256()
    try:
        first=os.fstat(fd)
        require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(first,k) for k in FIELDS),
                "native_input_open_identity")
        while True:
            chunk=os.read(fd,1024*1024)
            if not chunk:break
            if guard:resource_guard(check_attempt=False)
            digest.update(chunk);READ_BYTES+=len(chunk)
        last=os.fstat(fd)
    finally:os.close(fd)
    after=path.lstat()
    require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(last,k) for k in FIELDS)==
            tuple(getattr(after,k) for k in FIELDS),"native_input_changed_during_read")
    return dict(path=str(path),sha256=digest.hexdigest(),**{k:str(getattr(after,k)) for k in FIELDS})

def fixed_bytes(path,digest,maximum):
    global FIXED_READ_BYTES
    row=file_row(path,maximum=maximum)
    require(row["sha256"]==digest,"fixed_input_digest")
    raw=path.read_bytes();FIXED_READ_BYTES+=len(raw)
    require(len(raw)<=maximum and hashlib.sha256(raw).hexdigest()==digest,"fixed_input_reread")
    require(FIXED_READ_BYTES<=32*1024**2,"fixed_input_read_budget")
    return raw

def load_module(path,digest,name):
    fixed_bytes(path,digest,128*1024)
    spec=importlib.util.spec_from_file_location(name,path)
    require(spec is not None and spec.loader is not None,"actual_module_spec")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module)
    require(pathlib.Path(module.__file__).resolve()==path,"actual_module_origin")
    require(file_row(path)["sha256"]==digest,"module_changed_during_import")
    return module

def load_process_helper():
    global PROCESS
    PROCESS=load_module(HERE/"ram_projected_graph.py",HELPER_SHA,"loaded_account_native_owned_process")
    require(PROCESS.ENTRY_CREDENTIALS is None and not PROCESS.OWNED_CHILDREN,"old_query_not_executed")
    # Two fixed adapter bindings only: current raw-receipt root and actual
    # process-local entry receipt. No old source-query function is invoked.
    PROCESS.ENTRY_CREDENTIALS=ENTRY_CREDENTIALS
    PROCESS.ATTEMPT=STAGE_DIR/"operations"
    return {"source_sha256":HELPER_SHA,"bindings":["ENTRY_CREDENTIALS","ATTEMPT"],
            "source_query_invoked":False,"native_helper_source_modified":False}

def operation(argv,label,timeout=20,*,allow_nonzero=False):
    global OP_INDEX
    OP_INDEX+=1
    name=str(OP_INDEX).zfill(3)+"-"+label
    result=PROCESS.operation_observe(argv,name,timeout=timeout)
    if not allow_nonzero:require(result.returncode==0,"operation_nonzero_"+label)
    return result

def git(root,*args):
    result=operation(["/usr/bin/git","-c","core.packedGitWindowSize=16m",
        "-c","core.packedGitLimit=64m","-C",str(root),*args],"git",timeout=30)
    return result.stdout

def loaded_sources():
    allowed={pathlib.Path(__file__).resolve(),HERE/"native_audit.py",HERE/"ram_projected_graph.py"}
    result={}
    for name,module in sorted(sys.modules.items()):
        filename=getattr(module,"__file__",None)
        if not filename:continue
        path=pathlib.Path(filename).resolve()
        if path.is_relative_to(CONTROL.parent):
            require(path in allowed,"unexpected_repository_python_import")
            result[name]=file_row(path)
    require(set(result)=={"__main__","loaded_account_native_owned_process","loaded_account_native_auditor"},
            "native_actual_module_closure")
    return result

FIELDS = ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")

COLUMNS = ("path","sha256",*FIELDS,"resolved_path_or_same","generated_presence")

def decode_plan(encoded):
    table = encoded["inputs"]
    require(set(table)=={"schema","columns","rows"} and table["schema"]=="lossless-input-columns-v1" and
            table["columns"]==list(COLUMNS) and isinstance(table["rows"],list),"input_column_header")
    inputs = {}
    previous = None
    for values in table["rows"]:
        require(isinstance(values,list) and len(values)==len(COLUMNS),"input_column_row_width")
        path,digest = values[:2]
        require(isinstance(path,str) and path not in inputs and (previous is None or previous<path),
                "input_column_path_collision_or_order")
        require(isinstance(digest,str) and re.fullmatch(r"[0-9a-f]{64}",digest),"input_column_digest")
        require(all(isinstance(v,str) and re.fullmatch(r"[0-9]+",v) for v in values[2:11]),
                "input_column_integer_string")
        resolved,presence = values[11:13]
        require(resolved is None or (isinstance(resolved,str) and resolved!=path),"input_column_resolved_path")
        require(type(presence) is int and presence in (0,1,2),"input_column_presence")
        value = dict(path=path,sha256=digest,**dict(zip(FIELDS,values[2:11])),
                     resolved_path=path if resolved is None else resolved)
        if presence:
            value["generated_test_main"] = presence==2
        inputs[path] = value
        previous = path
    result = dict(encoded)
    result["inputs"] = inputs
    return result

def encode_plan(plan):
    rows = []
    base_keys = {"path","sha256","resolved_path",*FIELDS}
    for path,value in sorted(plan["inputs"].items()):
        require(path==value["path"] and set(value) in (base_keys,base_keys|{"generated_test_main"}),
                "input_column_schema")
        require(all(isinstance(value[k],str) for k in base_keys),"input_column_string_type")
        if "generated_test_main" in value:
            require(type(value["generated_test_main"]) is bool,"generated_presence_type")
        rows.append([path,value["sha256"],*[value[k] for k in FIELDS],
                     None if value["resolved_path"]==path else value["resolved_path"],
                     0 if "generated_test_main" not in value else (2 if value["generated_test_main"] else 1)])
    encoded = dict(plan)
    encoded["inputs"] = {"schema":"lossless-input-columns-v1","columns":list(COLUMNS),"rows":rows}
    require(decode_plan(encoded)==plan,"input_column_roundtrip")
    return encoded


def load_frozen_inputs(expected_digest):
    raw=fixed_bytes(HERE/"native-source.json",expected_digest,1024*1024)
    manifest=strict(raw)
    require(manifest["schema"]=="loaded-account-native-profile-inputs-v1" and
            manifest["heart_commit"]==HEART_SHA and manifest["any_sync_commit"]==SYNC_SHA and
            manifest["selected_methods"]==METHODS and manifest["old_methods_selected"]==0,
            "native_fixed_input_contract")
    require(manifest["source_graph_sha256"]==PLAN_SHA and
            manifest["source_stage_qualification_sha256"]==QUALIFICATION_SHA and
            manifest["process_helper_sha256"]==HELPER_SHA,"native_fixed_proof_binding")
    require(manifest["native_source_admission"] is False and
            manifest["semantic_completeness"] is False and manifest["destination_writes"] is False,
            "native_scope_stays_bounded")
    support=manifest["compiler_support"]
    require(support=={"state":"BLOCKED_COMPILER_SUPPORT","image":IMAGE,
                     "original_result_sha256":"ca681802575e0fd0d135be251184b89949dde0f46a957755ff2c019fa5013a76"},
            "fixed_image_compiler_failure_binding")
    original=strict(fixed_bytes(HERE/"native-compiler-support.json",
        support["original_result_sha256"],32*1024))
    require(original["status"]=="PASS_IMMUTABLE_IMAGE_TOOL_INVENTORY" and
            original["image"]==IMAGE and original["gcc_present"] is False and
            original["gpp_present"] is False and original["merged_tools"]=={} and
            original["native_builds"]==0 and original["tests"]==0,
            "actual_fixed_image_compiler_tools_absent")
    return manifest

def source_state(expected_controller):
    require(re.fullmatch(r"[0-9a-f]{40}",expected_controller) is not None,"controller_commit_type")
    heads={}
    for root,commit in ((HEART,HEART_SHA),(SYNC,SYNC_SHA),(CONTROL,expected_controller)):
        require(git(root,"rev-parse","HEAD").decode().strip()==commit,"native_current_head_changed")
        require(not git(root,"status","--porcelain=v1","--untracked-files=all").strip(),"native_current_tree_dirty")
        heads[str(root)]=commit
    require(CACHE.is_symlink() and os.readlink(CACHE)=="../cache" and CACHE.resolve()==CACHE_REAL,
            "original_cache_spelling_changed")
    records={}
    for item in git(CONTROL,"ls-tree","-rz",expected_controller,"--",
                    "Tools/AnyEngineValidation/loaded_account_witness").split(b"\0"):
        if not item:continue
        header,name=item.split(b"\t",1);mode,kind,oid=header.split()
        relative=name.decode();path=CONTROL/relative
        require(kind==b"blob" and mode in (b"100644",b"100755") and path.resolve()==path,
                "current_controller_tree_shape")
        raw=path.read_bytes()
        require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==oid.decode(),
                "current_controller_physical_git_difference")
        current=file_row(path)
        require(bool(int(current["st_mode"])&0o111)==(mode==b"100755"),"current_controller_git_mode")
        records[relative]=dict(current,git_blob=oid.decode(),git_mode=mode.decode())
    require(str(pathlib.Path(__file__).relative_to(CONTROL)) in records,"actual_native_controller_not_bound")
    authored={}
    for path,expected in FROZEN["authored_native_inputs"].items():
        actual=file_row(pathlib.Path(path))
        require(actual==expected,"frozen_authored_native_input_changed")
        authored[path]=actual
    return {"heads":heads,"controller_inputs":records,"authored_native_inputs":authored,
            "loaded_python":loaded_sources()}

def original_graph():
    q=strict(fixed_bytes(PROOF/"qualification.json",QUALIFICATION_SHA,128*1024))
    require(q["status"]=="PASS_COMPOSED_SOURCE_STAGE" and q["native_build_admission"] is False and
            q["four_native_controls"]=="NOT_RUN","retained_source_stage_scope")
    raw=fixed_bytes(PROOF/"offline/dependency-plan-before.json.gz",PLAN_SHA,2*1024**2)
    expanded=gzip.decompress(raw)
    require(len(expanded)<=6*1024**2,"retained_encoded_graph_bound")
    plan=decode_plan(strict(expanded))
    require(len(plan["inputs"])==11627 and len(plan["packages"])==1455 and len(plan["modules"])==204,
            "retained_graph_cardinality")
    generated=[(p,r) for p,r in plan["inputs"].items() if r.get("generated_test_main") is True]
    require(len(generated)==1 and generated[0][1]["sha256"]==GENERATED_SHA and
            int(generated[0][1]["st_size"])==3282,"retained_generated_template_identity")
    fixed_bytes(PROOF/"query/generated-test-main.go",GENERATED_SHA,128*1024)
    return plan

def dependency_state(plan):
    inputs={}
    for name,expected in sorted(plan["inputs"].items()):
        if expected.get("generated_test_main") is True:
            # This is retained original metadata only. The native build's own
            # generated cache entry is captured separately after its real build.
            inputs[name]=dict(expected)
            continue
        path=pathlib.Path(name)
        actual=file_row(path)
        actual["resolved_path"]=str(path.resolve())
        if "generated_test_main" in expected:actual["generated_test_main"]=False
        require(actual==expected,"native_dependency_differs_from_qualified_later_row")
        inputs[name]=actual
    current=dict(plan,inputs=inputs)
    return encode_plan(current)

def tool_state():
    tools={}
    for name,expected in sorted(FROZEN["available_tool_inputs"].items()):
        actual=file_row(pathlib.Path(name))
        require(actual==expected,"native_available_tool_identity_changed")
        tools[name]=actual
    require(str(GO) in tools and str(LIBRARY) in tools,"native_go_or_tantivy_pin_missing")
    require(tools[str(GO)]["sha256"]=="22201b57b855105df064a291863c3fc04f22a7431187a9205122aff42a0c825b" and
            tools[str(LIBRARY)]["sha256"]=="efee68b0fdf23fd8c1c630f10f4cad497bbbcb7372b6b985933324ebe730a601",
            "native_primary_tool_pin")
    return {"available_pinned_inputs":tools,
            "every_available_tool_executed_or_loaded":False,
            "top_level_go_and_actual_test_binary_bound_separately":True}

def snapshot(side,expected_controller,plan):
    state={"source":source_state(expected_controller),"dependencies":dependency_state(plan),"tools":tool_state()}
    refs={}
    for key,value in state.items():
        refs[key]=save(STAGE_DIR/(key+"-"+side+".json.gz"),value,packed=True)
    return state,refs

def generated_after_build():
    path=RAM_SPECS["cache"]["path"]/GENERATED_SHA[:2]/(GENERATED_SHA+"-d")
    actual=file_row(path,maximum=128*1024)
    require(actual["sha256"]==GENERATED_SHA and actual["st_size"]=="3282","actual_build_generated_main_changed")
    raw=path.read_bytes()
    preserved=raw_file(STAGE_DIR/"generated-test-main.go",raw)
    return {"origin":"actual native build cache after compile","actual_row":actual,"preserved":preserved,
            "retained_query_template_sha256":GENERATED_SHA,
            "historical_ram_inode_reused":False}

def elf_binary():
    path=RAM_SPECS["products"]["path"]/"loaded-account.test"
    value=file_row(path,maximum=BINARY_MAX)
    require(int(value["st_size"])>0 and int(value["st_nlink"])==1 and int(value["st_mode"])&0o111,
            "native_test_binary_shape")
    with path.open("rb") as source:header=source.read(64)
    require(header[:6]==b"\x7fELF\x02\x01" and struct.unpack_from("<H",header,18)[0]==183,
            "native_test_binary_not_arm64_elf")
    return value


def mount_record(path):
    found=[]
    for line in pathlib.Path("/proc/self/mountinfo").read_text().splitlines():
        left,right=line.split(" - ",1);a=left.split();b=right.split()
        if a[4]==str(path):
            found.append({"id":a[0],"parent_id":a[1],"device":a[2],"root":a[3],
                "mountpoint":a[4],"options":a[5],"filesystem":b[0],"source":b[1],"super_options":b[2]})
        require(not a[4].startswith(str(path)+"/"),"unexpected_nested_ram_mount")
    require(len(found)<=1,"duplicate_owned_ram_mount")
    return found[0] if found else None

def directory_id(path):
    value=path.lstat()
    require(stat.S_ISDIR(value.st_mode) and not path.is_symlink(),"ram_directory_shape")
    return {k:str(getattr(value,k)) for k in ("st_dev","st_ino","st_mode","st_uid","st_gid")}

def validate_ram(name,*,adopt=False):
    spec=RAM_SPECS[name];path=spec["path"];state=RAM_STATE[name]
    require(path.resolve()==path and directory_id(path.parent)==state["parent"],"ram_parent_relocated")
    current=mount_record(path)
    require(current is not None and current["filesystem"]=="tmpfs" and
            current["source"]==path.name,"ram_mount_origin")
    flags=set(current["options"].split(","))
    require({"rw","nodev","nosuid"}<=flags and ("noexec" in flags)==spec["noexec"],"ram_mount_flags")
    identity=directory_id(path)
    require(identity["st_uid"]=="1001" and identity["st_gid"]=="1001" and
            int(identity["st_mode"])==(stat.S_IFDIR|0o700),"ram_private_owner")
    major,minor=map(int,current["device"].split(":"))
    require(int(identity["st_dev"])==os.makedev(major,minor),"ram_device_identity")
    fs=os.statvfs(path)
    require(fs.f_frsize*fs.f_blocks==spec["bytes"] and fs.f_files==spec["inodes"],"ram_hard_capacity")
    stable={"mount":current,"identity":identity}
    if adopt:
        require("mounted" not in state,"ram_already_adopted")
        state["mounted"]=stable
    else:require(stable==state["mounted"],"ram_mount_identity_changed")
    return dict(stable,capacity=spec["bytes"],free_bytes=fs.f_frsize*fs.f_bavail,
                inodes=spec["inodes"],free_inodes=fs.f_favail)

def ram_all():
    return {name:validate_ram(name) for name in RAM_SPECS}

def prepare_ram():
    resource_guard(start=True)
    for name,spec in RAM_SPECS.items():
        path=spec["path"]
        require(path.parent==pathlib.Path("/dev/shm") and path.parent.resolve()==path.parent,
                "fixed_ram_parent")
        require(not path.exists() and not path.is_symlink() and mount_record(path) is None,
                "preserve_existing_ram")
        parent=directory_id(path.parent)
        require(parent["st_uid"]=="0" and int(parent["st_mode"])==(stat.S_IFDIR|0o1777),
                "native_ram_parent_identity")
        path.mkdir(mode=0o700)
        RAM_STATE[name]={"created":True,"parent":parent,"underlying":directory_id(path)}
        options="size="+str(spec["bytes"])+",nr_inodes="+str(spec["inodes"])+",mode=0700,uid=1001,gid=1001,nosuid,nodev"
        if spec["noexec"]:options+=",noexec"
        operation(["sudo","-n","mount","-t","tmpfs","-o",options,path.name,str(path)],"ram-mount-"+name)
        validate_ram(name,adopt=True)
        require(not any(path.iterdir()),"fresh_ram_not_empty")
        save(STAGE_DIR/("ram-created-"+name+".json"),RAM_STATE[name])
    (RAM_SPECS["tmp"]["path"]/"gopath").mkdir(mode=0o700)
    return ram_all()

def cache_source_inventory(deadline):
    root=CACHE_REAL/"go-build"
    require(root.resolve()==root and root.is_dir() and not root.is_symlink(),"original_cache_root")
    entries={}
    for base,dirs,files in os.walk(root,followlinks=False):
        require(time.monotonic()<deadline,"cache_inventory_deadline")
        resource_guard(check_attempt=False)
        dirs.sort();files.sort()
        for name in dirs+files:
            path=pathlib.Path(base)/name;relative=path.relative_to(root).as_posix()
            require(len(path.relative_to(root).parts)<=3 and "\0" not in relative and "\\" not in relative,
                    "cache_entry_path")
            value=path.lstat()
            require(stat.S_ISDIR(value.st_mode) or
                    (stat.S_ISREG(value.st_mode) and value.st_nlink==1),"cache_entry_type_or_alias")
            require(not path.is_symlink() and path.resolve()==path,"cache_entry_relocated")
            entries[relative]={k:str(getattr(value,k)) for k in FIELDS}
            require(len(entries)<=CACHE_ENTRY_MAX,"cache_entry_count")
    logical=sum(int(v["st_size"]) for v in entries.values() if stat.S_ISREG(int(v["st_mode"])))
    require(logical<=CACHE_SOURCE_MAX,"original_cache_copy_budget")
    return entries,logical

def copy_cache():
    global META_WRITTEN
    started=time.monotonic();deadline=started+120
    before,total=cache_source_inventory(deadline)
    target=RAM_SPECS["cache"]["path"]
    require(not any(target.iterdir()),"cache_copy_target_not_empty")
    manifest=STAGE_DIR/"cache-copy-original.jsonl.gz"
    expanded=0;files=0;copied=0
    with manifest.open("xb") as raw:
        os.chmod(manifest,0o600)
        with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0) as packed:
            for relative,expected in sorted(before.items()):
                require(time.monotonic()<deadline,"cache_copy_deadline")
                resource_guard()
                source=CACHE_REAL/"go-build"/relative;destination=target/relative
                require(not destination.exists() and not destination.is_symlink(),"cache_destination_exists")
                if stat.S_ISDIR(int(expected["st_mode"])):
                    destination.mkdir(mode=0o700)
                    record={"path":relative,"type":"directory","original":expected,"copy_mode":"0700"}
                else:
                    require(int(expected["st_size"])<=256*1024**2,"cache_single_file_budget")
                    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
                    digest=hashlib.sha256();count=0
                    try:
                        require({k:str(getattr(os.fstat(fd),k)) for k in FIELDS}==expected,"cache_open_changed")
                        with destination.open("xb") as out:
                            os.chmod(destination,0o600)
                            while True:
                                require(time.monotonic()<deadline,"cache_copy_deadline")
                                resource_guard(check_attempt=False)
                                chunk=os.read(fd,1024*1024)
                                if not chunk:break
                                out.write(chunk);digest.update(chunk);count+=len(chunk)
                            out.flush();os.fsync(out.fileno())
                        require({k:str(getattr(os.fstat(fd),k)) for k in FIELDS}==expected,"cache_source_changed")
                    finally:os.close(fd)
                    require(count==int(expected["st_size"]),"cache_copied_size")
                    readback=file_row(destination)
                    require(readback["sha256"]==digest.hexdigest(),"cache_independent_copy_readback")
                    record={"path":relative,"type":"file","original":expected,
                            "sha256":digest.hexdigest(),"copy":readback}
                    files+=1;copied+=count
                line=(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n").encode()
                expanded+=len(line);require(expanded<=CACHE_MANIFEST_RAW_MAX,"cache_manifest_expanded_budget")
                packed.write(line);packed.flush()
                require(raw.tell()<=CACHE_MANIFEST_GZIP_MAX,"cache_manifest_compressed_budget")
            packed.flush()
        raw.flush();os.fsync(raw.fileno())
    after,after_total=cache_source_inventory(deadline)
    require(before==after and total==after_total==copied,"original_cache_changed_during_copy")
    require(time.monotonic()<deadline,"cache_copy_late_completion")
    meta=file_row(manifest,maximum=CACHE_MANIFEST_GZIP_MAX)
    META_WRITTEN+=int(meta["st_size"])
    require(attempt_usage()["metadata"]<=METADATA_LIMIT-1024*1024,"cache_manifest_combined_metadata_budget")
    return {"status":"PASS_PRIVATE_COPY","source_root":str(CACHE_REAL/"go-build"),
        "destination_root":str(target),"source_entries":len(before),"files":files,"copied_bytes":copied,
        "source_tuple_before_after_equal":True,"every_copied_file_independently_read_back":True,
        "original_cache_written":False,"original_cache_evicted":False,"manifest":meta,
        "manifest_expanded_bytes":expanded,"elapsed_seconds":time.monotonic()-started,
        "compiled_product_acceptance":False}

def ram_output_inventory():
    result={}
    columns=["relative_path","kind","sha256",*FIELDS]
    for name in ("tmp","products"):
        root=RAM_SPECS[name]["path"];validate_ram(name)
        rows=[];total=0
        for base,dirs,files in os.walk(root,followlinks=False):
            dirs.sort();files.sort()
            for entry in dirs+files:
                path=pathlib.Path(base)/entry;relative=path.relative_to(root).as_posix()
                value=path.lstat()
                require(not path.is_symlink() and (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)),
                        "ram_output_unexpected_entry")
                if stat.S_ISREG(value.st_mode):
                    current=file_row(path,maximum=RAM_SPECS[name]["bytes"])
                    total+=int(current["st_size"]);kind="file";digest=current["sha256"]
                else:
                    current={k:str(getattr(value,k)) for k in FIELDS};kind="directory";digest=None
                rows.append([relative,kind,digest,*[current[k] for k in FIELDS]])
                require(len(rows)<=RAM_SPECS[name]["inodes"],"ram_output_inode_bound")
        rows.sort(key=lambda value:value[0])
        result[name]={"root":str(root),"schema":"complete-ram-output-columns-v1",
            "columns":columns,"entries":rows,"logical_bytes":total,"retained_in_ram":True,
            "durable_external_custody_complete":False}
    return result


def environment():
    work=ATTEMPT/"work"
    return {
        "CGO_ENABLED":"1","CC":"gcc","CXX":"g++","GOOS":"linux","GOARCH":"arm64",
        "GOMAXPROCS":"1","GOMEMLIMIT":"3072MiB","GOTOOLCHAIN":"local","GOWORK":"off",
        "GOFLAGS":"-mod=readonly -p=1","GOEXPERIMENT":"","GOPROXY":"off","GOSUMDB":"off",
        "GOMODCACHE":str(CACHE/"go-mod"),"GOCACHE":str(CACHE/"go-build"),
        "GOPATH":str(work/"gopath"),"GOTMPDIR":str(work),"TMPDIR":str(work),
        "HOME":str(work/"home"),"CGO_LDFLAGS":"-L"+str(LIBDIR),
        "PATH":str(GOROOT/"bin")+":/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT":str(ATTEMPT/"private/fixtures"),
    }

def container_mounts(build):
    return [
        (HEART,HEART,False),(SYNC,SYNC,False),(HERE,HERE,False),(GOROOT,GOROOT,False),
        (CACHE_REAL/"go-mod",CACHE/"go-mod",False),
        (RAM_SPECS["cache"]["path"],CACHE/"go-build",build),
        (LIBDIR,LIBDIR,False),
        (RAM_SPECS["tmp"]["path"],ATTEMPT/"work",True),
        (RAM_SPECS["tmp"]["path"],pathlib.Path("/tmp"),True),
        (RAM_SPECS["products"]["path"],ATTEMPT/"products",build),
        (ATTEMPT/"private/fixtures",ATTEMPT/"private/fixtures",True),
        (ATTEMPT/"image-data-empty",pathlib.Path("/var/lib/postgresql/data"),False),
    ]

def command_spec(method=None):
    build=method is None
    require(build or method in METHODS,"fixed_native_method")
    suffix="build" if build else "method-"+str(METHODS.index(method)+1)
    name="pinkha-loaded-account-native-"+suffix+"-20261123"
    binary=ATTEMPT/"products/loaded-account.test"
    entry=str(GO) if build else str(binary)
    args=(["test","-c","-work","-x","-p=1","-mod=readonly",
           "-modfile="+str(HERE/"candidate.mod"),"-tags",TAGS,"-o",str(binary),"./core/application"]
          if build else ["-test.v","-test.run=^"+method+"$","-test.count=1","-test.timeout="+GO_TEST_TIMEOUT])
    argv=DOCKER+["run","--pull=never","--name",name,"--cidfile",str(STAGE_DIR/(suffix+".cid")),
        "--label","pinkha.loaded-account-native="+HEART_SHA,"--network","none","--read-only",
        "--log-driver","none","--user","1001:1001","--cpus","1","--memory","4g","--memory-swap","4g",
        "--pids-limit","256","--cap-drop","ALL","--security-opt","no-new-privileges",
        "--workdir",str(HEART),"--entrypoint",entry]
    for source,destination,writable in container_mounts(build):
        argv+=["--mount","type=bind,source="+str(source)+",target="+str(destination)+("" if writable else ",readonly")]
    for key,value in sorted(environment().items()):argv+=["--env",key+"="+value]
    argv+=[IMAGE,*args]
    return {"name":name,"suffix":suffix,"cidpath":str(STAGE_DIR/(suffix+".cid")),
            "entry":entry,"args":args,"argv":argv,"method":method,"build":build}

def exact_absence(result,name):
    return result.returncode==1 and result.stdout==b"[]\n" and result.stderr==(
        "error: no such object: "+name+"\n").encode("ascii")

def container_preflight(spec):
    absent=operation(DOCKER+["inspect",spec["name"]],"container-absence",allow_nonzero=True)
    require(exact_absence(absent,spec["name"]),"native_container_name_not_proven_absent")
    image=operation(DOCKER+["image","inspect",IMAGE],"image-identity")
    values=strict(image.stdout)
    require(type(values) is list and len(values)==1 and values[0]["Id"]==IMAGE,"native_image_identity")
    require(values[0]["Architecture"]=="arm64" and values[0]["Os"]=="linux","native_image_platform")
    require(set(values[0]["Config"].get("Volumes") or {})=={"/var/lib/postgresql/data"},
            "unreviewed_image_anonymous_volume")

def validate_container(value,cid,spec):
    require(value["Id"]==cid and value["Name"]=="/"+spec["name"] and value["Image"]==IMAGE,
            "native_container_identity")
    require(value["Config"]["Labels"].get("pinkha.loaded-account-native")==HEART_SHA and
            value["Config"]["User"]=="1001:1001","native_container_source_owner")
    host=value["HostConfig"]
    require(host["NetworkMode"]=="none" and host["ReadonlyRootfs"] is True and
            host["LogConfig"]=={"Type":"none","Config":{}},"native_container_isolation")
    mounts={}
    for item in value["Mounts"]:
        destination=item["Destination"]
        require(destination not in mounts,"duplicate_native_container_mount")
        mounts[destination]=(item["Source"],item["RW"],item["Type"])
    expected={str(dst):(str(src.resolve()),rw,"bind") for src,dst,rw in container_mounts(spec["build"])}
    require(mounts==expected,"native_container_exact_mounts")
    require(value["Path"]==spec["entry"] and value["Args"]==spec["args"],"native_container_command")
    configured={}
    for item in value["Config"]["Env"]:
        key,content=item.split("=",1)
        require(key not in configured,"duplicate_native_environment")
        configured[key]=content
    require(all(configured.get(k)==v for k,v in environment().items()),"native_container_environment")
    require(value["Config"]["WorkingDir"]==str(HEART),"native_container_cwd")
    require(host["NanoCpus"]==1_000_000_000 and host["Memory"]==4*1024**3 and
            host["MemorySwap"]==4*1024**3 and host["PidsLimit"]==256,"native_container_resource_limits")
    require(set(host["CapDrop"] or [])=={"ALL"} and "no-new-privileges" in host["SecurityOpt"],
            "native_container_privileges")

def cleanup_container(spec):
    path=pathlib.Path(spec["cidpath"])
    if not path.exists():
        absent=operation(DOCKER+["inspect",spec["name"]],"container-without-cid",allow_nonzero=True)
        require(exact_absence(absent,spec["name"]),"native_container_unknown_without_cid")
        return {"state":"ABSENT","started":False,"safe_to_continue":True}
    value=path.lstat()
    require(stat.S_ISREG(value.st_mode) and not path.is_symlink() and value.st_size<=128,
            "native_cid_file_shape")
    cid=path.read_text().strip()
    require(re.fullmatch(r"[0-9a-f]{64}",cid) is not None,"native_cid_shape")
    before=operation(DOCKER+["inspect",cid],"container-before-cleanup")
    rows=strict(before.stdout)
    require(type(rows) is list and len(rows)==1,"native_inspection_shape")
    current=rows[0];validate_container(current,cid,spec);initial=current["State"]
    if initial["Running"]:
        operation(DOCKER+["kill",cid],"exact-owned-container-kill")
    after=operation(DOCKER+["inspect",cid],"container-after-cleanup")
    rows=strict(after.stdout)
    require(type(rows) is list and len(rows)==1,"native_final_inspection_shape")
    current=rows[0];validate_container(current,cid,spec)
    require(current["State"]["Running"] is False and current["State"]["Pid"]==0,
            "native_owned_container_still_running")
    return {"state":"STOPPED_RETAINED","id":cid,"initial_state":initial,"final_state":current["State"],
            "removed":False,"safe_to_continue":True}

def native_command(spec,record):
    global CURRENT
    timeout=BUILD_SECONDS if spec["build"] else TEST_SECONDS
    prefix=STAGE_DIR/spec["suffix"]
    record.update(spec=spec,started=now(),timeout_seconds=timeout,status="FAILED",
        primary_error=None,cleanup_error=None,owned_group_absent=False,
        stdout_complete=False,stderr_complete=False,actual_native_build=spec["build"],
        actual_selected_method=spec["method"])
    COMMANDS.append(record)
    start=time.monotonic();launch_start=None;child=None;streams={};files={};counts={"stdout":0,"stderr":0}
    limits={"stdout":1024*1024 if spec["build"] else 8*1024*1024,
            "stderr":8*1024*1024 if spec["build"] else 1024*1024}
    selector=selectors.DefaultSelector()
    try:
        record["resources_before"]=resource_guard()
        record["ram_before"]=ram_all()
        container_preflight(spec)
        for name in counts:
            path=prefix.with_suffix("."+name)
            files[name]=path.open("xb");os.chmod(path,0o600)
        record["resources_at_launch"]=resource_guard()
        require(record["resources_at_launch"]["memory_available"]>=MEM_COMMAND_START,"native_command_start_memory")
        record["preflight_elapsed_seconds"]=time.monotonic()-start
        launch_start=time.monotonic();record["launch_attempted"]=True
        child=subprocess.Popen(spec["argv"],cwd=HEART,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        CURRENT=child;record.update(pid=child.pid,pgid=os.getpgid(child.pid))
        require(record["pid"]==record["pgid"],"native_owned_cli_group")
        PROCESS.register_owned_child(child,record)
        for name,stream in (("stdout",child.stdout),("stderr",child.stderr)):
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name);streams[name]=stream
        while selector.get_map():
            require(time.monotonic()-launch_start<timeout,"native_command_timeout")
            observed=resource_guard()
            record["minimum_disk_free"]=min(record.get("minimum_disk_free",observed["disk_free"]),observed["disk_free"])
            record["minimum_memory_available"]=min(record.get("minimum_memory_available",observed["memory_available"]),observed["memory_available"])
            for key,_ in selector.select(0.25):
                name=key.data;chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    selector.unregister(key.fileobj);record[name+"_complete"]=True;continue
                remaining=limits[name]-counts[name]
                files[name].write(chunk[:max(0,remaining)]);counts[name]+=min(len(chunk),max(0,remaining))
                if len(chunk)>remaining:
                    record["output_limit"]={"stream":name,"bytes_observed_at_least":counts[name]+len(chunk)-max(0,remaining)}
                    raise RuntimeError("native_"+name+"_output_limit")
        record["returncode_before_cleanup"]=child.wait(timeout=max(0.001,timeout-(time.monotonic()-launch_start)))
        if record["returncode_before_cleanup"]!=0:
            record["primary_error"]={"type":"ChildProcessError","message":"native_command_nonzero",
                                     "returncode":record["returncode_before_cleanup"]}
        record["post_exit_resources"]=resource_guard()
        record["post_exit_elapsed"]=time.monotonic()-launch_start
        require(record["post_exit_elapsed"]<timeout,"native_late_completion")
        record["post_exit_admitted"]=True
    except BaseException as error:
        details={"type":type(error).__name__,"message":str(error)}
        if record["primary_error"] is None:record["primary_error"]=details
        else:record["later_command_error"]=details
    finally:
        if record.get("launch_attempted"):
            try:record["container_cleanup"]=cleanup_container(spec)
            except BaseException as error:
                record["cleanup_error"]={"phase":"container","type":type(error).__name__,"message":str(error)}
        if child is not None:
            try:
                PROCESS.stop_owned(child,record)
                record["returncode"]=child.wait(timeout=5)
                record["owned_group_absent"]=PROCESS.group_absent(child.pid)
                require(record["owned_group_absent"],"native_cli_group_remains")
            except BaseException as error:
                details={"phase":"cli","type":type(error).__name__,"message":str(error)}
                record.setdefault("additional_cleanup_errors",[]).append(details)
                if record["cleanup_error"] is None:record["cleanup_error"]=details
        CURRENT=None;selector.close()
        for stream in streams.values():stream.close()
        for name,target in files.items():
            target.flush();os.fsync(target.fileno());target.close()
            record[name]=file_row(prefix.with_suffix("."+name),guard=False)
        record.update(finished=now(),elapsed_seconds=time.monotonic()-start,
                      native_elapsed_seconds=None if launch_start is None else time.monotonic()-launch_start)
        if (record["primary_error"] is None and record["cleanup_error"] is None and
            record.get("returncode")==0 and record.get("returncode_before_cleanup")==0 and
            record["owned_group_absent"] and record.get("post_exit_admitted") and
            all(record[k+"_complete"] for k in counts) and
            record.get("container_cleanup",{}).get("final_state",{}).get("ExitCode")==0):
            record["status"]="PASS"
        save(prefix.with_suffix(".command.json"),record)
    return record


def named_events(stdout,method):
    value=stdout.lstat()
    require(stat.S_ISREG(value.st_mode) and not stdout.is_symlink() and value.st_size<=8*1024**2,
            "native_event_original_shape")
    raw=stdout.read_bytes();text=raw.decode("utf-8","strict")
    starts=re.findall(r"(?m)^=== RUN   (.+)$",text)
    terminals=re.findall(r"(?m)^--- (PASS|FAIL|SKIP): ([^\s]+) \(([^)\r\n]+)\)$",text)
    package=re.findall(r"(?m)^(PASS|FAIL)$",text)
    require(all(name==method for name in starts),"unexpected_native_method_start")
    require(all(name==method and re.fullmatch(r"\d+(?:\.\d+)?s",elapsed) for _,name,elapsed in terminals),
            "unexpected_native_method_terminal")
    require(len(starts)<=1 and len(terminals)<=1 and len(package)<=1,"duplicate_native_events")
    return {"method":method,"starts":starts,"terminals":[list(v) for v in terminals],"package":package,
            "pass":starts==[method] and len(terminals)==1 and terminals[0][0]=="PASS" and package==["PASS"],
            "stdout_sha256":hashlib.sha256(raw).hexdigest()}

def actual_build_event(command):
    path=STAGE_DIR/"build.stderr"
    if not command.get("launch_attempted"):return {"count":0,"launch_attempted":False}
    if not path.exists():return {"count":None,"launch_attempted":True,"reason":"original_stderr_absent"}
    original=file_row(path,maximum=8*1024**2,guard=False)
    raw=path.read_bytes()
    matches=re.findall(rb"(?m)^WORK=([^\r\n]+)$",raw)
    require(len(matches)<=1,"duplicate_go_build_work_event")
    if not matches:
        return {"count":None,"launch_attempted":True,"reason":"go_build_start_not_observed","original":original}
    work=matches[0].decode("ascii","strict")
    prefix=str(ATTEMPT/"work")+"/go-build"
    require(work.startswith(prefix) and work[len(prefix):].isdigit(),"actual_go_build_work_scope")
    return {"count":1,"launch_attempted":True,"original":original,"actual_go_work_path":work}

def binary_buildinfo(binary):
    output=operation([str(GO),"version","-m",binary["path"]],"binary-buildinfo",timeout=30)
    lines=output.stdout.decode("utf-8","strict").splitlines()
    require(lines and lines[0]==binary["path"]+": go1.26.5","actual_binary_go_version")
    original=raw_file(STAGE_DIR/"binary-buildinfo-original.txt",output.stdout)
    return {"original":original,"go_version":"go1.26.5","all_dependencies_embedded_claim":False,
            "actual_top_level_tool":file_row(GO),
            "dependency_origin":"fixed compiler invocation plus before/after source rows"}

def inspect_operations():
    rows={}
    for path in sorted((STAGE_DIR/"operations").glob("*.json")):
        value=strict(path.read_bytes())
        require(value.get("primary_error") is None and value.get("cleanup_error") is None and
                value.get("owned_group_absent") is True,"owned_operation_failure")
        require(value.get("cleanup_privilege",{}).get("restored") is True,"owned_operation_identity_not_restored")
        rows[path.name]=file_row(path,maximum=512*1024,guard=False)
    require(rows and not PROCESS.OWNED_CHILDREN,"owned_operation_registry_not_drained")
    return rows

def emergency_result(path,result):
    # Preserve the first outcome even if an observed fixture/output growth
    # already crossed its budget. This is a bounded original receipt only.
    raw=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    require(len(raw)<=512*1024 and not path.exists() and not path.is_symlink(),"bounded_original_result")
    with path.open("xb") as out:
        os.chmod(path,0o600);out.write(raw);out.flush();os.fsync(out.fileno())
    return {"path":str(path),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def interrupted(signum,_frame):
    raise InterruptedError("native_owned_signal_"+str(signum))

def main():
    global STAGE,STAGE_DIR,FROZEN,AUDIT,META_WRITTEN,RAM_STATE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("build","execute"))
    parser.add_argument("--expected-controller-sha",required=True)
    parser.add_argument("--expected-source-sha256",required=True)
    parser.add_argument("--expected-manifest-sha256",required=True)
    parser.add_argument("--expected-build-result-sha256")
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    require(args.execute and sys.flags.isolated and sys.dont_write_bytecode,"explicit_native_profile_entry")
    require(process_credentials()=={"uids":[1001,1001,0],"gids":[1001,1001,1001],"groups":ORDINARY_GROUPS},
            "ordinary_project_execution_identity")
    require(re.fullmatch(r"[0-9a-f]{64}",args.expected_source_sha256) is not None and
            re.fullmatch(r"[0-9a-f]{64}",args.expected_manifest_sha256) is not None,"native_pin_argument_shape")
    require(hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()==args.expected_source_sha256,
            "native_controller_source_pin")
    STAGE=args.stage;STAGE_DIR=ATTEMPT/("build" if STAGE=="build" else "execution")
    if STAGE=="build":
        initial=resource_guard(start=True,check_attempt=False)
        require(not ATTEMPT.exists() and not ATTEMPT.is_symlink(),"preserve_original_native_attempt")
        EVIDENCE.mkdir(mode=0o700,exist_ok=True);exact_private_dir(EVIDENCE)
        ATTEMPT.mkdir(mode=0o700)
        for name in ("private","private/fixtures","image-data-empty"):
            (ATTEMPT/name).mkdir(mode=0o700)
    else:
        initial=resource_guard()
        require(initial["memory_available"]>=MEM_COMMAND_START,"native_execute_start_memory")
        exact_private_dir(ATTEMPT)
    require(not STAGE_DIR.exists() and not STAGE_DIR.is_symlink(),"preserve_original_native_stage")
    STAGE_DIR.mkdir(mode=0o700);(STAGE_DIR/"operations").mkdir(mode=0o700)
    for path in (ATTEMPT,ATTEMPT/"private",ATTEMPT/"private/fixtures",STAGE_DIR):
        exact_private_dir(path)
    before_address=resource.getrlimit(resource.RLIMIT_AS)
    address=min([ADDRESS_LIMIT]+[v for v in before_address if v>=0])
    resource.setrlimit(resource.RLIMIT_AS,(address,before_address[1]))
    result={"schema":"loaded-account-native-profile-v1","stage":STAGE,"started":now(),"status":"FAILED",
        "primary_error":None,"final_errors":[],"source_controller":args.expected_controller_sha,
        "controller_sha256":args.expected_source_sha256,"manifest_sha256":args.expected_manifest_sha256,
        "heart_source":HEART_SHA,"any_sync_source":SYNC_SHA,"initial_resources":initial,
        "address_space_limit":address,"entry_identity":ENTRY_CREDENTIALS,
        "new_native_builds":0,"actual_starts":[],"actual_passes":[],"old_methods_replayed":0,
        "new_source_queries":0,"semantic_completeness":False,"native_source_admission":False,
        "file_payload_completeness":False,"destination_writes":False,
        "durable_binary_custody_complete":False,"ram_unmounted":False,
        "ordinary_dependency_records":"new current native-phase reads against qualified later offline rows",
        "historical_graph_loaded_after_recreated":False,"commands":COMMANDS}
    emergency_result(STAGE_DIR/"launch-intent.json",dict(result))
    handlers={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM)}
    for signum in handlers:signal.signal(signum,interrupted)
    signal.setitimer(signal.ITIMER_REAL,1350)
    before=plan=build=None
    try:
        result["process_helper"]=load_process_helper()
        FROZEN=load_frozen_inputs(args.expected_manifest_sha256)
        require(FROZEN["compiler_support"]["state"]!="BLOCKED_COMPILER_SUPPORT",
                "native_profile_blocked_fixed_image_has_no_compiler_tools")
        require(FROZEN["controller_sha256"]==args.expected_source_sha256,"manifest_native_controller_pin")
        AUDIT=load_module(HERE/"native_audit.py",FROZEN["auditor_sha256"],"loaded_account_native_auditor")
        require(AUDIT.METHODS==METHODS,"native_auditor_fixed_selection")
        plan=original_graph()
        before,refs=snapshot("before",args.expected_controller_sha,plan)
        result["before"]=refs
        if STAGE=="build":
            result["ram_initial"]=prepare_ram()
            (RAM_SPECS["tmp"]["path"]/"home").mkdir(mode=0o700)
            result["cache_copy"]=copy_cache()
            result["ram_state"]=save(STAGE_DIR/"ram-state.json",RAM_STATE)
            require(memory_available()>=MEM_COMMAND_START,"native_compile_memory_after_clone")
            command={};result["build_command"]=command
            native_command(command_spec(),command)
            result["build_event"]=actual_build_event(command)
            result["new_native_builds"]=result["build_event"]["count"]
            require(command["status"]=="PASS" and result["new_native_builds"]==1,"native_build_failed_preserved")
            result["binary"]=elf_binary()
            result["actual_generated_main"]=generated_after_build()
            result["buildinfo"]=binary_buildinfo(result["binary"])
            result["status"]="BUILD_PASS_RAM_CUSTODY_PENDING"
        else:
            require(args.expected_build_result_sha256 is not None and
                    re.fullmatch(r"[0-9a-f]{64}",args.expected_build_result_sha256) is not None,
                    "exact_original_build_receipt_required")
            build_raw=fixed_bytes(ATTEMPT/"build/result.json",args.expected_build_result_sha256,512*1024)
            build=strict(build_raw)
            require(build["status"]=="BUILD_PASS_RAM_CUSTODY_PENDING" and
                    build["primary_error"] is None and not build["final_errors"] and
                    build["source_controller"]==args.expected_controller_sha and
                    build["controller_sha256"]==args.expected_source_sha256 and
                    build["manifest_sha256"]==args.expected_manifest_sha256 and
                    build["new_native_builds"]==1 and build["actual_starts"]==[],
                    "native_build_execution_origin")
            state=build["ram_state"]
            raw=fixed_bytes(pathlib.Path(state["path"]),state["sha256"],128*1024)
            RAM_STATE=strict(raw)
            require(set(RAM_STATE)==set(RAM_SPECS),"actual_build_ram_state")
            result["ram_before_execution"]=ram_all()
            current=elf_binary();require(current==build["binary"],"actual_original_binary_changed")
            result["binary"]=current
            for method in METHODS:
                require(memory_available()>=MEM_COMMAND_START,"native_method_start_memory")
                require(elf_binary()==build["binary"],"native_binary_changed_between_methods")
                command={};result.setdefault("methods",[]).append({"method":method,"command":command})
                row=result["methods"][-1]
                native_command(command_spec(method),command)
                stdout=STAGE_DIR/(command["spec"]["suffix"]+".stdout")
                if stdout.exists():
                    events=named_events(stdout,method);row["events"]=events
                    result["actual_starts"]+=events["starts"]
                    if events["pass"]:result["actual_passes"].append(method)
                if command["status"]=="PASS" and row.get("events",{}).get("pass"):
                    try:
                        row["private_audit"]=AUDIT.audit_method(ATTEMPT/"private/fixtures",stdout,method)
                        row["status"]="PASS_NEW_NATIVE_METHOD"
                    except BaseException as error:
                        row["audit_error"]={"type":type(error).__name__,"message":str(error)}
                        row["status"]="FAILED"
                else:row["status"]="FAILED"
                save(STAGE_DIR/(command["spec"]["suffix"]+"-audit.json"),row)
                if row["status"]!="PASS_NEW_NATIVE_METHOD" and result["primary_error"] is None:
                    result["primary_error"]={"type":"NativeMethodFailure","message":method,"original_command":command}
                require(command.get("cleanup_error") is None and command.get("owned_group_absent") is True and
                        command.get("container_cleanup",{}).get("safe_to_continue") is True,
                        "native_method_custody_incomplete")
                resource_guard()
            require(len(result.get("methods",[]))==4 and
                    all(v["status"]=="PASS_NEW_NATIVE_METHOD" for v in result["methods"]) and
                    result["actual_starts"]==METHODS and result["actual_passes"]==METHODS,
                    "four_actual_native_controls_not_all_qualified")
            require(elf_binary()==build["binary"],"actual_native_binary_after_execution")
            result["status"]="FOUR_NATIVE_METHODS_PASS_RAM_CUSTODY_PENDING"
    except BaseException as error:
        details={"type":type(error).__name__,"message":str(error)}
        if result["primary_error"] is None:result["primary_error"]=details
        else:result["later_failure"]=details
        result["status"]="FAILED"
    finally:
        result["native_build_launch_attempts"]=sum(int(v.get("launch_attempted",False) and
                                                      v.get("spec",{}).get("build") is True) for v in COMMANDS)
        if STAGE=="build" and result.get("build_command") is not None:
            try:
                result["build_event"]=actual_build_event(result["build_command"])
                result["new_native_builds"]=result["build_event"]["count"]
            except BaseException as error:
                result["new_native_builds"]=None
                result["final_errors"].append({"scope":"actual-build-event",
                    "type":type(error).__name__,"message":str(error)})
        result["actual_native_launches"]=sum(int(v.get("launch_attempted",False)) for v in COMMANDS)
        # Native events stay recoverable even when a later receipt save raised.
        for command in COMMANDS:
            method=command.get("spec",{}).get("method")
            if method is None:continue
            try:
                stdout=STAGE_DIR/(command["spec"]["suffix"]+".stdout")
                if stdout.exists():
                    events=named_events(stdout,method)
                    if events["starts"] and method not in result["actual_starts"]:
                        result["actual_starts"].append(method)
                    if events["pass"] and method not in result["actual_passes"]:
                        result["actual_passes"].append(method)
            except BaseException as error:
                result["final_errors"].append({"scope":"named-events","method":method,
                    "type":type(error).__name__,"message":str(error)})
        # No automatic unmount, cache deletion, container removal, retry, or
        # product disposal. A later separately bound custody action must first
        # retain/read back the binary and all owned compiler partial outputs.
        if plan is not None and before is not None:
            try:
                after,refs=snapshot("after",args.expected_controller_sha,plan)
                result["after"]=refs
                require(before==after,"native_phase_source_or_dependency_changed")
                result["source_inputs_before_after_equal"]=True
            except BaseException as error:
                result["final_errors"].append({"scope":"source","type":type(error).__name__,"message":str(error)})
        if PROCESS is not None:
            try:result["owned_operations"]=inspect_operations()
            except BaseException as error:
                result["final_errors"].append({"scope":"owned-operations","type":type(error).__name__,"message":str(error)})
        if set(RAM_STATE)==set(RAM_SPECS):
            try:
                result["ram_final"]=ram_all()
                result["ram_outputs"]=save(STAGE_DIR/"ram-output-originals.json.gz",ram_output_inventory(),packed=True)
            except BaseException as error:
                result["final_errors"].append({"scope":"ram-custody","type":type(error).__name__,"message":str(error)})
        try:
            result["ram_state_observed_final"]=save(STAGE_DIR/"ram-state-observed-final.json",RAM_STATE)
        except BaseException as error:
            result["final_errors"].append({"scope":"ram-state-receipt","type":type(error).__name__,"message":str(error)})
        try:
            usage=attempt_usage()
            result["final_resources"]={"disk_free":free(),"memory_available":memory_available(),
                                       "attempt_usage":usage,"attempt_bytes":usage["total"]}
            if result["final_resources"]["disk_free"]<FINAL_FREE+512*1024:
                result["final_errors"].append({"scope":"capacity","minimum_free":FINAL_FREE,
                                              "actual":result["final_resources"]["disk_free"],"final_receipt_reserve_bytes":512*1024})
            if result["final_resources"]["memory_available"]<MEM_STOP:
                result["final_errors"].append({"scope":"memory","minimum_available":MEM_STOP,
                                              "actual":result["final_resources"]["memory_available"]})
            if usage["total"]>ATTEMPT_LIMIT:
                result["final_errors"].append({"scope":"attempt-budget","actual":usage["total"]})
            if usage["metadata"]>METADATA_LIMIT:
                result["final_errors"].append({"scope":"combined-metadata-budget","actual":usage["metadata"]})
        except BaseException as error:
            result["final_errors"].append({"scope":"final-resource-observation",
                "type":type(error).__name__,"message":str(error)})
        result["final_identity"]=process_credentials()
        if result["final_identity"]!={"uids":[1001,1001,0],"gids":[1001,1001,1001],"groups":ORDINARY_GROUPS}:
            result["final_errors"].append({"scope":"ordinary-identity-restoration"})
        result["file_hash_read_bytes"]=READ_BYTES;result["additional_fixed_read_bytes"]=FIXED_READ_BYTES
        result["available_tools_are_not_all_claimed_executed"]=True
        result["finished"]=now()
        signal.setitimer(signal.ITIMER_REAL,0)
        for signum,handler in handlers.items():signal.signal(signum,handler)
        if result["primary_error"] is not None or result["final_errors"]:result["status"]="FAILED"
        sealed=emergency_result(STAGE_DIR/"result.json",result)
        print(json.dumps({"status":result["status"],"stage":STAGE,"result":sealed,
              "actual_starts":result["actual_starts"],"actual_passes":result["actual_passes"],
              "new_native_builds":result["new_native_builds"],"new_source_queries":0,
              "durable_binary_custody_complete":False,"ram_retained":bool(RAM_STATE)}))
    return 0 if result["status"]!="FAILED" else 1

if __name__=="__main__":
    sys.exit(main())
