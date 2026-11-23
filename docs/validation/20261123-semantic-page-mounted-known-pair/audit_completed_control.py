#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,shutil
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123")
ORIGINAL=Path("/mnt/development/projects/diagnostics/semantic-page-mounted-known-pair-20261123")
DOC=ROOT/"docs/validation/20261123-semantic-page-mounted-known-pair"
FROZEN="f24dc168c1755482b92e642d7c7296210795e0e5"
NAME="test_mounted_known_pair.MountedKnownPairAdapterControl.test_mounted_import_and_owned_region_use_qualified_pair_without_fallback"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,v):
 with p.open("x") as f:f.write(json.dumps(v,sort_keys=True,indent=2)+"\n")
def git(*a):return subprocess.check_output(["git","-C",str(ROOT),*a])
assert git("rev-parse","HEAD").decode().strip()==FROZEN and not git("status","--porcelain")
assert shutil.disk_usage("/mnt/development").free>2500000000
review=read(DOC/"source-review.json")
assert sha(DOC/"source-review.json")=="0782d3cbd0b88238884a1f1b529f0c32caae6702222132c7e2f8827262b29923"
attempt=ORIGINAL/"attempt3"
receipt=read(attempt/"receipt.json");assert receipt["status"]=="PASS_ONE_NEW_MOUNTED_ADAPTER_CONTROL" and receipt["source_sha"]==FROZEN
assert receipt["returncode"]==0 and receipt["result"]["tests_run"]==1
assert receipt["result"]["failures"]==receipt["result"]["errors"]==receipt["result"]["skips"]==0
assert receipt["named_starts"]==receipt["named_passes"]==[NAME]
for name,row in receipt["files"].items():
 p=attempt/name;assert p.stat().st_size==row["bytes"] and sha(p)==row["sha256"],name
events=[json.loads(v) for v in (attempt/"events.jsonl").read_text().splitlines()]
assert [(v["event"],v["method"]) for v in events]==[("START",NAME),("PASS",NAME)]
before=read(attempt/"source-before.json");after=read(attempt/"source-after.json")
assert before==after and len(before)==172
for name,row in before.items():
 raw=(ROOT/name).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==row["sha256"]==review["source_sha256"][name]
 assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==row["git"]["oid"]
 assert git("rev-parse",FROZEN+":"+name).decode().strip()==row["git"]["oid"]
loaded=read(attempt/"loaded-repo-modules.json")
static=read(ORIGINAL/"static-import-closure.json")["modules"]
assert len(loaded)==33 and set(loaded)==set(static)
assert all(h==static[n]["sha256"]==review["source_sha256"][n] for n,h in loaded.items())
first=read(ORIGINAL/"attempt1/receipt.json")
assert first["result"]["tests_run"]==1 and first["result"]["errors"]==1 and first["named_passes"]==[]
assert (ORIGINAL/"attempt1/runner.py").read_bytes()==(attempt/"runner.py").read_bytes()
assert set(p.name for p in (ORIGINAL/"attempt2").iterdir())=={"runner.py"}
blocked=read(ORIGINAL/"execute-retry-command.json");assert blocked["returncode"]==1
guardlog=(ORIGINAL/"execute-retry-original.log").read_text()
assert "AssertionError: 2481676288" in guardlog
expected={"Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py":"57750eb5050d33eec1d4de4a02dbaefa083667d717877b6dd167db2df63500b3","Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_known_pair.py":"effc2dda81c383c4e3aad97a63569bbe553b32686fd54f72c3534596677f224a","Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_simulator.py":"3282bc162cef0486cd334fbdeb2ed2dcdf79980acf1e8d675badd26f273f56e1","Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py":"17205ab71cdfd8111fc21e6d070a42f621be727e47df9457685557bd22ee12fe","Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json":"19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f","Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json":"17c37d842009b23d50ab2222383c1f025242aa2e61f1828cf1bc1a346b5ed7e5"}
for n,h in expected.items():assert sha(ROOT/n)==h
known=DOC/"retained-component.json";retained=read(known)
assert len(retained["retained_four_method_names"])==4 and retained["old_tests_rerun"]==0
copies=[]
def copy(source,destination):
 destination.parent.mkdir(parents=True,exist_ok=True)
 with destination.open("xb") as f:f.write(source.read_bytes())
 assert sha(source)==sha(destination)
 copies.append({"original_path":str(source),"copy_path":destination.relative_to(DOC).as_posix(),"bytes":source.stat().st_size,"sha256":sha(source)})
for p in sorted(attempt.iterdir()):
 if p.is_file():copy(p,DOC/"attempt3"/p.name)
for name in ["execute_failed_control_retry.py","execute-retry-original.log","execute-retry-command.json"]:
 copy(ORIGINAL/name,DOC/"attempt2-blocked"/name)
copy(ORIGINAL/"attempt2/runner.py",DOC/"attempt2-blocked/runner.py")
for name in ["execute_failed_control_after_capacity.py","execute-after-capacity-original.log","execute-after-capacity-command.json"]:
 copy(ORIGINAL/name,DOC/"attempt3"/name)
