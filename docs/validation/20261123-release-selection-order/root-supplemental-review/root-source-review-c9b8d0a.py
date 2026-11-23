import ast,hashlib,json,os,shutil,stat,subprocess,sys,time
from pathlib import Path
R=Path("/mnt/development/projects/worktrees/anytype-wave15-release-selection-order-20261123")
DOC=R/"docs/validation/20261123-release-selection-order"
D=Path("/mnt/development/projects/diagnostics/release-selection-order-root-review-20261123")
H="c9b8d0a8aa784faad389f7a4bf5a702fa7e06ba5";OLD="97563de533579b0705eed0ad0028bdaa944ff470"
def need(c,m):
 if not c:raise RuntimeError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(R),*a],timeout=30)
need(shutil.disk_usage(R).free>=2517825792,"capacity guard")
need(git("rev-parse","HEAD").decode().strip()==H and git("status","--porcelain=v1","--untracked-files=all")==b"","freeze/clean")
hashes={"admission-inputs.json":"2d4b7d823193bcfa0af9bc6021d243992378457fcf0cc616e33702443464a16a","audit-admission-only.py":"f332f129eedb4b6cc27b45b2ca1abcfa78aa9933a84f3ffebdc389f602158a44","late-import-source-review.json":"961162f29ae27dec35e7b91a5f9b4e163479a0f117ef106d944023fdaf0cd2a1","failed-attempt1-seal.json":"09006459cfb82b1bc24e1bbb40a1908a18883cdb560c48474171a7384c8717bc"}
for n,h in hashes.items():need(sha((DOC/n).read_bytes())==h,"frozen hash "+n)
changed=git("diff","--name-status",OLD,H).decode().splitlines()
need(len(changed)==74 and all(s.startswith("A\tdocs/validation/20261123-release-selection-order/") for s in changed),"documentation-only additions")
M=json.loads((DOC/"admission-inputs.json").read_bytes())
need(len(M["inputs"])==116 and len(M["python_modules"])==40 and M["test_methods_to_run"]==0 and M["native_methods_to_run"]==0 and M["simulator_commands_to_run"]==0,"new scope")
paths={r["path"]:r for r in M["inputs"]}
for n in ["admission-inputs.json","audit-admission-only.py"]:paths[(DOC/n).relative_to(R).as_posix()]=None
rows=[]
for p,e in sorted(paths.items()):
 f=R/p;s=f.lstat();b=f.read_bytes();t=git("ls-tree","HEAD","--",p).split(b"\t",1)[0].split()
 need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and f.resolve()==f,"physical "+p)
 need(len(t)==3 and t[1]==b"blob" and git("cat-file","blob",t[2].decode())==b,"Git "+p)
 row={"path":p,"bytes":len(b),"mode":stat.S_IMODE(s.st_mode),"sha256":sha(b),"git_mode":t[0].decode(),"git_blob":t[2].decode(),"inode":s.st_ino,"mtime_ns":s.st_mtime_ns,"uid":s.st_uid}
 if e:need(all(row[k]==v for k,v in e.items()),"fixed input "+p)
 rows.append(row)
by={r["path"]:r for r in rows}
oldroot=DOC/"original-attempt1"
execution=(oldroot/"execution.json").read_bytes();E=json.loads(execution)
need(sha(execution)=="72cbce55797bc58517a7091352634485d38adb450d18b3742ecf807c10278c98","original execution")
need(E["status"]=="FAIL" and E["tests_run"]==1 and E["subcase_passes"]==3 and len(E["named_passes"])==1 and not E["named_failures"],"original outcome")
need(E["failure"]=={"type":"RuntimeError","message":"Unadmitted repository module: Tools/PinkhaSimulatorGate/run_t5_apple_pair.py"},"original failure")
events=[json.loads(x) for x in (oldroot/"events.jsonl").read_text().splitlines()]
need([x["action"] for x in events]==["START","SUBCASE_PASS","SUBCASE_PASS","SUBCASE_PASS","PASS"],"original events")
before=json.loads((oldroot/"source-before.json").read_bytes())
need(len(before)==44 and all(by[r["path"]]==r for r in before),"all44 current versus original before")
for r in before:need(git("show",OLD+":"+r["path"])==(R/r["path"]).read_bytes(),"old Git")
need(not (oldroot/"loaded-after.json").exists() and not (oldroot/"source-after.json").exists(),"historical-after fabrication")
oldM=json.loads((DOC/"control-inputs.json").read_bytes())
pair="Tools/PinkhaSimulatorGate/run_t5_apple_pair.py"
need(M["python_modules"]==dict(oldM["python_modules"],run_t5_apple_pair=pair),"only pair added")
need(len(M["expected_current_loaded"])==34 and len(M["original_loaded_before"])==33,"current import target")
need(by[pair]==M["late_input"] and sha((R/pair).read_bytes())=="11e11ec19eca11d506f56b37ad8ff76bcdbc40a28a4c233b4e57cb86432b1340","late pair")
need(git("show",OLD+":"+pair)==(R/pair).read_bytes(),"frozen late pair")
need(len(M["preserved_originals"])==69,"preserved count")
for r in M["preserved_originals"]:
 p=Path(r["source"]);s=p.lstat();b=p.read_bytes()
 need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and p.resolve()==p and stat.S_IMODE(s.st_mode)==r["original_mode"]==0o400 and s.st_uid==r["original_uid"] and s.st_ino==r["original_inode"] and s.st_mtime_ns==r["original_mtime_ns"],"original identity")
 need(len(b)==r["bytes"] and sha(b)==r["sha256"] and b==(R/r["path"]).read_bytes(),"original bytes")
