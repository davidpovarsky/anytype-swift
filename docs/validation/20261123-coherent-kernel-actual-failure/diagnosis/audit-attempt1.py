"""Read-only audit of immutable Release 45129057825 originals; no product execution."""
from pathlib import Path
import ast, datetime, hashlib, json, re, shutil, subprocess
BASE=Path("/mnt/development/projects/diagnostics/coherent-kernel-actual-result-20261123")
DIAG=BASE/"diagnosis"
ROOT=DIAG/"originals"
REPO=Path("/mnt/development/projects/worktrees/anytype-wave15-coherent-kernel-20261123")
CONTROL="a69d0967c1dad4b9476b04af2b681474983e0b96"
APP="d254a4a1ccd9288f585ff9374088cbaf965b36b4"
RUN="45129057825"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def blob(path):
    assert path.is_file() and not path.is_symlink()
    return path.read_bytes()
def digest(path): return sha(blob(path))
def read(name): return json.loads(blob(ROOT/name))
def proof(path, base=ROOT):
    raw=blob(path)
    return {"path":str(path.relative_to(base)), "bytes":len(raw), "sha256":sha(raw)}
expected={
"artifact.zip":(1599793,"8741a6d631e3152f12fa49109a5c37484443b13aaea47e4765aabc6c89bd2198"),
"job.log":(62114,"2a4adf38fc3bbd92cbb6c3c5be814f0e53c1872aa992d36bff266307824bfbed"),
"run.json":(23632,"7ca855c95ea651afb0979093fbd30b2f4e4c86c997f2688e0b3d1e0c6026e957"),
"artifacts.json":(803,"6488cc7a2753dd7aadfe5e3f4a50a5f6276331c19833dced7d5de63873f6dbed")
}
input_proofs=[]
for name in ["artifact.zip","job.log","run.json","jobs.json","artifacts.json"]:
    item=proof(BASE/name,BASE)
    if name in expected: assert (item["bytes"],item["sha256"])==expected[name]
    input_proofs.append(item)
inventory=json.loads(blob(DIAG/"inventory.json"))
assert digest(DIAG/"inventory.json")=="22ca03c069d469e7fac5745ad2e3d226383ff8c1d8dcf6af42b3526d5c19e2f6"
assert inventory["member_count"]==85 and inventory["links"]==0 and inventory["uncompressed_bytes"]==7080758
entries={e["path"]:e for e in inventory["entries"]}
assert len(entries)==85
assert {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()}==set(entries)
for name,e in entries.items():
    raw=blob(ROOT/name)
    assert len(raw)==e["bytes"] and sha(raw)==e["sha256"]
run=json.loads(blob(BASE/"run.json"))
jobs=json.loads(blob(BASE/"jobs.json"))
artifacts=json.loads(blob(BASE/"artifacts.json"))
assert str(run["id"])==RUN and run["head_sha"]==CONTROL and run["conclusion"]=="cancelled" and run["run_attempt"]==1
active=[j for j in jobs["jobs"] if j["id"]==137540092122]
assert len(active)==1
active=active[0]
assert active["conclusion"]=="cancelled"
artifact=[a for a in artifacts["artifacts"] if a["id"]==14798796696]
assert len(artifact)==1
artifact=artifact[0]
assert artifact["size_in_bytes"]==1599793 and artifact["digest"]=="sha256:"+expected["artifact.zip"][1]
worker=read("batch-worker.json")
editor=read("lanes/editor/execution.json")
admission=read("original-products/admission.json")
original_worker=read("original-products/originals/batch-worker.json")
execution=read("execution.json")
intent=read("batch-intent.json")
assert admission["execution_origin"]=={"control_source_sha":CONTROL,"run_attempt":"1","run_id":RUN}
assert admission["app_source_sha"]==APP and admission["source_tree_sha"]=="6066ff99e232d81ecad94395b038fdd8c15239a0"
assert admission["status"]=="ORIGINAL_PRODUCTS_ADMITTED_TESTS_NOT_RUN"
assert worker["candidate_input_hashes"]==editor["candidate_input_hashes"]==original_worker["candidate_input_hashes"]
assert len(worker["candidate_input_hashes"])==5929
assert worker["app_builds_this_run"]==worker["ui_runner_builds_this_run"]==0
assert execution["app_builds_this_run"]==execution["ui_runner_builds_this_run"]==0
assert worker["current_shared_app_accepted"] is False and execution["release_accepted"] is False
assert admission["source_proof"]["tracked_regular_files_compared"]==11468
source_cache={}
def source(path):
    if path not in source_cache:
        source_cache[path]=subprocess.check_output(["git","-C",str(REPO),"show",CONTROL+":"+path],timeout=30)
    return source_cache[path]
