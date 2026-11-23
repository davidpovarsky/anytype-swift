#!/usr/bin/env python3
import pathlib,hashlib,json,os,subprocess,shutil,datetime
D=pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-ram-graph-source-20261123")
C=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
P=C/"Tools/AnyEngineValidation/loaded_account_witness/complete_projected_graph.py"
HEAD="1b98b7a01acc3b08d48c30c566d207f499a103d2"
SHA="5de50261d94fecea6ccf5b3f6f70870200c518d15b1d628bb29ca77b4418a806"
OUT=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-offline-completion1")
assert os.getresuid()==(1001,1001,1001)
assert hashlib.sha256(P.read_bytes()).hexdigest()==SHA
assert subprocess.check_output(["git","-C",str(C),"rev-parse","HEAD"],timeout=30).decode().strip()==HEAD
assert not subprocess.check_output(["git","-C",str(C),"status","--porcelain=v1","--untracked-files=all"],timeout=30).strip()
assert shutil.disk_usage("/mnt/development").free>=1090519040
assert not OUT.exists() and not OUT.is_symlink()
record={"schema":"one-offline-completion-launch-v1","time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"controller":HEAD,"source_sha256":SHA,"new_go_queries":0,"new_native_builds":0,"new_tests":0,"query_reruns":0,"outer_timeout_seconds":180,"offline_timeout_seconds":120,"original_result_sha256":"249c5a4a5a16ce7f39669925d03e804c8dab1517899c487179d123912b66601f"}
M=D/"one-offline-completion-launch1.json"
with M.open("x") as f:
 os.chmod(M,0o600);json.dump(record,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
os.execv("/usr/bin/python3",["/usr/bin/python3","-I","-B",str(P),"--expected-controller-sha",HEAD,"--execute"])
