#!/usr/bin/env python3
"""Complete one original projected source graph offline.

No Go, compiler, test, container, mount or privilege operation is available here.
The original aggregate failure remains immutable. Ordinary dependency bytes are
read later; the generated test main uses its original captured RAM metadata.
"""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import re
import resource
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
ORIGINAL_CONTROL_SHA = "0f57f72e3f447d0bb67ffef783d22539094d9ad9"
PROFILE = HERE/"ram_projected_graph.py"
PROFILE_SHA = "cd5e46269f566870489f338471f9c63e14dfd6a8dd842be221fed5b1cccff6cf"
EVIDENCE = pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
ORIGINAL = EVIDENCE/"ram-projected-graph-attempt1"
OUTPUT = EVIDENCE/"ram-projected-offline-completion1"
ORIGINAL_AUDIT = CONTROL/"docs/validation/20261123-loaded-account-witness/projected-original-attempt1/audit.json"
AUDIT_SHA = "7e012986f763161783dc08030e06e7c08d80dcad8e5698c558c9d4aa503391d5"
RAM = pathlib.Path("/dev/shm/pinkha-loaded-account-projected-source-20261123")
CACHE = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/attempt4/cache")
CACHE_REAL = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/cache")
GOROOT = pathlib.Path("/mnt/development/projects/evidence/semantic-page-20261123-arm64/toolchains/go1.26.5/go")
GENERATED_HASH = "749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715"
GENERATED_RELATIVE = "go-cache/74/"+GENERATED_HASH+"-d"
GENERATED_PATH = RAM/GENERATED_RELATIVE
FIELDS = ("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
COLUMNS = ("path","sha256",*FIELDS,"resolved_path_or_same","generated_presence")
EXPANDED_LIMIT = 6*1024*1024
COMPRESSED_LIMIT = 2*1024*1024
TOTAL_LIMIT = 16*1024*1024
FLOOR = 1024**3
SECONDS = 120
GENERATED = {}
GENERATED_ROWS = {}
LATER_ROWS = {}
STARTED = None
LAST_RESOURCE = 0.0
READ_BYTES = 0
READ_LIMIT = 1024**3
ADDRESS_SPACE_LIMIT = 512*1024*1024
ORIGINAL_PINS = {
    "container-after-cleanup.json": {
        "bytes": 20135,
        "sha256": "1822473a94f9fd289ea637693bf95b9ed620bf70859b9c36d6379f8443e2ce8d"
    },
    "container-before-cleanup.json": {
        "bytes": 20136,
        "sha256": "232ffd23997e32ccf40ae3f9592702199786fb5c4a4e8f2ef6d30995a022fb99"
    },
    "container-before-ram-release.json": {
        "bytes": 20135,
        "sha256": "f98f96995b4e78ee6e0117de94a767588e31463047b53305df6941cad1295321"
    },
    "container-preflight-absence.json": {
        "bytes": 1384,
        "sha256": "f0d9eb42ab8903df2718adb1a0bb409f23373c851294d30382358a3fb9b46a45"
    },
    "container.cid": {
        "bytes": 64,
        "sha256": "a87fddd512637d725c1de45edb2ff80a5fedde590bb6f11851d90ab6761b04ac"
    },
    "generated-test-main/749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715.go": {
        "bytes": 3282,
        "sha256": "749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715"
    },
    "image-original.json": {
        "bytes": 4419,
        "sha256": "5ac98da23f00050b321f7c1b89dc9af5dd882ef4a6e1a87a6a7ff475923487aa"
    },
    "query-command.json": {
        "bytes": 9855,
        "sha256": "e5fae984747a0b93806770dcf0ff63bf7e863df23ebffb9e98c185514265b3ee"
    },
    "ram-inventory.json.gz": {
        "bytes": 181513,
        "sha256": "7e71cc6913fd3728768b3a793a9b8f7d056c9b3f37679af989fefb208fe398de"
    },
    "ram-mount.json": {
        "bytes": 1468,
        "sha256": "7150483c56546db8359c00a6796b5810f305db27fe61094d3b8c13b638de55f6"
    },
    "ram-normal-unmount.json": {
        "bytes": 1297,
        "sha256": "2956a47669f17544c6f736b45cc3b2cdc548f678a7c638937f3a22a10b785146"
    },
    "ram-originals.tar.gz": {
        "bytes": 1788509,
        "sha256": "dc557d7ff904e8bd1fed9a536ceb834334ef2310128a9fa4a0094c4bb3ce7154"
    },
    "result.json": {
        "bytes": 21501,
        "sha256": "249c5a4a5a16ce7f39669925d03e804c8dab1517899c487179d123912b66601f"
    },
    "source-after.json.gz": {
        "bytes": 291658,
        "sha256": "5315797213f33181be0d741a8411a451df7cc21673d19a5e79af70baa18f8487"
    },
    "source-before.json.gz": {
        "bytes": 291658,
        "sha256": "5315797213f33181be0d741a8411a451df7cc21673d19a5e79af70baa18f8487"
    },
    "stderr.log": {
        "bytes": 0,
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "stdout.log": {
        "bytes": 1234586,
        "sha256": "240201e3a30b6391adcbdc090ef9829fe66c36c62bfd59de1eba7b0aeee61dc3"
    }
}

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def now():
    return datetime.now(timezone.utc).isoformat()

def free():
    return shutil.disk_usage("/mnt/development").free

def guard():
    global LAST_RESOURCE
    require(STARTED is None or time.monotonic()-STARTED<SECONDS,"offline_completion_deadline")
    current = time.monotonic()
    if current-LAST_RESOURCE>=0.25:
        require(free()>=FLOOR,"offline_completion_capacity")
        LAST_RESOURCE = current

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

def row(path):
    global READ_BYTES
    guard()
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink(),"input_not_regular")
    require(before.st_size<=256*1024*1024,"single_input_read_budget")
    digest = hashlib.sha256()
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(first,k) for k in FIELDS),"input_open_identity")
        with os.fdopen(fd,"rb",closefd=False) as source:
            for chunk in iter(lambda:source.read(1024*1024),b""):
                guard()
                READ_BYTES += len(chunk)
                require(READ_BYTES<=READ_LIMIT,"offline_read_budget")
                digest.update(chunk)
        last = os.fstat(fd)
    finally:
        os.close(fd)
    after = path.lstat()
    require(tuple(getattr(before,k) for k in FIELDS)==tuple(getattr(last,k) for k in FIELDS)==
            tuple(getattr(after,k) for k in FIELDS),"input_changed_during_read")
    return dict(path=str(path),sha256=digest.hexdigest(),**{k:str(getattr(after,k)) for k in FIELDS})

