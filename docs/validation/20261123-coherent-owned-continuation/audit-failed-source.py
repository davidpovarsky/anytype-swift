from pathlib import Path
import ast,json,hashlib,subprocess,difflib
w=Path("/mnt/development/projects/worktrees/anytype-wave15-coherent-owned-continuation-20261123")
here=w/"docs/validation/20261123-coherent-owned-continuation"
source="ad05ea15beb10b98feb74ab5ec705e18535fa8ba"
original="3a6f932925a7cadd37490b91eed59c27f58da446"
name="Tools/PinkhaSimulatorGate/test_coherent_owned_continuation.py"
digest=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *args:subprocess.check_output(["git","-C",str(w),*args],timeout=30)
old=git("show",original+":"+name).decode()
new=(w/name).read_text()
assert git("diff","--name-only",original,source,"--","Tools").decode().splitlines()==[name]
reverse=new.replace('self.assertRaises(RuntimeError if case in {"changed_intent", "changed_admission"} else ValueError)',"self.assertRaises(ValueError)")
needle="self.assertRaises(RuntimeError):\n                        origin._preload_cleanup_sources()"
assert reverse.count(needle)==1
reverse=reverse.replace(needle,"self.assertRaises(ValueError):\n                        origin._preload_cleanup_sources()")
assert reverse==old
def methods(text):
 return {n.name:ast.get_source_segment(text,n) for n in ast.walk(ast.parse(text))
         if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")}
a,b=methods(old),methods(new)
failed="test_cleanup_snapshot_checks_live_bytes_closure_and_intent_without_git"
assert set(a)==set(b) and [k for k in a if a[k]!=b[k]]==[failed]
plan=json.loads((here/"control-inputs.json").read_bytes())
inputs={}
for path,wanted in plan["inputs"].items():
 raw=(w/path).read_bytes()
 assert raw==git("show",source+":"+path)
 row=dict(wanted,sha256=digest(raw),bytes=len(raw))
 entry=git("ls-tree","-z",source,"--",path).rstrip(b"\0")
 meta,actual=entry.split(b"\t",1)
 mode,kind,blob=meta.decode().split()
 assert actual.decode()==path and kind=="blob"
 row.update(mode=mode,blob=blob)
 if path!=name:assert row==wanted
 inputs[path]=row
seal_path=here/"attempt1-originals/seal.json"
seal=json.loads(seal_path.read_bytes())
for relative,row in seal["originals"].items():
 p=here/"attempt1-originals"/relative
 q=Path(row["original_path"])
 assert p.is_file() and not p.is_symlink() and q.is_file() and not q.is_symlink()
 assert p.read_bytes()==q.read_bytes() and digest(p.read_bytes())==row["sha256"] and p.stat().st_size==row["bytes"]
root=here/"attempt1-originals/attempt1"
receipt=json.loads((root/"execution.json").read_bytes())
before=json.loads((root/"source-before.json").read_bytes())
assert (root/"source-before.json").read_bytes()==(root/"source-after.json").read_bytes()
assert len(before["files"])==70
for path,row in before["files"].items():
 raw=git("show","9abf690fd418f042313ee627029ed862715b22a5:"+path)
 assert digest(raw)==row["sha256"] and len(raw)==row["bytes"]
events=[json.loads(line) for line in (root/"events.jsonl").read_text().splitlines()]
assert receipt["status"]=="FAIL" and receipt["errors"]==5 and receipt["failures"]==0 and receipt["skipped"]==0
starts=[r["test"] for r in events if r["action"]=="start"]
passes=[r["test"] for r in events if r["action"]=="pass"]
failures=[r for r in events if r["action"]=="subtest-fail"]
assert len(starts)==4 and starts[:3]==passes and len(failures)==5
assert all(row["test"]==starts[-1] and row["error_type"]=="RuntimeError" for row in failures)
for stem in ("loaded-before","loaded-after"):
 loaded=json.loads((root/(stem+".json")).read_bytes())
 for module,row in loaded.items():
  assert before["files"][row["path"]]["sha256"]==row["sha256"]
report=dict(protocol="pinkha-coherent-failed-method-only-review-v1",
 source_commit=source, original_source_commit=original, original_controller_commit="9abf690fd418f042313ee627029ed862715b22a5",
 original_seal_commit="d322886d287a903170b3fd6d985e0646b3ee4c88",
 original_seal_sha256=digest(seal_path.read_bytes()),
 original_execution_sha256=digest((root/"execution.json").read_bytes()),
 original_status=receipt["status"], original_source_rows_verified=70, original_artifacts_verified=len(seal["originals"]),
 old_wrapper_sha256=digest((here/"run-controls.py").read_bytes()), original_wrapper_modified=False,
 product_source_delta=False, code_delta_paths=[name],
 original_test_sha256=digest(old.encode()), corrected_test_sha256=digest(new.encode()),
 exact_whole_file_inverse=True, assertion_expressions_changed=2, affected_exception_expectations=5,
 failed_scopes=[row["subtest"] for row in failures],
 expected_exception_changes={key:{"from":"ValueError","to":"RuntimeError"} for key in
  ("initial_foreign_required_module:coherent_original_products",
   "initial_foreign_required_module:coherent_cleanup_snapshot",
   "initial_foreign_required_module:coherent_heart_release","changed_intent","changed_admission")},
 retained_method_source_sha256={key:digest(a[key].encode()) for key in a if key!=failed},
 retained_named_original_passes=passes,
 selected_new_execution=["CoherentOwnedContinuationTests."+failed], execution_status="NOT_RUN",
 original_tracebacks_path="attempt1-originals/attempt1/original.stderr",
 original_tracebacks_sha256=digest((root/"original.stderr").read_bytes()),
 limitations=["Original attempt1 remains FAIL","Three original passed methods are retained, not selected again",
              "Positive fourth-method subcases from attempt1 are not a complete fourth-method PASS",
              "No product, native, simulator or old suite execution"],inputs=inputs)

old_runner=(here/"run-controls.py").read_text()
new_runner=(here/"run-failed-cleanup-control.py").read_text()
assert digest(old_runner.encode())=="36964117af425caf65a8216d5143871f6de40b3942622833c34909d2c1bce916"
assert digest(new_runner.encode())=="d2d2cb874a83bfb54efe9c9a519c47cb93e96e8027027a99c93af90eb4b8b590"
rt=ast.parse(new_runner)
selected=next(ast.literal_eval(n.value) for n in rt.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=="TESTS" for t in n.targets))
selected_source=next(ast.literal_eval(n.value) for n in rt.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=="SOURCE" for t in n.targets))
assert selected==tuple(report["selected_new_execution"]) and selected_source==source
def funcs(text):
 result={}
 def walk(node,prefix=""):
  for child in node.body:
   if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
    result[prefix+child.name]=ast.dump(child,include_attributes=False)
   if isinstance(child,ast.ClassDef):walk(child,prefix+child.name+".")
 walk(ast.parse(text))
 return result
