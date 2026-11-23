from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-page-mounted-kernel-20261123")
BASE=Path("/mnt/development/projects/evidence/semantic-mounted-kernel-20261123")
D=BASE/"attempt1";A=BASE/"audit1";HEAD="b217a4646dfa5cea28c8dc4f97e1cc848845e22b"
assert shutil.disk_usage("/mnt/development").free>=2500000000
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(ROOT),*a],stderr=subprocess.PIPE,timeout=30)
assert git("rev-parse","HEAD").decode().strip()==HEAD and not git("status","--porcelain").strip()
assert not (A/"audit.json").exists()
r=read(D/"result.json")
assert sha(D/"result.json")=="d192a86274400acb1309d732b8a20bc31ba23e22e9a5d02efd51e9581b67b84f"
assert r["source_sha"]==HEAD and r["status"]=="PASS_ONE_NEW_MOUNTED_CALLER_CONTROL"
assert (r["tests_run"],r["failures"],r["errors"],r["skipped"])==(1,0,0,0)
assert r["new_app_or_ui_builds"]==r["old_control_methods_reexecuted"]==r["product_methods"]==r["apple_commands"]==0
assert r["actual_apple_acceptance"]=="NOT_RUN"
files={p.relative_to(D).as_posix():p for p in D.rglob("*") if p.is_file()}
assert all(not p.is_symlink() and p.resolve()==p for p in D.rglob("*"))
assert set(files)==set(r["originals"])|{"result.json"}
for name,item in r["originals"].items():
 p=files[name];s=p.stat()
 assert sha(p)==item["sha256"] and s.st_size==item["bytes"] and stat.S_IMODE(s.st_mode)==item["mode"]
m=read(ROOT/"docs/validation/20261123-semantic-mounted-kernel/control-inputs.json")
before=read(D/"source-before.json");after=read(D/"source-after.json")
assert before==after and len(before["inputs"])==35
assert before["source_sha"]==HEAD and before["input_manifest_sha256"]==sha(ROOT/"docs/validation/20261123-semantic-mounted-kernel/control-inputs.json")
assert set(before["inputs"])==set(m["files"])
for name,item in before["inputs"].items():
 p=ROOT/name;s=p.stat()
 assert p.resolve()==p and not p.is_symlink()
 assert item=={"sha256":sha(p),"bytes":s.st_size,"mode":stat.S_IMODE(s.st_mode),"inode":s.st_ino,"device":s.st_dev,"mtime_ns":s.st_mtime_ns}
 assert item["sha256"]==m["files"][name]["sha256"] and item["bytes"]==m["files"][name]["bytes"]
 assert git("show",HEAD+":"+name)==p.read_bytes()
lb=read(D/"loaded-sources-before.json");la=read(D/"loaded-sources-after.json")
assert lb==la==read(D/"originals/actual-import-source-closure-before.json")==read(D/"originals/actual-import-source-closure-after.json")
policy="Tools/PinkhaNativeDerived/package_evidence.py"
assert len(lb)==34 and set(lb)==set(m["files"])-{policy}
for name,item in lb.items():
 assert item["sha256"]==m["files"][name]["sha256"] and item["aliases"] and len(item["aliases"])==len(set(item["aliases"]))
assert "page154_mounted_kernel_control_subject" in lb["Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py"]["aliases"]
assert "page154_original_consumer_helpers" in lb["Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py"]["aliases"]
method="test_mounted_kernel_quiescence.MountedPageKernelCompositionTests."+m["selected_methods"][0]
events=read(D/"events.json")
assert [(x["event"],x["test"]) for x in events]==[("START",method),("PASS",method)]
log=(D/"controls.log").read_text()
assert log.count("Ran 1 test in ")==1 and log.endswith("\nOK\n")
assert sha(D/"original-controller.py")=="1b3b4396f27f3df67eabdfa255cac314db870721b4de6583d317ee01b0697fa7"
scope=read(D/"originals/scope.json")
assert scope["control_method"]==method and scope["actual_mounted_consumer_imported"] is True
assert scope["actual_owned_children"]==scope["actual_kernel_absence_observations"]==2
assert scope["injected_kernel_query_errors"]==1 and scope["synthetic_refusal_observations"]==2
assert scope["actual_apple_commands"]==scope["product_methods"]==scope["old_control_methods"]==0
assert scope["actual_page_readiness_or_product_acceptance"]=="NOT_RUN" and scope["first_actual_timeout_retained"] is True
c=read(D/"originals/actual-complete/actual-child.command.json")
t=read(D/"originals/actual-timeout/actual-timeout.command.json")
cl=read(D/"originals/actual-complete/actual-child.log")
tl=read(D/"originals/actual-timeout/actual-timeout.log")
cp=read(D/"originals/actual-complete-proof.json");tp=read(D/"originals/actual-timeout-proof.json")
cr=read(D/"originals/actual-complete/execution.json")["commands"]
tr=read(D/"originals/actual-timeout/execution.json")["commands"]
assert len(cr)==len(tr)==1 and c["worker_pid"]!=t["worker_pid"]
for raw,cal,row in ((c,cl,cr[0]),(t,tl,tr[0])):
 assert type(raw["worker_pid"]) is int and raw["worker_pid"]>1
 assert cal["pid"]==cal["pgid"]==raw["worker_pid"]
 assert raw["owned_group_cleanup"]=="TERM_THEN_KILL" and "cleanup_error_type" not in raw
 assert all(row[k]==v for k,v in raw.items())
