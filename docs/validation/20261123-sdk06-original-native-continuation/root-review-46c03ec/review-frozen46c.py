import pathlib,subprocess,json,hashlib,ast,stat,os
R=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-original-native-20261123")
D=pathlib.Path("/mnt/development/projects/diagnostics/sdk06-original-native-root-review-20261123")
N="docs/validation/20261123-sdk06-original-native-continuation/"
HEAD="46c03ec8692bee4ffe6304b041a4a4425d08e2dc";BASE="26b61bbee7dac17339a90111602c7ec83c7844e4"
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(ref,n):return subprocess.check_output(["git","-C",str(R),"show",ref+":"+n],timeout=30)
assert subprocess.check_output(["git","-C",str(R),"rev-parse","HEAD"],text=True).strip()==HEAD
assert not subprocess.check_output(["git","--no-optional-locks","-C",str(R),"status","--porcelain"])
inputs=json.loads(blob(HEAD,N+"control-inputs.json"));review=json.loads(blob(HEAD,N+"source-review.json"))
assert len(inputs["inputs"])==100 and inputs["methods"]==review["authored_methods"] and len(inputs["methods"])==3
verified=[]
for n,row in inputs["inputs"].items():
 b=blob(HEAD,n);p=R/n
 assert p.read_bytes()==b and len(b)==row["bytes"] and sha(b)==row["sha256"]
 mode=subprocess.check_output(["git","-C",str(R),"ls-tree",HEAD,"--",n],text=True).split()[0]
 assert mode==row["git_mode"] and bool(p.stat().st_mode&0o111)==(mode=="100755")
 verified.append({"path":n,"sha256":sha(b),"git_mode":mode})
inverse=json.loads(blob(HEAD,N+"exact-source-inverses.json"))
counts={}
for n,row in inverse["inverses"].items():
 current=blob(HEAD,n);baseline=blob(BASE,n)
 assert sha(current)==row["candidate_sha256"] and sha(baseline)==row["baseline_sha256"]
 text=current.decode()
 for h in reversed(row["hunks"]):
  assert text.count(h["after"])==1
  text=text.replace(h["after"],h["before"],1)
 assert text.encode()==baseline
 counts[n]=len(row["hunks"])
assert counts=={".github/workflows/torah-inspector-ipados27.yml":2,"Tools/PinkhaSimulatorGate/run_wave15_acceptance.py":18,"Tools/PinkhaSimulatorGate/shared_editor_existing_build.py":9}
literal=json.loads(blob(HEAD,N+"selection-copy-inverse.json"))
new=blob(HEAD,literal["new_file"]).decode();old=blob(BASE,literal["path"]).decode()
def fn(s,name):return next(ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==name)
a=fn(new,literal["function"]);b=fn(old,literal["function"])
assert b==literal["original"] and sha(b.encode())==literal["original_function_sha256"]
for h in reversed(literal["hunks"]):
 assert a.count(h["after"])==1
 a=a.replace(h["after"],h["before"],1)
assert a==b and len(literal["hunks"])==3 and blob(HEAD,literal["path"])==blob(BASE,literal["path"])
page="Tools/PinkhaSimulatorGate/run_owned_single_lane.py"
assert blob(HEAD,page)==blob("c0c1f851f80322c9f532e86505047498dfaf1adf",page)
assert sha(blob(HEAD,page))=="5d976901b73b5bc5e519ead3a89952220d8149e710561d92acc9f36e46247414"
source=json.loads(blob(HEAD,"Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"))
assert len(source["inputs"])==78 and len(source["modules"])==67 and len(source["preload_modules"])==64
assert source["preload_modules"]==sorted(x for x in source["modules"] if not x.startswith("test_") and x!="sdk06_original_native_continuation")
for n,expected in source["inputs"].items():
 b=blob(HEAD,n);assert sha(b)==expected["sha256"] and inputs["inputs"][n]["git_mode"]==expected["git_mode"]
proof={N+"original-stream-audit/stream-audit.json":"5fb77b4c59aed70e608cde394e89015508d06110e36495b279b7473831242014",N+"original-stream-audit/entry-map.json.gz":"03dec71655126bba3d266a004eb53c2a61a84f92c23937c4cd08dfd15be573bf",N+"original-stream-audit/seal.json":"4e24beb7fe86a4352275c29b602fda462a311b13f19bd5adc79212502741aa4f"}
for n,h in proof.items():assert sha(blob(HEAD,n))==h
actual_names=[]
for n in ["Tools/PinkhaSimulatorGate/test_sdk06_original_native.py","Tools/PinkhaSimulatorGate/test_sdk06_original_tagged_selector.py"]:
 t=ast.parse(blob(HEAD,n).decode())
 for c in t.body:
  if isinstance(c,ast.ClassDef):
   for m in c.body:
    if isinstance(m,ast.FunctionDef) and m.name.startswith("test_"):actual_names.append(pathlib.Path(n).stem+"/"+c.name+"/"+m.name)
assert sorted(actual_names)==sorted(inputs["methods"])
report={"protocol":"sdk06-original-native-root-source-review-v1","status":"PASS_SOURCE_REVIEW_NEW_CONTROLS_AUTHORIZED","source_sha":HEAD,"baseline":BASE,"verified_fixed_inputs":verified,"exact_existing_file_inverse_hunks":counts,"literal_selection_function_inverse_hunks":3,"unchanged_run_ui27_file":True,"inherited_page_supervisor_exact":True,"reviewed_current_inputs":78,"declared_python_modules":67,"fixed_production_preloads":64,"authorized_new_methods":inputs["methods"],"old_methods_authorized":0,"product_methods_authorized_by_this_review":0,"builds_authorized_by_this_review":0,"original_stream_proof_hashes":proof,"reviewed_scopes":["fixed original75bd/native5011 restoration and original failure","tag-only clone with original target and strict23/excluded7/cases32 qualification","exact finite5 generated descriptors with original-tree union and collision preservation","new UI-only build after pending components/ack/preparation; original App never rebuilt","current-controller pre-import Git/source closure and fixed preload","three new controls in exact frozen wrapper"],"limitations":["No actual current selector enumeration or Apple result is qualified","No original native/archive build is rerun","No native source9 auxiliary frameworks are falsely recreated"],"new_tests_run":0,"old_tests_replayed":0,"review_reader_sha256":sha(pathlib.Path(__file__).read_bytes())}
p=D/"source-review-46c03ec.json";raw=(json.dumps(report,sort_keys=True,indent=2)+"\n").encode()
with p.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
p.chmod(0o400)
print(json.dumps({"status":report["status"],"sha256":sha(raw),"path":str(p),"fixed_inputs":100,"inverse_hunks":counts,"new_methods":3,"tests_run":0}))