fa,fb=funcs(old_runner),funcs(new_runner)
assert set(fa)==set(fb)
changed=[name for name in fa if fa[name]!=fb[name]]
assert set(changed)=={"observe_sources","main"}
left,right=old_runner.splitlines(keepends=True),new_runner.splitlines(keepends=True)
back=list(right);hunks=[]
for tag,i,j,k,l in reversed(list(difflib.SequenceMatcher(a=left,b=right,autojunk=False).get_opcodes())):
 if tag=="equal":continue
 before,after="".join(left[i:j]),"".join(right[k:l])
 hunks.append({"original_lines":[i,j],"failed_only_lines":[k,l],
               "original_sha256":digest(before.encode()),"failed_only_sha256":digest(after.encode())})
 back[k:l]=left[i:j]
assert "".join(back)==old_runner
report["failed_only_wrapper"]={"sha256":digest(new_runner.encode()),"bytes":len(new_runner.encode()),
 "original_wrapper_sha256":digest(old_runner.encode()),"exact_whole_file_inverse":True,
 "unchanged_function_count":sum(fa[k]==fb[k] for k in fa),
 "changed_functions":changed,"inverse_hunks":list(reversed(hunks)),
 "patch":"".join(difflib.unified_diff(left,right,fromfile="original-four-method-wrapper",tofile="failed-only-wrapper"))}

print(json.dumps(report,sort_keys=True))
