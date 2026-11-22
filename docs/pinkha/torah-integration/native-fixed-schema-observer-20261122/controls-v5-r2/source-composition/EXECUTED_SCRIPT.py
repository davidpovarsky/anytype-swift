from pathlib import Path
import subprocess,json,hashlib,time,shutil
root=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
packet=root/"controls-v5-r2";source=root/"candidate-v5"
repo=Path(r"C:\Users\DAVID\Code\anytype-heart-original-schema-observer-20261122")
base="d98420b1113536afd08cde6de9a5816f6d27ffff"
dest=root/"composition-v5-r2"
if dest.exists():raise RuntimeError("composition already exists; inspect checkpoint, do not replay")
dest.mkdir();material=dest/"materialized";material.mkdir();logs=dest/"logs";logs.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):
 temp=path.with_name(path.name+".tmp");temp.write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8");temp.replace(path)
commands=[]
def run(label,args,cwd,input=None):
 i=len(commands)+1;out=logs/(str(i)+"-"+label+".stdout");err=logs/(str(i)+"-"+label+".stderr")
 record={"label":label,"argv":args,"cwd":str(cwd),"phase":"STARTING","started":time.time(),"stdout":str(out.relative_to(dest)),"stderr":str(err.relative_to(dest))}
 commands.append(record);write(dest/"COMMANDS.json",commands)
 with out.open("wb") as o,err.open("wb") as e:
  p=subprocess.Popen(args,cwd=cwd,stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,stdout=o,stderr=e)
  record.update({"phase":"RUNNING","pid":p.pid});write(dest/"COMMANDS.json",commands)
  try:p.communicate(input=input,timeout=30)
  except subprocess.TimeoutExpired:
   p.kill();p.wait(timeout=10);record["timed_out"]=True
  record.update({"phase":"TERMINAL","returncode":p.returncode,"stdout_sha256":sha(out),"stderr_sha256":sha(err),"finished":time.time()});write(dest/"COMMANDS.json",commands)
  if p.returncode or record.get("timed_out"):raise RuntimeError("source command failed "+label)
 return out.read_bytes()
