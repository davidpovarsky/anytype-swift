#!/usr/bin/env python3
"""Install a genuinely qualified original Import ABI into an owned SDK checkout.

The complete API-authenticated artifact is stream-validated, including CRC, SHA256
and Git blob identities. Only exact generated scopes and the actual Lib product
are selected. Production mode verifies already committed generated postimages and
installs only an absent Lib. An explicit preimage-overlay mode is also available.
This performs no generation, compiler tests, or generic dirty-tree exemption.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

SCOPES = [
    "Modules/ProtobufMessages/Sources/Protocol",
    "Modules/ProtobufMessages/Sources/Generated/CommandsInvocation",
    "Modules/ProtobufMessages/Sources/Generated/service+invocation.swift",
    "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey.swift",
    "Modules/Services/Sources/Generated/BundledPropertiesValueProvider.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey+SystemKeys.swift",
    "Modules/Services/Sources/Generated/BundledPropertyKey+internalKeys.swift",
    "Modules/Services/Sources/Generated/ObjectTypeUniqueKey+Bundled.swift",
    "Dependencies/Middleware/protobuf",
    "Dependencies/Middleware/genmodels",
    "Dependencies/Middleware/json",
]
LIB = "Dependencies/Middleware/Lib.xcframework"
EXPORTS = ["ServiceAnnotationSchemaRegister","ServiceAnnotationImport","ServiceAnnotationImportCancel"]
REPOSITORY = "davidpovarsky/anytype-swift"
SWIFT = "997e285617d57b31c4205976f01019819fa29a03"

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def safe_name(name):
    p = PurePosixPath(name)
    require(bool(name) and str(p) == name and not p.is_absolute()
            and ".." not in p.parts and "\0" not in name and "\\" not in name,
            "Noncanonical artifact path")
    return name

def sha_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def byte_row(raw, name):
    return {"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
            "git_blob":hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}

def stream_row(stream, name, size):
    sha, git = hashlib.sha256(),hashlib.sha1()
    git.update(b"blob " + str(size).encode() + b"\0")
    count = 0
    while chunk := stream.read(1024*1024):
        count += len(chunk)
        sha.update(chunk)
        git.update(chunk)
    require(count == size,"Artifact or source size changed while reading")
    return {"path":name,"bytes":count,"sha256":sha.hexdigest(),"git_blob":git.hexdigest()}

def file_row(path, name):
    require(path.is_file() and not path.is_symlink(),"Unexpected source type")
    with path.open("rb") as stream:
        return stream_row(stream,name,path.stat().st_size)

def api(endpoint):
    result = subprocess.run(["gh","api","repos/" + REPOSITORY + "/" + endpoint],
        capture_output=True,timeout=60,check=False)
    require(result.returncode == 0,"Authenticated GitHub metadata request failed")
    return json.loads(result.stdout)

def authenticate(archive, pin):
    require(pin["schema"] == "otzaria.original-import-rpc-abi-install-pin/2",
            "Unrecognized ABI installation pin")
    run = api("actions/runs/" + str(pin["run_id"]))
    artifact = api("actions/artifacts/" + str(pin["artifact_id"]))
    require(run["id"] == pin["run_id"] and run["head_sha"] == pin["head_sha"]
        and run["head_branch"] == pin["head_branch"] and run["path"] == pin["workflow_path"]
        and run["run_attempt"] == 1 and run["event"] == "push"
        and run["status"] == "completed" and run["conclusion"] == "success"
        and run["repository"]["full_name"] == REPOSITORY,
        "Original ABI run identity/outcome differs")
    require(artifact["id"] == pin["artifact_id"] and artifact["name"] == pin["artifact_name"]
        and artifact["size_in_bytes"] == pin["artifact_bytes"] and not artifact["expired"]
        and artifact["digest"] == "sha256:" + pin["artifact_sha256"]
        and artifact["workflow_run"]["id"] == pin["run_id"]
        and artifact["workflow_run"]["head_sha"] == pin["head_sha"],
        "Original ABI artifact identity differs")
    require(archive.is_file() and not archive.is_symlink()
        and archive.stat().st_size == pin["artifact_bytes"]
        and sha_file(archive) == pin["artifact_sha256"],"Original ABI archive bytes differ")
    return {"run":run,"artifact":artifact}

def verify_archive(zipped, pin):
    entries = zipped.infolist()
    names = [entry.filename for entry in entries]
    require(len(names) == pin["archive_member_count"] and len(set(names)) == len(names)
        and sum(entry.file_size for entry in entries) == pin["archive_uncompressed_bytes"]
        and max(entry.file_size for entry in entries) == pin["archive_largest_member_bytes"],
        "Measured complete ABI artifact inventory differs")
    for entry in entries:
        safe_name(entry.filename)
        require(not entry.is_dir() and stat.S_IFMT(entry.external_attr >> 16) in (0,stat.S_IFREG)
                and not entry.flag_bits & 1,"Unexpected encrypted/directory/symlink artifact member")
    require(zipped.getinfo("EVIDENCE_INDEX.json").file_size <= 16*1024*1024,"Oversized evidence index")
    index = json.loads(zipped.read("EVIDENCE_INDEX.json"))["files"]
    indexed = {row["path"]:row for row in index}
    require(len(indexed) == len(index) and set(indexed) == set(names)-{"EVIDENCE_INDEX.json"},
            "Complete ABI evidence coverage differs")
    for entry in entries:
        if entry.filename == "EVIDENCE_INDEX.json":
            continue
        expected = indexed[entry.filename]
        require(set(expected) == {"path","bytes","sha256","git_blob"},"ABI evidence index row schema differs")
        with zipped.open(entry) as stream:
            # ZipExtFile checks CRC when the complete member reaches EOF.
            actual = stream_row(stream,entry.filename,entry.file_size)
        require(actual == expected,"ABI evidence member identity/CRC differs: " + entry.filename)
    return indexed

def qualification_proofs(zipped, indexed, install, result, pin):
    """Require all three exact indexed proofs and the final source-bound case IDs."""
    def read_json(name):
        return json.loads(zipped.read(name))
    proof_names = ("generation_qualification", "changed_swift_qualification", "final_native_rpc_union")
    require(set(install["qualification_receipts"]) == set(proof_names),
            "The complete generation/Swift/final-union proof set is required")
    for name in proof_names:
        proof = install[name]
        require(all(proof[key] == pin[name][key] for key in
                    ("source", "run_id", "artifact_id", "artifact_sha256"))
                and proof["status"] == "PASS" and result[name] == proof,
                "Exact qualification identity differs: " + name)
        receipt = install["qualification_receipts"][name]
        safe_name(receipt["path"])
        require(indexed.get(receipt["path"]) == receipt and read_json(receipt["path"]) == proof,
                "Qualification proof is not its exact indexed receipt")
    generation = install["generation_qualification"]
    swift = install["changed_swift_qualification"]
    union = install["final_native_rpc_union"]
    require(generation["aggregate_producer_outcome"] == "FAIL"
            and generation["output_counts"] == {"native":11,"swift":696,"middleware":37}
            and generation["prior_whole_protocol_typecheck"] == "PASS_FOR_UNCHANGED_FILES_ONLY"
            and generation["generators_replayed_by_abi"] == 0
            and generation["native_generated_tree"] == install["generated_native_tree"]
            and generation["generated_index_sha256"] == pin["generated_index_sha256"],
            "Authentic generation proof was changed or overstated")
    require(swift["primary_count"] == 2 and swift["input_files"] == 689
            and swift["typecheck_invocations"] == 1
            and swift["generated_index_sha256"] == generation["generated_index_sha256"]
            and not swift["generation_replayed"] and not swift["full_sdk_typechecked"],
            "Actual changed-Swift qualification differs")
    schema_ids = union["schema_closure_case_ids"]
    require(isinstance(schema_ids, list) and schema_ids
            and all(isinstance(name, str) and "::" in name and "/" in name for name in schema_ids)
            and schema_ids == sorted(set(schema_ids))
            and schema_ids == pin["final_native_rpc_union"]["schema_closure_case_ids"],
            "Exact final source-bound schema test identities differ")
    relation_ids = union["relation_target_closure_case_ids"]
    require(isinstance(relation_ids, list) and len(relation_ids) == 8
            and all(isinstance(name, str) and "::" in name and "/" in name for name in relation_ids)
            and relation_ids == sorted(set(relation_ids))
            and relation_ids == pin["final_native_rpc_union"]["relation_target_closure_case_ids"]
            and not set(relation_ids) & set(schema_ids),
            "The separate eight relation-target source test identities differ")
    counts = {name: {"passes":count,"failures":0,"skipped":0,"not_run":0} for name,count in
              (("native9",9),("rpc9",9),("cancel_panic",1),("bundled_semantic",6),
               ("schema_closure",len(schema_ids)),("relation_target_closure",len(relation_ids)))}
    require(union["counts"] == counts
            and union["execution_manifest_sha256"] == pin["final_native_rpc_union"]["execution_manifest_sha256"]
            and union["canonical_native_tree"] == pin["native_source_tree"]
            and type(union["source_files"]) is int and type(union["required_compiler_inputs"]) is int
            and 0 < union["required_compiler_inputs"] <= union["source_files"]
            and union["source_files"] == pin["final_native_rpc_union"]["source_files"]
            and union["required_compiler_inputs"] == pin["final_native_rpc_union"]["required_compiler_inputs"]
            and union["source_module_link_stability"] == "PASS"
            and union["owned_native_temporary_removed"] and union["owned_command_groups_drained"]
            and union["native_tests_replayed"] == 0 and not union["full_sdk_acceptance"]
            and not union["body_ack_authority"],
            "The complete original Native/RPC union qualification differs")

def payload(zipped, indexed, pin):
    def read_json(name):
        return json.loads(zipped.read(name))
    result = read_json("RESULT.json")
    require(result["schema"] == "otzaria.original-import-rpc-abi/2" and result["status"] == "PASS"
        and result["control_head"] == pin["head_sha"] and result["pin_sha256"] == pin["abi_source_pin_sha256"]
        and result["original_mobile_abi_built"] and result["original_protobufmessages_and_invocation_linked"]
        and result["source_and_invocation_unchanged"] and result["owned_command_groups_drained"]
        and result["owned_work_removed"] and result["cleanup"]["removed"]
        and result["native_source_tree"] == pin["native_source_tree"]
        and result["generator_invocations"] == 0 and result["historical_tests_replayed"] == 0
        and result["native_import_executions"] == 0 and not result["full_editor_compiled"],
        "Original ABI source/compile/link/cleanup gates did not pass")
    install = read_json("RPC_ABI_INSTALLATION.json")
    require(install["schema"] == "otzaria.original-import-rpc-abi-installation/2"
        and install["abi_control_head"] == pin["head_sha"]
        and install["abi_pin_sha256"] == pin["abi_source_pin_sha256"]
        and install["native_source_tree"] == pin["native_source_tree"]
        and install["original_swift_base"] == SWIFT
        and install["lib_destination"] == LIB
        and install["lib_marker"] == "otzaria-original-import-rpc-" + pin["native_source_tree"]
        and install["required_defined_exports"] == EXPORTS
        and install["full_original_protobufmessages_invocation_linked"]
        and not install["full_sdk_owner_typechecked"] and not install["native_import_replayed"],
        "Original ABI installation contract differs")
    qualification_proofs(zipped, indexed, install, result, pin)
    for field in ("swift_preimage_index","generated_output_index","lib_index","mobile_slices","mobile_exports"):
        item = install[field]
        safe_name(item["path"])
        require(indexed.get(item["path"]) == item,"Installation inventory is not the indexed exact file")
    before = read_json(install["swift_preimage_index"]["path"])
    generated = read_json(install["generated_output_index"]["path"])
    require(install["generated_output_index"]["sha256"] == pin["generated_index_sha256"],
            "Installed generated output family differs from all three qualified inputs")
    framework = read_json(install["lib_index"]["path"])
    require(before["swift_base"] == SWIFT and before["scopes"] == SCOPES
        and set(generated) == {"native","swift","middleware"}
        and framework["marker"] == install["lib_marker"],"Original generated scope/index differs")
    destinations = {}
    for family in ("swift","middleware"):
        for row in generated[family]:
            destination = safe_name(row["path"])
            require(any(destination == scope or destination.startswith(scope+"/") for scope in SCOPES),
                    "Generated destination escapes original scope")
            require(destination not in destinations,"Duplicate generated destination")
            member = "generated/candidate/swift/" + destination
            require(indexed.get(member) == {**row,"path":member},"Generated row is not the actual indexed artifact")
            destinations[destination] = {"member":member,"row":row}
    expected_sources = sorted([r for f in ("swift","middleware") for r in generated[f]],key=lambda r:r["path"])
    framework_rows = framework["files"]
    require(len({r["path"] for r in framework_rows}) == len(framework_rows)
        and len(framework_rows) == install["lib_file_count"]
        and sum(r["bytes"] for r in framework_rows) == install["lib_total_bytes"]
        and max(r["bytes"] for r in framework_rows) == install["lib_largest_member_bytes"],
        "Measured original Lib inventory differs")
    for row in framework_rows:
        relative = safe_name(row["path"])
        destination,member = LIB + "/" + relative,"products/Lib.xcframework/" + relative
        require(indexed.get(member) == {**row,"path":member},"Lib member is not the actual indexed artifact")
        require(destination not in destinations,"Duplicate Lib destination")
        destinations[destination] = {"member":member,"row":{**row,"path":destination}}
    require(len({name.casefold() for name in destinations}) == len(destinations),
            "Artifact destinations collide on the Apple filesystem")
    return install,before,expected_sources,framework_rows,destinations

def check_parents(root, relative):
    safe_name(relative)
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
        require(not path.is_symlink(),"Refusing a source destination symlink")
    require(path.resolve().is_relative_to(root),"Source destination escapes checkout")
    return path

def inventory(root, scopes):
    rows = {}
    for scope in scopes:
        path = check_parents(root,scope)
        if not path.exists():
            continue
        paths = [path] if path.is_file() else list(path.rglob("*"))
        for item in paths:
            require(not item.is_symlink(),"Unexpected source-scope symlink")
            if item.is_dir():
                continue
            require(item.is_file(),"Unexpected source-scope filesystem type")
            name = item.relative_to(root).as_posix()
            require(name not in rows,"Overlapping source-scope inventories")
            rows[name] = file_row(item,name)
    return sorted(rows.values(),key=lambda r:r["path"])

def git_output(target, *args):
    result = subprocess.run(["git", "-C", str(target), *args],
        capture_output=True, timeout=60, check=False)
    require(result.returncode == 0, "Original SDK Git verification failed")
    return result.stdout

def verify_committed_generated(target, expected_sources):
    """Require exact working bytes and HEAD blobs, with no generated writes."""
    target = Path(target).resolve()
    actual_root = Path(git_output(target, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    require(actual_root == target, "Explicit SDK checkout root required")
    head = git_output(target, "rev-parse", "HEAD").decode().strip()
    require(len(head) == 40 and all(c in "0123456789abcdef" for c in head),
            "SDK HEAD identity is invalid")
    require(not git_output(target, "status", "--porcelain", "--untracked-files=no"),
            "SDK tracked source is not clean")
    require(inventory(target, SCOPES) == expected_sources,
            "Committed generated working bytes differ from the authenticated postimages")
    raw = git_output(target, "ls-tree", "-r", "-z", "--full-tree", "HEAD", "--", *SCOPES)
    observed = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split(" ")
        name = safe_name(name.decode())
        require(mode in ("100644", "100755") and kind == "blob" and name not in observed,
                "Unexpected generated Git record")
        observed[name] = blob
    expected = {entry["path"]: entry["git_blob"] for entry in expected_sources}
    require(len(expected) == len(expected_sources) and observed == expected,
            "Generated HEAD blob inventory differs from the authenticated postimages")
    return {"head": head, "working_files": len(expected_sources),
            "head_git_blobs": len(observed), "tracked_source_clean": True}

def install_archive(archive, target, pin, receipt_path, generated_mode="committed-postimages"):
    require(target.is_dir() and target != Path("/") and not target.is_symlink(),
            "Explicit owned SDK source checkout required")
    target = target.resolve()
    require(generated_mode in ("committed-postimages", "preimage-overlay"),
            "Unknown generated source installation mode")
    require(not receipt_path.exists(),"Refusing to overwrite an existing installation receipt")
    require(all(receipt_path != target / scope and not receipt_path.is_relative_to(target / scope)
                for scope in SCOPES + [LIB]), "Receipt must be outside installed source/product scopes")
    metadata = authenticate(archive,pin)
    with zipfile.ZipFile(archive) as zipped:
        indexed = verify_archive(zipped,pin)
        installation,before,expected_sources,framework_rows,destinations = payload(zipped,indexed,pin)
        committed_source = None
        if generated_mode == "committed-postimages":
            committed_source = verify_committed_generated(target, expected_sources)
            selected = {path: item for path, item in destinations.items() if path.startswith(LIB + "/")}
            install_scopes = [LIB]
        else:
            require(inventory(target,SCOPES) == sorted(before["files"],key=lambda r:r["path"]),
                    "Prepared SDK generated source does not match original qualified preimages")
            require(sorted(scope for scope in SCOPES if not (target / scope).exists()) ==
                    sorted(before["absent_scopes"]),"Original absent source scopes differ")
            selected, install_scopes = destinations, SCOPES + [LIB]
        require(not check_parents(target,LIB).exists(),"Refusing a previous or foreign Lib installation")
        selected_bytes = sum(item["row"]["bytes"] for item in selected.values())
        require(shutil.disk_usage(target.parent).free >= selected_bytes + 128*1024*1024,
                "Insufficient owned volume capacity for measured original ABI products")
        stage = Path(tempfile.mkdtemp(prefix=".otzaria-import-abi-install-",dir=target.parent))
        marker = json.dumps({"target":str(target),"source":pin["head_sha"],"pid":os.getpid()},sort_keys=True)
        (stage / "OWNER.json").write_text(marker)
        committed,backed_up = [],[]
        try:
            fresh,backup = stage / "new",stage / "before"
            for destination,item in selected.items():
                path = fresh / destination
                path.parent.mkdir(parents=True,exist_ok=True)
                with zipped.open(item["member"]) as source,path.open("xb") as sink:
                    shutil.copyfileobj(source,sink,1024*1024)
                require(file_row(path,destination) == item["row"],"Staged ABI product differs")
                permissions = (zipped.getinfo(item["member"]).external_attr >> 16) & 0o777
                path.chmod(permissions or 0o644)
            if generated_mode == "preimage-overlay":
                require(inventory(fresh,SCOPES) == expected_sources,"Staged generated inventory differs")
            else:
                require(not inventory(fresh,SCOPES), "Committed mode staged a generated source write")
            for scope in install_scopes:
                current,prepared = check_parents(target,scope),check_parents(fresh,scope)
                require(prepared.exists(),"Required generated/Lib scope is absent from actual artifact")
                if current.exists():
                    previous = backup / scope
                    previous.parent.mkdir(parents=True,exist_ok=True)
                    os.replace(current,previous)
                    backed_up.append(scope)
                current.parent.mkdir(parents=True,exist_ok=True)
                os.replace(prepared,current)
                committed.append(scope)
            require(inventory(target,SCOPES) == expected_sources,"Installed generated source differs")
            if committed_source is not None:
                require(verify_committed_generated(target, expected_sources) == committed_source,
                        "Committed generated source or HEAD changed during Lib installation")
            expected_lib = sorted([{**r,"path":LIB+"/"+r["path"]} for r in framework_rows],key=lambda r:r["path"])
            require(inventory(target,[LIB]) == expected_lib,"Installed Lib differs")
            result = {"schema":"otzaria.original-import-rpc-abi-installation-receipt/2","status":"PASS",
                "utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "target":str(target),"api_run_id":metadata["run"]["id"],"source":pin["head_sha"],
                "artifact_id":pin["artifact_id"],"artifact_sha256":pin["artifact_sha256"],
                "all_crc_members":pin["archive_member_count"],"all_indexed_members":len(indexed),
                "complete_uncompressed_bytes_verified":pin["archive_uncompressed_bytes"],
                "selected_product_bytes":selected_bytes,
                "generated_mode":generated_mode,"committed_generated_source":committed_source,
                "verified_generated_files":len(expected_sources),
                "installed_generated_files":len(expected_sources) if generated_mode == "preimage-overlay" else 0,
                "installed_lib_files":len(framework_rows),"installation":installation,
                "generated_typechecks_replayed":0,"native_tests_replayed":0,"abi_builds_replayed":0,
                "full_sdk_acceptance":"NOT_ESTABLISHED_BY_INSTALLATION",
                "scope":"Exact source/product installation only; complete original SDK, Host and runtime acceptance remain required."}
            receipt_path.parent.mkdir(parents=True,exist_ok=True)
            with receipt_path.open("x") as receipt:
                receipt.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
        except BaseException:
            # Only paths admitted and moved by this call are touched on rollback.
            for scope in reversed(committed):
                current = target / scope
                displaced = stage / "failed-new" / scope
                displaced.parent.mkdir(parents=True,exist_ok=True)
                if current.exists():
                    os.replace(current,displaced)
            for scope in reversed(backed_up):
                previous,current = backup / scope,target / scope
                current.parent.mkdir(parents=True,exist_ok=True)
                os.replace(previous,current)
            raise
        finally:
            require((stage / "OWNER.json").read_text() == marker,"Owned install staging marker changed")
            shutil.rmtree(stage)
    return result

def main():
    parser = argparse.ArgumentParser(__doc__)
    for name in ("archive","target","pin","pin-sha256","receipt"):
        parser.add_argument("--"+name,required=True)
    parser.add_argument("--generated-mode", choices=("committed-postimages", "preimage-overlay"),
                        default="committed-postimages")
    args = parser.parse_args()
    pin_path = Path(args.pin).resolve()
    require(sha_file(pin_path) == args.pin_sha256,"Exact artifact installation pin differs")
    pin = json.loads(pin_path.read_bytes())
    result = install_archive(Path(args.archive).resolve(),Path(args.target),pin,Path(args.receipt).resolve(),args.generated_mode)
    print(json.dumps({key:result[key] for key in ("status","source","artifact_id","installed_generated_files","installed_lib_files")}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
