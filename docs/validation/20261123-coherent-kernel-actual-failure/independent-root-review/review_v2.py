from pathlib import Path
import ast,datetime,hashlib,io,json,re,subprocess,zipfile
B=Path("/mnt/development/projects/diagnostics/coherent-kernel-actual-result-20261123")
D=B/"diagnosis"; O=D/"originals"; R=Path(__file__).parent
W=Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
CONTROL="a69d0967c1dad4b9476b04af2b681474983e0b96"; APP="d254a4a1ccd9288f585ff9374088cbaf965b36b4"; RUN="45129057825"
def h(b):return hashlib.sha256(b).hexdigest()
def raw(p):
 assert p.is_file() and not p.is_symlink()
 return p.read_bytes()
def j(p):return json.loads(raw(p))
def orig(p):return j(O/p)
def source(rel):return subprocess.check_output(["git","show",CONTROL+":"+rel],cwd=W,timeout=30)
expected={"artifact.zip":"8741a6d631e3152f12fa49109a5c37484443b13aaea47e4765aabc6c89bd2198","job.log":"2a4adf38fc3bbd92cbb6c3c5be814f0e53c1872aa992d36bff266307824bfbed","run.json":"7ca855c95ea651afb0979093fbd30b2f4e4c86c997f2688e0b3d1e0c6026e957","jobs.json":"49b376a200eefa1209b855e15dd4069794617a7b26e54b6c6e551613f93495ba","artifacts.json":"6488cc7a2753dd7aadfe5e3f4a50a5f6276331c19833dced7d5de63873f6dbed"}
for n,s in expected.items():assert h(raw(B/n))==s
run=j(B/"run.json");jobs=j(B/"jobs.json");arts=j(B/"artifacts.json")
assert str(run["id"])==RUN and run["head_sha"]==CONTROL and run["run_attempt"]==1 and run["conclusion"]=="cancelled"
job=next(x for x in jobs["jobs"] if x["id"]==137540092122)
assert job["conclusion"]=="cancelled" and job["started_at"]=="2026-11-23T07:32:12Z" and job["completed_at"]=="2026-11-23T07:44:14Z"
art=next(x for x in arts["artifacts"] if x["id"]==14798796696)
assert art["digest"]=="sha256:"+expected["artifact.zip"] and art["size_in_bytes"]==1599793
inv=j(D/"inventory.json");entries={x["path"]:x for x in inv["entries"]}
assert len(entries)==85 and sum(x["bytes"] for x in entries.values())==7080758
with zipfile.ZipFile(B/"artifact.zip") as outer:
 assert len(outer.infolist())==1 and outer.namelist()==[inv["inner_member"]]
 inner_bytes=outer.read(inv["inner_member"]);assert h(inner_bytes)==inv["inner_sha256"]
with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
 assert len(inner.infolist())==85 and len(set(inner.namelist()))==85 and set(inner.namelist())==set(entries)
 for name in inner.namelist():
  p=Path(name);assert not p.is_absolute() and ".." not in p.parts
  b=inner.read(name);assert raw(O/name)==b
  assert h(b)==entries[name]["sha256"] and len(b)==entries[name]["bytes"]
assert {str(p.relative_to(O)) for p in O.rglob("*") if p.is_file()}==set(entries)
adm=orig("original-products/admission.json");worker=orig("batch-worker.json");editor=orig("lanes/editor/execution.json");exe=orig("execution.json");intent=orig("batch-intent.json")
assert adm["execution_origin"]=={"control_source_sha":CONTROL,"run_attempt":"1","run_id":RUN}
assert adm["app_source_sha"]==APP and adm["status"]=="ORIGINAL_PRODUCTS_ADMITTED_TESTS_NOT_RUN"
original=orig("original-products/originals/batch-worker.json")
assert worker["candidate_input_hashes"]==editor["candidate_input_hashes"]==original["candidate_input_hashes"]
assert len(worker["candidate_input_hashes"])==5929
bindings=adm["controller_source_hashes"];assert len(bindings)==33
for rel,s in bindings.items():assert h(source(rel))==s
assert adm["source_proof"]["tracked_regular_files_compared"]==11468
for r in (worker,exe):
 assert r["app_builds_this_run"]==r["ui_runner_builds_this_run"]==0
 assert r["current_shared_app_accepted"] is False and r["release_accepted"] is False and r["full_matrix_accepted"] is False
