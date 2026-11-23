#!/usr/bin/env python3
"""Authenticate one retained native result. Never executes native tests or CI."""
import datetime, hashlib, io, json, pathlib, subprocess, zipfile
OUT=pathlib.Path("/mnt/development/projects/diagnostics/otzaria-native-annotation-budget-20261123/45139622096")
SOURCE="2da5419fa8b3e90ecca248ee9c83fd5055d8bca6"
PREFIX="docs/pinkha/torah-integration/native-owned-annotation-contract-20261123"
SWIFT="/mnt/development/projects/git-mirrors/anytype-swift.git"
HEART="/mnt/development/projects/git-mirrors/anytype-heart.git"
HEART_REV="d98420b1113536afd08cde6de9a5816f6d27ffff"
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def git(repo,rev,path):
    return subprocess.run(["runuser","-u","ubuntu","--","git","--git-dir="+repo,"show",rev+":"+path],check=True,capture_output=True).stdout
def write(name,data):
    raw=(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    (OUT/name).write_bytes(raw);return sha(raw)
def check(raw,row):
    assert len(raw)==row["bytes"] and sha(raw)==row["sha256"],row
    if "git_blob" in row: assert blob(raw)==row["git_blob"],row
def stream(raw):
    s=raw.decode();dec=json.JSONDecoder();pos=0;out=[]
    while pos<len(s):
        while pos<len(s) and s[pos].isspace(): pos+=1
        if pos==len(s): break
        item,end=dec.raw_decode(s,pos);out.append(item);pos=end
    return out
raw=(OUT/"original-native-archive.zip").read_bytes()
assert len(raw)==2983282 and sha(raw)=="428f7c124649d7d40067b31704b63742a9da17e35425a9f8a3b1ab89839c9df9"
artifact=json.loads((OUT/"ARTIFACTS.json").read_text())["artifacts"]
assert len(artifact)==1
artifact=artifact[0]
assert artifact["id"]==14802738032 and artifact["digest"]=="sha256:"+sha(raw)
assert artifact["workflow_run"]["id"]==45139622096 and artifact["workflow_run"]["head_sha"]==SOURCE
watch=json.loads((OUT/"WATCH_RESULT_1.json").read_text())
assert watch["observed_run"]["id"]==45139622096 and watch["head_sha"]==SOURCE
assert watch["observed_run"]["run_attempt"]==1 and watch["observed_run"]["conclusion"]=="failure"
assert watch["lock_released"] and watch["watch_exit_code"]==0
closed=json.loads((OUT/"OBSERVER_CLOSED.json").read_text())
assert closed["process_absent"] and closed["exclusive_lock_reacquired_and_released"]
manifest_raw=git(SWIFT,SOURCE,PREFIX+"/slice-a/EXECUTION_INPUTS.json")
assert sha(manifest_raw)=="34c60165bc4f98530055b96d514a756515ac0270ca76f2abd876299eb62db61d"
manifest=json.loads(manifest_raw)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    names=z.namelist()
    assert len(names)==51 and len(set(names))==51 and z.testzip() is None
    assert all(not n.startswith("/") and "\\" not in n and ".." not in pathlib.PurePosixPath(n).parts for n in names)
    index=json.loads(z.read("EVIDENCE_INDEX.json"))["files"]
    assert len(index)==50 and len({r["path"] for r in index})==50
    assert {r["path"] for r in index}==set(names)-{"EVIDENCE_INDEX.json"}
    for row in index: check(z.read(row["path"]),row)
    result=json.loads(z.read("RESULT.json"))
    assert result["control_head"]==SOURCE and result["heart_base"]==HEART_REV
    assert result["status"]=="FAIL" and result["error"]=="Unexpected specimen evidence files"
    assert result["execution_manifest_sha256"]==sha(manifest_raw)
    assert result["owned_command_groups_drained"] and result["owned_native_temporary_removed"]
    assert not any(result[k] for k in ("historical_controls_replayed","production_import_activated","body_ack_authority","cold_reopen_qualified","swift_invocation_qualified","generated_rpc_changes"))
    source_rows=[]
    keys=("bytes","destination","git_blob","revision","sha256","source_path")
    assert result["source_inputs"]==[{k:r[k] for k in keys} for r in manifest["source_inputs"]]
    for r in manifest["source_inputs"]:
        check(git(SWIFT,r["revision"],r["source_path"]),r)
        source_rows.append({**r,"exact_original_git_bytes_match":True})
    assert result["control_inputs"]==manifest["control_inputs"]
    controls=[]
    for r in manifest["control_inputs"]:
        check(git(SWIFT,SOURCE,PREFIX+"/"+r["path"]),r)
        controls.append({**r,"exact_final_git_bytes_match":True})
    authored=[]
    for r in manifest["new_native_inputs"]:
        check(git(SWIFT,r["source_revision"],PREFIX+"/"+r["path"]),r)
        check(git(SWIFT,SOURCE,PREFIX+"/"+r["path"]),r)
        authored.append({**r,"exact_source_and_run_revision_bytes_match":True})
    originals=[]
    for r in manifest["original_model_and_rpc_inputs"]:
        check(git(HEART,HEART_REV,r["path"]),r)
        originals.append({**r,"exact_original_git_bytes_match":True})
    prior_path=PREFIX+"/slice-a/run-45130249062/SOURCE_INTAKE.json"
    prior_raw=git(SWIFT,"9357b53ff8230128d1f3340118ec152770feb12a",prior_path)
    prior=json.loads(prior_raw)
    composed=json.loads(z.read("COMPOSED_NATIVE_SOURCES.json"))
    expected=dict(prior["composed_afterimages"])
    changed=[]
    for r in manifest["new_native_inputs"]:
        name=r["heart_path"]
        if expected[name]!=r["sha256"]: changed.append(name)
        expected[name]=r["sha256"]
    assert composed["all_declared_afterimages"]==expected and len(expected)==50 and len(changed)==3
    assert composed["unchanged_original_model_proto_rpc_inputs"]==manifest["original_model_and_rpc_inputs"]
    source_sha=write("SOURCE_INTAKE.json",{
        "source_revision":SOURCE,"manifest_sha256":sha(manifest_raw),
        "source_rows":source_rows,"control_rows":controls,"authored_rows":authored,
        "original_model_rpc_rows":originals,"composed_afterimages":expected,
        "prior_composition":{"revision":"9357b53ff8230128d1f3340118ec152770feb12a","path":prior_path,
            "sha256":sha(prior_raw),"unchanged_afterimages":47,"changed_afterimages":changed},
        "all_bound_source_bytes_authenticated":True,
        "final_runner_source_stability_loop_reached":False,
        "limitation":"The collector raised before the driver's final global source/module/link stability loop. Immutable source admission and actual compiler-declared inputs are retained; an after-all-tests runner tree comparison is not claimed."})
    commands=json.loads(z.read("COMMANDS.json"))
    assert len(commands)==14
    for c in commands:
        assert c["status"]=="TERMINAL" and not c["timed_out"]
        assert c["returncode"]==0 and c["effective_returncode"]==0
        assert any(x.get("drained") is True for x in c["cleanup"])
        assert sha(z.read(c["stdout"]))==c["stdout_sha256"] and sha(z.read(c["stderr"]))==c["stderr_sha256"]
    command_by_label={c["label"]:c for c in commands}
    native=[]
    for target in manifest["targets"]:
        label=target["name"]
        cmd=command_by_label["execute-"+label]
        events=[json.loads(l) for l in z.read(cmd["stdout"]).splitlines() if l.strip()]
        endings=[{"test":e["Test"],"action":e["Action"],"elapsed":e.get("Elapsed")} for e in events
                 if e.get("Test") and e.get("Action") in ("pass","fail","skip")]
        leaves=[x for x in endings if "/" in x["test"]]
        parents=[x for x in endings if "/" not in x["test"]]
        assert len(leaves)==len(target["expected_cases"]) and {x["test"] for x in leaves}==set(target["expected_cases"])
        assert all(x["action"]=="pass" for x in leaves)
        assert len(parents)==1 and parents[0]["test"]==target["parent"] and parents[0]["action"]=="pass"
        assert not any(e["Action"] in ("fail","skip") for e in events)
        observed=result["native_cases"][label]
        assert observed["leaf_cases"]==sorted(target["expected_cases"]) and observed["json_events"]==len(events)
        assert observed["leaf_pass"]==len(leaves) and observed["fail"]==observed["skip"]==observed["original_prior_cases_replayed"]==0
        assert result[label]=="ACTUAL_NATIVE_CASES_PASSED"
        compilecmd=command_by_label["compile-"+label]
        assert compilecmd["argv"][1:5]==["test","-c","-p","2"] and compilecmd["argv"][-1]==target["package"]
        assert "-test.run="+target["selector"] in cmd["argv"] and "-test.count=1" in cmd["argv"]
        native.append({"name":label,"parent":parents[0],"leaves":leaves,"raw_json_events":len(events),
            "raw_stdout_sha256":sha(z.read(cmd["stdout"])),"raw_stdout":cmd["stdout"],
            "native_binary":result["native_binaries"][label],
            "compile_command":compilecmd,"execution_command":cmd,
            "individual_before_after_binary_digest_check_reached":True,
            "basis":"execute_target records ACTUAL_NATIVE_CASES_PASSED only after its individual post-execution digest equality check.",
            "binary_not_retained":True})
    events_sha=write("NATIVE_CASES.json",{"targets":native,"native_exports":{"pass":4,"fail":0,"skip":0},
        "archive_admission":{"pass":32,"fail":0,"skip":0},"native_replay":False})
    declared=json.loads(z.read("DECLARED_NATIVE_INPUTS.json"))
    files={}
    for r in declared["files"]:
        if r["path"] in files: assert files[r["path"]]==r
        files[r["path"]]=r
    records=stream(z.read("08-declared-native-inputs.stdout"))
    heart_root=command_by_label["compile-native_exports"]["cwd"]
    coverage=[]
    closures={}
    for target in manifest["targets"]:
        p=target["import_path"]+".test"
        roots=[r for r in records if r.get("ImportPath")==p]
        assert len(roots)==1
        closures[target["name"]]={p,*roots[0]["Deps"]}
    for path,digest in composed["required_actual_compiler_coverage"].items():
        absolute=heart_root+"/"+path
        assert files[absolute]["sha256"]==digest
        included={}
        for target,closure in closures.items():
            variants=[]
            for r in records:
                if r.get("ImportPath") not in closure: continue
                input_paths={r.get("Dir","")+"/"+p for key in ("GoFiles","CgoFiles") for p in r.get(key,[])}
                if absolute in input_paths: variants.append(r["ImportPath"])
            included[target]=variants
        assert any(included.values()),path
        coverage.append({"path":path,"sha256":digest,"actual_compiled_package_variants":included,
                         "runtime_line_coverage_not_inferred":True})
    assert len(coverage)==19
    assert set(declared["selected_original_packages"])=={t["import_path"] for t in manifest["targets"]}
    model_closure=[]
    for r in manifest["original_model_and_rpc_inputs"]:
        absolute=heart_root+"/"+r["path"]
        if absolute in files: assert files[absolute]["sha256"]==r["sha256"]
        model_closure.append({**r,"in_actual_declared_go_input_files":absolute in files})
    compiler_sha=write("COMPILER_COVERAGE.json",{"go_package_records":len(records),
        "required_rows":19,"all_required_in_union_of_two_actual_compiled_closures":True,
        "per_target_required_rows":{k:sum(bool(r["actual_compiled_package_variants"][k]) for r in coverage) for k in closures},
        "rows":coverage,"original_model_proto_rpc_rows":model_closure,
        "declared_go_list_sha256":sha(z.read("08-declared-native-inputs.stdout")),
        "actual_native_binaries":result["native_binaries"],
        "individual_post_execution_binary_hash_checks_reached":True,
        "final_global_source_module_library_binary_checks_reached":False,
        "limitations":"Actual input closure is authenticated before compilation. Native executables were each checked after their own successful invocation, then deleted during owned cleanup. Global post-collector source/link verification was not reached; no retained-binary rehash or complete Apple SDK header closure is claimed."})
    final=json.loads(z.read("fixtures/schema-registration.json"))
    phases=[json.loads(z.read("fixtures/schema-registration-"+x+".json")) for x in ("00","01")]
    assert final["registration_complete"] and final["registration_calls"]==2
    assert final["unique_actual_creates"]==18 and final["actual_type_apply_calls"]==1 and final["matching_native_definitions"]==18
    assert phases[0]["phase"]==0 and phases[1]["phase"]==1
    assert phases[0]["error_category"]=="unresolved" and phases[0]["observation_disposition"]=="INCOMPLETE_OR_UNRESOLVED"
    assert phases[1]["error_category"]=="none" and phases[1]["observation_disposition"]=="MATCHING_SCHEMA_OBSERVED"
    assert all(p["app_admitted"] and p["historical_call_phase_only"] and not p["body_ack_authority"] for p in phases)
    assert len(phases[0]["creations"])==18 and not phases[1]["creations"]
    assert not phases[0]["type_apply_invoked"] and not phases[0]["type_apply_returned"]
    assert phases[1]["type_apply_invoked"] and phases[1]["type_apply_returned"]
    identities=[]
    for c in phases[0]["creations"]:
        assert c["invoked"] and c["returned_object_id"]==c["before"]["object_id"]==c["after"]["object_id"]
        assert c["before"]["disposition"]==4
        expected_after=5 if c["before"]["native_key"]=="ot-pinkhatorahannotationv1" else 1
        assert c["after"]["disposition"]==expected_after
        identities.append(c["returned_object_id"])
    assert len(set(identities))==18
    assert len(phases[1]["definitions"])==18
    for r in phases[1]["definitions"]:
        assert r["index"]=="ONE_MATCHING_LOCAL_INDEX_ROW" and not r["persisted_state_conflict"]
        assert r["native"]["disposition"]==1 and r["native"]["space_id"]==phases[1]["observation_space_id"]
    assert {r["native"]["object_id"] for r in phases[1]["definitions"]}==set(identities)
    schema_sha=write("SCHEMA_HISTORY_INTAKE.json",{"final":final,
        "phases":[{"file":"fixtures/schema-registration-%02d.json"%i,"sha256":sha(z.read("fixtures/schema-registration-%02d.json"%i)),
            "phase":p["phase"],"error_category":p["error_category"],"observation_disposition":p["observation_disposition"],
            "actual_creates":len(p["creations"]),"type_apply_invoked":p["type_apply_invoked"],
            "type_apply_returned":p["type_apply_returned"]} for i,p in enumerate(phases)],
        "same_18_actual_native_ids_across_history":True,"phase_00_is_real_unresolved_history_not_hidden":True,
        "phase_00_creation_observations":{"17_relation_after_dispositions":1,"type_after_disposition":5,
            "type_after_meaning":"FixedSchemaChangedWhileReading"},
        "disposition_source":{"revision":"7496e47fa4d37b0117abeae6b35ca5f4c8eaf638",
            "path":"docs/pinkha/torah-integration/native-annotation-schema-readback-20261122/native/core/block/object/objectcreator/fixed_schema_observer.go",
            "sha256":"f591939d759e733a37e776d189de36d597ddd30cab284142f82aa8de9de51d89"}})
    cleanup=json.loads(z.read("fixtures/native-export-cleanup.json"))
    assert cleanup["original_account_stop_returned_or_app_absent"] and cleanup["owned_directory_removed"]
    assert not cleanup["import_started"] and not cleanup["body_ack_authority"] and not cleanup["cold_reopen_qualified"]
    specimens=[]
    for kind in ("text","format","nested","attachment"):
        member="fixtures/"+kind+".zip";body=z.read(member)
        fixture=json.loads(z.read("fixtures/"+kind+"-manifest.json"))
        report=json.loads(z.read("fixtures/"+kind+"-export-report.json"))
        assert fixture["archive_bytes"]==len(body) and fixture["archive_sha256"]==sha(body)
        assert fixture["native_text_format_nested_attachment_checks_passed"] and fixture["original_export_report_success"]
        assert report.get("status",0)==0 and report["succeed"]==len(fixture["generated_snapshot_ids"])
        assert report.get("objectErrors",0)==report.get("fileErrors",0)==0 and not report.get("issues",[])
        with zipfile.ZipFile(io.BytesIO(body)) as iz:
            infos=iz.infolist();ns=[x.filename for x in infos]
            assert len(ns)==len(set(ns)) and iz.testzip() is None
            assert all(not n.startswith("/") and "\\" not in n and ".." not in pathlib.PurePosixPath(n).parts for n in ns)
            assert sum(x.file_size for x in infos)<=8<<20 and len(ns)<=512 and len(body)<=1048576
            rows={x["name"]:x for x in fixture["members"]}
            assert len(rows)==len(fixture["members"])==len(ns) and set(rows)==set(ns)
            inventory=[]
            for x in infos:
                data=iz.read(x);row=rows[x.filename]
                assert len(data)==row["bytes"]==x.file_size and sha(data)==row["sha256"]
                assert row["zip_flags"]==x.flag_bits and row["zip_method"]==x.compress_type and row["zip_extra_hex"]==x.extra.hex()
                inventory.append({"path":x.filename,"bytes":len(data),"sha256":sha(data),"flags":x.flag_bits,"method":x.compress_type})
            specimens.append({"kind":kind,"artifact_member":member,"bytes":len(body),"sha256":sha(body),
                "members":len(ns),"generated_snapshots":len(fixture["generated_snapshot_ids"]),
                "expanded_bytes":sum(x.file_size for x in infos),"inventory":inventory,"report":report,
                "actual_native_leaf_passed":True,"within_approved_1048576_archive_budget":True,
                "historical_65536_field":len(body)<=65536,"production_import_qualified":False})
    assert sum(x["members"] for x in specimens)==289
    specimen_sha=write("GENUINE_EXPORT_INVENTORY.json",{"status":"FOUR_ACTUAL_NATIVE_EXPORT_FIXTURE_LEAVES_PASSED",
        "scope":"Original text/format/nested/attachment assertions and exact generated/native export bytes. No import, cold reopen or Host acknowledgement.",
        "specimens":specimens})
    rejects=json.loads(z.read("fixtures/archive-admission-rejections.json"))
    rr=rejects["derived_rejection_cases"]
    assert len(rr)==26 and {x["case"] for x in rr}==set(manifest["expected_rejections"])
    actual={x["kind"]:x["sha256"] for x in specimens}
    for r in rr:
        assert r["refusal"]==manifest["expected_rejections"][r["case"]]
        assert r["base_sha256"]==actual[r["base_specimen"]] and r["variant_sha256"]!=r["base_sha256"]
    expected_fixtures={kind+suffix for kind in ("text","format","nested","attachment") for suffix in (".zip","-manifest.json","-export-report.json")}
    expected_fixtures|={"native-export-cleanup.json","archive-admission-rejections.json"}
    actual_fixtures={n.removeprefix("fixtures/") for n in names if n.startswith("fixtures/")}
    extra=sorted(actual_fixtures-expected_fixtures)
    assert extra==["schema-registration-00.json","schema-registration-01.json","schema-registration.json"]
    driver=git(SWIFT,SOURCE,PREFIX+"/slice-a/run_native_archive.py")
    diagnosis_sha=write("COLLECTOR_DIAGNOSIS.json",{"status":"GROUNDED_COLLECTOR_ALLOWLIST_FAILURE",
        "source_revision":SOURCE,"driver_path":PREFIX+"/slice-a/run_native_archive.py","driver_sha256":sha(driver),
        "error":"Unexpected specimen evidence files","failure_line":505,
        "missing_allowlist_files":extra,"unexpected_user_or_provider_payload":False,
        "native_calls_completed_before_collector":36,"all_history_retained":True,
        "historical_65536_field":{"source_line":302,"meaning":"A retained diagnostic comparison to the former 64 KiB limit; it is not the actual current native admission policy. All four archives pass the approved 1 MiB native parser and genuine current selectors."},
        "unreached_checks":["final global source input hash loop","final composed product/model/module hash loops","final native link input equality","final all-binaries equality loop","final control/source reread","final control HEAD equality"],
        "individual_binary_after_execution_checks_reached":True,
        "offline_repair_cannot_retroactively_change_ci_conclusion":True,"native_replay_required":False})
    intake={"schema":1,"status":"AUTHENTICATED_NATIVE_4_PLUS_32_PASS_WITH_COLLECTOR_WORKFLOW_FAILURE",
        "run_id":45139622096,"run_attempt":1,"source_sha":SOURCE,"workflow_conclusion":"failure",
        "artifact_id":14802738032,"artifact_bytes":len(raw),"artifact_sha256":sha(raw),
        "github_digest_matches":True,"safe_unique_crc_members":51,"index_rows_verified":50,
        "native_exports":{"pass":4,"fail":0,"skip":0},"archive_admission":{"pass":32,"fail":0,"skip":0},
        "commands":14,"all_commands_terminal_zero_and_drained":True,
        "actual_registration_calls":2,"actual_unique_schema_creates":18,"actual_type_apply_calls":1,
        "actual_original_exports":4,"specimen_members_authenticated":289,"cleanup":cleanup,
        "owned_native_temporary_removed":True,"observer_process_absent":True,"observer_lock_released":True,
        "source_intake_sha256":source_sha,"native_cases_sha256":events_sha,"compiler_coverage_sha256":compiler_sha,
        "schema_history_sha256":schema_sha,"specimen_inventory_sha256":specimen_sha,"collector_diagnosis_sha256":diagnosis_sha,
        "global_post_execution_source_stability_loop_reached":False,
        "historical_native_cases_replayed":False,"production_import_activated":False,"body_ack_authority":False,
        "cold_reopen_qualified":False,"swift_invocation_qualified":False,
        "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    intake_sha=write("INTAKE.json",intake)
    print(json.dumps({"status":intake["status"],"intake_sha256":intake_sha,"index_rows":50,"native_counts":[4,32],
        "compiler_union_rows":19,"compiler_per_target":{k:sum(bool(r["actual_compiled_package_variants"][k]) for r in coverage) for k in closures},
        "schema_calls":2,"specimen_member_rows":289,"collector_extra_files":extra}))