assert c["status"]=="COMPLETE" and c["return_code"]==0 and c["timeout_seconds"]==5
assert t["status"]=="TIMED_OUT" and t["error_type"]=="TimeoutExpired" and t["return_code"]==-15 and t["timeout_seconds"]==0.2
assert cp["command_sha256"]==sha(D/"originals/actual-complete/actual-child.command.json")
assert cp["log_sha256"]==sha(D/"originals/actual-complete/actual-child.log")
q=cp["quiescence"];assert q==cr[0]["owned_group_quiescence"]
assert q["status"]=="PASS" and q["live_members"]==0 and q["observations"]==0 and q["budget_seconds"]==10 and q["absence_source"]=="KERNEL_ESRCH"
assert tp["original_command_sha256"]==sha(D/"originals/actual-timeout/actual-timeout.command.json")
assert tp["original_log_sha256"]==sha(D/"originals/actual-timeout/actual-timeout.log")
assert tp["primary_type"]=="TimeoutExpired" and tp["primary_object_preserved"] is True and tp["original_projection_stays_failed"] is True
assert "owned_group_quiescence" not in tr[0] and tr[0]["quiescence_failure"]==tp["quiescence_failure"]
failure=tp["quiescence_failure"]
assert failure["error_type"]=="PermissionError" and failure["timeout_observations"]==[]
assert failure["quiescence_observation"]["status"]=="FAIL_KERNEL_QUERY"
assert failure["quiescence_observation"]["kernel_group_observation"]["errno"]==1
assert len(tp["injection"])==1 and tp["injection"][0]["kind"]=="SYNTHETIC_KERNEL_EPERM_AFTER_ACTUAL_CLEANUP"
for k,pid in ((q["kernel_group_observation"],c["worker_pid"]),(tp["independent_actual_group_absence"],t["worker_pid"])):
 assert k["operation"]=="os.killpg" and k["signal"]==0 and k["pgid"]==pid and k["errno"]==3 and k["outcome"]=="ABSENT_ESRCH"
 assert k["before_monotonic"]<=k["after_monotonic"]<=k["deadline_monotonic"] and 0<k["deadline_monotonic"]-k["before_monotonic"]<=10
synthetic=read(D/"originals/synthetic-profile-observations.json")
assert len(synthetic)==2 and all(x["actual_os_observation"] is False for x in synthetic)
assert [x["observation"]["status"] for x in synthetic]==["FAIL_DEADLINE","FAIL_PS_AFTER_KERNEL_GROUP_EXISTS"]
assert all(x["original_command_sha256"]==cp["command_sha256"] for x in synthetic)
assert synthetic[1]["observation"]["live_members"] is None
launch=read(BASE/"launch1/launch.json")
assert launch["source_sha"]==HEAD and launch["return_code"]==0
assert launch["controller_sha256"]==sha(D/"original-controller.py")
assert launch["stdout_sha256"]==sha(BASE/"launch1/stdout.log") and launch["stderr_sha256"]==sha(BASE/"launch1/stderr.log")
assert (BASE/"launch1/stderr.log").read_bytes()==b""
out={"protocol":"pinkha-page154-mounted-kernel-original-evidence-audit-v1","status":"PASS_ORIGINAL_ONE_CONTROL_EVIDENCE","source_sha":HEAD,"result_sha256":sha(D/"result.json"),"log_sha256":sha(D/"controls.log"),"events_sha256":sha(D/"events.json"),"original_files":{n:{"sha256":sha(p),"bytes":p.stat().st_size,"mode":stat.S_IMODE(p.stat().st_mode)}for n,p in files.items()},"source_inputs":35,"actual_loaded_repository_sources":34,"source_and_loaded_before_after_exact":True,"actual_named_methods":[method],"actual_pass":1,"actual_failed":0,"actual_children":[{"pid":c["worker_pid"],"pgid":cl["pgid"],"status":c["status"]},{"pid":t["worker_pid"],"pgid":tl["pgid"],"status":t["status"]}],"actual_timely_kernel_absence_observations":2,"primary_timeout_object_preservation_established_by_frozen_test_assertion":True,"original_timeout_and_query_failure_preserved":True,"injected_query_errors":1,"explicit_synthetic_refusals":2,"original_failure_replay":0,"old_control_methods_reexecuted":0,"Apple_or_product_methods":0,"full_Page_acceptance":"NOT_RUN","audit_reader_sha256":sha(Path(__file__)),"free_bytes":shutil.disk_usage("/mnt/development").free}
assert out["free_bytes"]>=2500000000
with (A/"audit.json").open("x") as f:json.dump(out,f,sort_keys=True,indent=2);f.write("\n")
print(json.dumps({"status":out["status"],"source_sha":HEAD,"audit_sha256":sha(A/"audit.json"),"original_files":len(files),"source_inputs":35,"loaded_sources":34,"actual_method_pass":1,"actual_children":out["actual_children"],"free_bytes":out["free_bytes"]}))
