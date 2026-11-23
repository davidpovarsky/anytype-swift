import ast,hashlib,json,os,shutil,stat,subprocess,time
from pathlib import Path
R=Path("/mnt/development/projects/worktrees/anytype-wave15-release-selection-order-20261123")
D=Path("/mnt/development/projects/diagnostics/release-selection-order-root-review-20261123")
HEAD="97563de533579b0705eed0ad0028bdaa944ff470"
DOC=R/"docs/validation/20261123-release-selection-order"
def need(c,m):
 if not c: raise RuntimeError(m)
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.check_output(["git","--no-optional-locks","-C",str(R),*a],timeout=30)
need(shutil.disk_usage(R).free>=2500000000+16777216,"capacity")
need(git("rev-parse","HEAD").decode().strip()==HEAD,"HEAD")
need(git("status","--porcelain=v1","--untracked-files=all")==b"","dirty writer")
expected={"control-inputs.json":"6347947179d47ac30c8e2e9fcd4c1fd2b697da9da88f0d75381fc87f530241b4","run-controls.py":"d53c27c208d363468f144ffadb267dad1fc2acb1aa7a6b551d1d6f9635e3e55c","control-freeze-review.json":"85af1aa689263dd04da6d8f9999094c2de7e0e0f096d18ce200203b608e86c39"}
for n,h in expected.items(): need(sha((DOC/n).read_bytes())==h,"frozen metadata "+n)
M=json.loads((DOC/"control-inputs.json").read_bytes())
paths={r["path"]:r for r in M["inputs"]}
for n in expected: paths[(DOC/n).relative_to(R).as_posix()]=None
rows=[]
for p,e in sorted(paths.items()):
 f=R/p;s=f.lstat();b=f.read_bytes()
 need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and f.resolve()==f,"physical "+p)
 t=git("ls-tree","HEAD","--",p).split(b"\t",1)[0].split()
 need(len(t)==3 and t[1]==b"blob","tree "+p)
 gb=git("cat-file","blob",t[2].decode())
 need(gb==b,"git bytes "+p)
 r={"path":p,"bytes":len(b),"mode":stat.S_IMODE(s.st_mode),"git_mode":t[0].decode(),"git_blob":t[2].decode(),"sha256":sha(b)}
 if e: need(all(r[k]==v for k,v in e.items()),"manifest "+p)
 rows.append(r)
inv=json.loads((R/M["inverse_metadata"]).read_bytes())
current=(R/inv["path"]).read_bytes();baseline=(R/M["baseline_caller"]).read_bytes()
need(sha(current)==inv["after_sha256"] and sha(baseline)==inv["before_sha256"],"inverse hash")
rest=current.decode()
need(len(inv["two_exact_substitutions"])==2,"hunk count")
for h in inv["two_exact_substitutions"]:
 need(rest.count(h["after"])==1,"nonunique inverse");rest=rest.replace(h["after"],h["before"])
need(rest.encode()==baseline,"whole inverse")
def defs(b):
 tree=ast.parse(b);lines=b.decode().splitlines(keepends=True)
 return {n.name:"".join(lines[n.lineno-1:n.end_lineno]) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
old,new=defs(baseline),defs(current)
need(set(old)==set(new),"definition inventory")
changed=[n for n in old if old[n]!=new[n]]
need(changed==["execute"] and len(old)-1==14,"definition scope")
need(len(M["inputs"])==42 and len(M["python_modules"])==39 and M["expected_methods"]==1 and M["expected_subcases"]==3,"control scope")
need(M["old_tests_to_run"]==0 and M["product_tests_to_run"]==0,"replay")
wrapper=(DOC/"run-controls.py").read_bytes();wt=ast.parse(wrapper)
const={}
for n in wt.body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
  try: const[n.targets[0].id]=ast.literal_eval(n.value)
  except (ValueError,TypeError): pass
need(const["TEST"]==M["test_names"][0] and M["test_names"]==[const["TEST"]],"method")
need(const["RESERVE"]==2500000000 and const["SOURCE"]==M["source_commit"],"wrapper bounds")
tt=ast.parse((R/"Tools/PinkhaSimulatorGate/test_coherent_selection_order.py").read_bytes())
test_names=[n.name for c in tt.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith("test_")]
need(test_names==["test_final_editor_plan_precedes_owned_seal_and_native_admission"],"new method inventory")
# No repository module imports or runtime methods are executed by this review.
for p in M["python_modules"].values(): ast.parse((R/p).read_bytes(),filename=p)
need(not Path("/mnt/development/projects/diagnostics/release-selection-order-controls-20261123/attempt1").exists(),"prior control output")
receipt={"protocol":"root-release-selection-order-source-review-v1","status":"SOURCE_REVIEW_PASS","checked_head":HEAD,"source_commit":M["source_commit"],"fixed_inputs":len(M["inputs"]),"runtime_metadata":2,"review_metadata":1,"verified_git_physical_inputs":len(rows),"input_rows":rows,"static_local_modules":len(M["python_modules"]),"whole_file_two_hunk_inverse":True,"changed_named_definitions":changed,"unchanged_other_named_definitions":14,"selected_tests":M["test_names"],"expected_methods":1,"expected_subcases":3,"reviewed_execution_boundaries":["real caller AST language/construction region","actual strict construction/selection guard","injected native boundary before delegation"],"sdk06_scope":"inactive original-only branch; root must rebind only caller hash after integration with exact inverse","new_tests_run":0,"old_tests_run":0,"product_methods_run":0,"repo_modules_imported":0,"native_commands":0,"free_bytes":shutil.disk_usage(R).free,"created_ns":str(time.time_ns())}
D.mkdir(mode=0o700,parents=True,exist_ok=True)
out=D/"source-review-97563de.json";raw=(json.dumps(receipt,sort_keys=True,indent=2)+"\n").encode()
with out.open("xb") as f: f.write(raw);f.flush();os.fsync(f.fileno())
out.chmod(0o400)
print(json.dumps({"status":receipt["status"],"head":HEAD,"path":str(out),"sha256":sha(raw),"inputs":len(rows),"free_bytes":receipt["free_bytes"],"tests":0}))
