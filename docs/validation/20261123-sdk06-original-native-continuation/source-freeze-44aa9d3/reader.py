from pathlib import Path
import ast,hashlib,json,stat,subprocess,shutil
r=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-original-native-20261123")
head="44aa9d3c64275917a79e6392ef619554d1af2990"
D="docs/validation/20261123-sdk06-original-native-continuation"
assert subprocess.check_output(["git","-C",str(r),"rev-parse","HEAD"],text=True).strip()==head
assert not subprocess.check_output(["git","-C",str(r),"status","--porcelain","--untracked-files=all"],text=True)
raw=(r/D/"failed-control-inputs.json").read_bytes();m=json.loads(raw)
assert hashlib.sha256(raw).hexdigest()=="a93c55f232b6c21b72645810e91c40e6e3cf3d0eb4a00382a20b2c4b9e8b2c74"
metadata=[D+"/"+n for n in ("control-inputs.json","run-controls.py","source-review.json","source-plan.json","exact-source-inverses.json","selection-copy-inverse.json","current-static-closure.json","failed-control-inputs.json","run-failed-lane-control.py","failed-method-review.json")]
names=sorted(set(m["inputs"])|set(metadata));assert len(names)==160
tree={}
for entry in subprocess.check_output(["git","-C",str(r),"ls-tree","-r","-z",head,"--",*names]).split(b"\0"):
 if entry:
  info,name=entry.split(b"\t",1);mode,kind,oid=info.decode().split();assert kind=="blob" and mode in {"100644","100755"};tree[name.decode()]=(mode,oid)
assert set(tree)==set(names)
blob=subprocess.check_output(["git","-C",str(r),"cat-file","--batch"],input=b"".join((tree[n][1]+"\n").encode() for n in names),timeout=30)
offset=0;rows={}
for n in names:
 end=blob.index(b"\n",offset);oid,kind,size=blob[offset:end].split();size=int(size);start=end+1;b=blob[start:start+size];offset=start+size+1
 assert kind==b"blob" and oid.decode()==tree[n][1] and blob[offset-1:offset]==b"\n" and len(b)==size
 p=r
 for part in n.split("/"):p=p/part;assert not p.is_symlink(),n
 st=p.stat();assert stat.S_ISREG(st.st_mode) and p.read_bytes()==b and bool(st.st_mode&0o111)==(tree[n][0]=="100755"),n
 row={"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),"git_mode":tree[n][0]}
 if n in m["inputs"]:assert row==m["inputs"][n],n
 rows[n]={**row,"git_blob":tree[n][1],"physical_mode":stat.S_IMODE(st.st_mode)}
assert offset==len(blob)
review=json.loads((r/D/"failed-method-review.json").read_bytes())
test=(r/"Tools/PinkhaSimulatorGate/test_sdk06_original_native.py").read_text()
old=subprocess.check_output(["git","-C",str(r),"show","cf70fdf165586baffd257fdb135cea06f64e745d:Tools/PinkhaSimulatorGate/test_sdk06_original_native.py"]).decode()
back=test
for h in reversed(review["test_inverse"]):assert back.count(h["after"])==1;back=back.replace(h["after"],h["before"],1)
assert back==old
wrapper=(r/D/"run-failed-lane-control.py").read_text()
back=wrapper.replace(review["wrapper_input_hash_substitution"]["after"],"PENDING_CONTROL_INPUTS_SHA")
for h in reversed(review["wrapper_inverse"]):assert back.count(h["after"])==1;back=back.replace(h["after"],h["before"],1)
back=back.replace("PENDING_CONTROL_INPUTS_SHA",review["wrapper_input_hash_substitution"]["before"])
assert back==(r/D/"run-controls.py").read_text()
ast.parse(wrapper);ast.parse(test)
print(json.dumps({"status":"DIRECT_FROZEN_GIT_PHYSICAL_MODE_PREFLIGHT_PASS","source":head,"input_count":len(names),"fixed_input_count":len(m["inputs"]),"metadata_count":len(metadata),"paths_sha256":hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"metadata":{n:rows[n] for n in metadata},"test_inverse_hunks":len(review["test_inverse"]),"wrapper_inverse_hunks":len(review["wrapper_inverse"]),"methods":m["methods"],"retained":m["retained_original_passes"],"production_imports":0,"controls_executed":0,"free":shutil.disk_usage(r).free},sort_keys=True))