bindings=[]
for name,expected_sha in admission["controller_source_hashes"].items():
    raw=source(name)
    assert sha(raw)==expected_sha
    bindings.append({"path":name,"sha256":expected_sha,"bytes":len(raw)})
assert len(bindings)==33
def region(path,start,end):
    raw=source(path); lines=raw.decode().splitlines()
    assert 1<=start<=end<=len(lines)
    return {"path":path,"source_sha256":sha(raw),"lines":[start,end],
            "region_sha256":sha(("\n".join(lines[start-1:end])+"\n").encode())}
GATE="Tools/PinkhaSimulatorGate/"
kernel=[]
preflight=read("preflight/preflight.json")
assert preflight["source_sha"]==CONTROL and preflight["run_id"]==RUN and preflight["run_attempt"]=="1"
assert preflight["status"]=="PREFLIGHT_PASS_UI_NOT_RUN" and len(preflight["commands"])==8
def verify_kernel(q,pid):
    assert q["status"]=="PASS" and q["absence_source"]=="KERNEL_ESRCH"
    assert q["budget_seconds"]==10 and q["pgid"]==pid and q["live_members"]==q["observations"]==0
    assert q["timeout_observations"]==[]
    k=q["kernel_group_observation"]
    assert k["operation"]=="os.killpg" and k["pgid"]==pid and k["signal"]==0
    assert k["errno"]==3 and k["error_type"]=="ProcessLookupError" and k["outcome"]=="ABSENT_ESRCH"
    assert k["before_monotonic"]<=k["after_monotonic"]<=k["deadline_monotonic"]
for row in preflight["commands"]:
    name=row["name"]
    obs_name="preflight/"+name+".observation.json"; command_name="preflight/"+name+".command.json"
    obs=read(obs_name); command=read(command_name)
    assert obs==row and all(obs.get(k)==v for k,v in command.items())
    assert obs["owned_group_cleanup"]=="TERM_THEN_KILL" and obs["return_code"]==0
    assert obs["log_sha256"]==digest(ROOT/"preflight"/(name+".log"))
    verify_kernel(obs["owned_group_quiescence"],command["worker_pid"])
    kernel.append({"kind":"preflight","name":name,"pid":command["worker_pid"],"observation":proof(ROOT/obs_name),
                   "original_command":proof(ROOT/command_name),"kernel":obs["owned_group_quiescence"]["kernel_group_observation"]})
for name in ["before","boot","boot-status"]:
    p="lanes/editor/owned-readiness/"+name
    projection=read(p+".command.json"); command=read(p+".owned.command.json")
    assert projection["original_owned_command"]==name+".owned.command.json"
    assert projection["original_owned_command_sha256"]==digest(ROOT/(p+".owned.command.json"))
    assert projection["cleanup_profile"]=="coherent-heart-release" and projection["return_code"]==0
    assert projection["argv"]==command["argv"] and projection["cwd"]==command["cwd"]
    assert projection["controller_process_id"]==command["worker_pid"]
    assert command["owned_group_cleanup"]=="TERM_THEN_KILL" and command["return_code"]==0
    verify_kernel(projection["owned_group_quiescence"],command["worker_pid"])
    kernel.append({"kind":"editor_readiness","name":name,"pid":command["worker_pid"],"observation":proof(ROOT/(p+".command.json")),
                   "original_command":proof(ROOT/(p+".owned.command.json")),"kernel":projection["owned_group_quiescence"]["kernel_group_observation"]})