trace=json.loads((DOC/"late-import-source-review.json").read_bytes())
for r in trace["call_path"]:
 b=(R/r["path"]).read_bytes();nodes=[n for n in ast.walk(ast.parse(b)) if isinstance(n,ast.FunctionDef) and n.name==r["function"]]
 need(len(nodes)==1 and sha(b)==r["source_sha256"] and ast.get_source_segment(b.decode(),nodes[0])==r["source"],"call path")
tree=ast.parse((R/pair).read_bytes())
for n in tree.body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):
  names=[a.name.split(".")[0] for a in n.names] if isinstance(n,ast.Import) else [n.module.split(".")[0]]
  need(all(x in sys.stdlib_module_names for x in names),"nonstdlib eager pair")
 elif isinstance(n,ast.FunctionDef):
  need(not n.decorator_list and all(v is None or isinstance(v,ast.Constant) and v.value in (None,True,False) for v in [*n.args.defaults,*n.args.kw_defaults]),"definition effect")
 elif isinstance(n,ast.If):
  need(ast.dump(n.test,include_attributes=False)=="Compare(left=Name(id='__name__', ctx=Load()), ops=[Eq()], comparators=[Constant(value='__main__')])","eager branch")
 else:need(isinstance(n,(ast.Assign,ast.AnnAssign,ast.Expr)) and not any(isinstance(v,ast.Call) for v in ast.walk(n)),"top-level effect")
wrapper=(DOC/"audit-admission-only.py").read_bytes();wt=ast.parse(wrapper)
need(not any(isinstance(n,ast.Attribute) and n.attr in {"TextTestRunner","loadTestsFromName","loadTestsFromModule","TestSuite"} for n in ast.walk(wt)),"test runner present")
need(not Path("/mnt/development/projects/diagnostics/release-selection-order-controls-20261123/admission-only1").exists(),"audit already started")
result={"protocol":"root-release-supplemental-import-admission-source-review-v1","status":"SOURCE_REVIEW_PASS","checked_head":H,"original_head":OLD,"source":M["source_commit"],"fixed_inputs":116,"metadata_inputs":2,"verified_input_rows":len(rows),"input_rows_sha256":sha(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()),"preserved_originals_verified":69,"old_before_current_exact":44,"original_named_passes":E["named_passes"],"original_subcase_passes":3,"original_wrapper_status":"FAIL","historical_loaded_after_available":False,"historical_source_after_available":False,"historical_after_reconstructed":False,"new_current_import_scope":34,"static_module_map":40,"only_added_module":pair,"exact_static_call_path":len(trace["call_path"]),"wrapper_sha256":sha(wrapper),"manifest_sha256":hashes["admission-inputs.json"],"no_replay":True,"project_modules_imported":0,"test_methods_executed":0,"review_scope":"source-only review; author audit must still execute only current import admission","created_ns":str(time.time_ns()),"free_bytes":shutil.disk_usage(R).free}
need(shutil.disk_usage(R).free>=2517825792,"capacity before receipt")
p=D/"source-review-c9b8d0a.json";raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
with p.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
p.chmod(0o400)
print(json.dumps({"status":result["status"],"head":H,"path":str(p),"sha256":sha(raw),"inputs":118,"originals":69,"tests":0,"free_bytes":result["free_bytes"]}))
