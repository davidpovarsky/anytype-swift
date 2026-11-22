import pathlib,json,hashlib,copy,re
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-textblock-existential-20261122")
def sha(b):return hashlib.sha256(b).hexdigest()
assert not (out/"SEMANTIC_INPUTS_V2.json").exists()
first=json.loads((out/"SEMANTIC_INPUTS.json").read_bytes())
assert sha((out/"SEMANTIC_INPUTS.json").read_bytes())=="bf5027b52cf4947b7a700fa2b6a70a13fb08ee1df143ba197307ec74fc38a297"
for row in first["compiled_inputs"]:assert sha((out/row["path"]).read_bytes())==row["sha256"]
p=out/"semantic-package/Tests/CutBoundary/OriginalCutHandlers.swift"
old=p.read_bytes();new=old
v2=json.loads((out/"V2_CANDIDATE_PROVENANCE.json").read_bytes())
def fn(text,token):
 s=text.index(token);br=text.index("{",s);depth=1;i=br+1
 while depth:
  depth += (text[i]=="{")-(text[i]=="}");i+=1
 return text[s:i]
for i,row in enumerate(v2["candidates"]):
 former=out/first["original_inputs"][i]["candidate_file"]
 original=fn(former.read_text(),"    private func cut(range: NSRange)").encode()
 candidate=fn((out/row["candidate_file"]).read_text(),"    private func cut(range: NSRange)").encode()
 assert new.count(original)==1
 new=new.replace(original,candidate)
assert new!=old
p.write_bytes(new)
inputs=copy.deepcopy(first)
inputs["predecessor_inputs_sha256"]=sha((out/"SEMANTIC_INPUTS.json").read_bytes())
inputs["first_candidate_failure_sha256"]=sha((out/"first-attempt/FAILURE_RESULT.json").read_bytes())
for i,row in enumerate(v2["candidates"]):
 inputs["original_inputs"][i]["candidate_file"]=row["candidate_file"]
 inputs["original_inputs"][i]["candidate_sha256"]=row["candidate_sha256"]
changed=[]
for row in inputs["compiled_inputs"]:
 actual=sha((out/row["path"]).read_bytes())
 if actual!=row["sha256"]:changed.append(row["path"])
 row["sha256"]=actual;row["bytes"]=(out/row["path"]).stat().st_size
assert changed==["semantic-package/Tests/CutBoundary/OriginalCutHandlers.swift"]
ex=json.loads((out/"SEMANTIC_EXECUTION.json").read_bytes())
red=next(x for x in ex["commands"] if x["label"]=="expected-old-cut-error")
assert red["returncode"]==1 and not red["timed_out"] and red["all_inputs_unchanged"]
inputs["preimage_expected_error_reuse"]={"record":red,"errors":json.loads((out/"first-attempt/FAILURE_RESULT.json").read_bytes())["error_lines"]["expected-old-cut-error"],"reexecuted":False}
inputs["changed_compiled_inputs"]=changed
inputs["limits"][0]="Both exact original cut(range:) bodies compile with only the reviewed local guard unwrap of the original weak service inside the same original scheduled closure. Original field types/capture lists, MainActor source/inference and text virtual guard are retained; other handler bodies/initializer/UI are explicit fixture projections."
inputs["limits"][5]="Actual initial old-source compilation reproduced the same existential error at both projected sites. The initial explicit-Void candidate failed the same two errors before any test execution. Exact old expectedRED is reused, not rerun; only the changed V2 handler projection is rebuilt against unchanged fixtures and assertions. Apple attributed only the original text handler; simple-table remains an analogous preventive source correction."
(out/"SEMANTIC_INPUTS_V2.json").write_text(json.dumps(inputs,indent=2)+"\n",encoding="utf-8")
(out/"prepare_v2_semantic_inputs.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({"status":"V2_FROZEN_NOT_EXECUTED","inputs_sha256":sha((out/"SEMANTIC_INPUTS_V2.json").read_bytes()),"only_changed_compiled_input":changed,"new_projection_sha256":sha(new),"old_expected_error_reused":inputs["preimage_expected_error_reuse"],"candidate_sha256":[x["candidate_sha256"] for x in inputs["original_inputs"] if x.get("candidate_sha256")]}))
