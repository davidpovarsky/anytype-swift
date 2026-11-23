import pathlib,hashlib,json,gzip,os,stat,collections
A=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-graph-attempt1")
R=json.loads((A/"result.json").read_bytes())
assert hashlib.sha256((A/"result.json").read_bytes()).hexdigest()=="249c5a4a5a16ce7f39669925d03e804c8dab1517899c487179d123912b66601f"
def read(path,pin):
 b=path.read_bytes()
 assert hashlib.sha256(b).hexdigest()==pin
 return b
raw=read(A/"stdout.log",R["query"]["stdout"]["sha256"])
text=raw.decode(); d=json.JSONDecoder(); off=0; packages=[]
while off<len(text):
 while off<len(text) and text[off].isspace():off+=1
 if off==len(text):break
 p,off=d.raw_decode(text,off); assert isinstance(p,dict) and not p.get("Error") and not p.get("DepsErrors");packages.append(p)
fields=("GoFiles","CgoFiles","CFiles","CXXFiles","MFiles","HFiles","FFiles","SFiles","SwigFiles","SwigCXXFiles","SysoFiles","EmbedFiles","TestGoFiles","XTestGoFiles","TestEmbedFiles","XTestEmbedFiles")
paths=set(); generated=[]; modules={}
for p in packages:
 for f in fields:
  for n in p.get(f,[]):
   v=pathlib.Path(n);paths.add(str(v if v.is_absolute() else pathlib.Path(p.get("Dir",""))/v))
   if v.is_absolute():generated.append({"package":p["ImportPath"],"name":p.get("Name"),"field":f,"path":str(v)})
 m=p.get("Module")
 if m:
  modules[(m["Path"],m.get("Version",""))]=m
  gm=m.get("Replace",m).get("GoMod")
  if gm:paths.add(gm)
invraw=read(A/"ram-inventory.json.gz",R["ram_finalization"]["inventory"]["sha256"])
invexp=gzip.decompress(invraw);assert hashlib.sha256(invexp).hexdigest()==R["ram_finalization"]["inventory"]["expanded_sha256"]
inv=json.loads(invexp)
generated_inventory={k:v for k,v in inv["files"].items() if v["classification"]=="validated_generated_test_main"}
files=[]
for p in sorted(A.rglob("*")):
 if p.is_file():
  st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink()
  files.append({"path":str(p.relative_to(A)),"bytes":st.st_size,"mode":oct(stat.S_IMODE(st.st_mode)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
snapshots={}
for k in ("source_before","source_after"):
 b=read(pathlib.Path(R[k]["path"]),R[k]["sha256"]);v=json.loads(gzip.decompress(b));snapshots[k]={"keys":list(v),"top_sizes":{n:len(w) if isinstance(w,(list,dict)) else None for n,w in v.items()}}
print(json.dumps({"packages":len(packages),"modules":len(modules),"distinct_source_paths":len(paths),"generated_refs":generated,"generated_inventory":generated_inventory,"inventory_counts":{"files":len(inv["files"]),"directories":len(inv["directories"]),"unexpected":inv["unexpected_payloads"],"logical_file_bytes":sum(int(v["st_size"]) for v in inv["files"].values())},"snapshots":snapshots,"files":files,"total_original_bytes":sum(v["bytes"] for v in files),"actual_read_only":True},sort_keys=True))
