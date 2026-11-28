import os,stat,hashlib,json,time,datetime
from pathlib import Path
TOOLCHAIN=Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin')
MODULES=('TorahInspectorCore','PinkhaKit','PinkhaAnyEngine','PinkhaAnyIntegration','PinkhaAnyHost')
began=time.monotonic()
def require(ok,label):
 if not ok:raise RuntimeError(label)
 if time.monotonic()-began>20:raise RuntimeError('bounded metadata read deadline')
identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_atime_ns)
def read_exact(p,expected_sha,maximum):
 require(p.resolve()==p,'canonical input')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
 try:
  b=os.fstat(fd);require(stat.S_ISREG(b.st_mode) and b.st_nlink==1 and b.st_size<=maximum,'bounded regular input')
  raw=bytearray()
  while len(raw)<=b.st_size:
   require(True,'deadline');v=os.read(fd,min(65536,b.st_size+1-len(raw)))
   if not v:break
   raw.extend(v)
  require(len(raw)==b.st_size and hashlib.sha256(raw).hexdigest()==expected_sha,'whole input digest')
  require(identity(b)==identity(os.fstat(fd))==identity(os.lstat(p)),'stable input including atime')
  return bytes(raw),{'path':str(p),'bytes':len(raw),'sha256':expected_sha,'metadataUnchangedIncludingAtime':True}
 finally:os.close(fd)
def observed_driver_commands(data):
    """The retained decoder, restricted to pinned MessagePack argv arrays."""
    needle = b'\xb3builtin-SwiftDriver'; offset = 0; found = {}
    while (start := data.find(needle, offset)) >= 0:
        offset = start+len(needle)
        require(start >= 3 and data[start-3] == 0xdc, 'expected original argv array16')
        count = int.from_bytes(data[start-2:start], 'big')
        require(1 <= count <= 256, 'bounded original driver argv')
        pos = start; args = []
        for _ in range(count):
            require(pos < len(data), 'complete original driver string')
            tag = data[pos]; pos += 1
            if 0xa0 <= tag <= 0xbf:
                length = tag & 31
            elif tag in (0xd9, 0xda, 0xdb):
                width = {0xd9: 1, 0xda: 2, 0xdb: 4}[tag]
                require(pos+width <= len(data), 'complete original string length')
                length = int.from_bytes(data[pos:pos+width], 'big'); pos += width
            else:
                raise RuntimeError('original driver argv contains non-string')
            require(length <= 8192 and pos+length <= len(data), 'bounded complete original string')
            args.append(data[pos:pos+length].decode()); pos += length
        if '-module-name' not in args:
            continue
        name = args[args.index('-module-name')+1]
        if name not in MODULES:
            continue
        require(args[:3] == ['builtin-SwiftDriver', '--', str(TOOLCHAIN/'swiftc')], 'original Swift driver')
        row = {'argv': args, 'rawArraySHA256': hashlib.sha256(data[start-3:pos]).hexdigest()}
        if name in found:
            require(found[name]['argv'] == row['argv'] and found[name]['rawArraySHA256'] == row['rawArraySHA256'],
                    'different duplicate original driver invocations')
            found[name]['identicalOccurrences'] += 1
        else:
            found[name] = row | {'identicalOccurrences': 1}
    return found


p=Path('/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127/out/Intermediates.noindex/XCBuildData/5f7ca1648219fca76b90928b9f530d1c2abba148c97b5a0410cbc00a30066ae3.xcbuilddata/task-store.msgpack')
raw,row=read_exact(p,'81dd4476f78ae077df1198d266910c2e570a7d364e5eb9ed965dbfb638e1257d',4*1024*1024)
commands=observed_driver_commands(raw)
d=Path('/mnt/development/projects/evidence/pinkha-original-type-runtime-provider25-20261127/prepared3')
listing=[]
if d.exists():
 require(d.resolve()==d and d.is_dir(),'prepared3 canonical directory')
 for e in os.scandir(d):
  require(len(listing)<128,'bounded prepared listing');listing.append({'name':e.name,'file':e.is_file(follow_symlinks=False),'directory':e.is_dir(follow_symlinks=False),'symlink':e.is_symlink()})
header=None
if any(x['name']=='crypto-header-source-manifest.json' and x['file'] for x in listing):
 h,m=read_exact(d/'crypto-header-source-manifest.json','4b5bbf85230625bee67f565b57f4de7338a5a55ca65d46ad5405a19a040d0961',1024*1024)
 header=m|{'text':h.decode('utf-8')}
print(json.dumps({'schema':'pinkha-retained-c3-product-argv-observation-v1','atUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'input':row,'observed':commands,'absent':[x for x in MODULES if x not in commands],'prepared3Listing':sorted(listing,key=lambda x:x['name']),'headerManifest':header,'scope':'Retained C3 command metadata only; no current-App/source/semantic/runtime qualification; original206 qualifier remains unchanged.','compilerInvocations':0,'nativeCalls':0},sort_keys=True))
