import pathlib,hashlib,json,os,shutil
P=pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-ram-graph-source-20261123/projected-original-audit1-parts")
D=P.parent/"projected-original-audit1"
A=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-graph-attempt1")
assert shutil.disk_usage("/mnt/development").free>=1073741824+1048576
assert sorted(p.name for p in P.iterdir())==[f"{i:03d}" for i in range(9)]
b=b"".join((P/f"{i:03d}").read_bytes() for i in range(9));assert len(b)==29687
values=json.loads(b);assert len(values)==9 and len({v["name"] for v in values})==9
allowed={"result-reader.py","metadata-reader.py","size-reader.py","custody-reader.py","metadata-observation.json","size-observation.json","custody-observation.json","sentinel-original.json","audit.json"}
assert {v["name"] for v in values}==allowed
audit=json.loads(next(v["text"] for v in values if v["name"]=="audit.json"))
for v in audit["originals"]:
 p=A/v["path"];raw=p.read_bytes();assert len(raw)==v["bytes"] and hashlib.sha256(raw).hexdigest()==v["sha256"]
assert sum(v["bytes"] for v in audit["originals"])==3891600
out=[]
for v in values:
 raw=v["text"].encode("ascii");p=D/v["name"]
 with p.open("xb") as f:os.chmod(p,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 out.append({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
raw=(A/"result.json").read_bytes();p=D/"original-result.json"
with p.open("xb") as f:os.chmod(p,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
out.append({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
index={"schema":"sealed-original-audit-index-v1","files":out,"source_payload_sha256":hashlib.sha256(b).hexdigest(),"original_query_reruns":0,"native_builds_tests":0}
raw=(json.dumps(index,sort_keys=True,indent=2)+"\n").encode();p=D/"index.json"
with p.open("xb") as f:os.chmod(p,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
fd=os.open(D,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
print(json.dumps({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"audit":next(x for x in out if x["path"].endswith("/audit.json")),"files":len(out),"new_bytes":sum(x["bytes"] for x in out)+len(raw)}))
