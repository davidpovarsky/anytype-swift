@'
import hashlib
from pathlib import Path
path=Path("/mnt/development/projects/diagnostics/sdk06-external-host-projection-measured-retry-20261123.py")
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="cb843b263cae5314e0240aeb23c1798f0a998204c1e8fbe51ef036cbda0adafd"
exec(compile(raw,str(path),"exec"),{"__name__":"__main__","__file__":str(path)})

'@ | ssh -T torah-dev python3 -B -
if($LASTEXITCODE -ne 0){throw 'Measured failed-method retry did not qualify; preserve originals'}