def pinned(path,sha256,size=None):
    value = row(path)
    require(value["sha256"]==sha256 and (size is None or int(value["st_size"])==size),"fixed_input_changed")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==sha256,"fixed_input_read_changed")
    return raw

def git(root,*args):
    guard()
    remaining = SECONDS-(time.monotonic()-STARTED) if STARTED is not None else 30
    return subprocess.check_output(["git","-C",str(root),*args],timeout=min(30,max(0.001,remaining)))

def current_source(expected):
    require(re.fullmatch(r"[0-9a-f]{40}",expected) is not None,"invalid_current_controller_identity")
    for root,commit in ((HEART,HEART_SHA),(SYNC,SYNC_SHA),(CONTROL,expected)):
        require(git(root,"rev-parse","HEAD").decode().strip()==commit,"current_head_changed")
        require(not git(root,"status","--porcelain=v1","--untracked-files=all").strip(),"current_tree_dirty")
    require(CACHE.is_symlink() and os.readlink(CACHE)=="../cache" and CACHE.resolve()==CACHE_REAL,"cache_spelling_changed")
    selected = ("Tools/AnyEngineValidation/loaded_account_witness",
                "docs/validation/20261123-loaded-account-witness/projected-original-attempt1",
                "docs/validation/20261123-loaded-account-witness/offline-completion")
    records = {}
    for item in git(CONTROL,"ls-tree","-rz",expected,"--",*selected).split(b"\0"):
        if not item:
            continue
        header,name = item.split(b"\t",1)
        mode,kind,oid = header.split()
        relative = name.decode()
        path = CONTROL/relative
        require(kind==b"blob" and mode in (b"100644",b"100755") and path.resolve()==path,"current_source_type_or_path")
        raw = path.read_bytes()
        require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==oid.decode(),"current_physical_git_difference")
        require(bool(path.stat().st_mode&0o111)==(mode==b"100755"),"current_executable_mode_difference")
        records[relative] = dict(row(path),git_blob=oid.decode(),git_mode=mode.decode())
    require(str(pathlib.Path(__file__).relative_to(CONTROL)) in records,"actual_offline_source_missing")
    loaded = {}
    for name,module in sorted(sys.modules.items()):
        filename = getattr(module,"__file__",None)
        if filename:
            path = pathlib.Path(filename).resolve()
            if path.is_relative_to(CONTROL.parent):
                require(path==pathlib.Path(__file__).resolve(),"unexpected_repository_import")
                loaded[name] = row(path)
    require(set(loaded)=={"__main__"},"actual_offline_module_binding")
    return {"controller_commit":expected,"records":records,"actual_loaded_python":loaded}

