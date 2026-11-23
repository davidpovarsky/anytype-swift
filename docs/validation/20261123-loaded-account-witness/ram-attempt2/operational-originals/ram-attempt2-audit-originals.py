#!/usr/bin/env python3
import gzip,hashlib,io,json,os,pathlib,shutil,stat,subprocess,tarfile
R=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
B=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
D=pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-ram-graph-source-20261123")
T=R/"docs/validation/20261123-loaded-account-witness/ram-attempt2"
H=lambda raw:hashlib.sha256(raw).hexdigest()
HEAD="bd5efdf894b068a4b2080245b03c9db4184652f3"
def git(*args):
 return subprocess.check_output(["git","-C",str(R),*args],timeout=30).decode().strip()
def read(p):
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
 with os.fdopen(fd,"rb") as f:
  a=os.fstat(f.fileno());b=f.read();z=os.fstat(f.fileno())
 keys=("st_dev","st_ino","st_mode","st_uid","st_gid","st_size","st_nlink","st_mtime_ns","st_ctime_ns")
 assert stat.S_ISREG(a.st_mode) and a.st_nlink==1
 assert all(getattr(a,k)==getattr(z,k) for k in keys)
 return b,{k:str(getattr(a,k)) for k in keys}
assert git("rev-parse","HEAD")==HEAD and not git("status","--porcelain=v1","--untracked-files=normal")
assert not T.exists() and shutil.disk_usage(R).free>=1073741824
pins={
R/"Tools/AnyEngineValidation/loaded_account_witness/ram_graph.py":"3b7b1802213811b57174e93e7de0ea52b712c4e76c34d0f89c14889eeba21ba3",
R/"Tools/AnyEngineValidation/loaded_account_witness/graph.py":"6aacb0c911aed49d88d9f0e7ef82b08a5ceab431139bb7b71f17c7d0aedfd23d",
D/"ram-custody-recovery.py":"849a9c658c5b821c7a7f7eb2fcaaad630438cc0b87936e9b8523f781d59db3f7",
D/"ram-custody-recovery-v2.py":"2e9ea367a86d6732e96fd173c485eea147ab4c49cde93f4ef4cf6d8140d4d041"}
for p,h in pins.items():assert H(read(p)[0])==h
payloads={};originals=[]
for dirname,label in (("ram-graph-attempt2","query-originals"),("ram-attempt2-custody-recovery","recovery-v1-originals"),("ram-attempt2-custody-recovery2","recovery-v2-originals")):
 for p in sorted((B/dirname).rglob("*")):
  assert not p.is_symlink()
  if p.is_dir():continue
  raw,meta=read(p);relative=p.relative_to(B/dirname).as_posix()
  target=label+"/"+relative;encoding="byte-exact"
  if dirname=="ram-graph-attempt2" and relative=="stdout.log":
   target+=".gz";saved=gzip.compress(raw,mtime=0);encoding="gzip derivative; decompressed bytes equal original"
   assert H(raw)=="dbc81f587ab0e53b07b15947afe2933c4eda4c55391ba3564e6ee44924f594af"
   assert len(raw)==8388608 and gzip.decompress(saved)==raw
  else:saved=raw
  payloads[target]=saved
  originals.append({"original_path":str(p),"metadata":meta,"original_sha256":H(raw),"retained_path":target,"retained_bytes":len(saved),"retained_sha256":H(saved),"encoding":encoding})
for n in ("ram-custody-recovery.py","ram-custody-recovery-freeze.json","ram-custody-recovery-v2.py","ram-custody-recovery-v2.diff","ram-custody-recovery-v2-freeze.json","ram-attempt2-recovery-observation-1.json","ram-launcher-attempt2.py","ram-launcher-attempt2-provenance.json","one-query-launch-attempt2.json"):
 raw,meta=read(D/n);payloads["operational-originals/"+n]=raw
 originals.append({"original_path":str(D/n),"metadata":meta,"original_sha256":H(raw),"retained_path":"operational-originals/"+n,"retained_bytes":len(raw),"retained_sha256":H(raw),"encoding":"byte-exact"})
