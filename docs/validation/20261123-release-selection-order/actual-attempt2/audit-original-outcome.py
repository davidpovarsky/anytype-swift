#!/usr/bin/env python3
"""Read-only verification of the sole original Release attempt2 carrier."""
import ast,hashlib,json,os,pathlib,re,shutil,stat,subprocess,time
D=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-attempt2-original-result-20261123")
R=D/"private-originals"
G="/mnt/development/projects/git-mirrors/anytype-swift.git"
HEAD="c0c1f851f80322c9f532e86505047498dfaf1adf"
APP="d254a4a1ccd9288f585ff9374088cbaf965b36b4"
ARCHIVE="8fc2cac021e7c9a8a14cbcefc718a1f5eb35429994963aca8b771bb2ee2c2891"
def need(v,m):
 if not v:raise ValueError(m)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def gitfile(path,head=HEAD):return subprocess.check_output(["git","--no-optional-locks","--git-dir="+G,"show",head+":"+path],timeout=30)
def kernel(row):
 need(row["status"]=="PASS" and row["absence_source"]=="KERNEL_ESRCH" and row["live_members"]==0,"Owned group absence failed")
 k=row["kernel_group_observation"]
 need(k["outcome"]=="ABSENT_ESRCH" and k["signal"]==0 and k["errno"]==3 and k["operation"]=="os.killpg","Wrong group observation")
 need(k["pgid"]==row["pgid"] and row["budget_seconds"]==10,"Wrong group identity/budget")
 return k["pgid"]
need(shutil.disk_usage(D).free>=2500000000,"Reserve insufficient")
started=time.time()
index=read(D/"original-extraction.json")
need(index["file_count"]==len(index["files"])==109 and index["logical_bytes"]==9205494,"Original extraction inventory changed")
for row in index["files"]:
 p=R/row["path"];s=p.lstat()
 need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and stat.S_IMODE(s.st_mode)==0o400 and s.st_size==row["bytes"] and sha(p)==row["sha256"],"Original changed: "+row["path"])
need(sha(D/"original-14816672145.zip")==index["archive_sha256"]==ARCHIVE,"Original carrier changed")
expected_metadata={"run.json":"98b98f6553de53e2c1e327d91cfc4afe5e28a7ffe0997db241e780b9c2b11e30","jobs.json":"67b26bf841a87a0e39314dfc6f01eedaa2e355b59b66f53c015e27583c352399","artifacts.json":"39faaab4bac624e9da43ca0b0a6fc8d78755b6ad805c5b5d845e13fb24ef4575","observer-result.json":"8ec45452c56f2c76e29d3615b9562453fa0e7fefb6349a579d04661cad2be055"}
for n,h in expected_metadata.items():need(sha(D/"api-originals"/n)==h,"Original API index changed")
run=read(D/"api-originals/run.json")
need((run["id"],run["run_attempt"],run["head_sha"],run["status"],run["conclusion"])==(45163515182,2,HEAD,"completed","failure"),"Run identity changed")
jobs=[j for j in read(D/"api-originals/jobs.json")["jobs"] if j["id"]==137674049304]
need(len(jobs)==1 and jobs[0]["run_attempt"]==2 and jobs[0]["head_sha"]==HEAD and jobs[0]["runner_id"]==1000024635,"Selected job changed")
artifacts=[a for a in read(D/"api-originals/artifacts.json")["artifacts"] if a["id"]==14816672145]
need(len(artifacts)==1 and artifacts[0]["name"]=="Pinkha-Coherent-Original-Products-45163515182-2" and artifacts[0]["digest"]=="sha256:"+ARCHIVE and artifacts[0]["size_in_bytes"]==2223532,"Artifact selection changed")
admit=read(R/"original-products/admission.json")
need(admit["status"]=="ORIGINAL_PRODUCTS_ADMITTED_TESTS_NOT_RUN" and admit["app_source_sha"]==APP,"Original App admission differs")
need(admit["app_builds_this_run"]==admit["ui_runner_builds_this_run"]==0,"Unexpected current build")
need(admit["execution_origin"]=={"control_source_sha":HEAD,"run_attempt":"2","run_id":"45163515182"},"Controller origin differs")
source=admit["controller_source_hashes"];need(len(source)==51,"Controller closure differs")
paths=sorted(source)
raw=subprocess.check_output(["git","--no-optional-locks","--git-dir="+G,"cat-file","--batch"],input=b"".join((HEAD+":"+p+"\n").encode() for p in paths),timeout=30)
pos=0;bindings=[];source_bytes={}
for name in paths:
 end=raw.index(b"\n",pos);oid,kind,size=raw[pos:end].split();size=int(size);start=end+1;b=raw[start:start+size];pos=start+size+1
 need(kind==b"blob" and len(b)==size and raw[start+size:start+size+1]==b"\n" and hashlib.sha256(b).hexdigest()==source[name],"Actual loaded source is not current Git: "+name)
 bindings.append({"path":name,"git_blob":oid.decode(),"sha256":source[name],"bytes":size});source_bytes[name]=b