def original_state():
    audit = json.loads(pinned(ORIGINAL_AUDIT,AUDIT_SHA))
    require({v["path"]:{"bytes":v["bytes"],"sha256":v["sha256"]} for v in audit["originals"]}==ORIGINAL_PINS,
            "audited_original_set_changed")
    records = {}
    for name,value in ORIGINAL_PINS.items():
        path = ORIGINAL/name
        pinned(path,value["sha256"],value["bytes"])
        records[name] = row(path)
    result = json.loads((ORIGINAL/"result.json").read_bytes())
    require(result["status"]=="FAILED" and result["primary_error"]==
            {"type":"RuntimeError","message":"expanded_source_map_limit"} and not result["final_errors"],
            "original_failure_contract")
    query = result["query"]
    require(query["status"]=="PASS" and query["returncode"]==0 and query["stdout_complete"] and
            query["stderr_complete"] and query["owned_group_absent"] and query["primary_error"] is None and
            query["cleanup_error"] is None,"original_query_contract")
    require(result["native_builds"]==0 and result["actual_test_methods"]==0,"original_product_execution")
    require(result["ram_finalization"]["status"]=="PASS_PRESERVED_AND_UNMOUNTED" and
            result["ram_finalization"]["unmounted"] and result["ram_finalization"]["directory_removed"],
            "original_custody_contract")
    require(not RAM.exists() and not RAM.is_symlink(),"preserve_unexpected_current_ram_state")
    raw = gzip.decompress((ORIGINAL/"source-before.json.gz").read_bytes())
    require(raw==gzip.decompress((ORIGINAL/"source-after.json.gz").read_bytes()) and
            hashlib.sha256(raw).hexdigest()=="f88dcb29ca8f644e1b24e6dca4936d86bd540d95a1b9f1b69456e4f45a3ce3ca",
            "original_source_pair_changed")
    snapshot = json.loads(raw)
    require(snapshot["heart"]["commit"]==HEART_SHA and snapshot["any_sync"]["commit"]==SYNC_SHA and
            snapshot["controller"]["commit"]==ORIGINAL_CONTROL_SHA,"original_source_origins")
    inv = json.loads(gzip.decompress((ORIGINAL/"ram-inventory.json.gz").read_bytes()))
    require(not inv["unexpected_payloads"] and len(inv["files"])==1905 and len(inv["directories"])==259,
            "original_ram_inventory")
    generated = {k:v for k,v in inv["files"].items() if v["classification"]=="validated_generated_test_main"}
    require(set(generated)=={GENERATED_RELATIVE},"original_generated_set")
    value = dict(generated[GENERATED_RELATIVE])
    value.pop("classification")
    require(value["path"]==str(GENERATED_PATH) and value["sha256"]==GENERATED_HASH and
            value["st_size"]=="3282","original_generated_identity")
    GENERATED_ROWS[str(GENERATED_PATH)] = value
    return {"records":records,"result":result,"source":snapshot,"audit":audit}

def verify_captured_sources(snapshot):
    records = {}
    for section in ("heart","any_sync","controller"):
        for name,old in snapshot[section]["inputs"].items():
            require(old["path"]==str(pathlib.Path(snapshot[section]["root"])/name),"captured_source_path")
            current = row(pathlib.Path(old["path"]))
            require(current=={k:old[k] for k in current},"captured_source_changed")
            records[current["path"]] = current
    for old in snapshot["tools"].values():
        current = row(pathlib.Path(old["path"]))
        require(current==old,"captured_tool_changed")
        records[current["path"]] = current
    return records

def generated_original(path):
    require(str(path)==str(GENERATED_PATH) and str(path) in GENERATED_ROWS,"unbound_original_generated_input")
    return dict(GENERATED_ROWS[str(path)])

def preserved_generated_bytes(path,original):
    require(original==generated_original(path),"original_generated_tuple_changed")
    saved = ORIGINAL/"generated-test-main"/(original["sha256"]+".go")
    return pinned(saved,original["sha256"],int(original["st_size"]))

