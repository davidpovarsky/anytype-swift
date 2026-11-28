import hashlib, os
from pathlib import Path
p=Path('/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-stage-0a4d01543136969a.py')
assert p.resolve(strict=True)==p and not p.is_symlink()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='0a4d01543136969aeb363bd56d0b87716fc25dab302b5580932740cefc28a548'
os.execv('/usr/bin/python3',['/usr/bin/python3','-B',str(p),'--coordination-story','1220963068892650'])