need(pos==len(raw),"Unexpected Git output")
snapshots=[]
for p in sorted((R/"control-source-snapshots").glob("*/*.json")):
 v=read(p);identity=v["identity"]
 need(v["snapshot_sha256"]==p.stem and identity["control_source_sha"]==identity["github_sha"]==HEAD and identity["run_id"]=="45163515182" and identity["run_attempt"]=="2","Snapshot origin differs")
 need(all(source.get(n)==h for n,h in v["controller_source_hashes"].items()),"Snapshot source drift")
 need(set(v["loaded_module_names"].values())==set(v["controller_source_hashes"]),"Snapshot loaded closure differs")
 snapshots.append({"path":str(p.relative_to(R)),"sha256":sha(p),"sources":len(v["controller_source_hashes"]),"loaded_names":len(v["loaded_module_names"]),"pid":identity["process_id"]})
need(len(snapshots)==4,"Snapshot inventory differs")
intent=read(R/"batch-intent.json");worker=read(R/"batch-worker.json");lane=read(R/"lanes/editor/execution.json");execution=read(R/"execution.json")
need(intent["control_source_sha"]==HEAD and intent["source_sha"]==APP and intent["run_id"]=="45163515182" and intent["run_attempt"]=="2","Intent changed")
need(execution["worker"]==worker and execution["worker_receipt_sha256"]==sha(R/"batch-worker.json"),"Worker publication differs")
need(worker["current_lane"]=="editor" and worker["phase"]=="LANE" and worker["status"]=="BATCH_ABORTED_SETUP_OR_IDENTITY","Wrong worker boundary")
need(lane["phase"]=="PREPARATION" and lane["status"]=="LANE_ABORTED_SETUP_OR_IDENTITY","Wrong lane boundary")
error="First selection is not the exact original native preparation"
need(worker["error"]==lane["error"]==error and worker["error_type"]==lane["error_type"]=="ValueError","Original failure changed")
old_lane=read(R/"original-products/originals/lanes/editor/execution.json")
need(len(lane["candidate_input_hashes"])==5929 and lane["candidate_input_hashes"]==worker["candidate_input_hashes"]==old_lane["candidate_input_hashes"],"Original5929 App input map changed")
need(lane["native_builds_this_run"]==lane["app_builds_this_run"]==lane["ui_runner_builds_this_run"]==0,"Unexpected lane build")
build=read(R/"original-products/originals/batch-build/same-job-build.json")
need(sha(R/"original-products/originals/batch-build/same-job-build.json")==admit["build_origin"]["original_build_receipt_sha256"]=="87834f312a69f814623c2fa8d14d07f017e0902dbf512d49717397c862fffca2","Original build receipt differs")
need(build["source"]["source_sha"]==APP and build["source"]["source_tree_sha"]==admit["source_tree_sha"],"Original source origin differs")
manifests={}
for kind,expected_count in (("native",5211),("ui",30)):
 p=R/("original-products/originals/coherent-"+kind+"-early-products/manifest.json");v=read(p)
 need(v["source_sha"]==APP and v["run_id"]=="45095838065" and v["run_attempt"]=="1" and len(v["products"])==expected_count,"Original Products manifest differs")
 need(admit["restored_entries"][kind]["entries"]==expected_count,"Restoration receipt inventory differs")
 original_name=pathlib.PurePosixPath(admit["descriptor_normalization"][kind]["original_path"]).name
 descriptor=v["products"]["Build/Products/"+original_name]
 need(descriptor["sha256"]==admit["descriptor_normalization"][kind]["original_sha256"]==build["artifacts"][kind+"_xctestrun_sha256"],"Original descriptor binding differs")
 manifests[kind]=v
