#!/usr/bin/env python3
"""Read-only intake of one genuine failed native run; never executes native tests."""
import datetime, hashlib, io, json, pathlib, subprocess, zipfile

OUT = pathlib.Path("/mnt/development/projects/diagnostics/otzaria-native-archive-readiness-20261123/45130249062")
SOURCE = "0ab05476960c6bbc563c12e038f16c6ceb25c1cd"
PREFIX = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
SWIFT = "/mnt/development/projects/git-mirrors/anytype-swift.git"
HEART = "/mnt/development/projects/git-mirrors/anytype-heart.git"
HEART_REV = "d98420b1113536afd08cde6de9a5816f6d27ffff"

def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
def read_git(repo, rev, path):
    return subprocess.run(["runuser", "-u", "ubuntu", "--", "git", "--git-dir="+repo, "show", rev+":"+path],
                          check=True, capture_output=True).stdout
def write(name, data):
    raw = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode()
    (OUT/name).write_bytes(raw)
    return sha(raw)
def check_row(raw, row):
    assert len(raw) == row["bytes"]
    assert sha(raw) == row["sha256"]
    if "git_blob" in row: assert blob(raw) == row["git_blob"]
def json_stream(raw):
    s=raw.decode(); dec=json.JSONDecoder(); pos=0; result=[]
    while pos < len(s):
        while pos < len(s) and s[pos].isspace(): pos+=1
        if pos == len(s): break
        item,end=dec.raw_decode(s,pos); result.append(item); pos=end
    return result

