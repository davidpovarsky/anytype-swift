import hashlib, os
from pathlib import Path
p = Path('/var/lib/sentinelx/uploads/pinkha-wave2-bookmark-missing-two-0e8fa19767222fef.py')
raw = p.read_bytes()
assert p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p
assert len(raw) == 34063 and hashlib.sha256(raw).hexdigest() == '0e8fa19767222fef6f954bf4bfdb34e58a77986251e69cf461b29f7311f01627'
os.chdir('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
os.environ['PWD'] = '/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127'
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-I', '-B', str(p), '--execute-reviewed-missing-two'])
