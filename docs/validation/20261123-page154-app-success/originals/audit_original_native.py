#!/usr/bin/env python3
"""Read-only audit of the single retained Page154 Apple run; executes no tests."""
from pathlib import Path
import ast, base64, hashlib, json, plistlib, re, subprocess, types
from datetime import datetime, timezone

ROOT = Path("/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit")
SELECTED = ROOT / "native-selected"
MIRROR = "/mnt/development/projects/git-mirrors/anytype-swift.git"
SOURCE = "68148339c275268795360d71d519a5baf003adf8"
RUN = 45116855451
ARTIFACT = 14794983588
ZIP_SHA = "082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46"
SELECTOR = "AnytypeTests/SemanticAnchorPage154NativeAcceptanceTests/testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument"
CONTRACT = "Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_contract.py"
CONTRACT_SHA = "235eae83ac85a8c280a10cf570e6675b87d11f6059c2ed46a2a12fda7c2df894"
def require(value, why):
    if not value: raise ValueError(why)
def sha(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(path.read_bytes())
def write_exact(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): require(path.read_bytes() == raw, "Refusing changed audit copy: " + str(path))
    else: path.write_bytes(raw)
def canonical(value): return json.loads(json.dumps(value, sort_keys=True))
def git_bytes(path):
    return subprocess.check_output(["git", "--git-dir="+MIRROR, "show", SOURCE+":"+path], timeout=30)

download = read_json(ROOT/"download-result.json")
require(download["status"]=="VERIFIED_ORIGINAL_ZIP" and download["actual_sha256"]==ZIP_SHA
        and download["actual_bytes"]==703289417 and download["declared_bytes"]==703289417
        and download["return_code"]==0 and download["run_id"]==RUN
        and download["run_attempt"]==1 and download["source_sha"]==SOURCE, "Wrong verified ZIP receipt")
require((ROOT/"artifact-14794983588.zip").stat().st_size==703289417, "ZIP changed size")
# The complete SHA was computed during the sole download. Do not reread 703 MB here.
terminal=read_json(ROOT/"terminal-observer.json")
require(terminal["id"]==RUN and terminal["run_attempt"]==1 and terminal["head_sha"]==SOURCE
        and terminal["status"]=="completed" and terminal["conclusion"]=="success", "Wrong terminal run")
api=read_json(ROOT/"original-artifacts-api.json")
require(api["total_count"]==1 and len(api["artifacts"])==1, "Unexpected artifacts")
artifact=api["artifacts"][0]
require(artifact["id"]==ARTIFACT and artifact["digest"]=="sha256:"+ZIP_SHA
        and artifact["size_in_bytes"]==703289417 and artifact["workflow_run"]["id"]==RUN
        and artifact["workflow_run"]["head_sha"]==SOURCE and not artifact["expired"], "API artifact origin differs")
jobs=read_json(ROOT/"original-attempt1-jobs-api.json")["jobs"]
job=[x for x in jobs if x["id"]==137501560037]
require(len(job)==1, "Wrong actual job")
job=job[0]
require(job["run_id"]==RUN and job["run_attempt"]==1 and job["head_sha"]==SOURCE
        and job["conclusion"]=="success" and job["runner_id"]==1000024441, "Wrong actual job origin")
selected_proof=read_json(ROOT/"native-selected-proof.json")
require(selected_proof["outer_sha256"]==ZIP_SHA, "Selected proof origin differs")
for row in selected_proof["members"]:
    raw=(SELECTED/row["name"]).read_bytes()
    require(len(raw)==row["bytes"] and sha(raw)==row["sha256"], "Changed original member: "+row["name"])

execution=read_json(SELECTED/"execution.json")
require(execution["protocol"]=="pinkha-semantic-page154-apple-consumer-v1"
        and execution["status"]=="PASS_ACTUAL_APP_FACTORY_EVENT_AND_READBACK"
        and execution["phase"]=="COMPLETE" and execution["source_and_framework_unchanged"] is True,
        "Original controller did not complete")
expected_binding={"sourceSHA":SOURCE, "runID":str(RUN), "runAttempt":"1",
                  "nonce":"70ae6b5bf7e34694b1917fda763475db"}
require(execution["binding"]==expected_binding, "Wrong run/nonce binding")
for key in ("native_builds","native_methods_rerun","existing_product_methods_rerun"):
    require(type(execution[key]) is int and execution[key]==0, "Unexpected repeated scope")
require(execution["app_builds_started"]==1 and execution["app_build_succeeded"] is True
        and execution["actual_xctest_commands_started"]==1 and execution["actual_product_methods_passed"]==1,
        "Wrong actual build/execution count")

before=read_json(SELECTED/"source-before.json"); after=read_json(SELECTED/"source-after.json")
require(before==after and (SELECTED/"source-before.json").read_bytes()==(SELECTED/"source-after.json").read_bytes(),
        "Source changed during original run")
tree=subprocess.check_output(["git","--git-dir="+MIRROR,"ls-tree","-rz",SOURCE],timeout=30)
tree_paths={r.split(b"\t",1)[1].decode("utf8") for r in tree.split(b"\0") if r}
require(tree_paths==set(before) and len(before)==12033, "Original tracked checkout inventory differs")
pins_path="Tools/PinkhaSemanticAnchorWire/apple_consumer/candidate-sources.json"
pins_raw=git_bytes(pins_path); pins=json.loads(pins_raw)
sources=set(pins)|{pins_path, CONTRACT,
 "Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py",
 "Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_simulator.py",
 "Tools/PinkhaSemanticAnchorWire/apple_consumer/ui_build.py",
 "Tools/PinkhaSemanticAnchorWire/apple_runtime/contract.py",
 "Tools/PinkhaSimulatorGate/early_build_products.py",
 "Tools/PinkhaSimulatorGate/run_owned_single_lane.py",
 "Tools/PinkhaSimulatorGate/run_ui27.py",
 "Tools/PinkhaSimulatorGate/shared_editor_existing_build.py",
 "Tools/PinkhaSimulatorGate/wave15_batch.py",
 ".github/workflows/pinkha-semantic-page-apple-consumer.yml",
 ".github/workflows/torah-inspector-ipados27.yml"}
require(sources<=tree_paths, "Missing exact audit source")
source_rows={}
for path in sorted(sources):
    raw=git_bytes(path); digest=sha(raw)
    require(before[path]==digest, "Original checkout source pin differs: "+path)
    if path in pins: require(pins[path]==digest, "Candidate manifest source pin differs: "+path)
    write_exact(ROOT/"audited-source"/path,raw)
    source_rows[path]={"sha256":digest,"bytes":len(raw)}
raw=(ROOT/"audited-source"/CONTRACT).read_bytes()
require(sha(raw)==CONTRACT_SHA, "Wrong exact original proof implementation")
allowed={"__future__","base64","binascii","copy","hashlib","json","pathlib","plistlib","re","shutil","tarfile"}
for node in ast.parse(raw).body:
    if isinstance(node,ast.Import): require(all(x.name in allowed for x in node.names),"Unexpected proof dependency")
    if isinstance(node,ast.ImportFrom): require(node.module in allowed,"Unexpected proof dependency")
module=types.ModuleType("original_page154_contract")
module.__file__=str(ROOT/"audited-source"/CONTRACT)
exec(compile(raw,module.__file__,"exec"),module.__dict__)
owned=execution["owned_simulator"];udid=owned["udid"]
require(udid=="6CC8D466-1200-4C0B-A3EF-8DADF62A565F" and owned["nonce"]==expected_binding["nonce"],
        "Wrong owned simulator")
actual=module.exact_execution(read_json(SELECTED/"actual-summary.json"),read_json(SELECTED/"actual-tests.json"),udid)
require(canonical(actual)==execution["actual_execution"], "Actual XCTest originals differ from receipt")
attachment=module.attachment(SELECTED/"actual-attachments",udid)
observed=module.observation(read_json(attachment),expected_binding)
require(observed==execution["observation"] and sha(attachment.read_bytes())==execution["observation_sha256"],
        "Native original attachment differs from validated receipt")
enum=read_json(SELECTED/"enumeration.json")
require(enum["errors"]==[] and len(enum["values"])==1,"Enumeration error or extra plan")
value=enum["values"][0]
require(value["testPlan"]=="AnytypeTests" and value["enabledTests"]==[{"identifier":SELECTOR+"()"}],
        "Enumeration did not admit exactly the one native boundary")
require(all(row["identifier"]!=SELECTOR+"()" for row in value["disabledTests"]),"Selected method disabled")
require(sha((SELECTED/"enumeration.json").read_bytes())==execution["enumeration"]["sha256"],
        "Enumeration digest differs")
commands=execution["commands"]
require(len(commands)==23,"Unexpected command cardinality")
for command in commands:
    q=command["owned_group_quiescence"]
    require(command["return_code"]==0 and command["status"]=="COMPLETE"
            and q["status"]=="PASS" and q["live_members"]==0 and q["pgid"]==command["worker_pid"]
            and q["budget_seconds"]==10 and q["observations"]>=1 and q["timeout_observations"]==[],
            "Command or owned process group unqualified: "+command["name"])
    log=SELECTED/(command["name"]+".log")
    if log.exists(): require(sha(log.read_bytes())==command["log_sha256"],"Command log hash differs")
actual_commands=[x for x in commands if x["argv"][:2]==["xcodebuild","test-without-building"]
                 and "-enumerate-tests" not in x["argv"]]
require(len(actual_commands)==1,"Unexpected extra actual test command")
for name in ("enumerate-exact-one","actual-single-xctest"):
    c=next(x for x in commands if x["name"]==name);argv=c["argv"]
    require(argv[argv.index("-only-testing")+1]==SELECTOR
            and argv[argv.index("-destination")+1]=="platform=iOS Simulator,id="+udid
            and argv.count("-only-testing")==1, "Exact actual selector/destination differs")
build=next(x for x in commands if x["name"]=="build-actual-candidate-app")
require(build["argv"][build["argv"].index("-configuration")+1]=="Debug-Anytype"
        and "OTHER_SWIFT_FLAGS=$(inherited) -D DEBUG -D PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 -D PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1" in build["argv"],
        "App candidate gate inactive")
for action in ("shutdown","delete"):
    c=next(x for x in commands if x["name"]=="cleanup-owned-"+action)
    require(c["argv"]==["xcrun","simctl",action,udid] and execution["owned_simulator_cleanup"][action]=={"return_code":0,"status":"PASS"},
            "Wrong owned simulator cleanup")
raw_log=(SELECTED/"actual-single-xctest.log").read_text(errors="strict")
terminal_text="Test Case '-[AnytypeTests.SemanticAnchorPage154NativeAcceptanceTests testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument]' passed (9.922 seconds)."
require(raw_log.count(terminal_text)==1 and "Executed 1 test, with 0 failures (0 unexpected)" in raw_log,
        "Raw XCTest terminal missing or duplicated")
require(len(re.findall(r"Test Case '-\[.*?\]' passed \(",raw_log))==1,"Extra passing raw XCTest")
bound=(SELECTED/"bound.xctestrun").read_bytes()
require(sha(bound)==execution["descriptor"]["copied_sha256"],"Bound descriptor hash differs")
pl=plistlib.loads(bound)
configs=pl["TestConfigurations"]
require(len(configs)==1 and len(configs[0]["TestTargets"])==1,"Bound descriptor contains extra target")
target=configs[0]["TestTargets"][0]
require(target["BlueprintName"]=="AnytypeTests"
        and target["OnlyTestIdentifiers"]==[SELECTOR.split("/",1)[1]], "Bound descriptor selector differs")
expected_env={"PINKHA_SEMANTIC_PAGE154_APPLE_CONSUMER":"1",
 "PINKHA_SEMANTIC_PAGE154_SOURCE_SHA":SOURCE,"PINKHA_SEMANTIC_PAGE154_RUN_ID":str(RUN),
 "PINKHA_SEMANTIC_PAGE154_RUN_ATTEMPT":"1","PINKHA_SEMANTIC_PAGE154_NONCE":expected_binding["nonce"]}
require(all(target["EnvironmentVariables"].get(k)==v for k,v in expected_env.items()),"Bound nonce environment differs")
copies=read_json(SELECTED/"runtime-copies.json")
require(copies["root_present"] is True and copies["test_host_present"] is True and len(copies["copies"])==2
        and all(x["marker_present"] is True for x in copies["copies"].values())
        and len({x["sha256"] for x in copies["copies"].values()})==1,"Actual compiled runtime copies differ")
require(execution["producer"]["run_id"]=="45098093058"
        and execution["producer"]["source_sha"]=="70c6aa3447baae2d8e2681228fb50236c4c60b3b"
        and execution["producer"]["archive_sha256"]==module.ARCHIVE_SHA, "Native framework lineage differs")
ui=execution["ui_runner_build"]
require(ui["builds_started"]==ui["builds_succeeded"]==1 and ui["ui_executions"]==ui["preparation_executions"]==0
        and ui["acceptance"]=="NOT_RUN" and ui["status"]=="BUILD_ONLY_ORIGINAL_PRODUCTS_PRESERVED",
        "Mounted UI scope was relabelled")
require(execution["limits"]==module.LIMITS and observed["limits"]==module.LIMITS,"Scope limits changed")
originals={str(path.relative_to(ROOT)):{"bytes":path.stat().st_size,"sha256":sha(path.read_bytes())}
           for path in [ROOT/"download-result.json",ROOT/"original-attempt1-jobs-api.json",
             ROOT/"original-artifacts-api.json",ROOT/"terminal-observer.json",
             ROOT/"original-job-137501560037.log",ROOT/"outer-inventory.json",ROOT/"native-selected-proof.json"]}
result={
 "schema":"pinkha-page154-original-native-audit-v1","status":"PASS_ACTUAL_NATIVE_BOUNDARY_ONE",
 "audited_at":datetime.now(timezone.utc).isoformat(),"run_id":RUN,"run_attempt":1,"source_sha":SOURCE,
 "artifact":{"id":ARTIFACT,"bytes":703289417,"sha256":ZIP_SHA,"full_hash_verified_during_sole_download":True},
 "runner":{"id":job["runner_id"],"name":job["runner_name"],"job_id":job["id"]},
 "actual_execution":canonical(actual),"binding":expected_binding,"observation":observed,
 "actual_attachment":{"path":str(attachment.relative_to(ROOT)),"bytes":attachment.stat().st_size,"sha256":sha(attachment.read_bytes())},
 "raw_terminal":{"exact_test_case_occurrences":1,"text":terminal_text,"interleaved_native_log_preserved":True},
 "source":{"tracked_before_after_count":12033,"tracked_set_matches_exact_git_tree":True,
           "before_after_byte_identical":True,"before_sha256":sha((SELECTED/"source-before.json").read_bytes()),
           "candidate_pin_count":len(pins),"independently_read_git_source_count":len(source_rows),
           "independently_read_git_sources":source_rows,
           "all_tracked_blobs_verified_by_original_checkout_inputs":True,
           "all_12033_blob_contents_reread_in_this_audit":False},
 "commands":{"count":23,"all_return_zero":True,"all_owned_groups_actual_zero":True,"timeout_observations":0,
             "app_builds":1,"ui_runner_builds":1,"actual_xctest_executions":1,"native_builds":0},
 "enumeration":{"plan":"AnytypeTests","enabled":1,"disabled":len(value["disabledTests"]),"errors":0,"selector":SELECTOR},
 "owned_simulator":owned,"owned_simulator_cleanup":execution["owned_simulator_cleanup"],
 "product_transport":{"native":execution["early_products"],"ui":ui["early_products"],
                      "independent_archive_inventory_owner":"/root/editor_migration",
                      "mounted_reuse_admission":"SEPARATE_REVIEW_REQUIRED"},
 "limits":module.LIMITS,"originals":originals,
 "audit_activity":{"product_methods_executed":0,"controller_tests_executed":0,"builds":0,"download_count":0,
                   "only_original_metadata_validated":True,"exact_original_contract_sha256":CONTRACT_SHA},
 "audit_script_sha256":sha(Path(__file__).read_bytes())
}
data=(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode()
out=ROOT/"INDEPENDENT_NATIVE_AUDIT.json"
require(not out.exists(),"Audit already recorded; read the persisted receipt instead of rerunning")
out.write_bytes(data)
print(json.dumps({"status":result["status"],"audit_sha256":sha(data),"path":str(out),
 "native_methods_passed":1,"new_methods_executed":0,"source_inventory":12033,"selected_git_sources":len(source_rows),
 "all_commands_return_zero":23,"observed_simulator":actual["device"],"ui_acceptance":"NOT_RUN"}))
