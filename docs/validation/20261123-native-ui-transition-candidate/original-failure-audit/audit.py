from pathlib import Path
import json,hashlib,gzip,sqlite3,subprocess,re,os
ROOT=Path("/mnt/development/projects/diagnostics/native-ui-451483-original-result-20261123")
R=ROOT/"private-originals"
G=["git","--no-optional-locks","--git-dir=/mnt/development/projects/git-mirrors/anytype-swift.git"]
CONTROL="9cafd32811e50f4e883efb034888d7ce1e349c02"
APP="4b09cc5478c60c1c6728a54f2a27a115637a835b"
RUN="45148353071"
UDID="4BF2948A-6EA4-472C-85D0-61F939A21E84"
def h(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def canonical(d):return h(json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode())
ledger=read(ROOT/"extraction.json")
invraw=(ROOT/"extracted-inventory.json.gz").read_bytes()
assert h(invraw)==ledger["extracted_inventory_sha256"]
inv=json.loads(gzip.decompress(invraw))
for row in inv["entries"]:
 p=R/row["path"]
 assert row["kind"]=="file" and p.is_file() and not p.is_symlink()
 raw=p.read_bytes()
 assert len(raw)==row["bytes"] and h(raw)==row["sha256"],"original_changed:"+row["path"]
assert len([p for p in R.rglob("*") if p.is_file()])==len(inv["entries"])==3292
ad=read(R/"native-ui-original-products-admission.json")
before=read(R/"native-ui-readiness-source-before.json")
after=read(R/"native-ui-readiness-source-after.json")
assert before["sources"]==after["sources"]
assert ad["controlCommit"]==CONTROL and ad["applicationCommit"]==APP and ad["currentRunID"]==RUN and ad["currentRunAttempt"]==1 and ad["ownedSimulatorUDID"]==UDID
assert (R/"control-source-sha.txt").read_text().strip()==CONTROL
assert (R/"application-source-sha.txt").read_text().strip()==APP
assert ad["currentApplicationBuilds"]==ad["currentUIRunnerBuilds"]==ad["currentNativeLibraryBuilds"]==0
inputs={}
def add(commit,rows,kind):
 for path,digest in rows.items():
  key=(commit,path)
  if key in inputs:assert inputs[key]["sha256"]==digest
  else:inputs[key]={"commit":commit,"path":path,"sha256":digest,"roles":[]}
  inputs[key]["roles"].append(kind)
add(CONTROL,ad["controllerSourceInputs"],"current_controller")
add(CONTROL,ad["qualifiedProvider"]["inputs"],"qualified_provider")
for row in ad["copiedDescriptor"]["currentControlModuleBindings"]:
 add(CONTROL,{row["path"]:row["sha256"]},"actual_imported_descriptor_helper")
for key,row in before["sources"].items():add(row["commit"],row["files"],"readiness_before_after:"+key)
add(APP,ad["sourceProof"]["originalFrozenInputs"],"original_frozen_product_inputs")
for key,row in inputs.items():
 raw=subprocess.check_output(G+["show",row["commit"]+":"+row["path"]])
 assert h(raw)==row["sha256"],"git_input_mismatch:"+row["path"]
 row["bytes"]=len(raw)
for name,row in before["moduleBindings"].items():
 source=before["sources"]["current" if row["origin"]=="CURRENT_CONTROL_CHECKOUT" else "originalApp"]
 assert row["path"] in source["files"]
tree={}
raw=subprocess.check_output(G+["ls-tree","-rz",APP,"--","Modules","NativeApp","Package.resolved","Tools/Hanlin"])
for row in raw.split(b"\0"):
 if not row:continue
 header,name=row.split(b"\t",1);mode,kind,blob=header.decode().split()
 assert kind=="blob" and mode in ("100644","100755")
 tree[name.decode()]=blob
assert len(tree)==ad["sourceProof"]["protectedFiles"]==3600
assert canonical(tree)==ad["sourceProof"]["protectedGitBlobsSHA256"]
metadata=[]
for path,digest in ad["originalMetadataSHA256"].items():
 p=R/"original-451082"/path
 assert h(p.read_bytes())==digest
 metadata.append({"path":str(p.relative_to(R)),"sha256":digest,"bytes":p.stat().st_size})
commands=[]
for p in sorted((R/"native-ui-original-commands").rglob("*.json")):
 row=read(p)
 if not isinstance(row.get("command"),list):continue
 streams={}
 for key in ("stdout","stderr"):
  if key not in row:continue
  rec=row[key];q=p.parent/rec["path"]
  assert q.parent==p.parent and q.is_file() and not q.is_symlink()
  raw=q.read_bytes();assert len(raw)==rec["bytes"] and h(raw)==rec["sha256"]
  streams[key]=rec
 commands.append({"path":str(p.relative_to(R)),"sha256":h(p.read_bytes()),"command":row["command"],"status":row.get("status"),"returncode":row.get("returncode"),"streams":streams})
expected={
"native-ui-continuation":[
"NativeLaunchTests/testHierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType",
"NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen",
"NativeLaunchTests/testSourceDragIntoNativeEditorPreservesTargetAndColdReopens",
"NativeLaunchTests/testHanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen"],
"archive-roundtrip":["NativeLaunchTests/testCanonicalArchiveFilesRoundtripPreservesMappingAndBodies"]}
stages=[]
current_names=[]
for stage,names in expected.items():
 exitrow=read(R/(stage+"-command-exit.json"));obs=read(R/(stage+"-process-observation.json"));plan=read(R/(stage+"-original-products-plan.json"))
 assert exitrow["command"]==obs["command"]==plan["command"]
 assert exitrow["testExit"]==obs["returncode"]==65 and obs["status"]=="EXIT_OBSERVED"
 selectors=[x.removeprefix("-only-testing:PinkhaAnyNativeUITests/") for x in exitrow["command"] if x.startswith("-only-testing:")]
 assert selectors==names and "test-without-building" in exitrow["command"] and "build-for-testing" not in exitrow["command"]
 assert exitrow["command"][exitrow["command"].index("-destination")+1]=="platform=iOS Simulator,id="+UDID
 summary=read(R/(stage+"-test-counts.json"));nodes=read(R/(stage+"-test-methods.json"))
 cases=[]
 def walk(v):
  if isinstance(v,dict):
   if v.get("nodeType")=="Test Case":cases.append(v)
   for value in v.values():walk(value)
  elif isinstance(v,list):
   for value in v:walk(value)
 walk(nodes)
 assert len(cases)==len(names) and {x["nodeIdentifier"].removesuffix("()") for x in cases}==set(names)
 assert all(x["result"]=="Failed" for x in cases)
 assert summary["passedTests"]==summary["skippedTests"]==summary["expectedFailures"]==0
 assert summary["failedTests"]==summary["totalTestCount"]==len(names)
 dev=summary["devicesAndConfigurations"][0]["device"]
 assert dev["deviceId"]==UDID and dev["osBuildNumber"]=="24B8117" and dev["architecture"]=="arm64"
 db=R/(stage+".xcresult")/"database.sqlite3"
 c=sqlite3.connect(db.as_uri()+"?mode=ro&immutable=1",uri=True)
 sql=c.execute("select TestCases.name,TestCaseRuns.result,TestCaseRuns.duration from TestCaseRuns join TestCases on TestCaseRuns.testCase_fk=TestCases.rowid").fetchall()
 assert len(sql)==len(cases)
 for name,result,duration in sql:
  node=next(x for x in cases if x["name"]==name)
  assert result=="Failure" and duration==node["durationInSeconds"]
 count=c.execute("select count(*) from Attachments").fetchone()[0]
 c.close()
 log=(R/(stage+".log")).read_text()
 starts=re.findall(r"Test Case '-\[PinkhaAnyNativeUITests.NativeLaunchTests ([A-Za-z0-9_]+)\]' started\.",log)
 assert len(starts)==len(names) and {"NativeLaunchTests/"+x for x in starts}==set(names)
 assert not re.search(r"Test Case .* passed \(",log)
 records=[{"method":x["nodeIdentifier"],"result":x["result"],"duration_seconds":x["durationInSeconds"],"failure_children":[z for z in x.get("children",[]) if z.get("nodeType")=="Failure Message"]} for x in cases]
 stages.append({"stage":stage,"methods":records,"summary_sha256":h((R/(stage+"-test-counts.json")).read_bytes()),"test_tree_sha256":h((R/(stage+"-test-methods.json")).read_bytes()),"raw_log_sha256":h((R/(stage+".log")).read_bytes()),"sqlite_sha256":h(db.read_bytes()),"attachment_count":count,"command_exit":65,"actual_starts":len(starts),"actual_passes":0})
 current_names.extend(names)
retained=ad["retainedProof"]
assert retained["retainedMethodCount"]==22 and retained["retainedMethodsExecutedThisRun"]==0
assert set(current_names).isdisjoint(retained["retainedMethodsWithOrigins"])
for stage in ("custom-type","native-history"):
 assert not (R/(stage+".xcresult")).exists() and not (R/(stage+"-command-exit.json")).exists()
cleanup=read(R/"native-ui-original-simulator-cleanup.json")
assert cleanup["status"]=="OWNED_SIMULATOR_REMOVAL_OBSERVED" and cleanup["absenceProof"] is True and cleanup["ownedSimulatorUDID"]==UDID
afterdev=read(R/"native-ui-original-commands/cleanup/devices-after.stdout")
device_rows=[x for values in afterdev["devices"].values() for x in values]
assert all(x["udid"]!=UDID for x in device_rows) and len(device_rows)==cleanup["absenceObservation"]["enumeratedDeviceCount"]
for action in ("shutdown","delete"):
 row=read(R/("native-ui-original-commands/cleanup/"+action+".json"))
 assert row["command"]==["xcrun","simctl",action,UDID] and row["returncode"]==0
created=(R/"native-ui-original-commands/create/create.stdout").read_text().strip()
assert created==UDID
beforedev=read(R/"native-ui-original-commands/create/devices-before.stdout")
assert all(x["udid"]!=UDID for vals in beforedev["devices"].values() for x in vals)
final=read(R/"final-products-check.json")
assert final["status"]=="UNCHANGED_ORIGINAL_PRODUCTS_CONTROL_AND_APP" and final["controlCommit"]==CONTROL and final["applicationCommit"]==APP
assert final["admissionSHA256"]==h((R/"native-ui-original-products-admission.json").read_bytes())
assert final["originalFiles"]==216 and final["copiedDescriptorSHA256"]==ad["copiedDescriptor"]["sha256"] and final["currentBuilds"]==0
provider=read(R/"hanlin-provider/provider-contract.json");stop=read(R/"hanlin-provider/server-start.json")
assert provider["phase"]==provider["providerRequests"]==provider["responsesDelivered"]==0 and provider["state"]=="awaiting_scenario"
assert provider["scenarioSHA256"] is None and provider["requestMetadata"]==[] and provider["rejections"]=={} and not provider["stopped"]
assert stop["runID"]==provider["runID"] and stop["stopped"] and stop["phase"]==0 and stop["providerRequests"]==0
provider_cleanup=read(R/"hanlin-provider/cleanup.json")
assert provider_cleanup["status"]=="OWNED_FIXTURE_STOPPED_AND_PRIVATE_MATERIAL_REMOVED"
result={"schema":1,"audit_status":"PASS","product_status":"FAIL","run":RUN,"attempt":1,"control_commit":CONTROL,"application_commit":APP,"owned_simulator_udid":UDID,"archive_sha256":ledger["archive_sha256"],"original_file_count_rehashed":3292,"original_uncompressed_bytes":ledger["uncompressed_bytes"],"extracted_inventory_sha256":ledger["extracted_inventory_sha256"],"git_input_bindings":sorted(inputs.values(),key=lambda x:(x["commit"],x["path"])),"git_input_count":len(inputs),"application_protected_git_blobs":len(tree),"application_protected_git_blobs_sha256":canonical(tree),"readiness_before_after_files":sum(len(x["files"]) for x in before["sources"].values()),"readiness_module_bindings":len(before["moduleBindings"]),"original_product_metadata":metadata,"original_command_receipts":commands,"stages":stages,"new_actual_methods":5,"new_passes":0,"new_failures":5,"new_skips":0,"retained_old_methods":22,"retained_old_methods_executed":0,"unexecuted_stages":["custom-type","native-history"],"provider_verification":"FAIL_BEFORE_SCENARIO_PHASE0_REQUESTS0","provider_verify_snapshot_is_distinct_from_shutdown_report":True,"provider_cleanup":"PASS","simulator_cleanup":"PASS_SHUTDOWN0_DELETE0_EXACT_ABSENCE","final_product_integrity":"ORIGINAL_RUNTIME_RECEIPT_PASS_216_FILES_UNCHANGED","product_integrity_limit":"Current runtime Products and copied descriptor are bound by original admission/final receipts; their full current bytes are not included in this result artifact.","no_new_builds":True,"audit_actions":"Read-only original files, SQLite immutable connections, and Git object reads; no imports of product/controller modules and no tests/builds."}
print(json.dumps(result,sort_keys=True))
