import ast,hashlib,json,os,shutil,stat,subprocess
from pathlib import Path
root=Path("/mnt/development/projects/worktrees/anytype-wave15-page-mounted-kernel-20261123")
docs=root/"docs/validation/20261123-semantic-mounted-kernel"
assert shutil.disk_usage("/mnt/development").free>=2500000000
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(root),*a],stderr=subprocess.PIPE,timeout=30)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name):return json.loads((docs/name).read_bytes())
bb="bb046d988d57bf5f530f71b8b86588b21ab7ded2"
old="410ead0fa664e8204f0f4f70f1ed784ca870efa0"
qualified="75bd6d7af18dfd511e85582ce7f994d2801b7703"
m=load("control-inputs.json");review=load("composition-source-review.json")
prior_modes=load("source-preflight.json")["files"]
copy_receipt=load("composition-baseline-copy.json")
assert copy_receipt["baseline_only_commit"]=="114e277eda54f3cad7eae43a93cb45c7bd1a6d99" and copy_receipt["tests_run"]==0
assert m["protocol"]=="pinkha-page154-mounted-kernel-control-inputs-v2"
assert len(m["files"])==35 and m["unchanged_original_eager_modules"]==29
assert m["unexecuted_pre_alignment_source"]==old
assert m["selected_methods"]==["test_actual_mounted_consumer_keeps_owned_kernel_deadline_and_first_error"]
assert m["composed_inputs"]==review["fixed_composed_inputs"]
parent=git("rev-parse","HEAD").decode().strip()
assert git("rev-parse","HEAD^").decode().strip()==old
assert sorted(git("diff","--name-only",old,parent).decode().splitlines())==sorted(m["composed_inputs"])
allowed={"Tools/PinkhaSimulatorGate/run_owned_single_lane.py","Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_kernel_quiescence.py",*m["composed_inputs"]}
changed=git("diff","--name-only",bb,"--").decode().splitlines()
assert all(p in allowed or p.startswith("docs/validation/20261123-semantic-mounted-kernel/") for p in changed)
index={}
for v in git("ls-files","--stage","-z").split(b"\0"):
 if not v:continue
 lhs,p=v.split(b"\t",1);mode,oid,stage=lhs.decode().split()
 assert stage=="0"
 index[p.decode()]={"mode":mode,"blob":oid}
rows={}
for p,e in m["files"].items():
 f=root/p;assert f.resolve()==f and f.is_file() and not f.is_symlink()
 b=f.read_bytes();info=f.stat();row={"sha256":sha(b),"bytes":len(b),"mode":stat.S_IMODE(info.st_mode),"git_blob":index[p]["blob"],"git_mode":index[p]["mode"]}
 assert row["sha256"]==e["sha256"] and row["bytes"]==e["bytes"]
 expected_mode=prior_modes[p]["mode"] if p in prior_modes else copy_receipt["copied"][p]["mode"]
 assert index[p]["mode"]=="100644" and row["mode"]==expected_mode==0o664
 assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==index[p]["blob"]
 assert git("show",":"+p)==b
 ast.parse(b,filename=p)
 if p in m["composed_inputs"]:
  origin,revision,h=m["composed_inputs"][p]
  assert e["origin"]==origin and sha(b)==h and git("show",revision+":"+p)==b
  row["exact_origin_commit"]=revision
 elif e["origin"]=="bb046":
  assert git("show",bb+":"+p)==b
  row["exact_origin_commit"]=bb
 else:assert e["origin"] in ("new_control","new_semantic_profile_over_75bd")
 rows[p]=row
