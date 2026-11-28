import base64, gzip, hashlib, json, os, stat, sys
p = '/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127/completion1.json'
offset = int(sys.argv[1]); assert offset in (0, 48000, 96000)
fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME)
try:
    before = os.fstat(fd)
    assert stat.S_ISREG(before.st_mode) and before.st_size == 589557 and before.st_nlink == 1
    parts=[]; total=0
    while total < 589557:
        part=os.read(fd, min(65536, 589557-total)); assert part
        parts.append(part); total += len(part)
    assert not os.read(fd, 1)
    after=os.fstat(fd)
    assert before == after
finally:
    os.close(fd)
raw=b''.join(parts)
assert len(raw)==589557 and hashlib.sha256(raw).hexdigest()=='ac38377da08aac68629d2ae04f8d4878a52eb8b28ee3e1009700c810902302d7'
packed=gzip.compress(raw,compresslevel=9,mtime=0)
encoded=base64.b64encode(packed).decode('ascii')
assert len(encoded) <= 144000 and offset < len(encoded)
print(json.dumps({'path':p,'rawBytes':len(raw),'rawSHA256':hashlib.sha256(raw).hexdigest(),'gzipBytes':len(packed),'gzipSHA256':hashlib.sha256(packed).hexdigest(),'base64Characters':len(encoded),'offset':offset,'chunk':encoded[offset:offset+48000],'unchangedStat':True},sort_keys=True))