assert len(kernel)==11 and len({k["pid"] for k in kernel})==11
ready=read("lanes/editor/owned-readiness/readiness.json")
owned=read("lanes/editor/owned-simulator.json")
assert ready["status"]=="OWNED_SIMULATOR_READY" and ready["bootstatus_return_code"]==ready["tests_executed"]==0
assert ready["destination"]==owned["udid"]=="20BAEE0C-6091-49F5-9D94-880A738FF852"
assert ready["before"]["udid"]==owned["udid"] and ready["before"]["state"]=="Shutdown"
assert ready["before"]["name"]==owned["name"]
assert ready["before"]["runtime_identifier"]==owned["runtime"]["identifier"]
assert ready["before"]["deviceTypeIdentifier"]==owned["device"]["identifier"]
assert ready["preboot_identity_sha256"]==digest(ROOT/"lanes/editor/owned-readiness/before.json")
assert ready["bootstatus_log_sha256"]==digest(ROOT/"lanes/editor/owned-readiness/boot-status.log")
lookup=read("lanes/editor/fresh-container-lookup.observation.json")
assert lookup["argv"]==["xcrun","simctl","get_app_container",owned["udid"],"io.anytype.app","data"]
assert lookup["status"]=="TIMED_OUT" and lookup["error_type"]=="TimeoutExpired"
assert lookup["timeout_seconds"]==30 and lookup["product_methods_executed"]==0
assert lookup["container_absence_proved"] is False and lookup["owned_group_absence_proved"] is False
for key in ["stdout","stderr"]:
    assert lookup[key]["bytes"]==0 and lookup[key]["sha256"]==sha(b"")
    assert not (ROOT/"lanes/editor"/lookup[key]["path"]).exists()
assert "lanes/editor/fresh-container.json" not in entries
current=[n for n in entries if not n.startswith("original-products/originals/")]
assert len(current)==74
commands=[]; product_commands=[]; events=[]
for name in current:
    p=ROOT/name
    if name.endswith(".json"):
        obj=json.loads(blob(p))
        if isinstance(obj,dict) and isinstance(obj.get("argv"),list):
            commands.append(name)
            if any(v in {"test","test-without-building","build-for-testing"} for v in obj["argv"] if isinstance(v,str)):
                product_commands.append(name)
    if name.endswith(".log"):
        for number,line in enumerate(blob(p).decode("utf-8","replace").splitlines(),1):
            if re.search(r"Test (Case|Suite) .+\b(started|passed|failed)\b",line):
                events.append({"path":name,"line":number,"text":line})
