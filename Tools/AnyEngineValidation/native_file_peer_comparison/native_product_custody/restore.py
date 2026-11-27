#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,shutil
root=Path(__file__).resolve().parent;r=json.loads((root/'receipt.json').read_text());src=Path(r['target']);dst=Path(r['source']);meta=r['sourceMetadata']
assert not dst.exists() and not dst.is_symlink(),'refuse overwrite'
assert src.is_file() and not src.is_symlink() and src.stat().st_nlink==1
assert src.stat().st_size==meta['bytes'] and hashlib.sha256(src.read_bytes()).hexdigest()==r['sourceSHA256']
assert shutil.disk_usage(dst.parent).free>=2*1024**3+meta['allocatedBytes']+4*1024**2
assert shutil.disk_usage(root).free>=512*1024**2
tmp=dst.with_name(dst.name+'.restore-79248a63');assert not tmp.exists()
h=hashlib.sha256();size=0
with src.open('rb') as a,tmp.open('xb') as b:
 for data in iter(lambda:a.read(1024**2),b''):b.write(data);h.update(data);size+=len(data)
 b.flush();os.fsync(b.fileno())
assert size==meta['bytes'] and h.hexdigest()==r['sourceSHA256']
os.chmod(tmp,meta['mode']);os.chown(tmp,meta['uid'],meta['gid']);os.utime(tmp,ns=(meta['atime_ns'],meta['mtime_ns']))
fd=os.open(tmp,os.O_RDONLY);os.fsync(fd);os.close(fd)
assert not dst.exists();os.replace(tmp,dst)
fd=os.open(dst.parent,os.O_RDONLY);os.fsync(fd);os.close(fd)
print(json.dumps({'restored':str(dst),'sha256':r['sourceSHA256'],'bytes':dst.stat().st_size,'mode':dst.stat().st_mode & 0o7777}))