archive=OUT/"original-native-annotation-archive.zip"
raw=archive.read_bytes()
assert len(raw)==2940742 and sha(raw)=="ce3c5bd8b4c3869a99dda8c8d5d0811586c7b5e86cd7e53bbee22e099db69355"
watch=json.loads((OUT/"WATCH_RESULT_1.json").read_text())
assert watch["observed_run"]["id"]==45130249062 and watch["head_sha"]==SOURCE
assert watch["observed_run"]["run_attempt"]==1 and watch["observed_run"]["conclusion"]=="failure"
assert watch["lock_released"] and watch["watch_exit_code"]==0
download=json.loads((OUT/"DOWNLOAD.json").read_text())
assert download["github_digest_matches"] and download["observer_process_absent"] and download["observer_lock_released"]
manifest_raw=read_git(SWIFT,SOURCE,PREFIX+"/slice-a/EXECUTION_INPUTS.json")
assert sha(manifest_raw)=="54b5945e160e7807a7db23550a195dbb5390c00646f174e87d938cb43b8a28db"
manifest=json.loads(manifest_raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    names=z.namelist()
    assert len(names)==39 and len(names)==len(set(names))
    for name in names:
        assert not name.startswith("/") and "\\" not in name and ".." not in pathlib.PurePosixPath(name).parts
    assert z.testzip() is None
    index=json.loads(z.read("EVIDENCE_INDEX.json"))["files"]
    assert len(index)==38 and {x["path"] for x in index}==set(names)-{"EVIDENCE_INDEX.json"}
    assert len({x["path"] for x in index})==38
    for row in index: check_row(z.read(row["path"]),row)
    result=json.loads(z.read("RESULT.json"))
    assert result["control_head"]==SOURCE and result["heart_base"]==HEART_REV and result["status"]=="FAIL"
    assert result["execution_manifest_sha256"]==sha(manifest_raw)
    assert result["archive_admission"]=="NOT_RUN" and not result["historical_controls_replayed"]
    assert result["owned_command_groups_drained"] and result["owned_native_temporary_removed"]
    assert not result["production_import_activated"] and not result["body_ack_authority"]

    source_rows=[]
    keys=("bytes","destination","git_blob","revision","sha256","source_path")
    assert result["source_inputs"] == [{k:r[k] for k in keys} for r in manifest["source_inputs"]]
    for r in manifest["source_inputs"]:
        body=read_git(SWIFT,r["revision"],r["source_path"]);check_row(body,r)
        source_rows.append({**r,"actual_original_git_bytes_match":True})
    assert result["control_inputs"]==manifest["control_inputs"]
    controls=[]
    for r in manifest["control_inputs"]:
        body=read_git(SWIFT,SOURCE,PREFIX+"/"+r["path"]);check_row(body,r)
        controls.append({**r,"actual_final_git_bytes_match":True})
    authored=[]
    for r in manifest["new_native_inputs"]:
        body=read_git(SWIFT,r["source_revision"],PREFIX+"/"+r["path"]);check_row(body,r)
        check_row(read_git(SWIFT,SOURCE,PREFIX+"/"+r["path"]),r)
        authored.append({**r,"actual_authored_revision_bytes_match":True})
    originals=[]
    for r in manifest["original_model_and_rpc_inputs"]:
        check_row(read_git(HEART,HEART_REV,r["path"]),r)
        originals.append({**r,"actual_original_git_bytes_match":True})

    composed=json.loads(z.read("COMPOSED_NATIVE_SOURCES.json"))
    prior_path=PREFIX+"/slice-a/run-45125326998/SOURCE_INTAKE.json"
    prior_raw=read_git(SWIFT,"8e91cea2a09d958e83e7f7c670c82248fd87a077",prior_path)
    assert sha(prior_raw)=="6a362a7d5ff43e7a3000d8698888f6d0266d03f8077517d847ae8de4183ae104"
    prior=json.loads(prior_raw)
    expected=dict(prior["composed_afterimages"])
    changed="core/application/owned_annotation_export_native_test.go"
    expected[changed]=next(x["sha256"] for x in manifest["new_native_inputs"] if x["heart_path"]==changed)
    assert composed["all_declared_afterimages"]==expected and len(expected)==50
    assert composed["unchanged_original_model_proto_rpc_inputs"]==manifest["original_model_and_rpc_inputs"]
    source_receipt={"source_rows":source_rows,"control_rows":controls,"authored_rows":authored,
        "original_model_rpc_rows":originals,"composed_afterimages":expected,
        "reused_prior_source_proof":{"revision":"8e91cea2a09d958e83e7f7c670c82248fd87a077",
        "path":prior_path,"sha256":sha(prior_raw),"same_composed_source_hashes":49,
        "changed_actual_fixture":changed,"native_tests_replayed":False}}
    source_receipt_sha=write("SOURCE_INTAKE.json",source_receipt)

    commands=json.loads(z.read("COMMANDS.json"))
    assert len(commands)==11
    for i,c in enumerate(commands):
        assert c["status"]=="TERMINAL" and not c["timed_out"]
        assert c["effective_returncode"]==(1 if i==10 else 0)
        assert any(x.get("drained") is True for x in c["cleanup"])
        assert sha(z.read(c["stdout"]))==c["stdout_sha256"]
        assert sha(z.read(c["stderr"]))==c["stderr_sha256"]
    assert commands[8]["label"]=="compile-native_exports"
    assert commands[10]["label"]=="execute-native_exports"
    assert not any("archive_admission" in c["label"] for c in commands)
    events=[json.loads(l) for l in z.read("11-execute-native_exports.stdout").decode().splitlines() if l.strip()]
    endings=[{"test":e["Test"],"action":e["Action"],"elapsed":e.get("Elapsed")}
             for e in events if e.get("Test") and e.get("Action") in ("pass","fail","skip")]
    actual_leaf=[x for x in endings if "/" in x["test"]]
    assert {x["test"] for x in actual_leaf}==set(manifest["targets"][0]["expected_cases"])
    assert len(actual_leaf)==4 and all(x["action"]=="fail" for x in actual_leaf)
    fail_texts=[e.get("Output","").strip() for e in events if "actual export lacks its native annotation root/type/Space" in e.get("Output","")]
    assert len(fail_texts)==4

    declared=json.loads(z.read("DECLARED_NATIVE_INPUTS.json"))
    files_by_path={}
    for r in declared["files"]:
        if r["path"] in files_by_path: assert files_by_path[r["path"]]==r
        files_by_path[r["path"]]=r
    records=json_stream(z.read("08-declared-native-inputs.stdout"))
    app_path="github.com/anyproto/anytype-heart/core/application.test"
    root_records=[r for r in records if r.get("ImportPath")==app_path]
    assert len(root_records)==1
    closure={app_path,*root_records[0]["Deps"]}
    native_root=commands[8]["cwd"]
    coverage=[]
    for path,digest in composed["required_actual_compiler_coverage"].items():
        absolute=native_root+"/"+path
        assert files_by_path[absolute]["sha256"]==digest
        variants=[]
        for r in records:
            if r.get("ImportPath") not in closure: continue
            included={r.get("Dir","")+"/"+p for key in ("GoFiles","CgoFiles") for p in r.get(key,[])}
            if absolute in included: variants.append(r["ImportPath"])
        coverage.append({"path":path,"sha256":digest,"declared_in_combined_go_list":True,
                         "included_in_compiled_application_test_closure":bool(variants),
                         "actual_package_variants":variants,"runtime_file_coverage_not_inferred":True})
    missing=[x["path"] for x in coverage if not x["included_in_compiled_application_test_closure"]]
    assert len(coverage)==19 and missing==["core/block/import/owned_annotation_archive_test.go"]
    compiler={"go_package_records":len(records),"combined_declared_required_rows":19,
        "actual_application_test_input_rows":18,"not_compiled_in_this_run":missing,"rows":coverage,
        "actual_successful_compiler_command":commands[8],"native_binary":result["native_binaries"]["native_exports"],
        "post_execution_binary_digest_check_reached":False,
        "post_execution_limit":"The command's nonzero return raises before execute_target's later digest check; no after-run binary equality is claimed.",
        "archive_test_binary_compiled":False,"archive_test_execution":"NOT_RUN",
        "go_list_sha256":sha(z.read("08-declared-native-inputs.stdout"))}
    compiler_sha=write("COMPILER_COVERAGE.json",compiler)

    schema=json.loads(z.read("fixtures/schema-registration.json"))
    phase=json.loads(z.read("fixtures/schema-registration-00.json"))
    assert schema["registration_complete"] and schema["registration_calls"]==1
    assert schema["unique_actual_creates"]==18 and schema["actual_type_apply_calls"]==1 and schema["matching_native_definitions"]==18
    assert phase["error_category"]=="none" and phase["app_admitted"] and phase["observation_disposition"]=="MATCHING_SCHEMA_OBSERVED"
    assert phase["type_apply_invoked"] and phase["type_apply_returned"] and len(phase["creations"])==18
    ids=[]
    for r in phase["creations"]:
        assert r["invoked"] and r["returned_object_id"]==r["before"]["object_id"]==r["after"]["object_id"]
        assert r["before"]["disposition"]==4 and r["after"]["disposition"]==1
        ids.append(r["returned_object_id"])
    assert len(set(ids))==18
    assert len(phase["definitions"])==18
    for r in phase["definitions"]:
        assert r["index"]=="ONE_MATCHING_LOCAL_INDEX_ROW" and not r["persisted_state_conflict"]
        assert r["native"]["disposition"]==1 and r["native"]["space_id"]==phase["observation_space_id"]
    cleanup=json.loads(z.read("fixtures/native-export-cleanup.json"))
    assert cleanup["original_account_stop_returned_or_app_absent"] and cleanup["owned_directory_removed"] and not cleanup["import_started"]
    specimens=[]
    for kind in ("text","format","nested","attachment"):
        member="fixtures/"+kind+".zip";body=z.read(member)
        with zipfile.ZipFile(io.BytesIO(body)) as iz:
            infos=iz.infolist();nms=[x.filename for x in infos]
            assert len(nms)==len(set(nms)) and iz.testzip() is None
            assert sum(x.file_size for x in infos)<8<<20
            assert all(not n.startswith("/") and "\\" not in n and ".." not in pathlib.PurePosixPath(n).parts for n in nms)
            report=json.loads(z.read("fixtures/"+kind+"-export-report.json"))
            specimens.append({"kind":kind,"artifact_member":member,"bytes":len(body),"sha256":sha(body),
                "members":len(nms),"expanded_bytes":sum(x.file_size for x in infos),
                "report":report,"zip_crc_and_safe_unique_inventory":True,
                "exceeds_existing_compressed_65536_budget":len(body)>65536,
                "native_export_calls_returned_and_report_guard_reached":True,
                "native_fixture_leaf":"FAIL","body_style_nested_attachment_assertions_reached":False,
                "archive_controls_executed":False,
                "inventory":[{"path":x.filename,"bytes":x.file_size,"sha256":sha(iz.read(x)),
                    "compressed_bytes":x.compress_size,"method":x.compress_type,"flags":x.flag_bits,
                    "extra_hex":x.extra.hex()} for x in infos]})
    specimen_sha=write("GENUINE_EXPORT_INVENTORY.json",{"status":"ACTUAL_NATIVE_EXPORT_BYTES_RETAINED_NOT_BODY_QUALIFIED","specimens":specimens})

    primary=pathlib.Path("/mnt/development/projects/worktrees/anytype-otzaria-native-import-design-20261123")/PREFIX/"bc-original-import-design"
    primary_binding=json.loads((primary/"SOURCE_BINDINGS.json").read_text())
    dependency=[]
    for r in primary_binding["primary_dependency_sources"]:
        tail="/github.com/anyproto/any-sync@v0.13.8/"+r["path"]
        found=[x for x in files_by_path.values() if x["path"].endswith(tail)]
        assert len(found)==1 and found[0]["bytes"]==r["bytes"] and found[0]["sha256"]==r["sha256"]
        dependency.append({**r,"actual_declared_apple_input":found[0],"source_bytes_match":True})
    modules=[p["module"] for p in declared["packages"] if p.get("module") and p["module"].get("Path")=="github.com/anyproto/any-sync"]
    assert modules and all(m["Version"]=="v0.13.8" and m["Sum"]=="h1:VVcAX/8VHwIB3D3mEaO0v3ojyixrYvaGI1nwgLja3zc=" for m in modules)
    dep_sha=write("ANY_SYNC_ACTUAL_INPUT_MATCH.json",{"status":"SEVEN_PRIMARY_BLOBS_MATCH_ACTUAL_APPLE_DECLARED_MODULE_INPUTS",
        "run":45130249062,"source":SOURCE,"module":modules[0],"files":dependency,"permission_race_executed":False})
    struct_raw=(OUT/"original-struct.pb.go").read_bytes()
    struct_rows=[x for x in files_by_path.values() if x["path"].endswith("/github.com/anyproto/protobuf@v1.3.3-0.20240201225420-6e325cf0ac38/types/struct.pb.go")]
    assert len(struct_rows)==1
    check_row(struct_raw,struct_rows[0])
    write("PROTOBUF_STRUCT_ACTUAL_INPUT_MATCH.json",{"actual_input":struct_rows[0],"source_git_blob":blob(struct_raw),"scope":"Original generated Struct tags for bounded forensic wire inspection, not a new generated runtime."})

    intake={"schema":1,"status":"AUTHENTICATED_NATIVE_FAILURE_WITH_FOUR_ORIGINAL_EXPORTS","run_id":45130249062,
        "source_sha":SOURCE,"run_attempt":1,"artifact_id":14798506507,"artifact_bytes":len(raw),
        "artifact_sha256":sha(raw),"github_digest_matches":True,"safe_unique_crc_members":39,"index_rows_verified":38,
        "native_application_binary_compiled":True,"native_leaf_pass":0,"native_leaf_fail":4,"native_leaf_skip":0,
        "native_parent_outcomes":[x for x in endings if "/" not in x["test"]],"native_leaf_outcomes":actual_leaf,
        "failure_assertion":fail_texts[0],"actual_registration_calls":1,"actual_unique_schema_creates":18,"actual_type_apply_calls":1,
        "actual_original_export_zip_count":4,"export_body_fidelity_qualified":False,"archive_control_cases_executed":0,
        "archive_control_binary_compiled":False,"all_11_commands_terminal_and_drained":True,
        "cleanup":cleanup,"owned_native_temporary_removed":True,"observer_process_absent":True,"observer_lock_released":True,
        "source_intake_sha256":source_receipt_sha,"compiler_coverage_sha256":compiler_sha,"specimen_inventory_sha256":specimen_sha,
        "actual_any_sync_input_match_sha256":dep_sha,"historical_native_tests_replayed":False,
        "production_import_activated":False,"body_ack_authority":False,"cold_reopen_qualified":False,
        "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    intake_sha=write("INTAKE.json",intake)
    print(json.dumps({"status":intake["status"],"intake_sha256":intake_sha,"source_sha256":source_receipt_sha,
        "compiler_sha256":compiler_sha,"specimen_inventory_sha256":specimen_sha,"any_sync_match_sha256":dep_sha,
        "source_rows":len(source_rows),"control_rows":len(controls),"authored_rows":len(authored),"original_rows":len(originals),
        "native_leaf_counts":{"pass":0,"fail":4,"skip":0},"original_exports":4,"archive_cases":0}))