assert len(commands)==26 and product_commands==[] and events==[]
assert not any(".xcresult" in n or n.endswith("fixture-isolation.json") for n in current)
assert worker["status"]=="BATCH_ABORTED_SETUP_OR_IDENTITY" and editor["status"]=="LANE_ABORTED_SETUP_OR_IDENTITY"
assert worker["error"]==editor["error"]==execution["error"]
assert "get_app_container" in worker["error"] and worker["error_type"]=="TimeoutExpired"
nested=read("coherent-nested-cleanup.json")
assert nested["status"]=="FAIL" and nested["groups_checked"]==0 and nested["original_owned_commands"]==[]
assert "git" in nested["error"] and "status" in nested["error"] and "30 seconds" in nested["error"]
outer=read("batch-worker.command.json")
assert outer["status"]=="FAILED_PROCESS_CLEANUP" and outer["termination_profile"]=="coherent-heart-release"
assert outer["timeout_seconds"]==6300 and outer["return_code"]==1 and outer["worker_pid"]==9256
assert outer["owned_group_cleanup"]=="TERM_THEN_KILL" and "ps" in outer["cleanup_error"] and "2 seconds" in outer["cleanup_error"]
assert outer["cleanup_probe_timeouts"]==[{"observation":1,"timeout_seconds":2}]
cleanup=read("batch-cleanup.json"); life=read("preflight/lifecycle-cleanup.json"); life_intent=read("preflight/lifecycle/intent.json")
assert cleanup["status"]=="PASS" and execution["cleanup"]==cleanup
assert life["status"]=="PASS" and life["source_sha"]==CONTROL and life["run_id"]==RUN and life["run_attempt"]=="1"
assert life["intent_sha256"]==preflight["intent_sha256"]==digest(ROOT/"preflight/lifecycle/intent.json")
assert life["cleanup_commands"]==0 and life["attempted_creations"]==2
assert life["prior_batch_cleanup"]["status"]=="REUSED_EXACT_CURRENT_BATCH_CLEANUP"
for name,expected_sha in life["prior_batch_cleanup"]["originals"].items(): assert digest(ROOT/name)==expected_sha
for key in ["retained_worker_receipt","retained_worker_command"]:
    row=execution[key]; assert digest(ROOT/row["path"])==row["sha256"]
assert intent["baseline_inventory_sha256"]==digest(ROOT/"batch-simulator-baseline.json")
assert life_intent["baseline_inventory_sha256"]==digest(ROOT/"preflight/simulator-inventory.json")
assert intent["control_source_sha"]==CONTROL and intent["source_sha"]==APP and intent["run_id"]==RUN and intent["run_attempt"]=="1"
created=[]
for kind,device in preflight["selected"].items():
    assert device["udid"].lower() not in {u.lower() for u in life_intent["baseline_udids"]}
    assert device in intent["preflight_devices"]
    path="preflight/lifecycle/lanes/preflight-"+kind+"/created-proof.json"
    cp=read(path); own=read("preflight/lifecycle/lanes/preflight-"+kind+"/owned-simulator.json")
    assert cp["udid"]==own["udid"]==device["udid"] and own["name"]==device["name"]
    assert cp["create_command_sha256"]==digest(ROOT/"preflight"/("create-"+kind+".command.json"))
    assert cp["create_log_sha256"]==digest(ROOT/"preflight"/cp["create_log"])
    assert blob(ROOT/"preflight"/cp["create_log"]).decode().strip()==device["udid"]
    created.append(device["udid"])
assert set(created)==set(life["known_owned_udids"])==set(life["prior_batch_cleanup"]["owned_udids"])
assert owned["udid"].lower() not in {u.lower() for u in intent["baseline_udids"]}
assert {k:v for k,v in owned.items() if k!="udid"} in intent["lane_devices"]
deleted=[x for x in cleanup["devices"] if x["status"]=="DELETED_OWNED_SIMULATOR"]
assert {x["udid"] for x in deleted}==set(created+[owned["udid"]])
assert all(x["delete_exit_code"]==0 for x in deleted)
assert len(cleanup["inventory_queries"])==3 and {x["selector"] for x in cleanup["inventory_queries"]}==set(created+[owned["udid"]])
assert all(x["selector_kind"]=="OWNED_UDID" and x["status"]=="RETURNED_VALID_SCOPED_INVENTORY" for x in cleanup["inventory_queries"])
assert len([x for x in cleanup["devices"] if x["status"]=="NOT_STARTED"])==5
workflow=source(".github/workflows/pinkha-coherent-original-products.yml").decode()
central=source(".github/workflows/torah-inspector-ipados27.yml").decode()
assert "timeout-minutes: 150" in workflow and "timeout-minutes: 120" in workflow
assert not re.search(r"(?m)^\s*concurrency\s*:",workflow+"\n"+central)
log=blob(BASE/"job.log").decode("utf-8","replace")
cancel=[{"line":i,"text":line} for i,line in enumerate(log.splitlines(),1) if "The operation was canceled." in line]
assert len(cancel)==1
dt=lambda s:datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
restore=[x for x in active["steps"] if x["name"]=="Restore original d254 Products and execute only unrun Release scopes"]
assert len(restore)==1 and restore[0]["conclusion"]=="cancelled"
report={
"status":"ORIGINAL_RELEASE_DIAGNOSIS_COMPLETE_NO_PRODUCT_EXECUTION",
"reviewed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"run":{"id":RUN,"attempt":"1","control_source_sha":CONTROL,"job_id":active["id"],"conclusion":"cancelled",
       "job_started_at":active["started_at"],"job_completed_at":active["completed_at"],
       "job_seconds":(dt(active["completed_at"])-dt(active["started_at"])).total_seconds(),
       "restore_step":restore[0],"step_limit_minutes":120,"job_limit_minutes":150},