def bind_generated(path,raw,original):
    require(hashlib.sha256(raw).hexdigest()==original["sha256"],"preserved_generated_content_changed")
    GENERATED[path.relative_to(RAM).as_posix()] = {
        "original_captured_metadata":dict(original),
        "preserved_copy_later_read":row(ORIGINAL/"generated-test-main"/(original["sha256"]+".go")),
        "meaning":"original_ephemeral_graph_source_not_a_future_build_input",
    }

def dependency_row(path):
    if path==GENERATED_PATH:
        return generated_original(path)
    key = str(path)
    if key not in LATER_ROWS:
        LATER_ROWS[key] = row(path)
    return dict(LATER_ROWS[key])

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
                    cache_relative = path.relative_to(RAM/"go-cache")
                    require(package["ImportPath"]=="github.com/anyproto/anytype-heart/core/application.test" and
                            package.get("Name")=="main" and field=="GoFiles" and
                            re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{64}-d",cache_relative.as_posix()) is not None,
                            "unadmitted_generated_graph_input")
                    original_generated = generated_original(path)
                    require(int(original_generated["st_size"])<=128*1024,"generated_test_main_size")
                    raw_generated = preserved_generated_bytes(path,original_generated)
                    require(raw_generated.startswith(b"\n// Code generated by 'go test'. DO NOT EDIT.\n\npackage main\n") and
                            hashlib.sha256(raw_generated).hexdigest()==path.name[:-2],
                            "generated_test_main_identity")
                    require(original_generated["path"]==str(path) and path.is_relative_to(RAM/"go-cache"),"generated_test_main_escape")
                    bind_generated(path,raw_generated,original_generated)
                else:
                    require(".." not in relative.parts,"dependency_file_escape")
                    path = directory/relative
                resolved = path if generated else path.resolve()
                require(generated or any(resolved.is_relative_to(root) for root in allowed),"unbound_dependency_root")
                inputs[str(path)] = dict(dependency_row(path),resolved_path=str(resolved),generated_test_main=generated)
        module = package.get("Module")
        if module:
            effective = module.get("Replace",module)
            modules[(module["Path"],module.get("Version",""))] = module
            gomod = effective.get("GoMod")
            if gomod:
                path = pathlib.Path(gomod)
                resolved = path.resolve()
                require(any(resolved.is_relative_to(root) for root in allowed) or path==HERE/"candidate.mod","unbound_module_manifest")
                inputs[str(path)] = dict(dependency_row(path),resolved_path=str(resolved))
    require(any(p["import_path"]=="github.com/anyproto/anytype-heart/core/application" for p in packages),"application_graph_missing")
    sync_rows = [m for (path,_version),m in modules.items() if path=="github.com/anyproto/any-sync"]
    require(len(sync_rows)==1 and sync_rows[0].get("Version")=="v0.13.8","any_sync_version_changed")
    replacement = sync_rows[0].get("Replace",{})
    require(replacement.get("Dir")==str(SYNC) and replacement.get("Path")==str(SYNC),"tracked_any_sync_replacement_not_resolved")
    require(str(HEART/"core/application/loaded_witness_test.go") in inputs and str(HEART/"core/application/loaded_witness_fixture_test.go") in inputs,"new_acceptance_controls_missing")
    require(str(SYNC/"commonspace/object/acl/syncacl/witness_read.go") in inputs,"new_native_acl_feature_missing")
    require(len(inputs)<=20000 and len(packages)<=5000,"dependency_graph_row_limit")
    return {"protocol":"loaded-account-offline-projected-source-graph-v1","packages":packages,
            "modules":[modules[key] for key in sorted(modules)],"inputs":inputs,
            "source_only":True,"compile_export_or_test_requested":False,"module_cache_mounted_readonly":True,
            "original_go_build_cache_mounted":False,"new_empty_ram_cache":True,
            "cache_stale_or_build_id_values_are_not_source_identity":True,
            "generated_main_custody":GENERATED}



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

def used():
    total = 0
    for directory in (ORIGINAL,OUTPUT):
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            require(not path.is_symlink(),"evidence_symlink")
            if path.is_file():
                total += path.stat().st_size
    return total

