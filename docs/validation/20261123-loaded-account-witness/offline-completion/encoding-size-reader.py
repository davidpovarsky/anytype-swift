import pathlib,hashlib,json,gzip,stat,collections
A=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-graph-attempt1")
raw=(A/"stdout.log").read_bytes()
assert hashlib.sha256(raw).hexdigest()=="240201e3a30b6391adcbdc090ef9829fe66c36c62bfd59de1eba7b0aeee61dc3"
inv=json.loads(gzip.decompress((A/"ram-inventory.json.gz").read_bytes()))
text=raw.decode(); dec=json.JSONDecoder(); off=0; pkgs=[]; inputs={}; modules={}
fields=("GoFiles","CgoFiles","CFiles","CXXFiles","MFiles","HFiles","FFiles","SFiles","SwigFiles","SwigCXXFiles","SysoFiles","EmbedFiles","TestGoFiles","XTestGoFiles","TestEmbedFiles","XTestEmbedFiles")
ram=pathlib.Path("/dev/shm/pinkha-loaded-account-projected-source-20261123")
sf=("st_dev","st_ino","st_mode","st_uid","st_gid","st_nlink","st_size","st_mtime_ns","st_ctime_ns")
def probe(p,generated=None):
 if p.is_relative_to(ram):
  v=dict(inv["files"][p.relative_to(ram).as_posix()]);v.pop("classification");resolved=str(p)
 else:
  st=p.stat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink()
  v={"path":str(p),"sha256":"0"*64,**{k:str(getattr(st,k)) for k in sf}};resolved=str(p.resolve())
 v["resolved_path"]=resolved
 if generated is not None:v["generated_test_main"]=generated
 return v
while off<len(text):
 while off<len(text) and text[off].isspace():off+=1
 if off==len(text):break
 p,off=dec.raw_decode(text,off);assert not p.get("Error") and not p.get("DepsErrors")
 pkgs.append({"import_path":p["ImportPath"],"directory":p.get("Dir"),"for_test":p.get("ForTest"),"standard":p.get("Standard",False),"module":p.get("Module")})
 for f in fields:
  for n in p.get(f,[]):
   q=pathlib.Path(n);g=q.is_absolute();q=q if g else pathlib.Path(p.get("Dir",""))/q
   inputs[str(q)]=probe(q,g)
 m=p.get("Module")
 if m:
  modules[(m["Path"],m.get("Version",""))]=m
  gm=m.get("Replace",m).get("GoMod")
  if gm:inputs[gm]=probe(pathlib.Path(gm))
plan={"protocol":"loaded-account-ram-cache-source-graph-v1","packages":pkgs,"modules":[modules[k] for k in sorted(modules)],"inputs":inputs,"source_only":True,"compile_export_or_test_requested":False,"module_cache_mounted_readonly":True,"original_go_build_cache_mounted":False,"new_empty_ram_cache":True,"cache_stale_or_build_id_values_are_not_source_identity":True,"generated_main_custody":{}}
table=[]
for p,v in sorted(inputs.items()):
 assert p==v["path"]
 table.append([p,v["sha256"]]+[v[k] for k in sf]+[None if v["resolved_path"]==p else v["resolved_path"],0 if "generated_test_main" not in v else (2 if v["generated_test_main"] else 1)])
copy=dict(plan);copy["inputs"]={"schema":"lossless-input-columns-v1","columns":["path","sha256",*sf,"resolved_path_or_same","generated_presence"],"rows":table}
decoded={}
for x in table:
 p=x[0];v={"path":p,"sha256":x[1],**dict(zip(sf,x[2:11])),"resolved_path":p if x[11] is None else x[11]}
 if x[12]:v["generated_test_main"]=x[12]==2
 decoded[p]=v
assert decoded==inputs
enc=lambda x:(json.dumps(x,sort_keys=True,separators=(",",":"))+"\n").encode()
print(json.dumps({"stat_only_size_measurement":True,"dependency_payload_hashes_read":False,"placeholder_digest_length":64,"packages":len(pkgs),"modules":len(modules),"inputs":len(inputs),"current_metadata_original_representation_bytes":len(enc(plan)),"lossless_table_bytes":len(enc(copy)),"limit":6*1024*1024,"generated_custody_not_included_in_estimate":True,"roundtrip_equal":decoded==inputs,"alias_resolved_paths":sum(v["resolved_path"]!=p for p,v in inputs.items()),"tuple_rows":len(table),"no_files_written":True,"total_dependency_logical_bytes":sum(int(v["st_size"]) for v in inputs.values()),"largest_dependency_bytes":max(int(v["st_size"]) for v in inputs.values())},sort_keys=True))
