#!/usr/bin/env python3
"""Deterministic lossless archive format for a fixed, closed native build set.

No shell archive/extract invocation, no traversal through archived symlinks, and
no local large archive. This module has no remote or retirement side effects.
"""
import base64
import collections
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import zlib

MIB = 1024**2
MANIFEST_NAME = '__pinkha_closed_build_custody__.json'
MAX_ENTRIES = 25000
MAX_MANIFEST = 8*MIB


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'))+'\n').encode()


def stamp(info):
    return [info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink, info.st_atime_ns]


def read_file(path):
    return os.fdopen(os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME), 'rb')


def digest_file(path, guard=lambda: None):
    h=hashlib.sha256()
    with read_file(path) as source:
        while data:=source.read(MIB):
            guard();h.update(data)
    return h.hexdigest()


def valid_relative(value):
    assert isinstance(value, str) and value and '\x00' not in value and '\\' not in value
    path=Path(value)
    assert not path.is_absolute() and all(part not in ('', '.', '..') for part in value.split('/'))
    assert path.as_posix()==value
    return path


def safe_path(stage, relative):
    p=stage/valid_relative(relative)
    current=stage
    assert current.is_dir() and not current.is_symlink()
    for component in p.relative_to(stage).parts[:-1]:
        current=current/component
        assert current.is_dir() and not current.is_symlink(), 'non-directory extraction parent'
    return p


def manifest(roots, guard=lambda: None, known_links=None):
    """Capture regular files, directories, symlinks and complete hardlink groups.

    O_NOATIME protects file/directory access metadata. The first readlink can
    update symlink atime; that ordinary read effect is recorded separately and
    the observed post-read value is the explicit custody baseline. Later reads
    use the captured target only after exact lstat race-witness validation.
    """
    rows=[];identities={};links={};groups=collections.defaultdict(list);access=[]
    for label, root in sorted(roots.items()):
        assert label in ('indexed', 'cache', 'legacy')
        root=Path(root);assert root.is_absolute() and root.parent.resolve()==root.parent
        assert root.is_dir() and not root.is_symlink()
        stack=[(label,root)]
        while stack:
            relative,path=stack.pop();valid_relative(relative);before=path.lstat()
            kind='directory' if stat.S_ISDIR(before.st_mode) else 'file' if stat.S_ISREG(before.st_mode) else 'symlink' if stat.S_ISLNK(before.st_mode) else None
            assert kind, 'special file is outside closed build custody: '+relative
            row={'path':relative,'kind':kind,'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,
                 'gid':before.st_gid,'atimeNS':before.st_atime_ns,'mtimeNS':before.st_mtime_ns,
                 'xattrs':{key:base64.b64encode(os.getxattr(path,key,follow_symlinks=False)).decode()
                           for key in sorted(os.listxattr(path,follow_symlinks=False))}}
            assert sum(len(key)+len(value) for key,value in row['xattrs'].items())<=MIB
            if kind=='file':
                row.update(bytes=before.st_size,sha256=digest_file(path,guard),nlink=before.st_nlink)
                groups[(before.st_dev,before.st_ino)].append(relative)
            elif kind=='symlink':
                if known_links is None:
                    target=os.readlink(path)
                else:
                    witness=known_links[relative]
                    assert stamp(before)==witness['stamp'],'symlink identity/metadata changed: '+relative
                    target=witness['target']
                row.update(target=target,bytes=before.st_size)
            else:
                fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOATIME)
                try:
                    with os.scandir(fd) as items:children=sorted(item.name for item in items)
                finally:os.close(fd)
                stack.extend((relative+'/'+name,path/name) for name in reversed(children))
            after=path.lstat()
            assert stamp(before)[:-1]==stamp(after)[:-1], 'source race: '+relative
            if before.st_atime_ns!=after.st_atime_ns:
                assert kind=='symlink' and known_links is None, 'unexpected access-time change'
                access.append({'path':relative,'beforeAtimeNS':before.st_atime_ns,'afterAtimeNS':after.st_atime_ns})
                row['atimeNS']=after.st_atime_ns
            identities[relative]=stamp(after)
            if kind=='symlink':links[relative]={'target':row['target'],'stamp':stamp(after)}
            rows.append(row);assert len(rows)<=MAX_ENTRIES
            if len(rows)%64==0:guard()
    rows.sort(key=lambda row:row['path'])
    by_path={row['path']:row for row in rows};topology=[]
    for paths in groups.values():
        paths.sort()
        assert all(by_path[path]['nlink']==len(paths) for path in paths), 'hardlink extends outside the approved root set'
        if len(paths)>1:
            identity={k:v for k,v in by_path[paths[0]].items() if k!='path'}
            assert all({k:v for k,v in by_path[path].items() if k!='path'}==identity for path in paths)
            topology.append(paths)
    topology.sort()
    value={'version':1,'roots':{label:str(path) for label,path in sorted(roots.items())},
           'entries':rows,'hardlinkTopology':topology}
    assert len(canonical_json(value))<=MAX_MANIFEST
    return value,identities,links,access