def save(path,value,*,packed=False):
    raw = canonical(value)
    require(len(raw)<=EXPANDED_LIMIT,"offline_expanded_metadata_limit")
    data = gzip.compress(raw,compresslevel=6,mtime=0) if packed else raw
    require(not packed or len(data)<=COMPRESSED_LIMIT,"offline_compressed_metadata_limit")
    require(used()+len(data)<=TOTAL_LIMIT-65536,"offline_combined_metadata_budget")
    with path.open("xb") as target:
        os.chmod(path,0o600)
        target.write(data)
        target.flush()
        os.fsync(target.fileno())
    require(path.read_bytes()==data,"offline_metadata_readback")
    return {"path":str(path),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),
            "encoding":"gzip-json" if packed else "json","expanded_bytes":len(raw),
            "expanded_sha256":hashlib.sha256(raw).hexdigest()}

def save_plan(path,plan):
    encoded = encode_plan(plan)
    logical = canonical(plan)
    saved = save(path,encoded,packed=True)
    saved.update(logical_bytes=len(logical),logical_sha256=hashlib.sha256(logical).hexdigest(),
                 exact_decode_equality=True,read_provenance="ordinary_dependencies_read_during_this_later_offline_completion")
    return saved

def verify_later_rows(plan):
    after = dict(plan)
    inputs = {}
    for path,value in plan["inputs"].items():
        if pathlib.Path(path)==GENERATED_PATH:
            actual = generated_original(pathlib.Path(path))
            pinned(ORIGINAL/"generated-test-main"/(GENERATED_HASH+".go"),GENERATED_HASH,3282)
        else:
            actual = row(pathlib.Path(path))
            require(actual==LATER_ROWS[path],"later_dependency_before_after_mismatch")
        actual["resolved_path"] = value["resolved_path"]
        if "generated_test_main" in value:
            actual["generated_test_main"] = value["generated_test_main"]
        require(actual==value,"later_input_projection_changed")
        inputs[path] = actual
    after["inputs"] = inputs
    require(after==plan,"later_graph_before_after_mismatch")
    return after

def interrupt(signum,_frame):
    raise InterruptedError("offline_completion_signal_"+str(signum))

