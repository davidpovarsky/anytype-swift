from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,hashlib
out=Path(__file__).resolve().parent
with (out/"original.stdout").open("xb") as stdout,(out/"original.stderr").open("xb") as stderr:
 proc=subprocess.run([sys.executable,"-B",str(out/"audit_candidates.py")],stdout=stdout,stderr=stderr,timeout=240)
result={"return_code":proc.returncode,"finished_at":datetime.now(timezone.utc).isoformat(),"stdout_sha256":hashlib.sha256((out/"original.stdout").read_bytes()).hexdigest(),"stderr_sha256":hashlib.sha256((out/"original.stderr").read_bytes()).hexdigest()}
with (out/"execution.json").open("x") as f:json.dump(result,f,sort_keys=True,indent=2);f.write("\n")