result={"status":"PREPARING_SOURCE_COMPOSITION","base":base,"source_index_sha256":sha(source/"SOURCE_REVIEW_INDEX.json"),"execution_manifest_sha256":sha(packet/"EXECUTION_INPUTS.json"),"builds":0,"tests":0,"native_calls":0,"go_invocations":0,"scope":"Owned partial affected-file materialization from immutable Git blobs; not a full checkout, build or native acceptance"}
write(dest/"RESULT.json",result)
try:
 manifest=json.loads((packet/"EXECUTION_INPUTS.json").read_text());sm=json.loads((source/"SOURCE_MANIFEST.json").read_text())
 assert result["source_index_sha256"]==manifest["source_index_sha256"]
 inventory_path=packet/manifest["r14_inventory"]["retained_path"];patch=packet/manifest["r14_patch"]["retained_path"]
 if sha(inventory_path)!=manifest["r14_inventory"]["sha256"] or sha(patch)!=manifest["r14_patch"]["sha256"]:raise RuntimeError("r14 changed")
 inventory=json.loads(inventory_path.read_text())
 product=sm["candidate"];tests=manifest["test_sources"]
 if set(e["path"] for e in inventory["files"]) & set(e["path"] for e in product):raise RuntimeError("r14/V5 path overlap")
 live_inputs=product+tests
 before={e["path"]:sha(repo/e["path"]) for e in live_inputs}
 if any(before[e["path"]]!=e["sha256"] for e in live_inputs):raise RuntimeError("owned working input differs before materialization")
 paths=sorted({e["path"] for e in inventory["files"]+product+tests}|set(manifest["original_module_hashes"]))
 records=run("immutable-tree",["git","ls-tree","-r","-z",base,"--",*paths],repo).split(b"\0")
 tree={}
 for record in records:
  if not record:continue
  meta,path=record.split(b"\t",1);mode,kind,oid=meta.decode().split()
  if kind!="blob" or mode!="100644":raise RuntimeError("unexpected original source type")
  tree[path.decode()]=oid
 objects=list(dict.fromkeys(tree.values()))
 batch=run("immutable-blobs",["git","cat-file","--batch"],repo,input=("\n".join(objects)+"\n").encode())
 offset=0;blobs={}
 for oid in objects:
  end=batch.index(b"\n",offset);header=batch[offset:end].decode().split();offset=end+1
  if header[:2]!=[oid,"blob"]:raise RuntimeError("Git batch object mismatch")
  n=int(header[2]);data=batch[offset:offset+n];offset+=n
  if batch[offset:offset+1]!=b"\n":raise RuntimeError("Git batch framing")
  offset+=1
  if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=oid:raise RuntimeError("Git blob bytes mismatch")
  blobs[oid]=data
 if offset!=len(batch):raise RuntimeError("Git batch trailing bytes")
 originals=[]
 for p,oid in tree.items():
  data=blobs[oid];out=material/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
  originals.append({"path":p,"git_blob":oid,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
 for e in inventory["files"]:
  p=material/e["path"]
  if e["before_sha256"] is None:
   if p.exists():raise RuntimeError("r14 expected genuinely new path")
  elif not p.exists() or sha(p)!=e["before_sha256"]:raise RuntimeError("r14 exact preimage differs "+e["path"])
 for p,expected in manifest["original_module_hashes"].items():
  if sha(material/p)!=expected:raise RuntimeError("original module/checksum differs")
 (dest/"ORIGINAL_BLOBS.json").write_text(json.dumps(originals,indent=2)+"\n",encoding="utf-8")
 result["original_blob_count"]=len(originals);result["requested_affected_paths"]=len(paths)
 write(dest/"RESULT.json",result)
 run("initialize-owned-temporary-git",["git","-c","core.autocrlf=false","init","--quiet"],material)
 run("r14-apply-check",["git","-c","core.autocrlf=false","apply","--check",str(patch)],material)
 run("r14-apply",["git","-c","core.autocrlf=false","apply",str(patch)],material)
 after_r14=[]
 for e in inventory["files"]:
  p=material/e["path"]
  if sha(p)!=e["after_sha256"]:raise RuntimeError("r14 composed output differs "+e["path"])
  after_r14.append({"path":e["path"],"sha256":sha(p),"bytes":p.stat().st_size})
 result["r14_outputs"]=after_r14;result["status"]="R14_COMPOSED_SOURCE_ONLY";write(dest/"RESULT.json",result)
 candidate_patch=source/"CANDIDATE.patch"
 run("v5-apply-check",["git","-c","core.autocrlf=false","apply","--check",str(candidate_patch)],material)
 run("v5-apply",["git","-c","core.autocrlf=false","apply",str(candidate_patch)],material)
 after_v5=[]
 for e in product:
  p=material/e["path"]
  if sha(p)!=e["sha256"]:raise RuntimeError("V5 composed output differs "+e["path"])
  after_v5.append({"path":e["path"],"sha256":sha(p),"bytes":p.stat().st_size})
 for e in tests:
  out=material/e["path"]
  if out.exists():raise RuntimeError("new control path collision")
  b=(packet/e["retained_path"]).read_bytes()
  if hashlib.sha256(b).hexdigest()!=e["sha256"]:raise RuntimeError("test source changed")
  out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
 for e in inventory["files"]:
  if sha(material/e["path"])!=e["after_sha256"]:raise RuntimeError("V5/test overlay changed r14 output")
 for p,expected in manifest["original_module_hashes"].items():
  if sha(material/p)!=expected:raise RuntimeError("overlay changed original module/checksum")
 after={e["path"]:sha(repo/e["path"]) for e in live_inputs}
 if before!=after:raise RuntimeError("owned actual V5 working source changed")
 result.update({"status":"PASS_SOURCE_COMPOSITION_ONLY","r14_path_count":len(after_r14),"v5_outputs":after_v5,"test_outputs":[{"path":e["path"],"sha256":sha(material/e["path"]),"bytes":(material/e["path"]).stat().st_size} for e in tests],"original_module_hashes":manifest["original_module_hashes"],"working_source_unchanged":True,"working_input_hashes":after,"r14_patch_sha256":sha(patch),"v5_patch_sha256":sha(candidate_patch),"materialized_source_path":str(material),"finished":time.time()})
except BaseException as error:
 result.update({"status":"FAIL_SOURCE_COMPOSITION_ONLY","error_type":type(error).__name__,"error":str(error),"finished":time.time()})
 write(dest/"RESULT.json",result)
 print(json.dumps(result));raise
write(dest/"RESULT.json",result)
print(json.dumps({"path":str(dest),"status":result["status"],"result_sha256":sha(dest/"RESULT.json"),"original_blob_count":len(originals),"r14_outputs":len(after_r14),"v5_outputs":len(after_v5),"new_test_copies":len(tests),"working_source_unchanged":True,"go_invocations":0,"builds":0,"tests":0,"native_calls":0}))
