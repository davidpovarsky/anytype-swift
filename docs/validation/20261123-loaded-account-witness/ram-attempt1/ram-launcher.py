import pathlib,hashlib,subprocess,os,json,shutil
root=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
program=root/"Tools/AnyEngineValidation/loaded_account_witness/ram_graph.py"
expected="47e054b2d23fec7ce6540ee3e380b7e079d00832"
assert hashlib.sha256(program.read_bytes()).hexdigest()=="e5905005b7f367b26ff744a68ed0edd3498a04b2f1a83f17c349025b474a6f5e"
assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],timeout=30).decode().strip()==expected
assert not subprocess.check_output(["git","-C",str(root),"status","--porcelain=v1","--untracked-files=all"],timeout=30).strip()
free=shutil.disk_usage("/mnt/development").free
assert free>=1024**3+16*1024*1024,("new_source_profile_start",free)
memory=int(next(x for x in pathlib.Path("/proc/meminfo").read_text().splitlines() if x.startswith("MemAvailable:")).split()[1])*1024
assert memory>=4*1024**3,("new_source_profile_memory",memory)
attempt=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-graph-attempt1")
assert not attempt.exists()
marker=pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-ram-graph-source-20261123/one-query-launch.json")
data={"controller":expected,"program_sha256":hashlib.sha256(program.read_bytes()).hexdigest(),"free_bytes":str(free),"memory_available_bytes":str(memory),"source_query_only":True,"maximum_query_launches":1,"native_builds_tests":0}
with marker.open("x") as f:
 os.chmod(marker,0o600);json.dump(data,f,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())
os.execv("/usr/bin/python3",["/usr/bin/python3","-B",str(program),"--expected-controller-sha",expected,"--execute"])