carriers=read(R/"lanes/editor/built-code-carriers.json")
need(len(carriers["manifest"]["carriers"])==103 and carriers["manifest"]["transformations"]==[] and carriers["manifest"]["full_bundle_equivalence"] is False,"Carrier scope changed")
for name,row in carriers["manifest"]["carriers"].items():
 old=manifests["native"]["products"].get("Build/Products/Release-Anytype-iphonesimulator/Anytype.app/"+name)
 need(old and old["kind"]=="file" and old["sha256"]==row["sha256"] and old["bytes"]==row["bytes"],"Observed restored carrier differs: "+name)
ready=read(R/"lanes/editor/owned-readiness/readiness.json");uid=ready["destination"]
need(ready["status"]=="OWNED_SIMULATOR_READY" and ready["tests_executed"]==0 and ready["bootstatus_return_code"]==0 and ready["bootstatus_timeout_seconds"]==180,"Actual readiness differs")
boot=read(R/"lanes/editor/owned-readiness/boot.owned.command.json");bootstatus=read(R/"lanes/editor/owned-readiness/boot-status.owned.command.json")
need(boot["return_code"]==bootstatus["return_code"]==0 and bootstatus["status"]=="COMPLETE","Actual boot failed")
need(bootstatus["argv"]==["xcrun","simctl","bootstatus",uid,"-b"] and bootstatus["timeout_seconds"]==180,"Owned bootstatus changed")
need(ready["bootstatus_log_sha256"]==sha(R/"lanes/editor/owned-readiness/boot-status.log"),"Boot output hash differs")
language=read(R/"lanes/editor/device-language-observation.json")
need(language["status"]=="DEVICE_LANGUAGE_PREFERENCES_VERIFIED" and language["command_exit_code"]==0 and language["simulator_udid"]==uid and language["device_language"]=="he" and language["app_language"]=="en","Actual language observation differs")
plan=read(R/"lanes/editor/selection-plan.json");fresh=read(R/"lanes/editor/fresh-container.json")
need(plan["preparation"]=="PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState" and plan==lane["selection"],"Native preparation selection changed")
derived=dict(plan);derived["device_language_verified"]=False;derived.pop("device_language");derived.pop("device_language_scope")
derived_bytes=(json.dumps(derived,indent=2)+"\n").encode()
need(hashlib.sha256(derived_bytes).hexdigest()==fresh["selection_plan_sha256"]=="c09670cd6fb4c55a8130506dda2bdaaf607a4d7698c386de4a18d0e68b392cc1","Initial sealed plan not explained by exact3-field language delta")
need(sha(R/"lanes/editor/selection-plan.json")=="0d202e0880ccd347684201a4947e151b74a7cbcc81d291f644eab2668cc8ce4f" and len(derived_bytes)==753,"Final plan changed")
need(fresh["container_absence_proved"] is False and fresh["lookup"]=="NOT_PERFORMED_CONSTRUCTION_CONTRACT" and fresh["prior_owned_install_or_selection_attempts"]==0,"Construction boundary differs")
need(not (R/"lanes/editor/construction/first-selection-attempt.json").exists(),"Native attempt unexpectedly recorded")
prep_path="AnyTypeTests/Pinkha/PinkhaStage1AcceptancePreparationTests.swift";prep=gitfile(prep_path,APP)
need(b"struct PinkhaStage1AcceptancePreparationTests" in prep and b"func prepareRealApplicationState() async throws" in prep,"Original native preparation source absent")
flow=source_bytes["Tools/PinkhaSimulatorGate/run_wave15_acceptance.py"].decode()
seal_at=flow.index("build_context.confirm_empty_container(udid, evidence)")
language_at=flow.index("language_observation = configure_editor_device_language(")
plan_update=flow.index('shared.write(evidence / "selection-plan.json", selection)',language_at)
selection_at=flow.index('preparation = run_selection(app, native_configuration, "AnytypeTests"')
need(seal_at<language_at<plan_update<selection_at,"Actual source ordering not reproduced")
construction=source_bytes["Tools/PinkhaSimulatorGate/coherent_fresh_construction.py"].decode()
need('and digest(directory / "selection-plan.json", origin.evidence) == fresh["selection_plan_sha256"]' in construction,"Strict whole-plan guard absent")
context=source_bytes["Tools/PinkhaSimulatorGate/coherent_original_products.py"].decode()
need(context.index("first = construction.selection_attempt(")<context.index("result = super().run_selection("),"Failure does not precede launch")
current_names=[x["path"] for x in index["files"] if not x["path"].startswith("original-products/originals/")]
need(not any(".xcresult" in n or n.endswith("-summary.json") or n.endswith("-tests.json") or "/preparation/" in n or "/ui/" in n for n in current_names),"Unexpected actual test originals")
launched=[]
for line in (R/"batch-worker.log").read_text().splitlines():
 try:v=json.loads(line)
 except json.JSONDecodeError:continue
 if isinstance(v,dict) and isinstance(v.get("command"),list):launched.append(v["command"])