def ns_text(value):
    seconds,nanos=divmod(value,1_000_000_000)
    return str(seconds)+'.'+str(nanos).zfill(9)


def tar_info(row, hardlink=None):
    info=tarfile.TarInfo(row['path']);info.mode=row['mode'];info.uid=row['uid'];info.gid=row['gid']
    info.uname=info.gname='';info.mtime=row['mtimeNS']//1_000_000_000
    info.pax_headers={'atime':ns_text(row['atimeNS']),'mtime':ns_text(row['mtimeNS'])}
    if row['kind']=='directory':info.type=tarfile.DIRTYPE
    elif row['kind']=='symlink':info.type=tarfile.SYMTYPE;info.linkname=row['target']
    elif hardlink:info.type=tarfile.LNKTYPE;info.linkname=hardlink
    else:info.type=tarfile.REGTYPE;info.size=row['bytes']
    return info


def tar_chunks(roots, wanted, identities, guard=lambda: None):
    """A deterministic tar stream; every input inode/byte is revalidated."""
    manifest_bytes=canonical_json(wanted);meta=tarfile.TarInfo(MANIFEST_NAME)
    meta.mode=0o600;meta.uid=meta.gid=0;meta.mtime=0;meta.size=len(manifest_bytes)
    count=0
    header=meta.tobuf(tarfile.PAX_FORMAT,encoding='utf-8',errors='strict')
    for piece in (header,manifest_bytes,b'\0'*(-len(manifest_bytes)%512)):
        count+=len(piece);yield piece
    first={path:paths[0] for paths in wanted['hardlinkTopology'] for path in paths[1:]}
    for row in wanted['entries']:
        guard();label,_,relative=row['path'].partition('/')
        path=Path(roots[label])/relative
        assert stamp(path.lstat())==identities[row['path']], 'archive input changed: '+row['path']
        header=tar_info(row,first.get(row['path'])).tobuf(tarfile.PAX_FORMAT,encoding='utf-8',errors='strict')
        count+=len(header);yield header
        if row['kind']=='file' and row['path'] not in first:
            digest=hashlib.sha256();length=0
            with read_file(path) as stream:
                while data:=stream.read(MIB):
                    guard();length+=len(data);digest.update(data);count+=len(data);yield data
            assert length==row['bytes'] and digest.hexdigest()==row['sha256'], 'archive file differs'
            padding=b'\0'*(-length%512);count+=len(padding);yield padding
        assert stamp(path.lstat())==identities[row['path']], 'archive input metadata changed'
    end=b'\0'*1024;count+=len(end);yield end
    yield b'\0'*(-count%tarfile.RECORDSIZE)


