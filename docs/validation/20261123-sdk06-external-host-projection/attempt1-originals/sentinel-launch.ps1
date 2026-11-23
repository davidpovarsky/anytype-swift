@'
import hashlib
from pathlib import Path
path=Path("/mnt/development/projects/diagnostics/sdk06-external-host-projection-launch-20261123.py")
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="fb60750130fd8d3b9b5e4a3cb79e9aa6fef29062623a54910eff448f23b23df2"
exec(compile(raw,str(path),"exec"),{"__name__":"__main__","__file__":str(path)})

'@ | ssh -T torah-dev python3 -B -
if($LASTEXITCODE -ne 0){throw 'The exact new SDK control did not qualify; preserve originals'}