kernel=[]
def verify_kernel(q,pid):
 assert type(pid) is int and pid>1
 assert q["status"]=="PASS" and q["absence_source"]=="KERNEL_ESRCH" and q["budget_seconds"]==10
 assert q["pgid"]==pid and q["observations"]==q["live_members"]==0 and q["timeout_observations"]==[]
 k=q["kernel_group_observation"]
 assert k["operation"]=="os.killpg" and k["pgid"]==pid and k["signal"]==0 and k["outcome"]=="ABSENT_ESRCH"
 assert k["errno"]==3 and k["error_type"]=="ProcessLookupError"
 assert k["before_monotonic"]<=k["after_monotonic"]<=k["deadline_monotonic"]
 kernel.append({"pid":pid,"observation":k})
pre=orig("preflight/preflight.json")
assert pre["status"]=="PREFLIGHT_PASS_UI_NOT_RUN" and pre["source_sha"]==CONTROL and pre["run_id"]==RUN
assert len(pre["commands"])==8
for row in pre["commands"]:
 name=row["name"];a=orig("preflight/"+name+".observation.json");c=orig("preflight/"+name+".command.json")
 assert a==row and all(a.get(k)==v for k,v in c.items()) and a["return_code"]==0
 assert a["owned_group_cleanup"]=="TERM_THEN_KILL" and a["log_sha256"]==h(raw(O/"preflight"/(name+".log")))
 verify_kernel(a["owned_group_quiescence"],c["worker_pid"])
for name in ["before","boot","boot-status"]:
 prefix="lanes/editor/owned-readiness/"+name
 p=orig(prefix+".command.json");c=orig(prefix+".owned.command.json")
 assert p["original_owned_command"]==name+".owned.command.json"
 assert p["original_owned_command_sha256"]==h(raw(O/(prefix+".owned.command.json")))
 assert p["argv"]==c["argv"] and p["cwd"]==c["cwd"] and p["return_code"]==0
 assert p["cleanup_profile"]=="coherent-heart-release"
 verify_kernel(p["owned_group_quiescence"],c["worker_pid"])
assert len(kernel)==11 and len({x["pid"] for x in kernel})==11
ready=orig("lanes/editor/owned-readiness/readiness.json")
assert ready["status"]=="OWNED_SIMULATOR_READY" and ready["bootstatus_return_code"]==0 and ready["tests_executed"]==0
lookup=orig("lanes/editor/fresh-container-lookup.observation.json")
assert lookup["status"]=="TIMED_OUT" and lookup["error_type"]=="TimeoutExpired" and lookup["timeout_seconds"]==30
assert lookup["product_methods_executed"]==0 and lookup["container_absence_proved"] is False and lookup["owned_group_absence_proved"] is False
assert lookup["argv"]==["xcrun","simctl","get_app_container","20BAEE0C-6091-49F5-9D94-880A738FF852","io.anytype.app","data"]
for channel in ["stdout","stderr"]:
 r=lookup[channel];assert r["bytes"]==0 and r["sha256"]==h(b"")
 assert not (O/"lanes/editor"/r["path"]).exists()
