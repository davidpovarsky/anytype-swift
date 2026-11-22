import pathlib,shutil,json,hashlib,re
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-unsplash-init-20261122")
failure=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-44997870962-failure")
observer=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-44997870962-observation")
proof=out/"evidence-ready";assert not proof.exists();proof.mkdir()
f=proof/"failed-568d";f.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
archive=failure/"github-artifact-14745480195.zip"
assert archive.stat().st_size==1430729 and sha(archive.read_bytes())=="97915d84057d876394844cd4e53f557d3e77d726dc38633e85a0903f9fa66215"
for name in ["github-artifact-14745480195.zip","ARTIFACT_RECEIPT.json"]:shutil.copyfile(failure/name,f/name)
for name in ["execution.json","framework-build.command.json","source-before.json","source-after.json","source-admission.json","source-controls-result.json","macro-trust/macro-approval.json","macro-trust/macro-restoration.json","macro-trust/owned-trust-state.json","owned-simulator-cleanup.json"]:
 dest=f/"selected"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(failure/"inner-0"/name,dest)
for name in ["OBSERVER_STARTED.json","SUMMARY.json","terminal-run.json","terminal-jobs.json","terminal-artifacts.json"]:
 dest=f/"observer"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(observer/name,dest)
command=json.loads((failure/"inner-0/framework-build.command.json").read_bytes())
execution=json.loads((failure/"inner-0/execution.json").read_bytes())
controls=json.loads((failure/"inner-0/source-controls-result.json").read_bytes())
restoration=json.loads((failure/"inner-0/macro-trust/macro-restoration.json").read_bytes())
lines=(failure/"inner-0/framework-build.stdout.log").read_text(encoding="utf-8",errors="replace").splitlines()
errors=[{"line":i+1,"diagnostic":line,"context":lines[max(0,i-2):i+15]} for i,line in enumerate(lines) if re.search(r"\.swift:\d+:\d+: error:",line)]
unlocated=[{"line":i+1,"diagnostic":line} for i,line in enumerate(lines) if "Internal Error: DecodingError" in line]
assert len(errors)==1 and "UnsplashItemsViewModel.swift:33:30" in errors[0]["diagnostic"]
assert len(unlocated)==1
assert command["returncode"]==65 and not command["timed_out"]
assert controls["status"]=="PASS_SOURCE_CONTROLS_221" and controls["tests_run"]==221
assert (failure/"inner-0/source-before.json").read_bytes()==(failure/"inner-0/source-after.json").read_bytes()
assert restoration["status"]=="EXACT_ORIGINAL_MACRO_TRUST_RESTORED"
diagnosis={"schema":1,"run":44997870962,"attempt":1,"head":"568d69f55a4b1b1bc318b8ee20144c720c8c16a5","source_checkpoint":"955c082bdd559050da38413f60897fcea876d8c4","phase":execution["phase"],"actual_framework_command_attempted":True,"semantic_framework_build_completed":False,"external_consumer_executed":False,"native_editor_ui_tests":execution["native_editor_ui_tests"],"framework_command":command,"unique_source_diagnostics":errors,"unlocated_driver_diagnostics":unlocated,"unlocated_driver_cause":"Unattributed; no source-specific cause inferred.","source_controls_status":controls["status"],"source_controls_tests_run":controls["tests_run"],"macro_trust_restored":restoration["status"],"source_before_after_bytes_equal":True,"download_count":1,"outer_archive_sha256":sha(archive.read_bytes())}
(f/"FAILURE_DIAGNOSIS.json").write_text(json.dumps(diagnosis,indent=2)+"\n",encoding="utf-8")
(proof/".gitattributes").write_bytes(b"* -text\n")
(out/"retain_failed_producer.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({"status":"FAILED_568D_EVIDENCE_RETAINED","path":str(f),"files":sum(p.is_file() for p in f.rglob("*")),"diagnosis_sha256":sha((f/"FAILURE_DIAGNOSIS.json").read_bytes()),"source_diagnostics":len(errors),"unlocated_driver_diagnostics":len(unlocated),"native_tests":execution["native_editor_ui_tests"]}))
