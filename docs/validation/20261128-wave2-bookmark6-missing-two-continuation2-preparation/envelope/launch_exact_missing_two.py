import hashlib, os
from pathlib import Path
p = Path('/var/lib/sentinelx/uploads/pinkha-wave2-bookmark-missing-two-d7b0eb74a542290f.py')
raw = p.read_bytes()
assert p.is_file() and not p.is_symlink() and p.resolve(strict=True) == p
assert len(raw) == 37159 and hashlib.sha256(raw).hexdigest() == 'd7b0eb74a542290f67d1d6a68c7dc3f0ee87773ca9c7f82cfb109666a4edce54'
os.chdir('/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127')
os.environ['PWD'] = '/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127'
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-I', '-B', str(p), '--execute-reviewed-missing-two'])
