#!/usr/bin/env python3
"""Restore the retained native product without replacing an existing path."""
from pathlib import Path
import hashlib,json,os,shutil


def install_exclusively(tmp, dst):
    """Atomically create dst, failing if any file or symlink already owns it.

    The fully verified temporary file is a sibling of dst. POSIX link provides
    the no-replace operation; a preceding exists() check alone cannot do that.
    Fsync the installed name before retiring the temporary link, so either name
    retains the verified bytes if the process stops during installation.
    """
    assert tmp.parent == dst.parent, 'temporary and destination must be siblings'
    os.link(tmp, dst, follow_symlinks=False)
    fd=os.open(dst.parent,os.O_RDONLY)
    try:
        os.fsync(fd)
        tmp.unlink()
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
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
    install_exclusively(tmp,dst)
    print(json.dumps({'restored':str(dst),'sha256':r['sourceSHA256'],'bytes':dst.stat().st_size,'mode':dst.stat().st_mode & 0o7777}))


if __name__ == '__main__':
    main()
