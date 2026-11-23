from pathlib import Path
import ast,collections,hashlib,json,subprocess,sys,shutil
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123")
OUT=Path("/mnt/development/projects/diagnostics/semantic-page-mounted-known-pair-20261123")
SOURCE="ad7425fd60bb2c76e943c9cfc77af8e6984cb845"
DIRS=["Tools/PinkhaSemanticAnchorWire/apple_mounted","Tools/PinkhaSemanticAnchorWire/apple_consumer","Tools/PinkhaSemanticAnchorWire/apple_runtime","Tools/PinkhaSimulatorGate","Tools/PinkhaNativeDerived","Tools/Hanlin"]
SEEDS=["Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_known_pair.py","Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py","Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py","Tools/PinkhaSemanticAnchorWire/apple_runtime/contract.py"]
DYNAMIC={"Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py":["Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py"],"Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py":["Tools/PinkhaSemanticAnchorWire/apple_runtime/contract.py"]}
def git(*a):return subprocess.check_output(["git","-C",str(ROOT),*a])
def sha(raw):return hashlib.sha256(raw).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==SOURCE and not git("status","--porcelain")
allrows={}
for raw in filter(None,git("ls-tree","-rz",SOURCE).split(b"\0")):
 meta,n=raw.split(b"\t",1);mode,kind,oid=meta.decode().split();allrows[n.decode()]={"mode":mode,"kind":kind,"oid":oid}
modules=collections.defaultdict(list)
for n in allrows:
 if n.endswith(".py") and str(Path(n).parent) in DIRS:modules[Path(n).stem].append(n)
standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)|{"__future__"}
def top_nodes(nodes):
 for n in nodes:
  yield n
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):continue
  if isinstance(n,ast.If) and any(isinstance(x,ast.Constant) and x.value=="__main__" for x in ast.walk(n.test)):continue
  for field in ("body","orelse","finalbody"):
   child=getattr(n,field,None)
   if isinstance(child,list):yield from top_nodes(child)
  for h in getattr(n,"handlers",[]):yield from top_nodes(h.body)
pending=list(SEEDS);visited={};edges=[];dynamic_calls=[];missing=[]
while pending:
 n=pending.pop()
 if n in visited:continue
 raw=git("show",SOURCE+":"+n);tree=ast.parse(raw);row=allrows[n]
 assert row["kind"]=="blob" and row["mode"] in ("100644","100755")
 visited[n]={"sha256":sha(raw),"bytes":len(raw),"git":row}
 p=ROOT/n
 if p.exists():assert p.is_file() and not p.is_symlink() and p.read_bytes()==raw
 else:missing.append(n)
 for node in top_nodes(tree.body):
  names=[]
  if isinstance(node,ast.Import):names=[v.name for v in node.names]
  elif isinstance(node,ast.ImportFrom):assert not node.level;names=[node.module]
  for name in names:
   if name.split(".")[0] in standard:continue
   choices=modules.get(name,[])
   assert len(choices)==1,(n,name,choices)
   edges.append({"from":n,"module":name,"to":choices[0]});pending.append(choices[0])
  if isinstance(node,(ast.Assign,ast.Expr)):
   for call in ast.walk(node):
    if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=="spec_from_file_location":
     dynamic_calls.append(n)
 for target in DYNAMIC.get(n,[]):edges.append({"from":n,"module":"explicit repository-relative import spec","to":target});pending.append(target)
assert sorted(set(dynamic_calls))==sorted(DYNAMIC),dynamic_calls
assert missing and all(n.startswith("Tools/Hanlin/") for n in missing)
free=shutil.disk_usage("/mnt/development").free;assert free>2501000000
subprocess.run(["git","-C",str(ROOT),"sparse-checkout","add","Tools/Hanlin"],check=True)
for n,row in visited.items():
 p=ROOT/n;assert p.is_file() and not p.is_symlink() and sha(p.read_bytes())==row["sha256"]
assert not git("status","--porcelain")
report={"status":"PASS_STATIC_TOP_LEVEL_IMPORT_AND_EXPLICIT_DYNAMIC_CLOSURE","source_sha":SOURCE,"modules":visited,"edges":edges,"module_count":len(visited),"previously_missing_exact_files":sorted(missing),"hydrated_tree":"Tools/Hanlin","hydrated_tracked_file_count":18,"hydrated_tracked_bytes":182956,"no_source_bytes_changed":True,"ordinary_imports_executed":0,"tests_executed":0,"explicit_dynamic_spec_sources":sorted(set(dynamic_calls)),"scope":"Top-level repo import graph plus the two existing explicit repository-relative dynamic modules. Function bodies are not executed by preflight; one composed control will record its actual loaded modules.","script_sha256":sha(Path(__file__).read_bytes()),"free_bytes_before":free,"free_bytes_after":shutil.disk_usage("/mnt/development").free}
with (OUT/"static-import-closure.json").open("x") as f:f.write(json.dumps(report,sort_keys=True,indent=2)+"\n")
print(json.dumps({"status":report["status"],"module_count":len(visited),"missing_resolved":len(missing),"receipt_sha256":sha((OUT/"static-import-closure.json").read_bytes()),"free_bytes":report["free_bytes_after"]}))