rootreview=Path("/mnt/development/projects/diagnostics/page154-success-and-products-root-review-20261123")
assert sha(rootreview/"root-review.json")=="9ee74166954495a20c469e7dd5d7bec2af4bb4eba6572f6a874ae2318bb2a403"
for name in ["root-review.json","review_originals.py","review.stdout","review.stderr"]:
 copy(rootreview/name,DOC/"independent-root-review"/name)
reclaim=Path("/mnt/development/projects/diagnostics/inline-swift-intermediate-capacity-review-20261123/reclaim-receipt.json")
assert sha(reclaim)=="5c34dcf1951556006113f110ce12834412d16d2b549ba3032f3089f95cf962cc"
copy(reclaim,DOC/"capacity/reclaim-receipt.json")
report={"status":"PASS_ONE_NEW_MOUNTED_KNOWN_PAIR_ADAPTER","source_sha":FROZEN,"source_commit_chain":["8a6d64ba152ba3aa4bb4376d070f63f5c9daceca","ad7425fd60bb2c76e943c9cfc77af8e6984cb845",FROZEN],"review_sha256":sha(DOC/"source-review.json"),"qualified_method":NAME,"current_actual_passed":1,"current_actual_failed":0,"current_actual_skipped":0,"original_unittest_seconds":0.196,"attempt1":{"source_sha":"ad7425fd60bb2c76e943c9cfc77af8e6984cb845","actual_started":1,"actual_errors":1,"actual_passed":0,"receipt_sha256":sha(ORIGINAL/"attempt1/receipt.json")},"attempt2":{"guard_free_bytes":2481676288,"required_free_bytes":2500000000,"actual_methods_started":0,"original_command_sha256":sha(ORIGINAL/"execute-retry-command.json")},"attempt3":{"actual_started":1,"actual_passed":1,"receipt_sha256":sha(attempt/"receipt.json"),"event_sha256":sha(attempt/"events.jsonl"),"original_log_sha256":sha(attempt/"controls.log")},"runner_byte_identical_across_actual_attempts":True,"controller_and_method_unchanged_across_attempts":True,"exact_source_inputs":172,"actual_loaded_modules":33,"actual_loaded_graph_equals_static_preflight":True,"retained_policy_passes":4,"retained_policy_reruns":0,"old_mounted_controls_rerun":0,"product_tests":0,"simulator_commands":0,"builds":0,"full_restores":0,"fixed_source_hashes":expected,"copied_originals":copies,"original_admission_qualification_unchanged":True,"root_combined_native_and_products_review_sha256":sha(rootreview/"root-review.json"),"capacity_reclaim_receipt_sha256":sha(reclaim),"limits":{"mounted_preparation":"NOT_RUN","actual_mounted_editor":"NOT_RUN","Apple_cold_reopen":"NOT_RUN","physical_device":"NOT_RUN","shipping":"OFF","full_product_acceptance":False},"audit_script_sha256":sha(Path(__file__)),"free_bytes":shutil.disk_usage("/mnt/development").free}
copy(Path(__file__),DOC/"audit_completed_control.py")
save(DOC/"qualification.json",report)
with (DOC/".gitattributes").open("a") as f:f.write("attempt3/*.log binary\nattempt2-blocked/*.log binary\nindependent-root-review/*.stdout binary\nindependent-root-review/*.stderr binary\n")
with (DOC/"README.md").open("a") as f:f.write("""
## Actual final outcome

At frozen f24dc168c1755482b92e642d7c7296210795e0e5, the failed new method was executed once more and passed: one named START/PASS, zero failures/errors/skips, original unittest duration 0.196 seconds. All 172 frozen input bytes and Git object bindings were unchanged. The actual 33 loaded repository modules exactly equal the statically reviewed import graph. The runner, controller and test source remained byte-identical across the two actual executions.

An intervening attempt stopped at the unchanged 2.5GB capacity guard, with 2,481,676,288 bytes free, before any test import or execution. Its original controller and output are preserved under attempt2-blocked. Root then independently reclaimed only the 618 reviewed Swift object/module-cache files while retaining Products and all other evidence. The actual passing retry is preserved under attempt3. The first import ERROR remains under attempt1. Only one distinct new method qualifies; the original four pair methods were not repeated.

The root's independent original native-result and Products admission review, its exact script and original stdout/stderr are copied unchanged under independent-root-review. The earlier admission qualification stays historical and unchanged. This completed controller adapter addresses the separately reported known-pair dispatch issue; it does not execute or qualify mounted preparation, the editor journey or Apple cold reopen. Those remain separate real Mac work owned by the root dispatcher.
""")
print(json.dumps({"status":report["status"],"qualification_sha256":sha(DOC/"qualification.json"),"copied_originals":len(copies),"copied_bytes":sum(v["bytes"] for v in copies),"actual_loaded_modules":len(loaded),"source_inputs":len(before),"free":report["free_bytes"]}))