class GzipArchiveReader:
    """Bounded synchronous read interface for a deterministic gzip level-1 tar."""
    def __init__(self, roots, wanted, identities, guard=lambda: None):
        self._source=iter(tar_chunks(roots,wanted,identities,guard));self._zip=zlib.compressobj(1,zlib.DEFLATED,31)
        self._buffer=bytearray();self._done=False;self.rawBytes=0;self.rawSHA256=hashlib.sha256()

    def read(self, count=65536):
        assert 0<count<=MIB
        while len(self._buffer)<count and not self._done:
            try:
                piece=next(self._source);self.rawBytes+=len(piece);self.rawSHA256.update(piece)
                self._buffer.extend(self._zip.compress(piece))
            except StopIteration:
                self._buffer.extend(self._zip.flush());self._done=True
        result=bytes(self._buffer[:count]);del self._buffer[:count];return result

    def close(self):
        self._source.close();self._buffer.clear()


def measured_archive(roots, wanted, identities, guard=lambda: None):
    source=GzipArchiveReader(roots,wanted,identities,guard);digest=hashlib.sha256();count=0
    try:
        while data:=source.read():guard();count+=len(data);digest.update(data)
        return {'bytes':count,'sha256':digest.hexdigest(),'tarBytes':source.rawBytes,
                'tarSHA256':source.rawSHA256.hexdigest(),'encoding':'gzip-level-1-tar-pax',
                'zlibCompileVersion':zlib.ZLIB_VERSION,'zlibRuntimeVersion':zlib.ZLIB_RUNTIME_VERSION}
    finally:source.close()


def fsync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOATIME)
    try:os.fsync(fd)
    finally:os.close(fd)


def restore_metadata(path, row):
    os.chown(path,row['uid'],row['gid'],follow_symlinks=False)
    if row['kind']!='symlink':os.chmod(path,row['mode'],follow_symlinks=False)
    else:assert stat.S_IMODE(path.lstat().st_mode)==row['mode']
    for key in set(os.listxattr(path,follow_symlinks=False))-set(row['xattrs']):os.removexattr(path,key,follow_symlinks=False)
    for key,value in row['xattrs'].items():os.setxattr(path,key,base64.b64decode(value,validate=True),follow_symlinks=False)
    os.utime(path,ns=(row['atimeNS'],row['mtimeNS']),follow_symlinks=False)


def verify_restored(stage, wanted, guard=lambda: None):
    # readlink may update only the newly restored destination atime. Restore
    # that value once and capture exact lstat witnesses for subsequent scans.
    links={}
    for row in wanted['entries']:
        if row['kind']=='symlink':
            path=safe_path(stage,row['path']);assert os.readlink(path)==row['target']
            os.utime(path,ns=(row['atimeNS'],row['mtimeNS']),follow_symlinks=False)
            links[row['path']]={'target':row['target'],'stamp':stamp(path.lstat())}
    actual,identities,links,_=manifest({label:stage/label for label in wanted['roots']},guard,links)
    actual['roots']=wanted['roots']
    assert actual==wanted,'restored complete bytes/metadata/topology differ'
    return identities,links


