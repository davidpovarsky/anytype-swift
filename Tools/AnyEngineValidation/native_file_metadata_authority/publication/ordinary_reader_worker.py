import hashlib,json,os,re,stat,subprocess,sys
from pathlib import Path
assert os.getuid()==1001 and os.getegid()==1002
assert len(sys.argv)==2 and len(sys.argv[1].encode())<=60*1024
request=json.loads(sys.argv[1]);rows=request['files']
assert 1<=len(rows)<=1001
common=Path(request['repository'])
assert str(common)=='/mnt/development/projects/git-mirrors/anytype-swift.git'
assert common.resolve()==common and common.is_dir()
assert re.fullmatch('[0-9a-f]{40}',request['commit'])
assert 0<request['tree']['bytes']<=8*1024**2
assert re.fullmatch('[0-9a-f]{64}',request['tree']['sha256'])
assert sum(row['bytes'] for row in rows)<=32*1024**2
for row in rows:
 p=Path(row['path']);assert p.resolve()==p and not p.is_symlink()
 assert p.is_relative_to(common/'objects') or p==Path(request['ref'])
 assert 0<=row['bytes']<=8*1024**2
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  before=os.fstat(stream.fileno());assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==row['bytes']
  data=stream.read(row['bytes']+1);after=os.fstat(stream.fileno())
  assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
packed=request['packedObjectIDs'];assert len(packed)<=1000 and len(set(packed))==len(packed)
assert all(re.fullmatch('[0-9a-f]{40}',value) for value in packed)
expected_blobs=request['expectedPackedBlobs']
assert set(expected_blobs)<=set(packed)
children=[];packed_rows=[]
git=['git','--no-optional-locks','-c','safe.directory='+str(common),'-c','gc.auto=0',
     '-c','maintenance.auto=false','-C',str(common)]

def git_stream(role,arguments,consume,stdin=None):
 # This child inherits the unchanged f9de owner's session/group. The worker
 # never signals or probes a historical child PID; exceptional descendants
 # remain owned by the supervisor's unreaped leader until group cleanup.
 child=subprocess.Popen(git+arguments,stdin=stdin,stdout=subprocess.PIPE,
                         start_new_session=False,close_fds=True,restore_signals=True)
 row={'role':role,'exitCode':None,'stdoutEOF':False,'sameOwnedGroup':False}
 children.append(row)
 try:
  assert os.getpgid(child.pid)==os.getpgrp()
  row['sameOwnedGroup']=True
  consume(child.stdout)
  assert child.stdout.read(1)==b'', 'complete child Git stdout EOF required'
  row['stdoutEOF']=True
  child.stdout.close()
  code=child.wait(timeout=5)
  row['exitCode']=code
  assert code==0, 'ordinary child Git must exit normally'
 except BaseException:
  print(json.dumps({'ordinaryChildGitFailure':row},sort_keys=True),file=sys.stderr)
  raise
 finally:
  child.stdout.close()

def read_exact(stream,count):
 parts=[];remaining=count
 while remaining:
  part=stream.read(min(65536,remaining))
  assert part, 'short Git content stream'
  parts.append(part);remaining-=len(part)
 return b''.join(parts)

def consume_objects(stream):
 total=0
 for wanted in packed:
  header=stream.readline(257)
  assert len(header)<=256 and header.endswith(b'\n')
  fields=header[:-1].decode('ascii').split(' ')
  assert len(fields)==3 and fields[0]==wanted
  kind=fields[1];assert kind in ('blob','tree','commit','tag')
  assert re.fullmatch('0|[1-9][0-9]*',fields[2])
  size=int(fields[2]);assert size<=8*1024**2
  total+=size;assert total<=32*1024**2
  object_hash=hashlib.sha1((kind+' '+str(size)).encode()+b'\0')
  content_hash=hashlib.sha256();remaining=size
  while remaining:
   data=read_exact(stream,min(65536,remaining));remaining-=len(data)
   object_hash.update(data);content_hash.update(data)
  assert read_exact(stream,1)==b'\n'
  assert object_hash.hexdigest()==wanted, 'packed Git object identity differs'
  body={'bytes':size,'sha256':content_hash.hexdigest()}
  if kind=='blob':
   assert wanted in expected_blobs and body==expected_blobs[wanted], 'exact declared source blob required'
  else:
   assert wanted not in expected_blobs
  packed_rows.append({'objectID':wanted,'type':kind,**body})

if packed:
 # A bounded anonymous descriptor avoids pipe write/read deadlock and creates
 # no file in a repository, account, source directory or shared temp location.
 ids=('\n'.join(packed)+'\n').encode('ascii');assert len(ids)<=41000
 descriptor=os.memfd_create('pinkha-published-object-ids',os.MFD_CLOEXEC)
 try:
  remaining=memoryview(ids)
  while remaining:
   written=os.write(descriptor,remaining);assert written>0;remaining=remaining[written:]
  os.lseek(descriptor,0,os.SEEK_SET)
  git_stream('exact-packed-object-content',['cat-file','--batch'],consume_objects,descriptor)
 finally:
  os.close(descriptor)

tree_result={}
def consume_tree(stream):
 hasher=hashlib.sha256();count=0
 while True:
  data=stream.read(65536)
  if not data:break
  count+=len(data);assert count<=request['tree']['bytes']
  hasher.update(data)
 tree_result.update(bytes=count,sha256=hasher.hexdigest())
 assert tree_result==request['tree'], 'ordinary complete candidate tree differs'

git_stream('complete-candidate-tree',['ls-tree','-r','-z',request['commit']],consume_tree)
print(json.dumps({'uid':os.getuid(),'effectiveGid':os.getegid(),'exactFilesRead':len(rows),
 'bytes':sum(row['bytes'] for row in rows),'allOriginalHashesMatch':True,
 'packedObjects':packed_rows,'packedBodiesSHA1Verified':True,
 'packedBlobPayloadsSHA256Verified':True,'candidateTree':tree_result,
 'childGitCommands':children},sort_keys=True))
