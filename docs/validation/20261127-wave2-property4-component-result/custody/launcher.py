import hashlib, os
from pathlib import Path
p=Path('/var/lib/sentinelx/uploads/pinkha-wave2-property4-stage-2a7ef1c0d7f5957e.py')
assert p.resolve(strict=True)==p and not p.is_symlink()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='2a7ef1c0d7f5957ef1194b27d34a5456d254b1d077f6e3eceda628925f236a1b'
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',str(p),'--coordination-story','1220960923229560'])