need(len(launched)==7 and not any("xcodebuild" in " ".join(x) or "test-without-building" in x or (len(x)>2 and x[:3]==["xcrun","simctl","install"]) for x in launched),"Unexpected test or install command")
nested=read(R/"coherent-nested-cleanup.json");outer=read(R/"batch-worker.command.json")
need(nested["status"]=="PASS" and nested["groups_checked"]==len(nested["original_owned_commands"])==4,"Nested cleanup differs")
groups=[]
for item in nested["original_owned_commands"]:
 groups.append(kernel(item));relative=item["path"].split("/evidence/",1)[1];p=R/relative
 need(sha(p)==item["sha256"] and read(p)["return_code"]==item["original_return_code"]==0,"Original nested command differs")
 for projection in item["projections"]:
  p=R/projection["path"].split("/evidence/",1)[1]
  need(sha(p)==projection["sha256"] and projection["original_owned_command_sha256"]==item["sha256"],"Original projection differs")
  need(kernel(projection["prior_quiescence"])==item["pgid"],"Projection group differs")
groups.append(kernel(outer["owned_group_quiescence"]))
need(outer["return_code"]==1 and outer["status"]=="WORKER_FAILED" and outer["termination_profile"]=="coherent-heart-release","Primary worker failure not retained")
clean=read(R/"batch-cleanup.json");deleted=[x for x in clean["devices"] if x["status"]=="DELETED_OWNED_SIMULATOR"]
need(clean["status"]=="PASS" and len(deleted)==3 and uid in {x["udid"] for x in deleted} and all(x["delete_exit_code"]==0 for x in deleted),"Owned cleanup differs")
need(execution["cleanup"]==clean and execution["worker_command"]==outer,"Final current result changed cleanup/worker")
snapshot=read(R/"coherent-cleanup-source-check.json")
need(snapshot["status"]=="EXACT_PRE_ADMITTED_CLEANUP_SOURCE_SNAPSHOT" and snapshot["control_source_sha"]==HEAD and snapshot["admitted_sources"]==snapshot["loaded_source_paths"]==51 and snapshot["git_subprocesses"]==0 and snapshot["original_intent_sha256"]==sha(R/"batch-intent.json"),"Cleanup source admission differs")
life=read(R/"preflight/lifecycle-cleanup.json")
need(life["status"]=="PASS" and life["cleanup_commands"]==0 and life["prior_batch_cleanup"]["status"]=="REUSED_EXACT_CURRENT_BATCH_CLEANUP","Prior exact cleanup not reused")
for name,h in life["prior_batch_cleanup"]["originals"].items():need(sha(R/name)==h,"Prior cleanup original binding differs")
report={"protocol":"release451635-attempt2-independent-original-review-v1","status":"PASS_ORIGINAL_FAILURE_BOUNDARY_VERIFIED","run_id":45163515182,"attempt":2,"controller_source_sha":HEAD,"app_source_sha":APP,"artifact_id":14816672145,"artifact_sha256":ARCHIVE,"original_files_verified":109,"original_extraction_sha256":sha(D/"original-extraction.json"),"original_metadata":expected_metadata,"current_controller_git_bindings":bindings,"loaded_source_snapshots":snapshots,"retained5929_candidate_inputs_exactly_equal_original_build_lane":True,"candidate_input_map_sha256":canonical(lane["candidate_input_hashes"]),"restored_native_entries_receipt":5211,"restored_ui_entries_receipt":30,"observed_carrier_rows_exact_original_manifest_matches":103,"restored_product_bytes_not_in_new_result_artifact":True,"full_bundle_equivalence_claimed":False,"app_builds_this_run":0,"ui_runner_builds_this_run":0,"actual_native_preparation_methods_started":0,"actual_product_methods_started":0,"actual_named_passes":[],"actual_named_failures":[],"actual_xcodebuild_launches":0,"actual_first_failure":{"phase":"PREPARATION","type":"ValueError","message":error,"cause":"INITIAL_SELECTION_PLAN_SEALED_BEFORE_VERIFIED_LANGUAGE_METADATA_REWRITE","sealed_initial_hash":fresh["selection_plan_sha256"],"actual_final_hash":sha(R/"lanes/editor/selection-plan.json"),"initial_plan_reconstructed_for_hash_explanation_only":True,"changed_fields":["device_language_verified","device_language","device_language_scope"],"preparation_method":plan["preparation"],"blueprint":"AnytypeTests","method_selector_mismatch_established":False},"original_native_preparation_source":{"path":prep_path,"source_sha":APP,"sha256":hashlib.sha256(prep).hexdigest()},"readiness":{"status":ready["status"],"boot_exit":0,"bootstatus_exit":0,"bootstatus_timeout_seconds":180,"bootstatus_log_bytes":(R/"lanes/editor/owned-readiness/boot-status.log").stat().st_size,"bootstatus_started_at":bootstatus["started_at"],"bootstatus_finished_at":bootstatus["finished_at"],"device_type":ready["before"]["deviceTypeIdentifier"],"runtime":ready["before"]["runtime_identifier"],"udid":uid},"device_language_observation_sha256":sha(R/"lanes/editor/device-language-observation.json"),"kernel_cleanup_unique_groups":sorted(set(groups)),"kernel_cleanup_unique_count":len(set(groups)),"owned_devices_deleted":deleted,"preflight_cleanup_reused_exact_current_batch":True,"cleanup_source_admission":snapshot,"release_accepted":False,"old_product_passes_replayed_by_audit":0,"tests_or_builds_executed_by_audit":0,"api_status_queries_by_audit":0,"elapsed_seconds":time.time()-started,"reader_sha256":sha(pathlib.Path(__file__))}
need(shutil.disk_usage(D).free>=2500000000,"Reserve crossed before audit write")
out=D/"independent-original-outcome-review.json";b=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
with out.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
out.chmod(0o400)
print(json.dumps({"status":report["status"],"report":str(out),"sha256":hashlib.sha256(b).hexdigest(),"source_bindings":len(bindings),"originals":109,"carrier_metadata_rows":103,"actual_methods_started":0,"first_failure":"PREPARATION: sealed-plan hash changed after verified device-language annotation","owned_groups_absent":len(set(groups)),"deleted_owned_devices":len(deleted),"free":shutil.disk_usage(D).free}))
