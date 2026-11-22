import pathlib,json,hashlib,shutil,difflib,datetime
old=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-20261122")
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-v2-20261122")
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,data):path.write_bytes(data.encode() if isinstance(data,str) else data)
def rec(path):
 data=(out/path).read_bytes();return {"path":path,"sha256":sha(data),"bytes":len(data)}
assert sha((old/"INPUTS.json").read_bytes())=="b181b4f4af4848bb6864d18e9826cc50bc7c732db9602a675246ff2abf236962"
assert sha((old/"run_controls.py").read_bytes())=="8001e55c0de3546ac46e1026cfe06b431883f11cf1fd54d892532eea8a3f1881"
assert not (old/"EXECUTION.json").exists() and not out.exists()
inputs=json.loads((old/"INPUTS.json").read_bytes())
for item in inputs["compiled_inputs"]:assert sha((old/item["path"]).read_bytes())==item["sha256"]
shutil.copytree(old,out)
manager_path="Tests/SelectedSpaceControls/ActiveSpaceManager.swift"
controls_path="Tests/SelectedSpaceControls/Controls.swift"
manager_before=(out/manager_path).read_text()
controls_before=(out/controls_path).read_text()
field="    private var probeDuplicateStopEntries = 0\n"
bump="            probeDuplicateStopEntries += 1\n"
method="    func probeDuplicateStopEntryCount() -> Int { probeDuplicateStopEntries }\n"
anchor="    private var stopOperation: Task<Void, Never>?\n"
assert manager_before.count(anchor)==1
manager=manager_before.replace(anchor,anchor+field)
anchor="        if let stopOperation {\n            await stopOperation.value\n"
assert manager.count(anchor)==1
manager=manager.replace(anchor,"        if let stopOperation {\n"+bump+"            await stopOperation.value\n")
anchor="extension ActiveSpaceManager {\n"
assert manager.count(anchor)==1
manager=manager.replace(anchor,anchor+method)
assert manager.replace(field,"").replace(bump,"").replace(method,"")==manager_before
controls_anchor="        let secondStop = Task { await manager.stopSubscription() }\n"
controls_insert="        try await selectionWait { await manager.probeDuplicateStopEntryCount() == 1 }\n"
assert controls_before.count(controls_anchor)==1
controls=controls_before.replace(controls_anchor,controls_anchor+controls_insert)
assert controls.replace(controls_insert,"")==controls_before
write(out/manager_path,manager)
write(out/controls_path,controls)
readouts=(out/"ManagerReadouts.swift.txt").read_text()
readouts=readouts.replace("extension ActiveSpaceManager {\n","extension ActiveSpaceManager {\n"+method)
write(out/"ManagerReadouts.swift.txt",readouts)
canonical=(out/"product-inputs/CANDIDATE_CANONICAL.swift").read_text()
projected=canonical
for module in ("AnytypeCore","Services","AsyncTools","ProtobufMessages"):projected=projected.replace("import "+module+"\n","")
assert manager.endswith(readouts)
recovered=manager[:-len(readouts)].replace(field,"").replace(bump,"")
assert recovered==projected
mapping=json.loads((out/"PROJECTIONS.json").read_bytes())
mapping["manager"].pop("full_body_unchanged")
mapping["manager"]["product_body_after_removing_explicit_fixture_observations_is_unchanged"]=True
mapping["manager"]["appended_readonly_accessor"]=rec("ManagerReadouts.swift.txt")
mapping["manager"]["fixture_counter_instrumentation"]={
 "field_insertion":field,"branch_insertion":bump,
 "exact_branch":"if let stopOperation; immediately before unchanged await stopOperation.value",
 "purpose":"Positive observation of actual duplicate-stop branch entry before releasing the first held clear; no scheduling/yield assumption",
 "inverse_recovers_full_canonical_manager_after_restoring_only_original_imports":True,
 "canonical_sha256":sha(canonical.encode()),"product_source_changed":False
}
write(out/"PROJECTIONS.json",json.dumps(mapping,indent=2)+"\n")
write(out/"prepare_v2_controls.py",pathlib.Path(__file__).read_bytes())
inputs["schema"]="original-selected-space-controls/v2"
inputs["prepared_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
inputs["previous_unexecuted_inputs_sha256"]=sha((old/"INPUTS.json").read_bytes())
inputs["compiled_inputs"]=[rec(x["path"]) for x in inputs["compiled_inputs"]]
inputs["projection_map"]=rec("PROJECTIONS.json")
inputs["fixture_revision"]=rec("prepare_v2_controls.py")
inputs["limits"][1]="Complete reviewed manager source, excluding four external imports, appending five read-only fixture accessors and inserting one fixture-only duplicate-stop observation counter before the unchanged original await. Removing that field/increment/accessor and restoring imports recovers the complete canonical product. Product candidates are not applied."
write(out/"INPUTS.json",json.dumps(inputs,indent=2)+"\n")
runner_before=(old/"run_controls.py").read_text()
runner=runner_before.replace(str(old),str(out)).replace(
 "b181b4f4af4848bb6864d18e9826cc50bc7c732db9602a675246ff2abf236962",sha((out/"INPUTS.json").read_bytes())
).replace('for key in ("package","projection_map","preparation"):','for key in ("package","projection_map","preparation","fixture_revision"):')
write(out/"run_controls.py",runner)
diff=""
for path,before,after in [(manager_path,manager_before,manager),(controls_path,controls_before,controls),("run_controls.py",runner_before,runner)]:
 diff+="".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="v1/"+path,tofile="v2/"+path))
write(out/"V1_TO_V2.patch",diff)
binding={"status":"FROZEN_V2_NO_EXECUTION","directory":str(out),"input_sha256":sha((out/"INPUTS.json").read_bytes()),
 "runner":rec("run_controls.py"),"delta":rec("V1_TO_V2.patch"),"projection":rec("PROJECTIONS.json"),
 "expected_groups":10,"changed_compiled_inputs":[manager_path,controls_path],
 "unchanged_compiled_inputs":15,"previous_unexecuted_directory":str(old),
 "old_inputs_sha256":sha((old/"INPUTS.json").read_bytes()),"old_runner_sha256":sha((old/"run_controls.py").read_bytes()),
 "full_canonical_inverse":True,"product_applied":False,"controls_executed":0}
write(out/"RUNNER_BINDING.json",json.dumps(binding,indent=2)+"\n")
print(json.dumps(binding))
