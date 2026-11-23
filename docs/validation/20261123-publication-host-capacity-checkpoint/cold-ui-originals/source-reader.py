from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,stat,shutil
p=Path("/mnt/development/projects/diagnostics/native-ui-451483-original-result-20261123/artifact-14807326846.zip")
base=p.parent
expected_bytes=140198044;expected_sha="d30b144798580d7533e309aca2d3acf60191a94a7a9f025e04b89192c7d79ba8"
def meta(st):return {k:str(v) for k,v in {"device":st.st_dev,"inode":st.st_ino,"mode":stat.S_IMODE(st.st_mode),"uid":st.st_uid,"gid":st.st_gid,"nlink":st.st_nlink,"bytes":st.st_size,"allocated":st.st_blocks*512,"mtime_ns":st.st_mtime_ns,"ctime_ns":st.st_ctime_ns}.items()}
assert p.resolve()==p
for x in (p,*p.parents):assert not x.is_symlink(),str(x)
before=meta(p.lstat());assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_size==expected_bytes and p.stat().st_nlink==1
h=hashlib.sha256();count=0
with p.open("rb") as f:
 assert meta(os.fstat(f.fileno()))==before
 while b:=f.read(4*1024**2):h.update(b);count+=len(b)
 assert meta(os.fstat(f.fileno()))==before
assert meta(p.lstat())==before and count==expected_bytes and h.hexdigest()==expected_sha
api_raw=(base/"original-artifact-metadata.json").read_bytes();api=json.loads(api_raw)
acq_raw=(base/"acquisition.json").read_bytes();acq=json.loads(acq_raw)
assert api["id"]==acq["artifact_id"]==14807326846
assert api["workflow_run"]["id"]==acq["run_id"]==45148353071
assert api["workflow_run"]["head_sha"]==acq["source_sha"]=="9cafd32811e50f4e883efb034888d7ce1e349c02"
assert api["digest"]=="sha256:"+expected_sha and api["size_in_bytes"]==count
assert acq["status"]=="PASS_FULL_ORIGINAL_ARCHIVE_ACQUIRED_ONCE" and acq["sha256"]==expected_sha and acq["path"]==str(p)
print(json.dumps({"status":"SOURCE_ARCHIVE_BYTES_VERIFIED_READ_ONLY","at":datetime.now(timezone.utc).isoformat(),"path":str(p),"metadata":before,"sha256":h.hexdigest(),"source_mutations":0,"app_source":acq["source_sha"],"origin_run":acq["run_id"],"origin_attempt":1,"artifact_id":acq["artifact_id"],"origin_api":{"path":str(base/"original-artifact-metadata.json"),"sha256":hashlib.sha256(api_raw).hexdigest(),"bytes":len(api_raw)},"original_acquisition":{"path":str(base/"acquisition.json"),"sha256":hashlib.sha256(acq_raw).hexdigest(),"bytes":len(acq_raw)},"qualification":"Copy-only full source hash and four stable exact metadata observations; final peer and reader gate required before redundant Oracle unlink.","free_bytes":shutil.disk_usage(p).free},sort_keys=True))
