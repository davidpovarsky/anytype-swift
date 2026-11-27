import hashlib, os
from pathlib import Path
p=Path('/var/lib/sentinelx/uploads/pinkha-wave2-hierarchy-rename-stage-b3cfea8a789c4aba.py')
assert p.resolve(strict=True)==p and not p.is_symlink()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='b3cfea8a789c4abae7f2f2b8aa3202dc7cf2725a5fae2438eb5c5c9d6342f7eb'
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',str(p),'--coordination-story','1220962223365617'])