supervisor="Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
s=(root/supervisor).read_bytes()
before=b'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE):'
after=b'if cleanup_profile in ("sdk06-enumeration", "sdk06-qualified", owned.COHERENT_HEART_PROFILE, "semantic-page154"):'
assert s.count(after)==1 and before not in s
assert s.replace(after,before,1)==git("show",qualified+":"+supervisor)
t=ast.parse(s);node=next(x for x in t.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name=="_sdk06_kernel_group_observation")
kernel=b"".join(s.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
assert len(kernel)==1665 and sha(kernel)=="d581843c94632933612d54d46036eb777ac15b154c13088cce90a0e7fced325a"
wrapper=(docs/"run_control.py").read_text();projection=wrapper
for h in reversed(review["wrapper_admission_hunks"]):
 assert projection.count(h["after"])==1
 projection=projection.replace(h["after"],h["before"],1)
assert projection.encode()==git("show",old+":docs/validation/20261123-semantic-mounted-kernel/run_control.py")
test="Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_kernel_quiescence.py"
assert (root/test).read_bytes()==git("show",old+":"+test)
assert sha((root/test).read_bytes())=="f8150ef073a21f67a7b8b08f4ffb0611855269a5d275fbaae077f7a743cdc642"
methods=[n.name for cls in ast.parse((root/test).read_bytes()).body if isinstance(cls,ast.ClassDef) and cls.name=="MountedPageKernelCompositionTests" for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")]
assert methods==m["selected_methods"]
assert (docs/"source-review.json").read_bytes()==git("show",old+":docs/validation/20261123-semantic-mounted-kernel/source-review.json")
assert (docs/"source-preflight.json").read_bytes()==git("show",old+":docs/validation/20261123-semantic-mounted-kernel/source-preflight.json")
assert review["current_manifest_sha256"]==sha((docs/"control-inputs.json").read_bytes())
assert review["current_wrapper_sha256"]==sha((docs/"run_control.py").read_bytes())
assert review["preflight_reader_sha256"]==sha(Path(__file__).read_bytes())
assert git("show",":docs/validation/20261123-semantic-mounted-kernel/composition-preflight-reader.py")==Path(__file__).read_bytes()
origins={}
for e in m["files"].values():origins[e["origin"]]=origins.get(e["origin"],0)+1
assert origins=={"bb046":29,"main9cafd":2,"new_control":2,"new_semantic_profile_over_75bd":1,"release6acab":1}
assert not Path("/mnt/development/projects/evidence/semantic-mounted-kernel-20261123/attempt1").exists()
receipt={"protocol":"pinkha-page154-kernel-composition-preflight-v1","status":"PASS_STATIC_SOURCE_FREEZE_NO_IMPORT_OR_TEST","source_parent_baseline_only":parent,"baseline_only_copy_commit_excluded_from_main":True,"prior_unexecuted_source":old,"prior_control_methods_executed":0,"declared_inputs":rows,"input_origin_counts":origins,"manifest_sha256":sha((docs/"control-inputs.json").read_bytes()),"source_review_sha256":sha((docs/"composition-source-review.json").read_bytes()),"test_sha256":sha((root/test).read_bytes()),"wrapper_sha256":sha((docs/"run_control.py").read_bytes()),"preflight_reader_sha256":sha(Path(__file__).read_bytes()),"whole_wrapper_six_hunk_inverse_to_old":True,"supervisor_whole_inverse_to_75bd":True,"unchanged_kernel_source_slice":{"bytes":len(kernel),"sha256":sha(kernel)},"exact_same_one_method":methods,"prior_source_review_and_preflight_preserved":True,"all_other_Page_App_Module_sources_unchanged":True,"actual_control_methods":0,"actual_native_or_product_methods":0,"imports_of_repository_modules":0,"full_Page_acceptance":"NOT_RUN","free_bytes":shutil.disk_usage("/mnt/development").free}
assert receipt["free_bytes"]>=2500000000
out=docs/"composition-preflight.json"
with out.open("xb") as stream:stream.write((json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode())
print(json.dumps({"status":receipt["status"],"declared_inputs":len(rows),"receipt":str(out),"sha256":sha(out.read_bytes()),"bytes":out.stat().st_size,"free_bytes":receipt["free_bytes"]}))