payloads["sentinel-originals.json"]=(D/"ram-attempt2-seal-tool-originals.json").read_bytes()
payloads["audit-originals.py"]=pathlib.Path(__file__).read_bytes()
q=json.loads(payloads["query-originals/result.json"])
v1=json.loads(payloads["recovery-v1-originals/result.json"])
v2=json.loads(payloads["recovery-v2-originals/result.json"])
assert H(payloads["query-originals/result.json"])=="26b3d52fb6baad3b1c7e1d36eedadcb7b39ed50abb56187cf155860f70b15f53"
assert q["status"]=="FAILED" and q["primary_error"]["message"]=="source_query_stdout_limit"
assert q["native_builds"]==0 and q["actual_test_methods"]==0
assert q["query"]["launch_attempted"] is True and q["query"]["source_enumeration_only"] is True
assert q["query"]["stdout_complete"] is False and q["query"]["stderr_complete"] is False
assert any(e["type"]=="PermissionError" and e["phase"]=="cli-group" for e in q["query"]["additional_cleanup_errors"])
assert q["query"]["cleanup_error"]["message"]=="docker_observation_failed_container-owned-kill"
argv=q["query"]["argv"];assert argv[argv.index("list"):argv.index("list")+4]==["list","-deps","-test","-json"]
assert "-compiled" not in argv and "-export" not in argv and "test" not in argv
before=payloads["query-originals/source-before.json.gz"];after=payloads["query-originals/source-after.json.gz"]
assert before==after and H(before)=="ff9f4542fd929155a2500aab22fef2a1c7c21574faed5b1544e253fd147c0eed"
snapshot=json.loads(gzip.decompress(before))
counts={k:len(snapshot[k]["inputs"]) for k in ("heart","any_sync","controller")}
assert counts=={"heart":2453,"any_sync":574,"controller":7} and len(snapshot["actual_loaded_python"])==1
assert snapshot["heart"]["commit"]=="24dc6393b30e6d1d80ec28ff624060af9bb4327a"
assert snapshot["any_sync"]["commit"]=="c005bd6cde8d8f8a6007c35f06894f3d89f9f07c"
assert snapshot["controller"]["commit"]==HEAD
assert H(payloads["recovery-v1-originals/result.json"])=="de0c3f5bdb23ebad7ed240567416cf39bec9ab13673dd1951ae55ef3268e1f9e"
assert v1["status"]=="FAILED" and v1["primary_error"]["message"]=="current_container_binding_Mounts"
assert H(payloads["recovery-v2-originals/result.json"])=="28d4aa6bbabf56b846fde74601fbfee76c414c354251b3bdd6a60dd5ab7ba8b8"
assert v2["status"]=="PASS_LATER_CUSTODY_RECOVERY" and v2["original_query_status"]==v2["original_cleanup_status"]=="FAILED"
assert v2["actual_new_go_queries"]==v2["native_builds_tests"]==0
assert v2["normal_unmount"]["returncode"]==0 and v2["normal_unmount"]["owned_group_absent"] is True
assert v2["ram_absent"] is True and v2["ram_still_exists"] is False
old=json.loads(json.loads(payloads["query-originals/container-before-cleanup.json"])["stdout"])[0]
def mounts(value):
 rows=value["Mounts"];out={}
 for row in rows:
  assert isinstance(row,dict) and isinstance(row["Destination"],str) and row["Destination"] not in out
  out[row["Destination"]]=row
 return out