assert not (O/"lanes/editor/fresh-container.json").exists()
nested=orig("coherent-nested-cleanup.json")
assert worker["coherent_nested_cleanup"]=={"status":"FAIL","error_type":"TimeoutExpired"}
assert nested["status"]=="FAIL" and nested["groups_checked"]==0 and nested["original_owned_commands"]==[]
assert nested["error_type"]=="TimeoutExpired" and "'status', '--porcelain', '--untracked-files=no'" in nested["error"]
outer=orig("batch-worker.command.json")
assert outer["status"]=="FAILED_PROCESS_CLEANUP" and outer["return_code"]==1 and outer["termination_profile"]=="coherent-heart-release"
assert outer["cleanup_error_type"]=="TimeoutExpired" and "'ps', '-axo', 'pid=,pgid=,stat='" in outer["cleanup_error"]
assert exe["supervisor_error"]==outer["cleanup_error"] and exe["error"]==worker["error"]==editor["error"]
clean=orig("batch-cleanup.json")
assert clean["status"]=="PASS"
deleted=[x for x in clean["devices"] if x["status"]=="DELETED_OWNED_SIMULATOR"]
assert len(deleted)==3 and {x["udid"] for x in deleted}=={"CE79FBE1-DFB4-4487-BE5E-B0B461105B45","EB210A8A-CBF1-4839-84E9-253D3CF25DAB","20BAEE0C-6091-49F5-9D94-880A738FF852"}
assert all(x["delete_exit_code"]==0 for x in deleted)
assert all(x.get("shutdown_exit_code",0)==0 for x in deleted)
current=[n for n in entries if not n.startswith("original-products/originals/")]
assert len(current)==74
argv=[]
for name in current:
 if name.endswith(".json"):
  obj=orig(name)
  if isinstance(obj,dict) and isinstance(obj.get("argv"),list):argv.append((name,obj["argv"]))
assert len(argv)==30
assert not any(any(y in x for y in ["test-without-building","build-for-testing","-only-testing:"]) for _,v in argv for x in v if isinstance(x,str))
events=[]
for name in current:
 if name.endswith(".log"):
  for line in raw(O/name).decode(errors="replace").splitlines():
   if re.search(r"Test Case .* (started|passed|failed)",line):events.append(line)
assert events==[]
batch=source("Tools/PinkhaSimulatorGate/wave15_batch.py").decode()
tree=ast.parse(batch)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="run_nested_worker_command")
calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="verify_owned_group_stopped"]
assert len(calls)==1 and calls[0].keywords==[]
first=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="validate_fresh_device_receipt")
assert "NEGATIVE_UNCLASSIFIED" in ast.get_source_segment(batch,first)
repo_flow=source(".github/workflows/pinkha-coherent-original-products.yml").decode()
central=source(".github/workflows/torah-inspector-ipados27.yml").decode()
assert "timeout-minutes: 150" in repo_flow and "timeout-minutes: 120" in repo_flow
assert not re.search(r"^\s*concurrency:",repo_flow,re.M) and not re.search(r"^\s*concurrency:",central,re.M)
assert "The operation was canceled." in raw(B/"job.log").decode()
result={"status":"PASS_INDEPENDENT_ORIGINAL_RELEASE_FAILURE_REVIEW","reviewed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":CONTROL,"original_app":APP,"run_id":RUN,"attempt":1,"actual_conclusion":"cancelled","outer_artifact_sha256":expected["artifact.zip"],"exact_zip_to_extracted_originals":85,"current_namespace_members":74,"original_controller_sources_bound_to_git":33,"identical_original_candidate_inputs":5929,"actual_kernel_esrch_observations":kernel,"actual_new_product_commands":0,"actual_named_test_events":0,"app_builds":0,"ui_builds":0,"readiness_passed":True,"first_preinstall_lookup_status":"TIMED_OUT","lookup_container_absence_proved":False,"missing_original_lookup_raw_streams_preserved_as_missing":True,"nested_cleanup_status":"FAIL","nested_groups_audited":0,"outer_process_cleanup_status":"FAILED_PROCESS_CLEANUP","exact_owned_devices_deleted":3,"all_process_groups_proven_absent":False,"cancellation_cause":"UNKNOWN","deadline_reached":False,"late_source_closure_proven":False,"new_tests_or_downloads":0,"prior_reader_failure":"First reader incorrectly took the compact worker cleanup projection as the full original receipt; corrected to the retained coherent-nested-cleanup.json. Also corrected the static validator function name before reaching that check. No original changed or test rerun.","source_script_sha256":h(raw(Path(__file__)))}
(R/"root-review.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":result["status"],"sha256":h(raw(R/"root-review.json")),"originals":85,"source_bindings":33,"actual_kernel_observations":11,"product_methods":0}))
