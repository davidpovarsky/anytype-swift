#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,stat,os,shutil
D=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-original-result-20261123")
R=D/"private-originals"
G=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
HEAD="c0c1f851f80322c9f532e86505047498dfaf1adf"
APP="d254a4a1ccd9288f585ff9374088cbaf965b36b4"
def read(n):return json.loads((R/n).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert shutil.disk_usage(D).free>=2500000000
index=json.loads((D/"original-extraction.json").read_bytes())
assert index["file_count"]==95 and len(index["files"])==95
for row in index["files"]:
 p=R/row["path"];s=p.lstat()
 assert stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode)==0o400 and s.st_size==row["bytes"] and sha(p)==row["sha256"]
assert sha(D/"original-14813934109.zip")==index["archive_sha256"]=="87052e03e4ed617c5782ab566393ecdaeb3891e3d4140d70c750900f1e89cc85"
run=json.loads((D/"api-originals/run.json").read_bytes())
assert (run["id"],run["run_attempt"],run["head_sha"],run["conclusion"])==(45163515182,1,HEAD,"failure")
admit=read("original-products/admission.json")
assert admit["status"]=="ORIGINAL_PRODUCTS_ADMITTED_TESTS_NOT_RUN" and admit["app_source_sha"]==APP
assert admit["app_builds_this_run"]==admit["ui_runner_builds_this_run"]==0
assert admit["restored_entries"]["native"]["entries"]==5211 and admit["restored_entries"]["ui"]["entries"]==30
source=admit["controller_source_hashes"];assert len(source)==51
paths=sorted(source)
data=subprocess.check_output(["git","-C",str(G),"cat-file","--batch"],input=b"".join((HEAD+":"+n+"\n").encode() for n in paths),timeout=30)
pos=0;bindings=[]
for n in paths:
 end=data.index(b"\n",pos);oid,kind,size=data[pos:end].split();size=int(size);start=end+1;b=data[start:start+size];pos=start+size+1
 assert kind==b"blob" and len(b)==size and data[start+size:start+size+1]==b"\n" and hashlib.sha256(b).hexdigest()==source[n]
 bindings.append({"path":n,"git_blob":oid.decode(),"sha256":source[n],"bytes":size})
assert pos==len(data)
intent=read("batch-intent.json");worker=read("batch-worker.json");lane=read("lanes/editor/execution.json")
ready=read("lanes/editor/owned-readiness/readiness.json")
assert intent["control_source_sha"]==HEAD and intent["source_sha"]==APP and intent["run_id"]=="45163515182" and intent["run_attempt"]=="1"
assert worker["control_source_sha"]==HEAD and worker["current_lane"]=="editor" and worker["phase"]=="LANE" and worker["status"]=="BATCH_ABORTED_SETUP_OR_IDENTITY"
assert lane["status"]=="LANE_ABORTED_SETUP_OR_IDENTITY" and lane["phase"]=="OWNED_SIMULATOR_READINESS"
assert ready["status"]=="FAIL" and ready["tests_executed"]==0 and ready["bootstatus_timeout_seconds"]==180 and ready["postboot_inventory_performed"] is False
command=read("lanes/editor/owned-readiness/boot-status.command.json")
original=read("lanes/editor/owned-readiness/boot-status.owned.command.json")
uid=ready["destination"]
assert command["argv"]==original["argv"]==["xcrun","simctl","bootstatus",uid,"-b"]
assert command["status"]==original["status"]=="TIMED_OUT" and command["return_code"]==original["return_code"]==-15 and command["timeout_seconds"]==original["timeout_seconds"]==180
assert worker["error_type"]==lane["error_type"]==ready["error_type"]==command["error_type"]==original["error_type"]=="TimeoutExpired"
assert worker["error"]==lane["error"]==ready["error"]
assert command["original_owned_command_sha256"]==sha(R/"lanes/editor/owned-readiness/boot-status.owned.command.json")
assert (R/"lanes/editor/owned-readiness/boot-status.log").stat().st_size==0
boot=read("lanes/editor/owned-readiness/boot.owned.command.json");assert boot["status"]=="COMPLETE" and boot["return_code"]==0
nested=read("coherent-nested-cleanup.json");outer=read("batch-worker.command.json")
assert nested["status"]=="PASS" and nested["groups_checked"]==4
for group in [*nested["original_owned_commands"],outer["owned_group_quiescence"]]:
 assert group["status"]=="PASS" and group["absence_source"]=="KERNEL_ESRCH" and group["live_members"]==0
 assert group["kernel_group_observation"]["outcome"]=="ABSENT_ESRCH"
clean=read("batch-cleanup.json");assert clean["status"]=="PASS"
deleted=[x for x in clean["devices"] if x["status"]=="DELETED_OWNED_SIMULATOR"]
assert len(deleted)==3 and uid in {x["udid"] for x in deleted} and all(x["delete_exit_code"]==0 for x in deleted)
snapshot=read("coherent-cleanup-source-check.json")
assert snapshot["status"]=="EXACT_PRE_ADMITTED_CLEANUP_SOURCE_SNAPSHOT" and snapshot["control_source_sha"]==HEAD and snapshot["admitted_sources"]==51 and snapshot["loaded_source_paths"]==51 and snapshot["git_subprocesses"]==0
assert snapshot["original_intent_sha256"]==sha(R/"batch-intent.json")
assert read("preflight/lifecycle-cleanup.json")["status"]=="PASS"
current_names=[x["path"] for x in index["files"] if not x["path"].startswith("original-products/originals/")]
assert not any(".xcresult/" in n or n.endswith("-tests.json") or n.endswith("-summary.json") for n in current_names)
report={"protocol":"release-451635-independent-original-outcome-review-v1","status":"PASS_ORIGINAL_FAILURE_BOUNDARY_VERIFIED","run_id":45163515182,"attempt":1,"controller_source_sha":HEAD,"app_source_sha":APP,"artifact_id":14813934109,"artifact_sha256":index["archive_sha256"],"original_files_verified":95,"original_archive_extraction_sha256":sha(D/"original-extraction.json"),"current_controller_git_bindings":bindings,"restored_native_entries_receipt":5211,"restored_ui_entries_receipt":30,"restored_product_bytes_not_in_new_result_artifact":True,"app_builds_this_run":0,"ui_runner_builds_this_run":0,"current_product_methods_executed":0,"original_failure":{"phase":lane["phase"],"type":"TimeoutExpired","command":command["argv"],"timeout_seconds":180,"return_code":-15,"boot_command_exit_code":0,"bootstatus_output_bytes":0,"underlying_boot_cause_established":False},"owned_kernel_cleanup_groups":5,"owned_devices_delete_exit0":3,"outer_cleanup_status":"PASS","cleanup_source_admission":snapshot,"readiness_accepted":False,"release_accepted":False,"old_tests_replayed_by_audit":0,"new_tests_executed_by_audit":0,"reader_source_sha256":sha(pathlib.Path(__file__))}
out=D/"root-original-outcome-review.json";raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
with out.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
out.chmod(0o400)
print(json.dumps({"status":report["status"],"receipt":str(out),"sha256":hashlib.sha256(raw).hexdigest(),"source_bindings":len(bindings),"product_methods":0,"first_failure":"OWNED_SIMULATOR_READINESS bootstatus180 TimeoutExpired","owned_kernel_cleanup_groups":5,"deleted_owned_devices":3}))