for label,prefix in (("initial_quiescence","initial"),("pre_unmount_quiescence","pre-unmount")):
 entry=v2[label];raw=payloads["recovery-v2-originals/"+prefix+"-container.json"]
 assert H(raw)==entry["container_observation_original"]["sha256"]
 obs=json.loads(raw);assert obs==entry["container_observation"]
 assert obs["returncode"]==0 and obs["primary_error"] is None and obs["cleanup_error"] is None and obs["owned_group_absent"] is True
 now=json.loads(obs["stdout"])[0]
 assert all(now[k]==old[k] for k in ("Id","Name","Image","Path","Args","Config","HostConfig"))
 assert mounts(now)==mounts(old) and len(mounts(now))==9
 assert now["State"]["Running"] is False and now["State"]["Pid"]==0
 assert entry["original_groups_absent"] is True and entry["original_processes"]==entry["process_scan_denied"]==[]
 assert entry["ram"]["mount"]["mount_id"]=="738" and entry["ram"]["mount"]["device"]=="0:71"
inv=json.loads(gzip.decompress(payloads["recovery-v2-originals/ram-inventory.json.gz"]))
assert inv["files"]==inv["directories"]=={} and inv["unexpected_payloads"]==[]
with gzip.GzipFile(fileobj=io.BytesIO(payloads["recovery-v2-originals/ram-originals.tar.gz"])) as z:
 with tarfile.open(fileobj=z,mode="r|") as tar:assert list(tar)==[]
 while z.read(65536):pass
assert not pathlib.Path("/dev/shm/pinkha-loaded-account-source-graph-20261123").exists()
combined=sum(int(x["metadata"]["st_size"]) for x in originals if str(B)+"/ram-" in x["original_path"])
assert combined==9099390 and combined<16*1024*1024
audit={"schema":"loaded-account-witness-ram-attempt2-originals-audit-v1","status":"PASS_ORIGINAL_EVIDENCE_AUDIT","controller_source_head":HEAD,"actual_go_source_queries":1,"actual_native_builds":0,"actual_test_methods":0,"complete_dependency_graph_admitted":False,"query_original_status":"FAILED","first_error":"source_query_stdout_limit","stdout_original_bytes":8388608,"stdout_complete":False,"original_cleanup_status":"FAILED","original_cleanup_errors":["docker_owned_kill_20_second_timeout","sudo_owned_cli_group_PermissionError"],"source_before_after_exact":True,"source_rows":counts,"actual_loaded_python_rows":1,"recovery_v1":{"status":"FAILED","raw_inspection_of_failed_invocation":"NOT_RECORDED","earlier2184_is_a_different_observation":True},"recovery_v2":{"status":"PASS_LATER_CUSTODY_RECOVERY","observed_final_ram_files":0,"observed_final_ram_directories":0,"generated_test_main_admitted":False,"earlier_transient_ram_contents_not_inferred":True,"full_remaining_ram_archive_readback":True,"exact_normal_unmount":True,"original_failures_unchanged":True},"combined_external_evidence_bytes":combined,"no_semantic_native_source_or_destination_authorization":True,"originals":originals,"source_pins":{str(p):h for p,h in pins.items()}}
payloads["audit.json"]=(json.dumps(audit,sort_keys=True,indent=2)+"\n").encode()
total=sum(map(len,payloads.values()))
assert total<2*1024*1024
assert shutil.disk_usage(R).free>=1073741824+total+65536
for relative,raw in payloads.items():
 p=T/relative;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==raw
for p,h in pins.items():assert H(read(p)[0])==h
assert git("rev-parse","HEAD")==HEAD
result={"status":"PASS_ORIGINAL_EVIDENCE_AUDIT","target":str(T),"files":len(payloads),"written_bytes":total,"audit_sha256":H(payloads["audit.json"]),"audit_path":str(T/"audit.json"),"original_query_status":"FAILED","recovery_v1_status":"FAILED","recovery_v2_status":"PASS_LATER_CUSTODY_RECOVERY","actual_go_queries":1,"new_builds_tests":0,"free_bytes":shutil.disk_usage(R).free}
with (D/"ram-attempt2-evidence-seal.json").open("x") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
print(json.dumps(result))
