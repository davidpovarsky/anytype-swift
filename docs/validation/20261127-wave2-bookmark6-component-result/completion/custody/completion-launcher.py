import hashlib, os, stat
p = '/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-readonly-completion-c628aee892a5cff1.py'
fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
try:
    info = os.fstat(fd)
    assert stat.S_ISREG(info.st_mode) and info.st_size == 63597
    raw = os.read(fd, 63598)
    assert len(raw) == 63597 and hashlib.sha256(raw).hexdigest() == 'c628aee892a5cff15bd80f2473f64cffaf831f816d51412a54e142f7e7c410a5'
finally:
    os.close(fd)
os.execv('/usr/bin/python3', ['/usr/bin/python3', '-I', '-B', p, '--qualify-original-attempt1'])
