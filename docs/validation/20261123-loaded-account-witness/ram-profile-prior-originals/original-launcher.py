import hashlib,os,pathlib,shutil,subprocess,sys
p=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
s=p/"Tools/AnyEngineValidation/loaded_account_witness/graph.py"
head="cd3f430633d9331ecad49230e0a20082f8f9e8b0"
available=shutil.disk_usage("/mnt/development").free
assert available>=2650000000,("source_only_start_reserve",available)
assert hashlib.sha256(s.read_bytes()).hexdigest()=="6aacb0c911aed49d88d9f0e7ef82b08a5ceab431139bb7b71f17c7d0aedfd23d"
assert subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],timeout=15).decode().strip()==head
assert not subprocess.check_output(["git","-C",str(p),"status","--porcelain=v1","--untracked-files=all"],timeout=15).strip()
os.execv(sys.executable,[sys.executable,"-B",str(s),"--expected-controller-sha",head,"--execute"])