"original_inputs":input_proofs,
"original_artifacts":{"inventory":proof(DIAG/"inventory.json",DIAG),"verified_extracted_entries":85,
 "uncompressed_bytes":7080758,"current_members":74,"retained_original_members":11,
 "new_extractions_in_this_audit":0,"redownloads":0},
"source_proof":{"current_loaded_sources_bound_to_exact_git":bindings,"initial_batched_reader_consumed":True,
 "initial_bound_count":33,"current_worker_and_editor_input_hashes_match_original_worker":True,"candidate_inputs":5929,
 "original_source_proof_receipt":admission["source_proof"],"original_build_origin":admission["build_origin"],
 "final_loaded_source_check_pass":False,"source_drift_established":False,
 "later_helpers_outside_initial_closure":[p for p in [
 GATE+"coherent_container_observation.py",GATE+"coherent_release_cleanup.py"] if p not in admission["controller_source_hashes"]],
 "later_check_failure":"Nested cleanup reached a repeated full-repository git status before collecting/checking the then-loaded closure; no late closure PASS exists."},
"new_product_scope":{"actual_named_starts":0,"actual_named_passes":0,"actual_named_failures":0,
 "current_command_records_checked":len(commands),"current_product_commands":product_commands,"current_xctest_events":events,
 "app_builds":0,"ui_runner_builds":0,"first_native_preparation_executed":False,"ui_executed":False,
 "release_accepted":False,"full_matrix_accepted":False,"old_product_results_relabelled":False,
 "evidence_basis":["First preinstall lookup timed out before the preparation call in exact source.",
 "Current 74-member namespace has no test/build command, named XCTest start/pass/fail, result bundle or fixture-isolation receipt.",
 "Lookup original explicitly records product_methods_executed=0."]},
"kernel_observations":{"actual_passed":11,"new_test_methods":0,"entries":kernel,
 "scope":"Actual preflight/readiness command group observations only; not product acceptance or outer-worker quiescence."},
"last_boundary":{"readiness":proof(ROOT/"lanes/editor/owned-readiness/readiness.json"),
 "readiness_status":ready["status"],"lookup":lookup,
 "lookup_original":proof(ROOT/"lanes/editor/fresh-container-lookup.observation.json"),
 "phase_label_is_broader_than_boundary":editor["phase"],
 "raw_stream_artifact_limitation":"Original observation records zero-byte stdout/stderr hashes, but .stdout/.stderr members are absent from the original ZIP; no missing raw file has been recreated.",
 "packager_source":region("Tools/PinkhaNativeDerived/package_evidence.py",15,32),
 "fresh_container_receipt_present":False,"container_absence_proved":False},
