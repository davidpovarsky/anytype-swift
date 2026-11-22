import pathlib,hashlib,json,difflib,shutil,datetime,re
d=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-textblock-existential-20261122")
first=d/"first-attempt";assert not first.exists();first.mkdir()
inputs=json.loads((d/"SEMANTIC_INPUTS.json").read_bytes())
execution=json.loads((d/"SEMANTIC_EXECUTION.json").read_bytes())
assert execution["commands"][-1]["returncode"]==1 and not execution["commands"][-1]["timed_out"]
assert execution["commands"][-1]["label"]=="swift-testing-new-cut-boundary"
for name in ["SEMANTIC_INPUTS.json","SEMANTIC_EXECUTION.json","run_cut_controls.py","prepare_semantic_control.py","RED_Handlers.swift","CUT_VOID.patch","SIMPLE_TABLE_CUT_VOID.patch","TextBlockActionHandler.CANDIDATE.swift","SimpleTablesTextBlockActionHandler.CANDIDATE.swift"]:
 shutil.copyfile(d/name,first/name)
for item in inputs["compiled_inputs"]:
 src=d/item["path"];assert hashlib.sha256(src.read_bytes()).hexdigest()==item["sha256"]
 dst=first/"compiled-inputs"/src.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst)
for row in execution["commands"]:
 for stream in ["stdout","stderr"]:
  name=row["label"]+"."+stream+".log";assert hashlib.sha256((d/name).read_bytes()).hexdigest()==row[stream+"_sha256"];shutil.copyfile(d/name,first/name)
errs={}
for label in ["expected-old-cut-error","swift-testing-new-cut-boundary"]:
 lines=(d/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace").splitlines()
 errs[label]=[x for x in lines if re.search(r":\d+:\d+: error:",x)]
assert len(errs["expected-old-cut-error"])==2 and len(errs["swift-testing-new-cut-boundary"])==2
assert all("type 'any BaseDocumentProtocol' cannot conform to 'BaseDocumentProtocol'" in x for vv in errs.values() for x in vv)
record={"status":"INITIAL_EXPLICIT_VOID_CANDIDATE_FAILED_SAME_EXISTENTIAL_BOUNDARY","executed_tests":0,"error_lines":errs,"initial_inputs_sha256":hashlib.sha256((first/"SEMANTIC_INPUTS.json").read_bytes()).hexdigest(),"reuse_scope":"Both original full-file parses and exact old-code expectedRED completed; oldRED is reused without another compiler invocation. Prior candidate parses apply only to the old candidate; the changed new candidate requires new parse. No passing test is replayed.","new_direction":"Guard-unwrapped original weak service inside original scheduled operation before same generic cut, no explicit-Void annotation required."}
(first/"FAILURE_RESULT.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
rows=[]
for base,candidate,path in [
 ("TextBlockActionHandler.BASE.swift","TextBlockActionHandler.V2.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift"),
 ("SimpleTablesTextBlockActionHandler.swift","SimpleTablesTextBlockActionHandler.V2.swift","Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/SimpleTable/Block/TextBlock/SimpleTablesTextBlockActionHandler.swift")
]:
 b=(d/base).read_bytes();start=b.index(b"    private func cut(range: NSRange) {");end=b.index(b"    private func createEmptyBlock()",start);old=b[start:end]
 needle=b"        actionHandler.scheduleMutationTask { [self] in\n            try await pasteboardService?.cut(document: document, blocksIds: [info.id], selectedTextRange: range)\n"
 repl=b"        actionHandler.scheduleMutationTask { [self] in\n            guard let pasteboardService else { return }\n            try await pasteboardService.cut(document: document, blocksIds: [info.id], selectedTextRange: range)\n"
 assert old.count(needle)==1
 new=old.replace(needle,repl);c=b.replace(old,new)
 (d/candidate).write_bytes(c)
 patch="".join(difflib.unified_diff(b.decode().splitlines(keepends=True),c.decode().splitlines(keepends=True),fromfile="a/"+path,tofile="b/"+path)).encode()
 pf=candidate.removesuffix(".swift")+".patch";(d/pf).write_bytes(patch)
 rows.append({"path":path,"base_file":base,"candidate_file":candidate,"base_sha256":hashlib.sha256(b).hexdigest(),"candidate_sha256":hashlib.sha256(c).hexdigest(),"patch_file":pf,"patch_sha256":hashlib.sha256(patch).hexdigest(),"patch":patch.decode(),"inverse_verified":c.replace(new,old)==b})
provenance={"schema":1,"head":"d8416b161ba7af42e8459d612a94f7591470513e","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"candidates":rows,"prior_failure_sha256":hashlib.sha256((first/"FAILURE_RESULT.json").read_bytes()).hexdigest(),"only_execution_time_original_weak_service_unwrap":True,"product_worktree_not_modified":True}
(d/"V2_CANDIDATE_PROVENANCE.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf-8")
(d/"prepare_v2_candidates.py").write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({"first_failure":record,"candidate":provenance},ensure_ascii=False))