def extract_stream(reader, stage, wanted, guard=lambda: None):
    """Restore only an exact expected manifest into an exclusive stage.

    The caller must authenticate the entire compressed stream before installing
    any original path. A failure leaves staging bytes for evidence/inspection.
    """
    assert stage.is_dir() and not stage.is_symlink() and not any(stage.iterdir())
    first={path:paths[0] for paths in wanted['hardlinkTopology'] for path in paths[1:]}
    manifest_bytes=canonical_json(wanted);expected=iter(wanted['entries']);seen=[]
    with tarfile.open(fileobj=reader,mode='r|gz',bufsize=65536) as archive:
        meta=archive.next()
        assert meta is not None and meta.name==MANIFEST_NAME and meta.isreg() and meta.size==len(manifest_bytes)
        member=archive.extractfile(meta);assert member is not None
        assert member.read(len(manifest_bytes)+1)==manifest_bytes
        while entry:=archive.next():
            guard();row=next(expected,None);assert row is not None,'unexpected archive entry'
            assert entry.name.rstrip('/')==row['path'] and entry.mode==row['mode'] and entry.uid==row['uid'] and entry.gid==row['gid']
            assert entry.pax_headers.get('atime')==ns_text(row['atimeNS']) and entry.pax_headers.get('mtime')==ns_text(row['mtimeNS'])
            path=safe_path(stage,row['path']);assert not path.exists() and not path.is_symlink()
            if row['kind']=='directory':assert entry.isdir();path.mkdir(mode=0o700)
            elif row['kind']=='symlink':assert entry.issym() and entry.linkname==row['target'];os.symlink(row['target'],path)
            elif row['path'] in first:
                assert entry.islnk() and entry.linkname==first[row['path']]
                source=safe_path(stage,entry.linkname);assert source.is_file() and not source.is_symlink()
                os.link(source,path,follow_symlinks=False)
            else:
                assert entry.isreg() and entry.size==row['bytes']
                member=archive.extractfile(entry);assert member is not None
                fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);digest=hashlib.sha256();length=0
                try:
                    while data:=member.read(MIB):
                        guard();length+=len(data);assert length<=row['bytes'];digest.update(data);view=memoryview(data)
                        while view:
                            amount=os.write(fd,view);assert amount>0;view=view[amount:]
                    assert length==row['bytes'] and digest.hexdigest()==row['sha256'];os.fsync(fd)
                finally:os.close(fd)
            seen.append(row)
        assert next(expected,None) is None,'archive truncated before all expected entries'
    # Set metadata only after all hardlinks/children exist. Files, then deepest
    # directories, preserve shared inode metadata and directory access times.
    for row in sorted(seen,key=lambda row:(row['kind']=='directory',-len(Path(row['path']).parts))):
        guard();path=safe_path(stage,row['path']);restore_metadata(path,row)
        if row['kind']=='directory':fsync_dir(path)
        elif row['kind']=='file':
            with read_file(path) as stream:os.fsync(stream.fileno())
    fsync_dir(stage);return verify_restored(stage,wanted,guard)


def tiny_roundtrip(root):
    """Actual metadata, hardlink, Unicode, symlink and binary restoration check."""
    before=root/'tiny-original';after=root/'tiny-restored';before.mkdir(mode=0o700);after.mkdir(mode=0o700)
    (before/'indexed').mkdir(mode=0o700);(before/'cache').mkdir(mode=0o700)
    sample=before/'indexed'/'בדיקה.bin';sample.write_bytes(bytes(range(256))*7+b'\x00\r\nEND')
    sample.chmod(0o640);os.setxattr(sample,'user.pinkha_custody',b'\x00exact\xff')
    os.link(sample,before/'cache'/'hardlink.bin');os.symlink('../indexed/בדיקה.bin',before/'cache'/'pointer')
    roots={label:before/label for label in ('indexed','cache')};wanted,identities,_,_=manifest(roots)
    one=measured_archive(roots,wanted,identities);two=measured_archive(roots,wanted,identities);assert one==two
    reader=GzipArchiveReader(roots,wanted,identities);raw=bytearray()
    while data:=reader.read():raw.extend(data)
    assert hashlib.sha256(raw).hexdigest()==one['sha256'] and len(raw)==one['bytes']
    extract_stream(io.BytesIO(raw),after,wanted)
    assert (after/'indexed'/'בדיקה.bin').stat().st_ino==(after/'cache'/'hardlink.bin').stat().st_ino
    assert sample.read_bytes()==(after/'indexed'/'בדיקה.bin').read_bytes()
    refused=False
    try:extract_stream(io.BytesIO(raw),after,wanted)
    except AssertionError:refused=True
    assert refused,'restore overwrote populated staging'
    for invalid in ('../escape','indexed/../../escape','/absolute','indexed/./alias','indexed//alias'):
        refused=False
        try:valid_relative(invalid)
        except AssertionError:refused=True
        assert refused,'unsafe archive path admitted'
    return {'status':'PASS_TINY_EXACT_ARCHIVE_RESTORE_AND_EXCLUSIVE_BOUNDARIES','entries':len(wanted['entries']),
            'binaryBytes':sample.stat().st_size,'hardlinkGroups':len(wanted['hardlinkTopology']),
            'archiveSHA256':one['sha256'],'archiveBytes':one['bytes'],'deterministicTwoPass':True,
            'unicodeFilename':True,'xattrBytesExact':True,'symlinkTargetExact':True,'populatedStageRefused':True,
            'traversalCasesRefused':5}