"cleanup":{"nested":nested,"outer":{k:outer[k] for k in [
 "status","started_at","finished_at","worker_pid","return_code","termination_profile","timeout_seconds",
 "owned_group_cleanup","cleanup_error_type","cleanup_error","cleanup_probe_timeouts"]},
 "devices":cleanup,"preflight_lifecycle":life,"exact_current_cleanup_hashes_verified":True,
 "preflight_new_ids_excluded_from_preflight_baseline":True,"editor_new_id_excluded_from_batch_baseline":True,
 "preflight_ids_are_expected_members_of_later_batch_baseline":True,
 "all_process_groups_proven_absent":False,"successful_simulator_cleanup_does_not_relabel_process_cleanup":True},
"cancellation":{"cause":"UNKNOWN","original_job_log_marker":cancel[0],
 "configured_step_or_job_deadline_reached":False,"central_or_reusable_workflow_concurrency_declared":False,
 "who_requested_cancellation":"UNKNOWN","provider_failure_cause":"UNKNOWN",
 "worker_to_cleanup_gap_seconds":(dt(cleanup["started_at"])-dt(outer["finished_at"])).total_seconds(),
 "gap_attribution":"UNKNOWN; no original phase-timed receipt proves what consumed this interval."},
"source_findings":{
 "freshness_current_contract":{"creation":region(GATE+"wave15_batch.py",727,745),
 "lookup":region(GATE+"wave15_batch.py",363,398),"validator":region(GATE+"wave15_batch.py",531,545),
 "fixture_isolation":region(GATE+"wave15_batch.py",413,427),
 "classification":"Required NEGATIVE_UNCLASSIFIED lookup result gate; its freshness basis is new owned device construction. It does not prove container absence.",
 "continuation_option":"Review a distinct coherent-only construction receipt for a just-created nonbaseline exact owned UDID, planned-name absence, initial Shutdown identity and successful readiness before first installation; validate that explicit contract and retain later actual fixture Space/container uniqueness. Do not treat this timeout as negative or absent, and preserve other/default lookup contracts.",
 "source_change_needed":True},
 "outer_teardown":{"source":region(GATE+"wave15_batch.py",874,946),
 "exact_gap":"The coherent-only run_nested_worker_command calls verify_owned_group_stopped(path) without cleanup_profile=profile at line 936.",
 "minimal_option":"Forward the existing validated coherent profile only at that call; retain original 10-second deadline and the same default helper behavior for other callers. Preserve quiescence_observation as well as timeout_observations on any new failure."},
 "nested_control_guard":{"anchor":region(GATE+"coherent_original_products.py",272,320),
 "reader":region(GATE+"coherent_controller_sources.py",44,80),
 "caller":region(GATE+"coherent_heart_release.py",418,437),
 "call_chain":["nested_cleanup","origin.nested_cleanup_anchor","validate_intent","verify_control","control_sources","git status --porcelain --untracked-files=no (30s)"],
 "finding":"The repeated full-root cleanliness command timed out before any group audit; earlier 33 exact source bindings remain qualified but do not establish the final dynamically loaded closure.",
 "continuation_option":"A cleanup-specific anchor can bind exact current run/attempt, controller origin, immutable original intent/admission and source closure without making unrelated full-worktree cleanliness a prerequisite to owned-group observation. Any revised closure policy must still check actual loaded cleanup helper bytes and preserve the old failure; do not reuse the initial 33 as a blanket waiver."}},
"limitations":["Cancellation cause remains unknown.","Original current product methods: zero.","No late source-closure or complete process cleanup pass.",
 "Decoded local-store witness, migration, Page mounted, Swift/App and network acceptance are outside this diagnosis."],
"operations":{"repo_source_edits":0,"product_tests":0,"old_control_reruns":0,"api_requests":0,"downloads":0,"new_archive_extractions":0},
"space_observation":{"free_bytes":shutil.disk_usage(DIAG).free,"minimum_reserve_bytes":2500000000}
}
print(json.dumps(report,sort_keys=True))
