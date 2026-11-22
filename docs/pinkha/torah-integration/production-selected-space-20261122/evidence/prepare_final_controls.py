import pathlib,json,hashlib,shutil,difflib,datetime,re
v1=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-20261122")
partial=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-v2-20261122")
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-selected-final-20261122")
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,data):path.write_bytes(data.encode() if isinstance(data,str) else data)
def rec(path):
 data=(out/path).read_bytes();return {"path":path,"sha256":sha(data),"bytes":len(data)}
assert sha((v1/"INPUTS.json").read_bytes())=="b181b4f4af4848bb6864d18e9826cc50bc7c732db9602a675246ff2abf236962"
assert sha((partial/"INPUTS.json").read_bytes())=="c7a3b40b7a5a5e8daa904d6f4c07dbb7208d4e517c43d8603fab66483353e9af"
assert sha((partial/"run_controls.py").read_bytes())=="a01f4224978ab7f7647c9953b3b18505b3d11becdc06948c92cbd15a0ed022d6"
assert not (v1/"EXECUTION.json").exists() and not (partial/"EXECUTION.json").exists() and not out.exists()
inputs=json.loads((partial/"INPUTS.json").read_bytes())
for item in inputs["compiled_inputs"]:assert sha((partial/item["path"]).read_bytes())==item["sha256"]
shutil.copytree(partial,out)
probe_path="Tests/SelectedSpaceControls/SelectionDependencyProbes.swift"
controls_path="Tests/SelectedSpaceControls/Controls.swift"
probe=(out/probe_path).read_text()
needle="    case nativePauseTimedOut, conditionTimedOut, missingManager\n"
assert probe.count(needle)==1
probe=probe.replace(needle,needle+"    case recordedAssertions([String])\n")
needle="        ProbeRegistry.assertions.value = []\n"
assert probe.count(needle)==1;probe=probe.replace(needle,"")
needle="    func stop() async {\n        releaseAll()\n        await manager?.stopSubscription()\n        await spaces.stopSubscription()\n    }\n"
assert probe.count(needle)==1
replacement="    func stop() async throws {\n        releaseAll()\n        await manager?.stopSubscription()\n        await spaces.stopSubscription()\n        let assertions = ProbeRegistry.assertions.value\n        guard assertions.isEmpty else { throw SelectionProbeError.recordedAssertions(assertions) }\n    }\n"
probe=probe.replace(needle,replacement)
write(out/probe_path,probe)
controls=(out/controls_path).read_text()
controls,count=re.subn(r"(?<!try )await (fixture|rejected|foreign)\.stop\(\)",r"try await \1.stop()",controls)
assert count==13,count
assert len(re.findall(r"try await (?:fixture|rejected|foreign)\.stop\(\)",controls))==13
assert not re.search(r"(?<!try )await (?:fixture|rejected|foreign)\.stop\(\)",controls)
write(out/controls_path,controls)
mapping=json.loads((out/"PROJECTIONS.json").read_bytes())
mapping["selection_probes"].append("Successful fixture cleanup throws if any recorded assertion exists after manager/Space teardown; no fixture resets the shared assertion list. All13 successful cleanup sites use try await.")
write(out/"PROJECTIONS.json",json.dumps(mapping,indent=2)+"\n")
write(out/"prepare_final_controls.py",pathlib.Path(__file__).read_bytes())
inputs["prepared_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
inputs["superseded_unexecuted_v2_inputs_sha256"]=sha((partial/"INPUTS.json").read_bytes())
inputs["compiled_inputs"]=[rec(x["path"]) for x in inputs["compiled_inputs"]]
inputs["projection_map"]=rec("PROJECTIONS.json")
inputs["fixture_revision"]=rec("prepare_final_controls.py")
inputs["limits"].append("Every successful fixture cleanup checks all recorded assertion/hold-timeout errors after actual owned teardown. No per-fixture reset can erase them.")
write(out/"INPUTS.json",json.dumps(inputs,indent=2)+"\n")
runner=(partial/"run_controls.py").read_text()
runner=runner.replace(str(partial),str(out)).replace("c7a3b40b7a5a5e8daa904d6f4c07dbb7208d4e517c43d8603fab66483353e9af",sha((out/"INPUTS.json").read_bytes()))
write(out/"run_controls.py",runner)
changed=["Tests/SelectedSpaceControls/ActiveSpaceManager.swift",controls_path,probe_path,"run_controls.py","PROJECTIONS.json"]
diff=""
for path in changed:
 before=(v1/path).read_text();after=(out/path).read_text()
 diff+="".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="v1/"+path,tofile="final-v2/"+path))
write(out/"V1_TO_FINAL_V2.patch",diff)
binding={"status":"FROZEN_FINAL_V2_NO_EXECUTION","directory":str(out),
 "input_sha256":sha((out/"INPUTS.json").read_bytes()),"runner":rec("run_controls.py"),
 "delta":rec("V1_TO_FINAL_V2.patch"),"projection":rec("PROJECTIONS.json"),
 "compiled_inputs":17,"changed_compiled_inputs":3,"unchanged_compiled_inputs":14,
 "expected_groups":10,"successful_cleanup_checks":count,
 "original_unexecuted_directory":str(v1),"counter_only_unexecuted_directory":str(partial),
 "product_candidates":[{"path":x["product_path"],"sha256":x["canonical_sha256"]} for x in inputs["product_candidates"]],
 "product_applied":False,"controls_executed":0}
write(out/"RUNNER_BINDING.json",json.dumps(binding,indent=2)+"\n")
print(json.dumps(binding))