def main():
    global STARTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-controller-sha",required=True)
    parser.add_argument("--execute",action="store_true")
    args = parser.parse_args()
    require(args.execute and sys.flags.isolated and sys.dont_write_bytecode,"explicit_isolated_offline_entry")
    require(os.getresuid()==(1001,1001,1001),"ordinary_owner_required_no_saved_privilege")
    require(free()>=FLOOR+TOTAL_LIMIT,"offline_initial_capacity")
    prior_address_limits = resource.getrlimit(resource.RLIMIT_AS)
    address_limit = min([ADDRESS_SPACE_LIMIT]+[v for v in prior_address_limits if v>=0])
    resource.setrlimit(resource.RLIMIT_AS,(address_limit,prior_address_limits[1]))
    require(not OUTPUT.exists() and not OUTPUT.is_symlink(),"preserve_original_offline_attempt")
    OUTPUT.mkdir(mode=0o700)
    STARTED = time.monotonic()
    signal.signal(signal.SIGTERM,interrupt)
    signal.signal(signal.SIGINT,interrupt)
    signal.signal(signal.SIGALRM,interrupt)
    signal.setitimer(signal.ITIMER_REAL,SECONDS)
    receipt = {"protocol":"later-offline-projected-source-graph-completion-v1","started":now(),"status":"FAILED",
        "primary_error":None,"final_errors":[],"new_go_queries":0,"new_native_builds":0,"new_test_methods":0,
        "container_mount_or_privilege_actions":0,"original_result_status":"FAILED",
        "semantic_source_admission":False,"migration_completeness":False,"destination_writes":False,
        "expected_controller_sha":args.expected_controller_sha,"original_controller_sha":ORIGINAL_CONTROL_SHA,
        "original_query_profile_sha256":PROFILE_SHA,"source_read_limit_bytes":READ_LIMIT,
        "duration_limit_seconds":SECONDS,"address_space_limit_bytes":address_limit,
        "prior_address_space_limits":list(prior_address_limits),"expanded_limit_bytes":EXPANDED_LIMIT,
        "compressed_limit_bytes":COMPRESSED_LIMIT,"combined_original_and_new_limit_bytes":TOTAL_LIMIT,
        "native_gates_unchanged":[2950000000,2600000000,2500000000]}
    before = original = captured = plan = None
    try:
        pinned(PROFILE,PROFILE_SHA)
        before = current_source(args.expected_controller_sha)
        receipt["current_source_before"] = save(OUTPUT/"current-source-before.json.gz",before,packed=True)
        original = original_state()
        receipt["original_inputs_before"] = save(OUTPUT/"original-inputs-before.json",original["records"])
        captured = verify_captured_sources(original["source"])
        receipt["captured_source_rows_before"] = save(OUTPUT/"captured-sources-before.json.gz",captured,packed=True)
        plan = dependency_plan((ORIGINAL/"stdout.log").read_bytes())
        require(len(plan["packages"])==1455 and len(plan["modules"])==204 and len(plan["inputs"])==11627,
                "original_dependency_cardinality_changed")
        require(set(GENERATED)=={GENERATED_RELATIVE},"generated_custody_missing")
        receipt["dependency_plan_before"] = save_plan(OUTPUT/"dependency-plan-before.json.gz",plan)
        later_after = verify_later_rows(plan)
        receipt["dependency_plan_after"] = save_plan(OUTPUT/"dependency-plan-after.json.gz",later_after)
        require(receipt["dependency_plan_before"]["expanded_sha256"]==
                receipt["dependency_plan_after"]["expanded_sha256"],"encoded_plan_before_after_changed")
        receipt["packages"] = len(plan["packages"])
        receipt["modules"] = len(plan["modules"])
        receipt["dependency_inputs"] = len(plan["inputs"])
        receipt["later_dependency_rows"] = len(LATER_ROWS)
        receipt["original_generated_rows"] = len(GENERATED)
        receipt["generated_custody"] = GENERATED
        receipt["provenance"] = {
            "query_stdout":"original_complete_exit_zero_output_no_requery",
            "ordinary_dependency_hashes":"later_offline_reads_not_recovered_original_lost_hash_map",
            "captured_source_and_tools":"original_before_after_rows_compared_to_current_bytes_and_full_tuples",
            "generated_test_main":"original_ram_inventory_metadata_and_original_preserved_bytes",
            "logical_plan":"new_offline_completion_not_the_unsaved_original_serialization",
            "new_empty_ram_cache_flag":"describes_original_query_only_no_new_cache_is_created",
        }
    except BaseException as error:
        receipt["primary_error"] = {"type":type(error).__name__,"message":str(error)}
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        for phase in ("original-inputs","captured-source","current-source"):
            try:
                if phase=="original-inputs" and original is not None:
                    after_original = original_state()["records"]
                    require(after_original==original["records"],"original_evidence_changed")
                    receipt["original_inputs_after"] = save(OUTPUT/"original-inputs-after.json",after_original)
                elif phase=="captured-source" and captured is not None:
                    after_captured = verify_captured_sources(original["source"])
                    require(after_captured==captured,"captured_source_changed_during_completion")
                    receipt["captured_source_rows_after"] = save(OUTPUT/"captured-sources-after.json.gz",after_captured,packed=True)
                elif phase=="current-source" and before is not None:
                    after_source = current_source(args.expected_controller_sha)
                    require(after_source==before,"current_source_changed_during_completion")
                    receipt["current_source_after"] = save(OUTPUT/"current-source-after.json.gz",after_source,packed=True)
            except BaseException as error:
                receipt["final_errors"].append({"phase":phase,"type":type(error).__name__,"message":str(error)})
        receipt["finished"] = now()
        receipt["elapsed_seconds"] = time.monotonic()-STARTED
        receipt["read_bytes"] = READ_BYTES
        receipt["free_final"] = free()
        receipt["effective_uid_final"] = os.geteuid()
        if receipt["elapsed_seconds"]>=SECONDS:
            receipt["final_errors"].append({"phase":"final-deadline","message":"offline_completion_deadline"})
        if receipt["free_final"]<FLOOR:
            receipt["final_errors"].append({"phase":"final-capacity","message":"offline_completion_capacity"})
        if receipt["effective_uid_final"]!=1001:
            receipt["final_errors"].append({"phase":"final-identity","message":"ordinary_owner_changed"})
        if receipt["primary_error"] is None and not receipt["final_errors"]:
            receipt["status"] = "PASS_LATER_OFFLINE_SOURCE_GRAPH"
        saved = save(OUTPUT/"result.json",receipt)
        print(json.dumps({"status":receipt["status"],"result":saved,"inputs":receipt.get("dependency_inputs"),
                          "new_go_queries":0,"native_builds":0,"test_methods":0}))
    return 0 if receipt["status"]=="PASS_LATER_OFFLINE_SOURCE_GRAPH" else 1

if __name__=="__main__":
    sys.exit(main())
